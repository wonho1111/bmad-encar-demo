# Story 4.4: 경로 B — 문서 기반 RAG (FR15)

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 구매자,
I want "패밀리카로 무난한 거" 같은 의미형/질적 질문에도 적합한 매물을 추천받고 싶다,
so that 정확한 조건(가격·차종)을 몰라도 의도만 말하면 어울리는 차를 추천받는다.

> **이 스토리의 본질:** 4.3이 "구조형 질의 → 정확한 SQL 필터"(경로 A)였다면, **4.4는 "의미형 질의 → 임베딩 유사도 검색"(경로 B)** 이다. 핵심은 **글의 의미가 비슷한 것끼리 찾기** — 사용자 질문을 4.2에서 만든 것과 같은 768차원 벡터로 바꾼 뒤, DB에 미리 적재된 ①매물 설명·옵션 임베딩과 ②가이드 문서 임베딩을 pgvector 코사인 유사도(`<=>`)로 검색해 **의미가 가까운 on_sale 매물**을 추천하고, **가이드 문서를 근거(왜 어울리는지)** 로 곁들인다. 4.2가 데이터(임베딩)를 채웠고, 이제 4.4가 그 데이터를 **검색**한다 — `embed_query()`(4.2에서 정의만 해둔 함수)가 드디어 실제로 쓰인다.
>
> *RAG(Retrieval-Augmented Generation): 질문과 관련된 문서를 먼저 검색(Retrieval)해 그 내용을 근거로 답을 만드는 방식.*
> *임베딩 유사도 검색: 글을 숫자 벡터로 바꿔, 벡터 사이 거리가 가까운(=의미가 비슷한) 것을 찾는 검색.*
> *코사인 유사도(`<=>`): 두 벡터가 가리키는 방향이 얼마나 비슷한지로 의미 근접도를 재는 척도. 거리가 0에 가까울수록 비슷함.*

## Acceptance Criteria

1. **(AC1 — 문서 RAG 노드)** `app/graph/doc_rag_node.py`의 `doc_rag_node`가 존재하고, "패밀리카로 무난한 거"·"초보 운전자에게 좋은 차" 류 **의미형/질적 질의**가 오면 ① 질의를 `embed_query()`(4.2)로 768 임베딩하고 ② **매물 설명·옵션 텍스트 임베딩(`listings.embedding`)과 가이드 문서 임베딩(`guide_documents.embedding`)을 pgvector 코사인 유사도(`<=>`)로 검색**해 의미가 가까운 매물과 근거(적합 차종/특성) 가이드 문서를 얻는다. 반환은 공통 계약 `{answer, listings[]}`(`ListingCard` 목록). [FR15, FR17]
2. **(AC2 — on_sale만 추천, FR11)** 유사도 검색으로 추천되는 매물은 **`status = 'on_sale'` 매물뿐**이다. `ai_readonly` RLS는 sold를 못 거르므로(`using(true)`) **코드가 직접 `WHERE status = 'on_sale'`을 넣어** sold·NULL 임베딩 매물을 제외한다. [FR11]
3. **(AC3 — 0건 안내, FR17)** 유사 매물이 0건이면 `listings: []` + `answer`에 조건 완화/재질문 유도 안내를 담는다(빈 목록만 던지지 않음). 임베딩·DB 호출 실패 시 `require()` fail-loud 또는 상위(전역 500)로 전파하고, 조용한 빈 결과를 만들지 않는다.
4. **(AC4 — 결정론적 검증)** 임베딩 호출과 DB를 모킹한 **순수 단위 테스트**가 존재한다 — 벡터 리터럴 포맷·`ListingCard` 매핑·0건 FR17 분기·근거 가이드 선택을 네트워크 없이 검증한다. 추가로 실 임베딩·실 DB 라이브 검증 1건 이상으로 의미형 질의가 타당한 매물·가이드를 돌려주고 sold가 제외됨을 눈으로 확인한다.

### 범위 밖 (이 스토리에서 구현하지 않음 — 과잉구현 금지)

- ❌ **라우터 의도 분류(A/B/C)** → **4.5**. 4.4는 `doc_rag_node`를 **호출 가능한 노드 함수**로만 만든다. **`/ai/search`는 건드리지 않는다**(4.3에서 경로 A에 실연결돼 있고, A/B 라우팅 분기는 4.5가 sql_rag_node·doc_rag_node 앞에 라우터를 꽂으며 한다).
- ❌ **전체 LangGraph `StateGraph` 조립(router→nodes→answer 와이어링)** → **4.5**.
- ❌ **가드 노드(경로 C·무관 질의 거절)·`answer_node`(정교한 답변 조립)** → **4.5**. 4.4의 `answer`는 노드가 만드는 **간단한 한국어 근거 요약**(예: "'…'에 어울리는 매물 N건을 찾았어요. (참고: {가이드 제목})")이면 충분. LLM 추가 호출로 답변을 정교화하지 않는다(4.5 소관).
- ❌ **가이드 문서 → 구조 조건(body_type/seats) LLM 추출 후 SQL 재질의(Design 2)** → 아래 "설계 결정(OI-B)" 참조. 단일 테이블·데모 규모에선 과잉. 모호·광범위 질의의 **되묻기(clarify)** 도 4.5 라우터 소관(deferred-work 4-3 #4 메모).
- ❌ **하이브리드 검색(BM25+벡터·RRF)·재순위(reranking)** → 연구 §5.6/§8 #8 "MVP는 벡터 단독". 본 스토리는 벡터 단독.
- ❌ **멀티턴 맥락(`context`) 반영** → **4.6**. (4.4 노드는 단일 `query`만 받는다.)
- ❌ **AI 검색 화면(웹 UI)** → **4.7**. **0004 마이그레이션·코퍼스·임베딩 backfill** → 이미 4.2 done(재실행 불필요).

## Tasks / Subtasks

- [x] **Task 1 — 라이브 데이터·의존성 전제 확인(이미 충족됐는지 점검만)** (AC: 1, 2)
  - [x] 1.1 `pip install -e ".[ai,dev]"` 설치 상태 확인(4.2/4.3에서 설치됨 — 추가 의존성 **없음**; pytest·import 정상 동작으로 확인).
  - [x] 1.2 MCP `execute_sql`로 라이브 데이터 전제 확인: `guide_documents` 6/6 임베딩·dim 768, `listings` null 0(44/44)·`on_sale` 42·dim 768. (4.2 backfill 결과 그대로 — 새 backfill 안 함.)
  - [x] 1.3 MCP로 `ai_readonly` 가시성 재확인: `set role ai_readonly` 후 guide 6·listings 44(on_sale 42) 에러 없이 보임(0004 정책 적용 — 함정 #1 회피).

- [x] **Task 2 — `app/graph/doc_rag_node.py` 문서 RAG 노드** (AC: 1, 2, 3)
  - [x] 2.1 `doc_rag_node(query: str) -> dict` 작성. embed_query(4.2 재사용) → 벡터 리터럴 → 매물 유사도 검색(on_sale 한정) + 가이드 유사도 검색 → rows_to_cards 매핑 + 근거 answer 조립.
  - [x] 2.2 매물 검색 SQL: `SELECT {SELECT_COLUMNS} FROM listings WHERE status = 'on_sale' AND embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT %s`, (벡터, DEFAULT_LIMIT) 바인딩, `run_select`(ai_readonly) 실행. **FR11은 이 WHERE가 책임**(AC2). sql_guard 미경유(LLM 미사용).
  - [x] 2.3 가이드 검색 SQL: `SELECT title FROM guide_documents WHERE embedding IS NOT NULL ORDER BY embedding <=> %s::vector LIMIT 1`(근거용 상위 1건). (title만 — content는 4.4 answer에 불필요.)
  - [x] 2.4 벡터 바인딩: `_vec_literal()`로 `list[float]` → `"[v1,...]"` 후 `%s::vector` 캐스팅(register_vector 없이 동작). 벡터·LIMIT 모두 파라미터 바인딩(f-string 직접삽입 없음).
  - [x] 2.5 answer 조립: N>0 → `"'{query}'에 어울리는 매물 {N}건을 찾았어요."` + 근거 가이드 있으면 ` (참고: {제목})`. N==0 → `_ANSWER_EMPTY`(FR17). LLM 추가 호출 없음.

- [x] **Task 3 — ListingCard 매핑·SELECT 컬럼 공유(drift 방지)** (AC: 1)
  - [x] 3.1 `app/graph/listing_cards.py` 신규 — `SELECT_COLUMNS`·`rows_to_cards()`를 단일출처로 추출(경로 A·B 공유).
  - [x] 3.2 `sql_rag_node.py`를 공유 헬퍼 import로 최소 수정(`_SELECT_COLUMNS=SELECT_COLUMNS`, 로컬 `_to_cards` 제거→`rows_to_cards` 사용). 동작 불변. `test_sql_rag_node.py`는 매핑 테스트 import만 새 위치로 변경(같은 로직 검증). 회귀 0.
  - [x] 3.3 (대안 불필요 — 공유 헬퍼 추출이 회귀 없이 성공.)

- [x] **Task 4 — pytest 단위 테스트(모킹) + 라이브 검증** (AC: 4)
  - [x] 4.1 `tests/test_doc_rag_node.py`(네트워크 무관, 7케이스): 벡터 리터럴 포맷 / embed_query에 원문 전달 / 매물 SQL의 `status='on_sale'`·`<=>`·파라미터 바인딩 / 튜플→ListingCard 매핑 / 0건 FR17·listings=[] / 근거 가이드 제목 포함 / 가이드 0건이어도 매물 반환. → 7 passed.
  - [x] 4.2 라이브 검증: `doc_rag_node` 3건 — "패밀리카로 무난한 거"→캠리·K8·말리부·카니발·니로(+근거 "패밀리카로 무난한 차종 고르기"), "초보 운전자에게 좋은 작은 차"→스파크·모닝·티볼리(+"초보 운전자에게 적합한 차종"), "연비 좋은 전기차"→EV6·니로EV·모델S·모델3·아이오닉5(전부 전기차, +"연료별 유지비와 연비 특성"). 의미검색 타당성 눈 확인.
  - [x] 4.3 FR11 라이브 교차검증: "정숙하고 안락한 대형 세단" 임베딩으로 status 무필터 NN 1위=**현대 그랜저 IG(sold, dist 0.2693)**, on_sale 한정 경로에서는 그랜저 제외·팰리세이드 진입. `WHERE status='on_sale'`이 sold를 실제로 거름을 데이터로 증명.
  - [x] 4.4 회귀: 전체 pytest **50 passed**(43 기존 + 7 신규). 공유 헬퍼 추출 후 sql_rag_node 테스트 정상.
  - [x] 4.5 (해당 없음 — 키 존재로 라이브 전부 수행. 거짓 "완료" 없음.)

- [x] **Task 5 — 보고 + 산출물 정리** (AC: 전체)
  - [x] 5.1 Completion Notes에 OI-B 결정·라이브 추천 예시·FR11 교차검증·§5.5 처리 기록.
  - [x] 5.2 변경/신규 파일을 File List에 기록.

### Review Findings (code-review 2026-06-21)

- [x] [Review][Patch] `_vec_literal`이 NaN/Inf 임베딩 성분을 무효 pgvector 리터럴로 방출 — fail-loud 누락 [api/app/embeddings.py `_check_dim`] — **수정 완료(2026-06-21):** `_check_dim`에 `math.isfinite` 유한성 검사를 추가해 NaN/Inf 성분이 섞이면 명확한 한국어 RuntimeError로 즉시 실패하도록 했다(경로 A·B 공통 보호). 회귀 테스트 `test_check_dim_rejects_non_finite_values` 추가. pytest 51 passed.
- [x] [Review][Defer] 근거 가이드에 유사도 임계값 없음 — 무관한 가이드도 "참고:"로 첨부될 수 있음 [api/app/graph/doc_rag_node.py:64-68] — deferred, 답변 정교화는 4.5 `answer_node` 소관(스토리 범위 밖)

> 트리아지: decision-needed 0 · patch 1 · defer 1 · dismiss 8. 자체 테스트 `pytest` 전체 50 passed(신규 doc_rag 7 포함), 회귀 0.
> dismiss 내역(검토 후 비채택): ①`_vec_literal` SQL 인젝션 의심 → 벡터는 `%s` 파라미터 바인딩이라 안전(오탐). ②`rows_to_cards` int(None) 크래시 → `0002_listings.sql` year/price/mileage `NOT NULL`로 불가능(오탐). ③answer의 `query` 보간 → 값으로 전달돼 format 인젝션 없음. ④listings/guide LIMIT 바인딩 스타일 불일치 → 1은 리터럴, 무해. ⑤`str(float)` 과학표기 의존 → pgvector가 수용, 현재 정상(잠재 취약성 메모만). ⑥`ListingCard` import "미사용" → 타입 주석에 사용 중. ⑦§5.5 필터+벡터 → 스펙대로 주석만(과한 튜닝 금지). ⑧int 캐스팅 NOT NULL 의존 → 현재 계약상 안전.

## Dev Notes

### ⚠️ 결정적 함정 — 반드시 숙지 (이 스토리의 실패 원인)

**함정 #1 — `ai_readonly`는 RLS로 sold를 못 거른다(FR11은 검색 쿼리가 책임).**
4.1·4.3에서 확정된 사실이 경로 B에도 그대로 적용된다: `ai_readonly`엔 `listings`·`guide_documents` 전 행을 보는 permissive 정책(`using(true)`)이 걸려 있어 **sold 매물도 보인다.** 그러므로 유사도 검색 SQL에 **반드시 `WHERE status = 'on_sale'`을 직접** 넣어야 한다(AC2). 4.3은 sql_guard가 이 존재를 검증했지만, **경로 B는 SQL을 코드가 직접 쓰므로 가드가 없다 → 코드가 빼먹으면 sold가 그대로 샌다.** 또한 `embedding IS NULL` 행이 섞이지 않게 `AND embedding IS NOT NULL`도 넣는다.
[Source: 4-1 readonly.py 주석(6-8); 4-3 함정 #2(78-80); conventions.md §6; epic-3-retro 액션4]

**함정 #2 — pgvector는 사전 필터링을 안 한다(필터+벡터 동시 사용 시 결과 누락, 연구 §5.5).**
pgvector는 **먼저 유사도로 후보를 뽑고 그다음 필터를 적용**한다 → `WHERE status='on_sale' ORDER BY embedding <=> q LIMIT 5` 같은 질의에서 (HNSW가 뽑은 후보 중 on_sale이 부족하면) **5개보다 적게** 나올 수 있다. 본 데모는 on_sale 42/44로 필터가 매우 느슨해 실질 위험은 작지만, **원리는 알고 코드에 주석**으로 남긴다. 완화책(필요 시): ① 세션에 `SET hnsw.iterative_scan = 'relaxed_order'`(pgvector 0.8.0, Supabase 지원) ② 후보 과다 조회 후 잘라쓰기. **데모 규모(44행)에선 `WHERE status='on_sale' ... LIMIT 5` 그대로로 충분** — 과한 튜닝(iterative_scan 세션 파라미터 배관)은 넣지 말고 주석으로만 근거 남길 것.
[Source: research §5.5(198-209), §8 #8(287)]

**함정 #3 — 질의 임베딩은 `embed_query`(RETRIEVAL_QUERY)를 써라(`embed_documents` 아님).**
4.2 `embeddings.py`는 적재용 `embed_documents`(task_type=RETRIEVAL_DOCUMENT)와 검색용 `embed_query`(RETRIEVAL_QUERY)를 구분해 만들었다. Gemini는 문서와 질의를 다른 벡터 공간 힌트로 인코딩하므로, **검색에서 `embed_documents`를 쓰면 매칭 품질이 떨어진다.** 4.4는 반드시 **`embed_query(query)`** 를 호출한다(4.2가 "정의만, 4.4에서 사용"으로 남겨둔 바로 그 함수). 저장 벡터도 검색 벡터도 모두 L2 정규화돼 있으니 코사인 `<=>`이 일관되게 동작한다.
[Source: 4-2 embeddings.py(50-52)·Dev Notes(186); research §5.1(173)]

**함정 #4 — 경로 B는 sql_guard를 거치지 않는다 — 그래서 더 조심.**
경로 A는 LLM이 SQL을 만들어 가드가 검사했다. 경로 B의 SQL은 **개발자가 직접 쓰고 벡터·LIMIT만 파라미터 바인딩**하므로 인젝션 위험이 없어 가드가 불필요하다. 단, 그 대가로 **FR11(on_sale)·LIMIT·테이블 한정이 전부 코드 책임**이다(가드가 안 잡아준다). SQL은 고정 문자열 + `%s` 파라미터로만 구성하고, **벡터/사용자값을 f-string으로 SQL에 직접 끼워넣지 말 것**(파라미터 바인딩 강제). 실행은 4.3과 동일하게 항상 `ai_readonly`(`run_select`)로(이중 방어).
[Source: 4-3 sql_guard.py 사상(1-12); architecture.md#AI 경로 안전장치(201)]

### 설계 결정 — OI-B: 의미검색 직접 추천 vs 가이드→구조조건 재질의 (확정: **의미검색 직접 추천 + 가이드 근거**)

경로 B를 구현하는 두 방식:
- **Design 1(채택) — 의미검색 직접 추천:** 질의 임베딩으로 `listings.embedding`을 NN 검색해 **의미가 가까운 on_sale 매물을 곧장 추천**하고, `guide_documents`도 NN 검색해 **근거(왜 어울리는지)** 를 answer에 곁들인다. AC1의 "매물 설명·옵션 텍스트 + 가이드 문서를 pgvector 유사도 검색"을 그대로 충족하고, AC2(on_sale)는 매물 검색 `WHERE`로 충족.
- **Design 2(미채택) — 가이드→구조조건 추출 후 SQL 재질의:** 가이드 문서를 검색→LLM으로 추천 body_type/seats 추출→구조 SQL 재생성. "근거 조건으로 매물 조회"에 더 문자적이나 **LLM SQL 재생성이 부활**해 sql_guard·재시도·실패모드가 다시 필요 → 단일 고정 테이블·데모 규모에 **과잉**. 프로젝트 원칙(스키마·구현 단순화)과 연구 §4.3(모호 질의는 라우터에서 되묻기)·deferred-work 4-3 #4(모호 질의 clarify는 4.5)와도 어긋남.

> Design 1에서 **가이드 문서는 장식이 아니라 answer의 "근거(적합 차종/특성)"** 로 실제 검색·노출된다(AC1 충족). "근거 조건으로 매물 조회"는 *매물 설명·옵션 임베딩 자체가 의미형 질의에 대한 근거 매칭*이라는 해석으로 충족한다. 정교한 근거→답변 합성은 4.5 `answer_node` 소관.

### doc_rag_node 설계 (`app/graph/doc_rag_node.py`)

```python
"""경로 B — 문서 기반 RAG 노드. 의미형 질의 → embed_query → pgvector 코사인 검색 → ListingCard.
  · 질의 임베딩은 embed_query(RETRIEVAL_QUERY, 4.2 재사용). embed_documents 아님(함정 #3).
  · 경로 B는 sql_guard를 안 거친다 → FR11(on_sale)·LIMIT은 코드가 직접 책임(함정 #1·#4).
  · 실행은 항상 ai_readonly(run_select, 4.1 재사용). 벡터는 %s::vector 파라미터 바인딩(직접 박기 금지).
4.4는 호출 가능한 노드 함수만 만든다. /ai/search 라우팅(A/B)·StateGraph 조립은 4.5.
"""
from app.embeddings import embed_query
from app.db.readonly import run_select
from app.graph.listing_cards import SELECT_COLUMNS, rows_to_cards  # 공유 헬퍼(Task 3)
from app.db.sql_guard import DEFAULT_LIMIT   # 추천 기본 개수(5) 재사용

def _vec_literal(vec: list[float]) -> str:
    # pgvector 텍스트 포맷 "[v1,v2,...]" — register_vector 없이 %s::vector로 캐스팅 가능.
    return "[" + ",".join(map(str, vec)) + "]"

def doc_rag_node(query: str) -> dict:   # returns {"answer": str, "listings": list[ListingCard]}
    qvec = _vec_literal(embed_query(query))   # 키 부재 시 require()가 fail-loud
    rows = run_select(
        f"SELECT {SELECT_COLUMNS} FROM listings "
        "WHERE status = 'on_sale' AND embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector LIMIT %s",
        (qvec, DEFAULT_LIMIT),
    )
    listings = rows_to_cards(rows)
    guides = run_select(
        "SELECT title FROM guide_documents WHERE embedding IS NOT NULL "
        "ORDER BY embedding <=> %s::vector LIMIT 1",
        (qvec,),
    )
    ...  # answer 조립(근거 가이드 제목 포함) + 0건 FR17 분기
```

- **`<=>`(코사인)**: 저장·질의 벡터 모두 L2 정규화돼 있어 코사인이 일관적(연구 §5.1). 거리 오름차순(ORDER BY ASC 기본)이 곧 유사도 내림차순.
- **`%s::vector` 캐스팅**: `run_select(query, params)`는 새 연결마다 `register_vector`를 호출하지 않으므로, 벡터를 텍스트 리터럴로 바인딩하고 SQL에서 `::vector`로 캐스팅하는 방식이 가장 단순·안전(4.2 backfill 설계 메모와 동일 발상, 단 여기선 읽기 경로).
- **`DEFAULT_LIMIT`(=5)** 재사용: brief "약 5개" 정합(4.3 코드리뷰에서 분리 확정). 경로 B도 동일 기본 개수.
- **answer 템플릿**: N>0 → `"'{query}'에 어울리는 매물 {n}건을 찾았어요."`(+근거 가이드 있으면 ` (참고: {title})`), N==0 → `"조건에 맞는 매물이 없어요. 원하시는 용도나 예산을 알려주시면 더 잘 찾아드릴게요."`(FR17). LLM 추가 호출 불필요.

### ListingCard 매핑·SELECT 컬럼 공유 (Task 3, drift 방지)

- 4.3 `sql_rag_node.py`에 이미 `_SELECT_COLUMNS = "id, manufacturer, model, year, price, mileage, region"`와 `_to_cards(rows)`가 있다. **두 노드가 같은 7필드·같은 순서**를 쓰므로 공유 헬퍼(`app/graph/listing_cards.py`)로 추출해 단일출처화한다(아키텍처 AR5 일관성·drift 금지).
- `rows_to_cards`는 튜플 인덱스 0~6을 `ListingCard(id=str, manufacturer, model, year=int, price=int, mileage=int, region)`로 매핑(4.3 `_to_cards`와 동일 로직 그대로 이동).
- `sql_rag_node.py`는 import만 바꾸고 **나머지 동작은 그대로** — 4.3의 `test_sql_rag_node.py`(7 케이스)가 깨지지 않아야 한다(회귀 0). 헬퍼 추출이 어려우면 최소한 컬럼 상수만이라도 공유하고 매핑 순서를 동일하게 맞춘다.

### 라이브러리·환경

- **추가 의존성 없음** — `langchain-google-genai`(embed_query)·`psycopg`/`pgvector`(읽기·벡터)·`run_select` 전부 4.2/4.3에 존재. [Source: api/pyproject.toml#optional-dependencies.ai]
- 임베딩 모델: `settings.gemini_embedding_model="gemini-embedding-001"`, `gemini_embedding_dim=768`(config.py 단일출처). 질의 임베딩 차원이 768인지 첫 호출 1건으로 확인(4.2 검증과 동일 — `_check_dim`이 fail-loud).
- 키: `GEMINI_API_KEY`·`DATABASE_URL`(Session pooler, :5432) — 4.2/4.3에서 `api/.env`에 입력됨(없으면 라이브 불가).
- pgvector 0.8.0(라이브 확인됨) — `hnsw.iterative_scan` 사용 가능하나 데모 규모상 미사용(함정 #2).

### 이전 스토리 학습 (적용할 패턴)

- **이중 방어·실행은 항상 ai_readonly(4.1·4.3):** 경로 B도 `run_select`(readonly.py)를 그대로 재사용 — 새 DB 헬퍼 만들지 말 것. 가드가 없는 대신 FR11·LIMIT을 코드가 책임.
- **`embed_query`는 4.2가 4.4용으로 남긴 함수:** 4.2 Completion Notes "embed_query()는 4.4 재사용 위해 정의만". 4.4가 그 약속을 이행. 재구현 금지(재사용).
- **단일출처·drift 금지(2-1·3-3·4-2·4-3):** 컬럼명·단위·차종 용어는 `0002_listings.sql`·`docs/conventions.md` 단일출처. ListingCard 7필드·SELECT 컬럼은 4.3과 동일(Task 3 공유 헬퍼).
- **fail-loud(1.4·4.1·4.3):** GEMINI_API_KEY/DATABASE_URL 부재 시 `require()`로 명확한 한국어 에러. 조용한 빈 결과 금지(0건 FR17 안내와 "실패로 인한 빈 결과"는 다르다 — 후자는 에러로).
- **실DB·실LLM 검증(4.2·4.3):** mock은 단위 테스트용. 의미검색은 라이브 1건 이상 + MCP `execute_sql` 교차검증으로 sold 제외·타당성 눈 확인. 키 없으면 escalate(거짓 통과 금지).
- **4.2가 채운 데이터:** `listings` 44건 임베딩(on_sale 42), `guide_documents` 6건 임베딩, 전수 768·L2 norm 1.0. 4.4는 **이 데이터를 검색만** 한다(재적재 금지 — backfill은 4.2 범위).

### 파일 구조 (생성/수정 대상)

```
api/app/graph/doc_rag_node.py        # 신규 — 경로 B 문서 RAG 노드(embed_query→코사인 검색→ListingCard)
api/app/graph/listing_cards.py       # 신규 — SELECT 컬럼·rows_to_cards 공유 헬퍼(drift 방지, Task 3)
api/app/graph/sql_rag_node.py        # 수정(최소) — 공유 헬퍼 import로 _SELECT_COLUMNS·_to_cards 대체
api/tests/test_doc_rag_node.py       # 신규 — 노드 순수 로직(임베딩·DB 모킹) 단위 테스트
```
- **만들지 않음(후속):** `graph/router_node.py`·`guard_node.py`·`answer_node.py`(4.5), `/ai/search` 라우팅 분기·StateGraph 조립(4.5), 0004 마이그레이션·코퍼스·backfill(4.2 done). [Source: architecture.md#Project Structure(382-391)]
- 기존 `embeddings.py`(embed_query)·`db/readonly.py`(run_select)·`schemas/ai.py`(ListingCard)·`db/sql_guard.py`(DEFAULT_LIMIT)는 **재사용**(변경 최소).

### 자체 테스트 방식 (CLAUDE.md §6)

- **백엔드 = HTTP/DB로 검증**(브라우저 아님). 4.4는 화면도 /ai/search 변경도 없으므로 **단위(모킹) + 라이브(노드 직접 호출)** 중심.
  - 단위: `pytest tests/test_doc_rag_node.py` — `embed_query`·`run_select` monkeypatch로 벡터 포맷·매핑·FR17·on_sale WHERE 포함을 네트워크 없이 검증(AC4 핵심).
  - 라이브: `doc_rag_node("패밀리카로 무난한 거")` 등 의미형 질의 1~2건 직접 호출 → 매물·근거 가이드 눈 확인. MCP `execute_sql`로 같은 임베딩의 NN을 sold 포함/제외로 비교해 FR11 실증.
  - HTTP: **4.4에선 /ai/search 미변경** → HTTP E2E는 4.3 상태 유지(경로 A) 확인 정도. 경로 B의 HTTP 노출은 4.5.
- 회귀: 4.1·4.2·4.3 기존 pytest(43 passed)가 여전히 통과(특히 sql_rag_node 공유 헬퍼 추출 후).

### 사용자 직접 처리 항목 (왜 / 어디서)

- **`api/.env`의 `GEMINI_API_KEY`** — 질의 임베딩(embed_query) 호출에 필수, 코드 밖 비밀값 / `api/.env`. (4.2/4.3에서 입력했으면 그대로 사용.)
- **`api/.env`의 `DATABASE_URL`(Session pooler)** — 유사도 검색을 ai_readonly로 실행하는 연결 / Supabase Connect → Session pooler(:5432). (4.1~4.3과 동일.)
- ⚠️ 둘 중 하나라도 없으면 **라이브 검증 불가** → 단위 테스트까지만 완료 보고하고 escalate. **거짓 "완료" 금지.**

### 알려진 이연(Deferred) — 이번 스토리에서 다시 따지지 말 것

- **DB 풀링·connect_timeout·async 블로킹 부재**(deferred-work 4-1) — `run_select`는 호출마다 새 연결을 열고 풀이 없다. 데모 경부하라 영향 작음. **4.4 범위 밖**(풀링 도입은 별도 작업). 그대로 재사용한다.
- **`context` 필드 크기 제약**(deferred-work 4-1) — 4.4 노드는 `context`를 받지 않으므로 무관. 멀티턴은 4.6.

### References

- [Source: epics.md#Story 4.4(484-498)] — 2개 AC 원문(doc_rag_node 의미검색·가이드 근거·on_sale 추천).
- [Source: epics.md#FR15(102), #FR17(104)] — 경로 B 문서 RAG·0건 안내.
- [Source: architecture.md#AI 경로 안전장치(201), #Format Patterns(268-271), #Project Structure(382-391)] — 읽기전용 롤·응답 계약·doc_rag_node 위치.
- [Source: architecture.md#Data Architecture(139-193)] — listings/guide_documents 임베딩·컬럼·HNSW.
- [Source: docs/conventions.md §1(임베딩768)·§4(응답·ListingCard)·§6(FR11)] — 768 단일출처·계약·sold 비노출.
- [Source: research §5.1(170-174)·§5.2(176-180)·§5.5(198-209)·§5.6(211-217)·§8 #8] — 코사인 `<=>`·HNSW·필터+벡터 함정·하이브리드 보류.
- [Source: 4-2 story embeddings.py(50-52)·Dev Notes(186-187)·Completion(301)] — `embed_query`(RETRIEVAL_QUERY) 4.4용 정의, task_type 구분.
- [Source: 4-2 story 라이브 데이터(221-226)·검증(285)] — guide 6·listings 44 임베딩 768·norm 1.0(4.4 검색 대상).
- [Source: 4-3 story sql_rag_node(_SELECT_COLUMNS·_to_cards)·sql_guard 사상·함정 #2] — 공유 헬퍼·ai_readonly 재사용·FR11 호출부 책임.
- [Source: 4-1 readonly.py(run_select·readonly_connection)] — ai_readonly 실행 헬퍼 재사용.
- [Source: deferred-work.md 4-1·4-3] — DB 풀링/타임아웃·모호질의 clarify(4.5)·context(4.6) 이연 경계.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (dev-story 워크플로우). 임베딩: `gemini-embedding-001`@768(Gemini API, RETRIEVAL_QUERY).

### Debug Log References

- 단위 테스트: `pytest tests/test_doc_rag_node.py` → 7 passed.
- 라이브 의미검색 로그(`doc_rag_node 질의=... 매물 N건, 근거 가이드=...`)로 실제 검색 결과 눈 확인.
- FR11 교차검증: `run_select`로 status 무필터 vs on_sale 한정 NN top5 비교(그랜저 IG[sold] 제외 확인).
- 전체 회귀: `pytest` → 50 passed (43 기존 + 7 신규).

### Completion Notes List

- **무엇을·왜:** 4.3(경로 A=정확한 조건 SQL)에 이어 **경로 B(의미형 질의 → 임베딩 유사도 검색)** 를 구현했다. 사용자 질문을 4.2와 같은 768 임베딩으로 바꿔, `listings.embedding`(매물 설명·옵션)과 `guide_documents.embedding`(가이드)을 pgvector 코사인 `<=>`로 검색해 의미가 가까운 **on_sale 매물을 추천**하고 가이드 문서를 **근거**로 곁들인다. 4.2가 "정의만" 해둔 `embed_query()`가 드디어 실사용됐다.
- **AC 충족:**
  - AC1: `doc_rag_node` 작성. 의미형 질의 → embed_query → 매물·가이드 둘 다 유사도 검색 → `{answer, listings[]}`(ListingCard) 반환.
  - AC2(FR11): 매물 검색 SQL에 `WHERE status='on_sale'`을 코드가 직접 강제. 라이브 교차검증으로 sold(그랜저 IG)가 의미상 1위여도 추천에서 제외됨을 데이터로 증명.
  - AC3(FR17): 매물 0건이면 `listings: []` + 조건 완화/재질문 안내. 키 부재는 `require()` fail-loud(조용한 빈 결과 아님).
  - AC4: 임베딩·DB 모킹 단위 테스트 7케이스(SQL의 on_sale·`<=>`·바인딩, 매핑, FR17, 근거 제목) + 라이브 3건·FR11 교차검증.
- **OI-B 결정(의미검색 직접 추천 + 가이드 근거):** 가이드→LLM 구조조건 추출 후 SQL 재질의(Design 2)는 단일 테이블·데모 규모에 과잉(LLM SQL 생성·가드 부활)이라 미채택. 의미검색으로 매물을 곧장 추천하고, 가이드는 answer의 근거로 검색·노출.
- **경로 B는 sql_guard 미경유(함정 #4):** LLM이 SQL을 만들지 않고 코드가 고정 SQL + `%s` 파라미터 바인딩만 하므로 인젝션 위험 없음 → 가드 불필요. 대가로 FR11(on_sale)·LIMIT을 코드가 책임짐. 실행은 항상 `ai_readonly`(이중 방어).
- **§5.5(필터+벡터) 처리:** pgvector는 사전 필터링을 안 해 필터+벡터 조합 시 결과가 LIMIT보다 적게 나올 수 있으나, 본 데모 on_sale 42/44로 필터가 느슨해 실질 위험 작음 → 코드 주석으로 근거만 남기고 과한 튜닝(iterative_scan 배관) 미적용.
- **drift 방지(Task 3):** SELECT 컬럼·튜플→ListingCard 매핑을 `listing_cards.py`로 단일출처화해 경로 A·B 공유. sql_rag_node는 import만 변경, 동작·테스트 불변(회귀 0).
- **라이브 의미검색 품질(눈 확인):** "패밀리카"→대형/SUV(캠리·K8·카니발), "초보자 작은 차"→소형(스파크·모닝), "전기차"→전 차량 전기차(EV6·아이오닉5·테슬라). 각 질의에 맞는 근거 가이드가 함께 반환됨.
- **범위 준수:** `/ai/search`·라우터·StateGraph·answer_node·guard_node는 안 건드림(4.5). 0004·코퍼스·backfill 재실행 안 함(4.2 done). `context`(멀티턴)는 노드가 받지 않음(4.6).

### File List

**신규**
- `api/app/graph/doc_rag_node.py` — 경로 B 문서 RAG 노드(embed_query → 코사인 검색 → ListingCard + 근거 가이드).
- `api/app/graph/listing_cards.py` — SELECT 컬럼·`rows_to_cards` 공유 헬퍼(경로 A·B drift 방지).
- `api/tests/test_doc_rag_node.py` — 노드 순수 로직 단위 테스트 7케이스(임베딩·DB 모킹).

**수정**
- `api/app/graph/sql_rag_node.py` — 공유 헬퍼 import로 `_SELECT_COLUMNS`·`_to_cards` 대체(동작 불변).
- `api/tests/test_sql_rag_node.py` — 매핑 테스트 import를 공유 헬퍼(`listing_cards.rows_to_cards`)로 변경(같은 로직 검증).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 4-4 상태 전이(ready-for-dev → in-progress → review).

## Change Log

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-06-21 | Story 4.4 컨텍스트 작성 — 경로 B 문서 RAG. OI-B=의미검색 직접 추천+가이드 근거 확정 | Status → ready-for-dev |
| 2026-06-21 | 경로 B 구현 — doc_rag_node(embed_query→pgvector 코사인 검색→ListingCard) + listing_cards 공유 헬퍼. 라이브 의미검색 3건·FR11 교차검증(sold 제외)·단위 7케이스. 50 passed | Status → review |
