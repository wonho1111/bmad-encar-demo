// Story 16.4 채팅 레포지토리 순수 함수 단위테스트 — roomTopic 형식·reuseFailedKey 4분기·
// flushChatMessageQueue(전부성공/부분실패시 순서·remaining 보존/예외를 실패로 흡수)·
// isIdempotentResendMatch(멱등 재전송 23505 후 재조회한 기존 행이 내 전송인지 판정, 3분기)·
// parseUnreadByRoomRows(chat_unread_by_room() RPC 응답 매핑, 코드리뷰 patch 6).
// web messages.test.ts(reuseFailedKey·flushMessageQueue)와 동일한 시나리오를 Dart로 미러링한다
// (docs/conventions.md §12.4·§12.5).
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
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
}
