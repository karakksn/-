import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re

st.set_page_config(page_title="실시간 뉴스 호재 & 매크로 레이더", layout="wide")

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
        font-size: 13px;
    }
    .badge-macro {
        background-color: #4338ca;
        color: #ffffff;
        font-weight: 800;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 13px;
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

st.title("🔥 실시간 뉴스 호재 & 시장 매크로 레이더")
st.caption("개별 종목 호재뿐 아니라 금리, 유가, 전쟁, 비트코인 등 증시 핵심 매크로 이슈를 3일 이내 최신순으로 전해드립니다.")

st.sidebar.header("⚙️ 실시간 감시")
auto_refresh = st.sidebar.toggle("⚡ 60초 자동 실시간 갱신", value=True)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

# 펀더멘털 CA/PA 연산 (캐싱)
@st.cache_data(ttl=3600)
def get_stock_profile(ticker):
    if not ticker or ticker == "MACRO":
        return None
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

# 기사 텍스트에서 개별 종목 티커 추출
def extract_ticker(title):
    match = re.search(r'\((?:NASDAQ|NYSE):\s*([A-Z]{1,5})\)', title, re.IGNORECASE)
    if match: return match.group(1).upper()
    match2 = re.search(r'\$([A-Z]{1,5})\b', title)
    if match2: return match2.group(1).upper()
    match3 = re.search(r'\b([A-Z]{2,5})\b', title)
    if match3:
        cand = match3.group(1).upper()
        if cand not in ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI", "CPI", "FED", "GDP", "WAR", "OIL"]:
            return cand
    return None

# 매크로(금리/유가/전쟁/코인) 및 종목 호재 통합 분석 엔진
def analyze_article(title):
    t_lower = title.lower()
    
    # --- [매크로 영역: 시장 전체에 영향을 끼치는 외생 변수] ---
    # 1. 금리 / 연준 / CPI 물가 지표
    if any(k in t_lower for k in ["fed", "federal reserve", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        category = "🏦 금리 / 통화정책"
        stars = 9
        title_kor = "미국 연준(Fed) 금리 정책 및 인플레이션 지표 발표"
        summary = [
            "• 기준금리 인하/인상 방향성과 파월 의장의 발언이 시장 전체 유동성을 좌우합니다.",
            "• 국채 금리 및 달러 환율 변동으로 기술주와 성장주 밸류에이션에 직접적인 영향을 미칩니다.",
            "• 시세 영향: 나스닥/S&P500 지수 전반의 방향성을 결정하는 최상위 매크로 변수입니다."
        ]
        return "MACRO", category, stars, title_kor, summary

    # 2. 전쟁 / 지정학적 갈등 / 무역 제재
    elif any(k in t_lower for k in ["war", "military", "strike", "middle east", "israel", "iran", "ukraine", "russia", "sanction"]):
        category = "⚔️ 전쟁 / 지정학 리스크"
        stars = 9
        title_kor = "글로벌 분쟁 및 지정학적 위기 고조 (안전자산 선호)"
        summary = [
            "• 국제 분쟁 및 군사적 긴장감 고조로 위험자산 회피 심리가 확산되고 있습니다.",
            "• 공급망 차질 우려와 함께 방산주/원자재/달러/금 등 안전자산으로 수급이 이동합니다.",
            "• 시세 영향: 단기 시장 변동성 확대 및 에너지·방산 섹터 상대적 강세 유발."
        ]
        return "MACRO", category, stars, title_kor, summary

    # 3. 유가 / 원유 / 에너지 시장
    elif any(k in t_lower for k in ["oil price", "crude oil", "opec", "brent", "gasoline", "energy price"]):
        category = "🛢️ 유가 / 에너지 동향"
        stars = 8
        title_kor = "국제 유가 및 OPEC 원유 생산 정책 변동"
        summary = [
            "• 원유 수급 불안정 또는 감산/증산 소식으로 국제 유가가 민감하게 요동치고 있습니다.",
            "• 유가 급등은 기업 생산 원가 증가 및 인플레이션 재점화 우려로 증시에 부담을 줍니다.",
            "• 시세 영향: 정유/에너지 기업 주가 직결 및 항공/운송 섹터 수익성에 영향."
        ]
        return "MACRO", category, stars, title_kor, summary

    # 4. 코인 / 비트코인 / 크립토
    elif any(k in t_lower for k in ["bitcoin", "crypto", "ethereum", "btc", "etf approval", "sec crypto"]):
        category = "🪙 암호화폐 / 비트코인"
        stars = 8
        title_kor = "비트코인 등 암호화폐 시장 변동성 및 규제 동향"
        summary = [
            "• 현물 ETF 자금 유입, 반감기, 또는 금융 규제 이슈로 가상자산 시장이 반응하고 있습니다.",
            "• 시장 전반의 투심 및 코인 보유 기업(마이크로스트래티지, 테슬라 등), 거래소 주가에 직결됩니다.",
            "• 시세 영향: 디지털 자산 관련주 및 핀테크 섹터의 강한 동반 급등락 형성."
        ]
        return "MACRO", category, stars, title_kor, summary

    # --- [개별 종목 호재 영역] ---
    ticker = extract_ticker(title)
    
    if any(k in t_lower for k in ["fda approval", "fda approves", "cleared by fda", "breakthrough"]):
        return ticker, "🧬 FDA 최종 승인", 10, "미국 FDA 신약/의료기기 시판 허가 최종 획득", [
            "• 규제 당국의 최종 상용화 승인을 획득하여 신규 매출이 본격화됩니다.",
            "• 바이오/헬스케어 섹터 내 단기 시세 폭발력이 가장 높은 최상급 촉매입니다.",
            "• 시세 영향: 장 시작 전후로 강력한 매수세와 갭상승이 나타날 가능성이 큽니다."
        ]
    elif any(k in t_lower for k in ["to acquire", "acquisition", "acquires", "merger agreement"]):
        return ticker, "🤝 대규모 M&A 체결", 9, "외형 확장 및 시너지 창출을 위한 대형 인수합병 단행", [
            "• 시장 점유율 확대를 위한 핵심 기업 지분 인수를 공식 체결했습니다.",
            "• 피인수 기업의 고객망과 기술이 연결되어 즉각적인 외형 성장이 기대됩니다.",
            "• 시세 영향: 거래 규모와 조건에 따라 장단기 시세 흐름이 가파르게 반응합니다."
        ]
    elif any(k in t_lower for k in ["secures contract", "awarded contract", "supply agreement", "major order"]):
        return ticker, "💰 대형 수주 계약", 8, "글로벌 고객사 대상 대규모 공급 수주 계약 체결", [
            "• 정부 기관 또는 주요 글로벌 대기업과의 납품 계약이 확정되었습니다.",
            "• 중장기 매출 파이프라인이 확보되어 실적 가시성이 크게 높아집니다.",
            "• 시세 영향: 확실한 실적 기반의 안정적 기관 매수세 유입이 기대됩니다."
        ]
    elif any(k in t_lower for k in ["raises guidance", "beats earnings", "record revenue", "earnings surprise"]):
        return ticker, "📈 어닝 서프라이즈", 8, "시장 전망치를 웃도는 실적 서프라이즈 및 목표치 상향", [
            "• 분기 실적이 월가 컨센서스를 대폭 상회하며 견고한 펀더멘털을 입증했습니다.",
            "• 경영진이 향후 성장 목표치를 높여 잡으며 실적 모멘텀이 강화되었습니다.",
            "• 시세 영향: 실적 장세에서 가장 정석적인 우상향 랠리를 이끕니다."
        ]
    elif any(k in t_lower for k in ["partnership", "partners with", "collaborates"]):
        return ticker, "🌐 전략적 파트너십", 7, "선두권 파트너사와 전략적 공동 비즈니스 협약 체결", [
            "• 파트너사와 공동 기술 개발 및 글로벌 판매망을 공유합니다.",
            "• 판로 확대 및 브랜드 신뢰도 상승에 따른 중장기적 프리미엄이 부여됩니다.",
            "• 시세 영향: 단기 테마성 매수세 및 중기 가치 재평가가 동시에 발생합니다."
        ]
    elif any(k in t_lower for k in ["ai", "nvidia", "patent", "breakthrough"]):
        return ticker, "🤖 AI/첨단 기술 혁신", 7, "차세대 AI 기술 상용화 및 핵심 독점 특허 확보", [
            "• 인공지능 인프라 결합 및 신기술 특허 취득으로 기술 장벽을 강화했습니다.",
            "• 시장 주도 AI/반도체 테마와 연계되어 높은 멀티플을 부여받을 수 있습니다.",
            "• 시세 영향: 모멘텀 수급 집중 시 가파른 단기 슈팅이 유발됩니다."
        ]

    # 일반 시장 소식
    return ticker, "📢 주요 비즈니스 동향", 5, "주요 기업 경영 및 시장 거래 동향 공시", [
        "• 기업의 최근 경영 현황 및 시장 거래 관련 뉴스가 보도되었습니다.",
        "• 단기 변동성보다는 정규 펀더멘털 추세 영향권입니다."
    ]

def star_render(stars):
    full = "★" * stars
    empty = "☆" * (10 - stars)
    return f"{full}{empty} ({stars}/10점)"

# 통합 RSS 뉴스 피드 수집 (개별 종목 + 매크로 전체)
def fetch_all_market_news():
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    
    # 미국 시장 종합 피드 (경제, 기술, 원자재, 크립토)
    rss_urls = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", # S&P500 종합
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F&region=US&lang=en-US",   # 원유/유가
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US", # 비트코인
        "https://finance.yahoo.com/news/rssindex"                                         # 실시간 속보 피드
    ]
    
    raw_entries = []
    for url in rss_urls:
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                raw_entries.extend(feed.entries)
        except Exception:
            continue

    seen_links = set()
    unique_entries = []
    for e in raw_entries:
        if hasattr(e, 'link') and e.link not in seen_links:
            seen_links.add(e.link)
            unique_entries.append(e)

    news_items = []
    for entry in unique_entries:
        title = entry.title
        
        # 1. 발행 시각 및 3일(72시간) 초과 필터링
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
            total_seconds = (now_kst - dt_kst).total_seconds()
            
            # [필터] 3일(72시간 = 259,200초) 지난 소식은 즉시 제외
            if total_seconds > 259200:
                continue
                
            diff_hours = int(total_seconds // 3600)
            diff_mins = int((total_seconds % 3600) // 60)
            timestamp_val = dt_kst.timestamp()
            
            if diff_hours == 0:
                time_ago = f"{max(1, diff_mins)}분 전"
            elif diff_hours < 24:
                time_ago = f"{diff_hours}시간 전"
            else:
                time_ago = f"{diff_hours // 24}일 전"
                
            pub_str = f"{dt_kst.strftime('%m/%d %H:%M')} ({time_ago})"
        else:
            # 시간 정보가 없으면 최근으로 간주
            timestamp_val = now_kst.timestamp()
            pub_str = "최근 24시간 이내"
            
        ticker, cat, stars, kor_title, summary_lines = analyze_article(title)
        
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
        
    # 최신 발생 순으로 정렬
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

# 60초 자동 갱신
@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_all_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 수집 현황:** 최근 3일 이내의 핵심 호재 및 매크로 뉴스 {len(news_list)}건 감지 (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            
            # 매크로 뉴스 vs 개별 종목 뉴스 구분 렌더링
            if t == "MACRO" or not t:
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로</span>'
                scout_text = "시장 전반 유동성 / 섹터 지수 영향"
            else:
                prof = get_stock_profile(t)
                if prof:
                    ticker_badge = f'<span class="badge-ticker">🔍 {t} ({prof["name"][:10]})</span>'
                    scout_text = f"CA {prof['ca']} / PA {prof['pa']} (+{prof['gap']} 포텐) | 도달: {prof['eta']}"
                else:
                    ticker_badge = f'<span class="badge-ticker">🔍 {t}</span>'
                    scout_text = "개별 종목 모멘텀 수급 집중"
                    
            stars_text = star_render(item["stars"])
            
            card_html = f"""
            <div class="news-card">
                <div class="meta-line">
                    {ticker_badge}
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 영향도/스카우팅: {scout_text}</span>
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
            
            with st.expander(f"📄 세부 원문 기사 및 링크 확인"):
                st.write(f"**영문 헤드라인:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 원문 보기]({item['link']})")
    else:
        st.info("현재 3일 이내의 시장 뉴스를 수신 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()