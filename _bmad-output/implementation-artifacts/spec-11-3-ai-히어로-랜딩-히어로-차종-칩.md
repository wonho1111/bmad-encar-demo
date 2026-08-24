---
title: 'AI 히어로 랜딩 (히어로 + 차종 칩)'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_revision: 'c31bf335d53c4625f186ab1661243058ab554b66'
final_revision: 'ac93121b1de3e8f321917ef80d3f4a5a882ecc65'
review_loop_iteration: 0
followup_review_recommended: false # patch findings this pass: medium 1, low 1 → 3×1+1×1=4 (<5), no high → false
context: ['_bmad-output/implementation-artifacts/epic-11-context.md', '_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/mockups/landing-1.html']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 랜딩(`/`)에 AI 자연어 검색 진입점이 없다 — 로그인 사용자는 우하단 플로팅 버튼 하나뿐이고, 비로그인 사용자는 로그인/회원가입 안내만 보여 서비스가 뭘 하는지 첫 화면에서 전혀 체감할 수 없다(FR33/FR35). 비로그인 홈에는 Story 11.2가 만든 상단 내비도 아직 없다(#152 — 11.2가 "곧 11.3이 다시 그릴 화면"이라 의도적으로 비워둔 결손).
**Approach:** 딥 petrol 그라데이션 히어로 밴드(흰 검색 pill + amber 검색 버튼 + petrol 반투명 제안칩 4개) + 그 아래 차종 빠른 진입 칩을, `page.tsx`의 로그인/비로그인 두 분기 모두에 추가한다. 히어로 입력은 로그인 여부와 무관하게 항상 활성 상태이고 제출 시점에만 분기한다 — 비로그인은 로그인 게이트로 보내고 질의를 보존, 로그인은 `/ai`로 즉시실행 핸드오프한다. 비로그인 분기에는 `AppHeader`도 새로 호출한다(#152 해소).

## Boundaries & Constraints

**Always:**
- 히어로 입력창은 비활성화·자물쇠·"로그인 필요" 사전 안내를 절대 붙이지 않는다(시도 전에 거절하지 않는다 — AC 개정 2026-07-14).
- 검색 pill은 모든 뷰포트에서 가로 1행(아이콘+입력+버튼) 유지 — 세로 스택·2줄 버튼 금지(D5).
- 입력은 500자 상한 + 실시간 카운터: `maxLength=500` + 제출 시 방어적 길이 재확인(ChatAssistant의 1000자 가드와 동일 스타일, 상한값만 다름).
- **[비로그인]** 제출/제안칩 클릭 → `/ai/search` 미호출. `sessionStorage`에 `{query, autoRun:false}` 저장(키: `encar-hero-search-handoff`, `web/src/lib/heroSearchHandoff.ts` 단일 출처) 후 `/login?redirectedFrom=%2F`로 이동. 잔여 횟수 카운터 등은 어디에도 표시하지 않는다.
- **[비로그인→로그인 복귀]** `/` 재진입 시 히어로가 sessionStorage를 읽어 입력창에 복원하고 즉시 `removeItem`(1회용) — 자동 실행 금지, 사용자가 다시 눌러야 한다.
- **[로그인]** 제출/제안칩 클릭 → `sessionStorage`에 `{query, autoRun:true}` 저장 후 `/ai`로 이동. `ChatAssistant`가 마운트 시 이를 소비(읽고 즉시 삭제)하고 `autoRun===true`면 1회만 자동 실행한다 — 읽는 즉시 지워 새로고침·뒤로가기로 인한 재과금을 막는다(에픽이 명시적으로 경고한 위험).
- 제안칩 클릭은 입력 제출과 동일하게 취급한다(칩 텍스트 = 그 문장으로 즉시 시도).
- 차종 칩은 AI가 아니라 순수 카탈로그 필터다 — `/search`로 직접 링크한다(게이트 없음, `/search`는 보호 경로가 아니다).
- 차종 칩 값은 `LISTING_OPTIONS.body_type`/`fuel`(단일 출처, `web/src/lib/constants.ts`)에 실재하는 값만 쓴다: 전체(무필터)·경차(`body_type=경차`)·SUV(`body_type=SUV`)·전기(`fuel=전기`)·화물(`body_type=화물차`)·승합(`body_type=승합차`). "세단"·"친환경"·"수입"은 대응 필드가 없어 제외한다(근거는 Design Notes).
- 색·타이포는 기존 8.1 토큰만 쓴다(`brand-petrol-strong`→`petrol-deepest` 그라데이션, `accent-amber`+`amber-ink`, `rounded-chip`/`rounded-full`) — 새 hex를 하드코딩하지 않는다.

**Block If:** (없음 — 차종 칩 taxonomy는 DB 화이트리스트 기준으로, sessionStorage 키/모양과 로그인 즉시실행 대상(`/ai` 핸드오프)은 위 Always로 이미 확정)

**Never:**
- 인기/최신 매물 그리드(Story 11.4)를 만들지 않는다 — 히어로 + 차종 칩까지만.
- `/search`의 필터 엔진(`SearchFilters.tsx`, `pickOption`)을 바꾸지 않는다 — 기존 화이트리스트 값만 골라 링크한다.
- `ChatAssistant`의 대화창·1000자 상한·기존 제출 흐름을 재작성하지 않는다 — 마운트 1회 핸드오프 소비만 추가한다.
- 로그인 사용자의 기존 우하단 플로팅 AI 버튼을 지우지 않는다(히어로와 다소 중복돼 보일 수 있으나 이 스토리 범위 밖 — 관찰만 남긴다).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 비로그인, 입력 제출 | query="가성비 좋은 첫차" | `/ai/search` 미호출, sessionStorage 저장, `/login?redirectedFrom=%2F`로 이동 | 없음 |
| 비로그인, 제안칩 클릭 | 칩 텍스트="4천만원대 전기 SUV" | 입력 제출과 동일 취급, 위와 동일 동작 | 없음 |
| 로그인 복귀 후 `/` 재진입 | sessionStorage에 이전 질의 존재 | 입력창에 복원, sessionStorage 즉시 삭제, 자동 실행 없음 | 없음 |
| 로그인 사용자, 입력 제출 | query, 세션 유효 | sessionStorage `{query,autoRun:true}` 저장 → `/ai`로 이동 → 도착 즉시 1회 자동 실행 | 없음 |
| 501자 이상 입력 시도(붙여넣기) | 500자 초과 텍스트 붙여넣기 | `maxLength=500`으로 잘림, 카운터 500/500 표시 | 조용히 제한(카운터가 안내를 대신함) |
| `/ai` 새로고침(핸드오프 소비 후) | sessionStorage 비어있음 | 자동 실행 없음, 평소처럼 빈 입력창 | 없음 |
| 차종 칩 클릭(예: 경차) | 로그인 여부 무관 | `/search?body_type=경차`로 이동, 게이트 없음 | 없음 |

</intent-contract>

## Code Map

- `web/src/lib/heroSearchHandoff.ts` (신규) -- sessionStorage 키/모양 단일 출처: `setHeroSearchHandoff({query,autoRun})` / `consumeHeroSearchHandoff()`(읽고 즉시 삭제, 없으면 null). 히어로와 `ChatAssistant`가 공유해 두 곳에서 키·모양이 어긋나는 사고를 막는다.
- `web/src/components/landing/HeroSearch.tsx` (신규, `'use client'`) -- 딥 petrol 히어로 밴드: 헤드라인(amber 음절)+서브텍스트+흰 검색 pill(500자 카운터)+제안칩 4개("가성비 좋은 첫차"·"4천만원대 전기 SUV"·"주행거리 짧은 무사고 세단"·"7인승 디젤 패밀리카", `landing-1.html` 원문 그대로). `authed: boolean` prop. 제출/칩클릭 시 로그인 분기 처리, 마운트 시 핸드오프 복원(미실행).
- `web/src/components/landing/CategoryChips.tsx` (신규, 서버 컴포넌트) -- 차종 6칩, `/search?...`로 직접 링크.
- `web/src/app/page.tsx` (수정) -- 비로그인 분기에 `<AppHeader roleLabel={null} email={null} currentPath="/" />` 추가(#152 해소). 양쪽 분기 모두 헤더 아래에 `<HeroSearch authed={...} />` + `<CategoryChips />` 삽입.
- `web/src/components/ai/ChatAssistant.tsx` (수정) -- 제출 로직을 `runSearch(query)`로 추출해 `handleSubmit`과 신규 마운트 `useEffect`(핸드오프 소비, `autoRun`이면 1회 실행)가 함께 재사용.

## Tasks & Acceptance

**Execution:**
- `web/src/lib/heroSearchHandoff.ts` -- set/consume 순수 함수 작성 -- 두 컴포넌트가 같은 키·모양을 강제로 공유하게 한다.
- `web/src/lib/heroSearchHandoff.test.ts` -- 단위테스트(저장→소비→재조회 시 null) -- 새로고침 재실행 방지 불변식을 코드로 고정.
- `web/src/components/landing/HeroSearch.tsx` -- 히어로+검색pill+제안칩+게이트/핸드오프 로직 -- FR33/UX-DR8/AC개정(체감≠실행) 구현.
- `web/src/components/landing/CategoryChips.tsx` -- 차종 6칩 -- FR35, 화이트리스트 값만 사용.
- `web/src/app/page.tsx` -- 비로그인 분기 AppHeader 추가 + 양쪽 분기에 히어로/칩 삽입 -- #152 해소 + FR33/35.
- `web/src/components/ai/ChatAssistant.tsx` -- `runSearch` 추출 + 마운트 핸드오프 소비 -- 로그인 사용자의 "즉시 실행" AC 충족, 새로고침 재과금 방지.

**Acceptance Criteria:**
- Given 비로그인 방문자가 `/`을 열면, when 첫 화면을 보면, then 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록이 `/search`와 동일하게 상단에 보인다(#152).
- Given 비로그인 방문자, when 히어로 입력에 질의를 쓰고 제출(또는 제안칩 클릭)하면, then `/ai/search`가 호출되지 않고 `/login?redirectedFrom=%2F`로 이동하며 잔여 횟수 문구는 어디에도 없다.
- Given 위 상태에서 로그인에 성공해 `/`로 복귀하면, when 히어로를 보면, then 입력창에 원래 질의가 복원돼 있고 검색은 자동 실행되지 않는다.
- Given 로그인 사용자, when 히어로에서 제출하거나 제안칩을 클릭하면, then 게이트 없이 `/ai`로 이동해 그 질의가 1회 자동 실행된 결과(답변+매물카드)가 뜬다.
- Given 위에서 `/ai`가 자동 실행된 직후, when 사용자가 새로고침하면, then 같은 질의가 재실행되지 않는다.
- Given 아무 로그인 상태, when 차종 칩(경차/SUV/전기/화물/승합/전체)을 클릭하면, then 대응하는 `body_type`/`fuel` 파라미터로 `/search`에 게이트 없이 진입한다.
- Given 히어로 입력에 500자를 입력한 상태, when 501번째 글자를 시도하면, then 더 입력되지 않고 카운터가 500/500을 보여준다.
- Given 데스크톱(≥1100)·태블릿(640~1099)·모바일(<640) 각 폭, when 히어로를 보면, then 검색 pill은 항상 가로 1행이고 헤드라인의 amber 음절 대비가 유지된다(D5).

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 1: (high 0, medium 1, low 0)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` (adversarial·edge-case-hunter 공통 지적) `HeroSearch`의 마운트 복원 effect가 `autoRun` 값을 확인하지 않고 아무 핸드오프나 소비해, 로그인 사용자가 제출 직후 `/ai` 마운트 전에 `/`로 돌아오면(뒤로가기 등) `ChatAssistant` 몫의 `autoRun:true` 핸드오프를 가로채 텍스트 복원만 하고 자동실행 약속을 조용히 깬다. 대칭적으로 `ChatAssistant`도 자기 것이 아닌 `autoRun:false` 핸드오프를 소비해버릴 수 있다. 추가로 `submit()`이 서버 렌더 시점의 `authed` prop만 믿고 재검증 없이 `autoRun:true` 핸드오프를 먼저 써버려, 세션이 막 만료된 상태였다면 그 핸드오프가 고아로 남아 나중에 엉뚱한 시점에 자동실행될 수 있다(에픽이 명시적으로 경고한 재과금 위험과 같은 계열) — 구현 서브에이전트를 동기적으로 재위임하려 했으나 세션 재개 채널이 백그라운드로만 열려(SKILL.md의 "절대 백그라운드 금지" 규칙과 충돌) 오케스트레이터가 직접 패치했다: (1) `heroSearchHandoff.ts`의 `consumeHeroSearchHandoff`에 `expectedAutoRun` 매개변수를 추가해 자기 몫이 아닌 값은 지우지 않고 그대로 두도록 수정, 양쪽 소비처(`HeroSearch.tsx`·`ChatAssistant.tsx`)를 이 API로 갱신, (2) `HeroSearch.submit()`이 로그인 분기 진입 전 `supabase.auth.getUser()`로 재검증(기존 `WishButton.tsx` 패턴과 동일)하도록 수정. `heroSearchHandoff.test.ts`에 교차 소비 방지 케이스 추가. 패치 후 lint·`tsc --noEmit`·vitest(232/232)·build 재실행 green 확인 + Playwright MCP로 로그인 즉시실행·새로고침 재실행 방지·비로그인 게이트·복원 4가지 재검증 완료.
  - `[low]` `[patch]` `heroSearchHandoff.ts`의 두 catch 블록이 손상된 값·저장 실패를 로그 없이 조용히 삼켜, 이 프로젝트의 fail-loud 관례(`WishButton.tsx` 등)와 어긋난다 — 오케스트레이터가 직접 `console.error` 추가(위 패치와 같은 파일이라 함께 적용).

defer 1건은 `deferred-work.md`가 동결 파일이라(project-context.md 지침) `docs/tech-debt.md` #165로 등재했다: 히어로의 로그인 분기·핸드오프 소비 로직(`useEffect` 기반)에 자동 회귀검사가 없다는 verification-gap·adversarial 공통 지적 — `useEffect`는 SSR에서 안 돌아 이 리포의 순수함수 전용 vitest 설정으로는 못 닿고, jsdom/RTL 도입이나 Playwright 스위트 신설은 이 스토리 범위를 넘는다. 트리거는 Story 11.5(반응형 뷰포트 E2E 감사) 착수 시 — 11-2가 이미 심어 둔 `#160`(`SiteNav` 상호작용 검사 부재)과 같은 E2E 층에서 함께 고정한다.

reject 7건: `HeroSearch`의 `redirectedFrom=%2F` 하드코딩(현재 유일한 사용처인 `/`에선 정확함, 재사용은 가정일 뿐 — A2), `MAX_QUERY_LENGTH` 상수명이 `ChatAssistant`와 겹치지만 값 500/1000 차이를 양쪽 주석이 이미 설명함, 500자 초과 시 무안내 절단(현재 `<input maxLength>`로 도달 불가능한 방어 코드 — 자기 발견 사실), 우하단 플로팅 AI 버튼 주석의 "전역" 표현 부정확(이 diff 이전부터 있던 기존 주석, 스펙 Never가 이미 "관찰만" 하기로 결정), 차종 칩의 "화물"·"승합" 축약 라벨이 `/search` 필터 드롭다운의 "화물차"·"승합차" 전체 표기와 다름(목업 원문 그대로의 의도된 축약이며 실제 필터링은 정확 — 스펙 Design Notes 근거), `#152` 실측 검증이 diff에 기록되지 않음(오케스트레이터가 Playwright MCP로 직접 라이브 검증 완료 — 아래 Auto Run Result 참고), 한글 IME 조합 중 카운터가 순간적으로 500을 넘어 보일 수 있음(제출 시 재절단으로 데이터 손실 없음, 표시만의 문제).

## Design Notes

차종 칩을 목업(전체·경차·세단·SUV·전기·친환경·수입·화물·승합, 9개)보다 줄여 6개(전체·경차·SUV·전기·화물·승합)만 구현한다. 목업의 "세단"·"친환경"·"수입"은 `LISTING_OPTIONS.body_type`/`fuel`(DB CHECK와 바이트 단위 일치가 요구되는 단일 출처)에 대응 값이 없다 — "세단"은 준중형/중형/대형차 3종에 걸쳐 있어 하나의 칩으로 묶으면 라벨과 실제 필터 결과가 어긋나고, "친환경"은 하이브리드+전기 OR 조건이라 `/search`의 단일 `.eq()` 구조를 바꿔야 하며(Never), "수입"은 원산지 컬럼 자체가 없다. 라벨과 다른 결과가 나오는 칩을 만드느니, 실제로 작동하는 6개만 낸다("존재 확인"≠"작동 확인", CLAUDE.md B9).

**대장 점검(workflow persistent fact 이행):** 착수 시 `deferred-work.md`를 읽어 `status: open`인 `DW-1`(11-0 follow-up)·`DW-2`(11-1 follow-up)·`DW-3`(11-2 follow-up) 3건을 확인했다. `DW-1`은 이미 `docs/tech-debt.md` #148에, `DW-2`는 이미 #149에 있다(추가 조치 없음). `DW-3`(11-2의 review-budget-followup)은 대응 항목이 없어 신규 **#164**로 이관했다. `deferred-work.md` 원본은 동결 파일이라 수정하지 않았다.

`sessionStorage`는 이 코드베이스에 전례가 없는 신규 패턴이다(기존 로그인 게이트 전례인 `WishButton`은 `redirectedFrom` URL 자체에 값을 실었다). 질의 텍스트는 URL에 싣기엔 길고 인코딩이 지저분해지며, 무엇보다 에픽 AC 문면이 "sessionStorage에 보존하고 redirectedFrom에 복귀 경로를 담는다"고 이미 지정했다. 로그인 사용자의 "즉시 실행" 핸드오프도 같은 메커니즘을 재사용한다 — 새 패턴을 두 번 만들지 않기 위함이며, `autoRun` 플래그는 읽는 즉시 지워 새로고침·뒤로가기로 인한 이중 과금을 원천 차단한다.

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 경고.
- `cd web && npx tsc --noEmit` -- expected: 0 에러.
- `cd web && npx vitest run` -- expected: 기존 스위트 전부 green + 신규 `heroSearchHandoff.test.ts` 통과.
- `cd web && npm run build` -- expected: 빌드 성공.

**Manual checks (browser MCP, 로컬 Supabase):**
- 비로그인으로 `/` 열어 상단 내비·히어로·제안칩·차종칩 렌더 확인, 제안칩 클릭 → 로그인 게이트 이동 확인.
- 로그인 → `/`로 복귀 → 입력창에 질의 복원 + 미실행 확인.
- 로그인 상태에서 히어로 제출 → `/ai` 자동 실행 결과 확인 → 새로고침 → 재실행 안 됨(네트워크 탭에 추가 `/ai/search` 호출 없음) 확인.
- 320~1280px 폭 왕복하며 검색 pill 1행 유지·차종칩 줄바꿈 확인.

## Auto Run Result

**요약:** 랜딩(`/`)에 AI 자연어 검색 히어로(딥 petrol 밴드+흰 검색 pill+제안칩 4개)와 차종 빠른 진입 칩(6개)을 신설했다. 히어로 입력은 로그인 여부와 무관하게 항상 활성 상태이며, 제출/칩클릭 시 로그인 사용자는 `/ai`로 즉시실행 핸드오프, 비로그인 사용자는 로그인 게이트로 보내고 질의를 `sessionStorage`에 보존했다가 복귀 시 복원(자동실행 없음)한다. 비로그인 홈에 `AppHeader`를 새로 호출해 `/search`와 동일한 상단 내비를 갖추었다(#152 해소).

**파일 변경:**
- `web/src/lib/heroSearchHandoff.ts` (신규) -- 히어로↔`/ai` 간 질의 핸드오프 sessionStorage 단일 출처. 코드리뷰 패치로 `consumeHeroSearchHandoff(expectedAutoRun)`이 자기 몫이 아닌 값은 지우지 않고 남겨두도록 수정, 두 catch 블록에 `console.error` 추가.
- `web/src/lib/heroSearchHandoff.test.ts` (신규) -- 저장→소비→재조회 1회용 불변식 + 교차 소비 방지(내 몫이 아닌 autoRun 값은 안 지움) 단위테스트 6건.
- `web/src/components/landing/HeroSearch.tsx` (신규, client) -- 히어로 밴드 본체. 코드리뷰 패치로 `submit()`이 로그인 분기 진입 전 `supabase.auth.getUser()`로 세션을 재검증하도록 수정(async화).
- `web/src/components/landing/CategoryChips.tsx` (신규, server) -- 차종 6칩(전체/경차/SUV/전기/화물/승합), `/search`로 직접 링크.
- `web/src/app/page.tsx` (수정) -- 비로그인 분기에 `AppHeader` 추가(#152) + 양쪽 분기에 `HeroSearch`+`CategoryChips` 삽입, 중복되던 비로그인 CTA 카드 제거(SiteNav가 동일 링크를 이미 제공).
- `web/src/components/ai/ChatAssistant.tsx` (수정) -- `runSearch(query)` 추출 + 마운트 시 핸드오프 소비(autoRun:true만, 코드리뷰 패치로 `expectedAutoRun` 인자 반영) → 1회 자동실행.
- `docs/tech-debt.md` (수정) -- `#164`(DW-3 이관, 11-2의 review-budget-followup) · `#165`(신규, 히어로 로그인 분기·핸드오프 소비 로직에 자동 회귀검사 없음 — Story 11.5 E2E 감사에서 `#160`과 함께 고정) 등재.
- `_bmad-output/implementation-artifacts/epic-11-context.md` (수정) -- 착수 전 이미 stale(에픽 문서의 11.3/11.5 AC 심기 이후 미재생성 상태)이라 재컴파일해 현재 내용 반영.

**리뷰 결과:** 4개 레이어(blind-hunter/adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행 → 원시 지적 다수 → 중복 제거 후 patch 2(medium 1·low 1, 전부 수정 완료) · defer 1(medium, `docs/tech-debt.md` #165) · reject 7(전부 이미 완화됐거나 스펙이 명시적으로 승인한 동작, 또는 오케스트레이터의 라이브 검증으로 이미 해소). intent-alignment 레이어는 "행동은 코드에 있으나 diff 자체엔 실행 증거(스크린샷·자동 테스트)가 없다"는 절차적 관찰을 남겼는데, 이는 아래 검증 항목에서 실측으로 해소했다. 상세는 위 Review Triage Log 참고.
patch 재위임 경로 관련 메모: 구현 서브에이전트를 SendMessage로 재개하려 했으나 백그라운드 재개만 지원돼(동기 재위임 채널 없음) SKILL.md의 "절대 백그라운드 금지" 규칙과 충돌 — 오케스트레이터가 직접 패치를 적용했다(step-04 "재위임 불가 시 직접 적용" 대체 경로).

**검증:** `npm run lint`(0경고) · `npx tsc --noEmit`(0에러) · `npx vitest run`(232/232 통과, 초기 구현 시 230 + 패치 후 교차소비 테스트 2건 추가) · `npm run build`(성공) 전부 오케스트레이터가 패치 적용 전후 두 차례 직접 재실행해 확인. Playwright MCP + 로컬 Supabase(로그인 계정 `buyer@test.com`)로 다음을 전부 실측 확인: 비로그인 `/`의 상단 내비가 `/search`와 동일(#152) · 제안칩 클릭 시 `/ai/search` 미호출 + `/login?redirectedFrom=%2F` 이동 + sessionStorage에 `{query,autoRun:false}` 저장 · 로그인 복귀 시 입력창 복원 + sessionStorage 삭제 + 자동실행 없음(네트워크 탭에 `/ai/search` 없음) · 로그인 상태 히어로 제출 시 `/ai`로 이동해 1회 자동실행(실제 AI 응답 + 매물카드 5건 수신) · 그 직후 새로고침 시 재실행 안 됨(추가 `/ai/search` 호출 없음, 패치 전후 두 차례 확인) · 차종 칩 6개의 링크 대상(`/search?body_type=…`/`?fuel=전기`) 정확 · 375px 폭에서 검색 pill 1행 유지(D5).

**잔여 리스크:**
- `#165`(신규): 히어로의 로그인 분기·핸드오프 소비 로직(`useEffect` 기반)에 자동 회귀검사가 없다 — 이 리포의 vitest 설정이 순수 함수만 단위테스트하는 프로젝트 관례(11-2의 `SiteNav.test.ts`와 동일 한계) 때문에, 지금은 Playwright MCP 수동 세션이 유일한 검증 수단이다. Story 11.5의 E2E 감사가 `#160`(SiteNav 상호작용)과 함께 고정하기로 예정.
- `#159`(11-2에서 이관, 재확인만): buyer·admin에게도 "내 차 팔기" 진입점이 보이고 눌러도 말없이 홈으로 튕긴다 — 이 스토리가 만든 문제는 아니며 그대로 남아 있다.
- 차종 칩을 목업 9개에서 6개로 줄인 것(Design Notes 근거)은 데이터 정합성을 위한 의도적 축소이지 결함이 아니지만, 사용자가 나중에 "세단"·"수입" 필터를 원하면 별도 스키마 작업(원산지 컬럼 신설 등)이 필요하다는 점은 기록해 둔다.

**잔존 아티팩트(이 스토리 범위 밖, 커밋 대상 아님):** 없음 — `git status --porcelain` 확인 결과 이 스토리가 만들거나 수정한 파일 전부가 리뷰 대상 diff에 포함됨.
