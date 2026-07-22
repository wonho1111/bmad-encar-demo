---
title: 'Story 10.3 — 옵션 통제어휘 + 우선순위 상수 + 저장구조 정비'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '3b029e7'
final_revision: '02b7dbe'  # 후속 리뷰 패스 커밋(이 값 기입은 --amend라 최종 HEAD SHA는 한 단계 뒤일 수 있음)
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

**Problem:** 옵션(`listings.options text[]`)이 자유 텍스트라 표준이 없고, 카드는 옵션을 아예 안 보여주며(차별화 옵션이 안 드러남), 상세는 정렬·분류 없는 평면 칩 나열이다. 등록 폼(`SellForm.tsx`)은 옵션을 쉼표로 join/split해 한 옵션 값에 쉼표가 들어가면 첫 수정 저장 때 둘로 쪼개진다(대장 #11).

**Approach:** 정규화 테이블을 만들지 않고 `text[]` 저장을 유지하되, **통제어휘(표준 옵션명 목록)·`COMMON_OPTIONS`(보편·저순위)·`OPTION_PRIORITY`(옵션명→점수)** 상수를 `docs/conventions.md` 단일 출처로 선언하고 web 한 모듈이 미러링한다(app은 Epic 16). 이 상수로 (1) 카드가 우선순위 상위 3~4개 희소 옵션을 노출(없으면 보편 fallback), (2) 상세가 5개 엔카 카테고리로 전량 그룹핑, (3) 쓰기 시 통제어휘로 검증한다. 저장 구분자를 쉼표→줄바꿈으로 바꾸고 파싱을 순수함수로 뽑아 #11을 재현 테스트로 닫는다.

## Boundaries & Constraints

**Always:**
- `options`는 `text[]` 유지 — 정규화 테이블·DB CHECK를 만들지 않는다(연구 근거 `research-data-options.md` §112~113, A2). 통제어휘 검증은 **앱 레이어**에서 한다.
- 통제어휘·`COMMON_OPTIONS`·`OPTION_PRIORITY`의 **값 정본은 `docs/conventions.md`**. 코드(web `options.ts`)는 그 문서를 출처로 명시해 미러링한다 — web TS/app Dart에 서로 다른 사본을 손으로 두지 않는다(이원화 금지, §1·§7 EMBEDDING_DIM·CHAT 상수와 같은 패턴).
- 통제어휘는 **현재 시드에 실재하는 모든 distinct 옵션명을 빠짐없이 덮는다**(각 옵션 → 정확히 1개 카테고리). 미달이면 테스트가 red. 동의어("HUD"/"헤드업디스플레이"/"증강현실HUD", "후방카메라"/"후방센서"/"주차센서")는 **각각 별도 표준항목으로 그대로 수록**한다 — 동의어 통합=정규화라 범위 밖(A2).
- 카드에 `options`를 싣는 것은 ListingCard 계약 변경이므로 `docs/conventions.md` §4.1 **락스텝 4곳 + `SELECT_COLUMNS` + 카드 select 문자열 3곳**을 동시에 갱신한다.
- `options`는 이미 `0011` anon GRANT(57행)·`sql_guard.ALLOWED_COLUMNS`에 있다 → **anon 42501 회귀 없음, 로그인 분기 불필요**(10.1 신뢰컬럼과 다른 점).
- 반응형/D5 무결성: 카드 옵션 칩 행은 좁아져도 **세로로 접거나 2줄로 밀지 않는다** — 밀도 높으면 "대표 1개 + 외 N개" 또는 truncate로 흡수(project-context 규칙 13).
- 마이그레이션은 additive·forward-only. 이 스토리는 **스키마 변경이 없다**(컬럼 이미 존재).

**Block If:**
- 통제어휘에 시드 옵션 하나를 어느 카테고리에도 합리적으로 못 넣는 경우 → `기타옵션`에 넣고 진행(블록 아님).
- (실질 블록 조건 없음 — 의도가 에픽 컨텍스트+연구 문서로 충분히 확정됨.)

**Never:**
- 옵션의 금전 가치(원가·감가율 수치) 표시 금지(데이터 없음, 과설계 — `research-data-options.md` §125).
- 10.4의 하이브리드 칩 피커(인기 8칩·아코디언·검색창)를 여기서 만들지 않는다 — 10.3의 입력은 줄바꿈 텍스트에어리어(임시), 피커는 10.4가 얹는다.
- app(Flutter) 카드/상세 위젯의 옵션 렌더 변경·app `options.ts` 상수·app 폼 #11 미러 수정 금지 → Epic 16. (app **카드 타입·select 문자열 파리티만** 이 스토리에서 맞춘다, 10.1 선례.)
- 관리자 상세(`ListingDetailFields.tsx`)의 평면 옵션 목록은 손대지 않는다(카테고리 그룹핑은 구매자 상세 한정).
- DB CHECK·트리거로 통제어휘를 강제하지 않는다(위 Always 근거).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 희소 옵션 보유 카드 | `options=['후방카메라','스마트키','선루프','통풍시트','내비게이션']` | 카드에 priority desc 상위 3~4개(선루프·통풍시트·내비…), 보편(후방카메라·스마트키)은 밀림 | — |
| 보편만 보유 카드(fallback) | `options=['후방카메라','스마트키','블루투스']` | 희소 없음 → 보편에서 상위 N개 채워 노출(빈 칩 행 금지) | — |
| 옵션 없음 카드 | `options=null` 또는 `[]` | 카드 옵션 칩 행 미표시(빈 잉크 없음) | — |
| 카드 밀도 초과 | 상위 N개가 좁은 폭에 안 들어감 | "대표 1개 + 외 N개" 또는 truncate — 세로 접힘/2줄 금지(D5) | — |
| 상세 그룹핑 | `options`에 5카테고리 혼재 + 통제어휘 밖 값 1개 | 카테고리별 섹션으로 전량 노출, 통제어휘 밖 값은 `기타옵션`에 | — |
| 줄바꿈 파싱(#11) | 폼 입력 `"스마트키, 후방카메라\n선루프"` | `['스마트키, 후방카메라','선루프']` — 쉼표 든 원소 보존 | 빈 줄·앞뒤 공백 제거, 중복 제거 |
| 쓰기 검증 | 폼 제출 옵션에 통제어휘 밖 이름 포함 | 제출 차단 + 어떤 이름이 비표준인지 한국어 메시지 | 표준 이름들만 남겨 저장하지 않고 **막고 알린다**(조용한 드롭 금지) |

</intent-contract>

## Code Map

- `docs/conventions.md` §4(42~58 ListingCard 필드 표)·§4.1(75~120 락스텝)·§10 끝(342행) -- 카드 계약에 `options` 추가 + 새 §11(통제어휘 정본) 삽입 자리.
- `web/src/lib/options.ts` -- **신규**. 통제어휘·상수·순수 헬퍼의 web 미러(단일 코드 출처).
- `web/src/components/listings/ListingCard.tsx:14-31` -- `ListingCardData`(options 없음 → 추가) + 카드 본문(옵션 칩 렌더 없음 → 상위 N개 추가).
- `api/app/schemas/ai.py:60-85` -- `class ListingCard`(options 없음 → 추가, `list[str] | None`).
- `app/lib/features/listings/listing.dart:20-38` -- `ListingCardData`(options 없음 → 타입 파리티 추가; 위젯 렌더는 Epic 16).
- `api/app/graph/listing_cards.py:32-35` -- `SELECT_COLUMNS`(options 없음 → 추가).
- `web/src/app/page.tsx:59-60` -- 홈 카드 select(options 추가).
- `web/src/app/(user)/search/page.tsx:113` -- /search 카드 select(options 추가).
- `app/lib/features/listings/listings_repository.dart:39-40` -- app `fetchListings` 카드 select(options 추가, 파리티).
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx:128-136` -- 구매자 상세 `OptionsSection`(평면 → 카테고리 그룹핑). `page.tsx:132`는 이미 options select함.
- `web/src/app/(user)/sell/SellForm.tsx:100,242-246,613-614` -- options read join `', '` → write split `,`(#11) + textarea 힌트. 줄바꿈 전환 + 제출 검증 자리.
- `supabase/migrations/0002_listings.sql:56` -- `options text[] default '{}'`(CHECK 없음 — 그대로 둔다). `0011:57`·`sql_guard.py:40` -- options 이미 anon GRANT·화이트리스트에 있음(회귀 근거).
- `docs/tech-debt.md` #11(129행) -- 이 스토리가 닫는다(web). app 폼 미러는 Epic 16으로 트리거 이관.
- `supabase/seed-local/data/listings.json`·`supabase/seed.sql` -- 통제어휘 커버리지 검증용 distinct 옵션 원천(71개 확인).

## Tasks & Acceptance

**Execution:** (의존 순서대로)

- `docs/conventions.md` -- (a) §4 ListingCard 필드 표에 `options | string[]\|null (장비 통제어휘 배열) | Epic 10 (10.3)` 행 추가(증분 신규, nullable). (b) 새 **§11 옵션 통제어휘·우선순위** 절 추가: 5개 엔카 카테고리(외관/내장·안전·편의/멀티미디어·시트·기타옵션), `COMMON_OPTIONS`(보편·저순위) 목록, `OPTION_PRIORITY` 티어 규칙(희소 high → 기본 mid → COMMON forced-lowest)과 연구 랭킹(선루프 > 내비≈HUD > 차로이탈방지보조 > 크루즈/후측방/서라운드뷰), 카드=상위 3~4 / 상세=카테고리 전량 규칙, "값 정본은 이 문서, 코드는 미러" 선언. -- 단일 출처 확립.
- `web/src/lib/options.ts` -- **신규**. §11을 미러하는 상수·순수 헬퍼(헤더에 "정본: conventions.md §11" 명시):
  - `CONTROLLED_OPTIONS`: `{category → readonly string[]}` — 시드 71개 distinct 값을 전부 수록(카테고리당 배열).
  - `COMMON_OPTIONS: ReadonlySet<string>` · `OPTION_PRIORITY: Record<string, number>`.
  - `optionPriority(name)`: `OPTION_PRIORITY[name] ?? (COMMON_OPTIONS.has(name) ? 0 : DEFAULT_MID)`.
  - `topOptions(options, n)`: priority desc(동점 입력순), 상위 n개(3~4). 전부 보편이면 보편에서 채움(fallback), 빈 배열이면 `[]`.
  - `groupByCategory(options)`: 카테고리별 배열, 통제어휘 밖 값 → `기타옵션`.
  - `partitionOptions(names)` → `{known, unknown}` · `parseOptionsInput(text)`(줄바꿈 split·trim·빈줄 제외·중복 제거) · `serializeOptions(arr)`(줄바꿈 join). -- 검증·저장·표시 로직의 단일 코드 출처. **#11 파싱을 순수함수로 격리해 테스트가 잡게 한다(B9).**
- `web/src/components/listings/ListingCard.tsx` -- `ListingCardData`에 `options?: string[] \| null` 추가 + 기존 카드 레이아웃 B의 옵션 슬롯(사진/차량명/meta/가격 아래)에 `topOptions(options,4)` 칩 렌더. 값 없으면 슬롯 미표시. D5 안전(truncate·"외 N", 세로 접힘 금지). -- 카드에 희소 옵션 노출.
- `api/app/schemas/ai.py` -- `ListingCard`에 `options: list[str] | None = None`. -- AI 응답 카드도 계약 파리티(드리프트 방지).
- `api/app/graph/listing_cards.py` -- `SELECT_COLUMNS`에 `options` 추가 + 튜플→ListingCard 매핑에 반영. -- api 카드가 실제로 옵션을 싣게.
- `app/lib/features/listings/listing.dart` -- `ListingCardData`에 `options` 필드(타입 파리티만; 카드 위젯 렌더는 Epic 16). -- 계약 락스텝.
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` · `app/lib/features/listings/listings_repository.dart` -- 각 카드 select 문자열에 `options` 추가(anon-safe). -- 값이 카드까지 도달.
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` -- `OptionsSection`을 `groupByCategory(options)`로 카테고리 섹션 렌더(전량, 빈 카테고리 생략, 통제어휘 밖 → 기타옵션). "등록된 옵션이 없습니다." 빈 상태 유지. -- 상세 카테고리 그룹핑.
- `web/src/app/(user)/sell/SellForm.tsx` -- (a) read: `serializeOptions(v.options ?? [])`, textarea value/onChange를 줄바꿈 기준으로, 힌트 "옵션을 한 줄에 하나씩". (b) 제출: `parseOptionsInput` → `partitionOptions`; `unknown`이 있으면 제출 차단 + "표준 옵션명이 아닙니다: …" 한국어 에러(조용한 드롭 금지), 없으면 `known` 배열 저장. -- #11 닫기 + 쓰기 검증.
- `web/src/lib/__tests__/options.test.ts` -- **신규**. (1) **커버리지**: 시드 distinct 옵션 전부가 `CONTROLLED_OPTIONS`에 있고 카테고리 1개에 속함(하나라도 빠지면 red — 시드 파일에서 distinct 추출해 단언). (2) `topOptions` 희소우선·보편fallback·상위N cap·빈배열. (3) `groupByCategory` 기타옵션 폴백. (4) **#11 라운드트립**: `parseOptionsInput('a, b\nc')`가 `['a, b','c']`(쉼표 보존). (5) `partitionOptions` known/unknown. -- I/O 매트릭스 전 케이스.
- `docs/tech-debt.md` -- **#11을 `✅ 해소`로 닫는다**(web: 줄바꿈 전환 + 순수함수 테스트 red-green 1줄 실측). app 폼 미러(`listing_form.dart` 동일 패턴)는 **Epic 16으로 트리거 이관**해 새 항목 또는 #52 계열에 1줄로 등재(근거·트리거 명시, B8). -- 대장은 하나, 미룬 것은 트리거와 함께.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-3-...` 상태 갱신 + `last_updated` 한 줄 요약. -- 상태 정합.

**Acceptance Criteria:**
- Given `options`에 희소+보편이 섞인 매물, when 카드를 렌더하면, then priority 상위 3~4개(희소 우선)만 칩으로 뜨고 보편은 밀린다. 희소가 없으면 보편으로 채운다(빈 행 아님). 좁은 폭에서 세로로 접히지 않는다(D5).
- Given `options=null/[]` 매물, when 카드를 렌더하면, then 옵션 칩 행이 그려지지 않는다.
- Given 5카테고리+통제어휘 밖 값이 섞인 매물, when 상세를 열면, then 카테고리별 섹션으로 전량 노출되고 통제어휘 밖 값은 `기타옵션`에 들어간다(희소 필터 없음).
- Given 한 원소에 쉼표가 든 옵션(`'스마트키, 후방카메라'`)을 가진 매물, when 등록 수정 폼을 열어 저장하면, then 그 원소가 둘로 쪼개지지 않고 그대로 1개로 유지된다(#11 해소).
- Given #11 재현 테스트, when `parseOptionsInput`을 쉼표 split로 되돌리면, then 라운드트립 테스트가 **red**가 되고 줄바꿈으로 원복하면 green이다.
- Given 통제어휘 밖 이름이 포함된 폼 제출, when 저장을 누르면, then 제출이 차단되고 비표준 이름이 한국어로 안내된다(조용히 드롭하지 않는다).
- Given 통제어휘 커버리지 테스트, when 시드에 통제어휘 밖 distinct 옵션이 하나라도 있으면, then 테스트가 red다.
- Given ListingCard 계약, when `options`를 추가하면, then 락스텝 4곳+`SELECT_COLUMNS`+카드 select 3곳이 함께 갱신돼 있고 anon `/search`가 42501 없이 뜬다.
- Given 대장, when 작업이 끝나면, then #11이 닫히고 app 폼 미러가 트리거와 함께 Epic 16으로 이관돼 있다.

## Design Notes

**통제어휘 값은 dev가 시드에서 짓되 커버리지 테스트가 강제한다.** 정본(§11)은 카테고리·티어·규칙을 정의하고, 실제 71개 옵션명 배치는 dev가 아래로 재현해 채운다 — 완성도는 "TBD 없음"이 아니라 **red-green 게이트**로 보장한다:
```bash
python3 -c "import json;o=set(x for r in json.load(open('supabase/seed-local/data/listings.json',encoding='utf-8')) for x in (r.get('options') or []));print('\n'.join(sorted(o)))"
```
카테고리 배치 지침(엔카 5분류, 연구 §71~79 근거 — 정확한 세부분류는 시대별로 바뀌므로 합리적 배치면 족하다):
- **안전:** 에어백·후측방경고·후측방모니터·차선유지보조·후방카메라·후방센서·후방감지센서·주차센서·원격주차·혼다센싱·후석알림
- **편의/멀티미디어:** 내비게이션·애플카플레이·블루투스·무선충전·무선업데이트·크루즈컨트롤·스마트크루즈·어댑티브크루즈·스마트키·에어컨·라디오·어라운드뷰·서라운드뷰·버추얼콕핏·HUD·헤드업디스플레이·증강현실HUD·뒷좌석모니터·후석엔터테인먼트·하이패스 + 오디오 브랜드(JBL사운드·렉시콘사운드·마크레빈슨·메리디안사운드·뱅앤올룹슨·부메스터사운드·하만카돈·프리미엄오디오)
- **시트:** 열선시트·통풍시트·가죽시트·나파가죽·나파가죽시트·레더시트·메모리시트·릴렉션시트
- **외관/내장:** LED헤드램프·매트릭스LED·선루프·파노라마선루프·파노라마글래스루프·앰비언트라이트·전동트렁크·전동슬라이딩도어·슬라이딩도어·카본인테리어·요크스티어링·파워스티어링·열선스티어링·M스포츠패키지·M서스펜션·콰트로
- **기타옵션:** 7인승·8인승·9인승·11인승·V2L·초고속충전·급속충전지원·오토파일럿

**우선순위 = 티어.** 71개를 개별 점수 매기지 않는다. `COMMON_OPTIONS`(후방카메라·후방센서·후방감지센서·주차센서·스마트키·블루투스·에어백·에어컨·라디오·파워스티어링·하이패스·애플카플레이·무선충전·열선시트·크루즈컨트롤·LED헤드램프·가죽시트·후석알림)=0(forced-lowest). 희소·셀링포인트(선루프·파노라마선루프·파노라마글래스루프·HUD계열·통풍시트·어라운드뷰·서라운드뷰·어댑티브크루즈·스마트크루즈·차선유지보조·후측방경고/모니터·오토파일럿·나파가죽·카본인테리어·오디오브랜드·V2L·초고속충전·릴렉션시트·앰비언트라이트·요크스티어링·콰트로·M패키지·매트릭스LED·후석엔터테인먼트·뒷좌석모니터)=high(선루프 계열 최상). 나머지=mid 기본값. 카드 `topOptions`가 이 순으로 정렬해 상위 N개.

**#11은 "값에 쉼표"가 핵심.** 시드엔 쉼표 든 옵션이 없어 지금은 잠복이다(대장 #11 "폼 입력만으론 발생 안 함"). 줄바꿈 구분자로 바꾸면 한 원소 안의 쉼표가 살아남는다. 파싱을 `options.ts` 순수함수로 뽑아 단위 테스트가 라운드트립을 잡게 한다 — 화면(SellForm)이 아니라 함수에서 red를 실측(#11 해소 방식은 대장 "입력 구분자 변경(줄바꿈)"과 일치).

**왜 DB CHECK가 아니라 앱 검증인가(B9 절충 명시).** B9는 "중요 값은 DB가 강제"라지만, 옵션명 비표준의 대가는 무결성이 아니라 표시상 미분류(→기타옵션)·저순위일 뿐이다(FR11·채팅길이 같은 계약과 성격이 다르다). 그리고 통제어휘를 DB CHECK로 강제하면 71+ 목록을 SQL에도 사본으로 둬야 해 이 스토리가 금지한 이원화가 생긴다. 그래서 검증은 쓰기 UI(SellForm) 층에 둔다. 10.4의 칩 피커는 이 검증을 **구조적으로**(비표준 입력 불가) 승격한다.

**app은 카드 계약 파리티만.** 10.1이 신뢰컬럼을 app `ListingCardData` 타입·select에 넣되 뱃지 위젯 렌더는 Epic 16으로 미룬 선례를 따른다 — `options`도 app 카드 타입·select만 맞추고 칩 위젯·상수·폼 #11 미러는 Epic 16.

## Verification

**Commands:**
- `cd web && npm run lint && npx tsc --noEmit && npm test` -- expected: 린트·타입 통과, `options.test.ts` 포함 vitest green(커버리지·topOptions·groupByCategory·#11·partition).
- **#11 red/green 실측:** `parseOptionsInput`을 쉼표 split로 임시 되돌림 → `npm test`가 라운드트립 케이스로 **red** → 줄바꿈 원복 → green. 두 출력 기록.
- **커버리지 red/green 실측:** `CONTROLLED_OPTIONS`에서 시드 옵션 하나(예: `V2L`)를 임시 제거 → 커버리지 테스트 **red** → 원복 green.
- `cd web && npm run build` -- expected: 빌드 성공(서버 컴포넌트 타입 정합).
- `cd api && python -m pytest` -- expected: 기존 테스트 green(`SELECT_COLUMNS`에 options 추가 후 카드 매핑 회귀 없음).

**Manual checks (재보기 전엔 선언하지 않는다, B4):**
- 로컬 Supabase(55322) + `cd web && npm run dev`(3000)로: (a) 희소 옵션 많은 시드 매물의 카드에 상위 3~4 희소 칩이 뜨고 보편이 밀리는지, 보편만 있는 매물은 fallback으로 채워지는지, 좁은 폭(390)에서 세로로 안 접히는지(D5), (b) 그 매물 상세에서 옵션이 카테고리별로 전량 그룹핑되는지, (c) **비로그인**으로 `/search`가 42501 없이 뜨는지 브라우저(MCP) 스크린샷으로 확인.
- #11 수동: 로컬 DB에서 한 매물 `options`에 쉼표 든 원소(`array['스마트키, 후방카메라']`)를 심고 수정 폼 열어 저장 → `select options from listings where id=…`로 원소가 1개로 유지되는지 확인.

## Spec Change Log

_(없음 — 이번 리뷰 패스에 bad_spec 없음. intent-alignment이 확인한 구현 판단(A2 앱검증·B2 app 파리티·C1 줄바꿈·D2 상위4캡·E2 티어·F1 상위N채움)은 전부 에픽/연구문서 근거가 있는 방어 가능 해석이라 스펙 수정 불필요.)_

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 4: (high 0, medium 2, low 2)
- defer: 1: (high 0, medium 0, low 1)
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` P1 — `HIGH_PRIORITY_OPTIONS`에서 `'나파가죽시트'`가 빠져 있었다. `conventions.md §11.2`(값 정본)는 이를 HIGH로 선언하고 실제 시드 매물 `fef24c05`(옵션 `["8인승","나파가죽시트","HUD","후석알림","파노라마선루프"]`)가 이를 담는데, 코드에선 MID(5)로 떨어져 `topOptions` 상위4에서 범용 `8인승`이 프리미엄 나파가죽 위로 올라갔다 — **스토리 헤드라인("희소·차별화 옵션 먼저")이 실데이터에서 뒤집히는** 지점. 3개 코드레인(적대·엣지케이스·검증갭)이 동일 근거로 수렴. `HIGH_PRIORITY_OPTIONS`에 `'나파가죽시트'` 추가로 코드↔문서 정합.
  - `[medium]` `[patch]` P2 — P1이 green으로 새어나간 원인: `COMMON_OPTIONS`·`HIGH_PRIORITY_OPTIONS`가 통제어휘의 부분집합인지, §11.2 선언 티어와 일치하는지 **못박는 불변 테스트가 없었다**. `options.test.ts`에 무결성 3건 신설(두 티어 ⊆ 통제어휘 + §11.2 하드코딩 기대배열과 정확 일치). **red/green 실측(재확인):** HIGH에서 `'나파가죽시트'` 제거 → 정확일치 테스트 red(나머지 22 green) → 원복 23/23 green. 기존 커버리지 테스트가 어휘엔 걸던 규율을 티어에도 확장.
  - `[low]` `[patch]` P3 — `optionPriority`가 통제어휘 밖 이름에 MID(5)를 줘 COMMON(0)보다 높았다(테스트도 `optionPriority('존재하지않는옵션') > 0`으로 그 오동작을 못박고 있었다). 통제어휘 밖은 카드에서 정상 보편옵션 위로 올라갈 자리였다(데모 데이터엔 커버리지로 미발생, 방어적 정정). `ALL_CONTROLLED_OPTIONS` 밖이면 `TIER_COMMON` 반환으로 바꾸고 테스트를 `≤ COMMON` 계약으로 정정 + in-vocab mid는 여전히 MID임을 못박는 케이스 추가.
  - `[low]` `[patch]` P4 — 카드 옵션 칩이 `key={opt}`라 `options`(text[], 원소 유일성 없음)에 중복이 오면 React 키 충돌·중복 칩(상세 `OptionsSection`은 `key={opt}-${i}`로 이미 방어). `topOptions`가 입력을 dedupe하도록 바꿔 카드가 동일 칩을 두 번 그릴 수 없게 함.

4개 리뷰 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 돌렸다(전부 opus, 무맥락 새 세션). **intent_gap·bad_spec 0** — 의도정합 레인이 구현이 방어 가능한 해석(A2/B2/C1/D2/E2/F1)을 충실히 따른다고 확인했고, 표면화한 것은 우선순위 상수의 코드↔문서 드리프트 1건(P1)과 그걸 못 잡던 검증 공백(P2), 그리고 순위 계약 견고성 2건(P3·P4)이었다.

- **defer 1건 → `docs/tech-debt.md` #114 신규 등재**(동결된 `deferred-work.md` 아님, 프로젝트 규칙 우선): 카드 옵션 칩이 <640px 1열에서 "외 N개" 축약 없이 잘릴 수 있다(D5 문자규칙은 `flex-nowrap`으로 지킴 — 세로 접힘 불가, 잔여개수 affordance만 없음, low). 트리거: Epic 10.7 통합 검증(대표 매물 카드 뷰포트별 실측).
- **reject 8건**(전부 low): (1) 통제어휘 밖 이름이 있는 레거시 매물 수정이 막힌다 — 데모 데이터는 전부 통제어휘 안(커버리지 보장)이라 미발생, 통제어휘는 10.4 피커도 동일하게 제약. (2) 임시 자유텍스트 폼이 유효 옵션 목록을 안 보여줘 하드블록이 막다른 길 — 짧은 임시 구간, 10.4 피커가 구조적으로 해소. (3) 줄바꿈-값-내-포함 잔여 위험 — 텍스트에어리어로 입력 불가(Enter=새 옵션), 시드/API 값에만 이론상 존재, 10.4 칩이 제거(§11.3 명시). (4) `parse(serialize)`가 중복/공백 원소에 항등 아님 — 수정 저장 시 중복 제거는 바람직한 동작. (5) 클라 검증 우회 가능 — §11.3이 B9 절충으로 이미 명시(설계). (6) app이 못 그리는 `options`를 fetch — 계약 파리티(10.1 선례, Epic 16). (7) F1 vs F2 fallback 해석 — "상위 3~4개만"이 F1(상위 N 채움)을 지지, 스펙이 근거와 함께 F1 채택. (8) §11 "값 정본" 문구 긴장(전량 목록은 options.ts에) — P2 정확일치 테스트가 코드↔문서를 락스텝으로 묶어 실질 무의미화.

### 2026-07-22 — Review pass (후속/follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 9: (high 0, medium 0, low 9)
- addressed_findings:
  - `[low]` `[patch]` FP1 — `optionPriority`가 `OPTION_PRIORITY[name]`을 직접 읽어 'toString'·'constructor' 같은 Object.prototype 상속 키가 **함수**를 돌려주고 `!== undefined`를 통과했다(엣지케이스 레인이 실행으로 확인: `optionPriority('toString')`→함수, `topOptions` 정렬에서 정크가 보편 `후방카메라` 위로 올라감 — 코드 주석·기존 테스트가 막겠다던 바로 그 계약을 어김). `Object.prototype.hasOwnProperty.call(OPTION_PRIORITY, name)` 조회로 바꿔 통제어휘 밖 prototype 키도 `TIER_COMMON`(0)으로 강등. 테스트 신설(toString/constructor/valueOf/hasOwnProperty/__proto__→0, `topOptions(['후방카메라','toString'])`가 정크를 위로 안 올림).
  - `[low]` `[patch]` FP2 — `groupByCategory`가 dedupe를 안 해(카드 `topOptions`는 지난 패스 P4에서 dedupe 도입) 같은 `text[]`에 중복 원소가 오면 카드는 칩 1개·상세는 2개로 **두 화면이 같은 데이터에 다른 칩**을 그렸다(적대·엣지케이스 수렴). `groupByCategory`에도 seen-set 추가. 테스트 신설(`['선루프','선루프','후방카메라']`→각 1개).
  - `[low]` `[patch]` FP3 — web 읽기 경로(`topOptions`/`groupByCategory`)가 비문자열 원소를 안 걸렀다 — api `rows_to_cards`·app `_asStringList`는 **이 diff에서 같은 방어를 추가**했는데 web만 빠져, DB `text[]`의 NULL 원소가 `optionPriority(null)`→키 `"null"`→blank 칩으로 렌더될 수 있었다(엣지케이스). 두 함수에 `typeof !== 'string'` skip 추가(dedupe 루프에 흡수). 테스트 신설(NULL 섞인 입력→걸러짐).
  - **red/green 실측(메인루프 직접):** 세 수정을 전부 되돌림(`git checkout dcc1194 -- options.ts`) → 신설 4테스트만 red·나머지 23 green → 복원 27/27 green. 각 테스트가 자기 수정을 실제로 잡음을 확인.

4개 리뷰 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 재실행(전부 opus, 무맥락 새 세션). **intent_gap·bad_spec 0** — 의도정합 레인이 이 diff가 방어 가능한 해석(순수함수 계약 = 해석 B)을 충실히 구현했고, D5 truncate-only·top-4 고정·티어 상수형이 모두 인텐트가 허용한 좁힘임을 재확인. 표면화한 것은 신규 `options.ts` 순수함수의 견고성 결함 3건(FP1 prototype 누출은 엣지케이스 레인이 실행으로 확정)뿐이라 전부 patch로 흡수.

- **defer 1건 → `docs/tech-debt.md` #115 신규 등재**(동결 `deferred-work.md` 아님, 프로젝트 규칙 우선): `sprint-status.yaml`의 `last_updated`가 산문·백틱·괄호를 담은 거대 단일 인용부호 스칼라라 아포스트로피 하나로 YAML 파싱이 깨질 수 있다 — 이미 커밋 `14f84e0`에서 한 번 발생·복구된 표준화 지뢰(low). 트리거: 다음 `last_updated` 편집·확장 시 블록 스칼라(`|`)로 전환.
- **reject 9건**(전부 low): (1) 편집 모드에서 통제어휘 밖 기존 옵션 보유 매물 저장 차단 — 인텐트가 명시적으로 쓰기 차단을 요구하고 데모 데이터는 전부 통제어휘 안(커버리지 보장)이라 미발생, 10.4 피커가 구조적 해소(직전 패스 reject #1과 동일 판단). (2) 줄바꿈 구분자도 값-내-줄바꿈엔 쉼표와 같은 취약 — 텍스트에어리어로 입력 불가(Enter=새 옵션)·시드/API에만 이론상, 10.4가 제거(직전 reject #3). (3) 티어 락스텝 테스트가 문서 원문이 아니라 손복사 배열과 대조 — 마크다운 프로즈 파싱은 취약하고, 정확일치 테스트가 코드↔테스트 드리프트는 여전히 잡음(직전 #8). (4) 커버리지 테스트가 단방향(seed⊆vocab)·count/typo 역검 없음 — 인텐트 요구(seed 커버) 밖 gilding. (5) 통제어휘 밖 정크가 카드 칩 자리를 차지(TIER_COMMON) — P3의 의도적 결정, 상세는 기타옵션에 노출, 데모 미발생. (6) SellForm 블록 경로 통합/E2E 테스트 부재 — 인텐트가 "화면 아니라 순수함수에서 red"를 명시 채택 + 수동 브라우저 검증이 UI 커버(의도정합 레인이 방어 가능 확인). (7) app `_asStringList` 무테스트(api 미러는 테스트됨) — 옵션 위젯 렌더가 Epic 16 이관이라 현재 소비자 없음. (8) 카드 총 개수/"외 N" 표시 부재 — 기존 defer #114와 동일 항목. (9) app/api 정규화 패리티-바이-코멘트 드리프트 — 단순 방어 함수, Epic 16 통합.

## Auto Run Result

Status: done
Baseline: `3b029e7` → Final: (아래 커밋)

**구현 요약:** 옵션(`listings.options text[]`)에 통제어휘·`COMMON_OPTIONS`·`OPTION_PRIORITY` 상수를 `conventions.md §11` 단일 출처로 세우고 web 한 모듈(`options.ts`)이 미러했다. 카드는 우선순위 상위 4개(희소 우선, 없으면 보편 fallback) 칩을, 구매자 상세는 5개 엔카 카테고리 전량 그룹핑을 노출한다. `SellForm` 옵션 저장을 쉼표→줄바꿈으로 바꿔 대장 #11(쉼표 든 값 라운드트립 손실)을 web에서 닫고(app 미러는 #113→Epic 16), 쓰기 시 통제어휘로 검증한다. `options`를 ListingCard 계약에 §4.1 락스텝으로 추가(web/api/app 타입 + `SELECT_COLUMNS` + 카드 select 3곳, anon GRANT에 이미 있어 42501 회귀 없음).

**변경 파일(리뷰된 diff, `.bmad-loop/policy.toml` 제외):**
- `docs/conventions.md` — §4 카드필드에 `options` 행 + 새 §11(통제어휘·티어·왜 앱검증인지).
- `web/src/lib/options.ts` (신규) — 통제어휘(71) + 상수 + 순수헬퍼(`topOptions`·`groupByCategory`·`partitionOptions`·`parseOptionsInput`/`serializeOptions`), 단일 코드 출처.
- `web/src/lib/__tests__/options.test.ts` (신규) — 커버리지·티어 무결성·#11 라운드트립·순위·dedupe (23건).
- `web/src/components/listings/ListingCard.tsx` — `options` 필드 + 상위4 칩(D5 `flex-nowrap`+truncate, dedupe).
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` — `OptionsSection` 카테고리 그룹핑.
- `web/src/app/(user)/sell/SellForm.tsx` — 쉼표→줄바꿈 + 통제어휘 제출 검증.
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` — 카드 select에 `options`.
- `api/app/schemas/ai.py` · `api/app/graph/listing_cards.py` — ListingCard `options` + `SELECT_COLUMNS`(11→12) + 계약-외 정규화.
- `api/tests/{test_listing_cards,test_sql_rag_node,test_doc_rag_node,test_demo_acceptance}.py` — 12튜플 픽스처 + options degrade 테스트.
- `app/lib/features/listings/{listing.dart,listings_repository.dart}` — 카드 타입·select 파리티(위젯 렌더는 Epic 16).
- `docs/tech-debt.md` — #11 ✅해소(web) · #113 신규(app 미러→Epic 16) · #114 신규(카드칩 <640px→Epic 10.7).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 10-3 상태.

**리뷰 결과:** patch 4건(모두 적용·재검증) · defer 1건(#114) · reject 8건. 상세 위 Triage Log.

**Follow-up 리뷰 권고:** true. (이번 패스 patch 심각도: high 0, medium 2, low 2 → 점수 3×2 + 1×2 = 8 ≥ 5. P1이 스토리 헤드라인 AC와 직결돼 재확인 가치 있음.)

**검증(직접 실행·관찰):**
- web `npm run lint`/`tsc --noEmit`/`npm test`/`build` — 전부 통과, 162/162(패치 후, +5 신규). 메인루프가 직접 재실행 확인.
- `#11` red/green 직접 실측: `parseOptionsInput` 쉼표 split 원복 → 2건 red → 줄바꿈 복원 18/18 green.
- P2 무결성 red/green 직접 실측: HIGH에서 `'나파가죽시트'` 제거 → §11.2 정확일치 테스트 red → 복원 23/23 green.
- api `pytest` — 206 passed, 17 skipped(회귀 없음). flutter analyze 0 / test 80(구현 세션 보고).
- 구현 세션 브라우저 실측: 실 DB 매물(6옵션)로 anon `/search` 200(42501 없음), 카드 상위4 희소칩(통풍시트·파노라마선루프·어댑티브크루즈·헤드업디스플레이)이 보편 2개를 밀어냄, 상세 4카테고리 그룹핑.

**잔여 리스크:**
- 카드 옵션칩 <640px 1열 "외 N" 축약 미관측(#114, Epic 10.7 실측 예정) — D5 세로접힘은 구조적으로 불가.
- 통제어휘 앱 검증은 클라 층(§11.3 B9 절충 명시) — DB CHECK 아님, 옵션명 표준화는 무결성 계약이 아니라 의도적.
- app 폼 #11 미러 미해소(#113, Epic 16) · 통제어휘 앱 이식 미완(Epic 16).
- 잔여 아티팩트(리뷰된 diff 밖): `.bmad-loop/policy.toml`(bmad-loop 오케스트레이션 노브, 이 스토리와 무관 — 커밋하지 않음).

---

### 후속 리뷰 패스 (2026-07-22, follow-up)

직전 패스가 `followup_review_recommended: true`(patch 점수 8)라 무맥락 새 세션 4레인(적대·엣지케이스·검증갭·의도정합, 전부 opus)으로 재리뷰했다.

**결과:** intent_gap 0 · bad_spec 0 · **patch 3(전부 low)** · defer 1(#115) · reject 9. 상세는 위 Review Triage Log의 "(후속/follow-up)" 항목.

**적용한 patch(전부 신규 `web/src/lib/options.ts` 순수함수 견고성):**
- FP1: `optionPriority`의 prototype 키 누출(`OPTION_PRIORITY['toString']`→함수) → `hasOwnProperty.call` 조회로 강등. 엣지케이스 레인이 실행으로 확정한 실 결함.
- FP2: `groupByCategory` dedupe 부재(카드는 dedupe) → seen-set 추가, 카드·상세 일관.
- FP3: web 읽기 경로 비문자열 원소 미필터(api/app는 이 diff에서 방어 추가) → `typeof !== 'string'` skip.

**검증(메인루프 직접 실행·관찰):**
- `web/src/lib/__tests__/options.test.ts`에 4테스트 신설 → `npm run lint`/`tsc --noEmit`/`npm test`/`build` 전부 통과, **166/166**(직전 162 +4).
- red/green 직접 실측: 세 수정 되돌림(`git checkout dcc1194 -- options.ts`) → 신설 4테스트만 red·나머지 23 green → 복원 27/27 green.
- api·flutter 무변경(이번 패스는 web `options.ts`/테스트만 수정) → 회귀 없음.

**Follow-up 재권고:** false. (이번 패스 patch 심각도 high 0·medium 0·low 3 → 점수 3×0 + 1×3 = 3 < 5, high 없음.)
