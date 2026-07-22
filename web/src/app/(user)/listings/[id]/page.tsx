// 구매자 매물 상세 (FR10·FR28) — 서버 컴포넌트.
//
// 동작:
//   1) 동적 라우트 params에서 id를 읽는다(Next.js 16: params는 Promise → await).
//   2) 그 id의 매물을 조회하되 판매중(on_sale)만 — FR11 단일 규칙은 buyerListingsQuery(@/lib/listings)에서 비롯된다.
//   3) 찾으면 사진 갤러리 + FR5 15필드를 **신뢰정보 → 차량정보 → 옵션 → 판매자정보** 순으로 그린다(Story 9.5 AC1).
//      못 찾으면 중립 톤 404 안내, 조회 자체가 실패하면 danger 톤 에러 안내(둘을 구분).
//
// 섹션 순서(AC1)의 ①신뢰정보·④판매자정보는 원래 Epic 9 골격이 남긴 빈 슬롯이었으나, Epic 10(10.2·10.6)이
//   차례로 채웠다. 그 값이 전부 없는 경우(신뢰속성 미입력·판매자 요약 RPC 조회 실패 등)엔 지금도
//   **그 섹션만 아무것도 렌더하지 않는다** — 빈 제목·빈 테두리·"준비중" 문구를 두면 의미 없는 잉크가 남는다.
//   (목업 detail-1.html은 옛 순서라 이 주석이 정답이다.)
//
// 열람: FR58(8.5)부터 /listings는 비로그인(anon)도 열람 가능 — on_sale은 RLS상 누구에게나 공개.
//   로그인 게이트는 "문의하기" 같은 행동에만 적용된다(아래 InquiryCta 3분기 참조).
//
// CM3(즉시 비노출): cookies() 기반 인증으로 매 요청 DB를 다시 읽는 동적 렌더다.
//   매물이 sold로 바뀌면 재조회 시 즉시 404 화면이 된다. 정적 캐시 잔존 방지로 force-dynamic 명시.
import Link from 'next/link';
import type { User } from '@supabase/supabase-js';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, UNITS, type UserRole } from '@/lib/constants';
import { buyerListingsQuery, fetchListingGalleryUrls } from '@/lib/listings';
import AppHeader from '@/components/layout/AppHeader';
import ListingGallery from '@/components/listings/ListingGallery';
import EmptyState from '@/components/ui/EmptyState';
import ErrorState from '@/components/ui/ErrorState';
import { buttonClasses } from '@/components/ui/Button';
import InquiryCta, { type InquiryCtaMode } from './InquiryCta';
import {
  VehicleInfoSection,
  OptionsSection,
  TrustInfoSection,
  SellerInfoSection,
} from './ListingDetailSections';

// CM3 보장: 상세도 매 요청 최신 DB 상태 반영(sold 즉시 비노출). 정적화 방지.
export const dynamic = 'force-dynamic';

// 상세 화면에 표시할 FR5 15필드 + 상태(라벨용) + seller_id(문의 CTA 분기용).
type ListingDetail = {
  id: string;
  seller_id: string; // 이 매물의 판매자(매물주). 본인이면 "문의하기" 대신 "내 매물 관리"를 보여준다.
  manufacturer: string;
  model: string;
  body_type: string;
  year: number;
  price: number; // 원(KRW)
  mileage: number; // km
  color: string;
  fuel: string;
  transmission: string;
  displacement: number; // cc
  seats: number;
  region: string;
  accident_free: boolean;
  seller_name: string | null; // 판매자 표시 이름(이메일 @앞부분, 0007). FR5 15필드 밖.
  options: string[] | null; // text[]; 빈 배열·null 가능
  description: string | null; // nullable
  status: string;
  // 신뢰속성 3필드(Story 10.2) — 로그인 사용자만 select에 포함(아래 trustColumns 분기).
  // anon은 select에서 아예 안 물으므로 undefined로 오는데, 렌더 직전에 null로 정규화한다(§4 계약).
  accident_status?: '무사고' | '단순교환' | '사고' | null;
  is_single_owner?: boolean | null;
  is_non_smoker?: boolean | null;
};

/**
 * 문의 CTA 3분기 판정 (AC7) — **상태를 갖는 건 inquiry뿐**이라 판정 자체는 서버(여기)에서 끝내고,
 * 실제 렌더·busy/error 상태는 클라이언트 컴포넌트 `<InquiryCta>` 하나가 맡는다(#82 종결, Story 10.6).
 * 데스크톱 sticky 요약 컬럼과 모바일 하단 고정 바가 **같은 판정**을 써야 하므로 한 자리에 모았다.
 */
function computeInquiryMode(listing: ListingDetail, user: User | null): InquiryCtaMode {
  if (!user) return 'anon'; // 비로그인
  if (user.id === listing.seller_id) return 'owner'; // 본인 매물
  return 'inquiry'; // 로그인 + 타인 매물
}

export default async function ListingDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params; // Next.js 16: params는 Promise라 await 필요.
  const supabase = await createClient();

  // 상단바용 역할 라벨(홈·/search 패턴 재사용 — profiles_select_self RLS로 본인 행 읽기).
  const {
    data: { user },
  } = await supabase.auth.getUser();
  let roleLabel: string | null = null;
  if (user) {
    const { data: profile } = await supabase
      .from('profiles')
      .select('role')
      .eq('id', user.id)
      .single();
    if (profile?.role) {
      roleLabel = ROLE_LABEL[profile.role as UserRole] ?? profile.role;
    }
  }

  // 단일 매물 조회 — 구매자 관점(판매중만) 시작점 buyerListingsQuery(FR11 단일 출처) + id 일치.
  //   maybeSingle(): 0건이면 null(존재하지 않음·sold·접근 권한 없음). edit 페이지와 동일 패턴.
  //
  // ⚠️ 신뢰속성 3컬럼은 **로그인 분기**로만 조회한다(search/page.tsx가 세운 패턴 그대로, 대장 #109).
  //   anon은 `0011_listings_anon_select.sql`이 컬럼 단위로 명시한 목록만 읽을 수 있고 그 3컬럼은
  //   목록에 없다 — anon 키로 요청하면 컬럼 하나만 막히는 게 아니라 `42501`로 select 전체가
  //   실패한다(실측, conventions.md §4.1). anon에도 열려면 새 GRANT 마이그레이션 + 사용자 승인이
  //   필요한데(§9.3 (b)) 이 스토리 범위가 아니므로 넓히지 않는다.
  const trustColumns = user ? ', accident_status, is_single_owner, is_non_smoker' : '';
  const { data: listingRow, error } = await buyerListingsQuery(
    supabase,
    `id, seller_id, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, seller_name, options, description, status${trustColumns}`,
  )
    .eq('id', id)
    .maybeSingle<ListingDetail>();

  if (error) {
    // 원본은 서버 로그에만(디버깅), 사용자에겐 한국어. "없음"이 아니라 "불러오기 실패"로 구분.
    console.error('[listings/detail] 매물 상세 조회 실패:', error);
  }

  // anon 경로는 위 select에서 신뢰속성 3컬럼을 아예 안 물었으므로 그 값이 `undefined`(키 자체
  // 없음)로 온다. 계약(conventions §4)은 "값이 없으면 null"이지 "필드가 없음"이 아니다 — 여기서
  // 명시적으로 null을 채워 타입 선언(`ListingDetail`)과 런타임 모양을 맞춘다(search/page.tsx와 동일 처리).
  const listing =
    listingRow && !user
      ? { ...listingRow, accident_status: null, is_single_owner: null, is_non_smoker: null }
      : listingRow;

  const header = (
    <AppHeader roleLabel={roleLabel ?? undefined} email={user?.email} currentPath={`/listings/${id}`} />
  );

  const backLink = (
    <Link href="/search" className={buttonClasses({ variant: 'secondary' })}>
      매물 목록으로
    </Link>
  );

  // 조회 실패(네트워크·RLS·DB) — "못 찾음"과 **구분**해 danger 톤(AC6).
  //   이건 우리 쪽 고장이고, 사용자가 다시 시도하면 될 수도 있는 상태다.
  if (error) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col items-center gap-4 p-6">
          {/* 상태 화면에도 h1을 남긴다 — 프리미티브(ErrorState·EmptyState)는 제목을 <p>로만 그리므로
              이게 없으면 이 화면엔 heading이 0개가 되어 문서 개요·heading 탐색이 끊긴다.
              관리자 매물 상세의 같은 분기도 <h1>매물 상세</h1>를 유지한다(리포 일관 패턴). */}
          <h1 className="text-section font-bold text-ink-primary">매물 상세</h1>
          <ErrorState
            tone="danger"
            message="매물 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
          />
          {backLink}
        </main>
      </>
    );
  }

  // 못 찾음(존재하지 않는 id·삭제됨·sold) → 구매자에게 비노출(FR11).
  //   ⚠️ **중립 톤이다 — danger(빨강)가 아니다**(UX-DR20). 판매완료는 오류가 아니라 정상적인 결과다.
  //   sold 필터를 여기서 손으로 다시 짜지 않는다: buyerListingsQuery가 FR11 단일 출처이고,
  //   sold는 `!listing`으로 합류해 자동으로 이 화면이 된다.
  //   이 리포는 notFound()/not-found.tsx를 한 번도 쓰지 않는다 — "조건부 렌더 + 커스텀 안내 UI"가
  //   일관된 패턴이라 관례를 바꾸지 않고 프리미티브만 교체했다.
  if (!listing) {
    return (
      <>
        {header}
        <main className="mx-auto flex max-w-2xl flex-col items-center gap-2 p-6">
          {/* 위 에러 분기와 같은 이유로 h1을 남긴다(heading 0개 방지). */}
          <h1 className="text-section font-bold text-ink-primary">매물 상세</h1>
          <EmptyState
            title="매물을 찾을 수 없어요."
            description="삭제됐거나 판매완료된 매물일 수 있어요."
            action={backLink}
          />
        </main>
      </>
    );
  }

  // 사진 갤러리 — 매물이 확인된 **뒤에** 조회한다. 그래야 sold·미존재 매물의 사진을 애초에 안 읽는다
  //   (FR11 이미지 축: DB RLS + 호출부 id 좁히기 2층, conventions §6).
  const galleryUrls = await fetchListingGalleryUrls(supabase, listing.id);

  // ④ 판매자정보 — 가입 시점(RLS로 막힘) + "다른 on_sale 매물 N건"(FR11 강제지점)을
  //   SECURITY DEFINER RPC 하나로 구한다(0019, Story 10.6). anon도 실행 가능(FR58).
  //   실패하면 서버 콘솔에만 로그하고 null로 정규화 — SellerInfoSection이 그 행만 숨긴다(I/O 매트릭스).
  const { data: sellerSummary, error: sellerSummaryError } = await supabase
    .rpc('get_seller_public_summary', {
      p_seller_id: listing.seller_id,
      p_exclude_listing_id: listing.id,
    })
    .maybeSingle<{ joined_at: string | null; other_on_sale_count: number | null }>();

  if (sellerSummaryError) {
    console.error('[listings/detail] 판매자 요약 조회 실패:', sellerSummaryError);
  }

  const title = `[${listing.manufacturer}] ${listing.model}`;
  const priceText = `${listing.price.toLocaleString('ko-KR')}${UNITS.price}`;
  const inquiryMode = computeInquiryMode(listing, user);
  const loginHref = `/login?redirectedFrom=${encodeURIComponent(`/listings/${listing.id}`)}`;

  return (
    <>
      {header}
      {/* pb-28: 모바일 하단 고정 바(아래)가 페이지 끝 콘텐츠를 가리지 않게 비워 두는 자리.
          데스크톱(lg)엔 고정 바가 없으므로 되돌린다. */}
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6 pb-28 lg:pb-6">
        {/* 제목 — 2열 어느 쪽에도 속하지 않는 페이지 머리. 폭이 좁아도 …로 자른다(D5). */}
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-2">
            <h1 className="min-w-0 truncate text-section font-bold text-ink-primary sm:text-display">
              {title}
            </h1>
            <span className="shrink-0 whitespace-nowrap rounded-badge border border-brand-petrol px-2 py-0.5 text-caption font-semibold text-brand-petrol">
              판매중
            </span>
          </div>
          <p className="truncate whitespace-nowrap text-meta font-medium text-ink-muted">
            {listing.year}년 · {listing.mileage.toLocaleString('ko-KR')}
            {UNITS.mileage} · {listing.region}
          </p>
        </div>

        {/* 2열(좌 갤러리·정보 / 우 요약 sticky) → 좁아지면 스택 1열. 폭 축소는 **열 수로만** 흡수한다(D5).
            minmax(0,1fr): 좌 컬럼이 긴 텍스트에 밀려 넘치지 않게 최소 폭을 0으로 풀어 준다. */}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
          <div className="flex min-w-0 flex-col gap-6">
            {/* key=매물 id — 갤러리의 현재 인덱스·실패기록은 이 매물에만 유효한 상태다.
                지금은 상세→상세 직접 이동 링크가 없어 실제로 밟히지 않지만(진입로는 /search 카드와
                채팅방뿐), 그런 링크가 생기면 React가 같은 자리의 컴포넌트를 재사용해 이전 매물의
                index가 남는다(사진 10장에서 2장짜리로 가면 "8/2"). 한 줄로 그 부류를 닫아 둔다. */}
            <ListingGallery key={listing.id} urls={galleryUrls} title={title} />

            {/* ① 신뢰정보 — TrustInfoSection이 뱃지·면책을 한 몸으로 그린다(Story 10.2, B9).
                신뢰속성이 전부 없으면(anon 포함) null을 반환해 섹션 자체가 안 그려진다(AC1). */}
            <TrustInfoSection listing={listing} />

            {/* ② 차량정보 */}
            <VehicleInfoSection listing={listing} />

            {/* ③ 옵션 — 카테고리 분류·희소옵션 강조는 Epic 10.3/10.4의 몫이다. */}
            <OptionsSection listing={listing} />

            {/* ④ 판매자정보 — 닉네임+가입 시점+다른 매물 N건 3행만(FR56, Story 10.6).
                값이 하나도 없으면 null을 반환해 섹션 자체가 안 그려진다(①과 동일 규칙). */}
            <SellerInfoSection
              sellerName={listing.seller_name}
              joinedAt={sellerSummaryError ? null : sellerSummary?.joined_at}
              otherOnSaleCount={sellerSummaryError ? null : sellerSummary?.other_on_sale_count}
            />
          </div>

          {/* 우 요약 컬럼 자리 — **`<InquiryCta>` 하나**가 데스크톱 sticky aside(≥1024px)와
              모바일 하단 고정 바(<1024px)를 **내부에서 둘 다** 그린다(#82 종결, Story 10.6).
              모바일 블록은 position:fixed라 이 grid 자식 자리에 있어도 뷰포트 하단에 그대로 고정된다
              (자세한 이유는 InquiryCta.tsx 헤더 주석). busy/error 상태가 두 블록에서 공유된다. */}
          <InquiryCta mode={inquiryMode} listingId={listing.id} loginHref={loginHref} priceText={priceText} />
        </div>

        {backLink}
      </main>
    </>
  );
}
