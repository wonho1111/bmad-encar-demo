"""api는 서명 URL을 절대 발급하지 않는다 — 불변식 가드 (Story 9.2 AC3).

오늘 ListingCard.image_url은 항상 None(8.3이 자리만 선점)이라 이 테스트는 지금도 자명히
통과한다. 하지만 9.6이 api에 storage_path 반환을 붙인 뒤에도 "서명 URL 문자열이 응답에
없다"를 계속 지키는 게 목적이다 — Supabase 서명 URL의 특징적인 경로/쿼리 패턴이 응답 JSON
어디에도 없는지 문자열 단위로 검사한다(필드명이 아니라 값의 모양을 본다 — 향후 어느 필드에
새어나가도 잡는다).

storage_path 존재 단언은 여기서 하지 않는다(9.6에서 활성화 — Dev Notes "api contract test
시퀀싱" 참고): 지금 storage_path를 api가 반환하지 않으므로 그 단언은 통과할 수 없는 거짓
목표가 된다.
"""

from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)

# Supabase 서명 URL의 특징 패턴(docs/conventions.md §10). object/render/upload 등 모든 서명 경로를
# `/sign/` 하나로 포괄하고, 서명 URL이 다른 URL 안에 끼어 퍼센트 인코딩(%2Fsign%2F·token%3D)된
# 경우까지 잡도록 응답을 1회 디코드한 뒤 검사한다.
# 예: https://<project>.supabase.co/storage/v1/object/sign/listing-images/<path>?token=<jwt>
_SIGNED_URL_MARKERS = ["/sign/", "token="]


def _auth():
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}


def _assert_no_signed_url(response_text: str):
    decoded = unquote(response_text)  # %2Fsign%2F·token%3D 로 숨은 서명 URL 우회를 막는다
    for marker in _SIGNED_URL_MARKERS:
        assert marker not in decoded, f"응답에 서명 URL로 보이는 문자열이 있음: {marker!r}"


def test_search_response_never_contains_signed_url_string(monkeypatch):
    # 오늘의 실제 형태: image_url이 None인 카드.
    card = {
        "id": "uuid-1", "manufacturer": "현대", "model": "싼타페",
        "year": 2020, "price": 26700000, "mileage": 62000, "region": "강원",
        "image_url": None,
    }
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": [card]},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "3천만원 이하 흰색 SUV"})
        assert r.status_code == 200
        _assert_no_signed_url(r.text)
    finally:
        app.dependency_overrides.clear()


def test_search_response_with_multiple_listings_never_contains_signed_url_string(monkeypatch):
    # 여러 매물이 섞여 응답해도(배치 상황을 흉내) 전체 응답 문자열에 서명 URL이 없어야 한다.
    cards = [
        {
            "id": f"uuid-{i}", "manufacturer": "기아", "model": "쏘렌토",
            "year": 2021, "price": 30000000, "mileage": 50000, "region": "서울",
            "image_url": None,
        }
        for i in range(3)
    ]
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 3건을 찾았어요.", "listings": cards},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "쏘렌토"})
        assert r.status_code == 200
        _assert_no_signed_url(r.text)
    finally:
        app.dependency_overrides.clear()


# --- 가드 자체가 살아있음을 증명하는 positive fixture --------------------------------
# 위 두 테스트는 오늘 image_url이 항상 None이라 "마커가 없다"만 확인할 뿐, 가드가 실제로
# 발화하는지는 한 번도 시연하지 못한다 → 마커를 지우거나 오타내도 초록으로 남는다. 아래 두 개는
# 가드 함수를 직접 겨눠 "서명 URL이 있으면 반드시 실패한다"를 못박는다. 마커가 고장나면 여기가
# red가 된다(B4: 만들었다가 아니라 '일부러 깨서 잡힌다'가 완료).
_LEAKED_SIGNED_URL = (
    "https://proj.supabase.co/storage/v1/object/sign/"
    "listing-images/u/l/a.png?token=eyJhbGciOiJIUzI1NiJ9.fake"
)


def test_guard_fires_on_plain_signed_url():
    with pytest.raises(AssertionError):
        _assert_no_signed_url(_LEAKED_SIGNED_URL)


def test_guard_fires_on_percent_encoded_signed_url():
    # 서명 URL이 다른 URL의 쿼리로 인코딩돼 끼어든 경우(P2) — 디코드 후 잡혀야 한다.
    from urllib.parse import quote

    encoded = f"https://cb.example.com/r?next={quote(_LEAKED_SIGNED_URL, safe='')}"
    with pytest.raises(AssertionError):
        _assert_no_signed_url(encoded)
