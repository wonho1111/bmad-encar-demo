'use client';

// 채팅방 메시지 송수신 + 폴링 (FR20·FR21, Story 5-3) — 채팅방 진입 화면의 "대화 본문".
//
// 핵심 책임:
//   1) 전송(FR21): 입력한 메시지를 chat_messages에 INSERT해 영속 저장하고, 내 화면에 즉시 반영.
//   2) 폴링 수신(FR20·NFR1): 3초마다 그 방의 "새 메시지만" 증분 조회해, 상대가 보낸 메시지를 ≤5초 내 갱신.
//   3) 목록 UI(AC#3): created_at 시간순, 내 메시지(오른쪽)·상대 메시지(왼쪽) 구분. 0건이면 빈 상태.
//
// 왜 클라이언트 컴포넌트인가:
//   대화 상태·입력값·로딩·에러를 브라우저에서 쥐고, setInterval로 주기 조회해야 하므로 'use client'가 필요하다
//   (서버 컴포넌트는 상태·타이머·이벤트를 못 가진다). 메시지의 진짜 출처는 DB이고, 여기 상태는 화면 캐시일 뿐.
//
// 보안: 진입 페이지(서버 컴포넌트)가 RLS로 "내가 이 방 당사자"임을 이미 확인한 뒤 본인 id(myUserId)를 내려준다.
//   전송 시 sender_id=myUserId라야 RLS(insert_participant)를 통과한다. 제3자는 애초에 이 화면에 도달하지 못한다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  fetchMessages,
  sendMessage,
  dedupeById,
  type ChatMessageRow,
} from '@/lib/messages';
import Button from '@/components/ui/Button';
import { CHAT } from '@/lib/constants';

// 폴링 주기 — NFR1 "채팅 폴링 준실시간(3~5초)" 범위의 하단값(체감 응답성↑).
//   증분 조회(gte 커서)+id dedupe라 요청이 겹쳐도 중복 메시지가 안 생기고, cleanup의 cancelled로 유령 요청도 차단.
//   더 빠른 실시간이 필요하면 폴링 대신 Supabase Realtime 구독이 정답(향후 과제).
const POLL_INTERVAL_MS = 3000;

export default function ChatRoomMessages({
  roomId,
  myUserId,
}: {
  roomId: string;
  myUserId: string;
}) {
  // 화면에 보이는 메시지(시간 오름차순). DB가 출처이고 이건 캐시 — 폴링/전송으로 증분 갱신된다.
  const [messages, setMessages] = useState<ChatMessageRow[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true); // 초기 1회 로드 중 표시
  const [sending, setSending] = useState(false); // 전송 중(연타 차단)
  const [error, setError] = useState<string | null>(null); // 전송/조회 에러(한국어)

  // 폴링 증분 커서 = "마지막으로 받은 메시지의 created_at". ref로 둬 setInterval 콜백이
  //   재생성 없이 항상 최신 커서를 참조하게 한다(stale closure 회피 — React 폴링 표준 패턴).
  const cursorRef = useRef<string | null>(null);

  // 받은 메시지들을 기존 목록에 합친다(id dedupe). 커서도 마지막 created_at으로 끌어올린다.
  //   함수형 업데이트(prev=>…)라 인터벌 콜백이 옛 상태를 잡지 않는다.
  const mergeIncoming = useCallback((incoming: ChatMessageRow[]) => {
    if (incoming.length === 0) return;
    setMessages((prev) => dedupeById([...prev, ...incoming]));
    // 증분은 시간 오름차순이라 마지막 원소의 created_at이 가장 최신. 커서를 그쪽으로 전진.
    const lastCreatedAt = incoming[incoming.length - 1].created_at;
    if (!cursorRef.current || lastCreatedAt > cursorRef.current) {
      cursorRef.current = lastCreatedAt;
    }
  }, []);

  // 초기 로드 + 폴링 — roomId가 바뀌면(다른 방 진입) 깨끗이 재시작.
  useEffect(() => {
    let cancelled = false; // unmount/방전환 후 늦게 도착한 응답을 무시하기 위한 플래그
    const supabase = createClient();

    // 초기 1회: 전체 메시지 로드(커서 없음).
    (async () => {
      setLoading(true);
      const res = await fetchMessages(supabase, roomId); // 커서 없음 = 전체
      if (cancelled) return;
      if ('error' in res) {
        setError('메시지를 불러오지 못했습니다. 잠시 후 다시 시도해주세요.');
      } else {
        setMessages(res.messages);
        // 마지막 메시지의 created_at을 폴링 시작 커서로(없으면 null = 다음 폴링은 전체부터).
        cursorRef.current = res.messages.at(-1)?.created_at ?? null;
      }
      setLoading(false);
    })();

    // 폴링: 3초마다 커서 "뒤"의 새 메시지만 증분 조회 → id dedupe로 합침.
    const timer = setInterval(async () => {
      const res = await fetchMessages(supabase, roomId, cursorRef.current);
      if (cancelled) return;
      if ('error' in res) return; // 일시 조회 실패는 조용히 넘기고 다음 주기에 재시도(폴링은 계속).
      mergeIncoming(res.messages);
    }, POLL_INTERVAL_MS);

    // cleanup: 인터벌 정리(메모리 누수·유령 요청 방지 — AC#5). 방 전환/이탈/언마운트 시 호출.
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [roomId, mergeIncoming]);

  // 전송 — 빈값/전송중이면 무시. 성공 시 낙관적 반영 + 커서 전진, 실패 시 한국어 에러 + 입력 복원.
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = input.trim();
    if (body === '' || sending) return; // 빈 메시지·연타 차단(클라 1차).

    setError(null);
    setSending(true);
    setInput(''); // 즉시 입력창 비움(피드백). 실패하면 아래에서 복원.
    try {
      const supabase = createClient();
      const res = await sendMessage(supabase, roomId, myUserId, body);
      if ('error' in res) {
        setError(res.error);
        setInput(body); // 실패 → 사용자가 곧바로 다시 보낼 수 있게 입력 복원.
        return;
      }
      // 성공: 저장된 행을 즉시 목록에 반영(낙관적). 폴링이 같은 행을 또 가져와도 id dedupe로 중복 없음.
      mergeIncoming([res.message]);
    } catch (err) {
      console.error('[chat/room] 메시지 전송 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      setInput(body);
    } finally {
      setSending(false);
    }
  }

  return (
    <section aria-label="메시지" className="flex flex-col gap-4">
      {/* 메시지 목록 — 시간 오름차순. 내 메시지 오른쪽·상대 왼쪽으로 구분(AC#3). */}
      <ul className="flex min-h-40 flex-col gap-2 rounded border border-zinc-200 p-4 dark:border-zinc-800">
        {loading ? (
          <li className="text-center text-sm text-zinc-500">메시지를 불러오는 중…</li>
        ) : messages.length === 0 ? (
          // 첫 대화 빈 상태(AC#3).
          <li className="text-center text-sm text-zinc-500">
            아직 주고받은 메시지가 없습니다. 먼저 인사를 건네보세요.
          </li>
        ) : (
          messages.map((m) => {
            const mine = m.sender_id === myUserId;
            return (
              <li key={m.id} className={mine ? 'flex justify-end' : 'flex justify-start'}>
                {/* whitespace-pre-wrap: 줄바꿈 보존. 본문은 사용자 입력이라 React 기본 이스케이프로 XSS 안전. */}
                <span
                  className={
                    mine
                      ? 'max-w-[80%] whitespace-pre-wrap rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900'
                      : 'max-w-[80%] whitespace-pre-wrap rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800'
                  }
                >
                  {m.body}
                </span>
              </li>
            );
          })
        )}
      </ul>

      {/* 에러 안내 — 조용한 실패 금지(fail-loud). */}
      {error && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {error}
        </p>
      )}

      {/* 입력 폼 — Enter 또는 전송 버튼으로 제출. 전송 중엔 비활성(연타 차단). */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="메시지를 입력하세요"
          aria-label="메시지 입력"
          disabled={sending}
          maxLength={CHAT.MESSAGE_MAX_LENGTH} // 길이 상한 1차 방어(기술부채 #8). 전송 가드·DB CHECK와 동일 값.
          className="flex-1 rounded border border-zinc-300 bg-transparent px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-700"
        />
        <Button type="submit" variant="primary" loading={sending} loadingText="전송 중…">
          전송
        </Button>
      </form>
    </section>
  );
}
