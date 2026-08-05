---
title: '14.2 가입 역할선택 제거 + 트리거 기본 role'
type: 'feature'
created: '2026-08-06'
status: 'ready-for-dev'
review_loop_iteration: 0
followup_review_recommended: false
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** web 가입 화면이 구매자/판매자 역할 선택을 강제해 FR52("로그인만 하면 누구나 사고팔 수 있다")와 충돌한다. `0001 handle_new_user` 트리거도 metadata에 role이 없으면 `'buyer'`로만 채워, 통합된 계정 모델에 맞는 기본값이 없다.

**Approach:** web 가입 화면에서 역할 선택 UI·상태·전송을 제거하고 안내 문구로 대체한다. 새 마이그레이션으로 `handle_new_user`를 교체해 metadata에 유효한 role(`buyer`/`seller`)이 없으면(admin 포함, 없음 포함) `'user'`로 기본 배정하되, 명시적 `buyer`/`seller` metadata는 하위호환으로 계속 반영한다(Flutter 앱은 이번 스토리에서 UI를 안 건드리므로, 그 앱이 여전히 role을 보내는 가입 경로를 깨지 않기 위함).

## Boundaries & Constraints

**Always:**
- `profiles.role` 컬럼명·기존 행 불변(forward-only, 14.1과 동일 원칙). 새 마이그 번호는 구현 시점 `supabase/migrations/`의 max+1(현재 0027 다음 — 하드코딩 금지).
- 트리거는 `buyer`/`seller`가 아닌 어떤 metadata role 값(`admin` 포함, 누락 포함)도 `'user'`로 강제한다 — admin 승격 경로가 여전히 없어야 한다(기존 방어의 강화판).
- web 가입 제출은 `options.data`에 role 키를 아예 보내지 않는다(트리거의 coalesce 기본값에 위임).
- DW-663 해소: `api/tests/integration/conftest.py::_create_user()`와 `test_chat_idempotency_real_db.py`의 자체 `_create_user` 사본을 새 트리거 계약에 맞게 갱신하고, `pytest tests/integration` 전체가 초록임을 확인한다. 확인 후 `deferred-work.md`의 DW-663을 `status: resolved`로 갱신한다.
- 이 변경이 여는 새 갭 — web에서 가입한 계정은 `auth.users.raw_user_meta_data`에 role 키가 없어, Flutter 앱의 `currentRoleProvider`(user_metadata 기반) 의존 화면(`sell_screen`·`edit_listing_screen`·`my_listings_screen`·`home_screen`·`chat_list_screen`)이 그런 계정엔 판매자 기능을 숨긴다 — 를 `deferred-work.md`에 신규 DW로 등재한다(trigger: "Flutter 쪽 역할 통합 미러링을 다루는 다음 스토리 착수 시").
- 로그인/로그아웃(FR2) 회귀 없음을 실제 브라우저에서 확인한다.

**Block If:**
- `conftest._create_user` 갱신 후에도 `pytest tests/integration` 전체가 초록이 아니면 → HALT(status: blocked) — 원인 불명 회귀를 덮지 않는다.
- 트리거 교체 후 admin metadata로 가입 시 실제 admin이 배정되는 회귀가 재현되면 → HALT(status: blocked).

**Never:**
- Flutter 앱(`app/lib/features/auth/signup_screen.dart`)의 역할 선택 UI 제거 — 이번 스토리 범위 밖(위 DW 등재로 갈음).
- Story 14.3 범위인 판매 게이트(`requireRole(SELLER)` → `requireUser()`) 변경 — 건드리지 않는다.
  > ✎ 2026-08-06 **실행 순서가 14.3 → 14.2로 뒤집혔다**(사용자 결정, 근거는 `sprint-status.yaml`의 epic-14 주석). 이 스토리를 시작하는 시점에 **판매 게이트는 14.3이 이미 `requireUser()`로 완화해 놓은 상태**다. 즉 이 `Never`는 "네가 풀어라"가 아니라 **"이미 풀려 있으니 그대로 두라"**는 뜻이다. 게이트가 아직 `requireRole(SELLER)`이면 14.3이 안 끝난 것이므로 진행하지 말고 멈춰라.
  > 이 순서 뒤집기의 이유: 원래 순서(14.2 먼저)에서는 이 `Never`와 위 `Always`(기본 role `'user'` 강제)가 **서로 모순**이었다 — 신규 가입자 전원이 `/sell`에서 튕기고, 그건 이 스토리의 존재 이유인 FR52를 정면으로 어긴다. 첫 시도(run 0381)의 dev 세션이 이 모순을 찾아 CRITICAL 에스컬레이션으로 멈췄고, **순서를 바꾸는 것만으로 스펙 내용을 하나도 안 고치고 해소됐다.**
- `profiles`에 새 컬럼(`account_type` 등) 추가 — 이번 증분은 값 의미만 다룬다.
- 기존 가입 계정의 `profiles.role`/`raw_user_meta_data`를 일괄 변경하는 UPDATE — 신규 가입에만 적용.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 역할 메타데이터 없음(신규 web 가입) | `signUp({email,password})`, role 키 없음 | `profiles.role = 'user'` | No error expected |
| 명시적 seller/buyer 메타데이터(하위호환 — 테스트·Flutter) | `metadata.role='seller'` | `profiles.role = 'seller'`(그대로 반영, 회귀 없음) | No error expected |
| admin 승격 시도 | `metadata.role='admin'` | `profiles.role = 'user'`(강제 차단) | No error, 조용히 무시하고 강제 |
| 로그인/로그아웃 회귀 | 기존 계정으로 로그인 후 로그아웃 | 이전과 동일하게 동작 | 기존과 동일 |

</intent-contract>

## Code Map

- `web/src/app/(auth)/signup/page.tsx` -- 역할 선택 `fieldset`·`role` state·`SIGNUP_ROLES`·`USER_ROLE`/`UserRole` import 제거, `options: {data: {role}}` 전송 제거, 안내 문구 추가.
- `supabase/migrations/000N_handle_new_user_default_role.sql`(N=구현 시점 max+1, 현재 0027 다음) -- `create or replace function public.handle_new_user()`로 기본값을 `'user'`로 교체(coalesce + 허용값 검증).
- `api/tests/integration/conftest.py` -- `_create_user()`의 role 계약 갱신(DW-663) + "metadata role 없음 → 'user'" 케이스 커버.
- `api/tests/integration/test_chat_idempotency_real_db.py` -- 자체 `_create_user` 사본, 동일하게 갱신(DW-663 블라스트 반경, conftest 이관 대상 아님 — 12.2 스펙이 이미 "이번 범위 밖"으로 확정).
- `api/tests/integration/test_role_check_relax_real_db.py` -- 신규 기본값 회귀 테스트(role 없음/무효/admin 시도) 추가할 자연스러운 자리(14.1이 만든 동일 트리거 대상 파일).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- Flutter 갭 신규 DW 등재 + DW-663 `status: resolved` 갱신.
- `app/lib/features/auth/user_role.dart` -- 읽기 전용 참고(이미 14.2를 향한 메모가 있음, 코드 변경 없음 — 실제 대응은 위 DW 등재로 갈음).

## Tasks & Acceptance

**Execution:**
- `web/src/app/(auth)/signup/page.tsx` -- 역할 선택 UI·상태·전송 제거, "차를 사고파는 건 가입 후 언제든 할 수 있어요." 안내 추가 -- FR52·UX-DR19
- `supabase/migrations/000N_handle_new_user_default_role.sql` -- `handle_new_user()` 교체(coalesce 기본값 `'user'`, `buyer`/`seller` 아닌 값은 전부 `'user'`로 강제) -- I3, admin 승격 방어 유지
- `api/tests/integration/conftest.py`, `test_chat_idempotency_real_db.py` -- `_create_user()` role 단언을 새 계약에 맞게 갱신 -- DW-663
- `api/tests/integration/test_role_check_relax_real_db.py` -- role 없음/무효/admin metadata 케이스 회귀 테스트 추가 -- I/O 매트릭스 커버
- `_bmad-output/implementation-artifacts/deferred-work.md` -- Flutter 갭 신규 DW 등재, DW-663 `status: resolved` -- CLAUDE.md B8

**Acceptance Criteria:**
- Given web 가입 화면, when 접근하면, then 역할 선택 라디오·안내가 없고 "차를 사고파는 건 가입 후 언제든 할 수 있어요." 문구가 보인다(FR52, UX-DR19)
- Given web 가입 제출, when 성공하면, then Auth 요청에 role 메타데이터가 실리지 않는다(코드 검사 또는 네트워크 탭으로 확인)
- Given 신규 마이그 적용 후 metadata에 role 키 없이 가입, when `profiles`를 조회하면, then `role='user'`
- Given metadata에 `role='seller'`(또는 `'buyer'`)를 명시해 가입(Flutter/테스트 하위호환 경로), when `profiles`를 조회하면, then 해당 값이 그대로 반영된다(회귀 없음)
- Given metadata에 `role='admin'`으로 가입 시도, when `profiles`를 조회하면, then `role='user'`로 강제되고 admin이 되지 않는다
- Given 기존 계정, when 로그인 후 로그아웃하면, then 이전과 동일하게 동작한다(FR2 회귀 없음)
- Given `conftest._create_user` 갱신 완료, when `pytest tests/integration` 전체를 실행하면, then 전부 통과한다(DW-663 해소 증거)
- Given 전체 `supabase/migrations/*.sql`, when `python3 scripts/check_migrations.py`를 실행하면, then exit code 0

## Spec Change Log

## Review Triage Log

### 2026-08-06 — Review pass
- intent_gap: 1: (high 1, medium 0, low 0)
- bad_spec: 0
- patch: 0
- defer: 0
- reject: 0
- addressed_findings:
  - none

Cascading order applied: the intent_gap below makes all other findings from this pass moot (not actioned). For the record, this pass's 4 parallel review layers (blind-hunter/adversarial, edge-case-hunter, verification-gap, intent-alignment) surfaced additional lower-severity items — a `name` field silently going NULL on email-less signups (edge-case-hunter, verification-gap), a sibling test helper (`test_view_count_rpc_real_db.py::_create_seller`) that still doesn't assert role, duplicated `_create_user` across two test files, an SQL f-string in a test, and the migration comment's unverified claim about Flutter — none of these were processed this pass.

**intent_gap (high):** This spec's `<intent-contract>` contains an internal contradiction that the READY-FOR-DEVELOPMENT gate should have caught but did not. `Always` commits the new signup trigger to defaulting every account without explicit `buyer`/`seller` metadata (i.e. every new web signup, since this same spec removes the only UI path that ever sent that metadata) to `role='user'`. `Never` forbids touching `web/src/lib/auth/guard.ts`'s `requireRole(SELLER)` gate (`web/src/app/(user)/sell/layout.tsx`), which is the *only* role gate in the product and does a strict `profile.role !== role` check. Combined, these two constraints guarantee that every new web signup is permanently redirected away from `/sell` — directly defeating FR52("로그인만 하면 누구나 사고팔 수 있다"), the requirement this very story cites as its reason for existing. Confirmed directly by reading `guard.ts:37` and `sell/layout.tsx:14` (not just trusting the reviewers). Independently flagged by 2 of 4 review layers (adversarial, verification-gap) and structurally corroborated by the intent-alignment audit.
  - Why this is intent_gap and not bad_spec/patch: the fix requires changing content that lives inside `<intent-contract>` — either the `Always` clause's literal default value (`'user'`) or the `Never` clause's exclusion of the sell gate — and bad_spec/patch are explicitly forbidden from touching `<intent-contract>` content.
  - Unresolved questions for the human/next planning pass:
    1. Should the trigger's default value be something that still passes the existing `requireRole(SELLER)` gate (e.g. `'seller'`, since selling is the only role-gated action in the product and buying is never role-gated) instead of introducing a new `'user'` value — fully satisfying FR52 today with zero gate changes, at the cost of `profiles.role='seller'` no longer meaning "chose to sell at signup"?
    2. Or should Story 14.2's scope be widened to include a minimal, temporary compatibility change to the sell gate (accepting the new default in addition to `'seller'`) even though the epic's own dependency note assigns the gate rewrite to Story 14.3?
    3. Or does the epic's 14.1→14.2→14.3 sequencing intend an accepted, temporary regression window between 14.2 and 14.3 landing — and if so, should 14.2 explicitly say so and gate its own "done" status on 14.3 shipping in the same batch?
  - Saved patch (the full attempted implementation, reverted from the working tree before this halt): `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-14-2-가입-역할선택-제거-트리거-기본-role.diff`
  - Code changes have been reverted to `baseline_revision` (`12e1db9661f14c55a2f12e85f9ae02ec9dcea7db`). This includes reverting the `deferred-work.md` edits (DW-663 resolution and DW-668 registration) made during the now-discarded implementation, since they were built on the flawed default-value decision.

## Design Notes

- **왜 `'user'`인가**: 14.1의 Design Notes가 이미 이 값을 신규 기본값 후보로 예시했고(`role in ('user', 'admin')`), FR61(Epic 15)이 예정한 "admin/일반" 2축 표시와 자연스럽게 대응한다. `ROLE_LABEL`(web `constants.ts`)이 이 값을 모르더라도 14.1이 이미 추가한 `??` 폴백 + `roleLabelFallback.test.ts` 스캔이 안전망이므로, 이번 스토리는 `constants.ts`를 건드릴 필요가 없다(라벨링 정리는 Epic 15 소유).
- **왜 metadata를 완전히 무시하지 않고 coalesce를 유지하는가**: Flutter 앱(`signup_screen.dart`)은 이번 스토리에서 UI를 그대로 두므로 여전히 `role` metadata를 보낸다. 트리거가 metadata를 완전히 무시하면 Flutter 가입 경로가 항상 `'user'`로만 찍혀 기존 동작이 조용히 바뀐다 — 최소 변경 원칙상 "web이 안 보내는 경우의 기본값만" 바꾸는 쪽이 더 외과적이다(CLAUDE.md A3).
- **Flutter 화면 노출 갭을 이 스토리가 고치지 않는 이유**: Flutter의 역할 기반 게이트를 소유권 기반으로 바꾸는 것은 Story 14.3(및 그 Flutter 대응분)의 성격이지, "가입 화면·트리거"만 다루는 14.2의 범위가 아니다. 다만 이 스토리가 그 갭을 **새로 여는 것**은 사실이므로 신고는 필수(CLAUDE.md B8).

## Verification

**Commands:**
- `python3 scripts/check_migrations.py` -- expected: exit 0
- `pytest tests/integration`(로컬 pgvector 컨테이너, 0001~신규 마이그 전체 적용 후) -- expected: 전체 통과, DW-663 대상 파일 포함
- `npx tsc --noEmit` / `npm run lint` / `npm test`(vitest) -- expected: 통과, 회귀 없음
- 브라우저로 실제 가입→로그인→로그아웃 흐름 실행 -- expected: 역할 선택 UI 없음, 정상 동작, devtools network에서 role 메타데이터 미전송 확인

**Manual checks (if no CLI):**
- 신규 pgvector 컨테이너에 0001~신규 마이그 전체 적용 후 `select role from public.profiles where id = <role 없이 가입시킨 유저>;`로 `'user'` 확인, `<admin metadata로 가입시킨 유저>`도 동일하게 `'user'` 확인.

## Auto Run Result

**Status:** `blocked` — blocking condition `intent gap`.

**요약:** 구현(step-03)은 스펙대로 완료돼 로컬에서 전부 검증됐었다(`check_migrations.py` exit 0, `pytest tests/integration` 98건 통과, `tsc`/`lint`/`vitest` 통과, 브라우저 E2E로 가입→로그인→로그아웃 확인). 그런데 리뷰(step-04)에서 4개 레이어 중 2개(adversarial·verification-gap)가 독립적으로, 그리고 intent-alignment 감사가 구조적으로 같은 결함을 지목했다: 이 스펙의 `<intent-contract>` 자체가 내부 모순을 담고 있었다 — `Always`가 신규 가입 기본값을 `'user'`로 강제하면서 `Never`가 `requireRole(SELLER)` 판매 게이트를 손대지 못하게 막아, **모든 신규 web 가입자가 영구히 `/sell`에서 튕겨나가는** 결과를 만든다(`web/src/lib/auth/guard.ts:37` + `web/src/app/(user)/sell/layout.tsx:14` 직접 확인). 이는 이 스토리가 존재하는 이유인 FR52("로그인만 하면 누구나 사고팔 수 있다")를 정면으로 어긴다. 수정이 `<intent-contract>` 내용 자체를 바꿔야 해서 patch/bad_spec으로 처리할 수 없어 intent_gap으로 분류하고 HALT했다.

**되돌린 것:** `web/src/app/(auth)/signup/page.tsx`, `api/tests/integration/conftest.py`, `api/tests/integration/test_chat_idempotency_real_db.py`, `api/tests/integration/test_role_check_relax_real_db.py`, `_bmad-output/implementation-artifacts/deferred-work.md`를 `baseline_revision`(`12e1db9`)으로 복원. 신규 미추적 파일 `supabase/migrations/0028_handle_new_user_default_role.sql`은 삭제. 시도했던 전체 diff는 `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-14-2-가입-역할선택-제거-트리거-기본-role.diff`에 보존.

**미해결 질문(다음 계획/사람 판단 필요):** `## Review Triage Log`의 intent_gap 항목 참고 — (1) 트리거 기본값을 기존 판매 게이트를 통과하는 값(예: `'seller'`)으로 정할지, (2) 이 스토리 범위를 넓혀 판매 게이트에 최소 하위호환을 더할지, (3) 아니면 14.2→14.3 사이의 일시적 회귀 창을 에픽이 의도적으로 받아들이는 것인지(그렇다면 그걸 스펙에 명시하고 14.3과 묶어야 하는지).

**잔여 위험:** 로컬 개발 Supabase DB가 되돌리기 전에 마이그 0025~0028까지 적용된 상태로 남아 있을 수 있다(구현 세션이 브라우저 검증을 위해 로컬 DB에 0028을 적용했었음 — 레포 마이그 파일 자체는 삭제됐지만, 로컬 DB 상태는 별도 확인 필요).
