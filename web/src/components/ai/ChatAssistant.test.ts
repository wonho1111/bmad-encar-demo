// buildContext 단위테스트 (Story 13.4 후속 코드리뷰)
//
// 왜 이 파일이 필요한가: 13.4가 되묻기 상한을 **서버가** 강제하도록 옮겼는데(DW-563), 서버가
// 세는 값은 클라이언트가 보낸 `context`의 길이다(`len(context)//2 >= 3`). 즉 이 함수가 몇 턴을
// 실어 보내느냐가 서버 상한이 발동할 수 있느냐를 그대로 결정한다 — MAX_CONTEXT_TURNS를 5 이하로
// 줄이는 순간(토큰 비용 절감 같은 흔한 이유로) 웹에서는 상한이 **영원히 발동하지 않는데**,
// api 테스트는 context 배열을 손으로 만들어 넣으므로 전부 초록으로 남는다.
// 앱(Flutter)은 같은 상수를 app/test/ai_search_test.dart가 이미 고정하고 있다 — 웹만 비어 있었다.
//
// DOM 없이 순수 함수만 부른다(vitest.config.ts 방침: environment=node).
import { describe, expect, it } from 'vitest';

import { buildContext } from './ChatAssistant';

// buildContext(messages: ChatMessage[]) — ChatMessage는 export되지 않지만 구조가 같으면 통과한다.
function msgs(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    role: (i % 2 === 0 ? 'user' : 'assistant') as 'user' | 'assistant',
    content: `메시지 ${i}`,
  }));
}

describe('buildContext', () => {
  it('최근 12턴까지만 실어 보낸다 — 서버 상한(3턴)이 발동할 수 있는 하한을 지킨다', () => {
    const ctx = buildContext(msgs(30));
    // 12 = MAX_CONTEXT_TURNS. 이 수를 6 미만으로 줄이면 서버의 `len(context)//2 >= 3` 강제 폴백이
    // 웹에서 절대 발동하지 않는다(DW-563이 만든 그 상한이 웹에 한해 죽는다).
    expect(ctx).toHaveLength(12);
    expect(ctx.length).toBeGreaterThanOrEqual(6);
    // 잘라내는 쪽은 "오래된 앞부분" — 최신 대화가 남아야 맥락화가 의미를 가진다.
    expect(ctx[ctx.length - 1].content).toBe('메시지 29');
  });

  it('12턴 미만이면 그대로 보낸다', () => {
    expect(buildContext(msgs(4))).toHaveLength(4);
  });

  it('내용이 빈 턴은 제외한다 — 서버 ConversationTurn이 최소 1자를 요구해 422가 난다', () => {
    const ctx = buildContext([
      { role: 'user' as const, content: '패밀리카' },
      { role: 'assistant' as const, content: '   ' },
      { role: 'user' as const, content: 'SUV' },
    ]);
    expect(ctx.map((t) => t.content)).toEqual(['패밀리카', 'SUV']);
  });

  it('각 턴 content는 2000자로 잘린다', () => {
    const ctx = buildContext([{ role: 'user' as const, content: 'ㄱ'.repeat(3000) }]);
    expect(ctx[0].content).toHaveLength(2000);
  });
});

// listing_ids 배선 (멀티턴 매물 참조) — 직전 턴에서 추천한 매물을 두고 "그중 두 번째
// 시세 알려줘"·"그 5개 비교해줘"라고 물으면 에이전트가 재검색만 반복하던 실측 결함의 수정.
// 서버(agent.py)가 "직전에 보여준 매물" 요약 블록을 만들려면 이 id들이 실제로 실려가야 한다.
describe('buildContext — listing_ids 배선', () => {
  const BASE_LISTING = {
    manufacturer: '현대',
    model: '아반떼 AD',
    year: 2017,
    price: 9260000,
    mileage: 106062,
    region: '서울',
  };

  it('매물카드가 있는 assistant 턴은 그 매물 id들을 listing_ids로 싣는다', () => {
    const ctx = buildContext([
      { role: 'user' as const, content: '1000만원 이하 실속형 차 추천해줘' },
      {
        role: 'assistant' as const,
        content: '2건을 찾았어요.',
        listings: [
          { ...BASE_LISTING, id: 'aaa' },
          { ...BASE_LISTING, id: 'bbb' },
        ],
      },
    ]);
    expect(ctx[1].listing_ids).toEqual(['aaa', 'bbb']);
  });

  it('카드는 없고 시세 진단만 있는 assistant 턴은 진단 대상 매물 id 1개를 싣는다', () => {
    const ctx = buildContext([
      { role: 'user' as const, content: '이 매물 시세 알려줘' },
      {
        role: 'assistant' as const,
        content: '시세를 분석했어요.',
        marketDiagnosis: {
          listing: { ...BASE_LISTING, id: 'ccc', fuel: '가솔린', transmission: '자동' as const, displacement: 1600, accident_free: true, accident_status: null },
          criteria: { step: 0, desc: '동일 모델', sample_count: 5 },
          stats: null,
          percentile: null,
          verdict: null,
          verdict_basis: null,
          tabpfn: { price: null, note: '' },
          comps: [],
        },
      },
    ]);
    expect(ctx[1].listing_ids).toEqual(['ccc']);
  });

  it('매물도 진단도 없는 assistant 턴(되묻기 등)은 listing_ids 키 자체가 없다', () => {
    const ctx = buildContext([
      { role: 'user' as const, content: '차 추천해줘' },
      { role: 'assistant' as const, content: '예산을 알려주시겠어요?', clarify: { question: '예산은요?', chips: ['2천만원 이하'] } },
    ]);
    expect(ctx[1]).not.toHaveProperty('listing_ids');
  });

  it('user 턴은 listing_ids를 담지 않는다(서버 스키마도 assistant 전용)', () => {
    const ctx = buildContext([{ role: 'user' as const, content: '3천만원 이하 SUV' }]);
    expect(ctx[0]).not.toHaveProperty('listing_ids');
  });
});

// 이 검사가 **안 보는 것**: 서버가 실제로 그 길이를 상한으로 해석하는지는 여기서 못 본다
// (그건 api/tests/test_graph.py의 상한 테스트 몫이다). 여기가 고정하는 것은 "웹이 서버 상한에
// 도달할 만큼의 턴을 실어 보낸다"는 한쪽 절반뿐이다 — 두 검사가 붙어야 경로가 닫힌다.
