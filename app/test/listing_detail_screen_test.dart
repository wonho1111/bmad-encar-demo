// review P7 — 상세 화면이 ListingGallery를 실제로 장착해 쓰는지 확인(new test).
// 리뷰가 listing_detail_screen.dart의 `ListingGallery(imageUrls: listing.imageUrls)` 줄을
// 주석 처리했는데도 전체 스위트가 green이었다 — listing_gallery_test.dart는 ListingGallery를
// 직접 pump하고(화면 배선은 안 본다), app_router_test.dart는 listingDetailProvider를
// null(못 찾음 분기)로 오버라이드해 AppBar 개수만 본다(그 분기는 ListingGallery까지 안 간다).
// 어느 쪽도 "상세 화면이 실제로 그 자리에 ListingGallery를 꽂아 쓰는지"를 안 본다.
// app_router_test.dart의 provider-override + pump 관례를 그대로 재사용해, 사진이 있는
// ListingDetail로 실제 화면을 pump하고 갤러리 카운터로 확인한다.
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_detail_screen.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 화면이 요구하는 필수 15필드만 채운 최소 상세 데이터. 사진은 `withImages`로 붙인다
/// (listing.dart 주석: `listings` 단일 row엔 없는 데이터라 fromMap이 안 채우고 이 메서드로
/// 별도 부착한다 — 실제 조회 경로와 같은 조립 방식).
ListingDetail _fakeDetail({required List<String> imageUrls}) {
  const base = ListingDetail(
    id: 'listing-1',
    sellerId: 'seller-1',
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
    status: 'on_sale',
  );
  return base.withImages(imageUrls);
}

void main() {
  // app_router_test.dart와 같은 이유로 딱 한 번 초기화한다 — _DetailContent가 전역
  // `supabase.auth.currentUser`를 직접 읽는다(문의하기 버튼 노출 여부 판단).
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  testWidgets('상세 화면이 실제로 ListingGallery를 장착해 "1/3" 카운터를 그린다', (tester) async {
    // listing_gallery_test.dart와 동일하게 loopback(아무도 안 듣는 포트) URL을 쓴다 — 이
    // 테스트의 관심사는 화면이 갤러리를 장착했는지이지, 실제 이미지 로드 성공 여부가 아니다.
    const urls = [
      'http://127.0.0.1:1/a.jpg',
      'http://127.0.0.1:1/b.jpg',
      'http://127.0.0.1:1/c.jpg',
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: urls)),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('1/3'),
      findsOneWidget,
      reason:
          '상세 화면이 ListingGallery를 실제로 장착해야만 이 카운터가 뜬다 — 그 배선 줄이 '
          '통째로 빠져도(주석 처리) 이전엔 어떤 테스트도 안 잡았다(review P7 실측: 172건 '
          '전부 green).',
    );
  });
}
