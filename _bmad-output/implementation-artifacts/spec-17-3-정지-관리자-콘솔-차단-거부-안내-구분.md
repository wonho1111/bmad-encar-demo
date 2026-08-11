---
title: '17.3 정지된 관리자 콘솔 차단 + 차단된 쓰기의 안내 문구 구분'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: 'e1a1cda'
final_revision: '009c239'  # 3패스 커밋 후 갱신 — 17-1 관례와 동일: 이 줄 자체는 다음(기록용) 커밋에 담긴다
review_loop_iteration: 0
warnings: ['oversized']
followup_review_recommended: true
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-17-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-17-1-정지-회원-쓰기-차단-rls.md'
---

<intent-contract>

## Intent

**Problem:** 17.1이 DB에서 정지 회원의 쓰기를 전부 막았다. 그런데 **화면은 그 사실을 모른다.**
두 층의 기준이 어긋나 있고, 그 결과 사용자가 보는 것은 "차단"이 아니라 "고장"이다.

1. **정지된 관리자가 `/admin` 콘솔에 그대로 들어간다**([[DW-806]]). `requireRole`(`web/src/lib/auth/guard.ts`)이
   `.select('role')`만 하고 `profile?.role !== role`만 비교한다 — **`status`를 읽지도 않는다**
   (2026-08-11 오케스트레이터가 파일을 직접 열어 재확인). DB 쪽 `is_admin_active()`는
   `role='admin' and status='active'`를 요구한다. 그래서 정지된 관리자는 콘솔에 들어가 회원 삭제·
   매물 삭제·거래 복원 버튼을 **전부 살아 있는 상태로** 보고, 누르면 **0행이 돌아와 아무 일도
   일어나지 않는다.** 0행은 예외를 던지지 않으므로 화면·로그 어디에도 흔적이 없다.

2. **차단된 쓰기가 엉뚱한 이유로 안내된다**([[DW-804]] (b)). 정지 회원이 자기 매물을 수정·삭제하면
   RLS가 0행을 돌려주고, 화면은 그걸 기존 분기 그대로 **"본인 매물만 삭제할 수 있습니다.
   (매물을 찾을 수 없거나 접근 권한이 없습니다.)"** 로 안내한다 — **자기 매물인데 소유권 문제라고
   말한다.** 등록 경로는 `42501`이 나서 `toKoreanError`가 *"본인 명의로만 매물을 등록할 수 있습니다"*
   를 띄운다 — 역시 사실과 다르다.

**Value:** 정지는 **의도된 제재**인데 지금은 **버그처럼 보인다.** 조작한 사람은 "관리 도구가
고장 났다" 또는 "내 계정이 이상하다"고 읽고 문의한다. 그리고 그 문의를 받는 사람이 원인을 찾아갈
단서가 화면·로그 어디에도 없다. 17.1이 강제력을 DB에 제대로 심었기 때문에, 이제 남은 일은
**그 강제가 왜 걸렸는지 사람에게 말해 주는 것**이다.

**두 항목을 한 스토리로 묶은 이유:** 둘 다 *"DB는 막는데 화면이 그 사유를 모른다"* 는 같은 결함의
두 표면이고, 해결도 같은 것 하나를 필요로 한다 — **화면이 현재 사용자의 `profiles.status`를
읽는 단일 경로.** 따로 하면 그 조회 헬퍼를 두 번 만들거나, 나중 스토리가 앞 스토리의 것을 못
찾아 두 벌이 생긴다. [[DW-806]]과 [[DW-804]]의 `trigger:`가 서로를 `related:`로 가리킨다.

## Boundaries & Constraints

**Always:**

- **불변식을 먼저 못박는다:**
  *"강제력은 계속 DB에만 있다. 화면이 하는 일은 **이미 DB가 내린 거부를 사용자에게 옳게 설명하는
  것**뿐이다."*
  CLAUDE.md B9 — *"앱 코드로 막으면 화면 하나 더 만들 때 까먹지만, 데이터 계층에 박으면 못
  어긴다."* 17.1 Never 절도 *"안내 문구를 다듬는 것은 되지만, 그것이 강제력의 자리가 되면 안 된다"*
  로 이 작업을 명시 허용한다.

- **⚠️ `requireRole`을 고치면 무한 리다이렉트가 생긴다 — 이걸 모르고 고치면 콘솔이 아예 안 열린다.**
  오케스트레이터가 코드를 읽어 확인한 사실(2026-08-11): `web/src/app/page.tsx`가
  `profile.role === 'admin'`이면 **무조건 `redirect('/admin')`** 을 한다(편의 랜딩, `page.tsx:64` 근처).
  그래서 `requireRole`이 정지된 관리자를 `redirect('/')`로 보내면
  **`/admin` → `/` → `/admin` → …** 이 된다.
  이 축의 처리를 반드시 설계에 포함한다. 선택지(택일하고 근거를 남긴다):
  ⓐ 정지 사용자 전용 안내 화면(예: `/suspended`)으로 보내고, `page.tsx`의 관리자 랜딩 분기도
    `status`를 보게 해 그쪽으로 보낸다 — **두 자리를 락스텝으로 고쳐야 한다.**
  ⓑ `page.tsx`의 관리자 랜딩 분기에 `status === 'active'` 조건을 더해 홈에 머물게 한다.
  어느 쪽이든 **정지된 관리자가 로그인 직후 어디에 도착하는지**가 명확해야 하고, 그 경로를
  **실제로 브라우저로 밟아** 확인한다(추론 금지 — CLAUDE.md B4).

- **화면은 "0행"을 정지로 단정하지 않는다 — 거부가 난 **뒤에** 사유를 조회한다.**
  0행은 최소 세 가지를 뜻한다: ① 타인 매물 ② 이미 삭제됨 ③ 행위자가 정지됨.
  올바른 순서는 **먼저 쓰기를 시도 → 거부(0행 또는 `42501`)를 받으면 → 그때 본인 `status`를 조회 →
  정지면 정지 문구, 아니면 기존 문구**다.
  ⚠️ **순서를 뒤집어 "쓰기 전에 status를 확인하고 막는" 형태로 쓰지 않는다.** 그건 사전 검사이고,
  사실상 화면이 강제력의 자리가 된다(불변식 위반). 그리고 그 사전 검사는 새 화면이 생길 때마다
  빠뜨려진다 — 정확히 B9가 경고하는 실패 형태다.

- **본인 `status` 조회 경로는 하나만 만든다.** `profiles_select_self` RLS(0001)가 본인 행을 열어
  주므로 새 정책은 필요 없다. 헬퍼 하나(`web/src/lib/auth/` 아래)로 두고 **모든 소비처가 그걸
  재사용**한다. 소비처가 각자 `.from('profiles').select('status')`를 쓰면 정본이 흩어진다.

- **문구는 사실만 말한다.** 정지 사유·해제 시점·문의처를 지어내지 않는다(그 데이터가 없다).
  최소 형태: *"정지된 계정입니다. 매물 등록·수정·삭제와 채팅 보내기가 제한됩니다."*
  17.1이 실제로 막는 범위(매물·사진·파일·관리자 쓰기·채팅 발신)와 **정확히 일치**해야 한다 —
  `docs/conventions.md` §8이 그 정본이다. 안 막는 것(열람·찜·안읽음)을 막힌다고 쓰지 않는다.

- **검사는 red를 실제로 확인한다**(CLAUDE.md B4 — *"만들었다가 아니라 잡는다가 완료다"*).
  최소 한 축은 **가드 자체를 되돌려**(status 조건 제거) red를 본다. 그리고 **표기를 바꿔 한 번 더**
  깬다(메모리 `guard-proof-must-vary-shape`).

- **기대값을 피검사 대상에서 다시 계산하지 않는다**(메모리 `self-consistent-assertions-never-fail`).
  `'suspended'`·`'active'`·리다이렉트 목적지 경로는 **글자 그대로 박는다.** 상수를 import해 기대값을
  만들면 상수가 바뀔 때 요청과 기대가 같이 바뀌어 영원히 통과한다(2026-08-10 실측 사례).

- **긍정 대조군을 반드시 짝으로 둔다.** "정지된 관리자가 못 들어간다"만 검사하면 **모든 관리자를
  막는** 구현도 green이다. *"활성 관리자는 전과 똑같이 들어가고 모든 관리 작업이 성공한다"* 를
  같이 고정한다. 문구 축도 마찬가지 — *"타인 매물 접근은 여전히 소유권 문구가 뜬다"*.

- **검사 옆에 "이 검사가 안 보는 것"을 실측해서 적는다**(Epic 13 회고 약속).

- 끝나면 [[DW-806]]을 done으로 닫고, **[[DW-804]]는 (b)만 닫고 (a)는 열어 둔다** — (a)(정지 판매자
  매물 노출 여부)는 사용자 결정으로 **17.4가 맡는다.** `trigger:`를 17.4로 갱신한다(CLAUDE.md B8 —
  *"미룬 항목엔 언제·어디서 고칠지를 대장에 함께 적는다"*).

**Block If (멈추고 escalate):**

- 정지된 관리자의 도착지를 정하는 데 **새 화면이 필요하다고 판단**되면(위 ⓐ), 그 화면의 존재
  자체는 제품 결정이므로 — 만들기 전에 멈추고 묻는다. ⓑ(홈에 머물기)는 새 화면이 아니므로 묻지
  않고 진행해도 된다.
- 본인 `status` 조회가 **로그인 직후 세션에서 실패**하는 것이 확인되면(RLS·GRANT 문제) 멈추고
  묻는다 — [[DW-722]]가 기록한 로컬 한정 GRANT 결손과 구별이 필요하다.

**Never:**

- **DB 정책·마이그레이션을 건드리지 않는다.** 이 스토리는 **웹 화면 전용**이다. 17.1이 심은 강제는
  그대로 두고, 화면이 그걸 설명만 한다.
- **화면 검사를 강제력으로 쓰지 않는다.** 버튼을 숨기거나 비활성화하는 것은 되지만, 그게 **유일한**
  차단이 되는 자리를 만들지 않는다. 지금 막히는 것은 전부 DB가 막는 것이어야 한다.
- **정지 판매자의 매물을 숨기지 않는다.** 그건 [[DW-804]] (a)이고 **17.4의 범위**다. 이 스토리에서
  조회 경로를 손대면 두 스토리의 근거가 섞여 나중에 추적이 안 된다.
- **앱(Flutter)을 건드리지 않는다.** 같은 문제가 앱에도 있지만(`listings_repository.dart`), 이
  스토리는 웹이다. 앱 축은 대장에 **별도 항목으로 등재**하고 `trigger:`를 적어 둔다(조용히 빠뜨리지
  않는다 — 그게 DW-669가 처음 생긴 방식이다).
- **관리자 감사 로그([[DW-718]])를 만들지 않는다.** 별건이고 트리거가 다르다.
- **운영(`main`) 배포를 하지 않는다.** `develop` 커밋까지만(CLAUDE.md B3).

</intent-contract>

## Code Map

- `web/src/lib/auth/guard.ts:21-40` -- `requireRole(role)`. `.select('role')` + `profile?.role !== role`
  → `redirect('/')`. **`status` 미조회.** 이 스토리의 1번 수정 대상.
- `web/src/lib/auth/guard.ts:9-18` -- `requireUser()`. 로그인만 확인. 판매자 화면들이 쓴다 —
  여기에 status를 넣을지 여부도 판단 대상(넣으면 **사전 검사**가 되므로 기본은 넣지 않는다).
- `web/src/app/(admin)/layout.tsx:14` -- `requireRole(USER_ROLE.ADMIN)` 단일 호출. `/admin` 전 화면의
  접근 통제가 여기 한 곳에 모여 있다(하위 page들의 주석이 "자동 상속"이라고 명시).
- `web/src/app/page.tsx:60-66` -- `profile.role === USER_ROLE.ADMIN` → `redirect('/admin')`.
  **무한 리다이렉트의 반대편.** 반드시 락스텝으로 본다.
- `web/src/app/(user)/sell/ListingActions.tsx:127` -- 삭제 0행 → `'본인 매물만 삭제할 수 있습니다. …'`.
- `web/src/app/(user)/sell/ListingActions.tsx:77` -- 구매완료 0행 → `'본인 매물만 구매 완료 처리할 수 있습니다. …'`.
- `web/src/app/(user)/sell/SellForm.tsx:349` -- 수정 0행 → `'본인 매물만 수정할 수 있습니다. …'`.
- `web/src/app/(user)/sell/SellForm.tsx:120-131` -- `toKoreanError(err, mode)`. `42501` → 소유권/명의
  문구. **정지도 `42501`로 온다**(INSERT의 `with check` 거부) — 두 사유가 같은 코드로 합류하는 자리.
- `web/src/app/(user)/sell/[id]/edit/page.tsx:62` -- 서버 컴포넌트의 "매물을 찾을 수 없거나 접근
  권한이 없습니다" 화면. 정지 회원은 **본인 매물을 읽을 수는 있으므로**(17.1이 읽기를 안 좁혔다)
  이 화면엔 안 걸린다 — 확인하고 Design Notes에 결과를 적는다(안 걸린다면 건드리지 않는다, A3).
- `supabase/migrations/0001_profiles.sql` -- `profiles_select_self`(`auth.uid() = id`, to authenticated).
  본인 `status` 조회가 이 정책을 탄다. **새 정책 불필요.**
- `supabase/migrations/0032_suspended_write_block.sql` -- 17.1이 심은 강제. **읽기만 하고 수정하지 않는다.**
- `docs/conventions.md` §8 -- 정지가 막는 범위/안 막는 범위의 정본. 안내 문구가 이 목록과 일치해야 한다.
- `web/tests/` (vitest) · `web/e2e/` (playwright) -- 기존 검사 위치와 관례. 새 인프라를 만들지 않는다.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-806]](닫음) · [[DW-804]]((b)만 닫고
  (a)는 17.4로 `trigger:` 갱신) · 앱(Flutter) 축 신규 등재.

## Tasks & Acceptance

**Execution:**

- `web/src/lib/auth/guard.ts` --
  1. 현재 사용자의 `status`를 읽는 **단일 헬퍼**를 추가한다(예: `getOwnStatus()` / `isSuspended()`).
     `profiles_select_self`로 본인 행만 읽는다. 조회 실패 시의 기본값을 **정하고 근거를 적는다** —
     실패를 "정지"로 읽으면 장애 때 전원이 잠기고, "활성"으로 읽으면 안내가 틀릴 뿐 강제는 DB가
     계속 한다. **후자가 기본값**이다(강제력은 DB에 있으므로 화면의 오판이 보안 구멍이 되지 않는다).
  2. `requireRole`이 `.select('role, status')`로 넓히고, `status !== 'active'`면 위 무한 리다이렉트
     축의 결론대로 보낸다.
- `web/src/app/page.tsx` -- 관리자 랜딩 분기를 위 결론과 **락스텝**으로 맞춘다(무한 리다이렉트 차단).
  이 두 파일이 서로의 전제다 — 한쪽만 고치면 콘솔이 안 열리거나 루프가 돈다.
- `web/src/app/(user)/sell/ListingActions.tsx` · `SellForm.tsx` -- 거부(0행 / `42501`)를 받은 **뒤**
  본인 `status`를 조회해 문구를 분기한다. 기존 문구는 **정지가 아닐 때 그대로 유지**한다(A3 —
  안 깨진 걸 고치지 않는다). 삭제·수정·구매완료·등록 4경로 전부.
- (선택, 근거를 남길 것) 정지 상태일 때 `/sell` 화면 상단에 **안내 배너**를 띄운다. 버튼을 없애지는
  않는다 — 없애면 "왜 안 되는지"를 설명할 자리가 사라지고, 화면이 강제력의 자리로 미끄러진다.
- `docs/conventions.md` §8 -- 화면 층의 역할을 한 줄 등재한다: *"정지의 강제는 DB에만 있고, 화면은
  거부 이후 사유를 설명한다(17.3). 화면 검사를 강제력으로 쓰지 않는다."* 강제 장치(테스트 파일명)도 같은 줄에.
- `web/tests/…` -- 단위/컴포넌트 검사: 문구 분기(정지 / 비소유 / 이미 삭제됨 3갈래), `requireRole`의
  분기.
- `web/e2e/…` -- E2E: 정지된 관리자가 `/admin`에 못 들어가고 **루프 없이** 정해진 곳에 도착하는 것,
  활성 관리자는 전과 동일한 것.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- 위 Never·Always대로 갱신.

**Acceptance Criteria:**

- Given `role='admin'`이고 `status='suspended'`인 로그인 사용자, when `/admin`에 접근, then 콘솔이
  렌더되지 않고 정해진 목적지로 이동한다.
- **(무한 리다이렉트 회귀 — 이 스토리가 만들 수 있는 가장 큰 사고)** Given 같은 사용자, when `/admin`
  또는 `/`에 접근, then **리다이렉트가 유한 번에 멈추고** 최종 화면이 렌더된다(브라우저로 실제
  확인 — `ERR_TOO_MANY_REDIRECTS`가 나지 않는다).
- **(긍정 대조군)** Given `role='admin'`이고 `status='active'`인 사용자, when `/admin` 접근 및 회원
  관리·매물 관리·거래 복원 화면 진입, then **전과 동일하게** 전부 정상 동작(회귀 0).
- **(긍정 대조군)** Given `role='user'`인 활성 사용자, when `/admin` 접근, then 전과 동일하게 홈으로
  이동(정지 조건 추가가 기존 역할 게이트를 바꾸지 않았다).
- Given `status='suspended'`인 판매자와 **본인 매물**, when `/sell`에서 삭제를 시도, then 안내가
  **정지 사유**를 말한다(`'본인 매물만 삭제할 수 있습니다'` 계열 문구가 **뜨지 않는다**).
- Given 같은 사용자, when 수정·구매완료·신규 등록을 각각 시도, then 세 경로 전부 정지 사유로 안내된다
  (등록은 `42501`, 나머지는 0행 — **경로마다 신호가 다르다는 것까지 검사가 구분한다**).
- **(긍정 대조군 — 없으면 "전부 정지 문구"와 구별 불가)** Given `status='active'`인 사용자와 **타인의**
  매물 id, when 수정·삭제를 시도, then **기존 소유권 문구가 그대로** 뜬다(정지 문구가 아니다).
- **(긍정 대조군)** Given `status='active'`인 판매자와 본인 매물, when 등록·수정·삭제·구매완료,
  then 전부 성공(회귀 0).
- **(사전 검사가 아님을 고정)** Given `status='suspended'`인 사용자, when 매물 삭제를 시도,
  then **DELETE 요청이 실제로 DB까지 간다**(화면이 미리 막아 요청을 안 보내는 형태가 아니다).
  네트워크 호출 또는 서버 로그로 확인한다 — 이 단언이 불변식("강제력은 DB에만")을 지키는 자리다.
- Given 안내 문구, when `docs/conventions.md` §8의 "막는 범위"와 대조, then 문구가 말하는 제한
  범위가 §8과 일치한다(막지 않는 것을 막힌다고 쓰지 않는다).
- **(red 증명 ⓐ)** Given `requireRole`에서 `status` 조건을 제거한 판, when 관리자 콘솔 검사를 실행,
  then 실패한다. 원복 후 통과.
- **(red 증명 ⓑ — 표기를 바꿔서)** Given 조건을 `status !== 'suspended'`가 아니라 다른 형태로
  뒤집은 판(예: 비교 대상을 `'active'`가 아닌 값으로), when 실행, then **긍정 대조군 쪽**이 실패한다
  (활성 관리자가 막힌다). 서로 다른 단언이 red가 되는 것까지 확인한다.
- Given 웹 전체 검사(vitest + playwright), when 실행, then 기존 검사 전량 green(회귀 0) + 새 검사 green.

## Design Notes

- **무한 리다이렉트 축: ⓑ를 골랐다**(`page.tsx`의 관리자 랜딩 분기에 `status === 'active'` 조건을
  더해 홈에 머물게 함) — ⓐ(`/suspended` 새 화면)는 Block If 조건("새 화면이 필요하다고 판단되면
  멈추고 묻는다")을 건드리므로, 새 화면 없이 기존 홈으로 충분한 ⓑ를 택했다. **브라우저로 실제
  밟은 결과**(2026-08-11, Playwright로 직접 조작): `admin@test.com`을 `suspended`로 전환 →
  `/admin` 직접 접근 시 리다이렉트가 유한 번에 끝나고 최종 URL이 `/`(`ERR_TOO_MANY_REDIRECTS`
  없음, 콘솔 에러 0건) → 이어서 `/`에 재접근해도 `/admin`으로 되튕기지 않고 `/`에 머묾(왕복 확인).
  이후 `admin@test.com`을 다시 `active`로 되돌려 로그인하니 즉시 `/admin`으로 정상 유도되고 콘솔이
  렌더됨(긍정 대조군, 회귀 0). 스크린샷: `suspended-admin-home.png`·
  `suspended-admin-blocked-from-admin.png`·`active-admin-console-ok.png`(세션 스크래치패드에 보관).
  ⚠️ 이 확인은 **수동 1회성 조작**이었다 — `web/e2e/suspended-access.spec.ts`의 자동 스위트는
  `fullyParallel: true`로 다른 스펙 파일이 같은 시각에 공유 시드 계정을 쓰기 때문에 이 계정들을
  **의도적으로 건드리지 않고** 전용 계정을 만들어 쓴다(그 파일 헤더 참고) — 이 절의 수동 절차를
  자동 스위트에 그대로 옮기면 안 된다.

- **⚠️ 2026-08-11 후속 리뷰 실측 정정 — `/admin` 게이트는 "미리 알려줄 뿐"이 아니다(쓰기와 읽기의
  강제 자리가 다르다).** 1패스는 `guard.ts` 주석과 `docs/conventions.md` §8에 *"DB의
  `is_admin_active()`가 이미 `role='admin' and status='active'`를 요구하므로 이 게이트는 못 막아도
  DB가 막는다"* 고 적었다. **읽기 축에서 거짓이다.** `supabase/migrations/0032_suspended_write_block.sql`
  을 직접 열어 확인한 결과(파일 주석 13~18·45~46·265~266 + 정책 정의 실측):
  - 관리자 **쓰기**(회원 삭제·매물 삭제·복원 RPC) — `is_admin_active()`로 교체돼 DB가 막는다. ✅
  - 관리자 **읽기**(콘솔의 회원·매물·채팅 목록/상세) — `listings_select_admin`·`profiles_select_admin`·
    `chat_*_select_admin`·`listing_images_select_admin`을 **일부러 `is_admin()` 그대로 뒀다**
    (0032가 그 결정을 명시한다: `is_admin()`을 전역으로 좁히면 읽기 정책까지 함께 좁아진다).
  즉 정지된 관리자는 DB 수준에서 **여전히 관리자 읽기 권한을 갖고 있고**, `requireRole`의 `status`
  검사가 **콘솔 열람의 유일한 차단**이다. 결과적으로 이 스토리는 §8의 "정지는 열람을 막지 않는다"에
  대한 **예외를 하나 만들었다** — 그 사실을 몰랐다면 다음 사람이 *"어차피 DB가 막는다"* 를 근거로
  이 조건을 지웠을 것이고, 그러면 정지된 관리자가 회원 개인정보·채팅 로그를 다시 열람하게 된다.
  이번 패스에서 `guard.ts` 주석과 §8 정본을 **사실대로 고치고**, 그 예외를 §8에 명시 등재했다(패치 1).
  (Intent 자체가 "정지된 관리자가 콘솔에 들어가는 것"을 고칠 결함으로 지목했으므로 **동작은 의도대로**다 —
  틀린 것은 코드가 아니라 그 근거로 적힌 문장이었다.)

- **`status` 조회 실패 시 기본값을 "활성"으로 둔 근거**: 강제력은 여전히 DB(RLS, `0032`)에 있으므로
  화면이 상태를 잘못 판단해도 결과는 "안내 문구가 틀릴 뿐"이지 쓰기가 실제로 통과하지는 않는다
  (보안 구멍이 아니다). 반대로 실패를 "정지"로 읽으면 일시적 조회 장애(네트워크 순단·GRANT 결손 등)
  만으로 활성 사용자 전원이 정지 안내를 보게 된다 — 오탐의 파급 범위가 훨씬 크다. **이 판단이
  틀리는 조건**: `profiles` 조회가 구조적으로(일시적이 아니라 지속적으로) 실패하는 경우 —
  예를 들어 [[DW-722]]류의 로컬 한정 GRANT 결손이 운영에도 있다면, 정지 회원이 계속 "활성"으로
  오판돼 정지 사유 안내를 영영 못 받는다(단, 그 경우에도 DB의 `listings_insert_own`/`update_own`/
  `delete_own` with check가 실제 쓰기는 계속 막으므로 데이터 보호는 유지된다 — 사용자 경험만
  나빠진다). 이번 리뷰 패스에서 조회 실패를 `console.error`로 남기도록 보강해, 그 지속 실패가
  최소한 로그에는 흔적을 남기게 했다(패치 3).

- **`/sell/[id]/edit` 서버 컴포넌트가 정지 축에 걸리는지 확인 결과**: **안 걸린다** — 코드 확인
  (`.eq('seller_id', user?.id ?? '')`만으로 조회, `status` 조건 없음) + 브라우저로 실측(정지시킨
  `seller@test.com`으로 `/sell/{listingId}/edit` 접근 → "매물 수정" 폼이 정상 렌더, "매물을 찾을 수
  없거나 접근 권한이 없습니다" 문구는 뜨지 않음). 17.1이 읽기(SELECT)를 안 좁혔으므로 예상대로다 —
  A3(안 깨진 걸 고치지 않는다)에 따라 이 파일은 손대지 않았다.

- **4개 쓰기 경로의 실측 신호 표**:

  | 경로 | 동작 | 신호 |
  |---|---|---|
  | 구매 완료 | `ListingActions.tsx` UPDATE(`status='sold'`) | 0행 |
  | 삭제 | `ListingActions.tsx` DELETE | 0행 |
  | 수정 | `SellForm.tsx` UPDATE | 0행 |
  | 신규 등록 | `SellForm.tsx` INSERT | `42501`(with check 위반) |

  전부 `web/e2e/suspended-access.spec.ts` B4~B7로 브라우저 기준 실측했고, 오케스트레이터가 직접
  수정 경로 하나(쏘나타 매물 UPDATE)를 브라우저로 재현해 네트워크 탭에서 실제
  `PATCH .../rest/v1/listings?id=eq...` → `200 OK`(빈 배열, 0행) → 뒤이은
  `GET .../rest/v1/profiles?select=status` 순서를 직접 확인했다(사전 검사가 아니라 거부 **뒤**
  조회라는 증거). 리뷰에서 이 증거가 E2E 스위트 자체에는 없다는 지적(verification-gap)이 나와
  B2·B4~B7에 동일한 네트워크 단언을 추가하는 패치를 별도로 진행한다.

- **red 증명 ⓐ·ⓑ 실행 로그 요약** (구현 세션 보고, `web/src/lib/auth/guard.test.ts` 대상):
  - ⓐ(status 조건 제거): "정지된 관리자는 홈(/)으로 리다이렉트된다" 단언만 실패, 나머지(긍정
    대조군 포함) green 유지 → 원복 후 전량 green.
  - ⓑ(비교를 `status !== 'active'`가 아니라 `status === 'active'`로 반대 방향 뒤집음): 이번엔
    **긍정 대조군**("활성 관리자는 리다이렉트 없이 통과한다") 단언이 실패 → 서로 다른 단언이
    서로 다른 변형에서 깨지는 것까지 확인(메모리 `guard-proof-must-vary-shape`) → 원복 후 전량
    green.

- **`(선택) /sell 상단 안내 배너`를 만들지 않은 근거**(스펙이 "근거를 남길 것"이라 요구했는데
  1패스가 비워 뒀다 — 2026-08-11 후속 리뷰 패치): **넣지 않았다.** 이 스토리가 고치는 4개 경로는
  전부 사용자가 버튼을 누른 **직후** 정지 사유를 말해 준다 — 배너는 같은 정보를 한 번 더 보여줄 뿐
  새로 알려 주는 것이 없다(A2 — 요청받지 않은 화면 요소를 넣지 않는다). 반면 배너가 실제로 값을
  갖는 자리는 `/sell`이 아니라 **정지된 관리자가 도착하는 홈**인데, 거기는 이 스토리가 안내를
  아예 안 한다(아래 "안 보는 것" 참고, [[DW-814]]로 등재). 배너의 존재 자체가 제품 결정이므로
  그 판단은 대장 항목의 `fix_sketch`에 "착수 전 사용자 확인"으로 남겼다.

- **이 검사가 안 보는 것** (실측 기반):
  - **앱(Flutter)의 같은 경로는 안 본다.** `listings_repository.dart` 등 앱 쪽 쓰기 경로는 이번
    스토리 범위 밖(스펙 Never 절)이며, DW-812로 대장에 별도 등재했다.
  - **정지된 관리자에게 "왜 튕겼는지"를 말해 주지 않는다.** 콘솔에서 홈으로 보내기만 하고 홈에
    안내가 없다 — Intent의 Value("그 강제가 왜 걸렸는지 사람에게 말해 주는 것")가 매물 축에서는
    달성됐지만 관리자 축에서는 **차단만 하고 설명은 못 했다**. 2026-08-11 후속 리뷰가 코드·E2E
    양쪽에서 확인(도착지 `page.tsx`에 배너 없음, E2E A그룹도 URL만 단언). [[DW-814]]로 등재.
  - **웹 채팅 발신은 안 본다 — 그런데 새 문구가 그 표면을 약속한다.** `SUSPENDED_WRITE_MESSAGE`가
    "채팅 보내기가 제한됩니다"라고 말하는데 `web/src/lib/messages.ts`는 `42501`을 여전히 "잠시 후
    다시 시도해주세요"로 안내한다(`grep` 실측 0건 배선). [[DW-813]]로 등재.
  - **사진·파일(Storage) 업로드 실패는 사유를 구분하지 않는다.** §8의 차단 범위엔 있지만 문구에도
    배선에도 없다. [[DW-815]]로 등재.
  - **관리자 콘솔 안쪽의 쓰기 버튼은 안 본다.** 진입 게이트가 대부분 가리지만, 콘솔을 연 채
    세션 중에 정지되면 버튼 클릭이 REST로 직행해 게이트를 안 탄다. [[DW-816]]으로 등재.
  - **세션 만료로 인한 거부를 "재로그인 필요"로 구분하지 못한다.** 만료되면 RLS가 anon으로 보아
    본인 매물도 0행이 돌아오고, `getOwnStatus`는 세션이 없으니 'active'로 폴백한다 — 사용자는
    자기 매물인데 "본인 매물만 …" 문구를 본다. 이번 패스에서 **로그는 남기게** 했고(패치 7),
    그 로그의 존재를 단위 검사가 고정한다. 구분해 **안내**하려면 호출부가 3상태를 받아야 하고
    그건 이 스토리 범위 밖이다.
  - **역방향 오귀속은 안 본다** — 정지된 사용자의 거부는 실제 사유(타인 매물·이미 삭제됨)와 무관하게
    전부 정지 문구가 된다. 그 사용자에게 정지가 사실이긴 하므로 의도적으로 둔다(`status.test.ts`
    하단에 한계로 명시).
  - **거부와 사유 재조회 사이의 경합(TOCTOU)를 안 본다.** `getOwnStatus`는 쓰기 거부와 **별도의**
    네트워크 왕복이다 — 그 짧은 틈에 관리자가 해당 계정의 `status`를 바꾸면(정지↔해제), 화면에
    뜨는 사유가 실제 거부 당시의 사유와 어긋날 수 있다(edge-case-hunter 리뷰가 실측 근거 없이
    코드 검토로 지적, 발생 확률은 매우 낮음 — 관리자 조작과 사용자 클릭이 같은 순간에 겹쳐야
    한다). DB 쪽에서 쓰기 결과와 사유를 한 응답으로 묶는 RPC 없이는 구조적으로 못 없애는
    창(window)이고, 그런 RPC를 새로 만드는 것은 이 스토리의 Never 절(DB 정책·마이그레이션을
    건드리지 않는다)을 벗어난다.
  - **조회 실패가 "정지도 아니고 활성도 아닌 제3의 신호"로 사용자에게 구분되지 않는다.** 실패는
    항상 "활성"과 동일하게 보인다(위 기본값 근거 참고) — 실패 자체를 사용자에게 알리는 문구는
    없다.
  - **"비소유"와 "이미 삭제됨"을 서로 다른 문구로 구분하지 못한다.** 둘 다 `status='active'` +
    0행이라는 같은 신호이기 때문에(`web/src/lib/auth/status.test.ts`가 이 계층의 한계로 명시).
  - **정적 계약 검사는 "의미가 같은 다른 표기"를 구분하지 못한다(3패스 실측).** `page.tsx`의 락스텝
    조건에서 두 비교의 **순서만 맞바꾸면**(`status === ACTIVE && role === ADMIN`) 동작은 완전히
    동일한데 단언이 red가 된다. 정규식이 코드의 *의미*가 아니라 *형태*를 보기 때문이고, 이건 이
    기법의 구조적 한계다(반대 방향의 구멍 — `&&`를 `||`로 바꾸는 것 — 은 3패스에서 막았다).
    실패해도 개발자를 곧장 그 코드로 데려가므로 잘못된 수정을 유도하지는 않지만, **정당한
    리팩터가 red를 낼 수 있다**는 것은 알고 있어야 한다.

## Verification

- `cd web && npm run test` (vitest) · `npm run test:e2e` (playwright) — 전량 green.
- 브라우저로 **정지된 관리자** 계정을 만들어 `/admin`·`/`를 실제로 눌러 본다(루프 없음 확인).
- 브라우저로 **정지된 판매자** 계정으로 `/sell`에서 삭제·수정·등록을 눌러 문구를 눈으로 확인한다.
- 위 두 가지는 스크린샷을 남긴다(원격 조종 키트 사용 시 Discord 보고 — CLAUDE.md B4).
- 활성 관리자·활성 판매자로 같은 동선을 밟아 회귀가 없음을 확인한다.

## Review Triage Log

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 1, low 6)
- defer: 0
- reject: 2
- addressed_findings:
  - `[medium]` `[patch]` `web/e2e/suspended-access.spec.ts`의 B2·B4~B7이 문구·DB 상태만 확인하고
    실제 네트워크 요청(DELETE/PATCH/POST가 `/rest/v1/listings`까지 갔는지)은 확인하지 않아, 스펙
    AC "(사전 검사가 아님을 고정)"가 요구한 증거 수준에 못 미쳤다(verification-gap·blind-hunter
    독립 지적, 동일 claim으로 중복 제거) — `waitForListingsRequest` 헬퍼를 추가해 각 쓰기 시도에
    실제 응답 관측 단언을 붙였다. 재실행 확인: 8/8 green.
  - `[low]` `[patch]` `status.ts`·`guard.ts`·`page.tsx`가 `PROFILE_STATUS` 상수 대신 리터럴
    문자열 `'active'`/`'suspended'`를 직접 썼다(같은 diff의 `LISTING_STATUS` 사용과 불일치) —
    세 파일 모두 상수 참조로 교체.
  - `[low]` `[patch]` `getOwnStatus`(status.ts)·`requireRole`(guard.ts)이 `profiles` 조회 실패를
    로그 없이 삼켰다 — 이 스토리가 고치려는 "0행 실패는 흔적이 없다"가 새 코드 안에 재현된
    아이러니(blind-hunter 지적) — 두 곳 다 실패 시 `console.error`를 남기도록 보강(폴백 동작은
    불변).
  - `[low]` `[patch]` `guard.ts`·`page.tsx`가 스펙 Always절("본인 status 조회 경로는 하나만
    만든다")과 달리 `getOwnStatus`를 안 쓰고 각자 쿼리한다(blind-hunter·intent-alignment 독립
    지적, 동일 claim으로 중복 제거) — 재구조화 대신(왕복 1회 추가라는 대가가 더 크다고 판단)
    두 자리 모두 "역할+정지를 한 번에 묻는 별개 게이트"라는 의도적 예외임을 코드 주석으로 명시.
  - `[low]` `[patch]` 이 스펙의 `## Design Notes`가 빈 템플릿이었고, `SellForm.tsx` 새 주석이
    가리키는 "실측표"가 실재하지 않았다(blind-hunter 지적) — 오케스트레이터가 구현 세션의 보고와
    직접 확인한 브라우저·네트워크 증거로 Design Notes를 채움(위 절 참고).
  - `[low]` `[patch]` `guard.ts`의 `requireRole` status 검사가 `role`과 무관하게 걸려, 나중에
    열람 전용 role에 재사용되면 `docs/conventions.md` §8("정지는 열람을 막지 않는다")을 조용히
    어길 수 있다(edge-case-hunter 지적, 현재는 ADMIN 전용이라 실피해 없음) — 코드 변경 대신(현재
    없는 시나리오에 조건을 미리 넣는 건 A2 위반) 재사용 전 재검토를 요구하는 주석만 추가.
  - `[low]` `[patch]` `deferred-work.md`의 신규 DW-812가 근거 없이 `severity: low`였는데, 동일
    실패 모드인 DW-804는 `medium`이었다(blind-hunter 지적) — `medium`으로 맞추고
    `reason_for_severity` 한 줄 추가.
- reject 2건(노이즈로 판단, 조치 없음): `getOwnStatus` 반복 호출의 캐싱 부재(blind-hunter, 순수
  UX 성능 관찰 — 지금 범위에서 캐싱을 넣는 건 A2가 경고하는 과설계); red 증명이 diff만으로는
  재검증 불가하다는 관찰(intent-alignment — red 증명은 태생적으로 일시적 산출물이고,
  `guard.test.ts`의 리터럴 기대값을 직접 읽어 방법론 타당성은 별도로 확인했다).
- 코드 변경 없이 문서(Design Notes "안 보는 것")로만 반영한 관찰 1건: `getOwnStatus` 재조회가
  쓰기 거부와 별도 왕복이라 그 사이 status가 바뀌면 사유가 어긋나는 경합(edge-case-hunter) — DB
  쪽에서 결과·사유를 한 응답으로 묶는 RPC 없이는 구조적으로 못 없애고, 그런 RPC는 스펙 Never절
  (마이그레이션 금지)을 벗어난다.

### 2026-08-11 — Review pass (2차, 후속)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 6, low 6)
- defer: 4: (high 0, medium 2, low 2)
- reject: 9
- addressed_findings:
  - `[medium]` `[patch]` **`guard.ts` 주석과 `docs/conventions.md` §8이 사실이 아닌 강제 근거를
    적었다** — *"is_admin_active()가 이미 요구하므로 못 막아도 DB가 막는다"*. `0032`를 직접 열어
    확인한 결과 그 함수는 **쓰기 정책 전용**이고 관리자 SELECT 정책 4종은 `is_admin()` 그대로다
    (0032 주석 13~18·45~46·265~266이 그 결정을 명시). 즉 `requireRole`의 status 검사가 **콘솔
    열람의 유일한 차단**이며, 이 스토리는 §8 "정지는 열람을 막지 않는다"의 예외를 만들었다
    (blind-hunter·edge-case-hunter 독립 지적, 동일 claim으로 중복 제거) — 두 자리의 문구를
    사실대로 고치고 그 예외를 §8 정본에 명시 등재. 동작(코드)은 Intent대로라 그대로 뒀다.
  - `[medium]` `[patch]` **1패스의 유일한 medium 패치가 실질적으로 아무것도 단언하지 않았다** —
    E2E 5곳의 `expect(res.url()).toContain('/rest/v1/listings')`는 `waitForListingsRequest`의
    predicate가 **이미 걸러 놓은** 값을 재확인하는 항상-참 단언이었다(3개 렌즈 독립 지적,
    메모리 `review-patches-need-their-own-pass`와 같은 형태) — predicate가 보장하지 않는 것으로
    교체: 0행 경로 4곳은 `status()===200` + 본문 `[]`, 등록 경로는 본문 `code==='42501'`.
    **실행으로 확인**(추측으로 박지 않았다): 8/8 green.
  - `[medium]` `[patch]` **배선·순서 계약을 CI가 못 본다** — 두 단위 검사가 스스로 "배선은 안
    본다"고 적고 E2E에 넘겼는데, `.github/workflows/tests.yml`(22행)이 E2E는 CI에 배선돼 있지
    않다고 직접 적는다. 리포엔 이미 이 사각지대 때문에 만든 정적 스캔 계약 검사 3건이 있는데
    (`restoreSoldWiringContract.test.ts` 등) 그 선례를 안 따랐다(verification-gap 3건, 동일
    근본원인) — `web/src/lib/auth/__tests__/suspendedGateWiringContract.test.ts` 신설:
    두 게이트의 락스텝 + 4개 쓰기 경로의 **"거부 뒤 조회" 순서**를 고정한다(문구가 같아도
    사전 검사화는 순서만이 구분한다).
  - `[medium]` `[patch]` `status.test.ts`가 기대값을 **피검사 모듈에서 import**했다
    (`toBe(SUSPENDED_WRITE_MESSAGE)`) — 스펙 Always 절과 메모리
    `self-consistent-assertions-never-fail`의 직접 위반(문구를 빈 문자열로 바꿔도 통과) —
    사용자에게 실제로 뜨는 문자열을 글자 그대로 박았다.
  - `[medium]` `[patch]` `guard.test.ts`의 가짜 클라이언트가 `select()` 인자를 무시해
    **가장 그럴듯한 회귀**(`.select('role, status')` → `.select('role')`, 이 스토리의 before-state)를
    못 잡았다(1패스 red 증명 ⓐ는 *비교*만 되돌렸고 *투영*은 안 건드렸다 — 메모리
    `guard-proof-must-vary-shape`) — 요청한 컬럼만 돌려주도록 고치고 select·eq 인자 단언 추가.
  - `[medium]` `[patch]` 정지된 관리자가 홈으로 튕길 때 **아무 안내가 없다** — Intent의 Value
    ("왜 걸렸는지 말해 주기")가 관리자 축에선 미달(blind-hunter·edge-case-hunter 독립 지적).
    배너 추가는 스펙이 요구하지 않은 UI이고 존재 자체가 제품 결정이라 코드로 넣지 않고,
    Design Notes "안 보는 것"에 한계를 명시 + [[DW-814]]로 대장 등재(trigger 포함).
  - `[low]` `[patch]` E2E B6의 `not.toBe('9990000')` 음성 단언 — 행이 사라져 `runPsql`이 빈
    문자열을 줘도 통과했다(같은 파일 B5가 삭제를 시도하므로 실제로 가능한 상태). 원래 값
    `12345000` 양성 단언으로 교체(형제 단언 3개는 이미 양성이었다).
  - `[low]` `[patch]` `getOwnStatus`의 **세션 없음** 경로에 로그가 없었다(profiles 조회 실패엔
    1패스가 넣었는데 비대칭) — 이 함수는 거부 뒤에만 불리므로 세션 없음 = 만료 의심이고 로그
    가치가 크다. 로그 추가 + "안 보는 것"에 세션 만료 축 기록.
  - `[low]` `[patch]` 1패스가 넣은 `console.error` 두 줄을 **보는 검사가 없었다**(지워도 전량
    green) — `vi.spyOn`으로 두 실패 경로의 흔적을 고정.
  - `[low]` `[patch]` `guard.test.ts`의 `beforeEach`가 `h.profile`을 리셋하지 않아 테스트 순서
    의존이 있었다 — 리셋 추가.
  - `[low]` `[patch]` §8이 E2E를 "강제 장치"로 등재했는데 **CI 미배선**이라는 사실이 빠졌다 —
    로컬 전용임을 명시하고, CI에서 실제로 도는 강제 장치(신설 계약 검사 포함)를 구분해 표기.
  - `[low]` `[patch]` 스펙의 "(선택, 근거를 남길 것) `/sell` 안내 배너"를 만들지 않았는데 근거가
    없었다 — Design Notes에 판단과 근거 기록(배너가 실제로 값을 갖는 자리는 `/sell`이 아니라
    정지 관리자가 도착하는 홈이고, 그건 [[DW-814]]로 넘겼다).
- defer 4건(전부 **신규** 대장 항목으로 등재, 기존 항목은 건드리지 않음):
  - `[medium]` [[DW-813]] 웹 채팅 발신의 정지 거부가 여전히 일반 오류 문구 — 새 문구가 사용자에게
    "채팅 보내기가 제한됩니다"라고 약속한 표면인데 배선이 0건이다(verification-gap·intent-alignment).
  - `[medium]` [[DW-814]] 정지된 관리자에게 사유 안내 부재(위 패치 6의 짝).
  - `[low]` [[DW-815]] 사진·파일(Storage) 업로드 실패가 정지 사유를 구분하지 않음.
  - `[low]` [[DW-816]] 관리자 콘솔 안쪽 쓰기 버튼의 0행 문구가 여전히 사유 미구분(낡은 탭 창).
- reject 9건(노이즈 또는 조치 불가로 판단): `page.tsx`가 select 에러를 무시해 이론상 무한
  리다이렉트가 가능하다는 지적(**변경 전에도 동일한 형태** — pre-existing이고 두 게이트가 매
  요청 번갈아 실패해야 성립) · DW-804의 `resolution:`+`status: open` 조합(오케스트레이터 소유
  필드, 이 세션은 기존 항목을 수정하지 않는다) · 스펙 frontmatter와 Auto Run Result 본문의
  status 표기 차이(각각 다른 시점의 기록) · DW-812가 실측 없이 등재됐다는 지적(**실측해 보니
  추정이 맞다** — 앱엔 관리자 화면 자체가 없고 `listings_repository.dart`는 0행을 그대로
  반환한다. 기존 항목이라 수정하지 않음) · `requireRole` 재사용 시 §8 위반 가능성(1패스가 이미
  주석으로 처리, 반복 지적) · E2E 이메일의 `Date.now()` 충돌(Playwright는 파일 단위로 워커를
  배정하고 desktop 외 프로젝트는 skip된다) · `SellForm`의 `!created` 폴백에 code가 없다는 지적
  (`.single()` insert는 0행 시 error를 내므로 도달 불가에 가깝다) · 활성 판매자 삭제 성공 경로가
  E2E에 없다는 지적(이 diff는 **0행일 때만** 새 코드가 도는 구조라 성공 경로를 바꾸지 않는다) ·
  B2의 `router.refresh()` 레이스(실측 근거 없는 추측, 8/8 green으로 재현되지 않음).

### 2026-08-11 — Review pass (3차, 후속)
- intent_gap: 0
- bad_spec: 0
- patch: 14: (high 0, medium 6, low 8)
- defer: 1: (high 0, medium 0, low 1)
- reject: 10
- addressed_findings:
  - `[medium]` `[patch]` **신설 계약 검사의 락스텝 정규식이 불리언 연산자를 안 봤다** —
    `page.tsx`의 두 조건 사이를 `[^)]*`로만 건너뛰어 `&&`를 `||`로 한 글자 바꿔도 통과했다
    (blind-hunter·edge-case-hunter 독립 지적, **둘 다 프로브로 green을 실측**). `||`가 되면
    정지 관리자만이 아니라 **모든 활성 로그인 사용자**가 `/`→`/admin`→`/` 무한 리다이렉트에
    빠진다 — 이 파일이 존재 이유로 직접 지목한 사고 ①인데 CI 4잡이 전부 초록이었다. 연산자를
    정규식에 고정. 오케스트레이터 red 확인: `&&`→`||` → 정확히 1건 red.
  - `[medium]` `[patch]` **`sliceBody`의 끝 앵커 `null`이 파일 끝까지 슬라이스했다** —
    `expectOrder`의 "첫 등장이 곧 그 자리" 규칙이 함수 밖까지 적용돼, 배선을 지우고 파일 뒤쪽에
    같은 호출을 가진 죽은 코드를 두면 계약이 통과했다(edge-case-hunter 프로브 실측 7/7 green).
    세 자리(`requireRole`·`handleDelete`·`handleSubmit`)에 실제 종료 앵커 부여 + `guard.ts`는
    파일 말미 형태를 단언. 오케스트레이터 red 확인: 배선 제거 + 파일 끝 데코이 → 2건 red.
  - `[medium]` `[patch]` **핸들러 **밖**의 사전 검사를 못 봤다** — 순서 계약이 4개 핸들러 본문만
    보므로, 컴포넌트 스코프에서 `useEffect`로 미리 조회해 버튼을 죽이는 **가장 자연스러운**
    사전 검사화가 슬라이스 밖이라 보이지 않았다(blind-hunter·verification-gap 독립 지적, 둘 다
    프로브 green 실측). 이건 스토리 불변식("강제력은 DB에만") 자체가 뚫리는 형태다. 파일 전체의
    `getOwnStatus(` 호출 수 == 핸들러 본문 안의 호출 수 단언 추가. 오케스트레이터 red 확인:
    `useEffect`가 아니라 **모듈 스코프 헬퍼** 형태(다른 표기)로도 red.
  - `[medium]` `[patch]` **`requireRole`이 `(admin)/layout.tsx`에 실제로 배선돼 있는지를 아무도
    안 봤다** — `requireUser()`로 바꿔도 367/367 green(verification-gap 프로브 실측).
    2패스가 §8에 *"`requireRole`의 status 검사가 콘솔 열람의 **유일한** 차단"*이라고 못박아
    놓고, 그 단 하나의 호출이 살아 있는지는 CI가 안 봤다. `guard.test.ts`가 "소스 스캔 몫"으로
    넘긴 것을 신설 소스 스캔이 받지 않은 것(blind-hunter도 독립 지적). 계약 추가. 오케스트레이터
    red 확인: `requireUser()` 교체(다른 표기) → 1건 red.
  - `[medium]` `[patch]` **`status.test.ts`의 가짜 클라이언트가 `select`/`eq` 인자를 무시했다** —
    2패스가 `guard.test.ts`에서 고친 바로 그 결함을 이 파일에 포팅하지 않았다. `.select('status')`를
    `.select('role')`로, `.eq('id', user.id)`를 엉뚱한 id로 바꿔도 둘 다 green(verification-gap
    프로브 2형태 실측). `tsc`가 앞엣것은 잡지만 CI `web` 잡은 `lint`+`vitest`만 돌린다
    (`tests.yml:198-217`) — 잡히는 자리가 CI 밖이면 안 잡히는 것이다. 인자 기록·투영 반영 +
    리터럴 단언 추가.
  - `[medium]` `[patch]` **안내 문구가 자기가 뜨는 4경로 중 하나를 열거하지 않았다** —
    `SUSPENDED_WRITE_MESSAGE`는 "매물 등록·수정·삭제와 채팅 보내기"라고 하는데 **구매 완료**
    경로에서도 이 문구가 뜬다(E2E B4가 그 사실을 증명한다). 사용자는 자기가 누른 동작이 목록에
    없는 안내를 읽는다 — 이 스토리가 없애려던 오인을 같은 화면에서 다시 만든다(blind-hunter·
    edge-case-hunter 독립 지적). Intent가 그 문자열을 "**최소 형태**"로 준 데다 "17.1이 막는
    범위와 일치"를 함께 요구하므로 확장이 Intent에 더 충실하다. 문구·`status.test.ts` 리터럴을
    락스텝 갱신.
  - `[low]` `[patch]` B그룹 순서 계약이 **조회한 값이 문구 선택으로 흘러가는지**를 안 봤다 —
    `const status = await getOwnStatus(...)`를 남긴 채 `void status;` 하고 상수를 넘겨도 green
    (verification-gap 프로브 실측). 마지막 토큰을 `writeRejectionMessage(status, …)` 형태로 좁힘.
  - `[low]` `[patch]` `guard.ts`의 `console.error` 분기를 **보는 검사가 없었다** — 통째로 지워도
    green(verification-gap 프로브 실측). 2패스가 `status.ts`의 로그 두 줄은 고정했는데 이 세 번째
    로그만 비대칭으로 남았다. `failSelect` 스위치 + 로그·리다이렉트 동시 단언 추가. 겸사로
    **`guard.ts`는 fail-closed(조회 실패 시 차단), `status.ts`는 fail-open(활성 폴백)** 이라는
    의도적 비대칭을 주석으로 명시(blind-hunter가 "근거가 한쪽만 문서화됐다"고 지적).
  - `[low]` `[patch]` `status.test.ts`의 로그 단언이 `toHaveBeenCalled()`뿐이라 **어느 실패
    경로인지 구분하지 못했다**(무관한 `console.error` 하나만 있어도 통과) — 2패스 패치가 형태만
    바꾼 같은 구멍을 남긴 셈이다(blind-hunter). 두 경로를 메시지 조각으로 구분.
  - `[low]` `[patch]` `guard.test.ts`의 한 테스트 **제목이 하지 않은 검증을 주장했다** —
    "status 컬럼을 요청하지 않으면 정지된 관리자를 통과시킨다"인데 본문은 `requireRole`을 한 번도
    부르지 않고 가짜 클라이언트의 투영만 확인한다(blind-hunter). 제목을 실제 대상으로 정정.
  - `[low]` `[patch]` E2E B7의 42501 단언이 **상태 코드를 안 보고** `json()` 파싱 예외에 무방비였다
    (0행 4경로는 상태+본문을 함께 보는데 등록 경로만 비대칭, blind-hunter) — 실제 관측값
    (PostgREST가 42501을 HTTP 403으로 매핑)을 확인해 박고, `text()`+가드 파싱으로 실패 메시지에
    원문이 실리게 함.
  - `[low]` `[patch]` `status.ts`의 주석이 *"문구는 §8과 정확히 일치한다"* 고 단언하는데 실제로는
    **§8의 진부분집합**이다(사진·파일·관리자 쓰기·조회수 누락) — 2패스가 `guard.ts`의 같은 계열
    거짓 문장은 고쳤으면서 이건 남겼다(blind-hunter). 부분집합임과 그 이유를 사실대로 기재.
  - `[low]` `[patch]` 이 변경이 새로 만든 **`docs/tech-debt.md #168` 인용 3곳이 낡은 상태를
    가리켰다** — 그 번호가 이관된 [[DW-468]]의 실제 상태는 `wont-do 2026-08-10`(사용자가 E2E를
    CI에 **안 붙이기로 확정**)인데, 세 자리 모두 "언젠가 해소될 구조적 한계"처럼 적었다
    (blind-hunter). 정적 계약 검사의 사각지대가 **임시가 아니라 영구**라는 사실이 가려지면 그
    자리를 메우는 투자가 계속 미뤄진다 — §8·계약 검사 헤더·스펙 잔여 리스크를 [[DW-468]] 인용으로 정정.
  - `[low]` `[patch]` 스펙 Design Notes가 수동 검증에서 **공유 시드 계정을 정지시킨 절차**를
    적어 두었는데, `web/e2e/suspended-access.spec.ts` 헤더는 병렬 실행(`fullyParallel: true`)
    때문에 그걸 명시적으로 금지한다(blind-hunter가 "장부와 스펙이 상충한다"고 지적 — 실제로는
    **서로 다른 두 절차**라 상충은 아니었다). 다음 사람이 수동 절차를 자동 스위트에 옮겨 옆
    스펙을 깨지 않도록 Design Notes에 한 줄 명시.
- defer 1건(**신규** 대장 항목으로만 등재, 기존 항목은 일절 건드리지 않음):
  - `[low]` [[DW-817]] `docs/tech-debt.md:166`의 이관 색인이 `#168`을 아직 `열림`으로 적는다 —
    실제 [[DW-468]]은 `wont-do 2026-08-10`이다. 이 변경 밖의 pre-existing 결함이라 defer.
- reject 10건(노이즈 또는 조치 불가로 판단): 문구가 약속한 채팅 배선 부재(이미 [[DW-813]] 등재,
  반복 지적 — 문구에서 "채팅"을 빼는 대안은 Intent가 그 문자열을 직접 지정했으므로 채택 불가) ·
  `ListingActions`의 `error` 분기(42501)가 `writeRejectionMessage`를 안 탄다는 지적(0032가 UPDATE/
  DELETE를 `using`에만 걸어 **현재는 항상 0행**으로 온다 — 도달 불가 시나리오에 방어 코드를 미리
  넣는 건 A2 위반) · `profiles.status`의 제3값 가정(`0001`의 CHECK 제약상 마이그레이션 없이는
  생길 수 없다) · [[DW-804]]의 `resolution:`+`status: open` 조합(3패스 연속 지적이지만 오케스트레이터
  소유 필드이고, 이 세션은 호출 지시로 **기존 항목 수정이 금지**돼 있다) · [[DW-812]]의 실측 결과가
  장부에 없다는 지적(같은 이유로 기존 항목 수정 불가) · `review_loop_iteration`이 0이라는 지적
  (그 카운터는 bad_spec 루프백 전용이고 3패스 모두 bad_spec 0이라 0이 정상) ·
  `sprint-status.yaml`이 미커밋이라는 지적(오케스트레이터 소유 파일, 아래 잔여 아티팩트로 보고) ·
  브랜치가 `develop`이 아니라는 지적(`test/bmad-loop`은 루프 검증용 브랜치로 오케스트레이터 소유) ·
  §8 신규 불릿이 제약과 경위를 섞었다는 지적(§8 전체가 이미 그 서술 밀도이고, 이 불릿만 다르게
  쓰면 A3 "기존 스타일에 맞춘다"를 어긴다) · 장부 [[DW-806]]과 스펙의 검증 계정 기록이 상충한다는
  지적(대조 결과 **상충 아님** — 자동 E2E는 throwaway 계정, 수동 검증은 시드 계정이라는 서로 다른
  두 절차다. 오해 소지만 위 patch 14로 해소).
- 오케스트레이터가 **직접 돌린 red 프로브 4형태**(서브에이전트 보고를 재확인 — 메모리
  `guard-proof-must-vary-shape`: 리뷰·구현 세션의 red/green은 자기가 쓴 표기에서만 성립할 수 있다).
  원복은 전부 백업본으로 했다(메모리 `probe-revert-never-git-checkout`):
  ⓐ `page.tsx`의 `&&`→`||` → 1건 red. ⓑ `(admin)/layout.tsx`를 `requireUser()`로 교체(리뷰어가 쓴
  것과 다른 표기) → 1건 red. ⓒ 사전 검사화를 `useEffect`가 아니라 **모듈 스코프 헬퍼**로(다른 표기)
  → 1건 red. ⓓ `handleSubmit` 배선 제거 + 파일 끝 데코이 → 2건 red. 4형태 모두 원복 후 371/371 복귀.
  **추가 관찰(조치 없음)**: `page.tsx`의 두 조건 **순서를 맞바꾸면**(의미 동일한 정당한 리팩터)
  락스텝 단언이 red가 된다 — 정적 스캔의 알려진 한계이며, 실패 시 개발자를 해당 코드로 데려가므로
  잘못된 수정을 유도하지는 않는다. 위 "안 보는 것"에 함께 적었다.

## Auto Run Result

**요약**: 17.1이 DB(RLS)에서 이미 막아둔 정지 회원의 쓰기를, 화면이 거부 **뒤에** 본인
`profiles.status`를 조회해 옳은 사유로 안내하도록 고쳤다(사전 검사 아님 — 불변식 유지). 두 표면을
고쳤다: ① `/admin` 콘솔 게이트(`requireRole`)가 `role`만이 아니라 `status`도 보게 해 정지된
관리자를 홈으로 돌려보내고, `page.tsx`의 관리자 랜딩 편의 분기를 락스텝으로 맞춰 무한 리다이렉트를
막았다(선택지 ⓑ — 새 화면 없이 홈에 머묾). ② 매물 등록·수정·삭제·구매완료 4개 쓰기 경로의 거부
문구가 정지·비소유·이미삭제를 구분해 안내하도록, 단일 헬퍼 `web/src/lib/auth/status.ts`를 새로
만들고 재사용시켰다. 리뷰 1패스에서 patch 7건(medium 1·low 6)이 나와 전부 반영했다(아래).

**변경 파일**:
- `web/src/lib/auth/status.ts` (신규) — `getOwnStatus`(거부 뒤 본인 status 조회, 실패 시
  `console.error` 후 'active' 폴백) · `writeRejectionMessage`(정지면 정지 문구, 아니면 호출부
  기존 문구 유지).
- `web/src/lib/auth/guard.ts` — `requireRole`이 `.select('role, status')`로 넓어지고 정지도
  홈으로 리다이렉트. 조회 실패 로그 추가, `PROFILE_STATUS` 상수 사용, `getOwnStatus`를 안 쓰는
  이유·향후 재사용 시 재검토 필요성을 주석으로 명시.
- `web/src/app/page.tsx` — 관리자 랜딩 분기가 `status==='active'`일 때만 `/admin`으로 보내
  `requireRole`과 락스텝(무한 리다이렉트 방지). 동일 사유로 `getOwnStatus` 미사용을 주석 명시.
- `web/src/app/(user)/sell/ListingActions.tsx`·`SellForm.tsx` — 구매완료·삭제·수정·등록 4경로가
  거부(0행/`42501`) 뒤 `getOwnStatus`로 사유를 구분. 기존 소유권/미존재 문구는 정지가 아닐 때
  그대로 유지(회귀 0).
- `docs/conventions.md` §8 — 화면 층의 역할(강제는 DB, 화면은 거부 이후 설명만) 한 줄 등재 +
  강제 장치(단위·E2E) 경로 표기.
- `_bmad-output/implementation-artifacts/deferred-work.md` — [[DW-806]] done, [[DW-804]] (b)만
  해소(resolution 기록)하고 (a)는 열어 둔 채 trigger를 17.4로 갱신, 신규 [[DW-812]](앱 축, 코드리뷰
  patch로 severity medium 확정) 등재.
- `web/src/lib/auth/guard.test.ts`·`status.test.ts` (신규, 단위) · `web/e2e/suspended-access.spec.ts`
  (신규, E2E — 리뷰 patch로 각 쓰기 시도에 실제 네트워크 응답 관측 단언 추가).
- 스펙 본문(이 파일) — `status: backlog → ready-for-dev → in-progress → in-review`,
  `baseline_revision` 갱신, Design Notes 전체 작성(오케스트레이터가 구현 보고 + 직접 브라우저·
  네트워크 검증으로 채움), Review Triage Log 1패스.

**리뷰 findings 분류(1패스, 4개 렌즈 병렬 — adversarial·edge-case-hunter·verification-gap·
intent-alignment)**: intent_gap 0 · bad_spec 0 · **patch 7**(medium 1·low 6, 전부 반영) ·
defer 0 · reject 2. 후속 리뷰 권장(`followup_review_recommended`): **true**
(3×medium(1) + 1×low(6) = 9 ≥ 5).

**검증 수행(오케스트레이터가 직접 실행·관찰, CLAUDE.md B4)**:
- `cd web && npm run test` (vitest) — **356/356 passed**(41 files), 패치 전·후 두 번 모두 직접
  재실행해 확인.
- `npx playwright test e2e/suspended-access.spec.ts e2e/core-flows.spec.ts e2e/write-flows.spec.ts
  --project="desktop-1280x800"` — **24/24 passed**(패치 전·후 두 번 모두 직접 재실행), 기존
  회귀 스위트(C1~C9, E1~E6) 포함 회귀 0.
- `npx tsc --noEmit`·`npm run lint` — clean.
- **브라우저 직접 조작(Playwright MCP, 시드 계정 `admin@test.com`/`seller@test.com`을 실제로
  정지→해제)**: ① 정지된 관리자로 `/admin` 접근 → `/`로 귀결, `ERR_TOO_MANY_REDIRECTS` 없음,
  `/` 재접근도 `/admin`으로 안 튕김. 활성 복귀 후 `/admin` 정상 재현(회귀 0). ② 정지된 판매자로
  본인 매물 수정 저장 시도 → 네트워크 탭에서 실제 `PATCH .../rest/v1/listings` → `200`(0행) →
  뒤이은 `GET .../rest/v1/profiles?select=status` 순서를 직접 확인(사전 검사가 아니라는 증거) →
  화면에 "정지된 계정입니다..." 문구 렌더. 삭제 시도도 동일 문구 확인, DB 행은 그대로 남음(psql
  대조). 완료 후 두 계정 모두 원래 상태(active)로 되돌리고 매물 개수(19건) 불변 확인.
- **red 증명(구현 세션 보고, 오케스트레이터가 `guard.test.ts` 코드로 리터럴 기대값 방법론 확인)**:
  ⓐ status 조건 제거 → "정지된 관리자 리다이렉트" 단언만 실패. ⓑ 비교 방향 반전
  (`status === 'active'`) → **긍정 대조군** 단언이 실패 — 서로 다른 변형에서 서로 다른 단언이
  깨지는 것까지 확인(메모리 `guard-proof-must-vary-shape`).

**잔여 리스크**:
- [[DW-804]] (a) — 정지 판매자 매물의 노출·문의 가능 여부는 미해결, 17.4로 이월(trigger 갱신 완료).
- [[DW-812]] — 앱(Flutter)의 동일 경로는 이 스토리가 다루지 않음, 별도 이월.
- `getOwnStatus` 재조회와 실제 쓰기 거부 사이의 경합(관리자가 그 찰나에 status를 바꾸는 경우) —
  발생 확률이 매우 낮고 스펙 Never절(DB 변경 금지) 안에서는 구조적으로 못 없앤다. Design Notes
  "안 보는 것"에 기록.
- 이번 세션이 로컬 Supabase 시드 데이터가 한 차례 비어 있는 것을 발견해 `scripts/seed-local.sh`로
  복구했다(이 스토리와 무관한 환경 문제, 기록만 남김).

---

## 2패스(후속 리뷰) 결과 — 2026-08-11

**왜 한 번 더 돌았나**: 1패스가 `followup_review_recommended: true`(점수 9 ≥ 5)를 남겼다. 4개 렌즈를
다시 병렬로 돌렸고, **1패스가 놓친 것 하나와 1패스 패치 자체의 결함 둘**이 나왔다.

**가장 무거운 발견 — 정본 문서에 사실이 아닌 강제 근거가 박혀 있었다**: 1패스는 `guard.ts` 주석과
`docs/conventions.md` §8에 *"`is_admin_active()`가 이미 요구하므로 이 게이트는 못 막아도 DB가 막는다"*
고 적었다. `0032`를 직접 열어 보니 그 함수는 **쓰기 정책 전용**이고 관리자 SELECT 정책 4종은
`is_admin()` 그대로였다(0032가 그 결정을 파일 주석에 명시한다). 즉 **`requireRole`의 status 검사가
콘솔 열람의 유일한 차단**이고, 이 스토리는 §8의 "정지는 열람을 막지 않는다"에 예외를 하나 만든
것이었다. 동작은 Intent대로라 코드는 그대로 두고, **근거로 적힌 문장**을 두 자리 다 사실대로 고쳐
그 예외를 정본에 등재했다. (이 문장을 안 고쳤다면 다음 사람이 *"어차피 DB가 막는다"* 를 근거로
조건을 지웠을 것이고, 그러면 정지된 관리자가 회원 개인정보·채팅 로그를 다시 열람하게 된다.)

**1패스 패치가 스스로 리뷰 대상이 됐다**(메모리 `review-patches-need-their-own-pass` 재확인):
1패스의 유일한 medium 패치였던 E2E 네트워크 단언 5개가 **항상 참**이었다 — `waitForListingsRequest`의
predicate가 이미 URL을 걸러 놓은 값을 다시 확인하고 있었다(3개 렌즈가 독립적으로 지적). predicate가
보장하지 않는 것(응답 상태·본문)으로 교체했고, **실행해서** 실제 응답과 맞는지 확인했다.

**CI가 못 보던 자리를 CI 안으로 들여왔다**: 두 단위 검사가 스스로 "배선은 안 본다"며 E2E에 넘겼는데
E2E는 CI에 배선돼 있지 않다. 리포엔 이미 같은 사각지대 때문에 만든 정적 스캔 계약 검사가 3건 있었고,
그 선례대로 `web/src/lib/auth/__tests__/suspendedGateWiringContract.test.ts`를 신설했다 — 두 게이트의
락스텝과 4개 쓰기 경로의 **"거부 뒤 조회" 순서**를 고정한다. 순서가 핵심이다: 사전 검사로 끌어올려도
사용자에게 뜨는 문구는 똑같아서, 순서만이 스토리 불변식("강제력은 DB에만")을 지킨다.

**2패스 변경 파일**:
- `web/src/lib/auth/__tests__/suspendedGateWiringContract.test.ts` (신규) — 배선·순서 계약 7건.
- `docs/conventions.md` §8 — 거짓 강제 근거 정정 + `/admin` 열람 차단이 명시적 예외임을 등재 +
  CI에서 실제로 도는 강제 장치와 로컬 전용 E2E를 구분 표기.
- `web/src/lib/auth/guard.ts` — 같은 정정을 주석에(코드 변경 없음).
- `web/src/lib/auth/status.ts` — 세션 없음(만료 의심) 경로에 로그 추가.
- `web/src/lib/auth/status.test.ts` — 기대 문구를 리터럴로 교체(자기일관 단언 제거), 두 실패
  경로의 로그를 `vi.spyOn`으로 고정, "안 보는 것" 4항목 추가.
- `web/src/lib/auth/guard.test.ts` — 가짜 클라이언트가 요청한 컬럼만 반환하도록 수정(투영 회귀
  탐지), select·eq 인자 단언 추가, `beforeEach`에 `h.profile` 리셋.
- `web/e2e/suspended-access.spec.ts` — 항상-참 단언 5곳을 실제 응답 관측으로 교체
  (`expectZeroRowRejection` 헬퍼 + 등록 경로의 `42501` 코드 단언), B6 음성 단언을 양성으로.
- `_bmad-output/implementation-artifacts/deferred-work.md` — **신규 4건만 추가**([[DW-813]]·
  [[DW-814]]·[[DW-815]]·[[DW-816]]). 기존 항목은 상태·resolution 포함 일절 수정하지 않았다.
- 스펙 본문(이 파일) — Design Notes에 실측 정정·배너 미구현 근거·"안 보는 것" 6항목 추가,
  Review Triage Log 2패스, 이 절.

**2패스 findings 분류**: intent_gap 0 · bad_spec 0 · **patch 12**(medium 6·low 6, 전부 반영) ·
**defer 4**(medium 2·low 2, 전부 신규 등재) · reject 9.

**2패스 검증(오케스트레이터가 직접 실행·관찰, CLAUDE.md B4)**:
- `npm test` (vitest) — **367/367 passed**(42 files). 1패스 356 → 새 검사 11건 추가.
- `npx tsc --noEmit` · `npm run lint` — clean.
- `npx playwright test e2e/suspended-access.spec.ts --project="desktop-1280x800"` — **8/8 passed**.
  이 실행이 새 단언(0행 경로 `200`+`[]`, 등록 경로 `code==='42501'`, 원가격 `12345000`)이 **실제
  응답과 일치**함을 확인해 줬다 — 추측으로 박은 값이 아니다.
- `npx playwright test e2e/core-flows.spec.ts e2e/write-flows.spec.ts --project="desktop-1280x800"`
  — **16/16 passed**, 회귀 0.
- **red 증명 4형태**(새 검사가 실제로 잡는지 — "만들었다가 아니라 잡는다가 완료다"). 원복은
  전부 백업본으로 했다(메모리 `probe-revert-never-git-checkout`):
  - ⓐ `page.tsx`의 `&& status === ACTIVE` 제거(락스텝 붕괴 = 무한 리다이렉트) → 락스텝 단언 **1건만** red.
  - ⓑ `handleDelete`의 배선 제거 → 해당 경로 단언 red.
  - ⓒ **거부 판정 앞에 조회를 "추가"만 하고 뒤는 그대로 두는 진짜 사전 검사화** → 처음엔
    **green으로 통과했다**(검사의 실제 구멍을 프로브가 뚫었다). `expectOrder`를 "첫 등장이 곧
    그 자리여야 한다"로 강화한 뒤 red 확인 — 프로브가 없었으면 이 구멍을 모른 채 넘어갔다.
  - ⓓ `guard.ts`의 `.select('role, status')` → `.select('role')`(이 스토리의 before-state 복귀) →
    **긍정 대조군 포함 3건** red. 서로 다른 변형이 서로 다른 단언을 깬다는 것까지 확인.
  - 4형태 모두 원복 후 전량 green 복귀를 확인했다.

**2패스 잔여 리스크**:
- [[DW-813]]~[[DW-816]] 4건 — 위 defer 목록 참고. 전부 `trigger:`를 붙여 등재했다.
- 신설 계약 검사는 **소스 문자열 스캔**이라 한계가 있다: 호출의 존재·순서는 보지만 런타임 동작은
  못 본다(그건 E2E 몫이고 E2E는 CI에 없다 — 구조적 한계다. [[DW-468]](`wont-do 2026-08-10`)가
  이걸 "언젠가 CI가 붙는다"가 아니라 **CI에 붙이지 않기로 확정한 사용자 결정**으로 못박아 뒀다 —
  이 정적 계약 검사들의 사각지대는 임시가 아니라 이 결정이 바뀌지 않는 한 영구적이다).
- ⓒ 프로브가 보여준 대로, 이런 정적 계약 검사는 **표현을 바꾼 우회**에 원리적으로 취약하다.
  지금 판은 "앞에도 호출하면 red"까지 막지만, 예컨대 헬퍼를 감싸 다른 이름으로 부르면 못 본다.

---

## 3패스(후속 리뷰) 결과 — 2026-08-11

**왜 한 번 더 돌았나**: 2패스가 `followup_review_recommended: true`(점수 3×6+1×6 = 24 ≥ 5)를 남겼다.
4개 렌즈를 다시 병렬로 돌렸고, 이번엔 **2패스가 새로 만든 계약 검사 자체의 구멍**이 주된 수확이었다
(메모리 `review-patches-need-their-own-pass`가 세 패스 연속으로 재확인됐다 — 리뷰 패치는 그 자체가
다음 리뷰의 대상이다).

**가장 무거운 발견 — 새 계약 검사가 자기 존재 이유를 못 지켰다.** 2패스가 만든
`suspendedGateWiringContract.test.ts`는 헤더에 자기가 막을 사고 4가지를 열거해 뒀는데, 그중 두
가지가 실제로는 통과했다(리뷰어들이 **프로브를 돌려 green을 실측**했고, 오케스트레이터가 다시
**다른 표기로** 재현했다):
- ① **무한 리다이렉트**: 락스텝 정규식이 두 조건 사이를 `[^)]*`로 건너뛰어 **불리언 연산자를 안
  봤다.** `&&`를 `||`로 한 글자 바꾸면 전량 green인데, 그러면 정지 관리자만이 아니라 **모든 활성
  로그인 사용자**가 무한 리다이렉트에 빠진다.
- ④ **사전 검사화**: 순서 계약이 4개 핸들러 **본문 안만** 봤다. 컴포넌트 스코프에서 미리 조회해
  버튼을 죽이는 — 사전 검사화의 **가장 자연스러운 모양** — 은 슬라이스 밖이라 안 보였다. 이건
  스토리 불변식("강제력은 DB에만") 자체가 뚫리는 형태다.
추가로 `sliceBody`의 끝 앵커가 `null`이면 파일 끝까지 슬라이스해, 배선을 지우고 파일 뒤쪽에 같은
호출을 가진 죽은 코드를 두면 계약이 통과했다. 세 구멍 다 이번에 막고 각각 red를 확인했다.

**게이트가 배선돼 있는지를 아무도 안 봤다.** 2패스가 `docs/conventions.md` §8에 *"`requireRole`의
status 검사가 콘솔 열람의 **유일한** 차단"*이라고 못박았는데(0032가 관리자 SELECT 정책 4종을
`is_admin()` 그대로 뒀기 때문), 그 단 하나의 호출이 `(admin)/layout.tsx`에 살아 있는지는 CI 어디에도
없었다 — `requireUser()`로 바꿔도 367/367 green이었다. `guard.test.ts`가 "소스 스캔 몫"이라 넘긴
것을 정작 신설 소스 스캔이 받지 않은, 책임이 두 문서 사이로 떨어진 형태다. 이번에 계약으로 박았다.

**사용자에게 뜨는 문구가 자기가 뜨는 자리 하나를 빠뜨렸다.** `SUSPENDED_WRITE_MESSAGE`가
"등록·수정·삭제와 채팅"만 열거하는데 **구매 완료** 경로에서도 이 문구가 뜬다(E2E B4가 증명한다).
자기가 방금 누른 동작이 목록에 없는 안내를 읽는 것은, 이 스토리가 없애려던 오인을 같은 화면에서
다시 만드는 일이다. Intent가 그 문자열을 "최소 형태"로 준 데다 "17.1이 막는 범위와 일치"를 함께
요구하므로 확장이 Intent에 더 충실하다고 판단해 문구·검사 리터럴을 락스텝으로 넓혔다.

**낡은 포인터가 사각지대를 임시처럼 보이게 했다.** 이 변경이 새로 만든 `#168` 인용 3곳이 E2E의 CI
미배선을 "언젠가 해소될 한계"처럼 적었는데, 그 번호가 이관된 [[DW-468]]의 실제 상태는
`wont-do 2026-08-10`(사용자가 **안 붙이기로 확정**)이다. 정적 계약 검사의 사각지대가 임시가 아니라
**영구**라는 사실이 가려지면 그 자리를 메우는 투자가 계속 미뤄진다 — 세 자리를 정정하고, 색인 쪽의
같은 오류는 [[DW-817]]로 등재했다.

**3패스 변경 파일**:
- `web/src/lib/auth/__tests__/suspendedGateWiringContract.test.ts` — 연산자 고정, 슬라이스 종료 앵커
  3곳, 핸들러 밖 호출 금지 단언 신설, `(admin)/layout.tsx` 배선 계약 신설, 순서 토큰에 값 결합
  요구. 7건 → 9건.
- `web/src/lib/auth/status.test.ts` — 가짜 클라이언트가 `select`/`eq` 인자를 실제로 반영하도록 수정
  + 리터럴 단언 신설, 로그 단언을 경로별 메시지로 좁힘.
- `web/src/lib/auth/guard.test.ts` — `failSelect` 스위치와 조회 실패 경로 검사 신설(로그 + 리다이렉트
  동시 단언), 오해를 부르던 테스트 제목 정정.
- `web/src/lib/auth/guard.ts` — fail-closed / fail-open 비대칭이 의도임을 주석으로 명시(코드 무변경).
- `web/src/lib/auth/status.ts` — 문구에 "구매 완료" 추가, 문구가 §8의 **부분집합**임을 사실대로 기재.
- `web/e2e/suspended-access.spec.ts` — B7에 상태 코드(403) 단언 추가 + 본문 파싱 방어.
- `docs/conventions.md` §8 — `#168` → [[DW-468]](`wont-do`) 인용 정정.
- `_bmad-output/implementation-artifacts/deferred-work.md` — **신규 [[DW-817]] 1건만 추가.** 기존
  항목은 상태·`resolution:` 포함 일절 수정하지 않았다(호출 지시).
- 스펙 본문(이 파일) — Design Notes에 "안 보는 것" 1항목·수동 검증 절차 주의 1줄 추가,
  Review Triage Log 3패스, 이 절.

**3패스 findings 분류**: intent_gap 0 · bad_spec 0 · **patch 14**(medium 6·low 8, 전부 반영) ·
**defer 1**(low 1, 신규 등재) · reject 10.

**3패스 검증(오케스트레이터가 직접 실행·관찰, CLAUDE.md B4)**:
- `npx vitest run` — **371/371 passed**(42 files). 2패스 367 → 새 검사 4건 추가.
- `npx tsc --noEmit` · `npm run lint` — clean(exit 0).
- `npx playwright test e2e/suspended-access.spec.ts e2e/core-flows.spec.ts e2e/write-flows.spec.ts
  --project="desktop-1280x800"` — **24/24 passed**(1.0분), 회귀 0. 로컬 Supabase 게이트웨이가
  실제로 응답하는지 먼저 확인하고 돌렸다(`http://127.0.0.1:55321/rest/v1/` → 200 — 메모리
  `local-supabase-gateway-silent-death`: 컨테이너 목록이 healthy여도 kong만 죽어 있을 수 있다).
- **red 프로브 4형태를 오케스트레이터가 직접 재현**(구현 세션 보고를 그대로 믿지 않았다 — 메모리
  `guard-proof-must-vary-shape`). 세 형태는 **리뷰어·구현 세션이 쓴 것과 다른 표기**로 깼다:
  게이트 제거는 `requireUser()` 교체로, 사전 검사화는 `useEffect`가 아니라 모듈 스코프 헬퍼로,
  슬라이스 누수는 `handleDelete`가 아니라 `handleSubmit` + 파일 끝 데코이로. 4형태 모두 red를
  확인하고 백업본으로 원복해 371/371 복귀까지 확인했다(`git checkout` 미사용 — 메모리
  `probe-revert-never-git-checkout`).

**3패스 잔여 리스크**:
- [[DW-817]] 1건 — 위 defer 참고(`trigger:` 포함 등재).
- **정적 계약 검사의 한계는 좁아졌을 뿐 사라지지 않았다.** 이번에 세 구멍을 막았지만, 세 패스에
  걸쳐 매번 **새 구멍이 하나씩 나왔다**는 사실 자체가 신호다. 이 기법은 형태를 보지 의미를 보지
  않으므로, 표현을 바꾼 우회(헬퍼를 감싸 다른 이름으로 부르기 등)에는 원리적으로 취약하다.
  런타임을 보는 유일한 검사(E2E)는 [[DW-468]]에 따라 **영구적으로 CI 밖**이다.
- 사용자 표면 3건([[DW-813]] 채팅 · [[DW-815]] Storage · [[DW-816]] 콘솔 내부 쓰기)은 여전히 열려
  있다 — 문구가 채팅 제한을 약속하는데 그 경로 배선이 0건이라는 [[DW-813]]이 그중 가장 눈에 띈다.
