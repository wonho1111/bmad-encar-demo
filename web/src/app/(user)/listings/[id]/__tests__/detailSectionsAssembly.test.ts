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

    const tree = TrustInfoSection({ listing, authed: true });

    // 신뢰정보 섹션에서 <TrustAttributes variant="detail">를 지우면 이 단언이 red가 된다.
    const trustNodes = collectNodes(tree).filter((n) => n.type === TrustAttributes);
    expect(trustNodes).toHaveLength(1);
    expect(trustNodes[0].props?.variant).toBe('detail');
    expect(trustNodes[0].props?.listing).toBe(listing);
  });

  // ✎ 2026-08-13 사용자 지적으로 계약이 **뒤집혔다.** 예전엔 신뢰속성이 하나도 없으면 섹션을
  //   통째로 안 그렸는데(AC1 "빈 섹션 금지"), 그러면 "이 차 무사고인가?"에 화면이 아무 말도 안
  //   하는 상태가 된다. 이제 섹션은 항상 그리되 **"없음"의 이유를 구분해서** 말한다:
  //     · 로그인 사용자 → 판매자가 입력을 안 한 것이다.
  //     · 비로그인 → 애초에 그 컬럼을 조회하지 않았다(0011 anon GRANT 목록 밖). 여기에
  //       "판매자가 입력하지 않았어요"를 쓰면 값이 **있는** 매물에도 그렇게 보인다 = 거짓말.
  //   두 문구가 섞이면 조용히 틀리므로, 두 분기를 각각 단언한다.
  const EMPTY_TRUST: ListingDetailSectionsData = {
    ...BASE,
    accident_status: null,
    is_single_owner: null,
    is_non_smoker: null,
  };

  it('신뢰속성 전무 + 로그인: 섹션은 그리되 "판매자가 입력하지 않았다"고 말한다', () => {
    const tree = TrustInfoSection({ listing: EMPTY_TRUST, authed: true });
    expect(tree, '섹션이 통째로 사라지면 안 된다').not.toBeNull();

    // 제목은 남는다 — 다만 `Section`은 이 하네스에서 **확장되지 않는 컴포넌트 노드**라 제목이
    // 텍스트 리프로 안 잡힌다(collectText는 확장된 트리만 훑는다). 루트 노드의 title prop을 직접 본다.
    expect(isElementNode(tree) ? tree.props?.title : undefined).toBe('신뢰정보');

    const text = collectText(tree).join(' ');
    expect(text).toContain('판매자가');
    expect(text).not.toContain('로그인'); // 조회 못 한 게 아니라 판매자가 안 넣은 것이다

    // 값이 없으므로 뱃지 컴포넌트는 마운트하지 않는다(빈 뱃지 줄이 남지 않게).
    expect(collectNodes(tree).filter((n) => n.type === TrustAttributes)).toHaveLength(0);
  });

  it('신뢰속성 전무 + 비로그인: "판매자가 입력 안 함"이 아니라 "로그인 후 볼 수 있다"고 말한다', () => {
    const tree = TrustInfoSection({ listing: EMPTY_TRUST, authed: false });
    expect(tree).not.toBeNull();

    const text = collectText(tree).join(' ');
    expect(text).toContain('로그인');
    expect(
      text,
      'anon에게 "판매자가 입력하지 않았어요"라고 하면 값이 있는 매물에도 그렇게 보인다(거짓)',
    ).not.toContain('판매자가');
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
