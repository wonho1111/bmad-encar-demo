// 홈 / 로그인 후 첫 화면 (FR2) — 서버 컴포넌트.
//
// 구성:
//   ① 인기/최신 매물 그리드(Story 11.4) — 인기(view_count desc)·최신(created_at desc) 각 4건을
//      홈에 바로 노출 + '전체 보기'→/search. 로그인·비로그인 양쪽 분기에 동일하게 렌더한다.
//      ⚠️ 홈은 필터·URL 상태를 소유하지 않는다(읽기 전용 발췌). 본격 탐색·필터는 /search가 소유.
//         → 검색 로직 이원화·회귀 방지. ListingCard를 그대로 재사용해 표시 로직도 단일 출처.
//   ② AI 검색 진입 — **상단바 'AI로 찾기' 링크**가 담당한다(SiteNav, 모든 소비자 화면 상시).
//
// ⚠️ **떠 있는 'AI 검색' 버튼은 2026-08-07에 제거했다.** 2026-06-25에 nav-ia-rules R3
//   (*"web에서는 가벼운 플로팅/상시 진입으로"* — 플로팅 **또는** 상시 진입)를 근거로 넣었는데,
//   2026-07-12 UX 확정(D12)이 그 뒤에 **웹엔 FAB이 없다는 것을 전제로** 앱의 "FAB 없음"까지
//   결정했다. 즉 확정 결정이 사실과 어긋난 상태로 한 달 넘게 있었다. 목업 6장(landing-1·
//   consistency-1·detail-1·forms-2·ai-flow-1·card-final-1)에도 `position:fixed` 요소가 0개다.
//   R3는 "플로팅/상시 진입" 둘 중 하나면 충족이고, 상단바 링크가 이미 전역 상시라 **R3도 그대로
//   지켜진다**(진입로가 줄지 않는다). 홈은 히어로가 AI 진입의 주인공이라 실질 손실도 없다.
//   ⚠️ 되살리려면 D12 문장부터 고쳐야 한다 — 코드만 바꾸면 같은 어긋남이 반복된다.
//
// ⚠️ **"본인 정보 영역"(역할 배지·표시 이름·구매문의 n건·판매중 n건)은 2026-07-29에 제거했다.**
//   2026-06-24 개편(nav-ia-rules.md)이 "구매자 홈=본인정보"로 넣었던 섹션인데, 2026-07-12 UX
//   결정이 그걸 **대체**했다: *"로그인 후 홈 = 공개 랜딩과 동일(A안) — FR58 단일 공개 홈 준수.
//   로그인 체감은 상단 찜·채팅 아이콘으로 충분. (예전 nav-ia-rules '구매자 홈=본인정보'는 FR58이
//   대체.)"* (`ux-designs/…/.decision-log.md`). Story 11.3이 히어로·차종칩을 **추가만** 하고 이
//   섹션을 안 지워, 대체됐어야 할 구버전 UI가 새 랜딩 위에 그대로 얹혀 있었다(사용자 지적).
//   제거로 로그인 홈의 DB 왕복도 2회(문의 수·판매중 수) 줄었다.
//
// 관리자는 여기서 /admin으로 랜딩 유도(아래 분기). 보호 경로 "차단"은 proxy(미들웨어)+requireRole 담당.
// 서버에서는 getSession()이 아니라 getUser()를 쓴다 — 쿠키를 그대로 믿지 않고 Auth 서버에 재검증해 신뢰 가능.
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { USER_ROLE, ROLE_LABEL, PROFILE_STATUS, type UserRole } from '@/lib/constants';
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
      .select('role, status')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      // 역할별 랜딩: 관리자는 로그인 후 곧바로 관리 페이지로 보낸다(편의 라우팅).
      //   보안 차단이 아니라 "도착지 유도"다 — /admin 자체의 접근 통제는 proxy + requireRole이 담당.
      // status==='active'일 때만 보낸다(spec-17-3, guard.ts의 requireRole과 락스텝) — 정지된
      //   관리자는 requireRole이 /admin에서 여기(/)로 돌려보내는데, 이 분기가 role만 보면
      //   무조건 다시 /admin으로 되돌려 "/admin → / → /admin → …" 무한 리다이렉트가 된다.
      //   정지된 관리자는 홈에 그대로 머문다(새 화면을 만들지 않는 선택지 ⓑ).
      // ⚠️ 여기도 guard.ts의 requireRole과 같은 이유로 `web/src/lib/auth/status.ts`의
      //   getOwnStatus를 쓰지 않는다 — role·status를 이미 한 번의 select로 묶어 읽고 있고,
      //   그 헬퍼를 또 부르면 auth.getUser() 왕복이 한 번 더 늘 뿐이다. getOwnStatus는 "쓰기
      //   거부 뒤 사유 안내"용 단일 경로다(ListingActions.tsx·SellForm.tsx).
      if (profile.role === USER_ROLE.ADMIN && profile.status === PROFILE_STATUS.ACTIVE) {
        redirect('/admin');
      }
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 로그인 상태: ① 인기/최신 매물 그리드 + ② AI 전역 진입(본인정보 섹션은 위 주석대로 제거됨).
  if (user) {
    // ① 인기(view_count desc)·최신(created_at desc) 2단 발췌 그리드 (Story 11.4, FR34).
    //   기존 "최근 매물" 단일 미리보기는 이 함수의 "최신" 단으로 흡수돼 대체됐다(신규 작성이 아니라 이관).
    const { popular, recent } = await fetchPopularAndRecentListings(supabase);

    // 찜 오버레이(Story 10.5) — 두 단의 id를 합쳐 한 번만 조회한다(Always 규칙, 중복 조회 방지).
    const wishedIds = await fetchWishedListingIds(supabase, user.id, [
      ...sectionListingIds(popular),
      ...sectionListingIds(recent),
    ]);

    return (
      <>
        <AppHeader roleLabel={roleLabel} email={user.email} currentPath="/" />
        {/* 히어로(AI 자연어 검색 진입점) + 차종 빠른 진입 칩 (Story 11.3, FR33/FR35) — 헤더 바로
            아래에 놓아 "이 서비스가 뭘 하는지"를 첫 화면에서 바로 체감하게 한다.
            로그인 사용자도 동일 히어로를 보되 제출 시 게이트 없이 /ai로 직행. */}
        <HeroSearch authed />
        <CategoryChips />
        {/* 폭을 max-w-2xl(672px)에서 넓힌다 — 그래야 그리드 카드 4장이 넓은 화면에서 실제로 4열이 된다
            (D5 브레이크포인트는 뷰포트 기준이라 본문이 좁으면 열만 늘고 칸이 찌그러진다, AC6). */}
        <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
          {/* 인기/최신 매물 그리드 — 발췌 4건씩 + 전체 보기(/search, 무필터). 읽기 전용
              (필터·상태는 /search가 소유, 랜딩은 URL 쿼리를 소유하지 않는다). */}
          <PopularRecentGrid popular={popular} recent={recent} wishedIds={wishedIds} authed />
        </main>
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
  const { popular, recent } = await fetchPopularAndRecentListings(supabase);

  return (
    <>
      <AppHeader roleLabel={null} email={null} currentPath="/" />
      <HeroSearch authed={false} />
      <CategoryChips />
      {/* /search와 동일 폭(max-w-6xl p-6) — 그래야 4열 그리드가 실제로 4칸이 된다(D5, Story 9.4 AC6). */}
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6">
        <PopularRecentGrid popular={popular} recent={recent} wishedIds={new Set()} authed={false} />
      </main>
    </>
  );
}
