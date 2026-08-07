// 매물 카드 위젯 — 탐색 목록·AI 검색 결과·홈 미리보기가 공유한다(web ListingCard 의 Flutter 판).
// 사진 5:3 대표 + "N장" 배지(Story 16.2, web ListingCardImage.tsx 미러) +
// 요약(제조사·모델·연식 / 가격(강조) / 주행·연료·지역, Story 10.1·대장 #67) + (있으면) 판매자 이름.
// 누르면 매물 상세로 이동(onTap 콜백을 받아 상위가 라우팅 — 화면 의존을 줄임).
// 디자인: 웹 DESIGN.md 라이트 팔레트(Story 16.1) — 흰 카드 + border-hairline, 가격을 굵게 강조.
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'listing.dart';
import 'listing_photo_widgets.dart';

class ListingCard extends StatelessWidget {
  const ListingCard({super.key, required this.listing, this.onTap});

  final ListingCardData listing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      elevation: 0,
      color: AppColors.surfaceRaised,
      clipBehavior: Clip.antiAlias, // 사진 셀이 카드 위쪽 라운드 밖으로 삐져나오지 않게.
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.borderHairline),
      ),
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _CardPhoto(listing: listing),
            Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 제조사·모델·연식 — 한 줄 요약.
                  Text(
                    '[${listing.manufacturer}] ${listing.model} · ${listing.year}년',
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, color: AppColors.inkPrimary),
                  ),
                  const SizedBox(height: 3),
                  // 가격 — 굵게 강조(원·천단위 콤마).
                  Text(
                    wonText(listing.price),
                    style: const TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 15,
                        color: AppColors.inkPrimary),
                  ),
                  const SizedBox(height: 3),
                  // 주행거리·연료·지역 — 보조 정보(muted). web ListingCard.tsx meta 줄과 같은 모양
                  // (`주행 · 연료 · 지역`, 대장 #67) — fuel이 없으면(계약-외 값) 그 마디만 생략한다.
                  // 한 줄 가로 유지(D5) — 넘치면 줄바꿈이 아니라 ellipsis로 자른다.
                  Text(
                    <String?>[kmText(listing.mileage), listing.fuel, listing.region]
                        .where((s) => s != null && s.isNotEmpty)
                        .join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: AppColors.inkMuted, fontSize: 12.5),
                  ),
                  // 판매자 표시 이름(있을 때만). AI 결과처럼 값이 없으면 줄 자체를 숨긴다.
                  if (listing.sellerName != null && listing.sellerName!.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Text(
                      '판매자 ${listing.sellerName}',
                      style: const TextStyle(color: AppColors.inkMuted, fontSize: 11),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 카드 상단 5:3 대표사진 — 없으면 플레이스홀더, 로드 실패도 같은 플레이스홀더로 폴백.
/// "N장" 배지는 `imageCount>=1`이면 사진 로드 성공 여부와 무관하게 표시한다(장수는 DB 행 수
/// 그대로가 아니라 계약-검증을 통과한 행 수다 — listings_repository.dart의 pickCoverImages 참조).
class _CardPhoto extends StatelessWidget {
  const _CardPhoto({required this.listing});

  final ListingCardData listing;

  @override
  Widget build(BuildContext context) {
    final url = listing.imageUrl;
    // 계약-외 값 정규화(conventions.md §4): 음수 count는 0으로 하한 처리(장수는 계약-검증을
    // 통과한 행 수 기준이다 — listings_repository.dart의 pickCoverImages 참조).
    final rawCount = listing.imageCount ?? 0;
    final count = rawCount < 0 ? 0 : rawCount;

    return AspectRatio(
      aspectRatio: 5 / 3,
      child: Stack(
        fit: StackFit.expand,
        children: [
          if (url == null || url.isEmpty)
            const PhotoPlaceholder()
          else
            LayoutBuilder(
              builder: (context, constraints) {
                // 표시 크기로 디코드해 메모리 사용을 실제 셀 크기에 맞춘다(원본 대신 셀 픽셀
                // 크기로 디코드 — 목록의 카드 수만큼 원본 전체를 메모리에 올리지 않는다).
                final width =
                    constraints.maxWidth * MediaQuery.devicePixelRatioOf(context);
                final cacheWidth = width.isFinite && width > 0 ? width.round() : null;
                return Image.network(
                  url,
                  fit: BoxFit.cover,
                  cacheWidth: cacheWidth,
                  errorBuilder: (context, error, stackTrace) {
                    // 사진은 부가정보 — 로드 실패를 "판매자가 사진을 안 올림"과 구분해 남긴다.
                    debugPrint('매물 카드 사진 로드 실패($url): $error');
                    return const PhotoPlaceholder();
                  },
                );
              },
            ),
          if (count >= 1)
            Positioned(bottom: 8, right: 8, child: PhotoCountBadge(text: '$count장')),
        ],
      ),
    );
  }
}
