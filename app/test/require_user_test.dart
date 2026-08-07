// RequireUser 게이트 검사 — 역할 통합(FR52·FR53)의 앱 쪽 계약을 고정한다.
//
// **이 검사가 존재하는 이유:** 앱의 판매 화면 3곳은 원래 `role != UserRole.seller`로 막고
// 있었고, 그 가드에는 검사가 **하나도 없었다**(앱 테스트는 UserRole enum의 값 변환만 봤다).
// 웹에서는 같은 성격의 변경(14.3)을 E2E가 잡아주지만, 앱은 이 환경에 기기·에뮬레이터가 없어
// 실행 확인을 못 한다. 그래서 **기기 없이 돌아가는 위젯 테스트**로 대신 고정한다.
//
// 이 검사가 **안 보는 것**(추측이 아니라 실제 한계):
//   · 실기기에서의 시각적 확인 — Epic 16-6(앱 통합 시연 검증)이 본다.
//   · 게이트를 통과한 뒤의 화면 본문(매물 목록·폼) — Supabase 세션이 필요해 여기선 안 그린다.
//     여기서 보는 것은 "게이트가 통과시키는가/막는가" 하나다.
//   · 세 화면이 이 위젯을 **실제로 쓰고 있는지** — 그건 아래 두 번째 group이 본다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/require_user.dart';
import 'package:app/features/listings/edit_listing_screen.dart';
import 'package:app/features/listings/my_listings_screen.dart';
import 'package:app/features/listings/sell_screen.dart';

/// 최소한의 가짜 사용자. RequireUser는 null 여부만 보므로 필드 값은 의미 없다.
User _fakeUser({String? role}) => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: role == null ? const {} : {'role': role},
  aud: 'authenticated',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

/// 호출부와 **같은 관례**로 게이트를 쓴다 — 테스트만 다른 방식으로 부르면
/// 화면에서 깨지는 모양을 못 본다.
class _GateHost extends ConsumerWidget {
  const _GateHost();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final blocked = requireUser(ref, '테스트');
    if (blocked != null) return blocked;
    return const Scaffold(body: Text('통과', key: Key('passed_through')));
  }
}

Widget _harness({required User? user}) => ProviderScope(
  overrides: [currentUserProvider.overrideWithValue(user)],
  child: const MaterialApp(home: _GateHost()),
);

void main() {
  group('RequireUser — 로그인만 본다(역할은 안 본다)', () {
    testWidgets('미로그인이면 막고 안내를 보여준다', (tester) async {
      await tester.pumpWidget(_harness(user: null));
      await tester.pump();

      expect(find.byKey(const Key('require_user_blocked')), findsOneWidget);
      expect(find.byKey(const Key('passed_through')), findsNothing);
    });

    // ⭐ 이 프로젝트가 지켜야 하는 핵심 계약이다 — 사용자가 명시한 에픽 14 최종 인수 조건
    //   ("기존 구매자·기존 판매자·신규 가입 계정이 전부 판매 화면에 도달")의 앱 쪽 표현.
    //   role 값을 바꿔가며 **전부 통과**해야 한다.
    for (final role in <String?>[null, 'user', 'buyer', 'seller']) {
      testWidgets("로그인했으면 role=${role ?? '(없음)'}이어도 통과시킨다", (tester) async {
        await tester.pumpWidget(_harness(user: _fakeUser(role: role)));
        await tester.pump();

        expect(
          find.byKey(const Key('passed_through')),
          findsOneWidget,
          reason: 'role=$role 계정이 막히면 역할 통합(FR52·FR53)이 깨진 것이다',
        );
        expect(find.byKey(const Key('require_user_blocked')), findsNothing);
      });
    }
  });

  group('RequireUser — showAppBar 파라미터(review, spec-16-1 P5)', () {
    // 하단 4탭 셸의 '내차팔기' 탭 루트(SellScreen(showAppBar: false))에서 세션이 끊기면,
    // requireUser가 showAppBar를 그대로 물려받아야 한다 — 안 물려주면(뮤테이션:
    // `requireUser(ref, title, showAppBar: widget.showAppBar)` → `requireUser(ref, title)`)
    // 기본값(true)이 적용돼 이 안내 화면이 자기 AppBar를 또 그린다. 셸이 이미 AppBar를
    // 그리고 있으므로 그 위에 하나가 더 겹친다.
    testWidgets('showAppBar:false — 미로그인이어도 자기 AppBar를 그리지 않는다(셸이 이미 그리므로)', (
      tester,
    ) async {
      await tester.pumpWidget(
        ProviderScope(
          overrides: [currentUserProvider.overrideWithValue(null)],
          child: MaterialApp(
            home: Consumer(
              builder: (context, ref, _) {
                return requireUser(ref, '테스트', showAppBar: false) ??
                    const SizedBox();
              },
            ),
          ),
        ),
      );
      await tester.pump();

      expect(
        find.byType(AppBar),
        findsNothing,
        reason:
            'showAppBar:false를 무시하면(뮤테이션) 기본값 true가 적용돼 여기서 '
            'AppBar가 하나 잡힌다',
      );
      expect(find.byKey(const Key('require_user_blocked')), findsOneWidget);
    });

    testWidgets('내차팔기 탭처럼 셸 AppBar 안에 SellScreen(showAppBar:false)을 올렸을 때 — '
        '미로그인이면 셸 AppBar 하나만 남는다', (tester) async {
      // app_router.dart의 _AppShell을 통째로 구동하지 않고, 그 배치(셸 AppBar + 탭
      // 화면을 body로)만 얇게 흉내낸다 — SellScreen(showAppBar: false)가 자기 AppBar를
      // 안 그린다는 계약이 지켜지는지가 검사 대상이다.
      await tester.pumpWidget(
        ProviderScope(
          overrides: [currentUserProvider.overrideWithValue(null)],
          child: MaterialApp(
            home: Scaffold(
              appBar: AppBar(title: const Text('매물 등록')), // 셸의 공통 AppBar를 흉내낸다.
              body: const SellScreen(showAppBar: false),
            ),
          ),
        ),
      );
      await tester.pump();

      expect(
        find.byType(AppBar),
        findsOneWidget,
        reason:
            'requireUser(showAppBar: widget.showAppBar) 배선이 뮤테이션으로 빠지면 '
            '(requireUser(ref, title)로 되돌아가면) 미로그인 안내가 자기 AppBar를 또 '
            '그려 셸 AppBar와 함께 2개가 된다',
      );
      expect(find.byKey(const Key('require_user_blocked')), findsOneWidget);
    });
  });

  // 위 group은 게이트 **자체**만 본다. 게이트가 아무리 옳아도 화면이 안 쓰면 소용없다 —
  // 원래 결함이 정확히 그 모양이었다(세 화면이 각자 인라인 가드를 들고 있었다).
  // 미로그인 상태로 각 화면을 그리면 게이트가 즉시 막으므로, 본문이 Supabase를 건드리기 전에
  // 판정이 끝난다. 그래서 기기·세션 없이도 "이 화면이 그 게이트를 통과 지점으로 쓰는가"를 볼 수 있다.
  group('판매 관련 화면 3곳이 실제로 RequireUser를 쓴다', () {
    final screens = <String, Widget>{
      'SellScreen(매물 등록)': const SellScreen(),
      'MyListingsScreen(내 매물 관리)': const MyListingsScreen(),
      'EditListingScreen(매물 수정)': const EditListingScreen(listingId: 'x'),
    };

    screens.forEach((name, screen) {
      testWidgets('$name — 미로그인이면 공용 게이트 안내가 뜬다', (tester) async {
        await tester.pumpWidget(
          ProviderScope(
            overrides: [currentUserProvider.overrideWithValue(null)],
            child: MaterialApp(home: screen),
          ),
        );
        await tester.pump();

        expect(
          find.byKey(const Key('require_user_blocked')),
          findsOneWidget,
          reason: '$name이 공용 RequireUser 대신 자체 가드를 쓰고 있으면 이 검사가 잡는다',
        );
      });
    });
  });
}
