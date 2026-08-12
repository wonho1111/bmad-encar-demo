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
import { fetchWishedListingIds } from '@/lib/wishlist';
import AppHeader from '@/components/layout/AppHeader';
import ListingGallery from '@/components/listings/ListingGallery';
import WishButton from '@/components/listings/WishButton';
import TrustAttributes from '@/components/listings/TrustAttributes';
import EmptyState from '@/components/ui/EmptyState';
import ErrorState from '@/components/ui/ErrorState';
import { buttonClasses } from '@/components/ui/Button';
import InquiryCta, { type InquiryCtaMode } from './InquiryCta';
import SellerInquiryButton from './SellerInquiryButton';
import { formatPrice } from '@/lib/price';
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
        <main className="mx-auto flex w-full max-w-2xl flex-col items-center gap-4 p-6">
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
        <main className="mx-auto flex w-full max-w-2xl flex-col items-center gap-2 p-6">
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

  // 조회수 +1 — 상세 페이지 진입 시 정확히 이 한 곳에서만 호출한다(Story 11.1).
  //   increment_listing_view RPC가 view_count의 유일한 쓰기 통로다(0020) — authenticated의
  //   컬럼 직접 UPDATE·INSERT, anon의 직접 쓰기는 DB에서 회수돼 있다. 호출마다 항상 +1(멱등
  //   아님, 의도된 동작) — 지켜야 하는 건 "호출 지점을 여기 하나로 한정"뿐이다(ListingCard 등
  //   카드 렌더 경로는 호출하지 않음 — viewCountCallSite.test.ts가 이 불변식을 소스 스캔으로 고정).
  //   실패해도 페이지 렌더는 막지 않는다(sellerSummaryError와 동일 패턴 — 조회수는 핵심 기능이 아님).
  const { error: viewCountError } = await supabase.rpc('increment_listing_view', {
    p_listing_id: listing.id,
  });

  if (viewCountError) {
    console.error('[listings/detail] 조회수 증가 실패:', viewCountError);
  }

  // 찜 여부(Story 10.5의 누락 보완, 2026-07-29) — 카드와 같은 오버레이 조회를 매물 1건에 대해 한다.
  //   비로그인이면 조회하지 않는다(하트는 그대로 보이고 게이트는 클릭에만 걸린다, FR58·conventions §8).
  const wished = user ? (await fetchWishedListingIds(supabase, user.id, [listing.id])).has(listing.id) : false;

  const title = `[${listing.manufacturer}] ${listing.model}`;
  const priceText = formatPrice(listing.price);
  const inquiryMode = computeInquiryMode(listing, user);
  const loginHref = `/login?redirectedFrom=${encodeURIComponent(`/listings/${listing.id}`)}`;

  // 요약 카드의 주요 제원 6칸 — 목업 detail-1.html `.spec-mini-grid`의 항목·순서 그대로
  // (연식·주행거리·연료·배기량·지역·색상). 전부 아래 "차량정보" 표에도 있는 값이다 — 여기 있는
  // 이유는 "스크롤 없이 CTA 옆에서 판단할 수 있게"이지 새 정보를 더하려는 게 아니다.
  const summarySpecs = [
    { label: '연식', value: `${listing.year}년` },
    { label: '주행거리', value: `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}` },
    { label: '연료', value: listing.fuel },
    { label: '배기량', value: `${listing.displacement.toLocaleString('ko-KR')}${UNITS.displacement}` },
    { label: '지역', value: listing.region },
    { label: '색상', value: listing.color },
  ];

  return (
    <>
      {header}
      {/* pb-28: 모바일 하단 고정 바(아래)가 페이지 끝 콘텐츠를 가리지 않게 비워 두는 자리.
          데스크톱(lg)엔 고정 바가 없으므로 되돌린다. */}
      <main className="mx-auto flex w-full max-w-6xl flex-col gap-6 p-6 pb-28 lg:pb-6">
        {/* 뒤로가기(breadcrumb) — 목업 detail-1.html `.breadcrumb-row`(2026-08-13 사용자 지적 #2:
            "뒤로가기 버튼이 없다"). 브라우저 뒤로가기(history)가 아니라 **매물 목록으로 가는 링크**다:
            상세로 들어오는 길이 목록만이 아니라 채팅방·직접 URL도 있어서, history를 되감으면
            사람마다 다른 곳으로 간다. 목적지가 늘 같은 링크가 예측 가능하다.
            예전엔 이 역할을 **페이지 맨 아래 "매물 목록으로" 버튼**이 했는데, 그 자리는 목업 기준
            문의 버튼 자리라 SellerInquiryButton에 내줬다. */}
        <Link
          href="/search"
          className="inline-flex w-fit items-center gap-1.5 text-meta font-semibold text-ink-secondary hover:text-ink-primary"
        >
          <svg viewBox="0 0 24 24" fill="none" aria-hidden className="h-3.5 w-3.5">
            <path d="M15 18l-6-6 6-6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          매물 목록
        </Link>

        {/* 위 2열: 좌 갤러리 / 우 요약 카드(sticky) → 좁아지면 스택 1열. 폭 축소는 **열 수로만** 흡수한다(D5).
            minmax(0,1fr): 좌 컬럼이 긴 텍스트에 밀려 넘치지 않게 최소 폭을 0으로 풀어 준다.
            ✎ 2026-08-13(#2) — 정보 섹션 카드 4개는 이 2열 **밖으로** 내려 전체 폭을 쓴다(목업의
            `.section-cards-wrap`). 예전엔 좌 컬럼 안에 있어서 차량정보 13행이 좁은 폭에 갇혀
            세로로 길게 늘어졌고, 오른쪽 요약 카드는 가격·버튼 둘뿐이라 크게 비어 보였다 —
            사용자가 지적한 "문의하기 쪽에 아무것도 없고 모든 값이 아래에 있다"가 이 배치다. */}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_340px]">
          {/* key=매물 id — 갤러리의 현재 인덱스·실패기록은 이 매물에만 유효한 상태다.
              지금은 상세→상세 직접 이동 링크가 없어 실제로 밟히지 않지만(진입로는 /search 카드와
              채팅방뿐), 그런 링크가 생기면 React가 같은 자리의 컴포넌트를 재사용해 이전 매물의
              index가 남는다(사진 10장에서 2장짜리로 가면 "8/2"). 한 줄로 그 부류를 닫아 둔다. */}
          <div className="min-w-0">
            <ListingGallery key={listing.id} urls={galleryUrls} title={title} />
          </div>

          {/* 요약 카드(목업 `.summary-col`) — 제목·찜 / 신뢰뱃지+짧은 면책 / 가격 / 주요제원 6칸 /
              CTA. 데스크톱에서만 카드 표면(테두리·배경·그림자)을 입히고 sticky로 붙인다. 모바일에선
              갤러리 바로 아래 흐름에 그대로 쌓이고(목업 모바일 프레임과 같은 순서), CTA는
              InquiryCta가 하단 고정 바로 대신 그린다. */}
          <aside className="flex min-w-0 flex-col gap-4 lg:sticky lg:top-6 lg:self-start lg:rounded-card lg:border lg:border-border-hairline lg:bg-surface-raised lg:p-5 lg:shadow-card lg:dark:shadow-none">
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 flex-col gap-1">
                {/* break-keep: 한국어를 어절 단위로만 끊는다(좁은 요약 컬럼에서 제목이 글자 중간에서
                    갈라지는 것 방지 — HeroSearch 헤드라인과 같은 처리). */}
                <h1 className="text-section font-bold text-ink-primary break-keep">
                  {title} · {listing.year}년
                </h1>
                {/* ✎ 2026-08-13 사용자 지적(중복 점검) — 여기 있던 "주행거리 · 지역" 요약 줄을 뺐다.
                    바로 아래 주요제원 6칸에 같은 두 값이 있고, 모바일에선 요약 카드가 세로로
                    쌓이면서 같은 값을 두 줄 간격으로 두 번 읽게 된다. 목업 `.summary-head`에도
                    제목 아래 별도 요약 줄은 없다(연식만 제목에 붙어 있다). */}
              </div>
              {/* 찜(♡) — 상세에도 하트가 있다(Story 10.5 누락 보완, 2026-07-29).
                  ⚠️ **InquiryCta 안이 아니라 여기(요약 카드 제목 줄)에 둔다.** InquiryCta는 요약 카드
                  블록과 모바일 하단 바 **두 블록을 동시에** 렌더하므로, 거기 넣으면 상태를 가진 하트가
                  두 번 마운트돼 한쪽만 채워지는 불일치가 생긴다(#82와 같은 부류). 이 자리는 두
                  뷰포트 모두에서 한 번만 그려진다. */}
              <WishButton listingId={listing.id} initialWished={wished} authed={!!user} variant="inline" />
            </div>

            {/* 신뢰 뱃지 + **짧은** 면책(목업 `.trust-disclaimer-sm`) — 긴 면책은 아래 "신뢰정보"
                카드가 그대로 보여준다. 뱃지가 없으면 아무것도 안 그린다. */}
            <TrustAttributes variant="summary" listing={listing} />

            {/* 가격 = 상세의 대표 숫자. 카드(26/800)보다 큰 large 변형(30/800, DESIGN.md:42).
                data-testid: 같은 가격 문자열이 모바일 하단 고정 바에도 있어(InquiryCta) 화면 전체에서
                텍스트로 찾으면 2건이 잡힌다. E2E(write-flows)가 이 대표 가격만 콕 집게 하는 훅이다 —
                이 요약 블록은 데스크톱·모바일 양쪽에서 항상 보이므로 뷰포트와 무관하게 안정적이다. */}
            <p
              data-testid="detail-price"
              className="whitespace-nowrap text-price-lg font-extrabold text-price-emphasis"
            >
              {priceText}
            </p>

            {/* 주요 제원 6칸(목업 `.spec-mini-grid`) — 아래 "차량정보" 표에 다 있는 값이지만,
                구매 판단에 가장 먼저 쓰이는 여섯 개를 스크롤 없이 CTA 옆에서 보게 한다. */}
            <dl className="grid grid-cols-2 gap-x-4 gap-y-3 border-t border-border-hairline pt-4">
              {summarySpecs.map(({ label, value }) => (
                <div key={label} className="flex min-w-0 flex-col">
                  <dt className="text-caption font-medium text-ink-muted">{label}</dt>
                  <dd className="truncate text-body font-bold text-ink-primary" title={value}>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>

            {/* CTA — 이 카드 안 버튼(데스크톱)과 모바일 하단 고정 바를 **한 컴포넌트**가 함께 그린다.
                모바일 블록은 position:fixed라 이 자리에 있어도 뷰포트 하단에 고정된다(#82 종결). */}
            <InquiryCta mode={inquiryMode} listingId={listing.id} loginHref={loginHref} priceText={priceText} />
          </aside>
        </div>

        {/* 아래: 정보 섹션 카드 4개 — 전체 폭(목업 `.section-cards-wrap`).
            ① 신뢰정보 — TrustInfoSection이 뱃지·긴 면책을 한 몸으로 그린다(Story 10.2, B9).
               신뢰속성이 전부 없으면(anon 포함) null을 반환해 섹션 자체가 안 그려진다(AC1). */}
        <TrustInfoSection listing={listing} />

        {/* ② 차량정보 */}
        <VehicleInfoSection listing={listing} />

        {/* ③ 옵션 — 카테고리 분류·희소옵션 강조는 Epic 10.3/10.4의 몫이다. */}
        <OptionsSection listing={listing} />

        {/* ④ 판매자정보 — 닉네임+가입 시점+다른 매물 N건 3행(FR56, Story 10.6) + 문의 버튼.
            값이 하나도 없으면 null을 반환해 섹션 자체가 안 그려진다(①과 동일 규칙). */}
        <SellerInfoSection
          sellerName={listing.seller_name}
          joinedAt={sellerSummaryError ? null : sellerSummary?.joined_at}
          otherOnSaleCount={sellerSummaryError ? null : sellerSummary?.other_on_sale_count}
          action={
            <SellerInquiryButton mode={inquiryMode} listingId={listing.id} loginHref={loginHref} />
          }
        />
      </main>
    </>
  );
}
