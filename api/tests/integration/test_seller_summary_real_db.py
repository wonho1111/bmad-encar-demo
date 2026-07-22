"""판매자 공개 요약 RPC 실DB 검증 — `get_seller_public_summary`가 FR11 필터를 실제로 강제하는가
(Story 10.6, 코드리뷰 2026-07-22 패치5).

왜 이 파일이 따로 있나:
  0019가 만든 SECURITY DEFINER 함수는 SQL 안에 `status = 'on_sale'`이라는 **글자**가 있는 것과,
  Postgres가 실제로 sold 매물을 세지 않는 것은 다른 사실이다(CLAUDE.md B4 "존재 확인은 작동
  확인이 아니다"). 이 함수는 SECURITY DEFINER라 **RLS가 적용되지 않는다** — 인라인
  `status = 'on_sale'` 조건이 FR11의 **유일한** 강제 지점이므로, 문자열 검사가 아니라 진짜
  Postgres로 확인한다(`test_fr11_cover_images_real_db.py`·`test_trust_attributes_real_db.py`와
  같은 이유, 같은 방식).

무엇을 증명하나:
  ① 판매자의 다른 on_sale 매물은 카운트된다.
  ② sold 매물은 몇 건을 추가해도 카운트에서 계속 빠진다(FR11 red/green).
  ③ "지금 보고 있는" 매물은 그 자신도 카운트에서 제외된다.
  ④ 가입 시점(profiles.created_at)은 RLS(0001, 본인·admin만)로 막힌 남의 프로필인데도
     SECURITY DEFINER 경유로는 anon조차 읽는다 — RLS 우회가 실제로 일어남을 증명한다.
  ⑤ exclude id가 NULL이어도(방어적 호출) 전체 on_sale을 정상 집계한다(패치2 회귀 고정 —
     수정 전엔 `id <> NULL`이 모든 행에서 NULL(불참)이 되어 집계가 항상 0이었다).

무엇을 **못 보나**: RPC 반환값을 `page.tsx`가 실제로 렌더에 옮기는지는 web의
  `sellerInfo.test.ts`(순수 함수 단위테스트) 몫이다 — 여기는 DB 계층만 본다.

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import os
import uuid

import psycopg
import pytest

_DSN = os.environ.get("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not _DSN, reason="TEST_DATABASE_URL 미설정 — 실DB 통합 검증은 CI의 api-db 잡에서 돈다"
)

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)


def _insert_listing(cur, listing_id, seller_id, status):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, %s, '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id, status),
    )


@pytest.fixture
def seeded():
    """판매자 1명 + on_sale 2건(그중 하나가 "현재" 매물) + sold 1건. 끝나면 **롤백**해 원상복구한다."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = uuid.uuid4()
            current_id, other_on_sale_id, sold_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

            c.execute(
                "insert into auth.users (id, email, raw_user_meta_data) "
                "values (%s, %s, '{\"role\":\"seller\"}'::jsonb)",
                (seller_id, "seller-summary-test@example.com"),
            )
            # 0001의 가입 트리거가 profiles 행을 만든다 — 여기 없으면 함수가 조회할 대상이 없다.
            c.execute("select id from public.profiles where id = %s", (seller_id,))
            assert c.fetchone() is not None, "가입 트리거가 profiles 행을 만들지 않았다"

            _insert_listing(c, current_id, seller_id, "on_sale")
            _insert_listing(c, other_on_sale_id, seller_id, "on_sale")
            _insert_listing(c, sold_id, seller_id, "sold")

            yield c, seller_id, current_id
        conn.rollback()


def _call(cur, seller_id, exclude_id, *, as_anon=True):
    """`get_seller_public_summary`를 호출한다.

    기본으로 **anon 롤로 임퍼소네이션**한다 — profiles는 본인·admin만 읽을 수 있는데(0001 RLS),
    RPC 경유로는 anon조차 남의 가입 시점을 읽어낼 수 있어야 "RLS가 아니라 함수 본문의 인라인
    조건이 FR11을 지킨다"는 이 함수의 설계(SECURITY DEFINER 안엔 RLS가 없음)가 실제로 성립한다.
    """
    if as_anon:
        cur.execute("set local role anon")
    cur.execute(
        "select joined_at, other_on_sale_count from public.get_seller_public_summary(%s, %s)",
        (seller_id, exclude_id),
    )
    row = cur.fetchone()
    if as_anon:
        cur.execute("reset role")
    return row


def test_other_on_sale_counted_current_excluded(seeded):
    """① 다른 on_sale은 세고 ③ 현재 매물 자신은 제외한다 — 정확히 1건이 남아야 한다."""
    cur, seller_id, current_id = seeded
    joined_at, count = _call(cur, seller_id, current_id)
    assert count == 1, "현재 매물 제외 후 다른 on_sale 1건만 남아야 한다"
    assert joined_at is not None


def test_anon_can_read_joined_at_despite_profiles_rls(seeded):
    """④ profiles RLS(본인·admin만)를 anon이 직접 못 읽어도, SECURITY DEFINER 경유로는 읽힌다."""
    cur, seller_id, current_id = seeded

    # 대조군: anon이 profiles를 직접 조회하면 막힌다(0001 RLS/기본 GRANT 부재로 거부) —
    # RPC가 아니라 여기가 원래 강제 지점이었다면 이 SELECT도 통과해야 하는데 실제로는 막힌다.
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with cur.connection.transaction():
            cur.execute("set local role anon")
            cur.execute("select created_at from public.profiles where id = %s", (seller_id,))
    cur.execute("reset role")

    # RPC 경유는 anon도 읽는다 — 상세는 비로그인도 열람 가능해야 하므로(FR58).
    joined_at, _count = _call(cur, seller_id, current_id)
    assert joined_at is not None


@pytest.mark.parametrize("extra_sold", [1, 3])
def test_additional_sold_listings_never_inflate_count(seeded, extra_sold):
    """② FR11 red/green: sold를 아무리 늘려도 집계는 절대 늘지 않는다."""
    cur, seller_id, current_id = seeded
    for _ in range(extra_sold):
        _insert_listing(cur, uuid.uuid4(), seller_id, "sold")

    _joined_at, count = _call(cur, seller_id, current_id)
    assert count == 1, "sold 매물을 몇 건 늘려도 집계는 그대로여야 한다(FR11)"


def test_null_exclude_id_still_counts_all_on_sale(seeded):
    """⑤ 패치2 회귀 고정: exclude id가 NULL이면 `id <> NULL`로 전 행이 탈락하지 않고,
    방어적으로 판매자의 on_sale 전체를 센다.

    수정 전엔 `id <> p_exclude_listing_id`가 NULL과 비교돼 매 행에서 NULL(SQL 3값 논리상
    조건 불충족 취급)이 되어, 이 함수를 GRANT받은 anon이 실수로(또는 악의로) NULL을 넘기면
    집계가 **항상 0**이었다 — 이 테스트가 red가 되면 그 회귀가 되돌아온 것이다.
    """
    cur, seller_id, _current_id = seeded
    _joined_at, count = _call(cur, seller_id, None)
    assert count == 2, "exclude id가 NULL이면 판매자의 on_sale 전체(2건)를 세야 한다"
