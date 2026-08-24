'use client';

// 로그인 화면 (FR2) — 이메일·비밀번호로 로그인한다.
// 성공하면 Supabase 세션 쿠키가 생기고, FR58(8.5)부터는 원래 가려던 경로(redirectedFrom)로 복귀한다
// (없으면 홈으로). 회원가입은 Story 1.2(/signup), 로그아웃은 같은 1.3의 LogoutButton에서 다룬다.
// middleware 라우트 가드·역할별 화면 분기는 Story 1.4 범위라 여기서는 다루지 않는다.
import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import Button from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
// 오픈 리다이렉트 방어는 @/lib/auth/redirect의 순수 함수가 담당한다(단위테스트로 고정 — 규칙12).
import { resolveSafeRedirect } from '@/lib/auth/redirect';

// Supabase 로그인 에러를 사용자용 한국어 메시지로 변환한다(원본 메시지/코드는 화면에 직접 노출하지 않음).
// 잘못된 자격은 보안상 "이메일/비밀번호 중 무엇이 틀렸는지" 구분하지 않고 동일 문구로 안내한다.
function toKoreanLoginError(err: { message: string; status?: number; code?: string }): string {
  const m = err.message.toLowerCase();
  if (err.code === 'invalid_credentials' || m.includes('invalid login credentials')) {
    return '이메일 또는 비밀번호가 올바르지 않습니다.';
  }
  if (err.code === 'email_not_confirmed' || m.includes('email not confirmed')) {
    return '이메일 인증이 완료되지 않았습니다. 받은 메일에서 인증을 완료해주세요.';
  }
  return '로그인 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}

function LoginForm() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (loading) return; // 진행 중 중복 제출 차단(빠른 연타/엔터 2회 방지)
    setError(null);

    // 제출 전 검증 — noValidate로 네이티브 검증을 끄므로 여기서 직접 막는다. 이메일은 앞뒤 공백 제거.
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError('이메일과 비밀번호를 입력해주세요.');
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email: trimmedEmail,
        password,
      });

      if (signInError) {
        setError(toKoreanLoginError(signInError));
        return;
      }

      // 에러 없이 세션이 비어 돌아오는 비정상 응답 → 거짓 성공 방지.
      if (!data.session) {
        setError('로그인 처리에 실패했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }

      // 성공 → 원래 가려던 경로(redirectedFrom)로 복귀, 없으면 홈.
      //
      // ⚠️ **router.push()가 아니라 전체 페이지 이동(location.assign)이다**(2026-08-13 사용자 지적 →
      //    운영 빌드로 재현). 예전 `router.push(target) + router.refresh()`는 이렇게 깨졌다:
      //      1) 비로그인 상태로 "내 차 팔기"(/sell)를 누른다 → proxy가 /login?redirectedFrom=%2Fsell로 보낸다.
      //      2) 이때 Next.js의 **클라이언트 라우터 캐시**에 "/sell = 로그인 화면"이라는 결과가 남는다.
      //      3) 그 화면에서 로그인에 성공해 router.push('/sell')을 하면, 라우터가 서버에 다시 묻지 않고
      //         2)의 캐시를 재생한다 → **로그인 화면이 그대로 다시 뜬다**(URL도 /login…에 머문다).
      //      4) 뒤로가기 후 다시 들어가면 캐시가 만료돼 정상 진입 — 사용자가 겪은 증상 그대로다.
      //    router.refresh()는 "지금 라우트"를 다시 받아올 뿐이라 이 재생을 막지 못했다(실측: 운영
      //    빌드 `next build && next start`에서 재현, dev 모드는 프리페치가 꺼져 있어 안 보인다).
      //    로그인은 **세션 쿠키가 바뀌는 순간**이라 이전 상태로 캐시된 화면은 전부 무효다 — 전체
      //    페이지 이동으로 라우터 캐시를 통째로 버리는 게 이 시점엔 오히려 정확하다.
      window.location.assign(resolveSafeRedirect(searchParams.get('redirectedFrom')));
    } catch (err) {
      setError(`네트워크 오류가 발생했습니다: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6">
      <h1 className="text-section font-bold text-ink-primary">로그인</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">이메일</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="rounded border border-border-hairline px-3 py-2 bg-surface-raised"
          />
        </label>

        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">비밀번호</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            className="rounded border border-border-hairline px-3 py-2 bg-surface-raised"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" loading={loading} loadingText="처리 중…">
          로그인
        </Button>
      </form>

      <p className="text-sm text-ink-muted">
        아직 계정이 없으신가요?{' '}
        <Link href="/signup" className="font-medium text-ink-primary underline">
          회원가입
        </Link>
      </p>
    </main>
  );
}

// useSearchParams를 쓰는 컴포넌트는 정적 프리렌더에서 빠지므로 Suspense 경계가 필요하다(Next.js 16).
// 그 말은 곧 **정적 HTML에 들어가는 건 아래 fallback**이라는 뜻이다 — fallback={null}로 두면
// JS가 붙기 전까지 로그인 페이지가 백지로 보인다(느린 회선·JS 실패 시 특히). 폼과 같은 골격의
// 스켈레톤을 놓아 그 사이를 메운다.
export default function LoginPage() {
  return (
    <Suspense fallback={<LoginFormSkeleton />}>
      <LoginForm />
    </Suspense>
  );
}

// LoginForm과 동일한 레이아웃(제목·입력 2개·버튼)의 자리표시자 — 하이드레이션 전후로 화면이
// 크게 튀지 않게 같은 간격·크기를 유지한다.
function LoginFormSkeleton() {
  return (
    <main className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center gap-6 p-6" aria-busy="true">
      <Skeleton className="h-8 w-24" />
      <div className="flex flex-col gap-4">
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-16 w-full" />
        <Skeleton className="h-10 w-full" />
      </div>
      <Skeleton className="h-5 w-48" />
    </main>
  );
}
