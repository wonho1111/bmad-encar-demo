"""정지(profiles.status='suspended') 회원의 쓰기 차단 실DB 검증 — 0032·0033이 실제로 막는가
(Story 17.1, DW-669·DW-717·DW-721·DW-782 + DW-674 일반 소유권 회귀).

왜 이 파일이 따로 있나:
  0032가 SQL로 RLS 정책·SECURITY DEFINER 함수를 고치는 것과, 정지된 세션으로 실제
  INSERT/UPDATE/DELETE를 쏴 보고 거부되는 것은 다른 사실이다(CLAUDE.md B4 "존재 확인은
  작동 확인이 아니다"). 이 파일은 그 실제 시도를 스펙 Acceptance Criteria 전항목에 대해 한다.

⚠️ **SQLSTATE 42501 vs "0행" — 이 파일 전체가 지키는 구분(재보고 확정한 것)**:
  Postgres RLS는 INSERT(WITH CHECK만 있는 경우)를 거부할 때 SQLSTATE 42501 예외를 던진다.
  반면 UPDATE/DELETE의 USING절이 대상 행을 애초에 안 보여주는 거부는 **예외가 아니라 그냥
  0행**이다(WHERE절이 걸러낸 것과 동일 — 로컬 실측: `update ... using(...)`이 필터링한 UPDATE는
  `UPDATE 0`만 찍고 끝난다, 에러 없음). 이 저장소의 기존 관례도 같은 사실을 이미 적어 뒀다
  (`0015_listings_update_not_sold.sql`:25-27 "RLS 거부는 에러가 아니라 0행으로 오므로"),
  그리고 이 스토리가 흡수하는 DW-674 원문도 정확히 "비소유자 UPDATE/DELETE가 **0행**, 타인
  명의 INSERT가 **42501**"이라고 구분해 적어 뒀다. 스펙 본문의 Acceptance Criteria는 UPDATE·
  DELETE 항목에도 "42501로 거부"라고 뭉뚱그려 적었는데, 로컬 실측(아래 각 테스트가 재현)
  결과 그 문구는 부정확하다 — 그래서 이 파일은 **실측된 대로** UPDATE/DELETE는 rowcount==0,
  INSERT만 SQLSTATE 42501로 단언한다. "쓰기가 성공하지 못한다"는 스펙의 불변식은 두 형태
  모두에서 동일하게 성립한다 — 관측 가능한 신호(예외 vs 0행)만 다르다.

무엇을 증명하나 (스펙 Acceptance Criteria 전항목 + DW-674):
  ① 정지된 판매자의 listings INSERT — 42501, 0행 삽입.
  ② 정지된 판매자의 (본인) listings UPDATE/DELETE — 0행, 매물 상태 불변.
  ③ 정지된 판매자의 (본인 매물) listing_images INSERT — 42501 / UPDATE·DELETE — 0행.
  ④ 정지된 판매자의 storage.objects(본인 경로) INSERT — 42501 / UPDATE·DELETE — 0행.
  ⑤ **활성** 판매자의 sold 매물 storage.objects 쓰기(DW-782, 정지와 무관) — INSERT 42501 /
     UPDATE·DELETE 0행.
  ⑤b storage.objects 경로의 두 번째 세그먼트가 uuid 형식이 아닐 때 — 예외(22P02) 없이 42501로
     조용히 거부(2026-08-11 코드리뷰: split_part(...)::uuid 캐스팅 가드).
  ⑥ 정지된 관리자의 listings_delete_admin(남의 매물) — 0행.
  ⑦ 정지된 관리자의 admin_restore_sold_listing RPC — 0행 반환, status 불변.
  ⑧ 정지된 관리자의 자가 정지 해제 시도(본인 profiles.status UPDATE) — 0행.
  ⑨ **활성** 관리자는 위 관리자 작업 전부 회귀 없이 성공(매물 삭제 1행·RPC 1행+status 변경·
     타인 profiles UPDATE 1행).
  ⑨b 정지된 관리자도 admin 읽기 정책(listings_select_admin·profiles_select_admin, 둘 다
     is_admin() 그대로)으로는 여전히 읽을 수 있다 — is_admin_active()를 쓰기 소비처에만 넣은
     설계 근거 자체를 실측한다(2026-08-11 코드리뷰가 지적: 이 근거를 검증하는 테스트가 없었다).
  ⑩ 정지된 회원의 읽기(본인 listings/profiles SELECT, 남의 on_sale 매물 탐색)는 전부 무변화.
  ⑪ [[DW-674]] 활성·비관리자가 **남의** listings UPDATE/DELETE — 0행(정지와 무관한 일반
     소유권 회귀 — 이 축을 지키는 반복 검사가 이 스토리 전까지 저장소에 없었다).
  ⑫ 정지된 채팅 참가자의 chat_messages INSERT — 42501(스펙 Design Notes의 "막는다" 결정).
  ⑬ **활성** 참가자의 정상 발신은 여전히 방송(realtime.messages)·안읽음 카운트가 그대로
     동작한다 — ⑫가 정상 흐름을 깨지 않는다는 실측(스펙 Design Notes가 요구한 확인).
  ⑭ 레거시 가입 경로(auth.users metadata에 role='seller')로 가입해도 profiles.role='user'로
     배정된다 — 0033이 통과 분기를 지워도 결과가 바뀌지 않는다(이미 도달 불가능한 분기였다는
     근거 재확인).

2026-08-11 bad_spec 루프백 #1이 추가한 항목 (거부-only 테스트 7건이 "정지만 막힘"과 "전부
막힘"을 구별 못 해 21/21 green으로 통과시켰던 결함들 — 위 목록과 짝을 이루는 긍정 대조군·
회귀 고정·전수조사 후속 단언):
  ⑮ **긍정 대조군** — 활성 판매자의 `listing_images`·`storage.objects` INSERT/UPDATE/DELETE는
     (sold가 아닌 자기 매물이면) 전부 성공한다. 이게 없으면 ③④가 "정지만 막는다"가 아니라
     "전부 막는다"로 잘못 짜여도 green이 된다.
  ⑯ **§10.1 순서 회귀 고정(on_sale·sold 양쪽 파라미터화, 3차 코드리뷰 patch로 실제 클라이언트
     순서를 미러링하도록 재작성)** — 활성 판매자가 실제 클라이언트 순서(① `listing_images`에서
     경로를 먼저 SELECT → ② `listings` 행 DELETE(cascade로 `listing_images` 소멸) → ③ ①에서
     미리 읽어 둔 경로로 `storage.objects` 사진 DELETE)를 밟으면 ③이 1행으로 성공하고 고아가
     0건 남는다. `sold` 분기는 추가로 매물이 아직 살아 있는 동안 사진 DELETE가 차단되는 것까지
     확인한다. storage owner DELETE가 "살아 있는 non-sold 매물" 긍정형으로 되돌아가면 이
     테스트가 red가 된다(로컬 실 스택 재현으로 확정된 최상위 결함, 위 마이그레이션 4)절 참조).
  ⑰ **관리자 쓰기 정책 6개 중 나머지 4개의 양방향** — `profiles_delete_admin`·
     `chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete`
     각각 정지된 관리자는 0행, 활성 관리자는 1행(⑥⑨는 `listings_delete_admin`·
     `admin_restore_sold_listing`·`profiles_update_admin` 3개만 덮었다).
  ⑱ **[[DW-674]] 타인 명의 INSERT** — 활성·비관리자가 `seller_id`를 타인으로 위조해 `listings`
     INSERT를 시도하면 42501(⑪은 UPDATE/DELETE만 덮었다 — INSERT 위조 단언 없이 DW-674가
     닫혔던 자리).
  ⑲ **storage 소유자 join의 소유권 축** — 활성 판매자 A가 `{A의 uid}/{B의 on_sale 매물
     id}/파일명` 경로로 INSERT를 시도하면 42501(경로 1번째 세그먼트만 보면 통과해 버리는 축 —
     join에 `l.seller_id = auth.uid()`가 있어야 막힌다).
  ⑳ **레거시(비-UUID) 경로 DELETE는 소유자가 정리 가능** — 2번째 경로 세그먼트가 UUID 형식이
     아닌 오브젝트도 소유자는 DELETE로 지울 수 있다(부정형 DELETE의 의도된 부작용 — CASE 가드가
     NULL을 돌려 `NOT EXISTS`가 참이 된다).

이 검사가 **안 보는 것** (추측이 아니라 실측/설계로 확인한 것):
  · **storage.objects DELETE는 플랫폼 보호 트리거를 우회해야 테스트할 수 있다.** 로컬 실
    Supabase 스택은 `storage.protect_objects_delete`(BEFORE DELETE FOR EACH STATEMENT)가
    `storage.allow_delete_query` 세션 GUC가 'true'가 아니면 **행 매치와 무관하게** SQLSTATE
    42501로 직접 SQL DELETE 자체를 막는다(Storage API 우회 방지 — Supabase 플랫폼 기능이지
    이 스토리가 만든 것이 아니다). 이 파일은 그 GUC를 켜고 RLS만 격리해서 본다 — **실제
    Storage API(HTTP) 경로는 검증하지 않는다**(이 저장소 다른 실DB 테스트 전반의 공통 gap과
    동일 성격, `test_restore_sold_listing_rpc_real_db.py` 헤더 참조). CI의 `migration-check-
    prelude.sql` 스텁에는 이 트리거가 없어 GUC 설정이 아무 효과 없이 무해하게 지나간다 —
    로컬·CI 양쪽에서 같은 코드로 동작한다.
  · **`is_admin_active()`가 다른 신규 SECURITY DEFINER 함수에도 일관 적용되는지는 범위
    밖이다** — 저장소 전체 SECURITY DEFINER 감사는 이 스토리가 하지 않는다.
  · **원격(prod) Supabase의 `authenticated` GRANT가 로컬과 동일한지는 검증하지 않는다**
    (DW-722 범위) — 로컬 grant 재적용으로 우회한다(아래 실행법 참조).
  · 관리자 감사 로그가 없으므로 "누가 언제 이 정책에 막혔는지"는 기록되지 않는다(DW-718,
    별건 — 이 스토리가 만들지 않는다).
  · 웹/앱이 이 SQLSTATE·0행을 사용자에게 어떤 문구로 보여주는지는 이 파일이 보지 않는다
    (DB 계층만 본다 — 화면 방어로 대체하지 않는다는 스토리 Never 절과 같은 경계).

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: 스택 기동 후 GRANT 보정(DW-722) —
    `psql "$LOCAL_DB_URL" -c "grant all on all tables in schema public to anon, authenticated, service_role;"`
    (스펙 Verification 원문의 `grant all on tables in schema public ...`는 문법 오류다 —
    Postgres는 `grant ... on all tables in schema ...`를 요구한다. 실측으로 확인해 정정.)
  TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).

  ⚠️ **위 GRANT는 `supabase db reset` 직후(다른 테스트가 아직 안 돈 상태)에만 그대로 실행한다.**
  이미 마이그레이션이 다 적용돼 있고 다른 테스트도 몇 번 돈 로컬 스택에 그대로 실행하면,
  `0011`·`0012`·`0020`·`0021`이 걸어 둔 컬럼 단위 GRANT 축소(anon의 `listings.embedding` 차단 등)가
  통째로 풀려 그 축소를 전제한 다른 테스트가 깨진다(2026-08-11 코드리뷰 세션이 실측 — 무관한
  테스트 9건이 빨간불이 됐다가 아래 재적용으로 복구). 이미 적용된 스택에서 GRANT를 다시 걸어야
  하면, 위 명령 직후 그 네 마이그레이션 파일을 다시 `psql -f`로 재적용해 축소를 복원한다.
"""

import uuid
from contextlib import contextmanager

import psycopg
import pytest

from conftest import _DSN, _create_user, pytestmark  # noqa: F401

_RLS_VIOLATION = "42501"

# RLS 거부와 "GRANT 누락으로 인한 권한 거부"는 둘 다 42501이라 sqlstate만으로는 구별되지 않는다
# (2026-08-11 2차 코드리뷰 patch — 이 스토리 1차 리뷰에서 실제로 storage GRANT 누락이 42501로
# 통과한 사례가 있었다, `scripts/migration-check-prelude.sql`의 storage GRANT 주석 참조). 저장소
# 관례대로(`test_chat_unread_real_db.py`) 메시지 마크까지 함께 대조한다.
_RLS_MESSAGE_MARK = "row-level security policy"

_LISTING_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)


@pytest.fixture
def db():
    """행을 만들고 **끝나면 롤백**한다(형제 파일들과 동일 패턴, DB 원상복구)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


def _insert_listing(cur, listing_id, seller_id, status="on_sale"):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, %s, '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id, status),
    )


def _suspend(cur, user_id):
    cur.execute("update public.profiles set status = 'suspended' where id = %s", (user_id,))


def _make_admin(cur, user_id):
    cur.execute("update public.profiles set role = 'admin' where id = %s", (user_id,))


def _listing_status(cur, listing_id):
    cur.execute("select status from public.listings where id = %s", (listing_id,))
    return cur.fetchone()[0]


def _profile_status(cur, user_id):
    cur.execute("select status from public.profiles where id = %s", (user_id,))
    return cur.fetchone()[0]


def _photo_path(owner_id, listing_id, filename="photo.jpg"):
    return f"{owner_id}/{listing_id}/{filename}"


def _insert_storage_object(cur, name):
    cur.execute(
        "insert into storage.objects (bucket_id, name) values ('listing-images', %s) returning id",
        (name,),
    )
    return cur.fetchone()[0]


def _insert_listing_image(cur, listing_id, storage_path, sort_order=0):
    cur.execute(
        "insert into public.listing_images (listing_id, storage_path, sort_order) "
        "values (%s, %s, %s) returning id",
        (listing_id, storage_path, sort_order),
    )
    return cur.fetchone()[0]


def _insert_chat_room(cur, listing_id, buyer_id, seller_id):
    room_id = uuid.uuid4()
    cur.execute(
        "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) values (%s, %s, %s, %s)",
        (room_id, listing_id, buyer_id, seller_id),
    )
    return room_id


def _insert_chat_message(cur, room_id, sender_id, body="메시지"):
    cur.execute(
        "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s) returning id",
        (room_id, sender_id, body),
    )
    return cur.fetchone()[0]


@contextmanager
def _as(cur, user_id):
    """authenticated 롤 + JWT sub로 특정 사용자를 흉내낸다(레포 관례: `set local role` +
    `request.jwt.claim.sub`). `storage.allow_delete_query`도 함께 켠다 — 로컬 실 Supabase의
    storage.objects DELETE 보호 트리거(플랫폼 기능, 위 헤더 참조)를 우회해 RLS만 격리해서
    보기 위함이다(storage.objects를 안 건드리는 테스트에는 무해).

    reset은 try/finally로 감싼다(0020·0025·0030 관례와 동일) — 예외가 SAVEPOINT 밖으로
    전파되는 경로에서는 트랜잭션이 이미 죽어 있어 reset 자체가 실패할 수 있으므로 조용히
    넘어간다(그 경우 SAVEPOINT 롤백이 SET LOCAL도 함께 되돌린다).
    """
    cur.execute(f"set local request.jwt.claim.sub = '{user_id}'")
    cur.execute("set local role authenticated")
    cur.execute("set local storage.allow_delete_query = 'true'")
    try:
        yield
    finally:
        try:
            cur.execute("reset role")
            cur.execute("reset request.jwt.claim.sub")
            cur.execute("reset storage.allow_delete_query")
        except psycopg.errors.InFailedSqlTransaction:
            pass


# ── ① listings INSERT — 정지된 판매자 ──────────────────────────────────────────────────────


def test_suspended_seller_cannot_insert_listing(db):
    cur = db
    seller_id = _create_user(cur, f"susp-ins-{uuid.uuid4()}@example.test")
    _suspend(cur, seller_id)
    new_id = uuid.uuid4()

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                cur.execute(
                    f"insert into public.listings ({_LISTING_COLS}) values "
                    "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
                    "'흰색', '가솔린', '자동', 1998, 5, '서울')",
                    (new_id, seller_id),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select count(*) from public.listings where id = %s", (new_id,))
    assert cur.fetchone()[0] == 0, "정지된 판매자의 INSERT가 실제로 행을 남겼다"


# ── ② listings UPDATE/DELETE — 정지된 판매자, 본인 매물 ─────────────────────────────────────


def test_suspended_seller_cannot_update_own_listing(db):
    cur = db
    seller_id = _create_user(cur, f"susp-upd-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute(
            "update public.listings set price = 1 where id = %s", (listing_id,)
        )
        assert cur.rowcount == 0, "정지된 판매자가 본인 매물을 UPDATE했다"

    cur.execute("select price from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 26700000, "매물 가격이 실제로 바뀌었다"


def test_suspended_seller_cannot_delete_own_listing(db):
    cur = db
    seller_id = _create_user(cur, f"susp-del-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute("delete from public.listings where id = %s", (listing_id,))
        assert cur.rowcount == 0, "정지된 판매자가 본인 매물을 DELETE했다"

    cur.execute("select count(*) from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 1, "매물이 실제로 사라졌다"


# ── ③ listing_images INSERT/UPDATE/DELETE — 정지된 판매자, 본인 매물 사진 ─────────────────────


def test_suspended_seller_cannot_insert_listing_image(db):
    cur = db
    seller_id = _create_user(cur, f"susp-img-ins-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)
    path = _photo_path(seller_id, listing_id, "new.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                cur.execute(
                    "insert into public.listing_images (listing_id, storage_path) values (%s, %s)",
                    (listing_id, path),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select count(*) from public.listing_images where storage_path = %s", (path,))
    assert cur.fetchone()[0] == 0


def test_suspended_seller_cannot_update_listing_image(db):
    cur = db
    seller_id = _create_user(cur, f"susp-img-upd-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "existing.jpg")
    image_id = _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute(
            "update public.listing_images set sort_order = 9 where id = %s", (image_id,)
        )
        assert cur.rowcount == 0, "정지된 판매자가 본인 매물 사진을 UPDATE했다"

    cur.execute("select sort_order from public.listing_images where id = %s", (image_id,))
    assert cur.fetchone()[0] == 0


def test_suspended_seller_cannot_delete_listing_image(db):
    cur = db
    seller_id = _create_user(cur, f"susp-img-del-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    path = _photo_path(seller_id, listing_id, "existing2.jpg")
    image_id = _insert_listing_image(cur, listing_id, path)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute("delete from public.listing_images where id = %s", (image_id,))
        assert cur.rowcount == 0, "정지된 판매자가 본인 매물 사진을 DELETE했다"

    cur.execute("select count(*) from public.listing_images where id = %s", (image_id,))
    assert cur.fetchone()[0] == 1


# ── ④ storage.objects INSERT/UPDATE/DELETE — 정지된 판매자, 본인 경로 ─────────────────────────


def test_suspended_seller_cannot_insert_storage_object(db):
    cur = db
    seller_id = _create_user(cur, f"susp-obj-ins-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)
    name = _photo_path(seller_id, listing_id, "new.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                _insert_storage_object(cur, name)
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (name,),
    )
    assert cur.fetchone()[0] == 0


def test_suspended_seller_cannot_update_storage_object(db):
    cur = db
    seller_id = _create_user(cur, f"susp-obj-upd-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    name = _photo_path(seller_id, listing_id, "existing.jpg")
    _insert_storage_object(cur, name)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute(
            "update storage.objects set metadata = '{\"x\":1}'::jsonb "
            "where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 0, "정지된 판매자가 본인 사진 파일을 UPDATE했다"


def test_suspended_seller_cannot_delete_storage_object(db):
    cur = db
    seller_id = _create_user(cur, f"susp-obj-del-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    name = _photo_path(seller_id, listing_id, "existing2.jpg")
    _insert_storage_object(cur, name)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 0, "정지된 판매자가 본인 사진 파일을 DELETE했다"

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (name,),
    )
    assert cur.fetchone()[0] == 1


# ── ⑤ storage.objects INSERT/UPDATE/DELETE — 활성 판매자, sold 매물 (DW-782, 정지와 무관) ────


def test_active_seller_cannot_write_storage_object_for_sold_listing(db):
    """DW-782: listing_images 행에만 있던 sold 차단이 storage.objects 파일 자체에도 있는가.
    이 테스트는 **정지와 무관** — 활성 판매자로만 시나리오를 구성해 sold 축을 격리한다."""
    cur = db
    seller_id = _create_user(cur, f"active-sold-obj-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")
    assert _profile_status(cur, seller_id) == "active", "전제 실패 — 이 검사는 정지와 무관해야 한다"
    existing_name = _photo_path(seller_id, listing_id, "existing.jpg")
    _insert_storage_object(cur, existing_name)
    new_name = _photo_path(seller_id, listing_id, "new.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                _insert_storage_object(cur, new_name)
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    with _as(cur, seller_id):
        cur.execute(
            "update storage.objects set metadata = '{\"x\":1}'::jsonb "
            "where bucket_id = 'listing-images' and name = %s",
            (existing_name,),
        )
        assert cur.rowcount == 0, "활성 판매자가 sold 매물의 사진 파일을 UPDATE했다"

        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (existing_name,),
        )
        assert cur.rowcount == 0, "활성 판매자가 sold 매물의 사진 파일을 DELETE했다"


# ── ⑤b storage.objects — 두 번째 경로 세그먼트가 UUID 형식이 아닐 때 예외가 아니라 조용히 거부 ──
#     (2026-08-11 코드리뷰 추가: split_part(...)::uuid 캐스팅을 형식 검증 없이 하면 42501 대신
#     invalid input syntax for type uuid 예외가 던져질 수 있었다 — 그 가드가 실제로 막는지 확인.)


def test_active_seller_malformed_storage_path_rejected_cleanly_not_uuid_exception(db):
    cur = db
    seller_id = _create_user(cur, f"malformed-path-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, seller_id) == "active", "전제 실패 — 정지와 무관해야 한다"
    # 두 번째 세그먼트가 uuid가 아니다 — 0013 트리거를 안 거치는 storage.objects 직접 쓰기라
    # 이런 이름이 그대로 정책까지 들어올 수 있다.
    bad_name = f"{seller_id}/not-a-uuid/photo.jpg"

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                _insert_storage_object(cur, bad_name)
    assert exc.value.sqlstate == _RLS_VIOLATION, (
        f"형식이 어긋난 경로가 42501이 아닌 다른 예외로 죽었다: {exc.value.sqlstate!r} "
        f"({exc.value})"
    )
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (bad_name,),
    )
    assert cur.fetchone()[0] == 0


# ── ⑤c storage.objects — 두 번째 세그먼트가 대문자 UUID일 때도 거부된다(P7, 2026-08-11 3차 코드리뷰) ──
#     0013의 enforce_listing_images_storage_path 트리거는 listing_id를 대소문자 구분 텍스트로
#     비교한다(split_part(name,'/',2) <> new.listing_id::text, uuid::text는 항상 소문자로
#     렌더링된다) — 그런데 이 정책의 정규식이 `[0-9a-fA-F]`로 대문자까지 받아 주면, 대문자 UUID
#     경로는 이 RLS 정책은 통과시키면서 그 경로로는 listing_images 행을 영원히 못 만드는 상태가
#     생긴다(파일은 올라가는데 행이 안 만들어짐). 정규식을 `[0-9a-f]`로 좁혀 이 축을 막는다.


def test_active_seller_uppercase_uuid_storage_path_rejected(db):
    cur = db
    seller_id = _create_user(cur, f"uppercase-uuid-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    assert _profile_status(cur, seller_id) == "active", "전제 실패 — 정지와 무관해야 한다"
    # 두 번째 세그먼트가 유효한 UUID이지만 대문자다 — split_part(...)::uuid 캐스팅 자체는
    # 성공하므로(Postgres의 uuid 입력은 대소문자 구분 없이 받는다) 캐스팅 가드(⑤b)에는 안 걸리고,
    # 이 정규식이 직접 대문자를 거부해야 한다.
    upper_name = f"{seller_id}/{str(listing_id).upper()}/photo.jpg"

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                _insert_storage_object(cur, upper_name)
    assert exc.value.sqlstate == _RLS_VIOLATION, (
        f"대문자 UUID 경로가 42501이 아닌 다른 예외로 죽었다: {exc.value.sqlstate!r} "
        f"({exc.value})"
    )
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (upper_name,),
    )
    assert cur.fetchone()[0] == 0


# ── ⑥ listings_delete_admin — 정지된 관리자, 남의 매물 ────────────────────────────────────


def test_suspended_admin_cannot_delete_others_listing(db):
    cur = db
    victim_id = _create_user(cur, f"victim-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, victim_id)
    admin_id = _create_user(cur, f"susp-admin-del-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute("delete from public.listings where id = %s", (listing_id,))
        assert cur.rowcount == 0, "정지된 관리자가 남의 매물을 DELETE했다"

    cur.execute("select count(*) from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 1


# ── ⑦ admin_restore_sold_listing RPC — 정지된 관리자 ──────────────────────────────────────


def test_suspended_admin_cannot_restore_sold_listing(db):
    cur = db
    seller_id = _create_user(cur, f"restore-seller-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")
    admin_id = _create_user(cur, f"susp-admin-rpc-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute(
            "select * from public.admin_restore_sold_listing(p_listing_id => %s)", (listing_id,)
        )
        assert cur.fetchall() == [], "정지된 관리자가 sold 매물을 되돌렸다"

    assert _listing_status(cur, listing_id) == "sold"


# ── ⑧ 정지된 관리자의 자가 정지 해제 시도 ──────────────────────────────────────────────────


def test_suspended_admin_cannot_unsuspend_self(db):
    cur = db
    admin_id = _create_user(cur, f"susp-admin-self-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute(
            "update public.profiles set status = 'active' where id = %s", (admin_id,)
        )
        assert cur.rowcount == 0, "정지된 관리자가 스스로 정지를 해제했다"

    assert _profile_status(cur, admin_id) == "suspended"


# ── ⑨ 활성 관리자 — 회귀 없음(관리자 액션 전부 정상 성공) ─────────────────────────────────────


def test_active_admin_can_still_perform_admin_actions(db):
    cur = db
    victim_id = _create_user(cur, f"active-admin-victim-{uuid.uuid4()}@example.test")
    to_delete_id = uuid.uuid4()
    _insert_listing(cur, to_delete_id, victim_id)
    to_restore_id = uuid.uuid4()
    _insert_listing(cur, to_restore_id, victim_id, status="sold")
    admin_id = _create_user(cur, f"active-admin-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    assert _profile_status(cur, admin_id) == "active", "전제 실패 — 이 검사는 활성 관리자여야 한다"

    with _as(cur, admin_id):
        cur.execute("delete from public.listings where id = %s", (to_delete_id,))
        assert cur.rowcount == 1, "활성 관리자가 남의 매물을 못 지웠다(회귀)"

        cur.execute(
            "select * from public.admin_restore_sold_listing(p_listing_id => %s)",
            (to_restore_id,),
        )
        assert [r[0] for r in cur.fetchall()] == [to_restore_id], "활성 관리자의 복구 RPC가 실패했다(회귀)"

        cur.execute(
            "update public.profiles set status = 'suspended' where id = %s returning id",
            (victim_id,),
        )
        assert cur.fetchone() == (victim_id,), "활성 관리자가 남의 profiles를 못 바꿨다(회귀)"

    assert _listing_status(cur, to_restore_id) == "on_sale"
    assert _profile_status(cur, victim_id) == "suspended"


# ── ⑨b 정지된 관리자의 읽기 — is_admin_active()를 새로 만든 이유 자체를 실측 ─────────────────
#     (2026-08-11 코드리뷰 추가: is_admin()을 전역으로 좁히지 않고 is_admin_active()를 쓰기
#     소비처에만 넣은 설계 근거가 "관리자 읽기 정책은 정지 여부와 무관하게 계속 열려야 한다"인데,
#     그걸 실제로 확인하는 테스트가 없었다 — 여기서 그 근거를 재본다.)


def test_suspended_admin_can_still_read_via_admin_select_policies(db):
    cur = db
    other_id = _create_user(cur, f"susp-admin-read-other-{uuid.uuid4()}@example.test")
    hidden_listing_id = uuid.uuid4()
    _insert_listing(cur, hidden_listing_id, other_id, status="sold")  # on_sale이 아니라 일반 열람으론 안 보임
    admin_id = _create_user(cur, f"susp-admin-read-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        # listings_select_admin(0002) — is_admin()만 체크, is_admin_active()로 바뀌지 않았다.
        cur.execute("select id from public.listings where id = %s", (hidden_listing_id,))
        assert cur.fetchone() == (hidden_listing_id,), (
            "정지된 관리자가 listings_select_admin으로 sold 매물을 못 읽는다(is_admin() 전역 회귀)"
        )

        # profiles_select_admin(0001) — 마찬가지로 is_admin()만 체크.
        cur.execute("select id from public.profiles where id = %s", (other_id,))
        assert cur.fetchone() == (other_id,), (
            "정지된 관리자가 profiles_select_admin으로 남의 profiles를 못 읽는다(is_admin() 전역 회귀)"
        )


# ── ⑩ 정지된 회원의 읽기 — 전부 무변화 ────────────────────────────────────────────────────


def test_suspended_member_reads_are_unaffected(db):
    cur = db
    seller_id = _create_user(cur, f"susp-read-{uuid.uuid4()}@example.test")
    own_listing_id = uuid.uuid4()
    _insert_listing(cur, own_listing_id, seller_id)
    other_seller_id = _create_user(cur, f"other-onsale-{uuid.uuid4()}@example.test")
    other_listing_id = uuid.uuid4()
    _insert_listing(cur, other_listing_id, other_seller_id)
    _suspend(cur, seller_id)

    with _as(cur, seller_id):
        cur.execute("select id from public.listings where id = %s", (own_listing_id,))
        assert cur.fetchone() == (own_listing_id,), "정지된 판매자가 본인 매물을 못 읽는다"

        cur.execute("select id from public.profiles where id = %s", (seller_id,))
        assert cur.fetchone() == (seller_id,), "정지된 판매자가 본인 profiles를 못 읽는다"

        cur.execute("select id from public.listings where id = %s", (other_listing_id,))
        assert cur.fetchone() == (other_listing_id,), "정지된 회원이 남의 on_sale 매물을 못 읽는다"


# ── ⑪ [[DW-674]] 일반 소유권 회귀 — 정지와 무관, 활성·비관리자가 남의 매물을 못 건드린다 ────────


def test_non_owner_cannot_update_or_delete_others_listing(db):
    """DW-674: `listings` 소유권 RLS를 지키는 반복 검사가 이 스토리 전까지 저장소에 없었다.
    이 테스트는 **정지와 무관**하다 — 둘 다 활성 계정으로 구성해 소유권 축만 격리한다."""
    cur = db
    owner_id = _create_user(cur, f"dw674-owner-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, owner_id)
    intruder_id = _create_user(cur, f"dw674-intruder-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패 — 활성 계정이어야 한다"

    with _as(cur, intruder_id):
        cur.execute("update public.listings set price = 1 where id = %s", (listing_id,))
        assert cur.rowcount == 0, "활성 비소유자가 남의 매물을 UPDATE했다"

        cur.execute("delete from public.listings where id = %s", (listing_id,))
        assert cur.rowcount == 0, "활성 비소유자가 남의 매물을 DELETE했다"

    cur.execute("select price from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 26700000
    cur.execute("select count(*) from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 1


# ── ⑫⑬ chat_messages_insert_participant — 정지 발신 차단 + 정상 발신 회귀 없음 ────────────────


def test_suspended_participant_cannot_send_chat_message(db):
    cur = db
    buyer_id = _create_user(cur, f"chat-susp-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chat-susp-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    _suspend(cur, buyer_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, buyer_id):
                cur.execute(
                    "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s)",
                    (room_id, buyer_id, "정지된 발신 시도"),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select count(*) from public.chat_messages where room_id = %s", (room_id,))
    assert cur.fetchone()[0] == 0


def test_active_participant_chat_still_broadcasts_and_updates_unread(db):
    """스펙 Design Notes가 요구한 확인: 정지 발신 차단(⑫)이 정상 참가자의 발신·방송(0023)·
    안읽음 계산(0024~0026)을 깨지 않는다. 둘 다 "INSERT가 이미 성공한 뒤"에만 동작하므로
    이론상 안전하다고 판단했던 것을 여기서 실제로 재현해 확인한다."""
    cur = db
    buyer_id = _create_user(cur, f"chat-ok-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chat-ok-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)

    with _as(cur, buyer_id):
        cur.execute(
            "insert into public.chat_messages (room_id, sender_id, body) values (%s, %s, %s) "
            "returning id",
            (room_id, buyer_id, "정상 메시지"),
        )
        assert cur.fetchone() is not None, "활성 참가자의 정상 발신이 막혔다(회귀)"

    cur.execute(
        "select count(*) from realtime.messages where topic = %s", (f"chat:room:{room_id}",)
    )
    assert cur.fetchone()[0] == 1, "정상 발신이 방송되지 않았다(0023 회귀)"

    with _as(cur, seller_id):
        cur.execute("select public.chat_unread_count()")
        assert cur.fetchone()[0] == 1, "정상 발신이 상대방 안읽음 카운트에 반영되지 않았다(0024~0026 회귀)"


# ── ⑭ 0033: 레거시 role='seller' 메타데이터도 여전히 'user'로 배정된다 (DW-682 재확인) ──────


def test_legacy_seller_metadata_still_yields_user_role(db):
    cur = db
    email = f"legacy-seller-signup-{uuid.uuid4()}@example.test"
    user_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, jsonb_build_object('role', 'seller'))",
        (user_id, email),
    )
    cur.execute("select role from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    assert row[0] == "user", (
        f"레거시 role='seller' 메타데이터가 여전히 반영됐다 — 0033이 지운 통과 분기가 "
        f"되살아났다: {row[0]!r}"
    )


# ══════════════════════════════════════════════════════════════════════════════════════════
# 2026-08-11 bad_spec 루프백 #1 — 긍정 대조군 · §10.1 순서 회귀 · 관리자 4정책 양방향 ·
# DW-674 INSERT 위조 · storage 소유권 축 · 레거시 경로 DELETE (⑮~⑳, 위 헤더 참조)
# ══════════════════════════════════════════════════════════════════════════════════════════


# ── ⑮ 긍정 대조군 — 활성 판매자의 listing_images·storage.objects 쓰기는 성공한다 ─────────────


def test_active_seller_can_write_listing_image(db):
    """긍정 대조군. 이게 없으면 ③(listing_images 거부 단언 3건)이 '정지만 막힘'이 아니라
    '전부 막힘'으로 잘못 짜여도 구별할 수 없다(2026-08-11 bad_spec 루프백 지적)."""
    cur = db
    seller_id = _create_user(cur, f"active-img-ctrl-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    assert _profile_status(cur, seller_id) == "active", "전제 실패 — 활성 계정이어야 한다"
    path = _photo_path(seller_id, listing_id, "control.jpg")

    with _as(cur, seller_id):
        cur.execute(
            "insert into public.listing_images (listing_id, storage_path) values (%s, %s) "
            "returning id",
            (listing_id, path),
        )
        image_id = cur.fetchone()[0]
        assert image_id is not None, "활성 판매자가 본인 매물 사진을 INSERT 못 했다(회귀)"

        cur.execute("update public.listing_images set sort_order = 3 where id = %s", (image_id,))
        assert cur.rowcount == 1, "활성 판매자가 본인 매물 사진을 UPDATE 못 했다(회귀)"

        cur.execute("delete from public.listing_images where id = %s", (image_id,))
        assert cur.rowcount == 1, "활성 판매자가 본인 매물 사진을 DELETE 못 했다(회귀)"


def test_active_seller_can_write_storage_object(db):
    """긍정 대조군. ④(storage.objects 거부 단언 3건)의 짝 — 없으면 '전부 막힘'과 구별 불가."""
    cur = db
    seller_id = _create_user(cur, f"active-obj-ctrl-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    assert _profile_status(cur, seller_id) == "active", "전제 실패"
    name = _photo_path(seller_id, listing_id, "control.jpg")

    with _as(cur, seller_id):
        object_id = _insert_storage_object(cur, name)
        assert object_id is not None, "활성 판매자가 본인 사진 파일을 INSERT 못 했다(회귀)"

        cur.execute(
            "update storage.objects set metadata = '{\"x\":1}'::jsonb "
            "where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 1, "활성 판매자가 본인 사진 파일을 UPDATE 못 했다(회귀)"

        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 1, "활성 판매자가 본인 사진 파일을 DELETE 못 했다(회귀)"


# ── ⑯ §10.1 순서 회귀 고정 — 매물 DELETE 먼저 → 사진 DELETE, 고아 0건 ──────────────────────


@pytest.mark.parametrize("listing_status", ["on_sale", "sold"])
def test_active_seller_delete_listing_then_photo_leaves_no_orphan(db, listing_status):
    """2026-08-11 bad_spec 루프백의 최상위(high) 결함을 고정하는 테스트. storage owner DELETE
    정책이 '살아 있는 non-sold 매물이 있어야 지울 수 있다'(긍정형)로 되돌아가면, 실제 클라이언트
    순서(§10.1: ① listing_images에서 경로를 먼저 읽음 → ② listings 행 DELETE → ③ 그 매물의
    storage.objects 사진을 ①에서 미리 읽어 둔 경로로 DELETE)에서 ③이 0행이 되고 고아 파일이
    영구 잔존한다(`web/.../upload.ts`의 `deleteListingImageObject`는 RLS 0행을 '이미 없음'으로
    읽어 성공으로 보고 — 화면·로그 어디에도 실패가 안 뜬다). 이 테스트가 바로 그 순서를 실제로
    밟는다 — `web/src/app/(user)/sell/photo-sync.ts`의 `listListingPhotoPaths`(listing_images
    SELECT) → `ListingActions.tsx`의 `handleDelete`(listings DELETE) →
    `deletePhotoObjectsByPaths`(storage.objects DELETE, 미리 읽어 둔 경로 사용) 순서를 그대로
    미러링한다(2026-08-11 3차 코드리뷰 patch — 이전 판은 listing_images 행을 아예 만들지 않고
    storage.objects만 지워, 실제 클라이언트가 밟는 cascade·경로 사전조회 축을 검증하지 못했다).

    `listing_status='sold'` 분기가 더 흥미로운 축이다(2026-08-11 3차 코드리뷰 patch) — 매물이
    아직 살아 있는 동안엔 DW-782의 sold 차단이 사진 DELETE를 막고, 매물 행이 사라지는 순간
    (§10.1 순서상 정상 경로) 그 차단이 풀려 소유자가 정리할 수 있어야 한다. 두 상태 전환을 같은
    테스트에서 실측한다."""
    cur = db
    seller_id = _create_user(cur, f"order-regress-{listing_status}-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status=listing_status)
    path = _photo_path(seller_id, listing_id, "order.jpg")
    _insert_listing_image(cur, listing_id, path)
    _insert_storage_object(cur, path)
    assert _profile_status(cur, seller_id) == "active", "전제 실패"

    with _as(cur, seller_id):
        if listing_status == "sold":
            # sold 매물이 아직 살아 있는 동안엔 사진 DELETE가 차단돼야 한다(DW-782) — 순서를
            # 밟기 전에 이 축이 실제로 막혀 있는지 먼저 확인한다.
            cur.execute(
                "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
                (path,),
            )
            assert cur.rowcount == 0, "sold 매물이 살아 있는데도 사진 DELETE가 통과했다"

        # ① 실제 클라이언트 순서: listing_images에서 경로를 먼저 읽는다(listListingPhotoPaths).
        cur.execute(
            "select storage_path from public.listing_images where listing_id = %s",
            (listing_id,),
        )
        fetched_paths = [row[0] for row in cur.fetchall()]
        assert fetched_paths == [path], "listing_images에서 경로를 못 읽었다(전제 조건)"

        # ② listings 행 DELETE — listing_images는 on delete cascade로 함께 사라진다.
        cur.execute("delete from public.listings where id = %s", (listing_id,))
        assert cur.rowcount == 1, "② listings DELETE가 실패했다(전제 조건)"

        # ③ 미리 읽어 둔 경로로 storage.objects를 지운다(deletePhotoObjectsByPaths).
        for fetched_path in fetched_paths:
            cur.execute(
                "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
                (fetched_path,),
            )
            assert cur.rowcount == 1, (
                "③ 매물이 이미 삭제된 뒤 사진 DELETE가 0행이 됐다 — storage owner DELETE 정책이 "
                "'살아 있는 non-sold 매물' 긍정형으로 되돌아갔다는 신호(§10.1 순서 회귀, "
                "2026-08-11 bad_spec 루프백이 고정한 축)"
            )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (path,),
    )
    assert cur.fetchone()[0] == 0, "고아 파일이 남았다"


# ── ⑰ 관리자 쓰기 정책 6개 중 나머지 4개 양방향 — profiles/chat_rooms/chat_messages DELETE ──
#     + storage.objects 관리자 DELETE (⑥⑨는 listings_delete_admin·admin_restore_sold_listing·
#     profiles_update_admin 3개만 덮었다 — 나머지 4개는 이전 판에서 미검증이었다)


def test_suspended_admin_cannot_delete_profile(db):
    cur = db
    victim_id = _create_user(cur, f"del-profile-victim-{uuid.uuid4()}@example.test")
    admin_id = _create_user(cur, f"susp-admin-delprof-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute("delete from public.profiles where id = %s", (victim_id,))
        assert cur.rowcount == 0, "정지된 관리자가 남의 profiles를 DELETE했다"

    cur.execute("select count(*) from public.profiles where id = %s", (victim_id,))
    assert cur.fetchone()[0] == 1


def test_active_admin_can_delete_profile(db):
    cur = db
    victim_id = _create_user(cur, f"del-profile-victim2-{uuid.uuid4()}@example.test")
    admin_id = _create_user(cur, f"active-admin-delprof-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    assert _profile_status(cur, admin_id) == "active", "전제 실패"

    with _as(cur, admin_id):
        cur.execute("delete from public.profiles where id = %s", (victim_id,))
        assert cur.rowcount == 1, "활성 관리자가 남의 profiles를 DELETE 못 했다(회귀)"


def test_suspended_admin_cannot_delete_chat_room(db):
    cur = db
    buyer_id = _create_user(cur, f"chatroom-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chatroom-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    admin_id = _create_user(cur, f"susp-admin-delroom-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute("delete from public.chat_rooms where id = %s", (room_id,))
        assert cur.rowcount == 0, "정지된 관리자가 chat_rooms를 DELETE했다"

    cur.execute("select count(*) from public.chat_rooms where id = %s", (room_id,))
    assert cur.fetchone()[0] == 1


def test_active_admin_can_delete_chat_room(db):
    cur = db
    buyer_id = _create_user(cur, f"chatroom-buyer2-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chatroom-seller2-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    admin_id = _create_user(cur, f"active-admin-delroom-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    assert _profile_status(cur, admin_id) == "active", "전제 실패"

    with _as(cur, admin_id):
        cur.execute("delete from public.chat_rooms where id = %s", (room_id,))
        assert cur.rowcount == 1, "활성 관리자가 chat_rooms를 DELETE 못 했다(회귀)"


def test_suspended_admin_cannot_delete_chat_message(db):
    cur = db
    buyer_id = _create_user(cur, f"chatmsg-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chatmsg-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    message_id = _insert_chat_message(cur, room_id, buyer_id)
    admin_id = _create_user(cur, f"susp-admin-delmsg-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute("delete from public.chat_messages where id = %s", (message_id,))
        assert cur.rowcount == 0, "정지된 관리자가 chat_messages를 DELETE했다"

    cur.execute("select count(*) from public.chat_messages where id = %s", (message_id,))
    assert cur.fetchone()[0] == 1


def test_active_admin_can_delete_chat_message(db):
    cur = db
    buyer_id = _create_user(cur, f"chatmsg-buyer2-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chatmsg-seller2-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    message_id = _insert_chat_message(cur, room_id, buyer_id)
    admin_id = _create_user(cur, f"active-admin-delmsg-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    assert _profile_status(cur, admin_id) == "active", "전제 실패"

    with _as(cur, admin_id):
        cur.execute("delete from public.chat_messages where id = %s", (message_id,))
        assert cur.rowcount == 1, "활성 관리자가 chat_messages를 DELETE 못 했다(회귀)"


def test_suspended_admin_cannot_delete_storage_object_via_admin_policy(db):
    cur = db
    seller_id = _create_user(cur, f"adminobj-seller-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    name = _photo_path(seller_id, listing_id, "adminobj.jpg")
    _insert_storage_object(cur, name)
    admin_id = _create_user(cur, f"susp-admin-delobj-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    _suspend(cur, admin_id)

    with _as(cur, admin_id):
        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 0, "정지된 관리자가 관리자 경로로 storage.objects를 DELETE했다"

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (name,),
    )
    assert cur.fetchone()[0] == 1


def test_active_admin_can_delete_storage_object_via_admin_policy(db):
    cur = db
    seller_id = _create_user(cur, f"adminobj-seller2-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    name = _photo_path(seller_id, listing_id, "adminobj2.jpg")
    _insert_storage_object(cur, name)
    admin_id = _create_user(cur, f"active-admin-delobj-{uuid.uuid4()}@example.test")
    _make_admin(cur, admin_id)
    assert _profile_status(cur, admin_id) == "active", "전제 실패"

    with _as(cur, admin_id):
        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 1, (
            "활성 관리자가 관리자 경로로 storage.objects를 DELETE 못 했다(회귀)"
        )


# ── ⑱ [[DW-674]] 타인 명의 listings INSERT — 활성·비관리자의 소유권 위조 시도 ────────────────


def test_intruder_cannot_insert_listing_for_other_seller(db):
    """DW-674의 trigger가 명시한 축("타인 명의 INSERT가 42501") — 이전 판은 UPDATE/DELETE만
    덮고 이 단언 없이 DW-674를 닫았다(2026-08-11 bad_spec 루프백이 저장소 전역 grep으로 부재
    확인)."""
    cur = db
    victim_id = _create_user(cur, f"forge-victim-{uuid.uuid4()}@example.test")
    intruder_id = _create_user(cur, f"forge-intruder-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패"
    new_id = uuid.uuid4()

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, intruder_id):
                cur.execute(
                    f"insert into public.listings ({_LISTING_COLS}) values "
                    "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
                    "'흰색', '가솔린', '자동', 1998, 5, '서울')",
                    (new_id, victim_id),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select count(*) from public.listings where id = %s", (new_id,))
    assert cur.fetchone()[0] == 0, "타인 명의 INSERT가 실제로 행을 남겼다"


# ── ⑲ storage 소유자 join의 소유권 축 — 남의 on_sale 매물 id를 자기 uid 아래 붙이는 시도 ──────


def test_intruder_cannot_insert_storage_object_for_other_sellers_listing(db):
    """storage 소유자 join에 `l.seller_id = auth.uid()`가 없으면, 경로 1번째 세그먼트(자기
    uid)만 맞고 2번째 세그먼트(listing_id)는 남의 on_sale 매물이어도 통과해 버린다(2026-08-11
    bad_spec 루프백이 지적 — 0031의 listing_images 정책은 이미 이 축을 본다)."""
    cur = db
    victim_id = _create_user(cur, f"pathforge-victim-{uuid.uuid4()}@example.test")
    victim_listing_id = uuid.uuid4()
    _insert_listing(cur, victim_listing_id, victim_id)  # on_sale, victim 소유
    intruder_id = _create_user(cur, f"pathforge-intruder-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패"
    # 1번째 세그먼트는 침입자 본인 uid(경로 소유권 검사는 통과) — 2번째만 남의 매물 id.
    name = _photo_path(intruder_id, victim_listing_id, "forged.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, intruder_id):
                _insert_storage_object(cur, name)
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (name,),
    )
    assert cur.fetchone()[0] == 0


# ── ⑳ 레거시(비-UUID) 경로 오브젝트도 소유자는 DELETE로 정리할 수 있다 ─────────────────────


def test_active_seller_can_delete_legacy_non_uuid_storage_object(db):
    """부정형 DELETE(`not exists(... status='sold')`)의 의도된 부작용 — 2번째 경로 세그먼트가
    UUID 형식이 아니면 CASE 가드가 NULL을 돌리고 `l.id = NULL`인 EXISTS는 항상 거짓이라
    NOT EXISTS가 참이 된다(=sold 매물이 아니라고 판정 → 삭제 허용). INSERT는 여전히 형식
    위반으로 거부되는 것과 대비된다(⑤b가 그 축을 이미 덮는다)."""
    cur = db
    seller_id = _create_user(cur, f"legacy-del-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, seller_id) == "active", "전제 실패"
    bad_name = f"{seller_id}/not-a-uuid/legacy.jpg"
    _insert_storage_object(cur, bad_name)

    with _as(cur, seller_id):
        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (bad_name,),
        )
        assert cur.rowcount == 1, "소유자가 레거시(비-UUID) 경로 오브젝트를 못 지웠다"

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (bad_name,),
    )
    assert cur.fetchone()[0] == 0


# ══════════════════════════════════════════════════════════════════════════════════════════
# 2026-08-11 2차 코드리뷰(4개 렌즈) patch — P2~P6 (설계 변경 없음, 검사 추가만)
# ══════════════════════════════════════════════════════════════════════════════════════════


# ── P2 — listings 본체 긍정 대조군(활성 판매자 INSERT/UPDATE 성공) ──────────────────────────


def test_active_seller_can_insert_and_update_own_listing(db):
    """긍정 대조군 — listings 본체. listing_images·storage.objects에는 이미 긍정 대조군이
    있는데 정작 listings 자체에는 없었다(2026-08-11 2차 코드리뷰 P2) — listings_insert_own/
    listings_update_own을 `with check (false)` 같은 형태로 잘못 써도 이 대조군 없이는
    35건 전부 green이었다."""
    cur = db
    seller_id = _create_user(cur, f"active-listing-ctrl-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, seller_id) == "active", "전제 실패"
    new_id = uuid.uuid4()

    with _as(cur, seller_id):
        cur.execute(
            f"insert into public.listings ({_LISTING_COLS}) values "
            "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
            "'흰색', '가솔린', '자동', 1998, 5, '서울')",
            (new_id, seller_id),
        )

        cur.execute("update public.listings set price = 25000000 where id = %s", (new_id,))
        assert cur.rowcount == 1, "활성 판매자가 본인 매물을 UPDATE 못 했다(회귀)"

    cur.execute("select price from public.listings where id = %s", (new_id,))
    row = cur.fetchone()
    assert row is not None, "활성 판매자의 INSERT가 실제로 행을 안 남겼다(회귀)"
    assert row[0] == 25000000


# ── P3 — 0015 sold-전환 비대칭 고정 ─────────────────────────────────────────────────────────


def test_active_seller_can_mark_sold_but_cannot_further_update_sold_listing(db):
    """0015의 sold-전환 비대칭 고정(2026-08-11 2차 코드리뷰 P3). `0032`는
    `listings_update_own`의 `using`에만 정지 조건을 추가하고 `with check`는 그대로 뒀다 —
    그 설계 근거(FR7 판매완료 전환은 여전히 허용)가 실제로 살아 있는지, `authenticated` 세션
    으로 직접 sold 전환 후 재수정을 시도해 확인한다. 저장소 전체에 이 축을 실제 세션으로
    돌리는 테스트가 이전까지 없었다."""
    cur = db
    seller_id = _create_user(cur, f"sold-transition-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)  # on_sale
    assert _profile_status(cur, seller_id) == "active", "전제 실패"

    with _as(cur, seller_id):
        cur.execute("update public.listings set status = 'sold' where id = %s", (listing_id,))
        assert cur.rowcount == 1, "활성 판매자가 자기 매물을 sold로 전환 못 했다(FR7 회귀)"

        cur.execute("update public.listings set price = 1 where id = %s", (listing_id,))
        assert cur.rowcount == 0, (
            "sold로 전환된 매물을 같은 세션에서 다시 UPDATE할 수 있었다 — 0015의 using 차단 회귀"
        )

    cur.execute("select status, price from public.listings where id = %s", (listing_id,))
    row = cur.fetchone()
    assert row[0] == "sold"
    assert row[1] == 26700000, "sold 전환 후 UPDATE가 실제로 값을 바꿨다"


# ── P4 — chat_messages_insert_participant 방-당사자 조건 고정 ───────────────────────────────


def test_third_party_non_participant_cannot_insert_chat_message(db):
    """`chat_messages_insert_participant`의 방-당사자 조건 고정(2026-08-11 2차 코드리뷰 P4) —
    `0032`가 0003의 `exists(select 1 from chat_rooms r where r.id=... and (auth.uid()=
    r.buyer_id or auth.uid()=r.seller_id))`를 손으로 재작성했다. 그 조건이 통째로 빠져도
    기존 테스트는 전부 green이었다(정지 테스트는 profiles-active 축으로, 정상 테스트는 진짜
    참가자로 통과하기 때문). 방의 buyer도 seller도 아닌 제3의 활성 사용자로 그 축을 직접
    깬다."""
    cur = db
    buyer_id = _create_user(cur, f"chat-3rd-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chat-3rd-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    outsider_id = _create_user(cur, f"chat-3rd-outsider-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, outsider_id) == "active", "전제 실패 — 활성 계정이어야 한다"

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, outsider_id):
                cur.execute(
                    "insert into public.chat_messages (room_id, sender_id, body) "
                    "values (%s, %s, %s)",
                    (room_id, outsider_id, "당사자 아닌데 보내는 메시지"),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select count(*) from public.chat_messages where room_id = %s", (room_id,))
    assert cur.fetchone()[0] == 0, "당사자가 아닌 제3자의 INSERT가 실제로 행을 남겼다"


# ── P5 — listing_images의 sold·소유권 축(0031, DW-390) 고정 ────────────────────────────────


def test_active_seller_cannot_write_listing_image_for_sold_listing(db):
    """`listing_images`의 sold 축(0031, DW-390) 고정(2026-08-11 2차 코드리뷰 P5). 같은 축을
    `storage.objects`에는 이미 `test_active_seller_cannot_write_storage_object_for_sold_listing`이
    지키는데, `listing_images` 행 자체에는 없었다 — `l.status <> 'sold'`를 떨어뜨려도 기존
    35건이 green이었다. **정지와 무관** — 활성 판매자로만 구성해 sold 축을 격리한다."""
    cur = db
    seller_id = _create_user(cur, f"img-sold-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")
    assert _profile_status(cur, seller_id) == "active", "전제 실패 — 이 검사는 정지와 무관하다"
    existing_path = _photo_path(seller_id, listing_id, "existing.jpg")
    existing_image_id = _insert_listing_image(cur, listing_id, existing_path)
    new_path = _photo_path(seller_id, listing_id, "new.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                cur.execute(
                    "insert into public.listing_images (listing_id, storage_path) "
                    "values (%s, %s)",
                    (listing_id, new_path),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    with _as(cur, seller_id):
        cur.execute(
            "update public.listing_images set sort_order = 9 where id = %s",
            (existing_image_id,),
        )
        assert cur.rowcount == 0, "활성 판매자가 sold 매물의 listing_images 행을 UPDATE했다"

        cur.execute("delete from public.listing_images where id = %s", (existing_image_id,))
        assert cur.rowcount == 0, "활성 판매자가 sold 매물의 listing_images 행을 DELETE했다"


def test_active_non_owner_cannot_insert_listing_image_for_others_listing(db):
    """`listing_images`의 소유권 축(0031) 고정 — 활성 비소유자가 남의 (on_sale) 매물에 사진
    행을 못 붙인다(2026-08-11 2차 코드리뷰 P5의 소유권 축 부분).

    경로는 **실제 소유자(owner_id)** 접두사를 쓴다 — 0013의 `enforce_listing_images_storage_path`
    트리거가 `storage_path`의 첫 세그먼트를 매물의 실제 `seller_id`와 대조하므로, 침입자의 uid를
    접두사로 쓰면 RLS가 아니라 그 트리거(§10 계약 위반, 별개의 RaiseException)가 먼저 막아
    이 테스트가 보려는 RLS 소유권 축(`l.seller_id = auth.uid()`)을 격리하지 못한다."""
    cur = db
    owner_id = _create_user(cur, f"img-owner-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, owner_id)
    intruder_id = _create_user(cur, f"img-intruder-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패"
    path = _photo_path(owner_id, listing_id, "intrusion.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, intruder_id):
                cur.execute(
                    "insert into public.listing_images (listing_id, storage_path) "
                    "values (%s, %s)",
                    (listing_id, path),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from public.listing_images where listing_id = %s and storage_path = %s",
        (listing_id, path),
    )
    assert cur.fetchone()[0] == 0


# ── P6 — storage owner UPDATE의 with check가 name을 실제로 보는지 고정 ──────────────────────


def test_active_owner_cannot_relink_storage_object_to_others_listing(db):
    """`listing_images_objects_owner_update`의 `with check` 축 고정(2026-08-11 2차 코드리뷰 P6,
    실측으로 재도출된 형태). 기존 UPDATE 테스트 3건은 전부 `metadata`만 바꿔 `name`이 그대로였다
    (`using`을 통과하면 값이 안 바뀐 `with check`도 자동 통과) — 이 테스트는 `name`을 실제로
    바꿔서 그 축을 깬다.

    ⚠️ **경로 첫 세그먼트(uid)는 그대로 두고 두 번째 세그먼트(listing_id)만 남의 것으로 바꾼다
    — 이유(2026-08-11 로컬 실 스택 실측으로 확정)**: `listing_images_objects_owner_select`가
    UPDATE의 **NEW 행에도** 적용되는데, 그 정책은 **첫 세그먼트만** 본다
    (`split_part(name,1)=auth.uid()`). 그래서 첫 세그먼트까지 남의 uid로 바꾸면 `with check`를
    완전히 열어도(`with check(true)`) SELECT 정책이 독자적으로 막아 버려 — rename 자체가
    `UPDATE 0`으로 걸린다 — `with check`가 실제로 무엇을 보는지 이 테스트가 증명하지 못한다
    (처음 이 형태로 짰다가 로컬 실측에서 발견 — 그 상태로는 `with check`를 `bucket_id` 하나로
    약화시켜도 이 테스트가 계속 green이었다, "표기를 바꿔 다시 깨본다"의 실사례). 반대로 **자기
    uid는 유지하고 listing_id만 남의 것**으로 바꾸면 SELECT 정책은 그대로 통과하고,
    `with check`의 `exists(... l.seller_id = auth.uid())` 절만 그 rename을 막는다 — 그래서
    이 형태라야 `with check` 단독 축을 격리해서 고정한다.

    ⚠️ 이 거부는 **rowcount 0이 아니라 예외다** — `using`은 UPDATE 대상 행(OLD, 자기 오브젝트)을
    통과시키므로 실제로 실행되고, `with check`가 걸러내는 것은 갱신 **결과(NEW) 행**이라
    Postgres가 "new row violates row-level security policy" 예외를 던진다(INSERT의 `with check`
    거부와 같은 신호 계열 — 대상 행이 안 보여 조용히 0행이 되는 `using` 단독 거부와 다르다).
    """
    cur = db
    seller_id = _create_user(cur, f"relink-owner-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    victim_id = _create_user(cur, f"relink-victim-{uuid.uuid4()}@example.test")
    victim_listing_id = uuid.uuid4()
    _insert_listing(cur, victim_listing_id, victim_id)
    own_name = _photo_path(seller_id, listing_id, "mine.jpg")
    _insert_storage_object(cur, own_name)
    # 첫 세그먼트(uid)는 seller_id 그대로 — SELECT 정책은 통과시킨다. 두 번째 세그먼트만
    # victim의 listing_id로 바꿔 with check의 소유권 절만 격리해서 시험한다.
    target_name = _photo_path(seller_id, victim_listing_id, "relinked.jpg")

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, seller_id):
                cur.execute(
                    "update storage.objects set name = %s "
                    "where bucket_id = 'listing-images' and name = %s",
                    (target_name, own_name),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION, (
        "활성 판매자가 자기 오브젝트를 남의 listing_id로 relink했다(예외 없이 통과) — "
        "with check가 listing 소유권을 안 본다"
    )
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (own_name,),
    )
    assert cur.fetchone()[0] == 1, "원본 오브젝트가 사라졌다(rename이 부분 성공했을 수 있다)"
    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (target_name,),
    )
    assert cur.fetchone()[0] == 0, "남의 경로에 오브젝트가 생겼다"


# ══════════════════════════════════════════════════════════════════════════════════════════
# 2026-08-11 3차 코드리뷰(4개 렌즈) patch — P1~P3·P6 (설계 변경 없음, 검사 추가만)
# ══════════════════════════════════════════════════════════════════════════════════════════


# ── P1 — 관리자 쓰기 정책 5개의 활성-비관리자 거부 축 ──────────────────────────────────────
#     ⑰ 블록은 각 정책을 "정지된 관리자(0행) vs 활성 관리자(1행)" 축으로만 검사한다.
#     `listings_delete_admin`만 ⑪(`test_non_owner_cannot_update_or_delete_others_listing`,
#     DW-674)이 활성 비관리자로도 우연히 덮는다. 나머지 5개(`profiles_delete_admin`·
#     `chat_rooms_delete_admin`·`chat_messages_delete_admin`·
#     `listing_images_objects_admin_delete`·`admin_restore_sold_listing`)는 그 정책이 통째로
#     `using (true)`(또는 RPC의 WHERE에서 `is_admin_active()`가 빠짐)가 돼도 "정지-관리자 축"만
#     으로는 안 잡힌다 — 비관리자가 그 상태에서도 여전히 거부되는 이유가 "관리자가 아니라서"인지
#     "정지라서"인지 구별이 안 되기 때문이다. 각 정책에 활성·비관리자 시도를 추가해 그 사각을
#     막는다.
#
#     ⚠️ **"남의 행"으로는 이 축을 격리할 수 없다(실측으로 발견, red 증명 중 뒤집힌 설계).**
#     처음엔 각각 "활성 비관리자가 **남의** 행을 DELETE"로 짰다. 그런데 Postgres RLS는 UPDATE·
#     DELETE 대상 행도 그 명령의 USING절뿐 아니라 **SELECT 정책으로도 걸러진다** — `profiles`·
#     `chat_rooms`·`chat_messages`·`storage.objects` 전부 "당사자 아니면 admin만 SELECT 가능"
#     이라, 비관리자·비당사자 침입자는애초에 그 행을 **볼 수조차 없다.** 그래서 `*_delete_admin`을
#     `using(true)`로 완전히 열어도 침입자 축에서는 여전히 `DELETE 0`이 나와 — red를 확인하려
#     실제로 정책을 약화시켜 재실행해 보고서야 드러났다(`profiles_delete_admin`을 `true`로 바꿔도
#     "남의 행" 형태는 green으로 남았다, 메모리 `guard-proof-must-vary-shape`의 실사례 재현).
#     그래서 아래 4건은 **본인에게는 SELECT 정책이 항상 열려 있는 행**(본인 profiles·본인이
#     당사자인 chat_rooms/chat_messages·본인 소유 경로의 storage.objects)을 대상으로,
#     admin 정책 말고는 그 DELETE를 허용할 다른 정책이 없는 조합을 골라 admin 정책만 격리한다
#     (storage.objects는 owner-delete가 sold 매물엔 안 먹히므로 sold 매물의 본인 사진을 쓴다).


def test_active_non_admin_cannot_delete_own_profile_via_admin_policy(db):
    """profiles에는 본인-DELETE 정책이 없다 — 유일한 DELETE 정책이 profiles_delete_admin이다.
    본인 행은 profiles_select_self로 항상 SELECT 가능하므로(위 헤더 참조), 이 행에 대한 DELETE
    결과는 오직 profiles_delete_admin의 is_admin_active() 판정만 반영한다."""
    cur = db
    intruder_id = _create_user(cur, f"p1-nonadmin-delprofile-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패"

    with _as(cur, intruder_id):
        cur.execute("delete from public.profiles where id = %s", (intruder_id,))
        assert cur.rowcount == 0, "활성 비관리자가 (본인 포함) profiles를 admin 정책으로 DELETE했다"

    cur.execute("select count(*) from public.profiles where id = %s", (intruder_id,))
    assert cur.fetchone()[0] == 1


def test_active_non_admin_cannot_delete_own_chat_room_via_admin_policy(db):
    """chat_rooms에도 당사자-DELETE 정책이 없다 — 유일한 DELETE 정책이 chat_rooms_delete_admin
    이다. buyer는 chat_rooms_select_participant로 자기 방을 항상 SELECT할 수 있다."""
    cur = db
    buyer_id = _create_user(cur, f"p1-nonadmin-delroom-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(
        cur, f"p1-nonadmin-delroom-seller-{uuid.uuid4()}@example.test", role="seller"
    )
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    assert _profile_status(cur, buyer_id) == "active", "전제 실패"

    with _as(cur, buyer_id):
        cur.execute("delete from public.chat_rooms where id = %s", (room_id,))
        assert cur.rowcount == 0, "활성 비관리자(당사자)가 chat_rooms를 admin 정책으로 DELETE했다"

    cur.execute("select count(*) from public.chat_rooms where id = %s", (room_id,))
    assert cur.fetchone()[0] == 1


def test_active_non_admin_cannot_delete_own_chat_message_via_admin_policy(db):
    """chat_messages에도 발신자-DELETE 정책이 없다 — 유일한 DELETE 정책이
    chat_messages_delete_admin이다. 발신자는 chat_messages_select_participant로 자기 메시지를
    항상 SELECT할 수 있다."""
    cur = db
    buyer_id = _create_user(cur, f"p1-nonadmin-delmsg-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(
        cur, f"p1-nonadmin-delmsg-seller-{uuid.uuid4()}@example.test", role="seller"
    )
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)
    message_id = _insert_chat_message(cur, room_id, buyer_id)
    assert _profile_status(cur, buyer_id) == "active", "전제 실패"

    with _as(cur, buyer_id):
        cur.execute("delete from public.chat_messages where id = %s", (message_id,))
        assert cur.rowcount == 0, (
            "활성 비관리자(발신자)가 chat_messages를 admin 정책으로 DELETE했다"
        )

    cur.execute("select count(*) from public.chat_messages where id = %s", (message_id,))
    assert cur.fetchone()[0] == 1


def test_active_non_admin_cannot_delete_own_sold_storage_object_via_admin_policy(db):
    """storage.objects는 owner-delete 정책도 있어(listing_images_objects_owner_delete) 본인
    경로면 그 정책만으로도 (sold가 아니면) 지울 수 있다 — admin 정책을 격리하려면 owner-delete가
    이미 막는 축(sold 매물)을 골라야 한다. 소유자는 listing_images_objects_owner_select로
    sold 여부와 무관하게 자기 경로를 항상 SELECT할 수 있다(위 정책 실측 — owner_select는 sold를
    안 본다)."""
    cur = db
    seller_id = _create_user(cur, f"p1-nonadmin-delobj-seller-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")
    name = _photo_path(seller_id, listing_id, "p1-nonadmin.jpg")
    _insert_storage_object(cur, name)
    assert _profile_status(cur, seller_id) == "active", "전제 실패"

    with _as(cur, seller_id):
        cur.execute(
            "delete from storage.objects where bucket_id = 'listing-images' and name = %s",
            (name,),
        )
        assert cur.rowcount == 0, (
            "활성 비관리자(소유자)가 sold 매물 사진을 admin 정책으로 DELETE했다"
        )

    cur.execute(
        "select count(*) from storage.objects where bucket_id = 'listing-images' and name = %s",
        (name,),
    )
    assert cur.fetchone()[0] == 1


def test_active_non_admin_cannot_restore_sold_listing(db):
    cur = db
    seller_id = _create_user(cur, f"p1-nonadmin-restore-seller-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id, status="sold")
    intruder_id = _create_user(cur, f"p1-nonadmin-restore-{uuid.uuid4()}@example.test")
    assert _profile_status(cur, intruder_id) == "active", "전제 실패"

    with _as(cur, intruder_id):
        cur.execute(
            "select * from public.admin_restore_sold_listing(p_listing_id => %s)", (listing_id,)
        )
        assert cur.fetchall() == [], "활성 비관리자가 sold 매물을 되돌렸다"

    assert _listing_status(cur, listing_id) == "sold"


# ── P2 — chat_messages_insert_participant의 sender_id 위조 차단(auth.uid() = sender_id) ──────
#     0032가 0003의 `chat_messages_insert_participant`를 drop→create로 다시 타이핑하며 그 conjunct
#     도 그대로 옮겼는데, 저장소의 다른 chat INSERT는 전부 postgres 소유자로 RLS를 우회하거나
#     자기 자신을 sender_id로 보내 이 conjunct가 실제로 살아 있는지 검증된 적이 없었다. 빠지면
#     참가자가 상대방 이름으로 메시지를 위조할 수 있고, 0023 브로드캐스트가 그 위조 행을 그대로
#     실어 나르며 0024~0026 안읽음 계산(`sender_id <> auth.uid()`)이 피해자의 배지를 잘못 움직인다.


def test_participant_cannot_impersonate_counterparty_as_sender(db):
    cur = db
    buyer_id = _create_user(cur, f"chat-forge-buyer-{uuid.uuid4()}@example.test")
    seller_id = _create_user(cur, f"chat-forge-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    room_id = _insert_chat_room(cur, listing_id, buyer_id, seller_id)

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, buyer_id):
                cur.execute(
                    "insert into public.chat_messages (room_id, sender_id, body) "
                    "values (%s, %s, %s)",
                    (room_id, seller_id, "상대방 이름으로 위조한 메시지"),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute(
        "select count(*) from public.chat_messages where room_id = %s and body = %s",
        (room_id, "상대방 이름으로 위조한 메시지"),
    )
    assert cur.fetchone()[0] == 0, "sender_id 위조 INSERT가 실제로 행을 남겼다"


# ── P3 — listings_update_own의 with check (auth.uid() = seller_id) 축 ────────────────────────
#     기존 UPDATE 테스트 4건은 전부 price·status만 바꿔 `using`이 이미 통과시킨 조건과 겹쳤다 —
#     `with check`를 `(true)`로 약화해도 그 4건은 green으로 남는다. seller_id를 실제로 재할당해야
#     이 축이 격리된다. 성공하면 0007의 set_listing_seller_name 트리거가 seller_name까지 뒤이어
#     뒤집는다.


def test_active_owner_cannot_reassign_listing_seller_id(db):
    cur = db
    owner_id = _create_user(cur, f"reassign-owner-{uuid.uuid4()}@example.test")
    victim_id = _create_user(cur, f"reassign-victim-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, owner_id)
    assert _profile_status(cur, owner_id) == "active", "전제 실패"

    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            with _as(cur, owner_id):
                cur.execute(
                    "update public.listings set seller_id = %s where id = %s",
                    (victim_id, listing_id),
                )
    assert exc.value.sqlstate == _RLS_VIOLATION, (
        "본인 매물을 남의 명의로 재할당했다(예외 없이 통과) — with check가 seller_id를 안 본다"
    )
    assert _RLS_MESSAGE_MARK in str(exc.value), (
        "42501이 났지만 RLS 정책 위반이 아니다 — GRANT 누락(환경 붕괴)일 수 있다"
    )

    cur.execute("select seller_id from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == owner_id, "매물의 seller_id가 실제로 바뀌었다"


# ── P6 — "안 막는다" 판정 3종(찜·안읽음 커서·채팅방 생성)이 실제로 열려 있다 ────────────────
#     `0032` §9·docs/conventions.md §8·스펙 Design Notes 세 곳이 전부 "정지 회원도 찜·안읽음
#     커서·채팅방 생성은 계속 쓸 수 있다"고 프로즈로만 적었는데, 그걸 확인하는 실행되는 검사가
#     하나도 없었다(0032가 실수로 이 세 축을 막아도 아무 것도 red가 안 된다). `increment_listing_view`
#     는 이 patch가 다루는 대상이 아니다(SECURITY DEFINER + anon도 호출 — 별도 축).


def test_suspended_member_can_still_wishlist_chat_room_reads_and_create_chat_room(db):
    cur = db
    seller_id = _create_user(cur, f"p6-seller-{uuid.uuid4()}@example.test", role="seller")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    member_id = _create_user(cur, f"p6-member-{uuid.uuid4()}@example.test")
    _suspend(cur, member_id)

    with _as(cur, member_id):
        # wishlists INSERT — 정지 회원도 찜을 추가할 수 있다("안 막는다" 판정, DW-801).
        cur.execute(
            "insert into public.wishlists (user_id, listing_id) values (%s, %s)",
            (member_id, listing_id),
        )
        cur.execute(
            "select count(*) from public.wishlists where user_id = %s and listing_id = %s",
            (member_id, listing_id),
        )
        assert cur.fetchone()[0] == 1, "정지 회원의 wishlists INSERT가 막혔다"

        # wishlists DELETE — 찜 취소도 막지 않는다.
        cur.execute(
            "delete from public.wishlists where user_id = %s and listing_id = %s",
            (member_id, listing_id),
        )
        assert cur.rowcount == 1, "정지 회원의 wishlists DELETE가 막혔다"

        # chat_rooms INSERT — 방 생성은 막지 않는다("발신"만 판단 대상이었다, DW-799).
        room_id = uuid.uuid4()
        cur.execute(
            "insert into public.chat_rooms (id, listing_id, buyer_id, seller_id) "
            "values (%s, %s, %s, %s)",
            (room_id, listing_id, member_id, seller_id),
        )
        cur.execute("select count(*) from public.chat_rooms where id = %s", (room_id,))
        assert cur.fetchone()[0] == 1, "정지 회원의 chat_rooms INSERT가 막혔다"

        # chat_room_reads INSERT — 본인 안읽음 커서 생성도 막지 않는다(DW-802).
        cur.execute(
            "insert into public.chat_room_reads (user_id, room_id) values (%s, %s)",
            (member_id, room_id),
        )
        cur.execute(
            "select count(*) from public.chat_room_reads where user_id = %s and room_id = %s",
            (member_id, room_id),
        )
        assert cur.fetchone()[0] == 1, "정지 회원의 chat_room_reads INSERT가 막혔다"

        # chat_room_reads UPDATE — last_read_at 갱신도 막지 않는다.
        cur.execute(
            "update public.chat_room_reads set last_read_at = now() "
            "where user_id = %s and room_id = %s",
            (member_id, room_id),
        )
        assert cur.rowcount == 1, "정지 회원의 chat_room_reads UPDATE가 막혔다"


# ══════════════════════════════════════════════════════════════════════════════════════════
# 2026-08-11 Story 17.2 — 조회수 RPC(increment_listing_view) 정지 가드 (DW-805)
# ══════════════════════════════════════════════════════════════════════════════════════════
# `0034_view_count_suspended_guard.sql`이 이 함수 본문에 정지 가드를 추가했다 — 17.1(0032) 9절이
# "해당 없음(anon도 호출)"으로 판정했던 자리를 뒤집는다(정문(listings 직접 쓰기)은 잠갔는데
# view_count RPC라는 옆문이 열려 있었다). 여기 붙이는 이유는 스펙(Story 17.2)이 "같은 관심사,
# 같은 헬퍼(_create_user/_insert_listing/_suspend/_as)를 재사용 — 새 파일을 만들지 않는다"고
# 지정했기 때문이다. RPC 자체의 GRANT·멱등성·트리거 하드닝(정지와 무관한 축)은 이미
# `test_view_count_rpc_real_db.py`(Story 11.1)가 지킨다 — 여기서는 **정지 축**만 새로 고정한다.
#
# 이 검사가 안 보는 것: `increment_listing_view`가 실제로 웹 상세 페이지에서 호출되는지는
# 이 파일이 보지 않는다(web `viewCountCallSite.test.ts`·수동 확인의 몫). 이 파일도
# `test_view_count_rpc_real_db.py`와 동일하게 `set local role`로 Postgres 롤만 흉내 낼 뿐,
# 실제 PostgREST/`supabase.rpc()` HTTP 경로는 거치지 않는다.


def _view_count(cur, listing_id):
    cur.execute("select view_count from public.listings where id = %s", (listing_id,))
    return cur.fetchone()[0]


def test_suspended_member_cannot_increment_view_count(db):
    """정지 회원의 조회수 증가 시도는 0행으로 조용히 실패한다(예외 없음 — 함수 안
    SECURITY DEFINER UPDATE의 WHERE절이 거른 것도 RLS using 거부와 같은 신호 형태)."""
    cur = db
    suspended_id = _create_user(cur, f"vc-susp-{uuid.uuid4()}@example.test")
    other_seller_id = _create_user(cur, f"vc-susp-other-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, other_seller_id)  # 정지 회원 소유가 아닌 매물
    _suspend(cur, suspended_id)
    before = _view_count(cur, listing_id)

    with _as(cur, suspended_id):
        cur.execute("select public.increment_listing_view(%s)", (listing_id,))

    assert _view_count(cur, listing_id) == before, "정지 회원의 조회수 증가가 통과했다"


def test_suspended_member_cannot_increment_view_count_of_own_listing(db):
    """소유 여부와 무관하다 — 정지는 행위자 기준이다. 자기 매물이어도 똑같이 막힌다."""
    cur = db
    seller_id = _create_user(cur, f"vc-susp-own-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    _suspend(cur, seller_id)
    before = _view_count(cur, listing_id)

    with _as(cur, seller_id):
        cur.execute("select public.increment_listing_view(%s)", (listing_id,))

    assert _view_count(cur, listing_id) == before, "정지 회원이 자기 매물의 조회수를 올렸다"


def test_anon_view_count_increment_unaffected_by_suspended_guard(db):
    """비로그인 회귀(스펙 AC) — 이게 없으면 정지 가드가 "전부 막힘"으로 잘못 짜여도 구별할 수
    없다. `auth.uid()`가 NULL이면 정지 판정 서브쿼리가 항상 0행이라 통과해야 한다(FR58, 설계
    의도 — 우연한 NULL 처리가 아니다)."""
    cur = db
    seller_id = _create_user(cur, f"vc-anon-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    before = _view_count(cur, listing_id)

    cur.execute("set local role anon")
    try:
        cur.execute("select public.increment_listing_view(%s)", (listing_id,))
    finally:
        cur.execute("reset role")

    assert _view_count(cur, listing_id) == before + 1, (
        "비로그인 호출이 정지 가드에 막혔다(FR58 회귀)"
    )


def test_active_member_view_count_increment_unaffected_by_suspended_guard(db):
    """활성 회원 회귀(스펙 AC) — 정지 가드가 정지된 사람만 막는지, "전부 막힘"이 아닌지 확인하는
    짝(비로그인 회귀와 함께 둬야 "정지만 막는다"가 증명된다)."""
    cur = db
    seller_id = _create_user(cur, f"vc-active-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    assert _profile_status(cur, seller_id) == "active", "전제 실패"
    before = _view_count(cur, listing_id)

    with _as(cur, seller_id):
        cur.execute("select public.increment_listing_view(%s)", (listing_id,))

    assert _view_count(cur, listing_id) == before + 1, "활성 회원의 조회수 증가가 막혔다(회귀)"


def test_active_view_count_increment_leaves_timestamps_unchanged(db):
    """트리거 회귀(스펙 Code Map) — 0020의 `listings_set_timestamps()`는 view_count가 바뀐
    UPDATE에서 updated_at을 갱신하지 않는다. 가드가 UPDATE를 0행으로 만들면 트리거가 애초에
    안 돌므로 정지 케이스는 별도로 볼 필요가 없다 — 이 테스트는 **활성 회원의 정상 증가**가
    그 계약을 여전히 지키는지만 확인한다(이 스토리가 이 축을 건드리지 않았다는 증거)."""
    cur = db
    seller_id = _create_user(cur, f"vc-trigger-{uuid.uuid4()}@example.test")
    listing_id = uuid.uuid4()
    _insert_listing(cur, listing_id, seller_id)
    cur.execute(
        "select updated_at, created_at from public.listings where id = %s", (listing_id,)
    )
    before_updated_at, before_created_at = cur.fetchone()

    with _as(cur, seller_id):
        cur.execute("select public.increment_listing_view(%s)", (listing_id,))

    cur.execute(
        "select updated_at, created_at from public.listings where id = %s", (listing_id,)
    )
    after_updated_at, after_created_at = cur.fetchone()
    assert after_updated_at == before_updated_at, "조회수 증가가 updated_at을 건드렸다(트리거 회귀)"
    assert after_created_at == before_created_at, "조회수 증가가 created_at을 건드렸다"
