-- 0020_listings_view_count.sql — 조회수(view_count) 컬럼 + increment RPC 하드닝 (Story 11.1)
-- 적용 순서: 0001 → … → 0019 → 0020(이 파일). self-contained: 참조하는 listings는 0002에서
--   이미 존재한다.
--
-- 왜 필요한가:
--   "인기 매물" 정렬(Story 11.4)을 만들려면 listings에 조회수가 있어야 한다. 그런데 컬럼만 추가하면
--   RLS(listings_update_own)는 "본인 매물이면 통과"만 보므로, 판매자가 자기 매물의 view_count를
--   직접 UPDATE로 조작할 수 있다(RLS는 행만 막고 컬럼은 못 막는다). 그래서 값을 바꾸는 유일한 통로를
--   SECURITY DEFINER RPC 하나로 좁히고, 컬럼 직접 쓰기는 authenticated·anon 양쪽에서 회수한다.
--   패턴 선례: `0019_seller_public_summary.sql`의 "SECURITY DEFINER + search_path 고정 + REVOKE ALL
--   FROM PUBLIC + GRANT TO anon,authenticated" 하드닝 조합을 그대로 따른다(리서치
--   `research-supabase-viewcount-rpc.md`가 Supabase 메인테이너 권장안과 일치함을 확인).
--
-- ⚠️ 컬럼 단위 REVOKE만으로는 안 막힌다(이 파일에서 가장 중요한 사실, 실측으로 확인) —
--   `alter default privileges ... grant all on tables to anon, authenticated`(플랫폼 기본 GRANT,
--   Supabase 원격 + 이 레포 게이트 프렐류드 둘 다 재현)가 listings 생성 시 authenticated에게
--   **테이블 전체**(모든 컬럼) INSERT·UPDATE 권한을 이미 준다. Postgres의 컬럼 권한 검사는
--   "테이블 단위 권한 OR 컬럼 단위 권한"이라, 컬럼 하나만 회수해도 테이블 단위 권한이 여전히
--   그 컬럼의 쓰기를 허용한다(로컬 Postgres로 직접 재현: 테이블 단위 GRANT ALL 후 컬럼 단위
--   REVOKE만 하면 has_column_privilege가 여전히 true). 그래서 0011이 anon의 SELECT에 쓴 것과
--   같은 2단계가 UPDATE·INSERT 두 축 모두에 필요하다: ① 테이블 전체 권한을 통째로 회수
--   ② view_count를 뺀 나머지 전 컬럼에 그 권한을 다시 GRANT. 이렇게 해야 "이전까지 authenticated가
--   쓸 수 있던 컬럼"은 그대로 쓰고 view_count만 막힌다(기존 등록/수정/구매완료 기능에 회귀 없음).
--
-- ── 1) view_count 컬럼 ────────────────────────────────────────────────
-- if not exists: 재적용 안전성(0007·0009·0017의 관례와 동일 — 이 레포의 컬럼 추가 마이그는 전부 이 형태).
alter table public.listings add column if not exists view_count int not null default 0;

comment on column public.listings.view_count is
  '누적 조회수(Story 11.1, 11.4 인기 정렬용). 유일한 쓰기 통로는 increment_listing_view RPC —
   authenticated의 컬럼 직접 UPDATE·INSERT, anon의 직접 쓰기는 전부 아래에서 회수한다.';

-- ── 2) increment_listing_view RPC — 이 id의 view_count를 1 증가시키는 것 "만" 한다 ──────
-- 0019와 동일한 하드닝: security definer + search_path 고정(빈 문자열 → 모든 테이블 참조에
-- public. 접두 필수) + 아래 REVOKE/GRANT로 실행 권한 최소화.
-- 범용 UPDATE로 확장하지 않는다 — 컬럼/값을 파라미터로 받지 않는다(A2, 이 스토리 Never 절).
create or replace function public.increment_listing_view(p_listing_id uuid)
returns void
language sql
security definer
set search_path = ''
as $$
  update public.listings set view_count = view_count + 1 where id = p_listing_id;
$$;

comment on function public.increment_listing_view(uuid) is
  '상세 페이지 진입 시 조회수 +1(Story 11.1). SECURITY DEFINER — anon·authenticated 모두 실행
   가능(FR58, 상세는 비로그인도 열람). 호출될 때마다 항상 +1(멱등 아님, 의도된 동작) — 호출 지점을
   상세 페이지 서버 컴포넌트 한 곳으로 한정하는 것이 유일한 안전장치(카드 렌더 경로는 호출하지 않음).';

-- Postgres는 새 함수의 EXECUTE를 기본으로 PUBLIC에 준다 — 0019와 동일 이유로 먼저 회수한 뒤
-- 필요한 롤에만 재부여한다(이 줄이 없으면 아래 grant가 장식이 되고 PUBLIC 경유로 누구나 호출 가능).
revoke all on function public.increment_listing_view(uuid) from public;
grant execute on function public.increment_listing_view(uuid) to anon, authenticated;

-- ── 3) authenticated의 view_count 직접 UPDATE 차단(컬럼 단위 하드닝, UPDATE 축) ─────────
-- 위 주석 설명대로, 테이블 전체 UPDATE를 먼저 통째로 회수한 뒤 view_count를 뺀 나머지 전 컬럼에
-- 다시 GRANT해야 실제로 막힌다(컬럼 단위 REVOKE 단독으로는 무효 — 실측 확인).
-- 목록 = view_count 추가 전까지 listings가 가진 전 컬럼(0002·0007·0017 누적, 25개) — 기존
-- 등록/수정(SellForm)·구매완료 처리(ListingActions)·모바일 앱(Flutter sell_controller)이 쓰던
-- 컬럼 전부를 그대로 유지해 회귀를 만들지 않는다. RLS(listings_update_own)가 행 단위(본인 매물만)는
-- 이미 강제하므로, 여기서는 "어떤 컬럼을 바꿀 수 있는가"만 좁힌다.
revoke update on public.listings from authenticated;

grant update (
  id,
  seller_id,
  status,
  embedding,
  created_at,
  updated_at,
  manufacturer,
  model,
  body_type,
  year,
  price,
  mileage,
  color,
  fuel,
  transmission,
  displacement,
  seats,
  region,
  accident_free,
  options,
  description,
  seller_name,
  accident_status,
  is_single_owner,
  is_non_smoker
) on public.listings to authenticated;
-- view_count는 위 목록에 없다 — authenticated의 직접 UPDATE 대상에서 제외된 유일한 컬럼.

-- ── 4) authenticated의 등록 시점 view_count 위조 차단(컬럼 단위 하드닝, INSERT 축) ───────
-- UPDATE만 막으면 판매자가 **등록(INSERT) 시점에** view_count를 원하는 값으로 심을 수 있다
-- (SellForm.tsx가 anon 키로 클라이언트에서 직접 `.from('listings').insert(...)`하므로 PostgREST
-- 호출 한 번이면 도달한다 — 실측: 999999가 그대로 저장됨). 이 축을 막지 않으면 "RPC가 유일한
-- 쓰기 통로"라는 이 스토리의 핵심 주장이 거짓이 된다. UPDATE 축과 동일한 2단계 패턴을 그대로 적용.
revoke insert on public.listings from authenticated;

grant insert (
  id,
  seller_id,
  status,
  embedding,
  created_at,
  updated_at,
  manufacturer,
  model,
  body_type,
  year,
  price,
  mileage,
  color,
  fuel,
  transmission,
  displacement,
  seats,
  region,
  accident_free,
  options,
  description,
  seller_name,
  accident_status,
  is_single_owner,
  is_non_smoker
) on public.listings to authenticated;
-- view_count는 위 목록에도 없다 — authenticated는 등록 시점에도 이 컬럼에 값을 지정할 수 없고,
-- INSERT 문에서 생략되므로 항상 컬럼 기본값(0)이 적용된다.

-- ── 5) anon의 listings 직접 쓰기 차단 ────────────────────────────────
-- anon이 listings에 직접 쓰는 정당한 경로는 없다(anon용 쓰기 RLS 정책이 하나도 없다) — 지금은
-- RLS가 0행으로 만들어 조용히 막고 있을 뿐 GRANT는 열려 있다(실측: anon=awdDxtm,
-- has_column_privilege('anon',…,'view_count','UPDATE')=true) — 나중에 anon 쓰기 정책이 하나라도
-- 생기면 즉시 뚫린다. anon의 유일한 정당한 쓰기 경로는 위 2번 블록이 준 increment_listing_view
-- RPC의 EXECUTE뿐이므로, *직접* 테이블 쓰기(INSERT/UPDATE/DELETE)만 회수한다.
-- ⚠️ `revoke all`은 쓰지 않는다 — 0011이 anon에게 준 컬럼 SELECT까지 함께 회수돼 비로그인
-- 열람이 깨진다(실측 확인). 그리고 이 revoke가 anon의 listings 테이블 권한 전체를 회수하는 것도
-- 아니다 — TRUNCATE·REFERENCES·TRIGGER·MAINTAIN은 그대로 남는다(#139, 이 스토리 범위 밖).
revoke insert, update, delete on public.listings from anon;

-- ── 6) updated_at 트리거를 listings 전용으로 교체(조회가 "수정 시각"을 덮어쓰지 않게) ────
-- 위 RPC의 UPDATE가 0002의 listings_set_updated_at을 그대로 발동시키면 조회할 때마다
-- updated_at(관리자 거래내역이 "거래일"로 쓰는 값)이 갱신돼 컬럼 의미가 조용히 바뀐다.
-- 그렇다고 트리거에 `when` 절을 걸어 통째로 건너뛰면 안 된다 — 공유 함수 public.set_updated_at()는
-- updated_at 갱신과 created_at := old.created_at(0002가 명시 문서화한 등록일 위조 차단) 두 임무를
-- 하는데, `when`은 트리거 자체를 꺼서 둘 다 함께 무력화한다(실측 재현: view_count와 함께
-- created_at을 바꾸는 UPDATE가 통과해 등록일이 위조됨). 그래서 listings 전용 트리거 함수를
-- 새로 만들어 두 임무를 함수 본문 안에서 분리한다 — created_at 보존은 항상, updated_at 갱신은
-- view_count가 안 바뀐 경우에만. 공유 함수 public.set_updated_at()는 건드리지 않는다 — 이
-- 마이그레이션이 그 함수를 쓰던 유일한 트리거(listings_set_updated_at, 0002)를 drop해서
-- 지금은 참조하는 트리거가 0건이지만(#142, 코드리뷰 2026-07-28 지적·grep으로 확인), 이 함수는
-- 0002가 만든 것이고 지우는 것은 이 스토리 범위 밖의 별도 판단이라 그대로 둔다(A3).
-- 조건을 `when` 절이 아니라 함수 본문에 두는 이유가 하나 더 있다: `when`에 new.view_count를
-- 쓰면 트리거가 그 컬럼에 pg_depend 의존을 걸어 향후 `drop column view_count`를 막고,
-- `drop ... cascade`는 트리거를 조용히 지워버린다.
create or replace function public.listings_set_timestamps()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.created_at := old.created_at;  -- created_at 불변 보장(UPDATE로 변경 불가, 0002와 동일 계약)
  -- 아래 조건이 거르는 것은 "view_count가 바뀐 UPDATE"이지 "view_count**만** 바뀐 UPDATE"가
  -- 아니다(#141, 코드리뷰 2026-07-28 지적·실측 확인) — price 등 다른 컬럼을 view_count와
  -- **함께** 바꾸는 UPDATE도 갱신을 건너뛴다(실측: `set price = 31111111, view_count =
  -- view_count + 1` → price는 바뀌지만 updated_at은 그대로). 동작은 그대로 둔다 — 지금은
  -- authenticated·anon 모두 view_count 쓰기 권한이 없어(3·4·5번 블록) 그런 혼합 UPDATE가
  -- 어떤 클라이언트 경로로도 도달 불가하다. 좁히려면 행 전체 비교가 필요한데, 운영의
  -- embedding이 vector(768)이라 이 환경에서 to_jsonb(record) 동작을 실측할 수 없다(#141 트리거).
  if new.view_count is not distinct from old.view_count then
    new.updated_at := now();  -- 조회수가 안 바뀐 UPDATE = 진짜 "수정"
  end if;
  return new;
end;
$$;

comment on function public.listings_set_timestamps() is
  'listings 전용 BEFORE UPDATE 트리거 함수(Story 11.1). created_at 보존은 항상, updated_at 갱신은
   view_count가 바뀐(다른 컬럼과 함께 바뀐 경우 포함) UPDATE에서는 건너뛴다 — 조회수 증가가
   "수정 시각"을 덮어쓰지 않게 한다(#141, 현재 이 분기에 도달하는 클라이언트 경로는 없음).
   공유 함수 public.set_updated_at()은 이 마이그레이션이 drop한 listings_set_updated_at 트리거가
   그 유일한 참조자였다 — 지금은 참조하는 트리거가 0건이지만(#142), 다른 마이그레이션 소유물이라
   여기서 지우지 않는다.';

-- if exists 필수 — 이 파일의 다른 블록이 지키는 재적용 안전성 관례와 일치. 없으면 트리거가 아직
-- 없는 DB(예: 이 마이그 재적용 직전 상태가 아닌 DB)에서 게이트가 ON_ERROR_STOP으로 통째로 롤백된다.
drop trigger if exists listings_set_updated_at on public.listings;
-- 새로 만드는 트리거 이름도 함께 drop해야 재적용이 성립한다(0007·0008·0016이 전부 이 형태 —
-- `drop trigger if exists <만들 이름>` 직후 `create trigger <같은 이름>`). 옛 이름만 지우면 이미
-- 0020이 적용된 DB에 다시 적용할 때 `trigger "listings_set_timestamps" already exists`로 죽는다
-- (실측: exit 3). create trigger엔 `or replace`·`if not exists`가 없어 이 drop이 유일한 수단이다.
drop trigger if exists listings_set_timestamps on public.listings;

create trigger listings_set_timestamps
  before update on public.listings
  for each row execute function public.listings_set_timestamps();

revoke execute on function public.listings_set_timestamps() from public, anon, authenticated;
--
-- ⚠️ 유지보수 함정(코드리뷰 지적, 0011의 anon SELECT 목록과 같은 종류의 경고) — 앞으로 listings에
-- authenticated가 직접 쓸 새 컬럼을 추가하면, 3번(UPDATE)·4번(INSERT) 두 GRANT 목록 모두에 그
-- 컬럼을 추가해야 한다. 안 하면 그 컬럼은 authenticated에게 조용히 쓰기 불가 상태가 된다(테이블
-- 전체 권한이 위에서 이미 회수됐으므로, 이 목록에 없는 컬럼은 기본값이 "막힘"이다).
