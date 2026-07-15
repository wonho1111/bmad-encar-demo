// 웹 측 공유 상수 — docs/conventions.md(단일 출처)와 값이 일치해야 한다.
// 값이 바뀌면 conventions.md를 먼저 고치고 여기에 반영한다.

/**
 * 임베딩 차원. gemini-embedding-001(768) ↔ pgvector vector(768)과 반드시 일치.
 * 불일치 시 AI 검색이 동작하지 않는다. (근거: docs/conventions.md §1)
 */
export const EMBEDDING_DIM = 768 as const;

/** 매물 상태 enum (DB CHECK와 일치). */
export const LISTING_STATUS = {
  ON_SALE: 'on_sale',
  SOLD: 'sold',
} as const;
export type ListingStatus = (typeof LISTING_STATUS)[keyof typeof LISTING_STATUS];

/** 회원 상태 enum (profiles.status CHECK와 일치 — 0001_profiles.sql). 관리자 회원 관리(6-2)에서 사용. */
export const PROFILE_STATUS = {
  ACTIVE: 'active',
  SUSPENDED: 'suspended',
} as const;
export type ProfileStatus = (typeof PROFILE_STATUS)[keyof typeof PROFILE_STATUS];

/** 사용자 역할 enum (profiles.role CHECK와 일치). */
export const USER_ROLE = {
  BUYER: 'buyer',
  SELLER: 'seller',
  ADMIN: 'admin',
} as const;
export type UserRole = (typeof USER_ROLE)[keyof typeof USER_ROLE];

/** 역할(영문 값) → 화면 표시용 한국어 라벨. 홈·관리자 상단바가 공유하는 단일 출처. */
export const ROLE_LABEL: Record<UserRole, string> = {
  [USER_ROLE.BUYER]: '구매자',
  [USER_ROLE.SELLER]: '판매자',
  [USER_ROLE.ADMIN]: '관리자',
};

/** 수치 필드 저장 단위 (표시·검색 전 구간 동일, docs/conventions.md §3). */
export const UNITS = {
  mileage: 'km',
  price: '원',
  displacement: 'cc',
} as const;

/**
 * 매물 고정 목록 6필드의 허용값 (드롭다운 옵션 단일 출처).
 *
 * ⚠️ 단일 출처 = `supabase/migrations/0002_listings.sql`의 CHECK 목록 + architecture.md 확정표.
 *    값·순서·문자를 **그대로(바이트 단위 일치)** 복사한다. 여기와 DB가 어긋나면(drift) 폼에서 고른 값이
 *    DB CHECK에 걸려 거절되거나, 반대로 막아야 할 값이 통과한다. 값이 바뀌면 마이그레이션을 먼저 고치고 여기 반영.
 *    (이 미러링은 Story 2-1 코드리뷰에서 2-2로 defer된 항목이다.)
 */
export const LISTING_OPTIONS = {
  manufacturer: [
    '현대', '기아', '제네시스', '쉐보레', '르노코리아', 'KG모빌리티',
    'BMW', '벤츠', '아우디', '폭스바겐', '토요타', '혼다', '렉서스', '테슬라', '기타',
  ],
  body_type: [
    '경차', '소형차', '준중형차', '중형차', '대형차', '스포츠카',
    'SUV', 'RV', '경승합차', '승합차', '화물차', '기타',
  ],
  color: ['흰색', '검정', '회색', '은색', '파랑', '빨강', '갈색', '녹색', '기타'],
  fuel: ['가솔린', '디젤', '하이브리드', '전기', 'LPG'],
  transmission: ['자동', '수동'],
  region: [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주',
  ],
} as const;

/**
 * 매물 수치 필드의 허용 범위 (DB CHECK와 일치 — 폼 클라이언트 검증·표시에 공유).
 * year/seats는 상·하한, 나머지는 0 이상. (근거: 0002_listings.sql CHECK)
 */
export const LISTING_RANGES = {
  year: { min: 1990, max: new Date().getFullYear() + 1 }, // 상한=올해+1(신차년식). DB CHECK: year <= extract(year from now())::int + 1
  seats: { min: 2, max: 11 }, // seats between 2 and 11
  price: { min: 0 }, // 원, 음수 불가 (bigint)
  mileage: { min: 0 }, // km, 음수 불가
  displacement: { min: 0 }, // cc, 전기차 0 허용
} as const;

/**
 * 채팅 메시지 제약 (DB CHECK와 일치 — 입력창 maxLength·전송 가드에 공유).
 * (근거: 0010_chat_message_length.sql, docs/conventions.md §7, 기술부채 #8)
 */
export const CHAT = {
  MESSAGE_MAX_LENGTH: 2000, // 본문 최대 글자 수(trim 후). DB CHECK: char_length(body) <= 2000
} as const;
