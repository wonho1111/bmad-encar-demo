---
title: 'Pretendard self-host 전환 (기술부채 #40)'
type: 'chore'
created: '2026-07-27'
status: 'done'
baseline_revision: 'd8c4677e7e681cf4000b806a0977dcfc063f5eb6'
final_revision: '930f37d4db98baab86efecbc5db28a58b8d54fd7'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/web/AGENTS.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** `web/src/app/layout.tsx`가 Pretendard를 jsDelivr CDN `<link rel="stylesheet">`(dynamic-subset)+`preconnect`로 로드한다. 외부 CDN 의존이라 첫 페인트를 늦출 수 있고, 수동 `<link>`는 next/font의 자동 fallback metric 보정을 못 받아 폰트 스왑 시 텍스트가 리플로우(FOUT/CLS)된다 — 다음 스토리(11.3 히어로)의 첫인상이 가장 크게 노출되는 화면이라 먼저 해소해야 한다.

**Approach:** Pretendard Variable `.woff2`를 저장소에 넣고 `next/font/local`로 self-host 전환한다. CDN `<link>`+`preconnect`를 제거하고, `globals.css`의 `--font-sans`가 로컬 폰트 변수를 우선 참조하게 바꾼다.

## Boundaries & Constraints

**Always:**
- Pretendard Variable `.woff2`는 GitHub `orioncactus/pretendard` release의 `dist/web/variable/woff2/PretendardVariable.woff2`에서 받아 `web/src/app/fonts/`에 둔다. 가변 폰트라 `next/font/local`에 `weight`를 명시할 경우 실제 축은 `45 920`이다(`100 900` 아님) — 생략도 가능.
- OFL 1.1 라이선스 전문을 폰트 바이너리와 같은 디렉터리에 동봉한다(`web/src/app/fonts/LICENSE.txt` 등).
- `globals.css`의 `--font-sans`(약 100번째 줄)는 `next/font/local`이 생성한 CSS 변수를 **최우선**으로 참조하고, 기존 폴백 스택(`system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`)은 그대로 유지한다.
- `layout.tsx`의 기존 보존 항목 — `suppressHydrationWarning`(body) · `min-h-full flex flex-col`(body) · `h-full antialiased`(html) — 은 그대로 둔다. 관련 주석도 CDN 로딩 설명이 더는 맞지 않으면 갱신한다.
- 코드 작성 전 Next 16 폰트 문서를 먼저 읽는다(`web/AGENTS.md` 원칙): `node_modules/next/dist/docs/01-app/01-getting-started/13-fonts.md`, `node_modules/next/dist/docs/01-app/03-api-reference/02-components/font.md`.
- 실제로 받은 `.woff2` 파일 크기를 재고 기록한다(`ls -la`) — CDN의 dynamic-subset과 달리 self-host는 정적 서브셋을 따로 만들지 않는 한 한글 전체를 통째로 받는다(요청 수↓·페이로드↑ 트레이드오프). 크기가 과하면(체감상 수 MB대) 서브셋 생성 여부를 Design Notes나 커밋 메시지에 판단 근거와 함께 남긴다 — 조용히 넘어가지 않는다.

**Block If:** (없음 — 소스·라이선스·폰트 축·API 시그니처 모두 사전 조사로 확정됨)

**Never:**
- 정적 서브셋 생성 파이프라인을 새로 만들지 않는다(이번 스토리 범위 아님 — 크기가 과하면 판단만 남기고, 실제 서브셋 구축은 별도 후속으로 미룬다).
- `Logo.tsx`나 디자인 토큰(색·spacing 등)을 건드리지 않는다 — 이 스토리는 폰트 로딩 방식 전환만 다룬다.
- DB·API·백엔드 코드는 무관 — 건드리지 않는다.

</intent-contract>

## Code Map

- `web/src/app/layout.tsx` -- `<head>`에서 CDN `<link rel="stylesheet">`+`preconnect`로 Pretendard를 로드 중. `next/font/local` import로 교체하고 생성된 `variable` 클래스를 `<html>`에 적용.
- `web/src/app/globals.css` (~line 100-102) -- `@theme static` 블록의 `--font-sans`가 문자열 폰트명("Pretendard Variable", Pretendard, …)만 나열. 로컬 폰트 CSS 변수를 최우선으로 삽입.
- `web/src/app/fonts/` (신규 디렉터리) -- `PretendardVariable.woff2` + 라이선스 텍스트를 새로 추가.
- `web/src/components/ui/Logo.tsx` -- Pretendard 800 weight로 "차" 글리프 렌더링. 코드 변경 없음, 회귀 확인 대상.

## Tasks & Acceptance

**Execution:**
- `web/src/app/fonts/PretendardVariable.woff2` -- GitHub release에서 다운로드해 추가 -- self-host는 바이너리가 레포 안에 있어야 함
- `web/src/app/fonts/LICENSE.txt` -- Pretendard OFL 1.1 라이선스 전문 동봉 -- OFL 재배포 조건
- `web/src/app/layout.tsx` -- CDN `<link>`+`preconnect` 제거, `next/font/local`로 폰트 로드 후 `<html>`에 `variable` 클래스 적용, CDN 설명 주석을 self-host 설명으로 갱신 -- 렌더 블로킹 외부 요청 제거 + fallback metric 자동 보정 확보
- `web/src/app/globals.css` -- `--font-sans`가 `next/font/local` CSS 변수를 최우선 참조하도록 수정, 폴백 스택은 유지 -- Tailwind `font-sans` 유틸이 self-host 폰트로 연결되게 함

**Acceptance Criteria:**
- Given 현재 CDN 기반 `layout.tsx`, when self-host 전환이 끝나면, then `web/src/app/fonts/`에 `.woff2`+라이선스가 존재하고 `--font-sans`가 로컬 폰트 변수를 우선 참조하며, CDN `<link>`+`preconnect`는 코드에서 제거되고, 기존 보존 속성 3종(`suppressHydrationWarning`·`min-h-full flex flex-col`·`h-full antialiased`)은 그대로 남아 있다.
- Given 전환된 랜딩을 브라우저에서 열었을 때, when computed style을 확인하면, then `font-family`가 Pretendard이고 `document.fonts.check()`가 400·800 weight 모두 true이며, 네트워크 탭에 `cdn.jsdelivr.net` 요청이 없고, `<Logo>`의 800 weight "차" 글자가 라이트·다크 양쪽에서 회귀 없이 렌더된다.
- Given `next build`, when 실행하면, then 빌드가 통과한다.

## Review Triage Log

### 2026-07-27 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 3 (medium 2, low 1)
- defer: 0
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` `globals.css:146-147`의 `body` 블록 주석이 여전히 "Pretendard는 CDN dynamic-subset `<link>`로 로드"라고 서술 — self-host 완료 후에도 갱신 안 됨(blind-hunter·verification-gap·intent-alignment 3개 렌즈가 독립적으로 지적). self-host 설명으로 갱신함.
  - `[medium]` `[patch]` 스펙 Boundaries의 "실제로 받은 .woff2 파일 크기를 재고 기록한다... 조용히 넘어가지 않는다" 요구가 코드/커밋 어디에도 기록되지 않음(blind-hunter·intent-alignment 공통 지적) — `layout.tsx` 주석에 실측값(≈1.96MiB)과 "과도한 수준 아님, 서브셋 파이프라인은 범위 밖" 판단 근거를 기록함.
  - `[low]` `[patch]` `layout.tsx` 주석이 "next/font가 자동으로 fallback metric을 보정해 리플로우를 줄인다"를 한글 본문에도 적용되는 것처럼 서술했으나, `adjustFontFallback` 기본값(로컬 폰트는 'Arial')은 라틴 지표만 제공해 실제로는 한글에 적용 안 됨(edge-case-hunter·blind-hunter 공통 지적) — 주석을 라틴 한정으로 정정함.

### 2026-07-27 — Review pass (후속리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 4 (medium 3, low 1)
- defer: 4 (medium 3, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` `globals.css:100`의 `--font-sans: var(--font-pretendard), …`가 폴백 인자 없는 `var()`라, 변수가 정의되지 않은 트리에서 **선언 전체가 invalid-at-computed-value-time**이 되어 뒤에 적은 한글 폴백(`Apple SD Gothic Neo`·`Malgun Gothic`)까지 통째로 날아감(3개 렌즈가 독립적으로 브라우저 실측). 변경 전 리터럴 스택엔 없던 결합이며 이 diff가 만든 것. `var(--font-pretendard, system-ui)`로 폴백 인자를 넣고 이유를 주석에 남김. **red→green 실측:** 패치 전 클래스 제거 시 `ui-sans-serif, system-ui, sans-serif`(한글 폴백 소실) → 패치 후 `system-ui, system-ui, -apple-system, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`(유지 확인).
  - `[medium]` `[patch]` `localFont()`가 `weight`를 생략해 생성된 `@font-face`에 **`font-weight` 서술자가 아예 방출되지 않음**(빌드 산출물 실측). CSS Fonts 4 기본값은 `normal`(400 고정)이라 클램프하는 엔진에선 전 화면 굵기 위계가 합성 볼드로 납작해진다. Chromium에선 무해함이 3개 렌즈에서 실측됐으나, **교체된 CDN CSS는 `font-weight: 45 920`을 명시하고 있었음**(직접 fetch해 확인) — 즉 이 diff가 기존 보증을 잃은 것. `weight: "45 920"` 추가로 승계. 축 정상 동작 재확인(라틴 폭 400→900이 1293.91→1416.88로 연속 증가, 대조군 `sans-serif`는 두 값만 오감).
  - `[medium]` `[patch]` `layout.tsx` 주석의 "과도한 수준은 아니라고 판단"이 **비교 대상 없이** 내려짐 — 교체된 쪽이 몇 바이트였는지가 어디에도 없어 스펙이 요구한 "판단 근거"가 실질적으로 비어 있었음(4개 렌즈 전부 지적). CDN dynamic-subset을 직접 재서(CSS 59,900 B + unicode-range 92분할, 청크당 약 34~44KB) 비교 수치와 "요청 수↓·첫 방문 전송량은 자릿수↑, 전 라우트 preload" 사실을 주석에 기록하고, 서브셋·측정은 대장 #126으로 넘겼음을 명시.
  - `[low]` `[patch]` 2MB 바이너리에 출처·체크섬 기록이 없어 진위 확인·재현이 불가(blind-hunter 지적). `layout.tsx` 주석에 소스 경로와 `sha256 9599f12f…`를 기록. (릴리스 버전은 이 환경에 fontTools가 없어 추출 불가 — 지어내지 않고 생략.)
- deferred (대장 `docs/tech-debt.md`에 **신규 항목으로만** 등재. 기존 항목(#40 포함)은 이번 호출의 제약대로 손대지 않음):
  - `[medium]` #124 — fallback metric 보정 페이스가 `src: local(Arial)`이라 한글엔 원천적으로 미적용이고, Arial 미설치 환경(Linux·Android)에선 라틴에도 무효. `next/font/local`의 `adjustFontFallback`에 한글 옵션이 없는 프레임워크 한계. 트리거 = Story 11.3.
  - `[low]` #125 — `<Logo>`가 레포 어디에서도 import되지 않음(직접 grep 확인). 지난 패스가 회귀 카나리아로 삼은 컴포넌트가 실은 렌더 경로에 없어, 기록된 "라이트/다크 회귀 없음"은 마크업 주입 관찰이었음. 트리거 = Epic 11 헤더·브랜딩 스토리.
  - `[medium]` #126 — self-host의 first-paint 순효과 미측정(전/후 타이밍·전송량 지표 0건). 부수 관측으로 preload가 프리렌더 라우트(`/login`·`/signup`)에만 붙고 동적 라우트(`/`·`/search`)엔 안 붙음. 서브셋 파이프라인 신설은 스펙 Never. 트리거 = Story 11.3.
  - `[medium]` #127 — "폰트를 외부 CDN에서 받지 않는다"는 규칙이 주석·대장에만 있고 실행되는 검사가 없음(B9). 트리거 = web에 E2E 층 도입(#106) 또는 루트 레이아웃·폰트 자산 재작업.
- rejected (6): ① 폴백 스택에 `"Pretendard Variable", Pretendard` 리터럴 복원 — 스펙 Always가 유지할 폴백 스택을 명시적으로 열거했고 그 목록에 없으며, "설치된 사용자는 2MB를 안 받는다"는 근거도 사실이 아님(preload는 family 순서와 무관). ② `globals.css` 주석의 `AC2` 태그 노후 — 8.1의 AC2가 이 토큰을 세운 것이 맞아 틀린 참조가 아님(A3). ③ 용량 실측값이 주석·대장에 중복돼 늙는다 — 스펙이 명시적으로 요구했고 직전 패스가 그 요구로 심은 것이라 되돌리면 intent 위반. ④ 대장 🟢 행 건수 23→22 미조정 · ⑤ `### 40.` 제목이 "✅ 해소"와 "📅 배정됨"을 동시 서술 — 둘 다 유효한 지적이나 **기존 대장 항목 수정**이라 이번 호출의 제약(오케스트레이터가 소유)에 걸려 처리하지 않음. 표 자체가 "건수는 믿지 마라"를 이미 선언 중. ⑥ preload가 동적 라우트에 안 붙는 비대칭 — Next의 정적/동적 귀속 규칙이지 이 diff의 결함이 아니며 조치는 측정 후 판단 사안. #126의 근거로 흡수.

### 2026-07-27 — Review pass (3차 후속리뷰)
- intent_gap: 0
- bad_spec: 0
- patch: 5 (medium 3, low 2)
- defer: 1 (low 1)
- reject: 7
- addressed_findings:
  - `[medium]` `[patch]` `layout.tsx` 주석의 "이 파일은 **전 라우트에서 preload된다**"가 사실이 아님(blind-hunter·edge-case-hunter·intent-alignment 3개 렌즈 독립 지적, 직접 재확인). 빌드 산출물 실측 — `.next/server/app/*.html` 4개 중 preload 태그가 있는 것은 `login.html`·`signup.html`뿐이고 동적 라우트(`/`·`/search`)엔 없다. 같은 커밋이 만든 대장 #126은 정반대를 적고 있어 **한 커밋의 두 산출물이 같은 빌드에 대해 반대 사실을 주장**하던 상태. 주석을 실측대로 정정.
  - `[medium]` `[patch]` 대장 #126의 **위치** 줄이 "전 라우트 `<link rel=preload>` 확인"이라 **같은 항목의 내용 줄과 자기모순**(blind-hunter 지적). 이 항목은 직전 패스가 만든 것이라 이번 diff 내부 텍스트 — 실측대로 정정하고 정정 사유를 주석으로 남김.
  - `[medium]` `[patch]` `web/README.md:21`이 여전히 "loads Pretendard **via the jsDelivr CDN** dynamic-subset stylesheet"라고 서술(blind-hunter·verification-gap 공통 지적). 레포에 남은 **마지막 거짓 서술**이자 신규 기여자가 가장 먼저 읽는 파일이며, 스펙 Always의 "CDN 로딩 설명이 더는 맞지 않으면 갱신한다"가 겨냥한 부류. self-host 서술로 교체하고 CDN 재유입 금지를 한 줄 덧붙임.
  - `[low]` `[patch]` `weight: "45 920"`이 **실제 가변축과 다름**(edge-case-hunter 지적 → fontTools로 직접 재확인: `fvar` `wght` = min 45 / default 400 / **max 930**). 스펙 Boundaries와 교체 대상 CDN CSS가 둘 다 `45 920`이라 그 값을 승계한 것인데, 원본이 상한을 10 낮게 적고 있었다. `"45 930"`으로 정정. **red→green 실측:** 같은 바이너리를 `45 920`/`45 930` 두 서술자로 각각 물려 930 요청 폭을 비교 — 옛 값은 1283.20(=920 값과 동일 = 클램프), 새 값은 1285.27(클램프 없음). 폰트 버전(1.309, name ID 5)도 함께 기록 — 직전 패스가 도구 부재로 비워둔 자리.
  - `[low]` `[patch]` `globals.css` 폴백 인자 주석이 근거로 든 `global-error.tsx`가 **레포에 존재하지 않음**(3개 렌즈 공통 지적). 시나리오 자체는 실재함을 확인 — Next 기본 에러 페이지가 루트 레이아웃을 거치지 않고 `<html id="__next_error__">`(폰트 클래스 없음)를 직접 그린다(빌드 산출물 확인). 패치를 정당화하는 load-bearing 주석이라 실재하는 근거로 정정.
- deferred (대장 `docs/tech-debt.md`에 **신규 항목으로만** 등재. 기존 항목(#40·요약표 포함)은 이번 호출의 제약대로 손대지 않음):
  - `[low]` #128 — #40 본문이 실측과 어긋난 채 닫혀 있다: ① 가변축 `45 920` 오기(실측 45–930) ② `document.fonts.check()` 인용이 반증 불가능(음성 대조군 실측: 존재하지 않는 family에도 400·800 모두 true) ③ `<Logo>` 회귀 근거가 실제보다 강함(#125와 같은 파일 안에서 어긋남). 코드·주석은 이번에 정정했으나 #40 본문은 오케스트레이터 소유라 미수정. 트리거 = 오케스트레이터가 #40을 손댈 때 또는 Story 11.3.
- rejected (7): ① 폴백 스택에 `"Pretendard Variable", Pretendard` 리터럴 복원(OS 설치본 매칭 상실) — 스펙 Always가 유지할 폴백 스택을 명시적으로 열거했고 그 목록에 없음(직전 패스와 동일 근거). ② `preload` 기본값 true가 1.96MiB를 CSS보다 먼저 고우선순위로 당긴다 — 실재하나 조치는 "측정 후 판단"이고 이미 #126이 그 자리를 잡고 있음(중복 등재 회피). ③ `adjustFontFallback: false`로 Arial 보정 페이스 제거 — 그 보정이야말로 intent의 Problem 문단이 요구한 것이고, 라틴 한정이라는 점은 주석에 이미 명시됨. 이 환경에서 해당 face가 `status: "error"`인 것도 실측했는데 이는 #124가 이미 담고 있음. ④ #124·#126의 트리거를 Story 11.3 인수조건으로 심어야 한다 — 이 워크플로의 프로젝트 규칙이 "트리거는 대장에 조건으로 쓴다"를 형식으로 지정했고, 대장을 읽어 스토리로 묶는 것은 sweep 단계의 역할. ⑤ 요약표 🟡/🟢 건수 미조정 · ⑥ #40 제목의 "✅ 해소"와 "📅 배정됨" 동시 서술 및 "다음 액션" 5번 항목 잔존 — 둘 다 유효하나 **기존 대장 항목 수정**이라 이번 호출의 제약에 걸림. #128에 트리거와 함께 묶어 넘김. ⑦ 2MB 바이너리에 `.gitattributes`/LFS·바이트 예산 부재 — #127이 이미 담고 있는 축.

## Design Notes

`next/font/local`은 `variable` 옵션을 주면 생성된 폰트-family명을 담은 CSS 변수(예: `--font-pretendard`)를 노출한다. `globals.css`는 이 변수를 `--font-sans` 최우선 항목으로 바꿔 끼우면 된다:

```css
--font-sans: var(--font-pretendard), system-ui, -apple-system,
  "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
```

`layout.tsx`에서는 `<html className={`h-full antialiased ${pretendard.variable}`}>` 형태로 기존 클래스에 변수 클래스를 덧붙인다. 로컬 폰트 fallback(`adjustFontFallback`)의 기본값이 `next/font/local`에서는 `'Arial'` 문자열이라는 점이 `next/font/google`과 다르지만(2026-07-16 조사 확인), 그대로 둬도 무방하다 — 별도 설정 불필요.

## Verification

**Commands:**
- `cd web && npm run build` -- expected: 성공 (Next 16 빌드 통과)
- `cd web && npm run lint` -- expected: 새 오류 없음

**Manual checks (if no CLI):**
- 로컬 dev 서버로 랜딩(`/`)을 열고 브라우저 devtools에서 computed `font-family`=Pretendard, `document.fonts.check("400 1em Pretendard")`/`800` 모두 true 확인.
- Network 탭에서 `cdn.jsdelivr.net` 요청이 더는 나가지 않음을 확인(필터링).
- 라이트/다크 각각에서 `<Logo>`(헤더 등 사용처)의 "차" 글자가 굵기·간격 회귀 없이 보이는지 육안 확인.
- `ls -la web/src/app/fonts/PretendardVariable.woff2`로 실제 파일 크기를 재고 기록.

## Auto Run Result

Status: done

**요약:** Pretendard 폰트 로딩을 jsDelivr CDN `<link>`에서 `next/font/local` self-host로 전환(기술부채 #40 해소). Epic 11 첫 스토리 — 다음 스토리(11.3 히어로)의 FOUT/CLS 노출을 미리 차단.

**변경 파일:**
- `web/src/app/layout.tsx` -- CDN `<link>`+`preconnect` 제거, `next/font/local`로 교체, `<html>`에 폰트 변수 클래스 적용
- `web/src/app/globals.css` -- `--font-sans`가 로컬 폰트 CSS 변수를 우선 참조하도록 변경
- `web/src/app/fonts/PretendardVariable.woff2` (신규) -- Pretendard Variable 폰트 바이너리(≈1.96MiB)
- `web/src/app/fonts/LICENSE.txt` (신규) -- OFL 1.1 라이선스 전문

**리뷰 결과 (2회 패스 · 매회 4개 렌즈: adversarial·edge-case-hunter·verification-gap·intent-alignment)**

- **1차 패스:** patch 3건 — CDN 시절 잔존 주석 갱신, 폰트 용량 실측 기록 추가, 한글엔 적용 안 되는 fallback 보정 과장 주석 정정. intent_gap 0, bad_spec 0, defer 0, reject 7.
- **2차 패스(후속리뷰):** patch 4건 · defer 4건 · reject 6건. intent_gap 0, bad_spec 0.
  - `globals.css`의 `var(--font-pretendard)`에 폴백 인자 추가 — 인자 없는 `var()`가 변수 미정의 트리에서 **한글 폴백 스택까지 통째로 무효화**하던 것을 CSS 자체에서 막음(red→green 실측).
  - `layout.tsx`에 `weight: "45 920"` 추가 — 생략 시 `@font-face`에 `font-weight` 서술자가 아예 안 나가 굵기 해석이 엔진 기본값에 맡겨지던 것을 복원. **교체된 CDN CSS가 원래 명시하고 있던 보증**이다.
  - 폰트 용량 판정에 **비교 대상**을 채움(CDN dynamic-subset을 직접 측정: CSS 59,900 B + 92분할, 청크당 약 34~44KB) + 소스 경로·sha256 기록.
  - defer 4건은 대장 `docs/tech-debt.md` **#124~#127로 신규 등재**(트리거 포함). 기존 항목(#40 포함)은 오케스트레이터 소유라 손대지 않음.

- **3차 패스(후속리뷰):** patch 5건 · defer 1건 · reject 7건. intent_gap 0, bad_spec 0.
  - `layout.tsx` 주석의 "전 라우트 preload" 서술이 **사실이 아님**을 빌드 산출물로 확정하고 정정 — preload는 프리렌더 라우트(`/login`·`/signup`)에만 붙는다. 같은 커밋의 대장 #126이 반대로 적고 있던 **위치** 줄도 함께 정정.
  - `weight`를 `45 920` → **`45 930`**으로 정정. 커밋된 바이너리의 `fvar` 축을 fontTools로 직접 읽어 확정(min 45 / default 400 / max 930). 스펙 Boundaries와 교체 대상 CDN CSS가 둘 다 상한을 10 낮게 적고 있었다. 폰트 버전 1.309도 함께 기록.
  - `web/README.md`가 여전히 "jsDelivr CDN으로 로드"라고 서술 — 레포에 남은 마지막 거짓 서술이라 self-host로 교체.
  - `globals.css` 폴백 인자 주석이 근거로 든 `global-error.tsx`가 실재하지 않아, **실재하는 근거**(Next 기본 에러 페이지가 루트 레이아웃 밖에서 `<html id="__next_error__">`를 직접 그림)로 교체.
  - defer 1건은 대장 **#128로 신규 등재**. 기존 항목(#40·요약표)은 오케스트레이터 소유라 손대지 않음.

**후속 리뷰 권고:** true (3차 패스 patch severity 점수 3×medium3 + 1×low2 = 11 ≥ 5)

**검증 수행 (3차 패스 — 이번 실측):**
- `npm run lint`·`npm run build` — 3차 패치 반영 후 재실행, 둘 다 통과(19개 라우트). 생성 CSS에 `@font-face{…font-weight:45 930}` 방출 확인.
- **`document.fonts.check()`는 반증 불가능한 계측임을 음성 대조군으로 확정** — 존재하지 않는 family(`ZZZ_Nonexistent_Family_12345`)에 대해서도 400·800 모두 `true`. 매치되는 face가 없으면 빈 집합이 "전부 로드됨"으로 취급되기 때문. 1·2차 패스가 헤드라인 증거로 인용하던 값이라, 아래의 **반증 가능한 단언**으로 대체한다.
- **폰트가 실제로 로드됐음(반증 가능):** `Array.from(document.fonts)` → `{family:"pretendard", weight:"45 930", status:"loaded"}`. 같은 목록에서 `{family:"pretendard Fallback", status:"error"}` — Arial 미설치 리눅스에서 보정 페이스가 **resolve 자체에 실패**함을 직접 관측(대장 #124의 근거를 실측으로 보강).
- **한글이 정말 Pretendard로 그려지는지 처음으로 판별**(1·2차 패스의 측정은 전부 라틴 한정이라 한글 폴백을 구분 못 했다): 한글 샘플 폭이 `--font-sans` 스택 1123.55px = 명시적 `pretendard` 1123.55px ≠ 폴백 전용 스택 1300px. 세 값이 이렇게 갈리므로 한글은 폴백이 아니라 self-host 폰트로 렌더된다.
- **weight 서술자 red→green:** 같은 바이너리를 `45 920`·`45 930` 두 서술자로 각각 물려 930 요청 폭 비교 — 옛 값 1283.20(920 값과 동일 = 클램프됨), 새 값 1285.27(클램프 없음). 축 연속성도 재확인(400/700/900/920/930 = 1179.59/1239.25/1279.23/1283.20/1285.27, 대조군 `sans-serif`는 700 이후 1246.78로 평평).
- preload 라우트별 실측: `.next/server/app/` 프리렌더 4개 중 `login.html`·`signup.html`만 `<link rel="preload" as="font">` 보유, `_global-error.html`·`_not-found.html`엔 없음.
- `next start`(포트 3047) + Playwright로 위 측정 수행 후 서버 종료 확인(포트 응답 없음).

**검증 수행 (1·2차 패스 기록):**
- `npm run lint`·`npm run build` — 2차 패치 반영 후 재실행, 둘 다 통과(19개 라우트 빌드).
- 생성된 CSS 실측: `@font-face{…font-weight:45 920}` 방출 확인, `--font-sans:var(--font-pretendard,system-ui), …` 확인.
- `next start` + Playwright 실측(포트 3041, 종료 확인): `document.fonts.check()` 400/800 true. **실패 모드 재현 테스트** — `<html>`에서 폰트 변수 클래스를 떼어도 한글 폴백(`Malgun Gothic`)이 살아남음을 확인(패치 전에는 소실됐다). **굵기 축 실측** — Pretendard 라틴 폭이 400/500/700/800/900에서 1293.91/1318.56/1367.55/1392.20/1416.88로 연속 증가(대조군 `sans-serif`는 1278.47/1378.03 두 값만) → 합성 볼드가 아닌 실제 가변축 동작.
- 폭 측정 주의사항(실측으로 확인): Pretendard의 **한글 자간은 굵기 불변**이라(전 weight 518.56px 동일) 한글 텍스트로는 굵기 검증이 원리적으로 불가능하다 — 라틴 샘플이 필요하다.

**잔여 위험:**
- **한글 CLS는 여전히 미보정** — fallback 페이스가 `src: local(Arial)`이라 한글엔 적용될 수 없고, Arial 미설치 환경(Linux·Android)에선 라틴에도 무효. 즉 #40이 정의한 두 뿌리 중 ②(FOUT/CLS)는 한국어 기준으로 해소되지 않았다. 대장 #124로 추적(트리거 = Story 11.3).
- **first-paint 순효과 미측정** — 렌더 블로킹 외부 스타일시트 제거는 확실한 이득이나, 1.96MiB preload가 순증인지 순감인지는 전/후 어느 수치로도 재지 않았다. 대장 #126. *(3차 패스 보정: preload는 "전량·전 라우트"가 아니라 **프리렌더 라우트에만** 붙는다 — 정작 히어로가 놓일 `/`엔 안 붙으므로 그 화면에서는 폰트 발견이 CSS 파싱 이후로 밀린다.)*
- **#40 본문이 실측과 어긋난 채 닫혀 있다** — 가변축 오기(`45 920`, 실제 45–930)·반증 불가능한 `fonts.check()` 인용·`<Logo>` 근거 과장 3건. 코드·주석은 이번 패스에서 정정했으나 대장 #40은 오케스트레이터 소유라 미수정. 대장 #128로 추적.
- **Chromium 외 엔진 미검증** — Firefox·Safari가 이 환경에 없다. 다만 `font-weight` 서술자를 실제 축(`45 930`)으로 명시했으므로 엔진 기본값·잘못된 상한에 대한 의존은 둘 다 제거됐다.
- **`<Logo>` 회귀 확인은 성립하지 않았다** — 이 컴포넌트는 레포 어디에서도 import되지 않는다(직접 grep 확인). 지난 패스의 "로그인 화면에서만 렌더된다"는 전제부터 사실이 아니었고, 확인은 동일 마크업 주입 관찰이었다. 대장 #125.
- **CDN 재유입을 막는 실행 검사 없음** — 규칙이 주석·대장·README에만 있다. 대장 #127.
