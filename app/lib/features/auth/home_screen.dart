// 인증 후 홈 — AI 검색부(①, 최상단) + 역할·이메일 + 매물 탐색 진입(②) + 최근 매물 미리보기.
// nav-ia-rules §1·§2: 구매자/판매자 공통 홈(R1 상위집합), 1순위 과업=매물 탐색(R2).
//   판매자 전용(등록·관리)은 역할에 따라 노출.
//
// ⚠️ **AI 진입은 2026-08-07에 FAB → 홈 최상단 검색부로 옮겼다.** 원래는 nav-ia-rules R3
//   (*"Flutter에서는 FAB 또는 상시 탭으로"*)를 근거로 FAB였는데, 2026-07-12 UX 확정 D12가
//   그걸 **명시적으로 폐기**했다:
//     *"AI 검색 = FAB 아님. **홈 최상단 큰 검색부**(웹 히어로 딥 petrol 밴드의 앱 번역판).
//       'AI가 제품의 얼굴'이라는 위계를 웹·앱 1:1 대응. (이전 앱의 AI=FAB는 'AI가 부가기능'
//       이던 흔적 → 폐기.)"*
//   근거는 Material Design 안티패턴(검색을 단일 FAB에 넣는 것)과 P2P 관례(FAB=생성 액션)다.
//   같은 날 웹의 떠 있는 'AI 검색' 버튼도 같은 이유로 제거했다(`web/src/app/page.tsx`).
//
//   ⚠️ **아직 안 된 것**: D12의 나머지 절반인 **하단 4탭(홈(AI)·찜·채팅·내차팔기)** 은
//   Story 16.1 몫이라 여기 없다. 웹 디자인 토큰(petrol 밴드) 미러링도 16.1이다 — 그래서
//   이 검색부는 **지금 앱 스타일(zinc/차콜)** 로 만들었다. 16.1이 이 자리를 히어로 밴드로
//   바꾸면서 하단 탭을 붙인다. 그때까지도 AI 진입로는 끊기지 않는다(그래서 FAB만 떼지 않았다).
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

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final loading = ref.watch(authControllerProvider).isLoading;
    // 역할 통합(FR52·FR53): 판매 진입을 **로그인 사용자 전원**에게 보인다.
    // 옛 코드는 `role == UserRole.seller`일 때만 보여줬는데, 그러면 게이트를 풀어도
    // 화면이 안 보여 도달할 수가 없다 — 문을 열었으면 문패도 보여야 한다.
    // 웹도 같다: 상단바의 '내 차 팔기'는 역할과 무관하게 항상 있다.
    final canSell = user != null;

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
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          // 당겨서 새로고침 → 최근 매물 재조회(등록·판매완료 후 수동 갱신 경로).
          onRefresh: () => ref.refresh(recentListingsProvider.future),
          child: SingleChildScrollView(
            // 내용이 짧아도 당겨서 새로고침이 되도록 항상 스크롤 가능.
            physics: const AlwaysScrollableScrollPhysics(),
            // 하단 패딩: 시스템 내비바 가림 방지(FAB이 없어져 그만큼의 여유는 뺐다).
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, 24 + MediaQuery.of(context).viewPadding.bottom),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // AI 검색부 — **홈 최상단**(D12). "AI가 제품의 얼굴"이라는 위계를 위치로
                  // 표현한다: 매물 탐색 CTA(R2)보다 위에 둔다. 웹 홈도 히어로가 최상단이다.
                  _AiSearchCta(
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const AiChatScreen()),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // 프로필 카드 — 이메일. 역할 배지는 '회원' 고정이다(역할 통합):
                  // 구매자/판매자 구분이 사라져 표시할 역할이 없고, 관리자는 모바일에서
                  // 애초에 차단되므로(main.dart, AR9) 이 화면에 도달하지 않는다.
                  _ProfileCard(
                    roleLabel: '회원',
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
                  if (canSell) ...[
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
/// AI 검색 진입 — 홈 최상단(D12: "AI 검색 = FAB 아님. 홈 최상단 큰 검색부").
/// `_SearchCta`(매물 탐색)와 같은 모양을 쓰되 **채움색으로 위계를 준다** — 둘이 나란히
/// 있을 때 어느 쪽이 이 제품의 얼굴인지가 보여야 한다(D12의 "AI가 제품의 얼굴" 위계).
/// ⚠️ 색은 지금 앱 토큰(zinc/차콜)이다. 웹의 petrol 히어로 밴드 미러링은 Story 16.1 몫.
class _AiSearchCta extends StatelessWidget {
  const _AiSearchCta({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      key: const Key('go_ai'),
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 18),
        decoration: BoxDecoration(
          color: AppColors.ink,
          borderRadius: BorderRadius.circular(12),
        ),
        child: const Row(
          children: [
            Icon(Icons.smart_toy_outlined, color: Colors.white, size: 22),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('원하는 차를 말로 찾으세요',
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w700)),
                  SizedBox(height: 2),
                  // 웹 히어로 placeholder와 같은 예시 문구(D13 마이크로카피).
                  Text('예: 3천만원대 무사고 흰색 SUV',
                      style: TextStyle(color: Color(0xFFD4D4D8), fontSize: 13)),
                ],
              ),
            ),
            Icon(Icons.chevron_right, color: Color(0xFFD4D4D8)),
          ],
        ),
      ),
    );
  }
}

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
