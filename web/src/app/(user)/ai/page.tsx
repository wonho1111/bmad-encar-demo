// AI 검색 화면 (FR12·Story 4-7) — 서버 컴포넌트.
//
// 동작:
//   1) 로그인 사용자(구매자·판매자 공통)의 역할 라벨을 조회해 공용 상단바(AppHeader)에 넘긴다(search/page.tsx 패턴 재사용).
//   2) 본문에 AI 채팅 컴포넌트(ChatAssistant, 클라이언트)를 배치 — 실제 대화·API 호출은 거기서 한다.
//
// 보호: proxy가 /ai 비로그인 1차 차단(PROTECTED_PREFIXES). 별도 역할 게이트 없음(로그인 사용자 공통).
//
// 무상태(FR18): 대화 맥락은 ChatAssistant의 클라이언트 상태에만 존재한다 — 서버는 대화를 저장하지 않으며
//   이 페이지는 매번 빈 화면으로 시작한다(새로고침=초기화). AI 검색은 매 요청 최신이라 정적화하지 않는다.
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';
import ChatAssistant from '@/components/ai/ChatAssistant';

// AI 검색은 인증 쿠키 기반 동적 화면이라 정적 캐시로 굳지 않게 한다(search/listings와 동일 정책).
export const dynamic = 'force-dynamic';

export default async function AiSearchPage() {
  const supabase = await createClient();

  // 상단바용 역할 라벨(홈·검색 페이지와 동일 패턴 — profiles_select_self RLS로 본인 행 읽기).
  const {
    data: { user },
  } = await supabase.auth.getUser();
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
    <>
      <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} currentPath="/ai" />
      <main className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
        <section className="flex flex-col gap-1">
          <h1 className="text-2xl font-semibold">AI 검색</h1>
          <p className="text-sm text-zinc-500">
            원하는 차를 자연어로 물어보세요. 이어서 후속 질문(예: &ldquo;그 중 더 싼 거&rdquo;)도 가능합니다.
          </p>
        </section>

        {/* 대화·API 호출·멀티턴 맥락 보관은 모두 클라이언트 컴포넌트가 담당. */}
        <ChatAssistant />
      </main>
    </>
  );
}
