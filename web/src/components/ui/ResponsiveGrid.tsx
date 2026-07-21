// D5 반응형 그리드 프리미티브 — 가로폭 흡수는 "열 수"로만 한다(4→2→1).
//
// 왜 이 컴포넌트가 있나:
//   project-context 규칙13(D5 무결성)이 전 UI에 강제하는 규약: 화면이 좁아져도 카드 내부 가로 배치
//   (신뢰속성 행·meta·버튼 라벨 등)를 세로로 접으면 안 된다. 이 규칙을 매 화면이 따로 구현하면 반드시
//   어긋나는 곳이 생긴다. 그래서 열 수·브레이크포인트를 이 컴포넌트 하나에 고정해두고, 소비 화면(9 카드·
//   11 랜딩·15 관리자 등)은 이 그리드에 카드를 넣기만 하면 흡수 규칙을 공짜로 상속한다.
//
// 브레이크포인트 정본(EXPERIENCE.md 161행): ≥1100px=4열 · 640~1099px=2열 · <640px=1열.
// 1100px은 Tailwind 기본 브레이크포인트가 아니므로 두 경계 다 arbitrary variant(`min-[640px]:`·
// `min-[1100px]:`)로 쓴다. 640은 Tailwind 기본 `sm:`과 같은 값이지만, `sm:`(이름 있는 브레이크포인트)과
// `min-[1100px]:`(arbitrary 브레이크포인트)를 섞으면 Tailwind가 둘을 다른 정렬 그룹으로 취급해
// CSS 출력 순서가 뒤바뀐다 — 640이 나중에 출력되며 1100 규칙을 덮어써 데스크톱에서 4열이 2열로
// 깨진다(직접 관찰로 발견). 그래서 두 경계를 같은 arbitrary 종류로 통일해 순서를 보장한다.
import { Children, isValidElement, type ReactNode } from 'react';

export default function ResponsiveGrid({
  children,
  className = '',
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    // role="list"/"listitem": display:grid인 <ul>은 Safari/VoiceOver에서 암묵적 리스트 시맨틱이
    // 빠진다. 각 자식을 감싼 div가 실제 grid item이 되므로 레이아웃(열 수·행 흐름)은 그대로 유지된다.
    <div
      role="list"
      className={`grid grid-cols-1 gap-5 min-[640px]:grid-cols-2 min-[1100px]:grid-cols-4 ${className}`}
    >
      {Children.toArray(children).map((child) => (
        <div key={isValidElement(child) ? child.key : undefined} role="listitem">
          {child}
        </div>
      ))}
    </div>
  );
}
