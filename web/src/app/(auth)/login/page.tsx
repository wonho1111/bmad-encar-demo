'use client';

// 로그인 화면 (FR2) — 이메일·비밀번호로 로그인한다.
// 성공하면 Supabase 세션 쿠키가 생기고 홈(/)으로 이동한다.
// 회원가입은 Story 1.2(/signup), 로그아웃은 같은 1.3의 LogoutButton에서 다룬다.
// middleware 라우트 가드·역할별 화면 분기는 Story 1.4 범위라 여기서는 다루지 않는다.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import Button from '@/components/ui/Button';

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

export default function LoginPage() {
  const router = useRouter();
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

      // 성공 → 홈으로 이동. router.refresh()로 서버 컴포넌트(홈)가 새 세션 쿠키를 다시 읽게 한다.
      router.push('/');
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
