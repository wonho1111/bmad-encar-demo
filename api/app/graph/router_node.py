"""라우터 노드 — FR13 의도 분류(A/B/C).

흐름: 자연어 질의 → (Gemini 구조화 출력) route 판정 → 결정론적 보정 → "A"/"B"/"C".
  · A = 구조형(가격·차종·연식·색상·지역·주행거리 등 명시 조건) → 경로 A(Text-to-SQL).
  · B = 질적·의미형(용도·느낌·추천 — "패밀리카로 무난한 거" 류) → 경로 B(문서 RAG).
  · C = 매물 무관(잡담·상식·다른 주제) → 가드(정중한 거절, FR16).

설계(OI2): LLM 단일 호출 + Pydantic Literal["A","B","C"] 구조화 출력으로 형식을 강제한다.
  그래도 LLM은 환각·형식이탈이 가능하므로(함정 #2), 코드가 결과를 한 번 더 검사해
  A/B/C 외 값/파싱 실패면 안전 기본값으로 보정한다(매물 신호 있으면 B, 명백 무관이면 C).
  키 부재(GEMINI_API_KEY)는 보정이 아니라 require()로 fail-loud — 조용한 오답을 만들지 않는다.

4.5는 이 함수를 그래프(graph.py)의 진입 노드로 쓴다. 단일 query만 본다(멀티턴 context는 4.6).
[Source: story 4.5 router_node 설계; architecture.md#OI2; research §8 #2]
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.schemas.ai import RouterDecision

logger = logging.getLogger(__name__)

# 분류 전용 시스템 프롬프트 — A/B/C 정의와 예시를 박는다.
# 차종·연료 등 상세 허용값은 분류엔 불필요(sql_rag_node가 단일출처) — 여기선 카테고리 정의·예시 위주.
_SYSTEM_PROMPT = """너는 중고차 매물 검색 어시스턴트의 "의도 분류기"다.
사용자 질의를 아래 셋 중 정확히 하나로만 분류해 route 값으로 출력한다.

- A (구조형): 가격·차종·연식·색상·지역·주행거리·연료·옵션명(스마트키 등) 같은 명시적 조건으로 매물을 거르는 질의.
    "추천해줘"·"좋은 거" 같은 표현이 섞여 있어도, 명시적 조건이 하나라도 있으면 A다.
    예) "3천만원 이하 흰색 SUV", "2020년 이후 제네시스", "10만km 미만 디젤", "서울 경차",
        "2천만원 이하 중형세단 스마트키 있는 거 추천해줘"
- B (질적·의미형): 명시적 조건이 전혀 없고 용도·느낌만으로 묻는 질의.
    예) "패밀리카로 무난한 거", "초보운전자에게 좋은 차", "출퇴근하기 편한 차", "가성비 좋은 차"
- C (매물 무관): 중고차 매물 검색과 관계없는 잡담·상식·다른 주제·인사.
    여기에는 **금융·세금·보험·법률 같은 일반지식 질문**도 포함된다 —
    이런 답은 "어떤 매물을 보여줄지"를 바꾸지 않으므로 매물 추천 범위 밖이다.
    예) "오늘 날씨 어때?", "파이썬 코드 짜줘", "안녕", "1+1은?",
        "할부랑 리스 차이가 뭐야?", "취득세 얼마 나와?", "자동차세 계산해줘", "자동차보험 어떻게 들어?"

규칙:
- route 는 반드시 "A", "B", "C" 중 하나.
- 가격·차종·연식·색상·지역·주행거리·연료·옵션명 같은 명시적 조건이 하나라도 있으면,
  "추천/옵션/좋은" 같은 말이 섞여 있어도 반드시 A로 분류한다(조건 우선 — A가 정확히 거른다).
- B는 그런 명시적 조건이 전혀 없고 순수하게 용도·느낌만 있을 때만 고른다(예: 초보용·패밀리카·출퇴근용).
- **할부·리스·취득세·자동차세·보험료처럼 "어떤 매물을 보여줄지" 바꾸지 않는 금융·세금·보험 일반지식은
  차에 관한 말이라도 B가 아니라 C로 분류한다**(매물 추천 도우미 범위 밖 — 정중히 거절).
- 차종·용도를 묻는 질의인데 조건이 흐릿하면(애매하면) C가 아니라 B로 분류한다(빈손보다 추천).
- 정말로 중고차 매물 검색과 무관하거나 위 금융·세금·보험 일반지식일 때만 C로 분류한다."""

# 결정론적 보정용 — 매물 관련 신호(이 단어가 보이면 "차 얘기"로 보고 B쪽으로 기운다).
_LISTING_SIGNALS = (
    "차", "자동차", "suv", "세단", "매물", "차량", "전기차", "디젤", "가솔린",
    "하이브리드", "경차", "트럭", "승합", "현대", "기아", "제네시스", "벤츠",
    "bmw", "테슬라", "아우디", "렉서스", "토요타", "혼다", "쉐보레", "만원",
    "천만원", "예산", "연비", "주행", "km", "연식", "패밀리", "출퇴근", "추천",
)


def _llm() -> ChatGoogleGenerativeAI:
    """분류용 LLM. temperature=0으로 같은 질의에 같은 분류가 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,  # gemini-3.1-flash-lite (env로 교체 가능)
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _fallback_route(query: str) -> str:
    """LLM 분류가 실패/형식이탈일 때의 결정론적 안전 기본값.

    매물 관련 신호가 조금이라도 있으면 B(추천이라도 주는 게 빈손보다 낫다),
    아무 신호도 없으면 C(매물 무관으로 보고 가드로 보낸다).
    """
    low = query.lower()
    if any(sig in low for sig in _LISTING_SIGNALS):
        return "B"
    return "C"


def router_node(query: str) -> str:
    """자연어 질의를 받아 "A"/"B"/"C" 중 하나를 반환한다(FR13).

    GEMINI_API_KEY 부재 시 _llm()의 require()가 명확한 한국어 에러로 즉시 실패(fail-loud).
    LLM이 A/B/C 외 값을 주거나 호출이 형식 오류면 _fallback_route로 결정론적 보정한다.
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
    if route not in ("A", "B", "C"):
        route = _fallback_route(query)

    logger.info("router_node 질의=%r → route=%s", query, route)
    return route
