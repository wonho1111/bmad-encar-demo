---
baseline_commit: 72bb9da85727e549a82987ee54c380db649d9377
---

# Story 9.2: 서명 URL 헬퍼 (아티팩트 범용)

Status: done

> ⚠️ **이 스토리의 이미지 스토리지 설계(비공개 버킷 + 서명 URL)는 Story 9.0(마이그 `0014`)으로 대체됐다** — 버킷은 공개, URL은 고정이다. 아래 본문은 **당시 결정의 기록**이며 지금 따라야 할 계약이 아니다. 현재 계약: `docs/conventions.md` §6.1·§10.

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a web·app 개발자,
I want 비공개 사진을 안전하게 보여줄 서명 URL 발급을 한 곳에서 관리하길,
so that 만료·배치 발급이 일관되고 향후 다른 아티팩트도 배관 재작업 없이 재사용한다.

> **이 스토리의 성격 (개발자 필독):** 9.1이 만든 **비공개 버킷 `listing-images` + `storage.objects` 읽기 RLS** 위에서, 그 사진을 화면에 보여줄 **서명 URL을 실제로 발급하는 배관**을 세운다. **이 레포엔 storage를 쓰는 코드가 web·app 통틀어 아직 0줄이다**(9.1 Dev Notes 확인) — 참고할 사내 선례가 없는 유일한 표면이다. 이 스토리는 **헬퍼(배관)만** 만든다: 실제로 사진을 카드/상세/AI 응답에 그리는 소비처는 9.3(업로더)·9.4(카드)·9.5(상세)·9.6(AI 카드)이고, 시드 사진은 9.7이 채운다.
>
> **A2/A3 범위 경계:** 헬퍼는 **범용**이다 — `getSignedUrl(bucket, path)`로 버킷·경로를 인자로 받고, 이미지 전용 로직·특정 버킷명을 헬퍼 안에 하드코딩하지 않는다. `SIGNED_URL_TTL = 3600`은 **단일 상수**(호출부 하드코딩 금지). 마이그레이션·화면 렌더링(JSX/Widget)·api 쿼리(`listing_cards.py`)는 **이 스토리 범위 밖**이다(아래 "건드리지 않을 것" 참고).
>
> **⚠️ 검증은 원격 Supabase에서 한다 (B4 존재≠작동):** 마이그레이션 게이트(도커 CI)는 프렐류드에 `grant usage on schema storage`가 없어 **storage RLS가 실제로 거르는지 증명하지 못한다**(9.1 실측). "정책이 있다"와 "실제로 서명이 발급/차단된다"는 다르다 — **실제 이미지 객체를 버킷에 넣고, on_sale일 때 서명이 되고 sold일 때 안 되는 것을 원격에서 실측**해야 이 스토리가 닫힌다.

## Acceptance Criteria

1. **(서명 주체 규칙 + 단일 TTL 상수 — AC1)** 서명은 **각 소비 클라이언트/서버가** 하고, **금지 대상은 api(FastAPI)뿐이다**. web = 서버 컴포넌트/route handler(**서버측 발급**), app(Flutter) = `supabase_flutter` Storage(**클라측 발급**, 앱엔 서버가 없음). 범용 헬퍼 `getSignedUrl(bucket, path)`는 `SIGNED_URL_TTL = 3600s` **단일 상수**를 쓴다(호출부 하드코딩 금지 — 아키텍처 anti-pattern "서명 만료 하드코딩"·"api가 서명 URL 반환" 둘 다 금기).
2. **(배치 발급 — AC2)** 목록은 `createSignedUrls` **배치 1회**로 발급한다(NFR7 저비용 — 카드 20장을 20번 왕복하지 않는다).
3. **(api는 서명 안 함 — AC3)** api는 서명 URL을 발급하지 않는다 — "**api 응답에 서명 URL 문자열이 존재하지 않는다**"를 contract test로 단언한다(불변식 가드). *api가 `storage_path`를 실제로 반환하는 것은 9.6의 몫이므로, 9.2의 contract test는 "서명 URL 부재"만 단언하고 "storage_path 존재" 단언은 9.6에서 활성화한다(아래 Dev Notes "api contract test 시퀀싱" 참고).*
4. **(sold 비노출 소스 강제 + TTL 잔존창 기록 — AC4·CM-B)** sold/삭제 매물은 서명 URL이 **발급되지 않아**(9.1 `storage.objects` 읽기 RLS가 `on_sale OR 본인 소유`만 SELECT 허용) FR11 비노출이 **소스에서** 강제됨을 원격 실측으로 확인한다. **단, 서명 URL은 발급 시점에만 RLS를 검사하고 TTL(최대 1시간) 동안 재검사하지 않는다** — `on_sale→sold` 전환 직전 발급된 URL은 최대 1시간 생존한다. 이 한계를 `docs/tech-debt.md` #50-2에 **TTL이 실제 구현된 지금 시점 기준으로** 정합화 기록한다(§6 FR11 강제지점 목록과 교차참조).

## Tasks / Subtasks

- [x] **Task 1 — web 서명 URL 헬퍼 신설 (`web/src/lib/storage/index.ts`) (AC: 1, 2)**
  - [x] 새 디렉터리 `web/src/lib/storage/`를 만들고 `index.ts`를 추가한다(아키텍처 line 295·231 확정 위치). import 별칭은 `@/lib/storage`.
  - [x] `SIGNED_URL_TTL = 3600` 상수를 **여기서** export한다(초 단위, 1시간). 정본은 `docs/conventions.md §10`, 이 상수는 그 값을 코드로 옮긴 것이며 **주석으로 정본을 가리킨다**. 다른 파일·호출부에서 `3600`을 다시 쓰지 않는다.
  - [x] `getSignedUrl(bucket, path): Promise<string | null>` — 서버 클라이언트(`@/lib/supabase/server`의 `createClient()`, **async**)를 내부에서 만들어 `supabase.storage.from(bucket).createSignedUrl(path, SIGNED_URL_TTL)` 호출. **에러/미존재/RLS 미통과 시 throw하지 않고 `null` 반환**(소비처가 §4 계약대로 "사진 준비중" 플레이스홀더를 그리게 함 — sold 매물은 여기서 자연히 null이 된다).
  - [x] `getSignedUrls(bucket, paths[]): Promise<(string | null)[]>` — `paths`가 비면 `[]` 반환, 아니면 `createSignedUrls(paths, SIGNED_URL_TTL)` **1회** 호출(AC2). 반환 배열은 **입력 순서를 보존**하고, 항목별 `{ path, signedUrl, error }`에서 실패분은 `null`로 매핑한다.
  - [x] 헬퍼는 **서버측 발급 전용**이다(아키텍처: web은 서버 컴포넌트/route에서 서명). 파일 상단 주석에 "server components·route handlers·server actions에서만 호출"을 명시한다. 클라이언트 번들에서 import하지 않는다(새 의존성 `server-only` 패키지 추가는 하지 않음 — A2, 주석 계약으로 충분).
  - [x] 버킷명·이미지 전용 로직을 헬퍼에 하드코딩하지 않는다(범용 아티팩트). 호출부가 `getSignedUrl('listing-images', storagePath)`로 버킷을 넘긴다.

- [x] **Task 2 — app(Flutter) 서명 URL 헬퍼 미러 (`app/lib/core/supabase/storage_helper.dart`) (AC: 1, 2)**
  - [x] `app/lib/core/supabase/storage_helper.dart`를 추가한다(아키텍처 line 322 `core/supabase/ …… Storage 서명 URL` 확정 위치, `supabase_client.dart`·`env.dart`의 형제).
  - [x] `const int kSignedUrlTtl = 3600;` — web `SIGNED_URL_TTL`의 **미러 상수**(프로젝트 "단일 출처 정본 + 언어별 미러" 관례 = `EMBEDDING_DIM`·채팅 길이와 동일). 주석으로 정본(`docs/conventions.md §10`)과 web 상수를 가리킨다.
  - [x] `Future<String?> getSignedUrl(String bucket, String path, {SupabaseClient? client})` — `client ?? supabase`(전역 싱글턴, 기존 리포지토리 DI 패턴 `client ?? supabase` 계승)로 `c.storage.from(bucket).createSignedUrl(path, kSignedUrlTtl)` 호출, **예외는 잡아 `null` 반환**(RLS 미통과·미존재 → 소비처 플레이스홀더).
  - [x] `Future<List<String?>> getSignedUrls(String bucket, List<String> paths, {SupabaseClient? client})` — 배치(`createSignedUrls`) 1회, 입력 순서 보존, 실패분 null. 빈 리스트면 `[]`.
  - [x] ⚠️ **설치된 `supabase_flutter ^2.15.0`의 정확한 반환 타입을 실물로 확인**하고 맞춘다 — `createSignedUrl`은 `Future<String>`(에러 시 throw), `createSignedUrls`는 `Future<List<SignedUrl>>`(각 원소 `.signedURL`)일 가능성이 높으나 버전에 따라 다를 수 있다. 추측 금지, `flutter analyze`로 타입 확정.
  - [x] **Dart 헬퍼의 라이브 서명 검증은 Epic 16(이미지 카드 앱 재설계)에서** 실폰으로 이뤄진다 — 지금은 앱에 이미지를 그리는 화면이 없어 호출부가 없다. 9.2는 헬퍼 신설 + `flutter analyze` 0-issue + (선택) fake 클라 단위테스트까지가 범위임을 스토리 기록에 남긴다(A4 검증 표면을 실제 변경 범위에 맞춤).

- [x] **Task 3 — 계약 문서 정합화 (`docs/conventions.md`) (AC: 1)**
  - [x] `docs/conventions.md §10`(이미지 스토리지 계약)에 **헬퍼 배관 사실**을 짧게 추가한다 — 서명 헬퍼 위치(web `@/lib/storage`, app `core/supabase/storage_helper.dart`), 시그니처 `getSignedUrl(bucket, path)`/배치 `getSignedUrls`, **null 반환 = 플레이스홀더**(§4의 "image_url null/빈문자열 → 사진 준비중"과 정합), TTL 상수 참조. §10은 이미 TTL·"api는 서명 안 함"을 규정하므로 **값을 복제하지 않고 배관 위치만** 덧붙인다(B8 제약 문서는 짧게, 정본 하나).
  - [x] §10의 "서명 URL 발급 구현은 Story 9.2" 문구가 이제 **구현 완료**임을 반영한다(예: "구현: `@/lib/storage`·`core/supabase/storage_helper.dart`, 9.2").

- [x] **Task 4 — api "서명 안 함" 가드 (contract test) (AC: 3)**
  - [x] api AI 검색 응답에 **서명 URL 문자열이 존재하지 않음**을 단언하는 결정론적 contract test를 추가한다(`api/tests/` — 기존 `test_ai_search.py` 스타일, LLM은 fake로 교체). 서명 URL 형태(예: `/storage/v1/object/sign/` 경로 또는 `token=` 쿼리를 포함하는 URL 문자열)가 응답 JSON 어디에도 없음을 검사한다. 오늘 `image_url`은 항상 `None`이라 자명히 통과하지만, 이 가드는 **9.6이 api에 storage_path 반환을 붙인 뒤에도 서명 URL이 새어나오지 않도록** 계속 지킨다.
  - [x] `api/app/graph/listing_cards.py`·`api/app/schemas/ai.py`·`api/app/db/sql_guard.py`는 **건드리지 않는다** — api가 `storage_path`를 실제 반환하는 것은 9.6의 몫이다(아래 "건드리지 않을 것").

- [x] **Task 5 — tech-debt 정합화 (TTL 잔존창 #50-2·관리자 sold 사진 #45) (AC: 4)**
  - [x] `docs/tech-debt.md #50-2`(서명 URL TTL 잔존창)를 **TTL이 실제 구현된 지금 기준**으로 정합화한다 — "서명 URL은 발급 시점에만 RLS를 검사하고 TTL(3600s) 동안 재검사하지 않아, `on_sale→sold` 전환 직전 발급된 대표 URL이 최대 1시간 생존한다. `docs/conventions.md §6`의 'sold는 모든 경로에서 비노출' 주장은 이 축에선 성립하지 않는다(데모 수용 한계)." 해소 방안(예: TTL 단축·서명 URL 무효화)은 별도 액션으로만 남기고 이번에 구현하지 않는다(A2).
  - [x] `docs/conventions.md §6`(FR11 강제지점 목록)의 storage RLS 항목에 이 TTL 잔존창 한계를 **각주/한 줄로 교차참조**해, 다음 사람이 §6만 읽고 "완전 비노출"로 오해하지 않게 한다(B8 거짓 안전감 제거).
  - [x] **#45(관리자 sold 사진 서명 불가)** 는 이번 스토리에서 **해소하지 않는다** — 읽기 RLS에 `is_admin()` 분기가 없어 관리자도 sold 매물 사진 서명 URL을 못 얻는다(메타는 보이나 파일 안 보임). 9.2 헬퍼는 이 제약을 **그대로 물려받으며**, 관리자 화면(Epic 15)이 이 비대칭을 마주칠 것임을 스토리 기록에 남긴다(트리거는 열린 채 유지).

- [x] **Task 6 — 검증 (원격 Supabase 실객체 실측 — B4 존재≠작동) (AC: 1, 2, 3, 4)**
  - [x] **테스트 픽스처 준비(원격):** 시드 매물 중 `status='on_sale'`인 것 하나를 골라 그 소유자 경로 `{seller_id}/{listing_id}/`에 **작은 테스트 이미지 1장**을 업로드하고(9.3 업로더가 아직 없으므로 **인증 세션을 쓴 소규모 스크립트**로 올린다), `listing_images` 행을 삽입한다(`storage_path`는 업로드 key와 **글자 그대로 동일**해야 RLS 조인 성립). 매물당 10장 상한·경로 소유자 규칙(9.1 트리거)을 준수한다. *(변경: 실제 seed 판매자 계정은 비밀번호를 알 수 없어(seed.sql이 세션변수로만 주입) 재사용 대신 **새 throwaway 유저+throwaway 매물**을 만들어 픽스처로 썼다 — seed 데이터·임베딩은 전혀 건드리지 않았고, 검증 후 유저·매물·이미지·객체 전부 삭제해 흔적 0으로 정리했다. 근거는 아래 Completion Notes.)*
  - [x] **(a) on_sale 서명 성공:** 헬퍼로 그 `storage_path`를 서명 → 받은 URL을 HTTP GET → **200 + 이미지 바이트** 확인. **로그아웃(anon) 경로와 로그인 경로 둘 다** 확인한다(FR58: anon도 on_sale 사진 열람 가능해야 함).
  - [x] **(b) sold 차단(FR11 소스 강제):** 그 매물을 `status='sold'`로 바꾸고 → **새로** 서명 시도 → 헬퍼가 **`null` 반환**(RLS 미통과로 발급 실패)함을 확인한다. "정책이 있다"가 아니라 "실제로 발급이 막힌다"를 실측한다.
  - [x] **(c) 정리:** 매물을 `on_sale`로 되돌리고, 삽입한 `listing_images` 행과 업로드한 테스트 객체를 삭제한다(시드 데이터·임베딩 보존, CM-A).
  - [x] **web E2E:** 배치(`getSignedUrls`)가 1회 호출로 다건을 발급하는지 관찰(NFR7). *(주의: 카드에 사진을 렌더하는 화면은 9.4/9.5이므로, 9.2 web 검증은 헬퍼 함수를 서버측에서 직접 호출해 결과를 관찰하는 수준 — 임시 route handler 또는 스크립트 — 으로 하고 임시 코드는 정리한다.)*
  - [x] **api:** Task 4 contract test 실행 → green 확인. 관련 기존 스위트(`test_ai_search.py` 등) 회귀 0.
  - [x] **app:** `flutter analyze` 0-issue(헬퍼 신설이 기존 코드를 안 깸). 라이브 서명은 Epic 16.
  - [x] 임시로 띄운 dev 서버·임시 route·테스트 픽스처를 모두 정리한다.

## Dev Notes

### 9.1이 세운 토대 (헬퍼가 의존하는 사실 — 재확인 금지, 그대로 사용)
- **버킷명(정확한 리터럴):** `'listing-images'` (private, `public=false`). `0012_listing_images.sql`.
- **경로 규칙:** `{user_id}/{listing_id}/{filename}` — **첫 세그먼트 = 소유자**. `storage_path` 컬럼 값 = 버킷 내 key **전체**(버킷명 미포함), `storage.objects.name`과 **바이트 단위로 동일**해야 RLS 조인이 성립.
- **`storage.objects` 읽기 RLS(`listing_images_objects_read`, anon·authenticated SELECT):** 해당 이미지의 매물이 `l.status='on_sale' OR l.seller_id=auth.uid()`일 때만 통과. **이 정책이 서명 URL 발급의 전제다** — 서명은 발급자의 `storage.objects` SELECT 권한을 요구하므로, sold이면서 남의 매물이면 서명이 실패한다(= AC4 소스 강제). anon도 대상(FR58).
- **`SIGNED_URL_TTL = 3600s`** — 사용자 확정(2026-07-13), `docs/conventions.md §10` 정본.
- **api 계약(CR2):** api는 `ai_readonly using(true)`로 sold 포함 `storage_path`를 읽을 수 있으나(FR11은 api 레벨에서 강제), **서명은 절대 안 한다**. 서명 금지 대상은 **api 하나뿐**.

### 아키텍처 "236 vs 332" 정합 (헬퍼 서명 주체 확정)
아키텍처 초안의 line 236 "서버만 서명"이 line 332 "web/app이 서명"과 모순됐고, **2026-07-13 "서버만"이 아니라 "api(FastAPI)만 금지"로 정정**됐다(Flutter는 서버가 없어 클라측 서명이 유일 경로 — PRD FR39·NFR7·ADR-IMG-01). 따라서:
- web = 서버 컴포넌트/route handler에서 **서버측** 발급 (`@supabase/ssr` 서버 클라)
- app = `supabase_flutter` Storage로 **클라측** 발급 (앱엔 서버 없음)
- api = **절대 서명 안 함**, `storage_path`만 반환 (anti-pattern: "api가 서명 URL 반환")

### api contract test 시퀀싱 (왜 9.2는 "서명 URL 부재"만 단언하나)
epic AC 원문은 "서명 URL 부재 **+ storage_path 존재**"를 함께 요구하지만, **api가 `storage_path`를 실제로 반환하기 시작하는 것은 9.6**(AI 응답 카드 사진)이다. 오늘 api `ListingCard.image_url`은 항상 `None`이다(8.3이 자리만 nullable로 선점). 그러므로:
- **9.2**: "api 응답에 서명 URL 문자열이 없다"는 **불변식**만 단언(지금도, 9.6 이후에도 참).
- **9.6**: api에 storage_path 반환을 붙이면서 "storage_path 존재" 단언을 그 contract test에 **추가**(9.6 AC의 "on_sale id로 대표 1장 storage_path만 별도 고정쿼리"와 락스텝).
- 이렇게 나누는 이유: 9.2에서 "storage_path 존재"를 단언하면 **지금 통과할 수 없는 거짓 목표**가 되어 A4(검증 가능한 목표)를 어긴다.

### 헬퍼 반환 계약: 실패 = `null`, throw 아님
`createSignedUrl`은 RLS 미통과·객체 미존재 시 (supabase-js v2는) 에러 객체를 반환한다. 헬퍼는 이를 **`null`로 흡수**한다 — 이유: (1) 소비처(카드/상세)는 `image_url`이 null이면 "사진 준비중"을 그리도록 §4 계약이 이미 정해져 있어, 서명 실패가 자연스럽게 플레이스홀더로 이어진다. (2) sold 매물의 서명 실패를 예외로 터뜨리면 페이지 전체가 죽는다 — null 흡수가 방어적이고 계약 정합적이다. 배치도 항목별 실패를 null로 매핑(부분 실패가 전체를 막지 않음).

### 검증이 원격이어야 하는 이유 (B4 존재≠작동)
마이그레이션 게이트(도커 CI)는 프렐류드에 `grant usage on schema storage`가 없어, 게이트에서 `storage.objects`를 anon/authenticated로 조회하면 `permission denied for schema storage`가 난다 — 즉 **CI 초록은 storage RLS가 "실제로 거르는지"를 증명하지 않는다**(9.1 실측). 서명 발급/차단은 **반드시 원격 Supabase(실제 버킷·실제 객체)에서** 확인한다. `mcp__supabase__execute_sql`로 매물 status를 토글하고 `listing_images` 행을 넣고 뺄 수 있으나, **객체 업로드/서명 자체는 storage API**라 인증 세션을 쓴 소규모 스크립트(supabase-js/flutter 클라)로 실측한다.

### 건드리지 않을 것 (범위 밖 — 명시적 non-goal)
- **마이그레이션 없음.** DB(테이블·버킷·RLS)는 9.1(0012·0013)이 이미 세웠다. 9.2는 순수 앱-레이어 배관이다.
- **화면 렌더링(JSX/Widget) 없음.** 카드에 사진 그리기 = 9.4(레이아웃 B)·9.5(상세 갤러리), AI 카드 = 9.6, 앱 = Epic 16. `ListingCard.tsx`·`listing_card.dart`·`listing.dart`의 렌더/파싱 로직 불변.
- **api 쿼리·스키마 불변.** `listing_cards.py`(SELECT_COLUMNS·rows_to_cards)·`schemas/ai.py`(ListingCard)·`sql_guard.py`(ALLOWED_COLUMNS)는 9.2에서 **안 건드린다** — api의 storage_path 반환은 9.6이 락스텝으로 붙인다. 9.2는 api에 **contract test만** 추가한다(코드 변경 아님).
- **업로더 없음.** 사진을 올리는 UI/로직은 9.3. Task 6의 업로드는 **검증용 임시 픽스처**이지 제품 기능이 아니며 검증 후 정리한다.
- **관리자 sold 사진 서명(#45) 해소 안 함.** 읽기 RLS에 `is_admin()` 분기 추가는 별도 액션(Epic 15가 마주침). 9.2는 제약을 물려받기만 한다.
- **TTL 잔존창(#50-2) "해소" 안 함.** 기록 정합화만. TTL 단축·URL 무효화 같은 실구현은 데모 범위 밖(A2).

### 테스트 표준 (project-context 규칙12)
- **web:** E2E(Playwright) 우선. 다만 서명 헬퍼는 서버측 순수 유틸에 가까워, **핵심 검증은 원격 실객체 대상 서명 성공/차단 실측**(Task 6 a·b)이 전부다. 헬퍼의 순수 로직(TTL 전달·배치 순서·null 매핑)에 Vitest 단위테스트를 붙이려면 storage 클라를 mock해야 하는데, **정작 중요한 "RLS가 거르는가"는 mock으로 증명 불가** → 실객체 실측이 본질이다. 단위테스트는 선택.
- **api:** LLM fake 교체 결정론적 pytest — "서명 URL 문자열 부재" contract test가 정확히 이 층에 맞는다.
- **app:** 순수 헬퍼 신설이라 `flutter analyze`(정적 분석)로 충분. 라이브 서명은 화면이 생기는 Epic 16에서 실폰 검증.
- **공통(B4):** "만들었다"가 아니라 "on_sale은 되고 sold는 막힌다를 실측했다"가 완료다.

### 배포·브랜치 (B3, AC-DEPLOY-1)
`develop`에서 작업·커밋 → 동작 확인. 이 스토리는 **DB 마이그레이션이 없는 앱-레이어 코드/문서/테스트 변경**이라 배포 순서 리스크가 없다(만드는 쪽 DB는 9.1이 이미 반영). web(Vercel)·app은 코드만 늘고, api는 테스트만 는다. `main` 병합은 사용자 승인 시에만.

### Project Structure Notes
- web import 별칭 `@/*` → `web/src/*`, TypeScript strict. 서버 클라 `@/lib/supabase/server`의 `createClient()`는 **async**(Next 16 `cookies()` async). `@supabase/supabase-js ^2.108.2` — `createSignedUrls` 배치 API 사용 가능.
- app은 `core/supabase/`에 client·env가 이미 있고 헬퍼를 형제로 추가. 전역 `supabase` 싱글턴 + 생성자 DI(`client ?? supabase`) 패턴 계승. `supabase_flutter ^2.15.0`.
- **변이(variance) 없음** — 두 헬퍼는 같은 개념(범용 서명 + 단일 TTL 상수)을 각 런타임 관례로 미러링. 언어가 다르니 코드 공유는 아니고 **패턴·상수값을 미러**(EMBEDDING_DIM·채팅 길이와 동일한 프로젝트 관례).

### References
- [Source: _bmad-output/planning-artifacts/epics-increment-2026-07-12.md#Story 9.2 (474~487행)] — AC 원문
- [Source: _bmad-output/planning-artifacts/architecture-increment-2026-07-12.md#line 236·332] — "서버만"→"api만 금지" 정합(2026-07-13 정정), web=서버측·app=클라측 서명
- [Source: architecture-increment-2026-07-12.md#line 231·295] — `SIGNED_URL_TTL` 단일 상수·`createSignedUrls` 배치·헬퍼 위치 `web/src/lib/storage/`
- [Source: architecture-increment-2026-07-12.md#line 259] — anti-pattern: "api가 서명 URL 반환"·"서명 만료 하드코딩"
- [Source: architecture-increment-2026-07-12.md#line 308·322·360(CR2/CR3)] — api는 storage_path만(9.6)·app `core/supabase/` Storage 서명·image_url 단일 서명 URL 계약
- [Source: docs/conventions.md §10(184~206행)] — 이미지 스토리지 계약 정본: 버킷명·경로·상한·TTL 3600·"api는 서명 안 함"
- [Source: docs/conventions.md §4(48·57행)·§4.1] — `image_url` null/빈문자열 → "사진 준비중" 플레이스홀더(헬퍼 null 반환과 정합)
- [Source: docs/conventions.md §6] — FR11 강제지점 목록(storage RLS 항목 — TTL 잔존창 교차참조 대상)
- [Source: docs/conventions.md §5] — service_role 금지(헬퍼는 anon key + RLS만)
- [Source: supabase/migrations/0012_listing_images.sql] — 버킷 `listing-images`·읽기 RLS `listing_images_objects_read`(on_sale OR own)
- [Source: supabase/migrations/0013_listing_images_path_integrity.sql] — storage_path 위조 차단 트리거(경로 소유자 = seller_id에서 직접 조회)
- [Source: docs/tech-debt.md #50-2] — 서명 URL TTL 잔존창(9.1이 등재, 9.2가 정합화)
- [Source: docs/tech-debt.md #45] — 관리자 sold 사진 서명 불가(읽기 RLS에 is_admin 분기 부재, 9.2 물려받음)
- [Source: _bmad-output/implementation-artifacts/9-1-listing-images-스키마-비공개-버킷-storage-rls.md] — 기반 스토리(버킷·RLS·경로·"storage 코드 0줄"·CI가 storage RLS 증명 못 함)
- [Source: _bmad-output/implementation-artifacts/8-3-listingcard-공유-계약-셸-개정.md] — `image_url` 계약(대표 서명 URL) 자리 선점, 값 채움 = Epic 9
- [Source: web/src/lib/supabase/server.ts] — 서버 클라 `createClient()`(async, @supabase/ssr)
- [Source: web/src/lib/supabase/client.ts·env.ts] — 브라우저 클라·env 게터(참고, 헬퍼는 서버 클라 사용)
- [Source: app/lib/core/supabase/supabase_client.dart] — 전역 `supabase` 싱글턴(헬퍼 형제 위치)
- [Source: app/lib/features/listings/listing.dart] — `ListingCardData.imageUrl`(현재 raw 문자열 파싱, 서명 로직 없음 — 9.2 이후 소비처가 헬퍼 사용)
- [Source: _bmad-output/project-context.md#규칙6·12·13] — service_role 금지·층별 테스트·반응형(참고)

## Dev Agent Record

### Agent Model Used

Claude Sonnet 5 (claude-sonnet-5)

### Debug Log References

- web: `npx tsc --noEmit` 0 errors, `npx eslint src/lib/storage/index.ts` 0 issues.
- app: `flutter analyze`(전체 프로젝트) → "No issues found!".
- api: `python -m pytest tests/test_ai_search.py tests/test_storage_signed_url_contract.py -q` → 12 passed. red→green 수동 검증: `test_storage_signed_url_contract.py`를 image_url에 가짜 서명 URL 문자열을 심어 일부러 깨서 실패(AssertionError, marker 정확히 잡음) 확인 후 원복.
- 원격 Supabase(`psrnsasxpkpwqdukjdmt`) 실측: throwaway 유저 2명 + 매물 2건 + 이미지 3장을 만들어 (a) on_sale 서명 성공(anon·로그인 둘 다 HTTP GET 200 + 이미지 바이트), (b) sold 전환 후 anon 서명 시도 → `Object not found`(RLS가 행을 가려 헬퍼 관점에서 null), 소유자 본인은 sold에도 여전히 서명 성공(RLS "본인 소유" 절이 별도로 유효 — 의도된 동작) 확인. 배치(`getSignedUrls`) 1회 호출로 3개 경로(실재 2개+미존재 1개)를 순서 보존 + null 매핑까지 정확히 반환함을 임시 route handler로 관찰.

### Completion Notes List

- ✅ AC1~AC4 전부 원격 실측으로 확인. web `@/lib/storage`·app `core/supabase/storage_helper.dart` 두 헬퍼 모두 null-on-failure 계약을 지킨다.
- ⚠️ **Task 6 픽스처 변경(스토리 원문 대비):** 원문은 "시드 매물 중 on_sale인 것 하나를 골라" 재사용하라고 했으나, 실제 시드 판매자 계정(`seller-seed2@test.com` 등)의 비밀번호는 `seed.sql`이 세션 변수(`app.seed_password`)로만 주입하고 저장소엔 평문이 없어 **로그인 세션을 만들 수 없었다**. 대신 매번 throwaway 유저(Supabase Auth 회원가입)+throwaway 매물을 만들어 검증하고, 검증 후 유저·매물·`listing_images`·storage 오브젝트를 전부 삭제해 흔적을 0으로 되돌렸다(시드 데이터·임베딩은 전혀 건드리지 않음, CM-A 유지).
- ⚠️ **정리 중 새 발견 (tech-debt.md #51로 등재):** 인증된 사용자가 **본인 소유** storage 오브젝트를 Storage API로 DELETE/LIST하려 하면 RLS qual·GRANT가 모두 맞는데도 403/빈 결과가 난다(SELECT/서명·INSERT는 정상). `service_role` 키로는 즉시 성공해 RLS 정책 자체의 버그는 아니고 Storage API 서버 레이어의 원인 미상 동작으로 보인다. 9.2는 delete를 구현하지 않아 오늘은 무해하지만, **9.3(업로더)이 사진 삭제/교체 UI를 만들 때 정면으로 부딪힐 것**이라 tech-debt.md에 새 항목(#51)으로 기록했다.
- 정리 과정에서 사용자가 `api/.env`에 임시로 넣어준 `SUPERBASE_SERVICE_ROLE_KEY`(1회용, 인증 DELETE가 막힌 임시 데이터 정리용)를 사용 후 파일에서 제거했다 — 코드베이스·git 이력 어디에도 커밋되지 않았다(`.env`는 gitignore).
- api contract test(`test_storage_signed_url_contract.py`)는 오늘은 `image_url`이 항상 `None`이라 자명히 통과하지만, 9.6이 storage_path 반환을 붙인 뒤에도 서명 URL 누출을 계속 잡도록 설계했다(Dev Notes "api contract test 시퀀싱" 참고 — "storage_path 존재" 단언은 여기서 추가하지 않음).
- **#45(관리자 sold 사진 서명 불가) 물려받음(Task 5 기록):** 9.1의 `storage.objects` 읽기 RLS에 `is_admin()` 분기가 없어, 관리자도 sold 매물 사진의 서명 URL을 얻지 못한다(매물 메타는 보이나 파일은 안 열림). 9.2 헬퍼는 이 비대칭을 **그대로 물려받으며**(별도 해소 없음), 관리자 화면을 만드는 **Epic 15**가 이 제약을 정면으로 마주칠 것이다. 트리거는 tech-debt #45에 열린 채 유지한다.

### File List

- `web/src/lib/storage/index.ts` (신규)
- `app/lib/core/supabase/storage_helper.dart` (신규)
- `api/tests/test_storage_signed_url_contract.py` (신규)
- `docs/conventions.md` (수정 — §10 헬퍼 배관 사실 추가, §6 TTL 잔존창 교차참조 각주 추가)
- `docs/tech-debt.md` (수정 — #50-2 TTL 정합화, #51 신규 등재, 요약 대시보드 갱신)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (수정 — 9-2 상태 전이)

### Change Log

- 2026-07-18: dev-story 실행 — web/app 서명 URL 헬퍼 신설, conventions.md·tech-debt.md 정합화, api contract test 추가, 원격 Supabase 실측(on_sale 성공/sold 차단) 완료. tech-debt #51(인증 DELETE/LIST 403) 신규 발견·등재. Status: ready-for-dev → in-progress → review.

## Review Findings

_2026-07-18 코드리뷰 (bmad-code-review, 3-레이어 병렬 적대: Blind Hunter · Edge Case Hunter · Acceptance Auditor). dismiss 4건(Blind #2 SDK 필드명·#4 auth 타깃 마스킹 → Edge가 실측 반증 / Auditor A2·A4 → 스펙 준수·설계상 불가피)._

- [x] [Review][Decision→해결] 배치 서명 URL의 path 동일성 가정 — **실측으로 반증됨(2026-07-18).** 우려는 "서버가 응답 path를 정규화해 돌려주면 `byPath` 조회 miss로 서명 성공 URL이 null이 된다"였으나, 3개 소스 실측 결과 **Supabase는 요청 path를 byte-identical·입력 순서대로 반향**한다: (1) storage-api 서버 `signObjectUrls`가 `paths.map(path => ({error, path, signedURL}))`로 입력 문자열을 그대로 되돌리고 DB결과는 존재확인 Set에만 씀, (2) storage-js 2.108.2·(3) storage_client 2.5.7 둘 다 응답 path·순서를 손대지 않음. → 현재 `byPath` 매칭은 정확하며 정규화(원안 (b))는 **일어날 수 없는 시나리오용 죽은 코드**라 A2 위반. **결정: 로직 불변 + 확인된 전제를 web·Dart 두 헬퍼에 한 줄 주석으로 박음**(B9 — 재조사 방지). [web/src/lib/storage/index.ts:31 · app/lib/core/supabase/storage_helper.dart:39]
- [x] [Review][Patch] contract test에 영구 positive fixture 부재 — **적용:** 가드 함수를 직접 겨눈 `test_guard_fires_on_plain_signed_url`·`test_guard_fires_on_percent_encoded_signed_url` 2개 추가. 마커를 임시로 `ZZZ_TEMP_BROKEN`으로 깨서 두 테스트가 red 되는 것 실측 → 원복 후 14 passed 재확인(B4). [api/tests/test_storage_signed_url_contract.py]
- [x] [Review][Patch] 서명 URL 마커 세트 불완전 — **적용:** 마커를 `["/sign/", "token="]`로 일반화(object/render/upload 서명 경로 포괄)하고, `_assert_no_signed_url`이 `unquote`로 1회 디코드 후 검사(퍼센트 인코딩 우회 차단). docstring도 실제 커버리지에 맞게 수정. [api/tests/test_storage_signed_url_contract.py]
- [x] [Review][Patch] conventions §10 문구가 server actions를 배제하는 것처럼 읽힘 — **적용:** §10 web 헬퍼 설명을 "서버 컴포넌트·route handler·server actions 전용(브라우저 번들 금지)"로 정정. [docs/conventions.md:207]
- [x] [Review][Patch] Task 5 #45 물려받음 기록이 Completion Notes에 없음 — **적용:** Completion Notes에 "#45 물려받음(Task 5 기록)" 항목 추가(관리자 sold 사진 서명 불가를 그대로 물려받고 Epic 15가 마주침, 트리거는 tech-debt #45에 유지). [본 스토리 파일]
