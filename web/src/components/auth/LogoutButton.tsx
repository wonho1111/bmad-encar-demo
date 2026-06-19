'use client';

// 로그아웃 버튼 (FR2) — 클릭하면 Supabase 세션을 파기하고 로그인 화면으로 보낸다.
// signOut()은 로컬 세션 쿠키와 서버 세션을 모두 무효화한다.
// router.refresh()로 서버 컴포넌트(홈 등)가 비로그인 상태를 다시 렌더하게 한다.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export default function LogoutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleLogout() {
    if (loading) return; // 중복 클릭 방지
    setError(null);
    setLoading(true);
    try {
      const supabase = createClient();
      const { error: signOutError } = await supabase.auth.signOut();
      if (signOutError) {
        // signOut이 에러를 반환(예: 네트워크 문제) → 한국어 안내, 버튼은 재활성되어 재시도 가능.
        setError('로그아웃 중 오류가 발생했습니다. 다시 시도해주세요.');
        return;
      }
      router.push('/login');
      router.refresh();
    } catch {
      // signOut이 throw하는 예외(네트워크 단절 등)도 사용자에게 알리고 재시도 가능하게 둔다.
      setError('로그아웃 중 오류가 발생했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <button
        type="button"
        onClick={handleLogout}
        disabled={loading}
        className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
      >
        {loading ? '처리 중…' : '로그아웃'}
      </button>
      {error && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
