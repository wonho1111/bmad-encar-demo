// 채팅 메시지 "조회·전송 규칙"의 단일 출처 (FR20·FR21, Story 5-3).
//
// 왜 한 곳에 모으나(@/lib/chat.ts의 openOrCreateRoom과 같은 정신):
//   "메시지를 어떻게 시간순으로 증분 조회하고, 어떻게 보내고, 에러를 어떻게 한국어로 바꾸나"라는 규칙이
//   화면 컴포넌트 곳곳에 흩어지면 드리프트(drift, 규칙이 조금씩 어긋남)가 생긴다. 그래서 이 모듈 한 곳에 모은다.
//
// 핵심 — DB(0003_chat.sql)가 보장하는 것을 신뢰한다:
//   · chat_messages_insert_participant RLS: auth.uid() = sender_id AND 그 방의 당사자일 때만 INSERT.
//     → sendMessage는 sender_id에 "본인 id"를 넣어야 통과한다(남의 명의 위조·끼어들기는 DB가 막음).
//   · chat_messages_select_participant RLS: 그 방의 당사자만 SELECT(제3자 0건).
//   · CHECK(length(btrim(body)) > 0): 공백만 메시지 거부(빈값 전송 시 23514). 클라가 1차로 trim() 차단.
//   · 인덱스 chat_messages_room_created_idx (room_id, created_at): 아래 증분 조회를 커버.
//
// 통신선/컬럼은 snake_case(AR5): room_id, sender_id, created_at, body.
import type { SupabaseClient } from '@supabase/supabase-js';
import { CHAT } from '@/lib/constants';

// 메시지 1건(통신선 그대로 snake_case). created_at은 ISO 문자열(timestamptz).
export type ChatMessageRow = {
  id: string;
  room_id: string;
  sender_id: string;
  body: string;
  created_at: string;
};

// Postgres SQLSTATE 코드(통신선 error.code에 그대로 실려 온다).
const PG_CHECK_VIOLATION = '23514'; // CHECK 위반(여기선 빈 본문 = body_not_blank)

/**
 * 한 방의 메시지를 시간순(오래된→최신)으로 조회한다.
 *
 * @param supabase       브라우저 Supabase 클라이언트(@/lib/supabase/client). RLS 경유라 "내 방"만 보인다.
 * @param roomId         조회할 방 id.
 * @param atOrAfterCreatedAt (선택) 폴링 증분용 커서. 주면 이 시각 "이상(>=)"의 메시지만 가져온다.
 *                       처음 로드는 생략(전체), 이후 폴링은 마지막 받은 created_at을 넘긴다.
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
    .select('id, room_id, sender_id, body, created_at')
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
 * @param supabase  브라우저 Supabase 클라이언트.
 * @param roomId    보낼 방 id.
 * @param senderId  보내는 사람 = 현재 로그인 사용자 id(본인). RLS가 auth.uid()=sender_id를 강제하므로 본인 id여야 통과.
 * @param body      메시지 본문. 앞뒤 공백은 잘라 저장한다.
 * @returns 성공 { message } / 실패 { error: 한국어 }
 */
export async function sendMessage(
  supabase: SupabaseClient,
  roomId: string,
  senderId: string,
  body: string,
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
    .insert({ room_id: roomId, sender_id: senderId, body: trimmed })
    .select('id, room_id, sender_id, body, created_at')
    .single<ChatMessageRow>();

  if (!error && data) return { message: data };

  // 빈 본문 CHECK 위반(클라 1차를 우회한 경우의 최종 방어) → 명확한 한국어 안내.
  if (error?.code === PG_CHECK_VIOLATION) {
    return { error: '빈 메시지는 보낼 수 없습니다.' };
  }

  // 그 외(RLS 거부·네트워크 등) → 일반 한국어 안내. 원본 에러는 여기서 로그로 남긴다.
  console.error('[messages] 메시지 전송 실패:', error);
  return { error: '메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.' };
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
