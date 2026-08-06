'use client';

// 관리자 매물 행의 액션 버튼 (FR23) — 삭제 + sold 매물 한정 "판매완료 되돌리기"(DW-391, Story 15.4).
//
// 설계(본보기: (admin)/admin/members/MemberActions.tsx · (user)/sell/ListingActions.tsx):
//   · 삭제: window.confirm 후 listings 행 DELETE(RLS listings_delete_admin, 0005).
//       - createClient()(browser, anon-key) 사용 — service_role 키는 클라이언트에 두지 않는다.
//       - .select('id')로 삭제된 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행 → 한국어 거부.
//       - 성공 시 router.refresh()로 목록에서 즉시 제거 반영.
//   · 되돌리기(sold 매물에만 렌더): admin_restore_sold_listing RPC 호출(0030) — status만
//       sold→on_sale로 되돌리는 좁은 SECURITY DEFINER RPC. MemberActions.tsx의 정지/해제와 동일한
//       모양: 실행 → RPC 호출 → .select 없이도 RPC 자체가 returning id라 데이터로 행 수를 본다 →
//       0행이면 한국어 오류 → 성공 시 router.refresh(). 확인 다이얼로그는 없다(삭제와 달리 되돌릴 수
//       있는 작업이고, MemberActions의 정지/해제 토글도 확인 없이 즉시 실행되는 것과 동일한 결).
//   · 삭제·되돌리기는 같은 행의 서로 다른 비동기 액션이라, 하나가 진행 중일 때 다른 하나를 누르면
//       레이스가 난다(코드리뷰 patch) — 그래서 두 버튼의 disabled는 자기 자신의 loading뿐 아니라
//       `busy`(deleting || restoring)도 함께 본다. loading prop은 그대로 각자 값을 써서 "처리 중…"
//       라벨은 실제로 실행 중인 버튼에만 뜬다.
//   · 정지 같은 부가 액션은 없다(FR23은 "부적절 매물 삭제"가 관리 동작 — 범위 컷).
//   · 매물의 seller_id는 profiles(id) on delete cascade이나 방향이 반대 → 매물을 지워도 판매자/계정은 그대로(매물만 제거).
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어 일반 안내.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { listListingPhotoPaths, deletePhotoObjectsByPaths } from '@/app/(user)/sell/photo-sync';
import { LISTING_STATUS, type ListingStatus } from '@/lib/constants';
import Button from '@/components/ui/Button';

type Props = {
  listingId: string;
  label: string; // 확인 메시지에 보여줄 매물 요약(예: "[현대] 아반떼 CN7")
  status: ListingStatus; // sold일 때만 "판매완료 되돌리기" 버튼을 렌더한다.
  // 삭제 성공 후 이동할 경로(선택). 상세 페이지에서 삭제하면 그 매물이 사라져 머무를 곳이 없으므로
  //   목록('/admin/listings')으로 보낸다. 목록 화면에선 생략 → 기존대로 router.refresh()로 행만 제거.
  redirectTo?: string;
};

export default function ListingAdminActions({ listingId, label, status, redirectTo }: Props) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [restoring, setRestoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRestore() {
    if (deleting || restoring) return; // 중복 클릭 + 삭제와의 레이스 차단
    setError(null);
    setRestoring(true);
    try {
      const supabase = createClient();
      // RPC 자체가 `returning id`라 .select() 없이도 data가 곧 바뀐 행 목록이다 — RLS/GRANT로
      // 막히거나(비관리자) 이미 on_sale이면 에러가 아니라 0행으로 온다(0030 설계).
      const { data, error: rpcError } = await supabase.rpc('admin_restore_sold_listing', {
        p_listing_id: listingId,
      });

      if (rpcError) {
        console.error('[admin/listings] admin_restore_sold_listing 실패:', rpcError);
        setError('되돌리기 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!data || data.length === 0) {
        // 0행: 이 버튼은 sold 매물에만 렌더되므로(관리자 화면), 실제 도달 경로는 대개 레이스다
        // (다른 관리자가 먼저 처리) — 그래서 그 경우를 먼저 안내하고, 드문 권한 상실은 괄호로 덧붙인다.
        setError('되돌릴 수 없습니다. 다른 관리자가 먼저 처리했을 수 있습니다. (또는 권한이 없거나 매물을 찾을 수 없습니다.)');
        return;
      }
      router.refresh();
    } catch (err) {
      console.error('[admin/listings] admin_restore_sold_listing 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setRestoring(false);
    }
  }

  async function handleDelete() {
    if (deleting || restoring) return; // 중복 클릭 + 되돌리기와의 레이스 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(삭제 실수 방지).
    const ok = window.confirm(
      `'${label}' 매물을 삭제할까요? 삭제하면 되돌릴 수 없습니다.`,
    );
    if (!ok) return;

    setError(null);
    setDeleting(true);
    try {
      // ⚠️ **경로는 매물을 지우기 전에 확보한다.** listing_images는 listings에 cascade로 매달려
      //    있어서, 매물을 먼저 지운 뒤 조회하면 0건이 나와 아무것도 못 지운다(코드리뷰 2026-07-19
      //    브라우저 실측 — 조용히 성공을 반환하며 고아가 100% 발생했다).
      const photos = await listListingPhotoPaths(listingId);

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

      // ⚠️ 매물 행을 먼저 지우고, 사진 파일 정리는 그다음이다(사용자 결정 2026-07-19, 옵션 a).
      //   전엔 "사진 먼저"였다 — 버킷이 비공개일 때는 행이 사라지면 Storage 읽기 정책이 그 행과
      //   조인해 참이 됐으므로, 행 없는 파일은 소유자도 못 지우는 영구 고아였다. 지금은
      //   0014에서 버킷이 공개로 바뀌고 Storage 정책이 경로 기반(첫 세그먼트 = auth.uid(), 관리자 별도
      //   분기)이라 행이 없어도 소유자·관리자에게 여전히 보이고 지울 수 있다 — 즉 고아가 **회수 가능**
      //   하다(docs/conventions.md §10.1). 반대로 매물 행은 한 번 지우면 되돌릴 수 없고, 예전 순서처럼
      //   사진부터 지우다 실패하면 매물 자체를 영영 못 지우는 상태가 남았다. 그래서 되돌릴 수 없는
      //   단계(행 삭제)를 먼저 확정하고, 되돌릴 수 있는 뒷정리(파일 삭제)를 나중으로 미룬다.
      // 매물은 이미 삭제됐다 — 아래 실패로 되돌리지 않는다. 남은 파일은 회수 가능한 고아이므로
      // 치명적 오류로 취급하지 않고, 콘솔 기록 + 안내 메시지로만 남긴다(별도 알림 UI는 없음).
      if (!photos.ok) {
        console.error('[admin/listings] 사진 목록을 못 읽어 정리를 건너뜀(고아 가능):', listingId);
        setError('매물은 삭제됐지만 일부 사진 파일이 남아있을 수 있습니다.');
      } else {
        const cleanup = await deletePhotoObjectsByPaths(photos.paths);
        if (!cleanup.ok) {
          console.error('[admin/listings] 매물 삭제 후 사진 오브젝트 정리 실패:', listingId);
          setError('매물은 삭제됐지만 일부 사진 파일이 남아있을 수 있습니다.');
        }
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

  const isSold = status === LISTING_STATUS.SOLD;
  const busy = deleting || restoring; // 한쪽이 진행 중이면 다른 쪽도 잠근다(같은 행에 동시 요청 방지).

  return (
    <div className="flex flex-col items-end gap-1">
      <div className="flex items-center gap-2">
        {/* sold 매물에만 렌더 — on_sale 매물은 되돌릴 게 없다(0030의 WHERE status='sold'와 동일 전제). */}
        {isSold && (
          <Button
            type="button"
            variant="info"
            size="sm"
            onClick={handleRestore}
            disabled={busy}
            loading={restoring}
            loadingText="처리 중…"
          >
            판매완료 되돌리기
          </Button>
        )}
        <Button
          type="button"
          variant="danger"
          size="sm"
          onClick={handleDelete}
          disabled={busy}
          loading={deleting}
          loadingText="삭제 중…"
        >
          삭제
        </Button>
      </div>
      {error && (
        <p role="alert" className="text-caption text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
