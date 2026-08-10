// FR11(판매완료 비노출)이 **실제로 나가는 요청**에 걸려 있는지 본다 — 2026-08-10 Epic 16
// 묶음 코드리뷰(verification-gap) 발견.
//
// ## 왜 이 파일이 따로 필요한가
//
// 지금까지 FR11을 지키던 유일한 검사는 `listings_repository_card_columns_test.dart`의
// **소스 텍스트 매칭**이었다: `expect(fetchPopularListingsBody, contains('_buyerQuery'))`.
// 함수 본문 문자열에 `_buyerQuery`라는 **글자**가 있는지만 보므로,
//
//   - `_buyerQuery` 호출을 지우고 **주석에 그 식별자만 남겨도** 통과하고,
//   - `.eq('status', ...)`의 인자를 다른 값으로 바꿔도 통과하며,
//   - 애초에 "sold가 실제로 빠지는가"는 어느 층에서도 확인하지 않았다.
//
// 이 파일은 대신 **HTTP 경계에서 실제 쿼리스트링**을 본다(같은 리포의
// `listings_repository_delete_test.dart`·`chat_repository_test.dart`가 이미 쓰는 기법).
// 소스에 무슨 글자가 있든 상관없이, PostgREST로 나가는 URL에 `status=eq.on_sale`이
// 실려야만 통과한다.
//
// ## 이 검사가 보지 못하는 것 (추측 아니라 명시)
//
//   - **서버가 정말 sold를 거르는지**는 안 본다. 그건 DB 몫이고(`0002_listings.sql` RLS +
//     `0011_listings_anon_select.sql` GRANT), 여기선 클라가 필터를 **보냈는지**만 증명한다.
//     둘 다 필요하다 — 클라가 안 보내면 anon에게도 sold가 보이고, DB가 안 막으면 다른
//     클라이언트가 뚫는다(§6 "새 조회 경로를 추가하면 강제 지점 목록에 함께 등록").
//   - 커버사진 부착·정렬·건수 계약은 다른 테스트 몫이다.
import 'dart:convert';

import 'package:app/features/listings/listing_filters.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:supabase_flutter/supabase_flutter.dart';

/// 경로만 기록하는 기존 fake와 달리 **전체 URL(쿼리스트링 포함)** 을 남긴다 — 이 파일이
/// 증명하려는 것이 바로 그 쿼리스트링이라서다.
class _UrlCapturingHttpClient extends http.BaseClient {
  final List<String> urls = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    urls.add('${request.method} ${request.url}');
    final body = request.url.path.contains('/rest/v1/listing_images')
        ? <dynamic>[]
        : <dynamic>[]; // 어느 경로든 빈 목록으로 성공 — 이 파일은 요청만 본다.
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      200,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

void main() {
  // ⚠️ **기대값을 `buyerVisibleStatus`에서 가져오지 않는다 — 리터럴 `'on_sale'`을 박는다.**
  // 2026-08-10 후속 코드리뷰(verification-gap)가 실측으로 잡은 결함: 처음엔 이 파일이
  // `contains('status=eq.$buyerVisibleStatus')`로 단언했는데, 그러면 **기대값을 피검사 대상에서
  // 다시 계산**하는 꼴이라 상수 자체가 'sold' 따위로 바뀌면 요청과 기대가 **함께** 바뀌어
  // 세 테스트 모두 계속 green이었다. 이 리포엔 같은 실패 모드의 실측 전례가 있다
  // ("자기일관 단언은 절대 실패하지 않는다"). 그래서 두 축으로 나눈다:
  //   ① 아래 상수 스냅샷 — 값 자체가 바뀌면 여기서 먼저 red
  //   ② 각 테스트 — 나가는 URL에 리터럴 'on_sale'이 실렸는지
  const expectedStatus = 'on_sale'; // FR11이 허용하는 유일한 구매자 노출 상태(리터럴, 의도적)

  test('FR11 상수 스냅샷 — buyerVisibleStatus가 조용히 바뀌면 여기서 먼저 걸린다', () {
    expect(buyerVisibleStatus, expectedStatus,
        reason: 'FR11의 단일 출처가 바뀌었다. 바꾸는 것이 의도였다면 이 스냅샷과 '
            'docs/conventions.md §6의 강제 지점 목록을 함께 고쳐야 한다 — '
            '값만 바꾸고 지나가면 구매자에게 sold가 새거나 정상 매물이 사라진다.');
  });

  late _UrlCapturingHttpClient fakeHttp;
  late SupabaseClient client;

  setUp(() {
    fakeHttp = _UrlCapturingHttpClient();
    client = SupabaseClient(
      'https://example.supabase.co',
      'test-anon-key-not-real',
      httpClient: fakeHttp,
    );
  });

  tearDown(() => client.dispose());

  /// `listings` 테이블로 나간 요청만 골라낸다(`listing_images` 커버사진 조회는 제외).
  List<String> listingsRequests() => fakeHttp.urls
      .where((u) => u.contains('/rest/v1/listings?') || u.contains('/rest/v1/listings&'))
      .toList();

  test('fetchListings — 나가는 URL에 status=eq.on_sale이 실린다(FR11)', () async {
    final repo = ListingsRepository(client: client);
    await repo.fetchListings(const ResolvedFilters());

    final reqs = listingsRequests();
    expect(reqs, isNotEmpty, reason: 'listings 조회 요청 자체가 안 나갔다');
    for (final u in reqs) {
      expect(u, contains('status=eq.$expectedStatus'),
          reason: 'FR11: 구매자 조회 경로는 판매중 상태만 요청해야 한다 — 이 URL엔 그 필터가 없다: $u');
    }
  });

  test('fetchPopularListings — 나가는 URL에 status=eq.on_sale이 실린다(FR11, spec-16-8이 새로 연 경로)',
      () async {
    final repo = ListingsRepository(client: client);
    await repo.fetchPopularListings();

    final reqs = listingsRequests();
    expect(reqs, isNotEmpty);
    for (final u in reqs) {
      expect(u, contains('status=eq.$expectedStatus'),
          reason: 'FR11: "지금 인기"도 예외가 아니다 — 경로를 열고 필터를 잊는 것이 이 규칙의 '
              '유일한 실패 모드다(conventions.md §6): $u');
    }
  });

  test('fetchListing(단건 상세) — 나가는 URL에 status=eq.on_sale이 실린다(FR11)', () async {
    final repo = ListingsRepository(client: client);
    await repo.fetchListing('listing-1');

    final reqs = listingsRequests();
    expect(reqs, isNotEmpty);
    for (final u in reqs) {
      expect(u, contains('status=eq.$expectedStatus'),
          reason: 'FR11: 딥링크로 sold 매물 id를 직접 열어도 나와선 안 된다: $u');
    }
  });
}
