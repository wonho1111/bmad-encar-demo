// `listingDetailColumns`(listings_repository.dart) 단위테스트 — Story 16.3 코드리뷰 지적.
// `fetchListing`(구매자 상세)·`fetchOwnListing`(본인 상세)이 공유하는 select 컬럼 문자열이다.
// 이전엔 두 메서드에 문자열이 각각 리터럴로 있었고, 그 문자열에서 신뢰속성 3컬럼
// (`accident_status`·`is_single_owner`·`is_non_smoker`)을 지워도 `ListingDetail.fromMap`이
// 조용히 null로 받아 상세 화면의 신뢰속성 섹션(AC2)만 안 뜰 뿐 스위트는 계속 green이었다 —
// 두 select 문자열을 직접 보는 테스트가 하나도 없었기 때문이다. 이제 상수 하나로 합쳐
// `@visibleForTesting`으로 노출했으니 그 상수 자체를 여기서 직접 단언한다.
import 'dart:io';

import 'package:app/features/listings/listings_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test(
      'listingDetailColumns(authed: true) — 신뢰속성 3컬럼(accident_status·is_single_owner·is_non_smoker)을 포함한다',
      () {
    expect(listingDetailColumns(), contains('accident_status'));
    expect(listingDetailColumns(), contains('is_single_owner'));
    expect(listingDetailColumns(), contains('is_non_smoker'));
  });

  // spec-16-6 인수 경위(실기기 실측) — anon(비로그인)이 신뢰속성 3컬럼을 select하면
  // `42501 permission denied`로 select **전체**가 실패한다(0011 GRANT 화이트리스트 밖).
  // 상세도 `/home`에서 push로 열려 anon이 닿을 수 있으므로(spec-16-6 FR58) 같은 방어가 필요.
  // ✎ 2026-08-13 — 계약이 뒤집혔다(0037 GRANT로 anon도 신뢰속성을 읽는다). 자세한 경위는
  // listings_repository_card_columns_test.dart의 같은 자리 주석 참조.
  test('listingDetailColumns — 로그인 여부와 무관하게 신뢰속성 3컬럼을 항상 포함한다(0037)', () {
    final cols = listingDetailColumns();
    for (final col in ['accident_status', 'is_single_owner', 'is_non_smoker']) {
      expect(cols, contains(col),
          reason: '$col이 빠지면 비로그인 상세에서 그 뱃지가 통째로 사라진다');
    }
    // accident_free(신뢰속성과 별개, NOT NULL bool)는 anon에게도 공개된 컬럼이라 그대로 남아야 한다.
    expect(cols, contains('accident_free'));
  });

  // 코드리뷰 지적(P11) — 위 테스트는 "상수 내용"만 본다. `fetchListing`·`fetchOwnListing`이
  // 실제로 이 상수를 쓰는지는 안 본다 — 둘 중 하나가 리터럴 select 문자열로 되돌아가도(예:
  // 신뢰속성 3컬럼이 빠진 채) 위 테스트는 계속 green이다. 이 리포에 Supabase 쿼리를 가로채는
  // 가짜(fake)가 없어(다른 레포지토리 테스트들도 순수 처리부만 단위테스트한다, 파일 상단 주석
  // 참조) 실행 경로로 확인할 수 없다 — 대신 소스 텍스트를 직접 읽어 두 메서드 본문에
  // `listingDetailColumns` 식별자가 실제로 등장하는지 확인한다(app_theme_color_drift_test.dart와
  // 같은 방식: flutter test의 cwd = app/).
  test(
      'listingDetailColumns가 fetchListing·fetchOwnListing 본문에서 실제로 참조된다'
      '(코드리뷰 지적 P11 — 상수 내용만으로는 "안 쓰고 리터럴로 되돌아감" 회귀를 못 잡는다)', () {
    final file = File('lib/features/listings/listings_repository.dart');
    expect(file.existsSync(), isTrue,
        reason: 'flutter test의 cwd가 app/가 아닐 수 있다(app_theme_color_drift_test.dart와 동일 전제)');
    final content = file.readAsStringSync();

    final fetchListingStart =
        content.indexOf('Future<ListingDetail?> fetchListing(String id) async {');
    final fetchOwnListingStart =
        content.indexOf('Future<ListingDetail?> fetchOwnListing(');
    expect(fetchListingStart, greaterThanOrEqualTo(0),
        reason: 'fetchListing 시그니처를 못 찾았다(이름/시그니처가 바뀌었을 수 있다)');
    expect(fetchOwnListingStart, greaterThan(fetchListingStart),
        reason: 'fetchOwnListing 시그니처를 못 찾았다');

    // 본문 시작은 각 시그니처의 `async {`부터다 — fetchOwnListing은 파라미터 목록이 여러 줄로
    // 꺾여 있어(`String id, {\n    required String sellerId,\n  }) async {`) 그 파라미터
    // 목록을 닫는 "  })"도 "\n  }"를 포함한다. 시그니처 시작점부터 바로 찾으면 그 파라미터
    // 닫는 자리에서 잘못 멈춘다 — `async {` 뒤부터 찾아야 실제 메서드 본문만 잡힌다. 본문은
    // 클래스 멤버 들여쓰기(2칸)로 닫힌다 — 본문 안의 try/catch·if 등 중첩 블록은 더 깊이
    // 들여써져 있어 "\n  }"(줄바꿈+공백 2개+닫는 중괄호)와 매치되지 않는다.
    final fetchListingBodyStart =
        content.indexOf('async {', fetchListingStart) + 'async {'.length;
    final fetchOwnListingBodyStart =
        content.indexOf('async {', fetchOwnListingStart) + 'async {'.length;
    final fetchListingEnd = content.indexOf('\n  }', fetchListingBodyStart);
    final fetchOwnListingEnd = content.indexOf('\n  }', fetchOwnListingBodyStart);
    expect(fetchListingEnd, greaterThan(fetchListingBodyStart));
    expect(fetchOwnListingEnd, greaterThan(fetchOwnListingBodyStart));

    final fetchListingBody = content.substring(fetchListingBodyStart, fetchListingEnd);
    final fetchOwnListingBody =
        content.substring(fetchOwnListingBodyStart, fetchOwnListingEnd);

    // spec-16-6 후속 리뷰(verification-gap 렌즈, 실측 확인) — 식별자만 찾으면
    // `listingDetailColumns()`로 하드코딩해도(이번에 고친 것과 똑같은 anon 42501 회귀) 계속
    // 통과한다. 실제로 `(_authed)` 인자가 배선됐는지까지 소스텍스트로 단언한다.
    final wiredPattern = RegExp(r'listingDetailColumns\(\)');
    expect(wiredPattern.hasMatch(fetchListingBody), isTrue,
        reason: 'fetchListing이 listingDetailColumns()로 호출하지 않는다 — '
            '리터럴 true로 하드코딩되면 anon 상세 조회가 42501로 다시 전체 실패한다');
    expect(wiredPattern.hasMatch(fetchOwnListingBody), isTrue,
        reason: 'fetchOwnListing이 listingDetailColumns()로 호출하지 않는다');

    // 파일 전체에서 'accident_free' 리터럴이 listingDetailColumns 선언 1곳에만 있어야 한다 —
    // 다른 자리(예: 위 두 메서드 중 하나가 리터럴 select 문자열로 되돌아간 경우)에 또
    // 나타나면 신뢰속성 컬럼이 상수 밖에 인라인됐다는 뜻이다.
    // ✎ 2026-08-13 — **주석은 빼고 센다.** 이 단언은 "select 리터럴이 상수 밖에 인라인됐나"를
    //   보는 건데, 소스 텍스트를 그대로 세면 컬럼 이름을 **설명하는 주석**까지 위반으로 잡는다
    //   (실제로 신뢰속성 필터를 설명하는 주석 한 줄 때문에 red가 났다 — 코드는 멀쩡했다).
    //   검사가 잡아야 할 것은 코드지 주석이 아니다.
    final codeOnly =
        content.split('\n').where((l) => !l.trimLeft().startsWith('//')).join('\n');
    final accidentFreeOccurrences = 'accident_free'.allMatches(codeOnly).length;
    expect(accidentFreeOccurrences, 1,
        reason: "'accident_free' 문자열이 listingDetailColumns 선언 1곳 밖에서도 발견됐다 — "
            '다른 .select(...) 리터럴에 신뢰속성 컬럼이 다시 인라인됐을 수 있다');
  });
}
