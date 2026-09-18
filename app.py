import streamlit as st
import yfinance as yf
import pandas as pd
from tradingview_screener import Query, Column
import feedparser
from datetime import datetime, timezone, timedelta
import re

st.set_page_config(page_title="실시간 뉴스 호재", layout="wide")

# CSS 스타일링: 카드 디자인 및 가독성 극대화
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    .news-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    .news-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 8px 14px -2px rgba(59, 130, 246, 0.12);
    }
    
    /* 1열 메타 태그 라인 */
    .meta-line {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #f1f5f9;
    }
    
    .badge-ticker {
        background-color: #0f172a;
        color: #ffffff;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 14px;
    }
    .badge-cat {
        background-color: #dbeafe;
        color: #1d4ed8;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
    }
    .badge-time {
        background-color: #fef3c7;
        color: #b45309;
        font-weight: 600;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
    }
    .badge-scout {
        background-color: #f1f5f9;
        color: #334155;
        font-size: 12px;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
    }
    
    /* 별점 스타일 */
    .star-badge {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        color: #b45309;
        font-weight: 800;
        font-size: 13px;
        padding: 3px 8px;
        border-radius: 6px;
        margin-left: auto;
    }
    
    /* 2열 뉴스 및 요약 */
    .news-title {
        font-size: 16px;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 8px;
    }
    .summary-box {
        background-color: #f8fafc;
        border-left: 3px solid #3b82f6;
        padding: 8px 12px;
        border-radius: 4px;
        font-size: 13px;
        color: #334155;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 실시간 뉴스 호재")
st.caption("실시간 수집된 호재 뉴스순으로 자동 갱신됩니다. (시장 영향도 및 종목 잠재력 즉시 제공)")

# 사이드바 설정 (잡다한 목록 삭제, 단일 실시간 감시 특화)
st.sidebar.header("⚙️ 실시간 레이더 설정")
scan_limit = st.sidebar.slider("스캔 종목 수", min_value=10, max_value=40, value=20, step=5)
auto_refresh = st.sidebar.toggle("⚡ 60초 자동 실시간 갱신", value=True)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 트레이딩뷰에서 현재 거래량과 주가 변동이 감지되는 실시간 후보군 추출
def fetch_active_tickers(limit):
    try:
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
    except Exception:
        return ["NVDA", "TSLA", "PLTR", "AMD", "LLY", "AAPL", "MSFT", "AMZN"]

# 펀더멘털 CA/PA 잠재력 프로필 계산
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
            "ca": ca,
            "pa": pa,
            "gap": gap,
            "eta": "약 3~6개월" if gap >= 20 else "전성기 도달",
            "verdict": "🌟 알짜 유망주" if gap >= 20 else "🛡️ 안정 우량주"
        }
    except Exception:
        return {
            "name": ticker, "ca": 105, "pa": 125, "gap": 20,
            "eta": "약 6~12개월", "verdict": "분석 대기"
        }

# 호재 분류, 별점(1~10), 2~3줄 요약 생성 함수
def analyze_news_detail(title):
    t_lower = title.lower()
    
    # 기본값
    category = "비즈니스 소식"
    stars = 5
    title_kor = title
    summary_lines = [
        "• 기업의 주요 사업 공시 및 시장 거래 동향이 보도되었습니다.",
        "• 단기 변동성보다는 중장기 펀더멘털 관점의 시장 흐름입니다."
    ]

    # 1. FDA / 임상 / 바이오 호재 (별 8~10점)
    if any(k in t_lower for k in ["fda approval", "fda approves", "cleared by fda", "breakthrough"]):
        category = "🧬 FDA 최종 승인"
        stars = 10
        title_kor = f"미국 FDA 신약/의료기기 시판 허가 승인 통과"
        summary_lines = [
            "• 규제 당국의 최종 판매 및 상용화 승인을 획득하여 신규 매출이 본격화됩니다.",
            "• 바이오/헬스케어 섹터 내 최고 수준의 급등 모멘텀 촉매로 평가됩니다.",
            "• 시세 영향: 당일 프리마켓 및 정규장에서 강력한 매수세 유입 가능성이 높습니다."
        ]
    elif any(k in t_lower for k in ["clinical trial", "phase 3", "phase 2", "positive results"]):
        category = "🧪 임상 시험 성공"
        stars = 8
        title_kor = "핵심 파이프라인 주요 임상 시험 유의미한 결과 발표"
        summary_lines = [
            "• 개발 중인 핵심 파이프라인이 임상 목표치를 충족하며 상용화 가능성을 높였습니다.",
            "• 향후 신약 허가 신청 및 라이선스 아웃(기술 수출) 기대감이 반영됩니다.",
            "• 시세 영향: 단기 기대감에 따른 급등 랠리가 촉발될 수 있습니다."
        ]

    # 2. 인수합병 (M&A) (별 8~9점)
    elif any(k in t_lower for k in ["to acquire", "acquisition", "acquires", "merger agreement"]):
        category = "🤝 대규모 인수합병(M&A)"
        stars = 9
        m = re.search(r"to acquire (.+)", title, re.IGNORECASE)
        target = m.group(1) if m else "유망 기업"
        title_kor = f"외형 성장 및 시너지 창출을 위한 [{target[:25]}] 지분 인수"
        summary_lines = [
            "• 공격적인 사업 다각화 및 점유율 확대를 위한 M&A 계약이 공식 체결되었습니다.",
            "• 피인수 기업의 고객군과 특허 기술이 연결되어 즉각적인 실적 합산 효과가 기대됩니다.",
            "• 시세 영향: 인수 규모와 조건에 따라 장단기 시세 흐름이 가파르게 반응합니다."
        ]

    # 3. 대형 수주 / 공급 계약 (별 7~9점)
    elif any(k in t_lower for k in ["secures contract", "awarded contract", "supply agreement", "major order"]):
        category = "💰 대형 공급/수주 계약"
        stars = 8
        title_kor = "대규모 제품/서비스 장기 공급 수주 계약 확정"
        summary_lines = [
            "• 글로벌 고객사 또는 정부 기관과의 대형 공급 수주가 공식화되었습니다.",
            "• 향후 수개 분기 동안 안정적인 매출 파이프라인과 영업이익을 보장받게 됩니다.",
            "• 시세 영향: 확실한 실적 기반의 기관 수급 유입이 기대되는 호재입니다."
        ]

    # 4. 전략적 파트너십 (별 6~8점)
    elif any(k in t_lower for k in ["partnership", "partners with", "collaborates"]):
        category = "🌐 전략적 파트너십"
        stars = 7
        title_kor = "업계 선두권 기업과 공동 사업 확장 파트너십 구축"
        summary_lines = [
            "• 빅테크 또는 글로벌 파트너사와 손잡고 차세대 솔루션 공동 개발에 착수합니다.",
            "• 판로 확대 및 브랜드 신뢰도 상승에 따른 중장기적 프리미엄이 부여됩니다.",
            "• 시세 영향: 단기 테마성 매수세 및 중기 가치 재평가가 동시에 발생합니다."
        ]

    # 5. 실적 호재 / 가이던스 상향 (별 7~9점)
    elif any(k in t_lower for k in ["raises guidance", "beats earnings", "record revenue", "earnings surprise"]):
        category = "📈 어닝 서프라이즈"
        stars = 8
        title_kor = "시장 예상치를 뛰어넘는 호실적 달성 및 연간 목표치 상향"
        summary_lines = [
            "• 최근 분기 매출과 주당순이익(EPS)이 월가 컨센서스를 대폭 웃돌았습니다.",
            "• 경영진이 향후 실적 가이던스를 공격적으로 상향 조정하며 강한 자신감을 보였습니다.",
            "• 시세 영향: 실적 장세에서 가장 정석적인 갭상승 및 추세 랠리를 유발합니다."
        ]

    # 6. AI 및 신기술 채택 (별 7~8점)
    elif any(k in t_lower for k in ["ai", "nvidia", "patent", "breakthrough"]):
        category = "🤖 AI/첨단 기술 혁신"
        stars = 7
        title_kor = "차세대 AI 기술 상용화 및 독점 특허권 취득"
        summary_lines = [
            "• 인공지능 인프라 결합 및 신기술 특허 취득으로 기술 장벽을 한층 높였습니다.",
            "• 시장 주도 섹터(AI/반도체) 테마와 연계되어 높은 밸류에이션 프리미엄을 받습니다.",
            "• 시세 영향: 모멘텀 수급 집중 시 가파른 단기 슈팅이 빈번하게 발생합니다."
        ]

    return category, stars, title_kor, summary_lines

def star_render(stars):
    # 별 1~10개 시각화
    full = "★" * stars
    empty = "☆" * (10 - stars)
    return f"{full}{empty} ({stars}/10점)"

def fetch_latest_catalysts(tickers):
    news_items = []
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    
    for t in tickers:
        try:
            feed = feedparser.parse(f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={t}&region=US&lang=en-US")
            if not feed.entries:
                continue
            entry = feed.entries[0]
            
            if hasattr(entry, 'published_parsed') and entry.published_parsed:
                dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
                diff_hours = int((now_kst - dt_kst).total_seconds() // 3600)
                diff_mins = int(((now_kst - dt_kst).total_seconds() % 3600) // 60)
                timestamp_val = dt_kst.timestamp()
                
                if diff_hours == 0:
                    time_ago = f"{diff_mins}분 전"
                else:
                    time_ago = f"{diff_hours}시간 전"
                pub_str = f"{dt_kst.strftime('%m/%d %H:%M')} ({time_ago})"
            else:
                timestamp_val = 0
                pub_str = "최근 24시간 이내"
                
            cat, stars, kor_title, summary_lines = analyze_news_detail(entry.title)
            
            news_items.append({
                "ticker": t,
                "timestamp": timestamp_val,
                "time": pub_str,
                "category": cat,
                "stars": stars,
                "title_kor": kor_title,
                "summary": summary_lines,
                "original_title": entry.title,
                "link": entry.link
            })
        except Exception:
            continue
            
    # 가장 최신 보도 뉴스 순으로 정렬
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

# 60초 주기 자동 리프레시 프래그먼트
@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_feed():
    tickers = fetch_active_tickers(scan_limit)
    news_list = fetch_latest_catalysts(tickers)
    
    if news_list:
        st.write(f"⏱️ **실시간 수집 현황:** 총 {len(news_list)}건의 호재 뉴스 감지 (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            prof = get_stock_profile(t)
            
            # 1줄: 종목명 > 호재분류 > 시간 > 잠재력 스카우팅 및 별점
            scout_text = f"CA {prof['ca']} / PA {prof['pa']} (+{prof['gap']} 포텐) | 도달: {prof['eta']}"
            stars_text = star_render(item["stars"])
            
            card_html = f"""
            <div class="news-card">
                <div class="meta-line">
                    <span class="badge-ticker">🔍 {t} ({prof['name'][:12]})</span>
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 잠재력 스카우팅: {scout_text}</span>
                    <span class="star-badge">{stars_text}</span>
                </div>
                <div class="news-title">
                    📢 {item['title_kor']}
                </div>
                <div class="summary-box">
                    {'<br>'.join(item['summary'])}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.expander(f"📄 [{t}] 영문 원문 기사 및 링크 확인"):
                st.write(f"**헤드라인:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 전문 열기]({item['link']})")
    else:
        st.info("현재 수집된 신규 호재 뉴스가 없습니다. 잠시 후 자동으로 다시 시도합니다.")

# 렌더링 호출
render_news_feed()