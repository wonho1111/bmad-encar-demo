# Story 1.1: 모노레포 스캐폴딩 + Supabase 연결 + 공유 계약 단일출처

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want web 앱 골격과 Supabase 프로젝트를 연결하고 공유 규약(임베딩 768 상수·네이밍·환경변수)을 한 곳에 고정하고 싶다,
so that 이후 모든 기능이 흔들리지 않는 토대 위에서 개발될 수 있다.

## Acceptance Criteria

1. **(웹 골격)** 빈 저장소에서 `create-next-app`으로 `web/`(Next.js 16, TypeScript·Tailwind·App Router·`src/` 디렉터리·Turbopack)를 생성하면, 개발 서버가 기동되고 기본 페이지가 뜬다. `app/`·`api/`는 이 스토리 범위가 아니다(후행 에픽).
2. **(Supabase 연결)** `web/src/lib/supabase/`(client·server 두 파일)와 `web/.env.local`(`NEXT_PUBLIC_SUPABASE_URL`·`NEXT_PUBLIC_SUPABASE_ANON_KEY`)을 설정하면, 앱이 Supabase에 연결된다(연결 확인 페이지 또는 헬스 체크로 입증).
3. **(공유 계약 단일출처)** 폴리글랏 일관성 규칙(AR5)을 공유 상수/문서로 명문화하면, 임베딩 차원(768)·통신선 snake_case·단위(km·원·cc) 규약이 **단일 출처**로 존재한다. 그리고 `.env.example`에 필요한 환경변수 키가 비밀값 없이 문서화되어 있다(이미 존재 — 검증·정합 확인).

## Tasks / Subtasks

- [x] **Task 1: `web/` Next.js 16 앱 스캐폴딩 (AC: 1)**
  - [x] 1.1 저장소 루트에서 실행: `npx create-next-app@latest web --typescript --tailwind --eslint --app --src-dir --turbopack` (대화형 프롬프트는 비대화 플래그로 회피; import alias 기본값 `@/*` 유지)
  - [x] 1.2 `web/package.json`의 Next.js 버전이 16.x(목표 16.2.7)인지 확인. 크게 어긋나면 보고 후 진행.
  - [x] 1.3 dev 서버를 **백그라운드 태스크**로 기동(`cd web && npm run dev`, 포트 `:3000`)하고 health check(`http://localhost:3000` 200 응답) 후 기본 페이지 렌더 확인. 확인 끝나면 프로세스 정리.
  - [x] 1.4 `app/`·`api/`·`supabase/`는 이 스토리에서 만들지 않는다(범위 밖).
- [x] **Task 2: Supabase 클라이언트 연결 배선 (AC: 2)**
  - [x] 2.1 `web/`에서 `@supabase/supabase-js`와 `@supabase/ssr` 설치.
  - [x] 2.2 `web/src/lib/supabase/client.ts`(브라우저용, `createBrowserClient`)와 `web/src/lib/supabase/server.ts`(서버 컴포넌트/액션용, `createServerClient` + Next.js `cookies()`) 작성.
  - [x] 2.3 `web/.env.local.example`(또는 루트 `.env.example` 참조 주석)에 맞춰 `web/.env.local`에 `NEXT_PUBLIC_SUPABASE_URL`·`NEXT_PUBLIC_SUPABASE_ANON_KEY` 키를 배치(값은 사용자가 직접 입력 — 아래 "사용자 직접 처리").
  - [x] 2.4 연결 입증: 임시 라우트(예: `web/src/app/health/page.tsx`)에서 서버 클라이언트로 가벼운 호출(예: `supabase.auth.getSession()` 또는 빈 쿼리)을 수행해 에러 없이 응답함을 확인. **테이블 조회는 하지 않는다**(스키마는 Epic 1 후속 스토리에서 생성). 검증 후 임시 라우트는 남겨두거나 제거(판단해 dev notes에 기록).
- [x] **Task 3: 공유 계약 단일출처 명문화 (AC: 3)**
  - [x] 3.1 `docs/conventions.md` 생성 — 폴리글랏 단일 출처 문서. 포함: ① 임베딩 차원 `768`(생성·저장·검색 전 구간 일치) ② 통신선(DB 컬럼·JSON 필드) `snake_case` 강제 ③ 단위 규칙(`mileage`=km 정수, `price`=원 정수, `displacement`=cc 정수) ④ AI 응답 공통 포맷 `{answer, listings[]}` / 에러 포맷 `{error:{code,message}}`. 출처는 architecture.md를 인용.
  - [x] 3.2 `web/src/lib/constants.ts` 생성 — 웹 측에서 import 가능한 타입 상수로 `EMBEDDING_DIM = 768` 등 핵심 상수 노출(문서와 값 일치). 향후 단위 포맷 유틸(`format.ts`)이 참조.
  - [x] 3.3 루트 `.env.example` 검증 — 이미 존재하므로 키 정합만 확인(`NEXT_PUBLIC_SUPABASE_URL/ANON_KEY`, `GEMINI_EMBEDDING_DIM=768` 등). 누락 시에만 보완, 비밀값은 절대 넣지 않는다.
  - [x] 3.4 `web/`가 새로 만든 `.gitignore`(create-next-app 생성)에 `.env*.local`이 포함됐는지 확인. 루트 `.gitignore`와 충돌·중복 점검.
- [x] **Task 4: 검증 및 보고**
  - [x] 4.1 `cd web && npm run build`(또는 `npm run lint`)로 빌드/린트 통과 확인.
  - [x] 4.2 dev 서버 기동 → 기본 페이지 + health 라우트 동작을 Playwright MCP 또는 curl로 확인하고 결과를 사실대로 보고.

### Review Findings (코드 리뷰 2026-06-19)

- [x] [Review][Patch] `getSession()`이 실제 연결을 증명하지 못함 — 세션 쿠키가 없으면 네트워크 호출 없이 로컬에서 반환되어, Supabase가 도달 불가여도 "연결 성공"으로 표시됨. AC2 검증 취지 약화. **해결(2026-06-19)**: GoTrue `/auth/v1/health`(apikey 헤더) fetch로 교체 — 인증 상태 무관 항상 네트워크 요청(200/401/throw로 도달·키·네트워크 구분). 실제 프로젝트로 엔드포인트 응답 검증 후 적용, Playwright로 "연결 성공" 재확인. server.ts 클라이언트는 `getUser()`로 별도 배선 확인(비로그인=정상). [web/src/app/health/page.tsx]
- [x] [Review][Defer] 브라우저/서버 Supabase 클라이언트에 env 누락 가드 없음 (`!`가 컴파일러만 침묵, 미설정 시 런타임에 불투명 에러) [web/src/lib/supabase/client.ts:7, server.ts:10] — deferred, @supabase/ssr 표준 패턴이며 오설정 시에만 발생(데모 범위에서 경미). middleware 스토리에서 재검토.

## Dev Notes

### 범위 경계 (반드시 준수)
- 이 스토리는 **`web/` 골격 + Supabase 연결 배선 + 공유 계약 문서/상수**까지만이다. 인증 화면(1.2)·DB 스키마/마이그레이션(1.2의 `0001_profiles`)·RLS는 **다음 스토리**다. 여기서 테이블을 만들거나 가입 폼을 구현하지 말 것.
- `app/`(Flutter)·`api/`(FastAPI)는 만들지 않는다. [Source: epics.md#Story-1.1, architecture.md#Implementation-Handoff]

### 아키텍처 결정 — 단일 `web/` 앱 (중요)
- architecture.md가 step-03의 `web-user`+`web-admin` **2앱 초기화를 명시적으로 대체**했다: 단일 `web/` 앱 + Next.js 라우트 그룹 `(user)`/`(admin)` + RBAC로 통합한다. 따라서 앱 이름은 **`web`** 하나다(`web-user`/`web-admin` 만들지 말 것). [Source: architecture.md#Project-Structure-&-Boundaries(line 314)]
- 디렉터리 구조 목표(이 스토리 해당분):
  - `web/src/app/layout.tsx`, `web/src/app/page.tsx` (create-next-app 기본)
  - `web/src/lib/supabase/{client.ts, server.ts}` — Supabase 직접 접근 (RLS 경유)
  - `web/src/lib/constants.ts` — 공유 상수(웹 측)
  - (후속) `web/src/lib/format.ts`, `web/src/lib/queries/`, `web/middleware.ts` — **이 스토리에서 안 만듦** [Source: architecture.md#Complete-Project-Directory-Structure]

### 통신 토폴로지 (왜 Supabase 직접 연결인가)
- 클라이언트(web)는 인증·CRUD·채팅을 **Supabase SDK로 직접** 호출하며 RLS로 보호된다. FastAPI는 **AI 검색 전용**(Epic 4)이다. 그래서 이 스토리에서 web↔Supabase 배선이 토대가 된다. [Source: architecture.md#API-&-Communication-Patterns, #Architectural-Boundaries]
- 보안: `anon key`는 RLS가 보호하므로 클라이언트 노출이 안전하다. `service_role` 키는 **사용하지 않는다**. [Source: .env.example(line 11)]

### 환경변수 배치 (이미 정의됨 — `.env.example` 존재)
- 루트 `.env.example`가 이미 작성돼 있다. 배치 규칙:
  - `web/.env.local` → 브라우저 전달값만, `NEXT_PUBLIC_` 접두사 필수 → `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
  - `GEMINI_EMBEDDING_DIM=768`·`GEMINI_API_KEY` 등은 **`api/.env`(서버 전용)** 소속이다 → 이 스토리의 web `.env.local`에는 넣지 않는다. (epics AC 문구의 "GEMINI_EMBEDDING_DIM=768"은 *공유 상수의 단일출처가 존재해야 한다*는 의미이며, 그 출처는 `.env.example`(api 섹션) + `docs/conventions.md` + `web/src/lib/constants.ts`로 충족한다.) [Source: .env.example(line 14-29), architecture.md#Infrastructure-&-Deployment]
- 임베딩 768 정합 점검용 1회성 스크립트가 이미 있다: `scripts/check-embedding-dim.ps1` (Gemini 키로 실제 차원 확인). 사용은 Epic 4 시점. [Source: scripts/check-embedding-dim.ps1]

### 공유 계약(AR5) 핵심값 — `docs/conventions.md`에 담을 내용
- **임베딩 차원:** `vector(768)` — 생성·저장·검색 전 구간 일치(불일치 시 AI 검색 미동작). [Source: architecture.md#Technical-Constraints]
- **통신선 네이밍:** DB 컬럼·JSON 페이로드 모두 `snake_case`. (예: `seller_id` → JSON `"seller_id"` → TS 내부에서 `sellerId`로 매핑) [Source: architecture.md#Naming-Patterns, #Pattern-Examples]
- **단위 규칙:** `mileage`=km 정수, `price`=원(KRW) 정수, `displacement`=cc 정수. mile/마일 금지. [Source: architecture.md#Unit-&-Measurement-Rules]
- **AI 응답 공통 계약:** `{ "answer": string, "listings": ListingCard[] }`, 0건이면 `listings: []` + `answer`에 조건 완화 안내. **에러 포맷:** `{ "error": { "code": string, "message": string } }`. [Source: architecture.md#Format-Patterns]

### 코드 컨벤션 (이 스토리 적용분)
- TS(웹): 컴포넌트 파일 `PascalCase.tsx`, 함수·변수 `camelCase`. 유틸/lib 파일은 `camelCase.ts`. [Source: architecture.md#Naming-Patterns]
- 사용자 노출 메시지·페이지 텍스트는 한국어. [Source: architecture.md#Process-Patterns]
- 강제 도구: web ESLint + Prettier(create-next-app이 ESLint 포함). [Source: architecture.md#Enforcement-Guidelines]

### 검증 표준 (테스트 방식)
- web(Next.js)은 dev 서버를 백그라운드 태스크로 띄우고 health check 후 **Playwright MCP**로 실제 브라우저를 열어 기본 페이지/health 라우트를 확인한다. 포트 `:3000`. 작업 종료 시 프로세스 정리. [Source: bmad-encar-demo/CLAUDE.md#6.구현-단계-테스트-방식]
- create-next-app은 기본 테스트 프레임워크가 없다(추후 추가). 이 스토리는 빌드·lint·실기동 확인으로 충족. [Source: architecture.md#Testing-Framework]

### 버전 (착수 시점 재확인 권장)
- Next.js 16.2.7 · `create-next-app@latest` 사용. `@supabase/supabase-js` + `@supabase/ssr`(Next.js App Router 쿠키 기반 세션). TanStack Query 5.101.0은 폴링·AI 채팅용이라 **후속 스토리에서 설치**(여기선 불필요). [Source: architecture.md#Selected-Approach, #Frontend-Architecture]

### Project Structure Notes
- 정합 확인: 단일 `web/` 앱 결정(architecture line 314)이 epics 1.1 AC의 "`web/`"와 일치한다. step-03의 2앱 명령은 폐기됨 — 충돌 없음, 단일 앱으로 진행.
- `--src-dir` 사용 → 모든 소스는 `web/src/` 아래. 따라서 epics AC가 느슨하게 적은 `web/lib/supabase/`는 실제로 **`web/src/lib/supabase/`**가 정답(architecture 구조 기준). [Source: architecture.md#Complete-Project-Directory-Structure(line 360)]

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Starter-Template-Evaluation]
- [Source: _bmad-output/planning-artifacts/architecture.md#Project-Structure-&-Boundaries]
- [Source: _bmad-output/planning-artifacts/architecture.md#Implementation-Patterns-&-Consistency-Rules]
- [Source: .env.example]
- [Source: scripts/check-embedding-dim.ps1]
- [Source: bmad-encar-demo/CLAUDE.md (작업 지침 1·3·6)]

### 사용자 직접 처리 항목 (왜 / 어디서)
- **Supabase 프로젝트 생성 + URL·anon key 발급** — `web/.env.local`에 넣을 실제 연결값. 코드 밖 비밀/프로젝트 자원이라 사용자만 가능 / Supabase 콘솔(supabase.com) → 프로젝트 Settings → API.
- **`web/.env.local`에 실제 값 입력** — `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` / 로컬 `web/.env.local` 파일.
- (참고) Supabase 프로젝트가 아직 없으면 dev가 코드·배선까지 완성하고, 연결 입증(AC2)은 키 입력 후 사용자가 최종 확인. dev는 키 없이 가능한 범위(빌드·구조·세션 호출 시도)까지 검증해 보고.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Amelia / dev-story)

### Debug Log References

- 스캐폴딩: `npx create-next-app@latest web ...` → Next.js **16.2.9**, React 19.2.4 설치 (목표 16.2.7과 동일 16.x 계열, dev notes 지침대로 진행).
- dev 서버: Turbopack, `:3000` `Ready in 1.6s`, `GET / 200`·`GET /health 200` 로그 확인.
- lint: `eslint` 무오류. build: `next build` 컴파일·TypeScript·정적 생성 성공, `/health`는 `ƒ (Dynamic)`로 분류(force-dynamic 의도대로).
- Playwright MCP: `/` 기본 페이지("Create Next App") + `/health` 렌더 확인. 키 미설정이라 health가 "환경변수 미설정"을 정상 표시.
- 정리: 잔존 dev 서버(PID 15552) `Stop-Process`로 종료, `:3000` down 확인.

### Completion Notes List

- **AC1 충족**: 단일 `web/` Next.js 16 앱 스캐폴딩(TS·Tailwind·App Router·`src/`·Turbopack), dev 서버 기동·기본 페이지 렌더 확인.
- **AC2 충족 (실연결 확인 완료)**: `src/lib/supabase/{client.ts,server.ts}`(`@supabase/ssr`) 작성. 사용자가 `web/.env.local`에 실제 `NEXT_PUBLIC_SUPABASE_URL` + publishable key 입력 후, `/health`가 GoTrue `/auth/v1/health`로 **실제 네트워크 도달**을 점검해 "연결 성공"을 Playwright로 확인(2026-06-19, 코드 리뷰 patch 반영). server.ts 클라이언트도 `getUser()` 호출로 배선 확인(비로그인=정상). 키는 publishable key 사용(service_role/secret 미사용, 아키텍처 준수).
- **AC3 충족**: `docs/conventions.md`(폴리글랏 단일 출처: 임베딩 768·snake_case·단위 km/원/cc·응답·에러 포맷·FR11) + `web/src/lib/constants.ts`(`EMBEDDING_DIM=768` 등 타입 상수). 루트 `.env.example`는 기존 파일이 키 정합함을 확인(수정 불필요).
- 범위 준수: `app/`·`api/`·`supabase/` 미생성. DB 스키마·인증 화면은 후속 스토리.
- 정리 항목: `.playwright-mcp/` 테스트 산출물을 루트 `.gitignore`에 추가.
- 미해결/후속: 실 Supabase 키 입력 후 `/health` 최종 확인(사용자). 확인 후 `/health` 임시 라우트는 제거 가능(현재는 검증 편의를 위해 유지).

### File List

- `web/` — Next.js 16 앱 전체 스캐폴딩 (신규, create-next-app 생성)
- `web/src/lib/supabase/client.ts` — 신규 (브라우저 Supabase 클라이언트)
- `web/src/lib/supabase/server.ts` — 신규 (서버 Supabase 클라이언트, 쿠키 연동)
- `web/src/lib/constants.ts` — 신규 (공유 상수: 임베딩 768·status·role·units)
- `web/src/app/health/page.tsx` — 신규 (연결 점검 임시 라우트)
- `web/.env.local` — 신규 (로컬 키 배치, gitignore 보호, 값 비움)
- `web/package.json` — `@supabase/supabase-js`·`@supabase/ssr` 의존성 추가
- `docs/conventions.md` — 신규 (공유 계약 단일 출처 문서)
- `.gitignore` — `.playwright-mcp/` 무시 추가

## Change Log

- 2026-06-19: Story 1.1 구현 완료 — web 스캐폴딩 + Supabase 클라이언트 배선 + 공유 계약 단일출처(conventions.md·constants.ts). lint/build/Playwright 검증 통과, Status → review. (Amelia)
- 2026-06-19: 코드 리뷰(Blind/Edge/Auditor 3-레이어) 수행 — AC1·2·3 PASS 확인. patch 1건 해결(health 연결 점검을 `getSession`→GoTrue `/auth/v1/health` 실프로브로 교체), defer 1건 기록(env 가드, deferred-work.md), dismiss 1건. lint/build/Playwright 재검증 통과, Status → done. (Amelia)
