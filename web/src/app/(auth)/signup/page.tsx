'use client';

// 회원가입 화면 (FR1) — 이메일·비밀번호 + 역할(구매자/판매자) 선택.
// 제출하면 Supabase Auth 계정이 생기고, DB 트리거(handle_new_user)가 profiles 행을
// role·status='active'로 함께 만든다. 역할은 options.data.role로 전달되어 트리거가 읽는다.
// 로그인/로그아웃은 Story 1.3 범위라 여기서는 다루지 않는다.
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { USER_ROLE, type UserRole } from '@/lib/constants';

// 가입 경로에서 고를 수 있는 역할은 구매자/판매자뿐(admin 제외 — 서버 트리거도 admin을 차단).
const SIGNUP_ROLES: { value: UserRole; label: string }[] = [
  { value: USER_ROLE.BUYER, label: '구매자' },
  { value: USER_ROLE.SELLER, label: '판매자' },
];

// Supabase 인증 에러를 사용자용 한국어 메시지로 변환한다(내부 코드는 로그로만).
function toKoreanError(message: string, status?: number): string {
  const m = message.toLowerCase();
  if (m.includes('already registered') || m.includes('already been registered') || status === 422) {
    return '이미 가입된 이메일입니다. 다른 이메일을 사용하거나 로그인해주세요.';
  }
  if (m.includes('password') && (m.includes('at least') || m.includes('should be'))) {
    return '비밀번호는 6자 이상이어야 합니다.';
  }
  if (m.includes('invalid') && m.includes('email')) {
    return '유효한 이메일 주소를 입력해주세요.';
  }
  if (m.includes('unable to validate email address')) {
    return '유효한 이메일 주소를 입력해주세요.';
  }
  return `가입 중 오류가 발생했습니다: ${message}`;
}

export default function SignupPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<UserRole>(USER_ROLE.BUYER);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      const supabase = createClient();
      const { data, error: signUpError } = await supabase.auth.signUp({
        email,
        password,
        options: { data: { role } }, // → auth.users.raw_user_meta_data.role (트리거가 읽음)
      });

      if (signUpError) {
        setError(toKoreanError(signUpError.message, signUpError.status));
        return;
      }

      // 이메일 확인(Confirm email)이 켜져 있으면 중복 이메일이 에러 없이
      // identities: [] 빈 배열로 돌아온다(이메일 열거 방지). 이를 중복으로 해석한다.
      if (data.user && data.user.identities && data.user.identities.length === 0) {
        setError('이미 가입된 이메일입니다. 다른 이메일을 사용하거나 로그인해주세요.');
        return;
      }

      if (data.session) {
        // 이메일 확인 비활성 → 가입 즉시 세션 생성(로그인됨). 로그인 흐름은 Story 1.3.
        setSuccess('가입이 완료되었습니다.');
      } else {
        // 이메일 확인 활성 → 확인 메일 발송, 세션은 확인 후 생성.
        setSuccess('가입 신청이 완료되었습니다. 이메일을 확인해 인증을 완료해주세요.');
      }
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
          <p role="status" className="rounded bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
            {success}
          </p>
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
