// 인증 후 홈 — 역할·이메일 + 매물 탐색 진입(②) + AI 검색 전역 진입(③, FAB).
// nav-ia-rules §1·§2: 구매자/판매자 공통 홈(R1 상위집합), 1순위 과업=매물 탐색(R2),
//   AI 는 전역 진입점(R3, Flutter=FAB). 판매자 전용(등록·관리)은 7.3·7.4 에서.
// 관리자(admin)는 모바일 제외(AR9) → main.dart 가 차단 화면으로 보낸다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../ai_search/ai_chat_screen.dart';
import '../listings/my_listings_screen.dart';
import '../listings/search_screen.dart';
import '../listings/sell_screen.dart';
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
      // AI 검색 전역 진입(nav-ia R3) — 어느 화면에서든 닿는 보조 동작을 홈에서 FAB 로.
      floatingActionButton: FloatingActionButton.extended(
        key: const Key('ai_fab'),
        onPressed: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => const AiChatScreen()),
        ),
        icon: const Icon(Icons.smart_toy_outlined),
        label: const Text('AI 검색'),
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

                // ② 매물 탐색 — 1순위 과업으로 바로 진입(R2).
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    key: const Key('go_search'),
                    onPressed: () => Navigator.of(context).push(
                      MaterialPageRoute(builder: (_) => const SearchScreen()),
                    ),
                    icon: const Icon(Icons.search),
                    label: const Text('매물 탐색'),
                  ),
                ),
                const SizedBox(height: 12),

                // 판매자 전용(nav-ia §2): 매물 등록 진입. buyer 에게는 노출 안 함.
                if (role == UserRole.seller) ...[
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('go_sell'),
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(builder: (_) => const SellScreen()),
                      ),
                      icon: const Icon(Icons.add_box_outlined),
                      label: const Text('매물 등록'),
                    ),
                  ),
                  const SizedBox(height: 12),

                  // 판매자 전용: 내 매물 관리(수정·삭제·구매완료, FR6·8). buyer 미노출.
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('go_my_listings'),
                      onPressed: () => Navigator.of(context).push(
                        MaterialPageRoute(
                            builder: (_) => const MyListingsScreen()),
                      ),
                      icon: const Icon(Icons.inventory_2_outlined),
                      label: const Text('내 매물 관리'),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
