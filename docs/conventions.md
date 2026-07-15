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

- **AI 검색 응답:** `{ "answer": string, "listings": ListingCard[] }`
  - 0건이면 `listings: []` + `answer`에 조건 완화 안내(FR17).
  - AI 검색 응답 카드(`SearchResponse.listings[]`)는 아래 **ListingCard와 동일한 계약을 공유**한다(별도 카드 타입 없음).
- **ListingCard 필드(snake_case):**
  - 기존(필수): `id, manufacturer, model, year, price, mileage, region`
  - 기존(nullable): `seller_name`(판매자 표시 이름, 0007 비정규화 — web/app은 Supabase에서 직접 읽어 노출, api 응답엔 포함되지 않음)
  - 증분 신규(전부 nullable — 컬럼 자체가 아직 DB에 없어 항상 `null`, 값 채움은 후속 에픽):
    | 필드 | 타입 | 값 채움 |
    |---|---|---|
    | `image_url` | string\|null (대표 서명 URL) | Epic 9 |
    | `image_count` | int\|null | Epic 9 |
    | `view_count` | int\|null | Epic 11 |
    | `accident_status` | `'무사고'\|'단순교환'\|'사고'`\|null | Epic 10 |
    | `is_single_owner` | bool\|null | Epic 10 |
    | `is_non_smoker` | bool\|null | Epic 10 |
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

필드 자리(nullable 계약)뿐 아니라 **실제 값까지 채울 때**는 위 4곳에 더해 `api/app/graph/listing_cards.py`의 `SELECT_COLUMNS`·`api/app/db/sql_guard.py`의 `ALLOWED_COLUMNS`도 락스텝으로 갱신해야 한다(DB 컬럼이 실제로 생긴 시점).

또한 값을 채우는 에픽은 위 **"계약-외 값 정규화(소비처 공통)"** 규칙을 렌더 코드에 반영한다(빈 문자열 image_url·도메인 밖 accident_status·음수 count·bool 3상태). web `isValidListing`은 신규 필드를 검증하지 않으므로 소비처가 방어적으로 읽어야 한다.

## 5. 환경변수 배치 (요약)

상세는 루트 `.env.example` 참조. 핵심 규칙:

- `web/.env.local` — 브라우저 전달값만, `NEXT_PUBLIC_` 접두사 필수 (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- `api/.env` — 서버 전용. **`GEMINI_API_KEY`는 오직 여기에만** 둔다(웹에 절대 넣지 않음). `GEMINI_EMBEDDING_DIM=768`도 여기.
- `app/.env` — Flutter(Epic 7, 나중).
- `service_role` 키는 사용하지 않는다. anon key는 RLS가 보호.

## 6. 판매완료 비노출 (FR11)

- `status='sold'` 매물은 구매자의 **모든 경로**(목록·필터·상세·AI SQL·문서 RAG)에서 노출되지 않는다.
- 강제 지점: RLS(authenticated = `0002_listings`에 동거, anon = `0011_listings_anon_select`) + `api/db/sql_guard.py` + 문서 RAG 결과 필터. (구현은 Epic 2~4, anon 경로는 Epic 8.5)
- **새 조회 경로를 열면 이 목록에 강제 지점을 추가**한다(규칙7). anon 열람은 §8이 상술한다.

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
- **행동 게이트는 사용자 입력을 삼키지 않는다:** 비로그인이 입력을 마친 뒤 게이트를 만나면, 그 입력을 보존했다가 로그인 복귀 시 복원한다(`redirectedFrom`은 **경로만** 나르고 폼 상태는 못 나른다 — 보존은 sessionStorage 등으로 명시 구현). **복원까지만 하고 자동 실행하지 않는다** — 과금 호출의 트리거를 페이지 로드에 매달면 새로고침·뒤로가기가 재과금이 된다. 마지막 실행은 항상 사용자의 클릭이다. (Story 11.3 히어로가 이 패턴의 첫 적용처.)
- **신규 진입점 추가 시:** 위 분류 기준으로 먼저 가른다. 열람이면 `proxy.ts`에 넣지 않고 컴포넌트 레벨 행동 게이트만 추가, 행동·개인·관리 영역이면 `proxy.ts`의 `PROTECTED_PREFIXES`에 추가한다.

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

### 9.2 파일명 규약

- **정본**: `NNNN_이름.sql` (4자리 번호, **0001부터**, 유일, 밀집 — 공백 없이). fresh DB(신규 환경)의 **단일 출처**다.
  - **밀집이 §9.1의 "번호 갭은 무죄"와 모순 아닌 이유**: 둘은 서로 다른 축이다. §9.1의 갭 무죄는 **의존성 축**("0003 자리가 비어도 0004가 깨지지 않는다" — 참이다). 여기의 밀집은 **번호 관리 축**이다. 번호가 0001~max로 빈틈없고 바닥번호가 유일하면, 새 마이그의 번호는 `max+1`이거나 중복(→ 검출)뿐이라 **뒤로 끼워넣을 자리가 구조적으로 없다**. 즉 밀집은 갭 자체가 해로워서가 아니라 **out-of-order 삽입을 git 이력 추적 없이 막는 가장 싼 방법**이라서 있다.
- **접미사 파일**: `NNNN[b-z]_이름.sql` (같은 바닥번호 + 알파벳 접미사). **용도가 두 가지이고, 둘을 혼동하면 안 된다:**
  - **(가) 접미사를 쓴 정본** — 앞 번호가 이미 예약·사용 중일 때 그 사이에 들어가는 **신규 정본**. **fresh DB에 반드시 필요하고 레포에 남는다. 절대 삭제 대상이 아니다.** 현재 레포의 유일한 접미사 파일 `0003c_chat_room_integrity.sql`이 여기 해당한다(코드리뷰 [Decision] 옵션 A로 신설된 chat_rooms 무결성 트리거 — 지우면 `seller_id` 위조 차단이 사라진다).
  - **(나) 따라잡기 패치** — 정본을 **in-place 수정**했을 때 *이미 살아있는* 원격 DB만 그 수정을 따라오게 하는 **멱등 패치**. 신규 환경은 정본이 이미 최신이라 불필요하므로 파일로 남기지 않는다. **현재 레포에 이 종류의 파일은 0개다**(원격 이력에만 존재).
  - ⚠️ **판별법**: 파일 헤더가 "정본 파일도 동일하게 갱신됨 / 기존 원격은 이 패치로 따라잡는다"라고 밝히면 (나), 그 외에는 (가)다. **접미사가 붙었다는 이유만으로 삭제하지 마라** — 게이트는 파일이 **없어진 것**을 잡지 못한다(`docs/deployment-runbook.md` §8).

이 규약은 여기 적기 전까지 어디에도 문서화돼 있지 않았고, 그래서 (가)와 (나)가 구분되지 않았다. (나)의 실제 사례는 **원격 적용 이력에만** 있다(`0002b_listings_created_at_immutable`·`0003b_chat_review_hardening`·`0003c_revoke_trigger_execute` — 셋 다 **레포에 커밋된 적 없다**. 그 존재는 `0003c_chat_room_integrity.sql` 헤더 주석의 적용 순서 서술로만 남아 있다).

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
