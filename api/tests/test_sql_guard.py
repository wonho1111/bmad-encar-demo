"""sql_guard 단위 테스트 — CM2(위험·범위밖 쿼리 실행 전 차단)의 핵심 증명.

네트워크·DB 무관 순수 로직이라 키 없이도 항상 돈다. LLM이 어떤 SQL을 만들든 가드가
결정론적으로 같은 판정을 내리는지 검증한다(함정 #1).
"""

import pytest

from app.db.sql_guard import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    MAX_OFFSET,
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


# ── LIMIT 음수·0 거부 (코드리뷰 후속: 이중 LIMIT 버그) ─────────────
def test_negative_limit_rejected():
    # 예전엔 음수가 "LIMIT 없음"으로 오인돼 `LIMIT -1 LIMIT 5`라는 실행 불가 SQL이 나왔다.
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT -1"
    assert _code(sql) == "limit_invalid"


def test_zero_limit_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT 0"
    assert _code(sql) == "limit_invalid"


# ── OFFSET 상한 (코드리뷰 후속: OFFSET 무상한 버그) ────────────────
def test_offset_within_cap_passes():
    # 정상 페이지네이션(LIMIT 5 OFFSET 10)은 과차단 없이 통과해야 한다.
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT 5 OFFSET 10"
    out = validate_select_sql(sql)
    assert "OFFSET 10" in out
    assert "LIMIT 5" in out


def test_offset_at_cap_passes():
    sql = f"SELECT id FROM listings WHERE status='on_sale' LIMIT 5 OFFSET {MAX_OFFSET}"
    out = validate_select_sql(sql)
    assert f"OFFSET {MAX_OFFSET}" in out


def test_excessive_offset_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT 5 OFFSET 999999"
    assert _code(sql) == "offset_exceeded"


def test_negative_offset_rejected():
    sql = "SELECT id FROM listings WHERE status='on_sale' LIMIT 5 OFFSET -1"
    assert _code(sql) == "offset_exceeded"


# ── 빈 입력 ────────────────────────────────────────────────────────
def test_empty_rejected():
    assert _code("   ") == "empty"


# ── listing_images 차단 (Story 9.6 AC3 — docs/tech-debt.md #48 닫음) ──────────────
# 왜 이 블록이 있나: `ALLOWED_TABLES = {"listings"}`가 사실상 listing_images를 막고 있었지만
#   **그걸 지키는 검사가 0개**였다. `0012_listing_images.sql:252`에 "sql_guard는 listings 단일
#   테이블을 유지하고 JOIN하지 않는다(9.6의 일)"는 주석 네 줄이 전부였다 — **주석은 계약이
#   아니다**(CLAUDE.md B9). 누군가 화이트리스트에 테이블을 하나 더 넣는 순간 조용히 뚫린다.
#
# 왜 중요한가: `ai_readonly`의 listing_images 정책은 `using(true)`라 **sold 매물의 사진 메타까지
#   전부 열려 있다**(0012:153, 의도된 설계 CR2). LLM이 만든 SQL이 그 테이블에 닿을 수 있게 되면
#   FR11(판매완료 비노출)이 그 경로에서 무너진다. 사진은 SELECT를 늘려서가 아니라 **손으로 쓴
#   고정 쿼리**(`listing_cards.attach_cover_images`)로만 붙인다 — 그쪽은 가드 대상이 아니고,
#   자기 WHERE절로 on_sale을 직접 건다(tests/test_listing_cards.py).


def test_join_listing_images_rejected():
    """LLM이 listing_images를 JOIN하면 거부된다 — 사진 경로로 가는 우회로를 막는다."""
    sql = (
        "SELECT l.id, l.manufacturer FROM listings l "
        "JOIN listing_images i ON i.listing_id = l.id "
        "WHERE l.status = 'on_sale'"
    )
    assert _code(sql) == "forbidden_table"


def test_select_from_listing_images_rejected():
    """JOIN 없이 listing_images를 직접 조회해도 거부된다."""
    sql = "SELECT storage_path FROM listing_images WHERE status = 'on_sale'"
    assert _code(sql) in ("forbidden_table", "forbidden_column")


def test_storage_path_column_rejected():
    """listings에 있는 척 storage_path를 요구해도 컬럼 화이트리스트가 거부한다."""
    sql = "SELECT id, storage_path FROM listings WHERE status = 'on_sale'"
    assert _code(sql) == "forbidden_column"


def test_allowed_tables_is_exactly_listings():
    """화이트리스트 자체를 못박는다 — 테이블이 늘면 여기가 red가 되어 리뷰를 강제한다.

    위 세 테스트는 "지금 listing_images가 막힌다"를 보이지만, 누군가 ALLOWED_TABLES에
    테이블을 추가하면 그 테이블은 아무 검사 없이 열린다. 이 단언이 그 변경을 눈에 띄게 만든다.
    """
    from app.db.sql_guard import ALLOWED_TABLES

    assert ALLOWED_TABLES == {"listings"}
