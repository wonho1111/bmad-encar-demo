"""api/tests/integration/ 공유 픽스처 — TEST_DATABASE_URL skip 가드·_create_user·_insert_listing
(Story 12.2, 대장 #188 "6번째 파일 추가 시" 트리거 충족).

왜 지금 만드나: 이 디렉터리의 실DB 통합 테스트 5개(test_fr11_cover_images_real_db.py·
test_seller_summary_real_db.py·test_trust_attributes_real_db.py·test_view_count_rpc_real_db.py·
test_chat_idempotency_real_db.py)가 전부 `TEST_DATABASE_URL` skip 가드·유저 생성·매물 INSERT를
각자 다시 구현해왔다(대장 #188 — 복제가 이미 12.1에서 `role` 하드코딩 결함을 한 번 만들었다).
이 스토리(12.2)가 `test_chat_realtime_broadcast_real_db.py`를 추가해 그 트리거를 충족시키므로,
새 파일이 쓸 공유 버전을 여기 올린다.

**기존 5개 파일은 이 conftest를 쓰도록 옮기지 않는다** — 이번 스토리 범위 밖이다(전체 이관은
별도 판단, 스펙 Always 절). 그래서 각 파일의 사본은 그대로 남아 있고, 이 conftest와 내용이
같아 보여도 우연이 아니라 `_create_user`/`_insert_listing`이 여기로 옮겨온 원본이 그것들
중 `test_chat_idempotency_real_db.py`의 버전(role 인자 + 가입 트리거 결과 단언 포함, 가장
엄격한 버전)이기 때문이다.

사용법: 새 통합 테스트 파일은 `from conftest import _DSN, _create_user, _insert_listing,
pytestmark`로 가져와 쓴다. `pytestmark`를 그대로 재바인딩하면 pytest가 그 이름을 모듈
전역에서 찾아 skip 마커로 인식한다(모듈별로 다시 선언할 필요 없음).

⚠️ **이 헬퍼들은 스스로 정리하지 않는다 — 호출자가 되돌려야 한다.** `auth.users`·`public.listings`에
실제 행을 쓰고 지우지 않으므로, 픽스처가 `with psycopg.connect(...) as conn:` 안에서 쓰고 마지막에
`conn.rollback()`으로 끝내야 한다(이 디렉터리 6개 파일이 전부 그 형태다). 이 계약이 각 파일의 픽스처
docstring에만 있으면 헬퍼만 가져다 쓰는 다음 사람이 놓치고, CI 공용 DB에 고아 행이 쌓인다 —
공유하려고 올린 것 옆에 계약도 같이 둔다(2026-07-28 3차 코드리뷰).
"""

import os
import uuid

import pytest

_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DSN, reason="TEST_DATABASE_URL 미설정 — 실DB 통합 검증은 CI의 api-db 잡에서 돈다"
)

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)


def _create_user(cur, email, role="buyer"):
    user_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, jsonb_build_object('role', %s::text))",
        (user_id, email, role),
    )
    # 0001의 가입 트리거가 profiles 행을 만든다 — listings/chat_rooms FK가 이를 요구한다.
    # role까지 대조하는 이유: 이 인자를 받아만 두고 확인하지 않으면 "판매자를 만들었다"가
    # 검사되지 않는 주장으로 남는다(12.1이 겪은 실제 결함 — 형제 파일의 _create_seller를
    # 옮기다 판매자 유저에도 role="buyer"를 하드코딩했었다, 대장 #188).
    cur.execute("select role from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    assert row[0] == role, f"가입 트리거가 role 메타데이터를 반영하지 않았다({row[0]} != {role})"
    return user_id


def _insert_listing(cur, listing_id, seller_id):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id),
    )
