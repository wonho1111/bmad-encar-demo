'use client';

// 관리자 매물 행의 액션 버튼 (FR23) — 삭제만 제공.
//
// 설계(본보기: (admin)/admin/members/MemberActions.tsx · (user)/sell/ListingActions.tsx):
//   · 삭제: window.confirm 후 listings 행 DELETE(RLS listings_delete_admin, 0005).
//       - createClient()(browser, anon-key) 사용 — service_role 키는 클라이언트에 두지 않는다.
//       - .select('id')로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행 → 한국어 거부.
//       - 성공 시 router.refresh()로 목록에서 즉시 제거 반영.
//   · 정지/수정 같은 부가 액션은 없다(FR23은 "부적절 매물 삭제"가 관리 동작 — 범위 컷).
//   · 매물의 seller_id는 profiles(id) on delete cascade이나 방향이 반대 → 매물을 지워도 판매자/계정은 그대로(매물만 제거).
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어 일반 안내.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { deleteListingPhotoObjects } from '@/app/(user)/sell/photo-sync';
import Button from '@/components/ui/Button';

type Props = {
  listingId: string;
  label: string; // 확인 메시지에 보여줄 매물 요약(예: "[현대] 아반떼 CN7")
  // 삭제 성공 후 이동할 경로(선택). 상세 페이지에서 삭제하면 그 매물이 사라져 머무를 곳이 없으므로
  //   목록('/admin/listings')으로 보낸다. 목록 화면에선 생략 → 기존대로 router.refresh()로 행만 제거.
  redirectTo?: string;
};

export default function ListingAdminActions({ listingId, label, redirectTo }: Props) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    if (deleting) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(삭제 실수 방지).
    const ok = window.confirm(
      `'${label}' 매물을 삭제할까요? 삭제하면 되돌릴 수 없습니다.`,
    );
    if (!ok) return;

    setError(null);
    setDeleting(true);
    try {
      // ⚠️ 매물보다 사진 파일을 먼저 지운다 — 판매자 삭제 경로((user)/sell/ListingActions.tsx)와 같은 계약.
      //   매물을 먼저 지우면 listing_images 행이 cascade로 사라지고, 남은 Storage 오브젝트는
      //   아무도 참조하지 않는 고아가 된다(docs/tech-debt.md #46).
      //   정리에 실패하면 매물 삭제를 하지 않는다 — "앞 단계가 성공했을 때만 다음 단계"(conventions §10.1).
      // 판매자 경로의 함수를 그대로 쓴다(로직 이원화 금지) — 정리 규칙이 두 벌이 되면 한쪽만 늙는다.
      const cleanup = await deleteListingPhotoObjects(listingId);
      if (!cleanup.ok) {
        setError('사진 파일을 정리하지 못해 매물을 삭제하지 않았습니다. 잠시 후 다시 시도해주세요.');
        return;
      }

      const supabase = createClient();
      // .select()로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      const { data: deleted, error: deleteError } = await supabase
        .from('listings')
        .delete()
        .eq('id', listingId)
        .select('id');

      if (deleteError) {
        console.error('[admin/listings] listings delete 실패:', deleteError);
        setError('매물 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!deleted || deleted.length === 0) {
        // 0행: 관리자 권한이 없거나(RLS 차단) 매물이 그새 삭제됨.
        setError('매물을 삭제할 수 없습니다. (권한이 없거나 매물을 찾을 수 없습니다.)');
        return;
      }
      // 상세에서 삭제했으면(목록으로 이동) 그 매물 페이지는 더 이상 유효하지 않다 → push.
      //   목록에서 삭제했으면 redirectTo 없음 → refresh로 그 행만 제거.
      if (redirectTo) {
        router.push(redirectTo);
      } else {
        router.refresh();
      }
    } catch (err) {
      console.error('[admin/listings] listings delete 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button
        type="button"
        variant="danger"
        size="sm"
        onClick={handleDelete}
        loading={deleting}
        loadingText="삭제 중…"
      >
        삭제
      </Button>
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
