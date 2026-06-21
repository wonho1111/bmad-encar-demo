'use client';

// AI 검색 채팅 컴포넌트 (FR12·FR18·Story 4-7) — 자연어 대화로 매물을 찾는 화면 본문.
//
// 핵심 책임:
//   1) 사용자가 입력한 자연어 질의를 /ai/search로 보내고(answer + 매물카드) 대화에 쌓는다.
//   2) 멀티턴(FR18): 직전 대화를 "클라이언트 상태"(아래 messages)로만 보관하다가, 후속 질의를 보낼 때
//      context로 동봉한다. 서버·DB·localStorage에 저장하지 않는다 → 새로고침하면 대화가 초기화된다(무상태).
//   3) 매물카드는 기존 ListingCard를 재사용(텍스트 7필드, 사진 없음) — 카드 클릭 시 /listings/[id] 상세로 이동.
//
// 왜 클라이언트 컴포넌트인가:
//   대화 상태(messages)·입력값·로딩·에러를 브라우저에서 쥐고 있어야 하고, Supabase 세션 토큰을 꺼내
//   인증 헤더로 보내야 하므로 'use client'가 필요하다(서버 컴포넌트는 상태·이벤트를 못 가진다).
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { searchAi, type ConversationTurn } from '@/lib/api/aiSearch';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import Button from '@/components/ui/Button';

// context 입력 계약(단일 출처: api/docs/ai-demo-queries.md, api/app/schemas/ai.py).
// 서버가 강제하는 한계를 클라이언트에서 미리 지켜 422를 자초하지 않는다.
const MAX_CONTEXT_TURNS = 12; // 최근 12턴만 동봉(초과분 잘라냄)
const MAX_CONTENT_LENGTH = 2000; // 각 턴 content 최대 2000자(초과 시 절단)
const MAX_QUERY_LENGTH = 1000; // 질의 최대 1000자(서버 SearchRequest.query 상한과 동일 — 초과 시 클라에서 미리 차단)

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

export default function ChatAssistant() {
  // 대화 기록 — 클라이언트 상태에만 존재(무상태). 새로고침/이탈 시 사라진다(FR18 의도된 동작).
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const query = input.trim();
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

      // 어시스턴트 답변(텍스트 + 매물카드)을 대화에 추가.
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.answer, listings: result.listings },
      ]);
    } catch (err) {
      // fail-loud: 실패를 조용히 삼키지 않고 한국어로 보여준다(AC5).
      setError(err instanceof Error ? err.message : 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.');
      // 실패하면 방금 낙관적으로 추가한 "사용자 질의 버블"을 되돌린다(롤백). 그러지 않으면
      //   (1) 답 없는 질의가 대화에 남고, (2) 다음 재시도 때 그 질의가 context로 또 실려 중복된다.
      // 입력값도 원래 질의로 복원해 사용자가 곧바로 다시 보낼 수 있게 한다.
      setMessages((prev) => prev.slice(0, -1));
      setInput(query);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-4">
      {/* 대화 기록 영역 */}
      <section className="flex flex-col gap-3" aria-label="AI 대화 기록">
        {messages.length === 0 && !loading ? (
          <p className="text-sm text-zinc-500">
            예: &ldquo;3천만원 이하 흰색 SUV&rdquo;, &ldquo;패밀리카로 무난한 거 추천해줘&rdquo;
          </p>
        ) : (
          messages.map((m, i) => (
            <div key={i} className="flex flex-col gap-2">
              {m.role === 'user' ? (
                // 사용자 말풍선 — 오른쪽 정렬.
                <div className="self-end rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">
                  {m.content}
                </div>
              ) : (
                // 어시스턴트 말풍선 — 답변 텍스트 + (있으면) 매물카드 목록.
                <div className="flex flex-col gap-2">
                  <div className="self-start whitespace-pre-wrap rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800">
                    {m.content}
                  </div>
                  {m.listings && m.listings.length > 0 && (
                    <ul className="flex flex-col gap-2">
                      {m.listings.map((l) => (
                        <li key={l.id}>
                          {/* 매물카드 재사용 — 클릭하면 /listings/[id] 상세로 이동(ListingCard 내장 Link). 사진 없음. */}
                          <ListingCard listing={l} />
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {/* 로딩 표시 — 요청 중인 동안 어시스턴트 자리에 placeholder. */}
        {loading && (
          <div className="self-start rounded-lg border border-zinc-200 px-3 py-2 text-sm text-zinc-500 dark:border-zinc-800">
            검색 중…
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
          className="flex-1 rounded border border-zinc-300 bg-transparent px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-700"
        />
        <Button type="submit" variant="primary" loading={loading} loadingText="검색 중…">
          전송
        </Button>
      </form>
    </div>
  );
}
