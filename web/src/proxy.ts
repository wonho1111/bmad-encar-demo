// 루트 라우트 가드 (FR3) — 요청이 화면에 닿기 전에 서버에서 먼저 실행된다.
//
// ⚠️ Next.js 16 주의: 예전의 `middleware.ts`는 deprecated이고 `proxy.ts`로 개명됐다.
//    함수명도 middleware → proxy. 단일 파일만 지원한다.
//    (에픽/아키텍처 문서엔 'middleware'로 적혀 있으나 실제 파일명은 proxy.ts다.)
//
// 역할:
//   1) 매 요청 세션 갱신(만료 토큰 자동 갱신) — updateSession()
//   2) 비로그인 사용자가 보호 경로에 접근하면 /login으로 리다이렉트(optimistic 체크)
// 관리자 "역할" 판정은 여기서 DB를 조회하지 않고, (admin)/layout.tsx의 서버 컴포넌트가
// 담당한다(Next.js 권장: proxy는 빠른 쿠키 체크만, 실제 인가는 데이터에 가까운 곳에서).
import { NextResponse, type NextRequest } from 'next/server';
import { updateSession } from '@/lib/supabase/session';

// 로그인이 필요한 보호 경로 접두사. 후행 에픽에서 추가 예정: '/chat'(문의 채팅).
// '/sell'(판매자 매물 등록·관리, Story 2-2~) — 비로그인 1차 차단. 역할(seller) 2차 집행은 (user)/sell 레이아웃의 requireRole.
// '/search'(구매자 매물 탐색, Story 3-1) — 로그인 사용자(구매자·판매자 공통)만. 역할 게이트 없음(on_sale은 RLS상 모두 공개).
const PROTECTED_PREFIXES = ['/admin', '/sell', '/search'];

function redirectToLogin(request: NextRequest, pathname: string) {
  const url = request.nextUrl.clone();
  url.pathname = '/login';
  // 로그인 후 원래 가려던 곳으로 돌아갈 수 있게 출발 경로를 동봉한다.
  url.searchParams.set('redirectedFrom', pathname);
  return NextResponse.redirect(url);
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 정확 일치 또는 하위 경로만 보호('/administrator' 같은 우연 일치 방지).
  // try 바깥에서 계산해, 세션 갱신이 실패해도 보호 여부를 판단할 수 있게 한다.
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );

  try {
    const { response, user } = await updateSession(request);

    if (isProtected && !user) {
      return redirectToLogin(request, pathname);
    }

    return response;
  } catch (e) {
    // env 누락 등으로 세션 갱신이 불가능한 경우.
    // 원인을 로그로 남기되, 보호 경로는 fail-closed로 막는다 — 인증을 확인할 수 없으면
    // 통과(fail-open)시키지 않고 /login으로 보낸다(보안 원칙). 공개 경로만 통과시킨다.
    console.error('[proxy] 세션 갱신 실패 — Supabase 환경변수(web/.env.local)를 확인하세요:', e);
    if (isProtected) {
      return redirectToLogin(request, pathname);
    }
    return NextResponse.next();
  }
}

export const config = {
  // 정적 자원·이미지·favicon은 제외한다(인증 로직이 CSS/JS/이미지 로딩을 막지 않게).
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
