"""신뢰속성 CHECK 제약 실DB 검증 — Postgres가 **실제로** 도메인 밖 값을 거르는가 (Story 10.1).

왜 이 파일이 따로 있나:
  0017이 만든 `accident_status`의 허용값 3개는 **CHECK 제약 하나**로만 지켜진다. 그 제약이
  실제로 거르는지는 문자열 검사나 가짜 DB로는 못 본다 — 마이그레이션 SQL에 `check (...)`
  라는 글자가 있는 것과, Postgres가 INSERT를 거부하는 것은 다른 사실이다(CLAUDE.md B4
  "존재 확인은 작동 확인이 아니다"). 그래서 진짜 Postgres에 붙는 이 층이 필요하다.

무엇을 증명하나 (spec의 I/O 매트릭스 DB 층 4행):
  ① 허용 3값은 저장된다 ② 도메인 밖 값은 SQLSTATE 23514로 거부된다
  ③ 미입력(생략)은 NULL로 저장된다(제3상태) ④ 신규 3컬럼은 nullable이라 기존 행을 막지 않는다

무엇을 **못 보나** (실측으로 확인한 CHECK의 사각지대 — 마이그 주석·대장과 같은 내용):
  · 마이그레이션 **이전에 이미 들어간 행** — CHECK는 신규/변경 행에만 걸린다.
  · `accident_free`와의 **논리적 모순**(`accident_free=true` + `accident_status='사고'`)은
    두 컬럼을 함께 보는 제약이 없어 그대로 통과한다. 아래 test_check_does_not_see_*가
    그 사실을 **의도적으로 초록으로** 못박는다(모르는 것과 알고 두는 것은 다르다).

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

_CHECK_VIOLATION = "23514"

# accident_status를 뺀 나머지 필수 컬럼 — 0002의 NOT NULL·CHECK를 모두 만족하는 최소 조합.
_BASE_COLS = (
    "id, seller_id, status, manufacturer, model, body_type, year, price, mileage, "
    "color, fuel, transmission, displacement, seats, region"
)
_BASE_VALS = (
    "%s, %s, 'on_sale', '현대', '싼타페', '중형차', 2020, 26700000, 62000, "
    "'흰색', '가솔린', '자동', 1998, 5, '서울'"
)


@pytest.fixture
def seeded():
    """트랜잭션 안에서 `(cursor, seller_id)`를 돌려주고 **끝나면 롤백**한다(DB 원상복구).

    ✎ 2026-07-22 코드리뷰(P10) — 전역 `_SELLER[cur]` 제거: 예전엔 seller_id를 모듈 전역
    딕셔너리에 커서 객체를 키로 담아 전달했다. 동작은 했지만 "왜 커서를 키로 쓰는가"가
    코드만 봐서는 안 드러났고, 테스트 함수가 눈에 안 보이는 전역에 의존하게 만들었다.
    픽스처가 필요한 값을 그냥 함께 반환하면 전역 자체가 필요 없다.
    """
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            # listings.seller_id는 profiles를 참조한다. 시드가 있으면 그걸 쓰고,
            # 없으면(= CI의 빈 컨테이너) 트랜잭션 안에서 직접 만든다.
            # ⚠️ skip으로 처리하면 CI에서 이 파일 전체가 **조용히 통과**한다 — 마이그레이션만
            #    적용된 빈 DB엔 profiles가 없기 때문이다. 거짓 통과 금지(CLAUDE.md B4).
            c.execute("select id from public.profiles limit 1")
            row = c.fetchone()
            if row is None:
                seller_id = str(uuid.uuid4())
                # 0001의 가입 트리거가 auth.users INSERT를 받아 profiles 행을 만든다.
                c.execute(
                    "insert into auth.users (id, email, raw_user_meta_data) "
                    "values (%s, 'trust-test@example.com', '{\"role\":\"seller\"}'::jsonb)",
                    (seller_id,),
                )
                c.execute("select id from public.profiles where id = %s", (seller_id,))
                assert c.fetchone() is not None, "가입 트리거가 profiles 행을 만들지 않았다"
                row = (seller_id,)
            yield c, row[0]
        conn.rollback()


def _insert(cur, seller_id, accident_status=None, *, omit=False):
    listing_id = str(uuid.uuid4())
    if omit:
        cur.execute(
            f"insert into public.listings ({_BASE_COLS}) values ({_BASE_VALS})",
            (listing_id, seller_id),
        )
    else:
        cur.execute(
            f"insert into public.listings ({_BASE_COLS}, accident_status) "
            f"values ({_BASE_VALS}, %s)",
            (listing_id, seller_id, accident_status),
        )
    return listing_id


@pytest.mark.parametrize("value", ["무사고", "단순교환", "사고"])
def test_allowed_values_are_stored(seeded, value):
    """① 허용 3값은 그대로 저장된다."""
    cur, seller_id = seeded
    listing_id = _insert(cur, seller_id, value)
    cur.execute("select accident_status from public.listings where id = %s", (listing_id,))
    assert cur.fetchone()[0] == value


@pytest.mark.parametrize("value", ["외판교환", "무사고 ", "accident_free", ""])
def test_out_of_domain_value_is_rejected(seeded, value):
    """② 도메인 밖 값은 CHECK 위반(23514)으로 거부된다 — 검사가 실제로 '잡는' 것을 증명.

    ✎ 2026-07-22 코드리뷰(P10) — 실패할 INSERT를 **SAVEPOINT**(`conn.transaction()`)로 감싼다.
    예전엔 실패 후 `cur.connection.rollback()`으로 **트랜잭션 전체**를 되돌렸는데, 그러면
    `seeded` 픽스처가 미리 심어 둔 auth.users/profiles 행까지 함께 사라진다. 지금은 이 테스트가
    그 뒤에 아무 것도 안 해서 무해했지만, 여기에 단언을 하나만 더 붙이면 "판매자가 없다"는
    엉뚱한 FK 오류로 실패했을 것이다. `conn.transaction()`은 이미 트랜잭션 안이면 SAVEPOINT를
    만들어 **이 INSERT 한 문장만** 되돌리고, 바깥 트랜잭션(셀러 행)은 그대로 살려 둔다.
    """
    cur, seller_id = seeded
    with pytest.raises(psycopg.errors.CheckViolation) as exc:
        with cur.connection.transaction():
            _insert(cur, seller_id, value)
    assert exc.value.sqlstate == _CHECK_VIOLATION


def test_omitted_value_is_null_third_state(seeded):
    """③ 미입력(컬럼 생략)은 NULL로 저장된다 — '무사고 아님'이 아니라 제3상태."""
    cur, seller_id = seeded
    listing_id = _insert(cur, seller_id, omit=True)
    cur.execute(
        "select accident_status, is_single_owner, is_non_smoker "
        "from public.listings where id = %s",
        (listing_id,),
    )
    assert cur.fetchone() == (None, None, None)


def test_new_columns_are_nullable(seeded):
    """④ 신규 3컬럼이 전부 nullable이다 — 기존 행이 NULL인 채로 남을 수 있는 근거."""
    cur, _seller_id = seeded
    cur.execute(
        "select column_name, is_nullable from information_schema.columns "
        "where table_schema = 'public' and table_name = 'listings' "
        "and column_name in ('accident_status', 'is_single_owner', 'is_non_smoker') "
        "order by column_name"
    )
    assert cur.fetchall() == [
        ("accident_status", "YES"),
        ("is_non_smoker", "YES"),
        ("is_single_owner", "YES"),
    ]


def test_new_columns_have_no_default_so_existing_rows_were_untouched(seeded):
    """④-b 기존 행이 NULL로 남는 **구조적 근거**: 신규 3컬럼에 DEFAULT가 없다.

    "기존 100건이 NULL이다"는 마이그 적용 시점의 1회성 사실이라 테스트로 재현할 수 없다
    (실측은 별도로 기록했다: 103건 전량 NULL·accident_free NULL 0건). 대신 그 사실이
    **성립할 수밖에 없는 조건**을 여기서 못박는다 — DEFAULT가 없으면 `add column`은
    기존 행에 아무 값도 쓰지 않는다. 누가 나중에 DEFAULT를 붙이면 여기가 red가 된다.
    `accident_free`가 원래 계약(NOT NULL·default true)을 유지하는지도 함께 본다.
    """
    cur, _seller_id = seeded
    cur.execute(
        "select column_name, column_default, is_nullable from information_schema.columns "
        "where table_schema = 'public' and table_name = 'listings' "
        "and column_name in ('accident_status', 'is_single_owner', 'is_non_smoker', "
        "'accident_free') order by column_name"
    )
    rows = dict((name, (default, nullable)) for name, default, nullable in cur.fetchall())

    for col in ("accident_status", "is_single_owner", "is_non_smoker"):
        assert rows[col] == (None, "YES"), f"{col}에 DEFAULT가 생겼거나 NOT NULL이 됐다"
    # 기존 컬럼은 드롭·변경 금지(additive) — 계약이 그대로인지 확인.
    assert rows["accident_free"] == ("true", "NO")


def test_check_does_not_see_contradiction_with_accident_free(seeded):
    """이 검사가 **안 보는 것**: accident_free=true + accident_status='사고' 모순은 통과한다.

    두 컬럼을 함께 보는 제약이 없기 때문이다. 지금은 의도적으로 두는 선택이다 —
    `accident_free`는 기존 15필드 쓰기 경로가, `accident_status`는 아직 쓰기 경로가
    없어(대장 참조) 둘이 동시에 채워질 자리가 없다. 쓰기 UI가 생기는 시점에 다시 판단한다.
    이 테스트가 red가 되면 그건 회귀가 아니라 **정책이 바뀐 것**이므로 함께 갱신한다.
    """
    cur, seller_id = seeded
    listing_id = _insert(cur, seller_id, "사고")
    cur.execute(
        "select accident_free, accident_status from public.listings where id = %s",
        (listing_id,),
    )
    assert cur.fetchone() == (True, "사고")  # 모순인데도 저장됨 — 확인된 사각지대
