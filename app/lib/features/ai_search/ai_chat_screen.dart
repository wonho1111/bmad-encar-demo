// AI 검색 채팅 화면(FR12·17·18 재현) — 자연어 대화로 매물을 찾는다.
// /ai/search 호출 → {answer, listings, clarify} → 자연어 답변 + 매물카드 + (있으면) 되묻기 칩.
// 멀티턴은 화면 로컬 상태(무상태). web ChatAssistant 의 동작(낙관적 버블·실패 롤백·context 동봉)을
// Flutter 로 이식(단, 되묻기 칩은 web이 아직 렌더하지 않는 앱 전용 확장 — spec-16-5).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/theme/app_theme.dart';
import '../listings/listing_card.dart';
import '../listings/listing_detail_screen.dart';
import '../wishlist/wishlist_providers.dart';
import 'ai_search_api.dart';
import 'chat_message.dart';

/// `searchAi`(ai_search_api.dart)와 같은 시그니처 — 테스트 전용 주입 시접(seam)에 쓴다.
typedef SearchAiFn = Future<SearchResult> Function({
  required String query,
  List<ConversationTurn>? context,
  required String? accessToken,
});

class AiChatScreen extends ConsumerStatefulWidget {
  const AiChatScreen({super.key, @visibleForTesting this.searchAiOverride});

  // 테스트 전용 시접 — 기본은 실제 네트워크 호출(searchAi). `API_BASE_URL`은 컴파일타임
  // 상수(String.fromEnvironment)라 테스트에서 값을 채울 수 없고, flutter_test는 실제 네트워크도
  // 막는다 — 이 화면의 검색 파이프라인(wished 배선 포함)을 오버라이드 없이 테스트할 방법이
  // 없다(ai_search_api.dart의 imageUrlBuilder seam과 같은 원칙, Story 16.3 코드리뷰 지적).
  @visibleForTesting
  final SearchAiFn? searchAiOverride;

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

  // [overrideQuery]: 되묻기 칩 탭 전용(spec-16-5 Design Notes) — 칩 문자열을 그대로 다음
  // 질의로 보낸다. 낙관적 버블·에러 롤백·로딩 잠금을 새로 만들지 않고 이 경로를 그대로 물려받는다.
  // 반환값 = 전송 성공 여부(칩 탭이 실패 시 "선택됨" 표시를 되돌리는 데 쓴다 — review).
  Future<bool> _submit({String? overrideQuery}) async {
    final query = (overrideQuery ?? _input.text).trim();
    if (query.isEmpty || _loading) return false; // 빈 질의·중복 전송 차단.

    // 질의가 UX 상한(500자)을 넘으면 422 가 떠 원인 모를 안내만 받는다 → 클라에서 먼저 알린다.
    // TextField의 maxLength가 타이핑 경로는 이미 막지만, 이 가드는 방어적으로 유지한다.
    // ⚠️ maxLength 와 **같은 단위(그래핌)** 로 센다 — String.length(UTF-16 코드유닛)로 세면
    // 이모지처럼 2코드유닛인 글자에서 "카운터는 400/500인데 전송은 막히고 500자로 줄이라는
    // 안내가 뜨는" 빠져나갈 수 없는 상태가 된다(review 실측).
    if (query.characters.length > maxQueryLength) {
      setState(() => _error = '질문이 너무 깁니다. $maxQueryLength자 이내로 줄여 다시 시도해주세요.');
      return false;
    }

    // 이번 질의 직전까지의 대화를 context 로(방금 query 는 context 가 아니라 query 로 보냄).
    final context = buildContext(_messages);

    setState(() {
      _error = null;
      _messages.add(ChatMessage(role: 'user', content: query)); // 낙관적 user 버블.
      // overrideQuery(칩 탭)로 온 제출이면 입력창은 손대지 않는다 — 사용자가 칩 탭 전에
      // 독립적으로 타이핑해 둔 초안이 있을 수 있고, 그건 칩 전송과 무관하다(review).
      if (overrideQuery == null) _input.clear();
      _loading = true;
    });
    _scrollToBottom();

    try {
      // 매 전송 시 현재 세션 토큰(만료 자동 갱신).
      final token = Supabase.instance.client.auth.currentSession?.accessToken;
      final search = widget.searchAiOverride ?? searchAi;
      final result = await search(
        query: query,
        context: context.isNotEmpty ? context : null,
        accessToken: token,
      );
      if (!mounted) return false;
      setState(() {
        _messages.add(
          ChatMessage(
            role: 'assistant',
            content: result.answer,
            listings: result.listings,
            clarify: result.clarify,
          ),
        );
        _loading = false;
      });
      _scrollToBottom();
      return true;
    } catch (e) {
      if (!mounted) return false;
      // fail-loud + 롤백: 방금 낙관적으로 넣은 user 버블 제거, 입력 복원(곧바로 재시도 가능).
      setState(() {
        _error = e is AiSearchException
            ? e.message
            : 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.';
        if (_messages.isNotEmpty && _messages.last.isUser) {
          _messages.removeLast();
        }
        // 위 clear()와 대칭 — 칩 탭 제출이었다면 입력창을 건드리지 않는다(사용자 초안 보존).
        if (overrideQuery == null) _input.text = query;
        _loading = false;
      });
      return false;
    }
  }

  // 되묻기 칩 탭(spec-16-5) — 탭한 문자열을 그 메시지에 기록(선택됨 표시, EXPERIENCE.md)한
  // 뒤 기존 _submit 파이프라인을 그대로 태운다. 새 user 버블이 곧바로 쌓이므로 이 메시지는
  // 다음 build부터 "마지막 메시지"가 아니게 되고, 그 결과 이 칩 행은 자동으로 비활성화된다
  // (코드리뷰 지적 — 낡은 칩이 영영 눌리는 문제, "마지막 메시지의 칩 행만 활성"이 곧 해법).
  //
  // 전송이 실패하면 "선택됨" 표시를 되돌린다(review 실측): 롤백으로 user 버블이 사라져 이
  // 메시지가 다시 마지막이 되고 칩 행도 다시 활성화되는데, 탭했던 칩만 `isSelected` 때문에
  // 영구 비활성으로 남아 "재시도 가능해 보이는데 그 칩만 죽어 있는" 상태가 됐다.
  //
  // ⚠️ 맨 앞의 _loading 가드가 없으면 **같은 프레임 연타**가 진행 중인 칩의 표시를 지운다
  // (review 실측): 첫 탭이 _loading 을 켜지만 칩 행이 실제로 비활성으로 다시 그려지는 건
  // 다음 build 이후라, 그 전에 들어온 두 번째 탭이 표시를 찍고 → _submit 이 _loading 때문에
  // 곧바로 false 를 돌려주고 → 아래 롤백이 **첫 탭의 표시까지** 지워 버린다.
  Future<void> _onChipTap(int messageIndex, int chipIndex) async {
    if (_loading) return;
    final chips = _messages[messageIndex].clarify?.chips;
    if (chips == null || chipIndex >= chips.length) return;
    setState(() {
      _messages[messageIndex] =
          _messages[messageIndex].withUsedChipIndex(chipIndex);
    });
    final ok = await _submit(overrideQuery: chips[chipIndex]);
    if (ok || !mounted) return;
    setState(() {
      if (messageIndex < _messages.length) {
        _messages[messageIndex] =
            _messages[messageIndex].withUsedChipIndex(null);
      }
    });
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
    // 찜 오버레이 — 카드 진입점 3곳(홈·검색·AI)이 공유하는 단일 provider(spec-16-3 Boundaries).
    final wishedIds = ref.watch(wishedListingIdsProvider).value ?? const <String>{};
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
                            child: Text(
                              '검색 중…',
                              style: TextStyle(color: Colors.grey),
                            ),
                          ),
                        );
                      }
                      // 칩 탭 = _onChipTap() 재호출(기존 낙관적 버블·롤백·로딩을 그대로
                      // 물려받는다). 활성 조건은 "이 메시지가 대화의 마지막일 것" 하나다 —
                      // 아니면 낡은(예전 턴) 되묻기 칩이 영원히 눌려 스크롤백 아무 데서나
                      // 현재 context로 재전송된다(코드리뷰 지적).
                      //
                      // 여기에 `_loading ||`을 함께 걸었던 적이 있으나 **도달 불가능한 조건**임이
                      // 실측으로 확인돼 걷어냈다(review): _loading 이 켜지는 setState 는 같은
                      // 자리에서 낙관적 user 버블을 append 하므로, 로딩 중에 마지막 메시지는
                      // 항상 그 user 버블이고 clarify 를 가진 assistant 메시지는 결코 isLast 가
                      // 아니다. 연타 경합은 렌더가 아니라 _onChipTap 맨 앞의 _loading 가드가
                      // 막는다(그 자리라야 다음 build 전에 들어온 탭도 걸린다).
                      final isLast = i == _messages.length - 1;
                      return _MessageBubble(
                        message: _messages[i],
                        onTapListing: _openDetail,
                        wishedIds: wishedIds,
                        onTapChip:
                            isLast ? (chipIndex) => _onChipTap(i, chipIndex) : null,
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
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _input,
                          enabled: !_loading,
                          // 500자 하드 제한 — 서버 하드 상한(1000)보다 엄격한 UX 상한
                          // (spec-16-5 Always, web HeroSearch.tsx 미러). maxLength가
                          // 타이핑·붙여넣기를 501번째 글자부터 막는다.
                          maxLength: maxQueryLength,
                          decoration: const InputDecoration(
                            hintText: '찾으시는 차를 자연어로 입력하세요',
                            isDense: true,
                            border: OutlineInputBorder(),
                            // 기본 Material 카운터를 끄고 아래에서 직접 그린다 — 기본
                            // 카운터는 입력 박스 **안쪽** 높이에 얹혀 Row 를 키우고, 그
                            // 결과 전송 버튼이 입력 박스 중심보다 10px 아래로 내려갔다
                            // (review 실측). web HeroSearch.tsx 도 카운터를 입력 밖에
                            // 따로 그린다.
                            counterText: '',
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
                  // 실시간 카운터(spec-16-5 Always). maxLength 와 같은 단위(그래핌)로 센다.
                  //
                  // 표시값은 상한으로 clamp 한다 — `maxLength`의 기본 강제 방식이 플랫폼마다
                  // 다르기 때문이다(review, Flutter SDK 실측): Android·Windows 는 enforced 라
                  // 501번째 글자가 아예 안 들어오지만, **web·iOS·macOS·linux 는
                  // truncateAfterCompositionEnds** — IME 조합이 진행 중인 동안은 상한을
                  // 넘겨도 통과시켰다가 조합이 끝날 때 잘라낸다(한글 입력이 정확히 이 경로다).
                  // clamp 가 없으면 조합 중 잠깐 "503/500"이 보인다. 조합 중 강제(enforced)로
                  // 바꾸지 않는 이유는 그게 CJK 입력을 깨뜨리기 때문이며, 그래서 Flutter 도
                  // 그 플랫폼들에서 이 방식을 기본값으로 둔다.
                  ValueListenableBuilder<TextEditingValue>(
                    valueListenable: _input,
                    builder: (context, value, _) {
                      final count = value.text.characters.length;
                      final shown = count > maxQueryLength ? maxQueryLength : count;
                      return Padding(
                        padding: const EdgeInsets.only(top: 4, right: 4),
                        // 기본 Material 카운터를 끄면서(counterText: '') 딸려 나간 접근성
                        // 시맨틱을 되살린다 — InputDecorator 는 기본 카운터를
                        // Semantics(liveRegion) 로 감싸 글자수를 읽어 주는데, 직접 그린
                        // Text 에는 그게 없어 스크린리더 사용자가 상한 근접을 알 수 없었다
                        // (review, input_decorator.dart 실측).
                        child: Semantics(
                          container: true,
                          liveRegion: true,
                          label: '입력 글자수 $shown / 최대 $maxQueryLength자',
                          child: ExcludeSemantics(
                            child: Text(
                              '$shown/$maxQueryLength',
                              key: const Key('ai_query_counter'),
                              style: const TextStyle(
                                fontSize: 12,
                                color: AppColors.inkMuted,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
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
  const _MessageBubble({
    required this.message,
    required this.onTapListing,
    required this.wishedIds,
    required this.onTapChip,
  });

  final ChatMessage message;
  final ValueChanged<String> onTapListing;
  final Set<String> wishedIds;
  // 탭된 **칩 인덱스**를 받는다(문자열이 아니라 — 중복 문자열 칩을 가르기 위해서다,
  // ChatMessage.usedChipIndex 주석 참조). null이면(이 메시지가 대화의 마지막이 아니면)
  // 칩이 비활성 상태로 렌더된다.
  final ValueChanged<int>? onTapChip;

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
            // petrol(브랜드 색) 배경 위 잉크는 하드코딩 흰색 대신 토큰을 쓴다(review,
            // spec-16-1 P10 — app_router.dart 프로필 아이콘과 같은 규칙).
            style: const TextStyle(color: AppColors.onPetrol),
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
        // 되묻기 칩(spec-16-5 Always) — clarify가 채워지고 chips가 비어있지 않을 때만 렌더.
        // 상한 초과 강제 폴백(clarify:null)·구조형/거절 응답(clarify:null)은 이 조건에서
        // 자연히 걸러진다(클라 자체 카운터 없이 서버 신호만으로 동작).
        if (message.clarify != null && message.clarify!.chips.isNotEmpty)
          _ClarifyChips(
            // 테스트가 "칩 행이 아예 없다"를 단언할 수 있는 손잡이(review: 이전 테스트는
            // 이 프로젝트에 존재하지 않는 ActionChip 을 찾고 있어 항상 통과했다).
            key: const Key('clarify_chips'),
            chips: message.clarify!.chips,
            onTap: onTapChip,
            selectedIndex: message.usedChipIndex,
          ),
        ...message.listings.map(
          (l) => ListingCard(
            // 새 질의로 대화가 늘어날 때 Flutter가 같은 위치의 카드 State를 다른 매물에
            // 재사용해 WishButton의 낙관적 하트 상태가 엉뚱한 매물에 붙는 걸 막는다(코드리뷰
            // 지적 — wishlist_screen.dart가 이미 쓰는 것과 같은 key).
            key: ValueKey(l.id),
            listing: l,
            wished: wishedIds.contains(l.id),
            onTap: () => onTapListing(l.id),
          ),
        ),
      ],
    );
  }
}

/// 되묻기 칩 행 — `chips` 배열 순서대로 탭 가능한 칩을 렌더한다(spec-16-5 AC1). 탭하면 그
/// 칩의 **인덱스**로 `onTap`(→ `_onChipTap` → `_submit(overrideQuery: chip)`)을 호출해 기존
/// 전송 파이프라인을 그대로 탄다. `onTap`이 null이면(이 메시지가 더 이상 대화의 마지막이
/// 아니면 — ai_chat_screen.dart의 `isLast` 게이트) 비활성 상태로 그린다. 자유 입력창은
/// 이때도 항상 활성이다(spec-16-5 Always, 칩만 잠긴다).
///
/// 가로 한 줄 고정(D5, project-context.md 13 — "전 UI governing", 2줄로 밀림 = 절대 금기):
/// `Wrap`은 좁은 화면에서 칩이 다음 줄로 밀릴 수 있어 쓰지 않는다. 넘치면 가로 스크롤로만
/// 흡수한다(D5가 허용하는 "가장자리 부분 클리핑" 형태).
class _ClarifyChips extends StatelessWidget {
  const _ClarifyChips({
    super.key,
    required this.chips,
    required this.onTap,
    this.selectedIndex,
  });

  final List<String> chips;
  final ValueChanged<int>? onTap;
  // 이 칩 행에서 이미 탭된 칩의 인덱스(있으면) — petrol 채움 + ✓ "선택됨" 표시(EXPERIENCE.md,
  // 비색 신호 중복 규칙: 색만으로 신호하지 않는다). 문자열이 아니라 인덱스인 이유는
  // ChatMessage.usedChipIndex 주석 참조(중복 문자열 칩).
  final int? selectedIndex;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            for (var i = 0; i < chips.length; i++) ...[
              if (i > 0) const SizedBox(width: 8),
              _buildChip(chips[i], i),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildChip(String chip, int index) {
    final isSelected = index == selectedIndex;
    // 이 칩을 지금 누를 수 있나. 선택된 칩은 "이미 고른 것"이라 petrol 채움을 유지하고,
    // 못 누르는 다른 칩(로딩 중·지난 턴)은 흐린 색으로 갈라 준다 — review: 지난 턴 칩이
    // 활성 칩과 똑같이 petrol 테두리로 보이는데 눌러도 아무 일이 없어, 사용자가 앱이
    // 고장난 줄 알고 반복 탭하게 된다(Flutter 기본 disabledColor 는 배경만 흐리게 하고
    // 여기서 하드코딩한 side·labelStyle 은 그대로 남는다).
    final tappable = onTap != null && !isSelected;
    final outline = isSelected || tappable ? AppColors.brandPetrol : AppColors.inkMuted;
    return ChoiceChip(
      key: ValueKey('clarify_chip_${index}_$chip'),
      label: Text(chip),
      avatar:
          isSelected ? const Icon(Icons.check, size: 16, color: AppColors.onPetrol) : null,
      selected: isSelected,
      showCheckmark: false, // 위 avatar 아이콘이 체크 표시를 대신한다(중복 방지).
      backgroundColor: Colors.transparent,
      selectedColor: AppColors.brandPetrol,
      side: BorderSide(color: outline),
      labelStyle: TextStyle(color: isSelected ? AppColors.onPetrol : outline),
      shape: const StadiumBorder(),
      // 이미 선택된 칩은 다시 눌러도 반응하지 않는다(탭 하나만 유효).
      onSelected: tappable ? (_) => onTap!(index) : null,
    );
  }
}
