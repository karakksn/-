import streamlit as st
import yfinance as yf
import feedparser
from datetime import datetime, timezone, timedelta
import re
import html

st.set_page_config(page_title="데일리 AI 주식 비서 - 정밀 심층 브리핑", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #f8fafc; color: #0f172a; }
    
    .briefing-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 20px;
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
        line-height: 1.4;
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
        margin-bottom: 10px;
    }
    .story-p:last-child {
        margin-bottom: 0px;
    }
    
    /* 실전 조언 영역 스타일 강화 */
    .action-container {
        background-color: #eff6ff;
        border: 1px solid #bfdbfe;
        border-left: 5px solid #2563eb;
        padding: 16px 20px;
        border-radius: 8px;
        font-size: 14px;
        color: #1e3a8a;
        line-height: 1.75;
    }
    .action-header {
        font-weight: 800;
        font-size: 15px;
        color: #1d4ed8;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .action-item {
        margin-bottom: 6px;
        padding-left: 4px;
    }
    .action-item:last-child {
        margin-bottom: 0px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📱 데일리 AI 주식 비서: 24시간 실시간 심층 브리핑")
st.caption("어려운 경제 용어를 쉬운 괄호 해설로 풀고, 당일 매매 시 꼭 확인해야 할 '상세 실전 대응 전략'을 함께 제시합니다.")

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

# 상세 스토리 + 정밀 실전 조언 생성 엔진
def make_deep_context_briefing(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 코인 / 비트코인 (매크로)
    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        headline = "🪙 비트코인 급변동! 가상자산 시장과 연동 주식들의 동반 슈팅"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "비트코인과 이더리움 등 주요 암호화폐 시세가 강한 변동성을 보이고 있으며, 현물 ETF(증권 시장에서 주식처럼 거래되는 가상자산 펀드)로의 기관 자금 흐름이 급변하고 있습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "가상자산 보유 기업(MSTR 등)이나 채굴·거래소 관련주는 비트코인 가격과 2~3배 이상의 지렛대(레버리지) 효과로 연동됩니다. 코인이 오를 땐 로켓처럼 쏘아 올리지만, 꺾일 땐 주가가 반토막 날 수 있습니다."
        ]
        action_steps = [
            "• **1단계 (선물 차트 확인):** 정규장 진입 전, 비트코인 선물 및 현물 시세가 전고점 저항선이나 직전 24시간 박스권 상단을 뚫고 안착했는지 먼저 확인하세요.",
            "• **2단계 (장초반 뇌동매매 금지):** 미국 장 개장 직후 첫 15~30분은 시초가 갭상승 후 개미 털기(차익 매물 출회)가 가장 심합니다. 시초가 추격 매수는 피하고 지지선 테스트를 기다리세요.",
            "• **3단계 (손절 및 분할 익절 라인):** 코인 관련주는 진입 시 손절선(-4~-5%)을 시스템 매도로 칼같이 걸어두고, 급등 시 1/3씩 분할 익절하여 원금을 확보하는 전략이 필수적입니다."
        ]
        return "🪙 코인/비트코인", 8, headline, paragraphs, action_steps

    # 2. FDA 승인
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        headline = "🎉 미국 식품의약국(FDA) 공식 시판 판매 승인 통과!"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "미국 FDA(식품의약국)로부터 신약 또는 첨단 의료기기에 대한 최종 품목 허가(정식 판매 승인)를 획득했습니다. 개발 실패 위험이 완전히 사라지고 병원 유통이 개시됩니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "바이오 주식에서 가장 치명적인 '임상 탈락' 리스크가 제거되었으며, 이제부터는 연구비만 쓰던 회사에서 제품 판매로 진짜 매출액(통장에 꽂히는 돈)을 벌어들이는 체질 개선이 시작됩니다."
        ]
        action_steps = [
            "• **1단계 (프리마켓 갭 크기 측정):** 프리마켓에서 이미 +30~50% 이상 폭등했다면 추격 매수는 위험합니다. 정규장 개장 후 갭을 메우는 눌림목(조정 구간)이 오는지 관찰하세요.",
            "• **2단계 (거래량 폭발 확인):** 당일 거래량이 5일 평균 거래량의 최소 300% 이상 터지면서 시초가 위를 지켜내는지 확인하세요. 시초가를 깨고 내려가면 '뉴스에 팔아라' 매물 출회 신호입니다.",
            "• **3단계 (목표가 리포트 주시):** 승인 발표 당일 밤부터 대형 투자은행들의 목표주가 상향 리포트가 쏟아지는지 모니터링하여 중기 보유 여부를 판단하세요."
        ]
        return "🧬 FDA 판매승인", 10, headline, paragraphs, action_steps

    # 3. 임상 시험 성공
    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        headline = "🧪 핵심 임상 시험 목표 달성! 신약 탄생에 성큼 다가섰다"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "환자 대상 임상 시험(약효와 부작용을 검증하는 시험)에서 1차 평가지표를 달성하며 통계적 유효성을 입증했습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "후보 물질의 가치가 장부상에 재평가되며, 글로벌 대형 제약사에 수천억 원대 로열티를 받고 권리를 넘기는 L/O(기술수출 계약) 가능성이 급격히 열렸습니다."
        ]
        action_steps = [
            "• **1단계 (데이터 세부 확인):** 단순히 '성공'이라는 단어만 보지 말고, 부작용(이상반응) 비율이 높지 않은지 원문 기사의 세부 지표를 체크하세요.",
            "• **2단계 (재료 소멸 경계):** 임상 발표 직후 급등했다가 윗꼬리를 달고 내려오는 패턴이 빈번합니다. 분봉상 20일 이동평균선을 깨면 단기 차익 실현을 고려하세요.",
            "• **3단계 (차기 일정 확인):** 다음 단계 임상 진입 시점이나 FDA 신청 일정이 언제로 예정되어 있는지 확인하여 보유 호흡을 설정하세요."
        ]
        return "🧪 임상 성공", 8, headline, paragraphs, action_steps

    # 4. 인수합병 (M&A)
    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "업계 유망 기업"
        headline = f"🤝 공격적인 덩치 키우기: [{target[:22]}] 인수합병(M&A) 공식 체결"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            f"회사가 미래 시장 지배력을 강화하기 위해 [{target[:25]}]의 지분을 대규모로 사들이는 M&A(인수합병)를 단행했습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "피인수 회사의 고객 명단과 기술이 오늘 당장 우리 회사 자산이 되며, 다음 분기부터 연결 재무제표(자회사 실적까지 합친 장부)상 매출 규모가 퀀텀점프합니다."
        ]
        action_steps = [
            "• **1단계 (피인수 vs 인수 주체 구분):** 보통 인수당하는 기업의 주가는 즉시 급등하지만, 인수하는 쪽은 막대한 자금 지출 우려로 당일 하락할 수 있습니다. 내가 가진 쪽이 어디인지 확인하세요.",
            "• **2단계 (자금 조달 방식 검토):** 사내 현금으로 샀다면 대형 호재이지만, 대규모 유상증자(주식을 새로 찍어내 주당 가치를 희석하는 방식)가 동반되었다면 단기 악재로 작용합니다.",
            "• **3단계 (독과점 심사 리스크):** 규모가 매우 큰 빅딜인 경우 정부 규제 당국의 반독점 승인 심사 통과 여부를 앞으로 수개월간 체크해야 합니다."
        ]
        return "🤝 대형 M&A", 9, headline, paragraphs, action_steps

    # 5. 대형 수주 / 납품 계약
    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        headline = "💰 거대 고객사와의 장기 대규모 공급 수주 계약 체결"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "정부 기관이나 글로벌 대기업과 장기 제품·서비스 공급 계약을 체결하여 확정 일감을 확보했습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "수주 잔고(향후 매출로 전환될 확정 계약 총액)가 쌓이면서 향후 수년간 실적 침체 우려가 사라져 주가 하방 지지선이 매우 단단해집니다."
        ]
        action_steps = [
            "• **1단계 (매출 대비 계약 규모 확인):** 이번 계약액이 회사 '연간 전체 매출액'의 최소 20~30% 이상을 차지하는지 확인하세요. 비중이 미미하다면 반짝 상승에 그칩니다.",
            "• **2단계 (분할 매수 타이밍):** 수주 뉴스는 하루짜리 반짝 테마가 아니라 실적주로 인정받는 계기이므로, 당일 갭상승을 무리하게 따라가지 말고 2~3일간 눌림목 지지를 확인할 때 분할 매수하세요.",
            "• **3단계 (마진율 훼손 여부):** 저가 출혈 수주가 아닌지, 원자재 가격 상승분을 전가할 수 있는 조건인지 코멘트를 살피세요."
        ]
        return "💰 대형 계약수주", 8, headline, paragraphs, action_steps

    # 6. 실적 서프라이즈 / 가이던스 상향
    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        headline = "📈 어닝 서프라이즈! 시장 예상치를 대폭 깬 역대급 실적 달성"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "분기 실적이 컨센서스(시장 예상치)를 훌쩍 넘겼으며, 경영진이 가이던스(앞으로 벌 돈 목표치)까지 공격적으로 상향했습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "주식 시장에서 '실제 찍힌 순이익'은 가장 확실한 보증수표입니다. 기관들이 목표주가를 올리며 비중을 확대하는 정석적인 우상향 랠리가 시작됩니다."
        ]
        action_steps = [
            "• **1단계 (컨퍼런스콜 핵심 확인):** 숫자뿐 아니라 경영진이 밝힌 '다음 분기 가이던스'가 함께 올랐는지 반드시 확인하세요. 실적이 잘 나와도 가이던스가 낮으면 급락합니다.",
            "• **2단계 (기관 매수세 포착):** 장중 거래대금이 터지면서 대량 체결 블록딜이 매수 우위인지 확인하세요. 대형 펀드의 유입은 3~5일간 지속되는 경향이 있습니다.",
            "• **3단계 (단기 고점 판별):** RSI 지표가 75 이상 과열권에 진입했다면 신규 진입보다는 보유자의 영역으로 보고 조정을 기다리세요."
        ]
        return "📈 실적 서프라이즈", 8, headline, paragraphs, action_steps

    # 7. 금리 / 연준 통화정책 (매크로)
    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        headline = "🏦 미국 중앙은행(연준)의 기준금리 결정 및 물가 지표 발표"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "미국 Fed(연준) 파월 의장의 통화정책 발언이나 CPI(소비자물가지수)가 발표되어 시중 유동성의 향방이 결정되었습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "금리를 내리면 기업들의 이자 부담이 줄고 주식 시장으로 돈이 몰려 기술주가 랠리를 펼치지만, 금리가 동결되거나 인상 기조면 빚 많은 성장주들은 밸류에이션이 깎입니다."
        ]
        action_steps = [
            "• **1단계 (미국채 10년물 금리 체크):** 개별 종목 차트보다 '미국 10년물 국채 금리(^TNX)'가 하락 안정되는지 실시간으로 먼저 확인하세요. 금리가 튀면 나스닥은 무조건 밀립니다.",
            "• **2단계 (현금 비중 조절):** 파월 의장의 기자회견 당일에는 지수가 분 단위로 요동치므로, 포트폴리오의 최소 20~30%는 현금으로 확보해 두는 것이 안전합니다.",
            "• **3단계 (피벗 수혜 섹터 선점):** 금리 인하 기대감이 커질 경우 중소형주(러셀2000)와 바이오, 고배당 리츠 섹터의 반등 탄력이 가장 먼저 반응합니다."
        ]
        return "🏦 금리/물가 매크로", 9, headline, paragraphs, action_steps

    # 8. 유가 / 원유 (매크로)
    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        headline = "🛢️ 국제 유가 급등락! 에너지 수급 불안과 증시 파급 효과"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "OPEC의 감산 결정이나 지정학적 분쟁으로 인해 국제 원유(WTI) 가격이 급변동하고 있습니다.",
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "기름값이 오르면 전 산업의 물류비와 생산 비용이 증가해 인플레이션을 자극하지만, 원유를 직접 시추해 파는 에너지 기업들에게는 막대한 횡재 이익이 돌아갑니다."
        ]
        action_steps = [
            "• **1단계 (섹터별 차별화 대응):** 항공, 운송, 화학주 등 원가 부담이 큰 섹터는 비중을 축소하고, 정유/에너지 섹터(XLE)는 헷지(위험 방어) 수단으로 단기 트레이딩하세요.",
            "• **2단계 (유가 $85~$90 저항선 관찰):** WTI 유가가 주요 심리적 저항선을 상방 돌파하는지 체크하세요. 저항선을 뚫으면 증시 전반에 인플레이션 쇼크가 재발합니다.",
            "• **3단계 (달러 인덱스 병행 체크):** 유가 상승과 함께 달러 강세가 동반되는지 확인하여 신흥국 및 기술주의 자금 유출 강도를 가늠하세요."
        ]
        return "🛢️ 유가/원자재", 8, headline, paragraphs, action_steps

    # 기본 소식 (상세 가이드)
    clean_title = title.replace(" - Yahoo Finance", "").replace("Yahoo Finance", "")
    headline = "📢 기업 주요 경영 전략 발표 및 시장 소식"
    paragraphs = [
        f"**📌 어떤 소식인가요?**<br>"
        f"현지 언론을 통해 [{clean_title[:55]}] 관련 주요 기업 동향이 보도되었습니다. 사업 방향성을 시장과 공유하는 정규 공시입니다.",
        "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
        "당장 주가가 상한가를 치는 초대형 사고는 아니지만, 회사가 착실히 본업 경쟁력을 다져가고 있는지 방향성을 확인하는 건강한 신호입니다."
    ]
    action_steps = [
        "• **1단계 (거래량 검증):** 오늘 거래량이 평소의 1.5배 이상 동반되지 않는다면 단순 단기 소음(Noise)일 수 있으니 추격 매수를 자제하세요.",
        "• **2단계 (핵심 지지선 점검):** 일봉상 20일선 및 60일 이동평균선 위에 주가가 안착해 있는지 기술적 추세를 먼저 확인하세요.",
        "• **3단계 (분할 매매 원칙):** 확신이 서지 않는 뉴스는 한 번에 몰빵하지 마시고, 3번에 나누어 분할 매수하는 보수적인 접근을 유지하세요."
    ]
    return "📢 기업 소식", 6, headline, paragraphs, action_steps

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
        
        # 24시간 이내 필터링
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
        category, stars, headline_kor, paragraphs_list, action_steps = make_deep_context_briefing(title, summary_raw)
        
        if any(cat_key in category for cat_key in ["금리", "유가", "코인"]):
            ticker = "MACRO"
            
        news_items.append({
            "ticker": ticker,
            "timestamp": timestamp_val,
            "time": pub_str,
            "category": category,
            "stars": stars,
            "headline": headline_kor,
            "paragraphs": paragraphs_list,
            "actions": action_steps,
            "original_title": title,
            "link": entry.link
        })
        
    news_items.sort(key=lambda x: x["timestamp"], reverse=True)
    return news_items

@st.fragment(run_every="60s" if auto_refresh else None)
def render_news_dashboard():
    news_list = fetch_24h_market_news()
    
    if news_list:
        st.write(f"⏱️ **실시간 정밀 브리핑:** 최근 24시간 이내 핵심 소식 **{len(news_list)}건** 감지 (최신순)")
        
        for item in news_list:
            t = item["ticker"]
            
            if t == "MACRO" or not t:
                ticker_badge = '<span class="badge-macro">🌍 글로벌 매크로</span>'
                scout_text = "시장 전체 지수 및 업종별 분위기에 영향"
            else:
                prof = get_stock_profile(t)
                if prof:
                    ticker_badge = f'<span class="badge-stock">🔍 {t} ({prof["name"][:10]})</span>'
                    scout_text = f"실력(CA) {prof['ca']} / 잠재력(PA) {prof['pa']} (+{prof['gap']}점 여유) | 예상: {prof['eta']}"
                else:
                    ticker_badge = f'<span class="badge-stock">🔍 {t}</span>'
                    scout_text = "개별 기업 뉴스에 수급 집중"
                    
            stars_text = star_render(item["stars"])
            paragraphs_html = "".join([f"<div class='story-p'>{p}</div>" for p in item['paragraphs']])
            actions_html = "".join([f"<div class='action-item'>{act}</div>" for act in item['actions']])
            
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
                <div class="story-section">
                    {paragraphs_html}
                </div>
                <div class="action-container">
                    <div class="action-header">💡 오늘 실전 대응 가이드 (체크포인트)</div>
                    {actions_html}
                </div>
            </div>
            """
            st.markdown(card_html, unsafe_allow_html=True)
            
            with st.expander(f"📄 현지 영문 원문 기사 및 링크 확인"):
                st.write(f"**원문 헤드라인:** {item['original_title']}")
                st.markdown(f"[🔗 야후 파이낸스 기사 원문 바로가기]({item['link']})")
    else:
        st.info("현재 24시간 이내의 실시간 속보를 확인 중입니다. 잠시 후 자동으로 갱신됩니다.")

render_news_dashboard()
