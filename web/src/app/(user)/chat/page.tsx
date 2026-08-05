// 문의 채팅방 목록 (FR19, Story 5-2) — 서버 컴포넌트.
//
// 동작:
//   1) 로그인 사용자가 당사자(구매자 또는 판매자)인 채팅방만 보여준다.
//      · 필터를 따로 걸지 않아도 RLS(chat_rooms_select_participant)가 "내 방"만 통과시킨다(제3자 0건).
//   2) 각 방은 매물 요약 + 내 역할에 따른 상대 표기와 함께, 클릭하면 그 대화(/chat/[roomId])로 진입.
//   3) 방이 없으면 빈 상태 안내. 조회 실패는 "없음"과 구분해 한국어 에러 안내(search/sell 패턴).
//
// 보호: proxy가 /chat 비로그인 1차 차단. 역할 게이트 없음(구매자·판매자 공통).
//
// 매 요청 최신 DB 상태를 반영해야 하므로(새 방·sold 변화 즉시) force-dynamic.
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, UNITS, USER_ROLE, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';

export const dynamic = 'force-dynamic';

// 방 1건 + 임베디드 매물 요약(PostgREST 조인). listings는 단일 객체로 온다(FK 단방향).
type ChatRoomRow = {
  id: string;
  listing_id: string;
  buyer_id: string;
  seller_id: string;
  buyer_name: string | null; // 상대 표기용 표시 이름(이메일 @앞부분, 0008)
  seller_name: string | null;
  created_at: string;
  listings: {
    manufacturer: string;
    model: string;
    year: number;
    price: number;
    status: string;
  } | null;
};

export default async function ChatListPage() {
  const supabase = await createClient();

  // 상단바용 역할 라벨 + 본인 식별(내가 buyer인지 seller인지로 상대 표기를 정한다).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  let roleLabel: string | null = null;
  // 빈 상태 안내 문구를 역할에 맞게 분기하려고 원시 role 값도 보관한다(판매자는 문의를 '받는' 입장).
  let role: UserRole | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      role = profile.role as UserRole;
      roleLabel = ROLE_LABEL[role] ?? profile.role;
    }
  }

  // 내 채팅방 목록 — RLS가 참여자 방만 통과시키므로 별도 필터 불필요. 매물 요약은 임베디드 조회로 함께.
  //   최신 문의 순(last_message_at desc, FR57·Story 12.5 — 방 생성순이 아니라 마지막 메시지 시각순)
  //   + id 2차정렬(같은 시각 행의 순서 안정화 — search 페이지와 동일 정신).
  const { data: rooms, error } = await supabase
    .from('chat_rooms')
    .select(
      'id, listing_id, buyer_id, seller_id, buyer_name, seller_name, created_at, listings(manufacturer, model, year, price, status)',
    )
    .order('last_message_at', { ascending: false })
    .order('id', { ascending: false })
    .returns<ChatRoomRow[]>();

  if (error) {
    // 원본은 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분.
    console.error('[chat/list] 채팅방 목록 조회 실패:', error);
  }

  // 방별 안읽음 수(DW-548) — `chat_unread_by_room()`(0026)이 안읽음이 있는 방만 행으로 준다.
  //   행이 없는 방 = 0건이므로 Map에서 못 찾으면 0으로 읽는다.
  //   조회 실패는 배지 없음으로 폴백한다 — 배지는 부가 정보라 방 목록 렌더 자체를 막지 않는다
  //   (AppHeader의 총합 배지와 같은 방침). 비로그인은 여기 도달하지 않지만(proxy 차단) 방어적으로 건너뛴다.
  const unreadByRoom = new Map<string, number>();
  if (user) {
    const { data: unreadRows, error: unreadError } = await supabase.rpc('chat_unread_by_room');
    if (unreadError) {
      console.error('[chat/list] 방별 안읽음 조회 실패:', unreadError);
    } else if (Array.isArray(unreadRows)) {
      for (const row of unreadRows as { room_id: string; unread: number }[]) {
        unreadByRoom.set(row.room_id, row.unread);
      }
    }
  }

  return (
    <>
      <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} currentPath="/chat" />
      <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
        <section className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">문의 채팅</h1>
          <p className="text-sm text-zinc-500">매물 문의로 시작된 채팅방 목록입니다.</p>
        </section>

        <section className="flex flex-col gap-3">
          {error ? (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              채팅방 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.
            </p>
          ) : !rooms || rooms.length === 0 ? (
            // 역할별 빈 상태: 구매자는 '문의하기를 눌러 시작', 판매자는 '문의가 들어오면 생긴다'(받는 입장).
            <p className="text-sm text-zinc-500">
              {role === USER_ROLE.SELLER
                ? '아직 들어온 문의가 없습니다. 구매자가 매물에 문의하면 여기에 채팅방이 생깁니다.'
                : '아직 문의한 채팅방이 없습니다. 매물 상세에서 ‘문의하기’를 눌러보세요.'}
            </p>
          ) : (
            <ul className="flex flex-col gap-2">
              {rooms.map((room) => {
                // 내가 구매자면 상대는 판매자, 판매자면 상대는 구매자. (한 방엔 정확히 두 당사자.)
                const iAmBuyer = user?.id === room.buyer_id;
                // 상대 표시 이름(이메일 @앞부분, 0008). 없으면 역할만 표기로 폴백.
                const counterpartName = iAmBuyer ? room.seller_name : room.buyer_name;
                const counterpart = iAmBuyer
                  ? counterpartName
                    ? `판매자 ${counterpartName}에게 문의`
                    : '판매자에게 문의'
                  : counterpartName
                    ? `구매자 ${counterpartName} 문의`
                    : '구매자 문의';
                const l = room.listings;
                // 매물 임베드가 null = 판매완료(sold)거나 구매자 RLS상 조회 불가한 매물.
                //   FR11(판매완료 매물은 구매자의 모든 경로에서 비노출 — 프로젝트 핵심 단일 규칙)을 지켜
                //   상세 정보(제조사·모델·가격)는 노출하지 않고 플레이스홀더만 보인다.
                //   [Decision 옵션D] sold를 다시 보이게 하지 않는다(RLS 확대·스냅샷·서버우회 채택 안 함).
                //   대화방 자체는 살아 있으므로 행은 그대로 클릭 가능(/chat/[roomId] 진입은 정상).
                const summary = l
                  ? `[${l.manufacturer}] ${l.model} · ${l.year}년 · ${l.price.toLocaleString('ko-KR')}${UNITS.price}`
                  : '판매 완료되었거나 조회할 수 없는 매물';
                const unread = unreadByRoom.get(room.id) ?? 0;
                return (
                  <li key={room.id}>
                    <Link
                      href={`/chat/${room.id}`}
                      className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm hover:bg-zinc-50 dark:border-zinc-800 dark:hover:bg-zinc-900"
                    >
                      <span className="flex flex-col gap-0.5">
                        <span className={l ? 'font-medium' : 'font-medium text-zinc-400'}>
                          {summary}
                        </span>
                        <span className="text-xs text-zinc-500">{counterpart}</span>
                      </span>
                      {/* 방별 안읽음 배지(DW-548) — 0이면 아무것도 그리지 않는다(빈 잉크 금지).
                          내비 총합 배지(SiteNav)와 **같은 규칙**으로 만든다: 색만으로 알리지 않도록
                          숫자를 함께 넣고, 눈에 보이는 숫자는 99에서 눌러 작은 원이 깨지지 않게 하되
                          aria-label엔 정확한 건수를 넣는다(UX-DR22 비색 신호 중복 — 상한은 레이아웃
                          사정이지 낭독 사정이 아니다). bg-red-600은 흰 글자 대비 4.83:1로 AA 통과. */}
                      <span className="flex shrink-0 items-center gap-2">
                        {unread > 0 && (
                          <span
                            aria-label={`안읽음 메시지 ${unread}건`}
                            className="flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1.5 text-[11px] font-semibold leading-none text-white"
                          >
                            {unread > 99 ? '99+' : unread}
                          </span>
                        )}
                        <span className="text-xs text-zinc-400">대화 열기 →</span>
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
    </>
  );
}
