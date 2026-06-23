-- 0005_admin_policies.sql — FR22~25 기반: 관리자 전권 "교차" RLS 정책 모음 (Epic 6 토대)
-- 스키마 단일 출처(supabase/migrations/). 적용 순서: 0001 → 0002 → 0003 → 0004 → 0005(이 파일) → 0006.
--   (번호 갭 의도됨: 0005=admin 교차 정책 자리. 0003·0006 헤더가 이 예약을 명시.)
--
-- 왜 이 파일만 따로 모으나(architecture.md L199 원칙):
--   각 테이블의 "그 테이블만의" RLS(소유권·참여자)는 해당 테이블 마이그레이션(0001·0002·0003)에 동거시킨다.
--   그래야 0001→0006 순서로 적용해도 각 에픽 시점에 필요한 RLS가 이미 존재한다.
--   반면 "관리자 전권"은 여러 테이블을 가로지르는 **교차 관심사**라, 한곳(0005)에 모아 두면
--   관리자 정책을 한 파일에서 일관되게 추가·점검할 수 있다(Epic 6 회원·매물·거래·채팅 관리의 공통 토대).
--
-- 이 마이그레이션이 하는 일(관리자=public.is_admin()인 사용자에게만 추가 권한 부여):
--   1) profiles  — 관리자 UPDATE(회원 정지, FR22) + DELETE(회원 삭제, FR22)
--   2) listings  — 관리자 DELETE(부적절 매물 삭제, FR23)
--   3) chat_rooms / chat_messages — 관리자 SELECT(대화 열람, FR25) + DELETE(방·메시지 삭제, FR25)
--
-- 이미 존재해 여기서 다시 만들지 않는 것(중복 금지):
--   · profiles_select_admin (0001) · listings_select_admin (0002) — 관리자 전체 조회는 이미 있음.
--
-- ⚠️ 핵심 설계(반드시 이해):
--   · 관리자 판별은 **반드시 `public.is_admin()`**(0001의 SECURITY DEFINER 헬퍼)을 쓴다.
--     RLS 안에서 profiles를 직접 서브쿼리하면 "infinite recursion in policy"가 나기 때문(0001 주석 참조).
--   · 모든 정책은 `to authenticated` 한정(0001~0003 일관). is_admin() EXECUTE는 authenticated만 보유(0001 L90~91).
--   · 정책은 permissive(기본) → 기존 정책과 OR로 결합된다. 비관리자에겐 is_admin()=false라
--     **아무 행도 추가로 열리지 않는다** → 기존 소유권·참여자 정책 그대로(회귀 0).
--   · chat 테이블엔 ai_readonly용 가시성 정책(using true)을 **절대 추가하지 않는다**(0003 주석 — AI 검색은 chat 미조회).
--   · 멱등성: 각 create policy 앞에 drop policy if exists(0006 패턴) → 재적용 안전.

-- ── 1) profiles — 관리자 회원 관리(정지·삭제, FR22) ──────────────────
-- UPDATE: 관리자가 임의 회원의 status를 바꾼다(예: active→suspended).
--   using(기존 행)=관리자 여부, with check(변경 후 행)=관리자 여부 →
--   소유권(profiles_update_self 부재)과 무관하게 관리자가 **타인** 행을 수정한 결과도 통과한다.
drop policy if exists "profiles_update_admin" on public.profiles;
create policy "profiles_update_admin" on public.profiles
  for update to authenticated
  using (public.is_admin())
  with check (public.is_admin());

-- DELETE: 관리자가 임의 회원 프로필 행을 삭제(FR22 "계정이 제거된다"의 DB 측 허용).
--   ※ 실제 "계정(auth.users) 삭제"는 6-2에서 admin API/서비스롤로 다룰 수 있다.
--     본 스토리는 profiles 행 삭제 RLS 토대까지가 범위.
drop policy if exists "profiles_delete_admin" on public.profiles;
create policy "profiles_delete_admin" on public.profiles
  for delete to authenticated
  using (public.is_admin());

-- ── 2) listings — 관리자 매물 삭제(FR23) ─────────────────────────────
-- 조회는 listings_select_admin(0002)이 이미 담당 → SELECT는 추가하지 않는다.
-- UPDATE는 현재 관리 요구사항에 없어 추가하지 않는다(필요 시 후속 스토리에서).
drop policy if exists "listings_delete_admin" on public.listings;
create policy "listings_delete_admin" on public.listings
  for delete to authenticated
  using (public.is_admin());

-- ── 3) chat_rooms — 관리자 열람·삭제(FR25) ───────────────────────────
-- SELECT: 관리자는 당사자가 아니어도 모든 방을 본다(참여자 한정 정책과 OR 결합).
drop policy if exists "chat_rooms_select_admin" on public.chat_rooms;
create policy "chat_rooms_select_admin" on public.chat_rooms
  for select to authenticated
  using (public.is_admin());

-- DELETE: 관리자가 문제 방을 삭제(방 삭제 시 0003의 on delete cascade로 메시지도 함께 정리).
drop policy if exists "chat_rooms_delete_admin" on public.chat_rooms;
create policy "chat_rooms_delete_admin" on public.chat_rooms
  for delete to authenticated
  using (public.is_admin());

-- ── 4) chat_messages — 관리자 열람·삭제(FR25) ────────────────────────
-- chat_messages SELECT는 0003에서 방(chat_rooms)을 EXISTS 조인해 "당사자만" 보게 돼 있다.
-- 관리자는 당사자가 아닐 수 있으므로, messages에도 별도 admin SELECT 정책을 둬야 대화 전문을 본다.
drop policy if exists "chat_messages_select_admin" on public.chat_messages;
create policy "chat_messages_select_admin" on public.chat_messages
  for select to authenticated
  using (public.is_admin());

-- DELETE: 관리자가 개별 메시지를 삭제(FR25 "방과 메시지가 제거된다" 정합 — 방 단위 cascade 외 단건 삭제도 허용).
drop policy if exists "chat_messages_delete_admin" on public.chat_messages;
create policy "chat_messages_delete_admin" on public.chat_messages
  for delete to authenticated
  using (public.is_admin());
