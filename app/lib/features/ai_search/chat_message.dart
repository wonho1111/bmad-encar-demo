// AI 채팅의 대화 한 줄 + context 직렬화(멀티턴, FR18). web ChatAssistant 의 ChatMessage/buildContext 이식.
// 대화는 화면 상태에만 존재(무상태) — 새로 열면 초기화. 후속 질의에 직전 대화를 context 로 동봉한다.
import '../listings/listing.dart';
import 'ai_search_api.dart';

// context 입력 계약(단일 출처: api/app/schemas/ai.py). 서버 강제값을 클라에서 미리 지켜 422 자초 방지.
const int maxContextTurns = 12; // 최근 12턴만 동봉
const int maxContentLength = 2000; // 각 턴 content 최대 2000자
const int maxQueryLength = 1000; // 질의 최대 1000자

/// 화면에 쌓이는 대화 한 줄. assistant 턴만 매물카드(listings)를 가질 수 있다.
class ChatMessage {
  const ChatMessage({
    required this.role,
    required this.content,
    this.listings = const [],
  });

  final String role; // 'user' | 'assistant'
  final String content; // user=질의, assistant=answer
  final List<ListingCardData> listings; // assistant 답변에 딸린 매물카드(없으면 빈 목록)

  bool get isUser => role == 'user';
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
