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
import { getPublicUrl } from './storage';
import { LISTING_IMAGES_BUCKET } from './storage/bucket';

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
export async function attachCoverImages<T extends { id: string }>(
  supabase: SupabaseClient,
  listings: T[],
): Promise<(T & { image_url: string | null; image_count: number })[]> {
  const withoutImages = () => listings.map((l) => ({ ...l, image_url: null, image_count: 0 }));

  if (listings.length === 0) return [];

  const { data, error } = await supabase
    .from('listing_images')
    .select('listing_id, storage_path, sort_order, id')
    .in(
      'listing_id',
      listings.map((l) => l.id),
    )
    .order('sort_order', { ascending: true })
    .order('id', { ascending: true })
    .returns<ListingImageRow[]>();

  if (error || !data) {
    console.error('[listings] 대표사진 조회 실패:', error);
    return withoutImages();
  }

  const covers = coverImages(data);
  return listings.map((l) => {
    const cover = covers.get(l.id);
    return {
      ...l,
      image_url: cover ? getPublicUrl(LISTING_IMAGES_BUCKET, cover.coverPath) : null,
      image_count: cover?.count ?? 0,
    };
  });
}
