// 관리자 차단 화면 — 모바일은 구매자·판매자 전용(AR9). admin 역할로 로그인하면
// 안내 후 로그아웃하도록 유도한다(운영은 web에서).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_controller.dart';

class AdminBlockedScreen extends ConsumerWidget {
  const AdminBlockedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loading = ref.watch(authControllerProvider).isLoading;
    return Scaffold(
      appBar: AppBar(title: const Text('안내')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.desktop_windows, size: 48, color: Colors.grey),
                const SizedBox(height: 16),
                const Text(
                  '관리자 기능은 웹에서 이용해주세요.\n모바일 앱은 구매자·판매자 전용입니다.',
                  key: Key('admin_blocked_message'),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 24),
                FilledButton(
                  key: const Key('admin_blocked_logout'),
                  onPressed: loading
                      ? null
                      : () => ref.read(authControllerProvider.notifier).signOut(),
                  child: const Text('로그아웃'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
