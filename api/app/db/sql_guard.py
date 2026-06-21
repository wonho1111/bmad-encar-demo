"""결정론적 SQL 안전장치 — LLM이 만든 SELECT를 실행 전에 검증한다(연구 §4.2).

핵심 사상(함정 #1): "프롬프트로 SELECT만 만들어줘"는 안전장치가 아니다. LLM은 환각·프롬프트
  인젝션으로 DROP·다중문장·서브쿼리로 다른 테이블을 읽는 SQL을 만들 수 있다. 그래서 **코드가
  매번 같은 규칙(결정론적)으로** 직접 검사하고, 통과한 쿼리만 실행한다. 못 미더우면 거부(fail-closed).

검증은 sqlparse(문장 구조 파싱)와 정규식(테이블·컬럼·필터 상세 검사)을 **병행**한다 —
  둘 중 하나라도 의심스러우면 거부한다(연구 §4.2 다층 방어).

이중 방어: 가드를 통과해도 실행은 항상 ai_readonly 롤(4.1, db/readonly.py)로만 한다.
  가드가 뚫려도 쓰기 구문은 DB가 거부한다.
[Source: research §4.2; architecture.md#AI 경로 안전장치; story 4.3 sql_guard 설계]
"""

import re

import sqlparse
from sqlparse.tokens import DDL, DML

# 추천 기본 개수와 안전 상한은 서로 다른 개념이다(코드리뷰 4.3에서 분리).
#   · DEFAULT_LIMIT: LLM이 LIMIT을 안 붙였을 때 주입하는 "기본 추천 개수".
#     product-brief 성공기준 "약 5개 정확히 추천"에 맞춰 5로 둔다.
#   · MAX_LIMIT: 과도 조회("차 보여줘")를 막는 절대 안전 상한(연구 §4.3). 초과 생성 시 거부.
DEFAULT_LIMIT = 5           # 기본 추천 개수 — brief "약 5개" 정합
MAX_LIMIT = 50             # 데모 안전 상한 — 초과 생성 시 거부(연구 §4.3)
# OFFSET 안전 상한 — 과도한 페이지네이션(예: OFFSET 999999)으로 DB를 훑는 것을 막는다.
#   데모 데이터 규모상 이 이상 건너뛸 일이 없으므로 초과 시 거부한다(MAX_LIMIT와 동일 스타일).
MAX_OFFSET = 1000          # 데모 안전 상한 — 초과 생성 시 거부

# 화이트리스트 — listings 단일 테이블만 허용(0002_listings.sql 단일출처).
ALLOWED_TABLES = {"listings"}

# ListingCard 7필드 + 필터 컬럼. 0002_listings.sql 컬럼명과 정확히 일치(drift 금지).
ALLOWED_COLUMNS = {
    "id", "manufacturer", "model", "year", "price", "mileage", "region",
    "body_type", "color", "fuel", "transmission", "displacement", "seats",
    "accident_free", "status", "options", "description",
}

# DML/DDL 등 SELECT가 아닌 위험 키워드 — 어디에 등장하든(서브쿼리 위장 포함) 거부.
_FORBIDDEN = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    "GRANT", "REVOKE", "COPY", "MERGE", "CALL", "EXECUTE",
}

# 조회 쿼리에 정상적으로 등장하는 SQL 절 키워드 — 컬럼 화이트리스트 검사에서 식별자 아님으로 무시.
# (위험 키워드는 여기 절대 넣지 않는다 → _FORBIDDEN·컬럼 검사로 걸러진다.)
_SQL_KEYWORDS = {
    "select", "from", "where", "and", "or", "not", "in", "is", "null",
    "true", "false", "like", "ilike", "between", "order", "by", "asc",
    "desc", "limit", "offset", "as", "on", "distinct",
}


class SqlGuardError(Exception):
    """가드 차단 예외 — 차단 사유 코드와 사용자용 한국어 메시지를 함께 보유한다."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def validate_select_sql(sql: str) -> str:
    """LLM이 만든 SQL을 검증하고, 통과하면 정규화된 안전 SQL(LIMIT 주입 포함)을 반환한다.

    실패하면 SqlGuardError(code, 한국어 message)를 raise한다(실행 전 차단, CM2).
    """
    if not sql or not sql.strip():
        raise SqlGuardError("empty", "생성된 SQL이 비어 있습니다.")

    raw = sql.strip()
    # 맨 끝의 세미콜론 1개만 제거 — 그래도 남은 ';'는 다중문장(스태킹)이므로 아래에서 거부.
    cleaned = raw[:-1].strip() if raw.endswith(";") else raw

    # ── 1) 단일 문장 ───────────────────────────────────────────────
    if ";" in cleaned:
        raise SqlGuardError("multiple_statements", "여러 SQL 문장은 실행할 수 없습니다.")

    parsed = sqlparse.parse(cleaned)
    if len(parsed) != 1:
        raise SqlGuardError("multiple_statements", "여러 SQL 문장은 실행할 수 없습니다.")
    stmt = parsed[0]

    # 이후 어휘 검사(주석·금지키워드·OR·서브쿼리·컬럼)는 문자열 리터럴을 먼저 제거한 본문으로
    # 수행한다 — 'DROP'·'update' 같은 정상 값(model·description 자유텍스트)이 위험 키워드로
    # 오탐돼 차단되지 않게 하기 위함(코드리뷰 4.3). status='on_sale' 검사만은 리터럴이
    # 필요하므로 원본(cleaned)을 그대로 쓴다.
    no_strings = re.sub(r"'[^']*'", " ", cleaned)

    # ── 2) 주석 금지(리터럴 제거 후 — 값 안의 '--' 등 오탐 방지) ────
    if "--" in no_strings or "/*" in no_strings or "*/" in no_strings:
        raise SqlGuardError("comment_not_allowed", "SQL 주석은 허용되지 않습니다.")

    # ── 3) SELECT 전용 ──────────────────────────────────────────────
    # sqlparse가 판정한 문장 타입이 SELECT가 아니면 거부(DELETE/UPDATE/UNKNOWN 등).
    if stmt.get_type() != "SELECT":
        raise SqlGuardError("not_select", "조회(SELECT) 쿼리만 허용됩니다.")

    # 토큰 어디에도 DML/DDL 위험 키워드가 없어야 한다(서브쿼리·위장 DDL 방지).
    for token in stmt.flatten():
        if token.ttype in (DML, DDL) and token.value.upper() in _FORBIDDEN:
            raise SqlGuardError("forbidden_keyword", "허용되지 않는 SQL 구문이 포함되어 있습니다.")
    # 정규식 보조 — 토큰 분류를 우회한 위험 키워드도 단어 경계로 한 번 더 차단(리터럴 제거본 검사).
    sql_upper = no_strings.upper()
    for kw in _FORBIDDEN:
        if re.search(rf"\b{kw}\b", sql_upper):
            raise SqlGuardError("forbidden_keyword", "허용되지 않는 SQL 구문이 포함되어 있습니다.")

    # ── 4) OR 금지 — status='on_sale' 무력화 차단(FR11, 코드리뷰 Critical) ──
    # 가드는 status 필터의 "존재"만 본다. OR가 허용되면 `status='on_sale' OR price<9e9`처럼
    # 써서 sold까지 새어나간다(ai_readonly RLS는 using(true)라 sold를 못 거름 → 쿼리가 유일
    # 방어선). 그래서 OR 자체를 거부해 status 필터가 항상 AND로 유효하게 만든다(프롬프트 규칙 ③ 동일 의도).
    if re.search(r"\bor\b", no_strings, re.IGNORECASE):
        raise SqlGuardError(
            "forbidden_or",
            "OR 조건은 허용되지 않습니다. 조건은 AND로만 결합해 주세요.",
        )

    # ── 5) 서브쿼리 금지 — 외부 LIMIT 우회·우회 조회 차단(코드리뷰 High) ──
    # 중첩 SELECT가 있으면 ① 내부 LIMIT이 외부 상한 검사를 가리고(전체 행 반환) ② 우회 조회
    # 위험이 있다. 단일 테이블 데모엔 서브쿼리가 불필요하므로 SELECT가 2개 이상이면 거부(fail-closed).
    if len(re.findall(r"\bselect\b", no_strings, re.IGNORECASE)) > 1:
        raise SqlGuardError("subquery_not_allowed", "중첩 조회(서브쿼리)는 허용되지 않습니다.")

    # ── 6) 테이블·컬럼 화이트리스트 ────────────────────────────────
    # SELECT * 금지 — 명시 컬럼만 허용(환각·과다노출 방지).
    if re.search(r"select\s+\*", no_strings, re.IGNORECASE):
        raise SqlGuardError("select_star", "전체 컬럼(SELECT *) 조회는 허용되지 않습니다.")

    # FROM/JOIN 뒤 테이블이 listings뿐인지 검사.
    tables = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w.]*)", no_strings, re.IGNORECASE)
    if not tables:
        raise SqlGuardError("no_table", "조회 대상 테이블을 찾을 수 없습니다.")
    for table in tables:
        if table.lower() not in ALLOWED_TABLES:
            raise SqlGuardError("forbidden_table", "허용되지 않는 테이블을 조회하고 있습니다.")

    # 영문 식별자만 추출해 컬럼 화이트리스트 검사.
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", no_strings.lower()))
    unknown = words - _SQL_KEYWORDS - ALLOWED_TABLES - ALLOWED_COLUMNS
    if unknown:
        # 화이트리스트에 없는 식별자(환각 컬럼·함수 등) → 거부(fail-closed).
        raise SqlGuardError(
            "forbidden_column",
            "허용되지 않는 컬럼 또는 식별자가 포함되어 있습니다.",
        )

    # ── 4) FR11 — status = 'on_sale' 필수 ─────────────────────────
    # RLS는 ai_readonly에 sold를 못 거른다 → 쿼리가 직접 on_sale을 강제해야 한다(함정 #2).
    # 주입이 아니라 "존재 검증 + 없으면 거부"(함정 #3: OR 우회 위험 회피).
    if not re.search(r"status\s*=\s*'on_sale'", cleaned, re.IGNORECASE):
        raise SqlGuardError(
            "missing_status_filter",
            "판매중 매물만 조회할 수 있도록 status = 'on_sale' 조건이 필요합니다.",
        )

    # ── 5) OFFSET 상한 검사 ────────────────────────────────────────
    # OFFSET은 "앞에서 N건 건너뛰기". 상한이 없으면 OFFSET 999999처럼 DB를 통째로 훑는
    # 우회 조회가 통과한다. 부호([-+]?)까지 잡아 음수/과도한 값을 모두 거부한다(MAX_LIMIT와 동일 정책).
    offset_match = re.search(r"\boffset\s+([-+]?\d+)", cleaned, re.IGNORECASE)
    if offset_match:
        off = int(offset_match.group(1))
        if off < 0 or off > MAX_OFFSET:
            raise SqlGuardError(
                "offset_exceeded",
                f"건너뛸 수 있는 매물 수(OFFSET)는 최대 {MAX_OFFSET}건입니다.",
            )

    # ── 6) LIMIT 검사·주입 ─────────────────────────────────────────
    # 부호([-+]?)까지 함께 잡는다. 안 그러면 `LIMIT -1`이 "LIMIT 없음"으로 오인돼
    #   `LIMIT -1 LIMIT 5`라는 실행 불가 SQL이 만들어진다(코드리뷰 후속 버그). 음수·0은 거부.
    limit_match = re.search(r"\blimit\s+([-+]?\d+)", cleaned, re.IGNORECASE)
    if limit_match:
        n = int(limit_match.group(1))
        if n <= 0:
            raise SqlGuardError(
                "limit_invalid",
                "LIMIT은 1 이상의 값이어야 합니다.",
            )
        if n > MAX_LIMIT:
            raise SqlGuardError(
                "limit_exceeded",
                f"한 번에 조회할 수 있는 매물은 최대 {MAX_LIMIT}건입니다.",
            )
        normalized = cleaned
    else:
        # LIMIT 없으면 끝에 append — append는 결정론적으로 안전(WHERE 변형 위험 없음).
        normalized = f"{cleaned} LIMIT {DEFAULT_LIMIT}"

    # ── 7) 통과 — 정규화된 안전 SQL 반환 ──────────────────────────
    return normalized
