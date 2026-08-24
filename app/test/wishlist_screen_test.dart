// WishlistScreen 위젯테스트(Story 16.3) — 목록/빈 상태/판매완료 타일을 단언한다.
// wishlistProvider를 직접 오버라이드해 실제 Supabase 조회(fetchWishlist·fetchCovers) 없이
// 화면의 렌더 분기만 본다(그 조회 로직 자체는 wishlist_repository_test.dart가 다룬다).
import 'package:app/features/listings/listing.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:app/features/wishlist/wishlist_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

ListingCardData _card() => const ListingCardData(
      id: 'listing-1',
      manufacturer: '현대',
      model: '아반떼',
      year: 2021,
      price: 18000000,
      mileage: 20000,
      region: '서울',
    );

Future<void> _pump(WidgetTester tester, List<WishlistTile> tiles) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [wishlistProvider.overrideWith((ref) async => tiles)],
      child: const MaterialApp(home: WishlistScreen()),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('0건 → 빈 상태 안내 문구', (tester) async {
    await _pump(tester, const []);

    expect(find.byKey(const Key('wishlist_empty')), findsOneWidget);
    expect(find.text('아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요.'), findsOneWidget);
  });

  testWidgets('정상 카드 타일 — 매물 카드가 렌더된다', (tester) async {
    await _pump(tester, [WishlistTile.card(_card())]);

    expect(find.text('[현대] 아반떼 · 2021년'), findsOneWidget);
    expect(find.byKey(const Key('wishlist_empty')), findsNothing);
    // 코드리뷰 지적(P7) — 이 화면의 카드는 정의상 항상 찜된 상태다(wishlist_screen.dart의
    // `wished: true` 리터럴, "이 화면에 있다는 것 자체가 찜된 상태"). 그 리터럴을 false로
    // 바꿔도 위 두 단언만으로는 안 잡혔다 — 다른 형제 배선 테스트들처럼 채워진 하트를
    // 직접 본다.
    expect(find.byIcon(Icons.favorite), findsOneWidget);
    expect(find.byIcon(Icons.favorite_border), findsNothing);
  });

  testWidgets('차단 타일(본인 소유 sold, 제목 있음) — 회색 타일 + "판매완료" 배지, 차량명 표시', (tester) async {
    await _pump(
      tester,
      [WishlistTile.blocked(listingId: 'listing-2', title: '[기아] K5 · 2020년')],
    );

    expect(find.text('판매완료'), findsOneWidget);
    expect(find.text('[기아] K5 · 2020년'), findsOneWidget);
  });

  testWidgets('차단 타일(타인 소유 sold, RLS로 embed 없음) — 제목 대신 일반 문구', (tester) async {
    await _pump(tester, [WishlistTile.blocked(listingId: 'listing-3')]);

    expect(find.text('판매완료'), findsOneWidget);
    expect(find.text('판매완료된 매물'), findsOneWidget);
  });

  testWidgets('차단 타일은 탭해도 상세로 이동하지 않는다(상세 진입 차단, FR11)', (tester) async {
    await _pump(
      tester,
      [WishlistTile.blocked(listingId: 'listing-2', title: '[기아] K5 · 2020년')],
    );

    await tester.tap(find.text('[기아] K5 · 2020년'));
    await tester.pumpAndSettle();

    // 차단 타일엔 onTap 자체가 없다 — 여전히 같은 화면(목록)에 머문다.
    expect(find.byType(WishlistScreen), findsOneWidget);
    expect(find.text('판매완료'), findsOneWidget);
  });

  testWidgets('조회 실패 → 한국어 에러 안내', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishlistProvider.overrideWith((ref) async => throw Exception('boom')),
        ],
        child: const MaterialApp(home: WishlistScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('wishlist_error')), findsOneWidget);
  });
}
