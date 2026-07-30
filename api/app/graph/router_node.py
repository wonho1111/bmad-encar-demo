"""라우터 노드 — FR13·FR43 의도 분류(REJECT/CLARIFY/SQL/HYBRID).

흐름: 자연어 질의 → (Gemini 구조화 출력) route 판정 → 결정론적 보정 →
  "REJECT"/"CLARIFY"/"SQL"/"HYBRID".
  · SQL = 구조형(가격·차종·연식·색상·지역·주행거리 등 명시 조건만) → 경로 SQL(Text-to-SQL).
  · HYBRID = 구조 조건 + 의미/느낌 조건이 함께 있는 조합형(신규, 예: "3천만원 이하로
    무난한 패밀리카") → 경로 HYBRID(13.3 전까지는 sql_rag_node로 임시 실행, graph.py 참조).
  · CLARIFY = 구조 조건 없이 순수 용도·느낌만 묻는 질의(구 B, "패밀리카로 무난한 거" 류)
    → 경로 CLARIFY(되묻기, 13.4 전까지는 doc_rag_node로 임시 실행 — 기존 B 경험 그대로).
  · REJECT = 매물 무관(잡담·상식·다른 주제·금융/세금/보험 일반지식) → 가드(정중한 거절, FR16).

설계(OI2): LLM 단일 호출 + Pydantic Literal["REJECT","CLARIFY","SQL","HYBRID"] 구조화 출력으로
  형식을 강제한다. 그래도 LLM은 환각·형식이탈이 가능하므로(함정 #2), 코드가 결과를 한 번 더
  검사해 4값 밖/파싱 실패면 안전 기본값으로 보정한다(매물 신호 있으면 CLARIFY, 없으면 REJECT —
  SQL·HYBRID는 확신 있는 구조 조건 추출이 전제이므로 폴백 대상이 아니다, 13.2).
  키 부재(GEMINI_API_KEY)는 보정이 아니라 require()로 fail-loud — 조용한 오답을 만들지 않는다.

4.5는 이 함수를 그래프(graph.py)의 진입 노드로 쓴다. 단일 query만 본다(멀티턴 context는 4.6).
[Source: story 4.5 router_node 설계; architecture.md#OI2; research §8 #2; story 13.2 4분기 라우팅]
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.schemas.ai import RouterDecision

logger = logging.getLogger(__name__)

# 분류 전용 시스템 프롬프트 — REJECT/CLARIFY/SQL/HYBRID 정의와 예시를 박는다(13.2, FR43).
# 차종·연료 등 상세 허용값은 분류엔 불필요(sql_rag_node가 단일출처) — 여기선 카테고리 정의·예시 위주.
_SYSTEM_PROMPT = """너는 중고차 매물 검색 어시스턴트의 "의도 분류기"다.
사용자 질의를 아래 넷 중 정확히 하나로만 분류해 route 값으로 출력한다.

- SQL (구조형): 가격·차종·연식·색상·지역·주행거리·연료·옵션명(스마트키 등) 같은 명시적 조건만으로
    매물을 거르는 질의. 용도·느낌 서술어는 섞여 있지 않다.
    "추천해줘"·"좋은 거" 같은 군더더기 표현이 섞여 있어도, 명시적 조건이 하나라도 있고
    용도·느낌 조건이 없으면 SQL이다.
    예) "3천만원 이하 흰색 SUV", "2020년 이후 제네시스", "10만km 미만 디젤", "서울 경차",
        "2천만원 이하 중형세단 스마트키 있는 거 추천해줘"
- HYBRID (조합형, 신규): 위 SQL의 명시적 조건과, 아래 CLARIFY의 용도·느낌 조건이 **함께** 있는 질의.
    예) "3천만원 이하로 무난한 패밀리카", "10만km 미만으로 출퇴근하기 편한 차",
        "2천만원 이하 초보운전자에게 무난한 세단"
- CLARIFY (질적·의미형, 되묻기): 명시적 조건이 전혀 없고 용도·느낌만으로 묻는 질의.
    예) "패밀리카로 무난한 거", "초보운전자에게 좋은 차", "출퇴근하기 편한 차", "가성비 좋은 차"
- REJECT (매물 무관): 중고차 매물 검색과 관계없는 잡담·상식·다른 주제·인사.
    여기에는 **금융·세금·보험·법률 같은 일반지식 질문**도 포함된다 —
    이런 답은 "어떤 매물을 보여줄지"를 바꾸지 않으므로 매물 추천 범위 밖이다.
    예) "오늘 날씨 어때?", "파이썬 코드 짜줘", "안녕", "1+1은?",
        "할부랑 리스 차이가 뭐야?", "취득세 얼마 나와?", "자동차세 계산해줘", "자동차보험 어떻게 들어?"

규칙:
- route 는 반드시 "SQL", "HYBRID", "CLARIFY", "REJECT" 중 하나.
- 명시적 조건과 용도·느낌 조건이 **둘 다** 있으면 HYBRID다(조합형이 최우선 판정).
- 명시적 조건만 있고 용도·느낌 조건이 없으면 SQL이다. "추천/옵션/좋은" 같은 군더더기 말이
  섞여 있어도 그 자체로는 용도·느낌 조건이 아니다(조건 우선 — SQL이 정확히 거른다).
- CLARIFY는 명시적 조건이 전혀 없고 순수하게 용도·느낌만 있을 때만 고른다(예: 초보용·패밀리카·출퇴근용).
- **할부·리스·취득세·자동차세·보험료처럼 "어떤 매물을 보여줄지" 바꾸지 않는 금융·세금·보험 일반지식은
  차에 관한 말이라도 CLARIFY가 아니라 REJECT로 분류한다**(매물 추천 도우미 범위 밖 — 정중히 거절).
- 차종·용도를 묻는 질의인데 조건이 흐릿하면(애매하면) REJECT가 아니라 CLARIFY로 분류한다(빈손보다 되묻기).
- 정말로 중고차 매물 검색과 무관하거나 위 금융·세금·보험 일반지식일 때만 REJECT로 분류한다."""

# 결정론적 보정용 — 매물 관련 신호(이 단어가 보이면 "차 얘기"로 보고 CLARIFY쪽으로 기운다).
_LISTING_SIGNALS = (
    "차", "자동차", "suv", "세단", "매물", "차량", "전기차", "디젤", "가솔린",
    "하이브리드", "경차", "트럭", "승합", "현대", "기아", "제네시스", "벤츠",
    "bmw", "테슬라", "아우디", "렉서스", "토요타", "혼다", "쉐보레", "만원",
    "천만원", "예산", "연비", "주행", "km", "연식", "패밀리", "출퇴근", "추천",
)

# 결정론적 보정용 — 금융·세금·보험 일반지식 신호. 위 프롬프트가 REJECT로 규정한 범주이며,
# _LISTING_SIGNALS보다 먼저 검사한다(아래 _fallback_route docstring의 실측 근거 참조).
_FINANCE_SIGNALS = ("할부", "리스료", "취득세", "자동차세", "보험", "이자율", "대출")


def _llm() -> ChatGoogleGenerativeAI:
    """분류용 LLM. temperature=0으로 같은 질의에 같은 분류가 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,  # gemini-3.1-flash-lite (env로 교체 가능)
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _fallback_route(query: str) -> str:
    """LLM 분류가 실패/형식이탈일 때의 결정론적 안전 기본값(13.2).

    매물 관련 신호가 조금이라도 있으면 CLARIFY(되묻기라도 주는 게 빈손보다 낫다),
    아무 신호도 없으면 REJECT(매물 무관으로 보고 가드로 보낸다).
    SQL·HYBRID는 확신 있는 구조 조건 추출이 전제이므로 키워드 휴리스틱만으로는 폴백하지 않는다.

    금융·세금·보험 신호는 매물 신호보다 **먼저** 본다(review-5 실측): `_LISTING_SIGNALS`의
    "차"가 "차이"·"자동차세"·"자동차보험" 안에서 부분 매칭돼, 위 프롬프트가 REJECT로 규정한
    질의 4개 중 3개가 CLARIFY로 새고 있었다 — 그러면 LLM 파싱이 실패하는 순간 보험·세금
    질문에 매물 목록이 나간다(FR16이 닫으려는 바로 그 답변).
    """
    low = query.lower()
    if any(sig in low for sig in _FINANCE_SIGNALS):
        return "REJECT"
    if any(sig in low for sig in _LISTING_SIGNALS):
        return "CLARIFY"
    return "REJECT"


def router_node(query: str) -> str:
    """자연어 질의를 받아 "REJECT"/"CLARIFY"/"SQL"/"HYBRID" 중 하나를 반환한다(FR13·FR43).

    GEMINI_API_KEY 부재 시 _llm()의 require()가 명확한 한국어 에러로 즉시 실패(fail-loud).
    LLM이 4값 밖의 값을 주거나 호출이 형식 오류면 _fallback_route로 결정론적 보정한다.
    """
    llm = _llm()  # 키 부재 시 여기서 fail-loud.
    structured = llm.with_structured_output(RouterDecision)
    messages = [("system", _SYSTEM_PROMPT), ("human", query)]

    try:
        decision = structured.invoke(messages)
        route = decision.route
    except Exception as exc:  # 구조화 출력 파싱 실패·일시 형식오류 → 보정(키 부재는 위에서 이미 처리)
        logger.warning("router_node 구조화 출력 실패 → 보정: %r", exc)
        route = _fallback_route(query)

    # 이중 안전: Literal이 막아주지만, 혹시 모를 형식이탈도 코드가 한 번 더 검사(함정 #2).
    if route not in ("REJECT", "CLARIFY", "SQL", "HYBRID"):
        route = _fallback_route(query)

    logger.info("router_node 질의=%r → route=%s", query, route)
    return route
