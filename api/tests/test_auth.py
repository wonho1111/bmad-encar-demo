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


def test_search_authorized_returns_contract_shape():
    # 실제 토큰 확보가 어려우므로 인증 의존성을 가짜 사용자로 오버라이드해 200 경로를 검증.
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    try:
        r = client.post("/ai/search", json={"query": "패밀리카 추천"})
        assert r.status_code == 200
        body = r.json()
        assert "answer" in body and isinstance(body["answer"], str)
        assert body["listings"] == []
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
