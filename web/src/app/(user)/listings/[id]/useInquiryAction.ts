'use client';

// 문의 개시(방 열기 또는 재사용) 동작 하나를 훅으로 뽑아낸 것 — 원래 InquiryCta.tsx 안에 있던
// handleInquiry + busy/error 상태를 그대로 옮겼다(2026-08-13 #2 상세 재구성).
//
// **왜 컴포넌트가 아니라 훅인가**: 상세 화면에 문의 버튼이 놓이는 자리가 세 곳이 됐다 —
//   ① 데스크톱 요약 컬럼, ② 모바일 하단 고정 바, ③ 맨 아래 "판매자정보" 카드(목업 detail-1.html의
//   `.seller-contact-btn`, 사용자 지적 #2 "가장 하단이 목업엔 문의하기").
//   ①②는 **같은 버튼의 두 배치**라 상태를 공유해야 한다(docs/tech-debt.md #82: 예전엔 각각
//   마운트해서, 데스크톱에서 문의가 실패해 에러가 뜬 채 창을 좁히면 하단 바는 깨끗한 "문의하기"로
//   보였다 — 같은 문의가 두 군데서 다르게 보였다는 뜻). 그래서 InquiryCta는 이 훅을 **한 번만**
//   부르고 두 블록이 그 값을 함께 읽는다.
//   ③은 화면상 멀리 떨어진 별개 버튼이고 ①②와 **동시에 보인다** — 즉 #82가 막으려던 "안 보이는
//   불일치"가 아니다. 그래서 자기 훅 인스턴스를 따로 갖는다(누른 쪽만 진행 표시가 뜬다).
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { openOrCreateRoom } from '@/lib/chat';

export type InquiryActionState = {
  busy: boolean;
  error: string | null;
  start: () => Promise<void>;
};

export function useInquiryAction(listingId: string): InquiryActionState {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
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

  return { busy, error, start };
}
