// heroSearchHandoff 단위테스트 — "새로고침 재실행 방지" 불변식을 코드로 고정한다(spec-11-3).
//
// 왜 이 함수만 테스트하나: consumeHeroSearchHandoff가 "읽고 즉시 삭제"를 안 지키면 로그인 사용자가
// /ai 도착 직후 새로고침할 때 같은 질의가 또 자동 실행돼 AI 검색 비용이 중복 과금된다(에픽이 명시적
// 으로 경고한 위험). 순수 함수라 값싸게 저장→소비→재조회 왕복을 전수 고정할 수 있다(project-context
// 규칙12 예외 조항 — vitest.config.ts 주석 참고).
import { beforeEach, describe, expect, it } from 'vitest';
import { consumeHeroSearchHandoff, setHeroSearchHandoff } from './heroSearchHandoff';

const STORAGE_KEY = 'encar-hero-search-handoff';

// vitest.config.ts는 node 환경(jsdom 미사용)이라 sessionStorage가 전역에 없다. 브라우저 Web
// Storage API 형태(getItem/setItem/removeItem)를 흉내 낸 최소 스텁으로 대체한다.
function createMemoryStorage(): Storage {
  const store = new Map<string, string>();
  return {
    getItem: (key: string) => store.get(key) ?? null,
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    clear: () => store.clear(),
    key: () => null,
    get length() {
      return store.size;
    },
  } as Storage;
}

beforeEach(() => {
  Object.defineProperty(globalThis, 'sessionStorage', {
    value: createMemoryStorage(),
    configurable: true,
  });
});

describe('heroSearchHandoff', () => {
  it('저장 후 기대한 autoRun으로 소비하면 값을 그대로 돌려주고, 재조회하면 null이다(1회용 불변식)', () => {
    setHeroSearchHandoff({ query: '가성비 좋은 첫차', autoRun: true });
    expect(consumeHeroSearchHandoff(true)).toEqual({ query: '가성비 좋은 첫차', autoRun: true });
    // 같은 값을 다시 읽으면(새로고침·뒤로가기 재현) null — 재실행 방지의 핵심.
    expect(consumeHeroSearchHandoff(true)).toBeNull();
  });

  it('autoRun:false(비로그인 게이트 케이스)도 그대로 왕복한다', () => {
    setHeroSearchHandoff({ query: '4천만원대 전기 SUV', autoRun: false });
    expect(consumeHeroSearchHandoff(false)).toEqual({ query: '4천만원대 전기 SUV', autoRun: false });
  });

  it('내 몫이 아닌 autoRun 값은 소비하지 않고 그대로 둔다(교차 소비 방지)', () => {
    // 로그인 사용자가 제출한 autoRun:true 핸드오프 — ChatAssistant(/ai) 몫이다.
    setHeroSearchHandoff({ query: '7인승 디젤 패밀리카', autoRun: true });
    // 랜딩(HeroSearch)이 autoRun:false를 기대하며 먼저 읽으면 — 내 것이 아니므로 null, 삭제도 안 함.
    expect(consumeHeroSearchHandoff(false)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
    // 나중에 진짜 주인(autoRun:true 기대)이 읽으면 여전히 온전하다.
    expect(consumeHeroSearchHandoff(true)).toEqual({ query: '7인승 디젤 패밀리카', autoRun: true });
  });

  it('내 몫이 아닌 autoRun 값은 소비하지 않고 그대로 둔다(대칭 방향 — autoRun:false를 ChatAssistant가 가로채지 않음)', () => {
    // 비로그인 사용자가 로그인 게이트로 향하며 남긴 autoRun:false 핸드오프 — HeroSearch(랜딩) 몫이다.
    setHeroSearchHandoff({ query: '주행거리 짧은 무사고 세단', autoRun: false });
    // ChatAssistant(/ai)가 autoRun:true를 기대하며 먼저 읽으면 — 내 것이 아니므로 null, 삭제도 안 함.
    expect(consumeHeroSearchHandoff(true)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).not.toBeNull();
    // 나중에 진짜 주인(autoRun:false 기대)이 읽으면 여전히 온전하다.
    expect(consumeHeroSearchHandoff(false)).toEqual({ query: '주행거리 짧은 무사고 세단', autoRun: false });
  });

  it('저장된 값이 없으면 null이다', () => {
    expect(consumeHeroSearchHandoff(true)).toBeNull();
  });

  it('손상된 JSON이 들어있으면 null을 반환하고 항목을 지운다', () => {
    sessionStorage.setItem(STORAGE_KEY, '{not-json');
    expect(consumeHeroSearchHandoff(true)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('모양이 어긋난 값(query 누락 등)은 null을 반환하고 항목을 지운다', () => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ autoRun: true }));
    expect(consumeHeroSearchHandoff(true)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  // 매물 카드(개선 1, 2026-09-01 → 표준 카드 교체) — "AI 시세 진단" 버튼이 listingSummary를 실어
  // 보내면 ChatAssistant가 그대로 왕복해 읽어야 한다. isListingSummary 검증 로직을 이 두 케이스로
  // 고정한다. 타입이 ListingCardData로 바뀌어 필수 필드에 region이 추가되고 imageUrl은 표준 카드의
  // 필드명(image_url)을 그대로 쓴다.
  it('listingSummary가 있으면 그대로 왕복한다', () => {
    const listingSummary = {
      id: 'aaa',
      manufacturer: '기아',
      model: '더 뉴 쏘렌토 UM',
      year: 2019,
      mileage: 69041,
      price: 15620000,
      region: '서울',
      image_url: 'https://example.com/a.jpg',
    };
    setHeroSearchHandoff({ query: '이 매물 시세 알려줘', autoRun: true, listingId: 'aaa', listingSummary });
    expect(consumeHeroSearchHandoff(true)).toEqual({
      query: '이 매물 시세 알려줘',
      autoRun: true,
      listingId: 'aaa',
      listingSummary,
    });
  });

  it('listingSummary의 모양이 어긋나면(필수 필드 누락) null을 반환하고 항목을 지운다', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        query: '이 매물 시세 알려줘',
        autoRun: true,
        listingSummary: { id: 'aaa', manufacturer: '기아' }, // model·year·mileage·price·region 누락
      }),
    );
    expect(consumeHeroSearchHandoff(true)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('listingSummary에 region이 없으면(표준 카드 필수 필드 누락) null을 반환하고 항목을 지운다', () => {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        query: '이 매물 시세 알려줘',
        autoRun: true,
        listingSummary: {
          id: 'aaa',
          manufacturer: '기아',
          model: '더 뉴 쏘렌토 UM',
          year: 2019,
          mileage: 69041,
          price: 15620000,
          // region 누락
        },
      }),
    );
    expect(consumeHeroSearchHandoff(true)).toBeNull();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });
});
