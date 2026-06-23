'use client';

// 관리자 회원 행의 액션 버튼 (FR22) — 정지/정지 해제 + 삭제.
//
// 설계(본보기: (user)/sell/ListingActions.tsx):
//   · 정지/해제: profiles.status를 active↔suspended로 토글.
//       - UPDATE payload는 { status }만 보낸다 → role 등 다른 필드 위조·부수변경 차단.
//       - RLS(profiles_update_admin, 0005)가 "관리자만" 타인 행 수정을 허용한다(with check=is_admin()).
//         관리자가 아니면(혹은 권한 상실) 0행이 돼 아래에서 한국어로 거부한다.
//       - 성공 시 router.refresh()로 목록(배지·라벨)을 즉시 갱신.
//   · 삭제: window.confirm 후 profiles 행 DELETE(RLS profiles_delete_admin).
//       - ⚠️ profiles 행 삭제 = "프로필(역할·상태) 제거"까지다. 로그인 계정 자체(auth.users)는
//         service-role/admin API가 있어야 지울 수 있어(키 미설정) 본 스토리 범위 밖이다.
//       - 0행이면 한국어 거부, 성공 시 router.refresh().
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어 일반 안내.
//   · 본인 행에는 이 컴포넌트를 아예 렌더하지 않는다(page에서 isSelf로 제어) → 자기 정지/삭제 사고 방지.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { PROFILE_STATUS, type ProfileStatus } from '@/lib/constants';
import Button from '@/components/ui/Button';

type Props = {
  memberId: string;
  status: ProfileStatus; // 현재 상태 — 버튼 라벨(정지/해제)을 결정한다.
  label: string; // 확인 메시지에 보여줄 회원 요약(예: "구매자 1a2b…")
};

export default function MemberActions({ memberId, status, label }: Props) {
  const router = useRouter();
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isSuspended = status === PROFILE_STATUS.SUSPENDED;
  // 다음으로 바꿀 상태 — 지금 정지면 active로 풀고, 활성이면 suspended로 정지.
  const nextStatus: ProfileStatus = isSuspended
    ? PROFILE_STATUS.ACTIVE
    : PROFILE_STATUS.SUSPENDED;

  async function handleToggle() {
    if (toggling) return; // 중복 클릭 차단
    setError(null);
    setToggling(true);
    try {
      const supabase = createClient();
      // payload는 status만 → 다른 필드 위조·부수변경 차단.
      // .select()로 바뀐 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      const { data: updated, error: updateError } = await supabase
        .from('profiles')
        .update({ status: nextStatus })
        .eq('id', memberId)
        .select('id');

      if (updateError) {
        console.error('[admin/members] profiles status UPDATE 실패:', updateError);
        setError('상태 변경 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!updated || updated.length === 0) {
        // 0행: 관리자 권한이 없거나(RLS 차단) 회원이 그새 삭제됨.
        setError('회원 상태를 변경할 수 없습니다. (권한이 없거나 회원을 찾을 수 없습니다.)');
        return;
      }
      router.refresh();
    } catch (err) {
      console.error('[admin/members] profiles status 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setToggling(false);
    }
  }

  async function handleDelete() {
    if (deleting) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(삭제 실수 방지).
    const ok = window.confirm(
      `'${label}' 회원을 삭제할까요? 프로필(역할·상태)이 제거되며 되돌릴 수 없습니다.`,
    );
    if (!ok) return;

    setError(null);
    setDeleting(true);
    try {
      const supabase = createClient();
      // .select()로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      const { data: deleted, error: deleteError } = await supabase
        .from('profiles')
        .delete()
        .eq('id', memberId)
        .select('id');

      if (deleteError) {
        console.error('[admin/members] profiles delete 실패:', deleteError);
        setError('회원 삭제 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!deleted || deleted.length === 0) {
        setError('회원을 삭제할 수 없습니다. (권한이 없거나 회원을 찾을 수 없습니다.)');
        return;
      }
      router.refresh();
    } catch (err) {
      console.error('[admin/members] profiles delete 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {/* 정지면 "정지 해제"(info), 활성이면 "정지"(secondary) */}
        <Button
          type="button"
          variant={isSuspended ? 'info' : 'secondary'}
          size="sm"
          onClick={handleToggle}
          loading={toggling}
          loadingText="처리 중…"
        >
          {isSuspended ? '정지 해제' : '정지'}
        </Button>
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
      </div>
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
