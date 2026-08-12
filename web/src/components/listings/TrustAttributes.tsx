// 신뢰 뱃지/상태칩 컴포넌트 — 카드(②)·상세(①) 공유 (Story 10.2).
//
// 왜 컴포넌트 하나로 묶나(B9 — 면책-뱃지 결속을 구조로 강제, **상세 한정**):
//   상세 페이지는 뱃지가 뜨는데 면책이 빠지면 CM-C(검증됨으로 오도 금지) 위반이다. 이걸 "규칙"이
//   아니라 "문법"으로 막기 위해, 뱃지와 면책을 이 한 컴포넌트가 **같은 반환값**으로 emit한다. 호출부
//   (ListingCard·TrustInfoSection)는 <TrustAttributes/> 하나만 꽂으므로 "호출부가 면책만 빼고
//   조립하는" 경로는 코드상 존재할 수 없다 — 다만 이 컴포넌트 **내부**에서 면책 JSX 노드를
//   실수로 지우는 경로까지 문법이 막아주지는 않는다(그건 이 파일이 스스로 깨질 수 있는 자리다).
//   그래서 결속을 두 계층에서 검사로 고정한다(TrustAttributes.test.ts): ① 데이터 계층 —
//   getTrustDisplay()가 뱃지 배열·면책 문자열을 같은 반환 객체로 내는지. ② 렌더 계층 — 컴포넌트를
//   함수로 직접 호출해 얻은 React 엘리먼트 트리에 면책 텍스트가 실제로 있는지(①만으로는 컴포넌트
//   JSX에서 면책 <p>를 지워도 못 잡는다 — 코드리뷰 2026-07-22 P1이 지적, red/green 실측 완료).
//   ⚠️ **카드는 더 이상 이 결속 대상이 아니다(사용자 승인, 2026-08-05)** — "판매자 제공 정보"
//   면책을 카드에서 뺐다. 사진 위에 겹치는 좁은 공간에 면책 한 줄까지 넣으면 뱃지·사진 둘 다
//   읽기 어려웠고, 같은 면책은 상세 페이지(TrustInfoSection)에 이미 있다. getTrustDisplay는 두
//   variant 모두 같은 disclaimer 문자열을 반환하지만(데이터 계층은 그대로 두어 변경 폭을 줄임),
//   카드 렌더는 그 값을 쓰지 않는다.
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

// 표시 자리 3종. 'detail'=상세 아래 "신뢰정보" 카드(긴 면책), 'summary'=상세 요약 컬럼(짧은 면책),
// 'card'=목록 카드(사진 위 뱃지만, 면책 렌더 안 함).
export type TrustVariant = 'card' | 'detail' | 'summary';

const DISCLAIMER_DETAIL =
  '판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요.'; // UX-DR19

// 상세 **요약 컬럼**용 짧은 면책 — 목업 detail-1.html의 `.trust-disclaimer-sm` 원문(2026-08-13 #2).
// 같은 화면 아래쪽 "신뢰정보" 카드가 위 긴 문구를 그대로 다시 보여주므로, 좁은 요약 컬럼에서는
// 한 줄짜리를 쓴다. **문구가 짧아졌을 뿐 "뱃지엔 반드시 면책이 딸려 나온다"는 결속은 그대로다**
// (getTrustDisplay가 여전히 한 반환값으로 둘을 함께 낸다 — 이 파일 상단 B9 주석).
const DISCLAIMER_SUMMARY = '판매자 제공 정보 · 차장님이 검증한 정보가 아닙니다';

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
 * 면책-뱃지 결속의 실제 자리(B9, 상세 한정 — 위 파일 상단 주석 참조). 뱃지가 하나라도 있으면
 * 반드시 면책 문구를 함께 반환한다 — 이 함수를 거치지 않고 뱃지만 그리는 경로가 없다
 * (TrustAttributes 컴포넌트가 이 결과만 렌더). 뱃지가 0개면 null(카드·상세 모두 아무것도
 * 렌더하지 않는다, AC1·AC3).
 */
export function getTrustDisplay(
  listing: TrustAttributesInput,
  // 'card'는 데이터 계층에서만 면책을 들고 있고 렌더는 쓰지 않는다(2026-08-05 카드 면책 제거).
  // 'summary'는 상세 요약 컬럼 — 같은 결속을 유지하되 짧은 문구를 쓴다(2026-08-13 #2).
  variant: TrustVariant,
): TrustDisplay | null {
  const badges = getTrustBadges(listing);
  if (badges.length === 0) return null;
  return {
    badges,
    disclaimer: variant === 'summary' ? DISCLAIMER_SUMMARY : DISCLAIMER_DETAIL,
  };
}

// 톤별 뱃지 클래스 — variant에 따라 배경이 갈린다(사용자 요구, 2026-08-05).
//   card: 사진 위에 절대배치로 겹치므로 반투명 배경 + backdrop-blur로 사진을 너무 가리지 않으면서
//     글자 대비를 확보한다("N장" 배지, ListingCardImage.tsx의 supports-[backdrop-filter]:backdrop-blur-sm
//     관례를 그대로 따름). 배경은 라이트/다크 테마와 무관하게 **고정 hex**를 쓴다 — trust-green-*
//     디자인 토큰은 테마에 따라 스왑되는데(다크에서 밝은 초록으로 뒤집힘 — "어두운 페이지 배경 위
//     글자색" 용도라서), 사진은 테마를 따라 바뀌지 않으니 그 토큰을 배경으로 쓰면 다크 모드에서
//     옅은 초록 배경 위 흰 글자로 대비가 무너진다. "N장" 배지가 bg-black 고정색을 쓰는 것과 같은 이유.
//     ⚠️ 불투명도 이력(사용자 요구, 2026-08-05): 85%/70%(1차) → 70%/55%(2차) → **45%/35%(3차)**.
//     2차가 "달라진 게 없어 보인다"는 피드백을 받아 확 낮췄다. 되돌릴 땐 이 줄의 이력대로
//     `bg-[#1B6E3D]/<n>`·`bg-black/<n>` 두 값만 바꾸면 된다(다른 곳은 안 건드려도 됨).
//     대신 흐림을 `backdrop-blur-sm`(4px) → `md`(12px) → **`lg`(16px)** 로 같이 올린다 — 배경을
//     더 비치게 하면서 가독성을 지키려면 "투명도"와 "흐림"을 반대 방향으로 함께 움직여야 한다.
//     흐림 미지원 브라우저에서는 불투명도만 적용되므로(supports-[] 가드) 그때 대비가 가장
//     약해진다 — 그래서 흰 글자 + semibold + 텍스트 그림자를 남겨 최저선을 지킨다.
//   detail: 문서 흐름 안이라 기존 불투명 톤(디자인 토큰)을 그대로 쓴다.
function badgeClassName(tone: 'green' | 'neutral', variant: TrustVariant): string {
  if (variant === 'card') {
    return tone === 'green'
      ? 'inline-flex items-center gap-1 rounded-badge bg-[#1B6E3D]/45 px-2 py-0.5 text-caption font-semibold text-white [text-shadow:0_1px_2px_rgb(0_0_0/0.55)] supports-[backdrop-filter]:backdrop-blur-lg'
      : 'inline-flex items-center rounded-badge bg-black/35 px-2 py-0.5 text-caption font-medium text-white [text-shadow:0_1px_2px_rgb(0_0_0/0.55)] supports-[backdrop-filter]:backdrop-blur-lg';
  }
  return tone === 'green'
    ? 'inline-flex items-center gap-1 rounded-badge bg-trust-green-bg px-2 py-0.5 text-caption font-semibold text-trust-green-ink'
    : 'inline-flex items-center rounded-badge border border-border-hairline px-2 py-0.5 text-caption font-medium text-ink-secondary';
}

export default function TrustAttributes({
  listing,
  variant,
}: {
  listing: TrustAttributesInput;
  variant: TrustVariant;
}) {
  const display = getTrustDisplay(listing, variant);
  if (!display) return null;

  const badges = display.badges.map((badge) => (
    <span key={badge.key} className={badgeClassName(badge.tone, variant)}>
      {/* 비색 신호 중복(접근성) — 초록 뱃지는 색만이 아니라 ✓ 아이콘 + 텍스트로도 표기. */}
      {badge.tone === 'green' && <span aria-hidden="true">✓</span>}
      {badge.label}
    </span>
  ));

  if (variant === 'card') {
    // 카드: 사진 위 좌상단에 절대배치로 겹친다(사용자 승인, 2026-08-05) — 신뢰속성 유무와
    // 무관하게 카드 본문 높이를 항상 같게 유지하려고 본문 흐름 밖으로 뺐다(예전엔 값이 없으면
    // 이 컴포넌트가 null을 반환해 슬롯 자체가 사라지며 카드 높이가 들쭉날쭉했다).
    // WishButton의 카드 배치(WishButton.tsx variant='card')와 같은 패턴 — 사진 박스
    // (aspect-[5/3])를 그대로 재현한 감싸개 안에서 좌상단에 건다. 찜 버튼은 그 박스
    // **아래쪽**(top-full)에 걸리므로 겹치지 않는다. left-2·right-2 양쪽을 다 고정해 뱃지가
    // 3개(무사고·1인소유·비흡연) 다 있어도 사진 폭을 넘지 않고 flex-wrap으로 줄바꿈된다.
    return (
      <div className="pointer-events-none absolute inset-x-0 top-0 aspect-[5/3]">
        <div className="absolute left-2 right-2 top-2 flex flex-wrap items-center gap-1.5">
          {badges}
        </div>
      </div>
    );
  }

  // 상세('detail')와 요약('summary'): 칩 행 아래 면책 문구를 별도 줄로. 문구 길이만 다르다(위 상수).
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-1.5">{badges}</div>
      <p className="text-meta text-ink-muted">{display.disclaimer}</p>
    </div>
  );
}
