// 판매자 정보 섹션 순수 헬퍼 단위테스트 (Story 10.6 — B9 "실행되는 검사").
//
// 이 파일이 검사하는 것:
//   1) `formatSellerJoinDate` — ISO 문자열 → "YYYY년 M월 가입"(null·빈 값·파싱 불가 문자열은 null).
//   2) `sellerOtherListingsLabel` — 집계 수 → "N건"/"없어요" 안내 문구 분기(null은 행 숨김용 null).
//
// **이 검사가 안 보는 것**: RPC(`get_seller_public_summary`, 0019)가 실제로 on_sale·현재 매물 제외
// 필터를 지키는지는 여기서 검사하지 않는다 — 그건 순수 함수가 아니라 DB 쿼리이므로 로컬 Supabase로
// anon 롤 임퍼소네이션해 손으로 실측한다(이 스토리의 Verification 절 참조).
import { describe, expect, it } from 'vitest';
import {
  formatSellerJoinDate,
  sellerOtherListingsLabel,
  SellerInfoSection,
} from '../ListingDetailSections';

// React 엘리먼트 트리(문자열·배열·{props:{children}} 노드)에서 텍스트 리프를 전부 모은다.
// jsdom·렌더러 없이 "이 텍스트가 트리 안에 실제로 있는가"를 확인하는 유일한 방법 —
// SellerInfoSection은 훅 없는 순수 함수 컴포넌트라 함수로 직접 호출하면 순수 객체 그래프가 반환된다
// (TrustAttributes.test.ts와 같은 전제·같은 헬퍼).
function collectText(node: unknown): string[] {
  if (node == null || typeof node === 'boolean') return [];
  if (typeof node === 'string' || typeof node === 'number') return [String(node)];
  if (Array.isArray(node)) return node.flatMap(collectText);
  if (typeof node === 'object' && 'props' in (node as Record<string, unknown>)) {
    const { children } = (node as { props?: { children?: unknown } }).props ?? {};
    return collectText(children);
  }
  return [];
}

describe('formatSellerJoinDate', () => {
  it('ISO 문자열을 "YYYY년 M월 가입"으로 포맷한다', () => {
    expect(formatSellerJoinDate('2024-03-15T00:00:00Z')).toBe('2024년 3월 가입');
  });

  it('월이 두 자리(예: 11월)여도 그대로 표시한다(0패딩 없음)', () => {
    expect(formatSellerJoinDate('2023-11-01T00:00:00Z')).toBe('2023년 11월 가입');
  });

  it('null이면 null(행 숨김)', () => {
    expect(formatSellerJoinDate(null)).toBeNull();
  });

  it('undefined면 null(anon select 드리프트 대비)', () => {
    expect(formatSellerJoinDate(undefined)).toBeNull();
  });

  it('빈 문자열이면 null', () => {
    expect(formatSellerJoinDate('')).toBeNull();
  });

  it('파싱 불가한 문자열이면 null(깨진 Date 렌더 방지)', () => {
    expect(formatSellerJoinDate('not-a-date')).toBeNull();
  });

  // 코드리뷰 2026-07-22 패치1: UTC 자정 경계값 — KST(+9)로 보면 다음날 08시라 3월로 넘어간다.
  // 런타임 로컬 타임존(getFullYear/getMonth)으로 읽으면 UTC 그대로 "2월"이 되어 틀린다.
  it('UTC 자정 경계값도 KST 기준으로 정확히 표시한다(타임존 고정, 런타임 로컬값 아님)', () => {
    expect(formatSellerJoinDate('2024-02-29T23:00:00Z')).toBe('2024년 3월 가입');
  });
});

describe('sellerOtherListingsLabel', () => {
  it('N건 있으면 "이 판매자의 다른 판매중 매물 N건"', () => {
    expect(sellerOtherListingsLabel(2)).toBe('이 판매자의 다른 판매중 매물 2건');
  });

  it('0건이면 "없어요" 안내 문구(I/O 매트릭스 — "다른 매물 없음")', () => {
    expect(sellerOtherListingsLabel(0)).toBe('이 판매자의 다른 판매중 매물이 없어요.');
  });

  it('큰 수는 천단위 콤마로 표시한다(conventions §3 단위 표기 관례)', () => {
    expect(sellerOtherListingsLabel(1234)).toBe('이 판매자의 다른 판매중 매물 1,234건');
  });

  it('null이면 null(RPC 조회 실패 — 집계 행 숨김)', () => {
    expect(sellerOtherListingsLabel(null)).toBeNull();
  });

  it('undefined면 null(anon select 드리프트 대비)', () => {
    expect(sellerOtherListingsLabel(undefined)).toBeNull();
  });
});

// 렌더 레이어 결속(follow-up 코드리뷰 2026-07-22) — 위 두 블록은 순수 헬퍼의 "문자열 생성"만 본다.
// 컴포넌트 JSX에서 "값이 전부 없으면 섹션째 숨김" 가드(`!sellerName && !joinLabel && !otherLabel`)를
// `||`로 뒤집거나 특정 행 <p>를 지워도(헬퍼는 멀쩡하니) 위 블록은 계속 green이다. 이 블록은
// SellerInfoSection을 함수로 직접 호출해 실제 반환 트리를 순회하며, I/O 매트릭스의 조립 시나리오
// (닉네임 행만 숨김 · 값 전무 시 섹션 숨김)를 렌더 계층에서 고정한다(TrustAttributes.test.ts와 같은 규율).
describe('SellerInfoSection 렌더 트리 — I/O 매트릭스 조립 시나리오', () => {
  it('세 값이 다 있으면 닉네임·가입월·N건이 트리에 함께 있다', () => {
    const element = SellerInfoSection({
      sellerName: '카매니아',
      joinedAt: '2024-03-15T00:00:00Z',
      otherOnSaleCount: 2,
    });
    const text = collectText(element).join(' ');
    expect(text).toContain('카매니아');
    expect(text).toContain('2024년 3월 가입');
    expect(text).toContain('이 판매자의 다른 판매중 매물 2건');
  });

  it('닉네임 없음(seller_name=null) → 닉네임 행만 숨기고 가입월·집계는 그대로 렌더', () => {
    const element = SellerInfoSection({
      sellerName: null,
      joinedAt: '2023-11-01T00:00:00Z',
      otherOnSaleCount: 0,
    });
    const text = collectText(element).join(' ');
    expect(element).not.toBeNull(); // 섹션은 그대로 렌더된다(닉네임만 빠짐)
    expect(text).toContain('2023년 11월 가입');
    expect(text).toContain('이 판매자의 다른 판매중 매물이 없어요.');
  });

  it('세 값이 다 없으면(닉네임 null + RPC 실패로 가입·집계 null) 섹션째 null을 반환한다(빈 슬롯 금지)', () => {
    // 이 가드(`!sellerName && !joinLabel && !otherLabel`)를 `||`로 뒤집으면 여기가 red가 된다 —
    // 빈 "판매자정보" 제목만 뜨는 경로(의미 없는 잉크)를 이 줄이 막는다.
    expect(
      SellerInfoSection({ sellerName: null, joinedAt: null, otherOnSaleCount: null }),
    ).toBeNull();
    expect(
      SellerInfoSection({ sellerName: undefined, joinedAt: undefined, otherOnSaleCount: undefined }),
    ).toBeNull();
  });
});
