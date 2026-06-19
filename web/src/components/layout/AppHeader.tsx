// 공용 상단바 — 로그인 상태에서 역할·이메일(좌)과 로그아웃(우)을 한 줄에 둔다.
// 홈(구매자/판매자)과 관리자 영역이 같은 상단바를 쓰게 해 UI 일관성을 맞추고,
// 화면 중앙은 콘텐츠(매물 탐색/등록·관리 기능) 자리로 비워둔다.
// 서버/클라이언트 어디서든 쓰는 표현용 컴포넌트(상태 없음). 로그아웃 동작만 클라이언트 컴포넌트에 위임.
import LogoutButton from '@/components/auth/LogoutButton';

export default function AppHeader({
  roleLabel,
  email,
}: {
  roleLabel?: string | null;
  email?: string | null;
}) {
  return (
    <header className="flex items-center justify-between border-b border-zinc-200 px-6 py-3 dark:border-zinc-800">
      <div className="flex items-baseline gap-2 text-sm">
        {roleLabel && <span className="font-medium">{roleLabel}</span>}
        {email && <span className="text-zinc-500">{email}</span>}
      </div>
      <LogoutButton />
    </header>
  );
}
