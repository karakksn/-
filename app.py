import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from tradingview_screener import Query, Column

st.set_page_config(page_title="FM Stock Scout - TradingView 연동", layout="wide")

st.markdown(
    """
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #1e222d; padding: 15px; border-radius: 10px; border: 1px solid #2e3548; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ FM 스타일 주식회사 포텐셜 스카우터")
st.caption("트레이딩뷰(TradingView) 실시간 스크리너에서 종목을 땡겨와 CA & PA를 분석합니다.")

# 사이드바: 트레이딩뷰 필터 선택
st.sidebar.header("📡 트레이딩뷰 소스 선택")
market_choice = st.sidebar.selectbox(
    "가져올 시장 / 조건 선택",
    [
        "미국 시가총액 Top 20 (S&P/나스닥)",
        "미국 기술주(Tech) 대형주 15선",
        "트레이딩뷰 관심종목 파일(.txt) 직접 업로드"
    ]
)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰에서 티커 긁어오기 함수
def fetch_tradingview_tickers(choice):
    tickers = []
    try:
        if choice == "미국 시가총액 Top 20 (S&P/나스닥)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'market_cap_basic')
                .order_by('market_cap_basic', ascending=False)
                .limit(20)
            )
            df = q.get_scanner_data()[1]
            tickers = df['name'].tolist()

        elif choice == "미국 기술주(Tech) 대형주 15선":
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
        st.sidebar.error(f"트레이딩뷰 데이터 수신 중 오류: {e}")
        tickers = ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]
    
    return tickers

# 티커 리스트 확보
if "파일" in market_choice:
    uploaded_file = st.sidebar.file_uploader("트레이딩뷰에서 내보낸 txt 파일", type=["txt"])
    if uploaded_file:
        raw_text = uploaded_file.read().decode("utf-8")
        # 트레이딩뷰 관심목록 포맷 (예: NASDAQ:AAPL, NYSE:TSLA 등) 처리
        raw_lines = [line.strip().split(":")[-1] for line in raw_text.splitlines() if line.strip()]
        ticker_list = [t for t in raw_lines if t.isalpha()]
    else:
        ticker_list = ["NVDA", "AAPL", "MSFT"]
else:
    ticker_list = fetch_tradingview_tickers(market_choice)

st.sidebar.write(f"가져온 종목 수: **{len(ticker_list)}개**")

@st.cache_data(ttl=3600)
def get_single_scout_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        name = info.get("shortName", ticker_symbol) or ticker_symbol
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        target_price = info.get("targetMeanPrice", current_price) or current_price
        currency = info.get("currency", "USD")
        
        roe = info.get("returnOnEquity", 0.0) or 0.0
        operating_margins = info.get("operatingMargins", 0.0) or 0.0
        debt_to_equity = info.get("debtToEquity", 100.0) or 100.0
        revenue_growth = info.get("revenueGrowth", 0.0) or 0.0
        earnings_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg_ratio = info.get("pegRatio", 2.0) or 2.0
        
        stat_profitability = clamp(((roe / 0.20) * 100 + (operating_margins / 0.25) * 100) / 2)
        stat_stability = clamp(max(10, 200 - debt_to_equity))
        stat_rev_growth = clamp((revenue_growth / 0.30) * 120 + 40)
        stat_earn_growth = clamp((earnings_growth / 0.30) * 120 + 40)
        stat_valuation = clamp((2.5 - min(peg_ratio, 2.5)) * 80)
        
        upside = (target_price - current_price) / current_price if current_price > 0 else 0
        stat_upside = clamp((upside / 0.40) * 120 + 50)
        
        ca = clamp(stat_profitability * 0.45 + stat_stability * 0.35 + stat_rev_growth * 0.2)
        potential_bonus = (stat_earn_growth * 0.35) + (stat_upside * 0.4) + (stat_valuation * 0.25)
        pa = clamp(ca * 0.5 + potential_bonus * 0.7)
        if pa < ca: pa = ca

        gap = pa - ca
        if pa >= 180 and gap >= 25: verdict = "🌟 원더키드 유망주"
        elif pa >= 170: verdict = "🛡️ 엘리트 우량주"
        elif gap >= 35: verdict = "💎 하이리스크 포텐형"
        else: verdict = "⚖️ 피크 도달"
            
        return {
            "티커": ticker_symbol,
            "기업명": name,
            "현재가": f"{current_price:,.2f} {currency}",
            "목표가": f"{target_price:,.2f} {currency}",
            "CA": ca,
            "PA": pa,
            "포텐 여유": gap,
            "스카우트 판정": verdict,
            "stats": {
                "수익성": stat_profitability, "안정성": stat_stability,
                "매출성장": stat_rev_growth, "이익성장": stat_earn_growth,
                "상승여력": stat_upside, "밸류에이션": stat_valuation
            }
        }
    except:
        return None

# 데이터 취합 및 출력
with st.spinner("트레이딩뷰 종목 수신 및 스카우팅 분석 중..."):
    reports = [res for t in ticker_list if (res := get_single_scout_data(t))]

if reports:
    df = pd.DataFrame(reports).sort_values(by="PA", ascending=False).reset_index(drop=True)
    
    st.subheader(f"📋 트레이딩뷰 연동 랭킹 ({market_choice})")
    st.dataframe(
        df[["티커", "기업명", "현재가", "CA", "PA", "포텐 여유", "스카우트 판정"]],
        use_container_width=True,
        column_config={
            "CA": st.column_config.ProgressColumn("CA (현재능력)", min_value=0, max_value=200, format="%d"),
            "PA": st.column_config.ProgressColumn("PA (잠재능력)", min_value=0, max_value=200, format="%d"),
            "포텐 여유": st.column_config.NumberColumn("+포텐", format="+%d"),
        }
    )
    
    st.divider()
    
    # 세부 육각형 차트
    selected_ticker = st.selectbox("상세 능력치를 볼 종목 선택:", df["티커"].tolist())
    target = next(r for r in reports if r["티커"] == selected_ticker)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("선택 기업", target["기업명"], delta=target["티커"])
    c2.metric("CA (현재능력)", f"{target['CA']} / 200")
    c3.metric("PA (잠재능력)", f"{target['PA']} / 200", delta=f"+{target['포텐 여유']}")
    c4.metric("판정", target["스카우트 판정"])
    
    cats = list(target["stats"].keys())
    vals = list(target["stats"].values())
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(r=[target["PA"]]*len(cats)+[target["PA"]], theta=cats+[cats[0]], fill='toself', fillcolor='rgba(255,165,0,0.1)', line=dict(color='orange', dash='dash'), name='PA 한계선'))
    fig.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=cats+[cats[0]], fill='toself', fillcolor='rgba(0,230,118,0.3)', line=dict(color='#00E676'), name='현재 스탯'))
    fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 200])), template="plotly_dark", height=420)
    st.plotly_chart(fig, use_container_width=True)