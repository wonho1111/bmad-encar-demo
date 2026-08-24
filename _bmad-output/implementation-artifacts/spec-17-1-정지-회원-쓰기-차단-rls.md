---
title: '17.1 정지 회원 쓰기 차단 (RLS + 정의자 함수 경로)'
type: 'feature'
created: '2026-08-10'
status: 'done'
# bad_spec 루프백 #1에서 코드를 83f8740 상태로 되돌렸으므로 baseline은 그대로 둔다.
# (baseline을 최신 커밋으로 옮기면 다음 리뷰 diff가 "직전 패치 대비 델타"만 보여 재파생된 구현
#  전체가 리뷰에서 안 보인다. 3패스가 잡은 결함도 전부 이 스토리가 새로 쓴 코드 안에 있었다.)
baseline_revision: '83f8740dd926b3c23297affe381006d06acb389c'
reverted_implementation_revision: '3de63c565419ad7f5f78367ba5a2515fa3997794'
final_revision: '14d16d8e05b04a7b8100e488c1a9da32c7a4fcb6'  # 3패스 커밋(이 줄 자체는 다음 커밋에 기록)
# 3패스 patch findings: high 0 · medium 4 · low 6 → 3×4 + 1×6 = 18 (≥5) → true
followup_review_recommended: true
review_loop_iteration: 0
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-17-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff'
warnings: ['oversized']
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

## Code Map

- `supabase/migrations/0001_profiles.sql` -- `is_admin()`(SECURITY DEFINER, `role='admin'`만 확인, `status` 안 봄) · `profiles_select_self` 정의. 정지 판정식이 여길 통과한다.
- `supabase/migrations/0002_listings.sql` -- `listings_insert_own`/`listings_delete_own` 원본(정지 조건 없음). `0032`가 재정의 대상.
- `supabase/migrations/0015_listings_update_not_sold.sql` -- `listings_update_own` 현재판(sold 전환은 `with check`에서 허용, `using`만 sold 재수정 차단). 정지 조건 추가 시 이 비대칭을 보존해야 함.
- `supabase/migrations/0005_admin_policies.sql` -- `profiles_update_admin`·`profiles_delete_admin`·`listings_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`. 전부 `is_admin()`만 체크 — 정지된 관리자를 막지 않는다.
- `supabase/migrations/0003_chat.sql` -- `chat_messages_insert_participant`(sender_id 본인 + 방 당사자만 체크, 정지 무관). 채팅 차단 여부 결정이 걸리는 자리.
- `supabase/migrations/0013_listing_images_path_integrity.sql` -- `storage.objects`의 `listing_images_objects_owner_insert/update/delete`(경로 소유권만 체크, sold·정지 둘 다 안 봄). DW-782와 이 스토리가 같이 닫는 자리.
- `supabase/migrations/0014_listing_images_public_bucket.sql:77-84` -- `listing_images_objects_admin_delete`(`is_admin()`만 체크).
- `supabase/migrations/0030_listings_restore_sold_rpc.sql` -- `admin_restore_sold_listing(uuid)`, SECURITY DEFINER, `WHERE ... and public.is_admin()`. DW-721이 지목한 RPC.
- `supabase/migrations/0031_listing_images_sold_write_block.sql` -- `listing_images_insert_own/update_own/delete_own`(현재 sold 조건만 있음, `exists (select from listings ...)` 패턴). 정지 조건 추가 대상, 같은 패턴 재사용.
- `supabase/migrations/0028_handle_new_user_default_role.sql:33-35` -- `handle_new_user()`의 buyer/seller 통과 분기(DW-682, 도달 경로 0 확인됨).
- `scripts/check_migrations.py` -- 번호 밀집·self-containment 정적/동적 게이트. 새 마이그레이션이 통과해야 함.
- `scripts/migration-check-prelude.sql:64` -- CI가 재현하는 플랫폼 기본 GRANT(`grant all on tables ... to anon, authenticated, service_role`). 로컬 DW-722 재현 시 이 한 줄만 따로 재적용.
- `api/tests/integration/test_chat_unread_real_db.py`, `api/tests/integration/test_role_check_relax_real_db.py`, `api/tests/integration/conftest.py` -- `set local role authenticated` + `set local request.jwt.claim.sub` 세션 흉내 패턴, `_create_user`/`_insert_listing` 공유 픽스처, `42501` + `"row-level security policy"` 이중 단언 관례.
- `docs/conventions.md` §8 -- 접근 게이트 분류 기준(열람 vs 행동). 정지 = 행동 차단 한 줄이 여기 등재된다.
- `docs/conventions.md` §9.1 -- 마이그레이션 전진 전용 규칙(`drop policy → create policy` 허용 패턴, 근거 주석 의무).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-669/717/721/674/682/782 항목. 완료 시 `resolution:`과 함께 done.
- `_bmad-output/implementation-artifacts/bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff` -- 되돌려진 `0030_listings_suspend_gate.sql` 원본(출발점, 구멍 2개 있음 — 그대로 재사용 금지).

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0032_suspended_write_block.sql` -- NEW. 다음을 한 파일에 담는다(같은 강제 묶음):
  1. `public.is_admin_active()` 함수 신설 — `is_admin()`과 동일하게 SECURITY DEFINER·`role='admin' and status='active'`를 확인. **이유**: `profiles_update_admin`/`profiles_delete_admin`은 `profiles` 테이블 자체를 보호하는 정책이라, 그 안에서 `profiles`를 직접 서브쿼리하면 0001·0005 주석이 이미 경고한 "자기참조 무한재귀"가 재현된다 — `is_admin()`이 SECURITY DEFINER로 분리된 것과 같은 이유로, 정지 조건을 더한 admin 판정도 같은 방식으로 분리해야 한다.
  2. `listings_insert_own`/`listings_update_own`(0015판 유지)/`listings_delete_own`(0002·0015) 재정의 — 기존 조건에 `and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')` 추가. `listings_update_own`은 **`using`에만** 추가하고 `with check`는 그대로 둔다 — `using`(OLD 행 선택)이 정지된 행위자에겐 애초에 행을 하나도 안 보여주므로 `with check`(NEW 행 검증)는 도달조차 하지 않는다(중복 조건 불필요); 이렇게 하면 0015가 `with check`에 의도적으로 남겨 둔 sold-전환 허용 비대칭도 그대로 보존된다.
  3. `listing_images_insert_own/update_own/delete_own`(0031판) 재정의 — 기존 `l.status <> 'sold'` join에 `and exists (select 1 from public.profiles where id = auth.uid() and status = 'active')` 추가.
  4. `storage.objects`의 `listing_images_objects_owner_insert/update/delete`(0013) 재정의 — 기존 owner-path 체크에 정지 조건을 더하고, `split_part(name,'/',2)::uuid`로 얻은 `listing_id`로 `public.listings`를 join해 sold 매물의 사진 쓰기를 막는다([[DW-782]] 닫음). **⚠️ verb마다 join 형태가 다르다 — 같은 조건을 세 verb에 복붙하면 매물 삭제 후 사진 정리가 죽는다(2026-08-11 실측, 아래 Spec Change Log 참조):**
     - **INSERT(`with check`)·UPDATE(`using`+`with check`)**: `exists (select 1 from public.listings l where l.id = <파싱된 uuid> and l.seller_id = auth.uid() and l.status <> 'sold')` — **살아 있는 자기 non-sold 매물**이 있어야 통과. 경로 2번째 세그먼트가 UUID 형식이 아니면 파싱 결과가 NULL이라 `exists`가 거짓 → 거부(경로 계약 위반은 계속 막는다). `l.seller_id = auth.uid()`는 0031의 `listing_images` 정책과 같은 소유권 축이다 — 이게 없으면 **남의 on_sale 매물 id**를 자기 uid prefix 아래 붙여 파일을 심을 수 있다.
     - **DELETE(`using`)**: 조건을 **부정형**으로 쓴다 — `not exists (select 1 from public.listings l where l.id = <파싱된 uuid> and l.status = 'sold')`. 즉 *"sold 매물의 사진만 못 지운다"*이고, **매물 행이 이미 없으면(=고아) 소유자가 지울 수 있다.** 이유: 웹·앱 모두 `docs/conventions.md` §10.1의 규정된 순서대로 **① `listings` 행 삭제 → ② 사진 오브젝트 정리**를 하므로, DELETE에 `exists(... 살아 있는 매물)`를 걸면 정상 판매자의 모든 매물 삭제가 사진을 **영구 고아**로 남기고 소유자는 그걸 다시는 못 지운다(`web/.../ListingActions.tsx`·`app/.../listings_repository.dart`가 그 순서, `upload.ts`의 `deleteListingImageObject`는 RLS 0행을 "이미 없음"으로 읽어 **성공으로 보고**하므로 완전히 조용히 실패한다). 같은 이유로 UUID 형식이 아닌 레거시 경로도 `not exists`가 참이 되어 소유자 정리가 가능하다.
     - 세 verb의 차이와 그 근거를 마이그레이션 각주에 남긴다(§9.1의 "왜" 의무).
  5. `listing_images_objects_admin_delete`(0014) · `listings_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`profiles_update_admin`·`profiles_delete_admin`(0005) 재정의 — `public.is_admin()` → `public.is_admin_active()`로 교체.
  6. `admin_restore_sold_listing`(0030) 재정의 — `WHERE`절의 `public.is_admin()` → `public.is_admin_active()`로 교체.
  7. `chat_messages_insert_participant`(0003) — 정지 발신자 차단 여부를 실제로 결정한다. INSERT 차단은 0023(브로드캐스트, AFTER INSERT 트리거)·0024~0026(안읽음, INSERT 이후 SELECT 계산)이 전부 "성공한 INSERT 이후"에만 동작하므로 이론상 안전 — 이걸 실DB로 확인한 뒤 조건을 더하거나(막기로 결정), 근거와 함께 보류한다(Block-If 조건 미충족 시 막는 쪽이 기본값).
  8. `is_admin()` 자체는 수정하지 않는다(전역 좁히기 금지 — Always 3항).
  각주에 §9.1이 요구하는 "왜/`using` vs `with check`" 근거를 남긴다.
- `supabase/migrations/0033_remove_legacy_role_passthrough.sql` -- NEW. `handle_new_user()`(0028)에서 buyer/seller 통과 분기를 제거한다([[DW-682]] — 도달 경로 0, 항상 `'user'`로 귀결). 트리거 함수 전체를 `create or replace`.
- **쓰기 경로 전수조사 산출물을 Design Notes에 표로 남긴다** (Always 2항이 요구한 것 — "정책 N개 고쳤다"로 끝내지 않는다). 목록은 grep이 아니라 **실측으로 뽑는다**: `select schemaname, tablename, policyname, cmd from pg_policies where cmd <> 'SELECT' and 'authenticated' = any(roles)` + `select p.proname from pg_proc p where p.prosecdef` (SECURITY DEFINER 전량, `public` 스키마). 뽑힌 **모든** 항목에 "막는다 / 안 막는다 + 이유" 한 줄씩. 최소한 아래 4건은 반드시 판정이 있어야 한다(리뷰가 실측으로 찾은, 이전 판에 판정이 없던 경로들):
  - `wishlists_insert_own`·`wishlists_delete_own`(0018) — 정지 회원이 찜을 계속 추가·삭제할 수 있다.
  - `chat_room_reads_insert_participant`·`chat_room_reads_update_own`(0024) — 정지 회원이 상대방 안읽음 배지를 움직이는 행을 쓴다.
  - `increment_listing_view`(0020) — **SECURITY DEFINER + `anon,authenticated`에 execute GRANT + `public.listings`를 UPDATE.** DW-721이 지목한 "정의자 함수가 RLS를 우회해 listings에 쓴다"와 같은 계열인데 Intent의 grep 목록에 없었다.
  - `chat_rooms_insert_participant`(0003) — 방 생성. 발신만 막고 방 생성을 열어 두면 "영구 빈 방"이 판매자 목록에 쌓인다는 귀결까지 판정에 적는다.
  판정이 "안 막는다"여도 된다 — 불변식 문장(매물·사진·파일·관리자 RPC)이 그 범주를 포함하지 않는다는 근거를 적으면 된다. **근거 없는 누락만 금지**다.
- `docs/conventions.md` §8 -- 정지의 의미를 정본으로 등재하되 **막는 범위와 막지 않는 범위를 함께** 적는다(막는 쪽만 적으면 "예외 없이"로 읽혀, 다음 사람이 새 쓰기 경로에 조건을 안 넣는다 — DW-669가 처음 생긴 방식 그대로다). 최소 형태: "정지(`profiles.status='suspended'`)는 열람이 아니라 쓰기 행동만 막는다 — 매물·사진·파일·관리자 쓰기·채팅 발신, RLS + SECURITY DEFINER 함수 양쪽에서(17-1). **막지 않는 쓰기**: <위 전수조사에서 '안 막는다'로 판정된 항목들> — 의도적 현재 범위."
- `supabase/seed.sql:170`·`:436` -- 0033이 지운 계약을 아직 사실로 적고 있다("트리거가 이 값을 그대로 반영해 profiles를 seller로 생성"). `_create_user` 사본 4개만 맞추고 이 **다섯 번째 생산자**를 빠뜨리면 정본 시드 파일이 같은 커밋이 삭제한 계약을 계속 문서화한다. 주석 정정(또는 메타를 `'{}'::jsonb`로) — 어느 쪽이든 시드의 최종 role 기대값은 바뀌지 않아야 한다.
- `api/tests/integration/test_suspended_write_block_real_db.py` -- NEW. `conftest.py`의 `_DSN`/`_create_user`/`_insert_listing`/`pytestmark` 재사용. 아래 시나리오 전부 + DW-674의 일반 소유권 회귀(정지와 무관하게 항상 성립해야 하는 축)를 같은 파일에 담는다(관련 관심사, 같은 세션 흉내 패턴 재사용).
  **⚠️ 거부만 단언하는 파일을 만들지 않는다.** 이전 판은 `listing_images`·`storage.objects` 테스트 7건이 전부 "거부"만 단언해서, 정지 조건을 **모두를 막는** 형태로 잘못 써도 21/21 green이었다. 각 표면마다 **긍정 대조군**(활성 판매자가 실제로 성공하는 것)을 짝으로 둔다 — 그게 없으면 "정확히 정지만 막는다"와 "전부 막는다"를 구별할 수 없다(CLAUDE.md B4 *"만들었다가 아니라 잡는다가 완료다"*).
- `api/tests/integration/conftest.py` -- `_create_user`가 트리거 이후 `update public.profiles set role = ...`로 role을 앉힐 때 **결과를 단언한다**(`assert cur.rowcount == 1`). 지금은 안 앉혀져도 헬퍼가 조용히 성공을 돌려주므로, 이후 테스트가 "판매자"라고 믿는 계정이 실제로는 아닐 수 있다(DW-683이 기록한 실패 계열). 같은 헬퍼 사본(`test_chat_idempotency_real_db.py` 등)도 동일하게.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-669]]·[[DW-717]]·[[DW-721]]·[[DW-674]]·[[DW-682]]·[[DW-782]]를 `resolution:`과 함께 done 처리(범위에서 뺀 것이 있으면 `trigger:` 갱신).

**Acceptance Criteria:**
- Given `profiles.status='suspended'`인 판매자 세션, when 자신을 `seller_id`로 하는 `listings` INSERT를 시도, then SQLSTATE `42501`로 거부되고 0행 삽입.
- Given 정지된 판매자와 그의 기존 매물, when 그 매물을 UPDATE 또는 DELETE, then **0행**(rowcount 0)으로 거부되고 값·존재 불변(Postgres RLS의 `using`절 거부는 예외가 아니라 대상 행을 애초에 안 보여주는 0행이다 — INSERT의 `with check` 거부만 `42501` 예외를 던진다; 실측으로 확정, 아래 Spec Change Log 참조).
- Given 정지된 판매자와 그의 기존 매물, when 그 매물의 `listing_images` 행을 INSERT, then `42501`로 거부 / UPDATE·DELETE, then **0행**으로 거부.
- Given 정지된 판매자, when `listing-images` 버킷의 `{자신의 uid}/{listing_id}/파일명` 경로로 `storage.objects` INSERT, then `42501`로 거부 / UPDATE·DELETE, then **0행**으로 거부.
- Given 활성 판매자와 `status='sold'`인 자신의 매물, when 그 매물의 `storage.objects` 사진 경로에 INSERT, then `42501`로 거부 / UPDATE·DELETE, then **0행**으로 거부([[DW-782]] — 정지 여부와 무관하게 성립).
- **(회귀 고정 — 2026-08-11 실측으로 깨져 있던 축)** Given 활성 판매자와 사진이 달린 자신의 `on_sale` 매물, when `docs/conventions.md` §10.1이 규정한 실제 클라이언트 순서대로 **① `listings` 행을 DELETE(1행) → ② 같은 세션에서 그 매물의 `storage.objects` 사진을 DELETE**, then 사진 DELETE가 **1행**으로 성공하고 버킷에 고아가 **0건** 남는다.
- **(긍정 대조군 — 없으면 "전부 막힘"과 구별 불가)** Given 활성 판매자와 자신의 `on_sale` 매물, when `listing_images` 행을 INSERT·UPDATE·DELETE하고 `storage.objects` 사진을 INSERT·UPDATE·DELETE, then 각각 성공(INSERT는 예외 없음, UPDATE·DELETE는 **1행**).
- Given 활성·비관리자 세션, when **타인의 uid를 `seller_id`로** 하는 `listings` INSERT를 시도(소유권 위조), then `42501`로 거부([[DW-674]]의 trigger가 명시적으로 요구한 축 — 이전 판은 UPDATE/DELETE만 덮고 이 INSERT 단언 없이 DW-674를 닫았다).
- Given 활성 판매자 A와 **다른 판매자 B의 `on_sale` 매물**, when A가 `{A의 uid}/{B의 매물 id}/파일명` 경로로 `storage.objects` INSERT, then `42501`로 거부(경로 1번째 세그먼트만 보면 통과해 버리는 축 — join에 `l.seller_id = auth.uid()`가 있어야 막힌다).
- Given 활성 판매자와 2번째 경로 세그먼트가 UUID 형식이 **아닌** 레거시 오브젝트, when 소유자가 그 오브젝트를 DELETE, then **1행**으로 성공(정리 가능) / when 같은 형식으로 INSERT, then `42501`로 거부(경로 계약 위반은 계속 차단).
- Given `role='admin' and status='suspended'`인 세션, when 남의 `listings` 행을 DELETE(`listings_delete_admin` 경유), then **0행**으로 거부.
- Given `role='admin' and status='suspended'`인 세션, when `status='sold'`인 매물에 `admin_restore_sold_listing(id)`를 호출, then 0행 반환·`status` 불변.
- Given `role='admin' and status='suspended'`인 세션, when 자기 자신의 `profiles.status`를 `'active'`로 UPDATE(자가 정지 해제 시도), then **0행**으로 거부.
- **(재정의한 관리자 쓰기 정책 6개를 하나도 빠뜨리지 않는다 — 이전 판은 6개 중 2개만 검증했다)** Given `role='admin' and status='suspended'`인 세션, when `profiles` DELETE(`profiles_delete_admin`)·`chat_rooms` DELETE·`chat_messages` DELETE·`storage.objects` DELETE(`listing_images_objects_admin_delete`)를 각각 시도, then 전부 **0행**으로 거부.
- Given `role='admin' and status='active'`인 세션, when 위와 동일한 관리자 작업들(타인 매물 삭제 · 복원 RPC · 타인 `profiles` UPDATE **및 DELETE** · `chat_rooms` DELETE · `chat_messages` DELETE · 관리자 경로 `storage.objects` DELETE)을 수행, then 기존과 동일하게 성공(회귀 없음 — `is_admin()`→`is_admin_active()` 교체가 활성 관리자에게서 아무 권한도 뺏지 않았음을 6개 전부에서 고정).
- Given 정지된 관리자 세션, when `listings_select_admin`·`profiles_select_admin`(둘 다 `is_admin()` 그대로, `is_admin_active()`로 교체되지 않음) 경유로 남의 매물·profiles를 SELECT, then 성공(관리자 읽기는 정지와 무관 — `is_admin_active()`를 쓰기 소비처에만 넣은 설계 근거 자체의 회귀 확인).
- Given 정지된 회원, when 자신의 `listings`/`profiles`를 SELECT하거나 다른 `on_sale` 매물을 탐색, then 전부 정지 이전과 동일하게 성공(열람 무변화).
- Given 활성·비관리자 세션, when 자신이 소유하지 않은 `listings` 행을 UPDATE/DELETE, then **0행**으로 거부·값 불변([[DW-674]] — 정지와 무관한 소유권 RLS 회귀 고정).
- Given 신규 가입자가 `auth.users` metadata에 `role='seller'`를 보내는 경우(레거시 경로), when `handle_new_user()`가 실행, then 여전히 `profiles.role='user'`로 배정(0033이 통과 분기를 지워도 결과가 바뀌지 않음을 확인 — 이미 도달 불가능한 분기였다는 근거 재확인).

## Spec Change Log

<!-- Append-only. 첫 bad_spec 루프백 전까지 비움. -->

### 2026-08-11 — AC 문구 정정 (리뷰 patch, bad_spec 루프백 아님)
- **트리거**: 코드리뷰(adversarial + intent-alignment)가 지적 — Acceptance Criteria가 UPDATE/DELETE
  거부도 전부 "SQLSTATE 42501로 거부"라고 적었으나, 실측(테스트 파일 헤더에 이미 기록됨) 결과
  Postgres RLS의 `using`절 거부는 예외가 아니라 대상 행을 애초에 안 보여주는 **0행**이다 — INSERT의
  `with check` 거부만 진짜로 `42501` 예외를 던진다.
- **수정한 것**: 위 Acceptance Criteria의 UPDATE/DELETE 항목 문구를 "42501로 거부"에서 "0행으로
  거부"로 정정(INSERT 항목은 그대로 42501 유지). 코드·마이그레이션·테스트는 이미 처음부터 실측된
  대로 옳게 작성돼 있었다 — **수정 대상은 이 문서뿐**이었다(코드 되돌림·재구현 없음).
- **피하는 known-bad 상태**: 이 문구를 안 고치면, 다음에 이 스펙만 읽고 웹/앱 에러 처리를 만드는
  사람이 UPDATE/DELETE 실패에서도 예외(42501)를 기대하고 짜서, 실제로는 조용한 0행 응답을 못
  잡는 코드를 만들 수 있었다.
- **KEEP**: 테스트 파일(`test_suspended_write_block_real_db.py`) 헤더의 SQLSTATE-vs-0행 구분 설명은
  정확했다 — 그대로 유지, 재파생 시에도 이 구분을 다시 흐리지 않는다.

### 2026-08-11 — bad_spec 루프백 #1 (후속 리뷰 패스)

- **트리거(최상위)**: `storage.objects` 소유자 DELETE 정책이 *"살아 있는 non-sold 매물이 있어야 지울 수 있다"*가 되어,
  웹·앱이 §10.1대로 **매물 행을 먼저 지운 뒤** 사진을 정리하면 그 DELETE가 0행이 되고 **사진이 영구 고아로 남는다.**
  4개 리뷰 렌즈 중 3개가 독립적으로 지적했고, 이 세션이 로컬 실 스택에서 직접 재현했다(대조군 `DELETE 1`/남은 0건 ↔
  실제 순서 `DELETE 0`/고아 1건). 클라이언트가 0행을 성공으로 읽어 **완전히 조용한 실패**다.
- **함께 잡힌 뿌리 (전부 스펙 쪽)**:
  (1) `listing_images`·`storage.objects` 테스트 7건이 전부 "거부"만 단언 — 정지 조건을 *모두를 막는* 형태로
      잘못 써도 21/21 green이었다(AC에 긍정 경로가 없었다).
  (2) 재정의한 관리자 쓰기 정책 6개 중 4개(`profiles_delete_admin`·`chat_rooms_delete_admin`·
      `chat_messages_delete_admin`·`listing_images_objects_admin_delete`)가 양방향 미검증 — AC에 없었다.
  (3) Intent Always 2항이 요구한 **쓰기 경로 전수조사 산출물**이 Tasks에 과업으로 없었고, 그래서 Design Notes에
      목록이 없다. 실측 결과 판정이 아예 없는 경로 4종 확인(`wishlists_*`·`chat_room_reads_*`·
      `increment_listing_view`(SECURITY DEFINER가 `listings`를 UPDATE)·`chat_rooms_insert_participant`).
  (4) [[DW-674]]의 trigger가 명시한 "타인 명의 INSERT 42501" 단언이 AC에 없어, 그게 없는 채로 DW-674가 닫혔다.
  (5) storage 소유자 join에 소유권(`l.seller_id = auth.uid()`) 축이 없어 남의 on_sale 매물 id로 파일을 심을 수 있다.
  (6) `supabase/seed.sql:170`이 0033이 지운 계약을 여전히 사실로 적는다(`_create_user` 사본 4개만 맞췄다).
- **수정한 것 (전부 `<intent-contract>` 밖)**: Tasks 4항을 verb별로 분리해 다시 씀(INSERT/UPDATE는 `exists(살아있는
  자기 non-sold 매물)`, DELETE는 `not exists(sold 매물)` 부정형) · 전수조사 산출물 과업 신설(실측 쿼리 지정) ·
  conventions §8 문구를 "막는 범위 + **막지 않는 범위**" 형태로 요구 · seed.sql 과업 추가 · conftest rowcount 단언 과업 추가 ·
  AC 8개 추가(§10.1 순서 회귀 · 긍정 대조군 · 관리자 6정책 양방향 · seller_id 위조 INSERT · 타인 매물 id 경로 · 레거시 경로) ·
  Verification의 red 증명을 "고른 3개"에서 "목록으로 적고 최소 6객체"로 강화.
- **피하는 known-bad 상태**: 세 verb에 같은 join을 복붙한 `0032`. 그 상태에서는 **정상 판매자의 모든 매물 삭제가
  사진을 영구 고아로 만들고**(소유자는 다시 못 지움, 관리자만 가능), 저장소가 단조 증가하며, §6.1의
  "매물 삭제는 사진 파일도 실제로 지운다" 계약과 §10.1 각주의 "회수 가능한 고아" 전제가 둘 다 거짓이 된다.
  또한 거부-only 테스트 파일은 이 결함을 **21/21 green으로 통과시켰다** — 재파생본이 긍정 대조군을 다시 빼면 안 된다.
- **KEEP (되돌린 구현에서 옳았던 것 — 재파생 시 살린다. 원본은 커밋 `3de63c5`에 그대로 있다)**:
  - `is_admin_active()`를 **새 SECURITY DEFINER 함수로 분리**한 설계와 그 근거(profiles 자기참조 재귀 회피),
    그리고 `is_admin()` 자체는 손대지 않아 **관리자 읽기 정책이 정지와 무관하게 열려 있음**을 실측으로 고정한
    테스트(`test_suspended_admin_can_still_read_via_admin_select_policies`) — 불변식 후반부의 유일한 증거다.
  - 채팅 발신 차단 결정과 그 안전성 근거(0023 브로드캐스트·0024~0026 안읽음이 전부 "INSERT 성공 이후"라
    영향 없음)를 **실DB로 확인한** 테스트(`test_active_participant_chat_still_broadcasts_and_updates_unread`).
  - `listings_update_own`의 `using`에만 정지 조건을 더해 0015의 sold-전환 비대칭을 보존한 판단.
  - `split_part(name,'/',2)` 캐스팅 전 **UUID 정규식 가드**(형식 오류가 22P02가 아니라 정책 거부로 떨어지게) —
    부정형 DELETE로 바꿔도 이 가드는 유지한다.
  - 테스트의 **리터럴 고정** 관례(`42501`·`'suspended'`·`'active'`·기대 가격을 피검사 대상에서 재계산하지 않음)와
    파일 헤더의 **SQLSTATE 42501 vs 0행 구분** 설명(위 2026-08-11 AC 정정 항목의 KEEP과 동일).
  - `scripts/migration-check-prelude.sql`의 **storage 스키마 USAGE + `storage.objects` GRANT + `metadata` 컬럼 스텁**
    (없으면 CI가 RLS가 아니라 권한 오류로 죽는다 — 1차 리뷰가 CI 재현으로 확인한 high 결함의 수정).
  - `0033`(DW-682 통과 분기 제거)과 `_create_user` 사본들의 계약 갱신 — 이번엔 `seed.sql`까지 포함해 마무리한다.

## Review Triage Log

<!-- Append-only. 첫 리뷰 패스 전까지 비움. -->

### 2026-08-11 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 1high, medium 4medium, low 1low)
- defer: 2 (low 2low)
- reject: 5 (low 5low)
- addressed_findings:
  - `[high]` `[patch]` `scripts/migration-check-prelude.sql`에 `authenticated`용 `storage` 스키마 USAGE + `storage.objects` 테이블 권한이 없어, CI(`api-db` 잡)가 새 storage.objects 테스트 4건 중 3건을 RLS가 아니라 "권한 없음"으로 죽이고 1건은 우연히(같은 SQLSTATE 42501) 통과한다 — CI 재현으로 확인됨. GRANT 추가.
  - `[medium]` `[patch]` `supabase/migrations/0032_suspended_write_block.sql`의 `storage.objects` 소유자 정책이 `split_part(name,'/',2)::uuid` 캐스팅 전에 형식 검증이 없어 잘못된 형식의 경로가 42501 대신 22P02 예외를 던짐 — 정규식 가드 추가.
  - `[medium]` `[patch]` `is_admin_active()`를 새로 만든 설계 근거(관리자 SELECT 정책이 정지된 관리자에게도 계속 열려 있어야 한다)를 검증하는 테스트가 없음 — 추가.
  - `[medium]` `[patch]` 스펙 Acceptance Criteria가 UPDATE/DELETE 거부도 "42501"이라 적었으나 실측은 0행(예외 없음)이었다(INSERT만 42501) — AC 문구 정정 + Spec Change Log 기록.
  - `[medium]` `[patch]` 새 테스트 파일의 로컬 실행법이 DW-722 GRANT 보정 레시피의 절반만 적어, 이미 마이그레이션이 적용된 로컬 DB에 그대로 적용하면 기존 GRANT 축소(0011·0012·0020·0021)가 풀려 무관한 테스트 9건이 깨진다 — 안내 보강.
  - `[low]` `[patch]` `test_restore_sold_listing_rpc_real_db.py`의 세 번째 `_create_user` 사본만 0033 계약 정정 문서화가 안 됨(role 미단언이라 무해하지만 드리프트) — 갱신.
  - `defer`: `chat_rooms_insert_participant`(0003)에 정지 조건 없음 — 채팅 "메시지 발신"만 이 스토리의 결정 대상이었고 "방 생성"은 불변식 문장(매물·사진·파일·관리자 RPC)에 없어 이 스토리 범위 밖으로 판단, DW로 이월.
  - `defer`: `is_admin_active()` 도입으로 "정지된 관리자는 자가 해제 불가"가 되어 전원 관리자가 정지되면 psql 직접 접근 외 복구 경로가 없음 — 데모 프로젝트라 저위험이나 런북 필요성으로 이월.
  - reject 5건(중복 낮은 확신 지적 3건, 재확인 결과 사실무근 1건, 이 스토리 소관 아닌 문서 1건) — 근거는 위 서브에이전트 원문 참조, 조용히 폐기.

### 2026-08-11 — Review pass (후속 리뷰, followup_review_recommended: true로 재진입)
- intent_gap: 0
- bad_spec: 8 (high 1, medium 4, low 3)
- patch: 0
- defer: 0
- reject: 8 (low 8)
- addressed_findings:
  - `[high]` `[bad_spec]` `storage.objects` 소유자 DELETE 정책에 `exists(살아 있는 non-sold 매물)` join이 걸려, §10.1이 규정한 실제 삭제 순서(매물 행 먼저 → 사진 정리)에서 사진 DELETE가 0행이 되고 **고아 파일이 영구 잔존**(로컬 실 스택 재현 확정). 클라이언트는 0행을 성공으로 읽어 조용히 실패. → Tasks 4항을 verb별로 재작성(DELETE는 `not exists(sold)` 부정형) + §10.1 순서 회귀 AC 신설.
  - `[medium]` `[bad_spec]` `listing_images`·`storage.objects` 테스트 7건이 거부만 단언 — "정지만 막힘"과 "전부 막힘"을 구별 못 함(위 high 결함이 21/21 green으로 통과한 이유). → 긍정 대조군 AC + 테스트 과업 신설.
  - `[medium]` `[bad_spec]` 재정의한 관리자 쓰기 정책 6개 중 4개가 양방향 미검증(`profiles_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete`). → 정지/활성 양방향 AC 신설.
  - `[medium]` `[bad_spec]` Intent Always 2항의 "쓰기 경로 전수조사 + 막는다/안 막는다 판정" 산출물이 Tasks에 과업으로 없어 Design Notes에 목록이 없다. 판정 없는 경로 4종 실측 확인(`wishlists_*`·`chat_room_reads_*`·`increment_listing_view`·`chat_rooms_insert_participant`). → 실측 쿼리를 지정한 전수조사 과업 + conventions §8 "막지 않는 범위" 명시 요구 신설.
  - `[medium]` `[bad_spec]` [[DW-674]]의 trigger가 명시한 "타인 명의 `listings` INSERT 42501" 단언이 AC에 없었고, 그 단언 없이 DW-674가 done으로 닫혔다(저장소 전역 grep으로 부재 확인). → 해당 AC 신설.
  - `[low]` `[bad_spec]` storage 소유자 join에 `l.seller_id = auth.uid()`가 없어 남의 on_sale 매물 id를 자기 uid prefix 아래 붙여 파일을 심을 수 있다(0031의 `listing_images` 정책은 이 축을 본다). → join 조건 + AC 신설.
  - `[low]` `[bad_spec]` 2번째 경로 세그먼트가 UUID가 아닌 레거시 오브젝트를 소유자가 영구 삭제 불가. → 부정형 DELETE로 함께 해소 + AC 신설.
  - `[low]` `[bad_spec]` `supabase/seed.sql:170`이 0033이 지운 계약("트리거가 role 메타를 반영한다")을 여전히 사실로 적는다 — `_create_user` 사본 4개만 맞추고 다섯 번째 생산자를 빠뜨렸다. → seed.sql 과업 신설. 함께 `conftest._create_user`의 사후 role UPDATE rowcount 미단언도 과업화.
  - reject 8건(전부 low): `sprint-status.yaml` 모순 지적(그 변경은 dev 실행이 아니라 오케스트레이터가 한 것) · `api/uv.lock` 부산물 미기재(의존성은 이전 커밋에서 이미 선언됨) · `split_part` 4중복 리팩터 요구(A3 "안 깨진 걸 리팩터하지 않는다") · project-context 규칙10 예외 미기재(conventions §9.1이 이미 새 번호 전진을 허용) · triage 카운트 표기·`review_loop_iteration` 지적(워크플로 산출 형식 자체) · DW-799 귀결 문구 보강 · `test_suspended_seller_cannot_update_storage_object` 사후 상태 재확인(rowcount 0으로 충분) · storage DELETE 테스트가 플랫폼 트리거를 끄고 본다는 점(테스트 헤더에 이미 명시, 대장 문구 수정은 이번 실행의 권한 밖).
  - defer 0건 — bad_spec 루프백이라 하위 분류는 moot(step-04 규칙). 재파생 후 리뷰에서 다시 판정된다.

### 2026-08-11 — Review pass (재파생본 리뷰, bad_spec 루프백 #1 이후)
- intent_gap: 0
- bad_spec: 0
- patch: 10 (medium 6, low 4)
- defer: 2 (medium 1, low 1)
- reject: 9 (low 9)
- addressed_findings:
  - `[medium]` `[patch]` 새 테스트가 `42501`만 단언해 **GRANT 누락으로 죽은 것과 RLS 거부가 구별되지 않았다.** 저장소 관례(`test_chat_unread_real_db.py`의 `_RLS_MESSAGE_MARK`)와 스펙 Code Map이 요구한 이중 단언이 빠져 있었다 — 이 스토리 1차 리뷰에서 실제로 storage GRANT 오류가 42501로 통과한 전례가 있다. 거부 단언 12곳 전부에 `"row-level security policy"` 메시지 단언 추가.
  - `[medium]` `[patch]` 활성 판매자의 `listings` INSERT/UPDATE **긍정 대조군이 없었다** — `listings_insert_own`을 "전부 거부"로 잘못 써도 전 테스트 green. `test_active_seller_can_insert_and_update_own_listing` 추가.
  - `[medium]` `[patch]` `0032`가 보존한다고 주장한 **0015의 sold-전환 비대칭**(`with check`는 그대로)이 아무 검사에도 없었다 — FR7 판매완료가 죽어도 green. `test_active_seller_can_mark_sold_but_cannot_further_update_sold_listing` 추가.
  - `[medium]` `[patch]` `chat_messages_insert_participant`의 **방 참가 조건**을 재타이핑했는데 저장소 전체에 비참가자 INSERT 거부 단언이 0건이었다(다른 파일의 chat INSERT는 전부 postgres 소유자라 RLS 우회). 조건이 빠지면 아무 로그인 사용자나 남의 방에 글을 쓸 수 있는데 전 테스트 green. `test_third_party_non_participant_cannot_insert_chat_message` 추가 — **red/green 직접 확인.**
  - `[medium]` `[patch]` `listing_images`의 **sold 축(0031, DW-390)**이 재타이핑됐는데 검사가 없었다(`storage.objects`의 같은 축에는 있었다). sold 매물 사진행 쓰기 + 비소유자 쓰기 테스트 2건 추가.
  - `[medium]` `[patch]` `storage.objects` UPDATE 테스트 3건이 전부 `metadata`만 바꿔 **`name`을 바꾸는 경로가 미검증**이었다. 테스트 추가. ⚠️ 처음 짠 형태(남의 uid 경로로 통째 rename)는 red 검증에서 **안 잡히는 검사**로 판명돼(SELECT 정책이 독자적으로 막아 `with check`를 완전히 열어도 green) 형태를 바꿔 다시 짰다 — 자기 uid는 유지하고 `listing_id`만 남의 것으로 바꾸는 `test_active_owner_cannot_relink_storage_object_to_others_listing`. 이 형태에서 red→green 직접 확인.
  - `[low]` `[patch]` `supabase/seed.sql:436` — 스펙이 `:170`·`:436` 둘 다 지목했는데 :170만 반영돼, 0033이 지운 계약을 두 번째 시드 블록이 계속 문서화하고 있었다. 정정.
  - `[low]` `[patch]` `0032`가 `admin_restore_sold_listing` 주석을 통째로 다시 쓰면서 **열린 장부 항목 DW-719의 유일한 코드 내 포인터 문장을 지웠다**(함수명 교체만 필요했던 재작성). 복원.
  - `[low]` `[patch]` `docs/conventions.md` §6이 스스로 요구하는 "정의자 함수는 쓰기 경로도 이 목록에 올린다"를 `is_admin_active()`가 안 지키고 있었다 — 관리자 쓰기 7경로 전부의 유일한 판정식인데 자기 항목이 없었다. §6 항목 + `comment on function` 추가.
  - `[low]` `[patch]` `0032` 9절 전수조사 합계가 15/6이었으나 실측은 **16/5** — `increment_listing_view`(함수)를 정책 그룹에도 계상해 합계만 우연히 21로 맞았다. "합계가 맞는다"는 자기검사가 누락을 못 잡는 상태였다. 정정.
  - `defer`: 전수조사 판정 목록이 **실행되는 검사가 아니다** — 새 `authenticated` 쓰기 정책을 추가해도 아무것도 red가 안 된다(DW-669가 생긴 방식 그대로). 새 인프라가 필요해 이월([[DW-803]]).
  - `defer`: 정지된 판매자의 매물이 계속 노출·문의 가능하고, 차단된 쓰기가 사용자에게 **"본인 매물만…"** 이라는 엉뚱한 이유로 보인다. 화면은 Never 절 범위 밖이라 이월([[DW-804]]).
  - reject 9건(전부 low): `increment_listing_view`가 `updated_at`을 오염시킨다는 지적 — **0020이 이미 전용 트리거로 막아 놨다(사실무근, 실측 확인)** · `listings_delete_own`에 sold 가드 없음(sold 매물 삭제는 FR6이 상태 무관으로 허용한 원래 설계, 이 변경이 만든 문제 아님) · `profiles` 행 없는 사용자가 정지와 같은 신호를 받음(어느 쪽이든 거부가 옳고 DW-670 본문 수정은 이번 실행 권한 밖) · owner UPDATE 긍정형/DELETE 부정형 비대칭(스펙이 명시 결정한 사항) · `split_part` 4중복 리팩터(A3 "안 깨진 걸 리팩터하지 않는다") · `api/uv.lock` 부산물(의존성은 이전 커밋에서 이미 선언) · 다른 테스트 3파일의 role 메타(계약 주장을 하지 않아 무해) · Storage HTTP API 미검증(테스트 헤더에 이미 명시된 기존 공백) · `Auto Run Result`·`sprint-status` 불일치(이 Finalize 단계가 갱신하는 항목이라 리뷰 findings 아님).

### 2026-08-11 — Review pass (3차 후속 리뷰, `status: done` 스펙 재진입)
- intent_gap: 0
- bad_spec: 0
- patch: 10 (medium 4, low 6)
- defer: 5 (medium 2, low 3)
- reject: 6 (low 6)
- addressed_findings:
  - `[medium]` `[patch]` 재정의한 관리자 쓰기 정책 6개 중 5개(`profiles_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete`·`admin_restore_sold_listing`)에 **활성 비관리자 거부 축이 없었다** — 지난 패스가 추가한 것은 정지/활성 관리자 양방향뿐이라, 개별 정책이 `using (true)`가 돼도 전 스위트가 green이었다(가장 날카로운 경우: 아무 로그인 사용자나 남의 `profiles` 행을 삭제). 5건 추가.
  - `[medium]` `[patch]` `chat_messages_insert_participant`의 **`auth.uid() = sender_id` 축**이 미검증 — `0032`가 이 정책을 통째로 재타이핑했는데, 저장소의 모든 채팅 INSERT는 postgres 소유자(RLS 우회)이거나 본인 명의라 이 조건을 빼도 green이었다. 정상 참가자가 **상대방 명의로** 메시지를 심을 수 있고(0023이 그 위조 행을 브로드캐스트, 0024~0026은 피해자 자신의 메시지로 세어 배지가 안 움직인다), 방 소유자와 달리 이 축을 보증하는 트리거도 없다. 테스트 추가.
  - `[medium]` `[patch]` `listings_update_own`의 **`with check (auth.uid() = seller_id)`** 가 미검증 — UPDATE 테스트 4건이 전부 `price`/`status`만 바꿔 `using`이 다 받아냈다. `with check`를 `(true)`로 열면 활성 판매자가 자기 매물을 **남의 계정으로 재할당**할 수 있고(0007 트리거가 `seller_name`까지 맞춰 준다) 전 테스트 green. 테스트 추가.
  - `[medium]` `[patch]` §10.1 삭제순서 회귀 테스트가 **`on_sale` 분기만** 고정 — 정작 흥미로운 쪽은 sold(매물이 살아 있는 동안은 사진 DELETE가 막히다가 행이 사라지는 순간 열린다)인데 비어 있었다. sold 분기 추가 + 실제 클라이언트 순서(① `listing_images`에서 경로 사전조회 → ② 매물 행 DELETE(cascade) → ③ 오브젝트 DELETE)를 그대로 재현하도록 재작성.
  - `[low]` `[patch]` 미차단 판정 3종(찜·안읽음 커서·방 생성)이 **주석·문서 3벌에만 있고 검사가 0건** — 정지 조건이 그쪽으로 새거나 면제가 조용히 사라져도 아무것도 red가 안 된다. 정지 회원이 실제로 성공하는 것을 고정하는 긍정 테스트 추가.
  - `[low]` `[patch]` `0032`의 경로 UUID 정규식이 `[0-9a-fA-F]`라 **대문자 UUID 경로를 통과**시키는데, `0013`의 `enforce_listing_images_storage_path` 트리거는 대소문자 구분 텍스트 비교라 같은 경로의 `listing_images` 행을 P0001로 거부한다 — 행을 영원히 만들 수 없는 자리에 파일만 올라간다(실측 확인). 정규식 4곳을 `[0-9a-f]`로 좁히고 거부 테스트 추가.
  - `[low]` `[patch]` `listings_update_own`의 "`with check`는 불필요" 논증이 **`listings`에 permissive UPDATE 정책이 하나뿐인 동안만** 성립한다는 의존성을 안 적었다(permissive 정책은 `with check`끼리 OR된다). 주석에 의존성 한 줄 추가(정책 자체는 스펙 결정대로 유지).
  - `[low]` `[patch]` `0032` 9절이 전수조사표가 여기 있는 이유를 *"이 실행의 guardrail이 스펙 파일 편집을 금지해"* 라고 적었으나 **거짓** — 스펙 Design Notes에 같은 표가 있다. 진짜 이유(self-contained 마이그레이션)로 정정하고 `docs/conventions.md` §8을 정본으로 명시.
  - `[low]` `[patch]` `_create_user` 사본 3벌이 서로 다른 규칙으로 갱신돼 있었다(`test_restore_sold_listing_rpc_real_db.py`만 role 미단언 + 메타 `'{}'`). 세 벌을 같은 계약으로 통일.
  - `defer`: `increment_listing_view`(SECURITY DEFINER가 `anon,authenticated` 권한으로 `listings`를 UPDATE)의 "안 막는다" 판정만 대장 항목이 없고, 사유(*"anon도 호출한다"*)가 정지된 authenticated를 통과시킬 근거가 못 된다 — [[DW-805]].
  - `defer`: `/admin` 콘솔 진입 게이트(`requireRole`)가 `status`를 안 봐 정지된 관리자가 살아 있는 UI를 보고 모든 작업이 조용히 0행으로 실패한다 — [[DW-806]]([[DW-804]]는 판매자 화면만 다뤘다).
  - `defer`: `storage.objects` 검증이 플랫폼 보호 트리거를 끈 **직접 SQL**로만 이뤄져 실제 Storage HTTP API 경로가 미검증 — [[DW-807]].
  - `defer`: `0032` 이후 [[DW-670]]이 기록한 증상(23503)이 재현되지 않고 42501로 바뀌었다(본문 수정은 이 실행 권한 밖이라 신규 항목으로) — [[DW-808]].
  - `defer`: 활성 관리자가 한 문장으로 자기 자신을 정지시킬 수 있다(`is_admin_active()`가 `stable`이라 문장 스냅샷을 본다, 실측 `UPDATE 1`) — [[DW-800]]이 기록한 것은 결과였고 이 항목은 그 상태로 들어가는 경로 — [[DW-809]].
  - reject 6건(전부 low): `listings_delete_own`에 sold 가드 없음(FR6 설계, 지난 패스가 이미 판정) · 스펙/`sprint-status` 상태면 불일치(이 Finalize 단계와 오케스트레이터 소관) · 프렐류드의 storage GRANT가 anon까지 준다는 지적(플랫폼 기본값을 재현하는 것이 그 파일의 역할, 기존 public 스키마 GRANT 줄과 같은 패턴) · `is_admin_active()`의 `search_path = public` vs `''`(본문이 전부 스키마 한정이라 값이 무의미, 형제 `is_admin()`과 같은 형태 유지 — A3) · storage owner UPDATE 긍정형/DELETE 부정형 비대칭(스펙 명시 결정, 지난 패스가 이미 판정) · `handle_new_user()`의 email NULL 시 `name` NULL(0009부터 있던 동작이고 0033이 바꾸지 않았다).

## Design Notes

**왜 `is_admin_active()`를 새로 만드나 (Always 3항 "새 헬퍼 불필요"와 배치되지 않는 이유):**
Intent의 3번 사실은 "판매자 본인 예외조건은 헬퍼 없이도 동작한다"는 뜻이지, "admin 쪽도 헬퍼가 필요 없다"는
뜻이 아니다. 판매자 조건(`exists (select from profiles where id=auth.uid() ...)`)은 **listings/listing_images/
storage.objects** 정책 안에서 쓰인다 — `profiles`가 아닌 다른 테이블의 정책이므로 자기참조가 아니다.
반면 `profiles_update_admin`/`profiles_delete_admin`은 **`profiles` 자신을 보호하는 정책**이고, 그 안에서
"호출자(auth.uid())가 활성 admin인가"를 알려면 다시 `profiles`를 서브쿼리해야 한다 — 이게 정확히 0001·0005
주석이 `is_admin()`을 SECURITY DEFINER로 분리해야 했던 이유("RLS 안에서 profiles를 직접 서브쿼리하면
infinite recursion in policy")와 같은 함정이다. 그래서 admin+status 판정만 새 SECURITY DEFINER 함수로 뺀다.
나머지 admin 소비처(`listings_delete_admin` 등)는 `profiles`가 아닌 테이블 정책이라 원칙적으로 직접 서브쿼리도
가능하지만, 관리자 판정 로직을 한 곳(`is_admin_active()`)에 모아 두는 편이 재조사 없이 일관되다.

**정지 회원 발신 차단 결정 — 결론: 막는다 (2026-08-11 실DB 확인 완료).**
근거: 0023의 브로드캐스트 트리거(AFTER INSERT)와 0024~0026의 안읽음 계산(INSERT 이후 SELECT)은 전부
"INSERT가 이미 성공한 뒤"에만 발화·조회한다 — 정지 발신자의 INSERT 자체를 막으면 그 행이 아예 없으므로
트리거가 돌지 않고, **다른 정상 참가자의 메시지 흐름에는 영향이 없다.** 이걸 추론으로 끝내지 않고
`test_active_participant_chat_still_broadcasts_and_updates_unread`가 실DB에서 정상 참가자의 발신 →
브로드캐스트 → 안읽음 카운트가 그대로 도는 것을 확인한다(Block-If 3번 조건이 실제로 발동하지 않음을
측정으로 확인한 것이다 — Epic 16이 고친 축을 되돌리지 않았다). `chat_messages_insert_participant`(0003)에
정지 조건을 추가했고, `docs/conventions.md` §8에도 한 줄로 등재했다.
⚠️ 방 **생성**(`chat_rooms_insert_participant`)은 막지 않았다 — 판단 대상이 "발신"이었다. 귀결은 [[DW-799]].

**쓰기 경로 전수조사 표 (2026-08-11 로컬 55322 실측, `0032`·`0033` 적용 후 — Always 2항):**

실측 쿼리 2개로 뽑았다(grep 목록 아님). `authenticated` 대상 non-SELECT 정책 **21행**,
`public` 스키마 SECURITY DEFINER 함수 **11행**. 아래 판정 합계가 21·11과 일치한다.
동일 내용이 `0032` 9절 주석에도 self-contained하게 들어 있다(마이그레이션만 읽어도 판정이 보이게).

| 경로(정책/함수) | 판정 | 이유 |
|---|---|---|
| `listings_insert_own`·`_update_own`·`_delete_own` | 막는다 | 불변식의 "매물" 축 본체. |
| `listing_images_insert_own`·`_update_own`·`_delete_own` | 막는다 | 불변식의 "사진(행)" 축. |
| `listing_images_objects_owner_insert`·`_update`·`_delete` | 막는다 | 불변식의 "파일" 축. **DELETE만 sold 조건이 부정형** — 위 삭제 순서 상호작용 참조. |
| `listings_delete_admin`·`profiles_update_admin`·`profiles_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete` | 막는다 | 불변식의 "관리자 쓰기" 축 — `is_admin()`→`is_admin_active()` 교체. 읽기 정책은 `is_admin()` 그대로. |
| `chat_messages_insert_participant` | 막는다 | 채팅 발신 결정(아래 블록) — Block-If 미충족이라 기본값대로 막았다. |
| `chat_rooms_insert_participant` | **안 막는다** | 판단 대상은 "발신"이었고 방 "생성"은 불변식 네 범주에 없다. 귀결(정지 회원이 만든 빈 방이 판매자 목록에 남음)까지 [[DW-799]]에 기록. |
| `wishlists_insert_own`·`wishlists_delete_own` | **안 막는다** | 찜은 본인만 보는 개인화 데이터 — "타인에게 영향을 주는 쓰기"가 아니다. [[DW-801]]. |
| `chat_room_reads_insert_participant`·`chat_room_reads_update_own` | **안 막는다** | 본인 안읽음 커서, 상대방에게 노출되는 값이 없다(§12 확인). [[DW-802]]. |
| `admin_restore_sold_listing`(SD) | 막는다 | [[DW-721]]이 지목한 RLS 우회 경로 — `is_admin_active()`로 교체. |
| `is_admin_active()`(SD) | 신설 | 이 스토리가 만든 판정 함수. |
| `is_admin()`(SD) | 손대지 않음 | Always 3항 — 전역으로 좁히면 관리자 **읽기** 정책까지 닫힌다. |
| `chat_messages_broadcast`·`chat_rooms_touch_last_message`·`enforce_chat_room_seller`·`set_chat_room_names`·`set_listing_seller_name`(SD) | 해당 없음 | 전부 INSERT **성공 이후**에만 도는 트리거 부산물 — 그 INSERT를 막으면 애초에 안 불린다. 함수 자체에 조건을 걸 자리가 아니다. |
| `increment_listing_view`(SD) | **안 막는다** | `anon`도 호출하므로 `profiles` 신원 자체가 없는 호출자가 있다 — 정지 게이트를 걸 자리가 아니다. 조회수 집계는 불변식의 "매물 쓰기" 범주 밖이라는 판단도 함께. |
| `handle_new_user()`(SD) | 해당 없음 | 가입 트리거 — "정지된 사용자의 쓰기"라는 전제 자체가 성립하지 않는다. (0033이 별건으로 손봤다 — [[DW-682]].) |
| `get_seller_public_summary()`(SD) | 해당 없음 | 읽기 전용. |

**⚠️ 삭제 순서 상호작용 (2026-08-11 실측, 재파생 시 반드시 보존할 근거):**
`storage.objects` 소유자 정책에서 `listings` join을 **INSERT/UPDATE와 DELETE에 같은 형태로 걸면 안 된다.**
로컬 실 스택(55322) 롤백 트랜잭션으로 재현: ① 매물이 살아 있을 때 소유자 사진 DELETE → `DELETE 1`, 남은 0건(정상).
② 실제 클라이언트 순서(매물 행 먼저 DELETE → 사진 DELETE) → 매물 `DELETE 1`, 사진 **`DELETE 0`**, 고아 1건 잔존.
`web/src/lib/storage/upload.ts`의 `deleteListingImageObject`는 RLS 0행 응답을 "이미 없음"으로 읽어 `true`를 돌려주므로
**화면·로그 어디에도 실패가 안 뜬다.** 그래서 DELETE는 `not exists (... status='sold')` 부정형으로 쓴다(Tasks 4항).

**red를 실제로 확인한 객체 / 확인하지 않은 객체 (Verification 절이 요구한 목록 — 2026-08-11):**
- **red 확인함(2차 리뷰 patch, 이 세션이 직접 측정)**: `chat_messages_insert_participant`의 **방 참가 조건** —
  그 조건만 뺀 정책으로 교체 → `test_third_party_non_participant_cannot_insert_chat_message` red 확인 → 원복 green 확인
  (교체 전·후 `pg_policies` 상태를 단언해 배경 세션 간섭 배제).
- **red 확인함 — 단, 첫 형태는 "안 잡히는 검사"였고 실측으로 고쳤다**:
  `listing_images_objects_owner_update`의 **`with check` 단독 축**.
  ⚠️ 처음 짠 형태(오브젝트 `name`을 **남의 uid/남의 listing_id** 경로로 통째 rename)는
  `with check`를 `true`로 완전히 열어도 **green으로 남았다**(이 세션이 정책 상태를 교체 전·후로
  단언하며 실측). 원인: `listing_images_objects_owner_select`가 UPDATE의 **NEW 행에도** 적용되는데
  그 정책은 경로 **첫 세그먼트만** 보므로, 첫 세그먼트를 남의 uid로 바꾸면 SELECT 정책이 독자적으로
  막아 `with check`가 무엇을 보는지 증명되지 않는다. → 테스트를 **자기 uid는 유지하고 listing_id만
  남의 것으로 바꾸는** 형태로 다시 짰고(`test_active_owner_cannot_relink_storage_object_to_others_listing`),
  그 형태에서 `with check`를 `bucket_id` 하나로 약화 → **red 확인** → `0032` 원복 → **green 확인**
  (교체 전·후 `pg_policies` 상태 단언으로 간섭 배제). 메모리 `guard-proof-must-vary-shape`의 실사례가
  이 스토리에서 한 번 더 재현된 셈이다 — 자기가 고른 표기로만 깨면 그 검사가 무엇을 보는지 증명되지 않는다.
- **red 확인함(1차 구현 세션 보고, 6+1)**: `listings_insert_own` · `listing_images_insert_own` ·
  `listing_images_objects_owner_insert` · `listing_images_objects_owner_delete`(**양방향** — 정지 조건을 빼면
  정지 판매자가 지울 수 있어 red, sold 조건을 `not exists`→`exists`로 되돌리면 §10.1 순서 회귀 테스트가 red) ·
  `profiles_update_admin` · `admin_restore_sold_listing` · `chat_messages_insert_participant`.
- **red 확인함(3차 리뷰 patch — 구현 세션이 1축, 이 리뷰 세션이 다른 형태로 1축을 각각 측정)**:
  `profiles_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete`·
  `admin_restore_sold_listing`의 **관리자 판정 축**(구현 세션: 각 정책을 `using (true)`로 약화 → red → 원복 green /
  이 리뷰 세션: 정책은 그대로 두고 **`is_admin_active()` 본문에서 `role='admin'` 절만 제거** → 같은 5건 red →
  마이그레이션 파일 재적용 → 51건 green. 두 형태가 서로 다른 자리를 깨는데 같은 5건이 잡혔다) ·
  `chat_messages_insert_participant`의 **`sender_id` 축**(조건 제거 → red → 원복 green) ·
  `listings_update_own`의 **`with check` 단독 축**(`(true)`로 약화 → red → 원복 green) ·
  `listing_images_objects_owner_insert`의 **경로 UUID 정규식**(`[0-9a-f]`→`[0-9a-fA-F]` 되돌림 → red → 원복 green).
  ⚠️ 이 축의 첫 설계("남의 행을 DELETE 시도")는 **안 잡히는 검사**였다 — Postgres가 DELETE 대상 행도 SELECT 정책으로
  거르므로 침입자에겐 그 행이 애초에 안 보여, admin 정책을 완전히 열어도 결과가 0행으로 같았다. 그래서 "본인에겐
  SELECT가 열려 있지만 admin 정책 말고는 그 DELETE를 허용할 정책이 없는 조합"으로 다시 짰다(메모리
  `pg-select-policy-applies-to-update-new-row`가 UPDATE의 NEW 행에서 기록한 함정이 DELETE 대상 행에서도 재현된 것).
- **red 확인 안 함**: `listings_update_own`·`listings_delete_own` · `listing_images_update_own`·`_delete_own` ·
  `listing_images_objects_owner_update` · `listings_delete_admin`·`profiles_delete_admin`·`chat_rooms_delete_admin`·
  `chat_messages_delete_admin`·`listing_images_objects_admin_delete`. 전부 위에서 red를 확인한 객체와 **같은
  조건식·같은 헬퍼**를 쓰지만, "같은 형태니 괜찮다"는 추론이지 측정이 아니다 — 다음에 이 파일을 손대는
  세션은 이 줄을 근거로 삼지 말고 다시 재라.

**이 검사가 안 보는 것 (2026-08-11 실측 기준):**
- `is_admin_active()` 자체의 SECURITY DEFINER 우회가 다른 신규 SECURITY DEFINER 함수에도 일관되게
  적용되는지는 이 스토리가 만든 함수들만 본다 — 저장소 전체의 SECURITY DEFINER 함수 감사는 범위 밖.
- 원격(prod) Supabase의 `authenticated` GRANT가 로컬과 동일한지는 이 스토리가 검증하지 않는다
  ([[DW-722]] 범위) — 로컬 grant 재적용으로 우회해 테스트한다.
- 관리자 감사 로그가 없으므로 "누가 언제 이 정책에 막혔는지"는 기록되지 않는다([[DW-718]], 별건).

## Verification

**Commands:**
- 로컬 스택 기동 후 GRANT 보정(DW-722): `psql "$LOCAL_DB_URL" -c "grant all on tables in schema public to anon, authenticated, service_role;"` -- expected: 이후 `authenticated`로 `profiles` SELECT 가능(migration-check-prelude.sql 전체를 로컬에 돌리지 않는다 — auth.uid() 스텁 오염 위험, DW-722 경고).
- `cd api && TEST_DATABASE_URL="$LOCAL_DB_URL" uv run pytest tests/integration/test_suspended_write_block_real_db.py -v` -- expected: 전부 통과(위 AC 전항목).
- `python3 scripts/check_migrations.py` -- expected: exit 0(정적 밀집·동적 self-containment 통과, `0032`·`0033` 포함).
- red 증명(CLAUDE.md B4): `0032`의 정지 조건 부분만 임시로 되돌린 사본을 로컬 DB에 적용 → 위 pytest 재실행 → 정지 관련 테스트가 실제로 red가 되는지 확인 → 원복 → green 재확인. (표기를 바꾸는 두 번째 축: 정책 자체를 되돌리는 방식으로 위 CLAUDE.md B4 요구를 만족한다 — 테스트 코드 쪽을 바꾸는 첫 번째 축과 다른 형태.)
  ⚠️ **되돌려 볼 대상을 고르지 말고, 되돌린 것과 안 되돌린 것을 목록으로 적는다.** 이전 판은 14개 변경 객체 중 3개만 red 증명하고 "이중 증명"이라고 적었고, 실제로 red를 안 재본 자리(storage owner DELETE)에 결함이 있었다. 최소한 아래는 각각 red를 확인한다: `listings_insert_own` · `listing_images_insert_own` · `listing_images_objects_owner_insert` · **`listing_images_objects_owner_delete`(양방향 — 정지 조건을 빼면 정지 판매자가 지울 수 있어야 red, sold 조건을 `not exists`에서 `exists`로 바꾸면 위 §10.1 순서 회귀 테스트가 red가 되어야 한다)** · `profiles_update_admin` · `admin_restore_sold_listing`. 실제로 red를 확인한 객체와 확인하지 않은 객체를 Design Notes의 "이 검사가 안 보는 것"에 그대로 적는다.
- 긍정 대조군 확인: 위 pytest에서 활성 판매자의 `listing_images`·`storage.objects` 쓰기 테스트가 **green**인 것을 함께 확인한다(전부 거부되는 상태로 회귀했으면 여기서 잡힌다).

**Manual checks (if no CLI):**
- `docs/conventions.md` §8에 정지 관련 한 줄과 채팅 발신 차단 결정이 실제로 등재됐는지 눈으로 확인.
- `deferred-work.md`에서 [[DW-669]]·[[DW-717]]·[[DW-721]]·[[DW-674]]·[[DW-682]]·[[DW-782]]가 `status: done`(또는 범위에서 뺀 항목은 갱신된 `trigger:`)으로 반영됐는지 확인.

## Auto Run Result

**요약**: 정지(`profiles.status='suspended'`) 회원의 쓰기를 매물·사진·파일·관리자 RPC·채팅 발신
전 경로에서 막는 RLS 정책 + `is_admin_active()` SECURITY DEFINER 헬퍼를 새 마이그레이션
`0032`·`0033`으로 구현하고, 실DB 통합 테스트 **41건**으로 검증했다.
**이 실행은 후속 리뷰 패스로 시작해 `bad_spec` 루프백 1회를 돌았다** — 1차 구현본(`3de63c5`)에
정상 판매자의 매물 삭제 후 사진 정리가 영구 실패하는 결함이 있어 코드를 baseline으로 되돌리고,
스펙을 고친 뒤 재파생했다. 재파생본에 대한 2차 리뷰에서 나온 patch 10건도 전부 반영했다.

**변경 파일**:
- `supabase/migrations/0032_suspended_write_block.sql` (신규) — `is_admin_active()` 함수 +
  `listings`·`listing_images`·`storage.objects`·`profiles`·`chat_rooms`·`chat_messages`·
  `admin_restore_sold_listing` 16개 쓰기 정책/함수 재정의 + 9절 쓰기 경로 전수조사 판정 주석.
- `supabase/migrations/0033_remove_legacy_role_passthrough.sql` (신규) — [[DW-682]], 가입 트리거
  buyer/seller 통과 분기 제거.
- `api/tests/integration/test_suspended_write_block_real_db.py` (신규, 41건) — 스펙 AC 전항목 +
  [[DW-674]] 소유권 회귀 + §10.1 삭제 순서 회귀 + 긍정 대조군 + 관리자 6정책 양방향.
- `scripts/migration-check-prelude.sql` — `storage` 스키마 USAGE + `storage.objects` GRANT·
  `metadata` 컬럼 스텁(없으면 CI가 RLS가 아니라 권한 오류로 죽는다).
- `docs/conventions.md` — §8에 정지 게이트 등재(막는 범위 + **막지 않는 범위** 함께),
  §6 정의자 함수 목록에 `is_admin_active()` 항목 추가, `admin_restore_sold_listing` 각주 정정.
- `supabase/seed.sql` — `:170`·`:436` 두 곳의 role 메타 주석을 0033 이후 계약으로 정정.
- `api/tests/integration/conftest.py`·`test_chat_idempotency_real_db.py`·
  `test_role_check_relax_real_db.py`·`test_restore_sold_listing_rpc_real_db.py` — `_create_user`
  계약 갱신 + 사후 role UPDATE `rowcount` 단언.
- `api/uv.lock` — `python-dotenv` 락 동기화(의존성 자체는 이전 커밋 `9988976`이 이미 선언).
- `_bmad-output/implementation-artifacts/deferred-work.md` — [[DW-669]]·[[DW-717]]·[[DW-721]]·
  [[DW-674]]·[[DW-682]]·[[DW-782]] done + 신규 [[DW-799]]·[[DW-801]]·[[DW-802]]·[[DW-803]]·[[DW-804]] 등재.
- 스펙 본문(이 파일) — Tasks 4항 verb별 재작성, AC 8개 추가, 전수조사 표·red 증명 목록 작성,
  Spec Change Log 2건, Review Triage Log 3패스.

**리뷰 findings 분류(3패스 합계)**:
- 1패스(후속 리뷰): intent_gap 0 · **bad_spec 8**(high 1·medium 4·low 3) · patch 0 · defer 0 · reject 8 → 코드 되돌림 + 스펙 수정 + 재파생.
- 2패스(재파생본): intent_gap 0 · bad_spec 0 · **patch 10**(medium 6·low 4, 전부 수정) · defer 2([[DW-803]]·[[DW-804]]) · reject 9.
- 3패스(`status: done` 재진입): intent_gap 0 · bad_spec 0 · **patch 10**(medium 4·low 6, 전부 수정) ·
  defer 5([[DW-805]]~[[DW-809]]) · reject 6. 테스트 41→**51건**.
  이 패스가 잡은 것은 전부 **"있는 정책이 틀렸다"가 아니라 "그 정책이 옳다는 증거가 없다"** 였다 —
  관리자 정책 5개·채팅 `sender_id`·`listings`의 `with check`·sold 삭제순서가 각각 완전히 열려도
  전 스위트가 green이었다(전부 실제로 깨서 확인). 실제 결함은 경로 UUID 정규식 1건(대문자 통과).

**검증 수행(전부 이 세션이 직접 실행·관찰)**:
- `python3 scripts/check_migrations.py` — exit 0(정적 + 동적 self-containment).
- 로컬 실 Supabase(55322) `api` 전체 — **647 passed, 8 skipped**(8건은 기존 환경 게이트).
- **CI(`api-db` 잡) 조건 재현** — 일회용 `pgvector/pgvector:pg17` 컨테이너에 프렐류드 + 전
  마이그레이션 순서 적용 후 `tests/integration` — **157 passed**. 컨테이너 폐기 완료.
- **결함 재현·해소 실측(bad_spec 루프백 근거)**: 1차 구현본에서 §10.1 순서(매물 행 먼저 삭제 →
  사진 정리)로 사진 DELETE가 **0행, 고아 1건 잔존**. 수정 후 같은 프로브에서 **DELETE 1, 고아 0건**.
  반대 방향도 확인 — sold 매물 사진 DELETE 0행(차단 유지), 정지 판매자 사진·매물 DELETE 0행(차단 유지).
- **red→green 직접 확인**: `chat_messages_insert_participant`의 방 참가 조건만 제거 →
  비참가자 테스트 red → 원복 green(교체 전·후 `pg_policies` 상태를 단언해 간섭 배제).
- **red 확인 결과 "안 잡힌다"로 판명된 축도 기록**: rename 권한상승 테스트는 `with check`를
  `true`로 열어도 green이었다 — SELECT 정책이 독립적으로도 막기 때문(양쪽 각각 실측). 실제 구멍은
  없으나 그 테스트는 `with check` 단독 축을 분리하지 못한다. 이 사실을 테스트 docstring과
  Design Notes에 그대로 적었다.

**3패스 검증 수행(전부 이 리뷰 세션이 직접 실행·관찰)**:
- `python3 scripts/check_migrations.py` — exit 0(정적 33파일 + 동적 컨테이너 적용 + 프로브 3종).
- 로컬 실 Supabase(55322) `api/tests/integration` 전량 — **167 passed**(패치 전 대비 회귀 0).
- 대상 파일 단독 — **51 passed**(41 → 51, 신규 10건).
- **형태를 바꾼 red 증명**(메모리 `guard-proof-must-vary-shape`): 구현 세션이 각 정책을 `using (true)`로
  약화해 red를 봤으므로, 이 리뷰 세션은 **다른 자리**를 깼다 — `is_admin_active()` 본문에서 `role='admin'`
  절만 제거(`pg_proc.prosrc` 전후 단언) → 관리자 비-admin 테스트 **5건 전부 red** → 마이그레이션 파일
  재적용 → **51 green**. 두 형태가 서로 다른 객체를 깨는데 같은 5건이 잡혔다.
- 로컬 DB를 `0032` 파일로 재적용해 파일-DB 드리프트 0 확인(`pg_proc.prosrc` 대조 후 167 passed 재확인).
- defer 5건은 대장에 쓰기 전에 전부 실측했다 — `requireRole`이 `.select('role')`만 하는 것(파일 확인) ·
  `increment_listing_view`가 `prosecdef=t` + `{postgres,anon,authenticated}` 실행 권한(psql) ·
  활성 관리자의 자가 정지가 실제로 `UPDATE 1`로 성립하는 것(롤백 트랜잭션) · DW-670의 23503 경로가
  이제 42501로 선행 차단되는 것(정책 본문 대조).

**잔여 리스크**:
- [[DW-803]] — 전수조사 판정이 실행되는 검사가 아니다. 새 쓰기 정책을 추가하며 판정을 빠뜨려도
  아무것도 red가 안 된다(DW-669가 생긴 방식). 다음 쓰기 정책 마이그레이션 스토리로 이월.
- [[DW-804]] — 정지 판매자의 매물이 계속 노출·문의 가능하고, 차단된 쓰기가 사용자에게 소유권
  문제로 안내된다. 화면은 이 스토리 Never 절 범위 밖이라 이월.
- [[DW-799]]·[[DW-801]]·[[DW-802]] — 채팅방 생성·찜·안읽음 커서는 의도적으로 안 막았다(근거는
  전수조사 표와 각 항목에 기록).
- [[DW-800]] — 관리자 전원이 정지되면 psql 직접 접근 외 복구 경로가 없다.
- **웹·앱 클라이언트 표면은 이 실행이 검증하지 않았다.** 웹·앱 코드는 한 줄도 안 바뀌었지만,
  이 변경이 만든 새 거부 신호(정지 사유의 0행)를 화면이 어떻게 보이는지는 재보지 않았다 —
  그 축이 [[DW-804]]다. Storage HTTP API 경로도 미검증(테스트 헤더에 명시된 기존 공백).
- `sprint-status.yaml`의 `17-1`은 이 스토리 실행 밖에서(오케스트레이터가) `done`으로 바뀌어 있었고,
  `epic-17`은 `backlog` 그대로다 — 이 실행은 그 파일을 갱신하지 않았다.
- 대장에서 이 스토리가 쓴 resolution 3건(DW-669·674·782)의 **본문을 정정**했다(테스트 건수 19→35→41,
  DELETE 정책이 부정형이라는 사실). `status:`는 하나도 바꾸지 않았고 기존 항목을 다시 열지도 않았다.
  ⚠️ 3패스에서는 대장의 **기존 항목을 일절 수정하지 않았다**(오케스트레이터 지시) — [[DW-805]]~[[DW-809]] 신규 5건만 추가했다.
  그래서 [[DW-670]]의 낡은 본문과 [[DW-782]]의 resolution 문구는 그대로 남아 있고, 그 사실 자체를
  [[DW-808]]·[[DW-807]]에 기록했다. 이 두 항목의 본문 정정은 대장 소유자(오케스트레이터)의 몫이다.
- 3패스가 고친 것은 대부분 **검사의 공백**이었다 — 즉 지난 두 패스 시점에도 코드는 옳았지만 그게 옳다는
  증거가 없었다. 같은 형태의 공백이 아직 남아 있다: Design Notes의 "red 확인 안 함" 목록 10객체는
  여전히 *"같은 조건식을 쓰니 괜찮다"* 는 **추론**이지 측정이 아니다.
- `0032`를 in-place로 수정했다(P7 정규식). 원격 미적용 상태라 conventions §9.1 위반은 아니지만,
  **이미 이 파일을 적용해 둔 다른 로컬 DB가 있다면 재적용이 필요하다**(이 세션의 55322는 재적용 완료).
