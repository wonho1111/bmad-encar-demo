// 홈 / 로그인 후 첫 화면 (FR2) — 서버 컴포넌트.
// 로그인 상태면 공용 상단바(역할·이메일·로그아웃)를 띄우고 중앙은 콘텐츠 자리로 비워둔다.
//   (구매자=매물 탐색, 판매자=매물 등록 UI가 Epic 2/3에서 이 중앙에 들어온다.)
// 비로그인 상태면 로그인/회원가입 링크를 중앙에 보여준다.
// 서버에서는 getSession()이 아니라 getUser()를 쓴다 — 쿠키를 그대로 믿지 않고 Auth 서버에 재검증해 신뢰 가능.
// 관리자는 여기서 /admin으로 랜딩 유도(아래 분기). 보호 경로 "차단"은 proxy(미들웨어)+requireRole 담당.
import Link from 'next/link';
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { USER_ROLE, ROLE_LABEL, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';
import { buttonClasses } from '@/components/ui/Button';

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
      //   관리자의 메인(/) 접근은 막지 않는다(직접 방문 시에도 /admin으로 안내될 뿐). 향후 seller 전용
      //   랜딩이 생기면 여기 한 곳에만 분기를 추가하면 된다(역할별 랜딩의 단일 결정 지점).
      if (profile.role === USER_ROLE.ADMIN) {
        redirect('/admin');
      }
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 로그인 상태: 상단바(역할·이메일·로그아웃) + 중앙은 향후 콘텐츠 자리.
  if (user) {
    return (
      <>
        <AppHeader roleLabel={roleLabel} email={user.email} />
        <main className="mx-auto flex max-w-md flex-col gap-6 p-6">
          <h1 className="text-2xl font-semibold">중고차 직거래</h1>
          {/* 매물 탐색(Story 3-1) — 구매자가 핵심 사용자지만, 판매자도 판매중(on_sale) 매물을 둘러볼 수 있다(RLS상 공개). */}
          <Link href="/search" className={buttonClasses({ variant: 'primary', className: 'w-fit' })}>
            매물 탐색
          </Link>
          {/* 판매자에게는 매물 등록 진입점을 함께 제공한다(Story 2-2). */}
          {roleLabel === ROLE_LABEL[USER_ROLE.SELLER] && (
            <Link href="/sell" className={buttonClasses({ variant: 'secondary', className: 'w-fit' })}>
              매물 등록·관리
            </Link>
          )}
        </main>
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
