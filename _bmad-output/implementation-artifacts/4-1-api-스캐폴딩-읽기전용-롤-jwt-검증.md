# Story 4.1: api 스캐폴딩 + 읽기전용 롤 + JWT 검증

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want AI 전용 FastAPI+LangGraph 백엔드(`api/`)와 읽기전용 DB 롤·Supabase JWT 검증을 세우고 싶다,
so that 안전한 토대(쓰기 불가·로그인 사용자만) 위에서 이후 AI 검색 노드(4.3~4.5)를 구현한다.

> **이 스토리의 본질:** 기능(실제 AI 검색)이 아니라 **토대(scaffolding)** 다. 지금까지 레포는 Next.js 웹 단일 스택이었고, 이 스토리에서 **처음으로 별도 Python 백엔드**가 추가된다. `POST /ai/search`는 아직 **빈 껍데기(stub)** — 진짜 라우터/Text-to-SQL/RAG는 4.3~4.5에서 붙인다. 4.1이 책임지는 건 ①앱이 뜨고 응답·문서가 나옴 ②AI가 DB에 닿을 때 **SELECT만** 되는 읽기전용 경로 ③**로그인 안 한 요청은 401**, 이 세 가지 안전 토대다.
>
> *스캐폴딩(scaffolding): 건물 짓기 전 세우는 비계처럼, 기능 코드를 올리기 전 디렉터리·설정·연결을 잡아두는 뼈대 작업.*

## Acceptance Criteria

1. **(AC1 — 앱 기동 + OpenAPI 문서)** `api/`가 스캐폴딩되고 `POST /ai/search`를 호출하면 FastAPI 앱이 응답하고, 자동 OpenAPI 문서(`/docs`, `/openapi.json`)가 노출된다.
   - *OpenAPI: REST API의 엔드포인트·요청·응답 형태를 기계가 읽을 수 있게 적은 표준 명세. FastAPI가 코드에서 자동 생성한다.*
2. **(AC2 — 읽기전용 롤, NFR2)** `0006_readonly_role` 마이그레이션이 적용된 뒤 AI 경로가 DB에 접근하면, **SELECT만 가능한 읽기전용 롤(`ai_readonly`)** 로 실행된다. 같은 경로로 INSERT/UPDATE/DELETE를 시도하면 권한 부족으로 거부된다.
3. **(AC3 — JWT 검증)** Supabase JWT 검증(`app/auth.py`)이 동작할 때, **인증 헤더가 없거나 무효한 요청은 401**로 거절된다(로그인 구매자만 허용). 유효한 토큰이면 통과한다.
   - *JWT(JSON Web Token): 로그인 성공 시 서버가 발급하는, 서명으로 위조를 막은 사용자 증명 토큰. 클라이언트가 `Authorization: Bearer <jwt>` 헤더로 동봉한다.*

### 범위 밖 (이 스토리에서 구현하지 않음 — 과잉구현 금지)

- ❌ 실제 LangGraph 노드(라우터/Text-to-SQL/문서RAG/가드/답변 조립) → **4.3~4.5**. 4.1의 `/ai/search`는 stub.
- ❌ `guide_documents` 테이블·pgvector HNSW·임베딩 backfill → **4.2**.
- ❌ `db/sql_guard.py`(SELECT 검증·LIMIT·화이트리스트) → **4.3**.
- ❌ 멀티턴 맥락 반영 로직 → **4.6** (단, 요청 스키마에 `context` 옵션 필드는 **지금 만들어두되 무시**해도 됨).
- ❌ AI 검색 화면(웹 UI) → **4.7**.

## Tasks / Subtasks

- [x] **Task 1 — `api/` 디렉터리 + Python 환경 스캐폴딩** (AC: 1)
  - [x] 1.1 `api/` 폴더와 `app/` 패키지 트리 생성 (아래 "파일 구조 요구사항"의 트리 그대로). 각 패키지 폴더에 `__init__.py` 둔다.
  - [x] 1.2 `api/pyproject.toml` 작성 — 의존성은 아키텍처 확정 버전(아래 "라이브러리·버전" 참조). 가상환경(venv)은 `api/.venv`에 생성.
  - [x] 1.3 `api/.env.example` 작성 — `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `DATABASE_URL`(읽기전용 연결용), `GEMINI_*`(다음 스토리 대비, 지금 미사용). 루트 `.env.example`의 `api/.env` 섹션과 **불일치 없게** 동기화.
  - [x] 1.4 `app/config.py` — `pydantic-settings`로 env 로드(누락 시 기동 시점에 명확한 에러). 웹의 `getSupabaseEnv()` fail-loud 패턴(1.4 학습)을 Python으로 재현.
- [x] **Task 2 — FastAPI 앱 + `POST /ai/search` stub + OpenAPI** (AC: 1)
  - [x] 2.1 `app/main.py` — FastAPI 인스턴스, `routers/ai.py` 라우터 포함, CORS(웹 `localhost:3000` 허용), 헬스 체크 `GET /health`.
  - [x] 2.2 `app/schemas/ai.py` — Pydantic 모델: `SearchRequest{query:str, context: list|None=None}`, `ListingCard{id,manufacturer,model,year,price,mileage,region}`(snake_case), `SearchResponse{answer:str, listings:list[ListingCard]}`, `ErrorBody{code,message}`/`ErrorResponse{error}`.
  - [x] 2.3 `app/routers/ai.py` — `POST /ai/search`. **인증 의존성 필수(Task 4)**. 본문: 진짜 AI 대신 **stub 응답** `{answer: "...(4.3~4.5에서 연결)", listings: []}` 반환. (선택: AC2 시연용으로 읽기전용 경로로 `on_sale` 매물 수를 세어 `answer`에 넣어 DB 연결까지 한 번에 증명.)
  - [x] 2.4 `/docs`·`/openapi.json` 노출 확인.
- [x] **Task 3 — `0006_readonly_role` 마이그레이션 + 읽기전용 연결** (AC: 2)
  - [x] 3.1 `supabase/migrations/0006_readonly_role.sql` 작성 (아래 "읽기전용 롤 설계" 그대로). 핵심: `ai_readonly` 롤 + `GRANT SELECT` + `ALTER DEFAULT PRIVILEGES ... GRANT SELECT` + **`listings`에 `to ai_readonly using(true)` permissive SELECT 정책**(⚠️ 아래 함정 참조) + `GRANT ai_readonly TO <연결롤>`(SET ROLE용). **INSERT/UPDATE/DELETE는 절대 GRANT하지 않는다.**
  - [x] 3.2 Supabase MCP `apply_migration`으로 실제 프로젝트(`psrnsasxpkpwqdukjdmt`)에 적용. 적용 후 `list_migrations`로 등록 확인.
  - [x] 3.3 `app/db/readonly.py` — `psycopg`로 `DATABASE_URL` 연결 후 **반드시 `SET ROLE ai_readonly`** 를 거는 컨텍스트 매니저/헬퍼. SELECT 전용 사용을 강제(쓰기 메서드 미제공).
  - [x] 3.4 검증: 읽기전용 경로로 `select count(*) from public.listings` → 0보다 큼(행이 보임). `insert into public.listings ...` → `insufficient_privilege`로 실패. 둘 다 자체 테스트로 증명.
- [x] **Task 4 — Supabase JWT 검증 (`app/auth.py`)** (AC: 3)
  - [x] 4.1 `app/auth.py` — FastAPI 의존성 `get_current_user`. `Authorization: Bearer <jwt>` 추출 → 검증 → user 반환. 헤더 없음/형식 오류/검증 실패 → `HTTPException(401)`(한국어 메시지 + `error` 포맷).
  - [x] 4.2 검증 방식: **권장 = supabase-py `auth.get_user(token)`**(추가 비밀값 불필요, `SUPABASE_URL`+`SUPABASE_ANON_KEY`만 사용). 대안(로컬·무네트워크)은 JWKS 검증 — "JWT 검증 방식" 참조. 택1 후 Dev Notes에 근거 기록.
  - [x] 4.3 `routers/ai.py`의 `/ai/search`에 `Depends(get_current_user)` 부착 → 미인증 401.
- [x] **Task 5 — pytest 자체 테스트 + 기동 검증 보고** (AC: 1,2,3)
  - [x] 5.1 `tests/test_health.py` — `GET /health` 200, `/openapi.json` 200 (AC1).
  - [x] 5.2 `tests/test_auth.py` — 토큰 없는 `POST /ai/search` → 401 (AC3). (유효 토큰 경로는 실제 토큰 확보가 어려우면 의존성 오버라이드로 200 확인.)
  - [x] 5.3 `tests/test_readonly.py` — 읽기전용 연결로 SELECT 성공 + INSERT 차단 (AC2). DB 접속 불가 환경이면 `skip` 처리하고 이유 명시.
  - [x] 5.4 dev 서버를 백그라운드로 기동(`uvicorn app.main:app --port 8000`) → `GET /health`·`/docs`·미인증 `POST /ai/search`(401) **HTTP로 직접 검증**(CLAUDE.md §6: 백엔드는 브라우저 아닌 HTTP로) → 끝나면 프로세스 정리.

### Review Findings (code review 2026-06-21)

- [x] [Review][Patch] Supabase Auth 장애를 401로 위장하지 말 것 — 전송 오류(연결 실패·타임아웃·5xx)는 `_auth_unavailable()`로 503 분리 + `logger.warning`으로 원인 로깅, 토큰 자체 무효만 401 유지. [api/app/auth.py] ✅ 적용
- [x] [Review][Patch] 미처리 예외가 공통 에러 포맷을 깨고 500 누출 — `@app.exception_handler(Exception)` 추가: 내부 메시지는 `logger.exception`으로만 남기고 사용자에겐 `{error:{code:"internal_error",...}}` 500 통일. [api/app/main.py] ✅ 적용
- [x] [Review][Patch] test_readonly 단언이 0건 함정을 못 잡음 — `>= 0` → `> 0`로 강화(라이브 DB 44행으로 통과 확인). [api/tests/test_readonly.py] ✅ 적용
- [x] [Review][Patch] create_client()가 try 밖에 있어 초기화 실패 시 비포맷 500 — `create_client`·`get_user`를 같은 try로 묶어 초기화 실패까지 잡음. [api/app/auth.py] ✅ 적용
- [x] [Review][Patch] query에 max_length 없음 + 공백-only 통과 — `max_length=1000` + `field_validator`로 공백-only 질의 거부. [api/app/schemas/ai.py] ✅ 적용
- [x] [Review][Defer] DB 경로 견고화(풀링·timeout·async 블로킹) [api/app/db/readonly.py, api/app/auth.py] — deferred, run_select 미사용 stub(4.3에서 처리)
- [x] [Review][Defer] context 필드 크기/스키마 제약 없음 [api/app/schemas/ai.py:13] — deferred, 실제 사용하는 4.6에서 제약
- [x] [Review][Defer] CORS 기본 origin이 127.0.0.1/Vercel preview/https 미포함 [api/app/main.py:24] — deferred, 배포 시 CORS_ORIGINS 설정(4.7)
- [x] [Review][Defer] 0006 ALTER DEFAULT PRIVILEGES는 동일 소유자 생성 테이블만 적용 [supabase/migrations/0006_readonly_role.sql] — deferred, 4.2 guide_documents에서 ai_readonly SELECT 명시 GRANT/정책

## Dev Notes

### 아키텍처 준수 (반드시 따를 가드레일)

- **토폴로지 경계(절대 위반 금지):** 클라이언트는 Supabase에 직접 접근(인증·CRUD·채팅, RLS 보호). FastAPI는 **AI 검색 전용**이며 **쓰기 권한이 없다.** AI 경로는 오직 읽기전용 롤로만 DB에 닿는다. [Source: architecture.md#Architectural Boundaries(396), #Critical Decisions(121)]
- **엔드포인트:** `POST /ai/search`. JSON 페이로드·필드는 **`snake_case`로 통일**(DB·Pydantic 일치, 변환 없음). [Source: architecture.md#Naming(250-252)]
- **공통 응답 계약:** `{ "answer": string, "listings": ListingCard[] }`. 0건이면 `listings: []`. **에러 포맷:** `{ "error": { "code": string, "message": string } }`, HTTP 상태코드 정확히(401/422/500 등). [Source: architecture.md#Format Patterns(268-271)]
- **ListingCard 필드(확정):** `id, manufacturer, model, year, price, mileage, region` — snake_case, **사진/썸네일 필드 없음**. [Source: architecture.md#Format Patterns(269)]
- **Python 컨벤션:** 모듈·함수 `snake_case`, 클래스 `PascalCase`. 구조는 **기능별(feature-based)**: `app/graph/`(LangGraph 노드, 4.3+), `app/routers/`, `app/schemas/`(Pydantic), `app/db/`. 테스트는 `tests/`(pytest). [Source: architecture.md#Code(257), #Structure Patterns(263)]
- **무상태(stateless):** 서버는 대화 이력을 저장하지 않는다(멀티턴은 클라이언트가 맥락 동봉, 4.6). 4.1에선 요청 스키마에 `context` 옵션만 받아두고 미사용. [Source: architecture.md#NFR4(39), epics.md Story 4.6]
- **인증 흐름:** 클라이언트가 Supabase 세션 토큰 보관 → AI 호출 시 `Authorization: Bearer <jwt>` 동봉 → `api/auth.py`가 검증. [Source: architecture.md#Communication Patterns(292), #핵심 인증/RBAC(412)]

### ⚠️ 결정적 함정 — 읽기전용 롤과 RLS의 상호작용 (이 스토리에서 가장 중요)

`listings`(0002)의 SELECT RLS 정책들은 전부 **`for select to authenticated`** 로 되어 있다. 즉 Supabase의 `authenticated` 롤에게만 행 가시성을 준다. 그런데 AI 경로는 **`authenticated`가 아닌 별도 `ai_readonly` 롤**로 DB에 직접 붙는다(PostgREST·RLS 우회 경로가 아니라 Postgres 직결). 이때:

- RLS가 켜진 테이블에서 **현재 롤(`ai_readonly`)에 적용되는 정책이 하나도 없으면 → 0건만 반환된다.** GRANT SELECT만 해서는 행이 안 보인다(테이블 권한 ≠ 행 가시성).
- 그래서 `0006`에서 **`ai_readonly`용 permissive SELECT 정책을 명시**해야 한다:
  ```sql
  create policy "listings_ai_readonly_select" on public.listings
    for select to ai_readonly using (true);
  ```
  → `ai_readonly`는 sold 포함 **모든 행**을 본다.
- **그러면 FR11(sold 비노출)은 누가 지키나?** → **앱(AI 경로)이 쿼리에서 `status='on_sale'`로 강제한다.** AI 경로는 RLS에 기대지 않고 스스로 필터한다. 이는 Epic 3 회고 **액션 #4**("Text-to-SQL sql_guard·문서 RAG 결과 필터에서도 sold 비노출")와 정확히 일치하는 의도된 설계다. 4.1에선 stub이라 실제 필터는 없지만, **읽기전용 헬퍼 주석에 "FR11은 호출부 쿼리가 책임(4.3+)"을 명시**해 다음 스토리가 잊지 않게 한다.

> 이 함정을 모르면: 읽기전용 롤이 조용히 0건을 반환 → AC2가 "DB 접근은 되는데 데이터가 없네"로 잘못 통과하고, 4.3에서야 터진다. **반드시 `select count(*)`가 0보다 큰지 자체 검증할 것.**

대안: `ai_readonly`에 `BYPASSRLS` 속성을 주면 정책 없이도 전 행이 보인다. 단 관리형 Supabase에서 `postgres`가 `BYPASSRLS` 롤 생성을 허용하는지 불확실하므로, **permissive 정책 방식을 1순위**로 한다(확실히 동작). MCP 적용 중 막히면 그때 BYPASSRLS를 시도.

### 읽기전용 롤 설계 (`0006_readonly_role.sql`)

```sql
-- 0006_readonly_role.sql — NFR2: AI 전용 읽기전용 롤(ai_readonly)
-- 적용 순서 메모: 0003(chat·Epic5)·0004(guide_documents·4.2)·0005(admin·Epic6)는 아직 미생성.
--   0006은 현재 존재하는 테이블(profiles·listings)에만 의존하므로 먼저 적용 가능.
--   guide_documents(4.2)에는 그 마이그레이션에서 동일한 ai_readonly SELECT 정책을 추가한다.
-- ⚠️ 쓰기 권한(INSERT/UPDATE/DELETE)은 어디에도 GRANT하지 않는다(NFR2 핵심).

-- 1) 롤 생성 (NOLOGIN: 직접 로그인 대신 연결 롤이 SET ROLE로 전환)
do $$ begin
  if not exists (select from pg_roles where rolname = 'ai_readonly') then
    create role ai_readonly nologin;
  end if;
end $$;

-- 2) 스키마 사용 + 현재 모든 테이블 SELECT
grant usage on schema public to ai_readonly;
grant select on all tables in schema public to ai_readonly;

-- 3) 앞으로 만들어질 테이블도 자동으로 SELECT 부여(예: 4.2 guide_documents)
alter default privileges in schema public grant select on tables to ai_readonly;

-- 4) RLS 가시성 — ai_readonly는 모든 행을 본다(FR11은 앱 쿼리가 status='on_sale'로 강제)
create policy "listings_ai_readonly_select" on public.listings
  for select to ai_readonly using (true);
-- (profiles를 AI가 읽어야 한다면 동일 패턴으로 정책 추가. 4.1 stub은 listings면 충분.)

-- 5) 연결 롤이 SET ROLE ai_readonly 할 수 있게 멤버십 부여
--    (Supabase 연결 사용자명에 맞춰 조정 — 보통 postgres)
grant ai_readonly to postgres;
```

- **런타임 사용 패턴:** `app/db/readonly.py`가 `DATABASE_URL`로 연결 → **즉시 `SET ROLE ai_readonly`** → 이후 모든 쿼리는 읽기전용 권한으로 실행. 쓰기 시도는 Postgres가 `insufficient_privilege`로 거부 → NFR2가 DB 차원에서 보장된다.
- **연결 방식 = Session 풀러로 확정(검토 완료).** Supabase **Session 풀러**(`...pooler.supabase.com:5432`, 사용자명 `postgres.<project_ref>`)를 쓴다. 근거: ① `SET ROLE`이 세션 내내 유지돼 읽기전용 패턴이 가장 단순 ② IPv4라 로컬(Windows)·Vercel에서 바로 연결 ③ psycopg prepared statement 기본 설정 그대로 동작. `DATABASE_URL`은 대시보드 Connect → **Session pooler** 문자열을 그대로 사용(포트 `5432` 확인 — `6543`은 Transaction 풀러이므로 아님).
  - **하지 말 것:** Transaction 풀러(`:6543`)는 트랜잭션마다 연결을 갈아끼워 `SET ROLE`이 풀린다. Direct 연결은 기본 IPv6라 환경에 따라 막힌다. 둘 다 4.1에선 쓰지 않는다.
  - **후속 전환 신호(지금 아님):** Vercel 서버리스에서 연결 수 한도에 부딪히면 그때 Transaction 풀러로 전환 + `SET LOCAL ROLE ai_readonly`(트랜잭션 한정) + psycopg `prepare_threshold=None`. 4.1에선 불필요.
- **마이그레이션 번호 갭은 의도된 것:** 아키텍처가 0006을 읽기전용 롤로 고정(단일 출처). 0003~0005는 타 에픽이 채운다. Supabase MCP `apply_migration`이 out-of-order를 받아주는지 적용 시 확인하고, 거부되면 사용자에게 보고(임의로 번호 바꾸지 말 것 — 아키텍처 매핑 깨짐).

### JWT 검증 방식 (`app/auth.py`)

| 방식 | 필요한 값 | 장점 | 단점 |
|---|---|---|---|
| **A. supabase-py `auth.get_user(token)`** (권장) | `SUPABASE_URL`, `SUPABASE_ANON_KEY` (이미 env에 있음) | 추가 비밀값 0, 구현 단순, 폐기 토큰까지 서버가 판정 | 요청당 Auth 서버 네트워크 호출 1회(데모 경부하라 무방, NFR1 관대) |
| B. JWKS 로컬 검증 (PyJWT + `PyJWKClient`) | `{SUPABASE_URL}/auth/v1/.well-known/jwks.json` (비밀값 불필요) | 네트워크 무관·빠름 | 키 캐싱·만료·알고리즘(ES256) 처리 코드 추가 |
| C. HS256 + JWT secret | `SUPABASE_JWT_SECRET`(대시보드) | 빠름 | **추가 비밀값** 관리 필요, 최신 Supabase는 비대칭키로 이동 중 |

- **4.1 권장: A**(가장 단순·추가 비밀값 없음). 성능이 문제되면 후속에서 B로 교체. 택일 근거를 Completion Notes에 남길 것.
- 401 응답 본문은 공통 에러 포맷 `{ "error": { "code": "unauthorized", "message": "로그인이 필요합니다." } }`.
- 사용자 노출 메시지는 한국어, 내부 로그는 코드·원인(architecture.md#Process Patterns(290)).

### 라이브러리·버전 (아키텍처 확정값)

```
fastapi==0.137.1
uvicorn[standard]
langgraph==1.2.4              # 4.3+에서 실사용. 지금 설치만(환경 1회 구성).
langgraph-cli[inmem]==0.4.28
langchain-google-genai        # 4.2 임베딩·4.3+ LLM. 지금 미사용.
supabase                      # auth.get_user(JWT 검증) + 필요 시 데이터
pgvector                      # 4.2 벡터. 지금 미사용.
psycopg[binary]               # 읽기전용 롤 직결(SET ROLE)
pydantic-settings             # config.py env 로드
pytest, httpx                 # 테스트(httpx = FastAPI TestClient 백엔드)
```
- Python ≥3.10 (현재 로컬 3.11.6 확인됨 — `python`·`python3` 모두 정상). [Source: architecture.md#Tech Stack(84-102)]
- `langgraph`·`langchain-google-genai`·`pgvector`는 **이번 스토리에서 코드로 쓰이지 않는다**(설치만). 환경을 한 번에 구성해 4.2~4.5 마찰을 줄이려는 의도. pyproject에 넣되 import하지 않는다(미사용 import는 린트 경고).

### 파일 구조 요구사항 (아키텍처 트리 그대로)

```
api/                              # 신규 — 레포 첫 Python 백엔드
├── pyproject.toml
├── .env.example                  # 루트 .env.example의 api/.env 섹션과 동기화
├── (.env)                        # gitignore됨 — 사용자가 실값 입력
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI 앱 + 라우터 포함 + CORS + /health
│   ├── config.py                 # pydantic-settings env 로드(fail-loud)
│   ├── auth.py                   # Supabase JWT 검증 → 401
│   ├── routers/
│   │   ├── __init__.py
│   │   └── ai.py                 # POST /ai/search (stub, 인증 필수)
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── ai.py                 # SearchRequest/SearchResponse/ListingCard/ErrorResponse
│   └── db/
│       ├── __init__.py
│       └── readonly.py           # ai_readonly 연결(SET ROLE) — SELECT 전용
└── tests/
    ├── __init__.py
    ├── test_health.py
    ├── test_auth.py
    └── test_readonly.py
```
- **4.1에서 만들지 않는 파일**(후속): `graph/*.py`(4.3~4.5), `db/sql_guard.py`(4.3), `embeddings.py`(4.2). 빈 파일로 미리 만들지 말 것(과잉구현). [Source: architecture.md#Project Structure(376-391)]

### Project Structure Notes

- `.gitignore`에 **Python/FastAPI 섹션이 이미 준비됨**(`__pycache__/`, `*.py[cod]`, `.venv/`, `.pytest_cache/`, `.mypy_cache/`) → `api/.venv` 등 자동 무시. 추가 설정 불필요.
- 루트 `.env.example`에 `api/.env` 섹션이 이미 문서화됨(`SUPABASE_URL`/`SUPABASE_ANON_KEY`/`GEMINI_*`). 이번에 **`DATABASE_URL`(읽기전용 직결용)을 추가**하고 `api/.env.example`과 양쪽을 일치시킨다.
- 마이그레이션은 `supabase/migrations/` 파일 + **Supabase MCP `apply_migration`** 로 실제 적용하는 2단계(Epic 1~3 동일 운영). 파일만 만들고 적용 안 하면 AC2 미충족.
- 포트 규칙: API `:8000`(CLAUDE.md §6). 웹은 `:3000`.

### 이전 스토리 학습 (적용할 패턴)

- **fail-loud env 가드(1.4):** 웹 `getSupabaseEnv()`가 누락 변수를 한국어로 명시해 throw. → `config.py`도 동일하게, 어떤 env가 비었는지 분명히 알리며 기동 실패시킨다(조용한 None 전파 금지).
- **단일 출처·drift 금지(2-1, 3-3):** 컬럼명·status 값·필드 목록은 architecture/0002의 정의를 그대로 재사용. `ListingCard` 필드도 임의 추가/변경 금지.
- **FR11 이중 방어 → AI는 앱 필터로(3-3 + 회고 액션4):** 위 "결정적 함정" 참조. 읽기전용 롤은 RLS로 sold를 못 거르므로 호출부가 `on_sale`을 강제(4.3+).
- **실DB 전환 검증(CM3, 3-3):** mock 말고 실제 Supabase에서 SELECT 됨/INSERT 막힘을 눈으로 확인.
- **escalate 기준(Epic 1~3):** 막히면 멈추고 사용자에게 보고. 특히 `DATABASE_URL`·JWT 검증 방식처럼 비밀값·외부설정이 필요한 지점.

### Git Intelligence (최근 작업 맥락)

- 최근 커밋은 전부 **웹(Next.js) UI/리팩터**(공용 Button, 상단바 홈 링크, 판매완료 비노출). 이 스토리는 **완전히 새로운 영역(Python `api/`)** 이라 기존 웹 코드와 충돌 지점이 없다 — 순수 신규 추가.
- 단, **루트 `.env.example` 수정**은 웹과 공유하는 파일이므로 기존 web 섹션을 건드리지 말고 api 섹션만 보강.
- 자동개발 예외(CLAUDE.md §3): 배포-테스트 목적 `develop` push는 허용, `main` 병합·push는 사용자 명시 요청 시에만.

### 자체 테스트 방식 (CLAUDE.md §6 준수)

- **백엔드는 브라우저가 아니라 HTTP로 검증한다.** `uvicorn`을 백그라운드(`run_in_background`)로 띄우고 health check 후:
  - `GET /health` → 200
  - `GET /docs`, `GET /openapi.json` → 200 (AC1)
  - 인증 없는 `POST /ai/search` → 401 (AC3)
  - (가능하면) 유효 토큰 `POST /ai/search` → 200 + `{answer, listings:[]}` 형태 (AC1/AC3)
- pytest(`tests/`)로 위를 자동화. DB 접속 불가 시 `test_readonly`는 skip + 사유 명시(거짓 통과 금지).
- 끝나면 uvicorn 프로세스 정리(Windows :8000 잔존 주의 — :3000 정리 학습과 동일 계열).

### References

- [Source: architecture.md#Initialization Commands(87-103)] — FastAPI+LangGraph 설치 명령·버전
- [Source: architecture.md#Critical Decisions(120-123)] — 토폴로지·읽기전용 롤·LIMIT/SELECT 검증
- [Source: architecture.md#Naming Conventions(245-257)] — snake_case 페이로드, `POST /ai/search`, Python 네이밍
- [Source: architecture.md#Format Patterns(268-271)] — 응답 계약 `{answer,listings}`·ListingCard·에러 포맷
- [Source: architecture.md#Communication/Process Patterns(290-292)] — 인증 흐름·에러 한국어
- [Source: architecture.md#Project Structure(327-391)] — supabase/migrations 번호, api/ 트리
- [Source: architecture.md#Architectural Boundaries(394-413)] — AI 쓰기 불가·읽기전용 롤·JWT(api/auth.py)
- [Source: epics.md#Story 4.1(417-435)] — 본 스토리 3개 AC 원문
- [Source: supabase/migrations/0002_listings.sql(86-118)] — listings RLS가 `to authenticated`인 점(함정 근거)
- [Source: epic-3-retro-2026-06-20.md#액션4·5(61-62), #Epic4 준비(78-83)] — FR11 AI 확장, 새 스택 단계적 진행 권장
- [Source: docs/conventions.md] — 단위(km·원·cc)·임베딩 768 규칙(4.2~4.3에서 본격 적용)

## Dev Agent Record

### Agent Model Used

claude-opus-4-8 (Claude Opus 4.8, 1M context)

### Debug Log References

- pytest: **7 passed, 1 skipped** (`test_readonly`는 `DATABASE_URL` 미설정으로 skip — 의도된 graceful skip).
- 라이브 HTTP(uvicorn :8000): `/health` 200, `/openapi.json` 200, `/docs` 200, 미인증 `POST /ai/search` → **401** `{"error":{"code":"unauthorized",...}}`.
- ⚠️ 한글 본문 curl 요청이 처음 400("error parsing body")으로 보였으나, **Windows 콘솔 코드페이지가 한글 바이트를 깨뜨린 curl 인코딩 artifact**였음. ASCII 본문·UTF-8 파일(`--data-binary @`) 본문 모두 401로 정상 확인. pytest TestClient(정상 UTF-8)에서도 한글 본문 401 PASS.
- AC2 DB 검증(Supabase MCP): `set role ai_readonly` 후 `select count(*) from listings` → **44행 조회**, `update ... where false` → **`42501 permission denied for table listings`**(쓰기 차단). `where false`로 데이터 무변경 보장.

### Completion Notes List

- **AC1(앱+OpenAPI) ✅** — `api/` FastAPI 스캐폴딩 완료. `POST /ai/search`(인증 필수 stub) + `GET /health` + 자동 `/docs`·`/openapi.json` 노출.
- **AC2(읽기전용 롤 NFR2) ✅** — `0006_readonly_role` 적용(파일 + Supabase MCP). **결정적 함정 회피**: `listings` RLS가 `to authenticated`라 별도 롤은 0건만 보이는 문제를, `ai_readonly`용 permissive SELECT 정책(`using(true)`)으로 해결 → 44행 가시 + 쓰기 거부 확인. FR11(sold 비노출)은 RLS가 아닌 호출부 쿼리(4.3+) 책임임을 코드 주석·마이그레이션에 명시.
- **AC3(JWT 401) ✅** — `auth.py`의 `get_current_user`(HTTPBearer, auto_error=False)가 미인증/형식오류를 401로 거절. 검증 방식 **A(supabase `auth.get_user`)** 채택 — 추가 비밀값 불필요(SUPABASE_URL+ANON_KEY만), 미인증 경로는 네트워크 호출 전 401이라 비밀값 없이도 동작·테스트 가능.
- **연결 방식 = Session 풀러 확정** — 사용자 검토 후 `DATABASE_URL`은 Session pooler(:5432)로 고정(`SET ROLE` 세션 유지·IPv4·psycopg 기본 동작). 코드·env·스토리에 반영.
- **의존성 그룹 분리(설계 결정)** — `pyproject.toml`에서 AI 스택(langgraph·langchain-google-genai·pgvector)을 `optional-dependencies.ai`로 분리. 4.1은 토대만이라 core+dev만 설치(`pip install -e ".[dev]"`), AI 라이브러리는 4.2~4.5에서 첫 사용 시 `.[ai]` 설치. 미사용 무거운 의존성을 4.1에 끌어들이지 않으면서 환경 스펙은 단일 출처로 선언.
- **범위 준수** — `graph/*`·`db/sql_guard.py`·`embeddings.py`는 만들지 않음(후속 스토리). stub은 DB·LLM 미접근(AC1/AC3 검증이 DB 가용성에 의존하지 않게 분리).
- **사용자 직접 처리 필요(차단 아님)** — `api/.env`에 `SUPABASE_URL`/`SUPABASE_ANON_KEY`(유효 토큰 경로·라이브 검증용), `DATABASE_URL`(Session pooler 문자열) 입력 시 `test_readonly` skip이 풀리고 앱→DB 읽기전용 경로가 실동작.

### File List

**신규 (api/ — 레포 첫 Python 백엔드)**
- `api/pyproject.toml`
- `api/.env.example`
- `api/app/__init__.py`
- `api/app/config.py`
- `api/app/main.py`
- `api/app/auth.py`
- `api/app/schemas/__init__.py`
- `api/app/schemas/ai.py`
- `api/app/routers/__init__.py`
- `api/app/routers/ai.py`
- `api/app/db/__init__.py`
- `api/app/db/readonly.py`
- `api/tests/__init__.py`
- `api/tests/test_health.py`
- `api/tests/test_auth.py`
- `api/tests/test_readonly.py`
- `supabase/migrations/0006_readonly_role.sql`

**수정**
- `.env.example` (루트 — api 섹션에 `DATABASE_URL` 추가)
- `_bmad-output/implementation-artifacts/4-1-api-스캐폴딩-읽기전용-롤-jwt-검증.md` (Dev Notes 연결방식 확정 + 본 기록)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (4-1 상태 전이, epic-4 in-progress)

> DB 변경: Supabase 프로젝트(`psrnsasxpkpwqdukjdmt`)에 `0006_readonly_role` 마이그레이션 적용됨(파일 + 원격 동시).

## Change Log

| 일자 | 변경 | 비고 |
|---|---|---|
| 2026-06-21 | Story 4.1 구현 — FastAPI `api/` 스캐폴딩 + `0006_readonly_role` + JWT 검증(401) | 7 passed/1 skipped, 라이브 HTTP·DB(MCP) 검증, Status → review |
