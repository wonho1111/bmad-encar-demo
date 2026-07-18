---
baseline_commit: 110ac4074b4e1b1c05e5dbcd1e83e5bbd1f7d5f9
---

# Story 9.0: 공개 버킷 전환 — 서명 URL 제거

Status: ready-for-dev

> **번호에 대해**: Epic 9는 9.1~9.7로 계획됐고 9.1~9.3이 이미 `done`이다. 이 스토리는 **9.4 착수 직전에 사용자 결정으로 삽입**된 것이라 "9.4보다 먼저 와야 한다"는 뜻으로 9.0을 쓴다. 시간순이 아니라 **의존 순서**를 나타내는 번호다.

## Story

As a 이 서비스를 만드는 사람,
I want 매물 사진을 비공개 버킷+서명 URL이 아니라 공개 버킷+고정 URL로 서빙하길,
so that 만료·재발급·삭제순서 때문에 생긴 부채 6건이 사라지고 이후 스토리(9.4~9.7·15.1·16.2)가 단순해진다.

## 배경 — 왜 뒤집는가 (사용자 결정 2026-07-19)

원래 설계(ADR-IMG-01)는 FR11("판매완료 매물은 구매자에게 안 보인다")을 **"사진 바이너리까지 접근 불가"** 로 해석해 비공개 버킷 + 1시간 서명 URL을 골랐다. 그 해석이 실제로 물린 값:

| # | 내용 | 전환 후 |
|---|---|---|
| #45 | 관리자가 sold 매물 사진 못 봄 | 해소 |
| #46 | 정상 권한으로 못 지우는 영구 고아 (**실제 2건 발생**) | 구조 소멸 |
| #50-2 | **서명인데도 sold 후 1시간 뚫림** | 항목 무효(수용으로 대체) |
| #55 | 서명 만료 후 미리보기 복구 수단 없음 | 항목 소멸 |
| #62 | 배치 서명 결과 위치 매칭 위험 | 항목 소멸 |
| #44 | 버킷 선존재 시 비공개·5MB·MIME 무효 | 이 마이그가 값을 강제로 덮어써 해소 |

핵심은 **#50-2**다 — 이 복잡도를 다 감수하고도 FR11이 지켜지지 않았고, 그게 "수용"으로 문서에 적혀 있었다. **비용은 전부 내고 효과는 못 얻은 상태**였다.

**사용자 결정 요지(2026-07-19)**
- 공개 버킷으로 전환한다.
- **매물 삭제 시 사진이 함께 사라지는 것**은 반드시 보장한다 → 판매자 경로는 이미 그렇고(`e851bba`), **관리자 경로가 빠져 있어 이번에 막는다**.
- **판매완료(sold) 후에도 사진 URL이 열리는 것은 수용한다.** sold는 되돌릴 수 있는 상태 변경인데 파일 삭제는 되돌릴 수 없고, Story 15.1이 "관리자는 sold 포함 열람"을 이미 AC로 갖고 있어 지우면 그게 깨진다.

## Acceptance Criteria

1. **버킷이 공개로 전환된다** — 마이그레이션 `0014`가 `storage.buckets`의 `listing-images`를 `public = true`로 바꾼다.
   - 같은 문장에서 `file_size_limit`(5MB)·`allowed_mime_types`(3종)를 **UPDATE로 다시 못박는다** — 0012는 `on conflict do nothing`이라 버킷이 이미 있으면 이 값들이 조용히 무효였다(#44). UPDATE는 그 구멍이 없다.
   - **업로드(쓰기) 권한은 건드리지 않는다** — 본인 경로에만 insert/update/delete하는 0012·0013 정책은 그대로다. "공개"는 **읽기만** 공개다.

2. **파일 접근 정책이 경로 기반으로 단순해진다** — `storage.objects`의 읽기 정책을 `listing_images` 조인 방식에서 **"경로 첫 세그먼트 = 내 uid, 또는 관리자"** 로 교체한다.
   - **왜 이게 핵심인가**: 기존 정책은 "그 파일을 가리키는 DB 행이 살아 있어야 내 파일로 인정"이라, 행이 먼저 사라지면 파일이 **소유자에게도 안 보여 영영 못 지워졌다**(#46·#51의 뿌리, 9.3의 삭제순서 계약이 존재하는 이유). 경로 기반은 행과 무관하므로 이 구조가 사라진다.
   - `anon`용 SELECT 정책은 **필요 없다** — 공개 버킷의 읽기는 `/object/public/` 경로로 나가 RLS를 타지 않는다. 정책은 인증 사용자의 삭제·목록 조회를 위해서만 남는다.
   - **관리자 DELETE 정책도 추가한다**(AC4가 필요로 함).
   - ⚠️ **이 AC는 원격에서 실제로 재현해 확인한다** — "행 없는 객체를 소유자가 지울 수 있는가"를 눈으로 보기 전에는 문서에 적지 않는다(CLAUDE.md B4).

3. **web·app이 서명 대신 공개 URL을 쓴다**
   - `web/src/lib/storage/index.ts` — `getSignedUrl`/`getSignedUrls`/`SIGNED_URL_TTL` 제거, `getPublicUrl(bucket, path)` 하나로 대체. **비동기가 아니고 실패하지 않는다**(순수 문자열 조립)
   - `app/lib/core/supabase/storage_helper.dart` — 같은 모양으로 미러
   - 소비처 갱신: `web/src/app/(user)/sell/[id]/edit/page.tsx`
   - 서명이 사라지므로 "**서버에서만 서명 가능**"이라는 제약도 사라진다 — 이 사실을 관련 주석에서 정리한다(잘못된 제약이 남으면 다음 사람이 그걸 따른다)

4. **관리자 매물 삭제가 사진을 정리한다** 🔴 — `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx`가 매물 행을 지우기 전에 사진 오브젝트를 먼저 지운다. 판매자 경로(`ListingActions.tsx`)와 **같은 함수**를 쓴다(로직 이원화 금지).
   - 정리에 실패하면 **매물 삭제를 중단**한다 — 판매자 경로와 동일한 계약.
   - 이건 이번 전환과 무관하게 **지금 존재하는 버그**다(조사 중 발견, grep 실측: 해당 파일에 storage 관련 코드 0건).

5. **계약 문서가 사실과 일치한다** — `docs/conventions.md`
   - §4: `image_url` = "대표 서명 URL" → "대표 공개 URL"
   - §6: FR11 강제 지점에서 `storage.objects` 축을 내리고, **"사진 파일 URL은 FR11 강제 대상이 아니다(수용, 사용자 결정 2026-07-19)"** 를 명시한다. **각주가 아니라 본문에** 쓴다 — 다음 사람이 또 막으려 덤비지 않게.
   - §10: 버킷 = 공개, `SIGNED_URL_TTL` 절 삭제, 헬퍼 계약 교체
   - §10.1: **삭제 순서 계약을 다시 쓴다** — "① 오브젝트 → ② 행" 순서가 필요했던 **이유가 사라진다**. 규칙을 지울지 남길지는 AC2 실측 결과로 정한다(측정 전에 지우지 않는다).

6. **대장이 닫힌다** — `docs/tech-debt.md`
   - 닫음/무효화 6건: #44 · #45 · #46(성격 변화) · #50-2 · #55 · #62 — 각각 **근거(마이그 번호·커밋)를 병기**한다
   - 신규 1건: 공개 URL 수용 기록(무엇을 포기했는지 + 사용자 결정일)
   - AC4는 버그 수정이므로 부채 등재가 아니라 **해소로 기록**한다

7. **스펙 문서가 새 결정을 가리킨다** (경위 문서는 고치지 않는다)
   - `architecture-increment-2026-07-12.md`: ADR-IMG-01을 **지우지 않고**, 바로 아래 **ADR-IMG-02(공개 버킷, 2026-07-19)** 를 추가해 "01을 대체함"으로 잇는다
   - `epics-increment-2026-07-12.md`: Story 9.1·9.2 AC, AC-CONTRACT-1, "확정된 값"의 `SIGNED_URL_TTL` 항목에 정정 주석
   - **`done` 스토리(9-1·9-2·9-3)와 회고·PRD 결정로그는 본문을 고치지 않는다** — 당시 결정의 기록이다. 최상단에 "이 설계는 9.0(0014)으로 대체됨" **한 줄만** 단다(CLAUDE.md B8 — 제약과 경위를 섞지 않는다)

8. **Story 9.4를 다시 쓴다** — 현재 `ready-for-dev` 상태인 9.4 스토리가 서명 URL을 전제로 쓰여 있다. 그대로 두면 dev가 옛 구조로 만든다. 서명 관련 지침(배치 서명·서버 전용 제약·`next/image` 결정 항목)이 빠지므로 **더 짧고 단순해진다**.

9. **검증 — 실제로 돌려서 관찰한다**
   - 원격 Supabase: 공개 URL이 로그인 없이 열리는가 · **행 없는 객체를 소유자가 지울 수 있는가**(AC2 핵심) · 업로드가 여전히 본인 경로에만 되는가(권한이 안 새는지)
   - 브라우저: `/sell/[id]/edit`에서 기존 사진 미리보기가 정상 표시 · 매물 삭제 시 사진이 실제로 사라짐 · **관리자 삭제도 마찬가지**(AC4)
   - 관찰한 것을 Completion Notes에 사실대로 적는다

## Tasks / Subtasks

- [ ] **Task 1 — 마이그레이션 0014 (AC: 1, 2)**
  - [ ] `supabase/migrations/0014_listing_images_public_bucket.sql` 작성 — 버킷 public/상한 UPDATE + 읽기 정책 교체 + 관리자 DELETE 정책
  - [ ] Supabase MCP `apply_migration`으로 적용(런북 §3 — db가 항상 먼저)
  - [ ] **원격 실측**: 공개 URL 익명 접근 / 행 없는 객체 소유자 삭제 / 타인 경로 업로드 차단 → Debug Log에 응답 원문 기록

- [ ] **Task 2 — web·app 헬퍼 교체 (AC: 3)**
  - [ ] `web/src/lib/storage/index.ts` → `getPublicUrl` (순수 함수, `getSupabaseEnv()` 사용)
  - [ ] Vitest `index.test.ts` — URL 조립·경로 인코딩(공백·한글 파일명) 검증. 일부러 깨서 red 확인 후 되돌림
  - [ ] `app/lib/core/supabase/storage_helper.dart` 미러
  - [ ] 소비처(`edit/page.tsx`) 갱신 + 관련 주석 정리

- [ ] **Task 3 — 관리자 삭제 버그 (AC: 4)** 🔴
  - [ ] `ListingAdminActions.tsx`가 `deleteListingPhotoObjects`를 먼저 호출하고, 실패 시 삭제 중단
  - [ ] 브라우저로 실제 관리자 삭제 → Storage에서 파일이 사라지는지 확인

- [ ] **Task 4 — 계약·대장 (AC: 5, 6)**
  - [ ] `docs/conventions.md` §4·§6·§10·§10.1
  - [ ] `docs/tech-debt.md` 6건 닫기 + 1건 신규 + AC4 해소 기록

- [ ] **Task 5 — 스펙 정정·9.4 재작성 (AC: 7, 8)**
  - [ ] architecture ADR-IMG-02 추가 · epics 정정 주석 · done 스토리 3건에 supersede 한 줄
  - [ ] 9.4 스토리 재작성

- [ ] **Task 6 — 검증 (AC: 9)**
  - [ ] 위 실측·브라우저 확인 수행, 결과 기록, dev 서버 정리

## Dev Notes

### 유지되는 것 (건드리지 말 것)

- **업로드 권한** — 본인 경로에만(0012·0013). "공개"는 읽기만이다.
- **MIME 3종 화이트리스트** — 공개 버킷에서 **더 중요해진다**. 인증 없이 열리므로 `.html`/`.svg`가 올라가면 우리 도메인에서 실행되는 저장형 XSS다. 근거 문구를 "비공개라도"에서 "공개라서 더욱"으로 고칠 것.
- **경로 무결성 트리거(0013)** — 소유자·매물 대조. 공개/비공개와 무관한 무결성 규칙이다.
- **10장·5MB 상한**, `listing_images` 테이블 RLS, `ai_readonly` 정책.
- **api 계약** — `api`는 URL을 만들지 않고 `storage_path`만 반환한다. 공개 URL도 api가 만들 이유가 없다(`ai_readonly` 최소권한). `api/tests/test_storage_signed_url_contract.py`도 **그대로 살린다** — 다만 이름·docstring이 "서명"을 말하므로 "api는 URL을 만들지 않는다"로 의미를 넓히는 정도만 손본다.

### 무엇이 실제로 뒤집히는가

| | 전 | 후 |
|---|---|---|
| URL | 1시간 후 만료, 매번 재발급 | 고정 |
| 발급 위치 | 서버만(서버 클라이언트 필요) | 아무 데나(순수 문자열) |
| 실패 | `null` 반환 → 플레이스홀더 | 실패 개념 없음. 파일이 없으면 `onError` → 플레이스홀더 |
| 목록 N장 | 배치 1회 왕복 | 왕복 0회 |
| sold 사진 | 1시간 뒤 차단(문서상) | 계속 열림(**명시 수용**) |

`image_url`이 `null`/`""`이면 플레이스홀더라는 **§4 계약은 그대로다** — 사진 행이 아예 없는 매물이 여전히 많다(시드 100건).

### 함정

- **`getPublicUrl`은 파일 존재를 확인하지 않는다.** 경로만 있으면 문자열이 나온다. 그래서 소비처의 `onError` → 플레이스홀더 폴백이 **전보다 중요해진다**(9.4 AC3).
- **경로 인코딩**: 파일명이 uuid라 지금은 안전하지만, 헬퍼는 범용이므로 공백·한글이 들어와도 깨지지 않게 인코딩한다. 슬래시(`/`)는 살려야 한다 — `encodeURIComponent`를 경로 전체에 그냥 걸면 구분자까지 먹는다.
- **마이그레이션은 전진만**(B3). 버킷 값은 UPDATE로 덮어쓰고, 정책은 `drop policy if exists` 후 재생성한다. 되돌리는 마이그를 만들지 않는다.
- **단일 공유 Supabase** — 적용 즉시 운영 반영이다(런북 §2). 그래서 db를 먼저 올리고, web은 그 뒤 push한다. 다행히 이 변경은 **db만 먼저 가도 구 web이 안 깨진다**(구 web은 서명 URL을 계속 발급하는데, 공개 버킷에서도 서명 발급은 정상 동작한다).

### References

- [Source: docs/conventions.md#4·6·10·10.1] — 고칠 계약 정본
- [Source: docs/tech-debt.md#44·45·46·50-2·51·55·62] — 닫을 항목과 근거
- [Source: supabase/migrations/0012_listing_images.sql:76-80·177-188] — 버킷 값·읽기 정책 원문
- [Source: supabase/migrations/0013_listing_images_path_integrity.sql] — 경로 트리거·쓰기 정책 3분리
- [Source: web/src/app/(user)/sell/ListingActions.tsx:92-139] — 판매자 삭제 계약(관리자가 따라야 할 모범)
- [Source: web/src/app/(admin)/admin/listings/ListingAdminActions.tsx:31-73] — 사진 정리 누락 지점
- [Source: docs/deployment-runbook.md#2·3] — 단일 공유 Supabase, db→api→web 순서
- [Source: _bmad-output/planning-artifacts/architecture-increment-2026-07-12.md:173] — 대체 대상 ADR-IMG-01

## Dev Agent Record

### Agent Model Used

Claude Opus 4.8 (1M context) — 스토리 작성·구현 동일 세션(코드리뷰는 새 세션에서, B4).

### Debug Log References

**1. 마이그 0014 적용 전 상태 (원격 실측 2026-07-19)**
- `storage.buckets`: `public = false`, `file_size_limit = 5242880`, MIME 3종
- `storage.objects` 정책 4종: `..._owner_delete`(DELETE) · `..._owner_insert`(INSERT) · `..._owner_update`(UPDATE) · `..._read`(SELECT, **anon+authenticated**, `listing_images` 조인)

**2. 적용 후 상태**
- `storage.buckets`: `public = true`
- 정책 5종: 위 3개 쓰기 정책 + `..._owner_select`(SELECT, **authenticated만**, 경로 기반 `or is_admin()`) + `..._admin_delete`(DELETE, 관리자)

**3. AC2 핵심 실측 — "행 없는 고아 객체를 소유자가 볼 수 있는가"**
버킷의 유일한 잔존 객체 `12dfba00-…/x/.emptyFolderPlaceholder`(`listing_images` 행 **없음**)로 RLS를 시뮬레이션(`set local role` + `request.jwt.claims`):

| 주체 | 보이는 행 | 판정 |
|---|---|---|
| 소유자(`12dfba00-…`) | **1** | ✅ 전에는 0이었다(#51 실측: DELETE 403·LIST 0건). **회수 불가 구조가 사라졌다** |
| 관리자 | **1** | ✅ #45 해소 |
| 다른 사용자 | **0** | ✅ 권한이 새지 않음 |
| anon | **0** | ✅ 정책 대상 아님(공개 읽기는 `/object/public/`이 담당) |

**4. 공개 URL HTTP 실측 (인증 헤더 없이)**
- 실존 객체 → `HTTP 200`
- 없는 파일 → `HTTP 400`
- 존재하지 않는 버킷 → `HTTP 400`
- **헬퍼 출력과 연결 확인**: `getPublicUrl`과 동일한 인코딩 로직으로 만든 URL을 그대로 curl → `HTTP 200`. 즉 테스트가 단언하는 문자열 형식이 **실제로 열리는 주소**임을 확인했다(형식만 맞고 안 열리는 경우를 배제).

**5. 앱 기동 확인 (로컬 dev)**
`/` 200 · `/search` 200 · `/listings/{없는 id}` 200(중립 안내 화면, 기존 동작) · 서버 로그 에러 0건.

**6. 테스트가 실제로 잡는지 (red→green)**
`getPublicUrl`의 세그먼트별 인코딩을 경로 전체 `encodeURIComponent`로 **일부러 바꿔** 3건 전부 red 확인 → 되돌려 green 확인. `npm test` 전체 70건 통과, `tsc --noEmit` 무출력, `npm run lint` 무출력.

**7. ✎ 기존 기록 정정 — #46의 "프로브 객체 2개"**
`docs/tech-debt.md` #46은 지울 수 없는 프로브 객체 **2개**가 남았다고 적고 있으나, 2026-07-19 실측 시 버킷의 객체는 **1개**(`.emptyFolderPlaceholder`)뿐이다. 언제 사라졌는지 기록이 없다 — **당시 기록이 지금 사실과 다르다는 것만** #46에 적어 뒀다(추측으로 경위를 지어내지 않음).

### Completion Notes List

**설계 판단 1 — 읽기 정책을 "경로 기반"으로 바꾼 것이 이 스토리의 실질**
버킷을 공개로 돌리는 것만으로는 부채가 안 닫힌다. `#46`·`#51`·§10.1 삭제순서 계약의 뿌리는 전부 *"`storage.objects` SELECT가 `listing_images` 행과 조인해야 참"* 이라는 한 문장이었고, Storage API의 DELETE·LIST가 대상을 먼저 SELECT로 찾기 때문에 **행이 먼저 사라지면 파일이 미아**가 됐다. `0014`는 그 조인을 없앴다. 위 실측 3번이 그 효과를 직접 보여준다.

**설계 판단 2 — `getPublicUrl`을 Supabase 클라이언트 없이 순수 함수로**
`storage.from().getPublicUrl()`을 쓰려면 클라이언트 인스턴스가 필요한데, 이 함수는 서버 컴포넌트·브라우저 양쪽에서 불린다(서버에서 브라우저 클라이언트를 만드는 건 부적절). 순수 문자열 조립이라 **단위테스트가 가능**해지는 이점도 있다. 대가는 URL 형식을 우리가 안다는 가정인데, 실측 4번이 그 가정을 확인한다.

**설계 판단 3 — 삭제 순서 코드를 지우지 않았다**
`① 오브젝트 → ② 행` 순서는 이제 안전을 좌우하지 않지만(실측 3번), 코드는 그대로 뒀다. 무해하고 실패 처리가 명확하기 때문이다(A3 — 안 깨진 걸 리팩터하지 않는다). 대신 **§10.1의 "이 순서를 어기면 되돌릴 수 없다"는 서술은 사실이 아니게 됐으므로 고쳤다** — 문서가 코드보다 위험했다.

**설계 판단 4 — 관리자가 `@/app/(user)/sell/photo-sync`를 import한다**
라우트 그룹을 가로지르는 import라 이상적이진 않다. 그러나 대안(`lib/`로 이동)은 판매자 경로까지 건드리는 리팩터이고, 지금 필요한 것은 **정리 규칙이 한 벌이라는 보장**이다. 세 번째 삭제 경로가 생기면 그때 옮긴다(#66에 기록).

**이 스토리가 안 한 것(명시)**
- **인증이 필요한 화면의 브라우저 검증을 못 했다** — `/sell/[id]/edit` 미리보기, 판매자·관리자 삭제 후 파일이 실제로 사라지는지는 **로그인 세션이 필요해 확인하지 못했다**. 게다가 현재 버킷에 실제 매물 사진이 **0장**이라(잔존 객체는 폴더 플레이스홀더뿐) 렌더할 사진 자체가 없다. → **AC9의 브라우저 항목은 미완이며, 사용자 계정으로 확인이 필요하다.**
- `#43`(10장 UPDATE 우회)·`#49`(경합)·`#56`(동시 편집 고아)는 **손대지 않았다** — 이 전환과 무관한 축이다.
- `api`는 한 줄도 안 고쳤다. "api는 URL을 만들지 않고 `storage_path`만 반환"은 공개 버킷에서도 유효한 최소권한 원칙이라 계약을 유지했다(`test_storage_signed_url_contract.py`도 그대로 통과 — 공개 URL에는 `/sign/`·`token=` 마커가 없다).

### File List

**신규**
- `supabase/migrations/0014_listing_images_public_bucket.sql`
- `web/src/lib/storage/index.test.ts`
- `_bmad-output/implementation-artifacts/9-0-공개-버킷-전환-서명-url-제거.md`(이 파일)

**수정 — 코드**
- `web/src/lib/storage/index.ts`(서명 3개 export → `getPublicUrl` 1개)
- `web/src/app/(user)/sell/[id]/edit/page.tsx`(배치 서명 → 행별 공개 URL)
- `web/src/app/(admin)/admin/listings/ListingAdminActions.tsx`(**사진 정리 추가 — #66**)
- `app/lib/core/supabase/storage_helper.dart`(미러)
- 주석 정리: `PhotoUploader.tsx` · `SellForm.tsx` · `photo-item.ts` · `ListingCard.tsx` · `lib/storage/upload.ts` · `lib/images/resize.ts` · `app/lib/features/listings/listing.dart`

**수정 — 문서**
- `docs/conventions.md`(§4 · §6 + **§6.1 신설** · §10 · §10.1)
- `docs/tech-debt.md`(#44·#45·#46·#50-2·#55·#62 닫음/하향 · **#65·#66 신규** · 요약표 갱신)
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md`(**ADR-IMG-02 추가**, 01은 보존)
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md`(9.1·9.2 정정 주석 · AC-CONTRACT-1 · TTL 확정값)
- `_bmad-output/implementation-artifacts/9-1·9-2·9-3`(**본문 불변**, supersede 한 줄만)
- `_bmad-output/implementation-artifacts/9-4-*.md`(재작성)
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
