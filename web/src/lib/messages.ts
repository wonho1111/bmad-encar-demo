// 채팅 메시지 "조회·전송 규칙"의 단일 출처 (FR20·FR21, Story 5-3 → 12.3 멱등 전송 추가).
//
// 왜 한 곳에 모으나(@/lib/chat.ts의 openOrCreateRoom과 같은 정신):
//   "메시지를 어떻게 시간순으로 증분 조회하고, 어떻게 보내고, 에러를 어떻게 한국어로 바꾸나"라는 규칙이
//   화면 컴포넌트 곳곳에 흩어지면 드리프트(drift, 규칙이 조금씩 어긋남)가 생긴다. 그래서 이 모듈 한 곳에 모은다.
//
// 핵심 — DB(0003_chat.sql·0022_chat_idempotency_key.sql)가 보장하는 것을 신뢰한다:
//   · chat_messages_insert_participant RLS: auth.uid() = sender_id AND 그 방의 당사자일 때만 INSERT.
//     → sendMessage는 sender_id에 "본인 id"를 넣어야 통과한다(남의 명의 위조·끼어들기는 DB가 막음).
//   · chat_messages_select_participant RLS: 그 방의 당사자만 SELECT(제3자 0건).
//   · CHECK(length(btrim(body)) > 0): 공백만 메시지 거부(빈값 전송 시 23514). 클라가 1차로 trim() 차단.
//   · 인덱스 chat_messages_room_created_idx (room_id, created_at): 아래 증분 조회를 커버.
//   · UNIQUE(room_id, client_message_id)(0022, chat_messages_room_client_message_unique): 같은
//     멱등키로 재전송(네트워크 재시도)하면 23505로 거부된다 — sendMessage가 그 경우 새 행을 만드는
//     대신 기존 행을 조회해 그 행으로 수렴시킨다(대장 #186, Story 12.3). 호출부(clientMessageId)는
//     `crypto.randomUUID()`로 만들어 이 함수에 넘긴다(생성 자체는 전송을 시작하는 화면 쪽 책임 —
//     pending 버블을 즉시 보여주려면 INSERT가 끝나기 전에 이미 키가 있어야 하기 때문).
//
// 통신선/컬럼은 snake_case(AR5): room_id, sender_id, created_at, body, client_message_id.
import type { SupabaseClient } from '@supabase/supabase-js';
import { CHAT } from '@/lib/constants';

// 메시지 1건(통신선 그대로 snake_case). created_at은 ISO 문자열(timestamptz).
// client_message_id: 멱등키(0022) — 12.3 이전 행은 NULL, 이후 행은 sendMessage가 항상 채운다.
export type ChatMessageRow = {
  id: string;
  room_id: string;
  sender_id: string;
  body: string;
  created_at: string;
  client_message_id: string | null;
};

// Postgres SQLSTATE 코드(통신선 error.code에 그대로 실려 온다).
const PG_CHECK_VIOLATION = '23514'; // CHECK 위반(여기선 빈 본문 = body_not_blank)
const PG_UNIQUE_VIOLATION = '23505'; // UNIQUE 위반(여기선 (room_id, client_message_id) 재전송)

/**
 * 한 방의 메시지를 시간순(오래된→최신)으로 조회한다.
 *
 * @param supabase       브라우저 Supabase 클라이언트(@/lib/supabase/client). RLS 경유라 "내 방"만 보인다.
 * @param roomId         조회할 방 id.
 * @param atOrAfterCreatedAt (선택) 증분 조회 커서. 주면 이 시각 "이상(>=)"의 메시지만 가져온다.
 *                       Story 12.3부터 화면(ChatRoomMessages)은 방 진입 시 커서 없이(전체) 딱 한 번만
 *                       부른다 — 이후 수신은 폴링이 아니라 Realtime 구독(chat:room:{roomId})이 맡는다.
 *                       이 매개변수 자체는 지우지 않고 남겨둔다 — 재연결 후 갭 보정(끊긴 동안 놓친
 *                       메시지를 커서로 재조회)이 Story 12.4의 몫으로 이미 정해져 있고, 그때 이 함수를
 *                       그대로 재사용할 자리이기 때문이다(Never 절 — 갭 보정은 12.4 범위).
 * @returns 성공 { messages } / 조회 실패 { error: true }
 *
 * 왜 gte(>=)이고 gt(>)가 아닌가 (라이브 DB로 검증한 실측 결정):
 *   메시지를 거의 동시에 두 건 보내면 created_at이 같은 밀리초로 찍힐 수 있다(now()는 같은 트랜잭션 내 상수라
 *   특히 빠른 연속 전송에서 동일 시각 발생). 이때 gt(>) 커서는 커서와 "같은 시각"의 새 메시지를 영영 건너뛴다(누락).
 *   gte(>=)는 커서 시각의 행을 다시 포함하므로 누락이 없고, 다시 딸려온 경계 행(이미 가진 것)은 호출부의
 *   id dedupe가 제거한다 → "누락 0 + 중복 0". 라이브 DB에서 gt=0건(놓침)·gte=2건(완전수신)으로 확인.
 *
 * 조회 실패를 "메시지 0건"과 반드시 구분한다(@/lib/chat.findExistingRoom과 같은 이유):
 *   읽기 오류를 "없음"으로 오인하면 폴링이 조용히 멈추고 진짜 실패가 로그에도 안 남는다.
 */
export async function fetchMessages(
  supabase: SupabaseClient,
  roomId: string,
  atOrAfterCreatedAt?: string | null,
): Promise<{ messages: ChatMessageRow[] } | { error: true }> {
  let query = supabase
    .from('chat_messages')
    .select('id, room_id, sender_id, body, created_at, client_message_id')
    .eq('room_id', roomId);

  // 증분 커서가 있으면 그 시각 "이상"(gte). 동시각 경계 행을 다시 포함해 누락을 막고,
  // 그 중복은 호출부의 id dedupe가 제거한다(누락 0·중복 0 — 위 주석의 실측 근거).
  if (atOrAfterCreatedAt) {
    query = query.gte('created_at', atOrAfterCreatedAt);
  }

  // 시간 오름차순 + id 2차정렬(같은 시각 행의 순서 안정화 — chat 목록·search와 동일 정신).
  const { data, error } = await query
    .order('created_at', { ascending: true })
    .order('id', { ascending: true })
    .returns<ChatMessageRow[]>();

  if (error) {
    console.error('[messages] 메시지 조회 실패:', error);
    return { error: true };
  }
  return { messages: data ?? [] };
}

// 보낸 결과 — 성공이면 저장된 행, 실패면 사용자에게 보여줄 한국어 메시지.
//   (원본 에러는 여기서 console.error로만 남기고, 사용자에겐 이 한국어만 보여준다 — ListingActions·chat.ts 규칙.)
export type SendMessageResult = { message: ChatMessageRow } | { error: string };

/**
 * 메시지를 보낸다(chat_messages에 INSERT → 영속 저장, FR21).
 *
 * @param supabase        브라우저 Supabase 클라이언트.
 * @param roomId          보낼 방 id.
 * @param senderId        보내는 사람 = 현재 로그인 사용자 id(본인). RLS가 auth.uid()=sender_id를 강제하므로 본인 id여야 통과.
 * @param body            메시지 본문. 앞뒤 공백은 잘라 저장한다.
 * @param clientMessageId 멱등키(0022, `crypto.randomUUID()` 관례) — 호출부(화면)가 전송 시작 시점에
 *                        만들어 넘긴다. 같은 방에 같은 키로 재INSERT하면(네트워크 재시도) DB가
 *                        23505로 거부하고, 이 함수는 그 경우 새 행을 만들지 않고 이미 저장된 행을
 *                        조회해 그 행으로 수렴시킨다(Story 12.3, UX-DR15 pending 확정 경로).
 * @returns 성공 { message } / 실패 { error: 한국어 }
 */
export async function sendMessage(
  supabase: SupabaseClient,
  roomId: string,
  senderId: string,
  body: string,
  clientMessageId: string,
): Promise<SendMessageResult> {
  // 1차 차단: 공백만이면 보내지 않는다(DB CHECK가 막기 전에 네트워크·UX 낭비 차단).
  const trimmed = body.trim();
  if (trimmed === '') {
    return { error: '메시지를 입력해주세요.' };
  }
  // 길이 상한 차단(기술부채 #8): DB CHECK(char_length<=2000)가 막기 전에 명확한 한국어로 안내.
  //   입력창 maxLength가 1차 방어지만, 붙여넣기 등 우회 경로의 최종 클라 방어.
  if (trimmed.length > CHAT.MESSAGE_MAX_LENGTH) {
    return { error: `메시지가 너무 깁니다. 최대 ${CHAT.MESSAGE_MAX_LENGTH}자까지 보낼 수 있습니다.` };
  }

  const { data, error } = await supabase
    .from('chat_messages')
    // sender_id는 본인(senderId) — RLS가 auth.uid()=sender_id를 검증. room_id 당사자 여부도 RLS가 본다.
    .insert({ room_id: roomId, sender_id: senderId, body: trimmed, client_message_id: clientMessageId })
    .select('id, room_id, sender_id, body, created_at, client_message_id')
    .single<ChatMessageRow>();

  if (!error && data) return { message: data };

  // 멱등 재전송(23505, UNIQUE(room_id, client_message_id) 위반) — 같은 키로 이미 저장된 행이
  //   있다는 뜻이므로 에러로 보여주지 않고 그 행을 조회해 확정한다(설계된 경로, 대장 #186).
  if (error?.code === PG_UNIQUE_VIOLATION) {
    const { data: existing, error: fetchError } = await supabase
      .from('chat_messages')
      .select('id, room_id, sender_id, body, created_at, client_message_id')
      .eq('room_id', roomId)
      .eq('client_message_id', clientMessageId)
      .single<ChatMessageRow>();
    // 조회된 행이 정말 "이 호출자 자신의 확정된 전송"인지 확인한다(코드리뷰 patch, low) — 이
    //   함수의 계약은 "호출자 자신이 방금 보낸 메시지를 돌려준다"는 것이지 "그 키를 가진 아무 행"이
    //   아니다. UUID 충돌 가능성은 사실상 0에 가깝지만, 명시적으로 확인하지 않으면 그 전제가 코드
    //   어디에도 드러나지 않는다. sender_id·body 둘 다 어긋나면 남의 행(또는 손상된 데이터)일
    //   가능성을 배제할 수 없으므로 성공으로 취급하지 않고 일반 에러로 폴백한다.
    if (!fetchError && existing && existing.sender_id === senderId && existing.body === trimmed) {
      return { message: existing };
    }
    // 여기까지 오면 (a) 기존 행 조회 자체가 실패했거나, (b) 조회는 됐는데 sender_id·body가 이
    //   호출자의 전송과 일치하지 않는 이례적 상황 — 둘 다 일반 에러로 폴백한다.
    console.error('[messages] 멱등 재전송 후 기존 행 조회 실패(또는 불일치):', fetchError, existing);
    return { error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' };
  }

  // 빈 본문 CHECK 위반(클라 1차를 우회한 경우의 최종 방어) → 명확한 한국어 안내.
  if (error?.code === PG_CHECK_VIOLATION) {
    return { error: '빈 메시지는 보낼 수 없습니다.' };
  }

  // 그 외(RLS 거부·네트워크 등) → 일반 한국어 안내. 원본 에러는 여기서 로그로 남긴다.
  console.error('[messages] 메시지 전송 실패:', error);
  return { error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' };
}

// 직전에 실패한 전송의 기억(화면이 들고 있는 값 그대로).
export type FailedSend = { clientMessageId: string; body: string; at: number };

// 오프라인(연결 끊김) 큐에 쌓인 메시지 1건 — 제출 시점에 만든 client_message_id를 그대로 들고 있다가
// 재연결 시 재사용한다(Story 12.4 Always — reuseFailedKey의 시간창 휴리스틱과 달리 새 키를 만들지
// 않는다. 어떤 항목을 재시도하는지 큐 자체가 이미 알고 있어 추측이 필요 없다, Design Notes).
export type QueuedMessage = { clientMessageId: string; body: string };

/**
 * 오프라인 큐를 순서대로(순차 await) flush한다 — 화면(ChatRoomMessages)에서 네트워크·상태를 떼어낸
 * 순수 알고리즘만 여기 둬 vitest로 직접 검증한다(B9 "실행되는 검사로 고정").
 *
 * 규칙(Story 12.4 Always):
 *   - 큐 순서대로 하나씩 sendFn을 호출한다(동시에 여러 건을 보내지 않는다 — 순서 보존).
 *   - 항목이 성공하면 sent에 담고 다음 항목으로 진행한다.
 *   - 항목이 실패하면 그 항목(과 그 뒤로 아직 시도하지 않은 나머지)을 remaining에 그대로 남기고
 *     즉시 멈춘다 — 뒤 항목을 먼저 보내면 순서가 깨지고, 실패한 항목을 버리면 메시지가 유실된다.
 *     다음 재연결 때 이 remaining을 그대로 다시 flush하면 된다(같은 client_message_id 재사용,
 *     23505 흡수 경로로 멱등 — sendFn 쪽 책임).
 *
 * @param queue  현재 큐(순서 보존).
 * @param sendFn 실제 전송 호출(호출부가 기존 sendMessage를 감싸 넘긴다 — 새 API 경로를 만들지 않는다).
 */
export async function flushMessageQueue(
  queue: QueuedMessage[],
  sendFn: (msg: QueuedMessage) => Promise<SendMessageResult>,
): Promise<{ remaining: QueuedMessage[]; sent: ChatMessageRow[] }> {
  const sent: ChatMessageRow[] = [];
  for (let i = 0; i < queue.length; i++) {
    let res: SendMessageResult;
    try {
      res = await sendFn(queue[i]);
    } catch (err) {
      // sendFn이 { error }를 돌려주는 대신 **던지는** 경우도 실패로 똑같이 취급한다(후속 리뷰
      // patch, R6). 안 잡으면 이 함수 전체가 reject하면서, 이 배치에서 이미 성공해 DB에 저장된
      // 앞쪽 행들(sent)이 호출부에 전달되지 않는다 — 그 행들은 mergeIncoming도 못 타고 큐에서도
      // 안 빠져 pending 버블로 남는다. 실패 지점부터 뒤 전부를 remaining으로 남기는 규칙은 error
      // 반환과 동일하다(순서 보존).
      console.error('[messages] 큐 flush 중 전송 예외:', err);
      return { remaining: queue.slice(i), sent };
    }
    if ('error' in res) {
      return { remaining: queue.slice(i), sent };
    }
    sent.push(res.message);
  }
  return { remaining: [], sent };
}

/**
 * "이번 전송이 방금 실패한 그 전송의 재시도인가"를 판정해, 맞으면 재사용할 멱등키를 돌려준다.
 * 아니면 null(호출부가 새 `crypto.randomUUID()`를 만든다).
 *
 * 왜 순수 함수로 빼는가(코드리뷰 patch 2차, low — CLAUDE.md B9 "규칙은 실행되는 검사로"):
 *   이 판정은 서로 반대 방향의 두 결함이 정면으로 맞부딪히는 자리다 —
 *   · 너무 안 쓰면: 실패 후 재시도가 매번 새 키를 만들어 "서버엔 저장됐는데 응답만 유실된" 경우
 *     중복 행이 쌓인다(FR41 멱등 보호가 유일한 재전송 경로에서 발동하지 않음).
 *   · 너무 오래 쓰면: 그 키가 무기한 남아 있다가 한참 뒤 우연히 같은 본문을 보낼 때 재사용돼
 *     23505 → 옛 행으로 수렴하고 새 메시지가 조용히 사라진다.
 *   화면 컴포넌트 안에 인라인으로 두면 어느 방향으로 뒤집혀도 아무 검사가 울지 않아서(이 레포의
 *   web 테스트는 node 환경 vitest라 컴포넌트를 렌더하지 않는다), 판정만 여기로 옮겨 고정한다.
 *
 * @param remembered 직전 실패 기록(없으면 null)
 * @param body       이번에 보내려는 본문(trim된 값)
 * @param now        현재 시각(ms) — 테스트가 시계를 주입할 수 있게 인자로 받는다
 * @param windowMs   재사용이 유효한 시간 창
 */
export function reuseFailedKey(
  remembered: FailedSend | null,
  body: string,
  now: number,
  windowMs: number,
): string | null {
  if (!remembered) return null;
  // 본문이 글자 그대로 같아야 한다 — 사용자가 고쳐서 보내면 그건 새 메시지다.
  if (remembered.body !== body) return null;
  if (now - remembered.at > windowMs) return null;
  return remembered.clientMessageId;
}

/**
 * id 기준 중복 제거 + 시간순 재정렬(append 머지용).
 *   폴링 증분 조회와 "내가 보낸 낙관적 메시지"가 같은 행을 두 번 넣으려 할 때 중복을 막는다(AC#5).
 *   같은 id 재등장 시 첫 등장만 남긴다.
 *
 * 왜 마지막에 (created_at, id)로 정렬하는가(AC#3 "시간 오름차순" 불변식 보장):
 *   [...prev, ...incoming] 머지는 입력 순서를 유지할 뿐 시간순을 보장하지 않는다. 거의 동시에 양쪽이
 *   메시지를 보내면(내 낙관적 전송 T_me 가 상대의 더 이른 T_other 보다 먼저 append) 화면이 시간 역순으로
 *   보일 수 있다. fetchMessages가 쓰는 것과 동일한 (created_at asc, id asc) 안정 정렬로 재정렬해 이를 막는다.
 */
export function dedupeById(messages: ChatMessageRow[]): ChatMessageRow[] {
  const seen = new Set<string>();
  const out: ChatMessageRow[] = [];
  for (const m of messages) {
    if (seen.has(m.id)) continue;
    seen.add(m.id);
    out.push(m);
  }
  // created_at 오름차순, 동시각이면 id로 안정화(fetchMessages의 order와 동일 규칙).
  out.sort((a, b) =>
    a.created_at < b.created_at
      ? -1
      : a.created_at > b.created_at
        ? 1
        : a.id < b.id
          ? -1
          : a.id > b.id
            ? 1
            : 0,
  );
  return out;
}
