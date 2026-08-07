// SearchScreen 배선 테스트(Story 16.3 코드리뷰 지적 #8) — `listing_trust_widgets_test.dart`·
// `wish_button_test.dart`는 단독 위젯만 pump해서 본다. 이 파일은 실제 화면 파이프라인
// (검색 결과 목록 → wishedListingIdsProvider → ListingCard의 `wished` prop → WishButton
// 아이콘)이 실제로 이어지는지, 세 진입점(홈·검색·AI) 중 검색 화면을 대표로 확인한다.
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_filters.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/search_screen.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 네트워크 없이 고정된 검색 결과를 돌려주는 가짜 레포 — SearchController가 진입 시 자동으로
/// 부르는 초기 조회(빈 필터)에 응답한다.
class _FakeListingsRepository extends ListingsRepository {
  _FakeListingsRepository(this.listings);
  final List<ListingCardData> listings;

  @override
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async => listings;
}

void main() {
  // app_router_test.dart·wish_button_test.dart와 같은 이유 — ListingsRepository()의 기본
  // 생성자(client 미지정 시)가 전역 `supabase` 게터를 읽는다. 실제 네트워크 호출은 위 가짜
  // 레포가 오버라이드하므로 없다.
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
      '검색 결과 카드는 wishedListingIdsProvider 값을 실제로 반영한다(찜한 매물만 채워진 하트)',
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

    // 카드 하나(사진 5:3 + 정보)가 기본 테스트 뷰포트(800×600)보다 크므로, 기본 크기로는
    // 두 번째 카드가 SliverList 캐시 범위 밖이라 안 만들어진다(listing_detail_screen_test.dart의
    // 스크롤 이슈와 동일 원인). 스크롤 대신 뷰포트를 넉넉히 키워 두 카드가 동시에 빌드되게
    // 한다 — 찜 안 한 카드(빈 하트)와 찜한 카드(채운 하트)를 한 화면에서 같이 비교해야 하므로
    // (스크롤하면 둘 중 하나가 화면 밖으로 밀려 같은 문제가 재현된다).
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(
            _FakeListingsRepository([wishedListing, otherListing]),
          ),
          // 실제 카드 진입점(home/search/ai)이 전부 공유하는 단일 provider — 여기만
          // 오버라이드해도 화면이 그 값을 정말로 ListingCard.wished까지 실어 나르는지 본다.
          wishedListingIdsProvider.overrideWith((ref) async => {'wished-1'}),
        ],
        child: const MaterialApp(home: SearchScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('[현대] 아반떼 · 2021년'), findsOneWidget);
    expect(find.text('[기아] K5 · 2020년'), findsOneWidget);
    expect(
      find.byIcon(Icons.favorite),
      findsOneWidget,
      reason: '검색 화면 실제 파이프라인을 통해 찜한 매물(wished-1) 카드만 채워진 하트여야 한다',
    );
    expect(
      find.byIcon(Icons.favorite_border),
      findsOneWidget,
      reason: '찜 안 한 매물(other-1) 카드는 빈 하트여야 한다',
    );
  });
}
