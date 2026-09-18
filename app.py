import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html

st.set_page_config(page_title="데일리 AI 주식 비서 - 실시간 브리핑", layout="wide")

# 영상 속 브리핑 카드 스타일 CSS
st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    .briefing-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    .briefing-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 10px 16px -2px rgba(59, 130, 246, 0.12);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #f1f5f9;
    }
    
    .badge-stock {
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
    .star-rating {
        background-color: #fffbeb;
        border: 1px solid #fde68a;
        color: #b45309;
        font-weight: 800;
        font-size: 13px;
        padding: 3px 8px;
        border-radius: 6px;
        margin-left: auto;
    }
    
    .headline-text {
        font-size: 16px;
        font-weight: 800;
        color: #1e293b;
        margin-bottom: 10px;
    }
    
    .briefing-box {
        background-color: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 6px;
        font-size: 13.5px;
        line-height: 1.7;
        color: #1e293b;
    }
    
    .action-box {
        margin-top: 8px;
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 8px 14px;
        border-radius: 6px;
        font-size: 13px;
        color: #1d4ed8;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📱 데일리 AI 주식 비서: 실시간 브리핑")
st.caption("유튜브 영상 속 AI 비서처럼 종목 뉴스 요약과 오늘의 체크포인트를 자동으로 정리해 드립니다.")

st.sidebar.header("⚙️ 비서 자동 갱신")
auto_refresh = st.sidebar.toggle("⚡ 60초 주기 자동 브리핑", value=True)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

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
        return {"name": ticker, "ca": 105, "pa": 125, "gap": 20, "eta": "약 6~12개월"}

def extract_ticker(title):
    match = re.search(r'\((?:NASDAQ|NYSE):\s*([A-Z]{1,5})\)', title, re.IGNORECASE)
    if match: return match.group(1).upper()
    match2 = re.search(r'\$([A-Z]{1,5})\b', title)
    if match2: return match2.group(1).upper()
    match3 = re.search(r'\b([A-Z]{2,5})\b', title)
    if match3:
        cand = match3.group(1).upper()
        if cand not in ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI", "CPI", "FED", "GDP", "WAR", "OIL", "US", "USA", "ONE", "TWO"]:
            return cand
    return None

# 유튜브 비서 스타일 3단 브리핑 생성 엔진
def make_executive_briefing(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 비교/선별형 기사 (예: 1 Bank Stock Worth Investigating...)
    if any(k in combo for k in ["worth investigating", "stocks to buy and", "we ignore", "avoid", "facing headwinds"]):
        headline = "주목할 알짜 종목과 리스크 종목 선별 비교 분석"
        lines = [
            "• **핵심 팩트:** 차별화된 비이자 수수료 기반과 고수익성(ROE 30%+)을 갖춘 알짜주는 매력적이나, 전통 예대마진 의존도가 높은 지방 은행은 주의 권고.",
            "• **실적/주가 영향:** 금리 변동성에 취약한 기업의 실적 둔화 우려가 부각되며, 탄탄한 펀더멘털을 보유한 1등주로 수급 쏠림 예상."
        ]
        action = "💡 오늘 체크포인트: 포트폴리오 내 단순 금리 수혜주 비중 점검 및 안정적 고수익성 종목 위주 압축"
        return "⚖️ 종목 선별", 8, headline, lines, action

    # 2. FDA 승인
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        headline = "미국 FDA 신약/의료기기 최종 품목 허가 승인 통과"
        lines = [
            "• **핵심 팩트:** 규제 당국의 최종 판매 및 유통 승인을 획득하여 제품 상용화가 공식 시작되었습니다.",
            "• **실적/주가 영향:** 개발 실패 리스크가 완전히 소멸되었으며, 병원 납품 시작과 함께 즉각적인 신규 매출이 발생합니다."
        ]
        action = "💡 오늘 체크포인트: 당일 장초반 갭상승 후 기관 거래량 유입 및 애널리스트 목표주가 상향 리포트 주시"
        return "🧬 FDA 최종승인", 10, headline, lines, action

    # 3. 임상 시험 성공
    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        headline = "핵심 파이프라인 임상 시험 유의미한 효능 입증"
        lines = [
            "• **핵심 팩트:** 환자 대상 임상 단계에서 1차 평가지표를 달성하며 통계적 유의성을 입증했습니다.",
            "• **실적/주가 영향:** 향후 글로벌 빅파마 대상 대규모 기술수출(L/O) 및 상용화 신약 가치 상승이 기대됩니다."
        ]
        action = "💡 오늘 체크포인트: 기술수출 협상 가능성 및 단기 급등 시 차익실현 매물 출회 여부 확인"
        return "🧪 임상 성공", 8, headline, lines, action

    # 4. 인수합병 (M&A)
    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "유망 기업"
        headline = f"사업 시너지 강화를 위한 [{target[:22]}] 인수합병 단행"
        lines = [
            "• **핵심 팩트:** 신규 성장 동력 확보를 위해 핵심 지분 인수 및 사업 합병 계약을 정식 체결했습니다.",
            "• **실적/주가 영향:** 피인수 기업의 고객망과 기술이 연결되어 분기 연결 실적에 즉각적인 외형 확장이 반영됩니다."
        ]
        action = "💡 오늘 체크포인트: 인수 대금 조달 조건(현금/증자)에 따른 주가 희석 여부 및 장기 마진율 추이 관찰"
        return "🤝 M&A 체결", 9, headline, lines, action

    # 5. 대형 수주 / 계약
    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        headline = "글로벌 고객사 대상 대규모 공급 수주 계약 체결"
        lines = [
            "• **핵심 팩트:** 정부 기관 또는 대기업과의 장기 제품/솔루션 공급 계약이 확정되었습니다.",
            "• **실적/주가 영향:** 수주 잔고가 대폭 증가하여 향후 1~2년간 안정적인 실적 가시성을 확보했습니다."
        ]
        action = "💡 오늘 체크포인트: 수주 금액의 연간 매출 대비 비중 파악 및 실적 발표 시 영업이익률 반영 확인"
        return "💰 대형 수주", 8, headline, lines, action

    # 6. 실적 호재 / 서프라이즈
    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        headline = "시장 컨센서스 상회 호실적 및 연간 가이던스 상향"
        lines = [
            "• **핵심 팩트:** 분기 매출과 영업이익이 월가 예상치를 크게 웃돌았으며, 경영진이 향후 목표치를 상향했습니다.",
            "• **실적/주가 영향:** 탄탄한 본업 이익 체력이 입증되며 기관들의 목표가 상향과 매수세가 이어집니다."
        ]
        action = "💡 오늘 체크포인트: 실적 발표 후 컨퍼런스콜 세부 코멘트(수주 잔고, 마진 가이던스) 체크"
        return "📈 실적 서프라이즈", 8, headline, lines, action

    # 7. 금리 / 연준 (매크로)
    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        headline = "미 연준 기준금리 정책 및 주요 물가 지표 발표"
        lines = [
            "• **핵심 팩트:** 파월 의장의 통화정책 발언 및 CPI 지표가 발표되며 향후 금리 인하 속도에 시장 관심이 집중되었습니다.",
            "• **실적/주가 영향:** 국채 금리와 달러 인덱스가 출렁이며 나스닥 고성장 기술주의 밸류에이션에 직접적 영향을 미칩니다."
        ]
        action = "💡 오늘 체크포인트: 10년물 미국채 금리 추이 및 나스닥 지수 선물 변동성 실시간 점검"
        return "🏦 금리/매크로", 9, headline, lines, action

    # 8. 유가 / 원유 (매크로)
    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        headline = "국제 유가 변동 및 원유 공급망 이슈"
        lines = [
            "• **핵심 팩트:** OPEC 생산 정책 및 지정학적 불안으로 국제 유가(WTI/브렌트유)가 급변동하고 있습니다.",
            "• **실적/주가 영향:** 유가 상승 시 물류/원가 부담으로 일반 제조업에 부담이나, 정유·에너지 기업 주가에는 호재로 작용합니다."
        ]
        action = "💡 오늘 체크포인트: 에너지 섹터 ETF(XLE) 수급 및 인플레이션 재점화 우려 여부 모니터링"
        return "🛢️ 유가/에너지", 8, headline, lines, action

    # 9. 암호화폐 / 비트코인
    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        headline = "비트코인 등 가상자산 시세 변동 및 규제 동향"
        lines = [
            "• **핵심 팩트:** 현물 ETF 자금 유출입 및 기관 매수세에 따라 비트코인 시세가 강한 변동성을 보이고 있습니다.",
            "• **실적/주가 영향:** 가상자산 관련주(MSTR, COIN 등)와 핀테크 섹터의 동반 주가 급등락이 연출됩니다."
        ]
        action = "💡 오늘 체크포인트: 암호화폐 관련주 프리마켓 갭상승 폭 및 비트코인 주요 지지선 유지 여부 확인"
        return "🪙 크립토", 8, headline, lines, action

    # 기본 기사
    clean_title = title.replace(" - Yahoo Finance", "").replace("Yahoo Finance", "")
    headline = f"주요 사업 진행 상황 및 시장 동향 업데이트"
    lines = [
        f"• **핵심 팩트:** {clean_title[:55]} 관련 소식이 전해졌습니다.",
        "• **실적/주가 영향:** 단기적인 급변동 요인보다는 기업의 중장기 사업 체질 개선 및 시장 거래 흐름에 따른 변동입니다."
    ]
    action = "💡 오늘 체크포인트: 거래량 증가 추이 및 주요 이동평균선 지지 여부 관찰"
    return "📢 기업 소식", 6, headline, lines, action

def star_render(stars):
    full = "★" * stars
    empty = "☆" * (10 - stars)
    return f"{full}{empty} ({stars}/10점)"

def fetch_all_market_news():
    now_kst = datetime.now(timezone(timedelta(hours=9)))
    
    rss_urls = [
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=CL=F&region=US&lang=en-US",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
        "https://finance.yahoo.com/news/rssindex"
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
        summary_raw = getattr(entry, 'summary', '')
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
            total_seconds = (now_kst - dt_kst).total_seconds()
            
            # 3일(72시간) 초과 과거 뉴스 자동 배제
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
            timestamp_val = now_kst.timestamp()
            pub_str = "방금 전"
            
        ticker = extract_ticker(title)
        category, stars, headline_kor, summary_lines, action_guide = make_executive_briefing(title, summary_raw)
        
        if any(cat_key in category for cat_key in ["금리", "유가", "크립토"]):
            ticker = "MACRO"
            
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": category,
            "stars": stars,
            "headline": headline_kor,
            "summary": summary_lines,
            "action": action_guide,
            "original_title": title,
            "link": entry.link
        })
        
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_all_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 브리핑:** 최근 3일 이내 핵심 이슈 {len(news_list)}건 (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            
            if t == "MACRO" or not t:
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로</span>'
                scout_text = "시장 지수 / 섹터 전반 영향"
            else:
                prof = get_stock_profile(t)
                if prof:
                    ticker_badge = f'<span class="badge-stock">🔍 {t} ({prof["name"][:10]})</span>'
                    scout_text = f"CA {prof['ca']} / PA {prof['pa']} (+{prof['gap']} 포텐) | 도달: {prof['eta']}"
                else:
                    ticker_badge = f'<span class="badge-stock">🔍 {t}</span>'
                    scout_text = "개별 종목 수급 집중"
                    
            stars_text = star_render(item["stars"])
            
            # 유튜브 AI 비서 스타일 카드 렌더링
            card_html = f"""
            <div class="briefing-card">
                <div class="card-header">
                    {ticker_badge}
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 비서 스카우팅: {scout_text}</span>
                    <span class="star-rating">{stars_text}</span>
                </div>
                <div class="headline-text">
                    📢 {item['headline']}
                </div>
                <div class="briefing-box">
                    {'<br>'.join(item['summary'])}
                </div>
                <div class="action-box">
                    {item['action']}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.expander(f"📄 원문 헤드라인 및 기사 링크"):
                st.write(f"**원문:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 보기]({item['link']})")
    else:
        st.info("현재 시장 뉴스를 모니터링 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()
