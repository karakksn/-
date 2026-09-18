import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re

st.set_page_config(page_title="실시간 뉴스 호재", layout="wide")

# CSS 스타일링
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
st.caption("미국 증시 전체 실시간 속보 피드에서 호재 종목을 자동 선별하여 최신순으로 띄웁니다.")

# 사이드바 (종목 수 슬라이더 제거)
st.sidebar.header("⚙️ 실시간 감시")
auto_refresh = st.sidebar.toggle("⚡ 60초 자동 실시간 갱신", value=True)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 펀더멘털 CA/PA 연산 (캐싱으로 고속 처리)
@st.cache_data(ttl=3600)
def get_stock_profile(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.fast_info
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
            "eta": "약 3~6개월" if gap >= 20 else "전성기 도달"
        }
    except Exception:
        return {
            "name": ticker, "ca": 105, "pa": 125, "gap": 20, "eta": "약 6~12개월"
        }

# 호재 분류 및 2~3줄 요약, 별점 계산
def analyze_news_detail(title):
    t_lower = title.lower()
    
    category = "비즈니스 소식"
    stars = 5
    title_kor = "주요 기업 비즈니스 업데이트 및 공시"
    summary_lines = [
        "• 기업의 최근 경영 현황 및 시장 거래 관련 뉴스가 보도되었습니다.",
        "• 단기 급변동보다는 정규 펀더멘털 추세 영향권입니다."
    ]

    if any(k in t_lower for k in ["fda approval", "fda approves", "cleared by fda", "breakthrough therapy"]):
        category = "🧬 FDA 최종 승인"
        stars = 10
        title_kor = "미국 FDA 신약/의료기기 최종 품목 허가 및 판매 승인"
        summary_lines = [
            "• 규제 당국의 최종 판매 승인을 획득하여 신규 매출 발생이 공식화되었습니다.",
            "• 제약/바이오 섹터 내 단기 시세 폭발력이 가장 높은 최상급 촉매입니다.",
            "• 시세 영향: 당일 장 시작 전후로 강력한 매수세 및 갭상승 가능성이 큽니다."
        ]
    elif any(k in t_lower for k in ["clinical trial", "phase 3", "phase 2", "positive topline"]):
        category = "🧪 핵심 임상 성공"
        stars = 8
        title_kor = "핵심 파이프라인 임상 시험 유의미한 효능 입증"
        summary_lines = [
            "• 주요 임상 단계에서 1차 평가지표를 달성하며 성공적인 결과를 발표했습니다.",
            "• 글로벌 기술 수출(L/O) 및 상용화 신약 가치 재평가가 시작됩니다.",
            "• 시세 영향: 단기 기대감에 따른 급등 랠리가 촉발될 수 있습니다."
        ]
    elif any(k in t_lower for k in ["to acquire", "acquisition", "acquires", "merger agreement"]):
        category = "🤝 대규모 M&A 체결"
        stars = 9
        title_kor = "외형 확장 및 시너지 창출을 위한 대규모 인수합병(M&A) 단행"
        summary_lines = [
            "• 시장 지배력 강화 및 사업 포트폴리오 확장을 위한 인수를 공식 체결했습니다.",
            "• 피인수 기업의 고객망과 기술이 합산되어 즉각적인 외형 성장이 기대됩니다.",
            "• 시세 영향: 거래 규모와 조건에 따라 강한 시세 분출이 나타납니다."
        ]
    elif any(k in t_lower for k in ["secures contract", "awarded contract", "supply agreement", "major order"]):
        category = "💰 대형 수주 계약"
        stars = 8
        title_kor = "글로벌 고객사 대상 대규모 공급 수주 계약 체결"
        summary_lines = [
            "• 정부 기관 또는 주요 대기업과의 공급 계약 체결이 확정되었습니다.",
            "• 중장기 매출 파이프라인이 확보되어 실적 가시성이 크게 높아집니다.",
            "• 시세 영향: 실적 신뢰도 상승에 따른 안정적 기관 수급 유입이 발생합니다."
        ]
    elif any(k in t_lower for k in ["partnership", "partners with", "collaborates"]):
        category = "🌐 전략적 파트너십"
        stars = 7
        title_kor = "업계 선두권 파트너와 전략적 비즈니스 협력 체결"
        summary_lines = [
            "• 핵심 파트너사와 공동 기술 개발 및 글로벌 판매망을 공유합니다.",
            "• 판로 확대 및 브랜드 가치 제고를 통한 시장 점유율 확장이 기대됩니다.",
            "• 시세 영향: 테마성 관심과 함께 중기 성장 프리미엄이 붙습니다."
        ]
    elif any(k in t_lower for k in ["raises guidance", "beats earnings", "record revenue", "earnings surprise"]):
        category = "📈 어닝 서프라이즈"
        stars = 8
        title_kor = "시장 전망치를 웃도는 실적 서프라이즈 및 연간 가이던스 상향"
        summary_lines = [
            "• 분기 실적이 시장 컨센서스를 대폭 상회하며 견고한 이익 체력을 입증했습니다.",
            "• 경영진이 향후 성장 목표치를 높여 잡으며 실적 모멘텀이 강화되었습니다.",
            "• 시세 영향: 실적 기반의 정석적인 우상향 랠리가 형성됩니다."
        ]
    elif any(k in t_lower for k in ["ai", "nvidia", "patent", "breakthrough"]):
        category = "🤖 AI/첨단 기술 혁신"
        stars = 7
        title_kor = "차세대 AI 기술 인프라 도입 및 핵심 독점 특허 확보"
        summary_lines = [
            "• 인공지능 인프라 결합 및 신기술 특허 취득으로 기술 장벽을 강화했습니다.",
            "• 시장 주도 AI/반도체 테마와 연계되어 높은 멀티플을 부여받을 수 있습니다.",
            "• 시세 영향: 모멘텀 수급 집중 시 가파른 단기 슈팅이 빈번하게 발생합니다."
        ]

    return category, stars, title_kor, summary_lines

def star_render(stars):
    full = "★" * stars
    empty = "☆" * (10 - stars)
    return f"{full}{empty} ({stars}/10점)"

# 헤드라인 텍스트에서 티커 추출 함수
def extract_ticker_from_text(title):
    # 예: (NASDAQ: NVDA), (NYSE: LLY), $TSLA, AAPL: 형태 매칭
    match = re.search(r'\((?:NASDAQ|NYSE):\s*([A-Z]{1,5})\)', title, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    match2 = re.search(r'\$([A-Z]{1,5})\b', title)
    if match2:
        return match2.group(1).upper()
    match3 = re.search(r'\b([A-Z]{2,5})\b', title)
    if match3:
        cand = match3.group(1).upper()
        if cand not in ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI"]:
            return cand
    return None

# 미국 증시 종합 실시간 속보 RSS 피드 수집 (종목 수 제한 없이 피드 직결)
def fetch_market_wide_news():
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    
    # 미국 시장 전체 종합 속보 및 비즈니스 와이어 피드
    rss_urls = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", # S&P 500 종합 피드
        "https://finance.yahoo.com/news/rssindex",                                    # 야후 파이낸스 실시간 속보
    ]
    
    raw_entries = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                raw_entries.extend(feed.entries)
        except Exception:
            continue

    # 중복 제거
    seen_links = set()
    unique_entries = []
    for e in raw_entries:
        if e.link not in seen_links:
            seen_links.add(e.link)
            unique_entries.append(e)

    news_items = []
    for entry in unique_entries:
        title = entry.title
        ticker = extract_ticker_from_text(title)
        if not ticker:
            continue
            
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
            diff_hours = int((now_kst - dt_kst).total_seconds() // 3600)
            diff_mins = int(((now_kst - dt_kst).total_seconds() % 3600) // 60)
            timestamp_val = dt_kst.timestamp()
            
            if diff_hours == 0:
                time_ago = f"{max(1, diff_mins)}분 전"
            else:
                time_ago = f"{diff_hours}시간 전"
            pub_str = f"{dt_kst.strftime('%m/%d %H:%M')} ({time_ago})"
        else:
            timestamp_val = 0
            pub_str = "방금 전"
            
        cat, stars, kor_title, summary_lines = analyze_news_detail(title)
        
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": cat,
            "stars": stars,
            "title_kor": kor_title,
            "summary": summary_lines,
            "original_title": title,
            "link": entry.link
        })
        
    # 최신 발생 뉴스 순 정렬
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_feed():
    news_list = fetch_market_wide_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 수집 현황:** 총 {len(news_list)}건의 실시간 속보 감지 (최신순 자동 정렬)")
        
        for item in news_list:
            t = item["ticker"]
            prof = get_stock_profile(t)
            
            scout_text = f"CA {prof['ca']} / PA {prof['pa']} (+{prof['gap']} 포텐) | 도달: {prof['eta']}"
            stars_text = star_render(item["stars"])
            
            card_html = f"""
            <div class="news-card">
                <div class="meta-line">
                    <span class="badge-ticker">🔍 {t} ({prof['name'][:12]})</span>
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 잠재력: {scout_text}</span>
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
                st.markdown(f"[🔗 야후 파이낸스 원문 기사 바로가기]({item['link']})")
    else:
        st.info("현재 시장 속보 피드를 탐색 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_feed()