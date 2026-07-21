-- 01_accounts.sql — 로컬 스택 전용: 운영과 "같은 UUID"로 데모 계정 9개 만들기
--
-- 왜 이 파일이 따로 있나 (supabase/seed.sql과 다른 점):
--   seed.sql은 로컬용이 아니라 "데이터의 단일 출처"이며 gen_random_uuid()로 계정을 만든다.
--   반면 매물(listings)·채팅(chat_rooms 등)은 운영 데이터를 seller_id/buyer_id로 그대로 복사해 오므로,
--   그 외래키가 가리키는 계정도 운영과 "같은 id"로 로컬에 있어야 한다. 그래서 이 파일은 seed.sql의
--   레시피(auth.users + auth.identities 함께 생성 → 트리거가 만든 profiles를 role/name으로 UPDATE)를
--   그대로 쓰되, id를 고정값으로 지정한다.
--
-- 비밀번호: 이 파일 단독으로 실행하면 안 된다. scripts/seed-local.sh 가
--   `SET app.seed_password = '<supabase/.env.seed 의 SEED_PASSWORD>';` 를 앞에 붙여 실행한다.
--   직접 psql로 돌릴 경우도 같은 SET 문을 먼저 보내야 한다(같은 세션이어야 current_setting이 읽음).
--
-- 멱등성: auth.users.id 존재 여부로 판단 → 두 번 실행해도 중복 생성되지 않는다.

do $$
begin
  if coalesce(nullif(current_setting('app.seed_password', true), ''), '') = '' then
    raise exception '[seed-local] app.seed_password 세션 변수가 설정되지 않았습니다. '
      'scripts/seed-local.sh 를 통해 실행하세요.';
  end if;
end $$;

do $$
declare
  -- (id, email, role, name) — 운영 profiles 조회 결과와 일치(status는 전부 active, 트리거 기본값)
  v_accounts jsonb := '[
    {"id":"e3601b76-0370-47a7-9ec3-389d5578a50a","email":"admin@test.com","role":"admin","name":"admin"},
    {"id":"371eb469-dac2-412a-ac1e-71c35d69697b","email":"buyer@test.com","role":"buyer","name":"buyer"},
    {"id":"ea8eddf6-8bc2-44cf-a896-d0c87a9bf1a2","email":"buyer2@test.com","role":"buyer","name":"buyer2"},
    {"id":"2ea0a1fb-5cd5-4139-906f-4fd3622c5047","email":"buyer3@test.com","role":"buyer","name":"buyer3"},
    {"id":"e2c9bae0-7f06-42f7-9fd8-3d449d05206d","email":"dev94-probe@test.com","role":"seller","name":"dev94-probe"},
    {"id":"12dfba00-2544-45f4-8ffe-bdeb32229b97","email":"seller-seed@test.com","role":"seller","name":"seller-seed"},
    {"id":"0f937a74-48ee-4e3a-9e78-4a3d85645727","email":"seller-seed2@test.com","role":"seller","name":"seller-seed2"},
    {"id":"c19a85e7-6e23-432f-aa1c-efc57f1782af","email":"seller-seed3@test.com","role":"seller","name":"seller-seed3"},
    {"id":"748caac4-5e45-403c-b8ee-1f5ccc16b813","email":"seller@test.com","role":"seller","name":"seller"}
  ]'::jsonb;
  v_password text := current_setting('app.seed_password', true);
  v_acc      jsonb;
  v_id       uuid;
  v_email    text;
  v_role     text;
  v_name     text;
begin
  for v_acc in select * from jsonb_array_elements(v_accounts) loop
    v_id    := (v_acc ->> 'id')::uuid;
    v_email := v_acc ->> 'email';
    v_role  := v_acc ->> 'role';
    v_name  := v_acc ->> 'name';

    -- (멱등) 같은 id의 계정이 없을 때만 새로 생성한다.
    if not exists (select 1 from auth.users where id = v_id) then
      -- auth.users: 인증 계정 본체 (seed.sql의 admin 블록과 동일 레시피).
      insert into auth.users (
        id, instance_id, aud, role, email, encrypted_password,
        email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
        confirmation_token, recovery_token, email_change_token_new, email_change,
        created_at, updated_at
      ) values (
        v_id,
        '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated',
        v_email,
        extensions.crypt(v_password, extensions.gen_salt('bf')),  -- bcrypt 해시
        now(),
        '{"provider":"email","providers":["email"]}'::jsonb,
        '{}'::jsonb,
        '', '', '', '',
        now(), now()
      );

      -- auth.identities: 이메일 로그인 연결 (없으면 비밀번호 로그인 불가).
      insert into auth.identities (
        provider_id, user_id, identity_data, provider,
        last_sign_in_at, created_at, updated_at
      ) values (
        v_id::text, v_id,
        jsonb_build_object('sub', v_id::text, 'email', v_email),
        'email', now(), now(), now()
      );
    end if;

    -- 트리거(handle_new_user)가 만든 profiles(기본 buyer)를 목표 role/name으로 맞춘다(멱등).
    update public.profiles
       set role = v_role, name = v_name
     where id = v_id
       and (role <> v_role or name is distinct from v_name);

    -- (안전장치) "조용한 실패" 방지 — profiles 행이 없으면 즉시 멈춘다.
    if not exists (
      select 1 from public.profiles where id = v_id and role = v_role
    ) then
      raise exception '[seed-local] 계정 준비 실패: % (id=%) 의 % 프로필이 없습니다.', v_email, v_id, v_role;
    end if;
  end loop;

  raise notice '[seed-local] 계정 9개 준비 완료';
end $$;
