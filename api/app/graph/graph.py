"""검색 파이프라인 StateGraph 조립 — router → (REJECT/CLARIFY/SQL/HYBRID) → answer → END
(FR13·FR16·FR17·FR43·FR45·FR46, 13.3 하이브리드 검색, 13.4 조건 좁혀 되묻기).

architecture가 그린 단일 파이프라인을 LangGraph StateGraph로 묶는다.
  질의 → 라우터(의도 4분류) → 분기:
    · SQL     → sql_rag_node    (구조형: Text-to-SQL)
    · HYBRID  → hybrid_rag_node (조합형: 구조조건 + 벡터 단일쿼리, Story 13.3)
    · CLARIFY → clarify_node    (질적·의미형, 되묻기 — Story 13.4. 고정 템플릿, LLM/DB 없음)
    · REJECT  → guard_node      (매물 무관: 정중한 거절)
  → answer_node(공통 계약 {answer, listings[], clarify, narrowed_by} 보장 + FR17 0건 안내) → END.

13.4(되묻기 상한, DW-563): CLARIFY 분기는 매 요청마다 클라이언트가 보내는 `context`(FR18)의
  길이로 서버가 직접 상한을 판정한다(`_clarify_step`). 상한(`_CLARIFY_TURN_CAP`) 이상이면
  클라이언트 협조와 무관하게 `clarify_node` 대신 `doc_rag_node`를 직접 호출해 현재까지의
  조건으로 실제 매물을 강제 제시한다 — 클라이언트만 세는 상한은 상한이 아니라는 판단(DW-563 해결).
  ⚠️ 세는 대상은 **되묻기 횟수가 아니라 대화 전체 길이**다: `context` 항목엔 라우트 태그가 없어
  "몇 번 연속 되물었는가"를 셀 수 없으므로 대리 신호로 총 턴 수를 쓴다. 따라서 앞선 3턴이 SQL
  검색이었어도 그 다음 애매한 질의는 상한 초과로 처리된다 — 스펙 Design Notes가 기록·수용한
  트레이드오프이며(보수적 방향: 이미 충분히 대화한 사용자에겐 더 묻지 않는다), 이 거동은
  `test_clarify_cap_counts_all_turns_not_only_clarify_turns`가 검사로 고정하고 있다.

설계 결정(OI2): architecture가 StateGraph(LangGraph)와 graph/ 노드 파일을 명시했으므로
  함수형 대안 대신 StateGraph를 채택한다. 노드 5개 단순 분기라 conditional_edges 한 번으로 충분.
  컴파일 비용을 매 요청마다 치르지 않도록 모듈 import 시 1회만 compile한다(함정 #4).

중요(함정 #1) — SQL·HYBRID 어댑터는 SqlGuardError를 삼키지 않는다.
  sql_rag_node·hybrid_rag_node가 가드 차단으로 SqlGuardError를 던지면 그대로 그래프 밖
  (/ai/search)으로 전파돼 기존 핸들러가 400으로 잡아야 한다. 어댑터가 try/except로 감싸
  빈 결과로 바꾸면 400이 사라지는 회귀가 난다 → 절대 감싸지 않는다.
[Source: story 4.5 graph 설계; spec-13-3-하이브리드-검색-sql-벡터.md; architecture.md#AI 데이터 흐름·OI2; 함정 #1·#4]
"""

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.graph.answer_node import answer_node
from app.graph.clarify_node import clarify_node
from app.graph.contextualize_node import contextualize_query
from app.graph.doc_rag_node import doc_rag_node
from app.graph.guard_node import guard_node
from app.graph.hybrid_rag_node import hybrid_rag_node
from app.graph.router_node import router_node
from app.graph.sql_rag_node import sql_rag_node

logger = logging.getLogger(__name__)

# 되묻기 상한(FR46, "최대 2~3턴" 상단값을 코드가 요구하는 단일 정수로 확정) — 대화가 이 턴 수
# 이상 진행됐으면 서버가 clarify_node 대신 doc_rag_node로 강제 폴백한다(DW-563).
# 비교는 `>=`다 — 즉 정확히 3턴째부터 이미 초과 처리이고, 되묻기는 0~2턴 시점까지만 허용된다.
_CLARIFY_TURN_CAP = 3
# 강제 폴백이 매물을 1건 이상 반환할 때만 덧붙이는 고정 안내(0건이면 doc_rag_node의 FR17 안내와
# 모순되므로 덧붙이지 않는다).
_CLARIFY_CAP_NOTICE = "여기까지의 조건으로 찾아드릴게요. 더 좁히시려면 검색 후 필터를 이용해보세요."


class SearchState(TypedDict, total=False):
    """그래프 상태 — 노드 사이를 흐르는 최소 dict."""

    query: str            # 입력 질의(라우터·경로 노드가 읽음)
    route: str            # 라우터 판정 "REJECT"/"CLARIFY"/"SQL"/"HYBRID"
    answer: str           # 경로/answer 노드가 채우는 자연어 설명
    listings: list        # 매물 카드 목록(ListingCard)
    clarify: dict | None  # CLARIFY 되묻기 페이로드({question, chips}) — clarify 노드가 채움
    clarify_turns: int    # 대화 전체 턴 수(되묻기 횟수 아님) — run_search가 진입 시점에 계산(13.4)
    narrowed_by: list[str] | None  # REJECT 전용 고정 상수(13.5) — SQL/HYBRID/CLARIFY는 None


def _router_step(state: SearchState) -> SearchState:
    """라우터 노드 — 질의를 REJECT/CLARIFY/SQL/HYBRID로 분류해 state["route"]에 기록(FR13·FR43)."""
    route = router_node(state["query"])
    return {"route": route}


def _sql_step(state: SearchState) -> SearchState:
    """SQL 어댑터 — sql_rag_node(Text-to-SQL) 호출. SqlGuardError는 삼키지 않고 전파(함정 #1)."""
    result = sql_rag_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"]}


def _hybrid_step(state: SearchState) -> SearchState:
    """HYBRID 어댑터 — hybrid_rag_node(구조조건+벡터 단일쿼리, Story 13.3) 호출.

    SqlGuardError는 _sql_step과 동일하게 감싸지 않고 그대로 전파한다(함정 #1) — 그래야
    가드가 2회 연속 차단할 때 /ai/search까지 SqlGuardError가 올라가 400(500 아님)이 된다.
    """
    result = hybrid_rag_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"]}


def _clarify_step(state: SearchState) -> SearchState:
    """CLARIFY 어댑터 — 되묻기 상한 이내면 clarify_node, 초과면 doc_rag_node로 강제 폴백(13.4, DW-563).

    대화가 상한(_CLARIFY_TURN_CAP) 턴 이상 진행됐으면 — 그 앞 턴들이 되묻기였든 SQL 검색이었든
    무관하게(clarify_turns는 라우트를 구분하지 않는 총 턴 수다) — 클라이언트 협조 여부와 무관하게 doc_rag_node(의미형
    RAG)를 직접 호출해 현재까지의 조건(effective_query)으로 실제 매물을 강제 제시한다. 매물이
    1건 이상이면 고정 안내(_CLARIFY_CAP_NOTICE)를 answer 뒤에 덧붙이고, 0건이면 doc_rag_node의
    기존 FR17 안내를 그대로 둔다(0건인데 "필터로 더 좁혀라"라고 말하는 모순 방지). 이 경로에서
    clarify는 항상 None(칩 없음 — 더 이상 안 묻는다는 신호).
    """
    if state.get("clarify_turns", 0) >= _CLARIFY_TURN_CAP:
        result = doc_rag_node(state["query"])
        answer = result["answer"]
        if result["listings"]:
            answer = f"{answer} {_CLARIFY_CAP_NOTICE}"
        return {"answer": answer, "listings": result["listings"], "clarify": None}

    result = clarify_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"], "clarify": result["clarify"]}


def _guard_step(state: SearchState) -> SearchState:
    """REJECT 어댑터 — guard_node(정중한 거절) 호출(FR16·FR47). narrowed_by 고정 상수를 통과시킨다(13.5)."""
    result = guard_node(state["query"])
    return {
        "answer": result["answer"],
        "listings": result["listings"],
        "narrowed_by": result["narrowed_by"],
    }


def _answer_step(state: SearchState) -> SearchState:
    """답변 조립 노드 — 공통 계약 정규화 + FR17 0건 안내 + clarify/narrowed_by 통과(13.4/13.5)."""
    return answer_node(
        {
            "answer": state.get("answer", ""),
            "listings": state.get("listings", []),
            "clarify": state.get("clarify"),
            "narrowed_by": state.get("narrowed_by"),
        }
    )


def _route_decision(state: SearchState) -> str:
    """conditional_edges 분기 키 — route 값(REJECT/CLARIFY/SQL/HYBRID)에 따라 다음 노드를 고른다.

    router_node가 이미 4값으로 보정해 주지만, 혹시 모를 예외값은 안전하게 guard로 보낸다
    (조용히 잘못된 경로로 흘리지 않는다).
    """
    route = state.get("route")
    if route in ("REJECT", "CLARIFY", "SQL", "HYBRID"):
        return route
    logger.warning("_route_decision 예기치 못한 route=%r → guard(REJECT)로 안전 보정", route)
    return "REJECT"


def _build_graph():
    """StateGraph 조립: router → conditional(REJECT/CLARIFY/SQL/HYBRID) → 각 경로 노드 → answer → END."""
    g = StateGraph(SearchState)
    g.add_node("router", _router_step)
    g.add_node("sql", _sql_step)
    g.add_node("hybrid", _hybrid_step)
    g.add_node("clarify", _clarify_step)
    g.add_node("guard", _guard_step)
    g.add_node("answer", _answer_step)

    g.set_entry_point("router")
    # 라우터 분류값으로 네 경로 중 하나로 분기. HYBRID는 hybrid_rag_node로(Story 13.3),
    # CLARIFY는 clarify_step으로(Story 13.4 — 상한 이내는 clarify_node, 초과는 doc_rag_node 강제 폴백).
    g.add_conditional_edges(
        "router",
        _route_decision,
        {"REJECT": "guard", "SQL": "sql", "HYBRID": "hybrid", "CLARIFY": "clarify"},
    )
    # 어느 경로를 타든 마지막엔 answer_node로 모여 계약을 보장한 뒤 종료.
    g.add_edge("sql", "answer")
    g.add_edge("hybrid", "answer")
    g.add_edge("clarify", "answer")
    g.add_edge("guard", "answer")
    g.add_edge("answer", END)
    return g.compile()


# 모듈 import 시 1회만 컴파일(요청마다 재빌드 금지 — 함정 #4).
COMPILED_GRAPH = _build_graph()


def run_search(query: str, context: list | None = None) -> dict:
    """그래프를 1회 실행해 {answer, listings[], route, clarify, narrowed_by}를 반환한다.

    멀티턴(FR18): 그래프 호출 "앞단"에서 contextualize_query(query, context)로 직전 대화를
      흡수한 독립 질의를 만든 뒤, 그 질의를 그래프에 흘린다. 맥락이 없으면(None·[]) 원 질의가
      그대로 들어가 4.5까지와 동일하게 동작한다(회귀 0). 맥락은 인자로만 흐르고 저장하지 않는다(무상태).
    /ai/search가 sql_rag_node 직접 호출 대신 이 함수를 부른다.
    SQL 경로(route=SQL·HYBRID)에서 SqlGuardError가 나면 여기서 잡지 않고 호출자(/ai/search)로
    전파한다(함정 #1).

    "route"는 13.1이 추가한 부가 키다(G2 baseline 러너 `scripts/run_phase_b.py`가 라우팅
      채점에 씀) — 기존 소비처(/ai/search·test_graph.py 등)는 answer/listings만 꺼내 쓰므로
      추가 키가 있어도 회귀 없다(additive).
    "narrowed_by"는 13.5가 추가한 REJECT 전용 고정 상수 키다 — SQL/HYBRID/CLARIFY 경로는
      None(회귀 없음, additive).
    """
    effective_query = contextualize_query(query, context)  # 단일턴이면 query 그대로 반환
    # 방어선 — 재작성 결과가 (예기치 못하게) 공백이면 원 질의로 되돌린다. 공개 경로는
    # 스키마가 빈 질의를 422로 이미 막지만, run_search는 내부에서도 재사용되는 함수이므로
    # 빈 질의가 그래프(라우터·LLM)로 새어 들어가지 않게 한 번 더 잠근다.
    if not (effective_query or "").strip():
        effective_query = query
    # 13.4(DW-563): 서버가 이미 매 요청마다 받는 context(FR18)의 길이로 "대화가 몇 턴 진행됐는가"를
    # 직접 계산한다 — 클라이언트가 스스로 멈추기를 기다리지 않는다. 한 턴 = user+assistant 2개 항목.
    # 이름과 달리 "되묻기 횟수"가 아니다: context 항목엔 라우트 태그가 없어 연속 CLARIFY 횟수는
    # 셀 수 없고, 대화 전체 길이를 대리 신호로 쓴다(스펙 Design Notes가 기록·수용한 근사치).
    clarify_turns = len(context or []) // 2
    final_state = COMPILED_GRAPH.invoke({"query": effective_query, "clarify_turns": clarify_turns})
    return {
        "answer": final_state["answer"],
        "listings": final_state["listings"],
        "route": final_state.get("route", ""),
        "clarify": final_state.get("clarify"),
        "narrowed_by": final_state.get("narrowed_by"),
    }
