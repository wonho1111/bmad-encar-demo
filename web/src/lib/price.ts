// 가격 **표시** 단일 출처 (2026-08-13 사용자 결정 #가격표기 A).
//
// 왜 만원인가: UX 목업 전체(card-final-1·landing-1·detail-1)가 "4,650만원" 표기이고, 엔카·헤이딜러
// 같은 실제 중고차 서비스도 같다. 우리 화면만 "41,120,000원"이라 자릿수가 길어 카드·모바일 하단
// 바에서 자리를 크게 먹고 한눈에 안 읽혔다.
//
// ⚠️ **바꾸는 건 "보여주는 글자"뿐이다.** DB(`listings.price`)와 입력 폼(/sell의 "가격 (원)",
//    /search의 가격 범위)은 **원 그대로**다(사용자 결정 원문: "입력 폼과 DB는 원 그대로 두고
//    표시만 바꿈"). 그래서 이 함수는 읽기 전용 표시 경로에서만 부른다 — 값을 저장하거나 다시
//    파싱하는 데 쓰지 않는다.
//
// 반올림하지 않는다(중요): 만원 단위로 딱 떨어지지 **않는** 값은 만원으로 뭉개지 않고 원 표기를
//   그대로 쓴다. 가격은 반올림이 곧 오표시(실제와 다른 금액을 보여주는 것)라, "짧게 보이는 것"보다
//   "틀리지 않는 것"이 우선이다. 지금 로컬 DB 166건은 전부 만원 단위(실측: `price % 10000 <> 0`이
//   0건)라 실제로는 전부 만원 표기로 나온다 — 폴백은 나중에 그런 값이 들어와도 조용히 틀리지
//   않게 하는 안전망이다.
import { UNITS } from '@/lib/constants';

const MAN = 10_000;

/**
 * 매물 가격을 화면 표기로 바꾼다. 41_120_000 → "4,112만원", 9_500 → "9,500원".
 * (원 표기가 필요한 곳은 `price.toLocaleString('ko-KR') + UNITS.price`를 직접 쓰지 말고 이 함수를 쓴다 —
 *  표기 규칙이 한 곳에만 있어야 다음에 또 갈리지 않는다.)
 */
export function formatPrice(price: number): string {
  if (!Number.isFinite(price)) return `-${UNITS.price}`; // 계약-외 값(NaN 등)이 "NaN원"으로 새지 않게.
  if (price < MAN || price % MAN !== 0) {
    return `${price.toLocaleString('ko-KR')}${UNITS.price}`;
  }
  return `${(price / MAN).toLocaleString('ko-KR')}${UNITS.priceMan}`;
}
