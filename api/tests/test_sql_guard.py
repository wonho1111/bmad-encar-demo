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
    """JOIN 없이 listing_images를 직접 조회해도 **테이블 화이트리스트**가 거부한다.

    ✎ 2026-07-20 코드리뷰: 원래 `in ("forbidden_table", "forbidden_column")` OR 단언이었다.
      그러면 테이블 차단이 뚫려도 컬럼 차단이 우연히 잡아주면 초록이라, 이 테스트의 제목이
      주장하는 것(테이블 차단)을 특정하지 못했다. 컬럼(`id`)은 화이트리스트에 있는 것으로
      바꿔 **테이블 차단만** 겨눈다 — 나머지 3건은 이미 정확한 코드로 단언하고 있었다.
    """
    sql = "SELECT id FROM listing_images WHERE status = 'on_sale'"
    assert _code(sql) == "forbidden_table"


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


# ── 하이브리드 벡터 절 화이트리스트 (13.1 — I/O 매트릭스 6행) ─────
# `ALLOWED_COLUMNS`/`_SQL_KEYWORDS`는 건드리지 않는다(1차 리뷰 패스가 되돌린 블랭킷 추가
# 방식 대신, `ORDER BY embedding <=> ...::vector` 모양을 위치-스코프로 통째 제거한다).
_HYBRID_GOOD = (
    "SELECT id, manufacturer, model, year, price, mileage, region "
    "FROM listings WHERE status = 'on_sale' AND body_type = 'SUV' "
    "ORDER BY embedding <=> %s::vector LIMIT 10"
)


def test_hybrid_vector_query_passes():
    """정상 하이브리드 벡터 쿼리는 화이트리스트를 통과하고 LIMIT을 그대로 유지한다."""
    out = validate_select_sql(_HYBRID_GOOD)
    assert "LIMIT 10" in out
    assert "embedding <=> %s::vector" in out


def test_hybrid_or_rejected():
    """하이브리드 형태에 OR을 섞어도 기존과 동일하게 거부된다(회귀 없음)."""
    sql = _HYBRID_GOOD.replace(
        "AND body_type = 'SUV' ",
        "AND body_type = 'SUV' OR price < 1 ",
    )
    assert _code(sql) == "forbidden_or"


def test_hybrid_subquery_rejected():
    """하이브리드 형태에 서브쿼리를 섞어도 기존과 동일하게 거부된다(회귀 없음)."""
    sql = (
        "SELECT id, manufacturer, model, year, price, mileage, region FROM listings "
        "WHERE status = 'on_sale' AND id IN (SELECT id FROM listings) "
        "ORDER BY embedding <=> %s::vector LIMIT 10"
    )
    assert _code(sql) == "subquery_not_allowed"


def test_hybrid_missing_status_filter_rejected():
    """하이브리드 형태에서도 status='on_sale' 누락 시 거부된다."""
    sql = (
        "SELECT id FROM listings WHERE body_type = 'SUV' "
        "ORDER BY embedding <=> %s::vector LIMIT 10"
    )
    assert _code(sql) == "missing_status_filter"


def test_hybrid_bind_placeholder_named_form_passes():
    """`%(name)s` 자리표시자 형태도 오탐 없이 통과한다(바인드 자리표시자 오탐 방지)."""
    sql = (
        "SELECT id FROM listings WHERE status = 'on_sale' "
        "ORDER BY embedding <=> %(query_embedding)s::vector LIMIT 5"
    )
    out = validate_select_sql(sql)
    assert "LIMIT 5" in out


def test_embedding_outside_vector_clause_still_rejected():
    """`embedding`이 벡터절 밖(예: SELECT 목록)에 나오면 여전히 forbidden_column으로 거부된다.

    위치-스코프 화이트리스트가 실제로 위치를 가리는지 증명하는 회귀 테스트(1차 패스가
    놓쳤던 위치-무관 취약점 — Spec Change Log 참조).
    """
    sql = "SELECT id, embedding FROM listings WHERE status = 'on_sale' LIMIT 5"
    assert _code(sql) == "forbidden_column"


def test_vector_alias_outside_order_by_still_rejected():
    """`vector`가 벡터절 밖(예: 테이블 별칭)에 나오면 여전히 forbidden_column으로 거부된다."""
    sql = "SELECT id FROM listings vector WHERE status = 'on_sale' LIMIT 5"
    assert _code(sql) == "forbidden_column"


def test_uppercase_percent_s_placeholder_in_vector_clause_rejected():
    """`%S`(대문자)는 psycopg 자리표시자가 아니라 절대 바인딩되지 않는다 — 전역 IGNORECASE가
    이 형태도 벡터절로 지워버리면 그 %S가 그대로 실행 SQL에 남아 psycopg 문법 오류가 된다
    (review pass 4). 식별자(order by embedding·vector)는 대소문자 무관해도, 자리표시자는
    대소문자를 구분해야 한다.
    """
    sql = "SELECT id FROM listings WHERE status = 'on_sale' ORDER BY EMBEDDING <=> %S::VECTOR LIMIT 5"
    assert _code(sql) == "forbidden_column"


def test_uppercase_vector_keywords_with_correct_case_placeholder_still_passes():
    """자리표시자만 대소문자를 구분할 뿐, ORDER BY/EMBEDDING/VECTOR 키워드는 여전히
    대소문자 무관하게 인식된다(위 수정이 위치-스코프 화이트리스트 자체를 깨지 않았음을 확인).
    """
    sql = "SELECT id FROM listings WHERE status = 'on_sale' ORDER BY EMBEDDING <=> %s::VECTOR LIMIT 5"
    out = validate_select_sql(sql)
    assert "LIMIT 5" in out


# ── 자리표시자(%s/%(name)s)는 벡터절 밖에서 거부된다(3차 리뷰 패스 신규) ──────────
# "방어적 이중 스트립"(벡터절 밖의 %s/%(name)s를 위치 무관하게 지우는 스텝)은 실제로는
# 가드를 여는 스텝이었다 — 지우면 자리표시자가 미화이트리스트 식별자로 안 잡히고 통과해
# run_select()가 params 없이 실행돼 psycopg 문법 오류(500)가 된다. 이 두 테스트가 그
# 스텝이 없어야 함을 실제로 잡는다(그 스텝을 다시 넣으면 아래 2건이 red가 된다).
def test_placeholder_outside_vector_clause_positional_form_rejected():
    """`%s`가 벡터절 밖(예: WHERE model = %s)에 나오면 forbidden_column으로 거부된다."""
    sql = "SELECT id FROM listings WHERE status='on_sale' AND model = %s LIMIT 5"
    assert _code(sql) == "forbidden_column"


def test_placeholder_outside_vector_clause_named_form_rejected():
    """`%(name)s`가 벡터절 밖(예: WHERE price <= %(maxp)s)에 나오면 forbidden_column으로 거부된다."""
    sql = "SELECT id FROM listings WHERE status='on_sale' AND price <= %(maxp)s LIMIT 5"
    assert _code(sql) == "forbidden_column"


# ── 문자열 리터럴 안의 limit/offset + 숫자가 실제 절을 가리지 않는다(3차 리뷰 패스 신규) ──
# LIMIT·OFFSET 숫자 매처가 cleaned(리터럴 포함)를 읽으면, description 등 자유텍스트 리터럴
# 안의 우연한 "limit 3"·"offset 999999" 같은 숫자가 실제 절보다 먼저 매치돼 MAX_LIMIT/
# MAX_OFFSET 우회나 DEFAULT_LIMIT 미주입(무제한 SELECT)으로 이어진다(Design Notes 실측표).
def test_literal_limit_digit_does_not_bypass_max_limit():
    """리터럴 속 'limit 3'이 실제 LIMIT 100보다 먼저 매치돼선 안 된다 — MAX_LIMIT 우회 차단."""
    sql = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = 'limit 3' LIMIT 100"
    )
    assert _code(sql) == "limit_exceeded"


def test_literal_limit_digit_without_real_limit_clause_still_gets_default():
    """실제 LIMIT절이 없으면(리터럴 속 'limit 10'뿐) DEFAULT_LIMIT이 그대로 덧붙는다.

    수정 전엔 `normalized = cleaned` 경로를 잘못 타 LIMIT 절이 아예 없는 무제한 SELECT를
    반환했다(Design Notes 실측). 숫자가 없는 'no limit here'만으로는 이 분기에 안 닿으므로
    (test_limit_word_inside_literal_does_not_trigger_malformed) 숫자 포함 케이스를 별도로 잠근다.
    """
    sql = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = 'limit 10'"
    )
    out = validate_select_sql(sql)
    assert f"LIMIT {DEFAULT_LIMIT}" in out


def test_literal_offset_digit_does_not_trigger_false_offset_exceeded():
    """리터럴 속 'offset 999999'가 실제 OFFSET절로 오인돼 정상 쿼리를 거부해선 안 된다."""
    sql = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = 'offset 999999'"
    )
    out = validate_select_sql(sql)
    assert f"LIMIT {DEFAULT_LIMIT}" in out


# ── LIMIT 괄호 형태(DW-315) — 숫자 형태 미인식 시 이중 LIMIT 대신 명시 거부 ──
def test_parenthesized_limit_rejected_as_malformed():
    """`LIMIT (10)`처럼 숫자가 바로 안 붙는 형태는 조용히 LIMIT 5를 덧붙이지 않고 거부한다."""
    sql = "SELECT id FROM listings WHERE status = 'on_sale' LIMIT (10)"
    assert _code(sql) == "limit_malformed"


def test_limit_word_inside_literal_does_not_trigger_malformed():
    """문자열 리터럴 안에 우연히 'limit' 단어가 있어도(실제 LIMIT절 없음) 오탐 거부하지 않는다.

    코드리뷰 패치: limit_malformed 분기가 `cleaned`(리터럴 미제거)를 검사하면
    `description = 'no limit here'` 같은 정상 값 때문에 정상 쿼리가 거부된다.
    """
    sql = "SELECT id, description FROM listings WHERE status='on_sale' AND description = 'no limit here'"
    out = validate_select_sql(sql)
    assert f"LIMIT {DEFAULT_LIMIT}" in out  # LIMIT 없었으므로 기본 LIMIT 정상 주입


def test_allowed_columns_is_exactly_pinned():
    """ALLOWED_COLUMNS를 정확 집합으로 고정한다 — 지금은 아무 테스트도 이 집합 전체를 보지 않아

    조용히 넓어질 수 있었다(Story 10.1). 신뢰속성 3컬럼(accident_status·is_single_owner·
    is_non_smoker)이 추가된 뒤에도 listings 테이블 밖 컬럼(storage_path 등)이 섞이지 않는지
    이 단언이 못박는다 — 늘어나면 여기가 red가 되어 리뷰를 강제한다.
    """
    from app.db.sql_guard import ALLOWED_COLUMNS

    assert ALLOWED_COLUMNS == {
        "id", "manufacturer", "model", "year", "price", "mileage", "region",
        "body_type", "color", "fuel", "transmission", "displacement", "seats",
        "accident_free", "status", "options", "description",
        "accident_status", "is_single_owner", "is_non_smoker",
    }


# ── review pass 5 — 벡터절 "끝"까지 고정한다 ────────────────────────────
# 벡터절 정규식이 접두사만 보면(끝 미고정), 매치 뒤에 뭐가 붙어도 절이 통째로 지워져
# 검증 없이 통과한다. 아래 3형태가 실제로 통과했었다.
def test_hybrid_vector_clause_with_desc_rejected():
    """`<=>`는 거리 연산자라 DESC는 "가장 안 닮은 순"이다 — 통과시키면 결과가 조용히 뒤집힌다."""
    sql = (
        "SELECT id FROM listings WHERE status='on_sale' "
        "ORDER BY embedding <=> %s::vector DESC LIMIT 10"
    )
    assert _code(sql) == "forbidden_column"


def test_hybrid_vector_clause_duplicated_rejected():
    """같은 절이 두 번이면 ORDER BY가 둘인 실행 불가 SQL — psycopg 문법오류(500)로 가기 전에 막는다."""
    sql = (
        "SELECT id FROM listings WHERE status='on_sale' "
        "ORDER BY embedding <=> %s::vector ORDER BY embedding <=> %s::vector LIMIT 5"
    )
    assert _code(sql) == "forbidden_column"


def test_hybrid_vector_clause_with_trailing_sort_key_rejected():
    """벡터절 뒤에 딸려오는 2차 정렬키는 검증된 적이 없다 — 넓히는 대신 거부한다."""
    sql = (
        "SELECT id FROM listings WHERE status='on_sale' "
        "ORDER BY embedding <=> %s::vector, price LIMIT 10"
    )
    assert _code(sql) == "forbidden_column"


def test_hybrid_vector_clause_allows_only_limit_or_offset_or_end():
    """반대 방향 고정 — 정상 3형태(끝·LIMIT·OFFSET)는 여전히 통과해야 한다."""
    base = "SELECT id FROM listings WHERE status='on_sale' ORDER BY embedding <=> %s::vector"
    assert f"LIMIT {DEFAULT_LIMIT}" in validate_select_sql(base)          # 절 뒤가 문장 끝
    assert "LIMIT 10" in validate_select_sql(base + " LIMIT 10")          # 절 뒤가 LIMIT
    assert "OFFSET 10" in validate_select_sql(base + " OFFSET 10 LIMIT 5")  # 절 뒤가 OFFSET


def test_vector_expression_outside_order_by_rejected():
    """ORDER BY 앵커가 위치-스코프의 전부다 — 같은 식이 SELECT 목록·WHERE에 오면 거부한다.

    앵커가 없으면 벡터식이 SELECT 목록의 무방비 숫자 슬롯에 들어가 rows_to_cards()에서
    잡히지 않는 TypeError(400 → 500)가 되고, 미바인드 %s가 params 없는 run_select()로 샌다.
    """
    in_select = (
        "SELECT id, embedding <=> %s::vector FROM listings WHERE status='on_sale' LIMIT 5"
    )
    in_where = (
        "SELECT id FROM listings WHERE status='on_sale' "
        "AND embedding <=> %s::vector < 0.3 LIMIT 5"
    )
    assert _code(in_select) == "forbidden_column"
    assert _code(in_where) == "forbidden_column"


# ── review pass 5 — 달러 인용 리터럴은 LIMIT/OFFSET 매처를 가로챈다 ──────
def test_dollar_quoted_literal_rejected():
    """`$$...$$`는 no_strings가 안 지우는 또 다른 문자열 리터럴 문법이다.

    허용하면 그 안의 "limit 3"이 실제 LIMIT절보다 먼저 매치돼 MAX_LIMIT 상한을 우회하고
    (`$$limit 3$$ LIMIT 100` → 100건 통과), 실제 LIMIT절이 없으면 DEFAULT_LIMIT 주입까지
    건너뛰어 무제한 SELECT가 된다. 작은따옴표 리터럴에서 이미 막은 것과 같은 구멍이다.
    """
    bypass = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = $$limit 3$$ LIMIT 100"
    )
    unbounded = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = $$limit 3$$"
    )
    tagged = (
        "SELECT id, description FROM listings WHERE status='on_sale' "
        "AND description = $x$limit 3$x$ LIMIT 100"
    )
    assert _code(bypass) == "dollar_quote_not_allowed"
    assert _code(unbounded) == "dollar_quote_not_allowed"
    assert _code(tagged) == "dollar_quote_not_allowed"
