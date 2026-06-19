// 판매자 영역 레이아웃 — role=seller만 통과시킨다(FR3·AC4).
// proxy가 "로그인 여부"를 1차로 거르고(/sell 보호 경로), 여기서 "판매자 역할"을 2차로 실집행한다.
//   - 비로그인 → /login (proxy가 먼저, requireRole도 동일)
//   - 비판매자(구매자·관리자) → 홈 /
// 라우트 그룹 `(user)`는 URL에 포함되지 않으므로 실제 경로는 /sell 이다.
// (admin)/layout.tsx와 동일한 이중 방어 패턴(재발명 금지).
import type { ReactNode } from 'react';
import { requireRole } from '@/lib/auth/guard';
import { USER_ROLE, ROLE_LABEL } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';

export default async function SellLayout({ children }: { children: ReactNode }) {
  // requireRole은 통과 시 로그인 사용자를 반환한다 → 상단바에 이메일을 표시한다.
  const user = await requireRole(USER_ROLE.SELLER);
  return (
    <>
      <AppHeader roleLabel={ROLE_LABEL[USER_ROLE.SELLER]} email={user.email} />
      {children}
    </>
  );
}
