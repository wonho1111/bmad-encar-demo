"""app/rerank_client.py 단위 테스트 — 사이드카(reranker_service.py) 없이 도는 테스트.

사이드카를 실제로 띄운 통합 검증(GPU 로드·실제 /rerank 응답·헬스)은 이 파일이 아니라
작업 보고에 실측으로 남긴다(다른 test_*.py들의 "DB/외부 서비스 불필요 단위 테스트" 관례와
동일 — test_market_price.py 상단 주석 참조).

검증 범위:
  · RERANKER_URL 미설정 → None (네트워크 호출 자체를 안 한다)
  · 연결 실패·타임아웃(3초) → None (예외를 밖으로 던지지 않는다)
  · 정상 응답 → id를 원본 인덱스로 되돌려 점수 내림차순으로 정렬한 인덱스 리스트

⚠️ 이 파일이 안 보는 것: 실제 HTTP 왕복, 사이드카의 422(docs 50건 초과)·503(모델 미로드)
   응답 처리. httpx.post를 몽키패치로 대체하므로 진짜 요청은 나가지 않는다.
"""

import httpx
import pytest

from app import rerank_client


class _FakeResponse:
    """httpx.Response 흉내 — raise_for_status()·json()만 필요하다."""

    def __init__(self, payload: dict, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("에러", request=None, response=self)

    def json(self):
        return self._payload


def test_url_미설정이면_None을_돌려주고_네트워크를_안_탄다(monkeypatch):
    monkeypatch.setattr(rerank_client.settings, "reranker_url", None)

    def _should_not_be_called(*args, **kwargs):
        raise AssertionError("RERANKER_URL이 없으면 httpx.post가 호출되면 안 된다")

    monkeypatch.setattr(rerank_client.httpx, "post", _should_not_be_called)

    result = rerank_client.rerank("쏘렌토", [("a", "쏘렌토 2020"), ("b", "그랜저 2019")])
    assert result is None


def test_연결_실패면_None을_돌려준다(monkeypatch):
    monkeypatch.setattr(rerank_client.settings, "reranker_url", "http://127.0.0.1:8801")

    def _raise_connect_error(*args, **kwargs):
        raise httpx.ConnectError("연결 거부")

    monkeypatch.setattr(rerank_client.httpx, "post", _raise_connect_error)

    result = rerank_client.rerank("쏘렌토", [("a", "쏘렌토 2020"), ("b", "그랜저 2019")])
    assert result is None


def test_타임아웃이면_None을_돌려준다(monkeypatch):
    monkeypatch.setattr(rerank_client.settings, "reranker_url", "http://127.0.0.1:8801")

    def _raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("3초 초과")

    monkeypatch.setattr(rerank_client.httpx, "post", _raise_timeout)

    result = rerank_client.rerank("쏘렌토", [("a", "쏘렌토 2020"), ("b", "그랜저 2019")])
    assert result is None


def test_정상_응답이면_점수_내림차순_인덱스를_돌려준다(monkeypatch):
    monkeypatch.setattr(rerank_client.settings, "reranker_url", "http://127.0.0.1:8801")

    docs = [("a", "쏘렌토 2020"), ("b", "그랜저 2019"), ("c", "아반떼 2021")]

    # 사이드카가 b(0.9) > c(0.5) > a(0.1) 순으로 점수를 매겼다고 가정.
    # 원본 docs 인덱스: a=0, b=1, c=2 → 기대 결과는 [1, 2, 0](점수 내림차순).
    fake_payload = {
        "scores": [
            {"id": "b", "score": 0.9},
            {"id": "c", "score": 0.5},
            {"id": "a", "score": 0.1},
        ]
    }

    def _fake_post(url, json, timeout):
        assert url == "http://127.0.0.1:8801/rerank"
        assert timeout == pytest.approx(3.0)
        return _FakeResponse(fake_payload)

    monkeypatch.setattr(rerank_client.httpx, "post", _fake_post)

    result = rerank_client.rerank("쏘렌토", docs)
    assert result == [1, 2, 0]
