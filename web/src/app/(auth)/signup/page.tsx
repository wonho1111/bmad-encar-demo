'use client';

// 회원가입 화면 (FR1) — 이메일·비밀번호 + 역할(구매자/판매자) 선택.
// 제출하면 Supabase Auth 계정이 생기고, DB 트리거(handle_new_user)가 profiles 행을
// role·status='active'로 함께 만든다. 역할은 options.data.role로 전달되어 트리거가 읽는다.
// 로그인/로그아웃은 Story 1.3 범위라 여기서는 다루지 않는다.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { createClient } from '@/lib/supabase/client';
import { USER_ROLE, type UserRole } from '@/lib/constants';

// 가입 경로에서 고를 수 있는 역할은 구매자/판매자뿐(admin 제외 — 서버 트리거도 admin을 차단).
const SIGNUP_ROLES: { value: UserRole; label: string }[] = [
  { value: USER_ROLE.BUYER, label: '구매자' },
  { value: USER_ROLE.SELLER, label: '판매자' },
];

// Supabase 인증 에러를 사용자용 한국어 메시지로 변환한다(원본 메시지/코드는 화면에 직접 노출하지 않음).
// 중복 판정은 status(422)가 아니라 에러 code/메시지로 좁힌다 — 422는 약한 비밀번호 등에도 쓰이기 때문.
function toKoreanError(err: { message: string; status?: number; code?: string }): string {
  const m = err.message.toLowerCase();
  if (err.code === 'user_already_exists' || m.includes('already registered') || m.includes('already been registered')) {
    return '이미 가입된 이메일입니다. 다른 이메일을 사용하거나 로그인해주세요.';
  }
  if (m.includes('password')) {
    return '비밀번호가 너무 짧거나 약합니다. 더 긴 비밀번호를 사용해주세요.';
  }
  if (m.includes('email')) {
    return '유효한 이메일 주소를 입력해주세요.';
  }
  return '가입 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}

export default function SignupPage() {
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(USER_ROLE.BUYER);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (loading) return; // 진행 중 중복 제출 차단(빠른 연타/엔터 2회 방지)
    setError(null);
    setSuccess(null);

    // 제출 전 검증 — noValidate로 네이티브 검증을 끄므로 여기서 직접 막는다. 이메일은 앞뒤 공백 제거.
    const trimmedEmail = email.trim();
    if (!trimmedEmail || !password) {
      setError('이메일과 비밀번호를 입력해주세요.');
      return;
    }
    if (password.length < 6) {
      setError('비밀번호는 6자 이상이어야 합니다.');
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const { data, error: signUpError } = await supabase.auth.signUp({
        email: trimmedEmail,
        password,
        options: { data: { role } }, // → auth.users.raw_user_meta_data.role (트리거가 읽음)
      });

      if (signUpError) {
        setError(toKoreanError(signUpError));
        return;
      }

      // signUp이 에러도 user도 없이 반환되는 비정상 응답 → 거짓 성공 방지.
      if (!data.user) {
        setError('가입 처리에 실패했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }

      // 이메일 확인(Confirm email)이 켜져 있으면 중복 이메일이 에러 없이
      // identities: [] 빈 배열로 돌아온다(이메일 열거 방지). 이를 중복으로 해석한다.
      if (data.user.identities && data.user.identities.length === 0) {
        setError('이미 가입된 이메일입니다. 다른 이메일을 사용하거나 로그인해주세요.');
        return;
      }

      if (data.session) {
        // 이메일 확인 비활성 → 가입 즉시 세션 생성(자동 로그인됨).
        // 곧바로 홈으로 이동해 로그인된 상태로 시작한다. replace로 뒤로가기 시 가입 폼이 다시 안 뜨게 한다.
        // refresh로 서버 컴포넌트(홈)가 새 세션 쿠키를 다시 읽게 한다.
        router.replace('/');
        router.refresh();
        return;
      }
      // 이메일 확인 활성 → 확인 메일 발송, 세션은 확인 후 생성. 화면 이동 없이 안내 + 로그인 링크.
      setSuccess('가입 신청이 완료되었습니다. 이메일을 확인해 인증을 완료한 뒤 로그인해주세요.');
    } catch (err) {
      setError(`네트워크 오류가 발생했습니다: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <h1 className="text-2xl font-semibold">회원가입</h1>

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
            minLength={6}
            autoComplete="new-password"
            className="rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900"
          />
        </label>

        <fieldset className="flex flex-col gap-2">
          <legend className="text-sm font-medium">역할 선택</legend>
          <div className="flex gap-4">
            {SIGNUP_ROLES.map((r) => (
              <label key={r.value} className="flex items-center gap-2">
                <input
                  type="radio"
                  name="role"
                  value={r.value}
                  checked={role === r.value}
                  onChange={() => setRole(r.value)}
                />
                <span>{r.label}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-zinc-500">
            역할은 가입 시 하나로 고정됩니다. 구매와 판매를 모두 하려면 계정을 2개 만들어주세요.
          </p>
        </fieldset>

        {error && (
          <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
            {error}
          </p>
        )}
        {success && (
          <div className="flex flex-col gap-2">
            <p role="status" className="rounded bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
              {success}
            </p>
            <Link href="/login" className="text-sm font-medium text-zinc-900 underline dark:text-zinc-100">
              로그인하러 가기
            </Link>
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          className="rounded bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
        >
          {loading ? '처리 중…' : '가입하기'}
        </button>
      </form>
    </main>
  );
}
