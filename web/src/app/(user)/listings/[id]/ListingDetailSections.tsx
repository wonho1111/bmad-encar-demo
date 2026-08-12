// 구매자 상세의 **정보 섹션**(차량정보 · 옵션) — 이 라우트 전용 표시부 (Story 9.5 AC1·AC5).
//
// ⚠️ **왜 `components/listings/ListingDetailFields.tsx`를 고치지 않고 새로 만들었나 (AC10).**
//   저 컴포넌트는 **관리자 매물 상세와 공유**한다(`(admin)/admin/listings/[id]/page.tsx`).
//   구매자 상세만 섹션 순서를 바꾸고 디자인 토큰을 입히는데 공유 컴포넌트를 제자리에서 뒤집으면,
//   이 스토리 범위 밖인 **관리자 화면이 함께 바뀐다**(관리자 리스킨은 Epic 15의 몫이다).
//   그래서 구매자 전용 레이아웃을 이 라우트 폴더에 두고, 공유 컴포넌트는 관리자가 계속 쓰게 둔다.
//   두 화면이 잠시 다른 마크업을 갖는 것은 **의도된 상태**이며, Epic 15가 관리자를 같은 토큰으로
//   올릴 때 합류 여부를 판단한다.
//
// 상태 없는 서버 컴포넌트다(표시만 한다). 값 채우기·조회는 page.tsx의 책임.
import { UNITS } from '@/lib/constants';
import TrustAttributes, { hasTrustAttributes } from '@/components/listings/TrustAttributes';
import { groupByCategory, OPTION_CATEGORY_ORDER } from '@/lib/options';

// FR5 15필드 중 **본문에 쓰는 값**(seller_id·status 등 페이지 로직용 필드는 제외).
// 15필드 내역 = 이 표 13행 + 옵션 + 설명. seller_name은 FR5 15필드 **밖**이다
// (0007이 넣은 비정규화 표시값 — 값이 없으면 행 자체를 숨긴다).
export type ListingDetailSectionsData = {
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
  seller_name?: string | null;
  options: string[] | null; // text[]; 빈 배열·null 가능
  description: string | null; // nullable
  // 신뢰속성 3필드(Story 10.2) — anon은 select에서 아예 안 물으므로 undefined로 올 수 있다.
  // TrustAttributes/hasTrustAttributes는 undefined도 null과 동일하게 처리한다(계약-외 정규화).
  accident_status?: '무사고' | '단순교환' | '사고' | null;
  is_single_owner?: boolean | null;
  is_non_smoker?: boolean | null;
};

/** 섹션 껍데기 — 4개 섹션이 같은 카드 표면·제목 위계를 갖게 한 자리에 모은다. */
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-card border border-border-hairline bg-surface-raised p-5 shadow-card dark:shadow-none">
      <h2 className="text-section font-bold text-ink-primary">{title}</h2>
      {children}
    </section>
  );
}

// 라벨-값 한 줄. **가로 배치를 유지한다** — 폭이 좁아도 세로로 접지 않고, 값이 길면 …로 자른다(D5).
function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-4 border-b border-border-hairline py-2 last:border-0">
      <span className="shrink-0 whitespace-nowrap text-meta font-medium text-ink-muted">{label}</span>
      {/* title=value(#79 ③, 코드리뷰 2026-07-22 P5로 문구 정정) — `title`은 **마우스 hover에서만**
          잘린 텍스트를 보여준다(비focusable `<span>`이라 키보드 포커스로는 안 뜬다 — 새 포커스
          장치는 이 스토리 범위 밖). `truncate`는 CSS 시각 자름일 뿐 DOM엔 전체 값이 그대로 있으므로
          스크린리더는 잘림과 무관하게 전체 텍스트를 읽는다 — 정보가 사라지는 건 "마우스 없는 화면
          잘림"뿐이고, 그 한 가지만 title이 보완한다. */}
      <span className="truncate text-body font-medium text-ink-primary" title={value}>
        {value}
      </span>
    </div>
  );
}

/**
 * ① 신뢰정보 — TrustAttributes(뱃지+면책, B9)를 "신뢰정보" 섹션 카드에 담는다(Story 10.2).
 *
 * ✎ 2026-08-13 사용자 지적 — **값이 없어도 섹션은 그린다.** 예전엔 신뢰속성이 하나도 없으면
 *   `null`을 반환해 섹션이 통째로 사라졌는데(Story 9.5 AC1 "빈 섹션 금지"), 그러면 구매자
 *   입장에서 "이 차는 무사고인가?"라는 질문에 화면이 **아무 말도 안 하는** 상태가 된다.
 *   빈 제목만 남기는 것과 "왜 없는지 말해 주는 것"은 다르다 — 후자는 정보다.
 *
 * ⚠️ **"없음"의 이유를 두 가지로 구분한다. 합치면 거짓말이 된다.**
 *   · 로그인 사용자에게 값이 없다 → 진짜로 판매자가 입력을 안 한 것이다.
 *   · **비로그인(anon)은 애초에 이 3개 컬럼을 조회하지 않는다**(page.tsx의 trustColumns 분기 —
 *     0011 마이그레이션이 anon에게 연 컬럼 목록에 그 셋이 없어서, 넣으면 select 전체가 42501로
 *     실패한다). 즉 anon 화면의 "없음"은 **판매자가 입력을 안 했다는 뜻이 아니다.** 그래서
 *     anon에게 "판매자가 입력하지 않았어요"라고 쓰면 값이 있는 매물에도 그렇게 보인다.
 *     (anon에게도 보이게 하려면 GRANT 마이그레이션이 필요하다 — 사용자 승인 대기, DW-836.)
 */
export function TrustInfoSection({
  listing,
  authed,
}: {
  listing: ListingDetailSectionsData;
  // 비로그인이면 신뢰속성 3컬럼을 조회 자체를 안 했다는 뜻(위 주석) — "없음"의 문구가 갈린다.
  authed: boolean;
}) {
  if (hasTrustAttributes(listing)) {
    return (
      <Section title="신뢰정보">
        <TrustAttributes variant="detail" listing={listing} />
      </Section>
    );
  }

  return (
    <Section title="신뢰정보">
      {authed ? (
        <p className="text-body text-ink-muted">
          판매자가 무사고·1인소유·비흡연 여부를 입력하지 않았어요. 계약 전 직접 확인하세요.
        </p>
      ) : (
        <p className="text-body text-ink-muted">
          무사고·1인소유·비흡연 정보는 로그인 후에 볼 수 있어요.
        </p>
      )}
    </Section>
  );
}

/** ② 차량정보 — FR5 표 13행(+판매자 표시명) + 설명. 필드를 새로 만들지도, 빼지도 않는다(AC5). */
export function VehicleInfoSection({ listing }: { listing: ListingDetailSectionsData }) {
  // 단위·표시 규칙(conventions §3): 천단위 콤마 + 단위.
  const mileageText = `${listing.mileage.toLocaleString('ko-KR')}${UNITS.mileage}`;
  const displacementText = `${listing.displacement.toLocaleString('ko-KR')}${UNITS.displacement}`;

  return (
    <Section title="차량정보">
      {/* ✎ 2026-08-13(#2) — 넓은 폭에서 2열로 나눈다(목업 detail-1.html `.spec-table`이
          `grid-template-columns:1fr 1fr`). 예전엔 어느 폭에서든 1열이라, 전체 폭으로 올라온
          이 카드에서 13행이 세로로 길게 늘어져 오른쪽이 통째로 비어 보였다.
          행 자체는 그대로다 — 필드를 새로 만들지도, 빼지도 않는다(AC5). */}
      <div className="flex flex-col sm:grid sm:grid-cols-2 sm:gap-x-8">
        <Field label="제조사" value={listing.manufacturer} />
        <Field label="모델" value={listing.model} />
        <Field label="차종" value={listing.body_type} />
        <Field label="연식" value={`${listing.year}년`} />
        {/* ✎ 2026-08-13 사용자 지적(중복 점검) — "가격" 행을 뺐다. 같은 값이 요약 카드의 대표 가격과
            모바일 하단 고정 바에 이미 있고, 모바일에선 요약 카드가 이 표 바로 위로 내려와 **같은
            숫자를 연달아 세 번** 보게 된다. 목업 detail-1.html의 `.spec-table`에도 가격 행은 없다
            (가격은 요약 컬럼의 몫). Story 9.5 AC5("필드를 빼지 않는다")보다 이 지적이 나중이다. */}
        <Field label="주행거리" value={mileageText} />
        <Field label="색상" value={listing.color} />
        <Field label="연료" value={listing.fuel} />
        <Field label="변속기" value={listing.transmission} />
        <Field label="배기량" value={displacementText} />
        <Field label="승차인원" value={`${listing.seats}인승`} />
        <Field label="지역" value={listing.region} />
        <Field label="사고이력" value={listing.accident_free ? '무사고' : '사고이력 있음'} />
        {/* 판매자 표시 이름(있을 때만) — 등록 시 트리거가 자동 기록한 값(이메일 @앞부분). */}
        {listing.seller_name && <Field label="판매자" value={listing.seller_name} />}
      </div>

      {/* 설명 = 15필드의 하나. 표 행이 아니라 자유 텍스트라 표 아래에 둔다(AC5). */}
      <div className="flex flex-col gap-1 border-t border-border-hairline pt-3">
        <h3 className="text-meta font-medium text-ink-muted">설명</h3>
        {listing.description && listing.description.trim() !== '' ? (
          <p className="whitespace-pre-wrap text-body text-ink-secondary">{listing.description}</p>
        ) : (
          <p className="text-body text-ink-muted">등록된 설명이 없습니다.</p>
        )}
      </div>
    </Section>
  );
}

/**
 * "YYYY년 M월 가입" — 순수 함수(단위테스트 대상, Story 10.6).
 * null·빈 값·파싱 불가한 문자열은 전부 null(행 숨김) — RPC 실패·미조회를 구분하지 않는다.
 */
export function formatSellerJoinDate(joinedAt: string | null | undefined): string | null {
  if (!joinedAt) return null;
  const date = new Date(joinedAt);
  if (Number.isNaN(date.getTime())) return null;
  // KST(Asia/Seoul) 고정 — 서버가 UTC로 도는 실배포에서 `date.getFullYear()/getMonth()`(런타임
  // 로컬 타임존)를 쓰면 자정 전후 값이 월을 건너뛴다(예: 2024-02-29T23:00:00Z = KST 2024-03-01
  // 08:00인데 UTC 기준으로 읽으면 "2월"이 된다 — 코드리뷰 2026-07-22 지적). 서비스가 한국
  // 서비스이므로 타임존을 명시로 고정한다(런타임 로컬값에 기대지 않음).
  const parts = new Intl.DateTimeFormat('ko-KR', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: 'numeric',
  }).formatToParts(date);
  const year = parts.find((p) => p.type === 'year')?.value;
  const month = parts.find((p) => p.type === 'month')?.value; // 0패딩 없음(예: "3")
  if (!year || !month) return null;
  return `${year}년 ${month}월 가입`;
}

/**
 * "이 판매자의 다른 판매중 매물 N건" — 순수 함수(단위테스트 대상, Story 10.6).
 * count가 null/undefined(RPC 실패)면 null(행 숨김). 0이면 "없어요" 안내 문구로 분기한다(I/O 매트릭스).
 */
export function sellerOtherListingsLabel(count: number | null | undefined): string | null {
  if (count === null || count === undefined) return null;
  if (count <= 0) return '이 판매자의 다른 판매중 매물이 없어요.';
  return `이 판매자의 다른 판매중 매물 ${count.toLocaleString('ko-KR')}건`;
}

/**
 * ④ 판매자정보 — 닉네임(`seller_name`, 0007 비정규화 재사용) + 가입 시점 + "다른 판매중 매물 N건"
 * 3가지만 노출한다(FR56, 평판·응답률·인증 배지 등 데이터 없는 지표는 절대 표시하지 않음).
 * 값이 하나도 없으면(닉네임 null + RPC 실패) 섹션 자체를 그리지 않는다(AC1과 동일한 "빈 섹션 금지" 관례).
 * 가입 시점·집계는 RPC(`get_seller_public_summary`, 0019) 조회 결과를 page.tsx가 그대로 넘긴다 —
 * 조회가 실패하면 page.tsx가 이미 null로 정규화해 넘기므로 이 컴포넌트는 "행 숨김"만 신경 쓴다.
 */
export function SellerInfoSection({
  sellerName,
  joinedAt,
  otherOnSaleCount,
  action,
}: {
  sellerName: string | null | undefined;
  joinedAt: string | null | undefined;
  otherOnSaleCount: number | null | undefined;
  // 카드 맨 아래 문의 버튼(목업 `.seller-contact-btn`) — page.tsx가 <SellerInquiryButton/>을 넣는다.
  // 여기서 직접 부르지 않는 이유: 그 버튼은 클라이언트 컴포넌트이고 3분기 판정(mode)에 서버가
  // 들고 있는 user가 필요하다 — 판정은 page.tsx 한 곳에서만 한다(AC7).
  action?: React.ReactNode;
}) {
  const joinLabel = formatSellerJoinDate(joinedAt);
  const otherLabel = sellerOtherListingsLabel(otherOnSaleCount);

  // ⚠️ 문의 버튼(action)은 이 판정에 넣지 않는다 — 판매자 정보가 하나도 없을 때 "버튼만 있는
  //   판매자정보 카드"가 남으면 그게 더 이상하다(AC1 "빈 섹션 금지"의 취지). 그 경우 문의는
  //   요약 카드·모바일 하단 바 쪽 CTA가 그대로 담당한다.
  if (!sellerName && !joinLabel && !otherLabel) return null;

  return (
    <Section title="판매자정보">
      <div className="flex flex-col gap-1">
        {sellerName && <p className="text-body font-semibold text-ink-primary">{sellerName}</p>}
        {joinLabel && <p className="text-meta text-ink-muted">{joinLabel}</p>}
        {otherLabel && <p className="text-meta text-ink-muted">{otherLabel}</p>}
      </div>
      {action}
    </Section>
  );
}

/**
 * ③ 옵션 — 5개 엔카 카테고리로 전량 그룹핑(희소 필터 없음, Story 10.3).
 * 통제어휘 밖 값은 `기타옵션`으로 폴백된다(groupByCategory, docs/conventions.md §11).
 */
export function OptionsSection({ listing }: { listing: ListingDetailSectionsData }) {
  const grouped = groupByCategory(listing.options);
  const categories = OPTION_CATEGORY_ORDER.filter((category) => (grouped[category]?.length ?? 0) > 0);

  return (
    <Section title="옵션">
      {categories.length === 0 ? (
        <p className="text-body text-ink-muted">등록된 옵션이 없습니다.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {categories.map((category) => (
            <div key={category} className="flex flex-col gap-1.5">
              <h4 className="text-meta font-medium text-ink-muted">{category}</h4>
              <ul className="flex flex-wrap gap-2">
                {grouped[category]!.map((opt, i) => (
                  <li
                    key={`${opt}-${i}`}
                    className="whitespace-nowrap rounded-chip border border-border-hairline px-2.5 py-1 text-caption font-medium text-ink-secondary"
                  >
                    {opt}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </Section>
  );
}
