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


def _call(cur, seller_id, exclude_id, *, as_anon=True, caller_id=None):
    """`get_seller_public_summary`를 호출한다.

    기본으로 **anon 롤로 임퍼소네이션**한다 — profiles는 본인·admin만 읽을 수 있는데(0001 RLS),
    RPC 경유로는 anon조차 남의 가입 시점을 읽어낼 수 있어야 "RLS가 아니라 함수 본문의 인라인
    조건이 FR11을 지킨다"는 이 함수의 설계(SECURITY DEFINER 안엔 RLS가 없음)가 실제로 성립한다.

    `caller_id`(Story 17.4 코드리뷰 patch)를 주면 그 사용자로 로그인한 것처럼(`authenticated`
    롤 + `request.jwt.claim.sub`) 호출한다 — 판매자 **본인**·**관리자**가 정지된 판매자의 요약을
    볼 때를 검증하려면 `auth.uid()`가 실제 값이어야 하는데 anon으로는 항상 NULL이라 그 분기를
    태울 수 없다. `caller_id`가 있으면 `as_anon`은 무시된다(상호 배타).
    """
    if caller_id is not None:
        cur.execute(f"set local request.jwt.claim.sub = '{caller_id}'")
        cur.execute("set local role authenticated")
    elif as_anon:
        cur.execute("set local role anon")
    cur.execute(
        "select joined_at, other_on_sale_count from public.get_seller_public_summary(%s, %s)",
        (seller_id, exclude_id),
    )
    row = cur.fetchone()
    if caller_id is not None:
        cur.execute("reset role")
        cur.execute("reset request.jwt.claim.sub")
    elif as_anon:
        cur.execute("reset role")
    return row


def test_other_on_sale_counted_current_excluded(seeded):
    """① 다른 on_sale은 세고 ③ 현재 매물 자신은 제외한다 — 정확히 1건이 남아야 한다."""
    cur, seller_id, current_id = seeded
    joined_at, count = _call(cur, seller_id, current_id)
    assert count == 1, "현재 매물 제외 후 다른 on_sale 1건만 남아야 한다"
    assert joined_at is not None


def test_anon_can_read_joined_at_despite_profiles_rls(seeded):
    """④ profiles RLS(본인·admin만)를 anon이 직접 못 읽어도, SECURITY DEFINER 경유로는 읽힌다.

    ── 2026-07-28 갱신(대장 #138) ──────────────────────────────────────────
    이 테스트는 원래 "anon이 profiles를 직접 읽으면 InsufficientPrivilege가 난다"고
    단언했다 — 즉 막는 층이 GRANT(권한)라는 가정이었다. 그 가정이 틀렸다는 게 운영 DB
    직접 실측(Supabase MCP)으로 드러났다:
        has_table_privilege('anon','public.profiles','SELECT')  = true   ← 권한은 있다
        has_table_privilege('anon','public.listings','SELECT')  = false  ← listings는 0011이
                                                                              회수해서 없다(대조군)
        profiles: rls_enabled = true, 정책 4개
        set local role anon; select count(*) from public.profiles  →  0  ← 0행. RLS가 거른다
    즉 막히는 건 맞는데 막는 층이 다르다 — 권한이 아니라 RLS(행 수준 정책)다. 보안 노출은
    없다. `scripts/migration-check-prelude.sql`의
    `alter default privileges ... grant all on tables to anon, authenticated`는 운영을 정확히
    재현하고 있었다(위 실측이 증명) — 프렐류드가 아니라 이 테스트의 가정이 틀렸었다. 그래서
    단언을 실제 방어층(RLS가 0행으로 거른다)에 맞게 고쳤다. RPC가 여전히 가입월을 돌려준다는
    이 테스트의 핵심 목적은 그대로 유지한다.
    """
    cur, seller_id, current_id = seeded

    # profiles: anon은 테이블 SELECT 권한 자체는 있다(플랫폼 기본 GRANT, alter default
    # privileges) — 그런데 RLS(0001, 본인·admin만)가 조용히 0행으로 거른다. 에러가 아니라
    # "빈 결과"로 막힌다는 게 위 실측의 핵심이고, 이 단언이 그것을 고정한다.
    cur.execute("set local role anon")
    cur.execute("select created_at from public.profiles where id = %s", (seller_id,))
    row = cur.fetchone()
    cur.execute("reset role")
    assert row is None, "anon의 profiles 직접 SELECT는 RLS가 0행으로 걸러야 한다(권한 오류가 아니다)"

    # 대조군: listings.embedding(RAG 코퍼스, 0011이 anon 컬럼 화이트리스트 밖으로 뺀 컬럼)은
    # 반대로 GRANT 층에서 막힌다 — 같은 anon 롤인데 테이블마다 막는 층이 다르다는 것을
    # 나란히 보여준다("권한으로 막힘"과 "정책으로 막힘"이 이 레포에 둘 다 존재한다).
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with cur.connection.transaction():
            cur.execute("set local role anon")
            cur.execute("select embedding from public.listings where id = %s", (current_id,))
    cur.execute("reset role")

    # RPC 경유는 anon도 읽는다 — 상세는 비로그인도 열람 가능해야 하므로(FR58). 이게 이 테스트의
    # 원래이자 핵심 목적: SECURITY DEFINER RPC가 RLS를 우회해 가입월을 돌려준다는 것.
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


def test_suspended_seller_listings_excluded_from_count_for_third_party(seeded):
    """Story 17.4(DW-804(a)) — **제3자(anon)** 가 볼 때, 정지된 판매자는 on_sale 매물이 있어도
    집계가 0이 된다.

    함수 본문에 `public.is_seller_active(p_seller_id)`(0035)를 추가했다 — SECURITY DEFINER라
    RLS가 대신 걸러주지 않으므로 이 인라인 조건이 유일한 강제 지점이다(0019·0035 주석과 동일
    이유). 긍정 대조군은 이 파일의 다른 테스트(`test_other_on_sale_counted_current_excluded`
    등)가 이미 활성 판매자 집계를 고정하고 있어 별도로 두지 않는다. **판매자 본인·관리자가 볼
    때는 다르다** — 아래 두 테스트(`test_suspended_seller_can_view_own_summary_with_correct_count`
    ·`test_admin_can_view_suspended_sellers_summary_with_correct_count`)가 그 축을 짝으로 고정한다
    (코드리뷰 patch — `is_seller_active` 단독 조건이던 1차 작성은 본인·관리자가 봐도 무조건 0을
    돌려주는 결함이 있었다, 불변식 "본인·관리자 조회는 그대로" 위반)."""
    cur, seller_id, current_id = seeded
    cur.execute("update public.profiles set status = 'suspended' where id = %s", (seller_id,))

    joined_at, count = _call(cur, seller_id, current_id)
    assert count == 0, "정지된 판매자의 다른 on_sale 매물이 집계에 포함됐다"
    assert joined_at is not None, (
        "정지된 판매자여도 가입 시점(joined_at)은 계속 반환돼야 한다 — 이 스토리가 좁힌 것은 "
        "매물 집계뿐이다(마이그레이션 주석 참조)"
    )


def test_suspended_seller_can_view_own_summary_with_correct_count(seeded):
    """정지된 판매자 **본인**이 자기 요약을 볼 때는 정지와 무관하게 실제 집계가 나온다
    (코드리뷰 patch — 불변식 "본인 조회는 그대로"). `auth.uid() = p_seller_id` 조건이 이 축의
    강제 지점이다(0035 5절)."""
    cur, seller_id, current_id = seeded
    cur.execute("update public.profiles set status = 'suspended' where id = %s", (seller_id,))

    joined_at, count = _call(cur, seller_id, current_id, caller_id=seller_id)
    assert count == 1, "정지된 판매자 본인이 자기 요약을 볼 때는 실제 on_sale 집계(1건)가 나와야 한다"
    assert joined_at is not None


def test_admin_can_view_suspended_sellers_summary_with_correct_count(seeded):
    """관리자가 정지된 판매자의 요약을 볼 때도 정지와 무관하게 실제 집계가 나온다(코드리뷰 patch —
    불변식 "관리자 조회는 그대로"). `public.is_admin()` 조건이 이 축의 강제 지점이다(0035 5절)."""
    cur, seller_id, current_id = seeded
    cur.execute("update public.profiles set status = 'suspended' where id = %s", (seller_id,))

    admin_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, '{\"role\": \"buyer\"}'::jsonb)",
        (admin_id, f"seller-summary-admin-{uuid.uuid4()}@example.com"),
    )
    cur.execute("update public.profiles set role = 'admin' where id = %s", (admin_id,))

    joined_at, count = _call(cur, seller_id, current_id, caller_id=admin_id)
    assert count == 1, "관리자가 정지된 판매자의 요약을 볼 때는 실제 on_sale 집계(1건)가 나와야 한다"
    assert joined_at is not None


def test_ordinary_buyer_caller_id_gets_zero_for_suspended_seller(seeded):
    """제3자(로그인한 일반 구매자)가 `caller_id=`로 볼 때도 0이어야 한다(코드리뷰 patch, P6).

    기존 `caller_id=` 케이스 둘은 전부 양성(판매자 본인 → 1, 관리자 → 1)뿐이었다 — anon 음성
    케이스는 `as_anon` 경로로 이미 있지만, **로그인한 일반 구매자**가 `auth.uid()`를 갖고 볼 때의
    음성 케이스가 없었다. 그래서 함수 조건을 `auth.uid() = p_seller_id`에서 `auth.uid() is not
    null`(로그인만 하면 통과)로 잘못 넓혀도 기존 테스트가 전부 green으로 남는 사각이 있었다 —
    이 테스트가 그 사각을 막는다."""
    cur, seller_id, current_id = seeded
    cur.execute("update public.profiles set status = 'suspended' where id = %s", (seller_id,))

    buyer_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, '{\"role\": \"buyer\"}'::jsonb)",
        (buyer_id, f"seller-summary-buyer-{uuid.uuid4()}@example.com"),
    )

    joined_at, count = _call(cur, seller_id, current_id, caller_id=buyer_id)
    assert count == 0, "일반 구매자가 정지된 판매자를 볼 때는 집계가 0이어야 한다(본인·관리자가 아니다)"
    assert joined_at is not None


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
