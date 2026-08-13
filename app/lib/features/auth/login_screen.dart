// 로그인 화면 (FR2) — 이메일·비밀번호로 로그인. (web login/page.tsx 동작 이식)
// 성공하면 authStateProvider 가 인증으로 흘러 app_router.dart의 redirect가 홈 셸로 보낸다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import 'auth_controller.dart';
import 'auth_errors.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  String? _error;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final loading = ref.read(authControllerProvider).isLoading;
    if (loading) return; // 진행 중 중복 제출 차단
    setState(() => _error = null);

    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = '이메일과 비밀번호를 입력해주세요.');
      return;
    }

    try {
      await ref.read(authControllerProvider.notifier).signIn(email: email, password: password);
      // 성공 → 화면 전환은 authStateProvider 가 처리. 여기서 push 하지 않는다.
    } catch (e) {
      if (mounted) setState(() => _error = toKoreanLoginError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final loading = ref.watch(authControllerProvider).isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('로그인'),
        // ✎ 2026-08-13 사용자 지적 #3 — **뒤로 갈 길이 아예 없었다.**
        //   찜·채팅 탭을 비로그인으로 누르면 app_router.dart의 redirect가 그 경로를 '/login'으로
        //   **갈아끼운다**(push가 아니라 replace) — 그래서 Navigator 스택에 되돌아갈 항목이 없고,
        //   AppBar도 자동 ← 를 못 그리고 시스템 back도 앱을 닫는다. 이 앱은 로그인 없이도
        //   매물을 둘러볼 수 있으므로(FR58) "로그인 아니면 나가기"는 잘못된 막다른 길이다.
        //   목적지는 홈 고정 — 여기로 오는 길이 찜·채팅·문의·찜하기 여러 갈래라 되감기(pop)로는
        //   사람마다 다른 곳으로 간다(웹 상세의 "매물 목록" 링크와 같은 판단).
        //   `context.go`(pushReplacement 성격)를 쓴다: 이 화면을 스택에 남기면 홈에서 시스템
        //   back을 눌렀을 때 로그인 화면으로 되돌아온다.
        leading: IconButton(
          key: const Key('login_close'),
          icon: const Icon(Icons.close),
          tooltip: '닫기',
          onPressed: () => context.go('/home'),
        ),
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            // 하단 패딩에 시스템 내비바 높이를 더해(edge-to-edge) 마지막 버튼이 가리지 않게.
            padding: EdgeInsets.fromLTRB(
                24, 24, 24, 24 + MediaQuery.of(context).viewPadding.bottom),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 왜 이 화면이 떴는지 한 줄 — 이 화면에 오는 대부분의 경로가 "찜/채팅 탭을
                // 눌렀다"라서, 아무 설명 없이 입력칸만 있으면 앱이 막힌 것처럼 보인다(위
                // leading 주석의 같은 문제의 다른 얼굴). 둘러보기는 계속 가능하다는 사실도
                // 함께 알린다 — 그게 위 닫기 버튼의 목적지이기도 하다.
                const Text(
                  '찜·채팅·내 차 팔기는 로그인이 필요해요.\n매물 둘러보기는 로그인 없이도 계속할 수 있어요.',
                  key: Key('login_reason'),
                  style: TextStyle(color: AppColors.inkMuted, fontSize: 13, height: 1.5),
                ),
                const SizedBox(height: 20),
                TextField(
                  key: const Key('login_email'),
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  decoration: const InputDecoration(labelText: '이메일'),
                ),
                const SizedBox(height: 16),
                TextField(
                  key: const Key('login_password'),
                  controller: _passwordCtrl,
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  decoration: const InputDecoration(labelText: '비밀번호'),
                  onSubmitted: (_) => _submit(),
                ),
                const SizedBox(height: 16),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      _error!,
                      key: const Key('login_error'),
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                FilledButton(
                  key: const Key('login_submit'),
                  onPressed: loading ? null : _submit,
                  child: Text(loading ? '처리 중…' : '로그인'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  key: const Key('go_signup'),
                  // `MaterialApp.router`(GoRouter) 아래서는 Navigator.pushNamed가 참조할
                  // 라우트 테이블이 없다 — go_router 자체의 push를 써야 한다
                  // (`/signup`은 app_router.dart의 최상위 GoRoute).
                  onPressed: loading ? null : () => context.push('/signup'),
                  child: const Text('아직 계정이 없으신가요? 회원가입'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
