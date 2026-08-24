// 계정·전체메뉴 드로어 — 우상단 아바타를 누르면 **오른쪽에서 밀려 들어오는 패널**.
//
// ✎ 2026-08-13 사용자 결정(레퍼런스 3장: 쏘카·엔카 로그인/비로그인 전체메뉴) — 이 자리는
//   오늘 하루에 세 번 바뀌었다. 경위를 남긴다:
//     ① 안드로이드 기본 팝업 메뉴(`PopupMenuButton`) → "너무 조잡해"(사용자 지적 #2)
//     ② 아래에서 올라오는 모달 바텀시트 → "상용앱에서 저런 걸 본 적이 없는데"
//     ③ **오른쪽에서 들어오는 드로어(지금)** — 사용자가 보내온 실제 앱 3개가 전부 이 형태다.
//   ②가 틀린 컴포넌트였다기보다 **자리가 틀렸다**: 바텀시트는 "하나 고르고 바로 닫는 선택"의
//   자리고(공유·정렬·사진 선택), 계정/전체메뉴는 국내 앱 대부분이 측면 패널이나 전용 화면을 쓴다.
//
// **폭은 화면을 꽉 채우지 않는다**(사용자 선택) — 엔카는 전체메뉴가 화면을 꽉 채우지만 우리는
// 메뉴가 적어서, 쏘카처럼 뒤 화면이 살짝 비치는 부분 폭이 맞다. 뒤가 보이면 "임시로 열린 패널"로
// 읽혀 닫는 법(바깥 탭)이 저절로 드러난다.
//
// 구성은 레퍼런스의 공통 골격을 따른다:
//   로그인  — 계정 헤더(아바타·이메일) + 로그아웃 / 내 것(내 매물 관리·찜·채팅) / 둘러보기(사기·AI)
//   비로그인 — 로그인 권유 한 줄 + [로그인][회원가입] 두 버튼(엔카 비로그인 전체메뉴와 같은 배치)
//              + 로그인 없이도 되는 둘러보기 항목
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../ai_search/ai_chat_screen.dart';
import '../listings/listings_providers.dart';
import '../listings/my_listings_screen.dart';
import '../listings/search_screen.dart';
import 'auth_controller.dart';

/// 드로어 폭 — 화면의 86%를 쓰되 340을 넘지 않는다(태블릿에서 과하게 넓어지지 않게).
/// `Drawer`의 기본값(304 고정)을 쓰지 않는 이유: 폰 폭이 390이면 304는 78%라 괜찮지만,
/// 좁은 기기(360)에서는 84%가 되어 "꽉 찬 것도 아니고 부분도 아닌" 애매한 폭이 된다.
@visibleForTesting
double accountDrawerWidth(double screenWidth) {
  final w = screenWidth * 0.86;
  return w > 340 ? 340 : w;
}

class AccountDrawer extends ConsumerWidget {
  const AccountDrawer({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final loading = ref.watch(authControllerProvider).isLoading;

    return Drawer(
      key: const Key('account_drawer'),
      width: accountDrawerWidth(MediaQuery.sizeOf(context).width),
      backgroundColor: AppColors.surfaceRaised,
      // 오른쪽에서 들어오므로 **왼쪽 모서리만** 둥글다(기본값은 오른쪽 드로어 기준이라 반대다).
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.horizontal(left: Radius.circular(16)),
      ),
      child: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          children: [
            // 닫기 — 바깥을 탭해도 닫히지만, 그건 보이지 않는 조작이라 명시 버튼을 둔다
            // (레퍼런스 두 앱 모두 헤더 우측에 ✕가 있다).
            Align(
              alignment: Alignment.centerRight,
              child: IconButton(
                key: const Key('account_drawer_close'),
                icon: const Icon(Icons.close),
                tooltip: '닫기',
                onPressed: () => Navigator.of(context).pop(),
              ),
            ),
            if (user != null) ...[
              Row(
                children: [
                  const CircleAvatar(
                    radius: 20,
                    backgroundColor: AppColors.brandPetrol,
                    child: Icon(Icons.person, color: AppColors.onPetrol, size: 22),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      user.email ?? '이메일 없음',
                      key: const Key('profile_email'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 14.5,
                          fontWeight: FontWeight.w700,
                          color: AppColors.inkPrimary),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 14),
              const Divider(height: 1, color: AppColors.borderHairline),
              _DrawerItem(
                itemKey: const Key('my_listings'),
                icon: Icons.sell_outlined,
                label: '내 매물 관리',
                onTap: () => _openMyListings(context),
              ),
              _DrawerItem(
                itemKey: const Key('drawer_wishlist'),
                icon: Icons.favorite_border,
                label: '찜한 매물',
                onTap: () => _go(context, '/wishlist'),
              ),
              _DrawerItem(
                itemKey: const Key('drawer_chat'),
                icon: Icons.chat_bubble_outline,
                label: '채팅',
                onTap: () => _go(context, '/chat'),
              ),
              const Divider(height: 1, color: AppColors.borderHairline),
              ..._browseItems(context),
              const Divider(height: 1, color: AppColors.borderHairline),
              _DrawerItem(
                itemKey: const Key('logout'),
                icon: Icons.logout,
                label: '로그아웃',
                // 진행 중엔 흐리게 비활성화(옛 메뉴 항목의 시각 피드백을 그대로 유지).
                enabled: !loading,
                danger: true,
                onTap: () => _signOut(context, ref),
              ),
            ] else ...[
              const Text(
                '로그인하고\n내 차를 찾아보세요',
                key: Key('account_drawer_guest_title'),
                style: TextStyle(
                    fontSize: 18,
                    height: 1.4,
                    fontWeight: FontWeight.w800,
                    color: AppColors.inkPrimary),
              ),
              const SizedBox(height: 14),
              // 로그인·회원가입을 나란히(엔카 비로그인 전체메뉴와 같은 배치) — 둘 다 같은 무게로
              // 두고 회원가입만 강조하지 않는다. 이 데모엔 가입 유인(혜택)이 없어서 강조할 근거가 없다.
              Row(
                children: [
                  Expanded(
                    child: FilledButton(
                      key: const Key('account_login'),
                      onPressed: () => _go(context, '/login'),
                      child: const Text('로그인'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: OutlinedButton(
                      key: const Key('account_signup'),
                      onPressed: () => _push(context, '/signup'),
                      child: const Text('회원가입'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                '매물 둘러보기는 로그인 없이도 계속할 수 있어요.',
                style: TextStyle(fontSize: 12.5, color: AppColors.inkMuted),
              ),
              const SizedBox(height: 12),
              const Divider(height: 1, color: AppColors.borderHairline),
              // ⚠️ 비로그인에는 내 매물 관리·찜·채팅·로그아웃을 **넣지 않는다**(2026-08-13 사용자
              //   지적 #2의 결함 — 예전 메뉴는 로그인 상태를 안 봐서 비로그인에게도 그대로 보였다).
              ..._browseItems(context),
            ],
          ],
        ),
      ),
    );
  }

  /// 로그인 여부와 무관하게 같은 목록 — 이 앱은 비로그인 열람을 허용한다(FR58).
  /// "내 차 팔기"는 넣지 않는다: 하단 탭에 상시 있고, 비로그인이 누르면 로그인으로 튕겨
  /// 방금 닫은 드로어로 다시 돌아오는 왕복이 된다.
  List<Widget> _browseItems(BuildContext context) => [
        _DrawerItem(
          itemKey: const Key('drawer_search'),
          icon: Icons.directions_car_outlined,
          label: '내 차 사기',
          onTap: () => _pushScreen(context, const SearchScreen()),
        ),
        _DrawerItem(
          itemKey: const Key('drawer_ai'),
          icon: Icons.auto_awesome_outlined,
          label: 'AI로 찾기',
          onTap: () => _pushScreen(context, const AiChatScreen()),
        ),
      ];

  /// 탭 루트(`/wishlist`·`/chat`)로 간다 — 드로어를 먼저 닫는다.
  /// ⚠️ 라우터·Navigator를 **pop 전에** 잡는다: pop 뒤의 context는 해체 중이라 조회가 실패할 수
  /// 있다(같은 규칙이 아래 세 함수 전부에 적용된다).
  void _go(BuildContext context, String location) {
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    router.go(location);
  }

  void _push(BuildContext context, String location) {
    final router = GoRouter.of(context);
    Navigator.of(context).pop();
    router.push(location);
  }

  /// 셸 밖(루트 Navigator)에 쌓는 상세류 화면 — 셸 경계 규칙(app_router.dart 상단).
  void _pushScreen(BuildContext context, Widget screen) {
    final navigator = Navigator.of(context, rootNavigator: true);
    Navigator.of(context).pop();
    navigator.push(MaterialPageRoute(builder: (_) => screen));
  }

  void _openMyListings(BuildContext context) {
    // 돌아올 때 홈 섹션을 다시 조회한다 — 이 push는 rootNavigator라 탭 onActivate를 거치지
    // 않으므로, 여기서 무효화하지 않으면 구매완료·삭제 결과가 홈에 반영되지 않는다.
    // 컨테이너도 pop 전에 잡는다(pop 후 `ref` 사용 금지 — 세션 만료로 셸이 갈릴 수 있다).
    final container = ProviderScope.containerOf(context, listen: false);
    final navigator = Navigator.of(context, rootNavigator: true);
    Navigator.of(context).pop();
    navigator
        .push(MaterialPageRoute(builder: (_) => const MyListingsScreen()))
        .then((_) {
      container.invalidate(recentListingsProvider);
      container.invalidate(popularListingsProvider);
    });
  }

  Future<void> _signOut(BuildContext context, WidgetRef ref) async {
    final messenger = ScaffoldMessenger.of(context);
    Navigator.of(context).pop();
    // signOut()은 실패 시 rethrow한다 — 삼키면 "눌러도 아무 반응 없는 버튼"이 된다.
    try {
      await ref.read(authControllerProvider.notifier).signOut();
    } catch (e) {
      // 원본 예외는 로그에만, 화면엔 고정 한국어(sell_controller.dart:147과 같은 규칙).
      // ignore: avoid_print
      print('[auth] 로그아웃 실패: $e');
      messenger
        ..hideCurrentSnackBar()
        ..showSnackBar(
          const SnackBar(content: Text('로그아웃에 실패했습니다. 잠시 후 다시 시도해주세요.')),
        );
    }
  }
}

/// 드로어 항목 한 줄 — 아이콘 + 라벨. 높이 52로 터치 타깃(48dp)을 넘긴다.
class _DrawerItem extends StatelessWidget {
  const _DrawerItem({
    required this.itemKey,
    required this.icon,
    required this.label,
    required this.onTap,
    this.enabled = true,
    this.danger = false,
  });

  final Key itemKey;
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool enabled;

  /// 로그아웃처럼 되돌리는 동작 — 색으로만 구분한다(배경은 그대로).
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final color = !enabled
        ? AppColors.inkMuted
        : danger
            ? AppColors.danger
            : AppColors.inkPrimary;
    return InkWell(
      key: itemKey,
      onTap: enabled ? onTap : null,
      child: SizedBox(
        height: 52,
        child: Row(
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style:
                    TextStyle(fontSize: 14.5, fontWeight: FontWeight.w600, color: color),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
