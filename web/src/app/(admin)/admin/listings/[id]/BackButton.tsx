'use client';

// 관리자 매물 상세의 "돌아가기" 버튼.
//
// 왜 만들었나(검토 결정, 2026-06-24 party-mode):
//   기존엔 backLink가 항상 '/admin/listings'(매물 관리)로 고정돼 있어서,
//   거래 내역·채팅 관리에서 상세로 들어와도 무조건 '매물 관리'로 튕겼다.
//   사용자 기대는 "들어온 그 화면으로 복귀"(브라우저 뒤로가기처럼)다.
//
// 동작: 앱 내에서 이동해 온 경우(이전 히스토리 있음) → 그 페이지로 뒤로가기.
//       새 탭·북마크·새로고침 등으로 히스토리가 없으면 → 폴백 경로(fallbackHref)로.
//   router.back()만 쓰면 히스토리가 없을 때 앱 밖으로 튀므로 폴백을 둔다(Amelia 권고).
//   진입 출처를 쿼리파라미터(?from=)로 넘기지 않는다 — 모든 진입점에 파라미터를 심을 필요가 없어 단순.
import { useRouter } from 'next/navigation';

export default function BackButton({
  fallbackHref,
  children,
}: {
  fallbackHref: string;
  children: React.ReactNode;
}) {
  const router = useRouter();

  function handleBack() {
    // history.length > 1 = 이 탭에서 앞서 다른 페이지를 거쳐 왔다는 뜻(앱 내 이동).
    //   1 이하면 직접 진입(새 탭·북마크)이라 돌아갈 곳이 없으므로 폴백으로 보낸다.
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
    } else {
      router.replace(fallbackHref);
    }
  }

  return (
    <button
      type="button"
      onClick={handleBack}
      className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
    >
      {children}
    </button>
  );
}
