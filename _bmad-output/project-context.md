---
project_name: 'bmad-encar-demo'
user_name: 'Dnjsg'
date: '2026-07-11'
sections_completed: ['technology_stack', 'critical_implementation_rules', 'testing_rules', 'version_gotchas']
existing_patterns_found: 12
status: 'complete'
rule_count: 13
optimized_for_llm: true
---

# Project Context for AI Agents

_이 파일은 이 프로젝트에서 코드를 구현할 때 AI 에이전트가 반드시 따라야 할 핵심 규칙·패턴을 담는다. LLM이 놓치기 쉬운 "당연하지 않은" 세부에 집중한다._

_단일 출처: 값이 바뀌면 `docs/conventions.md`(공유 계약)를 먼저 고치고 코드에 반영한다._

---

## Technology Stack & Versions

**폴리글랏 모노레포** — 4개 파트가 한 레포에 공존:

| 파트 | 스택 | 핵심 버전 |
|---|---|---|
| `web/` | Next.js **App Router** + React + TypeScript(strict) + Tailwind | next 16.2.9 · react 19.2.4 · tailwindcss v4 · TS 5 |
| `api/` | FastAPI + LangGraph (AI 검색 전용 백엔드) | fastapi 0.137.1 · langgraph 1.2.4 · Python ≥3.10 · psycopg[binary] · langchain-google-genai |
| `app/` | Flutter + Riverpod | Dart SDK ^3.12.2 · supabase_flutter 2.15 · flutter_riverpod 3.3 · http 1.6 |
| `supabase/` | Postgres + pgvector + RLS | 번호순 마이그레이션 `0001~0009` |

- **배포:** web=Vercel, api=Cloud Run(서울, 운영 `encar-ai-api`·개발 `encar-ai-api-dev`), app=수동. (Vercel은 api 480MB>250MB로 폐기됨 — api는 반드시 Cloud Run.)
- **AI 모델:** 생성 `gemini-3.1-flash-lite`(고정) · 임베딩 `gemini-embedding-001`.
- **⚠️ 최신버전 함정(옛 문법 금지):** Tailwind **v4**는 `tailwind.config.js`가 아니라 CSS `@theme` 기반(CSS-first) 설정. React **19**/Next **16 App Router**는 서버 컴포넌트가 기본이며 `'use client'`는 필요한 곳에만. AI가 옛 버전 문법을 쓰지 않도록 주의.

---

## Critical Implementation Rules

### 1. 공유 계약은 `docs/conventions.md`가 단일 출처
web·app·api·db 경계를 가로지르는 값은 전부 여기 정의. 코드보다 이 문서를 먼저 고친다.

### 2. 임베딩 차원 `768` 전 구간 고정
`gemini-embedding-001`(출력 768) ↔ pgvector `vector(768)` ↔ 생성·저장·검색 전부 일치해야 AI 검색이 동작. `GEMINI_EMBEDDING_DIM=768`(api) = `web/src/lib/constants.ts`의 `EMBEDDING_DIM`.

### 3. 통신선(wire)은 `snake_case`, 코드 내부는 언어 관례
- **DB 컬럼·JSON 페이로드는 모두 snake_case** (`seller_id`, `body_type`, `created_at`).
- 코드 내부: TS/Dart는 `sellerId`로 매핑, Python은 그대로. ❌ JSON에 `sellerId` 직접 노출 금지(Supabase 반환과 불일치 → 매핑 버그).

### 4. 단위는 저장 단위로 고정, 단위 미명시 금지
`mileage`=정수 km(마일 금지) · `price`=정수 원(KRW, 음수 불가) · `displacement`=정수 cc(전기차 0 허용) · `year`=4자리 연도. AI Text-to-SQL은 자연어 단위("10만km","3천만원")를 저장 단위로 정규화해 비교.

### 5. 응답·에러 공통 포맷
- AI 검색 응답: `{ "answer": string, "listings": ListingCard[] }`. 0건이면 `listings: []` + `answer`에 완화 안내(FR17).
- `ListingCard`: `id, manufacturer, model, year, price, mileage, region` (**현재 사진/썸네일 필드 없음** — 이미지 기능 도입 시 이 계약부터 확장).
- 에러: `{ "error": { "code": string, "message": string } }`, message는 **한국어**, HTTP 상태코드 정확히(400/401/403/404/422/500). 날짜=ISO 8601(UTC), null은 빈 문자열 대신 명시적 `null`.

### 6. 보안은 RLS가 지킨다 — `service_role` 키 금지
- 클라이언트는 **anon key만** 사용, 접근 제어는 전적으로 RLS. `service_role` 키는 어디에도 두지 않는다(이 때문에 "완전 계정 삭제"는 미구현 — profiles 행만 삭제).
- **`GEMINI_API_KEY`는 오직 `api/.env`에만** (웹에 절대 안 넣음). web 브라우저 노출값은 `NEXT_PUBLIC_` 접두사 필수.
- env 누락은 `web/src/lib/supabase/env.ts`의 `getSupabaseEnv()`로 일원화(어떤 변수가 비었는지 한국어로 throw). `process.env.X!` 비-널 단언 금지.
- AI SQL은 읽기전용 롤(`0006_readonly_role`) + `api/app/db/sql_guard.py`(sqlparse 토큰 검증)로 이중 차단. LLM이 만든 SELECT만 통과.

### 7. 판매완료 비노출은 단일 규칙(FR11)
`status='sold'` 매물은 구매자의 **모든 경로**(목록·필터·상세·AI SQL·문서 RAG)에서 노출 안 됨. 강제 지점: RLS(`0002_listings`) + `sql_guard.py` + 문서 RAG 결과 필터. 새 조회 경로를 추가하면 이 필터를 반드시 함께 적용.

### 8. 채팅 무결성은 DB로 못박는다
`buyer_id <> seller_id` CHECK 제약 + BEFORE INSERT 트리거가 클라가 보낸 `seller_id`를 매물 실소유자로 강제 덮어씀(위조 차단). UI 숨김에만 의존하지 않는다. 채팅 현재 방식=**4초 증분 폴링**(웹소켓 아님).

### 9. web 폴더·경로 규칙
- 라우트 그룹: `app/(auth)` · `app/(user)` · `app/(admin)`. `components/{ai,auth,layout,listings,ui}`, `lib/{api,auth,supabase}`.
- import 별칭 `@/*` → `./src/*`. TypeScript **strict 켜짐**. UI 문자열은 한국어.

### 10. DB 변경은 번호순 마이그레이션으로만 추적
`supabase/migrations/NNNN_이름.sql`, 전진(forward-only). **RLS 정책은 해당 테이블 마이그레이션에 동거**시킨다(별도 파일로 흩지 않음). 스키마 설명은 `docs/db-schema-guide.md`.

### 11. 브랜치·검증
`develop`에서 개발→동작 확인→`main` 병합. `main`엔 검증된 코드만. 구현하면 직접 실행·관찰해 확인(web=브라우저 E2E, api=HTTP/curl, app=실폰 mobile-mcp). 참고: mobile-mcp는 안드로이드 한글 입력 불가(ASCII만).

### 12. 테스트 규칙 (층별 — 근거: 각 프레임워크 공식 문서 + 테스트 피라미드)
하나로 뭉치지 않는다. 층마다 표준이 다르다:
- **api (FastAPI+LangGraph):** LLM을 fake로 교체해 pytest **결정론적 단위테스트**(라우팅·SQL가드·파라미터 추출). 실제 LLM 품질은 별도 **eval/live-smoke 트랙**(회귀 게이트, 매 커밋마다 돌리지 않음). ← 이미 실천 중, 표준 부합.
- **web (Next.js App Router):** **E2E(Playwright) 우선** — Next.js 공식이 async 서버 컴포넌트는 단위테스트 대신 E2E를 권장. 서버 컴포넌트 밖 순수 유틸(폼 검증 등)이 생기면 그것만 Vitest 단위테스트로 보강.
- **app (Flutter):** 핵심 Riverpod 컨트롤러 로직(채팅 폴링 상태 전이·필터 조합 등)은 `ProviderContainer.test`로 **순수 Dart 단위테스트 추가를 고려**(Supabase는 리포지토리로 감싸 fake 주입). 단순 화면은 실폰 E2E 유지. **트리거 = 컨트롤러 로직이 복잡해질 때.**
- **공통:** 구현 후 반드시 직접 실행·관찰(회귀 방지). E2E-only는 표면이 작을 때의 **의도적 절충**이지 무기한 표준이 아님.

### 13. 반응형 UI 무결성 (D5 — 전 UI governing, web·app·관리자 공통)
가로폭이 줄면 **그리드 열 수로만 흡수**(4→2→1). 개별 컴포넌트 **내부 가로 배치(신뢰속성 행·meta·옵션 칩·버튼 라벨·필터 버튼)를 세로로 접지 않는다** — 텍스트가 길거나 공간이 부족해도 **줄바꿈 찌그러짐·2줄로 밀리는 버튼·라벨 어긋남 = 금기**. 공간 부족은 `truncate`("…")·"외 N"·열 축소로만 처리. 가장자리 카드 부분 클리핑만 허용(모바일에서 살짝 가려지는 정도). **레이아웃 어긋남·깨짐 = 절대 금기.** 관리자 화면도 예외 없음. (원문: `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md` D5(107행)·`EXPERIENCE.md`(161행) 브레이크포인트 ≥1100=4열·640~1099=2열·<640=1열)

---

_기술부채 대장: `docs/tech-debt.md` · 보류/결정 이력: `_bmad-output/implementation-artifacts/deferred-work.md` · 역할별 내비 규칙: `_bmad-output/planning-artifacts/nav-ia-rules.md`_

---

## Usage Guidelines

**AI 에이전트용:**
- 코드 구현 전 이 파일을 먼저 읽는다. 모든 규칙을 그대로 따른다.
- 애매하면 더 보수적인 쪽을 택한다. 새 패턴이 생기면 이 파일을 갱신한다.
- 값이 충돌하면 단일 출처(`docs/conventions.md`)가 우선.

**사람용:**
- 이 파일은 lean하게 유지한다(에이전트 컨텍스트 효율). 스택·규칙이 바뀔 때만 갱신.
- 이번 증분(이미지·웹소켓·RAG개선·UI개편)에서 계약(규칙 3·5)이나 채팅 방식(규칙 8)이 바뀌면 **이 파일을 먼저** 고친다.

_Last Updated: 2026-07-12 (rule 13 반응형 무결성 추가)_
