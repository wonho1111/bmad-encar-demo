// 문의 채팅방 "생성 또는 재사용" 규칙의 단일 출처 (FR19, Story 5-2).
//
// 왜 한 곳에 모으나(@/lib/listings의 buyerListingsQuery와 같은 정신):
//   "같은 매물·구매자면 방을 새로 만들지 말고 기존 방을 재사용한다"는 규칙이 여러 곳에 흩어지면
//   드리프트(drift, 규칙이 조금씩 어긋남)가 생긴다. 그래서 이 함수 한 곳에서만 방을 연다.
//
// 핵심 — DB가 보장하는 무결성을 신뢰한다(supabase/migrations/0003c_chat_room_integrity.sql):
//   chat_rooms BEFORE INSERT 트리거가 seller_id를 "그 매물(listing_id)의 실제 소유자"로 강제 덮어쓴다.
//   → 클라이언트는 seller_id를 보낼 필요가 없다(보내도 무시됨). insert에는 listing_id·buyer_id만 넣는다.
//   → 같은 (listing_id, buyer_id)는 항상 같은 seller로 귀결되므로, 이 두 컬럼만으로 방을 유일하게 찾을 수 있다.
//
// 동작(select-first 후 insert, 경합은 재조회로 흡수):
//   1) 먼저 (listing_id, buyer_id)로 기존 방을 찾는다 → 있으면 그 방 재사용(중복 생성 방지).
//   2) 없으면 insert(listing_id, buyer_id) → 트리거가 seller_id를 매물주로 채운다.
//   3) 거의 동시에 두 번 눌려 UNIQUE(23505) 충돌이 나면, 그새 만들어진 방을 다시 조회해 그 id를 돌려준다.
//   4) 본인 매물에 문의(buyer=seller)면 트리거 후 CHECK(buyer_id<>seller_id) 위반(23514) → 한국어 거부.
import type { SupabaseClient } from '@supabase/supabase-js';
import { formatPrice } from './price';

// 방을 연 결과 — 성공이면 roomId, 실패면 사용자에게 보여줄 한국어 메시지.
//   (원본 에러는 호출부가 console.error로만 남기고, 사용자에겐 이 한국어만 보여준다 — ListingActions와 동일 규칙.)
export type OpenRoomResult = { roomId: string } | { error: string };

// 채팅 목록(chat/page.tsx)·방 상세(chat/[roomId]/page.tsx)가 공유하는 매물 임베드 형태.
export type ChatListingSummarySource = {
  manufacturer: string;
  model: string;
  year: number;
  price: number;
} | null;

/**
 * 채팅 목록·방 상세가 공유하는 매물 요약 문구 — `listings` 임베드가 null이면 대체 문구로 폴백한다
 * (Story 5-2 원본 로직, Story 17.4 코드리뷰 patch로 두 페이지 중복을 이 함수 하나로 모음).
 *
 * 임베드가 null이 되는 원인은 최소 두 가지다: **①** `status='sold'`(FR11, 판매완료 비노출) **②**
 * 판매자가 정지됨(Story 17.4, DW-804(a) — `listings_select_on_sale`/`_anon`이 이제 판매자가
 * 활성인지도 함께 본다, `supabase/migrations/0035_hide_suspended_seller_listings.sql`). 이 함수는
 * **그 두 원인을 구분하지 않는다** — PostgREST의 임베드 null은 "RLS가 이 행을 안 보여줬다"만
 * 알려줄 뿐 어느 정책이 막았는지는 알려주지 않으므로, 애초에 구분할 방법이 없다. 그래서 문구도
 * 하나("판매 완료되었거나 조회할 수 없는 매물")로 두 원인을 함께 흡수한다 — 새 문구를 만들지
 * 않고 기존 sold 문구를 그대로 재사용하는 이유이기도 하다. 대화방 자체는 이 함수와 무관하게
 * 계속 열린다(당사자 RLS는 `chat_rooms`를 직접 보지 `listings`를 경유하지 않는다).
 */
export function chatListingSummary(l: ChatListingSummarySource): string {
  return l
    ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${formatPrice(l.price)}`
    : '판매 완료되었거나 조회할 수 없는 매물';
}

// Postgres SQLSTATE 코드(통신선으로는 error.code에 그대로 실려 온다).
const PG_UNIQUE_VIOLATION = '23505'; // UNIQUE 제약 위반(경합으로 같은 방을 동시에 만들려 함)
const PG_CHECK_VIOLATION = '23514'; // CHECK 위반(여기선 buyer_id <> seller_id = 본인 매물 문의)
const PG_FK_VIOLATION = '23503'; // FK 위반(여기선 없는 매물 — 0003c 트리거가 같은 코드로 거부)

// (listing_id, buyer_id)로 기존 방을 1건 조회.
//   반환: { room } 조회 성공(방 없으면 room=null) / { error } 조회 자체 실패.
//   조회 실패를 "방 없음(null)"과 구분해야 한다 — 안 그러면 읽기 오류를 "없음"으로 오인해
//   불필요한 insert를 시도하고, 진짜 실패가 로그에도 안 남는다(code-review Medium 지적 반영).
async function findExistingRoom(
  supabase: SupabaseClient,
  listingId: string,
  buyerId: string,
): Promise<{ room: { id: string } | null } | { error: true }> {
  const { data, error } = await supabase
    .from('chat_rooms')
    .select('id')
    .eq('listing_id', listingId)
    .eq('buyer_id', buyerId)
    .maybeSingle<{ id: string }>();
  if (error) {
    console.error('[chat] 기존 방 조회 실패:', error);
    return { error: true };
  }
  return { room: data ?? null };
}

/**
 * 그 매물의 판매자와의 채팅방을 연다(있으면 재사용, 없으면 생성).
 *
 * @param supabase  브라우저 Supabase 클라이언트(@/lib/supabase/client). RLS 경유로 안전.
 * @param listingId 문의 대상 매물 id.
 * @param buyerId   현재 로그인 사용자 id(구매자). 방의 buyer_id가 된다.
 * @returns 성공 { roomId } / 실패 { error: 한국어 }
 */
export async function openOrCreateRoom(
  supabase: SupabaseClient,
  listingId: string,
  buyerId: string,
): Promise<OpenRoomResult> {
  // 1) 기존 방 재사용 우선 (AC#2)
  const existing = await findExistingRoom(supabase, listingId, buyerId);
  if ('error' in existing) {
    // 조회 자체가 실패 → "방 없음"으로 오인해 insert하지 않고 즉시 일반 안내(읽기 오류는 위에서 로그됨).
    return { error: '채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' };
  }
  if (existing.room) return { roomId: existing.room.id };

  // 2) 없으면 생성. seller_id는 보내지 않는다(트리거가 매물주로 강제 — 위조 차단·자동 연결).
  const { data: created, error } = await supabase
    .from('chat_rooms')
    .insert({ listing_id: listingId, buyer_id: buyerId })
    .select('id')
    .single<{ id: string }>();

  if (!error && created) return { roomId: created.id };

  // 3) UNIQUE 경합(23505): 그새 다른 탭/요청이 만든 방을 다시 찾아 재사용.
  if (error?.code === PG_UNIQUE_VIOLATION) {
    const raced = await findExistingRoom(supabase, listingId, buyerId);
    if (!('error' in raced) && raced.room) return { roomId: raced.room.id };
  }

  // 4) 본인 매물 문의(buyer=seller) → CHECK 위반(23514). 명확한 한국어 안내(AC#6 DB측 이중 방어).
  if (error?.code === PG_CHECK_VIOLATION) {
    return { error: '본인 매물에는 문의할 수 없습니다.' };
  }

  // 5) 없는 매물(23503 — 0003c 트리거가 거부): 삭제·판매완료된 매물일 수 있음. 명확한 한국어 안내.
  if (error?.code === PG_FK_VIOLATION) {
    return { error: '해당 매물을 찾을 수 없습니다. 삭제되었거나 판매가 완료된 매물일 수 있습니다.' };
  }

  // 6) 그 외(네트워크·RLS 등) → 일반 한국어 안내. 원본 에러는 여기서 로그로 남긴다.
  console.error('[chat] 채팅방 생성 실패:', error);
  return { error: '채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' };
}

/**
 * 방 진입 시 본인의 "마지막으로 읽은 시각"을 지금 시각으로 기록한다(FR57, Story 12.5).
 *
 * 안읽음 배지(chat_unread_count RPC)는 이 값보다 늦은 상대방 메시지 수로 계산되므로,
 * 방을 열 때마다 이 함수를 호출해야 다음 조회부터 그 방의 과거 메시지가 배지 집계에서 빠진다.
 * 방이 열려 있는 동안 실시간으로 도착하는 메시지에는 다시 호출하지 않는다(진입 1회로 한정 — 스펙
 * Never 절, `ChatRoomMessages.tsx`의 구독·큐 상태기계에는 손대지 않는다).
 *
 * 실패해도 화면을 막지 않는다(배지는 부가 정보) — 콘솔 로그만 남기고 호출부는 결과를 기다리지 않아도 된다.
 *
 * @param supabase 서버 컴포넌트 Supabase 클라이언트(@/lib/supabase/server). RLS(당사자 검사)를 경유.
 * @param roomId   진입한 방 id.
 * @param userId   현재 로그인 사용자 id.
 */
export async function markChatRoomRead(
  supabase: SupabaseClient,
  roomId: string,
  userId: string,
): Promise<void> {
  const { error } = await supabase
    .from('chat_room_reads')
    .upsert(
      { user_id: userId, room_id: roomId, last_read_at: new Date().toISOString() },
      { onConflict: 'user_id,room_id' },
    );

  if (error) {
    console.error('[chat] 읽음 상태 갱신 실패:', error);
  }
}
