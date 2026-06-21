"""검색 그래프 단위 테스트 — 분기 라우팅·가드·answer_node FR17을 네트워크 없이 검증(AC6).

router_node·sql_rag_node·doc_rag_node를 모킹해 route 값에 따라 올바른 경로 노드만
호출되는지(분기), guard가 listings=[]+유도 문구를 주는지(C), answer_node가 0건에
FR17 안내를 주입하는지 확인한다. LLM/DB는 일절 호출하지 않는다.
"""

import app.graph.graph as gmod
from app.graph.answer_node import answer_node, _EMPTY_FALLBACK
from app.graph.guard_node import guard_node


# ── 그래프 분기 라우팅 ─────────────────────────────────────────────
def _patch_nodes(monkeypatch, *, route, sql=None, doc=None):
    """라우터를 고정 route로, 경로 노드를 호출 추적용 가짜로 치환한다."""
    calls = {"sql": 0, "doc": 0, "guard": 0}

    def fake_sql(query):
        calls["sql"] += 1
        return sql or {"answer": "SQL 결과", "listings": ["s1"]}

    def fake_doc(query):
        calls["doc"] += 1
        return doc or {"answer": "DOC 결과", "listings": ["d1"]}

    real_guard = gmod.guard_node

    def fake_guard(query):
        calls["guard"] += 1
        return real_guard(query)

    monkeypatch.setattr(gmod, "router_node", lambda q: route)
    monkeypatch.setattr(gmod, "sql_rag_node", fake_sql)
    monkeypatch.setattr(gmod, "doc_rag_node", fake_doc)
    monkeypatch.setattr(gmod, "guard_node", fake_guard)
    return calls


def test_route_A_calls_sql_only(monkeypatch):
    calls = _patch_nodes(monkeypatch, route="A")
    out = gmod.run_search("3천만원 이하 SUV")
    assert calls["sql"] == 1 and calls["doc"] == 0 and calls["guard"] == 0
    assert out["answer"] == "SQL 결과" and out["listings"] == ["s1"]


def test_route_B_calls_doc_only(monkeypatch):
    calls = _patch_nodes(monkeypatch, route="B")
    out = gmod.run_search("패밀리카로 무난한 거")
    assert calls["doc"] == 1 and calls["sql"] == 0 and calls["guard"] == 0
    assert out["answer"] == "DOC 결과" and out["listings"] == ["d1"]


def test_route_C_calls_guard_and_returns_empty_listings(monkeypatch):
    calls = _patch_nodes(monkeypatch, route="C")
    out = gmod.run_search("오늘 날씨 어때?")
    assert calls["guard"] == 1 and calls["sql"] == 0 and calls["doc"] == 0
    assert out["listings"] == []  # 매물 무관 → 빈 목록(FR16)
    assert "중고차" in out["answer"]  # 검색 유도 문구


def test_unexpected_route_falls_back_to_guard(monkeypatch):
    # router가 예외값을 줘도 _route_decision이 안전하게 guard로 보낸다.
    calls = _patch_nodes(monkeypatch, route="Z")
    out = gmod.run_search("뭐라도")
    assert calls["guard"] == 1
    assert out["listings"] == []


def test_sql_guard_error_propagates_out_of_graph(monkeypatch):
    # 함정 #1 — 경로 A의 SqlGuardError는 그래프가 삼키지 않고 호출자에게 전파돼야 한다.
    from app.db.sql_guard import SqlGuardError

    def raising_sql(query):
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    monkeypatch.setattr(gmod, "router_node", lambda q: "A")
    monkeypatch.setattr(gmod, "sql_rag_node", raising_sql)

    import pytest

    with pytest.raises(SqlGuardError) as exc:
        gmod.run_search("매물 삭제해줘")
    assert exc.value.code == "not_select"


# ── answer_node 계약·FR17 ─────────────────────────────────────────
def test_answer_node_preserves_existing_answer_and_listings():
    out = answer_node({"answer": "찾았어요", "listings": ["a", "b"]})
    assert out == {"answer": "찾았어요", "listings": ["a", "b"]}


def test_answer_node_empty_result_injects_fr17_fallback():
    # 0건 + 빈 answer → FR17 공통 안내 주입(조용한 빈 결과 금지).
    out = answer_node({"answer": "", "listings": []})
    assert out["listings"] == []
    assert out["answer"] == _EMPTY_FALLBACK


def test_answer_node_none_listings_normalized_to_list():
    out = answer_node({"answer": "x", "listings": None})
    assert out["listings"] == []
    assert out["answer"] == "x"


def test_answer_node_listings_present_but_blank_answer_gets_count():
    # 매물은 있는데 문구가 비었으면 최소 건수 안내라도 채운다(빈 답 금지).
    out = answer_node({"answer": "  ", "listings": ["a", "b", "c"]})
    assert "3건" in out["answer"]
    assert out["listings"] == ["a", "b", "c"]


def test_answer_node_respects_node_empty_message():
    # 노드가 자기 0건 문구를 이미 채웠으면 fallback으로 덮어쓰지 않는다.
    msg = "조건에 맞는 매물이 없어요. 가격대를 넓혀보세요."
    out = answer_node({"answer": msg, "listings": []})
    assert out["answer"] == msg


# ── guard_node 직접 ───────────────────────────────────────────────
def test_guard_node_returns_empty_listings_and_guidance():
    out = guard_node("파이썬 코드 짜줘")
    assert out["listings"] == []
    assert "중고차" in out["answer"] and "어시스턴트" in out["answer"]


# ── 4.6 멀티턴 맥락화 배선 (run_search 앞단) ───────────────────────
def test_run_search_contextualizes_before_graph(monkeypatch):
    # context가 있으면 run_search가 contextualize_query로 재작성한 질의를 그래프(라우터)에 넘긴다.
    seen_query = {}

    def fake_router(q):
        seen_query["q"] = q  # 라우터가 받은 질의(=맥락화 결과)를 캡처
        return "B"

    monkeypatch.setattr(gmod, "router_node", fake_router)
    monkeypatch.setattr(gmod, "doc_rag_node", lambda q: {"answer": "ok", "listings": []})
    # 맥락화는 재작성된 독립 질의를 돌려주도록 모킹(LLM 없이).
    monkeypatch.setattr(gmod, "contextualize_query", lambda query, context: "재작성된 독립 질의")

    out = gmod.run_search("그 중 더 싼 거", [{"role": "user", "content": "패밀리카"}])
    assert seen_query["q"] == "재작성된 독립 질의"  # 그래프는 재작성 질의를 처리
    assert out["listings"] == []


def test_run_search_single_turn_passes_query_unchanged(monkeypatch):
    # context 없으면 원 query가 그대로 그래프로 간다(단일턴 회귀 0). 실제 contextualize_query 사용.
    seen_query = {}

    def fake_router(q):
        seen_query["q"] = q
        return "A"

    monkeypatch.setattr(gmod, "router_node", fake_router)
    monkeypatch.setattr(gmod, "sql_rag_node", lambda q: {"answer": "ok", "listings": ["s1"]})

    gmod.run_search("3천만원 이하 SUV")  # context 없음 → contextualize_query가 LLM 없이 그대로 반환
    assert seen_query["q"] == "3천만원 이하 SUV"
