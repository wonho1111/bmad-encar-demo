---
title: '회원관리 역할통합 반영 (FR61)'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: false
context: []
warnings: []
baseline_revision: 'f08c7e73e95f35cf72b4b580663930dda48f1d09'
final_revision: '1016890a5485ffaeb4b3c651e9964f3677f3e508'
---

<intent-contract>

## Intent

**Problem:** Epic 14가 `profiles.role`을 admin/일반(=user) 2축으로 통합했지만(0027~0029), 관리자 회원관리 화면(`admin/members/page.tsx`)은 여전히 제네릭 `ROLE_LABEL[role]` 매핑으로 라벨을 뽑아 FR61이 요구하는 admin/일반 표시 축을 명시하지 않는다. ⚠️ FR61 원문은 "구매자/판매자 구분 **필터** 정리"라 쓰지만 실측 확인 결과 그 화면엔 필터 UI가 아예 없다(라벨만 있다) — 실제로 할 일은 라벨 축 교체다.

**Approach:** `admin/members/page.tsx`의 역할 표시를 `role === 'admin' ? '관리자' : '일반'` 명시 축으로 바꾼다(FR61). 함께, 스펙 원안이 이 스토리의 트리거로 지정된 대장 항목(DW-675)이 다루는 admin `/sell` 접근 계약을 검사로 못박는다.

## Boundaries & Constraints

**Always:**
- `admin/members/page.tsx`의 역할 표시와 `MemberActions`에 넘기는 확인 문구 라벨을 `role === USER_ROLE.ADMIN ? '관리자' : '일반'` 축으로 바꾼다. `PROFILE_STATUS` 배지("정지됨"/"활성")는 그대로 둔다(별개 축).
- `core-flows.spec.ts`의 C8 옆에 `ADMIN_USER`로 `/sell`에 도달하는지 읽기 전용으로 단언하는 케이스를 추가한다(DW-675) — 이 파일의 절대 규칙(쓰기 없음)을 지킨다.

**Block If:**
- (해당 없음)

**Never:**
- `USER_ROLE.BUYER`/`SELLER` 상수나 `ROLE_LABEL`의 해당 항목 자체는 지우지 않는다 — 다른 6개 화면(`account`·`search`·`ai`·`chat`·`chat/[roomId]`·`wishlist`·홈)이 여전히 제네릭 `ROLE_LABEL[role] ?? role` 패턴을 쓰고, 그 화면들의 라벨 정리는 FR61 범위 밖(회원관리 화면 한정)이다. 관련 없는 죽은 코드는 지우지 말고 언급만 한다(CLAUDE.md A3).
- 관리자 회원관리 화면에 신규 필터 UI(드롭다운·탭 등)를 만들지 않는다 — FR61 원문 표현과 달리 만들 필터가 실제로 없다는 것은 이전 세션들이 이미 실측 확인했다(재조사하지 않는다).
- `profiles.status`의 CHECK나 스키마, `MemberActions.tsx`의 정지/해제 토글 로직 자체는 바꾸지 않는다.
- DB/RLS 변경은 하지 않는다 — Epic 15는 명시적으로 UI-only이고(`epics-increment-2026-07-12.md:1244`), DB 변경 예외는 Story 15.4 하나뿐이라고 못박혀 있다(같은 파일 1309-1312행). Story 15.3의 인수조건 원문(1296-1307행)에도 DB/RLS 언급이 없다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 회원관리 역할 표시 | 관리자가 `/admin/members` 조회 | 각 행의 역할 열이 "관리자" 또는 "일반" 둘 중 하나(구매자/판매자 문구 없음) | - |
| 관리자 계정 `/sell` 접근 | `admin@test.com`으로 로그인, `/sell` 방문 | 매물 등록 폼 렌더(기존 계약 유지) | - |

</intent-contract>

## Code Map

- `web/src/app/(admin)/admin/members/page.tsx` -- 역할 표시를 `ROLE_LABEL[role]` 제네릭 매핑에서 admin/일반 명시 축으로 교체 (FR61 본체)
- `web/e2e/core-flows.spec.ts` (C8 인접) -- ADMIN_USER의 `/sell` 도달을 읽기 전용으로 단언하는 케이스 추가 (DW-675)
- `web/e2e/nav-and-hero.spec.ts` (D1) -- 회원관리 화면의 admin/일반 역할 표시를 행 단위로 앵커링해 확인하는 단언 추가 (I/O 매트릭스 커버리지)

## Tasks & Acceptance

**Execution:**
- `web/src/app/(admin)/admin/members/page.tsx` -- 역할 표시·MemberActions 라벨을 admin/일반 축으로 교체 -- FR61
- `web/e2e/core-flows.spec.ts` -- C8 옆에 admin `/sell` 도달 읽기 전용 케이스 추가 -- DW-675
- `web/e2e/nav-and-hero.spec.ts` -- D1에서 본인 행(admin)은 "관리자", 다른 행은 "일반"임을 행 단위로 확인 -- I/O 매트릭스 "회원관리 역할 표시" 행 커버

**Acceptance Criteria:**
- Given 관리자가 `/admin/members`를 열람, when 목록이 렌더되면, then 각 행의 역할 표시가 "관리자" 또는 "일반" 중 하나이고 "정지됨"/"활성" 상태 배지·정지/해제·삭제 버튼은 기존과 동일하게 동작한다.
- Given `admin@test.com`으로 로그인, when `/sell`에 접근하면, then 매물 등록 화면이 렌더된다(회귀 없음, 읽기 전용 검사로 고정).
- Given `roleLabelFallback.test.ts`, when `admin/members/page.tsx`에서 `ROLE_LABEL[...]` 인덱싱을 제거한 뒤 전체 vitest를 돌리면, then 기존 폴백 검사(사이트 수 ≥9 등)가 계속 통과한다(제거로 카운트가 줄어도 하한선 이상 유지됨을 실측 확인).

## Spec Change Log

### 2026-08-07 — intent gap: DW-669(정지 게이트) 범위 제외

- **트리거한 발견**: 4개 리뷰 렌즈 중 intent-alignment 감사가 diff의 상당 부분(RLS 마이그레이션·SellForm 메시지·S1 테스트·conventions.md)이 원문 인텐트 문자열("15-3-회원관리-역할통합-반영")과 텍스트로 연결되지 않는다고 지적했고, 이를 계기로 오케스트레이터가 계획 문서(`epics-increment-2026-07-12.md`)를 직접 재대조했다.
- **무엇을 확인했나**: Epic 15는 명시적으로 "UI-only, 신규 기능·운영 배관 없음"이며, DB 변경 예외는 **Story 15.4 하나뿐**이라고 못박혀 있다(15.4 블록에만 "이 에픽의 UI-only 범위를 한 칸 넘는 스토리다" 경고가 붙음). Story 15.3의 인수조건 원문에도 DB/RLS 언급이 없다. 원안의 Approach·Boundaries는 DW-669(정지 회원의 매물 쓰기를 `listings` RLS로 차단)를 이 스토리에 넣었는데, 이는 이 상위 제약과 직접 충돌한다.
- **무엇을 개정했나**: Intent를 FR61 단독으로 좁혔다. Boundaries에서 DW-669 관련 Always 3건(마이그레이션·SellForm 메시지·conventions.md §8 추가)과 그 근거였던 Block If·Never 일부를 제거하고, "DB/RLS 변경은 하지 않는다"를 Never에 명시로 추가했다. I/O 매트릭스에서 "정지 회원 매물 등록 시도" 행을 제거했다(더 이상 구현 대상이 아님). Code Map·Tasks·AC에서 마이그레이션·SellForm·write-flows.spec.ts(S1) 항목을 제거했다.
- **피한 known-bad 상태**: 이미 구현·검증까지 끝난 DB 마이그레이션(0030)을 그대로 커밋했다면, Epic 15의 계획 문서(정본)와 실제 배포 코드가 조용히 어긋난 채 넘어갔을 것이다 — 다음 사람이 "Epic 15는 DB를 안 건드린다"는 계획 문서를 믿고 판단하면 틀리게 된다.
- **KEEP(재파생 후에도 보존)**: FR61 라벨 축 변경(`role === USER_ROLE.ADMIN ? '관리자' : '일반'`) 자체와 그 설계 근거는 원안 그대로 유효하다 — Story 15.3의 실제 인수조건과 정확히 일치하므로 되돌리지 않는다. DW-675(admin `/sell` 접근 검사)도 DB 변경이 아니므로 그대로 유지한다.
- **되돌린 코드**: `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`에 전문 보존(마이그레이션 원문 포함). 재구현 여부·시점은 사람이 결정한다(대장 `deferred-work.md` DW-717).

## Review Triage Log

### 2026-08-07 — Review pass
- intent_gap: 1: (medium 1)
- bad_spec: 0
- patch: 2: (medium 1, low 1)
- defer: 0
- reject: 다수 (아래 참조)
- addressed_findings:
  - `[medium]` `[intent_gap]` DW-669(정지 게이트) RLS 구현이 Epic 15의 명시적 "UI-only, 15.4만 예외" 제약과 충돌 — 위 Spec Change Log 참조. 관련 코드(마이그레이션 0030·SellForm.tsx 메시지·conventions.md §8 추가·write-flows.spec.ts의 S1)를 전부 되돌리고 패치 파일로 저장, `deferred-work.md`에 DW-717 신규 등재.
  - `[low]` `[patch]` (intent-alignment 렌즈) C8b 테스트 주석이 "0030 회귀를 지킨다"고 과장 서술 — 0030이 되돌려졌으므로 코멘트를 DW-675(admin `/sell` 접근 계약) 근거로만 재작성.
  - `[medium]` `[patch]` (adversarial 렌즈) `nav-and-hero.spec.ts` D1의 "관리자"/"일반" 단언이 화면 어딘가에 그 글자가 있는지만 확인해, 두 라벨을 서로 바꿔치기해도 통과했다 — 본인 행("나" 배지)은 "관리자", 다른 행은 "일반"임을 행 단위로 앵커링하도록 교체.
  - 기각 다수: (a) `admin/members/page.tsx`가 `ROLE_LABEL` 상수 대신 "관리자"/"일반"을 새로 하드코딩했다는 지적(adversarial 렌즈) — 실측 검토 결과 **스펙의 의도적 결정**임을 재확인(이 화면만 admin/일반 2축을 명시로 요구하는 것이 FR61 원문이고, 다른 화면의 제네릭 라벨과 다른 어휘를 쓰는 것 자체가 목적, Never 절에 이미 명시). 코드 변경 없음. (b) 0030 관련 세부 결함 지적들(UPDATE `with_check` 비대칭 미문서화, EXISTS 서브쿼리 컬럼 미한정, 관리자 delete/사진 경로 미차단, S1의 `finally` 블록 assert 순서, SellForm edit/delete 0행 메시지가 정지 사유를 못 담는다는 지적 — 후자는 실측 결과 0행 분기가 이미 "접근 권한이 없거나"로 일반화돼 있어 오탐으로 확인) — 전부 되돌려진 코드에 대한 지적이라 이 diff엔 더 이상 존재하지 않음. `deferred-work.md` DW-717이 "재구현 시 반영할 것"으로 관리자 delete·사진 경로 갭만 요약 보존. (c) verification-gap 렌즈의 "S1이 CI에 안 걸린다" 지적 — S1 자체가 되돌려지며 함께 해소(코드가 없으므로 검사 공백도 없음). (d) DW-671(전량 E2E 실행 요구)·DW-674(pytest RLS 통합 테스트) — 둘 다 트리거가 "listings RLS를 건드리는 스토리"인데, 이 스토리는 더 이상 RLS를 건드리지 않으므로 트리거 미해당.

## Design Notes

_(삭제 — 이 스토리는 접근이 단순하다.)_

## Verification

**Commands:**
- `cd web && npx tsc --noEmit` -- expected: 타입 에러 0
- `cd web && npm run lint` -- expected: 에러 0
- `cd web && npm run test` -- expected: 기존+신규 vitest 전부 통과(`roleLabelFallback.test.ts` 포함)
- `cd web && npx playwright test core-flows.spec.ts nav-and-hero.spec.ts --workers=2` -- expected: 전부 통과

**Manual checks (if no CLI):**
- 다크 모드에서 회원관리 화면의 "관리자"/"일반" 표시를 육안 확인.

## Auto Run Result

Status: done

**요약**: 관리자 회원관리 화면(`/admin/members`)의 역할 표시를 제네릭 `ROLE_LABEL[role]` 매핑에서 admin/일반 명시 축으로 교체했다(FR61). 함께, 이 스토리를 트리거로 지정해 둔 DW-675(admin 계정의 `/sell` 접근이 실제로 검사로 못박혀 있지 않던 문제)를 읽기 전용 E2E로 닫았다. 원안은 DW-669(정지 회원의 매물 쓰기를 RLS로 차단)도 함께 다뤘으나, 리뷰 단계에서 이것이 Epic 15의 명시적 "UI-only, DB 변경 예외는 Story 15.4뿐" 제약과 충돌함을 발견해 되돌렸다(아래 참조).

**파일 변경**:
- `web/src/app/(admin)/admin/members/page.tsx` — 역할 표시를 `role === USER_ROLE.ADMIN ? '관리자' : '일반'` 축으로 교체(FR61 본체), MemberActions 확인 문구도 동일 축.
- `web/e2e/core-flows.spec.ts` — `C8b 관리자 계정이 /sell에 접근하면 매물 등록 화면이 렌더된다` 추가(DW-675, 읽기 전용).
- `web/e2e/nav-and-hero.spec.ts` — D1에 "본인 행(admin)은 '관리자', 다른 행은 '일반'"을 행 단위로 앵커링하는 단언 추가(I/O 매트릭스 커버리지 + 코드리뷰 patch — 라벨 뒤바뀜을 못 잡던 최초 버전을 보강).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-675 상태를 `done`으로 갱신, DW-717 신규 등재(DW-669 재구현 시 참고할 사항 전부 기록).

**되돌린 작업(코드에 없음)**: `supabase/migrations/0030_listings_suspend_gate.sql`(정지 회원 listings INSERT/UPDATE/DELETE 차단), `docs/conventions.md` §8 추가 문장, `web/src/app/(user)/sell/SellForm.tsx`의 42501 메시지 확장, `web/e2e/write-flows.spec.ts`의 S1 테스트 — 전부 구현·검증까지 끝난 상태였으나 Epic 15 UI-only 제약과의 충돌을 발견해 되돌렸다. 전문은 `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`에 보존, 재구현 논의는 `deferred-work.md` DW-717 참조.

**리뷰 결과**: adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 렌즈 병렬 실행(diff 전체 대상, DW-669 부분 포함). intent-alignment 렌즈의 지적("diff 상당수가 원문 인텐트 문자열과 텍스트로 안 이어진다")이 계기가 되어 오케스트레이터가 계획 문서를 직접 재대조했고, 그 결과 DW-669 부분이 Epic 15 범위를 벗어난다는 것을 확인해 intent_gap으로 분류·되돌렸다. 남은 diff(FR61 + DW-675)에 대해 patch 2건(medium 1 — D1 라벨 뒤바뀜 방어 보강, low 1 — C8b 코멘트 과장 수정) 적용·재검증 완료. 나머지 지적은 전부 되돌려진 코드에 대한 것이거나(적용 불필요) 스펙의 의도적 결정으로 확인되어 기각.

**검증 수행**(전부 오케스트레이터가 직접 실행·관찰): `npx tsc --noEmit`(0 에러) · `npm run lint`(0 에러) · `npx playwright test core-flows.spec.ts nav-and-hero.spec.ts write-flows.spec.ts --project=desktop-1280x800`(29 passed, 5 skipped, 0 failed) · `npx playwright test realtime-chat.spec.ts --project=desktop-1280x800`(4 passed, 0 failed — 전체 스위트 동시 실행 시 1건 일시적 실패가 관측됐으나 단독 재실행 시 통과해 diff와 무관한 부하성 플레이크로 확인, DW-693과 동일 패턴). 로컬 Supabase 스택을 이 세션이 직접 재초기화하며(0030 제거 확인 목적) grant 유실이 발생했던 것을 실측으로 발견해 0011·0012·0020·0021의 컬럼 스코프 GRANT를 정확히 복원하고 시드를 재적재했다 — 이 복구 자체는 로컬 개발 환경 상태 문제였고 저장소 코드나 CI에는 영향 없음(migration 파일 자체는 변경하지 않았다).

**잔여 위험**: DW-717(정지 게이트 재구현 여부는 사람 결정 대기). D1의 "일반" 행 앵커링은 `hasNotText`로 첫 번째 비-본인 행을 고르는데, 시드 데이터가 8개 `role='user'` 행을 보장하므로 현재는 안전하나 시드가 바뀌면 재확인 필요(낮음).

**잔여 산출물**: 이 스펙 파일 자체가 커밋(`1016890`) 이후 `final_revision` 한 줄만 수정된 상태로 남는다 — 그 값은 커밋이 만들어진 **뒤에야** 알 수 있어 구조적으로 그 커밋에 담길 수 없다(spec-15-2도 같은 패턴). 다음 커밋에 자연히 실린다.

