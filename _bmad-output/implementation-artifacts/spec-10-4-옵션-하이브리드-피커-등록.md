---
title: 'Story 10.4 — 옵션 하이브리드 피커 (등록)'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '1a7b8a9'
final_revision: 'f1c937a'  # 후속 리뷰 패스(2026-07-22) 커밋. 직전 구현 커밋은 34e7eb4.
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-10-context.md'
  - '{project-root}/docs/tech-debt.md'
  - '{project-root}/web/AGENTS.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 매물 등록·수정 폼(`SellForm.tsx`)의 옵션 입력은 지금 임시 줄바꿈 텍스트에어리어다 — 판매자가 표준 옵션명을 외워 정확히 타이핑해야 하고, 오타 하나면 제출이 통째로 막힌다(Story 10.3이 남긴 임시 UI). Story 10.3이 세운 통제어휘·우선순위 상수를 소비하는 하이브리드 칩 피커로 승격해, 인기 옵션은 한 번에 고르고 희소 옵션은 검색·카테고리로 찾게 한다.

**Approach:** `web/src/lib/options.ts`(통제어휘·순수 헬퍼 단일 출처)에 인기 옵션 8종 상수와 희소 판정 헬퍼를 추가하고, 이를 소비하는 신규 `OptionPicker` 컴포넌트(인기 8칩 + "전체 옵션 더보기" 아코디언 체크리스트 + 검색창 + 선택 요약바)를 만든다. `SellForm`의 옵션 텍스트에어리어를 이 피커로 교체하되, 폼 상태·검증·dirty 로직은 그대로 두어(피커는 순수 표현층) 회귀 위험을 없앤다. 피커가 통제어휘 밖 입력을 **구조적으로 불가능**하게 만들어 §11.3 쓰기 검증을 승격한다.

## Boundaries & Constraints

**Always:**
- 값 정본은 `docs/conventions.md` §11이고 `options.ts`가 미러한다 — 인기 옵션 8종도 §11에 먼저 선언하고 코드가 뒤따른다(§11 "값 정본은 문서, 코드는 미러").
- 피커가 저장하는 모든 옵션명은 통제어휘 소속(`ALL_CONTROLLED_OPTIONS`)이어야 한다. 인기 8칩·카테고리 목록은 전부 표준 옵션명이다(예: `내비`가 아니라 `내비게이션`, `크루즈`가 아니라 `크루즈컨트롤`).
- DB 저장은 기존 `listings.options text[]` 배열 그대로 — 스키마·마이그레이션 변경 없음(§11 정규화 회피).
- 전체 옵션 목록은 `CONTROLLED_OPTIONS`를 `OPTION_CATEGORY_ORDER`(엔카 5분류)로 순회해 렌더한다 — 목업의 예시 이름을 하드코딩하지 않는다(단일 출처 유지).
- 반응형/D5 무결성: 칩·요약바·체크그리드는 폭이 좁아지면 **줄바꿈(wrap)/열 축소**로 흡수하고, 가로 배치를 세로로 찌그러뜨리거나 가로 스크롤을 만들지 않는다(DESIGN §D5).
- 접근성: 인기 칩은 토글 버튼 + `aria-pressed`, "전체 옵션 더보기"는 `aria-expanded`, 항목은 네이티브 `<input type=checkbox>` + 라벨 연결, 검색창은 라벨을 갖는다.
- 등록/수정 두 모드 모두에서 동작한다 — 수정 진입 시 기존 옵션이 선택 상태로 미리 채워진다.

**Block If:**
- (없음 — 인기 8종·카테고리·희소 판정 모두 §11/목업으로 확정됨. 미해결 결정 없음.)

**Never:**
- 옵션 정규화 테이블·DB CHECK·트리거 신설 금지(§11.3). 검증은 앱 레이어에 둔다.
- app(Flutter) 미러 금지 — 폼 피커는 web 전용, app은 Epic 16(§Design Notes "app은 카드 계약 파리티만").
- 목업의 부가 요소(임시저장 버튼 등) 도입 금지 — 옵션 피커 범위 밖.
- 기존 폼 필드·검증·사진·이탈경고·중복제출 빗장 등 옵션 무관 로직 리팩터 금지(A3 외과적 변경).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 인기 칩 토글 | 등록 폼에서 `선루프` 칩 클릭 | 칩이 selected(✓)로 바뀌고 요약바 개수 +1, 선택칩 추가. 재클릭 시 해제 | 없음 |
| 전체 옵션 검색 | "전체 옵션 더보기" 펼친 뒤 검색창에 `파노` 입력 | `파노라마선루프`·`파노라마글래스루프`만 남고 나머지·빈 카테고리는 숨김 | 매칭 0건이면 "검색 결과가 없어요" 안내 |
| 희소 태그 | 전체 목록에서 `선루프`(high)와 `스마트키`(common) 렌더 | `선루프`엔 "희소" 태그, `스마트키`엔 없음(`isRareOption`) | 없음 |
| 요약바 제거 | 선택된 옵션의 요약칩 × 클릭 | 해당 옵션 해제, 개수 −1, 관련 칩/체크박스 동기 해제 | 없음 |
| 제출 저장 | `스마트키`·`선루프` 선택 후 등록 | `listings.options = ['스마트키','선루프']`(배열)로 저장, 상세/카드가 읽음 | 없음(통제어휘 밖 값이 생길 수 없음) |
| 수정 프리필 | 기존 `options=['내비게이션','통풍시트']` 매물 수정 진입 | 두 칩/체크박스가 선택 상태로 미리 채워지고 요약바에 표시 | 없음 |
| 레거시 비표준값(방어) | 수정 진입 매물의 옵션에 통제어휘 밖 값이 섞임(현 시드엔 없음) | 요약바에 제거 가능한 칩으로 **보존·노출**(조용한 드롭 금지). 칩/체크로는 추가 불가 | 남아 있으면 제출 검증이 §11.3 한국어 안내로 차단 |

</intent-contract>

## Code Map

- `docs/conventions.md` §11.2 끝 -- 인기 옵션 8종(`POPULAR_OPTIONS`)·희소 판정 규칙을 값 정본에 추가할 자리(신규 소절).
- `web/src/lib/options.ts:104-189` -- `COMMON_OPTIONS`/`OPTION_PRIORITY`/`optionPriority` 인접. `POPULAR_OPTIONS`(8종)·`isRareOption(name)` 순수 export 추가.
- `web/src/app/(user)/sell/OptionPicker.tsx` -- **신규**. controlled 컴포넌트(`value: string[]`, `onChange`). 요약바 + 인기 8칩 + 더보기 토글 + (검색창 + 5카테고리 체크리스트) 패널.
- `web/src/app/(user)/sell/SellForm.tsx:22,44,616-627` -- 옵션 텍스트에어리어(616-627)를 `<OptionPicker value={parseOptionsInput(form.options)} onChange={(next)=>update('options', serializeOptions(next))} />`로 교체. `FormState.options`(줄바꿈 문자열)·`validateAndBuild`·`toFormState`는 **불변**(피커는 표현층). ⚠️ **dirty 로직만 예외**: 리뷰 패스에서 옵션 dirty를 순서무관 SET 비교(`optionsChanged`)로 조정함 — `toggleOption`의 append가 net-zero 토글에서 줄바꿈 문자열 순서를 바꿔 허위 이탈경고를 유발하기 때문(정당한 필연, 아래 Review Triage Log 참조). "dirty 불변" 원안은 이 append 의미론 때문에 성립하지 않았다.
- `web/src/lib/__tests__/options.test.ts:14-27` -- import 목록에 `POPULAR_OPTIONS`·`isRareOption` 추가 + 신규 케이스.
- `_bmad-output/implementation-artifacts/sprint-status.yaml:143` -- `10-4-...` 상태 + `last_updated` 갱신.

## Tasks & Acceptance

**Execution:** (의존 순서대로)

- `docs/conventions.md` -- §11.2 뒤에 **§11.4 인기 옵션(등록 피커 퀵칩)** 소절 추가: 8종 목록(스마트키·내비게이션·후방카메라·열선시트·통풍시트·선루프·크루즈컨트롤·어라운드뷰)과 "전부 표준 옵션명·`ALL_CONTROLLED_OPTIONS` 부분집합", "희소=high 티어(`isRareOption`)로 피커가 '희소' 태그를 붙인다"를 선언. 짧게. -- 값 정본 확립.
- `web/src/lib/options.ts` -- (a) `export const POPULAR_OPTIONS: readonly string[]`(§11.4 미러, 8종 캐노니컬명). (b) `export function isRareOption(name: string): boolean`(= `Object.prototype.hasOwnProperty.call(OPTION_PRIORITY, name)`, high 티어 = 희소). 헤더 주석에 §11.4 정본 명시. -- 피커가 소비할 순수 상수·헬퍼.
- `web/src/app/(user)/sell/OptionPicker.tsx` -- **신규** `'use client'` controlled 컴포넌트. props `{ value: string[]; onChange: (next: string[]) => void }`. 구성:
  - **요약바**: `선택한 옵션 N개` + `value` 전 항목을 제거(×) 가능한 칩으로(통제어휘 밖 값도 보존·노출).
  - **인기 옵션**: `POPULAR_OPTIONS`를 토글 `<button aria-pressed>` 칩으로. selected면 ✓.
  - **더보기 토글**: `<button aria-expanded>` "전체 옵션 더보기"(caret 회전). 기본 접힘.
  - **확장 패널**: 라벨 있는 검색 `<input>` + `OPTION_CATEGORY_ORDER`로 `CONTROLLED_OPTIONS` 카테고리별 `<label><input type=checkbox>…</label>` 그리드. 검색어(공백 trim, 대소문자 무시 substring)로 필터, 매칭 없는 카테고리는 숨김. `isRareOption`이면 "희소" 태그. 매칭 0건이면 안내 문구.
  - 선택 토글은 `onChange`로 다음 배열 전달(중복 없이, 기존 순서 유지 + 신규는 append). Tailwind로 신뢰-green(`brand`/petrol 계열) 사용, 가격 amber와 분리(§UX 색 규칙).
  - D5: 모든 행 `flex-wrap`/그리드 열 축소, 가로 스크롤·세로 찌그러짐 금지. -- 하이브리드 피커 본체.
- `web/src/app/(user)/sell/SellForm.tsx` -- 옵션 텍스트에어리어(및 그 힌트 주석)를 `OptionPicker`로 교체하고 `OptionPicker`를 import. `parseOptionsInput`/`serializeOptions`로 `form.options`(줄바꿈 문자열) 브리지. `partitionOptions` 백스톱 검증은 그대로 유지(심층 방어 — 레거시 비표준값 대비). 다른 로직 손대지 않음. -- 텍스트 입력 → 구조적 피커.
- `web/src/lib/__tests__/options.test.ts` -- 신규 케이스: (1) **인기 8종 불변식**: `POPULAR_OPTIONS`의 모든 원소가 `ALL_CONTROLLED_OPTIONS`에 있다(`내비`·`크루즈` 같은 비캐노니컬명이 끼면 red — 저장 시 검증 실패로 이어질 함정을 잡음). (2) `isRareOption`: high(`선루프`)=true, common(`스마트키`)=false, mid=false, 통제어휘 밖=false. -- 순수 계약 강제.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-4-옵션-하이브리드-피커-등록` 상태 갱신 + `last_updated` 한 줄 요약. -- 상태 정합.

**Acceptance Criteria:**
- Given 등록 폼, when 인기 옵션 칩(예 `통풍시트`)을 누르면, then 칩이 선택(aria-pressed=true, ✓)으로 바뀌고 요약바 개수·선택칩이 갱신되며, 재클릭 시 해제된다.
- Given "전체 옵션 더보기"를 펼치고 검색창에 `파노`를 입력하면, when 목록이 필터되면, then `파노라마선루프`·`파노라마글래스루프`만 남고 매칭 없는 카테고리는 숨겨진다.
- Given 전체 옵션 목록, when 렌더하면, then high 티어(`선루프` 등)엔 "희소" 태그가 붙고 보편(`스마트키` 등)엔 붙지 않는다.
- Given 인기 칩과 체크리스트에서 옵션을 골라 등록하면, when 저장되면, then `listings.options`에 선택 배열이 그대로 저장되고, 재조회/상세에서 통제어휘 밖 값 없이 동일 배열이 보인다.
- Given 기존 옵션을 가진 매물의 수정 진입, when 폼이 뜨면, then 그 옵션들이 칩/체크박스 선택 상태 + 요약바에 미리 채워진다.
- Given 폭 390px(모바일), when 옵션 피커를 렌더하면, then 칩·요약바·체크그리드가 줄바꿈/열축소로 흡수돼 가로 스크롤·레이아웃 깨짐이 없다(D5).
- Given `POPULAR_OPTIONS`에 비캐노니컬명을 넣으면, when 불변식 테스트를 돌리면, then red가 되고 캐노니컬명으로 되돌리면 green이다.

## Design Notes

**왜 `form.options`를 줄바꿈 문자열로 그대로 두나(A3 외과적).** `SellForm`의 dirty 비교(`form[k] !== initialForm[k]`)·`validateAndBuild`·`toFormState`가 전부 이 문자열 표현에 맞춰져 있다. 피커를 controlled 표현층으로 만들어(`value={parseOptionsInput(form.options)}`, `onChange`는 `serializeOptions`로 되쓰기) 브리지하면 폼 코어를 한 줄도 안 건드리고 회귀 위험이 없다. `FormState.options: string`을 `string[]`로 바꾸면 참조비교 dirty가 항상 참이 되는 등 파급이 크다 — 하지 않는다.

**인기 8칩은 캐노니컬명으로 저장·표시.** EXPERIENCE.md는 `내비`·`크루즈` 축약을 적지만 목업(`forms-2.html`)은 `내비게이션`·`크루즈컨트롤`로 확정했다. 저장값=표시값=통제어휘 캐노니컬명으로 통일해 라벨↔값 매핑층을 없앤다(A2). 불변식 테스트가 이 규칙을 강제한다.

**전체 목록은 코드 상수에서 렌더.** 목업은 예시로 통제어휘 밖 이름(알로이휠·ADAS 등)을 섞어 그렸지만, 실제 피커는 `CONTROLLED_OPTIONS`(71종, 5카테고리)만 렌더한다 — 목업은 레이아웃 참고이지 데이터 출처가 아니다.

**레거시 비표준값 방어(현 데이터엔 없음).** 시드·검증된 쓰기만 존재하므로 DB의 옵션은 통제어휘 부분집합이다(커버리지 테스트가 보증). 그래도 요약바가 `value` 전체를 제거 가능한 칩으로 노출해, 만에 하나 비표준값이 있어도 조용히 드롭하지 않고 보이게 한다(B3 additive 정신). 피커로는 비표준값을 **추가**할 수 없어 검증이 구조적으로 승격된다(§11.3).

## Verification

**Commands:**
- `cd web && npm run test` -- expected: 기존 27 케이스 + 신규 케이스 전부 green. 불변식 테스트는 red-green 왕복으로 1회 실측(`POPULAR_OPTIONS`에 `내비` 임시 삽입 → red → 되돌려 green).
- `cd web && npm run lint` -- expected: 신규/수정 파일 경고 0.
- `cd web && npm run build` -- expected: 타입·빌드 통과(`next build`).

**Manual checks (브라우저 E2E — 피커 스토리 DoD, B4):**
- 로컬 `next dev`(이미 :3000 가동 중) + Playwright로 `/sell` 등록 폼을 연다(로그인 필요 시 시드 판매자 계정 사용).
- 데스크톱(≥1100px)·모바일(390px) 두 뷰포트에서: 인기 8칩 토글, 더보기 펼침, 검색 필터(`파노`), 희소 태그, 요약바 개수/제거를 각각 조작해 확인하고 **가로 스크롤·레이아웃 깨짐이 없음(D5)**을 스크린샷으로 남긴다.
- 옵션 몇 개 선택 후 실제 등록 → 상세/카드에서 동일 배열이 뜨는지, 수정 진입 시 프리필되는지 확인(저장 왕복 실측).
- 브라우저 자동화가 환경 문제로 막히면(로컬 Supabase·인증) 그 사실을 로그와 함께 정직히 보고하고, 최소한 컴포넌트 렌더·토글을 수동으로 확인한 범위를 명시한다(재보기 전 선언 금지, B4).

## Spec Change Log

(없음 — bad_spec 루프백이 없었다.)

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 0
- reject: 11: (high 0, medium 0, low 11)
- addressed_findings:
  - `[medium]` `[patch]` 수정 모드에서 옵션을 껐다 켜면 배열 끝으로 append돼 직렬화 문자열 순서가 바뀌고, 순서 민감한 dirty 비교가 헛되이 참이 돼 이탈 경고(AC7)가 뜨던 문제 — `options`를 일반 키 비교에서 빼고 집합(정렬 후 비교)으로 판정하도록 `SellForm` dirty 로직 수정. 실브라우저로 토글 off/on→경고 없음, 진짜 변경→경고 뜸(음성 대조) 확인.
  - `[low]` `[patch]` 검색 결과 없음 문구(`검색 결과가 없어요`)에 `role="status" aria-live="polite"` 추가 — 스크린리더 고지.
  - `[low]` `[patch]` `<label>`→`<div>` 교체로 끊긴 "옵션 (선택)" 제목–피커 연결을 `role="group"` + `aria-labelledby`(+`useId`)로 복원(`SellForm`).
  - `[low]` `[patch]` `isRareOption` 프로토타입 키 방어(`hasOwnProperty`)를 테스트로 고정 — 형제 `optionPriority`와 동일 축(`toString`·`constructor`·`valueOf`·`hasOwnProperty`·`__proto__` 전부 false).
  - `[low]` `[patch]` 선택 토글 순수 로직 `toggleOption`을 `options.ts`로 추출·export하고 단위테스트(append·재토글 제거·중복없음·순서보존) 추가 — 저장소 관례(`photo-sync`)대로 테스트 가능한 모듈로.

Reject 요지(11): 인기칩 희소태그 누락(§11.4 정본이 "전체 목록에만"으로 명시 — 정합), 인기칩·아코디언 중복노출(승인 목업 그대로·상태 동기), 레거시 비표준값 저장차단/개수포함(그 데이터가 존재 불가 + 에러가 문제 옵션명 명시 + 칩 제거가능), 줄바꿈 라운드트립 손상(10.3 기존 브리지·도달 불가), 검색 약어/동의어(카테고리로 전량 도달 가능·범위 밖·latin명엔 toLowerCase 유효), done-without-verification·D5 미검증(실제로 red→green + 390px E2E 수행함), isRareOption 전체 HIGH셋 고정(기존 HIGH 무결성 테스트와 중복), 재확장 시 검색어 잔존(코스메틱), 요약바 caller 의존 dedup(존재하지 않는 2번째 소비자용 과방어).

### 2026-07-22 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 1, low 1)
- defer: 0
- reject: 13: (high 0, medium 0, low 13)
- addressed_findings:
  - `[medium]` `[patch]` 이전 패스에서 넣은 옵션 dirty의 순서무관 SET 비교(`SellForm`)가 **실행되는 검사로 고정돼 있지 않았다** — `SellForm`은 단위테스트가 없어, 그 비교가 회귀하면(정렬 제거·헬퍼 삭제) 옵션만 편집한 이탈경고가 조용히 사라지거나 허위로 뜨는데도 `npm run test`는 그대로 green이었다(B9 "규칙은 실행되는 검사로"). 비교 로직을 `options.ts`의 순수 헬퍼 `optionsChanged(current, initial)`로 추출(관례: `toggleOption`과 동일)하고 `SellForm`이 이를 호출하도록 위임한 뒤, 단위테스트 5건(순서만 다름·off/on 후 끝이동=not dirty, 추가·제거=dirty, 빈집합=not dirty)을 추가. 실측: 정렬 제거로 red(2 fail)→복원 green(182/182) 왕복 확인.
  - `[low]` `[patch]` Code Map(spec 66행)이 "dirty 로직은 **불변**"이라고 적혀 있으나 실제로는 이전 리뷰 패스에서 옵션 dirty를 바꿨다(Triage Log에만 기록) — 프리즈된 스펙의 기록이 거짓이라 향후 재구동이 "dirty 미변경, 검증 불필요"로 오독할 위험(B8 정확한 기록). Code Map 항목을 실제 변경(append 의미론 때문에 순서무관 SET 비교로 조정, 정당한 필연)과 Triage Log 참조로 정정.

Reject 요지(13, 대부분 이전 패스에서 이미 판정됨): 인기칩/희소태그 co-labeling(§11.4 정본이 "전체 목록에만"으로 허용 — 정합), 줄바꿈 원소 손상(§11.3 레거시 시나리오·통제어휘엔 개행 없음·10.3 기존 브리지·도달불가), 요약바 자체 dedup 계약(존재않는 2번째 소비자용 과방어·현 통합은 `parseOptionsInput`가 dedup), `isRareOption` 전체 HIGH셋 불변식 테스트(`OPTION_PRIORITY`가 HIGH에서 파생돼 구조적으로 성립+기존 무결성 테스트와 중복), 레거시 비표준값 편집잠금 에러문구(데이터 존재불가·요약바 ✕로 제거가능·에러가 옵션명 명시), 부분사진실패 stay시 옵션 baseline stale(전 필드 공통 기존 패턴·이 변경이 악화 안함), 검색어 잔존(코스메틱), OptionPicker 인라인 로직 미테스트(`handleRemove`=toggleOption 제거분기와 동일·검색필터는 표현층·컴포넌트 하네스 없음=범위밖), 브리지 배선 미실행(컴포넌트 하네스 부재=인정된 제약·수동 E2E 커버), 인기칩 그룹 라벨 부재(외곽 role=group가 피커 라벨링·코스메틱), `CONTROLLED_OPTIONS[category]` 가드(TS `Record` 타입이 desync 커버·도달불가), per-render 재계산/메모이제이션(현 규모 무영향·코스메틱), 레거시 칩 시각 구분(편집잠금 동류·도달불가).

## Auto Run Result

Status: done
Story: Epic 10 / Story 10.4 — 옵션 하이브리드 피커 (등록)

**구현 요약:** `SellForm`의 임시 옵션 텍스트에어리어를 하이브리드 칩 피커로 교체했다. 인기 8칩(캐노니컬명) + "전체 옵션 더보기"(옵션 검색창 + 엔카 5카테고리 체크리스트, high 티어엔 "희소" 태그) + 선택 요약바(개수 + 제거 가능 칩)로 구성했고, 통제어휘 밖 입력을 칩/체크로는 구조적으로 못 만들게 해 §11.3 쓰기 검증을 UI 층에서 승격했다. 폼 코어(FormState.options는 줄바꿈 문자열, 검증·프리필)는 건드리지 않고 `parseOptionsInput`/`serializeOptions`로 브리지했다(A3 외과적). 값 정본(인기 8종·희소 판정)은 conventions §11.4에 선언하고 `options.ts`가 미러한다.

**변경 파일:**
- `docs/conventions.md` -- §11.4(인기 옵션 8종 퀵칩 + 희소=high 티어 판정) 추가.
- `web/src/lib/options.ts` -- `POPULAR_OPTIONS`(8종 캐노니컬)·`isRareOption`·`toggleOption`(순수 토글 헬퍼) export 추가.
- `web/src/app/(user)/sell/OptionPicker.tsx` -- **신규** controlled 하이브리드 피커(요약바·인기칩·검색·카테고리 아코디언·희소태그·접근성 속성).
- `web/src/app/(user)/sell/SellForm.tsx` -- 옵션 텍스트에어리어를 `OptionPicker`로 교체(브리지), 옵션 dirty를 집합 비교로, 필드를 `role="group"` + `aria-labelledby`로.
- `web/src/lib/__tests__/options.test.ts` -- `POPULAR_OPTIONS` 불변식·`isRareOption`(프로토타입 키 포함)·`toggleOption` 테스트 추가.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-4` 상태·`last_updated` 갱신.

**리뷰 findings:** patch 5건 적용(위 Triage Log) · defer 0 · reject 11 · intent_gap 0 · bad_spec 0.
**Follow-up review 권고:** true (patched: high 0·medium 1·low 4 → 점수 3×1+1×4=7 ≥ 5).

**검증(오케스트레이터 직접 재실행):** `npm run test` 177/177 green · `npm run lint` exit 0 · `npm run build` exit 0. 불변식 red→green 1회 실측(dev). 브라우저 E2E(Playwright, seller 계정, 로컬 Supabase): 인기칩 토글↔aria-pressed·요약바, 더보기 aria-expanded, 검색 `파노`→2건·0건 안내, 희소 태그(선루프 O·스마트키 X), 요약바 × 동기 해제, 저장 왕복(listings.options 배열)·상세 표시·수정 프리필, 390px D5(scrollWidth===clientWidth) 확인. I/O 매트릭스 7행 전부 실행됨(레거시 비표준값 보존행은 DB에 out-of-vocab 값 주입해 편집 진입→요약바 보존·추가불가·제출차단 실측 후 정리). PATCH 1(순서 무관 dirty)은 실브라우저 음성 대조까지 재확인.

**잔여 리스크:** (1) `OptionPicker` 컴포넌트 렌더/상호작용은 자동 컴포넌트 테스트가 아니라 수동 E2E로만 커버된다(리포에 React 컴포넌트 테스트 하네스 없음 — 기존 관례). 순수 로직(`toggleOption`·`isRareOption`·`optionsChanged`·파싱)은 vitest가 고정. (2) 옵션 검색은 캐노니컬명 substring 매칭이라 약어·동의어는 못 찾는다(카테고리 브라우징으로 전량 도달 가능해 기능 손실은 없음). (3) app(Flutter) 폼 미러는 Epic 16으로 이관(계약만 공유).

---

### 2026-07-22 — 후속 리뷰 패스 결과

**한 일:** 프리즈된 done 스펙에 대한 신규 리뷰(4렌즈: adversarial·edge-case·verification-gap·intent-alignment)를 돌려, 이전 패스 이후에도 남아 있던 **검증 갭 1건**을 patch로 닫았다.

- **patch(medium):** 옵션 dirty의 순서무관 SET 비교가 `SellForm`에 인라인돼 있어 실행되는 검사가 없었다(SellForm은 단위테스트 부재). 비교를 순수 헬퍼 `optionsChanged`(→ `web/src/lib/options.ts`)로 추출해 `SellForm`이 위임하게 하고, 단위테스트 5건을 추가해 net-zero 토글=not dirty / 진짜 추가·제거=dirty를 고정. 정렬 제거로 red(2 fail)→복원 green(182/182) 왕복 실측.
- **patch(low):** Code Map의 "dirty 로직 불변" 오기를 실제 변경(순서무관 SET 비교로 조정)과 그 근거로 정정 — 향후 재구동이 스펙 기록만 보고 dirty를 안전한 미변경으로 오독하는 것을 방지(B8).
- **reject 13:** 대부분 이전 패스에서 이미 판정된 것들(§11.4 허용 co-labeling, 도달불가 레거시/줄바꿈 시나리오, 컴포넌트 하네스 부재로 인한 표현층 미테스트 등) — 상세는 Review Triage Log 참조.

**검증:** `npm run test` 182/182 green(177+신규 5) · `npm run lint` exit 0 · `npm run build` exit 0. `optionsChanged` 회귀 검사 red→green 1회 실측.

**Follow-up review 권고:** false (이번 패스 patched: high 0·medium 1·low 1 → 점수 3×1+1×1=4 < 5, high 없음 → 수렴).

**변경 파일(이 패스):** `web/src/lib/options.ts`(`optionsChanged` 추가) · `web/src/app/(user)/sell/SellForm.tsx`(인라인 비교 → 헬퍼 위임) · `web/src/lib/__tests__/options.test.ts`(`optionsChanged` 테스트 5건) · 이 스펙 문서(Code Map 정정·Triage Log·결과).
