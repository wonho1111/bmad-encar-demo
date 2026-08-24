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
    """auth.users에 유저를 만들고, 가입 트리거(handle_new_user)가 새 계약(Story 17.1, 0033)대로
    profiles.role을 채웠는지 확인한다.

    ⚠️ **0033(DW-682)부터 계약이 바뀌었다**: 트리거는 metadata의 role을 더 이상 읽지 않고
    **항상 'user'로 배정한다**(이전 0028 계약은 'buyer'/'seller' 메타데이터를 그대로 반영했다 —
    그 통과 분기가 도달 경로 0이라 0033이 지웠다). role=None/`'buyer'`/`'seller'` 어느 것을
    넘겨도 가입 직후 실제 profiles.role은 'user'다 — 이 함수가 그 사실을 먼저 단언한다.

    그런데 이 헬퍼를 쓰는 여러 테스트 파일은 "판매자"·"구매자" 같은 **의미상 구분**이 필요해
    role="seller"/"buyer"를 넘긴다(0033 이전부터 그래 왔다 — 호출부를 전부 고치면 이 스토리
    범위를 크게 넘는다). 그 필요를 깨지 않기 위해, role이 'buyer'/'seller'면 가입 트리거의
    'user' 배정을 확인한 **뒤** profiles를 UPDATE로 그 값으로 올린다(admin을 만들 때 이미 쓰던
    패턴과 동일 — 트리거로는 못 만드는 값을 트리거 이후에 직접 앉힌다). 그래서 이 헬퍼가 돌려주는
    user_id의 최종 profiles.role은 여전히 호출자가 넘긴 role과 같다 — 달라진 것은 "그 값이
    트리거의 산출물이 아니라 뒤이은 UPDATE의 산출물"이라는 경로뿐이다.

    role='admin' 같은 그 밖의 값은 **거부한다**(기존 계약 그대로) — 관리자·임의 role이 필요하면
    이 헬퍼로 만든 뒤 profiles를 직접 UPDATE로 올린다.
    """
    if role not in (None, "buyer", "seller"):
        raise ValueError(
            f"가입 트리거가 배정할 수 없는 role={role!r} — 트리거는 이 값을 'user'로 강제한다. "
            "필요하면 생성 후 `update public.profiles set role = …`로 올릴 것."
        )
    user_id = uuid.uuid4()
    if role is None:
        cur.execute(
            "insert into auth.users (id, email, raw_user_meta_data) values (%s, %s, '{}'::jsonb)",
            (user_id, email),
        )
    else:
        cur.execute(
            "insert into auth.users (id, email, raw_user_meta_data) "
            "values (%s, %s, jsonb_build_object('role', %s::text))",
            (user_id, email, role),
        )
    cur.execute("select role from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    assert row[0] == "user", (
        f"가입 트리거가 'user' 고정 계약(0033, DW-682)을 지키지 않았다: {row[0]!r}"
    )
    if role in ("buyer", "seller"):
        # 트리거는 더 이상 이 값을 반영하지 않는다 — 호출자가 의미상 구분을 원하면 직접 앉힌다.
        # rowcount를 단언하는 이유: 이 UPDATE가 조용히 0행이면(예: id 불일치) 호출자는 "판매자를
        # 만들었다"고 믿지만 실제로는 role이 여전히 'user'다 — DW-683이 기록한 것과 같은 실패
        # 유형("픽스처가 만들었다고 믿는 것과 실제가 다르다")을 이 지점에서도 반복하지 않는다.
        cur.execute("update public.profiles set role = %s where id = %s", (role, user_id))
        assert cur.rowcount == 1, (
            f"role={role!r} UPDATE가 정확히 한 행을 못 바꿨다(rowcount={cur.rowcount})"
        )
    return user_id


def _insert_listing(cur, listing_id, seller_id):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id),
    )
