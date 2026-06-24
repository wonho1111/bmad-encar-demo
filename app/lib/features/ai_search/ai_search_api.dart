// AI 검색 호출 클라이언트(FR12·7.2) — 앱이 FastAPI /ai/search 를 부르는 유일한 통로.
// web lib/api/aiSearch.ts 와 "동일한 계약"을 Flutter 로 이식한다(요청/응답·헤더·에러).
//
// 백엔드 계약(api/app/schemas/ai.py·routers/ai.py):
//   POST {API_BASE_URL}/ai/search
//   headers: Authorization: Bearer <supabase access_token>, Content-Type: application/json
//   body:    { query, context? }    // context = 직전 대화(멀티턴, 최대 12턴)
//   200:     { answer, listings[] } // listings 원소 = 매물카드 7필드
//   비200:   { error: { code, message } }  // 401·400·422·500·503 등 공통 포맷
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/supabase/env.dart';
import '../listings/listing.dart';

/// 멀티턴 대화 한 턴(FR18). 서버 ConversationTurn 과 동일(role + content).
class ConversationTurn {
  const ConversationTurn({required this.role, required this.content});

  final String role; // 'user' | 'assistant'
  final String content;

  Map<String, String> toJson() => {'role': role, 'content': content};
}

/// /ai/search 200 응답. listings 는 매물카드(ListingCardData) 배열.
class SearchResult {
  const SearchResult({required this.answer, required this.listings});

  final String answer;
  final List<ListingCardData> listings;
}

/// AI 검색 실패를 한국어 메시지로 감싸는 예외(화면은 message 만 보여주면 됨 — fail-loud).
class AiSearchException implements Exception {
  const AiSearchException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// 끝 슬래시를 정규화한 API 주소. 누락 시 "무엇이 비었는지" 한국어로 알린다(web getApiBaseUrl 철학).
String _apiBaseUrl() {
  final base = SupabaseEnv.apiBaseUrl;
  if (base.isEmpty) {
    throw const AiSearchException(
      'AI 검색 서버 주소(API_BASE_URL)가 설정되지 않았습니다. 빌드 시 '
      '--dart-define 또는 --dart-define-from-file 로 값을 넣어주세요 (app/.env.example 참고).',
    );
  }
  // 'http://x:8000/' + '/ai/search' 가 이중 슬래시가 되지 않도록 끝 슬래시 제거.
  return base.replaceAll(RegExp(r'/+$'), '');
}

/// 자연어 질의를 AI 검색 API 로 보내고 {answer, listings} 를 받는다.
/// 토큰이 없거나 비200이면 한국어 메시지를 담은 AiSearchException 을 던진다(조용한 실패 금지).
Future<SearchResult> searchAi({
  required String query,
  List<ConversationTurn>? context,
  required String? accessToken,
}) async {
  if (accessToken == null || accessToken.isEmpty) {
    // 세션 만료 등으로 토큰이 없을 수 있어 방어(어차피 서버가 401).
    throw const AiSearchException('로그인이 필요합니다. 다시 로그인한 뒤 시도해주세요.');
  }

  final url = Uri.parse('${_apiBaseUrl()}/ai/search');
  // context 가 있으면 동봉, 없으면 키 자체를 빼서 단일턴으로 보낸다(서버 기본값 None 과 동일).
  final body = <String, Object?>{
    'query': query,
    if (context != null && context.isNotEmpty)
      'context': context.map((t) => t.toJson()).toList(),
  };

  http.Response res;
  try {
    res = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer $accessToken',
      },
      body: jsonEncode(body),
    );
  } catch (_) {
    // 네트워크 자체 실패(API 미기동·끊김). 원인 대신 일반 안내.
    throw const AiSearchException('AI 검색 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.');
  }

  if (res.statusCode < 200 || res.statusCode >= 300) {
    throw AiSearchException(_extractErrorMessage(res));
  }

  // 200 — 응답 형태가 깨졌으면 일반 에러로.
  Object? data;
  try {
    data = jsonDecode(utf8.decode(res.bodyBytes));
  } catch (_) {
    throw const AiSearchException('AI 검색 응답을 해석하지 못했습니다. 잠시 후 다시 시도해주세요.');
  }
  return parseSearchResult(data);
}

/// 200 응답 본문(이미 디코드된 객체) → SearchResult.
/// listings 는 카드 7필드 가드(ListingCardData.fromMap)로 걸러 깨진 원소를 버린다.
/// 순수 함수로 분리 — 단위 테스트가 네트워크 없이 응답 파싱을 검증한다.
SearchResult parseSearchResult(Object? data) {
  if (data is! Map) {
    return const SearchResult(answer: '', listings: []);
  }
  final answer = data['answer'];
  final rawListings = data['listings'];
  final listings = <ListingCardData>[];
  if (rawListings is List) {
    for (final item in rawListings) {
      final card = ListingCardData.fromMap(item);
      if (card != null) listings.add(card); // 깨진 원소는 버린다(web isValidListing 동일).
    }
  }
  return SearchResult(
    answer: answer is String ? answer : '',
    listings: listings,
  );
}

/// 비200 응답에서 한국어 에러 메시지를 뽑는다. 공통 포맷({error:{code,message}})이면 그 message,
/// 아니면 상태코드별 일반 문구로 폴백(web extractErrorMessage 이식).
String _extractErrorMessage(http.Response res) {
  try {
    final data = jsonDecode(utf8.decode(res.bodyBytes));
    if (data is Map) {
      final error = data['error'];
      if (error is Map) {
        final message = error['message'];
        if (message is String && message.trim().isNotEmpty) return message;
      }
    }
  } catch (_) {
    // JSON 파싱 실패 — 아래 상태코드 폴백.
  }
  final status = res.statusCode;
  if (status == 401) return '로그인이 필요합니다. 다시 로그인한 뒤 시도해주세요.';
  if (status == 400) return '요청을 처리할 수 없습니다. 질문을 바꿔 다시 시도해주세요.';
  if (status == 422) return '질문 형식이 올바르지 않습니다. 다시 입력해주세요.';
  if (status >= 500) return 'AI 검색 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
  return 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.';
}
