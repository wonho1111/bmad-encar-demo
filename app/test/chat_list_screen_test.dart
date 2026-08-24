// Story 16.4 채팅 목록 화면 위젯테스트 — 방별 안읽음 배지(DW-548, §12.6) 렌더 확인(코드리뷰 지적:
// app_router_test.dart의 기존 테스트는 chatUnreadByRoomProvider *조회 횟수*만 셌지, 그 값을
// 화면이 실제로 무엇으로 그리는지는 아무도 보지 않았다).
//
// chat_room_screen_test.dart와 같은 방식으로 화면을 직접 harness로 구동한다(라우터를 거치지
// 않는다) — ChatListScreen은 showAppBar 파라미터만으로 셸/단독 두 자리에 쓰이는 순수한 화면이라
// app_router_test.dart처럼 라우팅 판정을 볼 필요가 없다(chat_room_screen_test.dart 헤더와 동일 근거).
//
// 이 파일이 안 보는 것: 내비 아이콘 총합 배지(chatUnreadTotalProvider)가 실제로 무엇을 렌더하는지
// — 그건 셸(_AppShell)이 그리므로 app_router_test.dart의 "_ChatTabIcon 안읽음 배지" group이 본다.
// (아래 "방을 열고 뒤로가기" group은 렌더가 아니라 그 provider가 **재조회되는지**(invalidate 배선)
// 만 보므로 위 한계와 모순되지 않는다 — app_router.dart의 실제 셸처럼 항상 watch하는 자리를
// 하네스에 직접 흉내 낸다.)
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart' show Supabase, User;

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/chat/chat_list_screen.dart';
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_providers.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:app/features/chat/chat_room_screen.dart';

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

/// 방 탭 → ChatRoomScreen이 열릴 때 실 네트워크를 타지 않도록 하는 최소 가짜 레포
/// (app_router_test.dart의 `_FakeChatRepo`와 동일 근거 — 이 파일은 방 화면 자체를 검증하지
/// 않고, "방을 열었다 돌아오면 배지 provider들이 재조회되는가"만 본다).
class _FakeChatRoomRepo extends ChatRepository {
  @override
  Future<List<ChatMessage>> fetchMessages(String roomId, {String? atOrAfterCreatedAt}) async =>
      const [];

  @override
  Future<ChatRoomSummary?> fetchRoom(String roomId) async => null; // 당사자 확인 스킵 → markRoomRead 미호출.
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

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

  group('제목 줄바꿈 방지(프로젝트 규칙 13/D5, 코드리뷰 patch 8)', () {
    testWidgets(
        '320dp 좁은 화면 + 긴 제조사·모델명 + 3자리 배지에서도 제목은 1줄로 말줄임되고 레이아웃이 안 무너진다', (
      tester,
    ) async {
      // 이 스토리가 같은 Row에 배지+패딩을 끼워 넣어 제목 폭이 좁아졌다 — 프로젝트 규칙 13(D5)은
      // 공간이 부족해도 줄바꿈으로 찌그러지지 않고 말줄임("…")으로만 처리하라고 못박는다.
      await tester.binding.setSurfaceSize(const Size(320, 640));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        _harness(
          rooms: [_room('room-1', model: '그랜저IG하이브리드익스클루시브풀옵션장기렌트특별출고모델')],
          unreadByRoom: const {'room-1': 150}, // 99+ 캡으로 3자리폭 배지("99+")를 만든다.
        ),
      );
      await tester.pumpAndSettle();

      final titleFinder = find.textContaining('그랜저IG');
      expect(titleFinder, findsOneWidget);
      final titleWidget = tester.widget<Text>(titleFinder);
      expect(titleWidget.maxLines, 1, reason: '2줄로 밀려 배지·가격 행과 어긋나면 안 된다');
      expect(titleWidget.overflow, TextOverflow.ellipsis, reason: '넘치는 부분은 "…"로 잘려야 한다');

      expect(find.text('99+'), findsOneWidget, reason: '3자리 폭 배지가 함께 있어도 제목 규칙은 그대로 지켜져야 한다');
      expect(tester.takeException(), isNull, reason: '좁은 화면에서 렌더 오버플로 예외가 나면 안 된다');
    });
  });

  group('방을 열고 뒤로가기(pop-back) → 배지 provider 재조회(코드리뷰 patch 2)', () {
    // 코드리뷰 patch 2 — 이 파일 헤더 바로 위 주석(spec-16-1 P2)이 chatRoomsProvider에 대해
    // 이미 한 번 고친 버그 클래스를 이번 스토리가 만든 chatUnreadByRoomProvider·
    // chatUnreadTotalProvider가 그대로 물려받았다: 방에서 markRoomRead가 끝나고 채팅 탭으로
    // 돌아와도 이미 그 탭에 있으므로 app_router.dart의 onActivate(탭 재진입 트리거)가 다시
    // 안 불려 배지가 줄지 않는다. 셋 다 같은 pop-back 콜백에서 함께 invalidate돼야 한다.
    testWidgets(
        '방을 열었다 뒤로가기로 돌아오면 chatRoomsProvider·chatUnreadByRoomProvider·'
        'chatUnreadTotalProvider 셋 다 다시 조회된다', (tester) async {
      var roomsFetchCount = 0;
      var byRoomFetchCount = 0;
      var totalFetchCount = 0;
      final repo = _FakeChatRoomRepo();

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            currentUserProvider.overrideWithValue(_fakeUser('buyer-1')),
            chatRepositoryProvider.overrideWithValue(repo),
            chatRoomsProvider.overrideWith((ref) async {
              roomsFetchCount++;
              return [_room('room-1', model: '아반떼')];
            }),
            chatUnreadByRoomProvider.overrideWith((ref) async {
              byRoomFetchCount++;
              return const <String, int>{'room-1': 2};
            }),
            chatUnreadTotalProvider.overrideWith((ref) async {
              totalFetchCount++;
              return 2;
            }),
          ],
          child: MaterialApp(
            home: Column(
              children: [
                // 실제 앱에서 chatUnreadTotalProvider를 항상 watch하는 자리는 셸의
                // _ChatTabIcon(app_router.dart)이다 — 이 하네스엔 셸이 없으므로 같은 이유로
                // 항상 watch하는 자리를 직접 흉내 낸다. watch하는 자리가 없으면 invalidate가
                // 아무 관찰 가능한 효과를 안 남긴다(Riverpod은 아무도 안 읽는 provider를
                // invalidate해도 재조회를 안 한다).
                Consumer(
                  builder: (context, ref, _) {
                    ref.watch(chatUnreadTotalProvider);
                    return const SizedBox.shrink();
                  },
                ),
                const Expanded(child: ChatListScreen()),
              ],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(roomsFetchCount, 1);
      expect(byRoomFetchCount, 1);
      expect(totalFetchCount, 1);

      await tester.tap(find.text('[현대] 아반떼 · 2020년'));
      await tester.pumpAndSettle();
      expect(find.byType(ChatRoomScreen), findsOneWidget, reason: '방 화면이 열려야 이후 뒤로가기가 의미 있다');

      await tester.pageBack();
      await tester.pumpAndSettle();

      expect(roomsFetchCount, 2, reason: '기존 동작(spec-16-1 P2) — 방 화면 이탈 시 재조회');
      expect(byRoomFetchCount, 2, reason: '방별 배지도 같은 pop-back에서 재조회돼야 한다(패치 2)');
      expect(totalFetchCount, 2, reason: '내비 총합 배지도 같은 pop-back에서 재조회돼야 한다(패치 2)');
    });
  });
}
