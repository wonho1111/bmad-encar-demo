// Story 16.2 — ListingGallery(상세 사진 갤러리) 위젯 테스트. I/O 매트릭스 갤러리 2행:
// 0장(플레이스홀더, 크래시 없음, CM-A) + N장 스와이프 시 "k/N" 카운터 갱신.
//
// 사진 URL은 loopback(`http://127.0.0.1:1`, 아무도 안 듣는 포트)을 쓴다 — 실제 로드 성공 여부는
// 이 테스트의 관심사가 아니고(카운터·스와이프만 본다), 실제 이미지를 받아오려 하면 원격 호스트
// 가용성에 테스트가 의존하게 된다.
import 'package:app/features/listings/listing_detail_screen.dart';
import 'package:app/features/listings/listing_photo_widgets.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> _pump(WidgetTester tester, List<String> imageUrls) async {
  await tester.pumpWidget(
    MaterialApp(
      home: Scaffold(body: ListingGallery(imageUrls: imageUrls)),
    ),
  );
}

void main() {
  testWidgets('사진 0장 → 플레이스홀더만 표시되고 크래시 없음(CM-A)', (tester) async {
    await _pump(tester, const []);

    expect(find.byType(PhotoPlaceholder), findsOneWidget);
    expect(find.byType(PageView), findsNothing);
    expect(find.byType(PhotoCountBadge), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('사진 1장 → PageView 없이도 "1/1" 카운터가 뜬다', (tester) async {
    await _pump(tester, const ['http://127.0.0.1:1/a.jpg']);

    expect(find.text('1/1'), findsOneWidget);
  });

  testWidgets('사진 N장(N>1) → 스와이프마다 "k/N" 카운터가 갱신된다', (tester) async {
    await _pump(tester, const [
      'http://127.0.0.1:1/a.jpg',
      'http://127.0.0.1:1/b.jpg',
      'http://127.0.0.1:1/c.jpg',
    ]);

    expect(find.text('1/3'), findsOneWidget);

    // 왼쪽으로 스와이프 → 다음 사진.
    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pumpAndSettle();
    expect(find.text('2/3'), findsOneWidget);

    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pumpAndSettle();
    expect(find.text('3/3'), findsOneWidget);

    expect(tester.takeException(), isNull);
  });

  testWidgets(
      '사진 목록이 줄어든 채로 위젯이 재사용되면(provider 재조회) 카운터가 0으로 되돌아간다(didUpdateWidget)',
      (tester) async {
    // 3장으로 시작해 "3/3"까지 스와이프한다.
    await _pump(tester, const [
      'http://127.0.0.1:1/a.jpg',
      'http://127.0.0.1:1/b.jpg',
      'http://127.0.0.1:1/c.jpg',
    ]);
    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pumpAndSettle();
    await tester.drag(find.byType(PageView), const Offset(-400, 0));
    await tester.pumpAndSettle();
    expect(find.text('3/3'), findsOneWidget);

    // 같은 위치에 같은 타입의 ListingGallery를 사진 1장짜리로 다시 pump한다 — 새 위젯
    // 인스턴스가 만들어지는 게 아니라 같은 State가 재사용되며 didUpdateWidget이 호출된다.
    // 이 오버라이드가 없으면 이전 _index(2)가 새 리스트 길이(1)를 넘어서 "3/1" 같은
    // 불가능한 카운터가 뜨거나(범위를 벗어난 인덱스로 PageView가 예외를 던질 수도 있다).
    await _pump(tester, const ['http://127.0.0.1:1/only.jpg']);
    await tester.pumpAndSettle();

    expect(find.text('1/1'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
