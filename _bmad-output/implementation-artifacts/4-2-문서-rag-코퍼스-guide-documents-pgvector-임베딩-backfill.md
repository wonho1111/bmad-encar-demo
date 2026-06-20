# Story 4.2: 문서 RAG 코퍼스 작성 + guide_documents + pgvector HNSW + 임베딩 backfill

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want 문서 RAG의 기반이 될 차량 상식·구매 가이드 문서를 직접 작성하고, 코퍼스·벡터 인덱스를 만들어 매물·문서 임베딩을 일괄 적재(backfill)하고 싶다,
so that 다음 스토리(4.4 문서 RAG·4.3 의미검색)가 **실제 데이터**로 동작한다.

> **이 스토리의 본질:** 4.1이 "AI 앱이 뜨는 토대"였다면, 4.2는 **"AI가 검색할 실제 데이터를 채우는 일"** 이다. 세 덩어리다 — ①`guide_documents` 테이블 + 벡터 인덱스(스키마), ②차량 상식·구매 가이드 문서를 **사람이 직접 글로 작성**(코퍼스②), ③매물 설명·옵션 텍스트(코퍼스①)와 가이드 문서를 **Gemini 768차원 임베딩으로 변환해 DB에 적재**(backfill). 이게 끝나면 4.4에서 "패밀리카 무난한 거" 같은 의미형 질문에 pgvector 유사도 검색이 가능해진다.
>
> *임베딩(embedding): 글의 의미를 숫자 벡터로 바꾼 것. 의미가 비슷한 글은 벡터도 가깝다 → 유사도 검색의 핵심.*
> *backfill(백필): 비어 있던(NULL) 기존 데이터 칸을 나중에 일괄로 채워 넣는 작업. 지금 매물 44건의 `embedding`이 전부 NULL이라 이를 채운다.*
> *코퍼스(corpus): 검색·학습의 대상이 되는 문서 모음.*

## Acceptance Criteria

1. **(AC1 — 스키마 + HNSW 인덱스)** `0004_guide_documents` 마이그레이션이 적용되면 `guide_documents(id, title, content, embedding vector(768), created_at)` 테이블과 `embedding`에 대한 **HNSW 인덱스**가 존재한다. `listings.embedding`에도 동일 HNSW 인덱스가 생성된다.
   - *HNSW(Hierarchical Navigable Small World): 벡터 유사도 검색을 빠르게 해주는 그래프형 인덱스. 수천~수만 행 규모에 적합(연구 권장).*
2. **(AC2 — 코퍼스② 작성 + 적재)** 차량 상식·구매 가이드 문서(차종별 특성·패밀리카/초보자 적합 차종·유지비·신뢰성·차형 용어 매핑 등)를 **실제 한국어 내용으로 작성**하고, `guide_documents`에 적재한다(경로 B 검색 대상). 작성 문서는 **형식적·빈 문자열 금지**, 사실에 근거한 자연스러운 한국어.
3. **(AC3 — 코퍼스①·② 768 임베딩 적재)** 코퍼스② 가이드 문서와 시드 매물의 설명·옵션 텍스트(코퍼스①)가 **Gemini 768 임베딩**으로 적재된다. `guide_documents.embedding`과 대상 `listings.embedding`이 채워지고, **모든 임베딩의 차원이 정확히 768**로 컬럼과 일치한다.
4. **(AC4 — listings backfill)** `embedding`이 NULL이던 시드 매물에 backfill을 실행하면 설명·옵션(+핵심 사양) 텍스트가 768 임베딩으로 채워진다. backfill은 **멱등**(재실행해도 중복/오류 없음)하고, 임베딩 차원(768)이 컬럼과 일치한다.

### 범위 밖 (이 스토리에서 구현하지 않음 — 과잉구현 금지)

- ❌ 실제 문서 RAG 검색 노드(`doc_rag_node`)·유사도 검색 쿼리 로직 → **4.4**.
- ❌ 라우터·Text-to-SQL·가드·답변 조립 → **4.3 / 4.5**.
- ❌ `/ai/search` stub을 실제 검색으로 교체 → **4.3~4.5**(4.2는 데이터만 채운다).
- ❌ 질의 시점 임베딩 사용(검색 흐름) → **4.4**. 단, 재사용 위해 `embed_query()` 헬퍼는 **지금 만들어두되 backfill에선 미사용**.
- ❌ AI 검색 화면(웹 UI) → **4.7**.
- ❌ OI5 데모 질의셋 → **4.5**(여기선 코퍼스만).

## Tasks / Subtasks

- [x] **Task 1 — `0004_guide_documents` 마이그레이션(테이블 + HNSW + ai_readonly 가시성)** (AC: 1)
  - [x] 1.1 `supabase/migrations/0004_guide_documents.sql` 작성 — 테이블 + `guide_documents` HNSW + `listings.embedding` HNSW + `ai_readonly` GRANT SELECT + RLS enable + `for select to ai_readonly using(true)` 정책.
  - [x] 1.2 Supabase MCP `apply_migration`으로 실제 프로젝트(`psrnsasxpkpwqdukjdmt`)에 적용 → `{"success":true}`. out-of-order 갭(0003·0005) 정상 통과.
  - [x] 1.3 적용 검증(MCP): `embedding`이 `vector(768)`, HNSW 인덱스 2개 존재(`m=16, ef_construction=200`), `set role ai_readonly; select count(*) from guide_documents;` 에러 없이 실행.

- [x] **Task 2 — 코퍼스② 가이드 문서 작성** (AC: 2)
  - [x] 2.1 `api/corpus/` 생성, 6개 문서 작성(차종별 특성 / 패밀리카 / 초보자 / 연료별 유지비 / 신뢰성 체크포인트 / 차형 용어 매핑).
  - [x] 2.2 사실 기반 자연스러운 한국어(content 690~1028자). `body_type`·`fuel` 허용값과 용어 일치(단일출처 정합).
  - [x] 2.3 파일 헤더 규칙: 첫 줄 `# 제목` → title, 나머지 → content.

- [x] **Task 3 — `app/embeddings.py` Gemini 768 임베딩 헬퍼(L2 정규화 필수)** (AC: 3)
  - [x] 3.1 AI 의존성 설치: `pip install -e ".[ai,dev]"`(langchain-google-genai 4.2.5·pgvector 0.4.2).
  - [x] 3.2 `api/app/embeddings.py` 작성 — `embed_documents()`(RETRIEVAL_DOCUMENT)·`embed_query()`(RETRIEVAL_QUERY), `output_dimensionality=768` + L2 정규화 + 차원 단언.
  - [x] 3.3 `config.py`의 `gemini_embedding_model`·`gemini_embedding_dim` 설정값 사용(하드코딩 없음).

- [x] **Task 4 — backfill 스크립트(쓰기 경로·멱등)** (AC: 3, 4)
  - [x] 4.1 `api/scripts/backfill_embeddings.py` 작성. 쓰기 연결(SET ROLE 미사용) + DATABASE_URL 비밀번호 퍼센트 인코딩(`safe_conninfo`).
  - [x] 4.2 매물 backfill: `embedding IS NULL` 행을 핵심사양+옵션+설명 합성 텍스트로 임베딩 후 UPDATE. IS NULL 가드로 멱등.
  - [x] 4.3 가이드 backfill: `api/corpus/*.md` 파싱 → delete 후 재삽입(파일 단일출처).
  - [x] 4.4 `pgvector.psycopg.register_vector`로 list↔vector 바인딩(택1). 진행 로그 출력.

- [x] **Task 5 — 실행 + 차원/건수 검증** (AC: 3, 4)
  - [x] 5.1 선행 요건 충족: `api/.env`에 `GEMINI_API_KEY`·`DATABASE_URL` 존재(escalate 불필요).
  - [x] 5.2 실 Gemini 임베딩 1건 선검증 → dim 768·L2 norm 1.0 확인 후 backfill 실행.
  - [x] 5.3 검증(MCP): guide_documents 6/6 임베딩·전수 768, listings null 0·44/44 임베딩·768.
  - [x] 5.4 ai_readonly 가시성 + 코사인 최근접(`<=>`) 검색 성공(함정 #1 회피 확인).
  - [x] 5.5 최근접 스모크: "패밀리카" 질의 → 차종별 특성(0.086)·초보자(0.125) 등 의미상 타당한 top3 반환.

- [x] **Task 6 — 보고 + 산출물 정리** (AC: 전체)
  - [x] 6.1 Completion Notes에 건수·차원·정규화·멱등·모델명 확정 근거 기록.
  - [x] 6.2 변경 파일·DB 변경을 File List에 기록.

## Dev Notes

### ⚠️ 결정적 함정 — 반드시 숙지 (이 스토리의 실패 3대 원인)

**함정 #1 — ai_readonly가 guide_documents를 못 본다(0006 함정 재현).**
`0006_readonly_role`은 이미 적용돼 있고 `alter default privileges ... grant select on tables to ai_readonly`가 걸려 있다. 하지만 **RLS가 켜진 테이블은 "테이블 권한(GRANT) ≠ 행 가시성(정책)"** 이다. 4.1 listings에서 겪은 것과 동일: GRANT만 하면 `ai_readonly`는 **0건만** 본다. 따라서 0004에서 `guide_documents`에 **`for select to ai_readonly using(true)` 정책을 명시**해야 한다. 이걸 빠뜨리면 4.4 문서 RAG가 "임베딩은 있는데 검색 결과가 0건"으로 조용히 실패한다.
[Source: 4-1 story #결정적 함정(84-99), Review Findings #8(deferred → 본 스토리가 처리)]

**함정 #2 — gemini-embedding-001은 768로 줄이면 자동 정규화하지 않는다(수동 L2 정규화 필수).**
`gemini-embedding-001`의 기본 차원은 **3072**다. `output_dimensionality=768`로 줄이면 **자동 정규화가 안 되어** 벡터 길이가 1이 아니다 → 코사인 유사도 검색 품질이 크게 망가진다. **임베딩을 받은 즉시 코드에서 L2 정규화**(각 성분을 벡터 크기로 나눔)해야 한다. (참고: 차세대 "Gemini Embedding 2"는 자동 정규화하지만, 본 프로젝트 단일출처는 `gemini-embedding-001`@768로 고정.) 저장·검색 모두 정규화된 벡터를 쓰고, HNSW 인덱스는 `vector_cosine_ops`로 만든다.
- **모델명 확정:** 연구 문서(§6.3)에 "`gemini-embedding-001` 폐기됨 [미확인]"이라는 메모가 있으나 **이는 부정확**하다 — 2026-06 확인 결과 `gemini-embedding-001`은 GA(정식)이며 768은 권장 차원(3072 대비 품질 손실 0.26%). 단일출처(`docs/conventions.md §1`·`config.py`)대로 진행하되, **실행 시 첫 응답 차원이 768인지 1건으로 먼저 확인**(다르면 멈추고 보고).
[Source: WebSearch 2026-06 — ai.google.dev/gemini-api/docs/embeddings; docs/conventions.md §1; research §6.3]

**함정 #3 — backfill은 ai_readonly로 쓰면 안 된다(읽기전용이라 INSERT/UPDATE 거부).**
4.1의 `app/db/readonly.py`는 연결 후 `SET ROLE ai_readonly`를 걸어 SELECT만 되게 한다. backfill은 **데이터를 쓰는 오프라인 적재 작업**이므로 그 헬퍼를 쓰면 `insufficient_privilege`로 실패한다. backfill 스크립트는 `DATABASE_URL`로 연결하되 **SET ROLE 없이**(=연결 롤 postgres, 쓰기·RLS 우회) 작업한다. ⚠️ **절대 `ai_readonly`에 쓰기 권한을 GRANT하지 말 것**(NFR2 위반). 런타임 AI 경로는 계속 읽기전용으로 둔다.
[Source: 4-1 app/db/readonly.py; architecture.md#AI 경로 안전장치(201)]

### 0004 마이그레이션 설계 (`supabase/migrations/0004_guide_documents.sql`)

```sql
-- 0004_guide_documents.sql — FR15 문서 RAG 코퍼스② + pgvector HNSW
-- 적용 순서: 0001 → 0002(+0002b/c/d 패치) → 0004 → 0006(이미 적용). 0003(chat)·0005(admin)은 타 에픽이 채움(번호 갭 의도됨).
-- ⚠️ 0006(읽기전용 롤) 적용 후이므로, ai_readonly가 이 테이블을 읽으려면 GRANT(테이블 권한) + 정책(행 가시성)이 둘 다 필요.

create extension if not exists vector;  -- 멱등(라이브 0.8.0 설치 확인됨)

-- ── 테이블 ───────────────────────────────────────────────
create table public.guide_documents (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  content     text not null,
  embedding   vector(768),                 -- gemini-embedding-001(output 768, L2 정규화) 정합 (conventions §1)
  created_at  timestamptz not null default now()
);

comment on table public.guide_documents is
  'FR15 문서 RAG 코퍼스② — 차량 상식·구매 가이드. embedding은 4.2 backfill(L2 정규화 768)로 채움. AI 읽기전용 경로만 조회.';

-- ── HNSW 인덱스 (코사인). 정규화된 768 벡터 대상. 연구 권장 m=16, ef_construction=200 ──
create index guide_documents_embedding_hnsw
  on public.guide_documents using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- listings.embedding 의미검색(4.4)용 동일 인덱스(없으면 순차 스캔). 빈/NULL 임베딩은 인덱스가 알아서 스킵.
create index if not exists listings_embedding_hnsw
  on public.listings using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- ── ai_readonly 권한 + RLS 가시성 (⚠️ 함정 #1: GRANT만으론 행 안 보임) ──
grant select on public.guide_documents to ai_readonly;
alter table public.guide_documents enable row level security;
create policy "guide_documents_ai_readonly_select" on public.guide_documents
  for select to ai_readonly using (true);
-- (클라이언트는 guide_documents를 직접 읽지 않음 → authenticated 정책은 미요구·생략. 필요해지면 후속에서 추가.)
```

- **HNSW를 빈 테이블에 먼저 만들어도 됨** — 행이 INSERT/UPDATE될 때 점진적으로 색인된다. backfill 전에 인덱스를 만들어두는 순서가 단순.
- **조회 시 `ef_search=40`**(연구 권장)은 인덱스 속성이 아니라 세션 파라미터(`set hnsw.ef_search=40`) — 실제 검색은 4.4 소관. 여기선 인덱스 생성까지만.
- **pgvector 0.8.0**라 `hnsw.iterative_scan` 등 신기능 사용 가능(4.4에서 필요 시).

### embeddings.py 설계 (`api/app/embeddings.py`)

```python
"""Gemini 768 임베딩 헬퍼 — gemini-embedding-001(output 768)은 자동 정규화하지 않으므로 L2 정규화 필수."""
import math
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from app.config import settings, require


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return vec if norm == 0 else [x / norm for x in vec]


def _client(task_type: str) -> GoogleGenerativeAIEmbeddings:
    return GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,                  # gemini-embedding-001
        google_api_key=require("GEMINI_API_KEY", settings.gemini_api_key),
        task_type=task_type,                                    # RETRIEVAL_DOCUMENT | RETRIEVAL_QUERY
        output_dimensionality=settings.gemini_embedding_dim,    # 768
    )


def _check_dim(vec: list[float]) -> list[float]:
    if len(vec) != settings.gemini_embedding_dim:               # fail-loud (conventions §1)
        raise RuntimeError(
            f"임베딩 차원 불일치: {len(vec)} != {settings.gemini_embedding_dim}. 모델/차원 설정 확인."
        )
    return vec


def embed_documents(texts: list[str]) -> list[list[float]]:
    """적재용(문서) 임베딩. 차원 검증 + L2 정규화."""
    vecs = _client("RETRIEVAL_DOCUMENT").embed_documents(texts)
    return [_l2_normalize(_check_dim(v)) for v in vecs]


def embed_query(text: str) -> list[float]:
    """질의용 임베딩 — 4.4에서 사용(여기선 정의만)."""
    return _l2_normalize(_check_dim(_client("RETRIEVAL_QUERY").embed_query(text)))
```

- **`task_type` 구분 이유:** Gemini는 적재 문서(`RETRIEVAL_DOCUMENT`)와 검색 질의(`RETRIEVAL_QUERY`)를 다른 벡터 공간 힌트로 인코딩 → 매칭 품질↑. backfill은 문서 쪽만 사용.
- `langchain-google-genai`의 정확한 인자명(`output_dimensionality`/`task_type`/`google_api_key`)은 설치 버전에서 1건 호출로 확인 후 진행(버전별 차이 가능). 핵심 계약은 "768 + L2 정규화 + RETRIEVAL_DOCUMENT".

### backfill 스크립트 (`api/scripts/backfill_embeddings.py`) — 설계 메모

- **쓰기 연결(함정 #3):** `psycopg.connect(settings.database_url)` 후 `SET ROLE` 호출 안 함. (readonly.py는 SET ROLE을 걸지만 이 스크립트는 그 헬퍼를 쓰지 않는다.)
- **vector 바인딩:** 가장 단순한 방식은 임베딩 리스트를 `"[v1,v2,...]"` 문자열로 만들어 SQL에서 `%s::vector`로 캐스팅. (또는 `from pgvector.psycopg import register_vector; register_vector(conn)` 후 리스트 직접 바인딩 — 택1.)
- **매물 임베딩 텍스트 합성(코퍼스①):** `description`이 없는 행도 의미가 생기도록 핵심 사양을 함께 엮는다. 예:
  `f"{manufacturer} {model} {body_type} {year}년식 {fuel}. 옵션: {', '.join(options or [])}. {description or ''}"`.
  (라이브: 44건 중 `description` 보유 42건 — 나머지 2건은 이전 테스트 잔여물이나, 합성 텍스트로 임베딩 가능.)
- **멱등:** 매물은 `WHERE embedding IS NULL`만 처리(재실행 시 채워진 건 스킵). 가이드는 `delete` 후 `insert`(파일이 단일출처). 둘 다 재실행 안전.
- **배치:** Gemini 호출 비용·레이트 고려해 텍스트를 묶어 `embed_documents([...])`로 한 번에(무료 등급이라 과도한 동시호출 자제). 실패 시 어디까지 처리했는지 로그.
- **위치 선택 근거:** 런타임 코드가 아닌 **일회성 적재 도구**라 `app/`(런타임 패키지)가 아니라 `api/scripts/`에 둔다. 아키텍처 트리의 `app/embeddings.py`(헬퍼)는 런타임·backfill 공용이므로 `app/`에 두고, 실행 진입점만 `scripts/`.

### 코퍼스② 필수 주제 (AC2 — 실제 한국어로 작성)

epics AC와 idea.md(OI6)가 지정한 경로 B 검색 대상. 아래 주제를 **사실 기반**으로 충실히 작성(데모 품질):

1. **차종별 특성** — `body_type` 허용값(경차/소형차/준중형차/중형차/대형차/스포츠카/SUV/RV/경승합차/승합차/화물차) 각각의 용도·장단점·대표 사용층.
2. **패밀리카 적합 차종** — 공간·안전·연비·승차인원 관점. 어떤 `body_type`/`seats`가 가족용으로 무난한지.
3. **초보 운전자 적합 차종** — 작은 차체·자동 변속·시야·주차 난이도.
4. **연료별 유지비·연비** — `fuel` 허용값(가솔린/디젤/하이브리드/전기/LPG) 각각의 유지비·연비·적합 주행 패턴.
5. **중고차 신뢰성·구매 체크포인트** — 무사고(`accident_free`)·주행거리(`mileage`)·연식(`year`) 보는 법, 합리적 판단 기준.
6. **차형 용어 매핑 가이드** — "세단/해치백/쿠페" 등 차체형태 용어 ↔ 본 데모의 크기기반 `body_type` 매핑(예: 세단→준중형차·중형차·대형차). **OI5(4.5 질의셋)와 직접 연결**되는 문서.

- **용어 일치(단일출처):** 문서 안의 차종·연료 표현을 `0002_listings.sql` CHECK 허용값과 맞춘다(Text-to-SQL·질의셋·시드와 drift 금지). [Source: epics.md#AR7]

### 이전 스토리 학습 (적용할 패턴)

- **0006 함정 = 본 스토리 함정 #1:** 4.1이 listings에서 겪고 해결한 "GRANT≠가시성"을 guide_documents에 그대로 적용. 4.1 Review #8(deferred)이 명시적으로 "4.2에서 ai_readonly SELECT GRANT/정책"을 지목 → **본 스토리가 그 부채를 갚는다.**
- **fail-loud(1.4·4.1 config.py):** 차원 불일치·키 부재를 조용히 넘기지 말고 명확한 한국어 에러로 즉시 실패.
- **단일출처·drift 금지(2-1·2-5·3-3):** 임베딩 차원 768, 차종·연료 용어, 단위(km·원·cc)는 `docs/conventions.md`·`0002`가 단일출처. 코퍼스 문서·합성 텍스트도 이 용어를 따른다.
- **실DB 검증(2-5·3-3·4-1):** mock 금지. Supabase MCP로 실제 행수·차원(`vector_dims`)·ai_readonly 가시성을 눈으로 확인. 거짓 통과 금지(키 없으면 escalate).
- **시드 매물 현황(2-5):** seed.sql에 시드 매물 39건 + 잔여물 → 라이브 44건, 전부 `embedding NULL`(2-5 AC2가 "Epic 4 backfill" 명시). 본 스토리가 그 약속을 이행.

### 라이브 DB 현재 상태 (2026-06-21 MCP 확인)

- `listings`: **44건, 전부 `embedding IS NULL`**, `on_sale` 42건, `description` 보유 42건.
- `guide_documents`: **미존재**(0004 신규 생성 대상).
- pgvector 확장: **0.8.0** 설치됨(HNSW·iterative_scan 지원).
- 적용된 마이그레이션: `0001_profiles`, `0002_listings`(+`0002b/c/d` 패치), `0006_readonly_role`. ⚠️ **로컬 `supabase/migrations/`에는 0002b/c/d 파일이 없다**(DB에만 적용됨, 선행 스토리 운영 흔적). 본 스토리는 이에 **의존하지 않으며** 0004만 새로 추가한다(0002b/c/d 파일화는 본 스토리 범위 밖 — 발견 사실로만 기록).

### 라이브러리·환경

- AI 그룹 설치: `cd api && pip install -e ".[ai]"` → `langchain-google-genai`(임베딩)·`pgvector`(psycopg vector 바인딩). [Source: api/pyproject.toml#optional-dependencies.ai]
- 설정값(이미 존재): `GEMINI_API_KEY`(사용자 입력 필요), `GEMINI_EMBEDDING_DIM=768`, `GEMINI_EMBEDDING_MODEL=gemini-embedding-001`, `DATABASE_URL`(Session pooler). [Source: api/app/config.py, api/.env.example]
- `scripts/check-embedding-dim.ps1`(아키텍처 언급): 현재 미존재. 차원 확인은 backfill 첫 호출 1건 단언으로 대체(별도 ps1 신설은 불필요·범위 밖).

### 파일 구조 (생성/수정 대상)

```
supabase/migrations/0004_guide_documents.sql   # 신규 — 테이블 + HNSW×2 + ai_readonly 정책
api/corpus/                                     # 신규 — 가이드 문서(.md, 한 주제=한 파일) 6개+
api/app/embeddings.py                           # 신규 — Gemini 768 임베딩(L2 정규화) 헬퍼
api/scripts/backfill_embeddings.py             # 신규 — 일회성 적재(쓰기 경로·멱등)
api/scripts/__init__.py                         # (필요 시) 패키지화
```
- **만들지 않음(후속):** `app/graph/doc_rag_node.py`(4.4), 검색 쿼리 로직(4.4), `/ai/search` 실연결(4.3~4.5). [Source: architecture.md#Project Structure(382-390)]

### 자체 테스트 방식 (CLAUDE.md §6)

- **백엔드·데이터 작업 = HTTP/DB로 검증**(브라우저 아님). 본 스토리는 화면이 없으므로 **DB 검증 중심**(2-5 시드와 동일 계열):
  - MCP `execute_sql`: `guide_documents` 행수·`embedding is not null`·`vector_dims(embedding)=768`, `listings` `embedding is null` 잔여 0·`vector_dims=768`.
  - MCP: `set role ai_readonly; select count(*) from guide_documents;` 에러 없음(함정 #1 회피 확인).
  - backfill 스크립트는 멱등 재실행 1회로 누적·중복 없음 확인.
- pytest는 임베딩 호출이 외부 키 의존이라 **단위 테스트는 정규화 함수(`_l2_normalize`)·차원 검증(`_check_dim`)** 같은 순수 로직만 대상(네트워크 없는 부분). 실 임베딩 적재는 라이브 DB 검증으로 갈음.

### 사용자 직접 처리 항목 (왜 / 어디서)

- **`api/.env`에 실제 `GEMINI_API_KEY` 입력** — Gemini 임베딩 호출에 필수, 코드 밖 비밀값이라 사용자만 입력 가능 / `api/.env`. (무료 등급으로 충분, NFR6.)
- **`api/.env`에 `DATABASE_URL`(Session pooler) 입력** — backfill 쓰기 연결에 필요 / Supabase 대시보드 Connect → Session pooler(:5432). (4.1과 동일 값.)
- ⚠️ 위 두 값이 없으면 backfill **실행 불가** → 구현물(마이그레이션·코퍼스·코드)까지만 완료하고 실행은 사용자 키 입력 후. **거짓 "완료" 보고 금지.**

### References

- [Source: epics.md#Story 4.2(437-461)] — 4개 AC 원문(스키마·코퍼스 작성·768 임베딩·backfill).
- [Source: epics.md#Epic4 기반 흡수(139), #FR15(40), #AR7(75)] — 코퍼스①②·시드 정합·HNSW.
- [Source: architecture.md#Data Architecture(133-193)] — guide_documents 컬럼·HNSW 권장·768 정합.
- [Source: architecture.md#Project Structure(327-391)] — 0004 위치·embeddings.py·마이그레이션 번호.
- [Source: docs/conventions.md §1] — 임베딩 768 단일출처·정합 점검.
- [Source: research/technical-ai-search-architecture-research-2026-06-16.md §5.2(176-182), §6.3(184-188), §7(192-202)] — HNSW(m=16/ef_construction=200/ef_search=40), 모델명 [미확인] 메모, 청킹.
- [Source: WebSearch 2026-06 ai.google.dev/gemini-api/docs/embeddings] — gemini-embedding-001 GA·768 권장·**<3072는 수동 L2 정규화 필요**.
- [Source: 4-1 story #결정적 함정(84-99)·Review #8(70)] — ai_readonly GRANT≠가시성, guide_documents 정책 부채 인계.
- [Source: 2-5 story AC2(16)] — 시드 매물 embedding은 NULL → Epic 4(4.2) backfill 약속.
- [Source: supabase/migrations/0002_listings.sql(20,30,86-118)·0006(라이브 적용)] — pgvector 확장·embedding 컬럼·RLS to authenticated(함정 근거).

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Claude Opus 4.8, 1M context)

### Debug Log References

- 마이그레이션: Supabase MCP `apply_migration(0004_guide_documents)` → `{"success":true}`.
- 임베딩 선검증(Python): `embed_documents(['패밀리카로 무난한 중형차 추천'])` → dim 768, L2 norm 1.0. `embed_query` 동일. → `GEMINI_API_KEY`(`AQ.Ab8...` 형식)도 langchain-google-genai 4.2.5에서 정상.
- pytest: **12 passed**(4.1의 7 + 신규 임베딩 4 + DATABASE_URL 채워져 이전 skip이던 test_readonly 통과). 회귀 0.
- backfill 1차: listings 44건·guide 6개 적재(commit 완료). 최종 요약 print만 Windows cp949 콘솔이 이모지(✅) 미지원으로 예외 → 데이터엔 무영향. print를 ASCII로 수정.
- backfill 2차(멱등 재실행): listings 0건(이미 채워져 스킵) + guide delete 후 6개 재삽입. 최종 출력 정상.
- DB 검증(MCP): guide_documents 6/6 임베딩, listings null 0·44/44 임베딩, 전수 `vector_dims=768`. 단일 행 L2 norm(올바른 쿼리) = 1.0000(guide·listing 모두). 멱등 재실행 후 guide 6건·distinct 6(중복 0).
- ⚠️ 검증 쿼리 함정 1건: 초기 norm 쿼리가 `unnest(...) limit 1`로 첫 성분만 잘라 0.0294 오표시 → `unnest((select embedding ... limit 1)::real[])`로 정정해 1.0 확인. 데이터 문제 아님.

### Completion Notes List

- **무엇을·왜:** 4.1의 "AI 토대" 위에 AI가 검색할 실제 데이터를 채웠다 — ①`guide_documents` 테이블+HNSW(스키마), ②차량 상식·구매 가이드 6개 문서 직접 작성(코퍼스②), ③매물 44건 설명·옵션(코퍼스①)과 가이드를 768 임베딩으로 일괄 적재. 4.4 문서 RAG·의미검색의 데이터 기반 완성.
- **AC 충족:**
  - AC1: `0004_guide_documents` 적용 — `guide_documents(id,title,content,embedding vector(768),created_at)` + HNSW 2개(guide_documents·listings, `vector_cosine_ops`, m=16/ef_construction=200).
  - AC2: 코퍼스② 6개 문서(차종별 특성·패밀리카·초보자·연료별 유지비·신뢰성 체크포인트·차형 용어 매핑) 사실 기반 한국어로 작성·적재. `body_type`/`fuel` 용어 단일출처 일치.
  - AC3: 가이드 6개 + 매물 44건 Gemini 768 임베딩 적재. 전수 `vector_dims=768`, L2 norm 1.0(정규화).
  - AC4: listings backfill로 NULL 44→0. `IS NULL` 가드로 멱등(재실행 시 매물 0건 스킵, 가이드 delete-then-insert로 중복 0).
- **결정적 함정 3건 모두 처리:**
  - #1(ai_readonly 가시성): 0004에 `for select to ai_readonly using(true)` 정책 명시 → 읽기전용 롤로 코사인 검색 성공 확인(4.1 Review #8 부채 해소).
  - #2(수동 L2 정규화): `gemini-embedding-001`@768은 자동 정규화 안 됨 → 코드에서 L2 정규화. 저장 벡터 norm 1.0 검증. **연구 §6.3의 "모델 폐기됨[미확인]" 메모는 부정확**(2026-06 확인: GA·768 권장)임을 확인하고 단일출처대로 진행.
  - #3(쓰기 경로): backfill은 `SET ROLE ai_readonly` 없이 연결 롤(postgres)로 쓰기. ai_readonly엔 쓰기 권한 부여 안 함(NFR2 유지).
- **부수 처리:** `DATABASE_URL` 비밀번호의 `?`·`$` 특수문자가 URL 파싱을 깨뜨려 `safe_conninfo()`로 퍼센트 인코딩. (4.1에서 이 연결은 미검증 상태였음 — 본 스토리에서 실연결·쓰기까지 검증.)
- **범위 준수:** `doc_rag_node`·검색 흐름·`/ai/search` 실연결은 만들지 않음(4.3~4.5). `embed_query()`는 4.4 재사용 위해 정의만.
- **데이터 상태:** 라이브 DB에 적재 완료(데모 데이터). guide_documents 6건, listings 44건 임베딩.

### File List

**신규**
- `supabase/migrations/0004_guide_documents.sql`
- `api/corpus/01-차종별-특성.md`
- `api/corpus/02-패밀리카-적합-차종.md`
- `api/corpus/03-초보운전자-적합-차종.md`
- `api/corpus/04-연료별-유지비-연비.md`
- `api/corpus/05-중고차-신뢰성-체크포인트.md`
- `api/corpus/06-차형-용어-매핑.md`
- `api/app/embeddings.py`
- `api/scripts/backfill_embeddings.py`
- `api/tests/test_embeddings.py`

**DB 변경 (Supabase 프로젝트 `psrnsasxpkpwqdukjdmt`)**
- `0004_guide_documents` 마이그레이션 적용(테이블 + HNSW×2 + ai_readonly 정책)
- 데이터 적재: `guide_documents` 6행, `listings` 44행 `embedding` backfill

**수정**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (4-2 상태 전이)
- `_bmad-output/implementation-artifacts/4-2-...-backfill.md` (본 기록)

## Change Log

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-06-21 | Story 4.2 구현 — `0004_guide_documents`+HNSW + 코퍼스 6문서 + Gemini 768 임베딩 backfill(매물44·가이드6) | 12 passed, 라이브 DB·MCP 검증(차원768·norm1.0·ai_readonly 의미검색), Status → review |
