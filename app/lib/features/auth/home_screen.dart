// 인증 후 홈 — 역할·이메일 + 매물 탐색 진입(②) + AI 검색 전역 진입(③, FAB) + 최근 매물 미리보기.
// nav-ia-rules §1·§2: 구매자/판매자 공통 홈(R1 상위집합), 1순위 과업=매물 탐색(R2),
//   AI 는 전역 진입점(R3, Flutter=FAB). 판매자 전용(등록·관리)은 역할에 따라 노출.
// 관리자(admin)는 모바일 제외(AR9) → main.dart 가 차단 화면으로 보낸다.
// 디자인: 웹 차콜/zinc 미니멀. 프로필 카드 + 검색 CTA + 퀵액션 + 최근 매물(웹 홈과 동형).
//   기능·동선·위젯 Key 는 그대로, 겉모습만 데모용으로 보강.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../ai_search/ai_chat_screen.dart';
import '../chat/chat_list_screen.dart';
import '../listings/listing_card.dart';
import '../listings/listing_detail_screen.dart';
import '../listings/listings_providers.dart';
import '../listings/my_listings_screen.dart';
import '../listings/search_screen.dart';
import '../listings/sell_screen.dart';
import 'auth_controller.dart';
import 'user_role.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final role = ref.watch(currentRoleProvider);
    final loading = ref.watch(authControllerProvider).isLoading;
    final isSeller = role == UserRole.seller;

    return Scaffold(
      appBar: AppBar(
        title: const Text('중고차 직거래'),
        actions: [
          // 로그아웃 — 글자색은 AppBarTheme(검정)을 상속해 가시화(이전 흰색 하드코딩 버그 수정).
          TextButton(
            key: const Key('logout'),
            onPressed: loading
                ? null
                : () => ref.read(authControllerProvider.notifier).signOut(),
            child: const Text('로그아웃'),
          ),
        ],
      ),
      // AI 검색 전역 진입(nav-ia R3) — 어느 화면에서든 닿는 보조 동작을 홈에서 FAB 로.
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('ai_fab'),
        onPressed: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const AiChatScreen()),
        ),
        icon: const Icon(Icons.smart_toy_outlined),
        label: const Text('AI 검색'),
      ),
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          // 당겨서 새로고침 → 최근 매물 재조회(등록·판매완료 후 수동 갱신 경로).
          onRefresh: () => ref.refresh(recentListingsProvider.future),
          child: SingleChildScrollView(
            // 내용이 짧아도 당겨서 새로고침이 되도록 항상 스크롤 가능.
            physics: const AlwaysScrollableScrollPhysics(),
            // 하단 패딩: 시스템 내비바 + FAB 가림 방지.
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, 96 + MediaQuery.of(context).viewPadding.bottom),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 프로필 카드 — 역할 배지 + 이메일.
                  _ProfileCard(
                    roleLabel: role?.label ?? '회원',
                    email: user?.email ?? '-',
                  ),
                  const SizedBox(height: 14),

                  // 검색 CTA(R2) — 1순위 과업으로 크게.
                  _SearchCta(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SearchScreen()),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 퀵액션 — 문의 채팅(공통). 판매자면 매물 등록·내 매물 관리 추가.
                  _QuickAction(
                    actionKey: const Key('go_chat'),
                    icon: Icons.chat_bubble_outline,
                    label: '문의 채팅',
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const ChatListScreen()),
                    ),
                  ),
                  if (isSeller) ...[
                    const SizedBox(height: 12),
                    Row(
                      children: [
                        Expanded(
                          child: _QuickAction(
                            actionKey: const Key('go_sell'),
                            icon: Icons.add_box_outlined,
                            label: '매물 등록',
                            // 등록 후 돌아오면 최근 매물 자동 새로고침.
                            onTap: () => Navigator.of(context)
                                .push(MaterialPageRoute(
                                    builder: (_) => const SellScreen()))
                                .then((_) =>
                                    ref.invalidate(recentListingsProvider)),
                          ),
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                          child: _QuickAction(
                            actionKey: const Key('go_my_listings'),
                            icon: Icons.inventory_2_outlined,
                            label: '내 매물 관리',
                            // 판매완료·삭제 후 돌아오면 최근 매물 자동 새로고침.
                            onTap: () => Navigator.of(context)
                                .push(MaterialPageRoute(
                                    builder: (_) => const MyListingsScreen()))
                                .then((_) =>
                                    ref.invalidate(recentListingsProvider)),
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 22),

                  // 최근 매물 섹션 — 헤더 + 더보기 + 카드 몇 장(웹 홈 미리보기와 동형).
                  Row(
                    children: [
                      Text('최근 매물',
                          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                              fontWeight: FontWeight.w700)),
                      const Spacer(),
                      InkWell(
                        onTap: () => Navigator.of(context).push(
                          MaterialPageRoute(builder: (_) => const SearchScreen()),
                        ),
                        child: const Padding(
                          padding: EdgeInsets.all(4),
                          child: Text('더보기 ›',
                              style: TextStyle(color: AppColors.muted, fontSize: 13)),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  const _RecentListings(),
                ],
              ),
            ),
          ),
        ),
        ),
      ),
    );
  }
}

/// 프로필 카드 — 옅은 면 + 역할 배지(차콜 칩) + 이메일.
class _ProfileCard extends StatelessWidget {
  const _ProfileCard({required this.roleLabel, required this.email});

  final String roleLabel;
  final String email;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: AppColors.surfaceMuted,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
            decoration: BoxDecoration(
              color: AppColors.ink,
              borderRadius: BorderRadius.circular(999),
            ),
            child: Text(
              roleLabel,
              key: const Key('home_role'),
              style: const TextStyle(
                  color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              email,
              key: const Key('home_email'),
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: AppColors.ink2, fontSize: 14),
            ),
          ),
        ],
      ),
    );
  }
}

/// 검색 CTA — 큰 카드(엔카 "어떤 차를 찾고 있나요?" 스타일). 누르면 매물 탐색.
class _SearchCta extends StatelessWidget {
  const _SearchCta({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: const Key('go_search'),
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: const Row(
          children: [
            Icon(Icons.search, color: AppColors.muted, size: 22),
            SizedBox(width: 12),
            Expanded(
              child: Text('어떤 차를 찾고 있나요?',
                  style: TextStyle(color: AppColors.muted, fontSize: 15)),
            ),
            Icon(Icons.chevron_right, color: AppColors.muted),
          ],
        ),
      ),
    );
  }
}

/// 퀵액션 카드 — 아이콘 + 라벨(보더 카드). 문의 채팅·매물 등록·내 매물 관리에 공용.
class _QuickAction extends StatelessWidget {
  const _QuickAction({
    required this.actionKey,
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final Key actionKey;
  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: actionKey,
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.ink, size: 20),
            const SizedBox(width: 8),
            Flexible(
              child: Text(label,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: AppColors.ink2,
                      fontSize: 14,
                      fontWeight: FontWeight.w500)),
            ),
          ],
        ),
      ),
    );
  }
}

/// 최근 매물 목록 — recentListingsProvider 를 watch 해 로딩/에러/빈/데이터 분기.
class _RecentListings extends ConsumerWidget {
  const _RecentListings();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final async = ref.watch(recentListingsProvider);
    return async.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, _) => const Padding(
        padding: EdgeInsets.symmetric(vertical: 16),
        child: Text('최근 매물을 불러오지 못했습니다.',
            style: TextStyle(color: AppColors.muted)),
      ),
      data: (listings) {
        if (listings.isEmpty) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('등록된 매물이 없습니다.',
                style: TextStyle(color: AppColors.muted)),
          );
        }
        return Column(
          // 카드가 카드 폭을 꽉 채우도록 stretch(없으면 내용 너비로 줄어 가운데 정렬돼 들쭉날쭉).
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final l in listings)
              ListingCard(
                listing: l,
                onTap: () => Navigator.of(context).push(
                  MaterialPageRoute(
                      builder: (_) => ListingDetailScreen(listingId: l.id)),
                ),
              ),
          ],
        );
      },
    );
  }
}
