// AI 검색 채팅 화면(FR12·17·18 재현) — 자연어 대화로 매물을 찾는다.
// /ai/search 호출 → {answer, listings} → 자연어 답변 + 매물카드. 멀티턴은 화면 로컬 상태(무상태).
// web ChatAssistant 의 동작(낙관적 버블·실패 롤백·context 동봉)을 Flutter 로 이식.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../listings/listing_card.dart';
import '../listings/listing_detail_screen.dart';
import 'ai_search_api.dart';
import 'chat_message.dart';

class AiChatScreen extends ConsumerStatefulWidget {
  const AiChatScreen({super.key});

  @override
  ConsumerState<AiChatScreen> createState() => _AiChatScreenState();
}

class _AiChatScreenState extends ConsumerState<AiChatScreen> {
  // 대화 기록 — 화면 상태에만 존재(무상태). 화면을 닫으면 사라진다(FR18 의도된 동작).
  final List<ChatMessage> _messages = [];
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final query = _input.text.trim();
    if (query.isEmpty || _loading) return; // 빈 질의·중복 전송 차단.

    // 질의가 서버 상한(1000자)을 넘으면 422 가 떠 원인 모를 안내만 받는다 → 클라에서 먼저 알린다.
    if (query.length > maxQueryLength) {
      setState(() => _error = '질문이 너무 깁니다. $maxQueryLength자 이내로 줄여 다시 시도해주세요.');
      return;
    }

    // 이번 질의 직전까지의 대화를 context 로(방금 query 는 context 가 아니라 query 로 보냄).
    final context = buildContext(_messages);

    setState(() {
      _error = null;
      _messages.add(ChatMessage(role: 'user', content: query)); // 낙관적 user 버블.
      _input.clear();
      _loading = true;
    });
    _scrollToBottom();

    try {
      // 매 전송 시 현재 세션 토큰(만료 자동 갱신).
      final token = Supabase.instance.client.auth.currentSession?.accessToken;
      final result = await searchAi(
        query: query,
        context: context.isNotEmpty ? context : null,
        accessToken: token,
      );
      if (!mounted) return;
      setState(() {
        _messages.add(ChatMessage(
          role: 'assistant',
          content: result.answer,
          listings: result.listings,
        ));
        _loading = false;
      });
      _scrollToBottom();
    } catch (e) {
      if (!mounted) return;
      // fail-loud + 롤백: 방금 낙관적으로 넣은 user 버블 제거, 입력 복원(곧바로 재시도 가능).
      setState(() {
        _error = e is AiSearchException
            ? e.message
            : 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.';
        if (_messages.isNotEmpty && _messages.last.isUser) {
          _messages.removeLast();
        }
        _input.text = query;
        _loading = false;
      });
    }
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) {
        _scroll.animateTo(
          _scroll.position.maxScrollExtent,
          duration: const Duration(milliseconds: 200),
          curve: Curves.easeOut,
        );
      }
    });
  }

  void _openDetail(String id) {
    Navigator.of(context).push(
      MaterialPageRoute(builder: (_) => ListingDetailScreen(listingId: id)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AI 검색')),
      body: Column(
        children: [
          Expanded(
            child: _messages.isEmpty && !_loading
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        '예: "3천만원 이하 흰색 SUV", "패밀리카로 무난한 거 추천해줘"',
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey),
                      ),
                    ),
                  )
                : ListView.builder(
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: _messages.length + (_loading ? 1 : 0),
                    itemBuilder: (context, i) {
                      if (i >= _messages.length) {
                        // 로딩 placeholder(요청 중).
                        return const Align(
                          alignment: Alignment.centerLeft,
                          child: Padding(
                            padding: EdgeInsets.symmetric(vertical: 6),
                            child: Text('검색 중…', style: TextStyle(color: Colors.grey)),
                          ),
                        );
                      }
                      return _MessageBubble(
                        message: _messages[i],
                        onTapListing: _openDetail,
                      );
                    },
                  ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Text(
                _error!,
                key: const Key('ai_error'),
                style: const TextStyle(color: Colors.red, fontSize: 13),
              ),
            ),
          const Divider(height: 1),
          // 입력 폼 — 전송 버튼 또는 키보드 제출. 로딩 중 비활성(연타 차단).
          // SafeArea(top:false): 하단 시스템 내비바(edge-to-edge)에 입력란이 가리지 않게 여백 확보.
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 12),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _input,
                      enabled: !_loading,
                      decoration: const InputDecoration(
                        hintText: '찾으시는 차를 자연어로 입력하세요',
                        isDense: true,
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _submit(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  FilledButton(
                    key: const Key('ai_send'),
                    onPressed: _loading ? null : _submit,
                    child: const Text('전송'),
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

/// 대화 한 줄 말풍선. user=오른쪽, assistant=왼쪽 + (있으면) 매물카드.
class _MessageBubble extends StatelessWidget {
  const _MessageBubble({required this.message, required this.onTapListing});

  final ChatMessage message;
  final ValueChanged<String> onTapListing;

  @override
  Widget build(BuildContext context) {
    if (message.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.primary,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(
            message.content,
            style: const TextStyle(color: Colors.white),
          ),
        ),
      );
    }
    // assistant — 답변 텍스트 + 매물카드 목록.
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          margin: const EdgeInsets.symmetric(vertical: 4),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(12),
          ),
          child: Text(message.content),
        ),
        ...message.listings.map(
          (l) => ListingCard(listing: l, onTap: () => onTapListing(l.id)),
        ),
      ],
    );
  }
}
