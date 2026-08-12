// `listingCardColumns`(listings_repository.dart) 단위테스트 — 후속 코드리뷰(spec-16-8 2차
// 리뷰 P4). `fetchListings`(매물 탐색)·`fetchPopularListings`(홈 "지금 인기")가 공유하는
// select 컬럼 문자열이다. `listings_repository_detail_columns_test.dart`(listingDetailColumns)
// 와 같은 선례 — 두 메서드가 각자 리터럴로 들고 있으면 카드 필드가 한쪽에만 반영되고도
// 스위트가 계속 green일 수 있다. 상수 하나로 합쳐 그 상수 자체와, 두 메서드가 실제로 그
// 상수를 참조하는지, 그리고 fetchPopularListings의 FR11 강제 지점(`_buyerQuery`)·정렬·건수
// 계약(AC3)을 여기서 직접 단언한다.
import 'dart:io';

import 'package:app/features/listings/listings_repository.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('listingCardColumns(authed: true) — 카드 12필드를 포함한다', () {
    for (final col in [
      'id',
      'manufacturer',
      'model',
      'year',
      'price',
      'mileage',
      'region',
      'seller_name',
      'fuel',
      'accident_status',
      'is_single_owner',
      'is_non_smoker',
      'options',
    ]) {
      expect(listingCardColumns(), contains(col), reason: '$col 컬럼이 빠지면 카드에서 그 필드가 사라진다');
    }
  });

  // ✎ 2026-08-13 — 계약이 **뒤집혔다.** 예전엔 anon이 신뢰속성 3컬럼을 select하면 42501로
  // select 전체가 죽어서(실기기 실측) anon 조회에선 그 3컬럼을 빼야 했다.
  // `0037_listings_anon_trust_columns.sql`이 GRANT를 열어(사용자 승인, 운영 적용 완료) 이제
  // **로그인 여부와 무관하게 항상** 조회한다 — 그전엔 비로그인 앱 사용자에게 신뢰 뱃지가
  // 한 번도 안 떴다. 분기 자체가 사라졌으므로 "anon은 빼야 한다"는 반대 단언도 함께 지운다.
  test('listingCardColumns — 로그인 여부와 무관하게 신뢰속성 3컬럼을 항상 포함한다(0037)', () {
    final cols = listingCardColumns();
    for (final col in ['accident_status', 'is_single_owner', 'is_non_smoker']) {
      expect(cols, contains(col),
          reason: '$col이 빠지면 비로그인 화면에서 그 뱃지가 통째로 사라진다');
    }
    // 나머지 9필드는 anon에게도 열려 있으므로(0011) 그대로 남아야 한다.
    for (final col in [
      'id',
      'manufacturer',
      'model',
      'year',
      'price',
      'mileage',
      'region',
      'seller_name',
      'fuel',
      'options',
    ]) {
      expect(cols, contains(col), reason: '$col은 anon에게도 공개된 컬럼이라 빠지면 안 된다');
    }
  });

  // listingDetailColumns 선례와 동일한 이유 — Supabase 쿼리를 가로채는 가짜가 없어 실행
  // 경로로는 확인할 수 없다(파일 상단 주석 참조). 소스 텍스트를 직접 읽어 두 메서드 본문에
  // `listingCardColumns` 식별자가 실제로 등장하는지 확인한다.
  test(
      'listingCardColumns가 fetchListings·fetchPopularListings 본문에서 실제로 참조된다'
      '(리터럴로 재-인라인되는 회귀를 잡는다)', () {
    final file = File('lib/features/listings/listings_repository.dart');
    expect(file.existsSync(), isTrue,
        reason: 'flutter test의 cwd가 app/가 아닐 수 있다(app_theme_color_drift_test.dart와 동일 전제)');
    final content = file.readAsStringSync();

    final fetchListingsStart =
        content.indexOf('Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async {');
    final fetchPopularListingsStart = content.indexOf(
        'Future<List<ListingCardData>> fetchPopularListings({int limit = 4}) async {');
    expect(fetchListingsStart, greaterThanOrEqualTo(0),
        reason: 'fetchListings 시그니처를 못 찾았다(이름/시그니처가 바뀌었을 수 있다)');
    expect(fetchPopularListingsStart, greaterThan(fetchListingsStart),
        reason: 'fetchPopularListings 시그니처를 못 찾았다');

    final fetchListingsBodyStart =
        content.indexOf('async {', fetchListingsStart) + 'async {'.length;
    final fetchPopularListingsBodyStart =
        content.indexOf('async {', fetchPopularListingsStart) + 'async {'.length;
    final fetchListingsEnd = content.indexOf('\n  }', fetchListingsBodyStart);
    final fetchPopularListingsEnd =
        content.indexOf('\n  }', fetchPopularListingsBodyStart);
    expect(fetchListingsEnd, greaterThan(fetchListingsBodyStart));
    expect(fetchPopularListingsEnd, greaterThan(fetchPopularListingsBodyStart));

    final fetchListingsBody =
        content.substring(fetchListingsBodyStart, fetchListingsEnd);
    final fetchPopularListingsBody =
        content.substring(fetchPopularListingsBodyStart, fetchPopularListingsEnd);

    // ✎ 2026-08-13 — 예전엔 `listingCardColumns(_authed)`로 **인자까지** 단언했다(그때는
    // anon 분기가 계약이었고, `(true)`로 하드코딩하는 회귀를 잡아야 했다). 0037 GRANT로 그
    // 분기가 사라져 함수는 이제 무인자다 — 잡아야 할 회귀도 "인자 하드코딩"이 아니라
    // **"상수를 안 쓰고 컬럼 문자열을 본문에 다시 인라인하는 것"** 하나로 줄었다.
    final wiredPattern = RegExp(r'listingCardColumns\(\)');
    expect(wiredPattern.hasMatch(fetchListingsBody), isTrue,
        reason: 'fetchListings가 listingCardColumns()를 호출하지 않는다 — 컬럼 문자열을 본문에 '
            '다시 인라인하면 상수를 고쳐도 이 경로만 옛 컬럼을 select한다');
    expect(wiredPattern.hasMatch(fetchPopularListingsBody), isTrue,
        reason: 'fetchPopularListings가 listingCardColumns()를 호출하지 않는다 — 같은 이유');

    // fetchPopularListings의 FR11 강제 지점(_buyerQuery = status='on_sale' 강제, AC3 정렬·
    // 건수 계약)을 소스 텍스트로 직접 단언한다 — 지금 이 계약을 지키는 테스트가 하나도 없었다.
    expect(fetchPopularListingsBody, contains('_buyerQuery'),
        reason: 'fetchPopularListings가 _buyerQuery(FR11 판매완료 비노출 강제)를 거치지 않는다');
    expect(fetchPopularListingsBody, contains(".order('view_count'"),
        reason: '"지금 인기"는 view_count desc 정렬이어야 한다(AC3)');
    expect(fetchPopularListingsBody, contains(".order('id'"),
        reason: 'view_count 동률 시 결정적 정렬을 위한 id 2차 정렬키가 빠졌다');
    expect(fetchPopularListingsBody, contains('.limit('),
        reason: '"지금 인기"는 상위 몇 건만 반환해야 한다(무제한 반환 방지)');

    // T7(spec-16-8 검증 갭) — 위는 정렬 컬럼("무엇으로 정렬하나")만 보고 방향("어느
    // 방향으로")은 안 봤다. `.order('view_count', ascending: true)`로 바꿔도(측정된 뮤테이션)
    // 위 `.order('view_count'` contains는 여전히 통과한다 — "지금 인기"가 최다조회가 아니라
    // 최소조회 4건을 보여주게 된다. 두 .order() 모두 ascending: false(내림차순)여야 한다.
    expect(
      fetchPopularListingsBody,
      contains(".order('view_count', ascending: false)"),
      reason: '"지금 인기"는 조회수 **내림차순**이어야 한다 — ascending: true면 최소조회 순으로 '
          '뒤집힌다(AC3)',
    );
    expect(
      fetchPopularListingsBody,
      contains(".order('id', ascending: false)"),
      reason: 'id 2차 정렬키도 내림차순이어야 한다(1차 정렬키와 방향이 갈리면 동률 처리가 '
          '일관되지 않는다)',
    );

    // T7(spec-16-8 검증 갭, docs/conventions.md §6 FR11 이미지축 강제 지점) — 위는 컬럼·정렬·
    // limit만 보고 대표사진 부착(_fetchCovers→attachCoverImages)은 안 봤다. `_fetchCovers(ids)`
    // 호출을 지우고 `attachCoverImages(rows, const {}, ...)`로 바꿔도(측정된 뮤테이션) 위
    // 단언들은 전부 그대로 통과한다 — "지금 인기" 카드 전원이 대표사진 없이 "사진 준비중"
    // 플레이스홀더로만 나온다.
    expect(
      fetchPopularListingsBody,
      contains('_fetchCovers'),
      reason: 'fetchPopularListings가 _fetchCovers(ids)로 대표사진을 조회하지 않으면 '
          '"지금 인기" 카드 전원이 사진 없이(플레이스홀더로) 렌더된다(docs/conventions.md §6)',
    );
    expect(
      fetchPopularListingsBody,
      contains('attachCoverImages'),
      reason: 'fetchPopularListings가 attachCoverImages로 조회한 대표사진을 실제로 붙이지 '
          '않으면 위와 같은 실패가 난다',
    );
  });

  test('fetchPopularListings의 기본 limit은 4건이다(AC3)', () {
    final file = File('lib/features/listings/listings_repository.dart');
    final content = file.readAsStringSync();
    expect(
      content,
      contains('fetchPopularListings({int limit = 4})'),
      reason: '기본 건수가 4가 아니면 홈 "지금 인기" 섹션의 계약(spec-16-8 AC3)이 바뀐 것이다',
    );
  });
}
