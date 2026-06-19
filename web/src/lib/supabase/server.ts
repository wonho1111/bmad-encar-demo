// 서버 컴포넌트 / 서버 액션 / 라우트 핸들러용 Supabase 클라이언트.
// Next.js의 쿠키 저장소와 연동해 세션을 읽고 갱신한다(SSR 인증).
// Next.js 16에서 cookies()는 비동기이므로 await로 받는다 → 이 함수도 async.
import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';
import { getSupabaseEnv } from './env';

export async function createClient() {
  const cookieStore = await cookies();
  // env 누락 시 어떤 변수가 비었는지 한국어로 알려주는 가드(불투명 throw 방지).
  const { url, anonKey } = getSupabaseEnv();

  return createServerClient(
    url,
    anonKey,
    {
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet) {
          // 서버 컴포넌트에서 호출되면 set이 불가능할 수 있다(읽기 전용 컨텍스트).
          // proxy(web/src/proxy.ts)가 세션 갱신을 담당하므로 여기서 set이 무시돼도 안전하다.
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
