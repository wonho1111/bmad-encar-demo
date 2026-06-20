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
