import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from tradingview_screener import Query, Column

st.set_page_config(page_title="FM Stock Scout Pro", layout="wide")

# 라이트/화이트 테마 친화적 스타일
st.markdown(
    """
    <style>
    .stApp {
        background-color: #f8f9fa;
        color: #1a1a1a;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
    }
    div[data-testid="stMetric"] label {
        color: #4a5568 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 800 !important;
    }
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ FM 스타일 주식회사 정밀 스카우터 Pro")
st.caption("페니주/착시 종목 필터링이 적용된 알고리즘으로 검증된 기업의 CA & PA를 추적합니다.")

st.sidebar.header("📡 스카우트 소스 & 필터")
market_choice = st.sidebar.selectbox(
    "스카우트 조건 선택",
    [
        "💎 검증된 미국 저평가 우량주 (주가 $5↑ / 시총 10억$↑)",
        "미국 시가총액 상위주",
        "미국 핵심 기술주(Tech)",
        "트레이딩뷰 관심종목 파일(.txt) 직접 업로드"
    ]
)

max_scan_limit = st.sidebar.slider("스카우트 검색 한도 (종목 수)", min_value=10, max_value=100, value=30, step=10)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰 쿼리: 페니주/장외주/동전주 원천 차단
def fetch_tradingview_tickers(choice, limit):
    try:
        if choice == "💎 검증된 미국 저평가 우량주 (주가 $5↑ / 시총 10억$↑)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'price_earnings_ttm', 'price_book_fq', 'debt_to_equity_fq', 'market_cap_basic', 'type', 'exchange')
                # 1. 보통주만 선별 (우선주, ETF 제외)
                .where(Column('type') == 'stock')
                # 2. 메이저 정규 거래소만
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                # 3. 페니주 차단: 주가 최소 5달러 이상
                .where(Column('close') >= 5.0)
                # 4. 시가총액 최소 10억 달러 (약 1조 3500억 원 이상, 안정적 중견기업 이상)
                .where(Column('market_cap_basic') >= 1_000_000_000)
                # 5. 건전한 흑자 밸류에이션
                .where(Column('price_earnings_ttm') > 0)
                .where(Column('price_earnings_ttm') < 18)
                .where(Column('price_book_fq') < 2.5)
                .where(Column('debt_to_equity_fq') < 150)
                .order_by('price_earnings_ttm', ascending=True)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

        elif choice == "미국 시가총액 상위주":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'market_cap_basic', 'type', 'exchange')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 5.0)
                .order_by('market_cap_basic', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

        elif choice == "미국 핵심 기술주(Tech)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'sector', 'type', 'exchange')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 5.0)
                .where(Column('sector') == 'Technology')
                .order_by('market_cap_basic', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

    except Exception as e:
        st.sidebar.error(f"트레이딩뷰 수신 오류: {e}")
        return ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]

if "파일" in market_choice:
    uploaded_file = st.sidebar.file_uploader("트레이딩뷰 관심종목 (.txt)", type=["txt"])
    if uploaded_file:
        raw_text = uploaded_file.read().decode("utf-8")
        raw_lines = [line.strip().split(":")[-1] for line in raw_text.splitlines() if line.strip()]
        ticker_list = [t for t in raw_lines if t.isalpha()]
    else:
        ticker_list = ["NVDA", "AAPL", "MSFT"]
else:
    ticker_list = fetch_tradingview_tickers(market_choice, max_scan_limit)

st.sidebar.info(f"선별된 정규 종목 수: **{len(ticker_list)}개**")

# 착시 방지 정밀 CA/PA 계산 엔진
@st.cache_data(ttl=3600)
def get_detailed_scout_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        name = info.get("shortName", ticker_symbol) or ticker_symbol
        currency = info.get("currency", "USD")
        
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        if current_price < 2.0:  # 2달러 미만 잡주는 최종 연산에서도 제외
            return None
        
        # 1. 목표주가 착시 보정 (애널리스트 커버리지 수 검증)
        num_analysts = info.get("numberOfAnalystOpinions", 0) or 0
        raw_target = info.get("targetMeanPrice", current_price) or current_price
        
        # 애널리스트가 너무 적거나(2명 이하) 목표가가 현재가의 2.5배를 넘는 극단값은 보수적 캡 적용
        if num_analysts < 3:
            target_price = min(raw_target, current_price * 1.3)  # 최대 30% 상승여력으로 제한
        else:
            target_price = min(raw_target, current_price * 2.0)  # 최대 100% 상승여력으로 캡

        # 펀더멘털 데이터 추출
        roe = info.get("returnOnEquity", 0.0) or 0.0
        op_margin = info.get("operatingMargins", 0.0) or 0.0
        debt_equity = info.get("debtToEquity", 100.0) or 100.0
        pe_ratio = info.get("trailingPE", info.get("forwardPE", 25.0)) or 25.0
        pb_ratio = info.get("priceToBook", 3.0) or 3.0
        rev_growth = info.get("revenueGrowth", 0.0) or 0.0
        earn_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg = info.get("pegRatio", 2.0) or 2.0
        
        # 52주 주가 위치
        high_52 = info.get("fiftyTwoWeekHigh", current_price) or current_price
        low_52 = info.get("fiftyTwoWeekLow", current_price) or current_price
        price_position = (current_price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0.5

        # ----------------------------------------------------
        # 2. 6대 세부 스탯 산정 (1~200)
        # ----------------------------------------------------
        # (1) 수익성 (적자면 대폭 감점)
        if roe <= 0 or op_margin <= 0:
            stat_profit = clamp(max(10, 40 + (roe * 100)))
        else:
            stat_profit = clamp(((roe / 0.18) * 85 + (op_margin / 0.20) * 85) / 2 + 30)

        # (2) 재무 안정성
        stat_stability = clamp(200 - (debt_equity * 0.8))

        # (3) 주가 밸류에이션 매력도
        score_pe = max(10, 180 - (pe_ratio * 4.5)) if pe_ratio > 0 else 30
        score_pb = max(10, 180 - (pb_ratio * 25.0)) if pb_ratio > 0 else 30
        stat_price_val = clamp((score_pe * 0.6) + (score_pb * 0.4))

        # (4) 복합 성장성 (성장률 극단값 클램핑)
        clean_earn_growth = max(-0.5, min(earn_growth, 0.8))
        clean_rev_growth = max(-0.5, min(rev_growth, 0.6))
        comp_growth = (clean_rev_growth * 0.4) + (clean_earn_growth * 0.6)
        stat_growth = clamp((comp_growth / 0.25) * 60 + 90)

        # (5) 목표가 괴리율 (상승 여력)
        upside = (target_price - current_price) / current_price
        clean_upside = max(-0.3, min(upside, 0.8))
        stat_upside = clamp((clean_upside / 0.35) * 60 + 80)

        # (6) 주가 모멘텀
        stat_momentum = clamp(price_position * 120 + 40)

        # ----------------------------------------------------
        # 3. CA (현재 가격 대비 실질 능력치)
        # ----------------------------------------------------
        ca = clamp(
            (stat_profit * 0.35 + stat_stability * 0.25) +
            (stat_price_val * 0.25) +
            (stat_momentum * 0.15)
        )

        # ----------------------------------------------------
        # 4. PA (잠재 능력치) 산출 & 착시 방지 패널티
        # ----------------------------------------------------
        growth_bonus = (stat_growth * 0.45) + (stat_upside * 0.40) + ((2.5 - min(peg, 2.5)) * 20)
        raw_pa = ca * 0.45 + growth_bonus * 0.65

        # [핵심 보완] CA가 75 미만인 부실/적자 기업은 포텐셜을 강제로 억제
        if ca < 75:
            pa = clamp(min(raw_pa, ca + 20))  # 부실주는 갭이 +20 이상 못 벌어지도록 차단
        else:
            pa = clamp(raw_pa)

        if pa < ca:
            pa = ca

        gap = pa - ca

        # ----------------------------------------------------
        # 5. 포텐 도달 기간 산정
        # ----------------------------------------------------
        effective_annual_growth = max(0.06, (comp_growth * 0.6) + (max(0.0, clean_upside) * 0.4))
        
        if ca < 75 or roe <= 0:
            reach_time_str = "도달 불투명 (적자/체질 부실)"
            reach_phase = "⚠️ 턴어라운드 우선"
        elif gap <= 4:
            reach_time_str = "현재 정점 (Peak)"
            reach_phase = "만개 완료"
        else:
            years_needed = (gap / 35.0) / (effective_annual_growth + 0.15)
            months_needed = int(years_needed * 12)
            if months_needed <= 6:
                reach_time_str = f"약 {max(3, months_needed)}개월 (단기 상승)"
                reach_phase = "🚀 실적 가속기"
            elif months_needed <= 18:
                reach_time_str = f"약 {months_needed}개월 (1년~1년 반)"
                reach_phase = "🌱 정규 전성기 진입"
            elif months_needed <= 36:
                reach_time_str = f"약 {months_needed // 12}년 {months_needed % 12}개월 (중장기)"
                reach_phase = "⏳ 안정적 우상향"
            else:
                reach_time_str = "3년 이상 소요"
                reach_phase = "🏗️ 장기 구조개혁"

        # 스카우트 등급 판정
        if ca < 75 or roe <= 0:
            verdict = "⚠️ 밸류트랩 경고 (적자/고위험)"
        elif pa >= 180 and gap >= 20:
            verdict = "🌟 월드클래스 원더키드 (Verified Wonderkid)"
        elif pa >= 170:
            verdict = "🛡️ 완성형 엘리트 우량주 (Solid Elite)"
        elif gap >= 25:
            verdict = "💎 알짜 성장 유망주 (Quality Growth)"
        else:
            verdict = "⚖️ 피크 도달 / 안정형 배당주"

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
                "수익성 (ROE/마진)": stat_profit,
                "재무건전성 (저부채)": stat_stability,
                "주가 가성비 (저PER/PBR)": stat_price_val,
                "복합 성장성 (매출/이익)": stat_growth,
                "목표가 상승여력": stat_upside,
                "가격 모멘텀": stat_momentum
            }
        }
    except Exception:
        return None

# 데이터 취합 및 출력
if ticker_list:
    progress = st.progress(0, text="스카우트 데이터 정밀 검증 중...")
    reports = []
    total = len(ticker_list)
    for idx, t in enumerate(ticker_list):
        data = get_detailed_scout_data(t)
        if data:
            reports.append(data)
        progress.progress((idx + 1) / total, text=f"검증 진행 중: {t} ({idx+1}/{total})")
    progress.empty()

    if reports:
        df_board = pd.DataFrame(reports).sort_values(by="PA (잠재능력)", ascending=False).reset_index(drop=True)

        st.subheader(f"📋 검증된 스카우팅 보드 (총 {len(df_board)}개 종목)")
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
        st.subheader("🔍 개별 기업 정밀 스카우팅 리포트")
        selected_ticker = st.selectbox(
            "분석할 기업을 선택하세요:",
            options=df_board["티커"].tolist(),
            format_func=lambda x: f"{x} - {df_board.loc[df_board['티커'] == x, '기업명'].values[0]}"
        )

        target = next(item for item in reports if item["티커"] == selected_ticker)

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.metric("종목명 (티커)", target["기업명"], delta=target["티커"])
        with c2:
            st.metric("현재 능력치 (CA)", f"{target['CA (현재능력)']} / 200")
        with c3:
            st.metric("잠재 능력치 (PA)", f"{target['PA (잠재능력)']} / 200", delta=f"+{target['포텐 여유']} Poten")
        with c4:
            st.metric("현재가 (목표가)", target["현재가"], delta=f"목표: {target['목표가']}")
        with c5:
            st.metric("포텐 도달 예상 시점", target["도달 예상 기간"], delta=target["성장 페이즈"])

        if "경고" in target["스카우트 판정"]:
            st.error(f"**스카우트 주의:** {target['스카우트 판정']} — 재무 건전성 및 실적이 부실하여 착시 가능성이 있습니다.")
        else:
            st.success(f"**스카우트 최종 판정:** {target['스카우트 판정']} | **진입 단계:** {target['성장 페이즈']}")

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
                radialaxis=dict(
                    visible=True,
                    range=[0, 200],
                    tickvals=[50, 100, 150, 200],
                    tickfont=dict(color="#718096", size=10),
                    gridcolor="#e2e8f0",
                    linecolor="#cbd5e1"
                ),
                angularaxis=dict(
                    tickfont=dict(color="#1e293b", size=11, family="Pretendard, Arial, sans-serif"),
                    gridcolor="#e2e8f0",
                    linecolor="#cbd5e1"
                )
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
                column_config={
                    "수치": st.column_config.ProgressColumn("점수", min_value=0, max_value=200, format="%d")
                }
            )
    else:
        st.warning("분석 가능한 종목 데이터를 불러오지 못했습니다.")