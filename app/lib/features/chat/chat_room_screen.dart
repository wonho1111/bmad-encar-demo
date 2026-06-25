// 채팅방 화면(FR20·21 재현) — 메시지 송수신 + 폴링 수신. web ChatRoomMessages.tsx 이식.
//   · 전송(FR21): chat_messages INSERT(영속) + 내 화면 즉시(낙관) 반영.
//   · 폴링 수신(FR20·NFR1): 3초마다 커서 뒤 새 메시지만 증분(gte) 조회 → dedupe 머지 → 상대 메시지 ≤5초 갱신.
//   · 목록: created_at 오름차순(동시각 id 2차). 내 메시지(오른쪽)·상대(왼쪽). 0건이면 빈 상태.
//   · 헤더(chatRoomDetailProvider): 매물 요약·상대 이름 + on_sale 일 때만 매물 상세 링크(FR11).
//
// 왜 StatefulWidget 인가: 대화 상태·입력·타이머·커서를 화면이 쥐어야 한다(web 'use client' 컴포넌트 대응).
//   initState 에서 초기 로드 + Timer.periodic 시작, dispose 에서 cancel(메모리 누수·유령 요청 방지).
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format/number_format.dart';
import '../../core/supabase/supabase_client.dart';
import '../listings/listing_detail_screen.dart';
import 'chat_models.dart';
import 'chat_providers.dart';
import 'chat_repository.dart';

/// 폴링 주기 — NFR1 "채팅 폴링 준실시간(3~5초)"의 하단값(web POLL_INTERVAL_MS=3000 과 일치, 체감 응답성↑).
///   증분(gte 커서)+id dedupe 라 요청이 겹쳐도 중복/누락 없음.
const Duration _pollInterval = Duration(seconds: 3);

class ChatRoomScreen extends ConsumerStatefulWidget {
  const ChatRoomScreen({super.key, required this.roomId});

  final String roomId;

  @override
  ConsumerState<ChatRoomScreen> createState() => _ChatRoomScreenState();
}

class _ChatRoomScreenState extends ConsumerState<ChatRoomScreen> {
  final _input = TextEditingController();
  final _scroll = ScrollController();

  List<ChatMessage> _messages = const [];
  String? _cursor; // 마지막으로 받은 메시지의 created_at(폴링 증분 커서). 멤버라 콜백이 항상 최신 참조.
  bool _loading = true; // 초기 1회 로드 중
  bool _sending = false; // 전송 중(연타 차단)
  String? _error; // 전송/조회 에러(한국어)
  Timer? _timer;

  ChatRepository get _repo => ref.read(chatRepositoryProvider);
  String? get _myId => supabase.auth.currentUser?.id;

  @override
  void initState() {
    super.initState();
    _initialLoad();
    // 폴링: 3초마다 커서 뒤 새 메시지만 증분 조회 → dedupe 머지.
    _timer = Timer.periodic(_pollInterval, (_) => _poll());
  }

  @override
  void dispose() {
    _timer?.cancel(); // 폴링 정리(AC3 — web useEffect cleanup 대응).
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _initialLoad() async {
    try {
      final msgs = await _repo.fetchMessages(widget.roomId); // 커서 없음 = 전체
      if (!mounted) return;
      setState(() {
        _messages = dedupeById(msgs);
        _cursor = _messages.isNotEmpty ? _messages.last.createdAt : null;
        _loading = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = '메시지를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.';
        _loading = false;
      });
    }
  }

  Future<void> _poll() async {
    try {
      final incoming =
          await _repo.fetchMessages(widget.roomId, atOrAfterCreatedAt: _cursor);
      if (!mounted || incoming.isEmpty) return;
      _mergeIncoming(incoming);
    } catch (_) {
      // 일시 조회 실패는 조용히 넘기고 다음 주기에 재시도(폴링은 계속).
    }
  }

  // 받은 메시지를 기존 목록에 합친다(id dedupe + 시간순 재정렬). 커서를 마지막 created_at 으로 전진.
  void _mergeIncoming(List<ChatMessage> incoming) {
    final merged = dedupeById([..._messages, ...incoming]);
    final last = merged.isNotEmpty ? merged.last.createdAt : _cursor;
    setState(() {
      _messages = merged;
      if (last != null && (_cursor == null || last.compareTo(_cursor!) > 0)) {
        _cursor = last;
      }
    });
    _scrollToBottom();
  }

  void _scrollToBottom() {
    // 다음 프레임에 맨 아래로(새 메시지 따라가기). 컨트롤러 미부착 시 무시.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.jumpTo(_scroll.position.maxScrollExtent);
      }
    });
  }

  Future<void> _send() async {
    final body = _input.text.trim();
    final myId = _myId;
    if (body.isEmpty || _sending || myId == null) return;

    setState(() {
      _error = null;
      _sending = true;
      _input.clear(); // 즉시 입력창 비움(피드백). 실패하면 복원.
    });

    final res = await _repo.sendMessage(
      roomId: widget.roomId,
      senderId: myId,
      body: body,
    );
    if (!mounted) return;

    switch (res) {
      case SendMessageSuccess(:final message):
        // 저장된 행을 즉시 반영(낙관). 폴링이 같은 행을 또 가져와도 dedupe 로 중복 없음.
        _mergeIncoming([message]);
        setState(() => _sending = false);
      case SendMessageFailure(:final message):
        setState(() {
          _error = message;
          _input.text = body; // 실패 → 다시 보낼 수 있게 입력 복원.
          _sending = false;
        });
    }
  }

  @override
  Widget build(BuildContext context) {
    final detailAsync = ref.watch(chatRoomDetailProvider(widget.roomId));
    final myId = _myId;

    return Scaffold(
      appBar: AppBar(title: const Text('문의 채팅')),
      body: Column(
        children: [
          // 헤더 — 매물 요약·상대 이름 + on_sale 매물 상세 링크.
          detailAsync.maybeWhen(
            data: (room) => room == null
                ? const SizedBox.shrink()
                : _RoomHeader(room: room, myId: myId),
            orElse: () => const SizedBox.shrink(),
          ),
          const Divider(height: 1),

          // 메시지 목록.
          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
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
                        itemCount: _messages.length,
                        itemBuilder: (context, i) {
                          final m = _messages[i];
                          final mine = myId != null && m.senderId == myId;
                          return _Bubble(body: m.body, mine: mine);
                        },
                      ),
          ),

          // 에러 안내(조용한 실패 금지).
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: Text(
                _error!,
                key: const Key('chat_error'),
                style: const TextStyle(color: Colors.red),
              ),
            ),

          // 입력 영역 — Enter(submit) 또는 전송 버튼. 전송 중 비활성(연타 차단).
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
                      enabled: !_sending,
                      textInputAction: TextInputAction.send,
                      onSubmitted: (_) => _send(),
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
                    onPressed: _sending ? null : _send,
                    child: _sending
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
                MaterialPageRoute(
                  builder: (_) => ListingDetailScreen(listingId: room.listingId),
                ),
              ),
              child: const Text('매물 상세'),
            ),
        ],
      ),
    );
  }
}

/// 메시지 버블 — 내 메시지 오른쪽(파랑), 상대 왼쪽(회색). 줄바꿈 보존.
class _Bubble extends StatelessWidget {
  const _Bubble({required this.body, required this.mine});

  final String body;
  final bool mine;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Align(
      alignment: mine ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: mine ? scheme.primary : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(
          body,
          style: TextStyle(color: mine ? scheme.onPrimary : scheme.onSurface),
        ),
      ),
    );
  }
}
