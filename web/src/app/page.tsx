// 홈 / 로그인 후 첫 화면 (FR2) — 서버 컴포넌트.
//
// 메인화면 개편(2026-06-24, party-mode 결정 / nav-ia-rules.md):
//   로그인 사용자(구매자·판매자)의 홈을 "버튼 허브"에서 "1순위 과업으로 바로 착지"로 바꾼다.
//   ① 본인 정보 영역(역할·이메일) — "내가 누구로 로그인했나"를 한눈에(역할 기반 서비스의 핵심).
//   ② 매물 탐색 미리보기 — 최근 매물 몇 건을 홈에 바로 노출 + '더보기'→/search.
//      ⚠️ 홈은 필터·URL 상태를 소유하지 않는다(읽기 전용 미리보기). 본격 탐색·필터는 /search가 소유.
//         → 검색 로직 이원화·회귀 방지. ListingCard를 그대로 재사용해 표시 로직도 단일 출처.
//   ③ AI 검색 — 페이지 한구석 버튼이 아니라 "어디서든 닿는 전역 진입"으로 떠 있는 버튼(R3).
//
// 관리자는 여기서 /admin으로 랜딩 유도(아래 분기). 보호 경로 "차단"은 proxy(미들웨어)+requireRole 담당.
// 서버에서는 getSession()이 아니라 getUser()를 쓴다 — 쿠키를 그대로 믿지 않고 Auth 서버에 재검증해 신뢰 가능.
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { USER_ROLE, ROLE_LABEL, type UserRole } from '@/lib/constants';
import { buyerListingsQuery } from '@/lib/listings';
import AppHeader from '@/components/layout/AppHeader';
import ListingCard, { type ListingCardData } from '@/components/listings/ListingCard';
import { buttonClasses } from '@/components/ui/Button';

// 홈도 매 요청 최신 DB를 반영해야 한다(미리보기에 sold가 잔존하지 않게). 정적화 방지(search·상세와 동일).
export const dynamic = 'force-dynamic';

// ② 미리보기에 보여줄 최근 매물 개수. "미리보기"라 적게(전체는 /search 더보기로).
const PREVIEW_COUNT = 4;

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

  // 로그인 상태: ① 본인정보 + ② 매물 미리보기 + ③ AI 전역 진입.
  if (user) {
    // ② 미리보기 데이터 — 구매자 관점(판매중만, FR11 단일 출처) 최근 N건. 필터 없음(미리보기).
    //   search 페이지와 같은 요약 컬럼·정렬을 쓰되 limit만 건다(상태·표시 규칙은 공유).
    const { data: previewListings, error: previewError } = await buyerListingsQuery(
      supabase,
      'id, manufacturer, model, year, price, mileage, region',
    )
      .order('created_at', { ascending: false })
      .order('id', { ascending: false })
      .limit(PREVIEW_COUNT)
      .returns<ListingCardData[]>();

    if (previewError) {
      // 미리보기 실패는 홈 전체를 막지 않는다 — 로그만 남기고 아래에서 안내 문구로 대체(비차단).
      console.error('[home] 매물 미리보기 조회 실패:', previewError);
    }

    const isSeller = roleLabel === ROLE_LABEL[USER_ROLE.SELLER];

    return (
      <>
        <AppHeader roleLabel={roleLabel} email={user.email} />
        <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
          {/* ① 본인 정보 영역 — 역할 배지 + 이메일. (profiles에 이름 컬럼이 없어 이메일을 식별자로 쓴다) */}
          <section className="flex flex-col gap-1 rounded-lg border border-zinc-200 bg-zinc-50 px-4 py-3 dark:border-zinc-800 dark:bg-zinc-900">
            <div className="flex items-center gap-2">
              {roleLabel && (
                <span className="rounded bg-zinc-900 px-2 py-0.5 text-xs font-medium text-white dark:bg-white dark:text-zinc-900">
                  {roleLabel}
                </span>
              )}
              <span className="text-sm font-medium">{user.email}</span>
            </div>
            <p className="text-xs text-zinc-500">
              {isSeller
                ? '내 매물을 관리하거나, 다른 매물을 둘러볼 수 있어요.'
                : '원하는 차를 탐색하고 판매자에게 바로 문의해보세요.'}
            </p>
          </section>

          {/* ② 매물 탐색 미리보기 — 최근 매물 N건 + 더보기. 읽기 전용(필터·상태는 /search가 소유). */}
          <section className="flex flex-col gap-3">
            <div className="flex items-baseline justify-between">
              <h2 className="text-lg font-semibold">최근 매물</h2>
              <Link href="/search" className="text-sm text-zinc-500 hover:underline">
                더보기 →
              </Link>
            </div>
            {previewError ? (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                매물을 불러오지 못했습니다.{' '}
                <Link href="/search" className="underline">
                  매물 탐색으로 이동
                </Link>
              </p>
            ) : !previewListings || previewListings.length === 0 ? (
              <p className="text-sm text-zinc-500">아직 등록된 매물이 없습니다.</p>
            ) : (
              <ul className="flex flex-col gap-2">
                {previewListings.map((l) => (
                  <li key={l.id}>
                    <ListingCard listing={l} />
                  </li>
                ))}
              </ul>
            )}
          </section>

          {/* 보조 동선 — 문의 채팅(구매자·판매자 공통) + 판매자에게는 매물 등록·관리. */}
          <section className="flex flex-wrap gap-3">
            <Link href="/chat" className={buttonClasses({ variant: 'secondary', className: 'w-fit' })}>
              문의 채팅
            </Link>
            {isSeller && (
              <Link href="/sell" className={buttonClasses({ variant: 'secondary', className: 'w-fit' })}>
                매물 등록·관리
              </Link>
            )}
          </section>
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

  // 비로그인 상태: 로그인/회원가입 링크를 중앙에 (상단바·로그아웃 없음).
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">중고차 직거래</h1>
      <div className="flex flex-col gap-3">
        <p className="text-sm text-zinc-500">로그인하고 서비스를 이용해보세요.</p>
        <div className="flex gap-3">
          <Link href="/login" className={buttonClasses({ variant: 'primary' })}>
            로그인
          </Link>
          <Link href="/signup" className={buttonClasses({ variant: 'secondary' })}>
            회원가입
          </Link>
        </div>
      </div>
    </main>
  );
}
