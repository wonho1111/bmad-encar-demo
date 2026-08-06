// 상태/역할 뱃지 프리미티브 — pill(rounded-badge) 하나로 상태(활성/정지됨·판매중/판매완료)·역할
// (관리자/일반회원)·"나" 표시·안읽음 카운트 등을 통일된 톤으로 보여준다. 화면마다 조금씩 다른
// bg-*/text-* 조합을 반복하지 않도록 admin-mockups-2.html의 pill 시각 패턴(pill-status-on/off,
// pill-type, pill-me)을 토큰으로 재현해 한 곳에 모았다(Story 15.1). EmptyState/ErrorState와 동일하게
// props 최소, 토큰 클래스만 사용한다.
//
// tone:
//   active    = 긍정/진행중 (활성·판매중·역할 라벨·안읽음 카운트) → petrol tint (mockup pill-status-on/pill-type/pill-count)
//   neutral   = 종료/비활성 (판매완료) → 중립 테두리 (mockup pill-status-off, wishlist BlockedWishTile과 동일 패턴)
//   highlight = 본인 표시("나") → amber (mockup pill-me)
//   danger    = 정지·경고 (정지됨) → 위험 신호(코드리뷰 patch, 15.1) — neutral과 같은 톤을 쓰면
//     "정지됨"이 무해한 "판매완료"와 시각적으로 구분되지 않아 관리자가 위험 상태를 놓치기 쉬웠다.
import type { ReactNode } from 'react';

export type BadgeTone = 'active' | 'neutral' | 'highlight' | 'danger';

// 모든 톤이 border를 갖는다(색만 다름). neutral만 테두리를 두면 같은 목록 행에서 "판매중"(active)과
// "판매완료"(neutral)의 박스 높이가 1px씩 어긋난다 — 통일하려고 만든 프리미티브가 정렬을 흔든다
// (코드리뷰 patch, 15.1).
// active의 잉크가 brand-petrol이 아니라 brand-petrol-strong인 이유(코드리뷰 patch, 15.1 — 실측):
// petrol을 10% 틴트로 깐 배경 위에 같은 petrol로 글자를 쓰면 다크에서 대비가 무너진다. 다크의
// --brand-petrol(#4FA39D)은 라이트(#1E6E6A)보다 밝아지는데 배경 틴트도 같이 밝아져, 카드 행
// (--surface-raised #2B2A26) 위에서 4.17:1 — 12px text-caption은 큰 글자가 아니므로 AA 4.5:1 미달.
// 잉크만 한 단계 진한 --brand-petrol-strong으로 바꾸면 라이트 7.55~7.84 / 다크 5.49~6.33으로 양 모드
// 모두 통과하고, mockup이 지정한 "petrol 틴트 배경 + petrol 글자" 배색은 그대로 유지된다.
// 같은 조합의 리포 선례: (user)/sell/OptionPicker.tsx:159.
const TONE_CLASSES: Record<BadgeTone, string> = {
  active: 'border-transparent bg-brand-petrol/10 text-brand-petrol-strong',
  neutral: 'border-border-hairline text-ink-secondary',
  highlight: 'border-transparent bg-accent-amber text-amber-ink',
  danger: 'border-transparent bg-danger/10 text-danger',
};

export default function Badge({
  tone = 'active',
  children,
}: {
  tone?: BadgeTone;
  children: ReactNode;
}) {
  return (
    // shrink-0 whitespace-nowrap: 뱃지는 대부분 justify-between 행의 flex item으로 놓인다. 기본
    // flex-shrink가 걸리면 좁은 폭에서 "판매완료"·"일반회원"이 두 줄로 접히는데, 이는 반응형 무결성
    // 규칙 D5("내부 가로 배치를 세로로 접지 않는다")가 금지하는 것이다. 공간 부족은 옆 텍스트의
    // truncate로 흡수한다(코드리뷰 patch, 15.1).
    <span
      className={`inline-block shrink-0 whitespace-nowrap rounded-badge border px-2 py-0.5 text-caption font-medium ${TONE_CLASSES[tone]}`}
    >
      {children}
    </span>
  );
}
