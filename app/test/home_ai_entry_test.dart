// 홈의 AI 진입 형태를 고정한다 — UX 확정 D12: *"AI 검색 = FAB 아님. 홈 최상단 큰 검색부"*.
//
// **이 검사가 존재하는 이유:** 앱 홈엔 `Key('ai_fab')` FAB이 붙어 있었는데, D12가 그걸
// 명시적으로 폐기(*"이전 앱의 AI=FAB는 'AI가 부가기능'이던 흔적 → 폐기"*)한 뒤에도 한 달 넘게
// 남아 있었고 **참조하는 검사가 하나도 없었다**(`grep -rn ai_fab app/` → 구현 1건뿐).
// 웹에서도 같은 날 같은 어긋남을 제거했고(`web/e2e/nav-and-hero.spec.ts` B5b), 앱도 같은 이유로
// 검사를 남긴다 — 문서에만 적어두면 다음에 또 놓친다.
//
// **두 축을 같이 본다.** "FAB이 없다"만 보면 AI 진입이 통째로 사라져도 초록이 된다 —
// 실제로 이번 작업에서 *"FAB만 떼면 AI로 갈 길이 사라진다"* 가 쟁점이었다. 그래서
// "FAB 없음"과 "최상단 AI 진입 있음"을 한 검사 안에서 함께 확인한다.
//
// 이 검사가 **안 보는 것**(추측이 아니라 실제 한계):
//   · 눌렀을 때 실제로 AI 화면이 뜨는지 — 라우팅 push 이후는 Supabase 세션이 필요해 여기선 안 본다.
//     실기기 확인은 Epic 16-6(앱 통합 시연 검증) 몫이다.
//   · 디자인 토큰(웹 petrol 히어로 밴드 미러링)과 하단 4탭 — 둘 다 Story 16.1 몫이라 아직 없다.
//   · 최근 매물 목록 본문 — 아래 harness는 매물 조회를 빈 목록으로 대체한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listings_providers.dart';

/// 최소한의 가짜 사용자 — 홈은 null 여부(로그인)만 본다(역할 통합 이후 역할은 안 본다).
User _fakeUser() => User(
      id: '00000000-0000-0000-0000-000000000001',
      appMetadata: const {},
      userMetadata: const {},
      aud: 'authenticated',
      email: 'seller@test.com',
      createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
    );

/// 홈을 기기·네트워크 없이 그린다. 최근 매물은 빈 목록으로 대체한다 — 이 검사가 보는 것은
/// 상단 진입 구성이지 목록 본문이 아니다.
Widget _harness() => ProviderScope(
      overrides: [
        currentUserProvider.overrideWithValue(_fakeUser()),
        recentListingsProvider
            .overrideWith((ref) async => const <ListingCardData>[]),
      ],
      child: const MaterialApp(home: HomeScreen()),
    );

void main() {
  group('홈 AI 진입 = 최상단 검색부(FAB 아님) — D12', () {
    testWidgets('FloatingActionButton이 없다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      expect(find.byType(FloatingActionButton), findsNothing);
      // 옛 키가 되살아나는 것도 같이 막는다.
      expect(find.byKey(const Key('ai_fab')), findsNothing);
    });

    testWidgets('AI 진입이 홈에 있고, 매물 탐색 CTA보다 위에 있다', (tester) async {
      await tester.pumpWidget(_harness());
      await tester.pump();

      final ai = find.byKey(const Key('go_ai'));
      final search = find.byKey(const Key('go_search'));
      expect(ai, findsOneWidget, reason: 'AI 진입이 사라지면 FAB을 뗀 의미가 없다');
      expect(search, findsOneWidget);

      // "최상단"은 위치로 정해진 것이라(D12: AI가 제품의 얼굴) 순서까지 고정한다 —
      // 있기만 하면 통과시키면 맨 아래로 밀려나도 초록이 된다.
      final aiY = tester.getTopLeft(ai).dy;
      final searchY = tester.getTopLeft(search).dy;
      expect(aiY, lessThan(searchY),
          reason: 'AI 진입이 매물 탐색 CTA보다 위에 있어야 한다');
    });
  });
}
