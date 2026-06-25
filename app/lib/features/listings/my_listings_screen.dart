// 내 매물 관리 화면(7.4, FR6·8 재현) — 판매자가 본인 매물을 보고 수정·삭제·구매완료한다.
//
// 구성:
//   · 본인 매물 목록(seller_id 필터 + RLS) — 각 행에 요약 + 상태 배지(판매중/판매완료) + 동작.
//   · 판매중(on_sale): [구매 완료]·[수정]·[삭제]. 판매완료(sold): [삭제]만(거래 끝난 매물 변경 방지).
//   · 구매완료·삭제는 확인 다이얼로그로 실수 방지. 0행 거부는 컨트롤러가 한국어로 돌려준다.
// 역할 가드(AC5): seller 만 진입(buyer/admin 차단). 7.3 sell_screen 패턴 재사용.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_controller.dart';
import '../auth/user_role.dart';
import 'edit_listing_screen.dart';
import 'listing.dart';
import 'listings_repository.dart' show statusOnSale;
import 'my_listings_controller.dart';

class MyListingsScreen extends ConsumerWidget {
  const MyListingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final role = ref.watch(currentRoleProvider);

    // ── 역할 가드(AC5): 판매자만 ───────────────────────────────────
    if (role != UserRole.seller) {
      return Scaffold(
        appBar: AppBar(title: const Text('내 매물 관리')),
        body: const Center(
          child: Padding(
            padding: EdgeInsets.all(24),
            child: Text(
              '판매자만 이용할 수 있습니다.',
              key: Key('my_listings_role_blocked'),
              textAlign: TextAlign.center,
            ),
          ),
        ),
      );
    }

    final st = ref.watch(myListingsControllerProvider);
    final notifier = ref.read(myListingsControllerProvider.notifier);

    return Scaffold(
      appBar: AppBar(
        title: const Text('내 매물 관리'),
        actions: [
          IconButton(
            key: const Key('my_listings_refresh'),
            onPressed: notifier.load,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // 액션(삭제/구매완료) 실패·거부 한국어 안내.
              if (st.actionError != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                  child: Text(
                    st.actionError!,
                    key: const Key('my_listings_action_error'),
                    style: TextStyle(color: Theme.of(context).colorScheme.error),
                  ),
                ),
              Expanded(
                child: st.listings.when(
                  loading: () =>
                      const Center(child: CircularProgressIndicator()),
                  error: (e, _) => const Center(
                    child: Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        '매물 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
                        key: Key('my_listings_load_error'),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ),
                  data: (list) {
                    if (list.isEmpty) {
                      return const Center(
                        child: Text(
                          '아직 등록한 매물이 없습니다.',
                          key: Key('my_listings_empty'),
                        ),
                      );
                    }
                    return ListView.separated(
                      // 하단 패딩에 시스템 내비바 높이를 더해(edge-to-edge) 마지막 카드 액션이 가리지 않게.
                      padding: EdgeInsets.fromLTRB(
                          16, 16, 16, 16 + MediaQuery.of(context).viewPadding.bottom),
                      itemCount: list.length,
                      separatorBuilder: (_, _) => const SizedBox(height: 8),
                      itemBuilder: (_, i) => _row(context, ref, list[i], st),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// 매물 한 행 — 요약 + 상태 배지 + 동작 버튼. busy 면 동작 비활성(중복 클릭 차단).
  Widget _row(
    BuildContext context,
    WidgetRef ref,
    OwnListing l,
    MyListingsState st,
  ) {
    final notifier = ref.read(myListingsControllerProvider.notifier);
    final onSale = l.status == statusOnSale;
    final busy = st.busyId != null; // 어떤 액션이든 진행 중이면 전체 비활성(단순·안전).

    return Card(
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 제목(제조사·모델·연식) + 상태 배지를 한 행에(제목은 길면 줄바꿈, 배지는 우상단 고정).
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Text(
                    '[${l.manufacturer}] ${l.model} · ${l.year}년',
                    style: const TextStyle(fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 8),
                _badge(onSale),
              ],
            ),
            const SizedBox(height: 4),
            // 가격은 별도 행에 굵게 — 긴 차명에도 레이아웃이 무너지지 않게(ListingCard 와 동일 구조).
            Text(
              _won(l.price),
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15),
            ),
            const SizedBox(height: 8),
            Wrap(
              alignment: WrapAlignment.end,
              spacing: 8,
              children: [
                if (onSale)
                  FilledButton.tonal(
                    key: Key('my_listing_sold_${l.id}'),
                    onPressed: busy ? null : () => _confirmSold(context, ref, l),
                    child: const Text('구매 완료'),
                  ),
                if (onSale)
                  OutlinedButton(
                    key: Key('my_listing_edit_${l.id}'),
                    onPressed: busy
                        ? null
                        : () async {
                            // 수정 화면으로 이동 → 수정 성공(true)이면 목록 새로고침.
                            final changed = await Navigator.of(context).push<bool>(
                              MaterialPageRoute(
                                builder: (_) =>
                                    EditListingScreen(listingId: l.id),
                              ),
                            );
                            if (changed == true) await notifier.load();
                          },
                    child: const Text('수정'),
                  ),
                OutlinedButton(
                  key: Key('my_listing_delete_${l.id}'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Theme.of(context).colorScheme.error,
                  ),
                  onPressed: busy ? null : () => _confirmDelete(context, ref, l),
                  child: const Text('삭제'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _badge(bool onSale) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      decoration: BoxDecoration(
        color: onSale ? Colors.green.shade100 : Colors.grey.shade300,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        onSale ? '판매중' : '판매완료',
        style: TextStyle(
          fontSize: 12,
          fontWeight: FontWeight.w500,
          color: onSale ? Colors.green.shade800 : Colors.grey.shade700,
        ),
      ),
    );
  }

  // 구매 완료 확인 → 컨트롤러 markSold. 취소하면 아무 일도 일어나지 않는다(실수 방지).
  Future<void> _confirmSold(
      BuildContext context, WidgetRef ref, OwnListing l) async {
    final ok = await _confirm(
      context,
      title: '구매 완료 처리',
      body: "'[${l.manufacturer}] ${l.model}' 매물을 구매 완료 처리할까요?\n"
          '처리하면 구매자에게 더 이상 노출되지 않습니다.',
      confirmText: '구매 완료',
    );
    if (ok) await ref.read(myListingsControllerProvider.notifier).markSold(l.id);
  }

  // 삭제 확인 → 컨트롤러 delete.
  Future<void> _confirmDelete(
      BuildContext context, WidgetRef ref, OwnListing l) async {
    final ok = await _confirm(
      context,
      title: '매물 삭제',
      body: "'[${l.manufacturer}] ${l.model}' 매물을 삭제할까요?\n삭제하면 되돌릴 수 없습니다.",
      confirmText: '삭제',
      danger: true,
    );
    if (ok) await ref.read(myListingsControllerProvider.notifier).delete(l.id);
  }

  Future<bool> _confirm(
    BuildContext context, {
    required String title,
    required String body,
    required String confirmText,
    bool danger = false,
  }) async {
    final res = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('취소'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            style: danger
                ? TextButton.styleFrom(
                    foregroundColor: Theme.of(ctx).colorScheme.error)
                : null,
            child: Text(confirmText),
          ),
        ],
      ),
    );
    return res ?? false;
  }

  // 원(KRW) 천단위 콤마(간단). web toLocaleString('ko-KR') 자리.
  String _won(int v) {
    final s = v.toString();
    final buf = StringBuffer();
    for (var i = 0; i < s.length; i++) {
      if (i > 0 && (s.length - i) % 3 == 0) buf.write(',');
      buf.write(s[i]);
    }
    return '${buf.toString()}원';
  }
}
