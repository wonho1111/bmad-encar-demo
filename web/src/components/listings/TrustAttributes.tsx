// 신뢰 뱃지/상태칩 + "판매자 제공 정보" 면책 — 카드(②)·상세(①) 공유 컴포넌트 (Story 10.2).
//
// 왜 컴포넌트 하나로 묶나(B9 — 면책-뱃지 결속을 구조로 강제):
//   뱃지가 뜨는데 면책이 빠지는 화면은 CM-C(검증됨으로 오도 금지) 위반이다. 이걸 "규칙"이 아니라
//   "문법"으로 막기 위해, 뱃지와 면책을 이 한 컴포넌트가 **같은 반환값**으로 emit한다. 호출부
//   (ListingCard·TrustInfoSection)는 <TrustAttributes/> 하나만 꽂으므로 "호출부가 면책만 빼고
//   조립하는" 경로는 코드상 존재할 수 없다 — 다만 이 컴포넌트 **내부**에서 면책 JSX 노드를
//   실수로 지우는 경로까지 문법이 막아주지는 않는다(그건 이 파일이 스스로 깨질 수 있는 자리다).
//   그래서 결속을 두 계층에서 검사로 고정한다(TrustAttributes.test.ts): ① 데이터 계층 —
//   getTrustDisplay()가 뱃지 배열·면책 문자열을 같은 반환 객체로 내는지. ② 렌더 계층 — 컴포넌트를
//   함수로 직접 호출해 얻은 React 엘리먼트 트리에 면책 텍스트가 실제로 있는지(①만으로는 컴포넌트
//   JSX에서 면책 <span>/<p>를 지워도 못 잡는다 — 코드리뷰 2026-07-22 P1이 지적, red/green 실측
//   완료). 두 계층 다 지키므로 "뱃지만 있고 면책이 빠지는 화면"이 조용히 배포되는 경로는 없다.
//
// 색 규칙(§4·epic-10-context, docs/conventions.md §4 계약-외 값 정규화):
//   accident_status='무사고'만 초록 신뢰 뱃지. '단순교환'·'사고'는 초록이 아닌 가치중립 상태칩
//   (amber 금지 — 가격/CTA 전용색). is_single_owner/is_non_smoker는 true일 때만 초록 칩,
//   null·false는 "아님"으로 단정하지 않고 미표시. 계약-외 값(3값 밖·빈 문자열)은 null과 동일 취급.
//
// 상태 없는 컴포넌트(서버 렌더 가능).
export type TrustAttributesInput = {
  accident_status?: '무사고' | '단순교환' | '사고' | null;
  is_single_owner?: boolean | null;
  is_non_smoker?: boolean | null;
};

type TrustBadge = {
  key: string;
  label: string;
  tone: 'green' | 'neutral';
};

export type TrustDisplay = {
  badges: TrustBadge[];
  disclaimer: string;
};

const DISCLAIMER_CARD = '판매자 제공 정보';
const DISCLAIMER_DETAIL =
  '판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요.'; // UX-DR19

// accident_status 계약-외 값 정규화(conventions §4): 3값 밖(빈 문자열 포함)이면 null과 동일.
const VALID_ACCIDENT_STATUSES = new Set(['무사고', '단순교환', '사고']);

// 표시할 뱃지 목록을 계산한다 — 이 함수의 "무엇을 그릴지" 판단과 아래 getTrustDisplay의
// "면책을 반드시 딸려 보낸다" 판단이 분리돼 있어야 결속을 단위테스트로 잡을 수 있다.
function getTrustBadges(listing: TrustAttributesInput): TrustBadge[] {
  const badges: TrustBadge[] = [];

  const accidentStatus = listing.accident_status;
  if (typeof accidentStatus === 'string' && VALID_ACCIDENT_STATUSES.has(accidentStatus)) {
    badges.push(
      accidentStatus === '무사고'
        ? { key: 'accident', label: '무사고', tone: 'green' }
        : { key: 'accident', label: accidentStatus, tone: 'neutral' },
    );
  }

  // is_single_owner/is_non_smoker: true일 때만 칩. null·false는 "아님"으로 그리지 않는다(미표시).
  if (listing.is_single_owner === true) {
    badges.push({ key: 'single-owner', label: '1인소유', tone: 'green' });
  }
  if (listing.is_non_smoker === true) {
    badges.push({ key: 'non-smoker', label: '비흡연', tone: 'green' });
  }

  return badges;
}

/** 카드·상세 호출부가 "그릴 게 있는지"만 물을 때 쓴다(빈 슬롯 렌더 방지, AC1). */
export function hasTrustAttributes(listing: TrustAttributesInput): boolean {
  return getTrustBadges(listing).length > 0;
}

/**
 * 면책-뱃지 결속의 실제 자리(B9). 뱃지가 하나라도 있으면 반드시 면책 문구를 함께 반환한다 —
 * 이 함수를 거치지 않고 뱃지만 그리는 경로가 없다(TrustAttributes 컴포넌트가 이 결과만 렌더).
 * 뱃지가 0개면 null(카드·상세 모두 아무것도 렌더하지 않는다, AC1·AC3).
 */
export function getTrustDisplay(
  listing: TrustAttributesInput,
  variant: 'card' | 'detail',
): TrustDisplay | null {
  const badges = getTrustBadges(listing);
  if (badges.length === 0) return null;
  return {
    badges,
    disclaimer: variant === 'card' ? DISCLAIMER_CARD : DISCLAIMER_DETAIL,
  };
}

export default function TrustAttributes({
  listing,
  variant,
}: {
  listing: TrustAttributesInput;
  variant: 'card' | 'detail';
}) {
  const display = getTrustDisplay(listing, variant);
  if (!display) return null;

  const badges = display.badges.map((badge) => (
    <span
      key={badge.key}
      className={
        badge.tone === 'green'
          ? 'inline-flex items-center gap-1 rounded-badge bg-trust-green-bg px-2 py-0.5 text-caption font-semibold text-trust-green-ink'
          : 'inline-flex items-center rounded-badge border border-border-hairline px-2 py-0.5 text-caption font-medium text-ink-secondary'
      }
    >
      {/* 비색 신호 중복(접근성) — 초록 뱃지는 색만이 아니라 ✓ 아이콘 + 텍스트로도 표기. */}
      {badge.tone === 'green' && <span aria-hidden="true">✓</span>}
      {badge.label}
    </span>
  ));

  if (variant === 'card') {
    // 카드: 사진 바로 아래 한 줄 — 칩들 + 짧은 면책(11px 톤다운)이 같은 행에 나란히.
    // pr-14(56px): 이 행이 정보 영역의 첫 줄이라 우상단 찜 버튼(44px+오프셋)과 같은 높이에 걸린다
    // (ListingCard.tsx가 차량명·meta에 두는 것과 같은 여백 — 없으면 면책 글자가 버튼 아래로 가려진다).
    return (
      <div className="flex flex-wrap items-center gap-1.5 pr-14">
        {badges}
        <span className="text-[11px] text-ink-muted">{display.disclaimer}</span>
      </div>
    );
  }

  // 상세: 칩 행 아래 전체 면책 문구(UX-DR19)를 별도 줄로.
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">{badges}</div>
      <p className="text-meta text-ink-muted">{display.disclaimer}</p>
    </div>
  );
}
