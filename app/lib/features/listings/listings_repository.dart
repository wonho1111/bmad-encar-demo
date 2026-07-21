// 매물 조회 레포지토리 — 구매자 관점(판매중만, FR11)으로 listings 를 읽는다.
//
// FR11 단일 규칙(web lib/listings.ts 이식):
//   구매자에게는 status='on_sale' 만. DB RLS(0002_listings)는 on_sale 을 모두에게 공개하되
//   본인 매물(own)·admin 도 통과시키므로, 판매자가 본인 sold 를 구매자 경로로 보면 샐 수 있다.
//   → 모든 구매자 조회를 _buyerQuery(=.eq('status','on_sale')) 한 곳에서 시작해 강제한다(이중 방어).
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/supabase_client.dart';
import 'listing.dart';
import 'listing_filters.dart';

/// 매물 상태 단일 상수(0002_listings CHECK·web LISTING_STATUS 미러 — drift 금지).
/// on_sale=판매중(구매자 공개), sold=판매완료(구매자 비노출 FR11).
const String statusOnSale = 'on_sale';
const String statusSold = 'sold';

/// 구매자에게 노출 가능한 매물 상태 = 판매중. 단일 상수(FR11 단일 출처).
const String buyerVisibleStatus = statusOnSale;

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
      'fuel, accident_status, is_single_owner, is_non_smoker',
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

    return rows
        .map(ListingCardData.fromMap)
        .whereType<ListingCardData>()
        .toList();
  }

  /// 단일 매물 상세 — 구매자 관점(판매중만) + id 일치. 0건이면 null(없음·sold·삭제).
  /// web listings/[id] 의 maybeSingle 패턴.
  Future<ListingDetail?> fetchListing(String id) async {
    final row = await _buyerQuery(
      'id, seller_id, manufacturer, model, body_type, year, price, mileage, '
      'color, fuel, transmission, displacement, seats, region, accident_free, '
      'seller_name, options, description, status',
    ).eq('id', id).maybeSingle();

    if (row == null) return null;
    return ListingDetail.fromMap(row);
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
        .select(
          'id, seller_id, manufacturer, model, body_type, year, price, mileage, '
          'color, fuel, transmission, displacement, seats, region, accident_free, '
          'seller_name, options, description, status',
        )
        .eq('id', id)
        .eq('seller_id', sellerId)
        .maybeSingle();

    if (row == null) return null;
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
  ///   전이 규칙: on_sale → sold 단방향만(되돌리기 없음, web 과 동일). 0이면 타인·없음·이미 sold.
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
