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

/// 가격 **표시**. 예: 41200000 → "4,120만원", 9500 → "9,500원".
///
/// ✎ 2026-08-13 — 웹과 같은 만원 표기로 맞춘다(web `web/src/lib/price.ts` formatPrice).
///   UX 목업 전체와 엔카·헤이딜러가 만원 표기인데 원 단위 전체 숫자는 자릿수가 길어 카드·
///   하단 바에서 한눈에 안 읽혔다. **바꾸는 건 보여주는 글자뿐이다** — DB와 입력 폼(등록
///   화면의 "가격 (원)", 검색 필터의 가격 범위)은 원 그대로다.
///
/// 반올림하지 않는다(중요): 만원 단위로 딱 떨어지지 않는 값은 뭉개지 않고 원 표기를 그대로
///   쓴다. 가격은 반올림이 곧 오표시(실제와 다른 금액)라, 짧게 보이는 것보다 틀리지 않는 것이
///   우선이다. 웹의 formatPrice와 **같은 규칙**이다 — 두 표면이 같은 매물에 다른 금액을
///   보여주면 안 되므로 한쪽만 바꾸면 안 된다.
String wonText(int price) {
  const man = 10000;
  if (price < man || price % man != 0) return '${thousands(price)}원';
  return '${thousands(price ~/ man)}만원';
}

/// 주행거리(km). 예: 35000 → "35,000km".
String kmText(int mileage) => '${thousands(mileage)}km';

/// 배기량(cc). 예: 1999 → "1,999cc".
String ccText(int displacement) => '${thousands(displacement)}cc';
