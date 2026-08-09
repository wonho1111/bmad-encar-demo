// syncListingPhotos / listListingPhotoPaths / deletePhotoObjectsByPaths 단위테스트
// (spec-16-7 I/O 매트릭스 + Boundaries) — web `photo-sync.test.ts`와 같은 계약을 Dart로
// 미러링한다.
//
// ⚠️ web은 Supabase를 통째로 목(vi.mock)으로 갈아 끼우지만, Dart supabase 클라이언트는 그런
// 모듈 목킹이 없다 — 대신 `chat_repository_test.dart`가 이미 쓰는 패턴대로 실제 `SupabaseClient`에
// 가짜 `http.BaseClient`를 주입해(`httpClient:`) 나간 요청(메서드·경로·쿼리·본문)을 그대로
// 캡처하고 응답을 우리가 정한다. resize/upload/deleteObject는 `photo_sync.dart`가 노출하는
// 주입 지점(ResizeFn/UploadFn/DeleteObjectFn)을 그대로 쓴다 — 새 mock 패키지 불필요(A2).
// 두 경계(HTTP·스토리지 함수)가 **같은 `log` 리스트**에 호출 순서대로 쌓인다 — 순서가 계약인
// 항목(삭제·업로드)은 이 한 리스트로만 판정할 수 있기 때문이다(web `h.log`와 동일 전략).
//
// ⚠️ 이 검사가 **안 보는 것**(추측이 아니라 구조상 명백한 것):
//   - 실제 Supabase의 RLS·트리거 동작(sold 차단 3정책, 10장 상한 트리거 등). 여기서는 그
//     경계를 가짜로 바꾸고 **우리 코드가 무엇을 어떤 순서로 어떤 요청을 보내는지**만 본다.
//     "정책이 실제로 거르는가"는 로컬 Supabase(도커) 실측의 몫이다(스토리 Verification 참조).
//   - 실제 이미지 리사이즈·압축(`flutter_image_compress` 플랫폼 채널) — `resizeFn`을 가짜로
//     두므로 저장본 규격은 `photo_resize_test.dart`(순수 함수 `computeTargetSize`)가 담당한다.
import 'dart:convert';
import 'dart:typed_data';

import 'package:app/core/supabase/storage_helper.dart' show UploadResult;
import 'package:app/features/listings/photo_item.dart';
import 'package:app/features/listings/photo_resize.dart';
import 'package:app/features/listings/photo_sync.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:image_picker/image_picker.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

const _userId = 'u1';
const _listingId = 'l1';

/// 캡처된 요청 — 메서드·쿼리·(디코딩된) 본문.
class _CapturedRequest {
  _CapturedRequest({
    required this.method,
    required this.query,
    required this.body,
    required this.wantsSingle,
  });

  final String method;
  final Map<String, String> query;
  final Map<String, dynamic> body;
  final bool wantsSingle;

  /// 사람이 읽는 한 줄 라벨(공유 log에 순서대로 쌓인다) — web `h.log` 라벨 전략과 동일 목적.
  String get label {
    final where = query.entries
        .where((e) => e.key != 'select')
        .map((e) => '${e.key}=${e.value}')
        .join('&');
    if (method == 'PATCH' && body.containsKey('is_cover')) {
      return 'cover:${body['is_cover']}|$where';
    }
    if (method == 'PATCH' && body.containsKey('sort_order')) {
      return 'sort:${body['sort_order']}|$where';
    }
    if (method == 'POST') return 'row:insert:sort=${body['sort_order']}';
    if (method == 'DELETE') return 'row:delete:$where';
    if (method == 'GET') return 'select:$where';
    return '$method:$where';
  }
}

/// 특정 요청에 대해 (상태코드, 응답바디)를 결정한다. null이면 기본 성공 처리.
typedef _Responder = ({int status, Object? body})? Function(_CapturedRequest req);

class _FakeHttpClient extends http.BaseClient {
  _FakeHttpClient(this.log);

  /// 스토리지 함수 가짜(resize/upload/deleteObject)와 **공유하는** 순서 로그.
  final List<String> log;

  final List<_CapturedRequest> requests = [];
  _Responder? responder;
  int _insertSeq = 0;

  /// select('storage_path')로 돌려줄 행들(listListingPhotoPaths 테스트용).
  List<Map<String, dynamic>> existingRows = const [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    var bodyStr = '';
    if (request is http.Request) bodyStr = request.body;
    Map<String, dynamic> bodyJson = const {};
    if (bodyStr.isNotEmpty) {
      final decoded = jsonDecode(bodyStr);
      if (decoded is Map<String, dynamic>) bodyJson = decoded;
    }
    final wantsSingle = request.headers['Accept']?.contains('vnd.pgrst.object') ?? false;
    final captured = _CapturedRequest(
      method: request.method,
      query: request.url.queryParameters,
      body: bodyJson,
      wantsSingle: wantsSingle,
    );
    requests.add(captured);
    log.add(captured.label);

    final custom = responder?.call(captured);
    int status;
    Object? respBody;
    if (custom != null) {
      status = custom.status;
      respBody = custom.body;
    } else if (request.method == 'GET') {
      status = 200;
      respBody = existingRows;
    } else if (request.method == 'POST') {
      _insertSeq += 1;
      final row = {...bodyJson, 'id': 'row-$_insertSeq'};
      status = 201;
      respBody = wantsSingle ? row : [row];
    } else {
      // PATCH/DELETE 기본 성공 — 1행 영향.
      status = 200;
      respBody = wantsSingle ? {'id': 'row-x'} : [
        {'id': 'row-x'},
      ];
    }

    final bytes = utf8.encode(jsonEncode(respBody));
    return http.StreamedResponse(
      Stream.value(bytes),
      status,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

/// 새로 고른 사진(아직 저장 전). `XFile.fromData`라 실제 파일시스템을 건드리지 않는다.
PhotoItem _newPhoto(String name) => PhotoItem(
      key: 'k-$name',
      previewUrl: '/tmp/$name.jpg',
      file: XFile.fromData(Uint8List(0), name: name, mimeType: 'image/jpeg'),
    );

/// 이미 저장된 사진(기존 행).
PhotoItem _savedPhoto(String name, {String? storagePath, String? rowId}) => PhotoItem(
      key: 'k-$name',
      previewUrl: 'https://cdn.test/$name',
      status: PhotoStatus.uploaded,
      storagePath: storagePath ?? '$_userId/$_listingId/$name.webp',
      rowId: rowId ?? 'row-$name',
    );

void main() {
  late List<String> log;
  late _FakeHttpClient fakeHttp;
  late SupabaseClient client;
  final deleteObjectFailFor = <String>{};
  final uploadFailFor = <String>{};

  Future<EncodedPhoto> fakeResize(XFile file) async {
    log.add('resize:${file.name}');
    // 원본 파일명을 바이트에 실어 보낸다 — uuid 파일명으로 업로드가 일어나도(_newFilename)
    // 어느 사진이었는지 업로드 단계에서 식별할 수 있게(테스트 전용 배선).
    return EncodedPhoto(
      bytes: Uint8List.fromList(utf8.encode(file.name)),
      extension: 'webp',
      mimeType: 'image/webp',
    );
  }

  Future<UploadResult> fakeUpload(
    String userId,
    String listingId,
    String filename,
    Uint8List bytes,
    String contentType,
  ) async {
    log.add('upload:start');
    // 실제 업로드는 비동기다 — 한 틱 쉬어 "순차인지 병렬인지"가 로그에 드러나게 한다.
    await Future<void>.delayed(Duration.zero);
    log.add('upload:end');
    final originalName = utf8.decode(bytes);
    if (uploadFailFor.contains(originalName)) {
      return const UploadResult.error('사진을 올리지 못했어요. 다시 시도해주세요.');
    }
    return UploadResult.ok('$userId/$listingId/$filename');
  }

  Future<bool> fakeDeleteObject(String storagePath) async {
    final ok = !deleteObjectFailFor.contains(storagePath);
    log.add('object:delete:$storagePath:${ok ? 'ok' : 'fail'}');
    return ok;
  }

  setUp(() {
    log = [];
    fakeHttp = _FakeHttpClient(log);
    client = SupabaseClient(
      'https://example.supabase.co',
      'test-anon-key-not-real',
      httpClient: fakeHttp,
    );
    deleteObjectFailFor.clear();
    uploadFailFor.clear();
  });

  tearDown(() => client.dispose());

  Future<PhotoSyncResult> sync(List<PhotoItem> photos, List<PhotoItem> initial) {
    return syncListingPhotos(
      _userId,
      _listingId,
      photos,
      initial,
      client: client,
      resizeFn: fakeResize,
      uploadFn: fakeUpload,
      deleteObjectFn: fakeDeleteObject,
    );
  }

  group('빈 입력은 아무 요청도 보내지 않는다(할 일이 없으면 DB를 건드리지 않는다)', () {
    test('photos·initialPhotos 둘 다 비어 있으면 요청 0건', () async {
      final r = await sync(const [], const []);
      expect(fakeHttp.requests, isEmpty);
      expect(r.savedCount, 0);
      expect(r.failedCount, 0);
      expect(r.warnings, isEmpty);
    });
  });

  group('계약① 삭제 순서 (§10.1 — 오브젝트 먼저 → listing_images 행 나중)', () {
    test('오브젝트를 먼저 지우고 그 다음 행을 지운다', () async {
      final gone = _savedPhoto('a');
      await sync(const [], [gone]);

      final objIdx = log.indexOf('object:delete:${gone.storagePath}:ok');
      final rowIdx = log.indexWhere((l) => l.startsWith('row:delete:'));
      expect(objIdx, greaterThanOrEqualTo(0));
      expect(rowIdx, greaterThanOrEqualTo(0));
      // 이 부등호가 계약 전부다 — 뒤집히면 소유자도 못 지우는 고아가 된다(#46).
      expect(objIdx, lessThan(rowIdx));
    });

    test('오브젝트 삭제가 실패하면 행을 지우지 않는다(영구 고아 방지)', () async {
      final gone = _savedPhoto('a');
      deleteObjectFailFor.add(gone.storagePath!);

      final r = await sync(const [], [gone]);

      expect(log, contains('object:delete:${gone.storagePath}:fail'));
      expect(
        fakeHttp.requests.any((req) => req.method == 'DELETE'),
        isFalse,
        reason: '행 삭제 HTTP 요청이 아예 나가면 안 된다',
      );
      expect(r.failedCount, 1);
      expect(r.warnings, contains('사진을 삭제하지 못했어요. 삭제 버튼을 다시 눌러주세요.'));
    });

    test('행 삭제가 실패(에러 응답)하면 조용히 넘기지 않고 warning으로 알린다', () async {
      final gone = _savedPhoto('a');
      fakeHttp.responder = (req) =>
          req.method == 'DELETE' ? (status: 400, body: {'message': 'boom'}) : null;

      final r = await sync(const [], [gone]);
      expect(r.warnings, contains('사진 삭제 정보를 정리하지 못했어요.'));
    });

    test('행 삭제가 0행(에러 아님)이면 성공으로 치지 않는다', () async {
      final gone = _savedPhoto('a');
      fakeHttp.responder = (req) => req.method == 'DELETE' ? (status: 200, body: <dynamic>[]) : null;

      final r = await sync(const [], [gone]);
      expect(r.warnings, contains('사진 삭제 정보를 정리하지 못했어요.'));
    });

    test('오브젝트 삭제 실패 항목은 다른 유지 사진 뒤로 밀려난다(I/O 매트릭스 "목록 맨 뒤로 이동")', () async {
      final kept = _savedPhoto('kept');
      final gone = _savedPhoto('gone');
      deleteObjectFailFor.add(gone.storagePath!);

      final r = await sync([kept], [kept, gone]);

      expect(r.photos.map((p) => p.key), ['k-kept', 'k-gone'], reason: '못 지운 사진이 맨 앞이 아니라 맨 뒤에 와야 한다');
      expect(r.photos.last.status, PhotoStatus.error, reason: '오류 상태로 표시돼야 한다');
      expect(r.photos.last.rowId, gone.rowId, reason: '행은 지워지지 않았으므로 rowId가 살아 있어야 한다');
    });
  });

  group('계약② 대표 기록 2문장 (#47-1 — 단일 UPDATE 금지)', () {
    test('전체 false로 내린 뒤 1장만 true로 올린다', () async {
      await sync([_newPhoto('a'), _newPhoto('b')], const []);

      final coverReqs = fakeHttp.requests
          .where((r) => r.method == 'PATCH' && r.body.containsKey('is_cover'))
          .toList();
      expect(coverReqs, hasLength(2));
      expect(coverReqs[0].body['is_cover'], false);
      expect(coverReqs[1].body['is_cover'], true);
    });

    test('두 문장 모두 이 매물로 범위를 좁힌다(listing_id 필터)', () async {
      final a = _savedPhoto('a');
      await sync([a], [a]);

      final coverReqs = fakeHttp.requests
          .where((r) => r.method == 'PATCH' && r.body.containsKey('is_cover'))
          .toList();
      for (final r in coverReqs) {
        expect(r.query['listing_id'], 'eq.$_listingId');
      }
    });

    test('대표 지정은 정확히 1장을 지목한다(storage_path 필터)', () async {
      final a = _savedPhoto('a');
      final b = _savedPhoto('b');
      await sync([a, b], [a, b]);

      final setCover = fakeHttp.requests.firstWhere(
        (r) => r.method == 'PATCH' && r.body['is_cover'] == true,
      );
      expect(setCover.query['storage_path'], 'eq.${a.storagePath}');
    });

    test('리셋(false) 문장이 실패하면 두 번째 문장을 아예 쏘지 않는다', () async {
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['is_cover'] == false)
              ? (status: 400, body: {'message': 'boom'})
              : null;

      final r = await sync([_newPhoto('a')], const []);

      expect(
        fakeHttp.requests.any((req) => req.method == 'PATCH' && req.body['is_cover'] == true),
        isFalse,
        reason: '어차피 부분 유니크 인덱스에 걸린다',
      );
      expect(r.warnings, contains('대표 사진 정보를 정리하지 못했어요.'));
    });

    test('대표 지정(true)이 실패하면 "성공"이라 말하지 않는다', () async {
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['is_cover'] == true)
              ? (status: 400, body: {'message': 'boom'})
              : null;

      final r = await sync([_newPhoto('a')], const []);
      expect(r.warnings, contains('대표 사진을 지정하지 못했어요.'));
    });

    test('저장된 사진이 0장이면(전부 지워짐) 대표 지정 문장을 쏘지 않는다', () async {
      final gone = _savedPhoto('a');
      await sync(const [], [gone]);

      expect(
        fakeHttp.requests.any((r) => r.method == 'PATCH' && r.body['is_cover'] == true),
        isFalse,
      );
      expect(
        fakeHttp.requests.any((r) => r.method == 'PATCH' && r.body['is_cover'] == false),
        isTrue,
      );
    });
  });

  group('계약③ 업로드·행 INSERT는 순차 (#49 — 10장 상한 경합 방지)', () {
    test('업로드가 겹치지 않는다(start,end,start,end — 병렬이면 start,start가 붙는다)', () async {
      await sync([_newPhoto('a'), _newPhoto('b'), _newPhoto('c')], const []);

      final uploads = log.where((l) => l.startsWith('upload:')).toList();
      expect(uploads, [
        'upload:start', 'upload:end',
        'upload:start', 'upload:end',
        'upload:start', 'upload:end',
      ]);
    });

    test('행 INSERT도 화면 순서대로 하나씩(sort_order 오름차순) 나간다', () async {
      await sync([_newPhoto('a'), _newPhoto('b')], const []);
      final inserts = fakeHttp.requests.where((r) => r.method == 'POST').toList();
      expect(inserts.map((r) => r.body['sort_order']), [0, 1]);
    });
  });

  group('불변식 "대표 = sort_order 0번"이 실패 경로에서도 유지된다', () {
    test('중간 INSERT가 실패해도 sort_order에 구멍이 남지 않는다', () async {
      var n = 0;
      fakeHttp.responder = (req) {
        if (req.method != 'POST') return null;
        n += 1;
        return n == 2 ? (status: 400, body: {'message': 'boom'}) : null;
      };

      final r = await sync([_newPhoto('a'), _newPhoto('b'), _newPhoto('c')], const []);

      final inserts = fakeHttp.requests.where((r) => r.method == 'POST').toList();
      expect(inserts.map((r) => r.body['sort_order']), [0, 1, 1]);
      expect(r.savedCount, 2);
      expect(r.failedCount, 1);
    });

    test('첫 INSERT가 실패하면 대표는 실제로 sort_order=0을 받은 사진에 붙는다', () async {
      var n = 0;
      fakeHttp.responder = (req) {
        if (req.method != 'POST') return null;
        n += 1;
        return n == 1 ? (status: 400, body: {'message': 'boom'}) : null;
      };

      await sync([_newPhoto('a'), _newPhoto('b')], const []);

      final setCover = fakeHttp.requests.firstWhere(
        (r) => r.method == 'PATCH' && r.body['is_cover'] == true,
      );
      // b의 storagePath는 uuid라 예측 불가하므로, insert 성공 요청의 storage_path와 대조한다.
      // a(실패)도 sort_order=0으로 시도했으므로(카운터 미증가) **마지막** sort_order=0 요청이
      // 실제 성공(b)이다 — 로그 순서가 [a:0:fail, b:0:성공]이기 때문.
      final successfulInsert = fakeHttp.requests.lastWhere(
        (r) => r.method == 'POST' && r.body['sort_order'] == 0,
      );
      expect(setCover.query['storage_path'], 'eq.${successfulInsert.body['storage_path']}');
    });
  });

  group('재제출 안전성 (역고아 방지)', () {
    test('INSERT 성공 시 rowId를 화면 상태에 되돌려준다', () async {
      final r = await sync([_newPhoto('a')], const []);
      expect(r.photos.single.rowId, 'row-1');
      expect(r.photos.single.storagePath, isNotNull);
    });

    test('돌려받은 결과를 그대로 재제출하면 INSERT가 아니라 순서 UPDATE만 나간다', () async {
      final first = await sync([_newPhoto('a')], const []);
      fakeHttp.requests.clear();
      log.clear();

      await sync(first.photos, first.photos);

      expect(fakeHttp.requests.where((r) => r.method == 'POST'), isEmpty);
      expect(
        fakeHttp.requests.any((r) => r.method == 'PATCH' && r.body.containsKey('sort_order')),
        isTrue,
      );
      expect(log.any((l) => l.startsWith('object:delete')), isFalse, reason: '저장된 파일을 지우지 않는다');
    });
  });

  group('검증 실패(용량초과·포맷거부) 항목 취급', () {
    PhotoItem rejected() => const PhotoItem(
          key: 'k-big',
          status: PhotoStatus.error,
          error: '5MB를 넘는 사진이에요.',
          retryable: false,
        );

    test('failedCount에 세지 않는다(세면 재제출 때마다 이동이 영구히 막힌다)', () async {
      final r = await sync([rejected(), _newPhoto('a')], const []);
      expect(r.failedCount, 0);
      expect(r.savedCount, 1);
    });

    test('업로드를 시도하지 않고 목록에는 남긴다(어느 파일이 왜 안 됐는지 보여준다)', () async {
      final r = await sync([rejected()], const []);
      expect(log.where((l) => l.startsWith('upload:')), isEmpty);
      expect(r.photos, hasLength(1));
      expect(r.photos.single.status, PhotoStatus.error);
    });
  });

  group('listListingPhotoPaths — 매물 삭제 전 사진 경로 미리 조회(§10.1)', () {
    test('행에 담긴 경로를 그대로 돌려준다', () async {
      fakeHttp.existingRows = [
        {'storage_path': 'p/1.webp'},
        {'storage_path': 'p/2.webp'},
      ];
      final r = await listListingPhotoPaths(_listingId, client: client);
      expect(r.ok, isTrue);
      expect(r.paths, ['p/1.webp', 'p/2.webp']);
    });

    test('조회 자체가 실패하면 "사진 없음"으로 갈음하지 않는다', () async {
      fakeHttp.responder = (req) => req.method == 'GET' ? (status: 400, body: {'message': 'boom'}) : null;
      final r = await listListingPhotoPaths(_listingId, client: client);
      expect(r.ok, isFalse);
    });
  });

  group('deletePhotoObjectsByPaths — 매물 삭제 흐름의 오브젝트 정리', () {
    test('하나가 실패해도 나머지는 계속 시도한다', () async {
      final r = await deletePhotoObjectsByPaths(
        ['p/1.webp', 'p/2.webp', 'p/3.webp'],
        deleteObjectFn: (path) async {
          final ok = path != 'p/1.webp';
          log.add('object:delete:$path:${ok ? 'ok' : 'fail'}');
          return ok;
        },
      );
      expect(r.ok, isFalse);
      expect(r.deleted, 2);
      expect(log, [
        'object:delete:p/1.webp:fail',
        'object:delete:p/2.webp:ok',
        'object:delete:p/3.webp:ok',
      ]);
    });

    test('경로가 비어 있으면 그대로 성공(삭제 0건)', () async {
      final r = await deletePhotoObjectsByPaths(const [], deleteObjectFn: (_) async => true);
      expect(r, (ok: true, deleted: 0));
    });
  });
}
