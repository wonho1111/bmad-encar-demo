"""handle_new_user()의 이름 결정 — 이메일 없는 OAuth(카카오) 가입에도 name이 채워지는가
(Story 18.1 AC2, 0040_handle_new_user_oauth_name.sql).

왜 이 파일이 따로 있나:
  0033까지의 계약은 `name = split_part(email, '@', 1)` 하나뿐이었다 — email이 NULL이면
  name도 NULL이다. 카카오 로그인은 이메일 동의항목이 "권한 없음"인 기본 앱으로는 이메일을
  아예 안 주므로(스토리 Dev Notes 실측), 이 경로를 실제로 재현하지 않으면 "카카오 가입은
  이름이 빈다"는 회귀가 어떤 기존 검사에도 걸리지 않는다(기존 role-matrix 검사는 전부
  email이 있는 가입만 다룬다).

무엇을 보나 (spec 없이 AC2 문구를 그대로 I/O 매트릭스로 삼는다):
  ① email 없음 + metadata.name 있음(카카오 실제 계약, kakao.go 확인) → name = metadata.name
  ② email 있음(기존 이메일 가입) → metadata에 name이 같이 있어도 **여전히 이메일 앞부분이 이긴다**
     (0040은 email 우선순위를 email → name → nickname → full_name → '회원' 순으로만 두므로
     기존 이메일·비밀번호 가입 동작은 절대 안 바뀌어야 한다 — 0040의 존재 이유가 딱 이 비회귀다)
  ③ email도 metadata도 전부 없음 → name = '회원'(마지막 폴백)
  ④ 0040을 이미 적용한 DB에 다시 적용해도(forward-only) 기존 행의 name이 바뀌지 않는다

무엇을 **못 보나**:
  · raw_user_meta_data->>'nickname' 키 자체가 실제로 쓰이는지는 못 본다 — 2026-09-29 확인한
    Supabase Auth의 Kakao provider(internal/api/provider/kakao.go)는 그 키를 채우지 않고
    name·full_name·preferred_username·user_name에 같은 닉네임 값을 넣는다. 이 폴백은 다른
    OAuth 공급자가 그 키를 쓸 가능성에 대비한 것이라 카카오 실사용 경로로는 검증되지 않는다.
  · 실제 카카오 동의 화면을 통한 E2E(T5)는 사용자가 직접 수동으로 확인한다 — 여기는 트리거
    로직만 auth.users에 직접 INSERT해 재현한다.

실행: CI의 api-db 잡. 로컬: TEST_DATABASE_URL='postgresql://postgres:postgres@127.0.0.1:5432/postgres'
  없으면 skip(거짓 통과 금지).
"""

import uuid
from pathlib import Path

import psycopg

from conftest import _DSN, pytestmark  # noqa: F401 — pytestmark는 skip 마커

_MIGRATIONS_DIR = Path(__file__).resolve().parents[3] / "supabase" / "migrations"
_MIGRATION_0040 = _MIGRATIONS_DIR / "0040_handle_new_user_oauth_name.sql"


def _apply_0040(cur):
    cur.execute(_MIGRATION_0040.read_text(encoding="utf-8"))


def _signup(cur, *, email, metadata):
    """가입 경로를 재현한다 — auth.users에 INSERT하고 트리거가 만든 profiles.name만 관측한다.

    conftest._create_user()를 쓰지 않는 이유: 그 헬퍼는 email을 필수 인자로 받고 role 계약만
    단언한다. 여기서는 email=NULL(카카오 무이메일)을 직접 다뤄야 해서 최소 형태로 새로 쓴다
    (test_role_check_relax_real_db.py의 _signup과 같은 이유 — 헬퍼와 다른 경로여야 독립적이다).
    """
    user_id = uuid.uuid4()
    cur.execute(
        "insert into auth.users (id, email, raw_user_meta_data) values (%s, %s, %s::jsonb)",
        (user_id, email, metadata),
    )
    cur.execute("select name from public.profiles where id = %s", (user_id,))
    row = cur.fetchone()
    assert row is not None, "가입 트리거가 profiles 행을 만들지 않았다"
    return user_id, row[0]


def test_no_email_uses_kakao_nickname_metadata():
    """① 이메일 없음 + metadata.name(카카오 닉네임 실제 계약) → name = 그 값(AC2 핵심)."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            _user_id, name = _signup(
                c, email=None, metadata='{"name": "카카오유저"}'
            )
            assert name == "카카오유저"
        conn.rollback()


def test_email_still_wins_over_metadata_name():
    """② 기존 이메일 가입 동작 무회귀 — metadata.name이 있어도 이메일 앞부분이 이긴다."""
    email = f"oauth-name-email-wins-{uuid.uuid4()}@example.test"
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            _user_id, name = _signup(c, email=email, metadata='{"name": "무시되어야함"}')
            assert name == email.split("@")[0]
        conn.rollback()


def test_no_email_and_no_metadata_falls_back_to_default_name():
    """③ 이메일도 카카오 닉네임도 전부 없으면 마지막 폴백 '회원'을 쓴다."""
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            _user_id, name = _signup(c, email=None, metadata="{}")
            assert name == "회원"
        conn.rollback()


def test_applying_migration_does_not_touch_existing_rows():
    """④ 0040을 이미 적용한 DB에 다시 적용해도(forward-only) 기존 행의 name이 그대로다.

    CI DB는 늘 0001부터 새로 만들어지므로 "이미 적용된 상태에 한 번 더 적용"하는 순간은
    재현된 적이 없다 — 0027 파일의 ⑥과 같은 이유로 여기서 직접 재현한다.
    """
    email = f"oauth-name-reapply-{uuid.uuid4()}@example.test"
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            _user_id, name_before = _signup(c, email=email, metadata='{"name": "재적용전"}')
            assert name_before == email.split("@")[0]

            _apply_0040(c)

            c.execute("select name from public.profiles where id = %s", (_user_id,))
            name_after = c.fetchone()[0]
            assert name_after == name_before, "0040 재적용이 기존 행의 name을 바꿨다 — forward-only 위반"
        conn.rollback()
