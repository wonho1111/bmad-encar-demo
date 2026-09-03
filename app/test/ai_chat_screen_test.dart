// AiChatScreen 배선 테스트(Story 16.3 코드리뷰 지적) — search_screen_test.dart·
// home_screen_wishlist_test.dart와 같은 이유·같은 모양이다: AI 검색 결과 카드가 실제 파이프라인
// (검색 응답 → wishedListingIdsProvider → ListingCard의 `wished` prop → WishButton 아이콘)으로
// 이어지는지 본다.
//
// AI 검색은 실제 네트워크 호출(searchAi)을 거치는데, `API_BASE_URL`은 컴파일타임 상수라
// 테스트에서 채울 수 없고 flutter_test는 실제 네트워크도 막는다(listing_card_test.dart 헤더
// 주석 참조) — 그래서 `AiChatScreen`의 `searchAiOverride` 시접(ai_chat_screen.dart, 테스트
// 전용)으로 네트워크 없이 고정 응답을 주입한다.
import 'dart:async';

import 'package:app/core/theme/app_theme.dart';
import 'package:app/features/ai_search/ai_chat_screen.dart';
import 'package:app/features/ai_search/ai_search_api.dart';
import 'package:app/features/ai_search/market_diagnosis_chart.dart';
import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_card.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// app_router_test.dart·wish_button_test.dart와 동일한 최소 가짜 로그인 사용자 — 16.6이
/// `_submit()`에 로그인 게이트를 추가하면서(currentUserProvider == null이면 서버 호출 없이
/// /login) 이 파일의 기존 테스트(전부 "로그인 상태에서 AI 검색"을 전제)는 이 오버라이드가
/// 없으면 첫 줄에서 게이트에 막혀버린다. 비로그인 게이트 자체를 검증하는 새 테스트만 별도로
/// `currentUserProvider.overrideWithValue(null)`을 명시한다.
User _fakeUser() => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'test@example.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

void main() {
  // wish_button_test.dart·search_screen_test.dart와 같은 이유 — `Supabase.instance`를
  // `_submit()`이 직접 읽는다(currentSession?.accessToken). 실제 네트워크 호출은
  // searchAiOverride가 대신하므로 없다.
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
      'AI 검색 결과 카드는 wishedListingIdsProvider 값을 실제로 반영한다(찜한 매물만 채워진 하트)',
      (tester) async {
    const wishedListing = ListingCardData(
      id: 'wished-1',
      manufacturer: '현대',
      model: '아반떼',
      year: 2021,
      price: 18000000,
      mileage: 20000,
      region: '서울',
    );
    const otherListing = ListingCardData(
      id: 'other-1',
      manufacturer: '기아',
      model: 'K5',
      year: 2020,
      price: 20000000,
      mileage: 30000,
      region: '부산',
    );

    // search_screen_test.dart와 같은 이유 — 기본 뷰포트로는 카드 두 개가 동시에 안 들어온다.
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          // 실제 카드 진입점(home/search/ai)이 전부 공유하는 단일 provider — 여기만
          // 오버라이드해도 화면이 그 값을 정말로 ListingCard.wished까지 실어 나르는지 본다.
          wishedListingIdsProvider.overrideWith((ref) async => {'wished-1'}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                const SearchResult(
              answer: '조건에 맞는 매물 2건입니다.',
              listings: [wishedListing, otherListing],
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '아반떼 찾아줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(find.text('[현대] 아반떼 · 2021년'), findsOneWidget);
    expect(find.text('[기아] K5 · 2020년'), findsOneWidget);
    expect(
      find.byIcon(Icons.favorite),
      findsOneWidget,
      reason: 'AI 검색 실제 파이프라인을 통해 찜한 매물(wished-1) 카드만 채워진 하트여야 한다',
    );
    expect(
      find.byIcon(Icons.favorite_border),
      findsOneWidget,
      reason: '찜 안 한 매물(other-1) 카드는 빈 하트여야 한다',
    );
  });

  // spec-16-8 AC5 — 히어로 제안 칩·실 입력 제출의 목적지 계약: initialQuery가 있으면 화면이
  // 열리자마자 그 문장으로 이미 조회를 시작한 상태다(입력창에 채우기만 하는 게 아니라, 직접
  // 타이핑 제출과 동일한 _submit(overrideQuery:) 파이프라인을 그대로 탄다).
  testWidgets(
      'initialQuery가 있으면 화면이 열리자마자 그 문장으로 이미 제출된 상태다(직접 타이핑과 동일 파이프라인)',
      (tester) async {
    var callCount = 0;
    final sentQueries = <String>[];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            initialQuery: '4천만원대 전기 SUV',
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              sentQueries.add(query);
              return const SearchResult(answer: '조건에 맞는 매물을 찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(callCount, 1, reason: '화면 진입만으로 자동 제출됐어야 한다');
    expect(sentQueries, ['4천만원대 전기 SUV']);
    // 입력창에 채우기만 한 게 아니라 실제로 제출됐다 — user 버블 + 응답 버블 둘 다 보인다.
    expect(find.text('4천만원대 전기 SUV'), findsOneWidget);
    expect(find.text('조건에 맞는 매물을 찾았어요.'), findsOneWidget);
  });

  // 2026-08-10 Epic 16 묶음 코드리뷰(verification-gap) — **실패 쪽 분기를 아무도 안 봤다.**
  // 위 테스트는 자동 제출 **성공**만 본다. 그런데 이 스토리가 새로 만든 파라미터
  // `restoreInputOnFailure`의 존재 이유는 정확히 **실패**다: 히어로에서 넘어온 경로는
  // `home_screen.dart`가 이미 입력창을 비운 뒤라 이 문장의 사본이 앱 어디에도 없고,
  // 실패했는데 복원까지 안 하면 사용자는 처음부터 다시 타이핑해야 한다.
  // 그 복원 분기(`if (overrideQuery == null || restoreInputOnFailure)`)를 실행하는 테스트가
  // 하나도 없어서, `restoreInputOnFailure` 조건을 지우거나 호출부가 기본값(false)으로
  // 회귀해도 전 스위트가 green이었다.
  //
  // ⚠️ 이 검사가 안 보는 것: 복원된 문장을 사용자가 **다시 눌러 재제출**하는 흐름은 안 본다
  //   (그건 별개 계약이고, §8의 "복원까지만 하고 자동 실행하지 않는다"는 웹 한정이다 —
  //    2026-08-10 결정, docs/conventions.md §8).
  testWidgets('히어로 자동 제출이 실패하면 그 문장을 입력창에 되돌려 놓는다(다시 타이핑하지 않게)',
      (tester) async {
    const q = '4천만원대 전기 SUV';

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            initialQuery: q,
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              throw Exception('network down');
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller?.text, q,
        reason: '히어로에서 넘어온 문장은 실패 시 입력창에 복원돼야 한다 — 비어 있으면 '
            '사용자가 그 문장을 다시 칠 방법이 없다(홈 검색창도 이미 비워졌다)');
  });

  testWidgets('initialQuery가 없으면(null) 자동 제출하지 않는다(기존 동작 무파괴)',
      (tester) async {
    var callCount = 0;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              return const SearchResult(answer: 'x', listings: []);
            },
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(callCount, 0, reason: 'initialQuery가 없으면 자동 제출이 없어야 한다');
  });

  // Story 16.5 — 되묻기 칩 렌더·탭 전송·500자 상한 (I/O 매트릭스).
  //
  // ⚠️ 이 검사들이 **안 보는 것**(추측이 아니라 이번 리뷰에서 실제로 확인한 범위):
  //  - 실제 화면 픽셀. 위젯트리의 사각형·색·콜백만 본다. 폰트·테마 적용 후 사람 눈에
  //    어떻게 보이는지는 실기기에서만 확인된다(대장 등재, 트리거 Epic 16-6).
  //  - HTTP 층. `searchAiOverride` 로 네트워크를 건너뛰므로 jsonDecode·상태코드·헤더는
  //    지나가지 않는다(`searchAi` 는 top-level `http.post` 를 직접 불러 주입 시접이 없다).
  //    wire JSON → 화면 이음매는 아래 마지막 테스트가 `parseSearchResult` 까지만 잇는다.
  //  - 서버가 실제로 무슨 칩을 보내는지. 칩 문자열은 전부 테스트가 지어낸 값이다.
  testWidgets(
      '되묻기 응답은 chips 순서대로 탭 가능한 칩을 렌더하고, 탭하면 그 문자열로 '
      '즉시 다음 질의를 보낸다(같은 _submit 파이프라인)', (tester) async {
    var callCount = 0;
    // 실제로 **무엇이 서버로 나갔는지** 붙잡는다(review: 이전엔 callCount 와 화면의 'SUV'
    // 텍스트만 봤는데, 그 버블은 전송값과 같은 지역변수로 그려지므로 전송값이 엉뚱해도
    // 화면은 멀쩡해 보인다 — 변이 실측으로 확인됨).
    final sentQueries = <String>[];
    final sentContexts = <List<ConversationTurn>?>[];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              sentQueries.add(query);
              sentContexts.add(context);
              if (callCount == 1) {
                // 첫 질의는 되묻기 라우트 — clarify 채워짐, listings 는 비어 있음.
                return const SearchResult(
                  answer: '어떤 용도로 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(
                    question: '어떤 용도로 찾으세요?',
                    chips: ['SUV', '전기차'],
                  ),
                );
              }
              // 칩 탭으로 온 두 번째 질의 — 구조형 응답(칩 없음).
              return const SearchResult(answer: '조건에 맞는 매물을 찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '패밀리카로 무난한 거 추천해줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(find.text('어떤 용도로 찾으세요?'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'SUV'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, '전기차'), findsOneWidget);
    // chips 배열 순서(['SUV', '전기차']) 그대로 좌→우 렌더되는지.
    expect(
      tester.getTopLeft(find.widgetWithText(ChoiceChip, 'SUV')).dx <
          tester.getTopLeft(find.widgetWithText(ChoiceChip, '전기차')).dx,
      isTrue,
    );

    // 탭 전에는 아직 "선택됨" 표시(체크 아이콘)가 없다 — 코드리뷰 지적(선택 피드백 부재).
    expect(
      tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'SUV')).selected,
      isFalse,
    );

    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'));
    await tester.pumpAndSettle();

    expect(callCount, 2, reason: '칩 탭이 기존 _submit 경로로 다음 질의를 보냈어야 한다');
    // 이 스토리의 헤드라인 AC — 탭한 **칩 문자열 그대로** 나가야 한다. 화면 버블이 아니라
    // 서버로 간 인자를 직접 본다.
    expect(sentQueries, ['패밀리카로 무난한 거 추천해줘', 'SUV']);
    // 칩 탭도 직전 대화를 context 로 함께 보낸다 — 서버는 이 배열 길이로 되묻기 3턴 상한을
    // 센다(정정된 I12). 여기가 끊기면 모든 칩 탭이 서버에 "1턴째"로 보여 상한이 영영 안
    // 걸리고, 클라엔 카운터가 없으므로(spec Never) 막을 다른 장치가 없다.
    expect(sentContexts.first, isNull, reason: '첫 질의 앞에는 대화가 없다');
    expect(
      sentContexts[1]?.map((t) => t.content).toList(),
      ['패밀리카로 무난한 거 추천해줘', '어떤 용도로 찾으세요?'],
      reason: '칩 탭은 직전 되묻기 턴까지를 context 로 실어야 한다',
    );
    // "SUV"는 이제 2곳에 있다 — 이전 되묻기 버블의 칩 라벨(대화 기록은 지워지지 않는다)과,
    // 이번 탭으로 새로 추가된 user 메시지 버블.
    expect(find.text('SUV'), findsNWidgets(2), reason: '칩 라벨 + 새 user 메시지 버블');
    expect(find.text('조건에 맞는 매물을 찾았어요.'), findsOneWidget);

    // 탭한 칩은 "선택됨"(petrol 채움 + 체크) 상태로 남는다 — EXPERIENCE.md 비색 신호 중복
    // 규칙(코드리뷰 지적 #4), 대화 기록을 스크롤해도 무엇을 탭했는지 알 수 있어야 한다.
    expect(
      tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'SUV')).selected,
      isTrue,
    );
    // 색 말고 **모양으로도** 신호하는지(EXPERIENCE.md 비색 신호 중복 규칙). `showCheckmark:
    // false` 라 `selected: true` 만으로는 체크 표시가 생기지 않으므로, 아이콘을 따로 본다
    // — review 변이 실측: `avatar: null` 로 지워도 기존 단언들은 전부 green 이었다.
    expect(
      find.descendant(
        of: find.widgetWithText(ChoiceChip, 'SUV'),
        matching: find.byIcon(Icons.check),
      ),
      findsOneWidget,
      reason: '선택 신호가 색 하나로만 남으면 안 된다',
    );

    // 이제 이 칩 행은 더 이상 "마지막 메시지"가 아니므로 비활성(잠김) — 코드리뷰 지적 #2.
    // '전기차' 칩을 다시 눌러도 아무 요청도 나가지 않는다(낡은 되묻기 칩의 조용한 재전송 방지).
    await tester.tap(find.widgetWithText(ChoiceChip, '전기차'));
    await tester.pumpAndSettle();
    expect(callCount, 2, reason: '더 이상 마지막 메시지가 아닌 칩 행은 탭해도 재전송하지 않아야 한다');
  });

  // review 실측 — 칩 문자열이 아니라 **인덱스**로 선택을 기억하는지. 칩 위젯 Key 는 이미
  // 인덱스로 중복을 가르고 있었는데 선택 판정만 문자열 비교로 남아 있어, 서버가 같은 문자열을
  // 둘 보내면 하나를 탭한 것만으로 둘 다 선택·비활성이 됐다(실측: selected 플래그 [true,
  // true, false]). 지금 서버는 서로 다른 고정 3개만 보내지만, Key 를 인덱스로 굳힌 판단이
  // 옳다면 선택 판정도 같은 기준이어야 한다.
  testWidgets('같은 문자열 칩이 둘 있어도 탭한 칩 하나만 선택된다', (tester) async {
    var callCount = 0;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              if (callCount == 1) {
                return const SearchResult(
                  answer: '어떤 걸 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(
                    question: '어떤 걸 찾으세요?',
                    chips: ['SUV', 'SUV', '세단'],
                  ),
                );
              }
              return const SearchResult(answer: '찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '질의');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('clarify_chip_0_SUV')));
    await tester.pumpAndSettle();

    final chips = find.byType(ChoiceChip);
    expect(
      [for (var i = 0; i < 3; i++) tester.widget<ChoiceChip>(chips.at(i)).selected],
      [true, false, false],
      reason: '탭한 칩(인덱스 0)만 선택돼야 한다 — 같은 문자열이라고 함께 선택되면 안 된다',
    );
  });

  // review 실측 — 같은 프레임 연타(리빌드 전이라 콜백이 아직 살아 있다)에서 진행 중인 칩의
  // 선택 표시가 지워졌다: 두 번째 탭이 표시를 찍고, _submit 이 _loading 때문에 곧바로 false 를
  // 돌려주고, 그 롤백이 첫 탭의 표시까지 지웠다(실측: selected=false). 가드를 _onChipTap
  // 맨 앞으로 옮겨 막는다.
  testWidgets('칩을 같은 프레임에 두 번 눌러도 요청은 한 번이고 선택 표시가 유지된다',
      (tester) async {
    final gate = Completer<SearchResult>();
    var callCount = 0;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              if (callCount == 1) {
                return const SearchResult(
                  answer: '어떤 용도로 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(
                    question: '어떤 용도로 찾으세요?',
                    chips: ['SUV', '세단'],
                  ),
                );
              }
              return gate.future; // 두 번째 요청은 열어 둔 채 붙잡는다.
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '질의');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    // pump() 없이 연달아 두 번 — 칩 행이 비활성으로 다시 그려지기 전이다.
    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'), warnIfMissed: false);
    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'), warnIfMissed: false);
    await tester.pump();

    expect(callCount, 2, reason: '연타해도 실제 요청은 한 번만 나가야 한다(첫 질의 + 칩 1회)');
    expect(
      tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'SUV')).selected,
      isTrue,
      reason: '전송이 진행 중인 칩의 "선택됨" 표시가 두 번째 탭 때문에 지워지면 안 된다',
    );

    gate.complete(const SearchResult(answer: '찾았어요.', listings: []));
    await tester.pumpAndSettle();
  });

  // 코드리뷰 지적 #1 — 칩 탭 제출은 입력창에 남아있던 사용자의 독립적인 초안을 건드리면 안
  // 된다(clear도, 실패 롤백의 복원도 모두 해당 없음).
  testWidgets('칩 탭으로 제출해도 입력창에 남아있던 사용자 초안 텍스트는 그대로 유지된다',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              if (query == '패밀리카로 무난한 거 추천해줘') {
                return const SearchResult(
                  answer: '어떤 용도로 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(question: '어떤 용도로 찾으세요?', chips: ['SUV']),
                );
              }
              return const SearchResult(answer: '조건에 맞는 매물을 찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '패밀리카로 무난한 거 추천해줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    // 되묻기 칩이 뜬 뒤, 사용자가 칩과 무관하게 다음 질문을 미리 입력해 둔 상황을 재현.
    await tester.enterText(find.byType(TextField), '내가 따로 적어둔 초안');

    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(
      field.controller!.text,
      '내가 따로 적어둔 초안',
      reason: '칩 탭 제출이 입력창의 독립적인 초안을 지우거나 덮어쓰면 안 된다',
    );
  });

  testWidgets('clarify.chips 가 빈 배열이면 칩 행 자체를 그리지 않는다', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                const SearchResult(
              answer: '질문입니다.',
              listings: [],
              clarify: ClarifyPayload(question: '질문입니다.', chips: []),
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '질의');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(find.text('질문입니다.'), findsOneWidget);
    // 실제로 렌더되는 위젯으로 단언한다 — 이전 판은 `find.byType(ActionChip)`을 봤는데
    // 이 레포에 ActionChip 은 한 곳도 없어(칩은 전부 ChoiceChip) 칩이 그려져도 통과했다
    // (코드리뷰 3개 레이어 독립 지적 + 변이 실측: 렌더 조건에서 `chips.isNotEmpty`를 지워도
    // 317/317 green 이었다).
    expect(find.byKey(const Key('clarify_chips')), findsNothing);
    expect(find.byType(ChoiceChip), findsNothing);
  });

  // 코드리뷰 지적 — 칩 탭 전송이 실패하면 "선택됨" 표시를 되돌려야 한다. 안 그러면 롤백으로
  // 칩 행은 다시 활성화되는데 방금 누른 칩만 isSelected 라 영구 비활성으로 남아, 한 번의
  // 일시적 네트워크 실패가 그 칩을 영영 못 누르게 만든다.
  testWidgets('칩 탭 전송이 실패하면 선택 표시가 풀리고 같은 칩을 다시 누를 수 있다',
      (tester) async {
    var callCount = 0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              if (callCount == 1) {
                return const SearchResult(
                  answer: '어떤 용도로 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(question: '어떤 용도로 찾으세요?', chips: ['SUV']),
                );
              }
              if (callCount == 2) {
                throw const AiSearchException('AI 검색 서버에 연결하지 못했습니다.');
              }
              return const SearchResult(answer: '조건에 맞는 매물을 찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '패밀리카로 무난한 거 추천해줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    // 칩 탭 전에 사용자가 따로 초안을 적어 둔 상황 — 실패 롤백이 이걸 덮어쓰면 안 된다.
    // (review 변이 실측: 롤백의 `overrideQuery == null` 조건을 지워도 전 스위트가 green
    // 이었다 — 초안 보존은 성공 경로만 검사되고 있었다.)
    await tester.enterText(find.byType(TextField), '내가 따로 적어둔 초안');

    // 첫 칩 탭 → 실패.
    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'));
    await tester.pumpAndSettle();
    expect(callCount, 2);
    expect(find.byKey(const Key('ai_error')), findsOneWidget);
    expect(
      tester.widget<TextField>(find.byType(TextField)).controller!.text,
      '내가 따로 적어둔 초안',
      reason: '칩 탭이 실패해도 롤백이 사용자 초안을 칩 문자열로 덮어쓰면 안 된다',
    );
    expect(
      tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, 'SUV')).selected,
      isFalse,
      reason: '실패한 전송은 "선택됨"으로 남으면 안 된다',
    );

    // 같은 칩 재시도 → 이번엔 성공.
    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'));
    await tester.pumpAndSettle();
    expect(callCount, 3, reason: '실패한 칩은 다시 누를 수 있어야 한다');
    expect(find.text('조건에 맞는 매물을 찾았어요.'), findsOneWidget);
  });

  // 코드리뷰 지적 — 못 누르는 칩(지난 턴)이 활성 칩과 똑같이 보이면 사용자는 앱이 고장난 줄
  // 안다. Flutter 기본 disabledColor 는 배경만 흐리게 하고, 여기서 하드코딩한 테두리·글자색은
  // 그대로 남아 있었다.
  testWidgets('지난 턴의 잠긴 칩은 활성 칩과 다른(흐린) 테두리·글자색으로 그려진다',
      (tester) async {
    var callCount = 0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              if (callCount == 1) {
                return const SearchResult(
                  answer: '어떤 용도로 찾으세요?',
                  listings: [],
                  clarify: ClarifyPayload(
                    question: '어떤 용도로 찾으세요?',
                    chips: ['SUV', '전기차'],
                  ),
                );
              }
              return const SearchResult(answer: '찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '질의');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    final activeOutline =
        tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, '전기차')).side!.color;

    // 'SUV' 를 눌러 턴을 넘기면 이 행 전체가 잠긴다.
    await tester.tap(find.widgetWithText(ChoiceChip, 'SUV'));
    await tester.pumpAndSettle();

    final locked = tester.widget<ChoiceChip>(find.widgetWithText(ChoiceChip, '전기차'));
    expect(locked.onSelected, isNull, reason: '지난 턴 칩은 눌리지 않아야 한다');
    expect(
      locked.side!.color,
      isNot(activeOutline),
      reason: '눌리지 않는 칩이 눌리는 칩과 똑같이 보이면 안 된다',
    );
    expect(locked.labelStyle!.color, isNot(AppColors.brandPetrol));
  });

  // D5(project-context.md 규칙 13, "2줄로 밀리는 버튼 = 절대 금기")를 주석이 아니라 검사로
  // 못박는다 — 서버 칩이 길어져도 칩 행은 한 줄이고 넘치는 만큼은 가로 스크롤이 흡수한다.
  testWidgets('좁은 화면에서 긴 칩이 와도 칩 행은 한 줄이다(가로 스크롤로만 흡수)',
      (tester) async {
    tester.view.physicalSize = const Size(360, 780);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        // 실제 앱이 쓰는 테마를 씌운다(main.dart 의 MaterialApp 4곳이 전부 buildAppTheme()).
        // 기하를 재는 검사가 배포되지 않는 표면에서 재고 있으면 테마가 바뀌어도 안 걸린다
        // (review 지적). 지금 값은 테마 유무와 무관하게 같은 것을 실측 확인했고, 이 배선은
        // 앞으로의 테마 변경을 이 검사 안으로 끌어들이기 위한 것이다.
        child: MaterialApp(
          theme: buildAppTheme(),
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                const SearchResult(
              answer: '어떤 용도로 찾으세요?',
              listings: [],
              clarify: ClarifyPayload(
                question: '어떤 용도로 찾으세요?',
                chips: ['3천만원 이하 가성비 세단', '패밀리용 대형 SUV', '전기차 또는 하이브리드'],
              ),
            ),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '질의');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    final chips = find.byType(ChoiceChip);
    expect(chips, findsNWidgets(3));
    final first = tester.getRect(chips.at(0));
    for (var i = 1; i < 3; i++) {
      final r = tester.getRect(chips.at(i));
      expect(r.top, first.top, reason: '칩이 다음 줄로 밀렸다(D5 위반)');
      expect(r.left, greaterThan(tester.getRect(chips.at(i - 1)).right - 1),
          reason: '칩은 좌→우 한 줄로만 놓인다');
    }
    // 넘치는 만큼을 **가로 스크롤이 실제로 흡수**하고 있는지 스크롤 상태로 확인한다.
    // 이전 판은 `chips.at(2).right > 360`(= 셋째 칩이 화면 밖) 이었는데, 그건 테스트가 고른
    // 칩 문자열이 마침 길다는 사실을 재확인할 뿐이라 칩이 짧아지면 D5 위반 없이도 빨간불이
    // 된다(review 지적).
    final row = tester.widget<SingleChildScrollView>(
      find.descendant(
        of: find.byKey(const Key('clarify_chips')),
        matching: find.byType(SingleChildScrollView),
      ),
    );
    expect(row.scrollDirection, Axis.horizontal);
    final position = tester
        .state<ScrollableState>(find.descendant(
          of: find.byKey(const Key('clarify_chips')),
          matching: find.byType(Scrollable),
        ))
        .position;
    expect(position.maxScrollExtent, greaterThan(0),
        reason: '한 줄에 다 안 들어가는 분량은 가로 스크롤이 흡수해야 한다');
  });

  testWidgets('입력 500자를 넘겨 시도해도 TextField가 더 받지 않고 카운터가 500/500을 보인다',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        // 위 D5 검사와 같은 이유로 실제 앱 테마를 씌운다 — 정렬은 입력 데코·버튼 테마가
        // 직접 좌우하는 값이라, 테마 없는 표면에서 재면 배포본을 안 보는 셈이 된다.
        child: MaterialApp(
          theme: buildAppTheme(),
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                const SearchResult(answer: 'x', listings: []),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), 'a' * 501);
    await tester.pump();

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text.length, 500);
    expect(
      tester.widget<Text>(find.byKey(const Key('ai_query_counter'))).data,
      '500/500',
    );
    // 카운터가 입력 박스 높이에 얹혀 전송 버튼을 아래로 밀지 않는지(코드리뷰 실측: 기본
    // Material 카운터를 쓰면 버튼 중심이 입력 텍스트 중심보다 10px 내려갔다).
    // 1px 여유를 둔다 — 막으려는 회귀는 10px 어긋남이라 이 여유로도 충분히 잡히고, 정확한
    // 부동소수 일치로 두면 폰트 메트릭·패딩이 조금만 달라져도 "정렬과 무관한 이유로" 빨간불이
    // 떠 다음 사람이 검사를 지우게 된다(review 지적).
    expect(
      (tester.getRect(find.byKey(const Key('ai_send'))).center.dy -
              tester.getRect(find.byType(EditableText)).center.dy)
          .abs(),
      lessThan(1.0),
      reason: '전송 버튼은 입력 박스와 세로 중심이 맞아야 한다',
    );
  });

  // review(Flutter SDK 실측) — `maxLength` 의 기본 강제 방식은 플랫폼마다 다르다.
  // Android·Windows 는 enforced 지만 web·iOS·macOS·linux 는 truncateAfterCompositionEnds 라,
  // IME 조합 중에는 상한을 넘겨도 통과시켰다가 조합이 끝날 때 자른다 — 한글 입력이 정확히
  // 그 경로다. 조합 중 강제로 바꾸면 CJK 입력이 깨지므로(그래서 Flutter 기본값이 이렇다)
  // 표시값을 clamp 해서 "503/500" 같은 자기모순만 없앤다.
  testWidgets('IME 조합 중 상한을 넘겨도 카운터는 500/500을 넘겨 표시하지 않는다',
      (tester) async {
    debugDefaultTargetPlatformOverride = TargetPlatform.iOS;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                const SearchResult(answer: 'x', listings: []),
          ),
        ),
      ),
    );

    await tester.tap(find.byType(TextField));
    await tester.pump();
    // 조합(composing) 구간을 단 채 상한을 넘겨 입력 — 이 플랫폼에서는 포매터가 통과시킨다.
    tester.testTextInput.updateEditingValue(
      TextEditingValue(
        text: 'a' * 503,
        selection: const TextSelection.collapsed(offset: 503),
        composing: const TextRange(start: 500, end: 503),
      ),
    );
    await tester.pump();
    // 포매터는 이미 돌았다. 단언 전에 되돌려 둔다 — flutter_test 는 테스트 **본문이 끝나는
    // 시점**에 이 전역이 원복됐는지 검사하므로 addTearDown 으로는 늦다.
    debugDefaultTargetPlatformOverride = null;

    final field = tester.widget<TextField>(find.byType(TextField));
    expect(field.controller!.text.length, 503,
        reason: '전제 확인 — 이 플랫폼은 조합 중 상한 초과를 허용한다');
    expect(
      tester.widget<Text>(find.byKey(const Key('ai_query_counter'))).data,
      '500/500',
      reason: '카운터가 상한을 넘겨 표시하면 사용자는 왜 막히는지 알 수 없다',
    );
  });

  // 코드리뷰 지적 — 상한을 세는 단위가 두 개면(TextField.maxLength=그래핌, String.length=
  // UTF-16 코드유닛) 이모지 입력에서 "카운터는 300/500인데 전송은 막히고 500자로 줄이라는
  // 안내가 뜨는" 빠져나갈 수 없는 상태가 된다.
  testWidgets('이모지처럼 2코드유닛인 글자도 그래핌 기준으로 세어 500자 이내면 전송된다',
      (tester) async {
    var sent = 0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              sent++;
              return const SearchResult(answer: '찾았어요.', listings: []);
            },
          ),
        ),
      ),
    );

    // 자동차 이모지 300개 = 그래핌 300개지만 String.length 는 600.
    final emoji = '🚗' * 300;
    expect(emoji.length, 600);

    await tester.enterText(find.byType(TextField), emoji);
    await tester.pump();
    expect(
      tester.widget<Text>(find.byKey(const Key('ai_query_counter'))).data,
      '300/500',
    );

    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(sent, 1, reason: '그래핌 300자는 상한(500) 이내라 전송돼야 한다');
    expect(find.byKey(const Key('ai_error')), findsNothing);
  });

  // 코드리뷰 지적 — 파싱 단위테스트는 JSON→SearchResult 만, 위젯테스트는 이미 만들어진
  // SearchResult→화면 만 봐서 "서버 JSON이 실제로 칩이 된다"를 지나가는 검사가 없었다.
  // 이 테스트가 그 이음매를 잇는다(실제 wire JSON을 parseSearchResult 에 통과시켜 주입).
  testWidgets('서버 wire JSON이 parseSearchResult를 거쳐 실제 칩으로 그려진다', (tester) async {
    // api/app/graph/clarify_node.py 가 내려보내는 형태 그대로(라이브 curl 실측값).
    final wire = <String, Object?>{
      'answer': '조금만 더 알려주세요. 어떤 조건이 중요하세요?',
      'listings': <Object?>[],
      'clarify': {
        'question': '조금만 더 알려주세요. 어떤 조건이 중요하세요?',
        'chips': ['3천만원 이하', 'SUV', '전기차'],
      },
      'narrowed_by': null,
    };

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                parseSearchResult(wire, imageUrlBuilder: (p) => 'https://x/$p'),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '패밀리카로 무난한 거 추천해줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('clarify_chips')), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, '3천만원 이하'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, 'SUV'), findsOneWidget);
    expect(find.widgetWithText(ChoiceChip, '전기차'), findsOneWidget);
  });

  // 4갈래 중 REJECT 만 화면까지 지나가는 검사가 없었다(스펙 AC3 + Never "narrowed_by 미렌더").
  // 앞선 두 패스는 "REJECT 는 clarify==null 이라 빈-chips 테스트와 같은 분기를 탄다"는 **추론**
  // 으로 이 자리를 비워 뒀는데, 변이 실측 결과 버블 본문에 narrowed_by 를 이어 붙여도 전
  // 스위트가 green 이었다 — 즉 그 Never 를 지키는 실행되는 검사가 하나도 없었다
  // (CLAUDE.md B4: 정연한 논증은 검증이 아니다).
  testWidgets('거절 응답(narrowed_by만 채워짐)은 안내 텍스트만 그리고 술어를 노출하지 않는다',
      (tester) async {
    // api/app/graph 의 REJECT 경로가 내려보내는 형태 그대로.
    final wire = <String, Object?>{
      'answer': '요청하신 조건에 맞는 매물을 찾지 못했어요.',
      'listings': <Object?>[],
      'clarify': null,
      'narrowed_by': ['price<=30000000', 'body_type=SUV', 'fuel=전기'],
    };

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(_fakeUser()),
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                parseSearchResult(wire, imageUrlBuilder: (p) => 'https://x/$p'),
          ),
        ),
      ),
    );

    await tester.enterText(find.byType(TextField), '오늘 날씨 어때?');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(find.text('요청하신 조건에 맞는 매물을 찾지 못했어요.'), findsOneWidget);
    // 칩도 카드도 없다.
    expect(find.byKey(const Key('clarify_chips')), findsNothing);
    expect(find.byType(ChoiceChip), findsNothing);
    expect(find.byType(ListingCard), findsNothing);
    // 원시 술어 문자열은 사람이 읽을 텍스트가 아니다 — 어떤 형태로도 화면에 나오면 안 된다.
    expect(find.textContaining('price<='), findsNothing);
    expect(find.textContaining('body_type='), findsNothing);
    expect(find.textContaining('fuel='), findsNothing);
  });

  testWidgets(
      '비로그인 상태에서 전송하면 AI 검색 호출 없이 /login으로 이동한다(FR58 행동 게이트, '
      'DW-738, spec-16-6)', (tester) async {
    var callCount = 0;
    // AiChatScreen은 홈에서 Navigator.push로 도달되므로 context.go가 동작하려면 GoRouter
    // 조상이 필요하다(wish_button_test.dart의 같은 이유 — 이 파일의 다른 테스트는 게이트를
    // 안 타므로 평범한 MaterialApp으로 충분했다).
    final router = GoRouter(
      initialLocation: '/ai',
      routes: [
        GoRoute(
          path: '/ai',
          builder: (context, state) => AiChatScreen(
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              return const SearchResult(answer: '호출되면 안 된다', listings: []);
            },
          ),
        ),
        GoRoute(
          path: '/login',
          builder: (context, state) => const Scaffold(
            body: Text('login-probe', key: Key('login_probe')),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(null), // 비로그인 명시.
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), '아반떼 찾아줘');
    await tester.tap(find.byKey(const Key('ai_send')));
    await tester.pumpAndSettle();

    expect(callCount, 0, reason: 'AI 검색(과금 호출)이 나가면 안 된다');
    expect(find.byKey(const Key('login_probe')), findsOneWidget);
    expect(tester.takeException(), isNull);
    // 낙관적 user 버블도 추가되지 않았어야 한다(서버 호출로 이어지는 어떤 부수효과도
    // 시작하지 않는다) — 화면 자체가 /login으로 바뀌었으니 이 매칭은 그 증거를 겹으로 남긴다.
    expect(find.text('아반떼 찾아줘'), findsNothing);
  });

  testWidgets(
      '비로그인 + initialQuery(히어로 자동 제출)도 호출 없이 /login으로 이동한다', (tester) async {
    var callCount = 0;
    final router = GoRouter(
      initialLocation: '/ai',
      routes: [
        GoRoute(
          path: '/ai',
          builder: (context, state) => AiChatScreen(
            initialQuery: '4천만원대 전기 SUV',
            searchAiOverride: ({required query, context, listingId, required accessToken}) async {
              callCount++;
              return const SearchResult(answer: '호출되면 안 된다', listings: []);
            },
          ),
        ),
        GoRoute(
          path: '/login',
          builder: (context, state) => const Scaffold(
            body: Text('login-probe', key: Key('login_probe')),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
          currentUserProvider.overrideWithValue(null),
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    expect(callCount, 0, reason: '히어로 자동 제출도 같은 _submit 게이트를 타야 한다');
    expect(find.byKey(const Key('login_probe')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  // AI 시세 진단(5단계) 위젯 테스트 — market_diagnosis_card.dart·market_diagnosis_chart.dart가
  // 정상 데이터로 크래시 없이 그려지는지(산점도 CustomPaint 포함), user 턴 위 ListingCard
  // 부착이 실제로 렌더되는지 본다. 서버 wire JSON을 parseSearchResult에 통과시켜 주입한다
  // (searchAiOverride 시접 — 위 되묻기 칩 테스트들과 같은 관례, "wire JSON이 실제로 화면에
  // 닿는지"까지 잇는다).
  group('AI 시세 진단(5단계) — 카드·산점도·요약 카드 렌더', () {
    Map<String, Object?> wireDiagnosis({String id = 'l-1', int step = 0}) => {
          'listing': {
            'id': id,
            'manufacturer': '기아',
            'model': '셀토스',
            'year': 2021,
            'mileage': 33000,
            'price': 22000000,
            'fuel': '가솔린',
            'transmission': '자동',
            'displacement': 1998,
            'accident_free': true,
            'accident_status': '무사고',
            'region': '경기',
          },
          'criteria': {'step': step, 'desc': '연식·주행거리 조건 완화', 'sample_count': 12},
          'stats': {
            'min': 19000000,
            'q1': 21000000,
            'median': 23000000,
            'q3': 25000000,
            'max': 27000000,
          },
          'percentile': 0.4,
          'verdict': '적정',
          'verdict_basis': '적정가',
          'tabpfn': {'price': 22500000, 'note': ''},
          'comps': [
            {'id': 'c1', 'model': '셀토스', 'year': 2020, 'mileage': 40000, 'price': 21000000},
            {'id': 'c2', 'model': '셀토스', 'year': 2022, 'mileage': 20000, 'price': 24000000},
          ],
        };

    testWidgets('단건 시세 진단 카드가 산점도를 포함해 크래시 없이 그려진다', (tester) async {
      final wire = <String, Object?>{
        'answer': '이 매물은 적정 가격대예요.',
        'listings': const <Object?>[],
        'market_diagnosis': wireDiagnosis(),
      };

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
            currentUserProvider.overrideWithValue(_fakeUser()),
          ],
          child: MaterialApp(
            home: AiChatScreen(
              searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                  parseSearchResult(wire, imageUrlBuilder: (p) => 'https://x/$p'),
            ),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '이 매물 시세 알려줘');
      await tester.tap(find.byKey(const Key('ai_send')));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull, reason: '진단 카드·산점도 렌더 중 예외가 없어야 한다');
      expect(find.byKey(const Key('market_diagnosis_card')), findsOneWidget);
      expect(find.byType(MarketDiagnosisChart), findsOneWidget,
          reason: '비교군(comps)이 있으므로 산점도가 실제로 붙어야 한다');
      // 통계 3칸·판정 배지·각주까지 실제 값으로 그려지는지(표시 항목 전부 미러 확인).
      expect(find.text('적정'), findsOneWidget);
      expect(find.textContaining('Built with PriorLabs-TabPFN'), findsOneWidget);
    });

    testWidgets('다건 시세 진단(2건 이상)은 단건 카드 대신 요약표를 그린다', (tester) async {
      final wire = <String, Object?>{
        'answer': '두 매물을 비교했어요.',
        'listings': const <Object?>[],
        'market_diagnoses': [wireDiagnosis(id: 'l-1'), wireDiagnosis(id: 'l-2')],
      };

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
            currentUserProvider.overrideWithValue(_fakeUser()),
          ],
          child: MaterialApp(
            home: AiChatScreen(
              searchAiOverride: ({required query, context, listingId, required accessToken}) async =>
                  parseSearchResult(wire, imageUrlBuilder: (p) => 'https://x/$p'),
            ),
          ),
        ),
      );

      await tester.enterText(find.byType(TextField), '두 매물 다 시세 알려줘');
      await tester.tap(find.byKey(const Key('ai_send')));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byKey(const Key('market_diagnosis_table')), findsOneWidget);
      expect(find.byKey(const Key('market_diagnosis_card')), findsNothing,
          reason: '2건 이상이면 단건 카드 대신 요약표만 그려야 한다(웹과 동일 분기)');
    });

    testWidgets('initialListingSummary가 있으면 user 턴 말풍선 위에 ListingCard가 부착돼 렌더된다',
        (tester) async {
      const summary = ListingCardData(
        id: 'l-1',
        manufacturer: '기아',
        model: '셀토스',
        year: 2021,
        price: 22000000,
        mileage: 33000,
        region: '경기',
      );

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
            currentUserProvider.overrideWithValue(_fakeUser()),
          ],
          child: MaterialApp(
            home: AiChatScreen(
              initialQuery: '이 매물 시세 알려줘 — 기아 셀토스 2021 · 3.3만km · 2,200만원',
              initialListingId: 'l-1',
              initialListingSummary: summary,
              searchAiOverride: ({required query, context, listingId, required accessToken}) async {
                // 프리필 핸드오프가 listingId를 실제로 실어 보내는지도 함께 확인한다.
                expect(listingId, 'l-1');
                return const SearchResult(answer: '이 매물은 적정 가격대예요.', listings: []);
              },
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byType(ListingCard), findsOneWidget,
          reason: '사용자 턴 위에 표준 ListingCard로 매물 요약이 렌더돼야 한다(전용 미니카드 아님)');
      expect(find.text('[기아] 셀토스 · 2021년'), findsOneWidget);

      // ListingCard가 말풍선(user 질의 텍스트)보다 위에 있는지(web items-end 배치 미러).
      final cardY = tester.getTopLeft(find.byType(ListingCard)).dy;
      final bubbleY = tester
          .getTopLeft(find.text('이 매물 시세 알려줘 — 기아 셀토스 2021 · 3.3만km · 2,200만원'))
          .dy;
      expect(cardY, lessThan(bubbleY));
    });
  });
}
