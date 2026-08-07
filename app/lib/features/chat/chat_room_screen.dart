// 채팅방 화면(FR20·21, Story 16.4) — 메시지 송수신 + Realtime 구독. web ChatRoomMessages.tsx 이식.
//   `docs/conventions.md` §12·§12.4·§12.5·§12.6이 이 화면의 계약 단일 출처다.
//
//   · 전송(FR21): chat_messages INSERT(영속) + 즉시 pending 버블(UX-DR15) → 서버 확정 시 실제 행으로.
//     client_message_id(멱등키, 0022)를 전송 시작 시점에 만들어 실어 보낸다(재전송해도 1행만 남음).
//   · 실시간 수신(FR20·NFR1, §12): `chat:room:{roomId}` private 채널을 구독해 폴링 없이 즉시 반영.
//     최초 SUBSCRIBED 도달 시 한 번 더 전체 로드해 "조회~구독 사이" 틈을 메운다(§12.3).
//   · 재연결·오프라인 큐잉·갭보정(§12.5): 끊기면(channelError/timedOut) 비차단 배너만 띄우고
//     입력·전송은 계속 허용한다. 끊긴 동안 제출은 네트워크 호출 없이 로컬 큐에 쌓이고, 재연결
//     (subscribed, 이전에 끊긴 적 있음)되면 순서대로 flush + 커서 재조회(백스톱)를 항상 병행한다.
//   · 읽음 갱신(§12.6): 당사자로 확인된 방 진입 시 1회만 chat_room_reads 를 upsert한다.
//
// Design Notes(스펙 참조): Dart `State` 필드는 React ref 미러링이 필요 없다 — StatefulWidget 의
//   인스턴스 메서드는 항상 `this.field`의 현재 값을 읽으므로(클로저 캡처 문제가 없음), web의
//   pendingQueueRef·lastMessageAtRef 같은 이중 상태(state+ref)를 그대로 옮기지 않고 평범한 필드
//   하나로 둔다. 같은 이유로 web의 onAuthStateChange→수동 setAuth 재호출도 옮기지 않는다
//   (`realtime_client`가 매 join/rejoin마다 `socket.accessToken`으로 자동 재인증한다, 실측 확인).
//
// 테스트 훅: `subscribeOverride`/`unsubscribeOverride`(@visibleForTesting)로 실시간 구독 생성을
//   주입할 수 있다 — 위젯테스트가 실제 소켓 없이 onInsert/onStatus 콜백을 직접 호출해 배너·큐
//   flush·갭보정 반응을 시뮬레이션한다(ai_chat_screen.dart의 searchAiOverride와 동일 패턴).
import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/format/number_format.dart';
import '../../core/supabase/supabase_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import '../listings/listing_detail_screen.dart';
import 'chat_models.dart';
import 'chat_providers.dart';
import 'chat_repository.dart';

/// 실패한 멱등키를 재사용할 수 있는 시간 창(§12.4) — "방금 실패한 그 전송을 다시 보내는 것"에만
/// 유효하다. web FAILED_KEY_REUSE_WINDOW_MS 미러(60초).
const int _kFailedKeyReuseWindowMs = 60000;

/// 재연결(초록 "다시 연결됐어요") 배너가 자동으로 사라지기까지의 시간(§12.5 Always 예시값).
const Duration _kReconnectBannerDismiss = Duration(seconds: 3);

/// Broadcast Replay 요청 범위 — 두 값의 **출처가 다르다**(§12.5): limit=25는 라이브러리
/// (`realtime_client`)가 정한 상한, since=72시간은 우리가 고른 값(필수 인자라 무엇이든 골라야
/// 한다). 어느 쪽이든 이 한도를 넘는 gap은 아래 갭보정(커서 재조회)이 항상 메운다.
const Duration _kReplaySinceWindow = Duration(hours: 72);
const int _kReplayLimit = 25;

/// 실시간 구독을 시작하는 함수 — 실제 구현은 `supabase.channel(...).subscribe()`를 감싸고,
/// 테스트는 이 자리를 오버라이드해 네트워크 없이 onInsert/onStatus 콜백만 캡처한다. 반환값은
/// 구독 핸들(Object, 실제로는 RealtimeChannel)이며 이 화면은 내용을 들여다보지 않고
/// unsubscribeOverride 에 그대로 돌려줄 뿐이다.
typedef ChatRealtimeSubscribeFn =
    Object Function({
      required String roomId,
      required void Function(Map<String, dynamic> payload) onInsert,
      required void Function(RealtimeSubscribeStatus status, Object? error) onStatus,
    });

typedef ChatRealtimeUnsubscribeFn = void Function(Object handle);

/// 기본 구독 구현 — `supabase.channel(roomTopic(roomId), opts: RealtimeChannelConfig(private: true,
/// replay: ReplayOption(...)))`로 private 채널을 열고 INSERT 브로드캐스트를 구독한다(§12).
/// private:true 가 없으면 0023의 realtime.messages RLS 자체가 평가되지 않는다.
Object _defaultChatSubscribe({
  required String roomId,
  required void Function(Map<String, dynamic> payload) onInsert,
  required void Function(RealtimeSubscribeStatus status, Object? error) onStatus,
}) {
  final since = DateTime.now().toUtc().subtract(_kReplaySinceWindow).millisecondsSinceEpoch;
  final channel = supabase.channel(
    roomTopic(roomId),
    opts: RealtimeChannelConfig(
      private: true,
      replay: ReplayOption(since: since, limit: _kReplayLimit),
    ),
  );
  channel.onBroadcast(event: 'INSERT', callback: onInsert);
  channel.subscribe(onStatus);
  return channel;
}

void _defaultChatUnsubscribe(Object handle) {
  supabase.removeChannel(handle as RealtimeChannel);
}

/// UUID v4 문자열 생성(client_message_id 용) — 별도 패키지 의존 없이 `dart:math`만으로 만든다
/// (web `crypto.randomUUID()` 관례를 Dart로 옮긴 것, A2 — 이 하나의 용도로 새 패키지를 더하지 않는다).
final Random _uuidRandom = Random.secure();

String _newClientMessageId() {
  final bytes = List<int>.generate(16, (_) => _uuidRandom.nextInt(256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40; // version 4
  bytes[8] = (bytes[8] & 0x3f) | 0x80; // variant 10
  String hex(int start, int end) =>
      bytes.sublist(start, end).map((b) => b.toRadixString(16).padLeft(2, '0')).join();
  return '${hex(0, 4)}-${hex(4, 6)}-${hex(6, 8)}-${hex(8, 10)}-${hex(10, 16)}';
}

/// 재연결 배너 종류 — 끊김(비차단 경고)과 재연결(초록, 자동 소멸)은 색·텍스트·수명이 다르다.
enum ChatReconnectBanner { disconnected, reconnected }

class ChatRoomScreen extends ConsumerStatefulWidget {
  const ChatRoomScreen({
    super.key,
    required this.roomId,
    @visibleForTesting this.subscribeOverride,
    @visibleForTesting this.unsubscribeOverride,
  });

  final String roomId;

  /// 테스트 전용 주입점(ai_chat_screen.dart의 searchAiOverride와 동일 패턴) — 실제 소켓 없이
  /// onInsert/onStatus 콜백을 캡처해 상태 전이를 직접 시뮬레이션할 수 있게 한다.
  final ChatRealtimeSubscribeFn? subscribeOverride;
  final ChatRealtimeUnsubscribeFn? unsubscribeOverride;

  @override
  ConsumerState<ChatRoomScreen> createState() => ChatRoomScreenState();
}

/// 공개 State(테스트가 `tester.state<ChatRoomScreenState>(...)`로 접근해 상태-콜백을 직접 호출한다).
class ChatRoomScreenState extends ConsumerState<ChatRoomScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  List<ChatMessage> _messages = const [];
  bool _loading = true; // 초기 1회 로드 중
  bool _sending = false; // 온라인 전송 중(연타 차단 — 온라인 경로 전용, §12.5)
  String? _error; // 전송 에러(한국어) — 다음 전송 때 지워진다
  String? _realtimeError; // CLOSED·구독 준비 실패 전용(끊김 배너와 수명이 다름)
  String? _loadError; // 초기 로드/갭보정 실패(새로고침 전까지 유지)
  String? _loadErrorSource; // 'initial' | 'gapfill' — 갭보정 성공 시 "자기가 세운 안내만" 거둔다
  String? _queueStuckNotice; // flush 미전송 건수 안내(§12.5 — error 칸과 분리)

  List<QueuedChatMessage> _pendingQueue = const [];
  ChatReconnectBanner? _reconnectBanner;
  Timer? _reconnectBannerTimer;

  bool _disconnected = false;
  bool _everDropped = false;
  bool _initialSyncDone = false;
  bool _isFlushing = false;
  bool _flushRequestedAgain = false;
  bool _disposed = false;

  String? _onlineInFlightKey; // 온라인 경로가 응답을 기다리는 항목 — flush 대상에서 제외.
  String? _lastMessageAt; // 갭보정 커서(마지막으로 반영한 메시지의 created_at).
  FailedSend? _lastFailed; // 직전 실패한 전송(멱등키 재사용 판정용).
  final Set<String> _landedKeys = {}; // 실제로 목록에 오른 client_message_id 모음.

  Object? _channelHandle;

  ChatRepository get _repo => ref.read(chatRepositoryProvider);
  String? get _myId => ref.read(currentUserProvider)?.id;

  @override
  void initState() {
    super.initState();
    unawaited(_startRoom());
  }

  @override
  void dispose() {
    _disposed = true;
    _reconnectBannerTimer?.cancel();
    final handle = _channelHandle;
    if (handle != null) {
      (widget.unsubscribeOverride ?? _defaultChatUnsubscribe)(handle);
    }
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _startRoom() async {
    await _initialLoad();
    if (_disposed) return;
    unawaited(_markReadIfParticipant());
    _subscribeRealtime();
  }

  Future<void> _initialLoad() async {
    try {
      final msgs = await _repo.fetchMessages(widget.roomId); // 커서 없음 = 전체(§12.3).
      if (_disposed) return;
      setState(() {
        _messages = dedupeById(msgs);
        if (_messages.isNotEmpty) _lastMessageAt = _messages.last.createdAt;
        for (final m in _messages) {
          if (m.clientMessageId != null) _landedKeys.add(m.clientMessageId!);
        }
        _loading = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (_disposed) return;
      setState(() {
        _loadError = '과거 대화를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.';
        _loadErrorSource = 'initial';
        _loading = false;
      });
    }
  }

  /// 방 진입 시 읽음 1회 갱신(§12.6) — "방 조회 성공"이 아니라 "당사자"(buyer/seller 직접 대조)일
  /// 때만 호출한다. 실패해도 화면을 막지 않는다.
  Future<void> _markReadIfParticipant() async {
    final myId = _myId;
    if (myId == null) return;
    try {
      final room = await _repo.fetchRoom(widget.roomId);
      if (room != null && (myId == room.buyerId || myId == room.sellerId)) {
        await _repo.markRoomRead(widget.roomId);
      }
    } catch (e) {
      // ignore: avoid_print
      print('[chat/room] 읽음 갱신 대상 확인 실패: $e');
    }
  }

  void _subscribeRealtime() {
    final subscribeFn = widget.subscribeOverride;
    if (subscribeFn == null && supabase.auth.currentSession == null) {
      // 실 세션이 없으면 구독하지 않는다 — private 채널 인가(0023의 realtime.messages RLS)는
      // auth.uid()를 요구하므로, 세션 없이 구독해도 거부될 뿐이다. 이 화면은 로그인 후에만
      // 도달하므로(app_router.dart redirect) 실사용에서 이 분기는 사실상 도달하지 않는다 —
      // 방어적 가드다(부수 효과로, subscribeOverride 를 안 주는 위젯테스트가 실제 네트워크를
      // 건드리지 않게 막아준다).
      return;
    }
    // (subscribeFn ?? _defaultChatSubscribe)가 동기적으로 던질 수 있다(예: channel.subscribe()가
    // 즉시 예외를 냄) — _startRoom()이 initState에서 unawaited()로 실행되므로, 여기서 안 잡으면
    // 그 예외는 조용히 unhandled Future error로 묻히고 사용자에게는 아무 배너도 없이 방이 그냥
    // "죽은" 상태가 된다(코드리뷰 patch 3). 다른 실패 경로(_initialLoad 등)와 같은 톤으로
    // _realtimeError를 세운다.
    try {
      _channelHandle = (subscribeFn ?? _defaultChatSubscribe)(
        roomId: widget.roomId,
        onInsert: handleBroadcastInsert,
        onStatus: handleSubscribeStatus,
      );
    } catch (e) {
      // ignore: avoid_print
      print('[chat/room] 실시간 구독 시작 실패: $e');
      if (_disposed) return;
      setState(() => _realtimeError = '실시간 연결을 시작하지 못했습니다. 새로고침 후 다시 시도해주세요.');
    }
  }

  // ── 받은 메시지 병합(초기 로드·전송 확정·실시간 방송 셋 다 이 경로로 합류) ────────────────
  void _mergeIncoming(List<ChatMessage> incoming) {
    if (incoming.isEmpty) return;
    for (final m in incoming) {
      if (m.clientMessageId != null) _landedKeys.add(m.clientMessageId!);
    }
    setState(() {
      _messages = dedupeById([..._messages, ...incoming]);
      if (_messages.isNotEmpty) _lastMessageAt = _messages.last.createdAt;
    });
    _scrollToBottom();
  }

  void _enqueuePending(QueuedChatMessage entry) {
    setState(() => _pendingQueue = [..._pendingQueue, entry]);
  }

  void _removePendingById(String clientMessageId) {
    setState(
      () => _pendingQueue = _pendingQueue.where((p) => p.clientMessageId != clientMessageId).toList(),
    );
  }

  /// `_queueStuckNotice`("메시지 N건을 아직 보내지 못했습니다")를 현재 `_pendingQueue` 상태로
  /// 다시 계산한다 — 이 안내는 원래 `_flushQueue()` 안에서만 set/clear됐는데,
  /// `handleBroadcastInsert`도 브로드캐스트 에코로 pending 항목을 지울 수 있다(이미 서버엔
  /// 저장됐고 응답만 늦게 확인된 경우). 그 경로를 거치지 않으면 flush가 아니라 에코로 뒤늦게
  /// 확인된 항목도 여전히 "못 보냄"으로 남아(또는 실제보다 많은 건수로) 사용자에게 거짓 정보를
  /// 보여준다(코드리뷰 patch 4). 안내가 애초에 떠 있지 않았다면 손대지 않는다 — flush 성공
  /// 직후처럼 안내가 없는 상태에서 이 함수가 새로 안내를 만들어내면 안 된다(그건 여전히
  /// `_flushQueue()`의 몫이다).
  void _refreshQueueStuckNotice() {
    if (_queueStuckNotice == null) return;
    final stuck = _pendingQueue.where((p) => p.clientMessageId != _onlineInFlightKey).length;
    setState(() {
      _queueStuckNotice = stuck > 0 ? '메시지 $stuck건을 아직 보내지 못했습니다.' : null;
    });
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  // ── 실시간 구독 콜백(테스트가 직접 호출해 시뮬레이션한다) ─────────────────────────────────

  /// `channel.onBroadcast(event: 'INSERT')` 콜백 — payload.record(신규 행)를 mergeIncoming으로
  /// 합류시키고, 같은 client_message_id가 큐(온라인 전송 중 또는 오프라인 큐)에 있으면 "브로드캐스트
  /// 에코"로 보고 확정한다(§12.4).
  @visibleForTesting
  void handleBroadcastInsert(Map<String, dynamic> payload) {
    if (_disposed) return;
    final record = payload['record'];
    final message = ChatMessage.fromMap(record);
    if (message == null) return;
    _mergeIncoming([message]);
    final key = message.clientMessageId;
    if (key != null && _pendingQueue.any((p) => p.clientMessageId == key)) {
      _removePendingById(key);
      _refreshQueueStuckNotice();
    }
    final failed = _lastFailed;
    if (failed != null && key == failed.clientMessageId) {
      _lastFailed = null;
      setState(() {
        _error = null;
        if (_input.text == failed.body) _input.clear();
      });
    }
  }

  /// `channel.subscribe(...)` 상태 콜백 — 연결 상태 판단은 channelError/timedOut(끊김) ↔
  /// subscribed(재연결, 이전에 끊긴 적 있을 때만)만 본다(§12.5 Always). closed는 별도 취급하고
  /// 재연결 배너 대상에 넣지 않는다.
  @visibleForTesting
  void handleSubscribeStatus(RealtimeSubscribeStatus status, Object? error) {
    if (_disposed) return;
    switch (status) {
      case RealtimeSubscribeStatus.channelError:
      case RealtimeSubscribeStatus.timedOut:
        // ignore: avoid_print
        print('[chat/room] 실시간 구독 끊김: $status $error');
        _everDropped = true;
        _disconnected = true;
        _reconnectBannerTimer?.cancel();
        _reconnectBannerTimer = null;
        setState(() => _reconnectBanner = ChatReconnectBanner.disconnected);
      case RealtimeSubscribeStatus.closed:
        // Never — 12.3 이래의 기존 분기 유지. 명시적 leave()(방 이탈·언마운트)에서만 발생하고
        // 그 경우는 위 _disposed 가드가 이미 걸러낸다 — 실사용에서 사실상 도달하지 않는다.
        // ignore: avoid_print
        print('[chat/room] 실시간 구독 실패: $status $error');
        setState(() => _realtimeError = '실시간 연결이 끊겼습니다. 새로고침 후 다시 시도해주세요.');
      case RealtimeSubscribeStatus.subscribed:
        _disconnected = false;
        if (_everDropped) {
          // 재연결(§12.5 Always) — 배너를 초록으로 바꾸고 큐 flush + 갭보정을 항상 함께 돌린다.
          _reconnectBannerTimer?.cancel();
          setState(() => _reconnectBanner = ChatReconnectBanner.reconnected);
          _reconnectBannerTimer = Timer(_kReconnectBannerDismiss, () {
            _reconnectBannerTimer = null;
            if (_disposed) return;
            setState(() => _reconnectBanner = null);
          });
          unawaited(_flushQueue());
          unawaited(_gapFillFromCursor());
        } else {
          setState(() => _realtimeError = null);
        }
        if (!_initialSyncDone) {
          _initialSyncDone = true;
          // 최초 구독이 열린 직후 한 번 더 전체 로드(§12.3) — 초기 로드는 구독보다 먼저 나가므로
          // 그 틈에 들어온 INSERT를 메운다. 재연결마다 도는 갭보정과는 별개(최초 1회 한정).
          unawaited(() async {
            try {
              final msgs = await _repo.fetchMessages(widget.roomId);
              if (_disposed) return;
              _mergeIncoming(msgs);
            } catch (_) {
              // 실패해도 초기 로드분은 이미 화면에 있다 — 조용히 넘어간다(최초 구독 보정은 부가 조치).
            }
          }());
        }
    }
  }

  // ── 오프라인 큐 flush(§12.5 Always) ──────────────────────────────────────────────────────
  Future<void> _flushQueue() async {
    if (_isFlushing) {
      _flushRequestedAgain = true;
      return;
    }
    final snapshot = _pendingQueue.where((p) => p.clientMessageId != _onlineInFlightKey).toList();
    if (snapshot.isEmpty) return;
    _isFlushing = true;
    try {
      final result = await flushChatMessageQueue(
        snapshot,
        (msg) => _repo.sendMessage(
          roomId: widget.roomId,
          senderId: _myId ?? '',
          body: msg.body,
          clientMessageId: msg.clientMessageId,
        ),
      );
      if (_disposed) return;
      if (result.sent.isNotEmpty) _mergeIncoming(result.sent);
      if (result.remaining.isNotEmpty) {
        // ignore: avoid_print
        print('[chat/room] 오프라인 큐 일부 전송 실패, 다음 재연결에 재시도: ${result.remaining.length}건 남음');
        setState(() => _queueStuckNotice = '메시지 ${result.remaining.length}건을 아직 보내지 못했습니다.');
      } else {
        setState(() => _queueStuckNotice = null);
      }
      // 스냅샷이 아니라 "지금" 큐에서 성공분의 id만 걷어낸다 — flush 도중 새로 쌓인 pending을 지우지
      // 않기 위함(web P1 patch와 동일 이유).
      final sentIds = result.sent.map((m) => m.clientMessageId).whereType<String>().toSet();
      setState(
        () => _pendingQueue = _pendingQueue.where((p) => !sentIds.contains(p.clientMessageId)).toList(),
      );
    } catch (e) {
      if (_disposed) return;
      // ignore: avoid_print
      print('[chat/room] 오프라인 큐 flush 중 예외: $e');
    } finally {
      _isFlushing = false;
      if (_flushRequestedAgain && !_disposed) {
        _flushRequestedAgain = false;
        unawaited(_flushQueue());
      }
    }
  }

  // ── 갭보정(재연결마다 커서 재조회 — replay와 별개로 항상 병행, §12.5) ───────────────────────
  Future<void> _gapFillFromCursor() async {
    final cursor = _lastMessageAt;
    try {
      final msgs = await _repo.fetchMessages(widget.roomId, atOrAfterCreatedAt: cursor);
      if (_disposed) return;
      _mergeIncoming(msgs);
      // 자기가 세운 안내만 거둔다 — 커서 있는 조회의 성공은 그 이전 구간(초기 로드 실패분)까지
      // 복구했다는 증거가 아니다. 커서 없이(전체 재조회로) 돈 경우에만 초기 로드 실패도 함께 거둔다.
      if (cursor == null || _loadErrorSource == 'gapfill') {
        setState(() {
          _loadError = null;
          _loadErrorSource = null;
        });
      }
    } catch (e) {
      if (_disposed) return;
      // ignore: avoid_print
      print('[chat/room] 갭보정 커서 재조회 중 예외: $e');
      setState(() {
        _loadError = '끊긴 동안 놓친 메시지를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.';
        _loadErrorSource = 'gapfill';
      });
    }
  }

  // ── 전송 ────────────────────────────────────────────────────────────────────────────────
  Future<void> _send() async {
    final body = _input.text.trim();
    if (body.isEmpty) return;
    // 연타 차단(sending)은 온라인 경로 전용이다(§12.5 Always) — 끊긴 상태의 제출은 네트워크 왕복이
    // 아니라 로컬 큐잉이라 잠글 이유가 없다.
    if (_sending && !_disconnected) return;

    final myId = _myId;
    if (myId == null) return; // 로그인 전제(router redirect) — 방어적으로만.

    setState(() => _error = null);
    _input.clear();

    if (_disconnected) {
      // 끊긴 동안 제출 — 네트워크 호출을 시도하지 않고 즉시 pending + 로컬 큐 적재(§12.5 Always).
      final clientMessageId =
          reuseFailedKey(_lastFailed, body, DateTime.now().millisecondsSinceEpoch, _kFailedKeyReuseWindowMs) ??
          _newClientMessageId();
      _enqueuePending(QueuedChatMessage(clientMessageId: clientMessageId, body: body));
      _lastFailed = null;
      return;
    }

    setState(() => _sending = true);
    String? clientMessageId;
    try {
      clientMessageId =
          reuseFailedKey(_lastFailed, body, DateTime.now().millisecondsSinceEpoch, _kFailedKeyReuseWindowMs) ??
          _newClientMessageId();
      _enqueuePending(QueuedChatMessage(clientMessageId: clientMessageId, body: body));
      _onlineInFlightKey = clientMessageId;
      final res = await _repo.sendMessage(
        roomId: widget.roomId,
        senderId: myId,
        body: body,
        clientMessageId: clientMessageId,
      );
      if (_disposed) return;
      switch (res) {
        case SendMessageSuccess(:final message):
          _mergeIncoming([message]);
          _removePendingById(clientMessageId);
          _lastFailed = null;
        case SendMessageFailure(:final message):
          if (_landedKeys.contains(clientMessageId)) {
            // 응답만 유실되고 서버엔 저장된 경우 — 브로드캐스트 에코가 이미 목록에 올려뒀다.
            _removePendingById(clientMessageId);
            _lastFailed = null;
          } else {
            setState(() {
              _error = message;
              if (_input.text.isEmpty) _input.text = body; // 입력창이 비어있을 때만 복원.
            });
            _removePendingById(clientMessageId);
            _lastFailed = FailedSend(
              clientMessageId: clientMessageId,
              body: body,
              at: DateTime.now().millisecondsSinceEpoch,
            );
          }
      }
    } catch (e) {
      if (_disposed) return;
      // ignore: avoid_print
      print('[chat/room] 메시지 전송 예외: $e');
      if (clientMessageId != null && _landedKeys.contains(clientMessageId)) {
        _removePendingById(clientMessageId);
        _lastFailed = null;
      } else {
        setState(() {
          _error = '네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
          if (_input.text.isEmpty) _input.text = body;
        });
        if (clientMessageId != null) {
          _removePendingById(clientMessageId);
          _lastFailed = FailedSend(
            clientMessageId: clientMessageId,
            body: body,
            at: DateTime.now().millisecondsSinceEpoch,
          );
        }
      }
    } finally {
      if (!_disposed) setState(() => _sending = false);
      if (clientMessageId != null && _onlineInFlightKey == clientMessageId) {
        _onlineInFlightKey = null;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(chatRoomDetailProvider(widget.roomId));
    final myId = _myId;
    final isDisconnected = _reconnectBanner == ChatReconnectBanner.disconnected;
    final inputDisabled = (_sending && !isDisconnected) || _loading;

    return Scaffold(
      appBar: AppBar(title: const Text('문의 채팅')),
      body: Column(
        children: [
          detailAsync.maybeWhen(
            data: (room) =>
                room == null ? const SizedBox.shrink() : _RoomHeader(room: room, myId: myId),
            orElse: () => const SizedBox.shrink(),
          ),
          const Divider(height: 1),

          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty && _pendingQueue.isEmpty
                ? const Center(
                    key: Key('chat_empty'),
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        '아직 주고받은 메시지가 없습니다. 먼저 인사를 건네보세요.',
                        textAlign: TextAlign.center,
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length + _pendingQueue.length,
                    itemBuilder: (context, i) {
                      if (i < _messages.length) {
                        final m = _messages[i];
                        final mine = myId != null && m.senderId == myId;
                        return _Bubble(key: ValueKey('msg_${m.id}'), body: m.body, mine: mine);
                      }
                      // pending 큐는 맨 끝에 순서대로(§12.5 — 여러 건 동시 대기 가능).
                      final p = _pendingQueue[i - _messages.length];
                      return _Bubble(
                        key: ValueKey('pending_${p.clientMessageId}'),
                        body: p.body,
                        mine: true,
                        pending: true,
                      );
                    },
                  ),
          ),

          // 재연결 배너(§12.5 Always) — 비차단. 색+텍스트 동시 표기(비색 신호 중복).
          if (_reconnectBanner == ChatReconnectBanner.disconnected)
            Container(
              key: const Key('chat_disconnected_banner'),
              width: double.infinity,
              color: AppColors.warnAmberBg,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: const Text(
                '연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요.',
                style: TextStyle(color: AppColors.warnAmberInk),
              ),
            ),
          if (_reconnectBanner == ChatReconnectBanner.reconnected)
            Container(
              key: const Key('chat_reconnected_banner'),
              width: double.infinity,
              color: AppColors.trustGreenBg,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: const Text('다시 연결됐어요', style: TextStyle(color: AppColors.trustGreenInk)),
            ),

          if (_realtimeError != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Text(
                _realtimeError!,
                key: const Key('chat_realtime_error'),
                style: const TextStyle(color: AppColors.danger),
              ),
            ),

          // flush 미전송 안내 — 전송 에러(error) 칸과 분리(§12.5, 다음 제출 때 지워지면 안 됨).
          if (_queueStuckNotice != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      '$_queueStuckNotice '
                      '${isDisconnected ? '연결이 끊겨 지금은 다시 보낼 수 없습니다. 연결이 회복되면 자동으로 재시도합니다.' : '"다시 보내기"를 누르면 지금 다시 시도하고, 누르지 않으면 연결이 다시 끊겼다 회복될 때 재시도합니다.'}',
                      key: const Key('chat_queue_stuck_notice'),
                      style: const TextStyle(color: AppColors.danger),
                    ),
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    key: const Key('chat_retry_flush'),
                    onPressed: isDisconnected ? null : () => unawaited(_flushQueue()),
                    child: const Text('다시 보내기'),
                  ),
                ],
              ),
            ),

          if (_loadError != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Text(
                _loadError!,
                key: const Key('chat_load_error'),
                style: const TextStyle(color: AppColors.danger),
              ),
            ),

          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Text(
                _error!,
                key: const Key('chat_error'),
                style: const TextStyle(color: AppColors.danger),
              ),
            ),

          // 입력 영역 — 끊긴 동안엔 sending 으로 잠그지 않는다(§12.5 Always, 비차단).
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('chat_input'),
                      controller: _input,
                      enabled: !inputDisabled,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => unawaited(_send()),
                      decoration: const InputDecoration(
                        hintText: '메시지를 입력하세요',
                        border: OutlineInputBorder(),
                        isDense: true,
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    key: const Key('chat_send'),
                    onPressed: inputDisabled ? null : () => unawaited(_send()),
                    child: _sending && !isDisconnected
                        ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Text('전송'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// 방 헤더 — 매물 요약(없으면 플레이스홀더) + 상대 이름 + on_sale 일 때만 매물 상세 링크.
class _RoomHeader extends StatelessWidget {
  const _RoomHeader({required this.room, required this.myId});

  final ChatRoomSummary room;
  final String? myId;

  @override
  Widget build(BuildContext context) {
    final iAmBuyer = myId != null && myId == room.buyerId;
    final counterLabel = iAmBuyer ? '판매자' : '구매자';
    final counterName = iAmBuyer ? room.sellerName : room.buyerName;
    final l = room.listing;
    final summary = l != null
        ? '[${l.manufacturer}] ${l.model} · ${l.year}년 · ${wonText(l.price)}'
        : '판매 완료되었거나 조회할 수 없는 매물';

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 12, 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  summary,
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: l != null ? null : Colors.grey,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  counterName != null
                      ? '$counterLabel $counterName와의 문의 채팅'
                      : '$counterLabel와의 문의 채팅',
                  style: TextStyle(fontSize: 12, color: Colors.grey[600]),
                ),
              ],
            ),
          ),
          // 매물이 살아있는(on_sale, 임베드 non-null) 방이면 상세로. sold(l=null)면 FR11 따라 숨김.
          if (l != null)
            TextButton(
              key: const Key('chat_to_listing'),
              onPressed: () => Navigator.of(context).push(
                MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: room.listingId)),
              ),
              child: const Text('매물 상세'),
            ),
        ],
      ),
    );
  }
}

/// 메시지 버블 — 내 메시지 오른쪽(petrol 채움), 상대 왼쪽(surface-raised). pending 이면 반투명.
class _Bubble extends StatelessWidget {
  const _Bubble({super.key, required this.body, required this.mine, this.pending = false});

  final String body;
  final bool mine;
  final bool pending;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Opacity(
        opacity: pending ? 0.6 : 1.0,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
          decoration: BoxDecoration(
            color: mine ? scheme.primary : scheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(body, style: TextStyle(color: mine ? scheme.onPrimary : scheme.onSurface)),
        ),
      ),
    );
  }
}
