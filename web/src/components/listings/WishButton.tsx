'use client';

// 찜(♡) 토글 버튼 (Story 10.5) — ListingCard의 죽은 하트 자리표시자(Epic 9)를 대신한다.
//
// 책임:
//   1) 낙관적 토글: 누르면 즉시 채워짐(♥) → wishlists insert/delete 확정. 실패 시 롤백 + 조용한 토스트.
//   2) 로그인 게이트(FR58): 비로그인 클릭 → /login?redirectedFrom=<현재경로+wish=id>로 이동
//      (아이콘은 바꾸지 않는다 — 저장이 안 됐으니). 로그인 후 원위치로 돌아오면 그 매물을 자동 반영.
//   3) 접근성: 히트영역 44×44(h-11 w-11) 유지, aria-pressed + "찜하기"↔"찜 취소" 라벨 전환.
//   4) 진행 중 연타 차단: pending이면 버튼을 disabled로 막는다(클릭 이벤트 자체가 안 붙는다).
//
// 왜 userId를 prop으로 안 받나: 이 컴포넌트의 계약은 {listingId, initialWished, authed} 셋뿐이다
//   (spec Code Map). 실제 토글에 필요한 auth.uid()는 클릭 시점에 브라우저 세션에서
//   supabase.auth.getUser()로 구한다 — 서버가 이미 검증한 값을 클라가 다시 스스로 구하는 편이
//   "클라가 보낸 값은 신뢰하지 않는다"(CLAUDE.md B9)와도 맞고, insert/delete는 어차피 RLS
//   (auth.uid() = user_id)가 최종 관문이라 여기서 잘못된 id를 보내도 DB가 막는다.
import { useCallback, useEffect, useRef, useState } from 'react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

// 조용한 토스트 노출 시간 — 전역 토스트 인프라 없이 로컬 state + setTimeout으로 최소 구현(A2,
// 대장 이월: 2번째 소비처가 생기면 공용 primitive로 승격).
const TOAST_DURATION_MS = 3000;

// Postgres 유니크 위반(SQLSTATE). 로그인 복귀 자동반영이 이미 찜된 상태에 다시 시도하면
// (예: 개발 모드 effect 이중 실행) insert가 이 코드로 실패한다 — 최종 상태는 어차피 "찜됨"이라 무시.
const PG_UNIQUE_VIOLATION = '23505';

export default function WishButton({
  listingId,
  initialWished,
  authed,
}: {
  listingId: string;
  initialWished: boolean;
  authed: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [wished, setWished] = useState(initialWished);
  const [pending, setPending] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const autoAppliedRef = useRef(false); // "?wish=" 자동반영은 이 카드당 1회만.
  const [autoWishPending, setAutoWishPending] = useState(false); // 아래 두 effect를 잇는 신호.
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback((message: string) => {
    setToast(message);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), TOAST_DURATION_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, []);

  // 서버(RLS)에 insert/delete를 보내고, 실패하면 롤백 + 토스트. `next`=적용하려는 목표 상태.
  const applyToggle = useCallback(
    async (next: boolean) => {
      if (pending) return;
      setPending(true);
      setWished(next); // 낙관적 반영 — 서버 확정 전에 즉시 아이콘부터 바꾼다.
      try {
        const supabase = createClient();
        const {
          data: { user },
        } = await supabase.auth.getUser();

        if (!user) {
          // `authed`는 서버 렌더 시점 값이다 — 그 사이 세션이 만료되면 authed=true인 채로 여기까지
          // 온다. 이건 "진짜 에러"가 아니라 재로그인이 필요한 상태라, 실패 토스트(재시도해도 안 되는
          // 문구)를 띄우는 대신 !authed 클릭과 동일하게 로그인 게이트로 보낸다(코드리뷰 2026-07-22 P3).
          setWished(!next); // 롤백(저장 안 됨)
          const nextParams = new URLSearchParams(searchParams.toString());
          nextParams.set('wish', listingId);
          const target = `${pathname}?${nextParams.toString()}`;
          router.push(`/login?redirectedFrom=${encodeURIComponent(target)}`);
          return;
        }

        if (next) {
          const { error } = await supabase
            .from('wishlists')
            .insert({ user_id: user.id, listing_id: listingId });
          if (error && error.code !== PG_UNIQUE_VIOLATION) throw error;
        } else {
          const { error } = await supabase
            .from('wishlists')
            .delete()
            .eq('user_id', user.id)
            .eq('listing_id', listingId);
          if (error) throw error;
        }
      } catch (err) {
        console.error('[wishlist] 찜 토글 실패:', err);
        setWished(!next); // 롤백 — 직전 상태로 복귀.
        showToast('찜 처리에 실패했어요. 잠시 후 다시 시도해주세요.');
      } finally {
        setPending(false);
      }
    },
    [pending, listingId, showToast, searchParams, pathname, router],
  );

  // 로그인 복귀 자동반영 — **감지/URL정리**와 **실제 토글 실행**을 서로 다른 effect로 나눈다.
  //   왜 나누나: 한 effect에서 둘 다 하면, 이 effect가 스스로 부르는 `router.replace`가 이 effect의
  //   의존값(searchParams)을 바꿔 **effect가 자기 자신을 재실행**시킨다. 그때 React가 직전 실행의
  //   cleanup(예정된 setTimeout을 clearTimeout)을 먼저 돌리므로, "찜 반영"이 실행되기도 전에 취소돼
  //   버린다 — URL은 깨끗해지는데 실제 insert는 영영 안 나가는 조용한 버그였다(실브라우저로 재현·확인).
  //   그래서 아래 effect는 searchParams가 바뀌어도 취소될 게 없다 — "무엇을 할지"만 정하고 끝난다.

  // ① 감지: URL의 `wish` 파라미터가 이 카드의 id와 같으면 1회만 신호를 세우고 파라미터를 지운다.
  //   로그인 전이면(authed=false, 아직 세션 반영 전 렌더 등) 아무것도 하지 않는다 — 다음 렌더에서
  //   authed=true가 되면 그때 반영.
  useEffect(() => {
    if (autoAppliedRef.current) return;
    if (!authed) return;
    if (searchParams.get('wish') !== listingId) return;
    autoAppliedRef.current = true;

    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.delete('wish');
    const query = nextParams.toString();
    router.replace(query ? `${pathname}?${query}` : pathname);

    // queueMicrotask로 미룬다(setTimeout이 아니라) — 이 effect는 cleanup을 반환하지 않으므로
    // router.replace가 유발하는 재실행이 이 예약을 취소할 방법이 없다(위 ①·② 분리 설명 참조).
    queueMicrotask(() => setAutoWishPending(true));
  }, [authed, listingId, searchParams, pathname, router]);

  // ② 실행: ①이 세운 신호에만 반응한다(searchParams에 의존하지 않으므로 위 router.replace가
  //   이 effect를 취소하지 못한다). setTimeout은 여기서도 필요하다 — applyToggle이 setState를
  //   부르는데, effect 본문에서 동기 호출하면 react-hooks/set-state-in-effect 린트가 잡는다.
  useEffect(() => {
    if (!autoWishPending) return;
    if (wished) return; // 이미 찜된 상태(예: 재적용)면 할 일 없음.
    const timer = setTimeout(() => void applyToggle(true), 0);
    return () => clearTimeout(timer);
    // wished·applyToggle은 의도적으로 deps에서 뺀다 — 이 effect는 autoWishPending이 처음 true가
    // 될 때 1회만 반응해야 한다(autoAppliedRef가 애초에 ①을 1회로 막아준다).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoWishPending]);

  function handleClick() {
    if (pending) return;

    if (!authed) {
      // 아이콘은 그대로 둔다(저장 불가 상태라 바꾸지 않음) — 로그인 게이트로 보냈다가 복귀 후 반영.
      const nextParams = new URLSearchParams(searchParams.toString());
      nextParams.set('wish', listingId);
      const target = `${pathname}?${nextParams.toString()}`;
      router.push(`/login?redirectedFrom=${encodeURIComponent(target)}`);
      return;
    }

    void applyToggle(!wished);
  }

  return (
    <div className="pointer-events-none absolute inset-x-0 top-0 aspect-[5/3]">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        aria-pressed={wished}
        aria-label={wished ? '찜 취소' : '찜하기'}
        className="pointer-events-auto absolute right-2 top-full mt-1 flex h-11 w-11 items-center justify-center rounded-full bg-surface-raised text-lg text-ink-primary shadow-card disabled:opacity-70"
      >
        <span aria-hidden="true">{wished ? '♥' : '♡'}</span>
      </button>

      {/* 조용한 토스트 — role="status"로 스크린리더에 알리되 화면 흐름을 막지 않는다. 전역 인프라 없이
          이 버튼 로컬 state로만 존재하다가 setTimeout으로 자동 소멸(A2). */}
      {toast && (
        <p
          role="status"
          className="pointer-events-none absolute right-2 top-[calc(100%+56px)] w-max max-w-[180px] rounded-chip bg-ink-primary px-2 py-1 text-caption text-white shadow-card"
        >
          {toast}
        </p>
      )}
    </div>
  );
}
