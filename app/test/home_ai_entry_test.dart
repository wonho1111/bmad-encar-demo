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
    testWidgets('히어로 배경에 글로우·차 실루엣 장식이 있다(DW-755)', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byKey(const Key('hero_glow')), findsOneWidget);
      expect(find.byKey(const Key('hero_car_silhouette')), findsOneWidget);

      // 코드리뷰 지적(P8) — 키 존재만 보면 위치는 안 잡힌다. 이 장식은 우하단(bottom-right)
      // 오버레이였다가 우상단(top-right)으로 옮겨진 패치라(코드 주석 참조), 그 자리가 되돌아가도
      // 이 검사가 아니면 아무도 못 잡는다.
      final positioned = tester.widget<Positioned>(
        find.ancestor(
          of: find.byKey(const Key('hero_car_silhouette')),
          matching: find.byType(Positioned),
        ),
      );
      expect(positioned.top, isNotNull, reason: '우상단이면 top이 있어야 한다');
      expect(positioned.right, isNotNull, reason: '우상단이면 right가 있어야 한다');
      expect(positioned.bottom, isNull,
          reason: 'bottom이 있으면 우하단으로 되돌아간 것이다(예전 배치)');
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

    // 코드리뷰 패치(spec-16-9 P2) — hero_glow(top:-30/right:-30)·hero_car_silhouette(top:-6/
    // right:-36)는 일부러 밴드 바깥으로 튀어나가게 배치돼 있다. 그걸 밴드 안으로 가둬주는 건
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
