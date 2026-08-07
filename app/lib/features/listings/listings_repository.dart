// 매물 조회 레포지토리 — 구매자 관점(판매중만, FR11)으로 listings 를 읽는다.
//
// FR11 단일 규칙(web lib/listings.ts 이식):
//   구매자에게는 status='on_sale' 만. DB RLS(0002_listings)는 on_sale 을 모두에게 공개하되
//   본인 매물(own)·admin 도 통과시키므로, 판매자가 본인 sold 를 구매자 경로로 보면 샐 수 있다.
//   → 모든 구매자 조회를 _buyerQuery(=.eq('status','on_sale')) 한 곳에서 시작해 강제한다(이중 방어).
import 'package:flutter/foundation.dart' show debugPrint, visibleForTesting;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/storage_helper.dart';
import '../../core/supabase/supabase_client.dart';
import 'listing.dart';
import 'listing_filters.dart';
import 'listing_images_bucket.dart';

/// 매물 상태 단일 상수(0002_listings CHECK·web LISTING_STATUS 미러 — drift 금지).
/// on_sale=판매중(구매자 공개), sold=판매완료(구매자 비노출 FR11).
const String statusOnSale = 'on_sale';
const String statusSold = 'sold';

/// 구매자에게 노출 가능한 매물 상태 = 판매중. 단일 상수(FR11 단일 출처).
const String buyerVisibleStatus = statusOnSale;

/// 상세 select 컬럼 — 구매자 상세(`fetchListing`)·본인 상세(`fetchOwnListing`) 둘이 공유한다
/// (`wishlist_repository.dart`의 `wishlistListingColumns`와 같은 재사용 방식). `@visibleForTesting`:
/// 신뢰속성 3컬럼(`accident_status`·`is_single_owner`·`is_non_smoker`)이 여기서 빠지면
/// `ListingDetail.fromMap`이 그 값을 null로만 받아 상세 화면의 신뢰속성 섹션 전체(AC2)가
/// 조용히 렌더되지 않는데, 이 두 select 문자열을 직접 보는 테스트가 없었다(코드리뷰 지적) —
/// 이 상수를 테스트가 직접 단언한다.
/// anon(비로그인)이 이 select를 그대로 쓰면 신뢰속성 3컬럼 때문에 `42501 permission denied`로
/// select 전체가 실패한다(§4.1 anon 단서와 동일 근거, web `/search`·`/listings/[id]`는 `user ?
/// trustColumns : ''`로 직접 분기한다) — 이 앱은 app_router.dart의 전역 redirect가 모든 화면을
/// 로그인 필수로 강제해 이 경로에 anon이 닿지 않는다(코드리뷰 지적 P15, 강제 지점은
/// app_router.dart의 redirect).
@visibleForTesting
const String listingDetailColumns =
    'id, seller_id, manufacturer, model, body_type, year, price, mileage, '
    'color, fuel, transmission, displacement, seats, region, accident_free, '
    'accident_status, is_single_owner, is_non_smoker, '
    'seller_name, options, description, status';

/// 대표사진 계산 결과 하나 — 매물 1건의 (sort_order, id) 최솟값 행 경로 + 계약-검증 통과 행 수.
class _CoverPick {
  _CoverPick(this.path, this.sortOrder, this.id, this.count);
  final String path;
  final int sortOrder;
  final String id;
  int count;
}

/// `listing_images` 한 행에서 정렬·URL 조립에 필요한 3필드만 담는다(갤러리 정렬용).
class _ImageRow {
  const _ImageRow(this.path, this.sortOrder, this.id);
  final String path;
  final int sortOrder;
  final String id;
}

/// (sort_order, id) 오름차순 비교자 — `_fetchCovers`(대표사진 승자 판정)와 `fetchListing`
/// (갤러리 전체 정렬)이 같은 규칙을 공유한다. 두 소비처가 각자 비교 로직을 따로 구현하면
/// 한쪽만 바뀌었을 때 "대표사진"과 "갤러리 1번째 사진"이 갈릴 수 있다(web coverImages.ts/
/// galleryImages.ts와 같은 원칙 — conventions.md §10.2, #47-2/#59 선례).
/// `@visibleForTesting`: 테스트가 정렬·타이브레이크 규칙을 직접 단언할 수 있게 노출한다.
@visibleForTesting
int compareImageOrder(int sortOrderA, String idA, int sortOrderB, String idB) {
  return sortOrderA != sortOrderB
      ? sortOrderA.compareTo(sortOrderB)
      : idA.compareTo(idB);
}

/// `listing_images` 원행(raw rows) → 매물별 대표사진(`sort_order,id` 최솟값) 경로 +
/// 계약-검증을 통과한 행 수. `_fetchCovers`의 순수 처리부만 뗀 것(쿼리는 호출부가 맡는다) —
/// Supabase 없이 이 매핑만 직접 테스트할 수 있게 top-level 함수로 분리했다.
/// 테스트 노출뿐 아니라 정식 재사용 대상이기도 하다(`@visibleForTesting` 아님) —
/// `WishlistRepository.fetchCovers`(Story 16.3, `wishlist_repository.dart`)가 찜 목록 화면의
/// 대표사진 승자 판정에 이 함수를 그대로 재사용한다. 같은 로직을 두 곳에 따로 두지 않기
/// 위해서다(#47-2/#59 선례와 동일 원칙).
Map<String, ({String path, int count})> pickCoverImages(
  List<Map<String, dynamic>> rows,
) {
  final picks = <String, _CoverPick>{};
  for (final row in rows) {
    final listingId = row['listing_id'];
    final storagePath = row['storage_path'];
    final id = row['id'];
    // 다른 계약값 숫자 필드(year·price·mileage·image_count 등, listing.dart의 asInt)와 같은
    // 방어 수준으로 맞춘다 — 타입이 int가 아니라고 행 전체를 버리지 않고 우선 강제변환을 시도한다.
    final sortOrder = asInt(row['sort_order']);
    if (listingId is! String ||
        storagePath is! String ||
        storagePath.trim().isEmpty || // 빈 경로는 "경로 없음"과 같다 — 버킷 루트 URL 방지.
        id is! String ||
        sortOrder == null) {
      // 행 전체(map)를 찍지 않는다 — storage_path 첫 구간이 소유자 user_id 라(§10) 기기 로그로
      // 샌다. debugPrint 는 release 에서도 살아 있다.
      debugPrint('listing_images 행 스킵(계약 위반): id=${row['id']}'); // 나쁜 데이터를 조용히 삼키지 않는다.
      continue; // 계약-외 값(강제변환도 실패)은 그 행만 건너뛴다.
    }

    final current = picks[listingId];
    if (current == null) {
      picks[listingId] = _CoverPick(storagePath, sortOrder, id, 1);
      continue;
    }
    current.count += 1; // 계약-검증을 통과한 행 수(스킵된 행은 세지 않는다).
    // 이름 주의: 비교 순서가 (새 행, 기존 승자)라 `< 0`은 **새 행**이 앞선다는 뜻이다.
    final newRowComesFirst =
        compareImageOrder(sortOrder, id, current.sortOrder, current.id) < 0;
    if (newRowComesFirst) {
      picks[listingId] = _CoverPick(storagePath, sortOrder, id, current.count);
    }
  }
  return {
    for (final entry in picks.entries)
      entry.key: (path: entry.value.path, count: entry.value.count),
  };
}

/// `listing_images` 원행(한 매물 것만) → (sort_order,id) 오름차순 정렬된 storage_path 리스트.
/// `fetchListing`의 순수 처리부만 뗀 것 — URL 조립(`getPublicUrl`)은 호출부가 맡는다(버킷명이
/// 이 함수 안에 스며들지 않는다).
/// `@visibleForTesting`: 테스트가 정렬·행 스킵 규칙을 직접 단언할 수 있게 노출한다.
@visibleForTesting
List<String> sortGalleryPaths(List<Map<String, dynamic>> rows) {
  final parsed = <_ImageRow>[];
  for (final r in rows) {
    final path = r['storage_path'];
    final rowId = r['id'];
    final sortOrder = asInt(r['sort_order']);
    if (path is! String ||
        path.trim().isEmpty || // 빈 경로는 "경로 없음"과 같다(pickCoverImages와 동일 방어).
        rowId is! String ||
        sortOrder == null) {
      // 행 전체(map)를 찍지 않는다 — pickCoverImages 와 같은 이유(§10 경로에 user_id 포함).
      debugPrint('listing_images 행 스킵(계약 위반): id=${r['id']}'); // 나쁜 데이터를 조용히 삼키지 않는다.
      continue; // 계약-외 값은 그 행만 건너뛴다(pickCoverImages와 동일 방어).
    }
    parsed.add(_ImageRow(path, sortOrder, rowId));
  }
  parsed.sort((a, b) => compareImageOrder(a.sortOrder, a.id, b.sortOrder, b.id));
  return parsed.map((r) => r.path).toList();
}

/// `listings` 원행 + 대표사진 맵 → 카드 목록. `fetchListings`의 순수 조립부만 뗀 것 —
/// 각 행에 대표사진 URL·장수를 붙여 `ListingCardData.fromMap`으로 변환한다(URL 조립은
/// buildUrl 콜백으로 주입받아 버킷명이 이 함수 안에 스며들지 않는다).
/// `@visibleForTesting`: 테스트가 이 부착 로직을 Supabase 없이 직접 단언할 수 있게 노출한다.
@visibleForTesting
List<ListingCardData> attachCoverImages(
  List<Map<String, dynamic>> rows,
  Map<String, ({String path, int count})> covers,
  String Function(String path) buildUrl,
) {
  return rows
      .map((r) {
        final id = r['id'];
        final cover = id is String ? covers[id] : null;
        return ListingCardData.fromMap({
          ...r,
          'image_url': cover == null ? null : buildUrl(cover.path),
          'image_count': cover?.count ?? 0,
        });
      })
      .whereType<ListingCardData>()
      .toList();
}

/// `listing_images` 원행(한 매물 것만) → 정렬된 갤러리 URL 리스트. `fetchListing`의 URL
/// 조립부만 뗀 것 — 정렬은 `sortGalleryPaths`에 맡기고 URL만 buildUrl로 조립한다.
/// `@visibleForTesting`: 테스트가 이 조립 로직을 Supabase 없이 직접 단언할 수 있게 노출한다.
@visibleForTesting
List<String> buildGalleryUrls(
  List<Map<String, dynamic>> rows,
  String Function(String path) buildUrl,
) {
  return sortGalleryPaths(rows).map(buildUrl).toList();
}

class ListingsRepository {
  ListingsRepository({SupabaseClient? client}) : _client = client ?? supabase;

  final SupabaseClient _client;

  /// 구매자 관점 조회 시작점 — from('listings').select(columns).eq('status','on_sale').
  /// 호출부가 이어서 필터·정렬·단건 조회를 체이닝한다. FR11 규칙이 여기서만 비롯된다.
  PostgrestFilterBuilder<List<Map<String, dynamic>>> _buyerQuery(String columns) {
    return _client
        .from('listings')
        .select(columns)
        .eq('status', buyerVisibleStatus);
  }

  /// 매물 목록(요약 7필드) — 필터 적용 + created_at desc, id desc 안정 정렬.
  /// 필터는 값이 있을 때만 체이닝(web SearchPage 와 동일). 키워드는 model ilike.
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async {
    var query = _buyerQuery(
      'id, manufacturer, model, year, price, mileage, region, seller_name, '
      'fuel, accident_status, is_single_owner, is_non_smoker, options',
    );

    if (f.keyword != null) {
      query = query.ilike('model', '%${f.keyword}%'); // 모델명 부분일치(대소문자 무시).
    }
    if (f.bodyType != null) query = query.eq('body_type', f.bodyType!);
    if (f.color != null) query = query.eq('color', f.color!);
    if (f.fuel != null) query = query.eq('fuel', f.fuel!);
    if (f.transmission != null) query = query.eq('transmission', f.transmission!);
    if (f.region != null) query = query.eq('region', f.region!);
    if (f.priceMin != null) query = query.gte('price', f.priceMin!);
    if (f.priceMax != null) query = query.lte('price', f.priceMax!);
    if (f.yearMin != null) query = query.gte('year', f.yearMin!);
    if (f.yearMax != null) query = query.lte('year', f.yearMax!);

    // created_at 같은 시드 행 순서가 새로고침마다 뒤집히지 않도록 id 를 2차 정렬키로(결정적 정렬).
    final rows = await query
        .order('created_at', ascending: false)
        .order('id', ascending: false);

    // 대표사진(목록 카드용) — 반환된 매물 id 전체로 listing_images 를 배치 조회한다.
    // web attachCoverImages 의 미러이되, 청크는 두지 않는다 — `fetchListings`는 페이지네이션
    // 없이 on_sale 전량을 반환하지만(app/lib 전역에 .range()/.limit() 0건), 데모 데이터 규모가
    // 작아 단일 `.inFilter()` 쿼리스트링이 PostgREST URL 길이 한도 안에 든다(A2, 과설계 방지).
    // 실 서비스 규모로 자라면 목록 자체에 페이지네이션이 먼저 필요해질 것이고, 그때 이 청크도
    // 같이 재검토한다.
    final ids = rows
        .map((r) => r['id'])
        .whereType<String>()
        .toList();
    final covers = await _fetchCovers(ids);

    return attachCoverImages(
      rows,
      covers,
      (p) => getPublicUrl(listingImagesBucket, p),
    );
  }

  /// 매물 id 목록 → 매물별 대표사진(`sort_order,id` 최솟값) + 계약-검증 통과 행 수.
  /// 쿼리 자체도 `order by sort_order, id`를 걸지만(§10.2), 승자 판정은 정렬 결과에만 기대지 않고
  /// 행마다 명시 비교한다(web coverImages.ts 와 같은 2층 방어, 실제 비교는 `pickCoverImages`).
  Future<Map<String, ({String path, int count})>> _fetchCovers(
    List<String> listingIds,
  ) async {
    if (listingIds.isEmpty) return {};

    // try 는 **쿼리만** 감싼다 — 매핑(`pickCoverImages`)까지 감싸면 거기 생긴 버그가
    // "사진 조회 실패"로 둔갑해 조용히 사진 없는 화면이 된다(Dart 의 catch 는 Error 도 잡는다).
    final List<Map<String, dynamic>> rows;
    try {
      rows = await _client
          .from('listing_images')
          .select('listing_id, storage_path, sort_order, id')
          .inFilter('listing_id', listingIds)
          .order('sort_order', ascending: true)
          .order('id', ascending: true);
    } catch (e) {
      // 사진은 부가정보 — 그것 때문에 핵심 화면(매물 목록)을 죽이지 않는다. 조회가 실패해도
      // 카드는 커버 없이(플레이스홀더로) 렌더된다 — 이 스토리 이전 동작과 같다.
      debugPrint('listing_images 대표사진 조회 실패: $e');
      return {};
    }
    return pickCoverImages(rows);
  }

  /// 단일 매물 상세 — 구매자 관점(판매중만) + id 일치. 0건이면 null(없음·sold·삭제).
  /// web listings/[id] 의 maybeSingle 패턴.
  Future<ListingDetail?> fetchListing(String id) async {
    final row = await _buyerQuery(listingDetailColumns).eq('id', id).maybeSingle();

    if (row == null) return null;
    final detail = ListingDetail.fromMap(row);
    if (detail == null) return null;

    // 상세 갤러리 전체 URL — web fetchListingGalleryUrls 미러. 매물을 먼저 찾은 뒤에만 조회하므로
    // sold/삭제된 매물은 위에서 이미 null 반환돼 이 지점에 오지 않는다(FR11 §6 호출부 좁히기).
    // 쿼리 정렬만 믿지 않고 클라이언트에서도 (sort_order, id)로 다시 정렬한다(`sortGalleryPaths`) —
    // `_fetchCovers`와 같은 2층 방어(§10.2, #47-2/#59 선례: 2차 정렬키 누락은 조회할 때마다
    // 순서가 바뀌는 실측된 버그 패턴). 갤러리 1번째 사진이 대표사진(`_fetchCovers`의 승자)과
    // 항상 같아야 한다.
    // try 는 **쿼리만** 감싼다 — 정렬·URL 조립까지 감싸면 거기 생긴 버그가 "사진 조회 실패"로
    // 둔갑해 조용히 사진 없는 상세가 된다(`_fetchCovers`와 같은 이유).
    final List<Map<String, dynamic>> imageRows;
    try {
      imageRows = await _client
          .from('listing_images')
          .select('storage_path, sort_order, id')
          .eq('listing_id', id)
          .order('sort_order', ascending: true)
          .order('id', ascending: true);
    } catch (e) {
      // 사진은 부가정보 — 그것 때문에 핵심 화면(매물 상세)을 죽이지 않는다. 사진 없이 상세를
      // 그대로 반환한다(사진 섹션은 플레이스홀더로 폴백).
      debugPrint('listing_images 갤러리 조회 실패($id): $e');
      return detail;
    }

    final urls = buildGalleryUrls(
      imageRows,
      (p) => getPublicUrl(listingImagesBucket, p),
    );

    return detail.withImages(urls);
  }

  /// 매물 등록(INSERT, FR5) — 본인 명의로 listings 행 생성.
  /// 구매자 조회용 _buyerQuery(status='on_sale' 강제)를 타지 않는다(이건 "쓰기"라 별개 경로).
  ///
  /// seller_id 는 호출부가 현재 로그인 user.id 로 넘긴다(정상 경로 명시). 위조해 넘겨도
  /// DB RLS(listings_insert_own: auth.uid()=seller_id, 0002)가 막는다 — 앱·DB 이중 방어.
  /// payload 는 validateAndBuildListing 이 만든 snake_case 정수 페이로드(status='on_sale' 포함).
  ///
  /// 에러(PostgrestException 등)는 변환 없이 그대로 던진다 → 호출부(컨트롤러)가 toKoreanListingError 로 한국어화.
  Future<void> createListing(
    Map<String, dynamic> payload, {
    required String sellerId,
  }) async {
    await _client.from('listings').insert({...payload, 'seller_id': sellerId});
  }

  // ──────────────────────────────────────────────────────────────────
  // 7.4 본인 매물 관리(FR6·8). 모두 "쓰기/소유자 읽기"라 구매자용 _buyerQuery(on_sale 강제)를 타지 않는다.
  //   본인은 sold 매물도 봐야 하고, UPDATE/DELETE 는 구매자 노출 규칙(FR11)과 무관하다.
  //   소유권은 DB RLS(listings_select_own / _update_own / _delete_own: auth.uid()=seller_id, 0002)가 강제하고,
  //   앱 쿼리도 seller_id 를 명시 필터한다(이중 방어). RLS 로 막힌 UPDATE/DELETE 는 "예외"가 아니라 "0행"으로 온다.
  // ──────────────────────────────────────────────────────────────────

  /// 본인 매물 목록(요약 6필드, status 포함) — seller_id 명시 필터 + 최신순.
  /// ⚠️ seller_id 필터 필수: listings SELECT 정책은 "on_sale ∪ 본인 ∪ admin" OR 결합이라
  ///    필터 없이 select 하면 "남의 판매중 매물"까지 섞인다(web sell/page.tsx 주석과 동일 함정).
  Future<List<OwnListing>> fetchOwnListings({required String sellerId}) async {
    final rows = await _client
        .from('listings')
        .select('id, manufacturer, model, year, price, status')
        .eq('seller_id', sellerId)
        .order('created_at', ascending: false)
        .order('id', ascending: false);

    return rows
        .map(OwnListing.fromMap)
        .whereType<OwnListing>()
        .toList();
  }

  /// 수정 폼을 채울 본인 단건(상세 15필드+status). 본인+id 일치, 0건이면 null(타인·없음).
  /// on_sale 강제 안 함 — sold 도 조회되며, 수정 차단은 호출부(컨트롤러/화면)가 status 로 판단한다.
  Future<ListingDetail?> fetchOwnListing(
    String id, {
    required String sellerId,
  }) async {
    final row = await _client
        .from('listings')
        .select(listingDetailColumns)
        .eq('id', id)
        .eq('seller_id', sellerId)
        .maybeSingle();

    if (row == null) return null;
    // ⚠️ 구매자 상세(fetchListing)와 달리 여기서는 .withImages(...)를 부르지 않는다 — 이 경로가
    // 채우는 ListingDetail.imageUrls는 항상 기본값(빈 리스트)이다. 의도적 누락이다(이 스토리
    // 범위 밖, 16.7 사진 업로더가 편집 화면에 사진 섹션을 붙일 때 함께 채운다) — 다음에 이
    // 화면에 사진을 그리는 사람이 "구매자 상세처럼 이미 채워져 있다"고 오해하지 않게 남긴다.
    return ListingDetail.fromMap(row);
  }

  /// 본인 매물 수정(UPDATE, FR6) — payload 는 폼이 만든 15필드(status·seller_id 미포함).
  /// .select('id') 로 갱신 행을 받아 "행 수"를 반환한다 → 0이면 RLS 차단(타인) 또는 없음.
  /// 에러는 그대로 던짐 → 컨트롤러가 toKoreanListingError 로 한국어화.
  ///
  /// 전제조건 .eq('status','on_sale') — 화면 진입(EditListingScreen)에서 sold 를 막지만,
  ///   진입 후 다른 기기/세션이 그새 구매완료(sold)했다면 "거래 끝난 매물"을 수정으로 덮어쓰는 사고가 난다.
  ///   markSold 와 같은 서버측 빗장을 둬, 그런 경우 0행이 돼 거부된다(동시성 방어 — 화면 가드와 이중).
  Future<int> updateListing(String id, Map<String, dynamic> payload) async {
    final rows = await _client
        .from('listings')
        .update(payload)
        .eq('id', id)
        .eq('status', statusOnSale)
        .select('id');
    return rows.length;
  }

  /// 본인 매물 삭제(DELETE, FR6) — 상태 무관(정리 목적).
  /// .select('id') 로 삭제 행 수 반환 → 0이면 RLS 차단(타인) 또는 이미 없음.
  Future<int> deleteListing(String id) async {
    final rows =
        await _client.from('listings').delete().eq('id', id).select('id');
    return rows.length;
  }

  /// 구매 완료(FR8) — status 를 sold 로 전환. payload 는 status 만(seller_id·다른 필드 위조/부수변경 차단).
  /// 전제조건 .eq('status','on_sale') — 이미 sold 거나 화면이 낡아 그새 바뀐 매물 재전환을 0행으로 막는다(서버측 빗장).
  ///   전이 규칙: on_sale → sold 단방향만(이 판매자 경로엔 되돌리기 없음, web 과 동일). 0이면
  ///   타인·없음·이미 sold. ⚠️ 관리자 전용 예외 있음(2026-08-07, Story 15.4) — web
  ///   `admin_restore_sold_listing` RPC(`0030`)로 관리자만 sold→on_sale을 되돌릴 수 있다.
  ///   이 앱엔 관리자 화면이 없어(admin_blocked_screen.dart) 이 경로가 노출되지 않는다.
  Future<int> markSold(String id) async {
    final rows = await _client
        .from('listings')
        .update({'status': statusSold})
        .eq('id', id)
        .eq('status', statusOnSale)
        .select('id');
    return rows.length;
  }
}
