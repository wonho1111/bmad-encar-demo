// storage_helper.dart의 쓰기측 헬퍼(Story 16.7 신규: buildStoragePath·uploadListingImage·
// deleteListingImageObject) 단위테스트.
//
// grep으로 확인: 이 세 함수는 이번 스토리에서 추가됐지만 어떤 테스트에서도 실행된 적이 없다.
// "덮는다"던 photo_sync 테스트들은 uploadFn/deleteObjectFn을 가짜로 주입해 경로 조립 자체를
// 테스트 안에서 다시 구현하므로, 실제 헬퍼가 무엇을 만드는지와 무관하게 통과한다. 이 파일은
// listings_repository_delete_test.dart·sell_controller_test.dart와 같은 가짜 http 클라이언트
// 패턴으로 실제 SupabaseClient를 통해 헬퍼를 직접 호출한다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/supabase/storage_helper.dart';
import 'package:app/features/listings/listing_images_bucket.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

typedef _Responder = ({int status, Object? body})? Function(http.BaseRequest req);

class _FakeHttpClient extends http.BaseClient {
  final List<http.BaseRequest> requests = [];
  _Responder? responder;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requests.add(request);
    final custom = responder?.call(request);
    final status = custom?.status ?? 200;
    // uploadBinary는 성공 응답에서 {'Key': ...}를 기대하고(storage_client 내부), remove는
    // 리스트를 기대한다 — 두 그룹 모두 이 기본값으로 충분하다(값 자체는 안 쓰인다).
    final body = custom?.body ?? {'Key': 'ignored'};
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      status,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

void main() {
  group('buildStoragePath', () {
    test(
      '{user_id}/{listing_id}/{filename} 순서로 조립한다 — 세그먼트 순서가 뒤바뀌면 '
      'Storage RLS와 listing_images 0013 트리거가 모든 업로드를 거부한다(계약)',
      () {
        expect(
          buildStoragePath('user-1', 'listing-1', 'photo.webp'),
          'user-1/listing-1/photo.webp',
        );
      },
    );
  });

  group('uploadListingImage', () {
    late _FakeHttpClient fakeHttp;
    late SupabaseClient client;

    setUp(() {
      fakeHttp = _FakeHttpClient();
      client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
    });

    tearDown(() => client.dispose());

    test(
      '요청 URL 경로가 /storage/v1/object/<bucket>/<user>/<listing>/<filename>이고 '
      'x-upsert 헤더가 true가 아니다(켜지면 존재확인 SELECT가 listing_images 읽기 정책에 '
      '걸려 원격에서 403이 재발한다)',
      () async {
        final result = await uploadListingImage(
          listingImagesBucket,
          'user-1',
          'listing-1',
          'photo.webp',
          Uint8List.fromList([1, 2, 3]),
          contentType: 'image/webp',
          client: client,
        );

        expect(result.ok, isTrue);
        expect(fakeHttp.requests, hasLength(1));
        final req = fakeHttp.requests.single;
        expect(
          req.url.path,
          '/storage/v1/object/$listingImagesBucket/user-1/listing-1/photo.webp',
        );
        expect(req.headers['x-upsert'], isNot('true'));
      },
    );

    test(
      '실패 응답(400)이면 예외를 던지지 않고 UploadResult.error(한국어 사유)를 돌려준다 '
      '— 사진 1장의 실패가 폼 제출 전체를 막으면 안 된다(AC3)',
      () async {
        fakeHttp.responder = (req) => (status: 400, body: {'message': 'boom'});

        final result = await uploadListingImage(
          listingImagesBucket,
          'user-1',
          'listing-1',
          'photo.webp',
          Uint8List.fromList([1, 2, 3]),
          contentType: 'image/webp',
          client: client,
        );

        expect(result.ok, isFalse);
        expect(result.storagePath, isNull);
        expect(result.reason, isNotNull);
        expect(
          RegExp(r'[가-힣]').hasMatch(result.reason!),
          isTrue,
          reason: '사용자에게 그대로 보일 사유이므로 한국어여야 한다',
        );
      },
    );
  });

  group('deleteListingImageObject', () {
    late _FakeHttpClient fakeHttp;
    late SupabaseClient client;

    setUp(() {
      fakeHttp = _FakeHttpClient();
      client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
    });

    tearDown(() => client.dispose());

    test('성공 응답이면 true를 돌려준다', () async {
      fakeHttp.responder = (req) => (status: 200, body: <dynamic>[]);

      final result = await deleteListingImageObject(
        listingImagesBucket,
        'user-1/listing-1/photo.webp',
        client: client,
      );

      expect(result, isTrue);
    });

    test('실패 응답(400)이면 예외를 던지지 않고 false를 돌려준다', () async {
      fakeHttp.responder = (req) => (status: 400, body: {'message': 'boom'});

      final result = await deleteListingImageObject(
        listingImagesBucket,
        'user-1/listing-1/photo.webp',
        client: client,
      );

      expect(result, isFalse);
    });
  });
}
