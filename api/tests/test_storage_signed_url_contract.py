"""api는 사진 **URL을 만들지 않는다** — 불변식 가드 (Story 9.2 AC3 · 9.0으로 범위 확장).

✎ 2026-07-19 코드리뷰: 이 파일은 원래 *서명* URL만 겨눴는데(`/sign/`·`token=`),
`docs/conventions.md` §10은 그보다 넓은 "api는 사진 URL을 만들지 않는다 — storage_path만
반환한다"를 **이 테스트가 지킨다**고 선언하고 있었다. 9.0이 서명 URL을 없애고 공개 URL
(`/storage/v1/object/public/...`)로 갈아탄 뒤로는 두 마커가 **하나도 매치하지 않으므로**,
api가 공개 URL을 응답에 실어도 이 테스트는 초록이었다 — 문서가 가리키는 가드가 비어 있었다.
마커를 `/storage/v1/`로 넓혀 sign·public·render·upload 경로를 전부 덮는다.


오늘 ListingCard.image_url은 항상 None(8.3이 자리만 선점)이라 이 테스트는 지금도 자명히
통과한다. 하지만 9.6이 api에 storage_path 반환을 붙인 뒤에도 "Storage URL 문자열이 응답에
없다"를 계속 지키는 게 목적이다 — Supabase Storage URL의 특징적인 경로/쿼리 패턴이 응답 JSON
어디에도 없는지 문자열 단위로 검사한다(필드명이 아니라 값의 모양을 본다 — 향후 어느 필드에
새어나가도 잡는다).

✅ **2026-07-20 Story 9.6 — storage_path 존재 단언 활성화.** 9.2가 *"9.6에서 활성화"*라고
비워 둔 자리다. 이제 api가 `image_path`(= `listing_images.storage_path` 원본)를 실제로
반환하므로, 아래 `test_response_carries_raw_storage_path_not_url`이 **쌍**을 못박는다 —
"URL은 없다"만으로는 api가 사진을 **아예 안 보내도** 초록이라서, 그 절반은 계약을 지키는 것이
아니라 **기능이 없는 것**과 구별되지 않았다.
"""

from urllib.parse import unquote

import pytest
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.main import app

client = TestClient(app)

# Supabase Storage URL의 특징 패턴(docs/conventions.md §10).
#   `/storage/v1/` — sign·public·render·upload 등 **모든** Storage 경로의 공통 접두. api는 이 중
#                    어느 것도 만들지 않는다(storage_path만 반환하고, URL 조립은 web·app의 몫).
#   `token=`       — 서명 URL의 쿼리. 경로가 바뀌어도 서명 토큰이 새는 것을 따로 잡는다.
# URL이 다른 URL 안에 끼어 퍼센트 인코딩(%2Fstorage%2F·token%3D)된 경우까지 잡도록 응답을
# 1회 디코드한 뒤 검사한다.
# 예: https://<project>.supabase.co/storage/v1/object/public/listing-images/<path>
#     https://<project>.supabase.co/storage/v1/object/sign/listing-images/<path>?token=<jwt>
_STORAGE_URL_MARKERS = ["/storage/v1/", "token="]


def _auth():
    app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}


def _assert_no_storage_url(response_text: str):
    decoded = unquote(response_text)  # %2Fstorage%2F·token%3D 로 숨은 URL 우회를 막는다
    for marker in _STORAGE_URL_MARKERS:
        assert marker not in decoded, f"응답에 Storage URL로 보이는 문자열이 있음: {marker!r}"


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
        _assert_no_storage_url(r.text)
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
        _assert_no_storage_url(r.text)
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
        _assert_no_storage_url(_LEAKED_SIGNED_URL)


def test_guard_fires_on_percent_encoded_signed_url():
    # 서명 URL이 다른 URL의 쿼리로 인코딩돼 끼어든 경우(P2) — 디코드 후 잡혀야 한다.
    from urllib.parse import quote

    encoded = f"https://cb.example.com/r?next={quote(_LEAKED_SIGNED_URL, safe='')}"
    with pytest.raises(AssertionError):
        _assert_no_storage_url(encoded)


# 공개 URL — 이 가드가 **원래 못 잡던** 형태다(2026-07-19 코드리뷰에서 발견).
# `/sign/`도 `token=`도 없어서 마커 2종을 전부 빠져나갔고, 그래서 §10이 이 파일을 근거로
# 선언한 "api는 URL을 만들지 않는다"가 실제로는 아무것도 지키지 않고 있었다.
# 이 테스트가 red→green으로 바뀐 것이 마커 확장이 실효가 있다는 증거다.
_LEAKED_PUBLIC_URL = (
    "https://proj.supabase.co/storage/v1/object/public/listing-images/u/l/a.webp"
)


def test_guard_fires_on_public_url():
    with pytest.raises(AssertionError):
        _assert_no_storage_url(_LEAKED_PUBLIC_URL)


def test_guard_fires_on_percent_encoded_public_url():
    from urllib.parse import quote

    encoded = f"https://cb.example.com/r?next={quote(_LEAKED_PUBLIC_URL, safe='')}"
    with pytest.raises(AssertionError):
        _assert_no_storage_url(encoded)


# --- 계약의 나머지 절반: api는 **원본 경로를 실제로 보낸다** (Story 9.6에서 활성화) ---------
# 위 테스트들은 "URL이 없다"만 본다. 그것만으로는 api가 사진 정보를 **아예 안 실어도** 초록이라,
# §10의 "storage_path만 반환한다"는 계약 중 절반("만 반환")만 지키고 나머지 절반("storage_path를
# 반환")은 아무도 안 지켰다. 9.6이 값을 채웠으므로 여기서 쌍을 닫는다.
_STORAGE_PATH = "0a1b2c3d-user/9f8e7d6c-listing/cover.webp"


def test_response_carries_raw_storage_path_not_url(monkeypatch):
    card = {
        "id": "uuid-1", "manufacturer": "현대", "model": "싼타페",
        "year": 2020, "price": 26700000, "mileage": 62000, "region": "강원",
        "image_url": None, "image_path": _STORAGE_PATH, "image_count": 3,
    }
    monkeypatch.setattr(
        "app.routers.ai.run_search",
        lambda query, context=None: {"answer": "조건에 맞는 매물 1건을 찾았어요.", "listings": [card]},
    )
    _auth()
    try:
        r = client.post("/ai/search", json={"query": "사진 있는 SUV"})
        assert r.status_code == 200
        body = r.json()["listings"][0]
        # ① 원본 경로가 그대로 실려 나간다(= web·app이 URL을 조립할 재료가 있다).
        assert body["image_path"] == _STORAGE_PATH
        assert body["image_count"] == 3
        # ② 그런데 URL은 여전히 api가 만들지 않는다 — image_url은 비어 있고 응답 어디에도
        #    Storage URL 문자열이 없다. 이 둘이 **동시에** 참이어야 §10 계약이다.
        assert body["image_url"] is None
        _assert_no_storage_url(r.text)
    finally:
        app.dependency_overrides.clear()
