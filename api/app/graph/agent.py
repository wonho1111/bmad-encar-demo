"""툴콜링 에이전트 루프 — 4단계 부품 B(DW-847·848·849를 에이전트 구조로 해결).

진입점 `run_search_agent(query, context=None) -> dict`. 반환 계약은 기존 run_search(graph.py)와
  동일한 {answer, listings[], route, clarify, narrowed_by}에 두 키를 더한다:
  `market_diagnosis: dict|None`(직전 market_price_stats 호출 결과), `tools_used: list[str]`
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
from app.graph import router_node as _router_node
from app.graph.agent_tools import AGENT_TOOLS, TOOLS_BY_NAME
from app.graph.contextualize_node import contextualize_query
from app.graph.guard_node import guard_node
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

_SYSTEM_PROMPT = """너는 중고차 매물을 상담해 추천하는 에이전트다. 아래 도구를 이용해
사용자의 조건에 맞는 매물을 찾고, 필요하면 근거를 곁들여 추천한다.

[도구] — 아래 4개만 실제로 호출 가능한 도구다. 그 외 이름(예: "clarify")은 도구가 아니다 —
되묻기는 도구 호출이 아니라 최종 답변의 clarify 필드를 채우는 것이다(아래 [되묻기 규칙] 참조).
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

[되묻기 규칙]
조건이 모호해 무엇을 찾아야 할지 판단할 수 없으면(예: "차 추천해줘"처럼 예산·용도·차종이
전혀 없음) 매물을 검색하지 말고 도구를 호출하지 말고, 최종 응답의 clarify 필드를 채워서
되물어라 — question은 무엇이 부족한지 짧게 묻고, chips는 그 질의 맥락에 맞는 후보 2~4개를
직접 만들어라(고정 문구를 반복하지 말고 질의 내용에 맞춰라). clarify를 채울 때 answer는
짧은 안내 한 줄만 남긴다.

[금지 사항]
- 수치(시세·통계·가격·연식·주행거리 등)는 도구가 실제로 돌려준 값만 인용한다 — 지어내지
  않는다. 특히 시세·적정가·가격대는 market_price_stats를 호출해 받은 값이 아니면 절대
  언급하지 마라(대략적인 범위 추정도 금지 — 모르면 search_listings/market_price_stats로
  확인하거나, 그래도 판단이 안 서면 clarify로 되물어라).
- 시세 설명에서 비교군의 성격은 market_price_stats 결과의 criteria(step·desc)를 그대로
  따른다 — 완화가 있었으면(예: "세대 해제") 그 사실을 언급하고, 완화된 비교군을 "동일
  모델 비교군"이라고 표현하지 마라(실제와 다른 설명이 된다).
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
        "tools_used": [],
    }


def _finalize(base_llm: ChatGoogleGenerativeAI, messages: list) -> _AgentFinalOutput:
    """도구 없이 structured output 1회 호출로 최종 응답을 만든다(router_node와 동일 관례)."""
    structured = base_llm.with_structured_output(_AgentFinalOutput)
    return structured.invoke(messages + [HumanMessage(_FINALIZE_INSTRUCTION)])


def _system_prompt(listing_id: str | None) -> str:
    """기본 시스템 프롬프트에 대상 매물 id 힌트를 덧붙인다(5단계, 상세 페이지 "AI 시세 진단" 버튼).

    도구 강제 호출은 아니다 — LLM이 시세 요청으로 판단할 때 market_price_stats를 이 id로
    호출하도록 프롬프트로만 유도한다(설계: 버튼이 프리필한 질의문 자체도 "이 매물 시세
    알려줘" 형태라 대부분 자연스럽게 이어지지만, id를 명시해 모호성을 줄인다).
    """
    if not listing_id:
        return _SYSTEM_PROMPT
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"[이번 요청의 대상 매물]\n"
        f"이번 요청의 대상 매물 id는 {listing_id}다. 시세 요청이면 market_price_stats를 이 id로 호출하라."
    )


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

    messages: list = [SystemMessage(_system_prompt(listing_id)), HumanMessage(effective_query)]
    seen_listings: dict[str, ListingCard] = {}
    tools_used: list[str] = []
    market_diagnosis: dict | None = None

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
    # for-else 없이 자연 종료(break)든 상한 도달(루프 그냥 끝남)이든 아래에서 동일하게
    # 지금까지 쌓인 messages로 최종 구조화 응답을 1회 만든다(설계: "도구 결과까지로 강제
    # 최종 응답" — 자연 종료 경로도 같은 structured-output 관문을 거쳐야 계약이 일정하다).

    final = _finalize(base_llm, messages)

    listings = [seen_listings[lid] for lid in final.selected_listing_ids if lid in seen_listings]
    clarify = final.clarify
    if clarify is not None:
        listings = []  # 기존 CLARIFY 경로(clarify_node)와 동일 계약 — 되물을 땐 매물 없음.

    # 진단 차트는 "매물 하나의 시세 진단"일 때만 노출한다 — 추천 흐름(카드 2장 이상)에서
    # 에이전트가 후보 검증용으로 market_price_stats를 여러 번 불러도, 마지막 1건의 차트만
    # 덜렁 붙어 혼란스럽다는 사용자 실측 지적(2026-08-31). 내부 도구 사용은 그대로 두고
    # 노출만 거른다(결정론 규칙 — LLM 판단에 맡기지 않음).
    if market_diagnosis is not None and len(listings) > 1:
        market_diagnosis = None

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
        "tools_used": tools_used,
    }
