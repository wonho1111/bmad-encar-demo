---
title: '반응형 뷰포트 E2E 감사 (SM-B)'
type: 'feature'
created: '2026-07-28'
status: 'done'
baseline_revision: 'd0ab82f46d590457b6c94e7802289aaad902b98c'
final_revision: '4034be2fe52c4fc271358be7301f56990b7f7959'
review_loop_iteration: 0
followup_review_recommended: true # patch findings this pass: medium 5, low 4 → 3×5+1×4=19 (≥5) → true
context: ['_bmad-output/implementation-artifacts/epic-11-context.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 랜딩(`/`)·목록(`/search`)·상세(`/listings/[id]`)·`/ai`가 완성됐지만, 반응형 회귀(FR36/D5)를 자동으로 잡는 장치가 전혀 없다(레포 전체 Playwright 스펙 0건). 같은 검증 공백 아래 이월된 결함·부채도 있다: `/ai`가 390px에서 가로로 넘친다(#84, 원인 규명됨·미검증 수정안 있음), 이미지 전면 장애 폴백이 목록에서만 실측됐다(#73), 그 실측이 재실행 불가능하다(#86), 내비 상호작용 4가지에 회귀검사가 없다(#160), 폰트 self-host 회귀를 잡는 검사가 없다(#127).
**Approach:** `web/`에 Playwright(E2E)를 처음 도입해 데스크톱(1280×800)·태블릿(800×1024)·모바일(390×844) 3뷰포트로 4개 화면의 그리드 재배치·레이아웃 무결성을 단언하고, 같은 층에서 위 5개 이월 항목을 각각의 스펙으로 닫는다. `#84`는 코드 수정 1줄(`min-w-0`) 후 실측 검증까지 이 스토리가 포함한다. `#127`은 브라우저가 필요 없으므로 vitest 유닛 테스트로 처리한다(대장 원문이 명시).

## Boundaries & Constraints

**Always:**
- 뷰포트 매트릭스는 정확히 데스크톱 1280×800 · 태블릿 800×1024 · 모바일 390×844를 쓴다(9.6/9.7/#84가 이미 실측에 쓴 값과 동일 — 연속성).
- 새 Playwright 스펙은 전부 `web/e2e/`에 두고 `web/package.json`에 `test:e2e` 스크립트로 로컬에서 재실행 가능해야 한다(#86 — "재실행 가능한 형태"의 실체는 커밋된 자동화 스펙 자체다. 과거 스크린샷 파일을 정적으로 커밋하는 것이 아니다 — 다시 돌리면 같은 증거가 재생산된다).
- `#127`(폰트 CDN 재유입·자산 비대) 검사는 브라우저 없이 `web/src/app/layout.tsx` 소스 문자열 + `web/src/app/fonts/` 총 용량만 확인하는 vitest 유닛 테스트로 만든다(대장 원문이 "vitest 한 건"이라 명시했고, 브라우저가 필요 없는 정적 검사다).
- 이미지 전면 장애 재현(#73)은 목록(`/search`)·상세(`/listings/[id]`)·`/ai` 세 소비처 모두에서 반복한다. `loading="lazy"` 때문에 화면 밖 카드는 요청 자체가 안 나가므로, 전량을 뷰포트에 넣도록 스크롤하거나 lazy를 우회한 뒤 단언한다.
- `#160`의 내비 검사는 대장 원문이 지정한 4개 시나리오를 그대로 심는다: (a) 390px 햄버거 열기→바깥클릭 닫힘, (b) Esc 닫힘+포커스가 트리거로 복귀, (c) 프로필▾ 연 상태에서 햄버거 열면 프로필 닫힘(상호배타), (d) 390px에서 열고 1280px로 리사이즈하면 패널이 DOM에서 사라지고 `aria-expanded="false"`.
- 이 스토리가 닫는 이월 항목(#73·#86·#127·#160·#84)은 각각 `docs/tech-debt.md`에 **날짜 붙은 ✅ 해소 라인**으로 갱신한다(B8 — 끝난 일은 대장을 닫는다). 동결 파일 `deferred-work.md`는 절대 건드리지 않는다.
- 착수 시 `deferred-work.md`의 `status: open` 항목을 확인한다(workflow persistent fact).

**Block If:** 로컬 Playwright 브라우저 설치(`npx playwright install chromium`)가 이 샌드박스에서 실행 불가능하고 대체 수단(기존 `~/.cache/ms-playwright`의 캐시된 chromium 재사용)도 실패하면 — E2E 스펙을 실행해 검증할 방법이 없다는 뜻이므로 HALT하고 상태를 보고한다. (사전 조사에서 캐시된 chromium-1226/1228/1232가 이미 존재하고 npm 레지스트리도 도달 가능함을 확인했으나, 실제 설치·실행은 구현 단계에서 실측한다.)

**Never:**
- `ResponsiveGrid.tsx`·`SiteNav.tsx`·`ListingCardImage.tsx`·`ListingGallery.tsx`의 기존 로직을 리팩터하거나 새로 설계하지 않는다 — 이 스토리는 감사(assert)이지 재설계가 아니다. 유일한 프로덕션 코드 수정은 `ChatAssistant.tsx`의 `#84` 1줄이다.
- CI(`.github/workflows/tests.yml`)에 새 e2e job을 추가하지 않는다 — 로컬 재실행 가능성(#86)까지가 이 스토리의 범위이며, CI 안정화(헤드리스 브라우저 설치·시크릿·로컬 Supabase 기동)는 별도 결정이 필요한 작업이다. `docs/tech-debt.md`에 새 항목으로 이월한다.
- 기존 vitest 단위테스트(`SiteNav.test.ts` 등)를 수정하거나 대체하지 않는다 — 이번 E2E 층은 그 위에 얹는 추가 층이다.
- 히어로·그리드·카드의 시각 디자인(색·간격·타이포)을 바꾸지 않는다 — 감사가 잡는 것은 구조적 붕괴(세로화·줄바꿈 어긋남·2줄 버튼·가로스크롤)이지 미세 조정이 아니다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 그리드 재배치 | `/search`(또는 랜딩 그리드)를 1280/800/390 폭으로 로드 | 카드 그리드가 4열/2열/1열로 재배치, 카드 내부 가로배치(신뢰속성 행 등) 세로화 없음, 버튼 2줄 없음 | 어긋나면 스펙 실패(red) |
| `/ai` 가로 오버플로 | `/ai`를 390×844로 로드(카드 0개·N개 양쪽) | `document.documentElement.scrollWidth <= clientWidth`(가로 스크롤 없음) | 실패 시 `#84` 재발로 스펙 실패 |
| 이미지 전면 장애 | `**/storage/v1/object/public/**` 요청을 abort, 데이터 조회는 살림, 전량 스크롤 | 목록·상세·`/ai` 각각에서 깨진 이미지 아이콘 0개, 플레이스홀더로 전량 대체 | 폴백 미발동 시 실패 |
| 내비 상호작용 4종 | 390px 햄버거 열기/Esc/프로필 동시열기/1280px 리사이즈 | 각 시나리오의 기대 상태(위 Always 항목) | 미충족 시 실패 |
| 폰트 회귀(정적) | `layout.tsx` 소스 + `fonts/` 디렉터리 용량 | 외부 폰트 오리진 문자열 없음, 총 용량 ≤ 2,300,000B(현재 실측 2,057,688B + 약 250KB 회귀 버퍼로 이 스토리가 확정) | 초과/CDN 문자열 발견 시 실패 |

</intent-contract>

## Code Map

- `web/package.json` -- `@playwright/test` devDependency 추가 + `test:e2e` 스크립트 -- E2E 실행 진입점
- `web/playwright.config.ts` (신규) -- 3개 뷰포트 프로젝트(1280×800/800×1024/390×844) + `webServer`(로컬 `next dev` 또는 `next start`, `web/.env.local` 기반 로컬 Supabase 사용) + baseURL
- `web/e2e/viewport-audit.spec.ts` (신규) -- 랜딩·`/search`·상세·`/ai` 4화면 × 3뷰포트 그리드 재배치·가로스크롤 없음 단언(#84 포함)
- `web/e2e/nav-interactions.spec.ts` (신규) -- `#160` 4개 시나리오
- `web/e2e/image-fallback.spec.ts` (신규) -- `#73`/`#86` 세 소비처 이미지 전면 장애 재현
- `web/src/app/fonts.budget.test.ts` (신규, vitest) -- `#127` 외부 폰트 오리진 부재 + 자산 용량 상한 단언
- `web/src/components/ai/ChatAssistant.tsx:207` -- 입력창 `className`에 `min-w-0` 추가 -- `#84` 수정(가설 검증 후 확정)
- `docs/tech-debt.md` -- `#73`·`#86`·`#127`·`#160`·`#84`에 날짜 붙은 ✅ 해소 라인 추가 + CI e2e 미배선을 새 번호로 이월
- `_bmad-output/project-context.md` §12 -- CI가 이제 무엇을 커버하는지(E2E는 로컬 전용, CI는 여전히 lint+vitest뿐) 갱신(#87 트리거 충족)

## Tasks & Acceptance

**Execution:**
- `web/package.json` -- `@playwright/test` 설치 + `test:e2e` 스크립트 추가 -- E2E 실행 인프라 마련
- `npx playwright install chromium` 실행 및 결과 확인 -- 기존 `~/.cache/ms-playwright` 캐시 재사용 여부 실측(Block If 조건 판정)
- `web/playwright.config.ts` -- 3뷰포트 프로젝트 정의 -- 매트릭스를 설정 한 곳에 고정
- `web/e2e/viewport-audit.spec.ts` -- 4화면×3뷰포트 그리드열수·가로스크롤·2줄버튼 단언 -- FR36/D5 감사 본체
- `web/src/components/ai/ChatAssistant.tsx` -- `min-w-0` 추가 -- `#84` 수정(390px 실측으로 확정, 가설이 틀리면 실제로 넘치지 않는 대안을 찾아 수정)
- `web/e2e/nav-interactions.spec.ts` -- `#160` 4개 시나리오 구현 -- 이미 한 번 잡힌 내비 결함의 재발 방지선
- `web/e2e/image-fallback.spec.ts` -- `#73` 이미지 abort 재현(목록·상세·`/ai`, lazy 우회 포함) -- 전면 장애와 "사진 없음"의 구별 가능성 실측 고정
- `web/src/app/fonts.budget.test.ts` -- `#127` 정적 검사(vitest) -- 폰트 CDN 재유입·용량 회귀 방지
- `docs/tech-debt.md` -- `#73`·`#86`·`#127`·`#160`·`#84` 해소 처리 + CI e2e 미배선 신규 이월 항목 등재 -- B8 대장 정리
- `_bmad-output/project-context.md` §12 -- CI/테스트 커버리지 서술 갱신 -- `#87` 해소

**Acceptance Criteria:**
- Given 데스크톱(1280)·태블릿(800)·모바일(390) 3뷰포트, when `web/e2e/viewport-audit.spec.ts`를 실행하면, then 랜딩·`/search`·상세·`/ai` 4화면 모두에서 그리드 열수 재배치(4/2/1)와 가로스크롤 없음이 green이다.
- Given `/ai`를 390×844로 로드, when 카드가 0개인 경우와 N개인 경우 각각 확인하면, then `document.documentElement.scrollWidth <= clientWidth`가 둘 다 참이다(`#84` 재발 없음).
- Given 이미지 스토리지 요청을 abort한 상태, when 목록·상세·`/ai`를 각각 열고 전량 스크롤하면, then 깨진 이미지 아이콘 0개·플레이스홀더 폴백 전량 발동이 세 화면 모두에서 확인된다(`#73`).
- Given 390px에서 햄버거를 연 상태, when 바깥을 클릭/Esc를 누름/프로필을 열음/1280px로 리사이즈하면, then `#160` 4개 시나리오가 각각 명시된 기대 상태(닫힘·포커스 복귀·상호배타·`aria-expanded="false"`)로 green이다.
- Given `web/src/app/layout.tsx`와 `web/src/app/fonts/`, when `fonts.budget.test.ts`(vitest)를 실행하면, then 외부 폰트 오리진 문자열이 없고 총 용량이 정한 상한 이하임이 확인된다(`#127`) — 일부러 임계값을 낮춰 red를 먼저 확인한 뒤 원복해 green을 확인한다(B4).
- Given 이 스토리가 닫는 5개 이월 항목, when `docs/tech-debt.md`를 확인하면, then 각 항목에 날짜 붙은 ✅ 해소 라인과 실측 근거가 남아 있다.

## Spec Change Log

## Review Triage Log

### 2026-07-28 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 0, medium 4, low 8)
- defer: 1: (high 0, medium 1, low 0)
- reject: 3: (high 0, medium 0, low 3)
- addressed_findings:
  - `[low]` `[patch]` `.github/workflows/tests.yml` 헤더 주석 "Playwright 스펙이 레포에 0개다"가 이 스토리로 인해 거짓이 됨 — 갱신
  - `[medium]` `[patch]` 랜딩(`/`) 그리드 감사가 `[role="list"]`의 `.first()`만 확인 — 인기/최신 두 그리드 중 "최신" 그리드는 열 수 검증에서 빠짐(2개 리뷰어 독립 확인) — 섹션별로 스코프해 둘 다 단언하도록 수정
  - `[low]` `[patch]` 그리드 0건(빈 상태)일 때 `assertGridColumns`가 명시적 처리 없이 타임아웃으로 흐름 — 빈 상태를 먼저 확인하는 가드 추가
  - `[medium]` `[patch]` 내비 바깥클릭 테스트가 하드코딩 좌표 `(195,500)`를 클릭 — 실제 매물 카드 링크와 겹칠 위험(2개 리뷰어 독립 확인) — 링크가 없는 안전한 지점을 확인 후 클릭하도록 수정
  - `[low]` `[patch]` 깨진 이미지 검사가 스타일용 클래스 `img.object-cover`를 식별자로 사용 — 리팩터 시 조용히 무력화될 위험 — 더 안정적인 선택자로 교체
  - `[low]` `[patch]` `buildMockListings`의 id 템플릿이 `count>=11`에서 깨짐(미사용 상태지만 무가드) — 패딩 로직 수정
  - `[low]` `[patch]` `loadDotEnvLocal`이 따옴표로 감싼 값을 벗기지 않음 — 벗기는 로직 추가
  - `[low]` `[patch]` `scrollFullPage`가 15회 캡을 넘겨도 "끝까지 스크롤됐는지"를 단언하지 않아 향후 컨텐츠가 늘면 #73이 고치려던 바로 그 지연로딩 공백이 조용히 재발할 수 있음 — 도달 확인 단언 추가
  - `[medium]` `[patch]` 폰트 CDN 가드가 알려진 5개 문자열 블랙리스트 + 속성 순서 의존 정규식이라 우회 가능 — `next/font/local` 사용 여부 + 외부 `<link rel="stylesheet">` 전면 부재를 확인하는 화이트리스트 방식으로 강화
  - `[low]` `[patch]` `docs/tech-debt.md` `#73` 해소 기록이 남은 관측-수단 설계 과제의 구체적 트리거를 명시하지 않음(B8) — 트리거 한 줄 추가
  - `[medium]` `[patch]` D5 내부무결성(세로화·2줄버튼) 검사가 `/`·`/search`에만 적용되고 상세·`/ai`는 페이지 전체 가로스크롤만 확인 — 두 화면에도 핵심 요소 단일행 단언 추가
  - `[low]` `[patch]` Playwright `webServer`가 포트 3000의 기존 프로세스를 신원 확인 없이 재사용(`reuseExistingServer`) — 정확성을 위해 항상 새로 기동하도록 변경
  - `[medium]` `[defer]` `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`가 `#84`와 동일한 원인(내장 `size` 힌트 + `mx-auto` 부모)으로 390px에서 동일하게 가로 오버플로(402px)를 일으킴을 실측 확인(verification-gap 리뷰가 로컬 스택에서 직접 측정) — 이 스토리의 손대지 않은 화면이라 `docs/tech-debt.md` #169로 신규 등재(트리거 포함)
  - `[reject]` 관리자/판매자 헤더 분기(#161)가 이번 내비 E2E에서 커버되지 않음 — `#160`의 범위(소비자용 SiteNav) 밖이라 애초에 대상이 아님
  - `[reject]` `mockAiSearch` 인터셉션 자체를 검증하지 않음 — 인터셉트 실패 시 실제 API 서버가 안 떠 있어 요청이 크게 실패하므로 조용한 통과 위험이 없음
  - `[reject]` `fetchOnSaleListingIdWithPhoto`가 판매완료 상태를 스스로 재검증하지 않음 — RLS(0012)가 on_sale 매물만 노출하도록 이미 강제하는 구조(B9 원칙과 일치, 의도된 설계)

### 2026-07-28 — Review pass (후속 2차 — `status: done` 스펙 재리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 15: (high 0, medium 9, low 6)
- defer: 3: (high 0, medium 1, low 2)
- reject: 12: (high 0, medium 0, low 12)
- addressed_findings:
  - `[medium]` `[patch]` `assertGridColumnsOrEmptyState`가 **매물 조회 실패**를 통과로 쳤다 — 그리드가 없을 때 `/매물이 없습니다|불러오지 못했습니다/` 한 정규식으로 묶어 인정했으므로, `PopularRecentGrid.tsx:41`·`search/page.tsx:199`의 에러 문구가 뜬 상태에서 이 스토리의 핵심 단언(4/2/1 그리드 재배치)이 **아무것도 측정하지 않은 채 green**이었다(3개 레이어가 독립 확인). 에러는 곧장 fail, 진짜 빈 상태만 인정, 둘 다 아니면 "침묵 상태"로 fail로 분리. B4: `fetchSection`을 강제로 `{error:true}`로 만들어 red 확인 후 원복해 green 확인
  - `[medium]` `[patch]` `assertSingleLine`의 오차 허용 `(lineHeight+padding+border)*1.4`가 대수적으로 `padding >= 1.5*lineHeight`인 순간부터 **2줄 렌더도 통과**시켰다 — 정확히 이 함수를 버튼에 재사용하려고 padding을 넣었을 때 생긴 구멍이다(D5 "2줄로 밀리는 버튼 = 금기"가 무력화). 배수는 line-height에만 곱하도록 수정 + 높이 0(미렌더) 통과 차단. B4: padding 40px·line-height 20px인 실제 2줄 렌더(80px)로 red 확인, 1줄 렌더로 green 확인
  - `[medium]` `[patch]` `mockAiSearch`가 `NEXT_PUBLIC_API_BASE_URL`의 끝 슬래시를 정규화하지 않아(`aiSearch.ts:50`은 `replace(/\/+$/,'')`로 지운다) 목업이 실제 요청 URL과 어긋날 수 있고, 가로챘는지 단언하지도 않았다 — 어긋나면 스펙이 **실제 백엔드(과금·비결정)로 흘러간다**. 정규화 + `requestCount()` 핸들 추가, 모든 호출부에서 단언. B4: 정규화를 끄고 끝 슬래시 base를 주어 `requestCount()==0` red 확인, 원복해 green 확인
  - `[medium]` `[patch]` `scrollFullPage`가 `document.body.scrollHeight`와 `window.scrollY+innerHeight`(documentElement 기준)를 섞어 비교해, `min-h-screen` flex 셸에서 **바닥에 닿기 전에 "끝까지 스크롤됨"으로 판정**될 수 있었다 — `loading="lazy"` 사각지대(#73)를 막으려고 만든 헬퍼가 그 사각지대를 스스로 재현하는 구조. 좌표계를 documentElement로 통일 + 높이 안정화까지 요구. B4: body 높이를 작게 위조해 옛 로직이 scrollY 800에서 "바닥"이라 답하는 것을 red로 확인, 새 로직이 scrollY≈2220까지 도달함을 green으로 확인
  - `[medium]` `[patch]` 이미지 전면 장애 실험이 **실제로 일어났는지 증명하지 않았다** — `ListingCardImage`가 실패 시 `<img>`를 언마운트하므로 깨진이미지 검사는 0개 중 0개가 될 수 있고, "사진 준비중" `>0`은 사진 없는 매물만으로도 만족된다. abort 경로가 안 맞으면(스토리지 URL 변경 등) 두 단언 다 green이다. abort 요청 수 카운터 + 사진 요소 존재 확인 추가. B4: abort 패턴을 어긋나게 바꿔 red 확인(옛 두 단언은 그 상태에서도 green임을 함께 재현), 원복해 green 확인
  - `[medium]` `[patch]` `fonts.budget.test.ts`의 용량 합산이 비재귀라 `fonts/<하위폴더>/`의 실제 파일은 세지 않고 폴더 inode(~4096B)만 셌다 — 하위 폴더에 큰 폰트를 넣는 것만으로 예산을 통째로 우회할 수 있었다. 재귀 순회로 수정. B4: `fonts/subdir/`에 3MB 파일을 심어 red(실제 5.2MB 보고) 확인 후 제거해 green 확인
  - `[medium]` `[patch]` `nav-interactions`·`image-fallback` 스펙이 프로젝트명을 하드코딩 문자열로 비교해 스킵 여부를 정했다 — `playwright.config.ts`에서 프로젝트 이름을 바꾸면 **7개 테스트가 전부 조용히 스킵되고 exit 0**이다(#160·#73·#86 회귀 방지선이 통째로 사라짐). 공용 `PROJECT_NAMES` 상수로 묶어 이름 변경이 조용히 넘어가지 않게 수정
  - `[medium]` `[patch]` `playwright.config.ts`의 포트가 3000 고정 + `reuseExistingServer:false`라 **3000이 점유된 흔한 상태에서 스위트 자체가 못 돈다**(이 프로젝트는 실제로 3020으로 밀린 이력이 있다) — `#86`이 닫은 "다시 돌릴 수 있음"이라는 주장을 정면으로 깨는 조건. `E2E_PORT` 환경변수로 재정의 가능하게 하고 `next start -p`까지 전달
  - `[medium]` `[patch]` D5 단일행 단언 3곳이 `if (await locator.count())`로 감싸여 있어 **0건 매칭이 곧 조용한 스킵**이었다 — 게다가 선택자가 `p.truncate.whitespace-nowrap`이라 검사 대상인 `whitespace-nowrap`을 지우는 회귀가 검사 자체를 함께 지운다. 같은 diff가 이미지에는 `data-testid`로 이 함정을 없앴는데 여기만 남아 있었다. `ListingCard.tsx`·`InquiryCta.tsx`에 동작 무관 `data-testid` 훅 추가 + 없으면 fail로 전환. B4: `data-testid`를 지워 red 확인 후 원복해 green 확인
  - `[low]` `[patch]` `fetchOnSaleListingIdWithPhoto`가 정렬 없는 `limit=1`이라 실행마다 다른 매물을 감사할 수 있어 실패가 재현되지 않았다 — `order=listing_id.asc` 고정
  - `[low]` `[patch]` `assertNoHorizontalOverflow` 주석이 `#155`도 잡는다고 적었으나, `#155`는 폭 ≤376px에서만 나타나고 이 매트릭스의 최소 폭이 390px이라 **구조적으로 관측 불가**다(대장 원문이 "390px 이상은 정상"이라 명시) — 거짓 커버리지 주장이라 삭제하고 관측 범위 밖임을 명시
  - `[low]` `[patch]` `loadDotEnvLocal`이 `web/.env.local` 부재 시 조용히 아무것도 안 해, 뒤에서 불투명한 타임아웃으로 실패했다 — 파일명과 복구 방법(`scripts/use-env.sh`)을 담은 한국어 에러로 즉시 실패하도록 변경
  - `[low]` `[patch]` `expectedColsFor`가 모르는 프로젝트명에 대해 조용히 1열을 기대값으로 반환했다(새 뷰포트를 추가하면 틀린 값으로 통과) — 예외를 던지도록 수정
  - `[low]` `[patch]` 랜딩 섹션 로케이터가 유일성을 단언하지 않아, 바깥 `<section>`이 두 제목을 함께 감싸면 `.first()`가 인기 그리드를 두 번 재고 최신 그리드가 다시 빠질 수 있었다(직전 패스가 고친 바로 그 결함) — 정확히 1개로 해소되는지 단언 추가
  - `[low]` `[patch]` 새 E2E 스위트를 **어떻게 돌리는지 리포 어디에도 없었다** — 전제조건(로컬 Supabase 기동·`use-env.sh`·`seed-local.sh`·`playwright install`·포트)이 코드 주석에만 있어, `#86`을 닫은 근거인 "다시 돌리면 재생산된다"가 다음 사람에겐 성립하지 않았다. `web/README.md`에 실제 스크립트명을 확인해 절차 추가
  - `[medium]` `[defer]` `#127` 폰트 CDN 가드가 `layout.tsx` 한 파일만 스캔해 `globals.css`의 `@import url(https://…)`(그 파일은 이미 `@import`를 쓰고 있어 살아 있는 경로다)·나머지 두 레이아웃·`rel="preload|preconnect"` 재유입이 무방비 — 관측 범위를 intent-contract가 "layout.tsx 소스 + fonts/ 용량만"으로 못박아 범위 밖. `docs/tech-debt.md` `#170`으로 신규 등재(트리거 포함)
  - `[low]` `[defer]` 감사가 브레이크포인트 경계값(639/640/1099/1100)을 한 번도 렌더하지 않아 임계값 한 칸 밀림 회귀를 3개 프로젝트 전부 green으로 통과시킨다(같은 클래스의 640/1100 순서 버그가 과거 실측 사례) — 뷰포트 매트릭스를 intent-contract가 "정확히 3개"로 못박아 범위 밖. `docs/tech-debt.md` `#171`로 신규 등재
  - `[low]` `[defer]` 대장 자체의 결함 2건 — 이 스토리가 닫은 6개 항목(`#73`·`#84`·`#86`·`#87`·`#127`·`#160`)의 제목이 여전히 열린 항목처럼 읽혀 이 파일이 정한 세는 법으로는 열린 것으로 집계되고, `#168`의 트리거가 날짜 없는 조건이라 B8을 만족하지 못한다. **한 번 고쳤다가 되돌렸다** — 이 세션의 호출 지시가 "기존 대장 항목을 수정·재개방·재작성하지 말 것(상태와 해소는 오케스트레이터가 소유)"으로 못박았고 둘 다 기존 항목의 상태·본문을 건드리는 일이다. `docs/tech-debt.md` `#172`로 신규 등재(경위·트리거 포함)
  - `[reject]` AC1 문구("4화면 모두에서 그리드 열수 재배치")와 실제 구현(그리드가 실재하는 랜딩·`/search`에만 열수 단언) 불일치 — intent-contract의 I/O 매트릭스가 이미 `/search(또는 랜딩 그리드)`로 범위를 정했고, 상세·`/ai`엔 카드 그리드가 없어 4/2/1 단언이 성립 자체를 안 한다. 구현이 구속력 있는 계약을 따랐고 스펙 안에 근거를 명시했으므로 결함이 아님
  - `[reject]` `#84` 수정(`size={1}`)이 CI 게이트에 없음 — 이미 `#168`로 등재된 의도적 결정
  - `[reject]` 컨테이너 수준(`<main>`에 `w-full`) 수정을 하지 않고 leaf(`size={1}`)로 고쳤다는 지적 — 동일 원인의 채팅방 사례는 이미 `#169`로 등재됐고, `<main>` 수정은 이 스토리가 손대기로 한 프로덕션 파일 밖
  - `[reject]` tsconfig가 `e2e/**`를 포함해 배포 빌드가 테스트 전용 파일에 타입 결합됨 — Vercel은 빌드 시 devDependencies를 설치하고 `npm run build`가 실제로 green이라 현 구성에서 발생하지 않음
  - `[reject]` 로그인 상태 랜딩·상세 변형 미커버 · `buildMockListings`의 `image_count` 고정으로 배지 분기 미감사 — 둘 다 감사 범위 확대 요구(intent 권한 밖)
  - `[reject]` `aria-haspopup` 로케이터 strict-mode 위험 · dotenv 인라인 주석/`export` 접두사 파싱 · shell env가 `.env.local`과 다를 때 경고 · `login()` 실패 시 메시지 · `assertGridColumns`의 미해결 `repeat()` 값 · `#169`의 심각도 표기 — 전부 현 리포에서 발생 조건이 없는 추측성 강화 요구

### 2026-07-28 — Review pass (후속 3차 — `status: done` 스펙 재리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 5, low 4)
- defer: 6: (high 0, medium 3, low 3)
- reject: 14: (high 0, medium 0, low 14)
- addressed_findings:
  - `[medium]` `[patch]` **이미지 전면 장애 실험이 90장 중 82장만 실제로 시험하고 있었다 — 나머지 8장은 요청조차 나가지 않았는데 세 단언이 전부 green이었다.** 오케스트레이터가 직접 실측: abort 걸고 `scrollFullPage` 후 `/search`(카드 95개) 상태가 `aborts: 82`, 살아남은 `img[data-testid="listing-photo"]` **8개**(`loading="lazy"`·`complete: false`·`naturalWidth: 0` — 즉 "폴백 실패"가 아니라 **"시험되지 않음"**). 원인은 `scrollFullPage`가 매 반복 `scrollTo(0, scrollHeight)`로 **바닥까지 점프**해 중간 구간 카드가 뷰포트를 한 번도 지나지 않는 것. 이것은 `#73` 원문의 결함(43/90만 시험되고 나머지는 "폴백이 안 뜬 것"이 아니라 "시험되지 않은 것")을 **`#73`을 닫은 스펙이 그대로 재현**한 형태다. 뷰포트 높이의 0.8배씩 점진 스크롤로 수정(반복 상한도 문서 높이에서 계산). B4: 옛 점프 방식을 되살려 red 확인(`사진 <img>가 8개 남아 있음`) → 원복해 green 확인
  - `[medium]` `[patch]` `assertPlaceholderFallbackFired`가 `>0`이라 **폴백이 한 번도 안 떠도 통과**했다 — 실측: abort를 아예 안 걸어도 `/search`에 "사진 준비중"이 5개 있다(사진 자체가 없는 매물). 테스트 제목과 AC는 "**전량** 발동"인데 단언은 "1개 이상"이었다. 살아남은 사진 `<img>` 0개 + 플레이스홀더 수 = 카드 수로 교체(상세는 갤러리가 `urls[index]` 한 장만 마운트하므로 그 한계를 실측 주석으로 명시하고 단언을 정직하게 좁힘 → `#177`로 등재)
  - `[medium]` `[patch]` D5 "세로화 없음" 검사가 **접힐 수 없는 요소**를 재고 있었다 — 대상인 `listing-meta`는 `truncate whitespace-nowrap`이고 Tailwind `truncate`가 이미 `white-space:nowrap`을 emit하므로 구조적으로 2줄이 안 된다. 주석을 실측 사실로 정정(이 검사가 잡는 것은 접힘이 아니라 **truncate 계약의 소실**)하고, computed `white-space`/`text-overflow` 단언을 추가해 짧은 시드 문자열에서도 클래스 삭제가 잡히게 했다. B4: `ListingCard.tsx:83`에서 클래스를 지워 **3개 프로젝트 전부 red**(패치 전에는 desktop에서만 red였다 — verification-gap 레이어가 실측) → 원복해 green
  - `[medium]` `[patch]` `playwright.config.ts`에서 **프로젝트를 삭제하면 7개 테스트가 조용히 스킵되고 exit 0**이었다 — `PROJECT_NAMES` 상수는 *이름 변경*만 묶었지 *존재*는 안 묶었다. 설정 로드 시점에 모든 `PROJECT_NAMES` 값이 실제 프로젝트 목록에 있는지 단언(없으면 한국어 에러). 닫지 못하는 축(`--project=` 부분 실행)은 의도된 사용자 선택이므로 주석으로 명시
  - `[medium]` `[patch]` `.first()`를 `toHaveCount(1)` **앞에** 붙여 중복 검출이 무력화돼 있었다 — `InquiryCta`는 데스크톱 aside·모바일 하단바 두 인스턴스가 같은 `data-testid`를 쓰므로, 브레이크포인트 회귀로 390px에서 **둘 다 보여도** 통과했다(`#82`가 고쳤던 바로 그 결함 형태). 좁히지 않은 로케이터에 개수를 단언한 뒤 `.first()`로 측정하도록 수정
  - `[low]` `[patch]` `expectedColsFor`가 프로젝트 **이름 접두사**로 기대 열 수를 정해, 이름은 그대로 두고 뷰포트만 바꾸면 렌더 폭과 무관한 값을 단언했다 — `testInfo.project.use.viewport.width` + D5 브레이크포인트에서 도출하도록 변경
  - `[low]` `[patch]` `E2E_PORT`가 무검증(`Number(… ?? 3000)`)이라 빈 문자열은 `0`, 오타는 `NaN`이 되어 `http://localhost:NaN`·`next start -p NaN`으로 **풀 빌드를 태운 뒤** 불투명하게 실패했다 — 1~65535 정수 검증 + 변수명·잘못된 값을 담은 한국어 에러
  - `[low]` `[patch]` 폰트 가드 2구멍 — (a) `toContain('from "next/font/local"')`가 큰따옴표 리터럴이라 포매팅 한 번에 red가 된다(`layout.tsx`는 단일 따옴표 코드베이스에서 유일한 큰따옴표 import) → 따옴표 무관 정규식, (b) `href={CDN_URL}` 같은 **JSX 표현식 href**는 정적으로 외부가 아님을 증명할 수 없는데 통과했다 → 표현식 href도 실패로 전환
  - `[low]` `[patch]` `fontsDirTotalBytes`가 `statSync`(심볼릭 링크 추종)라 순환 링크에서 스택 오버플로, 링크된 파일은 대상 바이트를 로컬처럼 계산했다 → `lstatSync` + 링크 건너뛰기
  - `[medium]` `[defer]` D5가 **이름으로 지목한** 신뢰속성 행(`TrustAttributes` `variant="card"`의 `flex flex-wrap`)이 카드 안에서 유일하게 진짜 접힐 수 있는 요소인데, 시드 데이터에 해당 속성이 없어 **95개 카드 전부에서 0회 렌더**된다(실측 `trustRows: 0`) — 감사 커버리지가 약한 게 아니라 0이다. 지금 단언을 심으면 죽은 코드가 되고 실효 있는 수정은 시드 변경이라 범위 밖 → `docs/tech-debt.md` `#173`
  - `[medium]` `[defer]` `web/e2e/**`가 **어떤 게이트에서도 타입체크되지 않는다**(CI web 잡 = lint + vitest, `tsc` 없음) — `project-names.ts` 주석이 약속한 "이름 바꾸면 타입 에러로 드러난다"가 실행되지 않는 자리에 있다. 실측: 잘못된 키에 `lint` exit 0 / `tsc --noEmit` exit 2. intent-contract의 Never(CI 워크플로 미변경)에 걸려 범위 밖 → `#175`
  - `[medium]` `[defer]` E2E가 의존하는 `data-testid` 4종 + `aria-haspopup` 계약이 **CI가 도는 어떤 테스트에도 고정돼 있지 않다**(`web/src/**/*.test.ts`에 참조 0건) — 조용한 0건 매칭을 막으려 심은 방어가 정작 실행되지 않는 자리에 있다 → `#176`
  - `[low]` `[defer]` 대장 기존 항목 3곳에 "Playwright 스펙이 레포에 0개다"라는 이미 거짓이 된 주장이 남아 있다 — 같은 주장을 담던 워크플로 헤더·project-context는 이 스토리가 고쳤는데 **정본만 낡았다**. 기존 항목 수정 금지 지시로 못 고침(`#172`와 짝) → `#174`
  - `[low]` `[defer]` 상세 이미지 폴백은 사진 1장만 시험한다 — `ListingGallery`가 `urls[index]`만 마운트하므로 캐러셀 2~N번째는 지연로딩이 아니라 **미마운트**라 스크롤로 도달 불가. "세 소비처 전량"이 상세에서는 구조적으로 성립하지 않음 → `#177`
  - `[low]` `[defer]` `#155`(`/search` 376px 넘침)의 유력 원인이 `#84` 수정 중 규명됐다(fit-content `mx-auto <main>` + `<input>` intrinsic 폭 — `#169`와 같은 메커니즘) — 기존 항목 수정 금지 + 이 매트릭스 최소 폭 390px이라 관측 수단 자체가 없어 못 고침 → `#178`
  - `[reject]` 스펙 frontmatter가 `in-review`인데 `sprint-status.yaml`은 `done`이고 `review_loop_iteration: 0`이다 — **이번 패스가 스스로 만든 상태**다(step-04가 리뷰 시작 시 `in-review`로 바꾸고 종료 시 `done`으로 되돌린다. `done` 스펙 재리뷰는 카운터를 0으로 리셋하고 시작하도록 워크플로가 규정한다)
  - `[reject]` `ListingCard.tsx`가 D5 파손 상태로 미커밋돼 있다 — **병렬로 돌던 verification-gap 레이어가 B4 실측을 위해 주입했다 되돌리는 중이던 순간을 adversarial 레이어가 본 것**이다. 직접 확인: 두 레이어 종료 후 `git status`에 해당 파일 없음(트리 깨끗)
  - `[reject]` AC1 문구(4화면)와 구현(2화면) 불일치 — 2차 패스에서 계약(I/O 매트릭스가 `/search`(또는 랜딩 그리드)로 범위 지정) 기준으로 이미 판정된 사안
  - `[reject]` 시드 비밀번호 `seller123`이 `helpers.ts`·`README.md`에 커밋됐다 — 로컬 docker Supabase 전용 값이고, 환경변수로 옮기면 `#86`이 닫은 "다시 돌리면 재생산된다"가 추가 사전조건에 의존하게 돼 손해가 이득보다 크다
  - `[reject]` "E2E는 CI에 없다" 근거가 3개 파일에 중복 서술 — 세 곳의 상세도가 서로 다르고(주석 한 줄 / §12 요약 / 대장 본문) 실제 드리프트 위험이 낮다
  - `[reject]` `waitForLoadState('networkidle')` 6회가 Playwright 권장에 어긋남 — 스위트가 반복 실행에서 안정적으로 green이고, 실제 실패 관측이 없는 추측성 지적
  - `[reject]` `assertGridColumnsOrEmptyState`의 빈 상태 수용 분기가 도달 불가(뒤따르는 meta 단언이 빈 그리드에서 실패) — verification-gap 레이어가 추적해 "vacuous pass가 아님"으로 확인. 설계상의 사소한 중복이지 결함이 아님
  - `[reject]` `#84` 수정에 CI 게이트가 없음 — 이미 `#168`로 등재된 의도적 결정
  - `[reject]` `size={1}`이 `flex-1` 삭제 시 입력창을 1글자 폭으로 붕괴시키는데 그걸 막는 단언이 없음 — 발생 조건이 없는 추측성 강화 요구
  - `[reject]` `/ai` 답변에 긴 무공백 토큰이 오면 `#84`가 재발 가능(`whitespace-pre-wrap` + `break-words` 부재) — 프로덕션 스타일 변경을 요구하므로 Never(시각 디자인 미변경)에 걸림
  - `[reject]` 랜딩·내비 감사가 비로그인/로그인 분기 중 한쪽만 커버 — 감사 범위 확대 요구(intent 권한 밖)
  - `[reject]` `assertGridColumnsOrEmptyState`가 컨테이너 내 `role="list"` 유일성을 단언하지 않음 — 현재 `ResponsiveGrid`만 그 role을 emit해 발생 조건 없음
  - `[reject]` 첫 카드만 D5 단언(가장 긴 콘텐츠가 표본이 아님) — 시드 meta 문자열이 균질해 발생 조건이 없고, 전량 순회는 범위 확대
  - `[reject]` `assertNoHorizontalOverflow`가 중첩 `overflow-x` 컨테이너를 못 봄 · `isVisible()` 비재시도 · `fetchOnSaleListingIdWithPhoto`가 다중 사진 매물을 보장 안 함 — 앞 둘은 발생 조건 없는 추측, 셋째는 `#177`에 흡수

## Design Notes

**대장 점검(workflow persistent fact 이행):** 착수 시 `deferred-work.md`를 읽어 `status: open`인 `DW-1`(11-0)·`DW-2`(11-1)·`DW-3`(11-2)를 확인했다 — 셋 다 Story 11-3이 이미 처리했다(`DW-1`→`docs/tech-debt.md` #148, `DW-2`→#149, `DW-3`→#164, 전부 "이미 있음"으로 중복 등재 없이 종결). 새 `DW-<번호>`는 없다(11-4는 `followup_review_recommended: false`로 마감). `deferred-work.md` 원본은 수정하지 않는다.

**Playwright 도입 가능성 사전 확인(계획 단계 실측):** 이 세션 환경에 `~/.cache/ms-playwright`가 이미 존재하고 `chromium-1226/1228/1232` 등 여러 리비전이 캐시돼 있다(Playwright MCP 도구가 이미 이 머신에서 브라우저를 구동 중이라는 방증). npm 레지스트리(`registry.npmjs.org`)도 도달 가능함을 확인했다. `@playwright/test` 설치 후 `npx playwright install chromium`이 캐시를 재사용하거나 네트워크로 받는 두 경로 모두 열려 있어 보이나, 실제 설치·구동은 구현 단계에서 실측하고 실패하면 Block If에 따라 HALT한다.

**#86 "재실행 가능한 형태"의 해석:** 대장 원문은 스크린샷·네트워크 로그·E2E 스크립트 셋 다 없다고 지적하지만, 이 스토리가 채우는 것은 **자동화 스크립트**다 — 다시 돌리면 스크린샷·로그가 그때그때 재생산되므로, 특정 시점의 스크린샷 파일 자체를 정적으로 커밋하는 것은 재실행 가능성의 본질이 아니고 곧 낡는다. 커밋되는 실체는 `web/e2e/*.spec.ts` + `npm run test:e2e`다.

**#127 폰트 용량 예산 값:** 대장 본문이 "합의된 바이트 예산"이라고만 적고 구체 숫자를 남기지 않았다. 현재 커밋된 `PretendardVariable.woff2`가 2,057,688B이므로, 이 스토리가 회귀 감지 목적의 상한을 **2,300,000B**(약 250KB 버퍼)로 확정해 테스트에 박는다. 이는 제품 요구가 아니라 내부 회귀 가드 임계값이므로 사람 판단을 막을 필요가 없다고 보았다(Block If 대상 아님).

**CI e2e 미배선:** 이 스토리는 로컬에서 `npm run test:e2e`로 재실행 가능한 스펙만 남긴다. CI에 자동으로 도는 e2e job을 만들려면 헤드리스 브라우저 설치·로컬 Supabase 기동·시크릿 관리가 추가로 필요해 별도 스토리 규모다 — `docs/tech-debt.md`에 새 항목으로 이월한다(트리거: CI 안정화가 필요해지는 시점, 예: 배포 전 게이트 요건이 생길 때).

## Verification

**Commands:**
- `cd web && npm run test:e2e` -- expected: 신규 Playwright 스펙 전부 green
- `cd web && npm test` -- expected: 기존 vitest(신규 `fonts.budget.test.ts` 포함) 전부 green, 회귀 없음
- `cd web && npm run lint` -- expected: green
- `cd web && npm run build` -- expected: 성공(신규 파일이 타입/빌드를 깨지 않음)

**Manual checks (if no CLI):**
- `docs/tech-debt.md`에서 `#73`·`#86`·`#127`·`#160`·`#84`가 날짜 붙은 ✅ 해소로 갱신됐는지 육안 확인.

## Auto Run Result

**요약:** 레포 최초의 Playwright E2E 스위트(`web/e2e/`)를 신설해 데스크톱(1280×800)·태블릿(800×1024)·모바일(390×844) 3뷰포트로 랜딩·`/search`·상세·`/ai` 4화면의 그리드 재배치(4/2/1열)와 D5 내부무결성(세로화·줄바꿈·단일행)을 감사한다. 같은 층에서 대장 이월 5건(`#73`·`#86`·`#127`·`#160`·`#84`)을 닫았고, `/ai` 390px 가로 오버플로(`#84`)는 원래 가설(`min-w-0`)이 실측에서 틀린 것으로 확인돼 실제 원인(`<input>` 기본 `size` 힌트)을 재규명해 수정했다. 코드리뷰(4개 레이어 병렬) 결과 12건을 패치, 1건을 대장(`docs/tech-debt.md` `#169`, 채팅방 화면의 동일 패턴 버그)으로 이관, 3건을 반려했다.

**파일 변경 (한 줄 요약):**
- `web/playwright.config.ts` (신규) — 3뷰포트 프로젝트 + 프로덕션 빌드 webServer(재사용 안 함, 매번 새로 기동)
- `web/e2e/helpers.ts` (신규) — 로그인·그리드열수·단일행·깨진이미지·전량스크롤·AI목업 등 공용 단언 유틸
- `web/e2e/viewport-audit.spec.ts` (신규) — 4화면×3뷰포트 그리드·오버플로·D5 무결성 감사(`#84` 포함)
- `web/e2e/nav-interactions.spec.ts` (신규) — `#160` 내비 상호작용 4시나리오
- `web/e2e/image-fallback.spec.ts` (신규) — `#73`/`#86` 이미지 전면 장애 3소비처 재현
- `web/src/app/fonts.budget.test.ts` (신규, vitest) — `#127` 폰트 CDN 재유입·용량 회귀 가드(화이트리스트 방식)
- `web/src/components/ai/ChatAssistant.tsx` — `#84` 수정(`size={1}` + `min-w-0`, 실측으로 확정)
- `web/src/components/listings/ListingCardImage.tsx`, `ListingGallery.tsx` — 코드리뷰 patch: `data-testid="listing-photo"` 추가(깨진이미지 검사 선택자 안정화)
- `web/package.json`/`package-lock.json` — `@playwright/test` devDependency + `test:e2e` 스크립트
- `web/.gitignore` — Playwright 산출물(`test-results/`·`playwright-report/`·`blob-report/`) 무시
- `.github/workflows/tests.yml` — 낡은 "Playwright 0개" 주석 코드리뷰 patch로 정정
- `docs/tech-debt.md` — `#73`·`#84`·`#86`·`#127`·`#160`·`#87` 해소 기록 + `#168`(CI e2e 미배선)·`#169`(defer: 채팅방 동일 버그) 신규 등재
- `_bmad-output/project-context.md` §12 — CI 실제 커버리지로 갱신(`#87` 해소)

**리뷰 결과 (4개 레이어 병렬: adversarial·edge-case-hunter·verification-gap·intent-alignment):**
- patch 12건 (medium 4, low 8) — 전부 구현 서브에이전트가 적용 후 재검증 완료(아래).
- defer 1건 (medium) — `ChatRoomMessages.tsx`가 `#84`와 동일 원인으로 390px 오버플로. 이 스토리 범위 밖(감사 대상 4화면에 미포함)이라 `docs/tech-debt.md` `#169`로 신규 등재(트리거 포함), `deferred-work.md`(동결)에는 쓰지 않음.
- reject 3건 — 관리자/판매자 헤더 미검증(`#160` 범위 밖), `mockAiSearch` 인터셉션 미검증(실패 시 이미 크게 실패), `fetchOnSaleListingIdWithPhoto`의 판매완료 재검증 부재(RLS가 이미 강제, 의도된 설계).
- follow-up review 권고: **true** (patch medium 4·low 8 → 3×4+1×8=20 ≥ 5).

**검증 수행 (직접 실행·관찰, 서브에이전트 보고에만 의존하지 않음):**
- `npm run lint` — clean
- `npm test` — 239 passed (24 files, `fonts.budget.test.ts` 포함)
- `npm run build` — 컴파일+타입체크 green
- `npm run test:e2e` — 22 passed, 14 skipped(뷰포트 무관 스펙은 프로젝트 1개에서만 실행하도록 의도적으로 스킵) — 패치 적용 전/후 두 차례 독립 실행, 결과 동일
- Matrix Test Audit: I/O 매트릭스 5행(그리드 재배치·`/ai` 오버플로·이미지 전면장애·내비 4종·폰트 회귀) 전부 통과하는 테스트로 커버 확인(개별 실행으로 재확인)
- B4(일부러 깨서 red 확인 후 되돌려 green): `#84`(size 되돌림), `#160` 4종 각각, `#73` 폴백(ref콜백 비활성화), `#127` 2종(임계값 낮춤 + CDN 문자열 주입, 화이트리스트 검사가 독립적으로 미확인 호스트도 잡음을 재확인) — 전부 실측 확인.

**잔존 리스크:**
- `#73`의 근본 설계 과제(전면장애 vs 진짜 0장을 구별하는 관측 수단)는 이 스토리 범위 밖으로 남음 — 대장에 명시.
- CI에 이 E2E 스위트가 배선되지 않음(의도적 결정, `#168`) — 로컬 실행에 의존.
- `#169`(채팅방 동일 버그)는 이 스토리가 고치지 않고 이관만 함.
- Playwright `webServer`가 매번 새로 빌드하도록 바꿔(패치 12) 로컬 반복 실행 시간이 다소 늘었다(정확성 우선, 트레이드오프 문서화됨).

**잔여물(포함되지 않음, `git status`에 남김):** 이 스펙 파일 자체 — `final_revision`(커밋 후에야 알 수 있는 해시)을 적어 넣는 마지막 메타데이터 수정 한 줄이 커밋 이후 발생해 워크플로 구조상 그 커밋에는 포함될 수 없다(선행 스토리 11-4와 동일한 패턴).

---

## Auto Run Result — 후속 리뷰 2차 (2026-07-28)

**무엇을 했나:** `status: done`이던 이 스펙을 대상으로 독립 후속 리뷰 패스를 돌렸다(4개 레이어 병렬: adversarial · edge-case-hunter · verification-gap · intent-alignment). 코드는 새로 만들지 않았고, **이미 통과 중이던 감사 층이 실제로는 무엇을 안 잡고 있었는지**를 찾아 15건을 고쳤다.

**핵심 발견의 성격:** 찾은 결함 대부분이 "테스트가 실패한다"가 아니라 **"테스트가 아무것도 안 재는데 green이다"**(vacuous pass)였다. 이 스토리가 닫은 `#73`(시험되지 않은 것을 통과로 읽음)과 정확히 같은 실패 형태가 새 감사 층 안에 여러 개 들어 있었다:
- 매물 조회가 **실패**해도 그리드 재배치 단언이 통과(핵심 AC가 측정 0회로 green)
- 이미지 abort가 **일어나지 않아도** 폴백 검사 2개가 모두 통과
- padding이 큰 버튼은 **2줄로 밀려도** 단일행 검사가 통과
- 폰트를 하위 폴더에 넣으면 용량 예산을 **통째로 우회**
- 프로젝트명을 바꾸면 7개 테스트가 **조용히 스킵되고 exit 0**

**파일 변경 (한 줄 요약):**
- `web/e2e/helpers.ts` — 에러/빈상태 분리, 단일행 오차식 수정, 목업 URL 정규화+호출 단언, 스크롤 좌표계 통일+안정화, 조회 정렬 고정, `#155` 거짓 커버리지 주장 삭제
- `web/e2e/project-names.ts` (신규) — 프로젝트명 상수 공용화(스킵 가드가 이름 변경에 조용히 무력화되지 않게)
- `web/playwright.config.ts` — `.env.local` 부재 시 즉시 실패, `E2E_PORT` 재정의 지원, 프로젝트명 상수 사용
- `web/e2e/viewport-audit.spec.ts` — 미상 프로젝트 예외, D5 단언을 `data-testid` 기반 실패(스킵 아님)로 전환, 랜딩 섹션 유일성 단언, 목업 호출 단언
- `web/e2e/image-fallback.spec.ts` — abort 실제 발생 카운터 단언 + 사진 요소 존재 확인
- `web/e2e/nav-interactions.spec.ts` — 프로젝트명 상수 사용
- `web/src/components/listings/ListingCard.tsx` · `web/src/app/(user)/listings/[id]/InquiryCta.tsx` — 동작 무관 `data-testid` 훅 추가(검사 선택자 안정화)
- `web/src/app/fonts.budget.test.ts` — 용량 합산 재귀화
- `web/README.md` — E2E 실행 전제조건·명령 문서화(`#86`의 "다시 돌릴 수 있음"을 실제로 성립시킴)
- `docs/tech-debt.md` — 신규 3건만 추가(`#170` 폰트 가드 스캔 범위 · `#171` 브레이크포인트 경계값 미커버 · `#172` 대장 자체 결함 2건). **기존 항목은 수정하지 않았다** — 호출 지시가 금지했다(한 번 고쳤다가 되돌린 경위는 `#172` 본문)

**검증 (오케스트레이터가 직접 실행·관찰, 서브에이전트 보고에만 의존하지 않음):**
- `npm run lint` — clean
- `npm test` — 24 files / 239 tests 전부 통과
- `npm run build` — 컴파일·타입체크 green, 20개 라우트 생성
- `npm run test:e2e` — **22 passed / 14 skipped / 0 failed**(스킵은 뷰포트 무관 스펙을 한 프로젝트에서만 돌리는 의도된 설계)
- B4(일부러 깨서 red → 원복해 green): 위 vacuous-pass 5종 전부 실측 확인. 특히 이미지 abort 건은 **깨뜨린 상태에서 기존 두 단언이 여전히 green임을 함께 재현**해, 새 카운터 단언이 없었다면 무엇이 지나갔을지를 증거로 남겼다

**리뷰 결과:** patch 15건(medium 9 · low 6) · defer 3건(대장 `#170`·`#171`·`#172`) · reject 12건. follow-up review 권고 = **true**(3×9+1×6=33 ≥ 5).

**잔존 리스크:**
- 폰트 CDN 가드의 스캔 범위(`globals.css`·나머지 레이아웃)는 계약상 범위 밖이라 여전히 열려 있다 — `#170`.
- 브레이크포인트 경계값은 감사되지 않는다 — `#171`.
- 이 스위트는 여전히 CI에 없다(의도적, `#168`) — 로컬 실행 전제이며, 이제 그 방법이 `web/README.md`에 적혀 있다.
- 대장의 제목 표기·`#168` 트리거 정리는 오케스트레이터 몫으로 남겼다 — `#172`.

---

## Auto Run Result — 후속 리뷰 3차 (2026-07-28)

**대장 점검(workflow persistent fact 이행):** `deferred-work.md`(동결)의 `status: open` 항목 3건을 확인했다 — `DW-1`: 이미 `docs/tech-debt.md` #148에 있음 · `DW-2`: 이미 #149에 있음 · `DW-3`: 이미 #164에 있음. 셋 다 이관 완료 상태라 중복 등재하지 않았고, 동결 파일은 건드리지 않았다. 새 `DW-<번호>`는 없다.

**무엇을 했나:** `status: done`이던 이 스펙에 3차 독립 리뷰 패스를 돌렸다(4개 레이어 병렬: adversarial · edge-case-hunter · verification-gap · intent-alignment). 프로덕션 코드는 한 줄도 바꾸지 않았고, **감사 층 자체가 무엇을 못 재고 있었는지**를 실측으로 찾아 9건을 고쳤다.

**이번 패스의 핵심 — 추론이 아니라 실측이 결론을 바꿨다.** 세 레이어가 "폴백 단언이 `>0`이라 약하다"를 지적했지만, 그건 강도 문제가 아니라 **커버리지 0.9할 문제**였다. 오케스트레이터가 직접 브라우저를 띄워 잰 값:

| 상태 | 카드 | 사진 `<img>` | "사진 준비중" | abort 발생 |
|---|---|---|---|---|
| abort 없음 | 95 | 90 | 5 | — |
| abort + 기존 `scrollFullPage` | 95 | **8 잔존** | 87 | **82** |

살아남은 8장은 전부 `loading="lazy"` · `complete: false` · `naturalWidth: 0` — **요청 자체가 안 나갔다.** 즉 "폴백이 잘 됐다"가 아니라 **"시험되지 않았다"**이고, 이것은 `#73` 원문이 지적한 결함(90장 중 43장만 시험)과 **글자 그대로 같은 형태**다. `#73`을 닫은 스펙이 `#73`을 재현하고 있었다. 원인은 `scrollFullPage`가 매 반복 바닥까지 점프해 중간 구간이 뷰포트를 지나지 않는 것이었고, 뷰포트 0.8배씩 점진 스크롤로 고쳐 **90/90 · 잔존 0**을 확인했다.

같은 성격의 두 번째: abort를 **아예 안 걸어도** "사진 준비중"이 5개 뜬다(사진 없는 매물). 그래서 `>0` 단언은 폴백이 한 번도 발화하지 않아도 green이었다.

**파일 변경 (한 줄 요약):**
- `web/e2e/helpers.ts` — 점진 스크롤로 전환(지연로딩 전량 노출), 폴백 단언을 "잔존 사진 0 + 플레이스홀더 = 카드 수"로 강화
- `web/e2e/image-fallback.spec.ts` — 세 소비처 호출부에 기대 카드 수 전달, 상세의 구조적 한계(갤러리 미마운트)를 실측 주석으로 명시
- `web/e2e/viewport-audit.spec.ts` — D5 주석을 실측 사실로 정정 + computed `white-space`/`text-overflow` 단언 추가, `.first()`/`toHaveCount(1)` 순서 교정, 기대 열 수를 뷰포트 폭에서 도출
- `web/playwright.config.ts` — 프로젝트 존재 단언(삭제 시 조용한 스킵 차단), `E2E_PORT` 값 검증
- `web/src/app/fonts.budget.test.ts` — 따옴표 무관 정규식, JSX 표현식 href 차단, 심볼릭 링크 안전 순회
- `docs/tech-debt.md` — **신규 6건만 추가**(`#173`~`#178`). 기존 항목은 한 글자도 수정하지 않았다(호출 지시)

**검증 (오케스트레이터가 직접 실행·관찰, 서브에이전트 보고에만 의존하지 않음):**
- `npm run lint` — clean
- `npm test` — 24 files / 239 tests 전부 통과
- `npm run build` — 컴파일·타입체크 green, 20개 라우트 생성
- `npm run test:e2e` — **22 passed / 14 skipped / 0 failed**
- B4(일부러 깨서 red → 원복해 green), 직접 수행: 옛 점프 스크롤을 되살리자 `/search` 폴백 스펙이 `사진 <img>가 8개 남아 있음 — 아직 폴백이 발화하지 않은 카드가 있다는 뜻(전량 발동 아님)`으로 **red**, 원복하니 3/3 **green**. 즉 새 단언은 **내가 실측한 결함을 실제로 잡는다** — "만들었다"가 아니라 "잡는다"를 확인했다

**리뷰 결과:** patch 9건(medium 5 · low 4) · defer 6건(`#173`~`#178`) · reject 14건. follow-up review 권고 = **true**(3×5+1×4=19 ≥ 5).

**잔존 리스크:**
- D5가 이름으로 지목한 신뢰속성 행은 시드에 안 뜨므로 **감사 커버리지 0**이다 — `#173`. 이번 패스가 고친 것은 "이 검사가 무엇을 재는지"에 대한 서술의 정직성이지, 그 행의 접힘 여부가 아니다.
- `web/e2e/**`는 실행도 타입체크도 어떤 게이트에도 없다 — `#175`(+`#168`). 수동 실행 사이에 조용히 썩을 수 있는 구조는 그대로다.
- 상세 화면 폴백은 사진 1장만 시험한다 — `#177`.
- 대장의 낡은 "Playwright 0개" 주장과 제목 표기 정리는 여전히 오케스트레이터 몫 — `#172`·`#174`.

**잔여물(포함되지 않음):** 없음 — 이 스펙 파일의 `final_revision` 한 줄만 커밋 이후에 갱신된다(선행 패스와 동일한 구조적 패턴).
