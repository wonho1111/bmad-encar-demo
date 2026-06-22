"""경로 A — Text-to-SQL 노드.

흐름: 자연어 질의 → (Gemini) SELECT 생성 → sql_guard 검증 → ai_readonly 실행 → ListingCard.
  · LLM이 만든 SQL은 절대 그대로 믿지 않는다 — 항상 validate_select_sql()을 거친다(함정 #1).
  · 실행은 항상 ai_readonly 롤(run_select)로만 한다(이중 방어, 4.1 재사용).
  · 가드 차단 시 오류를 LLM에 1회만 재주입해 재생성(무한루프 방지). 2회째도 차단이면 상위로.
    DB 오류(PsycopgError)는 재생성으로 못 고치므로 재시도하지 않고 그대로 상위(전역 500)로 보낸다.

4.3은 이 함수를 "호출 가능한 노드"로만 만든다. 전체 StateGraph(router→nodes→answer) 조립은 4.5.
[Source: story 4.3 sql_rag_node 설계·프롬프트 설계; research §4.1·4.3]
"""

import logging

from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import require, settings
from app.db.readonly import run_select
from app.db.sql_guard import (
    DEFAULT_LIMIT,
    MAX_LIMIT,
    SqlGuardError,
    validate_select_sql,
)
from app.graph.listing_cards import SELECT_COLUMNS, rows_to_cards

logger = logging.getLogger(__name__)

# ListingCard 7필드 — SELECT 컬럼 순서는 공유 헬퍼(listing_cards)에 단일출처로 둔다(경로 B와 공유).
_SELECT_COLUMNS = SELECT_COLUMNS

# 시스템 프롬프트 — 스키마·허용값·단위 정규화·불변 규칙을 LLM에 그대로 박는다.
# 허용값은 0002_listings.sql CHECK 목록과 정확히 일치(단일출처, drift 금지).
_SYSTEM_PROMPT = f"""너는 중고차 매물 DB를 검색하는 PostgreSQL SQL 생성기다. listings 테이블만 조회한다.

[스키마: listings 테이블 — 아래 컬럼과 허용값만 사용]
- id, manufacturer(제조사), model(모델·자유값), year(연식·정수), price(가격·원), mileage(주행거리·km),
  region(지역), body_type(차종), color(색상), fuel(연료), transmission(변속기),
  displacement(배기량·cc), seats(인승), accident_free(무사고 여부·boolean), status(상태),
  options(옵션 목록·text 배열. 예: ['후방카메라','스마트키','통풍시트','내비게이션','파노라마선루프'])
- manufacturer ∈ (현대,기아,제네시스,쉐보레,르노코리아,KG모빌리티,BMW,벤츠,아우디,폭스바겐,토요타,혼다,렉서스,테슬라,기타)
- body_type ∈ (경차,소형차,준중형차,중형차,대형차,스포츠카,SUV,RV,경승합차,승합차,화물차,기타)
- color ∈ (흰색,검정,회색,은색,파랑,빨강,갈색,녹색,기타)
- fuel ∈ (가솔린,디젤,하이브리드,전기,LPG)
- transmission ∈ (자동,수동)
- region ∈ (서울,부산,대구,인천,광주,대전,울산,세종,경기,강원,충북,충남,전북,전남,경북,경남,제주)

[불변 규칙 — 반드시 지켜라]
1. 반드시 `SELECT {_SELECT_COLUMNS} FROM listings` 로 시작한다.
2. WHERE 절에 `status = 'on_sale'` 을 항상 포함한다.
3. 조건은 AND 로만 결합한다. OR 는 절대 쓰지 않는다.
4. 특별히 더 많이 보여달라는 요청이 없으면 끝에 `LIMIT {DEFAULT_LIMIT}` 을 붙인다(최대 {MAX_LIMIT}).
5. SQL 한 문장만 출력한다. 설명·코드펜스(```)·세미콜론·주석을 붙이지 않는다.
6. id 는 UUID다. 비교(>,<,=)·정렬(ORDER BY)·페이지네이션(OFFSET)에 id 를 쓰지 마라
   (UUID를 숫자와 비교하면 DB 오류가 난다). "지금 것 말고 다른 거/더 보여줘"처럼 페이지네이션을
   요구해도, id 로 거르거나 OFFSET을 만들지 말고 기존 검색 조건을 그대로 유지해 조회한다.

[단위 정규화 — 자연어를 저장 단위(정수)로 변환]
- 주행거리: "만km" → ×10000 (예: "10만km 이하" → mileage <= 100000)
- 가격: "천만원"=10000000, "만원"=10000 (예: "3천만원 이하" → price <= 30000000)
- 방향: "이하/미만" → <= / < , "이상/초과" → >= / >

[차형 용어 매핑]
- 크기를 안 밝힌 "세단" → body_type IN ('준중형차','중형차','대형차')
- 크기를 밝힌 세단은 그 크기만 정확히 매핑한다: "준중형세단"→body_type = '준중형차',
  "중형세단"→body_type = '중형차', "대형세단"→body_type = '대형차' (넓게 IN으로 풀지 말 것)
- 데모에 없는 차형(해치백·쿠페 등)은 무리하게 매핑하지 말고 가격·기타 조건만 적용한다.

[옵션 필터 — options 배열]
- 사용자가 특정 옵션(예: 스마트키·통풍시트·후방카메라·내비게이션·파노라마선루프 등)을 요구하면
  `'<옵션명>' = ANY(options)` 형태로 정확히 거른다. 예: "스마트키 있는 거" → '스마트키' = ANY(options)
- 옵션이 여러 개면 각각의 `= ANY(options)` 조건을 AND 로 결합한다. 옵션명은 사용자 표현 그대로 쓴다.

출력: SQL 텍스트 한 줄만."""

_ANSWER_FOUND = "조건에 맞는 매물 {n}건을 찾았어요."
_ANSWER_EMPTY = "조건에 맞는 매물이 없어요. 가격대나 차종 조건을 넓혀보세요."  # FR17 조건 완화 안내


def _llm() -> ChatGoogleGenerativeAI:
    """SQL 생성용 LLM. temperature=0으로 같은 질의에 같은 SQL이 나오게 한다(재현성)."""
    return ChatGoogleGenerativeAI(
        model=settings.gemini_generation_model,  # gemini-3.1-flash-lite (env로 교체 가능)
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        temperature=0,
    )


def _content_to_text(content) -> str:
    """LLM 응답의 .content를 평문 텍스트로 만든다.

    일부 Gemini 모델은 .content를 문자열이 아니라 콘텐츠 블록 리스트
    (예: [{"type": "text", "text": "SELECT ..."}])로 돌려줄 때가 있다. 그 경우 text 블록만
    뽑아 이어 붙인다(이 처리를 안 하면 리스트가 통째로 문자열화돼 가드가 not_select로 막는다).
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return str(content)


def _strip_sql(text: str) -> str:
    """LLM 출력에서 코드펜스·앞뒤 공백을 제거해 순수 SQL만 남긴다."""
    s = text.strip()
    if s.startswith("```"):
        # ```sql ... ``` 형태 제거 — 첫 줄(``` 또는 ```sql)과 끝 ``` 를 떼어낸다.
        lines = s.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        s = "\n".join(lines).strip()
    return s


def sql_rag_node(query: str) -> dict:
    """자연어 질의를 받아 {"answer": str, "listings": list[ListingCard]}를 반환한다.

    GEMINI_API_KEY/DATABASE_URL 부재 시 require()가 명확한 한국어 에러로 즉시 실패(재시도 안 함).
    가드 차단은 1회 재생성 후에도 막히면 SqlGuardError를 상위로 전달한다.
    DB 오류(PsycopgError)는 재시도하지 않고 그대로 전파한다(전역 500 핸들러가 공통 포맷 처리).
    """
    llm = _llm()  # 키 부재 시 여기서 fail-loud — 아래 재시도 루프 전에 즉시 실패.

    # 대화 메시지 — 재시도 시 직전 SQL과 오류를 덧붙여 LLM이 스스로 고치게 한다.
    messages = [("system", _SYSTEM_PROMPT), ("human", query)]
    last_error: SqlGuardError | None = None

    for attempt in range(2):  # 최초 1회 + 재시도 1회
        raw = llm.invoke(messages).content
        text = _content_to_text(raw)
        sql = _strip_sql(text)
        logger.info("sql_rag_node attempt %d 생성 SQL: %s", attempt + 1, sql)

        try:
            safe_sql = validate_select_sql(sql)  # 가드 통과 못하면 SqlGuardError
            rows = run_select(safe_sql)           # ai_readonly 롤로 실행
            listings = rows_to_cards(rows)
            answer = _ANSWER_FOUND.format(n=len(listings)) if listings else _ANSWER_EMPTY
            return {"answer": answer, "listings": listings}
        except SqlGuardError as exc:
            # 가드 차단만 재시도 대상 — LLM이 SQL을 고치면 통과할 여지가 있다.
            # DB 오류(PsycopgError)는 여기서 잡지 않는다: 재생성으로 못 고치고(일시장애·권한 등),
            # 원본 DB 오류를 LLM 프롬프트에 주입할 이유도 없어 그대로 상위(전역 500)로 전파한다.
            last_error = exc
            logger.warning("sql_rag_node attempt %d 가드 차단: %s", attempt + 1, exc.message)
            # 직전 출력과 오류를 대화에 덧붙여 1회 재생성 요청.
            messages.append(("ai", text))
            messages.append((
                "human",
                f"방금 SQL이 거부됐어: {exc.message}. 위 불변 규칙을 모두 지켜서 SQL 한 줄만 다시 출력해.",
            ))

    # 최초+재시도 모두 가드 차단 — 마지막 가드 에러를 그대로 전달(사용자에게 의미 있는 한국어 400).
    assert last_error is not None  # 두 번 돌고도 return을 못 했다면 반드시 가드 차단이 있었다.
    raise last_error
