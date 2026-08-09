// SellScreen 공유 컨트롤러 누수 회귀 방지 — spec-16-1 review P3.
//
// sellControllerProvider(NotifierProvider.autoDispose)는 하단 4탭 셸의 '/sell' 브랜치
// 루트(등록 모드, 영구 마운트)와 rootNavigator로 push되는 수정 화면이 같은 인스턴스를
// 공유한다(셸이 브랜치를 IndexedStack으로 영구 마운트해 autoDispose 수명이 무력화된다 —
// sell_controller_test.dart가 이미 다루는 것과 같은 원인). 그 결과 한쪽 화면의
// success/error가 다른 쪽 화면에 새는 사고가 있었다:
//   sell_screen.dart의 post-frame 콜백이 build() 시점에 캡처한 `sell`을 그대로 쓰고,
//   `isEdit`(이 화면의 모드)만 보고 성공을 자기 것으로 오인해 — 등록 탭에 남아있던
//   미저장 초안을, 다른(수정) 화면의 성공적인 제출 하나로 지워버렸다.
//
// 이 회귀는 sell_controller_test.dart(컨트롤러만 구동)로는 못 잡는다 — 버그가 화면의
// post-frame 콜백 로직 자체에 있어서, 화면을 실제로 마운트해야 재현된다.
//
// ⚠️ **위젯 테스트에서 SupabaseClient를 직접 만들지 않는다.** `ListingsRepository`의
// 생성자가 `client ?? supabase`라 인스턴스가 필요해 보이지만, 테스트마다 실제
// `SupabaseClient`를 만들고 `addTearDown(client.dispose)`로 정리하면 **teardown에서
// 영영 끝나지 않는다** — `dispose()`가 realtime 종료를 기다리는데 `testWidgets`의 가짜
// 시계에서는 그 대기가 진행되지 않는다(실측: 테스트 본문 마지막 줄까지 다 통과한 뒤
// teardown에서 멈춰 10분 타임아웃으로 스위트가 죽었다). 그래서 app_router_test.dart와
// 같은 방식으로 파일당 한 번 전역 초기화만 하고(네트워크 호출 없음), 가짜 레포는 그
// 전역 클라이언트를 물려받되 두 쓰기 메서드를 모두 오버라이드해 실제로 쓰지 않는다.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/listing_form.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/sell_controller.dart';
import 'package:app/features/listings/sell_screen.dart';

/// 쓰기 두 경로를 다 가로채는 가짜 레포 — 실제 네트워크로 나가지 않는다.
/// `gate`를 주면 그 Completer가 끝날 때까지 쓰기가 매달려 "제출 진행 중"을 만들 수 있다.
class _RecordingRepo extends ListingsRepository {
  _RecordingRepo({this.gate});

  final Completer<void>? gate;

  @override
  Future<String> createListing(
    Map<String, dynamic> payload, {
    required String sellerId,
  }) async {
    if (gate != null) await gate!.future;
    return 'recorded-listing-id';
  }

  @override
  Future<int> updateListing(String id, Map<String, dynamic> payload) async {
    if (gate != null) await gate!.future;
    return 1; // 항상 성공(1행 영향) — 이 테스트는 성공 경로의 부작용만 본다.
  }
}

const _validInput = ListingFormInput(
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

User _fakeUser() => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'seller@test.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

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

  testWidgets('내차팔기 탭(등록 모드)에 남은 초안은 무관한 수정 제출 성공에도 지워지지 않는다', (
    tester,
  ) async {
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(_RecordingRepo()),
        currentUserProvider.overrideWithValue(_fakeUser()),
      ],
    );
    addTearDown(container.dispose);

    // 하단 셸의 '/sell' 브랜치 루트와 동일한 조건 — 등록 모드(editDetail 없음), showAppBar:false.
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SellScreen(showAppBar: false)),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('sell_model')), '내가 쓰던 초안');
    await tester.pump();
    expect(
      find.text('내가 쓰던 초안'),
      findsOneWidget,
      reason: '드라이빙 전제 확인 — 입력이 실제로 반영됐는지부터 본다',
    );

    // 다른 화면(수정 화면)이 같은 notifier로 무관한 수정 제출에 성공했다고 흉내낸다 —
    // 이 화면(SellScreen)은 이 submit을 호출하지 않았다(editingId도 다르다).
    final notifier = container.read(sellControllerProvider.notifier);
    notifier.updateInput(_validInput);
    await notifier.submit(editingId: 'listing-A');
    await tester.pumpAndSettle();

    expect(
      find.text('내가 쓰던 초안'),
      findsOneWidget,
      reason:
          '등록 탭의 초안이 남의(다른 editingId) 수정 성공 때문에 사라지면 회귀다 — '
          'sell_screen.dart의 post-frame 콜백이 editingId로 "내 성공인지" 확인해야 한다',
    );
    expect(
      find.text('매물 정보가 수정되었습니다.'),
      findsNothing,
      reason: '등록 탭은 자신이 시작하지 않은 수정 성공 배너를 보여줄 이유도 없다',
    );
  });

  testWidgets('내차팔기 탭의 초안은 **owner가 다른** 제출의 등록 성공에도 지워지지 않는다', (tester) async {
    // 위 테스트는 editingId가 다른(수정 vs 등록) 경우만 봤다. 이 테스트가 원래 지키던
    // 시나리오는 등록 모드 화면이 동시에 **둘** 뜨는 경우였다 — '/sell' 탭 루트와 옛 홈
    // 퀵액션(go_sell)이 push 하던 화면, 둘 다 editingId==null. go_sell은 spec-16-8에서
    // 제거돼 그 조합은 지금 재현되지 않는다(sell_controller.dart의 owner 필드 주석과 같은
    // 사정, 후속 코드리뷰 spec-16-8 2차 리뷰 P8). 지금 sellControllerProvider를 실제로
    // 동시에 공유하는 쌍은 '/sell' 탭 루트(등록, editingId=null)와
    // my_listings_screen.dart의 "수정" 버튼이 여는 수정 화면(editingId=실제 매물 id, 위
    // 테스트가 이미 다룸)이다. 이 테스트는 그 판정이 editingId가 우연히 갈리는 데 기대지
    // 않고 owner 필드로 이뤄진다는 것 자체를 검사한다 — owner만 다르고 editingId는 똑같이
    // null인 상황을 직접 만들어 확인한다(실측 재현 — 이 검사가 그 회귀를 고정한다).
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(_RecordingRepo()),
        currentUserProvider.overrideWithValue(_fakeUser()),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SellScreen(showAppBar: false)),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(find.byKey(const Key('sell_model')), '내가 쓰던 초안');
    await tester.pump();
    expect(find.text('내가 쓰던 초안'), findsOneWidget);

    // owner가 다른 화면이 등록에 성공한 상황(editingId는 이 화면과 똑같이 null, owner만 다르다).
    final notifier = container.read(sellControllerProvider.notifier);
    notifier.updateInput(_validInput);
    await notifier.submit(editingId: null, owner: Object());
    await tester.pumpAndSettle();

    expect(
      find.text('내가 쓰던 초안'),
      findsOneWidget,
      reason: '남의 등록 성공이 내 초안을 지우면 회귀다 — owner로 화면 인스턴스를 구분해야 한다',
    );
    expect(
      find.text('매물이 등록되었습니다. 구매자에게 바로 노출됩니다.'),
      findsNothing,
      reason: '내가 시작하지 않은 등록의 성공 배너가 이 화면에 뜨면 안 된다',
    );
  });

  testWidgets('남의 제출이 진행 중이어도 내 등록 버튼은 살아 있다', (tester) async {
    // loading 은 공유 상태라 owner 로 거르지 않으면 남의 제출이 내 버튼을 "등록 중…"으로
    // 잠근다. 게다가 SellController.submit()의 `if (state.loading) return` 때문에 눌러도
    // 아무 일이 일어나지 않아 "죽은 버튼"으로 보인다(실측 재현).
    final gate = Completer<void>();
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(_RecordingRepo(gate: gate)),
        currentUserProvider.overrideWithValue(_fakeUser()),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SellScreen(showAppBar: false)),
      ),
    );
    await tester.pumpAndSettle();

    final notifier = container.read(sellControllerProvider.notifier);
    notifier.updateInput(_validInput);
    unawaited(notifier.submit(editingId: 'listing-A', owner: Object()));
    await tester.pump();
    expect(container.read(sellControllerProvider).loading, isTrue);

    final button = tester.widget<FilledButton>(
      find.byKey(const Key('sell_submit')),
    );
    expect(
      button.onPressed,
      isNotNull,
      reason: '남의 제출이 도는 동안 내 등록 버튼이 잠기면 회귀다',
    );
    expect(find.text('등록 중…'), findsNothing);

    gate.complete();
    await tester.pumpAndSettle();
  });

  testWidgets('내가 시작한 검증 실패는 이 화면에 에러로 뜬다(owner 게이트의 긍정 방향)', (tester) async {
    // 위 두 검사는 전부 "남의 결과가 안 보인다"(부정 방향)만 본다. 그것만 있으면 owner 판정을
    // 통째로 false 로 만들어도 스위트가 초록이다 — 그러면 사용자는 등록 버튼을 눌러도
    // 아무 메시지도 못 보는 죽은 폼을 만나게 된다. 긍정 방향을 함께 고정한다.
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(_RecordingRepo()),
        currentUserProvider.overrideWithValue(_fakeUser()),
      ],
    );
    addTearDown(container.dispose);

    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SellScreen(showAppBar: false)),
      ),
    );
    await tester.pumpAndSettle();

    // 빈 폼으로 제출 → 클라이언트 검증 실패(쓰기 없음).
    // 폼이 길어 버튼이 뷰포트 밖에 있다 — 먼저 보이게 스크롤하지 않으면 탭이 빗나간다.
    await tester.ensureVisible(find.byKey(const Key('sell_submit')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('sell_submit')));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('sell_error')),
      findsOneWidget,
      reason: '내가 누른 제출의 실패 메시지는 반드시 이 화면에 보여야 한다',
    );
  });
}
