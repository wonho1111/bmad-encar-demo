"""정지된 판매자의 매물 비노출 실DB 검증 — 5주체(anon·로그인 구매자·판매자 본인·관리자·
ai_readonly) × (정지 판매자 매물 / 활성 판매자 매물) 격자 (Story 17.4, DW-804(a)).

왜 이 파일이 따로 있나:
  17.1의 불변식 후반부("정지된 계정의 읽기는 아무것도 줄어들지 않는다")를 이 스토리가
  사용자 지시(DW-804(a))로 뒤집는다 — `listings_select_on_sale`/`_anon`/`listings_ai_readonly_select`
  (0035)가 이제 판매자가 활성일 때만 매물을 보여준다. "정지 판매자 매물이 안 보인다"만 단언하면
  **판정식을 잘못 짜서 전체 매물이 사라져도 초록으로 통과한다**(0035 파일 헤더의 실측 — 인라인
  서브쿼리로 짜면 profiles RLS 때문에 exists가 항상 거짓이 되어 anon은 매물이 0건이 된다). 그래서
  이 파일의 모든 케이스는 **긍정 대조군**(활성 판매자 매물이 계속 보인다)을 짝으로 둔다.

무엇을 증명하나 (스펙 Acceptance Criteria):
  ① anon·② 로그인 구매자(타인) — 정지 판매자의 on_sale 매물이 안 보인다.
  ③④ 긍정 대조군 — 같은 두 주체가 **활성** 판매자의 on_sale 매물은 그대로 본다.
  ⑤ 긍정 대조군(건수 고정) — 활성 판매자 N명 중 1명을 정지하면 목록 건수가 **정확히 그 1명의
     매물 수만큼만** 준다(0이 되지 않는다).
  ⑥ 판매자 본인(정지됨) — 자기 매물은 그대로 본다(Never 절 — 정지 해제 후 복구 가능해야 함).
  ⑦⑧ 관리자(활성/정지 무관) — 정지 판매자의 매물을 그대로 본다(17.1의
     `test_suspended_admin_can_still_read_via_admin_select_policies`와 같은 축, `listings_select_admin`
     은 이 스토리가 건드리지 않았다).
  ⑨⑩ ai_readonly — 정지 판매자 매물은 안 보이고, 활성 판매자 매물은 보인다(AI 3경로가 코드
     수정 없이 이 RLS 정책 하나로 닫히는 설계, 0035 4절).
  ⑪ FR11 회귀 — `status='sold'`인 매물은 판매자가 활성이어도 ai_readonly에는 여전히 **보인다**
     (RLS가 아니라 `doc_rag_node.py`/`hybrid_rag_node.py`/`sql_guard.py`의 코드가 sold를 막는
     기존 설계, 0006 CR2 — 이 스토리가 그 축을 건드리지 않았음을 고정한다).
  ⑫⑬ `listing_images` 축 — 정지 판매자 사진은 anon·구매자에게 0행(**중첩 RLS 자동상속**, 별도
     정책 추가 없음 — 0035 3절 실측). ⑭ 긍정 대조군(활성 판매자 사진은 보인다).
  ⑮ 복구 — `status`를 `'active'`로 되돌리면 **아무 추가 조치 없이** 다시 보인다(숨김이 저장이
     아니라 조회 시점 판정이라는 증거 — Never 절 "매물 status를 바꾸지 않는다"와 짝).
  ⑯ 스키마 이동 회귀(2026-08-12 후속 코드리뷰, P1) — `public.is_seller_active`(0035)는
     PostgREST가 RPC로 자동 노출해 anon이 임의 uuid의 정지 여부를 알아내는 오라클이었다(실측:
     `0036_is_seller_active_private_schema.sql` 헤더). `private.is_seller_active`(0036)로 옮긴
     뒤 `public` 버전이 사라졌는지 + 정책이 실제로 쓰는 anon·authenticated·ai_readonly 세 롤의
     EXECUTE가 살아 있는지(빠지면 42501로 조회 전체가 죽는다, 양성 대조군)를 고정한다.
  ⑰ 병렬 플랜 회귀(2026-08-12 후속 코드리뷰, P1) — `private.is_seller_active`(0036)가 `parallel`
     절 없이 선언돼 기본값 PARALLEL UNSAFE였다 — listings를 읽는 모든 쿼리가 병렬 플랜을 못 받는
     회귀였다(실측: `0036_is_seller_active_private_schema.sql` 헤더 ⓐⓑ). 0036을 in-place로 고쳐
     `parallel safe`를 추가했고, `pg_proc.proparallel='s'`로 그 사실을 고정한다.
  ⑱ 사진 축 불변식 후반부(2026-08-12 후속 코드리뷰, P3) — ⑫⑬⑭는 "정지 판매자 사진이 안 보인다
     /활성 판매자 사진이 보인다"만 검사했다. `listings` 축은 본인·관리자 carve-out을 이미 검사로
     고정했는데(⑥⑦⑧) 사진 축은 안 했다 — 동작은 이미 옳았고(실측 확인) 검사만 없었다. 정지된
     판매자 본인과 관리자가 자기/타인의 정지 매물 사진을 그대로 보는 것을 여기서 고정한다.

이 검사가 **안 보는 것** (추측이 아니라 실측/설계로 확인):
  · **red 증명 ⓐⓑ는 이 파일에 자동화된 정책-뒤집기 테스트로 없다.** 정책·함수를 CI 공유 DB에서
    돌면서 실시간으로 뒤집었다 되돌리는 것은 다른 병렬 테스트와 경합하고 되돌림 실패 시 DB가
    깨진 상태로 남을 위험이 있다(17.1의 `test_suspended_write_block_real_db.py`도 같은 이유로
    이 패턴을 안 쓴다). 대신 개발 중 트랜잭션+rollback으로 두 표기 모두 수동 재현했다 — 결과는
    0035 마이그레이션 파일 헤더와 이 스토리 Design Notes(구현 세션 기록)에 남아 있다: ⓐ
    `is_seller_active` 조건을 뺀 판에서 anon이 정지 판매자 매물을 봄(t) · ⓑ 함수 본문을
    `status='suspended'`로 뒤집은 판에서 활성 판매자 매물이 안 보임(f) — 서로 다른 단언이
    각각 깨지는 것까지 확인.
  · **`chat_rooms` 방 생성 진입점은 이 파일이 안 본다.** DW-799 재판정 — 매물이 숨겨져도
    `enforce_chat_room_seller()`(0016, SECURITY DEFINER)가 listings RLS를 우회해 seller_id를
    조회하므로, listing_id를 이미 아는 구매자는 여전히 방을 만들 수 있다(개발 중 실측 확인,
    아래 참고). 브라우저 정상 흐름(상세페이지 → 문의하기 버튼)의 진입점은 사라진다(상세페이지가
    404가 되어 버튼 자체가 안 뜬다) — 그러나 API 직접 호출 경로는 열려 있다. deferred-work.md
    DW-799가 이 판정을 갱신해 들고 있다.
  · **`/wishlist` 회색 타일 흡수는 raw SQL 시뮬레이션으로만 확인했다** — PostgREST의 embed가
    RLS로 막힌 행을 LEFT JOIN처럼 NULL로 돌려준다는 것을 `wishlists LEFT JOIN listings` 형태로
    재현해 에러 없이 NULL이 나옴을 확인했다(개발 중 트랜잭션+rollback). 실제 PostgREST
    HTTP 응답이나 `/wishlist` 화면 렌더까지는 이 파일이 검증하지 않는다 — 그건
    `web/src/lib/__tests__/wishlist.test.ts`(`isWishedListingBlocked(null) === true`, 이미
    sold 축으로 존재)와 웹 E2E의 몫이다.
  · **`listing_images_objects_read`(storage.objects 파일 자체)는 이 파일이 안 본다** — 이 정책은
    애초에 존재하지 않는다: `0014_listing_images_public_bucket.sql:57`이 이 정책을 **drop**했고
    (같은 파일 :55 — 버킷을 공개로 전환하면서 익명 읽기는 `/object/public/` 경로가 담당하게
    됐다), 그 경로는 RLS를 아예 타지 않는다 — "listing_images 조인이라 12축과 같은 메커니즘으로
    자동 상속될 것"이라는 추정은 상속될 정책 자체가 없어 성립하지 않는다(2026-08-12 후속
    코드리뷰 patch, P4 — 이전 판은 이 정책이 아직 있다고 잘못 가정했다). 이 스토리가 이 축을
    범위에서 뺀 진짜 근거는 §6.1(사진 파일 URL은 FR11 대상이 아니라는 2026-07-19 사용자
    결정)과 같다: 파일 URL 접근은 매물·사진 **행** 조회와 다른 축이고, 이 스토리는 행 조회만
    다룬다.
  · **PostgREST의 실제 HTTP 응답 표면은 pytest가 보지 않는다.** 아래
    `test_public_is_seller_active_removed_private_version_exists_with_grants`는 `pg_proc`/
    `pg_namespace`/`has_function_privilege`로 "`public.is_seller_active`가 없고
    `private.is_seller_active`에 세 롤 GRANT가 있다"까지만 확인한다 — `/rest/v1/rpc/
    is_seller_active`가 실제로 42501/404를 반환하는지는 이 파일이 보지 않는다(그건 이 스토리
    코드리뷰 patch(P1)의 Verification 절이 curl로 직접 확인한다).

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import uuid
from contextlib import contextmanager

import psycopg
import pytest

from conftest import _DSN, _create_user, pytestmark  # noqa: F401
from test_suspended_write_block_real_db import (  # noqa: F401
    _as,
    _insert_listing,
    _insert_listing_image,
    _make_admin,
    _photo_path,
    _suspend,
)

@pytest.fixture
def db():
    """행을 만들고 끝나면 롤백한다(형제 파일과 동일 패턴, DB 원상복구)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


@contextmanager
def _as_anon(cur):
    """anon 롤을 흉내낸다(비로그인 조회)."""
    cur.execute("set local role anon")
    try:
        yield
    finally:
        try:
            cur.execute("reset role")
        except psycopg.errors.InFailedSqlTransaction:
            pass


@contextmanager
def _as_ai_readonly(cur):
    """ai_readonly 롤을 흉내낸다(AI 3경로 공용 — sql_guard/doc_rag_node/hybrid_rag_node가
    전부 이 롤로 `listings`에 붙는다, `api/app/db/readonly.py`)."""
    cur.execute("set local role ai_readonly")
    try:
        yield
    finally:
        try:
            cur.execute("reset role")
        except psycopg.errors.InFailedSqlTransaction:
            pass


def _listing_visible(cur, listing_id) -> bool:
    cur.execute("select exists(select 1 from public.listings where id = %s)", (listing_id,))
    return cur.fetchone()[0]


def _photo_visible(cur, listing_id) -> bool:
    cur.execute(
        "select exists(select 1 from public.listing_images where listing_id = %s)", (listing_id,)
    )
    return cur.fetchone()[0]


def _on_sale_count(cur, seller_ids=None) -> int:
    """`on_sale` 매물 건수. `seller_ids`가 없으면(기본) 전역 카운트 — 기존 호출처는 그대로 이
    동작을 쓴다. 넘기면 그 판매자들로 범위를 좁힌다(2026-08-12 후속 코드리뷰 patch, P5) — 전역
    카운트는 같은 트랜잭션이라도 READ COMMITTED에서 다른 세션의 커밋이 그 사이 섞여 들어올 수
    있고, `after > 0` 단언도 자기 시드가 아니라 남의 행 덕에 통과할 수 있다. 판매자 목록으로
    좁히면 두 건수 테스트가 자기가 심은 seller_a·seller_b만 세므로 이 문제가 사라진다."""
    if seller_ids is None:
        cur.execute("select count(*) from public.listings where status = 'on_sale'")
    else:
        cur.execute(
            "select count(*) from public.listings where status = 'on_sale' "
            "and seller_id = any(%s)",
            (list(seller_ids),),
        )
    return cur.fetchone()[0]


# ── ①③ anon — 정지 판매자는 안 보이고, 활성 판매자는 보인다(긍정 대조군) ─────────────────────


def test_anon_cannot_see_suspended_seller_listing(db):
    cur = db
    seller_id = _create_user(cur, f"hide-anon-susp-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as_anon(cur):
        assert not _listing_visible(cur, listing_id), "정지 판매자의 매물이 anon에게 보인다"


def test_anon_sees_active_seller_listing(db):
    """긍정 대조군 — 없으면 위 검사가 '전부 사라짐'에도 초록일 수 있다(0035 헤더 실측 참조)."""
    cur = db
    seller_id = _create_user(cur, f"hide-anon-active-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)

    with _as_anon(cur):
        assert _listing_visible(cur, listing_id), "활성 판매자의 매물이 anon에게 안 보인다(과잉 차단)"


# ── ②④ 로그인 구매자(타인) ──────────────────────────────────────────────────────────────────


def test_buyer_cannot_see_suspended_seller_listing(db):
    cur = db
    seller_id = _create_user(cur, f"hide-buyer-susp-{uuid.uuid4()}@example.test", role="seller")
    buyer_id = _create_user(cur, f"hide-buyer-{uuid.uuid4()}@example.test", role="buyer")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as(cur, buyer_id):
        assert not _listing_visible(cur, listing_id), "정지 판매자의 매물이 로그인 구매자에게 보인다"


def test_buyer_sees_active_seller_listing(db):
    """긍정 대조군."""
    cur = db
    seller_id = _create_user(cur, f"hide-buyer-active-{uuid.uuid4()}@example.test", role="seller")
    buyer_id = _create_user(cur, f"hide-buyer2-{uuid.uuid4()}@example.test", role="buyer")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)

    with _as(cur, buyer_id):
        assert _listing_visible(cur, listing_id), "활성 판매자의 매물이 로그인 구매자에게 안 보인다"


# ── ⑤ 긍정 대조군(건수 고정) — 정지된 판매자의 매물 수만큼만 정확히 준다(0이 되지 않는다) ────────
# 코드리뷰 patch(P7): n=1짜리 케이스 하나만으로는 "정확히 그 판매자의 매물 수만큼"과 "행 하나가
# 줄었다"를 구별할 수 없다(우연히 일치) — n=2 케이스를 짝으로 둬서 "그 판매자의 매물 수"가 실제로
# 세어지고 있음을 고정한다. 두 테스트 다 같은 시드(seller_a=2건, seller_b=1건)를 각각 독립적으로
# 만든다(트랜잭션+rollback으로 서로 격리, db 픽스처).


def test_listing_count_drops_by_exactly_one_when_suspended_seller_has_one_listing(db):
    cur = db
    seller_a = _create_user(cur, f"hide-count-a-{uuid.uuid4()}@example.test", role="seller")
    seller_b = _create_user(cur, f"hide-count-b-{uuid.uuid4()}@example.test", role="seller")
    listing_a1, listing_a2 = uuid.uuid4(), uuid.uuid4()
    listing_b1 = uuid.uuid4()
    _insert_listing(cur, listing_a1, seller_a)
    _insert_listing(cur, listing_a2, seller_a)
    _insert_listing(cur, listing_b1, seller_b)

    with _as_anon(cur):
        before = _on_sale_count(cur, seller_ids=[seller_a, seller_b])

    _suspend(cur, seller_b)

    with _as_anon(cur):
        after = _on_sale_count(cur, seller_ids=[seller_a, seller_b])

    assert after == before - 1, (
        f"정지 판매자(1건 매물) 정지 후 건수가 정확히 1만 줄어야 한다 (before={before}, after={after})"
    )
    # after > 0은 이제 자기 시드(seller_a, 여전히 활성)의 매물 덕에 성립한다 — 전역 카운트가
    # 아니라 seller_ids로 좁혔으므로 남의 행에 기대지 않는다(P5).
    assert after > 0, "건수가 0이 되면 '전부 사라짐'과 구별할 수 없다"


def test_listing_count_drops_by_exactly_two_when_suspended_seller_has_two_listings(db):
    """n=1 케이스와 짝 — 정지된 판매자의 매물이 2건이면 정확히 2만 줄어야 한다(1이나 3이 아니다).
    n=1만 있으면 "행 하나가 줄었다"는 잘못된 구현(예: LIMIT 1로 아무 매물이나 하나 숨기는 버그)도
    통과할 수 있어, 그 사각을 이 테스트가 막는다."""
    cur = db
    seller_a = _create_user(cur, f"hide-count2-a-{uuid.uuid4()}@example.test", role="seller")
    seller_b = _create_user(cur, f"hide-count2-b-{uuid.uuid4()}@example.test", role="seller")
    listing_a1, listing_a2 = uuid.uuid4(), uuid.uuid4()
    listing_b1 = uuid.uuid4()
    _insert_listing(cur, listing_a1, seller_a)
    _insert_listing(cur, listing_a2, seller_a)
    _insert_listing(cur, listing_b1, seller_b)

    with _as_anon(cur):
        before = _on_sale_count(cur, seller_ids=[seller_a, seller_b])

    _suspend(cur, seller_a)

    with _as_anon(cur):
        after = _on_sale_count(cur, seller_ids=[seller_a, seller_b])

    assert after == before - 2, (
        f"정지 판매자(2건 매물) 정지 후 건수가 정확히 2만 줄어야 한다 (before={before}, after={after})"
    )
    # after > 0은 이제 자기 시드(seller_b, 여전히 활성)의 매물 덕에 성립한다 — 전역 카운트가
    # 아니라 seller_ids로 좁혔으므로 남의 행에 기대지 않는다(P5).
    assert after > 0, "건수가 0이 되면 '전부 사라짐'과 구별할 수 없다"


# ── ⑥ 판매자 본인(정지됨) — 자기 매물은 그대로 본다 ──────────────────────────────────────────


def test_suspended_seller_still_sees_own_listing(db):
    cur = db
    seller_id = _create_user(cur, f"hide-self-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        assert _listing_visible(cur, listing_id), "정지된 판매자가 본인 매물을 못 본다(복구 불가능해짐)"


# ── ⑦⑧ 관리자(활성·정지 무관) — 정지 판매자의 매물을 그대로 본다 ─────────────────────────────


def test_active_admin_sees_suspended_seller_listing(db):
    cur = db
    seller_id = _create_user(cur, f"hide-admin-active-{uuid.uuid4()}@example.test", role="seller")
    admin_id = _create_user(cur, f"hide-admin-a-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as(cur, admin_id):
        assert _listing_visible(cur, listing_id), "활성 관리자가 정지 판매자의 매물을 못 본다"


def test_suspended_admin_sees_suspended_seller_listing(db):
    """17.1의 회귀 가드(listings_select_admin은 is_admin() 그대로)와 같은 축 — 이 스토리가
    그 정책을 안 건드렸음을 재확인한다."""
    cur = db
    seller_id = _create_user(cur, f"hide-admin-susp-{uuid.uuid4()}@example.test", role="seller")
    admin_id = _create_user(cur, f"hide-admin-b-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        assert _listing_visible(cur, listing_id), "정지된 관리자도 매물 열람은 유지돼야 한다(17.1 원칙)"


# ── ⑨⑩ ai_readonly — AI 3경로가 이 한 자리에서 닫힌다 ────────────────────────────────────────


def test_ai_readonly_cannot_see_suspended_seller_listing(db):
    cur = db
    seller_id = _create_user(cur, f"hide-ai-susp-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as_ai_readonly(cur):
        assert not _listing_visible(cur, listing_id), "정지 판매자의 매물이 ai_readonly에 보인다"


def test_ai_readonly_sees_active_seller_listing(db):
    """긍정 대조군."""
    cur = db
    seller_id = _create_user(cur, f"hide-ai-active-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)

    with _as_ai_readonly(cur):
        assert _listing_visible(cur, listing_id), "활성 판매자의 매물이 ai_readonly에 안 보인다"


def test_ai_readonly_still_sees_sold_listing_from_active_seller_fr11_regression(db):
    """FR11 회귀 0 — sold는 RLS가 아니라 코드(doc_rag_node.py 등)가 막는 기존 설계(0006 CR2).
    이 스토리가 `listings_ai_readonly_select`에 판매자 조건만 더했을 뿐 status 축은 안 건드렸다는
    것을 고정한다 — 여기서 sold가 안 보이게 바뀌면 AI 코드 3곳의 `status='on_sale'` 필터가
    이중 방어에서 유일한 방어로 바뀌어 있다는 뜻이라 그 코드가 놓치는 순간 sold가 노출된다."""
    cur = db
    seller_id = _create_user(cur, f"hide-ai-sold-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")

    with _as_ai_readonly(cur):
        assert _listing_visible(cur, listing_id), (
            "ai_readonly RLS가 sold까지 막기 시작했다 — 0006 CR2 설계(코드가 sold를 막는다)가 깨졌다"
        )


# ── ⑫⑬⑭ listing_images 축 — 중첩 RLS 자동 상속(0035 3절 실측, 별도 정책 추가 없음) ────────────


def test_suspended_seller_photo_hidden_from_anon(db):
    cur = db
    seller_id = _create_user(cur, f"hide-photo-anon-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "photo.jpg")
    _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as_anon(cur):
        assert not _photo_visible(cur, listing_id), "정지 판매자 매물 사진이 anon에게 보인다"


def test_suspended_seller_photo_hidden_from_buyer(db):
    cur = db
    seller_id = _create_user(cur, f"hide-photo-buyer-{uuid.uuid4()}@example.test", role="seller")
    buyer_id = _create_user(cur, f"hide-photo-buyer2-{uuid.uuid4()}@example.test", role="buyer")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "photo.jpg")
    _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as(cur, buyer_id):
        assert not _photo_visible(cur, listing_id), "정지 판매자 매물 사진이 로그인 구매자에게 보인다"


def test_active_seller_photo_visible_to_anon(db):
    """긍정 대조군 — 없으면 사진 축도 '전부 사라짐'과 구별 안 된다."""
    cur = db
    seller_id = _create_user(cur, f"hide-photo-active-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "photo.jpg")
    _insert_listing_image(cur, listing_id, path)

    with _as_anon(cur):
        assert _photo_visible(cur, listing_id), "활성 판매자 매물 사진이 anon에게 안 보인다"


# ── ⑱ 사진 축 불변식 후반부(2026-08-12 후속 코드리뷰, P3) — 본인·관리자는 그대로 본다 ──────────
# `listings` 축은 본인·관리자 carve-out을 검사로 고정했는데(⑥⑦⑧) 사진 축은 안 했다. 로컬 55322
# 실측(트랜잭션+rollback): 판매자를 정지시킨 뒤에도 본인은 자기 매물(1행)과 사진(1행)을 그대로
# 보고, 관리자도 그 매물(1행)과 사진(1행)을 그대로 본다 — 동작은 이미 옳았고 검사만 없었다.


def test_suspended_seller_still_sees_own_listing_photo(db):
    """⑥의 사진 판. 정지된 판매자 본인은 자기 매물 사진을 계속 본다(복구 후에도 사진이 그대로
    남아 있어야 하므로)."""
    cur = db
    seller_id = _create_user(cur, f"hide-photo-self-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "photo.jpg")
    _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        assert _photo_visible(cur, listing_id), "정지된 판매자가 본인 매물 사진을 못 본다"


def test_admin_sees_suspended_seller_listing_photo(db):
    """⑦⑧의 사진 판. 관리자는 정지 판매자 매물 사진을 그대로 본다."""
    cur = db
    seller_id = _create_user(cur, f"hide-photo-admin-{uuid.uuid4()}@example.test", role="seller")
    admin_id = _create_user(cur, f"hide-photo-admin-a-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "photo.jpg")
    _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as(cur, admin_id):
        assert _photo_visible(cur, listing_id), "관리자가 정지 판매자의 매물 사진을 못 본다"


# ── ⑮ 복구 — status를 되돌리면 아무 추가 조치 없이 다시 보인다(조회 시점 판정) ──────────────────


def test_unsuspend_restores_visibility_without_further_action(db):
    cur = db
    seller_id = _create_user(cur, f"hide-recover-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as_anon(cur):
        assert not _listing_visible(cur, listing_id), "정지 직후 매물이 여전히 보인다(전제 실패)"

    cur.execute("update public.profiles set status = 'active' where id = %s", (seller_id,))

    with _as_anon(cur):
        assert _listing_visible(cur, listing_id), (
            "정지를 해제했는데도 매물이 다시 보이지 않는다 — 숨김이 저장된 상태라면 CLAUDE.md B3 위반"
        )


# ── ⑯ 스키마 이동 회귀(2026-08-12 후속 코드리뷰, P1) — public.is_seller_active는 RPC 노출
#     오라클이었다(실측: 0036 파일 헤더). private로 옮긴 뒤 그 노출면이 사라졌는지 + 정책이
#     실제로 쓰는 세 롤의 EXECUTE가 살아 있는지(빠지면 42501로 조회 전체가 죽는다) 고정한다.


def test_public_is_seller_active_removed_private_version_exists_with_grants(db):
    cur = db

    cur.execute(
        "select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where p.proname = 'is_seller_active' and n.nspname = 'public'"
    )
    assert cur.fetchone()[0] == 0, (
        "public.is_seller_active가 아직 존재한다 — PostgREST가 RPC로 자동 노출해 anon이 임의 "
        "uuid의 정지 여부를 알아낼 수 있다(0036 헤더 실측). drop function이 빠졌다"
    )

    cur.execute(
        "select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where p.proname = 'is_seller_active' and n.nspname = 'private'"
    )
    assert cur.fetchone()[0] == 1, "private.is_seller_active가 없다 — 0036이 적용되지 않았다"

    # 양성 대조군 — GRANT가 빠지면 정책 평가 자체가 42501로 죽는다(0행이 아니라 요청 전체 실패).
    # anon·authenticated·ai_readonly 셋 다 실제로 이 함수를 참조하는 정책이 있다(listings_select_
    # on_sale/_anon·listings_ai_readonly_select, 0036). 0036 헤더는 "스키마 USAGE + 함수 EXECUTE
    # 둘 다 있어야 한다"고 적었는데, has_function_privilege는 함수 EXECUTE만 보고 스키마 USAGE는
    # 안 본다 — 그래서 has_schema_privilege도 함께 단언한다(2026-08-12 후속 코드리뷰 patch, P4).
    for role in ("anon", "authenticated", "ai_readonly"):
        cur.execute(
            "select has_function_privilege(%s, 'private.is_seller_active(uuid)', 'execute')",
            (role,),
        )
        assert cur.fetchone()[0] is True, (
            f"{role}에 private.is_seller_active EXECUTE가 없다 — 그 롤의 listings 조회가 "
            "42501로 통째로 죽는다(GRANT 누락은 0행이 아니라 요청 전체 실패로 나타난다)"
        )

        cur.execute("select has_schema_privilege(%s, 'private', 'usage')", (role,))
        assert cur.fetchone()[0] is True, (
            f"{role}에 private 스키마 USAGE가 없다 — 함수 EXECUTE가 있어도 스키마를 못 찾아 "
            "42501로 그 롤의 listings 조회가 통째로 죽는다(0036 헤더: 둘 다 있어야 한다)"
        )


# ── ⑰ 병렬 플랜 회귀(2026-08-12 후속 코드리뷰, P1) ────────────────────────────────────────────


def test_is_seller_active_is_parallel_safe(db):
    """`private.is_seller_active`가 `parallel safe`로 선언돼 있는가(0036 in-place 패치).

    이 함수는 listings_select_on_sale/_anon·listings_ai_readonly_select 세 정책의 using 절에
    들어간다 — `parallel` 절이 없으면 Postgres 기본값 PARALLEL UNSAFE가 되고, listings를 읽는
    모든 쿼리가 병렬 플랜을 아예 못 받는다.

    실측(로컬 55322, 트랜잭션+rollback, parallel_setup_cost=0·parallel_tuple_cost=0·
    min_parallel_table_scan_size=0·max_parallel_workers_per_gather=2):
      - 패치 전(parallel 절 없음) — `set local role anon; explain select id from public.listings
        where status='on_sale'` → Seq Scan(병렬 없음).
      - 대조군(정책 없는 슈퍼유저) → Gather / Workers Planned: 2 / Parallel Seq Scan.
      - ⓐ 정책에서 is_seller_active 조건을 빼고 17.4 이전 형태로 되돌리면 → Gather 복구(이
        회귀를 17.4가 만들었음이 증명됨).
      - ⓑ 조건은 그대로 두고 `alter function private.is_seller_active(uuid) parallel safe`만
        추가하면 → Gather 복구(한 단어가 원인).

    이 검사가 안 보는 것: 이 검사는 `pg_proc.proparallel` 카탈로그 플래그만 보고 실제 플랜
    (Gather 유무)은 보지 않는다 — 플랜 자체를 단언하면 테이블 크기·비용 GUC에 좌우돼 빈 테이블인
    fresh CI 컨테이너에서 불안정하다(로컬 실측처럼 GUC를 직접 낮추지 않는 한 CI에서는 애초에
    병렬 플랜 자체가 잘 안 뜬다), 그래서 일부러 카탈로그 축으로 고정했다. 플래너가 병렬 워커에
    함수를 맡길지 말지 실제로 참조하는 값이 바로 이 카탈로그 플래그이므로, 이 축이 근본 원인을
    가장 안정적으로 잡는다.
    """
    cur = db
    cur.execute(
        "select p.proparallel from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
        "where p.proname = 'is_seller_active' and n.nspname = 'private'"
    )
    row = cur.fetchone()
    assert row is not None, "private.is_seller_active를 찾을 수 없다"
    assert row[0] == "s", (
        f"private.is_seller_active의 proparallel이 {row[0]!r}이다 — 's'(PARALLEL SAFE)가 아니면 "
        "listings를 읽는 모든 쿼리가 병렬 플랜을 못 받는다(0036 헤더 실측 ⓐⓑ)"
    )
