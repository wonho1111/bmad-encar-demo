// 본인 매물 수정 진입 화면(7.4, FR6 재현).
//
// web (user)/sell/[id]/edit/page.tsx 이식:
//   1) 본인 매물만(seller_id 필터 + RLS) 단건 조회 — 타인·없음이면 한국어 차단(이중 방어).
//   2) 판매완료(sold) 매물은 수정 진입 차단(거래 끝난 매물 정보 변경 방지) — URL 직접 접근 대비 화면에서도 막는다.
//   3) 본인 on_sale 매물이면 SellScreen(수정 모드)에 상세를 넘겨 폼을 채운다(같은 15필드 폼 재사용).
//
// 조회는 FutureProvider.family(editListingProvider)로 — 화면이 watch 하면 로딩/에러/데이터 자동 분기.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../auth/user_role.dart';
import 'listings_providers.dart';
import 'listings_repository.dart' show statusOnSale;
import 'sell_screen.dart';

class EditListingScreen extends ConsumerWidget {
  const EditListingScreen({super.key, required this.listingId});

  final String listingId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final role = ref.watch(currentRoleProvider);

    // 역할 가드(AC5): 판매자만 수정 진입.
    if (role != UserRole.seller) {
      return Scaffold(
        appBar: AppBar(title: const Text('매물 수정')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              '판매자만 이용할 수 있습니다.',
              key: Key('edit_role_blocked'),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    final detailAsync = ref.watch(editListingProvider(listingId));

    return detailAsync.when(
      loading: () => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      ),
      error: (e, _) => _message(
        context,
        '매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
        key: 'edit_load_error',
      ),
      data: (detail) {
        // 본인 매물이 아니거나 존재하지 않음(0행 → null) — 한국어 차단(AC2).
        if (detail == null) {
          return _message(
            context,
            '매물을 찾을 수 없거나 접근 권한이 없습니다. 본인 매물만 수정할 수 있습니다.',
            key: 'edit_not_found',
          );
        }
        // 판매완료(sold) 매물은 수정 진입 차단(이중 방어 — 목록에서 버튼을 숨기지만 직접 진입 대비).
        if (detail.status != statusOnSale) {
          return _message(
            context,
            '판매완료된 매물은 수정할 수 없습니다.',
            key: 'edit_sold_blocked',
          );
        }
        // 본인 on_sale 매물 → 등록 폼을 재사용한 수정 화면(상세를 넘겨 폼을 채움).
        return SellScreen(editDetail: detail);
      },
    );
  }

  Widget _message(BuildContext context, String text, {required String key}) {
    return Scaffold(
      appBar: AppBar(title: const Text('매물 수정')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(text, key: Key(key), textAlign: TextAlign.center),
              const SizedBox(height: 16),
              OutlinedButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('내 매물 목록으로'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
