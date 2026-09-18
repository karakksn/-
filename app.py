import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html

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
st.caption("개별 종목 호재와 거시경제 이슈를 3일 이내 최신순으로 요약 브리핑합니다.")

st.sidebar.header("⚙️ 실시간 감시")
auto_refresh = st.sidebar.toggle("⚡ 60초 자동 실시간 갱신", value=True)

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
        if cand not in ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI", "CPI", "FED", "GDP", "WAR", "OIL", "US", "USA"]:
            return cand
    return None

# 영문 기사 핵심 내용 2줄 추출 함수
def generate_concise_summary(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 핵심 키워드 판별 및 2줄 요약
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        line1 = "• 미국 FDA 품목 허가 승인으로 신약·의료기기 공식 판매 및 상용화 착수"
        line2 = "• 단기 규제 불확실성 해소 및 즉각적인 신규 매출 파이프라인 가동 기대"
        return "🧬 FDA 승인", 10, "FDA 신약/의료기기 판매 승인 완료", [line1, line2]

    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        line1 = "• 주요 파이프라인 임상 시험에서 목표 효능 입증 및 긍정적 지표 확보"
        line2 = "• 차기 단계 진입 및 글로벌 기술수출(L/O) 계약 가능성 증대"
        return "🧪 임상 성공", 8, "핵심 임상 시험 긍정적 결과 발표", [line1, line2]

    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "유망 기업"
        line1 = f"• [{target[:30]}] 지분 인수 및 합병 계약을 공식 체결"
        line2 = "• 사업 포트폴리오 다각화 및 양사 고객망 통합을 통한 외형 성장 가속화"
        return "🤝 M&A 체결", 9, f"외형 확장을 위한 인수합병(M&A) 단행", [line1, line2]

    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        line1 = "• 대형 고객사 또는 정부 기관과의 장기 제품/솔루션 공급 계약 체결"
        line2 = "• 향후 분기별 매출 가시성 확보 및 안정적 수주 잔고 축적"
        return "💰 수주/계약", 8, "대규모 제품/서비스 공급 수주 계약", [line1, line2]

    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        line1 = "• 분기 실적이 시장 전망치를 상회(Earning Surprise)했거나 가이던스 상향 발표"
        line2 = "• 본업 수익성 개선이 확인되며 주가 밸류에이션 리레이팅 유발"
        return "📈 실적 호재", 8, "시장 예상치 상회 및 가이던스 상향", [line1, line2]

    if any(k in combo for k in ["dividend", "share repurchase", "buyback"]):
        line1 = "• 주주환원을 위한 대규모 자사주 매입 프로그램 또는 배당금 인상 결정"
        line2 = "• 유통 주식수 감소 및 주당순이익(EPS) 제고로 주가 하방 지지력 강화"
        return "🎁 주주환원", 7, "자사주 매입 및 배당 확대 발표", [line1, line2]

    if any(k in combo for k in ["partnership", "partners with", "collaborat", "alliance"]):
        line1 = "• 전략적 파트너사와 공동 기술 개발 및 글로벌 판매망 제휴 계약 체결"
        line2 = "• 단독 진출 한계를 극복하고 신규 시장 진입 속도 단축"
        return "🌐 전략 제휴", 7, "사업 확장을 위한 파트너십 구축", [line1, line2]

    if any(k in combo for k in ["ai", "nvidia", "chip", "semiconductor", "patent"]):
        line1 = "• 차세대 AI·반도체 기술 인프라 채택 또는 주요 핵심 특허 등록 완료"
        line2 = "• 시장 주도 첨단 기술 테마와의 연계성 확대로 기관 수급 유입 기대"
        return "🤖 신기술/AI", 7, "차세대 핵심 기술 및 특허 확보", [line1, line2]

    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        line1 = "• 미국 연준의 기준금리 정책 기조 및 인플레이션(물가) 지표 변화"
        line2 = "• 국채 금리와 달러화 변동에 따라 증시 전반의 유동성 흐름 결정"
        return "🏦 금리/매크로", 9, "연준 통화정책 및 물가 지표 동향", [line1, line2]

    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        line1 = "• 지정학적 요인 또는 원유 감산/증산 결정에 따른 국제 유가 변동"
        line2 = "• 기업 물류비·생산 원가 변동 및 정유/항공 섹터 직접 영향"
        return "🛢️ 유가/에너지", 8, "국제 유가 및 에너지 시장 변동", [line1, line2]

    if any(k in combo for k in ["war", "conflict", "strike", "middle east", "military", "sanction"]):
        line1 = "• 국제 지정학적 분쟁 격화 및 주요 무역/해상 공급망 차질 우려"
        line2 = "• 위험자산 회피 심리 확산과 방산·원자재 안전자산으로의 자금 이동"
        return "⚔️ 지정학 리스크", 9, "글로벌 지정학 위기 및 분쟁 동향", [line1, line2]

    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        line1 = "• 비트코인 등 가상자산 변동성 및 ETF 자금 유출입/규제 관련 소식"
        line2 = "• 디지털 자산 관련주 및 핀테크/투자 심리에 직접적인 연동 반응"
        return "🪙 크립토", 8, "암호화폐 시장 및 관련주 시세 동향", [line1, line2]

    # 기본 추출 (구체적 문장 기반)
    first_sentence = title.replace(" - Yahoo Finance", "")
    line1 = f"• 주요 내용: {first_sentence[:55]} 관련 시장 공시"
    line2 = "• 단기 돌발 재료보다는 정규 사업 진행 및 시장 거래 흐름에 따른 변동"
    return "📢 기업 소식", 6, f"주요 사업 및 거래 동향 업데이트", [line1, line2]

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
            
            # 3일 초과 뉴스 배제
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
        category, stars, kor_title, summary_lines = generate_concise_summary(title, summary_raw)
        
        # 매크로 카테고리인 경우 티커를 MACRO로 통일
        if any(cat_key in category for cat_key in ["금리", "유가", "지정학", "크립토"]):
            ticker = "MACRO"
            
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": category,
            "stars": stars,
            "title_kor": kor_title,
            "summary": summary_lines,
            "original_title": title,
            "link": entry.link
        })
        
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_all_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 수집 현황:** 최근 3일 이내 핵심 뉴스 {len(news_list)}건 (최신순 정렬)")
        
        for item in news_list:
            t = item["ticker"]
            
            if t == "MACRO" or not t:
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로</span>'
                scout_text = "시장 전반 지수 / 섹터 흐름 영향"
            else:
                prof = get_stock_profile(t)
                if prof:
                    ticker_badge = f'<span class="badge-ticker">🔍 {t} ({prof["name"][:10]})</span>'
                    scout_text = f"CA {prof['ca']} / PA {prof['pa']} (+{prof['gap']} 포텐) | 도달: {prof['eta']}"
                else:
                    ticker_badge = f'<span class="badge-ticker">🔍 {t}</span>'
                    scout_text = "개별 종목 수급 집중"
                    
            stars_text = star_render(item["stars"])
            
            card_html = f"""
            <div class="news-card">
                <div class="meta-line">
                    {ticker_badge}
                    <span class="badge-cat">{item['category']}</span>
                    <span class="badge-time">🕒 {item['time']}</span>
                    <span class="badge-scout">📊 잠재력/영향: {scout_text}</span>
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
            
            with st.expander(f"📄 원문 헤드라인 및 기사 링크"):
                st.write(f"**헤드라인:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 보기]({item['link']})")
    else:
        st.info("현재 3일 이내의 시장 뉴스를 탐색 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()