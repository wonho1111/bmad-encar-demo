// TrustAttributes 단위테스트 (Story 10.2).
//
// 왜 .test.ts(jsdom·RTL 없이)인가: 이 리포의 web 테스트 표준은 E2E(Playwright) 우선이고,
// vitest.config.ts는 node 환경 + `src/**/*.test.ts`만 실행한다(project-context 규칙12 —
// "서버 컴포넌트 밖 순수 유틸만 Vitest로 보강"). jsdom·렌더러가 없으므로 실제 DOM에 마운트하지는
// 않지만, `TrustAttributes`는 훅을 쓰지 않는 상태 없는 함수 컴포넌트라 **함수로 직접 호출**하면
// React 엘리먼트 트리(순수 객체)가 그대로 반환된다 — 이 트리를 순회해 "결속"을 두 계층에서 본다:
//   ① 데이터 계층(getTrustDisplay) — 뱃지 배열과 면책 문자열이 같은 반환 객체 안에 있는지.
//   ② 렌더 계층(TrustAttributes 컴포넌트 트리, P1 코드리뷰 2026-07-22) — 컴포넌트가 그 값을
//      실제로 별도 JSX 노드로 방출하는지. ①만으로는 컴포넌트 JSX에서 disclaimer <span>/<p>를
//      지워도 못 잡는다(반환 데이터는 멀쩡하니 ①은 green인데 화면엔 면책이 안 뜨는 경로가
//      생긴다) — 그래서 ②가 별도로 필요하다.
//
// 이 테스트가 안 보는 것(추측 아니라 실측 근거): 실제 브라우저 DOM에 ✓ 아이콘·초록 배경이
// 그려지는지, 하이드레이션 전 시점, 스크린리더가 실제로 읽는지 — 이 세 가지는 이 리포 표준상
// E2E-only다(대장 #106). 본 스토리의 Manual checks(브라우저 MCP)가 그 자리를 담당한다.
import { describe, expect, it } from 'vitest';
import TrustAttributes, {
  getTrustDisplay,
  hasTrustAttributes,
  type TrustAttributesInput,
} from './TrustAttributes';

// React 엘리먼트 트리(문자열·숫자·배열·{props:{children}} 노드)에서 텍스트 리프를 전부 모은다.
// 렌더러 없이(jsdom 없이) "이 텍스트가 트리 안에 실제로 있는가"를 확인하는 유일한 방법 —
// TrustAttributes를 함수로 직접 호출한 결과(순수 객체 그래프)에 대해서만 동작한다.
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

describe('getTrustDisplay — I/O 매트릭스', () => {
  it('무사고 → 초록 뱃지(✓+무사고) + 면책', () => {
    const listing: TrustAttributesInput = { accident_status: '무사고' };
    const display = getTrustDisplay(listing, 'card');
    expect(display?.badges).toEqual([{ key: 'accident', label: '무사고', tone: 'green' }]);
    expect(display?.disclaimer).toBe('판매자 제공 정보');
  });

  it('단순교환 → 초록이 아닌 중립 상태칩 + 면책', () => {
    const listing: TrustAttributesInput = { accident_status: '단순교환' };
    const display = getTrustDisplay(listing, 'card');
    expect(display?.badges).toEqual([{ key: 'accident', label: '단순교환', tone: 'neutral' }]);
  });

  it('사고 → 초록이 아닌 중립 상태칩 + 면책', () => {
    const listing: TrustAttributesInput = { accident_status: '사고' };
    const display = getTrustDisplay(listing, 'card');
    expect(display?.badges).toEqual([{ key: 'accident', label: '사고', tone: 'neutral' }]);
  });

  it('1인소유=true → 초록 칩', () => {
    const listing: TrustAttributesInput = { is_single_owner: true };
    const display = getTrustDisplay(listing, 'card');
    expect(display?.badges).toEqual([{ key: 'single-owner', label: '1인소유', tone: 'green' }]);
  });

  it('비흡연=true → 초록 칩', () => {
    const listing: TrustAttributesInput = { is_non_smoker: true };
    const display = getTrustDisplay(listing, 'card');
    expect(display?.badges).toEqual([{ key: 'non-smoker', label: '비흡연', tone: 'green' }]);
  });

  it('bool 미상(null) → 그 칩 미표시("아님"으로 단정 안 함)', () => {
    const listing: TrustAttributesInput = { is_single_owner: null, is_non_smoker: null };
    expect(getTrustDisplay(listing, 'card')).toBeNull();
  });

  it('bool false → 그 칩 미표시("아님"으로 단정 안 함)', () => {
    const listing: TrustAttributesInput = { is_single_owner: false, is_non_smoker: false };
    expect(getTrustDisplay(listing, 'card')).toBeNull();
  });

  it('3필드 전부 null → null 반환(카드·상세 모두 아무것도 렌더 안 함)', () => {
    const listing: TrustAttributesInput = {
      accident_status: null,
      is_single_owner: null,
      is_non_smoker: null,
    };
    expect(getTrustDisplay(listing, 'card')).toBeNull();
    expect(getTrustDisplay(listing, 'detail')).toBeNull();
    expect(hasTrustAttributes(listing)).toBe(false);
  });

  it('3필드 전부 undefined(값 자체를 안 보낸 입력) → null 반환', () => {
    expect(getTrustDisplay({}, 'card')).toBeNull();
    expect(hasTrustAttributes({})).toBe(false);
  });

  it('계약-외 값(3값 밖) → null과 동일 취급(미표시)', () => {
    // 실제 DB 값은 CHECK 제약이 있지만, 렌더 소비처는 방어적으로 처리해야 한다(conventions §4).
    const listing = { accident_status: '외판교환' } as unknown as TrustAttributesInput;
    expect(getTrustDisplay(listing, 'card')).toBeNull();
  });

  it('계약-외 값(빈 문자열) → null과 동일 취급(미표시)', () => {
    const listing = { accident_status: '' } as unknown as TrustAttributesInput;
    expect(getTrustDisplay(listing, 'card')).toBeNull();
  });

  it('혼합: 사고 + 비흡연 → 중립칩(사고) + 초록칩(비흡연) + 면책 1개', () => {
    const listing: TrustAttributesInput = { accident_status: '사고', is_non_smoker: true };
    const display = getTrustDisplay(listing, 'detail');
    expect(display?.badges).toEqual([
      { key: 'accident', label: '사고', tone: 'neutral' },
      { key: 'non-smoker', label: '비흡연', tone: 'green' },
    ]);
    // 면책은 배지 개수와 무관하게 문자열 하나 — 호출부가 배지마다 반복해 붙이지 않는다.
    expect(typeof display?.disclaimer).toBe('string');
  });

  it('detail variant는 상세 전용 문구(UX-DR19)를 그대로 낸다', () => {
    const listing: TrustAttributesInput = { accident_status: '무사고' };
    const display = getTrustDisplay(listing, 'detail');
    expect(display?.disclaimer).toBe(
      '판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요.',
    );
  });
});

describe('면책-뱃지 결속(B9) — "있는지"가 아니라 "결속되는지"', () => {
  // getTrustDisplay가 이 결속의 유일한 자리다(설계 근거: TrustAttributes 컴포넌트는 이 함수의
  // 반환값만 렌더하고, 배지·면책을 따로 조립하지 않는다). 그래서 "뱃지가 있으면 면책도 있다"를
  // 이 함수 하나로 전수 검증할 수 있다 — 호출부(ListingCard·TrustInfoSection)를 렌더하지 않아도
  // 결속이 깨지면 여기서 반드시 잡힌다.
  const casesWithBadges: Array<[string, TrustAttributesInput]> = [
    ['무사고', { accident_status: '무사고' }],
    ['단순교환', { accident_status: '단순교환' }],
    ['사고', { accident_status: '사고' }],
    ['1인소유', { is_single_owner: true }],
    ['비흡연', { is_non_smoker: true }],
    ['혼합', { accident_status: '사고', is_non_smoker: true }],
  ];

  it.each(casesWithBadges)('%s — 뱃지가 있으면 면책(card)도 항상 함께 있다', (_label, listing) => {
    const display = getTrustDisplay(listing, 'card');
    expect(display).not.toBeNull();
    expect(display!.badges.length).toBeGreaterThan(0);
    expect(display!.disclaimer.length).toBeGreaterThan(0); // 면책 emit을 지우면 이 줄이 red가 된다.
  });

  it.each(casesWithBadges)('%s — 뱃지가 있으면 면책(detail)도 항상 함께 있다', (_label, listing) => {
    const display = getTrustDisplay(listing, 'detail');
    expect(display).not.toBeNull();
    expect(display!.badges.length).toBeGreaterThan(0);
    expect(display!.disclaimer.length).toBeGreaterThan(0);
  });
});

describe('렌더 레이어 결속(P1, 코드리뷰 2026-07-22) — 컴포넌트 실제 반환 트리', () => {
  // 위 블록(getTrustDisplay)은 "데이터가 결속돼 있는가"만 본다 — TrustAttributes 컴포넌트의
  // JSX에서 disclaimer <span>/<p> 자체를 지워도(데이터는 멀쩡히 반환하니) 위 블록은 계속 green이다.
  // 이 블록은 컴포넌트를 **함수로 직접 호출**해 실제로 반환되는 React 엘리먼트 트리를 순회하고,
  // 뱃지 라벨 문자열이 트리에 있으면 면책 문자열도 트리에 실제로 있는지 본다 — 컴포넌트 JSX 자체의
  // 결속을 잡는 자리다.
  const casesWithBadges: Array<[string, TrustAttributesInput, string]> = [
    ['무사고', { accident_status: '무사고' }, '무사고'],
    ['단순교환', { accident_status: '단순교환' }, '단순교환'],
    ['사고', { accident_status: '사고' }, '사고'],
    ['1인소유', { is_single_owner: true }, '1인소유'],
    ['비흡연', { is_non_smoker: true }, '비흡연'],
    ['혼합', { accident_status: '사고', is_non_smoker: true }, '사고'],
  ];

  it.each(casesWithBadges)(
    '%s(card) — 렌더 트리에 뱃지 라벨과 "판매자 제공 정보"가 같이 있다',
    (_label, listing, badgeLabel) => {
      const element = TrustAttributes({ listing, variant: 'card' });
      const text = collectText(element).join(' ');
      expect(text).toContain(badgeLabel);
      // 컴포넌트 JSX에서 면책 <span>을 지우면(getTrustDisplay는 그대로 둬도) 이 줄이 red가 된다.
      expect(text).toContain('판매자 제공 정보');
    },
  );

  it.each(casesWithBadges)(
    '%s(detail) — 렌더 트리에 뱃지 라벨과 상세 면책 문구(UX-DR19)가 같이 있다',
    (_label, listing, badgeLabel) => {
      const element = TrustAttributes({ listing, variant: 'detail' });
      const text = collectText(element).join(' ');
      expect(text).toContain(badgeLabel);
      // 컴포넌트 JSX에서 면책 <p>를 지우면(getTrustDisplay는 그대로 둬도) 이 줄이 red가 된다.
      expect(text).toContain('판매자가 직접 입력한 정보예요');
    },
  );

  it('뱃지가 0개면 컴포넌트도 null을 반환한다(빈 슬롯 렌더 금지, AC1)', () => {
    expect(TrustAttributes({ listing: {}, variant: 'card' })).toBeNull();
    expect(TrustAttributes({ listing: {}, variant: 'detail' })).toBeNull();
  });
});

// 엘리먼트 트리에서 className 문자열을 전부 모은다(collectText가 텍스트만 보므로 톤 클래스는 못 본다).
// TrustAttributes를 함수로 직접 호출한 순수 객체 그래프에만 동작한다(위 collectText와 같은 전제).
function collectClassNames(node: unknown): string[] {
  if (node == null || typeof node !== 'object') return [];
  const props = (node as { props?: { className?: unknown; children?: unknown } }).props;
  const here = typeof props?.className === 'string' ? [props.className] : [];
  return here.concat(collectClassNames(props?.children), Array.isArray(node) ? node.flatMap(collectClassNames) : []);
}

describe('톤 결속(follow-up 코드리뷰 2026-07-22) — 초록의 비색 신호(✓·초록 클래스)가 실제로 방출되는가', () => {
  // 위 렌더 블록은 뱃지 라벨과 면책 텍스트만 본다 — 컴포넌트에서 ✓(<span aria-hidden>)를 지우거나
  // 초록 className을 중립 className으로 바꿔도 라벨·면책은 멀쩡하니 계속 green이었다. 그러면 초록
  // 뱃지가 '색만'으로 표기되는 §4 비색 신호(색+✓+텍스트) 위반이 조용히 통과한다. 여기서 트리의
  // 텍스트에 ✓가 있는지, className에 초록 토큰(trust-green)이 있는지를 직접 단언한다.
  // red/green 실측 지점: 컴포넌트에서 ✓ 노드를 지우면 초록 케이스가 red, 초록 className을 중립으로
  // 바꾸면 trust-green 단언이 red — 원복하면 green.
  it('초록 케이스(무사고, card) — 트리에 ✓와 trust-green 클래스가 함께 있다', () => {
    const element = TrustAttributes({ listing: { accident_status: '무사고' }, variant: 'card' });
    expect(collectText(element).join(' ')).toContain('✓');
    expect(collectClassNames(element).join(' ')).toContain('trust-green');
  });

  it('초록 케이스(1인소유, detail) — 트리에 ✓와 trust-green 클래스가 함께 있다', () => {
    const element = TrustAttributes({ listing: { is_single_owner: true }, variant: 'detail' });
    expect(collectText(element).join(' ')).toContain('✓');
    expect(collectClassNames(element).join(' ')).toContain('trust-green');
  });

  it('중립 케이스(사고, card) — ✓ 없음, 초록 클래스 없음(중립칩이 초록으로 오염되지 않는다)', () => {
    const element = TrustAttributes({ listing: { accident_status: '사고' }, variant: 'card' });
    expect(collectText(element).join(' ')).not.toContain('✓');
    expect(collectClassNames(element).join(' ')).not.toContain('trust-green');
  });

  it('중립 케이스(단순교환, card) — ✓ 없음', () => {
    const element = TrustAttributes({ listing: { accident_status: '단순교환' }, variant: 'card' });
    expect(collectText(element).join(' ')).not.toContain('✓');
  });

  it('혼합(사고+비흡연, card) — 초록 칩(비흡연)의 ✓·trust-green과 중립칩(사고)이 공존한다', () => {
    const element = TrustAttributes({
      listing: { accident_status: '사고', is_non_smoker: true },
      variant: 'card',
    });
    const text = collectText(element).join(' ');
    expect(text).toContain('사고'); // 중립칩
    expect(text).toContain('비흡연'); // 초록칩
    expect(text).toContain('✓'); // 초록칩의 비색 신호
    expect(collectClassNames(element).join(' ')).toContain('trust-green');
  });
});
