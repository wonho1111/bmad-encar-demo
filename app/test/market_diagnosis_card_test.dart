// 시세 진단 카드 위젯 테스트 — 실기기 지적 A6·A7(2026-09-16) 전용.
// market_diagnosis_test.dart는 이 카드가 쓰는 순수 함수만 보고(DOM 없음), ai_chat_screen_test.dart는
// 실제 채팅 흐름 배선을 본다 — 이 파일은 카드 하나만 pump해 "타일 2개 높이가 같은가"·"무한
// 높이 ListView 안에서도 죽지 않는가"를 좁게 확인한다.
import 'package:app/core/theme/app_theme.dart';
import 'package:app/features/ai_search/market_diagnosis.dart';
import 'package:app/features/ai_search/market_diagnosis_card.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

MarketDiagnosisData _data({required String? tabpfnNote, required int? tabpfnPrice}) {
  return MarketDiagnosisData(
    listing: const MarketDiagnosisListing(
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
    ),
    criteria: const MarketDiagnosisCriteria(step: 0, desc: '연식·주행거리·모델', sampleCount: 12),
    stats: const MarketDiagnosisStats(min: 19000000, q1: 20500000, median: 21500000, q3: 22800000, max: 24000000),
    percentile: 0.4,
    verdict: '적정',
    verdictBasis: '분위수',
    tabpfn: MarketDiagnosisTabpfn(
      price: tabpfnPrice,
      note: tabpfnNote ?? '',
      quantiles: const MarketDiagnosisQuantiles(q10: 19500000, q25: 21200000, q50: 21800000, q75: 22800000, q90: 23800000),
      cdfAtPrice: 0.4,
    ),
    comps: const [
      MarketDiagnosisComp(id: 'c-1', model: '셀토스', year: 2021, mileage: 31000, price: 21800000),
      MarketDiagnosisComp(id: 'c-2', model: '셀토스', year: 2020, mileage: 40000, price: 20500000),
    ],
  );
}

void main() {
  Widget wrap(Widget child) => MaterialApp(
        theme: buildAppTheme(),
        home: Scaffold(body: SingleChildScrollView(child: Padding(padding: const EdgeInsets.all(16), child: child))),
      );

  testWidgets('A6 — note가 한쪽 타일에만 있어도 두 타일 높이가 같다(IntrinsicHeight+stretch)', (tester) async {
    // tabpfn.price가 null이면 "표본 부족" + note가 AI 적정가 타일에만 붙는다 — 예전(Row+
    // Expanded, stretch 없음)엔 이쪽 타일만 더 길어졌다(red 재현 조건).
    final data = _data(
      tabpfnNote: '표본이 매우 부족해서 정확한 예측이 어려워요 조금 더 기다려 주시면 다시 계산해 드릴게요',
      tabpfnPrice: null,
    );

    await tester.pumpWidget(wrap(MarketDiagnosisCard(data: data, answer: '')));
    await tester.pumpAndSettle();

    final sampleHeight = tester.getSize(find.byKey(const Key('market_diagnosis_tile_sample'))).height;
    final tabpfnHeight = tester.getSize(find.byKey(const Key('market_diagnosis_tile_tabpfn'))).height;
    expect(tabpfnHeight, sampleHeight, reason: 'note 유무와 무관하게 두 타일은 항상 같은 높이여야 한다');
  });

  testWidgets('A6 — 무한 높이 ListView(채팅 말풍선과 같은 조건) 안에서도 예외 없이 렌더된다', (tester) async {
    final data = _data(tabpfnNote: null, tabpfnPrice: 21900000);

    await tester.pumpWidget(MaterialApp(
      theme: buildAppTheme(),
      home: Scaffold(
        body: ListView(
          children: [MarketDiagnosisCard(data: data, answer: '')],
        ),
      ),
    ));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('market_diagnosis_card')), findsOneWidget);
  });

  testWidgets('A7 — "자세히"를 펼쳐도 비교 매물 목록은 더 이상 없다(칩·통계·산점도는 남는다)', (tester) async {
    final data = _data(tabpfnNote: null, tabpfnPrice: 21900000);

    await tester.pumpWidget(wrap(MarketDiagnosisCard(data: data, answer: '')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('자세히'));
    await tester.pumpAndSettle();

    expect(find.text('비교 매물 목록'), findsNothing);
    expect(find.text('이런 차와 비교했어요:'), findsOneWidget);
    expect(find.text('최저'), findsOneWidget);
    expect(find.text('최고'), findsOneWidget);
  });
}
