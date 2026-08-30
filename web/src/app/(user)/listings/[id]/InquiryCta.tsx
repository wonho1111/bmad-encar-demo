'use client';

// 매물 상세의 문의 CTA — **데스크톱 요약 컬럼 안 버튼 + 모바일 하단 고정 바** 두 배치를 이
// 컴포넌트 하나가 함께 그린다(#82 종결, Story 10.6).
//
// 왜 하나로 합쳤나: 예전엔 두 배치에 각각 InquiryButton을 마운트해 busy/error 상태를 따로 들고 있었다
// (docs/tech-debt.md #82). ≥1024px에서 문의 실패로 에러가 뜬 채 창을 <1024px로 좁히면, 하단 바 쪽은
// 에러 없는 깨끗한 "문의하기"로 보였다 — 같은 문의가 두 군데서 다르게 보였다는 뜻이다.
// 여기서는 useInquiryAction 훅을 **한 번만** 부르고, 두 블록이 그 값을 함께 읽어 렌더한다.
//
// ✎ 2026-08-13(#2 상세 재구성) — 예전엔 이 컴포넌트가 `<aside>` 카드(가격 + 버튼)를 통째로
//   그렸다. 지금은 **요약 카드 자체를 page.tsx가 그리고**(제목·찜·신뢰뱃지·가격·주요제원 6칸까지
//   목업 detail-1.html의 `.summary-col` 구성 그대로), 이 컴포넌트는 그 카드 **안에 들어가는 버튼**과
//   모바일 고정 바만 맡는다. 사용자 지적이 정확히 그 지점이었다 — "문의하기 쪽에 아무것도 없고
//   모든 값이 아래에 있는데 목업엔 문의하기 쪽에 여러 정보가 있다".
//
// mode(anon/owner/inquiry)는 서버(page.tsx, user를 이미 들고 있음)가 계산해 넘긴다 — 상태를 갖는 분기는
// inquiry뿐이라 클라이언트는 그 계산을 다시 할 필요가 없다(AC7 3분기).
import Link from 'next/link';
import Button, { buttonClasses } from '@/components/ui/Button';
import { useInquiryAction } from './useInquiryAction';
import MarketDiagnosisButton, { type MarketDiagnosisButtonListing } from './MarketDiagnosisButton';

export type InquiryCtaMode = 'anon' | 'owner' | 'inquiry';

// CTA 밑 한 줄 안내(목업 `.cta-helper`) — 분기마다 다음에 무슨 일이 일어나는지 미리 알려준다.
const HELPER_TEXT: Record<InquiryCtaMode, string> = {
  anon: '로그인 후 판매자와 바로 채팅할 수 있어요',
  owner: '내가 등록한 매물이에요',
  inquiry: '판매자와 1:1 채팅으로 바로 이어져요',
};

export default function InquiryCta({
  mode,
  listingId,
  loginHref,
  priceText,
  marketDiagnosisListing,
}: {
  mode: InquiryCtaMode;
  listingId: string;
  loginHref: string;
  // "AI 시세 진단" 버튼(5단계)의 프리필 질의 재료 — page.tsx가 이미 들고 있는 요약 필드 그대로.
  marketDiagnosisListing: MarketDiagnosisButtonListing;
  priceText: string;
}) {
  const { busy, error, start } = useInquiryAction(listingId);

  // 3분기 중 실제로 "동작"(상태를 갖는 쪽)은 inquiry뿐 — anon/owner는 그냥 링크다(AC7).
  function renderAction() {
    if (mode === 'anon') {
      // 비로그인 — 버튼을 숨기지 않는다. 어포던스는 보이고 게이트는 클릭에만 걸린다(FR58, conventions §8).
      return (
        // data-testid: E2E(web/e2e/viewport-audit.spec.ts)가 텍스트·클래스가 아니라 이 안정적인
        // 훅으로 CTA를 찾는다(코드리뷰 patch, listing-photo와 동일 취지) — 요약 컬럼·모바일
        // 하단 바 두 인스턴스가 DOM에 항상 함께 있으므로(Tailwind가 display로만 전환) 실제로
        // 보이는 쪽만 `:visible`로 골라 쓴다.
        <Link href={loginHref} data-testid="inquiry-cta" className={buttonClasses({ className: 'w-full' })}>
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
          onClick={() => void start()}
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
      {/* 요약 카드 안 CTA — ≥1024px에서만(그 아래는 하단 고정 바가 대신한다).
          "AI 시세 진단"(5단계)은 문의하기 **위**에 한 줄 추가한다(목업 STEP1 확정, 레이아웃 변형
          없음) — 판단(시세)→행동(문의) 순서. 모바일 하단 고정 바는 가격+CTA 한 줄 레이아웃이라
          버튼을 하나 더 넣으면 그 자체가 레이아웃 변형이 되므로 여기 데스크톱 스택에만 둔다. */}
      <div className="hidden flex-col gap-2 lg:flex">
        <MarketDiagnosisButton mode={mode} listing={marketDiagnosisListing} loginHref={loginHref} />
        {renderAction()}
        <p className="text-center text-caption text-ink-muted">{HELPER_TEXT[mode]}</p>
      </div>

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
