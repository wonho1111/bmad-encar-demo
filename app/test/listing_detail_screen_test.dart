// review P7 — 상세 화면이 ListingGallery를 실제로 장착해 쓰는지 확인(new test).
// 리뷰가 listing_detail_screen.dart의 `ListingGallery(imageUrls: listing.imageUrls)` 줄을
// 주석 처리했는데도 전체 스위트가 green이었다 — listing_gallery_test.dart는 ListingGallery를
// 직접 pump하고(화면 배선은 안 본다), app_router_test.dart는 listingDetailProvider를
// null(못 찾음 분기)로 오버라이드해 AppBar 개수만 본다(그 분기는 ListingGallery까지 안 간다).
// 어느 쪽도 "상세 화면이 실제로 그 자리에 ListingGallery를 꽂아 쓰는지"를 안 본다.
// app_router_test.dart의 provider-override + pump 관례를 그대로 재사용해, 사진이 있는
// ListingDetail로 실제 화면을 pump하고 갤러리 카운터로 확인한다.
import 'package:app/core/theme/app_theme.dart';
import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/chat/chat_providers.dart';
import 'package:app/features/chat/chat_repository.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_detail_screen.dart';
import 'package:app/features/listings/listing_trust_widgets.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/wishlist/wishlist_providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// initState()의 `incrementListingView` 호출(DW-740, 16.6)이 실제 네트워크(가짜 자격증명)를
/// 타지 않도록 리포지토리 계층에서 끊는다(wish_button_test.dart·search_screen_test.dart와
/// 같은 이유) — 대부분의 테스트는 이 호출 자체를 검증하지 않으므로 기본은 조용히 삼키는 가짜,
/// 호출 횟수·인자를 검증하는 테스트만 카운터를 직접 읽는다.
class _FakeListingsRepository extends ListingsRepository {
  int incrementCalls = 0;
  final incrementedIds = <String>[];

  @override
  Future<void> incrementListingView(String listingId) async {
    incrementCalls++;
    incrementedIds.add(listingId);
  }
}

/// 비로그인 문의하기 탭(FR58, DW-738) 테스트용 — `openOrCreateRoom`이 실제로 호출되지
/// 않아야 함을 직접 카운트로 확인한다(단순히 "화면이 안 죽었다"보다 강한 증거).
class _FakeChatRepository extends ChatRepository {
  int openOrCreateRoomCalls = 0;

  @override
  Future<OpenRoomResult> openOrCreateRoom({
    required String listingId,
    required String buyerId,
  }) async {
    openOrCreateRoomCalls++;
    return const OpenRoomFailure('테스트에서는 호출되면 안 된다');
  }
}

/// 화면이 요구하는 필수 15필드만 채운 최소 상세 데이터. 사진은 `withImages`로 붙인다
/// (listing.dart 주석: `listings` 단일 row엔 없는 데이터라 fromMap이 안 채우고 이 메서드로
/// 별도 부착한다 — 실제 조회 경로와 같은 조립 방식).
ListingDetail _fakeDetail({
  required List<String> imageUrls,
  // 기존 "사고여부"(accidentFree) 행과 신뢰속성 accidentStatus 뱃지는 둘 다 "무사고" 텍스트를
  // 낼 수 있는 별개 필드다(spec-16-3 Design Notes — 혼동 금지, 승격하지 않는다). 기본값은 기존
  // 테스트와 동일하게 true로 유지하고, 신뢰속성 배선 테스트만 명시적으로 false를 넘겨 "무사고"
  // 텍스트 중복(사고여부 행 vs 신뢰속성 칩)을 피한다.
  bool accidentFree = true,
  String? accidentStatus,
  bool? isSingleOwner,
  bool? isNonSmoker,
  // 2026-08-13 상세 재구성으로 화면에 실제로 쓰이게 된 필드들(판매자정보 카드·옵션 카드·설명).
  String? sellerName,
  List<String>? options,
  String? description,
}) {
  final base = ListingDetail(
    id: 'listing-1',
    sellerId: 'seller-1',
    manufacturer: '현대',
    model: '아반떼',
    bodyType: '준중형차',
    year: 2021,
    price: 20000000,
    mileage: 10000,
    color: '흰색',
    fuel: '가솔린',
    transmission: '자동',
    displacement: 1600,
    seats: 5,
    region: '서울',
    accidentFree: accidentFree,
    status: 'on_sale',
    accidentStatus: accidentStatus,
    isSingleOwner: isSingleOwner,
    isNonSmoker: isNonSmoker,
    sellerName: sellerName,
    options: options,
    description: description,
  );
  return base.withImages(imageUrls);
}

void main() {
  // app_router_test.dart와 같은 이유로 딱 한 번 초기화한다 — _DetailContent가 전역
  // `supabase.auth.currentUser`를 직접 읽는다(문의하기 버튼 노출 여부 판단).
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  testWidgets('상세 화면이 실제로 ListingGallery를 장착해 "1/3" 카운터를 그린다', (tester) async {
    // listing_gallery_test.dart와 동일하게 loopback(아무도 안 듣는 포트) URL을 쓴다 — 이
    // 테스트의 관심사는 화면이 갤러리를 장착했는지이지, 실제 이미지 로드 성공 여부가 아니다.
    const urls = [
      'http://127.0.0.1:1/a.jpg',
      'http://127.0.0.1:1/b.jpg',
      'http://127.0.0.1:1/c.jpg',
    ];

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: urls)),
          // 16.6 — initState()의 incrementListingView가 실 네트워크를 안 타게 끊는다(위 클래스 주석).
          listingsRepositoryProvider.overrideWithValue(_FakeListingsRepository()),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('1/3'),
      findsOneWidget,
      reason:
          '상세 화면이 ListingGallery를 실제로 장착해야만 이 카운터가 뜬다 — 그 배선 줄이 '
          '통째로 빠져도(주석 처리) 이전엔 어떤 테스트도 안 잡았다(review P7 실측: 172건 '
          '전부 green).',
    );
  });

  testWidgets(
      '상세 화면이 신뢰속성 값을 실제로 받으면 TrustAttributesDetailSection과 찜 버튼이 함께 렌더된다'
      '(Story 16.3 코드리뷰 지적 #8 — 단독 위젯 테스트가 아니라 화면 배선 자체를 본다)',
      (tester) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1').overrideWith(
            (ref) async => _fakeDetail(
              imageUrls: const [],
              accidentFree: false, // "사고여부" 행이 "무사고" 텍스트와 안 겹치게(위 주석 참조).
              accidentStatus: '무사고',
              isSingleOwner: true,
              isNonSmoker: true,
            ),
          ),
          // 카드 진입점과 같은 단일 provider — 이 매물을 찜한 상태로 만들어 상세의 인라인
          // WishButton이 initialWished=true를 실제로 받는지까지 함께 본다.
          wishedListingIdsProvider.overrideWith((ref) async => {'listing-1'}),
          // 16.6 — initState()의 incrementListingView가 실 네트워크를 안 타게 끊는다.
          listingsRepositoryProvider.overrideWithValue(_FakeListingsRepository()),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    // ✎ 2026-08-13 상세 재구성(사용자 지적 #5) — **갤러리가 제목 줄보다 위로 올라갔다**(웹
    // 모바일 순서와 동일). 기본 테스트 뷰포트(800×600)에서는 갤러리 한 장이 그 높이를 거의
    // 다 먹어 제목 줄이 화면 밖에 남고, SliverList가 그 자식을 아예 안 만들어 이 테스트가
    // "안 그려짐"으로 오해했다(실측: 이 변경 직후 detail_wish_button 0개). 실제 기기 폭
    // (390×844)으로 맞춰 그 착시를 없앤다 — 폰에서는 갤러리(234) 아래 제목 줄이 첫 화면에 있다.
    tester.view.physicalSize = const Size(390, 844);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpAndSettle();

    // 제목 줄의 찜 버튼은 갤러리 바로 아래라 스크롤 전(첫 화면)에 이미 빌드돼 있다 — 아래에서
    // 트러스트 섹션을 보려고 스크롤하면 이 줄은 화면 밖으로 밀려나 SliverList가 다시 걷어내므로
    // (findsNothing이 "안 그려짐"인지 "스크롤로 밀림"인지 구분 못 함) 스크롤 전에 먼저 본다.
    // wishedListingIdsProvider 값을 실제로 반영해 채워진 하트여야 한다.
    expect(find.byKey(const Key('detail_wish_button')), findsOneWidget);
    expect(
      find.byIcon(Icons.favorite),
      findsOneWidget,
      reason: '상세 화면이 wishedListingIdsProvider 결과를 실제로 WishButton.initialWished에 실어야 한다',
    );

    // 2026-08-10 Epic 16 묶음 코드리뷰(verification-gap) — **`variant`를 아무도 안 봤다.**
    // `WishButton`은 카드용(그림자 2, 테두리 없음)과 상세용(그림자 0, 테두리 있음) 두 모양으로
    // 갈리는데(`wish_button.dart`의 `onCard` 분기), 검사는 키 존재와 하트 아이콘만 봤다.
    // 그래서 상세 호출부의 `variant: WishButtonVariant.inline`을 지워 기본값(card)으로 되돌려도
    // 전 스위트가 green이었다(아래 실측). 모양 자체를 단언해 그 회귀를 막는다.
    final material = tester.widget<Material>(
      find.descendant(
        of: find.byKey(const Key('detail_wish_button')),
        matching: find.byType(Material),
      ).first,
    );
    expect(material.elevation, 0,
        reason: '상세의 찜 버튼은 inline 변형이라 그림자가 없다 — 2면 카드용(card) 변형으로 되돌아간 것이다');
    expect((material.shape as CircleBorder).side.color, AppColors.borderHairline,
        reason: '상세는 그림자 대신 테두리로 구분한다 — BorderSide.none이면 card 변형이다');

    // 신뢰정보 섹션은 요약 블록 아래에 있어 첫 화면을 벗어난다 — 스크롤해
    // 실제로 빌드되게 한다(안 그러면 SliverList가 화면 밖 자식을 아예 안 만들어 findsNothing이
    // "안 그려짐"과 "화면 밖"을 구분하지 못하고 거짓양성 실패를 낸다).
    await tester.scrollUntilVisible(
      find.byType(TrustAttributesDetailSection),
      300,
      scrollable: find.byType(Scrollable).first,
    );
    await tester.pumpAndSettle();

    // 뱃지 + 면책이 **같은 블록 안에서** 함께 나온다(B9 결속이 화면 배선에서도 이어지는지).
    // ⚠️ 화면 전체(find.text)로 세지 않는다 — 2026-08-13 재구성으로 같은 라벨이 위쪽 요약
    // 블록에도 있어(의도된 중복) 전역 카운트는 스크롤 위치에 따라 1이 되기도 2가 되기도 한다.
    // 이 블록의 서브트리로 좁히면 그 흔들림 없이 결속만 본다.
    final section = find.byType(TrustAttributesDetailSection);
    expect(find.descendant(of: section, matching: find.text('무사고')), findsOneWidget);
    expect(find.descendant(of: section, matching: find.text('1인소유')), findsOneWidget);
    expect(find.descendant(of: section, matching: find.text('비흡연')), findsOneWidget);
    expect(
      find.descendant(
          of: section, matching: find.textContaining('판매자가 직접 입력한 정보')),
      findsOneWidget,
    );
    // 재구성으로 새로 들어온 요구 — 칩만 반복하지 않고 **속성별 설명**이 붙어야 한다(웹과 동일).
    expect(
      find.descendant(
          of: section, matching: find.textContaining('사고 이력이 없다고 판매자가 신고했습니다')),
      findsOneWidget,
    );
  });

  testWidgets(
      '상세 화면이 처음 빌드되면 incrementListingView가 정확히 한 번 호출된다(DW-740 해소, '
      'spec-16-6 AC1)', (tester) async {
    final repo = _FakeListingsRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
          listingsRepositoryProvider.overrideWithValue(repo),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      repo.incrementCalls,
      1,
      reason: '_DetailContentState.initState()가 매물 확인 후 정확히 1회 호출해야 한다'
          '(호출 지점 단일성은 view_count_call_site_test.dart가 소스 스캔으로 별도 고정)',
    );
    expect(repo.incrementedIds, ['listing-1']);
  });

  testWidgets(
      '비로그인 상태에서도 sticky 문의 바가 스크롤 없이 바로 보이고, 탭하면 방 생성 없이 '
      '/login으로 이동한다(FR58 행동 게이트, DW-738, spec-16-9로 sticky 바 이관)',
      (tester) async {
    final listingsRepo = _FakeListingsRepository();
    final chatRepo = _FakeChatRepository();
    final router = GoRouter(
      initialLocation: '/detail',
      routes: [
        GoRoute(
          path: '/detail',
          builder: (context, state) =>
              const ListingDetailScreen(listingId: 'listing-1'),
        ),
        GoRoute(
          path: '/login',
          builder: (context, state) => const Scaffold(
            body: Text('login-probe', key: Key('login_probe')),
          ),
        ),
      ],
    );

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
          listingsRepositoryProvider.overrideWithValue(listingsRepo),
          chatRepositoryProvider.overrideWithValue(chatRepo),
          currentUserProvider.overrideWithValue(null), // 비로그인 명시.
        ],
        child: MaterialApp.router(routerConfig: router),
      ),
    );
    await tester.pumpAndSettle();

    // spec-16-9(DW-735 해소) — 문의하기가 이제 Scaffold.bottomNavigationBar(sticky 바)라
    // 본문을 스크롤하지 않아도 첫 프레임에 바로 보인다(예전엔 본문 인라인 버튼이라 스크롤이
    // 필요했다 — 이 테스트가 바로 그 차이를 고정한다, 스크롤 코드를 지운 것 자체가 회귀 검사).
    expect(
      find.byKey(const Key('detail_sticky_bar')),
      findsOneWidget,
      reason: '스크롤하지 않은 첫 프레임에서 sticky 바가 바로 보여야 한다(AC⑦)',
    );
    expect(
      find.byKey(const Key('go_chat_inquiry')),
      findsOneWidget,
      reason: '본인 매물이 아니면 로그인 여부와 무관하게 문의하기 버튼이 렌더돼야 한다'
          '(화면 단위가 아니라 행동 단위 게이트)',
    );

    // 코드리뷰 지적(P8) — sticky 바 가격도 D5 anti-wrap 대상인데(카드 가격과 같은 원칙) 어떤
    // 테스트도 이 바 안의 가격 Text에 maxLines/overflow를 단언하지 않았다.
    final stickyPriceText = tester.widget<Text>(
      find.descendant(
        of: find.byKey(const Key('detail_sticky_bar')),
        // ✎ 2026-08-13 — 가격 표시가 만원 표기로 바뀌었다(number_format.wonText, 웹과 같은 규칙).
        matching: find.text('2,000만원'),
      ),
    );
    expect(stickyPriceText.maxLines, 1);
    expect(stickyPriceText.overflow, TextOverflow.ellipsis);

    await tester.tap(find.byKey(const Key('go_chat_inquiry')));
    await tester.pumpAndSettle();

    expect(
      chatRepo.openOrCreateRoomCalls,
      0,
      reason: '방 생성(서버 쓰기)이 나가면 안 된다',
    );
    expect(find.byKey(const Key('login_probe')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets(
      '로그인·타인 매물이면 sticky 바가 스크롤 없이 바로 보이고, 탭하면 문의 요청(openOrCreateRoom)'
      '이 나간다(spec-16-9, DW-735 해소)', (tester) async {
    final listingsRepo = _FakeListingsRepository();
    final chatRepo = _FakeChatRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
          listingsRepositoryProvider.overrideWithValue(listingsRepo),
          chatRepositoryProvider.overrideWithValue(chatRepo),
          // _fakeDetail의 sellerId='seller-1'과 다른 id — 타인 매물.
          currentUserProvider.overrideWithValue(
            User(
              id: 'buyer-1',
              appMetadata: const {},
              userMetadata: const {},
              aud: 'authenticated',
              email: 'buyer@test.com',
              createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
            ),
          ),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('detail_sticky_bar')),
      findsOneWidget,
      reason: '스크롤하지 않은 첫 프레임에서 sticky 바가 바로 보여야 한다(AC⑦)',
    );

    await tester.tap(find.byKey(const Key('go_chat_inquiry')));
    await tester.pumpAndSettle();

    expect(
      chatRepo.openOrCreateRoomCalls,
      1,
      reason: '로그인·타인 매물이면 실제로 문의 요청이 나가야 한다(openOrCreateRoom)',
    );
    expect(tester.takeException(), isNull);
  });

  // 코드리뷰 지적(P7) — 이 커밋이 수동 하단 패딩(`20 + viewPadding.bottom`)을 SafeArea(top:
  // false) 두 겹(본문·sticky 바)으로 바꿨는데, `app/test/`의 기본 테스트 뷰는 인셋이 전부
  // 0이라(어떤 테스트도 tester.view.padding을 건드리지 않는다) 이 SafeArea들이 실제로
  // 뭔가를 밀어내는지 아무도 관찰한 적이 없다 — 둘 중 하나를 지워도 스위트는 green이고,
  // 실기기(Android 제스처 바)에서만 문의하기 버튼이 그 아래 깔린다.
  testWidgets(
      '하단 시스템 인셋(제스처 바 48)이 있어도 문의하기 버튼이 그 위에 온전히 보인다(P7)',
      (tester) async {
    tester.view.padding = const FakeViewPadding(bottom: 48);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.reset);

    final listingsRepo = _FakeListingsRepository();
    final chatRepo = _FakeChatRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
          listingsRepositoryProvider.overrideWithValue(listingsRepo),
          chatRepositoryProvider.overrideWithValue(chatRepo),
          // 타인 매물(위 "로그인·타인 매물" 케이스와 동일 조건) — sticky 바가 실제로 뜬다.
          currentUserProvider.overrideWithValue(
            User(
              id: 'buyer-1',
              appMetadata: const {},
              userMetadata: const {},
              aud: 'authenticated',
              email: 'buyer@test.com',
              createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
            ),
          ),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final screenHeight = tester.getSize(find.byType(MaterialApp)).height;
    final buttonBottom =
        tester.getRect(find.byKey(const Key('go_chat_inquiry'))).bottom;

    expect(
      buttonBottom,
      lessThanOrEqualTo(screenHeight - 48),
      reason: 'SafeArea(top: false) 하나(본문 또는 sticky 바)라도 빠지면 문의하기 버튼이 '
          '48px 인셋(실기기 제스처 바) 아래로 내려간다 — 기본 테스트 뷰(인셋 0)만 보는 다른 '
          '테스트들은 이 회귀를 못 잡는다',
    );
  });

  testWidgets('본인 매물이면 sticky 바(bottomNavigationBar) 자체가 없다(spec-16-9, 기존 3분기 유지)',
      (tester) async {
    final listingsRepo = _FakeListingsRepository();
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          listingDetailProvider('listing-1')
              .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
          listingsRepositoryProvider.overrideWithValue(listingsRepo),
          // _fakeDetail의 sellerId와 같은 id — 본인 매물.
          currentUserProvider.overrideWithValue(
            User(
              id: 'seller-1',
              appMetadata: const {},
              userMetadata: const {},
              aud: 'authenticated',
              email: 'seller@test.com',
              createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
            ),
          ),
        ],
        child: const MaterialApp(
          home: ListingDetailScreen(listingId: 'listing-1'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.byKey(const Key('detail_sticky_bar')),
      findsNothing,
      reason: '본인 매물은 문의 CTA 자체가 없다(AC⑦ — 본인 매물 제외, 기존 3분기 그대로)',
    );
    expect(find.byKey(const Key('go_chat_inquiry')), findsNothing);
  });

  // ✎ 2026-08-13 사용자 지적 #5 — 상세를 웹 모바일 순서로 재구성했다. 아래 세 테스트가 그
  //   재구성의 계약(순서·판매자정보 카드·값 없음 분기)을 고정한다. 없으면 다음 사람이 순서를
  //   되돌리거나 카드를 빼도 아무도 못 잡는다(예전 구조가 정확히 그 상태였다).
  group('상세 재구성(2026-08-13 사용자 지적 #5) — 웹 모바일 순서 미러', () {
    Future<void> pumpDetail(WidgetTester tester,
        {SellerPublicSummary? summary, String? sellerName}) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            listingDetailProvider('listing-1').overrideWith(
              (ref) async => _fakeDetail(
                imageUrls: const [],
                accidentStatus: '무사고',
                sellerName: sellerName,
                options: const ['선루프'],
                description: '실사용 차량입니다.',
              ),
            ),
            wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
            listingsRepositoryProvider.overrideWithValue(_FakeListingsRepository()),
            sellerSummaryProvider((sellerId: 'seller-1', listingId: 'listing-1'))
                .overrideWith((ref) async => summary),
          ],
          child: const MaterialApp(
            home: ListingDetailScreen(listingId: 'listing-1'),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    testWidgets('세로 순서 — 갤러리 → 제목 → 가격 → 주요제원 → 신뢰정보 → 차량정보 → 옵션 → 판매자정보',
        (tester) async {
      await pumpDetail(tester,
          sellerName: '판매왕',
          summary: const SellerPublicSummary(joinedAt: null, otherOnSaleCount: null));

      // 스크롤로 화면 밖 자식까지 실제로 만들어 가며 각 자리의 y를 잰다(SliverList는 화면 밖
      // 자식을 안 만든다 — 좌표를 재려면 먼저 보이게 해야 한다).
      double topOf(Finder f) => tester.getTopLeft(f).dy;

      final galleryY = topOf(find.byType(ListingGallery));
      final titleY = topOf(find.byKey(const Key('detail_title')));
      final priceY = topOf(find.byKey(const Key('detail_price')));
      final specsY = topOf(find.byKey(const Key('detail_summary_specs')));
      expect(galleryY, lessThan(titleY), reason: '웹 모바일도 갤러리가 맨 위다');
      expect(titleY, lessThan(priceY));
      expect(priceY, lessThan(specsY),
          reason: '대표 가격이 주요제원보다 위 — 가격이 요약의 주인공이다');

      // 아래쪽 섹션들은 스크롤해서 순서를 확인한다(같은 프레임에 다 안 들어온다).
      await tester.scrollUntilVisible(find.text('판매자정보'), 300,
          scrollable: find.byType(Scrollable).first);
      await tester.pumpAndSettle();
      expect(topOf(find.text('차량정보')), lessThan(topOf(find.text('옵션'))));
      expect(topOf(find.text('옵션')), lessThan(topOf(find.text('판매자정보'))));
    });

    testWidgets('판매자정보 카드 — RPC 값(가입 시점·다른 판매중 매물 수)이 실제로 화면에 나온다(FR56)',
        (tester) async {
      await pumpDetail(
        tester,
        sellerName: '판매왕',
        summary: const SellerPublicSummary(
          joinedAt: '2026-03-02T00:30:00Z', // KST로는 3월 2일 09:30 — 월이 바뀌지 않는다.
          otherOnSaleCount: 3,
        ),
      );

      await tester.scrollUntilVisible(find.text('판매자정보'), 300,
          scrollable: find.byType(Scrollable).first);
      await tester.pumpAndSettle();

      expect(find.byKey(const Key('detail_seller_name')), findsOneWidget);
      expect(find.text('2026년 3월 가입'), findsOneWidget);
      expect(find.text('이 판매자의 다른 판매중 매물 3건'), findsOneWidget);
    });

    testWidgets('신뢰속성이 하나도 없으면 신뢰정보 섹션이 "입력하지 않았어요"로 답한다(빈 화면 아님)',
        (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            listingDetailProvider('listing-1')
                .overrideWith((ref) async => _fakeDetail(imageUrls: const [])),
            wishedListingIdsProvider.overrideWith((ref) async => <String>{}),
            listingsRepositoryProvider.overrideWithValue(_FakeListingsRepository()),
            sellerSummaryProvider((sellerId: 'seller-1', listingId: 'listing-1'))
                .overrideWith((ref) async => null),
          ],
          child: const MaterialApp(
            home: ListingDetailScreen(listingId: 'listing-1'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.scrollUntilVisible(find.byKey(const Key('detail_trust_empty')), 300,
          scrollable: find.byType(Scrollable).first);
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('detail_trust_empty')), findsOneWidget);
      // 섹션 자체가 사라지면 "이 차 무사고인가?"에 화면이 아무 말도 안 하게 된다(웹과 같은 판단).
      expect(find.text('신뢰정보'), findsOneWidget);
    });
  });

  group('판매자정보 표시 순수함수(web 미러) — 경계값', () {
    test('formatSellerJoinDate — KST 기준으로 연·월을 만든다(자정 전후에 월이 밀리지 않는다)', () {
      // UTC 2026-02-28T23:00Z = KST 2026-03-01 08:00 — 기기 타임존을 그대로 쓰면 "2월"이 된다.
      expect(formatSellerJoinDate('2026-02-28T23:00:00Z'), '2026년 3월 가입');
      expect(formatSellerJoinDate('2026-07-05T12:00:00Z'), '2026년 7월 가입');
      expect(formatSellerJoinDate(null), isNull);
      expect(formatSellerJoinDate(''), isNull);
      expect(formatSellerJoinDate('그냥-문자열'), isNull,
          reason: '파싱 불가는 행 숨김 — 잘못된 값을 화면에 그대로 흘리지 않는다');
    });

    test('sellerOtherListingsLabel — null은 숨김, 0은 "없어요", 1 이상은 건수', () {
      expect(sellerOtherListingsLabel(null), isNull);
      expect(sellerOtherListingsLabel(0), '이 판매자의 다른 판매중 매물이 없어요.');
      expect(sellerOtherListingsLabel(-1), '이 판매자의 다른 판매중 매물이 없어요.',
          reason: '음수는 계약-외 값 — 0과 같이 취급한다(conventions §4)');
      expect(sellerOtherListingsLabel(3), '이 판매자의 다른 판매중 매물 3건');
    });
  });
}
