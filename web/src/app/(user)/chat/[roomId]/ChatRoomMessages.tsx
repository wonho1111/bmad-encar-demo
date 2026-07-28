'use client';

// 채팅방 메시지 송수신 + 실시간 구독 (FR20·FR21, Story 5-3 → 12.3 폴링 제거) — 채팅방 진입 화면의 "대화 본문".
//
// 핵심 책임:
//   1) 전송(FR21): 입력한 메시지를 chat_messages에 client_message_id(멱등키, 0022)와 함께 INSERT하고,
//      전송 즉시 pending 버블로 보여주다가 서버 확정 시 실제 행으로 교체한다(UX-DR15).
//   2) 실시간 수신(FR20·NFR1, Story 12.3): `chat:room:{roomId}` private 채널을 구독해 상대의 INSERT를
//      폴링 없이 즉시 반영한다 — 0023이 놓은 Broadcast+RLS 토대를 이 화면이 처음 소비한다.
//   3) 목록 UI(AC#3): created_at 시간순, 내 메시지(오른쪽)·상대 메시지(왼쪽) 구분. 0건이면 빈 상태.
//
// 왜 클라이언트 컴포넌트인가:
//   대화 상태·입력값·로딩·에러·pending 버블을 브라우저에서 쥐고 Realtime 채널을 구독해야 하므로
//   'use client'가 필요하다(서버 컴포넌트는 상태·구독·이벤트를 못 가진다). 메시지의 진짜 출처는 DB이고,
//   여기 상태는 화면 캐시일 뿐.
//
// 보안: 진입 페이지(서버 컴포넌트)가 RLS로 "내가 이 방 당사자"임을 이미 확인한 뒤 본인 id(myUserId)를
//   내려준다. 전송 시 sender_id=myUserId라야 RLS(insert_participant)를 통과한다. 구독 인가는
//   realtime.messages RLS(0023)가 같은 당사자 조건으로 별도 강제한다(docs/conventions.md §12) —
//   제3자는 애초에 이 화면에도, 방송 구독에도 도달하지 못한다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import {
  fetchMessages,
  sendMessage,
  dedupeById,
  reuseFailedKey,
  type ChatMessageRow,
  type FailedSend,
} from '@/lib/messages';
import Button from '@/components/ui/Button';
import { CHAT } from '@/lib/constants';

// 구독 토픽 형식 — 0023의 트리거·RLS 리터럴('chat:room:' || room_id::text)과 문자 그대로 동일해야
// 한다(docs/conventions.md §12). 한쪽만 바뀌면 방송은 계속 나가는데 구독만 조용히 끊기거나, 반대로
// 방 없는 토픽이 열리는 식으로 어긋난다.
function roomTopic(roomId: string) {
  return `chat:room:${roomId}`;
}

// 전송 중인 낙관적 메시지 1건 — handleSubmit의 sending 가드가 동시 다건 전송을 막으므로 배열이 아니라
// 단일 값으로 충분하다(Always 절).
type PendingMessage = {
  clientMessageId: string;
  body: string;
};

// 실패한 멱등키를 재사용할 수 있는 시간 창. 재사용은 "방금 실패한 그 전송을 다시 보내는 것"에만
// 유효하다 — 창이 없으면, 서버엔 저장됐지만 방송도 응답도 못 받은 키가 무기한 남아 있다가 한참 뒤
// 사용자가 우연히 같은 본문("ㅇㅇ" 같은 짧은 답이 실제 시드 데이터에 있다)을 보낼 때 그 키가 재사용돼
// 23505 → 옛 행으로 수렴하고, 새 메시지는 조용히 전송되지 않는다(코드리뷰 patch, medium).
const FAILED_KEY_REUSE_WINDOW_MS = 60_000;

export default function ChatRoomMessages({
  roomId,
  myUserId,
}: {
  roomId: string;
  myUserId: string;
}) {
  // 화면에 보이는 메시지(시간 오름차순). DB가 출처이고 이건 캐시 — 초기 로드·실시간 구독으로 갱신된다.
  const [messages, setMessages] = useState<ChatMessageRow[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(true); // 초기 1회 로드 중 표시
  const [sending, setSending] = useState(false); // 전송 중(연타 차단)
  const [error, setError] = useState<string | null>(null); // 전송 에러(한국어) — 다음 전송 때 지워진다
  // 실시간 연결 상태는 error와 수명이 다르다 — 전송 에러는 다음 전송 때 지워져야 하지만, 연결이
  // 끊긴 사실은 다시 붙을 때까지 남아 있어야 한다. 한 칸을 같이 쓰면 handleSubmit의 setError(null)이
  // 구독 실패 경고를 지워버려, 폴링도 없는 상태에서 사용자가 "정상"이라 믿게 된다(코드리뷰 patch, medium).
  const [realtimeError, setRealtimeError] = useState<string | null>(null);
  // 초기 로드 실패도 error와 수명이 다르다(코드리뷰 patch 2차, medium) — 폴링이 있을 때는 3초 뒤
  // 재조회가 알아서 복구했지만 지금은 재조회 자체가 없다. 그런데 handleSubmit 첫 줄의 setError(null)이
  // 이 문구까지 지우므로, 사용자가 메시지를 한 번 보내는 순간 "과거 대화를 못 불러왔다"는 사실이
  // 화면에서 사라진다 — 남은 화면은 "대화가 원래 없던 방"과 구별되지 않는다.
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingMessage | null>(null); // 낙관적 pending 버블(UX-DR15)

  // pending의 client_message_id를 ref로도 들고 있다 — 실시간 구독 콜백(아래 useEffect에서 방 진입 시
  // 한 번만 배선)이 stale closure 없이 "지금" pending과 방금 도착한 행이 같은 전송인지 비교할 수 있게
  // 한다(React state는 클로저에 캡처된 시점 값이라 이펙트를 매 렌더 재배선하지 않는 한 최신값이 아니다).
  const pendingIdRef = useRef<string | null>(null);
  const setPendingMessage = useCallback((next: PendingMessage | null) => {
    pendingIdRef.current = next?.clientMessageId ?? null;
    setPending(next);
  }, []);

  // 직전에 실패한 전송의 (키, 본문) — 실패 후 사용자가 "입력값을 바꾸지 않고" 다시 제출하면 같은
  // client_message_id를 재사용해야 멱등 보호(FR41)가 실제로 발동한다(코드리뷰 patch, high). 이 앱엔
  // 자동 재전송이 없고 유일한 재전송 경로가 "실패 → 입력 복원 → 사용자가 다시 전송 클릭"이므로, 매번
  // 새 UUID를 만들면 서버엔 이미 저장됐는데 응답만 유실된 경우 재전송이 새 키로 들어가 중복 메시지가
  // 실제로 쌓일 수 있다. 사용자가 입력값을 고쳐서 보내면 그건 새 메시지이므로 새 키를 만든다.
  const lastFailedRef = useRef<FailedSend | null>(null);

  // 이 방에서 "실제로 목록에 올라온" 행들의 client_message_id 모음. 전송이 실패로 돌아왔는데 그 키의
  // 행이 이미 여기 있으면 = 서버엔 저장됐고 브로드캐스트 에코까지 도착한 것 → 실패로 알리면 안 된다
  // (화면엔 그 메시지가 보이는데 "보내지 못했습니다"가 함께 뜨는 모순, 코드리뷰 patch, medium).
  const landedKeysRef = useRef<Set<string>>(new Set());

  // 전송 응답을 기다리는 동안 방이 바뀔 수 있다(리마운트 없는 client-side 네비게이션) — 그때 도착한
  // 응답을 그대로 반영하면 A방의 메시지가 B방 목록에 섞이고 A방 입력값이 B방 입력창에 복원된다.
  // 초기 로드가 병합으로 바뀌면서(이전엔 통째 덮어쓰기라 잔상이 지워졌다) 이 잔상이 남게 됐다.
  const roomIdRef = useRef(roomId);

  // 받은 메시지들을 기존 목록에 합친다(id dedupe + created_at,id 정렬) — 초기 로드·전송 확정·실시간
  // 방송 셋 다 이 경로로 합류한다(Always: "도착 순서가 아니라 정렬 결과로 렌더").
  const mergeIncoming = useCallback((incoming: ChatMessageRow[]) => {
    if (incoming.length === 0) return;
    for (const m of incoming) {
      if (m.client_message_id) landedKeysRef.current.add(m.client_message_id);
    }
    setMessages((prev) => dedupeById([...prev, ...incoming]));
  }, []);

  // 초기 1회 전체 로드 + 실시간 구독 배선 — roomId가 바뀌면(다른 방 진입) 깨끗이 재시작.
  useEffect(() => {
    let cancelled = false; // unmount/방전환 후 늦게 도착한 응답·이벤트를 무시하기 위한 플래그
    const supabase = createClient();
    roomIdRef.current = roomId; // 전송 중 방이 바뀌었는지 판별할 기준(아래 handleSubmit 가드).

    // 초기 1회: 전체 메시지 로드(커서 없음) — 구독 이전 과거 메시지를 보여줄 유일한 경로(Always).
    // 그 이후 주기 재조회는 없다 — 상대 메시지는 아래 실시간 구독이 담당한다.
    (async () => {
      // roomId가 바뀌는 것은 리마운트 없이 다른 방으로 client-side 네비게이션한 경우도 포함한다
      // (React가 같은 컴포넌트 인스턴스를 재사용) — messages/loading뿐 아니라 이전 방의 pending
      // 버블·에러 문구·입력값·전송 상태도 함께 지워야 A방의 잔상이 B방 화면에 잠깐 보이지 않는다
      // (코드리뷰 patch, medium). 이 async 콜백 안(useEffect 바디 최상위가 아니라)에서 호출해야
      // `react-hooks/set-state-in-effect` 규칙(effect 바디 직접 setState 금지)에 걸리지 않는다.
      setMessages([]);
      setError(null);
      setLoadError(null);
      setRealtimeError(null);
      setInput('');
      setSending(false);
      setPendingMessage(null);
      lastFailedRef.current = null;
      landedKeysRef.current = new Set();

      setLoading(true);
      const res = await fetchMessages(supabase, roomId);
      if (cancelled) return;
      if ('error' in res) {
        setLoadError('과거 대화를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.');
      } else {
        // 병합(mergeIncoming)으로 반영한다 — 통째로 덮어쓰면(setMessages(res.messages)), 이 초기
        // 로드보다 실시간 방송이 먼저 도착해 화면에 올라간 메시지(자기가 막 보낸 것 포함)가 뒤늦게
        // 끝난 초기 로드에 지워지는 레이스가 있었다(코드리뷰 patch, medium — 다른 모든 갱신 경로는
        // 이미 병합을 거치는데 이 자리만 예외였다). 같은 함수를 쓰므로 landedKeys 기록도 함께 된다.
        mergeIncoming(res.messages);
      }
      setLoading(false);
    })();

    // private 채널 구독 — 방송 payload의 record(INSERT 신규 행)를 기존 mergeIncoming에 그대로
    // 합류시킨다(Always). 같은 client_message_id를 가진 pending이 있으면 "브로드캐스트 에코"로 보고
    // 확정한다(Design Notes — 자기 응답과 에코 중 먼저 도착하는 쪽을 따름).
    const channel = supabase.channel(roomTopic(roomId), { config: { private: true } });
    channel.on('broadcast', { event: 'INSERT' }, (message) => {
      // 방 전환/언마운트 후 늦게 도착한 이벤트는 무시한다(코드리뷰 patch, medium) — 이 콜백은
      // cleanup에서 채널 자체를 제거하지만, 제거가 완료되기 전에 이미 in-flight인 이벤트가 있을 수
      // 있어 다른 경로와 동일하게 cancelled를 확인한다.
      if (cancelled) return;
      const record = (message.payload as { record?: ChatMessageRow } | undefined)?.record;
      if (!record) return;
      mergeIncoming([record]);
      if (pendingIdRef.current && record.client_message_id === pendingIdRef.current) {
        setPendingMessage(null);
      }
      // 실패 응답이 에코보다 **먼저** 온 경우의 뒷정리(코드리뷰 patch 2차, low). 아래 handleSubmit의
      // landedKeys 검사는 "에코가 먼저 도착한" 순서만 구제한다 — 반대 순서(응답 실패 → 그 다음 에코
      // 도착)에서는 이미 "보내지 못했습니다" + 입력 복원이 떠 있는데 같은 메시지가 목록에도 올라와
      // 모순된 화면이 남는다. 그 행이 실제로 저장됐다는 증거가 방금 도착했으므로 실패 표시를 거둔다.
      const failed = lastFailedRef.current;
      if (failed && record.client_message_id === failed.clientMessageId) {
        lastFailedRef.current = null;
        setError(null);
        // 복원해둔 입력값을 그대로 두고 있을 때만 비운다 — 사용자가 이미 고쳐 쓰고 있으면 건드리지 않는다.
        setInput((current) => (current === failed.body ? '' : current));
      }
    });

    // 구독 전에 현재 세션 access token으로 setAuth — 0023의 공식 Broadcast Authorization 패턴
    // (realtime.messages RLS가 이 토큰의 auth.uid()로 당사자 여부를 본다, docs/conventions.md §12).
    // 세션이 아직 없으면(이례적 — 이 화면은 로그인 뒤에만 도달) setAuth 없이 구독을 시도해 RLS가
    // 자연스럽게 거부하게 둔다(조용히 건너뛰지 않음 — 아래 subscribe 콜백이 실패를 화면에도 남긴다).
    // 구독이 실제로 열린 적이 있는지 / 그 뒤 한 번이라도 끊긴 적이 있는지. 방마다 새로 시작해야 하므로
    // ref가 아니라 이 이펙트의 지역 변수로 둔다(방 전환 시 이펙트가 다시 돌면서 자동으로 초기화).
    let initialSyncDone = false;
    let everDropped = false;

    (async () => {
      try {
        const {
          data: { session },
        } = await supabase.auth.getSession();
        if (cancelled) return;
        if (session?.access_token) {
          await supabase.realtime.setAuth(session.access_token);
        }
        if (cancelled) return;
        channel.subscribe((status, err) => {
          if (cancelled) return;
          // 조용한 실패 금지(fail-loud, 이 파일의 다른 모든 에러 경로와 동일 원칙) — 콘솔 로그만
          // 남기면 화면상으로는 아무 일도 없었던 것처럼 보인다. 재연결 로직(12.4 범위)까지는
          // 만들지 않되, 최소한 사용자에게 보이게는 한다.
          //
          // CLOSED도 함께 본다(코드리뷰 patch, medium): phoenix의 onClose 훅은 rejoinTimer를 끄고
          // 소켓에서 채널을 떼어낸다(@supabase/phoenix `assets/js/phoenix/channel.js`의 onClose →
          // `rejoinTimer.reset()` + `socket.remove(this)`) — 즉 자동 재조인이 없는 **종착 상태**다.
          // 일시적 끊김은 onError를 타 CHANNEL_ERROR로 오고 재조인이 예약되지만, CLOSED는 그대로
          // 끝이라 폴링이 사라진 지금 이걸 놓치면 메시지가 조용히 영영 안 온다. 우리 쪽 정리
          // (cleanup)로 닫히는 경우는 위 cancelled 가드가 이미 걸러낸다.
          if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
            console.error('[chat/room] 실시간 구독 실패:', status, err);
            everDropped = true;
            setRealtimeError('실시간 연결이 끊겼습니다. 새로고침 후 다시 시도해주세요.');
          } else if (status === 'SUBSCRIBED') {
            if (everDropped) {
              // 자동 재조인(rejoinTimer)으로 되살아난 경우 — 경고를 그냥 지우면 안 된다(코드리뷰
              // patch 2차, medium). 끊겨 있는 동안 온 메시지는 아무 데도 없다(폴링 없음, 갭 보정은
              // Story 12.4 범위) — 경고를 지우면 사용자는 "다 정상"이라 읽고 그 구멍을 영영 모른다.
              // 연결 자체는 살아났다는 사실과 "그 구멍은 새로고침해야 메워진다"를 함께 남긴다.
              setRealtimeError(
                '실시간 연결이 복구됐습니다. 끊겨 있던 동안 도착한 메시지는 새로고침해야 보입니다.',
              );
            } else {
              setRealtimeError(null);
            }
            if (!initialSyncDone) {
              initialSyncDone = true;
              // 최초 구독이 열린 직후 한 번 더 전체 로드(코드리뷰 patch 2차, medium).
              // 위 초기 로드는 구독보다 **먼저** 나간다 — getSession→setAuth→웹소켓 join이 끝나기
              // 전까지의 틈에 들어온 INSERT는 그 응답에도 없고(이미 조회가 끝났다) 방송으로도 안 온다
              // (아직 구독 전이다). 폴링이 있을 땐 3초 뒤 커서 조회가 주워 담았지만 이제 복구 경로가
              // 새로고침뿐이라 조용한 영구 유실이 된다. 재연결 때마다 도는 갭 보정(12.4 범위)이 아니라
              // "초기 1회 로드"가 실제로 구독 시작점까지 닿게 하는 마무리라 최초 SUBSCRIBED에서만 돈다.
              void (async () => {
                const res = await fetchMessages(supabase, roomId);
                if (cancelled || 'error' in res) return; // 실패해도 초기 로드분은 이미 화면에 있다.
                mergeIncoming(res.messages);
              })();
            }
          }
        });
      } catch (err) {
        // getSession·setAuth가 실패하면 channel.subscribe 자체가 호출되지 않아 위 콜백(유일한
        // fail-loud 경로)이 아예 배선되지 않는다 — 그러면 화면은 초기 로드분만 띄운 채 영영 조용하다.
        // 그래서 여기서 직접 알린다(코드리뷰 patch, medium).
        if (cancelled) return;
        console.error('[chat/room] 실시간 구독 준비 실패:', err);
        setRealtimeError('실시간 연결에 실패했습니다. 새로고침 후 다시 시도해주세요.');
      }
    })();

    // 토큰 갱신마다(onAuthStateChange) 다시 setAuth — 구독이 만료된 토큰으로 굳지 않게 한다(Always).
    const {
      data: { subscription: authSubscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (cancelled) return;
      if (session?.access_token) {
        // setAuth는 async라 그냥 호출하면 거부(reject) 시 unhandled rejection이 된다 — 토큰 회전에
        // 실패하면 구독이 만료 토큰으로 굳는데, 이 리스너가 막으려던 바로 그 상황이 조용히 지나간다.
        // 재연결 로직은 12.4 범위라 만들지 않되, 최소한 로그로는 남긴다(코드리뷰 patch, low).
        void supabase.realtime
          .setAuth(session.access_token)
          .catch((err) => console.error('[chat/room] 토큰 갱신 후 setAuth 실패:', err));
      }
    });

    // cleanup: 채널·인증 리스너 정리(메모리 누수·유령 이벤트 방지 — 예전 폴링 인터벌 정리와 같은 자리).
    // 방 전환/이탈/언마운트 시 호출.
    return () => {
      cancelled = true;
      authSubscription.unsubscribe();
      supabase.removeChannel(channel);
    };
  }, [roomId, mergeIncoming, setPendingMessage]);

  // 전송 — 빈값/전송중이면 무시. pending 버블을 즉시 보여주고, 성공 시 실제 행으로 교체
  // (mergeIncoming) + pending 해제, 실패 시 한국어 에러 + 입력 복원 + pending 해제.
  //
  // 멱등키 선택 규칙(코드리뷰 patch, high): 직전 전송이 실패했고 이번에 보내는 본문이 그때와
  // "글자 그대로 같으면" 그때 실패했던 client_message_id를 재사용한다 — 새 키를 매번 만들면, 이
  // 앱의 유일한 재전송 경로("실패 → 입력 복원 → 사용자가 다시 전송 클릭")에서 서버엔 이미
  // 저장됐는데 응답만 유실된 경우가 새 키로 다시 들어가 FR41 멱등 보호(UNIQUE(room_id,
  // client_message_id))가 발동하지 않고 중복 메시지가 실제로 쌓일 수 있다. 사용자가 입력값을
  // 고쳐서 보내면 그건 새 메시지이므로 새 키를 만든다. 재사용은 FAILED_KEY_REUSE_WINDOW_MS 안에서만
  // 유효하다 — 그 이유는 상수 선언부 주석 참조(코드리뷰 patch, medium).
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = input.trim();
    if (body === '' || sending) return; // 빈 메시지·연타 차단(클라 1차).

    const roomAtSubmit = roomId; // 응답이 돌아왔을 때 아직 같은 방인지 판별할 기준.
    setError(null);
    setSending(true);
    setInput(''); // 즉시 입력창 비움(피드백). 실패하면 아래에서 복원.
    // 키 생성부터 try 안에서 한다(코드리뷰 patch, low) — 밖에 두면 여기서 던진 예외가
    // `finally { setSending(false) }`를 건너뛰어, 입력값은 이미 지워진 채 전송 버튼이 "전송 중…"
    // 으로 영구히 잠긴다(새로고침 말고는 복구 불가).
    let clientMessageId: string | null = null;
    try {
      clientMessageId =
        reuseFailedKey(lastFailedRef.current, body, Date.now(), FAILED_KEY_REUSE_WINDOW_MS) ??
        crypto.randomUUID();
      setPendingMessage({ clientMessageId, body }); // 전송 시작 시 즉시 pending 버블 표시(UX-DR15).
      const supabase = createClient();
      const res = await sendMessage(supabase, roomAtSubmit, myUserId, body, clientMessageId);
      // 응답을 기다리는 동안 다른 방으로 이동했으면 이 방 화면에 아무것도 쓰지 않는다.
      if (roomIdRef.current !== roomAtSubmit) return;
      if ('error' in res) {
        // 응답만 유실되고 서버엔 저장된 경우 — 브로드캐스트 에코가 이미 그 행을 목록에 올려뒀다.
        // 그때 "보내지 못했습니다"를 띄우면 같은 메시지가 화면에 보이는데 실패 안내와 복원된 입력값이
        // 함께 뜨는 모순이 된다. 실제로 전달됐으므로 성공으로 취급한다(코드리뷰 patch, medium).
        if (landedKeysRef.current.has(clientMessageId)) {
          setPendingMessage(null);
          lastFailedRef.current = null;
          return;
        }
        setError(res.error);
        setInput(body); // 실패 → 사용자가 곧바로 다시 보낼 수 있게 입력 복원.
        setPendingMessage(null);
        // 다음 재시도가 같은 키를 재사용하도록 기억(시각도 함께 — 재사용 창 판정용).
        lastFailedRef.current = { clientMessageId, body, at: Date.now() };
        return;
      }
      // 성공: 저장된 행을 목록에 반영. 브로드캐스트 에코가 이미 먼저 도착해 pending을 지웠을 수도
      // 있으므로(Design Notes 레이스 — 어느 경로가 먼저 오든), 지금도 같은 키일 때만 지운다.
      // dedupeById가 같은 행의 중복 렌더를 막는다.
      mergeIncoming([res.message]);
      if (pendingIdRef.current === clientMessageId) {
        setPendingMessage(null);
      }
      lastFailedRef.current = null; // 성공했으니 이 키를 다음 재시도용으로 기억할 필요가 없다.
    } catch (err) {
      if (roomIdRef.current !== roomAtSubmit) return;
      console.error('[chat/room] 메시지 전송 예외:', err);
      if (clientMessageId && landedKeysRef.current.has(clientMessageId)) {
        setPendingMessage(null);
        lastFailedRef.current = null;
        return;
      }
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      setInput(body);
      setPendingMessage(null);
      if (clientMessageId) lastFailedRef.current = { clientMessageId, body, at: Date.now() };
    } finally {
      // 위 세 경로와 같은 방 가드가 여기에도 필요하다(코드리뷰 patch 2차, low). 응답을 기다리는 동안
      // 방이 바뀌고 그 방에서 이미 새 전송이 시작됐다면, A방 응답이 B방의 sending을 풀어버려 연타
      // 차단이 뚫린다 — 그러면 서로 다른 멱등키로 두 번 INSERT돼 실제로 중복 행이 생긴다(pending을
      // 단일 값으로 둔 근거인 "sending이 동시 다건을 막는다"도 함께 깨진다).
      if (roomIdRef.current === roomAtSubmit) setSending(false);
    }
  }

  return (
    <section aria-label="메시지" className="flex flex-col gap-4">
      {/* 메시지 목록 — 시간 오름차순. 내 메시지 오른쪽·상대 왼쪽으로 구분(AC#3). pending은 맨 끝에 표시. */}
      <ul className="flex min-h-40 flex-col gap-2 rounded border border-zinc-200 p-4 dark:border-zinc-800">
        {loading ? (
          <li className="text-center text-sm text-zinc-500">메시지를 불러오는 중…</li>
        ) : messages.length === 0 && !pending ? (
          // 첫 대화 빈 상태(AC#3).
          <li className="text-center text-sm text-zinc-500">
            아직 주고받은 메시지가 없습니다. 먼저 인사를 건네보세요.
          </li>
        ) : (
          <>
            {messages.map((m) => {
              const mine = m.sender_id === myUserId;
              return (
                <li key={m.id} className={mine ? 'flex justify-end' : 'flex justify-start'}>
                  {/* whitespace-pre-wrap: 줄바꿈 보존. 본문은 사용자 입력이라 React 기본 이스케이프로 XSS 안전. */}
                  <span
                    className={
                      mine
                        ? 'max-w-[80%] break-words whitespace-pre-wrap rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900'
                        : 'max-w-[80%] break-words whitespace-pre-wrap rounded-lg border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-800'
                    }
                  >
                    {m.body}
                  </span>
                </li>
              );
            })}
            {/* pending 버블 — 서버 확정 전 낙관적 표시(UX-DR15). 확정되면 위 목록의 실제 행으로 교체되고
                이 버블은 사라진다(같은 문구가 두 번 보이지 않음). */}
            {pending && (
              <li className="flex justify-end">
                <span className="max-w-[80%] break-words whitespace-pre-wrap rounded-lg bg-zinc-900 px-3 py-2 text-sm text-white opacity-60 dark:bg-zinc-100 dark:text-zinc-900">
                  {pending.body}
                </span>
              </li>
            )}
          </>
        )}
      </ul>

      {/* 에러 안내 — 조용한 실패 금지(fail-loud). 수명이 서로 다른 신호라 세 칸으로 나눠 보여준다:
          실시간 연결 경고는 다시 붙을 때까지, 초기 로드 실패는 새로고침할 때까지(재조회 경로가 없다),
          전송 에러만 다음 전송 때 지워진다. 한 칸을 같이 쓰면 전송 한 번에 앞의 둘이 지워진다. */}
      {realtimeError && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {realtimeError}
        </p>
      )}
      {loadError && (
        <p role="alert" className="text-sm text-red-600 dark:text-red-400">
          {loadError}
        </p>
      )}
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
          // loading 중에도 잠근다(코드리뷰 patch 2차, low) — 초기 로드 중에는 위 목록이 "불러오는 중…"
          // 한 줄로 대체되므로 이때 보낸 메시지의 pending 버블이 렌더될 자리가 없다. 즉 UX-DR15(전송
          // 즉시 낙관적 표시)가 하필 피드백이 가장 필요한 느린 로드 구간에서만 깨진다.
          disabled={sending || loading}
          maxLength={CHAT.MESSAGE_MAX_LENGTH} // 길이 상한 1차 방어(기술부채 #8). 전송 가드·DB CHECK와 동일 값.
          // #84·대장 #169와 동일 원인(mx-auto 부모의 max-content 계산이 input 기본 size 힌트를 그대로
          // 반영해 390px에서 가로 오버플로가 남)이라 동일한 수정을 적용한다: size={1}로 기본 폭 힌트
          // 자체를 줄이고 min-w-0으로 flex 하한을 해제한다(ChatAssistant.tsx:198-219의 기존 적용례와
          // 동일 패턴).
          size={1}
          className="min-w-0 flex-1 rounded border border-zinc-300 bg-transparent px-3 py-2 text-sm disabled:opacity-50 dark:border-zinc-700"
        />
        <Button type="submit" variant="primary" loading={sending} loadingText="전송 중…">
          전송
        </Button>
      </form>
    </section>
  );
}
