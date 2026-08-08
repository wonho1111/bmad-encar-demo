// AI 검색 호출 클라이언트(FR12·7.2) — 앱이 FastAPI /ai/search 를 부르는 유일한 통로.
// web lib/api/aiSearch.ts 와 "동일한 계약"을 Flutter 로 이식한다(요청/응답·헤더·에러).
//
// 백엔드 계약(api/app/schemas/ai.py·routers/ai.py):
//   POST {API_BASE_URL}/ai/search
//   headers: Authorization: Bearer <supabase access_token>, Content-Type: application/json
//   body:    { query, context? }    // context = 직전 대화(멀티턴, 최대 12턴)
//   200:     { answer, listings[], clarify, narrowed_by } // listings 원소 = 매물카드 7필드
//                                            // clarify = 되묻기 페이로드 또는 null(FR46, docs/conventions.md §4)
//                                            // narrowed_by = REJECT 전용 고정 상수 또는 null(파싱만, 미렌더 — Story 16.5 Never)
//   비200:   { error: { code, message } }  // 401·400·422·500·503 등 공통 포맷
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../core/supabase/env.dart';
import '../../core/supabase/storage_helper.dart';
import '../listings/listing.dart';
import '../listings/listing_images_bucket.dart';

/// 멀티턴 대화 한 턴(FR18). 서버 ConversationTurn 과 동일(role + content).
class ConversationTurn {
  const ConversationTurn({required this.role, required this.content});

  final String role; // 'user' | 'assistant'
  final String content;

  Map<String, String> toJson() => {'role': role, 'content': content};
}

/// /ai/search 200 응답. listings 는 매물카드(ListingCardData) 배열.
class SearchResult {
  const SearchResult({
    required this.answer,
    required this.listings,
    this.clarify,
    this.narrowedBy,
  });

  final String answer;
  final List<ListingCardData> listings;
  // 되묻기 페이로드(FR46, Story 13.4) — 서버가 CLARIFY 경로를 타고 상한(3턴) 이내일 때만
  // 채워진다. 그 외(다른 라우트, 또는 상한 초과 강제 폴백)는 null — 칩 미표시의 유일한 신호다
  // (spec-16-5 Always, 클라 자체 카운터를 두지 않는다).
  final ClarifyPayload? clarify;
  // REJECT 전용 고정 상수 사유 술어 배열(FR47, Story 13.5). 파싱만 하고 화면에 렌더하지
  // 않는다(spec-16-5 Never — 원시 술어 문자열이라 사람이 읽을 텍스트가 아님, 대장 DW-597).
  final List<String>? narrowedBy;
}

/// 되묻기 페이로드(FR46, Story 13.4) — `question`(되묻는 문장) + `chips`(탭 가능한 후보 문자열).
class ClarifyPayload {
  const ClarifyPayload({required this.question, required this.chips});

  final String question;
  final List<String> chips;
}

/// wire 의 `clarify` 가 실제로 계약 형태(`question`: 문자열, `chips`: 문자열 배열)인지 확인해
/// 파싱한다. 형태가 깨지면(필드 누락·타입 불일치) null 로 폴백한다 — answer/listings 파싱은
/// 이 실패와 무관하게 계속 진행된다(web `isValidClarify` 기반, aiSearch.ts 48~56행).
///
/// ⚠️ 웹과 **한 겹 다르다**(review — "미러"라고만 적어두면 다음 사람이 동일하다고 믿는다):
/// 웹은 칩 원소의 타입만 보지만 여기선 공백뿐인 칩도 형태 불량으로 본다. 앱은 칩이 탭 대상이라
/// 빈 라벨 칩이 그려지면 눌러도 `_submit` 이 조용히 return 하는 "죽은 칩"이 되기 때문이다.
/// 서버 계약상(`clarify_node.py` 고정 3개) 도달하지 않는 상태라 웹과의 이 차이는 실동작에
/// 영향이 없다.
ClarifyPayload? parseClarifyPayload(Object? value) {
  if (value is! Map) return null;
  final question = value['question'];
  final rawChips = value['chips'];
  if (question is! String) return null;
  if (rawChips is! List) return null;
  final chips = <String>[];
  for (final chip in rawChips) {
    // 원소 하나라도 문자열이 아니거나 공백뿐이면(탭해도 반응 없는 죽은 칩이 되므로) 형태
    // 불량으로 전체 폐기(review — 부분 정상 chips만 살리지 않는다, 다른 형태 위반과 동일 규칙).
    if (chip is! String || chip.trim().isEmpty) return null;
    chips.add(chip);
  }
  return ClarifyPayload(question: question, chips: chips);
}

/// wire 의 `narrowed_by` 가 실제로 계약 형태(비어있지 않은 문자열 배열)인지 확인해 파싱한다.
/// 빈 배열(`[]`)은 "채워진 값"이 아니라 null 과 동일 취급한다 — 서버 계약상 narrowed_by 가
/// 채워지면 항상 고정 3개다(web `isValidNarrowedBy` 미러, aiSearch.ts 58~66행,
/// docs/conventions.md §4).
///
/// ⚠️ 빈 배열을 **신고하지는 않는다**(review — 이전 주석은 "wire/스키마 버그 신호"라고 적어
/// 검사가 있는 것처럼 읽혔지만, 누락·빈배열·형태불량이 전부 같은 null 로 합쳐질 뿐 로그도
/// assert 도 없다). 소비처가 없는 필드(spec-16-5 Never: 파싱하되 렌더하지 않는다)에 관측
/// 장치를 다는 건 과하다고 판단해, 주석을 코드 사실에 맞춰 낮춘다(CLAUDE.md B9 — 주석이
/// 계약인 척하지 않게).
List<String>? parseNarrowedBy(Object? value) {
  if (value is! List || value.isEmpty) return null;
  final result = <String>[];
  for (final item in value) {
    if (item is! String) return null;
    result.add(item);
  }
  return result;
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
///
/// api(`api/app/schemas/ai.py`)는 `image_url`을 채우지 않는다 — `image_path`(버킷 상대 경로)만
/// 보낸다(api는 URL을 만들지 않는다, listing.dart 53~68행 주석 참조: 변환은 "응답 매핑 계층에서
/// 한 번, 렌더 시점이 아니다"). 그래서 여기서 `image_path` → 공개 URL로 바꿔 `image_url` 자리에
/// 넣고, 경로 자체는 `fromMap`에 넘기지 않는다(web `resolveCardImage`의 미러) — 안 그러면 카드가
/// 항상 "사진 준비중" 플레이스홀더 위에 모순되게 "N장" 배지를 얹는다.
///
/// [imageUrlBuilder]: 기본은 `getPublicUrl`(전역 `supabase` 인스턴스 필요)이지만, 단위 테스트는
/// `supabase`를 초기화하지 않으므로 가짜 빌더를 주입할 수 있게 시접(seam)을 열어둔다.
/// 순수 함수로 분리 — 단위 테스트가 네트워크 없이 응답 파싱을 검증한다.
SearchResult parseSearchResult(
  Object? data, {
  String Function(String path)? imageUrlBuilder,
}) {
  if (data is! Map) {
    return const SearchResult(answer: '', listings: []);
  }
  final buildUrl =
      imageUrlBuilder ?? ((p) => getPublicUrl(listingImagesBucket, p));
  final answer = data['answer'];
  final rawListings = data['listings'];
  final listings = <ListingCardData>[];
  if (rawListings is List) {
    for (final item in rawListings) {
      if (item is! Map) continue; // fromMap도 걸러내지만 image_path 변환 전에 먼저 배제.
      final rawPath = item['image_path'];
      final path = rawPath is String ? rawPath.trim() : '';
      final url = path.isEmpty ? null : buildUrl(path);
      final rawCount = asInt(item['image_count']) ?? 0;
      final mapped = {...item}..remove('image_path'); // 카드는 image_url만 안다(경로는 버린다).
      mapped['image_url'] = url;
      // "url 없으면 count도 0" 강제는 여기서 하지 않는다 — `ListingCardData.fromMap`이 모든
      // 생산자를 대신해 그 규칙을 지킨다(listing.dart 참조). 여기서는 음수 방어만 남긴다.
      mapped['image_count'] = rawCount < 0 ? 0 : rawCount;
      final card = ListingCardData.fromMap(mapped);
      if (card != null) listings.add(card); // 깨진 원소는 버린다(web isValidListing 동일).
    }
  }
  return SearchResult(
    answer: answer is String ? answer : '',
    listings: listings,
    clarify: parseClarifyPayload(data['clarify']),
    narrowedBy: parseNarrowedBy(data['narrowed_by']),
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
