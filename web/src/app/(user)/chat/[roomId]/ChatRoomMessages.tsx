'use client';

// 채팅방 메시지 송수신 + 실시간 구독 (FR20·FR21, Story 5-3 → 12.3 폴링 제거 → 12.4 재연결 배너·갭보정)
// — 채팅방 진입 화면의 "대화 본문".
//
// 핵심 책임:
//   1) 전송(FR21): 입력한 메시지를 chat_messages에 client_message_id(멱등키, 0022)와 함께 INSERT하고,
//      전송 즉시 pending 버블로 보여주다가 서버 확정 시 실제 행으로 교체한다(UX-DR15).
//   2) 실시간 수신(FR20·NFR1, Story 12.3): `chat:room:{roomId}` private 채널을 구독해 상대의 INSERT를
//      폴링 없이 즉시 반영한다 — 0023이 놓은 Broadcast+RLS 토대를 이 화면이 처음 소비한다.
//   3) 목록 UI(AC#3): created_at 시간순, 내 메시지(오른쪽)·상대 메시지(왼쪽) 구분. 0건이면 빈 상태.
//   4) 재연결·오프라인 큐잉·갭보정(FR42, UX-DR19, Story 12.4): 구독이 끊겨도(CHANNEL_ERROR/TIMED_OUT)
//      비차단 배너만 띄우고 입력·전송은 계속 허용한다. 끊긴 동안 제출한 메시지는 네트워크 호출 없이
//      로컬 큐에 쌓아 즉시 pending으로 보여주고, 재연결(SUBSCRIBED, 이전에 끊긴 적 있음)되면 순서대로
//      flush한다(같은 client_message_id 재사용). 재연결 시 상대의 누락 메시지는 Broadcast Replay(채널
//      config) + 커서 재조회(fetchMessages)를 병행해 병합한다(docs/conventions.md §12.5).
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
  flushMessageQueue,
  type ChatMessageRow,
  type FailedSend,
  type QueuedMessage,
} from '@/lib/messages';
import Button from '@/components/ui/Button';
import { CHAT } from '@/lib/constants';

// 구독 토픽 형식 — 0023의 트리거·RLS 리터럴('chat:room:' || room_id::text)과 문자 그대로 동일해야
// 한다(docs/conventions.md §12). 한쪽만 바뀌면 방송은 계속 나가는데 구독만 조용히 끊기거나, 반대로
// 방 없는 토픽이 열리는 식으로 어긋난다.
function roomTopic(roomId: string) {
  return `chat:room:${roomId}`;
}

// 아직 확정되지 않은 pending 버블 1건(온라인 단건 전송 중이거나, 오프라인 큐에 쌓여 있는 것 둘 다).
// QueuedMessage(@/lib/messages)와 모양이 같다 — 오프라인 큐잉(Story 12.4)이 그 타입을 그대로 쓴다.
type PendingMessage = QueuedMessage;

// 실패한 멱등키를 재사용할 수 있는 시간 창. 재사용은 "방금 실패한 그 전송을 다시 보내는 것"에만
// 유효하다 — 창이 없으면, 서버엔 저장됐지만 방송도 응답도 못 받은 키가 무기한 남아 있다가 한참 뒤
// 사용자가 우연히 같은 본문("ㅇㅇ" 같은 짧은 답이 실제 시드 데이터에 있다)을 보낼 때 그 키가 재사용돼
// 23505 → 옛 행으로 수렴하고, 새 메시지는 조용히 전송되지 않는다(코드리뷰 patch, medium).
const FAILED_KEY_REUSE_WINDOW_MS = 60_000;

// 재연결(초록 "다시 연결됐어요") 배너가 떠 있다가 자동으로 사라지기까지의 시간(Story 12.4 Always —
// 스펙의 예시값 3000ms를 그대로 쓴다). 연결이 계속 정상이라는 신호를 영구히 남겨두면 화면이 배너로
// 어수선해지고, 동시에 "떠 있는 동안은 색+텍스트로 상태를 알린다"는 접근성 요구는 이미 충족했으므로
// 잠깐 뒤 조용히 지워도 정보 손실이 없다.
const RECONNECT_BANNER_DISMISS_MS = 3_000;

// Broadcast Replay 요청 범위. 두 값의 **출처가 다르다**(3차 후속 리뷰 patch, low — 이전 문구는
// 둘 다 "플랫폼 기본 한도"라고 적었으나 사실이 아니다. 정정 경위는 docs/conventions.md §12.5와
// 대장 #201):
//   · limit = 25 — 라이브러리(`@supabase/realtime-js`)가 정한 **상한**이다. 그 상한을 그대로 요청한다.
//   · since = 72시간 전 — `since`는 필수 인자이고 라이브러리는 기본값을 주지 않는다. 즉 **우리가 고른
//     값**이지 플랫폼이 규정한 값이 아니다. Epic 16.4가 Dart로 옮길 때 "플랫폼 상수"로 오해하면
//     안 된다.
// 어느 쪽이든 이 범위를 넘는 gap은 아래 gapFillFromCursor(커서 재조회)가 항상 메운다(Never — 이
// 한도를 client 코드로 재구현하거나 우회하지 않는다).
//
// ⚠️ `since = Date.now() - REPLAY_SINCE_WINDOW_MS`는 **채널 생성(컴포넌트 마운트) 시점에 한 번만**
// 계산된다(코드리뷰 patch, P6) — 그 config 객체는 재조인 때도 그대로 재사용되므로(join params,
// Design Notes) "지금부터 72시간 전"이 아니라 "이 방에 처음 들어온 시각으로부터 72시간 전"으로
// 고정된 채 탭이 오래 떠 있을수록 실제 커버 구간이 뒤로(과거 쪽으로) 밀린다. 이게 안전한 이유는
// gapFillFromCursor(커서 재조회)가 replay의 실제 커버 여부와 무관하게 재연결마다 **항상** 도는
// 백스톱이기 때문이다 — replay가 놓치는 몫이 늘어나도 커서 재조회가 그대로 메운다.
const REPLAY_SINCE_WINDOW_MS = 72 * 60 * 60 * 1000;
const REPLAY_LIMIT = 25;

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
  // 지금 화면에 떠 있는 loadError를 **누가** 세웠나(3차 후속 리뷰 patch, low). 갭보정 성공 시
  // loadError를 지우는 규칙(R1)이 무조건이면, "초기 전체 로드가 실패해 과거 대화가 통째로 비어
  // 있는" 상태에서 방송 한 건이 커서를 세우고 → 끊김 → 재연결 → 그 커서 이후만 조회하는 갭보정이
  // 성공하는 순서에서, 정작 복구되지 않은 과거 대화 경고까지 함께 지워진다. 커서 이후만 본 조회의
  // 성공은 "그 이전 구간도 잘 있다"는 증거가 아니므로, 갭보정은 자기가 세운 안내만 거둔다.
  const loadErrorSourceRef = useRef<'initial' | 'gapfill' | null>(null);
  // flush가 다 못 보낸 건수 안내(3차 후속 리뷰 patch, medium). error 칸을 쓰면 안 된다 — 그 칸은
  // handleSubmit 첫 줄의 setError(null)이 **다음 제출마다 무조건** 비우는 자리다(위 realtimeError·
  // loadError를 굳이 갈라둔 것과 똑같은 이유). 큐가 막힌 사용자의 가장 자연스러운 다음 행동이
  // "메시지를 한 번 더 쳐보는 것"인데, 그 순간 유일한 미전송 신호가 사라지고 화면은 완전히 정상으로
  // 보인다 — R3가 막으려던 조용한 실패가 다른 문으로 되돌아온다.
  const [queueStuckNotice, setQueueStuckNotice] = useState<string | null>(null);
  // 아직 확정되지 않은 pending 버블들(UX-DR15) — 12.3까지는 handleSubmit의 sending 가드가 동시
  // 다건 전송을 막아 단일 값으로 충분했지만, 12.4의 오프라인 큐잉(끊긴 동안 네트워크 호출 없이 여러
  // 건을 즉시 쌓는다, Always)은 그 가드를 타지 않으므로 배열/큐로 확장한다. 온라인 단건 전송(기존
  // 경로)도 이 큐에 항목 1개를 넣었다 빼는 것으로 동일하게 표현한다.
  const [pendingQueue, setPendingQueue] = useState<PendingMessage[]>([]);

  // pendingQueue를 ref로도 미러링 — 실시간 구독 콜백·큐 flush(아래 useEffect에서 방 진입 시 한 번만
  // 배선)가 stale closure 없이 "지금" 큐를 읽고 쓸 수 있게 한다(React state는 클로저에 캡처된 시점
  // 값이라 이펙트를 매 렌더 재배선하지 않는 한 최신값이 아니다 — 12.3의 pendingIdRef와 같은 이유).
  const pendingQueueRef = useRef<PendingMessage[]>([]);
  const setPendingQueueAndRef = useCallback((next: PendingMessage[]) => {
    pendingQueueRef.current = next;
    setPendingQueue(next);
  }, []);
  const enqueuePending = useCallback(
    (entry: PendingMessage) => setPendingQueueAndRef([...pendingQueueRef.current, entry]),
    [setPendingQueueAndRef],
  );
  const removePendingById = useCallback(
    (clientMessageId: string) =>
      setPendingQueueAndRef(
        pendingQueueRef.current.filter((p) => p.clientMessageId !== clientMessageId),
      ),
    [setPendingQueueAndRef],
  );

  // 재연결 배너(Story 12.4 Always) — 끊김일 땐 회색/빨강 비차단 문구, 재연결(SUBSCRIBED, 이전에 끊긴
  // 적 있음)이면 초록 "다시 연결됐어요"로 바뀐 뒤 타이머로 소멸한다. realtimeError(아래, CLOSED·구독
  // 준비 실패 전용)와 수명·의미가 다르므로 별도 상태로 둔다 — 한 칸을 같이 쓰면 재연결 성공이 CLOSED
  // 경고를 지우거나 그 반대의 뜻하지 않은 상호작용이 생긴다.
  type ReconnectBanner = { kind: 'disconnected' } | { kind: 'reconnected' };
  const [reconnectBanner, setReconnectBanner] = useState<ReconnectBanner | null>(null);
  const reconnectBannerTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // 지금 이 순간 연결이 끊겨 있는가 — handleSubmit(effect 밖의 별도 함수)이 동기적으로 읽어야 하므로
  // state가 아니라 ref다(구독 콜백은 effect 안에서 갱신, handleSubmit은 effect 밖에서 읽음 — 같은
  // 컴포넌트 스코프에 선언해 둘 다 참조할 수 있게 한다).
  const disconnectedRef = useRef(false);
  // 지금 온라인 경로(handleSubmit)가 응답을 기다리고 있는 항목의 키(3차 후속 리뷰 patch, low).
  // pendingQueue는 "온라인 전송 중"과 "오프라인 큐 대기"를 한 배열에 섞어 담는데, flush는 그 배열을
  // 통째로 스냅샷한다 — 전송 중에 끊겼다 붙으면 아직 응답을 못 받은 그 항목까지 flush가 다시 보내,
  // 같은 키로 두 요청이 동시에 뜬다. DB 멱등키(0022)가 실제 중복 행은 막지만 두 완료 핸들러가 같은
  // 항목에 대해 서로 다른 화면 갱신(에러 표시·입력 복원 vs 성공 병합)을 하게 되므로, 소유권이
  // 온라인 경로에 있는 동안은 flush 대상에서 뺀다.
  const onlineInFlightKeyRef = useRef<string | null>(null);
  // 갭보정 커서(재연결마다 이 시각 이후로 재조회) — "마지막으로 반영한 메시지의 created_at"을 아래
  // 별도 effect가 messages state에서 미러링한다(구독 콜백의 stale closure를 피하는 같은 패턴).
  const lastMessageAtRef = useRef<string | null>(null);

  // 미전송 안내 옆 "다시 보내기" 버튼이 호출할 최신 flushQueue를 담는 ref(대장 #206 재현 후 최소
  // 수정, Story 12.6) — flushQueue는 아래 effect 안에서 roomId가 바뀔 때마다 새로 정의되는 지역
  // 함수라 렌더(버튼 onClick)에서 직접 참조할 수 없다. 재연결 트리거 하나뿐이던 것에 "사용자가
  // 직접 다시 시도"라는 두 번째 트리거를 더하는 것뿐이고, flushQueue 자체의 순차 flush·멱등·큐
  // 보존 규칙은 그대로 재사용한다(새 전송 경로를 만들지 않음).
  const flushQueueRef = useRef<() => void>(() => {});

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
      loadErrorSourceRef.current = null;
      setQueueStuckNotice(null);
      setRealtimeError(null);
      setInput('');
      setSending(false);
      setPendingQueueAndRef([]);
      lastFailedRef.current = null;
      landedKeysRef.current = new Set();
      // 12.4 재연결 상태도 방 전환 시 함께 초기화한다 — 안 지우면 A방에서 끊긴 채였던 배너·큐 잔상이
      // B방 화면에 잠깐 보인다(위 pending·에러 초기화와 같은 이유).
      setReconnectBanner(null);
      if (reconnectBannerTimeoutRef.current) {
        clearTimeout(reconnectBannerTimeoutRef.current);
        reconnectBannerTimeoutRef.current = null;
      }
      disconnectedRef.current = false;
      lastMessageAtRef.current = null;
      onlineInFlightKeyRef.current = null;
      // flushQueueRef도 함께 초기화한다(코드리뷰 patch) — 아래에서 이 이펙트가 곧 새 flushQueue를
      // 다시 배선하므로 실질적 위험은 없었지만, 형제 ref들과 같은 자리에서 같이 리셋해 "roomId가
      // 바뀌면 이 블록의 ref들은 전부 초기화된다"는 불변식을 명시적으로 지킨다(방어적 일관성).
      flushQueueRef.current = () => {};

      setLoading(true);
      const res = await fetchMessages(supabase, roomId);
      if (cancelled) return;
      if ('error' in res) {
        setLoadError('과거 대화를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.');
        loadErrorSourceRef.current = 'initial';
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
    //
    // broadcast.replay(Story 12.4 Always) — 구독 시점에 Realtime 서버가 이 토픽의 최근 이력(0023이
    // 이미 realtime.broadcast_changes()로 영속 중)을 같은 broadcast/INSERT 이벤트로 재생한다. 별도
    // 소비 코드가 필요 없다 — 아래 핸들러가 그대로 받는다. 이 config는 재조인 시에도 그대로
    // 재사용되므로(채널 join params) 최초 생성 시 한 번만 추가하면 된다.
    //
    // ⚠️ 스펙 Design Notes는 이 옵션을 `{ replay: true }`(불리언)로 적었으나, 설치된
    // `@supabase/realtime-js@2.108.2`의 실제 타입·README(Broadcast Replay 절)는 `replay`가 불리언이
    // 아니라 `{ since: <필수, epoch ms>, limit?: <=25> }` 객체를 요구한다 — `true`는 tsc 타입 에러
    // (`Type 'boolean' is not assignable to type 'ReplayOption'`)로 컴파일 자체가 안 된다(실측). 의도
    // (replay 활성화 + 한도를 우회하지 않음)는 그대로 살리되, 실제 계약에 맞는 값으로 넣는다:
    // since = 72시간 전(REPLAY_SINCE_WINDOW_MS, **우리가 고른 값**), limit = 25(**라이브러리 상한**).
    // 두 값의 출처가 다르다는 사실은 위 상수 선언부 주석 참조(3차 후속 리뷰 patch).
    const channel = supabase.channel(roomTopic(roomId), {
      config: {
        private: true,
        broadcast: { replay: { since: Date.now() - REPLAY_SINCE_WINDOW_MS, limit: REPLAY_LIMIT } },
      },
    });
    channel.on('broadcast', { event: 'INSERT' }, (message) => {
      // 방 전환/언마운트 후 늦게 도착한 이벤트는 무시한다(코드리뷰 patch, medium) — 이 콜백은
      // cleanup에서 채널 자체를 제거하지만, 제거가 완료되기 전에 이미 in-flight인 이벤트가 있을 수
      // 있어 다른 경로와 동일하게 cancelled를 확인한다.
      if (cancelled) return;
      const record = (message.payload as { record?: ChatMessageRow } | undefined)?.record;
      if (!record) return;
      mergeIncoming([record]);
      // 같은 client_message_id가 큐(온라인 단건 전송 중이거나 오프라인 큐 flush 중)에 남아 있으면
      // "브로드캐스트 에코"로 보고 확정한다 — 12.3의 pendingIdRef 단일 비교를 큐 전체 탐색으로 확장.
      if (
        record.client_message_id &&
        pendingQueueRef.current.some((p) => p.clientMessageId === record.client_message_id)
      ) {
        removePendingById(record.client_message_id);
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
    // 연결이 flap(drop→reconnect→drop→reconnect)해 flushQueue가 짧은 간격으로 여러 번 호출돼도
    // 동시에 두 flush가 돌지 않게 막는 가드(코드리뷰 patch, P4) — DB 멱등키(0022)가 실제 중복 행은
    // 이미 막아주므로 안전성 문제는 아니지만, 굳이 같은 항목을 두 번 요청할 이유가 없다.
    let isFlushing = false;
    // 위 가드에 걸려 반려된 flush 요청이 있었는지 — 있으면 진행 중인 flush가 끝난 직후 한 번 더
    // 돈다(후속 리뷰 patch, R4 — 가드가 요청을 "버리지" 않고 "미루게" 만드는 자리).
    let flushRequestedAgain = false;

    // 재연결(초록) 배너를 RECONNECT_BANNER_DISMISS_MS 후 자동으로 지운다(Always). 새 드롭이 그 전에
    // 오면(아래 CHANNEL_ERROR/TIMED_OUT 분기) 예약을 취소하고 배너를 즉시 "끊김"으로 덮어쓴다.
    function scheduleReconnectBannerDismiss() {
      if (reconnectBannerTimeoutRef.current) clearTimeout(reconnectBannerTimeoutRef.current);
      reconnectBannerTimeoutRef.current = setTimeout(() => {
        reconnectBannerTimeoutRef.current = null;
        if (cancelled) return;
        setReconnectBanner(null);
      }, RECONNECT_BANNER_DISMISS_MS);
    }

    // 오프라인 큐 flush(Always) — 순서대로(순차 await) 기존 sendMessage()로 전송한다. 알고리즘 자체는
    // messages.ts의 순수 함수(flushMessageQueue, vitest로 검증)에 있고, 여기서는 그 결과를 화면 상태에
    // 반영만 한다. 큐잉 시점의 client_message_id를 그대로 넘기므로(sendFn), 재시도해도 23505 흡수
    // 경로로 멱등이 성립한다(Design Notes — reuseFailedKey의 시간창 휴리스틱이 필요 없는 이유).
    async function flushQueue() {
      // P4 — flap 중 중복 실행 방지(위 isFlushing 선언부 참조). 다만 요청을 그냥 버리면 안 된다
      // (후속 리뷰 patch, R4): flush는 순차 await라 시간이 걸리는데, 그 사이에 다시 끊겼다 붙으면
      // 그 구간에 큐잉된 항목은 이미 시작된 flush의 스냅샷에도 없고 새 flush도 뜨지 않아, 다음
      // 끊김→재연결이 또 올 때까지(어쩌면 영영) 전송되지 않는다. 그래서 "버림"이 아니라 "예약"으로
      // 처리한다 — 진행 중이면 표시만 해두고, 끝난 뒤 finally에서 한 번 더 돈다.
      if (isFlushing) {
        flushRequestedAgain = true;
        return;
      }
      // 온라인 경로가 아직 응답을 기다리는 항목은 그 경로의 소유이므로 건너뛴다(위 선언부 참조).
      // 그 항목은 온라인 경로가 스스로 성공/실패로 마무리하고, 실패하면 lastFailedRef를 통해 같은
      // 키로 재시도되거나 다음 제출에서 큐로 넘어온다.
      const queueSnapshot = pendingQueueRef.current.filter(
        (p) => p.clientMessageId !== onlineInFlightKeyRef.current,
      );
      if (queueSnapshot.length === 0) return;
      isFlushing = true;
      try {
        const { remaining, sent } = await flushMessageQueue(queueSnapshot, (msg: QueuedMessage) =>
          sendMessage(supabase, roomId, myUserId, msg.body, msg.clientMessageId),
        );
        if (cancelled) return;
        if (sent.length > 0) mergeIncoming(sent);
        // 실패한 항목(과 그 뒤로 아직 못 보낸 항목)은 remaining에 그대로 남아 다음 재연결 때
        // 재시도된다(Always — 버리지 않음).
        //
        // 이때 화면에도 반드시 남긴다(후속 리뷰 patch, R3). 이전엔 console.error만 남기고 "pending
        // 버블이 남아 있는 것 자체가 신호"라고 봤지만, 그 버블은 정상 전송 중 버블과 시각적으로
        // 완전히 동일하다(같은 opacity-60). 게다가 재시도 트리거가 "다음 끊김→재연결"뿐이라 연결이
        // 계속 정상이면 영영 재시도되지 않는다 — 초록 "다시 연결됐어요"가 3초 뒤 사라지고 나면
        // 화면은 완전히 정상으로 보이는데 메시지 N건은 전송되지 않은 상태다. 조용한 실패 금지
        // (fail-loud)가 정확히 이 자리에서 깨지므로, 몇 건이 남았는지 사용자에게 보이게 한다.
        //
        // 안내는 error가 아니라 전용 칸(queueStuckNotice)에 쓴다(3차 후속 리뷰 patch, medium) —
        // error는 다음 제출마다 지워지는 칸이라, 큐가 막힌 사용자가 메시지를 한 번 더 치는 순간
        // 유일한 신호가 사라진다. 문구도 실제 동작대로 적는다: 자동 재시도 트리거는 아래 SUBSCRIBED
        // 분기 하나뿐이라 "연결이 회복되면"이 아니라 **다시 끊겼다 붙어야** 돌아간다는 사실은 여전히
        // 남기되(그렇게 약속하면 안내 자체가 거짓말이 된다), 이제는 바로 옆 "다시 보내기" 버튼으로
        // 지금 당장 재시도할 수도 있다는 점을 함께 적는다(코드리뷰 patch, Story 12.6 후속) — 버튼이
        // 생긴 뒤로 "그때까지는 전송되지 않는다"는 더 이상 사실이 아니다.
        //
        // 단, 이 state에는 **"몇 건이 남았나"라는 사실만** 담는다(후속 리뷰 patch) — "어떻게 다시
        // 보내나"는 render에서 isDisconnected로 갈라 쓴다. 여기 문장으로 박아두면 flush 시점(항상
        // 재연결 직후 = 연결된 상태)의 안내가 그대로 굳어버려서, 그 뒤 다시 끊겨 재시도 버튼이
        // disabled로 잠긴 화면에서도 "버튼을 누르면 지금 다시 시도한다"고 말하는 거짓 안내가 된다
        // (스펙이 지정한 #206 재현 절차 — 재연결 → 부분 실패 → 재차단 — 이 정확히 그 상태다).
        // 주석을 아래 if 블록 **밖**에 두는 이유: roomTopicContract.test.ts가 "if (remaining.length
        // > 0) { ... setQueueStuckNotice(" 사이 400자를 창으로 잡아 실패 경로 배선을 고정한다.
        if (remaining.length > 0) {
          console.error(
            '[chat/room] 오프라인 큐 일부 전송 실패, 다음 재연결에 재시도:',
            remaining.length,
            '건 남음',
          );
          setQueueStuckNotice(`메시지 ${remaining.length}건을 아직 보내지 못했습니다.`);
        } else {
          // 큐를 끝까지 비웠으면 앞선 미전송 안내를 거둔다 — 안 지우면 이미 다 보낸 뒤에도 "N건
          // 미전송"이 화면에 박제된다(loadError에서 R1이 고친 것과 같은 방향의 실패).
          setQueueStuckNotice(null);
        }
        // 스냅샷이 아니라 "지금" 큐에서 성공분의 id만 걷어낸다(코드리뷰 patch, P1) — flush는 순차
        // await라 완료까지 시간이 걸리는데, 그 사이 연결이 이미 복구된 상태이므로 사용자가 온라인
        // 경로(handleSubmit)로 새 메시지를 추가 제출하면 pendingQueueRef.current에 항목이 늘어나
        // 있을 수 있다. remaining(스냅샷 파생값)으로 통째로 덮어쓰면 그 새 pending 버블이 화면에서
        // 잠깐 사라진다(전송 자체는 끝나 messages에는 반영되지만 pending 표시만 깜빡였다 사라지는
        // 혼란). 성공한 id만 걷어내면 mid-flush에 추가된 항목도, 이미 실패해 remaining에 남은
        // 항목도 그대로 보존된다.
        const sentIds = new Set(sent.map((m) => m.client_message_id));
        setPendingQueueAndRef(
          pendingQueueRef.current.filter((p) => !sentIds.has(p.clientMessageId)),
        );
      } catch (err) {
        // P2 — sendMessage는 던질 수 있다(handleSubmit이 이미 이 이유로 try/catch를 쓴다). 여기서
        // 안 잡으면 unhandled rejection이 되고, 이 배치의 pending들은 최종 상태 갱신을 영영 못 받아
        // "전송 중…" 버블로 화면에 무기한 박제된다(fail-loud 원칙 위반). 큐는 비우지 않는다 — 남아
        // 있는 pending 자체가 "아직 확정 안 됨"이라는 신호이고, 다음 재연결이 다시 시도한다.
        if (cancelled) return;
        console.error('[chat/room] 오프라인 큐 flush 중 예외:', err);
      } finally {
        isFlushing = false;
        // 진행 중에 들어온 flush 요청이 있었으면(그 사이 flap으로 새 항목이 큐에 들어왔다는 뜻)
        // 지금 한 번 더 돈다(후속 리뷰 patch, R4). 큐가 비어 있으면 위 길이 검사에서 즉시 반환하므로
        // 무한 재귀가 되지 않는다 — 매 회차마다 큐가 줄거나(전송 성공) 실패로 멈추고, 실패한 항목은
        // 새 요청 없이는 다시 돌지 않는다.
        if (flushRequestedAgain && !cancelled) {
          flushRequestedAgain = false;
          void flushQueue();
        }
      }
    }
    // 렌더(버튼 onClick)가 이 회차의 flushQueue를 부를 수 있게 ref에 담아 둔다(대장 #206 최소 수정) —
    // 재연결 자동 트리거와 똑같이 flushQueue()를 그대로 호출할 뿐, 새 전송 경로는 아니다.
    flushQueueRef.current = () => void flushQueue();

    // 갭보정(AC-CHAT-2, CR6) — 재연결마다 "마지막으로 반영한 메시지의 created_at"을 커서로 항상
    // fetchMessages를 다시 부른다(Broadcast Replay와 별개로 병행, Design Notes). 커서가 없으면(아직
    // 화면에 메시지가 없던 방) 전체 재조회로 자연스럽게 대체된다.
    async function gapFillFromCursor() {
      // 이번 조회가 커서 없이(= 전체 재조회로) 돌았는지 — 그렇다면 초기 로드 실패까지 실제로 메운
      // 것이므로 그 안내도 함께 거둘 수 있다(아래 성공 경로 참조).
      const cursor = lastMessageAtRef.current;
      try {
        const res = await fetchMessages(supabase, roomId, cursor);
        if (cancelled) return;
        if ('error' in res) {
          // 재조회 자체가 실패하면 fail-loud로 안내한다 — 큐 flush는 별개 경로라 이 실패로 막히지
          // 않는다(Always, I/O 매트릭스).
          setLoadError('끊긴 동안 놓친 메시지를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.');
          loadErrorSourceRef.current = 'gapfill';
          return;
        }
        mergeIncoming(res.messages);
        // 이번 갭보정이 성공했으면 앞선 갭보정 실패 안내를 지운다(후속 리뷰 patch, R1). 안 지우면
        // loadError를 비우는 경로가 "방 전환"뿐이라, 일시적 재조회 실패 한 번이 "새로고침 후 다시
        // 시도해주세요"를 세션 내내 박제한다 — 정작 메시지는 이미 화면에 병합돼 있는데 사용자는
        // 계속 새로고침하게 된다(fail-loud의 반대 실패: 이미 해결된 문제를 계속 알리는 것).
        //
        // 단, **자기가 세운 안내만** 거둔다(3차 후속 리뷰 patch, low). 커서가 있는 조회는 그 시각
        // 이후만 본 것이라, 성공했다고 해서 초기 전체 로드가 실패해 비어 있는 과거 구간까지 복구된
        // 것은 아니다 — 그 경고까지 지우면 대화가 통째로 빠진 화면이 "정상"으로 보인다. 커서 없이
        // 돈 조회는 전체 재조회라 초기 로드 실패도 실제로 메웠으므로 그때는 함께 거둔다.
        if (cursor === null || loadErrorSourceRef.current === 'gapfill') {
          setLoadError(null);
          loadErrorSourceRef.current = null;
        }
      } catch (err) {
        // P2 — fetchMessages도 던질 수 있다. 안 잡으면 unhandled rejection이 되고 갭보정 실패가
        // 화면 어디에도 안 남는다(fail-loud 위반). error 응답과 동일한 안내로 통일한다.
        if (cancelled) return;
        console.error('[chat/room] 갭보정 커서 재조회 중 예외:', err);
        setLoadError('끊긴 동안 놓친 메시지를 불러오지 못했습니다. 새로고침 후 다시 시도해주세요.');
        loadErrorSourceRef.current = 'gapfill';
      }
    }

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
          // 남기면 화면상으로는 아무 일도 없었던 것처럼 보인다.
          //
          // 연결 상태는 CHANNEL_ERROR/TIMED_OUT(끊김) ↔ SUBSCRIBED(재연결)만으로 판단한다(Story 12.4
          // Always) — 실측(Design Notes)상 네트워크 드롭은 이 두 상태만 오가고, 라이브러리의
          // rejoinTimer가 소켓 재연결마다 자동으로 재조인한다. 수동 재구독·소켓 재생성은 만들지 않는다
          // (Never).
          if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
            console.error('[chat/room] 실시간 구독 끊김:', status, err);
            everDropped = true;
            disconnectedRef.current = true;
            // 재연결 배너가 소멸 타이머를 걸어둔 채로 다시 끊겼을 수 있다 — 그 타이머가 나중에
            // "다시 연결됐어요"를 지우려던 예약이므로, 지금 배너를 "끊김"으로 덮어쓰기 전에 취소한다.
            if (reconnectBannerTimeoutRef.current) {
              clearTimeout(reconnectBannerTimeoutRef.current);
              reconnectBannerTimeoutRef.current = null;
            }
            setReconnectBanner({ kind: 'disconnected' });
          } else if (status === 'CLOSED') {
            // 12.3의 기존 분기 그대로 유지(Never — 제거·리팩터 금지). CLOSED는 명시적 leave()(방
            // 전환·언마운트)에서만 발생하고(Design Notes 실측), 그 경우는 위 cancelled 가드가 이미
            // 걸러낸다 — 그래서 실사용에서 이 분기는 사실상 도달하지 않는다. 그래도 도달한다면(이례적
            // 상황) 12.3이 두던 문구를 그대로 보여준다 — 12.4의 재연결 배너 대상이 아니다.
            console.error('[chat/room] 실시간 구독 실패:', status, err);
            everDropped = true;
            setRealtimeError('실시간 연결이 끊겼습니다. 새로고침 후 다시 시도해주세요.');
          } else if (status === 'SUBSCRIBED') {
            disconnectedRef.current = false;
            if (everDropped) {
              // 재연결(Always) — 배너를 초록 "다시 연결됐어요"로 바꾼 뒤 타이머로 소멸시키고, 오프라인
              // 큐 flush + 갭보정(커서 재조회)을 함께 돌린다. 12.3까지는 "새로고침해야 보인다"고
              // 안내만 했지만, 이제 둘 다 자동으로 메운다(Story 12.4가 그 자리를 대체).
              setReconnectBanner({ kind: 'reconnected' });
              scheduleReconnectBannerDismiss();
              void flushQueue();
              void gapFillFromCursor();
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

    // cleanup: 채널·인증 리스너·재연결 배너 타이머 정리(메모리 누수·유령 이벤트 방지 — 예전 폴링
    // 인터벌 정리와 같은 자리). 방 전환/이탈/언마운트 시 호출.
    return () => {
      cancelled = true;
      authSubscription.unsubscribe();
      supabase.removeChannel(channel);
      if (reconnectBannerTimeoutRef.current) {
        clearTimeout(reconnectBannerTimeoutRef.current);
        reconnectBannerTimeoutRef.current = null;
      }
    };
  }, [roomId, myUserId, mergeIncoming, setPendingQueueAndRef, removePendingById]);

  // 갭보정 커서 미러링 — "마지막으로 반영한 메시지의 created_at"을 ref로 들고 있어야 재연결 콜백(위
  // effect의 클로저, roomId가 바뀌지 않는 한 재배선되지 않는다)이 stale 값을 읽지 않는다. messages
  // state가 갱신될 때마다 이 effect가 최신값을 ref로 옮겨 둔다(pendingQueueRef와 같은 미러링 패턴).
  useEffect(() => {
    const last = messages[messages.length - 1];
    if (last) lastMessageAtRef.current = last.created_at;
  }, [messages]);

  // 전송 — 빈값/전송중이면 무시. pending 버블을 즉시 보여주고, 성공 시 실제 행으로 교체
  // (mergeIncoming) + pending 해제, 실패 시 한국어 에러 + 입력 복원 + pending 해제.
  //
  // 연결이 끊겨 있으면(Story 12.4 Always) 네트워크 호출 자체를 시도하지 않고 즉시 pending 버블 +
  // 로컬 큐에 적재한다 — 왕복이 없어 sending 가드(연타 차단)를 걸 이유가 없다. 여러 건 동시 대기가
  // 이 경로의 목적이다.
  //
  // 멱등키 선택 규칙(코드리뷰 patch, high): 직전 전송이 실패했고 이번에 보내는 본문이 그때와
  // "글자 그대로 같으면" 그때 실패했던 client_message_id를 재사용한다 — 새 키를 매번 만들면, 이
  // 앱의 유일한 재전송 경로("실패 → 입력 복원 → 사용자가 다시 전송 클릭")에서 서버엔 이미
  // 저장됐는데 응답만 유실된 경우가 새 키로 다시 들어가 FR41 멱등 보호(UNIQUE(room_id,
  // client_message_id))가 발동하지 않고 중복 메시지가 실제로 쌓일 수 있다. 사용자가 입력값을
  // 고쳐서 보내면 그건 새 메시지이므로 새 키를 만든다. 재사용은 FAILED_KEY_REUSE_WINDOW_MS 안에서만
  // 유효하다 — 그 이유는 상수 선언부 주석 참조(코드리뷰 patch, medium). 이 재사용 판정은 **제출
  // 시점**에 온라인·오프라인 두 경로가 똑같이 적용한다(후속 리뷰 patch, R2). 반면 재연결 시 큐를
  // flush할 때는 이 판정이 필요 없다 — 큐잉 시점에 정해진 키를 그대로 다시 쓰면 되기 때문이다
  // (어떤 항목을 재시도하는지 큐 자체가 이미 알고 있다, Design Notes).
  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const body = input.trim();
    if (body === '') return; // 빈 메시지 차단(클라 1차).
    // 연타 차단(sending)은 **온라인 경로 전용**이다(후속 리뷰 patch, R5). 이전엔 이 가드가 오프라인
    // 분기보다 앞에 있어서, 온라인 전송이 응답을 기다리는 중에 연결이 끊기면(= 실제로 연결이 죽는
    // 가장 흔한 순서다: 보냈는데 그 순간 네트워크가 나감) 그 요청이 끝날 때까지 사용자의 제출이
    // 큐에도 안 쌓이고 에러도 안 뜨는 무반응 구간이 생겼다. supabase-js 호출엔 타임아웃이 없어 그
    // 구간이 길어질 수 있고, 이는 "끊긴 동안에도 계속 작성·전송할 수 있다"(FR42·UX-DR19 비차단)와
    // 정면으로 어긋난다. 끊긴 상태의 제출은 네트워크 왕복이 아니라 로컬 큐잉이므로 애초에 연타로
    // 보호할 대상도 아니다(여러 건 동시 대기가 이 경로의 목적이다).
    if (sending && !disconnectedRef.current) return;

    setError(null);
    setInput(''); // 즉시 입력창 비움(피드백). 온라인 경로가 실패하면 아래에서 복원.

    if (disconnectedRef.current) {
      // 끊긴 동안 제출 — sendMessage 네트워크 호출을 시도하지 않는다(Always). 다만 sendMessage
      // 내부의 길이 검증(CHAT.MESSAGE_MAX_LENGTH)은 이 경로에선 호출 자체가 없어 돌지 않는다 —
      // 그대로 큐잉하면(코드리뷰 patch, P3) flushMessageQueue가 재연결마다 그 항목을 재시도하는데
      // sendMessage가 매번 같은 길이 에러를 돌려주고, 큐의 "실패 항목은 버리지 않는다" 규칙 때문에
      // 그 뒤의 모든 메시지까지 영영 막힌다(재연결마다 조용히 재시도만 반복 — 사용자에게 보이는
      // 신호가 없다). 그래서 sendMessage와 동일한 검증을 여기서 미리 돌려 막는다 — 온라인 경로가
      // 이미 하는 "즉시 에러 안내 + 입력 복원"과 같은 UX로 통일한다.
      if (body.length > CHAT.MESSAGE_MAX_LENGTH) {
        setError(`메시지가 너무 깁니다. 최대 ${CHAT.MESSAGE_MAX_LENGTH}자까지 보낼 수 있습니다.`);
        setInput(body); // 사용자가 줄여서 다시 보낼 수 있게 복원.
        return;
      }
      // 멱등키는 온라인 경로와 **같은 규칙**으로 고른다(후속 리뷰 patch, R2). 이전엔 여기서 무조건
      // 새 UUID를 만들었는데, 그러면 "온라인 전송 실패(서버엔 저장됐는데 응답만 유실) → 입력 복원
      // → 그 사이 연결이 끊김 → 사용자가 그대로 다시 전송"이라는 실제 가능한 순서에서 새 키로
      // 큐잉·flush돼 chat_messages에 중복 행이 진짜로 쌓인다 — FR41 멱등 보호가 정확히 이 시나리오
      // 때문에 존재하는데 오프라인 경로만 그 밖에 있었다. 큐잉된 뒤로는 그 키를 큐가 인수하므로
      // lastFailedRef는 비운다(온라인 경로가 같은 키를 또 재사용하면 두 경로가 같은 키를 동시에
      // 들고 있게 된다).
      const clientMessageId =
        reuseFailedKey(lastFailedRef.current, body, Date.now(), FAILED_KEY_REUSE_WINDOW_MS) ??
        crypto.randomUUID();
      enqueuePending({ clientMessageId, body });
      lastFailedRef.current = null;
      return;
    }

    const roomAtSubmit = roomId; // 응답이 돌아왔을 때 아직 같은 방인지 판별할 기준.
    setSending(true);
    // 키 생성부터 try 안에서 한다(코드리뷰 patch, low) — 밖에 두면 여기서 던진 예외가
    // `finally { setSending(false) }`를 건너뛰어, 입력값은 이미 지워진 채 전송 버튼이 "전송 중…"
    // 으로 영구히 잠긴다(새로고침 말고는 복구 불가).
    let clientMessageId: string | null = null;
    try {
      clientMessageId =
        reuseFailedKey(lastFailedRef.current, body, Date.now(), FAILED_KEY_REUSE_WINDOW_MS) ??
        crypto.randomUUID();
      enqueuePending({ clientMessageId, body }); // 전송 시작 시 즉시 pending 버블 표시(UX-DR15).
      onlineInFlightKeyRef.current = clientMessageId; // 이 항목의 소유권은 아래 finally까지 이 경로.
      const supabase = createClient();
      const res = await sendMessage(supabase, roomAtSubmit, myUserId, body, clientMessageId);
      // 응답을 기다리는 동안 다른 방으로 이동했으면 이 방 화면에 아무것도 쓰지 않는다.
      if (roomIdRef.current !== roomAtSubmit) return;
      if ('error' in res) {
        // 응답만 유실되고 서버엔 저장된 경우 — 브로드캐스트 에코가 이미 그 행을 목록에 올려뒀다.
        // 그때 "보내지 못했습니다"를 띄우면 같은 메시지가 화면에 보이는데 실패 안내와 복원된 입력값이
        // 함께 뜨는 모순이 된다. 실제로 전달됐으므로 성공으로 취급한다(코드리뷰 patch, medium).
        if (landedKeysRef.current.has(clientMessageId)) {
          removePendingById(clientMessageId);
          lastFailedRef.current = null;
          return;
        }
        setError(res.error);
        // 입력창이 아직 비어 있을 때만 복원한다(3차 후속 리뷰 patch, medium). R5가 끊김 중 입력창
        // 잠금을 푼 뒤로, "전송 → 응답 대기 중 연결 끊김 → 사용자가 그 사이 다음 메시지를 타이핑"
        // 이 정상 경로가 됐다. 이때 뒤늦게 도착한 실패 응답이 무조건 setInput(body)를 하면 사용자가
        // 쓰던 글이 옛 본문으로 덮여 사라진다. 위 브로드캐스트 에코 경로(mergeIncoming 안)가 이미
        // 같은 이유로 함수형 갱신을 쓰고 있다 — 같은 규칙을 이 두 실패 경로에도 적용한다.
        setInput((current) => (current === '' ? body : current));
        removePendingById(clientMessageId);
        // 다음 재시도가 같은 키를 재사용하도록 기억(시각도 함께 — 재사용 창 판정용).
        lastFailedRef.current = { clientMessageId, body, at: Date.now() };
        return;
      }
      // 성공: 저장된 행을 목록에 반영. 브로드캐스트 에코가 이미 먼저 도착해 pending을 지웠을 수도
      // 있으므로(Design Notes 레이스 — 어느 경로가 먼저 오든), removePendingById는 이미 없는 키를
      // 다시 지워도 안전하다(no-op).
      mergeIncoming([res.message]);
      removePendingById(clientMessageId);
      lastFailedRef.current = null; // 성공했으니 이 키를 다음 재시도용으로 기억할 필요가 없다.
    } catch (err) {
      if (roomIdRef.current !== roomAtSubmit) return;
      console.error('[chat/room] 메시지 전송 예외:', err);
      if (clientMessageId && landedKeysRef.current.has(clientMessageId)) {
        removePendingById(clientMessageId);
        lastFailedRef.current = null;
        return;
      }
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
      setInput((current) => (current === '' ? body : current)); // 위 실패 경로와 같은 이유.
      if (clientMessageId) removePendingById(clientMessageId);
      if (clientMessageId) lastFailedRef.current = { clientMessageId, body, at: Date.now() };
    } finally {
      // 위 세 경로와 같은 방 가드가 여기에도 필요하다(코드리뷰 patch 2차, low). 응답을 기다리는 동안
      // 방이 바뀌고 그 방에서 이미 새 전송이 시작됐다면, A방 응답이 B방의 sending을 풀어버려 연타
      // 차단이 뚫린다 — 그러면 서로 다른 멱등키로 두 번 INSERT돼 실제로 중복 행이 생긴다.
      if (roomIdRef.current === roomAtSubmit) setSending(false);
      // 소유권 해제 — 이 시점 이후로는 남아 있는 항목(실패해 큐에 그대로 있는 경우)을 flush가
      // 가져가도 안전하다. 다른 제출이 이미 새 키를 세웠으면 덮어쓰지 않는다.
      if (clientMessageId && onlineInFlightKeyRef.current === clientMessageId) {
        onlineInFlightKeyRef.current = null;
      }
    }
  }

  // 지금 끊긴 상태인가(렌더용) — handleSubmit이 읽는 disconnectedRef와 같은 사실을 배너 상태에서
  // 읽는다(ref는 렌더를 다시 트리거하지 않으므로 화면 분기에는 state 쪽을 쓴다). 입력창·전송 버튼을
  // 끊김 중에 잠그지 않기 위한 값이다(후속 리뷰 patch, R5 — 비차단).
  const isDisconnected = reconnectBanner?.kind === 'disconnected';

  return (
    <section aria-label="메시지" className="flex flex-col gap-4">
      {/* 메시지 목록 — 시간 오름차순. 내 메시지 오른쪽·상대 왼쪽으로 구분(AC#3). pending 큐는 맨 끝에
          순서대로 표시(Story 12.4 — 끊긴 동안 여러 건이 동시에 대기할 수 있다). */}
      <ul className="flex min-h-40 flex-col gap-2 rounded-card border border-border-hairline p-4">
        {loading ? (
          <li className="text-center text-sm text-ink-muted">메시지를 불러오는 중…</li>
        ) : messages.length === 0 && pendingQueue.length === 0 ? (
          // 첫 대화 빈 상태(AC#3).
          <li className="text-center text-sm text-ink-muted">
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
                        ? 'max-w-[80%] break-words whitespace-pre-wrap rounded-lg bg-brand-petrol px-3 py-2 text-sm text-surface-base'
                        : 'max-w-[80%] break-words whitespace-pre-wrap rounded-lg border border-border-hairline bg-surface-raised px-3 py-2 text-sm text-ink-primary'
                    }
                  >
                    {m.body}
                  </span>
                </li>
              );
            })}
            {/* pending 버블 — 서버 확정 전 낙관적 표시(UX-DR15). 확정되면(온라인 전송 성공/브로드캐스트
                에코, 또는 재연결 후 큐 flush 성공) 위 목록의 실제 행으로 교체되고 이 버블은 사라진다. */}
            {pendingQueue.map((p) => (
              <li key={p.clientMessageId} className="flex justify-end">
                <span className="max-w-[80%] break-words whitespace-pre-wrap rounded-lg bg-brand-petrol px-3 py-2 text-sm text-surface-base opacity-60">
                  {p.body}
                </span>
              </li>
            ))}
          </>
        )}
      </ul>

      {/* 재연결 배너(Story 12.4 Always) — 비차단(입력·전송을 잠그지 않는다). 색+텍스트를 함께 표기해
          접근성 비색 신호를 중복시킨다(색만으로 상태를 전달하지 않음). 끊김은 남아 있고, 재연결은
          RECONNECT_BANNER_DISMISS_MS 후 자동 소멸한다. */}
      {reconnectBanner?.kind === 'disconnected' && (
        <p role="status" className="rounded bg-warn-amber-bg px-3 py-2 text-sm text-warn-amber-ink">
          연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요.
        </p>
      )}
      {reconnectBanner?.kind === 'reconnected' && (
        <p role="status" className="rounded bg-trust-green-bg px-3 py-2 text-sm text-trust-green-ink">
          다시 연결됐어요
        </p>
      )}

      {/* 에러 안내 — 조용한 실패 금지(fail-loud). 수명이 서로 다른 신호라 세 칸으로 나눠 보여준다:
          실시간 연결 경고(CLOSED·구독 준비 실패 전용)는 다시 붙을 때까지, 초기 로드 실패는 새로고침할
          때까지(재조회 경로가 없다), 전송 에러만 다음 전송 때 지워진다. 한 칸을 같이 쓰면 전송 한
          번에 앞의 둘이 지워진다. */}
      {realtimeError && (
        <p role="alert" className="text-sm text-danger">
          {realtimeError}
        </p>
      )}
      {queueStuckNotice && (
        <div className="flex items-center justify-between gap-3 text-sm text-danger">
          {/* role="alert"는 텍스트에만 건다(코드리뷰 patch) — alert 리전은 스크린리더가 "읽기 전용
              알림"으로 다루는 자리라, 그 안에 포커스 가능한 버튼을 넣으면 상태 변화마다 버튼까지
              재announce되는 접근성 안티패턴이 된다. 버튼은 alert 리전의 형제로 바깥에 둔다(시각적
              레이아웃은 그대로). min-w-0(코드리뷰 patch, D5) — 좁은 화면에서 문장이 버튼이 아니라
              먼저 줄어들게 한다(project-context.md 규칙13, 버튼 2줄 밀림 금지). */}
          {/* 안내 문구의 뒷문장("어떻게 다시 보내나")은 render에서 현재 연결 상태로 갈라 쓴다
              (후속 리뷰 patch) — 바로 옆 버튼이 disabled={isDisconnected}로 잠기는데 문구만
              "누르면 지금 다시 시도한다"고 박혀 있으면, 스펙이 지정한 #206 재현 절차(재연결 →
              부분 실패 → 재차단)가 정확히 그 모순 상태를 만든다. 앞문장(몇 건 남았나)은 flush가
              센 값이라 state에 그대로 둔다. */}
          <span role="alert" className="min-w-0">
            {queueStuckNotice}{' '}
            {isDisconnected
              ? '연결이 끊겨 지금은 다시 보낼 수 없습니다. 연결이 회복되면 자동으로 재시도합니다.'
              : '옆의 "다시 보내기"를 누르면 지금 다시 시도하고, 누르지 않으면 연결이 다시 끊겼다 회복될 때 재시도합니다.'}
          </span>
          {/* 재시도 버튼(대장 #206 최소 수정, Story 12.6) — 유일한 재시도 트리거가 "다음 끊김→재연결"
              뿐이었던 것에, 사용자가 직접 지금 다시 시도할 수 있는 수단을 더한다. flushQueue()를
              그대로 호출하므로 순차 flush·멱등(client_message_id 재사용)·큐 보존 규칙은 그대로다 —
              새 전송 경로가 아니다. disabled={isDisconnected}(코드리뷰 patch 후속) — 끊긴 동안엔
              눌러도 onClick 가드가 그대로 no-op이라 예전엔 버튼이 멀쩡해 보이는데 눌러도 아무 반응이
              없었다(피드백 없는 조용한 실패). 이제 그 상태를 시각적으로도 비활성으로 드러낸다.
              onClick의 disconnectedRef 가드는 그대로 남긴다 — 안내가 뜬 뒤(render) 클릭 사이에
              연결이 다시 끊기는 경합에서 disabled prop(렌더 시점 값)만으로는 못 막는 순간을 막는
              최후 방어선이다(disconnectedRef 재사용, 새 state 없음). */}
          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={isDisconnected}
            className="shrink-0 whitespace-nowrap" // D5 — 버튼은 줄바꿈·줄어들기 없이 항상 한 줄을 지킨다.
            onClick={() => {
              if (!disconnectedRef.current) flushQueueRef.current();
            }}
          >
            다시 보내기
          </Button>
        </div>
      )}
      {loadError && (
        <p role="alert" className="text-sm text-danger">
          {loadError}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
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
          // 끊긴 동안엔 sending으로 잠그지 않는다(후속 리뷰 patch, R5) — 이 경로의 제출은 네트워크
          // 왕복이 아니라 로컬 큐잉이라 잠글 이유가 없고, 잠그면 "메시지는 계속 작성할 수 있어요"라는
          // 배너 문구와 화면이 정면으로 모순된다(비차단, FR42·UX-DR19). loading(초기 로드)은 그대로
          // 잠근다 — 그땐 pending 버블이 렌더될 자리 자체가 없다(아래 이유 참조).
          disabled={(sending && !isDisconnected) || loading}
          maxLength={CHAT.MESSAGE_MAX_LENGTH} // 길이 상한 1차 방어(기술부채 #8). 전송 가드·DB CHECK와 동일 값.
          // #84·대장 #169와 동일 원인(mx-auto 부모의 max-content 계산이 input 기본 size 힌트를 그대로
          // 반영해 390px에서 가로 오버플로가 남)이라 동일한 수정을 적용한다: size={1}로 기본 폭 힌트
          // 자체를 줄이고 min-w-0으로 flex 하한을 해제한다(ChatAssistant.tsx:198-219의 기존 적용례와
          // 동일 패턴).
          size={1}
          className="min-w-0 flex-1 rounded border border-border-hairline bg-transparent px-3 py-2 text-sm disabled:opacity-50"
        />
        {/* 전송 버튼도 같은 이유로 끊김 중엔 잠그지 않는다(후속 리뷰 patch, R5) — Button은 loading
            이면 자동으로 disabled가 되므로, 입력창만 풀고 버튼을 잠가두면 제출 자체가 막힌다. */}
        <Button
          type="submit"
          variant="primary"
          loading={sending && !isDisconnected}
          loadingText="전송 중…"
        >
          전송
        </Button>
      </form>
    </section>
  );
}
