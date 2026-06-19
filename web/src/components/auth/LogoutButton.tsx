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

  async function handleLogout() {
    if (loading) return; // 중복 클릭 방지
    setLoading(true);
    try {
      const supabase = createClient();
      await supabase.auth.signOut();
      router.push('/login');
      router.refresh();
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleLogout}
      disabled={loading}
      className="rounded border border-zinc-300 px-4 py-2 text-sm font-medium disabled:opacity-50 dark:border-zinc-700"
    >
      {loading ? '처리 중…' : '로그아웃'}
    </button>
  );
}
