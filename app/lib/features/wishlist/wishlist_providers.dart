// 찜(wishlist)의 Riverpod providers (Story 16.3) — listings_providers.dart와 같은 DI 패턴.
// - wishlistRepositoryProvider: 레포 1개 공유.
// - wishedListingIdsProvider: 로그인 사용자의 찜 id 전체 집합(카드 진입점 3곳이 공유하는 단일
//   오버레이 원천, spec-16-3 Boundaries). 찜 토글 성공 시 이 provider를 invalidate해 다른
//   화면의 카드도 다음 리빌드에 최신 상태를 반영한다(wish_button.dart).
// - wishlistProvider: 찜 목록 화면 전용 — entries를 최신순 그대로 순회하며 그 자리에서
//   카드 타일/차단(회색) 타일을 고른다(web wishlist/page.tsx의 "무엇을 그릴지"·"순서" 분리
//   원칙과 동일, 코드리뷰 2026-07-22 P2 선례).
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/supabase/storage_helper.dart';
import '../listings/listing.dart';
import '../listings/listing_images_bucket.dart';
import 'wishlist_repository.dart';

final wishlistRepositoryProvider = Provider<WishlistRepository>((ref) {
  return WishlistRepository();
});

/// 로그인 사용자의 찜 id 전체 집합. autoDispose를 안 쓴다 — 홈/검색/AI 세 화면이 동시에
/// watch하는 공유 원천이라, 화면 하나가 잠깐 사라져도(탭 전환 등) 캐시가 즉시 날아가면
/// 나머지 화면이 매번 재조회해야 한다(A2 — fetchListings 전량조회와 같은 단순화 근거).
final wishedListingIdsProvider = FutureProvider<Set<String>>((ref) async {
  final repo = ref.watch(wishlistRepositoryProvider);
  return repo.fetchWishedListingIds();
});

/// 찜 목록 화면의 한 타일 — 정상 카드(on_sale) 또는 차단 타일(판매완료·RLS차단) 둘 중 하나.
/// web BlockedWishTile/ListingCard 분기를 데이터로 미리 갈라 화면(wishlist_screen.dart)이
/// 렌더만 하게 한다.
class WishlistTile {
  const WishlistTile.card(this.listing)
      : blockedListingId = null,
        blockedTitle = null;

  const WishlistTile.blocked({required String listingId, String? title})
      : listing = null,
        blockedListingId = listingId,
        blockedTitle = title;

  final ListingCardData? listing;
  final String? blockedListingId;
  final String? blockedTitle;

  bool get isBlocked => listing == null;
}

/// embed(본인 소유 sold일 때만 값이 있음, 타인 소유 sold는 RLS가 null로 막음)에서 차단 타일
/// 제목을 뽑는다. embed가 없으면(RLS 차단) 제목을 지어내지 않고 null(화면이 일반 문구로 대신).
String? _blockedTitle(Map<String, dynamic>? embed) {
  if (embed == null) return null;
  final manufacturer = embed['manufacturer'];
  final model = embed['model'];
  final year = asInt(embed['year']);
  if (manufacturer is! String || model is! String || year == null) return null;
  return '[$manufacturer] $model · $year년';
}

/// embed의 `status`를 방어적으로 뽑는다(레포 전반의 관례 — listing.dart `fromMap`·
/// `WishlistEntry.fromMap`과 동일하게 하드 캐스트 대신 `is String` 확인, 코드리뷰 지적: wire
/// 값이 String이 아니면 provider 전체가 예외로 죽어 찜 탭이 통째로 에러 화면이 됐었다).
/// entry당 한 번만 계산해 아래 두 곳(on_sale id 추림·타일 분기)에 재사용한다(이전엔 같은 값을
/// 두 번 평가했다).
String? _entryStatus(Map<String, dynamic>? embed) {
  final raw = embed?['status'];
  return raw is String ? raw : null;
}

/// 찜 목록 AsyncValue — entries를 원래(최신순) 순서 그대로 한 번만 순회하며 타일을 만든다.
/// autoDispose: 찜 탭을 벗어나면 캐시를 버려, 다음 진입 시 항상 최신 DB 상태를 반영한다
/// (web `export const dynamic = 'force-dynamic'`과 같은 의도 — "방금 취소한 찜이 즉시 사라져야 함").
final wishlistProvider = FutureProvider.autoDispose<List<WishlistTile>>((ref) async {
  final repo = ref.watch(wishlistRepositoryProvider);
  final entries = await repo.fetchWishlist();
  final statuses = [for (final e in entries) _entryStatus(e.embed)];

  // on_sale(=차단 아님) 항목만 모아 대표사진을 한 번에 조회 → id로 다시 찾을 수 있게 Map으로.
  final onSaleIds = <String>[
    for (var i = 0; i < entries.length; i++)
      if (!isWishlistBlocked(entries[i].embed, statuses[i])) entries[i].listingId,
  ];
  final covers = await repo.fetchCovers(onSaleIds);

  final tiles = <WishlistTile>[];
  for (var i = 0; i < entries.length; i++) {
    final e = entries[i];
    if (isWishlistBlocked(e.embed, statuses[i])) {
      tiles.add(WishlistTile.blocked(listingId: e.listingId, title: _blockedTitle(e.embed)));
      continue;
    }
    // isWishlistBlocked가 false면 embed는 non-null이 보장된다(판정 함수 정의 참조).
    final cover = covers[e.listingId];
    final card = ListingCardData.fromMap({
      ...e.embed!,
      'image_url': cover == null ? null : getPublicUrl(listingImagesBucket, cover.path),
      'image_count': cover?.count ?? 0,
    });
    // fromMap이 계약 위반으로 null을 돌려주면(방어적) 그 행만 조용히 생략한다(전체 렌더를
    // 막지 않는다, web "못 찾으면 생략" 원칙과 동일 — 정상 데이터라면 사실상 도달 불가).
    if (card != null) tiles.add(WishlistTile.card(card));
  }
  return tiles;
});
