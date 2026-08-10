# 공유 계약 (Shared Contract) — 단일 출처

> 이 문서는 폴리글랏(Postgres·Python·TypeScript·Dart) 경계를 가로지르는 **공통 규약의 단일 출처**입니다.
> web·app·api 어느 파트든 아래 규칙을 동일하게 따릅니다. 값이 바뀌면 **이 문서를 먼저** 고치고 코드에 반영합니다.
> 근거: `_bmad-output/planning-artifacts/architecture.md` (AR5 일관성 규칙).
> 배포 순서·부분배포 정합성·롤백은 `docs/deployment-runbook.md` 참조.

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

- **AI 검색 응답:** `{ "answer": string, "listings": ListingCard[], "clarify": ClarifyPayload | null, "narrowed_by": string[] | null }`
  - 0건이면 `listings: []` + `answer`에 조건 완화 안내(FR17).
  - AI 검색 응답 카드(`SearchResponse.listings[]`)는 아래 **ListingCard와 동일한 계약을 공유**한다(별도 카드 타입 없음).
  - `clarify?: { question: string, chips: string[] }`(FR46, Story 13.4) — 서버가 CLARIFY(되묻기) 경로를 타고, **직전까지의 대화가 3턴 미만**일 때만 채워진다. 그 외(다른 라우트, 또는 CLARIFY라도 3턴 이상 진행돼 서버가 결과를 강제 제시한 경우)는 `null`.
    - **세는 것은 "되묻기 횟수"가 아니라 요청에 실린 `context`의 총 턴 수**다(`len(context)//2`, 한 턴 = user+assistant 2개 항목). 앞선 턴이 일반 검색이었어도 카운트에 들어간다 — 즉 `context`가 6개 항목 이상이면 그 요청은 이미 상한 초과다. 클라이언트가 "몇 번 더 물어볼 수 있나"를 자체 계산하려면 이 정의를 그대로 써야 서버와 어긋나지 않는다.
    - **클라이언트는 `clarify !== null`로만 판별한다.** 응답에 `route` 필드는 없다(내부 라우팅 값이라 노출하지 않음 — **13.5가 확정: 노출하지 않음**). 즉 `res.route === 'CLARIFY'` 같은 분기는 성립하지 않는다.
  - `narrowed_by?: string[] | null`(FR47, CR4, Story 13.5) — **REJECT 전용 고정 상수**다. 서버가 REJECT(매물 무관 질의 거절) 경로를 타면 항상 동일한 사유 술어 배열(예: `["price<=30000000", "body_type=SUV", "fuel=전기"]`, CR4 저장단위 정규화 형식)로 채워진다 — `query`나 대화 맥락을 읽어 값을 바꾸지 않는다(무상태·결정론, CLARIFY의 `chips`와 동일 철학). REJECT가 아닌 다른 라우트(SQL/HYBRID/CLARIFY)는 `null`. 클라이언트는 `narrowed_by !== null`로 REJECT 여부를 판별할 수 있다(별도 `route` 노출 불필요) — ⚠️ **단, 이 판별자는 `narrowed_by`가 REJECT 전용인 동안에만 유효하다.** SQL/HYBRID 0건 응답까지 이 필드를 확장하는 안이 별도로 열려 있고(DW-598), 그것이 채택되는 순간 이 판별자는 깨진다. 확장하는 쪽이 이 줄과 소비처를 **함께** 고쳐야 한다(그때는 판별 수단을 따로 마련한다). 이 배열을 탭 가능한 "재제안 칩" UI로 렌더하는 것은 이번 스토리 범위가 아니다(값만 배선, `clarify.chips`와 동일한 경계 — DW-587 선례).
    - **빈 배열(`[]`)은 "채워진 값"이 아니다 — `null`과 동일하게 취급한다.** 서버는 REJECT일 때 항상 비어 있지 않은 배열을 보내므로 `[]`는 정상 산출물이 아니고, 스키마(`SearchResponse`)도 길이를 강제하지 않는다. 따라서 소비처는 `narrowed_by !== null` 대신 **"비어 있지 않은 문자열 배열인가"**로 판별한다(web `aiSearch.ts`의 `isValidNarrowedBy`가 이 규약을 구현한다 — 형태가 어긋나거나 비면 `null`로 떨군다). DW-598이 이 필드를 0건 응답까지 확장할 때 "조건을 못 뽑았다"를 `[]`로 표현하더라도 이 규약이면 REJECT로 오분류되지 않는다.
- **ListingCard 필드(snake_case):**
  - 기존(필수): `id, manufacturer, model, year, price, mileage, region`
  - 기존(nullable): `seller_name`(판매자 표시 이름, 0007 비정규화 — web/app은 Supabase에서 직접 읽어 노출, api 응답엔 포함되지 않음)
  - 증분 신규(전부 nullable). ✎ 2026-07-20 코드리뷰 정정: 이 머리글은 원래 *"컬럼 자체가 아직 DB에
    없어 **항상 `null`**"*이었으나 더는 사실이 아니다 — **일부는 값이 실제로 채워진다**(아래 "값 채움"
    열이 그 시점이다). 예: `image_path`·`image_count`는 Story 9.6부터 api가 채워 보낸다.
    아직 안 채워진 필드는 그 열에 적힌 에픽이 오기 전까지 `null`이다:
    | 필드 | 타입 | 값 채움 |
    |---|---|---|
    | `image_url` | string\|null (대표 사진의 공개 URL) | Epic 9 |
    | `image_path` | string\|null (대표 사진의 **버킷 상대 경로** — AI 응답 wire 전용, 아래 주석) | Epic 9 (9.6) |
    | `image_count` | int\|null | Epic 9 |
    | `view_count` | int\|null | Epic 11 |
    | `fuel` | string\|null (연료 — `listings.fuel`, 카드 meta `주행·연료·지역` 3요소 중 하나) | Epic 10 (10.1) |
    | `accident_status` | `'무사고'\|'단순교환'\|'사고'`\|null | Epic 10 (10.1 컬럼 생성) |
    | `is_single_owner` | bool\|null | Epic 10 (10.1 컬럼 생성) |
    | `is_non_smoker` | bool\|null | Epic 10 (10.1 컬럼 생성) |
    | `options` | string[]\|null (장비 통제어휘 배열) | Epic 10 (10.3) |
  - **`image_path` vs `image_url` — 누가 무엇을 채우나 (Story 9.6):** 둘은 같은 사진을 가리키지만 **채우는 주체가 다르다.**
    - **`/ai/search` 응답(api)**: `image_path`만 채운다. `image_url`은 **항상 `null`**이다 — api는 사진 URL을 만들지 않기 때문이다(§10, `ai_readonly` 최소권한 CR2). 강제 장치: `api/tests/test_storage_signed_url_contract.py`.
    - **Supabase 직접 조회(web·app의 목록·상세)**: `image_path`가 없다. 소비처가 `listing_images`를 직접 읽어 `getPublicUrl`로 `image_url`을 만든다.
    - 따라서 **AI 응답을 받는 클라이언트는 `image_path`를 `getPublicUrl`로 바꿔 `image_url` 자리에 넣은 뒤 `image_path`를 버린다**(web `aiSearch.ts`가 그 자리). 카드 컴포넌트는 `image_url` 하나만 알면 되고, 두 경로의 차이를 몰라도 된다.
  - `image_url`이 null이면 클라가 "사진 준비중" 5:3 플레이스홀더를 렌더하는 것이 **계약의 일부**다. 변형 세트(`thumb`/`card`/`full`)는 클라이언트 렌더 파생이며 wire 계약이 아니다.
  - **찜(wishlist) 여부는 ListingCard wire 필드가 아니다.** "내가 찜했는지"는 사용자별 오버레이라 별도 조회/조인으로 처리한다(계약 오염 방지, Epic 10.5가 구현).
  - **계약-외 값 정규화(소비처 공통 — 값 채우는 Epic 9/10/11이 준수):** 소비처(web·app)의 파싱 관례가 서로 달라(예: Dart는 `is bool` strict, api Pydantic은 lax 강제변환) 같은 행을 다르게 볼 수 있으므로, 렌더 소비처는 아래를 **동일하게** 방어적으로 처리한다 —
    - `image_url`: **`null` 또는 빈 문자열(`""`) 모두** "사진 준비중" 플레이스홀더로 취급한다(빈 URL로 깨진 이미지 렌더 금지).
    - `accident_status`: `'무사고'|'단순교환'|'사고'` **3값 밖(또는 `""`)이면 신뢰 뱃지를 표시하지 않는다**(= `null`과 동일 취급). 초록 뱃지는 `'무사고'`일 때만(project-context 규칙 신뢰속성).
    - `view_count`·`image_count`: **음수는 `0`으로 하한 처리**한다("조회 -3" 등 노출 금지).
    - `is_single_owner`·`is_non_smoker`: `true`/`false`/미상(`null`)의 **3상태**다 — `null`(미상)을 `false`로 오해해 "1인소유 아님"으로 단정하지 않는다.
  - **런타임 가드 범위 주의:** web `isValidListing`(`aiSearch.ts`)은 필수 7필드만 검증하고 신규 nullable 필드는 검증하지 않는다 — 신규 필드를 읽는 렌더 소비처가 위 정규화로 스스로 방어한다.
- **에러 포맷:** `{ "error": { "code": string, "message": string } }`
  - 사용자 노출 `message`는 한국어, HTTP 상태코드는 정확히(400/401/403/404/422/500).
- **날짜:** ISO 8601 문자열(UTC). **불리언:** `true/false`. **null:** 빈 문자열 대신 명시적 `null`.

### 4.1 계약 변경 체크리스트

ListingCard 필드를 추가·변경할 때는 아래를 **동시에** 갱신한다:

1. 이 문서(`docs/conventions.md` §4) — 단일 출처
2. web `ListingCard.tsx`의 `ListingCardData`
3. api `schemas/ai.py`의 `ListingCard`
4. app `listing.dart`의 `ListingCardData`

> **예외 — AI 응답 wire 전용 필드는 2번 자리가 다르다** (✎ 2026-07-20 코드리뷰 추가).
> 화면 카드까지 가지 않고 **매핑 계층에서 소멸하는** 필드(현재 `image_path`)는 web 쪽 자리가
> `ListingCard.tsx`가 아니라 **`web/src/lib/api/aiSearch.ts`의 wire 타입**이다. web이 이 값을
> 공개 URL로 바꿔 `image_url`에 넣고 경로는 버리므로 `ListingCardData`에는 들어가지 않는다(§10).
> 이 예외가 없으면 다음 사람이 `ListingCard.tsx`를 뒤지다 아무것도 못 찾는다.

필드 자리(nullable 계약)뿐 아니라 **실제 값까지 채울 때**는 위 4곳에 더해 `api/app/graph/listing_cards.py`의 `SELECT_COLUMNS`·`api/app/db/sql_guard.py`의 `ALLOWED_COLUMNS`도 락스텝으로 갱신해야 한다(DB 컬럼이 실제로 생긴 시점).

> **락스텝 지점 추가 — 목록 select 문자열 4곳** (✎ 2026-07-22 Story 10.1 코드리뷰 추가, ✎
> 2026-08-08 Story 16.3 코드리뷰가 4번째 지점 추가).
> 위 4곳·`SELECT_COLUMNS`/`ALLOWED_COLUMNS`를 다 갱신해도, **화면이 실제로 그 컬럼을 요청하지
> 않으면** 값은 여전히 화면에 닿지 않는다. 그래서 값을 채우는 시점엔 아래 select 문자열 4곳도
> 함께 갱신한다: web `src/app/page.tsx`(홈 미리보기) · web `src/app/(user)/search/page.tsx`
> (`/search`) · app `listings_repository.dart`의 `fetchListings` · app `wishlist_repository.dart`의
> `wishlistListingColumns`(찜 목록 화면, Story 16.3). 넷 중 하나라도 빠지면 컬럼·타입·
> 프롬프트는 다 갖췄는데 그 화면만 "쿼리 비용은 내지만 표시는 안 되는" 상태가 된다 — 대장
> #67(카드 meta 연료 누락, Story 9.4가 필드는 계약에 넣고 select엔 안 물어 조용히 빠졌던
> 사례)이 이 자리에서 열렸었다.
>
> **락스텝 지점 추가 — 상세 select 문자열 2곳** (✎ 2026-08-08 Story 16.3 코드리뷰 추가). 위
> "목록 select 문자열 4곳"은 목록/카드 화면만 등재한다 — **상세 화면**의 select는 별개
> 자리이고, 이 스토리가 신뢰속성 3컬럼(`accident_status`·`is_single_owner`·`is_non_smoker`)을
> 상세에 처음 물리면서 그 자리가 락스텝 목록에 아예 없던 게 드러났다(코드리뷰 지적). 값을
> 채우는 시점엔 아래 상세 select 2곳도 함께 갱신한다: web `src/app/(user)/listings/[id]/page.tsx`
> (매물 상세) · app `listings_repository.dart`의 `listingDetailColumns`(`fetchListing`·
> `fetchOwnListing`이 공유, Story 16.3). 위 목록 select 4곳과 같은 실패 모드(컬럼·타입은
> 갖췄는데 상세 화면만 표시가 안 됨)가 이 자리에도 그대로 적용된다.

> ⚠️ **anon(비로그인) 열람 경로에 새 컬럼을 노출하려면 GRANT 마이그레이션 + 사용자 승인이
> 별도로 필요하다** (✎ 2026-07-22 Story 10.1 코드리뷰 추가, 사례는 대장 #109). `listings`의
> anon SELECT는 `0011_listings_anon_select.sql`이 **컬럼 단위로 화이트리스트**한다(§8) — 새
> 컬럼을 추가해도 anon엔 기본적으로 안 보인다(의도된 동작, `0011:36-37` 주석). 위 체크리스트를
> 그대로 따라 anon도 여는 화면(예: `/search`)의 select 문자열에 신규 컬럼을 넣으면, 그 컬럼이
> `0011`의 GRANT 목록에 없는 한 **anon 요청 전체**가 `42501 permission denied`로 실패한다
> (그 컬럼만 빠지는 게 아니라 목록 자체가 안 뜬다 — 실측). `0011` 이후 새 마이그레이션으로
> anon에 그 컬럼을 열려면 §9.3 (b) — **델타가 0이어도 "새 컬럼 노출"은 무조건 사용자 승인**이
> 필요하다(승인 없이 dev가 자율로 넓히지 않는다). 승인 전까지는 로그인 여부로 select 문자열을
> 분기해 anon 회귀를 피한다.

> ⚠️ **단, `listings` 테이블 밖에서 오는 값은 이 규칙에서 제외한다** (✎ 2026-07-20 코드리뷰 추가).
> `image_path`·`image_count`는 `listing_images`에서 **별도 고정쿼리**로 붙는다(§10.2). 이 값들
> 때문에 `SELECT_COLUMNS`를 늘리면 안 되고(7튜플 매핑이 깨진다), **`ALLOWED_COLUMNS`에
> `storage_path`를 넣는 것은 더더욱 안 된다** — 그러면 LLM이 만든 SQL이 사진 테이블에 닿을 수
> 있게 되고, `ai_readonly`의 그 테이블 정책은 `using(true)`라 **sold 사진까지 열려 있어**
> FR11이 그 경로에서 무너진다. `tests/test_sql_guard.py`의 4건이 이 확장을 red로 막는다.
> (이 단서가 없던 동안, 위 규칙을 그대로 따르면 가드를 여는 것이 "규칙 준수"로 읽혔다.)

또한 값을 채우는 에픽은 위 **"계약-외 값 정규화(소비처 공통)"** 규칙을 렌더 코드에 반영한다(빈 문자열 image_url·도메인 밖 accident_status·음수 count·bool 3상태). web `isValidListing`은 신규 필드를 검증하지 않으므로 소비처가 방어적으로 읽어야 한다.

## 5. 환경변수 배치 (요약)

상세는 루트 `.env.example` 참조. 핵심 규칙:

- `web/.env.local` — 브라우저 전달값만, `NEXT_PUBLIC_` 접두사 필수 (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- `api/.env` — 서버 전용. **`GEMINI_API_KEY`는 오직 여기에만** 둔다(웹에 절대 넣지 않음). `GEMINI_EMBEDDING_DIM=768`도 여기.
- `app/.env` — Flutter(Epic 7, 나중).
- `service_role` 키는 사용하지 않는다. anon key는 RLS가 보호.

## 6. 판매완료 비노출 (FR11)

- `status='sold'` 매물은 구매자의 **모든 조회 경로**(목록·필터·상세·AI SQL·문서 RAG)에서 노출되지 않는다.
- 강제 지점:
  - **매물 축** — RLS(authenticated SELECT/INSERT/DELETE = `0002_listings`에 동거, anon = `0011_listings_anon_select`, **authenticated UPDATE = `0015_listings_update_not_sold`**) + `api/db/sql_guard.py` + **문서 RAG 결과 필터**(`api/app/graph/doc_rag_node.py`, 고정 SQL의 `WHERE status = 'on_sale'` 한 줄 — 이 경로는 `sql_guard`를 **거치지 않고**(코드가 고정 SQL을 쓰므로 인젝션 위험이 없어 애초에 안 태운다) `ai_readonly` 롤의 `listings` RLS도 `using(true)`라 행 단위로 안 막는다. 즉 **그 한 줄이 유일한 강제 지점**이다) + **하이브리드 벡터검색**(`api/app/graph/hybrid_rag_node.py`, 코드가 `WHERE status = 'on_sale'` 절을 템플릿으로 붙임 — sql_guard도 거치지만 이 코드 조립이 실제 강제 지점). (구현은 Epic 2~4, anon 경로는 Epic 8.5, 하이브리드는 Story 13.3) 강제 장치: `api/tests/test_hybrid_rag_node.py`(DW-619) · `api/tests/integration/test_doc_rag_node_real_db.py`(문서 RAG 축 — 실 Postgres에 sold/on_sale을 **같은 임베딩**으로 심고 `doc_rag_node()`를 실제 호출해 sold가 안 실리는지 본다. `api-db` CI 잡이 실행).
    - ⚠️ **문서 RAG 축은 SQL 문자열 검사로는 안 지켜진다.** `api/tests/test_doc_rag_node.py`는 생성된 SQL에 `status = 'on_sale'` 글자가 있는지만 보므로, 조건을 `(status = 'on_sale' OR true)`로 **무력화해도 계속 초록**이다(13.8 3차 리뷰 실측). 그래서 실DB 강제 장치를 따로 둔다 — 위 `test_doc_rag_node_real_db.py`.
    - ⚠️ **UPDATE만 0002 밖에 산다.** `0015`가 `listings_update_own`을 drop-recreate하며 `using`에 `status <> 'sold'`를 넣었다(sold 매물 수정 차단, `docs/tech-debt.md` #54). *"authenticated RLS는 전부 0002에 있다"고 읽으면 틀린다* — 코드리뷰 2026-07-21이 락스텝 갱신 누락으로 잡은 자리.
    - ⚠️ **사진 축(`listing_images`)에는 이 조건이 없다** — sold 매물의 사진은 DB가 막지 않는다(`docs/tech-debt.md` #90, 원격 실측 확인).
  - **이미지 축** — `listing_images` RLS(`0012_listing_images`의 `listing_images_select_on_sale_anon` / `listing_images_select_on_sale` — 둘 다 `listings`에 조인해 `l.status = 'on_sale'`을 건다) + 소비처의 id 좁히기.
    - 소비처 목록(**새 조회 경로를 열면 여기에 추가한다**): `attachCoverImages`(목록 카드 — `buyerListingsQuery` 결과의 id만 조회) · `fetchListingGalleryUrls`(상세 갤러리, Story 9.5 — `buyerListingsQuery`로 매물을 먼저 찾은 뒤 **그 매물이 있을 때만** 호출한다. sold면 404 화면에서 끝나 이 함수까지 오지 않는다) · **`attach_cover_images`(api, AI 응답 카드 — Story 9.6)** · **`/wishlist` 찜 목록 페이지(Story 10.5)** — `attachCoverImages`를 다시 쓰되, `isWishedListingBlocked`로 걸러진 **on_sale 찜 매물 id만** 넘긴다(sold·RLS차단 항목은 회색 타일로 사진 없이 렌더 — 애초에 이 함수를 안 부른다). 강제 지점은 위와 동일하게 `listing_images`의 on_sale RLS.
      - **앱(Flutter)이 연 세 경로**: `ListingsRepository._fetchCovers`(`app/lib/features/listings/listings_repository.dart`, 앱 목록 카드 대표사진 — `_buyerQuery`(`.eq('status','on_sale')`) 결과의 id만 `.inFilter()`로 조회, Story 16.2) · `ListingsRepository.fetchListing`의 갤러리 조회(앱 상세 갤러리 — 매물을 `_buyerQuery`로 먼저 찾아 null이 아닐 때만 조회하므로 sold는 이 지점에 오지 않는다, web `fetchListingGalleryUrls`와 같은 좁히기, Story 16.2) · **`ListingsRepository.fetchPopularListings`(홈 "지금 인기" 섹션 — `_buyerQuery` 결과를 `view_count desc`로 정렬해 상위 몇 건만 뽑은 뒤 그 id만 `_fetchCovers`에 넘긴다, spec-16-8)**. 셋 다 앱의 anon/authenticated Supabase 세션으로 붙으므로 `0012_listing_images`의 on_sale RLS가 DB에서도 걸러 준다 — 즉 api의 `attach_cover_images`와 달리 **이중 방어**다. ⚠️ 강제 장치(자동 테스트)는 아직 없고, 수동 실측(anon 키로 직접 조회)으로만 확인됐다.
      - **앱이 연 네 번째 경로(Story 16.3)**: `WishlistRepository.fetchCovers`(`app/lib/features/wishlist/wishlist_repository.dart`, 앱 찜 목록 화면의 대표사진) — web `/wishlist`와 동일 패턴으로, `isWishlistBlocked`로 걸러진 **on_sale 찜 매물 id만** `.inFilter()`로 넘긴다(sold·RLS차단 항목은 이 함수를 애초에 안 부르고 회색 타일로 사진 없이 렌더). 대표사진 승자 판정은 `listings_repository.dart`의 top-level 공개 함수 `pickCoverImages`를 그대로 재사용해 로직을 두 곳에 따로 두지 않는다. 위 세 경로와 같은 authenticated Supabase 세션으로 붙으므로 `0012_listing_images`의 on_sale RLS가 DB에서도 이중 방어한다. ⚠️ 강제 장치는 `wishlist_providers_test.dart`의 `wishlistProvider` provider-레벨 테스트다(✎ 2026-08-08 Story 16.3 코드리뷰 정정 — 이전엔 `wishlist_repository_test.dart`의 `isWishlistBlocked` 단위테스트가 이 id 좁히기를 지킨다고 적혀 있었으나, 그 테스트는 판정 함수 자체를 격리해서만 보고 `fetchCovers`에 실제로 어떤 id가 넘어가는지는 보지 않는다 — `wishlistRepositoryProvider`를 가짜로 갈아 끼워 `wishlistProvider` 본문을 직접 돌려 on_sale id만 `fetchCovers`로 가는지 확인하는 쪽이 실제 강제 지점이다). 실제 DB 조회 자체는 여전히 수동 실측 대상이다.
      - ⚠️ **`attach_cover_images`만 성격이 다르다 — 여기서는 DB가 안 막는다.** 위 web 두 경로는 `authenticated`/`anon` 롤로 붙으므로 `listing_images`의 on_sale RLS가 **DB에서** 걸러 준다. 그런데 api는 `ai_readonly` 롤이고 그 롤의 정책은 `using(true)`라(`0012:153`, 의도된 설계 CR2) **sold 사진까지 전부 열려 있다.** 그래서 이 경로는 고정쿼리의 `l.status = 'on_sale'`이 **유일한 강제 지점**이다 — 까먹으면 그대로 뚫린다.
      - 강제 장치: `api/tests/test_listing_cards.py`(sold 사진이 응답에 실리지 않음 — 조건을 지우면 red) + `api/tests/test_sql_guard.py`(LLM 생성 SQL이 `listing_images`에 닿지 못함). 둘 다 `docs/tech-debt.md` #48을 닫은 근거다.
    - ✎ **2026-07-19 코드리뷰에 의해 등재.** 이 축은 0012부터 실재했는데 **이 목록에 한 번도 오른 적이 없었고**, 9.0이 `storage.objects` 항목을 지우면서 이미지 관련 강제 지점이 목록에서 완전히 사라졌다. 그 상태에서 9.4가 `listing_images` 조회 경로를 화면 2곳(`/search`·홈)에 새로 열었다. **차단은 실제로 동작한다**(실측) — 문제는 목록이 사실을 반영하지 않아, §6만 읽는 다음 사람은 이미지 축에 FR11 강제가 있다는 것 자체를 모른다는 점이다. 9.5(상세 갤러리)·9.6(AI 카드)이 같은 테이블을 열 때가 정확히 규칙7이 경고한 자리다.
    - ⚠️ **§6.1이 면제하는 것은 "사진 파일 URL"이지 `listing_images` 테이블 조회가 아니다.** 둘을 섞지 말 것.
  - **SECURITY DEFINER 함수 축** — 정의자 함수 안에서는 RLS가 적용되지 않는다(정의자=소유자 권한으로 평가되고, 소유자에겐 RLS가 애초에 안 걸린다). 그래서 위 두 축과 달리 RLS가 대신 걸러주지 않고, **함수 본문의 인라인 조건이 유일한 강제 지점**이다.
    - 소비처 목록: `get_seller_public_summary`(`0019_seller_public_summary.sql`, 상세 판매자정보 — Story 10.6) — anon·authenticated에 `grant execute`. 함수 안 `status = 'on_sale'` 조건이 유일한 강제 지점이며, 지우면 RLS가 대신 막아주지 않으므로 그대로 뚫린다. 강제 장치: `api/tests/integration/test_seller_summary_real_db.py`(`set local role anon`으로 RPC를 실제 호출 — sold 매물을 추가해도 집계가 안 늘어남을 확인, `status='on_sale'`을 지우면 red. `api-db` CI 잡이 실행).
    - `admin_restore_sold_listing`(`0030_listings_restore_sold_rpc.sql`, 관리자 판매완료 되돌리기 — Story 15.4, DW-391) — **`authenticated`에만** `grant execute`(anon은 EXECUTE 자체가 없다). 여기서 정의자 함수가 여는 것은 "조회"가 아니라 **`status` 쓰기**다: `0015`가 authenticated UPDATE에서 sold 행을 통째로 빼 놓았는데, 이 함수는 그 RLS를 우회해 `sold`→`on_sale`을 되돌린다. 함수 본문의 `where ... status='sold' and public.is_admin_active()`(0032, Story 17.1이 `is_admin()`에서 교체)가 유일한 강제 지점이며, 지우면 아무 로그인 사용자나 남의 매물 상태를 바꿀 수 있다. 강제 장치: `api/tests/integration/test_restore_sold_listing_rpc_real_db.py`(`set local role`로 anon·비관리자·판매자 본인을 각각 실제 호출 — 전부 거부되고 관리자만 1행. `api-db` CI 잡이 실행) + `test_suspended_write_block_real_db.py`(정지된 관리자도 0행 — DW-721 회귀 가드).
      - ⚠️ **위 매물 축의 "authenticated UPDATE = `0015`"를 유일한 UPDATE 관문으로 읽으면 틀린다.** `0030` 이후 sold 행을 되돌리는 문이 하나 더 있고, 그 문은 RLS 밖에 있다.
      - ✎ **정정(Story 17.1, 0032, DW-721 해소):** 이 항목은 원래 *"`is_admin()`은 `role`만 보고 `profiles.status`를 보지 않아 정지된 관리자도 통과한다"* 고 적혀 있었다. `is_admin()` 자체는 전역으로 좁히지 않았다(관리자 SELECT 정책까지 함께 좁아지는 부작용을 피하려고 — §8 참조) — 대신 **쓰기 소비처 전용**으로 `public.is_admin_active()`(SECURITY DEFINER, `role='admin' and status='active'`)를 새로 만들어 이 RPC를 포함한 관리자 쓰기 경로 전부를 그 함수로 교체했다. `is_admin()`은 여전히 `status`를 안 보지만, 이제 그걸 참조하는 자리는 **관리자 읽기 정책뿐**이라 안전하다(정지된 관리자도 열람은 허용돼야 한다는 §8 원칙과 정합).
    - `is_admin_active()`(`0032_suspended_write_block.sql`, 활성 관리자 판정 — Story 17.1, DW-721) — **`authenticated`에만** `grant execute`(public·anon은 회수). 이 함수 자체는 데이터를 열지 않지만, **관리자 쓰기 경로 전부의 유일한 판정식**이다: `listings_delete_admin`·`profiles_update_admin`·`profiles_delete_admin`·`chat_rooms_delete_admin`·`chat_messages_delete_admin`·`listing_images_objects_admin_delete` 6개 정책 + 위 `admin_restore_sold_listing` RPC가 전부 이 함수 하나를 부른다. 본문의 `role='admin' and status='active'`가 강제 지점이며, `status` 조건을 지우면 정지된 관리자가 그 7개 경로를 전부 되찾는다. SECURITY DEFINER인 이유는 `is_admin()`과 같다(`profiles` 자신을 지키는 정책 안에서 `profiles`를 서브쿼리하면 정책 무한재귀). 강제 장치: `api/tests/integration/test_suspended_write_block_real_db.py`(정지 관리자로 7경로 전부 0행 + 활성 관리자로 전부 성공 — 양방향 고정. `api-db` CI 잡이 실행).
      - ⚠️ **읽기 쪽으로 넓히지 않는다.** 관리자 SELECT 정책(`listings_select_admin`·`profiles_select_admin`·`chat_*_select_admin`·`listing_images_select_admin`)은 `is_admin()` 그대로다 — 정지된 관리자도 **열람은 허용**돼야 한다는 §8 원칙 때문이다. 이 함수를 SELECT 정책에 쓰면 그 원칙이 조용히 깨진다(회귀 가드: `test_suspended_admin_can_still_read_via_admin_select_policies`).
- **새 조회 경로를 열면 이 목록에 강제 지점을 추가**한다(규칙7). **정의자 함수는 조회뿐 아니라 쓰기 경로도 이 목록에 올린다** — RLS 밖이라는 성질이 같기 때문이다. anon 열람은 §8이 상술한다.

### 6.1 사진 파일 URL은 FR11 대상이 아니다 (명시 수용, 사용자 결정 2026-07-19)

**`listing-images` 버킷은 공개다. 사진 파일의 URL을 이미 아는 사람은 그 매물이 `sold`가 된 뒤에도 파일을 열 수 있다.** 이것은 버그가 아니라 **받아들이기로 한 결정**이다.

- **FR11이 막는 것**: 매물이 목록·검색·상세·AI 응답에 **나타나는 것**. 이건 위 강제 지점들이 그대로 막는다 — 변한 것이 없다.
- **FR11이 막지 않는 것**: 판매중일 때 사진 주소를 저장해 둔 사람이 나중에 그 주소를 다시 여는 것. 매물이 노출되는 게 아니라 **주소를 이미 아는 사람만** 접근한다(파일명이 uuid라 추측 불가).
- **왜 이렇게 정했나**: 이전 설계(비공개 버킷 + 1시간 서명 URL)는 이 복잡도를 다 치르고도 **TTL 동안 똑같이 뚫려 있었다**(`docs/tech-debt.md` #50-2 — "수용"으로 기록돼 있었다). 비용은 전부 내고 효과는 못 얻는 구조였고, 그 대가로 부채 5건(#45·#46·#50-2·#55·#62)이 열려 있었다. 상용 중고차·쇼핑 서비스도 상품 사진은 공개 CDN으로 서빙한다.
- **`sold`일 때 파일을 지우지 않는 이유**: `sold`는 되돌릴 수 있는 상태 변경인데 파일 삭제는 되돌릴 수 없다. 그리고 Story 15.1이 "관리자는 sold 포함 열람"을 이미 요구한다.
- **매물 삭제는 다르다** — 삭제하면 사진 파일도 실제로 지운다(§10.1). 삭제는 되돌릴 수 없는 사건이므로 파일도 함께 사라지는 것이 맞다.

⚠️ **이 절은 "아직 못 막은 것"이 아니라 "안 막기로 한 것"이다.** 다시 막으려 들기 전에 위 근거와 `docs/tech-debt.md`의 관련 항목을 먼저 읽을 것.

## 7. 채팅 메시지 길이 (Chat Message Length)

- **본문(`body`) 최대 `2000`자.** 공백 제거(trim) 후 글자 수 기준.
- 강제 지점(3층): DB CHECK(`0010_chat_message_length.sql`, `char_length(body) <= 2000`) + web 입력창 `maxLength` + `sendMessage` 길이 가드. 값은 `web/src/lib/constants.ts`의 `CHAT.MESSAGE_MAX_LENGTH`가 미러링.
- 빈 본문 금지는 별도 CHECK(`0003_chat.sql`, `length(btrim(body)) > 0`). (근거: 기술부채 #8 — 무제한 붙여넣기로 행·폴링 페이로드 비대화 방지)

## 8. 접근 게이트 계약 (Access Gate Contract, FR58)

로그인 게이트는 "열람"이 아니라 **"행동"에만** 적용한다. Epic 9~14의 신규 진입점은 이 계약을 따른다.

**분류 기준 — "열람이냐 행동이냐"는 화면이 아니라 대가로 가른다:**
1. 서버 자원만 읽으면 → **열람**
2. 상태를 바꾸거나(쓰기), **외부 유료 API를 호출해 청구서를 만들면** → **행동**

> ⚠️ **비용이 발생하는 엔드포인트는 신원을 요구한다.** 호출 1회가 실비(외부 API 과금)를 만드는 경로는 인증 없이 열지 않는다. 인증은 접근제어 장치이자 **유일한 과금 울타리**이기 때문이다 — 신원이 없으면 남용자를 특정할 수도, 한도를 걸 수도, 차단할 수도 없다. 이 원칙은 Epic 13(RAG 고도화 — 임베딩 비용)에도 동일 적용한다.

- **열람 (anon 허용, 로그인 불필요):** 매물 목록(`/search`)·매물 상세(`/listings/[id]`).
  - DB: `listings` RLS에 `to anon using (status = 'on_sale')` 정책이 있다(`0011_listings_anon_select.sql`). `sold`는 anon에게도 어느 경로로도 노출되지 않는다(§6 FR11과 동일 규칙, 새 경로도 예외 없음).
  - RLS는 **행**만 통제하고 **컬럼**은 통제하지 못한다. 그래서 0011은 anon에게 컬럼 스코프 `grant select (…)`를 명시해 `embedding` 등 비노출 컬럼을 차단한다. **anon 노출 컬럼을 늘리려면 0011 이후 새 마이그레이션으로 grant를 추가**한다(테이블에 컬럼만 추가하면 anon엔 안 보이는 게 기본값 — 의도된 동작).
  - web `proxy.ts`의 `PROTECTED_PREFIXES`에 위 경로들을 넣지 않는다.
- **행동 (로그인 필수 + 원위치 복귀):** **AI 검색(`/ai`, `/ai/search`)**·문의하기(채팅방 생성)·매물 등록/수정/삭제(`/sell`)·찜(Epic 10.5)·문의 채팅함 열람(`/chat`, 개인 대화 목록).
  - **AI 검색이 왜 행동인가:** 검색 1회 = Gemini 호출 3회 내외(질문 다듬기·경로 판단·SQL/답변 생성) = **실제 과금**. 위 분류 기준 2에 해당한다. `ai_readonly`·`sql_guard`는 **DB 권한**을 지키지 **API 키 지출**을 지키지 않는다 — 인증 완화가 권한 누수를 만들지 않는다는 말은 참이지만, 그것이 "열어도 안전하다"를 뜻하지는 않는다. (근거: 코드리뷰+party-mode 2026-07-14. 대안이었던 익명 N회 제한은 Cloud Run 다중 인스턴스에서 카운터를 공유할 수 없어 표시 숫자를 보장 못 하므로 폐기 — 지킬 수 없는 숫자는 표시하지 않는다.)
  - api `/ai/search`는 **JWT 필수**(`get_current_user`) — 무토큰 401, 무효 토큰 401, Auth 전송오류 503. `/ai`는 `proxy.ts`의 `PROTECTED_PREFIXES`에 포함된다.
  - **계정당 쿼터가 필요해지면** JWT의 사용자 ID로 Postgres 카운트를 걸면 된다(Redis 불필요). 신원을 지켜두면 나중 제한이 싸진다.
  - 페이지는 공개(열람)이지만 특정 액션만 게이트해야 하는 경우(예: 매물 상세의 "문의하기"), 그 액션 지점에서 비로그인에게 **로그인 유도 링크**(`/login?redirectedFrom=<현재경로>`)를 보여준다(버튼을 숨기지 않는다 — 어포던스는 노출).
  - `web/src/app/(auth)/login/page.tsx`가 `redirectedFrom` 쿼리를 읽어 로그인 성공 시 그 경로로 복귀한다. 오픈 리다이렉트 방어: `/`로 시작하고 `//`·`/\`로 시작하지 않는 내부 경로이며 인증 경로(`/login`·`/signup`) 자신이 아닐 때만 허용, 그 외는 `/`로 폴백.
  - `/admin`(관리자)·`/sell`(매물 등록·관리)·`/chat`(문의 인박스)은 페이지 단위로 여전히 `proxy.ts`가 보호한다(anon에게 의미 없는 개인/관리 영역).
- **행동 게이트는 사용자 입력을 삼키지 않는다 — ⚠️ 웹 한정, 앱은 예외(2026-08-10 사용자 결정):** 비로그인이 입력을 마친 뒤 게이트를 만나면, 그 입력을 보존했다가 로그인 복귀 시 복원한다(`redirectedFrom`은 **경로만** 나르고 폼 상태는 못 나른다 — 보존은 sessionStorage 등으로 명시 구현). **복원까지만 하고 자동 실행하지 않는다** — 과금 호출의 트리거를 페이지 로드에 매달면 새로고침·뒤로가기가 재과금이 된다. 마지막 실행은 항상 사용자의 클릭이다. (Story 11.3 히어로가 이 패턴의 첫 적용처.)
  - **앱(Flutter)은 이 조항을 따르지 않는다.** 비로그인이 AI 검색을 전송하면 질의를 버리고 `/login`으로 보내며(`ai_chat_screen.dart`), 로그인 후에는 `/home`으로만 돌아간다(원래 탭·질의 복원 없음). **이것이 앱의 의도된 동작이다.** 근거: Epic 16 묶음 코드리뷰(2026-08-10)에서 리뷰어 3명이 이 조항 위반으로 앱을 지적했고, 사용자가 *"앱에서는 그 기능 신경 쓰지 마, 그냥 검색 누르면 로그인으로 넘어가고 끝"* 으로 결정했다. **웹은 그대로 유지한다**(`heroSearchHandoff.ts` 양 갈래 모두 — `autoRun:true`는 로그인 사용자의 랜딩 히어로→`/ai` 자동 실행이라 지우면 랜딩 동선이 끊긴다).
  - ⚠️ 이 예외는 `epic-16-context.md`의 일반 규칙(*"'웹 한정'이라고 적혀 있지 않으면 전부 앱도 포함"*)을 **이 조항에 한해** 덮어쓴다. 다음 리뷰가 같은 지적을 반복하지 않도록 여기(정본)에 박아 둔다 — 코드에 주석만 달면 리뷰어는 계약 문서를 보고 또 지적한다. 경위는 `docs/decisions-archive.md`.
- **신규 진입점 추가 시:** 위 분류 기준으로 먼저 가른다. 열람이면 `proxy.ts`에 넣지 않고 컴포넌트 레벨 행동 게이트만 추가, 행동·개인·관리 영역이면 `proxy.ts`의 `PROTECTED_PREFIXES`에 추가한다.
- **정지(`profiles.status='suspended'`)도 이 축의 "행동" 게이트다(DW-669, Story 17.1):** 막는 것은 매물·사진·파일 등록/수정/삭제와 관리자 쓰기 액션(회원 삭제·매물 삭제·되돌리기 RPC 등)뿐이고, 로그인·열람(매물 조회, 본인 profiles 조회 등)은 막지 않는다. 강제 지점은 앱 코드가 아니라 `supabase/migrations/0032_suspended_write_block.sql`의 RLS 정책 + `public.is_admin_active()`(SECURITY DEFINER — RLS를 우회하는 `admin_restore_sold_listing` RPC도 이 함수로 함께 막는다, DW-721)다 — 화면마다 심지 않고 데이터 계층 하나로 모든 클라이언트를 예외 없이 막는다. **채팅 발신도 이 축에 포함된다** — 정지된 참가자의 `chat_messages` INSERT는 막고(`chat_messages_insert_participant`), 방송(0023)·안읽음 계산(0024~0026)은 "INSERT 성공 이후"에만 동작하므로 이 차단이 정상 참가자의 흐름을 깨지 않는다(실DB 확인: `api/tests/integration/test_suspended_write_block_real_db.py`). **막지 않는 쓰기(의도적 현재 범위, 2026-08-11 전수조사 — `pg_policies`·`pg_proc` 실측, 0032가 건드린 목록에 있는 것만 "막는다"다)**: `chat_rooms_insert_participant`(채팅방 생성 — 발신만 결정 대상이었다, [[DW-799]]로 이월) · `wishlists_insert_own`/`wishlists_delete_own`(찜 추가/삭제) · `chat_room_reads_insert_participant`/`chat_room_reads_update_own`(안읽음 커서 갱신) · `increment_listing_view`(SECURITY DEFINER, `anon`도 호출 가능해 애초에 `profiles` 신원으로 게이트할 수 없다 — 조회수 집계는 이 절 불변식의 "매물·사진·파일·관리자 쓰기" 범주에 없다). 근거: `_bmad-output/implementation-artifacts/deferred-work.md`의 [[DW-799]]·[[DW-801]]·[[DW-802]].

## 9. 마이그레이션 정책 (Story 8.6)

### 9.1 `supabase/migrations/`는 **레시피**다

**레포 파일만으로 빈 DB가 서야 한다.** "로그"(살아있는 DB에 뭘 했는지의 기록)가 아니라 **레시피**(신규 환경을 처음부터 재현하는 절차)로 다룬다. 이유 없는 규칙은 다음 사람이 또 뒤집으므로, 근거를 그대로 남긴다(2026-07-14 사용자 결정):

1. **원격 Supabase 프로젝트가 하나뿐이라 그게 날아가면 복구 = fresh DB다. 현재 복구 경로가 없다.** ← 이 결정을 떠받치는 주 기둥.
2. 외주/납품 인수조건 가능성은 **현재 비어 있다**(2026-07-14 정정: 납품 계획 없음). 살아나면 "맨 Postgres에서도 서는가"가 쟁점이 되고, 그땐 `docs/deployment-runbook.md` §8-①(사각지대)의 마지막 항목이 답이다.
3. **Epic 9~16이 마이그를 8개 더 얹는다.** 지금 1건(0004)인 순서 뒤틀림이 20개 파일에선 몇 건이 될지 모른다.

**범위 한정: Supabase 전제.** "레포만으로 DB가 선다"는 **Supabase 프로젝트 위에서** 참이면 된다. 맨 Postgres 이식성은 목표가 아니다 — 없는 시나리오를 위해 짓지 않는다.

**불변식의 정확한 이름** — "번호순=적용순"이라 부르지 않는다:

> **각 마이그는 자기가 필요로 하는 선행 상태를 스스로 만들거나(멱등 가드), 번호가 더 작은 마이그에만 의존한다. 원격 적용 이력의 순서는 상관없다.**

번호 갭은 무죄(자리를 비워둬도 무해), **역방향 의존만 유죄**. 이는 `.github/workflows/migration-gate.yml`(마이그레이션 게이트 CI)이 매 push마다 실제로 검증한다 — 자세한 것은 `docs/deployment-runbook.md` §7·§8.

**"전진(forward-only)"과 RLS 정책 교체의 관계** (✎ 2026-07-21 코드리뷰가 판단을 명시화):

CLAUDE.md B3는 *"DB 변경은 더하기만 — 기존 걸 지우거나 바꾸지 않는다"* 인데, **RLS 정책을 고치려면 형식상 `drop policy`를 거쳐야 한다**(Postgres에 `alter policy ... using` 이 있지만 조건 전체를 갈아끼우는 경우 drop-recreate가 더 읽힌다). `0015`가 그렇게 했고, 그것이 허용 예외인지 **판단한 기록이 없어** 다음 사람이 근거 없이 이 선례를 복사할 자리였다. 그래서 규칙으로 못박는다:

- ✅ **허용:** `drop policy if exists` → `create policy` **같은 이름으로**, 같은 파일 안에서 즉시 재생성. 정책은 **접근 규칙**이지 데이터가 아니라 소실되는 것이 없고, 이 패턴이라야 재적용이 멱등이 된다(`0005`·`0006`이 이미 쓰는 패턴).
- ✅ **허용(트리거도 동일):** `drop trigger if exists` → `create trigger` **같은 이름으로**, 같은 파일 안에서 즉시 재생성. 트리거도 정책과 같은 축이다 — **접근·배선 규칙**이지 데이터가 아니라 drop-recreate로 소실되는 것이 없고, 이 패턴이라야 마이그를 재적용해도 "already exists"로 죽지 않는다(멱등). `0016_chat_room_integrity.sql`(선례)·`0023_chat_realtime_broadcast.sql`이 이미 이 패턴을 쓴다 — 이 항목이 없어 두 파일이 근거 없이 같은 선례를 복사한 자리였다(2026-07-28 코드리뷰가 지적, CLAUDE.md B8 "각주에 둔 제약도 본문으로 올린다").
- ✅ **허용(같은 파일이 `create [or replace] function`으로 정의한 함수의 EXECUTE 회수):** 그 직후의 `revoke all on function ... from public/anon/authenticated`. 이건 "있던 권한을 없애는 것"이 아니라 **새 객체의 최초 권한을 정하는 것**이다 — Postgres가 새 함수에 PUBLIC EXECUTE를 자동으로 주기 때문에, 회수하지 않으면 PostgREST가 `/rest/v1/rpc`로 그 함수를 노출한다(SECURITY DEFINER 함수면 특히 위험). `0016`·`0020`·`0023`이 이미 이 패턴을 쓴다. **판정 기준을 "객체가 전에 있었나"가 아니라 "같은 파일의 어떤 문장이 그 객체를 정의하나"로 잡는다** — 마이그는 재적용 가능해야 하고 `create or replace`는 두 번째 적용부터 항상 "이미 있던 객체"가 되므로, 객체의 나이를 기준으로 삼으면 같은 파일이 적용 횟수에 따라 합법·불법을 오간다(2026-07-28 3차 코드리뷰가 지적).
- ✅ **허용(권한을 좁히는 회수 — 회수 직후 더 좁은 범위로 재부여):** `revoke <권한> on <테이블> from <롤>` → 같은 파일에서 즉시 `grant <권한> (컬럼 목록) ...`. 플랫폼 기본 GRANT는 테이블 전체를 열어두므로, **컬럼 단위로 좁히려면 먼저 회수하는 것 말고 방법이 없다**(실측: 컬럼 단위 revoke 단독은 무효). 이건 권한이 사라지는 게 아니라 **줄어드는** 것이고, 방향이 보안을 좁히는 쪽이다. `0011`(anon의 listings SELECT를 컬럼 화이트리스트로)·`0012`(listing_images)·`0020`(authenticated의 listings INSERT/UPDATE를 RPC 외 컬럼으로)이 이미 이 패턴을 쓴다.
- ❌ **금지:** 테이블·컬럼·인덱스의 drop, 그리고 **재부여 없이 권한만 거두는 GRANT 회수**. 이것들은 **데이터나 권한이 실제로 사라진다** — 되돌리려면 앞에 고치는 마이그를 하나 더 붙인다(B3).
- 📌 정책을 교체하는 마이그는 **무엇을 왜 바꾸는지와 함께 `using`/`with check` 중 어느 쪽에 조건을 거는지의 근거**를 파일 주석에 남긴다. 둘은 보는 대상이 다르다(`using`=변경 전 행, `with check`=변경 후 행) — `0015`가 그 판단을 적어둔 좋은 예다.

### 9.2 파일명 규약

- **정본**: `NNNN_이름.sql` (4자리 번호, **0001부터**, 유일, 밀집 — 공백 없이). fresh DB(신규 환경)의 **단일 출처**다.
  - **밀집이 §9.1의 "번호 갭은 무죄"와 모순 아닌 이유**: 둘은 서로 다른 축이다. §9.1의 갭 무죄는 **의존성 축**("0003 자리가 비어도 0004가 깨지지 않는다" — 참이다). 여기의 밀집은 **번호 관리 축**이다. 번호가 0001~max로 빈틈없고 바닥번호가 유일하면, 새 마이그의 번호는 `max+1`이거나 중복(→ 검출)뿐이라 **뒤로 끼워넣을 자리가 구조적으로 없다**. 즉 밀집은 갭 자체가 해로워서가 아니라 **out-of-order 삽입을 git 이력 추적 없이 막는 가장 싼 방법**이라서 있다.
- **🚫 알파벳 접미사(`NNNNb_이름.sql`)는 금지한다** (2026-07-21 폐지, 사용자 결정. 경위는 대장 `docs/tech-debt.md` #101).
  - **왜**: Supabase CLI는 `<timestamp>_name.sql`만 마이그로 인정해 접미사 파일을 **에러가 아니라 `Skipping`으로 조용히 건너뛴다.** 그래서 게이트는 초록인데 `supabase db reset`이 만든 fresh DB에는 그 파일이 통째로 빠진다. **실제로 일어났다** — `0003c_chat_room_integrity.sql`이 건너뛰어져 로컬 fresh DB에 `chat_rooms`의 `seller_id` 위조 방지 트리거가 없었다(원격에는 있었다. 원격은 CLI가 아니라 MCP로 적용해왔기 때문).
  - **그래서 새 마이그는 항상 `max+1`만 쓴다.** 사이에 끼워넣을 자리는 없다 — 위 밀집 규칙이 원래 노린 바가 그것이고, 접미사는 그 규칙에 뚫려 있던 구멍이었다.
  - **이 규칙은 `scripts/check_migrations.py`가 강제한다**(정규식 `^(\d{4})_([a-z0-9_]+)\.sql$`). 접미사 파일을 만들면 게이트가 종료코드 1로 실패한다 — 문서만으로 막지 않는다(CLAUDE.md B9).
- **따라잡기 패치**: 정본을 **in-place 수정**했을 때 *이미 살아있는* 원격 DB만 그 수정을 따라오게 하는 **멱등 패치**. 신규 환경은 정본이 이미 최신이라 불필요하므로 **파일로 남기지 않는다**(원격에 직접 적용하고 끝). 접미사 폐지의 영향을 받지 않는다 — 애초에 레포에 파일이 안 생기기 때문이다.

**폐지 이전의 이력**: 원격 적용 원장에는 접미사 이름이 5건 남아 있다(`0002b_listings_created_at_immutable`·`0002c_listings_price_bigint`·`0002d_listings_year_dynamic_max`·`0003b_chat_review_hardening`·`0003c_revoke_trigger_execute`). **레포에 커밋된 적 없고, 지금 와서 파일로 만들지 않는다.** 원격 원장과 레포 파일이 1:1이 아닌 것은 결함이 아니라 설명 가능한 이력이다(`docs/deployment-runbook.md` §8-8). 단 `0002b`는 그 이름이 말하는 보호장치가 **원격 DB에서 발견되지 않는다** — 열린 질문으로 대장 #103에 있다.

### 9.3 정본 in-place 수정 시 판정 규칙

위반 마이그 M이 뒤 번호 N의 객체(테이블·롤·함수 등)를 가정할 때(= self-contained 위반), 수정 방식을 아래 기준으로 가른다:

- **(a) → 개발자 자율 처리(사후 보고).** 아래 3조건을 **전부** 만족할 때:
  1. 수정이 **멱등 가드 추가만**이다(`do $$ ... if not exists ... end $$` 계열).
  2. 원격에 재적용해도 **상태 델타 0**임을 실측으로 확인했다.
  3. **기존 객체 정의가 불변**이다(컬럼 타입·제약·정책 술어 변경은 이 틀 밖).
- **(a′) → 개발자 자율 처리 + 실측 증거 첨부 (GRANT 변경 전용, 2026-07-16 신설).** GRANT 대상 변경은 조건①③을 구조적으로 어기지만, **아래를 전부 만족하면 승인 없이 진행한다**:
  1. **적용 전에 원격의 현재 권한을 실제로 떠서** 델타 0임을 확인하고, **그 출력을 작업 기록에 남긴다.** 예:
     ```sql
     select grantee, table_name, privilege_type
       from information_schema.role_table_grants
      where table_schema='public' and grantee in ('anon','authenticated','ai_readonly')
      order by table_name, grantee, privilege_type;
     -- 또는: select has_table_privilege('authenticated','public.listings','select');
     ```
  2. **델타가 0이 아니면 멈추고 사용자 승인**(= 실제로 권한이 바뀌는 변경이므로 (b)).
  3. **넓히는 방향이면 무조건 (b)**. 새 롤에 GRANT, 새 컬럼을 anon에 노출, `to public` 등 — 델타 0이어도 승인.
- **(b) → 멈추고 사용자 승인.** 위 어디에도 안 들어가면. 특히 **원격에 따라잡기 패치(`NNNNb`)가 실제로 필요해지는 순간 = 살아있는 공유 DB를 건드리는 순간 = 무조건 승인**이 필요하다.

> **왜 (a′)를 뒀나 (2026-07-16 사용자 결정):** 승인 자체가 안전을 만들지 않는다 — 사용자가 "예"라고 해도 GRANT가 정확해지지 않는다. **진짜 안전장치는 "델타 0"을 논증이 아니라 실측으로 증명하는 것**이고, 그건 사람을 깨우지 않고도 할 수 있다. 병목(승인 대기)을 없애되 이 프로젝트가 4번 반복한 결함(**재보지 않고 선언**)은 그대로 막는다.
>
> 단 **넓히는 방향은 여전히 (b)다.** 권한은 틀리면 조용히 넓어지고, 넓어진 건 아무도 안 알려준다 — 이 프로젝트가 이미 두 번 데인 자리다(8.5 `embedding` 컬럼 노출 위험: RLS는 행만 막지 열은 못 막음 / 8.6 게이트가 "정책 존재"만 보고 "정책이 듣는지"는 안 봄).

(선례: Story 8.6의 `0004_guide_documents.sql` 수정은 3조건을 전부 만족해 (a)로 처리됨 — `ai_readonly` 롤 생성을 `0006`에서 그대로 복사한 멱등 DO 블록으로 넣었고, 원격엔 이미 그 롤이 있어 재적용해도 no-op이다.)

### 9.4 배포·게이트

배포 순서·부분배포 정합성·롤백·마이그 적용 절차(Supabase MCP `apply_migration`)·게이트가 증명하는 것과 안 하는 것은 `docs/deployment-runbook.md`가 상술한다. **각 에픽 첫 마이그 스토리는 마이그레이션 게이트(CI) 통과가 DoD다.**

## 10. 이미지 스토리지 계약 (Story 9.1)

- **버킷**: `listing-images`(**공개, `public=true`** — `0014_listing_images_public_bucket.sql`, Story 9.0). 읽기만 공개다 — **업로드는 여전히 본인 경로에만** 가능하다(아래 Storage RLS).
  - 공개 오브젝트 URL 형식: `{SUPABASE_URL}/storage/v1/object/public/listing-images/{storage_path}`. 만료가 없다.
  - 전환 근거와 "sold 후에도 열린다"는 수용은 **§6.1**에 있다.
- **경로 규칙**: `{user_id}/{listing_id}/{filename}` — **첫 세그먼트가 소유자**다(Storage 쓰기 RLS가 이 사실에 의존).
  - ✅ **이 규칙은 DB가 강제한다**(`0013_listing_images_path_integrity.sql`) — `listing_images` 삽입·수정 시 트리거가 소유자를 **`storage_path`에서 파싱하지 않고 `listings`에서 직접 구해** 대조한다(CLAUDE.md B9 "중요한 값은 서버·DB가 직접 구한다"). 세그먼트가 정확히 3개가 아니거나 소유자·매물이 안 맞으면 거부.
  - **왜 트리거까지 필요했나**: `0012`는 이 규칙을 이 문서에만 두고 `storage_path`를 무검증 자유 문자열로 받았다. 그런데 Storage 읽기 RLS가 바로 그 문자열로 조인하므로, 판매자가 자기 매물에 **남의 경로**를 적으면 남의 사진 행이 anon에게 열렸다(원격 실측 재현: anon 0행 → 1행). (버킷이 공개가 된 지금도 이 트리거는 유효하다 — 막는 대상이 "파일 열람"이 아니라 **남의 파일을 내 매물에 갖다 붙이는 것**이기 때문이다.) **규약을 문서에만 두면 규약이 아니다.**
- **등록 순서**: **매물 행을 먼저 insert해 `listing_id`를 얻은 뒤** 그 경로로 업로드한다(스테이징 경로·이동 없음).
- **상한**: 매물당 최대 **10장** · 장당 최대 **5MB** · 허용 MIME `image/jpeg`·`image/png`·`image/webp` 3종.
  - 3개 상한은 **클라가 아니라 서버 쪽에 둔다** — 클라 검증은 우회 가능하다.
  - ⚠️ **강제하는 주체가 셋 다 다르다 (9.1 코드리뷰 정정, 2026-07-16 — 전엔 "전부 DB에 박는다"고 적혀 있었으나 사실보다 강했다):**

    | 상한 | 누가 강제하나 | 지금 상태 |
    |---|---|---|
    | 10장 | `listing_images`의 **BEFORE INSERT 트리거**(Postgres) | ⚠️ **INSERT만** — `listing_id`+`storage_path`를 함께 바꾸는 UPDATE로 **우회된다**(실측, `docs/tech-debt.md` #43). 동시 삽입 경합도 미해결(#49) |
    | 5MB | **Storage API 서버** (Postgres 아님 — `storage.buckets`는 값을 보관만 한다) | 마이그레이션 게이트는 이 축을 **전혀 증명하지 못한다**(스텁이 평범한 테이블이라 값만 들어간다) |
    | MIME 3종 | **Storage API 서버** (위와 동일) | 위와 동일 |

  - MIME 제한의 이유: **공개 버킷이라 더 중요하다** — 인증 없이 열리므로 타입 제한이 없으면 `.html`/`.svg` 업로드가 우리 도메인에서 실행되는 저장형 XSS가 된다.
  - ~~버킷 설정은 `on conflict do nothing`이라 버킷이 이미 존재하면 조용히 무효(#44)~~ → **해소.** `0014`가 `UPDATE`로 `public`·`file_size_limit`·`allowed_mime_types`를 덮어쓴다 — 버킷이 어떤 상태였든 그 문장에서 확정된다.
- **`listing_images.storage_path`** = 버킷 내 key **전체**(`{user_id}/{listing_id}/{filename}`, 버킷명 미포함) — `storage.objects.name`과 **글자 그대로 같아야** Storage RLS의 조인이 성립한다.
- **URL 만료가 없다.** ~~`SIGNED_URL_TTL = 3600`~~ 상수는 Story 9.0에서 **삭제됐다** — 공개 URL은 만료되지 않으므로 TTL·재발급·갱신 개념 자체가 없다.
- **api는 사진 URL을 만들지 않는다** — `storage_path`만 반환한다(`ai_readonly` 최소권한, CR2). URL 조립은 web·app이 각자 한다. 이 불변식은 `api/tests/test_storage_signed_url_contract.py`가 지킨다.
  - **그 `storage_path`가 실리는 wire 필드가 `ListingCard.image_path`다**(§4, Story 9.6). `image_url`이 아닌 이유가 바로 이 줄이다 — api가 URL을 못 만들므로 원본 경로를 담을 자리가 따로 필요했다.
  - **강제 장치가 무엇을 지키는지 정확히** (✎ 2026-07-20 코드리뷰 정정 — 원래 *"위 contract test가 ①②의 쌍을 지킨다"*고 적혀 있었으나 **사실이 아니었다**):
    - ① *"응답에 Storage URL 문자열이 없다"* → `api/tests/test_storage_signed_url_contract.py`가 지킨다. 마커(`/storage/v1/`·`token=`)가 고장나면 red가 되는 positive fixture 4건까지 갖췄다.
    - ② *"`image_path`에 원본 경로가 **실제로** 실린다"* → **contract test는 이걸 못 지킨다.** 그 파일은 `run_search`를 통째로 스텁으로 바꾸고 손으로 만든 dict를 넣으므로, 사진 부착 코드를 전부 지워도 초록이다(증명되는 것은 "응답모델이 `image_path`를 직렬화한다"뿐). ②를 실제로 못박는 것은 **노드 배선 테스트 2건**이다 — `tests/test_doc_rag_node.py`·`tests/test_sql_rag_node.py`의 `test_cards_carry_cover_image_from_shared_helper`(둘 다 `attach_cover_images` 호출을 벗기면 red).
- **URL 헬퍼(범용, Story 9.0)**: `getPublicUrl(bucket, path)` — web `@/lib/storage`·app `core/supabase/storage_helper.dart` 두 곳에 미러.
  - **동기 함수이고 실패하지 않는다** — 네트워크 왕복 없이 경로에서 문자열을 조립할 뿐이다. 서버·브라우저 어디서든 호출된다(9.0 이전의 "서버에서만 발급 가능" 제약은 사라졌다).
  - ⚠️ **파일 존재를 확인하지 않는다.** 경로만 있으면 URL이 나온다 — 없는 파일은 이미지 로드가 실패하므로 **소비처가 `onError`로 "사진 준비중" 플레이스홀더를 그려야 한다**(§4). 서명 시절엔 실패가 `null`로 와서 자동으로 플레이스홀더가 됐지만, 이제는 소비처 책임이다.
  - 경로는 `/` 구분자를 살린 채 세그먼트별로 URL 인코딩한다(경로 전체에 `encodeURIComponent`를 걸면 구분자가 `%2F`가 되어 깨진다).

### 10.1 업로더가 지켜야 하는 규칙 (Story 9.3 — 전부 원격 실측으로 확정)

- **저장본 규격**: 업로드 전 클라이언트가 **긴 변 ≤1600px · WebP · quality 0.82**로 다시 인코딩해 올린다. 원본 5MB 상한과는 **별개 장치**다.
  - 왜: app은 저장된 **원본**을 그대로 받으므로(ADR-IMG-02) 원본을 저장하면 목록 다중 다운로드에서 NFR7이 깨진다.
  - 구현은 브라우저 네이티브 canvas(`web/src/lib/images/resize.ts`) — 새 의존성 없음. WebP를 못 만드는 환경은 `image/jpeg` 0.85 폴백.
  - **저장본 크기는 "범위"로 단언하지 않는다 — 실측 분포로만 말한다.** 2026-07-21 시딩 후 **대표사진 90장 전량** 실측: **최소 50KB · 중앙값 197KB · 평균 229KB · 최대 615KB**(편차 12배). 목록 한 화면(4열×3행=12장) 환산 **약 2.7MB**.
    - ⚠️ 여기 적혀 있던 *"실측 196~205KB"*(2026-07-18, 표본 3장)는 **값이 아니라 형태로 틀렸다** — 90장 중 그 범위에 드는 건 **1장뿐**이다. 그 좁은 숫자가 *"저장본이 이미 작으니 `next/image`가 필요 없다"* 는 결정의 근거로 쓰였다(`docs/tech-debt.md` #80).
    - **왜 정본에 남아 있었나:** Story 9.7이 #80을 닫으면서 `ListingCardImage.tsx` 주석만 고치고 *"정본은 코드 주석 쪽"* 이라 판단했는데, **실제 정본은 이 문서다**(계약값은 여기 하나). 코드리뷰 2026-07-21이 정정. #80의 등재 사유가 *"검산 안 한 숫자가 결정을 오염시켰다"* 인데 같은 오염원이 계약 문서에 남아 있던 자리다.
    - 총량이 유의미해진 쪽은 상세가 아니라 **목록**이다 — 후속 판단은 `docs/tech-debt.md` #83.
- **대표(cover) = `sort_order` 최솟값 행**이다. 대표는 **별도 상태가 아니다** — 순서와 대표를 각각 두면 진실이 두 군데 생겨 어긋난다. `is_cover`는 이 규칙의 **파생 결과**로만 기록한다.
  - ✎ **정정(spec-16-11 후속 코드리뷰, 2026-08-10): 이 줄은 원래 "대표 = `sort_order` 0번"이었다.** 앱(Flutter)이 부분 실패 경로에서 대표를 지키려고 **대표 후보에게 남아 있는 다른 번호보다 반드시 작은 값(필요하면 음수)** 을 주게 되면서, 대표가 숫자 0을 받는다는 보장이 사라졌다. 읽는 쪽 계약(§10.2 "대표는 `sort_order` → `id` 정렬의 첫 행")은 처음부터 최솟값 기준이었으므로 **읽는 쪽은 바뀐 것이 없다** — 어긋나 있던 것은 이 쓰는 쪽 문장이다. `sort_order`에 하한 CHECK는 없다(`0012_listing_images.sql` 실측).
  - ⚠️ **쓰는 쪽이 둘인데 규칙이 갈렸다(2026-08-10 현재).** 앱은 위 방식, **web(`web/src/app/(user)/sell/photo-sync.ts`)은 아직 0부터 연속으로 매기는 옛 방식**이다. 같은 `listing_images`를 두 writer가 서로 다른 규칙으로 쓰고 있다 — 열린 항목은 `deferred-work.md`에 있다.
  - **⚠️ 대표 대상을 두 번 계산하지 않는다.** 순서를 매기는 단계에서 **실제로 저장에 성공한 첫 장**(코드에서는 `coverAssigned`/`coverPath`로 부른다 — `sort_order=0`을 받았는지가 아니다, 바로 위 정정대로 대표가 0을 받는다는 보장이 없다)을 기억해 두고 대표 단계가 그 값을 쓴다. "저장된 것 중 첫 번째"를 나중에 다시 구하면, 어느 항목이 탈락하는지에 대한 두 계산의 판단이 갈려 **대표가 최솟값이 아닌 행에 붙는다**(코드리뷰 2026-07-19 2차 — 재현 실행으로 확인). 화면의 대표 배지도 저장 대상과 **같은 술어**로 골라야 화면과 DB가 갈리지 않는다.
    - ✎ **정정(spec-16-11 후속 코드리뷰 2회차, 2026-08-10): 이 줄은 원래 "실제로 `sort_order=0`을 받은 행을 기억해 둔다"고 적혀 있었다.** 바로 위 부모 항목이 "대표 = `sort_order` 0번"에서 "대표 = `sort_order` 최솟값 행"으로 고쳐질 때 이 자식 항목은 함께 고쳐지지 않았다 — 아래 347행의 "9.0이 앞 문장만 고치고 이 문장을 안 고쳐서 생긴 일"과 같은 패턴이 이 절에서 다시 재현된 것이다.
- **대표 교체는 반드시 2문장** — ① 해당 매물 전체 `is_cover=false` → ② 대상 1장만 `true`.
  - 왜: 부분 유니크 인덱스 `listing_images_one_cover_per_listing`은 DEFERRABLE이 아니라, 자연스러운 단일 UPDATE(`set is_cover=(id=:new) where listing_id=:L`)는 문장 중간에 대표가 2장이 되는 순간 **`duplicate key`로 죽는다**(도커 실측, `docs/tech-debt.md` #47-1).
- **삭제 순서는 "무엇을 지우는가"에 따라 둘로 갈린다.** (**매물 삭제 시 사진도 반드시 지운다** — §6.1)

  | 무엇을 지우나 | 순서 | 앞 단계가 실패하면 |
  |---|---|---|
  | **사진 1장**(편집 중 제거) | ① Storage 오브젝트 → ② `listing_images` 행 | ②를 하지 않는다 |
  | **매물 전체**(삭제 버튼) | ① `listings` 행 → ② 사진 오브젝트 정리 | **삭제를 되돌리지 않는다**(정리 실패는 비치명) |

  - ✎ **왜 매물 삭제만 순서가 반대인가 (코드리뷰 2026-07-19 — 사용자 결정).** 두 경우의 **되돌릴 수 없는 쪽이 다르다.** 사진 1장 제거는 행을 남겨두면 다시 지울 수 있으니 파일부터 지우는 게 맞다. 반면 매물 삭제에서 사진을 먼저 지우면, `listings` DELETE가 실패했을 때 **사진만 영구 소실**되고 매물은 살아남아 "사진 준비중"으로 박제된다(`syncListingPhotos`는 `storagePath`가 있는 항목을 건너뛰므로 재업로드도 안 된다). 게다가 정리 실패 시 삭제를 중단하면 **매물이 영영 삭제 불가**가 될 수 있다. 아래 정정대로 남은 파일은 **회수 가능한** 고아이므로, **회수 가능한 쓰레기 < 복구 불가능한 손실**이라는 판단으로 매물 삭제만 뒤집었다. 강제 지점: `web/src/app/(user)/sell/ListingActions.tsx` · `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx`.
  - ✎ **정정(Story 9.0, 2026-07-19): 이 순서는 더 이상 "안전"을 좌우하지 않는다(고아가 회수 가능해졌다). 사진 1장 제거의 순서는 관례로 유지한다.**
    - **전에는 왜 목숨이 걸렸나**: `storage.objects`의 SELECT 정책이 `listing_images` 행과 **조인**해야 참이 됐고, Storage API의 DELETE·LIST는 대상을 먼저 SELECT로 찾는다. 그래서 행을 먼저 지우면 그 객체는 소유자에게도 안 보여 **정상 권한으로 영영 못 지웠다**(#46 영구 고아 / #51). 실측(2026-07-18): 행 없는 객체 → DELETE `403`·LIST `200` 0건.
    - **지금은**: `0014`가 SELECT 정책을 **경로 기반**(`경로 첫 세그먼트 = auth.uid()` 또는 관리자)으로 바꿔 `listing_images` 행과 무관해졌다. **행이 없어도 소유자·관리자에게 보이고 지울 수 있다.** 원격 실측(2026-07-19): 행 없는 고아 객체가 소유자에게 **0건 → 1건**으로 보임, 비소유자 0건, anon 0건, 관리자 1건.
    - **그래서 #46의 "회수 불가" 구조가 사라졌다.** 순서를 지키는 코드는 그대로 두되(무해하고, 실패 처리가 명확하다), **이 순서를 못 지켜 재앙이 난다는 서술은 이제 사실이 아니다.**
  - **⚠️ 순서의 필수 귀결(사진 1장 제거에만 해당): ①이 실패하면 ②를 하지 않는다.** 오브젝트 삭제가 실패했는데 행을 지우면 고아가 생긴다 — "순서만 지키면 안전"이 아니라 **"앞 단계가 성공했을 때만 다음 단계"**가 계약이다. `deleteListingImageObject`가 boolean을 돌려주는 이유가 이것이며, 호출부는 그 값을 반드시 본다. 강제 장치: `web/src/app/(user)/sell/photo-sync.test.ts` "계약① 삭제 순서".
    - ✎ **2026-07-19 코드리뷰 정정 — 이 문장은 한동안 바로 위 "순서는 안전을 좌우하지 않는다"와 정면으로 모순된 채 같은 절에 있었다**(전자는 "영구 고아가 만들어진다", 후자는 "그 구조가 사라졌다"). 9.0이 앞 문장만 고치고 이 문장을 안 고쳐서 생긴 일이고, 그 사이 매물 삭제 코드는 **철회된 쪽**을 구현하고 있었다. 지금은 **고아가 회수 가능**하므로 "영구"는 사실이 아니다 — 그래도 사진 1장 제거에서는 이 순서를 지킨다(정리할 쓰레기를 굳이 만들 이유가 없다). **매물 전체 삭제에는 적용하지 않는다**(위 표).
  - **⚠️ 단 "매치 0건"은 실패가 아니다 — 파일이 이미 없다는 뜻이고, 목적은 달성돼 있다.** 원격 실측(2026-07-19, 코드리뷰 2차): **행 없음+파일 없음**과 **행 있음+파일 없음**은 응답이 `error=null, data=[]`로 **글자 그대로 같아 구별할 수 없다.** 그러나 대조군(**행 있음+파일 있음** → `data=[그 경로]`)이 "행이 있으면 있는 파일은 실제로 지워진다"를 증명하므로, **위 삭제 순서를 지켜 행이 살아 있는 동안 호출하면 빈 배열 = 파일 없음**이다. 이걸 실패로 취급하면 파일 없는 고아 행 하나가 **매물을 영구히 삭제 불가**로 만든다(재시도해도 같은 자리에서 멈춘다). 강제 장치: `web/src/lib/storage/upload.test.ts`.
  - **오브젝트 정리는 하나가 실패해도 나머지를 계속 시도한다.** 첫 실패에서 멈추면 이미 지운 앞부분은 되돌릴 수 없는데 뒤는 손도 못 댄 상태가 남는다. Storage와 DB에 걸친 트랜잭션이 없으므로 완전한 원자성은 불가능하다 — 정리 범위를 넓히고 결과를 사실대로 보고하는 것이 최선이다.
- **업로드에 `x-upsert`를 쓰지 않는다** — 업서트는 존재확인 SELECT를 거쳐 같은 이유로 `403`이 된다(실측). 파일명이 uuid라 충돌 자체가 없다.
- **`listing_images` 행 INSERT는 순차(직렬)로** 보낸다. 10장 트리거가 count-후-insert라 병렬 삽입은 경합으로 상한이 샌다(#49). ⚠️ 클라의 10장 차단은 **UX 층의 1차 방어일 뿐** — 서버 검증(트리거·버킷 설정)을 이것으로 대체하지 않는다.
- **`sort_order` 값은 한 매물 안에서 서로 겹치지 않는다.** 겹치면 tie-break가 `id`로 넘어가(#47-2) **사용자가 아래로 내린 사진이 대표가 될 수 있다.** 읽는 쪽은 `order by sort_order, id`로 2차 정렬을 건다.
  - ✎ **정정(spec-16-11, 2026-08-10): 이 줄은 원래 "항상 연속 정수 0..n-1로 다시 매긴다(구멍 금지)"였다.** 지켜야 하는 것은 **연속성이 아니라 유일성**이다 — 연속성을 지키느라 실패한 자리를 다음 항목이 메우면, **DB에 옛 번호를 그대로 들고 남은 실패 행**과 겹쳐 오히려 대표가 뒤집혔다(DW-748). 앱은 이제 저장 직전에 그 매물의 현재 `sort_order`를 한 번 읽어 "아직 비워지지 않았을 수 있는 번호"를 피한다.
  - ⚠️ **대표가 받는 값은 그 매물에 남아 있는 가장 작은 `sort_order`보다 항상 작다 — 재정렬뿐 아니라 삭제 실패로 남은 행 하나가 그 바닥을 끌어내린다.** 재정렬을 전혀 하지 않아도(예: 삭제 실패로 낮은 값에 박제된 행이 결함1 필터에 걸려 `saved`에서 영영 빠지는 경우) 매 저장이 그 행의 값을 피해 더 내려간다 — 바닥을 정하는 것은 재정렬 횟수가 아니라 그 매물에 남아 있는 행 중 가장 작은 `sort_order`다(실측 예시: 6회 재정렬 → 최솟값 `-6`). 기능상 문제는 없지만(`sort_order`는 화면에 노출되지 않는 내부 정렬키이고 모든 소비처가 정렬만 한다) **"0부터 연속"을 가정하는 코드·스크립트를 새로 쓰지 않는다.**
    - ✎ **정정(spec-16-11 후속 코드리뷰 2회차, 2026-08-10): "강제 장치: `app/test/photo_sync_test.dart`의 spec-16-11 그룹"은 과장이었다.** 확인 결과 `supabase/migrations/0012_listing_images.sql`의 `sort_order`엔 CHECK가 없고 `listing_images_listing_sort_idx`도 평범한 non-unique btree라 DB 제약이 없으며, web writer(위 331행 정정 참조)는 아직 옛(0부터 연속) 규칙이라 이 유일성 규칙 자체를 지키지 않는다 — **이 규칙 위반을 실제로 막는 장치는 지금 없다**(이름을 붙인 검사가 없는 것보다, 안 지키는 걸 지킨다고 적어 두는 쪽이 더 나쁘다 — 이 문서에 이미 여러 차례 기록된 패턴이다, 예: 298행 9.1 정정·312행 2026-07-20 정정). `photo_sync_test.dart`의 spec-16-11 그룹이 실제로 하는 일은 **앱(Flutter) writer 자신의 출력**이 이 규칙을 지키는지(중복 없음·대표가 fake의 최종 행 상태로도 최솟값)만 확인하는 것이다 — DB 제약도, web writer도 보지 않는다.

### 10.2 **읽는 쪽**이 지켜야 하는 규칙 (Story 9.4 — 목록 카드가 첫 소비처)

§10.1이 쓰는 쪽 규칙이라면, 여기는 **화면에 그리는 쪽** 규칙이다. 9.3까지는 소비처가 없어 "미래 약속"이었고 강제 장치가 없었다(`docs/tech-debt.md` #59). 9.4에서 소비처가 생기며 **실행되는 검사로 옮겼다**(B9).

- **정렬은 언제나 `order by sort_order, id`.** 2차 키를 빼면 `sort_order` 동률(#47-2)에서 조회할 때마다 대표가 바뀐다. 강제 장치: `web/src/lib/images/coverImages.test.ts`.
- **대표는 `sort_order` → `id` 정렬의 첫 행이다. 읽는 쪽은 `is_cover`를 보지 않는다.**
  - 왜: `is_cover`는 순서의 **파생 결과**일 뿐이고(§10.1), 시드·레거시 행은 전부 `is_cover=false`일 수 있다. 그것만 믿으면 사진이 있는데도 대표가 없다고 나온다.
  - 강제 장치: `coverImages.ts`의 입력 타입에 **`is_cover`가 아예 없다** — 읽고 싶어도 못 읽는다.
- **대표 0장은 정상 상태다** (#47-4 결정, 2026-07-19). 사진이 0장인 매물은 오류가 아니며, 화면은 **"사진 준비중" 플레이스홀더**를 그린다. 빈 영역이나 깨진 이미지 아이콘을 두지 않는다.
- **URL이 있다고 파일이 있는 것은 아니다.** `getPublicUrl`은 존재를 확인하지 않고 문자열을 만든다(9.0 공개 버킷 전환). 따라서 **플레이스홀더 폴백을 반드시 둔다** — 서명 URL 시절엔 발급 실패가 `null`로 와서 자동 처리됐지만, 지금은 이것이 깨진 이미지를 막는 유일한 장치다.
  - ⚠️ **`onError` 하나로는 부족하다 — 두 겹이어야 한다** (코드리뷰 2026-07-19, 실브라우저 실측으로 발견).
    서버 컴포넌트가 그린 `<img>`는 HTML이 도착하는 즉시 로드를 시작하는데, **하이드레이션이 끝나기 전에** 에러가 나면 React가 그 이벤트를 재생하지 않아 `onError`가 **영영 발화하지 않는다.** 그러면 위 규칙이 금지한 깨진 이미지가 그대로 남는다. 그리고 **파일 없음(404)은 정확히 그렇게 빨리 실패한다** — 가장 흔한 실패가 유일한 방어를 그냥 지나갔다.
    - **필수 2겹**: ① `onError`(하이드레이션 이후 실패) + ② **ref 콜백에서 `img.complete && img.naturalWidth === 0` 확인**(이미 끝난 실패 — 이벤트를 놓쳐도 이 상태는 남는다).
    - 재현법(회귀 확인용): **이미지 요청만 끊고 데이터 조회는 살린다** — Playwright에서 `**/storage/v1/object/public/**` 를 `route.abort()` 한 뒤 목록을 새로 로드한다. *"매물은 뜨는데 사진만 전면 실패"* 라는 정확한 상황이 만들어진다.
      - ⚠️ **`loading="lazy"` 때문에 화면 밖 카드는 요청 자체를 안 보낸다** — 스크롤로 전량을 뷰포트에 넣지 않으면 "전량 검증"이 아니다(Story 9.7에서 90장 중 38장만 폴백한 이유가 이것이다).
      - ~~`chrome-headless-shell --host-resolver-rules="MAP <supabase-host> 127.0.0.1"`~~ — 호스트 전체를 죽여 **데이터 조회까지 함께 끊기므로** 이 질문에 답하지 못한다. 이 환경에서 `chrome-headless-shell` 가용 여부도 확인된 적 없다. (✎ 2026-07-21 코드리뷰: Story 9.7이 실제로는 abort 방식을 썼는데 정본은 안 고쳐져 있었다 — 다음 사람이 안 쓰는 방법을 따라갈 자리.)
      → **"사진 준비중" 플레이스홀더가 떠야 한다.** alt 텍스트·깨진 아이콘이 보이면 폴백이 죽은 것이다.
    - 구현 참고: `web/src/components/listings/ListingCardImage.tsx`. **9.5(상세 갤러리)·9.6(AI 카드)도 같은 2겹을 둔다** — `onError`만 복사하면 같은 자리를 다시 밟는다.
      - ✅ **9.5 이행(2026-07-20)**: `web/src/components/listings/ListingGallery.tsx`가 대표·썸네일 **양쪽**에 2겹을 둔다. 실브라우저 red/green 확인 — `storage_path`를 없는 파일로 바꾸자 대표+해당 썸네일이 플레이스홀더로 떨어졌고(깨진 아이콘 0), 되돌리자 4장 전부 `naturalWidth=1600`으로 복귀했다.
- **대표 판별을 두 군데서 하지 않는다.** 계산 자리는 `web/src/lib/images/coverImages.ts` 하나다(9.3 코드리뷰의 교훈 — 두 번 계산하면 화면과 DB가 갈린다).

- 근거: `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md` ADR-IMG-01·CR2·"확정된 값"(2026-07-13) · 마이그레이션 `supabase/migrations/0012_listing_images.sql` · Story 9.3 Debug Log 1.

## 11. 옵션 통제어휘·우선순위 (Story 10.3)

`listings.options`는 정규화 테이블을 두지 않고 `text[]` 저장을 유지한다(연구 근거
`research-data-options.md` §112~113, A2 — 과설계 회피). 대신 **표준 옵션명 목록(통제어휘)**·
**`COMMON_OPTIONS`(보편·저순위)**·**`OPTION_PRIORITY`(옵션명→우선순위)** 를 값의 정본으로
여기 선언하고, `web/src/lib/options.ts`·`app/lib/features/listings/options.dart` 두 모듈이 이
값을 미러링한다(§1 `EMBEDDING_DIM`·§7 `CHAT.MESSAGE_MAX_LENGTH`와 같은 패턴). 두 사본이
어긋나지 않는지는 `app/test/listing_options_drift_test.dart`(web 소스를 상대경로로 직접 읽어
대조, `app_theme_color_drift_test.dart`와 같은 방식)가 실행되는 검사로 고정한다. **통제어휘
검증은 앱 레이어**(SellForm 제출 시)에서 한다 — DB CHECK·트리거는 두지 않는다(아래 "왜 DB
CHECK가 아닌가" 참조).

### 11.1 5개 카테고리 (엔카 분류 기준)

각 표준 옵션명은 **정확히 1개 카테고리**에 속한다. 동의어("HUD"/"헤드업디스플레이"/
"증강현실HUD", "후방카메라"/"후방센서"/"주차센서" 등)는 **통합하지 않고 각각 별도 표준
항목으로 그대로 수록**한다(동의어 통합=정규화라 범위 밖, A2).

| 카테고리 | 대표 항목(전체 목록은 `options.ts`가 정본 코드) |
|---|---|
| 안전 | 에어백·후측방경고·후측방모니터·차선유지보조·후방카메라·후방센서·후방감지센서·주차센서·원격주차·혼다센싱·후석알림 |
| 편의/멀티미디어 | 내비게이션·애플카플레이·블루투스·무선충전·무선업데이트·크루즈컨트롤·스마트크루즈·어댑티브크루즈·스마트키·에어컨·라디오·어라운드뷰·서라운드뷰·버추얼콕핏·HUD·헤드업디스플레이·증강현실HUD·뒷좌석모니터·후석엔터테인먼트·하이패스 + 오디오 브랜드(JBL사운드·렉시콘사운드·마크레빈슨·메리디안사운드·뱅앤올룹슨·부메스터사운드·하만카돈·프리미엄오디오) |
| 시트 | 열선시트·통풍시트·가죽시트·나파가죽·나파가죽시트·레더시트·메모리시트·릴렉션시트 |
| 외관/내장 | LED헤드램프·매트릭스LED·선루프·파노라마선루프·파노라마글래스루프·앰비언트라이트·전동트렁크·전동슬라이딩도어·슬라이딩도어·카본인테리어·요크스티어링·파워스티어링·열선스티어링·M스포츠패키지·M서스펜션·콰트로 |
| 기타옵션 | 7인승·8인승·9인승·11인승·V2L·초고속충전·급속충전지원·오토파일럿 + 통제어휘 밖 입력값(카테고리 그룹핑 시 폴백) |

**커버리지 불변식:** 통제어휘는 **현재 시드(`supabase/seed-local/data/listings.json`)에 실재하는
모든 distinct 옵션명을 빠짐없이 덮는다.** `web/src/lib/__tests__/options.test.ts`의 커버리지
테스트가 이걸 강제한다 — 시드에 통제어휘 밖 옵션이 하나라도 있으면 red.

### 11.2 우선순위 티어

71개 개별 점수를 매기지 않고 **티어**로 가른다:

- **`COMMON_OPTIONS`(보편, 강제 최저 티어)**: 후방카메라·후방센서·후방감지센서·주차센서·스마트키·블루투스·에어백·에어컨·라디오·파워스티어링·하이패스·애플카플레이·무선충전·열선시트·크루즈컨트롤·LED헤드램프·가죽시트·후석알림.
- **희소·셀링포인트(high)**: 선루프·파노라마선루프·파노라마글래스루프·HUD·헤드업디스플레이·증강현실HUD·통풍시트·어라운드뷰·서라운드뷰·어댑티브크루즈·스마트크루즈·차선유지보조·후측방경고·후측방모니터·오토파일럿·나파가죽·나파가죽시트·카본인테리어·오디오 브랜드 8종·V2L·초고속충전·릴렉션시트·앰비언트라이트·요크스티어링·콰트로·M스포츠패키지·M서스펜션·매트릭스LED·후석엔터테인먼트·뒷좌석모니터(선루프 계열이 최상위).
- **나머지(mid, 기본값)**: 위 두 목록 밖의 모든 표준 옵션.

**카드 = 우선순위 상위 3개 + 나머지 개수 오버플로 칩**(희소 우선, 동점은 입력순). 전부 보편이면
보편에서 채운다(fallback — 빈 칩 행 금지). **칩 글자는 자르지 않는다** — 폭이 모자라면 웹은 칩을
통째로 감추고(`shrink-0` + `overflow-hidden`), 앱은 가로 스크롤로 흡수한다(오버플로 칩은 스크롤
밖에 고정해 항상 보이게 한다). 어느 쪽도 `truncate`로 글자를 줄이지 않는다.

> **⚠️ 오버플로 칩은 웹과 앱이 다르다(2026-08-09 Story 16.9, 의도된 편차 — 대장 DW-762).**
> 표기가 웹은 `+N`, 앱은 `외 N개`다(앱은 시각 스파인 `DESIGN.md` §L128을 따르기로 16.9가 명시
> 확정). **N을 세는 기준도 다르다** — 웹은 원본 배열 길이 기준, 앱은 중복 제거 후 기준이라 중복
> 값이 섞인 매물은 같은 데이터로 서로 다른 숫자를 보여준다. 표기는 의도된 편차지만 **계수 기준
> 불일치는 계산 규칙 차이라 통일이 필요하다** — 결론은 DW-762에서 낸다. 그전까지 이 절을 근거로
> 한쪽을 다른 쪽에 맞춰 "고치지" 말 것.
**상세 = 카테고리별 전량**(희소 필터 없음, 통제어휘 밖 값은 `기타옵션`으로 그룹핑).

> **왜 4→3인가 (사용자 결정 2026-07-29):** 상한이 4일 때 칩들이 `shrink`+`truncate`로 나란히
> 쪼그라들어 **전부** `통…`·`파노…`로 잘렸다 — 옵션이 4개 있다는 사실만 알리고 무슨 옵션인지는
> 하나도 못 읽는 상태. "몇 개를 못 보여주더라도 보이는 건 온전히 읽힌다"로 실패 방향을 뒤집었다.

### 11.3 왜 DB CHECK가 아니라 앱 검증인가

옵션명이 비표준이어도 대가는 무결성 손상이 아니라 **표시상 미분류(`기타옵션`)·저순위**일
뿐이다(FR11·채팅길이 같은 계약과 성격이 다르다). 통제어휘를 DB CHECK로 강제하면 71개+
목록을 SQL에도 **사본으로 한 벌 더** 둬야 하는데, 그 사본은 실행되는 대조 검사가 없어 반드시
늙는다(이 저장소가 이미 3건 실측한 실패 방식 — `project-context.md`). 그래서 검증은 쓰기 UI
(`SellForm.tsx`) 층에 둔다. 10.4의 하이브리드 칩 피커는 이 검증을 **구조적으로**(비표준
입력 자체가 불가능하게) 승격한다.

값 정본은 이 문서(§11)이고, **미러는 두 벌**이다 — `web/src/lib/options.ts`와
`app/lib/features/listings/options.dart`. 둘 다 헤더에 "정본: conventions.md §11"을 명시한다.
코드(카테고리 배치·티어 배열)를 바꾸려면 **이 문서를 먼저** 고친다.

**드리프트 검사가 보는 것과 못 보는 것**(`app/test/listing_options_drift_test.dart`가 web 소스를
상대경로로 직접 읽어 대조 — `app_theme_color_drift_test.dart`와 같은 방식): **보는 것** = 통제어휘
전체 집합 · `COMMON_OPTIONS` · 희소(high) 목록 · 카드 노출 개수(`cardOptionCount` ↔ web
`CARD_OPTION_COUNT`). **못 보는 것** = `optionPriority()`/`topOptions()` **함수 본문의 선택 로직**
(양쪽 각자 단위테스트만 있고 서로 대조하지 않는다) · 위 §11.2가 적은 오버플로 표기·계수 기준
차이(DW-762). 이 문서가 "검사로 고정된다"고 말하는 범위는 **보는 것**까지다.

### 11.4 인기 옵션 (등록 피커 퀵칩)

등록 폼의 하이브리드 옵션 피커(`web/src/app/(user)/sell/OptionPicker.tsx`, Story 10.4)가
기본으로 퀵칩 8종을 노출한다: **스마트키·내비게이션·후방카메라·열선시트·통풍시트·선루프·
크루즈컨트롤·어라운드뷰.** 전부 표준 옵션명(§11.1 캐노니컬명 — "내비"·"크루즈" 같은 축약형
금지)이며 `ALL_CONTROLLED_OPTIONS`의 부분집합이다.

희소 판정은 별도 목록을 두지 않고 §11.2의 high 티어를 그대로 쓴다 — `isRareOption(name)`이
true(= high 티어 소속)면 전체 옵션 목록에서 그 항목에 "희소" 태그를 붙인다.

## 12. 채팅 실시간 구독 계약 (Story 12.3)

Story 12.3이 웹의 3초 폴링을 걷어내고 `supabase/migrations/0023_chat_realtime_broadcast.sql`이
놓은 Broadcast+RLS 토대를 처음 소비한다. 이 절은 **그 소비 규칙의 단일 출처**다 — Epic 16
Story 16.4(Flutter 앱 미러링)가 같은 계약을 그대로 따라야 하므로, 값이 바뀌면 이 문서를 먼저
고치고 web·app 양쪽에 반영한다.

⚠️ **이 절은 §1 `EMBEDDING_DIM`·§7 `CHAT.MESSAGE_MAX_LENGTH`와 강제 방식이 다르다.** §1·§7은 코드가
**실제로 import해서 쓰는 공유 상수 하나**라 한쪽만 고치면 타입 불일치·빌드 실패로 드러난다. 반면
§12.1의 토픽 형식은 언어가 달라 공유가 불가능하고, **서로 다른 네 곳에 각자 따로 쓰인 문자열
리터럴**로 존재한다:

1. `supabase/migrations/0023_chat_realtime_broadcast.sql` — 트리거(방송)와 RLS 정책(구독 인가)
2. `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `roomTopic()` — 구독
3. `api/tests/integration/test_chat_realtime_broadcast_real_db.py`의 `_TOPIC_PREFIX` — 실DB 검증
4. `app/lib/features/chat/chat_repository.dart`의 `roomTopic()` — 구독(Epic 16.4, Flutter 앱)

한쪽만 바뀌어도 컴파일도 lint도 통과하므로, 이 계약은 문서가 아니라 **실행되는 검사**로 고정한다
(CLAUDE.md B9): `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`가 네 사본을
읽어 같은 문자열인지 단언하고 `private: true` 구독도 함께 확인한다 — `npm test`(vitest)에 포함되므로
CI에서 매 push마다 돈다. 값을 바꿀 땐 네 곳을 함께 고치고, 그 검사가 green인지 확인한다.

### 12.1 구독 토픽 형식

- **`` `chat:room:${roomId}` ``** — 0023의 트리거(`'chat:room:' || new.room_id::text`)·RLS
  정책(`'chat:room:' || r.id::text = realtime.topic()`) 리터럴과 **문자 그대로** 동일해야 한다.
  한쪽만 바뀌면 조용히 깨진다(방송은 계속 나가는데 아무도 못 듣거나, 반대로 존재하지 않는 방
  이름으로 구독을 시도하게 된다) — 값을 바꿀 땐 세 곳을 함께 고치고, 위 도입부가 가리키는
  `roomTopicContract.test.ts`가 green인지 확인한다(그 검사가 이 일치를 고정한다).
- web `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`의 `roomTopic()` 헬퍼가 이 형식을
  만든다. Epic 16.4가 `app/lib/features/chat/chat_repository.dart`에 같은 이름의 top-level
  함수 `roomTopic(String roomId) => 'chat:room:$roomId'`로 이 문자열 템플릿을 그대로 옮겼다 —
  이 자리가 위 도입부가 말하는 네 번째 사본이다.

### 12.2 private 채널 + setAuth 타이밍

- `supabase.channel(topic, { config: { private: true } })`로 구독한다 — `private: true`가
  있어야 Realtime 서버가 `realtime.messages` RLS(0023)를 실제로 평가한다.
- **구독(`channel.subscribe()`) 전에** 현재 세션의 access token으로
  `supabase.realtime.setAuth(token)`을 호출한다(Realtime Broadcast Authorization 공식 패턴) —
  RLS의 `auth.uid()`가 이 토큰에서 나온다. 순서를 지키지 않으면(구독 후 setAuth) 첫 구독 시도가
  무인가 상태로 나가 거부될 수 있다.
- `onAuthStateChange`(토큰 갱신)마다 **다시** `setAuth`를 호출한다 — 세션이 길어져 access token이
  회전되는 동안 구독이 만료된 토큰으로 굳지 않게 한다. (참고: `@supabase/supabase-js` 클라이언트
  자체도 `TOKEN_REFRESHED`/`SIGNED_IN`에서 내부적으로 비슷한 재동기화를 하지만, 초기 로드 시점의
  최초 `setAuth`는 이 규칙이 명시적으로 책임진다 — 내부 동작에 기대지 않는다.)
  - ✎ **Dart 예외(Epic 16.4 코드리뷰, 실측)**: 위 두 규칙(구독 전 수동 `setAuth` + `onAuthStateChange`
    마다 재호출)은 web(`@supabase/supabase-js`)에 대한 것이다 — 그 클라이언트는 이 재동기화를
    보장하지 않으므로 수동 배선이 필요하다. Dart `realtime_client-2.8.0`
    (`~/.pub-cache/hosted/pub.dev/realtime_client-2.8.0/lib/src/realtime_channel.dart:165-190`,
    실측 확인)은 사정이 다르다 — 채널이 매 join/rejoin마다 `socket.accessToken`(항상 최신 세션
    토큰)을 join payload에 실어 보내고, 응답 후 `socket.setAuth(socket.accessToken)`을
    **라이브러리가 자동으로** 호출한다. 그래서 앱(`app/lib/features/chat/chat_room_screen.dart`)은
    구독 전 수동 `setAuth`도, `onAuthStateChange → setAuth` 재호출도 어느 쪽도 부르지 않는다
    (스펙 spec-16-4 Never 절 — 검증 없이 "당연히 이식"하면 없어도 될 상태 배선이 하나 늘어난다).
    "내부 동작에 기대지 않는다"는 위 web 규칙과 모순되지 않는다 — web은 라이브러리가 그 보장을
    안 하니 수동 배선으로 명시 책임지는 것이고, Dart는 라이브러리 자신이 그 재인증을 실측으로
    보장하므로 그 계약에 기대는 것이지 "확인 안 하고 넘겨짚는 것"이 아니다.

### 12.3 payload 파싱 규칙

- 구독 콜백은 `channel.on('broadcast', { event: 'INSERT' }, (message) => { ... })` 형태다.
  `chat_messages_broadcast()` 트리거(0023)가 매 INSERT마다 이 이벤트로 방송한다(UPDATE/DELETE는
  이 테이블에 없다 — 0003 헤더: chat_messages는 영속·불변).
- **신규 행은 `message.payload.record`에 실려 온다**(Realtime의 `realtime.broadcast_changes()`
  payload 계약 — `record`=신규 행, `old_record`=NULL(AFTER INSERT라 항상)). 이 행을 그대로 기존
  `mergeIncoming`(dedupeById + `(created_at, id)` 정렬)에 합류시킨다 — **도착 순서가 아니라 정렬
  결과로 렌더한다**(방송이 초기 로드보다 먼저 도착해도, 늦게 와도 최종 화면은 항상 시간순).
- 방 진입 시 1회 전체 `fetchMessages` 로드는 그대로 유지한다 — 구독 이전에 쌓인 과거 메시지를
  보여줄 유일한 경로다. 그 이후 주기 재조회(폴링)는 없다.
- **그 전체 로드는 "최초 `SUBSCRIBED`" 때 한 번 더 돌려 구독 시작점까지 닿게 한다.** 첫 조회는
  구독보다 먼저 나가므로(`getSession`→`setAuth`→웹소켓 join이 끝나기 전) 그 틈에 들어온 INSERT는
  조회 응답에도 없고 방송으로도 오지 않는다 — 폴링이 없어 복구 경로가 새로고침뿐이라 그대로 두면
  조용한 영구 유실이 된다. **재연결 때마다 도는 갭 보정이 아니다**(그건 Story 12.4 범위) —
  최초 1회로 한정한다.

### 12.4 멱등 전송(client_message_id)

- `sendMessage`(`web/src/lib/messages.ts`)는 매 전송마다 호출부가 만든 `client_message_id`
  (`crypto.randomUUID()` 관례)를 INSERT에 싣는다. DB의 `UNIQUE(room_id, client_message_id)`
  (`chat_messages_room_client_message_unique`, 0022)가 같은 키의 재INSERT(네트워크 재시도)를
  `23505`로 거부한다.
- `sendMessage`는 `23505`를 에러로 올리지 않고 `(room_id, client_message_id)`로 **기존 행을
  조회해 그 행을 반환**한다 — 클라이언트 입장에서 재전송은 항상 "성공(그 행으로 수렴)"으로
  보인다. `chat_messages`엔 정확히 1행만 남는다.
- 화면은 전송 시작 시점(요청을 보내기 전)에 이미 `client_message_id`를 만들어 pending 버블을
  띄운다 — "자기 `sendMessage` 응답"과 "브로드캐스트 에코" 중 같은 키를 가진 실제 행이 **먼저
  도착하는 쪽**으로 pending을 확정한다(레이스 대비 이중 경로, 늦게 오는 쪽은 이미 지워진
  pending과 dedupeById가 중복 렌더를 막는다).
- `client_message_id`는 nullable이다 — 0022 이전(Story 12.3 도입 이전) 행은 `NULL`로 남는다.
  그래서 매칭은 **"기다리는 키가 있을 때만"** 한다 — 가드를 pending 쪽에 건다. 등호만 쓰면
  `null === null`이 참이라 옛 행 두 건이 서로 같은 전송으로 오인된다. 가드를 `record`
  쪽(`record.client_message_id != null`)에 걸어도 그 오인 자체는 막히지만, 정작 "확정할 pending이
  없는데 매칭 분기에 들어가는" 경우를 못 막으므로 **pending 쪽이 정본**이다.
  (Epic 16.4가 Dart로 옮길 때 이 순서를 그대로 따른다.)
  - ✎ **2026-07-29 Story 12.4 정정**: pending이 단일 값(`pendingIdRef`)이던 12.3 시점엔 위 가드가
    `if (pendingIdRef.current && record.client_message_id === pendingIdRef.current)`였다. 12.4가
    pending을 큐(배열)로 확장하면서(§12.5) 이 등호 비교가 **배열 탐색**으로 바뀌었다 —
    `record.client_message_id`가 큐의 어느 항목과도 일치하면 그 항목만 큐에서 제거한다. "기다리는
    키가 없으면 매칭하지 않는다"는 원 규칙(빈 큐는 아무 항목과도 일치하지 않으므로 자동으로 같은
    효과)은 그대로 유지된다 — 자료구조만 바뀌었을 뿐 규칙은 바뀌지 않았다.

## 12.5 재연결 배너 + 오프라인 큐잉 + 갭보정 (Story 12.4)

Story 12.3이 폴링을 걷어내며 남긴 구멍 — "연결이 끊기면 새로고침 말고는 복구 경로가 없다" —
을 이 절이 메운다. `ChatRoomMessages.tsx`의 **기존 `channel.subscribe(callback)` 콜백 하나**가
계속 확장의 유일한 배선판이다(§12.2가 이미 그렇게 정했다) — 이 절이 추가하는 것은 그 콜백이
이미 구분하던 상태 전이(CHANNEL_ERROR/TIMED_OUT ↔ SUBSCRIBED)에 새 반응(배너·큐 flush·갭보정)을
붙이는 것이지, 새 재구독·소켓 재생성 경로가 아니다.

- **연결 상태 판단은 두 전이만 본다**: `CHANNEL_ERROR`/`TIMED_OUT`(끊김) ↔ `SUBSCRIBED`(재연결,
  이전에 끊긴 적이 있을 때만). `CLOSED`는 이 판단에서 제외한다 — 실측(`@supabase/realtime-js`
  2.108.2 소스): 네트워크 드롭은 `CHANNEL_ERROR`/`TIMED_OUT`으로만 오고, 채널이 소켓 재연결마다
  자동으로 `rejoin()`한다(`socket.onOpen()` 리스너). `CLOSED`는 명시적 `leave()`(방 전환·언마운트)
  에서만 발생하며 12.3의 `cancelled` 가드가 이미 무해화한다 — 그래서 12.3이 두던 CLOSED 분기(회색
  경고 문구)는 그대로 두고, 이 절의 배너 로직은 CHANNEL_ERROR/TIMED_OUT/SUBSCRIBED 세 상태만 새로
  분기한다. **수동 재구독·채널/소켓 재생성 코드는 만들지 않는다** — 라이브러리의 자동 재조인과
  중복돼 오히려 혼란을 더한다.
- **배너**: 끊김 시 "연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요."(비차단 —
  입력·전송 버튼을 잠그지 않는다, FR42·UX-DR19). 재연결(SUBSCRIBED, 이전에 끊긴 적 있음) 시
  초록 "다시 연결됐어요"로 바뀐 뒤 일정 시간(예시값 3000ms) 후 자동 소멸한다 — 색만이 아니라
  텍스트도 함께 표기해 접근성 비색 신호를 중복시킨다.
- **오프라인 큐잉**: 끊긴 동안 제출한 메시지는 `sendMessage` 네트워크 호출을 **시도하지 않고**,
  제출 시점에 만든 `client_message_id`로 즉시 pending 버블을 띄우며 로컬(인메모리, `localStorage`
  등으로 영속화하지 않음) 큐에 순서대로 적재한다. 여러 건 동시 대기가 가능해야 하므로 12.3의 단일
  `pending` 값을 큐(배열)로 확장한다. 재연결되면 큐를 순서대로(순차 await) 기존 `sendMessage()`로
  flush한다 — **큐잉 시점의 `client_message_id`를 그대로 재사용**한다(새 키 생성 금지). 재시도해도
  DB의 `UNIQUE(room_id, client_message_id)`(§12.4, 0022)가 `23505`로 흡수해 멱등이 성립한다.
  실패한 항목은 버리지 않고 큐 맨 앞에 남겨 다음 재연결 때 재시도한다(순서 보존). 이 순차 flush
  알고리즘(성공분은 반영, 실패 시 그 항목부터 뒤 전부를 remaining으로 남기고 멈춤)은
  `web/src/lib/messages.ts`의 순수 함수 `flushMessageQueue`에 있고 `messages.test.ts`가 vitest로
  검증한다(B9) — 화면 컴포넌트는 이 함수에 실제 `sendMessage` 호출을 감싸 넘기기만 한다.
  - 왜 60초 재사용 창(`reuseFailedKey`, §12.4)을 큐 **flush**에 안 쓰는가: 그 휴리스틱은 "이번
    제출이 방금 실패한 그 제출의 재시도인가"를 본문 일치 + 시간창으로 **추측**한다. 큐 flush는 그
    추측이 필요 없다 — 어떤 항목을 재시도하는지 큐 자체가 이미 알고 있다.
    - 단, **제출 시점의 키 선택**은 온라인·오프라인이 같은 규칙을 쓴다(후속 리뷰 정정). 오프라인
      큐잉에서만 무조건 새 키를 만들면 "온라인 전송 실패(서버엔 저장, 응답만 유실) → 입력 복원 →
      그 사이 끊김 → 그대로 재전송"에서 새 키로 저장돼 **실제 중복 행**이 생긴다. 큐에 넣은 뒤에는
      그 키를 큐가 인수하므로 `lastFailedRef`는 비운다.
- **끊긴 동안 화면을 잠그지 않는다는 것은 입력창·전송 버튼의 `disabled`까지 포함한다**(후속 리뷰
  정정). 온라인 전송의 연타 가드(`sending`)를 끊김 상태에서도 걸면, 응답을 기다리던 중에 연결이
  죽는 가장 흔한 순서에서 그 요청이 끝날 때까지 제출이 무반응이 된다(supabase-js 호출엔 타임아웃이
  없다) — 배너 문구와 화면이 모순된다. 끊김 상태의 제출은 네트워크 왕복이 아니라 로컬 큐잉이므로
  애초에 연타로 보호할 대상이 아니다.
- **flush가 다 못 보내면 몇 건이 남았는지 화면에 남긴다**(후속 리뷰 정정, fail-loud). 남은 pending
  버블은 정상 전송 중 버블과 시각적으로 동일하고, 재시도 트리거는 "다음 끊김→재연결"뿐이라 연결이
  계속 정상이면 영영 재시도되지 않는다 — 콘솔 로그만으로는 사용자가 알 방법이 없다.
  - **이 안내는 전송 에러 칸(`error`)에 쓰지 않는다**(3차 후속 리뷰 정정). 그 칸은 제출마다
    무조건 비워지는 자리이고(§12.3이 `realtimeError`·`loadError`를 굳이 갈라둔 것과 같은 이유),
    큐가 막힌 사용자의 가장 자연스러운 다음 행동이 "한 번 더 보내보기"다 — 그 순간 유일한 미전송
    신호가 사라져 화면이 완전히 정상으로 보인다. **수명이 다른 신호는 다른 칸에 둔다**가 이 파일의
    규칙이고, 이 안내는 "큐가 실제로 비워질 때"만 지운다.
  - **문구는 실제 재시도 트리거대로 적는다**(3차 후속 리뷰 정정). 재시도는 SUBSCRIBED 재도달 분기
    하나에서만 일어나므로 "연결이 회복되면 다시 시도합니다"는 거짓이다 — 그 시점엔 연결이 **이미**
    회복돼 있고, 실제로는 **다시 끊겼다 붙어야** 돈다. 안내가 약속하는 동작과 코드가 하는 동작이
    다르면 fail-loud를 지킨 것이 아니다.
- **flush 진행 중에 들어온 재요청은 버리지 말고 미룬다**(후속 리뷰 정정). 중복 실행 가드가 요청을
  그냥 반려하면, flush가 도는 동안 flap으로 큐잉된 항목이 이미 시작된 flush의 스냅샷에도 없고 새
  flush도 뜨지 않아 다음 끊김까지 정체된다 — 가드는 "재실행 예약" 플래그와 짝을 이뤄야 한다.
- **한 pending 항목의 소유권은 한 경로만 갖는다**(3차 후속 리뷰 정정). pending 큐는 "온라인 전송
  중"과 "오프라인 대기"를 한 배열에 섞어 담으므로, 전송 중에 끊겼다 붙으면 flush가 아직 응답을
  못 받은 그 항목까지 스냅샷에 넣어 **같은 키로 두 요청을 동시에** 띄운다. 멱등키가 실제 중복
  행은 막지만 두 완료 핸들러가 같은 항목에 대해 서로 다른 화면 갱신(에러 표시·입력 복원 vs 성공
  병합)을 한다 — flush는 온라인 경로가 응답을 기다리는 중인 키를 제외한다.
- **온라인 전송 실패 시 입력 복원은 입력창이 비어 있을 때만 한다**(3차 후속 리뷰 정정). 끊김 중
  입력창 잠금을 푼 뒤로 "전송 → 응답 대기 중 끊김 → 그 사이 다음 메시지를 타이핑"이 정상 경로가
  됐으므로, 뒤늦게 도착한 실패 응답이 무조건 옛 본문을 써 넣으면 사용자가 쓰던 글이 사라진다.
  §12.4의 브로드캐스트 에코 경로가 이미 같은 이유로 함수형 갱신을 쓴다 — 같은 규칙을 실패 경로
  에도 적용한다.
- **끊긴 채로 방을 나가거나 새로고침하면 큐는 사라진다 — 이건 감수한 손실이지 복구되는 것이
  아니다**(3차 후속 리뷰 정정). 큐 항목은 **정의상 아직 서버에 INSERT되지 않은** 것이라
  `fetchMessages`(초기 전체 로드)가 되살릴 수 없다. "새로고침은 기존 경로로 복구된다"는 설명은
  이미 저장된 메시지에만 참이며 큐에는 적용되지 않는다. 인메모리 비영속은 데모 규모에서 의도적으로
  택한 절충이고, Epic 16.4가 이 절을 미러링할 때 **근거를 그대로 옮기지 말고 이 정정된 사실을**
  옮긴다.
- **갭보정(AC-CHAT-2, CR6)**: 재연결마다 두 경로를 **항상 함께** 수행한다.
  1. **Broadcast Replay** — 채널 생성 config에 `broadcast.replay`를 추가해 구독 시점에 최근 이력
     (플랫폼 기본 한도 ≤25건/72시간)을 같은 `broadcast`/`INSERT` 이벤트로 재생받는다. 별도 소비
     코드가 필요 없다(기존 `channel.on('broadcast', { event: 'INSERT' }, ...)` 핸들러가 그대로
     받는다). 이 config는 재조인 시에도 재사용되므로 최초 채널 생성 시 한 번만 추가한다.
     - ⚠️ **그 재사용에는 대가가 있다(3차 후속 리뷰 정정 — 이 사실은 코드 주석에만 있었다).**
       `since`가 `Date.now() - 72시간`으로 **채널 생성(마운트) 시점에 한 번만 계산**되고 그 값이
       재조인마다 그대로 다시 쓰이므로, 실제 커버 구간은 "지금부터 72시간 전"이 아니라 "이 방에
       처음 들어온 시각으로부터 72시간 전"으로 고정된 채 **탭이 오래 떠 있을수록 과거 쪽으로
       밀린다**. 이게 안전한 유일한 이유는 아래 2번(커서 재조회)이 replay의 커버 여부와 무관하게
       재연결마다 **항상** 도는 백스톱이기 때문이다. Epic 16.4가 미러링할 때 이 사실을 함께
       옮긴다 — 백스톱 없이 replay만 옮기면 그 시점에 조용한 유실이 된다.
     - ⚠️ **API 계약 정정(2026-07-29 실측)**: `@supabase/realtime-js@2.108.2`의 `replay`는 불리언이
       아니라 `{ since: <필수, epoch ms>, limit?: <=25> }` 객체다(타입·README 확인). `{ replay: true }`
       는 tsc 컴파일 자체가 안 된다. web 구현은 `since = Date.now() - 72시간`, `limit = 25`를 넘긴다.
       - 이 두 값의 출처를 정확히 구분한다(후속 리뷰 정정): **`limit`의 상한 25만 라이브러리가 정한
         값**이고(그 최대치를 그대로 요청한 것), **72시간은 우리가 고른 값**이다 — `since`는 필수
         인자라 무엇이든 골라야 한다. "플랫폼 기본 한도를 그대로 쓴다"는 표현은 `since`에 대해서는
         맞지 않는다. Epic 16.4가 Dart로 미러링할 때 72h를 "플랫폼 규정값"으로 오해하지 않도록 이
         구분을 그대로 옮긴다.
     - ⚠️ **replay는 삭제된 행도 재생할 수 있다(2026-07-29 로컬 실측 — 이 스토리의 verification
       중 실제로 걸림)**. `realtime.messages`(replay가 읽는 원장)는 `chat_messages`의 삭제와
       동기화되지 않는다 — 과거 수동 검증 중 직접 SQL로 지운 chat_messages 행의 방송 payload가
       `realtime.messages`엔 최대 72시간 남아 있어, 그 방에 재연결하면 **이미 지워진 메시지가
       되살아나 보였다**(로컬 E2E `viewport-audit.spec.ts`의 채팅방 오버플로 검사가 이 잔재로
       실제로 red가 됐다 — 긴 URL 테스트 메시지의 방송 로그가 남아 있었음). 실제 제품에서는
       `chat_messages`가 append-only(0003 헤더 — UPDATE/DELETE 경로가 없다)라 이 문제가 발생하지
       않는다 — **수동 SQL로 chat_messages를 직접 지우며 실시간 검증을 했을 때만** 나타나는
       로컬 개발 환경 함정이다. 같은 방식으로 수동 검증할 때는 지운 행의 `realtime.messages` 잔여
       행도 함께 지운다(`delete from realtime.messages where topic = 'chat:room:{roomId}' and
       (payload->'record'->>'id') not in (select id::text from chat_messages where
       room_id = '{roomId}')`).
  2. **커서 재조회** — 마지막으로 반영한 메시지의 `created_at`을 커서로 `fetchMessages(supabase,
     roomId, cursor)`(`gte`, §12.4 CR6와 동일 규칙 — strict `>` 아님)를 재연결마다 호출한다.
     Replay의 한도(≤25건/72h)를 넘는 gap은 이 경로만 채운다. Replay가 실패하거나 한도를 넘겨도
     이 경로는 독립적으로 항상 돈다 — 두 경로가 겹쳐 반환해도 기존 `mergeIncoming`/`dedupeById`
     (id 기준)가 중복 없이 접는다.
  - 이 한도(`limit ≤ 25` + 우리가 고른 `since` 창)를 client 코드로 재구현하거나 우회하지 않는다 —
    커서 재조회가 그 몫을 이미 메운다. (위 API 계약 정정대로 "둘 다 플랫폼 기본값"이 아니다.)
  - **두 경로의 보호 강도는 커서 쪽이 더 세야 한다.** replay는 있으면 좋은 최적화이고 커서 재조회가
    항상 맞는 백스톱인데, 초기엔 replay에만 실행되는 검사가 붙어 있었다(3차 후속 리뷰에서 정정 —
    `roomTopicContract.test.ts`가 재연결 분기의 `gapFillFromCursor()` 배선과 커서 인자 전달을 함께
    고정한다).
  - **커서 재조회가 성공해도 그것이 지우는 안내는 자기가 세운 것뿐이다**(3차 후속 리뷰 정정).
    커서 이후만 본 조회의 성공은 "그 이전 구간도 잘 있다"는 증거가 아니므로, 초기 전체 로드가
    실패해 과거 대화가 비어 있다는 경고까지 함께 지우면 대화가 통째로 빠진 화면이 "정상"으로
    보인다. 커서 없이(전체 재조회로) 돈 경우에만 초기 로드 실패 안내도 함께 거둔다.
- **네트워크 상태 감지에 `navigator.onLine`/`online`/`offline` 이벤트를 쓰지 않는다** — 실측상
  라이브러리는 순수 웹소켓 신호(끊김·heartbeat 타임아웃)로만 재연결하며 그 신호는 이미
  `channel.subscribe` 콜백으로 들어온다. 채널 status 콜백 하나로 충분하다.
- 이 절이 확장하는 파일: `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(배너·큐·갭보정
  배선)·`web/src/lib/messages.ts`(`QueuedMessage` 타입·`flushMessageQueue` 순수 함수). Epic 16.4가
  Flutter로 미러링할 때 이 절 전체(§12.5)를 그대로 따른다.

## 12.6 안읽음 배지 + 방 목록 정렬 계약 (Story 12.5, FR57)

Epic 16 Story 16.4(Flutter 안읽음 미러링, §12.5의 실시간 구독 미러링과 같은 선례)가 참조할
단일 출처다. 값이 바뀌면 이 문서를 먼저 고치고 web·app 양쪽에 반영한다.

- **테이블**: `chat_room_reads(user_id, room_id, last_read_at)` — 복합 PK `(user_id, room_id)`,
  둘 다 `on delete cascade`(`supabase/migrations/0024_chat_room_reads.sql`). "이 사용자가 이
  방을 마지막으로 언제 열었나"만 담는다 — 집계·비정규화 컬럼 없음(A2, 0018 wishlists와 동일한
  "본인 소유 관계 테이블 + 단순 RLS" 패턴).
- **정렬 기준**: `chat_rooms.last_message_at`(신설 컬럼) — 방 생성 시각(`created_at`)이 아니라
  **그 방의 마지막 메시지 시각**. `chat_messages` AFTER INSERT 트리거 `chat_messages_touch_room_last_message`
  (실행 함수는 `chat_rooms_touch_last_message()`, SECURITY DEFINER — `chat_rooms`는 UPDATE 정책이
  없어 authenticated 권한으로는 이 갱신이 불가능하다)가 매 INSERT마다 `greatest(기존값, 새 시각)`로
  단조증가만 허용하며 갱신한다(코드리뷰 patch — 동시 전송 등으로 커밋 순서가 시각순과 어긋나도
  정렬 기준이 되돌아가지 않는다). 방 목록(`web/src/app/(user)/chat/page.tsx`)은
  `.order('last_message_at', { ascending: false }).order('id', { ascending: false })`로 정렬한다
  (동시각 안정화용 id 2차정렬은 기존 관례 유지).
- **안읽음 집계 공식**: 내가 당사자인 방의 `chat_messages` 중 `sender_id <> auth.uid()`이고
  `created_at > coalesce(그 방의 내 chat_room_reads.last_read_at, '-infinity')`인 행의 개수.
  이 공식을 구현하는 자리는 `chat_unread_count()` RPC(인자 없음, SECURITY INVOKER) **하나뿐**이다
  — 화면·다른 쿼리가 이 계산을 다시 구현하지 않는다. INVOKER인 이유: 호출자 자신의 기존
  RLS(`chat_messages_select_participant`·`chat_room_reads_select_own`)로 자기 읽음행만 보이므로
  정의자 권한으로 승격할 이유가 없다(A2 최소 권한). `authenticated`에만 EXECUTE가 있다
  (anon 회수 — 비로그인은 배지가 없다).
  - ⚠️ **"내가 당사자인 방" 조건은 RLS에 맡기지 않고 함수 안에 `chat_rooms` 조인으로 명시한다**
    (`0025_chat_unread_participant_scope.sql`). 0024는 "INVOKER라 RLS가 이미 방 경계를 긋는다"고
    보고 이 조인을 생략했는데, **관리자에게는 그 전제가 깨진다** — `0005_admin_policies.sql`의
    `chat_messages_select_admin (using is_admin())`이 참여자 정책과 **OR로** 합쳐지므로 관리자에겐
    전체 메시지가 보인다. 그 결과 관리자가 소비자 화면을 열면 배지가 "플랫폼 전체 메시지 수"가
    됐다(로컬 실측: 참여 방 0개인 관리자에게 10 = 전체 메시지 수). Flutter(Epic 16.4)도 이 RPC를
    그대로 호출하면 되므로 앱 쪽에서 따로 방 필터를 걸 필요는 없다.
- **갱신 시점**: 방 진입(`web/src/app/(user)/chat/[roomId]/page.tsx`, 당사자 확인이 끝난 지점)
  **1회**만 `chat_room_reads.last_read_at`을 지금 시각으로 upsert한다 —
  - ⚠️ **여기서 말하는 "당사자 확인"은 방 조회가 0건이 아니라는 것이 아니라 `buyer_id`/`seller_id`
    직접 대조다.** 위 RPC와 **같은 축**의 함정이다 — `0005_admin_policies.sql`의
    `chat_rooms_select_admin (using is_admin())`도 참여자 정책과 OR로 합쳐지므로 관리자에게는
    남의 방도 조회된다. 대조 없이 호출하면 `chat_room_reads`의 참여자 RLS가 42501로 거부하고,
    `markChatRoomRead`가 그 실패를 콘솔로만 삼켜 관리자 열람마다 조용히 에러만 쌓인다
    (후속 코드리뷰 patch — 호출 위치·`await`·인자 순서는
    `web/src/app/(user)/chat/__tests__/unreadWiringContract.test.ts`가 고정한다).
  `web/src/lib/chat.ts`의 `markChatRoomRead(supabase, roomId, userId)`가 유일한 갱신 통로다.
  방이 열려 있는 동안 실시간으로 도착하는 메시지마다 다시 갱신하지 않는다(§12.5의 실시간 구독
  콜백·큐 상태기계에는 손대지 않는다 — 과설계 방지, A3). 그래서 방을 오래 열어둔 채 여러 건을
  라이브로 본 뒤 재진입 없이 나가면 그 메시지들은 다음 진입 전까지 안읽음으로 남는다(알려진 범위
  밖 edge case, `docs/tech-debt.md` #210).
- **배지 표기**: 내비 채팅🔔(`web/src/components/layout/SiteNav.tsx`)에 점(색 배지) 안에 숫자를
  넣어 "점+숫자"를 한 요소로 표기하고, `aria-label`에도 건수를 반영한다(예: "채팅, 안읽음 메시지
  3건" — 비색 신호 중복, UX-DR22). 0이면 배지를 렌더하지 않는다. **보이는 배지는 99 초과를
  "99+"로 누르지만 `aria-label`은 정확한 건수를 유지한다** — 상한을 둔 이유가 작은 원형 배지의
  레이아웃 사정이라 화면 낭독에는 해당되지 않는다(후속 코드리뷰 patch).
  - ✎ **정정(Epic 16.4 코드리뷰)**: 이 문단은 예전에 "방 목록 각 행에는 방별 개별 안읽음
    표시를 두지 않는다(FR57 AC가 요구하는 건 내비 총합과 정렬뿐 — Never, 과설계 금지)"라고
    적어 뒀었다. 그 Never는 **DW-548(대장, 2026-07-29)로 사용자 결정에 의해 뒤집혔다** — 총합
    배지만으로는 목록에 들어가도 어느 방이 새 메시지인지 알 수 없어 배지가 절반만 일한다는
    지적 때문이다(근거는 `0026_chat_unread_by_room.sql` 헤더 주석 참조). 방별 배지는 실제로
    구현돼 있다: web `web/src/app/(user)/chat/page.tsx` 141-172행(`chat_unread_by_room()` RPC
    소비), app `app/lib/features/chat/chat_list_screen.dart`의 `_RoomTile`(Epic 16.4가 같은
    RPC를 `chatUnreadByRoomProvider`로 미러링). 위 문단의 "총합·정렬만" 문구는 이 문서 드리프트였다 —
    지금 정본은: 내비 총합 + 방 목록 정렬 + **방별 개별 배지** 세 가지 전부다.
  배지 색은 **`bg-red-600`(#DC2626)** 이다 — 10px 소형 텍스트라 흰 글자 대비가 WCAG AA(4.5:1)를
  넘어야 하고, `bg-red-500`(#EF4444)은 3.76:1로 미달이다(후속 코드리뷰 patch, 실측: #DC2626은
  흰 배경 대비 4.83:1). 라이트·다크 양쪽에서 같은 값을 쓴다. app은 라이트 고정이라 동일한
  용도의 토큰(`AppColors.danger`, `#C0392B`)을 재사용한다 — 새 색을 하드코딩하지 않는다는
  기존 관례(`app_theme.dart` 규칙)를 따른 것이다. 정확히 같은 hex는 아니지만
  `#C0392B`의 흰 글자 대비는 **5.44:1**(WCAG AA 4.5:1 충족, 오히려 web의 4.83:1보다 높다,
  실측, 코드리뷰 patch) — 웹 다크모드가 없는 앱에는 대비 재계산이 필요 없는 범위의 차이다.
  **RPC가 실패하면 배지를 렌더하지 않는다**(0과 구분 표시하지 않음) — 배지는 부가 정보라
  헤더·페이지 렌더 자체를 막지 않는다(콘솔 로그만). Flutter(16.4)는 이 실패-폴백을 `chat_repository.dart`의
  `fetchUnreadTotal()`/`fetchUnreadByRoom()`이 각각 `0`/`{}`로 흡수하는 형태로 구현한다(호출부는
  실패와 "0건"을 구분하지 않는다 — web과 동일 방침).
  카운트 계산은 `web/src/components/layout/AppHeader.tsx`가 **consumer 분기·로그인 상태일 때만**
  `chat_unread_count()`를 호출해 맡는다(admin 분기·비로그인은 호출하지 않음) — 이 때문에
  `AppHeader`가 비동기 컴포넌트로 바뀌었다(대장 #209, `#183` getUser 증폭 층에 RPC 호출이
  하나 더 얹힘). app에는 admin 화면 자체가 없으므로(Epic 16.4 범위 밖) 이 분기가 필요 없다 —
  `chatUnreadTotalProvider`는 로그인 후 도달하는 하단 4탭 셸에서만 그려진다.

---

## 13. 모달·팝업 ARIA 규약 (Story 8.2 코드리뷰, 사용자 확정)

`FocusTrap`(`web/src/components/ui/FocusTrap.tsx`)은 **포커스 동작만** 책임진다 — 포커스 이동,
Tab 순환, Esc 닫힘, 트리거 복귀. **시맨틱은 강제하지 않는다.** 그래서 소비처가 붙여야 한다.

- **모달·바텀시트·로그인 게이트** — FocusTrap 컨테이너에 `role="dialog"` + `aria-modal="true"`
  + `aria-labelledby`를 **반드시 부착한다**(UX-DR22 접근성 바닥).
- **드롭다운·리스트박스** — `menu` / `listbox` role을 사용한다.

FocusTrap은 8.2 코드리뷰에서 `...rest`를 컨테이너 `div`로 전달하도록 patch돼 부착이 가능하다
(그 전엔 통로 자체가 없었다).

> **왜 규약으로 두나:** 프리미티브가 시맨틱을 강제하면 드롭다운·팝오버까지 `dialog`가 되어
> 낭독이 틀린다. 반대로 규약이 없으면 소비처가 매번 잊는다 — 그래서 프리미티브가 아니라
> **여기**에 박는다.
>
> **현재 미준수 1건**: `SiteNav`의 드롭다운·햄버거 패널이 `menu`/`listbox` role 없이
> `aria-label`만 쓴다(장부 `DW-454`, 구 `#154`). `SellForm`의 이탈 확인 모달은 규약대로
> 3종을 다 붙였다(`role="dialog"` + `aria-modal` + `aria-labelledby`) — 2026-07-29 실측.

## 14. Role 어휘 (Story 16.1, DW-681)

역할(role) 값의 정본은 지금까지 `0029_unify_existing_account_roles.sql`의 컬럼 주석에만
있었고 이 문서엔 없었다(DW-681 — "role 어휘의 정본이 DB 컬럼 주석에만 있고
`docs/conventions.md`엔 없다"). 값이 흩어진 사본(`web/src/lib/constants.ts`의 `USER_ROLE`·
`app/lib/features/auth/user_role.dart`의 `UserRole` enum)은 **이 절**을 따른다 — 값을 바꾸면
여기부터 먼저 고친다(§0 문서 규칙과 동일한 단일 출처 원칙).

- **정본 문구** (`0029`의 `profiles.role` 컬럼 주석, 글자 그대로):
  > 계정 종류. admin만 특별 취급(`is_admin()`) — 그 외는 전부 `'user'`이며 구매/판매 구분이
  > 없다(역할 통합, 0027·0028·0029). 매물 접근 권한은 이 값이 아니라 소유권(`seller_id`)+RLS로
  > 판정한다.
- **DB에 실제로 저장되는 값**: `profiles.role`은 `admin` 또는 `user` 두 값뿐이다(0029가
  기존 `buyer`/`seller` 계정을 전부 `user`로 통일했고, 0028이 신규 가입 기본값을 `user`로
  바꿨다). `buyer`/`seller`는 더 이상 DB에 새로 쓰이지 않는다.
  - ⚠️ **CHECK 제약은 이 두 값으로 좁혀져 있지 않다** — 0027이 CHECK를 완화해 DB가 강제하는
    값 집합이 아니다. 위 "실제로 저장되는 값"은 **트리거·마이그레이션이 실제로 채우는 값**을
    말하는 것이지, 컬럼이 허용하는 값의 전부가 아니다.
- **앱(Flutter) 쪽 계약이 다른 이유**: `app/lib/features/auth/user_role.dart`의 `UserRole`
  enum은 `buyer`/`seller`/`admin` 세 값만 안다 — `'user'`나 그 밖의 미상 문자열은
  `UserRole.fromValue()`가 **의도적으로 `null`로 삼킨다**(모르는 값을 억지로 매핑하지 않는다).
  그래서 `currentRoleProvider`(`auth_controller.dart`)는 role 메타데이터가 없을 때뿐 아니라
  `'user'`일 때도 `null`을 반환한다 — 둘 다 "특별 취급할 역할 없음"으로 같게 다뤄지고,
  판정에 쓰는 것은 이 값 자체가 아니라 **`null`이 아닌가/`admin`인가** 두 가지뿐이다
  (`app_router.dart`의 `redirect`·구 `main.dart`의 `AuthGate`가 그렇게 쓴다). 이 계약은
  `app/test/current_role_provider_test.dart`(DW-686)가 고정한다.
- **권한 판정은 role이 아니라 소유권+RLS다** — 위 정본 문구 그대로다. `role`은 "관리자인가
  아닌가"만 가르는 값이고, 매물 접근·채팅 참여 같은 나머지 권한은 각 테이블의 RLS(§6·§8)와
  `seller_id`/`buyer_id` 같은 소유권 컬럼이 판정한다. 새 화면·API를 짤 때 `role=='user'`
  같은 비교로 "일반 사용자만 가능"을 표현하지 않는다 — 그 구분 자체가 이미 없다.
