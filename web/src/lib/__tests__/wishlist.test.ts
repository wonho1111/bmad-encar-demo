// 찜(wishlist) 순수 로직 단위테스트 (Story 10.5 — B9 "실행되는 검사").
//
// 이 파일이 검사하는 것:
//   1) `isWishedListingBlocked` — on_sale/sold/null 3상태 판정식(찜 목록의 회색 처리 여부).
//   2) `buildWishedIdSet` — wishlists 행 배열 → 찜 id 집합 구성(카드 초기 상태 오버레이의 핵심 로직).
//
// **이 검사가 안 보는 것**: `fetchWishedListingIds`·`fetchWishlist`의 실제 DB 조회(Supabase 쿼리
// 체인)는 여기서 mock하지 않는다 — 그 부분은 순수 로직이 아니라 RLS·네트워크에 기대는 통합 동작이라
// 로컬 Supabase 스택으로 손수 검증한다(Story 문서의 red/green 실측 기록, Design Notes 참조).
import { describe, expect, it } from 'vitest';
import { buildWishedIdSet, isWishedListingBlocked, type WishlistListingEmbed } from '../wishlist';

function embed(overrides: Partial<NonNullable<WishlistListingEmbed>> = {}): NonNullable<WishlistListingEmbed> {
  return {
    id: 'L1',
    manufacturer: '현대',
    model: '아반떼',
    year: 2021,
    price: 15_000_000,
    mileage: 50_000,
    region: '서울',
    seller_name: '판매자',
    fuel: '가솔린',
    accident_status: null,
    is_single_owner: null,
    is_non_smoker: null,
    options: null,
    status: 'on_sale',
    ...overrides,
  };
}

describe('isWishedListingBlocked', () => {
  it('on_sale이면 false(정상 카드로 렌더)', () => {
    expect(isWishedListingBlocked(embed({ status: 'on_sale' }))).toBe(false);
  });

  it('sold면 true(회색 비활성 — 본인 소유 sold, RLS가 값을 보여준 경우)', () => {
    expect(isWishedListingBlocked(embed({ status: 'sold' }))).toBe(true);
  });

  it('null(embed 없음)이면 true(회색 비활성 — RLS가 막은 타인 소유 sold)', () => {
    expect(isWishedListingBlocked(null)).toBe(true);
  });

  // 코드리뷰 2026-07-22 P4: allowlist 판정 실측. status가 미상(undefined — select 드리프트)이거나
  // on_sale/sold 밖의 미래 값이면 "정상 클릭 카드로 새어나가지 않고" 차단(true)돼야 한다.
  it('status가 미상(undefined)이면 true(select 드리프트로 값이 안 실려도 기본 차단)', () => {
    expect(isWishedListingBlocked(embed({ status: undefined as unknown as 'on_sale' }))).toBe(true);
  });

  it('status가 on_sale/sold 밖의 미래 값이면 true(신규 status 추가 시에도 기본 차단)', () => {
    expect(isWishedListingBlocked(embed({ status: 'reserved' as unknown as 'on_sale' }))).toBe(true);
  });

  // red/green 실측(B4 "재보기 전엔 선언하지 않는다"): 판정식을 denylist(`=== 'sold'`)로 되돌리면
  // 위 두 신규 케이스(undefined·미래값)가 즉시 fail한다. 아래는 그 자리를 문서로 남긴 실측 절차 —
  // 실제로는 코드를 `return embed.status === 'sold';` 로 되돌려 이 두 테스트가 fail(red)하는 것을
  // 확인한 뒤 원상복구해 다시 pass(green)하는 것을 실행 로그로 검증했다(Verification 절 참조).
});

describe('buildWishedIdSet', () => {
  it('행이 없으면 빈 Set', () => {
    expect(buildWishedIdSet([])).toEqual(new Set());
  });

  it('listing_id들을 Set으로 모은다', () => {
    const set = buildWishedIdSet([{ listing_id: 'A' }, { listing_id: 'B' }]);
    expect(set.has('A')).toBe(true);
    expect(set.has('B')).toBe(true);
    expect(set.has('C')).toBe(false);
  });

  it('중복 listing_id는 하나로 합쳐진다(Set 특성)', () => {
    const set = buildWishedIdSet([{ listing_id: 'A' }, { listing_id: 'A' }]);
    expect(set.size).toBe(1);
  });
});
