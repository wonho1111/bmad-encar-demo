// 신뢰속성 판정 단위테스트(Story 16.3) — spec-16-3 I/O & Edge-Case Matrix 신뢰속성 6행을
// `getTrustBadges` 순수함수로 직접 단언한다(web TrustAttributes.test.ts 미러).
// + 위젯 레벨 결속(B9): 상세는 뱃지+면책이 한 위젯에서 함께 나오고, 카드는 면책이 없다.
import 'package:app/features/listings/listing_trust_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('getTrustBadges — I/O 매트릭스', () {
    test('무사고 → 초록 뱃지(accident, green)', () {
      final badges = getTrustBadges(accidentStatus: '무사고');
      expect(badges, hasLength(1));
      expect(badges.single.key, 'accident');
      expect(badges.single.label, '무사고');
      expect(badges.single.tone, TrustTone.green);
    });

    test('단순교환 → 중립 뱃지(초록 아님)', () {
      final badges = getTrustBadges(accidentStatus: '단순교환');
      expect(badges.single.tone, TrustTone.neutral);
      expect(badges.single.label, '단순교환');
    });

    test('사고 → 중립 뱃지(초록 아님)', () {
      final badges = getTrustBadges(accidentStatus: '사고');
      expect(badges.single.tone, TrustTone.neutral);
      expect(badges.single.label, '사고');
    });

    test('계약-외 값("외판교환") → null과 동일 취급(미표시)', () {
      expect(getTrustBadges(accidentStatus: '외판교환'), isEmpty);
    });

    test('계약-외 값(빈 문자열) → null과 동일 취급(미표시)', () {
      expect(getTrustBadges(accidentStatus: ''), isEmpty);
    });

    test('1인소유=true·비흡연=true → 초록 칩 2개 추가', () {
      final badges = getTrustBadges(isSingleOwner: true, isNonSmoker: true);
      expect(badges.map((b) => b.key), ['single-owner', 'non-smoker']);
      expect(badges.every((b) => b.tone == TrustTone.green), isTrue);
    });

    test('bool 미상(null) → 그 칩만 미표시(다른 칩은 그대로)', () {
      final badges = getTrustBadges(
        accidentStatus: '무사고',
        isSingleOwner: null,
        isNonSmoker: true,
      );
      expect(badges.map((b) => b.key), ['accident', 'non-smoker']);
    });

    test('bool false → "아님"으로 단정하지 않고 미표시', () {
      final badges = getTrustBadges(isSingleOwner: false, isNonSmoker: false);
      expect(badges, isEmpty);
    });

    test('3필드 전부 미입력 → 빈 배열(카드·상세 모두 아무것도 렌더 안 함)', () {
      expect(getTrustBadges(), isEmpty);
    });
  });

  group('위젯 결속(B9) — 카드는 면책 없음, 상세는 뱃지+면책 결속', () {
    testWidgets('카드 오버레이 — 뱃지는 있지만 면책 문구는 렌더되지 않는다', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                TrustAttributesCardOverlay(
                  accidentStatus: '무사고',
                  isSingleOwner: null,
                  isNonSmoker: null,
                ),
              ],
            ),
          ),
        ),
      );
      expect(find.text('무사고'), findsOneWidget);
      expect(find.textContaining('판매자가 직접 입력한 정보'), findsNothing);
    });

    testWidgets('카드 오버레이 — 뱃지 0개면 아무것도 그리지 않는다(SizedBox.shrink)', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: Stack(
              children: [
                TrustAttributesCardOverlay(
                  accidentStatus: null,
                  isSingleOwner: null,
                  isNonSmoker: null,
                ),
              ],
            ),
          ),
        ),
      );
      // `find.byType(Positioned)` was vacuous(코드리뷰 지적 P6) — TrustAttributesCardOverlay
      // 자체는 애초에 Positioned를 반환하지 않는다(위치는 호출부 listing_card.dart가 감싼다,
      // 위 클래스 주석 참조), 그래서 그 assert는 뱃지가 있든 없든 항상 통과했다. 실제로 뭘
      // 그렸는지(Wrap·Text 자체가 없어야 함)를 이 위젯의 서브트리로 좁혀 확인한다.
      expect(
        find.descendant(
          of: find.byType(TrustAttributesCardOverlay),
          matching: find.byType(Wrap),
        ),
        findsNothing,
      );
      expect(
        find.descendant(
          of: find.byType(TrustAttributesCardOverlay),
          matching: find.byType(Text),
        ),
        findsNothing,
      );
    });

    testWidgets('상세 섹션 — 뱃지가 있으면 면책 문구가 반드시 같은 위젯에서 함께 나온다(B9)',
        (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TrustAttributesDetailSection(
              accidentStatus: '사고',
              isSingleOwner: null,
              isNonSmoker: true,
            ),
          ),
        ),
      );
      expect(find.text('사고'), findsOneWidget);
      expect(find.text('비흡연'), findsOneWidget);
      expect(find.textContaining('판매자가 직접 입력한 정보'), findsOneWidget);
    });

    testWidgets('상세 섹션 — 값이 전부 없으면 섹션 자체가 없다(AC3)', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TrustAttributesDetailSection(
              accidentStatus: null,
              isSingleOwner: null,
              isNonSmoker: null,
            ),
          ),
        ),
      );
      expect(find.byType(TrustAttributesDetailSection), findsOneWidget);
      expect(find.textContaining('판매자가 직접 입력한 정보'), findsNothing);
    });
  });
}
