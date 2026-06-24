// 매물 상세 화면(FR10·11 재현) — id 로 판매중 매물 1건을 조회해 FR5 15필드 + 옵션·설명을 표시.
// 사진 없음. 못 찾음(없음·sold·삭제)·조회 실패를 구분해 안내한다(web listings/[id] 패턴).
// 뒤로가기는 시스템 back(AppBar 기본 ← ) — 출처(탐색/AI결과)로 복귀(nav-ia R5).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format/number_format.dart';
import 'listing.dart';
import 'listings_providers.dart';

class ListingDetailScreen extends ConsumerWidget {
  const ListingDetailScreen({super.key, required this.listingId});

  final String listingId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detailAsync = ref.watch(listingDetailProvider(listingId));

    return Scaffold(
      appBar: AppBar(title: const Text('매물 상세')),
      body: detailAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        // 조회 실패(네트워크·RLS·DB) — "못 찾음"과 구분해 빨강 에러.
        error: (e, _) => _MessageBody(
          key: const Key('detail_error'),
          icon: Icons.error_outline,
          color: Colors.red,
          message: '매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
        ),
        data: (listing) {
          // 못 찾음(없는 id·sold·삭제) → 구매자에게 비노출(FR11).
          if (listing == null) {
            return const _MessageBody(
              key: Key('detail_not_found'),
              icon: Icons.search_off,
              color: Colors.grey,
              message: '매물을 찾을 수 없습니다. 판매가 완료되었거나 삭제된 매물일 수 있습니다.',
            );
          }
          return _DetailContent(listing: listing);
        },
      ),
    );
  }
}

/// 못찾음/에러 공통 안내 본문.
class _MessageBody extends StatelessWidget {
  const _MessageBody({
    super.key,
    required this.icon,
    required this.color,
    required this.message,
  });

  final IconData icon;
  final Color color;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}

/// 상세 본문 — 제목 + 기본정보(15필드) + 옵션 + 설명.
class _DetailContent extends StatelessWidget {
  const _DetailContent({required this.listing});

  final ListingDetail listing;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        // 제목 = 제조사·모델 + 상태 배지(on_sale 만 도달하므로 "판매중").
        Row(
          children: [
            Expanded(
              child: Text(
                '[${listing.manufacturer}] ${listing.model}',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: Colors.green[100],
                borderRadius: BorderRadius.circular(4),
              ),
              child: Text(
                '판매중',
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                  color: Colors.green[800],
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(
          '${listing.year}년 · ${wonText(listing.price)}',
          style: TextStyle(color: Colors.grey[600]),
        ),
        const SizedBox(height: 20),

        // 기본 정보(FR5 15필드). 사진 없음.
        const Text('기본 정보', style: TextStyle(fontWeight: FontWeight.bold)),
        const SizedBox(height: 8),
        _row('제조사', listing.manufacturer),
        _row('모델', listing.model),
        _row('차종', listing.bodyType),
        _row('연식', '${listing.year}년'),
        _row('가격', wonText(listing.price)),
        _row('주행거리', kmText(listing.mileage)),
        _row('색상', listing.color),
        _row('연료', listing.fuel),
        _row('변속기', listing.transmission),
        _row('배기량', ccText(listing.displacement)),
        _row('승차인원', '${listing.seats}인승'),
        _row('지역', listing.region),
        _row('사고여부', listing.accidentFree ? '무사고' : '사고이력 있음'),
        if (listing.sellerName != null && listing.sellerName!.isNotEmpty)
          _row('판매자', listing.sellerName!),

        // 옵션(있을 때만).
        if (listing.options != null && listing.options!.isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('옵션', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: listing.options!
                .map((o) => Chip(label: Text(o, style: const TextStyle(fontSize: 12))))
                .toList(),
          ),
        ],

        // 설명(있을 때만).
        if (listing.description != null && listing.description!.trim().isNotEmpty) ...[
          const SizedBox(height: 16),
          const Text('설명', style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text(listing.description!),
        ],
      ],
    );
  }

  Widget _row(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 88,
            child: Text(label, style: TextStyle(color: Colors.grey[600])),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }
}
