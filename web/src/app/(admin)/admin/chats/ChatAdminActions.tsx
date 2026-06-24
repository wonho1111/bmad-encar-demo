'use client';

// 관리자 채팅방 행의 액션 버튼 (FR25) — 삭제만 제공.
//
// 설계(본보기: (admin)/admin/listings/ListingAdminActions.tsx):
//   · 삭제: window.confirm 후 chat_rooms 행 DELETE(RLS chat_rooms_delete_admin, 0005).
//       - createClient()(browser, anon-key) 사용 — service_role 키는 클라이언트에 두지 않는다.
//       - .select('id')로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행 → 한국어 거부.
//       - 성공 시 router.refresh()로 목록에서 즉시 제거 반영.
//   · ⚠️ 방만 지운다 — 그 방의 메시지(chat_messages)는 0003의 on delete cascade가 DB에서 자동 정리한다.
//       (클라에서 메시지를 따로 삭제하지 않는다 → "방과 메시지가 제거된다"(FR25)는 DB가 보장.)
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어 일반 안내.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import Button from '@/components/ui/Button';

type Props = {
  roomId: string;
  label: string; // 확인 메시지에 보여줄 방 요약(예: "[현대] 아반떼 CN7 · 2020년 · 1,500만원")
};

export default function ChatAdminActions({ roomId, label }: Props) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    if (deleting) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(삭제 실수 방지).
    const ok = window.confirm(
      `'${label}' 채팅방을 삭제할까요? 방과 대화 내용이 모두 제거되며 되돌릴 수 없습니다.`,
    );
    if (!ok) return;

    setError(null);
    setDeleting(true);
    try {
      const supabase = createClient();
      // .select()로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      //   방을 지우면 그 방의 메시지는 chat_messages.room_id on delete cascade(0003)로 함께 제거된다.
      const { data: deleted, error: deleteError } = await supabase
        .from('chat_rooms')
        .delete()
        .eq('id', roomId)
        .select('id');

      if (deleteError) {
        console.error('[admin/chats] chat_rooms delete 실패:', deleteError);
        setError('채팅방 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!deleted || deleted.length === 0) {
        // 0행: 관리자 권한이 없거나(RLS 차단) 방이 그새 삭제됨.
        setError('채팅방을 삭제할 수 없습니다. (권한이 없거나 방을 찾을 수 없습니다.)');
        return;
      }
      router.refresh();
    } catch (err) {
      console.error('[admin/chats] chat_rooms delete 예외:', err);
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
