// 관리자 영역 홈 — 운영 기능 진입 허브.
// 접근 제어는 상위 (admin)/layout.tsx의 requireRole(admin)이 담당하므로 이 화면엔 인증 로직이 없다.
// 회원 관리(6-2)·매물 관리(6-3)·거래 내역(6-4)·채팅 관리(6-5) 전부 구현 완료 → 진입 링크 노출.
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
        {/* 매물 관리(FR23) — 판매완료 포함 전체 매물 조회 + 삭제 */}
        <Link href="/admin/listings" className={buttonClasses({ variant: 'primary' })}>
          매물 관리
        </Link>
        {/* 거래 내역(FR24) — 판매완료(sold) 매물 조회 전용 */}
        <Link href="/admin/transactions" className={buttonClasses({ variant: 'primary' })}>
          거래 내역
        </Link>
        {/* 채팅 관리(FR25) — 전체 채팅방 조회 + 대화 열람 + 방 삭제 */}
        <Link href="/admin/chats" className={buttonClasses({ variant: 'primary' })}>
          채팅 관리
        </Link>
      </nav>
    </main>
  );
}
