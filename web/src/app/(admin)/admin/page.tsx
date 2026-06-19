// 관리자 영역 홈(자리표시) — FR3 접근 제어가 동작함을 보이는 최소 화면.
// 실제 관리 기능(회원·매물·거래·채팅 관리)과 관리자 전권 RLS(0005_admin_policies)는 Epic 6에서 구현한다.
// 접근 제어는 상위 (admin)/layout.tsx의 requireRole(admin)이 담당하므로 이 화면엔 인증 로직이 없다.
export default function AdminHomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
      <h1 className="text-2xl font-semibold">관리자 영역</h1>
      <p className="text-sm text-zinc-500">
        관리 기능은 준비 중입니다. (회원·매물·거래내역·채팅 관리는 추후 제공됩니다.)
      </p>
    </main>
  );
}
