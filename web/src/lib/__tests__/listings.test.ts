// 인기/최신 매물 그리드(Story 11.4)의 anon 정규화 단위테스트 (B9 "실행되는 검사").
//
// 이 파일이 검사하는 것:
//   `normalizeAnonTrustColumns` — anon(비로그인) 조회 결과에서 신뢰속성 3필드
//   (accident_status·is_single_owner·is_non_smoker)를 null로 강제하는 순수 함수.
//   I/O 매트릭스의 "비로그인, 매물 존재" 케이스(신뢰속성 3필드는 표시 안 됨=null)를 코드로 고정한다.
//
// **이 검사가 안 보는 것**: `fetchPopularAndRecentListings`의 실제 DB 조회(Supabase 쿼리 체인·
// attachCoverImages·anon 42501 회귀)는 여기서 mock하지 않는다 — 그 부분은 RLS·GRANT·인덱스에
// 기대는 통합 동작이라 로컬 Supabase 스택 + 브라우저 MCP로 손수 검증한다(Verification 절 참조).
import { describe, expect, it } from 'vitest';
import { normalizeAnonTrustColumns } from '../listings';
import type { ListingCardData } from '@/components/listings/ListingCard';

function row(overrides: Partial<ListingCardData> = {}): ListingCardData {
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
    options: null,
    ...overrides,
  };
}

describe('normalizeAnonTrustColumns', () => {
  it('authed=false면 신뢰속성 3필드를 null로 강제한다(값이 undefined로 온 경우)', () => {
    const rows = [row()]; // 신뢰속성 3필드 키 자체가 없음(anon select에서 아예 안 물었을 때와 동일 모양)
    const [normalized] = normalizeAnonTrustColumns(rows, false);
    expect(normalized.accident_status).toBeNull();
    expect(normalized.is_single_owner).toBeNull();
    expect(normalized.is_non_smoker).toBeNull();
  });

  it('authed=false면 값이 이미 채워져 있어도 null로 덮어쓴다(계약-외 값 방어)', () => {
    const rows = [
      row({ accident_status: '무사고', is_single_owner: true, is_non_smoker: false }),
    ];
    const [normalized] = normalizeAnonTrustColumns(rows, false);
    expect(normalized.accident_status).toBeNull();
    expect(normalized.is_single_owner).toBeNull();
    expect(normalized.is_non_smoker).toBeNull();
  });

  it('authed=true면 원래 값을 그대로 통과시킨다(로그인 사용자는 신뢰속성을 본다)', () => {
    const rows = [
      row({ accident_status: '단순교환', is_single_owner: true, is_non_smoker: null }),
    ];
    const [normalized] = normalizeAnonTrustColumns(rows, true);
    expect(normalized.accident_status).toBe('단순교환');
    expect(normalized.is_single_owner).toBe(true);
    expect(normalized.is_non_smoker).toBeNull();
  });

  it('나머지 필드는 그대로 보존한다(신뢰속성 3필드만 건드린다)', () => {
    const rows = [row({ id: 'L2', price: 20_000_000 })];
    const [normalized] = normalizeAnonTrustColumns(rows, false);
    expect(normalized.id).toBe('L2');
    expect(normalized.price).toBe(20_000_000);
    expect(normalized.manufacturer).toBe('현대');
  });

  it('빈 배열이면 빈 배열을 돌려준다', () => {
    expect(normalizeAnonTrustColumns([], false)).toEqual([]);
  });
});
