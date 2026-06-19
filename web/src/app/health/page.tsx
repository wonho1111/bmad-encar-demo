// 연결 점검용 임시 라우트 (Story 1.1 AC2 입증).
// 환경변수 유무를 확인하고, 값이 있으면 Supabase에 실제 네트워크 요청을 보내 도달 가능성을 검증한다.
//
// ⚠️ 연결 점검은 GoTrue health 엔드포인트(/auth/v1/health)로 한다.
//    - getSession()은 세션 쿠키가 없으면 네트워크를 타지 않아(로컬 반환) 서버가 죽어도 "성공"으로 보일 수 있다(코드 리뷰 지적).
//    - getUser()도 세션이 없으면 단축 반환할 수 있다.
//    - /auth/v1/health는 인증 상태와 무관하게 항상 네트워크를 타며, 테이블도 필요 없다(스키마 독립).
//      → 200: 도달 성공 / 401: 키 문제 / fetch throw: URL·네트워크 문제
//
// 또한 서버 Supabase 클라이언트를 실제로 생성·호출해 server.ts 배선이 동작함을 함께 확인한다.
// 검증이 끝나면 이 라우트는 제거해도 된다.
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic'; // 매 요청마다 실제 연결 상태를 확인

export default async function HealthPage() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  const configured = Boolean(url && anonKey);

  let connection: string;
  let authState = '확인 안 함';

  if (!configured) {
    connection = '환경변수 미설정 — web/.env.local에 Supabase URL/anon key를 입력하세요.';
  } else {
    // 1) 실제 도달 점검 — GoTrue health (항상 네트워크 요청)
    try {
      const res = await fetch(`${url}/auth/v1/health`, {
        headers: { apikey: anonKey! },
        cache: 'no-store',
      });
      if (res.ok) {
        connection = '연결 성공 — Supabase에 도달했습니다.';
      } else if (res.status === 401) {
        connection = '도달했으나 인증 거부(401) — anon/publishable key를 확인하세요.';
      } else {
        connection = `도달했으나 예상 밖 응답: HTTP ${res.status}`;
      }
    } catch (e) {
      connection = `연결 실패(네트워크/URL) — ${e instanceof Error ? e.message : String(e)}`;
    }

    // 2) 서버 Supabase 클라이언트 배선 확인(server.ts 동작) — 로그인 상태는 부가 정보
    try {
      const supabase = await createClient();
      const { data } = await supabase.auth.getUser();
      authState = data.user ? `로그인됨(${data.user.id})` : '비로그인(정상)';
    } catch (e) {
      authState = `클라이언트 생성/호출 예외 — ${e instanceof Error ? e.message : String(e)}`;
    }
  }

  return (
    <main style={{ padding: 24, fontFamily: 'monospace' }}>
      <h1>Health Check</h1>
      <ul>
        <li>NEXT_PUBLIC_SUPABASE_URL: {url ? '설정됨' : '비어 있음'}</li>
        <li>NEXT_PUBLIC_SUPABASE_ANON_KEY: {anonKey ? '설정됨' : '비어 있음'}</li>
        <li>Supabase 연결: {connection}</li>
        <li>서버 클라이언트/인증 상태: {authState}</li>
      </ul>
    </main>
  );
}
