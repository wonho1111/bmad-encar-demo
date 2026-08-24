// 앱 진입점.
// 1) Supabase 초기화(키 누락이면 안내 화면으로 폴백 — 앱이 통째로 죽지 않게).
// 2) ProviderScope 로 Riverpod 활성화.
// 3) 인증 상태에 따른 화면 분기(미인증→로그인/가입, buyer/seller(또는 역할 미상)→홈,
//    admin→차단 안내 AR9)는 Story 16.1부터 `core/router/app_router.dart`의 GoRouter
//    `redirect`가 선언형으로 담당한다(이전엔 여기 `AuthGate`가 imperative 하게 했다).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

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
      // ⚠️ **인증 오류와 설정 오류를 가른다**(2026-08-13, DW-836 — 실기기에서 실제로 밟았다).
      //   예전엔 이 스트림이 **어떤 이유로 error가 되든** "설정 필요" 화면으로 보냈다. 그런데
      //   실기기에서 실제로 걸린 것은 설정 문제가 아니라 **정상적인 세션 만료**였다:
      //     AuthApiException(message: Invalid Refresh Token: Refresh Token Not Found, code: refresh_token_not_found)
      //   그 화면엔 로그인으로 가는 길이 없어 사용자가 할 수 있는 게 **앱 데이터 삭제뿐**이었고,
      //   영문 예외 원문이 그대로 노출됐다.
      //   세션 만료는 고장이 아니라 정상 수명주기다(며칠 뒤 재실행·앱 재설치·토큰 회수) —
      //   그때 "설정 필요"라고 말하면 사용자는 자기 설정이 잘못된 줄 안다.
      //   그래서 `AuthException` 계열이면 **남은 세션을 지우고 로그인 화면으로** 보낸다.
      //   나머지(환경변수 누락 등 진짜 설정 문제)만 ConfigErrorScreen에 남는다.
      error: (e, _) {
        if (isExpiredSessionError(e)) {
          return const ExpiredSessionRecovery();
        }
        return MaterialApp(
          title: '중고차 직거래',
          theme: buildAppTheme(),
          home: ConfigErrorScreen(message: '인증 상태 확인 중 오류: $e'),
        );
      },
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

/// 만료된(갱신 불가) 세션을 정리하고 로그인 화면으로 보내는 복구 단계 (DW-836).
///
/// 왜 별도 위젯인가: 정리(`signOut`)는 **비동기 부수효과**라 build 중에 부를 수 없다.
/// 그리고 정리가 끝나면 **우리가 직접 라우터를 렌더한다** — 스트림이 복구되기를 기다리지 않는다.
/// 스트림이 끝내 error에 머무는 경우까지 생각하면, 기다리는 설계는 "무한 스피너"라는 더 나쁜
/// 막다른 길이 된다(고치려던 것과 같은 부류의 함정). 라우터의 redirect는 `currentUser`를 동기로
/// 읽고 그 값은 정리 후 null이므로, 렌더하는 순간 `/login`으로 간다.
/// 이 오류가 "설정 문제"가 아니라 **세션 문제**인가 — 위 분기의 정책을 한 줄로 못박은 자리.
/// 여기를 좁히면(예: 특정 code만) 다른 인증 오류가 다시 "설정 필요"로 새므로, 정책 자체를
/// 테스트가 잡을 수 있게 이름 있는 함수로 뺀다.
@visibleForTesting
bool isExpiredSessionError(Object error) => error is AuthException;

@visibleForTesting
class ExpiredSessionRecovery extends StatefulWidget {
  const ExpiredSessionRecovery({super.key});

  @override
  State<ExpiredSessionRecovery> createState() => _ExpiredSessionRecoveryState();
}

class _ExpiredSessionRecoveryState extends State<ExpiredSessionRecovery> {
  bool _cleaned = false;

  @override
  void initState() {
    super.initState();
    _clearStaleSession();
  }

  Future<void> _clearStaleSession() async {
    try {
      // 로컬에 남은 세션을 지운다. 서버 호출이 실패해도(이미 무효한 토큰이라 흔하다) 상관없다 —
      // 목적은 "이 앱이 더 이상 그 세션을 들고 있지 않게" 하는 것이고, 실패해도 아래에서
      // 로그인 화면으로는 반드시 보낸다.
      // 타임아웃을 건다 — 네트워크가 느리거나 막히면 `signOut()`이 오래 매달릴 수 있는데, 그동안
      // 사용자는 스피너만 본다. 그건 우리가 고치려던 "막다른 길"의 다른 얼굴이다. 로컬 세션 정리는
      // 서버 응답과 무관하게 이뤄지므로, 기다리다 마는 편이 갇히는 것보다 낫다.
      await supabase.auth.signOut().timeout(const Duration(seconds: 3));
    } catch (_) {
      // 삼킨다(위 주석) — 여기서 다시 에러 화면으로 가면 원래 막다른 길로 되돌아간다.
    }
    if (mounted) setState(() => _cleaned = true);
  }

  @override
  Widget build(BuildContext context) {
    if (!_cleaned) {
      return MaterialApp(
        title: '중고차 직거래',
        theme: buildAppTheme(),
        home: const Scaffold(body: Center(child: CircularProgressIndicator())),
      );
    }
    // 정리 완료 — 평소 경로(라우터)로 넘긴다. 세션이 없으므로 redirect가 /login으로 보낸다.
    return Consumer(
      builder: (context, ref, _) => MaterialApp.router(
        title: '중고차 직거래',
        theme: buildAppTheme(),
        routerConfig: ref.watch(appRouterProvider),
      ),
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
