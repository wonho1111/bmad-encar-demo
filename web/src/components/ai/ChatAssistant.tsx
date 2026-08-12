'use client';

// AI 검색 채팅 컴포넌트 (FR12·FR18·Story 4-7) — 자연어 대화로 매물을 찾는 화면 본문.
//
// 핵심 책임:
//   1) 사용자가 입력한 자연어 질의를 /ai/search로 보내고(answer + 매물카드) 대화에 쌓는다.
//   2) 멀티턴(FR18): 직전 대화를 "클라이언트 상태"(아래 messages)로만 보관하다가, 후속 질의를 보낼 때
//      context로 동봉한다. 서버·DB·localStorage에 저장하지 않는다 → 새로고침하면 대화가 초기화된다(무상태).
//   3) 매물카드는 기존 ListingCard를 재사용 — 카드 클릭 시 /listings/[id] 상세로 이동.
//      대표사진·"N장" 배지·"사진 준비중" 플레이스홀더는 ListingCard(9.4)가 그대로 처리한다.
//      (Story 9.6 정정: 전엔 "사진 없음"이라고 적혀 있었다 — api가 image_url을 못 채워서 그랬는데,
//       9.6이 image_path를 붙이고 aiSearch.ts가 공개 URL로 바꾸면서 사실이 아니게 됐다.
//       이 파일의 렌더 코드는 한 줄도 바뀌지 않았다 — 값이 채워지자 카드가 알아서 그린다.)
//
// 왜 클라이언트 컴포넌트인가:
//   대화 상태(messages)·입력값·로딩·에러를 브라우저에서 쥐고 있어야 하고, Supabase 세션 토큰을 꺼내
//   인증 헤더로 보내야 하므로 'use client'가 필요하다(서버 컴포넌트는 상태·이벤트를 못 가진다).
import { useEffect, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { searchAi, type ConversationTurn } from '@/lib/api/aiSearch';
import { consumeHeroSearchHandoff } from '@/lib/heroSearchHandoff';
import { buildWishedIdSet } from '@/lib/wishlist';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import Button from '@/components/ui/Button';

// context 입력 계약(단일 출처: api/docs/ai-demo-queries.md, api/app/schemas/ai.py).
// 서버가 강제하는 한계를 클라이언트에서 미리 지켜 422를 자초하지 않는다.
const MAX_CONTEXT_TURNS = 12; // 최근 12턴만 동봉(초과분 잘라냄)
const MAX_CONTENT_LENGTH = 2000; // 각 턴 content 최대 2000자(초과 시 절단)
const MAX_QUERY_LENGTH = 1000; // 질의 최대 1000자(서버 SearchRequest.query 상한과 동일 — 초과 시 클라에서 미리 차단)

// 이 시간을 넘기면 "서버를 깨우는 중"으로 문구를 바꾼다(대장 DW-543).
// 2.5초인 이유: 깨어 있는 서버의 실측 응답이 0.065초라 정상 검색은 여기 도달하지 못하고,
// 콜드스타트 실측 4.4초보다는 충분히 짧아 기다리는 사람이 이유를 일찍 안다.
const SLOW_SEARCH_NOTICE_MS = 2500;

// 화면에 쌓이는 대화 한 줄. assistant 턴만 매물카드(listings)를 가질 수 있다.
type ChatMessage = {
  role: 'user' | 'assistant';
  content: string; // user=질의, assistant=answer 텍스트
  listings?: ListingCardData[]; // assistant 답변에 딸린 매물카드(없으면 0건)
};

/**
 * 화면 대화(messages)를 서버로 보낼 context(턴 배열)로 직렬화한다.
 *   - 매물카드(listings)는 제외하고 role/content만 보낸다(서버 스키마 = role+content).
 *   - 최근 MAX_CONTEXT_TURNS개만 — 대화가 길어져도 12턴 초과로 422 나지 않게.
 *   - 각 content는 MAX_CONTENT_LENGTH로 안전 절단.
 * 순수 함수로 분리해 동작을 명확히 하고(테스트·추론 용이), 무상태 직렬화임을 드러낸다.
 */
export function buildContext(messages: ChatMessage[]): ConversationTurn[] {
  return messages
    // 내용이 빈(공백뿐인) 턴은 먼저 제거한다. 서버 ConversationTurn.content는 최소 1자를 요구하므로,
    // 예컨대 답변이 비어 있던 assistant 턴(content="")을 그대로 동봉하면 다음 질의가 통째로 422로 거절된다
    // (멀쩡한 질의인데 "질문 형식이 올바르지 않습니다"가 떠 대화가 막히는 오염). 빈 턴을 빼 이를 막는다.
    .filter((m) => m.content.trim() !== '')
    .slice(-MAX_CONTEXT_TURNS) // 최근 N턴
    .map((m) => ({
      role: m.role,
      content: m.content.slice(0, MAX_CONTENT_LENGTH),
    }));
}

export default function ChatAssistant({ authed }: { authed: boolean }) {
  // 대화 기록 — 클라이언트 상태에만 존재(무상태). 새로고침/이탈 시 사라진다(FR18 의도된 동작).
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // 이 대화에 등장한 매물 중 "내가 이미 찜한" id 집합 — 카드 하트의 초기 상태로만 쓴다.
  //   /search·랜딩은 **서버**가 fetchWishedListingIds로 같은 값을 구해 카드에 주입하지만,
  //   AI 결과 매물은 브라우저가 /ai/search 응답으로 받으므로 그 자리가 없다. 그래서 여기서
  //   브라우저 Supabase 클라이언트로 한 번 더 구한다(조회 실패는 "찜 0건"과 같게 처리 — 오버레이
  //   실패로 답변 렌더 전체를 막지 않는다, @/lib/wishlist의 house 방침과 동일).
  const [wishedIds, setWishedIds] = useState<Set<string>>(new Set());
  // 검색이 SLOW_SEARCH_NOTICE_MS를 넘겼는지 — 로딩 문구를 "서버를 깨우는 중"으로 바꾼다(DW-543).
  const [slowNotice, setSlowNotice] = useState(false);

  // 실제 검색 실행 — handleSubmit(폼 제출)과 아래 마운트 핸드오프 소비(히어로에서 넘어온 자동
  // 실행) 둘 다 여기로 합류한다(spec-11-3 Code Map). 분리 전엔 handleSubmit 안에 있던 로직 그대로다
  // — 동작은 바뀌지 않고 호출 경로만 하나 더 생겼다.
  async function runSearch(query: string) {
    if (query === '' || loading) return; // 빈 질의·중복 전송 차단(클라 1차 검증).

    // 질의가 서버 상한(1000자)을 넘으면, 그대로 보내봐야 422가 떠 "질문 형식이 올바르지 않습니다"라는
    // 원인 모를 안내만 받는다. 길이 초과를 클라에서 먼저 잡아 "왜 막혔는지"를 또렷이 알려준다(fail-loud).
    if (query.length > MAX_QUERY_LENGTH) {
      setError(`질문이 너무 깁니다. ${MAX_QUERY_LENGTH}자 이내로 줄여 다시 시도해주세요.`);
      return;
    }

    setError(null);
    // 이번 질의 직전까지의 대화를 context로(중복 금지 — 방금 입력한 query는 context가 아니라 query로 보낸다).
    const context = buildContext(messages);
    // 사용자 턴을 먼저 화면에 반영(즉시 피드백).
    setMessages((prev) => [...prev, { role: 'user', content: query }]);
    setInput('');
    setLoading(true);

    // "서버를 깨우는 중" 문구 타이머(DW-543). **effect가 아니라 여기서 건다** — effect에 두면
    // 콜백 안의 setState가 `react-hooks/set-state-in-effect`에 걸린다(실측: lint 에러 1건).
    // 이벤트 핸들러에서 거는 건 규칙이 다루는 대상이 아니고, 위 조기 반환(빈 질의·길이 초과)은
    // 전부 이 줄보다 **앞에** 있으므로 "걸어놓고 안 지우는" 경로가 생기지 않는다.
    const slowTimer = setTimeout(() => setSlowNotice(true), SLOW_SEARCH_NOTICE_MS);

    try {
      // Supabase 세션에서 access_token을 꺼내 인증 헤더로 보낸다(매 요청 getSession으로 최신 토큰 확보 — 만료 자동 갱신).
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      const result = await searchAi({
        query,
        context: context.length > 0 ? context : undefined,
        accessToken: session?.access_token,
      });

      // 찜 오버레이 — 카드가 **마운트되기 전에** 구한다. WishButton은 initialWished를 마운트
      // 시점에 한 번만 읽으므로(이후 prop 변화는 무시), 카드를 먼저 그리고 나중에 채우면 이미
      // 찜한 매물이 계속 빈 하트로 남는다.
      if (session?.user && result.listings.length > 0) {
        const { data, error: wishError } = await supabase
          .from('wishlists')
          .select('listing_id')
          .eq('user_id', session.user.id)
          .in(
            'listing_id',
            result.listings.map((l) => l.id),
          );
        if (wishError || !data) {
          console.error('[ai] 찜 오버레이 조회 실패:', wishError);
        } else {
          const found = buildWishedIdSet(data);
          setWishedIds((prev) => new Set([...prev, ...found]));
        }
      }

      // 어시스턴트 답변(텍스트 + 매물카드)을 대화에 추가.
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, listings: result.listings },
      ]);
    } catch (err) {
      // 화면엔 한국어 안내만 뜨므로(AC5), 원인은 콘솔에 남겨 재현 없이도 진단할 수 있게 한다(DW-659).
      console.error('[ai] 검색 실패:', { query, err });
      // fail-loud: 실패를 조용히 삼키지 않고 한국어로 보여준다(AC5).
      setError(err instanceof Error ? err.message : 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.');
      // 실패하면 방금 낙관적으로 추가한 "사용자 질의 버블"을 되돌린다(롤백). 그러지 않으면
      //   (1) 답 없는 질의가 대화에 남고, (2) 다음 재시도 때 그 질의가 context로 또 실려 중복된다.
      // 입력값도 원래 질의로 복원해 사용자가 곧바로 다시 보낼 수 있게 한다.
      setMessages((prev) => prev.slice(0, -1));
      setInput(query);
    } finally {
      // finally는 성공·에러 어느 경로에서도 돈다 — 타이머 해제와 문구 초기화를 여기 한 곳에 둔다.
      clearTimeout(slowTimer);
      setSlowNotice(false);
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await runSearch(input.trim());
  }

  // 마운트 1회: 랜딩 히어로에서 로그인 사용자가 제출한 핸드오프를 소비한다(읽고 즉시 삭제 —
  // heroSearchHandoff.ts 단일 출처). autoRun===true일 때만 1회 자동 실행한다.
  //   왜 마운트에서만 읽고 지우나: 이 화면은 무상태(FR18, 새로고침=대화 초기화)라, 여기서 지우지
  //   않으면 사용자가 자동 실행 직후 새로고침할 때 같은 질의가 다시 자동 실행돼 AI 검색 비용이
  //   중복 과금된다(에픽이 명시적으로 경고한 위험) — consumeHeroSearchHandoff의 "읽는 즉시 삭제"가
  //   이걸 막는다.
  //   queueMicrotask + cleanup 없음(WishButton.tsx와 동일 관례, HeroSearch.tsx 마운트 effect 참고):
  //   setTimeout으로 지연시키면 React Strict Mode의 (실행→cleanup→실행) 왕복에서 cleanup이 예약을
  //   취소해 자동 실행이 영영 안 일어나는 조용한 버그가 난다. queueMicrotask는 취소 수단이 없어
  //   2회차 호출은 이미 비워진 storage를 보고 그냥 return하고, 1회차가 예약한 microtask만 실행된다.
  //   runSearch를 deps에서 뺀 이유: 이 effect는 마운트 시 1회만 실행돼야 하고, sessionStorage 자체가
  //   1회용(consume이 지움)이라 이후 재실행돼도 handoff가 없어 아무 일도 안 한다 — 의도적 생략.
  useEffect(() => {
    // autoRun:true만 내 몫이다 — autoRun:false(비로그인 게이트 복원용)는 HeroSearch(랜딩) 몫이라
    // 여기선 손대지 않고 그대로 둔다(11-3 코드리뷰 지적: 무조건 소비하면 랜딩이 나중에 못 읽는다).
    const handoff = consumeHeroSearchHandoff(true);
    if (!handoff) return;
    queueMicrotask(() => {
      void runSearch(handoff.query);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* 대화 기록 영역 */}
      <section className="flex flex-col gap-3" aria-label="AI 대화 기록">
        {messages.length === 0 && !loading ? (
          <p className="text-sm text-ink-muted">
            예: &ldquo;3천만원 이하 흰색 SUV&rdquo;, &ldquo;패밀리카로 무난한 거 추천해줘&rdquo;
          </p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className="flex flex-col gap-2">
              {m.role === 'user' ? (
                // 사용자 말풍선 — 오른쪽 정렬.
                <div className="self-end rounded-lg bg-brand-petrol px-3 py-2 text-sm text-surface-base">
                  {m.content}
                </div>
              ) : (
                // 어시스턴트 말풍선 — 답변 텍스트 + (있으면) 매물카드 목록.
                <div className="flex flex-col gap-2">
                  <div className="self-start whitespace-pre-wrap rounded-lg border border-border-hairline px-3 py-2 text-sm">
                    {m.content}
                  </div>
                  {m.listings && m.listings.length > 0 && (
                    // ✎ 2026-08-13 2차 지적 #5("AI채팅 매물카드가 너무 크게 나온다") — 세로 1열에서
                    //   ≥640px 2열로 바꾼다. 예전엔 카드가 대화 폭(max-w-3xl ≈ 768px)을 통째로 차지해
                    //   사진 하나가 430px 높이로 그려졌다 — 카드 한 장이 화면을 덮어 "몇 건 찾았는지"가
                    //   안 보였다. 2열이면 카드 폭이 /search 카드와 비슷한 자리로 내려온다.
                    //   ⚠️ 공용 ResponsiveGrid를 쓰지 않는다: 그건 **뷰포트** 폭(640/1100)으로 열수를
                    //   가르는데, 여기 컨테이너는 뷰포트가 아니라 768px 고정 대화 칼럼이라 1100px
                    //   구간에서 4열이 되어 카드가 180px로 뭉개진다(그리드 규칙이 실제 폭과 어긋난다).
                    <ul className="grid gap-3 sm:grid-cols-2">
                      {m.listings.map((l) => (
                        <li key={l.id}>
                          {/* 매물카드 재사용 — 클릭하면 /listings/[id] 상세로 이동(ListingCard 내장 Link).
                              ⚠️ `authed`·`wished`를 반드시 넘긴다(2026-07-29 버그 수정): 안 넘기면
                              ListingCard 기본값 `authed=false`가 걸려, **로그인 상태인데도** 하트를
                              누르면 찜이 저장되는 대신 로그인 화면으로 튕겼다(/search·랜딩은 넘기고
                              AI 결과만 빠져 있었다). */}
                          <ListingCard listing={l} authed={authed} wished={wishedIds.has(l.id)} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {/* 로딩 표시 — 요청 중인 동안 어시스턴트 자리에 placeholder.
            오래 걸리면(SLOW_SEARCH_NOTICE_MS) 문구를 바꿔 **왜** 기다리는지 알린다(대장 DW-543).
            근거는 추측이 아니라 실측이다: AI 서버(Cloud Run)가 쉬고 있으면 깨어나는 데 4.4초,
            깨어난 뒤엔 0.065초다. 즉 첫 검색만 느리고 그 뒤론 빠른데, 화면이 "검색 중…"만 계속
            보여주면 사용자는 서비스가 느린 줄 안다. 고치는 대신 정직하게 말하는 쪽을 먼저 한다
            — 상시 대기(최소 인스턴스 1)는 상시 비용이라 제품 결정이다. */}
        {loading && (
          <div
            role="status"
            className="self-start rounded-lg border border-border-hairline px-3 py-2 text-sm text-ink-muted"
          >
            {slowNotice ? 'AI 서버를 깨우는 중이에요. 첫 검색은 몇 초 걸릴 수 있어요…' : '검색 중…'}
          </div>
        )}
      </section>

      {/* 에러 안내 — 조용한 실패 금지(fail-loud). */}
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      {/* 입력 폼 — Enter 또는 전송 버튼으로 제출. 로딩 중엔 비활성(연타 차단). */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="찾으시는 차를 자연어로 입력하세요"
          aria-label="AI 검색 질의 입력"
          disabled={loading}
          // #84 수정 — 390px에서 실측해 확정(원래 가설이었던 min-w-0 단독으로는 재현이 그대로였다.
          // 실제 원인: <main>이 이 페이지에서 max-w-3xl + mx-auto인데, mx-auto(좌우 auto 마진)는
          // 부모(<body class="flex flex-col">)의 stretch를 깨고 자기 content의 "선호 폭"만큼만
          // 차지한다(centering) — 그 선호 폭 계산(max-content)은 flex-basis:0%(=flex-1)로 렌더될
          // 실제 폭과 무관하게 <input>의 **기본 size=20** 힌트를 그대로 반영해 폼 행이 354px로
          // 잡히고 main이 402px(354+p-6 48)까지 넓어졌다. min-w-0(flex-shrink 하한 해제)는 "실제
          // 배치된 뒤" 줄어드는 것만 도와줄 뿐 이 max-content 계산엔 관여하지 않아 효과가 없었다.
          // size={1}로 그 기본 힌트 자체를 줄이면 main의 선호 폭이 390 밑으로 내려가 오버플로가
          // 사라진다(실측: main 402px→390px). flex-1이 이미 실제 렌더 폭을 결정하므로 size는
          // 화면에 보이는 입력창 크기에 영향이 없다(글자 수 제한도 아님 — maxLength와 무관).
          size={1}
          className="min-w-0 flex-1 rounded border border-border-hairline bg-transparent px-3 py-2 text-sm disabled:opacity-50"
        />
        <Button type="submit" variant="primary" loading={loading} loadingText="검색 중…">
          전송
        </Button>
      </form>
    </div>
  );
}
