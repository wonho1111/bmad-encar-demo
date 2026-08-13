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

  group(
      '위젯 결속(B9) — 카드 행은 짧은 면책 포함, 상세는 긴 면책 결속(spec-16-9로 카드도 결속 대상에 들어옴)',
      () {
    // ✎ 2026-08-13 사용자 지적 #4로 **계약이 다시 뒤집혔다** — 카드 칩이 사진 아래 전용 행에서
    //   **사진 위 오버레이**로 돌아가면서(웹과 같은 자리) 짧은 면책 "판매자 제공 정보"가 빠졌다.
    //   그전 계약(spec-16-9: 카드도 면책 결속 대상)을 그대로 검사하던 테스트를 이 반대 방향
    //   단언으로 바꾼다. **면책이 어디에도 없으면 안 되므로**(CM-C) 같은 테스트에서 상세 쪽
    //   긴 면책이 여전히 나오는지 함께 본다 — 한쪽만 보면 "카드에서 뺐다"가 "어디서도 안 나온다"로
    //   조용히 번진다.
    testWidgets('카드 오버레이 — 칩만 나오고 면책은 없다(면책은 상세가 진다)', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TrustAttributesCardOverlay(
              accidentStatus: '무사고',
              isSingleOwner: null,
              isNonSmoker: null,
            ),
          ),
        ),
      );
      expect(find.text('무사고'), findsOneWidget);
      expect(find.text('판매자 제공 정보'), findsNothing,
          reason: '웹 카드에도 없는 문구다 — 사진 위 좁은 자리에 면책까지 얹지 않는다');
      expect(find.textContaining('판매자가 직접 입력한 정보'), findsNothing);

      // 같은 값을 상세 섹션으로 렌더하면 긴 면책이 반드시 함께 나온다(결속은 상세 한정으로 유지).
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: SingleChildScrollView(
              child: TrustAttributesDetailSection(
                accidentStatus: '무사고',
                isSingleOwner: null,
                isNonSmoker: null,
              ),
            ),
          ),
        ),
      );
      expect(find.textContaining('판매자가 직접 입력한 정보'), findsOneWidget,
          reason: '카드에서 뺀 면책이 상세에도 없으면 검증됨으로 오도된다(CM-C)');
    });

    // 코드리뷰 지적(P6) — 2줄 접힘을 막으려고 Wrap→가로 스크롤(SingleChildScrollView+Row)로
    // 바꾼 패치가 있었는데, 뱃지 3개(무사고·1인소유·비흡연)를 전부 렌더하는 테스트가 0건이라
    // 그 패치 자체가 무가드였다. 실측(390px 뷰포트): 행 너비 214.5px vs 가용 폭 ~310px, 세
    // 뱃지가 dy 255~271 한 줄에 다 들어간다 — 지금은 접힘이 일어나지 않는다.
    testWidgets('카드 행 — 뱃지 3개(무사고·1인소유·비흡연)가 전부 한 줄에 렌더된다(P6)',
        (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TrustAttributesCardOverlay(
              accidentStatus: '무사고',
              isSingleOwner: true,
              isNonSmoker: true,
            ),
          ),
        ),
      );

      final accident = find.text('무사고');
      final singleOwner = find.text('1인소유');
      final nonSmoker = find.text('비흡연');
      expect(accident, findsOneWidget);
      expect(singleOwner, findsOneWidget);
      expect(nonSmoker, findsOneWidget);

      final accidentTop = tester.getTopLeft(accident).dy;
      expect(tester.getTopLeft(singleOwner).dy, accidentTop,
          reason: '세 뱃지가 같은 줄(top)에 있어야 한다 — 다르면 2줄로 접힌 것이다');
      expect(tester.getTopLeft(nonSmoker).dy, accidentTop,
          reason: '세 뱃지가 같은 줄(top)에 있어야 한다 — 다르면 2줄로 접힌 것이다');
    });

    // 코드리뷰 지적(P6) — 이 커밋이 `_TrustChip`의 `onCard`(반투명+블러) 분기를 지우고 카드·
    // 상세가 한 스타일을 공유하게 했는데, '단순교환'/'사고' 같은 중립(비초록) 뱃지를 카드 행
    // 경로(TrustAttributesCardOverlay)로 렌더하는 테스트가 하나도 없었다. 지금까지 카드 레벨
    // 테스트는 전부 '무사고'(초록)거나 전부 null이라, 중립 분기의 `border: Border.all(
    // borderHairline)`이 사라져도(배경이 투명이라 흰 카드 위에서 뱃지 자체가 안 보이게 돼도)
    // 스위트는 green이었다.
    // ✎ 2026-08-13 사용자 지시로 **계약이 뒤집혔다** — '사고'·'단순교환'은 카드 칩에서 뺀다.
    //   (그전엔 중립칩의 테두리·글자색이 흰 카드 위에서 안 보이지 않는지를 봤다.)
    //   정보를 없앤 게 아니라 자리를 옮긴 것이라, **상세에는 여전히 나오는지**를 같은 테스트에서
    //   함께 단언한다 — 한쪽만 보면 "카드에서 뺐다"가 "어디서도 안 보인다"로 조용히 번질 수 있다.
    testWidgets('카드 행 — 사고·단순교환은 칩으로 안 나온다(상세에는 그대로 나온다)',
        (tester) async {
      for (final status in ['사고', '단순교환']) {
        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: TrustAttributesCardOverlay(
                accidentStatus: status,
                isSingleOwner: null,
                isNonSmoker: null,
              ),
            ),
          ),
        );
        expect(find.text(status), findsNothing,
            reason: '카드 칩은 긍정 신호의 자리다 — 부정 상태가 같은 모양으로 섞이면 '
                '"뱃지가 붙어 있다 = 좋은 차"라는 읽기가 무너진다');

        await tester.pumpWidget(
          MaterialApp(
            home: Scaffold(
              body: SingleChildScrollView(
                child: TrustAttributesDetailSection(
                  accidentStatus: status,
                  isSingleOwner: null,
                  isNonSmoker: null,
                ),
              ),
            ),
          ),
        );
        expect(find.text(status), findsOneWidget,
            reason: '상세에서까지 사라지면 구매자가 사고 이력을 알 길이 없다');
      }
    });

    testWidgets('카드 행 — 뱃지 0개면 아무것도(면책도) 그리지 않는다(SizedBox.shrink)', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: TrustAttributesCardOverlay(
              accidentStatus: null,
              isSingleOwner: null,
              isNonSmoker: null,
            ),
          ),
        ),
      );
      // `find.byType(Positioned)` was vacuous(코드리뷰 지적 P6, 구 TrustAttributesCardOverlay
      // 시절 — 그 위젯 자체는 Positioned를 반환하지 않았다). 실제로 뭘 그렸는지(Text 자체가
      // 없어야 함)를 이 위젯의 서브트리로 좁혀 확인한다.
      //
      // 코드리뷰 지적(P7) — 위 `Wrap` 매처는 그 자체로 또 vacuous였다. `TrustAttributesCardOverlay`는
      // 뱃지가 있는 분기(populated branch)에서도 `Wrap`을 렌더한 적이 없다(실제로는
      // `SingleChildScrollView`+`Row` — listing_trust_widgets.dart 참조) — 즉 이
      // `find.byType(Wrap)` → `findsNothing` 단언은 무엇을 해도 항상 참이라 이 위젯을 조금도
      // 검사하지 못했다. populated 분기가 실제로 쓰는 `SingleChildScrollView`로 바꿔야 "0개
      // 분기엔 그 위젯도 없다"가 실제로 의미를 가진다.
      // populated 분기가 실제로 쓰는 위젯으로 좁힌다 — 2026-08-13에 가로 스크롤 행에서
      // `Wrap`(사진 위 오버레이)으로 바뀌었으므로 여기도 함께 바꾼다. 안 바꾸면 "있지도 않은
      // 위젯이 없다"를 단언하는 vacuous 검사로 되돌아간다(P7이 지적했던 바로 그 형태).
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
