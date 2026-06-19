-- seed.sql — 데모용 초기 데이터 단일 출처 (AR7)
-- 적용 순서: 마이그레이션(0001~) 적용 후 이 시드를 실행한다.
--
-- 이 파일이 채우는 데이터(에픽 진행에 따라 섹션이 늘어난다):
--   [Story 1.5] 관리자 계정 1개          ← admin 섹션
--   [Story 2.5] 샘플 매물 (listings)      ← 시드 전용 판매자 + 매물 39건
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

  -- (안전장치) "조용한 실패" 방지.
  --   위 update는 트리거가 만든 profiles 행이 있다고 전제한다. 만약 그 행이 없으면
  --   (트리거 비활성/외부에서 만들어진 고아 계정 등) update가 0행에 매칭되고 에러 없이
  --   끝나, admin 권한이 안 붙은 반쪽 계정이 조용히 남을 수 있다. → 결과를 직접 확인해
  --   admin이 아니면 예외를 던져 멈춘다(실패를 묻지 않고 즉시 드러냄).
  if not exists (
    select 1 from public.profiles p
    join auth.users u on u.id = p.id
    where u.email = v_email and p.role = 'admin'
  ) then
    raise exception '[seed] admin 시드 실패: % 의 admin 프로필이 없습니다 '
      '(트리거가 profiles 행을 만들었는지, 마이그레이션 0001이 적용됐는지 확인).', v_email;
  end if;

  raise notice '[seed] admin 계정 준비 완료: %', v_email;
end $$;

-- ════════════════════════════════════════════════════════════════════
-- [Story 2.5] 샘플 매물 시드 (AR7)
-- ════════════════════════════════════════════════════════════════════
-- 무엇을 / 왜:
--   탐색(Epic 3)·AI 검색(Epic 4) 시연을 위해 텍스트가 충실한 샘플 매물 39건을 넣는다.
--   값은 0002_listings.sql의 CHECK 목록(=UI 드롭다운·Text-to-SQL 허용값·constants.ts LISTING_OPTIONS)과
--   바이트 단위로 일치해야 한다(drift 시 INSERT가 CHECK에 걸린다).
--
-- 두 단계로 구성:
--   1) 시드 전용 판매자 계정(seller-seed@test.com) — 매물 seller_id가 가리킬 유효한 판매자.
--      가입 흐름 밖에서 만들므로 admin 시드(위)와 같은 auth.users+auth.identities 패턴을 쓴다.
--      단 admin과 달리 role은 'seller'로 승격(트리거가 만든 buyer를 UPDATE).
--   2) 그 판매자 명의로 매물 39건 INSERT.
--
-- 멱등성(중요): 재실행 시 매물이 누적되지 않도록, "시드 전용 판매자 소유 매물만 삭제 후 재삽입"한다.
--   → admin 시드·일반 seller@test.com 매물·다른 잔여 데이터는 건드리지 않는다.
--   (id가 gen_random_uuid() 기본값이라 ON CONFLICT 키가 없어 '삭제 후 삽입'이 가장 단순·안전.)
--
-- embedding: 전부 NULL로 둔다(컬럼 생략 = 기본 NULL). Epic 4(Story 4.2)에서 일괄 적재(backfill).
--   description·options 텍스트가 그때 코퍼스①(임베딩 대상)이 되므로 자연스러운 한국어로 충실히 작성한다.
--
-- ⚠️ 데모 전용 자격증명: seller-seed@test.com / seller123 (운영 전 교체).
do $$
declare
  v_email     text := 'seller-seed@test.com';
  v_password  text := 'seller123';
  v_seller_id uuid;
begin
  -- ── 1) 시드 전용 판매자 계정 (멱등) ──────────────────────────────
  if not exists (select 1 from auth.users where email = v_email) then
    v_seller_id := gen_random_uuid();

    insert into auth.users (
      id, instance_id, aud, role, email, encrypted_password,
      email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
      confirmation_token, recovery_token, email_change_token_new, email_change,
      created_at, updated_at
    ) values (
      v_seller_id,
      '00000000-0000-0000-0000-000000000000',
      'authenticated', 'authenticated',
      v_email,
      extensions.crypt(v_password, extensions.gen_salt('bf')),  -- bcrypt 해시
      now(),
      '{"provider":"email","providers":["email"]}'::jsonb,
      '{"role":"seller"}'::jsonb,   -- 가입 메타: 트리거(handle_new_user)가 이 값으로 profiles를 seller로 생성 → 아래 UPDATE는 대개 no-op(안전망). admin 블록은 메타 없이 buyer로 생성된 뒤 UPDATE로 승격하는 점과 다름.
      '', '', '', '',
      now(), now()
    );

    insert into auth.identities (
      provider_id, user_id, identity_data, provider,
      last_sign_in_at, created_at, updated_at
    ) values (
      v_seller_id::text, v_seller_id,
      jsonb_build_object('sub', v_seller_id::text, 'email', v_email),
      'email', now(), now(), now()
    );
  end if;

  -- 판매자 id 확정(신규/기존 공통). 트리거가 만든 profiles를 seller로 승격(멱등).
  select id into v_seller_id from auth.users where email = v_email;
  update public.profiles set role = 'seller'
   where id = v_seller_id and role <> 'seller';

  -- (안전장치) seller 프로필이 실제로 존재하는지 확인 — 없으면 조용한 실패 대신 즉시 멈춤.
  if not exists (
    select 1 from public.profiles where id = v_seller_id and role = 'seller'
  ) then
    raise exception '[seed] 시드 판매자 준비 실패: % 의 seller 프로필이 없습니다 '
      '(트리거/마이그레이션 0001 확인).', v_email;
  end if;

  -- ── 2) 매물 멱등 정리: 이 시드 판매자 소유 매물만 삭제 ───────────
  --     (다른 계정 매물·잔여 테스트 데이터는 보존)
  delete from public.listings where seller_id = v_seller_id;

  -- ── 3) 샘플 매물 39건 INSERT ─────────────────────────────────────
  --   고정 6필드 값 = CHECK 허용값(바이트 일치). embedding 생략(=NULL).
  --   분포: 차종 11종, 연료 5종 전부, 지역 다수, 가격 250만~2.2억 고루. 대부분 on_sale, 일부 sold.
  insert into public.listings
    (seller_id, status, manufacturer, model, body_type, year, price, mileage,
     color, fuel, transmission, displacement, seats, region, accident_free, options, description)
  values
    -- 국산 가솔린·하이브리드 세단/준중형 (대중 가격대)
    (v_seller_id, 'on_sale', '현대', '아반떼 CN7', '준중형차', 2021, 17800000, 38000,
     '흰색', '가솔린', '자동', 1598, 5, '서울', true,
     array['후방카메라','스마트키','크루즈컨트롤','애플카플레이'],
     '2021년식 아반떼 CN7 가솔린 모델입니다. 주행거리 3만8천km로 관리가 잘 되어 있고 무사고 차량입니다. 출퇴근용으로 적합하며 연비가 우수합니다. 정기점검 이력 보유.'),
    (v_seller_id, 'on_sale', '기아', 'K5 DL3', '중형차', 2022, 24500000, 21000,
     '검정', '하이브리드', '자동', 1598, 5, '경기', true,
     array['파노라마선루프','통풍시트','열선시트','어라운드뷰','내비게이션'],
     '2022년식 K5 하이브리드 풀옵션 차량입니다. 통풍·열선시트와 파노라마 선루프가 적용되어 사계절 쾌적합니다. 하이브리드라 유지비가 적게 들고 주행거리 2만1천km로 신차급 컨디션입니다.'),
    (v_seller_id, 'on_sale', '현대', '쏘나타 DN8', '중형차', 2020, 19900000, 56000,
     '회색', '가솔린', '자동', 1999, 5, '인천', true,
     array['스마트크루즈','차선유지보조','후측방경고','무선충전'],
     '2020년식 쏘나타 DN8 가솔린입니다. 차선유지보조와 스마트크루즈 등 주행보조 기능이 충실합니다. 5만6천km 주행, 무사고이며 실내 흡연 이력 없습니다.'),
    (v_seller_id, 'on_sale', '기아', '모닝 JA', '경차', 2019, 7200000, 49000,
     '흰색', '가솔린', '자동', 998, 5, '부산', true,
     array['후방센서','블루투스','열선시트'],
     '2019년식 모닝입니다. 경차라 세금·보험·연비 모두 부담이 적어 첫차로 좋습니다. 4만9천km 주행, 잔고장 없이 잘 타던 차량입니다.'),
    (v_seller_id, 'on_sale', '쉐보레', '스파크', '경차', 2018, 5800000, 67000,
     '파랑', '가솔린', '수동', 999, 5, '대구', false,
     array['블루투스','후방센서'],
     '2018년식 스파크 수동 모델입니다. 가벼운 접촉 사고 이력이 있어 가격을 낮췄습니다(수리 완료). 수동 변속기를 선호하시는 분께 추천하며 연비가 매우 좋습니다.'),
    -- 국산 SUV/RV (가솔린·디젤·하이브리드)
    (v_seller_id, 'on_sale', '현대', '투싼 NX4', 'SUV', 2022, 28900000, 24000,
     '은색', '디젤', '자동', 1598, 5, '경기', true,
     array['파노라마선루프','전동트렁크','어라운드뷰','후측방모니터','내비게이션'],
     '2022년식 투싼 NX4 디젤 4WD입니다. 넓은 실내와 큰 트렁크로 캠핑·가족 나들이에 좋습니다. 2만4천km, 무사고이며 디젤 특유의 힘있는 주행감을 느낄 수 있습니다.'),
    (v_seller_id, 'on_sale', '기아', '쏘렌토 MQ4', 'SUV', 2021, 33500000, 41000,
     '검정', '디젤', '자동', 2151, 7, '충남', true,
     array['7인승','통풍시트','HUD','스마트크루즈','파노라마선루프'],
     '2021년식 쏘렌토 7인승 디젤입니다. 3열 시트로 대가족에게 적합하며 HUD와 통풍시트 등 편의사양이 풍부합니다. 4만1천km 주행, 무사고 차량입니다.'),
    (v_seller_id, 'on_sale', '현대', '싼타페 TM', 'SUV', 2020, 26700000, 62000,
     '흰색', '디젤', '자동', 2199, 7, '강원', true,
     array['7인승','전동트렁크','후방카메라','열선스티어링'],
     '2020년식 싼타페 디젤 7인승입니다. 강원 지역에서 운행했고 사륜구동이라 눈길 주행에 강합니다. 6만2천km, 무사고이며 정비 이력이 투명합니다.'),
    (v_seller_id, 'on_sale', '기아', '카니발 KA4', 'RV', 2022, 37800000, 33000,
     '회색', '디젤', '자동', 2151, 9, '경남', true,
     array['9인승','뒷좌석모니터','전동슬라이딩도어','어라운드뷰'],
     '2022년식 카니발 9인승 디젤입니다. 패밀리카·법인 의전용으로 최고의 공간을 제공합니다. 전동 슬라이딩 도어와 뒷좌석 모니터 장착. 3만3천km 무사고.'),
    (v_seller_id, 'on_sale', '현대', '팰리세이드', '대형차', 2021, 39900000, 45000,
     '검정', '디젤', '자동', 2199, 8, '서울', true,
     array['8인승','나파가죽시트','HUD','후석알림','파노라마선루프'],
     '2021년식 팰리세이드 8인승 디젤 풀옵션입니다. 대형 SUV의 웅장한 존재감과 고급스러운 나파가죽 인테리어가 돋보입니다. 4만5천km, 무사고 1인 신조 차량입니다.'),
    -- LPG / 화물 / 승합
    (v_seller_id, 'on_sale', '르노코리아', 'SM6', '중형차', 2019, 13500000, 78000,
     '은색', 'LPG', '자동', 1998, 5, '대전', true,
     array['가죽시트','내비게이션','후방카메라'],
     '2019년식 SM6 LPG 모델입니다. LPG라 연료비가 매우 저렴해 운행거리가 많은 분께 적합합니다. 7만8천km 주행, 무사고이며 가죽시트 적용 차량입니다.'),
    (v_seller_id, 'on_sale', '현대', '포터2', '화물차', 2020, 16800000, 89000,
     '흰색', '디젤', '수동', 2497, 3, '경기', true,
     array['에어컨','파워스티어링'],
     '2020년식 포터2 1톤 디젤 화물차입니다. 소상공인 운반·배송용으로 많이 찾는 모델입니다. 8만9천km, 엔진·미션 상태 양호하며 화물 적재함 깨끗합니다.'),
    (v_seller_id, 'on_sale', '기아', '봉고3', '화물차', 2019, 14500000, 102000,
     '흰색', 'LPG', '수동', 2497, 3, '충북', true,
     array['에어컨','라디오'],
     '2019년식 봉고3 LPG 1톤 트럭입니다. LPG라 유류비 절감 효과가 큽니다. 10만2천km로 주행거리는 있으나 정비를 꾸준히 해 컨디션이 좋습니다.'),
    (v_seller_id, 'on_sale', '현대', '스타리아', '승합차', 2022, 35000000, 28000,
     '회색', '디젤', '자동', 2199, 11, '인천', true,
     array['11인승','전동슬라이딩도어','후방카메라','크루즈컨트롤'],
     '2022년식 스타리아 11인승 디젤입니다. 통근버스·단체 이동용으로 넓고 편안합니다. 2만8천km, 무사고이며 실내 매우 깨끗합니다.'),
    (v_seller_id, 'on_sale', '기아', '레이', '경승합차', 2021, 11900000, 35000,
     '흰색', '가솔린', '자동', 998, 5, '광주', true,
     array['슬라이딩도어','후방카메라','블루투스'],
     '2021년식 레이입니다. 박스형 디자인으로 실내 공간이 넓고 슬라이딩 도어로 승하차가 편합니다. 3만5천km, 무사고이며 도심 운행에 최적입니다.'),
    -- 전기차 (전기·displacement 0)
    (v_seller_id, 'on_sale', '테슬라', '모델3', '준중형차', 2022, 42000000, 31000,
     '흰색', '전기', '자동', 0, 5, '서울', true,
     array['오토파일럿','파노라마글래스루프','무선업데이트','프리미엄오디오'],
     '2022년식 테슬라 모델3 롱레인지입니다. 1회 충전 주행거리가 길고 오토파일럿이 적용되어 장거리 운전이 편합니다. 3만1천km, 무사고이며 배터리 상태 양호합니다.'),
    (v_seller_id, 'on_sale', '현대', '아이오닉5', 'SUV', 2022, 39500000, 26000,
     '회색', '전기', '자동', 0, 5, '경기', true,
     array['V2L','증강현실HUD','릴렉션시트','초고속충전'],
     '2022년식 아이오닉5입니다. 800V 초고속 충전으로 18분 만에 80% 충전 가능합니다. V2L로 캠핑 시 전자기기 사용이 편리합니다. 2만6천km 무사고.'),
    (v_seller_id, 'on_sale', '기아', 'EV6', 'SUV', 2023, 44900000, 14000,
     '검정', '전기', '자동', 0, 5, '부산', true,
     array['증강현실HUD','메리디안사운드','원격주차','초고속충전'],
     '2023년식 EV6 GT라인입니다. 1만4천km로 거의 신차 상태이며 디자인과 주행 성능이 뛰어납니다. 무사고, 초고속 충전 지원으로 일상 사용이 매우 편합니다.'),
    (v_seller_id, 'on_sale', '기아', '니로 EV', '소형차', 2021, 27800000, 47000,
     '파랑', '전기', '자동', 0, 5, '대전', true,
     array['스마트크루즈','후방카메라','열선시트'],
     '2021년식 니로 EV입니다. 준중형급 실내공간에 전기차의 경제성을 갖춰 패밀리 첫 전기차로 인기입니다. 4만7천km, 무사고 차량입니다.'),
    -- 수입 가솔린/디젤 세단·SUV
    (v_seller_id, 'on_sale', 'BMW', '520i', '중형차', 2020, 38500000, 52000,
     '검정', '가솔린', '자동', 1998, 5, '서울', true,
     array['나파가죽','HUD','하만카돈','어댑티브크루즈','파노라마선루프'],
     '2020년식 BMW 520i G30입니다. 다이나믹한 주행감과 고급스러운 인테리어를 자랑합니다. 5만2천km, 무사고이며 BMW 공식 서비스센터 정비 이력 보유.'),
    (v_seller_id, 'on_sale', '벤츠', 'E250', '중형차', 2019, 36900000, 64000,
     '은색', '가솔린', '자동', 1991, 5, '경기', true,
     array['부메스터사운드','앰비언트라이트','파노라마선루프','메모리시트'],
     '2019년식 벤츠 E250 W213입니다. 앰비언트 라이트와 부메스터 사운드로 고급스러운 분위기를 연출합니다. 6만4천km, 무사고이며 실내 컨디션 우수합니다.'),
    (v_seller_id, 'on_sale', '아우디', 'A6 40 TDI', '대형차', 2020, 41500000, 49000,
     '회색', '디젤', '자동', 1968, 5, '인천', true,
     array['뱅앤올룹슨','버추얼콕핏','매트릭스LED','어댑티브크루즈'],
     '2020년식 아우디 A6 40 TDI입니다. 디젤이라 연비가 좋고 정숙성이 뛰어납니다. 버추얼 콕핏과 매트릭스 LED가 적용된 차량입니다. 4만9천km 무사고.'),
    (v_seller_id, 'on_sale', '폭스바겐', '티구안', 'SUV', 2019, 27500000, 71000,
     '흰색', '디젤', '자동', 1968, 5, '충남', true,
     array['파노라마선루프','LED헤드램프','후방카메라','하이패스'],
     '2019년식 폭스바겐 티구안 디젤입니다. 단단한 하체와 안정적인 고속 주행이 장점입니다. 7만1천km, 무사고이며 합리적인 가격에 내놓습니다.'),
    (v_seller_id, 'on_sale', '아우디', 'Q5', 'SUV', 2021, 48900000, 38000,
     '검정', '가솔린', '자동', 1984, 5, '서울', true,
     array['콰트로','버추얼콕핏','뱅앤올룹슨','파노라마선루프','전동트렁크'],
     '2021년식 아우디 Q5 콰트로입니다. 사륜구동으로 어떤 노면에서도 안정적이며 프리미엄 SUV의 품격을 갖췄습니다. 3만8천km, 무사고 1인 차량입니다.'),
    (v_seller_id, 'on_sale', 'BMW', 'X3', 'SUV', 2020, 45500000, 55000,
     '흰색', '디젤', '자동', 1995, 5, '경기', true,
     array['HUD','하만카돈','어댑티브크루즈','파노라마선루프','전동트렁크'],
     '2020년식 BMW X3 20d xDrive입니다. 디젤 사륜으로 힘과 효율을 모두 잡았습니다. 5만5천km, 무사고이며 정비 이력 투명한 차량입니다.'),
    -- 수입 하이브리드/고급
    (v_seller_id, 'on_sale', '렉서스', 'ES300h', '중형차', 2021, 43500000, 36000,
     '은색', '하이브리드', '자동', 2487, 5, '대구', true,
     array['마크레빈슨','통풍시트','HUD','어댑티브크루즈'],
     '2021년식 렉서스 ES300h 하이브리드입니다. 정숙성과 연비가 탁월하며 마크레빈슨 사운드가 일품입니다. 3만6천km, 무사고이며 잔고장 없는 차량입니다.'),
    (v_seller_id, 'on_sale', '토요타', '캠리 하이브리드', '중형차', 2020, 28900000, 58000,
     '검정', '하이브리드', '자동', 2487, 5, '부산', true,
     array['JBL사운드','어댑티브크루즈','후방카메라','무선충전'],
     '2020년식 토요타 캠리 하이브리드입니다. 내구성 좋기로 유명한 모델로 유지비가 적게 듭니다. 5만8천km, 무사고이며 패밀리 세단으로 추천합니다.'),
    (v_seller_id, 'on_sale', '혼다', 'CR-V', 'SUV', 2019, 25500000, 69000,
     '회색', '가솔린', '자동', 1497, 5, '광주', true,
     array['혼다센싱','전동트렁크','후방카메라','열선시트'],
     '2019년식 혼다 CR-V 터보입니다. 실용적인 공간과 혼다센싱 안전사양을 갖췄습니다. 6만9천km, 무사고이며 잔고장 적은 일본차의 장점이 그대로입니다.'),
    (v_seller_id, 'on_sale', '제네시스', 'G80 RG3', '대형차', 2021, 52900000, 32000,
     '검정', '가솔린', '자동', 2497, 5, '서울', true,
     array['렉시콘사운드','나파가죽','HUD','후석엔터테인먼트','파노라마선루프'],
     '2021년식 제네시스 G80입니다. 국산 플래그십 세단으로 정숙성과 고급감이 수입차에 뒤지지 않습니다. 3만2천km, 무사고 1인 신조이며 풀옵션 차량입니다.'),
    (v_seller_id, 'on_sale', '제네시스', 'GV70', 'SUV', 2022, 54500000, 25000,
     '흰색', '디젤', '자동', 2199, 5, '경기', true,
     array['렉시콘사운드','나파가죽','전동트렁크','어라운드뷰','HUD'],
     '2022년식 제네시스 GV70 디젤입니다. 스포티한 디자인과 고급스러운 마감이 돋보이는 프리미엄 SUV입니다. 2만5천km, 무사고이며 신차급 컨디션입니다.'),
    -- 스포츠카 / 고가
    (v_seller_id, 'on_sale', 'BMW', 'M4', '스포츠카', 2021, 89000000, 18000,
     '파랑', '가솔린', '자동', 2993, 4, '서울', true,
     array['M스포츠패키지','카본인테리어','하만카돈','M서스펜션'],
     '2021년식 BMW M4 컴페티션입니다. 510마력의 강력한 퍼포먼스를 자랑하는 고성능 쿠페입니다. 1만8천km, 무사고이며 카본 인테리어가 적용된 차량입니다.'),
    (v_seller_id, 'on_sale', '테슬라', '모델S', '대형차', 2022, 98000000, 22000,
     '검정', '전기', '자동', 0, 5, '경기', true,
     array['오토파일럿','요크스티어링','프리미엄오디오','초고속충전'],
     '2022년식 테슬라 모델S 롱레인지입니다. 압도적인 가속력과 긴 주행거리를 갖춘 플래그십 전기 세단입니다. 2만2천km, 무사고이며 배터리 컨디션 최상입니다.'),
    -- 저가/오래된 매물 (가격대 다양화)
    (v_seller_id, 'on_sale', '현대', '아반떼 MD', '준중형차', 2014, 6500000, 132000,
     '흰색', '가솔린', '자동', 1591, 5, '전북', true,
     array['후방센서','블루투스'],
     '2014년식 아반떼 MD입니다. 주행거리는 많지만 가격이 저렴해 입문용·세컨카로 적합합니다. 큰 사고 없이 관리된 차량으로 소모품 교체 이력 보유.'),
    (v_seller_id, 'on_sale', '기아', '쏘울', 'RV', 2015, 7800000, 118000,
     '빨강', '가솔린', '자동', 1591, 5, '전남', false,
     array['후방카메라','블루투스','열선시트'],
     '2015년식 쏘울입니다. 개성있는 디자인과 넓은 실내가 매력입니다. 경미한 사고 이력이 있으나 수리 완료했고 주행에 문제 없습니다. 가성비 좋은 매물입니다.'),
    (v_seller_id, 'on_sale', '쉐보레', '말리부', '중형차', 2017, 11200000, 95000,
     '은색', '가솔린', '자동', 1490, 5, '경북', true,
     array['후방카메라','애플카플레이','크루즈컨트롤'],
     '2017년식 말리부 1.5 터보입니다. 넓은 실내와 부드러운 승차감이 장점입니다. 9만5천km, 무사고이며 합리적인 가격대의 중형 세단을 찾는 분께 추천합니다.'),
    (v_seller_id, 'on_sale', 'KG모빌리티', '티볼리', 'SUV', 2018, 10500000, 87000,
     '갈색', '가솔린', '자동', 1597, 5, '울산', true,
     array['후방카메라','스마트키','열선시트'],
     '2018년식 티볼리(구 쌍용)입니다. 소형 SUV로 도심 주행과 주차가 편리합니다. 8만7천km, 무사고이며 첫차나 세컨카로 부담 없는 가격입니다.'),
    (v_seller_id, 'on_sale', '르노코리아', 'QM6', 'SUV', 2019, 16500000, 73000,
     '녹색', 'LPG', '자동', 1998, 5, '제주', true,
     array['파노라마선루프','후방카메라','가죽시트'],
     '2019년식 QM6 LPG입니다. LPG SUV라 연료비 부담이 적고 제주 지역에서 운행하던 차량입니다. 7만3천km, 무사고이며 파노라마 선루프가 적용됐습니다.'),
    -- 판매완료(sold) 샘플 — 비노출 규칙(Epic 3) 시연용 소수 포함
    (v_seller_id, 'sold', '현대', '그랜저 IG', '대형차', 2019, 21500000, 88000,
     '검정', '가솔린', '자동', 2999, 5, '서울', true,
     array['통풍시트','HUD','어라운드뷰','내비게이션'],
     '2019년식 그랜저 IG 3.0입니다. 정숙하고 안락한 승차감의 대형 세단입니다. 8만8천km, 무사고 차량이었으며 거래가 완료된 매물입니다.'),
    (v_seller_id, 'sold', '기아', '스포티지 NQ5', 'SUV', 2022, 29900000, 19000,
     '흰색', '가솔린', '자동', 1598, 5, '경기', true,
     array['파노라마선루프','어라운드뷰','통풍시트','스마트크루즈'],
     '2022년식 스포티지 NQ5 가솔린입니다. 세련된 디자인과 넓은 실내가 인기인 모델입니다. 1만9천km 신차급이었으며 거래 완료되었습니다.')
  ;

  raise notice '[seed] 샘플 매물 준비 완료: 판매자 % / 매물 %건',
    v_email, (select count(*) from public.listings where seller_id = v_seller_id);
end $$;
