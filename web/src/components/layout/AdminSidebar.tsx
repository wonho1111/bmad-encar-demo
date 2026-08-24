'use client';

// 관리자 내비 셸(spec-15-2) — SiteNav.tsx의 FocusTrap-dialog + matchMedia 자동닫힘 패턴을 그대로
// 이식한다(760px 브레이크포인트, outside-pointerdown-close). 데스크톱(≥760px)은 고정 사이드바
// (240px = w-60, sticky) + 5개 nav item, 모바일(<760px)은 햄버거 버튼 + FocusTrap 슬라이드인 패널이다.
//
// AppHeader.tsx는 서버 컴포넌트인데 사이드바 열림/닫힘 상태는 클라이언트 상태가 필요하다 — 그래서
// 이 컴포넌트를 AppHeader와 완전히 독립된 클라이언트 컴포넌트로 두어 AppHeader 자체는 건드리지
// 않는다(spec-15-2 Design Notes — 15.1이 같은 이유로 AppHeader를 범위 밖에 둔 것과 동일 판단이며,
// DW-695(AppHeader 잔존 zinc)를 이번에 우연히 건드리지 않기 위한 목적도 겸한다).
//
// 사이드바 붕괴 breakpoint(760px)는 D5 그리드 브레이크포인트(1100/640, project-context 규칙13)와
// 다른 축이다 — "내비 셸 표시 방식" vs "그리드 열수"라 관리자 화면에 그리드가 없다는 사실과 무관하게
// 섞지 않는다(spec-15-2 Always).
//
// 각 상세 화면의 뒤로가기 버튼은 그대로 둔다 — 이 사이드바는 추가되는 내비이지 기존 페이지
// 내비를 대체하지 않는다(spec-15-2 Always). 단 "대시보드 허브의 4개 링크 버튼"은 예외가 됐다 —
// 그 허브 화면 자체가 2026-08-13(#9)에 없어졌다(app/(admin)/admin/page.tsx 주석 참조).
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import FocusTrap from '@/components/ui/FocusTrap';

// ✎ 2026-08-13 사용자 결정 #9 — 맨 앞의 "대시보드"(/admin)를 뺐다. 그 화면은 여기 있는 4개
// 목적지로 가는 링크만 있는 허브였는데, 이 사이드바가 생기면서 하는 일이 없어졌다.
// `/admin`은 이제 /admin/members로 전달만 한다(app/(admin)/admin/page.tsx).
const ADMIN_NAV_LINKS: { label: string; href: string }[] = [
  { label: '회원관리', href: '/admin/members' },
  { label: '매물 관리', href: '/admin/listings' },
  { label: '거래내역', href: '/admin/transactions' },
  { label: '채팅관리', href: '/admin/chats' },
];

// 햄버거 히트영역 44×44px(h-11 w-11) — SiteNav.tsx의 ICON_BUTTON_CLASS와 동일 기준(접근성 바닥).
const HAMBURGER_CLASS =
  'flex h-11 w-11 items-center justify-center rounded-badge text-xl text-ink-secondary hover:bg-surface-base hover:text-ink-primary';

const LINK_CLASS =
  'rounded-badge px-3 py-2 text-sm font-medium text-ink-secondary hover:bg-surface-base hover:text-ink-primary';
// active 표시 — brand-petrol 틴트 배경 + petrol 글자(공용 Badge tone="active"와 같은 축의 신호,
// 색만이 아니라 배경 자체가 달라지므로 비색 신호도 함께 있다: aria-current="page"로 보강).
const ACTIVE_LINK_CLASS = 'rounded-badge bg-brand-petrol/10 px-3 py-2 text-sm font-semibold text-brand-petrol';

// 현재 경로가 이 nav item에 속하는지 — 목록뿐 아니라 그 상세(/admin/listings/[id],
// /admin/chats/[roomId])도 같은 항목을 active로 표시해야 하므로 하위 경로까지 startsWith로 포함한다.
// (예전엔 '/admin' 대시보드 항목만 정확 일치로 빼는 예외가 있었는데, 그 항목이 없어져 예외도 함께
//  사라졌다 — 남은 4개는 서로의 하위 경로가 아니라 startsWith가 겹칠 일이 없다.)
function isActiveHref(pathname: string | null, href: string): boolean {
  if (!pathname) return false;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AdminSidebar() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  // 트리거+패널을 함께 감싸는 컨테이너 — outside-click 판정("이 안을 클릭했나")에 쓴다(SiteNav.tsx와 동일).
  const menuContainerRef = useRef<HTMLDivElement>(null);

  // outside-click 닫기(SiteNav.tsx 코드리뷰 지적과 동일 이유) — FocusTrap은 포커스 이탈만 되돌릴 뿐
  // 마우스 바깥 클릭은 안 막으므로 여기서 직접 감지한다. pointerdown을 쓰는 이유도 SiteNav.tsx와
  // 동일: 이 패널은 <760px 모바일 전용 UI라 터치·펜까지 포괄해야 하고, 트리거 재클릭 토글(아래
  // onClick)보다 먼저 발화해야 두 핸들러가 서로 상태를 되돌리지 않는다.
  useEffect(() => {
    if (!menuOpen) return;
    function handlePointerDown(event: PointerEvent) {
      if (menuContainerRef.current && !menuContainerRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [menuOpen]);

  // 경로가 바뀌면 패널을 닫는다(코드리뷰 patch). 패널 안 링크는 각자 onClick으로 닫지만, 그건
  // "링크를 눌러서 이동한 경우"만 덮는다 — 메뉴를 열어 둔 채 브라우저 뒤로가기를 누르면 pathname은
  // 바뀌고 menuOpen은 true로 남아, 새 화면 위에 이전 화면에서 연 메뉴가 그대로 덮인다. 원본
  // SiteNav.tsx엔 이 구멍이 없다 — 거기는 usePathname을 아예 안 써서 경로 변화와 무관하기 때문이다.
  //
  // useEffect가 아니라 **렌더 중 조정**인 이유: 이 프로젝트의 lint(react-hooks/set-state-in-effect)가
  // 이펙트 안 setState를 막는다. React 공식이 권하는 "값이 바뀌면 렌더 중에 상태를 조정한다" 패턴을
  // 쓴다 — 추가 렌더 없이 같은 커밋에서 정리되므로, 이펙트로 닫을 때처럼 열린 패널이 한 프레임
  // 깜빡이지도 않는다.
  const [prevPathname, setPrevPathname] = useState(pathname);
  if (pathname !== prevPathname) {
    setPrevPathname(pathname);
    setMenuOpen(false);
  }

  // 760px 이상으로 리사이즈되면 패널을 강제로 닫는다(SiteNav.tsx와 동일 — 모바일 전용 상태가
  // 뷰포트를 벗어난 채로 남아 있다가 다시 좁아지면 클릭 없이 되살아나는 것을 막는다).
  useEffect(() => {
    const mql = window.matchMedia('(min-width: 760px)');
    function handleChange(event: MediaQueryListEvent) {
      if (event.matches) setMenuOpen(false);
    }
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, []);

  return (
    <>
      {/* 데스크톱(≥760px) 고정 사이드바 — 240px(w-60), sticky로 스크롤에 따라간다. */}
      <nav
        aria-label="관리자 메뉴"
        className="sticky top-0 hidden h-fit w-60 shrink-0 flex-col gap-1 border-r border-border-hairline bg-surface-raised p-4 min-[760px]:flex"
      >
        {ADMIN_NAV_LINKS.map((link) => {
          const active = isActiveHref(pathname, link.href);
          return (
            <Link
              key={link.href}
              href={link.href}
              aria-current={active ? 'page' : undefined}
              className={active ? ACTIVE_LINK_CLASS : LINK_CLASS}
            >
              {link.label}
            </Link>
          );
        })}
      </nav>

      {/* 모바일(<760px) 햄버거 + FocusTrap 슬라이드인 패널 — SiteNav.tsx의 햄버거 패널과 동일 메커니즘
          (Tab 순환·Esc 닫힘·outside-pointerdown-close·리사이즈 자동닫힘). */}
      <div ref={menuContainerRef} className="relative border-b border-border-hairline min-[760px]:hidden">
        <button
          type="button"
          aria-haspopup="dialog"
          aria-expanded={menuOpen}
          aria-label={menuOpen ? '관리자 메뉴 닫기' : '관리자 메뉴 열기'}
          onClick={() => setMenuOpen((v) => !v)}
          className={`m-1 ${HAMBURGER_CLASS}`}
        >
          <span aria-hidden>☰</span>
        </button>
        {menuOpen && (
          <FocusTrap
            open
            onClose={() => setMenuOpen(false)}
            role="dialog"
            aria-modal="true"
            aria-label="관리자 메뉴"
            className="absolute inset-x-0 top-full z-30 flex flex-col gap-1 border-b border-border-hairline bg-surface-raised p-3 shadow-card dark:shadow-none"
          >
            {ADMIN_NAV_LINKS.map((link) => {
              const active = isActiveHref(pathname, link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  aria-current={active ? 'page' : undefined}
                  className={active ? ACTIVE_LINK_CLASS : LINK_CLASS}
                >
                  {link.label}
                </Link>
              );
            })}
          </FocusTrap>
        )}
      </div>
    </>
  );
}
