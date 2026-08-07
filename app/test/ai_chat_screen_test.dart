// AiChatScreen 배선 테스트(Story 16.3 코드리뷰 지적) — search_screen_test.dart·
// home_screen_wishlist_test.dart와 같은 이유·같은 모양이다: AI 검색 결과 카드가 실제 파이프라인
// (검색 응답 → wishedListingIdsProvider → ListingCard의 `wished` prop → WishButton 아이콘)으로
// 이어지는지 본다.
//
// AI 검색은 실제 네트워크 호출(searchAi)을 거치는데, `API_BASE_URL`은 컴파일타임 상수라
// 테스트에서 채울 수 없고 flutter_test는 실제 네트워크도 막는다(listing_card_test.dart 헤더
// 주석 참조) — 그래서 `AiChatScreen`의 `searchAiOverride` 시접(ai_chat_screen.dart, 테스트
// 전용)으로 네트워크 없이 고정 응답을 주입한다.
import 'package:app/features/ai_search/ai_chat_screen.dart';
import 'package:app/features/ai_search/ai_search_api.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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
        ],
        child: MaterialApp(
          home: AiChatScreen(
            searchAiOverride: ({required query, context, required accessToken}) async =>
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
}
