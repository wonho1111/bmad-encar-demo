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

  /// select('storage_path')로 돌려줄 행들(listListingPhotoPaths 테스트용) — 그리고
  /// **T6**: 이제 이 필드는 손으로 유지하는 게 아니라 성공한 쓰기를 실제로 반영해 갱신되는
  /// "가짜 DB 현재 상태"다. 아래 send()가 성공한 PATCH(sort_order)/POST/DELETE만 반영한다
  /// (실패·0행 응답은 절대 반영하지 않는다 — 그래야 "0행도 실패"라는 계약을 이 가짜도 지킨다).
  List<Map<String, dynamic>> existingRows = [];

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
    // 기본 처리(custom==null)로 실제 POST가 성공할 때만 합성한 신규 행 — T6가 existingRows에
    // 반영할 유일한 "실제로 만들어진 행"이다(테스트가 status만 바꿔 POST 성공을 가짜로
    // 흉내내는 경우는 이 스위트에 없다 — custom 응답은 전부 실패 주입용이다).
    Map<String, dynamic>? insertedRow;
    if (custom != null) {
      status = custom.status;
      respBody = custom.body;
    } else if (request.method == 'GET') {
      status = 200;
      respBody = existingRows;
    } else if (request.method == 'POST') {
      _insertSeq += 1;
      insertedRow = {...bodyJson, 'id': 'row-$_insertSeq'};
      status = 201;
      respBody = wantsSingle ? insertedRow : [insertedRow];
    } else {
      // PATCH/DELETE 기본 성공 — 1행 영향.
      status = 200;
      respBody = wantsSingle ? {'id': 'row-x'} : [
        {'id': 'row-x'},
      ];
    }

    // T6 — 성공한 쓰기만 existingRows(가짜 DB)에 반영한다. "성공"은 2xx이면서 응답이 실제로
    // 행을 가리킨 경우(List면 비어 있지 않음)다 — 0행 응답(예: T5의 실패 흉내)은 여기서
    // 걸러져 반영되지 않는다. 이러면 이 파일의 불변식 검사가 하드코딩한 옛 값이 아니라
    // 이 가짜가 실제로 들고 있는 최종 상태를 읽을 수 있다(파일 헤더 T6 지적 대응).
    final wroteRow = status >= 200 && status < 300 && (respBody is List ? respBody.isNotEmpty : respBody != null);
    if (wroteRow) {
      final idFilter = captured.query['id'];
      final targetId = (idFilter != null && idFilter.startsWith('eq.')) ? idFilter.substring(3) : null;
      if (request.method == 'PATCH' && bodyJson.containsKey('sort_order') && targetId != null) {
        final idx = existingRows.indexWhere((r) => r['id'] == targetId);
        if (idx >= 0) {
          final updated = List<Map<String, dynamic>>.from(existingRows);
          updated[idx] = {...updated[idx], 'sort_order': bodyJson['sort_order']};
          existingRows = updated;
        }
      } else if (request.method == 'POST' && insertedRow != null) {
        existingRows = [...existingRows, insertedRow];
      } else if (request.method == 'DELETE' && targetId != null) {
        existingRows = existingRows.where((r) => r['id'] != targetId).toList();
      }
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
      expect(r.warnings, contains('사진 삭제 정보를 정리하지 못했어요. 삭제 버튼을 다시 눌러주세요.'));
      // 회귀(review 발견, spec-16-7): 예전엔 warning만 남기고 이 항목을 목록에서 빼버려,
      // 파일 없는 행이 DB에 영구히 남는데 화면에도 baseline에도 없어 재시도가 불가능했다.
      expect(
        r.photos.map((p) => p.rowId),
        [gone.rowId],
        reason: '행이 안 지워졌으면 그 항목은 목록에 남아 다시 삭제를 시도할 수 있어야 한다',
      );
      expect(r.photos.single.status, PhotoStatus.error);
    });

    test('행 삭제가 0행(에러 아님)이면 성공으로 치지 않는다', () async {
      final gone = _savedPhoto('a');
      fakeHttp.responder = (req) => req.method == 'DELETE' ? (status: 200, body: <dynamic>[]) : null;

      final r = await sync(const [], [gone]);
      expect(r.warnings, contains('사진 삭제 정보를 정리하지 못했어요. 삭제 버튼을 다시 눌러주세요.'));
      expect(
        r.photos.map((p) => p.rowId),
        [gone.rowId],
        reason: '0행도 "행이 남았다"는 뜻이므로 항목을 목록에서 지우면 안 된다',
      );
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

    // 2026-08-10 Epic 16 묶음 코드리뷰(verification-gap) — **보상 삭제를 아무도 안 봤다.**
    // 위 테스트들은 sort_order·savedCount·failedCount만 본다. 그런데 INSERT가 실패하면
    // 이미 올라간 Storage 오브젝트는 **아무 행도 가리키지 않는 고아**가 되므로 코드가
    // `deleteObject(p.storagePath!)`로 즉시 정리를 시도한다(photo_sync.dart, "행이 없으면
    // 그 오브젝트는 아무도 못 읽는 고아가 된다"). 그 호출이 사라지거나 엉뚱한 경로를 넘겨도
    // 전 스위트가 green이었다 — 고아 파일은 화면에 안 보여서 아무도 눈치채지 못한다.
    // 파일 헤더의 "이 검사가 안 보는 것" 목록에도 이 항목은 없었다(저자도 몰랐다는 뜻).
    test('INSERT가 실패하면 그 사진의 Storage 오브젝트를 즉시 정리한다(고아 방지)', () async {
      var n = 0;
      fakeHttp.responder = (req) {
        if (req.method != 'POST') return null;
        n += 1;
        return n == 2 ? (status: 400, body: {'message': 'boom'}) : null;
      };

      final r = await sync([_newPhoto('a'), _newPhoto('b'), _newPhoto('c')], const []);
      expect(r.failedCount, 1, reason: '전제: 두 번째 INSERT가 실제로 실패해야 이 검사가 의미 있다');

      final cleanups = log.where((l) => l.startsWith('object:delete:')).toList();
      expect(cleanups.length, 1,
          reason: '실패한 1건만 정리해야 한다 — 0이면 고아 파일이 Storage에 영구히 쌓이고, '
              '2건 이상이면 성공한 사진까지 지운 것이다. 실제: $cleanups');
      expect(cleanups.single, contains(_newPhoto('b').file!.name),
          reason: 'INSERT가 실패한 바로 그 사진(b)의 경로를 지워야 한다 — 다른 경로를 넘기면 '
              '고아는 그대로 남고 멀쩡한 파일이 지워진다. 실제: ${cleanups.single}');
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

    // DW-797(2026-08-10 후속 코드리뷰) — 위 테스트는 **대표가 실제로 넘어간다는 사실**까지만
    // 확인하고 "그걸 사용자에게 알렸는가"는 아무도 안 봤다. 그래서 기존 행 실패 분기에만
    // 있던 경고 조건이 신규 행 INSERT 실패 분기에 빠져 있어도 전 스위트가 green이었다.
    // 시나리오는 바로 위 테스트와 같다(맨 앞 사진의 INSERT만 실패) — 거기에 warnings를 단언한다.
    test('맨 앞 사진의 INSERT가 실패해 대표가 넘어가면 그 사실을 사용자에게 알린다(DW-797)',
        () async {
      var n = 0;
      fakeHttp.responder = (req) {
        if (req.method != 'POST') return null;
        n += 1;
        return n == 1 ? (status: 400, body: {'message': 'boom'}) : null;
      };

      final r = await sync([_newPhoto('a'), _newPhoto('b')], const []);

      expect(r.failedCount, 1, reason: '전제: 첫 INSERT가 실제로 실패해야 이 검사가 의미 있다');
      expect(
        r.warnings.any((w) => w.contains('대표 사진이 바뀌었을 수 있어요')),
        isTrue,
        reason: '판매자가 맨 앞에 둔 사진이 대표가 되지 못했다 — 개별 카드의 실패 배지만으로는 '
            '"대표가 다른 장으로 확정됐다"는 사실을 알 수 없다. 실제 warnings: ${r.warnings}',
      );
      expect(
        r.warnings.any((w) => w.contains('순서를 저장하지 못한')),
        isFalse,
        reason: 'INSERT 실패는 "순서 저장 실패"가 아니다 — 그 행은 아예 만들어지지 않았다. '
            '사실과 다른 문구를 붙이면 판매자가 엉뚱한 데를 고치려 든다. 실제: ${r.warnings}',
      );
    });
  });

  group('spec-16-11 결함1 근본수정 — 행 삭제 실패 항목은 저장 대상에서만 빠진다(목록엔 유지)', () {
    test('사진 1장짜리 매물: Storage 삭제는 성공·행 삭제만 실패하면, 그 행은 sort_order를 '
        '새로 받지 않고 대표로도 지정되지 않는다(AC1)', () async {
      final gone = _savedPhoto('a');
      fakeHttp.responder = (req) =>
          req.method == 'DELETE' ? (status: 400, body: {'message': 'boom'}) : null;

      final r = await sync(const [], [gone]);

      // 화면 목록엔 오류 상태로 남아 재시도 가능해야 한다(기존 계약, 회귀 확인).
      expect(r.photos.single.status, PhotoStatus.error);
      expect(r.photos.single.rowId, gone.rowId);

      // 결함1 핵심: 이 행은 sort_order UPDATE를 받지 않는다 — saved에서 빠졌기 때문이다.
      expect(
        fakeHttp.requests.any((req) => req.method == 'PATCH' && req.body.containsKey('sort_order')),
        isFalse,
        reason: '삭제에 실패해 남은 행은 저장 대상(saved)에서 빠져야 한다 — sort_order UPDATE가 나가면 안 된다',
      );
      // 대표로도 지정되지 않는다 — coverPath가 null이라 is_cover=true 문장 자체가 안 나간다.
      expect(
        fakeHttp.requests.any((req) => req.method == 'PATCH' && req.body['is_cover'] == true),
        isFalse,
        reason: '저장할 사진이 없으므로(saved가 비었으므로) 대표 지정 문장이 나가면 안 된다',
      );
    });

    test('여러 장 중 하나만 삭제 실패해도 나머지는 정상적으로 sort_order를 받고, 실패한 행만 빠진다', () async {
      final kept = _savedPhoto('kept');
      final gone = _savedPhoto('gone');
      fakeHttp.responder = (req) =>
          req.method == 'DELETE' ? (status: 400, body: {'message': 'boom'}) : null;

      await sync([kept], [kept, gone]);

      final sortReqs = fakeHttp.requests
          .where((r) => r.method == 'PATCH' && r.body.containsKey('sort_order'))
          .toList();
      expect(sortReqs, hasLength(1), reason: 'kept 1건만 sort_order UPDATE를 받아야 한다');
      expect(sortReqs.single.query['id'], 'eq.${kept.rowId}');
    });
  });

  group('spec-16-11 결함2(DW-748) — sort_order UPDATE 실패 행이 옛 번호를 들고 남아도 중복이 생기지 않는다', () {
    test('재정렬 없이 재제출 중 한 행의 UPDATE가 실패해도 최종 sort_order에 중복이 없다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      final c = _savedPhoto('c', rowId: 'row-c');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
        {'id': 'row-c', 'sort_order': 2},
      ];
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['sort_order'] != null && req.query['id'] == 'eq.row-b')
              ? (status: 400, body: {'message': 'boom'})
              : null;

      final r = await sync([a, b, c], [a, b, c]);

      // T6 — 하드코딩 literal(예전의 `const bOldOrder = 1`) 대신 가짜 DB가 실제로 반영한 최종
      // 상태(existingRows)를 읽는다. b는 UPDATE가 실패했으므로 이 가짜도 그 행의 sort_order를
      // 갱신하지 않았어야 한다 — literal이 아니라 그 사실 자체를 확인한다.
      final finalById = {
        for (final row in fakeHttp.existingRows) row['id'] as String: row['sort_order'] as int,
      };
      expect(finalById['row-b'], 1, reason: 'b는 UPDATE 실패로 옛 값을 그대로 들고 있어야 한다');
      expect(finalById.values.toSet().length, finalById.length,
          reason: '살아있는 모든 행의 최종 sort_order에 중복이 없어야 한다(DW-748)');
      // spec-16-11 후속 코드리뷰 패치(P5) — a(화면 맨 앞)가 b보다 먼저 처리되어 이미 대표로
      // 확정된 뒤에 b의 UPDATE가 실패한다. 대표가 이미 정해졌으므로 "대표 사진이 바뀌었을 수
      // 있다"는 문구는 이 시나리오에선 거짓이다 — 강화된 경고가 아니라 평범한 경고여야 한다.
      expect(r.warnings, contains('사진 순서를 저장하지 못한 항목이 있어요.'));
      expect(r.warnings, isNot(contains('사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.')));
    });

    test('재정렬과 동시에 다른 행의 UPDATE가 실패해도(반례) 최종 sort_order에 중복이 없고, '
        '화면 맨 앞 사진이 (sort_order,id) 최솟값을 갖는다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      final c = _savedPhoto('c', rowId: 'row-c');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
        {'id': 'row-c', 'sort_order': 2},
      ];
      // 화면 순서를 c, a, b로 재정렬(사용자가 c를 맨 앞으로) — c와 무관한 b의 UPDATE만 실패시킨다.
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['sort_order'] != null && req.query['id'] == 'eq.row-b')
              ? (status: 400, body: {'message': 'boom'})
              : null;

      await sync([c, a, b], [a, b, c]);

      // T6 — literal(`const bOldOrder = 1`) 대신 가짜 DB의 최종 상태를 읽는다.
      final finalById = {
        for (final row in fakeHttp.existingRows) row['id'] as String: row['sort_order'] as int,
      };
      final bOldOrder = finalById['row-b']!;
      expect(bOldOrder, 1, reason: 'b는 UPDATE 실패로 옛 값을 그대로 들고 있어야 한다');

      // 이 반례가 바로 DW-748의 핵심 위험 지점이다 — c가 맨 앞으로 이동하며 원래 0·1·2 자리를
      // 다시 채우려 하는데, b가 실패해 1을 그대로 들고 있으면 다른 행이 1을 다시 쓰면 중복이 난다.
      expect(finalById.values.toSet().length, finalById.length, reason: '재정렬+실패가 겹쳐도 중복이 없어야 한다');
      // 화면 맨 앞(c)이 실제로 (sort_order,id) 최솟값을 가져야 한다 — b가 실패로 옛 번호(1)를
      // 그대로 들고 있어도 c가 그보다 작아야 한다(파일 최상단 경고: 대표는 sort_order로 읽힌다).
      expect(finalById['row-c'], lessThan(bOldOrder));
      expect(finalById['row-c'], lessThan(finalById['row-a']!));
    });
  });

  group('spec-16-11 불변식 통합 검사 — 부분 실패를 섞은 시나리오에서도 중복 없고 대표가 의도한 장이다', () {
    test('행 삭제 실패(대표였던 사진) + sort_order UPDATE 실패가 동시에 있어도 sort_order 중복이 '
        '없고, 대표는 화면 맨 앞의 정상 저장된 사진이다', () async {
      final gone = _savedPhoto('gone', rowId: 'row-gone'); // 기존 대표(sort_order 0) — 삭제 시도, 행 삭제 실패 예정
      final a = _savedPhoto('a', rowId: 'row-a'); // 화면 맨 앞으로 옮겨 새 대표가 될 사진
      final b = _savedPhoto('b', rowId: 'row-b'); // sort_order UPDATE 실패 예정
      fakeHttp.existingRows = [
        {'id': 'row-gone', 'sort_order': 0},
        {'id': 'row-a', 'sort_order': 1},
        {'id': 'row-b', 'sort_order': 2},
      ];
      fakeHttp.responder = (req) {
        if (req.method == 'DELETE') return (status: 400, body: {'message': 'boom'}); // 행 삭제 실패
        if (req.method == 'PATCH' &&
            req.body['sort_order'] != null &&
            req.query['id'] == 'eq.row-b') {
          return (status: 400, body: {'message': 'boom'}); // sort_order UPDATE 실패
        }
        return null;
      };

      // 화면: gone은 지우고, a를 맨 앞으로 재배치.
      final r = await sync([a, b], [gone, a, b]);

      // gone은 저장 대상에서 빠졌으므로 sort_order UPDATE를 받지 않는다(결함1).
      expect(
        fakeHttp.requests.any(
          (req) =>
              req.method == 'PATCH' &&
              req.body.containsKey('sort_order') &&
              req.query['id'] == 'eq.row-gone',
        ),
        isFalse,
      );

      // T6 — literal(`const bOldOrder = 2`·`const goneOldOrder = 0`) 대신 가짜 DB의 최종
      // 상태(existingRows)를 읽는다. gone은 행 삭제가 실패했으니 그대로 살아 있고, b는
      // sort_order UPDATE가 실패했으니 옛 값을 그대로 갖고 있어야 한다 — 픽스처를 손으로
      // 베껴 쓴 literal이 실제로 반영된 값과 갈라지는 사고를 이 가짜 자체가 막는다.
      final finalById = {
        for (final row in fakeHttp.existingRows) row['id'] as String: row['sort_order'] as int,
      };
      expect(finalById['row-gone'], 0, reason: 'gone은 행 삭제 실패로 그대로 살아 있어야 한다');
      expect(finalById['row-b'], 2, reason: 'b는 UPDATE 실패로 옛 값을 그대로 들고 있어야 한다');
      final aOrder = finalById['row-a']!;

      // 불변식 그 자체: 살아있는 모든 행의 최종 sort_order에 중복이 없다.
      expect(finalById.values.toSet().length, finalById.length);
      // 불변식 그 자체: 화면 맨 앞(a)이 실제로 최솟값이다 — gone이 옛 대표 번호(0)를 그대로
      // 들고 있어도 a가 그보다 작아야 한다(결함1+결함2를 함께 근본수정한 핵심).
      expect(aOrder, lessThan(finalById['row-gone']!));
      expect(aOrder, lessThan(finalById['row-b']!));

      // is_cover도 화면 맨 앞(a)을 지목해야 한다(단, 실제로 읽히는 건 sort_order다 — 위 단언이 핵심).
      final setCover = fakeHttp.requests.firstWhere(
        (req) => req.method == 'PATCH' && req.body['is_cover'] == true,
      );
      expect(setCover.query['storage_path'], 'eq.${a.storagePath}');

      // 사용자에게 사실대로 알린다 — 삭제 실패·순서 실패 각각의 경고가 남는다.
      expect(r.warnings, contains('사진 삭제 정보를 정리하지 못했어요. 삭제 버튼을 다시 눌러주세요.'));
      // spec-16-11 후속 코드리뷰 패치(P5) — 화면 맨 앞(a)이 saved의 첫 항목이라 b보다 먼저
      // 처리돼 이미 대표로 확정된 뒤에 b의 UPDATE가 실패한다. 대표가 이미 정해졌으므로
      // "대표 사진이 바뀌었을 수 있다"는 강화된 문구는 이 시나리오엔 맞지 않는다.
      expect(r.warnings, contains('사진 순서를 저장하지 못한 항목이 있어요.'));
      expect(r.warnings, isNot(contains('사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.')));
    });
  });

  group('spec-16-11 후속 코드리뷰(2026-08-10) 패치 — candidateOrder가 자기 옛 번호를 우선 재사용한다', () {
    test('실패가 전혀 없는 평범한 재저장을 반복해도 대표 사진의 sort_order가 계속 음수로 밀려나지 않는다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
      ];

      await sync([a, b], [a, b]);
      final firstSortReqs = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final aOrder1 = firstSortReqs.firstWhere((req) => req.query['id'] == 'eq.row-a').body['sort_order'] as int;
      // 실패가 없었으니 대표(맨 앞) a는 자기 옛 번호(0)를 그대로 유지해야 한다 — 후속
      // 코드리뷰(2026-08-10) 지적: 첫 구현은 실패가 없어도 매번 예약값보다 작은 새 번호(-1)를
      // 줘서 이 값이 -1이 됐었다.
      expect(aOrder1, 0);

      // T6 — existingRows는 이제 성공한 PATCH를 스스로 반영한다(가짜가 진짜 쓰기를 따라간다),
      // 그래서 두 번째 저장 전에 픽스처를 손으로 다시 만들어 줄 필요가 없다 — 예전엔 이 자리에서
      // literal을 손으로 베껴 썼는데, 그게 실제 반영값과 갈라지는 사고를 이 파일이 이미 겪었다.
      final requestCountAfterFirst = fakeHttp.requests.length;

      await sync([a, b], [a, b]);
      final secondSortReqs = fakeHttp.requests
          .skip(requestCountAfterFirst)
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final aOrder2 = secondSortReqs.firstWhere((req) => req.query['id'] == 'eq.row-a').body['sort_order'] as int;
      expect(aOrder2, aOrder1,
          reason: '두 번째 저장에서도 실패가 없으니 대표 사진의 sort_order는 첫 저장과 같아야 한다 '
              '— 매 저장마다 값이 계속 내려가면(드리프트) "실제 저장 성공 개수 기준 연속 정수" '
              '계약이 저장을 반복할 때마다 스스로 깨진다.');
    });

    test('기존 사진이 있는 매물에 새로 추가한 사진을 맨 앞(대표)으로 끌어와 저장하면, '
        '그 새 사진이 기존 사진들의 옛 번호보다 작은 sort_order로 대표가 된다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      final fresh = _newPhoto('fresh');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
      ];

      // 화면: 새 사진을 맨 앞으로 끌어오고, 기존 두 장은 뒤로 밀린다. initial(기존 행)은 a·b뿐.
      final r = await sync([fresh, a, b], [a, b]);

      final insert = fakeHttp.requests.singleWhere((req) => req.method == 'POST');
      final insertOrder = insert.body['sort_order'] as int;
      final sortReqs = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final aOrder = sortReqs.firstWhere((req) => req.query['id'] == 'eq.row-a').body['sort_order'] as int;
      final bOrder = sortReqs.firstWhere((req) => req.query['id'] == 'eq.row-b').body['sort_order'] as int;

      // 새 사진(INSERT 대상)이 기존 두 행보다 작은 값을 받아야 (sort_order,id) 최솟값으로 이긴다.
      expect(insertOrder, lessThan(aOrder));
      expect(insertOrder, lessThan(bOrder));
      expect({insertOrder, aOrder, bOrder}.length, 3, reason: '중복이 없어야 한다');

      final setCover = fakeHttp.requests.firstWhere(
        (req) => req.method == 'PATCH' && req.body['is_cover'] == true,
      );
      expect(setCover.query['storage_path'], 'eq.${insert.body['storage_path']}',
          reason: '대표는 화면 맨 앞의 새 사진이어야 한다');
      expect(r.warnings, isEmpty, reason: '이 시나리오엔 실패가 없다');
    });
  });

  group('spec-16-11 후속 코드리뷰(2026-08-10) 패치 검증 — 새 회귀 테스트(T1~T5)', () {
    test('T1 — 이미 중복된 옛 sort_order 데이터에서 실패가 겹쳐도 살아 있는 중복을 재생산하지 않는다(P1)', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      // DW-748이 원래 겨냥한, 아직 정리되지 않은 데이터 — 두 행이 이미 같은 옛 번호(0)를 들고 있다.
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 0},
      ];
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['sort_order'] != null && req.query['id'] == 'eq.row-b')
              ? (status: 400, body: {'message': 'boom'})
              : null;

      await sync([a, b], [a, b]);

      final sortReqs = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final aOrder = sortReqs.firstWhere((req) => req.query['id'] == 'eq.row-a').body['sort_order'] as int;
      // b의 UPDATE가 실패해 0을 그대로 들고 있다. a가 정확히 0을 다시 쓰면(옛 `candidateOrder`의
      // `<=` 버그) 살아 있는 중복이 그대로 재생산된다 — a는 반드시 0보다 작아야 한다.
      expect(aOrder, lessThan(0),
          reason: 'candidateOrder가 ownOld==minOther일 때도 ownOld를 재사용하면(옛 `<=`) '
              'b가 아직 들고 있는 0을 a가 다시 써서 중복이 재생산된다');
    });

    test('T2 — 화면 기준선이 비어 있어도 DB에 살아있는 행이 있으면 스냅샷을 읽어 충돌을 피한다(P2)', () async {
      // 화면 기준선(initialPhotos)은 비어 있지만 DB에는 살아있는 행이 있는 상황 — 이전 INSERT의
      // rowId를 못 읽어 baseline에서 빠졌거나 toPhotoItems가 계약 위반 행을 버린 경우 재현된다.
      fakeHttp.existingRows = [
        {'id': 'row-old', 'sort_order': 0},
      ];
      final fresh = _newPhoto('fresh');

      await sync([fresh], const []);

      expect(
        fakeHttp.requests.any((req) => req.method == 'GET'),
        isTrue,
        reason: '게이트가 initialPhotos가 아니라 saved를 봐야 한다 — saved가 비어있지 않으므로 '
            'GET이 나가야 한다(옛 게이트는 initialPhotos가 비었다는 이유로 이 GET을 건너뛰었다)',
      );
      final insert = fakeHttp.requests.singleWhere((req) => req.method == 'POST');
      expect(
        insert.body['sort_order'] as int,
        lessThan(0),
        reason: '이미 있는 행(0)과 충돌하지 않으려면 그보다 작은 값을 받아야 한다',
      );

      // P3(2회차 후속 코드리뷰) — 이 스냅샷 GET에 listing_id 필터가 빠지면(뮤테이션으로 실측)
      // 전 스위트가 green으로 남는다. 남의 매물 행까지 예약값으로 끌어와 이 매물과 무관한
      // sort_order와 충돌을 피하려다 불필요하게 더 내려가거나, 반대로 실제로 겹치는 남의 매물
      // 행을 못 보고 지나칠 수 있다.
      final get = fakeHttp.requests.firstWhere((r) => r.method == 'GET');
      expect(get.query['listing_id'], 'eq.$_listingId',
          reason: '스냅샷이 남의 매물 행까지 예약하면 안 된다');
    });

    test('T3 — 기존 sort_order 스냅샷 조회 자체가 실패해도 저장은 계속되고 사용자에게 알린다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      fakeHttp.responder =
          (req) => req.method == 'GET' ? (status: 500, body: {'message': 'boom'}) : null;

      final r = await sync([a], [a]);

      expect(
        fakeHttp.requests.any((req) => req.method == 'PATCH' && req.body.containsKey('sort_order')),
        isTrue,
        reason: '스냅샷 조회가 실패해도 sort_order 저장 자체는 계속돼야 한다',
      );
      final coverPatches = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('is_cover'))
          .toList();
      expect(coverPatches, hasLength(2), reason: '대표 기록 2문장도 그대로 나가야 한다');
      expect(
        r.warnings,
        contains('기존 사진 순서 정보를 불러오지 못해 일부 안전 점검을 건너뛰었어요. 저장 후 대표 사진을 확인해 주세요.'),
      );
    });

    test('T4 — 화면 맨 앞(첫 saved 항목)의 sort_order UPDATE가 실패해도 다음 후보가 대표를 이어받는다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
      ];
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['sort_order'] != null && req.query['id'] == 'eq.row-a')
              ? (status: 400, body: {'message': 'boom'})
              : null;

      final r = await sync([a, b], [a, b]);

      final sortReqs = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final bOrder = sortReqs.firstWhere((req) => req.query['id'] == 'eq.row-b').body['sort_order'] as int;
      // a는 UPDATE 실패로 옛 값(0)을 그대로 들고 있다 — b가 그보다 작아야 대표를 이어받는다.
      expect(bOrder, lessThan(0));

      final setCover = fakeHttp.requests.firstWhere(
        (req) => req.method == 'PATCH' && req.body['is_cover'] == true,
      );
      expect(setCover.query['storage_path'], 'eq.${b.storagePath}',
          reason: '최초 후보(a)가 실패하면 다음 후보(b)가 대표를 이어받아야 한다');
      // P4 — 이 실패는 catch 분기(예외)를 탄다. 대표가 아직 안 정해진 상태(a가 첫 saved
      // 항목)에서 난 실패이므로 "대표가 바뀌었을 수 있다" 문구가 나가야 한다 — 예전엔 이
      // 분기의 경고가 어느 테스트로도 단언되지 않았다(measurement).
      expect(r.warnings, contains('사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.'));
    });

    test('T5 — sort_order PATCH가 200인데 0행을 돌려주는 조용한 실패(RLS 등)도 실패로 취급한다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
      ];
      // 세션 만료·매물이 판매완료로 바뀌는 등 실제 운영에서 재현되는 모양 — 예외가 아니라
      // 200에 빈 배열로 온다(data.isEmpty 경로, catch 경로가 아니다).
      fakeHttp.responder = (req) =>
          (req.method == 'PATCH' && req.body['sort_order'] != null && req.query['id'] == 'eq.row-a')
              ? (status: 200, body: <dynamic>[])
              : null;

      final r = await sync([a, b], [a, b]);

      expect(r.warnings, contains('사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.'));

      final sortReqs = fakeHttp.requests
          .where((req) => req.method == 'PATCH' && req.body.containsKey('sort_order'))
          .toList();
      final bOrder = sortReqs.firstWhere((req) => req.query['id'] == 'eq.row-b').body['sort_order'] as int;
      // 0행 응답도 실패로 취급해 a가 여전히 0을 들고 있다고 봐야 한다 — b가 그 번호를
      // 다시 쓰면 살아 있는 중복이 생긴다.
      expect(bOrder, isNot(0), reason: '0행 응답(조용한 실패)을 성공으로 오인하면 b가 0을 재사용해 중복이 생긴다');
      expect(bOrder, lessThan(0));
    });
  });

  group('spec-16-11 후속 코드리뷰 2회차(2026-08-10) 패치 검증 — P1·P2', () {
    test(
        'P1 — 대표 확정 전에 한 행, 확정 후에 다른 행이 각각 실패해도 경고가 정확히 1개, '
        '대표-언급 문장 하나로 합쳐진다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      final c = _savedPhoto('c', rowId: 'row-c');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 0},
        {'id': 'row-b', 'sort_order': 1},
        {'id': 'row-c', 'sort_order': 2},
      ];
      // a(화면 맨 앞, 대표 후보)는 대표가 정해지기 전에 실패하고, c는 b가 대표로 확정된
      // 뒤에 실패한다 — 두 실패가 대표 확정 시점의 앞뒤로 갈린다.
      fakeHttp.responder = (req) => (req.method == 'PATCH' &&
              req.body['sort_order'] != null &&
              (req.query['id'] == 'eq.row-a' || req.query['id'] == 'eq.row-c'))
          ? (status: 400, body: {'message': 'boom'})
          : null;

      final r = await sync([a, b, c], [a, b, c]);

      // 측정: 패치 전에는 a의 실패가 "…바뀌었을 수 있어요" 문구를, c의 실패가 평범한 문구를
      // 각각 warnings에 넣어 toSet()으로도 못 합쳐진 채 ' · '로 이어붙어 사용자에게
      // "…바뀌었을 수 있어요. · 사진 순서를 저장하지 못한 항목이 있어요."처럼 중복·모순으로
      // 보이는 문구가 나갔다. 지금은 조건만 보고 문장을 한 번만 조립하므로 1개여야 한다.
      expect(r.warnings.length, 1);
      expect(r.warnings.single, '사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.');
    });

    test(
        'P2 — 스냅샷 조회 자체가 실패한 상태에서 대표가 이미 확정된 뒤 다른 행이 실패해도 '
        '"대표가 바뀌었을 수 있다" 문구가 나간다', () async {
      final a = _savedPhoto('a', rowId: 'row-a');
      final b = _savedPhoto('b', rowId: 'row-b');
      fakeHttp.existingRows = [
        {'id': 'row-a', 'sort_order': 5},
        {'id': 'row-b', 'sort_order': -3},
      ];
      fakeHttp.responder = (req) {
        if (req.method == 'GET') return (status: 500, body: {'message': 'boom'});
        if (req.method == 'PATCH' &&
            req.body['sort_order'] != null &&
            req.query['id'] == 'eq.row-b') {
          return (status: 400, body: {'message': 'boom'});
        }
        return null;
      };

      final r = await sync([a, b], [a, b]);

      // 측정: 스냅샷 GET이 500이라 reservedOrders·oldOrderByRowId가 둘 다 빈 채로 진행된다 —
      // a는 candidateOrder(null)이 order(=0)를 그대로 돌려줘 PATCH가 성공하고(대표로 확정),
      // b는 sort_order:1로 PATCH를 시도했다가 실패해 옛 값(-3)을 그대로 든다. 최종
      // {row-a: 0, row-b: -3}에서는 -3이 더 작아 실제 대표는 b로 넘어갔는데도, coverAssigned만
      // 보면 "이미 확정됐다"고 오판해 경고가 안 나갔었다 — snapshotOk도 함께 봐야 한다.
      final finalById = {
        for (final row in fakeHttp.existingRows) row['id'] as String: row['sort_order'] as int,
      };
      expect(finalById['row-a'], 0);
      expect(finalById['row-b'], -3, reason: 'b는 PATCH 실패로 옛 값을 그대로 들고 있어야 한다');
      expect(finalById['row-b'], lessThan(finalById['row-a']!),
          reason: '실제 (sort_order,id) 최솟값은 b다 — 대표가 b로 넘어갔다는 뜻');

      expect(r.warnings, contains('사진 순서를 저장하지 못한 항목이 있어요. 대표 사진이 바뀌었을 수 있어요.'));
      expect(
        r.warnings,
        contains('기존 사진 순서 정보를 불러오지 못해 일부 안전 점검을 건너뛰었어요. 저장 후 대표 사진을 확인해 주세요.'),
      );
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
