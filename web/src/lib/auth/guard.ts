// 서버 컴포넌트/레이아웃용 접근 제어 헬퍼 (FR3).
// proxy(루트 라우트 가드)가 "로그인 여부"를 빠르게 거른다면, 여기서는 데이터에 가까운 곳에서
// 실제 인가(역할 확인)를 집행한다 — Next.js 권장 이중 방어. Epic 2/3/6이 재사용할 단일 출처.
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import type { UserRole } from '@/lib/constants';

// 로그인 필수 — 비로그인 시 /login으로 보낸다. 반환: 로그인 사용자(이후 코드에서 non-null 보장).
export async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect('/login'); // redirect()는 throw하므로 이 아래로 진행되지 않는다.
  }
  return user;
}

// 특정 역할 필수 — 비로그인은 /login, 역할 불일치는 홈(/)으로 보낸다.
// 본인 역할은 profiles_select_self RLS로 읽는다(0001_profiles에 이미 존재, 새 정책 불필요).
export async function requireRole(role: UserRole) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect('/login');
  }

  const { data: profile } = await supabase
    .from('profiles')
    .select('role')
    .eq('id', user.id)
    .single();

  if (profile?.role !== role) {
    redirect('/'); // 권한 없음 → 홈으로(권한 밖 화면 노출 차단).
  }
  return user;
}
