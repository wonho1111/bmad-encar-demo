// 7.2 천단위 콤마 포맷 단위 테스트(원·km·cc).
import 'package:flutter_test/flutter_test.dart';
import 'package:app/core/format/number_format.dart';

void main() {
  test('thousands 천단위 콤마', () {
    expect(thousands(0), '0');
    expect(thousands(100), '100');
    expect(thousands(1000), '1,000');
    expect(thousands(12000000), '12,000,000');
    expect(thousands(-3500), '-3,500');
  });

  test('단위 텍스트', () {
    // ✎ 2026-08-13 — 만원 표기로 바뀌었다(웹 formatPrice와 같은 규칙).
    expect(wonText(25000000), '2,500만원');
    expect(kmText(35000), '35,000km');
    expect(ccText(1999), '1,999cc');
  });
}
