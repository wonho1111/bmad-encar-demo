// 공용 상단바 — 로그인 상태에서 서비스명(홈 링크)·역할·이메일(좌)과 로그아웃(우)을 한 줄에 둔다.
// 홈(구매자/판매자)과 관리자 영역이 같은 상단바를 쓰게 해 UI 일관성을 맞추고,
// 화면 중앙은 콘텐츠(매물 탐색/등록·관리 기능) 자리로 비워둔다.
// "중고차 직거래" 제목을 홈(/)으로 가는 링크로 두어, 모든 화면에서 공통 홈 버튼 역할을 한다
//   (검색·상세를 오가다 한 번에 홈으로 돌아갈 진입점이 없던 문제 해소).
// 서버/클라이언트 어디서든 쓰는 표현용 컴포넌트(상태 없음). 로그아웃 동작만 클라이언트 컴포넌트에 위임.
import Link from 'next/link';
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
      <div className="flex items-baseline gap-3 text-sm">
        {/* 서비스명 = 홈(/) 링크. 어느 화면에서든 클릭하면 홈으로 돌아간다(공통 홈 버튼). */}
        <Link href="/" className="font-semibold hover:underline">
          중고차 직거래
        </Link>
        {roleLabel && <span className="font-medium text-zinc-500">{roleLabel}</span>}
        {email && <span className="text-zinc-500">{email}</span>}
      </div>
      <LogoutButton />
    </header>
  );
}
