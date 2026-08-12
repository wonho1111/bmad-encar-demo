// 공용 상단바 — variant로 두 갈래를 가른다(Story 11.2, spec-11-2-상단-내비-재구성.md).
//   · 'admin'(기본값 아님, (admin)/layout.tsx가 명시 전달) — 기존 최소 헤더(역할·이메일·로그아웃)
//     그대로. 관리자는 운영 허브 전용 역할이라 소비자 내비(내 차 사기 등)가 의미 없다(nav-ia-rules.md §1).
//   · 'consumer'(기본값, 나머지 9개 호출부 — account/page.tsx 포함) — 로고(홈 링크) + SiteNav(데스크톱 3링크·모바일 햄버거·
//     로그인상태별 찜/채팅/프로필▾ 또는 로그인).
// 서버 컴포넌트 — 로그인 상태 판별·상호작용은 각 갈래(LogoutButton·SiteNav)의
// 클라이언트 컴포넌트에 위임한다.
// consumer 분기·로그인 상태일 때만 안읽음 총합(FR57, Story 12.5)을 계산하려고 비동기 컴포넌트로
// 전환했다(admin 분기·비로그인은 호출하지 않는다). 대장 #183(getUser 증폭) 층에 RPC 호출이
// 하나 더 얹히는 것은 알려진 tech-debt로 등재해 둔다.
import Link from 'next/link';
import LogoutButton from '@/components/auth/LogoutButton';
import Logo from '@/components/ui/Logo';
import { createClient } from '@/lib/supabase/server';
import SiteNav from './SiteNav';

export default async function AppHeader({
  roleLabel,
  email,
  currentPath,
  variant = 'consumer',
}: {
  roleLabel?: string | null;
  email?: string | null;
  // 헤더는 서버 컴포넌트라 현재 경로를 스스로 알 수 없어 호출부가 넘긴다 —
  //   로그인 링크에 redirectedFrom으로 실어 로그인 후 원위치로 복귀시킨다(conventions.md §8).
  currentPath?: string;
  variant?: 'consumer' | 'admin';
}) {
  if (variant === 'admin') {
    // 기존 admin 렌더 경로 그대로 보존(회귀 방지) — 9개 호출부 중 (admin)/layout.tsx 1곳만 여기로 온다.
    // 단, 이전 헤더가 email 존재 시 보여주던 찜(/wishlist) 링크는 여기 없다 — 소실이 아니라 의도:
    // spec-11-2가 admin 헤더를 "역할라벨·이메일·로그아웃"으로 한정했다(소비자 내비는 admin 역할에
    // 의미 없음, nav-ia-rules.md §1).
    // 3차 코드리뷰 지적 P9 — 위 "그대로 보존"은 정확하지 않았다. 두 가지가 실제로 달라졌다:
    //   · 예전 헤더는 email이 없으면 `/login?redirectedFrom=…` 링크를 보여줬는데, 여기는
    //     <LogoutButton />을 무조건 그린다 — email 부재 분기가 없다. 이건 안전하다:
    //     (admin)/layout.tsx가 requireAdmin()으로 먼저 막아 이 컴포넌트엔 세션 있는 요청만
    //     들어오므로, 로그인 링크 분기는 애초에 도달 불가능한 코드였을 것이다.
    //   · 그래서 currentPath는 이 분기에서 쓰지 않는다(로그인 링크의 redirectedFrom이 없으니
    //     쓸 자리가 없다) — prop으로는 받되 이 분기 안에서는 미사용이다.
    return (
      <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
        <div className="flex items-baseline gap-3 text-sm">
          <Link href="/" className="font-semibold hover:underline">
            중고차 직거래
          </Link>
          {roleLabel && <span className="font-medium text-zinc-500">{roleLabel}</span>}
          {email && <span className="text-zinc-500">{email}</span>}
        </div>
        <LogoutButton />
      </header>
    );
  }

  // 안읽음 총합(FR57, Story 12.5) — consumer 분기·로그인 상태일 때만 계산한다(admin 분기·비로그인은
  // 이 지점에 도달하지 않거나 email이 없어 호출을 건너뛴다). RPC 실패는 배지 없음으로 폴백한다 —
  // 배지는 부가 정보라 헤더 렌더 자체를 막지 않는다(콘솔 로그만).
  let unreadCount: number | undefined;
  if (email) {
    const supabase = await createClient();
    const { data, error } = await supabase.rpc('chat_unread_count');
    if (error) {
      console.error('[AppHeader] 안읽음 카운트 조회 실패:', error);
    } else if (typeof data === 'number') {
      unreadCount = data;
    }
  }

  return (
    // relative — 모바일 햄버거 패널(SiteNav.tsx, absolute inset-x-0 top-full)의 포지션 기준.
    // SiteNav 루트 div가 아니라 여기 둬야 패널이 로고를 지나 header 왼쪽 끝(0)부터 시작한다
    // (코드리뷰 지적, 실측 근거는 SiteNav.tsx 쪽 주석 참조). 프로필 드롭다운은 자기 컨테이너에
    // 별도 relative가 있어 이 변경과 무관하다.
    <header className="relative border-b border-border-hairline bg-surface-raised">
      <div className="mx-auto flex max-w-6xl items-center gap-4 px-6 py-3">
        {/* Logo(/ui/Logo.tsx)를 홈 링크로 배선 — 지금까지 어디서도 안 쓰이던 컴포넌트(기술부채 #125)를
            이 자리로 연결한다. 어느 화면에서든 클릭하면 홈으로 돌아가는 공통 진입점(기존 동작 유지). */}
        <Link href="/" aria-label="홈으로 이동" className="shrink-0">
          <Logo size="sm" />
        </Link>
        <SiteNav email={email} currentPath={currentPath} unreadCount={unreadCount} />
      </div>
    </header>
  );
}
