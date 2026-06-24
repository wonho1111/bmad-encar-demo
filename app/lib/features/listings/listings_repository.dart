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

/// 구매자에게 노출 가능한 매물 상태 = 판매중. 단일 상수(FR11 단일 출처).
const String buyerVisibleStatus = 'on_sale';

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
      'id, manufacturer, model, year, price, mileage, region, seller_name',
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
}
