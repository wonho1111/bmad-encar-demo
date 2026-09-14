// buildDensityCurve 단위테스트 — 시세 카드 밀도 곡선(③, DW-885 재작업)의 순수 함수만 검증한다
// (vitest.config.ts 방침: node 환경, DOM 없는 순수 로직만 여기서 고정한다).
//
// 왜 이 테스트가 필요한가: 종전엔 분위수마다 고정 높이를 박고 Catmull-Rom 스플라인으로 이어
// q25·q50처럼 이웃 분위수가 가까우면 오버슈트로 정점 근처가 움푹 파였다(운영 실측 8건 캡처).
// 재작업한 buildDensityCurve는 "구간 질량÷폭 = 밀도"를 가우시안 커널로 평활한 값이라 구조적으로
// 오버슈트가 없다 — 그 불변식(파임 없음)을 q25·q50이 가까운 입력으로 직접 고정한다.
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { describe, expect, it } from 'vitest';

import MarketDiagnosisPriceChart, { buildDensityCurve, type Quantiles5 } from './MarketDiagnosisPriceChart';

/** 곡선 점들에서 정점 인덱스를 찾고, 정점 왼쪽이 단조 증가·오른쪽이 단조 감소인지 확인한다. */
function isUnimodalNoDip(points: { x: number; y: number }[]): boolean {
  let peakIdx = 0;
  for (let i = 1; i < points.length; i++) {
    if (points[i].y > points[peakIdx].y) peakIdx = i;
  }
  for (let i = 1; i <= peakIdx; i++) {
    if (points[i].y < points[i - 1].y - 1e-9) return false; // 왼쪽에서 내려갔다가 다시 오르면 파임
  }
  for (let i = peakIdx + 1; i < points.length; i++) {
    if (points[i].y > points[i - 1].y + 1e-9) return false; // 오른쪽에서 다시 오르면 파임
  }
  return true;
}

describe('buildDensityCurve', () => {
  it('정점을 1로 정규화한다', () => {
    const q: Quantiles5 = { q10: 18_000_000, q25: 20_500_000, q50: 22_500_000, q75: 24_500_000, q90: 26_000_000 };
    const curve = buildDensityCurve(q);
    const maxY = Math.max(...curve.map((p) => p.y));
    expect(maxY).toBeCloseTo(1, 6);
  });

  it('q25·q50이 가까운 입력에서도 정점 왼쪽은 단조 증가·오른쪽은 단조 감소한다(파임 없음)', () => {
    // 종전 Catmull-Rom 스플라인이 실제로 파이던 조건 — q25·q50 간격(100)이 q10·q25 간격(900)
    // 보다 훨씬 좁아, 그 구간(질량 0.25)의 밀도가 크게 튀어 오른다.
    const q: Quantiles5 = { q10: 1_000, q25: 1_900, q50: 2_000, q75: 3_000, q90: 4_000 };
    const curve = buildDensityCurve(q);
    expect(isUnimodalNoDip(curve)).toBe(true);
  });

  it('분위수 간격이 고른 입력에서도 파임이 없다', () => {
    const q: Quantiles5 = { q10: 1_000, q25: 2_000, q50: 2_500, q75: 3_000, q90: 4_000 };
    const curve = buildDensityCurve(q);
    expect(isUnimodalNoDip(curve)).toBe(true);
  });

  it('그리드 점 개수는 요구 범위(60~80) 안이다', () => {
    const q: Quantiles5 = { q10: 1_000, q25: 2_000, q50: 2_500, q75: 3_000, q90: 4_000 };
    const curve = buildDensityCurve(q);
    expect(curve.length).toBeGreaterThanOrEqual(60);
    expect(curve.length).toBeLessThanOrEqual(80);
  });

  it('좁은 구간([q25,q50])이 넓은 구간([q10,q25])보다 밀도가 높다 — 정점이 좁은 쪽으로 몰린다', () => {
    const q: Quantiles5 = { q10: 1_000, q25: 1_900, q50: 2_000, q75: 3_000, q90: 4_000 };
    const curve = buildDensityCurve(q);
    const peak = curve.reduce((max, p) => (p.y > max.y ? p : max));
    // 정점 x가 q25~q50(좁은 구간, 1_900~2_000) 근처여야 한다 — q10~q25(넓은 구간)에 있으면 안 된다.
    expect(peak.x).toBeGreaterThan(1_800);
    expect(peak.x).toBeLessThan(2_200);
  });
});

// 렌더 계약(2026-09-15 운영 실측 후속, 카드 8건 재캡처) — 훅 없는 컴포넌트라 MarketDiagnosis.test.ts와
// 같은 방식(renderToStaticMarkup)으로 마크업만 고정한다.
describe('MarketDiagnosisPriceChart — 렌더 계약(2026-09-15 운영 실측 후속)', () => {
  const Q: Quantiles5 = { q10: 18_000_000, q25: 20_500_000, q50: 22_500_000, q75: 24_500_000, q90: 26_000_000 };

  it('세로축 제목이 CSS writing-mode 대신 svg rotate(-90)로 눕혀 있다 — 2026-09-15 실측(한 자씩 쌓여 못 읽음)', () => {
    const html = renderToStaticMarkup(
      createElement(MarketDiagnosisPriceChart, { listingPrice: Q.q50, stats: null, comps: [], quantiles: Q }),
    );
    expect(html).toContain('rotate(-90');
    expect(html).not.toContain('vertical-rl');
  });

  it('곡선 아래 음영(fillPath)이 q10~q90 상자가 아니라 꼬리 포함 곡선 전체를 덮는다 — 2026-09-15 실측(상자처럼 잘려 보임)', () => {
    // listingPrice=q10, comp 1건=q90으로 놓아 "이 매물" 세로선·비교군 점을 각각 xScale(q10)·
    // xScale(q90)의 독립 기준점으로 쓴다(음영 자체가 낸 좌표로 음영을 검증하는 자기일관 단언이
    // 되지 않도록, 서로 다른 두 렌더 요소에서 기준을 뽑는다).
    const html = renderToStaticMarkup(
      createElement(MarketDiagnosisPriceChart, {
        listingPrice: Q.q10,
        stats: null,
        comps: [{ id: 'c1', model: '테스트', year: 2021, mileage: 30_000, price: Q.q90 }],
        quantiles: Q,
      }),
    );

    const listingLine = html.match(/<line x1="([\d.eE+-]+)"[^>]*stroke="var\(--price-emphasis\)"/);
    const compCircle = html.match(/<circle cx="([\d.eE+-]+)"[^>]*fill="var\(--brand-petrol\)" opacity="0\.55"/);
    const fillPath = html.match(/<path d="([^"]+)" fill="var\(--brand-petrol\)" opacity="0\.08"/);
    expect(listingLine).not.toBeNull();
    expect(compCircle).not.toBeNull();
    expect(fillPath).not.toBeNull();

    const q10X = Number(listingLine![1]);
    const q90X = Number(compCircle![1]);
    const fillXs = [...fillPath![1].matchAll(/[ML] (-?[\d.eE+-]+) -?[\d.eE+-]+/g)].map((m) => Number(m[1]));

    // 꼬리 포함이면 음영의 x 범위가 q10~q90보다 넓어야 한다(상자였다면 q10X·q90X와 같았을 값).
    expect(Math.min(...fillXs)).toBeLessThan(q10X);
    expect(Math.max(...fillXs)).toBeGreaterThan(q90X);
  });
});
