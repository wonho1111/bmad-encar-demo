---
title: '인기/최신 매물 그리드'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_revision: '548348226ffca75bc91f2272d355e5af80e5a20c'
final_revision: '3dfca487b1cd305403ebf2b85e6122f9d9116b9c'
review_loop_iteration: 0
followup_review_recommended: false # patch findings this pass: medium 1, low 1 → 3×1+1×1=4 (<5), no high → false
context: ['_bmad-output/implementation-artifacts/epic-11-context.md']
warnings: ['oversized'] # 두 쿼리(인기/최신)+anon 정규화+마이그레이션+대장 #134/#144 컨텍스트를 한 파일에 응집(단일 스토리 cross-layer)한 결과 1600 토큰 목표 초과 — 이전 11.x 스토리들과 같은 패턴.
---

<intent-contract>

## Intent

**Problem:** 랜딩(`/`)의 히어로+차종 칩(11.3) 아래에 실제 매물이 없어, 방문자가 "진짜 매물이 있는 서비스"라는 감을 검색 전에 못 잡는다. 로그인 사용자만 보던 기존 "최근 매물" 단일 섹션도 view_count(11.1) 정렬을 전혀 쓰지 않는다.
**Approach:** `CategoryChips` 아래에 인기(view_count desc)·최신(created_at desc) 2단 발췌 그리드(각 4건)를 신설해 로그인·비로그인 양쪽 분기에 동일하게 렌더한다. 기존 "최근 매물" 단일 섹션은 이 그리드의 "최신" 단으로 흡수돼 대체된다. 각 단의 "전체 보기"는 `/search`로만 진입(필터·정렬 파라미터 없음 — 랜딩은 URL 쿼리를 소유하지 않는다). 대장 이월 `#134`(anon view_count SELECT 권한)·`#144`(정렬 인덱스)를 같은 마이그레이션에서 함께 해소한다.

## Boundaries & Constraints

**Always:**
- 인기 단: `buyerListingsQuery`(on_sale만, FR11) + `.order('view_count', {ascending:false}).order('id', {ascending:false}).limit(4)`.
- 최신 단: `buyerListingsQuery` + `.order('created_at', {ascending:false}).order('id', {ascending:false}).limit(4)` — 기존 홈 미리보기와 동일 쿼리 모양.
- 두 단 모두 `attachCoverImages`로 대표사진을 채운다(9.4와 동일 함수, 로직 이원화 금지).
- `/search`처럼 로그인 사용자에게만 신뢰속성 3컬럼(`accident_status`,`is_single_owner`,`is_non_smoker`)을 select에 포함하고, anon 행은 그 3필드를 명시적으로 `null`로 채운다(anon은 0011 화이트리스트에 그 컬럼이 없어 select 자체가 42501로 죽는다 — `SearchPage`의 `trustColumns`/`normalizedRows` 패턴을 그대로 따른다).
- 찜 오버레이(`fetchWishedListingIds`)는 로그인 시에만, 두 단의 id를 합쳐 한 번만 조회한다.
- 각 단이 비었거나(0건) 조회 실패해도 다른 단·히어로·차종칩 렌더를 막지 않는다(`console.error`로만 로깅, 기존 홈 미리보기 방침과 동일).
- 반응형은 `ResponsiveGrid`(4/2/1열)를 그대로 재사용한다 — 새 그리드 규칙을 만들지 않는다(D5).
- 마이그레이션(다음 빈 번호, 0021)에 `grant select (view_count) on public.listings to anon;`과 `create index if not exists listings_view_count_idx on public.listings (view_count desc) where status = 'on_sale';`를 함께 넣는다(`#134`·`#144` 해소, `docs/tech-debt.md` 144번이 지정한 정확한 형태).
- 비로그인으로 랜딩을 열어 인기 단이 42501 없이 렌더됨을 반드시 실측 검증한다(`#134`가 로그인 상태에선 안 걸리는 비대칭이라 놓치기 쉬움, 문서 경고).

**Block If:** (없음 — 쿼리 모양·컬럼 화이트리스트·마이그레이션 내용 전부 기존 패턴·대장 문서로 확정됨)

**Never:**
- `/search`의 필터 엔진·정렬(`SearchPage`, `SearchFilters`)을 바꾸지 않는다 — "전체 보기"는 무필터 `/search` 진입만 한다.
- anon 컬럼 화이트리스트를 이 스토리가 필요로 하는 `view_count` 외로 넓히지 않는다.
- `ListingCard`에 조회수 숫자를 새로 표시하지 않는다 — AC는 "정렬"만 요구하며 카드 디자인은 Epic 9/10 확정본을 그대로 쓴다(`view_count`는 `ListingCardData`에 이미 optional로 존재하나 미표시 필드).
- 로그인 사용자 홈의 "본인 정보" 섹션(구매문의·판매중 n건 텍스트 메뉴)·우하단 AI 플로팅 버튼은 건드리지 않는다 — 이 스토리는 "최근 매물" 서브섹션만 대체한다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 비로그인, 매물 존재 | anon, on_sale 매물 5건 이상 | 인기 4건·최신 4건 그리드가 각각 렌더, 신뢰속성 3필드는 표시 안 됨(null) | 없음 |
| 로그인, 매물 존재 | authenticated | 인기 4건·최신 4건 + 신뢰속성 뱃지까지 표시 | 없음 |
| on_sale 매물 0건 | 빈 카탈로그 | 두 단 모두 "아직 등록된 매물이 없습니다." 안내 | 없음 |
| 인기 단 조회 실패, 최신 단 성공 | 인기 쿼리 error | 최신 단은 정상 렌더, 인기 단만 에러 안내 문구 | 서버 로그에 원본 error, 사용자에겐 "불러오지 못했습니다" |
| 조회수 동률 다수 | 여러 매물 view_count=0(신규 등록 직후) | id desc tie-break로 결정적 순서(새로고침해도 순서 불변) | 없음 |
| 인기 단과 최신 단에 같은 매물 중복 등장 | 방금 등록 + 이미 조회수 높음 | 두 단에 동일 매물이 각각 나타남(허용 — 서로 다른 랭킹 발췌) | 없음 |

</intent-contract>

## Code Map

- `supabase/migrations/0021_listings_view_count_anon_grant.sql` (신규) -- anon `view_count` SELECT 권한 + 부분 인덱스(`#134`·`#144` 해소).
- `web/src/lib/listings.ts` (수정) -- `fetchPopularAndRecentListings(supabase, user)` 추가: 인기/최신 두 쿼리 병렬 실행 + trustColumns 조건부 + anon null 정규화 + `attachCoverImages` 적용, `{popular, recent}` 반환.
- `web/src/components/landing/PopularRecentGrid.tsx` (신규, 서버 컴포넌트) -- 인기/최신 2개 섹션(제목+"전체 보기"+`ResponsiveGrid`+`ListingCard`), 내부 `ListingGridSection` 서브컴포넌트로 중복 제거.
- `web/src/app/page.tsx` (수정) -- 로그인 분기의 기존 "최근 매물" 단일 섹션(미리보기 쿼리·`previewListings`·`previewError`)을 제거하고 `fetchPopularAndRecentListings`+`PopularRecentGrid` 호출로 교체. 비로그인 분기에 `<main>` 래퍼 + `PopularRecentGrid` 신설(`/search`의 `max-w-6xl p-6` 패턴과 동일 폭).
- `docs/tech-debt.md` (수정) -- `#134`·`#144` 항목을 이 스토리가 해소했다고 표시(상태 갱신, B5 — 대장 이월 약속의 이행 확인은 문서가 아니라 코드지만, 대장 자체도 닫아야 "안 한 것"과 구분된다).

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0021_listings_view_count_anon_grant.sql` -- GRANT + 부분 인덱스 작성 -- `#134`(비로그인 인기정렬 42501)·`#144`(정렬 인덱스 부재) 해소.
- `web/src/lib/listings.ts` -- `fetchPopularAndRecentListings` 추가 -- 인기/최신 쿼리·trustColumns·null 정규화·이미지 첨부를 한 곳에 모아 `page.tsx` 양쪽 분기가 같은 함수를 쓰게 한다.
- `web/src/lib/__tests__/listings.test.ts` (기존 파일 있으면 확장, 없으면 신규) -- anon 정규화(신뢰속성 3필드 null 강제) 단위테스트 -- I/O 매트릭스의 "비로그인" 케이스를 코드로 고정.
- `web/src/components/landing/PopularRecentGrid.tsx` -- 인기/최신 섹션 렌더 -- FR34.
- `web/src/app/page.tsx` -- 로그인 분기 교체 + 비로그인 분기 신설 -- FR34, sold 제외(FR11)는 `buyerListingsQuery` 상속.

**Acceptance Criteria:**
- Given 완성된 매물 카드(Epic 9/10)와 view_count(11.1), when 랜딩을 렌더하면, then 인기(view_count 정렬)/최근 등록(created_at 정렬) 2단 발췌 그리드가 표시된다(FR34).
- Given 랜딩의 각 그리드 단, when "전체 보기"를 클릭하면, then `/search`로 진입하고 랜딩은 필터·쿼리파라미터를 넘기지 않는다.
- Given sold로 전환된 매물, when 랜딩을 다시 로드하면, then 그 매물은 인기·최신 어느 단에도 나타나지 않는다(FR11).
- Given ≥1100px/640~1099px/<640px 각 폭, when 그리드를 보면, then 4/2/1열로 재배치되고 카드 내부 가로배치는 세로화되지 않는다(D5).
- Given 비로그인 방문자, when 랜딩을 열면, then 인기 단이 42501 오류 없이 렌더된다(`#134` 회귀 확인 — 로그인 상태만 검증하면 이 결함을 놓친다).

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 2: (high 0, medium 0, low 2)
- reject: 6: (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` (adversarial·edge-case-hunter 공통 지적) `fetchSection`(`web/src/lib/listings.ts`)이 Supabase 쿼리·`attachCoverImages`를 `try/catch` 없이 호출해, 쿼리가 `{data,error}`가 아니라 실제 예외(throw)로 실패하면 `Promise.all`이 통째로 터져 `Home()` 전체(히어로·차종칩·본인정보까지)가 깨진다 — intent-contract Always("각 단이 비었거나 조회 실패해도 다른 단·히어로·차종칩 렌더를 막지 않는다")를 위반하는 경로. `fetchSection` 본문을 `try/catch`로 감싸 예외도 `{error:true}`로 흡수하도록 패치.
  - `[low]` `[patch]` (adversarial 지적) 기존 "최근 매물" 섹션의 에러 문구에 있던 "매물 탐색으로 이동" 복구 링크가 `PopularRecentGrid.tsx`의 새 에러 분기에서 빠져 스크린리더 사용자가 alert 안에서 바로 행동할 수단이 없어졌다 — alert 텍스트에 `/search` 링크를 다시 추가.

defer 2건은 `deferred-work.md`가 동결 파일이라 `docs/tech-debt.md`에 새 번호로 등재했다: ① 마이그레이션 게이트(`scripts/check_migrations.py`)의 anon 컬럼 권한 프로브가 "아무 컬럼이나 SELECT 가능한가"만 보는 범용 검사라, `anon`의 `view_count` SELECT 권한(#134 해소분)이 향후 실수로 되돌려져도 게이트가 못 잡는다(verification-gap·adversarial 공통 지적) — 게이트 인프라 변경은 이 스토리 범위 밖(A3), Story 11.5 E2E 착수 또는 게이트 정비 시점(Epic 13, #143과 같은 축)으로 이관. ② `fetchSection`의 `{error:true}` 반환 로직 자체(쿼리 실패 시 분기)가 mock 기반 단위테스트로 검증되지 않는다(`#166`이 이미 인정한 "JSX 렌더 미검증"과는 별개 공백) — 같은 트리거(Story 11.5)에서 함께 처리.

reject 6건: 인기·최신 두 단이 겹치는 매물의 `attachCoverImages` 중복 호출(찜 id는 dedup했는데 사진 조회는 안 했다는 지적 — 결과는 정확하고 이 리포 규모(100여 건)에서 비용이 무시할 만하며, 병합하면 단별 실패 격리 설계와 충돌), 찜 id 배열에 중복 id가 dedup 없이 `.in()`에 전달됨(Postgres가 정확히 처리, 결과 영향 없음), `listings_view_count_idx`가 `id` tie-break 컬럼까지 커버하지 못함(`docs/tech-debt.md` #144가 지정한 정확한 인덱스 형태 그대로 구현 — 그 이상은 대장이 승인하지 않은 추측성 확장, A2), 두 쿼리가 원자적 스냅샷이 아니라는 지적(intent 자체가 "2단 개별 쿼리"를 Always로 못박아 이 리포 규모에서 이론적 위험일 뿐), `normalizeAnonTrustColumns` 주석의 근거 설명이 실제 `TrustAttributes.tsx`의 undefined/null 처리와 정확히 일치하진 않음(동작 자체는 Always 규칙대로 맞음, 주석 표현만의 문제 — 코드 정확성에 영향 없음), 비로그인 트래픽 증가로 인한 DB 부하 우려(랜딩은 원래 이 리포에서 가장 트래픽이 큰 공개 페이지고 캐시 없음은 기존 로그인 분기 미리보기도 동일했던 기존 패턴 — 이 스토리가 새로 만든 위험이 아니라 사전부터 있던 아키텍처 특성).

**AC5(비로그인 42501 회귀) 재검증:** intent-alignment 레이어가 "구현 서브에이전트의 브라우저 검증 스냅샷이 실제로 비로그인+랜딩 조합을 보여주는지 근거가 불명확하다"고 지적해, 오케스트레이터가 직접 재검증했다(B4 — 재보기 전엔 선언하지 않는다). 이 스토리의 diff가 반영된 코드로 새 dev 서버(포트 3211, 기존 3117 프로세스는 2026-07-27 21:22 시작된 구코드 잔존 프로세스로 확인돼 배제)를 띄우고 `curl`(쿠키 없음=비로그인)로 `/`를 직접 요청 → 응답 HTML에 "지금 인기"·"방금 올라온 매물" 섹션이 실제 매물과 함께 렌더됨을 확인, "불러오지 못했습니다"·"아직 등록된 매물이 없습니다" 문구는 없었고 서버 로그에도 42501/permission denied 없음. AC5는 실측으로 확인됨. 검증에 쓴 임시 dev 서버는 종료함.

## Design Notes

**단당 개수 = 4:** AC 문면엔 개수가 없어, 근거를 목업(`ux-designs/.../mockups/landing-1.html:604-726`)에서 가져온다 — "지금 인기"·"방금 올라온 매물" 두 섹션 모두 데스크톱 4열 그리드에 카드 4장씩 배치돼 있다. 기존 홈 미리보기의 `PREVIEW_COUNT=4`와도 일치해 새 상수를 도입하지 않고 그대로 재사용한다.

**섹션 제목만 쓰고 eyebrow 부제는 넣지 않는다:** 목업은 `eyebrow-sm`(예: "많이 보고 있는 매물"/"최신순") 서브라벨을 쓰지만, 이 코드베이스엔 그 토큰·클래스가 없다(8.1 디자인 토큰에 없음, `HeroSearch`·`CategoryChips`도 eyebrow 없이 제목만 씀). 새 텍스트 스타일을 이 스토리에서 만들지 않고, 기존 홈 "최근 매물" 섹션과 같은 형태(`text-section`+"전체 보기" 링크)로 통일한다. 섹션 제목은 목업 문구를 그대로 쓴다: 인기="지금 인기", 최신="방금 올라온 매물".

**대장 점검(workflow persistent fact 이행):** 착수 시 `deferred-work.md`를 읽어 `status: open`인 `DW-1`(11-0)·`DW-2`(11-1)·`DW-3`(11-2) 3건을 확인했다 — 전부 Story 11-3이 이미 처리했다(`DW-1`→`docs/tech-debt.md` #148, `DW-2`→#149, `DW-3`→#164, 전부 "이미 있음"으로 중복 등재 없이 종결). 이 스토리 착수 시점에 새 `DW-<번호>` 항목은 없다(11-3은 `followup_review_recommended: false`로 마감돼 후속 DW가 생성되지 않았다). `deferred-work.md` 원본은 동결 파일이라 수정하지 않는다.

**"최근 매물" 섹션 대체(신규 작성 아님):** 기존 로그인 홈의 "최근 매물" 섹션은 이 스토리가 만들려는 최신 단과 쿼리 모양이 동일하다(`created_at desc, id desc, limit 4`). 그 섹션을 남겨두고 인기 단만 추가하면 홈에 3단 그리드가 되어 UX 목업과도, 에픽 목표("2단 발췌")와도 어긋난다 — 그래서 기존 섹션의 쿼리·렌더를 `PopularRecentGrid`의 최신 단으로 흡수한다(A3: 이미 있던 로직을 옮기는 것이지 무관한 리팩터가 아니다).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 경고.
- `cd web && npx tsc --noEmit` -- expected: 0 에러.
- `cd web && npx vitest run` -- expected: 기존 스위트 전부 green + 신규 anon 정규화 테스트 통과.
- `cd web && npm run build` -- expected: 빌드 성공.
- 마이그레이션 재적용(스크래치 Postgres에 0001~0021 순서 적용) -- expected: exit 0, `has_column_privilege('anon', 'public.listings', 'view_count', 'SELECT')` = true.

**Manual checks (browser MCP, 로컬 Supabase):**
- 비로그인으로 `/` 열어 인기·최신 그리드 렌더 확인(신뢰속성 미표시), 네트워크/콘솔에 42501 없음 확인.
- 로그인 상태로 `/` 열어 인기·최신 그리드 + 신뢰속성 뱃지 확인.
- 두 그리드 "전체 보기" 클릭 → `/search`(쿼리파라미터 없음) 진입 확인.
- 판매완료 처리한 매물 하나를 새로고침 후 인기·최신 어느 단에도 없음 확인.
- 320~1280px 폭 왕복하며 4/2/1열 재배치 확인.

## Auto Run Result

**요약:** 랜딩(`/`)에 인기(view_count desc)·최신(created_at desc) 2단 발췌 그리드(각 4건)를 신설했다. 로그인·비로그인 양쪽 분기가 같은 함수(`fetchPopularAndRecentListings`)·컴포넌트(`PopularRecentGrid`)를 공유한다. 로그인 홈의 기존 "최근 매물" 단일 섹션은 이 그리드의 "최신" 단으로 흡수돼 대체됐고, 비로그인 홈에는 이 그리드가 처음 생겼다. 대장 이월 `#134`(anon view_count SELECT 권한)·`#144`(정렬 인덱스)를 마이그레이션 0021에서 함께 해소했다.

**파일 변경:**
- `supabase/migrations/0021_listings_view_count_anon_grant.sql` (신규) -- `grant select (view_count) ... to anon` + `listings_view_count_idx` 부분 인덱스. `#134`·`#144` 해소.
- `web/src/lib/listings.ts` (수정) -- `fetchPopularAndRecentListings`/`fetchSection`/`normalizeAnonTrustColumns` 추가. 코드리뷰 패치로 `fetchSection`을 `try/catch`로 감싸 예외도 단별 실패로 흡수하도록 수정.
- `web/src/components/landing/PopularRecentGrid.tsx` (신규) -- 인기/최신 2개 섹션(제목+전체보기+그리드/빈상태/에러). 코드리뷰 패치로 에러 문구에 `/search` 복구 링크 추가.
- `web/src/app/page.tsx` (수정) -- 로그인 분기의 "최근 매물" 단일 섹션 제거 후 신규 그리드로 교체, 비로그인 분기에 `<main>`+그리드 신설.
- `web/src/lib/__tests__/listings.test.ts` (신규) -- `normalizeAnonTrustColumns` 단위테스트 5건.
- `docs/tech-debt.md` (수정) -- `#134`·`#144`를 "✅ 해소"로 갱신, `#166`(Matrix 미검증 4행, 코드리뷰로 범위 보강)·`#167`(마이그레이션 게이트가 anon view_count 권한 회귀를 못 잡음, 신규) 등재.

**리뷰 결과:** 4개 레이어(blind-hunter/adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행 → patch 2(medium 1·low 1, 전부 수정 완료: `fetchSection` try/catch + 에러 문구 복구 링크) · defer 2(low, `docs/tech-debt.md` #166 보강·#167 신규) · reject 6(전부 결과에 영향 없는 최적화 여지이거나 스펙이 이미 승인한 형태). 구현 서브에이전트를 SendMessage로 재개하려 했으나 백그라운드 재개만 지원돼(동기 재위임 채널 없음, 11-3과 동일 제약) 오케스트레이터가 직접 패치를 적용했다(해당 background 작업은 즉시 `TaskStop`으로 중단해 충돌 방지).

**AC5 재검증(오케스트레이터 직접 실측):** intent-alignment 레이어가 구현 서브에이전트의 브라우저 검증 스냅샷이 "비로그인+랜딩" 조합을 명확히 보여주지 못한다고 지적해, 재보기 전 선언 금지(B4) 원칙에 따라 직접 재검증했다. 포트 3117의 기존 next 프로세스가 2026-07-27 21:22 시작된 구코드 잔존 서버임을 확인하고 배제, 이 스토리의 최신 코드로 임시 dev 서버(포트 3211)를 새로 띄워 `curl`(쿠키 없음=비로그인)로 `/`를 요청 → 응답에 "지금 인기"·"방금 올라온 매물" 섹션이 실제 매물과 함께 렌더됨을 확인, 에러/빈상태 문구 없음, 서버 로그에도 42501 없음. 검증 후 임시 서버는 종료.

**검증:** 패치 적용 후 재실행 — `npm run lint`(0경고) · `npx tsc --noEmit`(0에러) · `npx vitest run`(237/237 통과) · `npm run build`(성공). 구현 시점에는 추가로 `scripts/check_migrations.py`(21개 마이그 정적+동적 게이트 통과, 0021 재적용 exit 0)와 로컬 Supabase Playwright MCP 수동 검증(로그인/비로그인 렌더, sold 제외, 반응형 4/2/1열)을 수행했다.

**잔여 리스크:**
- `#166`(보강): 그리드 빈 상태·단별 실패 격리(JSX)·`fetchSection` 에러 로직 자체·tie-break·양단 중복 노출 4가지가 자동 검사 0건 — Story 11.5 E2E 착수 시 해소 예정.
- `#167`(신규): 마이그레이션 게이트가 `anon`의 `view_count` SELECT 권한 회귀를 구체적으로 잡지 못한다 — 게이트 정비(Epic 13, `#143`과 같은 축) 또는 Story 11.5 착수 시 해소 예정.
- 인기·최신 두 단이 겹치는 매물의 사진 조회(`attachCoverImages`)가 단별로 중복 실행되는 비효율이 있으나(reject 처리, 찜 id dedup과의 비일관성 지적), 결과 정확성엔 영향 없고 이 리포 규모에서 비용은 무시할 만하다.

**잔존 아티팩트(이 스토리 범위 밖, 커밋 대상 아님):** 없음 — `git status --porcelain` 확인 결과 이 스토리가 만들거나 수정한 파일 전부가 리뷰 대상 diff에 포함됨.

