// 시세 카드 그래프(MarketDiagnosisPriceChart) 위젯 테스트 — 실기기 지적 A2(2026-09-16) 전용.
// market_diagnosis_test.dart는 buildDensityCurve 등 이 그래프가 쓰는 순수 함수만 본다(DOM
// 없음) — 이 파일은 실제로 pump해서 폭에 따라 그래프 자체 높이가 달라지는지(컴팩트 모드)를
// 확인한다.
import 'package:app/features/ai_search/market_diagnosis.dart';
import 'package:app/features/ai_search/market_diagnosis_price_chart.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

const _listing = MarketDiagnosisListing(
  id: 'l-1',
  manufacturer: '기아',
  model: '셀토스',
  year: 2021,
  mileage: 33000,
  price: 22000000,
  fuel: '가솔린',
  transmission: '자동',
  displacement: 1998,
  accidentFree: true,
  accidentStatus: '무사고',
  region: '경기',
);

const _quantiles = MarketDiagnosisQuantiles(q10: 19500000, q25: 21200000, q50: 21800000, q75: 22800000, q90: 23800000);

const _comps = [
  MarketDiagnosisComp(id: 'c-1', model: '셀토스', year: 2021, mileage: 31000, price: 21800000),
  MarketDiagnosisComp(id: 'c-2', model: '셀토스', year: 2020, mileage: 40000, price: 20500000),
];

List<double> _compsNear25mWithOutlier() {
  // 비교군 50건(2,500만 근처) + 이상치 1건(9,999만) — 엔카 "가격문의" 표시값 사례(2026-09-16 실측).
  final prices = [for (var i = 0; i < 50; i++) 24000000.0 + i * 20000];
  prices.add(99990000.0);
  return prices;
}

Future<double> _pumpChartHeight(WidgetTester tester, double width) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(
        body: Align(
          alignment: Alignment.topLeft,
          child: SizedBox(
            width: width,
            child: const MarketDiagnosisPriceChart(
              listing: _listing,
              stats: null,
              comps: _comps,
              quantiles: _quantiles,
              verdict: '적정',
            ),
          ),
        ),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return tester.getSize(find.byType(AspectRatio)).height;
}

void main() {
  testWidgets('A2 — 폭 380dp면 컴팩트 모드로 그래프 높이가 200 이상이다', (tester) async {
    final height = await _pumpChartHeight(tester, 380);
    expect(height, greaterThanOrEqualTo(200));
  });

  testWidgets('A2 — 폭 700dp면 기존 640×(210+18) 비율 그대로다(컴팩트 비율로 바뀌지 않는다)', (tester) async {
    final height = await _pumpChartHeight(tester, 700);
    final expected = 700 * (210 + 18) / 640; // ≈ 249.4
    expect(height, closeTo(expected, 0.5));
  });

  // 축 이상치 결함 회귀(2026-09-16 실측, web computePriceDomain 테스트 미러): 비교군에 엔카
  // "가격문의" 표시값(9,999만원) 1건이 섞이면 옛 로직(compPrices 전체를 domain에 넣음)은
  // 가로축이 1억까지 늘어나 정상 분포(2,500만원대) 곡선이 바늘처럼 눌렸다. computePriceDomain은
  // 2~98 백분위 밖 값을 domain에서 빼고 개수만 outliersAbove/Below로 돌려준다.
  group('computePriceDomain — 이상치 결함 회귀(2026-09-16)', () {
    test('비교군 50건(2,500만 근처) + 이상치 1건(9,999만)이어도 축 최대가 4,000만 이하이고 이상치는 1건으로 집계된다', () {
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

    test('표본이 20건 미만이면 백분위로 자르지 않는다(자를 여유가 없음) — 이상치도 그대로 domain에 들어간다', () {
      final result = computePriceDomain(
        compPrices: [24000000, 24500000, 99990000],
        listingPrice: 25000000,
        quantiles: null,
        stats: null,
        curveEndpoints: null,
      );

      expect(result.priceMax, greaterThan(90000000));
      expect(result.outliersAbove, 0);
    });
  });
}
