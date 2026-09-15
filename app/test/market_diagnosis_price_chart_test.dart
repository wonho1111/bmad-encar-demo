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
}
