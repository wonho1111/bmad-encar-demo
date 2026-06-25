// 앱 진입점.
// 1) Supabase 초기화(키 누락이면 안내 화면으로 폴백 — 앱이 통째로 죽지 않게).
// 2) ProviderScope 로 Riverpod 활성화.
// 3) 인증 상태에 따라 화면 분기: 미인증→로그인/가입, buyer/seller→홈, admin→차단 안내(AR9).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/supabase/env.dart';
import 'core/supabase/supabase_client.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/admin_blocked_screen.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/home_screen.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/signup_screen.dart';
import 'features/auth/user_role.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // 키가 주입돼 있을 때만 Supabase 초기화. 누락 시 초기화를 건너뛰고
  // 안내 화면을 띄운다(빌드/렌더 자체는 되게 해서 원인을 화면으로 보여줌).
  String? initError;
  if (SupabaseEnv.isConfigured) {
    try {
      await initSupabase();
    } catch (e) {
      initError = e.toString();
    }
  } else {
    initError =
        'Supabase 환경변수(SUPABASE_URL·SUPABASE_ANON_KEY)가 주입되지 않았습니다. '
        '빌드 시 --dart-define 또는 --dart-define-from-file 로 값을 넣어주세요 (app/.env.example 참고).';
  }

  runApp(ProviderScope(child: EncarApp(initError: initError)));
}

class EncarApp extends StatelessWidget {
  const EncarApp({super.key, this.initError});

  /// Supabase 초기화 실패/미설정 사유(있으면 안내 화면 표시).
  final String? initError;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: '중고차 직거래',
      theme: buildAppTheme(),
      // 가입 화면은 라우트로 진입(로그인↔가입 이동). 홈/분기는 home 으로 처리.
      routes: {
        '/signup': (_) => const SignupScreen(),
      },
      home: initError != null
          ? ConfigErrorScreen(message: initError!)
          : const AuthGate(),
    );
  }
}

/// 인증 상태에 따라 보여줄 최상위 화면을 고르는 게이트.
class AuthGate extends ConsumerWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authStateProvider);

    // 세션 스트림의 첫 이벤트(저장 세션 복원)를 기다리는 동안 로딩.
    return authState.when(
      loading: () => const Scaffold(body: Center(child: CircularProgressIndicator())),
      error: (e, _) => ConfigErrorScreen(message: '인증 상태 확인 중 오류: $e'),
      data: (_) {
        final user = ref.watch(currentUserProvider);
        if (user == null) return const LoginScreen();

        final role = ref.watch(currentRoleProvider);
        // 관리자는 모바일 제외(AR9) → 차단 안내.
        if (role == UserRole.admin) return const AdminBlockedScreen();
        // buyer/seller(또는 역할 미상) → 공통 홈.
        return const HomeScreen();
      },
    );
  }
}

/// 환경변수 누락·초기화 실패를 사용자에게 한국어로 안내하는 화면.
class ConfigErrorScreen extends StatelessWidget {
  const ConfigErrorScreen({super.key, required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('설정 필요')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.warning_amber_rounded, size: 48, color: Colors.orange),
                const SizedBox(height: 16),
                Text(
                  message,
                  key: const Key('config_error'),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
