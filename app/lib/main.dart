// 앱 진입점.
// 1) Supabase 초기화(키 누락이면 안내 화면으로 폴백 — 앱이 통째로 죽지 않게).
// 2) ProviderScope 로 Riverpod 활성화.
// 3) 인증 상태에 따른 화면 분기(미인증→로그인/가입, buyer/seller(또는 역할 미상)→홈,
//    admin→차단 안내 AR9)는 Story 16.1부터 `core/router/app_router.dart`의 GoRouter
//    `redirect`가 선언형으로 담당한다(이전엔 여기 `AuthGate`가 imperative 하게 했다).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'core/router/app_router.dart';
import 'core/supabase/env.dart';
import 'core/supabase/supabase_client.dart';
import 'core/theme/app_theme.dart';
import 'features/auth/auth_controller.dart';

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

class EncarApp extends ConsumerWidget {
  const EncarApp({super.key, this.initError});

  /// Supabase 초기화 실패/미설정 사유(있으면 안내 화면 표시).
  final String? initError;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // 초기화-에러 폴백은 라우터 진입 전 단계에서 그대로 분기한다(기존 동작 보존) —
    // 이 경우 GoRouter 자체를 만들지 않는다(Supabase 없이는 인증 스트림도 없다).
    if (initError != null) {
      return MaterialApp(
        title: '중고차 직거래',
        theme: buildAppTheme(),
        home: ConfigErrorScreen(message: initError!),
      );
    }

    // 세션 스트림의 첫 이벤트(저장 세션 복원)를 기다리는 동안 로딩 화면 —
    // 옛 AuthGate가 authStateProvider.when(loading/error/data)로 하던 것과 동일한 화면을
    // GoRouter 진입 전 단계에서 재현한다(app_router.dart의 redirect는 currentUser를
    // 동기로만 읽으므로 이 분기 자체를 대신하지 않는다).
    final authState = ref.watch(authStateProvider);
    return authState.when(
      loading: () => MaterialApp(
        title: '중고차 직거래',
        theme: buildAppTheme(),
        home: const Scaffold(body: Center(child: CircularProgressIndicator())),
      ),
      error: (e, _) => MaterialApp(
        title: '중고차 직거래',
        theme: buildAppTheme(),
        home: ConfigErrorScreen(message: '인증 상태 확인 중 오류: $e'),
      ),
      data: (_) {
        final router = ref.watch(appRouterProvider);
        return MaterialApp.router(
          title: '중고차 직거래',
          theme: buildAppTheme(),
          routerConfig: router,
        );
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
