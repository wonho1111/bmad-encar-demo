'use client';

// 본인 매물 행의 관리 버튼 (FR6) — 수정 진입 링크 + 삭제 버튼.
//
// 설계:
//   · 수정: /sell/[id]/edit 로 이동(서버 컴포넌트가 본인 매물만 조회해 폼에 채움).
//   · 삭제: 실수 방지로 확인(window.confirm) 후 DELETE.
//       - RLS(listings_delete_own)가 타인 매물 삭제를 에러가 아니라 0행으로 막는다 → .select()로 0행이면 한국어 거부 안내(AC4).
//       - 성공 시 router.refresh()로 목록에서 즉시 제거 반영(AC3).
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어.
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

type Props = {
  listingId: string;
  label: string; // 확인 메시지에 보여줄 매물 요약(예: "[현대] 아반떼 CN7")
  canEdit?: boolean; // 판매중일 때만 수정 진입 노출(판매완료 매물 정보 변경 방지). 기본 true.
};

export default function ListingActions({ listingId, label, canEdit = true }: Props) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    if (deleting) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(AC3 실수 방지).
    const ok = window.confirm(`'${label}' 매물을 삭제할까요? 삭제하면 되돌릴 수 없습니다.`);
    if (!ok) return;

    setError(null);
    setDeleting(true);
    try {
      const supabase = createClient();
      // .select()로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      const { data: deleted, error: deleteError } = await supabase
        .from('listings')
        .delete()
        .eq('id', listingId)
        .select('id');

      if (deleteError) {
        console.error('[sell] listings delete 실패:', deleteError);
        setError('매물 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!deleted || deleted.length === 0) {
        // 본인 매물이 아니거나 이미 삭제됨(RLS 0행).
        setError('본인 매물만 삭제할 수 있습니다. (매물을 찾을 수 없거나 접근 권한이 없습니다.)');
        return;
      }

      // 성공 → 목록 갱신으로 즉시 제거 반영.
      router.refresh();
    } catch (err) {
      // 원본 에러는 콘솔에만(디버깅), 사용자에겐 한국어 일반 안내(원본 메시지 노출 금지 — 스토리 §AC4 규칙).
      console.error('[sell] listings delete 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {canEdit && (
          <Link
            href={`/sell/${listingId}/edit`}
            className="rounded border border-zinc-300 px-2 py-1 text-xs font-medium dark:border-zinc-700"
          >
            수정
          </Link>
        )}
        <button
          type="button"
          onClick={handleDelete}
          disabled={deleting}
          className="rounded border border-red-300 px-2 py-1 text-xs font-medium text-red-700 disabled:opacity-50 dark:border-red-800 dark:text-red-300"
        >
          {deleting ? '삭제 중…' : '삭제'}
        </button>
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
