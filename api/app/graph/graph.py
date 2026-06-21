"""검색 파이프라인 StateGraph 조립 — router → (A/B/C) → answer → END (FR13·FR16·FR17).

architecture가 그린 단일 파이프라인을 LangGraph StateGraph로 묶는다.
  질의 → 라우터(의도 A/B/C 분류) → 분기:
    · A → sql_rag_node  (경로 A: Text-to-SQL)
    · B → doc_rag_node  (경로 B: 문서 RAG)
    · C → guard_node    (경로 C: 정중한 거절)
  → answer_node(공통 계약 {answer, listings[]} 보장 + FR17 0건 안내) → END.

설계 결정(OI2): architecture가 StateGraph(LangGraph)와 graph/ 노드 파일을 명시했으므로
  함수형 대안 대신 StateGraph를 채택한다. 노드 4개 단순 분기라 conditional_edges 한 번으로 충분.
  컴파일 비용을 매 요청마다 치르지 않도록 모듈 import 시 1회만 compile한다(함정 #4).

중요(함정 #1) — 경로 A 어댑터는 SqlGuardError를 삼키지 않는다.
  sql_rag_node가 가드 차단으로 SqlGuardError를 던지면 그대로 그래프 밖(/ai/search)으로
  전파돼 기존 핸들러가 400으로 잡아야 한다. 어댑터가 try/except로 감싸 빈 결과로 바꾸면
  400이 사라지는 회귀가 난다 → 절대 감싸지 않는다.
[Source: story 4.5 graph 설계; architecture.md#AI 데이터 흐름·OI2; 함정 #1·#4]
"""

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from app.graph.answer_node import answer_node
from app.graph.contextualize_node import contextualize_query
from app.graph.doc_rag_node import doc_rag_node
from app.graph.guard_node import guard_node
from app.graph.router_node import router_node
from app.graph.sql_rag_node import sql_rag_node

logger = logging.getLogger(__name__)


class SearchState(TypedDict, total=False):
    """그래프 상태 — 노드 사이를 흐르는 최소 dict."""

    query: str            # 입력 질의(라우터·경로 노드가 읽음)
    route: str            # 라우터 판정 "A"/"B"/"C"
    answer: str           # 경로/answer 노드가 채우는 자연어 설명
    listings: list        # 매물 카드 목록(ListingCard)


def _router_step(state: SearchState) -> SearchState:
    """라우터 노드 — 질의를 A/B/C로 분류해 state["route"]에 기록(FR13)."""
    route = router_node(state["query"])
    return {"route": route}


def _sql_step(state: SearchState) -> SearchState:
    """경로 A 어댑터 — sql_rag_node 호출. SqlGuardError는 삼키지 않고 전파(함정 #1)."""
    result = sql_rag_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"]}


def _doc_step(state: SearchState) -> SearchState:
    """경로 B 어댑터 — doc_rag_node(의미형 RAG) 호출."""
    result = doc_rag_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"]}


def _guard_step(state: SearchState) -> SearchState:
    """경로 C 어댑터 — guard_node(정중한 거절) 호출(FR16)."""
    result = guard_node(state["query"])
    return {"answer": result["answer"], "listings": result["listings"]}


def _answer_step(state: SearchState) -> SearchState:
    """답변 조립 노드 — 공통 계약 정규화 + FR17 0건 안내."""
    return answer_node({"answer": state.get("answer", ""), "listings": state.get("listings", [])})


def _route_decision(state: SearchState) -> str:
    """conditional_edges 분기 키 — route 값(A/B/C)에 따라 다음 노드를 고른다.

    router_node가 이미 A/B/C로 보정해 주지만, 혹시 모를 예외값은 안전하게 guard로 보낸다
    (조용히 잘못된 경로로 흘리지 않는다).
    """
    route = state.get("route")
    if route in ("A", "B", "C"):
        return route
    logger.warning("_route_decision 예기치 못한 route=%r → guard(C)로 안전 보정", route)
    return "C"


def _build_graph():
    """StateGraph 조립: router → conditional(A/B/C) → 각 경로 노드 → answer → END."""
    g = StateGraph(SearchState)
    g.add_node("router", _router_step)
    g.add_node("sql", _sql_step)
    g.add_node("doc", _doc_step)
    g.add_node("guard", _guard_step)
    g.add_node("answer", _answer_step)

    g.set_entry_point("router")
    # 라우터 분류값으로 세 경로 중 하나로 분기.
    g.add_conditional_edges(
        "router",
        _route_decision,
        {"A": "sql", "B": "doc", "C": "guard"},
    )
    # 어느 경로를 타든 마지막엔 answer_node로 모여 계약을 보장한 뒤 종료.
    g.add_edge("sql", "answer")
    g.add_edge("doc", "answer")
    g.add_edge("guard", "answer")
    g.add_edge("answer", END)
    return g.compile()


# 모듈 import 시 1회만 컴파일(요청마다 재빌드 금지 — 함정 #4).
COMPILED_GRAPH = _build_graph()


def run_search(query: str, context: list | None = None) -> dict:
    """그래프를 1회 실행해 {answer, listings[]}를 반환한다.

    멀티턴(FR18): 그래프 호출 "앞단"에서 contextualize_query(query, context)로 직전 대화를
      흡수한 독립 질의를 만든 뒤, 그 질의를 그래프에 흘린다. 맥락이 없으면(None·[]) 원 질의가
      그대로 들어가 4.5까지와 동일하게 동작한다(회귀 0). 맥락은 인자로만 흐르고 저장하지 않는다(무상태).
    /ai/search가 sql_rag_node 직접 호출 대신 이 함수를 부른다.
    경로 A에서 SqlGuardError가 나면 여기서 잡지 않고 호출자(/ai/search)로 전파한다(함정 #1).
    """
    effective_query = contextualize_query(query, context)  # 단일턴이면 query 그대로 반환
    # 방어선 — 재작성 결과가 (예기치 못하게) 공백이면 원 질의로 되돌린다. 공개 경로는
    # 스키마가 빈 질의를 422로 이미 막지만, run_search는 내부에서도 재사용되는 함수이므로
    # 빈 질의가 그래프(라우터·LLM)로 새어 들어가지 않게 한 번 더 잠근다.
    if not (effective_query or "").strip():
        effective_query = query
    final_state = COMPILED_GRAPH.invoke({"query": effective_query})
    return {"answer": final_state["answer"], "listings": final_state["listings"]}
