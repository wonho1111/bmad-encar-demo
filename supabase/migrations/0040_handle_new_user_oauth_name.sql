-- 0040_handle_new_user_oauth_name.sql — handle_new_user()의 name을 카카오 등 이메일 없는
-- OAuth 가입에도 채워지게 교체 (Story 18.1 AC2)
-- self-contained: 이 파일이 참조하는 것은 public.profiles(0001)뿐이다. handle_new_user() 자체는
--   0001에서 만들어져 0009·0028·0033이 차례로 create or replace했다 — 이 파일이 네 번째 교체다.
--
-- 왜: 0033까지의 name 규칙은 `split_part(new.email, '@', 1)` 하나뿐이었다. 카카오 로그인은
--   이메일 동의항목이 "권한 없음"인 기본 앱으로는 이메일을 아예 안 주므로(스토리 Dev Notes
--   2026-09-29 실측), new.email이 NULL이면 split_part도 NULL이 되어 profiles.name이 빈 채로
--   남는다(AC2 위반). 카카오는 대신 raw_user_meta_data에 닉네임을 실어 보낸다 — Supabase Auth의
--   Kakao provider(internal/api/provider/kakao.go, 2026-09-29 소스 확인)가 카카오 API의
--   kakao_account.profile.nickname 값을 Claims.Name·FullName에 그대로 채우므로, 실제 저장되는
--   metadata 키는 raw_user_meta_data->>'name'(그리고 ->>'full_name')이다. ->>'nickname' 키
--   자체는 카카오 경로에서는 채워지지 않지만, 다른 OAuth 공급자가 그 키를 쓸 가능성에 대비해
--   순서상 다음 폴백으로 남겨둔다(A2: 있어도 해 되지 않는 값싼 대비, 없어도 동작은 그대로).
--
-- 무엇을: handle_new_user()를 create or replace로 교체한다(0001의 SECURITY DEFINER·트리거
--   배선·revoke execute는 함수 객체가 그대로 유지되므로 다시 손댈 필요가 없다). name을
--   이메일 앞부분 → metadata.name → metadata.nickname → metadata.full_name → '회원' 순
--   coalesce로 바꾼다. role='user'·status='active' 배정과 on conflict do nothing은 그대로 유지한다.
--
-- 기존 행은 건드리지 않는다(forward-only, CLAUDE.md B3) — 이 마이그는 함수 정의만 바꾸고
-- profiles를 UPDATE하지 않는다. 이미 가입된 계정의 name은 그대로 남는다.

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, role, status, name)
  values (
    new.id,
    'user',
    'active',
    coalesce(
      nullif(split_part(new.email, '@', 1), ''),
      nullif(new.raw_user_meta_data->>'name', ''),
      nullif(new.raw_user_meta_data->>'nickname', ''),
      nullif(new.raw_user_meta_data->>'full_name', ''),
      '회원'
    )
  )
  on conflict (id) do nothing;

  return new;
end;
$$;
