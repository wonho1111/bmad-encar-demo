'use client';

// 소비자용 상단 내비 본체(spec-11-2) — AppHeader(서버 컴포넌트)가 로고 뒤에 배선한다.
//
// 구성:
//   · 데스크톱(≥760px): 가운데 텍스트 링크(내 차 사기·AI로 찾기·내 차 팔기) 상시 노출.
//     오른쪽은 로그인 상태에 따라 (비로그인) 로그인 텍스트 링크 /
//     (로그인) 찜♡·채팅🔔 아이콘 + 프로필▾ 드롭다운.
//   · 모바일(<760px): 텍스트 링크(가운데 3개 + 비로그인용 로그인)가 햄버거(☰)
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
//
// ✎ 2026-08-13 사용자 지적 #1("테두리나 이모지 일관성이 없음") — 세 가지를 함께 맞췄다:
//   ① **이모지(♡·💬·☰)를 선(stroke) 아이콘으로 교체**한다. 이모지는 글꼴이 그리므로 OS·브라우저마다
//      두께·색·크기가 제각각이고(♡는 얇은 윤곽선, 💬는 색이 박힌 컬러 이모지) 서로 다른 그림처럼
//      보였다. 목업(mockups/detail-1.html `.topnav-right`)은 셋 다 같은 굵기의 stroke SVG다.
//   ② **테두리를 셋 다 두른다.** 예전엔 아무 버튼에도 테두리가 없었는데 목업의 `.icon-btn`은
//      1px border + 흰 배경이라 "누를 수 있는 것"이 눈에 잡힌다.
//   ③ 크기는 목업의 34px이 아니라 **44px을 유지**한다 — 34px은 이 리포가 못박은 접근성 바닥(44px)
//      아래다. 테두리·아이콘만 목업을 따르고 히트영역은 우리 기준을 지킨다.
const ICON_BUTTON_CLASS =
  'flex h-11 w-11 items-center justify-center rounded-badge border border-border-hairline bg-surface-raised text-ink-secondary hover:bg-surface-base hover:text-ink-primary';

// 아이콘 3종 — 전부 24×24 viewBox·stroke 1.8·currentColor로 통일한다(위 ①의 실체).
// path 데이터는 목업 mockups/detail-1.html의 것을 그대로 쓴다(하트·햄버거). 채팅만 종(🔔)이 아니라
// 말풍선이다 — 이 앱엔 알림함이 없고 이 링크는 문의 채팅으로 가므로(2026-07-29 사용자 결정), 그
// 결정을 SVG로 옮기면서도 유지한다.
const ICON_SVG_CLASS = 'h-[18px] w-[18px]';

function HeartIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={ICON_SVG_CLASS}>
      <path
        d="M12 20.5s-7.5-4.6-10-9.2C.5 8 2 4.5 5.5 4.1c2-.2 3.7.8 4.9 2.5 1.2-1.7 2.9-2.7 4.9-2.5C18.8 4.5 20.3 8 19 11.3c-2.5 4.6-10 9.2-10 9.2z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={ICON_SVG_CLASS}>
      <path
        d="M4 5.5h16a1 1 0 0 1 1 1v8.5a1 1 0 0 1-1 1H9.5L4.8 19.6A.5.5 0 0 1 4 19.2V6.5a1 1 0 0 1 1-1z"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className={ICON_SVG_CLASS}>
      <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function ChevronDownIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden className="h-3 w-3 text-ink-muted">
      <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const TEXT_LINK_CLASS = 'text-sm font-medium text-ink-secondary hover:text-ink-primary';
const PANEL_LINK_CLASS = 'rounded px-3 py-3 text-sm font-medium text-ink-primary hover:bg-surface-base';

// 안읽음 배지 표기 상한(코드리뷰 patch, FR57) — 99 초과는 "99+"로 눌러 작은 원형 배지가 깨지지
// 않게 한다. 롤아웃 시점(스펙 I/O 매트릭스)엔 과거 메시지 전부가 1회성으로 잡혀 두 자리를 넘길 수 있다.
// ⚠️ **이 상한은 눈에 보이는 배지에만 적용한다.** aria-label에는 정확한 건수를 넣는다 — 상한을
//    둔 이유가 "작은 원이 깨진다"는 레이아웃 사정이라 화면 낭독에는 해당되지 않고, 스크린리더
//    사용자만 "99+건"이라는 뭉갠 값을 받는 것은 비색 신호 중복(UX-DR22)의 취지에 어긋난다
//    (후속 코드리뷰 patch).
function formatUnreadBadge(count: number): string {
  return count > 99 ? '99+' : String(count);
}

export default function SiteNav({
  email,
  currentPath,
  unreadCount,
}: {
  email?: string | null;
  currentPath?: string;
  // 안읽음 문의 총합(FR57, Story 12.5) — AppHeader가 로그인 시에만 chat_unread_count()로 계산해 넘긴다.
  // 0 또는 undefined면 배지를 렌더하지 않는다.
  unreadCount?: number;
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
              <HeartIcon />
            </Link>
            {/* 안읽음 배지(FR57) — 점(색이 있는 작은 배지) 안에 숫자를 넣어 "점+숫자"를 한 요소로
                충족하고, aria-label에도 건수를 반영해 비색 신호를 중복시킨다(UX-DR22). 0(또는
                undefined)이면 배지를 렌더하지 않는다 — 방 목록에는 방별 개별 표시를 두지 않는다(Never).
                99 초과는 "99+"로 표기(코드리뷰 patch) — 롤아웃 시점엔 과거 메시지 전부가 1회성으로
                잡혀(스펙 I/O 매트릭스) 숫자가 커질 수 있는데, 상한 없이 그대로 넣으면 이 작은
                원형 배지가 깨진다. */}
            <Link
              href="/chat"
              aria-label={unreadCount ? `채팅, 안읽음 메시지 ${unreadCount}건` : '채팅'}
              className={`relative ${ICON_BUTTON_CLASS}`}
            >
              {/* 말풍선 — UX-DR16 원문은 "채팅🔔"이었으나 종 모양이 "알림함"으로 읽혀
                  실제로 문의 채팅으로 이동하는 동작과 어긋난다는 사용자 지적으로 말풍선으로
                  교체했다(사용자 결정 2026-07-29). 이 앱엔 알림함 기능 자체가 없다(푸시는
                  PRD에서 "다음 증분"으로 범위 밖). 링크·배지·aria-label은 그대로다.
                  2026-08-13(#1)에 컬러 이모지 💬 → 같은 굵기의 stroke SVG로 바꿨다(위 ICON_BUTTON_CLASS 주석). */}
              <ChatIcon />
              {/* bg-red-600 — red-500(#EF4444)은 흰 글자 대비 3.76:1로 AA(4.5:1) 미달이다.
                  red-600(#DC2626)은 4.83:1로 통과하며 라이트·다크 양쪽 배경에서 같은 값을 쓴다
                  (후속 코드리뷰 patch. 이 배지는 10px 소형 텍스트라 대비 여유가 없다). */}
              {unreadCount ? (
                <span
                  aria-hidden
                  className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold leading-none text-white"
                >
                  {formatUnreadBadge(unreadCount)}
                </span>
              ) : null}
            </Link>
            <div ref={profileContainerRef} className="relative">
              <button
                type="button"
                aria-haspopup="true"
                aria-expanded={profileOpen}
                aria-label={profileOpen ? '프로필 메뉴 닫기' : '프로필 메뉴 열기'}
                onClick={toggleProfile}
                // 목업 `.profile-btn`(pill + 아바타 + 라벨 + 셰브런) — 옆 아이콘 버튼과 같은 테두리·배경을
                // 쓰되 모양만 알약이라 "계정"임이 구분된다(#1). 높이는 아이콘 버튼과 같은 44px.
                className="flex h-11 shrink-0 items-center gap-1.5 rounded-full border border-border-hairline bg-surface-raised py-1 pl-1.5 pr-2 text-sm font-semibold text-ink-primary hover:bg-surface-base min-[760px]:gap-2 min-[760px]:pr-3"
              >
                <span
                  aria-hidden
                  className="h-7 w-7 shrink-0 rounded-full bg-gradient-to-br from-accent-amber to-price-emphasis"
                />
                {/* 라벨은 <760px에서 숨긴다 — 그 폭에선 오른쪽에 찜·채팅·프로필·햄버거 넷이 들어가는데,
                    라벨까지 있으면 "프로 / 필"로 두 줄이 된다(390px 실측). 버튼의 접근성 이름은
                    위 aria-label이 이미 갖고 있어 라벨을 숨겨도 화면낭독엔 손실이 없다. */}
                <span className="hidden whitespace-nowrap min-[760px]:inline">프로필</span>
                <ChevronDownIcon />
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
          // 비로그인 데스크톱 — 로그인 링크 하나. <760px에선 숨기고 햄버거로 접는다(아래 모바일 패널이 다시 그린다).
          //
          // ✎ 2026-08-13 사용자 지적 #4 — 여기 있던 "내 차 등록"(/sell)을 뺐다. 이유 두 가지:
          //   ① 가운데 주요 메뉴의 "내 차 팔기"가 **같은 /sell**로 가는 중복 링크였다.
          //   ② 로그인하면 이 자리가 찜·채팅·프로필로 바뀌면서 그 버튼만 사라져, 로그인 전후로
          //      "있던 버튼이 없어지는" 어긋남이 생겼다. 가운데 "내 차 팔기"는 로그인 여부와
          //      무관하게 그대로 있으므로 진입로 자체가 없어지는 것은 아니다.
          <div className="hidden items-center gap-4 min-[760px]:flex">
            <Link href={loginHref} className={TEXT_LINK_CLASS}>
              로그인
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
            <MenuIcon />
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
              {/* 비로그인만 — "내 차 등록"은 위 데스크톱 분기와 같은 이유로 뺐다(#4, /sell 중복). */}
              {!email && (
                <Link href={loginHref} onClick={() => setMenuOpen(false)} className={PANEL_LINK_CLASS}>
                  로그인
                </Link>
              )}
            </FocusTrap>
          )}
        </div>
      </div>
    </div>
  );
}
