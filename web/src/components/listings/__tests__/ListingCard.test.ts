// ListingCard 조립 테스트 (Story 10.7, SM-C 통합 검증).
//
// 왜 새로 필요한가(중복 아님, 스펙 Design Notes): 뱃지-면책 결속(TrustAttributes.test.ts)과
// 희소 우선 랭킹(options.test.ts)은 이미 단위테스트가 커버한다. 하지만 "카드가 그 둘을 실제로
// **별개 블록으로 조립**한다"는 어떤 테스트도 안 본다 — ListingCard를 건드리는 테스트가 0개였다
// (조사 실측). 카드에서 <TrustAttributes>를 통째로 빼거나 topOptions 호출을 지워도 전 스위트
// green이었던 회귀를 이 파일이 잡는다(B9 "규칙은 어길 수 없는 자리에 박는다").
//
// 왜 .test.ts(jsdom 없이)인가: TrustAttributes.test.ts와 같은 이유 — vitest.config.ts는 node
// 환경이고(project-context 규칙12), ListingCard는 훅을 쓰지 않는 상태 없는 함수 컴포넌트라
// **함수로 직접 호출**하면 React 엘리먼트 트리(순수 객체)가 그대로 반환된다. 자식으로 쓰인
// <TrustAttributes>·<WishButton>·<ListingCardImage>·next/link의 <Link>는 JSX가 그 함수를
// **호출하지 않고** {type, props} 노드로만 남긴다(React.createElement가 하는 일) — 그래서
// 'use client' 컴포넌트를 vi.mock으로 스텁할 필요가 없었다(실측: 이 파일 작성 전 스크래치
// 테스트로 클라이언트 전용 import가 node에서 그대로 통과함을 확인). topOptions는 ListingCard
// 본문 안에서 **실제로 실행**되므로 칩 순서는 진짜 로직의 결과다.
//
// 이 테스트가 안 보는 것(추측 아니라 실측 근거): 실제 브라우저에 뱃지 색·✓ 아이콘이 그려지는지,
// 좁은 뷰포트에서 칩이 실제로 어떻게 잘리는지 — 이건 E2E-only다(대장 #106). Story 10.7의 수동
// 브라우저 실측(Auto Run Result)이 그 자리를 담당한다. 뱃지 톤(초록/중립)·면책 결속 자체·
// topOptions의 정렬 알고리즘은 각각 TrustAttributes.test.ts·options.test.ts가 이미 커버하므로
// 여기서 재검증하지 않는다 — 이 파일은 오직 "ListingCard가 그 결과물들을 실제로 조립하는가"만 본다.
//
// ⚠️ 이 기법의 전제(코드리뷰 2026-07-22): ListingCard가 동기·훅 없는 순수 함수 컴포넌트여야 한다.
// 만약 async(RSC 데이터 페치)가 되거나 훅을 쓰게 되면 함수 호출이 의미 있게 실패하지 않고 throw한다 —
// 그때는 이 파일을 렌더 기반 하네스로 옮겨야 한다(node 함수호출 트리로는 더 못 본다).
import { describe, expect, it } from 'vitest';
import ListingCard, { type ListingCardData } from '../ListingCard';
import TrustAttributes from '../TrustAttributes';
import { topOptions } from '@/lib/options';

// React 엘리먼트(순수 객체)인지 판별 — {type, props} 형태만 대상으로 한다.
type ElementNode = { type: unknown; props?: { children?: unknown; [key: string]: unknown } };

function isElementNode(node: unknown): node is ElementNode {
  return typeof node === 'object' && node !== null && 'type' in node && 'props' in node;
}

// 트리 전체(children 포함)에서 만나는 모든 엘리먼트 노드를 깊이우선으로 모은다. 호스트 노드
// ('div'·'span' 등 문자열 type)와 커스텀 컴포넌트 노드(함수 참조 type) 구분 없이 동일하게
// props.children을 따라 내려간다 — TrustAttributes.test.ts의 collectText와 같은 원리.
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

// 텍스트 리프만 모은다(TrustAttributes.test.ts와 동일 기법) — 칩 하나의 표시 문자열을 읽을 때 쓴다.
function collectText(node: unknown): string[] {
  if (node == null || typeof node === 'boolean') return [];
  if (typeof node === 'string' || typeof node === 'number') return [String(node)];
  if (Array.isArray(node)) return node.flatMap(collectText);
  if (isElementNode(node)) return collectText(node.props?.children);
  return [];
}

// "옵션칩 컨테이너"를 className이 아니라 **구조**로 찾는다: children이 전부 'span' 타입인
// non-empty 배열을 가진 노드 — 그래야 클래스명을 리팩터해도(스타일 변경) 테스트가 안 깨지고,
// 대신 "칩들을 별개 컨테이너로 묶어 렌더하는가"라는 조립 자체를 검사한다.
function findChipContainer(root: unknown): ElementNode | undefined {
  return collectNodes(root).find((node) => {
    const children = node.props?.children;
    return (
      Array.isArray(children) &&
      children.length > 0 &&
      children.every((child) => isElementNode(child) && child.type === 'span')
    );
  });
}

function chipTexts(container: ElementNode): string[] {
  const children = container.props?.children;
  const list = Array.isArray(children) ? children : [children];
  return list.map((child) => collectText(child).join(''));
}

const BASE_LISTING: ListingCardData = {
  id: 'demo-listing-1',
  manufacturer: '현대',
  model: '쏘나타',
  year: 2021,
  price: 21_000_000,
  mileage: 42_000,
  region: '서울',
};

describe('ListingCard 조립 — SM-C(카드에서 신뢰속성과 옵션이 구분·희소우선 노출)', () => {
  it('대표 매물(신뢰 풀세트+희소 옵션): TrustAttributes(card) 노드와 옵션칩 컨테이너가 별개로 존재하고, 칩 순서가 topOptions(options,4)와 일치한다(희소 우선)', () => {
    const listing: ListingCardData = {
      ...BASE_LISTING,
      accident_status: '무사고',
      is_single_owner: true,
      is_non_smoker: true,
      // 5개 중 '파노라마선루프' 1개만 HIGH 티어 — topOptions가 그것만 맨 앞으로 올리고
      // 나머지는 입력 순서를 유지한 채 상위 4개만 남기는지(5번째 '라디오'는 잘림)를 함께 본다.
      options: ['블루투스', '파노라마선루프', '스마트키', '에어컨', '라디오'],
    };

    const tree = ListingCard({ listing });
    const nodes = collectNodes(tree);

    // ① TrustAttributes(variant='card') 노드가 정확히 1개 존재 — 카드에서 신뢰블록을 지우면
    //    이 단언이 즉시 red가 된다(회귀 대상 1).
    const trustNodes = nodes.filter((n) => n.type === TrustAttributes);
    expect(trustNodes).toHaveLength(1);
    expect(trustNodes[0].props?.variant).toBe('card');
    expect(trustNodes[0].props?.listing).toBe(listing); // 같은 listing 객체를 그대로 전달

    // ② 옵션칩 컨테이너가 별도 노드로 존재하고, 순서가 topOptions(options,4)와 일치 —
    //    topOptions 호출을 지우거나(칩이 원본 순서 그대로 렌더) 앞 4개만 자르는 slice를
    //    지우면 이 단언이 red가 된다(회귀 대상 2). 신뢰블록과 옵션칩이 트리에서 서로 다른
    //    노드로 잡히는 것 자체가 "별개로 조립됨"의 증거다(TrustAttributes는 self-closing이라
    //    children 부재는 자명해 따로 단언하지 않는다 — 코드리뷰 2026-07-22).
    const expectedChips = topOptions(listing.options, 4);
    expect(expectedChips[0]).toBe('파노라마선루프'); // 희소 옵션이 실제로 맨 앞인지(스펙 전제 확인)
    expect(expectedChips).toHaveLength(4); // 5개 중 4개만(희소 1 + 보편 3), '라디오'는 잘림

    const container = findChipContainer(tree);
    expect(container).toBeDefined();
    expect(chipTexts(container!)).toEqual(expectedChips);
    expect(chipTexts(container!)[0]).toBe('파노라마선루프'); // 희소 옵션 최상단(SM-C)
  });

  it('옵션 없는 카드(options=[]): 옵션칩 컨테이너는 부재하지만 TrustAttributes는 여전히 마운트된다', () => {
    const listing: ListingCardData = {
      ...BASE_LISTING,
      accident_status: '사고',
      options: [],
    };

    const tree = ListingCard({ listing });
    const nodes = collectNodes(tree);

    expect(findChipContainer(tree)).toBeUndefined(); // cardOptions.length===0 가드
    const trustNodes = nodes.filter((n) => n.type === TrustAttributes);
    expect(trustNodes).toHaveLength(1); // 옵션이 없어도 신뢰블록 슬롯 자체는 그대로 조립됨
    expect(trustNodes[0].props?.variant).toBe('card');
  });

  it('NULL 신뢰속성 매물(세 컬럼 NULL): TrustAttributes는 여전히 마운트되고, 옵션칩은 정상 렌더된다(제3상태에서도 옵션 조립은 영향받지 않는다)', () => {
    const listing: ListingCardData = {
      ...BASE_LISTING,
      accident_status: null,
      is_single_owner: null,
      is_non_smoker: null,
      options: ['블루투스', '파노라마선루프'],
    };

    const tree = ListingCard({ listing });
    const nodes = collectNodes(tree);

    // TrustAttributes 자체가 null을 반환하는지(빈 뱃지)는 TrustAttributes.test.ts가 이미
    // 커버한다 — 여기서는 ListingCard가 이 경우에도 <TrustAttributes>를 여전히 호출해
    // 조립에서 빼지 않는지만 본다(예: "값이 없으면 아예 컴포넌트를 안 부른다" 같은 조건 분기가
    // ListingCard 쪽에 실수로 생기는 회귀를 잡는다).
    const trustNodes = nodes.filter((n) => n.type === TrustAttributes);
    expect(trustNodes).toHaveLength(1);
    expect(trustNodes[0].props?.listing).toMatchObject({
      accident_status: null,
      is_single_owner: null,
      is_non_smoker: null,
    });

    const expectedChips = topOptions(listing.options, 4);
    const container = findChipContainer(tree);
    expect(container).toBeDefined();
    expect(chipTexts(container!)).toEqual(expectedChips);
    expect(chipTexts(container!)[0]).toBe('파노라마선루프');
  });
});
