// deleteListing() 오케스트레이션 테스트(Story 16.7 리뷰 발견 — listListingPhotoPaths →
// listings DELETE → deletePhotoObjectsByPaths를 잇는 조합 로직 자체가 통째로 미검증이었다).
// 개별 부품(경로 조회 실패 처리·오브젝트 정리 부분 실패 처리)의 세부 분기는
// photo_sync_test.dart의 listListingPhotoPaths/deletePhotoObjectsByPaths 단위테스트가 이미
// 담당한다 — 이 파일은 deleteListing이 그 부품들을 **올바른 순서·조건으로** 부르는지만 본다.
//
// ⚠️ 이 검사가 안 보는 것: 실제 Storage 오브젝트 정리 성공/실패의 세부 값(그건 위 단위테스트
// 몫). 여기서는 정리 시도 자체가 나갔는지(로그에 /storage/ 경로가 찍혔는지)만 본다.
import 'dart:convert';

import 'package:app/features/listings/listings_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

typedef _Responder = ({int status, Object? body})? Function(http.BaseRequest req);

class _FakeHttpClient extends http.BaseClient {
  final List<String> log = [];
  _Responder? responder;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    log.add('${request.method} $path');

    final custom = responder?.call(request);
    final status = custom?.status ?? 200;
    var body = custom?.body;
    if (body == null) {
      if (path.contains('/rest/v1/listing_images')) {
        body = [
          {'storage_path': 'u1/l1/a.webp', 'id': 'row-1'},
        ];
      } else if (path.contains('/rest/v1/listings')) {
        body = [
          {'id': 'l1'},
        ];
      } else {
        body = <dynamic>[]; // storage 정리 등 기타 호출 — 기본 성공으로 흘려보낸다.
      }
    }

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

  test('사진 경로 조회(listing_images GET)가 매물 삭제(listings DELETE)보다 먼저 나간다(§10.1)', () async {
    final repo = ListingsRepository(client: client);
    await repo.deleteListing('l1');

    final restCalls = fakeHttp.log.where((l) => l.contains('/rest/v1/')).toList();
    final getIdx = restCalls.indexWhere(
      (l) => l.startsWith('GET') && l.contains('listing_images'),
    );
    final deleteIdx = restCalls.indexWhere(
      (l) => l.startsWith('DELETE') && l.contains('/listings'),
    );
    expect(getIdx, greaterThanOrEqualTo(0));
    expect(deleteIdx, greaterThanOrEqualTo(0));
    expect(
      getIdx,
      lessThan(deleteIdx),
      reason: 'cascade가 행을 먼저 지우면 어떤 파일을 지울지 알 방법이 없어진다',
    );
  });

  test('listings DELETE가 0행(RLS 차단·이미 없음)이면 사진 정리를 시도하지 않는다', () async {
    fakeHttp.responder = (req) {
      if (req.method == 'DELETE' && req.url.path.contains('/rest/v1/listings')) {
        return (status: 200, body: <dynamic>[]); // 0행
      }
      return null;
    };

    final repo = ListingsRepository(client: client);
    final result = await repo.deleteListing('l1');

    expect(result, 0);
    expect(
      fakeHttp.log.any((l) => l.contains('/storage/')),
      isFalse,
      reason: '삭제 자체가 안 됐으면 사진도 건드리지 않는다',
    );
  });

  test('경로 조회 자체가 실패해도(paths.ok==false) 매물 삭제는 계속 진행되고 정리만 건너뛴다', () async {
    fakeHttp.responder = (req) {
      if (req.method == 'GET' && req.url.path.contains('/rest/v1/listing_images')) {
        return (status: 400, body: {'message': 'boom'});
      }
      return null;
    };

    final repo = ListingsRepository(client: client);
    final result = await repo.deleteListing('l1');

    expect(result, 1, reason: '경로 조회 실패가 매물 삭제 자체를 막으면 안 된다(베스트에포트)');
    expect(
      fakeHttp.log.any((l) => l.contains('/storage/')),
      isFalse,
      reason: '지울 경로를 모르므로 정리를 시도하지 않는다(파일을 잘못 건드리는 것보다 안전)',
    );
  });
}
