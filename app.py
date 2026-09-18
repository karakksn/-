import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html

st.set_page_config(page_title="데일리 AI 주식 비서 - 24시간 실시간 브리핑", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    .briefing-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 20px 24px;
        margin-bottom: 18px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    .briefing-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 10px 18px -2px rgba(59, 130, 246, 0.12);
    }
    
    .card-header {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 14px;
        padding-bottom: 10px;
        border-bottom: 1px solid #f1f5f9;
    }
    
    .badge-stock {
        background-color: #0f172a;
        color: #ffffff;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 6px;
        font-size: 13px;
    }
    .badge-macro {
        background-color: #4338ca;
        color: #ffffff;
        font-weight: 800;
        padding: 5px 12px;
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
        padding: 4px 10px;
        border-radius: 6px;
        margin-left: auto;
    }
    
    .headline-text {
        font-size: 17px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 12px;
    }
    
    .explain-box {
        background-color: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 14px 18px;
        border-radius: 6px;
        font-size: 14px;
        line-height: 1.8;
        color: #1e293b;
        margin-bottom: 10px;
    }
    
    .action-box {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 10px 16px;
        border-radius: 6px;
        font-size: 13.5px;
        color: #1d4ed8;
        font-weight: 600;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📱 데일리 AI 주식 비서: 24시간 실시간 브리핑")
st.caption("최근 24시간 이내의 핵심 뉴스를 어려운 주식용어 뒤에 쉬운 풀이(괄호 해설)를 달아 직관적으로 설명해 드립니다.")

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

# 어려운 주식용어 뒤에 (쉬운 풀이)를 덧붙여주는 브리핑 생성 엔진
def make_easy_story_briefing(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 비교/선별형 기사 (예: 1 Bank Stock Worth Investigating and 2 We Ignore)
    if any(k in combo for k in ["worth investigating", "stocks to buy and", "we ignore", "avoid", "facing headwinds", "better buy"]):
        headline = "🔍 알짜 유망주 vs 지금 피해야 할 종목 비교 분석"
        explains = [
            "• **무슨 일인가요?** 같은 업종 안에서도 돈을 잘 버는 똘똘한 1등 기업과, 겉만 멀쩡하고 위험한 종목을 가려낸 리포트(증권사 분석 보고서)가 나왔습니다.",
            "• **쉽게 이해하기:** 단순 대출 이자만 받아서는 남는 게 별로 없습니다. 핀테크 수수료처럼 다른 곳에서 쏠쏠하게 돈을 잘 벌며 ROE(투자한 내 돈 대비 얼마나 순이익을 냈는지 보는 수익률)가 30%가 넘는 회사는 유망하지만, 금리가 흔들릴 때 NIM(순이자마진, 대출 이자에서 예금 이자를 뺀 순마진)이 줄어들며 타격을 입는 평범한 지방 은행들은 지금 피하는 게 안전합니다."
        ]
        action = "💡 오늘 이렇게 보세요: 내 계좌에 단순히 남들이 사서 따라 산 종목이 있는지 점검하고, 펀더멘털(기업의 기초 체력과 돈 버는 능력)이 튼튼한 알짜 회사 위주로 압축할 타이밍입니다."
        return "⚖️ 종목 선별", 8, headline, explains, action

    # 2. FDA 승인
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        headline = "🎉 미국 정부(FDA) 공식 판매 허가 승인 통과!"
        explains = [
            "• **무슨 일인가요?** 까다롭기로 유명한 미국 FDA(식품의약국, 미국의 의약품 허가 기관)에서 신약이나 의료기기를 정식으로 판매해도 좋다는 최종 허가를 내줬습니다.",
            "• **쉽게 이해하기:** 바이오 주식에서 가장 무서운 건 '약 개발 실패' 리스크(위험 요소)인데, 그 거대한 불확실성이 완전히 끝났습니다. 이제 병원과 약국에 깔리면서 회사 통장에 진짜 매출(제품을 팔아 번 돈)이 꽂히기 시작하므로 주가 상승 탄력이 매우 큽니다."
        ]
        action = "💡 오늘 이렇게 보세요: 장 시작하자마자 갭상승(전날 종가보다 훨씬 높게 시초가가 시작되는 현상)이 나타날 수 있습니다. 쫓아가며 급하게 사기보다는 기관(전문 투자 펀드)들의 수급(주식을 사 모으는 자금 유입)이 계속 이어지는지 지켜보세요."
        return "🧬 FDA 판매승인", 10, headline, explains, action

    # 3. 임상 시험 성공
    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        headline = "🧪 환자 대상 약효 시험 성공! 상용화 한 걸음 앞"
        explains = [
            "• **무슨 일인가요?** 개발 중인 신약을 실제 환자들에게 투여해 본 임상 시험(약의 안전성과 치료 효과를 실제 사람에게 검증하는 시험)에서 뚜렷한 약효가 확인되었습니다.",
            "• **쉽게 이해하기:** 신약 시험은 도중에 엎어지는 경우가 태반인데, 큰 고비를 넘겼습니다. 다른 거대 글로벌 제약사들이 눈독을 들이며 기술을 비싼 값에 사가겠다고 손을 내미는 L/O(기술수출, 신약 기술을 다른 제약사에 로열티를 받고 파는 계약) 가능성이 아주 높아졌습니다."
        ]
        action = "💡 오늘 이렇게 보세요: 기대감으로 단기 급등할 수 있습니다. 발표 직후 반짝 오르고 차익실현(이익을 보고 주식을 팔아 현금화하는 매물)이 쏟아질 수 있으니 다음 시험 일정이나 파트너십 소식을 함께 체크하세요."
        return "🧪 임상 시험 성공", 8, headline, explains, action

    # 4. 인수합병 (M&A)
    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "유망 기업"
        headline = f"🤝 덩치 키우기: [{target[:20]}] 기업 전격 인수!"
        explains = [
            "• **무슨 일인가요?** 회사가 시장에서 경쟁력을 높이기 위해 다른 유망한 회사를 사들이는 M&A(인수합병, 다른 기업의 지분을 사들여 내 식구로 만드는 것) 계약을 공식 체결했습니다.",
            "• **쉽게 이해하기:** 새로운 시장에 맨땅에 헤딩하며 들어가는 대신, 이미 잘나가는 업체를 통째로 흡수한 것입니다. 그 회사가 갖고 있던 고객 명단과 기술이 즉시 합산되어 연결 재무제표(자회사 실적까지 합친 회계 장부)에 매출이 크게 불어납니다."
        ]
        action = "💡 오늘 이렇게 보세요: 회사를 인수하느라 무리하게 빚을 냈는지, 아니면 유상증자(주식을 새로 찍어내 주주 돈을 빌려 주당 가치를 떨어뜨리는 일) 없이 회사 금고의 현금으로 알뜰하게 잘 샀는지 조건을 살피는 것이 핵심입니다."
        return "🤝 회사 인수합병", 9, headline, explains, action

    # 5. 대형 수주 / 공급 계약
    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        headline = "💰 대형 고객사로부터 대규모 납품 계약 따냈다!"
        explains = [
            "• **무슨 일인가요?** 대기업이나 정부 기관에 대량으로 물건이나 서비스를 공급하기로 정식 수주(제품 공급 주문을 따내는 것) 계약 도장을 찍었습니다.",
            "• **쉽게 이해하기:** 장사하는 사람 입장에서 '앞으로 몇 년 동안 꾸준히 팔릴 대형 일감'을 미리 확보한 것과 같습니다. 수주 잔고(앞으로 납품해서 돈으로 바뀔 계약 일감 총액)가 쌓여 실적이 꺾일 걱정이 사라지므로 주가에 든든한 바닥이 형성됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 이번 계약 금액이 이 회사 한 해 전체 매출액(1년간 벌어들인 총금액)의 몇 %를 차지할 정도로 거대한 규모인지 확인하면 주가가 얼마나 강하게 반응할지 가늠할 수 있습니다."
        return "💰 대형 계약 수주", 8, headline, explains, action

    # 6. 실적 호재 / 서프라이즈
    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        headline = "📈 어닝 서프라이즈: 예상보다 돈을 훨씬 더 많이 벌었다!"
        explains = [
            "• **무슨 일인가요?** 지난 분기에 회사가 실제로 벌어들인 돈이 컨센서스(시장 증권사 전문가들의 평균 예상치)를 훌쩍 뛰어넘는 어닝 서프라이즈(깜짝 호실적)를 기록했습니다. 심지어 회사 경영진이 가이던스(기업이 스스로 밝힌 앞으로 벌 돈 목표치)까지 상향 조정했습니다.",
            "• **쉽게 이해하기:** 말만 번지르르한 게 아니라 통장에 찍힌 진짜 영업이익(본업 장사로 순수하게 남긴 알짜 이익)으로 실력을 증명했습니다. 주식 시장에서 기관 투자자들의 자금이 가장 안심하고 들어오는 최고의 호재입니다."
        ]
        action = "💡 오늘 이렇게 보세요: 실적이 좋으면 기관(펀드 매니저)들이 며칠에 걸쳐 꾸준히 사 모으기 때문에 냄비처럼 하루 만에 식지 않고 안정적으로 우상향(주가가 계단식으로 오르는 흐름)하는지 관찰하세요."
        return "📈 깜짝 실적 호재", 8, headline, explains, action

    # 7. 금리 / 연준 (매크로)
    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        headline = "🏦 미국 중앙은행(연준) 금리 및 물가 소식"
        explains = [
            "• **무슨 일인가요?** 미국 기준금리(중앙은행이 정하는 돈의 기본 이자율)를 결정하는 Fed(연준, 미국의 중앙은행) 파월 의장의 발언이나 CPI(소비자물가지수, 물가가 얼마나 올랐는지 보는 지표)가 발표되었습니다.",
            "• **쉽게 이해하기:** 금리는 '돈의 가격'입니다. 금리를 내리면 은행 예금 대신 주식 시장으로 돈이 몰리고 기업들의 대출 이자 부담이 줄어들어 주가가 오르지만, 금리를 내리지 않고 버티면 부채(빚)가 많은 기술 성장주들은 주가가 짓눌리게 됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 개별 주식의 잘못이 아니라 시장 전체가 출렁이는 매크로(거시 경제 환경) 이슈이므로, 나스닥 지수 선물이 안정되는지 먼저 확인하고 매매하세요."
        return "🏦 금리/물가 이슈", 9, headline, explains, action

    # 8. 유가 / 원유 (매크로)
    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        headline = "🛢️ 기름값(국제 유가) 요동: 내 주식엔 어떤 영향이?"
        explains = [
            "• **무슨 일인가요?** 중동 분쟁이나 OPEC(석유수출국기구, 산유국 모임)의 원유 감산(기름 생산량을 줄이는 것) 정책으로 국제 유가가 출렁이고 있습니다.",
            "• **쉽게 이해하기:** 기름값이 오르면 공장 가동 비용, 항공유, 화물 운송비가 전부 올라 인플레이션(물가가 전반적으로 치솟는 현상)을 다시 자극합니다. 일반 기업들에게는 비용 부담이지만, 원유를 직접 캐서 파는 정유/에너지 주식에는 호재가 됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 항공주나 일반 제조업 주식은 잠시 숨고르기에 들어갈 수 있고, 에너지 섹터(관련 업종 주식 묶음) 쪽으로 매수세가 쏠리는지 확인하세요."
        return "🛢️ 유가/기름값", 8, headline, explains, action

    # 9. 암호화폐 / 비트코인
    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        headline = "🪙 비트코인 급등락: 코인 관련 주식도 함께 흔들린다"
        explains = [
            "• **무슨 일인가요?** 비트코인 시세가 급격히 움직이거나 현물 ETF(거래소에 상장되어 주식처럼 사고파는 펀드) 자금 유출입 소식이 전해졌습니다.",
            "• **쉽게 이해하기:** 비트코인을 회사 금고에 잔뜩 사 모아둔 기업이나 코인 거래소 주식들은 가상자산 시세와 커플링(두 자산의 가격이 똑같이 연동되어 움직이는 현상)됩니다. 코인이 오르면 이들 주가도 함께 폭발합니다."
        ]
        action = "💡 오늘 이렇게 보세요: 변동성(주가가 위아래로 출렁이는 폭)이 매우 크기 때문에 무리하게 추격매수(오르는 주식을 급하게 따라 사는 것)하지 마시고 비트코인이 주요 지지선을 지켜주는지 먼저 확인하세요."
        return "🪙 코인/비트코인", 8, headline, explains, action

    # 기본 소식
    clean_title = title.replace(" - Yahoo Finance", "").replace("Yahoo Finance", "")
    headline = "📢 회사 주요 경영 업데이트 및 시장 소식"
    explains = [
        f"• **무슨 일인가요?** {clean_title[:55]} 관련 뉴스가 전해졌습니다.",
        "• **쉽게 이해하기:** 오늘 당장 주가가 폭등하는 급등 재료라기보다는, 회사가 사업을 진행하면서 시장에 소식을 알리는 정규 공시(기업의 주요 내용을 투자자에게 공식 발표하는 것)입니다. 기업의 기초 체력을 확인하는 용도로 읽으시면 좋습니다."
    ]
    action = "💡 오늘 이렇게 보세요: 평소 거래량(주식이 사고팔린 수량)보다 갑자기 2~3배 이상 많은 거래가 터지는지 호가창을 가볍게 체크해 보세요."
    return "📢 기업 소식", 6, headline, explains, action

def star_render(stars):
    full = "★" * stars
    empty = "☆" * (10 - stars)
    return f"{full}{empty} ({stars}/10점)"

def fetch_24h_market_news():
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
        
        # 24시간(1일 = 86,400초) 초과 과거 뉴스는 자동 배제
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
            total_seconds = (now_kst - dt_kst).total_seconds()
            
            if total_seconds > 86400:
                continue
                
            diff_hours = int(total_seconds // 3600)
            diff_mins = int((total_seconds % 3600) // 60)
            timestamp_val = dt_kst.timestamp()
            
            if diff_hours == 0:
                time_ago = f"{max(1, diff_mins)}분 전"
            else:
                time_ago = f"{diff_hours}시간 전"
                
            pub_str = f"{dt_kst.strftime('%H:%M')} ({time_ago})"
        else:
            timestamp_val = now_kst.timestamp()
            pub_str = "방금 전"
            
        ticker = extract_ticker(title)
        category, stars, headline_kor, explains_list, action_guide = make_easy_story_briefing(title, summary_raw)
        
        if any(cat_key in category for cat_key in ["금리", "유가", "코인"]):
            ticker = "MACRO"
            
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": category,
            "stars": stars,
            "headline": headline_kor,
            "explains": explains_list,
            "action": action_guide,
            "original_title": title,
            "link": entry.link
        })
        
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_24h_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 브리핑 현황:** 최근 24시간(1일) 이내 발생한 핵심 소식 **{len(news_list)}건** 감지 (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            
            if t == "MACRO" or not t:
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로</span>'
                scout_text = "시장 전체 지수 / 섹터 분위기에 영향"
            else:
                prof = get_stock_profile(t)
                if prof:
                    ticker_badge = f'<span class="badge-stock">🔍 {t} ({prof["name"][:10]})</span>'
                    scout_text = f"실력(CA) {prof['ca']} / 잠재력(PA) {prof['pa']} (+{prof['gap']}점 여유) | 예상: {prof['eta']}"
                else:
                    ticker_badge = f'<span class="badge-stock">🔍 {t}</span>'
                    scout_text = "개별 종목에 관심 집중"
                    
            stars_text = star_render(item["stars"])
            
            card_html = f"""
            <div class="briefing-card">
                <div class="card-header">
                    {ticker_badge}
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 비서 진단: {scout_text}</span>
                    <span class="star-rating">{stars_text}</span>
                </div>
                <div class="headline-text">
                    {item['headline']}
                </div>
                <div class="explain-box">
                    {'<br><br>'.join(item['explains'])}
                </div>
                <div class="action-box">
                    {item['action']}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.expander(f"📄 현지 영문 원문 기사 확인"):
                st.write(f"**원문 제목:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 전문 보기]({item['link']})")
    else:
        st.info("현재 24시간 이내의 실시간 속보를 확인 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()
