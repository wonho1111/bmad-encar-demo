// 매물 카드 위젯 — 탐색 목록·AI 검색 결과가 공유한다(web ListingCard 의 Flutter 판).
// 사진 없음. 7필드 요약(제조사·모델·연식 / 가격·주행·지역) + (있으면) 판매자 이름.
// 누르면 매물 상세로 이동(onTap 콜백을 받아 상위가 라우팅 — 화면 의존을 줄임).
import 'package:flutter/material.dart';

import '../../core/format/number_format.dart';
import 'listing.dart';

class ListingCard extends StatelessWidget {
  const ListingCard({super.key, required this.listing, this.onTap});

  final ListingCardData listing;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 제조사·모델·연식 — 한 줄 요약.
              Text(
                '[${listing.manufacturer}] ${listing.model} · ${listing.year}년',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
              const SizedBox(height: 4),
              // 가격·주행거리·지역 — 단위 규칙(원·km, 천단위 콤마).
              Text(
                '${wonText(listing.price)} · ${kmText(listing.mileage)} · ${listing.region}',
                style: TextStyle(color: Colors.grey[600], fontSize: 13),
              ),
              // 판매자 표시 이름(있을 때만). AI 결과처럼 값이 없으면 줄 자체를 숨긴다.
              if (listing.sellerName != null && listing.sellerName!.isNotEmpty) ...[
                const SizedBox(height: 2),
                Text(
                  '판매자 ${listing.sellerName}',
                  style: TextStyle(color: Colors.grey[500], fontSize: 11),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
