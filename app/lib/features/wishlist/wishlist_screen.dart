// 찜 목록 화면(Story 16.3) — `WishlistPlaceholderScreen`(Story 16.1)을 대체한다.
// 본인 찜 매물을 최신순으로: on_sale이면 정상 카드(하트 눌러 바로 해제 가능), 판매완료거나
// RLS로 막힌(타인 소유 sold) 매물이면 회색 비활성 타일 + "판매완료" 배지로 표시하고 상세
// 진입을 막는다(FR11, web isWishedListingBlocked 미러). 0건이면 빈 상태 안내.
// appBar 없음 — 셸(app_router.dart)의 공통 AppBar(탭 제목 + 우상단 프로필 아바타)를 그대로 쓴다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../listings/listing_card.dart';
import '../listings/listing_detail_screen.dart';
import 'wishlist_providers.dart';

class WishlistScreen extends ConsumerWidget {
  const WishlistScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(wishlistProvider);

    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              '찜 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
              key: Key('wishlist_error'),
              style: TextStyle(color: AppColors.danger),
              textAlign: TextAlign.center,
            ),
          ),
        ),
        data: (tiles) {
          if (tiles.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(24),
                child: Column(
                  key: Key('wishlist_empty'),
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(Icons.favorite_border, size: 48, color: AppColors.inkMuted),
                    SizedBox(height: 16),
                    Text(
                      '아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: AppColors.inkMuted, fontSize: 15),
                    ),
                  ],
                ),
              ),
            );
          }
          return ListView.builder(
            // 하단 패딩: `viewPadding.bottom`이 아니라 `MediaQuery.paddingOf(context).bottom`.
            // 셸의 `NavigationBar`가 이미 시스템 인셋을 흡수해 Scaffold가 `padding`에서
            // 걷어내므로, 원본 `viewPadding`을 또 더하면 하단 여백이 이중으로 커진다.
            // (2026-08-10 Epic 16 묶음 코드리뷰, 리뷰어 2명이 독립 발견 — 셸 브랜치 루트 4개
            //  중 이 화면만 옛 패턴이었다. 형제 3개는 이미 `paddingOf`다:
            //  home_screen.dart:113 · chat_list_screen.dart:84 · sell_screen.dart:313)
            padding: EdgeInsets.fromLTRB(
                12, 12, 12, 12 + MediaQuery.paddingOf(context).bottom),
            itemCount: tiles.length,
            itemBuilder: (context, i) {
              final tile = tiles[i];
              if (tile.isBlocked) {
                return _BlockedWishTile(
                  key: ValueKey('blocked_${tile.blockedListingId}'),
                  title: tile.blockedTitle,
                );
              }
              final listing = tile.listing!;
              return ListingCard(
                // 차단 타일과 동일하게 안정적인 key를 준다 — 없으면 목록이 줄어들 때(찜 해제 등)
                // Flutter가 같은 위치의 Element/State(WishButton 포함)를 다른 매물에 재사용해,
                // 방금 해제한 카드의 pending/낙관적 하트 상태가 잠깐 엉뚱한 매물에 붙어 보일 수
                // 있다(코드리뷰 지적).
                key: ValueKey(listing.id),
                listing: listing,
                wished: true, // 이 화면에 있다는 것 자체가 찜된 상태(정의상 항상 true).
                onTap: () => Navigator.of(context, rootNavigator: true).push(
                  MaterialPageRoute(
                      builder: (_) => ListingDetailScreen(listingId: listing.id)),
                ),
              );
            },
          );
        },
      ),
    );
  }
}

/// 판매완료(또는 RLS로 안 보이는 타인 소유 sold) 매물의 회색 비활성 타일. 상세 링크 없음
/// (진입 차단, FR11·UX-DR20). embed가 있으면(본인 소유 sold) 차량명을, 없으면(RLS 차단)
/// 일반 문구를 보여준다 — 없는 정보를 지어내지 않는다(web BlockedWishTile 미러).
class _BlockedWishTile extends StatelessWidget {
  const _BlockedWishTile({super.key, required this.title});

  final String? title;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: 0.6,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AppColors.surfaceRaised,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: AppColors.borderHairline),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                border: Border.all(color: AppColors.borderHairline),
                borderRadius: BorderRadius.circular(11),
              ),
              child: const Text(
                '판매완료',
                style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w600, color: AppColors.inkSecondary),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                title ?? '판매완료된 매물',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: AppColors.inkSecondary),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
