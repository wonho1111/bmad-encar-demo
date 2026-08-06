// 로그인만 확인하는 게이트 — 역할은 보지 않는다(역할 통합, FR52·FR53).
//
// web의 `lib/auth/guard.ts` `requireUser()`와 **같은 자리**이고, 일부러 같은 모양(함수)으로
// 뒀다. Story 14.3이 웹에서 `requireRole(SELLER)` → `requireUser()`로 완화한 것을 앱에 미러링한다.
//
// **왜 공용으로 빼나:** 판매 관련 화면 3곳(등록·내 매물 관리·수정)이 각자 같은 가드를 인라인으로
// 들고 있었다. 그러면 게이트를 바꿀 때 한 곳을 빠뜨려도 나머지가 초록이라 아무도 모른다 —
// 웹에서 실제로 그 사고가 났다(대장 #180). 한 곳으로 모으면 못 어긴다(CLAUDE.md B9).
//
// **왜 역할을 안 보나:** 누가 사고파는지는 계정 종류가 아니라 **매물의 소유권**으로 판정한다.
// 수정·삭제·구매완료가 등록자 본인만 가능한 것은 RLS가 이미 강제하므로(0002 등), 화면 가드는
// "로그인했는가"만 보면 된다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth_controller.dart';

/// 미로그인이면 안내 화면을, 로그인 상태면 `null`을 돌려준다.
///
/// 호출부 관례(세 화면 동일):
/// ```dart
/// final blocked = requireUser(ref, title);
/// if (blocked != null) return blocked;
/// ```
Widget? requireUser(WidgetRef ref, String title) {
  final user = ref.watch(currentUserProvider);
  if (user != null) return null;
  return Scaffold(
    appBar: AppBar(title: Text(title)),
    body: const Center(
      child: Padding(
        padding: EdgeInsets.all(24),
        child: Text(
          '로그인이 필요합니다.',
          key: Key('require_user_blocked'),
          textAlign: TextAlign.center,
        ),
      ),
    ),
  );
}
