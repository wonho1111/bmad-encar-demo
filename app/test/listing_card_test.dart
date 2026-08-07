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
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/listing_card.dart';
import 'package:app/features/listings/listing_photo_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

ListingCardData _card({String? imageUrl, int? imageCount}) => ListingCardData(
      id: 'l1',
      manufacturer: '현대',
      model: '아반떼',
      year: 2021,
      price: 18000000,
      mileage: 20000,
      region: '서울',
      imageUrl: imageUrl,
      imageCount: imageCount,
    );

Future<void> _pump(WidgetTester tester, ListingCardData listing) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: ListingCard(listing: listing)),
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
}
