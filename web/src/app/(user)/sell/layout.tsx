// 매물 등록·관리 레이아웃 — 소유권 기반 게이트(FR52·FR53). role 값과 무관하게 로그인만 확인한다.
// proxy가 "로그인 여부"를 1차로 거르고(/sell 보호 경로), 여기서도 로그인 여부를 2차로 재확인한다.
//   - 비로그인 → /login (proxy가 먼저, requireUser도 동일)
// role='buyer'/'seller' 구분 없이 로그인 사용자 누구나 이 화면에 들어올 수 있다(spec-14-3).
// 그 뒤 DB가 무엇을 막고 무엇을 안 막는지는 나뉜다:
//   · 등록(INSERT) — listings_insert_own은 `with check (auth.uid() = seller_id)`라 "남의 명의로
//     등록"만 막는다. "누가 등록할 수 있나"를 제한하는 곳은 DB가 아니라 이 로그인 게이트뿐이다.
//   · 수정·삭제·구매완료(UPDATE/DELETE) — listings_update_own·listings_delete_own의 소유권 조건이
//     실제로 타인 행을 0행으로 막는다(여기가 RLS가 집행하는 구간이다).
// 라우트 그룹 `(user)`는 URL에 포함되지 않으므로 실제 경로는 /sell 이다.
import type { ReactNode } from 'react';
import { requireUser } from '@/lib/auth/guard';
import AppHeader from '@/components/layout/AppHeader';

export default async function SellLayout({ children }: { children: ReactNode }) {
  // requireUser는 통과 시 로그인 사용자를 반환한다 → 상단바에 이메일을 표시한다.
  const user = await requireUser();
  return (
    <>
      <AppHeader email={user.email} currentPath="/sell" />
      {children}
    </>
  );
}
