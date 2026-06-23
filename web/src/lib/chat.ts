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

// 방을 연 결과 — 성공이면 roomId, 실패면 사용자에게 보여줄 한국어 메시지.
//   (원본 에러는 호출부가 console.error로만 남기고, 사용자에겐 이 한국어만 보여준다 — ListingActions와 동일 규칙.)
export type OpenRoomResult = { roomId: string } | { error: string };

// Postgres SQLSTATE 코드(통신선으로는 error.code에 그대로 실려 온다).
const PG_UNIQUE_VIOLATION = '23505'; // UNIQUE 제약 위반(경합으로 같은 방을 동시에 만들려 함)
const PG_CHECK_VIOLATION = '23514'; // CHECK 위반(여기선 buyer_id <> seller_id = 본인 매물 문의)

// (listing_id, buyer_id)로 기존 방을 1건 조회. 없으면 null, 있으면 그 방의 id.
async function findExistingRoom(
  supabase: SupabaseClient,
  listingId: string,
  buyerId: string,
): Promise<{ id: string } | null> {
  const { data } = await supabase
    .from('chat_rooms')
    .select('id')
    .eq('listing_id', listingId)
    .eq('buyer_id', buyerId)
    .maybeSingle<{ id: string }>();
  return data ?? null;
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
  if (existing) return { roomId: existing.id };

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
    if (raced) return { roomId: raced.id };
  }

  // 4) 본인 매물 문의(buyer=seller) → CHECK 위반(23514). 명확한 한국어 안내(AC#6 DB측 이중 방어).
  if (error?.code === PG_CHECK_VIOLATION) {
    return { error: '본인 매물에는 문의할 수 없습니다.' };
  }

  // 5) 그 외(네트워크·RLS·없는 매물 등) → 일반 한국어 안내. 원본 에러는 호출부가 로그로 남긴다.
  console.error('[chat] 채팅방 생성 실패:', error);
  return { error: '채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.' };
}
