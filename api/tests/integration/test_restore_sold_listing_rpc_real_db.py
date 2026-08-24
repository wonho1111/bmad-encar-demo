"""관리자 판매완료 되돌리기 RPC 하드닝 실DB 검증 — `admin_restore_sold_listing`이 유일한 되돌리기
통로이고, 관리자·sold 매물 조합에서만 실제로 동작하는가 (DW-391, Story 15.4).

왜 이 파일이 따로 있나:
  `0030`이 만든 GRANT/REVOKE·WHERE 절이 SQL에 그 **글자**로 있는 것과, Postgres가 실제로
  비관리자·anon의 호출을 거부하고 관리자 호출만 통과시키는 것은 다른 사실이다(CLAUDE.md B4
  "존재 확인은 작동 확인이 아니다"). `test_view_count_rpc_real_db.py`(0020)·
  `test_chat_unread_real_db.py`(0025)와 같은 방식(`SET LOCAL ROLE` + `request.jwt.claim.sub`
  임퍼소네이션)으로 실제 Postgres에 붙어 확인한다.

무엇을 증명하나 (spec I/O 매트릭스 5행 + Never 절 2가지):
  ① 관리자가 sold 매물에서 호출하면 정확히 1행(id) 반환, status가 on_sale로 바뀐다(AC1).
  ② 비관리자(authenticated, 구매자)가 직접 호출하면 0행, status 불변.
  ③ 매물 소유자(판매자) 본인이라도 관리자가 아니면 거부된다 — 관리자 판별이 소유권이 아니라
     오직 is_admin()임을 확인한다.
  ④ anon은 EXECUTE 권한 자체가 없어 InsufficientPrivilege(42501)로 거부된다.
  ⑤ 이미 on_sale인 행에 관리자가 재호출해도 0행, 에러 없음(멱등).
  ⑥ 존재하지 않는 id로 호출해도 에러 없이 조용히 0행 처리된다.
  ⑦ 명명 인자(`p_listing_id => ...`) 계약 — 프로덕션(supabase-js)이 실제로 쓰는 호출 형태.
  ⑨ AC2 행동 검증 — sold 행에 대한 **테이블 직접 UPDATE**는 판매자에게도 관리자에게도 0행이다
     (= 복구 통로가 RPC 하나뿐임을 정책 이름이 아니라 실제 시도로 증명한다).
  ⑧ Never 절 구조 검증 — listings UPDATE 정책 집합에 관리자 전면 정책(`listings_update_admin`류)이
     없다(복구 경로가 정책이 아니라 좁은 RPC라는 스펙 AC2). RPC 파라미터는 `p_listing_id uuid`
     하나뿐이다(컬럼·값을 파라미터로 받지 않는다). EXECUTE는 authenticated에만 있고 anon·public엔
     없다.

무엇을 **못 보나**: web `ListingAdminActions.tsx`가 이 RPC를 실제로 호출하는지는 정적 스캔·수동
  확인 몫이다 — 여기는 DB 계층(스키마·권한·RLS)만 본다. `SET LOCAL ROLE`은 Postgres 역할만 바꿀
  뿐 실제 프로덕션 경로인 PostgREST/`supabase.rpc()` HTTP 계층은 거치지 않는다(기존 실DB 테스트
  전반의 공통 gap, 대장 #133과 동일 성격).

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

_INSUFFICIENT_PRIVILEGE = "42501"

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


def _create_user(cur, email, *, role=None):
    # ⚠️ 2026-08-11 갱신(Story 17.1, 0033): 가입 트리거는 metadata의 role을 더 이상 안 읽는다
    # (항상 'user'로 배정) — conftest.py·test_chat_idempotency_real_db.py의 같은 정정과 동일
    # 계약(2026-08-11 3차 코드리뷰 patch로 이 사본도 그 두 곳과 형태를 맞췄다: metadata는
    # jsonb_build_object('role', ...)로 보내고, 트리거 직후 role=='user'를 실제로 단언한다 —
    # 이전엔 이 사본만 '{}'::jsonb를 보내고 그 단언이 없어 세 사본의 계약 정정 문서화가 갈렸다).
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
    # 0001의 가입 트리거가 profiles 행을 만든다 — listings.seller_id FK가 이를 요구한다.
    cur.execute("select role from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    assert row[0] == "user", (
        f"가입 트리거가 'user' 고정 계약(0033, DW-682)을 지키지 않았다: {row[0]!r}"
    )
    if role is not None:
        # 관리자는 운영자가 승격시키는 역할이라 가입 메타데이터로 안 온다(0028 시절에도, 0033 이후에도
        # 마찬가지) — profiles를 직접 올린다(is_admin()이 보는 것이 이 컬럼이다).
        cur.execute("update public.profiles set role = %s where id = %s", (role, user_id))
        assert cur.rowcount == 1, (
            f"role={role!r} UPDATE가 정확히 한 행을 못 바꿨다(rowcount={cur.rowcount})"
        )
    return user_id


@pytest.fixture
def seeded():
    """판매자 1명(sold 매물 1건 소유) + 관리자 1명 + 비관리자(구매자) 1명. 끝나면 롤백."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = _create_user(c, f"restore-seller-{uuid.uuid4()}@example.com")
            admin_id = _create_user(c, f"restore-admin-{uuid.uuid4()}@example.com", role="admin")
            buyer_id = _create_user(c, f"restore-buyer-{uuid.uuid4()}@example.com")
            listing_id = uuid.uuid4()
            _insert_listing(c, listing_id, seller_id, status="sold")
            yield c, listing_id, seller_id, admin_id, buyer_id
        conn.rollback()


def _status(cur, listing_id):
    cur.execute("select status from public.listings where id = %s", (listing_id,))
    return cur.fetchone()[0]


def _call_rpc(cur, listing_id, *, as_role, sub=None, named=True):
    """`admin_restore_sold_listing`을 지정한 롤(+선택적으로 JWT sub)로 임퍼소네이션해 호출하고
    반환된 행(list of tuples)을 돌려준다.

    ⚠️ reset role은 try/finally로 감싼다(0020·0025 관례와 동일 이유) — 안 그러면 예외 발생 시
    롤이 새어 다음 단언이 엉뚱한 이유로 통과/실패한다.
    """
    cur.execute("set local role %s" % as_role)
    try:
        if sub is not None:
            cur.execute(f"set local request.jwt.claim.sub = '{sub}'")
        if named:
            cur.execute(
                "select * from public.admin_restore_sold_listing(p_listing_id => %s)",
                (listing_id,),
            )
        else:
            cur.execute(
                "select * from public.admin_restore_sold_listing(%s)", (listing_id,)
            )
        return cur.fetchall()
    finally:
        try:
            cur.execute("reset role")
        except psycopg.errors.InFailedSqlTransaction:
            pass


def _other_columns_snapshot(cur, listing_id):
    """status·updated_at을 뺀 나머지 전 컬럼 값(순서 고정) — RPC가 status 외에는 아무것도
    안 바꾼다는 Never 절("컬럼·값을 파라미터로 받지 않는다")을 실측으로 고정하기 위한 대조군."""
    cur.execute(
        "select column_name from information_schema.columns "
        "where table_schema = 'public' and table_name = 'listings' "
        "and column_name not in ('status', 'updated_at') "
        "order by column_name"
    )
    cols = [row[0] for row in cur.fetchall()]
    cur.execute(f"select {', '.join(cols)} from public.listings where id = %s", (listing_id,))
    return dict(zip(cols, cur.fetchone()))


def _updated_at(cur, listing_id):
    cur.execute("select updated_at from public.listings where id = %s", (listing_id,))
    return cur.fetchone()[0]


def test_admin_restores_sold_listing(seeded):
    """① AC1 / I-O 매트릭스 1행 — 관리자가 sold 매물에서 호출하면 정확히 1행(id) 반환,
    status가 on_sale로 바뀐다. Never 절 실측(코드리뷰 patch) — status·updated_at을 뺀 나머지
    컬럼은 전부 호출 전후 동일해야 한다(RPC가 범용 UPDATE로 확장되지 않았다는 증거)."""
    cur, listing_id, _seller_id, admin_id, _buyer_id = seeded
    before = _other_columns_snapshot(cur, listing_id)

    # 코드리뷰 patch — updated_at은 위 대조군에서 **제외**했으므로, 제외한 채로 두면 "이 컬럼이
    #   어떻게 되는지 아무도 안 본다"가 된다(제외와 미검증은 다르다). 0020의 listings_set_timestamps
    #   BEFORE UPDATE 트리거가 이 SECURITY DEFINER 경로에서도 실제로 발화하는지 고정한다 —
    #   DW-718(관리자 액션 감사 로그 부재)을 defer한 근거가 "적어도 updated_at은 움직인다"라서,
    #   그 전제 자체를 실측으로 못박아 둔다.
    #
    #   ⚠️ 왜 "호출 전후 비교"가 아니라 "낡은 값을 심고 덮이는지"인가(실측으로 배운 것):
    #     트리거는 `new.updated_at := now()`인데 Postgres의 now()는 **트랜잭션 시작 시각**이다.
    #     이 픽스처는 INSERT와 RPC 호출이 같은 트랜잭션 안에 있어, 트리거가 정상 발화해도 전후
    #     값이 **똑같다**. 단순 전후 비교는 그래서 구조적으로 항상 실패한다(제품 결함 아님).
    #     대신 명백히 과거인 값을 심어두고, 호출 뒤 그 값이 덮여 있는지를 본다.
    #
    #   ⚠️⚠️ 심을 때 트리거를 **꺼야 한다**(3차 코드리뷰 실측 — 안 끄면 이 검사는 무의미했다):
    #     낡은 값을 심는 UPDATE 자체가 "view_count가 안 바뀐 UPDATE"라 listings_set_timestamps가
    #     그 자리에서 발화해 updated_at을 now()로 덮는다. 즉 _STALE은 **한 번도 저장되지 않고**,
    #     아래 단언은 RPC를 호출하기도 전에 이미 참이었다(실측: 시드 직후 `updated_at > stale` = t).
    #     그 상태의 검사가 증명하는 것은 "RPC 경로에서 트리거가 발화한다"가 아니라 "트리거가
    #     존재한다"뿐이다 — 트리거를 drop하면 red가 되므로 red/green 실험으로도 구별되지 않았다.
    #     그래서 (a) 심는 동안만 트리거를 끄고, (b) 심은 값이 실제로 남았는지를 **먼저 단언**해
    #     이 검사가 다시 조용히 무의미해지는 것을 막는다.
    _STALE = "2020-01-01T00:00:00+00:00"
    cur.execute("select %s::timestamptz", (_STALE,))
    stale_ts = cur.fetchone()[0]
    cur.execute("alter table public.listings disable trigger listings_set_timestamps")
    try:
        cur.execute("update public.listings set updated_at = %s where id = %s", (_STALE, listing_id))
    finally:
        cur.execute("alter table public.listings enable trigger listings_set_timestamps")
    assert _updated_at(cur, listing_id) == stale_ts, (
        "낡은 값이 심어지지 않았다 — 이 상태로는 아래 updated_at 단언이 RPC와 무관하게 항상 참이 된다"
    )

    with cur.connection.transaction():
        rows = _call_rpc(cur, listing_id, as_role="authenticated", sub=admin_id)
    assert [r[0] for r in rows] == [listing_id]
    assert _status(cur, listing_id) == "on_sale"
    after = _other_columns_snapshot(cur, listing_id)
    assert after == before, f"status 외 컬럼이 바뀌었다(범용 UPDATE로 확장된 회귀 의심): {before} vs {after}"

    assert _updated_at(cur, listing_id) > stale_ts, (
        "되돌리기 후 updated_at이 갱신되지 않았다 — 관리자 복구의 유일한 시각 증거가 사라진다"
    )


def test_named_argument_contract(seeded):
    """⑦ 명명 인자 계약 — 프로덕션(supabase-js)은 `{ p_listing_id: ... }`처럼 항상 명명
    인자로 호출한다. 이미 기본 호출이 named=True이므로 이 테스트는 그 경로가 회귀 없이 도달
    가능함을 별도로 고정한다(0020 관례와 동일)."""
    cur, listing_id, _seller_id, admin_id, _buyer_id = seeded
    with cur.connection.transaction():
        rows = _call_rpc(cur, listing_id, as_role="authenticated", sub=admin_id, named=True)
    assert [r[0] for r in rows] == [listing_id]


def test_non_admin_authenticated_call_is_noop(seeded):
    """② I-O 매트릭스 2행 — 비관리자(구매자) authenticated가 직접 호출하면 0행, status 불변."""
    cur, listing_id, _seller_id, _admin_id, buyer_id = seeded
    with cur.connection.transaction():
        rows = _call_rpc(cur, listing_id, as_role="authenticated", sub=buyer_id)
    assert rows == []
    assert _status(cur, listing_id) == "sold"


def test_seller_of_the_listing_cannot_self_restore(seeded):
    """③ 매물 소유자(판매자) 본인이라도 관리자가 아니면 거부된다 — 관리자 판별이 소유권이
    아니라 오직 `is_admin()`임을 확인한다(RLS `listings_update_own`이 애초에 sold 행을 빼므로
    이 경로가 아니라 RPC의 `is_admin()` 조건이 방어선임을 증명)."""
    cur, listing_id, seller_id, _admin_id, _buyer_id = seeded
    with cur.connection.transaction():
        rows = _call_rpc(cur, listing_id, as_role="authenticated", sub=seller_id)
    assert rows == []
    assert _status(cur, listing_id) == "sold"


def test_anon_execute_is_denied(seeded):
    """④ I-O 매트릭스 3행 — anon은 EXECUTE 권한 자체가 없어 InsufficientPrivilege(42501)로
    거부된다(increment_listing_view와 달리 이 RPC는 anon에 grant하지 않는다, 0030)."""
    cur, listing_id, _seller_id, _admin_id, _buyer_id = seeded
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            _call_rpc(cur, listing_id, as_role="anon")
    assert exc.value.sqlstate == _INSUFFICIENT_PRIVILEGE
    assert _status(cur, listing_id) == "sold"


def test_idempotent_on_already_on_sale_row(seeded):
    """⑤ I-O 매트릭스 4행 — 이미 on_sale인 행에 관리자가 재호출하면 0행, 에러 없음(멱등)."""
    cur, listing_id, _seller_id, admin_id, _buyer_id = seeded
    with cur.connection.transaction():
        first = _call_rpc(cur, listing_id, as_role="authenticated", sub=admin_id)
    assert [r[0] for r in first] == [listing_id]
    assert _status(cur, listing_id) == "on_sale"

    with cur.connection.transaction():
        second = _call_rpc(cur, listing_id, as_role="authenticated", sub=admin_id)
    assert second == [], "이미 on_sale인 행 재호출은 0행이어야 한다(멱등, 에러 아님)"
    assert _status(cur, listing_id) == "on_sale"


def test_nonexistent_listing_id_is_silent_noop(seeded):
    """⑥ 존재하지 않는(또는 이미 삭제된) listing_id로 호출해도 에러 없이 조용히 0행 처리된다
    (범용 UPDATE로 확장하지 않는다는 Never 절과 동일 이유 — 존재 확인 로직은 이 함수의 단일
    동작 밖의 일이다)."""
    cur, listing_id, _seller_id, admin_id, _buyer_id = seeded
    missing_id = uuid.uuid4()
    with cur.connection.transaction():
        rows = _call_rpc(cur, missing_id, as_role="authenticated", sub=admin_id)
    assert rows == []
    assert _status(cur, listing_id) == "sold", "존재하지 않는 id 호출이 다른 행에 영향을 주면 안 된다"


def test_no_broad_admin_update_policy_exists(seeded):
    """⑧-a AC2 구조 검증 — 복구 경로가 `listings_update_admin` 같은 전면 UPDATE 정책이 아니라
    좁은 RPC다. listings의 UPDATE 정책 중 이름에 "admin"이 들어간 것이 없어야 한다 — 있다면
    관리자 전면 UPDATE 정책이 새로 생겨 0015가 막은 "sold 매물 임의 수정"을 반쯤 되연 것이다
    (스펙 Never 절 위반).

    ⚠️ 코드리뷰 patch: 최초 버전은 정책 집합 전체가 정확히 `{"listings_update_own"}`인지
    비교했다 — 이 스토리와 무관한 좁은 UPDATE 정책이 나중에 하나 더 생기면(예: 다른 스토리가
    다른 이유로 UPDATE 정책을 추가) 그 정책이 "admin 전면 정책"이 아니어도 이 테스트가 깨져,
    실패 메시지가 "관리자 전면 UPDATE 정책 신설 의심"이라고 잘못 지목하게 된다. 그래서 이
    Never 절이 실제로 금지하는 것("admin"이 들어간 UPDATE 정책)만 좁혀서 확인한다.
    """
    cur, *_ = seeded
    cur.execute(
        "select policyname from pg_policies "
        "where schemaname = 'public' and tablename = 'listings' and cmd = 'UPDATE'"
    )
    policies = {row[0] for row in cur.fetchall()}
    assert "listings_update_own" in policies, f"기존 listings_update_own(0015) 정책이 사라졌다: {policies}"
    admin_policies = {p for p in policies if "admin" in p}
    assert not admin_policies, (
        f"listings에 관리자 전면 UPDATE 정책이 새로 생겼다(Never 절 위반 의심): {admin_policies}"
    )


def test_rpc_is_the_only_door_to_a_sold_row(seeded):
    """⑨ AC2 **행동** 검증 — 위 ⑧-a는 정책 *이름*만 본다(코드리뷰 지적). 이름 검사는 누군가
    `listings_update_moderation` 같은 이름으로 전면 UPDATE 정책을 열거나, `listings_update_own`을
    이름만 남기고 `using` 술어를 무르게 바꿔도 전부 통과한다 — 즉 "RPC가 유일한 통로"라는 주장
    자체는 실측된 적이 없었다.

    그래서 **다른 문(테이블 직접 UPDATE)을 실제로 밀어본다**: sold 행에 대해 판매자 본인도,
    관리자도 `update public.listings set status='on_sale'`이 0행이어야 한다(0015의 RLS `using`이
    sold 행을 UPDATE 대상에서 빼므로 에러가 아니라 0행). 이 두 단언이 살아 있는 한, 복구 통로는
    RPC 하나로 유지된다.

    (`status` 컬럼은 0020이 authenticated에 UPDATE GRANT를 준 컬럼 목록에 들어 있다 —
     즉 여기서 0행이 나오는 이유는 컬럼 권한이 아니라 **RLS 행 필터**임이 분리돼 증명된다.)
    """
    cur, listing_id, seller_id, admin_id, _buyer_id = seeded

    for label, sub in (("판매자 본인", seller_id), ("관리자", admin_id)):
        with cur.connection.transaction():
            cur.execute("set local role authenticated")
            try:
                cur.execute(f"set local request.jwt.claim.sub = '{sub}'")
                cur.execute(
                    "update public.listings set status = 'on_sale' where id = %s", (listing_id,)
                )
                rowcount = cur.rowcount
            finally:
                # _call_rpc와 같은 이유로 감싼다(3차 코드리뷰 — 인라인하면서 이 가드가 빠져 있었다):
                # 위 UPDATE가 0행이 아니라 **예외**로 실패하면(향후 컬럼 권한 변경 등) reset role이
                # InFailedSqlTransaction으로 다시 죽어, 원래 원인이 그 예외에 가려진다.
                try:
                    cur.execute("reset role")
                except psycopg.errors.InFailedSqlTransaction:
                    pass
        assert rowcount == 0, (
            f"{label}이 테이블 직접 UPDATE로 sold 행을 되돌렸다 — 0015의 RLS가 무력해졌고 "
            f"'복구 통로는 RPC 하나'라는 AC2가 깨졌다"
        )
        assert _status(cur, listing_id) == "sold"


def test_rpc_has_single_uuid_parameter():
    """⑧-b Never 절 — 컬럼·값을 파라미터로 받지 않는다. 함수 시그니처가 `p_listing_id uuid`
    하나뿐인지 구조적으로 고정한다(누군가 범용 UPDATE로 확장해도 이 테스트가 잡는다).

    ⚠️ **오버로드까지 본다**(3차 코드리뷰 지적). `create or replace`는 시그니처를 조용히 넓힐 수
    없지만, `create function admin_restore_sold_listing(uuid, text)`처럼 **형제 함수**를 새로
    만드는 것은 막지 못한다 — 그게 바로 Never 절이 금지하는 모양이다. 전에는 `fetchone()`으로
    한 행만 봐서, 좁은 쪽이 먼저 반환되면 넓은 형제가 있어도 통과했다. 아래 ⑧-c(GRANT 검사)도
    함수 이름으로만 필터하므로, 여기서 "이름당 함수 1개"를 고정하는 것이 그 검사의 전제도 함께
    지켜 준다."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select pg_get_function_identity_arguments(oid) from pg_proc "
                "where proname = 'admin_restore_sold_listing' "
                "and pronamespace = 'public'::regnamespace"
            )
            rows = cur.fetchall()
    assert rows, "admin_restore_sold_listing 함수가 존재하지 않는다(0030 미적용?)"
    assert len(rows) == 1, (
        "admin_restore_sold_listing 오버로드가 생겼다 — 넓은 시그니처가 Never 절을 우회한다: "
        f"{[r[0] for r in rows]}"
    )
    assert rows[0][0] == "p_listing_id uuid", f"RPC 파라미터 시그니처가 예상과 다르다: {rows[0][0]}"


def test_grant_execute_only_to_authenticated():
    """⑧-c anon은 EXECUTE 권한 자체가 없어야 한다(increment_listing_view와 다른 점 — 이 RPC는
    is_admin()처럼 로그인 사용자만 호출 대상이다, 0030 설계 노트). PUBLIC 경유 실행도 열려
    있으면 안 된다(revoke all ... from public 확인).

    ⚠️ 함수 소유자(이 로컬 스택은 `postgres`)는 REVOKE ALL과 무관하게 항상 암묵적 EXECUTE를
    갖고 `information_schema.routine_privileges`에도 명시 행으로 나타난다(Postgres 표준 동작,
    실측 확인) — 소유자는 `pg_proc.proowner`로 실시간 조회해 비교에서 제외한다(코드리뷰
    patch — 세 롤을 개별로만 확인하면 향후 제3의 롤에 실수로 EXECUTE가 부여돼도 못 잡는다.
    소유자를 뺀 grantee 집합이 정확히 `{authenticated}`인지 통째로 비교해 그 구멍을 막는다).
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select r.rolname from pg_proc p join pg_authid r on r.oid = p.proowner "
                "where p.proname = 'admin_restore_sold_listing' "
                "and p.pronamespace = 'public'::regnamespace"
            )
            (owner,) = cur.fetchone()

            cur.execute(
                "select grantee from information_schema.routine_privileges "
                "where routine_schema = 'public' "
                "and routine_name = 'admin_restore_sold_listing' "
                "and privilege_type = 'EXECUTE'"
            )
            grantees = {row[0] for row in cur.fetchall()}
    assert "anon" not in grantees, f"anon에 EXECUTE가 있으면 안 된다: {grantees}"
    assert "PUBLIC" not in grantees, f"PUBLIC(전체)에 EXECUTE가 있으면 안 된다: {grantees}"
    non_owner_grantees = grantees - {owner}
    assert non_owner_grantees == {"authenticated"}, (
        f"소유자({owner})를 뺀 EXECUTE 대상이 authenticated 하나여야 한다: {non_owner_grantees}"
    )
