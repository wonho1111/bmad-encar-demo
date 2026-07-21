// resolveCardImage — AI 응답의 `image_path`를 공개 URL로 바꾸는 매핑 (Story 9.6 AC5).
//
// 왜 단위테스트인가: 순수 함수이고(서버 컴포넌트 밖) 여기가 **api와 카드 사이의 유일한 접합부**다.
// 한 글자만 틀려도 모든 AI 카드가 조용히 "사진 준비중"으로 떨어지는데, 화면상으로는 진짜
// "사진 없는 매물"과 구별되지 않는다(docs/tech-debt.md #73). 선례: images/coverImages.test.ts.
import { beforeAll, describe, expect, it } from 'vitest';

import { resolveCardImage } from './aiSearch';

const BASE = 'https://example.supabase.co';

beforeAll(() => {
  // getPublicUrl이 getSupabaseEnv()로 읽는 값(없으면 한국어로 throw).
  process.env.NEXT_PUBLIC_SUPABASE_URL = BASE;
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';
});

/** 사진 필드를 뺀 나머지 필수 7필드(값 자체는 이 테스트의 관심사가 아니다). */
const BASE_CARD = {
  id: 'l-1',
  manufacturer: '현대',
  model: '싼타페',
  year: 2020,
  price: 26700000,
  mileage: 62000,
  region: '강원',
};

describe('resolveCardImage', () => {
  it('정상: image_path를 공개 URL로 조립해 image_url에 넣고, 경로는 버린다', () => {
    const card = resolveCardImage({ ...BASE_CARD, image_path: 'uid/l-1/a.webp', image_count: 3 });

    expect(card.image_url).toBe(`${BASE}/storage/v1/object/public/listing-images/uid/l-1/a.webp`);
    expect(card.image_count).toBe(3);
    // image_path는 ListingCardData 계약에 없다 — 카드는 URL만 안다(conventions.md §4).
    expect(card).not.toHaveProperty('image_path');
    // 나머지 필드는 손대지 않는다.
    expect(card.id).toBe('l-1');
    expect(card.price).toBe(26700000);
  });

  it('null: 사진 0장 매물은 image_url=null·count=0 → "사진 준비중" 플레이스홀더', () => {
    const card = resolveCardImage({ ...BASE_CARD, image_path: null, image_count: 0 });

    expect(card.image_url).toBeNull();
    expect(card.image_count).toBe(0);
  });

  it('빈 문자열: 빈 URL로 깨진 이미지를 렌더하지 않는다 (§4 계약-외 값 정규화)', () => {
    // 빈 경로로 getPublicUrl을 부르면 버킷 루트를 가리키는 URL이 나와 <img>가 깨진다.
    expect(resolveCardImage({ ...BASE_CARD, image_path: '' }).image_url).toBeNull();
    // 공백만 있는 경로도 같다 — 문자열이긴 하지만 가리키는 파일이 없다.
    expect(resolveCardImage({ ...BASE_CARD, image_path: '   ' }).image_url).toBeNull();
  });

  it('음수·비숫자 count: 0으로 하한 처리한다 ("N장" 배지에 음수 노출 금지)', () => {
    expect(resolveCardImage({ ...BASE_CARD, image_count: -3 }).image_count).toBe(0);
    expect(resolveCardImage({ ...BASE_CARD, image_count: '5' }).image_count).toBe(0);
    expect(resolveCardImage({ ...BASE_CARD, image_count: null }).image_count).toBe(0);
    expect(resolveCardImage({ ...BASE_CARD, image_count: undefined }).image_count).toBe(0);
    expect(resolveCardImage({ ...BASE_CARD, image_count: NaN }).image_count).toBe(0);
  });

  it('image_path가 문자열이 아니면 URL을 만들지 않는다 (서버가 계약을 벗어난 값을 보내도 안 터진다)', () => {
    // isValidListing은 필수 7필드만 보므로 이런 값이 여기까지 올 수 있다(§4 "런타임 가드 범위 주의").
    expect(resolveCardImage({ ...BASE_CARD, image_path: 42 }).image_url).toBeNull();
    expect(resolveCardImage({ ...BASE_CARD, image_path: { a: 1 } }).image_url).toBeNull();
    expect(resolveCardImage({ ...BASE_CARD }).image_url).toBeNull(); // 필드 자체가 없음
  });

  // --- 코드리뷰 2026-07-20 반영분 ---------------------------------------------------

  it('소수 count: 정수로 자른다 ("2.7장" 배지 금지 — 계약 타입은 int)', () => {
    // Number.isFinite(2.7)은 true라 기존 방어(숫자인가?)를 그대로 통과했다.
    // 반올림이 아니라 버림이다 — 3.9장을 "4장"이라 부르면 없는 사진을 약속하는 셈이다.
    expect(resolveCardImage({ ...BASE_CARD, image_path: 'u/l/a.webp', image_count: 2.7 }).image_count).toBe(2);
    expect(resolveCardImage({ ...BASE_CARD, image_path: 'u/l/a.webp', image_count: 3.9 }).image_count).toBe(3);
  });

  it('사진이 없으면 장수도 0이다 ("사진 준비중" 위에 "5장" 배지가 얹히지 않는다)', () => {
    // 두 값을 따로 정규화하면 화면이 자기모순이 된다 — 플레이스홀더인데 배지는 5장.
    // ListingCardImage가 배지를 사진 분기 밖에 두는 것은 의도된 설계지만(로드 실패해도
    // 장수는 남긴다 — 9.4), 그건 "경로는 있는데 실패"용이고 "경로가 아예 없음"과는 다르다.
    expect(resolveCardImage({ ...BASE_CARD, image_path: '', image_count: 5 }).image_count).toBe(0);
    expect(resolveCardImage({ ...BASE_CARD, image_count: 5 }).image_count).toBe(0);
    // 반대로 경로가 있으면 장수는 그대로 살아 있어야 한다(과잉 차단 금지).
    expect(resolveCardImage({ ...BASE_CARD, image_path: 'u/l/a.webp', image_count: 5 }).image_count).toBe(5);
  });
});
