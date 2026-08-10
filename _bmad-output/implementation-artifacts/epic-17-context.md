# Epic 17 Context: 접근 제어 마무리 (backend-only)

<!-- 손으로 작성(2026-08-10). Epic 17은 `epics-increment-2026-07-12.md`에 절이 없다 —
     Epic 15 진행 중 사용자 결정으로 신설된 에픽이고, 정본은 `sprint-status.yaml`의
     "--- Epic 17: 접근 제어 마무리 (backend-only) ---" 주석 블록이다.
     compile-epic-context가 만들 원본이 없으므로 이 파일이 그 자리를 대신한다. -->

## Goal

"정지(suspended)"라는 관리자 조치가 **데이터 계층에서 실제로 무엇을 막는지** 확정하고 강제한다.
지금은 화면(`MemberActions.tsx`)에 정지 버튼이 있고 `profiles.status` 값도 바뀌지만, **그 값을 읽어
무언가를 거부하는 코드가 저장소 전체에 0건**이다(DW-669 실측). 즉 정지된 회원은 계속 로그인해
매물을 등록·수정·삭제하고 사진을 올린다.

이 에픽은 backend-only다 — 새 화면을 만들지 않고, RLS 정책·DB 함수·마이그레이션과 그것을 지키는
자동 검사만 다룬다.

## Stories

- Story 17.1: 정지 회원 쓰기 차단 (RLS) — `17-1-정지-회원-쓰기-차단-rls`

## Requirements & Constraints

- **FR22(관리자 회원 정지)의 실질을 만든다.** 화면 액션이 이미 존재하므로 새 UI 요구는 없다.
- **정지는 "쓰기 행동"만 막는다. 열람은 그대로 허용한다.** `docs/conventions.md` §8이 세운
  "열람이냐 행동이냐" 축과 같은 기준이다. 구체적으로:
  - 정지된 회원도 로그인하고 매물을 **본다**.
  - 정지된 판매자의 기존 매물은 다른 구매자에게 **계속 보인다**(`listings_select_*`는 건드리지 않는다).
  - 막는 것은 INSERT/UPDATE/DELETE와 그에 딸린 사진·파일 쓰기다.
- **강제 지점은 앱 게이트가 아니라 데이터 계층이다**(CLAUDE.md B9 — "화면 방어로 대체하지 않는다").
  화면마다 정지 검사를 심으면 새 화면이 생길 때마다 빠진다. RLS에 박으면 웹·앱·향후 클라이언트가
  예외 없이 걸린다.
- **SECURITY DEFINER 경로는 RLS 밖이다.** RLS만 손보면 정의자 함수(RPC)로 우회된다 — [[DW-721]]이
  이 구멍을 실측해 뒀다. 그래서 이 에픽의 범위는 "RLS"가 아니라 **"쓰기 경로 전부"**다.
- **마이그레이션은 전진만 한다**(CLAUDE.md B3 · `docs/conventions.md` §9.1). 정책은 데이터가 아니라
  접근 규칙이므로 `drop policy → create policy`(같은 파일 안 즉시 재생성)는 §9.1이 명시 허용한
  전진 패턴이다 — 이미 `0015`·`0031`이 그렇게 했다.

## Technical Decisions

- **정지 판정식**: `exists (select 1 from public.profiles where id = auth.uid() and status = 'active')`.
  - 이 서브쿼리는 호출자 권한으로 평가되므로 `profiles` RLS를 탄다. `profiles_select_self`
    (`auth.uid() = id`, `to authenticated`)가 본인 행을 열어 주므로 **동작한다**(0001 실측 확인).
    SECURITY DEFINER 헬퍼를 새로 만들 이유가 없다.
  - ⚠️ 단, `authenticated`에 `profiles` 테이블 SELECT **GRANT**가 있어야 한다. 원격은 Supabase
    플랫폼 기본 GRANT가 주고 CI는 `scripts/migration-check-prelude.sql`이 재현하지만,
    **로컬 `supabase db reset` 직후에는 없다**([[DW-722]] 실측). 로컬 검증 전에 이걸 먼저 확인한다.
- **관리자 경로는 `is_admin()`을 전역으로 좁히지 않는다.** `is_admin()`에 `and status='active'`를
  더하면 **읽기 정책까지 함께 좁아진다**(`chat_rooms_select_admin`·`chat_messages_select_admin`·
  `listing_images` 관리자 SELECT 등). 그건 위 "정지는 열람을 막지 않는다" 제약과 정면으로 어긋난다.
  따라서 **쓰기 자리에만** 정지 조건을 더한다. `grep -n "is_admin()" supabase/migrations/*.sql`로
  확인한 관리자 **쓰기** 소비처:
  `profiles_update_admin`·`profiles_delete_admin`(0005) · `listings_delete_admin`(0005) ·
  `chat_rooms_delete_admin`(0005) · `chat_messages_delete_admin`(0005) ·
  `admin_restore_sold_listing`(0030, SECURITY DEFINER RPC) · `0014`의 관리자 쓰기 분기(83행).
  구현 세션은 이 목록을 **직접 재확인**한 뒤 범위를 정한다(이 목록을 그대로 믿지 않는다).
- **저장된 패치를 출발점으로 쓰되 그대로 재사용하지 않는다.**
  `bmad-dev-auto-intent-gap-patch-15-3-회원관리-역할통합-반영.diff`에 15-3 세션이 짜고 검증했다가
  Epic 15의 UI-only 제약 때문에 되돌린 `0030_listings_suspend_gate.sql` 전문이 보존돼 있다.
  **그 코드에는 코드리뷰가 실측한 구멍 2개가 그대로 있다**(관리자 delete 미차단, 사진·파일 경로
  미차단). 재사용하면 구멍째로 간다.
- **스토리지 경로 계약**: `listing-images` 버킷의 오브젝트 이름은 `{seller_uid}/{listing_id}/{파일명}`
  이다(0013이 트리거로 강제). 따라서 `storage.objects` 정책에서 `split_part(name,'/',2)`로
  `listing_id`를 얻을 수 있다 — [[DW-782]](sold 차단의 파일 쪽 누락)를 같은 파일에서 닫을 수 있는 근거다.

## Cross-Story Dependencies

이 에픽이 소유·흡수하는 장부 항목(같은 마이그레이션 묶음에서 처리한다):

| 항목 | 무엇 | 왜 여기냐 |
|---|---|---|
| [[DW-669]] | 정지 회원 쓰기가 아무 데서도 안 막힘 | 이 에픽의 본체 |
| [[DW-717]] | 위 구현이 Epic 15 UI-only와 충돌해 되돌려짐 | 사용자 결정 (b)안 = 이 스토리가 소유 |
| [[DW-721]] | `is_admin()`이 status를 안 봐서 정지된 관리자가 RPC로 거래를 되돌림 | "RLS만으로는 안 닫힌다"고 이 스토리를 콕 집어 지목 |
| [[DW-674]] | `listings` 소유권 RLS를 지키는 반복 검사가 저장소에 없음 | trigger가 "`listings` RLS를 다음에 건드리는 마이그레이션 스토리" = 이 스토리 |
| [[DW-682]] | `0028`의 buyer/seller 통과 분기가 도달 경로 0인데 남아 있음 | sprint-status Epic 17 주석이 "같은 마이그레이션 묶음에서" 지정 |
| [[DW-782]] | sold 쓰기 차단이 `listing_images` 행에만 있고 파일엔 없음 | 17-1이 건드릴 정책 파일이 정확히 그 파일 |
