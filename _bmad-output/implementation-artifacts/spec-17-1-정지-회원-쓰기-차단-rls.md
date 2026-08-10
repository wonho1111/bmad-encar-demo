---
title: '17.1 정지 회원 쓰기 차단 (RLS + 정의자 함수 경로)'
type: 'feature'
created: '2026-08-10'
status: 'draft'
review_loop_iteration: 0
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-17-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff'
---

<intent-contract>

## Intent

**Problem:** 관리자가 회원을 "정지"시켜도(`profiles.status='suspended'`, FR22) **아무 일도 일어나지 않는다.**
그 회원은 계속 로그인해 매물을 등록·수정·삭제하고 사진을 올린다. `grep -rln "suspended"` 결과
매치는 컬럼 정의·관리자 UI·상수뿐이고 **정지를 근거로 무언가를 거부하는 코드는 0건**이다([[DW-669]] 실측).

**⚠️ 먼저 알아야 할 사실 3가지 — 이걸 모르고 시작하면 반쪽만 고친다.**

1. **이미 한 번 구현했다가 되돌린 코드가 있고, 그 코드엔 실측된 구멍 2개가 있다.**
   `bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`에 15-3 세션이 짜고
   (vitest 336/336 · playwright 73/73 통과) 검증했다가 Epic 15의 UI-only 제약과 충돌해 되돌린
   `0030_listings_suspend_gate.sql` 전문이 보존돼 있다([[DW-717]]). **출발점으로는 쓸 수 있지만
   그대로 재사용하면 안 된다** — 그 코드리뷰가 로컬 DB 실측으로 찾은 구멍 2개가 미반영 상태다:
   - **정지된 관리자**는 `listings_delete_admin`(0005)으로 여전히 **남의 매물을 삭제**할 수 있다(DELETE 성공 확인).
   - `listing_images`·`storage.objects` 쓰기 정책이 없어 **정지된 판매자가 사진을 계속 추가·삭제**할 수 있다(INSERT/DELETE 성공 확인).

2. **RLS만 고치면 안 닫히는 경로가 있다 — 정의자 함수(SECURITY DEFINER).**
   [[DW-721]]이 실측했다: `is_admin()`은 `role='admin'`만 보고 `status`를 안 본다. 그래서
   **정지된 관리자가 `admin_restore_sold_listing` RPC(0030)로 이미 완료된 거래를 되돌릴 수 있다**
   (2026-08-07 로컬 실측: `rows=1`, `status`가 실제로 `on_sale`로 바뀜). 이 RPC는 SECURITY DEFINER라
   **RLS를 통째로 우회**한다. DW-721은 이 스토리를 이름으로 지목하며 *"17-1이 RLS 범위로만 설계되면
   이 경로는 닫히지 않는다"* 고 경고한다.

3. **정지 판정식은 `profiles` RLS를 탄다.** 정책 안의
   `exists (select 1 from public.profiles where id = auth.uid() and status = 'active')`는
   호출자 권한으로 평가되지만, `profiles_select_self`(`auth.uid() = id`, `to authenticated`, 0001)가
   본인 행을 열어 주므로 **동작한다**. 새 SECURITY DEFINER 헬퍼를 만들 이유가 없다.
   ⚠️ 단 `authenticated`에 `profiles` SELECT **GRANT**가 필요한데, **로컬 `supabase db reset` 직후엔
   그 GRANT가 없다**([[DW-722]] 실측 — 원격은 플랫폼이, CI는 프렐류드가 준다). 로컬에서 검증이
   이상하게 실패하면 먼저 이걸 의심한다.

**Value:** 화면에 있는 "정지" 버튼이 지금은 **아무 강제력이 없는 표시**다. 관리자가 악성 판매자를
정지시켰다고 믿는 동안 그 판매자는 계속 매물을 올린다. 그리고 이 결함은 화면 문제와 달리
**앱·웹 어느 클라이언트로 접속해도 똑같이 열려 있다** — 그래서 해결 자리도 화면이 아니라
데이터 계층이다(CLAUDE.md B9: *"앱 코드로 막으면 화면 하나 더 만들 때 까먹지만, 데이터 계층에
박으면 못 어긴다"*).

**함께 닫는 것(같은 마이그레이션 묶음, sprint-status.yaml Epic 17 주석의 사용자 지정):**
- [[DW-682]] — `0028`의 buyer/seller 통과 분기. 유일한 공급자였던 Flutter 가입 화면이 `16-0`에서
  role 전송을 멈춰(웹은 14.2에서 이미 멈춤) **도달 경로가 0인데도** 제거되지 않았다.
- [[DW-782]] — `sold` 매물 쓰기 차단이 `listing_images` **행**에만 있고 실제 **파일**(`storage.objects`)엔
  없다. 이 스토리가 건드릴 정책 파일이 정확히 그 파일이다.
- [[DW-674]] — `listings` 소유권 RLS 자체를 지키는 반복 실행 검사가 저장소에 0건이다. 그 항목의
  trigger가 *"`listings` RLS를 다음에 건드리는 마이그레이션 스토리"* = 이 스토리다.

## Boundaries & Constraints

**Always:**

- **불변식을 한 문장으로 먼저 못박는다:**
  *"`profiles.status = 'suspended'`인 계정은 매물·사진·파일·관리자 RPC 어느 경로로도 쓰기를
  성공시킬 수 없다. 반대로 그 계정의 **읽기**는 아무것도 줄어들지 않는다."*
  아래 작업은 전부 이 한 문장을 지키기 위한 것이다.

- **쓰기 경로를 전수 조사하고 그 목록을 Design Notes에 남긴다.** "정책 3개 고쳤다"로 끝내지 않는다.
  최소한 아래를 직접 확인한다(이 목록은 오케스트레이터가 grep으로 뽑은 것이니 **다시 재어 보고
  틀렸으면 정정한다**):
  `listings` INSERT/UPDATE/DELETE(0002·0015) · `listing_images` INSERT/UPDATE/DELETE(0031) ·
  `storage.objects`의 `listing_images_objects_owner_insert/update/delete`(0013) ·
  `listings_delete_admin`(0005) · `profiles_update_admin`·`profiles_delete_admin`(0005) ·
  `chat_rooms_delete_admin`·`chat_messages_delete_admin`(0005) ·
  `admin_restore_sold_listing` RPC(0030) · `0014`의 관리자 쓰기 분기.
  각 항목에 **"막는다 / 안 막는다 + 그 이유"** 를 적는다. 안 막기로 한 것이 있으면 그 근거가 남아야
  다음 사람이 다시 조사하지 않는다.

- **`is_admin()`을 전역으로 좁히지 않는다 — 쓰기 자리에만 정지 조건을 더한다.**
  `is_admin()`에 `and status='active'`를 넣으면 **읽기 정책까지 함께 좁아진다**
  (`chat_rooms_select_admin`·`chat_messages_select_admin`·`0012`의 `listing_images` 관리자 SELECT 등).
  그건 이 스토리의 불변식 후반부("읽기는 줄지 않는다")와 정면으로 어긋난다.
  ⚠️ **다른 결론이 낫다고 판단되면 바꿔도 된다 — 단 근거를 실측으로 만든다**: `is_admin()`을 좁혔을
  때 어느 SELECT 정책이 실제로 닫히는지 로컬 DB에서 재어 보고 그 결과를 Design Notes에 적는다.
  추론만으로 뒤집지 않는다(CLAUDE.md B4 *"재보기 전엔 선언하지 않는다"*).

- **채팅은 이번 범위에서 판단만 하고, 판단 결과를 적는다.** 정지 회원이 **메시지를 보낼 수 있는지**는
  이 스토리가 정하지 않으면 아무도 정하지 않는다. 막든 안 막든 **결론과 이유를 Design Notes와
  `docs/conventions.md` §8에 한 줄로 남긴다.** (조용히 범위 밖으로 두지 않는다 — 그게 DW-669가
  처음 생긴 방식이다.)

- **`docs/conventions.md` §8(접근 게이트 계약)에 정지의 의미를 정본으로 등재한다.**
  DW-669가 *"정하면 §8에 한 줄로 적어야 다음 사람이 다시 묻지 않는다"* 고 요구했다. 문장은
  "정지는 열람이 아니라 쓰기 행동만 막는다" 축으로 §8의 기존 분류 기준과 같은 자리에 붙인다.

- **검사는 실DB(`api/tests/integration`)에 만든다 — CI `api-db` 잡이 실제로 돌리는 자리다.**
  기존 관례를 그대로 쓴다: `set local role authenticated` + `set local request.jwt.claim.sub`로
  세션을 흉내 내는 방식(`test_chat_unread_real_db.py`·`test_role_check_relax_real_db.py`가 이미 쓴다).
  새 인프라를 만들지 않는다.

- **"존재 확인"으로 닫지 않는다**(CLAUDE.md B4). 정책이 **있는 것**과 실제로 **거르는 것**은 다르다.
  정지 계정을 실제로 만들어 그 세션으로 INSERT/UPDATE/DELETE를 **쏴 보고 거부되는 것**을 확인한다.
  [[DW-782]]도 마찬가지 — sold 매물 사진 경로에 실제 쓰기를 시도해 거부돼야 닫는다.

- **red→green을 표기를 바꿔가며 두 가지 방식으로 증명한다**(CLAUDE.md B4 · 메모리
  `guard-proof-must-vary-shape`). 자기가 쓴 표기로만 깨면 그 검사가 실제로 무엇을 보는지 증명되지
  않는다. 최소 한 축은 **정책 자체를 되돌려**(정지 조건을 뺀 버전으로 교체) red를 확인한다.

- **기대값을 피검사 대상에서 다시 계산하지 않는다**(메모리 `self-consistent-assertions-never-fail`).
  `'suspended'`·`'active'`·SQLSTATE `42501` 같은 값은 **글자 그대로 박는다.** 코드에서 상수를
  가져다 쓰면 상수가 바뀔 때 요청과 기대값이 같이 바뀌어 영원히 통과한다(2026-08-10 실측 사례).

- **검사 옆에 "이 검사가 안 보는 것"을 적는다**(Epic 13 회고 약속, 코드에서 이행이 확인된 항목).
  추측이 아니라 실측해서 적는다.

- 끝나면 **[[DW-669]]·[[DW-717]]·[[DW-721]]·[[DW-674]]·[[DW-682]]·[[DW-782]]를 `resolution:`과 함께
  done으로 닫는다**(CLAUDE.md B8 *"일을 끝내면 대장을 닫는다"*). 범위에서 뺀 것이 있으면 닫지 말고
  **왜 뺐는지와 다음 자리를 `trigger:`에 적어** 열어 둔다.

**Block If (멈추고 escalate):**

- 위 "쓰기 경로 전수 조사"에서 **`is_admin()` 전역 수정 없이는 닫을 수 없는 경로**가 나오고, 그
  전역 수정이 읽기 정책을 실제로 좁힌다는 것이 실측으로 확인되면 — 두 손해 중 무엇을 고를지는
  사용자 판단이다. 멈추고 묻는다.
- 정지 조건이 **웹·앱의 정상 동작을 깨는 것**이 확인되면(예: `authenticated` GRANT 문제가
  DW-722의 로컬 한정이 아니라 원격에도 해당한다는 증거가 나오면) 멈추고 묻는다.
- 채팅 쓰기 차단이 실시간 구독(0023 broadcast)이나 안읽음 계산(0024~0026)을 깨는 것이 확인되면
  멈추고 묻는다 — 그 축은 Epic 16이 방금 고친 자리라 되돌리면 안 된다.

**Never:**

- **`listings_select_*`·`listing_images` SELECT·`profiles` SELECT 어느 것도 좁히지 않는다.**
  정지된 판매자의 기존 매물은 다른 구매자에게 **계속 보여야 한다**. 정지는 열람을 막지 않는다.
- **되돌리는 마이그레이션을 쓰지 않는다.** 전진만 한다(CLAUDE.md B3 · conventions §9.1). 기존
  마이그레이션 파일을 **수정하지 않는다** — 새 번호(`0032` 이후)로 추가한다.
  `drop policy → create policy`(같은 파일 안 즉시 재생성)는 §9.1이 허용한 전진 패턴이다.
- **화면(웹·앱)에 정지 검사를 심어 DB 차단을 대체하지 않는다.** 안내 문구를 다듬는 것은 되지만,
  그것이 강제력의 자리가 되면 안 된다(CLAUDE.md B9).
- 저장된 15-3 패치를 **검토 없이 그대로 적용하지 않는다**(구멍 2개가 미반영 — 위 Intent 1번).
- 관리자 감사 로그([[DW-718]])를 만들지 않는다 — 별건이고 트리거가 다르다.
- **운영(`main`) 배포·원격 DB 적용을 하지 않는다.** 마이그레이션 파일을 만들고 **로컬에서** 검증까지만
  한다. 원격 적용은 사용자 승인 사안이다(CLAUDE.md B3).
- 새 화면·새 기능을 만들지 않는다(이 에픽은 backend-only).

</intent-contract>
