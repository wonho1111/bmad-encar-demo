// 인증 후 홈(토대) — 역할·이메일 표시 + 로그아웃.
// nav-ia-rules §1: buyer/seller 공통 홈(R1 상위집합). 탐색 미리보기·AI FAB 등은 7.2부터.
// 관리자(admin)는 모바일 제외(AR9) → 여기까지 오지 않고 main.dart 가 차단 화면으로 보낸다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_controller.dart';
import 'user_role.dart';

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(currentUserProvider);
    final role = ref.watch(currentRoleProvider);
    final loading = ref.watch(authControllerProvider).isLoading;

    return Scaffold(
      appBar: AppBar(
        title: const Text('엔카 데모'),
        actions: [
          TextButton(
            key: const Key('logout'),
            onPressed: loading
                ? null
                : () => ref.read(authControllerProvider.notifier).signOut(),
            child: const Text('로그아웃', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Padding(
            padding: const EdgeInsets.all(24),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('환영합니다 👋', style: Theme.of(context).textTheme.headlineSmall),
                const SizedBox(height: 12),
                Text('이메일: ${user?.email ?? '-'}', key: const Key('home_email')),
                const SizedBox(height: 4),
                Text('역할: ${role?.label ?? '미상'}', key: const Key('home_role')),
                const SizedBox(height: 24),
                const Text(
                  '앱 골격(7.1)이 정상 동작합니다. 매물 탐색·AI 검색·판매 등 화면은 다음 스토리(7.2~)에서 추가됩니다.',
                  style: TextStyle(color: Colors.grey),
                ),
                if (role == UserRole.seller) ...[
                  const SizedBox(height: 16),
                  const Text('· 판매자: 내 매물 등록·관리(7.3·7.4 예정)'),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
