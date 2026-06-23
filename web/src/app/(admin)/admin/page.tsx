// 관리자 영역 홈 — 운영 기능 진입 허브.
// 접근 제어는 상위 (admin)/layout.tsx의 requireRole(admin)이 담당하므로 이 화면엔 인증 로직이 없다.
// 회원 관리(6-2)는 구현 완료 → 진입 링크 노출. 매물/거래내역/채팅 관리는 6-3~6-5에서 추가된다.
import Link from 'next/link';
import { buttonClasses } from '@/components/ui/Button';

export default function AdminHomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">관리자 영역</h1>
        <p className="text-sm text-zinc-500">운영 기능을 선택하세요.</p>
      </div>

      <nav className="flex flex-col gap-3">
        {/* 회원 관리(FR22) — 전체 회원 조회 + 정지/삭제 */}
        <Link href="/admin/members" className={buttonClasses({ variant: 'primary' })}>
          회원 관리
        </Link>
      </nav>

      <p className="text-xs text-zinc-400">
        매물·거래내역·채팅 관리는 추후 제공됩니다.
      </p>
    </main>
  );
}
