// 찜(wishlist) 레포지토리 — Supabase 직접 호출(api 미경유, epic-16-context.md Technical
// Decisions: "이미지 Storage·Realtime 채팅·찜은 FastAPI를 경유하지 않는다"). web lib/wishlist.ts +
// WishButton.tsx의 인라인 toggle을 한 클래스로 합친 Flutter 판(A2 — Dart는 파일 하나 더 두는 게
// web처럼 "조회 헬퍼 파일 + 버튼 컴포넌트 인라인 mutation"으로 가르는 것보다 무겁지 않다).
//
// 로그인 게이트를 이식하지 않는다(spec-16-3 Boundaries) — app_router.dart의 redirect가 이미
// 앱 전역을 로그인 필수로 강제하므로, `supabase.auth.currentUser`가 non-null임을 전제하고
// 곧바로 `.id`를 쓴다(기존 관례, listing_detail_screen.dart의 문의하기와 동일 전제).
import 'package:flutter/foundation.dart' show debugPrint, visibleForTesting;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/supabase_client.dart';
import '../listings/listings_repository.dart' show statusOnSale, pickCoverImages;

// Postgres 유니크 위반(SQLSTATE) — chat_repository.dart와 동일 관례(코드만, 문자열 없음).
const String _pgUniqueViolation = '23505';

/// `wishlists` 한 행 + 조인된 매물 임베드(web WishlistEntry 미러).
/// `embed`는 RLS가 막으면(타인 소유 sold) null로 온다 — 조회 실패가 아니라 정상 응답이다
/// (web fetchWishlist 주석과 동일 근거).
class WishlistEntry {
  const WishlistEntry({required this.listingId, required this.createdAt, this.embed});

  final String listingId;
  final DateTime createdAt;
  final Map<String, dynamic>? embed;

  static WishlistEntry? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final listingId = raw['listing_id'];
    if (listingId is! String) return null;
    final createdAtRaw = raw['created_at'];
    final createdAt = createdAtRaw is String ? DateTime.tryParse(createdAtRaw) : null;
    final embedRaw = raw['listings'];
    final embed = embedRaw is Map ? Map<String, dynamic>.from(embedRaw) : null;
    return WishlistEntry(
      listingId: listingId,
      // created_at 파싱 실패는 사실상 도달 불가(DB NOT NULL default now()) — 방어적으로만 처리.
      createdAt: createdAt ?? DateTime.fromMillisecondsSinceEpoch(0),
      embed: embed,
    );
  }
}

/// 찜 목록에서 이 항목을 "회색+판매완료 비활성"으로 그려야 하는지 판정하는 순수 술어
/// (web isWishedListingBlocked 미러). embed=null(RLS 차단, 타인 소유 sold) 또는 status가
/// on_sale이 아니면(sold·null·미래의 제3상태 전부 포함) true — allowlist 판정(FR11 "기본 차단"
/// 정신, web 코드리뷰 2026-07-22 P4와 동일 근거). `wishlist_providers.dart`의 `wishlistProvider`가
/// 타일을 가르는 데 정식으로 재사용한다(테스트 전용이 아니다).
bool isWishlistBlocked(Map<String, dynamic>? embed, String? status) {
  if (embed == null) return true;
  return status != statusOnSale;
}

/// insert 중 나온 `PostgrestException`을 무시해도 되는지 판정하는 순수 술어 — `isWishlistBlocked`와
/// 같은 추출 원칙(코드리뷰 지적 P12): 이 분기 로직을 `toggle` 본문에 직접 두면, 모든 테스트가
/// `toggle` 자체를 가짜(fake)로 갈아 끼우는 이 리포의 관례상 어떤 테스트로도 실행되지 않는다.
/// 판정만 여기로 빼면 그 분기를 Supabase 없이 직접 단언할 수 있다.
bool isIgnorableWishInsertError(PostgrestException e) => e.code == _pgUniqueViolation;

/// 찜 목록 조회 시 listings에서 함께 가져오는 카드용 컬럼 + status(판매완료 판정 전용).
/// ListingCardData.fromMap이 읽는 필드의 상위집합이라 이 결과를 그대로 fromMap에 넘길 수 있다
/// (web WishlistListingEmbed와 같은 구조적 재사용). `@visibleForTesting`:
/// `listings_repository.dart`의 `listingDetailColumns`와 같은 이유 — 신뢰속성 3컬럼
/// (`accident_status`·`is_single_owner`·`is_non_smoker`)이 여기서 빠지면 찜 목록 카드만
/// 조용히 뱃지를 잃는데, 이 상수를 직접 보는 테스트가 없었다(코드리뷰 지적).
/// anon(비로그인)이 이 select를 그대로 쓰면 신뢰속성 3컬럼 때문에 `42501 permission
/// denied`로 select 전체가 실패한다(§4.1 anon 단서와 동일 근거) — 이 앱은 app_router.dart의
/// 전역 redirect가 모든 화면을 로그인 필수로 강제해 이 경로에 anon이 닿지 않는다(web은
/// `/search`에서 `user ? trustColumns : ''`로 직접 분기한다, 코드리뷰 지적 P15).
@visibleForTesting
const String wishlistListingColumns =
    'id, manufacturer, model, year, price, mileage, region, seller_name, fuel, '
    'accident_status, is_single_owner, is_non_smoker, options, status';

class WishlistRepository {
  WishlistRepository({SupabaseClient? client}) : _client = client ?? supabase;

  final SupabaseClient _client;

  /// 낙관적 토글의 서버측 절반 — insert(wish=true) 또는 delete(wish=false).
  /// 유니크 위반(이미 찜된 상태에 다시 insert)은 최종 상태가 어차피 "찜됨"이라 무시한다
  /// (web applyToggle과 동일 근거 — 연타 차단이 있어도 네트워크 재시도 등으로 벌어질 수 있다).
  Future<void> toggle(String listingId, {required bool wish}) async {
    final userId = _client.auth.currentUser!.id;
    if (wish) {
      try {
        await _client.from('wishlists').insert({'user_id': userId, 'listing_id': listingId});
      } on PostgrestException catch (e) {
        if (!isIgnorableWishInsertError(e)) rethrow;
      }
    } else {
      await _client
          .from('wishlists')
          .delete()
          .eq('user_id', userId)
          .eq('listing_id', listingId);
    }
  }

  /// 로그인 사용자의 찜 id 전체 집합 — 카드 진입점 3곳(홈·검색·AI)이 공유하는 단일 오버레이 원천
  /// (spec-16-3 Boundaries: 화면별 id-scoped 조회 대신 전체 집합 재사용, fetchListings의
  /// 전량조회와 같은 근거, A2). 조회 실패는 "찜 0건"과 같은 빈 Set으로 처리한다(web
  /// fetchWishedListingIds와 동일 방침 — 오버레이 실패로 카드 렌더 전체를 막지 않는다).
  Future<Set<String>> fetchWishedListingIds() async {
    final userId = _client.auth.currentUser?.id;
    if (userId == null) return {};
    try {
      final rows =
          await _client.from('wishlists').select('listing_id').eq('user_id', userId);
      return rows.map((r) => r['listing_id']).whereType<String>().toSet();
    } catch (e) {
      // 예외 전체를 찍지 않는다 — wish_button.dart의 동일 방어와 같은 이유(listings_repository.dart
      // pickCoverImages 주석 원칙 — debugPrint는 release에서도 살아 있다). 모양(타입·코드)만.
      debugPrint('[wishlist] 찜 오버레이 조회 실패: ${e.runtimeType}'
          '${e is PostgrestException ? '(${e.code})' : ''}');
      return {};
    }
  }

  /// 본인 찜 전체를 최신순(찜한 시각 내림차순)으로 매물 카드 컬럼과 함께 조회(찜 목록 화면 전용).
  Future<List<WishlistEntry>> fetchWishlist() async {
    final userId = _client.auth.currentUser?.id;
    if (userId == null) return [];
    final rows = await _client
        .from('wishlists')
        .select('listing_id, created_at, listings($wishlistListingColumns)')
        .eq('user_id', userId)
        .order('created_at', ascending: false);
    return rows.map(WishlistEntry.fromMap).whereType<WishlistEntry>().toList();
  }

  /// on_sale 찜 매물의 대표사진 — id 목록으로 `listing_images`를 배치 조회한다(§6 이미지 축
  /// 신규 소비처, docs/conventions.md §6에 등록됨). `pickCoverImages`(listings_repository.dart,
  /// top-level 공개 함수)를 그대로 재사용해 대표사진 승자 판정 로직을 두 곳에 따로 두지 않는다
  /// (같은 방어 원칙 — listings_repository.dart 주석 참조).
  Future<Map<String, ({String path, int count})>> fetchCovers(List<String> listingIds) async {
    if (listingIds.isEmpty) return {};
    try {
      final rows = await _client
          .from('listing_images')
          .select('listing_id, storage_path, sort_order, id')
          .inFilter('listing_id', listingIds)
          .order('sort_order', ascending: true)
          .order('id', ascending: true);
      return pickCoverImages(rows);
    } catch (e) {
      // 사진은 부가정보 — 조회 실패가 찜 목록 자체를 죽이지 않는다(listings_repository.dart와 동일 방침).
      // 예외 전체를 찍지 않는 이유는 위 fetchWishedListingIds와 동일(개인정보가 새는 것을 막는다).
      debugPrint('[wishlist] 찜 목록 대표사진 조회 실패: ${e.runtimeType}'
          '${e is PostgrestException ? '(${e.code})' : ''}');
      return {};
    }
  }
}
