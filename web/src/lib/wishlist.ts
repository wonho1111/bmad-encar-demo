// 찜(wishlist) 서버 조회 헬퍼 + 순수 술어 (Story 10.5).
//
// 찜 여부는 ListingCard wire 필드가 아니다(docs/conventions.md §4·65) — "내가 찜했는지"는
// 사용자별 오버레이라 이 파일이 별도 조회로 다룬다(계약 오염 방지). 클라이언트 mutation
// (insert/delete 토글)은 이 파일에 두지 않는다 — WishButton.tsx가 얇게 인라인으로 처리한다
// (헬퍼 하나 더 두면 그게 더 무겁다, A2).
import type { SupabaseClient } from '@supabase/supabase-js';
import { LISTING_STATUS } from './constants';

// 찜 목록 조회 시 listings에서 함께 가져오는 카드용 컬럼 + status(찜 목록 전용 — 판매완료 판정에 필요).
// ListingCardData(components/listings/ListingCard.tsx)의 구조적 상위집합이라, 이 타입 값을 그대로
// <ListingCard listing={...}> 에 넘길 수 있다(구조적 타이핑, 별도 매핑 불필요).
export type WishlistListingEmbed = {
  id: string;
  manufacturer: string;
  model: string;
  year: number;
  price: number;
  mileage: number;
  region: string;
  seller_name: string | null;
  fuel: string | null;
  accident_status: '무사고' | '단순교환' | '사고' | null;
  is_single_owner: boolean | null;
  is_non_smoker: boolean | null;
  options: string[] | null;
  status: 'on_sale' | 'sold';
} | null; // RLS가 막으면(타인 소유 + sold) PostgREST가 embed를 null로 돌려준다.

export type WishlistEntry = {
  listing_id: string;
  created_at: string;
  listings: WishlistListingEmbed;
};

const WISHLIST_LISTING_COLUMNS =
  'id, manufacturer, model, year, price, mileage, region, seller_name, fuel, ' +
  'accident_status, is_single_owner, is_non_smoker, options, status';

/**
 * 주어진 wishlists 행들에서 찜 id 집합을 만드는 순수 함수(테스트 대상 — wishlist.test.ts).
 * `fetchWishedListingIds`가 이 함수를 감싸 DB 조회를 붙인다.
 */
export function buildWishedIdSet(rows: { listing_id: string }[]): Set<string> {
  return new Set(rows.map((r) => r.listing_id));
}

/**
 * 주어진 매물 id 목록 중 "본인이 찜한" id 집합을 구한다 — 카드 렌더 시 하트 초기 상태(`wished`)에 쓴다.
 * RLS(`wishlists_select_own`)가 본인 행만 돌려주므로 `.eq('user_id', userId)`는 이중 방어(0002/0011과
 * 같은 원칙 — 앱 쿼리에서도 조건을 명시해 RLS 한 겹에만 기대지 않는다).
 *
 * 조회 실패는 "찜 0건"과 같은 결과(빈 Set)로 처리한다 — 오버레이 실패로 카드 렌더 전체를 막지 않는다
 * (attachCoverImages와 같은 방침, @/lib/listings).
 */
export async function fetchWishedListingIds(
  supabase: SupabaseClient,
  userId: string,
  listingIds: string[],
): Promise<Set<string>> {
  if (listingIds.length === 0) return new Set();

  const { data, error } = await supabase
    .from('wishlists')
    .select('listing_id')
    .eq('user_id', userId)
    .in('listing_id', listingIds);

  if (error || !data) {
    console.error('[wishlist] 찜 오버레이 조회 실패:', error);
    return new Set();
  }
  return buildWishedIdSet(data);
}

/**
 * 본인 찜 목록을 최신순(찜한 시각 내림차순)으로 매물 카드 컬럼과 함께 조회한다 (`/wishlist` 페이지 전용).
 *
 * `listings` 임베드가 `null`로 오는 경우 — **RLS가 막은 것이지 조회 실패가 아니다.** 타인 소유의
 * sold 매물은 listings SELECT RLS(0002 `listings_select_on_sale`/`listings_select_own`) 어디에도
 * 안 걸려 embed가 null로 온다. 본인 소유 sold 매물은 `listings_select_own`이 계속 보여주므로
 * status='sold'로 값이 채워져 온다. 두 경우 다 `isWishedListingBlocked`가 걸러 회색 처리한다.
 * (하드삭제된 매물의 찜 행은 cascade로 이미 사라져 여기 나타나지 않는다 — Design Notes 참조.)
 */
export async function fetchWishlist(
  supabase: SupabaseClient,
  userId: string,
): Promise<{ entries: WishlistEntry[] } | { error: true }> {
  const { data, error } = await supabase
    .from('wishlists')
    .select(`listing_id, created_at, listings(${WISHLIST_LISTING_COLUMNS})`)
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .returns<WishlistEntry[]>();

  if (error || !data) {
    console.error('[wishlist] 찜 목록 조회 실패:', error);
    return { error: true };
  }
  return { entries: data };
}

/**
 * 찜 목록에서 이 매물을 "회색 + 판매완료 비활성"으로 그려야 하는지 판정하는 순수 술어.
 * embed=null(RLS가 막음, 타인 소유 sold) 또는 status가 on_sale이 아니면(sold·undefined·미래에
 * 생길 제3의 상태 전부 포함) ⟹ true. **allowlist**로 판정한다 — "sold일 때만 차단"(denylist)이면
 * select 문자열 드리프트로 status가 안 실려 오거나(undefined) 훗날 3번째 상태가 생겼을 때 "정상
 * 클릭 카드"로 새어나간다(FR11 "기본 차단" 정신 — 코드리뷰 2026-07-22 P4). on_sale이 명시적으로
 * 확인될 때만 false(정상 카드로 렌더).
 */
export function isWishedListingBlocked(embed: WishlistListingEmbed): boolean {
  if (!embed) return true;
  return embed.status !== LISTING_STATUS.ON_SALE;
}
