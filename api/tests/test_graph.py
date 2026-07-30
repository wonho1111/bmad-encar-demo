"""검색 그래프 단위 테스트 — 분기 라우팅·가드·answer_node FR17·CLARIFY 되묻기(13.4)를
네트워크 없이 검증(AC6).

router_node·sql_rag_node·doc_rag_node·clarify_node를 모킹해 route 값에 따라 올바른 경로
노드만 호출되는지(분기), guard가 listings=[]+유도 문구를 주는지(C), answer_node가 0건에
FR17 안내를 주입하는지, CLARIFY가 되묻기 상한 이내/초과에 따라 clarify_node/doc_rag_node
중 올바른 쪽만 타는지(DW-563) 확인한다. LLM/DB는 일절 호출하지 않는다.
"""

import app.graph.graph as gmod
from app.graph.answer_node import answer_node, _EMPTY_FALLBACK
from app.graph.guard_node import guard_node


# ── 그래프 분기 라우팅 ─────────────────────────────────────────────
def _patch_nodes(monkeypatch, *, route, sql=None, hybrid=None, doc=None, clarify=None):
    """라우터를 고정 route로, 경로 노드를 호출 추적용 가짜로 치환한다."""
    calls = {"sql": 0, "hybrid": 0, "doc": 0, "guard": 0, "clarify": 0}

    def fake_sql(query):
        calls["sql"] += 1
        return sql or {"answer": "SQL 결과", "listings": ["s1"]}

    def fake_hybrid(query):
        calls["hybrid"] += 1
        return hybrid or {"answer": "HYBRID 결과", "listings": ["h1"]}

    def fake_doc(query):
        calls["doc"] += 1
        return doc or {"answer": "DOC 결과", "listings": ["d1"]}

    def fake_clarify(query):
        calls["clarify"] += 1
        return clarify or {
            "answer": "되묻기 질문",
            "listings": [],
            "clarify": {"question": "되묻기 질문", "chips": ["a", "b", "c"]},
        }

    real_guard = gmod.guard_node

    def fake_guard(query):
        calls["guard"] += 1
        return real_guard(query)

    monkeypatch.setattr(gmod, "router_node", lambda q: route)
    monkeypatch.setattr(gmod, "sql_rag_node", fake_sql)
    monkeypatch.setattr(gmod, "hybrid_rag_node", fake_hybrid)
    monkeypatch.setattr(gmod, "doc_rag_node", fake_doc)
    monkeypatch.setattr(gmod, "clarify_node", fake_clarify)
    monkeypatch.setattr(gmod, "guard_node", fake_guard)
    return calls


def test_route_SQL_calls_sql_only(monkeypatch):
    calls = _patch_nodes(monkeypatch, route="SQL")
    out = gmod.run_search("3천만원 이하 SUV")
    assert calls["sql"] == 1 and calls["hybrid"] == 0 and calls["doc"] == 0 and calls["guard"] == 0
    assert out["answer"] == "SQL 결과" and out["listings"] == ["s1"]
    # run_phase_b.py→score_ab.py가 routing_correct/gate_pass 채점에 그대로 쓰는 값이라
    # 실제 그래프 배선을 타면서 "SQL"이 채워지는지 못박는다(코드리뷰 패치 — 이전엔 미검증이라
    # route를 항상 빈 문자열로 망가뜨려도 이 테스트들이 전부 통과했었다).
    assert out["route"] == "SQL"


def test_route_HYBRID_calls_hybrid_only(monkeypatch):
    # HYBRID(조합형)는 Story 13.3부터 hybrid_rag_node(구조조건+벡터 단일쿼리)로 실제 배선된다
    # (13.2까지의 sql_rag_node 임시 배선은 여기서 대체됐다).
    calls = _patch_nodes(monkeypatch, route="HYBRID")
    out = gmod.run_search("3천만원 이하로 무난한 패밀리카")
    assert calls["hybrid"] == 1 and calls["sql"] == 0 and calls["doc"] == 0 and calls["guard"] == 0
    assert out["answer"] == "HYBRID 결과" and out["listings"] == ["h1"]
    assert out["route"] == "HYBRID"


def test_route_CLARIFY_calls_clarify_only(monkeypatch):
    # 13.4: CLARIFY는 doc_rag_node 임시 배선(13.2)이 아니라 clarify_node로 실제 배선된다.
    # 되묻기 상한 이내(context 없음 → clarify_turns=0)이므로 clarify_node만 호출되고
    # doc는 더 이상 CLARIFY 경로에서 호출되지 않는다.
    calls = _patch_nodes(monkeypatch, route="CLARIFY")
    out = gmod.run_search("패밀리카로 무난한 거")
    assert calls["clarify"] == 1
    assert calls["doc"] == 0 and calls["sql"] == 0 and calls["hybrid"] == 0 and calls["guard"] == 0
    assert out["answer"] == "되묻기 질문" and out["listings"] == []
    assert out["clarify"] == {"question": "되묻기 질문", "chips": ["a", "b", "c"]}
    assert out["route"] == "CLARIFY"


def test_clarify_turn_cap_not_yet_reached_still_clarifies(monkeypatch):
    # clarify_turns=2 < _CLARIFY_TURN_CAP(3) → 여전히 clarify_node를 호출한다(강제 폴백 없음).
    calls = _patch_nodes(monkeypatch, route="CLARIFY")
    # 이 테스트는 상한 계산(clarify_turns)만 검증한다 — 맥락화 자체(LLM 호출)는 무관하므로
    # contextualize_query를 그대로 통과시키는 가짜로 치환해 네트워크 호출을 막는다.
    monkeypatch.setattr(gmod, "contextualize_query", lambda query, context: query)
    # 2턴(=user+assistant 4개 항목)짜리 context를 흉내낸다 — run_search가 len(context)//2로 계산.
    context = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}] * 2
    out = gmod.run_search("패밀리카로 무난한 거", context)
    assert calls["clarify"] == 1 and calls["doc"] == 0
    assert out["clarify"] is not None
    assert out["listings"] == []


def test_clarify_turn_cap_forces_doc_fallback(monkeypatch):
    # clarify_turns=3(context 길이 6) 이상이면 clarify_node 대신 doc_rag_node를 강제 호출하고
    # 매물이 1건 이상이면 answer에 _CLARIFY_CAP_NOTICE를 덧붙인다(DW-563).
    calls = _patch_nodes(
        monkeypatch,
        route="CLARIFY",
        doc={"answer": "찾은 결과 문구", "listings": ["d1"]},
    )
    monkeypatch.setattr(gmod, "contextualize_query", lambda query, context: query)
    context = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}] * 3
    out = gmod.run_search("패밀리카로 무난한 거", context)
    assert calls["doc"] == 1 and calls["clarify"] == 0
    assert out["clarify"] is None
    assert out["listings"] == ["d1"]
    assert gmod._CLARIFY_CAP_NOTICE in out["answer"]
    assert out["answer"].startswith("찾은 결과 문구")


def test_clarify_cap_counts_all_turns_not_only_clarify_turns(monkeypatch):
    """상한이 세는 것은 **대화 전체 턴 수**이지 "연속 되묻기 횟수"가 아니다 — 기록된 트레이드오프를 고정한다.

    앞선 3턴이 전부 일반 검색(SQL)이었고 되묻기는 한 번도 없었어도, 4번째 애매한 질의는 상한
    초과로 처리돼 칩 없이 결과가 강제 제시된다. `context` 항목엔 라우트 태그가 없어 연속 CLARIFY
    횟수를 셀 수 없기 때문에 대화 길이를 대리 신호로 쓴 결과다(스펙 Design Notes가 인지·수용).

    왜 이 검사가 따로 필요한가: 기존 상한 테스트 3건은 context를 전부 되묻기처럼 생긴 턴으로만
    만들어서, "되묻기 횟수만 센다"는 (틀린) 구현으로 바꿔도 똑같이 초록이다 — 두 해석을 구분하지
    못한다. 이 검사가 그 구분을 맡아, 나중에 누가 "연속 CLARIFY만 세도록" 바꾸면 빨갛게 만든다.
    바꾸는 것이 옳다는 결론이 나면 이 검사를 **의도적으로** 고쳐야 하고, 그때 스펙 Design Notes와
    docs/conventions.md §4도 함께 고쳐진다(조용한 드리프트 방지).
    """
    calls = _patch_nodes(
        monkeypatch,
        route="CLARIFY",
        doc={"answer": "찾은 결과 문구", "listings": ["d1"]},
    )
    monkeypatch.setattr(gmod, "contextualize_query", lambda query, context: query)
    # 되묻기가 아니라 일반 검색 3턴 — 되묻기 횟수는 0이다.
    context = [
        {"role": "user", "content": "3천만원 이하 SUV"},
        {"role": "assistant", "content": "조건에 맞는 매물 5건을 찾았어요."},
        {"role": "user", "content": "2020년 이후로"},
        {"role": "assistant", "content": "조건에 맞는 매물 3건을 찾았어요."},
        {"role": "user", "content": "서울만"},
        {"role": "assistant", "content": "조건에 맞는 매물 2건을 찾았어요."},
    ]
    out = gmod.run_search("패밀리카로 무난한 거", context)
    assert calls["doc"] == 1 and calls["clarify"] == 0
    assert out["clarify"] is None


def test_clarify_turn_cap_forced_but_zero_listings_no_notice(monkeypatch):
    # 같은 상한 초과 조건이라도 doc_rag_node가 0건(FR17 안내)을 반환하면 _CLARIFY_CAP_NOTICE를
    # 덧붙이지 않는다 — "0건인데 필터로 더 좁혀라"라는 모순을 막는다(회귀 방지).
    fr17_msg = "조건에 맞는 매물이 없어요. 원하시는 용도나 예산을 알려주시면 더 잘 찾아드릴게요."
    calls = _patch_nodes(
        monkeypatch,
        route="CLARIFY",
        doc={"answer": fr17_msg, "listings": []},
    )
    monkeypatch.setattr(gmod, "contextualize_query", lambda query, context: query)
    context = [{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}] * 3
    out = gmod.run_search("패밀리카로 무난한 거", context)
    assert calls["doc"] == 1
    assert out["clarify"] is None
    assert out["listings"] == []
    assert out["answer"] == fr17_msg
    assert gmod._CLARIFY_CAP_NOTICE not in out["answer"]


def test_route_REJECT_calls_guard_and_returns_empty_listings(monkeypatch):
    calls = _patch_nodes(monkeypatch, route="REJECT")
    out = gmod.run_search("오늘 날씨 어때?")
    assert calls["guard"] == 1 and calls["sql"] == 0 and calls["hybrid"] == 0 and calls["doc"] == 0
    assert out["listings"] == []  # 매물 무관 → 빈 목록(FR16)
    assert "중고차" in out["answer"]  # 검색 유도 문구
    assert out["route"] == "REJECT"


def test_unexpected_route_falls_back_to_guard(monkeypatch):
    # router가 예외값을 줘도 _route_decision이 안전하게 guard로 보낸다.
    calls = _patch_nodes(monkeypatch, route="Z")
    out = gmod.run_search("뭐라도")
    assert calls["guard"] == 1
    assert out["listings"] == []
    # ⚠️ 실제 동작 그대로 고정: _route_decision은 "어느 노드로 갈지"만 REJECT로 보정하고
    # state["route"] 자체는 원래 라우터 원시값("Z")을 그대로 들고 있다(정규화하지 않음).
    # 즉 run_phase_b.py가 캡처하는 route는 이 raw 값이다 — routing_correct 채점 시
    # 라우터가 4값 밖의 값을 내면 "Z" 그대로 채점 대상이 된다는 뜻(별도 개선은 범위 밖).
    assert out["route"] == "Z"


def test_sql_guard_error_propagates_out_of_graph(monkeypatch):
    # 함정 #1 — 경로 SQL의 SqlGuardError는 그래프가 삼키지 않고 호출자에게 전파돼야 한다.
    from app.db.sql_guard import SqlGuardError

    def raising_sql(query):
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    monkeypatch.setattr(gmod, "router_node", lambda q: "SQL")
    monkeypatch.setattr(gmod, "sql_rag_node", raising_sql)

    import pytest

    with pytest.raises(SqlGuardError) as exc:
        gmod.run_search("매물 삭제해줘")
    assert exc.value.code == "not_select"


def test_hybrid_sql_guard_error_propagates_out_of_graph(monkeypatch):
    # 13.3 리뷰: _hybrid_step 독스트링은 _sql_step과 동일하게 SqlGuardError를 삼키지 않는다고
    # 주장하지만, 그 불변식을 그래프(run_search) 레벨에서 확인하는 짝 테스트가 없었다 —
    # 위 test_sql_guard_error_propagates_out_of_graph(SQL)의 HYBRID 버전.
    from app.db.sql_guard import SqlGuardError

    def raising_hybrid(query):
        raise SqlGuardError("forbidden_or", "OR 조건은 허용되지 않습니다.")

    monkeypatch.setattr(gmod, "router_node", lambda q: "HYBRID")
    monkeypatch.setattr(gmod, "hybrid_rag_node", raising_hybrid)

    import pytest

    with pytest.raises(SqlGuardError) as exc:
        gmod.run_search("3천만원 이하로 무난한 패밀리카")
    assert exc.value.code == "forbidden_or"


# ── answer_node 계약·FR17 ─────────────────────────────────────────
def test_answer_node_preserves_existing_answer_and_listings():
    out = answer_node({"answer": "찾았어요", "listings": ["a", "b"]})
    # 13.4: answer_node가 clarify 키를 계약에 추가로 채우므로(값 없으면 None) 그 키도 함께 확인한다.
    assert out == {"answer": "찾았어요", "listings": ["a", "b"], "clarify": None}


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


def test_answer_node_passes_through_clarify_field():
    # 13.4 함정 #3 승계 — clarify 키가 있으면(값 그대로) 새 판단 없이 그대로 통과시킨다.
    clarify_payload = {"question": "q", "chips": ["a"]}
    out = answer_node({"answer": "q", "listings": [], "clarify": clarify_payload})
    assert out["clarify"] == clarify_payload


def test_answer_node_clarify_absent_defaults_to_none():
    # clarify 키 자체가 없는 결과(기존 sql/hybrid/guard 경로)는 None으로 채워진다.
    out = answer_node({"answer": "찾았어요", "listings": ["a"]})
    assert out["clarify"] is None


# ── guard_node 직접 ───────────────────────────────────────────────
def test_guard_node_returns_empty_listings_and_guidance():
    out = guard_node("파이썬 코드 짜줘")
    assert out["listings"] == []
    # "갈림길" 멘트 — 매물 검색으로 재유도하는 정보(매물·예산·용도)를 담는다(dead-end 0%, 안건2/3).
    assert "매물" in out["answer"] and "예산" in out["answer"]


# ── 4.6 멀티턴 맥락화 배선 (run_search 앞단) ───────────────────────
def test_run_search_contextualizes_before_graph(monkeypatch):
    # context가 있으면 run_search가 contextualize_query로 재작성한 질의를 그래프(라우터)에 넘긴다.
    seen_query = {}

    def fake_router(q):
        seen_query["q"] = q  # 라우터가 받은 질의(=맥락화 결과)를 캡처
        return "CLARIFY"

    monkeypatch.setattr(gmod, "router_node", fake_router)
    # 13.4: CLARIFY 경로가 실제로 부르는 노드는 이제 clarify_node다(doc_rag_node 아님).
    monkeypatch.setattr(
        gmod, "clarify_node", lambda q: {"answer": "ok", "listings": [], "clarify": None}
    )
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
        return "SQL"

    monkeypatch.setattr(gmod, "router_node", fake_router)
    monkeypatch.setattr(gmod, "sql_rag_node", lambda q: {"answer": "ok", "listings": ["s1"]})

    gmod.run_search("3천만원 이하 SUV")  # context 없음 → contextualize_query가 LLM 없이 그대로 반환
    assert seen_query["q"] == "3천만원 이하 SUV"
