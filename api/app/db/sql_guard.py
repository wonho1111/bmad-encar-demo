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
from sqlparse.sql import Comparison, Parenthesis, Where
from sqlparse.tokens import DDL, DML
from sqlparse.tokens import Comparison as COMPARISON_OP

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
# accident_status·is_single_owner·is_non_smoker는 0017_listings_trust_attributes.sql(Story 10.1)
# 이 추가한 신뢰속성 3컬럼 — listings 밖 컬럼(예: storage_path)은 여기 넣지 않는다
# (conventions.md §4.1 경고 — FR11이 그 경로에서 무너진다).
# 하이브리드(SQL+벡터) 검색의 `embedding`·`vector`도 여기 넣지 않는다 — 위치와 무관하게
# 어디서나 통과해 버리기 때문이다. 그 둘은 validate_select_sql() 안의 벡터절 정규식이
# `ORDER BY embedding <=> %s::vector` 라는 정확한 모양·위치에서만 통과시킨다(13.3이 참고할
# 자리는 그 정규식 옆의 주석이다 — Story 13.1).
ALLOWED_COLUMNS = {
    "id", "manufacturer", "model", "year", "price", "mileage", "region",
    "body_type", "color", "fuel", "transmission", "displacement", "seats",
    "accident_free", "status", "options", "description",
    "accident_status", "is_single_owner", "is_non_smoker",
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
    # any: 배열 멤버십 검사용(`'스마트키' = ANY(options)`). 서브쿼리(`= ANY(SELECT ...)`)는
    #   위 5)에서 select 2개 이상으로 이미 차단되므로, 배열 형태만 통과한다(안전).
    "any",
}


class SqlGuardError(Exception):
    """가드 차단 예외 — 차단 사유 코드와 사용자용 한국어 메시지를 함께 보유한다."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# ── status = 'on_sale' 부정 우회 차단 — 구조적(sqlparse 토큰) 검사(DW-557, review-2) ──
# 최초 구현(문자열 존재 검사)·review-1(부정 연산자 정규식 나열)이 둘 다 실측으로 뚫렸다
# (review-1: 괄호 2겹 이상·`=false`/`<>true`, review-2: 따옴표 불리언 `='f'`·괄호로 감싼
# 불리언 `=(false)`). "어떤 문자열로 부정을 표현했는가"를 나열하는 정규식은 두더지 잡기라
# 수렴하지 않는다는 것이 두 라운드 연속 증명됐다(Design Notes). 그래서 표현 형태가 아니라
# 구조를 본다: WHERE절의 최상위 AND 결합항 중 "부정·재비교 없이 `status = 'on_sale'`가
# 그대로 있는 항"이 하나라도 있는가만 확인한다. 그 항 자체가 다른 무언가와 다시 비교되거나
# (`(status='on_sale') = <무엇이든>`), NOT·IS 등으로 감싸이면 — 그 겉을 감싼 표현이 무엇이든
# 좌변이 더 이상 순수 `status` 식별자가 아니게 되므로 자동으로 탈락한다(별도 나열 불필요).
def _strip_ws(tokens):
    return [t for t in tokens if not t.is_whitespace]


def _peel_grouping_parens(tokens):
    """전체가 괄호 하나로만 감싸인 경우 그 괄호를 벗긴다(깊이 무관, 반복 적용).

    `(status='on_sale')`·`((status='on_sale'))`처럼 순수 그룹핑 괄호는 최상위로 인정한다.
    `NOT (status='on_sale')`처럼 앞에 다른 토큰(NOT 등)이 붙어 있으면 tokens 길이가
    1이 아니므로 이 함수가 손대지 않고 그대로 반환 — 아래 길이 검사에서 자연히 탈락한다.
    """
    while len(tokens) == 1 and isinstance(tokens[0], Parenthesis):
        inner = _strip_ws(tokens[0].tokens)  # inner[0]='(', inner[-1]=')'
        tokens = _strip_ws(inner[1:-1])
    return tokens


def _conjunct_is_bare_status_on_sale(tokens):
    """이 AND 결합항이 부정·재비교 없이 정확히 `status = 'on_sale'` 하나뿐인가.

    NOT·IS (NOT) TRUE/FALSE·다른 값과의 재비교(`= false`·`= 'f'`·`= (false)` 등)는 전부
    이 항을 "좌변=status 식별자, 연산자='=', 우변='on_sale' 문자열"이라는 정확히 3토큰
    형태에서 벗어나게 만들므로, 표현을 나열하지 않고도 구조만으로 전부 걸러진다.
    """
    tokens = _peel_grouping_parens(_strip_ws(tokens))
    if len(tokens) == 1 and isinstance(tokens[0], Comparison):
        tokens = _peel_grouping_parens(_strip_ws(tokens[0].tokens))
    if len(tokens) != 3:
        return False
    left, op, right = tokens
    if op.ttype is not COMPARISON_OP or op.normalized != "=":
        return False
    left_name = left.get_real_name() if hasattr(left, "get_real_name") else left.value
    if (left_name or "").strip().lower() != "status":
        return False
    if right.ttype not in (sqlparse.tokens.Literal.String.Single,):
        return False
    if right.value.strip("'").lower() != "on_sale":
        return False
    return True


def _split_top_level_and(tokens):
    """최상위(괄호 안에 들어있지 않은) AND 키워드 기준으로 토큰을 결합항 리스트로 나눈다."""
    groups = [[]]
    for t in tokens:
        if t.ttype is sqlparse.tokens.Keyword and t.normalized == "AND":
            groups.append([])
        else:
            groups[-1].append(t)
    return groups


# sqlparse의 Where 그룹은 절 키워드를 만나면 닫히지만, 두 경우엔 닫히지 않아 그 꼬리가
# 결합항 안으로 딸려 들어와 3토큰 형태를 깬다(= 정상 SQL이 missing_status_filter로 오탈락):
#   (a) 애초에 Where의 종료 키워드가 아닌 것 — OFFSET·FETCH·WINDOW (review-4 실측).
#   (b) 종료 키워드인데 공백이 한 칸이 아니라 sqlparse의 문자열 매칭이 빗나가는 것 —
#       `ORDER  BY`(두 칸)·`ORDER\tBY`·`ORDER\nBY` (review-5 실측: 베이스라인에서 통과하던
#       쿼리가 구조 검사 도입 후 거부로 뒤집혔다). sqlparse는 키워드를 정규화할 때 대문자로만
#       바꾸고 공백은 접지 않으므로, 여기서도 접어서 비교해야 같은 절로 인식된다.
# 실측 도달성(추측 아님 — 아래 6개를 실제로 넣어 확인, B4): 이 검사에 **실제로 도달**하는
#   것은 OFFSET과 공백 변형 ORDER BY뿐이다. FETCH·WINDOW·GROUP BY는 꼬리가 새기는 하지만
#   앞선 식별자 화이트리스트가 forbidden_column으로 먼저 거부하고, HAVING은 애초에 안 샌다.
#   도달 못 하는 것도 남겨 두는 이유는 13.3이 화이트리스트를 넓히면 그때 처음 살아나서다.
_WHERE_TAIL_KEYWORDS = frozenset({
    "OFFSET", "FETCH", "WINDOW", "ORDER BY", "GROUP BY", "HAVING",
})


def _fold_ws(value: str) -> str:
    """토큰 값의 연속 공백·탭·줄바꿈을 한 칸으로 접는다(`ORDER  BY` → `ORDER BY`)."""
    return " ".join(value.split())


def _cut_where_tail(tokens):
    """WHERE 술어 뒤에 딸려온 절 키워드 이후를 잘라낸다(공백을 접어서 비교)."""
    for i, t in enumerate(tokens):
        if t.ttype is sqlparse.tokens.Keyword and _fold_ws(t.normalized).upper() in _WHERE_TAIL_KEYWORDS:
            return tokens[:i]
    return tokens


def _flatten_conjuncts(tokens):
    """최상위 AND 결합항을 괄호 깊이에 무관하게 평탄화해 돌려준다.

    `(status='on_sale' AND price<X) AND year>2020`처럼 AND 그룹이 괄호에 싸인 채
    다른 결합항과 나란히 있으면, 그 괄호 안의 항들도 의미상 최상위 AND 결합항이다.
    괄호를 벗기고 재귀적으로 쪼개야 안쪽의 `status='on_sale'`을 찾을 수 있다(review-4
    실측: 이걸 안 하면 베이스라인이 통과시키던 정상 SQL이 오탈락한다).

    부정은 이 평탄화를 통과하지 못한다 — `NOT (...)`·`(NOT ...)`은 토큰이 2개라
    `_peel_grouping_parens`가 벗기지 않고, 3토큰 매치에서도 탈락한다. OR 그룹도
    AND로 쪼개지지 않아 통째로 한 결합항으로 남아 매치에 실패한다(OR 자체는 별도
    검사가 전면 금지).
    """
    tokens = _peel_grouping_parens(_strip_ws(tokens))
    groups = _split_top_level_and(tokens)
    if len(groups) == 1:
        return [tokens]
    flat = []
    for g in groups:
        flat.extend(_flatten_conjuncts(g))
    return flat


def _has_unnegated_status_on_sale(stmt) -> bool:
    """WHERE절의 최상위 AND 결합항 중 부정 없는 `status = 'on_sale'`가 하나라도 있는가."""
    where = next((t for t in stmt.tokens if isinstance(t, Where)), None)
    if where is None:
        return False
    inner = _strip_ws(where.tokens)
    # inner[0]는 'WHERE' 키워드 — 결합항 분리 전에 제거.
    inner = inner[1:] if inner and inner[0].ttype is sqlparse.tokens.Keyword else inner
    inner = _cut_where_tail(inner)
    # WHERE절 전체를 바깥 괄호 하나로 감싼 형태(`WHERE (a AND b)` — Gemini가 종종 쓰는
    # 방어적 스타일, review-3 실측)를 포함해, 괄호에 싸인 AND 그룹을 재귀적으로 평탄화한다.
    return any(_conjunct_is_bare_status_on_sale(c) for c in _flatten_conjuncts(inner))


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
    # 달러 인용($$...$$·$tag$...$tag$)은 Postgres의 또 다른 문자열 리터럴 문법이다. 아래
    # no_strings는 작은따옴표만 지우므로, 달러 인용을 허용하면 그 안의 내용이 "리터럴이 아닌
    # 본문"으로 남아 LIMIT·OFFSET 숫자 매처를 가로챈다(실측: `description = $$limit 3$$ LIMIT 100`
    # → 리터럴의 3이 먼저 매치돼 MAX_LIMIT 우회, `description = $$limit 3$$` → LIMIT 절이
    # 아예 없는 무제한 SELECT). 작은따옴표 리터럴에 대해 3차 리뷰 패스가 막은 것과 같은
    # 구멍이다. psycopg 자리표시자는 %s 스타일이라 정상 경로에 '$'가 등장할 이유가 없으므로,
    # 파싱 규칙을 늘리는 대신 '$' 자체를 fail-closed로 거부한다(review pass 5).
    if "$" in cleaned:
        raise SqlGuardError(
            "dollar_quote_not_allowed",
            "달러 인용($$) 문법은 허용되지 않습니다. 문자열은 작은따옴표로 작성해 주세요.",
        )

    no_strings = re.sub(r"'[^']*'", " ", cleaned)

    # 하이브리드 벡터 절 — 위치-스코프 통째 제거(13.1, 1차 리뷰 패스 수정. Spec Change Log 참조).
    #   `ORDER BY embedding <=> <자리표시자>::vector` 절은 **코드가 붙인다, LLM이 아니다**(I4) —
    #   13.3(하이브리드 노드)이 이 자리를 참고한다. 정확히 이 모양·이 위치에서만 embedding·
    #   vector·%s/%(name)s 자리표시자를 통째로 소비해 지운다(문자열 리터럴 제거와 같은 자리·
    #   같은 스타일). `embedding`/`vector`는 ALLOWED_COLUMNS/_SQL_KEYWORDS에 넣지 않는다 —
    #   그러면 위치와 무관하게 어디서나 통과해 rows_to_cards()의 무방비 숫자 슬롯에서 크래시
    #   표면을 새로 연다(1차 구현이 이렇게 했다가 리뷰에서 되돌려짐). 이 매치 밖의 embedding·
    #   vector(예: SELECT 목록)는 여전히 미화이트리스트 식별자로 forbidden_column 거부된다.
    # 자리표시자(%s·%(name)s)는 위 정규식이 벡터절 "안"에서만 소비한다 — 벡터절 밖의 자리
    # 표시자를 별도로 지우는 "방어적 이중 스트립" 스텝은 두지 않는다(3차 리뷰 패스 수정).
    # 그런 스텝은 방어가 아니라 가드를 여는 스텝이었다: 식별자 스캔이 보는 본문에서 자리
    # 표시자를 지우면 그 자리표시자가 미화이트리스트 식별자로 안 잡히고 통과해 버린다.
    # 벡터절 밖의 `%s`/`%(name)s`(예: `WHERE model = %s`)는 여전히 forbidden_column으로
    # 거부돼야 한다 — run_select()가 params 없이 호출되므로, 통과시키면 psycopg 문법
    # 오류로 400이 500이 된다(Spec Change Log 3차 패스, Design Notes 참조).
    # 식별자(order by embedding·vector)는 대소문자 무관하게 인식하되, 자리표시자(%s·%(name)s)는
    # 대소문자를 구분한다(review pass 4 수정) — 전역 IGNORECASE였을 때 `%S`(대문자)도 매치돼
    # 벡터절이 통째로 지워졌는데, `%S`는 psycopg가 인식하는 자리표시자가 아니라 절대 바인딩되지
    # 않는다. (?i:...) 로컬 플래그로 식별자 부분만 대소문자 무시를 유지한다.
    # 절의 "끝"도 고정한다(review pass 5). 끝을 안 잠그면 매치 뒤에 뭐가 붙든 그 절이 통째로
    # 지워져, 절 모양이 아니라 "접두사"만 검사하는 셈이 된다 — 실측으로 세 형태가 통과했다:
    #   `... <=> %s::vector DESC`        → <=>는 거리 연산자라 DESC는 "가장 안 닮은 순"이 된다
    #                                      (가드는 통과시키고 결과만 조용히 뒤집힌다)
    #   `... <=> %s::vector, price`      → 검증된 적 없는 2차 정렬키가 딸려 들어온다
    #   같은 절 2번 반복                  → ORDER BY가 둘인 실행 불가 SQL이 통과해 psycopg
    #                                      문법 오류 → 400이 500이 된다
    # 그래서 벡터절 뒤에는 문장 끝·LIMIT·OFFSET만 올 수 있게 lookahead로 못박는다. 여기 안
    # 걸리는 변형(괄호·복합 정렬키 등)은 지워지지 않으므로 embedding/vector가 미화이트리스트
    # 식별자로 남아 forbidden_column으로 거부된다 — 넓히는 쪽이 아니라 막는 쪽으로 실패한다.
    # DW-555: 13.3(hybrid_rag_node)은 별칭·2차 정렬키 없이 정확히 이 모양(`ORDER BY
    # embedding <=> %s::vector LIMIT <정수>`)만 코드로 조립해 쓰므로, 이 정규식을 넓힐
    # 필요가 없음을 hybrid_rag_node 구현·테스트로 확인 완료(DW-555 닫음).
    no_vector = re.sub(
        r"(?i:order\s+by\s+embedding)\s*<=>\s*(?:%s|%\(\w+\)s)\s*::\s*(?i:vector)"
        r"(?=\s*$|\s+(?i:limit|offset)\b)",
        " ",
        no_strings,
    )

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
    # 써서 sold까지 새어나간다(ai_readonly RLS는 Story 17.4(0035/0036)로 판매자 활성 여부만
    # 걸러졌을 뿐 sold는 여전히 못 거름 → 이 쿼리가 유일 방어선). 그래서 OR 자체를 거부해 status
    # 필터가 항상 AND로 유효하게 만든다(프롬프트 규칙 ③ 동일 의도).
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

    # 영문 식별자만 추출해 컬럼 화이트리스트 검사. 하이브리드 벡터절이 이미 지워진 no_vector를
    # 써서, 그 절 안의 embedding/vector/자리표시자만 위치-스코프로 통과시킨다(위 주석 참조).
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", no_vector.lower()))
    unknown = words - _SQL_KEYWORDS - ALLOWED_TABLES - ALLOWED_COLUMNS
    if unknown:
        # 화이트리스트에 없는 식별자(환각 컬럼·함수 등) → 거부(fail-closed).
        raise SqlGuardError(
            "forbidden_column",
            "허용되지 않는 컬럼 또는 식별자가 포함되어 있습니다.",
        )

    # ── 4) FR11 — status = 'on_sale' 필수(구조적 검사, DW-557 review-2) ────
    # RLS는 ai_readonly에 sold를 못 거른다 → 쿼리가 직접 on_sale을 강제해야 한다(함정 #2).
    # "문자열 존재"도, "알려진 부정 표현 나열"도 아니라 — WHERE절을 sqlparse로 토큰
    # 파싱해 최상위 AND 결합항 중 부정·재비교 없는 `status = 'on_sale'`이 실제로 있는지
    # 구조적으로 확인한다(_has_unnegated_status_on_sale, 위 정의 참조). stmt는 이미
    # 파싱돼 있으므로 재파싱하지 않는다.
    if not _has_unnegated_status_on_sale(stmt):
        raise SqlGuardError(
            "missing_status_filter",
            "판매중 매물만 조회할 수 있도록 status = 'on_sale' 조건이 필요합니다.",
        )

    # ── 8) LIMIT·OFFSET 절 중복 금지 (DW-558, bare-integer 전체 앵커링의 일부) ──────
    # 번호를 8부터 잇는 이유(13.3 리뷰 패치): 위 1~6이 이미 4)·5)·6)을 한 번씩 쓰고,
    # 4) FR11이 그걸 재사용하는 건 이 diff 이전부터 있던 상태라 손대지 않는다(A3) —
    # 그 뒤를 5)·6)·7)로 이으면 위 5) 서브쿼리·6) 테이블/컬럼과, 그리고 파일 끝의
    # 기존 단독 7) 통과와 또 충돌한다. 겹치지 않는 새 번호(8~11)로 이어 붙인다.
    # 정상 SQL은 LIMIT·OFFSET이 각각 최대 1개다. `LIMIT 5 LIMIT 999`처럼 절이 두 번
    # 등장하면, 뒤에서 하는 숫자 매처(re.search는 첫 성공 매치만 본다)가 두 번째 절의
    # 값만 보고 첫 번째 절의 존재를 놓칠 수 있다 — 그 틈에서 "값은 상한 이내"로 우연히
    # 통과하면 실행 단계에서 psycopg 문법 오류(이중 LIMIT은 실행 불가)로 400이 500이
    # 된다(DW-558). 개수 검사를 먼저 해 이 형태를 값 판정 이전에 명시 거부한다.
    if len(re.findall(r"\blimit\b", no_strings, re.IGNORECASE)) > 1:
        raise SqlGuardError(
            "limit_malformed",
            "LIMIT 절이 두 번 이상 등장합니다. LIMIT은 한 번만 사용해 주세요.",
        )
    if len(re.findall(r"\boffset\b", no_strings, re.IGNORECASE)) > 1:
        raise SqlGuardError(
            "offset_malformed",
            "OFFSET 절이 두 번 이상 등장합니다. OFFSET은 한 번만 사용해 주세요.",
        )

    # ── 9) OFFSET 상한 검사 ────────────────────────────────────────
    # OFFSET은 "앞에서 N건 건너뛰기". 상한이 없으면 OFFSET 999999처럼 DB를 통째로 훑는
    # 우회 조회가 통과한다. 부호([-+]?)까지 잡아 음수/과도한 값을 모두 거부한다(MAX_LIMIT와 동일 정책).
    # no_strings(리터럴 제거본)로 검사한다 — cleaned로 검사하면 description 등 자유텍스트
    # 리터럴 안의 우연한 "offset 999999" 같은 숫자가 실제 OFFSET절보다 먼저 매치돼 이
    # 검사를 우회시킨다(3차 리뷰 패스 수정 — limit_malformed 분기에만 적용됐던 규칙을
    # 짝이 되는 숫자 매처에도 동일 적용). 반환값(normalized)은 계속 cleaned 기반이다
    # (리터럴이 지워진 SQL을 실행하면 안 되므로).
    # 값 뒤(lookahead)를 문장 끝 또는 LIMIT 절로 앵커링한다(DW-558) — 전엔 "OFFSET" 뒤
    # 첫 정수만 부분 매치해 `OFFSET 5 (999999)`·`OFFSET 500+600`처럼 값 뒤에 다른 토큰이
    # 붙어도 앞의 5·500만 보고 통과시켰다(가짜 값이 실제 우회분을 가렸다). 이제 값 뒤에
    # 절 경계가 아닌 무엇이 오면 매치 자체가 실패해 아래 elif(offset_malformed)로 떨어진다.
    offset_match = re.search(
        r"\boffset\s+([-+]?\d+)(?=\s*$|\s+limit\b)", no_strings, re.IGNORECASE
    )
    if offset_match:
        off = int(offset_match.group(1))
        if off < 0 or off > MAX_OFFSET:
            raise SqlGuardError(
                "offset_exceeded",
                f"건너뛸 수 있는 매물 수(OFFSET)는 최대 {MAX_OFFSET}건입니다.",
            )
    elif re.search(r"\boffset\b", no_strings, re.IGNORECASE):
        # OFFSET 키워드는 있는데 위 앵커링된 숫자 패턴에 안 걸리는 형태
        # (`OFFSET 5 (999999)`·`OFFSET 500+600`) — 조용히 통과시키지 않고 명시 거부한다
        # (DW-558 신규 offset_malformed, limit_malformed와 동일 설계).
        raise SqlGuardError(
            "offset_malformed",
            "OFFSET 형식을 인식할 수 없습니다. 정수 리터럴(예: OFFSET 10)로 작성해 주세요.",
        )

    # ── 10) LIMIT 검사·주입 ─────────────────────────────────────────
    # 부호([-+]?)까지 함께 잡는다. 안 그러면 `LIMIT -1`이 "LIMIT 없음"으로 오인돼
    #   `LIMIT -1 LIMIT 5`라는 실행 불가 SQL이 만들어진다(코드리뷰 후속 버그). 음수·0은 거부.
    # no_strings로 검사 — 위 OFFSET과 동일 이유(리터럴 속 "limit 3" 같은 숫자가 먼저 매치돼
    # MAX_LIMIT 상한 검사를 우회하는 것을 막는다, 3차 리뷰 패스 수정).
    # 값 뒤(lookahead)를 문장 끝 또는 OFFSET 절로 앵커링한다(DW-558) — 전엔 "LIMIT" 뒤
    # 첫 정수만 부분 매치해 `LIMIT 5+100`·`LIMIT 10, 5`처럼 값 뒤에 다른 토큰이 붙어도
    # 앞의 5·10만 보고 통과시켰다(예: `LIMIT 5+100`이 n=5로 판정돼 MAX_LIMIT 상한 검사를
    # 우회하고 실행 시 95행 전량이 반환됐다 — DW-558 실측). 이제 값 뒤에 절 경계가 아닌
    # 무엇이 오면 매치 자체가 실패해 아래 elif(limit_malformed)로 떨어진다.
    limit_match = re.search(
        r"\blimit\s+([-+]?\d+)(?=\s*$|\s+offset\b)", no_strings, re.IGNORECASE
    )
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
    elif re.search(r"\blimit\b", no_strings, re.IGNORECASE):
        # no_strings(문자열 리터럴 이미 제거됨)로 검사 — cleaned로 검사하면 description 등
        # 자유텍스트 리터럴 안의 우연한 "limit" 단어(예: 'no limit here')가 이 분기를 잘못
        # 태워 정상 쿼리를 limit_malformed로 오탐 거부한다(코드리뷰 패치).
        # LIMIT 키워드는 있는데 위 앵커링된 숫자 패턴에 안 걸리는 형태(예: `LIMIT (10)`·
        # `LIMIT 5+100`·`LIMIT 10, 5`) — 조용히 뒤에 LIMIT 5를 이어붙이면 이중 LIMIT의
        # 깨진 SQL이 실행 단계에서야 터진다(DW-315·DW-558). 형식 오류로 명시 거부한다
        # ("값은 잡았는데 0 이하"인 limit_invalid와는 원인이 달라 코드를 분리한다 — Design Notes 참조).
        raise SqlGuardError(
            "limit_malformed",
            "LIMIT 형식을 인식할 수 없습니다. 정수 리터럴(예: LIMIT 10)로 작성해 주세요.",
        )
    else:
        # LIMIT 없으면 끝에 append — append는 결정론적으로 안전(WHERE 변형 위험 없음).
        normalized = f"{cleaned} LIMIT {DEFAULT_LIMIT}"

    # ── 11) 통과 — 정규화된 안전 SQL 반환 ──────────────────────────
    return normalized
