// 구매자 매물 목록 + 필터 검색 (FR9) — 서버 컴포넌트.
//
// 동작:
//   1) URL 쿼리스트링(searchParams)에서 필터를 읽는다(Next.js 16: searchParams는 Promise → await).
//   2) listings를 조회하되 판매중(on_sale)만 — FR11 단일 규칙은 buyerListingsQuery(@/lib/listings)에서 비롯된다.
//   3) 결과를 ListingCard로 렌더. 0건이면 빈 상태 안내, 조회 실패면 별도 한국어 에러 안내(0건과 구분).
//
// 열람: FR58(8.5)부터 /search는 비로그인(anon)도 열람 가능한 공개 경로 — proxy 차단 없음.
//   on_sale만 보이는 FR11 규칙은 buyerListingsQuery + DB RLS가 집행. 로그인 사용자는 상단바에 역할 라벨이 추가로 붙는다.
//
// FR11 비노출 규칙(판매완료는 구매자에게 안 보임)과 이중 방어 근거는 @/lib/listings 한 곳에 모았다(단일 출처).
//
// CM3(즉시 비노출): 이 페이지는 cookies() 기반 인증을 쓰므로 매 요청 DB를 다시 읽는 동적 렌더다.
//   매물이 sold로 바뀌면 재조회 시 즉시 사라진다. 정적 캐시로 잔존하지 않도록 force-dynamic을 명시한다.
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, LISTING_OPTIONS, type UserRole } from '@/lib/constants';
import { buyerListingsQuery, attachCoverImages } from '@/lib/listings';
import AppHeader from '@/components/layout/AppHeader';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import ResponsiveGrid from '@/components/ui/ResponsiveGrid';
import SearchFilters, { type SearchFilterValues } from './SearchFilters';

// CM3 보장: 구매자 목록은 매 요청 최신 DB 상태를 반영해야 한다(sold 즉시 비노출). 정적화 방지.
export const dynamic = 'force-dynamic';

// searchParams 한 항목은 string | string[] | undefined → 첫 문자열만 안전하게 꺼낸다.
function asStr(v: string | string[] | undefined): string {
  if (Array.isArray(v)) return v[0] ?? '';
  return v ?? '';
}

// "목록에 있는 값일 때만" 통과시킨다(목록 밖 임의 값은 무시 → 쿼리 오염 방지). 빈 값이면 미적용.
function pickOption(v: string, options: readonly string[]): string | null {
  return v !== '' && options.includes(v) ? v : null;
}

// 정수 파싱 — "숫자만으로 된 문자열"일 때만 통과시킨다(미적용이면 null).
//   ⚠️ Number()는 '1e9'(=10억)·'0x10' 같은 표기도 정수로 받아들이고, 아주 큰 값은 DB bigint 범위를
//      넘겨 조회 에러를 낸다(사용자에겐 "불러오기 실패"로 잘못 보임). 그래서 정규식으로 순수 숫자열만
//      허용하고, 안전 정수(MAX_SAFE_INTEGER) 이하만 통과시킨다 — 범위 밖이면 그 필터는 그냥 미적용.
function asInt(v: string): number | null {
  const s = v.trim();
  if (!/^\d+$/.test(s)) return null; // 부호·소수점·지수표기·16진수 등은 모두 거른다(미적용).
  const n = Number(s);
  return Number.isSafeInteger(n) ? n : null;
}

// LIKE 패턴 메타문자(\ % _)를 이스케이프 — 사용자가 친 '%'·'_'를 "특수문자"가 아니라 "그 글자 자체"로
// 검색하게 한다. 안 하면 '%' 입력이 "전부 일치"가 돼 키워드 필터가 무력화된다(AC1 부분일치 보장).
function escapeLike(s: string): string {
  return s.replace(/[\\%_]/g, '\\$&');
}

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const sp = await searchParams; // Next.js 16: searchParams는 Promise라 await 필요.
  const supabase = await createClient();

  // 상단바용 역할 라벨(홈 패턴 재사용 — profiles_select_self RLS로 본인 행 읽기).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // ── URL 필터 파싱 ───────────────────────────────────────────────
  const q = asStr(sp.q).trim();
  const bodyType = pickOption(asStr(sp.body_type), LISTING_OPTIONS.body_type);
  const color = pickOption(asStr(sp.color), LISTING_OPTIONS.color);
  const fuel = pickOption(asStr(sp.fuel), LISTING_OPTIONS.fuel);
  const transmission = pickOption(asStr(sp.transmission), LISTING_OPTIONS.transmission);
  const region = pickOption(asStr(sp.region), LISTING_OPTIONS.region);
  let priceMin = asInt(asStr(sp.price_min));
  let priceMax = asInt(asStr(sp.price_max));
  let yearMin = asInt(asStr(sp.year_min));
  let yearMax = asInt(asStr(sp.year_max));

  // 최소>최대로 거꾸로 입력하면(예: 최소 5000~최대 1000) 0건이 나와 혼란 → 둘 다 유효할 때만 값을 맞바꿔(swap) 정상 범위로 보정.
  if (priceMin !== null && priceMax !== null && priceMin > priceMax) {
    [priceMin, priceMax] = [priceMax, priceMin];
  }
  if (yearMin !== null && yearMax !== null && yearMin > yearMax) {
    [yearMin, yearMax] = [yearMax, yearMin];
  }

  // ── 쿼리 빌드 ───────────────────────────────────────────────────
  // 구매자 관점(판매중만) 시작점은 buyerListingsQuery(FR11 단일 출처). 조건은 값이 있을 때만 체이닝한다.
  //
  // ⚠️ /search는 anon(비로그인)도 여는 열람 경로다(conventions.md §8). anon은 `0011_listings_anon_select.sql`이
  //   컬럼 단위로 select 권한을 명시한 목록만 읽을 수 있고, 신뢰속성 3컬럼(accident_status·
  //   is_single_owner·is_non_smoker)은 그 목록에 없다(실측: anon 키로 이 3컬럼을 요청하면
  //   `42501 permission denied` — select 전체가 실패해 목록 자체가 안 뜬다). fuel은 이미
  //   0011에 있어 anon도 안전하다.
  //   신규 GRANT를 추가해 anon에도 열 수 있지만, conventions.md §9.3은 anon 노출 컬럼을
  //   "넓히는" GRANT 변경을 dev 자율 판단이 아니라 **사용자 승인 필수(b)**로 못박는다 —
  //   그래서 이 스토리(값이 흐르게 하는 것)에서 임의로 넓히지 않고, 로그인 사용자에게만
  //   신뢰속성을 함께 조회한다(대장에 등재, 10.2 착수 시 재검토).
  const trustColumns = user ? ', accident_status, is_single_owner, is_non_smoker' : '';
  let query = buyerListingsQuery(
    supabase,
    `id, manufacturer, model, year, price, mileage, region, seller_name, fuel${trustColumns}`,
  );

  if (q) query = query.ilike('model', `%${escapeLike(q)}%`); // 모델명 부분일치(대소문자 무시, LIKE 메타문자 이스케이프)
  if (bodyType) query = query.eq('body_type', bodyType);
  if (color) query = query.eq('color', color);
  if (fuel) query = query.eq('fuel', fuel);
  if (transmission) query = query.eq('transmission', transmission);
  if (region) query = query.eq('region', region);

  // 가격·연식 범위 — 위에서 역전(min>max) 입력은 이미 swap으로 보정했으므로 여기선 그대로 적용한다.
  // 한쪽만 있으면 그 한쪽만 적용(min만→이상, max만→이하).
  if (priceMin !== null) query = query.gte('price', priceMin);
  if (priceMax !== null) query = query.lte('price', priceMax);
  if (yearMin !== null) query = query.gte('year', yearMin);
  if (yearMax !== null) query = query.lte('year', yearMax);

  // created_at 내림차순. 시드처럼 created_at이 같은 행들의 순서가 새로고침마다 뒤집히지 않도록
  // id를 2차 정렬키로 둔다(안정적·결정적 정렬).
  query = query.order('created_at', { ascending: false }).order('id', { ascending: false });

  const { data: rows, error } = await query.returns<ListingCardData[]>();

  // anon 경로는 위 select에서 신뢰속성 3컬럼을 아예 안 물었으므로(trustColumns 참조) 그 값이
  // 행에 `undefined`(키 자체가 없음)로 온다. 계약(conventions §4)은 "값이 없으면 null"이지
  // "필드가 없음"이 아니다 — 10.2가 뱃지 로직에서 `listing.accident_status`를 읽을 때 undefined와
  // null을 다르게 다루면(예: `=== null`로만 미상 판정) anon 렌더만 조용히 갈린다. 그래서 여기서
  // 명시적으로 null을 채워 런타임 모양을 선언한 타입(`ListingCardData`)과 맞춘다.
  const normalizedRows = rows && !user
    ? rows.map((r) => ({
        ...r,
        accident_status: null,
        is_single_owner: null,
        is_non_smoker: null,
      }))
    : rows;

  // 대표사진 URL·장수를 채운다(Story 9.4). 홈 미리보기와 **같은 함수**를 쓴다 — 로직 이원화 금지.
  const listings = normalizedRows ? await attachCoverImages(supabase, normalizedRows) : normalizedRows;

  if (error) {
    // 원본은 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분(AC2).
    console.error('[search] 매물 목록 조회 실패:', error);
  }

  // SearchFilters에 넘길 초기값(현재 URL 그대로 폼에 반영 → 새로고침해도 유지).
  const initialFilters: SearchFilterValues = {
    q,
    body_type: bodyType ?? '',
    color: color ?? '',
    fuel: fuel ?? '',
    transmission: transmission ?? '',
    region: region ?? '',
    price_min: priceMin !== null ? String(priceMin) : '',
    price_max: priceMax !== null ? String(priceMax) : '',
    year_min: yearMin !== null ? String(yearMin) : '',
    year_max: yearMax !== null ? String(yearMax) : '',
  };

  return (
    <>
      <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} currentPath="/search" />
      {/* max-w-3xl(768px)이면 4열 브레이크포인트(≥1100px)에 도달해도 칸이 안 생긴다 —
          D5의 4열을 실제로 보이게 하려면 본문 폭도 함께 열어야 한다(Story 9.4 AC6). */}
      <main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
        <section className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">매물 탐색</h1>
          <p className="text-sm text-zinc-500">
            원하는 조건으로 판매 중인 매물을 검색하세요.
          </p>
        </section>

        <SearchFilters initial={initialFilters} />

        <section className="flex flex-col gap-3">
          {error ? (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              매물 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
            </p>
          ) : !listings || listings.length === 0 ? (
            <p className="text-sm text-zinc-500">
              조건에 맞는 매물이 없습니다. 필터를 완화해 보세요.
            </p>
          ) : (
            <>
              <p className="text-sm text-zinc-500">{listings.length}건의 매물</p>
              {/* D5: 가로폭은 **열 수로만** 흡수한다(≥1100px 4열 · 640~1099px 2열 · <640px 1열).
                  카드 내부 가로 배치는 어느 폭에서도 접히지 않는다 — 규칙은 ResponsiveGrid가 소유. */}
              <ResponsiveGrid>
                {listings.map((l) => (
                  <ListingCard key={l.id} listing={l} />
                ))}
              </ResponsiveGrid>
            </>
          )}
        </section>
      </main>
    </>
  );
}
