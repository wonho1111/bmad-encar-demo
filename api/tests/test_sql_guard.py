"""sql_guard 단위 테스트 — CM2(위험·범위밖 쿼리 실행 전 차단)의 핵심 증명.

네트워크·DB 무관 순수 로직이라 키 없이도 항상 돈다. LLM이 어떤 SQL을 만들든 가드가
결정론적으로 같은 판정을 내리는지 검증한다(함정 #1).
"""

import pytest

from app.db.sql_guard import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    SqlGuardError,
    validate_select_sql,
)

# 가드를 통과해야 하는 정상 SELECT(7필드·status='on_sale' 포함).
_GOOD = (
    "SELECT id, manufacturer, model, year, price, mileage, region "
    "FROM listings WHERE status = 'on_sale' AND color = '흰색' "
    "AND body_type = 'SUV' AND price <= 30000000"
)


def _code(sql: str) -> str:
    """validate_select_sql이 던지는 SqlGuardError의 code를 돌려준다(없으면 실패)."""
    with pytest.raises(SqlGuardError) as exc_info:
        validate_select_sql(sql)
    return exc_info.value.code


# ── 통과 케이스 ────────────────────────────────────────────────────
def test_valid_select_passes_and_injects_limit():
    out = validate_select_sql(_GOOD)
    # LIMIT가 없었으므로 기본 LIMIT가 주입돼야 한다.
    assert f"LIMIT {DEFAULT_LIMIT}" in out
    assert out.lower().startswith("select id")


def test_existing_limit_within_cap_preserved():
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT 10"
    out = validate_select_sql(sql)
    assert "LIMIT 10" in out
    assert "LIMIT 50" not in out  # 중복 주입 없음


# ── SELECT 외 구문 거부 ────────────────────────────────────────────
@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM listings WHERE id = '1'",
        "UPDATE listings SET price = 0 WHERE status='on_sale'",
        "INSERT INTO listings (id) VALUES ('x')",
        "DROP TABLE listings",
        "ALTER TABLE listings ADD COLUMN x int",
        "TRUNCATE listings",
    ],
)
def test_non_select_rejected(sql):
    # not_select 또는 forbidden_keyword 중 하나로 차단되면 된다(실행 전 차단이 핵심).
    assert _code(sql) in {"not_select", "forbidden_keyword", "missing_status_filter", "no_table"}


# ── 다중 문장·주석 거부 ────────────────────────────────────────────
def test_stacked_statements_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale'; DROP TABLE listings"
    assert _code(sql) == "multiple_statements"


def test_line_comment_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale' -- 주석"
    assert _code(sql) == "comment_not_allowed"


def test_block_comment_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale' /* x */"
    assert _code(sql) == "comment_not_allowed"


# ── 비화이트리스트 테이블·컬럼 거부 ────────────────────────────────
def test_forbidden_table_rejected():
    sql = "SELECT id FROM profiles WHERE status='on_sale'"
    assert _code(sql) == "forbidden_table"


def test_subquery_other_table_rejected():
    sql = (
        "SELECT id FROM listings WHERE status='on_sale' "
        "AND seller_id IN (SELECT id FROM profiles)"
    )
    # 서브쿼리 금지(코드리뷰 High) — 또는 profiles 테이블/환각 컬럼으로도 차단된다.
    assert _code(sql) in {"subquery_not_allowed", "forbidden_table", "forbidden_column"}


def test_subquery_same_table_rejected():
    # 서브쿼리 내부 LIMIT이 외부 상한 검사를 가리는 우회(코드리뷰 High) — 중첩 SELECT 자체를 거부.
    sql = (
        "SELECT id, manufacturer, model, year, price, mileage, region "
        "FROM listings WHERE status='on_sale' "
        "AND year IN (SELECT year FROM listings LIMIT 50)"
    )
    assert _code(sql) == "subquery_not_allowed"


# ── OR 금지: status='on_sale' 무력화로 sold 누출 차단(FR11, 코드리뷰 Critical) ──
def test_or_rejected():
    sql = (
        "SELECT id, manufacturer, model, year, price, mileage, region "
        "FROM listings WHERE status = 'on_sale' OR price < 99999999"
    )
    assert _code(sql) == "forbidden_or"


# ── 문자열 리터럴 안의 키워드는 오탐 차단하지 않는다(코드리뷰 Medium) ──
def test_keyword_inside_literal_passes():
    # model 값에 'DROP'이 들어가도 정상 SELECT로 통과해야 한다(리터럴 제거 후 검사).
    sql = "SELECT id, model FROM listings WHERE status='on_sale' AND model = 'DROP'"
    out = validate_select_sql(sql)
    assert f"LIMIT {DEFAULT_LIMIT}" in out


def test_hallucinated_column_rejected():
    sql = "SELECT password FROM listings WHERE status='on_sale'"
    assert _code(sql) == "forbidden_column"


def test_select_star_rejected():
    sql = "SELECT * FROM listings WHERE status='on_sale'"
    assert _code(sql) == "select_star"


# ── FR11: status='on_sale' 누락 거부 ──────────────────────────────
def test_missing_status_filter_rejected():
    sql = "SELECT id FROM listings WHERE color='흰색'"
    assert _code(sql) == "missing_status_filter"


def test_sold_filter_does_not_satisfy():
    # status='sold'만 있으면 on_sale 필터가 아니므로 거부(sold 비노출).
    sql = "SELECT id FROM listings WHERE status='sold'"
    assert _code(sql) == "missing_status_filter"


# ── LIMIT 상한 ─────────────────────────────────────────────────────
def test_limit_over_cap_rejected():
    sql = f"SELECT id FROM listings WHERE status='on_sale' LIMIT {MAX_LIMIT + 1}"
    assert _code(sql) == "limit_exceeded"


def test_limit_at_cap_passes():
    sql = f"SELECT id FROM listings WHERE status='on_sale' LIMIT {MAX_LIMIT}"
    out = validate_select_sql(sql)
    assert f"LIMIT {MAX_LIMIT}" in out


# ── 빈 입력 ────────────────────────────────────────────────────────
def test_empty_rejected():
    assert _code("   ") == "empty"
