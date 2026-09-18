import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html

st.set_page_config(page_title="실시간 뉴스 호재 & 마켓 레이더", layout="wide")

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
        border-left: 4px solid #3b82f6;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 13.5px;
        color: #1e293b;
        line-height: 1.7;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🔥 실시간 뉴스 호재 & 시장 핵심 레이더")
st.caption("어려운 금융 용어 대신, 어떤 종목을 왜 주목/조심해야 하는지 직관적인 2줄 해설로 브리핑합니다.")

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
        if cand not in ["FDA", "CEO", "CFO", "SEC", "NEW", "FOR", "THE", "AND", "TOP", "ALL", "AI", "CPI", "FED", "GDP", "WAR", "OIL", "US", "USA", "ONE", "TWO"]:
            return cand
    return None

# 쉽고 직관적인 2줄 요약 (추천/비추천 및 명확한 이유)
def generate_intuitive_summary(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 비교/선별형 기사 (예: 1 Bank Stock Worth Investigating and 2 We Ignore)
    if any(k in combo for k in ["worth investigating", "stocks to buy and", "we ignore", "avoid", "facing headwinds", "better buy"]):
        line1 = "• 🟢 주목 종목: 차별화된 사업 모델과 높은 수익성(고ROE)을 갖춰 지금 파고들 만한 유망주."
        line2 = "• 🔴 주의 종목: 시장 금리나 경기 침체에 취약해 실적 타격을 입기 쉬운 일반 기업은 배제 권고."
        return "⚖️ 종목 선별 리포트", 8, "주목할 알짜주와 지금 피해야 할 종목 비교 분석", [line1, line2]

    # 2. FDA 승인 / 바이오 호재
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        line1 = "• 🟢 추천/호재: 미국 정부(FDA)로부터 약품·기기 공식 판매 허가를 따냈습니다."
        line2 = "• 💡 이유: 허가가 떨어지면 곧바로 병원에 납품되고 판매 매출이 찍히기 때문에 주가가 가장 빠르게 튑니다."
        return "🧬 FDA 승인", 10, "FDA 최종 품목 허가 승인 통과", [line1, line2]

    # 3. 임상 시험 성공
    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        line1 = "• 🟢 추천/호재: 환자 대상 핵심 임상 시험에서 약효와 안전성을 입증했습니다."
        line2 = "• 💡 이유: 개발 실패 위험이 크게 줄어들고 다른 글로벌 대형 제약사에 기술을 비싸게 팔 수 있는 길이 열렸습니다."
        return "🧪 임상 성공", 8, "핵심 파이프라인 임상 목표 달성", [line1, line2]

    # 4. 인수합병 (M&A)
    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "유망 기업"
        line1 = f"• 🟢 호재/확장: 다른 유망 기업([{target[:20]}])을 통째로 인수해 덩치를 키웠습니다."
        line2 = "• 💡 이유: 그 회사가 갖고 있던 기술과 고객 명단을 그대로 흡수해 단기간에 매출이 급증하는 효과가 생깁니다."
        return "🤝 M&A 체결", 9, "외형 성장을 위한 대규모 인수합병", [line1, line2]

    # 5. 대형 수주 / 공급 계약
    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        line1 = "• 🟢 추천/호재: 대기업이나 정부로부터 대규모 납품/공급 계약을 따냈습니다."
        line2 = "• 💡 이유: 몇 분기 동안 꾸준히 들어올 돈(확정 매출)이 생겨 회사의 실적 신뢰도가 매우 높아집니다."
        return "💰 대형 수주", 8, "대규모 제품/서비스 공급 수주 확보", [line1, line2]

    # 6. 실적 호재 / 가이던스 상향
    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        line1 = "• 🟢 추천/호재: 지난 분기 돈을 예상보다 훨씬 많이 벌었고, 앞으로 더 벌겠다고 발표했습니다."
        line2 = "• 💡 이유: 기업의 실제 이익이 탄탄하게 받쳐주면 기관 투자자들의 매수세가 계속 이어져 안정적으로 오릅니다."
        return "📈 실적 서프라이즈", 8, "시장 예상치 상회 및 성장 목표 상향", [line1, line2]

    # 7. 주주환원 (자사주 매입 / 배당 인상)
    if any(k in combo for k in ["dividend", "share repurchase", "buyback"]):
        line1 = "• 🟢 호재: 회사 돈으로 자기 주식을 사서 없애거나(자사주 소각), 배당금을 올려주기로 했습니다."
        line2 = "• 💡 이유: 시장에 돌아다니는 주식 수가 줄어들어 주당 가치가 올라가고 주가가 떨어지지 않게 받쳐줍니다."
        return "🎁 주주환원", 7, "자사주 매입 및 배당금 확대", [line1, line2]

    # 8. 전략 제휴 / 파트너십
    if any(k in combo for k in ["partnership", "partners with", "collaborat", "alliance"]):
        line1 = "• 🟢 호재: 거대 파트너 기업과 손을 잡고 시장 진출을 함께하기로 했습니다."
        line2 = "• 💡 이유: 혼자서 뚫기 힘든 글로벌 판매망을 빌려 쓸 수 있어 신규 시장 개척 속도가 훨씬 빨라집니다."
        return "🌐 전략 제휴", 7, "글로벌 대기업과 전략적 파트너십", [line1, line2]

    # 9. AI 및 반도체 신기술
    if any(k in combo for k in ["ai", "nvidia", "chip", "semiconductor", "patent"]):
        line1 = "• 🟢 주목: 시장에서 가장 인기 있는 AI 반도체 생태계에 참여하거나 독점 특허를 냈습니다."
        line2 = "• 💡 이유: 최신 테마의 중심에 서면서 시장의 유동성 수급이 한 번에 몰려 단기 급등 탄력이 커집니다."
        return "🤖 AI/신기술", 7, "차세대 핵심 기술 도입 및 특허 확보", [line1, line2]

    # 10. 금리 / 연준 (매크로)
    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        line1 = "• 🌍 시장 변수: 미국 중앙은행(연준)의 기준금리 및 물가 지표에 대한 결정입니다."
        line2 = "• 💡 이유: 금리를 내리면 시장에 돈이 풀려 주가가 오르지만, 금리를 유지하면 빚 많은 기업들이 부담을 느낍니다."
        return "🏦 금리/연준", 9, "미국 기준금리 정책 및 물가 지표 동향", [line1, line2]

    # 11. 유가 / 원유 (매크로)
    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        line1 = "• 🌍 시장 변수: 산유국의 감산이나 전쟁 우려로 국제 유가가 출렁이고 있습니다."
        line2 = "• 💡 이유: 기름값이 오르면 물가가 다시 뛰어 증시에 악재가 되지만, 에너지/정유 기업 주가에는 호재가 됩니다."
        return "🛢️ 유가/에너지", 8, "국제 유가 및 에너지 원자재 동향", [line1, line2]

    # 12. 전쟁 / 지정학 (매크로)
    if any(k in combo for k in ["war", "conflict", "strike", "middle east", "military", "sanction"]):
        line1 = "• 🔴 리스크: 중동이나 동유럽 등 국제 분쟁이 격화되며 위험 회피 심리가 커졌습니다."
        line2 = "• 💡 이유: 주식 같은 위험자산에서 돈이 빠져나가 금이나 달러로 숨기 때문에 방산주를 제외한 증시가 흔들릴 수 있습니다."
        return "⚔️ 지정학 리스크", 9, "국제 분쟁 고조 및 안전자산 선호", [line1, line2]

    # 13. 비트코인 / 크립토 (매크로)
    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        line1 = "• 🪙 코인 변수: 비트코인 시세 급변동 및 현물 ETF 자금 흐름 소식입니다."
        line2 = "• 💡 이유: 코인 시장에 돈이 몰리면 관련 보유 기업과 거래소 주가가 크게 뛰고 시장 전반의 투자 심리를 자극합니다."
        return "🪙 크립토", 8, "암호화폐 시장 및 관련주 시세 흐름", [line1, line2]

    # 기본 (추출 문장 기반 쉬운 2줄 설명)
    clean_title = title.replace(" - Yahoo Finance", "").replace("Yahoo Finance", "")
    line1 = f"• 📢 주요 소식: {clean_title[:50]} 관련 최신 이슈가 전해졌습니다."
    line2 = "• 💡 이유: 즉각적인 주가 폭발보다는 회사의 중장기 체질 변화나 업계 흐름을 파악하는 데 참고할 소식입니다."
    return "📢 기업 소식", 6, "주요 기업 동향 및 시장 이슈", [line1, line2]

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
            
            # 3일(72시간) 초과 과거 뉴스 자동 필터링
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
        category, stars, kor_title, summary_lines = generate_intuitive_summary(title, summary_raw)
        
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
        st.write(f"⏱️ **실시간 수집 현황:** 최근 3일 이내 핵심 뉴스 {len(news_list)}건 (최신순)")
        
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
