// 문의 채팅방 진입 (FR19, Story 5-2) — 서버 컴포넌트.
//
// 동작:
//   1) roomId의 방을 조회한다. RLS(chat_rooms_select_participant)상 당사자가 아니면 0건(null) →
//      "찾을 수 없음/접근 불가" 안내(존재하지 않는 방·삭제·제3자 접근을 한데 묶어 안내 — 정보 누출 방지).
//   2) 당사자면 매물 요약·상대 헤더 + 메시지 영역의 "빈 골격"을 보여준다.
//
// ⚠️ 범위(Story 5-2): 방 진입까지만. 메시지 입력·전송·폴링(주고받기)은 5-3에서 구현한다.
//    그래서 여기엔 입력창·전송 버튼·폴링이 없다(과구현 금지). 메시지 영역은 안내 박스만 둔다.
//
// 보호: proxy가 /chat 비로그인 1차 차단. 참여자 한정은 RLS가 집행. force-dynamic(매 요청 최신 상태).
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, UNITS, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';

export const dynamic = 'force-dynamic';

type ChatRoomDetail = {
  id: string;
  listing_id: string;
  buyer_id: string;
  seller_id: string;
  listings: {
    manufacturer: string;
    model: string;
    year: number;
    price: number;
    status: string;
  } | null;
};

export default async function ChatRoomPage({
  params,
}: {
  params: Promise<{ roomId: string }>;
}) {
  const { roomId } = await params; // Next.js 16: params는 Promise라 await 필요.
  const supabase = await createClient();

  // 상단바용 역할 라벨 + 본인 식별(상대 표기·당사자 판정).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 방 조회 — RLS상 당사자가 아니면 0건(null). maybeSingle()로 0건을 에러가 아닌 null로 받는다.
  const { data: room, error } = await supabase
    .from('chat_rooms')
    .select(
      'id, listing_id, buyer_id, seller_id, listings(manufacturer, model, year, price, status)',
    )
    .eq('id', roomId)
    .maybeSingle<ChatRoomDetail>();

  if (error) {
    console.error('[chat/room] 채팅방 조회 실패:', error);
  }

  const header = <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} />;

  const backLink = (
    <Link
      href="/chat"
      className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
    >
      채팅방 목록으로
    </Link>
  );

  // 조회 실패(네트워크·DB) — "못 찾음"과 구분해 빨강 에러 안내.
  if (error) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
          <h1 className="text-2xl font-semibold">문의 채팅</h1>
          <p
            role="alert"
            className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300"
          >
            채팅방을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
          </p>
          {backLink}
        </main>
      </>
    );
  }

  // 못 찾음(없는 방·삭제·제3자 접근으로 RLS 0건) — 한 안내로 묶는다(어느 경우인지 노출하지 않음).
  if (!room) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
          <h1 className="text-2xl font-semibold">문의 채팅</h1>
          <p
            role="alert"
            className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
          >
            채팅방을 찾을 수 없습니다. 접근 권한이 없거나 삭제된 방일 수 있습니다.
          </p>
          {backLink}
        </main>
      </>
    );
  }

  // 당사자 — 매물 요약·상대 헤더 + 메시지 빈 골격.
  const iAmBuyer = user?.id === room.buyer_id;
  const counterpart = iAmBuyer ? '판매자' : '구매자';
  const l = room.listings;
  const summary = l
    ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${l.price.toLocaleString('ko-KR')}${UNITS.price}`
    : '매물 정보 없음';
  const sold = l?.status === 'sold';

  return (
    <>
      {header}
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        {/* 방 헤더 — 어떤 매물·누구와의 대화인지 */}
        <section className="flex flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <h1 className="text-xl font-semibold">{summary}</h1>
            {sold && (
              <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400">
                판매완료
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-500">{counterpart}와의 문의 채팅</p>
        </section>

        {/* 메시지 영역(빈 골격) — 송수신은 5-3에서. 지금은 안내 박스만. */}
        <section
          aria-label="메시지"
          className="flex min-h-40 flex-col items-center justify-center rounded border border-dashed border-zinc-300 p-6 text-center text-sm text-zinc-500 dark:border-zinc-700"
        >
          아직 주고받은 메시지가 없습니다.
          <br />
          메시지 송수신 기능은 곧 제공됩니다.
        </section>

        {backLink}
      </main>
    </>
  );
}
