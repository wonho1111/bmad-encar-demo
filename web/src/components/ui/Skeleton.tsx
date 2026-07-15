// 로딩 상태 프리미티브 — 펄스 블록(`Skeleton`) + 카드형 조합 헬퍼(`CardSkeleton`).
// 소비 화면(9 카드·11 랜딩 등)이 실제 데이터가 오기 전 자리표시로 그리드/캐러셀에 채운다.
// 토큰만 사용(하드코딩 hex 금지 — 8.1 규약), reduced-motion에서 펄스 정지(motion-reduce 변형).

export function Skeleton({ className = '' }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`animate-pulse rounded-card bg-placeholder-bg motion-reduce:animate-none ${className}`}
    />
  );
}

// 대표 카드형 스켈레톤(사진 5:3 + 텍스트 라인 2줄) — ResponsiveGrid 칸 하나에 그대로 넣는 용도.
// label은 props로 받는다(하드코딩 금지 — AC3). 기본값은 두되 소비처가 맥락 문구로 덮어쓸 수 있다.
export function CardSkeleton({ label = '불러오는 중' }: { label?: string } = {}) {
  return (
    <div
      aria-busy="true"
      aria-label={label}
      className="flex flex-col gap-3 rounded-card border border-border-hairline bg-surface-raised p-[18px] shadow-card dark:shadow-none"
    >
      <Skeleton className="aspect-[5/3] w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-4 w-1/2" />
    </div>
  );
}
