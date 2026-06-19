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
