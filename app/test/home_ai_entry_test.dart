// 홈의 AI 진입 형태를 고정한다 — UX 확정 D12: *"AI 검색 = FAB 아님. 홈 최상단 큰 검색부"*.
//
// **이 검사가 존재하는 이유:** 앱 홈엔 `Key('ai_fab')` FAB이 붙어 있었는데, D12가 그걸
// 명시적으로 폐기(*"이전 앱의 AI=FAB는 'AI가 부가기능'이던 흔적 → 폐기"*)한 뒤에도 한 달 넘게
// 남아 있었고 **참조하는 검사가 하나도 없었다**(`grep -rn ai_fab app/` → 구현 1건뿐).
// 웹에서도 같은 날 같은 어긋남을 제거했고(`web/e2e/nav-and-hero.spec.ts` B5b), 앱도 같은 이유로
// 검사를 남긴다 — 문서에만 적어두면 다음에 또 놓친다.
//
// **두 축을 같이 본다.** "FAB이 없다"만 보면 AI 진입이 통째로 사라져도 초록이 된다 —
// 실제로 이번 작업에서 *"FAB만 떼면 AI로 갈 길이 사라진다"* 가 쟁점이었다. 그래서
// "FAB 없음"과 "최상단 AI 진입 있음"을 한 검사 안에서 함께 확인한다.
//
// 이 검사가 **안 보는 것**(추측이 아니라 실제 한계):
//   · 눌렀을 때 실제로 AI 화면이 뜨는지 — 라우팅 push 이후는 Supabase 세션이 필요해 여기선 안 본다.
//     실기기 확인은 Epic 16-6(앱 통합 시연 검증) 몫이다.
//   · 디자인 토큰(웹 petrol 히어로 밴드 미러링)과 하단 4탭 — 둘 다 Story 16.1 몫이라 아직 없다.
//   · 최근 매물 목록 본문 — 아래 harness는 매물 조회를 빈 목록으로 대체한다.
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/core/theme/app_theme.dart';
import 'package:app/features/ai_search/ai_chat_screen.dart';
import 'package:app/features/ai_search/chat_message.dart' show maxQueryLength;
import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listings_providers.dart';

/// 최소한의 가짜 사용자 — 홈은 null 여부(로그인)만 본다(역할 통합 이후 역할은 안 본다).
User _fakeUser() => User(
      id: '00000000-0000-0000-0000-000000000001',
      appMetadata: const {},
      userMetadata: const {},
      aud: 'authenticated',
      email: 'seller@test.com',
      createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
    );

/// 홈을 기기·네트워크 없이 그린다. 최근·인기 매물은 빈 목록으로 대체한다 — 이 검사가 보는 것은
/// 상단 진입 구성(과 spec-16-8의 섹션 순서)이지 목록 본문이 아니다.
Widget _harness() => ProviderScope(
      overrides: [
        currentUserProvider.overrideWithValue(_fakeUser()),
        recentListingsProvider
            .overrideWith((ref) async => const <ListingCardData>[]),
        popularListingsProvider
            .overrideWith((ref) async => const <ListingCardData>[]),
      ],
      child: const MaterialApp(home: HomeScreen()),
    );

void main() {
  group('홈 AI 진입 = 최상단 검색부(FAB 아님) — D12', () {
    testWidgets('FloatingActionButton이 없다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byType(FloatingActionButton), findsNothing);
      // 옛 키가 되살아나는 것도 같이 막는다.
      expect(find.byKey(const Key('ai_fab')), findsNothing);
    });

    testWidgets('AI 진입이 홈 최상단에 있다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byKey(const Key('go_ai')), findsOneWidget,
          reason: 'AI 진입이 사라지면 FAB을 뗀 의미가 없다');
    });

    // spec-16-9(DW-755 해소) — 히어로 바로 아래의 별도 매물 탐색 CTA(`_SearchCta`,
    // `Key('go_search')`)를 같은 커밋에서 제거했다. 채택 전 이 키를 실제로 되살려(뮤테이션)
    // red를 확인하고 되돌려 green을 재확인했다(CLAUDE.md B4).
    testWidgets('go_search는 더 이상 없다 — 히어로 다음 위젯은 차종 칩이다(AC②)', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byKey(const Key('go_search')), findsNothing);

      final ai = find.byKey(const Key('go_ai'));
      final chips = find.byKey(const Key('category_chips'));
      expect(ai, findsOneWidget);
      expect(chips, findsOneWidget);
      expect(tester.getTopLeft(ai).dy, lessThan(tester.getTopLeft(chips).dy),
          reason: '히어로가 차종 칩보다 위에 있어야 한다');
    });

    // spec-16-9(DW-755 해소, AC①) — 히어로가 화면 폭을 꽉 채우는 밴드인지(좌우 여백 0).
    // 예전엔 Center+ConstrainedBox(480)+Padding(16) **안**에 있어 양옆에 여백이 있었다.
    testWidgets('히어로가 화면 폭을 꽉 채운다(좌우 여백 0)', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final heroWidth = tester.getSize(find.byKey(const Key('go_ai'))).width;
      final screenWidth = tester.getSize(find.byType(MaterialApp)).width;
      expect(
        heroWidth,
        screenWidth,
        reason: '히어로 좌우에 여백이 남으면(예전 카드형 레이아웃) 화면 폭과 같지 않게 된다',
      );
    });

    // 코드리뷰 패치(spec-16-9) — 히어로 배경 장식(글로우·차 실루엣)이 스파인이 명시적으로
    // 요구한 요소(DW-755)인데 이걸 보는 테스트가 0건이었다. 존재를 단언한다 — 나중에 누가
    // 실수로 지워도 이 테스트가 잡는다.
    // ✎ 2026-08-10 — amber 글로우는 사용자 결정으로 **제거**됐다(잘린 노란 얼룩으로 읽혔다,
    // DW-770). 그래서 "글로우가 있다"가 아니라 **"없다"**를 단언한다 — 누가 같은 구현을 다시
    // 넣으면 이 테스트가 잡는다. 차 실루엣은 그대로 요구사항이다.
    testWidgets('히어로 배경에 차 실루엣이 있고, amber 글로우 원은 없다(DW-755·DW-770)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byKey(const Key('hero_car_silhouette')), findsOneWidget);
      expect(find.byKey(const Key('hero_glow')), findsNothing,
          reason: '단일 amber 원 글로우는 실기기에서 잘린 얼룩으로 보여 제거했다 — '
              '다시 넣으려면 다중 레이어 메시로(DW-770), 값 하나 되돌리는 식이 아니다');
    });

    // spec-16-10(Always, AC④) — 꽉 찬 Material 아이콘이 아니라 목업과 같은 path의
    // CustomPaint(라인아트)여야 한다. 배치는 이제 Positioned가 아니라 CustomPainter 내부에서
    // 밴드 크기의 비율로 계산되므로(Positioned.fill), 위치 단언은 더 이상 Positioned의
    // top/right/bottom 필드로 볼 수 없다 — "더 이상 Icon이 아니다"를 직접 단언한다. 채택 전
    // 이 위젯을 다시 Icon(Icons.directions_car_filled)으로 되돌려(측정된 뮤테이션) red를
    // 확인하고 되돌려 green을 재확인했다(CLAUDE.md B4).
    testWidgets('hero_car_silhouette가 더 이상 Icon이 아니라 CustomPaint 라인아트다(AC④)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final silhouette = find.byKey(const Key('hero_car_silhouette'));
      expect(silhouette, findsOneWidget);
      expect(tester.widget(silhouette), isA<CustomPaint>(),
          reason: '목업(consistency-1.html .silhouette) 라인아트를 이식한 CustomPainter여야 '
              '한다 — 꽉 찬 Material 아이콘이면 이 단언이 실패한다');
      expect((tester.widget<CustomPaint>(silhouette)).painter, isNotNull,
          reason: 'painter가 null이면 위젯 타입은 그대로 CustomPaint인데 아무것도 안 그려진다');
    });

    // 코드리뷰 지적(이 패스) — 위 테스트는 **위젯 타입**만 본다. 그래서 `painter`가 그리는 내용이
    // 통째로 사라져도(paint() 본문을 비우거나, _carPath()가 빈 Path를 돌려주거나, translate/scale을
    // 서로 바꿔 넣어도) 전 스위트가 green으로 남았다 — spec-16-9에서 이 실루엣이 실제로 표류한
    // 전례가 있는 축인데, CustomPainter로 옮기면서 "무엇이 그려지는가"를 보는 검사가 하나도 없었다.
    // flutter_test의 `paints`(기록 캔버스)로 **실제 드로잉 명령**을 직접 단언한다:
    //   · translate/scale = carSilhouetteOffset이 계산한 값 그대로 캔버스에 적용됐는가
    //     (순수함수 단위테스트는 계산만 보고, 그 결과가 실제로 쓰였는지는 안 본다)
    //   · path = 차체 안쪽 점을 포함하고 바깥(지붕 위·앞범퍼 밖) 점은 제외하는가
    //     — 빈 Path면 includes에서 실패한다. 바퀴 아치 안쪽 점(524,170)을 제외로 두어
    //       SVG sweep-flag→clockwise 매핑이 뒤집히면(아치가 아래로 볼록) 잡히게 한다.
    //   · circle 2개 = 목업 좌표(204/524, 192, r30) 그대로인가
    // 이 세션이 직접 red를 실측 확인했다(뒤 Review Triage Log 참조).
    testWidgets('hero_car_silhouette가 실제로 목업 도형을 그린다(그리기 명령 직접 단언)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final silhouette = find.byKey(const Key('hero_car_silhouette'));

      // 코드리뷰 3패스 지적(verification-gap 렌즈, 실측) — 아래 `paints` 단언은 위젯이 **어떤
      // 크기의 상자를 받았든** 그 크기로 기대값을 다시 계산하므로 항상 자기 자신과 일치한다.
      // 즉 `Positioned.fill`을 spec-16-10 이전의 고정 픽셀 상자(`Positioned(top:-6, right:-36,
      // width:150, height:150)`)로 되돌려도 전 스위트가 green이었다 — 이 스토리가 없앤 바로 그
      // 회귀 형태다. 기대값 계산에 쓰이는 그 크기 자체를 먼저 밴드에 못박아야 단언이 공허해지지
      // 않는다: `Positioned.fill`이면 실루엣 상자 = 히어로 밴드(`go_ai`) 상자다.
      final bandSize = tester.getSize(find.byKey(const Key('go_ai')));
      expect(tester.getSize(silhouette), bandSize,
          reason: '실루엣이 밴드 전체를 덮는 Positioned.fill이 아니면(예: 고정 픽셀 상자로 '
              '되돌아가면) paint()가 받는 size가 밴드 크기가 아니게 되고, 아래 단언들은 '
              '그 잘못된 크기와 자기 자신을 비교하며 통과한다');
      expect(tester.getTopLeft(silhouette), tester.getTopLeft(find.byKey(const Key('go_ai'))),
          reason: '크기만 같고 원점이 어긋나도 배치는 틀어진다');

      final offset = carSilhouetteOffset(bandSize);

      expect(
        silhouette,
        paints
          ..translate(x: offset.dx, y: offset.dy)
          // canvas.scale(s)는 sy를 안 넘기므로 기록에도 y가 null로 남는다(실측: `scale(0.7, null)`)
          // — x만 단언한다.
          ..scale(x: offset.scale)
          ..path(
            includes: const [Offset(320, 150), Offset(100, 160)],
            excludes: const [Offset(320, 10), Offset(20, 40), Offset(524, 170)],
            // 코드리뷰 3패스 지적(adversarial, 실측) — 색·투명도를 아무도 안 봐서 `_opacity`를
            // 0.09→0.85로 바꿔도 전 스위트가 green이었다. 스파인이 이 장식에 요구한 건
            // "옅게, 칩·검색창 비침범"이라 투명도가 곧 요구사항이다(짙어지면 CustomPaint가
            // 글로우 위에 그려져 밴드를 흰색으로 덮는다).
            // 기대값의 `0.09`는 이 테스트가 박는 상수다 — 소스의 `_opacity`는 private이라
            // 여기서 읽어올 수 없고, 읽어오면 그게 곧 자기 자신과의 비교가 된다.
            color: AppColors.onPetrol.withValues(alpha: 0.09),
          )
          ..circle(x: 204, y: 192, radius: 30)
          ..circle(x: 524, y: 192, radius: 30),
      );
    });

    // 코드리뷰 패치(spec-16-9 P1) — 기존 검사는 그라데이션의 colors.first만 AppColors.
    // brandPetrolStrong(홈 탭 AppBar의 단색)과 같은지만 봤다. 그런데 이음매가 실제로 안 보이려면
    // "시작색이 같다"뿐 아니라 "축(begin/end)이 세로"여야 한다 — 대각선(topLeft→bottomRight)
    // 이면 히어로 윗변의 오른쪽으로 갈수록 이미 petrolDeepest 쪽으로 섞여 AppBar와 만나는 경계
    // 오른쪽 절반에서 색이 꺾인다(코드 주석 실측치 참조). 이 검사가 axis를 직접 보지 않으면
    // 대각선으로 되돌리는 리팩터도 green으로 통과한다.
    testWidgets('히어로 그라데이션 축이 topCenter→bottomCenter다(AppBar 이음매가 안 보이려면 '
        '대각선이 아니라 세로축이어야 한다, AC①)', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final container =
          tester.widget<Container>(find.byKey(const Key('go_ai')));
      final gradient = (container.decoration as BoxDecoration).gradient as LinearGradient;
      expect(gradient.begin, Alignment.topCenter);
      expect(gradient.end, Alignment.bottomCenter);
    });

    // 코드리뷰 패치(spec-16-9 P2) — hero_glow(top:-30/right:-30)는 일부러 밴드 바깥으로
    // 튀어나가게 배치돼 있다(spec-16-10부터 hero_car_silhouette도 CustomPainter 내부에서
    // 밴드 밖으로 그려진다 — 둘 다 이 clip이 없으면 새어나간다). 그걸 밴드 안으로 가둬주는 건
    // 오직 이 Container의 clipBehavior뿐인데, 지금까지 아무 테스트도 그 값을 보지 않았다 —
    // Stack은 자식이 부모 밖으로 나가도 오버플로 에러를 던지지 않으므로(clip이 없어도 조용히
    // 통과), clipBehavior를 지워도 전체 스위트가 green으로 남는다. amber 글로우가 petrol
    // AppBar 위로 번져 보이는 회귀를 잡을 유일한 장치라 직접 단언한다.
    testWidgets('히어로 Container가 Clip.hardEdge다(밴드 밖 장식이 새어나가지 않게, P2)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final container =
          tester.widget<Container>(find.byKey(const Key('go_ai')));
      expect(container.clipBehavior, Clip.hardEdge);
    });

    // spec-16-10(Always) — 히어로 하단 곡률 22→16(사용자가 실기기 육안으로 과하다고 판단,
    // Design Notes). 코드리뷰 지적 — 카드 radius(listing_card_test.dart)만 테스트가 있고
    // 이 축은 아무 테스트도 안 봤다. 채택 전 16을 22로 되돌려(측정된 뮤테이션) red를 확인하고
    // 되돌려 green을 재확인했다(CLAUDE.md B4).
    testWidgets('히어로 밴드 하단 곡률이 16이다(spec-16-10, 22에서 낮춤)', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final container =
          tester.widget<Container>(find.byKey(const Key('go_ai')));
      final decoration = container.decoration as BoxDecoration;
      final radius = decoration.borderRadius as BorderRadius;
      expect(radius.bottomLeft, const Radius.circular(16));
      expect(radius.bottomRight, const Radius.circular(16));
      // 코드리뷰 지적(이 패스) — 아래 두 줄이 없으면 `BorderRadius.circular(16)`(네 모서리 전부)로
      // 바꿔도 이 테스트가 통과한다. 그런데 위쪽 모서리가 둥글어지는 순간 spec-16-9 AC①이 요구한
      // "앱바~히어로가 색 경계 없이 한 면"이 깨진다(위 코드 주석: 위쪽은 각지게 유지).
      expect(radius.topLeft, Radius.zero, reason: '히어로 상단은 AppBar와 맞닿으므로 각져야 한다');
      expect(radius.topRight, Radius.zero, reason: '히어로 상단은 AppBar와 맞닿으므로 각져야 한다');
    });

    // spec-16-8 Review Triage Log #8 — 빈/공백만 입력해도 조용히 아무 일도 안 하는 기존 관례
    // (AiChatScreen._submit·웹 HeroSearch.submit과 동일)를 이 히어로 제출 경로도 따른다.
    // 동작 자체는 바꾸지 않고(이미 옳다), 실제로 그 가드가 작동하는지 처음으로 확인한다.
    testWidgets('공백만 입력하고 검색 버튼을 눌러도 AiChatScreen으로 안 넘어간다(#8)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      await tester.enterText(find.byKey(const Key('hero_query_input')), '   ');
      await tester.tap(find.byKey(const Key('hero_search_button')));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(
        find.byType(AiChatScreen),
        findsNothing,
        reason: '공백만 입력한 제출은 조용히 무시돼야 한다(AiChatScreen으로 넘어가면 안 된다)',
      );
      expect(find.byKey(const Key('go_ai')), findsOneWidget,
          reason: '제출이 무시됐다면 홈 히어로가 그대로 남아 있어야 한다');
    });
  });

  // spec-16-10(DW-767 해소) — 히어로 마감 4축(타이포·eyebrow·검색창 테두리·실루엣) 중 실루엣은
  // 위 그룹에 이미 있다. 여기는 나머지 축 — 헤드라인 관계 크기·eyebrow 위치·검색창 유효 테두리.
  group('히어로 마감(spec-16-10, DW-767 해소) — 타이포·테두리', () {
    // AC — 헤드라인 위에 eyebrow가 먼저(더 위에) 렌더돼야 한다. 채택 전 eyebrow의
    // SizedBox(height: 10)를 지워 헤드라인 앞으로 옮기지 않고 그대로 뒀다가(순서 자체를
    // 바꾸는 뮤테이션으로) red를 확인하고 되돌려 green을 재확인했다(CLAUDE.md B4).
    testWidgets('eyebrow 라벨 "AI 매물 검색"이 헤드라인보다 위에 있다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final eyebrow = find.byKey(const Key('hero_eyebrow'));
      final headline = find.byKey(const Key('hero_headline'));
      expect(eyebrow, findsOneWidget);
      expect(headline, findsOneWidget);
      expect(find.text('AI 매물 검색'), findsOneWidget);

      expect(tester.getTopLeft(eyebrow).dy, lessThan(tester.getTopLeft(headline).dy),
          reason: 'eyebrow가 헤드라인 아래로 밀리면 "먼저 알린다"는 의도가 깨진다');
    });

    // AC — 새 색 토큰 없이 기존 AppColors만 쓴다(Always). 텍스트·테두리=onPetrolMuted,
    // 점 인디케이터=accentAmber(Design Notes의 예시 배정을 그대로 코드로 고정). 코드리뷰
    // 지적 — 처음엔 텍스트·점 색만 보고 pill 테두리(Border.all(onPetrolMuted))는 빠져 있었다
    // (AC의 "테두리=onPetrolMuted" 절반이 검사 없이 통과할 수 있었다).
    testWidgets('eyebrow는 새 색 토큰 없이 기존 AppColors(onPetrolMuted·accentAmber)로만 그려진다',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final text = tester.widget<Text>(find.text('AI 매물 검색'));
      expect(text.style?.color, AppColors.onPetrolMuted);

      final pill = tester.widget<Container>(find.byKey(const Key('hero_eyebrow')));
      final pillBorder = (pill.decoration as BoxDecoration).border as Border;
      // 코드리뷰 지적(이 패스) — 여기서 alpha까지 못박으면(예전엔 `withValues(alpha: 0.35)`로
      // 단언했다) 스펙 Always가 "검사도 색을 단언하지 않는다"고 한 이유(목업 간 색조가 갈린다)를
      // 정면으로 어긴다. 투명도를 조금 조정하는 정당한 변경에도 red가 난다. AC가 실제로 요구하는
      // 건 "새 색 토큰 없이 기존 팔레트에서 골랐다"는 **출처**뿐이므로, alpha를 빼고 밑색만 본다.
      expect(pillBorder.top.color.withValues(alpha: 1), AppColors.onPetrolMuted.withValues(alpha: 1),
          reason: '테두리 색이 기존 AppColors(onPetrolMuted) 계열에서 나와야 한다(농도는 자유)');

      final dot = tester.widget<Container>(
        find.descendant(
          of: find.byKey(const Key('hero_eyebrow')),
          matching: find.byWidgetPredicate((w) =>
              w is Container &&
              w.decoration is BoxDecoration &&
              (w.decoration as BoxDecoration).shape == BoxShape.circle),
        ),
      );
      expect((dot.decoration as BoxDecoration).color, AppColors.accentAmber);
    });

    // AC — eyebrow는 "자간 넓힌 12px"(스펙 Always가 `DESIGN.md typography.scale.caption`과
    // 크기가 일치한다고 명시한 값)여야 한다. 코드리뷰 3패스 지적(adversarial, 실측) — 위
    // 두 테스트는 색과 세로 순서만 봐서 `fontSize: 12 → 26`, `letterSpacing: 1.4 → 0`을
    // 동시에 넣어도 전 스위트가 green이었다. 즉 이 스토리가 고치려던 바로 그 결함(타이포가
    // 검사되지 않아 조용히 어긋나는 것)이 새로 만든 요소에 그대로 남아 있었다.
    //
    // 크기는 DW-767이 세운 원칙대로 **관계**로 단언한다(eyebrow < 헤드라인) — 스파인의
    // caption(12)과 display(36)이 나중에 함께 조정돼도 위계는 유지돼야 한다. 자간만 절대값
    // 방향으로 본다(0보다 크다 = "넓혔다"가 곧 요구사항 자체라 관계로 바꿀 대상이 없다).
    testWidgets('eyebrow가 헤드라인보다 작고 자간이 넓다(typography.scale.caption 위계)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final eyebrowStyle = tester.widget<Text>(find.text('AI 매물 검색')).style!;
      final headlineSize = (tester
              .renderObject<RenderParagraph>(find.byKey(const Key('hero_headline')))
              .text as TextSpan)
          .style!
          .fontSize!;

      expect(eyebrowStyle.fontSize, isNotNull);
      expect(eyebrowStyle.fontSize!, lessThan(headlineSize),
          reason: 'eyebrow가 헤드라인만큼 커지면 "먼저 작게 알리고 헤드라인이 주인공"이라는 '
              '위계가 사라진다 — 목업 .eyebrow는 12px, 헤드라인은 display 스케일이다');
      expect(eyebrowStyle.letterSpacing, isNotNull);
      expect(eyebrowStyle.letterSpacing!, greaterThan(0),
          reason: '스펙 Always가 요구한 "자간 넓힌" 라벨 — 0이면 목업의 pill 라벨 느낌이 사라진다');
    });

    // AC — 헤드라인이 "원하는 차를" / "말로 찾으세요" 2줄로 나타난다. 이건 **스냅샷**이라
    // 36을 그대로 박아도 된다(DW-767 관계 요구는 아래 별도 테스트가 진다 — 코드리뷰 지적:
    // 이 테스트에 절대값 단언까지 같이 있으면 그게 먼저 깨져서 관계 단언이 생존자로서
    // 실제로 실행되는지 확인할 길이 없어진다).
    // ✎ 2026-08-10 사용자 육안 결정으로 값이 바뀌었다: 36px 2줄 → **24px 한 줄**.
    // 이 크기는 세 번 뒤집혔다(19 → 36 → 24) — 전부 사람이 실기기를 보고 내린 판단이다.
    // 그래서 여기서만은 절대값을 **일부러** 박는다: 다음 사람이 값을 조용히 바꾸면 red로
    // 알리는 게 목적이고, 바꾸려면 사용자 판단이 다시 필요하다는 뜻이다. 크기의 **역할**
    // (카드 차량명보다 크다)은 아래 별도 테스트가 관계로 지키므로 두 축이 겹치지 않는다.
    testWidgets('헤드라인이 24px(app-home-2 목업)·하드 줄바꿈 없이 렌더된다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final headlineSpan =
          tester.renderObject<RenderParagraph>(find.byKey(const Key('hero_headline'))).text;
      expect((headlineSpan as TextSpan).style?.fontSize, 24);

      // 한 줄 — 문구 안에 **하드 줄바꿈이 없어야** 한다. 폭이 좁아 자연 줄바꿈으로 2줄이
      // 되는 것은 결함이 아니지만(D5의 "세로로 접지 않는다"는 가로 배치 규칙이지 문장
      // 규칙이 아니다), `\n`을 박아 넣으면 **어떤 폭에서도 무조건 2줄**이 된다.
      expect(headlineSpan.toPlainText(), '원하는 차를 말로 찾으세요');
      expect(headlineSpan.toPlainText().contains('\n'), isFalse,
          reason: '하드 줄바꿈이 다시 들어가면 넓은 화면에서도 강제로 2줄이 된다');
    });

    // AC — 헤드라인의 실효 fontSize가 매물 카드 차량명의 실효 fontSize보다 커야 한다
    // (DW-767 — "숫자를 박지 말고 관계로 박아야 토큰이 바뀌어도 산다"는 그 항목 자신의
    // trigger 문구 그대로: 이 테스트는 양쪽 크기를 변수로만 읽고 비교할 뿐, 어느 쪽도
    // 하드코딩하지 않는다 — 36이 나중에 32나 40으로 바뀌어도 이 테스트는 안 깨져야 한다).
    // `buildAppTheme()`를 명시해 실제 앱 테마로 pump한다(themeless `MaterialApp`은 카드
    // 차량명의 앰비언트 기본 텍스트 스타일이 실제 앱과 우연히 같을 뿐 보장되지 않는다 —
    // 위 검색창 테두리 테스트와 같은 이유). 채택 전 헤드라인 fontSize를 12로 낮춰(측정된
    // 뮤테이션) red를 확인하고 36으로 되돌려 green을 재확인했다(CLAUDE.md B4).
    testWidgets('헤드라인 실효 fontSize가 매물 카드 차량명의 실효 fontSize보다 크다(DW-767, 관계만)',
        (tester) async {
      const listing = ListingCardData(
        id: 'l1',
        manufacturer: '현대',
        model: '아반떼',
        year: 2021,
        price: 18000000,
        mileage: 20000,
        region: '서울',
      );
      await tester.pumpWidget(ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider.overrideWith((ref) async => const <ListingCardData>[]),
          popularListingsProvider.overrideWith((ref) async => const [listing]),
        ],
        child: MaterialApp(theme: buildAppTheme(), home: const HomeScreen()),
      ));
      await tester.pumpAndSettle();

      final headlineSize = tester
          .renderObject<RenderParagraph>(find.byKey(const Key('hero_headline')))
          .text
          .style
          ?.fontSize;

      final cardNameFinder = find.text('[현대] 아반떼 · 2021년');
      expect(cardNameFinder, findsOneWidget);
      // 이 값을 하드코딩하지 않는다 — `listing_card.dart`의 차량명 `Text`엔 fontSize가 없어
      // buildAppTheme()의 앰비언트 기본 텍스트 스타일(Material 3 bodyMedium 상당, 실측
      // 14px — DESIGN.md의 card-title 토큰(16px)이 아니다, 그 토큰은 아직 이 Text에 배선돼
      // 있지 않다)을 그대로 상속한다. 이 테스트는 "지금 몇 px인가"가 아니라 "헤드라인보다
      // 작은가"만 본다.
      final cardNameSize =
          tester.renderObject<RenderParagraph>(cardNameFinder).text.style?.fontSize;

      expect(headlineSize, isNotNull);
      expect(cardNameSize, isNotNull);
      expect(headlineSize!, greaterThan(cardNameSize!),
          reason: '헤드라인이 카드 차량명보다 커야 한다 — 예전엔 19px로 카드 차량명과 비슷하거나 '
              '작았다(DW-767 원인)');
    });

    // AC — 히어로 검색창은 활성·포커스 상태 모두 "실제로 그려지는 테두리"가 없어야 한다.
    // Design Notes: 로컬 `InputDecoration.border`만 보면 이미 InputBorder.none이라
    // vacuous(공허)해진다 — `applyDefaults` 이후의 유효 enabledBorder/focusedBorder를 봐야
    // 테마의 OutlineInputBorder가 새어 나오는지 실제로 잡힌다.
    //
    // 이 테스트는 반드시 `buildAppTheme()`(실제 앱이 main.dart에서 쓰는 그 테마)로 pump해야
    // 한다 — `_harness()`는 테마 없는 기본 `MaterialApp`이라 `Theme.of(context)
    // .inputDecorationTheme`가 app_theme.dart의 OutlineInputBorder를 아예 안 갖고 있다. 이
    // 세션이 직접 재검증하며 실측한 사실: `_harness()`로 이 검사를 돌리면 enabledBorder를
    // 지워도(뮤테이션) `effective.enabledBorder`가 `null`이 될 뿐 앱의 실제 테마가 새는지는
    // 전혀 증명하지 못한다(테마 자체가 로드되지 않으니 항상 null) — 이 버그의 원인이었던
    // "테마가 새어나온다"는 시나리오를 검사가 실제로는 보지 못하는 vacuous 상태였다. 그래서
    // 이 테스트만 실제 테마로 pump하도록 고쳤다.
    //
    // 채택 전 enabledBorder·focusedBorder 두 줄을 지워(측정된 뮤테이션, border:
    // InputBorder.none만 남김) red를 확인하고(`Expected: null, Actual: OutlineInputBorder`로
    // 테마의 실제 OutlineInputBorder가 새어나오는 것까지 확인) 되돌려 green을 재확인했다
    // (CLAUDE.md B4).
    testWidgets(
        '히어로 검색창은 activation·focus 상태 모두 유효 enabledBorder/focusedBorder가 '
        'InputBorder.none이다(실제 app_theme로 pump)', (tester) async {
      await tester.pumpWidget(ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider.overrideWith((ref) async => const <ListingCardData>[]),
          popularListingsProvider.overrideWith((ref) async => const <ListingCardData>[]),
        ],
        child: MaterialApp(theme: buildAppTheme(), home: const HomeScreen()),
      ));
      await tester.pump();

      final field = tester.widget<TextField>(find.byKey(const Key('hero_query_input')));
      final context = tester.element(find.byKey(const Key('hero_query_input')));
      final theme = Theme.of(context).inputDecorationTheme;
      // 테마가 실제로 로드됐는지부터 확인한다 — 그러지 않으면 아래 단언이 다시 vacuous해진다.
      expect(theme.enabledBorder, isA<OutlineInputBorder>(),
          reason: '이 pump가 app_theme.dart를 실제로 쓰고 있는지 확인하는 카나리아 — 여기서부터 '
              'null이면 아래 단언은 아무것도 증명하지 못한다');
      final effective = field.decoration!.applyDefaults(theme);

      expect(effective.enabledBorder, InputBorder.none,
          reason: '로컬 enabledBorder가 없으면 applyDefaults가 테마의 OutlineInputBorder로 '
              '채운다(app_theme.dart) — 실제로 그려지는 테두리가 생긴다');
      expect(effective.focusedBorder, InputBorder.none,
          reason: '로컬 focusedBorder가 없으면 포커스 시 테마의 petrol OutlineInputBorder가 뜬다');
    });

    // 코드리뷰 지적 — `hero_car_silhouette`가 더 이상 Icon이 아니라는 위젯 테스트(위 그룹)는
    // "라인아트로 바뀌었다"만 보고 **어디에 그려지는지는 안 본다**. spec-16-9는 이 실루엣이
    // 우하단으로 표류한 실제 회귀를 `Positioned` 필드로 잡은 적이 있는데, CustomPainter로
    // 옮긴 뒤(spec-16-10) 그 자리를 대신 지키는 검사가 없었다 — `carSilhouetteOffset`의
    // 부호(`rightFraction`/`topFraction`) 하나가 뒤집혀도 잡을 도리가 없었다. `paint()` 내부
    // 계산이라 위젯 트리로는 안 보이므로(listing_card.dart `safeCardPhotoHeight`와 같은 이유)
    // 순수 함수로 뽑아 여기서 직접 잰다. 두 가지 밴드 크기로 검증해 부호·비례(퍼센트 기반임)
    // 둘 다 확인한다 — 하나만 보면 고정 픽셀로 되돌아가도 우연히 같은 크기에서만 통과할 수
    // 있다.
    // ✎ 2026-08-10 사용자 결정으로 배치가 **웹 값으로 통일**됐다(top:-14% → bottom:-6%).
    // 웹(`HeroSearch.tsx`)과 같은 규칙인지를 이 테스트가 지킨다 — 한쪽만 바꾸면 두 화면이
    // 또 갈린다(그게 이 변경의 발단이었다).
    test('carSilhouetteOffset — 웹과 같은 CSS 퍼센트(right:-4%·bottom:-6%·width:58%)를 '
        '부호까지 정확히 환산한다', () {
      final a = carSilhouetteOffset(const Size(400, 200));
      expect(a.scale, closeTo(0.3625, 1e-9)); // (400*0.58)/640
      expect(a.dx, closeTo(184, 1e-9)); // 400 - 232 + 0.04*400
      // 요소 높이 = 220 * 0.3625 = 79.75 → dy = 200 - 79.75 + 0.06*200 = 132.25
      expect(a.dy, closeTo(132.25, 1e-9));

      // 우측 밖으로 흘러나가는지(right:-4%) — 실루엣 우측 끝이 밴드 우측 끝을 넘어야 한다.
      final elementWidthA = 400 * 0.58;
      expect(a.dx + elementWidthA, greaterThan(400));

      // 아래로도 흘러나가는지(bottom:-6%) — 실루엣 아래 끝이 밴드 아래 끝을 넘어야 한다.
      expect(a.dy + 220 * a.scale, greaterThan(200));

      // 다른 밴드 크기에서도 같은 퍼센트 규칙을 유지하는지(고정 픽셀로 되돌아가는 회귀 방지).
      final b = carSilhouetteOffset(const Size(1000, 300));
      expect(b.scale, closeTo(0.90625, 1e-9)); // (1000*0.58)/640
      expect(b.dx, closeTo(460, 1e-9)); // 1000 - 580 + 0.04*1000
      expect(b.dy, closeTo(300 - 220 * 0.90625 + 18, 1e-9));
      expect(b.scale / a.scale, closeTo(1000 / 400, 1e-9),
          reason: '고정 픽셀이면 이 비율이 안 맞는다 — scale은 밴드 폭에 비례해야 한다');
    });
  });

  // spec-16-8(DW-736 해소) — 웹 랜딩(Epic 11) 정보구조 미러: 히어로 > 차종칩 > "지금 인기" >
  // "방금 올라온 매물" 순서, 그리고 Epic 7 잔재 퀵액션 3개가 같은 커밋에서 사라졌는지.
  //
  // "있음/없음"이 아니라 **좌표·개수로** 단언한다(home_ai_entry_test.dart 선례와 같은 원칙) —
  // 있기만 하면 통과시키면 섹션이 엉뚱한 순서로 밀려도 초록이 된다. 채택 전 순서를 실제로
  // 한 번 뒤집어(SizedBox 순서 교환) red를 확인하고 되돌려 green을 재확인했다(CLAUDE.md B4:
  // "재보기 전엔 선언하지 않는다").
  group('홈 정보구조 = 웹 랜딩 미러(spec-16-8, DW-736 해소)', () {
    testWidgets('히어로 > 차종칩 > "지금 인기" > "방금 올라온 매물" 순서로 렌더된다(AC1)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final hero = find.byKey(const Key('go_ai'));
      final chips = find.byKey(const Key('category_chips'));
      final popular = find.text('지금 인기');
      final recent = find.text('방금 올라온 매물');

      expect(hero, findsOneWidget, reason: '히어로가 사라지면 순서 자체를 잴 수 없다');
      expect(chips, findsOneWidget, reason: '차종 칩 줄이 있어야 한다');
      expect(popular, findsOneWidget, reason: '"지금 인기" 섹션이 있어야 한다');
      expect(recent, findsOneWidget,
          reason: '"최근 매물"이 아니라 "방금 올라온 매물"로 개칭돼 있어야 한다');

      final heroY = tester.getTopLeft(hero).dy;
      final chipsY = tester.getTopLeft(chips).dy;
      final popularY = tester.getTopLeft(popular).dy;
      final recentY = tester.getTopLeft(recent).dy;

      expect(heroY, lessThan(chipsY), reason: '히어로가 차종 칩보다 위에 있어야 한다');
      expect(chipsY, lessThan(popularY), reason: '차종 칩이 "지금 인기"보다 위에 있어야 한다');
      expect(popularY, lessThan(recentY),
          reason: '"지금 인기"가 "방금 올라온 매물"보다 위에 있어야 한다');
    });

    testWidgets('Epic 7 잔재 퀵액션 3개(문의 채팅·매물 등록·내 매물 관리)는 어디에도 없다(AC4)',
        (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byKey(const Key('go_chat')), findsNothing,
          reason: '문의 채팅 퀵액션은 하단 "채팅" 탭과 목적지가 겹쳐 제거 대상이었다');
      expect(find.byKey(const Key('go_sell')), findsNothing,
          reason: '매물 등록 퀵액션은 하단 "내차팔기" 탭과 목적지가 겹쳐 제거 대상이었다');
      expect(find.byKey(const Key('go_my_listings')), findsNothing,
          reason: '내 매물 관리 퀵액션도 같은 이유로 제거 대상이었다');
    });

    // spec-16-9 Always — 차종 칩 "전체"는 항상 petrol 채움(선택) 상태로 보인다(정적 표시일
    // 뿐, 이 화면엔 실제 필터 선택 추적이 없다). 나머지 5개는 기존 아웃라인 스타일 그대로.
    testWidgets('차종 칩 "전체"는 petrol 채움, 나머지는 아웃라인 스타일이다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final allChip = tester.widget<Container>(
        find.descendant(
          of: find.byKey(const ValueKey('category_chip_전체')),
          matching: find.byType(Container),
        ),
      );
      final allDecoration = allChip.decoration as BoxDecoration;
      expect(allDecoration.color, AppColors.brandPetrol);
      expect(allDecoration.border, isNull);

      final suvChip = tester.widget<Container>(
        find.descendant(
          of: find.byKey(const ValueKey('category_chip_SUV')),
          matching: find.byType(Container),
        ),
      );
      final suvDecoration = suvChip.decoration as BoxDecoration;
      expect(suvDecoration.color, AppColors.surfaceRaised);
      expect(suvDecoration.border, isNotNull);
    });

    // I/O 매트릭스(spec-16-8) "인기 조회 실패" 행 — popularListingsProvider 가 에러여도
    // _PopularListings(별개 ConsumerWidget)만 에러 문구를 보이고, 나머지 섹션은 그 에러와
    // 무관하게 정상 렌더돼야 한다(웹 fetchSection의 섹션별 독립 격리 미러). 지금까지는 이
    // provider가 성공(빈 목록)으로만 오버라이드돼 이 분기를 검사가 한 번도 안 밟았다.
    testWidgets('"지금 인기" 조회 실패 시 그 섹션만 에러, 나머지 섹션은 정상 렌더(I/O 매트릭스)',
        (tester) async {
      await tester.pumpWidget(ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider
              .overrideWith((ref) async => const <ListingCardData>[]),
          popularListingsProvider.overrideWith(
              (ref) => Future<List<ListingCardData>>.error('인기 매물 조회 실패')),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ));
      // pump() 1회는 로딩 프레임만 그린다(실측 확인) — Future.error가 마이크로태스크로
      // resolve된 뒤 에러 상태로 리빌드될 때까지 pumpAndSettle로 흘려보낸다.
      await tester.pumpAndSettle();

      // "지금 인기" 섹션은 에러 문구로 대체된다(home_screen.dart _PopularListings error 분기).
      expect(find.byKey(const Key('popular_error')), findsOneWidget,
          reason: '인기 섹션은 에러 상태를 자체 문구로 보여줘야 한다');
      expect(find.text('지금 인기 매물을 불러오지 못했습니다.'), findsOneWidget);

      // 나머지는 그 에러와 무관하게 정상 렌더돼야 한다 — 섹션별 독립 격리.
      expect(find.byKey(const Key('go_ai')), findsOneWidget,
          reason: '히어로는 인기 섹션 에러와 무관해야 한다');
      expect(find.byKey(const Key('category_chips')), findsOneWidget,
          reason: '차종 칩 줄도 인기 섹션 에러와 무관해야 한다');
      expect(find.text('방금 올라온 매물'), findsOneWidget,
          reason: '"방금 올라온 매물" 섹션도 인기 섹션 에러와 무관하게 렌더돼야 한다');
    });

    // T9(spec-16-8 검증 갭) — 위 테스트는 "popular 실패 → 나머지 정상" 방향만 본다. 반대
    // 방향("recent 실패 → 나머지(히어로·차종칩·popular) 정상")은 어떤 테스트도 보지 않았다 —
    // 두 섹션이 실제로는 별개 ConsumerWidget(_PopularListings·_RecentListings)이라 한쪽이
    // 무너져도 다른 쪽이 안 죽어야 하는데, 예를 들어 두 섹션이 하나의 공유 에러 경로로
    // 합쳐지는 회귀가 나도 이 반대 방향을 보는 테스트가 없으면 못 잡는다.
    // recent_error 키(home_screen.dart _RecentListings error 분기)는 바로 이 테스트를 위해
    // 붙었다.
    testWidgets('"방금 올라온 매물" 조회 실패 시 그 섹션만 에러, 나머지 섹션은 정상 렌더(T9, I/O 매트릭스 반대 방향)',
        (tester) async {
      await tester.pumpWidget(ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider.overrideWith(
              (ref) => Future<List<ListingCardData>>.error('최근 매물 조회 실패')),
          popularListingsProvider
              .overrideWith((ref) async => const <ListingCardData>[]),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ));
      await tester.pumpAndSettle();

      // "방금 올라온 매물" 섹션은 에러 문구로 대체된다(home_screen.dart _RecentListings error 분기).
      expect(find.byKey(const Key('recent_error')), findsOneWidget,
          reason: '방금 올라온 매물 섹션은 에러 상태를 자체 문구로 보여줘야 한다');
      expect(find.text('방금 올라온 매물을 불러오지 못했습니다.'), findsOneWidget);

      // 나머지는 그 에러와 무관하게 정상 렌더돼야 한다 — 섹션별 독립 격리(반대 방향).
      expect(find.byKey(const Key('go_ai')), findsOneWidget,
          reason: '히어로는 최근 매물 섹션 에러와 무관해야 한다');
      expect(find.byKey(const Key('category_chips')), findsOneWidget,
          reason: '차종 칩 줄도 최근 매물 섹션 에러와 무관해야 한다');
      expect(find.text('지금 인기'), findsOneWidget,
          reason: '"지금 인기" 섹션도 최근 매물 섹션 에러와 무관하게 렌더돼야 한다');
      expect(find.byKey(const Key('popular_error')), findsNothing,
          reason: '"지금 인기" 섹션은 정상 데이터 상태라 에러 문구가 없어야 한다');
    });
  });

  // T8(spec-16-8 검증 갭) — 히어로 제출(_AiSearchCta._submit)의 세 후처리(500자 방어적
  // 자르기·검색 버튼 제출 후 입력창 비우기·칩 제출은 입력창 보존)를 실제로 지키는지 아무
  // 테스트도 보지 않았다. 측정된 뮤테이션(두 500자 상한 지점을 maxQueryLength*10으로 풀고
  // _controller.clear()를 지움)이 스위트를 green으로 유지했다.
  group('히어로 제출 후처리 — 500자 방어적 자르기·입력창 비움/보존(T8, spec-16-8 AC1·AC5)', () {
    // AiChatScreen이 initState에서 곧바로 실 searchAi를 호출하므로(테스트 전용 override를
    // 홈이 넘기지 않는다), app_router_test.dart와 같은 이유로 Supabase를 가짜 자격증명으로
    // 초기화해 둔다 — 초기화하지 않으면 `Supabase.instance` 접근 자체가 StateError를 던져
    // "AI 검색에 실패했습니다"라는 별개의 일반 오류로 뒤섞인다. 초기화해 두면
    // `accessToken == null`이 즉시(네트워크 없이) `AiSearchException('로그인이 필요합니다…')`을
    // 던져 결정적이다(ai_search_api.dart).
    setUpAll(() async {
      TestWidgetsFlutterBinding.ensureInitialized();
      SharedPreferences.setMockInitialValues({});
      await Supabase.initialize(
        url: 'https://example.supabase.co',
        // ignore: deprecated_member_use
        anonKey: 'test-anon-key-not-real',
      );
    });

    testWidgets(
        'maxQueryLength자를 초과해 입력하고 검색 버튼으로 제출하면 AiChatScreen에는 정확히 '
        'maxQueryLength자만 전달되고 "질문이 너무 깁니다" 에러가 뜨지 않는다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final longQuery = '가' * (maxQueryLength + 50);
      await tester.enterText(
          find.byKey(const Key('hero_query_input')), longQuery);
      await tester.tap(find.byKey(const Key('hero_search_button')));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      final aiChatScreen =
          tester.widget<AiChatScreen>(find.byType(AiChatScreen));
      expect(
        aiChatScreen.initialQuery?.characters.length,
        maxQueryLength,
        reason: '히어로가 500자 방어적 자르기를 하지 않으면(측정된 뮤테이션) 초과분이 그대로 '
            'AiChatScreen에 전달된다',
      );
      // AiChatScreen이 initState에서 곧바로 검색을 시도하다 실 세션이 없어 실패하므로
      // "로그인이 필요합니다…" 류의 일반 오류는 뜬다(이 테스트가 보려는 것과 무관) — 여기서
      // 확인할 것은 그 특정 "질문이 너무 깁니다" 문구가 **아니라는** 점이다. 그 문구가 뜨면
      // 히어로가 자르지 않은 채로 넘겼다는 뜻이다.
      expect(
        find.text('질문이 너무 깁니다. $maxQueryLength자 이내로 줄여 다시 시도해주세요.'),
        findsNothing,
        reason: 'AiChatScreen에 500자 초과 질의가 전달되면 그 화면 자신의 상한 검사가 이 문구를 '
            '띄운다 — 히어로가 이미 잘라 보냈어야 이 문구가 없다',
      );
    });

    testWidgets('검색 버튼으로 제출하면 hero_query_input의 입력창이 비워진다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      // 컨트롤러를 push 전에 미리 잡아둔다 — push 뒤에는 HomeScreen이 완전히 가려진
      // 이전 route가 되어 skipOffstage 기본값인 find.byKey가 더 이상 찾지 못한다(위 T4
      // 테스트들의 "offstage 무관" 주석과 같은 메커니즘). 컨트롤러는 위젯이 아니라 평범한
      // Dart 객체라 참조만 있으면 이후에도 값을 직접 읽을 수 있다.
      final controller =
          tester.widget<TextField>(find.byKey(const Key('hero_query_input'))).controller!;

      await tester.enterText(
          find.byKey(const Key('hero_query_input')), '아반떼 찾아줘');
      await tester.tap(find.byKey(const Key('hero_search_button')));
      await tester.pumpAndSettle();

      expect(
        controller.text,
        isEmpty,
        reason: '검색 버튼 제출 후 입력창을 비우지 않으면(_controller.clear() 누락) '
            'AiChatScreen에서 뒤로가기로 돌아왔을 때 방금 검색한 문장이 그대로 남는다',
      );
    });

    testWidgets('제안 칩으로 제출해도 입력창에 남아있던 타이핑 초안은 그대로 보존된다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final controller =
          tester.widget<TextField>(find.byKey(const Key('hero_query_input'))).controller!;

      await tester.enterText(
          find.byKey(const Key('hero_query_input')), '내가 쓰던 초안');
      await tester.tap(
          find.byKey(const ValueKey('hero_suggestion_가성비 좋은 첫차')));
      await tester.pumpAndSettle();

      expect(
        controller.text,
        '내가 쓰던 초안',
        reason: '제안 칩 제출은 그 칩 문장만 보내야 한다 — 입력창의 독립적인 타이핑 초안까지 '
            '지우면 칩 탭 전에 쓰던 글이 사라진다(fromChip 예외가 사라지는 뮤테이션이면 여기서 '
            '빈 문자열이 된다)',
      );

      final aiChatScreen =
          tester.widget<AiChatScreen>(find.byType(AiChatScreen));
      expect(aiChatScreen.initialQuery, '가성비 좋은 첫차',
          reason: '칩 제출은 칩 문장 자체를 AiChatScreen에 넘겨야 한다');
    });
  });
}
