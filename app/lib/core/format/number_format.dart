// 숫자 표시 포맷 — 천단위 콤마(단위 규칙: 원·km·cc, docs/conventions §3).
// intl 패키지 없이 직접 구현(의존성 최소화). 음수도 안전 처리.

/// 정수를 천단위 콤마 문자열로. 예: 12000000 → "12,000,000".
String thousands(int n) {
  final neg = n < 0;
  final digits = n.abs().toString();
  final buf = StringBuffer();
  for (var i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 == 0) buf.write(',');
    buf.write(digits[i]);
  }
  return neg ? '-${buf.toString()}' : buf.toString();
}

/// 가격(원). 예: 12000000 → "12,000,000원".
String wonText(int price) => '${thousands(price)}원';

/// 주행거리(km). 예: 35000 → "35,000km".
String kmText(int mileage) => '${thousands(mileage)}km';

/// 배기량(cc). 예: 1999 → "1,999cc".
String ccText(int displacement) => '${thousands(displacement)}cc';
