'use client';

// 매물 상세의 "문의하기" 버튼 (FR19, Story 5-2).
//
// 동작: 클릭하면 그 매물의 판매자와의 채팅방을 열고(있으면 재사용, 없으면 생성) 그 방으로 이동한다.
//   상대(판매자)를 고르는 화면은 없다 — 매물 주인에게 자동 연결(DB 트리거가 seller_id를 매물주로 강제).
//
// 패턴은 sell/ListingActions.tsx를 그대로 따른다:
//   · 브라우저 Supabase로 직접 처리(RLS 보호) · 중복 클릭 차단(busy 가드) · 한국어 에러 표시(원본은 콘솔만)
//   · 처리 중 loading 표시.
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { openOrCreateRoom } from '@/lib/chat';
import Button from '@/components/ui/Button';

export default function InquiryButton({ listingId }: { listingId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleInquiry() {
    if (busy) return; // 연타 차단(방이 두 번 열리는 것·이중 이동 방지)
    setError(null);
    setBusy(true);
    try {
      const supabase = createClient();

      // 현재 로그인 사용자 = 구매자. 방의 buyer_id가 된다.
      //   getUser()는 Auth 서버에 재검증해 신뢰 가능(쿠키만 믿지 않음).
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        // proxy가 비로그인을 1차로 막지만, 만약을 대비한 방어.
        setError('로그인이 필요합니다. 다시 로그인해주세요.');
        return;
      }

      // 방 열기(생성 또는 재사용) — 규칙은 @/lib/chat 한 곳에서.
      const result = await openOrCreateRoom(supabase, listingId, user.id);
      if ('error' in result) {
        setError(result.error);
        return;
      }

      // 성공 → 그 채팅방으로 이동.
      router.push(`/chat/${result.roomId}`);
    } catch (err) {
      console.error('[listings/detail] 문의하기 예외:', err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-1">
      <Button
        type="button"
        variant="primary"
        onClick={handleInquiry}
        loading={busy}
        loadingText="문의 채팅방 여는 중…"
        className="w-fit"
      >
        문의하기
      </Button>
      {error && (
        <p role="alert" className="text-xs text-red-600 dark:text-red-400">
          {error}
        </p>
      )}
    </div>
  );
}
