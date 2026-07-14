// 관리자 영역 레이아웃 — role=admin만 통과시킨다(FR3).
// proxy가 "로그인 여부"를 1차로 거르고, 여기서 "관리자 역할"을 2차로 실집행한다.
//   - 비로그인 → /login
//   - 비관리자(구매자·판매자) → 홈 /
// 라우트 그룹 `(admin)`은 URL에 포함되지 않으므로 실제 경로는 /admin 이다.
import type { ReactNode } from 'react';
import { requireRole } from '@/lib/auth/guard';
import { USER_ROLE, ROLE_LABEL } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';

export default async function AdminLayout({ children }: { children: ReactNode }) {
  // requireRole은 통과 시 로그인 사용자를 반환한다 → 상단바에 이메일을 표시한다.
  const user = await requireRole(USER_ROLE.ADMIN);
  // 홈(/)과 동일한 공용 상단바(역할·이메일 좌, 로그아웃 우)를 쓴다.
  //   관리자는 홈으로 가면 /admin으로 다시 유도되므로, 로그아웃 동선을 관리 영역 안에 둔다.
  return (
    <>
      <AppHeader roleLabel={ROLE_LABEL[USER_ROLE.ADMIN]} email={user.email} currentPath="/admin" />
      {children}
    </>
  );
}
