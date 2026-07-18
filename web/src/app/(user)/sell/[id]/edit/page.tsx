// 본인 매물 수정 화면 (FR6) — 서버 컴포넌트.
// 라우트: /sell/[id]/edit  (라우트 그룹 (user)는 URL에 미포함)
// 역할 게이트는 상위 (user)/sell/layout.tsx의 requireRole(seller)이 담당한다(하위 라우트 자동 적용).
//
// 동작:
//   1) 현재 로그인 판매자 확인.
//   2) id 매물을 본인 것만(.eq('seller_id', user.id)) 조회 — 타인 매물 id면 0건이라 한국어 안내(AC4 앱측 방어).
//        ⚠️ RLS만으로는 부족: SELECT 정책이 "on_sale ∪ own ∪ admin"의 OR 결합이라
//        seller_id 필터가 없으면 남의 on_sale 매물도 읽혀 "수정 가능"처럼 보일 수 있다(2-2 버그와 동일 원리).
//   3) 본인 매물이면 기존 값을 SellForm(edit 모드)에 채워 렌더 → 제출 시 UPDATE(2-3).
//
// Next.js 16 주의: 동적 라우트 params는 Promise이므로 await 한다. [web/AGENTS.md, node_modules/next/dist/docs]
import Link from 'next/link';
import { createClient } from '@/lib/supabase/server';
import { getSignedUrls } from '@/lib/storage';
import { LISTING_IMAGES_BUCKET } from '@/lib/storage/bucket';
import { LISTING_STATUS } from '@/lib/constants';
import SellForm, { type ListingInitialValues } from '../../SellForm';
import { toPhotoItems } from '../../photo-item';

// 수정 폼에 필요한 필드 + 소유권 판정용 id + 판매완료 여부 판정용 status. (status는 폼에서 변경하지 않음)
type EditableListing = ListingInitialValues & { id: string; status: string };

export default async function EditListingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params; // Next.js 16: params는 Promise → await 필수.
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  // 본인 매물만 조회 — 없으면(타인 매물·존재하지 않음) maybeSingle()이 null 반환.
  const { data: listing, error } = await supabase
    .from('listings')
    .select(
      'id, status, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, options, description',
    )
    .eq('id', id)
    .eq('seller_id', user?.id ?? '')
    .maybeSingle<EditableListing>();

  if (error) {
    // 조회 자체가 실패(네트워크·RLS·DB) — "없음"과 구분해 한국어로 안내.
    console.error('[sell/edit] 매물 조회 실패:', error);
  }

  // 본인 매물이 아니거나 존재하지 않음 → 수정 폼을 노출하지 않고 한국어 안내(AC4).
  if (!listing) {
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">매물 수정</h1>
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          매물을 찾을 수 없거나 접근 권한이 없습니다. 본인 매물만 수정할 수 있습니다.
        </p>
        <Link
          href="/sell"
          className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
        >
          내 매물 목록으로
        </Link>
      </main>
    );
  }

  // 판매완료(sold) 매물은 수정 진입을 막는다(거래 끝난 매물 정보 변경 방지).
  //   목록에서 sold 행은 수정 버튼을 숨기지만(page.tsx), URL 직접 접근 대비 서버에서도 한 번 더 막는다(이중 방어).
  //   상태 전환(구매완료/되돌리기)은 2-4 소관이라 여기서 다루지 않는다(스코프 침범 금지).
  if (listing.status === LISTING_STATUS.SOLD) {
    return (
      <main className="mx-auto flex max-w-2xl flex-col gap-4 p-6">
        <h1 className="text-2xl font-semibold">매물 수정</h1>
        <p role="alert" className="rounded bg-zinc-100 px-3 py-2 text-sm text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300">
          판매완료된 매물은 수정할 수 없습니다.
        </p>
        <Link
          href="/sell"
          className="w-fit rounded border border-zinc-300 px-4 py-2 text-sm font-medium dark:border-zinc-700"
        >
          내 매물 목록으로
        </Link>
      </main>
    );
  }

  // 기존 사진 — 화면 순서대로(sort_order). tie-break가 정의돼 있지 않아(#47-2) id를 2차 정렬로
  // 붙인다. 그래야 값이 겹치는 과거 데이터가 있어도 조회 순서가 매번 같다.
  const { data: imageRows, error: imageError } = await supabase
    .from('listing_images')
    .select('id, storage_path')
    .eq('listing_id', listing.id)
    .order('sort_order', { ascending: true })
    .order('id', { ascending: true });

  if (imageError) console.error('[sell/edit] 사진 조회 실패:', imageError);

  // 서명은 **서버에서** 한다 — lib/storage는 서버 전용이고, 브라우저에서 서명하지 않는다(9.2).
  // 배치 1회 호출로 N장을 받는다(NFR7). 개별 실패는 null이 되어 "미리보기 없음"으로 그려진다.
  const rows = imageRows ?? [];
  const signedUrls = await getSignedUrls(LISTING_IMAGES_BUCKET, rows.map((r) => r.storage_path));
  const initialPhotos = toPhotoItems(
    rows.map((r, i) => ({ id: r.id, storage_path: r.storage_path, url: signedUrls[i] })),
  );

  return (
    <main className="mx-auto flex max-w-2xl flex-col gap-8 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">매물 수정</h1>
        <p className="text-sm text-zinc-500">
          내 매물 정보를 수정합니다. (구매 완료 처리는 별도 기능입니다.)
        </p>
      </section>

      <SellForm mode="edit" listingId={listing.id} initialValues={listing} initialPhotos={initialPhotos} />
    </main>
  );
}
