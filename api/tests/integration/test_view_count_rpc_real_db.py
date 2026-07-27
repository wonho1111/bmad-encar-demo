"""조회수 RPC 하드닝 실DB 검증 — `increment_listing_view`가 유일한 쓰기 통로인가 (Story 11.1).

왜 이 파일이 따로 있나:
  0020이 만든 컬럼 단위 REVOKE는 SQL에 그 **글자**가 있는 것과, Postgres가 실제로
  authenticated·anon의 직접 쓰기를 거부하는 것은 다른 사실이다(CLAUDE.md B4 "존재 확인은
  작동 확인이 아니다"). 특히 이 레포는 `alter default privileges ... grant all on tables to
  anon, authenticated`(플랫폼 기본 GRANT, 원격+로컬 게이트 프렐류드 둘 다 재현)로 authenticated가
  listings **테이블 전체** INSERT·UPDATE 권한을 이미 갖고 있다 — 컬럼 하나만 회수하는 REVOKE는
  테이블 단위 권한이 남아 있으면 무효가 된다(로컬 Postgres로 직접 재현해 확인한 사실, 0020 주석
  참조). 그래서 0020은 UPDATE·INSERT 두 축 모두 "테이블 전체 회수 → view_count를 뺀 나머지
  컬럼만 재-GRANT" 2단계를 쓰고, anon은 직접 쓰기 3동사를 통째로 회수한다 — 그게 실제로
  view_count만 막고 다른 컬럼(기존 등록/수정 기능)은 그대로 쓰게 두는지, 진짜 Postgres로
  확인한다(`test_seller_summary_real_db.py`·`test_trust_attributes_real_db.py`와 같은 이유,
  같은 방식).

무엇을 증명하나 (spec I/O 매트릭스 4행 + 후속 리뷰 1·2차 신설분 전부):
  ① anon/authenticated 롤로 RPC를 호출하면 성공하고 대상 행의 view_count가 정확히 1 증가한다.
  ② 반복 호출 시 누적 증가한다(멱등이 아님 — 의도된 동작, Design Notes "멱등의 실제 의미").
  ③ authenticated가 view_count를 직접 UPDATE하면 InsufficientPrivilege(42501)로 거부되고,
     **다른 컬럼**(price)은 여전히 UPDATE 가능하다(회귀 아님을 증명).
  ④ anon/authenticated가 아닌 롤(`ai_readonly`, 0006)로 RPC를 호출하면 EXECUTE 권한이 없어
     거부된다(PUBLIC 경유 실행이 열려 있지 않음도 함께 증명).
  ⑤ 존재하지 않는(또는 삭제된) id로 호출해도 에러 없이 조용히 0행 처리되고, 다른 행엔 영향 없다.
  ⑥ INSERT 축: authenticated가 view_count를 지정해 INSERT하면 거부되고, 지정하지 않으면 성공하며
     기본값 0이 적용된다(등록 시점 위조 차단).
  ⑦·⑧ anon·authenticated × INSERT·UPDATE 4조합의 권한 완전성을, 기대 컬럼 집합을
     `information_schema.columns`에서 실시간 도출해 검증한다(하드코딩 리터럴이면 0020 이후
     추가되는 컬럼의 GRANT 누락을 구조적으로 못 잡는다 — 리뷰 실측 재현됨).
  ⑨ RPC 호출 전후 updated_at은 변하지 않고, view_count는 실제로 1 증가한다(둘 다 함께 단언 —
     한쪽만 보면 트리거를 통째로 지우거나 RPC를 no-op으로 바꿔도 green이 된다, 리뷰 실측).
  ⑩ 최소 한 곳은 프로덕션과 같은 명명 인자(`p_listing_id => ...`)로 호출한다 — 위치 인자로만
     부르면 파라미터명을 바꿔도 pytest는 green인 채 PostgREST 경로만 깨진다(리뷰 실측).
  ⑪ 트리거 양방향: (a) view_count를 안 바꾸는 평범한 수정(price)은 updated_at을 갱신한다,
     (b) created_at 위조는 view_count를 함께 바꾸든 안 바꾸든 항상 원복된다(루프백 #2가 잡은
     결함 — `when` 가드는 두 경우 다 트리거 자체를 꺼서 위조 차단까지 죽였다, 실측 재현).
  ⑫ anon DELETE 축: `has_table_privilege`로 anon이 listings DELETE 권한이 없음을 확인한다
     (5번 블록이 회수하는 3개 축 중 유일하게 검증이 비어 있던 축).
  ⑬ SellForm/Flutter가 실제로 보내는 컬럼 집합(options 배열·description·신뢰속성 3종 포함)으로
     INSERT해 등록 경로 전체에 회귀가 없음을 증명한다 — 좁은 스팟체크(15컬럼)로는 4번 블록이
     재-GRANT한 25개 중 10개가 실수로 빠져도 못 잡는다.

무엇을 **못 보나**: web `/listings/[id]` 서버 컴포넌트가 이 RPC를 실제로 1회 호출하는지는
  `viewCountCallSite.test.ts`(정적 소스 스캔)와 수동 확인 몫이다 — 여기는 DB 계층(스키마·권한·
  트리거)만 본다. 또한 이 테스트들은 `set local role`로 Postgres 역할만 바꿀 뿐 실제 프로덕션
  경로인 PostgREST/`supabase.rpc()` HTTP 계층은 거치지 않는다(대장 #133, 기존에도 있던 gap).

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:55322/postgres'
  없으면 skip(거짓 통과 금지).
"""

import os
import time
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

# 0020 이전(view_count 도입 전) listings 컬럼 집합은 여기 하드코딩하지 않는다 — 권한 완전성
# 테스트(⑦·⑧)는 information_schema.columns에서 매번 실시간으로 뽑는다(리뷰 지적, 하드코딩이면
# 새 컬럼 추가 시 GRANT 누락을 구조적으로 못 잡는다).


def _insert_listing(cur, listing_id, seller_id):
    cur.execute(
        f"insert into public.listings ({_LISTING_COLS}) values "
        "(%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
        "'흰색', '가솔린', '자동', 1998, 5, '서울')",
        (listing_id, seller_id),
    )


def _create_seller(cur, email):
    seller_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) "
        "values (%s, %s, '{\"role\":\"seller\"}'::jsonb)",
        (seller_id, email),
    )
    # 0001의 가입 트리거가 profiles 행을 만든다 — listings.seller_id FK가 이를 요구한다.
    cur.execute("select id from public.profiles where id = %s", (seller_id,))
    assert cur.fetchone() is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    return seller_id


@pytest.fixture
def seeded():
    """판매자 1명 + 매물 1건. 끝나면 **롤백**해 원상복구한다(다른 실DB 테스트와 동일 패턴)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            seller_id = _create_seller(c, f"vc-{uuid.uuid4()}@example.com")
            listing_id = uuid.uuid4()
            _insert_listing(c, listing_id, seller_id)
            yield c, listing_id, seller_id
        conn.rollback()


@pytest.fixture
def seeded_committed():
    """updated_at 관찰 전용 — `now()`는 트랜잭션 내내 고정이라 롤백 픽스처(위 `seeded`)로는
    updated_at 변화 자체를 관측할 수 없다(1차 구현이 스스로 발견한 함정). 그래서 autocommit
    커넥션으로 커밋하며 진행하고, 끝나면 auth.users를 지워 profiles·listings까지 cascade로
    직접 정리한다.

    ⚠️ 이메일은 실행마다 유일하게(uuid) 만든다(코드리뷰 2026-07-28 지적) — 하드코딩 이메일은
    프로세스가 테스트 도중 죽으면(커밋된 채로 남아) 실제 Supabase의 auth.users 유니크 제약에
    걸려 이후 모든 실행이 red가 된다.
    """
    conn = psycopg.connect(_DSN, autocommit=True)
    try:
        with conn.cursor() as c:
            # P5-b(코드리뷰 2026-07-28): _create_seller·_insert_listing을 try **안**으로 옮긴다.
            # autocommit 커넥션이라 이 둘 사이에서 실패하면(예: FK 위반) 판매자·profiles 행이
            # 커밋된 채 실제 DB에 남는데, 원래 위치는 그 구간이 finally 밖이라 정리되지 않았다.
            seller_id = None
            try:
                seller_id = _create_seller(c, f"vc-committed-{uuid.uuid4()}@example.com")
                listing_id = uuid.uuid4()
                _insert_listing(c, listing_id, seller_id)
                yield c, listing_id, seller_id
            finally:
                if seller_id is not None:
                    c.execute("delete from auth.users where id = %s", (seller_id,))
    finally:
        conn.close()


def _view_count(cur, listing_id):
    cur.execute("select view_count from public.listings where id = %s", (listing_id,))
    return cur.fetchone()[0]


def _call_rpc(cur, listing_id, *, as_role, local=True, named=False):
    """`increment_listing_view`를 지정한 롤로 임퍼소네이션해 호출한다.

    `local=True`(기본)는 `SET LOCAL ROLE` — 롤백 픽스처(`seeded`)에서 `with
    cur.connection.transaction()` 세이브포인트 안에 쓴다. `local=False`는 `SET ROLE` — autocommit
    커넥션(`seeded_committed`)에서 쓴다(SET LOCAL은 트랜잭션 경계에서 무효화되므로 autocommit과
    안 맞는다).

    ⚠️ reset role은 try/finally로 감싼다(코드리뷰 2026-07-28 지적) — 안 그러면 예외 발생 시
    롤이 새어 다음 단언이 엉뚱한 이유로 통과/실패한다. 다만 실패한 호출은 보통 세이브포인트
    안에서 일어나 트랜잭션이 이미 중단(aborted)된 상태이므로, 그 상태에서의 reset role 시도
    자체가 `InFailedSqlTransaction`을 내는 게 정상이다 — 그건 무시한다(감싸는 세이브포인트
    롤백이 SET LOCAL ROLE도 함께 되돌리므로 실질적으로 새는 것이 없다).
    """
    cur.execute(("set local role %s" if local else "set role %s") % as_role)
    try:
        if named:
            cur.execute("select public.increment_listing_view(p_listing_id => %s)", (listing_id,))
        else:
            cur.execute("select public.increment_listing_view(%s)", (listing_id,))
    finally:
        try:
            cur.execute("reset role")
        except psycopg.errors.InFailedSqlTransaction:
            pass


def test_view_count_starts_at_zero(seeded):
    """AC1 전제: 컬럼 기본값 0(마이그 적용 직후 상태)."""
    cur, listing_id, _seller_id = seeded
    assert _view_count(cur, listing_id) == 0


@pytest.mark.parametrize("role", ["anon", "authenticated"])
def test_rpc_call_increments_exactly_one(seeded, role):
    """① anon/authenticated 롤로 호출하면 성공하고 정확히 1 증가한다."""
    cur, listing_id, _seller_id = seeded
    with cur.connection.transaction():
        _call_rpc(cur, listing_id, as_role=role)
    assert _view_count(cur, listing_id) == 1


def test_named_argument_contract(seeded):
    """⑩ 명명 인자 계약 — 프로덕션(PostgREST/supabase-js)은 `{ p_listing_id: ... }`처럼 항상
    명명 인자로 호출한다. 위치 인자로만 테스트하면 파라미터 이름을 바꿔도 pytest는 green인 채
    프로덕션 경로만 PGRST202로 깨진다(리뷰 실측). 최소 이 한 곳은 `p_listing_id => ...` 형태로
    호출해 그 계약을 고정한다.
    """
    cur, listing_id, _seller_id = seeded
    with cur.connection.transaction():
        _call_rpc(cur, listing_id, as_role="authenticated", named=True)
    assert _view_count(cur, listing_id) == 1


def test_repeated_calls_accumulate_not_idempotent(seeded):
    """② 반복 호출은 누적된다 — RPC는 멱등이 아니다(호출마다 항상 +1, 의도된 동작).

    Design Notes "'멱등'의 실제 의미": 지켜야 하는 건 DB 레벨 멱등성이 아니라 "호출 지점을
    상세 페이지 한 곳으로 한정하는 것"뿐이다. 이 테스트는 함수 자체가 멱등이 **아님**을
    고정해, 누군가 나중에 "멱등하게 고치자"며 조용히 동작을 바꾸는 회귀를 막는다.
    """
    cur, listing_id, _seller_id = seeded
    with cur.connection.transaction():
        for _ in range(3):
            _call_rpc(cur, listing_id, as_role="authenticated")
    assert _view_count(cur, listing_id) == 3


def test_nonexistent_listing_id_is_silent_noop(seeded):
    """⑤ 존재하지 않는(또는 이미 삭제된) listing_id로 호출해도 에러 없이 조용히 0행 처리된다
    (범용 UPDATE로 확장하지 않는다는 스펙 Never 절과 동일 이유 — 존재 확인 로직은 이 함수의
    단일 동작 밖의 일이다). 다른 행(seeded 매물)의 view_count가 영향받지 않는지도 함께 확인한다.
    """
    cur, listing_id, _seller_id = seeded
    missing_id = uuid.uuid4()

    with cur.connection.transaction():
        _call_rpc(cur, missing_id, as_role="authenticated")  # 에러 없이 통과해야 한다

    assert _view_count(cur, listing_id) == 0, "존재하지 않는 id 호출이 다른 행에 영향을 주면 안 된다"


def test_authenticated_direct_column_update_is_rejected(seeded):
    """③ authenticated가 view_count를 직접 UPDATE하면 InsufficientPrivilege(42501)로 거부된다.

    RLS(listings_update_own)가 아니라 **GRANT/REVOKE**가 이 방어선이다 — 본인 소유 매물(RLS는
    통과하는 행)로 시도하는 이유가 바로 그것이다: 행 소유권이 있어도 컬럼 권한이 없으면 여전히
    거부돼야 "컬럼 단위 하드닝이 진짜 방어선"임이 증명된다(RLS가 어쩌다 같이 막은 게 아님).
    """
    cur, listing_id, seller_id = seeded
    with pytest.raises(psycopg.errors.InsufficientPrivilege) as exc:
        with cur.connection.transaction():
            cur.execute("set local role authenticated")
            cur.execute(f"set local request.jwt.claim.sub = '{seller_id}'")
            cur.execute(
                "update public.listings set view_count = 999 where id = %s", (listing_id,)
            )
    assert exc.value.sqlstate == _INSUFFICIENT_PRIVILEGE
    cur.execute("reset role")


def test_authenticated_can_still_update_other_columns(seeded):
    """③-b 회귀 방지: view_count만 막혔을 뿐, authenticated는 여전히 자기 매물의 다른
    컬럼(price)을 직접 UPDATE할 수 있어야 한다 — 0020이 기존 등록/수정 기능을 깨지 않았다는 증거.
    """
    cur, listing_id, seller_id = seeded
    with cur.connection.transaction():
        cur.execute("set local role authenticated")
        cur.execute(f"set local request.jwt.claim.sub = '{seller_id}'")
        cur.execute(
            "update public.listings set price = 30000000 where id = %s", (listing_id,)
        )
        cur.execute("reset role")

    cur.execute("select price from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == 30000000


def test_authenticated_insert_with_view_count_is_rejected(seeded):
    """⑥ INSERT 축: authenticated가 등록 시점에 view_count를 지정하면 InsufficientPrivilege로
    거부된다 — 이게 없으면 SellForm이 anon 키로 직접 insert하는 경로로 view_count를 임의 값
    (예: 999999)으로 심을 수 있다(리뷰 실측 재현).
    """
    cur, _listing_id, seller_id = seeded
    new_id = uuid.uuid4()
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with cur.connection.transaction():
            cur.execute("set local role authenticated")
            cur.execute(f"set local request.jwt.claim.sub = '{seller_id}'")
            cur.execute(
                f"insert into public.listings ({_LISTING_COLS}, view_count) values "
                "(%s, %s, 'on_sale', '현대', '아반떼', '준중형차', 2021, 20000000, 10000, "
                "'흰색', '가솔린', '자동', 1600, 5, '서울', 999999)",
                (new_id, seller_id),
            )
    cur.execute("reset role")


def test_authenticated_insert_without_view_count_defaults_to_zero(seeded):
    """⑥-b: view_count를 아예 지정하지 않고 등록하면 정상 성공하고, 그 행의 view_count는
    컬럼 기본값 0이다 — 등록 경로 자체는 회귀 없이 그대로 동작해야 한다.
    """
    cur, _listing_id, seller_id = seeded
    new_id = uuid.uuid4()
    with cur.connection.transaction():
        cur.execute("set local role authenticated")
        cur.execute(f"set local request.jwt.claim.sub = '{seller_id}'")
        cur.execute(
            f"insert into public.listings ({_LISTING_COLS}) values "
            "(%s, %s, 'on_sale', '현대', '아반떼', '준중형차', 2021, 20000000, 10000, "
            "'흰색', '가솔린', '자동', 1600, 5, '서울')",
            (new_id, seller_id),
        )
        cur.execute("reset role")

    cur.execute("select view_count from public.listings where id = %s", (new_id,))
    assert cur.fetchone()[0] == 0


def test_authenticated_insert_with_real_registration_payload(seeded):
    """⑬ 실제 등록 페이로드 회귀 방지: 위 ⑥-b 테스트는 15개 컬럼만 넣어, 4번 블록이 재-GRANT한
    25개 중 10개(options·description·신뢰속성 3종 등)를 안 건드린다. SellForm(web)·
    sell_controller(Flutter)가 실제로 다루는 컬럼 집합에 신뢰속성 3종까지 더한 폭넓은 페이로드로
    한 건 더 등록해, GRANT 목록의 나머지 절반에도 회귀가 없음을 증명한다.
    """
    cur, _listing_id, seller_id = seeded
    new_id = uuid.uuid4()
    with cur.connection.transaction():
        cur.execute("set local role authenticated")
        cur.execute(f"set local request.jwt.claim.sub = '{seller_id}'")
        cur.execute(
            "insert into public.listings ("
            "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
            "color, fuel, transmission, displacement, seats, region, accident_free, "
            "options, description, accident_status, is_single_owner, is_non_smoker"
            ") values ("
            "%s, %s, 'on_sale', '기아', 'K5', '중형차', 2022, 28000000, 5000, "
            "'검정', '가솔린', '자동', 1999, 5, '경기', true, "
            "array['선루프', '통풍시트'], '무사고 차량입니다', '무사고', true, true"
            ")",
            (new_id, seller_id),
        )
        cur.execute("reset role")

    cur.execute(
        "select accident_status, is_single_owner, is_non_smoker, options, description, view_count "
        "from public.listings where id = %s",
        (new_id,),
    )
    accident_status, is_single_owner, is_non_smoker, options, description, view_count = cur.fetchone()
    assert accident_status == "무사고"
    assert is_single_owner is True
    assert is_non_smoker is True
    assert options == ["선루프", "통풍시트"]
    assert description == "무사고 차량입니다"
    assert view_count == 0


def test_non_anon_authenticated_role_execute_is_rejected(seeded):
    """④ anon/authenticated가 아닌 롤(`ai_readonly`, 0006)로 RPC를 호출하면 EXECUTE 권한이
    없어 거부된다 — `revoke all on function ... from public` 후 anon·authenticated에만
    grant했으므로, 그 두 롤 밖은 PUBLIC 경유로도 실행할 수 없어야 한다.
    """
    cur, listing_id, _seller_id = seeded
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with cur.connection.transaction():
            _call_rpc(cur, listing_id, as_role="ai_readonly")
    assert _view_count(cur, listing_id) == 0


@pytest.mark.parametrize(
    "role,privilege",
    [
        ("authenticated", "UPDATE"),
        ("authenticated", "INSERT"),
        ("anon", "UPDATE"),
        ("anon", "INSERT"),
    ],
)
def test_grant_completeness_four_combinations(seeded, role, privilege):
    """⑦·⑧ 권한 완전성 — (anon·authenticated) × (INSERT·UPDATE) 4조합 전부.

    기대 컬럼 집합을 하드코딩하지 않고 `information_schema.columns`에서 **실시간으로** 뽑아
    `{전 컬럼} - {view_count}`와 비교한다(authenticated 기준). 하드코딩 리터럴은 "0020 이후
    새로 추가된 컬럼이 GRANT 목록에서 누락"되는 함정을 구조적으로 못 잡는다(리뷰에서
    `alter table ... add column`으로 재현: 컬럼이 조용히 쓰기 불가가 됐는데 테스트는
    green이었다).

    P2(코드리뷰 2026-07-28) — anon 쪽은 `information_schema.column_privileges`의 빈 집합
    비교에 의존하지 않는다. 그 방식은 쿼리가 어떤 이유로든 0행을 돌려주기만 하면 통과해,
    `grantee='anon'`도 `grantee='anonn'`(오타)도 똑같이 통과함이 실측됐다 — "4조합 전부
    검증"이라는 docstring의 주장 중 anon 쪽 절반이 실제로는 아무것도 검증하지 않고 있었다.
    대신 전 컬럼에 대해 `has_column_privilege('anon', ...)`가 개별로 False임을 직접 묻고,
    같은 프로브를 authenticated + 화이트리스트 컬럼(price)으로 먼저 돌려 True가 나오는
    **대조군**을 둔다 — 대조군이 없으면 프로브 자체가 망가져도(예: 함수명 오타) 여전히
    조용히 통과한다.
    """
    cur, _listing_id, _seller_id = seeded

    cur.execute(
        "select column_name from information_schema.columns "
        "where table_schema = 'public' and table_name = 'listings'"
    )
    all_columns = {row[0] for row in cur.fetchall()}

    if role == "authenticated":
        expected = all_columns - {"view_count"}

        cur.execute(
            "select column_name from information_schema.column_privileges "
            "where table_schema = 'public' and table_name = 'listings' "
            "and grantee = %s and privilege_type = %s",
            (role, privilege),
        )
        granted = {row[0] for row in cur.fetchall()}

        assert granted == expected, (
            f"{role}의 {privilege} 가능 컬럼 집합이 기대와 다르다"
            f" (누락: {expected - granted}, 초과: {granted - expected})"
        )
        assert "view_count" not in granted, "view_count는 authenticated의 쓰기 대상에서 제외돼야 한다"
    else:
        # 대조군 — 프로브(has_column_privilege) 자체가 살아 있는지 먼저 확인한다. 이게 없으면
        # 아래 for 루프가 전부 False를 돌려줘도 "정말 막힌 것"과 "프로브가 죽은 것"을 구별 못 한다.
        cur.execute(
            "select has_column_privilege('authenticated', 'public.listings', 'price', %s)",
            (privilege,),
        )
        assert cur.fetchone()[0] is True, "대조군 실패 — has_column_privilege 프로브 자체가 깨졌다"

        for col in sorted(all_columns):
            cur.execute(
                "select has_column_privilege('anon', 'public.listings', %s, %s)",
                (col, privilege),
            )
            assert cur.fetchone()[0] is False, f"anon이 {col}에 {privilege} 권한을 가지면 안 된다"


def test_anon_can_select_whitelisted_columns_but_view_count_still_denied(seeded):
    """P1(코드리뷰 2026-07-28) — 0020의 5번 블록은 `revoke all`이 아니라
    `revoke insert, update, delete ... from anon`만 쓴다. 마이그레이션 주석이 그 이유를
    "revoke all을 쓰면 0011이 anon에게 준 컬럼 SELECT까지 날아가 비로그인 열람이 깨진다"고
    적어 뒀는데, 그 불변식을 지키는 실행 검사가 없었다(리뷰 실측 — 리포 전체에서 anon으로
    listings를 읽는 테스트가 0건). 두 방향을 함께 고정한다:
      (a) 0011 화이트리스트 컬럼(id·manufacturer·model·price)은 anon으로 SELECT가 성공하고
          그 매물 행이 실제로 보인다 — 비로그인 열람이 이 스토리로 깨지지 않았다.
      (b) view_count는 여전히 anon에 안 보인다(#134가 기록한 현재 상태 — Story 11.4의
          선결 조건이므로, 지금 여기서 바뀌면 이 테스트가 즉시 알려야 한다).
    """
    cur, listing_id, _seller_id = seeded
    cur.execute("set local role anon")
    try:
        with cur.connection.transaction():
            cur.execute(
                "select id, manufacturer, model, price from public.listings where id = %s",
                (listing_id,),
            )
            row = cur.fetchone()
        assert row is not None, "anon이 0011 화이트리스트 컬럼으로 매물 행을 못 읽었다 — 비로그인 열람이 깨졌다"
        assert row[0] == listing_id

        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with cur.connection.transaction():
                cur.execute(
                    "select view_count from public.listings where id = %s", (listing_id,)
                )
    finally:
        try:
            cur.execute("reset role")
        except psycopg.errors.InFailedSqlTransaction:
            pass


def test_anon_has_no_delete_privilege_on_listings(seeded):
    """⑫ anon DELETE 축 — 5번 블록이 회수하는 3개 축(INSERT·UPDATE·DELETE) 중 INSERT·UPDATE는
    위 4조합 테스트가 컬럼 단위로 이미 검증하지만 DELETE는 테이블 단위 권한이라(컬럼이 없다)
    `has_table_privilege`로 따로 확인해야 한다 — 지금까지 검증이 비어 있던 축이다.
    """
    cur, _listing_id, _seller_id = seeded
    cur.execute("select has_table_privilege('anon', 'public.listings', 'DELETE')")
    assert cur.fetchone()[0] is False


def test_created_at_forgery_reverted_even_with_view_count_change(seeded):
    """⑪(b) — created_at 위조는 view_count를 함께 바꾸든 안 바꾸든 항상 되돌려진다.

    루프백 #2가 잡은 결함: 트리거에 `when (new.view_count is not distinct from old.view_count)`
    가드를 걸면, view_count가 바뀌는 UPDATE에서는 트리거 자체가 통째로 안 돌아 created_at 위조
    차단(0002)까지 함께 죽는다(실측 재현: `update … set created_at='2000-01-01', view_count =
    view_count + 1`이 통과해 등록일이 위조됐다). `listings_set_timestamps()`는 조건을 `when`
    절이 아니라 함수 본문 안에 둬 created_at 보존만은 항상 실행되게 한다 — 이 테스트가 그
    계약을 고정한다.

    GRANT 계층(authenticated는 view_count UPDATE 권한이 없다, ③)과는 별개 축이다 — 여기서는
    트리거 자체의 동작만 보려는 것이므로, 컬럼 권한 제약이 없는 연결 롤(이 테스트가 접속한
    계정, 보통 postgres)로 직접 UPDATE한다.
    """
    cur, listing_id, _seller_id = seeded
    cur.execute("select created_at from public.listings where id = %s", (listing_id,))
    (original_created_at,) = cur.fetchone()

    with cur.connection.transaction():
        cur.execute(
            "update public.listings set created_at = '2000-01-01', view_count = view_count + 1 "
            "where id = %s",
            (listing_id,),
        )

    cur.execute("select created_at, view_count from public.listings where id = %s", (listing_id,))
    created_at, view_count = cur.fetchone()
    assert created_at == original_created_at, "view_count와 함께 바꿔도 created_at은 되돌려져야 한다"
    assert view_count == 1


def test_created_at_forgery_reverted_without_view_count_change(seeded):
    """⑪(b) 짝 — view_count를 안 건드리는 평범한 위조 시도도 여전히 되돌려진다(0002의 기존
    계약에 이 스토리가 회귀를 만들지 않았음을 확인).
    """
    cur, listing_id, _seller_id = seeded
    cur.execute("select created_at from public.listings where id = %s", (listing_id,))
    (original_created_at,) = cur.fetchone()

    with cur.connection.transaction():
        cur.execute(
            "update public.listings set created_at = '2000-01-01' where id = %s",
            (listing_id,),
        )

    cur.execute("select created_at from public.listings where id = %s", (listing_id,))
    (created_at,) = cur.fetchone()
    assert created_at == original_created_at


def test_ordinary_update_bumps_updated_at(seeded_committed):
    """⑪(a) — view_count를 안 바꾸는 평범한 수정(price)은 updated_at을 갱신한다(엄격히 증가).

    트리거가 통째로 사라지거나 `after update`로 잘못 재생성되면 이 테스트가 red가 된다(2차
    리뷰 실측: 기존엔 "안 바뀐다" 한 방향만 봐서 이 회귀를 아무도 못 잡았다).
    """
    cur, listing_id, seller_id = seeded_committed
    cur.execute("select updated_at from public.listings where id = %s", (listing_id,))
    (before,) = cur.fetchone()

    time.sleep(0.05)
    cur.execute("set role authenticated")
    try:
        cur.execute(f"set request.jwt.claim.sub = '{seller_id}'")
        cur.execute("update public.listings set price = 30000000 where id = %s", (listing_id,))
    finally:
        # P5-a(코드리뷰 2026-07-28): try/finally 없이 reset role만 뒤에 두면, UPDATE가 예외를
        # 던질 때 롤이 authenticated로 샌다 — autocommit 커넥션이라 세이브포인트가 없어(다른
        # 픽스처의 `set local role`과 다름) 이 픽스처는 스스로 되돌리지 못한다. 그 상태로
        # seeded_committed의 teardown(`delete from auth.users`)이 authenticated 롤로 돌면
        # `permission denied for schema auth`가 나서 진짜 실패 원인이 가려진다(리뷰 실측).
        cur.execute("reset role")

    cur.execute("select updated_at, price from public.listings where id = %s", (listing_id,))
    after, price = cur.fetchone()
    assert after > before, "view_count를 안 건드리는 평범한 수정은 updated_at을 엄격히 갱신해야 한다"
    assert price == 30000000


def test_increment_leaves_updated_at_unchanged_and_bumps_view_count(seeded_committed):
    """⑨ + ⑪(c) — RPC 호출 전후로 updated_at은 변하지 않고, view_count는 실제로 1 증가한다.

    두 단언을 함께 두는 이유(리뷰 실측): "updated_at 불변"만 보면 트리거를 통째로 지워도,
    `after update`로 잘못 재생성해도, RPC 본문을 no-op으로 바꿔도 전부 green이었다 — "실제로
    증가했다"를 같이 확인해야 RPC가 정말 일을 했다는 것도 함께 고정된다.
    """
    cur, listing_id, _seller_id = seeded_committed
    cur.execute("select updated_at, view_count from public.listings where id = %s", (listing_id,))
    before_updated_at, before_view_count = cur.fetchone()

    time.sleep(0.05)
    _call_rpc(cur, listing_id, as_role="authenticated", local=False)

    cur.execute("select updated_at, view_count from public.listings where id = %s", (listing_id,))
    after_updated_at, after_view_count = cur.fetchone()

    assert after_updated_at == before_updated_at, "조회수 증가가 updated_at을 건드리면 안 된다"
    assert after_view_count == before_view_count + 1, "RPC가 실제로 view_count를 증가시켜야 한다(no-op 회귀 방지)"
