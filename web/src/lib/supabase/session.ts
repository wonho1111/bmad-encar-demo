// proxy(web/src/proxy.ts) 전용 Supabase 세션 갱신 헬퍼.
// 매 요청마다 만료된 액세스 토큰을 갱신하고, 갱신된 쿠키를 응답에 실어 보낸다.
// (Story 1.3까지는 이 갱신이 없어 "서버측 세션 자동 갱신 미동작" 한계가 있었다 → 본 헬퍼로 해소.)
//
// ⚠️ Next.js 16에서 middleware는 proxy로 개명됐고, proxy는 기본 Node.js 런타임이라
//    @supabase/ssr가 그대로 동작한다(옛 Edge 런타임 제약 없음).
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';
import { getSupabaseEnv } from './env';

export async function updateSession(request: NextRequest) {
  // 기본 응답 — 이후 토큰 갱신이 일어나면 새 응답으로 교체하며 쿠키를 옮겨 담는다.
  let response = NextResponse.next({ request });

  const { url, anonKey } = getSupabaseEnv();

  const supabase = createServerClient(url, anonKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        // 요청·응답 쿠키 양쪽에 기록한다. 한쪽이라도 빠지면 갱신된 토큰이 유실돼
        // "사용자가 무작위로 로그아웃되는" 버그가 난다(Supabase 공식 SSR 패턴).
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
      },
    },
  });

  // ⚠️ createServerClient와 getUser() 사이에 다른 로직을 넣지 말 것(공식 경고).
  //    getUser는 쿠키를 맹신하지 않고 Auth 서버에 재검증한다(getSession 대신 사용).
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return { response, user };
}
