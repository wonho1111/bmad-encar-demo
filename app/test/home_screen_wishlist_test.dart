// HomeScreen 배선 테스트(Story 16.3 코드리뷰 지적) — search_screen_test.dart와 같은 이유·같은
// 모양이다: 홈의 최근 매물 미리보기가 실제 파이프라인(recentListingsProvider → ListingCard의
// `wished` prop → WishButton 아이콘)으로 wishedListingIdsProvider 값을 실어 나르는지 본다.
// home_ai_entry_test.dart는 상단 AI 진입 구성만 보고 목록 본문은 빈 목록으로 대체한다 — 이
// 파일이 그 빈틈(목록 카드의 `wished` 배선)을 메운다.
import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 최소한의 가짜 사용자 — home_ai_entry_test.dart와 동일(홈은 null 여부만 본다).
User _fakeUser() => User(
      id: '00000000-0000-0000-0000-000000000001',
      appMetadata: const {},
      userMetadata: const {},
      aud: 'authenticated',
      email: 'seller@test.com',
      createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
    );

void main() {
  testWidgets(
      '홈 최근 매물 카드는 wishedListingIdsProvider 값을 실제로 반영한다(찜한 매물만 채워진 하트)',
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

    // search_screen_test.dart와 같은 이유 — 기본 뷰포트(800×600)로는 카드 두 개가 화면 안에
    // 동시에 들어오지 않는다. 홈은 Column(비-lazy)이라 스크롤 밖이어도 위젯 자체는 트리에
    // 만들어지지만, 뷰포트를 넉넉히 키워 두 하트를 한 화면에서 같이 비교한다.
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider
              .overrideWith((ref) async => const [wishedListing, otherListing]),
          // 실제 카드 진입점(home/search/ai)이 전부 공유하는 단일 provider — 여기만
          // 오버라이드해도 화면이 그 값을 정말로 ListingCard.wished까지 실어 나르는지 본다.
          wishedListingIdsProvider.overrideWith((ref) async => {'wished-1'}),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('[현대] 아반떼 · 2021년'), findsOneWidget);
    expect(find.text('[기아] K5 · 2020년'), findsOneWidget);
    expect(
      find.byIcon(Icons.favorite),
      findsOneWidget,
      reason: '홈 화면 실제 파이프라인을 통해 찜한 매물(wished-1) 카드만 채워진 하트여야 한다',
    );
    expect(
      find.byIcon(Icons.favorite_border),
      findsOneWidget,
      reason: '찜 안 한 매물(other-1) 카드는 빈 하트여야 한다',
    );
  });
}
