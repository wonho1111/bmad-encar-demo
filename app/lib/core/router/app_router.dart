// GoRouter 설정(Story 16.1) — 선언형 라우팅 + 하단 4탭 셸.
//
// 이전에는 main.dart의 `AuthGate`가 Navigator 1.0 위에서 인증 상태를 보고 화면을
// imperative 하게 골랐다(미인증→로그인, admin→차단, 그 외→홈). 이 파일은 **같은 판정**을
// `GoRouter.redirect`로 선언형으로 옮긴다 — 동작은 그대로, 메커니즘만 바뀐다.
//
// ⚠️ **GoRouter 리액티비티 함정**: `redirect`는 라우터 생성 시 한 번만 평가되지 않는다.
//   `refreshListenable`이 알려줄 때만 재평가된다. `authStateProvider`(Riverpod StreamProvider)의
//   변화가 로그인/로그아웃 시 실제로 재평가를 트리거하게 하려면, `notifyListeners()`를 호출하는
//   `Listenable` 브리지가 필요하다 — 아래 `_GoRouterRefreshNotifier` + `ref.listen`.
//   이걸 빠뜨리면 로그인해도 로그인 화면에 멈춰 있는 흔한 실패 모드가 생긴다.
//
// ⚠️ **셸 경계(spec-16-1의 1급 설계 결정)**: 셸(`_AppShell`) 안에 사는 것은 탭 루트 4개뿐
//   (`/home`·`/wishlist`·`/chat`·`/sell`)이다. 상세류 화면(AI 채팅·매물 탐색·매물 상세·
//   채팅방·내 매물 관리·매물 수정)은 각 화면이 `Navigator.of(context, rootNavigator: true)`로
//   셸 밖 루트 Navigator에 쌓는다(home_screen.dart·chat_list_screen.dart·
//   listing_detail_screen.dart 등) — 이 파일은 그 대상 화면들의 GoRoute를 따로 등록하지
//   않는다. 브랜치 안에 쌓이면 셸의 AppBar·NavigationBar가 상세 화면 위에 그대로 남는
//   레이아웃 결함이 생긴다(실측 확인, Spec Change Log 2026-08-07 #2).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../features/auth/admin_blocked_screen.dart';
import '../../features/auth/auth_controller.dart';
import '../../features/auth/home_screen.dart';
import '../../features/auth/login_screen.dart';
import '../../features/auth/signup_screen.dart';
import '../../features/auth/user_role.dart';
import '../../features/chat/chat_list_screen.dart';
import '../../features/chat/chat_providers.dart';
import '../../features/listings/listings_providers.dart';
import '../../features/listings/sell_controller.dart';
import '../../features/listings/sell_screen.dart';
import '../../features/wishlist/wishlist_providers.dart';
import '../../features/wishlist/wishlist_screen.dart';
import '../theme/app_theme.dart';

/// GoRouter가 요구하는 최소 `Listenable` — 외부에서 `notify()`를 부르면 그대로
/// `notifyListeners()`로 흘려보낸다. 실제로 언제 부를지는 아래 provider의 `ref.listen`이 정한다.
class _GoRouterRefreshNotifier extends ChangeNotifier {
  void notify() => notifyListeners();
}

/// 하단 4탭 브랜치 서술자 — 인덱스별 경로·화면 빌더·AppBar 제목·NavigationDestination
/// 아이콘/라벨·탭 (재)활성화 시 실행할 부수효과를 한 자리에 묶는다.
///
/// **왜 한 곳으로 모으나:** 예전엔 이 정보가 세 곳에 흩어져 있었다 — 탭별 AppBar 제목 리스트,
/// `NavigationBar.destinations`의 하드코딩 리스트(아이콘·라벨·Key), `onDestinationSelected`의
/// `if (index == 2)` 매직넘버(채팅 탭만 무효화). 탭을 재정렬하거나 추가/삭제하면 이 셋이 같이
/// 안 바뀔 위험이 있었다 — 특히 매직넘버는 "인덱스 2가 채팅"이라는 사실이 코드 어디에도 안
/// 적혀 있어, 탭 순서를 바꾸면 엉뚱한 provider가 조용히 무효화된다(review, spec-16-1 P1).
/// 지금은 `_kTabBranches`(아래) 하나가 branches 목록·AppBar 제목·NavigationBar 항목·탭
/// 활성화 부수효과를 전부 만들어내므로, 인덱스가 어긋날 자리가 없다.
class _TabBranch {
  const _TabBranch({
    required this.key,
    required this.path,
    required this.title,
    required this.label,
    required this.icon,
    required this.selectedIcon,
    required this.builder,
    this.onActivate,
  });

  final Key key;
  final String path;

  /// 셸 AppBar 제목(전체 문구). NavigationDestination의 `label`(짧은 탭 표기)과는 자리가
  /// 달라 어휘가 갈릴 수 있다 — 예: 홈 탭은 title '중고차 직거래'/label '홈', 내차팔기 탭은
  /// title '매물 등록'/label '내차팔기'. 같은 탭을 가리키기만 하면 되고, 글자가 똑같아야
  /// 한다는 규칙은 없다(예전 주석의 "같은 어휘로 맞춘다"는 실제와 다른 주장이었다 — review,
  /// spec-16-1 P9).
  final String title;
  final String label;
  final IconData icon;
  final IconData selectedIcon;
  final Widget Function(BuildContext, GoRouterState) builder;

  /// 이 탭이 `NavigationBar`에서 (재)선택될 때 호출 — `/chat`·`/home`·`/sell`처럼 브랜치가
  /// `StatefulShellRoute`의 IndexedStack으로 영구 마운트돼 autoDispose가 무력화된 provider를,
  /// 자연스러운 dispose 대신 "탭을 누를 때마다 무효화"로 명시 갱신한다.
  ///   · chatRoomsProvider: 채팅 탭을 다시 눌러도 새 문의·읽지 않음 카운터가 안 갱신되던 버그
  ///     (review_loop_iteration 1, bug #3).
  ///   · recentListingsProvider: 내차팔기 탭에서 매물을 등록하고 홈 탭으로 돌아와도 최근
  ///     매물이 등록 전 목록에 고정되던 버그(review, spec-16-1 P1) — home_screen.dart의
  ///     `.then((_) => ref.invalidate(...))`는 퀵액션(rootNavigator push) 경로만 잡고
  ///     하단 탭 전환 경로는 못 잡았다.
  ///   · sellControllerProvider: 등록 탭 루트와 수정 화면(push)이 같은 provider를 공유해
  ///     한쪽의 success/error/editingId가 다른 쪽에 새던 문제(review, spec-16-1 P3) — 탭을
  ///     누를 때마다 무효화해 이전 화면이 남긴 잔여 상태를 지운다. 입력 중이던 텍스트는
  ///     화면의 TextEditingController가 따로 쥐고 있어 이걸로 지워지지 않는다.
  ///   · wishedListingIdsProvider: non-autoDispose라 한 번 조회가 실패하면(빈 Set으로 조용히
  ///     삼킴, wishlist_repository.dart) 앱이 켜져 있는 동안 하트가 계속 빈 채로 남는다 —
  ///     유일한 다른 무효화 지점은 찜 토글 성공(wish_button.dart)뿐이라 사용자가 하트를 한 번도
  ///     안 누르면 영영 복구되지 않는다(코드리뷰 지적). 홈 탭은 카드를 보여주는 화면 중 유일한
  ///     실제 탭이고(검색·AI는 홈에서 push되는 화면이라 별도 탭이 아니다), 이 provider는 화면
  ///     전역이 공유하는 단일 인스턴스라 홈 탭 재진입만으로도 검색·AI 진입점까지 함께 복구된다.
  final void Function(WidgetRef ref)? onActivate;
}

final _kTabBranches = <_TabBranch>[
  _TabBranch(
    key: const Key('tab_home'),
    path: '/home',
    title: '중고차 직거래',
    label: '홈',
    icon: Icons.home_outlined,
    selectedIcon: Icons.home,
    builder: (context, state) => const HomeScreen(),
    onActivate: (ref) {
      ref.invalidate(recentListingsProvider);
      ref.invalidate(wishedListingIdsProvider);
    },
  ),
  _TabBranch(
    key: const Key('tab_wishlist'),
    path: '/wishlist',
    title: '찜한 매물',
    label: '찜',
    icon: Icons.favorite_border,
    selectedIcon: Icons.favorite,
    builder: (context, state) => const WishlistScreen(),
    // wishlistProvider는 autoDispose지만 이 브랜치도 IndexedStack으로 영구 마운트되므로
    // (recentListingsProvider·chatRoomsProvider와 같은 함정, 위 _TabBranch.onActivate 문서
    // 참조) 탭을 다시 누를 때 명시 무효화해야 "방금 취소한 찜"이 즉시 사라진다.
    onActivate: (ref) => ref.invalidate(wishlistProvider),
  ),
  _TabBranch(
    key: const Key('tab_chat'),
    path: '/chat',
    title: '채팅',
    label: '채팅',
    icon: Icons.chat_bubble_outline,
    selectedIcon: Icons.chat_bubble,
    // showAppBar: false — 셸(_AppShell)이 이미 공통 AppBar(제목+아바타)를 그린다.
    // 홈 퀵액션의 Navigator.push(ChatListScreen())는 기본값(true)이라 영향 없다.
    builder: (context, state) => const ChatListScreen(showAppBar: false),
    onActivate: (ref) => ref.invalidate(chatRoomsProvider),
  ),
  _TabBranch(
    key: const Key('tab_sell'),
    path: '/sell',
    title: '매물 등록',
    label: '내차팔기',
    icon: Icons.sell_outlined,
    selectedIcon: Icons.sell,
    // showAppBar: false — 위와 동일한 이유. 홈의 "매물 등록"·수정 진입은 기본값(true)이라
    // 영향 없다.
    builder: (context, state) => const SellScreen(showAppBar: false),
    // 제출이 진행 중이면 무효화하지 않는다 — 무효화하면 새 컨트롤러의 loading 이 false 라
    // 버튼이 다시 눌려 같은 매물이 두 번 INSERT 될 수 있다(실측: 진행 중 탭 재선택 →
    // loading=false). 진행 중 상태는 그 제출이 끝나면서 스스로 결과로 바뀐다.
    onActivate: (ref) {
      if (!ref.read(sellControllerProvider).loading) {
        ref.invalidate(sellControllerProvider);
      }
    },
  ),
];

/// 앱 라우터. redirect 안에서는 `ref.read`만 쓴다(watch가 아님) — 그 provider들을 watch하면
/// 이 provider 자신이 매 인증 변화마다 재생성돼 라우터 인스턴스(와 탭 상태)가 통째로
/// 날아간다. 재평가는 아래 `ref.listen` + `_GoRouterRefreshNotifier`가 대신 트리거한다
/// (Riverpod 3엔 `StreamProvider.stream` 같은 raw Stream 접근자가 없어 `ref.listen`으로
/// 옮긴다).
///
/// `authStateProvider`(전역 `supabase` 싱글턴을 감싼 Riverpod provider, auth_controller.dart)를
/// 직접 구독하므로, 전역 `supabase`를 이 파일이 직접 만지지 않는다 — 테스트가
/// `authStateProvider`를 오버라이드하면 실제 Supabase 초기화 없이 라우터를 통째로
/// 구동할 수 있다(app_router_test.dart).
final appRouterProvider = Provider<GoRouter>((ref) {
  final refresh = _GoRouterRefreshNotifier();
  ref.listen(authStateProvider, (previous, next) => refresh.notify());

  // 상세류 push(AI 채팅·탐색·매물 상세·채팅방 등)를 셸 밖으로 보낼 때 쓰는 루트 Navigator
  // key. 지금은 각 화면이 `Navigator.of(context, rootNavigator: true)`로 이 Navigator를
  // 찾아 쓰므로 명시적으로 참조하는 코드는 없지만, `GoRouter`에 박아둬 "이 앱의 루트
  // Navigator가 어디인지"를 코드 상에서 고정한다(spec-16-1 Code Map).
  // provider 몸체 안(라이브러리 top-level이 아니라)에 두는 이유: top-level GlobalKey는
  // 프로세스 전역 싱글턴이라, ProviderScope 두 개가 동시에 떠서 각자 GoRouter를 만들면
  // (예: 위젯 테스트가 라우터 하네스 두 개를 함께 마운트) 같은 GlobalKey를 여러 Navigator가
  // 나눠 쓰게 돼 "Multiple widgets used the same GlobalKey"로 죽는다(실측 확인, review,
  // spec-16-1 P7). provider 안에 두면 라우터 인스턴스마다 새 key가 생겨 수명이 그 라우터와
  // 같아진다.
  final rootNavigatorKey = GlobalKey<NavigatorState>();

  final router = GoRouter(
    navigatorKey: rootNavigatorKey,
    initialLocation: '/home',
    refreshListenable: refresh,
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final isAuthRoute = loc == '/login' || loc == '/signup';

      final user = ref.read(currentUserProvider);
      if (user == null) {
        // 미인증 → 로그인/가입 화면이 아니면 로그인으로. (기존 AuthGate와 동일 동작.)
        return isAuthRoute ? null : '/login';
      }

      final role = ref.read(currentRoleProvider);
      if (role == UserRole.admin) {
        // 관리자는 모바일 제외(AR9) → 차단 안내.
        return loc == '/admin-blocked' ? null : '/admin-blocked';
      }

      // buyer/seller(또는 역할 미상, DW-686) → 공통 홈 셸. 인증/가입/차단 화면에
      // 남아 있으면 홈으로 되돌린다.
      if (isAuthRoute || loc == '/admin-blocked') {
        return '/home';
      }
      return null;
    },
    // 매칭되는 라우트가 없을 때(오타 딥링크 등) Flutter 기본 무장식 에러 화면 대신 이 앱
    // 톤의 최소 안내를 보여준다(ConfigErrorScreen과 같은 결의 에러 화면 패턴).
    errorBuilder: (context, state) => Scaffold(
      appBar: AppBar(title: const Text('오류')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.error_outline,
                size: 48,
                color: AppColors.inkMuted,
              ),
              const SizedBox(height: 16),
              const Text(
                '페이지를 찾을 수 없습니다.',
                key: Key('route_not_found'),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              FilledButton(
                onPressed: () => context.go('/home'),
                child: const Text('홈으로'),
              ),
            ],
          ),
        ),
      ),
    ),
    routes: [
      GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
      GoRoute(
        path: '/signup',
        builder: (context, state) => const SignupScreen(),
      ),
      GoRoute(
        path: '/admin-blocked',
        builder: (context, state) => const AdminBlockedScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            _AppShell(navigationShell: navigationShell),
        branches: [
          for (final b in _kTabBranches)
            StatefulShellBranch(
              routes: [GoRoute(path: b.path, builder: b.builder)],
            ),
        ],
      ),
    ],
  );

  // 정리 순서: router.dispose를 먼저, refresh.dispose를 그다음(GoRouter가 refreshListenable을
  // 참조하고 있을 수 있으므로 그걸 먼저 버리면 안 된다). Riverpod의 onDispose 콜백은 등록
  // 순서대로(FIFO) 실행된다(riverpod 3.3.2 core/ref.dart:788, `for (final cb in
  // callbacks)`) — LIFO가 아니다(예전 주석은 "나중에 등록한 게 먼저 돈다"고 반대로 적혀
  // 있었다, review, spec-16-1 P8). 등록 순서에 기대는 대신, 한 콜백 안에서 원하는 순서를
  // 직접 보장한다.
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });

  return router;
});

/// 하단 4탭 셸 스캐폴드 — 공통 AppBar(탭별 제목 + 우상단 프로필 아바타) + `NavigationBar`
/// (FAB 없음). `StatefulShellRoute`가 각 브랜치의 `Navigator`를 보존하므로 탭을 전환해도
/// 스크롤·네비 스택이 유지된다(`navigationShell`이 이미 만들어둔 보장 — 이 위젯은 그 위에 얹을 뿐).
class _AppShell extends ConsumerWidget {
  const _AppShell({required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  /// 탭 전환의 **유일한** 통로 — 그 탭이 선언한 부수효과(주로 영구 마운트로 무력화된
  /// autoDispose provider 무효화)를 실행한 뒤 브랜치를 옮긴다. 어느 인덱스가 어느 provider를
  /// 무효화하는지는 `_kTabBranches` 하나가 정한다(`_TabBranch.onActivate` 참조).
  ///
  /// 탭을 옮기는 경로는 하단 NavigationBar 와 시스템 back(PopScope) 둘이다. 둘 다 여기를
  /// 거치게 해서 "한쪽만 부수효과를 실행하는" 새는 자리를 없앤다.
  void _activate(WidgetRef ref, int index, {bool initialLocation = false}) {
    _kTabBranches[index].onActivate?.call(ref);
    navigationShell.goBranch(index, initialLocation: initialLocation);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return PopScope(
      // 홈 탭(인덱스 0)에서만 실제 pop(=앱 종료)을 허용한다. 그 외 탭에서 시스템 back을
      // 누르면 앱이 죽지 않고 홈 탭으로 복귀해야 한다("뒤로가기 = OS back(R5)" —
      // `_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md`
      // 'Responsive & Platform' 절 '네이티브 앱 구조 델타', nav-ia-rules §3 R5). 상세류
      // 화면은 이미 rootNavigator로 셸 밖에 쌓이므로 거기서의 back은 이 PopScope와 무관하게
      // 그 화면 자신의 Navigator가 처리한다.
      canPop: navigationShell.currentIndex == 0,
      onPopInvokedWithResult: (didPop, result) {
        if (didPop) return;
        // 홈 탭으로 돌아가는 것도 `_activate`를 거친다 — 예전엔 여기서 goBranch(0)만 불러
        // 홈 탭의 onActivate(최근 매물 재조회)를 건너뛰었다. 그래서 내차팔기 탭에서 매물을
        // 등록하고 **시스템 back**으로 홈에 오면 최근 매물이 갱신되지 않았다(실측: 조회 1회
        // 고정 — 탭 버튼으로 오면 2회). 탭 전환 경로가 둘인데 부수효과가 한쪽에만 걸려 있으면
        // 반드시 이렇게 새므로, 두 경로를 같은 함수로 모은다.
        _activate(ref, 0);
      },
      child: Scaffold(
        backgroundColor: AppColors.surfaceBase,
        appBar: AppBar(
          title: Text(_kTabBranches[navigationShell.currentIndex].title),
          actions: const [_ProfileAvatarButton(), SizedBox(width: 8)],
        ),
        body: navigationShell,
        bottomNavigationBar: NavigationBar(
          selectedIndex: navigationShell.currentIndex,
          onDestinationSelected: (index) => _activate(
            ref,
            index,
            // 이미 선택된 탭을 다시 누르면 그 브랜치의 첫 화면으로(initialLocation) — 표준 관례.
            initialLocation: index == navigationShell.currentIndex,
          ),
          destinations: [
            for (final b in _kTabBranches)
              NavigationDestination(
                key: b.key,
                icon: Icon(b.icon),
                selectedIcon: Icon(b.selectedIcon),
                label: b.label,
              ),
          ],
        ),
      ),
    );
  }
}

/// 우상단 프로필 아바타 — 이메일 확인 + 로그아웃(구 홈 AppBar의 "로그아웃" 텍스트버튼 +
/// `_ProfileCard`를 대체). 로그아웃 후 화면 전환은 위 redirect가 authStateProvider 변화를
/// 받아 자동으로 처리한다(여기서 직접 push하지 않는다).
class _ProfileAvatarButton extends ConsumerWidget {
  const _ProfileAvatarButton();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final loading = ref.watch(authControllerProvider).isLoading;

    return PopupMenuButton<String>(
      key: const Key('profile_avatar'),
      tooltip: '프로필',
      icon: const CircleAvatar(
        radius: 16,
        backgroundColor: AppColors.brandPetrol,
        child: Icon(Icons.person, color: AppColors.onPetrol, size: 18),
      ),
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          child: Text(user?.email ?? '-', key: const Key('profile_email')),
        ),
        const PopupMenuDivider(),
        PopupMenuItem<String>(
          value: 'logout',
          key: const Key('logout'),
          // 로그아웃 진행 중엔 흐리게 비활성화 — 옛 TextButton(onPressed: loading ? null : ...)의
          // 시각 피드백과 동일하게(다시 눌러도 반응 없어 보이는 것 방지).
          enabled: !loading,
          child: const Text('로그아웃'),
        ),
      ],
      onSelected: (value) async {
        if (value != 'logout' || loading) return;
        // AuthController.signOut()은 실패 시 rethrow한다 — await 없이 fire-and-forget으로
        // 부르면 실패가 "눌러도 아무 반응 없는 버튼"으로만 보인다(spec-16-1 Task). 실패를
        // 사용자에게 SnackBar로 보여준다.
        try {
          await ref.read(authControllerProvider.notifier).signOut();
        } catch (e) {
          // 원본 예외는 로그에만 남긴다 — 화면엔 고정 한국어 문구만(sell_controller.dart:147과
          // 같은 규칙: 원본 에러·코드를 화면에 노출하지 않는다. review, spec-16-1 P6).
          // ignore: avoid_print
          print('[auth] 로그아웃 실패: $e');
          if (context.mounted) {
            ScaffoldMessenger.of(context)
              ..hideCurrentSnackBar()
              ..showSnackBar(
                const SnackBar(content: Text('로그아웃에 실패했습니다. 잠시 후 다시 시도해주세요.')),
              );
          }
        }
      },
    );
  }
}
