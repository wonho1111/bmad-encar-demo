'use client';

// 소비자용 상단 내비 본체(spec-11-2) — AppHeader(서버 컴포넌트)가 로고 뒤에 배선한다.
//
// 구성:
//   · 데스크톱(≥760px): 가운데 텍스트 링크(내 차 사기·AI로 찾기·내 차 팔기) 상시 노출.
//     오른쪽은 로그인 상태에 따라 (비로그인) 로그인·내 차 등록 텍스트 링크 /
//     (로그인) 찜♡·채팅🔔 아이콘 + 프로필▾ 드롭다운.
//   · 모바일(<760px): 텍스트 링크(가운데 3개 + 비로그인용 로그인·내 차 등록)가 햄버거(☰)
//     패널 안으로 접힌다. 찜·채팅 아이콘·프로필▾은 로그인 시 뷰포트와 무관하게 항상 보인다
//     (intent-contract "Always" — 로그인 사용자가 텍스트 링크에 가려 찜/채팅에 못 닿는 것을 막음).
//
// 760px은 Tailwind 기본 브레이크포인트가 아니라 mockups/consistency-1.html의 실측치라
// arbitrary variant(`min-[760px]:`)로 쓴다 — ResponsiveGrid가 640/1100에 쓰는 것과 같은 관례.
//
// 드롭다운·햄버거 패널은 기존 FocusTrap(포커스 이동+Tab 순환+Esc 닫힘+트리거 복귀)을 그대로
// 재사용한다(deferred-work.md 8.2 코드리뷰 결정 — "11 내비 드롭다운"이 바로 이 소비처).
// FocusTrap은 포커스가 컨테이너 밖으로 나가면 즉시 도로 끌어오지만(키보드/프로그램 포커스 방어),
// 마우스로 컨테이너 밖을 클릭하는 것까지는 안 막는다 — 그건 이 컴포넌트가 outside-click으로 직접 닫는다
// (코드리뷰 지적, 아래 useEffect 2개). 트리거 버튼도 각 컨테이너 ref 안에 포함시켜, 트리거를 다시
// 클릭했을 때 outside-click이 먼저 닫고 onClick 토글이 다시 열어버리는 경합을 피한다.
//
// role="menu"/"menuitem"은 WAI-ARIA menu 패턴(방향키·Home/End 탐색)을 함의하는데 여기선 Tab
// 순환만 구현돼 있어 실제 동작과 어긋난다(코드리뷰 지적) — 그래서 role은 안 붙인다. 트리거의
// aria-haspopup도 같은 이유로 "menu"가 아니라 "true"(2차 코드리뷰 지적 — "menu"는 그 자체로
// 메뉴 패턴을 약속하는 값이라 role 미부착과 모순됐다)로 둬, 코드가 스스로와 일치하게 한다.
// aria-label만으로 "여기 팝업이 있다"만 알린다(FocusTrap의 Tab 순환 popover로서는 그걸로 충분).
import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import FocusTrap from '@/components/ui/FocusTrap';
import LogoutButton from '@/components/auth/LogoutButton';
import { getConsumerNavLinks } from './nav-links';

// 아이콘 버튼 공통 스타일 — 히트영역 44×44px(h-11 w-11 = 2.75rem = 44px, intent-contract 접근성 바닥).
const ICON_BUTTON_CLASS =
  'flex h-11 w-11 items-center justify-center rounded-badge text-xl text-ink-secondary hover:bg-surface-base hover:text-ink-primary';

const TEXT_LINK_CLASS = 'text-sm font-medium text-ink-secondary hover:text-ink-primary';
const PANEL_LINK_CLASS = 'rounded px-3 py-3 text-sm font-medium text-ink-primary hover:bg-surface-base';

export default function SiteNav({
  email,
  currentPath,
}: {
  email?: string | null;
  currentPath?: string;
}) {
  const [profileOpen, setProfileOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  // 트리거+패널을 함께 감싸는 컨테이너 — outside-click 판정("이 안을 클릭했나")과 mutual-exclusion에 쓴다.
  const profileContainerRef = useRef<HTMLDivElement>(null);
  const menuContainerRef = useRef<HTMLDivElement>(null);

  // outside-click 닫기(코드리뷰 지적 #1) — FocusTrap은 포커스 이탈만 되돌릴 뿐 마우스 바깥 클릭은
  // 안 막으므로, 컨테이너 밖 pointerdown을 여기서 직접 감지해 닫는다. pointerdown을 쓰는 이유
  // (3차 코드리뷰 지적 P10 — 예전엔 mousedown이었다): 이 패널은 <760px 모바일 전용 UI라 마우스만
  // 잡는 mousedown으로는 터치·펜 입력을 놓친다 — pointerdown은 마우스·터치·펜을 모두 포괄하면서도
  // mousedown보다 먼저 발화해, 트리거를 다시 눌러 닫는 토글(onClick, 아래)보다 먼저 실행돼야 두
  // 핸들러가 서로 상태를 되돌리지 않는다는 기존 순서 요구를 그대로 지킨다 — 단 트리거도 컨테이너
  // 안에 있으므로 트리거 클릭 자체는 "바깥"으로 안 잡힌다.
  useEffect(() => {
    if (!profileOpen) return;
    function handlePointerDown(event: PointerEvent) {
      if (profileContainerRef.current && !profileContainerRef.current.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener('pointerdown', handlePointerDown);
    return () => document.removeEventListener('pointerdown', handlePointerDown);
  }, [profileOpen]);

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

  // 760px 이상으로 리사이즈되면 햄버거를 강제로 닫는다(코드리뷰 지적, 실측: 390px에서 열고
  // 1280px로 리사이즈해도 패널이 DOM에 남고 aria-expanded="true"가 유지된 채 다시 390px로
  // 줄이면 클릭 없이 되살아남) — 햄버거는 <760px 전용 UI라 그 폭을 벗어나면 상태가 무의미하다.
  // 프로필▾는 뷰포트 무관 상시 노출이라 대상 아님.
  useEffect(() => {
    const mql = window.matchMedia('(min-width: 760px)');
    function handleChange(event: MediaQueryListEvent) {
      if (event.matches) setMenuOpen(false);
    }
    mql.addEventListener('change', handleChange);
    return () => mql.removeEventListener('change', handleChange);
  }, []);

  // role-aware 훅 자리(nav-links.ts) — AppHeader가 roleLabel(문자열)만 받고 실제 role은
  // 안 받으므로 지금은 null을 넘긴다. Epic 14가 role을 스레딩할 때 이 자리를 바꾼다.
  const navLinks = getConsumerNavLinks(null);
  const loginHref = currentPath ? `/login?redirectedFrom=${encodeURIComponent(currentPath)}` : '/login';

  // 프로필▾·햄버거는 로그인 시 <760px에서 동시에 보인다(찜/채팅/프로필▾가 뷰포트 무관 상시 노출이라)
  // — 하나를 열 때 다른 하나를 닫아 FocusTrap 2개가 동시에 document 포커스를 다투지 않게 한다(코드리뷰 지적 #6).
  function toggleProfile() {
    setMenuOpen(false);
    setProfileOpen((v) => !v);
  }
  function toggleMenu() {
    setProfileOpen(false);
    setMenuOpen((v) => !v);
  }

  return (
    // relative는 여기 안 둔다 — 이 div는 로고 뒤(header 안 두 번째 flex 아이템)에서 시작해서
    // 모바일 패널(absolute inset-x-0)의 기준이 되면 패널이 로고만큼 오른쪽으로 밀린다(코드리뷰
    // 지적, 실측: 390px 뷰포트에서 패널 left=117.48px). 포지션 기준은 AppHeader.tsx의 <header>로 옮겼다.
    <div className="flex flex-1 items-center justify-between gap-4">
      {/* 가운데 3개 링크 — 데스크톱만(모바일은 햄버거 패널 안에). */}
      <nav aria-label="주요 메뉴" className="hidden items-center gap-6 min-[760px]:flex">
        {navLinks.map((link) => (
          <Link key={link.href} href={link.href} className={TEXT_LINK_CLASS}>
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="ml-auto flex items-center gap-2">
        {email ? (
          <>
            <Link href="/wishlist" aria-label="찜한 매물" className={ICON_BUTTON_CLASS}>
              <span aria-hidden>♡</span>
            </Link>
            <Link href="/chat" aria-label="채팅" className={ICON_BUTTON_CLASS}>
              <span aria-hidden>🔔</span>
            </Link>
            <div ref={profileContainerRef} className="relative">
              <button
                type="button"
                aria-haspopup="true"
                aria-expanded={profileOpen}
                aria-label={profileOpen ? '프로필 메뉴 닫기' : '프로필 메뉴 열기'}
                onClick={toggleProfile}
                className="flex h-11 items-center gap-1 rounded-badge px-2 text-sm font-medium text-ink-secondary hover:bg-surface-base hover:text-ink-primary"
              >
                프로필<span aria-hidden>▾</span>
              </button>
              {profileOpen && (
                <FocusTrap
                  open
                  onClose={() => setProfileOpen(false)}
                  aria-label="프로필 메뉴"
                  className="absolute right-0 top-full z-30 mt-2 flex w-44 flex-col gap-1 rounded-card border border-border-hairline bg-surface-raised p-2 shadow-card dark:shadow-none"
                >
                  <Link
                    href="/sell"
                    onClick={() => setProfileOpen(false)}
                    className="rounded px-3 py-2 text-sm text-ink-primary hover:bg-surface-base"
                  >
                    내 매물 관리
                  </Link>
                  <Link
                    href="/account"
                    onClick={() => setProfileOpen(false)}
                    className="rounded px-3 py-2 text-sm text-ink-primary hover:bg-surface-base"
                  >
                    내 정보
                  </Link>
                  <div className="px-1 pt-1">
                    <LogoutButton />
                  </div>
                </FocusTrap>
              )}
            </div>
          </>
        ) : (
          // 비로그인 데스크톱 — 로그인·내 차 등록도 텍스트 링크라 <760px에선 숨기고 햄버거로 접는다
          // (아래 모바일 패널이 같은 두 링크를 다시 그린다).
          <div className="hidden items-center gap-4 min-[760px]:flex">
            <Link href={loginHref} className={TEXT_LINK_CLASS}>
              로그인
            </Link>
            <Link href="/sell" className={TEXT_LINK_CLASS}>
              내 차 등록
            </Link>
          </div>
        )}

        {/* 모바일 햄버거 — <760px에서만 보인다(위 두 그룹은 그 폭에서 숨음). */}
        <div ref={menuContainerRef} className="min-[760px]:hidden">
          <button
            type="button"
            aria-haspopup="dialog"
            aria-expanded={menuOpen}
            aria-label={menuOpen ? '메뉴 닫기' : '메뉴 열기'}
            onClick={toggleMenu}
            className={ICON_BUTTON_CLASS}
          >
            <span aria-hidden>☰</span>
          </button>
          {menuOpen && (
            <FocusTrap
              open
              onClose={() => setMenuOpen(false)}
              role="dialog"
              aria-modal="true"
              aria-label="메뉴"
              className="absolute inset-x-0 top-full z-30 flex flex-col gap-1 border-b border-border-hairline bg-surface-raised p-3 shadow-card dark:shadow-none"
            >
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className={PANEL_LINK_CLASS}
                >
                  {link.label}
                </Link>
              ))}
              {!email && (
                <>
                  <Link href={loginHref} onClick={() => setMenuOpen(false)} className={PANEL_LINK_CLASS}>
                    로그인
                  </Link>
                  <Link href="/sell" onClick={() => setMenuOpen(false)} className={PANEL_LINK_CLASS}>
                    내 차 등록
                  </Link>
                </>
              )}
            </FocusTrap>
          )}
        </div>
      </div>
    </div>
  );
}
