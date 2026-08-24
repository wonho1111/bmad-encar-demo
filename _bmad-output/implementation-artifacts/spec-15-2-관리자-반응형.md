---
title: '관리자 웹 반응형 — 사이드바 내비 셸 + D5 뷰포트 무결성 감사'
type: 'feature'
created: '2026-08-06'
status: 'done'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['oversized']
baseline_revision: '00ab1e5892713713d79548ffa7a3eec3dddb3d6b'
final_revision: '5c6b841f6193ac9efcf67e4b24ddd8ef65ba16eb'
---

<intent-contract>

## Intent

**Problem:** 관리자 6화면은 15.1에서 토큰 리스킨만 됐고 반응형 구조는 그대로다 — 페이지 기반 내비(대시보드 허브 4링크 + 각 화면의 뒤로가기)뿐이고 데스크톱 고정 사이드바·모바일 대응이 없다. D5 반응형 무결성(project-context 규칙13: ≥1100px=4열·640~1099px=2열·<640px=1열, 가로 배치 세로화 금지)을 실측으로 검증하는 자동 검사도 관리자 경로엔 0건이다(`viewport-audit.spec.ts`에 `/admin*` 없음, `core-flows.spec.ts` C6은 목록 4개만 데스크톱에서 방문). 15.1 후속 리뷰가 등재한 DW-696·697·699·701 네 건도 트리거를 "Story 15.2 착수 시"로 명시해 뒀다.

**Approach:** 관리자 5개 내비 목적지(대시보드/회원관리/전체매물/거래내역/채팅관리)에 `SiteNav.tsx`의 FocusTrap-dialog + matchMedia 자동닫힘 패턴을 이식해 데스크톱 고정 사이드바 + 모바일 슬라이드인을 추가한다. 이어서 `viewport-audit.spec.ts`에 관리자 경로, `messageBubbleWrap` 계약에 관리자 채팅 버블, `core-flows.spec.ts` C6에 상세 라우트를 추가해 D5를 실측으로 닫고, DW-699(죽은 호버)·DW-696(잔여 zinc 4파일)을 함께 처리한다.

## Boundaries & Constraints

**Always:**
- 사이드바는 새 클라이언트 컴포넌트 `web/src/components/layout/AdminSidebar.tsx`로 만들어 `(admin)/layout.tsx`에서 `AppHeader` 아래·children 옆에 마운트한다. **`AppHeader.tsx`는 수정하지 않는다**(DW-695는 "AppHeader를 실제로 건드리는 스토리 착수 시"가 트리거인데, 이 설계는 그 파일을 안 건드리므로 트리거되지 않는다 — 계속 열어 둔다).
- 사이드바 붕괴 breakpoint는 `SiteNav.tsx`가 이미 쓰는 760px(`min-[760px]:`, `matchMedia('(min-width: 760px)')`)를 그대로 따른다 — D5의 그리드 브레이크포인트(1100/640)와는 다른 축(내비 셸 vs 그리드 열수)이므로 혼용하지 않는다.
- 데스크톱(≥760px): 고정 사이드바(240px, sticky) + 5개 nav item, 현재 경로 active 표시. 모바일(<760px): 햄버거 버튼 + `FocusTrap` 슬라이드인 패널(SiteNav의 outside-pointerdown-close + matchMedia 자동닫힘 패턴 재사용).
- 대시보드 허브의 기존 4개 링크 버튼, 각 상세 화면의 뒤로가기 버튼은 그대로 둔다(제거 안 함) — 사이드바는 추가되는 내비이지 기존 페이지 내비를 대체하지 않는다.
- 사이드바가 콘텐츠 폭을 줄이는 것이 D5(가로 배치 세로화 금지·가로스크롤 금지)를 깨지 않는지 관리자 6화면 모두 3개 뷰포트(1280/800/390)에서 실측 확인한다.
- `viewport-audit.spec.ts`에 관리자 6경로(목록 4 + 상세 2 중 대표 1개씩)를 추가해 가로스크롤 없음을 3뷰포트에서 확인한다(그리드 열수 단언은 관리자 화면에 그리드가 없으므로 적용하지 않는다 — 파일 헤더 주석의 기존 규칙과 동일한 논리로 스코프한다).
- `messageBubbleWrap.test.ts`의 `BUBBLE_CLASS`에 백틱 템플릿 리터럴 분기를 추가하고(DW-701), 관리자 채팅 버블(`admin/chats/[roomId]/page.tsx`)도 같은 계약으로 스캔한다(DW-697 ①) — 파일별 기대 개수를 각각 단언한다(사용자 3개, 관리자 1개).
- `core-flows.spec.ts` C6을 관리자 상세 라우트(`/admin/listings/[id]`, `/admin/chats/[roomId]`)까지 넓히고 `isSeller` 기준 좌/우 배치를 단언한다(DW-697 ③).
- DW-699: `chat/page.tsx`·`chat/[roomId]/page.tsx`·`admin/chats/page.tsx`의 죽은 라이트모드 호버(현재 대비 1.045:1)를 다른 축 신호(예: `hover:border-brand-petrol` 또는 `hover:underline`, 새 토큰 추가 없이)로 교체하고 실제 변화를 수치나 관찰로 남긴다.
- DW-696: `search/page.tsx`·`components/ai/ChatAssistant.tsx`·`components/landing/PopularRecentGrid.tsx`·`(user)/ai/page.tsx`의 잔존 `zinc-*`(14건)를 15.1과 동일한 토큰으로 치환하고 grep 0건을 재확인한다.
- 새 검사는 "만들었다"가 아니라 "잡는다"로 닫는다(CLAUDE.md B4) — `messageBubbleWrap` 확장·`viewport-audit` 관리자 추가 후 각각 일부러 깨서 red 확인 → 되돌려 green 확인.

**Block If:**
- 사이드바 폭(240px) 때문에 640~1099px 구간에서 관리자 화면 콘텐츠가 실제로 가로스크롤 없이 들어가지 않는 경우(예: 회원관리 행의 배지+액션 조합이 줄바꿈됨) — 그 구간에서도 사이드바를 접을지 판단이 필요하므로 HALT.
- DW-699 호버 대비 해소에 `globals.css`의 새 hex/토큰 추가가 실제로 불가피하다고 실측 확인된 경우(다른 축 신호 옵션이 불충분함을 먼저 확인한 뒤에도) — HALT.

**Never:**
- 관리자 화면에 카드 그리드→모바일 캐러셀 패턴은 적용하지 않는다 — 현재 6화면 모두 그리드가 아니라 단일 열 리스트/상세이며 새 그리드를 만들지 않는다.
- 필터 사이드바→바텀시트 패턴도 적용하지 않는다 — 관리자 화면에 필터 UI가 아직 없다(FR61 필터 교체는 Story 15.3 소관).
- 신규 관리 기능(집계 KPI 카드 등)을 추가하지 않는다(Epic 15 UI-only 원칙 유지).
- `AppHeader.tsx`·`globals.css`는 수정하지 않는다.
- DW-698(`OptionPicker.tsx` 대비)·DW-700(`(auth)/layout.tsx` 주석)은 이 스토리의 트리거 대상이 아니므로 손대지 않는다(각각 다른 트리거 조건을 갖는다).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 데스크톱 사이드바 | viewport ≥760px, `/admin/members` 방문 | 고정 사이드바 표시, "회원관리" 항목 active 스타일 | - |
| 모바일 슬라이드인 열기 | viewport <760px, 햄버거 클릭 | FocusTrap 패널 열림, Tab이 패널 안에서 순환, Esc/바깥 클릭으로 닫힘 | - |
| 모바일→데스크톱 리사이즈 | 패널이 열린 채 viewport가 760px 이상으로 커짐 | matchMedia 리스너가 패널을 자동으로 닫음(SiteNav와 동일) | - |
| 관리자 상세 라우트 D5 | `/admin/listings/[id]`, 390px | 가로스크롤 없음, 라벨·뱃지 두 줄 안 됨(가장자리 클리핑만 허용) | - |

</intent-contract>

## Code Map

- `web/src/components/layout/SiteNav.tsx` -- 이식할 FocusTrap-dialog + matchMedia 자동닫힘 패턴의 원본(760px 브레이크포인트, outside-pointerdown-close)
- `web/src/components/layout/AdminSidebar.tsx` (신규) -- 데스크톱 고정 사이드바 + 모바일 햄버거/슬라이드인, 5개 nav item, active 상태
- `web/src/app/(admin)/layout.tsx` -- `AdminSidebar` 마운트(`AppHeader`는 그대로)
- `web/src/components/ui/FocusTrap.tsx` -- 모바일 패널에 재사용할 기존 포커스트랩
- `web/src/app/(admin)/admin/page.tsx`, `admin/members/page.tsx`, `admin/listings/page.tsx`, `admin/listings/[id]/page.tsx`, `admin/transactions/page.tsx`, `admin/chats/page.tsx`, `admin/chats/[roomId]/page.tsx` -- 사이드바로 콘텐츠 폭이 줄어도 D5가 깨지지 않는지 확인(그리드/필터 변경 없음)
- `web/e2e/viewport-audit.spec.ts` -- 관리자 6경로 추가(가로스크롤 없음, 그리드 열수 단언은 제외)
- `web/e2e/core-flows.spec.ts` (C6) -- 상세 라우트 2개 추가, `isSeller` 배치 단언
- `web/e2e/nav-and-hero.spec.ts` -- I/O 매트릭스 1~3행(active 표시·모바일 슬라이드인 Tab순환/Esc닫힘·리사이즈 자동닫힘) 커버 테스트 추가(구현 중 매트릭스 감사에서 누락 발견, `SiteNav.tsx` B3/B5 패턴 재사용)
- `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts` -- `BUBBLE_CLASS` 백틱 분기 추가 + 관리자 파일 스캔 추가
- `web/src/app/(admin)/admin/chats/[roomId]/page.tsx` -- 버블 스캔 대상(로직 수정 없음, 검사만 확장)
- `web/src/app/(user)/chat/page.tsx`, `chat/[roomId]/page.tsx`, `(admin)/admin/chats/page.tsx` -- DW-699 호버 신호 교체
- `web/src/app/(user)/search/page.tsx`, `components/ai/ChatAssistant.tsx`, `components/landing/PopularRecentGrid.tsx`, `(user)/ai/page.tsx` -- DW-696 잔존 `zinc-*` 치환

## Tasks & Acceptance

**Execution:**
- `web/src/components/layout/AdminSidebar.tsx` (신규) -- `SiteNav.tsx` 패턴 이식(760px, FocusTrap, matchMedia 자동닫힘), 5개 nav item + active 표시 -- 이 스토리의 본체
- `web/src/app/(admin)/layout.tsx` -- `AdminSidebar` 마운트, 레이아웃을 `flex`로 재구성(사이드바+콘텐츠) -- `AppHeader`는 미수정
- `web/e2e/viewport-audit.spec.ts` -- 관리자 6경로 추가(가로스크롤 단언만, 그리드 열수 제외) -- DW-697 ②
- `web/e2e/core-flows.spec.ts` -- C6에 `/admin/listings/[id]`·`/admin/chats/[roomId]` 추가, `isSeller` 좌우 배치 단언 -- DW-697 ③
- `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts` -- 백틱 분기 정규식 + 관리자 파일 스캔 추가, 파일별 개수 단언 -- DW-701 + DW-697 ①
- `web/src/app/(user)/chat/page.tsx`, `chat/[roomId]/page.tsx`, `(admin)/admin/chats/page.tsx` -- 죽은 호버를 다른 축 신호로 교체 -- DW-699
- `web/src/app/(user)/search/page.tsx`, `components/ai/ChatAssistant.tsx`, `components/landing/PopularRecentGrid.tsx`, `(user)/ai/page.tsx` -- `zinc-*` → 토큰 치환 -- DW-696

**Acceptance Criteria:**
- Given ≥760px 뷰포트로 관리자 6화면 아무 경로나 방문, when 렌더되면, then 고정 사이드바가 보이고 현재 경로의 nav item이 active 스타일이다.
- Given <760px 뷰포트, when 햄버거를 클릭하면, then FocusTrap 패널이 열리고 Esc 또는 바깥 클릭으로 닫히며, 열린 채 뷰포트가 760px 이상으로 커지면 자동으로 닫힌다.
- Given 관리자 6화면(목록 4 + 상세 2), when 1280/800/390px 3개 뷰포트에서 렌더하면, then 가로스크롤이 없고 배지·라벨이 두 줄로 밀리지 않는다.
- Given `npx playwright test e2e/viewport-audit.spec.ts`, when 관리자 6경로 케이스를 포함해 실행하면, then 전부 통과한다.
- Given `messageBubbleWrap.test.ts`에 관리자 파일을 포함시키고 관리자 버블에서 `break-words`를 일부러 지운 뒤 실행하면, then red가 뜨고(회귀가 실제로 잡힘), 되돌리면 green이다.
- Given `core-flows.spec.ts` C6, when 관리자 상세 라우트 2곳을 포함해 실행하면, then 통과하고 `isSeller` 기준 좌/우 배치가 단언된다.
- Given `chat/page.tsx`·`chat/[roomId]/page.tsx`·`admin/chats/page.tsx`의 행/칩, when 라이트 모드에서 마우스를 올리면, then 눈에 보이는 시각적 변화가 있다(이전엔 1.045:1로 사실상 무변화).
- Given `search/page.tsx`·`ChatAssistant.tsx`·`PopularRecentGrid.tsx`·`ai/page.tsx`, when 리스킨 후 `grep -rn "zinc-"`를 4파일에 실행하면, then 결과가 0건이다.
- Given 대시보드 허브의 기존 4개 링크와 각 상세 화면의 뒤로가기 버튼, when 사이드바 추가 후 렌더하면, then 그대로 존재하고 동작한다(제거되지 않음).

## Spec Change Log

## Review Triage Log

### 2026-08-06 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 4, low 1)
- defer: 5: (high 0, medium 1, low 4)
- reject: 4: (high 0, medium 0, low 4)
- addressed_findings:
  - `[medium]` `[patch]` `AdminSidebar.tsx`의 `/admin/listings` nav 라벨이 `'전체매물'`로 그 페이지 자신의 `<h1>`("매물 관리")과 다른 단어였다(실측: 5개 페이지 `<h1>` 전수 grep) — 리포의 기존 관례(SiteNav 링크 텍스트=도착 페이지 제목)를 어겨 클릭한 메뉴명과 화면 제목이 어긋났다. `'매물 관리'`로 교체.
  - `[medium]` `[patch]` `core-flows.spec.ts` C6의 관리자 채팅방 좌/우 배치 루프가 개별 메시지만 검사하고 판매자/그외 양쪽이 실제로 다 나왔는지는 집계하지 않아(adversarial·edge-case 두 렌즈가 독립적으로 지적), 시드 데이터가 한쪽으로 치우치면 "isSeller 기준 좌우 배치" 단언이 허수아비로 통과할 수 있었다. 루프 안에서 `sellerCount`/`otherCount`를 세어 둘 다 `toBeGreaterThan(0)`으로 단언 추가.
  - `[medium]` `[patch]` DW-699 호버 대비 수정(`hover:border-brand-petrol`)을 되돌려도 잡는 검사가 없었다 — `chat/__tests__/hoverContrast.test.ts` 신설(소스 스캔, `messageBubbleWrap.test.ts`와 동일 기법). 관리자 파일 하나를 실제로 되돌려 red 확인 → 복구해 green 확인(CLAUDE.md B4).
  - `[low]` `[patch]` 모바일 관리자 메뉴의 바깥-클릭-닫힘 로직(`SiteNav.tsx`에서 이식)에 대응하는 테스트가 없었다(SiteNav 자신은 `nav-interactions.spec.ts`가 이 축을 갖고 있음) — `nav-and-hero.spec.ts`에 `D4 [mobile 390] 패널 바깥을 클릭하면 닫힌다` 추가.
  - `[medium]` `[patch]` DW-696·697·699·701 네 항목 모두 `trigger: Story 15.2 착수 시`로 지정돼 있었고 이번 구현이 fix_sketch를 전부 실제로 구현했는데(zinc grep 0건, 관리자 뷰포트/버블/C6 테스트 추가, 호버 신호 교체, 백틱 정규식 수정), `deferred-work.md` 파일 자체는 손대지 않아 네 항목 다 `status: open`으로 남아 있었다(CLAUDE.md B8 위반 상태). 네 항목의 `status`를 `done 2026-08-06`으로 갱신하고 각각 완료 근거를 `resolution:` 줄로 추가. 다른 항목은 손대지 않음.
  - defer 5건은 대장에 신규 등재(아래 요약, 전문은 `deferred-work.md` 참조): **DW-703**(C6 관리자 버블 테스트의 "기타" 발신자 분기가 시드 데이터에 그런 발신자가 없어 한 번도 실측되지 않음) · **DW-704**(같은 테스트의 기대 클래스가 같은 렌더의 `senderLabel`에서 파생돼, buyer/seller 컬럼이 소스에서 뒤바뀌는 근본 결함이 나도 라벨과 정렬이 "같이 틀린 채" 서로 일치해 통과함) · **DW-705**(`AdminSidebar.tsx`의 리사이즈 자동닫힘이 `FocusTrap`을 언마운트할 때 트리거 버튼이 이미 `min-[760px]:hidden`이라 포커스 복귀가 실패할 수 있음 — `SiteNav.tsx`의 동일 패턴에도 있는 기존 결함) · **DW-706**(같은 컴포넌트의 바깥-클릭-닫힘이 `pointerdown` 상태변경과 `FocusTrap`의 `focusin` 재포착 사이 경합으로 클릭한 요소가 아니라 햄버거 버튼에 포커스가 남을 수 있음 — 역시 `SiteNav.tsx`에서 이식된 기존 결함) · **DW-707**(`fetchChatRoomIdForSeedUser`가 "buyer·seller 메시지가 둘 다 있다"는 전제를 코드로 강제하지 않고 주석으로만 적어 둠 — 시드 데이터가 바뀌면 이 전제에 기대는 테스트들이 조용히 약해짐).
  - 기각 4건(근거 확인 후 실제 결함 아님으로 판정): 사이드바가 `sticky top-0`이고 `AppHeader`는 아니라 스크롤 시 헤더만 사라지고 사이드바가 남는다는 지적(Vercel·Stripe·GitHub 설정 화면 등에서도 흔한 정상 패턴이고, 인텐트가 명시한 제약을 어기지 않으며 콘텐츠를 가리지도 않는다) · deferred-work.md의 DW-696/699 대상 파일(관리자 밖 4개 소비자 화면)이 인텐트 슬러그("관리자-반응형")만 보면 범위 밖으로 보인다는 지적(이 스펙의 `<intent-contract>` Always가 명시적으로 그 4파일·3파일을 포함시켰고, 근거는 대장의 기존 트리거 지정이다 — 스코프 권위는 인텐트 본문이지 슬러그가 아니다) · viewport-audit의 "가로스크롤 없음"이 "반응형이 잘 됐다"는 체감을 다 증명하진 못한다는 지적(스펙의 Block If가 정확히 그 위험을 좁은 구간의 줄바꿈 여부로 실측하도록 이미 겨냥하고 있고, 이번 실행에서 그 조건은 트리거되지 않았다) · 스펙 본문이 "관리자 6화면"이라 쓰고 실제 viewport-audit 루프는 대시보드 포함 5경로+상세 2로 7경로를 도는 수 불일치(더 넓게 도는 방향의 불일치라 커버리지 손실이 없고, `<intent-contract>`는 이 워크플로에서 수정 불가 영역이라 고칠 방법도 없다).

### 2026-08-06 — Review pass (후속)
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 5, low 5)
- defer: 4: (high 0, medium 0, low 4)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` **같은 커밋이 DW-699로 "죽었다"고 판정한 호버 조합을 DW-696 치환이 다시 심었다.** `search/page.tsx`의 페이저 칩이 `hover:bg-zinc-100 dark:hover:bg-zinc-800` → `hover:bg-surface-raised`로 바뀌었는데, 이 칩은 카드가 아니라 body 배경(#FAFAF8) 위에 바로 놓여 호버가 #FFFFFF로 가도 대비 1.045:1이고, 다크 호버는 대응 클래스가 사라져 신호가 0이 됐다. `hover:border-brand-petrol`로 교체(라이트 4.69:1 · 다크 3.88:1, 아래 실측).
  - `[low]` `[patch]` 그 위반을 신설 가드가 **구조적으로 못 봤다** — `hoverContrast.test.ts`가 대상 3파일 하드코딩 + 큰따옴표 전용 정규식이라, 작은따옴표 `const`로 뽑힌 페이저 클래스는 파일을 넣어도 0건 매치였다. 작은따옴표 분기 추가 + `search/page.tsx` 편입 + 빈 스캔 시 루프가 통째로 건너뛰어 초록이 되는 문제에 명시적 전제 단언 추가. 되돌려 red 확인 → 복구해 green 확인.
  - `[medium]` `[patch]` **D3(리사이즈 자동닫힘) 테스트가 실패할 수 없었다.** 모바일 컨테이너가 `min-[760px]:hidden`이라 900px에서는 display:none이 되고, matchMedia 자동닫힘을 통째로 지워도 (a)햄버거는 안 보이고 (b)회원관리는 데스크톱 것 하나만 잡혀 두 단언이 CSS만으로 충족됐다. 다시 390px로 되돌려 `aria-expanded`와 패널 링크 부재를 확인하도록 보강 — 자동닫힘을 제거해 red 확인 → 복구해 green 확인.
  - `[medium]` `[patch]` **관리자 뷰포트 감사가 이 스토리의 Block If를 볼 수 없는 단언만 갖고 있었다.** 인수조건은 "가로스크롤 없음 **+ 배지·라벨이 두 줄로 안 밀림**"이고 Block If는 회원 행 줄바꿈인데, 줄바꿈은 오히려 가로스크롤을 없애는 방향이라 `assertNoHorizontalOverflow`만으로는 반대로 움직인다. 이 파일의 다른 describe 전부가 쓰는 `assertSingleLine`을 회원 행에 추가 — 행을 세로 배치로 바꿔 red 확인(800px) → 복구해 green 확인.
  - `[medium]` `[patch]` **`AdminSidebar`를 CI가 검사하지 않았다.** 이 컴포넌트를 덮는 단언이 전부 E2E인데 E2E는 CI에서 안 돈다(project-context §12). 원본 `SiteNav.tsx`는 같은 축을 CI에서 도는 `SiteNav.test.ts`로 고정해 두고 있었고, 5개 라벨 중 `매물 관리`·`거래내역`은 E2E 포함 **어떤 검사도 이름을 부르지 않았다**(실측 grep 0건). 같은 기법의 `AdminSidebar.test.ts` 신설(라벨·href 5쌍, 목적지 개수, 760px CSS/JS 일치, 44px 히트영역, w-60) — 라벨 하나와 브레이크포인트 하나를 깨서 red 확인 → 복구해 green 확인.
  - `[low]` `[patch]` `isActiveHref`의 `startsWith` 분기(이 함수가 단순 일치가 아닌 **유일한 이유**)를 지나는 단언이 없었다 — 목록 경로만 보는 D1은 `pathname === href`로 되돌려도 초록이었다. 상세 라우트 active + `/admin` 정확일치 예외를 D1에 추가, 되돌려 red 확인 → 복구해 green 확인.
  - `[medium]` `[patch]` **D4가 무작위 좌표(`mouse.click(200,700)`)를 쳤다.** 그 좌표가 무엇 위에 떨어지는지 아무 보장이 없는데, 이 화면의 `MemberActions` 정지 버튼은 확인창 없이 즉시 `profiles`를 UPDATE한다 — 시드 회원 수·행 높이가 바뀌면 "DB에 쓰지 않는다"고 선언한 스펙이 시드 계정을 정지시키고 이후 로그인 테스트가 엉뚱한 이유로 깨진다. 확실히 비활성인 상단바 이메일 텍스트를 치도록 교체 + "닫힘"과 "이동해서 사라짐"을 구분하는 URL·`aria-expanded` 가드 추가.
  - `[low]` `[patch]` 관리자 뷰포트 감사에 "관리자 화면이 실제로 그려졌는지" 확인이 없어, 세션 만료·권한 회귀로 전부 `/login`으로 튕겨도 로그인 화면엔 가로스크롤이 없어 7개 단언이 모두 통과했다(C6은 같은 위험을 에러 문구+행 수로 막고 있었다). 경로 유지 단언 추가.
  - `[low]` `[patch]` 스펙의 마지막 인수조건("허브 4링크·상세 뒤로가기가 사이드바 추가 후에도 그대로")을 보는 검사가 없었다 — 사이드바가 생겼으니 허브 버튼은 중복이라며 지우는 건 다음 사람에게 자연스러운 판단인데, 지워도 전 스위트가 초록이다. `D1b` 신설.
  - `[low]` `[patch]` DW-699의 완료 기준("바꾼 뒤 실제 델타를 **숫자로** 적는다 — 눈으로 닫지 않는다")이 안 지켜져 세 곳 주석이 전부 **옛** 값(1.045:1)만 반복했다. WCAG relative luminance로 새 신호를 실측해 기록: 라이트 `#E6E3DD→#1E6E6A` = **4.69:1**(옛 1.045:1 대비 4.5배), 다크 `#3B3934→#4FA39D` = **3.88:1**(옛 1.147:1 대비 3.4배).
  - defer 4건 신규 등재(전문은 `deferred-work.md`): **DW-708**(`zinc-*` 금지 규칙에 실행 가드가 없다 — DW-696이 그 판단을 열린 질문으로 적어 뒀는데 답도 이월도 없이 닫혔다) · **DW-709**(`BUBBLE_CLASS` 백틱 분기에 앵커가 없어 인접 템플릿 리터럴 사이를 가로질러 매치될 수 있다) · **DW-710**(`ACTIVE_LINK_CLASS`만 호버 반응이 없어 현재 항목이 죽은 컨트롤로 보인다) · **DW-711**(Block If가 건 640~1099px "구간"이 이산점 3개로만 표본화돼, 사이드바가 살아 있는 가장 좁은 760~800 경계가 미관측).
  - 기각 8건: AppHeader 잔존 원시색·헤더/사이드바 테두리 이음매(인텐트 Never가 `AppHeader.tsx` 수정을 금지하고 [[DW-695]]가 그 자리를 이미 갖고 있다) · 사이드바 때문에 헤더와 본문 중앙정렬이 어긋난다(인텐트가 지정한 레이아웃의 직접 결과이며, 사이드바 이전에도 헤더는 full-width·main은 `mx-auto`라 같은 축의 차이가 이미 있었다) · frontmatter/sprint-status 상태 불일치(이 finalize 단계가 처리하는 워크플로 기록이지 결함이 아니다) · `SiteNav` 로직을 추출하지 않고 복제했다(인텐트 Approach가 "이식"을 명시적으로 지시했다) · 나머지 4개 라벨의 띄어쓰기가 도착 페이지 `<h1>`과 다르다(인텐트가 라벨 문자열을 직접 지정했고 차이는 공백 하나다) · `AdminSidebar`의 `LINK_CLASS` `hover:bg-surface-base`가 죽은 대비다(같은 클래스에 `hover:text-ink-primary`가 함께 있어 글자색 축의 신호가 살아 있다 — active 항목만 호버가 아예 없는 별건은 DW-710으로 등재) · C6 주석의 `[desktop]` 표기와 실제 프로젝트 스코프 불일치(기존·무해하며 더 넓게 도는 방향) · DW-705/706 재지적(이미 대장에 등재됨).

### 2026-08-06 — Review pass (3차)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 1, medium 4, low 3)
- defer: 4: (high 0, medium 0, low 4)
- reject: 11: (high 0, medium 0, low 11)
- addressed_findings:
  - `[high]` `[patch]` **2차가 Block If를 보라고 새로 건 `assertSingleLine`이 여전히 그 실패 모드를 볼 수 없었다 — 대상도 표본도 틀렸다.** (가) 재던 것은 `li` 안 첫 `span`(라벨 묶음)인데 그 안은 `truncate`(=`whitespace-nowrap`)라 **구조적으로 두 줄이 될 수 없다**. Block If가 말하는 것은 "배지+액션 조합이 줄바꿈됨" = 행(`li`) 자체가 두 줄이 되는 것이다. 실측: `li`에 `flex-wrap`, 액션 div에 `basis-full`을 넣어 액션을 아랫줄로 내려도 라벨 span 높이는 그대로라 green이었고, 줄바꿈은 가로스크롤을 오히려 없애므로 옆의 `assertNoHorizontalOverflow`도 green이었다(세 렌즈가 각각 독립적으로 돌연변이로 확인). (나) 회원 목록은 가입일 오름차순이고 본인 행엔 `MemberActions`를 렌더하지 않아, `.first()`는 "가장 많은 요소가 든 행"이라는 주석과 달리 **액션 버튼이 없는 가장 헐거운 행**을 고를 수 있었다. → `li`를 직접 재고, 액션 버튼을 실제로 가진 행을 고르도록 교체. 같은 돌연변이로 red 확인 → 원복 green.
  - `[medium]` `[patch]` **`AdminSidebar.test.ts`가 라벨과 href를 쌍으로 고정하지 못했다** — 주석은 "쌍으로 고정한다"고 적었는데 구현은 `toContain(href)`와 `toContain(label)`을 **따로** 건 두 단언이라, 두 항목의 href를 서로 바꿔치면 5개 라벨도 5개 href도 그대로 존재해 9/9 green이었다(세 렌즈가 각각 돌연변이로 확인). 메뉴 이름과 도착 화면이 어긋나는 것은 이 파일이 존재하는 이유 그 자체다. 렌더된 `<a>`를 `[라벨, href]` 튜플로 뽑아 순서까지 `toEqual`로 비교하도록 교체.
  - `[medium]` `[patch]` **측정값 단언을 주석이 대신 충족하고 있었다.** `toContain('w-60')`·`toContain('h-11 w-11')`이 파일 원문을 봤는데, 이 컴포넌트의 주석이 자기 값을 설명하느라 `240px = w-60`·`히트영역 44×44px(h-11 w-11)`라고 **문자 그대로** 적어 둔다 — 실제 className에서 지워도 주석이 단언을 충족해 green이었다(실측: `w-60`→`w-96`, `h-11 w-11`→`h-8 w-8`로 9/9 통과). 이 파일이 지키려는 두 숫자(240px 폭·44px 접근성 히트영역)가 무방비였다. 주석을 걷어낸 코드만 스캔하도록 교체(줄 주석을 **먼저** 지운다 — `// ... /admin/* ...`처럼 줄 주석 안의 `/*`가 블록 주석 시작으로 잡혀 30줄이 통째로 날아가는 것을 실제로 겪었다).
  - `[medium]` `[patch]` **이 스토리의 본체(데스크톱에서 사이드바를 콘텐츠 *옆에* 놓기)를 어떤 검사도 안 봤다.** 그 배치를 만드는 것은 `(admin)/layout.tsx`의 `min-[760px]:flex` 하나인데 `AdminSidebar.test.ts`는 `AdminSidebar.tsx`만 읽는다 — 래퍼를 통째로 지우면 사이드바가 콘텐츠 **위에 전폭으로 쌓이는데도**(스토리의 시각적 결과가 사라지는데도) vitest 340건·E2E 48건이 전부 green이었다(두 렌즈가 각각 돌연변이로 확인, 전폭으로 쌓이면 가로스크롤도 안 생겨 viewport-audit도 못 본다). 브레이크포인트 일치 스캔을 두 파일 합산으로 넓히고, flex 래퍼·콘텐츠 `min-w-0 flex-1`을 직접 고정하는 검사를 추가. 래퍼를 지워 red 확인 → 원복 green.
  - `[medium]` `[patch]` **2차의 호버 대비 patch가 비활성 컨트롤에 가짜 신호를 심었다.** `search/page.tsx`의 `pagerLinkClass`를 `hover:border-brand-petrol`(1.045:1 → 4.69:1)로 고쳤는데, 그 상수를 첫/끝 페이지의 **비활성** `<span aria-disabled>` 두 곳이 함께 쓰고 있었다 — 눌러도 아무 일이 없는 자리가 눈에 띄게 반짝이게 됐다. 호버가 사실상 안 보이던 때는 드러나지 않던 문제라, 대비를 고친 그 patch가 만들어낸 결과다. 활성/비활성 상수를 분리. (회귀 가드는 기존 `hoverContrast.test.ts`의 개수 단언이 이미 잡는다 — 비활성 쪽에 호버를 되돌리면 스캔이 2건이 돼 red, 실측 확인.)
  - `[low]` `[patch]` `AdminSidebar.test.ts`의 링크 개수 세기가 `/href="\/admin[^"]*"/`라 **`/admin`으로 시작하지 않는 링크를 추가해도** 개수가 5로 유지됐다 — "추가·삭제 둘 다 잡는다"는 이름과 달리 추가를 못 잡았다. 위 튜플 비교로 흡수.
  - `[low]` `[patch]` **2차가 추가한 "경로 바뀌면 패널 닫기"를 지나는 검사가 하나도 없었다.** 이건 원본 `SiteNav.tsx`엔 **없는** 동작이라(거기는 `usePathname`을 안 쓴다) 이식 대칭성으로도 안 덮이고, 패널 안 링크는 각자 `onClick`으로 닫으므로 D2·D4는 그 줄을 지워도 초록이며, `AdminSidebar.test.ts`는 라우터 밖 1회 렌더라 구조적으로 볼 수 없다. `nav-and-hero.spec.ts`에 D5 신설. **처음 쓴 D5가 실패할 수 없어 한 번 더 고쳤다** — `page.goto()` 두 번은 각각 문서 전체 로드라 뒤로가기도 문서 로드가 되고 컴포넌트가 새로 마운트돼 `menuOpen`이 초기값으로 돌아갔다(자동닫힘을 통째로 지워도 green이었다). 앱 안 링크를 눌러 클라이언트 내비게이션으로 이동하도록 바꾼 뒤 red 확인 → 원복 green.
  - `[low]` `[patch]` 2차가 추가한 "관리자 경로에 머물렀나" 가드가 **목록 루프 안에만** 걸려 있어, 정작 이 스토리가 새로 추가한 상세 2경로는 여전히 무방비였다(세션 만료·권한 회귀로 `/login`에 튕겨도 로그인 화면엔 가로스크롤이 없어 통과). 경로 유지 + 에러 문구 부재를 함께 확인하도록 추가. 없는 id로 바꿔 red 확인. (`getByRole('alert')`는 쓸 수 없었다 — Next dev의 route announcer가 빈 `role="alert"`를 항상 하나 심어 둬 어떤 화면에서도 0이 되지 않는다. 실측으로 확인하고 C6과 같은 에러 문구 방식으로 바꿨다.)
  - defer 4건 신규 등재(전문은 `deferred-work.md`): **DW-712**(`hoverContrast.test.ts`에 백틱 분기가 없다 — 같은 커밋의 `messageBubbleWrap`이 DW-701로 배운 교훈이 형제 가드엔 안 왔다) · **DW-713**(그 가드의 대상이 여전히 손으로 적은 4파일 목록이다 — 주석은 "이 클래스 조합을 쓰는 곳 전부"라고 적었고, 실제 위반이 한 번 그 틈으로 들어온 적이 있다) · **DW-714**(모바일 관리자 패널이 열린 채 페이지가 스크롤돼, 포커스는 갇혔는데 갇힌 패널이 화면 밖으로 나갈 수 있다 — `SiteNav`에서 이식된 구조, DW-705·706과 같은 계열이나 축이 다르다) · **DW-715**(I/O 매트릭스가 지목한 `/admin/listings/[id]` @390의 "두 줄 안 됨"을 아무도 재지 않는다 — 단일행 단언은 회원관리에만 걸렸다).
  - 기각 11건: `AdminSidebar`의 `hover:bg-surface-base` 죽은 대비 재지적(2차에서 같은 근거로 기각 — `hover:text-ink-primary`가 함께 있어 글자색 축 신호가 살아 있고, active 항목 전용 별건은 이미 DW-710) · DW-699 수치가 WCAG 1.4.11(지시자 대 인접 배경)이 아니라는 지적(인수조건은 "눈에 보이는 변화"이고 기록된 4.69:1은 옛 테두리색↔새 테두리색 델타로 그 질문에 정확히 답한다) · DW-708·DW-711 본문의 정확성 지적 2건(이미 등재된 기존 항목이며, 이 리뷰는 신규 등재만 하고 기존 항목의 상태·본문은 건드리지 않는다 — 오케스트레이터 소관) · `review_loop_iteration: 0`이 두 패스 뒤에도 0이라는 지적(이 카운터는 bad_spec 루프백에서만 증가하고 `done` 스펙의 새 리뷰 진입 시 0으로 리셋되는 것이 워크플로 정의다 — 값이 정확하다) · `h-fit` 때문에 `border-r`가 중간에 끊긴다는 지적(`sticky top-0`이 동작하려면 필요한 조합이고, 인텐트의 "고정 사이드바(240px, sticky)"를 어기지 않는다) · `ADMIN_USER` 상수가 e2e 3파일에 중복(2파일 중복은 이 스토리 이전부터 있던 기존 패턴이고 무해하다) · `hoverContrast`가 `hover:border-brand-petrol`만 요구해 인텐트가 대안으로 허용한 `hover:underline`을 배제한다는 지적(가드는 채택된 구현을 고정하는 것이 목적이며, 대안으로 바꾸려면 가드도 함께 고치는 것이 정상 절차다) · `hoverContrast.test.ts`가 chat 폴더에 있다는 위치 지적(파일을 옮겨도 대상 목록이 손목록인 한 실패 모드는 그대로다 — 실질 축인 전역 스캔 전환을 DW-713으로 등재했다) · 라벨 `전체매물`→`매물 관리` 이탈(1차 패스가 도착 페이지 `<h1>` 일치 근거로 이미 patch 처리) · "관리자 6화면"인데 7경로를 돈다는 수 불일치(1차에서 같은 근거로 기각 — 더 넓게 도는 방향이라 커버리지 손실이 없다).

## Design Notes

- **브레이크포인트를 두 축으로 분리한다.** D5의 1100/640은 "그리드 열수"를 위한 것이고, 사이드바 붕괴는 "내비 셸 표시 방식"이라 `SiteNav.tsx`가 이미 검증해 둔 760px을 그대로 쓴다. 두 축을 하나로 합치면(예: 1100px에서 사이드바를 접음) 관리자 화면에 그리드가 없다는 사실과 무관하게 불필요한 결합이 생긴다.
- **`AppHeader.tsx`를 피하는 것은 의도적 설계 결정이다.** 사이드바 상태(열림/닫힘)는 클라이언트 컴포넌트가 필요한데, `AppHeader`는 서버 컴포넌트다. `SiteNav`가 소비자 쪽에서 그랬듯 `AdminSidebar`를 완전히 독립된 클라이언트 컴포넌트로 두면 `AppHeader` 자체를 바꿀 필요가 없다 — 이는 15.1이 같은 이유로 `AppHeader`를 범위 밖에 둔 것과 같은 판단이며, DW-695(AppHeader 잔존 zinc)를 이번에 우연히 건드리지 않기 위한 목적도 겸한다.
- DW-699 호버 수정은 "새 토큰 추가"(옵션 ①)보다 "다른 축 신호로 대체"(옵션 ②, `hover:border-brand-petrol` 등)를 기본으로 삼는다 — 토큰 추가 없이 되는 더 싼 경로이기 때문이다(fix_sketch 원문 권고와 동일).

## Verification

**Commands:**
- `cd web && npx tsc --noEmit` -- expected: 타입 에러 0
- `cd web && npm run lint` -- expected: 에러 0
- `cd web && npm run test` -- expected: 기존+신규 vitest 전부 통과(`messageBubbleWrap` 포함)
- `cd web && npx playwright test e2e/viewport-audit.spec.ts e2e/core-flows.spec.ts e2e/nav-and-hero.spec.ts` -- expected: 전부 통과(로컬 Supabase 컨테이너 필요 — CI 로컬 재현 절차 참고)
- `cd web && grep -rn "zinc-" "src/app/(user)/search/page.tsx" "src/components/ai/ChatAssistant.tsx" "src/components/landing/PopularRecentGrid.tsx" "src/app/(user)/ai/page.tsx"` -- expected: 결과 0건

**Manual checks (if no CLI):**
- 다크 모드에서 사이드바(데스크톱)·모바일 슬라이드인 패널·DW-699 호버 신호를 육안 확인.

## Auto Run Result

Status: done

**요약**: 관리자 6화면에 반응형 사이드바 내비 셸(데스크톱 고정 사이드바 + 모바일 햄버거/슬라이드인, `SiteNav.tsx` 패턴 이식)을 추가하고, D5 반응형 무결성을 관리자 경로에서 실측으로 검증하는 자동 검사(뷰포트 가로스크롤 감사, 상세 라우트 좌/우 배치, 말풍선 줄바꿈 계약)를 신설했다. 15.1 후속 리뷰가 "Story 15.2 착수 시" 처리하도록 지정해 둔 DW-696·697·699·701(잔여 zinc 토큰·검사 공백 3종·죽은 호버·정규식 결함) 네 건을 함께 닫았다.

**파일 변경**:
- `web/src/components/layout/AdminSidebar.tsx` (신규) — 데스크톱 고정 사이드바 + 모바일 햄버거/FocusTrap 슬라이드인, 5개 nav item, active 표시.
- `web/src/app/(admin)/layout.tsx` — `AdminSidebar` 마운트(flex 레이아웃), `AppHeader`는 미수정.
- `web/e2e/viewport-audit.spec.ts` — 관리자 6경로 가로스크롤 감사 추가(DW-697 ②).
- `web/e2e/core-flows.spec.ts` — C6에 상세 라우트 2개 + `isSeller` 좌/우 배치 단언(양쪽 최소 1건 집계 포함, 코드리뷰 patch) 추가(DW-697 ③).
- `web/e2e/nav-and-hero.spec.ts` — `spec-15-2 관리자 사이드바` describe에 D1(active 표시)·D2(Tab순환/Esc닫힘)·D3(리사이즈 자동닫힘)·D4(바깥클릭 닫힘, 코드리뷰 patch) 4건 추가.
- `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts` — 백틱 템플릿 리터럴 분기 추가 + 관리자 버블 스캔 신설(DW-701, DW-697 ①).
- `web/src/app/(user)/chat/page.tsx`, `chat/[roomId]/page.tsx`, `(admin)/admin/chats/page.tsx` — 죽은 호버(`hover:bg-surface-*`, 대비 1.045:1)를 `hover:border-brand-petrol`로 교체(DW-699).
- `web/src/app/(user)/chat/__tests__/hoverContrast.test.ts` (신규, 코드리뷰 patch) — 위 호버 교체가 되돌려지지 않도록 소스 스캔 가드.
- `web/src/app/(user)/search/page.tsx`, `components/ai/ChatAssistant.tsx`, `components/landing/PopularRecentGrid.tsx`, `(user)/ai/page.tsx` — 잔존 `zinc-*` 14건을 토큰으로 치환(DW-696).
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-696·697·699·701 상태를 `done 2026-08-06`으로 갱신(코드리뷰 patch), DW-703~707 신규 등재(defer 라우팅).

**리뷰 결과**: adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 렌즈 병렬 실행. patch 5(medium 4, low 1) 전부 적용·재검증 완료. defer 5건(DW-703~707) 등재 — 전부 `SiteNav.tsx`에서 이식된 기존 패턴의 잠재 결함이거나 시드 데이터 의존적 커버리지 공백으로, 이 스토리가 새로 만든 결함은 아님. reject 4건(사이드바 sticky 레이아웃, 스코프 권위 오해, D5 검증의 인식론적 한계, 6/7 경로 수 표현 불일치) — 근거 확인 후 실제 결함 아님.

**검증 수행**: `npx tsc --noEmit`(0 에러) · `npm run lint`(0 에러) · `npm run test`(36 files, 328 tests 전부 통과) · `npx playwright test e2e/viewport-audit.spec.ts e2e/core-flows.spec.ts e2e/nav-and-hero.spec.ts --workers=2`(47 passed, 52 skipped(project-scoped), 0 failed) · `grep -rn "zinc-"` 4개 대상 파일(0건) — 전부 오케스트레이터가 직접 재실행해 독립 확인(서브에이전트 보고에만 의존하지 않음). I/O 매트릭스 4행 전부 통과 테스트로 커버됨(데스크톱 active=D1, 모바일 Tab순환/Esc닫힘=D2, 리사이즈 자동닫힘=D3, D5 가로스크롤=viewport-audit 관리자 스위트). red/green 자체 검증 2건 수행: (1) 신설 D1 테스트의 `aria-current` 배선을 실제로 끊어 red 확인 → 복구해 green 확인, (2) 신설 hoverContrast 테스트를 관리자 버블에서 되돌려 red 확인 → 복구해 green 확인.

**잔여 위험**: DW-703~707(모두 low, 상세는 `deferred-work.md` 참조) — 시드 데이터 편향 2건, `SiteNav.tsx`에서 이식된 포커스 관리 기존 결함 2건, 헬퍼 전제 미검증 1건. 모두 이 스토리가 새로 만든 문제가 아니고 현재 시드 데이터·기능으로는 재현되지 않는다.

---

## 후속 리뷰 패스 (2026-08-06, 2차)

**왜 한 번 더 돌았나**: 1차 패스가 `followup_review_recommended: true`로 닫혀 있었다. 2차는 같은 4개 렌즈를 새 세션(사전 맥락 없음)으로 병렬 실행했다.

**무엇이 더 나왔나 (patch 10건, 전부 적용·재검증)**: 1차가 못 본 축은 두 갈래였다.
1. **새로 만든 검사들이 정작 실패할 수 없었다.** D3(리사이즈 자동닫힘)은 기능을 통째로 지워도 CSS(`min-[760px]:hidden`)가 두 단언을 대신 충족해 초록이었고, D1은 `isActiveHref`를 단순 일치로 되돌려도 초록이었으며, 관리자 뷰포트 감사는 이 스토리 Block If의 실패 모드(줄바꿈)가 오히려 그 단언을 **만족시키는** 방향이라 구조적으로 못 봤다. 셋 다 실제로 깨서 red를 확인한 뒤 보강했다.
2. **규칙을 만든 커밋이 같은 커밋 안에서 그 규칙을 어겼고, 규칙의 가드가 그 자리를 못 봤다.** DW-696 토큰 치환이 `search/page.tsx` 페이저에 DW-699가 "죽었다"고 판정한 호버 조합을 새로 심었는데, 신설 `hoverContrast.test.ts`는 대상 3파일 하드코딩 + 큰따옴표 전용 정규식이라 그 자리를 볼 수 없었다. 클래스를 고치고 가드를 그 자리까지 넓혔다.
   추가로 `AdminSidebar`는 **CI가 한 번도 검사하지 않는 상태**였다(덮는 단언이 전부 로컬 전용 E2E). 원본 `SiteNav.tsx`에는 CI에서 도는 `SiteNav.test.ts`가 있는데 이식하면서 가드는 안 왔고, 5개 라벨 중 2개는 어떤 검사도 이름을 부르지 않았다 — `AdminSidebar.test.ts`를 신설했다.

**추가 파일 변경**:
- `web/src/components/layout/AdminSidebar.test.ts` (신규) — CI에서 도는 렌더 계약 검사(라벨·href 5쌍, 목적지 개수, 760px CSS/JS 일치, 44px 히트영역, w-60).
- `web/src/components/layout/AdminSidebar.tsx` — 경로 변경 시 모바일 패널을 닫는다(뒤로가기로 화면이 바뀌어도 이전 메뉴가 덮여 있던 문제). lint(`react-hooks/set-state-in-effect`) 때문에 이펙트가 아니라 React 공식의 "렌더 중 상태 조정" 패턴을 썼다.
- `web/src/app/(user)/search/page.tsx` — 페이저 호버를 `hover:border-brand-petrol`로 교체 + 실측 수치 기록.
- `web/src/app/(user)/chat/__tests__/hoverContrast.test.ts` — 작은따옴표 분기, `search/page.tsx` 편입, 빈 스캔 방어.
- `web/e2e/nav-and-hero.spec.ts` — D1에 상세 라우트 active 단언, D1b 신설(허브 4링크·뒤로가기 보존), D3에 모바일 복귀 후 상태 확인, D4의 무작위 좌표 클릭 제거.
- `web/e2e/viewport-audit.spec.ts` — 관리자 스위트에 경로 유지 가드 + 회원 행 `assertSingleLine`.

**2차 검증 수행**(전부 오케스트레이터가 직접 실행·관찰): `npx tsc --noEmit`(0) · `npm run lint`(0) · `npm run test`(37 files, **340 tests** 통과 — 1차 328에서 +12) · `npx playwright test e2e/viewport-audit.spec.ts e2e/core-flows.spec.ts e2e/nav-and-hero.spec.ts --workers=2`(**48 passed, 54 skipped, 0 failed**) · `grep -rn "zinc-"` 4개 대상 파일(0건 — 중간에 patch 주석이 이 문자열을 재도입해 인수조건을 깨뜨린 것을 발견하고 문구를 고쳤다).
**red/green 자체 검증 5건**(CLAUDE.md B4): ① `search` 페이저 호버를 되돌려 red → 복구 green, ② `AdminSidebar` 라벨 1개 + 브레이크포인트 1개를 깨서 red → 복구 green, ③ matchMedia 자동닫힘을 제거해 D3 red → 복구 green, ④ 회원 행을 세로 배치로 바꿔 800px에서 `assertSingleLine` red → 복구 green, ⑤ `isActiveHref`를 단순 일치로 되돌려 D1 red → 복구 green.

**잔여 산출물**: 이 스펙 파일 자체가 커밋(`baad7c4`) 이후 한 줄 수정된 상태로 남는다 — `final_revision`은 커밋이 만들어진 **뒤에야** 알 수 있는 값이라 구조적으로 그 커밋에 담길 수 없다(1차 패스도 같은 상태로 끝났다). 다음 커밋에 자연히 실린다.

**2차 잔여 위험**: DW-708~711(전부 low) — 색 토큰 규칙의 실행 가드 부재, 버블 정규식 앵커, active 항목 호버 부재, 760~800 경계 미표본. 넷 다 현재 화면·시드로는 재현되지 않으며, 각각 다시 볼 시점을 `trigger:`로 지정해 대장에 등재했다.

---

## 후속 리뷰 패스 (2026-08-06, 3차)

**왜 한 번 더 돌았나**: 2차 패스가 `followup_review_recommended: true`로 닫혀 있었다. 3차도 같은 4개 렌즈를 새 세션(사전 맥락 없음)으로 병렬 실행했다.

**무엇이 더 나왔나 (patch 8건, 전부 적용·재검증)**: 3차가 찾은 것은 거의 전부 **2차가 만든 수리 그 자체의 결함**이었다. 2차는 "새로 만든 검사들이 정작 실패할 수 없었다"를 주제로 닫았는데, 그때 새로 만든 검사들이 다시 같은 병을 앓았다. 그리고 이번엔 세 렌즈가 **논증이 아니라 돌연변이 실행**으로 증명했다 — 코드를 실제로 깨뜨린 뒤 전 스위트가 초록으로 남는 것을 관측했다.

1. **Block If를 보라고 만든 단언이 여전히 Block If를 못 봤다.** 2차가 회원 행에 건 `assertSingleLine`은 행이 아니라 그 안의 라벨 묶음을 재고 있었고, 그 묶음은 `truncate`라 구조적으로 두 줄이 될 수 없다. 행을 실제로 줄바꿈시켜도 48건 전부 green이었다. 게다가 고른 행은 "요소가 가장 많은 행"이라는 주석과 달리 액션 버튼이 없는 본인 행일 수 있었다(가입일 오름차순 + 본인 행 액션 미렌더).
2. **스토리의 본체를 지우면 340건이 전부 초록이었다.** 사이드바를 콘텐츠 옆에 놓는 것은 `(admin)/layout.tsx`의 flex 래퍼 하나인데, 2차가 만든 `AdminSidebar.test.ts`는 컴포넌트 파일만 읽는다. 래퍼를 지우면 사이드바가 콘텐츠 위에 전폭으로 쌓이고 — 전폭이니 가로스크롤도 안 생겨 — vitest도 E2E도 뷰포트 감사도 아무것도 못 봤다.
3. **그 `AdminSidebar.test.ts` 자신도 두 군데가 못 잡았다.** 라벨↔href를 "쌍으로 고정한다"고 주석에 적고 실제로는 따로 검사해 두 항목의 목적지를 맞바꿔도 9/9 초록이었고, 240px·44px 두 숫자는 **컴포넌트 주석이 그 값을 문자 그대로 적어 둬서** className에서 지워도 주석이 단언을 대신 충족했다.
4. **대비를 고친 patch가 비활성 컨트롤에 가짜 신호를 심었다.** 2차가 눈에 띄게 만든 페이저 호버 클래스를 첫/끝 페이지의 비활성 span이 함께 쓰고 있었다 — 호버가 안 보이던 시절엔 드러나지 않던 문제다.

**추가 파일 변경**:
- `web/src/components/layout/AdminSidebar.test.ts` — 링크를 `[라벨, href]` 튜플로 비교(쌍·순서·개수 동시 고정), 주석 제거 후 측정값 스캔, `(admin)/layout.tsx`까지 브레이크포인트 합산 + flex 래퍼·`min-w-0 flex-1` 고정 검사 신설.
- `web/e2e/viewport-audit.spec.ts` — 단일행 단언을 행(`li`) 자체 + 액션 버튼을 가진 행으로 교체, 상세 2경로에 경로 유지·에러 문구 부재 가드 추가.
- `web/e2e/nav-and-hero.spec.ts` — D5 신설(패널을 연 채 뒤로가기 → 클라이언트 내비게이션으로 경로만 바뀔 때 패널이 닫히는지).
- `web/src/app/(user)/search/page.tsx` — 페이저의 활성/비활성 클래스 분리(비활성에서 호버 신호 제거).

**3차 검증 수행**(전부 오케스트레이터가 직접 실행·관찰): `npx tsc --noEmit`(0) · `npm run lint`(0) · `npm run test`(37 files, **336 tests** 통과 — 2차 340에서 −4는 라벨 `it.each` 5건을 튜플 비교 1건으로 합치고 레이아웃 검사 1건을 더한 결과) · `npx playwright test e2e/viewport-audit.spec.ts e2e/core-flows.spec.ts e2e/nav-and-hero.spec.ts --workers=2`(**49 passed, 56 skipped, 0 failed** — 2차 48에서 D5 신설로 +1) · `grep -rn "zinc-"` 4개 대상 파일(0건).
**red/green 자체 검증 5건**(CLAUDE.md B4): ① 회원 행에 `flex-wrap`+`basis-full`을 넣어 액션을 아랫줄로 내려 800px에서 red → 원복 green(패치 전엔 이 돌연변이가 green이었다), ② `AdminSidebar` 두 항목의 href를 맞바꿔 red → 원복 green, ③ className의 `w-60`·`h-11 w-11`을 바꿔 red(주석엔 그 문자열이 그대로 남은 채) → 원복 green, ④ `(admin)/layout.tsx`의 flex 래퍼를 제거해 red → 원복 green, ⑤ 경로변경 자동닫힘을 제거해 D5 red → 원복 green. 추가로 상세 라우트를 없는 id로 바꿔 새 렌더 가드가 red가 되는 것을 확인했다.

**3차에서 스스로 잡은 것**: 처음 쓴 D5가 **실패할 수 없었다**. `page.goto()` 두 번은 각각 문서 전체 로드라 뒤로가기도 문서 로드가 되고 컴포넌트가 새로 마운트돼 상태가 초기화된다 — 자동닫힘을 통째로 지워도 초록이었다. 앱 안 링크를 눌러 클라이언트 내비게이션으로 이동하도록 고친 뒤에야 red가 났다. 이번 패스가 지적한 병을 이번 패스가 한 번 더 앓은 셈이라, 기록으로 남긴다.

**3차 잔여 위험**: DW-712~715(전부 low) — 호버 가드의 백틱 분기 부재·손목록 대상, 모바일 패널 스크롤 잠금 부재, 매트릭스가 지목한 상세 라우트의 단일행 미측정. 넷 다 현재 화면·시드로는 재현되지 않으며, 각각 다시 볼 시점을 `trigger:`로 지정해 대장에 등재했다.

**후속 리뷰 권고**: `true`. 이번 패스 patch는 high 1 · medium 4 · low 3이고, high가 하나라도 있으면 권고는 참이다(점수식으로도 3×4+3=15 ≥ 5). 다만 성격은 1·2차와 다르다 — 이번 8건 중 6건이 **2차가 만든 검사·수정 자체의 결함**이었다. 3차에서 코드 동작 자체의 결함으로 새로 나온 것은 비활성 페이저 호버 1건뿐이고, 나머지는 "가드가 무엇을 못 보는가"였다.
