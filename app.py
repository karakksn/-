import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from tradingview_screener import Query, Column

st.set_page_config(page_title="FM Stock Scout Pro - GARP Wonderkid", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #f8f9fa; color: #1a1a1a; }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05) !important;
    }
    div[data-testid="stMetric"] label { color: #4a5568 !important; font-weight: 600 !important; }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] { color: #111827 !important; font-weight: 800 !important; }
    section[data-testid="stSidebar"] { background-color: #ffffff !important; border-right: 1px solid #e2e8f0; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ FM 정밀 스카우터: 고포텐 알짜 유망주(GARP) 엔진")
st.caption("실적이 고속 성장하면서도 거품이 끼지 않은 '원더키드(GARP)' 기업을 집중 발굴합니다.")

# 사이드바
st.sidebar.header("📡 스카우트 전략 선택")
market_choice = st.sidebar.selectbox(
    "스카우트 전략 프리셋",
    [
        "🌟 알짜 원더키드 발굴 (매출성장 15%↑ / ROE 12%↑ / 고성장 가치주)",
        "🚀 테크/AI 슈퍼 성장주 (이익 폭발형)",
        "🛡️ 완성형 배당/우량 대형주",
        "트레이딩뷰 관심종목 파일(.txt) 업로드"
    ]
)

max_scan_limit = st.sidebar.slider("스카우트 대상 수량", min_value=15, max_value=60, value=30, step=5)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰 고포텐 알짜 종목 필터 함수
def fetch_tradingview_tickers(choice, limit):
    try:
        if choice == "🌟 알짜 원더키드 발굴 (매출성장 15%↑ / ROE 12%↑ / 고성장 가치주)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'total_revenue_growth_fq', 'return_on_equity_fq', 'debt_to_equity_fq', 'market_cap_basic', 'type', 'exchange')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 10.0)                     # 주가 $10 이상 (완전한 정규주)
                .where(Column('market_cap_basic') >= 2_000_000_000) # 시총 20억 달러(2.7조 원) 이상 탄탄한 기업
                .where(Column('total_revenue_growth_fq') >= 15.0)   # 매출성장률 최소 +15% 이상
                .where(Column('return_on_equity_fq') >= 12.0)       # ROE 최소 12% 이상 (고수익성)
                .where(Column('debt_to_equity_fq') <= 120.0)        # 건전한 부채비율
                .order_by('total_revenue_growth_fq', ascending=False) # 성장률 가장 가파른 순
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return [t for t in df['name'].tolist() if not t.endswith(('P', 'M', 'N', 'WS'))]

        elif choice == "🚀 테크/AI 슈퍼 성장주 (이익 폭발형)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'earnings_per_share_diluted_growth_fq', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 15.0)
                .where(Column('market_cap_basic') >= 5_000_000_000)
                .where(Column('earnings_per_share_diluted_growth_fq') >= 25.0) # EPS 성장 25% 이상
                .order_by('earnings_per_share_diluted_growth_fq', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

        elif choice == "🛡️ 완성형 배당/우량 대형주":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 20.0)
                .order_by('market_cap_basic', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

    except Exception as e:
        st.sidebar.error(f"트레이딩뷰 통신 오류: {e}")
        return ["NVDA", "AVGO", "LLY", "TSM", "AAPL", "MSFT", "AMZN", "META"]

if "파일" in market_choice:
    uploaded_file = st.sidebar.file_uploader("관심종목 (.txt)", type=["txt"])
    if uploaded_file:
        raw_text = uploaded_file.read().decode("utf-8")
        raw_lines = [line.strip().split(":")[-1] for line in raw_text.splitlines() if line.strip()]
        ticker_list = [t for t in raw_lines if t.isalpha()]
    else:
        ticker_list = ["NVDA", "AVGO", "LLY"]
else:
    ticker_list = fetch_tradingview_tickers(market_choice, max_scan_limit)

st.sidebar.info(f"스카우팅 분석 대상: **{len(ticker_list)}개 기업**")

# CA/PA 계산 엔진 (GARP 중심)
@st.cache_data(ttl=3600)
def get_detailed_scout_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        name = info.get("shortName", ticker_symbol) or ticker_symbol
        currency = info.get("currency", "USD")
        
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        if current_price < 5.0:
            return None
            
        raw_target = info.get("targetMeanPrice", current_price) or current_price
        target_price = min(raw_target, current_price * 1.8) # 비현실적 목표주가는 최대 80% 상승으로 캡
        
        roe = info.get("returnOnEquity", 0.0) or 0.0
        op_margin = info.get("operatingMargins", 0.0) or 0.0
        debt_equity = info.get("debtToEquity", 100.0) or 100.0
        pe_ratio = info.get("trailingPE", info.get("forwardPE", 28.0)) or 28.0
        rev_growth = info.get("revenueGrowth", 0.0) or 0.0
        earn_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg = info.get("pegRatio", 2.0) or 2.0
        
        # 1. 6대 핵심 스탯 산출 (1~200)
        # (1) 수익 창출력 (ROE + 영업이익률)
        stat_profit = clamp(((roe / 0.20) * 80 + (op_margin / 0.25) * 80) / 2 + 30)
        
        # (2) 재무 안전성
        stat_stability = clamp(200 - (debt_equity * 0.7))
        
        # (3) 매출 폭발력
        stat_rev = clamp((rev_growth / 0.35) * 90 + 60)
        
        # (4) 이익 성장 가속도
        stat_earn = clamp((earn_growth / 0.35) * 90 + 60)
        
        # (5) 밸류에이션 매력도 (PEG 1.5 이하 우대)
        stat_valuation = clamp((2.5 - min(peg, 2.5)) * 60 + 50)
        
        # (6) 목표주가 상승 여력
        upside = (target_price - current_price) / current_price
        stat_upside = clamp((upside / 0.35) * 80 + 70)

        # 2. CA: 현재 이익 창출력과 재무 체력 (기초 체력)
        ca = clamp(stat_profit * 0.45 + stat_stability * 0.35 + stat_valuation * 0.20)

        # 3. PA: 현재 체력에 고성장 동력 + 월가 상승 여력 결합
        growth_power = (stat_rev * 0.35) + (stat_earn * 0.40) + (stat_upside * 0.25)
        pa = clamp(ca * 0.45 + growth_power * 0.65)
        if pa < ca:
            pa = ca
        
        gap = pa - ca

        # 4. 포텐 도달 기간 산정
        comp_growth = max(0.05, (rev_growth * 0.4) + (earn_growth * 0.6))
        if gap <= 5:
            reach_time_str = "현재 전성기 (Peak)"
            reach_phase = "만개 완료"
        else:
            years = (gap / 35.0) / (comp_growth + 0.15)
            months = int(years * 12)
            if months <= 8:
                reach_time_str = f"약 {max(3, months)}개월 (초고속 도달)"
                reach_phase = "🚀 폭발적 성장기"
            elif months <= 20:
                reach_time_str = f"약 {months}개월 (1년 내외)"
                reach_phase = "🌱 정규 만개기"
            else:
                reach_time_str = f"약 {months // 12}년+ (중기)"
                reach_phase = "⏳ 안정적 순항"

        # 판정 등급 부여
        if ca >= 130 and pa >= 175 and gap >= 20:
            verdict = "🌟 S급 원더키드 (Elite Wonderkid)"
        elif ca >= 140 and pa >= 165:
            verdict = "🛡️ 완성형 최우량주 (Solid Elite)"
        elif gap >= 30 and ca >= 100:
            verdict = "💎 고성장 알짜주 (High Growth)"
        else:
            verdict = "⚖️ 안정 성장형 (Steady)"

        return {
            "티커": ticker_symbol,
            "기업명": name,
            "현재가": f"{current_price:,.2f} {currency}",
            "목표가": f"{target_price:,.2f} {currency}",
            "CA (현재능력)": ca,
            "PA (잠재능력)": pa,
            "포텐 여유": gap,
            "도달 예상 기간": reach_time_str,
            "성장 페이즈": reach_phase,
            "스카우트 판정": verdict,
            "stats": {
                "수익 창출력": stat_profit,
                "재무 안전성": stat_stability,
                "매출 성장성": stat_rev,
                "이익 성장성": stat_earn,
                "밸류 매력(PEG)": stat_valuation,
                "상승 여력": stat_upside
            }
        }
    except Exception:
        return None

# 데이터 수집 및 렌더링
if ticker_list:
    progress = st.progress(0, text="알짜 유망주 스카우팅 분석 중...")
    reports = []
    total = len(ticker_list)
    for idx, t in enumerate(ticker_list):
        data = get_detailed_scout_data(t)
        if data:
            reports.append(data)
        progress.progress((idx + 1) / total, text=f"검증 중: {t} ({idx+1}/{total})")
    progress.empty()

    if reports:
        # PA 순 정렬
        df_board = pd.DataFrame(reports).sort_values(by="PA (잠재능력)", ascending=False).reset_index(drop=True)

        st.subheader(f"📋 고포텐 알짜 스카우팅 보드 (총 {len(df_board)}개)")
        st.dataframe(
            df_board[["티커", "기업명", "현재가", "CA (현재능력)", "PA (잠재능력)", "포텐 여유", "도달 예상 기간", "스카우트 판정"]],
            use_container_width=True,
            column_config={
                "CA (현재능력)": st.column_config.ProgressColumn("CA", min_value=0, max_value=200, format="%d"),
                "PA (잠재능력)": st.column_config.ProgressColumn("PA", min_value=0, max_value=200, format="%d"),
                "포텐 여유": st.column_config.NumberColumn("+포텐", format="+%d"),
            }
        )

        st.divider()

        # 개별 리포트
        st.subheader("🔍 개별 기업 정밀 육각형 리포트")
        selected_ticker = st.selectbox(
            "분석할 기업 선택:",
            options=df_board["티커"].tolist(),
            format_func=lambda x: f"{x} - {df_board.loc[df_board['티커'] == x, '기업명'].values[0]}"
        )

        target = next(item for item in reports if item["티커"] == selected_ticker)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("기업명 (티커)", target["기업명"], delta=target["티커"])
        with c2: st.metric("현재 능력치 (CA)", f"{target['CA (현재능력)']} / 200")
        with c3: st.metric("잠재 능력치 (PA)", f"{target['PA (잠재능력)']} / 200", delta=f"+{target['포텐 여유']} Poten")
        with c4: st.metric("현재가 (목표가)", target["현재가"], delta=f"목표: {target['목표가']}")
        with c5: st.metric("도달 예상 시점", target["도달 예상 기간"], delta=target["성장 페이즈"])

        st.success(f"**스카우트 판정:** {target['스카우트 판정']} | **페이즈:** {target['성장 페이즈']}")

        chart_col, detail_col = st.columns([1.1, 0.9])
        categories = list(target["stats"].keys())
        values = list(target["stats"].values())

        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=[target["PA (잠재능력)"]] * len(categories) + [target["PA (잠재능력)"]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(255, 179, 0, 0.08)',
            line=dict(color='#FFA000', width=1.5, dash='dash'),
            name='잠재 한계치 (PA)'
        ))
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(16, 185, 129, 0.35)',
            line=dict(color='#059669', width=2.5),
            name='현재 세부 스탯'
        ))

        fig.update_layout(
            polar=dict(
                bgcolor='#ffffff',
                radialaxis=dict(visible=True, range=[0, 200], tickvals=[50, 100, 150, 200], tickfont=dict(color="#718096", size=10), gridcolor="#e2e8f0"),
                angularaxis=dict(tickfont=dict(color="#1e293b", size=11), gridcolor="#e2e8f0")
            ),
            paper_bgcolor='#ffffff',
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
            margin=dict(l=40, r=40, t=20, b=40),
            height=430
        )

        with chart_col:
            st.plotly_chart(fig, use_container_width=True)

        with detail_col:
            st.markdown("##### 📊 6대 세부 포지션 스탯 (0~200)")
            stats_df = pd.DataFrame({"스탯 항목": categories, "수치": values})
            st.dataframe(
                stats_df,
                hide_index=True,
                use_container_width=True,
                column_config={"수치": st.column_config.ProgressColumn("점수", min_value=0, max_value=200, format="%d")}
            )