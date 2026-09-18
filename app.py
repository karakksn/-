import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from tradingview_screener import Query, Column

# 페이지 기본 설정 (화이트/라이트 테마 친화적 구성)
st.set_page_config(page_title="FM Stock Scout Pro", layout="wide")

# CSS: 검은 사각형 배너를 세련된 화이트 카드로 교체
st.markdown(
    """
    <style>
    /* 전체 배경 */
    .stApp {
        background-color: #f8f9fa;
        color: #1a1a1a;
    }
    /* 메트릭 카드: 흰색 배경 + 부드러운 그림자 */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    }
    div[data-testid="stMetric"] label {
        color: #4a5568 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #111827 !important;
        font-weight: 800 !important;
    }
    /* 사이드바 스타일 */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("⚽ FM 스타일 주식회사 정밀 스카우터")
st.caption("기업의 현재 주가 밸류에이션, 성장 가속도, 포텐 만개 시점(도달 소요 기간)을 1~200 FM 시스템으로 정밀 추적합니다.")

# 사이드바 설정
st.sidebar.header("📡 스카우트 소스 & 필터")
market_choice = st.sidebar.selectbox(
    "스카우트 조건 선택",
    [
        "💎 미국 저평가 우량주 (소형주 포함 / 보통주)",
        "미국 시가총액 상위주",
        "미국 핵심 기술주(Tech)",
        "트레이딩뷰 관심종목 파일(.txt) 직접 업로드"
    ]
)

max_scan_limit = st.sidebar.slider("스카우트 검색 한도 (최대 종목 수)", min_value=10, max_value=200, value=40, step=10)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰 보통주 전용 수집 함수
def fetch_tradingview_tickers(choice, limit):
    try:
        if choice == "💎 미국 저평가 우량주 (소형주 포함 / 보통주)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'price_earnings_ttm', 'price_book_fq', 'debt_to_equity_fq', 'market_cap_basic', 'type', 'exchange')
                .where(Column('type') == 'stock') # 보통주 한정
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 2.0)
                .where(Column('market_cap_basic') >= 300_000_000)
                .where(Column('price_earnings_ttm') > 0)
                .where(Column('price_earnings_ttm') < 16)
                .where(Column('price_book_fq') < 2.2)
                .where(Column('debt_to_equity_fq') < 160)
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
                .where(Column('sector') == 'Technology')
                .order_by('market_cap_basic', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()

    except Exception as e:
        st.sidebar.error(f"트레이딩뷰 수신 오류: {e}")
        return ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META"]

# 티커 리스트 가져오기
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

st.sidebar.info(f"스카우트 대상 종목: **{len(ticker_list)}개**")

# 정밀 CA/PA 및 도달 기간 산정 엔진
@st.cache_data(ttl=3600)
def get_detailed_scout_data(ticker_symbol):
    try:
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        name = info.get("shortName", ticker_symbol) or ticker_symbol
        currency = info.get("currency", "USD")
        
        current_price = info.get("currentPrice", info.get("regularMarketPrice", 0)) or 0
        if current_price <= 0:
            return None
        
        target_price = info.get("targetMeanPrice", current_price) or current_price
        
        # 펀더멘털 데이터
        roe = info.get("returnOnEquity", 0.0) or 0.0
        op_margin = info.get("operatingMargins", 0.0) or 0.0
        debt_equity = info.get("debtToEquity", 100.0) or 100.0
        pe_ratio = info.get("trailingPE", info.get("forwardPE", 25.0)) or 25.0
        pb_ratio = info.get("priceToBook", 3.0) or 3.0
        rev_growth = info.get("revenueGrowth", 0.0) or 0.0
        earn_growth = info.get("earningsGrowth", 0.0) or 0.0
        peg = info.get("pegRatio", 2.0) or 2.0
        
        # 주가 모멘텀 (52주 고점 대비 주가 위치)
        high_52 = info.get("fiftyTwoWeekHigh", current_price) or current_price
        low_52 = info.get("fiftyTwoWeekLow", current_price) or current_price
        price_position = (current_price - low_52) / (high_52 - low_52) if high_52 > low_52 else 0.5

        # ----------------------------------------------------
        # 1. 섬세한 6대 스탯 산정 (1~200)
        # ----------------------------------------------------
        # (1) 수익성: ROE + 영업이익률
        stat_profit = clamp(((roe / 0.18) * 90 + (op_margin / 0.22) * 90) / 2 + 20)
        
        # (2) 재무 안정성: 부채비율 기준
        stat_stability = clamp(200 - (debt_equity * 0.75))
        
        # (3) 주가 가성비(현재 주가 대비 밸류에이션 매력도)
        # PER 12 이하, PBR 1.5 이하일 때 높은 점수
        score_pe = max(10, 180 - (pe_ratio * 4.5)) if pe_ratio > 0 else 40
        score_pb = max(10, 180 - (pb_ratio * 25.0)) if pb_ratio > 0 else 40
        stat_price_val = clamp((score_pe * 0.6) + (score_pb * 0.4))
        
        # (4) 복합 성장성: 매출 및 이익 증가율 결합
        comp_growth = (rev_growth * 0.4) + (earn_growth * 0.6)
        stat_growth = clamp((comp_growth / 0.25) * 80 + 80)
        
        # (5) 목표주가 상승 여력(Upside Gap)
        upside = (target_price - current_price) / current_price
        stat_upside = clamp((upside / 0.35) * 80 + 70)
        
        # (6) 주가 모멘텀 & 가격 방어력
        stat_momentum = clamp(price_position * 120 + 40)

        # ----------------------------------------------------
        # 2. CA (현재 가격 대비 실질 능력치)
        # ----------------------------------------------------
        # 기본 펀더멘털(60%) + 현재 주가 밸류에이션 매력도(25%) + 모멘텀(15%)
        ca = clamp(
            (stat_profit * 0.35 + stat_stability * 0.25) +
            (stat_price_val * 0.25) +
            (stat_momentum * 0.15)
        )

        # ----------------------------------------------------
        # 3. PA (이론적 최대 잠재 능력치)
        # ----------------------------------------------------
        # 미래 상승 여력과 성장 속도가 클수록 CA 위에 보너스 축적
        growth_bonus = (stat_growth * 0.45) + (stat_upside * 0.40) + ((2.5 - min(peg, 2.5)) * 25)
        pa = clamp(ca * 0.45 + growth_bonus * 0.65)
        if pa < ca:
            pa = ca

        gap = pa - ca

        # ----------------------------------------------------
        # 4. 잠재력 도달 예상 시점 (Time-to-PA) 산출식
        # ----------------------------------------------------
        # 연간 유효 성장 추진력 (%): 실적 성장률과 괴리율을 조합
        effective_annual_growth = max(0.05, (comp_growth * 0.6) + (max(0.0, upside) * 0.4))
        
        if gap <= 3:
            reach_time_str = "현재 정점 도달 (Peak)"
            reach_phase = "만개 완료"
        else:
            # 갭 1포인트 극복에 필요한 표준 도달 소수점 연수
            years_needed = (gap / 40.0) / (effective_annual_growth + 0.15)
            months_needed = int(years_needed * 12)
            
            if months_needed <= 6:
                reach_time_str = f"약 {max(3, months_needed)}개월 이내 (단기 급상승)"
                reach_phase = "🚀 초고속 폭발기"
            elif months_needed <= 18:
                reach_time_str = f"약 {months_needed}개월 (1년~1년 반)"
                reach_phase = "🌱 정규 전성기 진입기"
            elif months_needed <= 36:
                reach_time_str = f"약 {months_needed // 12}년 {months_needed % 12}개월 (중장기)"
                reach_phase = "⏳ 안정적 중장기 성장"
            else:
                reach_time_str = "3년 이상 (체질 개선 필요)"
                reach_phase = "🏗️ 장기 구조 개혁형"

        # 판정 등급
        if pa >= 180 and gap >= 25:
            verdict = "🌟 월드클래스 원더키드 (Elite Wonderkid)"
        elif pa >= 170:
            verdict = "🛡️ 완성형 엘리트 우량주 (Solid Elite)"
        elif gap >= 35:
            verdict = "💎 원석 발굴형 (High Risk Potential)"
        else:
            verdict = "⚖️ 피크 도달 / 안정 성장"

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

# 데이터 수집 실행
if ticker_list:
    progress = st.progress(0, text="스카우트 데이터 정밀 분석 중...")
    reports = []
    total = len(ticker_list)
    for idx, t in enumerate(ticker_list):
        data = get_detailed_scout_data(t)
        if data:
            reports.append(data)
        progress.progress((idx + 1) / total, text=f"분석 중: {t} ({idx+1}/{total})")
    progress.empty()

    if reports:
        df_board = pd.DataFrame(reports).sort_values(by="PA (잠재능력)", ascending=False).reset_index(drop=True)

        st.subheader(f"📋 스카우팅 보드 (총 {len(df_board)}개 종목 순위)")
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

        # ----------------------------------------------------
        # 개별 리포트 상세 영역 (화이트 디자인 적용)
        # ----------------------------------------------------
        st.subheader("🔍 개별 기업 정밀 스카우팅 리포트")
        selected_ticker = st.selectbox(
            "분석할 기업을 선택하세요:",
            options=df_board["티커"].tolist(),
            format_func=lambda x: f"{x} - {df_board.loc[df_board['티커'] == x, '기업명'].values[0]}"
        )

        target = next(item for item in reports if item["티커"] == selected_ticker)

        # 상단 카드 5개 (화이트 테마 배경)
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

        st.success(f"**스카우트 최종 판정:** {target['스카우트 판정']} | **진입 단계:** {target['성장 페이즈']}")

        chart_col, detail_col = st.columns([1.1, 0.9])
        categories = list(target["stats"].keys())
        values = list(target["stats"].values())

        # 레이더 차트 (배경을 완전한 화이트/투명으로 교체)
        fig = go.Figure()
        
        # 잠재 한계선 (점선 가이드)
        fig.add_trace(go.Scatterpolar(
            r=[target["PA (잠재능력)"]] * len(categories) + [target["PA (잠재능력)"]],
            theta=categories + [categories[0]],
            fill='toself',
            fillcolor='rgba(255, 179, 0, 0.08)',
            line=dict(color='#FFA000', width=1.5, dash='dash'),
            name='잠재 한계치 (PA)'
        ))
        
        # 현재 능력치 다각형
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
                bgcolor='#ffffff',  # 차트 내부 원형 배경: 완전한 흰색
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
            paper_bgcolor='#ffffff',  # 차트 외곽 전체 여백: 흰색
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