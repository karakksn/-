import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from tradingview_screener import Query, Column

st.set_page_config(page_title="FM Stock Scout Dashboard", layout="wide")

# 다크 모드 스타일
st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2e3548; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽주식회사 포텐셜 스카우터")
st.caption("트레이딩뷰(TradingView) 실시간 스크리너와 연동하여 종목을 발굴하고 CA & PA 능력치를 분석합니다.")

# 사이드바: 트레이딩뷰 스크리너 프리셋 선택
st.sidebar.header("📡 트레이딩뷰 스카우트 소스")
market_choice = st.sidebar.selectbox(
    "가져올 시장 / 조건 선택",
    [
        "💎 미국 저평가 우량주 발굴 (PER<15, PBR<2)",
        "미국 시가총액 Top 15 (S&P/나스닥)",
        "미국 핵심 기술주(Tech) 15선",
        "트레이딩뷰 관심종목 파일(.txt) 직접 업로드"
    ]
)

def clamp(val, min_val=1, max_val=200):
    """값을 1~200점 범위로 보정"""
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰에서 종목 땡겨오기 함수
def fetch_tradingview_tickers(choice):
    tickers = []
    try:
        if choice == "💎 미국 저평가 우량주 발굴 (PER<15, PBR<2)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'price_earnings_ttm', 'price_book_fq', 'debt_to_equity_fq', 'market_cap_basic')
                .where(Column('price_earnings_ttm') > 0)
                .where(Column('price_earnings_ttm') < 15)
                .where(Column('price_book_fq') < 2.0)
                .where(Column('debt_to_equity_fq') < 150)
                .where(Column('market_cap_basic') > 2_000_000_000)
                .order_by('price_earnings_ttm', ascending=True)
                .limit(15)
            )
            df = q.get_scanner_data()[1]
            tickers = df['name'].tolist()

        elif choice == "미국 시가총액 Top 15 (S&P/나스닥)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'market_cap_basic')
                .order_by('market_cap_basic', ascending=False)
                .limit(15)
            )
            df = q.get_scanner_data()[1]
            tickers = df['name'].tolist()

        elif choice == "미국 핵심 기술주(Tech) 15선":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'sector', 'market_cap_basic')
                .where(Column('sector') == 'Technology')
                .order_by('market_cap_basic', ascending=False)
                .limit(15)
            )
            df = q.get_scanner_data()[1]
            tickers = df['name'].tolist()

    except Exception as e:
        st.sidebar.error(f"트레이딩뷰 데이터 수신 중 오류 발생: {e}")
        # 오류 발생 시 기본 안전 종목군
        tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]
    
    return tickers

# 티커 리스트 추출
if "파일" in market_choice:
    uploaded_file = st.sidebar.file_uploader("트레이딩뷰에서 내보낸 txt 파일", type=["txt"])
    if uploaded_file:
        raw_text = uploaded_file.read().decode("utf-8")
        raw_lines = [line.strip().split(":")[-1] for line in raw_text.splitlines() if line.strip()]
        ticker_list = [t for t in raw_lines if t.isalpha()]
    else:
        ticker_list = ["NVDA", "AAPL", "MSFT"]
else:
    ticker_list = fetch_tradingview_tickers(market_choice)

st.sidebar.info(f"스카우트 수집 종목 수: **{len(ticker_list)}개**")

# 단일 종목 CA & PA 계산 함수
@st.cache_data(ttl=3600)
def get_single_scout_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        name = info.get("shortName", ticker_symbol) or ticker_symbol
        currency = info.get("currency", "USD")
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        target_price = info.get("targetMeanPrice", current_price) or current_price
        
        roe = info.get("returnOnEquity", 0.0) or 0.0
        operating_margins = info.get("operatingMargins", 0.0) or 0.0
        debt_to_equity = info.get("debtToEquity", 100.0) or 100.0
        revenue_growth = info.get("revenueGrowth", 0.0) or 0.0
        earnings_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg_ratio = info.get("pegRatio", 2.0) or 2.0
        
        # 6대 세부 스탯 (1~200)
        stat_profitability = clamp(((roe / 0.20) * 100 + (operating_margins / 0.25) * 100) / 2)
        stat_stability = clamp(max(10, 200 - debt_to_equity))
        stat_rev_growth = clamp((revenue_growth / 0.30) * 120 + 40)
        stat_earn_growth = clamp((earnings_growth / 0.30) * 120 + 40)
        stat_valuation = clamp((2.5 - min(peg_ratio, 2.5)) * 80)
        
        upside = (target_price - current_price) / current_price if current_price > 0 else 0
        stat_upside = clamp((upside / 0.40) * 120 + 50)
        
        # 종합 CA 및 PA 공식
        ca = clamp(stat_profitability * 0.45 + stat_stability * 0.35 + stat_rev_growth * 0.2)
        potential_bonus = (stat_earn_growth * 0.35) + (stat_upside * 0.4) + (stat_valuation * 0.25)
        pa = clamp(ca * 0.5 + potential_bonus * 0.7)
        
        if pa < ca:
            pa = ca

        gap = pa - ca
        if pa >= 180 and gap >= 25:
            verdict = "🌟 원더키드 유망주"
        elif pa >= 170:
            verdict = "🛡️ 완성형 엘리트 우량주"
        elif gap >= 35:
            verdict = "💎 하이리스크 포텐형"
        else:
            verdict = "⚖️ 피크 도달"
            
        return {
            "티커": ticker_symbol,
            "기업명": name,
            "현재가": f"{current_price:,.2f} {currency}",
            "목표가": f"{target_price:,.2f} {currency}",
            "CA (현재능력)": ca,
            "PA (잠재능력)": pa,
            "포텐 여유": gap,
            "스카우트 판정": verdict,
            "stats": {
                "수익성 (ROE/마진)": stat_profitability,
                "재무건전성 (저부채)": stat_stability,
                "매출 성장성": stat_rev_growth,
                "이익 성장성": stat_earn_growth,
                "목표가 괴리율": stat_upside,
                "밸류에이션 매력": stat_valuation
            }
        }
    except Exception:
        return None

# 데이터 수집 및 렌더링
with st.spinner("트레이딩뷰 종목 수집 및 펀더멘털 스카우팅 분석 중..."):
    all_reports = []
    for t in ticker_list:
        res = get_single_scout_data(t)
        if res:
            all_reports.append(res)

if all_reports:
    # 1. 스카우팅 명단 (PA 내림차순 정렬)
    df_board = pd.DataFrame(all_reports).sort_values(by="PA (잠재능력)", ascending=False).reset_index(drop=True)
    
    st.subheader(f"📋 트레이딩뷰 실시간 스카우팅 보드 — {market_choice}")
    st.dataframe(
        df_board[["티커", "기업명", "현재가", "CA (현재능력)", "PA (잠재능력)", "포텐 여유", "스카우트 판정"]],
        use_container_width=True,
        column_config={
            "CA (현재능력)": st.column_config.ProgressColumn("CA (현재능력)", min_value=0, max_value=200, format="%d"),
            "PA (잠재능력)": st.column_config.ProgressColumn("PA (잠재능력)", min_value=0, max_value=200, format="%d"),
            "포텐 여유": st.column_config.NumberColumn("+포텐", format="+%d"),
        }
    )
    
    st.divider()

    # 2. 개별 기업 레이더 차트 및 스탯 뷰어
    st.subheader("🔍 개별 기업 육각형 능력치 리포트")
    selected_ticker = st.selectbox(
        "육각형 차트로 확인할 기업을 선택하세요:",
        options=df_board["티커"].tolist(),
        format_func=lambda x: f"{x} - {df_board.loc[df_board['티커'] == x, '기업명'].values[0]}"
    )

    data = next(item for item in all_reports if item["티커"] == selected_ticker)

    # 지표 카드 요약
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("기업명 (종목)", data["기업명"], delta=data["티커"])
    with col2:
        st.metric("현재 능력치 (CA)", f"{data['CA (현재능력)']} / 200")
    with col3:
        st.metric("잠재 능력치 (PA)", f"{data['PA (잠재능력)']} / 200", delta=f"+{data['포텐 여유']} Poten")
    with col4:
        st.metric("현재가 (목표가)", data["현재가"], delta=f"목표: {data['목표가']}")

    st.info(f"**스카우트 총평:** {data['스카우트 판정']}")

    # 차트 및 테이블 배치
    chart_col, detail_col = st.columns([1.2, 0.8])
    categories = list(data["stats"].keys())
    values = list(data["stats"].values())

    fig = go.Figure()
    # 잠재 능력치 한계선
    fig.add_trace(go.Scatterpolar(
        r=[data["PA (잠재능력)"]] * len(categories) + [data["PA (잠재능력)"]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(255, 165, 0, 0.08)',
        line=dict(color='rgba(255, 165, 0, 0.4)', dash='dash'),
        name='잠재 한계치 (PA Bound)'
    ))
    # 현재 세부 스탯 다각형
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(0, 230, 118, 0.35)',
        line=dict(color='#00E676', width=2),
        name='스탯 분포'
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 200], tickvals=[50, 100, 150, 200], tickfont=dict(color="#888888", size=9)),
            angularaxis=dict(tickfont=dict(color="#FFFFFF", size=11, family="Arial Black"))
        ),
        showlegend=True,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=30, b=30),
        height=450
    )

    with chart_col:
        st.plotly_chart(fig, use_container_width=True)

    with detail_col:
        stats_df = pd.DataFrame({"세부 항목": categories, "점수": values})
        st.dataframe(
            stats_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "점수": st.column_config.ProgressColumn("점수", min_value=0, max_value=200, format="%d")
            }
        )
else:
    st.warning("분석할 수 있는 종목 데이터를 가져오지 못했습니다. 사이드바 조건을 다시 선택해 주세요.")