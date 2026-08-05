"""profiles.role CHECK 완화 실DB 검증 — 완화가 **실제로** 일어났는가 (Story 14.1, 0027).

왜 이 파일이 따로 있나:
  0027은 0001의 3값 enum CHECK(`role in ('buyer','seller','admin')`)를 걷어냈다. 그런데
  이 스토리가 검증으로 내세운 `scripts/check_migrations.py`는 profiles를 보는 프로브가
  없다(동적 프로브 3개는 listings 컬럼 GRANT·listings.embedding 차단·guide_documents 정책).
  실제로 0027의 새 CHECK를 원래 3값 enum으로 되돌려도 그 게이트는 **동일하게 exit 0**이다
  (14.1 리뷰에서 실행해 확인, 대장 등재). 즉 이 스토리의 유일한 자동 검증이 이 스토리가
  완전히 틀려도 red가 되지 않는다 — 제약을 없앴는데 대체 검사가 하나도 없는 상태였다
  (CLAUDE.md B4 "'만들었다'가 아니라 '잡는다'가 완료다", B9 "규칙은 어길 수 없는 자리에").

  tests.yml이 `supabase/migrations/**`를 paths 트리거로 넣은 이유가 정확히 이 경우다 —
  "그 제약을 약화·삭제하는 변경"을 잡으려고. 그 층에 assertion을 놓는 것이 이 파일이다.

무엇을 증명하나 (spec의 I/O 매트릭스 DB 층 4행 + 0027 사후조건과 같은 축):
  ① buyer/seller/admin 밖의 임의 값이 저장된다 — 0027을 되돌리면 여기가 red가 된다
  ② 빈 문자열은 남은 CHECK(23514)로 여전히 거부된다
  ③ NULL은 컬럼의 NOT NULL(23502)로 여전히 거부된다 — CHECK와 무관하게 유효
  ④ role='admin' 행에서 is_admin()이 true — admin 게이트 무회귀
  ⑤ buyer/seller를 강제하는 CHECK가 **이름과 무관하게** 하나도 남아 있지 않다
     (0027의 `drop ... if exists`가 이름 드리프트로 no-op이 됐는지를 이름을 모른 채 잡는다)

⑥~⑧은 3차 리뷰가 추가했다. ①~⑤는 전부 "**적용이 끝난 뒤의 DB 상태**"만 본다 — CI DB는 항상
0001부터 순서대로 새로 만들어지므로, 0027이 **적용되는 순간**에만 성립하는 일(기존 행을 건드리는가,
드리프트를 만나면 멈추는가)은 그 어느 것도 관측되지 않았다. 그래서 아래 세 검사는 0027 파일을
**디스크에서 읽어 트랜잭션 안에서 다시 실행**하고 그 순간을 관측한다(파일과 검사가 드리프트할 수 없다):
  ⑥ 이미 role='buyer' 행이 있는 상태에 0027을 적용해도 그 값이 그대로다 — spec의 I/O 매트릭스
     1행("기존 값 보존")과 Never 절("일괄 UPDATE 금지")이 실제로 성립하는지를 재현해서 본다
  ⑦ 제약 이름이 드리프트해 `drop`이 no-op이 되면 0027이 **실패한다** — 0027 끝의 사후조건 가드는
     CI DB에서 발화 조건 자체가 만들어지지 않아, 지워도 약화시켜도 아무것도 red가 되지 않았다
  ⑧ 0027 본문에 profiles를 바꾸는 UPDATE/DELETE가 없다 — Never 절을 문장 층에서 한 번 더 못박는다

무엇을 **못 보나** (실측으로 확인한 사각지대 — 0027 주석과 같은 내용):
  · role의 **어휘**는 이제 DB가 강제하지 않는다. `' '`·`'ADMIN'`·`'admin '`도 전부 통과하고
    is_admin()은 그것들을 admin으로 인정하지 않는다. 아래 test_relaxed_check_does_not_see_*가
    그 사실을 **의도적으로 초록으로** 못박는다(모르는 것과 알고 두는 것은 다르다).
  · ⑥의 재실행은 "0027을 이미 적용한 DB에 한 번 더 적용"이라 **운영 DB의 첫 적용과 완전히 같지는
    않다**(첫 적용 때만 3값 CHECK가 살아 있다). 그 1회성 사실의 실측은 spec의 Verification
    Evidence에 있고, 여기서는 재현 가능한 부분(기존 행 무변경)만 매번 못박는다.
  · **신규 가입(INSERT) 경로**는 여전히 buyer/seller로 강제된다 — 0009의 handle_new_user가
    `v_role not in ('buyer','seller') then v_role := 'buyer'`이기 때문이다. 완화의 효용이
    실제로 드러나는 건 그 트리거를 바꾸는 Story 14.2부터이고, 그건 이 스토리 범위 밖이다.

실행: CI의 `api-db` 잡이 pgvector 컨테이너를 띄우고 TEST_DATABASE_URL을 준다.
  로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:5432/postgres'
  없으면 skip(거짓 통과 금지).
"""

import re
import uuid
from pathlib import Path

import psycopg
import pytest

from conftest import _DSN, _create_user, pytestmark  # noqa: F401 — pytestmark는 skip 마커

_CHECK_VIOLATION = "23514"
_NOT_NULL_VIOLATION = "23502"

# 검사가 보는 마이그레이션 파일 자체. 본문을 여기 복사하지 않고 매번 디스크에서 읽는다 —
# 사본을 두면 파일이 바뀌어도 검사는 옛 본문을 계속 통과시킨다(이 리포가 반복해서 겪은 실패).
_MIGRATION_PATH = (
    Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "0027_role_check_relax.sql"
)


def _migration_sql():
    return _MIGRATION_PATH.read_text(encoding="utf-8")


def _apply_migration(cur):
    """0027 전문을 현재 트랜잭션 안에서 실행한다(psycopg3는 파라미터 없는 다중 문장을 그대로 보낸다)."""
    cur.execute(_migration_sql())


@pytest.fixture
def db():
    """행을 만들지 않고 커서만 주고 **끝나면 롤백**한다(DB 원상복구).

    카탈로그만 보거나 마이그레이션을 재실행하는 검사용이다. `profile` 픽스처를 쓰면 가입 트리거의
    동작(=Story 14.2가 바꿀 예정인 것)에 불필요하게 묶여, CHECK와 무관한 이유로 red가 될 수 있다.
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


@pytest.fixture
def profile():
    """트랜잭션 안에서 `(cursor, profile_id)`를 돌려주고 **끝나면 롤백**한다(DB 원상복구).

    가입 트리거(handle_new_user)는 buyer/seller만 배정하므로(0009: `if v_role not in
    ('buyer','seller') then v_role := 'buyer'`), 임의 값·admin은 트리거로 만들 수 없다.
    그래서 트리거로 buyer 프로필을 만든 뒤 UPDATE로 role을 바꾼다 — CHECK 평가는
    INSERT든 UPDATE든 동일하게 걸리므로 이 경로로 제약을 시험할 수 있다.
    (profiles.id는 auth.users FK라 임의 uuid로 직접 INSERT하는 경로는 애초에 막혀 있다.)
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            user_id = _create_user(c, f"role-relax-{uuid.uuid4()}@example.test")
            yield c, user_id
        conn.rollback()


def _set_role(cur, profile_id, value):
    cur.execute("update public.profiles set role = %s where id = %s", (value, profile_id))


@pytest.mark.parametrize("value", ["user", "member", "consolidated-role", "whatever-14-2-picks"])
def test_non_enum_role_is_accepted(profile, value):
    """① 3값 밖의 임의 값이 저장된다 — 이 스토리가 한 일 그 자체.

    0027을 되돌리거나 누가 다시 3값 CHECK를 붙이면 여기가 red가 된다. 그것이 이 파일의 존재 이유다.
    """
    cur, profile_id = profile
    _set_role(cur, profile_id, value)
    cur.execute("select role from public.profiles where id = %s", (profile_id,))
    assert cur.fetchone()[0] == value


def test_empty_string_role_is_still_rejected(profile):
    """② 빈 문자열은 남은 CHECK가 여전히 거부한다(23514) — 완화가 '전부 허용'은 아니다."""
    cur, profile_id = profile
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with cur.connection.transaction():  # SAVEPOINT — 바깥 트랜잭션(프로필 행)은 살린다
            _set_role(cur, profile_id, "")
    assert exc.value.sqlstate == _CHECK_VIOLATION


def test_null_role_is_still_rejected_by_not_null(profile):
    """③ NULL은 컬럼의 NOT NULL이 거부한다(23502) — CHECK는 NULL에 unknown이라 무관하다."""
    cur, profile_id = profile
    with pytest.raises(psycopg.errors.NotNullViolation) as exc:
        with cur.connection.transaction():
            _set_role(cur, profile_id, None)
    assert exc.value.sqlstate == _NOT_NULL_VIOLATION


def test_is_admin_still_true_for_admin_role(profile):
    """④ admin 게이트 무회귀 — role='admin'인 사용자를 흉내내면 is_admin()이 true.

    is_admin()(0001)은 `auth.uid()`로 자기 행을 찾아 `role = 'admin'`을 정확일치 비교한다.
    프렐류드의 auth.uid() 스텁이 `request.jwt.claim.sub`를 읽으므로 그 값을 세팅해 흉내낸다
    (test_chat_unread_real_db.py와 같은 방식).
    """
    cur, profile_id = profile
    _set_role(cur, profile_id, "admin")
    cur.execute(f"set local request.jwt.claim.sub = '{profile_id}'")
    try:
        cur.execute("select public.is_admin()")
        assert cur.fetchone()[0] is True
    finally:
        cur.execute("reset request.jwt.claim.sub")


def test_no_check_constraint_still_enforces_buyer_or_seller(profile):
    """⑤ buyer/seller를 강제하는 CHECK가 **이름과 무관하게** 하나도 없다.

    0027은 `drop constraint if exists profiles_role_check`로 이름을 지정해 지운다. 배포 대상
    DB의 제약 이름이 다르면 그 drop은 조용히 no-op이 되고, 뒤이은 add는 **두 번째** CHECK로
    성공한다 — Postgres는 같은 테이블의 CHECK를 AND로 결합하므로 옛 3값 제약이 그대로 살아
    있는 채 마이그는 성공을 보고한다. 이름을 하나도 가정하지 않고 정의 문자열로 확인해
    그 경우를 잡는다(0027 끝의 `do $$ ... raise exception` 사후조건과 같은 축, 다른 층).
    """
    cur, _profile_id = profile
    cur.execute(
        "select conname, pg_get_constraintdef(oid) from pg_constraint "
        "where conrelid = 'public.profiles'::regclass and contype = 'c'"
    )
    offenders = [(name, d) for name, d in cur.fetchall() if "buyer" in d or "seller" in d]
    assert offenders == [], f"3값 enum CHECK가 아직 남아 있다: {offenders}"


@pytest.mark.parametrize("value", [" ", "ADMIN", "admin ", "Admin"])
def test_relaxed_check_does_not_see_whitespace_or_case_variants(profile, value):
    """이 검사가 **안 보는 것**: 공백·대소문자 변형도 전부 통과하고, admin으로 인정되지 않는다.

    0027이 어휘 검사를 걷어냈으므로 이건 회귀가 아니라 **의도된 상태**다(14.2가 기본값을
    정할 때 다시 좁힐지 판단한다). 여기가 red가 되면 정책이 바뀐 것이므로 함께 갱신한다.
    """
    cur, profile_id = profile
    _set_role(cur, profile_id, value)
    cur.execute("select role from public.profiles where id = %s", (profile_id,))
    assert cur.fetchone()[0] == value  # 저장은 된다

    cur.execute(f"set local request.jwt.claim.sub = '{profile_id}'")
    try:
        cur.execute("select public.is_admin()")
        assert cur.fetchone()[0] is False  # 그러나 admin은 아니다(정확일치)
    finally:
        cur.execute("reset request.jwt.claim.sub")


# --- 아래 셋은 "적용이 끝난 상태"가 아니라 **적용되는 순간**을 본다(파일 헤더 ⑥~⑧). ---


def test_applying_migration_does_not_touch_existing_rows(profile):
    """⑥ 이미 role 값을 가진 행이 있는 상태에 0027을 적용해도 그 값이 그대로다.

    spec의 I/O 매트릭스 1행("기존 값 보존")과 Never 절("기존 role을 일괄 변경하는 UPDATE 금지")을
    지탱하는 자리인데, CI DB는 늘 빈 profiles에 마이그를 적용하므로 이 조건이 재현된 적이 없었다.
    여기서는 행을 **먼저** 만들고 0027을 다시 실행해 그 순간을 관측한다(끝나면 롤백).
    """
    cur, profile_id = profile
    cur.execute("select role from public.profiles where id = %s", (profile_id,))
    assert cur.fetchone()[0] == "buyer"

    _apply_migration(cur)

    cur.execute("select role from public.profiles where id = %s", (profile_id,))
    assert cur.fetchone()[0] == "buyer", "0027이 기존 행의 role을 바꿨다 — forward-only 위반"


def test_migration_aborts_when_drop_is_a_no_op(db):
    """⑦ 제약 이름이 드리프트해 `drop`이 no-op이 되면 0027이 **실패한다**.

    0027 끝의 사후조건(`do $$ ... raise exception`)이 바로 그 경우를 잡으려고 있는데, CI DB는
    언제나 이 레포의 0001로 만들어지므로 발화 조건 자체가 생기지 않는다 — 즉 그 가드를 통째로
    지워도 아무것도 red가 되지 않았다(3차 리뷰 실측). 드리프트를 여기서 재현해 가드를 살린다.

    재현 방법: 현재 제약을 걷어내고 **다른 이름**으로 3값 enum CHECK를 붙인다. 그러면 0027의
    `drop ... if exists profiles_role_check`는 대상이 없어 no-op이 되고, 뒤이은 add는 두 번째
    CHECK로 성공한다(Postgres는 CHECK를 AND 결합) — 사후조건이 없다면 마이그가 성공을 보고한다.
    `not valid`로 붙이는 이유: 이 검사의 관심은 카탈로그에 그 정의가 있느냐지 기존 행 검증이
    아니고, 같은 DB를 쓰는 형제 테스트가 남긴 행 때문에 setup이 실패하면 안 되기 때문이다.
    """
    db.execute("alter table public.profiles drop constraint if exists profiles_role_check")
    db.execute(
        "alter table public.profiles add constraint profiles_role_check_legacy "
        "check (role in ('buyer','seller','admin')) not valid"
    )

    with pytest.raises(psycopg.errors.RaiseException) as exc:
        _apply_migration(db)

    assert "3값 CHECK가 아직 남아 있다" in str(exc.value)


def test_migration_contains_no_data_mutation():
    """⑧ 0027 본문에 profiles의 데이터를 바꾸는 문장이 없다(Never 절을 문장 층에서 못박는다).

    ⑥은 "이 마이그를 지금 돌리면 행이 안 바뀐다"를 보고, 이건 "애초에 바꾸는 문장이 없다"를 본다.
    둘 다 필요한 이유: 조건부 UPDATE(예: `where role = 'buyer'`)는 테스트가 만든 행에 안 걸리면
    ⑥을 통과할 수 있다. 주석은 제외하고 실행되는 SQL만 본다.
    """
    body = "\n".join(
        line for line in _migration_sql().splitlines() if not line.lstrip().startswith("--")
    )
    mutations = re.findall(r"\b(update|delete\s+from|truncate)\b", body, flags=re.IGNORECASE)
    assert mutations == [], f"0027에 데이터 변경 문장이 있다: {mutations}"
