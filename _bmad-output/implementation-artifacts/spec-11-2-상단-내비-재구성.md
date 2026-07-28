---
title: '상단 내비 재구성'
type: 'feature'
created: '2026-07-28'
status: done
baseline_revision: 'd6548a9f7e79eed13e89b5eead650dab94eb1f4e'
final_revision: '9d5fb41' # 3차 리뷰의 코드·문서 변경을 담은 커밋
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 현재 `AppHeader`는 Epic 11 이전 임시 최소 헤더(로고 자리에 평문 텍스트, 찜은 텍스트 링크 하나)라 "내 차 사기·AI로 찾기·내 차 팔기" 같은 1급 진입점이 없고 반응형·프로필 메뉴도 없어(FR38 미충족) 소비자가 메뉴에서 헤매기 쉽다.
**Approach:** 로그인 상태별 소비자 내비(로고·내 차 사기·AI로 찾기·내 차 팔기 | 비로그인=로그인·내 차 등록 / 로그인=찜♡·채팅🔔·프로필▾)를 재구성하고, 모바일 햄버거·프로필 드롭다운을 신설한다. 관리자 페이지는 기존 최소 헤더를 그대로 둔다. "프로필▾ → 내 정보"가 가리킬 최소 읽기전용 계정 페이지를 신설하되, 닉네임 편집 등 전체 기능은 대장(tech-debt.md)에 이관한다(이를 구현하는 스토리가 아직 없어 없으면 dropdown 항목이 죽은 링크가 된다).

## Boundaries & Constraints

**Always:**
- 라벨은 소비자 자연어만 쓴다(내 차 사기·AI로 찾기·내 차 팔기·내 차 등록·찜·로그아웃) — "탐색"·"매물 탐색" 등 개발용어 금지(UX-DR18).
- 전역 "문의" 메뉴는 두지 않는다(문의는 매물 상세에서만 개시).
- 링크: 내 차 사기→`/search`, AI로 찾기→`/ai`, 내 차 팔기/내 차 등록→`/sell`, 찜♡→`/wishlist`, 채팅🔔→`/chat`, 로그인→`/login?redirectedFrom=<currentPath>`. 채팅🔔은 아이콘 자리만(안읽음 배지 없음 — Epic 12/Story 12.5 소관, 9.4 찜 시드 방식과 동일 전례).
- 아이콘 버튼(찜·채팅·햄버거)은 히트영역 ≥44×44px + 한국어 `aria-label`. 프로필 드롭다운·모바일 햄버거 패널은 기존 `FocusTrap`(`web/src/components/ui/FocusTrap.tsx`)으로 감싼다(Esc 닫힘, 닫힐 때 트리거로 포커스 복귀 — 이미 구현된 메커니즘, 재사용만 한다).
- 반응형 collapse는 **760px** 기준(`mockups/consistency-1.html`의 명시적 실측치 "내비→햄버거 = 760px"): `<760px`에서 텍스트 링크가 햄버거로 접히고, 찜·채팅 아이콘은 로그인 시 항상 상단 노출. 카드 그리드의 640/1100 기준과는 별개 값이다.
- 관리자(`(admin)` 레이아웃) 페이지는 기존 최소 헤더(역할라벨·이메일·로그아웃)를 그대로 유지한다 — 신규 소비자 메뉴는 admin에 렌더하지 않는다(관리자는 사고팔지 않으므로 UX-DR16 대상이 아님).
- role-aware 확장 지점: nav 링크 계산은 별도 순수 함수(`nav-links.ts`)로 분리해, Epic 14의 역할 분기가 이 함수만 바꾸면 되게 한다(내비 JSX 파일 재작성 불필요).
- `Logo` 컴포넌트(`web/src/components/ui/Logo.tsx`)를 홈(`/`) 링크로 감싸 배선한다(현재 어디에도 안 쓰이고 있음 — 기술부채 #125의 대상).

**Block If:** (없음 — "내 정보" 페이지 범위, admin 예외, 760px 기준값 등 실행 중 갈릴 수 있었던 판단은 전부 위 조사(EXPERIENCE.md·nav-ia-rules.md·mockups/consistency-1.html·기존 코드)로 사전에 확정됨. 남은 유일한 불확실성은 `docs/tech-debt.md`의 다음 빈 번호(`#148`)뿐인데, 착수 시 재확인만 하면 되므로 블로킹 아님.)

**Never:**
- `requireRole('seller')`(`web/src/lib/auth/guard.ts`) 동작을 바꾸지 않는다 — buyer가 로그인 상태에서 "내 차 팔기"를 눌러 `/sell` 진입 시 홈으로 리다이렉트되는 기존 동작은 이 스토리 범위 밖(Epic 14 역할 통합이 다룬다).
- "내 정보" 페이지에 닉네임 편집·저장 폼·`profiles` UPDATE RLS/GRANT를 구현하지 않는다 — 신규 DB 마이그레이션 없음. 읽기 전용 표시만 한다.
- 채팅 안읽음 배지 데이터·집계 로직을 구현하지 않는다(Epic 12).
- 랜딩 히어로·인기/최신 그리드(Story 11.3/11.4)에 손대지 않는다 — 홈 페이지(`app/page.tsx`)의 본문 콘텐츠는 그대로 둔다(헤더 렌더 호출부만 그대로 유지, 수정 없음).
- 8개 기존 `AppHeader` 호출부의 `roleLabel`/`email`/`currentPath` prop 시그니처를 바꾸지 않는다(관리자 레이아웃 1곳만 신규 `variant` prop을 추가로 전달).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 비로그인 데스크톱 렌더 | `email=null`, `variant='consumer'`, width≥760px | 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록 표시. 찜/채팅/프로필▾ 없음 | 없음 |
| 로그인 데스크톱 렌더 | `email` 있음, width≥760px | 로고·3개 링크·찜♡·채팅🔔·프로필▾ 표시. 로그인/내 차 등록 없음 | 없음 |
| 관리자 페이지 렌더 | `variant='admin'` | 기존 최소 헤더(역할라벨·이메일·로그아웃)만, 신규 소비자 메뉴 미노출 | 없음 |
| 모바일 뷰포트 | width<760px, 로그인 | 텍스트 링크가 햄버거(☰)로 접힘, 찜·채팅 아이콘은 상단 상시 노출 | 없음 |
| 프로필▾ 드롭다운 열기 | 클릭/Enter | 내 매물 관리(`/sell`)·내 정보(`/account`)·로그아웃 노출, FocusTrap 적용, Esc로 닫히고 트리거로 포커스 복귀 | 없음 |
| 햄버거 패널 열기 | 클릭(width<760px) | 텍스트 링크 목록 노출, FocusTrap 적용, Esc로 닫힘 | 없음 |
| `/account` 비로그인 직접 접근 | 세션 없음 | `proxy.ts`가 `/login?redirectedFrom=/account`로 리다이렉트 | 없음(기존 보호 경로 패턴) |
| `/account` 로그인 접근 | 세션 있음 | 이메일·역할 라벨·표시 이름을 읽기 전용으로 렌더 | 프로필 조회 실패 시 한국어 에러 문구(기존 `sellerSummaryError` 패턴) |

</intent-contract>

## Code Map

- `web/src/components/layout/nav-links.ts` (신규) -- role-aware 확장 지점: `getConsumerNavLinks(role: UserRole | null)` 순수 함수, 현재는 role 무관 동일 3개 링크 반환(내 차 사기·AI로 찾기·내 차 팔기) — Epic 14가 이 함수만 확장하면 됨.
- `web/src/components/layout/SiteNav.tsx` (신규, `'use client'`) -- 데스크톱 링크 행 + 우측 로그인상태 분기(찜♡·채팅🔔·프로필▾ 또는 로그인·내 차 등록) + 모바일 햄버거(<760px) + 프로필 드롭다운, 둘 다 `FocusTrap` 재사용.
- `web/src/components/layout/AppHeader.tsx` (수정) -- `Logo`를 `/` 링크로 배선, `variant?: 'consumer' | 'admin'`(기본 `'consumer'`) prop 추가. `'admin'`이면 기존 로직(역할라벨·이메일·로그아웃) 그대로, 그 외엔 `SiteNav` 렌더.
- `web/src/app/(admin)/layout.tsx` (수정, 1줄) -- `<AppHeader variant="admin" .../>`로 기존 동작 명시 보존.
- `web/src/app/(user)/account/page.tsx` (신규) -- "내 정보" 읽기전용 페이지: `requireUser()` 게이트 + `profiles.role/name` 조회 + 이메일·역할라벨·이름 표시.
- `web/src/proxy.ts` (수정) -- `PROTECTED_PREFIXES`에 `'/account'` 추가(개인 페이지, `/wishlist`·`/chat`와 동일 패턴 — 로그인 필수, 본인 데이터만 노출은 서버 컴포넌트의 `auth.getUser()` 자체가 보장).
- `docs/tech-debt.md` (수정) -- 3건 신규 등재: `#148`(대장 점검, workflow persistent fact 이행 -- `deferred-work.md`의 `DW-1`: 11-0 리뷰의 독립 후속 리뷰 권장이 미이관), `#149`(같은 사유, `DW-2`: 11-1의 독립 후속 리뷰 권장), `#150`("내 정보(닉네임 등) 편집 기능 미구현" -- `/account`는 읽기 전용, EXPERIENCE.md가 이미 명세한 편집 동작(검증·저장/취소·토스트)을 구현하는 스토리가 아직 없음, 트리거 = 향후 계정 관리 스토리). `#148`·`#149`는 이 스토리의 실체가 아니라 이관 작업일 뿐이므로 Design Notes에 근거를 남긴다.

## Tasks & Acceptance

**Execution:**
- `web/src/components/layout/nav-links.ts` -- `getConsumerNavLinks(role)` 작성 -- role-aware 훅 자리를 실제 함수로 못박아 Epic 14가 이 파일만 확장하면 되게 한다.
- `web/src/components/layout/SiteNav.tsx` -- 데스크톱 nav + 모바일 햄버거 + 프로필▾ 드롭다운 작성 -- `FocusTrap`을 그대로 재사용해 접근성 요구(포커스 트랩·Esc·복귀)를 새로 만들지 않는다. 아이콘 버튼엔 `aria-label`("찜한 매물"/"채팅"/"메뉴 열기" 등) 명시.
- `web/src/components/layout/AppHeader.tsx` -- `Logo` 배선 + `variant` 분기 -- 관리자 회귀를 막기 위해 기존 admin 렌더 경로는 조건부로 그대로 보존.
- `web/src/app/(admin)/layout.tsx` -- `variant="admin"` 전달 -- 이 한 줄만 바뀌므로 다른 7개 호출부는 무변경.
- `web/src/app/(user)/account/page.tsx` -- 읽기전용 계정 페이지 -- `requireUser()` + `profiles` select(`role`,`name`) + 이메일(auth user)·역할라벨(`ROLE_LABEL`)·이름 렌더.
- `web/src/proxy.ts` -- `PROTECTED_PREFIXES`에 `/account` 추가 -- 다른 보호 경로와 동일하게 비로그인 1차 차단.
- `docs/tech-debt.md` -- `#148`·`#149`(DW-1·DW-2 이관)·`#150`("내 정보" defer) 추가 -- 대장 미기재 시 두 사실(독립 후속 리뷰 권장·"내 정보" 미완성)이 조용히 사라진다(B8). 이관 후 `deferred-work.md`는 절대 수정하지 않는다(동결 파일, PreToolUse 훅이 쓰기를 차단).

**Acceptance Criteria:**
- Given 비로그인 사용자가 데스크톱(≥760px)에서 아무 공개 페이지를 열면, when 상단 내비를 보면, then 로고·내 차 사기·AI로 찾기·내 차 팔기·로그인·내 차 등록이 보이고 찜/채팅/프로필▾는 없다.
- Given 로그인 사용자(구매자 또는 판매자)가 데스크톱에서 페이지를 열면, when 상단 내비를 보면, then 로고·3개 링크·찜♡·채팅🔔·프로필▾가 보이고 로그인/내 차 등록은 없으며, 전역 "문의" 메뉴는 어디에도 없다.
- Given 로그인 사용자, when 프로필▾를 클릭하면, then 내 매물 관리(`/sell`)·내 정보(`/account`)·로그아웃이 나타나고, Esc를 누르면 닫히며 포커스가 트리거로 돌아온다.
- Given 관리자로 로그인한 사용자가 `/admin`을 열면, when 상단바를 보면, then 기존과 동일한 최소 헤더(역할·이메일·로그아웃)만 보이고 신규 소비자 메뉴 항목은 보이지 않는다.
- Given 뷰포트 폭을 760px 아래로 좁히면, when 내비를 보면, then 텍스트 링크는 햄버거(☰) 안으로 접히고, 로그인 사용자의 찜·채팅 아이콘은 상단에 그대로 남는다.
- Given 로그인 사용자가 "내 정보"를 클릭해 `/account`로 이동하면, when 페이지가 렌더되면, then 이메일·역할·이름이 표시된다(편집 폼은 없음).
- Given 비로그인 사용자가 `/account`에 직접 URL로 접근하면, when 요청이 처리되면, then `/login?redirectedFrom=%2Faccount`로 리다이렉트된다.
- Given 로그인한 buyer가 "내 차 팔기"를 클릭해 `/sell`에 진입하면, when `requireRole('seller')`가 평가되면, then (이 스토리로 변경되지 않은) 기존 동작대로 홈으로 리다이렉트된다 — 회귀가 아님을 확인한다.

## Design Notes

**"내 정보"를 왜 읽기전용으로 좁혔나:** EXPERIENCE.md(Component Patterns)는 닉네임 편집(필수·공백/길이 검증·저장/취소·토스트)을 상세히 그려두었지만, 이를 만드는 스토리가 백로그 어디에도 없다(Epic 6~14 전수 확인). 반면 같은 에픽의 채팅🔔 배지도 동일하게 "아직 소유 스토리가 없는 하위 기능"이라 "아이콘 자리만" 배치하는 선례를 이미 남겼다(epic-11-context.md) — 그 전례를 "내 정보"에도 적용한다. 다만 채팅은 목적지(`/chat`)가 이미 동작하므로 아이콘만 자리표시자면 충분했던 반면, "내 정보"는 목적지 자체가 없어(클릭하면 404) 최소 읽기전용 페이지까지는 만들어야 AC의 "구성된다"(드롭다운 항목이 살아있다)를 충족한다. 편집 기능은 별도 마이그레이션(RLS `profiles_update_self` + 컬럼 단위 GRANT 하드닝, Story 11.1의 view_count 패턴과 동형)이 필요한 별개 작업이라 대장(#150)에 이관한다.

**대장 점검(workflow persistent fact 이행):** 착수 시 `deferred-work.md`를 읽어 `status: open`인 `DW-1`(11-0 follow-up review recommended)·`DW-2`(11-1 follow-up review recommended) 2건을 발견했다. `docs/tech-debt.md`에 대응 항목이 없어(둘 다 스토리 코드리뷰의 실체적 defer 목록 `#124~#147`과는 별개로, "review budget 소진으로 독립 후속 리뷰가 필요하다"는 메타 권고 자체가 어디에도 등재돼 있지 않음) `#148`·`#149`로 신규 이관한다. `deferred-work.md` 원본은 동결 파일이라 수정하지 않는다.

**admin 예외:** 관리자는 `/admin` 운영 허브로 즉시 유도되는 별도 역할(nav-ia-rules.md §1)이라 "내 차 사기·AI로 찾기·내 차 팔기" 같은 소비자 메뉴가 의미 없다. `variant` prop으로 분기해 기존 admin 렌더 경로를 그대로 보존한다(회귀 없음).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 경고.
- `cd web && npx tsc --noEmit` -- expected: 0 에러.
- `cd web && npx vitest run` -- expected: 기존 스위트 전부 green(회귀 없음).
- `cd web && npm run build` -- expected: 빌드 성공(신규 라우트 `/account` 포함).

**Manual checks (browser MCP, 로컬 Supabase):**
- 데스크톱(1280px) 뷰포트에서 비로그인/구매자 로그인/판매자 로그인/관리자 로그인 4가지 상태로 각 페이지를 열어 내비 구성이 AC대로 나오는지 스크린샷으로 확인.
- 뷰포트를 700px로 리사이즈해 햄버거 전환과 찜·채팅 아이콘 상시 노출을 확인.
- 키보드만으로 프로필▾ 열기→Tab 순환→Esc 닫힘→포커스 복귀, 햄버거도 동일하게 확인.
- 로그인 상태에서 `/account` 접근해 이메일·역할·이름이 실제 값으로 뜨는지 확인, 비로그인으로 `/account` 직접 접근 시 로그인으로 리다이렉트되는지 확인.
- buyer로 로그인해 "내 차 팔기" 클릭 → 기존처럼 홈으로 튕기는지 확인(회귀 아님을 실측으로 남긴다).

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 1, medium 2, low 6)
- defer: 1: (low 1)
- reject: 8: (low 7, medium 1)
- addressed_findings:
  - `[high]` `[patch]` 프로필▾ 드롭다운·모바일 햄버거 패널이 바깥 클릭으로 안 닫힘(재사용한 `FocusTrap`은 포커스 이탈만 막고 마우스 바깥 클릭 닫기는 지원 안 함) — `SiteNav.tsx`에 컨테이너별 outside-click(`mousedown`) 핸들러 2개 추가로 수정.
  - `[medium]` `[patch]` 프로필▾·햄버거 트리거가 토글이 아니라 항상 열기만 함(다시 눌러도 안 닫힘) — `onClick`을 `(v) => !v]` 토글로 수정.
  - `[medium]` `[patch]` 로그인 상태 모바일(<760px)에서 프로필▾·햄버거 버튼이 동시에 보여 두 `FocusTrap`이 동시에 열리면 포커스가 서로 다툼 — 하나를 열 때 다른 하나를 먼저 닫도록 상호배타 처리.
  - `[low]` `[patch]` 트리거 `aria-label`이 열림/닫힘 상태와 무관하게 "…열기"로 고정 — 상태에 따라 "…닫기"로 바뀌도록 수정.
  - `[low]` `[patch]` 프로필 드롭다운의 `role="menu"`/`"menuitem"`이 실제 구현(Tab 순환만, 화살표키 탐색 없음)과 어긋남 — role 속성 제거.
  - `[low]` `[patch]` `LogoutButton`을 감싼 `role="menuitem"` div가 실제 인터랙티브 버튼을 이중으로 감쌈 — role 제거, 평범한 wrapper로 변경.
  - `[low]` `[patch]` `AppHeader.tsx` 주석이 "8개 호출부"라 적었지만 이 스토리가 추가한 `account/page.tsx`까지 포함하면 9개 — 주석 수정.
  - `[low]` `[patch]` `account/page.tsx`의 이메일 표시에 `역할`·`이름`과 달리 `'-'` 폴백이 없어 이메일 없는 계정(폰 인증 등)에서 빈칸 노출 — `?? '-'` 추가.
  - `[low]` `[patch]` `nav-links.test.ts`의 두 번째 테스트가 `role`을 무시하는 구현을 검증해 논리상 절대 실패할 수 없음(회귀 방지 효과 없음) — 해당 테스트 블록 삭제.

패치 9건 전부 구현 서브에이전트에 재위임해 적용 후, lint·`tsc --noEmit`·`vitest run`(216/216 통과, 태생적으로 실패 불가능하던 테스트 삭제로 217→216)·`npm run build`를 오케스트레이터가 직접 재실행해 확인했고, Playwright MCP로 프로필▾·햄버거의 토글/바깥클릭/Esc/상호배타 동작을 재검증했다(상세는 Auto Run Result 참고).

defer 1건은 `docs/tech-debt.md` #151로 등재(이 스토리가 만든 문제가 아니라 `requireUser()`의 기존 설계 — `deferred-work.md`는 동결 파일이라 project-context.md 지침에 따라 대장(`docs/tech-debt.md`)에 대신 기록).

reject 8건은 이미 intent-contract가 명시적으로 승인한 동작(예: `variant` 기본값 `'consumer'`, 채팅 🔔 아이콘, `nav-links.ts`의 role 파라미터 선설계, buyer가 "내 매물 관리" 클릭 시 `/sell`에서 홈으로 튕기는 기존 `requireRole` 동작 — 이 AC가 "회귀 아님"으로 직접 검증함)이거나, 실제로는 이미 수행됐지만 diff 자체엔 남지 않는 증거(브라우저 수동 검증 — 이 프로젝트의 Vitest 관례가 순수 함수만 단위테스트하고 나머지는 Playwright MCP 세션으로 확인하는 방식이라, 검증이 diff에 파일로 남지 않는 게 정상)였다.

### 2026-07-28 — Review pass (후속 리뷰, 2회차)
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 7: (high 0, medium 2, low 5)
- reject: 11: (high 0, medium 1, low 10)
- addressed_findings:
  - `[medium]` `[patch]` 모바일 햄버거 패널이 헤더 왼쪽 끝이 아니라 로고 뒤에서 시작(실측 390px 뷰포트: 패널 left=117.48 / right=366 vs 헤더 0 / 390). 원인은 `absolute inset-x-0`의 포지션 기준이 로고 뒤에서 시작하는 `SiteNav` 루트 div였던 것 — `relative`를 `AppHeader`의 `<header>`로 옮겨 해결. 패치 후 재측정 left=0 / right=390으로 헤더 전폭 일치 확인(D5 레이아웃 어긋남 금기).
  - `[medium]` `[patch]` admin/consumer 분기를 지키는 자동 검사가 하나도 없어 `variant="admin"` 한 줄이 지워져도 lint·tsc·vitest·build가 전부 green(= 관리자 콘솔에 소비자 내비가 새도 아무도 못 잡음) — `AppHeader.test.ts` 신규(레포 선례 `ListingCard.test.ts` 함수 호출 방식 + `viewCountCallSite.test.ts` 소스 스캔). 일부러 깨서 red 1건 확인 → 되돌려 green 219/219 확인(B9·B4).
  - `[medium]` `[patch]` `/account`가 `.single()`이라 `profiles` 행이 없으면(PGRST116) 카드 전체가 에러로 대체돼, DB를 거치지 않는 `user.email`까지 함께 가려짐 — 이 페이지의 목적("어느 계정으로 로그인했나")이 무너진다. `.maybeSingle()` + `<dl>` 상시 렌더 + 진짜 에러만 배너로 얹는 구조로 수정.
  - `[low]` `[patch]` 760px를 넘겨도 `menuOpen`이 살아남아(실측: 390px에서 열고 1280px로 리사이즈 시 패널이 DOM에 잔류·`aria-expanded="true"` 유지, 다시 390px로 줄이면 클릭 없이 되살아남) — `matchMedia('(min-width: 760px)')` 리스너로 닫는다. 패치 후 왕복 리사이즈 시 패널 DOM 제거·`aria-expanded="false"` 확인.
  - `[low]` `[patch]` 트리거가 `aria-haspopup="menu"`인데 1차 리뷰가 `role="menu"`를 제거해, 보조기술에 WAI-ARIA 메뉴 패턴(방향키·Home/End)을 약속하고 안 지키는 모순 — `aria-haspopup="true"`로 정합화(규약 자체의 재판단은 대장 #154).
  - `[low]` `[patch]` `AppHeader` admin 분기 주석이 "기존 admin 렌더 경로 그대로 보존"이라 적었지만 실제로는 이전 헤더의 찜(`/wishlist`) 링크가 빠져 있음 — intent가 admin 헤더를 "역할라벨·이메일·로그아웃"으로 한정했으므로 **의도된 것**이라, 코드가 아니라 주석을 사실대로 수정.

**측정으로 기각된 주장 2건**(리뷰어 지적을 논증이 아니라 실측으로 갈랐다 — B4): (1) "로그인 헤더가 360px에서 가로로 넘친다" → **거짓**. 320~1280px 전 구간에서 `header`·내부 행의 `scrollWidth`가 뷰포트와 정확히 일치했다. 다만 같은 측정에서 `/search` **문서 전체**가 ≤376px에서 가로 스크롤을 만드는 것을 발견했는데, 로그인/비로그인 수치가 동일해 이 스토리와 무관한 본문 문제라 대장 #155로 이관. (2) "760px를 넘으면 숨겨진 `FocusTrap`이 포커스 블랙홀이 된다" → **거짓**. 리사이즈 후 `document.activeElement`가 `<body>`로 풀리고 Tab이 정상 순회했다(`display:none` 요소의 `focus()`는 no-op이라 포커스를 뺏지 못한다). 남은 실체는 "상태가 살아남아 되살아난다"뿐이라 low로 재산정해 패치했다.

defer 7건은 전부 `docs/tech-debt.md`에 신규 #152~#158로 등재했다(`deferred-work.md`는 동결 파일 — project-context.md 지침). 이번 실행 지시가 **기존 대장 항목의 수정·재개방을 금지**했으므로, 트리거가 소진된 #125조차 직접 닫지 않고 #158(신규)로만 남겼다.

reject 11건은 intent-contract가 이미 명시적으로 승인한 동작(buyer의 `/sell` 리다이렉트 — AC가 "회귀 아님"으로 직접 검증 / `nav-links.ts`의 role 선설계 / `variant` 기본값 / admin 예외의 `(admin)` 레이아웃 한정)이거나, 위 실측으로 거짓이 확인된 2건이거나, 프로젝트 규칙상 손댈 수 없는 것(동결 파일 `deferred-work.md`의 DW-1·DW-2)이다.

### 2026-07-28 — Review pass (후속 리뷰, 3회차)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 5, low 6)
- defer: 5: (high 0, medium 2, low 3)
- reject: 12: (high 0, medium 2, low 10)
- addressed_findings:
  - `[medium]` `[patch]` `AppHeader.test.ts`의 소스 스캔 정규식 `[^>]*`가 첫 `>`에서 잘려, prop에 `>`가 들어간 호출부(화살표 함수 등)에서는 **정상 코드인데 실패**하고 `variant={'admin'}` 표기는 **못 본다** — 비탐욕 `/>` 매칭 + 세 표기를 모두 받는 값 정규식으로 교체.
  - `[medium]` `[patch]` `AppHeader.test.ts`의 admin 테스트가 `LogoutButton` 존재를 단언하지 않아, 그 한 줄을 지워도 lint·tsc·vitest가 전부 green(리뷰어가 실제로 삭제해 확인). 관리자는 홈으로 가면 `/admin`으로 되돌려져 소비자 헤더의 로그아웃에 **영원히 못 닿으므로** 로그아웃 수단이 통째로 사라진다 — 존재 단언 추가.
  - `[medium]` `[patch]` 같은 소스 스캔이 **단방향**이었다(admin 호출부가 `variant="admin"`을 가졌나만 확인). 소비자 페이지에 `variant="admin"`이 붙으면 이 스토리 산출물 전체가 그 화면에서 사라지는데 아무것도 안 잡았다(리뷰어가 `search/page.tsx`에 주입해 green 확인) — 역방향 스캔 추가.
  - `[medium]` `[patch]` `SiteNav`의 렌더 계약에 검사가 0건 — `loginHref`를 상수 `'/login'`으로 되돌려도(로그인 후 원위치 복귀가 깨짐) 전부 green. `react-dom`이 이미 의존성이고 현행 node 환경 vitest에서 `renderToStaticMarkup`이 동작함을 확인해 `SiteNav.test.ts` 신설(비로그인 `redirectedFrom`·`currentPath` 미전달 시 순수 `/login`·로그인 시 찜/채팅/프로필 노출).
  - `[medium]` `[patch]` 2차 리뷰가 등재한 `#152`가 **스스로 지정한 자리에 안 심겼다** — 항목 본문이 "Story 11.3 인수조건으로 심는다, 대장에만 적으면 조용히 또 밀린다"고 적었는데 `epics-increment-2026-07-12.md`의 11.3 절은 무변경이었다(B5 위반). 11.3에 해당 인수조건을 실제로 심었다.
  - `[low]` `[patch]` 760px·44×44는 intent가 근거까지 달아 못박은 실측치인데 코드에 문자열로만 존재해 750px로 바꿔도 전부 green — `SiteNav.test.ts`에 값 고정 소스 스캔 추가(`min-[Npx]:` 전량이 760인지 대조).
  - `[low]` `[patch]` `proxy.ts`의 `PROTECTED_PREFIXES`에서 `/account`를 지워도 아무것도 안 잡음(2차 게이트가 살아 데이터는 안 새지만 로그인 후 복귀가 깨짐) — `proxy.test.ts` 신설(6개 경로 멤버십 소스 스캔).
  - `[low]` `[patch]` `vitest.config.ts` 주석이 "컴포넌트를 여기서 테스트하지 않는다"인데 2차 리뷰가 그 아래에 컴포넌트 테스트를 넣었다(이 스토리가 `#154`·`#156`에서 스스로 지적한 "규약과 코드가 갈림"과 같은 형태) — 실제 경계(jsdom·RTL 없이 직접 호출·`renderToStaticMarkup`·소스 스캔)를 적도록 주석 정정.
  - `[low]` `[patch]` 신규 `/account`가 consumer 헤더에 **쓰이지 않는** `roleLabel` prop을 넘김(`#153`이 진단한 패턴의 7번째 사례인데, 신규 파일이라 기존 8개 호출부 시그니처 동결과 무관) — prop 제거(본문 `<dd>`의 표시는 유지).
  - `[low]` `[patch]` `AppHeader` admin 분기 주석의 "기존 admin 렌더 경로 그대로 보존"이 아직 부정확 — 옛 헤더가 `email` 없을 때 보여주던 로그인 링크 폴백이 사라졌고 `currentPath`도 이 분기에서 안 쓰인다. 둘 다 옳은 상태이므로(`requireAdmin()`이 세션을 보장 → 로그인 링크는 도달 불가 코드) 코드가 아니라 주석을 사실대로 정정.
  - `[low]` `[patch]` outside-click 핸들러가 `handlePointerDown`이라는 이름으로 `mousedown`만 듣고 있었다 — 이름/동작 불일치이면서, 이 패널은 `<760px` **모바일 전용** UI인데 마우스 전용 이벤트에 매달려 있었다. `pointerdown`(마우스·터치·펜 공통, `mousedown`보다 먼저 발화해 기존 순서 논리 유지)으로 통일.

**측정으로 기각된 주장 2건**(논증이 아니라 실측으로 갈랐다 — B4): (1) "바깥 클릭으로 닫을 때 `FocusTrap`의 `focusin`이 사용자가 방금 누른 요소에서 포커스를 빼앗는다" → **거짓**. 패널을 연 뒤 본문 버튼을 실제로 클릭하니 `document.activeElement`가 **그 버튼**이었다(`activeInHeader: false`). (2) "상호배타로 패널을 바꿔 열면 새 트랩이 **다른 패널의 트리거**를 자기 트리거로 캡처해 Esc 시 엉뚱한 버튼으로 복귀한다" → **거짓**. 프로필▾을 연 상태에서 햄버거를 열고 Esc를 누르니 포커스가 `메뉴 열기`(= 올바른 트리거)로 돌아왔다.

**`#158`이 요구한 미이행 측정을 이번에 수행했다**(대장 항목 자체는 지시에 따라 손대지 않음): 실브라우저에서 헤더 로고 배지("차")의 `getComputedStyle(...).fontWeight` = **`"800"`**, `font-family`가 `pretendard`로 해석되고 `document.fonts.check('800 16px pretendard')` = **`true`**(self-host된 800 웨이트가 실제로 로드됨). 워드마크("차장님")는 `Logo.tsx`가 지정한 대로 700이다. 즉 `#125`가 요구한 "800 weight 렌더 실경로 확인"은 **충족됐다** — 남은 것은 `#125`를 닫는 장부 정리뿐이고, 그 종결은 오케스트레이터 소관이다.

defer 5건은 전부 `docs/tech-debt.md`에 신규 **#159~#163**으로 등재했다(`deferred-work.md`는 동결 파일 — project-context.md 지침). 이번에도 **기존 대장 항목의 수정·재개방은 하지 않았다.** 그리고 이번 패스는 defer를 적는 데서 멈추지 않고 **"고칠 자리"에 실제로 심었다**(B5) — `#152`는 Story 11.3 인수조건으로, `#160`은 Story 11.5 인수조건으로.

reject 12건: intent-contract가 명시적으로 승인·지정한 것(`nav-links.ts`의 role 선설계 / 이모지 ♡·🔔 / 데스크톱·모바일 모두에 나오는 "내 차 팔기"+"내 차 등록" 병존 / 비로그인이 `/ai`·`/sell`을 눌러 로그인 게이트를 만나는 흐름 — 11.3 AC 개정의 "시도 전에 거절하지 않는다" 원칙과 오히려 일치), 실측·스키마로 성립하지 않는 것(위 2건 + `ROLE_LABEL` 폴백 — DB가 `check (role in ('buyer','seller','admin'))`로 미지 값을 원천 차단 + 760px 리사이즈 시 포커스가 `<body>`로 가는 것은 2차 리뷰가 이미 "Tab 정상 순회"로 판정한 사실), 되살리면 도달 불가 코드가 되는 것(admin 분기의 로그인 링크 폴백 — `requireAdmin()`이 세션 보장, A2), 그리고 코스메틱(`aria-label` 상태 이중 인코딩·`aria-controls` 부재 — 1차 리뷰가 의도적으로 정한 형태 / 헤더 `max-w-6xl` vs `/account` `max-w-2xl`)이다.

## Auto Run Result

**요약:** Epic 11 이전 임시 최소 헤더를 로그인 상태별 소비자 내비(로고·내 차 사기·AI로 찾기·내 차 팔기 | 비로그인=로그인·내 차 등록 / 로그인=찜♡·채팅🔔·프로필▾)로 재구성했다. 모바일 햄버거(<760px)·프로필 드롭다운을 신설했고, 관리자 페이지는 `variant="admin"`으로 분기해 기존 최소 헤더를 그대로 보존했다. 프로필▾ → "내 정보"가 가리킬 읽기전용 계정 페이지(`/account`)도 신규 작성했다.

**파일 변경:**
- `web/src/components/layout/nav-links.ts` (신규) -- role-aware 확장 지점 순수 함수, 현재는 role 무관 동일 3개 링크 반환.
- `web/src/components/layout/nav-links.test.ts` (신규) -- 위 함수 단위테스트.
- `web/src/components/layout/SiteNav.tsx` (신규) -- 데스크톱 내비·모바일 햄버거·프로필▾ 드롭다운 본체.
- `web/src/components/layout/AppHeader.tsx` (수정) -- `Logo`를 홈 링크로 배선, `variant` prop으로 admin/consumer 분기.
- `web/src/app/(admin)/layout.tsx` (수정, 1줄) -- `variant="admin"` 전달.
- `web/src/app/(user)/account/page.tsx` (신규) -- "내 정보" 읽기전용 페이지.
- `web/src/proxy.ts` (수정) -- `PROTECTED_PREFIXES`에 `/account` 추가.
- `docs/tech-debt.md` (수정) -- #148·#149(DW-1/DW-2 이관)·#150("내 정보" 편집 defer)·#151(코드리뷰가 찾은 `requireUser()` redirectedFrom 비대칭 defer) 추가.

**리뷰 결과:** blind-hunter(adversarial)·edge-case-hunter·verification-gap·intent-alignment 4개 레이어를 병렬 실행, 총 22건 원시 지적 → 중복 제거 후 18건 고유 판정 → patch 9(high 1·medium 2·low 6, 전부 구현 서브에이전트에 위임해 수정 완료)·defer 1(low, `docs/tech-debt.md` #151)·reject 8(intent-contract가 이미 명시적으로 승인했거나, 이 프로젝트 관례상 diff에 안 남는 이미 수행된 브라우저 검증). 상세는 위 Review Triage Log 참고.

**검증:** `npm run lint`(0경고)·`npx tsc --noEmit`(0에러)·`npx vitest run`(216/216 통과)·`npm run build`(성공, `/account` 라우트 포함) 전부 오케스트레이터가 패치 적용 전후 두 차례 직접 재실행해 확인. Playwright MCP + 로컬 Supabase로 비로그인/구매자/판매자/관리자 4가지 상태의 데스크톱·모바일(700px) 렌더, 프로필▾·햄버거의 열기/닫기(토글·바깥클릭·Esc)·상호배타·포커스 복귀, `/account` 로그인·비로그인 접근, buyer의 "내 차 팔기" 기존 리다이렉트 회귀 여부를 전부 실측 확인(구현 서브에이전트가 최초 구현 시 1회 + 패치 적용 후 1회, 총 2회 수행).

**잔여 리스크:**
- `SiteNav.tsx`의 프로필▾가 <760px에서 햄버거 패널 안으로 접히지 않고 항상 노출되는 배치는 intent-contract의 I/O 매트릭스가 명시하지 않은 해석이다(모바일 행은 "찜·채팅 아이콘 상시 노출"만 언급, 프로필▾ 위치는 안 다룸). 실제 확인 결과 동작엔 문제없으나(상호배타로 햄버거와 안 겹침), 차후 매트릭스에 이 행을 보강할 여지가 있다.
- reject된 8건 중 "admin이 URL로 `/account`에 직접 접근하면 소비자용 내비가 뜬다"는 항목은 실제 도달 경로(관리자 헤더에 `/account` 링크 없음)가 없어 극히 낮은 우선순위로 reject했으나, 완전히 불가능한 경로는 아니다.

**잔존 아티팩트(이 스토리 범위 밖, 커밋 안 함):**
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` — 세션 시작 전부터 이미 staged 상태였던, Story 11.4/11.5에 대장(#134·#144) 이월 인수조건을 추가한 변경. 이 스토리(11-2)와 무관해 건드리지 않았고, 커밋에도 포함하지 않았다 — 원래 staged 상태 그대로 남아 있다.

---

### 2026-07-28 후속 리뷰(2회차) 결과

**무엇을 했나:** `status: done`으로 종료됐던 11-2를 새 세션에서 다시 리뷰했다(B4 — 작업한 세션이 자기 작업을 보면 같은 사각지대를 갖는다). 4개 레이어(adversarial·edge-case·verification-gap·intent-alignment) 병렬 실행 → 원시 지적 34건 → 중복 제거·독립 판정 24건 → patch 6 / defer 7 / reject 11.

**추가 변경 파일:**
- `web/src/components/layout/AppHeader.tsx` — `<header>`에 `relative` 추가(모바일 패널 포지션 기준 이동) · admin 분기 주석을 사실대로 정정(찜 링크 부재는 의도).
- `web/src/components/layout/SiteNav.tsx` — 루트 div에서 `relative` 제거 · 760px 이상 리사이즈 시 햄버거 닫는 `matchMedia` 효과 추가 · `aria-haspopup` `"menu"`→`"true"`.
- `web/src/app/(user)/account/page.tsx` — `.single()`→`.maybeSingle()`, `<dl>` 상시 렌더(이메일은 에러여도 노출), 에러는 배너로 분리.
- `web/src/components/layout/AppHeader.test.ts` (신규) — admin/consumer 분기 불변식 3건(consumer=SiteNav+Logo 렌더 및 prop 전달 / admin=둘 다 미렌더 / `(admin)` 아래 호출부 전수 `variant="admin"` 소스 스캔). 파일 상단에 **이 검사가 안 보는 것**을 명시(실제 브라우저 렌더·CSS는 E2E 몫).
- `docs/tech-debt.md` — #152~#158 신규 7건.

**검증(전부 오케스트레이터가 직접 재실행):** `npm run lint` 0경고 · `npx tsc --noEmit` 0에러 · `npx vitest run` **219/219 green**(신규 3건 포함, 216→219) · `npm run build` 성공(`/account` 라우트 생성 확인). **신규 검사 red/green 확인:** `(admin)/layout.tsx`에서 `variant="admin"`을 일부러 지워 `vitest`가 **1 failed**로 떨어지는 것 확인 → 되돌려 219/219 green 복귀 확인("만들었다"가 아니라 "잡는다"가 완료 — B4).
**브라우저 실측(로컬 Supabase + dev 서버, Playwright MCP, 시드 판매자 계정):** 패치 전 측정으로 패널 위치 어긋남(left 117.48)·760px 잔류 상태·헤더 미넘침·아이콘 44×44를 확인했고, 패치 후 재측정에서 패널 전폭 일치(left 0 / right 390), 프로필 드롭다운 우측 정렬 무회귀(dropdown.right = trigger.right = 1192, 폭 176), 760px 왕복 후 패널 닫힘, Esc·바깥클릭·상호배타 정상, `/account` 로그인 시 이메일·역할·이름 표시 및 비로그인 시 `/login?redirectedFrom=%2Faccount` 리다이렉트를 확인했다.

**후속 리뷰 권장:** `true`. 근거 — 이번 패스에서 patch로 처리한 지적은 high 0 · medium 3 · low 3이고, 산식 `3 × medium + 1 × low = 3×3 + 3 = 12`로 기준값 5를 넘는다.

**잔여 리스크:**
- 신규 `AppHeader.test.ts`는 **엘리먼트 트리와 소스 텍스트**만 본다. 실제 브라우저에서 관리자 콘솔에 소비자 내비가 안 보이는지(CSS·레이아웃)는 여전히 E2E 몫이고, 이 레포엔 커밋된 Playwright 스위트가 없다(브라우저 검증은 매번 수동 MCP 세션). 즉 **회귀 방지선은 prop 경로 한 겹뿐**이다.
- `/search`의 ≤376px 가로 스크롤(#155)은 이 스토리가 원인이 아님을 실측으로 갈랐지만, **아직 열려 있는 D5 위반**이다. 320~360px는 실기기 폭이라 체감 가능한 결함이다.
- 드롭다운·모달 ARIA가 사용자 확정 규약(대장 790행)과 어긋난 채 남았다(#154). 키보드 조작은 정상이나 규약을 지킬지 완화할지는 사람이 정해야 한다 — 다음 `FocusTrap` 소비 스토리에서 먼저 물어야 한다.
- 비로그인 홈(`/`)에는 신규 내비가 여전히 안 보인다(#152). AC1의 문면과 어긋나는 상태이며, **Story 11.3의 인수조건으로 심지 않으면 조용히 또 밀린다**(B5).

**잔존 아티팩트(이 스토리 범위 밖, 커밋 안 함):**
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` — 이 세션 시작 전부터 staged 상태였던 무관한 변경. 그대로 둔다.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 세션 시작 전부터 modified 상태. 그대로 둔다.

---

### 2026-07-28 후속 리뷰(3회차) 결과

**무엇을 했나:** `status: done`이던 11-2를 다시 새 세션에서 리뷰했다. 4개 레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행 → 원시 지적 32건 → 중복 제거·독립 판정 **28건** → patch 11 / defer 5 / reject 12.

이번 패스의 성격이 앞선 두 패스와 다르다. **verification-gap 레이어가 주장이 아니라 실험으로 말했다** — 코드를 실제로 깨뜨리고 `lint`·`tsc`·`vitest`·`build`를 돌려 **전부 green인 것을 확인한 뒤 원복**하는 방식으로 회귀 구멍 5개를 실증했다. 그래서 이번 patch의 절반 이상이 "기능 버그 수정"이 아니라 **"이미 있는 기능을 지키는 검사 세우기"**다(B9 — 규칙은 어길 수 없는 자리에 박는다).

**추가 변경 파일:**
- `web/src/components/layout/AppHeader.test.ts` — 소스 스캔 정규식을 속성 문법 인식형으로 교체(`>` 포함 prop에서 잘리던 것·`variant={'admin'}`을 놓치던 것) · admin 분기의 `LogoutButton` 존재 단언 추가 · `(admin)` **밖** 호출부에 `variant="admin"`이 붙지 않았는지 보는 역방향 스캔 추가.
- `web/src/components/layout/SiteNav.test.ts` (신규) — `renderToStaticMarkup` 기반 렌더 계약 검사(비로그인 `redirectedFrom` 조립 / `currentPath` 없을 때 순수 `/login` / 로그인 시 찜·채팅·프로필 노출) + 760px·44×44 값 고정 소스 스캔. 파일 상단에 **이 검사가 안 보는 것**을 명시(`useEffect`는 SSR에서 안 돌므로 클릭·키보드·리사이즈 층은 E2E 몫 — `#160`).
- `web/src/proxy.test.ts` (신규) — `PROTECTED_PREFIXES` 6개 경로 멤버십 소스 스캔(`/account` 포함).
- `web/vitest.config.ts` — 실제 테스트 경계를 적도록 주석 정정(값 변경 없음).
- `web/src/components/layout/SiteNav.tsx` — outside-click을 `mousedown` → **`pointerdown`**(모바일 전용 UI인데 마우스 전용 이벤트에 매달려 있었고, 핸들러 이름과도 어긋났다).
- `web/src/components/layout/AppHeader.tsx` — admin 분기 주석 정정(로그인 링크 폴백 부재·`currentPath` 미사용이 의도임을 명시).
- `web/src/app/(user)/account/page.tsx` — 소비처 없는 `roleLabel` prop 전달 제거.
- `docs/tech-debt.md` — 신규 **#159~#163** 5건.
- `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md` — **`#152` → Story 11.3 인수조건**, **`#160` → Story 11.5 인수조건**으로 심음(B5). ⚠️ 이 파일은 세션 시작 전부터 남의 staged 변경이 얹혀 있어 **커밋하지 않았다**(아래 잔존 아티팩트 참조).

**검증(전부 오케스트레이터가 직접 재실행):** `npm run lint` 0경고 · `npx tsc --noEmit` 0에러 · `npx vitest run` **225/225 green**(219→225, 신규 6건) · `npm run build` 성공(`/account` 포함 20개 라우트 생성).
**신규 검사 red/green 확인(5건 전부 — "만들었다"가 아니라 "잡는다"가 완료, B4):** ① admin 분기의 `<LogoutButton />` 삭제 → red ② `search/page.tsx`에 `variant="admin"` 주입 → red ③ `loginHref`를 상수 `'/login'`으로 → red ④ `min-[760px]:` 하나를 `min-[750px]:`로 → red ⑤ `PROTECTED_PREFIXES`에서 `'/account'` 제거 → red. 다섯 건 모두 원복 후 green 복귀 확인. (④는 첫 시도에서 **통과해버렸다** — "760이 3개 이상"이라는 느슨한 단언이 4개 중 3개만 남은 상태를 구분 못 했다. `min-[Npx]:` 전량과 `min-[760px]:` 개수를 대조하도록 고쳐 다시 red를 받았다.)
**브라우저 실측(로컬 Supabase + dev 서버, Playwright MCP, 시드 판매자 계정):** `pointerdown` 전환 후에도 바깥클릭 닫힘 정상(클릭한 요소에 포커스가 남는 것까지 확인) · Esc 닫힘 + 트리거 포커스 복귀 · 트리거 재클릭 토글 · 390px↔1280px 왕복 시 패널 제거 및 미부활 · 프로필▾ ↔ 햄버거 상호배타(Esc 후 올바른 트리거로 복귀) · 데스크톱 1280px 로그인 헤더 구성(로고·3링크·찜·채팅·프로필▾, 햄버거 없음, `scrollWidth` 1280 = 뷰포트) · `/account` 렌더(이메일·역할·이름 실값, `roleLabel` prop 제거 후 회귀 없음) · 비로그인 `/account` → `307 /login?redirectedFrom=%2Faccount` · 로고 배지 `fontWeight` **800** + `pretendard` 실제 로드(`#158` 요구 측정).

**대장 점검(workflow persistent fact 이행):** `deferred-work.md`의 `status: open` 항목은 여전히 `DW-1`·`DW-2` 2건뿐이고 신규 항목은 없다. **`DW-1`: 이미 #148에 있음 · `DW-2`: 이미 #149에 있음** — 둘 다 이 스토리 1차 실행에서 이관 완료돼 추가 조치 없음(동결 파일은 손대지 않았다).

**후속 리뷰 권장:** `true`. 근거 — 이번 패스에서 patch로 처리한 지적은 high 0 · medium 5 · low 6이고, 산식 `3 × medium + 1 × low = 3×5 + 6 = 21`로 기준값 5를 넘는다. 다만 성격은 앞선 패스와 다르다 — **이번 medium 5건 중 4건이 "기능 결함"이 아니라 "검사 부재"**였고 그 4건은 이번에 닫혔다. 남은 위험은 아래 잔여 리스크의 E2E 공백 한 곳으로 수렴한다.

**잔여 리스크:**
- **상호작용 층은 여전히 자동 검사가 없다(`#160`).** 이번에 세운 `SiteNav.test.ts`는 SSR 렌더 계약까지만 고정한다 — 클릭·Esc·리사이즈·상호배타는 `useEffect` 안에 있고 SSR에서 실행되지 않으므로 구조적으로 닿지 않는다. 이 스토리가 실측으로 **네 번** 잡아 고친 결함들이 바로 그 층에 있다. Story 11.5 인수조건으로 심어 뒀다.
- **buyer·admin에게 `/sell` 진입점 3개가 그대로 보이고 누르면 말없이 홈으로 튕긴다(`#159`).** intent가 명시적으로 범위 밖으로 밀어 둔 승계 동작이지만, `nav-ia-rules.md` §2("내 매물 등록·관리는 판매자 전용")와는 어긋난 상태다. Epic 14가 `role`을 헤더까지 스레딩할 때 `#153`과 한 자리에서 답해야 한다.
- **비로그인 홈(`/`)에는 여전히 새 내비가 없다(`#152`).** AC1의 문면과 어긋난 상태 그대로다. 다만 이번에 **Story 11.3 인수조건으로 실제로 심었으므로** 대장에만 적혀 조용히 밀릴 위험은 제거됐다.
- **드롭다운·모달 ARIA가 사용자 확정 규약과 어긋난 채 남았다(`#154`).** 이번 리뷰도 같은 지점을 다시 지적했으나(상태를 `aria-label`에 넣는 것·`aria-controls` 부재), 규약을 지킬지 완화할지는 사람이 정할 문제라 손대지 않았다. `FocusTrap`을 쓰는 다음 스토리에서 **먼저 물어야 한다**.

**잔존 아티팩트(이 스토리 범위 밖 — 커밋하지 않음):**
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 세션 시작 전부터 modified 상태. 손대지 않았다.

**⚠️ 앞선 두 패스와 달라진 것 — `epics-increment-2026-07-12.md`가 이번엔 커밋됐다:**
이 파일은 세션 시작 전부터 **이전 스토리(11-1) 리뷰의 심기**(Story 11.4에 `#134`·`#144` 이월 인수조건 추가)가 **staged 상태로** 얹혀 있었고, 1·2차 패스는 이를 잔존 아티팩트로 남겼다. 이번 패스는 같은 파일의 Story 11.3·11.5 절에 `#152`·`#160`을 심어야 했는데, 파일이 이미 staged라 커밋 시 이전 심기까지 함께 실렸다. **되돌리지 않았다** — 실린 내용이 같은 성격의 정당한 B5 심기이고, 계속 미커밋으로 두는 것 자체가 "심었는데 유실되는" 실패 모드이기 때문이다. 커밋 메시지에 그 사실을 명시했다.
