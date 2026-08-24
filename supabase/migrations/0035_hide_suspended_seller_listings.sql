-- 0035_hide_suspended_seller_listings.sql — 정지된 판매자의 매물을 구매자·비로그인·AI 응답
-- 어느 조회 경로에서도 숨긴다 (Story 17.4, DW-804(a))
-- self-contained: 이 파일이 참조하는 것은 전부 자기보다 앞 번호다 — public.profiles(0001)·
--   public.listings(0002·0006·0011)·public.listing_images(0012)·public.get_seller_public_summary
--   (0019). 뒤 번호를 가정하지 않는다.
--
-- ── 이 파일이 뒤집는 것 ──────────────────────────────────────────────────────────────────────
-- 17.1의 불변식 후반부는 "정지된 계정의 읽기는 아무것도 줄어들지 않는다"였고, 그 문장의 근거로
-- listings_select_*를 하나도 건드리지 않았다. 이 스토리는 사용자 지시(2026-08-11 Discord,
-- DW-804(a) — "숨겨야돼")로 그 문장을 폐기한다: 매물은 계속 노출되는데 판매자는 17.1이 발신을
-- 막아 영원히 답할 수 없어, 구매자가 "무시당했다"고 읽는 문제(DW-804) 때문이다.
-- 새 불변식(이 파일 전체가 지키는 한 문장): "profiles.status='suspended'인 판매자의 매물은
-- 구매자·비로그인·AI 응답 어느 조회 경로에서도 노출되지 않는다. 단 판매자 본인과 관리자에게는
-- 그대로 보인다." 뒷문장이 앞문장만큼 중요하다 — 본인이 못 보면 정지 해제 후 복구가 불가능하고,
-- 관리자가 못 보면 관리 콘솔이 빈 화면이 된다. 그래서 이 파일은 listings_select_own·
-- listings_select_admin·listing_images_select_own·listing_images_select_admin 어느 것도
-- 건드리지 않는다.
--
-- ── 왜 SECURITY DEFINER 판정 함수인가 (실측으로 확정, 추론이 아니다) ──────────────────────────
-- "이 매물의 판매자가 활성인가"를 정책 안에서 순진하게
--   exists (select 1 from public.profiles where id = listings.seller_id and status = 'active')
-- 로 물으면, 그 서브쿼리는 **호출자 권한**으로 평가되어 profiles RLS를 그대로 탄다. profiles의
-- SELECT 정책은 profiles_select_self(본인만)·profiles_select_admin(관리자만) 둘뿐이고 anon
-- 대상 정책은 0건이다 — 그래서 "남의" profiles 행(=매물 판매자)을 읽으려는 이 서브쿼리는 항상
-- 0행을 보고 exists가 항상 거짓이 된다. 결과: 비로그인은 모든 매물이, 로그인 구매자는 자기 것
-- 말고 전부가 사라진다. 그리고 "정지 판매자 매물이 안 보인다"만 단언하는 검사는 이 상태에서도
-- green이다(활성 판매자 매물도 같이 사라졌다는 걸 놓친다) — 그래서 이 스토리의 모든 검사는
-- 긍정 대조군을 짝으로 둔다(아래 5절 + api/tests/integration/test_suspended_seller_hidden_real_db.py).
--
-- 2026-08-12 로컬 55322 실측(트랜잭션+rollback으로 확인, 흔적 없음): 활성 판매자의 on_sale
-- 매물 1건을 심고 위 인라인 서브쿼리로 anon 정책을 바꾼 뒤 anon으로 `select count(*)`를
-- 실행하면 결과가 **0**이다(활성 판매자 매물인데도 안 보인다 — 예측대로 재현).
--
-- 해법은 이 레포에 이미 있는 패턴이다: is_admin()(0001)·is_admin_active()(0032)와 같은 이유로
-- SECURITY DEFINER 함수를 만든다 — 정의자(소유자) 권한으로 실행되면 소유자에게는 RLS가 애초에
-- 안 걸리므로 profiles를 "누구의" 행이든 읽을 수 있다.
--
-- ── 1) is_seller_active(uuid) — SECURITY DEFINER 판정 함수 ───────────────────────────────────
create or replace function public.is_seller_active(p_seller_id uuid)
returns boolean
language sql
security definer
set search_path = ''
stable
as $$
  select exists (
    select 1 from public.profiles
    where id = p_seller_id and status = 'active'
  );
$$;

comment on function public.is_seller_active(uuid) is
  '판매자(profiles.id=p_seller_id)가 활성(status=''active'')인가 — Story 17.4, DW-804(a).
   is_admin()(0001)·is_admin_active()(0032)와 같은 이유로 SECURITY DEFINER다: 이 함수를 참조하는
   listings_select_on_sale/_anon·listing_images_select_on_sale/_anon·listings_ai_readonly_select
   정책은 "남의"(매물 판매자의) profiles 행을 물어야 하는데, 인라인 서브쿼리는 호출자 권한으로
   평가돼 profiles RLS(본인·관리자만 SELECT, anon 대상 정책 0건)를 그대로 타서 exists가 항상
   거짓이 되고 결과적으로 전체 매물이 사라진다(2026-08-12 로컬 실측으로 확정 — 위 파일 헤더
   주석 참조). 소비처: listings_select_on_sale/_anon(0035)·listings_ai_readonly_select(0035)·
   listing_images는 listings에 조인해 간접 적용(자동 상속, 아래 3절 실측)·
   get_seller_public_summary(0019, 함수 안에서 직접 호출).
   판매자 행이 없는 경우(profiles가 없는 seller_id)는 exists가 거짓 → false(매물 숨김)다.
   listings.seller_id는 `references public.profiles(id) on delete cascade`(0002)라 판매자
   profiles가 없는 매물은 애초에 존재할 수 없으므로(FK가 보장) 이 분기는 도달 불가능이지만,
   방어적으로 "판정 불가 = 숨김" 쪽으로 fail-closed하는 것이 이 함수의 성격과 맞다.';

-- public 스키마 함수는 PostgREST가 RPC로 자동 노출한다 — is_admin()·is_admin_active()와 동일하게
-- 회수한다. 이 함수를 실제로 부르는 롤에만 execute를 준다: authenticated(listings_select_on_sale)·
-- anon(listings_select_on_sale_anon)·ai_readonly(listings_ai_readonly_select, 아래 4절 — AI 3경로를
-- 이 한 자리에서 닫기로 한 선택). get_seller_public_summary(0019)는 SECURITY DEFINER로 postgres
-- 소유자 권한으로 실행되므로 이 함수 호출에 별도 GRANT가 필요 없다.
revoke all on function public.is_seller_active(uuid) from public, anon, authenticated;
grant  execute on function public.is_seller_active(uuid) to anon, authenticated, ai_readonly;

-- ── 2) listings — 매물 축: authenticated·anon on_sale SELECT에 판매자 활성 조건 추가 ──────────
-- drop→create(§9.1 허용 전진 패턴). listings_select_own·listings_select_admin은 건드리지 않는다
-- (Never — 본인·관리자 조회는 그대로).
drop policy if exists "listings_select_on_sale" on public.listings;

create policy "listings_select_on_sale" on public.listings
  for select to authenticated
  using (status = 'on_sale' and public.is_seller_active(seller_id));

drop policy if exists "listings_select_on_sale_anon" on public.listings;

create policy "listings_select_on_sale_anon" on public.listings
  for select to anon
  using (status = 'on_sale' and public.is_seller_active(seller_id));

-- ── 3) listing_images — 사진 축: 중첩 RLS로 자동 상속되는지 실측 ─────────────────────────────
-- listing_images_select_on_sale/_anon(0012)은 `exists (select 1 from public.listings l where
-- l.id = listing_images.listing_id and l.status = 'on_sale')`로 listings에 조인한다. 이 서브쿼리도
-- 호출자 권한으로 평가되므로, 위 2절이 listings SELECT를 좁힌 순간 이 EXISTS도 같은 좁아진
-- listings를 보게 된다 — 2026-08-12 로컬 실측(트랜잭션+rollback)으로 확인: 이 파일 2절 적용
-- 후 정지 판매자의 사진 행을 anon·authenticated(비소유자) 양쪽으로 조회하면 0행, 활성 판매자
-- 사진은 그대로 보인다. 즉 **자동으로 따라온다** — 이 절은 별도 정책을 추가하지 않는다
-- (추측이 아니라 실측 결과, 아래 api/tests/integration/test_suspended_seller_hidden_real_db.py가
-- 이 사실을 고정한다).

-- ── 4) listings_ai_readonly_select — AI 3경로를 이 한 자리에서 닫는다 ────────────────────────
-- ai_readonly 롤은 listings를 sold 포함 전부 보도록 using(true)로 설계됐다(0006, CR2 — FR11은
-- 코드가 WHERE status='on_sale'로 직접 막는다). 그 설계 자체(status 필터가 RLS 밖)는 건드리지
-- 않는다 — 여기서 추가하는 것은 "판매자가 활성인가"뿐이다. 이렇게 하면 경로 A(sql_guard가
-- 검증하는 LLM 생성 SQL)·경로 B(doc_rag_node.py의 고정 SQL)·하이브리드(hybrid_rag_node.py)
-- 세 경로가 **코드를 한 줄도 안 고치고** 이 정책 하나로 동시에 닫힌다 — 세 곳에 조건을 흩는
-- 것보다 단순하고(CLAUDE.md A2), 새 AI 조회 경로가 생겨도 자동으로 걸린다(B9).
--
-- sql_guard(api/app/db/sql_guard.py)는 검증기이지 주입기가 아니다(LLM이 만든 SQL에
-- status='on_sale'이 부정 없이 들어 있는지 검사만 한다) — 그래서 "LLM에게 판매자 조건을 추가로
-- 요구"하는 방향은 택하지 않았다(프롬프트로 강제하는 건 계약이 아니다, B9).
--
-- 2026-08-12 로컬 실측: 이 정책 변경이 FR11(sold) 축을 깨지 않는다 — `set local role
-- ai_readonly`로 status='sold' 매물을 조회하면(판매자 활성 무관) 여전히 보인다(코드의
-- status='on_sale' 필터가 원래도 sold를 걸렀고, 이 정책 변경은 그 축을 손대지 않았다). 상세는
-- api/tests/integration/test_doc_rag_node_real_db.py의 회귀 케이스 참조.
drop policy if exists "listings_ai_readonly_select" on public.listings;

create policy "listings_ai_readonly_select" on public.listings
  for select to ai_readonly
  using (public.is_seller_active(seller_id));

-- ── 5) get_seller_public_summary(0019) — SECURITY DEFINER 축: 함수 본문에 조건 추가 ──────────
-- 정의자 함수 안에서는 RLS가 적용되지 않는다(정의자=소유자 권한으로 평가) — 그래서 이 함수는
-- 위 2·4절과 무관하게 여전히 정지 판매자의 매물을 셀 수 있었다. 함수 본문의 인라인 조건이
-- 이 경로의 유일한 강제 지점이다(0019가 이미 그렇게 설계된 이유와 동일).
--
-- ⚠️ 조건은 `is_seller_active(p_seller_id)` 하나만으로 걸면 안 된다(1차 작성 실수, 코드리뷰
-- patch로 발견) — 이 RPC는 "구매자가 남을 볼 때"뿐 아니라 매물 상세 페이지(SellerInfoSection)가
-- **호출자가 누구든 항상** 부른다. `is_seller_active`만으로 걸면 정지된 판매자 본인이나 관리자가
-- 자기(또는 남의) 매물 상세를 봐도 other_on_sale_count가 무조건 0으로 나온다 — 실제로 다른
-- on_sale 매물이 있어도 그렇다. 이는 이 스토리의 불변식 후반부("판매자 본인과 관리자에게는
-- 그대로 보인다")를 정확히 위반한다. 그래서 "판매자가 활성이다" **또는** "호출자가 그 판매자
-- 본인이다" **또는** "호출자가 관리자다" 셋 중 하나면 통과하도록 OR로 넓힌다 — 매물 목록/상세의
-- listings RLS(2·4절)와 달리, 이 RPC는 세 시점(구매자·본인·관리자) 모두가 같은 함수를 거치기
-- 때문에 함수 안에서 그 세 갈래를 직접 갈라야 한다(RLS처럼 역할별 정책을 나눠 걸 수가 없다 —
-- SECURITY DEFINER 함수는 하나뿐이고 호출자 롤로 분기하지 않는다).
create or replace function public.get_seller_public_summary(
  p_seller_id uuid,
  p_exclude_listing_id uuid
) returns table (joined_at timestamptz, other_on_sale_count integer)
language sql
security definer
set search_path = public
stable
as $$
  select
    (select created_at from public.profiles where id = p_seller_id),
    (select count(*)::int from public.listings
       where seller_id = p_seller_id and status = 'on_sale'
         and (
           public.is_seller_active(p_seller_id)
           or auth.uid() = p_seller_id
           or public.is_admin()
         )
         and (p_exclude_listing_id is null or id <> p_exclude_listing_id));
$$;

comment on function public.get_seller_public_summary(uuid, uuid) is
  '판매자 공개 요약(가입 시점 + 다른 on_sale 매물 수, 현재 매물 제외) — FR56. FR11 필터
   (status=on_sale)를 함수 안에서 강제한다. ✎ Story 17.4(DW-804(a))가 본문에
   (is_seller_active(p_seller_id) or auth.uid()=p_seller_id or is_admin()) 조건을 추가 —
   **남이 정지된 판매자를 볼 때만** other_on_sale_count가 0으로 집계된다. 판매자 본인이 자기
   매물 상세를 볼 때, 또는 관리자가 볼 때는 정지 여부와 무관하게 실제 집계가 그대로 나온다(불변식
   "본인·관리자 조회는 그대로" — is_seller_active 단독 조건으로 걸었던 1차 작성은 이 축을 놓쳐
   본인·관리자에게도 무조건 0을 돌려주는 결함이 있었다, 코드리뷰 patch로 수정). 가입 시점
   joined_at 자체는 애초에 이 조건과 무관하게 항상 반환한다. GRANT는 0019가 이미 anon·
   authenticated에 줬고 이 파일은 시그니처를 바꾸지 않으므로 그대로 유지된다.';

-- create or replace는 기존 GRANT(anon·authenticated의 EXECUTE)를 유지한다(0032 6절·0034가 이미
-- 쓴 전제와 동일) — revoke/grant를 다시 적지 않는다.
