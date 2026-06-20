"""AC1 — 앱 기동 + OpenAPI 문서 노출."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_openapi_exposed():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    assert "/ai/search" in r.json()["paths"]


def test_swagger_docs_exposed():
    assert client.get("/docs").status_code == 200
