"""마이그레이션이 기존 채팅 메시지를 **소급 방송**하지 않는지 정적으로 확인한다
(Story 12.2, I/O 매트릭스 3행 / 스펙 Never 절).

왜 DB 없이 도는 자리에 있나:
  이 검사는 마이그레이션 파일의 **텍스트만** 읽는다. 원래는 실DB 통합 테스트 파일 안에 있었는데,
  그 파일은 `TEST_DATABASE_URL` skip 가드를 모듈 전체에 걸고 있어서 **DB가 없으면 이 검사까지 함께
  건너뛰었다**(실측: 환경변수 없이 돌리면 9 skipped — 이 검사 포함). 소급 방송을 막는 유일한
  가드가 CI의 api-db 잡에서만 돌고 개발자 로컬에선 존재하지 않는 셈이라, DB가 필요 없는 자리로
  옮겼다. 이제 `api` 잡(DB 없는 pytest)에서도 돈다.

무엇을 보나:
  트리거가 AFTER INSERT라는 것 자체가 "생성 이후의 INSERT에만 반응"을 이미 보장한다(Postgres
  실행 모델). 이 검사가 잡는 것은 그다음 회귀다 — **누군가 나중에 마이그레이션에 과거 메시지를
  다시 흘려보내는 문장을 추가하는 것**. 그래서 방송을 만들 수 있는 두 종류를 다 본다:
    ⓐ `realtime.messages`/`chat_messages`를 직접 건드리는 데이터 조작문(INSERT/UPDATE/MERGE/COPY)
    ⓑ 방송 함수(`realtime.send`/`realtime.broadcast_changes`)를 **트리거 함수 본문 밖에서** 호출
  ⓑ를 넣은 이유: 실제로 소급 방송을 쓰려면 가장 자연스러운 형태가
  `select realtime.send(...) from public.chat_messages` 인데, 처음 정규식은 ⓐ만 봐서 이 형태를
  통째로 놓쳤다(2026-07-28 후속 리뷰가 실측 — 그 문장을 실제로 돌리니 방송 0건 → 2건이 됐다).

무엇을 못 보나: 문장이 **있는지**만 본다. 그 문장이 실행되면 실제로 무슨 일이 일어나는지는 보지
  않는다. 또 검사 대상은 `supabase/migrations/*.sql` 중 0023 이후 번호뿐이다 — 0022 이하는 트리거
  자체가 없던 시절이라 소급 방송이라는 개념이 성립하지 않고, **마이그레이션 파일 밖**(일회용
  `scripts/` SQL·`api/` 앱 코드·원격에 손으로 실행하는 문장)은 아예 시야 밖이다. 이 검사가 초록인
  것은 "소급 방송이 불가능하다"가 아니라 "마이그레이션 파일에는 그 문장이 없다"만 뜻한다.
  `update public.chat_messages`도 보지 않는다 — 트리거가 AFTER **INSERT**뿐이라 UPDATE로는 방송이
  나갈 수 없고, 나중에 UPDATE가 방송에 배선되는 회귀는 실DB 쪽 ⑥
  (`test_chat_realtime_broadcast_real_db.py`)이 `pg_get_triggerdef`로 잡는다. 여기서까지 막으면
  새 컬럼을 채우는 정상 마이그(CLAUDE.md B3의 additive 백필)가 게이트를 red로 만든다.
"""

import re
from pathlib import Path

_MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "supabase" / "migrations"

# 0023(트리거 도입)부터 검사한다. 그 이전 번호는 방송 자체가 존재하지 않았다.
_FIRST_GUARDED_NUMBER = 23

# 스키마 접두어는 선택적이고 공백·따옴표를 허용한다 — `insert into realtime . "messages"` 같은
# 형태로 우회되면 안 된다. `only`(UPDATE ONLY)도 받는다.
_QUALIFIED = r'(?:"?{schema}"?\s*\.\s*)?"?{table}"?'
# realtime.messages는 쓰기 전부를 본다(행을 만드는 것도, 이미 나간 방송을 조작하는 것도 금지).
_DML_WRITE = r"(?:insert\s+into|update|merge\s+into|copy)\s+(?:only\s+)?"
# chat_messages는 **행을 만드는 문장만** 본다 — 트리거가 AFTER INSERT뿐이라 UPDATE로는 방송이
# 나갈 수 없고, 그것까지 막으면 새 컬럼을 채우는 정상 마이그가 걸린다(위 docstring 참조).
_DML_INSERTING = r"(?:insert\s+into|merge\s+into|copy)\s+(?:only\s+)?"
_FORBIDDEN = re.compile(
    _DML_WRITE + _QUALIFIED.format(schema="realtime", table="messages")
    + r"\b|" + _DML_INSERTING + _QUALIFIED.format(schema="public", table="chat_messages") + r"\b"
    # 방송 함수를 직접 부르는 형태(select/perform/do 블록 어디서든)
    + r"|realtime\s*\.\s*(?:send|broadcast_changes)\s*\(",
    re.IGNORECASE,
)

# 함수 **정의**의 본문만 들어낸다. 꼬리표($fn$ 등)를 붙인 달러 인용도 같은 꼬리표로 닫히는 데까지
# 짝지어 지운다(역참조 \1).
_FUNCTION_BODY = re.compile(
    r"create\s+(?:or\s+replace\s+)?function\b.*?\$(\w*)\$.*?\$\1\$",
    re.DOTALL | re.IGNORECASE,
)


def _strip_sql_comments(sql: str) -> str:
    """`--` 줄 주석과 `/* */` 블록 주석을 지운다.

    필요한 이유: 이 파일들은 주석이 본문보다 길다. 주석 안의 설명 문장(예: "…chat_messages를
    update하지 않는다")이 금지 패턴에 걸리면 **문서를 고쳤을 뿐인데 게이트가 red**가 된다.
    거짓 양성은 거짓 음성만큼이나 빨리 검사를 무력화시킨다(사람들이 무시하기 시작한다)."""
    return re.sub(r"--[^\n]*|/\*.*?\*/", "", sql, flags=re.DOTALL)


def _strip_function_bodies(sql: str) -> str:
    """`create [or replace] function ... as $태그$ ... $태그$` 의 **본문만** 들어낸다.

    왜 이 모양이어야 하나(2026-07-28 3차 리뷰가 양방향 실측): 이전 구현은 `$$...$$`를 무조건
    지웠는데, 그건 함수 정의만 지우는 게 아니라 **`do $$ ... $$` 익명 블록도 통째로 지웠다**.
    그래서 소급 방송을 쓰는 가장 자연스러운 두 형태
    (`do $$ begin perform realtime.send(...) from public.chat_messages m; end $$;`,
    `do $$ begin insert into realtime.messages ...; end $$;`)가 **가드를 그냥 통과했다**(실측).
    반대 방향도 깨져 있었다 — 함수 본문을 `$fn$...$fn$`처럼 꼬리표로 감싸면 안 지워져서
    **정상 트리거 함수가 위반으로 걸렸다**(거짓 양성, 실측).

    함수 본문을 제외하는 이유 자체는 그대로다: 본문 안의 `perform realtime.broadcast_changes(...)`는
    소급 방송이 아니라 이 기능 자체이고, 소급 방송은 본문 **밖**의 실행 문장으로 일어난다."""
    return _FUNCTION_BODY.sub(" ", sql)


def _offending_match(sql: str):
    """실제 검사 파이프라인. **파일 검사와 자기검사가 반드시 같은 것을 통과하게** 하나로 묶었다.

    이전엔 파일 검사만 `$$` 제거를 했고 자기검사(`test_guard_actually_catches_a_backfill`)는 그
    단계 없이 정규식만 돌렸다 — 즉 "가드가 잡는다"는 확인이 **실제로 도는 적 없는 경로**를 상대로
    이뤄졌고, 그래서 위의 `do $$` 사각지대를 자기검사가 스스로 보지 못했다(B4)."""
    return _FORBIDDEN.search(_strip_function_bodies(_strip_sql_comments(sql)))


def _guarded_migration_files():
    files = []
    for path in sorted(_MIGRATIONS_DIR.glob("*.sql")):
        match = re.match(r"(\d+)_", path.name)
        if match and int(match.group(1)) >= _FIRST_GUARDED_NUMBER:
            files.append(path)
    return files


def test_migrations_dir_is_findable():
    """경로 계산(`parents[2]`)이 깨지면 아래 검사가 '파일 0개라 통과'로 조용히 무력화된다 —
    그 상태를 통과가 아니라 실패로 만든다."""
    assert _MIGRATIONS_DIR.is_dir(), f"마이그레이션 디렉터리를 찾지 못했다: {_MIGRATIONS_DIR}"
    assert _guarded_migration_files(), (
        f"{_FIRST_GUARDED_NUMBER:04d} 이상 번호의 마이그레이션이 하나도 없다 — 경로/번호 규칙이 "
        f"바뀌었는지 확인할 것: {_MIGRATIONS_DIR}"
    )


def test_no_retroactive_broadcast_statement():
    """0023 이후 마이그레이션 어디에도 기존 메시지를 소급 방송할 수 있는 문장이 없다.

    트리거 함수 본문 안의 `perform realtime.broadcast_changes(...)`는 제외한다 — 그건 소급 방송이
    아니라 이 기능 자체다(`_strip_function_bodies` 참조)."""
    offenders = []
    for path in _guarded_migration_files():
        match = _offending_match(path.read_text(encoding="utf-8"))
        if match:
            offenders.append(f"{path.name}: {match.group(0).strip()}")

    assert not offenders, (
        "마이그레이션이 기존 chat_messages를 소급 방송할 수 있는 문장을 포함한다 — "
        "이 트리거 이후의 신규 INSERT만 방송해야 한다(스펙 Never 절): " + "; ".join(offenders)
    )


def test_guard_actually_catches_a_backfill():
    """가드가 **잡는다**는 것을 확인한다(만들었다가 아니라 잡는다가 완료, CLAUDE.md B4).

    실제로 놓쳤던 형태를 포함해 대표적인 소급 방송 문장들을 넣어보고 전부 걸리는지 본다.
    **파일 검사와 똑같은 `_offending_match`를 쓴다** — 이전엔 여기서만 정규식을 직접 불러
    `$$` 제거 단계를 건너뛰었고, 그래서 아래 `do $$` 두 형태의 사각지대를 스스로 보지 못했다."""
    should_catch = [
        "insert into realtime.messages (topic, payload) select 1;",
        'insert into "realtime" . "messages" (topic) values (1);',
        "update realtime.messages set payload = '{}'::jsonb;",
        "merge into public.chat_messages using x on true;",
        "copy realtime.messages from stdin;",
        # 1차 정규식이 통째로 놓쳤던 형태 — 실측으로 소급 방송이 실제 발생함을 확인한 것
        "select realtime.send(jsonb_build_object('record', to_jsonb(m)), 'INSERT', "
        "'chat:room:' || m.room_id::text) from public.chat_messages m;",
        # 2차 구현($$ 무조건 제거)이 놓쳤던 형태 — 익명 블록은 함수 정의가 아니라 **실행문**이다.
        "do $$ begin perform realtime.send(jsonb_build_object('record', to_jsonb(m)), 'INSERT', "
        "'chat:room:' || m.room_id::text) from public.chat_messages m; end $$;",
        "do $$ begin insert into realtime.messages (topic) select 1; end $$;",
        "do $x$ begin perform realtime.broadcast_changes('t','INSERT','INSERT','a','b',null,null); end $x$;",
    ]
    for statement in should_catch:
        assert _offending_match(statement), f"가드가 놓쳤다: {statement}"

    should_not_catch = [
        "-- update public.chat_messages 하지 않는다는 설명 주석",
        "/* insert into realtime.messages 를 언급하는 블록 주석 */",
        "create trigger t after insert on public.chat_messages for each row execute function f();",
        "drop policy if exists p on realtime.messages;",
        # 이 기능 자체 — 트리거 함수 본문의 방송 호출. 꼬리표 없는 것과 붙은 것 **둘 다** 정상이어야
        # 한다(2차 구현은 꼬리표가 붙으면 본문을 못 지워 정상 마이그를 red로 만들었다).
        "create or replace function f() returns trigger language plpgsql as "
        "$$ begin perform realtime.broadcast_changes('t','I','I','a','b',new,old); end $$;",
        "create or replace function f() returns trigger language plpgsql as "
        "$fn$ begin perform realtime.broadcast_changes('t','I','I','a','b',new,old); end $fn$;",
        # 새 nullable 컬럼을 채우는 정상 백필(CLAUDE.md B3) — UPDATE로는 방송이 나갈 수 없다.
        "update public.chat_messages set read_at = now() where read_at is null;",
    ]
    for statement in should_not_catch:
        assert not _offending_match(statement), f"거짓 양성: {statement}"
