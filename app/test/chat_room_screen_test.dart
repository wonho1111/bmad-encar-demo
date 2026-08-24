// Story 16.4 채팅방 화면 위젯테스트 — 초기 로드·전송·pending 버블·참여자일 때만 markRoomRead
// 호출을 가짜 레포(_FakeChatRepository extends ChatRepository, app_router_test.dart의
// _FakeChatRepo 패턴 재사용)로 검증하고, 상태-콜백 시뮬레이션(subscribeOverride 가 캡처한
// onInsert/onStatus 를 직접 호출)으로 배너·disabled·큐 flush 반응을 실제 소켓 없이 검증한다.
//
// 이 파일이 안 보는 것: 실제 Realtime 서버가 그 토픽으로 방송을 내보내고 구독이 붙는지(런타임
// 동작) — 그건 스펙의 Manual checks(로컬 Supabase 2계정 실측) 몫이다. 여기서는 "상태 전이가
// 오면 화면이 무엇을 하는가"만 상태 콜백을 직접 호출해 고정한다.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
// StateProvider는 riverpod 3에서 "legacy" API로 분리돼 기본 barrel엔 없다(app_router_test.dart와
// 동일 이유) — 세션 중 사용자가 null로 바뀌는(P4 시나리오) mutable 테스트 상태로만 쓴다.
import 'package:flutter_riverpod/legacy.dart' show StateProvider;
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_providers.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:app/features/chat/chat_room_screen.dart';

User _fakeUser(String id) => User(
  id: id,
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'test@example.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

const _buyerId = '00000000-0000-0000-0000-000000000b01';
const _sellerId = '00000000-0000-0000-0000-000000000s01';
const _strangerId = '00000000-0000-0000-0000-0000000005ff';

ChatMessage _msg(String id, String senderId, String body, {String? clientMessageId}) => ChatMessage(
  id: id,
  roomId: 'room-1',
  senderId: senderId,
  body: body,
  createdAt: '2026-08-08T00:00:00+00:00',
  clientMessageId: clientMessageId,
);

/// 가짜 레포 — app_router_test.dart의 `_FakeChatRepo`(fetchMessages만 고정)를 이 화면 전용으로
/// 확장한다. 호출 기록(sendCalls·markRoomReadCalls·fetchMessagesCursors)을 보관해 테스트가
/// "무엇이, 몇 번, 어떤 인자로 불렸는가"를 단언할 수 있게 한다.
class _FakeChatRepository extends ChatRepository {
  _FakeChatRepository({
    this.initialMessages = const [],
    this.room,
    this.sendMessageImpl,
    this.fetchMessagesShouldFail,
  });

  List<ChatMessage> initialMessages;
  ChatRoomSummary? room;
  Future<SendMessageResult> Function(String body, String clientMessageId)? sendMessageImpl;

  /// 특정 호출(그 호출의 커서 값 기준)에서 fetchMessages가 실패하게 만드는 훅(코드리뷰 patch 9) —
  /// 갭보정 실패→복구 시나리오(§12.5 "자기가 세운 안내만 거둔다": 갭보정 실패로 세운 안내는
  /// 그 다음 갭보정이 성공해야만 지워진다)를 테스트가 직접 조립할 수 있게 한다. null(기본값)이면
  /// 항상 성공하는 기존 동작 그대로다.
  bool Function(String? cursor)? fetchMessagesShouldFail;

  final List<String> markRoomReadCalls = [];
  final List<Map<String, String>> sendCalls = [];
  final List<String?> fetchMessagesCursors = [];
  int fetchMessagesCallCount = 0;

  @override
  Future<List<ChatMessage>> fetchMessages(String roomId, {String? atOrAfterCreatedAt}) async {
    fetchMessagesCallCount++;
    fetchMessagesCursors.add(atOrAfterCreatedAt);
    if (fetchMessagesShouldFail?.call(atOrAfterCreatedAt) ?? false) {
      throw Exception('fake fetchMessages 실패(테스트 훅)');
    }
    // 최초 1회(커서 없음)만 initialMessages 를 돌려준다 — 이후(최초 SUBSCRIBED 보정·갭보정)
    // 호출은 "새 메시지 없음"으로 비워서, 테스트가 그 후속 mergeIncoming으로 화면이 흔들리지
    // 않는 것을 전제로 단언할 수 있게 한다(필요한 테스트는 sendMessageImpl/직접 호출로 새
    // 메시지를 만들어 mergeIncoming을 별도로 검증한다).
    if (atOrAfterCreatedAt == null && fetchMessagesCallCount == 1) return initialMessages;
    return const [];
  }

  @override
  Future<ChatRoomSummary?> fetchRoom(String roomId) async => room;

  @override
  Future<void> markRoomRead(String roomId) async {
    markRoomReadCalls.add(roomId);
  }

  @override
  Future<SendMessageResult> sendMessage({
    required String roomId,
    required String senderId,
    required String body,
    required String clientMessageId,
  }) async {
    sendCalls.add({'body': body, 'clientMessageId': clientMessageId});
    if (sendMessageImpl != null) return sendMessageImpl!(body, clientMessageId);
    return SendMessageSuccess(_msg('sent-${sendCalls.length}', senderId, body, clientMessageId: clientMessageId));
  }
}

/// subscribeOverride 가 캡처한 콜백 — 테스트가 실제 소켓 없이 상태 전이를 직접 호출한다.
class _CapturedRealtime {
  void Function(Map<String, dynamic> payload)? onInsert;
  void Function(RealtimeSubscribeStatus status, Object? error)? onStatus;
}

Widget _harness({
  required User user,
  required ChatRepository repo,
  _CapturedRealtime? captured,
}) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWithValue(user),
      chatRepositoryProvider.overrideWithValue(repo),
    ],
    child: MaterialApp(
      home: ChatRoomScreen(
        roomId: 'room-1',
        subscribeOverride: captured == null
            ? null
            : ({required roomId, required onInsert, required onStatus}) {
                captured.onInsert = onInsert;
                captured.onStatus = onStatus;
                return Object(); // 실제 채널이 필요 없는 불투명 핸들.
              },
        unsubscribeOverride: captured == null ? null : (_) {},
      ),
    ),
  );
}

/// 세션 중 사용자가 null로 바뀌는(예: 로그아웃) 시나리오 전용 harness — `_myId`가 `ref.read`로
/// 즉시 읽히므로(§12.4 Design Notes — Dart는 ref 미러링이 필요 없다), 이 provider의 state를
/// 바꾸면 다음 `_flushQueue()` 호출부터 바로 반영된다(코드리뷰 patch 4 테스트용).
final _mutableUserProvider = StateProvider<User?>((ref) => null);

Widget _harnessMutableUser({
  required User? initialUser,
  required ChatRepository repo,
  required _CapturedRealtime captured,
}) {
  return ProviderScope(
    overrides: [
      _mutableUserProvider.overrideWith((ref) => initialUser),
      currentUserProvider.overrideWith((ref) => ref.watch(_mutableUserProvider)),
      chatRepositoryProvider.overrideWithValue(repo),
    ],
    child: MaterialApp(
      home: ChatRoomScreen(
        roomId: 'room-1',
        subscribeOverride: ({required roomId, required onInsert, required onStatus}) {
          captured.onInsert = onInsert;
          captured.onStatus = onStatus;
          return Object();
        },
        unsubscribeOverride: (_) {},
      ),
    ),
  );
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  group('초기 로드', () {
    testWidgets('메시지가 있으면 시간순으로 렌더된다', (tester) async {
      final repo = _FakeChatRepository(
        initialMessages: [_msg('m1', _sellerId, '안녕하세요'), _msg('m2', _buyerId, '네 안녕하세요')],
      );
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('msg_m1')), findsOneWidget);
      expect(find.byKey(const Key('msg_m2')), findsOneWidget);
      expect(find.text('안녕하세요'), findsOneWidget);
    });

    testWidgets('메시지가 없으면 빈 상태 문구가 뜬다', (tester) async {
      final repo = _FakeChatRepository();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chat_empty')), findsOneWidget);
    });
  });

  group('전송·pending 버블', () {
    testWidgets('전송 시작 시 즉시 pending 버블이 뜨고, 확정되면 실제 메시지로 바뀐다', (tester) async {
      final gate = Completer<SendMessageResult>();
      final repo = _FakeChatRepository(
        sendMessageImpl: (body, clientMessageId) => gate.future,
      );
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('chat_input')), '문의드립니다');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump(); // pending 버블은 응답을 기다리지 않고 즉시 뜬다.

      expect(repo.sendCalls.length, 1);
      expect(repo.sendCalls.single['body'], '문의드립니다');
      final clientMessageId = repo.sendCalls.single['clientMessageId']!;
      expect(find.byKey(Key('pending_$clientMessageId')), findsOneWidget);

      gate.complete(
        SendMessageSuccess(_msg('saved-1', _buyerId, '문의드립니다', clientMessageId: clientMessageId)),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(Key('pending_$clientMessageId')), findsNothing);
      expect(find.byKey(const Key('msg_saved-1')), findsOneWidget);
    });

    testWidgets('전송 실패 시 한국어 에러 + 입력 복원(입력창이 비어있을 때만)', (tester) async {
      final repo = _FakeChatRepository(
        sendMessageImpl: (body, clientMessageId) async =>
            const SendMessageFailure('메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.'),
      );
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('chat_input')), '실패할 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chat_error')), findsOneWidget);
      expect(find.text('실패할 메시지'), findsOneWidget, reason: '입력창이 비어있었으므로 복원된다');

      // 코드리뷰 patch 13 — `_lastFailed = FailedSend(...)` 대입(화면 배선)이 실제로 쓰이는지는
      // 이때까지 어떤 테스트도 안 봤다(순수함수 reuseFailedKey 자체는 chat_repository_test.dart가
      // 이미 본다). 이 대입들을 지워도 그 단위테스트는 여전히 green이었다 — 실제 결과는 재시도가
      // 항상 새 키를 만들어 DB의 UNIQUE(room_id, client_message_id) 가드를 그냥 우회하고, 같은
      // 메시지가 중복 행으로 남는 것이다. 같은 본문으로 다시 보내면 같은 키가 재사용되는지 여기서
      // 직접 확인한다.
      final firstClientMessageId = repo.sendCalls.single['clientMessageId'];
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pumpAndSettle();

      expect(repo.sendCalls.length, 2);
      expect(
        repo.sendCalls[1]['clientMessageId'],
        firstClientMessageId,
        reason: '같은 본문으로 재시도하면 직전 실패의 client_message_id를 재사용해야 한다(§12.4)',
      );

      // 본문이 다르면 옛 키를 재사용하면 안 된다(엉뚱한 메시지가 옛 메시지로 오인된다).
      await tester.enterText(find.byKey(const Key('chat_input')), '다른 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pumpAndSettle();

      expect(repo.sendCalls.length, 3);
      expect(
        repo.sendCalls[2]['clientMessageId'],
        isNot(firstClientMessageId),
        reason: '본문이 다르면 새 client_message_id를 만들어야 한다',
      );
    });
  });

  group('markRoomRead — 당사자일 때만 1회 호출', () {
    ChatRoomSummary roomOf({required String buyerId, required String sellerId}) => ChatRoomSummary(
      id: 'room-1',
      listingId: 'listing-1',
      buyerId: buyerId,
      sellerId: sellerId,
    );

    testWidgets('내가 buyer 인 방 → markRoomRead 가 1회 호출된다', (tester) async {
      final repo = _FakeChatRepository(room: roomOf(buyerId: _buyerId, sellerId: _sellerId));
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      expect(repo.markRoomReadCalls, ['room-1']);
    });

    testWidgets('내가 seller 인 방 → markRoomRead 가 1회 호출된다', (tester) async {
      final repo = _FakeChatRepository(room: roomOf(buyerId: _buyerId, sellerId: _sellerId));
      await tester.pumpWidget(_harness(user: _fakeUser(_sellerId), repo: repo));
      await tester.pumpAndSettle();

      expect(repo.markRoomReadCalls, ['room-1']);
    });

    testWidgets('당사자가 아니면(제3자) → markRoomRead 가 호출되지 않는다', (tester) async {
      // "방 조회 성공"과 "당사자"는 다른 것(§12.6) — admin RLS가 OR로 합쳐져 방이 조회는 돼도
      // buyer/seller 직접 대조로 걸러야 한다.
      final repo = _FakeChatRepository(room: roomOf(buyerId: _buyerId, sellerId: _sellerId));
      await tester.pumpWidget(_harness(user: _fakeUser(_strangerId), repo: repo));
      await tester.pumpAndSettle();

      expect(repo.markRoomReadCalls, isEmpty);
    });

    testWidgets('방 자체가 없으면(조회 null) → markRoomRead 가 호출되지 않는다', (tester) async {
      final repo = _FakeChatRepository(room: null);
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      expect(repo.markRoomReadCalls, isEmpty);
    });
  });

  group('subscribeOverride 없이 실 세션도 없으면 안내를 남긴다(코드리뷰 patch 5)', () {
    testWidgets('구독을 시도조차 못 하면 조용히 죽지 않고 chat_realtime_error 안내가 뜬다', (
      tester,
    ) async {
      final repo = _FakeChatRepository();
      // captured를 안 주면 _harness가 subscribeOverride를 null로 둔다 — 이 테스트 환경엔 실
      // Supabase 세션이 없으므로(setUpAll이 로그인은 하지 않는다) `_subscribeRealtime()`의
      // "subscribeFn == null && currentSession == null" 분기를 그대로 태운다. 폴링이 없는 이
      // 화면이 아무 안내 없이 "겉보기엔 멀쩡한데 평생 아무것도 못 받는" 상태가 되면 안 된다.
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('chat_realtime_error')),
        findsOneWidget,
        reason: '채널도 없고 안내도 없으면 사용자는 방이 정상인 줄 알고 계속 기다리게 된다',
      );
    });
  });

  group('subscribed 도달 시 _realtimeError를 무조건 지운다(코드리뷰 patch 6)', () {
    testWidgets(
        'closed로 빨간 안내가 세워진 뒤 channelError→subscribed(재연결)로 와도 그 안내가 지워진다', (
      tester,
    ) async {
      final captured = _CapturedRealtime();
      final repo = _FakeChatRepository();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      // closed 분기가 빨간 _realtimeError를 세운다(12.3 이래의 기존 분기).
      captured.onStatus!(RealtimeSubscribeStatus.closed, null);
      await tester.pump();
      expect(find.byKey(const Key('chat_realtime_error')), findsOneWidget);

      // 끊겼다(channelError, _everDropped=true) → 재연결(subscribed)까지 온다. 예전 코드는
      // subscribed의 "재연결(_everDropped)" 분기에서 _realtimeError를 안 지웠으므로, 빨간
      // "실시간 연결이 끊겼습니다" 문구가 초록 "다시 연결됐어요" 배너 위에 영구히 남았다.
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('chat_realtime_error')),
        findsNothing,
        reason: 'subscribed에 닿았다는 것 자체가 지금은 연결돼 있다는 뜻이므로, 재연결 분기든 '
            '최초 구독 분기든 상관없이 지워야 한다',
      );
      expect(
        find.byKey(const Key('chat_reconnected_banner')),
        findsOneWidget,
        reason: '재연결 배너도 정상적으로 함께 떠야 한다(이 패치가 그 배선을 건드리지 않았다는 확인)',
      );
    });
  });

  group('상태-콜백 시뮬레이션 — 배너·disabled·큐 flush', () {
    testWidgets('channelError → 끊김 배너가 뜨고 입력·전송은 잠기지 않는다', (tester) async {
      final captured = _CapturedRealtime();
      final repo = _FakeChatRepository();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      captured.onStatus!(RealtimeSubscribeStatus.channelError, 'boom');
      await tester.pump();

      expect(find.byKey(const Key('chat_disconnected_banner')), findsOneWidget);
      final input = tester.widget<TextField>(find.byKey(const Key('chat_input')));
      expect(input.enabled, isTrue, reason: '끊긴 동안에도 입력은 잠기지 않는다(비차단, FR42)');
      final button = tester.widget<FilledButton>(find.byKey(const Key('chat_send')));
      expect(button.onPressed, isNotNull, reason: '전송 버튼도 끊긴 동안 잠기지 않는다');
    });

    testWidgets('끊긴 동안 제출 → 네트워크 호출 없이 즉시 pending 큐에 적재된다', (tester) async {
      final captured = _CapturedRealtime();
      final repo = _FakeChatRepository();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();

      await tester.enterText(find.byKey(const Key('chat_input')), '끊긴 동안 보낸 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();

      expect(repo.sendCalls, isEmpty, reason: '끊긴 동안은 sendMessage 네트워크 호출을 시도하지 않는다');
      expect(find.text('끊긴 동안 보낸 메시지'), findsOneWidget, reason: 'pending 버블로 즉시 보인다');
    });

    testWidgets('재연결(subscribed, 이전에 끊긴 적 있음) → 초록 배너 + 큐 flush + 갭보정이 함께 돈다', (
      tester,
    ) async {
      final captured = _CapturedRealtime();
      // 초기 메시지를 1건 심어 갭보정 커서(마지막으로 반영한 메시지의 created_at)가 실제로
      // 채워지게 한다 — 커서가 없으면(아직 메시지가 없던 방) 갭보정은 전체 재조회로 자연스럽게
      // 대체돼(§12.5) atOrAfterCreatedAt=null로 호출된다(그 경로 자체는 정상 동작).
      final repo = _FakeChatRepository(initialMessages: [_msg('m0', _sellerId, '초기 메시지')]);
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      // 끊김 → 오프라인 큐잉.
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), '오프라인 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();
      expect(repo.sendCalls, isEmpty);

      // 재연결 — 순차 flush(§12.5)와 커서 갭보정(§12.5 백스톱)이 항상 함께 돈다.
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chat_reconnected_banner')), findsOneWidget);
      expect(repo.sendCalls.length, 1, reason: '큐잉된 항목이 재연결 시 flush된다');
      expect(repo.sendCalls.single['body'], '오프라인 메시지');
      expect(
        repo.fetchMessagesCursors.any((c) => c != null),
        isTrue,
        reason: '갭보정이 커서(atOrAfterCreatedAt)를 실어 fetchMessages를 다시 호출한다',
      );

      // 재연결 배너는 3초 후 자동 소멸(§12.5 Always 예시값).
      await tester.pump(const Duration(seconds: 3));
      expect(find.byKey(const Key('chat_reconnected_banner')), findsNothing);
    });

    testWidgets('브로드캐스트 INSERT 수신 → 폴링 없이 즉시 목록에 반영된다', (tester) async {
      final captured = _CapturedRealtime();
      final repo = _FakeChatRepository();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      // 실제 realtime_client onBroadcast 콜백은 innerPayload가 아니라 전체 broadcast envelope를
      // 넘긴다(코드리뷰 patch 1, extractBroadcastRecord 주석 참조) — 위젯테스트도 그 실제 모양을
      // 그대로 흉내 낸다(테스트가 결함을 가리지 않도록).
      captured.onInsert!({
        'type': 'broadcast',
        'event': 'INSERT',
        'payload': {
          'record': {
            'id': 'broadcast-1',
            'room_id': 'room-1',
            'sender_id': _sellerId,
            'body': '실시간으로 온 메시지',
            'created_at': '2026-08-08T00:00:01+00:00',
          },
        },
      });
      await tester.pump();

      expect(find.byKey(const Key('msg_broadcast-1')), findsOneWidget);
      expect(find.text('실시간으로 온 메시지'), findsOneWidget);
    });

    testWidgets(
        'brodcast 에코로 pending이 지워지면 큐 미전송 안내(queueStuckNotice)도 즉시 다시 계산된다'
        '(코드리뷰 patch 4 — flush 안에서만 갱신되던 안내가 브로드캐스트 경로에서 안 갱신되던 문제)', (
      tester,
    ) async {
      // 시나리오: flush가 두 건 중 한 건만 실패시켜(sendMessageImpl) "1건 못 보냄" 안내가 뜬다.
      // 그 뒤 그 실패한 건의 브로드캐스트 에코가 뒤늦게 도착한다(응답만 유실되고 서버엔 저장된
      // 흔한 케이스) — handleBroadcastInsert가 그 항목을 pending에서 지우면서 안내도 같이
      // 사라져야 한다(안 지우면 이미 도착한 메시지를 두고 "아직 못 보냄"이라는 거짓 안내가 남는다).
      final captured = _CapturedRealtime();
      var shouldFailB = true;
      final repo = _FakeChatRepository(
        sendMessageImpl: (body, clientMessageId) async {
          if (body == 'B' && shouldFailB) {
            return const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
          }
          return SendMessageSuccess(_msg('sent-$body', _buyerId, body, clientMessageId: clientMessageId));
        },
      );
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), 'A');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), 'B');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();

      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chat_queue_stuck_notice')), findsOneWidget);
      final clientMessageIdB = repo.sendCalls.firstWhere((c) => c['body'] == 'B')['clientMessageId']!;

      // 이제 그 실패했던 메시지의 브로드캐스트 에코가 뒤늦게 도착한다(서버엔 이미 저장돼 있었다).
      // 실제 envelope 모양(전체 broadcast envelope, innerPayload가 아니다)을 그대로 흉내 낸다.
      captured.onInsert!({
        'type': 'broadcast',
        'event': 'INSERT',
        'payload': {
          'record': {
            'id': 'broadcast-b',
            'room_id': 'room-1',
            'sender_id': _buyerId,
            'body': 'B',
            'created_at': '2026-08-08T00:00:02+00:00',
            'client_message_id': clientMessageIdB,
          },
        },
      });
      await tester.pump();

      expect(
        find.byKey(const Key('chat_queue_stuck_notice')),
        findsNothing,
        reason:
            '브로드캐스트 에코로 마지막 pending 항목이 확인됐으니 "못 보냄" 안내는 즉시 사라져야 '
            '한다 — flush를 다시 돌려야만 지워진다면 그 사이 화면이 거짓 정보를 보여준다',
      );
    });
  });

  group('오프라인 큐 일부 전송 실패 안내(코드리뷰 patch 8) — flush 미전송 안내 + "다시 보내기"', () {
    testWidgets('2건 중 1건만 실패 → 정확한 남은 건수가 뜨고, "다시 보내기"를 누르면 다시 flush를 시도한다', (
      tester,
    ) async {
      final captured = _CapturedRealtime();
      final repo = _FakeChatRepository(
        // 'B'는 항상 실패시킨다 — flush가 몇 번 재시도되든 계속 remaining에 남아, 재시도 버튼이
        // 실제로 sendFn을 다시 부르는지(sendCalls 증가)를 확인할 수 있게 한다.
        sendMessageImpl: (body, clientMessageId) async {
          if (body == 'B') {
            return const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
          }
          return SendMessageSuccess(_msg('sent-$body', _buyerId, body, clientMessageId: clientMessageId));
        },
      );
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      // 끊긴 동안 두 건을 큐에 쌓는다.
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), 'A');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), 'B');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();

      // 재연결 → flush가 순서대로 돈다: A는 성공, B는 실패 → remaining 1건.
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('chat_queue_stuck_notice')), findsOneWidget);
      final noticeWidget = tester.widget<Text>(find.byKey(const Key('chat_queue_stuck_notice')));
      expect(
        noticeWidget.data,
        contains('메시지 1건을 아직 보내지 못했습니다.'),
        reason: '2건 중 A는 성공했으니 남은 건수는 정확히 1건이어야 한다',
      );
      final sendCallsAfterFlush = repo.sendCalls.length;
      expect(sendCallsAfterFlush, 2, reason: 'A·B 둘 다 시도됐어야 한다(A 성공·B 실패)');

      expect(find.byKey(const Key('chat_retry_flush')), findsOneWidget);
      await tester.tap(find.byKey(const Key('chat_retry_flush')));
      await tester.pumpAndSettle();

      expect(
        repo.sendCalls.length,
        greaterThan(sendCallsAfterFlush),
        reason: '"다시 보내기" 버튼이 실제로 flush를 다시 시도해야 한다(남은 B만 재시도)',
      );
      expect(
        repo.sendCalls.last['body'],
        'B',
        reason: '재시도는 아직 못 보낸 B만 다시 시도한다(A는 이미 큐에서 빠졌다)',
      );
      expect(
        find.byKey(const Key('chat_queue_stuck_notice')),
        findsOneWidget,
        reason: 'B가 여전히 실패하므로 안내는 그대로 남아 있어야 한다',
      );
    });
  });

  group('갭보정 실패→복구(코드리뷰 patch 9) — §12.5 "자기가 세운 안내만 거둔다"', () {
    testWidgets(
        '재연결 → 갭보정 실패로 chat_load_error가 뜸 → 다음 재연결 → 갭보정 성공으로 사라짐', (
      tester,
    ) async {
      var gapfillCallsWithCursor = 0;
      final repo = _FakeChatRepository(
        initialMessages: [_msg('m0', _sellerId, '초기 메시지')],
        fetchMessagesShouldFail: (cursor) {
          // 초기 로드·최초 SUBSCRIBED 보정 로드는 커서가 없다(atOrAfterCreatedAt == null) —
          // 이 테스트가 보려는 것은 갭보정(커서 있는 호출) 경로이므로 그쪽만 건드린다.
          if (cursor == null) return false;
          gapfillCallsWithCursor++;
          return gapfillCallsWithCursor == 1; // 첫 번째 갭보정 호출만 실패시킨다.
        },
      );
      final captured = _CapturedRealtime();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      // 첫 재연결 — 갭보정이 실패한다(위 훅의 1번째 커서 호출).
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('chat_load_error')),
        findsOneWidget,
        reason: '갭보정 실패는 "새로고침 전까지 유지"되는 chat_load_error를 세워야 한다',
      );

      // 두 번째 재연결 — 이번엔 갭보정이 성공한다(훅의 2번째 커서 호출).
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('chat_load_error')),
        findsNothing,
        reason:
            '자기가 세운 안내만 거둔다(§12.5) — 갭보정 실패로 세운 안내는 그 다음 갭보정이 '
            '성공해야 지워진다. 다른 무관한 성공(예: flush)으로는 안 지워져야 하고, 실제로 '
            '그 다음 갭보정이 성공했으니 지금은 지워져야 한다',
      );
    });
  });

  group('온라인 전송 응답 대기 중 끊김 → 실패해도 pending을 지우지 않고 큐로 넘긴다(코드리뷰 patch 3)', () {
    testWidgets(
        '전송 응답을 기다리는 동안 channelError → 뒤늦게 실패 응답 → pending이 그대로 남고, '
        '재연결 시 같은 clientMessageId로 재시도돼 성공한다', (tester) async {
      final gate = Completer<SendMessageResult>();
      var callCount = 0;
      final repo = _FakeChatRepository(
        sendMessageImpl: (body, clientMessageId) {
          callCount++;
          // 1번째 호출(온라인 경로) — 끊기기 전에 이미 나간 요청이라 gate가 풀릴 때까지 대기.
          if (callCount == 1) return gate.future;
          // 2번째 호출(재연결 flush) — 이번엔 성공.
          return Future.value(
            SendMessageSuccess(_msg('flushed-1', _buyerId, body, clientMessageId: clientMessageId)),
          );
        },
      );
      final captured = _CapturedRealtime();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('chat_input')), '전송 중 끊긴 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump(); // pending 버블은 응답을 기다리지 않고 즉시 뜬다.

      expect(repo.sendCalls.length, 1);
      final clientMessageId = repo.sendCalls.single['clientMessageId']!;
      expect(find.byKey(Key('pending_$clientMessageId')), findsOneWidget);

      // 응답을 기다리는 도중 연결이 끊긴다 — §12.5 Always: 끊긴 동안에도 입력·전송은 잠기지
      // 않는다(연타 가드는 온라인 경로 전용). 이 순서(전송 → 응답 대기 중 끊김)가 바로 이
      // 결함이 실제로 일어나는 자리다.
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();

      // 뒤늦게 실패 응답이 도착한다(예: 요청은 이미 나갔는데 응답 왕복 중 끊긴 경우).
      gate.complete(const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'));
      await tester.pumpAndSettle();

      expect(
        find.byKey(Key('pending_$clientMessageId')),
        findsOneWidget,
        reason:
            '끊긴 채로 실패했으니 pending을 지우면 안 된다 — 지우고 아무 데도 안 남기면 사용자가 '
            '화면에서 본 메시지가 조용히 사라진다(재큐잉 없이 드롭됨)',
      );
      expect(
        find.byKey(const Key('chat_error')),
        findsNothing,
        reason: '끊긴 채로 실패한 건 "에러"가 아니라 "다음 재연결을 기다리는 정상 큐잉 상태"다',
      );

      // 재연결 — flush가 같은 clientMessageId로 재시도한다.
      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(callCount, 2, reason: '재연결 flush가 실제로 재시도해야 한다');
      expect(
        repo.sendCalls.last['clientMessageId'],
        clientMessageId,
        reason: '새 키를 만들지 않고 기존 clientMessageId를 재사용해야 한다(§12.5 — 새 키면 '
            'UNIQUE(room_id, client_message_id) 가드를 우회해 중복 행이 생길 수 있다)',
      );
      expect(find.byKey(Key('pending_$clientMessageId')), findsNothing, reason: '재시도가 성공해 확정됐다');
      expect(find.byKey(const Key('msg_flushed-1')), findsOneWidget);
    });

    testWidgets('입력창이 비어있지 않아도(다음 메시지를 타이핑 중이어도) 그 글이 안 사라진다', (tester) async {
      // §12.5 후속 리뷰 정정("입력창이 비어있을 때만 복원")을 이 실패 경로에서도 지킨다는
      // 것을 직접 확인한다 — 끊긴 채 실패한 온라인 전송이 입력창을 건드리면(옛 본문을 억지로
      // 채우면) 사용자가 그 사이 입력해 둔 다음 메시지가 사라진다.
      final gate = Completer<SendMessageResult>();
      final repo = _FakeChatRepository(sendMessageImpl: (body, clientMessageId) => gate.future);
      final captured = _CapturedRealtime();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured));
      await tester.pumpAndSettle();

      await tester.enterText(find.byKey(const Key('chat_input')), '첫 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();

      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();

      // 끊긴 동안엔 입력창이 잠기지 않으므로 사용자가 다음 글을 타이핑해 둔다.
      await tester.enterText(find.byKey(const Key('chat_input')), '타이핑 중인 다음 메시지');
      await tester.pump();

      gate.complete(const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'));
      await tester.pumpAndSettle();

      expect(
        find.text('타이핑 중인 다음 메시지'),
        findsOneWidget,
        reason: '입력창이 비어있지 않았으므로 실패한 첫 메시지의 본문으로 덮어써지면 안 된다',
      );
    });
  });

  group('_flushQueue — myId == null이면 bail-out한다(코드리뷰 patch 4)', () {
    // `_send()`는 myId == null이면 애초에 시도조차 하지 않는데, `_flushQueue()`는 같은 전제를
    // 공유하지 않고 `senderId: _myId ?? ''`로 빈 문자열을 실어 보냈다 — 두 경로가 같은 전제를
    // 다르게 다루면, RLS가 빈 sender_id를 거부하는 게 일반 네트워크 오류처럼 보인다. 이 테스트는
    // 재연결 시점에 세션이 이미 없는(로그아웃된) 상태를 만들어 flush가 네트워크를 아예 안 타고
    // 큐를 그대로 남기는지 확인한다.
    testWidgets('재연결 시점에 myId가 null이면 sendMessage를 호출하지 않고 큐를 그대로 남긴다', (
      tester,
    ) async {
      final repo = _FakeChatRepository();
      final captured = _CapturedRealtime();
      await tester.pumpWidget(
        _harnessMutableUser(initialUser: _fakeUser(_buyerId), repo: repo, captured: captured),
      );
      await tester.pumpAndSettle();

      // 끊긴 동안 큐에 적재.
      captured.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), '세션 없이 재연결됨');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();
      expect(repo.sendCalls, isEmpty);

      // 재연결 직전 세션이 사라진다(예: 다른 탭에서 로그아웃).
      final element = tester.element(find.byType(ChatRoomScreen));
      ProviderScope.containerOf(element).read(_mutableUserProvider.notifier).state = null;

      captured.onStatus!(RealtimeSubscribeStatus.subscribed, null);
      await tester.pumpAndSettle();

      expect(
        repo.sendCalls,
        isEmpty,
        reason: 'myId가 없으면 네트워크를 아예 타면 안 된다(빈 sender_id로 나가면 RLS가 일반 '
            '오류처럼 거부한다) — _send()와 같은 전제를 공유해야 한다',
      );
      expect(
        find.byKey(const Key('chat_queue_stuck_notice')),
        findsOneWidget,
        reason: '큐가 안 비워졌으니 기존 "일부 실패" 안내를 그대로 재사용해 사용자에게 알려야 한다',
      );
      expect(
        find.text('세션 없이 재연결됨'),
        findsOneWidget,
        reason: 'pending 버블이 그대로 남아 있어야 한다(드롭되지 않음)',
      );
    });
  });

  group('방 이탈 → 큐 유실(§12.5 Never — 오프라인 큐는 State 필드일 뿐, 어디에도 영속하지 않는다)', () {
    testWidgets('끊긴 채 큐에 항목을 남기고 방을 나갔다 다시 들어오면 그 항목은 사라져 있다', (
      tester,
    ) async {
      final repo = _FakeChatRepository();

      final captured1 = _CapturedRealtime();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured1));
      await tester.pumpAndSettle();

      // 끊긴 채 제출 → 네트워크 호출 없이 로컬 큐(= State 필드)에만 쌓인다(위 그룹과 동일 전제).
      captured1.onStatus!(RealtimeSubscribeStatus.channelError, null);
      await tester.pump();
      await tester.enterText(find.byKey(const Key('chat_input')), '끊긴 채 두고 나간 메시지');
      await tester.tap(find.byKey(const Key('chat_send')));
      await tester.pump();

      expect(repo.sendCalls, isEmpty, reason: '나가기 전까지도 아직 네트워크로 보낸 적이 없다');
      expect(
        find.text('끊긴 채 두고 나간 메시지'),
        findsOneWidget,
        reason: '나가기 전엔 pending 버블로 화면에 보인다',
      );

      // 방을 나간다 — 위젯 트리를 통째로 교체해 ChatRoomScreenState.dispose()가 실제로 돈다
      // (Navigator.pop 이 아니라 트리 교체를 쓰는 이유: 이 harness는 MaterialApp.home 하나짜리라
      // pop할 이전 라우트가 없다 — 실제 앱에서는 chat_list_screen.dart의 rootNavigator push가
      // pop되며 같은 dispose를 일으킨다, 관찰 가능한 결과는 동일하다).
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pumpAndSettle();

      // 같은 방에 다시 들어온다 — 새 State 인스턴스(같은 repo 를 재사용해, 혹시라도 레포지토리
      // 쪽에 큐가 남아있다면 그것도 함께 잡아낸다).
      final captured2 = _CapturedRealtime();
      await tester.pumpWidget(_harness(user: _fakeUser(_buyerId), repo: repo, captured: captured2));
      await tester.pumpAndSettle();

      expect(
        find.text('끊긴 채 두고 나간 메시지'),
        findsNothing,
        reason:
            '오프라인 큐는 ChatRoomScreenState의 평범한 필드일 뿐이라 위젯이 dispose되면 함께 '
            '사라진다 — 어떤 영속 저장소(로컬 DB·SharedPreferences 등)에도 쓰지 않는다는 '
            '§12.5 Never 계약의 관찰 가능한 결과다. 만약 어디엔가 몰래 저장해뒀다면 재진입 시 '
            '이 pending 버블이 되살아나 보였을 것이다.',
      );
      expect(
        repo.sendCalls,
        isEmpty,
        reason: '재진입 후에도 그 메시지가 뒤늦게 네트워크로 전송된 적이 없어야 한다 — '
            '"몰래 살아남아 나중에 전송됨"이 아니라 "완전히 유실"임을 함께 확인한다',
      );
    });
  });

  // 2026-08-10 Epic 16 묶음 코드리뷰(verification-gap) — **구독 해제를 아무도 안 봤다.**
  // `dispose()`가 `(unsubscribeOverride ?? _defaultChatUnsubscribe)(handle)`로 채널을 정리하는데,
  // 이 파일의 `unsubscribeOverride`는 두 자리 모두 아무것도 기록하지 않는 no-op 람다였다.
  // 그래서 해제 호출이 통째로 사라지거나 **엉뚱한 handle**을 넘겨도 전 스위트가 green이었다.
  // "몇 번, 어떤 handle로 불렸나"를 실제로 기록해 단언한다 — 소켓 채널 누수는 화면에 안 보인다.
  group('실시간 구독 해제(코드리뷰 2026-08-10)', () {
    testWidgets('화면이 사라지면 subscribe가 돌려준 바로 그 handle로 정확히 1회 해제한다',
        (tester) async {
      final handle = Object(); // 이 인스턴스가 그대로 되돌아와야 한다.
      final unsubscribed = <Object>[];

      await tester.pumpWidget(ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser(_buyerId)),
          chatRepositoryProvider.overrideWithValue(_FakeChatRepository()),
        ],
        child: MaterialApp(
          home: ChatRoomScreen(
            roomId: 'room-1',
            subscribeOverride: ({required roomId, required onInsert, required onStatus}) => handle,
            unsubscribeOverride: unsubscribed.add,
          ),
        ),
      ));
      await tester.pump();

      expect(unsubscribed, isEmpty, reason: '화면이 살아 있는 동안엔 해제하면 안 된다');

      await tester.pumpWidget(const SizedBox.shrink()); // 트리 교체 = dispose
      await tester.pump();

      expect(unsubscribed.length, 1,
          reason: 'dispose가 정확히 1회 해제해야 한다 — 0이면 채널이 등록된 채 남아 누수된다');
      expect(identical(unsubscribed.single, handle), isTrue,
          reason: 'subscribe가 돌려준 그 handle이어야 한다 — 다른 값을 넘기면 실제 채널은 안 지워진다');
    });
  });
}
