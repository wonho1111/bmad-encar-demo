// buildDensityCurve 단위테스트 — 시세 카드 밀도 곡선(③, DW-885 재작업)의 순수 함수만 검증한다
// (vitest.config.ts 방침: node 환경, DOM 없는 순수 로직만 여기서 고정한다).
//
// 왜 이 테스트가 필요한가: 종전엔 분위수마다 고정 높이를 박고 Catmull-Rom 스플라인으로 이어
// q25·q50처럼 이웃 분위수가 가까우면 오버슈트로 정점 근처가 움푹 파였다(운영 실측 8건 캡처).
// 재작업한 buildDensityCurve는 "구간 질량÷폭 = 밀도"를 가우시안 커널로 평활한 값이라 구조적으로
// 오버슈트가 없다 — 그 불변식(파임 없음)을 q25·q50이 가까운 입력으로 직접 고정한다.
import { describe, expect, it } from 'vitest';

import { buildDensityCurve, type Quantiles5 } from './MarketDiagnosisPriceChart';

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
