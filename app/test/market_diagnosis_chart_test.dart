// 산점도(③, 주행거리×가격) 가격축(세로축) 이상치 방어 회귀(2026-09-16, DW-888 확장) — 밀도
// 곡선 그래프(market_diagnosis_price_chart.dart)에 넣은 computePriceDomain 규칙을 산점도에도
// 그대로 적용했는지 확인한다. 산점도(market_diagnosis_chart.dart)는 이 함수를 quantiles/
// stats/curveEndpoints 전부 비우고 호출한다(대상가만 포함) — 그 호출 방식을 그대로 재현해
// 축 계산이 위젯에 묻히지 않고 순수 함수로 검증 가능한지 고정한다(web MarketDiagnosisChart.
// test.ts 미러).
import 'package:app/features/ai_search/market_diagnosis_price_chart.dart';
import 'package:flutter_test/flutter_test.dart';

List<double> _compsNear25mWithOutlier() {
  final prices = [for (var i = 0; i < 50; i++) 24500000.0 + i * 20000.0]; // 24.5M~25.48M
  prices.add(98000000.0); // 이상치 1건
  return prices;
}

void main() {
  test('산점도 가격축 — 비교군 50건(2,500만 근처) + 이상치 1건(9,800만)이어도 축 최대가 4,000만 이하이고 이상치는 1건으로 집계된다', () {
    final result = computePriceDomain(
      compPrices: _compsNear25mWithOutlier(),
      listingPrice: 25000000,
      quantiles: null,
      stats: null,
      curveEndpoints: null,
    );

    expect(result.priceMax, lessThanOrEqualTo(40000000));
    expect(result.outliersAbove, 1);
    expect(result.outliersBelow, 0);
  });
}
