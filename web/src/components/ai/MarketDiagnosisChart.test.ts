// 산점도(③, 주행거리×가격) 가격축(세로축) 이상치 방어 회귀(2026-09-16, DW-888 확장) — 밀도
// 곡선 그래프(MarketDiagnosisPriceChart.tsx)에 넣은 computePriceDomain 규칙을 산점도에도 그대로
// 적용했는지 확인한다. 산점도는 MarketDiagnosisChart.tsx에서 이 함수를 quantiles/stats/
// curveEndpoints 전부 비우고 호출한다(대상가만 포함) — 그 호출 방식을 그대로 재현해 축 계산이
// 컴포넌트에 묻히지 않고 순수 함수로 검증 가능한지 고정한다.
import { describe, expect, it } from 'vitest';

import { computePriceDomain } from './MarketDiagnosisPriceChart';

describe('MarketDiagnosisChart(산점도) 가격축 — computePriceDomain 재사용', () => {
  it('비교군 50건(2,500만 근처) + 이상치 1건(9,800만)이어도 가격축 최대가 4,000만 이하이고 이상치는 1건으로 집계된다', () => {
    const compPrices = Array.from({ length: 50 }, (_, i) => 24_500_000 + i * 20_000); // 24.5M~25.48M
    compPrices.push(98_000_000);

    const result = computePriceDomain({
      compPrices,
      listingPrice: 25_000_000,
      quantiles: null, // 산점도는 밀도 곡선이 없다
      stats: null, // stats.min/max는 이상치를 그대로 담고 있어 넘기지 않는다
      curveEndpoints: null,
    });

    expect(result.priceMax).toBeLessThanOrEqual(40_000_000);
    expect(result.outliersAbove).toBe(1);
    expect(result.outliersBelow).toBe(0);
  });
});
