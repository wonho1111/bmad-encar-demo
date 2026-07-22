'use client';

// 매물 상세의 문의 CTA — 데스크톱 sticky aside + 모바일 하단 고정 바 **두 배치를 이 컴포넌트 하나가**
// 함께 그린다(#82 종결, Story 10.6).
//
// 왜 하나로 합쳤나: 예전엔 두 배치에 각각 InquiryButton을 마운트해 busy/error 상태를 따로 들고 있었다
// (docs/tech-debt.md #82). ≥1024px에서 문의 실패로 에러가 뜬 채 창을 <1024px로 좁히면, 하단 바 쪽은
// 에러 없는 깨끗한 "문의하기"로 보였다 — 같은 문의가 두 군데서 다르게 보였다는 뜻이다.
// 여기서는 busy/error state를 이 컴포넌트 최상위에 **한 번만** 두고, 두 블록(desktop aside/mobile bar)이
// 그 값을 함께 읽어 렌더한다. 모바일 블록은 `position:fixed`라 이 컴포넌트가 grid 안에 있어도 뷰포트
// 하단에 그대로 고정된다(레이아웃엔 영향 없음).
//
// mode(anon/owner/inquiry)는 서버(page.tsx, user를 이미 들고 있음)가 계산해 넘긴다 — 상태를 갖는 분기는
// inquiry뿐이라 클라이언트는 그 계산을 다시 할 필요가 없다(AC7 3분기).
//
// 문의 개시 로직(openOrCreateRoom + busy/error) 자체는 옛 InquiryButton.tsx를 그대로 옮겼다
// (삭제됨 — 유일 사용처가 이 페이지였고 여기로 흡수됨, A3).
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { openOrCreateRoom } from '@/lib/chat';
import Button, { buttonClasses } from '@/components/ui/Button';

export type InquiryCtaMode = 'anon' | 'owner' | 'inquiry';

export default function InquiryCta({
  mode,
  listingId,
  loginHref,
  priceText,
}: {
  mode: InquiryCtaMode;
  listingId: string;
  loginHref: string;
  priceText: string;
}) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleInquiry() {
    if (busy) return; // 연타 차단(방이 두 번 열리는 것·이중 이동 방지)
    setError(null);
    setBusy(true);
    try {
      const supabase = createClient();

      // 현재 로그인 사용자 = 구매자. 방의 buyer_id가 된다.
      //   getUser()는 Auth 서버에 재검증해 신뢰 가능(쿠키만 믿지 않음).
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        // proxy가 비로그인을 1차로 막지만, 만약을 대비한 방어.
        setError('로그인이 필요합니다. 다시 로그인해주세요.');
        return;
      }

      // 방 열기(생성 또는 재사용) — 규칙은 @/lib/chat 한 곳에서.
      const result = await openOrCreateRoom(supabase, listingId, user.id);
      if ('error' in result) {
        setError(result.error);
        return;
      }

      // 성공 → 그 채팅방으로 이동.
      router.push(`/chat/${result.roomId}`);
    } catch (err) {
      console.error('[listings/detail] 문의하기 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setBusy(false);
    }
  }

  // 3분기 중 실제로 "동작"(상태를 갖는 쪽)은 inquiry뿐 — anon/owner는 그냥 링크다(AC7).
  function renderAction() {
    if (mode === 'anon') {
      // 비로그인 — 버튼을 숨기지 않는다. 어포던스는 보이고 게이트는 클릭에만 걸린다(FR58, conventions §8).
      return (
        <Link href={loginHref} className={buttonClasses({ className: 'w-full' })}>
          로그인하고 문의하기
        </Link>
      );
    }
    if (mode === 'owner') {
      // 본인 매물 — 자기 자신에게는 문의할 수 없다(DB의 CHECK(buyer_id<>seller_id)와 정합).
      //   버튼을 숨기지 않고 판매자 관리 화면으로 보낸다(9.5에서 바뀐 지점 — 막다른 길 방지).
      return (
        <Link href="/sell" className={buttonClasses({ variant: 'secondary', className: 'w-full' })}>
          내 매물 관리
        </Link>
      );
    }
    // 로그인 + 타인 매물 — 기존 문의 개시 흐름 그대로(방이 있으면 재사용, 없으면 생성).
    return (
      <div className="flex flex-col gap-1">
        <Button
          type="button"
          variant="primary"
          onClick={handleInquiry}
          loading={busy}
          loadingText="문의 채팅방 여는 중…"
          className="w-full"
        >
          문의하기
        </Button>
        {error && (
          <p role="alert" className="text-xs text-red-600 dark:text-red-400">
            {error}
          </p>
        )}
      </div>
    );
  }

  return (
    <>
      {/* 데스크톱 sticky aside — Story 9.5 AC7·D9. ≥1024px에서만(그 아래는 하단 고정 바가 대신한다).
          top-6: 이 앱의 상단바는 sticky가 아니라 함께 스크롤되므로, 헤더 높이가 아니라 본문
          여백(p-6)과 같은 값을 띄운다. */}
      <aside className="hidden lg:block">
        <div className="sticky top-6 flex flex-col gap-3 rounded-card border border-border-hairline bg-surface-raised p-5 shadow-card dark:shadow-none">
          {/* 가격 = 상세의 대표 숫자. 카드(26/800)보다 큰 large 변형(30/800, DESIGN.md:42). */}
          <p className="whitespace-nowrap text-price-lg font-extrabold text-price-emphasis">{priceText}</p>
          {renderAction()}
        </div>
      </aside>

      {/* 모바일·태블릿(<1024px) 하단 고정 바 — 가격 + CTA 상시(AC7).
          shadow-float = 떠 있는 요소용 겹 그림자(DESIGN.md:115). 가로 한 줄을 유지하고, 공간이
          부족하면 가격을 …로 자른다(D5 — 세로로 접거나 2줄로 밀지 않는다). */}
      <div className="fixed inset-x-0 bottom-0 z-10 flex items-center justify-between gap-3 border-t border-border-hairline bg-surface-raised px-4 py-3 shadow-float lg:hidden">
        <p className="truncate whitespace-nowrap text-price font-extrabold text-price-emphasis">{priceText}</p>
        <div className="shrink-0">{renderAction()}</div>
      </div>
    </>
  );
}
