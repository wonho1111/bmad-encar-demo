// 상세 섹션 조립 테스트 (Story 10.7, SM-C 통합 검증 — 상세 절반).
//
// 왜 필요한가: SM-C는 카드"와 상세" 두 표면에 걸쳐 있다. ListingCard.test.ts가 카드 조립을
// 잡지만, 상세 페이지에서 같은 두 거동(신뢰블록 마운트 + 옵션 그룹 렌더)을 조립하는 자리
// (TrustInfoSection·OptionsSection)에는 회귀 가드가 없었다 — 상세에서 <TrustAttributes
// variant="detail">를 지우거나 OptionsSection 그룹 렌더를 비워도 전 스위트 green이었다.
// 이 파일이 그 비대칭을 닫는다(카드 테스트의 상세 짝, 코드리뷰 2026-07-22 verification-gap).
//
// 기법·전제는 ListingCard.test.ts와 동일: node 환경에서 상태 없는 서버 컴포넌트를 순수 함수로
// 호출해 반환된 React 엘리먼트 트리(순수 객체)를 순회한다. Section·TrustAttributes 등 자식
// 컴포넌트는 확장되지 않는 {type, props} 노드로 남는다. ⚠️ TrustInfoSection/OptionsSection이
// async가 되거나 훅을 쓰게 되면 이 호출은 throw하므로 렌더 기반 하네스로 옮겨야 한다.
//
// 안 보는 것: 실제 브라우저 색·아이콘·섹션 시각 분리(E2E-only, 대장 #106) — Story 10.7 수동
// 실측이 담당. 뱃지-면책 결속·groupByCategory 분류 알고리즘은 TrustAttributes.test.ts·
// options.test.ts가 이미 커버하므로 여기선 "상세가 그 결과물들을 조립하는가"만 본다.
import { describe, expect, it } from 'vitest';
import TrustAttributes from '@/components/listings/TrustAttributes';
import {
  OptionsSection,
  TrustInfoSection,
  type ListingDetailSectionsData,
} from '../ListingDetailSections';

type ElementNode = { type: unknown; props?: { children?: unknown; [key: string]: unknown } };

function isElementNode(node: unknown): node is ElementNode {
  return typeof node === 'object' && node !== null && 'type' in node && 'props' in node;
}

// 트리 전체(children 포함)를 깊이우선으로 모은다 — ListingCard.test.ts의 collectNodes와 동일.
function collectNodes(node: unknown, out: ElementNode[] = []): ElementNode[] {
  if (node == null || typeof node === 'boolean') return out;
  if (Array.isArray(node)) {
    node.forEach((child) => collectNodes(child, out));
    return out;
  }
  if (isElementNode(node)) {
    out.push(node);
    collectNodes(node.props?.children, out);
  }
  return out;
}

// 텍스트 리프만 모은다 — 옵션 칩 문자열을 읽을 때 쓴다.
function collectText(node: unknown): string[] {
  if (node == null || typeof node === 'boolean') return [];
  if (typeof node === 'string' || typeof node === 'number') return [String(node)];
  if (Array.isArray(node)) return node.flatMap(collectText);
  if (isElementNode(node)) return collectText(node.props?.children);
  return [];
}

// FR5 필수 필드를 전부 채운 기준 매물(신뢰속성·옵션은 각 테스트가 덮어쓴다).
const BASE: ListingDetailSectionsData = {
  manufacturer: '현대',
  model: '쏘나타',
  body_type: '중형',
  year: 2021,
  price: 21_000_000,
  mileage: 42_000,
  color: '흰색',
  fuel: '가솔린',
  transmission: '자동',
  displacement: 1999,
  seats: 5,
  region: '서울',
  accident_free: true,
  options: null,
  description: null,
};

describe('상세 조립 — SM-C(상세에서 신뢰속성과 옵션이 구분·조립)', () => {
  it('신뢰 풀세트: TrustInfoSection이 <TrustAttributes variant="detail">를 마운트한다', () => {
    const listing: ListingDetailSectionsData = {
      ...BASE,
      accident_status: '무사고',
      is_single_owner: true,
      is_non_smoker: true,
    };

    const tree = TrustInfoSection({ listing });

    // 신뢰정보 섹션에서 <TrustAttributes variant="detail">를 지우면 이 단언이 red가 된다.
    const trustNodes = collectNodes(tree).filter((n) => n.type === TrustAttributes);
    expect(trustNodes).toHaveLength(1);
    expect(trustNodes[0].props?.variant).toBe('detail');
    expect(trustNodes[0].props?.listing).toBe(listing);
  });

  it('신뢰속성 전무(세 컬럼 null): TrustInfoSection은 null을 반환한다(빈 섹션 금지, AC1)', () => {
    const listing: ListingDetailSectionsData = {
      ...BASE,
      accident_status: null,
      is_single_owner: null,
      is_non_smoker: null,
    };

    // hasTrustAttributes가 false면 섹션 자체를 안 그린다 — 이 가드가 빠지면 빈 신뢰정보 카드가 뜬다.
    expect(TrustInfoSection({ listing })).toBeNull();
  });

  it('옵션 있음: OptionsSection이 옵션을 <li> 칩으로 렌더한다(희소 포함)', () => {
    const listing: ListingDetailSectionsData = {
      ...BASE,
      options: ['파노라마선루프', '블루투스', '후방카메라'],
    };

    const tree = OptionsSection({ listing });
    const text = collectText(tree);
    expect(text).toContain('파노라마선루프');
    expect(text).toContain('블루투스');

    // 옵션 칩은 <li> 노드로 조립된다 — 그룹 렌더를 비우면 <li>가 사라져 red가 된다.
    const liNodes = collectNodes(tree).filter((n) => n.type === 'li');
    expect(liNodes.length).toBeGreaterThanOrEqual(3);
  });

  it('옵션 없음: OptionsSection은 빈 안내 문구를 렌더하고 칩(<li>)은 없다', () => {
    const listing: ListingDetailSectionsData = { ...BASE, options: [] };

    const tree = OptionsSection({ listing });
    expect(collectText(tree).join('')).toContain('등록된 옵션이 없습니다');
    expect(collectNodes(tree).filter((n) => n.type === 'li')).toHaveLength(0);
  });
});
