// 홈 / 로그인 후 첫 화면 (FR2) — 서버 컴포넌트.
//
// 메인화면 개편(2026-06-24, party-mode 결정 / nav-ia-rules.md):
//   로그인 사용자(구매자·판매자)의 홈을 "버튼 허브"에서 "1순위 과업으로 바로 착지"로 바꾼다.
//   ① 본인 정보 영역(역할·이메일) — "내가 누구로 로그인했나"를 한눈에(역할 기반 서비스의 핵심).
//   ② 인기/최신 매물 그리드(Story 11.4) — 인기(view_count desc)·최신(created_at desc) 각 4건을
//      홈에 바로 노출 + '전체 보기'→/search. 로그인·비로그인 양쪽 분기에 동일하게 렌더한다.
//      ⚠️ 홈은 필터·URL 상태를 소유하지 않는다(읽기 전용 발췌). 본격 탐색·필터는 /search가 소유.
//         → 검색 로직 이원화·회귀 방지. ListingCard를 그대로 재사용해 표시 로직도 단일 출처.
//   ③ AI 검색 — 페이지 한구석 버튼이 아니라 "어디서든 닿는 전역 진입"으로 떠 있는 버튼(R3).
//
// 관리자는 여기서 /admin으로 랜딩 유도(아래 분기). 보호 경로 "차단"은 proxy(미들웨어)+requireRole 담당.
// 서버에서는 getSession()이 아니라 getUser()를 쓴다 — 쿠키를 그대로 믿지 않고 Auth 서버에 재검증해 신뢰 가능.
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { USER_ROLE, ROLE_LABEL, LISTING_STATUS, type UserRole } from '@/lib/constants';
import { fetchPopularAndRecentListings, type PopularRecentSection } from '@/lib/listings';
import { fetchWishedListingIds } from '@/lib/wishlist';
import AppHeader from '@/components/layout/AppHeader';
import HeroSearch from '@/components/landing/HeroSearch';
import CategoryChips from '@/components/landing/CategoryChips';
import PopularRecentGrid from '@/components/landing/PopularRecentGrid';

// 홈도 매 요청 최신 DB를 반영해야 한다(그리드에 sold가 잔존하지 않게). 정적화 방지(search·상세와 동일).
export const dynamic = 'force-dynamic';

// 인기·최신 두 단의 id를 합쳐 찜 오버레이를 한 번만 조회하기 위한 헬퍼(Story 11.4 Always 규칙).
// 조회 실패한 단은 error만 있고 listings가 없으므로 빈 배열로 취급한다.
function sectionListingIds(section: PopularRecentSection): string[] {
  return 'listings' in section ? section.listings.map((l) => l.id) : [];
}

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 로그인 상태면 본인 역할 조회(profiles_select_self RLS가 본인 행 읽기를 허용).
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      // 역할별 랜딩: 관리자는 로그인 후 곧바로 관리 페이지로 보낸다(편의 라우팅).
      //   보안 차단이 아니라 "도착지 유도"다 — /admin 자체의 접근 통제는 proxy + requireRole이 담당.
      if (profile.role === USER_ROLE.ADMIN) {
        redirect('/admin');
      }
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 로그인 상태: ① 본인정보 + ② 인기/최신 매물 그리드 + ③ AI 전역 진입.
  if (user) {
    // ② 인기(view_count desc)·최신(created_at desc) 2단 발췌 그리드 (Story 11.4, FR34).
    //   기존 "최근 매물" 단일 미리보기는 이 함수의 "최신" 단으로 흡수돼 대체됐다(신규 작성이 아니라 이관).
    const { popular, recent } = await fetchPopularAndRecentListings(supabase, user);

    // 찜 오버레이(Story 10.5) — 두 단의 id를 합쳐 한 번만 조회한다(Always 규칙, 중복 조회 방지).
    const wishedIds = await fetchWishedListingIds(supabase, user.id, [
      ...sectionListingIds(popular),
      ...sectionListingIds(recent),
    ]);

    const isSeller = roleLabel === ROLE_LABEL[USER_ROLE.SELLER];

    // ① 카드 표시 이름 = 이메일의 '@' 앞부분(별도 이름 컬럼 없이 식별용). 본인 이메일은 항상 읽을 수 있어 DB 조회 불필요.
    const displayName = user.email ? user.email.split('@')[0] : '사용자';

    // ③ "구매문의 n건"(공통) — 본인이 참여한 문의 채팅방 수. chat_rooms 참여자 RLS가
    //   자동으로 본인 방만(판매자=받은 문의, 구매자=보낸 문의) 세므로 별도 필터가 필요 없다. head:true로 개수만.
    const { count: roomCount } = await supabase
      .from('chat_rooms')
      .select('id', { count: 'exact', head: true });
    const inquiryCount = roomCount ?? 0;

    // ③ "판매중 n건"(판매자만) — 본인 매물 중 판매중 개수. 본인 행이라 RLS로 바로 읽힌다.
    let onSaleCount = 0;
    if (isSeller) {
      const { count } = await supabase
        .from('listings')
        .select('id', { count: 'exact', head: true })
        .eq('seller_id', user.id)
        .eq('status', LISTING_STATUS.ON_SALE);
      onSaleCount = count ?? 0;
    }

    return (
      <>
        <AppHeader roleLabel={roleLabel} email={user.email} currentPath="/" />
        {/* 히어로(AI 자연어 검색 진입점) + 차종 빠른 진입 칩 (Story 11.3, FR33/FR35) — 헤더 바로
            아래, 기존 본인정보/미리보기 섹션보다 먼저 배치해 "이 서비스가 뭘 하는지" 첫 화면에서
            바로 체감하게 한다. 로그인 사용자도 동일 히어로를 보되 제출 시 게이트 없이 /ai로 직행. */}
        <HeroSearch authed />
        <CategoryChips />
        {/* 폭을 max-w-2xl(672px)에서 넓힌다 — 그래야 그리드 카드 4장이 넓은 화면에서 실제로 4열이 된다
            (D5 브레이크포인트는 뷰포트 기준이라 본문이 좁으면 열만 늘고 칸이 찌그러진다, AC6). */}
        <main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
          {/* ① 본인 정보 영역 — 역할 배지 + 표시 이름(이메일 @앞부분; 이메일 전체는 상단바에 있음).
              그 아래에 자주 쓰는 동선을 엔카 마이페이지 스타일의 "텍스트 메뉴"로 둔다(버튼처럼 보이지 않게, hover 시 강조).
              · 문의 채팅: 구매자·판매자 공통.  · 판매중 n건: 판매자만(매물 등록·관리 /sell로 진입, 건수는 가변). */}
          <section className="flex flex-col gap-3 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex items-center gap-2">
              {roleLabel && (
                <span className="rounded bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white dark:bg-white dark:text-zinc-900">
                  {roleLabel}
                </span>
              )}
              <span className="text-sm font-medium">{displayName}</span>
            </div>
            <nav className="flex items-center gap-5 border-t border-zinc-200 pt-2 text-sm dark:border-zinc-800">
              {/* 구매문의(공통) — 본인 참여 문의 채팅방 수. hover 시 빨강 강조. 버튼 테두리 없음(텍스트 메뉴). */}
              <Link href="/chat" className="text-zinc-600 transition-colors hover:text-red-600 dark:text-zinc-300">
                구매문의 <span className="font-semibold text-zinc-900 dark:text-zinc-100">{inquiryCount}</span>건
              </Link>
              {/* 판매중 n건(판매자만) — 매물 등록·관리(/sell)로 진입. 건수는 본인 판매중 매물 수에 따라 가변. */}
              {isSeller && (
                <Link href="/sell" className="text-zinc-600 transition-colors hover:text-red-600 dark:text-zinc-300">
                  판매중 <span className="font-semibold text-zinc-900 dark:text-zinc-100">{onSaleCount}</span>건
                </Link>
              )}
            </nav>
          </section>

          {/* ② 인기/최신 매물 그리드 — 발췌 4건씩 + 전체 보기(/search, 무필터). 읽기 전용
              (필터·상태는 /search가 소유, 랜딩은 URL 쿼리를 소유하지 않는다). */}
          <PopularRecentGrid popular={popular} recent={recent} wishedIds={wishedIds} authed />
        </main>

        {/* ③ AI 검색 전역 진입 — 화면 우하단에 떠 있는 버튼(어느 화면에서든 닿는 전역 동작, R3).
            서버 컴포넌트 그대로 — 단순 링크라 클라이언트 상태가 필요 없다. fixed로 본문 위에 띄운다. */}
        <Link
          href="/ai"
          aria-label="AI 검색 열기"
          className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full bg-zinc-900 px-5 py-3 text-sm font-medium text-white shadow-lg transition-colors hover:bg-zinc-700 dark:bg-white dark:text-zinc-900 dark:hover:bg-zinc-200"
        >
          <span aria-hidden>✨</span> AI 검색
        </Link>
      </>
    );
  }

  // 비로그인 상태 (Story 11.3, #152 해소): 이제 /search와 동일한 상단 내비를 보여준다 —
  //   이전엔 이 분기가 상단바 없이 "로그인/회원가입" 카드만 중앙에 띄웠는데(로그인·내 차 등록
  //   진입로가 여기 하나뿐이었음), SiteNav가 같은 링크(로그인·내 차 등록)를 헤더 우측에 이미
  //   제공하므로 중복 CTA 카드는 걷어내고 그 자리에 히어로+차종칩을 놓는다. 히어로 입력창은
  //   로그인 여부와 무관하게 항상 활성 — 제출 시점에만 로그인 게이트로 분기한다(Always 규칙).
  //
  // 인기/최신 매물 그리드(Story 11.4, FR34) — 로그인 분기와 동일한 함수·컴포넌트를 재사용한다.
  //   비로그인은 신뢰속성 3필드가 select에서 아예 빠지고(anon 화이트리스트, #134 참조 — 이 스토리가
  //   마이그레이션 0021로 view_count 읽기 권한만 추가로 열었다), 찜 오버레이는 로그인 시에만 조회하므로
  //   여기선 항상 빈 Set이다.
  const { popular, recent } = await fetchPopularAndRecentListings(supabase, null);

  return (
    <>
      <AppHeader roleLabel={null} email={null} currentPath="/" />
      <HeroSearch authed={false} />
      <CategoryChips />
      {/* /search와 동일 폭(max-w-6xl p-6) — 그래야 4열 그리드가 실제로 4칸이 된다(D5, Story 9.4 AC6). */}
      <main className="mx-auto flex max-w-6xl flex-col gap-6 p-6">
        <PopularRecentGrid popular={popular} recent={recent} wishedIds={new Set()} authed={false} />
      </main>
    </>
  );
}
