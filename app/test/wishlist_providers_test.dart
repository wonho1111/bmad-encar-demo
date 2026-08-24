// wishlistProvider 본문 테스트(Story 16.3 코드리뷰 지적) — `wishlist_screen_test.dart`·
// `app_router_test.dart`는 이 provider 자체를 오버라이드해 완성된 타일을 주입하므로,
// FR11(판매완료 비노출, docs/conventions.md §6) id-narrowing(on_sale만 fetchCovers로) ·
// `_blockedTitle` · cover→image_url 조립은 그동안 어떤 테스트로도 실행되지 않았다
// (docs/conventions.md §6이 이 경로를 이미지 축 신규 소비처로 등록한 자리이기도 하다).
// 이 파일은 `wishlistRepositoryProvider`만 가짜로 갈아 끼워 provider 본문을 직접 돌린다.
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:app/features/wishlist/wishlist_repository.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 고정 entries를 돌려주고, fetchCovers에 실제로 넘어온 id 목록을 캡처하는 가짜 레포.
class _FakeWishlistRepository extends WishlistRepository {
  _FakeWishlistRepository(this.entries);

  final List<WishlistEntry> entries;
  List<String>? capturedCoverIds;

  @override
  Future<List<WishlistEntry>> fetchWishlist() async => entries;

  @override
  Future<Map<String, ({String path, int count})>> fetchCovers(
    List<String> listingIds,
  ) async {
    capturedCoverIds = listingIds;
    return {for (final id in listingIds) id: (path: '$id/cover.jpg', count: 1)};
  }
}

void main() {
  // getPublicUrl(storage_helper.dart)이 전역 `supabase` 게터를 읽는다(cover→image_url 조립).
  // 실제 네트워크 호출은 없다(getPublicUrl은 로컬 문자열 조립만 한다).
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  test(
      'wishlistProvider — on_sale만 fetchCovers로 넘어가고(sold/embed-null 제외), '
      'sold·embed-null은 각각 제목 있는/없는 blocked 타일, cover는 image_url로 조립된다',
      () async {
    final repo = _FakeWishlistRepository([
      WishlistEntry(
        listingId: 'on-sale-1',
        createdAt: DateTime(2026, 8, 7),
        embed: const {
          'id': 'on-sale-1',
          'manufacturer': '현대',
          'model': '아반떼',
          'year': 2021,
          'price': 18000000,
          'mileage': 20000,
          'region': '서울',
          'status': 'on_sale',
        },
      ),
      WishlistEntry(
        listingId: 'sold-1', // 본인 소유 sold — embed는 있지만 status가 on_sale이 아니다.
        createdAt: DateTime(2026, 8, 6),
        embed: const {
          'id': 'sold-1',
          'manufacturer': '기아',
          'model': 'K5',
          'year': 2020,
          'price': 20000000,
          'mileage': 30000,
          'region': '부산',
          'status': 'sold',
        },
      ),
      WishlistEntry(
        listingId: 'blocked-1', // 타인 소유 sold — RLS가 embed 자체를 null로 막는다.
        createdAt: DateTime(2026, 8, 5),
        // embed 생략 → null(기본값).
      ),
    ]);

    final container = ProviderContainer(
      overrides: [wishlistRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);

    final tiles = await container.read(wishlistProvider.future);

    // FR11 id-narrowing — sold·embed-null id는 fetchCovers에 절대 넘어가면 안 된다.
    expect(repo.capturedCoverIds, ['on-sale-1']);

    expect(tiles, hasLength(3));

    expect(tiles[0].isBlocked, isFalse);
    expect(tiles[0].listing!.id, 'on-sale-1');
    expect(tiles[0].listing!.imageUrl, contains('on-sale-1/cover.jpg'),
        reason: 'fetchCovers가 돌려준 path가 카드의 image_url로 조립돼야 한다');

    expect(tiles[1].isBlocked, isTrue);
    expect(tiles[1].blockedTitle, '[기아] K5 · 2020년',
        reason: '본인 소유 sold는 embed가 있으니 제목을 지어낼 수 있다');

    expect(tiles[2].isBlocked, isTrue);
    expect(tiles[2].blockedTitle, isNull,
        reason: 'embed가 RLS로 없으면 없는 정보를 지어내지 않고 null(화면이 일반 문구로 대신)');
  });

  test(
      '_entryStatus — status가 String이 아니면(계약-외 값) 예외 대신 차단 타일로 처리한다'
      '(코드리뷰 지적 P9 — 예전엔 하드 캐스트라 이 값 하나가 찜 탭 전체를 에러 화면으로 죽였다)',
      () async {
    final repo = _FakeWishlistRepository([
      WishlistEntry(
        listingId: 'weird-status-1',
        createdAt: DateTime(2026, 8, 7),
        embed: const {
          'id': 'weird-status-1',
          'manufacturer': '현대',
          'model': '아반떼',
          'year': 2021,
          'price': 18000000,
          'mileage': 20000,
          'region': '서울',
          'status': 123, // wire 계약 위반 — String이어야 하는데 숫자가 왔다.
        },
      ),
    ]);

    final container = ProviderContainer(
      overrides: [wishlistRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);

    // 예외 없이 정상 resolve돼야 한다 — 하드 캐스트였다면 여기서 던진다.
    final tiles = await container.read(wishlistProvider.future);

    expect(tiles, hasLength(1));
    expect(tiles.single.isBlocked, isTrue,
        reason: 'status가 on_sale임을 String으로 확인 못 하면 allowlist 판정상 차단이 맞다(FR11)');
  });
}
