// 회원가입 화면 (FR1) — 이메일·비밀번호 + 역할(구매자/판매자) 선택. (web signup/page.tsx 동작 이식)
// 역할은 data:{'role':...} 로 메타데이터에 실려, web과 동일한 DB 트리거가 profiles 를 만든다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_controller.dart';
import 'auth_errors.dart';
import 'user_role.dart';

class SignupScreen extends ConsumerStatefulWidget {
  const SignupScreen({super.key});

  @override
  ConsumerState<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends ConsumerState<SignupScreen> {
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  UserRole _role = UserRole.buyer;
  String? _error;
  String? _success;

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final loading = ref.read(authControllerProvider).isLoading;
    if (loading) return;
    setState(() {
      _error = null;
      _success = null;
    });

    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;
    if (email.isEmpty || password.isEmpty) {
      setState(() => _error = '이메일과 비밀번호를 입력해주세요.');
      return;
    }
    if (password.length < 6) {
      setState(() => _error = '비밀번호는 6자 이상이어야 합니다.');
      return;
    }

    try {
      final notice = await ref
          .read(authControllerProvider.notifier)
          .signUp(email: email, password: password, role: _role);
      // notice == null → 즉시 로그인됨(화면 전환은 authStateProvider 가 처리).
      // notice != null → 이메일 확인 필요. 안내 + 로그인 링크 표시.
      if (notice != null && mounted) setState(() => _success = notice);
    } catch (e) {
      if (mounted) setState(() => _error = toKoreanSignupError(e));
    }
  }

  @override
  Widget build(BuildContext context) {
    final loading = ref.watch(authControllerProvider).isLoading;

    return Scaffold(
      appBar: AppBar(title: const Text('회원가입')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextField(
                  key: const Key('signup_email'),
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  autofillHints: const [AutofillHints.email],
                  decoration: const InputDecoration(labelText: '이메일'),
                ),
                const SizedBox(height: 16),
                TextField(
                  key: const Key('signup_password'),
                  controller: _passwordCtrl,
                  obscureText: true,
                  autofillHints: const [AutofillHints.newPassword],
                  decoration: const InputDecoration(labelText: '비밀번호 (6자 이상)'),
                ),
                const SizedBox(height: 16),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('역할 선택', style: TextStyle(fontWeight: FontWeight.w600)),
                ),
                for (final r in UserRole.signupRoles)
                  RadioListTile<UserRole>(
                    key: Key('signup_role_${r.value}'),
                    value: r,
                    // ignore: deprecated_member_use
                    groupValue: _role,
                    title: Text(r.label),
                    contentPadding: EdgeInsets.zero,
                    // ignore: deprecated_member_use
                    onChanged: loading ? null : (v) => setState(() => _role = v!),
                  ),
                const Padding(
                  padding: EdgeInsets.only(bottom: 8),
                  child: Text(
                    '역할은 가입 시 하나로 고정됩니다. 구매와 판매를 모두 하려면 계정을 2개 만들어주세요.',
                    style: TextStyle(fontSize: 12, color: Colors.grey),
                  ),
                ),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Text(
                      _error!,
                      key: const Key('signup_error'),
                      style: TextStyle(color: Theme.of(context).colorScheme.error),
                    ),
                  ),
                if (_success != null)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_success!,
                            key: const Key('signup_success'),
                            style: const TextStyle(color: Colors.green)),
                        TextButton(
                          onPressed: () => Navigator.of(context).pop(),
                          child: const Text('로그인하러 가기'),
                        ),
                      ],
                    ),
                  ),
                FilledButton(
                  key: const Key('signup_submit'),
                  onPressed: loading ? null : _submit,
                  child: Text(loading ? '처리 중…' : '가입하기'),
                ),
                const SizedBox(height: 12),
                TextButton(
                  onPressed: loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('이미 계정이 있으신가요? 로그인'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
