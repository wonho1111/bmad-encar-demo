// 홈 / 로그인 후 첫 화면 (FR2) — 서버 컴포넌트.
// 로그인 상태면 이메일·역할을 보여주고 로그아웃 버튼을, 비로그인 상태면 로그인/회원가입 링크를 보여준다.
// 서버에서는 getSession()이 아니라 getUser()를 쓴다 — 쿠키를 그대로 믿지 않고 Auth 서버에 재검증해 신뢰 가능.
// (보호 경로 직접 접근 차단·역할별 라우팅은 Story 1.4 middleware 범위)
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { USER_ROLE, type UserRole } from '@/lib/constants';
import LogoutButton from '@/components/auth/LogoutButton';

// profiles.role 값(영문)을 화면 표시용 한국어 라벨로 변환한다. 값의 단일 출처는 USER_ROLE 상수.
const ROLE_LABEL: Record<UserRole, string> = {
  [USER_ROLE.BUYER]: '구매자',
  [USER_ROLE.SELLER]: '판매자',
  [USER_ROLE.ADMIN]: '관리자',
};

export default async function Home() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 로그인 상태면 본인 역할 조회(profiles_select_self RLS가 본인 행 읽기를 허용).
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">중고차 직거래</h1>

      {user ? (
        <div className="flex flex-col gap-4">
          <div className="rounded bg-zinc-50 px-4 py-3 text-sm dark:bg-zinc-900">
            <p>
              <span className="text-zinc-500">이메일</span> {user.email}
            </p>
            {roleLabel && (
              <p>
                <span className="text-zinc-500">역할</span> {roleLabel}
              </p>
            )}
          </div>
          <LogoutButton />
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-sm text-zinc-500">로그인하고 서비스를 이용해보세요.</p>
          <div className="flex gap-3">
            <Link
              href="/login"
              className="rounded bg-zinc-900 px-4 py-2 text-sm font-medium text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              로그인
            </Link>
            <Link
              href="/signup"
              className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
            >
              회원가입
            </Link>
          </div>
        </div>
      )}
    </main>
  );
}
