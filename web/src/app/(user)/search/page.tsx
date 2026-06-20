// 구매자 매물 목록 + 필터 검색 (FR9) — 서버 컴포넌트.
//
// 동작:
//   1) URL 쿼리스트링(searchParams)에서 필터를 읽는다(Next.js 16: searchParams는 Promise → await).
//   2) listings를 조회하되 status='on_sale'만(FR11 — 판매완료는 구매자에게 안 보임).
//   3) 결과를 ListingCard로 렌더. 0건이면 빈 상태 안내, 조회 실패면 별도 한국어 에러 안내(0건과 구분).
//
// 보호: proxy가 /search 비로그인 1차 차단. 여기선 로그인 사용자(구매자·판매자 공통)가 on_sale을 본다.
//   별도 역할 게이트 없음 — on_sale은 RLS상 모두에게 공개라 구매자·판매자 모두 탐색 가능.
//
// ⚠️ FR11 이중 방어:
//   RLS는 구매자에게 on_sale만 통과시키지만, 판매자가 /search에 들어오면 RLS의 'own' 정책으로
//   본인 sold가 섞일 수 있다 → 앱 쿼리에 .eq('status','on_sale')을 명시해 "구매자 관점(판매중만)"을 강제.
//   (2-2/2-3에서 확립한 'SELECT RLS는 on_sale∪own∪admin OR결합'의 반대 방향 적용.)
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, LISTING_STATUS, LISTING_OPTIONS, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import SearchFilters, { type SearchFilterValues } from './SearchFilters';

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
  // status='on_sale' 명시(FR11). 조건은 값이 있을 때만 체이닝한다.
  let query = supabase
    .from('listings')
    .select('id, manufacturer, model, year, price, mileage, region')
    .eq('status', LISTING_STATUS.ON_SALE);

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

  const { data: listings, error } = await query.returns<ListingCardData[]>();

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
      <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} />
      <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
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
              <ul className="flex flex-col gap-2">
                {listings.map((l) => (
                  <li key={l.id}>
                    <ListingCard listing={l} />
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>
      </main>
    </>
  );
}
