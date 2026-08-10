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
  · **신규 가입(INSERT) 경로**는 이 스토리(14.1) 시점엔 여전히 buyer/seller로 강제됐다 — 0009의
    handle_new_user가 `v_role not in ('buyer','seller') then v_role := 'buyer'`였기 때문이다.
    완화의 효용은 그 트리거를 바꾸는 Story 14.2(0028_handle_new_user_default_role.sql)부터
    실제로 드러난다 — 이 파일 아래쪽의 `test_handle_new_user_default_role_matrix`가 그 계약을
    검증한다(같은 트리거 대상 파일이라 14.2가 이 자리에 추가했다).

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
_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
_MIGRATION_PATH = _MIGRATIONS_DIR / "0027_role_check_relax.sql"

# ⑧(아래 test_migration_contains_no_data_mutation)이 훑는 범위. **파일 목록을 손으로 적지 않는다** —
# 0027 이상 번호를 디스크에서 매번 긁는다. 이유(Story 14.2 후속 리뷰 2차 지적): 직전 버전은
# ["0027…", "0028…"] 리터럴이었는데, 그건 이 검사가 고치려던 결함("검사가 0027 하나만 봤다")을
# 0029에서 그대로 재발시킨다 — 목록에 추가하는 걸 잊어도 아무것도 red가 안 된다.
# 형제 검사 api/tests/test_migration_no_backfill.py가 이미 같은 문제를 glob + 자기검사로 풀었고,
# 여기서 그 패턴을 그대로 따른다.
#
# 왜 0027부터인가: 0027이 profiles.role의 3값 CHECK를 걷어내면서 "기존 행은 안 건드린다"가
# **주석에만 사는 약속**이 됐다. 그 이전 번호는 이 축의 약속을 하지 않는다.
#
# CI의 api-db 잡은 **빈 DB**에 마이그를 적용하므로, 나중에 누가 백필 UPDATE를 넣어도 0건이
# 바뀌어 전부 초록으로 통과한다 — 문장 층에서 막는 이 검사가 유일한 방어다.
_FIRST_FORWARD_ONLY_NUMBER = 27

# `public.profiles`를 **대상으로 하는** 쓰기 문장만 본다. 직전 버전은 파일 어디든 `update`라는
# 단어가 있으면 걸었는데, 그 형태로는 범위를 0029+로 넓히는 순간 profiles와 무관한 정상
# 마이그(다른 테이블 백필 등)가 전부 거짓 red가 된다 — 거짓 양성은 거짓 음성만큼 빨리 검사를
# 무력화시킨다. 대신 대상이 profiles일 때는 INSERT/MERGE/COPY도 함께 본다(직전 버전이 놓친 구멍:
# `merge into public.profiles`·`insert into public.profiles … select`로 백필하면 통과했다).
_PROFILES_WRITE = re.compile(
    r"(?:insert\s+into|update|delete\s+from|merge\s+into|truncate(?:\s+table)?|copy)\s+"
    r"(?:only\s+)?(?:\"?public\"?\s*\.\s*)?\"?profiles\"?\b",
    re.IGNORECASE,
)

# 함수 **정의**의 본문은 검사 대상에서 뺀다. 마이그 적용 시점에 실행되는 것이 아니라 나중에
# 호출될 때 도는 코드이기 때문이다(0028의 `insert into public.profiles`가 바로 이 경우 — 그건
# 가입 트리거 그 자체지 백필이 아니다). 익명 블록 `do $$ … $$`는 **안** 뺀다 — 그건 적용 시점에
# 실제로 도는 문장이라 백필을 숨기기 가장 좋은 자리다. 꼬리표($fn$)를 붙인 달러 인용도 역참조로 짝짓는다.
_FUNCTION_BODY = re.compile(
    r"create\s+(?:or\s+replace\s+)?function\b.*?\$(\w*)\$.*?\$\1\$",
    re.DOTALL | re.IGNORECASE,
)


def _forward_only_migrations():
    files = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        match = re.match(r"(\d+)_", path.name)
        if match and int(match.group(1)) >= _FIRST_FORWARD_ONLY_NUMBER:
            files.append(path)
    return files


def _executable_sql(sql: str) -> str:
    """주석과 함수 정의 본문을 걷어내고 **적용 시점에 실제로 도는 문장만** 남긴다."""
    without_comments = re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.DOTALL)
    return _FUNCTION_BODY.sub(" ", without_comments)


def _migration_sql():
    return _MIGRATION_PATH.read_text(encoding="utf-8")


def _apply_migration(cur):
    """0027 전문을 현재 트랜잭션 안에서 실행한다(psycopg3는 파라미터 없는 다중 문장을 그대로 보낸다)."""
    cur.execute(_migration_sql())


@pytest.fixture
def db():
    """행을 만들지 않고 커서만 주고 **끝나면 롤백**한다(DB 원상복구).

    카탈로그만 보거나 마이그레이션을 재실행하는 검사용이다. `profile` 픽스처를 쓰면 가입 트리거의
    동작(=Story 14.2의 0028이 이미 한 번 바꾼 것)에 불필요하게 묶여, CHECK와 무관한 이유로
    red가 될 수 있다.
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


@pytest.fixture
def profile():
    """트랜잭션 안에서 `(cursor, profile_id)`를 돌려주고 **끝나면 롤백**한다(DB 원상복구).

    가입 트리거(handle_new_user)는 metadata의 buyer/seller만 그대로 반영하고 나머지는 전부
    한 값으로 강제하므로(0028: buyer/seller가 아니면 `'user'` — 0028 이전인 0009는 같은
    자리에서 `'buyer'`였다), 임의 값·admin은 트리거로 만들 수 없다. 그래서 트리거로 프로필을
    만든 뒤 UPDATE로 role을 바꾼다 — CHECK 평가는
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


@pytest.mark.parametrize("value", ["user", "member", "consolidated-role", "whatever-else"])
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

    0027이 어휘 검사를 걷어냈으므로 이건 회귀가 아니라 **의도된 상태**다. 14.2는 기본값을
    `'user'`로 정하면서 이 UPDATE 경로는 **좁히지 않기로** 했다 — 0028이 강제하는 것은
    신규 가입(INSERT) 경로뿐이고, 이미 만들어진 행의 role을 임의 문자열로 바꾸는 것을
    막는 장치는 여전히 없다(관리자 UI 외엔 그 UPDATE를 하는 코드가 없다는 사실에 기대는 상태).
    여기가 red가 되면 정책이 바뀐 것이므로 함께 갱신한다.
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


def test_forward_only_migrations_are_findable():
    """⑧의 검사 대상이 0개가 되면 "통과"가 아니라 실패다.

    glob이 조용히 빈 목록을 돌려주는 상태(경로 계산이 깨졌거나 번호 규칙이 바뀜)에서
    아래 ⑧은 아무것도 안 보면서 초록이 된다 — 검사가 무력화되는 가장 흔한 방식이다.
    """
    assert _MIGRATIONS_DIR.is_dir(), f"마이그레이션 디렉터리를 찾지 못했다: {_MIGRATIONS_DIR}"
    assert _forward_only_migrations(), (
        f"{_FIRST_FORWARD_ONLY_NUMBER:04d} 이상 번호의 마이그레이션이 하나도 없다 — "
        f"경로/번호 규칙이 바뀌었는지 확인할 것: {_MIGRATIONS_DIR}"
    )


# 이 규칙의 **명시적 예외**. 비워두는 것이 정상이고, 항목을 넣는 것은 "기존 행을 일부러 바꾼다"는
# 결정을 했다는 뜻이다 — 그런 결정은 되돌릴 수 없으므로(CLAUDE.md B3) 여기에 근거를 남긴다.
# ⚠️ 예외로 등재해도 검사에서 사라지는 게 아니다. 아래 test_0029_* 두 건이 "그 변경이 **의도한
#    범위 안에서만** 일어나는가"를 대신 본다. 예외 등재 = 검사 면제가 아니라 **검사 이관**이다.
_DATA_MUTATION_ALLOWED = {
    # 2026-08-06 사용자 결정: 역할 통합을 마무리하며 기존 계정의 buyer/seller를 없앤다.
    # 0027이 CHECK를 풀고 0028이 신규 기본값을 바꿨지만 **이미 있던 계정은 그대로**여서 계정
    # 모집단이 갈라져 있었다(옛 가입자 buyer/seller vs 신규 user). 그 구분은 역할 통합 이후
    # 아무 기능도 하지 않는데(권한은 소유권+RLS로 판정) 화면 라벨만 뜻 없이 남아 있었다.
    "0029_unify_existing_account_roles.sql",
}


def test_migration_contains_no_data_mutation():
    """⑧ 0027 이후 어느 마이그레이션도 profiles의 **기존 행**을 바꾸지 않는다(Never 절을 문장 층에서).

    단 `_DATA_MUTATION_ALLOWED`에 등재된 파일은 뺀다 — 그 목록에 넣는 것 자체가 기록이다.

    ⑥은 "이 마이그를 지금 돌리면 행이 안 바뀐다"를 보고, 이건 "애초에 바꾸는 문장이 없다"를 본다.
    둘 다 필요한 이유: 조건부 UPDATE(예: `where role = 'buyer'`)는 테스트가 만든 행에 안 걸리면
    ⑥을 통과할 수 있다.

    이 검사가 **안 보는 것**(추측 아니라 실측):
      · 함수 정의 본문 — 적용 시점에 도는 문장이 아니다(0028의 가입 트리거 INSERT가 그 경우).
        누가 handle_new_user 본문에 백필을 넣어도 여기선 안 걸린다. 익명 `do $$ … $$`는 본다.
      · profiles가 **아닌** 테이블의 백필 — 이 파일의 약속 범위 밖이다.
      · 마이그레이션 파일 밖(scripts/ 일회용 SQL·원격에 손으로 친 문장)은 아예 시야 밖이다.
    """
    offenders = []
    for path in _forward_only_migrations():
        if path.name in _DATA_MUTATION_ALLOWED:
            continue
        match = _PROFILES_WRITE.search(_executable_sql(path.read_text(encoding="utf-8")))
        if match:
            offenders.append(f"{path.name}: {match.group(0)!r}")
    assert offenders == [], (
        f"profiles의 데이터를 바꾸는 문장이 있다: {offenders} — "
        "의도한 것이면 _DATA_MUTATION_ALLOWED에 근거와 함께 등재하고, "
        "그 변경의 범위를 보는 검사를 함께 추가할 것"
    )


def test_allowlist_entries_actually_exist():
    """예외 목록이 **실재하는 파일**을 가리키는지 본다.

    파일 이름이 바뀌거나 지워지면 예외가 조용히 무의미해지고, 그러면 ⑧이 그 파일을 다시
    잡아야 하는데 목록에 남은 옛 이름 때문에 "왜 통과하지?"를 뒤늦게 추적하게 된다.
    """
    names = {p.name for p in _forward_only_migrations()}
    missing = sorted(_DATA_MUTATION_ALLOWED - names)
    assert missing == [], f"예외 목록이 없는 파일을 가리킨다: {missing}"


# --- 아래는 Story 14.2(0028_handle_new_user_default_role.sql)가 추가했다 ---
# 0027이 CHECK를 완화한 그 트리거의 기본값을 0028이 바꾸므로, 같은 트리거를 다루는 이 파일이
# 자연스러운 자리다(spec-14-2 Code Map). spec의 I/O & Edge-Case Matrix를 그대로 재현한다.


def _signup(cur, email, meta_role):
    """가입 경로를 재현한다 — auth.users에 INSERT하고 트리거가 만든 profiles 행을 **관측만** 한다.

    conftest._create_user()를 쓰지 않는 이유(Story 14.2 후속 리뷰 2차 지적): 그 헬퍼는 스스로
    role 계약을 단언한다. 그래서 트리거가 깨지면 **픽스처 setup 단계에서** 먼저 터지고, 아래
    매트릭스의 단언은 한 번도 도달하지 못한다 — "독립된 회귀 테스트"라는 주장이 사실이 아니게 되고,
    나중에 헬퍼의 단언을 완화하면 매트릭스는 계속 초록이면서 아무것도 안 지키게 된다.
    여기서는 관측만 하고 판단은 테스트가 한다(헬퍼와 다른 경로여야 '독립'이다).
    """
    user_id = uuid.uuid4()
    if meta_role is None:
        cur.execute(
            "insert into auth.users (id, email, raw_user_meta_data) values (%s, %s, '{}'::jsonb)",
            (user_id, email),
        )
    else:
        cur.execute(
            "insert into auth.users (id, email, raw_user_meta_data) "
            "values (%s, %s, jsonb_build_object('role', %s::text))",
            (user_id, email, meta_role),
        )
    cur.execute("select role, name from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    return user_id, row


@pytest.mark.parametrize(
    "meta_role, expected_role",
    [
        (None, "user"),  # 역할 메타데이터 없음(신규 web 가입) → 기본값 'user'
        # ✎ 정정(Story 17.1, 0033_remove_legacy_role_passthrough.sql, DW-682): 아래 두 행은
        #   0028 시점엔 각각 "buyer"·"seller"가 기대값이었다(그 시점엔 메타데이터를 그대로
        #   반영하는 하위호환 분기가 있었다). 그 분기는 도달 경로가 0이라(Flutter가 16-0에서
        #   role 전송을 멈춤, 웹은 14.2에서 이미 멈춤) 0033이 지웠다 — 이제 무슨 값을 보내도
        #   결과는 항상 'user'다. 이 행들이 "buyer"/"seller"를 기대하면 0033을 되돌린 것과
        #   똑같은 상태에서만 초록이 된다(회귀 가드로 남긴다).
        ("buyer", "user"),  # 레거시 buyer 메타데이터 — 이제 통과하지 않는다(0033)
        ("seller", "user"),  # 레거시 seller 메타데이터 — 이제 통과하지 않는다(0033)
        ("admin", "user"),  # admin 승격 시도 → 강제 차단, 'user'로 배정
        ("whatever", "user"),  # buyer/seller가 아닌 임의 문자열도 'user'로 강제
    ],
)
def test_handle_new_user_default_role_matrix(meta_role, expected_role):
    """0028 → 0033(Story 17.1) 이후 handle_new_user()가 채우는 profiles 행 — spec의 I/O &
    Edge-Case Matrix 전량.

    (건수를 적지 않는다: 옛 문구의 "4행"은 실제 5행일 때 이미 틀려 있었다 — 수치 사본은 늙는다.)

    role만이 아니라 name도 본다. 0028은 함수를 **통째로** replace하면서 0009가 넣은
    `name = split_part(email,'@',1)` 기록을 손으로 다시 옮겨 적었는데, 그 줄을 빼도 통합 테스트
    전량이 초록이었다(실측). name이 사라지면 /admin/members가 `m.name ?? shortId(m.id)` 폴백으로
    조용히 UUID 앞자리를 보여준다 — 화면이 깨지지 않아 더 늦게 발견된다.

    admin 케이스는 신규 가입 경로로 admin이 배정되는 회귀(spec Block If 2행)를 잡는다 —
    여기가 red가 되면 즉시 HALT 대상이다.
    """
    email = f"role-matrix-{uuid.uuid4()}@example.test"
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            _profile_id, (role, name) = _signup(c, email, meta_role)
            assert role == expected_role
            assert name == email.split("@")[0]
        conn.rollback()


def test_handle_new_user_keeps_security_definer_and_pinned_search_path(db):
    """0028이 손으로 다시 적어 넣은 권한 속성이 실제로 붙어 있는가.

    왜 필요한가(실측): 살아 있는 함수에서 `security definer`와 `set search_path`를 떼어내도
    `pytest tests/integration` 100건이 **전부 통과**했고 `check_migrations.py`도 exit 0이었다.
    통합 테스트는 superuser(postgres)로 붙으므로 정의자 권한이 구조적으로 관측되지 않는다 —
    반면 실제 가입은 GoTrue의 supabase_auth_admin이 이 트리거를 돌리고, profiles엔 그 롤용
    INSERT 정책이 없다. 즉 security definer가 빠지면 **가입 자체가 조용히 깨진다**.
    search_path 고정이 빠지면 SECURITY DEFINER 함수는 search_path 탈취면이 된다.

    이 함수는 이미 세 번 재작성됐다(0001 → 0009 → 0028). 형제 트리거 함수는 같은 이유로 이미
    같은 검사를 갖고 있다(test_chat_realtime_broadcast_real_db.py의 broadcast 함수 검사).
    """
    db.execute(
        "select p.prosecdef, p.proconfig from pg_proc p "
        "join pg_namespace n on n.oid = p.pronamespace "
        "where n.nspname = 'public' and p.proname = 'handle_new_user'"
    )
    rows = db.fetchall()
    assert len(rows) == 1, f"public.handle_new_user가 정확히 하나가 아니다: {rows}"
    prosecdef, proconfig = rows[0]
    assert prosecdef is True, "handle_new_user가 security definer가 아니다 — 실제 가입이 깨진다"
    assert proconfig and any(
        setting.lower().replace(" ", "") == "search_path=public" for setting in proconfig
    ), f"handle_new_user에 search_path 고정이 없다: {proconfig}"


def test_signup_trigger_is_still_wired_to_auth_users(db):
    """0028의 `create or replace function`이 0001의 트리거 배선을 그대로 유지했는가.

    함수만 바꾸고 배선은 안 건드리는 것이 0028의 전제인데(주석에 그렇게 적혀 있다), 그 전제를
    확인하는 것이 없었다. 배선이 끊기면 profiles 행 자체가 안 생기고, 그건 FK 때문에 매물·채팅
    전부가 뒤늦게 깨지는 방식으로만 드러난다.
    """
    db.execute(
        "select t.tgname from pg_trigger t "
        "join pg_class c on c.oid = t.tgrelid "
        "join pg_namespace n on n.oid = c.relnamespace "
        "join pg_proc p on p.oid = t.tgfoid "
        "where n.nspname = 'auth' and c.relname = 'users' "
        "and p.proname = 'handle_new_user' and not t.tgisinternal"
    )
    assert db.fetchall(), "auth.users에 handle_new_user를 부르는 트리거가 없다"


def test_admin_signup_metadata_does_not_grant_is_admin():
    """admin metadata로 가입해도 is_admin()은 여전히 false다(Block If 2행의 실제 회귀 재현).

    위 매트릭스 테스트는 profiles.role만 보므로, "role이 'user'로 강제됐다"와 "그래서 관리자
    권한도 없다"는 별개로 확인해야 한다(is_admin()은 role='admin' 정확일치만 본다, 0001).

    **양성 대조를 같은 커넥션에서 함께 돈다**(Story 14.2 후속 리뷰 2차 지적): `set local
    request.jwt.claim.sub`가 안 먹히면 auth.uid()가 NULL → is_admin()이 무조건 false가 되어
    이 검사는 아무것도 안 보면서 영원히 초록이다. 그래서 같은 커넥션·같은 세션 변수로 role만
    'admin'으로 올렸을 때 true가 되는 것을 먼저 확인한다 — 그게 초록이어야 아래 false가 의미를 갖는다.
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            profile_id, (role, _name) = _signup(
                c, f"admin-signup-attempt-{uuid.uuid4()}@example.test", "admin"
            )
            assert role == "user", f"admin metadata가 차단되지 않았다: {role}"
            # SET LOCAL은 파라미터 바인딩을 받지 않는다(실측: `$1`에서 SyntaxError).
            # profile_id는 이 테스트가 만든 uuid라 문자열 합성이 안전하다.
            c.execute(f"set local request.jwt.claim.sub = '{profile_id}'")
            c.execute("select public.is_admin()")
            assert c.fetchone()[0] is False

            # 양성 대조 — 이 세션에서 is_admin()이 애초에 true가 될 수 있는가.
            c.execute("update public.profiles set role = 'admin' where id = %s", (profile_id,))
            c.execute("select public.is_admin()")
            assert c.fetchone()[0] is True, (
                "양성 대조 실패 — request.jwt.claim.sub가 안 먹혀 위 false가 무의미하다"
            )
        conn.rollback()


# --- 아래는 0029(기존 계정 역할 통합)가 추가했다 ---
# `_DATA_MUTATION_ALLOWED`에 0029를 등재하면서 ⑧의 감시가 그 파일에서 걷혔다. 그 자리를
# 비워두면 "예외 등재 = 검사 면제"가 되므로, 아래 두 건이 **그 변경의 경계**를 대신 본다.
# 즉 ⑧이 "바꾸지 마라"를 봤다면, 여기서는 "바꾸되 여기까지만"을 본다.

_MIGRATION_0029 = _MIGRATIONS_DIR / "0029_unify_existing_account_roles.sql"


def _apply_0029(cur):
    cur.execute(_MIGRATION_0029.read_text(encoding="utf-8"))


def test_0029_preserves_admin(db):
    """관리자는 양쪽(profiles.role · metadata) 모두 그대로 남는다.

    왜 이게 경계인가: `is_admin()`(0001)은 `profiles.role = 'admin'` 정확일치를 보고, 앱의
    관리자 차단(main.dart, AR9)은 metadata의 'admin'을 본다. **둘 중 하나만 날아가도**
    관리자 기능이나 모바일 차단이 조용히 깨진다. 0029의 UPDATE 두 문장이 각각 admin을
    제외하는지를 실제 행으로 확인한다.
    """
    admin_id = _create_user(db, f"role-0029-admin-{uuid.uuid4()}@example.test", role="seller")
    # 트리거로는 admin을 만들 수 없으므로(0028) 양쪽 축을 직접 admin으로 맞춘다.
    _set_role(db, admin_id, "admin")
    db.execute(
        "update auth.users set raw_user_meta_data = "
        "jsonb_set(coalesce(raw_user_meta_data, '{}'::jsonb), '{role}', '\"admin\"') where id = %s",
        (admin_id,),
    )

    _apply_0029(db)

    db.execute("select role from public.profiles where id = %s", (admin_id,))
    assert db.fetchone()[0] == "admin", "0029가 admin의 profiles.role을 지웠다 — is_admin()이 깨진다"
    db.execute("select raw_user_meta_data ->> 'role' from auth.users where id = %s", (admin_id,))
    assert db.fetchone()[0] == "admin", "0029가 admin의 metadata role을 지웠다 — 앱 관리자 차단이 깨진다"


def test_0029_unifies_non_admin_and_is_idempotent(db):
    """비관리자는 양쪽 축이 정리되고, **재적용해도 같은 결과**다.

    멱등을 보는 이유: 이 마이그는 일회성 데이터 정리라 사고 복구·환경 재구성 과정에서 두 번
    돌 수 있다. 두 번째 실행이 실패하거나 값을 또 바꾸면 그때 원인을 찾기 어렵다.
    """
    user_id = _create_user(db, f"role-0029-user-{uuid.uuid4()}@example.test", role="seller")
    db.execute("select role from public.profiles where id = %s", (user_id,))
    assert db.fetchone()[0] == "seller", "전제 실패 — 이 검사는 옛 역할을 가진 행으로 시작해야 한다"

    _apply_0029(db)
    db.execute(
        "select p.role, u.raw_user_meta_data ? 'role' "
        "from public.profiles p join auth.users u on u.id = p.id where p.id = %s",
        (user_id,),
    )
    role_after, meta_has_role = db.fetchone()
    assert role_after == "user", f"비관리자 role이 통일되지 않았다: {role_after!r}"
    assert meta_has_role is False, "비관리자 metadata에 role이 남았다 — 앱 쪽 사본이 안 지워졌다"

    _apply_0029(db)  # 두 번째 적용 — 사후조건 블록까지 다시 돈다
    db.execute("select role from public.profiles where id = %s", (user_id,))
    assert db.fetchone()[0] == "user", "재적용이 값을 또 바꿨다 — 멱등하지 않다"
