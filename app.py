import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from tradingview_screener import Query, Column
import feedparser

st.set_page_config(page_title="FM Stock Scout Pro", layout="wide")

# 화이트/라이트 스타일
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

st.title("⚽ FM 정밀 스카우터 Pro: 펀더멘털 & 뉴스 촉매 통합")
st.caption("기업의 재무 포텐셜(CA/PA)과 최신 24시간 실시간 뉴스 호재(Catalyst)를 동시에 분석합니다.")

# 사이드바 설정 - 뉴스 호재 급등주 메뉴를 1순위로 추가
st.sidebar.header("📡 스카우트 전략 선택")
market_choice = st.sidebar.selectbox(
    "스카우트 전략 프리셋",
    [
        "🔥 오늘 실시간 뉴스 호재/급등 촉매주 (거래량 폭발+상승)",
        "🌟 알짜 원더키드 발굴 (매출성장 15%↑ / ROE 12%↑ / 고성장 가치주)",
        "🚀 테크/AI 슈퍼 성장주 (이익 폭발형)",
        "🛡️ 완성형 배당/우량 대형주",
        "트레이딩뷰 관심종목 파일(.txt) 직접 업로드"
    ]
)

max_scan_limit = st.sidebar.slider("스카우트 대상 수량", min_value=10, max_value=50, value=25, step=5)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 1. 트레이딩뷰 종목 수집 엔진
def fetch_tradingview_tickers(choice, limit):
    try:
        if choice == "🔥 오늘 실시간 뉴스 호재/급등 촉매주 (거래량 폭발+상승)":
            # 당일 거래량이 평소의 1.8배 이상 터지면서 주가가 상승 중인 뉴스 모멘텀 종목군
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'change', 'volume', 'average_volume_10d_calc', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 5.0)                       # 페니주 차단 ($5 이상)
                .where(Column('market_cap_basic') >= 500_000_000)   # 시총 5억 달러 이상
                .where(Column('change') >= 2.0)                     # 당일 주가 상승 중
                .where(Column('volume') > Column('average_volume_10d_calc') * 1.5) # 거래량 급증
                .order_by('volume', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return [t for t in df['name'].tolist() if not t.endswith(('P', 'M', 'N', 'WS'))]

        elif choice == "🌟 알짜 원더키드 발굴 (매출성장 15%↑ / ROE 12%↑ / 고성장 가치주)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'total_revenue_growth_fq', 'return_on_equity_fq', 'debt_to_equity_fq', 'market_cap_basic', 'type', 'exchange')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 10.0)
                .where(Column('market_cap_basic') >= 2_000_000_000)
                .where(Column('total_revenue_growth_fq') >= 15.0)
                .where(Column('return_on_equity_fq') >= 12.0)
                .where(Column('debt_to_equity_fq') <= 120.0)
                .order_by('total_revenue_growth_fq', ascending=False)
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
                .where(Column('earnings_per_share_diluted_growth_fq') >= 25.0)
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
        return ["NVDA", "TSLA", "PLTR", "AMD", "LLY", "AAPL", "MSFT"]

if "파일" in market_choice:
    uploaded_file = st.sidebar.file_uploader("관심종목 (.txt)", type=["txt"])
    if uploaded_file:
        raw_text = uploaded_file.read().decode("utf-8")
        raw_lines = [line.strip().split(":")[-1] for line in raw_text.splitlines() if line.strip()]
        ticker_list = [t for t in raw_lines if t.isalpha()]
    else:
        ticker_list = ["NVDA", "TSLA", "PLTR"]
else:
    ticker_list = fetch_tradingview_tickers(market_choice, max_scan_limit)

st.sidebar.info(f"스카우팅 분석 대상: **{len(ticker_list)}개 기업**")

# 2. 실시간 뉴스 호재/촉매 분석 함수
CATALYST_MAP = {
    "FDA 승인 / 바이오": ["fda approval", "fda approves", "cleared", "clinical trial"],
    "대형 수주 / 파트너십": ["partnership", "secures contract", "awarded", "deal signed", "agreement"],
    "실적 호재 / 가이던스 상향": ["raises guidance", "beats estimates", "record revenue", "strong earnings", "upgrade"],
    "인수합병 / M&A": ["acquisition", "acquired", "merger", "takeover"],
    "AI / 핵심 기술 채택": ["ai partnership", "nvidia partner", "patent granted", "breakthrough"]
}

def analyze_live_news(ticker):
    try:
        rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
        feed = feedparser.parse(rss_url)
        if not feed.entries:
            return {"score": 50, "catalysts": [], "headlines": ["최근 뉴스 없음"]}
        
        detected_catalysts = []
        headlines = []
        positive_words = ["surge", "jump", "growth", "profit", "gain", "bullish", "record", "beat", "buy"]
        
        pos_count = 0
        for entry in feed.entries[:6]:
            title = entry.title
            headlines.append(title)
            t_lower = title.lower()
            
            for cat, kws in CATALYST_MAP.items():
                for kw in kws:
                    if kw in t_lower and cat not in detected_catalysts:
                        detected_catalysts.append(cat)
                        
            for pw in positive_words:
                if pw in t_lower:
                    pos_count += 1
                    break

        news_power = clamp(50 + (len(detected_catalysts) * 20) + (pos_count * 8))
        return {"score": news_power, "catalysts": detected_catalysts, "headlines": headlines[:4]}
    except:
        return {"score": 50, "catalysts": [], "headlines": ["뉴스 수신 불가"]}

# 3. 정밀 펀더멘털 CA/PA 엔진
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
        target_price = min(raw_target, current_price * 1.8)
        
        roe = info.get("returnOnEquity", 0.0) or 0.0
        op_margin = info.get("operatingMargins", 0.0) or 0.0
        debt_equity = info.get("debtToEquity", 100.0) or 100.0
        rev_growth = info.get("revenueGrowth", 0.0) or 0.0
        earn_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg = info.get("pegRatio", 2.0) or 2.0
        
        stat_profit = clamp(((roe / 0.20) * 80 + (op_margin / 0.25) * 80) / 2 + 30)
        stat_stability = clamp(200 - (debt_equity * 0.7))
        stat_rev = clamp((rev_growth / 0.35) * 90 + 60)
        stat_earn = clamp((earn_growth / 0.35) * 90 + 60)
        stat_valuation = clamp((2.5 - min(peg, 2.5)) * 60 + 50)
        
        upside = (target_price - current_price) / current_price
        stat_upside = clamp((upside / 0.35) * 80 + 70)

        ca = clamp(stat_profit * 0.45 + stat_stability * 0.35 + stat_valuation * 0.20)
        growth_power = (stat_rev * 0.35) + (stat_earn * 0.40) + (stat_upside * 0.25)
        pa = clamp(ca * 0.45 + growth_power * 0.65)
        if pa < ca: pa = ca
        
        gap = pa - ca
        comp_growth = max(0.05, (rev_growth * 0.4) + (earn_growth * 0.6))
        
        if gap <= 5:
            reach_time_str = "현재 전성기 (Peak)"
            reach_phase = "만개 완료"
        else:
            months = int(((gap / 35.0) / (comp_growth + 0.15)) * 12)
            if months <= 8:
                reach_time_str = f"약 {max(3, months)}개월 (초고속 도달)"
                reach_phase = "🚀 폭발적 성장기"
            elif months <= 20:
                reach_time_str = f"약 {months}개월 (1년 내외)"
                reach_phase = "🌱 정규 만개기"
            else:
                reach_time_str = f"약 {months // 12}년+ (중기)"
                reach_phase = "⏳ 안정적 순항"

        if ca >= 130 and pa >= 175 and gap >= 20: verdict = "🌟 S급 원더키드"
        elif ca >= 140 and pa >= 165: verdict = "🛡️ 완성형 최우량주"
        elif gap >= 30 and ca >= 100: verdict = "💎 고성장 알짜주"
        else: verdict = "⚖️ 안정 성장형"

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
                "수익 창출력": stat_profit, "재무 안전성": stat_stability,
                "매출 성장성": stat_rev, "이익 성장성": stat_earn,
                "밸류 매력": stat_valuation, "상승 여력": stat_upside
            }
        }
    except:
        return None

# 실행 및 데이터 수집
if ticker_list:
    prog = st.progress(0, text="스카우트 데이터 분석 중...")
    reports = []
    total = len(ticker_list)
    for idx, t in enumerate(ticker_list):
        data = get_detailed_scout_data(t)
        if data:
            reports.append(data)
        prog.progress((idx + 1) / total, text=f"분석 중: {t} ({idx+1}/{total})")
    prog.empty()

    if reports:
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

        # 개별 기업 상세 조회
        st.subheader("🔍 개별 기업 정밀 리포트 & 실시간 뉴스 레이더")
        selected_ticker = st.selectbox(
            "분석할 기업 선택:",
            options=df_board["티커"].tolist(),
            format_func=lambda x: f"{x} - {df_board.loc[df_board['티커'] == x, '기업명'].values[0]}"
        )

        target = next(item for item in reports if item["티커"] == selected_ticker)
        news_data = analyze_live_news(selected_ticker)

        # 상단 요약 카드
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: st.metric("기업명 (티커)", target["기업명"], delta=target["티커"])
        with c2: st.metric("현재 능력치 (CA)", f"{target['CA (현재능력)']} / 200")
        with c3: st.metric("잠재 능력치 (PA)", f"{target['PA (잠재능력)']} / 200", delta=f"+{target['포텐 여유']} Poten")
        with c4: st.metric("뉴스 호재 파워", f"{news_data['score']} / 100", delta="실시간 수집")
        with c5: st.metric("도달 예상 시점", target["도달 예상 기간"], delta=target["성장 페이즈"])

        # 좌측: 육각형 레이더 차트 / 우측: 실시간 뉴스 호재 브리핑
        chart_col, news_col = st.columns([1, 1])

        with chart_col:
            st.markdown("##### 📊 FM 능력치 육각형")
            categories = list(target["stats"].keys())
            values = list(target["stats"].values())

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[target["PA (잠재능력)"]] * len(categories) + [target["PA (잠재능력)"]],
                theta=categories + [categories[0]],
                fill='toself', fillcolor='rgba(255, 179, 0, 0.08)',
                line=dict(color='#FFA000', width=1.5, dash='dash'), name='잠재 한계치 (PA)'
            ))
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill='toself', fillcolor='rgba(16, 185, 129, 0.35)',
                line=dict(color='#059669', width=2.5), name='현재 스탯'
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor='#ffffff',
                    radialaxis=dict(visible=True, range=[0, 200], tickvals=[50, 100, 150, 200], tickfont=dict(color="#718096", size=9), gridcolor="#e2e8f0"),
                    angularaxis=dict(tickfont=dict(color="#1e293b", size=10), gridcolor="#e2e8f0")
                ),
                paper_bgcolor='#ffffff',
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
                margin=dict(l=30, r=30, t=10, b=30), height=380
            )
            st.plotly_chart(fig, use_container_width=True)

        with news_col:
            st.markdown("##### 📰 실시간 뉴스 호재(Catalyst) 레이더")
            if news_data["catalysts"]:
                st.success(f"🔥 **포착된 핵심 호재:** {', '.join(news_data['catalysts'])}")
            else:
                st.info("ℹ️ 현재 감지된 특이 돌발 호재 없음 (일반 펀더멘털 흐름)")
            
            st.markdown("**최근 24시간 실시간 헤드라인:**")
            for hl in news_data["headlines"]:
                st.markdown(f"- 📄 {hl}")