import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html
import requests
from bs4 import BeautifulSoup

st.set_page_config(page_title="데일리 AI 주식 비서 - 정밀 실전 브리핑", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    .briefing-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease-in-out;
    }
    .briefing-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 10px 20px -2px rgba(59, 130, 246, 0.12);
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
        font-size: 18px;
        font-weight: 800;
        color: #0f172a;
        margin-bottom: 14px;
        line-height: 1.45;
    }
    
    .story-section {
        background-color: #f8fafc;
        border-left: 4px solid #10b981;
        padding: 16px 20px;
        border-radius: 6px;
        font-size: 14.5px;
        line-height: 1.85;
        color: #1e293b;
        margin-bottom: 14px;
    }
    .story-p {
        margin-bottom: 12px;
    }
    .story-p:last-child {
        margin-bottom: 0px;
    }
    
    .action-container {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        padding: 18px 22px;
        border-radius: 8px;
        font-size: 14px;
        color: #1e3a8a;
        line-height: 1.8;
    }
    
    /* 직관적인 매수/관망/매도 포지션 배지 */
    .signal-badge-buy {
        display: inline-block;
        background-color: #16a34a;
        color: #ffffff;
        font-weight: 800;
        font-size: 13.5px;
        padding: 4px 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .signal-badge-hold {
        display: inline-block;
        background-color: #d97706;
        color: #ffffff;
        font-weight: 800;
        font-size: 13.5px;
        padding: 4px 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .signal-badge-split {
        display: inline-block;
        background-color: #2563eb;
        color: #ffffff;
        font-weight: 800;
        font-size: 13.5px;
        padding: 4px 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .signal-badge-sell {
        display: inline-block;
        background-color: #dc2626;
        color: #ffffff;
        font-weight: 800;
        font-size: 13.5px;
        padding: 4px 12px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    
    .action-item {
        margin-bottom: 7px;
    }
    .action-item:last-child {
        margin-bottom: 0px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📱 데일리 AI 주식 비서: 실시간 가격 & 정밀 매매 가이드")
st.caption("기사 맥락을 명쾌한 한글로 풀고, [매수 추천 / 관망 유지 / 분할 매수] 포지션과 구체적 가격을 직접 제시합니다.")

st.sidebar.header("⚙️ 비서 자동 갱신")
auto_refresh = st.sidebar.toggle("⚡ 60초 주기 자동 브리핑", value=True)

def clamp(val, min_val=1, max_val=200):
    return int(max(min_val, min(val, max_val)))

@st.cache_data(ttl=1800)
def get_stock_price_levels(ticker):
    if not ticker:
        return None
    try:
        sym = "SPY" if ticker == "MACRO" else ticker
        stock = yf.Ticker(sym)
        hist = stock.history(period="6mo")
        full_info = stock.info
        name = full_info.get("shortName", sym) or sym
        
        if hist.empty:
            cur_p = full_info.get("currentPrice", full_info.get("regularMarketPrice", 100.0))
            high_52 = full_info.get("fiftyTwoWeekHigh", cur_p)
            low_52 = full_info.get("fiftyTwoWeekLow", cur_p)
            ma20 = cur_p
        else:
            cur_p = hist['Close'].iloc[-1]
            high_52 = hist['High'].max()
            low_52 = hist['Low'].min()
            ma20 = hist['Close'].tail(20).mean() if len(hist) >= 20 else cur_p
            
        diff_to_high = ((high_52 - cur_p) / cur_p * 100) if cur_p > 0 else 0
        diff_to_ma20 = ((cur_p - ma20) / ma20 * 100) if ma20 > 0 else 0

        buy_target_low = round(ma20 * 0.99, 2)
        buy_target_high = round(ma20 * 1.015, 2)
        stop_loss_price = round(ma20 * 0.965, 2)
        take_profit_price = round(high_52 * 0.98, 2)

        return {
            "symbol": sym,
            "name": name,
            "cur_price": round(cur_p, 2),
            "high_52": round(high_52, 2),
            "low_52": round(low_52, 2),
            "ma20": round(ma20, 2),
            "diff_to_high": round(diff_to_high, 1),
            "diff_to_ma20": round(diff_to_ma20, 1),
            "buy_range": f"${buy_target_low} ~ ${buy_target_high}",
            "stop_loss": stop_loss_price,
            "take_profit": take_profit_price
        }
    except Exception:
        return None

@st.cache_data(ttl=3600)
def fetch_full_article_content(link):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(link, headers=headers, timeout=4)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            paragraphs = soup.find_all('p')
            texts = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30]
            full_body = " ".join(texts[:6])
            if len(full_body) > 80:
                return full_body
    except Exception:
        pass
    return ""

def extract_ticker_refined(title, summary_raw, full_body):
    combined = title + " " + summary_raw + " " + full_body
    
    # 종합 매크로 시황 패턴
    if any(k in combined.lower() for k in ["updates with economic data", "world markets' overview", "stock market today", "wall st", "s&p 500 settles", "nasdaq slides"]):
        return "MACRO"

    # 빅테크 M7
    if any(k in title.lower() for k in ["magnificent seven", "magnificent 7", "m7"]):
        for tk in ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "META", "TSLA"]:
            if tk in combined.upper():
                return tk
        return "NVDA"

    # 산업재(Industrials) 대표 ETF 및 종목
    if "industrials" in title.lower() or "industrial stock" in title.lower():
        for tk in ["CAT", "GE", "HON", "UNP", "DE", "LMT"]:
            if tk in combined.upper():
                return tk
        return "XLI" # 산업재 대표 ETF

    # 금융/은행
    if "bank stock" in title.lower():
        if "bancorp" in combined.lower() or "tbbk" in combined.lower():
            return "TBBK"
        return "KRE"

    # 일반 티커 추출
    m = re.findall(r'\b([A-Z]{2,5})\b', title)
    ignore = ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI", "CPI", "FED", "GDP", "WAR", "OIL", "US", "USA", "ONE", "TWO", "BANK", "STOCK", "WORTH", "AVOID", "LOOK", "DIRT", "SEE", "WHY", "LONG", "TERM", "QUESTION"]
    cands = [x for x in m if x not in ignore]
    if cands:
        return cands[0]
        
    m_cash = re.search(r'\$([A-Z]{1,5})\b', combined)
    if m_cash:
        return m_cash.group(1).upper()
        
    return "MACRO"

# 심층 한글 해설 + 직관적 신호등 배지(매수/관망/매도) 생성 엔진
def make_deep_actionable_briefing(title, summary_raw, full_body, pdata):
    full_context = (title + " " + summary_raw + " " + full_body).lower()

    # 1. 섹터별 선별 리포트 (산업재/은행/소비재: 1개 추천 vs 2개 의문/기피)
    if any(k in full_context for k in ["worth investigating", "we question", "we ignore", "we avoid", "facing headwinds", "better buy", "long-term investors and 2"]):
        sector_name = "산업재(제조·기계·건설)" if "industrial" in full_context else ("금융·은행" if "bank" in full_context else "해당 업종")
        headline = f"🔍 {sector_name} 섹터 점검: 장기 보유할 '알짜 1등주'와 실적 의문으로 '피해야 할 위험주 2개' 선별"
        paragraphs = [
            f"**📌 어떤 소식인가요?**<br>"
            f"월가 전문 분석팀에서 {sector_name} 섹터 내 종목들을 정밀 분석하여, **'지금 사서 장기 투자하기에 완벽한 1등 우량주 1개'**와 **'겉보기엔 유명하지만 실적 둔화와 부채 부담으로 의문(Question)이 제기되는 피해야 할 위험 종목 2개'**를 냉정하게 갈라낸 심층 리포트입니다.",
            
            "**💡 왜 내 주식 계좌에 중요한가요? (원리 풀이)**<br>"
            "경기 사이클을 타는 섹터는 모든 종목이 다 함께 오르지 못합니다. 불황에도 고객 수주 잔고가 꽉 차 있고 자체 현금 창출력이 탄탄한 1등 기업은 경기 침체를 뚫고 신고가를 치지만, 대출 빚이 많거나 마진이 깎이는 2·3등 기업은 주가가 장기간 바닥을 기게 됩니다.<br>"
            "따라서 단순히 '유명한 대형주'라고 무턱대고 사면 안 되며, 리스크가 높은 종목은 덜어내고 확실한 실적주로 포트폴리오를 압축해야 내 원금을 지킬 수 있습니다."
        ]
        
        if pdata:
            if pdata['diff_to_ma20'] > 5.0:
                signal_html = '<span class="signal-badge-hold">🟡 관망 유지 / 단기 매수 자제</span>'
                guide_msg = "현재 주가가 20일선 대비 많이 떠 있는 단기 과열 구간이므로 지금 추격 매수하는 것은 자제해야 합니다."
            else:
                signal_html = '<span class="signal-badge-split">🔵 분할 매수 고려</span>'
                guide_msg = "우량 1등주가 안정 지지선에 위치해 있으므로 무리하지 않는 선에서 분할 진입이 가능한 자리입니다."

            actions = [
                signal_html,
                f"• **현재 주가 상태:** 현재가 **${pdata['cur_price']}** (최근 20일 이평선 ${pdata['ma20']} 대비 {pdata['diff_to_ma20']:+0.1f}%)",
                f"• **실전 매수 가격대:** {guide_msg} 지지선 부근인 **{pdata['buy_range']}**에 걸어두고 2~3회에 나누어 매수하세요.",
                f"• **1차 목표 매도가:** 52주 전고점 부근인 **${pdata['take_profit']}** 도달 시 물량의 절반을 익절하여 수익을 확정하세요.",
                f"• **손절 마지노선:** 단기 지지선이 무너지는 **${pdata['stop_loss']}** 이탈 시에는 종목 교체를 위해 비중을 축소하세요."
            ]
        else:
            actions = [
                '<span class="signal-badge-hold">🟡 관망 유지</span>',
                "• **대응 지침:** 추천된 알짜 1등주의 20일 이동평균선 지지 여부를 먼저 확인한 뒤 분할 매수를 검토하세요."
            ]
        return "⚖️ 종목 선별 리포트", 8, headline, paragraphs, actions

    # 2. 미국 증시 종합 시황 (유가/경제지표 업데이트)
    elif any(k in full_context for k in ["updates with economic data", "recent oil price", "world markets", "corporate stock", "market summary"]):
        headline = "🌐 뉴욕 증시 종합 시황: 최신 경제 지표 발표와 국제 유가 변동에 따른 시장 진단"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "최근 발표된 거시 경제 지표와 국제 원유 가격의 변동, 그리고 글로벌 시장의 마감 흐름을 총망라한 종합 시황 분석입니다. 개별 기업의 이슈가 아니라 시장 전체를 움직이는 '큰손들의 자금 흐름'을 짚어줍니다.",
            
            "**💡 왜 내 주식 계좌에 중요한가요? (원리 풀이)**<br>"
            "내 보유 종목에 악재가 없더라도, 기름값(유가)이 뛰거나 물가 지표가 불안정하면 연준(Fed)의 금리 인하 기대감이 후퇴하며 지수 전체가 조정을 받습니다.<br>"
            "시장의 큰 파도가 어디로 치는지 확인해야 섣부른 뇌동매매를 피하고 안정적인 매수 타이밍을 잡을 수 있습니다."
        ]
        if pdata:
            is_over = pdata['diff_to_ma20'] > 3.0
            signal_html = '<span class="signal-badge-hold">🟡 관망 유지 / 현금 비중 확대</span>' if is_over else '<span class="signal-badge-buy">🟢 지수 분할 매수 유효</span>'
            
            actions = [
                signal_html,
                f"• **현재 시장 지수 상태 (S&P 500 대장주 SPY 기준):** 현재가 **${pdata['cur_price']}** (20일선 대비 {pdata['diff_to_ma20']:+0.1f}%)",
                f"• **오늘 이렇게 행동하세요:** 지수가 방향을 잡기 전까지 무리한 신규 베팅은 자제하시고, 지수 지지 가격대인 **{pdata['buy_range']}**까지 내려올 때만 우량주 위주로 소액 진입하세요.",
                f"• **전고점 및 목표치:** 52주 신고가인 **${pdata['high_52']}** 부근에 근접할수록 현금 비중을 최소 20~30% 확보해 두는 것이 안전합니다."
            ]
        else:
            actions = [
                '<span class="signal-badge-hold">🟡 관망 유지</span>',
                "• **대응 지침:** 나스닥 선물 지수가 안정세를 되찾을 때까지 신규 매수는 쉬어가세요."
            ]
        return "🌐 시장 종합 시황", 8, headline, paragraphs, actions

    # 3. 매그니피센트 7 (M7) 저평가/고평가 분석 기사
    elif any(k in full_context for k in ["magnificent seven", "magnificent 7", "dirt cheap", "some members of the group"]):
        headline = "🚀 매그니피센트 7 빅테크 점검: 실적 대비 '역대급 헐값(Dirt Cheap)' 저평가 알짜주 선별"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "미국 증시를 주도하는 7대 빅테크 종목 중 일부가 시장 전반의 일시적 공포 심리로 인해 **실제 벌어들이는 막대한 이익 대비 주가가 지나치게 싼 바닥권(Dirt Cheap)까지 밀려 내려왔다**는 분석입니다.",
            "**💡 왜 내 주식 계좌에 중요한가요? (원리 풀이)**<br>"
            "실적이 꺾인 부실 기업의 하락은 피해야 하지만, AI 인프라 매출이 계속 늘어나는 1등 우량주의 하락은 반등 시 가장 큰 수익을 안겨주는 '바겐세일' 기회가 됩니다."
        ]
        if pdata:
            signal_html = '<span class="signal-badge-buy">🟢 매수 추천 / 분할 진입</span>'
            actions = [
                signal_html,
                f"• **현재가:** **${pdata['cur_price']}** / **52주 최고가(전고점):** **${pdata['high_52']}** (**+{pdata['diff_to_high']}%** 추가 상승 여력)",
                f"• **추천 매수가:** 한 번에 몰빵하지 마시고, 20일선 부근인 **{pdata['buy_range']}**에 걸어두고 2회에 걸쳐 분할 매수하세요.",
                f"• **오늘 자제할 상황:** 장 시작 후 +3% 이상 급등 출발하면 절대 추격하지 마시고 눌림목을 기다리세요.",
                f"• **1차 익절가 & 손절가:** 전고점 직전인 **${pdata['take_profit']}**에서 절반 익절, 지지선 깨지는 **${pdata['stop_loss']}** 이탈 시 손절."
            ]
        else:
            actions = ['<span class="signal-badge-buy">🟢 분할 매수 추천</span>', "• 우량 빅테크 눌림목 구간 분할 매수 고려."]
        return "🌟 빅테크 정밀분석", 9, headline, paragraphs, actions

    # 4. FDA 승인
    elif any(k in full_context for k in ["fda approval", "fda approves", "cleared"]):
        headline = "🎉 미국 식품의약국(FDA) 신약/의료기기 최종 시판 승인 통과!"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "미국 FDA로부터 최종 판매 허가를 공식 취득했습니다. 바이오 주식 최대 악재인 '개발 실패 리스크'가 소멸하고 정식 유통을 통한 매출 급증 단계로 직결됩니다."
        ]
        if pdata:
            signal_html = '<span class="signal-badge-hold">🟡 추격 매수 자제 / 장중 눌림목 확인</span>'
            actions = [
                signal_html,
                f"• **현재가:** **${pdata['cur_price']}** / **52주 전고점:** **${pdata['high_52']}**",
                f"• **매매 타이밍:** 개장 직후 15분간은 단기 차익 매물이 쏟아지므로 시초가 매수는 절대 자제하세요.",
                f"• **진입 조건:** 15분 이후 시초가 위를 지켜내며 거래량이 300% 이상 유지될 때만 소액 진입하세요."
            ]
        else:
            actions = ['<span class="signal-badge-hold">🟡 관망 유지</span>', "• 장초반 변동성 안정 후 매매 검토."]
        return "🧬 FDA 판매승인", 10, headline, paragraphs, actions

    # 기본 소식
    clean_title = title.replace(" - Yahoo Finance", "")
    headline = f"📢 기업 주요 경영 전략 발표 및 시장 거래 공시"
    paragraphs = [
        f"**📌 어떤 소식인가요?**<br>"
        f"현지 공시를 통해 [{clean_title[:55]}] 관련 소식이 보도되었습니다. 단기 폭등 재료라기보다는 회사가 사업을 정석대로 추진하고 있는지 체질을 확인하는 뉴스입니다."
    ]
    if pdata:
        actions = [
            '<span class="signal-badge-hold">🟡 관망 유지</span>',
            f"• **현재 가격:** **${pdata['cur_price']}** / 52주 전고점 **${pdata['high_52']}**",
            f"• **오늘의 대응:** 대형 호재가 붙은 날이 아니므로 무리한 신규 매수는 자제하시고, 20일선 **${pdata['ma20']}**을 안정적으로 지키는지 관망하는 것이 좋습니다."
        ]
    else:
        actions = ['<span class="signal-badge-hold">🟡 관망 유지</span>', "• 거래량 급증 여부 확인 전까지 매수 자제."]
    return "📢 시장 소식", 6, headline, paragraphs, actions

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
        link = entry.link
        
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            dt_utc = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            dt_kst = dt_utc.astimezone(timezone(timedelta(hours=9)))
            total_seconds = (now_kst - dt_kst).total_seconds()
            
            if total_seconds > 86400:
                continue
                
            diff_hours = int(total_seconds // 3600)
            diff_mins = int((total_seconds % 3600) // 60)
            timestamp_val = dt_kst.timestamp()
            pub_str = f"{dt_kst.strftime('%H:%M')} ({diff_hours}시간 전)" if diff_hours > 0 else f"{dt_kst.strftime('%H:%M')} ({max(1, diff_mins)}분 전)"
        else:
            timestamp_val = now_kst.timestamp()
            pub_str = "방금 전"
            
        full_body = fetch_full_article_content(link)
        ticker = extract_ticker_refined(title, summary_raw, full_body)
        price_data = get_stock_price_levels(ticker)
        
        cat, stars, head_kor, paras, acts = make_deep_actionable_briefing(title, summary_raw, full_body, price_data)
        
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": cat,
            "stars": stars,
            "headline": head_kor,
            "paragraphs": paras,
            "actions": acts,
            "price_data": price_data,
            "original_title": title,
            "link": link
        })
        
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_24h_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 정밀 브리핑:** 최근 24시간 이내 핵심 소식 **{len(news_list)}건** (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            pdata = item["price_data"]
            
            if not t or t == "MACRO":
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로 (S&P 500)</span>'
                scout_text = f"SPY ${pdata['cur_price']} | 전고점 ${pdata['high_52']} (여유 {pdata['diff_to_high']:+0.1f}%)" if pdata else "시장 전체 지수 영향"
            else:
                if pdata:
                    ticker_badge = f'<span class="badge-stock">🔍 {t} (${pdata["cur_price"]})</span>'
                    scout_text = f"전고점 ${pdata['high_52']} (여유 {pdata['diff_to_high']:+0.1f}%) | 20일선 ${pdata['ma20']}"
                else:
                    ticker_badge = f'<span class="badge-stock">🔍 {t}</span>'
                    scout_text = "개별 종목 집중"
                    
            stars_text = star_render(item["stars"])
            paragraphs_html = "".join([f"<div class='story-p'>{p}</div>" for p in item['paragraphs']])
            actions_html = "".join([f"<div class='action-item'>{act}</div>" for act in item['actions']])
            
            card_html = f"""
            <div class="briefing-card">
                <div class="card-header">
                    {ticker_badge}
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 실시간 가격: {scout_text}</span>
                    <span class="star-rating">{stars_text}</span>
                </div>
                <div class="headline-text">
                    {item['headline']}
                </div>
                <div class="story-section">
                    {paragraphs_html}
                </div>
                <div class="action-container">
                    <div class="action-header">💡 오늘 실전 가격 및 매매 가이드</div>
                    {actions_html}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.expander(f"📄 원문 헤드라인 및 기사 보기"):
                st.write(f"**원문 제목:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 원문 바로가기]({item['link']})")
    else:
        st.info("현재 24시간 이내의 실시간 속보를 확인 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()
