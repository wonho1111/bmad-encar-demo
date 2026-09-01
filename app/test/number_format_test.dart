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

  // AI 시세 진단(5단계) — 통계값 표기 회귀: percentile_cont 보간 중앙값(만원 단위 깨짐)이
  // 원 표기로 새지 않아야 한다(web price.ts formatStatPrice 미러, 같은 경계값으로 고정).
  test('formatStatPrice — 통계값은 만원 반올림 후 wonText로 표기한다(매물 호가는 wonText가 정답)', () {
    expect(formatStatPrice(13475000), '1,348만원'); // 1347.5 → 반올림(away from zero) → 1348.
    expect(formatStatPrice(17800000), '1,780만원'); // 이미 만원 단위 값은 wonText와 동일.
    expect(formatStatPrice(13474999), '1,347만원'); // 반올림 경계(내림).
  });
}
