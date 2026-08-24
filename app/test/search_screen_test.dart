// SearchScreen 배선 테스트(Story 16.3 코드리뷰 지적 #8) — `listing_trust_widgets_test.dart`·
// `wish_button_test.dart`는 단독 위젯만 pump해서 본다. 이 파일은 실제 화면 파이프라인
// (검색 결과 목록 → wishedListingIdsProvider → ListingCard의 `wished` prop → WishButton
// 아이콘)이 실제로 이어지는지, 세 진입점(홈·검색·AI) 중 검색 화면을 대표로 확인한다.
import 'dart:async';

import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_filters.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/search_screen.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// 네트워크 없이 고정된 검색 결과를 돌려주는 가짜 레포 — SearchController가 진입 시 자동으로
/// 부르는 초기 조회(빈 필터)에 응답한다.
class _FakeListingsRepository extends ListingsRepository {
  _FakeListingsRepository(this.listings);
  final List<ListingCardData> listings;

  @override
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async => listings;
}

/// 어떤 필터로 몇 번 조회됐는지 기록하는 가짜 레포(spec-16-8 Code Map — initialBodyType/
/// initialFuel 테스트용). 필터 유무로 다른 고정 결과를 돌려준다.
class _RecordingFakeRepository extends ListingsRepository {
  _RecordingFakeRepository({required this.filteredResult, required this.emptyResult});

  final List<ListingCardData> filteredResult;
  final List<ListingCardData> emptyResult;
  final calls = <ResolvedFilters>[];

  @override
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async {
    calls.add(f);
    final hasFilter = f.bodyType != null || f.fuel != null;
    return hasFilter ? filteredResult : emptyResult;
  }
}

/// "필터 진입 경합"(spec-16-8 Design Notes) 재현용 가짜 레포 — 빈 필터 조회와 필터 조회를
/// 각각 별도 Completer로 붙잡아 뒀다가, 테스트가 원하는 순서로 풀어준다(응답 도착 순서를
/// 테스트가 직접 통제).
class _RaceFakeRepository extends ListingsRepository {
  _RaceFakeRepository({required this.filteredResult, required this.emptyResult});

  final List<ListingCardData> filteredResult;
  final List<ListingCardData> emptyResult;
  final emptyGate = Completer<void>();
  final filteredGate = Completer<void>();

  @override
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async {
    final hasFilter = f.bodyType != null || f.fuel != null;
    if (hasFilter) {
      await filteredGate.future;
      return filteredResult;
    }
    await emptyGate.future;
    return emptyResult;
  }
}

/// 스테일 **에러** 응답 재현용 가짜 레포(spec-16-8 Review Triage Log #5) — `_RaceFakeRepository`는
/// 스테일 **성공** 응답만 재현하고(위 테스트), 에러 분기의 requestId 스테일 방어는 어떤 테스트도
/// 거치지 않았다(verification-gap 발견). 첫 호출(= 자동 초기조회, requestId=1)을 게이트로 잡아
/// 뒀다가 나중에 실패(throw)로 풀고, 두 번째 호출(명시적 search(), requestId=2)은 즉시 성공으로
/// 돌려준다 — "이미 최신 성공 데이터가 반영된 뒤, 더 오래된 요청이 뒤늦게 에러로 도착"하는 순서를
/// 결정적으로 만든다.
class _StaleErrorRaceRepository extends ListingsRepository {
  final firstCallGate = Completer<void>();
  int callCount = 0;

  @override
  Future<List<ListingCardData>> fetchListings(ResolvedFilters f) async {
    callCount++;
    if (callCount == 1) {
      await firstCallGate.future;
      throw Exception('stale-error');
    }
    return const [
      ListingCardData(
        id: 'newer-1',
        manufacturer: '현대',
        model: '쏘나타',
        year: 2023,
        price: 25000000,
        mileage: 5000,
        region: '서울',
      ),
    ];
  }
}

void main() {
  // app_router_test.dart·wish_button_test.dart와 같은 이유 — ListingsRepository()의 기본
  // 생성자(client 미지정 시)가 전역 `supabase` 게터를 읽는다. 실제 네트워크 호출은 위 가짜
  // 레포가 오버라이드하므로 없다.
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  testWidgets(
      '검색 결과 카드는 wishedListingIdsProvider 값을 실제로 반영한다(찜한 매물만 채워진 하트)',
      (tester) async {
    const wishedListing = ListingCardData(
      id: 'wished-1',
      manufacturer: '현대',
      model: '아반떼',
      year: 2021,
      price: 18000000,
      mileage: 20000,
      region: '서울',
    );
    const otherListing = ListingCardData(
      id: 'other-1',
      manufacturer: '기아',
      model: 'K5',
      year: 2020,
      price: 20000000,
      mileage: 30000,
      region: '부산',
    );

    // 카드 하나(사진 5:3 + 정보)가 기본 테스트 뷰포트(800×600)보다 크므로, 기본 크기로는
    // 두 번째 카드가 SliverList 캐시 범위 밖이라 안 만들어진다(listing_detail_screen_test.dart의
    // 스크롤 이슈와 동일 원인). 스크롤 대신 뷰포트를 넉넉히 키워 두 카드가 동시에 빌드되게
    // 한다 — 찜 안 한 카드(빈 하트)와 찜한 카드(채운 하트)를 한 화면에서 같이 비교해야 하므로
    // (스크롤하면 둘 중 하나가 화면 밖으로 밀려 같은 문제가 재현된다).
    tester.view.physicalSize = const Size(800, 2400);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(
            _FakeListingsRepository([wishedListing, otherListing]),
          ),
          // 실제 카드 진입점(home/search/ai)이 전부 공유하는 단일 provider — 여기만
          // 오버라이드해도 화면이 그 값을 정말로 ListingCard.wished까지 실어 나르는지 본다.
          wishedListingIdsProvider.overrideWith((ref) async => {'wished-1'}),
        ],
        child: const MaterialApp(home: SearchScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('[현대] 아반떼 · 2021년'), findsOneWidget);
    expect(find.text('[기아] K5 · 2020년'), findsOneWidget);
    expect(
      find.byIcon(Icons.favorite),
      findsOneWidget,
      reason: '검색 화면 실제 파이프라인을 통해 찜한 매물(wished-1) 카드만 채워진 하트여야 한다',
    );
    expect(
      find.byIcon(Icons.favorite_border),
      findsOneWidget,
      reason: '찜 안 한 매물(other-1) 카드는 빈 하트여야 한다',
    );
  });

  // spec-16-8 AC2 — 차종 칩의 목적지 계약: initialBodyType/initialFuel이 있으면 진입 즉시
  // 그 필터로 조회한다(수동 검색 버튼 없이).
  testWidgets(
      'initialBodyType가 있으면 진입 즉시 그 필터로 조회한다(수동 검색 버튼 없이)',
      (tester) async {
    final fake = _RecordingFakeRepository(
      filteredResult: const [
        ListingCardData(
          id: 'suv-1',
          manufacturer: '기아',
          model: '스포티지',
          year: 2022,
          price: 28000000,
          mileage: 15000,
          region: '서울',
        ),
      ],
      emptyResult: const [],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(fake),
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
        ],
        child: const MaterialApp(home: SearchScreen(initialBodyType: 'SUV')),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      fake.calls.any((f) => f.bodyType == 'SUV'),
      isTrue,
      reason: '진입 즉시 body_type=SUV로 조회했어야 한다',
    );
    expect(find.text('[기아] 스포티지 · 2022년'), findsOneWidget,
        reason: '필터 결과가 화면에 보여야 한다(수동 검색 버튼을 누르지 않아도)');
  });

  // spec-16-8 Design Notes "필터 진입 경합" — searchControllerProvider는 앱 전역 싱글턴이라
  // 이번 세션 첫 진입 시 provider의 build()가 빈 필터 초기조회를 자동으로 예약한다. 차종 칩
  // 탭으로 이 provider를 처음 읽으면 그 자동 조회와 겹치는데, **응답이 어떤 순서로 와도**
  // 최종 화면은 필터 결과를 보여줘야 한다(I/O 매트릭스). 여기서는 "빈 필터 응답이 필터
  // 응답보다 늦게 도착"하는 쪽을 재현한다 — 이게 이 방어가 없으면 실제로 깨지는 순서다.
  testWidgets(
      '차종 칩으로 첫 진입 + 빈 필터 초기조회 응답이 필터 조회 응답보다 늦게 와도 '
      '최종 화면은 필터 결과를 보여준다(필터 진입 경합)', (tester) async {
    final fake = _RaceFakeRepository(
      filteredResult: const [
        ListingCardData(
          id: 'suv-1',
          manufacturer: '기아',
          model: '스포티지',
          year: 2022,
          price: 28000000,
          mileage: 15000,
          region: '서울',
        ),
      ],
      emptyResult: const [
        ListingCardData(
          id: 'k5-1',
          manufacturer: '기아',
          model: 'K5',
          year: 2020,
          price: 20000000,
          mileage: 30000,
          region: '부산',
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(fake),
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
        ],
        child: const MaterialApp(home: SearchScreen(initialBodyType: 'SUV')),
      ),
    );
    await tester.pump();

    // 필터 조회 응답이 먼저 도착.
    fake.filteredGate.complete();
    await tester.pump();
    await tester.pump();

    // 빈 필터 초기조회 응답이 뒤늦게 도착 — 이게 방금 반영된 필터 결과를 덮어쓰면 안 된다.
    fake.emptyGate.complete();
    await tester.pump();
    await tester.pump();

    expect(find.text('[기아] 스포티지 · 2022년'), findsOneWidget,
        reason: '늦게 도착한 빈 필터 응답이 필터 결과를 덮어쓰면 안 된다');
    expect(find.text('[기아] K5 · 2020년'), findsNothing,
        reason: '빈 필터 결과가 화면에 남아있으면 안 된다');
  });

  // spec-16-8 Review Triage Log #5 — SearchController.search()의 requestId 스테일 응답
  // 방어는 성공 분기·에러 분기 둘 다에 있다. 위 "필터 진입 경합" 테스트는 성공 쪽만 태운다 —
  // 여기서는 provider를 직접 구동해 에러 쪽 방어를 확인한다(위젯 없이도 이 로직 자체는
  // SearchController 단위로 검증 가능하므로, SearchScreen을 pump할 필요가 없다).
  test(
      '스테일 에러 응답 — 더 오래된 요청이 뒤늦게 에러로 완료돼도 이미 반영된 최신 성공 '
      '데이터를 덮어쓰지 않는다', () async {
    final repo = _StaleErrorRaceRepository();
    final container = ProviderContainer(
      overrides: [listingsRepositoryProvider.overrideWithValue(repo)],
    );
    addTearDown(container.dispose);

    // 1) provider를 처음 읽으면 build()가 빈 필터 자동 초기조회를 Future.microtask로
    //    예약한다 — 그게 requestId=1(더 오래된 요청)이 되도록, 그 마이크로태스크가 실제로
    //    시작해 firstCallGate에 걸릴 때까지 한 번 플러시한다.
    final notifier = container.read(searchControllerProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    expect(repo.callCount, 1,
        reason: '자동 초기조회가 requestId=1로 이미 시작해 게이트에 걸려 있어야 한다');

    // 2) 명시적 search() 호출이 requestId=2(더 최신 요청) — 게이트가 없어 즉시 성공으로 끝난다.
    await notifier.search();
    final afterNewer = container.read(searchControllerProvider).results;
    expect(
      afterNewer.value?.map((l) => l.id).toList(),
      ['newer-1'],
      reason: '최신 요청(requestId=2)의 성공 데이터가 먼저 반영돼야 이후 비교가 의미 있다',
    );

    // 3) 이제 더 오래된 요청(requestId=1)을 에러로 풀어준다 — SearchController.search()의
    //    catch 분기 stale 가드(requestId != _requestId → return)가 실제로 이 상태 갱신을
    //    막는지 본다.
    repo.firstCallGate.complete();
    await Future<void>.delayed(Duration.zero);

    final results = container.read(searchControllerProvider).results;
    expect(
      results.hasError,
      isFalse,
      reason: '더 오래된 요청의 에러가 이미 반영된 최신 성공 데이터를 덮어쓰면 안 된다',
    );
    expect(
      results.value?.map((l) => l.id).toList(),
      ['newer-1'],
      reason: '최신 성공 데이터가 그대로 남아 있어야 한다',
    );
  });

  // 후속 코드리뷰(spec-16-8 2차 리뷰) P1 — "전체" 칩(둘 다 null)도 initState의 리셋 경로를
  // 타야 한다. searchControllerProvider는 앱 전역 싱글턴이라, 같은 컨트롤러를 그대로 둔 채
  // SUV 칩 → "전체" 칩 순서로 재진입하는 실제 경로를 재현한다(같은 ProviderContainer 위에서
  // SearchScreen을 두 번 pump — 라우팅으로 화면이 바뀌면 실제로 새 State가 만들어지는 것과 동일).
  testWidgets(
      '"전체" 칩(둘 다 null) 진입은 컨트롤러가 이미 SUV 필터·결과를 들고 있어도 무필터로 리셋한다',
      (tester) async {
    final fake = _RecordingFakeRepository(
      filteredResult: const [
        ListingCardData(
          id: 'suv-1',
          manufacturer: '기아',
          model: '스포티지',
          year: 2022,
          price: 28000000,
          mileage: 15000,
          region: '서울',
        ),
      ],
      emptyResult: const [
        ListingCardData(
          id: 'any-1',
          manufacturer: '현대',
          model: '쏘나타',
          year: 2021,
          price: 22000000,
          mileage: 10000,
          region: '부산',
        ),
      ],
    );
    final container = ProviderContainer(
      overrides: [
        listingsRepositoryProvider.overrideWithValue(fake),
        wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
      ],
    );
    addTearDown(container.dispose);

    // 1) SUV 칩으로 먼저 진입 — 컨트롤러가 SUV 필터·결과를 들고 있는 상태를 만든다.
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(
          home: SearchScreen(key: Key('search_suv'), initialBodyType: 'SUV'),
        ),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('[기아] 스포티지 · 2022년'), findsOneWidget);

    // 2) 뒤로가기 후 "전체" 칩으로 재진입 — 같은 컨트롤러 위에 **새** SearchScreen 인스턴스를
    //    마운트한다(다른 Key라 Flutter가 기존 State를 재사용하지 않고 dispose+새 initState를
    //    돈다 — 실제 라우팅에서 SUV 칩 push → pop → "전체" 칩 push가 매번 별도 Route/State를
    //    만드는 것과 동일한 초기화 조건).
    await tester.pumpWidget(
      UncontrolledProviderScope(
        container: container,
        child: const MaterialApp(home: SearchScreen(key: Key('search_all'))),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      fake.calls.last.bodyType,
      isNull,
      reason: '"전체" 진입은 컨트롤러 입력을 무필터로 리셋해야 한다',
    );
    expect(
      fake.calls.last.fuel,
      isNull,
      reason: '"전체" 진입은 fuel도 무필터로 리셋해야 한다',
    );
    expect(find.text('[현대] 쏘나타 · 2021년'), findsOneWidget,
        reason: '"전체" 라벨 아래 무필터 결과가 보여야 한다');
    expect(find.text('[기아] 스포티지 · 2022년'), findsNothing,
        reason: '이전 SUV 필터 결과가 "전체" 라벨 아래 남아있으면 AC2 위반이다');
  });

  // spec-16-8 Code Map이 initialBodyType·initialFuel 둘 다 "진입 즉시 조회" 계약을 약속하는데,
  // 위 테스트들은 initialBodyType만 태웠다(fuel 경로는 어떤 테스트도 거치지 않았다 —
  // 후속 코드리뷰 spec-16-8 2차 리뷰 P13). "전기" 칩(fuel 필터)으로도 동일하게 확인한다.
  testWidgets(
      'initialFuel이 있으면 진입 즉시 그 필터로 조회한다(수동 검색 버튼 없이)',
      (tester) async {
    final fake = _RecordingFakeRepository(
      filteredResult: const [
        ListingCardData(
          id: 'ev-1',
          manufacturer: '테슬라',
          model: '모델Y',
          year: 2023,
          price: 55000000,
          mileage: 8000,
          region: '서울',
        ),
      ],
      emptyResult: const [],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(fake),
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
        ],
        child: const MaterialApp(home: SearchScreen(initialFuel: '전기')),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      fake.calls.any((f) => f.fuel == '전기'),
      isTrue,
      reason: '진입 즉시 fuel=전기로 조회했어야 한다',
    );
    expect(find.text('[테슬라] 모델Y · 2023년'), findsOneWidget,
        reason: '필터 결과가 화면에 보여야 한다(수동 검색 버튼을 누르지 않아도)');
  });

  // 후속 코드리뷰(spec-16-8 2차 리뷰) P13 — initState가 예약한 Future.microtask 안의
  // `if (!mounted) return;` 가드를 실제로 검증하는 테스트가 없었다. 화면을 빠르게 떠나는
  // 경로(칩 탭 직후 바로 뒤로가기)를 재현해, 그 microtask가 dispose된 State를 건드려도
  // 예외 없이 조용히 끝나는지 확인한다.
  //
  // ⚠️ 이 검사가 **보지 못하는 것**(실측, B4) — flutter_test의 `pump()`는 한 프레임을
  // 그리는 동안 예약된 microtask를 **그 same pump() 호출이 끝나기 전에** 항상 먼저
  // 흘려보낸다(`AutomatedTestWidgetsFlutterBinding.pump` — handleDrawFrame 뒤 즉시
  // flushMicrotasks). 그래서 이 initState의 Future.microtask는 이 화면을 마운트하는
  // `pumpWidget` 호출 **자체가 끝나기 전에** 항상 이미 실행되고(mounted=true로 정상
  // 통과), 그 다음 줄에서 다른 위젯으로 교체해도 "그 사이"를 잡을 수 없다 — 실제로 가드를
  // 지우고 이 파일을 다시 돌려봐도(코드리뷰 지시에 따른 실측) 이 테스트는 계속 초록이었다
  // (아래 verification 보고 참조). 즉 이 테스트는 "빠르게 떠나도 예외 없음"이라는 회귀
  // 방지 가치는 있지만, `if (!mounted) return;` 한 줄이 실제로 막는 레이스를 이 프레임워크
  // 안에서 강제로 재현하는 방법을 찾지 못했다 — 가드는 남기되(다른 경로에서 방어적 가치가
  // 있을 수 있음), 이 테스트가 그 가드의 필요성을 증명하지는 못한다는 점을 그대로 적는다.
  testWidgets(
      '진입 직후(마이크로태스크가 돌기 전) 화면을 떠나도 예외가 나지 않는다(mounted 가드)',
      (tester) async {
    final fake = _RecordingFakeRepository(
      filteredResult: const [],
      emptyResult: const [],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingsRepositoryProvider.overrideWithValue(fake),
          wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
        ],
        child: const MaterialApp(home: SearchScreen(initialBodyType: 'SUV')),
      ),
    );
    // pumpAndSettle 하지 않는다 — settle 전(이 화면을 곧바로 떠나는 경로)을 재현한다.
    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pump(); // 남은 마이크로태스크를 흘려보낸다.

    expect(
      tester.takeException(),
      isNull,
      reason: 'dispose된 SearchScreen에서 예약된 콜백이 ref.read/notifier를 건드리면 '
          '"widget disposed" 예외가 날 수 있다 — mounted 가드가 이를 막아야 한다',
    );
  });
}
