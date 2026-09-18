import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# 페이지 기본 설정
st.set_page_config(page_title="FM Stock Scout Dashboard", layout="wide")

# 다크 모드 스타일 커스텀
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
st.caption("기업의 재무/성장성 데이터를 FM 에디터의 CA(현재 능력치) & PA(잠재 능력치)로 시각화합니다.")

# 사이드바 티커 입력창
st.sidebar.header("🔍 스카우트 대상 검색")
ticker_input = st.sidebar.text_input(
    "티커 입력 (예: NVDA, AAPL, 005930.KS)", 
    value="NVDA"
).upper().strip()

def clamp(val, min_val=1, max_val=200):
    """값을 FM 스케일(1~200) 범위로 제한"""
    return int(max(min_val, min(val, max_val)))

@st.cache_data(ttl=3600)
def get_stock_scout_data(ticker_symbol):
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    name = info.get("shortName", ticker_symbol)
    currency = info.get("currency", "USD")
    current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
    target_price = info.get("targetMeanPrice", current_price) or current_price
    
    # 기본 재무 및 성장 지표 추출
    roe = info.get("returnOnEquity", 0.0) or 0.0
    operating_margins = info.get("operatingMargins", 0.0) or 0.0
    debt_to_equity = info.get("debtToEquity", 100.0) or 100.0
    revenue_growth = info.get("revenueGrowth", 0.0) or 0.0
    earnings_growth = info.get("earningsGrowth", 0.0) or 0.0
    peg_ratio = info.get("pegRatio", 2.0) or 2.0
    
    # 6대 세부 스탯 산출 (1~200점 스케일)
    stat_profitability = clamp(((roe / 0.20) * 100 + (operating_margins / 0.25) * 100) / 2)
    stat_stability = clamp(max(10, 200 - debt_to_equity))
    stat_rev_growth = clamp((revenue_growth / 0.30) * 120 + 40)
    stat_earn_growth = clamp((earnings_growth / 0.30) * 120 + 40)
    stat_valuation = clamp((2.5 - min(peg_ratio, 2.5)) * 80)
    
    upside = (target_price - current_price) / current_price if current_price > 0 else 0
    stat_upside = clamp((upside / 0.40) * 120 + 50)
    
    # CA (현재 펀더멘털) 및 PA (성장 잠재력 가산치 반영)
    ca = clamp(stat_profitability * 0.45 + stat_stability * 0.35 + stat_rev_growth * 0.2)
    potential_bonus = (stat_earn_growth * 0.35) + (stat_upside * 0.4) + (stat_valuation * 0.25)
    pa = clamp(ca * 0.5 + potential_bonus * 0.7)
    
    # FM 원칙: PA는 CA보다 낮아지지 않음
    if pa < ca:
        pa = ca

    gap = pa - ca
    if pa >= 180 and gap >= 25:
        verdict = "🌟 월드클래스 원더키드 (High Growth Wonderkid)"
    elif pa >= 170:
        verdict = "🛡️ 완성형 엘리트 대형주 (Solid Elite)"
    elif gap >= 35:
        verdict = "💎 포텐 만개 대기중 (High Risk High Return)"
    else:
        verdict = "⚖️ 피크 도달/성장 정체 (Peak Reached)"
        
    stats_dict = {
        "수익성 (ROE/마진)": stat_profitability,
        "재무건전성 (저부채)": stat_stability,
        "매출 성장성": stat_rev_growth,
        "이익 성장성": stat_earn_growth,
        "목표가 괴리율 (상승여력)": stat_upside,
        "밸류에이션 매력 (PEG)": stat_valuation,
    }
    
    return {
        "name": name,
        "ticker": ticker_symbol,
        "price": f"{current_price:,.2f} {currency}",
        "target_price": f"{target_price:,.2f} {currency}",
        "ca": ca,
        "pa": pa,
        "gap": gap,
        "verdict": verdict,
        "stats": stats_dict
    }

# 실행 및 화면 출력
try:
    with st.spinner(f"'{ticker_input}' 스카우팅 데이터 불러오는 중..."):
        data = get_stock_scout_data(ticker_input)
    
    # 상단 요약 배너
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(label="기업명 (종목코드)", value=f"{data['name']}", delta=data['ticker'])
    with col2:
        st.metric(label="현재 능력치 (CA)", value=f"{data['ca']} / 200")
    with col3:
        st.metric(label="잠재 능력치 (PA)", value=f"{data['pa']} / 200", delta=f"+{data['gap']} Poten")
    with col4:
        st.metric(label="현재가 (목표가)", value=data['price'], delta=f"목표: {data['target_price']}")

    st.info(f"**스카우트 총평:** {data['verdict']}")
    st.divider()

    # 육각형 레이더 차트 및 세부 테이블
    chart_col, detail_col = st.columns([1.2, 0.8])

    categories = list(data["stats"].keys())
    values = list(data["stats"].values())

    fig = go.Figure()

    # 잠재 한계선 (PA 외곽선)
    fig.add_trace(go.Scatterpolar(
        r=[data["pa"]] * len(categories) + [data["pa"]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(255, 165, 0, 0.08)',
        line=dict(color='rgba(255, 165, 0, 0.4)', dash='dash'),
        name='잠재 한계치 (PA Bound)'
    ))

    # 현재 능력치 다각형
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
            radialaxis=dict(
                visible=True,
                range=[0, 200],
                tickvals=[50, 100, 150, 200],
                tickfont=dict(color="#888888", size=9)
            ),
            angularaxis=dict(
                tickfont=dict(color="#FFFFFF", size=11, family="Arial Black")
            )
        ),
        showlegend=True,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=30, b=30),
        height=480
    )

    with chart_col:
        st.subheader("📊 FM 능력치 육각형 (Radar Chart)")
        st.plotly_chart(fig, use_container_width=True)

    with detail_col:
        st.subheader("📋 세부 포지션 스탯 (0~200)")
        stats_df = pd.DataFrame({
            "스탯 항목": categories,
            "수치": values
        })
        st.dataframe(
            stats_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "수치": st.column_config.ProgressColumn(
                    "능력치 점수",
                    min_value=0,
                    max_value=200,
                    format="%d"
                )
            }
        )

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.warning("미국 주식(NVDA, AAPL 등) 또는 한국 주식(005930.KS, 035420.KS 등)의 올바른 티커인지 확인해 주세요.")