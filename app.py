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
        margin-bottom: 12px;
    }
    
    .story-p {
        margin-bottom: 10px;
    }
    .story-p:last-child {
        margin-bottom: 0px;
    }
    
    .action-box {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        padding: 12px 18px;
        border-radius: 6px;
        font-size: 14px;
        color: #1d4ed8;
        font-weight: 600;
        line-height: 1.6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📱 데일리 AI 주식 비서: 24시간 실시간 심층 브리핑")
st.caption("단순 요약이 아닌, 사건의 전후 맥락과 왜 주가에 중요한지 초보자의 눈높이에 맞춰 상세하고 깊이 있게 해설합니다.")

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

# 상세하고 명확한 맥락 중심의 심층 스토리 브리핑 생성 엔진
def make_deep_context_briefing(title, summary_raw):
    clean_text = re.sub(r'<[^>]+>', '', summary_raw or '')
    clean_text = html.unescape(clean_text).strip()
    combo = (title + " " + clean_text).lower()

    # 1. 종목 비교 / 선별 리포트 (예: 1 Bank Stock Worth Investigating...)
    if any(k in combo for k in ["worth investigating", "stocks to buy and", "we ignore", "avoid", "facing headwinds", "better buy"]):
        headline = "🔍 같은 업종 내 '알짜 기업'과 '지금 피해야 할 위험 종목' 선별 분석"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "증권가 전문 분석팀에서 같은 섹터(동일 업종 묶음)에 속해 있더라도 돈 버는 실력에 따라 종목의 운명이 완전히 갈리고 있다는 심층 보고서를 내놓았습니다. 겉보기엔 비슷한 회사 같지만, 내부를 뜯어보면 지금 당장 포트폴리오(내 보유 주식 구성)에 담아야 할 진짜 알짜 기업과, 리스크(위험 요소)가 커서 쳐다보지 말아야 할 종목을 냉정하게 구분했습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "보통 은행이나 금융사를 예로 들면, 일반 사람들은 단순히 '예금 받아서 대출해 주고 이자 남기는(예대마진)' 평범한 지방 은행들을 떠올립니다. 하지만 금리가 변동할 때 이런 단순한 회사들은 NIM(순이자마진, 대출 이자에서 예금 이자를 빼고 실제로 손에 쥐는 알짜 마진율)이 쪼그라들고 대출 연체 위험이 커져 큰 타격을 입습니다.<br>"
            "반면, 추천된 유망 기업은 대출 이자에만 목매지 않고 '핀테크 앱이나 결제 시스템을 빌려주고 수수료'를 꼬박꼬박 챙기며, ROE(자기자본이익률, 투자된 내 돈 대비 얼마나 알차게 순이익을 벌어들였는지를 나타내는 핵심 수익성 지표)가 무려 30%를 넘나드는 압도적인 펀더멘털(기업의 기초 체력과 돈 버는 힘)을 보여주고 있습니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "시장이 불안정하거나 금리 방향성이 모호할수록, 투자자들의 돈은 어설픈 2등·3등 주식에서 빠져나와 확실한 실적과 이익 방어력을 입증한 '1등 알짜주'로 쏠리는 수급 집중 현상이 나타납니다."
        ]
        action = "💡 오늘 이렇게 대응하세요: 내가 가진 종목이 단순히 업종 분위기에 편승해 따라 오르는 '무늬만 테마주'인지, 아니면 자체적인 현금 창출력으로 하락장을 버텨낼 수 있는 '진짜 알짜주'인지 계좌 비중을 냉정히 점검할 타이밍입니다."
        return "⚖️ 종목 정밀선별", 8, headline, paragraphs, action

    # 2. FDA 최종 승인
    if any(k in combo for k in ["fda approval", "fda approves", "cleared"]):
        headline = "🎉 미국 식품의약국(FDA) 공식 시판 판매 승인 통과!"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "세계에서 가장 엄격한 심사 기준을 적용하는 미국 FDA(식품의약국)로부터 신약 또는 첨단 의료기기에 대한 최종 시판 허가(정식 판매 승인) 통보를 받았습니다. 회사가 오랜 기간 천문학적인 연구비를 쏟아부었던 결실이 공식적으로 인정받았습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "바이오나 헬스케어 주식에 투자할 때 투자자들이 가장 두려워하는 것은 '수년간 공들인 약이 막판에 허가를 못 받고 폐기되는 일'입니다. 이번 승인으로 그 거대한 개발 실패 리스크(위험 요소)가 완전히 해소되었습니다.<br>"
            "이제부터는 연구소 단계가 아니라 병원, 약국, 글로벌 유통망에 제품이 실제로 깔리며 회사 통장에 '진짜 매출액(제품을 팔아 번 돈)'과 영업이익(본업 장사로 순수하게 남긴 돈)이 가파르게 찍히는 본격적인 상용화 국면에 진입합니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "바이오 섹터에서 FDA 승인은 단기 주가를 수십 % 이상 단숨에 밀어 올리는 가장 폭발력 있는 호재 촉매(주가 상승을 촉발하는 핵심 재료)로 작용합니다."
        ]
        action = "💡 오늘 이렇게 대응하세요: 장 시작과 동시에 갭상승(전날 마감 가격보다 훨씬 높은 가격에서 시초가가 형성되는 현상)이 나타날 가능성이 높습니다. 장 초반 흥분 매수에 섣불리 뛰어들기보다는, 기관(전문 펀드 투자자)들이 물량을 내던지지 않고 꾸준히 매집하는지 확인하는 것이 안전합니다."
        return "🧬 FDA 판매승인", 10, headline, paragraphs, action

    # 3. 임상 시험 성공
    if any(k in combo for k in ["clinical trial", "phase 3", "phase 2", "topline"]):
        headline = "🧪 핵심 임상 시험 목표 달성! 신약 탄생에 성큼 다가섰다"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "실제 환자들을 대상으로 진행된 임상 시험(신약 후보 물질이 인간에게 안전하고 질병을 치료하는 효과가 있는지 검증하는 단계)에서 1차 평가지표를 성공적으로 충족하며 탁월한 효능 데이터를 공식 발표했습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "신약 개발은 수백 개 중 단 몇 개만 살아남을 정도로 통과하기 어려운 험난한 과정입니다. 특히 임상 2상이나 3상 단계에서 유의미한 수치를 뽑아냈다는 것은 최종 시판 허가까지의 성공 확률이 기하급수적으로 높아졌음을 의미합니다.<br>"
            "자체적으로 약을 다 팔지 않더라도, 다른 거대 글로벌 제약사(빅파마)들이 이 결과를 보고 눈독을 들이며 수천억 원대 계약금을 주고 기술을 사가는 L/O(기술수출 계약, 신약 권리를 다른 제약사에 넘기고 로열티를 받는 계약) 협상 테이블이 열리게 됩니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "회사의 잠재적 파이프라인(개발 중인 신약 프로젝트 가치) 가치가 장부상에 재평가되면서 중기적인 우상향 랠리의 기틀이 마련됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 발표 직후 단기 급등에 따른 차익실현(단기 차익을 노리고 주식을 팔아 현금화하는 매물)이 쏟아져 일시적으로 흔들릴 수 있습니다. 시험 데이터의 안전성 이슈가 없는지 확인하고 다음 규제 당국 미팅 일정을 확인하세요."
        return "🧪 임상 성공", 8, headline, paragraphs, action

    # 4. 인수합병 (M&A)
    if any(k in combo for k in ["acquire", "acquisition", "merger", "buyout"]):
        m = re.search(r"(?:to acquire|acquisition of)\s+([A-Za-z0-9\s,\.\-]+?)(?:for|\.|\band\b|$)", title, re.IGNORECASE)
        target = m.group(1).strip() if m else "업계 유망 기업"
        headline = f"🤝 공격적인 덩치 키우기: [{target[:22]}] 인수합병(M&A) 공식 체결"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            f"회사가 미래 시장 지배력을 강화하고 새로운 먹거리를 확보하기 위해 [{target[:25]}]의 지분을 대규모로 사들이는 M&A(인수합병, 다른 기업을 돈으로 매수해 자회사로 편입하는 경영 전략)를 단행했습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "새로운 기술을 직접 연구하고 새 고객을 바닥부터 모으려면 5~10년의 긴 시간과 막대한 돈이 들어갑니다. 하지만 이미 그 시장에서 자리 잡은 유망 회사를 인수하면, 그 회사가 보유한 특허 기술과 탄탄한 고객 명단이 오늘 당장 우리 회사의 자산이 됩니다.<br>"
            "다음 분기부터는 피인수 회사가 벌어들이는 매출과 영업이익이 연결 재무제표(자회사 실적까지 하나로 합쳐서 보여주는 기업 회계 장부)에 고스란히 더해져 회사의 외형 규모가 한 단계 도약하게 됩니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "인수 금액이 지나치게 비싸지 않고 회사 성장에 꼭 필요한 알짜 기업이라면, 시장은 이를 강력한 성장 드라이브로 해석해 주가 밸류에이션(기업 가치 평가 배수)을 높여줍니다."
        ]
        action = "💡 오늘 이렇게 보세요: 회사를 사들이느라 무리하게 빚을 냈거나 유상증자(새로 주식을 마구 찍어내 주주 돈을 빌려 주당 가치를 희석시키는 일)를 했는지, 아니면 회사에 쌓아둔 현금으로 건전하게 인수했는지 자금 조달 방식을 확인하세요."
        return "🤝 대형 M&A", 9, headline, paragraphs, action

    # 5. 대형 수주 / 납품 계약
    if any(k in combo for k in ["contract", "awarded", "supply agreement", "order"]):
        headline = "💰 거대 고객사와의 장기 대규모 공급 수주 계약 체결"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "미국 정부 기관이나 글로벌 대형 기업과 다년간 제품 및 첨단 서비스를 독점 공급하기로 하는 정식 수주(물품 공급 주문을 공식 계약으로 따내는 것) 계약서에 서명을 마쳤습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "장사하는 기업 입장에서 가장 불안한 것은 '다음 달, 내년에 경기가 나빠져서 물건이 안 팔리면 어쩌지?' 하는 불확실성입니다. 하지만 이런 대형 수주 계약이 체결되면 수주 잔고(앞으로 납품하면서 회사 통장으로 따박따박 들어올 확정된 계약 총액)가 쌓이게 됩니다.<br>"
            "경기가 출렁여도 이미 확보된 계약 물량 덕분에 향후 1~2년간 회사의 최소 매출과 이익이 보장되므로, 실적 침체에 대한 걱정이 눈 녹듯 사라지고 주가에 아주 튼튼한 하방 지지선(더 이상 떨어지지 않게 받쳐주는 가격대)이 생깁니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "깜짝 실적이 아니라 '지속 가능한 실적'이 확인되었기 때문에, 단타성 개미 투자자뿐 아니라 장기 자금을 굴리는 연기금과 대형 펀드들이 안심하고 주식을 사 모으는 계기가 됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 이번에 따낸 계약 총금액이 이 회사가 1년 동안 벌어들이는 연간 전체 매출액의 몇 %에 달하는 수준인지 확인하세요. 비중이 30~50%를 넘어가는 매머드급 계약이라면 주가 상승 탄력이 훨씬 오래 지속됩니다."
        return "💰 대형 계약수주", 8, headline, paragraphs, action

    # 6. 실적 서프라이즈 / 가이던스 상향
    if any(k in combo for k in ["guidance", "beats", "earnings surprise", "record revenue", "quarter results"]):
        headline = "📈 어닝 서프라이즈! 시장 예상치를 대폭 깬 역대급 실적 달성"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "최근 분기 실적 발표에서 회사가 실제로 벌어들인 매출과 순이익이 월가 전문가들의 컨센서스(증권사 애널리스트들의 평균 실적 예상치)를 큰 폭으로 뛰어넘는 어닝 서프라이즈(깜짝 호실적)를 기록했습니다. 이에 더해 경영진은 향후 벌어들일 목표치인 가이던스(기업이 스스로 발표하는 향후 분기·연간 실적 전망 목표)까지 대폭 올려 잡았습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "주식 시장에서 온갖 풍문이나 테마는 거품이 끼기 쉽지만, 회사의 계좌에 실제로 들어온 '돈(영업이익)'은 절대로 거짓말을 하지 않습니다. 실적이 컨센서스를 이겼다는 것은 제품이 시장에서 불티나게 팔리고 있으며 원가 절감까지 성공했다는 완벽한 방증입니다.<br>"
            "더욱이 사장님이 직접 '앞으로 남은 기간 동안 돈을 더 많이 벌 자신감이 있다'며 가이던스를 높였다는 것은, 회사의 성장 엔진이 일시적인 반짝 유행이 아니라 구조적으로 가속화되고 있음을 뜻합니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "실적 장세에서 호실적과 가이던스 상향의 조합은 주가가 계단식으로 계속해서 신고가를 뚫고 올라가는 우상향(주가가 꾸준히 오르는 장기 추세) 랠리를 만드는 가장 정석적인 재료입니다."
        ]
        action = "💡 오늘 이렇게 보세요: 실적 호재는 하루 만에 시세가 끝나지 않습니다. 실적 발표 직후 열리는 컨퍼런스콜(회사 경영진이 기관 투자자들과 실적을 설명하고 질의응답하는 회의)에서 어떤 긍정적 코멘트가 나왔는지 확인하고 눌림목(상승 도중 잠깐 숨고르는 조정 구간)을 노려보세요."
        return "📈 실적 서프라이즈", 8, headline, paragraphs, action

    # 7. 금리 / 연준 통화정책 (매크로)
    if any(k in combo for k in ["fed", "interest rate", "rate cut", "rate hike", "inflation", "cpi", "powell"]):
        headline = "🏦 미국 중앙은행(연준)의 기준금리 결정 및 인플레이션 물가 지표 발표"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "세계 금융시장의 사령탑인 미국 Fed(연방준비제도, 미국의 중앙은행)의 제롬 파월 의장이 금리 방향성에 대해 공식 발언을 내놓았거나, 미국의 물가가 얼마나 올랐는지를 측정하는 CPI(소비자물가지수, 물가 상승률을 보여주는 핵심 경제 지표) 수치가 발표되었습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "금리는 쉽게 말해 '돈을 빌리는 값(이자)'입니다. 기준금리를 내리면 은행에 돈을 묶어둘 이유가 없어져 시중의 거대한 돈이 주식 시장으로 쏟아져 들어오고, 기술 기업들의 막대한 대출 이자 부담이 줄어들어 주가가 활활 타오릅니다.<br>"
            "반대로 물가가 안 잡혀서 연준이 '금리를 계속 높게 유지하겠다'고 엄포를 놓으면, 빚이 많고 먼 미래의 꿈을 먹고 사는 기술 성장주들은 자금 조달 비용이 늘어나 주가가 무겁게 짓눌리게 됩니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "이 소식은 개별 종목 하나의 문제가 아니라, 나스닥과 S&P 500 지수 전체를 위아래로 수 퍼센트씩 뒤흔드는 최상위 매크로(거시 경제 전체의 큰 흐름) 변수입니다."
        ]
        action = "💡 오늘 이렇게 보세요: 개별 주식이 잘못해서 떨어지는 것이 아니라 거시 환경의 바람이 부는 것이므로, 10년물 미국 국채 금리가 치솟는지 아니면 안정되는지를 먼저 확인하고 매매를 결정하세요."
        return "🏦 금리/물가 매크로", 9, headline, paragraphs, action

    # 8. 유가 / 원유 (매크로)
    if any(k in combo for k in ["oil", "crude", "opec", "energy", "gas"]):
        headline = "🛢️ 국제 유가 급등락! 에너지 수급 불안과 증시 파급 효과"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "중동 산유국들의 분쟁이나 OPEC(석유수출국기구, 전 세계 원유 공급량을 조절하는 산유국 카르텔)의 감산(석유 생산량을 줄여 가격을 방어하는 조치) 결정으로 인해 국제 원유(WTI 및 브렌트유) 가격이 가파르게 요동치고 있습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "석유는 단순한 기름이 아니라 공장을 돌리고, 물건을 나르고, 플라스틱을 만드는 전 세계 모든 산업의 핏줄입니다. 유가가 치솟으면 모든 회사의 물류비와 생산 원가가 뛰어 제품 가격이 오르고, 이는 진정되던 인플레이션(물가 상승 현상)에 다시 불을 지펴 연준이 금리를 못 내리게 발목을 잡습니다.<br>"
            "하지만 모든 기업에 악재인 것은 아닙니다. 땅에서 원유를 직접 뽑아 올려 비싸게 파는 정유사나 에너지 기업들에게는 막대한 횡재 이익이 떨어지는 최고의 호재가 됩니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "항공사, 해운사, 일반 소비재 기업들은 비용 부담으로 주가가 주춤하는 반면, 에너지 섹터(석유·가스 관련 주식 집합)로 기관들의 매수 자금이 급격히 피신하는 차별화 장세가 나타납니다."
        ]
        action = "💡 오늘 이렇게 보세요: 기름값 상승세가 단기 쇼크인지 장기 추세인지 살피고, 내 포트폴리오에 에너지 관련주 비중을 헷지(위험을 분산하고 방어하는 투자 기법) 차원에서 편입할지 고려해 보세요."
        return "🛢️ 유가/원자재", 8, headline, paragraphs, action

    # 9. 암호화폐 / 비트코인
    if any(k in combo for k in ["bitcoin", "crypto", "ethereum", "btc"]):
        headline = "🪙 비트코인 급변동! 가상자산 시장과 연동 주식들의 동반 슈팅"
        paragraphs = [
            "**📌 어떤 소식인가요?**<br>"
            "비트코인과 이더리움 등 주요 암호화폐 시세가 거센 변동성을 보이며 출렁이고 있으며, 대형 기관들의 현물 ETF(증권 시장에서 주식처럼 편리하게 사고파는 가상자산 펀드)로의 자금 유입 및 규제 당국의 정책 변화가 보도되었습니다.",
            
            "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
            "요즘 주식 시장에는 비트코인을 회사 금고에 수천~수만 개씩 사 모아두며 사실상 비트코인 펀드처럼 움직이는 기업들(예: 마이크로스트래티지 등)과 가상자산 거래소 기업들이 다수 상장되어 있습니다.<br>"
            "이들 기업의 주가는 비트코인 가격과 커플링(두 자산이 마치 한 몸인 것처럼 완벽하게 같은 방향으로 움직이는 현상)되어, 비트코인이 5%만 올라도 주가는 10~20%씩 폭발하는 지렛대(레버리지) 효과를 보여줍니다.",
            
            "**📊 시장 영향 및 파급력**<br>"
            "가상자산 시장에 돈이 돌기 시작하면 증시 전반의 위험자산 선호 심리가 되살아나며 중소형 기술주와 핀테크 섹터로도 온기가 빠르게 확산됩니다."
        ]
        action = "💡 오늘 이렇게 보세요: 코인 관련 주식은 상승 탄력이 엄청난 만큼 하락할 때의 충격도 매우 큽니다. 비트코인이 전고점이나 핵심 지지 가격대를 탄탄히 지켜주는지 차트를 먼저 확인한 뒤 진입하세요."
        return "🪙 코인/비트코인", 8, headline, paragraphs, action

    # 기본 소식 (맥락 보강)
    clean_title = title.replace(" - Yahoo Finance", "").replace("Yahoo Finance", "")
    headline = "📢 기업 주요 경영 전략 발표 및 비즈니스 현황 공시"
    paragraphs = [
        f"**📌 어떤 소식인가요?**<br>"
        f"현지 언론을 통해 [{clean_title[:55]}] 관련 주요 기업 동향이 공식 보도되었습니다. 회사의 새로운 서비스 런칭이나 사업 방향성을 시장 투자자들에게 공유하는 내용입니다.",
        
        "**💡 왜 내 돈과 주가에 중요한가요? (원리 풀이)**<br>"
        "오늘 당장 자고 일어났더니 주가가 상한가를 치는 식의 단기 폭탄 호재는 아니지만, 회사가 본업에서 발을 빼지 않고 착실하게 새로운 시장을 개척하며 펀더멘털(기업의 본질 가치)을 다져가고 있음을 보여주는 건강한 신호입니다.<br>"
        "주식 시장에서는 이런 작은 경영 업데이트들이 겹겹이 쌓여 다음 분기 실적의 밑거름이 되므로, 회사가 올바른 방향으로 나아가고 있는지 나침반 역할을 해줍니다.",
        
        "**📊 시장 영향 및 파급력**<br>"
        "주가에 급격한 갭을 만들기보다는 장기적인 기업 신뢰도를 높여 기관들의 지속적인 보유 유인을 제공합니다."
    ]
    action = "💡 오늘 이렇게 보세요: 단기 급등을 노리기보다는, 오늘 평소 거래량(주식이 하루 동안 체결된 총량)보다 의미 있는 수급이 유입되는지 호가창과 거래량을 가볍게 체크해 보세요."
    return "📢 기업 소식", 6, headline, paragraphs, action

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
        category, stars, headline_kor, paragraphs_list, action_guide = make_deep_context_briefing(title, summary_raw)
        
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
            
            # 단락들을 깔끔한 문단 구분(<div class='story-p'>)으로 렌더링
            paragraphs_html = "".join([f"<div class='story-p'>{p}</div>" for p in item['paragraphs']])
            
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
                <div class="action-box">
                    {item['action']}
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
