// spec-16-11(DW-751) — 수정 화면의 기존 사진 조회 경로(`fetchOwnListingPhotos` → `toPhotoItems`)가
// 전 테스트 스위트에서 한 번도 실행되지 않던 문제를 닫는다.
//
// ## 왜 이 파일이 따로 필요한가
//
// 유일한 기존 테스트(`edit_listing_screen_photos_test.dart`)는 `ListingsRepository`를 통째로
// 가짜로 갈아 끼워 `fetchOwnListingPhotos`가 반환할 `List<PhotoItem>`을 리터럴로 직접 준다 —
// 그래서 `.order('sort_order')`나 `id` 타이브레이크가 빠져도, `toPhotoItems`의 필드 매핑이
// 깨져도 그 화면 테스트는 계속 초록이었다(DW-751). 이 파일은 대신:
//   - `toPhotoItems`는 원행(raw row map)으로 **직접** 호출해 단언한다(같은 리포의
//     `listings_repository_image_order_test.dart`가 `pickCoverImages`/`sortGalleryPaths`에
//     쓰는 관행 그대로 — 리포지토리를 가짜로 갈아 끼우지 않는다).
//   - `fetchOwnListingPhotos`는 `listings_repository_fr11_wire_test.dart`가 어제 만든
//     **URL 캡처 fake**를 그대로 써서, 가짜 http로 나간 실제 쿼리스트링에
//     `order=sort_order.asc,id.asc`가 실렸는지 본다.
//
// ## 이 검사가 보지 못하는 것 (추측 아니라 명시)
//   - 실제 Supabase의 정렬 실행 자체(그건 DB 몫 — 여기선 클라가 그 요청을 **보냈는지**만 본다).
//   - `getPublicUrl`이 만드는 URL의 정확한 형태(호스트·경로 조립 규칙 자체) — 여기서는 결과
//     문자열에 버킷명이 실렸는지(즉 `getPublicUrl`을 **거쳤는지**)만 본다. 그 조립 규칙 자체의
//     실측은 `listing_images_bucket_test.dart` 몫이다.
//
// ✎ P5(spec-16-11 후속 코드리뷰 2회차, 2026-08-10) — 이 절은 원래 "`fetchOwnListingPhotos`
// 테스트는 응답을 빈 배열로 고정해 URL 조립 자체가 실행되지 않는다"고 적혀 있었다. 그 상태에서는
// `toPhotoItems` 호출을 통째로 지우고 `return const <PhotoItem>[];`로 바꿔도 이 파일이 계속
// green이었다 — DW-751이 닫으려던 갭이 이 파일 자체에 다시 열려 있었다(측정). `_UrlCapturingHttpClient`에
// `rows` 필드를 추가해 응답을 실제로 채우는 테스트를 더해 닫았다.
import 'dart:convert';

import 'package:app/features/listings/listing_images_bucket.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/photo_item.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

void main() {
  // getPublicUrl(storage_helper.dart)이 전역 `supabase` 게터를 읽는다(P5의 previewUrl 조립
  // 검사가 실제로 그 경로를 태운다) — wishlist_providers_test.dart와 동일 패턴. 실제 네트워크
  // 호출은 없다(getPublicUrl은 로컬 문자열 조립만 한다).
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  group('toPhotoItems — 원행 map을 직접 넘겨 단언(리포지토리를 가짜로 갈아 끼우지 않는다, DW-751)',
      () {
    test('원행 순서를 그대로 보존한다(정렬은 이 함수의 책임이 아니다 — 호출부가 이미 정렬해 넘긴다)',
        () {
      final rows = [
        {'id': 'r-2', 'storage_path': 'u/l/2.webp', 'sort_order': 1},
        {'id': 'r-1', 'storage_path': 'u/l/1.webp', 'sort_order': 0},
      ];
      final items = toPhotoItems(rows, (p) => 'https://cdn.test/$p');
      expect(items.map((i) => i.rowId), ['r-2', 'r-1'],
          reason: '입력이 이미 sort_order 역순이면 그대로 역순 출력이어야 한다 — 재정렬하면 이 '
              '함수가 "정렬도 책임진다"는 잘못된 가정을 다음 사람이 갖게 된다');
    });

    test('필드가 정확히 매핑된다 — rowId·storagePath·previewUrl·status·key', () {
      final rows = [
        {'id': 'row-abc', 'storage_path': 'u1/l1/x.webp', 'sort_order': 0},
      ];
      final items = toPhotoItems(rows, (p) => 'https://cdn.test/$p');
      final item = items.single;
      expect(item.rowId, 'row-abc');
      expect(item.storagePath, 'u1/l1/x.webp');
      expect(item.previewUrl, 'https://cdn.test/u1/l1/x.webp');
      expect(item.status, PhotoStatus.uploaded);
      expect(item.key, 'photo-row-row-abc');
    });

    test('buildUrl 콜백이 storage_path로 정확히 호출된다(버킷명이 이 함수에 스며들지 않는다)',
        () {
      final calls = <String>[];
      toPhotoItems(
        [
          {'id': 'r1', 'storage_path': 'a/b/c.webp', 'sort_order': 0},
        ],
        (p) {
          calls.add(p);
          return 'x';
        },
      );
      expect(calls, ['a/b/c.webp']);
    });

    test('계약을 어긴 행(id 누락·경로 빈 문자열·타입 불일치)은 건너뛴다(§10.2와 동일 방어 원칙)',
        () {
      final rows = <Map<String, dynamic>>[
        {'id': 'ok', 'storage_path': 'u/l/ok.webp', 'sort_order': 0},
        {'storage_path': 'u/l/no-id.webp', 'sort_order': 1}, // id 없음
        {'id': 'no-path', 'storage_path': '', 'sort_order': 2}, // 빈 경로
        {'id': 'blank-path', 'storage_path': '   ', 'sort_order': 3}, // 공백뿐
        {'id': 123, 'storage_path': 'u/l/bad-id.webp', 'sort_order': 4}, // id 타입 불일치
      ];
      final items = toPhotoItems(rows, (p) => p);
      expect(items.map((i) => i.rowId), ['ok']);
    });

    test('빈 입력 → 빈 리스트', () {
      expect(toPhotoItems(const [], (p) => p), isEmpty);
    });
  });

  group('fetchOwnListingPhotos — 나가는 쿼리에 order=sort_order.asc,id.asc가 실린다(DW-751)', () {
    late _UrlCapturingHttpClient fakeHttp;
    late SupabaseClient client;

    setUp(() {
      fakeHttp = _UrlCapturingHttpClient();
      client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
    });

    tearDown(() => client.dispose());

    test('listing_images 요청 URL에 정렬 규칙(sort_order 오름차순 → id 오름차순)이 실제로 실린다',
        () async {
      final repo = ListingsRepository(client: client);
      await repo.fetchOwnListingPhotos('listing-1');

      final reqs = fakeHttp.urls.where((u) => u.contains('/rest/v1/listing_images')).toList();
      expect(reqs, isNotEmpty, reason: 'listing_images 조회 요청 자체가 안 나갔다');
      for (final u in reqs) {
        final order = Uri.parse(u.substring(u.indexOf(' ') + 1)).queryParameters['order'];
        // postgrest-dart의 실제 직렬화 형태(실측) — `.order()` 두 번 체이닝이 `nullslast`
        // 접미사까지 붙여 하나의 order 파라미터로 합쳐진다. 문자열을 통째로 대조해 "sort_order가
        // 먼저, id가 나중, 둘 다 오름차순"이라는 계약을 정확히 잡는다.
        expect(order, 'sort_order.asc.nullslast,id.asc.nullslast',
            reason: 'DW-751: 이 정렬이 빠지면 수정 화면이 기존 사진을 임의 순서로 실어, '
                '판매자가 사진을 건드리지 않고 저장만 해도 대표가 조용히 바뀔 수 있다: $u');
      }
    });

    test('listing_id 필터도 함께 실린다(남의 매물 사진이 섞이지 않는다)', () async {
      final repo = ListingsRepository(client: client);
      await repo.fetchOwnListingPhotos('listing-42');

      final reqs = fakeHttp.urls.where((u) => u.contains('/rest/v1/listing_images')).toList();
      expect(reqs, isNotEmpty);
      for (final u in reqs) {
        expect(u, contains('listing_id=eq.listing-42'));
      }
    });

    test(
        'P5(2회차 후속 코드리뷰) — 응답 행 2개를 실제로 매핑한다: rowId는 응답 순서대로, '
        'storagePath는 그대로, previewUrl은 getPublicUrl을 거쳐 조립된다', () async {
      fakeHttp.rows = [
        {'id': 'row-1', 'storage_path': 'u1/l1/1.webp', 'sort_order': 0},
        {'id': 'row-2', 'storage_path': 'u1/l1/2.webp', 'sort_order': 1},
      ];
      final repo = ListingsRepository(client: client);

      final items = await repo.fetchOwnListingPhotos('listing-1');

      // DW-751이 닫으려던 갭 그대로: `return const <PhotoItem>[];`로 본문을 통째로 바꿔도
      // 이 단언이 없으면 위 두 테스트(요청만 보는 테스트)는 계속 green이었다.
      expect(items.map((i) => i.rowId), ['row-1', 'row-2'],
          reason: '응답 순서를 그대로 보존해야 한다(정렬은 쿼리의 order=가 이미 했다)');
      expect(items[0].storagePath, 'u1/l1/1.webp');
      expect(items[1].storagePath, 'u1/l1/2.webp');
      for (final item in items) {
        expect(item.previewUrl, contains(listingImagesBucket),
            reason: 'getPublicUrl(버킷, storage_path)을 실제로 거쳐야 URL에 버킷명이 실린다 — '
                '매핑 자체를 건너뛰면 이 URL이 아예 만들어지지 않는다');
      }
    });
  });
}

/// 나간 전체 URL(쿼리스트링 포함)을 남기는 fake — `listings_repository_fr11_wire_test.dart`의
/// `_UrlCapturingHttpClient`와 동일 기법(이 파일이 증명하려는 것도 쿼리스트링이라서다).
class _UrlCapturingHttpClient extends http.BaseClient {
  /// 응답으로 돌려줄 행 — 기본은 빈 목록이라 기존 테스트(요청만 보는 테스트)는 그대로다.
  /// P5(2회차 후속 코드리뷰) — 이 필드가 없으면 `fetchOwnListingPhotos`가 실제로 무엇을
  /// **돌려주는지**는 어느 테스트도 보지 않는다: `toPhotoItems` 호출을 통째로 지우고
  /// `return const <PhotoItem>[];`로 바꿔도 전 스위트가 green이었다(DW-751이 닫으려던 갭 그대로).
  List<Map<String, dynamic>> rows = [];

  final List<String> urls = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    urls.add('${request.method} ${request.url}');
    final bytes = utf8.encode(jsonEncode(rows));
    return http.StreamedResponse(
      Stream.value(bytes),
      200,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}
