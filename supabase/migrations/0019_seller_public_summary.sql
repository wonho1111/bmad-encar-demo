-- 0019_seller_public_summary.sql — 판매자 공개 요약 RPC (Story 10.6, FR56)
-- 적용 순서: 0001 → … → 0018 → 0019(이 파일). self-contained: 참조하는 profiles/listings는 0001/0002에서
--   이미 존재한다.
--
-- 왜 필요한가:
--   상세 페이지 ④판매자정보 슬롯에 "가입 시점"과 "이 판매자의 다른 판매중 매물 N건"을 보여주려 한다.
--   가입 시점(profiles.created_at)은 RLS(0001 profiles_select_self)상 본인·admin만 읽을 수 있어
--   구매자가 남의 행을 직접 조회할 수 없다. 집계(다른 on_sale 매물 수)는 FR11 강제지점(sold 비노출)이라
--   앱 코드가 아니라 DB 안에서 걸러야 한다(conventions.md §6, CLAUDE.md B9).
--   → SECURITY DEFINER 함수 하나로 두 값을 한 번에 구해 anon·authenticated 모두에게 실행 권한만 준다
--     (테이블 GRANT를 넓히지 않으므로 anon 컬럼 화이트리스트(0011)에 델타가 없다).
--
-- 정의자 권한·search_path 고정은 0007의 관례를 그대로 따른다 — 단 노출 방향은 0007과 **반대**다
-- (코드리뷰 2026-07-22 정정: "0007 관례 그대로"라고만 적었던 것은 과장이었다). 0007의 함수는
-- **트리거 전용**이라 EXECUTE를 모든 롤에서 회수한다(anon/authenticated는 절대 직접 호출 못 함).
-- 이 함수는 반대로 **anon·authenticated에 EXECUTE를 GRANT해 RPC로 직접 호출되도록 설계**했다
-- (상세는 비로그인도 열람 가능해야 하므로, FR58). 따라가는 건 "정의자 권한 + search_path 고정"
-- 두 관례뿐이고, 노출 여부는 함수마다 의도적으로 다르다.
--
-- ⚠️ SECURITY DEFINER 함수 안에서는 RLS가 적용되지 않는다(정의자=테이블 소유자 권한으로 평가되고,
-- 소유자에겐 RLS가 애초에 안 걸린다 — 이 함수의 seller_id 인자로 남의 profiles 행을 읽을 수 있는
-- 이유이기도 하다). 그래서 아래 `status = 'on_sale'` 인라인 조건이 이 경로의 **유일한** FR11
-- 강제 지점이다 — RLS가 대신 걸러줄 것이라 믿고 이 줄을 지우면 안 된다.

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
         and (p_exclude_listing_id is null or id <> p_exclude_listing_id));
$$;

comment on function public.get_seller_public_summary(uuid, uuid) is
  '판매자 공개 요약(가입 시점 + 다른 on_sale 매물 수, 현재 매물 제외) — FR56. FR11 필터(status=on_sale)를 함수 안에서 강제한다.';

-- Postgres는 새 함수의 EXECUTE를 기본으로 PUBLIC에 준다 — 이 줄이 없으면 아래 grant가 장식이 되고
-- (anon·authenticated는 PUBLIC 경유로 이미 실행 가능), 롤을 좁히려 grant를 지워도 PUBLIC이 계속 뚫린다
-- (코드리뷰 2026-07-22 지적, #119의 "authenticated 전용으로 좁힘" 경로가 실제로 동작하려면 이 revoke가 전제다).
-- 0007이 트리거 함수에 하는 것과 같은 하드닝(다만 0007은 anon/authenticated에서까지 회수하는 트리거 전용).
revoke all on function public.get_seller_public_summary(uuid, uuid) from public;
-- anon도 상세 열람이 가능하므로(FR58) 두 롤에만 실행 권한을 부여한다. 테이블 GRANT는 넓히지 않는다.
grant execute on function public.get_seller_public_summary(uuid, uuid) to anon, authenticated;
