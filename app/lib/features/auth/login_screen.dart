// 로그인 화면 (FR2) — 이메일·비밀번호로 로그인. (web login/page.tsx 동작 이식)
// 성공하면 authStateProvider 가 인증으로 흘러 main.dart 가 홈으로 분기한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
      appBar: AppBar(title: const Text('로그인')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
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
                  onPressed: loading
                      ? null
                      : () => Navigator.of(context).pushNamed('/signup'),
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
