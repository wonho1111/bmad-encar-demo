// Story 16.4 채팅 레포지토리 순수 함수 단위테스트 — roomTopic 형식·reuseFailedKey 4분기·
// flushChatMessageQueue(전부성공/부분실패시 순서·remaining 보존/예외를 실패로 흡수)·
// isIdempotentResendMatch(멱등 재전송 23505 후 재조회한 기존 행이 내 전송인지 판정, 3분기)·
// parseUnreadByRoomRows(chat_unread_by_room() RPC 응답 매핑, 코드리뷰 patch 6)·
// markRoomRead 실제 upsert 배선(코드리뷰 patch 12, 가짜 httpClient로 실 SupabaseClient 구동).
// web messages.test.ts(reuseFailedKey·flushMessageQueue)·chat.test.ts(markChatRoomRead)와 동일한
// 시나리오를 Dart로 미러링한다(docs/conventions.md §12.4·§12.5·§12.6).
import 'dart:convert';
import 'dart:io';

import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart' show SupabaseClient;

/// `SupabaseClient(..., httpClient: ...)`에 주입할 가짜 HTTP 클라이언트 — 실제 네트워크를 타지
/// 않고 나간 요청(메서드·URL·헤더·본문)을 그대로 캡처한다. web `chat.test.ts`가 `vi.fn()`으로
/// `.from().upsert()`를 통째로 목킹하는 것과 같은 목적을 Dart 쪽 실제 주입 지점으로 이룬다
/// (mockito/mocktail 등 새 패키지 없이 `package:http`의 `BaseClient`만으로 충분 — A2).
class _CapturedRequest {
  _CapturedRequest({
    required this.method,
    required this.url,
    required this.headers,
    required this.body,
  });

  final String method;
  final Uri url;
  final Map<String, String> headers;
  final String body;
}

class _FakeHttpClient extends http.BaseClient {
  // 두 테스트 모두 성공 응답(201, 빈 본문)만 필요해 커스터마이즈 지점을 두지 않는다(A2) —
  // 실패 응답 시나리오가 필요해지면 그때 매개변수화한다.
  static const int _statusCode = 201;
  static const String _responseBody = '';

  final List<_CapturedRequest> requests = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    var body = '';
    if (request is http.Request) body = request.body;
    requests.add(
      _CapturedRequest(
        method: request.method,
        url: request.url,
        headers: Map<String, String>.from(request.headers),
        body: body,
      ),
    );
    final bytes = utf8.encode(_responseBody);
    return http.StreamedResponse(
      Stream.value(bytes),
      _statusCode,
      request: request,
      headers: {'content-length': '${bytes.length}'},
    );
  }
}

/// 로그인 세션을 네트워크 없이 주입한다 — `markRoomRead`가 `_client.auth.currentUser?.id`를
/// 읽으므로 세션이 있어야 upsert까지 도달한다. `access_token`이 진짜 JWT가 아니어도 무방하다:
/// `gotrue-2.22.0`의 `Session._expiresAt`는 JWT 파싱이 실패하면(FormatException) null을 반환하고
/// `isExpired`는 `expiresAt == null`이면 false로 본다(실측 확인) — 그래서 `recoverSession`이
/// "만료 안 됨" 분기로 들어가 네트워크 재발급 없이 세션을 즉시 저장한다.
Future<void> _signIn(SupabaseClient client, String userId) => client.auth.recoverSession(
  jsonEncode({
    'access_token': 'not-a-real-jwt',
    'token_type': 'bearer',
    'refresh_token': 'refresh-token',
    'expires_in': 3600,
    'user': {
      'id': userId,
      'aud': 'authenticated',
      'app_metadata': <String, dynamic>{},
      'created_at': '2026-01-01T00:00:00Z',
    },
  }),
);

/// 멱등 재전송(23505) 경로 전용 fake — 요청 순서에 따라 다른 응답을 돌려줘야 해서
/// 위 `_FakeHttpClient`(201 고정)와 별도로 둔다. 기존 것을 매개변수화하면 그 단순함에
/// 기대는 두 테스트까지 함께 흔들린다.
class _ScriptedHttpClient extends http.BaseClient {
  _ScriptedHttpClient(this.script);

  /// (상태코드, 본문) — 요청 순서대로 하나씩 소비한다.
  final List<({int status, String body})> script;
  final List<_CapturedRequest> requests = [];
  int _i = 0;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    var body = '';
    if (request is http.Request) body = request.body;
    requests.add(_CapturedRequest(
      method: request.method,
      url: request.url,
      headers: Map<String, String>.from(request.headers),
      body: body,
    ));
    final step = _i < script.length ? script[_i] : (status: 200, body: '[]');
    _i += 1;
    final bytes = utf8.encode(step.body);
    return http.StreamedResponse(
      Stream.value(bytes),
      step.status,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

void main() {
  group('markRoomRead — 실제 upsert 배선(FR57/§12.6, 코드리뷰 patch 12)', () {
    // markRoomRead()는 실 네트워크 호출 메서드라 위젯테스트가 지금까지 ChatRepository를 통째로
    // 가짜로 갈아 끼워 검증해 왔다(chat_room_screen_test.dart의 _FakeChatRepository) — 그래서
    // upsert의 실제 인자(테이블명·(user_id, room_id) 복합키·onConflict 문자열)는 어떤 테스트로도
    // 실행되지 않았다. web은 이 정확히 같은 문제를 가짜 SupabaseClient(`chat.test.ts`)로 잡는다
    // — `ChatRepository`의 생성자가 이미 `SupabaseClient? client`를 받으므로, `SupabaseClient`
    // 자체가 지원하는 `httpClient` 주입 지점으로 같은 효과를 낸다(새 mock 패키지 불필요, A2).
    test('chat_room_reads에 (user_id, room_id) 복합키로 upsert하고 onConflict를 싣는다', () async {
      final fakeHttp = _FakeHttpClient();
      final client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
      addTearDown(client.dispose);
      await _signIn(client, 'user-1');

      final repo = ChatRepository(client: client);
      await repo.markRoomRead('room-1');

      expect(fakeHttp.requests, hasLength(1));
      final req = fakeHttp.requests.single;
      expect(req.method, 'POST');
      expect(req.url.path, endsWith('/rest/v1/chat_room_reads'));
      expect(
        req.url.queryParameters['on_conflict'],
        'user_id,room_id',
        reason: '복합 PK(user_id, room_id) 위에서 UPSERT가 성립하려면 이 충돌 대상이 필요하다',
      );
      expect(req.headers['Prefer'], contains('resolution=merge-duplicates'));

      final body = jsonDecode(req.body) as Map<String, dynamic>;
      expect(body['user_id'], 'user-1');
      expect(body['room_id'], 'room-1');
      expect(body['last_read_at'], isA<String>());
      expect(
        () => DateTime.parse(body['last_read_at'] as String),
        returnsNormally,
        reason: 'last_read_at은 파싱 가능한 ISO 문자열이어야 한다',
      );
    });

    test('로그인 세션이 없으면(currentUser == null) upsert를 아예 시도하지 않는다', () async {
      final fakeHttp = _FakeHttpClient();
      final client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
      addTearDown(client.dispose);
      // _signIn을 호출하지 않는다 — currentUser가 null인 상태 그대로.

      final repo = ChatRepository(client: client);
      await repo.markRoomRead('room-1');

      expect(fakeHttp.requests, isEmpty, reason: '보낼 사람이 없으면 네트워크를 아예 타면 안 된다');
    });
  });

  group('fetchRooms 정렬 배선(FR57/§12.6, 코드리뷰 patch 10) — 소스 정적 스캔', () {
    // fetchRooms()는 실 네트워크 호출 메서드라 이 레포 관례상(다른 레포지토리 테스트들과 동일 —
    // wishlist_repository_test.dart 헤더 참조) 위젯/유닛 테스트로 실행하지 않는다 — 오직
    // ChatRoomSummary.fromMap 파싱만 chat_model_test.dart가 본다. 그래서 `.order('last_message_at', …)`
    // 를 `created_at`으로 되돌려도(방 생성순으로 회귀해도) 어떤 테스트도 안 잡았다. web이 같은
    // 문제를 `unreadWiringContract.test.ts`(소스 정적 스캔)로 고정한 것과 동일 기법을 Dart
    // 소스에도 적용한다(B9 "실행되는 검사로 고정").
    //
    // 이 검사가 안 보는 것: 정렬이 실제 화면에 최신순으로 보이는지(런타임 동작) — 그건 스펙의
    // Manual checks(로컬 Supabase 실측) 몫이다. 여기서는 "쿼리가 그 컬럼으로 정렬을 건다"만 본다.
    test('fetchRooms는 last_message_at desc, id desc로 정렬한다', () {
      final source = File('lib/features/chat/chat_repository.dart').readAsStringSync();
      final methodStart = source.indexOf('Future<List<ChatRoomSummary>> fetchRooms(');
      expect(
        methodStart,
        greaterThan(-1),
        reason: 'fetchRooms 메서드를 찾지 못했습니다(이름이 바뀌었다면 이 검사도 함께 고칠 것)',
      );
      // 다음 메서드(fetchRoom) 시작 전까지로 본문을 잘라, 다른 메서드의 .order() 호출과
      // (예: fetchMessages의 created_at·id 정렬) 섞이지 않게 한다.
      final nextMethodStart = source.indexOf(
        '\n  Future<ChatRoomSummary?> fetchRoom(',
        methodStart,
      );
      expect(nextMethodStart, greaterThan(methodStart));
      final body = source.substring(methodStart, nextMethodStart);

      final orderKeys = RegExp(
        r"\.order\(\s*'([a-z0-9_]+)'",
      ).allMatches(body).map((m) => m.group(1)).toList();

      expect(orderKeys.length, greaterThanOrEqualTo(2));
      expect(
        orderKeys[0],
        'last_message_at',
        reason: '방 생성 시각(created_at)이 아니라 그 방의 마지막 메시지 시각순이어야 한다(§12.6)',
      );
      expect(orderKeys[1], 'id', reason: '동시각 안정화용 2차정렬(기존 관례 유지)');
      expect(
        body,
        contains("order('last_message_at', ascending: false)"),
        reason: '내림차순(최신 문의가 위)이어야 한다',
      );
    });
  });
  group('roomTopic', () {
    test('chat:room:{roomId} 형식 — 0023 SQL 트리거·RLS 리터럴과 문자 그대로 동일해야 한다', () {
      expect(roomTopic('abc-123'), 'chat:room:abc-123');
    });
  });

  group('reuseFailedKey', () {
    test('직전 실패 없음 → null(새 키를 만들어야 함)', () {
      expect(reuseFailedKey(null, '안녕', 1000, 60000), isNull);
    });

    test('본문이 다르면 → null(새 메시지이므로 재사용하지 않음)', () {
      final failed = FailedSend(clientMessageId: 'k1', body: '안녕', at: 1000);
      expect(reuseFailedKey(failed, '다른 메시지', 1500, 60000), isNull);
    });

    test('재사용 창을 넘기면 → null(오래된 키는 재사용하지 않음)', () {
      final failed = FailedSend(clientMessageId: 'k1', body: '안녕', at: 1000);
      // now - at = 60001 > windowMs(60000)
      expect(reuseFailedKey(failed, '안녕', 61001, 60000), isNull);
    });

    test('본문이 같고 창 안이면 → 그 키를 재사용한다', () {
      final failed = FailedSend(clientMessageId: 'k1', body: '안녕', at: 1000);
      // now - at = 60000 == windowMs → 경계값은 포함(> 만 초과로 거부).
      expect(reuseFailedKey(failed, '안녕', 61000, 60000), 'k1');
      expect(reuseFailedKey(failed, '안녕', 30000, 60000), 'k1');
    });
  });

  group('isIdempotentResendMatch — 멱등 재전송(23505) 후 재조회한 기존 행 판정', () {
    // sendMessage() 자체는 실 Supabase 호출이라 이 리포의 관례(다른 레포지토리 테스트와 동일 —
    // wishlist_repository_test.dart 헤더 참조) 상 여기서 다루지 않는다. 그 안의 23505 분기가
    // "재조회한 기존 행이 내 전송인가"를 판정하는 부분만 순수 함수로 떼어 여기서 직접 검증한다.
    test('sender_id·body 둘 다 일치 → true(멱등 재전송 성공으로 수렴)', () {
      expect(
        isIdempotentResendMatch(
          existingSenderId: 'user-1',
          existingBody: '안녕하세요',
          callerSenderId: 'user-1',
          callerBody: '안녕하세요',
        ),
        isTrue,
      );
    });

    test('sender_id 불일치 → false(다른 사용자의 행 — UUID 충돌 배제)', () {
      expect(
        isIdempotentResendMatch(
          existingSenderId: 'user-2',
          existingBody: '안녕하세요',
          callerSenderId: 'user-1',
          callerBody: '안녕하세요',
        ),
        isFalse,
      );
    });

    test('body 불일치 → false(손상 데이터 배제)', () {
      expect(
        isIdempotentResendMatch(
          existingSenderId: 'user-1',
          existingBody: '다른 내용',
          callerSenderId: 'user-1',
          callerBody: '안녕하세요',
        ),
        isFalse,
      );
    });
  });

  group('parseUnreadByRoomRows — chat_unread_by_room() RPC 응답 매핑(코드리뷰 patch 6)', () {
    // fetchUnreadByRoom() 자체는 실 네트워크 호출이라 이 리포 관례상 여기서 다루지 않는다
    // (wishlist_repository_test.dart 헤더와 동일 근거) — 매핑 로직만 순수 함수로 떼어 검증한다.
    test('정상 케이스 — room_id·unread가 둘 다 유효한 행만 Map으로 담긴다', () {
      final result = parseUnreadByRoomRows([
        {'room_id': 'room-1', 'unread': 3},
        {'room_id': 'room-2', 'unread': 5},
      ]);
      expect(result, {'room-1': 3, 'room-2': 5});
    });

    test('rows 자체가 List가 아니면 → 빈 Map(RPC 응답 형태 자체가 깨진 경우)', () {
      expect(parseUnreadByRoomRows(null), isEmpty);
      expect(parseUnreadByRoomRows('unexpected-string'), isEmpty);
    });

    test('각 행이 Map이 아니면 → 그 행만 건너뛴다', () {
      final result = parseUnreadByRoomRows([
        'not-a-map',
        {'room_id': 'room-1', 'unread': 2},
      ]);
      expect(result, {'room-1': 2});
    });

    test('room_id가 없거나 String이 아니면 → 그 행만 건너뛴다', () {
      final result = parseUnreadByRoomRows([
        {'unread': 2}, // room_id 없음
        {'room_id': 123, 'unread': 4}, // room_id가 숫자
        {'room_id': 'room-1', 'unread': 1},
      ]);
      expect(result, {'room-1': 1});
    });

    test('unread가 숫자로 안 읽히면 → 그 행만 건너뛴다', () {
      final result = parseUnreadByRoomRows([
        {'room_id': 'room-1', 'unread': 'not-a-number'},
        {'room_id': 'room-2', 'unread': null},
        {'room_id': 'room-3', 'unread': 7},
      ]);
      expect(result, {'room-3': 7});
    });

    test('빈 리스트 → 빈 Map', () {
      expect(parseUnreadByRoomRows(const []), isEmpty);
    });
  });

  group('flushChatMessageQueue', () {
    ChatMessage msgFor(QueuedChatMessage q) => ChatMessage(
      id: 'row-${q.clientMessageId}',
      roomId: 'room-1',
      senderId: 'me',
      body: q.body,
      createdAt: '2026-08-08T00:00:00+00:00',
      clientMessageId: q.clientMessageId,
    );

    test('전부 성공 → remaining 비어있고 sent 는 순서대로 전부 담긴다', () async {
      final queue = [
        const QueuedChatMessage(clientMessageId: 'a', body: '하나'),
        const QueuedChatMessage(clientMessageId: 'b', body: '둘'),
        const QueuedChatMessage(clientMessageId: 'c', body: '셋'),
      ];
      final calledOrder = <String>[];
      final result = await flushChatMessageQueue(queue, (msg) async {
        calledOrder.add(msg.clientMessageId);
        return SendMessageSuccess(msgFor(msg));
      });

      expect(calledOrder, ['a', 'b', 'c'], reason: '순차 await(동시 전송 없음) — 순서 보존');
      expect(result.remaining, isEmpty);
      expect(result.sent.map((m) => m.clientMessageId).toList(), ['a', 'b', 'c']);
    });

    test('중간 항목 실패 → 그 항목부터 뒤 전부 remaining, 앞쪽 성공분은 sent 에 보존', () async {
      final queue = [
        const QueuedChatMessage(clientMessageId: 'a', body: '하나'),
        const QueuedChatMessage(clientMessageId: 'b', body: '둘'),
        const QueuedChatMessage(clientMessageId: 'c', body: '셋'),
      ];
      final result = await flushChatMessageQueue(queue, (msg) async {
        if (msg.clientMessageId == 'b') {
          return const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        }
        return SendMessageSuccess(msgFor(msg));
      });

      expect(
        result.sent.map((m) => m.clientMessageId).toList(),
        ['a'],
        reason: 'b 이전(성공분)까지만 sent 에 담긴다',
      );
      expect(
        result.remaining.map((q) => q.clientMessageId).toList(),
        ['b', 'c'],
        reason: '실패한 b와 그 뒤로 아직 시도 안 한 c 가 순서 그대로 remaining에 남는다(뒤 항목을 '
            '먼저 보내지 않음 — 순서 보존, 실패 항목을 버리지 않음 — 유실 방지)',
      );
    });

    test('sendFn 이 예외를 던지면 → 그 항목부터 뒤 전부 remaining 으로 흡수(성공분은 보존)', () async {
      final queue = [
        const QueuedChatMessage(clientMessageId: 'a', body: '하나'),
        const QueuedChatMessage(clientMessageId: 'b', body: '둘'),
      ];
      final result = await flushChatMessageQueue(queue, (msg) async {
        if (msg.clientMessageId == 'b') {
          throw Exception('네트워크 단절');
        }
        return SendMessageSuccess(msgFor(msg));
      });

      expect(result.sent.map((m) => m.clientMessageId).toList(), ['a']);
      expect(
        result.remaining.map((q) => q.clientMessageId).toList(),
        ['b'],
        reason: 'sendFn 이 { error } 대신 던지는 경우도 실패와 동일하게 취급해야 이 함수 전체가 '
            'reject하지 않고 이미 성공한 sent 를 호출부에 돌려준다',
      );
    });

    test('빈 큐 → remaining/sent 둘 다 비어있고 sendFn 은 호출되지 않는다', () async {
      var calls = 0;
      final result = await flushChatMessageQueue(const [], (msg) async {
        calls++;
        return SendMessageSuccess(msgFor(msg));
      });
      expect(calls, 0);
      expect(result.remaining, isEmpty);
      expect(result.sent, isEmpty);
    });
  });

  // 2026-08-10 Epic 16 묶음 코드리뷰(verification-gap) — **멱등 재전송 경로가 통째로 미실행이었다.**
  // §12.4의 헤드라인 계약("재전송은 항상 성공하고 chat_messages엔 정확히 1행만 남는다")을
  // 구현하는 코드는 `sendMessage`의 `23505` catch 블록인데,
  //   · `chat_repository_test.dart`는 순수 판정 함수 `isIdempotentResendMatch`만 손으로 만든
  //     문자열로 검증했고("sendMessage() 자체는 실 Supabase 호출이라 여기서 다루지 않는다"),
  //   · `chat_room_screen_test.dart`의 `_FakeChatRepository.sendMessage()`는 실제 구현을 통째로
  //     덮어써서 이 블록을 절대 태우지 않는다.
  // 그래서 재조회 필터가 빠지거나 인자 순서가 뒤바뀌어도 전 스위트가 green이었다.
  // 같은 파일이 `markRoomRead`에 이미 쓰는 `SupabaseClient(httpClient:)` 기법을 그대로 쓴다.
  group('멱등 재전송(23505) 실제 경로 — 코드리뷰 2026-08-10', () {
    test('INSERT가 23505로 거절되면 그 키의 기존 행을 재조회해 성공으로 확정한다', () async {
      const roomId = 'room-1';
      const senderId = 'user-1';
      const cid = 'client-msg-1';
      final existingRow = {
        'id': 'msg-1',
        'room_id': roomId,
        'sender_id': senderId,
        'body': '안녕하세요',
        'created_at': '2026-08-10T00:00:00+00:00',
        'client_message_id': cid,
      };

      final fakeHttp = _ScriptedHttpClient([
        // 1) INSERT → UNIQUE(room_id, client_message_id) 위반
        (status: 409, body: jsonEncode({'code': '23505', 'message': 'duplicate key'})),
        // 2) 재조회 → 이미 저장돼 있던 그 행
        (status: 200, body: jsonEncode(existingRow)),
      ]);
      final client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
      addTearDown(client.dispose);
      await _signIn(client, senderId);

      final result = await ChatRepository(client: client).sendMessage(
        roomId: roomId,
        senderId: senderId,
        body: '안녕하세요',
        clientMessageId: cid,
      );

      expect(result, isA<SendMessageSuccess>(),
          reason: '§12.4: 재전송은 에러가 아니라 그 행으로 수렴한다 — 실패로 보이면 사용자는 '
              '이미 보낸 메시지를 못 보냈다고 오해한다');
      expect((result as SendMessageSuccess).message.id, 'msg-1');

      // 재조회가 **두 필터를 모두** 실었는지 본다 — client_message_id를 빠뜨리면 같은 방의
      // 엉뚱한 메시지를 자기 전송으로 오인해 표시한다.
      expect(fakeHttp.requests, hasLength(2),
          reason: 'INSERT 1회 + 재조회 1회여야 한다. 실제: ${fakeHttp.requests.map((r) => r.method).toList()}');
      final refetch = fakeHttp.requests[1];
      expect(refetch.method, 'GET');
      expect(refetch.url.queryParameters['room_id'], 'eq.$roomId');
      expect(refetch.url.queryParameters['client_message_id'], 'eq.$cid',
          reason: '멱등키 필터가 빠지면 그 방의 아무 행이나 집어올 수 있다');
    });

    test('재조회한 행이 내 것이 아니면(보낸 사람이 다름) 성공으로 위장하지 않는다', () async {
      const cid = 'client-msg-2';
      final othersRow = {
        'id': 'msg-9',
        'room_id': 'room-1',
        'sender_id': 'someone-else', // 같은 키인데 다른 사람이 보낸 행
        'body': '안녕하세요',
        'created_at': '2026-08-10T00:00:00+00:00',
        'client_message_id': cid,
      };

      final fakeHttp = _ScriptedHttpClient([
        (status: 409, body: jsonEncode({'code': '23505', 'message': 'duplicate key'})),
        (status: 200, body: jsonEncode(othersRow)),
      ]);
      final client = SupabaseClient(
        'https://example.supabase.co',
        'test-anon-key-not-real',
        httpClient: fakeHttp,
      );
      addTearDown(client.dispose);
      await _signIn(client, 'user-1');

      final result = await ChatRepository(client: client).sendMessage(
        roomId: 'room-1',
        senderId: 'user-1',
        body: '안녕하세요',
        clientMessageId: cid,
      );

      expect(result, isA<SendMessageFailure>(),
          reason: '멱등 수렴은 "같은 사람이 같은 내용을 다시 보낸 경우"에만 성립한다 — '
              '남의 행을 내 전송으로 확정하면 화면에 남의 메시지가 내 것으로 뜬다');
    });
  });
}
