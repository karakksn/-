import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from tradingview_screener import Query, Column
import feedparser
from datetime import datetime, timezone, timedelta
import re

st.set_page_config(page_title="Market Catalyst Pro - 실시간 호재 레이더", layout="wide")

# 직관적인 카드 및 툴팁 CSS
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    /* 뉴스 카드 메인 스타일 */
    .catalyst-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    .catalyst-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 8px 12px -2px rgba(59, 130, 246, 0.12);
    }
    
    /* 뱃지 스타일 */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        font-size: 12px;
        font-weight: 700;
        border-radius: 6px;
        margin-right: 6px;
    }
    .badge-ticker {
        background-color: #1e293b;
        color: #ffffff;
        font-size: 14px;
        cursor: pointer;
        position: relative;
    }
    .badge-cat { background-color: #dbeafe; color: #1d4ed8; }
    .badge-time { background-color: #fef3c7; color: #b45309; }
    .badge-effect { background-color: #dcfce7; color: #15803d; }
    
    /* 호버 툴팁 스타일 */
    .tooltip-box {
        position: relative;
        display: inline-block;
        cursor: pointer;
    }
    .tooltip-box .tooltip-text {
        visibility: hidden;
        width: 240px;
        background-color: #0f172a;
        color: #ffffff;
        text-align: left;
        border-radius: 8px;
        padding: 10px 12px;
        position: absolute;
        z-index: 50;
        bottom: 125%;
        left: 50%;
        transform: translateX(-50%);
        opacity: 0;
        transition: opacity 0.25s;
        font-size: 12px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        line-height: 1.5;
    }
    .tooltip-box .tooltip-text::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #0f172a transparent transparent transparent;
    }
    .tooltip-box:hover .tooltip-text {
        visibility: visible;
        opacity: 1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 오늘의 실시간 호재 촉매 레이더")
st.caption("오늘 시장에서 즉시 주시해야 할 핵심 종목과 호재 내용, 적용 시점을 한눈에 확인하세요. (종목에 마우스를 올리면 잠재력이 표시됩니다)")

st.sidebar.header("📡 스카우트 설정")
market_choice = st.sidebar.selectbox(
    "스카우트 전략 프리셋",
    [
        "🔥 오늘 실시간 뉴스 호재/급등 촉매주",
        "🌟 알짜 원더키드 발굴 (고성장 가치주)",
        "🚀 테크/AI 슈퍼 성장주 (이익 폭발형)",
        "🛡️ 완성형 우량 대형주"
    ]
)
scan_limit = st.sidebar.slider("스캔 종목 수", min_value=10, max_value=30, value=15, step=5)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰 실시간 티커 추출
def fetch_tradingview_tickers(choice, limit):
    try:
        if choice == "🔥 오늘 실시간 뉴스 호재/급등 촉매주":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'change', 'volume', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('close') >= 2.0)
                .where(Column('market_cap_basic') >= 200_000_000)
                .where(Column('change') >= 1.0)
                .order_by('volume', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return [t for t in df['name'].tolist() if not t.endswith(('P', 'M', 'N', 'WS'))]
        elif choice == "🌟 알짜 원더키드 발굴 (고성장 가치주)":
            q = (
                Query()
                .set_markets('america')
                .select('name', 'close', 'total_revenue_growth_fq', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .where(Column('total_revenue_growth_fq') >= 15.0)
                .order_by('total_revenue_growth_fq', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()
        else:
            q = (
                Query()
                .set_markets('america')
                .select('name', 'market_cap_basic')
                .where(Column('type') == 'stock')
                .where(Column('exchange').isin(['NASDAQ', 'NYSE']))
                .order_by('market_cap_basic', ascending=False)
                .limit(limit)
            )
            df = q.get_scanner_data()[1]
            return df['name'].tolist()
    except Exception:
        return ["NVDA", "TSLA", "PLTR", "AMD", "LLY", "AAPL", "MSFT"]

ticker_list = fetch_tradingview_tickers(market_choice, scan_limit)

# 펀더멘털 및 CA/PA 연산 (간소화)
@st.cache_data(ttl=1800)
def get_stock_profile(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
        cur_p = getattr(info, 'last_price', None) or 10.0
        full_info = stock.info
        name = full_info.get("shortName", ticker) or ticker
        
        roe = full_info.get("returnOnEquity", 0.12) or 0.12
        op_margin = full_info.get("operatingMargins", 0.15) or 0.15
        rev_growth = full_info.get("revenueGrowth", 0.10) or 0.10
        earn_growth = full_info.get("earningsGrowth", 0.12) or 0.12
        
        ca = clamp((roe * 400 + op_margin * 300) / 2 + 60)
        pa = clamp(ca + (rev_growth * 80 + earn_growth * 100) + 15)
        gap = pa - ca
        
        return {
            "name": name,
            "price": cur_p,
            "ca": ca,
            "pa": pa,
            "gap": gap,
            "eta": "약 3~6개월 (단기 상승)" if gap >= 20 else "현재 전성기 (Peak)",
            "verdict": "🌟 알짜 유망주" if gap >= 20 else "🛡️ 안정형 우량주",
            "stats": {
                "수익성": clamp(roe * 500 + 50),
                "영업이익률": clamp(op_margin * 500 + 50),
                "매출성장": clamp(rev_growth * 400 + 70),
                "이익성장": clamp(earn_growth * 400 + 70),
                "현재 능력치": ca,
                "잠재력 한계": pa
            }
        }
    except Exception:
        return {
            "name": ticker, "price": 0, "ca": 100, "pa": 120, "gap": 20,
            "eta": "분석 대기", "verdict": "모니터링 대상",
            "stats": {"수익성": 100, "영업이익률": 100, "매출성장": 100, "이익성장": 100, "현재 능력치": 100, "잠재력 한계": 120}
        }

# 영문 헤드라인을 간결하고 명확한 한글 문장으로 요약 번역
def summarize_to_korean(title):
    t_lower = title.lower()
    
    # 주요 호재 패턴별 한글 번역
    if any(k in t_lower for k in ["acquisition", "acquires", "acquire", "merger"]):
        m = re.search(r"to acquire (.+)", title, re.IGNORECASE)
        target = m.group(1) if m else "유망 기업"
        return f"🤝 대규모 인수합병(M&A) 단행: {target[:30]} 인수 계약 체결", "인수합병 (M&A)"
        
    elif any(k in t_lower for k in ["partnership", "partner", "collaborat"]):
        return "🤝 전략적 사업 파트너십 체결 및 글로벌 시장 공동 확장", "전략적 파트너십"
        
    elif any(k in t_lower for k in ["contract", "secures", "awarded", "order"]):
        return "💰 대규모 공급 수주 계약 확보 (신규 매출 가시화)", "대형 수주/계약"
        
    elif any(k in t_lower for k in ["fda", "approval", "cleared", "trial", "phase"]):
        return "🧬 신약/의료기기 규제 당국 승인 완료 및 임상 진전", "FDA/신약 허가"
        
    elif any(k in t_lower for k in ["earnings", "revenue", "quarter", "results", "guidance"]):
        if any(k in t_lower for k in ["record", "beat", "strong", "jump", "surge", "raises"]):
            return "📈 시장 예상치를 웃돈 어닝 서프라이즈 및 가이던스 상향 발표", "실적 호재"
        return "📊 분기 실적 발표 및 사업 포트폴리오 업데이트 공시", "실적 발표"
        
    elif any(k in t_lower for k in ["ai", "nvidia", "chip", "patent"]):
        return "🤖 차세대 AI 인프라 도입 및 핵심 기술 특허 취득", "AI/신기술 확보"
        
    elif any(k in t_lower for k in ["shares rally", "jump", "surge", "gain"]):
        return "🚀 장중 매수세 집중으로 주가 모멘텀 급등세 분출", "주가 급등 모멘텀"
        
    else:
        # 일반 뉴스 요약
        return f"📢 주요 비즈니스 및 시장 동향 업데이트 ({title[:40]}...)", "비즈니스 뉴스"

# 최신 뉴스 피드 수집
def fetch_top_catalysts(tickers):
    news_items = []
    for t in tickers:
        try:
            feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
            if not feed.entries:
                continue
            entry = feed.entries[0] # 가장 최신 기사 1개
            
            # 시간 계산 (KST)
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
                diff_hours = int((datetime.now(timezone(timedelta(hours=9))) - dt_kst).total_seconds() // 3600)
                pub_str = f"{dt_kst.strftime('%m/%d %H:%M')} ({diff_hours}시간 전)"
                
                if diff_hours <= 8:
                    effect_str = "⚡ 오늘 정규장 즉각 반영 중 (핵심 주시)"
                elif diff_hours <= 24:
                    effect_str = "📈 단기 시세 추세 지속 반영"
                else:
                    effect_str = "⏳ 기본 가치 선반영 단계"
            else:
                pub_str = "오늘"
                effect_str = "⚡ 실시간 시장 거래 반영"
                
            kor_summary, category = summarize_to_korean(entry.title)
            
            news_items.append({
                "ticker": t,
                "category": category,
                "summary": kor_summary,
                "original_title": entry.title,
                "link": entry.link,
                "time": pub_str,
                "effect": effect_str
            })
        except Exception:
            continue
    return news_items

# --- 화면 렌더링 ---
with st.spinner("오늘 장 최신 호재 뉴스와 종목 잠재력을 분석하는 중..."):
    catalyst_list = fetch_top_catalysts(ticker_list)

if catalyst_list:
    st.markdown("### 🔔 오늘 장 최우선 주시 종목 리스트")
    st.caption("각 종목에 마우스를 올리면 잠재력(CA/PA)이 바로 뜹니다. 카드를 눌러 상세 내용을 확인하세요.")
    
    for item in catalyst_list:
        t = item["ticker"]
        prof = get_stock_profile(t)
        
        # 종목 호버 툴팁 HTML
        tooltip_html = f"""
        <div class="tooltip-box">
            <span class="badge badge-ticker">🔍 {t} ({prof['name'][:10]})</span>
            <div class="tooltip-text">
                <b>📊 {t} 잠재력 스카우팅</b><br>
                • 현재 실력(CA): <b>{prof['ca']}</b> / 200<br>
                • 잠재 능력(PA): <b>{prof['pa']}</b> / 200<br>
                • 포텐 여유: <b>+{prof['gap']}</b> Poten<br>
                • 도달 예상: {prof['eta']}<br>
                • 스카우트: {prof['verdict']}
            </div>
        </div>
        """
        
        # 메인 카드 렌더링
        st.markdown(
            f"""
            <div class="catalyst-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <div>
                        {tooltip_html}
                        <span class="badge badge-cat">{item['category']}</span>
                        <span class="badge badge-time">🕒 {item['time']}</span>
                    </div>
                    <div>
                        <span class="badge badge-effect">{item['effect']}</span>
                    </div>
                </div>
                <div style="font-size: 16px; font-weight: 700; color: #1e293b; margin: 8px 0;">
                    {item['summary']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # 클릭 시 펼쳐지는 상세 원문
        with st.expander(f"📄 {t} 원문 헤드라인 및 세부 기사 링크 보기"):
            st.write(f"**영문 원문:** {item['original_title']}")
            st.markdown(f"[🔗 야후 파이낸스 원문 기사 바로가기]({item['link']})")

    st.divider()

    # 하단 탭: 개별 세부 차트 및 전체 순위 테이블
    tab1, tab2 = st.tabs(["📊 선택 종목 육각형 레이더 차트", "📋 전체 스카우팅 랭킹 표"])
    
    with tab1:
        sel_ticker = st.selectbox("정밀 분석할 종목 선택:", options=[c["ticker"] for c in catalyst_list])
        target_prof = get_stock_profile(sel_ticker)
        
        col_c, col_d = st.columns([1, 1])
        with col_c:
            cats = list(target_prof["stats"].keys())
            vals = list(target_prof["stats"].values())
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=[target_prof["pa"]] * len(cats) + [target_prof["pa"]],
                theta=cats + [cats[0]],
                fill='toself', fillcolor='rgba(255, 179, 0, 0.08)',
                line=dict(color='#FFA000', width=1.5, dash='dash'), name='잠재 한계치 (PA)'
            ))
            fig.add_trace(go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill='toself', fillcolor='rgba(16, 185, 129, 0.35)',
                line=dict(color='#059669', width=2.5), name='현재 능력'
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor='#ffffff',
                    radialaxis=dict(visible=True, range=[0, 200], tickvals=[50, 100, 150, 200], tickfont=dict(size=9)),
                    angularaxis=dict(tickfont=dict(size=11, color="#1e293b"))
                ),
                paper_bgcolor='#ffffff',
                margin=dict(l=30, r=30, t=10, b=30), height=350
            )
            st.plotly_chart(fig, use_container_width=True)
            
        with col_d:
            st.write(f"### {sel_ticker} 능력치 총평")
            st.metric("현재 능력치 (CA)", f"{target_prof['ca']} / 200")
            st.metric("잠재 능력치 (PA)", f"{target_prof['pa']} / 200", delta=f"+{target_prof['gap']} Poten")
            st.info(f"**판정:** {target_prof['verdict']} | **예상 시점:** {target_prof['eta']}")

    with tab2:
        table_rows = []
        for c in catalyst_list:
            p = get_stock_profile(c["ticker"])
            table_rows.append({
                "티커": c["ticker"],
                "기업명": p["name"],
                "호재 분류": c["category"],
                "CA": p["ca"],
                "PA": p["pa"],
                "포텐": f"+{p['gap']}",
                "적용 타이밍": c["effect"]
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True)
else:
    st.info("현재 수집된 실시간 촉매 뉴스가 없습니다. 잠시 후 새로고침해 주세요.")