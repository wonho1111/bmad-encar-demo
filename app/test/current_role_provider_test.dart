// DW-686 — currentRoleProvider의 role-없음 계약을 고정한다.
//
// **이 검사가 존재하는 이유:** 14.2가 가입 역할선택을 없애며 currentRoleProvider(auth_controller.dart)가
// role 메타데이터 없는 세션에서 null을 반환하게 됐는데, app/test/ 에는 이를 단언하는 검사가
// 한 줄도 없었다(spec-16-1 Intent, DW-686). 이 스토리에서 화면 분기 메커니즘이 main.dart의
// `AuthGate`(imperative)에서 app_router.dart의 `redirect`(선언형)로 바뀌는데, 그 redirect도
// 같은 provider를 본다 — "role 없는 세션은 admin이 아니므로 홈 셸로 간다"는 계약이 조용히
// 깨져도 지금까지는 아무도 못 잡았다.
//
// require_user_test.dart의 `_fakeUser`+`ProviderScope(overrides:...)` 패턴을 그대로 재사용한다
// (기기·세션 없이 role 메타데이터만 바꿔가며 provider 판정을 본다).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';

/// require_user_test.dart와 동일한 최소 가짜 사용자. role만 바뀐다.
User _fakeUser({String? role}) => User(
      id: '00000000-0000-0000-0000-000000000001',
      appMetadata: const {},
      userMetadata: role == null ? const {} : {'role': role},
      aud: 'authenticated',
      createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
    );

/// currentRoleProvider의 값을 화면에 그대로 노출하는 최소 호스트 — 검사는 이 텍스트만 본다.
class _RoleHost extends ConsumerWidget {
  const _RoleHost();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final role = ref.watch(currentRoleProvider);
    return Scaffold(
      body: Text(role?.name ?? 'null', key: const Key('role_result')),
    );
  }
}

Widget _harness({required User? user}) => ProviderScope(
      overrides: [currentUserProvider.overrideWithValue(user)],
      child: const MaterialApp(home: _RoleHost()),
    );

void main() {
  group('currentRoleProvider — role 없음/미상 계약(DW-686)', () {
    testWidgets('role 메타데이터가 없으면 null(admin 아님 → 홈 셸 허용, AC4)', (tester) async {
      await tester.pumpWidget(_harness(user: _fakeUser(role: null)));
      await tester.pump();

      expect(find.text('null'), findsOneWidget,
          reason: 'role 없는 세션이 null이 아니게 되면(예: 예외로 죽거나 다른 값) '
              'app_router.dart의 redirect가 이 세션을 admin 판정과 혼동할 수 있다');
    });

    testWidgets("role='user'(0029 이후 기존 계정 통일값)여도 null — enum이 모르는 문자열은 무시",
        (tester) async {
      await tester.pumpWidget(_harness(user: _fakeUser(role: 'user')));
      await tester.pump();

      expect(find.text('null'), findsOneWidget,
          reason: "UserRole enum에 'user' 멤버가 없다 — fromValue가 조용히 삼켜 null이 되는 것이 "
              '의도된 동작이다(role 값을 추가하지 않는다, spec-16-1 Never).');
    });

    testWidgets("role='admin'이면 UserRole.admin(모바일 차단 AR9의 전제)", (tester) async {
      await tester.pumpWidget(_harness(user: _fakeUser(role: 'admin')));
      await tester.pump();

      expect(find.text('admin'), findsOneWidget);
    });
  });
}
