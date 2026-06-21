# Story 4.3: 경로 A — Text-to-SQL + 안전장치 (FR14)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 구매자,
I want 가격·차종·색상 같은 구조형 조건을 자연어 한 문장으로 말하면 정확히 필터된 매물을 받고 싶다,
so that 복잡한 필터 UI 없이 "3천만원 이하 흰색 SUV"처럼 대화로 조건 검색을 한다.

> **이 스토리의 본질:** 4.1이 "AI 앱이 뜨는 토대", 4.2가 "AI가 검색할 데이터"였다면, **4.3은 AI가 실제로 매물 DB를 검색하는 첫 경로(경로 A)** 다. 핵심은 **LLM이 만든 SQL을 그대로 믿지 않는 것** — LLM(대형 언어모델)이 자연어 질의를 SQL로 바꾸면, 코드가 **결정론적(deterministic·매번 같은 규칙)으로 그 SQL을 검사**해 위험하거나 범위 밖이면 실행 전에 차단한다. 두 덩어리다 — ①**Text-to-SQL 생성**(질의 → SELECT 쿼리, `sql_rag_node`), ②**안전장치**(`sql_guard`: SELECT 전용·테이블/컬럼 화이트리스트·기본 LIMIT·판매완료 제외 검증). 이게 끝나면 `/ai/search`가 stub을 벗고 실제 필터된 매물을 돌려준다.
>
> *Text-to-SQL: 자연어 질문을 SQL 쿼리로 자동 변환하는 기술.*
> *화이트리스트(whitelist): "이것만 허용" 목록. 허용된 테이블·컬럼만 쿼리에 등장할 수 있게 막는다.*
> *sqlparse: SQL 문자열을 토큰(낱말)으로 분해해 구조를 검사하게 해주는 파이썬 라이브러리.*

## Acceptance Criteria

1. **(AC1 — Text-to-SQL 노드)** `app/graph/sql_rag_node.py`의 `sql_rag_node`가 존재하고, "3천만원 이하 흰색 SUV" 류 구조형 질의가 오면 그 조건으로 필터된 **`on_sale` 매물**이 `ListingCard` 목록으로 반환된다. 0건이면 `listings: []` + `answer`에 조건 완화 안내(FR17). [FR14, FR11]
2. **(AC2 — sql_guard 통과 쿼리만 실행)** `app/db/sql_guard.py`의 가드가 적용되어, 실행되는 쿼리는 **① 단일 SELECT문 ② 화이트리스트 테이블(`listings`)·컬럼만 참조 ③ 기본 LIMIT 강제(없으면 주입, 상한 초과 차단) ④ `status = 'on_sale'` 포함** 검증을 모두 통과한 쿼리뿐이다.
3. **(AC3 — 위험·범위밖 쿼리 실행 전 차단, CM2)** SELECT 외 구문(INSERT/UPDATE/DELETE/DROP/ALTER 등), 다중 문장(`;` 스태킹), 주석, 비화이트리스트 테이블/컬럼이 생성되면 **실행 전에 차단**되고 사용자에겐 공통 에러 포맷으로 한국어 안내가 반환된다(서버 500 누출 금지).
4. **(AC4 — 자연어 단위 정규화)** 자연어 단위가 저장 단위로 정규화되어 비교된다 — "10만km" → `mileage <= 100000`, "3천만원" → `price <= 30000000` ([Source: docs/conventions.md §3]). "세단" 류 차체형태 용어는 `body_type` 허용값으로 매핑되거나(예: 세단→준중형차·중형차·대형차) 무시된다(OI5 규칙).

### 범위 밖 (이 스토리에서 구현하지 않음 — 과잉구현 금지)

- ❌ **라우터 의도 분류(A/B/C)** → **4.5**. 4.3은 `/ai/search`가 **모든 질의를 경로 A(Text-to-SQL)로** 처리한다(라우터는 4.5에서 sql_rag_node 앞에 삽입).
- ❌ **문서 RAG(경로 B)·`doc_rag_node`** → **4.4**.
- ❌ **가드 노드(경로 C·무관 질의 거절)·답변 조립 노드(`answer_node`)** → **4.5**. 4.3의 `answer`는 노드가 만든 **간단한 한국어 요약**(예: "조건에 맞는 매물 N건을 찾았습니다")이면 충분.
- ❌ **멀티턴 맥락(`context`) 반영** → **4.6**. 요청 스키마의 `context`는 받되 무시.
- ❌ **AI 검색 화면(웹 UI)** → **4.7**.
- ❌ **전체 LangGraph `StateGraph` 조립(router→nodes→answer 와이어링)** → **4.5**. 4.3은 `sql_rag_node`를 **호출 가능한 노드 함수**로 만들고 `/ai/search`가 직접 호출한다(최소 와이어링).
- ❌ **SQL Agent(ReAct 반복·`sql_db_*` 툴·스키마 자동 조회)** → 본 데모는 단일 고정 테이블이라 불필요. 아래 "설계 결정(OI2)" 참조.

## Tasks / Subtasks

- [x] **Task 1 — 의존성 추가(`sqlparse`) + `.[ai]` 설치 확인** (AC: 2, 3)
  - [x] 1.1 `api/pyproject.toml`의 `optional-dependencies.ai`에 `sqlparse` 추가(결정론적 SQL 검증용 — 연구 §4.2 명시). langgraph는 4.3에서 **노드 함수만** 쓰면 import 불필요할 수 있으나, 이미 ai 그룹에 선언됨.
  - [x] 1.2 `cd api && pip install -e ".[ai,dev]"`로 sqlparse·langchain-google-genai 설치 확인(4.2에서 ai 그룹은 이미 설치됨 — sqlparse만 추가 설치). → `.venv`에 sqlparse 0.5.5 설치 확인.

- [x] **Task 2 — `app/db/sql_guard.py` 결정론적 안전장치** (AC: 2, 3)
  - [x] 2.1 `validate_select_sql(sql: str) -> str` 작성. sqlparse로 파싱 후 아래 검증(아래 "sql_guard 설계" 규칙 그대로). 통과 시 **정규화된 안전 SQL**(LIMIT 주입 포함) 반환, 실패 시 `SqlGuardError`(코드·한국어 메시지) raise.
  - [x] 2.2 검증 규칙: ①단일 문장 ②첫 토큰이 `SELECT`(DML/DDL 키워드 거부) ③`;` 다중·주석(`--`,`/* */`) 거부 ④화이트리스트 테이블(`listings`)·컬럼만 등장 ⑤`status = 'on_sale'` 리터럴 존재(없으면 거부) ⑥`LIMIT` 없으면 `LIMIT {DEFAULT_LIMIT}` 주입, 있으면 상한(`MAX_LIMIT`) 초과 시 거부.
  - [x] 2.3 화이트리스트 상수: 테이블=`{"listings"}`, 컬럼=ListingCard 7필드 + 필터 컬럼(`body_type, color, fuel, transmission, price, mileage, year, displacement, seats, region, accident_free, status`) + `*` 금지(명시 컬럼만). 상수는 0002 단일출처와 일치.

- [x] **Task 3 — `app/graph/sql_rag_node.py` Text-to-SQL 노드** (AC: 1, 4)
  - [x] 3.1 `app/graph/__init__.py` 생성(패키지화). `sql_rag_node` 노드 함수 작성.
  - [x] 3.2 `ChatGoogleGenerativeAI`(model=`settings.gemini_generation_model`=`gemini-flash-latest`, `GEMINI_API_KEY`)로 질의→SELECT 생성. 시스템 프롬프트에 **스키마(화이트리스트 컬럼+CHECK 허용값)·단위 정규화 규칙·차형 용어 매핑·`status='on_sale'` 필수·LIMIT 필수·SQL만 출력**을 명시(아래 "프롬프트 설계").
  - [x] 3.3 생성 SQL → `validate_select_sql()` 통과 → `run_select()`(ai_readonly)로 실행 → 행을 `ListingCard`로 매핑.
  - [x] 3.4 가드 거부·실행 오류 시 **최대 1회** 오류 메시지를 LLM에 재주입해 재생성(무한루프 방지). 재시도도 실패하면 가드 에러를 그대로 상위로 전달.
  - [x] 3.5 `answer` 생성: 결과 건수 기반 간단 한국어 요약(0건이면 조건 완화 안내, FR17). LLM 추가 호출 없이 템플릿으로 충분.

- [x] **Task 4 — `/ai/search` 실연결(stub 제거)** (AC: 1, 3)
  - [x] 4.1 `app/routers/ai.py`의 stub을 `sql_rag_node` 호출로 교체. 인증 의존성(`get_current_user`)·응답 계약(`{answer, listings[]}`)은 유지.
  - [x] 4.2 `SqlGuardError`·LLM/DB 오류를 공통 에러 포맷으로 변환(가드 차단은 사용자에게 의미 있는 한국어 400으로, 그 외는 전역 핸들러가 공통 500). 비밀값(GEMINI_API_KEY/DATABASE_URL) 부재 시 4.1의 `require()` fail-loud로 명확히 실패.
  - [x] 4.3 `context` 필드는 받되 무시(4.6). `SearchResponse`/`ListingCard` 스키마 변경 없음(이미 4.1 확정).

- [x] **Task 5 — pytest 단위 테스트(가드) + 라이브 검증** (AC: 전체)
  - [x] 5.1 `tests/test_sql_guard.py`(네트워크 무관, 핵심): SELECT 통과 / DELETE·UPDATE·INSERT·DROP·ALTER 거부 / 다중문장(`;`)·주석 거부 / 비화이트리스트 테이블(`profiles`)·컬럼 거부 / LIMIT 없으면 주입·상한 초과 거부 / `status='on_sale'` 없으면 거부. **CM2 검증의 핵심**. → 20 케이스 통과.
  - [x] 5.2 라이브 검증(GEMINI_API_KEY+DATABASE_URL 필요, 4.2에서 입력됨): `sql_rag_node("3천만원 이하 흰색 SUV")` → 생성 SQL `... price <= 30000000 AND color = '흰색' AND body_type = 'SUV' LIMIT 50`, on_sale 흰색 SUV 2건 반환. MCP 교차검증 일치(전체 상태 3건 중 sold 1건 제외 → FR11 실증).
  - [x] 5.3 단위 정규화 라이브: `"주행거리 10만km 이하 디젤차"` → 생성 SQL에 `mileage <= 100000` 포함 확인(AC4), 디젤 11건 반환.
  - [x] 5.4 HTTP E2E: uvicorn 백그라운드(`:8000`) → 미인증 `POST /ai/search` 401(`unauthorized`)·잘못된 토큰 401 확인, `/health` 200. TestClient로 인증 통과 시 `{answer, listings[]}` 200·가드 차단 400 확인. 프로세스 정리(:8000 LISTENING 없음 확인).
  - [x] 5.5 키 부재로 라이브 불가 시: (해당 없음 — 키 존재로 라이브 전부 수행) 거짓 "완료" 없음.

- [x] **Task 6 — 보고 + 산출물 정리** (AC: 전체)
  - [x] 6.1 Completion Notes에 OI2 결정 근거·생성 SQL 예시·가드 거부 사례·단위 정규화 확인을 기록.
  - [x] 6.2 변경 파일을 File List에 기록.

## Dev Notes

### ⚠️ 결정적 함정 — 반드시 숙지 (이 스토리의 실패 원인)

**함정 #1 — 프롬프트만으로는 절대 안전하지 않다(결정론적 검증 필수).**
"SELECT만 만들어줘"라고 LLM에 시켜도 LLM은 DROP·다중문장·서브쿼리로 다른 테이블을 읽는 SQL을 만들 수 있다(환각·프롬프트 인젝션). **연구 §4.2 핵심 결론: LLM이 만든 SQL은 코드의 결정론적 검증(sqlparse)을 반드시 거쳐야 한다.** 가드를 "있으면 좋은 것"으로 두지 말 것 — 가드 미통과 SQL은 **절대 실행하지 않는다.** 이중 방어로 실행은 항상 `ai_readonly` 롤(4.1)로만 한다(가드가 뚫려도 쓰기는 DB가 거부).
[Source: research §4.2(130-145), §8 #4(283); architecture.md#AI 경로 안전장치(201)]

**함정 #2 — `ai_readonly`는 RLS로 sold를 못 거른다(FR11은 쿼리가 책임).**
4.1에서 확정: `ai_readonly`엔 `listings` 전 행을 보는 permissive 정책(`using(true)`)이 걸려 있어 **sold 매물도 보인다.** RLS는 FR11을 안 지켜준다 → **생성 SQL이 반드시 `status = 'on_sale'`을 포함**해야 하고, 가드가 그 존재를 검증한다(없으면 거부). 이는 Epic 3 회고 액션 #4("Text-to-SQL sql_guard에서도 sold 비노출")와 4.1 readonly.py 주석이 명시한 부채를 본 스토리가 갚는 지점이다.
[Source: 4-1 readonly.py 주석(10-12)·결정적 함정(84-99); conventions.md §6; epic-3-retro 액션4]

**함정 #3 — `status='on_sale'` 주입을 복잡 WHERE에 끼워넣지 말 것(OR 우회 위험).**
임의의 WHERE에 ` AND status='on_sale'`을 문자열로 끼워넣으면 `WHERE a OR b`에서 우선순위가 깨져 sold가 샐 수 있다. **결정론적으로 안전한 방법 = 주입이 아니라 검증+거부:** 가드는 `status = 'on_sale'`이 리터럴로 있으면 통과, 없으면 거부하고 노드가 1회 재생성을 요청한다. 프롬프트는 **OR 금지·AND로만 조건 결합·`status='on_sale'` 항상 포함**을 강제한다. (LIMIT은 끝에 append만 하면 안전하므로 없을 때 주입 허용.)
[Source: 본 설계 결정 — research §4.2 layer 4/5 해석]

**함정 #4 — 생성 모델명·단위 정규화는 실호출 1건으로 선검증(4.2 패턴).**
연구 §4.4·§8 #11은 "Gemini 모델명·수치 [미확인], 구현 전 재확인"이라 경고한다. 단일출처(`config.py`)는 `gemini-flash-latest`로 고정 — **4.2가 임베딩 모델을 실호출로 확정했듯**, 첫 SQL 생성 1건으로 모델 응답·단위 정규화("10만km"→100000)가 실제로 되는지 눈으로 확인 후 진행(안 되면 멈추고 보고).
[Source: research §4.4(160-164), §8 #11(290); 4-2 함정 #2 패턴]

### 설계 결정 — OI2: SQL Agent vs 제약 Chain (확정: **제약 Chain + 결정론적 가드**)

연구 §4.1·§8 #3은 SQL **Agent**(ReAct 반복·스키마 자동조회·자가수정)를 권장(신뢰도 **보통**)하나, **본 데모는 제약 Chain(단발 생성)을 택한다.** 근거:
- **단일 고정 테이블**(`listings`) — Agent의 강점인 스키마 탐색·다중테이블 조인이 불필요. 스키마는 프롬프트에 직접 박는다.
- **안전성** — Agent의 자율 반복은 결정론적 통제가 어렵다. 본 스토리의 핵심 AC는 **가드(결정론적 검증)** 이고, 실제 안전은 Agent가 아니라 가드가 만든다.
- **단순성·비용** — 초보 개발자·무료 등급 데모. 단발 생성 + 가드 + (오류 시) **최대 1회** 재주입이면 충분.
- Agent의 자가수정 효과는 "가드 거부/실행오류 → LLM 재주입 1회"로 **축소 재현**한다(연구 §4.3 다단계 재시도의 경량판, 무한루프 방지).

> 4.5 라우터도 동일 철학(구조화 출력 기반 분류, 연구 §8 #2). 4.3은 그 앞단 경로 A만 완성한다.

### sql_guard 설계 (`app/db/sql_guard.py`)

```python
"""결정론적 SQL 안전장치 — LLM이 만든 SELECT를 실행 전에 검증(연구 §4.2). 통과한 쿼리만 실행."""
import sqlparse
from sqlparse.tokens import DML, Keyword

DEFAULT_LIMIT = 50          # 연구 §4.3 "기본 LIMIT 주입"
MAX_LIMIT = 50              # 데모 상한(초과 생성 시 거부)
ALLOWED_TABLES = {"listings"}
ALLOWED_COLUMNS = {         # ListingCard 7필드 + 필터 컬럼 (0002 단일출처와 일치)
    "id", "manufacturer", "model", "year", "price", "mileage", "region",
    "body_type", "color", "fuel", "transmission", "displacement", "seats",
    "accident_free", "status", "options", "description",
}
_FORBIDDEN = {"INSERT","UPDATE","DELETE","DROP","ALTER","TRUNCATE","CREATE",
              "GRANT","REVOKE","COPY","MERGE","CALL","EXECUTE"}

class SqlGuardError(Exception):
    """가드 차단 — code(예: 'not_select','forbidden_table')와 한국어 message 보유."""
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)
```

**검증 순서(통과 못하면 즉시 `SqlGuardError`):**
1. **단일 문장:** `sqlparse.parse(sql)`로 statement 1개만(여분 `;`·다중문장 거부). 주석(`--`, `/* */`) 포함 시 거부.
2. **SELECT 전용:** 첫 유효 토큰의 ttype이 `DML`이고 값이 `SELECT`. 토큰 어디에도 `_FORBIDDEN` 키워드 없음(서브쿼리 위장 DDL 방지).
3. **테이블/컬럼 화이트리스트:** 식별자 추출 → `listings` 외 테이블 참조 거부. `SELECT *` 거부(명시 컬럼만). 등장 컬럼이 `ALLOWED_COLUMNS` 부분집합인지 확인(환각 컬럼 차단).
4. **FR11:** 정규화 텍스트에 `status = 'on_sale'`(공백·따옴표 변형 허용한 정규식 매칭) 존재. 없으면 `SqlGuardError("missing_status_filter", ...)`.
5. **LIMIT:** `LIMIT n` 있으면 `n <= MAX_LIMIT` 확인(초과 거부). 없으면 끝에 ` LIMIT {DEFAULT_LIMIT}` append(append는 결정론적 안전).
6. 통과 시 정규화된 SQL 문자열 반환.

- **구현 팁:** sqlparse는 검증·토큰화용이지 보안 경계가 아니다 — 실행은 항상 `ai_readonly`(4.1)로(이중 방어). 화이트리스트 비교는 소문자 정규화. 정규식 보조(예: `re.search(r"status\s*=\s*'on_sale'", sql_lower)`)는 sqlparse 토큰 검사와 **병행**(둘 중 하나라도 의심스러우면 거부).
- **거부는 안전한 기본값:** 애매하면 통과시키지 말고 거부(fail-closed).

### sql_rag_node 설계 (`app/graph/sql_rag_node.py`)

```python
"""경로 A — Text-to-SQL 노드. 질의→SELECT 생성→sql_guard 검증→ai_readonly 실행→ListingCard."""
from langchain_google_genai import ChatGoogleGenerativeAI
from app.config import settings, require
from app.db.readonly import run_select
from app.db.sql_guard import validate_select_sql, SqlGuardError
from app.schemas.ai import ListingCard

# state는 4.5에서 StateGraph로 확장될 최소 형태(dict). 지금은 함수 호출로 충분.
def sql_rag_node(query: str) -> dict:   # returns {"answer": str, "listings": list[ListingCard]}
    ...
```

- **LLM 호출:** `ChatGoogleGenerativeAI(model=settings.gemini_generation_model, google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key), temperature=0)`. temperature=0으로 재현성↑.
- **SELECT 컬럼 고정:** 프롬프트가 `SELECT id, manufacturer, model, year, price, mileage, region FROM listings WHERE ...` 형태로만 생성하게 유도(ListingCard 7필드). WHERE 조건은 질의에서. → 매핑이 단순해지고 가드 컬럼 검사도 쉬움.
- **재시도:** 가드/실행 실패 시 오류 문자열을 사용자 메시지에 덧붙여 1회 재생성. 2회째도 실패면 `SqlGuardError`를 라우터가 잡아 사용자 에러로.
- **결과 매핑:** `run_select`가 튜플을 주므로 컬럼 순서를 고정(SELECT 순서와 동일)해 `ListingCard(id=..., ...)`. `price`/`mileage`/`year`는 int 캐스팅.
- **answer 템플릿:** N>0 → `"조건에 맞는 매물 {N}건을 찾았어요."`, N==0 → `"조건에 맞는 매물이 없어요. 가격대나 차종 조건을 넓혀보세요."`(FR17 조건 완화 안내). **LLM 추가 호출 불필요**(answer_node 정교화는 4.5).

### 프롬프트 설계 (시스템 프롬프트에 반드시 포함)

1. **역할:** "너는 중고차 매물 DB를 검색하는 SQL 생성기다. PostgreSQL `listings` 테이블만 조회한다."
2. **스키마+허용값:** 컬럼명과 CHECK 허용값을 그대로 제시(아래 단일출처). 예: `body_type` ∈ {경차,소형차,준중형차,중형차,대형차,스포츠카,SUV,RV,경승합차,승합차,화물차,기타}; `color` ∈ {흰색,검정,회색,은색,파랑,빨강,갈색,녹색,기타}; `fuel` ∈ {가솔린,디젤,하이브리드,전기,LPG}; `transmission` ∈ {자동,수동}; `region` ∈ {서울,…,제주}.
3. **불변 규칙(MUST):** ①`SELECT id, manufacturer, model, year, price, mileage, region FROM listings`로 시작 ②`WHERE status = 'on_sale'` 항상 포함 ③조건은 **AND로만** 결합(OR 금지) ④`LIMIT 50` 이하 ⑤SQL 한 문장만 출력(설명·코드펜스·세미콜론 여분 금지).
4. **단위 정규화(conventions §3):** "만km"→×10000(예: 10만km→`mileage <= 100000`), "천만원/만원"→원 정수(예: 3천만원→`price <= 30000000`). 방향: "이하/미만"→`<=`/`<`, "이상/초과"→`>=`/`>`.
5. **차형 용어 매핑(OI5):** "세단"→`body_type IN ('준중형차','중형차','대형차')`, "해치백/쿠페" 등 데모에 없는 형태는 무리하게 매핑 말고 가격·기타 조건만 적용. "패밀리카/무난한" 같은 **의미형은 경로 B(4.4) 소관**이나, 4.3엔 라우터가 없으므로 들어오면 합리적 구조 조건으로 best-effort 변환(완벽 불필요).
6. **출력:** SQL 텍스트만. (langchain `.invoke()` 결과의 코드펜스/공백은 노드에서 strip.)

### 이전 스토리 학습 (적용할 패턴)

- **이중 방어·실행은 항상 ai_readonly(4.1):** 가드(앱) + 읽기전용 롤(DB). `run_select`(readonly.py)를 그대로 재사용 — 새 DB 헬퍼 만들지 말 것.
- **FR11 호출부 책임(4.1 함정·conventions §6):** `status='on_sale'`은 RLS가 아닌 생성 SQL이 강제. 가드가 검증.
- **단일출처·drift 금지(2-1·3-3·4-2):** 컬럼명·CHECK 허용값·단위는 `0002_listings.sql`·`docs/conventions.md`가 단일출처. 프롬프트·화이트리스트·테스트가 같은 값을 써야 함(시드·UI 드롭다운과도 일치).
- **fail-loud(1.4·4.1):** GEMINI_API_KEY/DATABASE_URL 부재 시 `require()`로 명확한 한국어 에러. 조용한 빈 결과 금지.
- **실DB·실LLM 검증(4.2):** mock 금지. 가드는 순수 단위테스트, 생성·실행은 라이브 1건 이상 눈으로 확인. 키 없으면 escalate(거짓 통과 금지).
- **4.2가 채운 데이터:** listings 44건(embedding·on_sale 42건). 4.3은 **임베딩을 쓰지 않는다**(경로 A는 구조 필터·정확 조건). 임베딩 유사도 검색은 4.4.

### 라이브러리·환경

- 추가: `sqlparse`(가드). 기존 ai 그룹: `langchain-google-genai`(ChatGoogleGenerativeAI), `psycopg`(readonly). [Source: api/pyproject.toml]
- 생성 모델: `settings.gemini_generation_model = "gemini-flash-latest"`(config.py 단일출처, 연구 §4.4 "Flash로 충분"). 첫 호출 1건으로 실제 응답 확인(함정 #4).
- 키: `GEMINI_API_KEY`·`DATABASE_URL`(Session pooler, :5432) — 4.2에서 `api/.env`에 입력됨(없으면 라이브 불가).

### 파일 구조 (생성/수정 대상)

```
api/app/graph/__init__.py            # 신규 — 패키지화
api/app/graph/sql_rag_node.py        # 신규 — 경로 A Text-to-SQL 노드
api/app/db/sql_guard.py              # 신규 — 결정론적 SELECT 검증(연구 §4.2)
api/app/routers/ai.py                # 수정 — stub 제거, sql_rag_node 호출
api/pyproject.toml                   # 수정 — ai 그룹에 sqlparse 추가
api/tests/test_sql_guard.py          # 신규 — 가드 단위 테스트(CM2)
```
- **만들지 않음(후속):** `graph/router_node.py`·`guard_node.py`·`answer_node.py`(4.5), `graph/doc_rag_node.py`(4.4), 전체 StateGraph 조립(4.5). [Source: architecture.md#Project Structure(382-391)]
- 기존 `schemas/ai.py`(SearchRequest/Response/ListingCard)·`db/readonly.py`(run_select)·`auth.py`는 **재사용**(변경 최소).

### 자체 테스트 방식 (CLAUDE.md §6)

- **백엔드 = HTTP/DB로 검증**(브라우저 아님). 화면 없음 → 단위(가드) + 라이브(생성·실행) 중심.
  - 가드: `pytest tests/test_sql_guard.py` — 네트워크 무관 순수 로직. **CM2(범위밖 차단) 핵심 증명**.
  - 생성·실행: 라이브 LLM 1건 + ai_readonly 실행으로 on_sale 필터·단위 정규화 확인(MCP `execute_sql`로 기대 결과 교차검증 가능).
  - HTTP: uvicorn `:8000` 백그라운드 → 미인증 401 유지 + 인증(오버라이드) `{answer,listings}` 형태. 끝나면 프로세스 정리.
- 회귀: 4.1·4.2 기존 pytest(12 passed)가 여전히 통과해야 함.

### 사용자 직접 처리 항목 (왜 / 어디서)

- **`api/.env`의 `GEMINI_API_KEY`** — SQL 생성 LLM 호출에 필수, 코드 밖 비밀값 / `api/.env`. (4.2에서 입력했으면 그대로 사용.)
- **`api/.env`의 `DATABASE_URL`(Session pooler)** — 생성 SQL을 ai_readonly로 실행하는 연결 / Supabase Connect → Session pooler(:5432). (4.1·4.2와 동일.)
- ⚠️ 둘 중 하나라도 없으면 **라이브 검증 불가** → 가드 단위테스트까지만 완료 보고하고 escalate. **거짓 "완료" 금지.**

### References

- [Source: epics.md#Story 4.3(463-482)] — 3개 AC 원문(노드·가드·차단·단위 정규화).
- [Source: epics.md#FR14(39), #NFR2(59), #AR7·AR8 OI2(75-76)] — 경로 A·안전장치 3종·OI2(Agent vs Chain) 결정 위임.
- [Source: architecture.md#AI 경로 안전장치(201), #Critical Decisions(120-123)] — 읽기전용 롤+LIMIT+SELECT 화이트리스트.
- [Source: architecture.md#listings 컬럼(147-189)] — 컬럼명·CHECK 허용값·차형 매핑(189) 단일출처.
- [Source: architecture.md#Format Patterns(268-271), #Project Structure(376-391)] — 응답 계약·sql_rag_node/sql_guard 위치.
- [Source: docs/conventions.md §3(단위)·§4(응답·ListingCard)·§6(FR11)] — 단위 정규화·계약·sold 비노출 강제 지점.
- [Source: research §4.1(120-128)·§4.2(130-145)·§4.3(149-158)·§4.4(160-164)·§8 #3·#4·#11] — Agent vs Chain, 다층 방어, 실패모드/재시도, 모델·미확인 경고.
- [Source: 4-1 readonly.py(run_select)·결정적 함정(84-99); 4-1 story Review #6(deferred → run_select 4.3에서 실사용)] — ai_readonly 재사용·FR11 호출부 책임.
- [Source: 4-2 story Dev Notes·함정 #2/#4] — 실호출 1건 선검증 패턴, embed_query는 4.4 소관(4.3 미사용).
- [Source: epic-3-retro 액션 #4] — Text-to-SQL sql_guard에서도 sold 비노출.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (dev-story 워크플로우). 생성 LLM: `gemini-flash-latest`(Gemini API).

### Debug Log References

- 가드 단위 테스트: `pytest tests/test_sql_guard.py` → 20 passed.
- 라이브 생성 로그(`sql_rag_node attempt 1 생성 SQL: ...`)로 실제 생성 SQL 눈 확인.
- 전체 회귀: `pytest` → 33 passed (4.1·4.2 기존 + 4.3 신규).

### Completion Notes List

- **OI2 결정(제약 Chain + 결정론적 가드)**: 단일 고정 테이블(listings)이라 SQL Agent의 스키마 탐색·자가수정이 불필요. 안전은 Agent가 아니라 `sql_guard`(결정론적 검증)가 만든다. 자가수정은 "가드/실행 오류 → LLM 1회 재주입"으로 경량 재현(무한루프 방지).
- **가드(`sql_guard.py`)**: sqlparse(문장 구조)와 정규식(테이블·컬럼·필터)을 병행, 의심 시 거부(fail-closed). 단일문장·SELECT전용·DML/DDL금지·주석금지·테이블/컬럼 화이트리스트·`SELECT *`금지·`status='on_sale'`필수·LIMIT 검사/주입. 20개 단위테스트로 CM2(범위밖·위험 쿼리 실행 전 차단) 증명.
- **생성 SQL 예시(라이브)**:
  - "3천만원 이하 흰색 SUV" → `SELECT id, manufacturer, model, year, price, mileage, region FROM listings WHERE status = 'on_sale' AND price <= 30000000 AND color = '흰색' AND body_type = 'SUV' LIMIT 50` → 2건.
  - "주행거리 10만km 이하 디젤차" → `... WHERE status = 'on_sale' AND mileage <= 100000 AND fuel = '디젤' LIMIT 50` → 11건.
- **단위 정규화(AC4) 확인**: "3천만원"→`price<=30000000`, "10만km"→`mileage<=100000`. 둘 다 생성 SQL에서 직접 확인.
- **FR11 실증(MCP 교차검증)**: 흰색 SUV 3천만↓이 전체 상태 기준 3건이나 `status='on_sale'` 강제로 sold 1건 제외 → 노드는 2건만 반환. 가드의 on_sale 검증이 실제로 sold를 걸러냄을 데이터로 확인.
- **가드 거부 사례**: DELETE/UPDATE/INSERT/DROP/ALTER/TRUNCATE → `not_select`/`forbidden_keyword`, 스태킹(`;`) → `multiple_statements`, 주석 → `comment_not_allowed`, `profiles` → `forbidden_table`, 환각 컬럼 → `forbidden_column`, `SELECT *` → `select_star`, on_sale 누락 → `missing_status_filter`, LIMIT 초과 → `limit_exceeded`. 사용자에겐 공통 에러 포맷 400(서버 500 누출 없음).
- **구현 중 발견·수정한 버그(라이브 검증의 성과)**: `gemini-flash-latest`는 `.content`를 문자열이 아니라 콘텐츠 블록 리스트(`[{"type":"text","text":"SELECT ..."}]`)로 반환 → 통째로 문자열화하면 가드가 `not_select`로 차단. `_content_to_text()`로 text 블록만 추출하도록 수정하고 회귀 테스트(`test_sql_rag_node.py`) 추가.
- **이중 방어 유지**: 실행은 항상 `ai_readonly` 롤(`run_select`, 4.1 재사용). 가드를 통과해도 쓰기는 DB가 거부.

### File List

- `api/pyproject.toml` — 수정: ai 그룹에 `sqlparse` 추가.
- `api/app/db/sql_guard.py` — 신규: 결정론적 SELECT 검증 + `SqlGuardError`.
- `api/app/graph/__init__.py` — 신규: graph 패키지화.
- `api/app/graph/sql_rag_node.py` — 신규: 경로 A Text-to-SQL 노드(생성→가드→실행→ListingCard, 1회 재시도).
- `api/app/routers/ai.py` — 수정: stub 제거, `sql_rag_node` 실연결 + 가드 차단 400 변환.
- `api/tests/test_sql_guard.py` — 신규: 가드 단위 테스트 20케이스(CM2).
- `api/tests/test_sql_rag_node.py` — 신규: 노드 순수 로직(콘텐츠 파싱·카드 매핑) 회귀 테스트 7케이스.
- `api/tests/test_auth.py` — 수정: 실연결에 맞춰 인증/계약 테스트를 노드 monkeypatch로 갱신 + 가드 차단 400 테스트 추가.

### Review Findings

(code-review 2026-06-21 — Blind Hunter · Edge Case Hunter · Acceptance Auditor 3종 병렬 적대적 리뷰)

**Patch (수정 필요):**

- [x] [Review][Patch] **OR로 `status='on_sale'` 무력화 → sold 매물 누출 (FR11 위반, Critical)** [api/app/db/sql_guard.py:122] — 가드는 `status = 'on_sale'` 문자열 *존재*만 확인하고 AND 결합을 강제하지 않음. `... WHERE status = 'on_sale' OR price < 99999999` 가 통과돼 sold 포함 전체 반환. ai_readonly RLS는 `using(true)`라 sold를 못 거름(readonly.py 명시) → 쿼리 필터가 유일한 방어선. 프롬프트 규칙3·코드 주석(L121 "OR 우회 위험 회피")이 이미 OR 금지를 의도하나 가드 미구현. 수정: 가드에서 OR(문자열 리터럴 밖) 거부.
- [x] [Review][Patch] **서브쿼리 LIMIT이 정규식에 먼저 잡혀 외부 쿼리 상한 우회 (High)** [api/app/db/sql_guard.py:129] — `re.search(r"\blimit\s+(\d+)")`가 첫 LIMIT(서브쿼리 내부)을 잡아 외부 쿼리에 LIMIT 미주입 → 전체 행 반환(MAX_LIMIT 50 우회). 수정: 중첩 SELECT(서브쿼리) 거부(단일테이블 데모엔 불필요) 또는 최상위 LIMIT만 인식.
- [x] [Review][Patch] **forbidden_keyword·comment 검사가 문자열 리터럴 제거 전 원본에 실행 → 정상 쿼리 오탐 차단 (Medium)** [api/app/db/sql_guard.py:72,90] — `model = 'DROP···'`·description 내 영문(UPDATE 등) 리터럴이 정상이어도 `forbidden_keyword`/`comment_not_allowed`로 차단(fail-closed 오탐). 컬럼 검사(L109)만 문자열 제거 선행. 수정: 키워드·주석 검사도 `no_strings`(리터럴 제거본)에 실행하도록 순서 조정.
- [x] [Review][Patch] **PsycopgError에도 LLM 재시도 + 원본 DB 오류를 프롬프트에 재주입 (Low)** [api/app/graph/sql_rag_node.py:149] — DB 일시장애를 LLM 재생성으로 못 고치는데 유료 LLM 호출 1회 낭비 + `str(exc)`(DB 내부정보)를 모델 컨텍스트에 주입. 수정: 재시도 대상을 `SqlGuardError`로 한정, DB 오류는 즉시 상위 전달.
- [x] [Review][Patch] **LIMIT 기본값/상한 미분리로 brief "약 5개" 정합 깨짐 (사용자 확인 후 추가)** [api/app/db/sql_guard.py:20-21, sql_rag_node.py:46] — product-brief 성공기준 "약 5개 정확히 추천"이 PRD/아키텍처로 내려오며 증발, 연구 §4.3 안전상한 `50`이 `DEFAULT_LIMIT`·`MAX_LIMIT` 양쪽에 복사됨. 프롬프트도 "LIMIT 50 이하"라 느슨한 질의가 최대 50개 반환. 수정: 두 개념 분리 — `DEFAULT_LIMIT=5`(추천 기본·brief 정합) / `MAX_LIMIT=50`(과도조회 안전상한 유지) + 프롬프트 규칙 ④를 기본 `LIMIT 5`로.

**Defer (이번 변경 밖·후속):**

- [x] [Review][Defer] **AC4 단위 정규화·차형(세단) 매핑이 결정론적 단위테스트 없음** [api/tests/] — deferred, LLM 프롬프트+라이브 1회에만 의존. LLM 출력 모킹/회귀 테스트 추가는 별도 작업.
- [x] [Review][Defer] **FR17 0건 안내·IN-매핑 가드 통과 경로 단위테스트 미커버** [api/tests/test_auth.py] — deferred, 노드 monkeypatch로 우회돼 실 경로 미검증.
- [x] [Review][Defer] **LIMIT 비정수형(0/음수/`(10)`/OFFSET-only) → 잘못된 SQL 또는 오해성 0건** [api/app/db/sql_guard.py:129] — deferred, temp=0 프롬프트에서 발생 가능성 낮고 대부분 fail-safe(오류→재시도).

## Change Log

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-06-21 | Story 4.3 컨텍스트 작성 — 경로 A Text-to-SQL + sql_guard. OI2=제약 Chain+결정론적 가드 확정 | Status → ready-for-dev |
| 2026-06-21 | 경로 A 구현 — sql_guard(20 테스트)·sql_rag_node·/ai/search 실연결. 라이브 생성·실행·단위정규화·FR11(sold 제외) 검증. content 블록 파싱 버그 수정. 33 tests passed | Status → review |
| 2026-06-21 | code-review 통과 — patch 5건 반영(OR우회 차단·서브쿼리 차단·리터럴 키워드 오탐 수정·PsycopgError 재시도 제거·LIMIT 5/50 분리[brief "약5개" 정합]) + 가드 테스트 보강. 43 tests passed | Status → done |
| 2026-06-22 | code-review 후속: sql_guard 음수 LIMIT·OFFSET 상한 보강(사용자 결정) — `LIMIT -1`/`LIMIT 0` 거부, OFFSET MAX_OFFSET(1000) 상한·음수 거부. 경계 테스트 6건 추가. 141 passed/3 skipped | — |
