// 구매자 매물 가시성(FR11)의 단일 출처 — "구매자에게는 판매중(on_sale)만 보인다"는 규칙이
// 여기 한 곳에서만 정의된다. 목록(/search)·상세(/listings/[id]) 등 모든 구매자 경로가 이 헬퍼를
// 거치므로, 규칙을 바꿀 일이 생겨도 이 파일만 고치면 전 경로에 일관 적용된다(drift 방지).
//
// 왜 앱에서도 한 번 더 거르나(이중 방어):
//   DB의 RLS(supabase/migrations/0002_listings.sql)는 구매자에게 on_sale만 통과시키지만,
//   RLS는 "본인 매물(own)"·"관리자(admin)"도 함께 통과시킨다(OR 결합). 따라서 판매자가 본인 sold
//   매물의 구매자용 URL(/search·/listings/[id])에 들어오면 RLS 'own' 정책으로 sold가 새어들 수 있다.
//   그래서 앱 쿼리에 status='on_sale'을 명시해 "구매자 관점(판매중만)"을 강제한다(FR11 단일 규칙).
//   (근거: 0002_listings.sql:90-101, docs/conventions.md §6)
import type { SupabaseClient } from '@supabase/supabase-js';
import { LISTING_STATUS } from './constants';
import { coverImages, type ListingImageRow } from './images/coverImages';
import { galleryImages } from './images/galleryImages';
import { getPublicUrl } from './storage';
import { LISTING_IMAGES_BUCKET } from './storage/bucket';
import type { ListingCardData } from '@/components/listings/ListingCard';

// 구매자에게 노출 가능한 매물 상태 = 판매중(on_sale). 단일 상수(FR11 단일 출처).
export const BUYER_VISIBLE_STATUS = LISTING_STATUS.ON_SALE;

/**
 * 구매자 관점의 listings 조회 시작점.
 *   from('listings').select(columns).eq('status', 'on_sale') 까지 적용한 쿼리 빌더를 돌려준다.
 *   호출부는 이어서 .eq('id', …)·.ilike(…)·.order(…)·.maybeSingle()·.returns<…>() 등을 체이닝한다.
 * 이렇게 하면 "판매중만"이라는 FR11 규칙이 모든 구매자 경로에서 이 한 함수에서만 비롯된다.
 *
 * @param supabase  서버 Supabase 클라이언트(@/lib/supabase/server의 createClient 결과)
 * @param columns   select할 컬럼 문자열(경로마다 다르므로 인자로 받는다 — 목록은 요약 7필드, 상세는 15필드+status)
 */
export function buyerListingsQuery(supabase: SupabaseClient, columns: string) {
  return supabase
    .from('listings')
    .select(columns)
    .eq('status', BUYER_VISIBLE_STATUS);
}

/**
 * 매물 목록에 **대표사진 URL·사진 장수**를 채워 넣는다 (Story 9.4 AC2·3·5·9).
 *
 * `/search`와 홈 미리보기가 **같은 함수**를 쓴다 — 목록마다 따로 짜면 한쪽만 정렬을 빠뜨리거나
 * 대표를 다르게 골라 두 화면이 갈린다(9.3 코드리뷰의 교훈).
 *
 * 흐름:
 *   ① 이 페이지에 뜬 매물 id를 모아 `listing_images`를 **쿼리 한 번**으로 가져온다(N+1 금지)
 *   ② `coverImages`가 매물별 대표 경로·장수를 정한다(대표 판별의 유일한 자리)
 *   ③ `getPublicUrl`로 URL 문자열을 조립한다 — 공개 버킷이라 **네트워크 왕복 0회·만료 없음**(9.0)
 *
 * ⚠️ **정렬을 여기서 반드시 건다**(`sort_order` → `id`). `sort_order`에 tie-break가 없어서
 *    2차 키가 없으면 조회할 때마다 대표가 바뀐다(#59·#47-2). `coverImages`도 자체적으로 같은
 *    규칙으로 고르므로 둘 중 하나가 빠져도 결과는 같지만, **계약을 두 층에 다 박아 둔다**(B9).
 *
 * ⚠️ **조회 실패는 목록 전체를 막지 않는다** — 사진 없이 텍스트만 보이는 편이 빈 화면보다 낫다.
 *    실패하면 서버 로그에만 남기고 사진 자리는 플레이스홀더가 된다.
 */
// PostgREST GET 요청은 쿼리 문자열에 `.in()` 목록을 그대로 실어 보낸다. uuid 1개≈40바이트라
// 매물이 많아지면(대형 카탈로그) 게이트웨이의 요청 줄 길이 상한을 넘겨 414로 죽는다 — `/search`엔
// `.limit()`이 없어 실제로 벌어질 수 있는 크기다. 그래서 id 목록을 이 크기로 잘라 여러 번 나눠 쏜다.
const COVER_IMAGES_CHUNK_SIZE = 50;

function chunk<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) chunks.push(items.slice(i, i + size));
  return chunks;
}

export async function attachCoverImages<T extends { id: string }>(
  supabase: SupabaseClient,
  listings: T[],
): Promise<(T & { image_url: string | null; image_count: number })[]> {
  const withoutImages = () => listings.map((l) => ({ ...l, image_url: null, image_count: 0 }));

  if (listings.length === 0) return [];

  const idChunks = chunk(
    listings.map((l) => l.id),
    COVER_IMAGES_CHUNK_SIZE,
  );

  const results = await Promise.all(
    idChunks.map((ids) =>
      supabase
        .from('listing_images')
        .select('listing_id, storage_path, sort_order, id')
        .in('listing_id', ids)
        .order('sort_order', { ascending: true })
        .order('id', { ascending: true })
        .returns<ListingImageRow[]>(),
    ),
  );

  // 청크 하나가 실패해도 나머지 청크의 사진은 살린다 — 한 청크의 실패로 전체를 withoutImages()로
  // 떨어뜨리면, 대형 카탈로그에서 청크 하나만 어긋나도 페이지의 모든 카드가 사진을 잃는다(코드리뷰).
  // 실패한 청크에 속한 매물은 rows에 아무 행도 안 들어가므로 자연히 image_url:null로 떨어진다 —
  // 그 매물만 플레이스홀더가 되고 다른 청크는 영향받지 않는다.
  const rows: ListingImageRow[] = [];
  let successCount = 0;
  for (const { data, error } of results) {
    if (error || !data) {
      console.error('[listings] 대표사진 조회 실패(청크):', error);
      continue;
    }
    successCount += 1;
    rows.push(...data);
  }

  // 청크가 전부 실패한 경우에만 기존 폴백(전체 플레이스홀더)을 쓴다 — 부분 실패와 전체 실패를
  // 구분해야 "청크 하나 실패로 전부 잃는" 원래 버그를 다시 만들지 않는다.
  if (successCount === 0) return withoutImages();

  const covers = coverImages(rows);
  return listings.map((l) => {
    const cover = covers.get(l.id);
    return {
      ...l,
      image_url: cover ? getPublicUrl(LISTING_IMAGES_BUCKET, cover.coverPath) : null,
      image_count: cover?.count ?? 0,
    };
  });
}

/**
 * 매물 **1건**의 사진 전 장을 화면 순서대로 공개 URL 배열로 돌려준다 (Story 9.5 AC2·AC3).
 *
 * `attachCoverImages`와 왜 따로인가: 저건 목록용이라 매물마다 **대표 1장 + 장수**만 준다.
 * 상세 갤러리는 전 장이 필요하므로 형태 자체가 다르다 — 목록 함수를 억지로 재사용하면
 * 대표만 나오거나, 목록 전부의 사진을 다 끌어오게 된다.
 *
 * ⚠️ **FR11(판매완료 비노출)은 2층으로 지켜진다** — 어느 한 층에 기대지 않는다(`conventions.md` §6 이미지 축):
 *   ① **DB**: `listing_images` RLS(`listing_images_select_on_sale[_anon]`)가 `listings`에 조인해
 *      `status='on_sale'`을 건다 — sold 매물의 사진 행은 애초에 안 나온다.
 *   ② **호출부**: 상세 페이지가 `buyerListingsQuery`로 매물을 먼저 좁힌 뒤, 그 결과가 있을 때만
 *      이 함수를 부른다(`attachCoverImages`와 같은 방식). 매물이 sold면 여기까지 오지 않는다.
 *
 * ⚠️ **정렬은 쿼리와 순수 함수 양쪽에 다 건다**(`sort_order` → `id`). `sort_order`에 tie-break가
 *    없어서(#47-2) 2차 키가 빠지면 **새로고침마다 사진 순서가 바뀐다**(#59). 계약을 두 층에 박아
 *    한쪽이 빠져도 화면이 흔들리지 않게 한다(B9).
 *
 * ⚠️ **조회 실패는 상세 페이지 전체를 막지 않는다** — 사진 없이 정보만 보이는 편이 빈 화면보다 낫다.
 *    실패하면 서버 로그에만 남기고 갤러리 자리는 "사진 준비중" 플레이스홀더가 된다.
 *    ⚠️ 그 대가로 **"조회 실패"와 "정말 사진 0장"이 화면상 구별되지 않는다**(대장 #73의 3중 무음
 *    폴백 — 상세도 목록과 같은 구조를 그대로 상속한다). 해소는 관측 수단이 필요한 별건이다.
 *
 * ⚠️ `select`에 **`credit`을 넣지 않는다** — 저작자 표시는 하지 않기로 결정됐다(대장 #70 ⚪).
 *    필요한 컬럼만 명시하는 이유이기도 하다(`select *`면 안 쓰는 값이 딸려온다).
 */
export async function fetchListingGalleryUrls(
  supabase: SupabaseClient,
  listingId: string,
): Promise<string[]> {
  const { data, error } = await supabase
    .from('listing_images')
    .select('listing_id, storage_path, sort_order, id')
    .eq('listing_id', listingId)
    .order('sort_order', { ascending: true })
    .order('id', { ascending: true })
    .returns<ListingImageRow[]>();

  if (error || !data) {
    console.error('[listings] 상세 갤러리 사진 조회 실패:', error);
    return [];
  }

  return galleryImages(data).map((path) => getPublicUrl(LISTING_IMAGES_BUCKET, path));
}

// ── 인기/최신 매물 그리드 (Story 11.4, FR34) ──────────────────────────────

// 단당 발췌 개수. 근거는 목업(landing-1.html:604-726, 데스크톱 4열×카드 4장)이자 기존 홈
// 미리보기의 PREVIEW_COUNT와 동일값 — 새 상수를 도입하는 게 아니라 그 값을 그대로 옮겨온다.
const POPULAR_RECENT_GRID_COUNT = 4;

// 인기·최신 두 단이 공유하는 select 컬럼. 신뢰속성 3필드(accident_status·is_single_owner·
// is_non_smoker)는 로그인 사용자에게만 묻는다 — anon은 0011 화이트리스트에 그 컬럼이 없어
// select 자체가 42501로 죽는다(SearchPage의 trustColumns와 동일 이유, 동일 패턴).
function popularRecentColumns(authed: boolean): string {
  const trustColumns = authed ? ', accident_status, is_single_owner, is_non_smoker' : '';
  return `id, manufacturer, model, year, price, mileage, region, seller_name, fuel, options${trustColumns}`;
}

/**
 * anon(비로그인) 조회 결과에서 신뢰속성 3필드를 `null`로 명시 정규화한다(순수 함수 — DB 없이 테스트 가능).
 *
 * anon 경로는 위 `popularRecentColumns`가 애초에 그 3컬럼을 select하지 않으므로 값이 `undefined`
 * (키 자체가 없음)로 온다. 계약(ListingCardData)은 "값이 없으면 null"이지 "필드가 없음"이 아니다 —
 * `TrustAttributes`가 `undefined`와 `null`을 다르게 다루면 anon 렌더만 조용히 갈릴 수 있어, 여기서
 * 런타임 모양을 선언한 타입과 맞춘다. `SearchPage`의 `normalizedRows`와 같은 패턴(로직 이원화 금지 —
 * 그쪽은 페이지 안에 인라인으로 있고, 이 함수는 그 계약을 재사용 가능한 순수 함수로 뽑은 것).
 */
export function normalizeAnonTrustColumns(rows: ListingCardData[], authed: boolean): ListingCardData[] {
  if (authed) return rows;
  return rows.map((r) => ({
    ...r,
    accident_status: null,
    is_single_owner: null,
    is_non_smoker: null,
  }));
}

type CoverImaged<T> = T & { image_url: string | null; image_count: number };

// 한 단(인기 또는 최신)의 결과 — 조회 실패는 이 단만 error로 표시하고 다른 단·히어로·차종칩
// 렌더를 막지 않는다(intent-contract Always). 0건은 error가 아니라 빈 listings 배열로 구분된다.
export type PopularRecentSection =
  | { listings: CoverImaged<ListingCardData>[] }
  | { error: true };

export type PopularAndRecentListings = {
  popular: PopularRecentSection;
  recent: PopularRecentSection;
};

async function fetchSection(
  supabase: SupabaseClient,
  authed: boolean,
  orderColumn: 'view_count' | 'created_at',
  label: string,
): Promise<PopularRecentSection> {
  // try/catch로 감싼다 — Supabase 클라이언트가 {data,error}가 아니라 실제 예외(네트워크 단 등)를
  // 던지면 이 함수가 그대로 reject되고, 그걸 부르는 Promise.all(fetchPopularAndRecentListings)이
  // 통째로 터져 히어로·차종칩·본인정보까지 포함한 Home() 전체가 죽는다 — "이 단만 실패, 나머지는
  // 정상 렌더"라는 intent-contract Always 규칙을 이 함수 하나가 어길 수 있었다(코드리뷰 patch).
  try {
    const { data, error } = await buyerListingsQuery(supabase, popularRecentColumns(authed))
      .order(orderColumn, { ascending: false })
      .order('id', { ascending: false })
      .limit(POPULAR_RECENT_GRID_COUNT)
      .returns<ListingCardData[]>();

    if (error || !data) {
      console.error(`[listings] ${label} 매물 그리드 조회 실패:`, error);
      return { error: true };
    }

    const normalized = normalizeAnonTrustColumns(data, authed);
    const listings = await attachCoverImages(supabase, normalized);
    return { listings };
  } catch (err) {
    console.error(`[listings] ${label} 매물 그리드 조회 실패(예외):`, err);
    return { error: true };
  }
}

/**
 * 랜딩의 인기(view_count desc)·최신(created_at desc) 2단 발췌 그리드 데이터를 만든다 (Story 11.4, FR34).
 *
 * 두 쿼리는 병렬로 실행하고, 한쪽이 실패해도 다른 쪽·나머지 랜딩 렌더를 막지 않는다 — 각 단의
 * 성패를 독립적으로 반환해 호출부(`page.tsx`)가 단별로 에러 문구를 그릴 수 있게 한다.
 * `attachCoverImages`(9.4와 동일 함수)로 대표사진을 채우고, 찜 오버레이(`fetchWishedListingIds`)는
 * 사용자별 조회라 여기 포함하지 않는다 — 호출부가 두 단의 id를 합쳐 한 번만 조회한다.
 */
export async function fetchPopularAndRecentListings(
  supabase: SupabaseClient,
  user: { id: string } | null,
): Promise<PopularAndRecentListings> {
  const authed = !!user;
  const [popular, recent] = await Promise.all([
    fetchSection(supabase, authed, 'view_count', '인기'),
    fetchSection(supabase, authed, 'created_at', '최신'),
  ]);
  return { popular, recent };
}
