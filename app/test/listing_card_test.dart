// Story 16.2 — ListingCard 사진 셀 위젯 테스트. I/O 매트릭스 카드 3행(사진 있음/없음/로드실패)
// + imageCount 0/1/N 배지 표시 여부를 단언한다.
//
// 로드 실패는 loopback 주소(`http://127.0.0.1:1`)로 재현한다 — `flutter_test`(TestWidgetsFlutterBinding)는
// 스위트 안에서 HttpClient를 만드는 순간 모든 HTTP 요청을 실제 네트워크 없이 항상 400으로
// 가로챈다(플러터 프레임워크의 명시된 테스트 동작). 그래서 어떤 URL을 쓰든 결정적으로 실패하며,
// 실제 인터넷 접근이나 원격 호스트 가용성에 기대지 않는다.
//
// ⚠️ `find.byType(Image)`는 로드 성공/실패와 무관하게 항상 매칭된다 — `Image.network(...)`가
// 반환하는 `Image` 위젯 자체는 errorBuilder가 대신 그려질 때도 트리에 그대로 남기 때문이다
// (내부 `_ImageState.build()`가 무엇을 그리는지만 갈릴 뿐). 그래서 로드 실패 단언은
// `find.byType(Image)`의 부재가 아니라 `PhotoPlaceholder`의 존재로 확인한다.
import 'package:app/core/theme/app_theme.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_card.dart';
import 'package:app/features/listings/listing_photo_widgets.dart';
import 'package:app/features/wishlist/wish_button.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

ListingCardData _card({
  String? imageUrl,
  int? imageCount,
  String? accidentStatus,
  bool? isSingleOwner,
  bool? isNonSmoker,
  String? sellerName,
  List<String>? options,
}) =>
    ListingCardData(
      id: 'l1',
      manufacturer: '현대',
      model: '아반떼',
      year: 2021,
      price: 18000000,
      mileage: 20000,
      region: '서울',
      imageUrl: imageUrl,
      imageCount: imageCount,
      accidentStatus: accidentStatus,
      isSingleOwner: isSingleOwner,
      isNonSmoker: isNonSmoker,
      sellerName: sellerName,
      options: options,
    );

// 코드리뷰 지적(P4, CLAUDE.md B4 "그 검사가 안 보는 것을 검사 옆에 적는다") — 아래
// SingleChildScrollView는 카드가 고정 뷰포트(기본 800×600)를 넘칠 때 RenderFlex overflowed를
// 피하려는 정당한 우회지만, 그 대가로 이 파일의 모든 테스트가 카드의 세로 오버플로 자체를
// 영영 못 본다(스크롤 컨테이너 안에서는 자식이 아무리 길어도 오버플로 에러가 안 난다). 이게
// 괜찮은 이유(추측이 아니라 실측 확인, grep으로 호출부 4곳을 직접 확인): 실제 화면에서
// ListingCard를 쓰는 곳은 home_screen.dart(Column, 바깥이 SingleChildScrollView)·
// search_screen.dart·wishlist_screen.dart·ai_chat_screen.dart(셋 다 ListView.builder) 뿐이고,
// 넷 다 세로로 무한히 늘어날 수 있는 컨테이너다 — 카드 높이를 미리 고정하는 그리드(예:
// GridView, 고정 extent 리스트)는 하나도 없다. 그래서 이 회피가 가리는 실패 모드는 실제
// 화면에서 애초에 발생하지 않는다.
Future<void> _pump(
  WidgetTester tester,
  ListingCardData listing, {
  VoidCallback? onTap,
  bool wished = false, // 이 파일의 테스트들은 하트 상태를 다루지 않는다 — 고정값으로 충분.
}) async {
  await tester.pumpWidget(
    // ProviderScope: Story 16.3부터 ListingCard가 WishButton(ConsumerStatefulWidget)을
    // 내장한다 — WishButton 자신은 build()에서 provider를 읽지 않으므로(탭 시점에만 읽음)
    // Supabase 초기화는 필요 없지만, Riverpod 컨테이너를 찾을 조상은 있어야 한다.
    ProviderScope(
      child: MaterialApp(
        home: Scaffold(
          // SingleChildScrollView — 실제 화면(홈·검색·AI 결과)에서 ListingCard는 항상
          // 스크롤 가능한 목록 안에 있다(spec-16-9로 카드가 신뢰속성 행·옵션 칩까지 더해져
          // 키가 커졌다 — 고정 뷰포트(기본 800×600)에 `Scaffold(body:)`로 바로 꽂으면
          // `RenderFlex overflowed` 에러가 난다, 실측). 스크롤 컨테이너로 감싸 실제 배치
          // 조건과 맞춘다.
          body: SingleChildScrollView(
            child: ListingCard(listing: listing, onTap: onTap, wished: wished),
          ),
        ),
      ),
    ),
  );
}

void main() {
  testWidgets('imageUrl 없음(null) → 플레이스홀더, 배지 없음(imageCount도 없음)', (tester) async {
    await _pump(tester, _card());

    expect(find.byType(PhotoPlaceholder), findsOneWidget);
    expect(find.byType(PhotoCountBadge), findsNothing);
  });

  testWidgets('imageUrl 빈 문자열 → 플레이스홀더(계약-외 값 정규화, conventions.md §4)',
      (tester) async {
    await _pump(tester, _card(imageUrl: '', imageCount: 2));

    expect(find.byType(PhotoPlaceholder), findsOneWidget);
    // "N장" 배지는 사진 로드 성공 여부와 무관하게 imageCount>=1이면 표시된다.
    expect(find.text('2장'), findsOneWidget);
  });

  testWidgets(
      'imageUrl 있음 → 응답 전(구성 직후)엔 플레이스홀더 없이 Image 위젯이 빌드되고, '
      'imageCount>=1이면 "N장" 배지가 뜬다', (tester) async {
    // ⚠️ 이 테스트는 "사진 로드 성공"을 증명하지 않는다 — flutter_test(TestWidgetsFlutterBinding)는
    // 스위트 안에서 HttpClient가 만들어지는 순간 모든 HTTP 요청을 실제 네트워크 없이 항상 400으로
    // 가로챈다(위 파일 헤더 주석), 즉 이 URL도 결국은 실패로 귀결된다. 여기서 확인하는 건 응답이
    // 오기 전(pumpWidget 직후, 비동기 완료를 기다리지 않은 시점)의 위젯 트리 구성뿐이다 —
    // Image 위젯이 만들어지고 플레이스홀더로 아직 안 바뀌었는지, 배지가 뜨는지.
    await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg', imageCount: 3));

    expect(find.byType(PhotoPlaceholder), findsNothing);
    expect(find.byType(Image), findsOneWidget);
    expect(find.text('3장'), findsOneWidget);
  });

  testWidgets('imageCount 0 → 사진이 있어도 배지는 뜨지 않는다', (tester) async {
    await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg', imageCount: 0));

    expect(find.byType(PhotoCountBadge), findsNothing);
  });

  testWidgets('imageCount null → 배지 없음(기본값 0 취급)', (tester) async {
    await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg'));

    expect(find.byType(PhotoCountBadge), findsNothing);
  });

  testWidgets('imageUrl 있으나 로드 실패 → 플레이스홀더로 폴백하되 "N장" 배지는 유지',
      (tester) async {
    await _pump(
      tester,
      _card(imageUrl: 'http://127.0.0.1:1/broken.jpg', imageCount: 5),
    );

    // errorBuilder는 비동기(마이크로태스크)로 발화한다. 고정 1초 sleep 대신 최대 40회(50ms 간격
    // = 최대 2초)까지 짧게 폴링하고 플레이스홀더가 뜨는 즉시 멈춘다 — 실시간 고정 대기는 CI
    // 부하가 크면 그마저도 부족해 flaky해지고, 평소엔 불필요하게 느리다.
    var settled = false;
    for (var i = 0; i < 40 && !settled; i++) {
      await tester.runAsync(
        () => Future<void>.delayed(const Duration(milliseconds: 50)),
      );
      await tester.pump();
      settled = find.byType(PhotoPlaceholder).evaluate().isNotEmpty;
    }
    expect(settled, isTrue,
        reason: '2초 안에 이미지 로드 실패(errorBuilder)가 반영되지 않았다 — 폴링 예산 초과.');

    expect(find.byType(PhotoPlaceholder), findsOneWidget);
    // AC: 로드 실패에도 "N장" 배지는 그대로 남는다(장수는 계약-검증 통과 행 수, 로드 성공과 무관).
    expect(find.text('5장'), findsOneWidget);
  });

  testWidgets(
      'AC 고정: 5:3 AspectRatio · BoxFit.cover · 배지가 우하단(8,8) · 배지 배경이 완전 불투명',
      (tester) async {
    await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg', imageCount: 2));

    final aspectRatio = tester.widget<AspectRatio>(find.byType(AspectRatio));
    expect(aspectRatio.aspectRatio, 5 / 3);

    final image = tester.widget<Image>(find.byType(Image));
    expect(image.fit, BoxFit.cover);

    final positioned = tester.widget<Positioned>(
      find.ancestor(of: find.byType(PhotoCountBadge), matching: find.byType(Positioned)),
    );
    expect(positioned.bottom, 8);
    expect(positioned.right, 8);

    final badgeContainer = tester.widget<Container>(
      find.descendant(of: find.byType(PhotoCountBadge), matching: find.byType(Container)),
    );
    final decoration = badgeContainer.decoration as BoxDecoration;
    // "불투명(반투명 아님)" AC — 배경색 알파가 완전 불투명(255)이어야 한다.
    expect(decoration.color!.a, 1.0);
  });

  // Story 16.3 코드리뷰 지적 — 카드의 신뢰속성 배선을 보는 테스트가 하나도 없어서
  // `TrustAttributesCardOverlay(...)` 블록 전체를 `SizedBox.shrink()`로 지워도 스위트가
  // green이었다(AC1 미고정). 아래 3개가 그 사각지대를 메운다.
  group('신뢰속성 뱃지 배선(Story 16.3 코드리뷰 지적)', () {
    testWidgets('신뢰속성 값이 있으면 카드에 뱃지가 렌더되고, 전부 없으면 아무것도 안 뜬다',
        (tester) async {
      await _pump(tester, _card(accidentStatus: '무사고', isNonSmoker: true));

      expect(find.text('무사고'), findsOneWidget);
      expect(find.text('비흡연'), findsOneWidget);

      await _pump(tester, _card());

      expect(find.text('무사고'), findsNothing);
      expect(find.text('비흡연'), findsNothing);
    });

    testWidgets(
        '뱃지 라벨을 탭해도 카드 탭(onTap)이 그대로 발화한다(P1 — spec-16-9로 신뢰속성이 오버레이에서 '
        '사진 아래 전용 행으로 바뀌어 IgnorePointer 자체가 더 이상 필요 없지만, 그 결과가 여전히 '
        '지켜지는지는 계속 고정한다)', (tester) async {
      var tapped = false;
      await _pump(
        tester,
        _card(accidentStatus: '무사고'),
        onTap: () => tapped = true,
      );

      await tester.tap(find.text('무사고'));
      await tester.pump();

      expect(tapped, isTrue,
          reason: '신뢰속성 행이 카드 탭(InkWell) 영역을 가로막으면 여기서 실패한다');
    });

    // ⚠️ 이 가드를 "ListingCard를 실제 무한 폭 부모(가로 스크롤 등)에 pump해 takeException()이
    // null인지" 보는 위젯 테스트로는 격리해서 볼 수 없다(실측 확인, B4) — `_CardPhoto` 쪽의
    // 별개 `Column`(`CrossAxisAlignment.stretch`)이 이 가드와 무관하게 "무한 폭+stretch는
    // 안 된다"는 Flutter 자체 제약으로 먼저 죽는다(가드를 넣거나 빼거나 결과가 같다 — 즉 그
    // 시나리오로는 가드 유무를 구분하는 테스트 자체가 성립하지 않는다). 그래서 가드 로직을
    // `safeCardPhotoHeight`로 뽑아 직접 잰다(listing_card.dart 참조).
    test('safeCardPhotoHeight — 무한/0 이하 폭은 안전한 폴백(300 기준)으로 대체한다(isFinite 가드)',
        () {
      expect(safeCardPhotoHeight(double.infinity), 300 / (5 / 3));
      expect(safeCardPhotoHeight(0), 300 / (5 / 3));
      expect(safeCardPhotoHeight(-10), 300 / (5 / 3));
    });

    test('safeCardPhotoHeight — 정상 폭이면 그대로 5:3 비율로 계산한다', () {
      expect(safeCardPhotoHeight(360), 360 / (5 / 3));
    });
  });

  // 코드리뷰 지적(P1/P2) — 찜 버튼을 사진 하단 경계에 절반 겹치게 놓았더니 "N장" 배지(같은
  // 우하단)를 가렸다(실측: 배지 LTRB(751.5,453,792,476) vs 찜 LTRB(748,462,792,506)). web
  // 원본(WishButton.tsx `top-full mt-1`)처럼 사진 "아래"에 완전히 걸어 겹침을 없앤다.
  group('찜 버튼 위치(P1/P2 코드리뷰)', () {
    testWidgets('찜 버튼이 사진 "N장" 배지를 가리지 않는다', (tester) async {
      await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg', imageCount: 3));

      final badgeRect = tester.getRect(find.byType(PhotoCountBadge));
      final wishRect = tester.getRect(find.byKey(const Key('wish_button')));

      expect(badgeRect.overlaps(wishRect), isFalse,
          reason: '찜 버튼이 사진 우하단 "N장" 배지를 덮으면 안 된다(P1)');
    });

    testWidgets('찜 버튼은 카드 경계 안에 온전히 들어온다(P2 — 카드 clip 전제 실측 확인)',
        (tester) async {
      await _pump(tester, _card(imageUrl: 'https://example.com/photo.jpg', imageCount: 1));

      final cardRect = tester.getRect(find.byType(ListingCard));
      final wishRect = tester.getRect(find.byKey(const Key('wish_button')));

      expect(wishRect.left, greaterThanOrEqualTo(cardRect.left));
      expect(wishRect.right, lessThanOrEqualTo(cardRect.right));
      expect(wishRect.top, greaterThanOrEqualTo(cardRect.top));
      expect(wishRect.bottom, lessThanOrEqualTo(cardRect.bottom));
    });
  });

  // spec-16-9(DW-760 해소) — 카드 재정렬: 신뢰속성 위치·가격 강조·옵션 칩. 목업(card-final-1.html)·
  // DESIGN.md 레이아웃 B가 정본이다(이 스토리에 한해 웹 코드보다 우선, Design Notes). 채택 전
  // 실제로 한 번씩 깨서(가격 폰트 크기를 14로 되돌림·옵션 칩 블록을 통째로 지움·신뢰속성 행을
  // 사진보다 위로 옮김) red를 확인하고 되돌려 green을 재확인했다(CLAUDE.md B4).
  group('카드 재정렬(spec-16-9, DW-760 해소)', () {
    testWidgets('가격이 26px/800/priceEmphasis이고, 차량명보다 큰 텍스트다(AC④)', (tester) async {
      await _pump(tester, _card());

      final priceFinder = find.text('18,000,000원');
      final priceText = tester.widget<Text>(priceFinder);
      expect(priceText.style?.fontSize, 26);
      expect(priceText.style?.fontWeight, FontWeight.w800);
      expect(priceText.style?.color, AppColors.priceEmphasis);
      // D5 anti-wrap 가드 — 가격은 한 줄로 유지하고 넘치면 ellipsis로 자른다(줄바꿈 금지).
      expect(priceText.maxLines, 1);
      expect(priceText.overflow, TextOverflow.ellipsis);

      // 코드리뷰 지적(P3) — 차량명 Text의 style엔 fontSize가 없다(테마 기본값 14를 상속).
      // `nameText.style?.fontSize ?? 0`은 항상 0이라 `0 < 26`이 항상 참이라서 무엇을 해도
      // 절대 못 깨지는 검사였다. 렌더된 실제 크기(RenderParagraph, 테마 상속 반영)를 직접 잰다.
      final nameFinder = find.text('[현대] 아반떼 · 2021년');
      final nameSize =
          tester.renderObject<RenderParagraph>(nameFinder).text.style?.fontSize;
      final priceSize =
          tester.renderObject<RenderParagraph>(priceFinder).text.style?.fontSize;
      expect(nameSize, isNotNull);
      expect(priceSize, isNotNull);
      expect(
        priceSize!,
        greaterThan(nameSize!),
        reason: '가격(26px)이 차량명(테마 상속 14px)보다 커야 한다 — 예전엔 15px/inkPrimary로 '
            '거의 같은 무게였다',
      );
    });

    testWidgets('신뢰속성 행이 사진 뒤(문서 순서상 아래)에 온다 — 오버레이가 아니다(AC⑥)',
        (tester) async {
      await _pump(
        tester,
        _card(imageUrl: 'https://example.com/photo.jpg', accidentStatus: '무사고'),
      );

      // AspectRatio는 _CardPhoto가 유일하게 쓰는 공개 타입(사진 5:3 셀) — 그 하단 경계보다
      // 신뢰속성 텍스트가 아래(더 큰 dy)에 있어야 "사진 뒤"다.
      final photoBottom = tester.getBottomLeft(find.byType(AspectRatio)).dy;
      final trustTop = tester.getTopLeft(find.text('무사고')).dy;
      expect(
        trustTop,
        greaterThanOrEqualTo(photoBottom),
        reason: '예전엔 신뢰속성이 사진 좌상단 오버레이라 사진보다 위(작은 dy)에 겹쳐 있었다',
      );
    });

    // 코드리뷰 지적(P3) — spec의 AC는 정보 영역 세로 순서를 사진 → 신뢰속성 행 → 차량명 →
    // meta → 가격 → 옵션 칩으로 못박는데, 지금까지 고정된 좌표 단언은 "신뢰속성이 사진보다
    // 아래"뿐이었다. 차량명·meta·가격·옵션 칩 네 마디의 순서는 어떤 테스트도 안 봐서, 예전
    // 레이아웃(이름 → 가격 → meta)으로 되돌려도 스위트가 green으로 남는다. 폰트 크기·우측
    // 여백 단언(위 테스트들)은 각 줄이 어떤 스타일인지만 보고 그 줄들이 서로 어떤 순서인지는
    // 보지 않으므로(order-independent) 이 좌표 비교가 별도로 필요하다.
    testWidgets('정보 영역 순서 — 차량명 → meta → 가격 → 옵션 칩 순으로 세로 배치된다(AC)',
        (tester) async {
      await _pump(
        tester,
        _card(sellerName: '홍길동', options: const ['선루프', '통풍시트']),
      );

      final nameY = tester.getTopLeft(find.text('[현대] 아반떼 · 2021년')).dy;
      final metaY = tester.getTopLeft(find.textContaining('판매자 홍길동')).dy;
      final priceY = tester.getTopLeft(find.text('18,000,000원')).dy;
      final chipsY = tester.getTopLeft(find.text('선루프')).dy;

      expect(nameY, lessThan(metaY), reason: '차량명이 meta보다 위에 있어야 한다');
      expect(metaY, lessThan(priceY), reason: 'meta가 가격보다 위에 있어야 한다');
      expect(priceY, lessThan(chipsY), reason: '가격이 옵션 칩보다 위에 있어야 한다');
    });

    testWidgets('meta 줄에 판매자가 합쳐진다(더 이상 별도 줄이 아니다)', (tester) async {
      await _pump(tester, _card(sellerName: '홍길동'));

      expect(find.textContaining('판매자 홍길동'), findsOneWidget);
    });

    // 코드리뷰 지적(P1) — 신뢰속성 행·차량명 줄은 찜 버튼 겹침 구간(오른쪽 52px)을 피하는
    // Padding이 있는데 meta 줄에는 없었다. 신뢰속성이 전부 null(일반적인 기존 데이터)이면
    // TrustAttributesCardRow가 SizedBox.shrink()라 meta 줄이 그 구간의 첫 줄로 올라오고,
    // 판매자 이름이 길면 찜 버튼 바로 아래에서 ellipsis로 잘린다.
    testWidgets('meta 줄도 찜 버튼 겹침 구간을 피한다(신뢰속성 0개 + 긴 판매자명, P1)',
        (tester) async {
      tester.view.physicalSize = const Size(390, 844);
      tester.view.devicePixelRatio = 1.0;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await _pump(
        tester,
        _card(sellerName: '아주아주아주아주아주아주아주긴판매자이름입니다'),
      );

      final metaFinder = find.textContaining('판매자 아주아주');
      final wishFinder = find.byType(WishButton);
      expect(metaFinder, findsOneWidget);
      expect(wishFinder, findsOneWidget);

      expect(
        tester.getRect(metaFinder).right,
        lessThanOrEqualTo(tester.getRect(wishFinder).left),
        reason: 'meta 줄에 우측 여백(right: 52) Padding이 없으면 찜 버튼과 겹친다(P1)',
      );
    });

    group('옵션 칩(AC⑤)', () {
      testWidgets(
          '옵션 0개(null) — "등록된 옵션 없음" 플레이스홀더 칩으로 슬롯을 예약하고 muted 스타일이다',
          (tester) async {
        await _pump(tester, _card());

        final labelFinder = find.text('등록된 옵션 없음');
        expect(labelFinder, findsOneWidget);

        // 코드리뷰 지적(P8) — 라벨 텍스트만 보고 있었고, 플레이스홀더 칩이 실제 옵션 칩(petrol
        // 강조)과 구분되는 muted 스타일(회색 아웃라인)인지는 아무 검사도 안 봤다
        // (home_ai_entry_test.dart의 chip decoration 색 단언 관례를 따른다).
        final chipContainer = tester.widget<Container>(
          find.ancestor(of: labelFinder, matching: find.byType(Container)).first,
        );
        final chipDecoration = chipContainer.decoration as BoxDecoration;
        expect((chipDecoration.border as Border).top.color, AppColors.borderHairline);

        final chipText = tester.widget<Text>(labelFinder);
        expect(chipText.style?.color, AppColors.inkMuted);
      });

      testWidgets('옵션 5개(희소 2개 포함) — 희소가 우선 노출되고 나머지는 "외 N개"로 접힌다, 최대 3개',
          (tester) async {
        // 선루프·통풍시트=희소(high), 내비게이션=mid, 스마트키·라디오=보편(common) —
        // docs/conventions.md §11.2/§11.4. 우선순위 상위 3개(선루프·통풍시트·내비게이션)만
        // 칩으로 뜨고, 나머지 2개(스마트키·라디오)는 "외 2개"로 접힌다.
        await _pump(
          tester,
          _card(
            options: const ['선루프', '통풍시트', '내비게이션', '스마트키', '라디오'],
          ),
        );

        expect(find.text('선루프'), findsOneWidget);
        expect(find.text('통풍시트'), findsOneWidget);
        expect(find.text('내비게이션'), findsOneWidget);
        expect(find.text('외 2개'), findsOneWidget);
        expect(find.text('스마트키'), findsNothing,
            reason: '상위 3개 밖의 보편 옵션은 개별 칩이 아니라 오버플로 개수에만 반영된다');
        expect(find.text('라디오'), findsNothing);
      });

      // 코드리뷰 지적(P5) — 예전엔 emptiness 판정만 trim하고 원본(공백 포함) 값을 그대로
      // 우선순위 조회·dedup에 넘겼다. ' 선루프'는 통제어휘 조회 실패로 최하위로 강등되고,
      // '선루프'와 dedup되지 않아 칩이 두 번 뜬다.
      testWidgets('앞뒤 공백은 정규화된다 — 같은 옵션이 중복 칩으로 뜨지 않고 공백뿐인 값은 무시된다',
          (tester) async {
        await _pump(
          tester,
          _card(options: const [' 선루프', '선루프', '  ', '스마트키']),
        );

        expect(find.text('선루프'), findsOneWidget,
            reason: '공백 포함/미포함 "선루프"는 정규화 후 같은 값이라 칩이 한 번만 떠야 한다');
        expect(find.text(' 선루프'), findsNothing);
        expect(find.text(''), findsNothing, reason: '공백뿐인 값은 빈 라벨 칩을 만들면 안 된다');
      });

      // 코드리뷰 패치(spec-16-9 P5) — 긴 옵션 라벨 3개가 390px 카드 폭을 넘기면, 예전
      // 구현(오버플로 칩이 가로 스크롤 Row의 마지막 자식)에서는 "외 N개"가 오른쪽 화면 밖으로
      // 밀려나 사용자가 옆으로 끌기 전엔 안 보였다. 존재만(findsOneWidget) 확인하면 트리에는
      // 있지만 화면 밖으로 밀린 상태도 통과해버리므로, 실제 좌표(오버플로 칩의 우측 끝이 카드
      // 우측 끝 안쪽인지)로 "보이는지"를 단언한다.
      testWidgets('긴 옵션 라벨 3개 + 오버플로 — "외 N개" 칩이 카드 폭 안에서 항상 보인다(P5)',
          (tester) async {
        tester.view.physicalSize = const Size(390, 844);
        tester.view.devicePixelRatio = 1.0;
        addTearDown(tester.view.resetPhysicalSize);
        addTearDown(tester.view.resetDevicePixelRatio);

        await _pump(
          tester,
          _card(
            options: const [
              '파노라마글래스루프',
              '헤드업디스플레이',
              '어댑티브크루즈',
              '스마트키',
              '라디오',
            ],
          ),
        );

        final overflowFinder = find.text('외 2개');
        expect(overflowFinder, findsOneWidget);

        final cardRight = tester.getRect(find.byType(ListingCard)).right;
        final overflowRight = tester.getRect(overflowFinder).right;
        expect(
          overflowRight,
          lessThanOrEqualTo(cardRight),
          reason: '오버플로 칩이 카드 오른쪽 경계 밖으로 밀리면(스크롤해야만 보이면) 이 카드는 '
              '"옵션이 딱 3개뿐"으로 보인다',
        );
      });
    });
  });
}
