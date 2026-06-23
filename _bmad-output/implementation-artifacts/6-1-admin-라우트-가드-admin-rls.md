# Story 6.1: admin 라우트 가드 + admin RLS

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want `/admin`을 admin만 통과시키고 관리자 전권 교차 RLS 정책(`0005_admin_policies`)을 적용하고 싶다,
so that 운영 기능(회원·매물·거래·채팅 관리, Epic 6 후속 스토리)이 관리자에게만 열린다.

## Acceptance Criteria

1. **Given** `(admin)` 라우트 가드(`proxy.ts` 1차 + `(admin)/layout.tsx`의 `requireRole(admin)` 2차)와 `0005_admin_policies`(관리자 전권 교차 정책)가 적용되면, **When** 비관리자(비로그인·구매자·판매자)가 `/admin`에 접근하면, **Then** 1차 미들웨어(비로그인→`/login`) + 2차 레이아웃(비관리자→`/`)으로 차단된다. (epics.md L643~645)
2. **Given** 관리자 계정(role=admin)으로, **When** `/admin`에 접근하면, **Then** 관리자 화면이 열린다. (epics.md L647~649)
3. **Given** `0005_admin_policies` 마이그레이션이 적용되면, **When** RLS 정책을 확인하면, **Then** 여러 테이블을 가로지르는 관리자 전권 교차 정책이 `0005_admin_policies` **한 파일에 모여** 존재한다(테이블별 RLS는 각 테이블 마이그레이션에 동거시키되, **관리자 교차 정책만** 0005로 분리하는 architecture.md 원칙). (architecture.md L199, L334, L461)
4. **Given** `0005_admin_policies`가 적용되면, **When** 관리자가 전체 회원(`profiles`)을 정지(UPDATE)·삭제(DELETE)하려 하면, **Then** RLS가 허용한다(FR22 토대). 비관리자는 타인 `profiles`를 UPDATE/DELETE할 수 없다(기존 default-deny 유지).
5. **Given** `0005_admin_policies`가 적용되면, **When** 관리자가 임의 매물(`listings`)을 삭제(DELETE)하려 하면, **Then** RLS가 허용한다(FR23 토대). (조회는 기존 `listings_select_admin`이 이미 담당 → 중복 추가 금지)
6. **Given** `0005_admin_policies`가 적용되면, **When** 관리자가 임의 채팅방·메시지(`chat_rooms`·`chat_messages`)를 열람(SELECT)·삭제(DELETE)하려 하면, **Then** RLS가 허용한다(FR25 토대). 비관리자(제3자)는 기존 참여자 한정 정책대로 0건/거부가 유지된다.
7. **Given** 마이그레이션 적용 후, **When** `get_advisors(security)`를 실행하면, **Then** 본 스토리로 인한 신규 보안 경고(RLS 누락·정책 오류)가 0건이다(기존 vector/is_admin/leaked-password 경고는 본 스토리 무관).

## Tasks / Subtasks

- [x] Task 1: 라우트 가드 현황 사실 확인(이미 Epic 1에서 구현됨 — 신규 코드 불필요 여부 판정) (AC: #1, #2)
  - [x] `web/src/proxy.ts` 확인 — `PROTECTED_PREFIXES`에 `/admin`이 이미 포함됨(L22). 비로그인 1차 차단·fail-closed 동작 확인.
  - [x] `web/src/app/(admin)/layout.tsx` 확인 — `requireRole(USER_ROLE.ADMIN)`로 2차 집행함(구현됨).
  - [x] `web/src/lib/auth/guard.ts`의 `requireRole` 확인 — 비로그인→`/login`, 역할 불일치→`/` 리다이렉트.
  - [x] 결론: 라우트 가드는 Epic 1(1-4·1-5)에서 완성됨 → **이 스토리에서 라우트 가드 코드 변경 없음**. 본 스토리의 신규 산출물은 `0005_admin_policies.sql`(Task 2). Dev Notes/Completion에 명시함.
- [x] Task 2: `0005_admin_policies.sql` 마이그레이션 작성 — 관리자 전권 교차 정책만 모음 (AC: #3, #4, #5, #6)
  - [x] `supabase/migrations/0005_admin_policies.sql` 신규 작성 — 헤더 주석 0001~0006 스타일. 정책명 `<table>_<action>_admin`.
  - [x] **profiles**: 기존 `profiles_select_admin` 중복 생성 안 함. 신규 `profiles_update_admin`(UPDATE, with check도 is_admin) + `profiles_delete_admin`(DELETE).
  - [x] **listings**: 기존 `listings_select_admin` 중복 안 함. 신규 `listings_delete_admin`(DELETE). UPDATE는 요구 없어 미추가.
  - [x] **chat_rooms**: 신규 `chat_rooms_select_admin` + `chat_rooms_delete_admin`.
  - [x] **chat_messages**: 신규 `chat_messages_select_admin` + `chat_messages_delete_admin`.
  - [x] 멱등성: 각 create policy 앞에 `drop policy if exists`(0006 패턴).
  - [x] 모든 정책 `to authenticated` + `public.is_admin()` 재사용 → 무한재귀 회피.
  - [x] 한국어 인라인 주석으로 의도 설명(0001~0003 스타일).
- [x] Task 3: 마이그레이션 적용·검증 (AC: #3~#7)
  - [x] Supabase MCP `apply_migration(name="0005_admin_policies")` 적용 → `{"success":true}`.
  - [x] `list_migrations`로 `0005_admin_policies` 등록 확인(version 20260623233045).
  - [x] `pg_policies` 조회 → 신규 admin 정책 **7개** 모두 존재·`{authenticated}`·`qual=is_admin()`(profiles_update_admin은 with_check도 is_admin()). 기존 profiles/listings SELECT admin은 재사용.
  - [x] `get_advisors(security)` → 본 스토리 신규 경고 0건(기존 vector/is_admin/leaked-password 3건만, 본 스토리 무관). AC#7 충족.
  - [x] (선택) 동작 스모크: MCP 롤 RLS 우회로 차단/허용 동작 재현 한계 → 정책 정의 존재 확인으로 갈음. 실제 관리자 동작 E2E는 6-2~6-5에서 인증 클라이언트로 검증(5-1과 동일 입장).
- [x] Task 4: 라우트 가드 자체 검증(웹 E2E, 가능 범위) (AC: #1, #2)
  - [x] 로컬 `web` dev 서버 백그라운드 기동(`:3000`) + health 확인(/login 200).
  - [x] Playwright MCP로 ① 비로그인 `/admin` → `/login?redirectedFrom=%2Fadmin`(proxy 1차), ② 비관리자(buyer) `/admin` → `/`(layout 2차), ③ 관리자(admin@test.com) 로그인 후 `/admin` → "관리자 영역" 화면 노출(role=관리자) 확인. 세 분기 모두 통과.
  - [x] dev 서버 프로세스 정리 완료.

## Dev Notes

### 핵심 요지(가장 먼저 이해할 것)
- 이 스토리는 **두 갈래**다: (가) **라우트 가드** — 이미 Epic 1에서 완성돼 있어 **신규 코드 없음**(사실 확인만). (나) **관리자 전권 교차 RLS** — `0005_admin_policies.sql`을 **새로 만든다**(이 스토리의 실질 산출물).
- 즉, "1차 미들웨어"(proxy.ts) + "2차 레이아웃"(requireRole)은 그대로 두고, **"2차 RLS" = DB 차원의 관리자 전권**을 0005로 채워 넣는 게 본 작업의 본체다. (epics.md L645 "1차 미들웨어 + 2차 RLS로 차단" 중 RLS 부분.)

### 반드시 먼저 읽을 것 (기존 패턴 — drift 금지)
- `supabase/migrations/0001_profiles.sql` — ⚠️ **`is_admin()` SECURITY DEFINER 헬퍼**(L57~68): RLS 안에서 `profiles`를 직접 서브쿼리하면 "infinite recursion in policy"가 난다. 관리자 판정은 **반드시 `public.is_admin()`** 을 쓴다. 또 `profiles_select_admin`(L80~81)이 **이미 존재** → SELECT admin 정책 중복 생성 금지. 정책 네이밍 `<table>_<action>_<scope>`.
- `supabase/migrations/0002_listings.sql` — `listings_select_admin`(L100~101) **이미 존재**(SELECT 중복 금지). 소유권 UPDATE/DELETE(`*_own`)는 본인 한정 → 관리자 DELETE는 별도 정책 필요. OR 결합(여러 정책은 permissive라 OR로 합쳐짐) 이해.
- `supabase/migrations/0003_chat.sql` — chat_rooms/chat_messages는 **참여자 한정 SELECT/INSERT만** 존재, UPDATE/DELETE 미설정(default-deny). L86·L117 주석이 "관리자 삭제권은 Epic6 `0005_admin_policies`(교차 정책)에서 추가"라고 **명시** → 이 스토리가 그 약속을 이행한다. ⚠️ chat_messages 정책은 `chat_rooms`를 EXISTS로 조인하므로, admin SELECT 정책을 추가할 때 두 테이블 각각에 추가해야 관리자가 둘 다 본다.
- `supabase/migrations/0006_readonly_role.sql` — `drop policy if exists ... ; create policy ...`(L36~38) **멱등 패턴**을 그대로 따른다. ⚠️ chat 테이블엔 ai_readonly 가시성 정책을 **만들지 않은** 의도(0건 노출)이므로, 본 스토리에서 chat에 admin 정책을 추가해도 ai_readonly용 `using(true)`는 절대 추가하지 말 것(AI 검색은 chat 미조회).
- `web/src/proxy.ts`(L22 `/admin` 포함) · `web/src/app/(admin)/layout.tsx`(requireRole admin) · `web/src/lib/auth/guard.ts`(requireRole) — 라우트 가드 3종 세트. **읽고 현상 확인만**(변경 없음).

### RLS 설계 결정(확정)
- **관리자 전권 = `public.is_admin()`**: 0001의 SECURITY DEFINER 헬퍼를 재사용 → RLS 자기참조 재귀 없이 "현재 사용자가 admin인가"를 판정. anon에는 EXECUTE가 회수돼 있고 authenticated만 가지므로(0001 L90~91), 모든 admin 정책은 `to authenticated`로 한정한다.
- **추가 정책(신규 7개)**:
  - `profiles_update_admin` (UPDATE) — FR22 정지(`status=suspended`). `using (is_admin()) with check (is_admin())`. with check도 is_admin()이라야 관리자가 **타인** 행을 수정한 결과가 통과한다(본인 한정이 아님).
  - `profiles_delete_admin` (DELETE) — FR22 삭제. `using (is_admin())`. ※ `profiles.id`는 `auth.users` 참조(on delete cascade) — 실제 "계정 삭제"는 auth.users 삭제가 정석이나, 그건 6-2에서 admin API/서비스롤로 다룰 수 있음. 본 스토리는 **profiles 행 삭제 RLS 토대**까지가 범위(FR22 "계정이 제거된다"의 DB 측 허용). 6-2 구현 방식(서비스롤 vs RLS)은 그 스토리에서 결정.
  - `listings_delete_admin` (DELETE) — FR23.
  - `chat_rooms_select_admin` / `chat_rooms_delete_admin`, `chat_messages_select_admin` / `chat_messages_delete_admin` — FR25 열람·삭제. chat_rooms 삭제 시 cascade로 메시지도 제거되지만(0003 FK on delete cascade), 메시지 단건 삭제 요구가 생길 수 있어 messages에도 DELETE admin 정책을 둔다(FR25 "방과 메시지가 제거된다" 정합).
- **중복 금지**: SELECT admin은 profiles·listings에 이미 존재 → 재생성하지 않는다(멱등 drop을 쓰더라도 굳이 건드리지 않음). chat 두 테이블만 SELECT admin 신규.
- **비관리자 영향 없음(회귀 안전)**: 모든 신규 정책은 permissive + `is_admin()` 조건 → 비관리자에겐 평가 결과 false라 **아무 행도 추가로 열리지 않는다**. 기존 참여자/소유권 정책은 그대로 유지된다(회귀 0).

### 마이그레이션 적용 방식(기존 이력 기준)
- `list_migrations` 현황(라이브 확인): 0001·0002(+b/c/d)·0006·0004·0003(+b/c)이 모두 적용됨. 0003·0004·0006은 **Supabase MCP `apply_migration`** 으로 원격 직접 적용된 패턴 → 이 스토리도 **MCP `apply_migration(name="0005_admin_policies")`** 로 적용한다.
- 번호 갭(0005)은 architecture.md(L334)·0003/0006 헤더가 예약해 둔 자리 → 0005 사용이 설계 의도와 정합.
- 적용 후 `pg_policies`·`get_advisors(security)`로 **사실 검증**하고 결과를 Debug Log/Completion에 기록(5-1과 동일 규율).

### 테스트 표준(이 스토리)
- **DB 정책 검증(SQL 레벨)**: `pg_policies`로 신규 admin 정책 7개 존재·`{authenticated}`·`qual`에 `is_admin()` 포함 확인. `get_advisors(security)` 신규 경고 0건.
- **RLS 동작의 한계(명시)**: MCP 연결 롤은 RLS 우회(슈퍼유저급) → 실제 "관리자만 허용/비관리자 차단" 동작 재현은 인증 클라이언트가 필요. 정책 정의 존재로 갈음하고, 실제 동작 E2E는 **6-2~6-5(관리 화면)** 에서 관리자 로그인 클라이언트로 검증한다(5-1과 동일 입장).
- **라우트 가드 E2E(웹)**: Playwright MCP로 비로그인 `/admin`→`/login` 리다이렉트는 검증 가능. 관리자 로그인 후 진입은 시드 관리자 자격이 있으면 검증(없으면 한계로 사실 보고). 가드 코드는 1-4/1-5에서 이미 검증된 자산이므로, 본 스토리에선 회귀 점검 수준으로 충분.

### Project Structure Notes
- **신규 파일 1개**: `supabase/migrations/0005_admin_policies.sql`. 마이그레이션 단일 출처(`supabase/migrations/`) 유지(0001 헤더 명시).
- **코드(web) 변경 0**: 라우트 가드는 기존 자산 재사용. `(admin)/admin/page.tsx`의 자리표시 화면도 그대로(실 관리 기능은 6-2~6-5).
- 정책 네이밍 `<table>_<action>_admin`로 일관(기존 `*_admin`/`*_own`/`*_participant` 규약 연장).

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story-6.1 L635~649]
- [Source: _bmad-output/planning-artifacts/epics.md#Epic-6 L631~709 — FR22~25 관리 기능 범위]
- [Source: _bmad-output/planning-artifacts/epics.md L149 — "(admin) 라우트 가드 + 관리자 전권 교차 정책(0005_admin_policies)"]
- [Source: _bmad-output/planning-artifacts/architecture.md L199 — RLS 배치 원칙: 관리자 전권 교차 정책만 0005로 분리]
- [Source: _bmad-output/planning-artifacts/architecture.md L334 — 0005_admin_policies 파일 역할(FR22~25 전권 교차)]
- [Source: _bmad-output/planning-artifacts/architecture.md L397, L408, L412, L461 — 이중 방어선(proxy+layout+RLS)·admin 교차 정책]
- [Source: supabase/migrations/0001_profiles.sql L57~91 — is_admin() 헬퍼·profiles_select_admin·EXECUTE 권한]
- [Source: supabase/migrations/0002_listings.sql L94~118 — listings_select_admin·소유권 정책]
- [Source: supabase/migrations/0003_chat.sql L86, L117 — "관리자 삭제권은 0005에서" 명시]
- [Source: supabase/migrations/0006_readonly_role.sql L36~38 — drop-if-exists 멱등 패턴]
- [Source: web/src/proxy.ts, web/src/app/(admin)/layout.tsx, web/src/lib/auth/guard.ts — 라우트 가드 3종]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- `apply_migration(name="0005_admin_policies")` → `{"success":true}`
- `list_migrations` → `0005_admin_policies` 등록(version `20260623233045`)
- `pg_policies`(admin 정책 9개 = 기존 SELECT 2 + 신규 7): chat_messages_delete_admin·chat_messages_select_admin·chat_rooms_delete_admin·chat_rooms_select_admin·listings_delete_admin·profiles_delete_admin·profiles_update_admin(신규 7) + listings_select_admin·profiles_select_admin(기존). 전부 `{authenticated}`, `qual=is_admin()`; profiles_update_admin은 `with_check=is_admin()`.
- `get_advisors(security)` → 신규 경고 0건(기존 3건: extension_in_public(vector)·is_admin SECURITY DEFINER executable·leaked_password_protection — 전부 본 스토리 이전부터 존재, 무관)
- Playwright E2E: ① 비로그인 `/admin` → `/login?redirectedFrom=%2Fadmin` ② buyer `/admin` → `/`(home) ③ admin 로그인 후 `/admin` → "관리자 영역" 노출(헤더 role=관리자, admin@test.com)

### Completion Notes List

- **무엇을·왜**: 관리자에게만 운영 기능을 여는 두 겹의 잠금 중 "DB 잠금(2차 RLS)"을 채워 넣었다. 1차(웹 미들웨어 `proxy.ts`)와 2차 레이아웃 역할 확인(`requireRole(admin)`)은 이미 Epic 1에서 만들어져 있어 **코드 변경 없이 그대로 재사용**했고, 이 스토리는 여러 테이블을 가로지르는 **관리자 전권 RLS 정책**을 `0005_admin_policies.sql` 한 파일로 새로 만들었다. 비유하면, 관리자실 문은 이미 잠겨 있었고(웹 가드), 이번에 관리자실 안의 캐비닛들(회원·매물·채팅 데이터)에도 "관리자 키로만 열리는 자물쇠"를 DB 차원에서 달아준 셈이다.
- **신규 정책 7개**: profiles UPDATE(회원 정지 FR22)·DELETE(회원 삭제 FR22), listings DELETE(매물 삭제 FR23), chat_rooms SELECT/DELETE·chat_messages SELECT/DELETE(채팅 열람·삭제 FR25). 모두 `public.is_admin()`(0001의 SECURITY DEFINER 헬퍼) 판정 + `to authenticated` 한정.
- **중복 회피**: profiles·listings의 관리자 SELECT는 이미 0001·0002에 존재해 재생성하지 않았다(조회는 그대로, 이번엔 수정/삭제/채팅 권한만 보강).
- **회귀 안전**: 신규 정책은 permissive + is_admin() 조건이라 비관리자에겐 평가가 false → 추가로 열리는 행이 0. 기존 소유권(`*_own`)·참여자(`*_participant`) 정책은 그대로. 라이브 advisor 신규 경고 0건으로 확인.
- **검증 한계(명시)**: Supabase MCP 연결 롤은 슈퍼유저급이라 RLS를 우회하므로, "관리자만 허용/비관리자 차단"의 실제 행 차단 동작을 인증 클라이언트로 재현하진 않았다(5-1과 동일 입장). 정책 정의(qual/with_check) 존재로 갈음하고, 실제 동작은 6-2~6-5 관리 화면에서 관리자 로그인 클라이언트로 E2E 검증한다. 라우트 가드(AC#1·#2)는 Playwright로 세 분기(비로그인/비관리자/관리자) 실제 동작을 확인했다.

### File List

- `supabase/migrations/0005_admin_policies.sql` (신규)
- `_bmad-output/implementation-artifacts/6-1-admin-라우트-가드-admin-rls.md` (스토리 — 본 파일)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (epic-6 in-progress, 6-1 review)

## Change Log

- 2026-06-24: 스토리 6-1 컨텍스트 생성(ready-for-dev) — 라우트 가드는 Epic 1 기존 자산(신규 코드 없음), 실질 산출물은 `0005_admin_policies.sql`(관리자 전권 교차 RLS) 임을 명확화. (create-story)
- 2026-06-24: 관리자 전권 교차 RLS `0005_admin_policies` 작성·적용·검증(신규 정책 7개) + 라우트 가드 3분기 Playwright E2E 통과. 상태 review. (dev, story 6-1)
