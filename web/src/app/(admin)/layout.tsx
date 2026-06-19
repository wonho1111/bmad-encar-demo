// 관리자 영역 레이아웃 — role=admin만 통과시킨다(FR3).
// proxy가 "로그인 여부"를 1차로 거르고, 여기서 "관리자 역할"을 2차로 실집행한다.
//   - 비로그인 → /login
//   - 비관리자(구매자·판매자) → 홈 /
// 라우트 그룹 `(admin)`은 URL에 포함되지 않으므로 실제 경로는 /admin 이다.
import type { ReactNode } from 'react';
import { requireRole } from '@/lib/auth/guard';
import { USER_ROLE } from '@/lib/constants';

export default async function AdminLayout({ children }: { children: ReactNode }) {
  await requireRole(USER_ROLE.ADMIN);
  return <>{children}</>;
}
