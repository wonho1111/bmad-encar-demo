'use client';

// 로그인 화면 (FR2) — 이메일·비밀번호로 로그인한다.
// 성공하면 Supabase 세션 쿠키가 생기고, FR58(8.5)부터는 원래 가려던 경로(redirectedFrom)로 복귀한다
// (없으면 홈으로). 회원가입은 Story 1.2(/signup), 로그아웃은 같은 1.3의 LogoutButton에서 다룬다.
// middleware 라우트 가드·역할별 화면 분기는 Story 1.4 범위라 여기서는 다루지 않는다.
import { Suspense, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
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
  const router = useRouter();
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

      // 성공 → 원래 가려던 경로(redirectedFrom)로 복귀, 없으면 홈. router.refresh()로 서버
      // 컴포넌트가 새 세션 쿠키를 다시 읽게 한다.
      router.push(resolveSafeRedirect(searchParams.get('redirectedFrom')));
      router.refresh();
    } catch (err) {
      setError(`네트워크 오류가 발생했습니다: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">로그인</h1>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">이메일</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="email"
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
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
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>

        {error && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}

        <Button type="submit" variant="primary" loading={loading} loadingText="처리 중…">
          로그인
        </Button>
      </form>

      <p className="text-sm text-zinc-500">
        아직 계정이 없으신가요?{' '}
        <Link href="/signup" className="font-medium text-zinc-900 underline dark:text-zinc-100">
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
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6" aria-busy="true">
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
