// 서버 컴포넌트 / 서버 액션 / 라우트 핸들러용 Supabase 클라이언트.
// Next.js의 쿠키 저장소와 연동해 세션을 읽고 갱신한다(SSR 인증).
// Next.js 16에서 cookies()는 비동기이므로 await로 받는다 → 이 함수도 async.
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

export async function createClient() {
  const cookieStore = await cookies();

  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          // 서버 컴포넌트에서 호출되면 set이 불가능할 수 있다(읽기 전용 컨텍스트).
          // 미들웨어가 세션 갱신을 담당하므로 여기서는 무시해도 안전하다(후속 스토리에서 middleware 추가).
          try {
            cookiesToSet.forEach(({ name, value, options }) =>
              cookieStore.set(name, value, options),
            );
          } catch {
            // Server Component에서 set 호출 시 발생 — 무시.
          }
        },
      },
    },
  );
}
