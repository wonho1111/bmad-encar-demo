// 홈 당겨서 새로고침 — 섹션 하나(popularListingsProvider)가 실패해도 다른 섹션
// (recentListingsProvider)의 새로고침·전체 화면이 죽지 않아야 한다(코드리뷰 발견,
// spec-16-8 Review Triage Log #2 — 이전엔 `Future.wait([...])`가 두 refresh를 그대로 묶어,
// 하나가 reject되면 나머지 하나의 rejection이 아무도 catch하지 않는 관찰되지 않은 예외가
// 됐다). 웹 `fetchSection`이 지키는 "한 섹션 실패가 다른 섹션·전체 화면을 안 죽인다"
// 원칙을 새로고침 경로에서도 확인한다.
import 'dart:async';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/auth/home_screen.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// home_screen_wishlist_test.dart와 동일한 최소 가짜 사용자.
User _fakeUser() => User(
      id: '00000000-0000-0000-0000-000000000001',
      appMetadata: const {},
      userMetadata: const {},
      aud: 'authenticated',
      email: 'seller@test.com',
      createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
    );

const _recentListing = ListingCardData(
  id: 'recent-1',
  manufacturer: '현대',
  model: '아반떼',
  year: 2021,
  price: 18000000,
  mileage: 20000,
  region: '서울',
);

void main() {
  testWidgets(
      '당겨서 새로고침 — popularListingsProvider가 실패해도 예외가 새지 않고 '
      'recentListingsProvider 섹션은 정상 렌더된다', (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider.overrideWith((ref) async => const [_recentListing]),
          // "지금 인기" 섹션은 새로고침 때마다 실패한다 — 이 provider가 autoDispose라
          // ref.refresh()가 build()를 다시 태우므로 최초 렌더·새로고침 둘 다 이 실패를 탄다.
          popularListingsProvider.overrideWith((ref) async => throw Exception('인기 매물 조회 실패')),
          wishedListingIdsProvider.overrideWith((ref) async => const <String>{}),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('[현대] 아반떼 · 2021년'),
      findsOneWidget,
      reason: '새로고침 전 recentListingsProvider 섹션은 정상 렌더돼야 이후 비교가 의미 있다',
    );
    expect(find.byKey(const Key('popular_error')), findsOneWidget,
        reason: '새로고침 전에도 popularListingsProvider는 이미 실패 상태여야 한다');

    // RefreshIndicatorState.show()로 실제 당겨서 새로고침 경로(onRefresh)를 직접 구동한다 —
    // 제스처(fling/drag)보다 결정적이고, 이 테스트가 보려는 것은 onRefresh 콜백 자체의
    // 내결함성이지 스크롤 물리가 아니다.
    final refreshState =
        tester.state<RefreshIndicatorState>(find.byType(RefreshIndicator));
    unawaited(refreshState.show());
    await tester.pumpAndSettle();

    expect(
      tester.takeException(),
      isNull,
      reason:
          'popularListingsProvider의 refresh 실패가 recentListingsProvider의 refresh를 '
          '묶은 Future.wait를 즉시 reject시켜, 그 나머지 refresh의 rejection이 관찰되지 '
          '않은 예외로 새면 안 된다',
    );
    expect(
      find.text('[현대] 아반떼 · 2021년'),
      findsOneWidget,
      reason:
          '한쪽(popular) refresh 실패가 다른 쪽(recent) refresh·렌더를 막으면 안 된다'
          '(웹 fetchSection과 같은 섹션별 격리 원칙)',
    );
    expect(
      find.byKey(const Key('popular_error')),
      findsOneWidget,
      reason: '실패한 섹션은 실패 자체는 그대로 에러 문구로 보여야 한다(감춰지면 안 된다)',
    );
  });

  // T2(spec-16-8 검증 갭) — 위 테스트는 격리(한쪽이 실패해도 다른 쪽이 죽지 않는다)만 본다.
  // popularListingsProvider가 항상 throw이므로 위 단언은 새로고침 **전**에도 이미 참이라,
  // onRefresh의 본문을 통째로 지우거나 popularListingsProvider의 refresh 줄만 지워도
  // 위 테스트는 계속 green이다(측정됨) — "새로고침이 실제로 재조회를 일으키는지" 자체를
  // 아무도 보지 않았다. 두 provider를 카운팅 override로 바꿔 실제 호출 횟수를 직접 센다
  // (app_router_test.dart의 "내 매물 관리를 열었다 돌아오면 두 홈 섹션이 다시 조회된다"와
  // 같은 카운팅 패턴).
  testWidgets(
      '당겨서 새로고침 — recentListingsProvider·popularListingsProvider가 실제로 다시 조회된다(각 2회)',
      (tester) async {
    var recentCount = 0;
    var popularCount = 0;
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          currentUserProvider.overrideWithValue(_fakeUser()),
          recentListingsProvider.overrideWith((ref) async {
            recentCount++;
            return const [_recentListing];
          }),
          popularListingsProvider.overrideWith((ref) async {
            popularCount++;
            return const <ListingCardData>[];
          }),
          wishedListingIdsProvider.overrideWith((ref) async => const <String>{}),
        ],
        child: const MaterialApp(home: HomeScreen()),
      ),
    );
    await tester.pumpAndSettle();
    expect(recentCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');
    expect(popularCount, 1, reason: '첫 진입은 정상적으로 1회 조회돼야 한다');

    final refreshState =
        tester.state<RefreshIndicatorState>(find.byType(RefreshIndicator));
    unawaited(refreshState.show());
    await tester.pumpAndSettle();

    expect(
      recentCount,
      2,
      reason: '당겨서 새로고침을 하면 방금 올라온 매물 섹션이 다시 조회돼야 한다',
    );
    expect(
      popularCount,
      2,
      reason: '당겨서 새로고침을 하면 지금 인기 섹션도 다시 조회돼야 한다 — onRefresh에서 '
          'popularListingsProvider의 refresh 줄이 빠지면(측정된 뮤테이션) 이 값이 1에 '
          '멈춘다',
    );
  });
}
