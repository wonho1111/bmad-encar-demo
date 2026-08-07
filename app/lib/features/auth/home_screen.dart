// 인증 후 홈 — AI 검색부(①, 최상단) + 매물 탐색 진입(②) + 최근 매물 미리보기.
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
// ⚠️ **Story 16.1 반영**: D12의 나머지 절반인 하단 4탭(홈(AI)·찜·채팅·내차팔기)이 라우터 셸
//   (`core/router/app_router.dart`)에 생겼다. 그래서 이 화면은 더 이상 자체 AppBar를 갖지
//   않는다 — 상단 타이틀·우상단 프로필 아바타는 그 셸이 공통으로 제공한다(Scaffold에
//   appBar를 주지 않는 이유). 로그아웃 텍스트버튼·프로필 카드도 그 아바타 메뉴로 이관됐다.
//   AI 검색부는 웹 DESIGN.md 히어로 규칙대로 petrol 그라데이션 + amber 강조로 재도장했다
//   (글로우/메시/차량 실루엣 아트는 데모 범위 밖 — spec-16-1 Never).
//
//   ⚠️ **셸 경계(spec-16-1 Code Map)**: 이 화면은 하단 4탭 셸의 '홈' 브랜치 루트다 —
//   `StatefulShellRoute`가 브랜치별 Navigator를 보존하므로, 이 화면에서 다른 화면으로
//   `Navigator.push`하면 그 push는 브랜치의 (셸에 감싸인) Navigator에 쌓인다. 셸이 이미
//   AppBar·NavigationBar를 그리고 있으므로, 상세류(AI 채팅·탐색·문의 채팅·매물 등록·
//   내 매물 관리·매물 상세)를 그 안에 쌓으면 AppBar가 2개, 하단 탭이 상세 위에 남는
//   레이아웃 결함이 생긴다(실측 확인, Spec Change Log 2026-08-07 #2). 그래서 아래 모든
//   push는 `rootNavigator: true`로 셸 밖(앱의 진짜 루트 Navigator)으로 보낸다.
// 관리자(admin)는 모바일 제외(AR9) → app_router.dart의 redirect가 차단 화면으로 보낸다.
// 기능·동선·위젯 Key 는 그대로, 겉모습만 데모용으로 보강.
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
    // 역할 통합(FR52·FR53): 판매 진입을 **로그인 사용자 전원**에게 보인다.
    // 옛 코드는 `role == UserRole.seller`일 때만 보여줬는데, 그러면 게이트를 풀어도
    // 화면이 안 보여 도달할 수가 없다 — 문을 열었으면 문패도 보여야 한다.
    // 웹도 같다: 상단바의 '내 차 팔기'는 역할과 무관하게 항상 있다.
    final canSell = user != null;

    // appBar 없음(위 주석) — 셸의 Material 이 InkWell 등에 필요한 Material 조상 역할도
    // 겸하므로 Scaffold(body:) 만으로 충분하다.
    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: SafeArea(
        top: false,
        child: RefreshIndicator(
          // 당겨서 새로고침 → 최근 매물 재조회(등록·판매완료 후 수동 갱신 경로).
          onRefresh: () => ref.refresh(recentListingsProvider.future),
          child: SingleChildScrollView(
            // 내용이 짧아도 당겨서 새로고침이 되도록 항상 스크롤 가능.
            physics: const AlwaysScrollableScrollPhysics(),
            // 하단 패딩: 시스템 내비바 가림 방지. `viewPadding.bottom`이 아니라
            // `MediaQuery.paddingOf(context).bottom`을 쓴다 — 셸의 `NavigationBar`가
            // 이미 그 시스템 인셋을 흡수해 Scaffold가 `padding`에서 걷어내므로,
            // 원본 `viewPadding`을 또 더하면 하단 여백이 이중으로 커진다(spec-16-1 Task).
            padding: EdgeInsets.fromLTRB(
                16, 16, 16, 24 + MediaQuery.paddingOf(context).bottom),
          child: Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 480),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // AI 검색부 — **홈 최상단**(D12). "AI가 제품의 얼굴"이라는 위계를 위치로
                  // 표현한다: 매물 탐색 CTA(R2)보다 위에 둔다. 웹 홈도 히어로가 최상단이다.
                  _AiSearchCta(
                    onTap: () => Navigator.of(context, rootNavigator: true).push(
                      MaterialPageRoute(builder: (_) => const AiChatScreen()),
                    ),
                  ),
                  const SizedBox(height: 14),

                  // 검색 CTA(R2) — 1순위 과업으로 크게.
                  _SearchCta(
                    onTap: () => Navigator.of(context, rootNavigator: true).push(
                      MaterialPageRoute(builder: (_) => const SearchScreen()),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 퀵액션 — 문의 채팅(공통). 판매자면 매물 등록·내 매물 관리 추가.
                  // 하단 "채팅"·"내차팔기" 탭과 목적지가 겹치지만, 이 스토리는 내비 셸
                  // 추가이지 홈 정보구조 재설계가 아니라서 그대로 둔다(spec-16-1 Never).
                  _QuickAction(
                    actionKey: const Key('go_chat'),
                    icon: Icons.chat_bubble_outline,
                    label: '문의 채팅',
                    onTap: () => Navigator.of(context, rootNavigator: true).push(
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
                            onTap: () => Navigator.of(context, rootNavigator: true)
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
                            onTap: () => Navigator.of(context, rootNavigator: true)
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
                        onTap: () => Navigator.of(context, rootNavigator: true).push(
                          MaterialPageRoute(builder: (_) => const SearchScreen()),
                        ),
                        child: const Padding(
                          padding: EdgeInsets.all(4),
                          child: Text('더보기 ›',
                              style: TextStyle(color: AppColors.inkMuted, fontSize: 13)),
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

/// 검색 CTA — 큰 카드(엔카 "어떤 차를 찾고 있나요?" 스타일). 누르면 매물 탐색.
/// AI 검색 진입 — 홈 최상단(D12: "AI 검색 = FAB 아님. 홈 최상단 큰 검색부").
/// petrol 그라데이션(brand-petrol-strong → petrol-deepest, DESIGN.md AI 히어로 밴드 규칙)으로
/// `_SearchCta`(매물 탐색)와 위계를 가른다 — 둘이 나란히 있을 때 어느 쪽이 이 제품의 얼굴인지
/// 보여야 한다(D12의 "AI가 제품의 얼굴" 위계). 글로우/메시/차량 실루엣 아트는 재현하지 않는다
/// (spec-16-1 Never — 데모 범위의 과잉 크래프트 방지).
/// amber는 이 카드의 아이콘 배지 하나에만 쓴다(DESIGN.md "화면당 amber는 손에 꼽을 정도로") —
/// amber 위 아이콘은 규칙대로 어두운 잉크(`inkPrimary`), 흰색 금지.
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
          borderRadius: BorderRadius.circular(12),
          gradient: const LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [AppColors.brandPetrolStrong, AppColors.petrolDeepest],
          ),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: const BoxDecoration(
                color: AppColors.accentAmber,
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.smart_toy_outlined,
                  color: AppColors.inkPrimary, size: 20),
            ),
            const SizedBox(width: 12),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('원하는 차를 말로 찾으세요',
                      style: TextStyle(
                          color: AppColors.onPetrol,
                          fontSize: 15,
                          fontWeight: FontWeight.w700)),
                  SizedBox(height: 2),
                  // 웹 히어로 placeholder와 같은 예시 문구(D13 마이크로카피).
                  Text('예: 3천만원대 무사고 흰색 SUV',
                      style: TextStyle(color: AppColors.onPetrolMuted, fontSize: 13)),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.onPetrolMuted),
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
          color: AppColors.surfaceRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.borderHairline),
        ),
        child: const Row(
          children: [
            Icon(Icons.search, color: AppColors.inkMuted, size: 22),
            SizedBox(width: 12),
            Expanded(
              child: Text('어떤 차를 찾고 있나요?',
                  style: TextStyle(color: AppColors.inkMuted, fontSize: 15)),
            ),
            Icon(Icons.chevron_right, color: AppColors.inkMuted),
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
          color: AppColors.surfaceRaised,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.borderHairline),
        ),
        child: Row(
          children: [
            Icon(icon, color: AppColors.brandPetrol, size: 20),
            const SizedBox(width: 8),
            Flexible(
              child: Text(label,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: AppColors.inkPrimary,
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
            style: TextStyle(color: AppColors.inkMuted)),
      ),
      data: (listings) {
        if (listings.isEmpty) {
          return const Padding(
            padding: EdgeInsets.symmetric(vertical: 16),
            child: Text('등록된 매물이 없습니다.',
                style: TextStyle(color: AppColors.inkMuted)),
          );
        }
        return Column(
          // 카드가 카드 폭을 꽉 채우도록 stretch(없으면 내용 너비로 줄어 가운데 정렬돼 들쭉날쭉).
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final l in listings)
              ListingCard(
                listing: l,
                onTap: () => Navigator.of(context, rootNavigator: true).push(
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
