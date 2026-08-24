---
title: '14.3 소유권 기반 판매 게이트'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
baseline_revision: '75b5b0cc325c256a35187bf31ff4b9bc9bc1d740'
final_revision: '27e9dd7'
---

<intent-contract>

## Intent

**Problem:** `/sell`(매물 등록·본인 매물 관리) 진입은 지금 `requireRole(USER_ROLE.SELLER)`로 막혀 있어 `role='seller'`가 아닌 로그인 사용자(예: 기존 buyer 계정, 14.2 이후 신규 가입자)는 홈으로 튕긴다. 이는 에픽 14의 목표(FR52: 로그인만 하면 누구나 사고팔 수 있다)와 정면으로 어긋난다.

**Approach:** `web/src/app/(user)/sell/layout.tsx`의 게이트를 `requireRole(SELLER)`에서 `requireUser()`(로그인 여부만 확인)로 교체한다. 매물 수정·삭제·구매완료는 이미 `listings` RLS(소유권 기반, `seller_id = auth.uid()`)로만 제한되어 있어 손댈 필요가 없다 — 사전 조사(RLS 정책·컴포넌트 코드 전수 확인)로 실측했다.

## Boundaries & Constraints

**Always:**
- `/sell` 접근은 로그인 여부만으로 결정한다(`requireUser()`) — `profiles.role` 값과 무관하게 통과시킨다.
- 매물 등록(INSERT)·수정(UPDATE)·삭제(DELETE)·구매완료(UPDATE status=sold)는 지금처럼 `listings` RLS(소유권)만으로 제한된 채 그대로 둔다 — 이 스토리는 그 정책을 하나도 건드리지 않는다.
- admin 게이트(`(admin)/layout.tsx`의 `requireRole(USER_ROLE.ADMIN)`)는 그대로 둔다(FR54, 관리자 축은 별개).
- 이미 `role='buyer'`·`role='seller'`인 기존 계정은 데이터 변경 없이 그대로 `/sell`에 진입 가능해야 한다(두 값을 차별하지 않는다).
- `web/src/proxy.ts:19`의 "역할(seller) 2차 집행은 ... requireRole" 주석은 이제 사실과 다르므로 정정한다(코드-주석 불일치 방지).

**Block If:**
- `listings` INSERT/UPDATE/DELETE RLS를 다시 조회했을 때 실제로 `role` 컬럼을 참조하는 조건이 발견되면(사전 조사와 다르면) → 완화 범위 재판단이 필요하므로 HALT(status: blocked).

**Never:**
- 신규 DB 마이그레이션 추가 — 이 스토리는 순수 app 계층(web) 변경이다.
- 회원가입 화면의 역할 선택 제거·가입 트리거 기본값 변경(Story 14.2 범위) — 건드리지 않는다. 14.3은 14.2보다 먼저 실행되며 14.2에 의존하지 않는다(에픽 컨텍스트 확정 순서).
- Flutter 앱의 판매 게이트·화면 로직 변경 — 에픽 범위가 명시적으로 web 한정이다(Flutter 쪽 role 미러링 갭의 DW 등재는 아직 안 됐다 — spec-14-2가 자기 Tasks에서 등재하기로 계획했을 뿐이며, spec-14-2는 이 시점에 아직 미구현이다(status: ready-for-dev). 14-3이 14-2보다 먼저 실행되는 순서이므로 이 스토리 시점에 등재가 안 돼 있는 것이 정상이다 — 정정: 2026-08-06 코드리뷰, 이전 "이미 등재" 서술은 사실과 달랐다).
- `profiles.role` 컬럼 값·CHECK 제약 변경(14.1이 이미 완화 완료, done).
- `USER_ROLE`·`ROLE_LABEL` 상수 구조 변경.
- DW-451(`requireUser()`에 `currentPath`/`redirectedFrom` 파라미터를 추가해 호출부 5곳 이상을 한 번에 고치는 작업) — 이 스토리는 기존 시그니처 그대로 `requireUser()`를 한 곳 더 호출할 뿐, 그 전면 리팩터는 하지 않는다(별개로 열려 있는 항목, 근거는 Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 비로그인 접근 | 세션 없음, `/sell` 접속 | `/login?redirectedFrom=/sell`로 리다이렉트(무변경) | No error expected |
| 기존 buyer 계정 접근 | `role='buyer'`로 로그인, `/sell` 접속 | 홈으로 튕기지 않고 매물 등록 화면이 렌더된다(FR52, 변경된 동작) | No error expected |
| 기존 seller 계정 접근 | `role='seller'`로 로그인, `/sell` 접속 | 매물 등록 화면이 렌더된다(기존과 동일 결과, 경로만 변경) | No error expected |
| 타인 매물 수정 시도 | A가 등록한 매물 id로 B가 `/sell/[id]/edit` 접속 | "본인 매물만" 안내와 함께 폼이 뜨지 않는다(RLS 무변경 회귀 없음) | 앱단 `maybeSingle()` null → 한국어 안내(기존 동작) |
| 타인 매물 삭제/구매완료 시도 | A가 등록한 매물에 B가 삭제/구매완료 요청 | 0행 응답 → 한국어 거부 안내(RLS 무변경 회귀 없음) | `listings_delete_own`/`listings_update_own` RLS가 0행으로 차단(기존 동작) |
| admin 접근 | admin 계정으로 `/admin` 접속 | 기존과 동일하게 접근 가능(무변경) | No error expected |

</intent-contract>

## Code Map

- `web/src/app/(user)/sell/layout.tsx` -- 이 스토리의 본체. `requireRole(USER_ROLE.SELLER)` → `requireUser()`로 교체, 관련 import·주석·`AppHeader` 호출 정리.
- `web/src/lib/auth/guard.ts` -- `requireUser()`/`requireRole()` 정의(읽기 전용, 기존 함수 재사용 — 함수 자체는 수정 없음).
- `web/src/proxy.ts:19` -- `/sell` 1차 게이트 설명 주석이 "역할(seller) 2차 집행"을 언급 — 정정 대상.
- `supabase/migrations/0002_listings.sql:103-116` -- `listings_insert_own`·`listings_delete_own` RLS가 이미 소유권 기반(`seller_id = auth.uid()`)이고, INSERT 정책 주석이 "역할(seller) 게이트는 앱/프록시 책임"이라고 명시함을 확인(읽기 전용 참고, 변경 없음).
  ⚠️ **UPDATE는 이 파일이 현행이 아니다**(3차 리뷰 실측): `listings_update_own`은 `supabase/migrations/0015_listings_update_not_sold.sql`이 drop 후 재생성해 `status <> 'sold'` 조건이 붙은 상태가 유효 정책이다. 또한 `listings`에는 `0005_admin_policies.sql`의 `listings_delete_admin`(관리자 DELETE, `is_admin()` 경유)도 있다 — listings의 유효 정책 집합은 이 세 파일에 흩어져 있다.
- `supabase/migrations/0002_listings.sql:94-95`(`listings_select_on_sale`) -- **타인의 `on_sale` 매물도 SELECT는 통과한다.** 그래서 `/sell/[id]/edit`에서 타인 매물 폼이 안 뜨게 막는 실주체는 RLS가 아니라 그 페이지의 앱측 `.eq('seller_id', ...)` 필터다(해당 파일이 이미 ⚠️로 경고하고 있다). 읽기 전용 참고, 변경 없음.
- `web/src/app/(user)/sell/page.tsx`, `[id]/edit/page.tsx`, `ListingActions.tsx` -- 이미 `seller_id` 앱측 필터 + RLS로 본인 매물만 다루고 있음을 확인(읽기 전용 참고, 변경 없음).
- `web/src/components/layout/AppHeader.tsx` -- `variant='consumer'`(기본값, `/sell`이 쓰는 분기)에서 `roleLabel` prop이 렌더되지 않는 죽은 값임을 확인(사전 조사, 변경 없음 — 아래 Design Notes 참고).
- `web/e2e/core-flows.spec.ts`(C5, C7), `web/e2e/write-flows.spec.ts`(E1·E3·E5, SELLER 계정 사용) -- 기존 회귀 스위트. 이 변경으로 깨지지 않음을 확인용으로 재실행한다(수정 대상 아님).
- `web/e2e/core-flows.spec.ts`(C8, 코드리뷰 patch 추가) -- 이 스토리의 핵심 신규 동작(role='buyer' 계정이 `/sell`에 도달) 자체를 검증하는 신규 회귀 케이스. C5·C7 재실행만으로는 "buyer가 실제로 통과하는지"를 아무도 자동 검사하지 않는다는 갭이 3개 독립 리뷰 레이어에서 공통으로 지적돼 추가했다.

## Tasks & Acceptance

**Execution:**
- `web/src/app/(user)/sell/layout.tsx` -- `import { requireRole } from '@/lib/auth/guard'`를 `import { requireUser } from '@/lib/auth/guard'`로, `requireRole(USER_ROLE.SELLER)` 호출을 `requireUser()`로 교체. 더 이상 쓰지 않게 되는 `USER_ROLE`·`ROLE_LABEL` import와 `AppHeader`에 넘기던 고정 `roleLabel={ROLE_LABEL[USER_ROLE.SELLER]}`를 제거한다(`/sell`이 이제 판매자 전용이 아니므로 그 라벨은 더 이상 사실이 아니다 — `account/page.tsx`가 이미 쓰는 패턴대로 `roleLabel`을 아예 넘기지 않는다). 파일 상단 주석(현재 "role=seller만 통과시킨다")도 소유권 기반 설명으로 정정한다 -- FR52·FR53 핵심 변경.
- `web/src/proxy.ts:19` -- "역할(seller) 2차 집행은 (user)/sell 레이아웃의 requireRole." 주석을 "로그인만 필요(2차 방어는 requireUser()) — 수정·삭제·구매완료는 listings RLS의 소유권 정책이 집행."로 정정 -- 코드-주석 불일치 방지.

**Acceptance Criteria:**
- Given 기존 `role='buyer'` 계정으로 로그인, when 프로필▾ → 내 매물 관리(`/sell`)를 클릭하면, then 홈으로 리다이렉트되지 않고 매물 등록 화면이 실제 브라우저에서 렌더된다(FR52)
- Given 비로그인 상태, when `/sell`에 접속하면, then `/login?redirectedFrom=/sell`로 리다이렉트된다(기존 동작 무변경, `core-flows.spec.ts` C5 재확인)
- Given A 계정이 등록한 매물, when B 계정이 그 매물의 수정 페이지(`/sell/[id]/edit`)에 직접 접속하면, then "본인 매물만 수정할 수 있습니다" 안내가 뜨고 폼은 노출되지 않는다(회귀 없음)
- Given admin 계정, when `/admin`에 접속하면, then 기존과 동일하게 접근 가능하다(`requireRole(ADMIN)` 무변경, `core-flows.spec.ts` C6·C7 재확인)
- Given 위 변경 후, when `web/e2e/write-flows.spec.ts`의 SELLER 계정 기반 등록·수정·구매완료 흐름(E1·E3·E5)을 재실행하면, then 전부 통과한다(회귀 없음)

## Design Notes

- **왜 RLS를 안 건드리나:** `supabase/migrations/0002_listings.sql`의 INSERT/UPDATE/DELETE 정책은 처음부터 `seller_id = auth.uid()`(소유권)만 검사했고, INSERT 정책 주석이 "역할(seller) 게이트는 앱/프록시 책임"이라고 명시한다. 즉 역할 제약은 DB가 아니라 오직 `sell/layout.tsx`의 `requireRole(SELLER)` 한 곳에만 있었다 — 그 한 곳만 바꾸면 FR52·FR53이 완성된다.
- **`roleLabel` prop을 제거하는 이유:** `AppHeader`는 `variant='consumer'`(기본값, `/sell`이 쓰는 분기)에서 `roleLabel`을 아예 렌더하지 않는다(`account/page.tsx`의 기존 주석이 이미 "기존 6개 호출부의 죽은 prop"이라고 지적). 지금까지는 죽은 값이라 안전했지만, 앞으로 `/sell`이 판매자 전용이 아니게 되면 "판매자"라는 값 자체가 틀린 서술이 된다 — 죽은 코드라도 틀린 서술을 남겨두지 않는다.
- **DW-451(redirectedFrom 시그니처 확장)을 지금 안 하는 이유:** 이 스토리는 `requireUser()`를 새 호출부 하나(`sell/layout.tsx`)에 추가할 뿐 함수 시그니처는 그대로 재사용한다. DW-451이 요구하는 건 `currentPath` 파라미터 추가 + 기존 호출부 5곳 이상을 한 번에 고치는 별도 작업이라, 판매 게이트를 소유권 기반으로 바꾸는 이 스토리의 범위를 넘어선다. 범위를 넓히지 않고 Never로 명시해 다음 사람이 "빠뜨렸나?"로 헷갈리지 않게 한다.
- **14.2보다 먼저 실행하는 이유:** 이 스토리는 14.1(role CHECK 완화, done)에만 의존하고 14.2(가입 트리거 기본값)에는 의존하지 않는다 — 순서를 뒤집지 않으면 "신규 가입자는 role 기본값을 받았지만 판매 게이트는 아직 seller만 통과"라는 중간 모순 상태가 생긴다(에픽 컨텍스트 2026-08-06 확정 사유).
- **admin 계정도 이제 `/sell`에 들어온다(의도된 결과):** `requireUser()`는 role을 아예 읽지 않으므로, 이전에 `requireRole(SELLER)`가 홈으로 튕기던 admin도 통과한다. 이는 Always의 "`profiles.role` 값과 무관하게 통과시킨다"가 곧바로 뜻하는 바이며, admin **게이트**(`(admin)/layout.tsx`)는 손대지 않았으므로 FR54와 충돌하지 않는다. admin이 매물을 등록하면 그 매물의 소유자는 admin 자신이고 `listings` RLS가 그대로 집행한다.
- **`/login?redirectedFrom=/sell`을 만드는 층은 proxy다(게이트가 아니다):** `guard.ts`의 `requireUser()`는 `redirect('/login')`만 하고 쿼리를 붙이지 않는다. 비로그인 접근에서 관측되는 `redirectedFrom`은 `proxy.ts`가 1차에서 붙인 것이다(그래서 AC2·매트릭스 1행은 만족되지만, 그 근거는 이 스토리가 바꾼 층이 아니다). 이 비대칭이 DW-451이 열려 있는 이유다.
- **Block If 해제 근거(2026-08-06 3차 리뷰에서 재실측·정정):** 이전 근거는 `grep -n "role" supabase/migrations/0002_listings.sql` → 0건이었는데, 그 검색은 구조적으로 두 가지를 못 본다 — (a) **뒤 마이그레이션이 교체한 정책**: `listings_update_own`은 `0015_listings_update_not_sold.sql`이 drop 후 재생성해 현행 조건이 `auth.uid() = seller_id and status <> 'sold'`다(0002판은 더 이상 유효 정책이 아니다). (b) **함수를 경유한 간접 role 참조**: `0005_admin_policies.sql`의 `listings_delete_admin`은 `using (public.is_admin())`이고 `is_admin()` 본문(`0001_profiles.sql`)이 `where id = auth.uid() and role = 'admin'`이다. 즉 **listings의 DELETE 정책 하나는 실제로 role을 참조한다.**
  그럼에도 Block If는 발동하지 않는다. 이 조건의 목적은 "**seller 자격**이 DB에 박혀 있으면 앱 게이트만 풀어선 안 된다"를 잡는 것인데, 걸린 것은 관리자에게 **추가 권한을 주는** 정책이고 Always가 admin 축(FR54) 보존을 명시하고 있다. 소유자를 제한하는 세 정책(`listings_insert_own`·`listings_update_own`(0015판)·`listings_delete_own`)은 모두 `seller_id = auth.uid()`만 보며 role을 읽지 않는다.
  ⚠️ **다음에 이 조건을 재검증할 사람에게**: 마이그레이션 파일 하나를 grep하지 말고, 전 마이그레이션을 적용한 DB에서 `select policyname, qual, with_check from pg_policies where tablename='listings'`를 읽고 참조된 함수 본문까지 펼쳐라. 파일 텍스트는 유효 정책이 아니다.
- **등록(INSERT)은 RLS가 제한하지 않는다(3차 리뷰 정정):** `listings_insert_own`은 `with check (auth.uid() = seller_id)`뿐이라 **남의 명의로 등록하는 것만** 막는다 — "누가 등록할 수 있나"에 대한 유일한 제한은 이 스토리가 바꾼 `/sell` 로그인 게이트다. 소유권 RLS가 실제로 타인 행을 0행으로 막는 구간은 **수정·삭제·구매완료(UPDATE/DELETE)**다. 2차 리뷰까지의 주석·학습문서가 이 둘을 뭉뚱그려 "등록·수정·삭제를 RLS 소유권이 정한다"고 서술했는데, 그대로 믿으면 "DB가 받쳐주니 게이트를 풀어도 된다"는 잘못된 안심으로 이어진다(DW-669가 그 오해의 구체 사례다).
- **계약 정본은 원래부터 "로그인만"이었다:** `docs/conventions.md` §8(접근 게이트 계약, FR58)은 `/sell`을 "행동 = 로그인 필수"로만 분류하고 판매자 역할을 요구한 적이 없다. 즉 이번 변경은 계약을 바꾼 게 아니라 **계약보다 엄격했던 코드를 계약에 맞춘 것**이다 — 그래서 `conventions.md`는 수정하지 않는다.
- **`0002_listings.sql`의 INSERT 정책 주석은 이제 낡았다(고치지 않음):** 그 주석("역할(seller) 게이트는 앱/프록시 책임")은 이 스토리 이전 시점의 사실을 적은 것이고, 지금은 그런 역할 게이트가 앱에 더 이상 존재하지 않는다. 그래도 in-place로 고치지 않는다 — `docs/conventions.md` §9.1의 전진(forward-only) 마이그레이션 정책상 이미 적용된 마이그레이션 파일의 주석을 지금 와서 고치는 것은 "과거 시점의 기록"과 "현재 동작"을 구분하지 못하게 만든다. 이 주석은 **작성 당시의 이력**으로 읽어야 하며, 현재 게이트 동작의 출처는 아니다(현재 동작은 `sell/layout.tsx`·`proxy.ts` 주석과 이 스펙이 최신 출처).

## Verification

**Commands:**
- `npx tsc --noEmit` -- expected: exit 0
- `npm run lint` -- expected: 통과
- `npm test`(vitest) -- expected: 기존 전체 통과(회귀 없음)
- `npm run test:e2e`(= `npx playwright test`, **파일을 골라 돌리지 않는다**) -- expected: 기존 전체 통과(회귀 없음, 로컬 Supabase 필요).
  > ⚠️ 2026-08-06 후속 리뷰에서 정정: 원래 이 자리는 `core-flows.spec.ts write-flows.spec.ts`만 지정했는데, 그 두 파일은 이 변경의 회귀를 **구조적으로 볼 수 없는** 부분집합이었다. `/sell`을 여는 스펙은 `nav-and-hero.spec.ts`에도 있었고(B8), 거기 남아 있던 옛 동작 단언을 부분 실행이 놓쳤다. **라우트 게이트를 바꾸는 변경은 전량 실행이 아니면 검증이 아니다.**

**Manual checks (if no CLI):**
- 실제 브라우저로 기존 buyer 계정(`buyer@test.com`) 로그인 → 프로필▾ → 내 매물 관리 클릭 → `/sell`이 실제로 열리는지 확인(회귀 스위트엔 없는 신규 확인 지점, AC1).

## Verification Evidence

실제로 돌려 확인한 기록(CLAUDE.md B4).

- `npx tsc --noEmit` → exit 0(구현 세션·오케스트레이터 세션 양쪽에서 재확인).
- `npm run lint` → 경고·에러 0.
- `npm test`(vitest) → 33개 파일 308개 테스트 전부 통과(구현 세션·오케스트레이터 세션 양쪽에서 재확인, 회귀 없음).
- `npx playwright test core-flows.spec.ts write-flows.spec.ts`(로컬 Supabase, desktop 프로젝트) → C2(매물 목록 필터) 1건 실패, 나머지 통과. C2 실패는 변경 전 코드(`git stash`)에서도 동일하게 재현되는 기존 시드 데이터 드리프트로 확인됨 — 이 스토리와 무관.
  > ⚠️ 2026-08-06 후속 리뷰 정정: 이전 서술("12건 **전부** 통과")은 같은 줄에서 C2 실패를 인정하면서 "전부 통과"라고 쓴 자기모순이었고, 열거한 케이스 수(9건)와 적힌 숫자(12건)도 맞지 않았다. 손으로 센 숫자 대신 **러너가 출력한 통과/실패 줄과 실패 케이스**를 적는다.
- **AC1(신규 확인 지점, 회귀 스위트에 없음)** — 오케스트레이터 세션이 직접 브라우저로 재현: `buyer@test.com`(role='buyer') 로그인 → `/sell` 진입 → 홈으로 튕기지 않고 "매물 등록" 폼이 렌더됨을 스냅샷으로 확인.
- **비로그인 리다이렉트** — `curl -s -o /dev/null -w '%{http_code} -> %{redirect_url}' http://localhost:3000/sell` → `307 -> http://localhost:3000/login?redirectedFrom=%2Fsell`(무변경 확인).
- **I/O 매트릭스 4행("타인 매물 수정 시도")** — 구현 산출물에는 이 행을 실제로 검증한 기록이 없어(Matrix Test Audit 갭) 오케스트레이터 세션이 직접 재현: buyer 로그인 상태로 seller 소유 on_sale 매물의 `/sell/[id]/edit` URL에 직접 접속 → "매물을 찾을 수 없거나 접근 권한이 없습니다. 본인 매물만 수정할 수 있습니다." 안내만 뜨고 폼은 렌더되지 않음을 스냅샷으로 확인(AC3).
- **I/O 매트릭스 5행("타인 매물 삭제/구매완료 시도")** — 마찬가지로 검증 기록이 없어 직접 재현. `ListingActions.tsx`의 실제 UPDATE/DELETE 조건과 동일한 조건으로, buyer의 세션을 흉내 낸 psql 트랜잭션(`set local role authenticated; set local request.jwt.claim.sub = '<buyer-uuid>'`)에서 seller 소유 매물에 `update ... set status='sold' where status='on_sale'` → `UPDATE 0`, `delete from listings where id=...` → `DELETE 0`(둘 다 RLS로 0행, 트랜잭션은 `rollback`으로 정리해 데이터 무변경).
- ⚠️ **위 tsc/lint/vitest/Playwright 통과 건수는 모두 로컬 1회성 실행 결과다 — 이 브랜치(`test/bmad-loop`)에서는 CI가 아예 돌지 않는다.** `migration-gate.yml`은 DW-661이, `tests.yml`(api-db·web 잡, Story 14.1이 추가한 15건 포함)은 DW-664가 이미 등재한 대로 `develop`·`main`·PR에만 걸려 있어 이 브랜치의 push로는 트리거되지 않는다(재조사 불필요 — 두 항목이 원인·해결 시점까지 문서화해 뒀다). 즉 위 통과 기록은 "CI가 초록"이 아니라 "이 세션이 로컬에서 한 번 실행해 봤더니 통과했다"는 뜻으로 읽어야 한다.

### 2026-08-06 후속 리뷰 패스에서 실제로 돌린 것

- `npx tsc --noEmit` → exit 0 · `npm run lint` → 출력 없음(경고·에러 0) · `npm test`(vitest) → 33개 파일 308건 전부 통과.
- **`npx playwright test`(전량, `E2E_PORT=3021`, 로컬 Supabase + 빌드서버)** → **58 passed / 3 failed / 86 skipped**(86 skip은 desktop 전용 케이스가 tablet·mobile 프로젝트에서 건너뛴 것으로 설계된 동작). 이 스토리의 두 케이스 **B8·C8은 통과**.
- 실패 3건은 **전부 이번 변경과 무관한 선재 실패임을 기준 커밋(`75b5b0c`)에서 재현해 확인**했다(추측이 아니라 실행): 워킹트리를 stash한 뒤 `git checkout 75b5b0c -- web/`으로 되돌려 돌린 결과 — `image-fallback.spec.ts` 2건("abort 실험이 한 번도 안 걸렸음") **동일 실패**, `core-flows.spec.ts` C2(매물 목록 검색·필터) **동일 실패**. 이후 `git checkout HEAD -- web/` + `git stash pop`으로 원복 확인.
- **B8이 실제로 red였음을 직접 확인**(검사를 "만들었다"가 아니라 "잡는다"를 증명, CLAUDE.md B4): 고치기 전 B8(`buyer가 /sell 접근하면 홈으로`)을 현재 코드에 그대로 되돌려 실행 → **1 failed**. 수정본을 복원해 다시 실행 → **B8·C8 2 passed**.
- **Block If 해제 근거**: `grep -n "role" supabase/migrations/0002_listings.sql` → 매치 0건. `listings`의 INSERT/UPDATE/DELETE 정책 어디에도 `role` 참조가 없어 HALT 조건은 발동하지 않는다.

## Spec Change Log

## Review Triage Log

### 2026-08-06 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 2, low 5)
- defer: 0
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[low]` `[patch]` `web/src/app/(user)/sell/page.tsx:1-2`·`web/src/app/(user)/sell/[id]/edit/page.tsx:3`의 헤더 주석이 여전히 "역할 게이트는 requireRole(seller)이 담당"이라고 서술 — sell/layout.tsx·proxy.ts와 동일하게 "게이트는 requireUser()로 로그인만 확인, 본인 매물 여부는 listings RLS 소유권 정책이 집행"으로 정정
  - `[medium]` `[patch]` 이 스토리의 핵심 신규 동작(role='buyer' 계정이 `/sell`에 도달)을 검증하는 자동화 테스트가 전무(3개 독립 레이어가 공통 지적) — `core-flows.spec.ts`에 C8 신규(읽기 전용, buyer 로그인 → `/sell` → 매물 등록 폼 렌더 확인) 추가
  - `[low]` `[patch]` Verification Evidence가 이 브랜치에서 CI가 안 도는 사실(DW-661·DW-664 기존 등재)을 안 밝혀 "308건 통과"가 상시 게이트처럼 읽힘 — 로컬 1회성 실행이라는 caveat 추가
  - `[low]` `[patch]` epic-14-context.md 재생성 과정에서 이전 리뷰 패스가 실측 확인한 "FR61 원문은 필터 정리라 쓰지만 실제로는 필터 UI가 없다(라벨만 있다)" 경고가 누락됨 — 복원(Epic 15/Story 15.3 재조사 낭비 방지)
  - `[medium]` `[patch]` spec-14-3 자신의 Never 절이 "Flutter role 미러링 갭은 spec-14-2가 이미 DW로 등재"라고 주장했으나 실측(deferred-work.md grep) 결과 사실이 아님(그런 등재 없음, spec-14-2는 아직 미구현) — "아직 등재 안 됐고 spec-14-2 자기 Tasks에서 등재할 계획일 뿐"으로 정정
  - `[low]` `[patch]` `web/src/app/(user)/chat/page.tsx:109`의 빈 채팅목록 문구가 `role === SELLER`로 분기 — 이 스토리로 buyer 계정도 실제 판매자가 될 수 있어 문구가 부정확해질 수 있음 — 역할 중립 문구("아직 채팅방이 없습니다.") 하나로 통일
  - `[low]` `[patch]` `supabase/migrations/0002_listings.sql`의 INSERT 정책 주석("역할(seller) 게이트는 앱/프록시 책임")이 이제 낡았으나 forward-only 정책상 in-place 수정 불가 — spec Design Notes에 "이력으로만 읽는다"는 한 줄 명시
- rejected: edge-case-hunter가 제기한 "auth 계정은 있으나 profiles row가 없는 사용자" 우려(low confidence 자체 표기) — requireUser()가 애초부터 profiles 존재를 확인하지 않는 기존 패턴이고(/account·/admin/members 등 기존 호출부와 동일), 이 스토리가 새로 만든 위험이 아님 · epic-14-context.md 목표 섹션에서 "경쟁 서비스도 역할을 안 나눈다"는 근거 문장이 짧아진 것(compile-epic-context 스킬 자체가 "간결하게" 원칙을 명시, 사실관계 오류 아님) · 가입 화면(signup)의 구매자/판매자 선택이 이제 무의미해진 것(이미 커밋 75b5b0c와 epic-14-context "스토리 간 의존" 섹션이 이 전환기 상태를 사용자 명시 결정으로 충분히 문서화, 이 스토리 스펙에 중복 서술 불필요)

### 2026-08-06 — Review pass (후속)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 1, low 6)
- defer: 4: (high 0, medium 2, low 2)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` `web/e2e/nav-and-hero.spec.ts:156`의 기존 테스트 B8이 **이 스토리가 삭제한 옛 동작**("buyer가 `/sell` 접근하면 홈으로")을 그대로 단언한 채 남아 있었다 — 신규 C8과 같은 계정·같은 경로에 대해 정반대를 단언하므로 `npm run test:e2e` 전량은 red였다. 이전 패스의 검증이 `core-flows`·`write-flows` 두 파일만 돌려 구조적으로 이 파일을 볼 수 없었던 것이 원인. B8을 새 동작(매물 등록 화면 렌더 + `/sell` 유지)으로 뒤집고, 고치기 전 상태로 red·수정 후 green을 각각 실행해 확인
  - `[medium]` `[patch]` C8이 전제(`buyer@test.com`의 `profiles.role`이 실제로 `'buyer'`)를 주석으로만 주장하고 단언하지 않아, 시드·가입 트리거가 바뀌면 "로그인 사용자가 `/sell`에 간다"로 조용히 약해지면서도 계속 초록일 수 있었다 — 같은 파일 C4가 이미 쓰는 `runPsql` 전제 고정 관례로 DB에서 실측해 단언. 아울러 `goto` 직후 pathname부터 읽던 순서를 "화면 렌더 대기 → pathname 확인"으로 바꿔, 아직 끝나지 않은 리다이렉트를 통과로 보던 약한 단언을 보강
  - `[low]` `[patch]` `web/src/app/(user)/chat/page.tsx:45`의 새 주석이 `role`을 "roleLabel 계산에 쓴다"고만 적어 죽은 경로를 살아 있는 것처럼 서술 — 그 `roleLabel`이 `AppHeader`의 consumer 분기에서 렌더되지 않는다는 사실과 추적 중인 장부 항목(DW-453)을 함께 명시
  - `[low]` `[patch]` `docs/learning/06-file-reference.md:177`·`docs/learning/04-web-frontend.md:69`가 여전히 "`(user)/sell/layout.tsx` = 판매자 역할 게이트(`requireRole(seller)`)"라고 가르침 — 이전 패스의 주석 정정 스윕이 `web/src`만 grep해 문서를 놓쳤다. 소유권 기반 설명으로 정정
  - `[low]` `[patch]` `epic-14-context.md`의 FR61 경고 복원이 절반만 됐다 — 두 번째 항목("이 울타리가 '그 파일을 열지 말라'는 뜻은 아니다")이 여전히 빠져 있어, 정작 그 오해를 막으려고 쓴 문장이 사라진 상태였다. 복원
  - `[low]` `[patch]` `## Verification`의 Playwright 명령이 파일 2개만 지정 → 전량(`npm run test:e2e`)으로 교체하고 "라우트 게이트 변경은 전량 실행이 아니면 검증이 아니다"를 명시. 함께 Verification Evidence의 자기모순 수치("12건 **전부** 통과"라고 쓰면서 같은 줄에서 C2 실패를 인정, 열거한 케이스는 9건)를 러너 출력 기준으로 정정
  - `[low]` `[patch]` 잔여 리스크 (3)의 "`develop`/`main`으로 병합돼 CI가 도는 시점부터 실질화된다"가 사실이 아님 — `tests.yml`이 돌리는 잡은 api·api-db·web(lint+vitest)·app 4개뿐이고 **Playwright 잡 자체가 어느 브랜치에도 없다**(같은 워크플로 주석이 로컬 전용임을 명시). 정정
  - `[low]` `[patch]` Design Notes에 네 가지 근거 누락 — (a) `requireUser()`가 role을 안 읽으므로 **admin도 이제 `/sell`에 들어온다**는 의도된 귀결(Always의 "role 값과 무관하게 통과"가 곧바로 뜻하는 바, admin 게이트는 무변경이라 FR54와 무충돌) (b) `redirectedFrom`을 붙이는 층은 `requireUser()`가 아니라 `proxy.ts`라는 사실(DW-451이 열려 있는 이유) (c) Block If를 해제한 실제 grep 결과 (d) `docs/conventions.md` §8이 원래부터 `/sell`을 "로그인 필수"로만 규정했으므로 이번 변경은 **계약보다 엄격했던 코드를 계약에 맞춘 것**이라는 점(그래서 계약 문서는 수정하지 않는다)
- deferred: 장부에 신규 4건 등재(기존 항목은 지시대로 일절 수정하지 않음) — `DW-668` Flutter 앱이 아직 역할 게이트라 같은 계정이 web에선 팔고 앱에선 차단됨(에픽 범위가 web 한정이라 코드는 안 고침) · `DW-669` 정지(`suspended`) 회원의 판매를 게이트도 RLS도 막지 않음(이전 게이트도 role만 봤으므로 선재) · `DW-670` `profiles` 행 없는 로그인 사용자의 등록이 FK 오류(23503) 한국어 매핑 누락으로 정체불명 문구가 됨 · `DW-671` 라우트 게이트를 바꿔도 E2E 전량 실행을 강제하는 장치가 없음(이번 B8 사고의 구조적 원인)
- rejected: DW-451(`requireUser()` 시그니처 확장)·DW-453(죽은 `roleLabel` prop 정리) 두 기존 항목의 트리거가 이 스토리에서 발화했다는 지적 — 실재하는 사실이나 **이 실행의 지시가 기존 장부 항목의 수정·재개를 금지**해(오케스트레이터 소유) 이 세션이 처리할 수 없다, 보고로만 올린다 · "admin의 `/sell` 진입을 막아야 한다"는 제안 — Always가 "`profiles.role` 값과 무관하게 통과시킨다"고 명시하므로 막는 것이 오히려 계약 위반, Design Notes에 의도된 귀결로 기록하는 선에서 그침 · `conventions.md` §8에 `/sell` 2차 게이트 규칙을 추가하라는 제안 — §8은 이미 `/sell`을 "행동 = 로그인 필수"로 규정하고 판매자 역할을 요구한 적이 없어 계약 변경이 불필요 · `roleLabelFallback.test.ts`의 하한선(`>= 9`)이 낡았다는 지적 — 실측 사이트 12곳이라 이번 삭제로 깨지지 않음 · 잔여 아티팩트 서술이 `sprint-status.yaml`도 커밋 안 됐음을 빠뜨렸다는 지적 / `sprint-status.yaml`은 `done`인데 스펙은 `in-review`라는 불일치 — 둘 다 이번 패스의 정상 종료·커밋으로 해소 · `epic-14-context.md` 재생성이 경쟁사 리서치 근거 문장을 줄였다는 지적 — 이전 패스에서 같은 근거로 이미 기각(컴파일 스킬이 "간결하게"를 명시, 사실관계 오류 아님)

### 2026-08-06 — Review pass (3차)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 3, low 3)
- defer: 5: (high 0, medium 3, low 2)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[high]` `[patch]` `web/src/app/(user)/sell/[id]/edit/page.tsx:4` — 2차 패스가 새로 넣은 주석("본인 매물 여부는 listings RLS의 소유권 정책이 집행한다")이 **같은 파일 9-11행의 기존 ⚠️ 경고와 정면 모순**이었다. 그 경고는 "RLS만으로는 부족: SELECT 정책이 on_sale ∪ own ∪ admin의 OR 결합이라 seller_id 필터가 없으면 남의 on_sale 매물도 읽힌다"고 못박고 있고, 마이그레이션을 직접 열어 `listings_select_on_sale`(0002:94-95)이 실재함을 확인했다. 새 주석을 믿고 44행의 `.eq('seller_id', ...)`를 "RLS가 하니 중복"이라 지우면 타인의 판매중 매물 수정 폼이 그 사람의 값으로 채워진 채 열린다. 주석을 "폼 노출을 막는 것은 앱측 필터이고 RLS는 그 뒤의 UPDATE/DELETE만 0행으로 막는다"로 정정
  - `[medium]` `[patch]` `web/src/app/(user)/sell/layout.tsx`·`docs/learning/04-web-frontend.md`가 "등록(INSERT)·수정·삭제를 listings RLS의 소유권이 제한한다"고 뭉뚱그렸으나, `listings_insert_own`은 `with check (auth.uid() = seller_id)`뿐이라 **남의 명의 등록만** 막는다(정책 본문 직접 확인) — "누가 등록할 수 있나"의 유일한 제한은 이 스토리가 바꾼 로그인 게이트다. 그대로 두면 "DB가 받쳐주니 게이트를 풀어도 된다"는 잘못된 안심을 남긴다(DW-669가 그 오해의 구체 사례). 등록과 수정·삭제를 나눠 서술
  - `[medium]` `[patch]` Block If 해제 근거(`grep -n "role" 0002_listings.sql` → 0건)가 구조적으로 두 가지를 못 봤다 — (a) `listings_update_own`은 `0015_listings_update_not_sold.sql`이 drop 후 재생성해 0002판이 현행이 아니고, (b) `0005_admin_policies.sql`의 `listings_delete_admin`이 `is_admin()`(본문에 `role = 'admin'`)을 경유해 **실제로 role을 참조한다**. 세 마이그레이션을 직접 열어 확인했다. 결론(HALT 아님)은 유지된다 — 걸린 것은 관리자에게 추가 권한을 주는 정책이고 Always가 admin 축 보존을 명시하므로. 근거 서술과 Code Map을 정정하고, 재검증 방법을 "파일 grep"이 아니라 "적용된 DB의 `pg_policies` 조회 + 참조 함수 본문 전개"로 명시
  - `[medium]` `[patch]` `web/src/app/(user)/chat/page.tsx` 빈 채팅목록 문구 — 1차 패스가 역할 분기를 없애면서 **다음 행동 안내까지 함께 삭제**해(옛 문구 둘 다 "문의하기를 눌러보세요"/"문의가 들어오면 생깁니다"를 담고 있었다) 빈 화면에서 사용자가 갈 곳을 잃었다. 없앨 대상은 역할 분기였지 안내가 아니다. 두 역할 모두에게 참인 한 문장으로 안내를 복원
  - `[low]` `[patch]` `docs/learning/04-web-frontend.md:48` 라우트 트리가 여전히 `"/sell" 매물 등록·관리 (판매자)` — 2차 패스가 같은 파일 69행은 고쳤으나 21줄 위 트리는 놓쳤다(`requireRole` 심볼로 스윕해 트리엔 안 걸렸다). 트리는 그 절에서 먼저 읽는 지도라 정정 효과를 무력화한다
  - `[low]` `[patch]` `docs/learning/06-file-reference.md:176` — 2차 패스가 고친 177행 **바로 위 줄**이 `/sell 판매자 내 매물 목록`으로 남아 두 줄이 서로 모순됐다. 겸사 실제와도 달랐다(그 페이지는 등록 폼 + 내 매물 목록)
  - `[low]` `[patch]` `web/e2e/core-flows.spec.ts` C8이 role 전제는 `buyer@test.com` 리터럴로 검사하면서 로그인은 `login(page)` 기본값(`SEED_USER`)으로 한다 — 상수를 다른 계정으로 바꾸면 "검사한 계정"과 "실제 구동 계정"이 갈라진 채 초록이 된다. 2차 패스가 이 테스트에 전제 고정을 넣은 취지 그대로, 계정을 `SEED_USER`에서 읽도록 통일
- deferred: 장부에 신규 5건 등재(기존 항목은 지시대로 일절 수정하지 않음) — `DW-672` `/sell/[id]/edit`의 타인 매물 차단 실주체인 앱측 `seller_id` 필터를 지키는 검사가 없음 · `DW-673` role='buyer' 계정의 실제 **등록**(write)이 무검사(C8은 렌더까지, write-flows는 전부 seller 계정) · `DW-674` 유일한 방어선으로 승격된 `listings` 소유권 RLS 자체에 반복 실행 검사가 없음 · `DW-675` "admin도 `/sell`에 들어온다"는 의도된 결과 선언이 무검사 · `DW-676` `/account`가 아직 "역할: 구매자"를 실제 렌더
- rejected: `chat/page.tsx`의 `profiles` 조회가 죽은 코드라는 지적 — `role`은 여전히 `roleLabel` 계산에 쓰이고 그 prop이 죽은 것은 6개 페이지 공통의 **선재** 문제로 DW-453이 이미 추적 중이라, 이 diff가 만든 고아가 아니다(CLAUDE.md A3) · B8이 C8의 약한 중복이고 nav 스위트에 있다는 지적 — 시드가 바뀌면 C8이 빨갛게 실패해 알 수 있고 중복 자체는 무해 · `roleLabelFallback.test.ts` 화이트리스트가 1개만 남아 언젠가 빈 배열이 될 수 있다는 지적 — 실측 12개 사이트가 남아 있고 하한선 검사가 별도로 있다 · `review_loop_iteration`·`Spec Change Log`가 패스 수와 안 맞는다는 지적 — 워크플로 엔진이 소유하는 필드다 · `conventions.md` §8에 소유권 규칙을 추가하라는 제안 — 2차 패스가 이미 기각(§8은 게이트 계약이고 `/sell`을 "로그인 필수"로 규정한 것이 지금도 정확) · `0002_listings.sql` INSERT 주석이 낡았다는 지적 — 2차 패스가 forward-only 근거로 처리 완료 · E2E가 CI에 없다·이 브랜치에서 CI가 안 돈다는 지적 — DW-671·DW-664·DW-661이 이미 등재 · signup의 역할 선택이 무의미해졌다는 지적 — Story 14.2 범위, 두 차례 기각

## Auto Run Result

_2026-08-06 **3차** 리뷰 패스 기준으로 전면 갱신했다(이전 실행의 결과 서술은 이 절이 대체한다 — 두 벌을 남기면 어느 쪽이 최신인지 알 수 없다)._

**요약**: `/sell`(매물 등록·본인 매물 관리) 진입 게이트를 `requireRole(USER_ROLE.SELLER)`(role='seller'만 통과)에서 `requireUser()`(로그인 여부만 확인)로 교체했다. 코드 본체는 그 한 줄이고, 나머지는 그 변경으로 **거짓이 된 서술**을 따라가며 고친 것이다. 세 번의 리뷰 패스에서 총 22건을 패치했다 — 1차 7건(형제 파일 주석, 회귀 테스트 부재, 스펙의 사실 오류), 2차 8건(**high 1**: 삭제된 옛 동작을 단언한 채 남아 E2E 전량을 red로 만들던 기존 테스트 B8), 3차 7건(**high 1**: 아래).

**3차 패스가 잡은 핵심**: 2차 패스가 "RLS 소유권이 집행한다"는 설명을 여러 파일에 퍼뜨렸는데, **그 설명이 DB의 실제 동작과 두 곳에서 어긋났다.** (1) `/sell/[id]/edit`에서 타인 매물 폼이 안 뜨는 이유는 RLS가 아니라 앱측 `seller_id` 필터다 — SELECT 정책이 타인의 판매중 매물을 허용하기 때문이고, 정작 그 파일이 ⚠️로 그렇게 경고하고 있는데 새 주석이 바로 위에서 반대로 말하고 있었다. (2) 등록(INSERT) 정책은 "남의 명의 등록"만 막을 뿐 "누가 등록하나"는 제한하지 않는다. 두 서술을 그대로 두면 다음 사람이 "DB가 받쳐준다"고 믿고 앱측 방어를 지우거나 게이트를 더 풀 수 있다.

**변경 파일**(누적):
- `web/src/app/(user)/sell/layout.tsx` — 게이트 교체(스토리 본체), 죽은 `roleLabel` prop·미사용 import 제거. 3차 patch: 등록(INSERT)과 수정·삭제(UPDATE/DELETE)를 나눠 서술 — RLS가 실제로 막는 구간이 다르다.
- `web/src/app/(user)/sell/[id]/edit/page.tsx` — 1차 patch: stale 주석 정정. **3차 patch(high)**: 그 정정이 같은 파일의 기존 ⚠️ 경고와 모순됐던 것을 바로잡음.
- `web/src/proxy.ts` — `/sell` 게이트 설명 주석 정정.
- `web/src/app/(user)/sell/page.tsx` — 1차 patch: stale `requireRole(seller)` 주석 정정.
- `web/src/lib/__tests__/roleLabelFallback.test.ts` — `roleLabel` 제거로 깨지는 화이트리스트 기대값 갱신.
- `web/src/app/(user)/chat/page.tsx` — 1차 patch: 빈 채팅목록 문구의 역할 분기 제거. 2차 patch: 주석 정정. 3차 patch: 그 과정에서 함께 사라졌던 **다음 행동 안내**를 역할 중립 문장으로 복원.
- `web/e2e/core-flows.spec.ts` — 1차 patch: C8 신규. 2차 patch: 전제를 psql로 실측 단언 + 렌더 대기 순서 보강. 3차 patch: 계정을 리터럴 대신 `SEED_USER` 상수에서 읽도록 통일.
- `web/e2e/nav-and-hero.spec.ts` — **2차 patch(high)**: 기존 B8을 새 동작으로 뒤집음.
- `docs/learning/04-web-frontend.md`, `docs/learning/06-file-reference.md` — 2차 patch: "sell 레이아웃 = 판매자 역할 게이트" 서술 정정. 3차 patch: 그 스윕이 놓친 **바로 옆 줄** 2곳(라우트 트리의 `(판매자)`, 파일 표의 `판매자 내 매물 목록`)까지 정정 + 등록/수정 비대칭 명시.
- `_bmad-output/implementation-artifacts/epic-14-context.md` — 재컴파일 + 유실된 FR61 경고 복원.
- `_bmad-output/implementation-artifacts/deferred-work.md` — 2차 defer 4건(DW-668~671) + 3차 defer 5건(DW-672~676) 신규 등재. **기존 항목은 지시대로 일절 수정하지 않았다.**
- `_bmad-output/implementation-artifacts/spec-14-3-소유권-기반-판매-게이트.md` — 이 스펙(3차 patch로 Block If 근거·Code Map의 낡은 정책 인용 정정).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 이 스토리를 `done`으로 표시.

**리뷰 결과**: 3차도 4개 레이어(blind-hunter·edge-case-hunter·verification-gap·intent-alignment)를 병렬 실행. intent_gap 0 · bad_spec 0 · **patch 7(high 1, medium 3, low 3, 전부 적용)** · defer 5(장부 신규 등재) · reject 8. 레이어가 올린 주장은 그대로 받지 않고 **마이그레이션·컴포넌트·테스트 파일을 직접 열어 실측한 뒤** triage했다 — 그 과정에서 "chat의 profiles 조회가 이 변경이 만든 고아"라는 주장은 사실이 아님을 확인해 기각했다(`role`은 여전히 `roleLabel` 계산에 쓰이고, 그 prop이 죽은 것은 DW-453이 추적 중인 선재 문제다).

**후속 리뷰 권고**: `true` — 이번 패스의 patch에 **high 1건**이 포함되어 규칙상 자동 확정(점수식으로도 3×3+1×3=12 ≥ 5). 다만 성격이 달라졌다: 1·2차의 high는 "코드/테스트가 실제로 깨져 있었다"였고, 3차의 high는 "설명이 DB 동작과 어긋났다"다. 남은 위험도 코드가 아니라 **검사 부재** 쪽으로 옮겨갔다(DW-672~675).

**검증 수행**(전부 이번 세션이 직접 실행·관찰):
- `npx tsc --noEmit` → exit 0 · `npm run lint` → 출력 없음(경고·에러 0) · `npx vitest run` → 33개 파일 308건 전부 통과.
- **`npx playwright test` 전량**(`E2E_PORT=3022`, 로컬 Supabase 컨테이너 + 운영 빌드 서버) → **58 passed / 3 failed / 86 skipped**. 스펙이 못박은 대로 파일을 골라 돌리지 않고 전량 실행했다.
- 실패 3건(`image-fallback` 2건, `core-flows` C2)은 **2차 패스가 기준 커밋 `75b5b0c`으로 코드를 되돌려 재현해 선재 실패임을 이미 실행으로 확인**한 것과 정확히 같은 3건이다 — 이번 패치가 새 실패를 만들지 않았다.
- 이 스토리의 두 케이스가 실제로 돌고 통과하는지 개별 재확인: `npx playwright test --project=desktop-1280x800 -g "C8|B8"` → **2 passed**(C8은 3차 patch로 계정 참조를 바꾼 뒤에도 psql 전제 단언이 `role='buyer'`를 실제로 읽고 통과).
- Block If 재검증(3차): 파일 grep 대신 마이그레이션 3개(`0002`·`0005`·`0015`)를 직접 열어 `listings`의 유효 정책 집합을 확인. `listings_delete_admin`이 `is_admin()` 경유로 role을 참조하나, 소유자를 제한하는 세 정책은 role을 읽지 않으므로 HALT 조건은 발동하지 않는다(근거를 스펙 Design Notes에 정정 기록).

**잔여 리스크**:
1. `image-fallback` 2건·C2 1건은 여전히 red다 — 선재 실패이며 이 스토리 범위 밖이라 손대지 않았다. "선재"라는 이유로 계속 넘기면 다음 스토리도 같은 논리를 쓰므로 DW-671(전량 실행 강제)과 함께 봐야 한다.
2. Playwright(E2E) 층은 **어느 브랜치에서도 CI에 없다** — `tests.yml`의 잡은 api·api-db·web(lint+vitest)·app 4개뿐이다. B8·C8의 회귀 방지 효력은 병합으로도 실질화되지 않고, 누군가 로컬에서 전량 실행할 때만 작동한다.
3. 이 브랜치(`test/bmad-loop`)는 `tests.yml`·`migration-gate.yml` 어느 쪽도 트리거하지 않는다(DW-661·DW-664 등재) — 위 통과 기록은 "CI 초록"이 아니라 "이 세션이 로컬에서 실행해 확인했다"는 뜻이다.
4. **이 스토리가 유일한 방어선으로 승격시킨 것들이 대부분 무검사다** — 앱측 `seller_id` 필터(DW-672), buyer 계정의 실제 등록(DW-673), `listings` 소유권 RLS 자체(DW-674), admin 진입이라는 의도된 결정(DW-675). 코드는 지금 옳게 동작하지만(3차 리뷰가 정책 본문과 필터를 직접 확인), 되돌아가도 아무도 안 잡는다. 각 항목에 "어느 스토리에서 심을지"를 트리거로 지정해 뒀다.
5. 기존 장부 항목 DW-451(`requireUser()` 시그니처 확장)·DW-453(죽은 `roleLabel` prop 정리)의 트리거가 이 스토리에서 실제로 발화했으나, 이 실행은 기존 항목을 수정할 권한이 없어 처리하지 못했다 — 오케스트레이터의 판단이 필요하다.
