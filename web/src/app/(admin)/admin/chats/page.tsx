// 관리자 채팅 관리 — 전체 채팅방 목록 (FR25) — 서버 컴포넌트.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 구성:
//   1) 전체 채팅방 목록 — chat_rooms_select_admin RLS(0005, using=is_admin())로 관리자는 당사자가 아니어도 전체 방을 본다.
//      · (user)/chat/page.tsx는 "내 방"만 보려 했지만(참여자 한정 RLS), 여기선 정반대로 전부 보는 게 목적이라 필터를 뺀다.
//      · 일반 SELECT 정책(chat_rooms_select_participant, 0003)과 admin SELECT가 OR로 결합 → 관리자 세션엔 모든 행이 열린다.
//   2) 행마다: 방 열람 링크(/admin/chats/[roomId]) + 삭제 액션(ChatAdminActions, 클라이언트 컴포넌트).
//      방을 삭제하면 0003의 on delete cascade로 그 방의 메시지(chat_messages)도 함께 제거된다(FR25 "방과 메시지가 제거된다").
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { UNITS } from '@/lib/constants';
import ChatAdminActions from './ChatAdminActions';

// 방 1건 + 임베디드 매물 요약(PostgREST 조인). listings는 단일 객체(FK 단방향).
type AdminChatRoom = {
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

// 당사자 id를 화면 식별용으로 짧게 보여준다(전체 UUID는 길어 가독성↓). 앞 8자. (회원 관리 shortId와 동일 정신)
function shortId(id: string): string {
  return id.slice(0, 8);
}

export default async function AdminChatsPage() {
  const supabase = await createClient();

  // 전체 채팅방 최신순 조회 — 필터를 두지 않는다(관리자는 전부 본다).
  //   chat_rooms_select_admin(0005, using=is_admin())이 모든 방을 반환한다.
  //   매물 요약은 임베디드 조인으로 함께(listings_select_admin로 sold 포함 조회 가능 → 보통 null은 "매물 삭제됨").
  //   최신순(created_at desc) + id 2차정렬(같은 시각 행의 순서 안정화 — chat 목록·search와 동일 정신).
  //   error를 함께 받아 "조회 실패"와 "방 없음"을 구분한다(listings/members 페이지 패턴).
  const { data: rooms, error } = await supabase
    .from('chat_rooms')
    .select(
      'id, listing_id, buyer_id, seller_id, created_at, listings(manufacturer, model, year, price, status)',
    )
    .order('created_at', { ascending: false })
    .order('id', { ascending: false })
    .returns<AdminChatRoom[]>();

  if (error) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/chats] 채팅방 목록 조회 실패:', error);
  }

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">채팅 관리</h1>
        <p className="text-sm text-zinc-500">
          전체 채팅방을 조회하고, 대화 내용을 열람하거나 문제 방을 삭제할 수 있습니다.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        {error ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            채팅방 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !rooms || rooms.length === 0 ? (
          <p className="text-sm text-zinc-500">채팅방이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {rooms.map((room) => {
              const l = room.listings;
              // 매물 임베드가 null = 매물이 삭제된 방(또는 RLS상 조회 불가). 상세 대신 플레이스홀더.
              const summary = l
                ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${l.price.toLocaleString('ko-KR')}${UNITS.price}`
                : '삭제되었거나 조회할 수 없는 매물';
              const createdLabel = new Date(room.created_at).toLocaleString('ko-KR');
              return (
                <li
                  key={room.id}
                  className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
                >
                  <Link
                    href={`/admin/chats/${room.id}`}
                    className="flex flex-1 flex-col gap-0.5 hover:underline"
                  >
                    <span className={l ? 'font-medium' : 'font-medium text-zinc-400'}>
                      {summary}
                    </span>
                    {/* 당사자 식별: 구매자/판매자 id 축약 + 생성일. (이메일은 profiles에 없음 — 6-2 결정) */}
                    <span className="text-xs text-zinc-500">
                      구매자 {shortId(room.buyer_id)} · 판매자 {shortId(room.seller_id)} ·{' '}
                      {createdLabel}
                    </span>
                  </Link>
                  <ChatAdminActions roomId={room.id} label={summary} />
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
