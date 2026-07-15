// 모바일 캐러셀 프리미티브 — <640px 랜딩(인기/최신)처럼 캐러셀이 필요한 맥락 전용(UX-DR21).
//
// 전체 목록 화면은 ResponsiveGrid의 1열을 쓰고, 랜딩처럼 "가로로 훑어보는" 맥락만 이 컴포넌트를 쓴다
// (소비처가 선택). 1.2장 노출 = 다음 카드가 살짝 보여야 "옆으로 더 있다"는 스크롤 가능 신호가 된다.
// 스냅은 CSS(`snap-x snap-mandatory` + 자식 `snap-start`)만으로 충족되므로 JS(화살표 버튼 등)는
// 요청되지 않은 기능이라 넣지 않는다(A2).
import type { ReactNode } from 'react';

export default function CardCarousel({
  children,
  ariaLabel,
  className = '',
}: {
  children: ReactNode;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <div
      role="region"
      aria-label={ariaLabel || undefined}
      tabIndex={0}
      className={`scrollbar-hide flex snap-x snap-mandatory gap-4 overflow-x-auto motion-reduce:scroll-auto ${className}`}
    >
      {children}
    </div>
  );
}

// 캐러셀 자식 카드에 씌우는 래퍼 — basis-[82%]가 뷰포트 1장 대비 약 1.2장 노출을 만든다
// (카드 사이 gap-4까지 합쳐 다음 카드가 살짝 보이는 폭).
// min-w-0 필수: flex 아이템은 기본 min-width:auto(콘텐츠 크기)라, shrink-0과 만나면 카드 내부의
// 안 접히는 텍스트(차량명 truncate 등)가 basis를 무시하고 아이템을 옆으로 늘려버린다
// (직접 관찰로 발견 — 카드가 82%가 아니라 콘텐츠 폭만큼 튀어나옴). min-w-0이 그 강제 확장을 막는다.
export function CardCarouselItem({ children }: { children: ReactNode }) {
  return <div className="min-w-0 shrink-0 snap-start basis-[82%]">{children}</div>;
}
