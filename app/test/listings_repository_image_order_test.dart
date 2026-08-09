// Story 16.2 코드리뷰 patch — `listings_repository.dart`의 `pickCoverImages`/`sortGalleryPaths`
// (원행 파싱·정렬 순수 함수)와 `compareImageOrder`((sort_order, id) 비교자)를 직접 단언한다.
//
// 이 파일은 원래 `_pickCover`/`_sortGallery`를 로컬로 재구현해 그 사본만 검증했다 — 헤더 주석은
// "그래서 실 소비처(`_fetchCovers`·`fetchListing`)가 보장된다"고 주장했지만, 사본과 원본이
// 갈리면(예: 이번에 추가된 빈 문자열 `storage_path` 스킵) 이 파일은 계속 green이면서 실제
// 소비처는 그 방어가 없는 상태로 남을 수 있었다. 이제 원본 함수(`pickCoverImages`/
// `sortGalleryPaths`, `@visibleForTesting`로 노출됨)를 raw row map으로 직접 호출해 그 사각지대를
// 없앤다.
//
// 3회차 리뷰 patch — 사진을 **카드·갤러리에 실제로 붙이는** 조립부(`attachCoverImages`/
// `buildGalleryUrls`)도 여기서 직접 부른다. 그 전에는 파싱·정렬만 검증돼 있었고 부착 자체는
// 어떤 테스트도 실행하지 않아, 리뷰가 `fetchListings`에서 `image_url`/`image_count`를 통째로
// null·0으로 만들고 `withImages`를 지워도 전체 스위트가 green이었다(실측) — 기능이 통째로
// 사라져도 CI가 안 잡는 상태였다.
//
// ⚠️ 이 파일이 다루지 않는 것(정확히 무엇이 검증되는지):
//   · Supabase 쿼리 자체(`.from('listing_images').select(...).inFilter/.eq/.order` 체이닝) —
//     `_fetchCovers`/`fetchListing`이 실제로 그 쿼리를 만드는지는 여기서 실행되지 않는다.
//   · `getPublicUrl`(경로 → 공개 URL 조립) — URL 조립은 주입된 buildUrl 콜백이 대신하므로
//     실제 헬퍼는 호출되지 않는다(호출부 책임).
//   · 버킷 이름(`listing_images_bucket.dart`) — 위와 같은 이유로 이 파일과 무관하다.
//     대신 `listing_images_bucket_test.dart`가 마이그레이션 정본과 대조한다.
//   Supabase 클라이언트를 가짜로 주입해 `ListingsRepository`를 통째로 검증하는 통합 테스트가
//   필요해지면 별도 파일로 추가한다(이 파일의 책임을 넓히지 않는다).
import 'package:app/features/listings/listings_repository.dart';
import 'package:flutter_test/flutter_test.dart';

/// `listing_images` 원행 하나를 만든다. 계약 위반 행(필드 누락·빈 경로 등)은 각 테스트가
/// 직접 리터럴로 구성한다(이 헬퍼로는 표현할 수 없는 게 의도다 — 정상 행만 만든다).
Map<String, dynamic> _row({
  String listingId = 'L1',
  required String path,
  required int sortOrder,
  required String id,
}) =>
    <String, dynamic>{
      'listing_id': listingId,
      'storage_path': path,
      'sort_order': sortOrder,
      'id': id,
    };

void main() {
  group('compareImageOrder', () {
    test('sort_order가 다르면 그 순서로 정렬한다', () {
      expect(compareImageOrder(0, 'b', 1, 'a'), lessThan(0));
      expect(compareImageOrder(2, 'a', 1, 'z'), greaterThan(0));
    });

    test('sort_order가 같으면 id 오름차순으로 타이브레이크한다(#47-2 — 2차 정렬키 누락 시 '
        '조회마다 순서가 바뀌던 실측된 버그 패턴)', () {
      expect(compareImageOrder(0, 'aa', 0, 'zz'), lessThan(0));
      expect(compareImageOrder(0, 'zz', 0, 'aa'), greaterThan(0));
      expect(compareImageOrder(5, 'x', 5, 'x'), 0);
    });
  });

  group('pickCoverImages(_fetchCovers 순수 처리부 — 대표사진 승자 판정 + 카운트)', () {
    test('대표는 (sort_order,id) 최솟값이다 — sort_order 동률은 id로 갈린다', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'c.jpg', sortOrder: 2, id: 'row-c'),
        _row(path: 'a1.jpg', sortOrder: 0, id: 'row-a1'),
        _row(path: 'a0.jpg', sortOrder: 0, id: 'row-a0'), // id가 더 작아 실제 대표가 돼야 함
        _row(path: 'b.jpg', sortOrder: 1, id: 'row-b'),
      ];
      final picks = pickCoverImages(rows);
      expect(picks['L1']!.path, 'a0.jpg');
      expect(picks['L1']!.count, 4); // 4행 전부 계약을 통과했으므로 카운트도 4.
    });

    test('입력 순서가 섞여 들어와도 승자는 같다(정렬된 입력을 가정하지 않는다)', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'a0.jpg', sortOrder: 0, id: 'row-a0'),
        _row(path: 'c.jpg', sortOrder: 2, id: 'row-c'),
        _row(path: 'b.jpg', sortOrder: 1, id: 'row-b'),
        _row(path: 'a1.jpg', sortOrder: 0, id: 'row-a1'),
      ];
      expect(pickCoverImages(rows)['L1']!.path, 'a0.jpg');
    });

    test('계약을 어긴 행(빈 경로·필드 누락·타입 불일치)은 건너뛰고 카운트에도 안 들어간다', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'ok.jpg', sortOrder: 0, id: 'row-ok'),
        {'listing_id': 'L1', 'storage_path': '', 'sort_order': 1, 'id': 'row-empty'}, // 빈 경로
        {'listing_id': 'L1', 'storage_path': '   ', 'sort_order': 2, 'id': 'row-blank'}, // 공백뿐인 경로
        {'listing_id': 'L1', 'storage_path': 'x.jpg', 'sort_order': 'nope', 'id': 'row-bad-sort'}, // 강제변환 실패
        {'listing_id': 'L1', 'storage_path': 'y.jpg', 'id': 'row-missing-sort'}, // sort_order 자체 없음
        {'storage_path': 'z.jpg', 'sort_order': 3, 'id': 'row-no-listing'}, // listing_id 없음
      ];
      final picks = pickCoverImages(rows);
      expect(picks['L1']!.path, 'ok.jpg');
      expect(picks['L1']!.count, 1); // 계약 통과 행은 1개뿐(나머지 5행은 스킵).
    });

    test('빈 입력 → 빈 맵', () {
      expect(pickCoverImages(const <Map<String, dynamic>>[]), isEmpty);
    });

    test('매물이 여러 건이면 매물별로 각자 대표·카운트를 고른다(서로 섞이지 않는다)', () {
      final rows = <Map<String, dynamic>>[
        _row(listingId: 'L1', path: 'l1-b.jpg', sortOrder: 1, id: 'row-l1-b'),
        _row(listingId: 'L1', path: 'l1-a.jpg', sortOrder: 0, id: 'row-l1-a'),
        _row(listingId: 'L2', path: 'l2-a.jpg', sortOrder: 0, id: 'row-l2-a'),
      ];
      final picks = pickCoverImages(rows);
      expect(picks['L1']!.path, 'l1-a.jpg');
      expect(picks['L1']!.count, 2);
      expect(picks['L2']!.path, 'l2-a.jpg');
      expect(picks['L2']!.count, 1);
    });
  });

  group('sortGalleryPaths(fetchListing 갤러리 순수 처리부 — 전체 정렬)', () {
    test('정렬 결과가 (sort_order,id) 오름차순 전체 순서와 일치한다', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'c.jpg', sortOrder: 2, id: 'row-c'),
        _row(path: 'a1.jpg', sortOrder: 0, id: 'row-a1'),
        _row(path: 'a0.jpg', sortOrder: 0, id: 'row-a0'),
        _row(path: 'b.jpg', sortOrder: 1, id: 'row-b'),
      ];
      expect(sortGalleryPaths(rows), ['a0.jpg', 'a1.jpg', 'b.jpg', 'c.jpg']);
    });

    test('1번째 사진은 pickCoverImages가 고른 대표와 항상 같다(대표 판별을 두 군데서 하지 '
        '않는다 — web galleryImages.test.ts와 같은 회귀 방지 취지)', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'c.jpg', sortOrder: 2, id: 'row-c'),
        _row(path: 'a1.jpg', sortOrder: 0, id: 'row-a1'),
        _row(path: 'a0.jpg', sortOrder: 0, id: 'row-a0'),
        _row(path: 'b.jpg', sortOrder: 1, id: 'row-b'),
      ];
      final sorted = sortGalleryPaths(rows);
      final cover = pickCoverImages(rows)['L1']!;
      expect(sorted.first, cover.path);
    });

    test('계약을 어긴 행(빈 경로·필드 누락)은 건너뛴다', () {
      final rows = <Map<String, dynamic>>[
        _row(path: 'ok.jpg', sortOrder: 0, id: 'row-ok'),
        {'storage_path': '   ', 'sort_order': 1, 'id': 'row-blank'}, // 공백뿐인 경로
        {'storage_path': 'x.jpg', 'id': 'row-missing-sort'}, // sort_order 없음
      ];
      expect(sortGalleryPaths(rows), ['ok.jpg']);
    });

    test('빈 입력 → 빈 리스트', () {
      expect(sortGalleryPaths(const <Map<String, dynamic>>[]), isEmpty);
    });
  });

  // 사진을 카드에 실제로 붙이는 자리 — `fetchListings`가 대표사진 맵을 매물 행에 합쳐
  // `ListingCardData`를 만드는 그 로직 그대로다(쿼리만 호출부에 남고 여기서 전부 실행된다).
  group('attachCoverImages', () {
    test('대표사진이 있으면 URL과 장수가 카드에 실린다', () {
      final cards = attachCoverImages(
        [_listingRow(id: 'L1')],
        {'L1': (path: 'u/L1/a.webp', count: 3)},
        (p) => 'https://cdn.test/$p',
      );
      expect(cards.single.imageUrl, 'https://cdn.test/u/L1/a.webp');
      expect(cards.single.imageCount, 3);
    });

    test('대표사진이 없는 매물은 URL null·장수 0 — 배지가 뜨지 않을 상태로 내려간다', () {
      final cards = attachCoverImages(
        [_listingRow(id: 'L1')],
        const {}, // 사진 0장이거나 사진 쿼리가 실패해 빈 맵으로 강등된 경우
        (p) => 'https://cdn.test/$p',
      );
      expect(cards.single.imageUrl, isNull);
      expect(cards.single.imageCount, 0);
    });

    test('매물마다 자기 대표사진만 받는다(맵이 섞이지 않는다)', () {
      final cards = attachCoverImages(
        [_listingRow(id: 'L1'), _listingRow(id: 'L2')],
        {
          'L1': (path: 'u/L1/a.webp', count: 1),
          'L2': (path: 'u/L2/b.webp', count: 5),
        },
        (p) => 'https://cdn.test/$p',
      );
      expect(cards[0].imageUrl, 'https://cdn.test/u/L1/a.webp');
      expect(cards[0].imageCount, 1);
      expect(cards[1].imageUrl, 'https://cdn.test/u/L2/b.webp');
      expect(cards[1].imageCount, 5);
    });

    test('계약을 어긴 매물 행은 카드로 만들지 않고 버린다(나머지는 정상 표시)', () {
      final cards = attachCoverImages(
        [
          _listingRow(id: 'L1'),
          <String, dynamic>{'id': 'L2'}, // 필수 7필드 미충족
        ],
        {'L1': (path: 'u/L1/a.webp', count: 1)},
        (p) => 'https://cdn.test/$p',
      );
      expect(cards.map((c) => c.id), ['L1']);
    });

    // 코드리뷰 패치(spec-16-9) — 카드 옵션 칩(_OptionChipsRow)의 데이터 출처인 `options` 필드가
    // 행 조립 경로(attachCoverImages)를 거쳐도 살아남는지 보는 테스트가 0건이었다.
    test('options 필드가 카드 조립 경로를 거쳐도 그대로 남는다', () {
      final cards = attachCoverImages(
        [_listingRow(id: 'L1', options: const ['선루프', '통풍시트'])],
        {'L1': (path: 'u/L1/a.webp', count: 1)},
        (p) => 'https://cdn.test/$p',
      );
      expect(cards.single.options, ['선루프', '통풍시트']);
    });
  });

  group('buildGalleryUrls', () {
    test('정렬된 순서 그대로 URL이 조립된다', () {
      final urls = buildGalleryUrls(
        [
          _row(path: 'c.webp', sortOrder: 2, id: 'r3'),
          _row(path: 'a.webp', sortOrder: 0, id: 'r1'),
          _row(path: 'b.webp', sortOrder: 1, id: 'r2'),
        ],
        (p) => 'https://cdn.test/$p',
      );
      expect(urls, [
        'https://cdn.test/a.webp',
        'https://cdn.test/b.webp',
        'https://cdn.test/c.webp',
      ]);
    });

    test('갤러리 1번째 URL은 대표사진과 같은 사진을 가리킨다', () {
      final rows = [
        _row(path: 'z.webp', sortOrder: 1, id: 'r2'),
        _row(path: 'a.webp', sortOrder: 0, id: 'r1'),
      ];
      final cover = pickCoverImages(rows)['L1']!;
      expect(buildGalleryUrls(rows, (p) => p).first, cover.path);
    });

    test('사진이 없으면 빈 리스트 — 상세는 플레이스홀더로 폴백한다', () {
      expect(buildGalleryUrls(const <Map<String, dynamic>>[], (p) => p), isEmpty);
    });
  });
}

/// `listings` 원행 하나(카드 필수 7필드 충족). 사진 관련 키는 일부러 넣지 않는다 —
/// `attachCoverImages`가 붙이는 것만 검증하기 위해서다.
Map<String, dynamic> _listingRow({required String id, List<String>? options}) =>
    <String, dynamic>{
      'id': id,
      'manufacturer': '현대',
      'model': '아반떼',
      'year': 2020,
      'price': 15000000,
      'mileage': 30000,
      'region': '서울',
      'options': ?options,
    };
