"""조합형(구조+의미) 하이브리드 검색 노드 — SQL+벡터 단일쿼리(FR45, Story 13.3).

흐름: 자연어 질의 → (가이드 질의확장, 있으면) → (Gemini) WHERE 구조조건만 추출
  → 코드가 벡터절·LIMIT를 붙여 조립 → sql_guard 검증 → ai_readonly 실행(임베딩 바인딩)
  → ListingCard.
  · LLM은 WHERE 구조조건 표현식만 낸다 — SELECT/status/ORDER BY/LIMIT은 절대 언급하지
    않는다. 그 절들은 **코드**가 정확히 `ORDER BY embedding <=> %s::vector LIMIT <정수>`
    모양으로 붙인다(I4, sql_guard의 벡터절 정규식이 기대하는 자리 — Story 13.1 주석 참조).
  · 구조조건을 하나도 못 뽑으면(순수 용도·느낌만 있는 질의) doc_rag_node(query, qvec=qvec)를
    그대로 호출해 폴백한다(기존 벡터검색 재사용, 별도 폴백 SQL을 새로 쓰지 않는다 — 드리프트
    방지). qvec을 넘겨 재시도 루프 진입 전 이미 계산한 임베딩을 재사용한다 — 안 넘기면
    doc_rag_node가 embed_query(query)를 다시 계산해 Gemini 임베딩 API를 중복 호출한다
    (코드리뷰: 바로 이 폴백 경로가 이 스토리가 없애려던 재임베딩을 다시 만들 뻔했다).
  · 조립된 SQL은 항상 validate_select_sql()을 거친다(LLM 생성 텍스트를 신뢰하지 않는다,
    함정 #1). 가드 차단 시 sql_rag_node와 동일한 1회 재생성 재시도 패턴을 따른다.
  · 가드 통과 후 embed_query로 만든 질의 임베딩을 %s 자리표시자에 실제로 바인딩해
    run_select(safe_sql, (qvec,))로 실행한다(DW-559 — 미바인드 실행 방지).
  · 질의확장(FR44, Story 13.6): 재시도 루프 진입 전 1회 `find_relevant_guide()`로 top-k 상대
    게이트(FR49)를 통과한 가이드 목록을 조회한다. 그중 상위 최대 `_GUIDE_INJECT_MAX`건만,
    그리고 content 누적 글자수가 `_GUIDE_INJECT_CHAR_CAP`을 넘기 전까지만 시스템 프롬프트에
    덧붙여 LLM이 "패밀리카" 같은 느낌 표현을 가이드가 제시하는 구조조건(body_type 등)으로
    바꾸게 한다 — 무조건 곁들이지 않는다(서로 다른 페르소나 섹션의 가이드가 전부 들어가면
    조건 AND 폭발로 0건이 되거나 프롬프트가 비대해진다). 최종 answer 인용은 doc_rag_node와
    동일하게 상위 최대 2개 제목을 결정론적으로 붙인다(답변 문장 자체는 LLM이 새로 짓지 않는다).

Design Notes(spec 13.3): 하이브리드 조립은 가드 통과 "직전"에 완성한다 — LLM 조건 →
  코드가 전체 SQL 문자열로 합친 뒤에야 validate_select_sql()을 부른다. 가드를 먼저
  부르고 나중에 벡터절을 이어붙이면 정규식이 못 보는 위치에 결합돼 embedding/vector가
  미화이트리스트 식별자로 거부된다.

13.3은 이 함수를 "호출 가능한 노드"로만 만든다. graph.py가 HYBRID 분기를 이 노드로 배선한다.
[Source: spec-13-3-하이브리드-검색-sql-벡터.md; sql_guard.py 벡터절 정규식 주석(13.1);
 spec-13-6-가이드-문서-content-활용-거리-컷오프.md]
"""

import logging
import re

import psycopg
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.db.readonly import run_select
from app.db.sql_guard import (
    DEFAULT_LIMIT,
    SqlGuardError,
    validate_select_sql,
)
from app.embeddings import embed_query
from app.graph.doc_rag_node import citation_titles, doc_rag_node
from app.graph.listing_cards import SELECT_COLUMNS, attach_cover_images, rows_to_cards
from app.graph.multi_query import find_relevant_guides_fused
from app.graph.sql_rag_node import _DOMAIN_RULES, _content_to_text, _strip_sql

logger = logging.getLogger(__name__)

# ListingCard 7필드 — SELECT 컬럼 순서는 공유 헬퍼(listing_cards)에 단일출처로 둔다(경로 A·B와 공유).
_SELECT_COLUMNS = SELECT_COLUMNS

# 구조조건 추출 전용 규칙 — 도메인 규칙(_DOMAIN_RULES, sql_rag_node에서 재사용)에 이 규칙만
# 덧붙인다. SELECT/status/ORDER BY/LIMIT은 코드가 붙이므로 LLM에게 언급을 금지한다(I4).
_HYBRID_INSTRUCTIONS = """[구조조건 추출 규칙 — 반드시 지켜라]
1. 질의에서 구조적으로 판별 가능한 조건(가격·연식·주행거리·차종·색상·연료·변속기·배기량·
   인승·무사고 여부·옵션 등)만 뽑아 WHERE에 들어갈 조건 표현식 한 줄로 출력한다.
2. 느낌·용도 표현(무난한·가성비·패밀리카·데일리용 등)이 섞여 있어도 **구조 조건이 하나라도
   있으면 반드시 그것만 뽑아 출력한다** — 느낌 표현은 무시하고 버려라. 그건 네가 아니라
   코드가 벡터검색으로 처리한다. 질의가 애매해 보인다는 이유로 NONE을 내면 안 된다.
   예: "3천만원 이하로 무난한 패밀리카" → `price <= 30000000`  ("무난한 패밀리카"는 버린다)
   예: "주행거리 5만 이하 깔끔한 차"     → `mileage <= 50000`
3. 구조 조건이 **정말 하나도 없을 때만**(예: "무난한 차 추천해줘") 다른 말 없이 정확히
   `NONE`만 출력한다.
4. `SELECT`·`status`·`ORDER BY`·`LIMIT`은 절대 언급하지 않는다 — 코드가 붙인다.
5. 조건은 AND 로만 결합한다. OR 는 절대 쓰지 않는다.
6. `WHERE`·`AND`로 시작하지 않는다 — 조건 표현식 자체만 낸다(코드가 `AND (...)`로 감싼다).
7. 조건 표현식(또는 `NONE`) 한 줄만 출력한다. 설명·코드펜스(```)·세미콜론·주석을 붙이지 않는다."""

_SYSTEM_PROMPT = f"""너는 중고차 매물 DB 검색을 위해 WHERE 구조조건만 뽑는 조수다. listings 테이블만 다룬다.

{_DOMAIN_RULES}

{_HYBRID_INSTRUCTIONS}

출력: 조건 표현식 한 줄 또는 NONE."""

# top-k 상대 게이트(FR49, doc_rag_node._GUIDE_TOP_K/_GUIDE_MARGIN/_GUIDE_DISTANCE_CEILING)
# 통과분 중 실제로 프롬프트에 주입할 개수·글자수 상한 — 전부 넣으면 서로 다른 페르소나
# 섹션의 가이드가 뒤섞여 조건 AND 폭발로 0건이 되거나 프롬프트가 비대해진다.
_GUIDE_INJECT_MAX = 3
_GUIDE_INJECT_CHAR_CAP = 3000

# 가이드 질의확장(FR44, Story 13.6) — find_relevant_guide()가 top-k 상대 게이트로 찾아낸
# 가이드마다 이 블록을 이어 붙인다. content를 시스템 프롬프트 뒤에 덧붙이는 블록.
_GUIDE_BLOCK_TEMPLATE = """

[참고 가이드 문서 — "{title}"]
{content}"""

# 여러 가이드 블록 뒤에 1회만 붙는 우선순위 지시문. 규칙 2(느낌 표현 버리기)보다 이 매핑이
# 우선한다는 것을 명시해, LLM이 "패밀리카" 같은 느낌 표현을 가이드가 제시하는 구조조건으로
# 바꾸게 한다. 이 지시문은 조건추출에만 쓰이고 답변 문장을 새로 짓는 데는 쓰이지 않는다
# (답변 인용은 hybrid_rag_node가 결정론적 문자열 붙이기로 별도 처리, AC2).
_GUIDE_PRIORITY_NOTE = """

위 가이드 매핑은 규칙 2(느낌·용도 표현 버리기)보다 우선한다 — 질의의 느낌·용도 표현이 위
가이드가 제시하는 구조조건(차종·인승 등)과 대응되면, 규칙 2로 버리지 말고 그 구조조건을
뽑아 출력한다. 이 가이드 내용으로 답변 문장을 새로 짓지는 않는다(조건 추출에만 참고)."""

_ANSWER_FOUND = "조건에 맞는 매물 {n}건을 찾았어요."
_ANSWER_EMPTY = "조건에 맞는 매물이 없어요. 가격대나 차종 조건을 넓혀보세요."  # FR17 조건 완화 안내

# 최상급×HYBRID 정렬 충돌 — 옵션(b) 채택(spec-13-9 Design Notes). HYBRID는 벡터 유사도로만
# 정렬하고 최상급이 요구하는 가격 등 정렬은 반영하지 않는다(오늘도 이미 그렇게 동작 중) —
# 이 상수·헬퍼는 그 사실을 답변에 알리는 캐비엇만 추가한다(sql_guard·SQL 조립은 미변경).
# contextualize_node._SUPERLATIVE_PRICE_RE와 같은 어휘·모양("제일"·"가장" + 가격 형용사
# 근접)을 감지 목적만 다르게 쓴다 — 공유 유틸로 뽑지 않고 파일마다 지역 상수로 둔다
# (3줄 중복 < 조기 추상화, A2, Design Notes).
#
# ⚠️ 순서 무관 AND는 부족하다(코드리뷰 정정) — "제일"과 가격 형용사가 각각 문장 어디에나
# 있기만 하면 결합으로 오판된다. 실측: "가장 인기있는 싼타페 보여줘"는 "싼"이 "싼타페"의
# 부분문자열이라 매칭되고("싼" ⊂ "싼타페"), "가장 인기 많고 저렴한 SUV"·"제일 안전한 차인데
# 가격도 싸게"도 부사·형용사가 멀리 떨어진 서로 무관한 절인데 걸린다. 최상급 부사 바로 뒤
# 0~4자 이내에 가격 형용사가 와야만 "가격 정렬 요청"으로 본다(contextualize_node와 동일 정규식).
#
# ⚠️ 근접만으론 부족하다(코드리뷰 정정, 13.9 3차) — `\S{0,4}?`는 0자도 허용하므로 부사 **바로
# 뒤**에 차종명이 오면 여전히 오탐이었다(실측: "가장 싼타페 보여줘"·"제일 싼타페 보여줘"가
# True). 그래서 가격 형용사 뒤에 한글 음절이 이어지면 매칭하지 않는다 — "싼타페"의 "싼",
# "싸지 않은"의 "싸", "비싸도 되는"의 "비싸"가 여기서 걸러진다. `저렴`만 예외인데,
# "저렴한"처럼 관형형 어미가 붙는 게 정상 표기라 경계를 걸면 정상 질의가 죽는다(실측).
_SUPERLATIVE_PRICE_RE = re.compile(r"(제일|가장)\s*\S{0,4}?((싼|싸|비싼|비싸)(?![가-힣])|저렴)")
# ⚠️ 문구를 한 문장으로 줄였다(사용자 결정, 2026-08-05). 원래는 뒤에 "구조적 조건만으로 다시
# 물어보시면 가격순으로 볼 수 있어요(예: …)"라는 재질의 안내가 붙어 있었는데, 실제 답변 본문이
# "조건에 맞는 매물 5건을 찾았어요." 한 줄이라 **안내가 답변보다 길었고**, 자기가 못 한 일을
# 사용자 숙제로 넘기는 인상이었다. 고지 자체는 남긴다 — 없애면 "제일 싼"이라고 물은 사용자가
# 가격순이 아닌 결과를 아무 설명 없이 받게 된다(그게 이 상수의 존재 이유다).
_SUPERLATIVE_CAVEAT = "가격순 정렬은 반영되지 않았어요."


def _has_superlative(query: str) -> bool:
    """질의에 최상급 부사("제일"·"가장")와 가격 형용사가 근접해서 함께 있는지.

    router_node의 프롬프트 규칙(최상급 부사+가격 형용사 결합만 구조조건)과 판정 기준을
    맞춘다 — 부사만 있는 비가격 최상급("가장 안전한", "가장 인기있는")은 여기서 False다.
    부사·형용사가 문장 안에 각각 따로 있어도(순서 무관 AND) 결합으로 오판하지 않도록
    근접 정규식으로 판정한다(코드리뷰 정정 — "가장 인기있는 싼타페"의 "싼"이 차종명
    "싼타페"의 부분문자열일 뿐인데 결합으로 잘못 잡히던 문제 포함).
    """
    return bool(_SUPERLATIVE_PRICE_RE.search(query))


# 폴백 신호(NONE) 인식 — 정확히 "NONE"만 보면 LLM이 `NONE.`·`"NONE"`처럼 살짝 어긋나게
# 낼 때 폴백을 놓치고, 그 문자열이 조건으로 조립돼 가드 차단(400)까지 간다(실측: `NONE.`
# → forbidden_column). 따옴표·백틱·마침표·공백만 두른 형태는 전부 폴백으로 읽는다.
_NONE_SENTINEL_RE = re.compile(r"""^["'`.\s]*none["'`.\s]*$""", re.IGNORECASE)

# 가드는 통과했지만 DB가 실행하지 못하는 조건일 때 사용자에게 나가는 메시지.
# code는 sql_guard의 차단 코드와 겹치지 않는 별도 값 — 라우터(ai.py)가 SqlGuardError를
# 400으로 매핑하므로, 이 변환이 없으면 psycopg 예외가 그대로 올라가 500이 된다.
_NOT_EXECUTABLE_MESSAGE = "검색 조건을 이해하지 못했어요. 조건을 조금 더 간단히 말씀해 주세요."


def _llm() -> ChatGoogleGenerativeAI:
    """구조조건 추출용 LLM. temperature=0으로 같은 질의에 같은 조건이 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _vec_literal(vec: list[float]) -> str:
    """list[float] → pgvector 텍스트 리터럴 "[v1,v2,...]"(doc_rag_node와 동일 로직, 3줄 중복 허용).

    이 문자열을 %s 파라미터로 바인딩하고 SQL에서 ::vector로 캐스팅한다(사용자값/벡터를
    f-string으로 SQL에 직접 박지 않는다 — 항상 파라미터 바인딩).
    """
    return "[" + ",".join(map(str, vec)) + "]"


def _select_guides_to_inject(
    guides: list[tuple[str, str]],
) -> list[tuple[str, str]]:
    """게이트를 통과한 가이드 중 실제로 프롬프트에 주입할 것만 추린다.

    상위 최대 `_GUIDE_INJECT_MAX`개를 우선 자르고, content 누적 글자수가
    `_GUIDE_INJECT_CHAR_CAP`을 넘기는 순간부터는 넘긴 문서부터 제외한다(그 앞까지는
    담는다) — 서로 다른 페르소나 섹션의 상충 매핑이 전부 프롬프트에 들어가 조건 AND
    폭발로 0건이 되는 것과 프롬프트 비대화를 막는다.
    """
    selected: list[tuple[str, str]] = []
    total_chars = 0
    for title, content in guides[:_GUIDE_INJECT_MAX]:
        if total_chars + len(content) > _GUIDE_INJECT_CHAR_CAP:
            break
        selected.append((title, content))
        total_chars += len(content)
    return selected


def _append_retry_turn(messages: list, text: str, reason: str) -> None:
    """재생성 요청 1턴을 대화에 덧붙인다(가드 차단·실행 불가 두 경로가 같은 문구를 쓴다)."""
    messages.append(("ai", text))
    messages.append((
        "human",
        f"방금 조건으로 {reason}. 구조조건 표현식만 위 규칙을 모두 지켜서 한 줄로 다시 "
        "출력해(SELECT/status/ORDER BY/LIMIT 언급 금지, `WHERE`·`AND`로 시작하지 말 것).",
    ))


def hybrid_rag_node(query: str) -> dict:
    """조합형 질의를 받아 {"answer": str, "listings": list[ListingCard]}를 반환한다.

    GEMINI_API_KEY/DATABASE_URL 부재 시 embed_query/run_select 내부 require()가 명확한
    한국어 에러로 즉시 실패한다. 가드 차단은 1회 재생성 후에도 막히면 SqlGuardError를
    상위로 전달한다(sql_rag_node와 동일 계약 — graph.py가 삼키지 않고 전파).

    "가드는 통과했지만 실행이 안 되는 조건"(psycopg ProgrammingError/DataError)도 같은
    재시도 대상이며, 2회째도 실패하면 SqlGuardError로 변환해 전달한다 — 사용자에게는
    500이 아니라 400 한국어 안내가 나가야 한다는 계약을 지키기 위해서다.

    질의확장(FR44, Story 13.6): 재시도 루프 진입 전에 질의 임베딩을 1회만 계산해(재시도마다
    재임베딩하던 기존 낭비 제거) find_relevant_guide()에 넘긴다. top-k 상대 게이트(FR49)를
    통과한 가이드 중 주입 상한(_GUIDE_INJECT_MAX/_GUIDE_INJECT_CHAR_CAP) 이내분을 시스템
    프롬프트에 덧붙이고, listings가 나오면 doc_rag_node와 동일하게(상위 최대 2개 제목)
    결정론적 인용을 붙인다.
    """
    llm = _llm()  # 키 부재 시 여기서 fail-loud — 아래 재시도 루프 전에 즉시 실패.

    qvec = embed_query(query)  # 키 부재 시 여기서 fail-loud — 재시도 루프 전 1회만 계산.
    qvec_literal = _vec_literal(qvec)
    # multi-query 분해 + RRF 병합(질의 희석 완화) — 짧은 질의는 내부에서 자동으로 원 질의
    # 단독 검색과 동일하게 동작한다(추가 임베딩 호출 0회, app/graph/multi_query.py).
    guides = find_relevant_guides_fused(query, qvec_literal)

    system_prompt = _SYSTEM_PROMPT
    injected_guides = _select_guides_to_inject(guides)
    if injected_guides:
        blocks = "".join(
            _GUIDE_BLOCK_TEMPLATE.format(title=title, content=content)
            for title, content in injected_guides
        )
        system_prompt += blocks + _GUIDE_PRIORITY_NOTE

    messages = [("system", system_prompt), ("human", query)]
    last_error: SqlGuardError | None = None

    for attempt in range(2):  # 최초 1회 + 재시도 1회
        raw = llm.invoke(messages).content
        text = _content_to_text(raw)
        condition = _strip_sql(text)
        condition_stripped = condition.strip()
        logger.info("hybrid_rag_node attempt %d 구조조건: %s", attempt + 1, condition)

        if not condition_stripped or _NONE_SENTINEL_RE.match(condition_stripped):
            # 구조조건 미추출(정확히 NONE이거나 빈/공백 응답) — 별도 폴백 SQL을 새로 쓰지
            # 않고 기존 벡터검색을 그대로 재사용한다. 빈 응답을 NONE과 다르게 취급하면
            # 아래에서 `AND ()`라는 깨진 SQL이 조립돼(가드는 다른 AND항인 status='on_sale'
            # 만으로 통과시키므로 못 잡는다) 실행 단계에서 psycopg 문법 오류로 죽는다.
            result = doc_rag_node(query, qvec=qvec)  # 위에서 계산한 임베딩 재사용(코드리뷰 — 재임베딩 제거)
            # 이 폴백은 스펙 예시("제일 싼 패밀리카")가 실제로 타는 경로다(구조조건이 하나도
            # 없는 순수 최상급+의미 질의) — 정상 SQL 조립 분기에만 캐비엇을 붙이면 바로 이
            # 예시 케이스가 캐비엇 없이 나간다(코드리뷰 정정).
            if result["listings"] and _has_superlative(query):
                result = {**result, "answer": f"{result['answer']} {_SUPERLATIVE_CAVEAT}"}
            return result

        # psycopg는 params가 있으면(아래 run_select) SQL 문자열 전체에서 '%'를 자리표시자로
        # 스캔한다 — 따옴표 리터럴 안(예: `model LIKE '%아반떼%'`)도 예외가 아니다. sql_guard의
        # 리터럴 스트립(no_strings)은 검증에서만 그 '%'를 무시하고, 반환값(cleaned)엔 그대로
        # 남기 때문에 여기서 미리 이스케이프하지 않으면 통과된 SQL이 실행 단계에서 psycopg
        # ProgrammingError(또는 멀티바이트 리터럴이면 UnicodeDecodeError)로 죽는다(400이 아니라
        # 500 — DW-559와 같은 부류의 회귀). LLM이 낸 부분만 이스케이프하고, 코드가 붙이는
        # 벡터절의 진짜 %s 자리표시자는 이스케이프 뒤에 그대로 이어붙인다.
        base_sql = (
            f"SELECT {_SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' "
            f"AND ({condition})"
        ).replace("%", "%%")
        sql = f"{base_sql} ORDER BY embedding <=> %s::vector LIMIT {DEFAULT_LIMIT}"
        try:
            safe_sql = validate_select_sql(sql)  # 가드 통과 못하면 SqlGuardError
            rows = run_select(safe_sql, (qvec_literal,))  # DW-559 — 임베딩 바인딩(호이스트 재사용)
            listings = attach_cover_images(rows_to_cards(rows))
            answer = _ANSWER_FOUND.format(n=len(listings)) if listings else _ANSWER_EMPTY
            # 공백 제목은 find_relevant_guide가 이미 걸렀으니 guides의 title은 항상 비어
            # 있지 않다(3회차 코드리뷰). `listings and`가 실제 게이트다: 0건이면 FR17 안내에
            # 인용을 붙이지 않는다(AC3, I/O 매트릭스 5행). 이 조건이 사라져도 스위트가
            # 초록이던 구멍은 test_hybrid_empty_result_with_guide_omits_citation이 닫는다.
            # 인용은 주입 상한(_select_guides_to_inject)과 무관하게 게이트 통과분 전체(guides)
            # 중 citation_titles로 문서명 기준 중복 제거 후 상위 최대 2개를 쓴다 —
            # doc_rag_node와 동일한 규칙(AC2, 청킹 후 인용 장황화 방지 공유 헬퍼).
            if listings and guides:
                titles = citation_titles(guides)
                answer += f" (참고: {', '.join(titles)})"
            if listings and _has_superlative(query):
                # 최상급이 있어도 HYBRID는 벡터 정렬만 적용한다 — 그 사실을 알린다(옵션 b).
                # 0건이면(listings 없음) 이 캐비엇도 인용과 같은 이유로 붙이지 않는다.
                answer += f" {_SUPERLATIVE_CAVEAT}"
            return {"answer": answer, "listings": listings}
        except SqlGuardError as exc:
            # 가드 차단만 재시도 대상 — LLM이 조건을 고치면 통과할 여지가 있다.
            last_error = exc
            logger.warning("hybrid_rag_node attempt %d 가드 차단: %s", attempt + 1, exc.message)
            _append_retry_turn(messages, text, f"조립한 SQL이 거부됐어: {exc.message}")
        except (psycopg.ProgrammingError, psycopg.DataError) as exc:
            # 가드를 통과했지만 DB가 실행하지 못하는 조건 — 조각(`AND (<조건>)`)으로 합치는
            # 구조 때문에 "가드는 통과하는데 실행은 안 되는" 형태가 존재한다(실측: `WHERE
            # price <= N`·`AND price <= N`·`price <= N AND`·`price`·`price < (100`·`없음`
            # 전부 가드 통과 후 psycopg SyntaxError/DatatypeMismatch/UndefinedColumn).
            # 잡지 않으면 except SqlGuardError를 스쳐 지나가 400이 아니라 500이 된다 —
            # DW-559·`%` 이스케이프와 같은 부류의 실패가 다른 경로로 재발하는 자리다.
            # 연결 장애(OperationalError)는 조건 문제가 아니므로 일부러 잡지 않는다(500 유지).
            last_error = SqlGuardError("condition_not_executable", _NOT_EXECUTABLE_MESSAGE)
            logger.warning("hybrid_rag_node attempt %d 실행 불가 조건: %s", attempt + 1, exc)
            _append_retry_turn(
                messages, text, "조립한 SQL이 실행되지 않았어(문법/타입 오류)"
            )

    # 최초+재시도 모두 가드 차단 — 마지막 가드 에러를 그대로 전달(사용자에게 의미 있는 한국어 400).
    assert last_error is not None
    raise last_error
