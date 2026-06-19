# Story 1.4: 역할별 접근 제어 + profiles RLS

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 서비스 운영 주체,
I want 역할(구매자/판매자/관리자)에 따라 화면·데이터 접근을 통제하고 싶다,
so that 권한 밖 기능·데이터에 접근하지 못하게 한다.

## Acceptance Criteria

1. **(비로그인 → 보호 경로 → 로그인 리다이렉트)** 라우트 가드가 동작할 때, 비로그인 사용자가 보호 경로(현재는 `/admin/*`)에 접근하면 `/login`으로 리다이렉트된다. (로그인 후 원래 가려던 곳으로 돌아갈 수 있게 `?redirectedFrom=` 쿼리를 동봉한다.)
2. **(profiles RLS — 본인 행만, 관리자는 전체)** `0001_profiles`에 동거된 profiles RLS 정책이 적용된 상태에서, 사용자가 profiles를 조회하면 **본인 행만** 읽히고, **관리자만 전체**를 읽는다. (새 마이그레이션 없이 Epic 1 시점에 이미 활성 — 본 스토리는 검증만 한다.)
3. **(역할 분기 차단)** 판매자(또는 구매자) 계정으로 관리자 전용 경로(`/admin/*`)에 접근하면 역할 분기로 차단된다(홈으로 리다이렉트). 관리자 계정만 통과한다.

> **범위 주의(반드시 준수):** 이 스토리는 **접근 제어 골격**(세션 갱신 proxy + 보호 경로 인증 가드 + 관리자 역할 게이트 + profiles RLS 검증)까지다. **실제 관리자 화면(회원·매물·거래·채팅 관리)과 `0005_admin_policies`(관리자 전권 교차 정책)는 Story 6.1/Epic 6** 소관이다. 여기서는 게이트가 동작함을 보이는 **최소 `/admin` 자리표시(placeholder) 페이지**만 만든다. 매물·검색·채팅 등 다른 보호 경로는 아직 화면이 없으므로(후행 에픽) proxy의 보호 경로 목록에 주석으로만 예약한다. `app/`(Flutter)·`api/`(FastAPI)는 만들지 않는다.

## Tasks / Subtasks

- [x] **Task 1: Supabase 세션 갱신 헬퍼 (AC: 1, 2, 3 기반)**
  - [x] 1.1 `web/src/lib/supabase/session.ts` 작성 — `updateSession(request: NextRequest)` export. `@supabase/ssr`의 `createServerClient`를 **NextRequest/NextResponse 쿠키에 배선**(getAll/setAll)해 만료 토큰을 갱신한다. 이게 1.3에서 미뤄둔 "서버측 세션 자동 갱신"을 완성한다.
  - [x] 1.2 헬퍼 안에서 `supabase.auth.getUser()`를 호출해(서버 재검증) 로그인 여부를 판별하고, `{ response, user }`를 반환한다. **`createServerClient`와 `getUser()` 사이에 다른 로직을 넣지 말 것**(Supabase 공식 경고 — 세션 동기화가 깨질 수 있음).
  - [x] 1.3 응답 쿠키 보존 규칙 준수: 새 `NextResponse`를 만들 때 반드시 기존 `response.cookies`를 복사해 돌려준다(토큰 갱신 쿠키 유실 방지). Supabase 공식 SSR 패턴 그대로.
- [x] **Task 2: 루트 proxy 라우트 가드 (AC: 1)**
  - [x] 2.1 `web/src/proxy.ts` 작성 — **`middleware.ts`가 아니라 `proxy.ts`**(Next.js 16에서 middleware는 deprecated·proxy로 개명). `proxy(request)` 함수 + `config.matcher` export.
  - [x] 2.2 모든 매칭 요청에서 Task 1의 `updateSession()`을 호출해 세션을 갱신한다(인증 상태와 무관하게 토큰 갱신은 항상 수행).
  - [x] 2.3 보호 경로 상수(`PROTECTED_PREFIXES = ['/admin']`, 후행 에픽용 `/sell`·`/chat` 등은 주석으로 예약) 정의. 비로그인 + 보호 경로 → `NextResponse.redirect('/login?redirectedFrom=<원경로>')`.
  - [x] 2.4 `config.matcher`로 정적자원·이미지·`favicon.ico` 제외(인증 로직이 CSS/JS/이미지 로딩을 막지 않게). 공개 경로(`/`·`/login`·`/signup`·`/health`)는 세션 갱신은 받되 리다이렉트되지 않는다(보호 목록에 없으므로 자연히 통과).
  - [x] 2.5 **env 가드(deferred-work 처리):** Supabase env(`NEXT_PUBLIC_SUPABASE_URL`/`ANON_KEY`) 누락 시 proxy는 명확한 한국어 경고를 **로그**로 남기고 요청은 통과(`NextResponse.next()`)시킨다 — 가드 부재로 인한 불투명 throw를 방지. (아래 Task 5와 짝.)
- [x] **Task 3: 관리자 영역 자리표시 + 역할 게이트 (AC: 2, 3)**
  - [x] 3.1 `web/src/lib/auth/guard.ts` 작성 — 서버 컴포넌트용 재사용 헬퍼: `requireUser()`(비로그인 시 `/login` redirect), `requireRole(role)`(역할 불일치 시 `/` redirect). `@/lib/supabase/server`의 `createClient()` + `getUser()` + `profiles.role` 조회 사용. Epic 2/3/6이 재사용할 단일 출처.
  - [x] 3.2 `web/src/app/(admin)/admin/page.tsx` 작성 — 최소 자리표시("관리자 영역 — 준비 중", Epic 6 안내). 라우트 그룹 `(admin)`은 URL에 안 들어가므로 실제 경로는 `/admin`.
  - [x] 3.3 `web/src/app/(admin)/layout.tsx`(또는 page 상단)에서 `requireRole(USER_ROLE.ADMIN)` 호출 — 비관리자(구매자·판매자)는 홈으로 리다이렉트(AC3 2차·실질 집행), 비로그인은 `/login`(AC1과 일관). proxy(1차 optimistic) + 서버 컴포넌트(2차 실집행) 이중 방어.
  - [x] 3.4 역할 조회는 `profiles_select_self`(본인 행) RLS로 허용됨 — 새 쿼리/정책 만들지 말 것. 관리자 라벨·상수는 `USER_ROLE` 재사용(영문 리터럴 금지).
- [x] **Task 4: profiles RLS 검증 (AC: 2)** — 새 마이그레이션 없음
  - [x] 4.1 `0001_profiles.sql`의 `profiles_select_self`·`profiles_select_admin` 정책이 적용돼 있는지 확인(`list_tables`/`execute_sql`로 정책 존재 점검). **0001을 수정하지 말 것**(1.2에서 완성·적용됨).
  - [x] 4.2 구매자·판매자 테스트 계정 각 1개로 로그인 → `select * from profiles`가 **본인 1행만** 반환함을 E2E/SQL로 확인(타인 행 비노출 = select_self 동작).
  - [x] 4.3 관리자 전체 조회(`profiles_select_admin`)는 관리자 계정이 아직 없으므로(시드는 Story 1.5) **정책 존재 + `is_admin()` 경로**로 검증하고, 실계정 E2E는 1.5 이후로 명시 이연. (`execute_sql`로 admin 역할 행을 임시 생성·조회·정리하는 교차검증은 선택.)
- [x] **Task 5: env 누락 가드 보강 (deferred-work 종결)**
  - [x] 5.1 `web/src/lib/supabase/client.ts`·`server.ts`의 `process.env.…!` 비-널 단언을 **런타임 가드**로 보강 — 누락 시 어떤 변수가 비었는지 명시한 한국어 에러를 throw(불투명 throw → 명확 진단). `@supabase/ssr` 표준 패턴 유지하되 오설정 진단성만 개선.
  - [x] 5.2 처리 완료 후 `_bmad-output/implementation-artifacts/deferred-work.md`에서 해당 env 가드 항목(1-1·1-2발) 2건을 **제거**(또는 "Story 1.4에서 해소" 표기).
- [x] **Task 6: 검증 및 보고 (AC: 전체)**
  - [x] 6.1 `npm run lint`(무오류) + `npm run build`(Next 16.2.9 통과, `proxy.ts` 인식 확인).
  - [x] 6.2 dev 서버 백그라운드 기동 → health check(`/login` 200) → **Playwright E2E**:
    - ① 비로그인으로 `/admin` 직접 접근 → `/login`(`?redirectedFrom=/admin`) 리다이렉트(AC1).
    - ② 판매자 가입·로그인 → `/admin` 접근 → 홈 `/`로 차단(AC3).
    - ③ (관리자 계정 부재) 관리자 통과 happy-path는 `execute_sql`로 임시 admin 계정 만들어 검증하거나 Story 1.5 이후로 이연 — 택1 후 결과 명기.
    - ④ profiles 본인 행만 조회됨 확인(AC2, Task 4.2).
    - 종료 후 `:3000` 정리(잔존 PID Stop-Process, 포트 DOWN 확인), 테스트 계정 `execute_sql`로 cascade 삭제(`users_left=0` 교차검증).
  - [x] 6.3 결과 사실대로 보고(아래 Completion Notes). 관리자 happy-path 검증 방식(임시계정 vs 이연)을 명시.

## Dev Notes

### ⚠️ 가장 중요 — Next.js 16: `middleware.ts` → `proxy.ts` (학습 데이터와 다름)
- **에픽·아키텍처 문서는 `middleware.ts`라고 적혀 있지만, 설치된 Next.js 16.2.9에서 그 파일명은 deprecated이고 `proxy.ts`로 개명됐다.** `middleware()` 함수도 `proxy()`로 바뀐다. 이건 `web/AGENTS.md`가 경고한 "당신이 아는 Next.js가 아니다"의 대표 사례. **반드시 `proxy.ts`로 작성**한다(아니면 동작/빌드 경고).
  - 함수: `export function proxy(request: NextRequest) {…}`(또는 default export). 단일 파일만 지원.
  - 위치: `--src-dir`이므로 `web/src/proxy.ts`(app과 같은 레벨).
  - **Runtime:** Next 16 proxy는 기본 **Node.js 런타임** — `@supabase/ssr`가 그대로 동작(옛 Edge 런타임 제약 없음). `runtime` config는 proxy에서 설정 불가(에러).
  - [Source: web/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md (Migration to Proxy / Version history v16.0.0), web/AGENTS.md]
- **Proxy = optimistic 체크만.** Next.js 인증 가이드: proxy는 "쿠키 기반 빠른 인증/리다이렉트"용이며 **DB 조회·전체 인가 솔루션으로 쓰지 말라**. 보안의 본진은 데이터에 가까운 곳(RLS·서버 컴포넌트)이다. → 그래서 본 스토리는 **proxy=로그인 여부 게이트(1차)**, **관리자 역할 게이트는 `(admin)` 서버 레이아웃 + RLS(2차)**로 나눈다. proxy에서 매 요청 `profiles.role`을 DB 조회하지 않는다(성능·prefetch 폭주 방지). [Source: web/node_modules/next/dist/docs/01-app/02-guides/authentication.md (Optimistic checks with Proxy)]
  - **아키텍처와의 정합:** architecture.md는 "/admin = 1차 미들웨어 + 2차 RLS"를 명시한다. 본 스토리는 그 의도(비관리자는 /admin 불가, 이중 방어)를 충족하되, **1차 역할 판정 위치를 proxy가 아닌 `(admin)` 서버 레이아웃**에 둔다(Next 16 권장 + DB 조회 회피). proxy를 JWT 클레임 기반 역할 게이트로 끌어올리는 것은 Story 6.1에서 admin 본격화 시 선택적으로 검토. [Source: architecture.md#Architectural-Boundaries(사용자/관리자 경계), epics.md#Story-6.1]

### Supabase SSR 세션 갱신 패턴 (proxy)
- 표준 `@supabase/ssr` 패턴은 "middleware에서 `updateSession` 호출 → 만료 토큰 자동 갱신 + 갱신 쿠키를 응답에 기록"이다. 우리 버전에선 그 호출부가 `proxy.ts`다. 헬퍼는 `web/src/lib/supabase/session.ts`에 둔다(이름에 'middleware' 쓰지 않음 — 혼동 방지).
- **불변 규칙(공식):** ① `createServerClient`↔`getUser()` 사이에 코드 삽입 금지. ② 응답을 새로 만들면 기존 쿠키를 반드시 복사해 반환. 어기면 "사용자가 무작위 로그아웃" 버그. [Source: @supabase/ssr 0.12.0 공식 SSR 가이드, web/src/lib/supabase/server.ts 주석("미들웨어가 세션 갱신을 담당")]
- 서버에선 **`getUser()`**(Auth 서버 재검증), `getSession()` 금지 — 1.3에서 확립한 규칙 동일. [Source: 1-3 Dev Notes]
- 이 작업으로 1.3이 남긴 한계("middleware 부재로 서버측 토큰 자동 갱신 미동작")가 해소된다. `server.ts`의 "후속 스토리에서 middleware 추가" 주석은 "proxy가 갱신 담당"으로 갱신해도 됨(선택). [Source: 1-3 Completion Notes(세션 자동 갱신 한계)]

### 재발명 금지 — 기존 자산 재사용
- **역할 상수:** `@/lib/constants`의 `USER_ROLE`/`UserRole`. 새 enum·`'admin'` 리터럴 직접 작성 금지. 역할 라벨이 필요하면 1.3 홈의 `ROLE_LABEL` 패턴 재사용(값은 `USER_ROLE` 기준). [Source: web/src/lib/constants.ts, web/src/app/page.tsx(ROLE_LABEL)]
- **Supabase 클라이언트:** 브라우저 `@/lib/supabase/client`, 서버 컴포넌트 `@/lib/supabase/server`(async — `await createClient()`). proxy 전용은 `session.ts`의 새 헬퍼. 새 클라이언트 팩토리 난립 금지. [Source: 1-1/1-2/1-3 File List]
- **역할 조회 패턴:** 홈(`page.tsx`)이 이미 `supabase.from('profiles').select('role').eq('id', user.id).single()`로 본인 역할을 읽는다 — `guard.ts`도 동일 패턴 재사용. [Source: web/src/app/page.tsx:26-34]
- **0001_profiles 그대로:** `profiles_select_self`·`profiles_select_admin`·`is_admin()`이 이미 존재·적용됨. **마이그레이션 신규 생성/수정 금지.** [Source: supabase/migrations/0001_profiles.sql:70-91]

### 라우트 가드 구현 패턴 (proxy.ts 골자)
```ts
// web/src/proxy.ts (개념 — 실제 작성 시 docs 재확인)
import { NextResponse, type NextRequest } from 'next/server';
import { updateSession } from '@/lib/supabase/session';

const PROTECTED_PREFIXES = ['/admin']; // 후행 에픽: '/sell', '/chat' 등 추가 예정

export async function proxy(request: NextRequest) {
  const { response, user } = await updateSession(request); // 세션 갱신 + 사용자
  const { pathname } = request.nextUrl;
  const isProtected = PROTECTED_PREFIXES.some((p) => pathname.startsWith(p));
  if (isProtected && !user) {
    const url = request.nextUrl.clone();
    url.pathname = '/login';
    url.searchParams.set('redirectedFrom', pathname);
    return NextResponse.redirect(url);
  }
  return response; // 갱신 쿠키 보존된 응답
}

export const config = {
  // 정적자원·이미지 제외 (auth가 CSS/JS/이미지 로딩을 막지 않게)
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)'],
};
```
- 관리자 **역할** 게이트는 위 proxy가 아니라 `(admin)/layout.tsx`에서 `requireRole(USER_ROLE.ADMIN)`로 집행(DB 조회는 서버 컴포넌트에서). 비관리자 → 홈, 비로그인 → 로그인. [Source: authentication.md(DAL 권장), architecture.md#사용자/관리자-경계]
- **`redirectedFrom` 활용(선택):** 로그인 화면이 쿼리를 읽어 성공 후 그 경로로 보내면 UX↑. 1.3 로그인은 현재 항상 `/`로 보냄 — 쿼리 처리를 더하면 가점이나 필수는 아님(보호 경로가 `/admin`뿐이라 영향 작음).

### 검증 표준 (테스트 방식)
- web은 dev 서버 백그라운드 기동 + health check 후 **Playwright MCP** 실브라우저 E2E. 포트 `:3000`. 종료 시 프로세스 정리. [Source: bmad-encar-demo/CLAUDE.md#6, 1-3 검증]
- create-next-app 기본 테스트 프레임워크 없음 → 빌드·lint·실 E2E로 충족. [Source: architecture.md#Testing-Framework]
- **테스트 계정 라이프사이클:** 직전 스토리들이 테스트 계정을 모두 삭제했으므로 DB가 비어 있다 → E2E는 (a) 가입으로 필요한 계정(판매자/구매자) 생성 → (b) 검증 → (c) 종료 시 `execute_sql` cascade 삭제·교차검증. [Source: 1-3 Dev Notes(테스트 계정 라이프사이클)]
- **관리자 happy-path 딜레마:** admin 계정 시드는 **Story 1.5**다(아직 없음). AC3의 "관리자만 통과"를 지금 E2E하려면 `execute_sql`로 임시 admin profile을 만들어 검증하거나, 통과 케이스만 1.5 이후로 이연한다 — 택1 후 명시. 차단 케이스(판매자→/admin 차단)는 지금 완전 검증 가능. [Source: epics.md#Story-1.5]

### 이전 스토리(1.1·1.2·1.3) 학습 — 그대로 적용
- **연결·키 배선 완료:** `web/.env.local`에 Supabase URL/anon key 설정됨. 키 재배선 안 함. **anon key만**, `service_role` 금지. [Source: 1-1 Completion Notes]
- **이메일 확인(Confirm email) OFF:** 가입 즉시 세션 생성 → 테스트 계정 가입 직후 로그인 검증 가능. dev는 실제 설정 재확인. [Source: 1-2/1-3 Completion Notes]
- **dev 서버 정리(Windows):** 백그라운드 기동 → 종료 시 `:3000` 점유 PID `Stop-Process` + 포트 down 확인. [Source: 1-1 Debug Log, memory: web-dev-server-cleanup]
- **`/health` 임시 라우트 건드리지 말 것**(1.1 잔존, 제거는 본 스토리 의무 아님). proxy matcher에서 `/health`는 보호 목록에 없으니 자연 통과.
- **이연 항목(env 가드)은 본 스토리에서 종결:** deferred-work.md의 Supabase 클라이언트 env 누락 가드 2건(1-1·1-2발)이 "Story 1.4(middleware) 도입 시 처리"로 명시 이연돼 있다 → Task 5에서 처리하고 목록에서 제거. [Source: _bmad-output/implementation-artifacts/deferred-work.md]

### 코드 컨벤션 (이 스토리 적용분)
- 통신선(DB 컬럼·메타데이터)은 `snake_case`(`role`). 컴포넌트 파일 `PascalCase.tsx`, 유틸/함수·변수 `camelCase`(`updateSession`, `requireRole`). proxy/라우트 파일은 Next 규약명(`proxy.ts`, `page.tsx`, `layout.tsx`). [Source: architecture.md#Naming-Patterns]
- 사용자 노출 메시지·페이지 텍스트는 **한국어**, 로그엔 코드/원인. [Source: architecture.md#Process-Patterns]
- 강제 도구: web ESLint + Prettier. [Source: architecture.md#Enforcement-Guidelines]

### Project Structure Notes
- `--src-dir` 구조 → 모든 웹 소스는 `web/src/` 아래.
- **신규 파일:** `web/src/proxy.ts`, `web/src/lib/supabase/session.ts`, `web/src/lib/auth/guard.ts`, `web/src/app/(admin)/admin/page.tsx`, `web/src/app/(admin)/layout.tsx`.
- **수정 파일:** `web/src/lib/supabase/client.ts`·`server.ts`(env 가드), `_bmad-output/implementation-artifacts/deferred-work.md`(항목 제거), `_bmad-output/implementation-artifacts/sprint-status.yaml`(상태 전이).
- 아키텍처 구조도 정합: `(admin)/admin`(line 353), `middleware.ts`(line 365 — **실제로는 `proxy.ts`로 구현**, 문서 명칭은 옛 버전). 홈을 `(user)` 그룹으로 재배치하는 것은 **본 스토리 범위 아님**(필요 시 후행 정리) — 1.4는 `(admin)` 그룹만 도입. [Source: architecture.md#Complete-Project-Directory-Structure(line 339~366), 1-3 Project Structure Notes]

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.4]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-1.5 (관리자 시드 — admin happy-path 검증 의존)]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.1 (admin 라우트 가드·0005_admin_policies — 본격 admin 게이트는 여기)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication-&-Security (RLS 배치 원칙·1차 미들웨어+2차 RLS)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Architectural-Boundaries (사용자/관리자 경계)]
- [Source: _bmad-output/planning-artifacts/architecture.md#Complete-Project-Directory-Structure(line 339~366, 405·412)]
- [Source: web/node_modules/next/dist/docs/01-app/03-api-reference/03-file-conventions/proxy.md (middleware→proxy 개명·Node 런타임·matcher)]
- [Source: web/node_modules/next/dist/docs/01-app/02-guides/authentication.md (Optimistic checks with Proxy·DAL)]
- [Source: supabase/migrations/0001_profiles.sql (profiles RLS·is_admin — 본 스토리는 검증만)]
- [Source: web/src/app/page.tsx, web/src/lib/{constants.ts,supabase/{client,server}.ts}, web/AGENTS.md]
- [Source: _bmad-output/implementation-artifacts/1-3-로그인-로그아웃.md (세션/getUser 패턴·테스트 계정 라이프사이클·정리)]
- [Source: _bmad-output/implementation-artifacts/deferred-work.md (env 가드 이연 — 본 스토리 종결)]
- [Source: bmad-encar-demo/CLAUDE.md (작업 지침 1·2·3·6)]

### 사용자 직접 처리 항목 (왜 / 어디서)
- **(확인만) Supabase 이메일 확인(Confirm email) 설정** — OFF여야 가입 직후 로그인 검증이 매끄럽다 / Supabase 콘솔 → Authentication.
- **(이미 완료, 확인만)** `web/.env.local` Supabase URL/anon key — proxy 세션 갱신이 안 되면 키부터 확인 / `web/.env.local`.
- **(Epic 1 종료 시 안내 예정)** 관리자 계정 happy-path 완전 검증은 **Story 1.5(관리자 시드)** 이후 가능 — 본 스토리는 차단 케이스 위주 검증.

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (dev-story)

### Debug Log References

- 빌드: `next build`(Next.js 16.2.9, Turbopack) 컴파일·TypeScript 성공, lint 무오류. Route: `/`·`/admin`·`/health` ƒ(Dynamic), `/login`·`/signup` ○(Static). **`ƒ Proxy (Middleware)`** 항목 출력 = `proxy.ts` 정상 인식.
- dev 서버 백그라운드 기동(`:3000` Ready 1.3s) → health check `GET /login` = 200.
- Playwright E2E(`:3000`):
  - **AC1**: 비로그인으로 `/admin` 접근 → `/login?redirectedFrom=%2Fadmin` 리다이렉트 확인.
  - **AC3(차단)**: 판매자(seller-14) 가입·자동로그인 → 홈에 "역할 판매자" 표시(select_self 동작) → `/admin` 접근 → 홈 `/`로 차단 확인.
  - **관리자 happy-path**: admin-14 가입(buyer) → `execute_sql`로 role='admin' 전환 → 재로그인 없이 `/admin` 접근 → "관리자 영역" 화면 표시 확인(서버 컴포넌트가 매 요청 role 재조회).
  - **AC2(RLS 임퍼소네이션)**: profiles 2행 상태에서 `set local role authenticated` + `request.jwt.claims.sub` 설정 → 판매자 컨텍스트 `visible_rows=1`(본인만, select_self), 관리자 컨텍스트 `visible_rows=2`(전체, select_admin via is_admin).
- 정리: 테스트 계정 2건 `delete from auth.users`(cascade) → `users_left=0, total_profiles=0` 교차검증. Playwright 종료, dev 서버 `:3000` 점유 PID 2760 Stop-Process → `:3000` DOWN 확인. 임시 로그·`.playwright-mcp` 제거.

### Completion Notes List

- **AC1 충족**: `web/src/proxy.ts`(Next.js 16 — `middleware.ts` 아님)가 비로그인 + 보호 경로(`/admin`) 접근을 `/login?redirectedFrom=`로 리다이렉트. `updateSession()`이 매 요청 세션 갱신도 수행(1.3이 남긴 "서버측 토큰 자동 갱신 미동작" 한계 해소).
- **AC2 충족**: `0001_profiles`의 `profiles_select_self`/`profiles_select_admin` 정책을 **새 마이그레이션 없이** 검증 — RLS 임퍼소네이션으로 본인=1행, 관리자=전체 확인. 홈·관리자 화면의 실제 역할 조회도 동일 정책으로 동작.
- **AC3 충족**: `(admin)/layout.tsx`의 `requireRole(USER_ROLE.ADMIN)`가 비관리자(판매자)를 홈으로, 비로그인을 `/login`으로 차단. 관리자만 `/admin` 통과. proxy(1차 로그인 게이트) + 서버 컴포넌트(2차 역할 집행) 이중 방어.
- **Next.js 16 함정 처리**: 에픽/아키텍처 문서의 `middleware.ts`는 Next 16에서 deprecated → **`proxy.ts`로 구현**(공식 docs 확인). proxy는 Node 런타임이라 `@supabase/ssr` 정상 동작.
- **설계 결정(아키텍처 정합)**: architecture의 "/admin 1차 미들웨어 + 2차 RLS" 의도는 충족하되, **역할 판정 위치를 proxy가 아닌 `(admin)` 서버 레이아웃**에 둠(Next.js 권장: proxy는 DB 조회 없는 optimistic 체크만). proxy의 JWT-클레임 기반 역할 게이트 격상은 Story 6.1에서 선택적으로 검토.
- **재발명 금지 준수**: 역할 상수 `USER_ROLE` 재사용, Supabase 클라이언트 기존 팩토리 사용, 홈의 역할 조회 패턴을 `guard.ts`로 일반화. 새 enum·마이그레이션·정책 미생성.
- **deferred-work 종결**: Supabase env 누락 가드(1-1·1-2 이연 2건)를 `lib/supabase/env.ts`로 일원화(`getSupabaseEnv` — 누락 변수명 명시 한국어 에러). `client.ts`/`server.ts`의 `process.env.…!` 비-널 단언 제거. proxy는 env 누락 시 경고 로그 + 통과(graceful). `deferred-work.md`에서 해당 항목 제거.
- **관리자 happy-path 검증 방식**: 관리자 시드(Story 1.5) 전이라 `execute_sql`로 **임시 admin 계정**을 만들어 통과 케이스까지 완전 검증함(검증 후 cascade 삭제). 사용자 동의하에 진행 — 데모 DB·본인 계정이라 위험 없음.
- **범위 준수**: 실제 관리자 기능·`0005_admin_policies`는 Epic 6(미구현). `(admin)/admin`은 자리표시만. 매물·검색·채팅 보호 경로는 화면 부재로 proxy 보호목록에 주석 예약. `app/`·`api/` 미생성. 홈의 `(user)` 그룹 재배치는 미수행(후행).

### File List

- `web/src/proxy.ts` — 신규 (Next.js 16 루트 라우트 가드: 세션 갱신 + 보호경로 비로그인 리다이렉트)
- `web/src/lib/supabase/session.ts` — 신규 (proxy용 `updateSession` 세션 갱신 헬퍼)
- `web/src/lib/supabase/env.ts` — 신규 (Supabase env 누락 가드 단일 출처 `getSupabaseEnv`)
- `web/src/lib/auth/guard.ts` — 신규 (서버 컴포넌트용 `requireUser`/`requireRole` 접근 제어 헬퍼)
- `web/src/app/(admin)/layout.tsx` — 신규 (관리자 영역 역할 게이트 `requireRole(admin)`)
- `web/src/app/(admin)/admin/page.tsx` — 신규 (관리자 영역 자리표시 화면)
- `web/src/lib/supabase/client.ts` — 수정 (env 가드 적용, 비-널 단언 제거)
- `web/src/lib/supabase/server.ts` — 수정 (env 가드 적용, 주석 proxy로 갱신)
- `_bmad-output/implementation-artifacts/deferred-work.md` — 수정 (env 가드 항목 해소 처리)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 수정 (1-4 상태 전이)

## Change Log

- 2026-06-20: Story 1.4 구현 — Next.js 16 `proxy.ts` 라우트 가드(세션 갱신 + 보호경로 인증) · `(admin)` 역할 게이트 · profiles RLS 검증(새 마이그레이션 없음) · Supabase env 가드 일원화(deferred-work 종결). lint/build 통과, Playwright E2E로 AC1~3 검증(비로그인 차단·판매자 차단·관리자 통과·RLS self=1/admin=2) + 임시 admin 계정 교차검증·정리. Status → review. (dev-story)
