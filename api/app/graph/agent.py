"""툴콜링 에이전트 루프 — 4단계 부품 B(DW-847·848·849를 에이전트 구조로 해결).

진입점 `run_search_agent(query, context=None) -> dict`. 반환 계약은 기존 run_search(graph.py)와
  동일한 {answer, listings[], route, clarify, narrowed_by}에 키를 더한다:
  `market_diagnosis: dict|None`(직전 market_price_stats 호출 결과), `market_diagnoses:
  list[dict]|None`(2026-08-31 추가 — market_price_stats가 이번 대화에서 2건 이상 결과를
  냈을 때만 그 전부를 담는다, 상한 5. 1건 이하면 None), `tools_used: list[str]`
  (실제로 호출된 도구 이름, 호출 순서 그대로 — 중복 허용). route는 항상 "AGENT"로 고정한다
  (routers/ai.py의 스위치가 이 값으로 그래프 기반 run_search와 구분하지 않아도 되지만,
  응답 계약의 다른 소비처가 route를 로깅·분기에 쓸 수 있어 값을 비우지 않는다).

흐름: contextualize_query(FR18, 기존 그대로 재사용) → 결정론적 REJECT 사전 차단(아래 설계
  결정 참조) → 툴콜링 루프(최대 _MAX_STEPS회) → structured output으로 최종 응답 조립.

설계 결정 — 수동 while(정확히는 for) 루프 vs LangGraph create_react_agent(A2, 단순함 우선):
  langgraph.prebuilt.create_react_agent는 이 레포에 이미 설치돼(langgraph==1.2.4) 있어 쓸 수
  있었지만, 이 스토리가 요구하는 세 가지 — (1) 정확히 6스텝에서 강제 종료하고 "그때까지의
  도구 결과"로 별도 structured-output 최종 응답을 만드는 것, (2) selected_listing_ids를
  도구가 실제로 돌려준 id 집합으로 사후 검증(벗어난 id는 버림), (3) market_price_stats의
  마지막 호출 결과를 market_diagnosis로 노출 — 셋 다 create_react_agent의 메시지 리스트
  출력을 다시 파싱해 똑같이 구현해야 한다(그 라이브러리는 "메시지 오간 기록"만 주지,
  구조화된 최종 응답·도구별 부작용 훅을 주지 않는다). 즉 어느 쪽을 써도 이 파일의 핵심
  로직(스텝 카운트·검증·상태 누적)은 직접 짜야 하고, LangGraph를 얹으면 그 위에 그래프
  컴파일·상태 스키마·조건부 엣지까지 추가 개념이 하나 더 얹힌다 — 이 정도 규모(도구 4개,
  분기 없는 단일 루프)에 StateGraph를 새로 컴파일하는 비용은 과설계다("시니어 엔지니어가
  과설계라 할까?" 기준, A2). graph.py가 이미 StateGraph를 쓰는 것은 라우터가 REJECT/CLARIFY/
  SQL/HYBRID 4갈래로 실제 분기하기 때문이고, 이 에이전트는 분기가 아니라 "같은 노드(LLM
  호출)를 반복"하는 루프라 파이썬 for 문이 곧 최소 구현이다. 그래서 LLM 호출(`llm.bind_tools`)
  자체는 LangGraph 생태계(langchain_google_genai) 관례를 그대로 따르되, 오케스트레이션은
  이 모듈의 평범한 for 루프로 짠다.

설계 결정 — 결정론적 REJECT 사전 차단: 스펙은 "router_node에서 결정론 패턴만 재사용
  가능하면 재사용, LLM 라우터 호출은 하지 않는다"고 명시한다. router_node.py를 보면 LLM
  분류 자체는 결정론이 아니지만, `_fallback_route`가 쓰는 `_FINANCE_SIGNALS`(할부·리스료·
  취득세·자동차세·보험·이자율·대출)만은 순수 결정론 키워드 목록이다 — router_node의
  프롬프트가 "이런 금융·세금·보험 일반지식은 REJECT로 분류하라"고 명시한 규칙을 코드로
  옮긴 것이다(test_router_node.py::test_fallback_route_sends_finance_knowledge_to_REJECT_...
  가 그 일치를 잠근다). 원래 이 목록은 LLM 파싱이 "실패했을 때"의 안전망으로만 쓰였지만,
  여기서는 그 결정론 규칙을 LLM 호출 "이전"의 값싼 사전 필터로 재사용한다 — 금융/세금/보험
  일반지식 질의는 굳이 4~6번의 Gemini 호출을 도는 툴콜링 루프를 태울 이유가 없다(FR16과
  같은 이유, 매물 추천 범위 밖). guard_node의 고정 거절 문구·narrowed_by를 그대로 재사용해
  기존 REJECT 경로와 동일한 사용자 경험을 보장한다(문구 drift 방지).
[Source: 4단계 부품 B 작업 지시; DW-847(동적 되묻기)·DW-848(정렬 축)·DW-849(과다조회+되추림);
 app/graph/graph.py(OI2·함정 #1/#3/#4 계승); app/graph/router_node.py(_FINANCE_SIGNALS)]
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from app.config import require, settings
from app.db.readonly import run_select
from app.graph import router_node as _router_node
from app.graph.agent_tools import AGENT_TOOLS, TOOLS_BY_NAME
from app.graph.contextualize_node import contextualize_query
from app.graph.guard_node import guard_node
from app.graph.listing_cards import SELECT_COLUMNS, rows_to_cards
from app.schemas.ai import ClarifyPayload, ListingCard

# LangSmith 루프 관제(4단계 요구): 루프 안의 LLM 2회+도구+최종화가 형제 런으로 흩어지지
# 않고 run_search_agent 하나의 트레이스로 묶이게 한다. langsmith 미설치/트레이싱 꺼짐이면
# @traceable은 no-op이라 동작에 영향이 없다(실측: 형제 4런 → 단일 트리, 2026-08-31).
try:
    from langsmith import traceable as _traceable
except Exception:  # pragma: no cover - langsmith는 langchain-core 동반 설치가 기본
    def _traceable(**_kwargs):
        def _wrap(fn):
            return fn
        return _wrap

logger = logging.getLogger(__name__)

# 스텝 상한(설계 확정값) — 초과 시 그때까지의 도구 결과만으로 강제 최종 응답을 만든다.
# 1스텝 = LLM 호출 1회(그 안에서 도구를 여러 개 동시에 부를 수도 있다, tool_calls는 배치).
_MAX_STEPS = 6

# 다건 시세 진단(market_diagnoses) 수집 상한(설계 확정값) — 2026-08-31 사용자 승인.
_MAX_MARKET_DIAGNOSES = 5

_SYSTEM_PROMPT = """너는 중고차 매물을 상담해 추천하는 에이전트다. 아래 도구를 이용해
사용자의 조건에 맞는 매물을 찾고, 필요하면 근거를 곁들여 추천한다.

[도구] — 아래 4개만 실제로 호출 가능한 도구다. 그 외 이름(예: "clarify")은 도구가 아니다 —
되묻기는 도구 호출이 아니라 최종 답변의 clarify 필드를 채우는 것이다(아래 [검색 필터 규칙 — 말한 조건만 건다]
- 사용자가 명시하지 않은 필터를 지어내지 마라. 특히 **연식(year_min/year_max)**: 직전에 다룬
  매물의 연식을 새 검색 조건으로 승격하지 마라 — "같은 차종/같은 모델" 요청은 모델 기준이지
  연식 기준이 아니다(실측 결함 2026-09-01: 기준 매물이 2019년식이라 year_min=2019를 몰래
  걸어 2018년식 정답이 잘림).
- "~년식으로 확대/넓혀 검색"은 연식 **범위를 넓히라**는 뜻이다(예: 2018년식으로 확대 →
  year_min을 2018로 내리고 year_max는 걸지 않음). 그 연식 하나만 고르라는 뜻이 아니다.
- 사용자가 옵션을 여러 개 나열하면("~있고, ~달려 있고") 전부 필수다 → search_listings의
  options_required에 함께 담아라(옵션 간 AND 의미 — 하나라도 빠진 매물은 제외된다). 1인소유·
  비흡연은 옵션 목록에 섞지 말고 전용 인자(single_owner_only/non_smoker_only)로 걸어라.
- **조건을 전부 만족하는 매물이 1건이라도 있으면 그것만 추천하라 — 조건 미달 매물로 개수를
  채우지 마라**(실측 결함 2026-09-01: 통풍시트+스마트크루즈를 둘 다 요구했는데, 하나만 있는
  매물까지 끼워 3건을 채워 추천함). 검색 결과가 0건이라 조건을 완화했다면(예: 옵션 하나를
  빼거나 가격대를 넓혔다면) 어떤 조건을 뺐는지 답변에 반드시 명시하라.

[되묻기 규칙] 참조).
- search_listings: 구조 조건(가격·연식·주행거리·차종·연료·옵션 등)으로 매물을 최대 20건까지
  과다조회한다. 이 20건은 최종 추천 개수가 아니라 되추릴 재료다.
- search_guides: 중고차 구매 가이드 문서를 의미 검색한다. search_listings 결과가 한 조건에
  쏠려 보이면(예: 하이브리드만 5건, 특정 차급만 나옴) 이 도구로 관련 섹션을 읽고 차급·용도를
  다양하게 조합해 최종 5건 내외로 되추려라(예: 하이브리드 소형 4건+대형 3건+준중형 1건 →
  소형+준중형으로 5건을 고른다). 검색 결과가 이미 다양하면 되추릴 필요 없다.
- market_price_stats: 매물 1건의 시세를 진단한다(비교군 통계·적정가 예측). "그중 N번째
  매물 시세 알려줘"처럼 직전 검색 결과를 가리키면, 그 목록에서 N번째 매물의 id로 이 도구를
  호출해라. 시세·적정가·가격대를 한 마디라도 언급하려면 **먼저 이 도구를 호출해서 얻은
  값만** 써라 — 호출 없이 아는 대로 가격대를 말하지 마라(일반 지식으로 추정한 시세는 금지).
- compare_listings: 매물 최대 4건의 핵심 필드를 나란히 비교한다.

[직전 목록 참조] — 아래 [직전 대화에서 보여준 매물] 블록이 있을 때만 해당한다.
사용자가 "그중 N번째", "아까 그 아반떼", "그 5개 비교"처럼 직전에 보여준 매물을 가리키는
요청을 하면, 새로 search_listings를 부르지 말고 그 블록의 id로 market_price_stats나
compare_listings를 바로 호출해라(새 검색은 새 조건을 찾을 때만 쓴다). 그 블록에서 조건에
맞는 매물이 여럿이면(예: "아반떼 시세 알려줘"인데 목록에 아반떼가 2대) 임의로 하나를 골라
호출하지 말고, 최종 응답의 clarify로 어느 것인지 물어라 — chips는 그 후보들을 "모델 연식
가격"(예: "아반떼 AD 2017 926만원") 형태로 2~4개 만들어라. compare_listings 결과로 답할
땐 비교한 매물들의 id를 selected_listing_ids에 담아라.
"나머지", "그 외", "이 중 ~것"은 직전 목록에서 이미 다룬(진단·비교한) 매물을 제외한 항목을
뜻한다 — 이때도 반드시 그 블록의 id를 쓰고 search_listings를 새로 부르지 마라.
주어가 없는 후속 요청("아니 시세분석해달라고", "그거 말고")은 위 [직전 대화에서 보여준
매물] 블록의 매물을 가리키는 것으로 우선 해석하라 — 대화가 그보다 앞서 다른 차종을 다뤘어도
그 오래된 주제로 건너뛰지 마라(블록이 항상 가장 최근에 실제로 보여준 매물이다). 시세 분석
요청에는 매물 재추천을 얹지 마라 — 대상 1건의 진단(또는 대상을 특정하기 위한 clarify)만
응답하고, 별개 조건으로 새 매물 목록을 함께 내놓지 마라.
생략형 후속 질의("레이는?", "그거는?"처럼 동사 없이 차종·대상만 던지는 요청)는 직전 턴과
같은 작업을 새 대상에 적용하라 — 직전 턴이 시세 진단이었으면 이번 요청도 그 새 대상의
시세 진단이다(재검색이 아니다). 그 새 대상이 [직전 대화에서 보여준 매물] 블록에 있으면
그 id를 그대로 써서 market_price_stats를 호출해라 — 블록에 없으면 그때만 search_listings로
새로 찾아라.
위 [직전 대화에서 보여준 매물] 블록 자체가 **없는** 상태에서 "그중", "나머지"처럼 직전 목록을
가리키는 표현을 쓰거나, 대상을 지목하지 않은 채 시세 분석·비교를 요청하면(예: "아니
시세분석해달라고", "그거 말고"도 이 경우에 해당한다 — 대화가 그 전에 아무 매물도 보여주지
않았다면), 그 요청을 새 조건으로 오해해 search_listings나 market_price_stats를 부르지 마라 —
가리킬 매물이 아예 없으므로 무엇이든 호출하면 엉뚱한 매물을 지어내는 것이다. 대신 clarify로
어떤 차량을 말하는지 되물어라 — chips는 예산·차종을 묻는 고정 칩이 아니라 "어떤 차량을
찾으셨나요?"처럼 대상을 확인하는 질문에 맞춘 후보로 만들어라.

[되묻기 규칙]
조건이 모호해 무엇을 찾아야 할지 판단할 수 없으면(예: "차 추천해줘"처럼 예산·용도·차종이
전혀 없음) 매물을 검색하지 말고 도구를 호출하지 말고, 최종 응답의 clarify 필드를 채워서
되물어라 — question은 무엇이 부족한지 짧게 묻고, chips는 그 질의 맥락에 맞는 후보 2~4개를
직접 만들어라(고정 문구를 반복하지 말고 질의 내용에 맞춰라). clarify를 채울 때 answer는
짧은 안내 한 줄만 남긴다. 단, 매물을 이미 찾아 제시할 수 있으면 clarify가 아니라 매물 제시가
정답이다 — '쏘렌토 있어?' 같은 재고 확인 질의도 매물을 보여주며 답한다.

[답변 형식]
답변은 한 덩어리로 몰아 쓰지 말고 2~3문장 단위로 문단을 나누고(문단 사이 빈 줄), 여러
매물을 다루면 "1. ", "2. "처럼 번호 목록으로 써라 — 벽처럼 이어진 긴 문장은 읽기 어렵다.
번호 목록이 끝나면 마무리 문장(예: "궁금하시면 말씀해 주세요")은 마지막 번호 항목에 이어
쓰지 말고, 반드시 빈 줄로 구분해 별도 문단으로 써라 — 번호 목록 항목처럼 읽히면 안 된다.

[금지 사항]
- 수치(시세·통계·가격·연식·주행거리 등)는 도구가 실제로 돌려준 값만 인용한다 — 지어내지
  않는다. 특히 시세·적정가·가격대는 market_price_stats를 호출해 받은 값이 아니면 절대
  언급하지 마라(대략적인 범위 추정도 금지 — 모르면 search_listings/market_price_stats로
  확인하거나, 그래도 판단이 안 서면 clarify로 되물어라). 매물별 저렴/적정/높음 같은 시세
  판정 서술도 market_price_stats를 호출한 매물에 대해서만 하라. 여러 매물의 시세 판정을
  요청받으면 각 매물에 대해 이 도구를 각각 호출하라(최대 5건) — 호출하지 않은 매물의
  판정을 지어내지 마라.
- 시세 설명에서 비교군의 성격은 market_price_stats 결과의 criteria(step·desc)를 그대로
  따른다 — 완화가 있었으면(예: "세대 해제") 그 사실을 언급하고, 완화된 비교군을 "동일
  모델 비교군"이라고 표현하지 마라(실제와 다른 설명이 된다).
- 답변에서 매물의 연료·연식 등 속성을 서술할 땐 도구가 돌려준 그 매물의 실제 값과
  일치시켜라(예: 가솔린 매물을 하이브리드 무리로 묶어 서술 금지).
- 대출·리스·보험료·세금 계산 같은 금융 상담은 하지 않는다(매물 추천 범위 밖). 그런 질문이
  섞이면 정중히 범위를 안내하고 매물 조건으로 화제를 돌려라.
- 안전·법률 조언(사고 처리·정비 방법 등)은 하지 않는다 — 매물 추천에만 집중한다.

최종 답변에서 매물을 추천했다면 그 매물들의 id를 selected_listing_ids에 담아라 — 도구가
한 번도 보여주지 않은 id를 지어내지 마라."""

# 강제 최종화 지시 — 스텝 상한 도달/자연 종료 어느 쪽이든 이 한 번의 structured-output
# 호출로 최종 응답을 만든다(도구 없이, 지금까지의 대화 기록만 근거로).
_FINALIZE_INSTRUCTION = (
    "지금까지의 도구 호출 결과만 근거로 최종 응답을 구조화된 형식으로 정리해라. "
    "매물을 추천한다면 도구가 실제로 돌려준 id만 selected_listing_ids에 담아라. "
    "조건이 여전히 모호해 검색을 못 했다면 clarify를 채우고 answer는 짧은 안내만 남겨라."
)


class _AgentFinalOutput(BaseModel):
    """에이전트 최종 구조화 출력 — with_structured_output으로 강제(router_node와 동일 관례)."""

    answer: str
    selected_listing_ids: list[str] = Field(default_factory=list)
    clarify: ClarifyPayload | None = None


def _llm() -> ChatGoogleGenerativeAI:
    """에이전트용 LLM. temperature=0으로 같은 대화 상태에 같은 도구 선택이 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _deterministic_reject(query: str) -> bool:
    """router_node의 결정론 REJECT 패턴(_FINANCE_SIGNALS)만 재사용한 사전 차단.

    router_node._fallback_route와 판정 기준을 동일하게 유지한다(모듈 상단 "설계 결정"
    참조) — 금융·세금·보험 일반지식은 매물 추천 범위 밖이므로 LLM 툴콜링 루프를 아예
    태우지 않는다.
    """
    low = query.lower()
    return any(sig in low for sig in _router_node._FINANCE_SIGNALS)


def _reject_result(query: str) -> dict:
    result = guard_node(query)
    return {
        "answer": result["answer"],
        "listings": [],
        "route": "AGENT",
        "clarify": None,
        "narrowed_by": result["narrowed_by"],
        "market_diagnosis": None,
        "market_diagnoses": None,
        "tools_used": [],
    }


def _finalize(base_llm: ChatGoogleGenerativeAI, messages: list, found_count: int = 0) -> _AgentFinalOutput:
    """도구 없이 structured output 1회 호출로 최종 응답을 만든다(router_node와 동일 관례).

    found_count: 루프 동안 도구가 실제로 찾은 매물 수. 0이 아니면 최종화 지시에 사실로
    주입한다 — 회귀 실측(S1·S14, 2026-08-31): 도구가 매물을 찾았는데도 최종화 LLM이
    selected_listing_ids를 비우고 "찾았다"는 서술+되묻기만 내는 자기모순 응답을 냈다.
    """
    structured = base_llm.with_structured_output(_AgentFinalOutput)
    instruction = _FINALIZE_INSTRUCTION
    if found_count:
        instruction += (
            f"\n[사실] 도구가 이번 대화에서 매물 {found_count}건을 실제로 찾았다. 사용자 의도가 "
            "매물 탐색·조회('쏘렌토 있어?' 같은 재고 확인 포함)라면 그중 조건에 맞는 3~5건의 id를 "
            "selected_listing_ids에 반드시 채워라 — 찾았다고 서술만 하고 목록을 비우는 응답은 "
            "금지다. 매물을 골랐다면 clarify는 채우지 마라."
        )
    return structured.invoke(messages + [HumanMessage(instruction)])


_RECENT_LISTINGS_MERGE_CAP = 20


def _recent_assistant_listing_ids(context: list | None) -> list[str]:
    """context에서 listing_ids를 실은 **모든** 어시스턴트 턴의 id들을 최신 턴부터 병합한다
    (멀티턴 매물 참조).

    2026-08-31 개정(사용자 실측 결함 P1): 예전엔 "가장 최근 listing_ids 보유 턴 하나"만
    썼다 — 그래서 "레이 추천해줘"(1턴) → "그 옵션 뭐 있어?"(2턴, listing_ids 없음) →
    "레이는?"(3턴) 같은 흐름에서 3턴이 1턴의 매물을 더는 참조할 수 없었다(2턴 전 매물을
    못 봄). 이제는 최신 턴부터 과거로 스캔하며 listing_ids가 있는 **모든** 어시스턴트
    턴의 id를 순서대로(최근 것이 앞) 모은다 — 같은 id가 여러 턴에 걸쳐 반복되면 최초(가장
    최근) 등장만 남기고 중복 제거하며, 총 `_RECENT_LISTINGS_MERGE_CAP`(20)건에서 자른다
    (ConversationTurn.listing_ids 개별 상한 20과 동일선상 — 프롬프트가 과도하게 커지지
    않게). 다만 스캔은 직전 대화 안에서만(무상태 — context가 서버로 넘어온 이번 요청
    분량만) 이뤄지고, ConversationTurn 자체가 서버·DB에 저장되지 않으므로 무상태 원칙은
    그대로다. 턴은 Pydantic ConversationTurn 또는 dict 둘 다 받아들인다
    (contextualize_node.py와 동일 관례).
    """
    if not context:
        return []
    merged: list[str] = []
    seen: set[str] = set()
    for turn in reversed(context):
        role = getattr(turn, "role", None) or (turn.get("role") if isinstance(turn, dict) else None)
        if role != "assistant":
            continue
        ids = getattr(turn, "listing_ids", None)
        if ids is None and isinstance(turn, dict):
            ids = turn.get("listing_ids")
        if not ids:
            continue  # 이 어시스턴트 턴엔 listing_ids가 없다 — 더 이전 턴을 계속 찾는다.
        for lid in ids:
            if lid not in seen:
                seen.add(lid)
                merged.append(lid)
        if len(merged) >= _RECENT_LISTINGS_MERGE_CAP:
            break
    return merged[:_RECENT_LISTINGS_MERGE_CAP]


def _format_recent_listings_block(cards: list[ListingCard], ordered_ids: list[str]) -> str | None:
    """조회된 카드들을 원래 id 순서(여러 턴을 병합한 순서 — 최근 턴 매물이 앞, "N번째"
    지시어와 대응)대로 번호를 새로 매겨 요약한다. DB에 없는(존재하지 않는) id는 조용히
    건너뛴다(강건성)."""
    by_id = {c.id: c for c in cards}
    lines = []
    for lid in ordered_ids:
        card = by_id.get(lid)
        if card is None:
            continue  # 존재하지 않는 id 무시(강건성) — 팔린 매물·잘못된 id 등.
        lines.append(
            f"{len(lines) + 1}. {card.manufacturer} {card.model} {card.year}년식 · "
            f"{card.price:,}원 · {card.mileage:,}km (id: {card.id})"
        )
    if not lines:
        return None
    return "[직전 대화에서 보여준 매물]\n" + "\n".join(lines)


def _recent_listings_prompt_block(context: list | None) -> str | None:
    """직전 대화의 매물 id들로 DB를 조회해(SELECT만) 시스템 프롬프트용 요약 블록을 만든다.

    조회 실패(DB 장애·비UUID 등)는 루프를 막지 않는다 — 이 블록은 "있으면 좋은" 보조
    힌트이지 필수 경로가 아니므로, 실패 시 경고 로그만 남기고 힌트 없이 그대로 진행한다.
    """
    ids = _recent_assistant_listing_ids(context)
    if not ids:
        return None
    try:
        rows = run_select(
            f"SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND id = ANY(%s::uuid[])",
            (ids,),
        )
        cards = rows_to_cards(rows)
    except Exception as exc:  # DB 장애·비UUID 등 — 힌트 없이 진행(경고 로그만, fail-loud 아님).
        logger.warning("직전 대화 매물 요약 조회 실패 — 프롬프트 힌트 없이 진행: %r", exc)
        return None
    return _format_recent_listings_block(cards, ids)


def _system_prompt(listing_id: str | None, context: list | None = None, original_query: str | None = None) -> str:
    """기본 시스템 프롬프트에 (1) 대상 매물 id 힌트(5단계, 상세 페이지 "AI 시세 진단" 버튼),
    (2) 직전 대화가 보여준 매물 요약(멀티턴 매물 참조)을 덧붙인다. 둘 다 없으면 원본 그대로
    돌려준다(회귀 0 — 기존 listing_id 전용 테스트가 이 동치를 고정한다).

    도구 강제 호출은 아니다 — LLM이 시세 요청으로 판단할 때 market_price_stats를 이 id로
    호출하도록 프롬프트로만 유도한다(설계: 버튼이 프리필한 질의문 자체도 "이 매물 시세
    알려줘" 형태라 대부분 자연스럽게 이어지지만, id를 명시해 모호성을 줄인다).
    """
    prompt = _SYSTEM_PROMPT
    if listing_id:
        prompt += (
            f"\n\n[이번 요청의 대상 매물]\n"
            f"이번 요청의 대상 매물 id는 {listing_id}다. 시세 요청이면 market_price_stats를 이 id로 호출하라."
        )
    recent_block = _recent_listings_prompt_block(context)
    if recent_block:
        prompt += f"\n\n{recent_block}"
    if original_query:
        # 맥락 재작성기(contextualize)가 직전 매물의 속성(연식 등)을 질의문에 구워 넣으면
        # 에이전트는 "사용자가 그 연식을 요구했다"고 오인해 필터를 지어낸다(실측 2026-09-01:
        # "같은 차중에서 무사고 스마트크루즈" → 재작성 "2019년식 모델 중…" → year=2019 필터로
        # 2018년식 정답 누락). 원문을 함께 줘서 필터 판단 기준을 원문으로 고정한다.
        prompt += (
            f"\n\n[사용자 원문]\n{original_query}\n"
            "(검색 필터를 걸지 말지는 이 원문을 기준으로 판단하라 — 재작성된 질의에 직전 매물의 "
            "연식·주행거리 등 속성이 끼어 있어도, 원문에서 사용자가 직접 요구하지 않았다면 그 값은 "
            "어느 매물을 가리키는지 알려주는 맥락일 뿐 필터 조건이 아니다.)"
        )
    return prompt


@_traceable(name="run_search_agent", run_type="chain")
def run_search_agent(query: str, context: list | None = None, listing_id: str | None = None) -> dict:
    """툴콜링 에이전트 루프를 1회 실행해 {answer, listings[], route, clarify, narrowed_by,
    market_diagnosis, tools_used}를 반환한다.

    GEMINI_API_KEY/DATABASE_URL 부재는 도구·LLM 내부의 require()가 명확한 한국어 에러로
    즉시 실패한다(조용한 빈 결과 금지 — 기존 노드들과 동일한 fail-loud 원칙).

    listing_id(선택, 5단계): 상세 페이지 "AI 시세 진단" 버튼이 프리필 질의와 함께 보낸 대상
    매물 id. 있으면 시스템 프롬프트에 힌트를 덧붙인다(_system_prompt) — 기본값 None이라
    기존 호출부(호출 시 인자를 안 주는 곳)는 회귀 없이 그대로 동작한다.
    """
    effective_query = contextualize_query(query, context)  # 단일턴이면 query 그대로 반환
    if not (effective_query or "").strip():
        effective_query = query  # graph.run_search와 동일한 방어선(재작성 결과 공백 대비).

    if _deterministic_reject(effective_query):
        return _reject_result(effective_query)

    base_llm = _llm()  # 키 부재 시 여기서 fail-loud — 루프 진입 전에 즉시 실패.
    tool_llm = base_llm.bind_tools(AGENT_TOOLS)

    original = query if effective_query != query else None  # 재작성이 실제로 일어난 턴만 원문 병기
    messages: list = [SystemMessage(_system_prompt(listing_id, context, original)), HumanMessage(effective_query)]
    seen_listings: dict[str, ListingCard] = {}
    tools_used: list[str] = []
    market_diagnosis: dict | None = None
    # 다건 시세 진단(2026-08-31, 사용자 승인) — market_price_stats 호출마다 결과를 전부
    # 모아둔다(매물을 못 찾은 호출은 artifact가 None이라 담기지 않는다). 상한
    # _MAX_MARKET_DIAGNOSES는 프롬프트·응답 크기를 무한정 키우지 않기 위한 설계 확정값 —
    # _MAX_STEPS(6)보다 크게 잡을 이유가 없다(한 스텝에 도구 호출이 여럿이어도 실사용에서
    # market_price_stats만 6번 넘게 부르는 경우는 없다고 가정).
    market_diagnoses_all: list[dict] = []

    for _step in range(_MAX_STEPS):
        ai_msg = tool_llm.invoke(messages)
        messages.append(ai_msg)
        if not ai_msg.tool_calls:
            break  # 자연 종료 — 모델이 더 이상 도구를 요청하지 않는다.

        for tool_call in ai_msg.tool_calls:
            tool_name = tool_call.get("name")
            tools_used.append(tool_name)
            tool_obj = TOOLS_BY_NAME.get(tool_name)
            if tool_obj is None:
                # 모델이 존재하지 않는 도구 이름을 지어낸 경우(환각) — 실행 대신 오류를
                # ToolMessage로 돌려줘 모델이 스스로 고치게 한다(라우터·SQL 노드의 재생성
                # 재시도 패턴과 같은 태도, 루프를 그대로 죽이지 않는다).
                messages.append(
                    ToolMessage(content=f"알 수 없는 도구입니다: {tool_name}", tool_call_id=tool_call["id"])
                )
                continue
            try:
                tool_msg = tool_obj.invoke(tool_call)
            except Exception as exc:  # 도구 내부 오류(DB·검증 등) — 루프를 죽이지 않고 모델에 알린다.
                logger.warning("agent 도구 %s 실행 실패: %r", tool_name, exc)
                messages.append(
                    ToolMessage(content=f"도구 실행 중 오류가 발생했습니다: {exc}", tool_call_id=tool_call["id"])
                )
                continue

            messages.append(tool_msg)
            artifact = getattr(tool_msg, "artifact", None)
            if tool_name in ("search_listings", "compare_listings") and artifact:
                for card in artifact:
                    seen_listings[card.id] = card
            elif tool_name == "market_price_stats":
                # "마지막 호출 1건"을 그대로 반영한다 — 매물을 못 찾은 마지막 호출이면
                # market_diagnosis도 None으로 덮인다(가장 최근 상태를 있는 그대로 노출).
                market_diagnosis = artifact
                if artifact is not None and len(market_diagnoses_all) < _MAX_MARKET_DIAGNOSES:
                    market_diagnoses_all.append(artifact)
    # for-else 없이 자연 종료(break)든 상한 도달(루프 그냥 끝남)이든 아래에서 동일하게
    # 지금까지 쌓인 messages로 최종 구조화 응답을 1회 만든다(설계: "도구 결과까지로 강제
    # 최종 응답" — 자연 종료 경로도 같은 structured-output 관문을 거쳐야 계약이 일정하다).

    final = _finalize(base_llm, messages, found_count=len(seen_listings))

    listings = [seen_listings[lid] for lid in final.selected_listing_ids if lid in seen_listings]
    clarify = final.clarify
    if clarify is not None and listings:
        # 모순 응답 방지(회귀 실측 S1): 매물을 골라놓고 clarify까지 채우면 검색 결과가 우선 —
        # 카드 0장 + "찾았다" 서술 + 되묻기 조합보다 매물 제시가 항상 낫다. 순수 되묻기
        # (selected 비어 있음)는 기존 계약대로 매물 없음이 자연 유지된다.
        clarify = None

    # 진단 차트는 "매물 하나의 시세 진단"일 때만 노출한다 — 추천 흐름(카드 2장 이상)에서
    # 에이전트가 후보 검증용으로 market_price_stats를 여러 번 불러도, 마지막 1건의 차트만
    # 덜렁 붙어 혼란스럽다는 사용자 실측 지적(2026-08-31). 내부 도구 사용은 그대로 두고
    # 노출만 거른다(결정론 규칙 — LLM 판단에 맡기지 않음).
    if market_diagnosis is not None and len(listings) > 1:
        market_diagnosis = None

    # 다건 시세 진단 노출 — market_price_stats가 실제로 2건 이상 결과를 냈을 때만 채운다.
    # 1건 이하면 None(웹은 기존 market_diagnosis 단건 차트를 그대로 쓴다, additive).
    market_diagnoses = market_diagnoses_all if len(market_diagnoses_all) >= 2 else None

    logger.info(
        "run_search_agent 질의=%r → 도구=%r 매물=%d건 clarify=%s",
        effective_query, tools_used, len(listings), clarify is not None,
    )

    return {
        "answer": final.answer,
        "listings": listings,
        "route": "AGENT",
        "clarify": clarify.model_dump() if clarify is not None else None,
        "narrowed_by": None,
        "market_diagnosis": market_diagnosis,
        "market_diagnoses": market_diagnoses,
        "tools_used": tools_used,
    }
