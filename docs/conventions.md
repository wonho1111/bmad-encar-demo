# 공유 계약 (Shared Contract) — 단일 출처

> 이 문서는 폴리글랏(Postgres·Python·TypeScript·Dart) 경계를 가로지르는 **공통 규약의 단일 출처**입니다.
> web·app·api 어느 파트든 아래 규칙을 동일하게 따릅니다. 값이 바뀌면 **이 문서를 먼저** 고치고 코드에 반영합니다.
> 근거: `_bmad-output/planning-artifacts/architecture.md` (AR5 일관성 규칙).

## 1. 임베딩 차원 (Embedding Dimension)

- **`768` 고정.** 임베딩 모델 `gemini-embedding-001`(출력 768) ↔ pgvector `vector(768)` ↔ 생성·저장·검색 전 구간 **반드시 일치**.
- 불일치 시 AI 검색이 동작하지 않는다. 환경변수 `GEMINI_EMBEDDING_DIM=768`(api 전용)·`web/src/lib/constants.ts`의 `EMBEDDING_DIM`이 같은 값을 가리킨다.
- 정합 점검 스크립트: `scripts/check-embedding-dim.ps1` (실제 Gemini 응답 차원 확인 — Epic 4 시점 사용).

## 2. 통신선 네이밍 (Wire Naming) — snake_case

- **DB 컬럼·JSON 페이로드는 모두 `snake_case`.** (예: `seller_id`, `created_at`, `body_type`)
- 변환이 불필요하도록 Postgres ↔ Pydantic ↔ Supabase 반환을 일치시킨다.
- 코드 *내부* 표현은 각 언어 관례를 따른다:
  - TS(web): 통신선 `seller_id` → 코드 내부 `sellerId`로 매핑.
  - Dart(app): 통신선 `seller_id` → 모델 필드 `sellerId`.
  - Python(api): 통신선 그대로 `seller_id` (snake_case라 변환 불필요).
- ❌ 금지: JSON에 `sellerId`를 직접 노출 (Supabase 반환과 불일치 → 매핑 버그).

## 3. 단위·측정 규칙 (Units)

전 구간(저장·입력·검색·AI Text-to-SQL·표시)에서 수치 필드 단위를 고정한다. 단위 미명시 금지.

| 필드 | 저장 단위 | 표시 예 | 자연어 허용 | 비고 |
|------|-----------|---------|-------------|------|
| `mileage` (주행거리) | 정수 **km** | `103,000km` | "약 10만km" | **mile/마일 금지** |
| `price` (가격) | 정수 **원(KRW)** | `29,800,000원` | "2,980만원" | 음수 불가 |
| `displacement` (배기량) | 정수 **cc** | `1,998cc` | — | 전기차 0 허용 |
| `year` (연식) | 정수 4자리 연도 | `2021` | — | — |

- AI Text-to-SQL은 자연어 단위("10만km", "3천만원")를 저장 단위(km·원 정수)로 **정규화**해 비교한다.

## 4. 응답·에러 공통 포맷

- **AI 검색 응답:** `{ "answer": string, "listings": ListingCard[] }`
  - 0건이면 `listings: []` + `answer`에 조건 완화 안내(FR17).
- **ListingCard 필드(snake_case):** `id, manufacturer, model, year, price, mileage, region` (사진 없음 — 썸네일 필드 없음).
- **에러 포맷:** `{ "error": { "code": string, "message": string } }`
  - 사용자 노출 `message`는 한국어, HTTP 상태코드는 정확히(400/401/403/404/422/500).
- **날짜:** ISO 8601 문자열(UTC). **불리언:** `true/false`. **null:** 빈 문자열 대신 명시적 `null`.

## 5. 환경변수 배치 (요약)

상세는 루트 `.env.example` 참조. 핵심 규칙:

- `web/.env.local` — 브라우저 전달값만, `NEXT_PUBLIC_` 접두사 필수 (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- `api/.env` — 서버 전용. **`GEMINI_API_KEY`는 오직 여기에만** 둔다(웹에 절대 넣지 않음). `GEMINI_EMBEDDING_DIM=768`도 여기.
- `app/.env` — Flutter(Epic 7, 나중).
- `service_role` 키는 사용하지 않는다. anon key는 RLS가 보호.

## 6. 판매완료 비노출 (FR11)

- `status='sold'` 매물은 구매자의 **모든 경로**(목록·필터·상세·AI SQL·문서 RAG)에서 노출되지 않는다.
- 강제 지점: RLS(`0002_listings`에 동거) + `api/db/sql_guard.py` + 문서 RAG 결과 필터. (구현은 Epic 2~4)
