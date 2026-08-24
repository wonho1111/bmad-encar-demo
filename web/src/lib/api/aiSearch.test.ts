// resolveCardImage — AI 응답의 `image_path`를 공개 URL로 바꾸는 매핑 (Story 9.6 AC5).
//
// 왜 단위테스트인가: 순수 함수이고(서버 컴포넌트 밖) 여기가 **api와 카드 사이의 유일한 접합부**다.
// 한 글자만 틀려도 모든 AI 카드가 조용히 "사진 준비중"으로 떨어지는데, 화면상으로는 진짜
// "사진 없는 매물"과 구별되지 않는다(docs/tech-debt.md #73). 선례: images/coverImages.test.ts.
import { afterEach, beforeAll, describe, expect, it } from 'vitest';

import { resolveCardImage, searchAi } from './aiSearch';

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

// searchAi — 응답 매핑 (Story 13.4 후속 코드리뷰)
//
// 왜 이 테스트가 필요한가: `SearchResult` 타입에 `clarify`를 선언해 두고 실제 매핑에서
// 빠뜨리면, 타입은 "필드가 있다"고 말하는데 값은 영원히 undefined다. 그러면 나중에 칩 UI를
// 만드는 사람이 `if (result.clarify)`로 분기해도 서버가 칩을 보내는 상황에서조차 아무 일도
// 일어나지 않고, 아무 데서도 오류가 나지 않는다(조용한 실패). 실제로 그 상태였다.
describe('searchAi 응답 매핑', () => {
  const originalFetch = globalThis.fetch;

  function mockJsonResponse(payload: unknown) {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })) as typeof globalThis.fetch;
  }

  beforeAll(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.example.test';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('서버가 clarify를 보내면 그대로 실어 돌려준다', async () => {
    const clarify = { question: '조건을 조금만 좁혀볼게요', chips: ['3천만원 이하', 'SUV', '전기차'] };
    mockJsonResponse({ answer: '조건을 조금만 좁혀볼게요', listings: [], clarify });

    const result = await searchAi({ query: '패밀리카로 무난한 거', accessToken: 'token' });

    expect(result.clarify).toEqual(clarify);
  });

  it('clarify가 없으면(다른 라우트·상한 초과) null로 정규화한다 — undefined로 새지 않는다', async () => {
    mockJsonResponse({ answer: '조건에 맞는 매물 1건을 찾았어요.', listings: [] });

    const result = await searchAi({ query: '3천만원 이하 SUV', accessToken: 'token' });

    expect(result.clarify).toBeNull();
  });

  // 형태가 깨진 clarify는 버린다 — listings에 isValidListing이 있는 이유와 같다.
  // 통과시키면 칩 UI가 `clarify.chips.map(...)`에서 터지고, 그 오류는 try/catch 밖이라
  // 대화 화면 전체가 날아간다(이 파일 상단 주석의 listings 사례와 동일한 실패 형태).
  it.each([
    ['chips가 배열이 아님', { question: '좁혀볼게요', chips: 'SUV' }],
    ['chips 원소가 문자열이 아님', { question: '좁혀볼게요', chips: ['SUV', 3000] }],
    ['question이 없음', { chips: ['SUV'] }],
    ['객체가 아님', '좁혀볼게요'],
  ])('계약을 어긴 clarify(%s)는 null로 떨군다', async (_label, broken) => {
    mockJsonResponse({ answer: '조건을 조금만 좁혀볼게요', listings: [], clarify: broken });

    const result = await searchAi({ query: '패밀리카로 무난한 거', accessToken: 'token' });

    expect(result.clarify).toBeNull();
  });
});

// searchAi — narrowed_by 매핑 (Story 13.5)
//
// 왜 이 테스트가 필요한가: 위 clarify 테스트 상단 주석과 같은 이유다 — 타입만 선언하고 매핑을
// 빠뜨리면 값이 영원히 undefined로 새고, 실제 재제안 칩 UI를 만드는 사람이 값을 믿고 써도
// 아무 데서도 오류가 나지 않는다(13.4 1차 리뷰가 clarify에서 잡았던 것과 동일한 함정 재발 방지).
describe('searchAi narrowed_by 매핑', () => {
  const originalFetch = globalThis.fetch;

  function mockJsonResponse(payload: unknown) {
    globalThis.fetch = (async () =>
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })) as typeof globalThis.fetch;
  }

  beforeAll(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'https://api.example.test';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('서버가 narrowed_by(정상 문자열 배열)를 보내면 그대로 실어 돌려준다', async () => {
    const narrowedBy = ['price<=30000000', 'body_type=SUV', 'fuel=전기'];
    mockJsonResponse({
      answer: '저는 중고차 찾기를 도와드리는 차장님이에요.',
      listings: [],
      narrowed_by: narrowedBy,
    });

    const result = await searchAi({ query: '오늘 날씨 어때?', accessToken: 'token' });

    expect(result.narrowed_by).toEqual(narrowedBy);
  });

  it('narrowed_by가 없으면(다른 라우트) null로 정규화한다 — undefined로 새지 않는다', async () => {
    mockJsonResponse({ answer: '조건에 맞는 매물 1건을 찾았어요.', listings: [] });

    const result = await searchAi({ query: '3천만원 이하 SUV', accessToken: 'token' });

    expect(result.narrowed_by).toBeNull();
  });

  it('깨진 형태(숫자 배열)의 narrowed_by는 null로 떨군다', async () => {
    mockJsonResponse({
      answer: '저는 중고차 찾기를 도와드리는 차장님이에요.',
      listings: [],
      narrowed_by: [123, 456],
    });

    const result = await searchAi({ query: '오늘 날씨 어때?', accessToken: 'token' });

    expect(result.narrowed_by).toBeNull();
  });

  it('빈 배열([])은 정상값이 아니라 wire 버그 신호로 보고 null로 떨군다', async () => {
    // 서버 계약상 narrowed_by는 채워지면 항상 고정 3개다 — 빈 배열은 REJECT 판별
    // (narrowed_by !== null)을 잘못 트리거할 수 있는 스키마 위반 신호다(코드리뷰 2026-07-31).
    mockJsonResponse({
      answer: '저는 중고차 찾기를 도와드리는 차장님이에요.',
      listings: [],
      narrowed_by: [],
    });

    const result = await searchAi({ query: '오늘 날씨 어때?', accessToken: 'token' });

    expect(result.narrowed_by).toBeNull();
  });
});
