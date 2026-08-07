// Story 16.4 채팅 목록 화면 위젯테스트 — 방별 안읽음 배지(DW-548, §12.6) 렌더 확인(코드리뷰 지적:
// app_router_test.dart의 기존 테스트는 chatUnreadByRoomProvider *조회 횟수*만 셌지, 그 값을
// 화면이 실제로 무엇으로 그리는지는 아무도 보지 않았다).
//
// chat_room_screen_test.dart와 같은 방식으로 화면을 직접 harness로 구동한다(라우터를 거치지
// 않는다) — ChatListScreen은 showAppBar 파라미터만으로 셸/단독 두 자리에 쓰이는 순수한 화면이라
// app_router_test.dart처럼 라우팅 판정을 볼 필요가 없다(chat_room_screen_test.dart 헤더와 동일 근거).
//
// 이 파일이 안 보는 것: 내비 아이콘 총합 배지(chatUnreadTotalProvider) — 그건 셸(_AppShell)이
// 그리므로 app_router_test.dart의 "_ChatTabIcon 안읽음 배지" group이 본다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show User;

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/chat/chat_list_screen.dart';
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_providers.dart';

User _fakeUser(String id) => User(
  id: id,
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'test@example.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

/// model을 방마다 다르게 줘서 각 방의 Card를 화면에 뜬 고유 텍스트로 구분해 찾는다.
ChatRoomSummary _room(String id, {required String model}) => ChatRoomSummary(
  id: id,
  listingId: 'listing-$id',
  buyerId: 'buyer-1',
  sellerId: 'seller-1',
  buyerName: '구매자',
  sellerName: '판매자',
  listing: ChatRoomListing(
    manufacturer: '현대',
    model: model,
    year: 2020,
    price: 20000000,
    status: 'on_sale',
  ),
);

Widget _harness({
  required List<ChatRoomSummary> rooms,
  required Map<String, int> unreadByRoom,
}) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWithValue(_fakeUser('buyer-1')),
      chatRoomsProvider.overrideWith((ref) async => rooms),
      chatUnreadByRoomProvider.overrideWith((ref) async => unreadByRoom),
    ],
    child: const MaterialApp(home: ChatListScreen()),
  );
}

void main() {
  group('방별 안읽음 배지(DW-548, §12.6)', () {
    testWidgets('안읽음 3건인 방은 배지에 "3"이 보이고, 0건(unreadByRoom에 없음)인 방은 배지가 없다', (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(
          rooms: [_room('room-1', model: '아반떼'), _room('room-2', model: '쏘나타')],
          unreadByRoom: const {'room-1': 3},
        ),
      );
      await tester.pumpAndSettle();

      final tile1 = find.ancestor(
        of: find.text('[현대] 아반떼 · 2020년'),
        matching: find.byType(Card),
      );
      final tile2 = find.ancestor(
        of: find.text('[현대] 쏘나타 · 2020년'),
        matching: find.byType(Card),
      );
      expect(tile1, findsOneWidget);
      expect(tile2, findsOneWidget);

      expect(
        find.descendant(of: tile1, matching: find.text('3')),
        findsOneWidget,
        reason: 'room-1(안읽음 3건)은 배지 숫자 "3"이 그 방의 행에 보여야 한다',
      );
      expect(
        find.descendant(of: tile2, matching: find.byType(Badge)),
        findsNothing,
        reason: 'room-2(unreadByRoom에 없음 → 0건)는 배지 자체가 그려지면 안 된다',
      );
    });

    // 아래 두 테스트는 app_router_test.dart의 "_ChatTabIcon 안읽음 배지" group과 같은 수준으로
    // 맞춘다(코드리뷰 patch 5) — 내비 총합 배지는 99+ 캡·시맨틱 라벨을 둘 다 검증하는데,
    // 같은 접근성 계약(Semantics+ExcludeSemantics, "안읽음 메시지 N건")을 쓰는 방별 배지는
    // 이전엔 3건 케이스만 있고 캡·시맨틱 라벨 검증이 없었다.
    testWidgets('안읽음 3건 — 시맨틱 라벨도 같은 건수를 담는다', (tester) async {
      final semanticsHandle = tester.ensureSemantics();
      await tester.pumpWidget(
        _harness(
          rooms: [_room('room-1', model: '아반떼')],
          unreadByRoom: const {'room-1': 3},
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.bySemanticsLabel(RegExp('안읽음 메시지 3건')),
        findsOneWidget,
        reason: '스크린리더 라벨도 시각 배지와 같은 건수를 담아야 한다(ExcludeSemantics가 시각 텍스트만 감춘다)',
      );
      semanticsHandle.dispose();
    });

    testWidgets('안읽음 150건 — 시각 배지는 "99+"로 캡되지만 시맨틱 라벨은 실제 건수(150)를 담는다', (
      tester,
    ) async {
      final semanticsHandle = tester.ensureSemantics();
      await tester.pumpWidget(
        _harness(
          rooms: [_room('room-1', model: '아반떼')],
          unreadByRoom: const {'room-1': 150},
        ),
      );
      await tester.pumpAndSettle();

      final tile1 = find.ancestor(
        of: find.text('[현대] 아반떼 · 2020년'),
        matching: find.byType(Card),
      );
      expect(
        find.descendant(of: tile1, matching: find.text('99+')),
        findsOneWidget,
        reason: '99 초과는 시각적으로 "99+"로 눌러야 한다',
      );
      expect(
        find.descendant(of: tile1, matching: find.text('150')),
        findsNothing,
        reason: '시각 텍스트에 150이 그대로 노출되면 캡이 동작하지 않은 것이다',
      );
      expect(
        find.bySemanticsLabel(RegExp('안읽음 메시지 150건')),
        findsOneWidget,
        reason: '스크린리더는 캡 없이 실제 건수(150)를 그대로 읽어야 한다',
      );
      semanticsHandle.dispose();
    });
  });
}
