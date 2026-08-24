// AI 채팅의 대화 한 줄 + context 직렬화(멀티턴, FR18). web ChatAssistant 의 ChatMessage/buildContext 이식.
// 대화는 화면 상태에만 존재(무상태) — 새로 열면 초기화. 후속 질의에 직전 대화를 context 로 동봉한다.
import '../listings/listing.dart';
import 'ai_search_api.dart';

// context 입력 계약(단일 출처: api/app/schemas/ai.py). 서버 강제값을 클라에서 미리 지켜 422 자초 방지.
// ⚠️ 이 "단일 출처" 문구는 아래 두 상수에만 적용된다 — maxQueryLength 는 의도적으로 서버와 다르다.
const int maxContextTurns = 12; // 최근 12턴만 동봉
const int maxContentLength = 2000; // 각 턴 content 최대 2000자

// ⚠️ 여기부터는 서버 계약이 아니라 **클라 UX 상한**이다(위 "단일 출처"의 예외 — 서버 값으로
// 되돌리지 말 것). 질의 최대 500자: 서버 하드 상한(1000, api/app/schemas/ai.py)보다 엄격하며,
// web HeroSearch.tsx(MAX_QUERY_LENGTH=500)가 이미 쓰는 값이자 EXPERIENCE.md·epics AC가 명시한
// 값이다(spec-16-5 Design Notes — 웹 ChatAssistant.tsx가 아직 1000을 쓰는 것은 그쪽의 미해결
// 드리프트이지 이 값이 따라야 할 정본이 아니다).
// 세는 단위는 **그래핑(사용자가 보는 글자)** 이다 — TextField.maxLength 와 같은 단위로 세야
// 카운터가 "500/500"인데 전송은 막히는 모순이 안 생긴다(review: 이모지 등 UTF-16 2코드유닛
// 문자에서 String.length 와 갈라진다).
const int maxQueryLength = 500;

/// 화면에 쌓이는 대화 한 줄. assistant 턴만 매물카드(listings)·되묻기 칩(clarify)을 가질 수 있다.
class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.content,
    this.listings = const [],
    this.clarify,
    this.usedChipIndex,
  });

  final String role; // 'user' | 'assistant'
  final String content; // user=질의, assistant=answer
  final List<ListingCardData> listings; // assistant 답변에 딸린 매물카드(없으면 빈 목록)
  // 되묻기 페이로드(assistant 턴만, Story 16.5) — null이면 되묻기 칩을 그리지 않는다.
  final ClarifyPayload? clarify;
  // 이 메시지의 되묻기 칩 중 실제로 탭된 칩의 **인덱스**(없으면 null) — 코드리뷰 지적:
  // 되묻기 행이 최신 메시지가 아니게 돼(잠긴 뒤에도) 무엇을 탭했는지 스크롤백에서 알 수
  // 있어야 한다("선택됨" 표시, EXPERIENCE.md "petrol 채움 선택됨 상태로 전환").
  // ⚠️ 문자열이 아니라 인덱스로 기억한다 — 문자열로 비교하면 서버가 같은 칩 문자열을 둘
  // 보냈을 때 하나를 탭한 것만으로 **모든 동일 문자열 칩이 선택·비활성**이 된다(review 실측:
  // chips ['SUV','SUV','세단']에서 첫 칩 탭 → selected 플래그가 [true, true, false]).
  // 칩 위젯 Key가 이미 인덱스로 중복을 가르고 있으므로 선택 판정도 같은 기준을 쓴다.
  final int? usedChipIndex;

  bool get isUser => role == 'user';

  /// 탭된 칩 인덱스를 갈아 끼운 사본. `null`을 주면 표시를 지운다 — 칩 탭 전송이 실패했을 때
  /// 되돌리는 용도다(review: 실패한 칩이 "선택됨"으로 굳으면 영영 다시 못 누른다).
  /// ⚠️ Dart 관례의 `copyWith`(`?? this.x`)로 두지 않는다 — 그 형태는 null 로 되돌릴 수 없어
  /// 지우기용 메서드를 하나 더 만들어야 했고, 전 필드를 두 번 나열하게 돼 나중에 필드가
  /// 늘면 한쪽이 조용히 그 필드를 떨군다(review).
  ChatMessage withUsedChipIndex(int? index) => ChatMessage(
        role: role,
        content: content,
        listings: listings,
        clarify: clarify,
        usedChipIndex: index,
      );
}

/// 화면 대화 → 서버로 보낼 context(턴 배열). web buildContext 이식.
///   - 빈(공백뿐) 턴 제거(서버 min_length=1 위반 → 다음 질의 통째 422 방지).
///   - 최근 maxContextTurns 개만, 각 content 는 maxContentLength 로 절단.
///   - 매물카드는 제외(서버 스키마 = role+content).
List<ConversationTurn> buildContext(List<ChatMessage> messages) {
  return messages
      .where((m) => m.content.trim().isNotEmpty)
      .toList()
      .reversed
      .take(maxContextTurns) // 뒤에서 N개
      .toList()
      .reversed
      .map((m) => ConversationTurn(
            role: m.role,
            content: m.content.length > maxContentLength
                ? m.content.substring(0, maxContentLength)
                : m.content,
          ))
      .toList();
}
