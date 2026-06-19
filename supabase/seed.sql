-- seed.sql — 데모용 초기 데이터 단일 출처 (AR7)
-- 적용 순서: 마이그레이션(0001~) 적용 후 이 시드를 실행한다.
--
-- 이 파일이 채우는 데이터(에픽 진행에 따라 섹션이 늘어난다):
--   [Story 1.5] 관리자 계정 1개          ← 본 파일 현재 범위
--   [Story 2.5] 샘플 매물 (listings)      ← 추후 추가
--   [Story 4.2] 가이드 문서 코퍼스        ← 추후 추가
--
-- 적용 방법: 로컬 Supabase 스택이 없으므로(`supabase db reset` 사용 불가),
--   이 파일 내용을 그대로 호스티드 DB에 실행한다(Supabase MCP execute_sql 등).
--   이 파일은 "데이터의 단일 출처"로 저장소에 보존된다.
--
-- 멱등성: 두 번 실행해도 계정이 중복 생성되지 않도록 작성했다.

-- ════════════════════════════════════════════════════════════════════
-- [Story 1.5] 관리자 계정 시드 (FR4)
-- ════════════════════════════════════════════════════════════════════
-- 왜 SQL로 직접 만드나:
--   일반 가입(/signup)은 구매자/판매자만 허용하고, DB 트리거(handle_new_user)도
--   admin 메타를 buyer로 강제한다(=가입 경로로 admin 생성 차단, Story 1.4/AC3).
--   따라서 관리자는 "가입 흐름 밖"에서 만들어야 한다 — 그것이 이 시드의 역할이다.
--
-- 두 가지 필수 포인트:
--   1) auth.users + auth.identities 둘 다 있어야 이메일+비밀번호 로그인이 동작한다.
--      identities가 없으면 계정은 보여도 로그인이 실패한다(GoTrue가 identities를 참조).
--   2) auth.users insert 시 트리거가 profiles 행을 buyer로 만든다 →
--      insert 후 profiles.role을 'admin'으로 승격(UPDATE)해야 한다.
--
-- ⚠️ 데모 전용 자격증명이다. 운영 전 반드시 비밀번호를 교체할 것.
--     이메일: admin@test.com / 비밀번호: admin123
do $$
declare
  v_email    text := 'admin@test.com';
  v_password text := 'admin123';
  v_id       uuid;
begin
  -- (멱등) 같은 이메일 계정이 없을 때만 새로 생성한다.
  if not exists (select 1 from auth.users where email = v_email) then
    v_id := gen_random_uuid();

    -- auth.users: 인증 계정 본체.
    --   encrypted_password 는 bcrypt 해시여야 한다(평문이면 로그인 실패).
    --   email_confirmed_at 를 채워 이메일 확인 없이도 로그인 가능하게 한다.
    --   *_token / email_change 문자열 컬럼은 빈 문자열로 둔다
    --   (NULL이면 일부 GoTrue 버전이 로그인 시 스캔 에러를 낸다).
    insert into auth.users (
      id, instance_id, aud, role, email, encrypted_password,
      email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
      confirmation_token, recovery_token, email_change_token_new, email_change,
      created_at, updated_at
    ) values (
      v_id,
      '00000000-0000-0000-0000-000000000000',
      'authenticated',            -- aud (auth 시스템 값)
      'authenticated',            -- role (auth 시스템 롤 — profiles.role과 무관)
      v_email,
      extensions.crypt(v_password, extensions.gen_salt('bf')),  -- bcrypt 해시
      now(),
      '{"provider":"email","providers":["email"]}'::jsonb,
      '{}'::jsonb,
      '', '', '', '',
      now(), now()
    );

    -- auth.identities: 이메일 로그인 연결(없으면 비밀번호 로그인 불가).
    --   provider_id 는 최신 GoTrue에서 NOT NULL 필수 → 사용자 id를 text로 넣는다.
    insert into auth.identities (
      provider_id, user_id, identity_data, provider,
      last_sign_in_at, created_at, updated_at
    ) values (
      v_id::text,
      v_id,
      jsonb_build_object('sub', v_id::text, 'email', v_email),
      'email',
      now(), now(), now()
    );
  end if;

  -- 트리거가 만든 profiles(기본 buyer)를 admin으로 승격한다.
  --   계정이 이미 있던 경우(재실행)에도 admin 보장 → 멱등.
  update public.profiles
     set role = 'admin'
   where id = (select id from auth.users where email = v_email)
     and role <> 'admin';
end $$;
