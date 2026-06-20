'use client';

// 본인 매물 행의 관리 버튼 (FR6·FR8) — 구매 완료 버튼 + 수정 진입 링크 + 삭제 버튼.
//
// 설계:
//   · 구매 완료(2-4·FR8): 실수 방지 확인(window.confirm) 후 status를 sold로 전환.
//       - UPDATE payload에 { status:'sold' }만 보낸다 → seller_id·다른 필드 위조/부수변경 차단(AC3·AC4).
//       - RLS(listings_update_own)가 타인 매물 전환을 에러가 아니라 0행으로 막는다 → .select()로 0행이면 한국어 거부 안내(AC3).
//       - 판매중(on_sale)일 때만 버튼 노출(canComplete) → 이미 sold면 버튼 자체가 없다(AC2 앱측).
//       - 성공 시 router.refresh()로 목록을 갱신 → 배지가 "판매완료"로 바뀐다(AC1).
//   · 수정: /sell/[id]/edit 로 이동(서버 컴포넌트가 본인 매물만 조회해 폼에 채움).
//   · 삭제: 실수 방지로 확인(window.confirm) 후 DELETE.
//       - RLS(listings_delete_own)가 타인 매물 삭제를 에러가 아니라 0행으로 막는다 → .select()로 0행이면 한국어 거부 안내.
//       - 성공 시 router.refresh()로 목록에서 즉시 제거 반영.
//   · 원본 에러·코드는 콘솔에만, 사용자에겐 한국어.
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { LISTING_STATUS } from '@/lib/constants';
import Button, { buttonClasses } from '@/components/ui/Button';

type Props = {
  listingId: string;
  label: string; // 확인 메시지에 보여줄 매물 요약(예: "[현대] 아반떼 CN7")
  canEdit?: boolean; // 판매중일 때만 수정 진입 노출(판매완료 매물 정보 변경 방지). 기본 false(안전 기본값).
  canComplete?: boolean; // 판매중일 때만 "구매 완료" 버튼 노출(이미 sold면 숨김 — AC2). 기본 false(안전 기본값).
};

// canEdit·canComplete 기본값은 false(fail-safe) — 상태를 바꾸는 버튼이므로, 호출부가 status 조건을
//   깜빡 빠뜨려도 sold 매물에 버튼이 잘못 노출되지 않게 "닫힘"으로 시작한다(과노출보다 미노출이 안전).
export default function ListingActions({
  listingId,
  label,
  canEdit = false,
  canComplete = false,
}: Props) {
  const router = useRouter();
  const [deleting, setDeleting] = useState(false);
  const [completing, setCompleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // "구매 완료" 전환 (FR8) — status를 sold로만 바꾼다(판매자 본인, 상대 지정 불필요).
  async function handleComplete() {
    if (completing) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(AC1 실수 방지).
    const ok = window.confirm(
      `'${label}' 매물을 구매 완료 처리할까요? 처리하면 구매자에게 더 이상 노출되지 않습니다.`,
    );
    if (!ok) return;

    setError(null);
    setCompleting(true);
    try {
      const supabase = createClient();
      // payload는 status만 — seller_id·다른 필드를 보내지 않아 위조·부수변경을 원천 차단(AC3·AC4).
      // .eq('status','on_sale') 전제조건 — 이미 sold인(또는 화면이 낡아 그새 바뀐) 매물을 다시 누르거나
      //   URL로 강제 재전환을 시도하면 매칭 행이 0개가 돼 아래 0행 분기에서 거부된다(AC2 "다시 전환 시도해도 거부").
      //   화면 버튼은 canComplete로 가리지만(앱측 1차), 이 조건이 "조용한 no-op 성공"까지 막는 서버측 빗장이다.
      // .select()로 바뀐 행을 받아 행 수를 본다 — RLS로 막히면 에러가 아니라 0행.
      const { data: updated, error: updateError } = await supabase
        .from('listings')
        .update({ status: LISTING_STATUS.SOLD })
        .eq('id', listingId)
        .eq('status', LISTING_STATUS.ON_SALE)
        .select('id');

      if (updateError) {
        console.error('[sell] listings 구매완료 UPDATE 실패:', updateError);
        setError('구매 완료 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
        return;
      }
      if (!updated || updated.length === 0) {
        // 0행이 나오는 경우: ① 타인 매물(RLS 차단) ② 매물 없음(그새 삭제됨) ③ 이미 sold(전제조건 불충족).
        setError(
          '본인 매물만 구매 완료 처리할 수 있습니다. (매물을 찾을 수 없거나, 접근 권한이 없거나, 이미 구매 완료된 매물입니다.)',
        );
        return;
      }

      // 성공 → 목록 갱신으로 "판매완료" 배지 즉시 반영(AC1).
      router.refresh();
    } catch (err) {
      console.error('[sell] listings 구매완료 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setCompleting(false);
    }
  }

  async function handleDelete() {
    if (deleting) return; // 중복 클릭 차단
    // 확인 단계 — 취소하면 아무 일도 일어나지 않는다(삭제 실수 방지, FR6).
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
        {canComplete && (
          <Button
            type="button"
            variant="info"
            size="sm"
            onClick={handleComplete}
            loading={completing}
            loadingText="처리 중…"
          >
            구매 완료
          </Button>
        )}
        {canEdit && (
          <Link
            href={`/sell/${listingId}/edit`}
            className={buttonClasses({ variant: 'secondary', size: 'sm' })}
          >
            수정
          </Link>
        )}
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
