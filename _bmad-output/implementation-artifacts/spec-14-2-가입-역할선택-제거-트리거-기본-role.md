---
title: '14.2 가입 역할선택 제거 + 트리거 기본 role'
type: 'feature'
created: '2026-08-06'
status: 'done'
baseline_revision: '3b4aaf985ebd06775ec0ccc88bda196e67166f7f'
# final_revision은 리뷰된 변경이 전부 담긴 커밋이다. 이 줄 자체를 기록하는 커밋(장부 마감)은
# 그 뒤에 오므로 포함되지 않는다 — baseline..final_revision으로 diff를 뜨는 소비자는 그 점을 감안할 것.
final_revision: '253f0c21a60c1d913ea730c2f1fd13957b79afee'
review_loop_iteration: 0
# patch high 0 · medium 2 · low 8 → 3×2 + 1×8 = 14 ≥ 5 → true (2026-08-06 후속 리뷰 2차)
followup_review_recommended: true
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

### 2026-08-06 — Review pass (retry, after epic reorder 14.3→14.2)
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 1: (high 0, medium 1, low 0)
- reject: 1
- addressed_findings:
  - `[medium]` `[patch]` `web/src/lib/constants.ts`의 `ROLE_LABEL`에 `'user'` 키가 없어 신규 가입자의 역할 표시가 영문 "user"로 노출되는 문제 — `USER_ROLE.USER`·`ROLE_LABEL[USER_ROLE.USER]: '회원'` 추가로 수정.
  - `[medium]` `[patch]` DW-668(Flutter 역할 게이트 불일치)이 자신의 trigger 절이 지정한 "Story 14.2 리뷰에서 실제 발생 여부 확인 시 severity를 high로 올린다"를 이행받지 못한 채 방치됨 — severity를 high로 갱신하고 DW-678과 상호 참조 추가.
  - `[low]` `[patch]` DW-678의 evidence가 "5개 화면"의 근거로 든 grep이 실제로는 6건(main.dart 포함)을 반환하는데 그 차이가 설명되지 않음 — main.dart는 admin 판별용이라 대상에서 제외된다는 문장 추가.
  - `[low]` `[patch]` 이 스펙의 `## Auto Run Result`가 이전(실패한) 시도의 `blocked` 결과를 그대로 담아 새 frontmatter status(`in-review`)와 자기모순이었음 — 아래 `## Auto Run Result`를 이번 통과분으로 교체.

이번 패스의 4개 병렬 레이어(blind-hunter/adversarial, edge-case-hunter, verification-gap, intent-alignment) 결과: edge-case-hunter는 findings 0건(화이트리스트 구조라 처리 안 된 분기가 없음을 직접 확인). adversarial 6건 중 3건은 위 patch로 처리, 1건(핵심 시나리오 E2E 부재)은 defer로 DW-679 등재, 1건(DW-664 CI 미가동)은 기존 DW-664와 중복이라 reject, 1건(Auto Run Result 자기모순)은 patch로 처리(아래 섹션 교체). verification-gap 1건은 adversarial의 ROLE_LABEL 지적과 동일 클레임이라 중복 제거 후 patch로 함께 처리. intent-alignment는 findings 형식이 아닌 서술 감사였고, 그 결과(로그인/로그아웃 회귀 확인이 diff/장부에 별도 기록으로 남지 않음)는 이번에 교체하는 `## Auto Run Result`에 그 근거를 명시하는 것으로 반영했다(별도 트리아지 항목으로 세지 않음 — 실제 확인 자체는 구현 세션이 이미 수행했고 기록 누락만 문제였음).

### 2026-08-06 — Review pass (follow-up, status: done 스펙에 대한 재리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 4: (high 0, medium 2, low 2)
- reject: 12
- addressed_findings:
  - `[medium]` `[patch]` 이 스토리의 web 쪽 계약("`signUp()`에 role metadata를 안 보낸다")을 지키는 실행되는 검사가 하나도 없었다 — 4개 레이어 중 3개(adversarial·edge-case·verification-gap)가 독립적으로 지적했고, 그중 둘이 `options: {data:{role:'seller'}}`를 되돌려 넣고 web CI 잡의 두 명령(`npm run lint`·`npm test`)을 그대로 돌려 **전부 초록**임을 실증했다. `web/src/app/(auth)/signup/__tests__/signupNoRoleMetadata.test.ts` 신규 추가(중괄호 짝맞춤으로 `auth.signUp(...)` 인자를 잘라내 `options`/`data`/`role` 부재를 단언 + 호출부를 못 찾은 상태를 통과로 오인하지 않는 자기검사). CLAUDE.md B9.
  - `[medium]` `[patch]` `ROLE_LABEL`의 `'user'` 라벨을 지켜주는 것이 TypeScript 타입뿐이었는데, web CI 잡은 `tsc --noEmit`도 `next build`도 돌리지 않는다(실측: 라벨을 지우고 `npm run lint` exit 0 · vitest 308건 전부 통과, `tsc --noEmit`만 TS2741로 잡음). `roleLabelFallback.test.ts`에 `Object.keys(ROLE_LABEL) === Object.values(USER_ROLE)` 전사상 단언 추가 — 이건 CI에서 실제로 돈다.
  - `[low]` `[patch]` `supabase/migrations/0028`도 0027과 똑같은 forward-only 약속("기존 행을 안 건드린다")을 주석으로만 하고 있었고, 그 약속을 문장 층에서 못박는 검사(⑧ `test_migration_contains_no_data_mutation`)는 0027 하나만 보고 있었다 — CI api-db 잡은 **빈 DB**에 마이그를 적용하므로 나중에 백필 UPDATE가 들어가도 0건이 바뀌어 초록으로 통과한다. ⑧을 0027·0028 두 파일로 parametrize.
  - `[low]` `[patch]` `api/tests/integration/test_role_check_relax_real_db.py`의 픽스처 docstring 3곳이 0028 이전 세계를 현재형으로 서술하고 있었다("가입 트리거는 buyer/seller만 배정하므로(0009: …)", "Story 14.2가 바꿀 **예정인** 것", 파라미터 값 `"whatever-14-2-picks"`, "14.2가 기본값을 정할 때 다시 좁힐지 판단한다" — 14.2는 이미 정했고 좁히지 않기로 했다). 전부 현행화 + 좁히지 않기로 한 결정을 명시.
  - `[low]` `[patch]` `supabase/seed.sql`(3곳)·`supabase/seed-local/01_accounts.sql`(1곳)의 주석이 "트리거가 만든 profiles(기본 buyer)"라고 단언 — 0028이 그 문장을 거짓으로 만들었다. 네 곳 모두 현행화(동작은 원래도 무해했다 — 두 시드 모두 뒤이어 목표 role로 UPDATE하므로 `web/e2e`의 C8이 기대하는 `buyer@test.com` role='buyer'는 그대로다).
  - `[low]` `[patch]` `signup/page.tsx` 헤더 주석이 "트리거의 **coalesce** 기본값에 위임한다"고 적었으나 0028은 coalesce가 아니라 화이트리스트 IF다(동작은 오히려 더 강하다 — 순수 coalesce였다면 `'admin'`이 통과했을 것). 문구 정정 + 계약을 강제하는 검사 파일명을 함께 적음.

이번 패스의 4개 병렬 레이어(blind-hunter/adversarial, edge-case-hunter, verification-gap, intent-alignment) 결과 요약:
- **defer 4건**은 전부 `deferred-work.md`에 신규 항목으로만 등재했다(오케스트레이터 지시대로 기존 항목은 손대지 않음) — DW-680(DW-668의 high 승격 근거가 "실측"이 아니고 제자리 수정이라 장부 append-only 규칙도 어겼다) · DW-681(`docs/conventions.md`에 role 어휘 절이 없어 `'user'`의 정본이 없다) · DW-682(0028의 buyer/seller 통과 분기에 제거 트리거가 없다) · DW-683(`test_fr11_cover_images_real_db.py`의 seller 픽스처 INSERT가 항상 no-op).
- **reject 12건**의 주요 근거: (a) "0028에 postcondition이 없고 `check_migrations.py` 프로브가 profiles를 안 본다"는 지적은 **실제 방어 지점을 잘못 짚었다** — 0028의 계약을 지키는 것은 마이그 게이트가 아니라 api-db CI 잡이 돌리는 `test_handle_new_user_default_role_matrix`이고, 그 잡은 프렐류드+전체 마이그 적용 후 `tests/integration` 전량을 돈다(워크플로 파일에서 직접 확인). (b) "0028이 0027의 CHECK 제거를 전제하는데 precondition 가드가 없다"는 지적은 적용 루프가 `ON_ERROR_STOP` + 번호순이라 0027 실패 시 0028에 도달하지 못하며, 비원자성 일반론은 이미 DW-665가 열려 있다. (c) `conftest._create_user`의 `expected_role` 매핑이 12.1 방어를 약화시킨다는 지적은 실제 호출부를 전수 확인한 결과 buyer/seller 외 값을 넘기는 곳이 이번에 추가한 의도적 테스트뿐이라 잠재적 위험에 그친다(12.1의 결함 유형 — seller 헬퍼가 buyer를 하드코딩 — 은 여전히 잡힌다). (d) `test_admin_signup_metadata_does_not_grant_is_admin`이 옛 트리거에서도 초록이라는 지적은 사실이나, 그 테스트는 여전히 red가 될 수 있는 불변식 검사다. (e) 나머지는 기존 장부 항목 수정을 요구하거나(이번 세션 금지) 스타일·표현 수준이다.
- **intent-alignment**는 findings 형식이 아닌 서술 감사였고, 그 핵심(“I/O 매트릭스는 signUp API 면에 쓰였는데 검증은 raw SQL 면을 친다”, “role 미전송 계약이 사는 면엔 검사가 0개”)은 위 patch 1·2로 실제 검사를 그 면에 심는 것으로 반영했다.

### 2026-08-06 — Review pass (follow-up 2, `status: done` 스펙 재리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 2, low 8)
- defer: 4: (high 0, medium 3, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` 1차 후속 패스가 심은 `signupNoRoleMetadata.test.ts`가 계약을 깨는 **가장 값싼 방법**을 못 잡았다 — adversarial·edge-case 두 렌즈가 독립 지적했고 edge-case는 우회 소스를 실제로 돌려 GREEN임을 실증했다. ① `const extra = {data:{role:'seller'}}` + `signUp({email,password,...extra})` 스프레드 우회 ② 두 번째 `auth.signUp(` 호출부(검사는 첫 호출부만 본다) ③ `stripComments`가 `https://`를 줄 주석으로 오인해 그 줄 뒤를 잘라내 **URL 뒤에 오는 키가 스캔에 안 보였다**(두 구현을 같은 입력에 돌려 비교 확인). 세 갈래를 각각 막고 ①②를 실제로 넣어 red 확인 후 원복.
  - `[medium]` `[patch]` 0028이 `create or replace`로 함수를 통째로 다시 쓰면서 손으로 옮겨 적은 `security definer`·`set search_path = public`을 **아무 검사도 보지 않았다** — verification-gap 렌즈가 살아 있는 함수에서 둘을 떼고 `pytest tests/integration` 100건 전부 통과·`check_migrations.py` exit 0을 실측했다. 통합 테스트는 superuser로 붙어 정의자 권한이 구조적으로 관측되지 않는 반면, 실제 가입은 GoTrue의 `supabase_auth_admin`이 이 트리거를 돌린다(profiles에 그 롤용 INSERT 정책 없음) — 빠지면 **가입 자체가 조용히 깨진다**. 형제 트리거 함수엔 이미 같은 검사가 있다. `test_handle_new_user_keeps_security_definer_and_pinned_search_path` 추가.
  - `[low]` `[patch]` 0028의 전제인 "0001의 트리거 배선은 그대로 유지된다"를 확인하는 것이 없었다 — `test_signup_trigger_is_still_wired_to_auth_users` 추가(배선을 drop해 red 확인).
  - `[low]` `[patch]` 0028이 0009로부터 손으로 옮겨 적은 `name = split_part(email,'@',1)` 기록을 아무도 안 봤다(실측: 그 줄을 빼도 100건 전부 통과). 사라지면 `/admin/members`가 `m.name ?? shortId(m.id)` 폴백으로 조용히 UUID 앞자리를 보여준다. 매트릭스 테스트가 `name`까지 단언하도록 확장.
  - `[low]` `[patch]` ⑧ `test_migration_contains_no_data_mutation`이 **직전 패스가 고친 방식 그대로** 다음 번호에서 재발할 구조였다(하드코딩 2파일 목록 — 0029를 추가하는 걸 잊어도 아무것도 red가 안 된다). 형제 검사 `api/tests/test_migration_no_backfill.py`가 이미 쓰는 glob + 빈 목록 자기검사 패턴으로 교체. 동시에 정규식이 `merge into`·`insert … select` 백필을 놓치던 것을 대상 테이블(`public.profiles`)로 좁히면서 함께 잡도록 넓혔고, 함수 정의 본문은 제외했다(적용 시점에 도는 문장이 아니다). 네 가지 형태로 깨서 전부 red 확인.
  - `[low]` `[patch]` 매트릭스 테스트의 "독립된 회귀 테스트"라는 주장이 사실이 아니었다 — `conftest._create_user()`가 같은 단언을 먼저 하므로 트리거가 깨지면 픽스처 setup에서 터지고 이 테스트 자신의 단언엔 도달하지 못한다(나중에 헬퍼 단언을 완화하면 계속 초록이면서 아무것도 안 지킨다). 헬퍼를 안 거치는 `_signup()`으로 독립시켰다.
  - `[low]` `[patch]` `_create_user(..., role='admin')`이 조용히 `'user'`로 재해석되고 단언까지 동의해, "관리자를 만들었다"고 믿는 테스트가 경고 없이 통과할 수 있었다(DW-683과 같은 실패 유형). `buyer`/`seller`/`None` 밖의 값은 `ValueError`로 거부하도록 두 사본 모두 수정.
  - `[low]` `[patch]` `test_admin_signup_metadata_does_not_grant_is_admin`이 헛되이 초록일 수 있었다 — `set local request.jwt.claim.sub`가 안 먹히면 `auth.uid()`가 NULL이라 `is_admin()`이 무조건 false다. 같은 커넥션에서 role을 올리면 true가 되는 **양성 대조**를 추가(세션 변수명을 일부러 틀려 red 확인).
  - `[low]` `[patch]` 1차 패스의 주석 현행화가 두 곳을 놓쳤다 — `test_chat_unread_real_db.py:278`("buyer로 떨어진다 — **실측**"이라는 단어까지 달려 있어 더 믿기 쉽다)·`docs/learning/01-db.md:70`("buyer/seller만 허용"). 둘 다 현행화.
  - `[low]` `[patch]` 새 검사 두 곳의 "CI에서 실제로 돈다"가 브랜치 사실과 어긋났다 — `tests.yml`은 `on.push.branches: [develop, main]`이라 작업 브랜치에서는 안 돈다(DW-664, 열려 있음). 두 파일에 그 단서를 명시하고, 이 스펙의 `## Auto Run Result`에 있던 **낡은 검증 블록이 새 것보다 뒤에 오던 자기모순**(pytest 99건/vitest 308건 vs 100건/311건)도 함께 정리했다.

이번 패스의 4개 병렬 레이어 결과 요약:
- **defer 4건**은 전부 신규 항목으로만 등재했다(오케스트레이터 지시대로 기존 항목 무수정) — DW-684(통합 테스트 계정 모집단이 운영과 갈라짐: `role='user'` 시나리오 0건) · DW-685(role 관련 DW 5건이 지목한 "Epic 16 첫 스토리"에 role 얘기가 없고 아무것도 안 심었다 — B5·B8 위반) · DW-686(앱 테스트가 옛 계약을 정답으로 단언해 `flutter test`가 영원히 초록) · DW-687(web 배포와 원격 0028 적용 사이 창의 가입자가 영구히 `'buyer'`).
- **reject 6건**의 근거: (a) "DW-668의 append-only 위반을 되돌려라" — 이미 DW-680이 등재했고, 기존 장부 항목 수정은 이번 세션이 명시적으로 금지받았다. (b) "`final_revision`이 자기를 기록한 커밋을 포함하지 않는다" — 그 필드의 구조적 성질이고 이번 패스가 어차피 갱신한다. (c) "`docs/conventions.md`에 role 절을 지금 추가하라" — DW-681이 트리거와 함께 이미 등재했다(그 트리거가 겨냥한 자리 문제는 DW-685로 별도 등재). (d) "0028 안에 사후조건 블록을 넣어라" — 이 리포의 선례는 그 방어를 마이그 파일이 아니라 통합 테스트 층에 둔다(형제 broadcast 함수 검사). 위 patch 2·3이 그 자리에 넣었다. (e) 나머지는 표현·스타일 수준이거나 이미 열린 장부 항목의 재기술.
- **intent-alignment**는 서술 감사였다. 핵심 관측("매트릭스는 `signUp` API 면에 쓰였는데 검증은 raw SQL 면을 친다", "FR52 자체를 지키는 실행 검사는 어느 면에도 없다", "`_create_user` 기본값이 `buyer`라 기존 호출부는 전부 하위호환 분기를 탄다")은 각각 DW-679(이미 등재)·DW-684(신규)로 장부에 남겼다. 면(surface) 간극 자체는 이 스토리의 스코프가 아니라 검증 층의 구조적 한계라 patch로 만들지 않았다.

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

**Status:** `done`.

**참고 — 위 첫 번째 시도(2026-08-06, run 0381)의 기록:** 첫 시도는 이 스펙 자신의 `Always`(신규 기본값 `'user'` 강제)와 `Never`(판매 게이트 불변)가 서로 모순임을 발견해 `blocked`로 멈췄다. 그 모순은 에픽 실행 순서를 14.3→14.2로 뒤집는 것만으로(스펙 내용은 한 글자도 안 바꾸고) 해소됐다 — Story 14.3이 먼저 `requireRole(SELLER)`를 `requireUser()`로 풀어놓아, 이번 시도를 시작하는 시점엔 `Never`가 막는 그 게이트가 이미 소유권 기반이었다. 아래는 이번(두 번째, 성공한) 시도의 결과다.

**요약:** web 가입 화면에서 역할 선택 UI·상태·전송을 제거하고 안내 문구로 대체했다. 새 마이그레이션(`0028`)으로 `handle_new_user` 트리거를 교체해, metadata에 `buyer`/`seller`가 명시되지 않으면(누락·`admin`·그 외 임의 문자열 모두) `profiles.role`을 `'user'`로 기본 배정한다. `buyer`/`seller` 명시값은 하위호환으로 계속 반영해 Flutter 가입 경로를 깨지 않는다.

**파일 변경:**
- `web/src/app/(auth)/signup/page.tsx` — 역할 선택 라디오·`role` state·`SIGNUP_ROLES`·`options.data.role` 전송 제거, "차를 사고파는 건 가입 후 언제든 할 수 있어요." 안내로 대체.
- `supabase/migrations/0028_handle_new_user_default_role.sql`(신규) — 가입 트리거 기본값을 `'user'`로 교체(buyer/seller는 그대로 반영, 그 외 전부 강제).
- `api/tests/integration/conftest.py`, `test_chat_idempotency_real_db.py` — `_create_user()`가 `role=None`(메타데이터 자체 없음)을 지원하도록 확장, 새 트리거 계약에 맞게 단언 갱신(DW-663 해소).
- `api/tests/integration/test_role_check_relax_real_db.py` — I/O 매트릭스 4행(없음/buyer/seller/admin/임의값)을 재현하는 `test_handle_new_user_default_role_matrix` + `test_admin_signup_metadata_does_not_grant_is_admin` 추가.
- `web/src/lib/constants.ts` — 리뷰 patch: `USER_ROLE.USER`/`ROLE_LABEL['user']: '회원'` 추가(아래 리뷰 결과 참고).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-663을 `done`으로 닫음, DW-678(Flutter 미러링 갭)·DW-679(FR52 E2E 부재) 신규 등재, DW-668 severity를 리뷰에서 high로 갱신.

**리뷰 결과(자세한 내용은 `## Review Triage Log`의 2026-08-06 재시도 패스 참고):** intent_gap 0 · bad_spec 0 · patch 4(전부 적용 완료 — `ROLE_LABEL` 'user' 라벨 누락, DW-668 트리거 미이행, DW-678 evidence 오차, 이 섹션의 자기모순) · defer 1(DW-679로 등재) · reject 1(DW-664와 중복).

**검증(이 통과 패스 시점 기준 — 이후 패스에서 건수가 늘었다, 아래 후속 패스 절 참고):**
- `python3 scripts/check_migrations.py` → exit 0(0001~0028 전체, 정적+동적, patch 반영 후 재확인 완료)
- `pytest tests/integration`(로컬 pgvector 컨테이너, 매번 신규 일회용) → 99건 전체 통과, 트리거를 옛 버전으로 되돌려 신규 4건이 실제로 red가 됨을 먼저 확인한 뒤(B4) green 재확인.
- `npx tsc --noEmit` / `npm run lint` / `npm test`(vitest) → 통과(308건).
- 브라우저 E2E(Playwright, 로컬 Supabase): 신규 계정 가입(역할 UI 없음) → signUp 요청 바디 `"data":{}` 확인(role 미전송) → `profiles.role='user'`·`raw_user_meta_data`에 role 키 없음을 DB에서 확인 → 그 계정으로 `/sell` 접근 시 매물 등록 화면 정상 도달(FR52 실증) → 로그아웃 → 재로그인 정상 동작(FR2 회귀 없음, I/O 매트릭스 전 행 커버). 이 경로를 지키는 자동화 E2E는 아직 없다는 점을 DW-679로 별도 등재했다.

---

## 후속 리뷰 패스(2026-08-06, `status: done` 스펙 재리뷰)

**무엇을 했나:** 코드는 이미 done이었으므로 **새 기능은 추가하지 않았다.** 이 패스가 한 일은 "이 스토리가 만든 계약을 지키는 것이 실제로 무엇인가"를 되짚어, **주석뿐이던 자리에 실행되는 검사를 심는 것**이었다(CLAUDE.md B9 — 주석·문서는 계약이 아니다).

**추가로 바뀐 파일(위 목록에 더해):**
- `web/src/app/(auth)/signup/__tests__/signupNoRoleMetadata.test.ts`(신규) — `signUp()` 호출부에 `options`/`data`/`role` 키가 없음을 소스 스캔으로 단언. 호출부를 못 찾으면 그 자체로 red가 되는 자기검사 포함.
- `web/src/lib/__tests__/roleLabelFallback.test.ts` — `ROLE_LABEL`이 `USER_ROLE`의 모든 값을 덮는지(전사상) 단언 1건 추가. 타입만으로는 CI에서 안 걸린다는 것을 실측으로 확인한 뒤 심었다.
- `web/src/app/(auth)/signup/page.tsx` — 헤더 주석의 "coalesce 기본값" 표현 정정(0028은 화이트리스트 IF) + 계약을 강제하는 검사 파일명 명시.
- `api/tests/integration/test_role_check_relax_real_db.py` — ⑧ `test_migration_contains_no_data_mutation`을 0027·0028 두 파일로 parametrize, 픽스처 docstring 3곳을 0028 이후 현실로 현행화.
- `supabase/seed.sql`·`supabase/seed-local/01_accounts.sql` — "트리거가 만든 profiles(기본 buyer)"라고 단언하던 주석 4곳 현행화(동작 변경 없음).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-680~683 **신규 4건만 추가**(오케스트레이터 지시대로 기존 항목은 수정하지 않았다).

**리뷰 결과:** intent_gap 0 · bad_spec 0 · **patch 6**(medium 2 · low 4, 전부 적용 완료) · **defer 4**(DW-680~683) · reject 12. `followup_review_recommended: true` — patch high 0건, medium 2건·low 4건 → 3×2 + 1×4 = **10 ≥ 5**.

**검증(이번 패스에서 직접 실행·관찰):**
- 새 검사 2건을 **일부러 깨서 red 확인 후 되돌려 green 확인**(B4 — "만들었다"가 아니라 "잡는다"가 완료다): `signup/page.tsx`에 `options: { data: { role: 'seller' } }`를 넣고 `constants.ts`에서 `'회원'` 라벨을 지운 상태로 vitest → 정확히 그 2건만 red(`311건 중 2 failed`). 원복 후 **34파일 311건 전부 통과**.
- ⑧의 0028 커버리지도 같은 방식으로 확인: 0028 끝에 `update public.profiles set role='user' where role='buyer';`를 붙이자 `test_migration_contains_no_data_mutation[0028_…]`만 red, 원복 후 green.
- `npm run lint` exit 0 · `npx tsc --noEmit` exit 0.
- `pytest tests/integration` — 일회용 pgvector 컨테이너(pgvector/pgvector:pg17)에 프렐류드 + `0001~0028` 전량 적용 후 **100건 전부 통과**(직전 99건 + ⑧ parametrize로 1건 증가).
- `python3 scripts/check_migrations.py` → **exit 0**(정적 + 동적 프로브 3종 포함).

**잔여 위험(이번 패스가 확인한 것):**
- **DW-678(Flutter 갭)은 여전히 코드 읽기로만 확인된 상태다.** 앱을 실제로 띄워 재현한 적이 없으며, 그럼에도 DW-668이 "실측 확인됨"으로 severity high가 됐다 — 이 근거 등급 문제를 DW-680으로 등재했다. 결론(신규 web 가입자가 앱 판매화면에서 차단됨) 자체는 분기 조건이 명확해 뒤집힐 것으로 보이지 않는다.
- **`'user'`라는 값의 정본이 아직 없다**(DW-681) — `docs/conventions.md`에 role 어휘 절이 없어, 현재 정의는 코드 주석 3곳뿐이고 그중 `app/lib/features/auth/user_role.dart` 헤더는 이미 거짓이다.
- **web E2E는 여전히 CI에서 안 돈다**(DW-664·DW-679). 이번에 심은 것은 vitest 정적 스캔이라 "소스에 role이 없다"까지만 보증하고, 실제 네트워크 요청 바디는 보지 않는다.
- 원격(운영) Supabase 프로젝트에는 아직 `0028`이 적용되지 않았다 — 이번 패스도 로컬에서만 검증했다(CLAUDE.md B3에 따라 운영 반영은 별도 승인 필요).

**잔여 산출물(커밋하지 않음):** `_bmad-output/implementation-artifacts/sprint-status.yaml`이 이 세션 시작 시점에 이미 수정된 상태였다. 이 리뷰가 만든 변경이 아니고 오케스트레이터가 소유하는 파일이므로 손대지 않고 그대로 두었다.

---

## 후속 리뷰 패스 2차(2026-08-06, `status: done` 스펙 재리뷰)

**무엇을 했나:** 1차 후속 패스가 "주석뿐이던 자리에 검사를 심었다"면, 이번 패스는 **그 검사들이 실제로 무엇을 잡는지 측정**했다. 세 검사가 자기가 막는다고 적어둔 것을 실은 못 막고 있었고(전부 실측으로 확인), 0028이 함수를 통째로 다시 쓰면서 손으로 옮겨 적은 속성 두 가지는 아무도 안 보고 있었다.

**추가로 바뀐 파일:**
- `web/src/app/(auth)/signup/__tests__/signupNoRoleMetadata.test.ts` — ① 스프레드·간접 전달 우회 차단(파일 어디에도 `data:` 키 금지 + 인자에 `...` 금지) ② `auth.signUp(` 호출부가 정확히 1개임을 단언(둘째 호출부가 검사 밖으로 새던 것) ③ `stripComments`가 `https://`의 프로토콜 슬래시를 주석으로 오인해 그 줄 뒤를 통째로 잘라내던 것 수정 ④ CI 브랜치 트리거(DW-664) 단서 명시.
- `api/tests/integration/test_role_check_relax_real_db.py` — `test_handle_new_user_keeps_security_definer_and_pinned_search_path`·`test_signup_trigger_is_still_wired_to_auth_users` 신규 추가. 매트릭스 테스트는 `conftest._create_user`를 안 거치는 자체 `_signup()` 헬퍼로 독립시키고(전엔 헬퍼가 먼저 단언해 자기 단언에 도달하지 못했다) `profiles.name`까지 단언. ⑧ forward-only 검사는 하드코딩 2파일 목록 → **0027 이상 glob + 빈 목록 자기검사**로 교체하고, 대상을 `public.profiles` 쓰기로 좁히면서 `merge`·`insert … select`를 포함시키고 함수 정의 본문은 제외. admin 테스트에 **양성 대조**(같은 커넥션에서 role을 올리면 `is_admin()`이 true가 되는지) 추가.
- `api/tests/integration/conftest.py`·`test_chat_idempotency_real_db.py` — `_create_user()`가 `buyer`/`seller`/`None` 밖의 role 요청을 조용히 `'user'`로 재해석하지 않고 `ValueError`로 거부.
- `api/tests/integration/test_chat_unread_real_db.py`·`docs/learning/01-db.md` — 0028이 거짓으로 만든 서술 2곳 현행화(1차 패스가 놓친 자리).
- `web/src/lib/__tests__/roleLabelFallback.test.ts` — "CI에서 실제로 돈다"에 DW-664 단서 추가.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-684~687 **신규 4건만 추가**(오케스트레이터 지시대로 기존 항목은 수정하지 않았다).

**리뷰 결과:** intent_gap 0 · bad_spec 0 · **patch 10**(medium 2 · low 8, 전부 적용 완료) · **defer 4**(DW-684~687) · reject 6.

**검증(이번 패스에서 직접 실행·관찰 — 전부 red 확인 후 원복해 green 재확인, B4):**
- `pytest tests/integration` — 일회용 pgvector 컨테이너(pgvector/pgvector:pg17)에 프렐류드 + `0001~0028` 전량 적용 후 **102건 전부 통과**.
- 살아 있는 함수에서 `security definer`·`set search_path`를 떼자 새 검사 **하나만** red(직전까지는 이 변형이 100건 전부 통과였다 — 즉 아무도 안 보고 있었다). 원복 후 green.
- 트리거 배선(`on_auth_user_created`)을 drop → 배선 검사 red. `insert … (id, role, status)`로 `name` 기록을 빼자 → 매트릭스 red. 둘 다 원복 후 green.
- ⑧을 네 가지로 깨서 전부 red 확인: 함수 본문 밖 `update public.profiles …` · `merge into public.profiles …` · `insert into public.profiles … select …`(뒤 둘은 **옛 정규식이 통과시키던 형태**) · `_FIRST_FORWARD_ONLY_NUMBER`를 99로 바꿔 대상 0건 만들기(자기검사가 잡음).
- `_create_user(..., role='admin')`이 실제로 `ValueError`로 거부되는 것 확인. admin 테스트의 세션 변수명을 일부러 틀리자 **양성 대조가 red** — 즉 이 검사가 헛되이 초록일 수 있던 상태를 막았다.
- vitest: `page.tsx`에 ① 스프레드 우회 ② 둘째 `signUp` 호출부를 각각 넣어 red 확인(둘 다 직전 검사에서는 **통과했다**, 실측), 원복 후 **34파일 313건 전부 통과**. URL이 든 정당한 변경은 이제 거짓 red를 내지 않는 것도 확인.
- `npm run lint` exit 0 · `npx tsc --noEmit` exit 0 · `python3 scripts/check_migrations.py` exit 0(동적 프로브 3종 포함).

**잔여 위험:**
- **이 검사들은 아직 CI에서 한 번도 돈 적이 없다**(DW-664). `.github/workflows/tests.yml`은 `on.push.branches: [develop, main]`이라 작업 브랜치 push에서는 안 돈다 — 게이트 시점은 `develop` 병합이다. 이번에 두 테스트 파일의 "CI에서 돈다" 주석에 그 단서를 박았다.
- **DW-678(Flutter 갭)은 여전히 코드 읽기로만 확인된 상태**이고(DW-680), 앱 쪽엔 이 문제를 red로 알려줄 검사가 하나도 없다(DW-686 신규). 게다가 그 5건이 지목한 "Epic 16 첫 스토리"에는 role 얘기가 없다(DW-685 신규) — 지정만 하고 심지 않은 상태다.
- 통합 테스트가 여전히 `buyer`/`seller` 계정으로만 시나리오를 돈다(DW-684 신규). `profiles.role`을 읽는 RLS 정책이 처음 생기는 날 그 정책은 실제 사용자 유형에 대해 미검증인 채 배포된다.
- 원격(운영) Supabase에 `0028` 미적용 — 배포 순서(DB 먼저)를 지키지 않으면 그 창의 가입자가 영구히 `'buyer'`로 남는다(DW-687 신규). 운영 반영은 CLAUDE.md B3에 따라 별도 승인 필요.
- ⑧이 **안 보는 것**을 검사 옆에 적어두었다: 함수 정의 본문 안의 백필, profiles가 아닌 테이블, 마이그레이션 파일 밖의 SQL.

**잔여 산출물(커밋하지 않음):** `_bmad-output/implementation-artifacts/sprint-status.yaml` — 이 세션 시작 시점에 이미 수정돼 있었고, 오케스트레이터가 소유하는 파일이라 손대지 않았다.
