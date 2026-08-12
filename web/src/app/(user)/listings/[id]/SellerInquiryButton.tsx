'use client';

// "판매자정보" 카드 맨 아래 문의 버튼 — 목업 detail-1.html `.seller-contact-btn`
// ("판매자에게 문의하기", 2026-08-13 사용자 지적 #2).
//
// 왜 필요했나: 이 화면의 **가장 아래 버튼이 "매물 목록으로"** 였다. 매물을 다 읽고 내려온 사람에게
// 마지막으로 권하는 행동이 "나가기"였다는 뜻이다. 목업은 그 자리에 문의를 놓는다. 목록으로
// 돌아가는 길은 화면 맨 위 breadcrumb("‹ 매물 목록")으로 옮겼다.
//
// 상태는 InquiryCta와 **공유하지 않는다**(각자 useInquiryAction 인스턴스). 이유는
// useInquiryAction.ts 상단 주석 참조 — 두 버튼은 화면에 동시에 보이므로 #82(안 보이는 불일치)와
// 다른 상황이고, 누른 쪽에만 진행 표시가 뜨는 게 자연스럽다.
import Link from 'next/link';
import Button, { buttonClasses } from '@/components/ui/Button';
import type { InquiryCtaMode } from './InquiryCta';
import { useInquiryAction } from './useInquiryAction';

export default function SellerInquiryButton({
  mode,
  listingId,
  loginHref,
}: {
  mode: InquiryCtaMode;
  listingId: string;
  loginHref: string;
}) {
  const { busy, error, start } = useInquiryAction(listingId);

  // 3분기는 InquiryCta와 같은 규칙이다(AC7) — 여기선 톤만 secondary(주 CTA는 위 요약 카드 쪽).
  if (mode === 'anon') {
    return (
      <Link
        href={loginHref}
        className={buttonClasses({ variant: 'secondary', className: 'w-full' })}
      >
        로그인하고 판매자에게 문의하기
      </Link>
    );
  }
  if (mode === 'owner') {
    return (
      <Link href="/sell" className={buttonClasses({ variant: 'secondary', className: 'w-full' })}>
        내 매물 관리
      </Link>
    );
  }
  return (
    <div className="flex flex-col gap-1">
      <Button
        type="button"
        variant="secondary"
        onClick={() => void start()}
        loading={busy}
        loadingText="문의 채팅방 여는 중…"
        className="w-full"
      >
        판매자에게 문의하기
      </Button>
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
