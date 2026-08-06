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
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, LISTING_OPTIONS, type UserRole } from '@/lib/constants';
import { buyerListingsQuery, attachCoverImages } from '@/lib/listings';
import { fetchWishedListingIds } from '@/lib/wishlist';
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

// 한 페이지에 보여줄 매물 수 (대장 DW-542 해소, 2026-07-29).
// **왜 24인가:** D5 그리드가 ≥1100px에서 4열·640~1099px에서 2열이라, 4와 2의 공배수여야 마지막 줄이
// 어중간하게 비지 않는다(24 = 4열×6줄 = 2열×12줄 = 1열×24개). 12는 한 화면에 너무 적고 48은
// 사진 무게(장당 150~190KB, DW-541)를 그대로 되돌린다.
//
// **왜 페이지네이션이 필요했나(실측 2026-07-29):** 이 목록엔 `.limit()`이 없어 판매중 매물
// **전량 93건**을 한 페이지에 그렸다 — HTML 압축 전 320KB + 사진 90장. 사진 캐시까지 꺼져 있어
// (DW-541) 방문할 때마다 그 전부를 새로 받았다.
const PAGE_SIZE = 24;

// URL의 `page`를 1 이상 정수로 정규화한다. 없거나 이상한 값이면 1(첫 페이지)로 떨어진다 —
// 필터 파싱과 같은 방침(계약 밖 값은 조용히 무시, 에러 화면으로 만들지 않는다).
function asPage(v: string): number {
  const n = asInt(v);
  return n !== null && n >= 1 ? n : 1;
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
  const page = asPage(asStr(sp.page)); // 1-기반. 필터와 달리 항상 값이 있다(기본 1).
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
  // options는 이미 0011에서 anon GRANT돼 있다(로그인 분기 불필요, conventions §11 — 10.1
  // 신뢰컬럼과 다른 점). 그래서 trustColumns와 달리 로그인 여부와 무관하게 항상 조회한다.
  // SearchFilters에 넘길 초기값(현재 URL 그대로 폼에 반영 → 새로고침해도 유지).
  //   조회보다 **먼저** 만든다 — 아래 "마지막 페이지로 되돌리기"가 pageHref를 쓰는데, 그게 이 값을 읽는다.
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

  // 페이지 이동 링크 — **정규화된 필터값**으로 쿼리를 다시 조립한다(원본 sp를 그대로 옮기지 않는다).
  //   그래야 목록 밖 값·중복 키·모르는 파라미터가 페이지를 넘길 때마다 따라다니지 않는다
  //   (위 pickOption/asInt가 이미 무시한 값을 URL에만 남겨두면 화면과 주소가 어긋난다).
  //   page=1은 아예 안 붙인다 — 첫 페이지 주소를 지금과 똑같이 유지해 기존 링크·북마크가 안 깨진다.
  //   ※ 필터를 다시 적용하면 SearchFilters가 자기 필드로만 URL을 새로 만들므로 page는 자연히
  //     떨어져 1페이지로 돌아간다(별도 리셋 코드 불필요).
  function pageHref(target: number): string {
    const params = new URLSearchParams();
    for (const [key, value] of Object.entries(initialFilters)) {
      if (value !== '') params.set(key, value);
    }
    if (target > 1) params.set('page', String(target));
    const query = params.toString();
    return query ? `/search?${query}` : '/search';
  }

  // 필터 체이닝을 함수로 뽑는다 — 범위 밖 page를 마지막 페이지로 되돌릴 때(아래) **같은 조건**으로
  // 총 건수를 다시 물어야 하는데, 조건을 두 번 적으면 한쪽만 고쳐져 갈린다(단일 출처).
  // 제네릭 대신 넘겨받은 빌더를 그대로 돌려주는 얇은 함수다 — 타입은 호출부에서 추론된다.
  function applyFilters<T extends {
    ilike: (c: string, p: string) => T;
    eq: (c: string, v: string) => T;
    gte: (c: string, v: number) => T;
    lte: (c: string, v: number) => T;
  }>(builder: T): T {
    let b = builder;
    if (q) b = b.ilike('model', `%${escapeLike(q)}%`); // 모델명 부분일치(대소문자 무시, LIKE 메타문자 이스케이프)
    if (bodyType) b = b.eq('body_type', bodyType);
    if (color) b = b.eq('color', color);
    if (fuel) b = b.eq('fuel', fuel);
    if (transmission) b = b.eq('transmission', transmission);
    if (region) b = b.eq('region', region);
    // 가격·연식 범위 — 위에서 역전(min>max) 입력은 이미 swap으로 보정했으므로 여기선 그대로 적용한다.
    // 한쪽만 있으면 그 한쪽만 적용(min만→이상, max만→이하).
    if (priceMin !== null) b = b.gte('price', priceMin);
    if (priceMax !== null) b = b.lte('price', priceMax);
    if (yearMin !== null) b = b.gte('year', yearMin);
    if (yearMax !== null) b = b.lte('year', yearMax);
    return b;
  }

  // count:'exact' — 총 건수를 **같은 응답**의 Content-Range로 받는다(왕복 증가 없음, DW-542).
  const query = applyFilters(
    buyerListingsQuery(
      supabase,
      `id, manufacturer, model, year, price, mileage, region, seller_name, fuel, options${trustColumns}`,
      { count: 'exact' },
    ),
  )
    // created_at 내림차순. 시드처럼 created_at이 같은 행들의 순서가 새로고침마다 뒤집히지 않도록
    // id를 2차 정렬키로 둔다(안정적·결정적 정렬).
    .order('created_at', { ascending: false })
    .order('id', { ascending: false });

  // 이 페이지 몫만 잘라 온다(DW-542). range는 양끝 포함이라 끝값은 -1 한다.
  //   ⚠️ **정렬을 건 뒤에 range를 건다** — 순서가 뒤바뀌면 "아무 24건"을 잘라 정렬하는 꼴이 된다.
  const from = (page - 1) * PAGE_SIZE;
  const { data: rows, error, count } = await query
    .range(from, from + PAGE_SIZE - 1)
    .returns<ListingCardData[]>();

  const totalCount = count ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalCount / PAGE_SIZE));

  // 범위를 벗어난 page는 **빈 결과가 아니라 에러로 온다** — 실측(2026-07-29, `?page=99`):
  //   PGRST103 "Requested range not satisfiable / An offset of 2352 was requested, but there are
  //   only 95 rows." 즉 착수 전 가정("0행으로 돌아온다")이 틀렸다.
  //
  // **마지막 페이지로 보낸다**(사용자 요청 2026-07-29 — 안내문을 읽히는 것보다 원하던 곳에 데려다
  // 놓는 게 낫다). 총 건수는 이 응답에 없으므로(에러라 count가 null) **같은 필터로 개수만** 다시
  // 묻는다 — `head: true`라 행은 안 받아 가볍고, 손으로 주소를 고친 드문 길에서만 도는 왕복이다.
  // 정상 경로엔 아무 비용도 붙지 않는다.
  //
  // ⚠️ `last < page`일 때만 보낸다 — 두 조회 사이에 매물이 늘어 last가 page 이상이 되는 경합에서
  //   같은 자리로 무한히 되돌려 보내지 않게 하는 정지 조건이다(엄격히 작아지므로 반드시 끝난다).
  //   그 경합에 걸리면 리다이렉트 없이 아래 안내문으로 떨어진다(막다른 길은 안 만든다).
  const rangeOutOfBounds = error?.code === 'PGRST103';
  if (rangeOutOfBounds) {
    const { count: totalOnly } = await applyFilters(
      buyerListingsQuery(supabase, 'id', { count: 'exact', head: true }),
    );
    const lastPage = Math.max(1, Math.ceil((totalOnly ?? 0) / PAGE_SIZE));
    if (lastPage < page) {
      redirect(pageHref(lastPage)); // redirect()는 throw하므로 아래로 진행되지 않는다.
    }
  }

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

  // 찜 오버레이(Story 10.5) — ListingCardData wire 필드가 아니라 사용자별 별도 조회다(conventions §4).
  //   /search는 anon도 여는 열람 경로라 로그인일 때만 조회한다(비로그인은 항상 빈 Set = 전부 미찜).
  const wishedIds = user && listings
    ? await fetchWishedListingIds(supabase, user.id, listings.map((l) => l.id))
    : new Set<string>();

  if (error && !rangeOutOfBounds) {
    // 원본은 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분(AC2).
    // 범위 밖 page(PGRST103)는 사용자가 주소를 고친 결과지 장애가 아니므로 에러 로그를 남기지 않는다
    // — 남기면 진짜 장애가 그 소음에 묻힌다.
    console.error('[search] 매물 목록 조회 실패:', error);
  }

  // hover:border-brand-petrol(DW-699와 동일 근거, 코드리뷰 patch) — DW-696 토큰 치환 과정에서 옛
  // 원시색 호버(라이트/다크 각각의 회색 배경)를 `hover:bg-surface-raised` 하나로 바꿨는데, 이 페이저는
  // 카드가 아니라 body 배경(--surface-base #FAFAF8) 위에 바로 놓인 칩이라 호버가 #FFFFFF로 가도
  // 대비 1.045:1 — 같은 커밋이 DW-699로 "죽은 호버"라 판정해 걷어낸 바로 그 조합이었다. 게다가
  // 다크 모드 호버는 치환 과정에서 대응 클래스가 사라져 신호가 0이 됐다. 테두리 축으로 바꾼 뒤
  // 실측: 라이트 1.045:1 → 4.69:1, 다크 1.147:1 → 3.88:1(WCAG relative luminance).
  //
  // 활성/비활성을 **다른 상수로 나눈다**(코드리뷰 patch). 원래 하나를 양쪽이 같이 썼는데, 호버를
  // 눈에 띄게(1.045:1 → 4.69:1) 고친 순간 첫/끝 페이지의 **비활성** "← 이전"·"다음 →"까지 같이
  // 반짝이게 됐다 — 눌러도 아무 일이 없는 자리에 "누를 수 있다"는 신호를 준 셈이다. 호버가 사실상
  // 안 보이던 때는 드러나지 않던 문제라, 대비를 고친 그 patch가 만들어낸 결과다.
  const pagerBaseClass = 'rounded border border-border-hairline px-3 py-1.5 text-sm';
  const pagerLinkClass =
    'rounded border border-border-hairline px-3 py-1.5 text-sm hover:border-brand-petrol';

  return (
    <>
      <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} currentPath="/search" />
      {/* max-w-3xl(768px)이면 4열 브레이크포인트(≥1100px)에 도달해도 칸이 안 생긴다 —
          D5의 4열을 실제로 보이게 하려면 본문 폭도 함께 열어야 한다(Story 9.4 AC6). */}
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
        <section className="flex flex-col gap-1">
          {/* 제목은 이 화면에 들어오는 내비 링크("내 차 사기")와 같은 말을 쓴다 — EXPERIENCE.md
              Anti-patterns가 **"매물 탐색"·"탐색"을 개발용어 라벨로 명시 금지**하는데(소비자
              자연어로 치환), 내비만 고치고 도착 화면 제목이 옛 라벨로 남아 있었다. */}
          <h1 className="text-2xl font-semibold">내 차 사기</h1>
          <p className="text-sm text-ink-muted">
            원하는 조건으로 판매 중인 매물을 검색하세요.
          </p>
        </section>

        <SearchFilters initial={initialFilters} />

        <section className="flex flex-col gap-3">
          {rangeOutOfBounds ? (
            // 범위 밖 page — 에러가 아니라 "돌아갈 길"을 준다(위 rangeOutOfBounds 주석 참조).
            <p className="text-sm text-ink-muted">
              이 페이지에는 매물이 없습니다.{' '}
              <Link href={pageHref(1)} className="underline">
                첫 페이지로
              </Link>
            </p>
          ) : error ? (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              매물 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
            </p>
          ) : !listings || listings.length === 0 ? (
            <p className="text-sm text-ink-muted">
              조건에 맞는 매물이 없습니다. 필터를 완화해 보세요.
            </p>
          ) : (
            <>
              {/* 총 건수는 **전체**를 말한다(이 페이지에 그린 수가 아니라) — 페이지네이션 후에도
                  "조건에 몇 건이 걸렸나"는 전체 기준이어야 필터를 조절할 근거가 된다. */}
              <p className="text-sm text-ink-muted">
                {totalCount}건의 매물
                {totalPages > 1 && ` · ${page}/${totalPages} 페이지`}
              </p>
              {/* D5: 가로폭은 **열 수로만** 흡수한다(≥1100px 4열 · 640~1099px 2열 · <640px 1열).
                  카드 내부 가로 배치는 어느 폭에서도 접히지 않는다 — 규칙은 ResponsiveGrid가 소유. */}
              <ResponsiveGrid>
                {listings.map((l) => (
                  <ListingCard key={l.id} listing={l} wished={wishedIds.has(l.id)} authed={!!user} />
                ))}
              </ResponsiveGrid>

              {/* 페이지 이동 — 한 페이지뿐이면 아예 렌더하지 않는다(빈 잉크 금지, Story 8.2 AC1).
                  링크(<a>)라서 자바스크립트 없이도 동작하고, 주소가 그대로 공유·북마크된다. */}
              {totalPages > 1 && (
                <nav aria-label="페이지 이동" className="flex items-center justify-center gap-3 pt-2">
                  {page > 1 ? (
                    <Link href={pageHref(page - 1)} rel="prev" className={pagerLinkClass}>
                      ← 이전
                    </Link>
                  ) : (
                    // 첫/끝 페이지에서 버튼을 지우지 않고 비활성으로 남긴다 — 자리가 사라지면
                    // 옆 버튼이 움직여 연속 클릭이 어긋난다(터치에서 특히).
                    <span aria-disabled className={`${pagerBaseClass} opacity-40`}>
                      ← 이전
                    </span>
                  )}
                  <span aria-current="page" className="text-sm text-ink-muted">
                    {page} / {totalPages}
                  </span>
                  {page < totalPages ? (
                    <Link href={pageHref(page + 1)} rel="next" className={pagerLinkClass}>
                      다음 →
                    </Link>
                  ) : (
                    <span aria-disabled className={`${pagerBaseClass} opacity-40`}>
                      다음 →
                    </span>
                  )}
                </nav>
              )}
            </>
          )}
        </section>
      </main>
    </>
  );
}
