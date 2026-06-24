// 문의 채팅방 진입 (FR19, Story 5-2) — 서버 컴포넌트.
//
// 동작:
//   1) roomId의 방을 조회한다. RLS(chat_rooms_select_participant)상 당사자가 아니면 0건(null) →
//      "찾을 수 없음/접근 불가" 안내(존재하지 않는 방·삭제·제3자 접근을 한데 묶어 안내 — 정보 누출 방지).
//   2) 당사자면 매물 요약·상대 헤더 + 메시지 영역의 "빈 골격"을 보여준다.
//
// 메시지 송수신·폴링(Story 5-3): 당사자면 메시지 영역에 <ChatRoomMessages>(클라이언트 컴포넌트)를 렌더한다.
//   전송(INSERT 영속)·폴링 수신(3초)·내/상대 구분 목록은 그 컴포넌트가 담당. 이 서버 페이지는 "당사자 확인 +
//   본인 id 전달"까지만 한다(RLS로 방을 못 읽으면 아래에서 이미 "찾을 수 없음" 안내로 빠진다).
//
// 보호: proxy가 /chat 비로그인 1차 차단. 참여자 한정은 RLS가 집행. force-dynamic(매 요청 최신 상태).
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, UNITS, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';
import ChatRoomMessages from './ChatRoomMessages';

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
  // 매물 임베드가 null = 판매완료(sold)거나 구매자 RLS상 조회 불가한 매물.
  //   FR11(판매완료 매물은 구매자의 모든 경로에서 비노출 — 프로젝트 핵심 단일 규칙)을 지켜
  //   매물 상세 정보는 노출하지 않고 플레이스홀더만 보인다. 대화방은 살아 있어 채팅은 그대로 가능.
  //   [Decision 옵션D] sold를 다시 보이게 하지 않는다(RLS 확대·스냅샷·서버우회 채택 안 함).
  const summary = l
    ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${l.price.toLocaleString('ko-KR')}${UNITS.price}`
    : '판매 완료되었거나 조회할 수 없는 매물';

  return (
    <>
      {header}
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        {/* 방 헤더 — 어떤 매물·누구와의 대화인지 (매물이 안 보이면 플레이스홀더 — FR11 준수) */}
        <section className="flex flex-col gap-1">
          <div className="flex items-center justify-between gap-2">
            <h1 className={l ? 'text-xl font-semibold' : 'text-xl font-semibold text-zinc-400'}>
              {summary}
            </h1>
          </div>
          <p className="text-sm text-zinc-500">{counterpart}와의 문의 채팅</p>
        </section>

        {/* 메시지 영역 — 송수신·폴링(5-3). 당사자 확인이 끝난 지점이므로 본인 id를 내려 RLS 전송을 통과시킨다.
            user.id가 없는 비정상 상황(여기 도달 전 proxy·RLS가 막지만)엔 안내로 폴백(방어). */}
        {user?.id ? (
          <ChatRoomMessages roomId={room.id} myUserId={user.id} />
        ) : (
          <p
            role="alert"
            className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
          >
            로그인이 필요합니다. 다시 로그인해주세요.
          </p>
        )}

        {backLink}
      </main>
    </>
  );
}
