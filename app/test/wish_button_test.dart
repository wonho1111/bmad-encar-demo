// WishButton 위젯테스트(Story 16.3) — 낙관적 토글(즉시 반영)·실패 롤백+SnackBar·연타 차단을
// I/O 매트릭스대로 확인한다(web WishButton.tsx의 handleClick/applyToggle 미러, 로그인 게이트
// 없이 — 앱은 라우터 전역이 이미 로그인 필수라 그 분기는 이식하지 않는다, spec-16-3 Boundaries).
import 'dart:async';

import 'package:app/features/wishlist/wish_button.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:app/features/wishlist/wishlist_repository.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 네트워크 없이 토글 결과를 제어하는 가짜 레포 — `onToggle`이 주어지면 그 Future를 기다리고
/// (연타 차단·낙관적 반영 타이밍 테스트용), 없으면 즉시 성공한다.
class _FakeWishlistRepository extends WishlistRepository {
  _FakeWishlistRepository({this.onToggle});

  final Future<void> Function(String listingId, bool wish)? onToggle;
  int callCount = 0;
  final calls = <bool>[];

  @override
  Future<void> toggle(String listingId, {required bool wish}) async {
    callCount++;
    calls.add(wish);
    if (onToggle != null) {
      await onToggle!(listingId, wish);
    }
  }
}

Future<void> _pump(
  WidgetTester tester,
  WishlistRepository repo, {
  bool initialWished = false,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: [wishlistRepositoryProvider.overrideWithValue(repo)],
      child: MaterialApp(
        home: Scaffold(
          body: WishButton(listingId: 'listing-1', initialWished: initialWished),
        ),
      ),
    ),
  );
}

void main() {
  // app_router_test.dart와 같은 이유 — WishlistRepository() 기본 생성자가 전역 `supabase`
  // 게터를 읽는다(client 미지정 시). 실제 네트워크 호출은 가짜 레포가 오버라이드하므로 없다.
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  testWidgets('미찜 상태에서 탭 → 즉시 하트가 채워진다(낙관적 반영)', (tester) async {
    final repo = _FakeWishlistRepository();
    await _pump(tester, repo, initialWished: false);

    expect(find.byIcon(Icons.favorite_border), findsOneWidget);
    await tester.tap(find.byType(WishButton));
    await tester.pump(); // 낙관적 반영은 서버 응답을 기다리지 않고 즉시 일어난다.

    expect(find.byIcon(Icons.favorite), findsOneWidget);
    await tester.pumpAndSettle();
    expect(repo.calls, [true]);
  });

  testWidgets('찜 상태에서 탭 → 즉시 하트가 비워지고 delete가 호출된다', (tester) async {
    final repo = _FakeWishlistRepository();
    await _pump(tester, repo, initialWished: true);

    await tester.tap(find.byType(WishButton));
    await tester.pump();

    expect(find.byIcon(Icons.favorite_border), findsOneWidget);
    await tester.pumpAndSettle();
    expect(repo.calls, [false]);
  });

  testWidgets('toggle 실패 → 아이콘이 직전 상태로 롤백되고 SnackBar가 뜬다', (tester) async {
    // Completer로 서버 응답을 미뤄야 "낙관적 반영(채워짐)"과 "롤백(비워짐)"이 서로 다른
    // 프레임으로 관측된다 — 즉시 실패하는 Future는 async/await 체인이 마이크로태스크만으로
    // 이어져 있어 pump() 한 번에 낙관적 반영과 롤백이 같은 프레임에 뭉쳐버린다(실측).
    final gate = Completer<void>();
    final repo = _FakeWishlistRepository(onToggle: (_, _) => gate.future);
    await _pump(tester, repo, initialWished: false);

    await tester.tap(find.byType(WishButton));
    await tester.pump(); // 낙관적 반영 — 서버 응답 전이라 채워진 상태.
    expect(find.byIcon(Icons.favorite), findsOneWidget);

    gate.completeError(Exception('network error'));
    await tester.pumpAndSettle(); // 실패가 반영될 때까지.

    expect(find.byIcon(Icons.favorite_border), findsOneWidget, reason: '롤백');
    expect(find.text('찜 처리에 실패했어요. 잠시 후 다시 시도해주세요.'), findsOneWidget);
  });

  testWidgets('진행 중 연타는 재요청을 만들지 않는다(pending 동안 disabled)', (tester) async {
    final gate = Completer<void>();
    final repo = _FakeWishlistRepository(onToggle: (_, _) => gate.future);
    await _pump(tester, repo, initialWished: false);

    await tester.tap(find.byType(WishButton));
    await tester.pump(); // 첫 탭 — pending 진입, 서버 응답 대기 중.
    expect(repo.callCount, 1);

    // pending 동안 다시 탭해도 onTap이 null이라 이벤트 자체가 안 붙는다.
    await tester.tap(find.byType(WishButton));
    await tester.pump();
    expect(repo.callCount, 1, reason: '연타가 두 번째 요청을 만들면 안 된다');

    gate.complete();
    await tester.pumpAndSettle();
    expect(repo.callCount, 1);
  });

  testWidgets(
      '토글 성공 시 wishedListingIdsProvider·wishlistProvider가 실제로 재조회된다(코드리뷰 지적 — '
      '두 invalidate 줄을 지워도 기존 스위트는 fake repo의 호출 로그와 로컬 아이콘만 보므로 green이었다)',
      (tester) async {
    final repo = _FakeWishlistRepository();
    // app_router_test.dart:769의 fetchCount 패턴과 동일 — invalidate가 실제로 재조회를
    // 일으키는지는 그 provider를 watch하는 소비자가 있어야 관측된다(watch하는 쪽이 없으면
    // invalidate는 다음에 읽을 때를 위한 표시일 뿐 즉시 재실행되지 않는다). 실제 화면(찜 목록·
    // 홈/검색/AI 카드)이 그 watcher 역할을 하므로, 여기선 최소 Consumer로 그 배선을 재현한다.
    var idsFetchCount = 0;
    var listFetchCount = 0;

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          wishlistRepositoryProvider.overrideWithValue(repo),
          wishedListingIdsProvider.overrideWith((ref) async {
            idsFetchCount++;
            return <String>{};
          }),
          wishlistProvider.overrideWith((ref) async {
            listFetchCount++;
            return <WishlistTile>[];
          }),
        ],
        child: MaterialApp(
          home: Scaffold(
            body: Column(
              children: [
                Consumer(builder: (context, ref, _) {
                  ref.watch(wishedListingIdsProvider);
                  ref.watch(wishlistProvider);
                  return const SizedBox.shrink();
                }),
                const WishButton(listingId: 'listing-1', initialWished: false),
              ],
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(idsFetchCount, 1, reason: '초기 watch로 1회 조회돼야 한다');
    expect(listFetchCount, 1, reason: '초기 watch로 1회 조회돼야 한다');

    await tester.tap(find.byType(WishButton));
    await tester.pumpAndSettle();

    expect(idsFetchCount, 2, reason: 'wishedListingIdsProvider가 토글 성공 시 invalidate돼야 한다');
    expect(listFetchCount, 2, reason: 'wishlistProvider도 함께 invalidate돼야 한다(P2 — 찜 목록 화면 자체 취소 반영)');
  });

  testWidgets(
      '탭 직후 화면을 떠나(위젯 unmount) 응답이 나중에 와도 두 provider가 재조회된다(코드리뷰 지적 P4 — '
      '예전엔 invalidate 앞의 `if (!mounted) return;`이 서버 쓰기가 성공했는데도 무효화를 통째로 건너뛰었다)',
      (tester) async {
    final gate = Completer<void>();
    final repo = _FakeWishlistRepository(onToggle: (_, _) => gate.future);
    var idsFetchCount = 0;
    var listFetchCount = 0;

    // showButton=false로 다시 pump하면 WishButton이 트리에서 사라져(unmount) 그 State가
    // dispose된다 — 바깥 ProviderScope/Consumer는 같은 자리에서 재사용되므로 fetchCount는
    // 계속 관측 가능하다.
    Widget harness({required bool showButton}) => ProviderScope(
          overrides: [
            wishlistRepositoryProvider.overrideWithValue(repo),
            wishedListingIdsProvider.overrideWith((ref) async {
              idsFetchCount++;
              return <String>{};
            }),
            wishlistProvider.overrideWith((ref) async {
              listFetchCount++;
              return <WishlistTile>[];
            }),
          ],
          child: MaterialApp(
            home: Scaffold(
              body: Column(
                children: [
                  Consumer(builder: (context, ref, _) {
                    ref.watch(wishedListingIdsProvider);
                    ref.watch(wishlistProvider);
                    return const SizedBox.shrink();
                  }),
                  if (showButton)
                    const WishButton(listingId: 'listing-1', initialWished: false),
                ],
              ),
            ),
          ),
        );

    await tester.pumpWidget(harness(showButton: true));
    await tester.pumpAndSettle();
    expect(idsFetchCount, 1, reason: '초기 watch로 1회 조회돼야 한다');
    expect(listFetchCount, 1, reason: '초기 watch로 1회 조회돼야 한다');

    await tester.tap(find.byType(WishButton));
    await tester.pump(); // pending 진입 — 서버 응답은 gate가 아직 안 풀려 대기 중.

    await tester.pumpWidget(harness(showButton: false)); // 화면 이탈 — WishButton dispose.
    await tester.pump();

    gate.complete(); // 서버 쓰기 성공 확정 — 이 시점엔 이미 WishButton이 없다.
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull, reason: 'dispose된 위젯의 ref를 건드리면 예외가 나야 정상 잡힌다');
    expect(idsFetchCount, 2, reason: 'unmount 이후에도 성공한 토글은 invalidate를 실행해야 한다(P4)');
    expect(listFetchCount, 2, reason: 'unmount 이후에도 성공한 토글은 invalidate를 실행해야 한다(P4)');
  });

  testWidgets(
      'listingId가 바뀌면(키 없이 같은 자리 재사용) _pending 중이어도 새 initialWished로 '
      '리셋된다(코드리뷰 지적 P5 — initialWished가 두 매물에서 우연히 같은 값이면 기존 동기화 '
      '조건(!_pending && initialWished 변경)만으로는 못 잡는다. ValueKey는 2차 방어일 뿐, '
      '위젯 자체가 안전해야 한다)',
      (tester) async {
    final gate = Completer<void>();
    final repo = _FakeWishlistRepository(onToggle: (_, _) => gate.future);

    Widget harness(String listingId, bool initialWished) => ProviderScope(
          overrides: [wishlistRepositoryProvider.overrideWithValue(repo)],
          child: MaterialApp(
            home: Scaffold(
              body: WishButton(listingId: listingId, initialWished: initialWished),
            ),
          ),
        );

    // listing-A는 미찜 상태로 시작 → 탭하면 낙관적으로 채워지지만, 서버 응답은 gate가
    // 막아 pending 상태로 묶어둔다.
    await tester.pumpWidget(harness('listing-A', false));
    await tester.tap(find.byType(WishButton));
    await tester.pump();
    expect(find.byIcon(Icons.favorite), findsOneWidget, reason: '낙관적 반영으로 채워진 상태');

    // key 없이 같은 위치에 다른 listingId(listing-B, initialWished도 마찬가지로 false)로
    // 재빌드 — Flutter가 같은 State를 재사용한다(didUpdateWidget 경로). listing-A의 toggle은
    // 아직 pending이라 응답이 안 왔고, initialWished 값 자체는 두 매물이 똑같이 false다.
    await tester.pumpWidget(harness('listing-B', false));
    await tester.pump();

    expect(find.byIcon(Icons.favorite_border), findsOneWidget,
        reason: 'listingId가 바뀌었는데 이전 매물(listing-A)의 pending 낙관적 상태가 '
            '새 매물(listing-B)에 남으면 안 된다(P5)');

    gate.complete(); // 정리 — pending Future를 매달아 두지 않는다.
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('히트영역이 44×44다(코드리뷰 지적 P13 — 주석에 "사실"로만 적혀 있던 값을 실측한다)',
      (tester) async {
    await _pump(tester, _FakeWishlistRepository());

    expect(
      tester.getSize(find.byKey(const Key('wish_button'))),
      const Size(kWishButtonSize, kWishButtonSize),
    );
  });

  testWidgets(
      'Semantics — 라벨이 찜하기/찜 취소로 전환되고, pending 동안 버튼이 비활성으로 알려진다'
      '(코드리뷰 지적 P13)', (tester) async {
    // 기본적으로 위젯 테스트는 접근성 트리를 만들지 않는다(성능) — 이 핸들이 살아있는 동안만
    // 실제로 만들어진다. addTearDown이 아니라 테스트 끝에서 직접 dispose한다 — 위젯 테스트의
    // 종료 검증(_endOfTestVerifications)이 addTearDown 콜백보다 먼저 돌아, addTearDown에
    // 맡기면 "핸들이 아직 살아있다"는 프레임워크 자체 예외가 난다(실측).
    final semanticsHandle = tester.ensureSemantics();

    final gate = Completer<void>();
    final repo = _FakeWishlistRepository(onToggle: (_, _) => gate.future);
    await _pump(tester, repo, initialWished: false);

    expect(
      tester.getSemantics(find.byKey(const Key('wish_button'))),
      matchesSemantics(
        label: '찜하기',
        isButton: true,
        hasEnabledState: true,
        isEnabled: true,
        hasToggledState: true,
        isFocusable: true,
        hasTapAction: true,
        hasFocusAction: true,
      ),
    );

    await tester.tap(find.byType(WishButton));
    await tester.pump(); // 낙관적 반영 + pending 진입 — 서버 응답은 gate가 막아 대기 중.

    expect(
      tester.getSemantics(find.byKey(const Key('wish_button'))),
      matchesSemantics(
        label: '찜 취소',
        isButton: true,
        hasEnabledState: true,
        isEnabled: false, // pending — onTap이 null이라 disabled로 알려야 한다.
        hasToggledState: true,
        isToggled: true,
        isFocusable: true,
        hasFocusAction: true,
        // hasTapAction: false(기본값) — onTap이 null이면 tap 액션 자체가 안 붙는다.
      ),
      reason: 'pending 동안엔 onTap이 null이라 스크린리더에도 비활성으로 알려야 한다',
    );

    gate.complete();
    await tester.pumpAndSettle();

    expect(
      tester.getSemantics(find.byKey(const Key('wish_button'))),
      matchesSemantics(
        label: '찜 취소',
        isButton: true,
        hasEnabledState: true,
        isEnabled: true,
        hasToggledState: true,
        isToggled: true,
        isFocusable: true,
        hasTapAction: true,
        hasFocusAction: true,
      ),
      reason: '응답이 오면 다시 활성으로 돌아와야 한다',
    );

    semanticsHandle.dispose();
  });
}
