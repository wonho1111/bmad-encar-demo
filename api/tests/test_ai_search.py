"""/ai/search HTTP 계약 회귀 테스트 — 그래프(run_search) 모킹으로 네트워크 없이 검증(AC6).

4.5에서 라우터가 sql_rag_node 직접호출 → run_search(그래프)로 바뀌었다. 그 교체 이후에도
기존 계약(200 {answer, listings[]} / 422 빈질의 / 400 SqlGuardError)이 그대로 보존되는지
(회귀 0) 확인한다. 인증 의존성은 가짜 사용자로 오버라이드한다.

4단계 부품 B: routers/ai.py가 `settings.ai_agent_mode`(기본 True)로 run_search_agent와
run_search를 스위치하게 됐다 — 이 파일은 원래대로 레거시 그래프(run_search) 계약만 검증하는
파일이므로, 아래 autouse 픽스처로 이 파일 안에서만 ai_agent_mode=False를 강제해 기존
monkeypatch("app.routers.ai.run_search", ...)들이 계속 실제로 호출되게 한다(회귀 0). 에이전트
경로의 계약은 test_agent_loop.py가 별도로 검증한다.
"""

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.config import settings
from app.db.sql_guard import SqlGuardError
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _force_legacy_graph_pipeline(monkeypatch):
    monkeypatch.setattr(settings, "ai_agent_mode", False)


def _auth():
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}


def test_search_returns_contract_with_listings(monkeypatch):
    # 그래프가 매물을 돌려주면 {answer, listings[]} 계약이 그대로 응답된다.
    card = {
        "id": "uuid-1", "manufacturer": "현대", "model": "싼타페",
        "year": 2020, "price": 26700000, "mileage": 62000, "region": "강원",
    }
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": [card]},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 흰색 SUV"})
        assert r.status_code == 200
        body = r.json()
        assert body["answer"].startswith("조건에 맞는 매물")
        assert len(body["listings"]) == 1
        assert body["listings"][0]["manufacturer"] == "현대"
    finally:
        app.dependency_overrides.clear()


def test_search_returns_clarify_payload_when_present(monkeypatch):
    # 13.4: run_search가 clarify를 채워 돌려주면 HTTP 응답 JSON에도 그대로 실린다(직렬화 경계 확인).
    # 코드리뷰가 발견한 공백 — 라우터의 `clarify=result.get("clarify")`를 지워도 전체 스위트가
    # 초록으로 남았던 자리라, 이 테스트가 그 회귀를 실제로 잡는지가 핵심(존재만이 아니라 작동 확인).
    clarify_payload = {"question": "조건을 조금만 좁혀볼게요.", "chips": ["3천만원 이하", "SUV", "전기차"]}
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {
            "answer": "조건을 조금만 좁혀볼게요.",
            "listings": [],
            "clarify": clarify_payload,
        },
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "패밀리카로 무난한 거"})
        assert r.status_code == 200
        assert r.json()["clarify"] == clarify_payload
    finally:
        app.dependency_overrides.clear()


def test_search_clarify_absent_serializes_to_null(monkeypatch):
    # run_search가 clarify 키를 아예 안 주면(기존 SQL/HYBRID/REJECT 경로) 응답의 clarify는 null.
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": []},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
        assert r.status_code == 200
        assert r.json()["clarify"] is None
    finally:
        app.dependency_overrides.clear()


def test_search_returns_narrowed_by_when_present(monkeypatch):
    # 13.5: run_search가 REJECT의 narrowed_by 고정 상수를 채워 돌려주면 HTTP 응답에도 그대로 실린다.
    narrowed_by = ["price<=30000000", "body_type=SUV", "fuel=전기"]
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {
            "answer": "저는 중고차 찾기를 도와드리는 차장님이에요.",
            "listings": [],
            "narrowed_by": narrowed_by,
        },
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "오늘 날씨 어때?"})
        assert r.status_code == 200
        assert r.json()["narrowed_by"] == narrowed_by
    finally:
        app.dependency_overrides.clear()


def test_search_narrowed_by_absent_serializes_to_null(monkeypatch):
    # run_search가 narrowed_by 키를 아예 안 주면(기존 SQL/HYBRID/CLARIFY 경로) 응답의 narrowed_by는 null.
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": []},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
        assert r.status_code == 200
        assert r.json()["narrowed_by"] is None
    finally:
        app.dependency_overrides.clear()


def test_search_response_validation_error_returns_500_with_cors(monkeypatch):
    # DW-593 해결 실측 증거: run_search가 SearchResponse 스키마를 위반하는 값(narrowed_by에
    # 비문자열)을 반환하면, 응답 조립이 try 안에서 실패해 except Exception(CORS 안쪽) 500이 된다.
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {
            "answer": "저는 중고차 찾기를 도와드리는 차장님이에요.",
            "listings": [],
            "narrowed_by": [123],  # 스키마 위반 — list[str] 아님
        },
    )
    _auth()
    try:
        r = client.post(
            "/ai/search",
            json={"query": "오늘 날씨 어때?"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert r.status_code == 500
        assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
        assert r.json()["error"]["code"] == "internal_error"
    finally:
        app.dependency_overrides.clear()


def test_search_guard_route_returns_empty_listings(monkeypatch):
    # 경로 C(매물 무관) — 그래프가 빈 목록 + 유도 문구를 주면 200으로 그대로 전달.
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "저는 중고차 매물 검색을 도와드려요.", "listings": []},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "오늘 날씨 어때?"})
        assert r.status_code == 200
        assert r.json()["listings"] == []
        assert "중고차" in r.json()["answer"]
    finally:
        app.dependency_overrides.clear()


def test_search_sql_guard_error_returns_400(monkeypatch):
    # 경로 A 가드 차단 — 그래프 안에서 던진 SqlGuardError가 /ai/search까지 전파돼 400(회귀 보호).
    def _raise(query, context=None):
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    monkeypatch.setattr("app.routers.ai.run_search", _raise)
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "매물 삭제해줘"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "not_select"
    finally:
        app.dependency_overrides.clear()


def test_search_without_token_returns_401():
    # 인증 없이 호출하면 라우트 본문에 닿기 전 401(AI 검색은 로그인 필수 — conventions.md §8).
    r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
    assert r.status_code == 401


def test_search_empty_query_returns_422():
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "   "})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.clear()


# ───────── 4.6 멀티턴 맥락(FR18) 회귀 ─────────

def test_search_oversized_context_returns_422():
    # context가 12턴을 넘으면(max_length) 422로 거절 — DoS 여지 차단(AC1).
    _auth()
    try:
        big = [{"role": "user", "content": f"질문{i}"} for i in range(13)]
        r = client.post("/ai/search", json={"query": "그거", "context": big})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.clear()


def test_search_context_with_bad_turn_returns_422():
    # context 원소가 role/content 스키마를 벗어나면 422(원소 타입 강제, AC1).
    _auth()
    try:
        r = client.post(
            "/ai/search",
            json={"query": "그거", "context": [{"role": "system", "content": "x"}]},
        )
        assert r.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_search_passes_context_to_run_search(monkeypatch):
    # context가 run_search(query, context)로 그대로 전달되는지 인자 캡처로 확인(AC2 배선).
    captured = {}

    def _capture(query, context=None):
        captured["query"] = query
        captured["context"] = context
        return {"answer": "맥락 반영 결과", "listings": []}

    monkeypatch.setattr("app.routers.ai.run_search", _capture)
    _auth()
    try:
        ctx = [
            {"role": "user", "content": "패밀리카로 무난한 거"},
            {"role": "assistant", "content": "싼타페 추천"},
        ]
        r = client.post("/ai/search", json={"query": "그 중 더 싼 거", "context": ctx})
        assert r.status_code == 200
        assert captured["query"] == "그 중 더 싼 거"
        assert captured["context"] is not None and len(captured["context"]) == 2
    finally:
        app.dependency_overrides.clear()


def test_search_is_stateless_across_requests(monkeypatch):
    # 무상태(AC3): 서버는 직전 요청을 기억하지 않는다. run_search는 받은 context만 본다.
    # context 있는 요청 → 없는 요청을 연속 호출해도, 둘째가 첫째 맥락을 물려받지 않음을 확인.
    seen = []

    def _spy(query, context=None):
        seen.append(context)
        return {"answer": "ok", "listings": []}

    monkeypatch.setattr("app.routers.ai.run_search", _spy)
    _auth()
    try:
        client.post(
            "/ai/search",
            json={"query": "패밀리카", "context": [{"role": "user", "content": "패밀리카로 무난한 거"}]},
        )
        client.post("/ai/search", json={"query": "안녕"})  # context 없음
        assert seen[0] is not None and len(seen[0]) == 1
        assert seen[1] is None  # 둘째 요청은 맥락이 전혀 없다(서버가 첫째를 기억 안 함)
    finally:
        app.dependency_overrides.clear()


def test_pool_timeout_returns_503(monkeypatch):
    # 8.4 코드리뷰 패치 회귀: DB 커넥션 풀 대여가 타임아웃되면 catch-all 500이 아니라 503으로
    # 안내해야 한다. 이 테스트가 없으면, 그래프 노드가 PoolTimeout을 내부에서 감싸버려
    # 라우터의 except PoolTimeout에 애초에 닿지 못하게 되어도 아무도 눈치채지 못한다.
    from psycopg_pool import PoolTimeout

    def _raise(query, context=None):
        raise PoolTimeout("pool exhausted")

    monkeypatch.setattr("app.routers.ai.run_search", _raise)
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
        assert r.status_code == 503
        assert r.json()["error"]["code"] == "pool_exhausted"
    finally:
        app.dependency_overrides.clear()
