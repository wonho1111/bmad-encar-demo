// 소비자 내비 링크 — role-aware 확장 지점(spec-11-2 §Code Map).
//
// 지금은 role과 무관하게 항상 같은 3개 링크("내 차 사기·AI로 찾기·내 차 팔기")를 반환한다.
// role 파라미터는 지금 쓰이지 않지만 자리를 미리 잡아둔다 — Epic 14가 역할별 분기(예: 관리자
// 전용 링크 추가·판매자 전용 항목 등)를 붙일 때 이 함수 하나만 고치면 되고, 이 함수를 쓰는
// SiteNav.tsx의 JSX는 재작성할 필요가 없다(epic-11-context.md "role-aware 훅 자리로 선설계").
import type { UserRole } from '@/lib/constants';

export type NavLink = {
  label: string;
  href: string;
};

export function getConsumerNavLinks(role: UserRole | null): NavLink[] {
  void role; // 지금은 role 무관 — Epic 14가 실제 분기를 넣을 자리(위 주석 참조).
  return [
    { label: '내 차 사기', href: '/search' },
    { label: 'AI로 찾기', href: '/ai' },
    { label: '내 차 팔기', href: '/sell' },
  ];
}
