"""/ai/search HTTP 계약 회귀 테스트 — 그래프(run_search) 모킹으로 네트워크 없이 검증(AC6).

4.5에서 라우터가 sql_rag_node 직접호출 → run_search(그래프)로 바뀌었다. 그 교체 이후에도
기존 계약(200 {answer, listings[]} / 401 미인증 / 422 빈질의 / 400 SqlGuardError)이
그대로 보존되는지(회귀 0) 확인한다. 인증 의존성은 가짜 사용자로 오버라이드한다.
"""

from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.db.sql_guard import SqlGuardError
from app.main import app

client = TestClient(app)


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
        lambda query: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": [card]},
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


def test_search_guard_route_returns_empty_listings(monkeypatch):
    # 경로 C(매물 무관) — 그래프가 빈 목록 + 유도 문구를 주면 200으로 그대로 전달.
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query: {"answer": "저는 중고차 매물 검색을 도와드려요.", "listings": []},
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
    def _raise(query):
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
    r = client.post("/ai/search", json={"query": "3천만원 이하 SUV"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_search_empty_query_returns_422():
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "   "})
        assert r.status_code == 422
        assert r.json()["error"]["code"] == "validation_error"
    finally:
        app.dependency_overrides.clear()
