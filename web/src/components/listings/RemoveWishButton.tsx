'use client';

// 찜 목록의 "판매완료" 타일에서 찜을 해제하는 버튼 (코드리뷰 2026-07-22 P1).
//
// 왜 필요한가: on_sale 카드는 WishButton으로 찜을 해제할 수 있는데, 판매완료(sold)로 바뀐 찜은
// 해제 수단이 전혀 없어 목록에 영구히 남는다(비대칭·클러터). 동작은 WishButton의 "찜 취소"와
// 같지만(wishlists에서 (user_id, listing_id) delete), sold 타일엔 하트 아이콘이 어울리지 않아
// 별도의 작은 텍스트 버튼으로 둔다.
//
// WishButton과 달리 낙관적 반영이 없다 — 이 버튼이 지우는 타일은 카드가 아니라 통째로 사라지는
// 대상이라(회색 타일 자체가 없어짐), "즉시 지웠다가 실패 시 되살리는" 낙관적 UI보다 성공 후
// router.refresh()로 서버 재조회해 지우는 편이 더 단순하다(A2).
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';

export default function RemoveWishButton({ listingId }: { listingId: string }) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleClick() {
    if (pending) return;
    setPending(true);
    setError(null);
    try {
      const supabase = createClient();
      const {
        data: { user },
      } = await supabase.auth.getUser();

      if (!user) {
        // 세션 만료 — WishButton P3와 같은 원칙: 재시도해도 안 되는 실패 문구 대신 로그인으로 보낸다.
        router.push(`/login?redirectedFrom=${encodeURIComponent('/wishlist')}`);
        return;
      }

      const { error: deleteError } = await supabase
        .from('wishlists')
        .delete()
        .eq('user_id', user.id)
        .eq('listing_id', listingId);
      if (deleteError) throw deleteError;

      router.refresh(); // 성공 → 서버가 목록을 다시 조회하면 이 타일은 결과에서 빠진다.
    } catch (err) {
      console.error('[wishlist] 찜 목록에서 제거 실패:', err);
      setError('제거하지 못했어요. 잠시 후 다시 시도해주세요.');
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={handleClick}
        disabled={pending}
        aria-label="찜 목록에서 제거"
        className="text-caption font-medium text-ink-secondary underline decoration-dotted underline-offset-2 disabled:opacity-50"
      >
        {pending ? '제거 중…' : '찜 목록에서 제거'}
      </button>
      {error && (
        <p role="alert" className="text-caption text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
