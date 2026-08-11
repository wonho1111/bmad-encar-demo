-- 0036_is_seller_active_private_schema.sql — is_seller_active(uuid)를 public에서 private
-- 스키마로 옮긴다 (Story 17.4 후속 코드리뷰 patch, P1 [high]) — 0035가 "PostgREST가 RPC로
-- 자동 노출한다 — is_admin()·is_admin_active()와 동일하게 회수한다"고 적었는데, 그 REVOKE는
-- 실제로는 노출을 막지 못했다(아래 실측).
--
-- self-contained: 이 파일이 참조하는 것은 전부 자기보다 앞 번호다 — public.profiles(0001)·
--   public.listings(0002·0006·0011)·public.is_admin()(0001)·public.is_seller_active(0035, 이
--   파일이 대체)·public.get_seller_public_summary(0019·0035). 뒤 번호를 가정하지 않는다.
--
-- ── 실측(2026-08-12, 로컬 55321) — 0035:67-71의 "동일하게 회수한다"는 틀렸다 ──────────────────
-- anon 키만으로 `POST /rest/v1/rpc/is_seller_active {"p_seller_id":"<uuid>"}` → **true**.
-- 그 프로필을 suspended로 바꾼 뒤 같은 호출 → **false**. 원복 후 재호출 → 다시 true.
-- 즉 **모든 uuid에 대한 정지 여부 오라클**이 anon에게 열려 있었다 — `revoke all ... from public`이
-- 걸려 있었는데도(0035 1절) 막히지 않았다.
-- 양성 대조군(비교 대상 ①): `GET /rest/v1/profiles?id=eq.<uuid>&select=id,status`(anon 키) →
-- `[]` — `profiles` RLS는 정상적으로 이 직접 조회를 막는다. 즉 뚫린 것은 `profiles` 테이블
-- 자체가 아니라 함수를 경유한 RPC 경로였다.
-- 비교 대상 ②(같은 계보의 자매 함수): `POST /rest/v1/rpc/is_admin`(anon) → `42501 permission
-- denied`. `is_admin()`(0001)·`is_admin_active()`(0032)는 **인자가 없고** `authenticated`에만
-- grant돼 있어 REVOKE만으로 anon 경로가 실제로 막힌다 — 0035가 "동일하게"라고 쓴 전제 자체가
-- 이 함수(인자 있음, `anon`에 EXECUTE 필요)에는 성립하지 않았다: `listings_select_on_sale_anon`
-- 정책이 `anon` 롤로 평가되려면 `is_seller_active`도 `anon`에 EXECUTE가 있어야 하고,
-- PostgREST는 스키마가 노출 목록(`supabase/config.toml:13`, `schemas = ["public",
-- "graphql_public"]`)에 있으면 그 GRANT를 그대로 `/rest/v1/rpc/<함수명>` 경로로 연결한다 —
-- `revoke ... from public`은 "인가 없는 임의 롤"만 막을 뿐, `anon` 자체에게 준 EXECUTE는 그대로
-- 유효하고 PostgREST는 그 유효한 EXECUTE를 보고 RPC를 연다.
--
-- ── 해법 — public이 아닌 스키마로 옮긴다(REVOKE가 아니라 노출면 자체를 없앤다) ─────────────────
-- `supabase/config.toml`의 노출 목록에 없는 스키마는 PostgREST가 애초에 RPC 경로를 만들지
-- 않는다(REVOKE 여부와 무관). `private` 스키마를 새로 만들고 함수를 그리로 옮긴다.
--
-- ⚠️ 이 정책들을 평가하는 롤(anon·authenticated·ai_readonly)은 스키마 USAGE + 함수 EXECUTE
-- **둘 다** 있어야 한다 — 정책 조건 자체가 그 롤의 세션 권한으로 평가되기 때문이다(SECURITY
-- DEFINER는 함수 본문 안의 권한만 우회하지, 함수를 "찾아 호출하는" 권한까지 우회하지 않는다).
-- 둘 중 하나라도 빠지면 그 롤의 listings 조회 전체가 42501로 죽는다(조용히 0행이 되는 게
-- 아니다 — 스펙 Boundaries 절이 GRANT 누락 증상으로 미리 경고한 것과 같은 실패 모드).

create schema if not exists private;
grant usage on schema private to anon, authenticated, ai_readonly;

-- ── is_seller_active(uuid) — 본문은 0035와 동일, 스키마만 private ────────────────────────────
create or replace function private.is_seller_active(p_seller_id uuid)
returns boolean
language sql
security definer
set search_path = ''
stable
parallel safe
as $$
  select exists (
    select 1 from public.profiles
    where id = p_seller_id and status = 'active'
  );
$$;

comment on function private.is_seller_active(uuid) is
  '판매자(profiles.id=p_seller_id)가 활성(status=''active'')인가 — Story 17.4, DW-804(a).
   0036이 public.is_seller_active(0035)를 private 스키마로 옮긴 버전이다(함수 본문은 완전히
   동일) — public 스키마 함수는 PostgREST가 anon 키만으로 /rest/v1/rpc/is_seller_active를 통해
   RPC 호출 가능하게 자동 노출하고, revoke all ... from public은 이미 anon에 준 EXECUTE를
   막지 못해 이 경로로 임의 uuid의 정지 여부를 anon이 알아낼 수 있었다(이 파일 헤더 실측).
   private 스키마는 supabase/config.toml의 노출 목록(schemas) 밖이라 PostgREST가 RPC 경로
   자체를 만들지 않는다. SECURITY DEFINER인 이유는 0035와 같다(profiles RLS 우회가 필요 —
   listings_select_on_sale/_anon·listings_ai_readonly_select 정책이 "남의"(매물 판매자의)
   profiles 행을 물어야 하는데 인라인 서브쿼리는 profiles RLS를 그대로 타서 전체 매물이
   사라진다, 0035 파일 헤더 참조). 소비처: listings_select_on_sale/_anon(이 파일 아래)·
   listings_ai_readonly_select(이 파일 아래)·listing_images는 listings에 조인해 간접 적용
   (자동 상속, 0035 3절 실측)·get_seller_public_summary(이 파일 아래, create or replace).
   판매자 행이 없는 경우(profiles가 없는 seller_id)는 exists가 거짓 → false(매물 숨김)다.
   listings.seller_id는 references public.profiles(id) on delete cascade(0002)라 판매자
   profiles가 없는 매물은 존재할 수 없어(FK가 보장) 이 분기는 도달 불가능이지만, 방어적으로
   "판정 불가 = 숨김" 쪽으로 fail-closed하는 것이 이 함수의 성격과 맞다(0035와 동일 판단).
   ✎ 2026-08-12 후속 코드리뷰 patch(P1) — parallel safe: 이 함수가 listings_select_on_sale/
   _anon·listings_ai_readonly_select 세 정책의 using 절에 들어가는데, parallel 절을 안 쓰면
   Postgres 기본값 PARALLEL UNSAFE라 listings를 읽는 모든 쿼리가 병렬 플랜을 못 받는다(실측,
   로컬 55322, 트랜잭션+rollback, parallel_setup_cost=0·parallel_tuple_cost=0·
   min_parallel_table_scan_size=0·max_parallel_workers_per_gather=2): 이 정책판에서
   `set local role anon; explain select id from public.listings where status=''on_sale''`
   → Seq Scan(병렬 없음), 대조군(정책 없는 슈퍼유저) → Gather/Workers Planned: 2/Parallel Seq
   Scan. ⓐ 정책에서 이 함수 조건을 빼고 17.4 이전 형태로 되돌리면 → Gather 복구(이 회귀를
   17.4가 만들었다는 증거). ⓑ 조건은 그대로 두고 `alter function ... parallel safe`만 추가하면
   → Gather 복구(한 단어가 원인). PARALLEL SAFE 조건도 충족한다 — 이 함수는 public.profiles를
   대상으로 단일 SELECT(exists)만 하고 쓰기·시퀀스 사용·트랜잭션 상태 변경이 없다. 형제 함수
   is_admin()·is_admin_active()·get_seller_public_summary는 여전히 proparallel=''u''이며(실측
   확인) 이 패치가 건드리지 않았다 — 범위를 이 스토리(17.4)가 만든 함수 하나로 한정한다(A3
   외과적 변경).';

-- anon·authenticated·ai_readonly 세 롤 모두 실제로 이 함수를 참조하는 정책이 있다(아래) —
-- 그 외 롤에는 주지 않는다(0035 1절과 동일 최소권한 원칙, 이번엔 스키마 이동만 한다).
revoke all on function private.is_seller_active(uuid) from public;
grant  execute on function private.is_seller_active(uuid) to anon, authenticated, ai_readonly;

-- ── listings — 3개 정책을 private.is_seller_active 참조로 drop→create ───────────────────────
-- 이름·조건은 0035와 byte-identical, 함수 참조만 public. → private.으로 바뀐다(§9.1 전진 패턴).
drop policy if exists "listings_select_on_sale" on public.listings;

create policy "listings_select_on_sale" on public.listings
  for select to authenticated
  using (status = 'on_sale' and private.is_seller_active(seller_id));

drop policy if exists "listings_select_on_sale_anon" on public.listings;

create policy "listings_select_on_sale_anon" on public.listings
  for select to anon
  using (status = 'on_sale' and private.is_seller_active(seller_id));

drop policy if exists "listings_ai_readonly_select" on public.listings;

create policy "listings_ai_readonly_select" on public.listings
  for select to ai_readonly
  using (private.is_seller_active(seller_id));

-- ── get_seller_public_summary(0019·0035) — public.is_seller_active → private.is_seller_active만 교체 ──
-- 그 외(본인·관리자 carve-out, exclude id 처리)는 0035 그대로다.
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
           private.is_seller_active(p_seller_id)
           or auth.uid() = p_seller_id
           or public.is_admin()
         )
         and (p_exclude_listing_id is null or id <> p_exclude_listing_id));
$$;

comment on function public.get_seller_public_summary(uuid, uuid) is
  '판매자 공개 요약(가입 시점 + 다른 on_sale 매물 수, 현재 매물 제외) — FR56. FR11 필터
   (status=on_sale)를 함수 안에서 강제한다. (is_seller_active(p_seller_id) or
   auth.uid()=p_seller_id or is_admin()) 조건으로 **남이 정지된 판매자를 볼 때만**
   other_on_sale_count가 0으로 집계된다(Story 17.4, DW-804(a)). ✎ 0036이 is_seller_active의
   참조를 private.is_seller_active로 갱신했다(함수가 private 스키마로 옮겨졌을 뿐 조건의 의미는
   0035와 동일 — private.is_seller_active는 이 파일 위에서 새로 정의됨). 판매자 본인이 자기
   매물 상세를 볼 때, 또는 관리자가 볼 때는 정지 여부와 무관하게 실제 집계가 그대로 나온다.
   가입 시점 joined_at 자체는 이 조건과 무관하게 항상 반환한다. GRANT는 0019가 이미 anon·
   authenticated에 줬고 이 파일은 시그니처를 바꾸지 않으므로 그대로 유지된다.';

-- ── public.is_seller_active(0035) 제거 — private 버전으로 완전히 대체됐다 ────────────────────
-- 위 세 정책 + get_seller_public_summary가 이제 전부 private.is_seller_active를 참조하므로
-- public 버전을 참조하는 곳이 없다. 남겨두면 노출 오라클이 그대로 재현되므로(이 파일 헤더 실측)
-- 반드시 지운다.
drop function if exists public.is_seller_active(uuid);
