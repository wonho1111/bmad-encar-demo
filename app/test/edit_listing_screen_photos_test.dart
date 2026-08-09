// EditListingScreen의 기존 사진 로딩 경로(Story 16.7) — editListingPhotosProvider →
// fetchOwnListingPhotos → toPhotoItems 상당 → SellScreen.initialPhotos 배선을 다룬다
// (review 발견, verification-gap — 이 경로 전체가 어디에도 테스트되지 않았다).
//
// ⚠️ editListingProvider(listings_providers.dart)는 `currentUserProvider`가 아니라 전역
// `supabase.auth.currentUser`를 직접 읽는다(require_user.dart의 로그인 게이트와 다른 값
// 소스) — 그래서 이 화면의 "정상 로드" 분기를 보려면 게이트(currentUserProvider)뿐 아니라
// 전역 Supabase 클라이언트에도 실제로 로그인 세션을 넣어야 한다. `chat_repository_test.dart`가
// 이미 쓰는 `recoverSession(...)` 패턴(네트워크 없이 세션만 로컬 저장)을 그대로 가져온다.
//
// ⚠️ 이 검사가 안 보는 것: 실제 Supabase 쿼리 자체(그건 listings_repository의 다른 테스트·
// 로컬 Supabase 실측 몫). 여기서는 오직 "화면이 provider 데이터/에러를 올바른 분기로 그리는가"
// 만 본다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/edit_listing_screen.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/photo_item.dart';

const _listingId = 'listing-1';
const _sellerId = '00000000-0000-0000-0000-000000000001';

ListingDetail _detail() => const ListingDetail(
  id: _listingId,
  sellerId: _sellerId,
  manufacturer: '현대',
  model: '아반떼',
  bodyType: '준중형차',
  year: 2021,
  price: 20000000,
  mileage: 10000,
  color: '흰색',
  fuel: '가솔린',
  transmission: '자동',
  displacement: 1600,
  seats: 5,
  region: '서울',
  accidentFree: true,
  status: statusOnSale,
);

/// fetchOwnListing/fetchOwnListingPhotos만 가짜로 갈아 끼운다 — 나머지 메서드는 이 테스트가
/// 안 부르므로 건드릴 필요 없다.
class _FakeRepo extends ListingsRepository {
  _FakeRepo({this.photos, this.photosError});

  final List<PhotoItem>? photos;
  final Object? photosError;

  @override
  Future<ListingDetail?> fetchOwnListing(String id, {required String sellerId}) async =>
      _detail();

  @override
  Future<List<PhotoItem>> fetchOwnListingPhotos(String listingId) async {
    if (photosError != null) throw photosError!;
    return photos ?? const [];
  }
}

Future<void> _signIn(SupabaseClient client, String userId) => client.auth.recoverSession(
  '{"access_token":"not-a-real-jwt","token_type":"bearer","refresh_token":"refresh-token",'
  '"expires_in":3600,"user":{"id":"$userId","aud":"authenticated","app_metadata":{},'
  '"created_at":"2026-01-01T00:00:00Z"}}',
);

User _fakeUser() => User(
  id: _sellerId,
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'seller@test.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
    // editListingProvider가 supabase.auth.currentUser를 직접 읽으므로(currentUserProvider와
    // 별개 값 소스), 전역 클라이언트에도 실제로 로그인 세션을 넣어야 그 provider가 null을
    // 돌려주지 않는다.
    await _signIn(Supabase.instance.client, _sellerId);
  });

  Future<void> pump(WidgetTester tester, ListingsRepository repo) async {
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(repo),
        currentUserProvider.overrideWithValue(_fakeUser()),
      ],
    );
    addTearDown(container.dispose);
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: EditListingScreen(listingId: _listingId)),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets(
    '기존 사진이 있는 매물을 수정 진입하면 업로더 초기 상태에 그 장수가 반영된다(review 발견)',
    (tester) async {
      final saved = PhotoItem(
        key: 'row-1',
        previewUrl: 'https://cdn.test/1.webp',
        status: PhotoStatus.uploaded,
        storagePath: '$_sellerId/$_listingId/1.webp',
        rowId: 'row-1',
      );
      await pump(tester, _FakeRepo(photos: [saved]));

      expect(find.byKey(const Key('edit_load_error')), findsNothing);
      expect(find.byKey(const Key('edit_photos_load_error')), findsNothing);
      await tester.ensureVisible(find.byKey(const Key('photo_count')));
      expect(
        find.text('1/10'),
        findsOneWidget,
        reason: 'editListingPhotosProvider가 돌려준 사진이 SellScreen.initialPhotos로 실제로 넘어가야 한다',
      );
    },
  );

  testWidgets(
    '사진 조회(listing_images)가 실패하면 매물 정보와 별도로 사진 전용 오류 화면을 보여준다(review 발견)',
    (tester) async {
      await pump(tester, _FakeRepo(photosError: Exception('boom')));

      expect(
        find.byKey(const Key('edit_photos_load_error')),
        findsOneWidget,
        reason: 'editListingProvider(매물 자체)는 성공했는데 사진 조회만 실패한 경우를 구분해 보여줘야 한다',
      );
    },
  );
}
