'use client';

// 로그아웃 버튼 (FR2) — 클릭하면 Supabase 세션을 파기하고 **공개 랜딩(/)** 으로 보낸다.
// signOut()은 로컬 세션 쿠키와 서버 세션을 모두 무효화한다.
// router.refresh()로 서버 컴포넌트(홈 등)가 비로그인 상태를 다시 렌더하게 한다.
//
// ⚠️ **2026-07-29 이전엔 `/login`으로 보냈다(대장 DW-547).** Story 1.3(2026-06) 시점엔 그게 옳았다 —
// 그때는 비로그인 사용자가 볼 수 있는 화면이 하나도 없어서 로그아웃 후 갈 곳이 로그인 화면뿐이었다.
// 그 전제를 **FR58(비로그인 열람 허용, Story 8.5)이 뒤집었는데** 이 한 줄이 함께 갱신되지 않았다.
// FR58 규칙은 "비로그인도 랜딩·탐색·상세를 열람할 수 있고, 로그인 게이트는 **행동**(문의·등록·찜)
// 에만 건다"이므로, 로그아웃한 사용자의 목적지는 아무것도 못 보는 화면이 아니라 공개 랜딩이다.
// (UX 문서엔 "로그아웃 후 목적지"를 정한 문장이 애초에 없어 어긋남이 오래 안 보였다 — 사용자 지적으로 발견.)
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import Button from '@/components/ui/Button';

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
      router.push('/');
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
      <Button
        type="button"
        variant="secondary"
        onClick={handleLogout}
        loading={loading}
        loadingText="처리 중…"
      >
        로그아웃
      </Button>
      {error && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {error}
        </p>
      )}
    </div>
  );
}
