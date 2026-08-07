// spec-16-1 I/O & Edge-Case Matrix 커버리지 — app_router.dart의 redirect·셸을 실제로
// 구동해서 본다(provider 값만 보는 것과 다르다: current_role_provider_test.dart는
// currentRoleProvider 하나만 보고, 이 파일은 그 값을 GoRouter가 실제로 어느 화면으로
// 옮기는지까지 본다).
//
// 매트릭스 5행 중 이 파일이 다루는 4행:
//   1) 미인증 앱 실행 → `/login`
//   2) admin 로그인 → `/admin-blocked`
//   3) role 없는 세션 → 홈 셸(차단 아님)
//   5) 찜 탭 진입 → 플레이스홀더, 크래시 없음
// 그리고 4행(탭 전환 후 복귀)은 스크롤 오프셋 보존을 "매트릭스 4행(스크롤)" group이 본다
// (매트릭스 원문이 명시한 채팅 탭으로 확인한다 — review, spec-16-1 P13). 네비 스택 보존은
// 이 앱 아키텍처에서 재현 불가능해 별도 group을 두지 않는다(파일 하단 "이 파일이 안 보는
// 것" 참조).
//
// review_loop_iteration 1(bad_spec 루프백)이 실측한 4개 결함의 회귀도 이 파일이 고정한다:
//   · 홈 퀵액션(상세류) push 후 AppBar 2개 공존 — "AppBar 단일성" group
//   · 채팅 탭 재진입 시 chatRoomsProvider 재조회 불가 — "chatRoomsProvider 재조회" group
//   · 비홈 탭에서 시스템 back이 앱을 종료 — "PopScope" group
//   · 로그인 방향 redirect 분기 미검증(뮤테이션 생존) — "로그인 방향 리액티브 redirect" group
//
// 스토리 자체 Verification이 "컴파일·단위/위젯 테스트 수준"으로 범위를 그은 대로, 여기도
// 실기기 대신 위젯 테스트로 본다. require_user_test.dart·home_ai_entry_test.dart의
// `_fakeUser`+`ProviderScope(overrides:...)` 관례를 그대로 재사용한다.
//
// 이 파일이 안 보는 것(추측이 아니라 실제 한계):
//   · '/sell' 탭 재방문 후 수정→등록이 INSERT로 가는지(autoDispose 수명 충돌 해소)는
//     sell_controller_test.dart가 본다 — 15필드 폼을 위젯 테스트로 채우는 것보다
//     컨트롤러를 직접 구동하는 쪽이 더 빠르고 안정적이다(A2 단순함).
//   · AC7("go_ai·go_search·go_chat·go_sell·go_my_listings·최근매물카드 중 어느 것이든")의
//     모든 진입점을 낱낱이 돌리지는 않는다 — go_ai·go_search·go_chat·go_sell·최근매물카드·
//     채팅방(chat_list_screen.dart 방 탭)까지 "브랜치 안에서 시작하는 push 포함, 전부
//     rootNavigator: true 메커니즘을 쓴다"는 사실을 대표 검증한다(review, spec-16-1 P4 —
//     브랜치 **안에서** 시작하는 push가 특히 회귀 위험이 크다: 셸 경계 코드가 화면
//     자신이 아니라 그 화면을 여는 쪽에 있어서, 새 진입점을 추가할 때 빠뜨리기 쉽다).
//   · 브랜치 안(그 탭의 Navigator)에 직접 push한 화면이 탭 전환 후에도 남아있는지 —
//     이 앱 아키텍처에서는 애초에 도달 불가능하다(설계상 한계, review, spec-16-1 P13).
//     실제 상세류 push는 전부 `rootNavigator: true`로 셸 밖(진짜 루트 Navigator)에
//     쌓인다(위 셸 경계 원칙). 그러니 "브랜치 Navigator에 직접 push한 프로브가 탭을
//     오가도 남아있다"를 검증하는 테스트는 go_router의 `StatefulShellRoute` 자체가 이미
//     보장하는 것을 확인할 뿐이라, 이 리포의 어떤 변경(회귀)도 못 잡는다(실측: 그
//     메커니즘을 되돌리는 어떤 뮤테이션도 없이 항상 green) — 그래서 여기 두지 않는다.
import 'dart:async';

// `SearchController`를 hide한다 — listings_providers.dart의 우리 `SearchController`
// (탐색 화면 컨트롤러)와 이름이 겹친다(Flutter Material의 SearchAnchor용 위젯). 이 파일은
// Material의 SearchController를 안 쓴다.
import 'package:flutter/material.dart' hide SearchController;
import 'package:flutter_riverpod/flutter_riverpod.dart';
// `Override`는 flutter_riverpod.dart의 기본 barrel엔 없다(riverpod 3의 의도적 분리) —
// misc.dart가 그 공개 창구다.
import 'package:flutter_riverpod/misc.dart' show Override;
// `StateProvider`도 마찬가지로 기본 barrel엔 없다 — riverpod 3에서 "legacy" API로 분리됐다
// (권장 대체는 Notifier이지만, 로그인/로그아웃 테스트의 mutable 테스트 상태로는 이게 제일 간단하다).
import 'package:flutter_riverpod/legacy.dart' show StateProvider;
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/core/router/app_router.dart';
import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/chat/chat_list_screen.dart';
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_providers.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_card.dart';
import 'package:app/features/listings/listing_form.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/sell_controller.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:app/features/wishlist/wishlist_screen.dart';

/// require_user_test.dart·current_role_provider_test.dart와 동일한 최소 가짜 사용자.
User _fakeUser({String? role}) => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: role == null ? const {} : {'role': role},
  aud: 'authenticated',
  email: 'test@example.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

/// 라우터를 실제로 구동하는 하네스. `appRouterProvider`가 내부에서 보는 provider들
/// (`currentUserProvider`·`currentRoleProvider`(파생)·`authStateProvider`)을 오버라이드해
/// 기기·네트워크·Supabase 초기화 없이 판정을 확인한다.
///
/// `authStateProvider`를 빈 스트림으로 오버라이드하는 이유: app_router.dart의
/// `appRouterProvider`가 `ref.listen(authStateProvider, ...)`로 refreshListenable을
/// 연결하는데, 오버라이드하지 않으면 그 provider의 실제 구현이 전역 `supabase` 싱글턴을
/// 만져 "초기화 안 됨" 예외로 죽는다.
// chatUnreadTotalProvider(Story 16.4, §12.6)는 non-autoDispose이고 하단 NavigationBar
// (`_ChatTabIcon`, app_router.dart)가 셸 자체에서 매 프레임 watch한다 — chatRoomsProvider와
// 달리 채팅 탭을 누르기 전에도, 채팅과 무관한 이 파일의 다른 모든 테스트에서도 조회가 나간다.
// 기본값을 0/빈 Map으로 고정해 두지 않으면 이 파일의 모든 홈-셸 테스트가 실 Supabase 네트워크를
// 매번 건드린다(가짜 자격증명뿐이라 매번 실패하지만, 느리고 시끄럽다). 이 파일의 다섯
// ProviderContainer/_harness 구성이 이 기본값을 공유한다. Riverpod는 같은 provider를
// overrides 리스트에 두 번 넣으면 assert로 죽으므로(실측 확인), 이 두 provider 자체를
// 검증하는 테스트는 이 기본값을 넣지 않고 카운팅 override를 직접 넣는다.
List<Override> _chatUnreadDefaults() => [
  chatUnreadTotalProvider.overrideWith((ref) async => 0),
  chatUnreadByRoomProvider.overrideWith((ref) async => const <String, int>{}),
];

Widget _harness({
  required User? user,
  List<Override> extraOverrides = const [],
  bool chatUnreadDefaults = true,
}) {
  return ProviderScope(
    overrides: [
      currentUserProvider.overrideWithValue(user),
      authStateProvider.overrideWith((ref) => const Stream<AuthState>.empty()),
      if (chatUnreadDefaults) ..._chatUnreadDefaults(),
      ...extraOverrides,
    ],
    child: Consumer(
      builder: (context, ref, _) {
        final router = ref.watch(appRouterProvider);
        return MaterialApp.router(routerConfig: router);
      },
    ),
  );
}

/// 홈 셸(로그인 상태)로 들어가는 테스트가 공통으로 필요로 하는 오버라이드 —
/// HomeScreen이 최근 매물을 조회하므로, 실제 Supabase 없이 빈/고정 목록으로 대체한다
/// (home_ai_entry_test.dart와 동일 패턴).
Override _recentListings(List<ListingCardData> data) =>
    recentListingsProvider.overrideWith((ref) async => data);

ListingCardData _fakeListing(int i) => ListingCardData(
  id: 'listing-$i',
  manufacturer: '현대',
  model: '아반떼 $i',
  year: 2020,
  price: 20000000 + i * 100000,
  mileage: 50000,
  region: '서울',
);

/// chatRoomsProvider 오버라이드용 가짜 방 목록 항목 — listing 임베드를 채워 화면에
/// 구분 가능한 텍스트가 뜨게 한다(방 탭 탭 테스트가 특정 방을 찾아 눌러야 하므로).
ChatRoomSummary _fakeRoom(int i) => ChatRoomSummary(
  id: 'room-$i',
  listingId: 'listing-$i',
  buyerId: 'buyer-1',
  sellerId: 'seller-1',
  buyerName: '구매자',
  sellerName: '판매자',
  listing: ChatRoomListing(
    manufacturer: '현대',
    model: '아반떼 $i',
    year: 2020,
    price: 20000000 + i * 100000,
    status: 'on_sale',
  ),
);

/// ChatRoomScreen이 방을 열 때 쓰는 레포 — 실제 네트워크 없이 즉시 빈 목록을 돌려준다
/// (폴링 타이머는 여전히 돌지만, 이 테스트들은 타이머가 실제로 발화하기 전에 화면을
/// pop해 정리한다 — 그렇지 않으면 "pending timer"로 테스트가 실패한다).
class _FakeChatRepo extends ChatRepository {
  @override
  Future<List<ChatMessage>> fetchMessages(
    String roomId, {
    String? atOrAfterCreatedAt,
  }) async => const [];

  /// Story 16.4 — ChatRoomScreen이 진입 시 당사자 확인(markRoomRead 게이트)을 위해 직접
  /// `fetchRoom`을 호출한다. 오버라이드하지 않으면 실 Supabase 클라이언트로 네트워크 호출이
  /// 나가버린다(가짜 자격증명뿐인 테스트 환경에서는 무의미하고 느리다) — null(참여자 아님)로
  /// 고정해 markRoomRead 호출 자체를 건너뛰게 한다(이 파일의 테스트는 읽음 갱신을 검증하지
  /// 않는다 — 그건 chat_room_screen_test.dart 몫).
  @override
  Future<ChatRoomSummary?> fetchRoom(String roomId) async => null;
}

/// go_search 테스트용 — SearchController.build()의 `Future.microtask(search)`가 실제
/// listingsRepositoryProvider(전역 supabase)로 네트워크를 타지 않도록 즉시 빈 결과로 고정한다.
class _FakeSearchController extends SearchController {
  @override
  SearchState build() =>
      const SearchState(results: AsyncValue.data(<ListingCardData>[]));
}

/// 쓰기가 끝나는 시점을 테스트가 잡고 있는 가짜 레포 — "제출이 진행 중"인 순간을 만든다.
class _GatedRepo extends ListingsRepository {
  _GatedRepo(this.gate);

  final Completer<void> gate;

  @override
  Future<void> createListing(
    Map<String, dynamic> payload, {
    required String sellerId,
  }) async => gate.future;

  @override
  Future<int> updateListing(String id, Map<String, dynamic> payload) async {
    await gate.future;
    return 1;
  }
}

/// 검증을 통과하는 최소 입력 — submit()이 실제로 쓰기 단계까지 가야 loading이 켜진다.
const _validSellInput = ListingFormInput(
  manufacturer: '현대',
  model: '아반떼',
  bodyType: '준중형차',
  year: '2021',
  price: '20000000',
  mileage: '10000',
  color: '흰색',
  fuel: '가솔린',
  transmission: '자동',
  displacement: '1600',
  seats: '5',
  region: '서울',
);

void main() {
  // 이 파일 전체에서 딱 한 번 가짜 자격증명으로 Supabase를 초기화한다(네트워크 호출은
  // 없다). **왜 아직 필요한가** — spec-16-1 Task가 지목한 원인(`ChatListScreen`이 provider를
  // 거치지 않고 전역 `supabase.auth.currentUser`를 직독하던 것)은 해소했지만, 전역 싱글턴을
  // 무는 자리가 둘 더 남아 있고 둘 다 이 스토리 범위 밖이다:
  //   · `ChatRoomScreen`(채팅방 — 16.4가 다룰 파일)이 전역 `supabase`를 직접 쓴다.
  //   · `ListingsRepository`의 생성자가 `client ?? supabase`라, 가짜 레포를 만들기만 해도
  //     전역이 필요하다(테스트마다 SupabaseClient를 따로 만들면 teardown이 realtime 종료를
  //     기다리다 멈춘다 — 실측, review, spec-16-1 P11).
  // 실제로 초기화를 빼고 돌려본 결과 이 두 자리에서만 실패했다(다른 테스트는 전부 통과).
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  group('매트릭스 1행 — 미인증 앱 실행 → /login', () {
    testWidgets('세션 없음이면 LoginScreen이 뜬다', (tester) async {
      await tester.pumpWidget(_harness(user: null));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('login_email')),
        findsOneWidget,
        reason: '미인증 세션은 redirect가 /login으로 보내야 한다(기존 AuthGate와 동일 동작)',
      );
      expect(find.byType(HomeScreen), findsNothing);
    });
  });

  group('매트릭스 2행 — admin 로그인 → /admin-blocked', () {
    testWidgets("role='admin'이면 AdminBlockedScreen이 뜬다(AR9)", (tester) async {
      await tester.pumpWidget(_harness(user: _fakeUser(role: 'admin')));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('admin_blocked_message')),
        findsOneWidget,
        reason: 'admin은 모바일 제외(AR9) — 홈 셸이 아니라 차단 안내로 가야 한다',
      );
      expect(find.byType(HomeScreen), findsNothing);
    });
  });

  group('매트릭스 3행 — role 없는 세션 → 홈 셸(차단 아님)', () {
    testWidgets('role 메타데이터 없음(14.2 이후 신규가입) → 홈 셸의 하단 4탭이 보인다', (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [_recentListings(const [])],
        ),
      );
      await tester.pumpAndSettle();

      // 차단 화면이 아니라 홈 셸이어야 한다 — currentRoleProvider(null 메타)==null이
      // admin 판정에 걸리지 않는다는 것을 라우팅 결과로 확인(current_role_provider_test.dart는
      // provider 값만 보고, 여기는 그 값이 실제로 화면을 가르는지까지 본다).
      expect(find.byKey(const Key('admin_blocked_message')), findsNothing);
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(find.byKey(const Key('go_ai')), findsOneWidget);

      // 하단 4탭 — FAB 없음(D12·spec-16-1).
      expect(find.byKey(const Key('tab_home')), findsOneWidget);
      expect(find.byKey(const Key('tab_wishlist')), findsOneWidget);
      expect(find.byKey(const Key('tab_chat')), findsOneWidget);
      expect(find.byKey(const Key('tab_sell')), findsOneWidget);
      expect(find.byType(FloatingActionButton), findsNothing);
    });

    testWidgets("role='user'(0029 기존계정 통일값)여도 홈 셸 — null과 동일 취급", (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: 'user'),
          extraOverrides: [_recentListings(const [])],
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('admin_blocked_message')), findsNothing);
      expect(find.byType(HomeScreen), findsOneWidget);
    });
  });

  group('매트릭스 5행 — 찜 탭 진입 → 실제 찜 목록 화면, 크래시 없음(Story 16.3)', () {
    testWidgets('하단 "찜" 탭을 누르면 WishlistScreen이 뜨고 예외가 없다(0건이면 빈 상태 안내)',
        (tester) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            wishlistProvider.overrideWith((ref) async => const []),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();

      expect(
        tester.takeException(),
        isNull,
        reason: '찜 탭 진입이 예외 없이 렌더돼야 한다',
      );
      expect(find.byType(WishlistScreen), findsOneWidget);
      expect(find.byKey(const Key('wishlist_empty')), findsOneWidget);
      // 홈은 여전히 트리에 있다 — 사라진 게 아니라 IndexedStack이 오프스테이지로 보존한 것이다
      // (아래 탭 보존 group과 같은 전제). `find`류는 기본적으로 offstage 요소를 건너뛰므로
      // (`skipOffstage`), 보존을 실제로 확인하려면 그 스킵을 꺼야 한다 — 껐다 켰다 비교해
      // "찾을 수 없음(꺼짐)"과 "없음(제거됨)"을 구분한다.
      expect(
        find.byType(HomeScreen, skipOffstage: false),
        findsOneWidget,
        reason:
            '홈 탭이 실제로 사라졌다면(재생성) 탭을 오갈 때마다 스크롤·상태가 매번 '
            '초기화된다는 뜻이다 — 오프스테이지 보존이 이 스토리의 핵심 계약이다',
      );
      expect(
        find.byType(HomeScreen),
        findsNothing,
        reason: '반대로 offstage 기본값(skip)에서는 안 잡혀야 한다 — 찜 탭이 실제 활성 탭이라는 뜻',
      );
    });
  });

  group('매트릭스 4행(스크롤) — 탭 전환 후 복귀: StatefulShellRoute 탭 상태 보존', () {
    // 매트릭스 4행 원문은 "채팅 탭에서 스크롤 후 홈→채팅 재이동"이다(spec-16-1 I/O 매트릭스).
    // 예전엔 이 group이 홈 탭으로 대신 증명했는데(같은 StatefulShellRoute 메커니즘이라
    // 실질 커버리지 갭은 아니었다), 매트릭스가 명시한 탭 자체를 검증하는 테스트가 없다는
    // 지적을 받아(review, spec-16-1 P13) 채팅 탭으로 옮긴다.
    testWidgets('채팅 탭에서 스크롤한 뒤 홈 탭에 갔다 돌아오면 스크롤 위치가 유지된다', (tester) async {
      // 스크롤이 실제로 발생하도록 채팅방을 여러 건 채운다(빈 목록이면 넘칠 내용이 없다).
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            chatRoomsProvider.overrideWith((ref) async {
              fetchCount++;
              return [for (var i = 0; i < 20; i++) _fakeRoom(i)];
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();
      expect(fetchCount, 1);

      // 채팅 화면 **안의** Scrollable로 범위를 좁힌다 — `find.byType(Scrollable).first`는
      // 트리 순서에 기대는 것이라, 레이아웃이 바뀌어 다른 탭·다른 위젯의 Scrollable이
      // 먼저 잡히면 이 검사가 조용히 엉뚱한 것을 재게 된다.
      final chatScrollable = find.descendant(
        of: find.byType(ChatListScreen),
        matching: find.byType(Scrollable),
      );
      expect(
        chatScrollable,
        findsOneWidget,
        reason: '채팅 목록이 스크롤 가능해야 이 검사가 스크롤 보존을 실제로 확인할 수 있다',
      );

      // 아래로 드래그(음수 dy)해 스크롤을 이동시킨다.
      await tester.drag(chatScrollable, const Offset(0, -300));
      await tester.pumpAndSettle();
      final offsetBeforeSwitch = tester
          .state<ScrollableState>(chatScrollable)
          .position
          .pixels;
      expect(
        offsetBeforeSwitch,
        greaterThan(0),
        reason: '드래그가 실제로 스크롤을 이동시켰는지부터 확인한다(0이면 이 검사가 아무것도 못 잡는다)',
      );

      // 홈 탭으로 전환 → 다시 채팅으로.
      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();

      final offsetAfterReturn = tester
          .state<ScrollableState>(chatScrollable)
          .position
          .pixels;
      expect(
        offsetAfterReturn,
        offsetBeforeSwitch,
        reason:
            'StatefulShellRoute가 브랜치별 Navigator를 IndexedStack으로 보존해야 '
            '탭을 오가도 스크롤 위치가 그대로다 — 되돌아왔는데 0으로 리셋되면 '
            '브랜치가 매번 다시 만들어지고 있다는 뜻이다(회귀).',
      );
    });
  });

  group(
    'AppBar 단일성 — 홈 퀵액션(rootNavigator push)·채팅/내차팔기 탭 모두 AppBar가 정확히 1개',
    () {
      // review_loop_iteration 1 bug #1: 홈 퀵액션으로 상세류 화면을 열면 셸의 AppBar·
      // NavigationBar가 그 화면 위에 그대로 남아 AppBar=2, NavigationBar=1이 실측됐다.
      // rootNavigator: true push가 이 화면들을 셸 밖(진짜 루트 Navigator)에 쌓아 셸 자체가
      // 안 보이는지를 본다 — AppBar 개수뿐 아니라 NavigationBar findsNothing까지 함께 본다
      // (AppBar만 세면 셸이 그대로 남아있어도 위에 화면이 덮어 AppBar가 우연히 1개로 보일 수
      // 있다 — 실제로는 NavigationBar가 화면 아래 계속 깔려 있는 상태를 놓친다).
      testWidgets('go_ai(AI 검색) — 셸이 사라지고 AiChatScreen만 남는다', (tester) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [_recentListings(const [])],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('go_ai')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(AppBar), findsOneWidget);
        expect(
          find.byType(NavigationBar),
          findsNothing,
          reason:
              '셸이 여전히 아래 깔려 있다면 NavigationBar가 트리에 남아있다(offstage 무관 —'
              ' rootNavigator push는 셸 자체를 스택 아래로 완전히 덮으므로 skipOffstage 기본값'
              '으로도 안 잡혀야 정상이다)',
        );
        expect(
          find.text('중고차 직거래'),
          findsNothing,
          reason: '셸 제목("중고차 직거래")도 함께 사라져야 한다',
        );
      });

      testWidgets('go_chat(문의 채팅 퀵액션) — 셸이 사라지고 ChatListScreen만 남는다', (
        tester,
      ) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings(const []),
              // chatRoomsProvider는 FutureProvider.autoDispose — 빌드 즉시 조회를 시도하므로
              // 실제 Supabase 없이 크래시하지 않도록 빈 목록으로 대체한다.
              chatRoomsProvider.overrideWith(
                (ref) async => const <ChatRoomSummary>[],
              ),
            ],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('go_chat')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(
          find.byType(AppBar),
          findsOneWidget,
          reason:
              '이게 바로 review_loop_iteration 1이 실측한 재현 시나리오다 — 첫 구현은 '
              '여기서 AppBar가 2개(셸 것 + ChatListScreen 자기 것) 잡혔다',
        );
        expect(find.byType(NavigationBar), findsNothing);
      });

      testWidgets('go_sell(매물 등록 퀵액션) — 셸이 사라지고 SellScreen만 남는다', (
        tester,
      ) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [_recentListings(const [])],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('go_sell')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(AppBar), findsOneWidget);
        expect(find.byType(NavigationBar), findsNothing);
      });

      testWidgets('채팅 탭(브랜치 루트)에는 AppBar가 정확히 1개', (tester) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings(const []),
              chatRoomsProvider.overrideWith(
                (ref) async => const <ChatRoomSummary>[],
              ),
            ],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('tab_chat')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(
          find.byType(AppBar),
          findsOneWidget,
          reason:
              'showAppBar 배선이 실수로 뒤집히면(true로 되돌아가면) 셸 AppBar 위에 '
              'ChatListScreen 자기 AppBar가 또 그려져 2개가 잡힌다',
        );
      });

      testWidgets('내차팔기 탭(브랜치 루트)에는 AppBar가 정확히 1개', (tester) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [_recentListings(const [])],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('tab_sell')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(
          find.byType(AppBar),
          findsOneWidget,
          reason:
              'showAppBar 배선이 실수로 뒤집히면 SellScreen 자기 AppBar가 또 그려져 '
              '2개가 잡힌다',
        );
      });

      // 아래 세 테스트는 review(spec-16-1 P4)가 지적한 대로 추가한다 — 지금까지는
      // go_ai·go_chat·go_sell(모두 **홈에서** 시작하는 push)만 pin돼 있었다. 8곳의
      // `rootNavigator: true` 중 5곳은 어떤 테스트도 뮤테이션하면 안 잡혔다(실측: 되돌려도
      // 스위트가 그대로 green). 그중에서도 브랜치 **안**(홈 탭 본문의 카드·채팅 탭의 방
      // 목록)에서 시작하는 push가 가장 위험하다 — 셸 경계를 지키는 코드가 그 화면 자신이
      // 아니라 "그 화면을 여는 지점"에 있어서, 새 진입점을 추가할 때 특히 빠뜨리기 쉽다.
      testWidgets('go_search(매물 탐색 CTA) — 셸이 사라지고 SearchScreen만 남는다', (
        tester,
      ) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings(const []),
              // SearchController.build()가 진입 즉시 검색을 시도한다 — 실제 네트워크를 타지
              // 않도록 즉시 빈 결과를 돌려주는 가짜로 대체한다(그렇지 않으면 실제 DNS/네트워크
              // 타임아웃을 기다리게 돼 테스트가 느려지거나 흔들린다).
              searchControllerProvider.overrideWith(
                () => _FakeSearchController(),
              ),
            ],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('go_search')));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(find.byType(AppBar), findsOneWidget);
        expect(find.byType(NavigationBar), findsNothing);
      });

      testWidgets('최근 매물 카드(홈 탭 본문 — 브랜치 안에서 시작하는 push) — 셸이 사라지고 '
          'ListingDetailScreen만 남는다', (tester) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings([_fakeListing(0)]),
              // 상세 조회는 실제 네트워크를 타지 않도록 고정값으로 대체 — AppBar 개수만
              // 확인하면 되므로 "찾을 수 없음" 분기(null)로 충분하다.
              listingDetailProvider(
                'listing-0',
              ).overrideWith((ref) async => null),
            ],
          ),
        );
        await tester.pumpAndSettle();

        // Story 16.2가 카드에 5:3 사진 셀을 추가해 카드가 커졌다 — 기본 테스트 뷰포트(800×600)
        // 밖으로 밀려날 수 있어 탭 전에 스크롤로 보이게 한다(홈 화면은 SingleChildScrollView).
        await tester.ensureVisible(find.byType(ListingCard));
        await tester.pumpAndSettle();

        await tester.tap(find.byType(ListingCard));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(
          find.byType(AppBar),
          findsOneWidget,
          reason:
              '홈 탭 **본문**(브랜치 안)에서 시작하는 push다 — home_screen.dart:353의 '
              'rootNavigator: true가 빠지면 셸 AppBar 위에 상세 화면 AppBar가 겹쳐 2개가 된다',
        );
        expect(find.byType(NavigationBar), findsNothing);
      });

      testWidgets('채팅방(채팅 탭 방 목록 — 브랜치 안에서 시작하는 push) — 셸이 사라지고 '
          'ChatRoomScreen만 남는다', (tester) async {
        var fetchCount = 0;
        final room = _fakeRoom(0);
        final repo = _FakeChatRepo();
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings(const []),
              chatRoomsProvider.overrideWith((ref) async {
                fetchCount++;
                return [room];
              }),
              chatRoomDetailProvider(room.id).overrideWith((ref) async => room),
              chatRepositoryProvider.overrideWithValue(repo),
            ],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(const Key('tab_chat')));
        await tester.pumpAndSettle();
        expect(fetchCount, 1, reason: '채팅 탭 첫 진입은 1회 조회돼야 한다');

        await tester.tap(find.text('[현대] 아반떼 0 · 2020년'));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull);
        expect(
          find.byType(AppBar),
          findsOneWidget,
          reason:
              '채팅 탭(브랜치) **안**의 방 목록에서 시작하는 push다 — '
              'chat_list_screen.dart의 rootNavigator: true가 빠지면 셸 AppBar 위에 방 '
              'AppBar가 겹쳐 2개가 된다',
        );
        expect(find.byType(NavigationBar), findsNothing);

        // 방을 닫고 돌아온다(review, spec-16-1 P2) — chat_list_screen.dart:107 근처의
        // `.then((_) => ref.invalidate(chatRoomsProvider))`가 없으면 여기서 재조회가 안
        // 일어나 fetchCount가 1에 멈춘다(읽지 않음 카운터·최신 메시지가 방을 나와도 영원히
        // 안 갱신되는 것과 같은 증상).
        expect(find.byType(BackButton), findsOneWidget);
        await tester.tap(find.byType(BackButton));
        await tester.pumpAndSettle();

        expect(
          fetchCount,
          2,
          reason:
              '방을 열었다 돌아오면 채팅방 목록이 다시 조회돼야 한다 — 탭 재진입 '
              '무효화(app_router.dart)만으로는 이 경로(같은 탭 안에서 방을 여닫는 것)를 '
              '못 잡는다',
        );
      });
    },
  );

  group('chatRoomsProvider 재조회 — 채팅 탭 재진입 시 autoDispose 계약을 명시 무효화로 대신한다', () {
    // review_loop_iteration 1 bug #3: '/chat' 브랜치가 IndexedStack으로 영구 마운트되면서
    // chatRoomsProvider(FutureProvider.autoDispose, "닫으면 캐시를 버려 재진입 시 최신을
    // 다시 읽는다")의 자연 dispose가 안 일어났다 — 실측: 재진입해도 조회 1회에 고정.
    // app_router.dart의 NavigationBar.onDestinationSelected가 탭 활성화 시
    // ref.invalidate(chatRoomsProvider)를 명시 호출하는지를 조회 횟수로 확인한다.
    testWidgets('채팅 탭을 한 번 본 뒤 홈으로 갔다가 돌아오면 조회가 다시 일어난다(2회)', (tester) async {
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            chatRoomsProvider.overrideWith((ref) async {
              fetchCount++;
              return const <ChatRoomSummary>[];
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();
      expect(fetchCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');

      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();

      expect(
        fetchCount,
        2,
        reason:
            '탭을 재방문했는데 1회에 멈춰 있으면 무효화가 안 걸린 것이다 — 새 문의·읽지 '
            '않음 카운터가 영원히 갱신 안 되는 실사용 버그와 같은 증상이다',
      );
    });
  });

  group('chatUnreadTotalProvider·chatUnreadByRoomProvider 재조회 — 채팅 탭 재진입 시 무효화(Story 16.4, §12.6)', () {
    // §12.6 Always: "다음 진입/로드 시점 기준"으로 배지가 줄어야 한다 — 방을 읽고 채팅 탭을
    // 나갔다 재진입하면 그 시점에 다시 조회돼야 한다는 뜻이다. app_router.dart의 tab_chat
    // onActivate가 chatRoomsProvider와 나란히 이 두 provider도 invalidate하는지 조회 횟수로 확인한다.
    //
    // 두 provider는 수명이 다르다(chatRoomsProvider와 대비해 주의할 점): chatUnreadTotalProvider는
    // non-autoDispose이고 하단 NavigationBar(셸 자체, `_ChatTabIcon`)가 매 프레임 watch하므로
    // **앱을 켜자마자(채팅 탭을 누르기 전에도)** 이미 1회 조회된다. 반면 chatUnreadByRoomProvider는
    // ChatListScreen(브랜치 콘텐츠) 안에서만 watch하므로 chatRoomsProvider와 같은 패턴 —
    // 채팅 탭을 처음 열 때 비로소 1회 조회된다.
    testWidgets('채팅 탭을 한 번 본 뒤 홈으로 갔다가 돌아오면 안읽음 배지 두 provider 모두 다시 조회된다', (
      tester,
    ) async {
      var totalFetchCount = 0;
      var byRoomFetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          chatUnreadDefaults: false, // 이 테스트 자신이 카운팅 override를 넣는다(중복 override 금지).
          extraOverrides: [
            _recentListings(const []),
            chatRoomsProvider.overrideWith((ref) async => const <ChatRoomSummary>[]),
            chatUnreadTotalProvider.overrideWith((ref) async {
              totalFetchCount++;
              return 0;
            }),
            chatUnreadByRoomProvider.overrideWith((ref) async {
              byRoomFetchCount++;
              return const <String, int>{};
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();
      expect(totalFetchCount, 1, reason: '내비 배지는 셸이 항상 그리므로 채팅 탭을 누르기 전에도 조회된다');
      expect(byRoomFetchCount, 0, reason: '방별 배지는 ChatListScreen 안에서만 watch하므로 아직 안 열림');

      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();
      expect(totalFetchCount, 2, reason: '탭 활성화 onActivate가 무효화해 다시 조회된다');
      expect(byRoomFetchCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');

      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_chat')));
      await tester.pumpAndSettle();

      expect(
        totalFetchCount,
        3,
        reason: '탭을 재방문했는데 안 늘었으면 무효화가 안 걸린 것이다 — 방금 읽은 방의 안읽음 '
            '감소가 내비 배지에 영원히 반영되지 않는 실사용 버그와 같은 증상이다',
      );
      expect(byRoomFetchCount, 2, reason: '목록 각 행의 방별 배지도 같은 이유로 재조회돼야 한다');
    });
  });

  group('_ChatTabIcon 안읽음 배지 — 실제 렌더된 숫자·99+ 캡·시맨틱스(spec-16-4 I/O 매트릭스, 코드리뷰 지적)', () {
    // 위 두 group은 provider *조회 횟수*만 세고, 배지가 실제로 무엇을 그리는지는 아무 테스트도
    // 확인하지 않았다(코드리뷰 지적) — chatUnreadTotalProvider를 구체적인 값으로 오버라이드해
    // app_router.dart의 `_ChatTabIcon`이 그 값을 실제로 렌더하는지 여기서 직접 본다.
    testWidgets('안읽음 7건 → 배지 숫자 "7"이 보이고, 시맨틱 라벨도 같은 건수를 담는다', (
      tester,
    ) async {
      // 기본적으로 위젯 테스트는 접근성 트리를 만들지 않는다 — 이 핸들이 살아있는 동안만
      // 실제로 만들어진다(wish_button_test.dart와 동일 패턴).
      final semanticsHandle = tester.ensureSemantics();
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          chatUnreadDefaults: false, // 이 테스트 자신이 구체값으로 override한다(중복 override 금지).
          extraOverrides: [
            _recentListings(const []),
            chatUnreadTotalProvider.overrideWith((ref) async => 7),
            chatUnreadByRoomProvider.overrideWith((ref) async => const <String, int>{}),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.descendant(of: find.byKey(const Key('tab_chat')), matching: find.text('7')),
        findsOneWidget,
        reason: '99 이하는 시각 배지에 실제 건수를 그대로 보여야 한다',
      );
      // NavigationDestination 자신의 탭 라벨("채팅")과 우리 배지 Semantics의 label이 상위
      // 시맨틱 노드로 병합돼("채팅\n채팅, 안읽음 메시지 7건" 형태) 정확히 일치 비교는 항상
      // 실패한다(실측) — RegExp로 부분일치를 확인한다(exact String 매처는 실측 결과와 다름).
      expect(
        find.bySemanticsLabel(RegExp('채팅, 안읽음 메시지 7건')),
        findsOneWidget,
        reason: '스크린리더 라벨도 같은 건수를 담아야 한다(ExcludeSemantics가 시각 텍스트만 감춘다)',
      );
      semanticsHandle.dispose();
    });

    testWidgets('안읽음 150건 → 시각 배지는 "99+"로 캡되지만 시맨틱 라벨은 실제 건수(150)를 담는다', (
      tester,
    ) async {
      final semanticsHandle = tester.ensureSemantics();
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          chatUnreadDefaults: false,
          extraOverrides: [
            _recentListings(const []),
            chatUnreadTotalProvider.overrideWith((ref) async => 150),
            chatUnreadByRoomProvider.overrideWith((ref) async => const <String, int>{}),
          ],
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.descendant(of: find.byKey(const Key('tab_chat')), matching: find.text('99+')),
        findsOneWidget,
        reason: '99 초과는 시각적으로 "99+"로 눌러야 한다',
      );
      expect(
        find.descendant(of: find.byKey(const Key('tab_chat')), matching: find.text('150')),
        findsNothing,
        reason: '시각 텍스트에 150이 그대로 노출되면 캡이 동작하지 않은 것이다',
      );
      expect(
        find.bySemanticsLabel(RegExp('채팅, 안읽음 메시지 150건')),
        findsOneWidget,
        reason: '스크린리더는 캡 없이 실제 건수(150)를 그대로 읽어야 한다',
      );
      semanticsHandle.dispose();
    });
  });

  group('recentListingsProvider 재조회 — 홈 탭 재진입 시 autoDispose 계약을 명시 무효화로 대신한다', () {
    // chatRoomsProvider와 똑같은 결함이었다(review, spec-16-1 P1) — '/home' 브랜치도
    // IndexedStack으로 영구 마운트돼 recentListingsProvider(FutureProvider.autoDispose)의
    // 자연 dispose가 안 일어난다. home_screen.dart의 퀵액션(.then((_) =>
    // ref.invalidate(...)))은 그 퀵액션으로 나갔다 돌아오는 경로만 잡는다 — 내차팔기
    // "탭"에서 매물을 등록하고 홈 "탭"으로 전환하는 경로(퀵액션이 아니라 하단 탭)는
    // 못 잡았다(실측: 조회 1회 고정). app_router.dart의 NavigationBar.onDestinationSelected가
    // 홈 탭 활성화 시 ref.invalidate(recentListingsProvider)를 명시 호출하는지를 조회
    // 횟수로 확인한다.
    testWidgets('홈 탭을 한 번 본 뒤 찜 탭으로 갔다가 돌아오면 조회가 다시 일어난다(2회)', (tester) async {
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            recentListingsProvider.overrideWith((ref) async {
              fetchCount++;
              return const <ListingCardData>[];
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();
      expect(fetchCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();

      expect(
        fetchCount,
        2,
        reason:
            '탭을 재방문했는데 1회에 멈춰 있으면 무효화가 안 걸린 것이다 — 내차팔기 '
            '탭에서 매물을 등록하고 홈으로 돌아와도 최근 매물이 등록 전 목록에 계속 '
            '고정되는 실사용 버그와 같은 증상이다',
      );
    });
  });

  group('wishlistProvider 재조회 — 찜 탭 재진입 시 autoDispose 계약을 명시 무효화로 대신한다', () {
    // 위 recentListings·chatRooms와 같은 원인·같은 계약(Story 16.3) — '/wishlist' 브랜치도
    // IndexedStack으로 영구 마운트돼 wishlistProvider(FutureProvider.autoDispose)의 자연
    // dispose가 안 일어난다. app_router.dart의 `_TabBranch.onActivate`가 찜 탭 활성화 시
    // ref.invalidate(wishlistProvider)를 명시 호출하는지를 조회 횟수로 확인한다 — 이게 없으면
    // 찜 목록에서 하트를 해제해도(다른 탭에 갔다와야만) 타일이 안 사라진다는 뜻이다.
    testWidgets('찜 탭을 한 번 본 뒤 홈 탭으로 갔다가 돌아오면 조회가 다시 일어난다(2회)', (tester) async {
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            wishlistProvider.overrideWith((ref) async {
              fetchCount++;
              return const [];
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();
      expect(fetchCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');

      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();

      expect(
        fetchCount,
        2,
        reason:
            '탭을 재방문했는데 1회에 멈춰 있으면 무효화가 안 걸린 것이다 — 찜을 해제해도 '
            '탭을 나갔다 들어오기 전까지 타일이 그대로 남는 실사용 버그와 같은 증상이다',
      );
    });
  });

  group('wishedListingIdsProvider 재조회 — 홈 탭 재활성화 시 명시 무효화를 실행한다(코드리뷰 지적 P8)', () {
    // app_router.dart의 tab_home `_TabBranch.onActivate`가 recentListingsProvider와 나란히
    // `ref.invalidate(wishedListingIdsProvider)`도 호출한다(_TabBranch.onActivate 문서 참조 —
    // wishedListingIdsProvider는 non-autoDispose라 한 번 조회가 실패하면 앱이 켜져 있는 동안
    // 하트가 계속 빈 채로 남는다). 그 줄을 지워도 스위트가 green이었다(코드리뷰 지적, 실측) —
    // 위 recentListingsProvider·wishlistProvider group과 같은 fetchCount 패턴으로 고정한다.
    testWidgets('홈 탭을 한 번 본 뒤 찜 탭으로 갔다가 돌아오면 조회가 다시 일어난다(2회)', (tester) async {
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            wishedListingIdsProvider.overrideWith((ref) async {
              fetchCount++;
              return const <String>{};
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();
      expect(fetchCount, 1,
          reason: '첫 진입은 HomeScreen이 카드 하트를 위해 watch하므로 1회 조회돼야 한다');

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();

      expect(
        fetchCount,
        2,
        reason:
            '탭을 재방문했는데 1회에 멈춰 있으면 무효화가 안 걸린 것이다 — 첫 조회가 실패해도 '
            '(빈 Set으로 조용히 삼킴) 하트를 한 번도 안 누르면 세션 내내 복구되지 않는 '
            '실사용 버그와 같은 증상이다',
      );
    });
  });

  group('sellControllerProvider 재조회 — 내차팔기 탭 활성화 시 잔여 상태를 지운다', () {
    // 위 두 형제(chatRooms·recentListings)와 같은 원인·같은 계약인데, 이 세 번째만
    // 어떤 테스트도 보지 않았다 — app_router.dart의 그 줄을 지워도 스위트가 전부 초록이었다
    // (뮤테이션 생존, 후속 리뷰 실측). 여기서 고정한다.
    testWidgets('내차팔기 탭을 다시 누르면 이전 화면이 남긴 editingId가 지워진다', (tester) async {
      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser(role: null)),
          authStateProvider.overrideWith(
            (ref) => const Stream<AuthState>.empty(),
          ),
          ..._chatUnreadDefaults(),
          _recentListings(const []),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: Consumer(
            builder: (context, ref, _) =>
                MaterialApp.router(routerConfig: ref.watch(appRouterProvider)),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 내차팔기 탭을 **먼저** 연다. 화면의 initState 도 진입 시 한 번 무효화하는데,
      // 그건 브랜치가 처음 마운트될 때 딱 한 번뿐이다 — 그걸 먼저 소진시켜야 이 검사가
      // 실제로 탭 활성화(onActivate)만 보게 된다(안 그러면 onActivate를 통째로 지워도
      // 초록으로 통과한다 — 실측 확인).
      await tester.tap(find.byKey(const Key('tab_sell')));
      await tester.pumpAndSettle();

      // 수정 화면을 한 번 거친 것과 같은 잔여 상태(브랜치 영구 마운트라 자연 소멸 안 됨).
      container
          .read(sellControllerProvider.notifier)
          .startEdit('listing-EDIT', const ListingFormInput());
      expect(container.read(sellControllerProvider).editingId, 'listing-EDIT');

      // 다른 탭에 들렀다가 내차팔기 탭으로 되돌아온다(브랜치는 이미 마운트돼 있어
      // initState 는 다시 안 돈다 — 여기서 지워지는 건 오직 onActivate 때문이다).
      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_sell')));
      await tester.pumpAndSettle();

      expect(
        container.read(sellControllerProvider).editingId,
        isNull,
        reason:
            '내차팔기 탭 활성화가 sellControllerProvider를 무효화하지 않으면 이전 화면의 '
            'editingId·성공/에러 배너가 등록 탭에 그대로 남는다',
      );
    });

    testWidgets('제출이 진행 중이면 탭을 다시 눌러도 무효화하지 않는다(중복 등록 방지)', (tester) async {
      final gate = Completer<void>();
      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser(role: null)),
          authStateProvider.overrideWith(
            (ref) => const Stream<AuthState>.empty(),
          ),
          ..._chatUnreadDefaults(),
          _recentListings(const []),
          listingsRepositoryProvider.overrideWithValue(_GatedRepo(gate)),
        ],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: Consumer(
            builder: (context, ref, _) =>
                MaterialApp.router(routerConfig: ref.watch(appRouterProvider)),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // 내차팔기 탭을 먼저 연다 — 화면이 provider 를 watch 해야 autoDispose 가 즉시
      // 회수하지 않는다(셸에서 실제로 벌어지는 상황과 동일: 탭 루트가 영구 마운트된다).
      await tester.tap(find.byKey(const Key('tab_sell')));
      await tester.pumpAndSettle();

      final notifier = container.read(sellControllerProvider.notifier);
      notifier.updateInput(_validSellInput);
      unawaited(notifier.submit(editingId: null, owner: 'tab-root'));
      await tester.pump();
      expect(
        container.read(sellControllerProvider).loading,
        isTrue,
        reason: '드라이빙 전제 확인 — 제출이 실제로 진행 중이어야 이 검사가 의미가 있다',
      );

      // 진행 중에 탭을 다시 누른다(홈에 들렀다 오는 것도 같은 경로다).
      await tester.tap(find.byKey(const Key('tab_home')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('tab_sell')));
      await tester.pumpAndSettle();

      expect(
        container.read(sellControllerProvider).loading,
        isTrue,
        reason:
            '진행 중인 제출을 무효화하면 새 컨트롤러의 loading이 false라 등록 버튼이 다시 '
            '눌린다 — 같은 매물이 두 번 INSERT되는 창이 열린다(실측 재현)',
      );

      gate.complete();
      await tester.pumpAndSettle();
    });
  });

  group('셸 크롬 — 탭별 AppBar 제목과 하단 라벨', () {
    // _kTabBranches는 "제목·라벨·부수효과가 인덱스 어긋남으로 흩어지지 않게" 하나로 모은
    // 자료구조인데, 정작 그 안의 제목·라벨을 단언하는 곳이 없었다(뮤테이션 생존: 제목을
    // 'XXBROKENXX'로 바꿔도 전부 초록). 탭을 다루는 다음 스토리(16.2·16.3)가 항목을
    // 재배열·복사할 때 조용히 어긋나는 것을 막는다.
    const expected = <String, List<String>>{
      'tab_home': ['중고차 직거래', '홈'],
      'tab_wishlist': ['찜한 매물', '찜'],
      'tab_chat': ['채팅', '채팅'],
      'tab_sell': ['매물 등록', '내차팔기'],
    };

    for (final entry in expected.entries) {
      testWidgets('${entry.key} — AppBar 제목 "${entry.value[0]}" · 라벨 "${entry.value[1]}"', (
        tester,
      ) async {
        await tester.pumpWidget(
          _harness(
            user: _fakeUser(role: null),
            extraOverrides: [
              _recentListings(const []),
              chatRoomsProvider.overrideWith(
                (ref) async => const <ChatRoomSummary>[],
              ),
            ],
          ),
        );
        await tester.pumpAndSettle();

        await tester.tap(find.byKey(Key(entry.key)));
        await tester.pumpAndSettle();

        expect(
          find.descendant(
            of: find.byType(AppBar),
            matching: find.text(entry.value[0]),
          ),
          findsOneWidget,
          reason: '탭 인덱스와 제목이 어긋나면 다른 탭의 제목이 뜬다',
        );
        expect(
          find.descendant(
            of: find.byKey(Key(entry.key)),
            matching: find.text(entry.value[1]),
          ),
          findsOneWidget,
          reason: '하단 내비 라벨도 같은 자료구조가 정한다',
        );
      });
    }
  });

  group('PopScope — 비홈 탭에서 시스템 back은 앱을 종료하지 않고 홈 탭으로 복귀한다', () {
    // review_loop_iteration 1 bug #4: 비홈 탭에서 시스템 back을 누르면 `handlePopRoute`가
    // false를 반환해(=아무도 못 막아) 안드로이드에서 앱이 그대로 종료됐다.
    testWidgets('찜 탭에서 시스템 back을 누르면 홈 탭으로 돌아오고 앱은 안 죽는다', (tester) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [_recentListings(const [])],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();
      expect(find.byType(WishlistScreen), findsOneWidget);

      // 시스템 back 제스처/버튼을 시뮬레이션한다 — 이 메서드가 PopScope가 등록한
      // popDisposition을 실제로 태운다(canPop==false면 핸들된 것으로 처리되고 앱까지는
      // 전파되지 않는다).
      final handled = await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();

      expect(
        handled,
        isTrue,
        reason: 'PopScope(canPop: false)가 back을 가로챘다는 뜻 — 앱 종료로 새지 않았다',
      );
      expect(
        find.byType(HomeScreen),
        findsOneWidget,
        reason:
            '비홈 탭에서 시스템 back → 홈 탭 복귀('
            '_bmad-output/planning-artifacts/ux-designs/'
            'ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md "Responsive & Platform" '
            '"네이티브 앱 구조 델타", nav-ia-rules §3 R5)',
      );
    });

    testWidgets('시스템 back으로 홈에 복귀할 때도 홈 탭의 재조회가 일어난다', (tester) async {
      // 탭을 옮기는 경로는 둘(하단 NavigationBar / 시스템 back)인데 예전엔 부수효과
      // (recentListingsProvider 무효화)가 NavigationBar 쪽에만 걸려 있었다 — 실측: 탭
      // 버튼으로 홈에 오면 조회 2회, back으로 오면 1회 고정. 그래서 내차팔기 탭에서 매물을
      // 등록하고 back으로 홈에 오면 최근 매물이 등록 전 목록 그대로였다.
      var fetchCount = 0;
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            recentListingsProvider.overrideWith((ref) async {
              fetchCount++;
              return const <ListingCardData>[];
            }),
          ],
        ),
      );
      await tester.pumpAndSettle();
      expect(fetchCount, 1);

      await tester.tap(find.byKey(const Key('tab_wishlist')));
      await tester.pumpAndSettle();

      final handled = await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();

      expect(handled, isTrue);
      expect(find.byType(HomeScreen), findsOneWidget);
      expect(
        fetchCount,
        2,
        reason:
            'back으로 홈에 왔을 때 재조회가 안 되면, 탭 전환 경로 두 개 중 한쪽만 '
            '부수효과를 태우고 있다는 뜻이다',
      );
    });

    testWidgets('홈 탭에서는 시스템 back이 PopScope에 가로막히지 않는다(실제 앱 종료 경로로 감)', (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [_recentListings(const [])],
        ),
      );
      await tester.pumpAndSettle();
      expect(find.byType(HomeScreen), findsOneWidget);

      final handled = await tester.binding.handlePopRoute();
      await tester.pumpAndSettle();

      // 홈은 canPop:true이므로 이 셸의 PopScope는 back을 가로막지 않는다 — 더 바깥에
      // pop할 라우트가 없어 시스템이 앱 종료를 진행한다(테스트 환경에서는 예외 없이
      // false로 돌아온다: 처리할 라우트가 더 없다는 뜻).
      expect(
        handled,
        isFalse,
        reason:
            '홈 탭에서 canPop이 막지 않으므로 더 이상 pop할 라우트가 없다는 신호가 '
            '와야 한다 — 여기까지 true가 나오면 홈에서도 계속 탭 0으로 붙잡고 있다는 뜻',
      );
    });
  });

  group('리액티브 redirect', () {
    testWidgets(
      '로그아웃하면 ref.listen(authStateProvider)이 redirect를 재평가해 /login에 닿는다',
      (tester) async {
        // 위 _harness는 authStateProvider를 빈(끝난) 스트림으로 고정 오버라이드하므로
        // 리액티브 경로 자체를 태우지 못한다(파일 헤더 "이 검사가 안 보는 것" 참조). 이
        // 테스트는 그 한계를 메운다 — 진짜 StreamController로 로그아웃 이벤트를 흘려보내
        // ref.listen(authStateProvider, ...) → refresh.notify() → GoRouter가 redirect를
        // 실제로 다시 평가하는 경로 그 자체를 확인한다(끝난 상태를 미리 만들어 두고
        // "당연히 /login이겠지"라고 스텁하지 않는다).
        final authEvents = StreamController<AuthState>.broadcast();
        addTearDown(authEvents.close);

        final container = ProviderContainer(
          overrides: [
            // currentUserProvider를 고정값이 아니라 이 provider를 watch하는 형태로 오버라이드해야
            // "로그아웃 시 user가 null이 된다"를 테스트 도중에 실제로 바꿀 수 있다.
            currentUserProvider.overrideWith(
              (ref) => ref.watch(_fakeUserProvider),
            ),
            authStateProvider.overrideWith((ref) => authEvents.stream),
            // AuthController.signOut()의 실제 구현은 전역 supabase.auth.signOut()을 호출한다.
            // 실제 로그아웃이 일으키는 두 가지 효과(① currentUser→null ② 인증 스트림에 새
            // 이벤트)를 흉내 내는 페이크로 바꿔치기한다 — 아래 _FakeAuthController.
            authControllerProvider.overrideWith(
              () => _FakeAuthController(authEvents),
            ),
            ..._chatUnreadDefaults(),
            _recentListings(const []),
          ],
        );
        addTearDown(container.dispose);
        container.read(_fakeUserProvider.notifier).state = _fakeUser(
          role: null,
        );

        await tester.pumpWidget(
          UncontrolledProviderScope(
            container: container,
            child: Consumer(
              builder: (context, ref, _) {
                final router = ref.watch(appRouterProvider);
                return MaterialApp.router(routerConfig: router);
              },
            ),
          ),
        );
        await tester.pumpAndSettle();
        expect(
          find.byType(HomeScreen),
          findsOneWidget,
          reason: '로그아웃 전엔 홈 셸이 보여야 이후 전환 확인이 의미가 있다',
        );

        await tester.tap(find.byKey(const Key('profile_avatar')));
        await tester.pumpAndSettle();
        await tester.tap(find.byKey(const Key('logout')));
        await tester.pumpAndSettle();

        expect(
          find.byKey(const Key('login_email')),
          findsOneWidget,
          reason:
              'currentUser만 null로 바꾸고 authEvents에 이벤트를 안 흘렸다면 '
              'refreshListenable이 몰라 redirect가 재평가되지 않고 여전히 홈 셸에 '
              '머물렀을 것이다 — 이 단언이 통과한다는 것은 ref.listen 브리지가 실제로 '
              '작동했다는 뜻이다(스텁이 아니라 리액티브 경로 자체를 태움)',
        );
      },
    );

    testWidgets('로그인하면 redirect의 isAuthRoute → /home 분기가 재평가돼 홈 셸에 닿는다', (
      tester,
    ) async {
      // 위 로그아웃 테스트의 역방향 — spec-16-1 Verification "채택 전 red 확인 #4"가
      // 지목한 정확히 그 분기(`redirect`의 `isAuthRoute → '/home'`)를 태운다. 그 줄을
      // `return null`로 바꿔도 위 로그아웃 테스트는 여전히 통과한다(로그아웃은 그 분기를
      // 안 거친다) — 이 테스트가 없으면 그 뮤테이션이 안 잡힌다(실측: 리뷰 세션이 101건
      // 스위트 전체로 확인).
      final authEvents = StreamController<AuthState>.broadcast();
      addTearDown(authEvents.close);

      final container = ProviderContainer(
        overrides: [
          currentUserProvider.overrideWith(
            (ref) => ref.watch(_fakeUserProvider),
          ),
          authStateProvider.overrideWith((ref) => authEvents.stream),
          ..._chatUnreadDefaults(),
          _recentListings(const []),
        ],
      );
      addTearDown(container.dispose);
      // 시작은 미인증 — /login에 머문다.
      container.read(_fakeUserProvider.notifier).state = null;

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: Consumer(
            builder: (context, ref, _) {
              final router = ref.watch(appRouterProvider);
              return MaterialApp.router(routerConfig: router);
            },
          ),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        find.byKey(const Key('login_email')),
        findsOneWidget,
        reason: '로그인 전엔 /login에 있어야 이후 전환 확인이 의미가 있다',
      );

      // 로그인 성공을 흉내 낸다 — currentUser를 채우고 인증 스트림에 signedIn을 흘린다.
      container.read(_fakeUserProvider.notifier).state = _fakeUser(role: null);
      authEvents.add(const AuthState(AuthChangeEvent.signedIn, null));
      await tester.pumpAndSettle();

      expect(
        find.byType(HomeScreen),
        findsOneWidget,
        reason:
            'currentUser가 채워지고 refreshListenable이 알림을 받으면 redirect가 '
            '재평가돼 인증 라우트(/login)에서 /home으로 밀려나야 한다',
      );
    });
  });

  group('로그아웃 실패 — 원본 예외 대신 고정 한국어 안내(review, spec-16-1 P6)', () {
    testWidgets('signOut()이 던지면 SnackBar에 고정 문구만 뜨고 원본 예외 문자열은 새지 않는다', (
      tester,
    ) async {
      await tester.pumpWidget(
        _harness(
          user: _fakeUser(role: null),
          extraOverrides: [
            _recentListings(const []),
            authControllerProvider.overrideWith(() => _FailingAuthController()),
          ],
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byKey(const Key('profile_avatar')));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const Key('logout')));
      await tester.pumpAndSettle();

      expect(
        find.text('로그아웃에 실패했습니다. 잠시 후 다시 시도해주세요.'),
        findsOneWidget,
        reason: '고정 한국어 문구가 SnackBar로 떠야 한다',
      );
      expect(
        find.textContaining('전용회선-오류-코드-999'),
        findsNothing,
        reason:
            '원본 예외 문자열이 화면에 그대로 새면 안 된다 — sell_controller.dart:147과 '
            '같은 규칙(원본은 로그에만, 화면엔 고정 한국어)',
      );
      // 로그아웃 실패는 currentUser를 안 바꾸므로 redirect가 계속 홈 셸에 둔다(로그인 화면으로
      // 밀려나지 않는다 — 실패했는데 화면이 바뀌면 그것대로 다른 혼란이다).
      expect(find.byType(HomeScreen), findsOneWidget);
    });
  });
}

/// 위 로그아웃/로그인 테스트 전용 — "지금 로그인된 사용자"를 테스트 도중에 바꿀 수 있게 하는
/// mutable 상태. `currentUserProvider.overrideWithValue(...)`(다른 테스트들이 쓰는 고정값)로는
/// 로그인/로그아웃 도중의 값 변화를 표현할 수 없어 별도로 둔다.
final _fakeUserProvider = StateProvider<User?>((ref) => null);

/// `AuthController.signOut()`의 실제 구현은 전역 `supabase.auth.signOut()`을 호출해
/// Supabase 초기화가 안 된 위젯 테스트에서는 쓸 수 없다. 로그아웃이 실제로 일으키는
/// 두 가지 효과 — ① `currentUserProvider`가 보는 값이 null이 된다 ② 인증 스트림
/// (`authStateProvider`)에 새 이벤트가 온다 — 만 흉내 낸다. 이 두 가지가 **함께** 있어야
/// `app_router.dart`의 `ref.listen(authStateProvider, ...)` → `refresh.notify()` →
/// redirect 재평가라는 실제 경로가 타진다.
class _FakeAuthController extends AuthController {
  _FakeAuthController(this._authEvents);

  final StreamController<AuthState> _authEvents;

  @override
  Future<void> signOut() async {
    state = const AsyncValue.loading();
    ref.read(_fakeUserProvider.notifier).state = null;
    _authEvents.add(const AuthState(AuthChangeEvent.signedOut, null));
    state = const AsyncValue.data(null);
  }
}

/// 로그아웃 실패 테스트 전용 — `AuthController.signOut()`의 실제 구현(state = error →
/// rethrow)을 그대로 흉내 낸다. 예외 메시지에 식별하기 쉬운 문자열을 박아, 화면에 그
/// 문자열이 그대로 새는지(P6이 금지하는 것)를 검사로 확인할 수 있게 한다.
class _FailingAuthController extends AuthController {
  @override
  Future<void> signOut() async {
    state = const AsyncValue.loading();
    final e = Exception('전용회선-오류-코드-999');
    state = AsyncValue.error(e, StackTrace.current);
    throw e;
  }
}
