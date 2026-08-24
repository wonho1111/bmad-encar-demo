-- 0033_remove_legacy_role_passthrough.sql — handle_new_user()의 buyer/seller 통과 분기 제거 (DW-682)
-- self-contained: 이 파일이 참조하는 것은 public.profiles(0001)뿐이다. handle_new_user() 자체는
--   0001에서 만들어져 0009·0028이 차례로 create or replace했다 — 이 파일이 세 번째 교체다.
--
-- 왜: 0028(Story 14.2)은 auth.users의 raw_user_meta_data.role이 정확히 'buyer'/'seller'면 그
--   값을 그대로 반영하는 하위호환 분기를 남겨 뒀다("Flutter 앱은 이 스토리에서 UI를 안 건드리므로
--   여전히 role metadata를 보낸다"는 전제). 그런데 Story 16-0에서 Flutter 가입 화면이 role 전송을
--   멈췄고(웹은 14.2에서 이미 멈춤), 그 결과 이 분기로 실제 들어오는 값은 0건이다(DW-682 실측 —
--   저장소 전체에서 role metadata를 보내는 가입 호출자가 없다). 도달 경로가 없는 분기를 남겨두면
--   다음 사람이 "레거시 클라이언트가 아직 이 값을 쓴다"고 오인해 지우기를 주저하게 만든다.
--
-- 무엇을: handle_new_user()를 create or replace로 교체한다(0001의 SECURITY DEFINER·트리거
--   배선·revoke execute는 함수 객체가 그대로 유지되므로 다시 손댈 필요가 없다 — 0028이 이미 같은
--   전제로 교체했다). metadata.role을 더 이상 읽지 않고 role은 항상 'user'로 배정한다. name
--   기록(0009)·on conflict do nothing은 그대로 유지한다.
--
-- 기존 행은 건드리지 않는다(forward-only, CLAUDE.md B3) — 이 마이그는 함수 정의만 바꾸고
-- profiles를 UPDATE하지 않는다. 이미 buyer/seller로 배정된 계정의 role은 그대로 남는다
-- (0029가 이미 기존 계정 role을 통일했다 — 이 마이그와는 별개 작업).

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, role, status, name)
  values (new.id, 'user', 'active', split_part(new.email, '@', 1))
  on conflict (id) do nothing;

  return new;
end;
$$;
