// 차장님 로고 lockup (UX-DR9/D7 방향 A "차 배지")
// petrol 라운드-스퀘어 배지 + 굵은 "차"(Pretendard 800) + "차장님" 워드마크.
// 색·radius·폰트는 전부 Story 8.1 디자인 토큰 사용(하드코딩 hex 금지).
// 순수 표시 컴포넌트 — 클릭/링크 없음(내비 배선은 Epic 11).
// 실제 아트워크는 추후 제작 — 현재 lockup 임시.

type LogoSize = "sm" | "md";

// 배지 글자색을 surface-base로 두는 이유: brand-petrol 배지는 라이트=진한 청록/다크=밝은 청록으로
// 스왑되는데, surface-base는 라이트≈흰색/다크≈검정으로 정반대로 스왑되므로 양 모드 모두 대비가 유지된다.
// 배지 글자("차")는 **배지 크기의 약 0.43배**로 둔다 — 목업(mockups/detail-1.html의 `.logo-mark`)이
// 29px 배지에 12.5px 글자를 쓴 비율이다. 예전엔 sm=28px 배지에 16px(0.57배)이라 "차"가 배지를
// 꽉 채워 어색했다(2026-08-13 사용자 지적 #3). 배지 자체 크기는 그대로 두고 글자만 줄인다.
const SIZES: Record<LogoSize, { badge: string; word: string }> = {
  sm: { badge: "h-7 w-7 text-xs", word: "text-base" },
  md: { badge: "h-10 w-10 text-lg", word: "text-xl" },
};

export default function Logo({ size = "md" }: { size?: LogoSize }) {
  const s = SIZES[size];
  return (
    <span className="inline-flex select-none items-center gap-2">
      <span
        aria-hidden
        className={`inline-flex items-center justify-center rounded-badge bg-brand-petrol font-extrabold text-surface-base ${s.badge}`}
      >
        차
      </span>
      <span className={`font-bold text-ink-primary ${s.word}`}>차장님</span>
    </span>
  );
}
