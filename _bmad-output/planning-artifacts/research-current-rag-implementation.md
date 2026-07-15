# 현재 AI 검색(RAG) 구현 상태 조사 — 코드 기반 사실 기록

조사일: 2026-07-11 | 조사 범위: `api/app/graph/**`, `api/app/db/**`, `api/app/**`, `api/tests/**`,
`api/scripts/backfill_embeddings.py`, `_bmad-output/implementation-artifacts/4-*.md`,
`docs/learning/03-langgraph-ai.md`, `supabase/migrations/0004_guide_documents.sql`

추측 없이 코드를 직접 읽고 확인한 사실만 담는다. `file:line` 표기는 저장소 루트
(`C:\Users\dnjsg\workspace\bmad-encar-demo`) 기준 상대경로다.

---

## 1. 파일·노드 지도

```
api/app/graph/
  graph.py             — StateGraph 조립 + run_search() 진입점
  contextualize_node.py — 그래프 진입 "전"에 호출되는 멀티턴 맥락화(FR18)
  router_node.py        — 그래프 진입 노드. A/B/C 3분류
  sql_rag_node.py        — 경로 A: Text-to-SQL
  doc_rag_node.py        — 경로 B: 임베딩 유사도 검색(매물 + 가이드문서)
  guard_node.py          — 경로 C: 고정 거절 문구(LLM 미호출)
  answer_node.py         — 공통 계약 {answer, listings[]} 정규화 + FR17 0건 안내
  listing_cards.py       — SELECT 컬럼·행→ListingCard 매핑 공유 헬퍼(경로 A·B 공용)

api/app/db/
  sql_guard.py  — 결정론적 SELECT 검증(화이트리스트·OR 금지·서브쿼리 금지·LIMIT/OFFSET 상한)
  readonly.py   — ai_readonly 롤로 SET ROLE 후 SELECT만 실행

api/app/embeddings.py   — Gemini 768차원 임베딩(L2 정규화), RETRIEVAL_DOCUMENT/RETRIEVAL_QUERY
api/app/routers/ai.py   — POST /ai/search — 인증 → run_search() → 에러 매핑
api/app/schemas/ai.py   — RouterDecision(Literal A/B/C), SearchRequest/Response, ConversationTurn
api/app/auth.py         — Supabase JWT 검증(get_current_user)
api/app/config.py       — .env 로드, require() fail-loud 헬퍼

api/scripts/backfill_embeddings.py — listings.embedding + guide_documents 일괄 적재(오프라인 스크립트, 런타임 아님)
api/corpus/*.md (10개) — 가이드 문서 원문. _excluded/ 2개(할부·보험/세금)는 로더가 비재귀라 자동 제외
supabase/migrations/0004_guide_documents.sql — guide_documents 테이블 + HNSW 인덱스 + RLS
```

파이프라인 요약(`api/app/graph/graph.py:1-131`, `docs/learning/03-langgraph-ai.md:19-41`):

```
POST /ai/search
  → contextualize_query(query, context)   [그래프 진입 "전", graph.py:124]
  → COMPILED_GRAPH.invoke({query})
      router(A/B/C 분류)
        A → sql_rag_node   → answer_node → END
        B → doc_rag_node   → answer_node → END
        C → guard_node     → answer_node → END
```

---

## 2. 분기별 현황

### 라우팅 분기 — A/B/C 3갈래 확인 (질문 1)

`api/app/graph/router_node.py:83-105`. 갈래는 정확히 3개, 코드가 명시:
- A = 구조형(가격·차종·연식·색상·지역·주행거리·연료·옵션명 등 명시 조건) → 경로 A
- B = 질적·의미형(용도·느낌만, 명시 조건 없음) → 경로 B
- C = 매물 무관(잡담·상식·금융/세금/보험 일반지식 포함) → 가드(거절)

판정 방식: LLM(Gemini) 단일 호출 + Pydantic `Literal["A","B","C"]` 구조화 출력
(`with_structured_output(RouterDecision)`, `router_node.py:90`, 스키마는
`api/app/schemas/ai.py:16-27`). temperature=0(재현성, `router_node.py:67`).
구조화 출력 파싱 실패·형식이탈 시 `_fallback_route()`로 결정론적 보정
(매물 신호 단어 있으면 B, 없으면 C — `router_node.py:71-80`). `GEMINI_API_KEY` 부재는
보정 대상이 아니라 `require()`로 즉시 실패(fail-loud, `router_node.py:89`).

라우터 판정 자체는 **LLM 프롬프트 기반**이며 규칙엔진이 아니다. 다만 그래프 분기 자체는
`_route_decision()`(`graph.py:74-84`)이 A/B/C만 통과시키고 그 외 값은 강제로 C(guard)로 보내는
결정론적 안전망을 갖는다.

### 경로 A — Text-to-SQL (질문 2)

`api/app/graph/sql_rag_node.py`. 흐름:
1. Gemini LLM에게 스키마·허용값·불변 규칙이 담긴 시스템 프롬프트 + 사용자 질의를 주고
   SQL 텍스트 한 줄 생성(`sql_rag_node.py:34-74`).
2. `validate_select_sql()`(`api/app/db/sql_guard.py:67-195`)로 검증 — 단일 문장·주석 금지·
   SELECT 전용·DML/DDL 키워드 금지·**OR 금지**(status='on_sale' 무력화 방지)·서브쿼리 금지·
   `SELECT *` 금지·테이블 화이트리스트(`listings`만)·컬럼 화이트리스트·`status='on_sale'` 필수·
   OFFSET 상한(1000)·LIMIT 상한(50, 기본 5) 검사. 실패하면 `SqlGuardError`.
3. 통과한 SQL만 `run_select()`(`api/app/db/readonly.py:38-43`)로 실행. 이 함수는 연결 직후
   `SET ROLE ai_readonly`(`readonly.py:20,32`)를 걸어, 가드가 뚫려도 DB 권한상 쓰기가 불가능한
   이중 방어 구조.
4. 가드 차단 시 오류 메시지를 LLM에 1회 재주입해 재생성(`sql_rag_node.py:136-159`). 2회째도
   막히면 `SqlGuardError`를 상위로 전파(그래프 밖 `/ai/search`가 400으로 처리,
   `api/app/routers/ai.py:34-40`). DB 오류(psycopg 예외)는 재시도 없이 그대로 전파(500).

### 경로 B — 문서 RAG (질문 3, 사용자 가설 검증)

`api/app/graph/doc_rag_node.py:42-81`. **가설과 달리, 매물 임베딩만 쓰는 게 아니라
`guide_documents` 테이블도 실제로 조회한다.** 다만 그 쓰임이 제한적이다:

- 질의를 `embed_query()`(768차원, RETRIEVAL_QUERY 타입)로 벡터화(`doc_rag_node.py:48`).
- **매물 검색(주 결과)**: `listings` 테이블에서 `status='on_sale' AND embedding IS NOT NULL`
  조건으로 코사인 거리(`<=>`) 오름차순 정렬해 5건 조회(`doc_rag_node.py:55-61`). 이게
  사용자에게 보여지는 `listings[]` 카드의 원천이다.
- **가이드 문서(부가 근거, 단 1건만)**: `guide_documents` 테이블에서 같은 질의벡터로 가장
  가까운 문서 **제목 1개만** 조회(`doc_rag_node.py:64-69`). 이 제목이 answer 문자열 끝에
  `"(참고: {guide_title})"` 형태로 덧붙는다(`doc_rag_node.py:78-80`). **문서 본문(content)은
  응답에 전혀 쓰이지 않는다** — SELECT 자체가 `title`만 가져온다(`doc_rag_node.py:65`).

즉 가이드 문서 코퍼스는 "만들어놓고 완전히 안 쓰는" 상태는 아니지만, RAG의 핵심인
"문서 내용을 근거로 답을 생성"하는 용도로는 쓰이지 않고, 매물 추천에 **제목 한 줄을
장식적으로 덧붙이는 정도**로만 쓰인다. 문서 content가 LLM 프롬프트에 주입돼 답변 생성에
반영되는 경로는 코드 어디에도 없다.

경로 B는 LLM이 SQL을 만들지 않는다 — 코드가 고정 SQL 문자열 + 파라미터 바인딩만 쓰므로
`sql_guard`를 거치지 않는다(주석상 명시: `doc_rag_node.py:5-8`). `status='on_sale'` 필터링은
전적으로 이 코드가 직접 책임진다(ai_readonly RLS가 `using(true)`라 sold를 못 거름).

### 하이브리드(SQL+임베딩 조합) 분기 (질문 4)

**존재하지 않는다.** `graph.py`의 `_route_decision()`은 A/B/C 세 갈래 중 정확히 하나로만
분기하며(`graph.py:74-107`), 두 경로를 조합해서 실행하는 노드나 조건은 없다. 저장소 전체를
"하이브리드/hybrid" 키워드로 검색해도 SQL 검색과 벡터 검색을 조합하는 설계·코드는 없고,
매칭되는 것은 전부 연료 타입 값 `"하이브리드"`(hybrid 자동차)뿐이다. `architecture.md`에도
하이브리드 검색 설계 언급 없음.

### 되묻기/조건 좁히기(clarification) (질문 5)

**전용 로직 없음.** "명확화 질문을 먼저 던지고 사용자 답을 받은 뒤 재검색"하는 흐름은
코드 어디에도 없다. 존재하는 것은 두 가지뿐이며 둘 다 clarification이 아니다:
- FR17 0건 안내: 결과가 0건이면 "조건을 넓혀보세요/용도를 알려주시면 다시 찾아드릴게요" 같은
  **문구만** 답변에 붙는다(`answer_node.py:21-26`, `doc_rag_node.py:29`,
  `sql_rag_node.py:77`). 이건 답변 텍스트일 뿐, 그래프가 되물음 상태로 멈추거나 사용자
  응답을 기다리는 게 아니다 — 한 번의 요청-응답으로 끝난다(그래프에 루프/대기 노드 없음).
- 멀티턴 맥락화(`contextualize_node.py`, FR18): 사용자가 스스로 후속 질문을 던졌을 때
  이전 대화를 반영해 질의를 재작성하는 기능이며, AI가 먼저 되묻는 기능이 아니다.

### LangGraph 상태 그래프 구조

`StateGraph(SearchState)` — 노드 5개(router/sql/doc/guard/answer), `set_entry_point("router")`,
`add_conditional_edges`로 A/B/C 분기, 세 경로 모두 answer로 수렴 후 `END`
(`graph.py:87-108`). 모듈 import 시 1회만 `compile()`해 `COMPILED_GRAPH` 전역에 캐시
(`graph.py:112`) — 요청마다 재컴파일하지 않음. 체크포인터(checkpointer)·메모리 저장소는
사용하지 않음(무상태 설계, FR18 주석에 명시: `contextualize_node.py:8-10`).

---

## 3. LangChain / LangGraph / LangSmith 사용 현황 (질문 6)

의존성 선언 (`api/pyproject.toml:12-25`, `api/requirements.txt`):
```
langgraph==1.2.4
langchain-google-genai   (버전 미고정 — 설치본은 4.2.5)
pgvector
sqlparse
```
설치본 확인(`api/.venv/Lib/site-packages`):
- `langgraph 1.2.4`, `langgraph-cli 0.4.28`, `langgraph_checkpoint 4.1.1`,
  `langgraph_prebuilt 1.1.0`, `langgraph_sdk 0.4.2`
- `langchain_core 1.4.8`, `langchain_google_genai 4.2.5`, `langchain_protocol 0.0.18`
- **`langsmith 0.8.18`도 설치돼 있음** — 그러나 이건 `langchain-core`/`langgraph`의 **전이
  의존성**일 뿐이다. 저장소 전체를 `langsmith|LANGCHAIN_TRACING|LANGSMITH` 키워드로 검색한
  결과 **일치하는 파일 0건** — `import langsmith`, `LANGCHAIN_TRACING_V2`,
  `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` 등 트레이싱 관련 코드·환경변수가 코드베이스
  어디에도 없다. `.env.example`(`api/.env.example`)에도 LangSmith 관련 키가 없다.
  → **LangSmith는 설치만 돼 있을 뿐 실제로 연동·사용되지 않는다.**

실제 import되는 것:
- `from langgraph.graph import END, StateGraph` (`graph.py:24`) — StateGraph 조립에만 사용.
- `from langchain_google_genai import ChatGoogleGenerativeAI` — 라우터
  (`router_node.py:19`)·맥락화(`contextualize_node.py:23`)·SQL 생성(`sql_rag_node.py:15`)
  3곳에서 LLM 클라이언트로 사용.
- `from langchain_google_genai import GoogleGenerativeAIEmbeddings` (`embeddings.py:14`) —
  임베딩 클라이언트.
- LangChain의 다른 구성요소(체인 `Runnable`, `PromptTemplate`, 메모리, 에이전트, 툴콜링,
  리트리버 추상화 등)는 사용하지 않는다. `ChatGoogleGenerativeAI.with_structured_output()`과
  `.invoke()`만 직접 호출하는 얇은 사용 패턴.

---

## 4. 가이드 문서 코퍼스 실사용 여부 (질문 7)

**원문 위치**: `api/corpus/*.md` — 10개 활성 문서(예: `01-차종별-특성.md`,
`02-패밀리카-적합-차종.md`, `05-중고차-신뢰성-체크포인트.md` 등) + `_excluded/`에 2개
(`08-할부-리스-현금-비교.md`, `09-보험-세금-기초.md`, party-mode 결정으로 코퍼스에서 의도적
제외 — `api/corpus/_excluded/README.md:9-18`. 이유: "매물 추천 근거가 아닌 일반지식이라
라우터가 C로 보내야 하는데, 코퍼스에 남기면 B로 잘못 채택될 위험").

**적재 위치·방식**: `guide_documents` 테이블(`supabase/migrations/0004_guide_documents.sql:19-25`,
컬럼: id/title/content/embedding vector(768)/created_at). 적재는 오프라인 스크립트
`api/scripts/backfill_embeddings.py`가 담당(`load_corpus()` — `.md` 파일을 첫 줄 `# 제목` 기준
title/content로 분리, `backfill_guides()` — 제목+본문을 함께 임베딩해 `content`는 본문만 저장,
전량 delete 후 재삽입하는 멱등 방식, `backfill_embeddings.py:102-146`). **청킹(chunking)은
없다** — 문서 하나 전체가 통째로 한 임베딩 벡터 하나에 대응된다(문서 내 섹션별 분할 없음).

**실제 조회(런타임)**: 경로 B(`doc_rag_node.py:64-69`)에서만 조회하며, 앞서 §2에서 밝힌 대로
**title만 SELECT**해 답변 문구에 "(참고: 제목)" 형태로 한 줄 첨부하는 용도로만 쓴다.
content(본문)를 읽어 LLM 프롬프트에 주입하거나 답변 생성 근거로 활용하는 코드는 없다.
경로 A(Text-to-SQL)는 `guide_documents`를 전혀 참조하지 않는다. 라우터(A/B/C 분류)도
`guide_documents`를 참조하지 않는다(분류는 순수 프롬프트 규칙).

**결론**: 사용자 가설("가이드 문서 만들었지만 실제론 매물 설명 임베딩만 씀")은 **정확히
맞지는 않다** — guide_documents 테이블은 실제로 쿼리된다. 하지만 실질적으로는 "제목 한 줄
장식"에 그쳐, RAG로서 문서 내용이 답변에 반영되는 수준의 활용은 아니다.

---

## 5. 사용자 6대 고도화 목표 대비 갭 표

| # | 목표 | 현재 상태 | 갭 |
|---|------|-----------|-----|
| 1 | 거절(guard) 로직 | 있음. 경로 C는 라우터가 잡담·상식·금융/세금/보험 일반지식을 분류하면 `guard_node.py`가 **고정 템플릿 문구**로 거절 + 검색 유도(`guard_node.py:23-27,30-36`). LLM 미호출, 결정론적. | 거절 문구가 완전 고정이라 질의 맥락 반영이 전혀 없음(모든 C 질의에 토씨 하나 안 다른 동일 답변). 페르소나·톤 다양화나 "왜 거절됐는지"에 대한 질의별 설명은 없음. |
| 2 | 조건 되묻기(clarification) | **없음.** 0건일 때 "조건을 넓혀보세요" 식 **안내 문구**만 있고(`answer_node.py:21-26`), AI가 먼저 되묻고 사용자 응답을 기다리는 대화 상태(멀티턴 루프)는 그래프에 없음. B 라우팅 시 "애매하면 C 대신 B로 보낸다"(`router_node.py:50`)는 규칙이 있으나 이것도 명시적 되묻기가 아니라 "빈손보다 추천"이라는 대체 전략일 뿐. | 명확화 질문 생성 노드, 대화 상태 유지(질문 대기), 사용자 답변을 반영해 재검색하는 루프가 전부 부재. LangGraph 체크포인터/interrupt 기능도 미사용이라 구조적으로 멀티턴 "대기" 자체가 불가능(무상태 설계). |
| 3 | SQL+벡터 하이브리드 검색 | **없음.** 라우터가 A(SQL) 또는 B(벡터) 중 하나로만 배타적 분기(`graph.py:98-102`). 두 결과를 병합·재순위화(rerank)하는 로직 없음. | 조건(SQL)과 의미(벡터)를 동시에 반영해야 하는 질의(예: "3천만원 이하 SUV 중 패밀리카로 무난한 거")는 라우터가 A 또는 B 하나로만 강제 분류되어, 못 잡은 쪽 신호가 유실됨. |
| 4 | 가이드 문서 참조 분기(경로 B 활성화) | **경로 B 자체는 존재**하지만, `guide_documents`는 title 1건만 장식적으로 인용(§4). 본문 content가 답변 생성에 근거로 쓰이는 진짜 "문서 참조 RAG"는 아님. | 문서 content를 LLM 컨텍스트에 주입해 "왜 이 매물을 추천하는지"를 문서 근거로 설명하는 생성 단계가 없음(현재는 코드가 고정 문자열 템플릿만 채움, `answer_node.py:6-12`의 "LLM 재작성 금지" 설계와 충돌 지점). |
| 5 | 문서 청킹(chunking) | **없음.** `backfill_embeddings.py`가 corpus 문서 1개 = 1행 = 1임베딩 벡터로 그대로 적재(`load_corpus()`/`backfill_guides()`, `backfill_embeddings.py:102-146`). 섹션·문단 단위 분할 없음. | 문서가 길면(멀티 섹션) 임베딩이 문서 전체 평균적 의미만 담아, 특정 섹션에 정확히 대응하는 질의의 검색 정밀도가 떨어질 수 있음. 청크 단위 저장·검색·근거 인용(문서 내 특정 구절 인용) 불가. |
| 6 | LangChain/LangGraph/LangSmith 적극 활용 | **얕은 사용.** LangGraph는 StateGraph 조립에만 사용(체크포인터·서브그래프·interrupt·streaming 미사용). LangChain은 `ChatGoogleGenerativeAI`/`GoogleGenerativeAIEmbeddings` 클라이언트 래퍼 + `with_structured_output()`만 사용(체인·프롬프트템플릿·리트리버 추상화·에이전트·툴콜링 미사용). **LangSmith는 설치만 되어 있고 트레이싱 연동 코드·환경변수가 전혀 없음**(§3). | 관측성(트레이싱/로그) 부재로 라우팅 오분류·SQL 생성 실패 등을 LangSmith 대시보드로 추적할 수 없음(현재는 `logging` 모듈의 텍스트 로그만 존재, 예: `router_node.py:104`). LangGraph의 상태 지속(persistence)·재시작 가능한 워크플로 기능도 미사용. |

---

## 요약 (반환용)

- **라우팅**: 정확히 A(Text-to-SQL)/B(문서·임베딩 RAG)/C(거절) 3분기. LLM 구조화 출력
  (`with_structured_output(Literal["A","B","C"])`, temperature=0) + 실패 시 키워드 기반
  결정론적 폴백. `router_node.py:83-105`.
- **경로 A**: Gemini가 SQL 생성 → `sql_guard.validate_select_sql()`(화이트리스트·OR/서브쿼리
  금지·on_sale 필수·LIMIT/OFFSET 상한) → `ai_readonly` 롤로만 실행(이중 방어). 가드 차단 시
  1회 재생성.
- **경로 B**: 코드가 고정 SQL(sql_guard 미경유)로 (1) `listings.embedding` 코사인 검색 5건
  (실제 카드), (2) `guide_documents.embedding` 코사인 검색 **title 1건만** 부가 인용. **가이드
  문서는 실제 쿼리되지만 title 장식용일 뿐, content가 답변 근거로 쓰이지 않는다** — 사용자
  가설과 부분적으로만 일치.
- **하이브리드 분기**: 없음. A/B/C는 배타적 단일 경로.
- **되묻기(clarification)**: 없음. 0건 시 텍스트 안내만 있을 뿐 대화 상태 대기·재질문 루프
  없음(무상태 설계, 체크포인터 미사용).
- **LangGraph/LangChain**: LangGraph는 StateGraph 조립에만(1.2.4), LangChain은 Gemini
  LLM/임베딩 클라이언트 래퍼로만 얕게 사용. **LangSmith는 전이 의존성으로 설치만 됐을 뿐
  트레이싱 연동 코드·환경변수가 전무**(코드베이스 전체 검색 0건).
- **문서 청킹**: 없음. corpus 문서 1개 = 1행 = 1벡터, 섹션 분할 없음.
- **최대 갭 3개**: (1) SQL+벡터 하이브리드 검색 부재(조건+의미 동시 질의를 못 받음),
  (2) 가이드 문서가 title만 장식적으로 쓰이고 content가 답변 생성에 미반영(진짜 문서 RAG
  아님), (3) LangSmith 트레이싱 미연동으로 라우팅/생성 실패에 대한 관측성이 텍스트 로그 수준에
  그침.

전체 문서: `C:\Users\dnjsg\workspace\bmad-encar-demo\_bmad-output\planning-artifacts\research-current-rag-implementation.md`
