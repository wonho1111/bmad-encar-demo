// 찜 탭 플레이스홀더(Story 16.1) — 실제 찜 토글·목록은 16.3 몫이다(spec-16-1 Never 경계).
// 이 화면은 하단 4탭 셸이 완전하다는 것만 보여준다. appBar 없음 — 셸(app_router.dart)의
// 공통 AppBar(우상단 프로필 아바타)를 그대로 쓴다.
import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

class WishlistPlaceholderScreen extends StatelessWidget {
  const WishlistPlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.surfaceBase,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            key: const Key('wishlist_placeholder'),
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.favorite_border, size: 48, color: AppColors.inkMuted),
              const SizedBox(height: 16),
              const Text(
                '찜 목록은 곧 제공됩니다.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.inkMuted, fontSize: 15),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
