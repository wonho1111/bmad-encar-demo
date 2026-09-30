// OAuth(카카오) 로그인 콜백 라우트 (Story 18.1, AC1·AC3) — signInWithOAuth가 돌려보내는 지점.
//
// 흐름: 로그인 화면의 "카카오로 시작하기" → 카카오 동의 화면 → 여기(`/auth/callback?code=…`)로
// 복귀 → exchangeCodeForSession으로 code를 세션 쿠키로 바꿔치기 → 홈으로 이동.
// 실패(사용자가 동의 화면에서 취소했거나 code 교환 실패)하면 원본 provider 메시지는 절대
// 그대로 노출하지 않고 `/login?error=oauth`로 보낸다 — 실제 문구는 toKoreanOAuthError가 만든다.
import { NextResponse, type NextRequest } from 'next/server';
import { createClient } from '@/lib/supabase/server';

export async function GET(request: NextRequest) {
  const { searchParams, origin } = request.nextUrl;
  const code = searchParams.get('code');
  // 카카오 동의 화면 취소 등은 code 없이 error/error_description 쿼리로 돌아온다.
  const providerError = searchParams.get('error') ?? searchParams.get('error_description');

  if (!code || providerError) {
    return NextResponse.redirect(new URL('/login?error=oauth', origin));
  }

  const supabase = await createClient();
  const { error } = await supabase.auth.exchangeCodeForSession(code);
  if (error) {
    return NextResponse.redirect(new URL('/login?error=oauth', origin));
  }

  return NextResponse.redirect(new URL('/', origin));
}
