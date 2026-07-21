// 매물 카드 위젯 — 탐색 목록·AI 검색 결과·홈 미리보기가 공유한다(web ListingCard 의 Flutter 판).
// 사진 없음. 요약(제조사·모델·연식 / 가격(강조) / 주행·연료·지역, Story 10.1·대장 #67) + (있으면) 판매자 이름.
// 누르면 매물 상세로 이동(onTap 콜백을 받아 상위가 라우팅 — 화면 의존을 줄임).
// 디자인: 웹 차콜/zinc 미니멀 — 흰 카드 + zinc-200 보더, 가격을 굵게 강조.
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import 'listing.dart';

class ListingCard extends StatelessWidget {
  const ListingCard({super.key, required this.listing, this.onTap});

  final ListingCardData listing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 제조사·모델·연식 — 한 줄 요약.
              Text(
                '[${listing.manufacturer}] ${listing.model} · ${listing.year}년',
                style: const TextStyle(
                    fontWeight: FontWeight.w600, color: AppColors.ink2),
              ),
              const SizedBox(height: 3),
              // 가격 — 굵게 강조(원·천단위 콤마).
              Text(
                wonText(listing.price),
                style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                    color: AppColors.ink2),
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
                style: const TextStyle(color: AppColors.muted, fontSize: 12.5),
              ),
              // 판매자 표시 이름(있을 때만). AI 결과처럼 값이 없으면 줄 자체를 숨긴다.
              if (listing.sellerName != null && listing.sellerName!.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  '판매자 ${listing.sellerName}',
                  style: const TextStyle(color: Color(0xFFA1A1AA), fontSize: 11),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
