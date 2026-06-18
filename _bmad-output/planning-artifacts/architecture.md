---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
lastStep: 8
status: 'complete'
completedAt: '2026-06-18'
inputDocuments:
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/prd.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/addendum.md
  - _bmad-output/planning-artifacts/prds/prd-bmad-encar-demo-2026-06-17/.decision-log.md
  - _bmad-output/planning-artifacts/product-brief-encar-demo-2026-06-16.md
  - _bmad-output/planning-artifacts/research/technical-ai-search-architecture-research-2026-06-16.md
  - docs/idea.md
workflowType: 'architecture'
project_name: 'bmad-encar-demo'
user_name: 'Dnjsg'
date: '2026-06-18'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements (FR 25개 / 6그룹):**
- F1 인증·계정(FR1~4): 이메일/비밀번호 가입 시 역할(구매자/판매자) 선택·고정, 역할별 접근 제어(RBAC), 관리자 계정 별도. → Supabase Auth + 역할 기반 권한이 모든 API/화면에 걸친 횡단 관심사.
- F2 매물 등록·관리(FR5~8): 16필드 매물 CRUD, 본인 매물만 수정/삭제, 즉시 노출, "구매 완료"→판매완료 상태 전환. → 소유권 기반 인가 + 상태 머신.
- F3 매물 탐색(FR9~11): 키워드/필터 검색, 상세 조회, **판매완료 전 경로 비노출(FR11) = 단일 데이터 규칙**.
- F4 AI 검색 어시스턴트(FR12~18, 핵심): 라우터 3분류 → 경로 A(Text-to-SQL) / 경로 B(문서 RAG) / 가드(C), 자연어+매물카드 응답, 0건 시 조건 완화 안내, 멀티턴(클라이언트 보관). → 시스템 최고 난도 영역.
- F5 문의 채팅(FR19~21): 채팅방 생성, 폴링 송수신, 메시지 DB 영속.
- F6 관리자(FR22~25): 회원/매물/거래내역/채팅 조회·삭제.

**Non-Functional Requirements:**
- NFR1 성능: AI 응답 수 초(Gemini 호출 1~2회), 채팅 폴링 3~5초.
- NFR2 보안·권한(아키텍처 강제 제약): Text-to-SQL은 **결정론적 안전장치** — ① 읽기 전용 DB 롤, ② 기본 LIMIT 강제, ③ 실행 전 쿼리 검증(SELECT 전용·테이블/컬럼 화이트리스트). RLS 적용 권장. 프롬프트 지시에만 의존 금지.
- NFR3 플랫폼: 반응형 웹(사용자·관리자) + Flutter 앱 공통 동작.
- NFR4 배포·확장: Vercel 단일 배포, 무상태 전제, Supabase에 상태 저장. 차선: 백엔드만 Cloud Run/Railway 분리.
- NFR5 데이터·프라이버시: 채팅 메시지 영속, AI 대화 미저장(클라이언트 보관).
- NFR6 비용: Gemini 무료 등급 · Vercel Hobby · Supabase 무료/저가 티어.

**Scale & Complexity:**
- Primary domain: 풀스택 (웹 2 + 모바일 1 클라이언트 / FastAPI 단일 API / AI 백엔드)
- Complexity level: 중(medium) — 데모·경부하지만 2경로 RAG + 안전장치가 난도 상승.
- Estimated architectural components: 약 6 — ① 프론트(웹×2·Flutter) ② FastAPI 게이트웨이 ③ LangGraph AI 오케스트레이션 ④ Supabase(Postgres+pgvector+Auth) ⑤ 인증·RBAC ⑥ 폴링 채팅.

### Technical Constraints & Dependencies

- **모델·차원 고정:** 생성 `gemini-flash-latest`, 임베딩 `gemini-embedding-001`(출력 768차원) ↔ pgvector `vector(768)` **반드시 일치**(불일치 시 미동작).
- **Vercel 제약:** 함수 번들 500MB·실행 300초 한도, 무거운 라이브러리 미적재, Supabase 연결 풀링 필요.
- **무상태 전제:** AI 대화 전용 테이블 없음, 멀티턴 맥락은 클라이언트가 동봉.
- **LLM provider-agnostic:** LangGraph로 추후 모델 교체 가능성 유지.
- **RAG 코퍼스 의존:** 경로 B는 ① 매물 설명·옵션 텍스트 + ② 차량 상식·가이드 문서 두 코퍼스에 의존(문서 내용은 구현 단계 작성).

### Cross-Cutting Concerns Identified

1. **인증·인가(RBAC + 소유권):** 역할 분기 + 본인 매물만 수정/삭제(FR6) + 관리자 전권.
2. **AI 쿼리 안전장치(NFR2):** 읽기 전용 롤·LIMIT·화이트리스트 검증 — API·DB·AI 노드에 걸침.
3. **판매완료 비노출(FR11):** SQL·RAG·필터·목록·상세 전 경로 공통 단일 규칙.
4. **임베딩 차원 정합(768):** 임베딩 생성·저장·검색 전 구간 일관 유지.
5. **무상태/멀티턴 경계:** 클라이언트 보관 vs DB 영속(채팅) 경계 명확화.
6. **3-클라이언트 일관성:** 웹×2·Flutter가 동일 API 계약을 공유.

## Starter Template Evaluation

### Primary Technology Domain

폴리글랏 풀스택 — Next.js 웹 ×2(사용자·관리자) + Flutter 모바일 앱 + Python(FastAPI+LangGraph) AI 백엔드 + Supabase. 단일 스타터로 전체를 커버하는 템플릿은 없음.

### Starter Options Considered (현재 버전, 2026-06 웹 검증)

- **단일 통합 스타터(T3/RedwoodJS 등):** ❌ JS 풀스택 전제 → Flutter·Python(LangGraph) 미포함으로 부적합.
- **Turborepo 모노레포:** 가능하나 JS 중심 캐싱 도구. Python·Flutter 파트 이점 적고 데모엔 과함 → 보류.
- **파트별 공식 스캐폴딩 + 경량 폴더 모노레포:** ✅ 채택. 각 파트는 공식 CLI로 생성, 한 저장소(현 git repo)에 폴더로 공존. 학습·데모에 가장 단순.

### Selected Approach: 경량 폴더 모노레포 + 공식 스캐폴딩

**Rationale:** 스택이 PRD에서 확정됨 → "무엇을 쓰나"가 아니라 "공식 도구로 최신 버전 부트스트랩"이 목표. 빌드 도구 모노레포(Turborepo 등) 없이 폴더 분리만으로 충분(경부하·데모). 각 파트 독립 실행/배포 가능.

**검증된 현재 버전(2026-06):**
- **Next.js 16.2.7** — Turbopack 기본 번들러, `create-next-app` AI-ready 스캐폴드
- **Flutter 3.44.0** (stable, 2026-05-18)
- **FastAPI 0.137.1**
- **LangGraph 1.2.4** / **langgraph-cli 0.4.28** (Python ≥3.10)

**Initialization Commands (구현 첫 스토리로 실행):**

```bash
# 1) 사용자용 웹
npx create-next-app@latest web-user --typescript --tailwind --eslint --app --src-dir --turbopack

# 2) 관리자용 웹 (별도 앱; step-06에서 통합 여부 재검토)
npx create-next-app@latest web-admin --typescript --tailwind --eslint --app --src-dir --turbopack

# 3) 모바일 앱 (Flutter 3.44.0)
flutter create --org com.encardemo app

# 4) AI 백엔드 (FastAPI + LangGraph) — Python 가상환경 후
pip install "fastapi==0.137.1" "uvicorn[standard]" "langgraph==1.2.4" \
            "langgraph-cli[inmem]==0.4.28" "langchain-google-genai" \
            "supabase" "pgvector" "psycopg[binary]"
```

**Architectural Decisions Provided by Starter:**

- **Language & Runtime:** TypeScript(웹), Dart(앱), Python ≥3.10(API). Next.js는 App Router + `src/` 구조.
- **Styling Solution:** Tailwind CSS(웹 2종 공통). Flutter는 기본 Material 위젯.
- **Build Tooling:** Turbopack(Next.js 기본), Flutter 빌드 체인, uvicorn(개발 서버).
- **Testing Framework:** Next.js 기본(없음 → 추후 추가), Flutter `flutter_test` 내장, Python `pytest`(추가).
- **Code Organization:** 폴더 모노레포 — `web-user/ web-admin/ app/ api/` 한 저장소 공존.
- **Development Experience:** Next.js HMR(Turbopack), Flutter hot reload, langgraph-cli로 그래프 시각 디버깅(LangGraph Studio).

**Note:** 위 초기화 명령 실행을 **구현 단계의 첫 스토리**로 삼는다. 버전은 착수 시점에 재확인 권장.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (구현 차단 요소 — 확정):**
- 통신 토폴로지: 클라이언트가 Supabase 직접 접근(인증·CRUD·채팅, RLS 보호), FastAPI는 **AI 검색 전용**.
- AI 검색 안전장치: 읽기 전용 DB 롤 + LIMIT 강제 + SELECT 화이트리스트 검증(NFR2).
- 데이터 모델: 단순 스키마 6테이블(아래).

**Important Decisions (구조 형성):**
- 웹: Next.js App Router + Server Components + **TanStack Query 5.101.0**(폴링·AI 채팅 클라이언트 상태).
- 앱: Flutter + **flutter_riverpod ^3.3.2** + `supabase_flutter` SDK.
- AI 백엔드 배포: Vercel Python 서버리스 우선, 번들 500MB 초과 시 Cloud Run 전환.

**Deferred (Post-MVP):**
- 캐싱·레이트리밋·고급 모니터링·CI 테스트 자동화 — 데모 경부하라 보류(Vercel 로그 수준).

### Data Architecture

**DB:** Supabase(PostgreSQL) + pgvector. 단순 스키마 원칙(점진 확장, 마이그레이션으로 추적).

**테이블(초기 6개):**
- `profiles` — `id`(auth.users 참조), `role`(buyer/seller/admin), `status`(active/suspended).
- `listings` — 매물 16필드(FR5) + `seller_id`, `status`(on_sale/sold), `embedding vector(768)`(코퍼스① 설명·옵션 임베딩), `created_at`. 상세 컬럼 정의는 아래 표 참조.
- `chat_rooms` — `listing_id`, `buyer_id`, `seller_id`, `created_at`.
- `chat_messages` — `room_id`, `sender_id`, `body`, `created_at`.
- `guide_documents` — `title`, `content`, `embedding vector(768)`(코퍼스② 차량 상식·가이드).
- (auth.users는 Supabase Auth 관리)

**`listings` 컬럼 정의 (확정):** FR5 필드를 정의. 차종(`body_type`)은 Encar·K-Car 등 국내 중고차 앱 분류를 따르는 **단일 컬럼**(차급·차형을 합친 관행 분류). 고정 목록은 `text + CHECK`, 숫자 범위는 `CHECK`. 아래 영문 컬럼명을 DB·JSON·코드·Text-to-SQL 화이트리스트 전 구간에서 동일하게 사용(drift 금지).

```sql
-- supabase/migrations/0002_listings.sql (구현 단계에서 생성)
-- 단위: price=원(KRW), mileage=km, displacement=cc
create table listings (
  -- 시스템 컬럼 (FR5 외)
  id            uuid primary key default gen_random_uuid(),
  seller_id     uuid not null references profiles(id) on delete cascade,
  status        text not null default 'on_sale' check (status in ('on_sale','sold')),
  embedding     vector(768),
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),

  -- FR5 16필드
  manufacturer  text not null check (manufacturer in (        -- 제조사(고정)
                  '현대','기아','제네시스','쉐보레','르노코리아','KG모빌리티',
                  'BMW','벤츠','아우디','폭스바겐','토요타','혼다','렉서스','테슬라','기타')),
  model         text not null,                                 -- 모델(자유 입력)
  body_type     text not null check (body_type in (            -- 차종(Encar/K-Car 분류)
                  '경차','소형차','준중형차','중형차','대형차','스포츠카',
                  'SUV','RV','경승합차','승합차','화물차','기타')),
  year          int  not null check (year between 1990 and 2027),
  price         int  not null check (price >= 0),              -- 원
  mileage       int  not null check (mileage >= 0),            -- km
  color         text not null check (color in (
                  '흰색','검정','회색','은색','파랑','빨강','갈색','녹색','기타')),
  fuel          text not null check (fuel in (
                  '가솔린','디젤','하이브리드','전기','LPG')),
  transmission  text not null check (transmission in ('자동','수동')),
  displacement  int  not null check (displacement >= 0),       -- cc, 전기차 0 허용
  seats         int  not null check (seats between 2 and 11),
  region        text not null check (region in (
                  '서울','부산','대구','인천','광주','대전','울산','세종',
                  '경기','강원','충북','충남','전북','전남','경북','경남','제주')),
  accident_free boolean not null default true,                 -- 무사고 여부
  options       text[] default '{}',                           -- 코퍼스① 임베딩 대상
  description   text,                                          -- 코퍼스① 임베딩 대상
  photos        text[] default '{}'                            -- URL 배열, 대표=photos[0]
);
```

> **정합성 주의:** 위 CHECK 목록값은 **UI 드롭다운 · AI Text-to-SQL 허용값 · 데모 시드 데이터 · 질의셋(OI5)**과 동일해야 한다. `year` 상한(2027)은 CHECK 정적값이라 연도 경과 시 마이그레이션으로 상향한다.

**검증 전략:** API는 Pydantic(LangGraph 구조화 출력 포함), 웹은 Zod/타입, Supabase 자동 생성 타입 활용.
**마이그레이션:** Supabase 마이그레이션으로 스키마 버전 관리.
**벡터 인덱스:** HNSW 권장(OI3) — 임베딩 차원 768 고정, 모델↔컬럼 일치 강제.

### Authentication & Security

- **인증:** Supabase Auth(이메일/비밀번호). 가입 시 역할 선택 → `profiles.role` 고정.
- **인가:** RLS 정책으로 역할·소유권 강제 — 판매자는 본인 매물만 수정/삭제(FR6), 구매자/판매자/관리자 분기(FR3), 관리자 전권.
- **판매완료 비노출(FR11):** RLS·쿼리 공통으로 `status='sold'` 구매자 화면 제외.
- **AI 경로 안전장치(NFR2):** FastAPI AI 엔드포인트는 **전용 읽기 전용 Postgres 롤**로 DB 접근(클라이언트 RLS 경로와 분리). Text-to-SQL은 SELECT 전용 + 기본 LIMIT + 테이블/컬럼 화이트리스트 + 실행 전 검증. AI 호출 시 Supabase JWT 검증으로 로그인 구매자만 허용.

### API & Communication Patterns

- **클라이언트 CRUD/채팅:** Supabase SDK 직접 호출(REST/RPC), RLS로 보호.
- **AI 검색:** FastAPI REST 엔드포인트(예: `POST /ai/search`) — 자연어 질의 + 클라이언트 보관 멀티턴 맥락 동봉(무상태). 자동 OpenAPI 문서.
- **채팅 폴링:** 클라이언트가 3~5초 간격으로 Supabase에서 메시지 조회(NFR1).
- **에러 처리 표준:** 일관된 JSON 에러 형태(코드·메시지). AI 0건 → 조건 완화 안내(FR17).

### Frontend Architecture

- **웹(사용자·관리자):** Next.js 16 App Router, Server Components 기본, 클라이언트 갱신(폴링·AI 채팅)은 TanStack Query, 스타일 Tailwind. 전역 상태 라이브러리(Redux) 불필요.
- **앱:** Flutter 3.44, Riverpod 상태관리, `supabase_flutter`로 인증·CRUD·채팅, AI 호출은 HTTP 클라이언트(dio/http).
- **3-클라이언트 일관성:** AI 검색 응답 스키마(자연어+매물카드)를 공통 계약으로 고정.

### Infrastructure & Deployment

- **호스팅:** 웹×2 + FastAPI → Vercel(우선). AI 번들 초과 시 백엔드만 Cloud Run 분리. 앱은 스토어 외 데모(에뮬레이터/디바이스).
- **환경설정:** `.env`/Vercel 환경변수로 Gemini 키·Supabase URL/키·`GEMINI_EMBEDDING_DIM=768` 주입.
- **연결 풀링:** Supabase 풀링 설정(무상태 서버리스 대응).
- **CI/CD·모니터링:** 데모 수준 — Vercel git 연동 배포 + 기본 로그. 고급 파이프라인 보류.

### Decision Impact Analysis

**구현 순서(권장):**
1. 모노레포 스캐폴딩(step-03 명령) + Supabase 프로젝트·스키마 마이그레이션.
2. 인증·RLS·역할(profiles) → 매물 CRUD → 필터 검색.
3. 폴링 채팅.
4. AI 백엔드(LangGraph 라우터 → 경로 A/B/가드) + 읽기 전용 롤 + 임베딩 적재.
5. 관리자 기능.

**교차 의존성:**
- 토폴로지 선택 → AI 엔드포인트는 별도 읽기 전용 롤 필요 + JWT 검증 공유.
- 임베딩 차원(768) → 임베딩 생성·저장·검색 전 구간 일치.
- FR11(판매완료 비노출) → RLS·Text-to-SQL·문서 RAG 결과 필터 모두에 반영.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**핵심 충돌 지점:** 폴리글랏(Postgres·Python·TS·Dart) 경계의 표기법, 응답·에러 포맷, 파일·상태 네이밍, **수치 필드 단위** 등 ~7개 영역.

### Naming Patterns

**Database (Postgres/Supabase):**
- 테이블: 복수형 `snake_case` — `profiles`, `listings`, `chat_rooms`, `chat_messages`, `guide_documents`.
- 컬럼: `snake_case` (`seller_id`, `created_at`). PK는 `id`(uuid). FK는 `<엔티티>_id`.
- 인덱스: `idx_<table>_<column>`. 타임스탬프: `created_at` / `updated_at`(UTC).

**API (FastAPI AI 엔드포인트 + Supabase):**
- REST 경로 복수 명사, 경로 파라미터 `{id}`. AI 엔드포인트: `POST /ai/search`.
- **JSON 페이로드는 `snake_case`로 통일**(DB·Pydantic과 일치, 변환 불필요).

**Code:**
- TS(웹): 컴포넌트 파일 `PascalCase.tsx`(`ListingCard.tsx`), 함수·변수 `camelCase`.
- Dart(앱): 파일 `snake_case.dart`(`listing_card.dart`), 클래스 `PascalCase`.
- Python(API): 모듈·함수 `snake_case`, 클래스 `PascalCase`.

### Structure Patterns

- **웹:** `src/app`(라우트), `src/components`(기능별 폴더), `src/lib`(supabase 클라이언트·유틸·쿼리). 테스트는 `*.test.ts` 코로케이션.
- **앱:** `lib/features/<기능>/`, `lib/core/`, 테스트는 `test/`.
- **API:** `app/graph/`(LangGraph 노드), `app/routers/`, `app/schemas/`(Pydantic), `app/db/`. 테스트는 `tests/`(pytest).
- 컴포넌트/모듈은 **타입별이 아니라 기능별(feature-based)**로 묶는다.

### Format Patterns

- **AI 응답(공통 계약):** `{ "answer": string, "listings": ListingCard[] }`. 0건이면 `listings: []` + `answer`에 조건 완화 안내(FR17).
- **ListingCard 필드:** `id, manufacturer, model, year, price, mileage, region, thumbnail_url`(snake_case).
- **에러 포맷:** `{ "error": { "code": string, "message": string } }`. HTTP 상태코드 정확히 사용(400/401/403/404/422/500).
- **날짜:** ISO 8601 문자열(UTC). **불리언:** `true/false`. **null:** 빈 문자열 대신 명시적 `null`.

### Unit & Measurement Rules (단위·측정 규칙)

전 구간(저장·입력·검색·AI Text-to-SQL·표시)에서 수치 필드 단위를 **명시적으로 고정**한다. 단위 미명시는 AI 검색 쿼리와 실제 데이터 불일치를 유발하므로 금지.

- **`mileage` (주행거리):** **정수 킬로미터(km)** 로 저장. 입력·검색·AI 쿼리 모두 km 기준. 표시 포맷은 천단위 구분 + `km`(예: `103,000km`), 자연어 답변은 "만km" 허용. **mile/마일 절대 사용 금지.**
- **`price` (가격):** 정수 **원(KRW)**. 표시 시 천단위 구분(예: `29,800,000원`), 자연어는 "만원/천만원" 허용.
- **`displacement` (배기량):** 정수 **cc**. **`year` (연식):** 정수 4자리 연도. **`mileage`/`price`/`displacement`는 음수 불가.**
- AI Text-to-SQL 변환 시 자연어 단위("10만km", "3천만원")를 저장 단위(km·원 정수)로 정규화해 비교한다.

### Communication Patterns

- **TanStack Query 키:** 배열 컨벤션 — `['listings', filters]`, `['chat', roomId]`. 폴링은 `refetchInterval`(3~5초 상수).
- **Riverpod:** 프로바이더 명 `<name>Provider`, 비동기는 `AsyncValue`로 로딩/에러/데이터 표현.
- **상태 업데이트:** 항상 불변(immutable) 갱신. 직접 변이 금지.

### Process Patterns

- **에러 처리:** 사용자 노출 메시지는 한국어, 내부 로그는 코드·원인. 웹은 error boundary, 앱은 `AsyncValue.error`.
- **로딩 상태:** 전역 아닌 지역(local) 우선 — TanStack Query `isLoading`, Riverpod `AsyncLoading`.
- **인증 흐름:** 클라이언트는 Supabase 세션 토큰 보관 → AI 호출 시 `Authorization: Bearer <jwt>` 동봉.

### Enforcement Guidelines

**모든 구현 에이전트는 반드시:**
- 통신선(DB 컬럼·JSON 필드)에 `snake_case`만 사용한다.
- AI 응답·에러를 위 공통 포맷으로 반환한다.
- 수치 필드를 **위 단위 규칙(km·원·cc)대로** 저장·표시한다.
- 판매완료(`status='sold'`) 매물을 구매자 경로에 노출하지 않는다(FR11).

**도구로 강제:** 웹 ESLint+Prettier, 앱 `flutter_lints`+`dart analyze`, API `ruff`+`black`.

### Pattern Examples

- ✅ `listings.seller_id` → JSON `"seller_id"` → TS 코드 내부 `sellerId`로 매핑.
- ❌ JSON에 `sellerId` 직접 노출(Supabase 반환과 불일치 → 매핑 버그).
- ✅ 주행거리: 저장 `103000`(km 정수) → 표시 `103,000km` → 자연어 "약 10만km".
- ❌ 주행거리를 단위 없이 `103000`만 표시하거나 mile로 저장.
- ✅ 에러: `{ "error": { "code": "LISTING_NOT_FOUND", "message": "매물을 찾을 수 없습니다." } }`.

## Project Structure & Boundaries

> **관리자 페이지 결정:** 별도 앱(`web-admin`) 대신 **단일 `web/` 앱 + Next.js 라우트 그룹 `(user)`/`(admin)` + RBAC**로 통합한다. 보안은 Supabase RLS(서버 측)가 강제하므로 앱 분리는 보안 이득이 없고, 데모에선 스캐폴딩·공유 코드·배포가 단순해짐. (step-03의 `web-user`+`web-admin` 2앱 초기화를 본 결정이 대체)

### Complete Project Directory Structure

```
bmad-encar-demo/                  # 경량 폴더 모노레포 (단일 git repo)
├── README.md
├── .gitignore
├── .env.example                  # 공통 환경변수 예시 (Gemini·Supabase 키)
├── docs/idea.md
├── _bmad-output/                 # 기획·아키텍처 산출물
├── scripts/check-embedding-dim.ps1
│
├── supabase/                     # DB 정의 (단일 출처)
│   ├── migrations/
│   │   ├── 0001_profiles.sql            # FR1~4 역할·상태
│   │   ├── 0002_listings.sql            # FR5 16필드 + status + embedding vector(768)
│   │   ├── 0003_chat.sql                # FR19~21 rooms·messages
│   │   ├── 0004_guide_documents.sql     # FR15 코퍼스② + pgvector HNSW
│   │   ├── 0005_rls_policies.sql        # FR3·6·11 RLS (관리자 role=admin 정책 포함)
│   │   └── 0006_readonly_role.sql       # NFR2 AI 전용 읽기 전용 롤
│   ├── seed.sql                  # 관리자 계정·샘플 매물·가이드 문서(OI6)
│   └── config.toml
│
├── web/                          # Next.js 16 — 사용자+관리자 단일 반응형 웹
│   ├── package.json · next.config.ts · tailwind.config.ts · tsconfig.json
│   ├── .env.local
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── (auth)/login · signup           # FR1·2
│   │   │   ├── (user)/                          # 사용자 영역 (라우트 그룹)
│   │   │   │   ├── page.tsx                     # 홈/매물 목록
│   │   │   │   ├── search/page.tsx              # FR9 필터 검색
│   │   │   │   ├── listings/[id]/page.tsx       # FR10 상세
│   │   │   │   ├── ai/page.tsx                  # FR12~18 AI 채팅
│   │   │   │   ├── sell/                        # FR5~8 판매자 등록·관리
│   │   │   │   └── chat/[roomId]/page.tsx       # FR19~21 문의 채팅
│   │   │   └── (admin)/admin/                   # 관리자 영역 (role=admin 전용)
│   │   │       ├── members/page.tsx             # FR22 회원 조회·정지/삭제
│   │   │       ├── listings/page.tsx            # FR23 전체 매물·삭제
│   │   │       ├── transactions/page.tsx        # FR24 거래내역
│   │   │       └── chats/page.tsx               # FR25 채팅 열람·삭제
│   │   ├── components/{ui, listings/ListingCard.tsx, ai/ChatAssistant.tsx, chat/, admin/}
│   │   ├── lib/
│   │   │   ├── supabase/{client.ts, server.ts} # 직접 접근
│   │   │   ├── api/aiSearch.ts                 # FastAPI /ai/search 호출
│   │   │   ├── queries/                        # TanStack Query 훅(폴링 포함)
│   │   │   └── format.ts                       # km·원 표시 포맷(단위 규칙)
│   │   ├── types/database.ts                   # supabase 생성 타입
│   │   └── middleware.ts                        # 세션 가드 + /admin은 role=admin만 통과
│   └── tests/
│
├── app/                          # Flutter 3.44 — 모바일 앱 (사용자용)
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── main.dart
│   │   ├── core/{supabase, router, theme, format}/         # 단위 포맷 공통
│   │   └── features/{auth, listings, ai_search, chat}/     # Riverpod providers
│   └── test/
│
└── api/                          # FastAPI + LangGraph — AI 검색 전용
    ├── pyproject.toml · .env.example
    ├── app/
    │   ├── main.py                              # FastAPI 앱
    │   ├── routers/ai.py                        # POST /ai/search
    │   ├── auth.py                              # Supabase JWT 검증
    │   ├── graph/
    │   │   ├── router_node.py                   # FR13 의도 분류 A/B/C
    │   │   ├── sql_rag_node.py                  # FR14 경로 A Text-to-SQL
    │   │   ├── doc_rag_node.py                  # FR15 경로 B 문서 RAG
    │   │   ├── guard_node.py                    # FR16 경로 C 가드
    │   │   └── answer_node.py                   # FR17 답변+매물카드
    │   ├── schemas/                             # Pydantic 요청·응답·라우터 출력
    │   ├── db/{readonly.py, sql_guard.py}       # NFR2 읽기전용 롤·SELECT 검증
    │   └── embeddings.py                        # Gemini 768 임베딩
    └── tests/                                   # pytest
```

### Architectural Boundaries

- **API 경계:** ① Supabase(인증·CRUD·채팅, RLS 직접 접근) ② FastAPI `/ai/search`(AI 전용, 읽기 전용 롤). 두 경계는 분리되며 AI는 쓰기 권한 없음.
- **사용자/관리자 경계:** 단일 `web/` 앱 내 라우트 그룹 — `(user)` vs `(admin)/admin`. `middleware.ts`가 `/admin` 접근을 `role=admin`으로 제한(1차), RLS가 서버에서 재차 강제(2차 방어선).
- **컴포넌트 경계:** 웹은 Server Component(조회)/Client Component(폴링·채팅, TanStack Query). 앱은 feature별 Riverpod provider. AI 채팅 멀티턴 맥락은 클라이언트 상태에만 존재(무상태).
- **데이터 경계:** 스키마 단일 출처 = `supabase/migrations/`. 클라이언트는 RLS 경유, AI는 읽기 전용 롤 경유. 임베딩(vector 768)은 `listings`·`guide_documents`에 위치.

### Requirements to Structure Mapping

- **인증·계정(FR1~4):** `supabase/0001·0005` + `web/(auth)` / `app/features/auth` + `middleware.ts`.
- **매물 등록·관리(FR5~8):** `0002` + `web/(user)/sell` + `app/features/listings`.
- **매물 탐색(FR9~11):** `(user)/search`·`listings/[id]` + `0005`(FR11 RLS).
- **AI 검색(FR12~18):** `api/app/graph/*` + 클라 `ai/` 화면 + `api/aiSearch.ts`.
- **문의 채팅(FR19~21):** `0003` + `(user)/chat/[roomId]` + `features/chat`(폴링).
- **관리자(FR22~25):** `web/(admin)/admin/*` (role=admin 보호).

### Cross-Cutting Concerns

- **인증/RBAC:** Supabase Auth + `profiles.role` + RLS(`0005`) + `middleware.ts`(/admin 보호) + JWT 검증(`api/auth.py`).
- **AI 안전장치(NFR2):** `0006_readonly_role` + `api/db/sql_guard.py`.
- **단위 규칙:** `web/lib/format.ts`, `app/core/format`, `api` 정규화 — km·원 통일.
- **판매완료 비노출(FR11):** RLS + `sql_guard` + 문서 RAG 결과 필터 공통.

### Integration Points & Data Flow

- **내부 통신:** 클라 → Supabase(SDK). 클라 → FastAPI(`POST /ai/search`, JWT 동봉).
- **외부 연동:** Gemini API(생성·임베딩), Supabase(Auth·Postgres·pgvector).
- **AI 데이터 흐름:** 질의+맥락 → 라우터 → (A SQL / B 문서RAG / C 가드) → 읽기전용 DB 조회 → answer_node → `{answer, listings[]}` → 클라 렌더.

### Deployment Structure

- **Vercel:** `web`(사용자+관리자 단일 앱) + `api`(Python 서버리스) = 프로젝트 2개. 번들 500MB 초과 시 `api`만 Cloud Run.
- **Supabase:** 호스팅 Postgres+pgvector+Auth. 마이그레이션으로 스키마 적용.
- **앱:** 스토어 외 데모(에뮬레이터/디바이스), `.env`로 API·Supabase 주소 주입.

## Architecture Validation Results

### Coherence Validation ✅

- **결정 호환성:** Next.js 16.2.7 · Flutter 3.44 · FastAPI 0.137.1 · LangGraph 1.2.4 · Supabase(pgvector 768) · Gemini — 상호 충돌 없음. "Supabase 직접 + FastAPI AI 전용" 토폴로지가 무상태·Vercel 제약과 정합.
- **패턴 일관성:** snake_case 통신선 규칙이 Postgres·Pydantic·Supabase 반환과 일치. 단위 규칙(km·원·cc)이 저장·검색·표시·Text-to-SQL 전 구간 적용. TanStack Query/Riverpod 상태 패턴이 폴링·AI와 정합.
- **구조 정합:** `web`(라우트 그룹)·`app`·`api`·`supabase` 경계가 결정·패턴을 그대로 수용. 단일 스키마 출처(migrations)와 RLS/읽기전용 롤 분리가 명확.

### Requirements Coverage Validation ✅

- **기능 요구사항(FR1~25):** 전부 구조에 매핑됨 — 인증(FR1~4)·매물(FR5~8)·탐색(FR9~11)·AI(FR12~18)·채팅(FR19~21)·관리자(FR22~25). FR11(판매완료 비노출)은 RLS+sql_guard+문서RAG 필터 3중 적용.
- **비기능(NFR1~6):** 성능(폴링·Gemini 1~2회), 보안(읽기전용 롤·SELECT 검증·RLS), 플랫폼(반응형 웹+Flutter), 배포(Vercel+Cloud Run 차선), 데이터(채팅 영속·AI 미저장), 비용(무료 티어) 모두 반영.

### Implementation Readiness Validation ✅

- **결정 완전성:** 핵심 결정·라이브러리 버전 고정(2026-06 검증). 토폴로지·배포 명시.
- **구조 완전성:** 파일·디렉터리·경계·FR 매핑 구체화(플레이스홀더 아님).
- **패턴 완전성:** 네이밍·구조·포맷·단위·통신·프로세스 + 강제 도구(ESLint/flutter_lints/ruff)까지.

### Gap Analysis Results

- **Critical(차단):** 없음.
- **Important(구현 시점 결정):**
  - **OI2** — Text-to-SQL 구현 방식(SQL Agent vs 제약된 Chain) 및 라우터 구조화 출력(Pydantic 스키마) 최종 선택. 아키텍처는 안전장치·패턴을 규정했고, 세부 구현 방식은 첫 AI 스토리에서 확정.
  - **OI5** — 가드 합격 판정용 데모 질의셋(구조형/질적/회색/무관) 작성 — 테스트 근거.
  - **OI6** — 문서 기반 RAG 코퍼스(차량 상식·가이드) 실제 내용 작성.
- **Nice-to-Have:** UX 명세(선택, 건너뜀) — 화면은 구조로 정의됨. 추후 `bmad-ux`로 보강 가능.

### Validation Issues Addressed

- 주행거리 단위 미명시 → **단위·측정 규칙**으로 km 고정(검증 중 발견·반영).
- 관리자 앱 분리 과투자 → 단일 앱 `(admin)` 라우트+RBAC로 단순화(보안은 RLS가 동등 보장).

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY FOR IMPLEMENTATION (16/16 체크, Critical Gap 없음)
**Confidence Level:** high

**Key Strengths:**
- AI 안전장치(NFR2)를 결정론적으로 명문화(읽기전용 롤·SELECT 검증·LIMIT).
- 폴리글랏 경계 일관성 규칙(snake_case·단위)으로 매핑 버그 예방.
- 데모 규모에 맞춘 단순 토폴로지(과투자 제거).

**Areas for Future Enhancement:**
- OI2/OI5/OI6(구현 시점 처리), UX 명세, 캐싱·레이트리밋·모니터링(Post-MVP).

### Implementation Handoff

**AI Agent Guidelines:**
- 모든 아키텍처 결정을 문서 그대로 따른다.
- 일관성 규칙(snake_case·단위·응답/에러 포맷)을 전 컴포넌트에 적용한다.
- 프로젝트 구조·경계를 준수하고, 아키텍처 질문은 본 문서를 참조한다.

**First Implementation Priority:**
모노레포 스캐폴딩 + Supabase 마이그레이션 실행(step-03 명령). 이후: 인증·RLS → 매물 CRUD → 검색 → 채팅 → AI 백엔드 → 관리자.
