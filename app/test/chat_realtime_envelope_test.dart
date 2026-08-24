// Story 16.4 코드리뷰 patch 1 — 실시간 채팅 수신이 완전히 죽어 있던 결함(P1)의 재발 방지 검사.
//
// 왜 이 파일이 필요한가: `chat_room_screen_test.dart`의 위젯테스트는 `subscribeOverride`로
// `onInsert` 콜백을 직접 캡처해 우리가 손으로 만든 Map을 넘긴다 — 그 Map의 모양(envelope 깊이)이
// 우리 짐작대로였다면, 실제 `realtime_client`가 넘기는 모양과 달라도 테스트 자신은 항상 green이다
// (테스트가 계약을 "확인"하는 게 아니라 "정의"해버린 것 — 이번 결함이 정확히 그렇게 살아남았다:
// `handleBroadcastInsert`가 `payload['record']`를 읽었는데 실제 콜백 인자는 그보다 한 단계 깊은
// `{'type':'broadcast','event':...,'payload':{'record':...}}`였다).
//
// 이 파일은 그 사각지대를 메운다 — **실제** `realtime_client` 패키지(`RealtimeClient`+
// `RealtimeChannel.onBroadcast`)를 직접 구동해, 그 라이브러리가 실제로 넘기는 envelope 모양으로
// `extractBroadcastRecord`(chat_room_screen.dart)를 검증한다. 소켓 연결은 필요 없다 —
// `socket.onConnMessage(...)`로 수신 프레임을 직접 주입하는 기법을 쓴다(realtime_client의 자체
// 테스트 `test/socket_test.dart:594-625` "decodes a legacy object frame and dispatches it when
// version is v1"과 정확히 같은 기법 — 우리 코드가 아니라 **라이브러리 자신의 테스트가 이미 증명한
// 방식**이라 신뢰할 수 있다).
//
// 이 파일이 안 보는 것: 실제 웹소켓 연결·인증·구독(subscribe) 자체 — 그건 스펙의 Manual
// checks(로컬 Supabase 2계정 실측) 몫이다. 여기서는 "라이브러리가 이 모양으로 콜백을 부르면 우리
// 파싱 함수가 record를 뽑아내는가"만 고정한다.
import 'dart:convert';

import 'package:app/features/chat/chat_room_screen.dart';
import 'package:flutter_test/flutter_test.dart';
// realtime_client는 supabase_flutter가 이미 pubspec.lock에 끌어온 전이(transitive) 의존성이다
// (app/pubspec.lock 참조) — 이 파일이 실제 라이브러리 디스패치 경로(RealtimeClient.onConnMessage)
// 를 직접 구동하는 유일한 이유로 새 패키지를 추가하지 않고 그 전이 의존성을 그대로 가져다 쓴다(A2).
// ignore: depend_on_referenced_packages
import 'package:realtime_client/realtime_client.dart';

void main() {
  group('extractBroadcastRecord — 실제 realtime_client 디스패치 경로로 envelope 깊이를 고정', () {
    test(
        '실제 RealtimeClient.onConnMessage(legacy v1 프레임) → onBroadcast 콜백 → extractBroadcastRecord가 '
        'record를 정확히 뽑아낸다', () {
      final socket = RealtimeClient(
        'wss://example.supabase.co',
        version: RealtimeProtocolVersion.v1,
      );
      final channel = socket.channel('chat:room:room-1');

      Map<String, dynamic>? received;
      channel.onBroadcast(
        event: 'INSERT',
        callback: (payload) => received = payload,
      );

      // realtime_client 자신의 test/socket_test.dart:594-625와 동일한 기법 — 실제 웹소켓 연결 없이
      // 서버가 보내는 프레임 하나를 직접 주입해 디코드~디스패치 경로 전체를 실제로 태운다.
      socket.onConnMessage(json.encode({
        'topic': 'realtime:chat:room:room-1',
        'event': 'broadcast',
        'payload': {
          'type': 'broadcast',
          'event': 'INSERT',
          'payload': {
            'record': {
              'id': 'm1',
              'room_id': 'room-1',
              'sender_id': 'seller-1',
              'body': '안녕하세요',
              'created_at': '2026-08-08T00:00:00+00:00',
            },
          },
        },
        'ref': null,
      }));

      expect(
        received,
        isNotNull,
        reason: 'onBroadcast 콜백 자체가 안 불렸다면 이 검사는 애초에 무의미하다',
      );
      final record = extractBroadcastRecord(received!);
      expect(
        record,
        isA<Map>(),
        reason: '실제 라이브러리가 넘기는 envelope에서 record를 뽑아내야 한다',
      );
      expect((record as Map)['id'], 'm1');
      expect(record['body'], '안녕하세요');
    });

    test('실제 콜백 인자를 한 단계 얕게(payload[\'record\'])읽으면 항상 null이다 — 이 결함이 실제로 있었다는 증거', () {
      final socket = RealtimeClient(
        'wss://example.supabase.co',
        version: RealtimeProtocolVersion.v1,
      );
      final channel = socket.channel('chat:room:room-1');

      Map<String, dynamic>? received;
      channel.onBroadcast(event: 'INSERT', callback: (payload) => received = payload);

      socket.onConnMessage(json.encode({
        'topic': 'realtime:chat:room:room-1',
        'event': 'broadcast',
        'payload': {
          'type': 'broadcast',
          'event': 'INSERT',
          'payload': {
            'record': {'id': 'm1'},
          },
        },
        'ref': null,
      }));

      expect(received, isNotNull);
      // 결함이 있던 원래 코드가 한 일 — payload['record']를 직접 읽으면 항상 null(실제로는
      // payload['payload']['record']에 있으므로). extractBroadcastRecord는 이 함정을 피한다.
      expect(
        received!['record'],
        isNull,
        reason: '얕은 읽기는 항상 null을 준다 — 이게 P1 결함이 조용히 살아남은 이유다',
      );
      expect(extractBroadcastRecord(received!), isNotNull, reason: '올바른 깊이로 읽으면 찾아낸다');
    });

    test('안쪽 payload가 없거나 Map이 아니면 null(방어적) — 던지지 않는다', () {
      expect(extractBroadcastRecord({'type': 'broadcast', 'event': 'INSERT'}), isNull);
      expect(
        extractBroadcastRecord({'type': 'broadcast', 'event': 'INSERT', 'payload': 'not-a-map'}),
        isNull,
      );
    });
  });
}
