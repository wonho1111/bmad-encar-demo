"""`/ai/search` 인증 게이트 — 무토큰 401, 빈 Bearer 401, 무효 토큰 401, 인증 통과 200.

FR58(8.5)은 열람(매물 목록·상세)만 anon에 열고 이 엔드포인트는 **로그인 필수로 남긴다**:
검색 1회 = Gemini 호출 3회 내외 = 실제 과금이므로 "열람"이 아니라 "행동"이다(conventions.md §8).
"""

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)


def test_search_without_token_returns_401():
    # 토큰 없음 → 네트워크 호출 전에 바로 401(비밀값 없이도 이 경로가 동작해야 한다).
    r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_search_with_empty_bearer_returns_401():
    # "Bearer" 뒤 토큰 없음 = 무토큰 취급 → 401.
    r = client.post(
        "/ai/search",
        json={"query": "x"},
        headers={"Authorization": "Bearer"},
    )
    assert r.status_code == 401


def test_search_with_invalid_token_returns_401(monkeypatch):
    # 토큰은 있으나 Auth 서버가 사용자를 못 준 경우 → 401.
    # env(SUPABASE_URL/ANON_KEY)를 monkeypatch로 채운다: _validate_token이 create_client 전에
    # require()로 fail-loud 하므로, 이걸 안 채우면 .env 없는 CI에서 401이 아니라 500으로 실패한다.
    monkeypatch.setattr("app.auth.settings.supabase_url", "https://test.supabase.co")
    monkeypatch.setattr("app.auth.settings.supabase_anon_key", "test-anon-key")

    class _FakeAuthResp:
        user = None

    class _FakeAuth:
        def get_user(self, token):
            return _FakeAuthResp()

    class _FakeClient:
        auth = _FakeAuth()

    monkeypatch.setattr("supabase.create_client", lambda url, key: _FakeClient())
    r = client.post(
        "/ai/search",
        json={"query": "x"},
        headers={"Authorization": "Bearer invalid-token"},
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_search_authorized_returns_contract_shape(monkeypatch):
    # 인증 의존성을 가짜 사용자로 오버라이드해 200 경로를 검증.
    # 4.5부터 라우터가 그래프(run_search)를 호출하므로, 이 테스트는 "인증 통과 +
    # 응답 계약 형태"만 보도록 그래프를 가짜로 치환한다(라이브 검증은 test_graph/test_ai_search).
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 0건을 찾았어요.", "listings": []},
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

    def _raise(query, context=None):
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    monkeypatch.setattr("app.routers.ai.run_search", _raise)
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
