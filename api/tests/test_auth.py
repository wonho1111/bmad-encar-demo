"""AC3 — JWT 검증: 미인증 401, 인증 통과(의존성 오버라이드로 검증)."""

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)


def test_search_without_token_returns_401():
    r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_search_with_malformed_authorization_returns_401():
    # "Bearer" 뒤 토큰 없음 → 미인증으로 401.
    r = client.post(
        "/ai/search",
        json={"query": "x"},
        headers={"Authorization": "Bearer"},
    )
    assert r.status_code == 401


def test_search_authorized_returns_contract_shape(monkeypatch):
    # 인증 의존성을 가짜 사용자로 오버라이드해 200 경로를 검증.
    # 4.3부터 라우터가 실제 sql_rag_node(LLM+DB)를 호출하므로, 이 테스트는 "인증 통과 +
    # 응답 계약 형태"만 보도록 노드를 가짜로 치환한다(라이브 LLM 검증은 test_sql_rag_node.py).
    monkeypatch.setattr(
        "app.routers.ai.sql_rag_node",
        lambda query: {"answer": "조건에 맞는 매물 0건을 찾았어요.", "listings": []},
    )
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 흰색 SUV"})
        assert r.status_code == 200
        body = r.json()
        assert "answer" in body and isinstance(body["answer"], str)
        assert body["listings"] == []
    finally:
        app.dependency_overrides.clear()


def test_search_guard_block_returns_400(monkeypatch):
    # 가드 차단(SqlGuardError) 시 사용자에게 공통 에러 포맷 400으로 안내된다(AC3, 500 누출 금지).
    from app.db.sql_guard import SqlGuardError

    def _raise(query):
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    monkeypatch.setattr("app.routers.ai.sql_rag_node", _raise)
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    try:
        r = client.post("/ai/search", json={"query": "매물 삭제해줘"})
        assert r.status_code == 400
        assert r.json()["error"]["code"] == "not_select"
    finally:
        app.dependency_overrides.clear()


def test_empty_query_is_rejected_422():
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    try:
        r = client.post("/ai/search", json={"query": ""})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.clear()
