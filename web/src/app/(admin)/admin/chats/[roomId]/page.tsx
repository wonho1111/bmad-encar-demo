// 관리자 채팅방 대화 열람 (FR25) — 서버 컴포넌트, 조회 전용.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// (user)/chat/[roomId]와의 차이(이게 핵심):
//   · 당사자 한정이 아니다 — chat_rooms_select_admin·chat_messages_select_admin(0005)으로 관리자는
//     당사자가 아니어도 방·메시지 전문을 본다(감독 목적).
//   · 송수신·폴링이 없다 — 관리자는 대화에 끼지 않고 읽기만 한다. 그래서 (user) 화면이 쓰는
//     클라이언트 컴포넌트(ChatRoomMessages, setInterval 폴링·INSERT 전송)를 쓰지 않고,
//     서버에서 chat_messages를 시간순 1회 조회해 정적으로 렌더한다.
//   · force-dynamic — 조회 전용이지만 매 진입 시 최신 대화를 반영해야 하므로 캐시하지 않는다.
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { UNITS } from '@/lib/constants';

export const dynamic = 'force-dynamic';

type AdminChatRoomDetail = {
  id: string;
  listing_id: string;
  buyer_id: string;
  seller_id: string;
  created_at: string;
  listings: {
    manufacturer: string;
    model: string;
    year: number;
    price: number;
    status: string;
  } | null;
};

type AdminChatMessage = {
  id: string;
  sender_id: string;
  body: string;
  created_at: string;
};

export default async function AdminChatRoomPage({
  params,
}: {
  params: Promise<{ roomId: string }>;
}) {
  const { roomId } = await params; // Next.js 16: params는 Promise라 await 필요.
  const supabase = await createClient();

  const backLink = (
    <Link
      href="/admin/chats"
      className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
    >
      채팅 관리로
    </Link>
  );

  // 방 단건 조회 — admin RLS(chat_rooms_select_admin)로 당사자가 아니어도 조회된다.
  //   maybeSingle()로 0건(없는 방·삭제됨)을 에러가 아닌 null로 받는다.
  const { data: room, error: roomError } = await supabase
    .from('chat_rooms')
    .select(
      'id, listing_id, buyer_id, seller_id, created_at, listings(manufacturer, model, year, price, status)',
    )
    .eq('id', roomId)
    .maybeSingle<AdminChatRoomDetail>();

  if (roomError) {
    console.error('[admin/chats/room] 채팅방 조회 실패:', roomError);
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">채팅방 대화</h1>
        <p
          role="alert"
          className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
        >
          채팅방을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
        </p>
        {backLink}
      </main>
    );
  }

  if (!room) {
    // 없는 방·삭제된 방 — 한 안내로 묶는다.
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">채팅방 대화</h1>
        <p
          role="alert"
          className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
        >
          채팅방을 찾을 수 없습니다. 삭제된 방일 수 있습니다.
        </p>
        {backLink}
      </main>
    );
  }

  // 그 방의 메시지 전문을 시간순(오래된→최신)으로 1회 조회 — admin RLS(chat_messages_select_admin)로 전문 열람.
  //   created_at asc + id asc 안정 정렬(동시각 행 순서 안정화 — (user)/chat·search와 동일 규칙).
  const { data: messages, error: msgError } = await supabase
    .from('chat_messages')
    .select('id, sender_id, body, created_at')
    .eq('room_id', roomId)
    .order('created_at', { ascending: true })
    .order('id', { ascending: true })
    .returns<AdminChatMessage[]>();

  if (msgError) {
    console.error('[admin/chats/room] 메시지 조회 실패:', msgError);
  }

  const l = room.listings;
  // 매물 임베드 null = 매물이 삭제된 방. 상세 대신 플레이스홀더.
  const summary = l
    ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${l.price.toLocaleString('ko-KR')}${UNITS.price}`
    : '삭제되었거나 조회할 수 없는 매물';

  // 보낸 사람 라벨 — sender_id를 방의 buyer/seller와 대조해 "구매자"/"판매자"로, 그 외는 "기타".
  //   (profiles엔 이메일이 없어(6-2 결정) admin anon-key로 타인 이메일 조회 불가 → 역할 라벨 + id 축약으로 식별.)
  function senderLabel(senderId: string): string {
    if (senderId === room!.buyer_id) return '구매자';
    if (senderId === room!.seller_id) return '판매자';
    return '기타';
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
      {/* 방 헤더 — 어떤 매물·누구 사이의 대화인지 */}
      <section className="flex flex-col gap-1">
        <h1 className={l ? 'text-xl font-semibold' : 'text-xl font-semibold text-zinc-400'}>
          {summary}
        </h1>
        <p className="text-sm text-zinc-500">
          구매자 {room.buyer_id.slice(0, 8)} ↔ 판매자 {room.seller_id.slice(0, 8)} 의 문의 채팅 (열람
          전용)
        </p>
      </section>

      {/* 메시지 영역 — 조회 전용(폴링·전송 없음). 서버에서 시간순 1회 로드한 전문. */}
      <section aria-label="대화 내용" className="flex flex-col gap-2">
        {msgError ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            대화 내용을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
          </p>
        ) : !messages || messages.length === 0 ? (
          <p className="rounded border border-zinc-200 p-4 text-center text-sm text-zinc-500 dark:border-zinc-800">
            메시지가 없습니다.
          </p>
        ) : (
          <ul className="flex flex-col gap-2 rounded border border-zinc-200 p-4 dark:border-zinc-800">
            {messages.map((m) => (
              <li key={m.id} className="flex flex-col gap-0.5">
                <span className="text-xs text-zinc-500">
                  {senderLabel(m.sender_id)} · {new Date(m.created_at).toLocaleString('ko-KR')}
                </span>
                {/* whitespace-pre-wrap: 줄바꿈 보존. 본문은 사용자 입력이라 React 기본 이스케이프로 XSS 안전. */}
                <span className="whitespace-pre-wrap text-sm">{m.body}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {backLink}
    </main>
  );
}
