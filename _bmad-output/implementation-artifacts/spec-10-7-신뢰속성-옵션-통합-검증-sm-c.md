---
title: 'Story 10.7 — 신뢰속성·옵션 통합 검증 (SM-C)'
type: 'chore'
created: '2026-07-22'
status: 'done'
baseline_revision: 'dbe7608'
final_revision: 'c8a6329'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-10-context.md'
  - '{project-root}/docs/tech-debt.md'
  - '{project-root}/web/AGENTS.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Epic 10은 신뢰속성(뱃지+면책)·희소 옵션 우선노출·NULL 제3상태를 각각 구현하고 단위테스트로 굳혔다(10.2 `TrustAttributes.test.ts`, 10.3 `options.test.ts`). 그러나 SM-C의 핵심 주장 — "카드에서 신뢰속성이 옵션과 **구분**돼 보이고, 면책이 뱃지와 함께 뜨고, 희소 옵션이 **우선 노출**된다" — 은 (1) **카드 조립 계층**에서 어떤 자동 검사로도 묶여 있지 않고(`ListingCard`를 건드리는 테스트가 0개 — 카드에서 `<TrustAttributes>`를 통째로 빼거나 `topOptions` 호출을 지워도 전 스위트 green), (2) 이를 눈으로 실증할 **대표 매물이 로컬에 결정적으로 존재한다는 보장이 없다**(`03_trust_demo.sql`은 신뢰 3컬럼만 심고 `options`는 운영 스냅샷 운에 맡긴다 → 신뢰속성 풀세트 + 희소 옵션을 **동시에** 가진 매물이 없을 수 있다).

**Approach:** SM-C를 **재현 가능한 exit-gate**로 굳힌다 — (a) `03_trust_demo.sql`이 대표 all-trust 매물에 희소(HIGH 티어) 옵션을 결정적·멱등으로 심어 SM-C 실증 매물을 항상 만들고, (b) `ListingCard` **조립 테스트**를 신설해 "카드가 `TrustAttributes(variant=card)`를 마운트 + 옵션 칩을 희소 우선 순서로 렌더 + 둘이 별개 노드"를 못 지워지게 박고(B9, `TrustAttributes.test.ts`의 함수호출-트리 기법 재사용), (c) 로컬 실 DB + 브라우저(Playwright MCP)로 카드·상세를 **네 상태**(무사고/사고/단순교환/NULL)로 실측해 SM-C·CM-C·제3상태를 눈으로 확인·기록한다. 이미 단위 커버된 로직(`getTrustDisplay` 결속·`topOptions` 랭킹·NULL 정규화)은 **중복 재작성하지 않는다**.

## Boundaries & Constraints

**Always:**
- 새 테스트는 **카드 조립 계층**(ListingCard가 신뢰 블록과 옵션 칩을 실제로 별개로 배치하는지)만 새로 덮는다 — 이미 커밋된 단위 커버(뱃지-면책 결속·NULL→null·희소 우선 랭킹)를 중복하지 않는다.
- `03_trust_demo.sql` 변경은 **additive·멱등**(`array_append` + 존재검사, DELETE 없음)이며 기존 게이팅(`do $$` 대상 미달 시 크게 실패)·행 선택 술어(`status='on_sale'` + `accident_free` + id 정렬)를 **보존**한다.
- 시드에 심는 희소 옵션명은 반드시 `HIGH_PRIORITY_OPTIONS`(`web/src/lib/options.ts`)/`conventions.md §11` 통제어휘 값이어야 한다(자유문자열 금지 — 통제어휘 위반이면 SM-C 데모 자체가 규약 위반이다).
- 브라우저 실측은 로컬 Supabase + 확장된 `03_trust_demo` 적용 후의 **실 DB**로 하고, 네 상태(무사고=초록·사고=중립칩·단순교환=중립칩·NULL=미표시)를 **모두** 관찰한다 — "에러 0"이 아니라 네 상태가 실제로 눈에 구분됨을 본다(B4).
- 실측 중 이미 대장에 있는 결함을 재발견하면 신규 등재하지 말고 번호만 참조한다: #106(커밋 E2E 부재)·#112(상세 사고정보 이중표시)·#114(카드 칩 좁은 폭 축약 부재)·#115(sprint-status YAML 취약).

**Block If:**
- 카드 조립 테스트가 `ListingCard`의 **실제 조립**을 검증할 수 없고(클라이언트 전용 import가 node vitest에서 `vi.mock`으로도 근본적으로 안 풀림), 남는 우회로가 전부 이미 커버된 로직의 재작성뿐이라면 — 즉 SM-C 조립을 못 잡는 "장식용 green 테스트"만 커밋하게 되는 상황이면 HALT(무의미한 검사를 커밋하지 않는다, B9).
- SM-C를 실측한 결과 **카드에서 신뢰속성과 옵션이 실제로 구분돼 보이지 않거나** 면책이 빠지는 경로가 발견되면(단순 스타일 결함이 아니라 SM-C 자체가 미착지), 이는 이 검증 스토리 범위를 넘는 기능 결함이므로 HALT(임의로 UI를 고치지 않는다 — A3).

**Never:**
- 새 프로덕션 기능(스키마·API·UI **동작** 변경) 추가 — 이건 exit-gate 검증 스토리다. 마이그레이션 신설 금지(`seed-local`은 마이그레이션이 아니다).
- 커밋된 Playwright 스펙 신설(리포 표준 = E2E는 수동 스크립트, #106) — 브라우저 실측은 1회 측정·기록에 그친다.
- 이미 단위 커버된 로직 재작성, `TrustAttributes.tsx`·`options.ts`·`ListingCard.tsx`의 **동작** 수정.
- 데이터 없는 지표(평판·응답률·인증 배지) 노출·가짜 검증 UI(CM-C·FR30 정직성).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 대표 매물 카드 | `accident_status='무사고'`, `is_single_owner=t`, `is_non_smoker=t`, `options=[희소1, 보편…]` | 초록 뱃지 3 + "판매자 제공 정보" 면책(뱃지와 한 몸) + 옵션 칩 **최상단에 희소1** | 정상 |
| 사고 매물 카드 | `accident_status='사고'` | 초록 아님·중립 상태칩 "사고", 면책은 그대로 | 정상 |
| NULL 매물 카드 | 세 컬럼 NULL | 신뢰 블록 미표시(빈 높이·빈 테두리 없음), 옵션·나머지 정상 | 정상 |
| 카드 조립 회귀 | `ListingCard(대표 fixture)` 함수호출 트리 | `TrustAttributes(variant='card')` 노드 존재 **and** 옵션칩 컨테이너 존재(별개 노드) **and** 칩 순서 = `topOptions(options,4)`, 첫 칩=희소1 | 단언 실패 = red |
| 옵션 없는 카드 조립 | `options=[]` | 옵션칩 컨테이너 부재(`cardOptions.length===0` 가드), `TrustAttributes`는 **여전히** 마운트 | 단언 실패 = red |
| 상세 신뢰 섹션 | 대표 매물 상세 | 신뢰정보(긴 UX-DR19 면책) → 차량 → 옵션 → 판매자 순서, 신뢰↔옵션 **별개 섹션** | 정상 |
| 시드 멱등 | `03_trust_demo` 2회 실행 | 대표 행 `options`에 희소 **중복 안 생김**(존재검사), 값 동일 | 재실행 동일 |

</intent-contract>

## Code Map

- `supabase/seed-local/03_trust_demo.sql` -- **수정**. 대표 all-trust 2행(현재 첫 `update … set accident_status='무사고' …`의 대상)에 `HIGH_PRIORITY_OPTIONS` 중 1개를 **멱등 append**하도록 확장. 기존 게이팅 `do $$`·행 선택 술어·나머지 UPDATE는 그대로.
- `web/src/components/listings/ListingCard.tsx` -- **읽기 전용(수정 없음)**. 조립 테스트 대상. 신뢰 블록 = line 66 `<TrustAttributes variant="card" listing={listing} />`, 옵션 칩 = line 100–111 `topOptions(listing.options, CARD_OPTION_COUNT=4)` 결과. 둘은 title/meta/price를 사이에 둔 별개 형제 노드.
- `web/src/lib/options.ts` -- **읽기**. `topOptions`(line 243)·`HIGH_PRIORITY_OPTIONS`(line 132) — 시드에 심을 희소 옵션명 및 테스트 기대 순서의 출처.
- `web/src/components/listings/TrustAttributes.tsx` -- **읽기**. 기본 export `TrustAttributes`(테스트에서 element `type` 매칭용). 뱃지-면책 결속·NULL 정규화는 이미 `TrustAttributes.test.ts`가 커버.
- `web/src/components/listings/__tests__/ListingCard.test.ts` -- **신규**. `ListingCard`를 함수로 호출해 반환 element 트리에서 (1) `TrustAttributes`(variant='card') 노드, (2) 옵션칩 컨테이너와 칩 순서(희소 우선), (3) NULL·빈옵션 분기를 단언. `TrustAttributes.test.ts`의 node-env·함수호출 트리 관례를 따르고, 클라이언트 import(`WishButton`·`next/link`·`ListingCardImage`)가 node에서 문제되면 `vi.mock`으로 스텁.
- `docs/tech-debt.md` -- **조건부**. 실측 중 **신규** 결함이 나오면 형식대로(`### N. …` + 위치/무엇/실측/트리거) 등재. 이미 등재분(#106·#112·#114·#115) 재발견은 번호만 참조, 신규 등재 금지(오케스트레이터 소유).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- 10-7 상태 갱신. `last_updated`는 **단순 스칼라 유지**(#115 — 인용부호·괄호·백틱 금지).

## Tasks & Acceptance

**Execution:**
- `supabase/seed-local/03_trust_demo.sql` -- 대표 all-trust 2행 `options`에 HIGH 티어 옵션 1개 멱등 append -- SM-C 실증 매물을 스냅샷 운에 안 맡기고 결정화(finding-5).
- `web/src/components/listings/__tests__/ListingCard.test.ts` -- 카드 조립 테스트 신설(신뢰블록 + 희소우선 옵션칩 + 별개 노드 + NULL/빈옵션 분기) -- SM-C의 "구분 + 우선노출"을 카드 계층에 못 지워지게 박음(B9). red/green 실측 필수.
- 실 DB + 브라우저 실측 -- 네 상태 카드·상세 관찰·기록(SM-C·CM-C·NULL) -- 색·아이콘·레이아웃은 vitest가 못 보므로 1회 측정·기록(house pattern, E2E 부재=#106).
- `docs/tech-debt.md` / `sprint-status.yaml` -- (조건부) 신규 결함 등재 + 상태 갱신 -- 대장·스프린트 정합(B8).

**Acceptance Criteria:**
- Given 대표 매물(무사고+1인소유+비흡연 + 희소 옵션), when 카드를 렌더하면, then 초록 신뢰 뱃지 3개 + "판매자 제공 정보" 면책이 **한 몸으로**, 그리고 **희소 옵션이 옵션 칩 최상단**에 표시된다(SM-C — 실 DB + 브라우저 실측).
- Given `ListingCard` 조립, when 대표 fixture로 함수호출 트리를 검사하면, then `TrustAttributes(variant='card')` 노드와 옵션칩 컨테이너가 **별개로** 존재하고 칩 순서가 `topOptions(options,4)`와 일치한다(희소 우선) — 커밋된 vitest, 신뢰 블록/`topOptions` 사용을 제거하면 red.
- Given 미입력(NULL) 신뢰속성 매물, when 카드·상세를 렌더하면, then 초록 뱃지도 사고 표시도 없이(제3상태) 빈 잉크 없이 정상 렌더된다(브라우저 실측 + 조립 테스트 NULL 분기).
- Given 신뢰 뱃지가 뜨는 모든 경로, when 렌더하면, then 면책 라벨이 **항상 함께** 뜬다(CM-C 재확인 — 카드는 `TrustAttributes` 마운트 단언으로, 결속 자체는 기존 `TrustAttributes.test.ts`로).
- Given `03_trust_demo`를 2회 실행, when 시드를 재적용하면, then 대표 행 `options`에 희소가 **중복되지 않고** 값이 동일하다(멱등).
- Given 실측 중 이미 대장에 있는 결함(#106·#112·#114·#115)을 재발견, when 기록하면, then 신규 등재 없이 번호만 참조한다.

## Spec Change Log

(없음 — bad_spec 루프백이 없었다.)

## Review Triage Log

### 2026-07-22 — Review pass (4레인: 적대·엣지케이스·검증갭·의도정합)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 0, low 8)
- defer: 0
- reject: 7
- addressed_findings:
  - `[low]` `[patch]` `ListingCard.test.ts`의 `expect(trustNodes[0].props?.children).toBeUndefined()`가 동어반복(self-closing이라 children은 항상 undefined) — 오해 소지 있는 주석과 함께 제거, 별개-노드 증거는 트리에서 두 노드를 각각 찾는 것으로 이미 성립함을 주석에 명시.
  - `[low]` `[patch]` 함수호출-트리 기법이 ListingCard의 동기·훅없음에 의존하는데 실패 모드 경고가 없음 — async/훅 전환 시 렌더 하네스로 이관하라는 ⚠️ 주석 추가.
  - `[low]` `[patch]` SM-C는 카드+상세 두 표면인데 커밋된 조립 가드가 카드만 덮음(상세 `TrustInfoSection`/`OptionsSection` 무커버) — `detailSectionsAssembly.test.ts` 신설(4건: detail 뱃지 마운트·NULL 섹션 숨김·옵션 칩 렌더·빈옵션 문구). red/green 실측: detail `<TrustAttributes variant="detail">` 제거 시 red, 원복 green.
  - `[low]` `[patch]` 시드의 데모 불변식(대표 2행이 실제로 희소 옵션을 가짐)이 수동 재실행으로만 검증됨 — `03_trust_demo.sql`에 사후 `do $$` 게이트 추가(대표 2행에 '파노라마선루프'가 안 심겼으면 raise). 로컬 DB red/green 실측: 한 행에서 옵션 제거 후 게이트가 raise(롤백), 정상 시 통과.
  - `[low]` `[patch]` 시드 주석이 `options.ts:134` 라인번호 하드코딩(라인 로트) — 심볼명·§11.2 참조로 교체.
  - `[low]` `[patch]` #115(sprint-status YAML 지뢰) 트리거가 발동(바로 그 `last_updated` 줄을 편집)했는데 dev가 더 취약한 무인용 plain 스칼라로 바꿈 — #115 지정 픽스인 **블록 스칼라(`last_updated: |`)** 로 전환, `yaml.safe_load` 파싱 실측. #115를 ✅ 해소로 종결.
  - `[low]` `[patch]` #114(카드 칩 좁은폭 "외 N" 부재) 트리거가 10.7을 결정 지점으로 지정했는데 결정 미기록 — 390px 실측 + **현행 유지** 결정 근거(희소 우선노출이 잘림과 무관하게 성립, "외 N"은 SM-C 필수 아닌 폴리시)를 대장에 등재, ✅ 판단 완료로 종결.
  - `[low]` `[patch]` #112(상세 사고정보 이중표시)가 10.7을 후보 조정 지점으로 명명 — 검증 전용 스코프에서 조정 안 함 + 근거(#108 쓰기경로 전엔 모순 불가·A2)를 대장에 기록, 열린 채 유지.
- rejected: 7 — (1) epic-10 done인데 #109로 anon엔 신뢰뱃지 비노출: §9.3(b) 승인 필요라 무인 불가, 이미 대장 등재·잔여 리스크로 표기·B5 고지 대상 → 신규 조치 없음. (2) SM-C 시각 주장이 CI 가드 없음(수동만): 리포 표준=E2E 수동(#106), Auto Run Result에 정직 명시. (3) 10.6 핸드오프의 vitest 201 vs 실제 205 불일치: 선행 스토리 기록 문제, 본 스토리 카운트(205→212)는 실측 정확. (4) 카드 NULL 테스트가 컴포넌트 미확장: NULL 뱃지억제는 `TrustAttributes.test.ts` 담당(위임), 카드 테스트는 조립만 봄이 의도. (5) `findChipContainer` all-span 휴리스틱 취약: 대안(data-testid)은 읽기전용 소스 수정 필요, 3레인이 현 유일매칭 확인. (6) 희소우선이 주입 2행으로만 실증: 결정적 데모가 시드의 의도된 목적. (7) 카드계층 면책 미단언: 결속은 `TrustAttributes.test.ts` 렌더층 + 카드 마운트 단언이 이미 가드.

## Design Notes

**왜 카드 조립 테스트가 새로 필요한가(중복 아님).** SM-C의 로직 절반(뱃지-면책 결속·희소 랭킹)은 10.2/10.3 단위테스트가 이미 덮는다. 그러나 "카드가 그 둘을 실제로 **별개 블록으로 조립**한다"는 어떤 테스트도 안 본다 — `ListingCard`를 건드리는 테스트가 0개다(조사 실측). 카드에서 `<TrustAttributes>`(line 66)를 통째로 빼거나 `topOptions` 호출(line 53)을 지워도 전 스위트 green이다. 그 회귀를 잡는 게 이 스토리의 커밋 산출물이며, SM-C를 "만들었다"가 아니라 "잡는다"로 굳히는 자리다(B4).

**함수호출 트리 기법(`TrustAttributes.test.ts`와 동일).** vitest는 node 환경이라 DOM에 마운트하지 않지만, `ListingCard`를 함수로 부르면 React element 트리(순수 객체)가 반환된다. `topOptions`는 그 안에서 **실제 실행**되고, `<TrustAttributes>`·`<WishButton>`은 확장되지 않는 element 노드(`{type, props}`)로 남는다 — 그래서 "카드가 `TrustAttributes`(variant='card')를 자식으로 두는지"와 "옵션 칩 순서"를 트리 순회로 단언할 수 있다. `WishButton`/`next/link`/`ListingCardImage`가 node import를 깨면 `vi.mock`으로 스텁한다(표준 vitest, 최소 개입).

**왜 시드에 옵션을 심나.** `03_trust_demo`는 이미 "뱃지를 눈으로 보려면 대표 소수에 값을 심어야 한다"는 이유로 trust 3컬럼을 UPDATE한다. SM-C의 옵션 절반도 같은 이유로 결정화가 필요하다 — 스냅샷이 그 행에 희소 옵션을 담았는지는 보장이 없다(finding-5). 같은 파일·같은 행·같은 근거라 응집적이다. 멱등 골든 예시(대상은 기존 첫 UPDATE의 2행):
```sql
-- 기존 첫 UPDATE(무사고+1인소유+비흡연)의 대상 2행에, 희소 옵션 1개를 멱등 append
update public.listings
   set options = array_append(coalesce(options, '{}'), '파노라마선루프')
 where id in (
   select id from public.listings
    where status = 'on_sale' and accident_free = true
    order by id limit 2
 )
   and not ('파노라마선루프' = any(coalesce(options, '{}')));
```
`'파노라마선루프'`는 `HIGH_PRIORITY_OPTIONS`(options.ts:134) 멤버다 — 다른 HIGH 멤버로 바꿔도 되나 반드시 통제어휘 안이어야 한다.

**왜 커밋 Playwright를 안 만드나.** 리포 표준은 "E2E는 수동 스크립트, vitest는 순수 로직만"이고 커밋된 Playwright 스펙이 0개인 것 자체가 #106으로 이미 추적 중이다. 색·아이콘이 실제 브라우저에 그려지는지는 E2E-only이므로 1회 측정·기록하고 새 커밋 하네스를 만들지 않는다(A2 단순함 우선).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 errors
- `cd web && npx tsc --noEmit` -- expected: 타입 에러 0(신규 테스트 포함)
- `cd web && npm run test` -- expected: 기존 + 신규 `ListingCard.test.ts` 전부 green. **red/green 실측**: 카드 조립 단언(`TrustAttributes` 노드 존재 or 칩 순서)을 일부러 깨서(기대 반전) red 확인 → 원복 green.
- `cd web && npm run build` -- expected: 빌드 성공(클라이언트/서버 경계 위반 없음)
- `cd api && pytest`(+ `api-db` integration) -- expected: 기존 green(이 스토리는 api를 안 건드리므로 회귀 없음 확인만). 신규 마이그레이션 없음 → 마이그레이션 게이트 무변.

**Manual / measured (E2E — 커밋 하네스 없음, house pattern):**
- 로컬 Supabase 기동 → `scripts/seed-local.sh`(02→03 순서, **확장된 03 포함**) 적용 → `cd web && npm run dev`. Playwright MCP로 목록/검색에서 **대표 all-trust 카드**: 초록 뱃지 3 + "판매자 제공 정보" 면책 + **희소 옵션 칩 최상단** 관찰·스크린샷. 상세 진입: 신뢰정보(긴 면책)→차량→옵션→판매자 순서, 신뢰↔옵션 **별개 섹션** 확인. **사고·단순교환·NULL** 매물 각 1건: 색·상태칩·미표시가 네 상태로 구분됨을 관찰. 로그인/비로그인 둘 다 신뢰 섹션이 뜨는지(anon 조회 가능, 10.1/10.2) 확인. 찾은 텍스트/셀렉터·스크린샷을 `## Auto Run Result`에 수치·근거로 기록("에러 0"이 아니라 네 상태가 구분됨을 본다).
- 로컬 브라우저 환경이 못 뜨면(로컬 Supabase·dev 기동 불가) 그 항목만 **escalate**로 기록(사용자 직접 실측), 커밋 산출물(seed+test+suite)은 진행한다.

## Auto Run Result

Status: done

**구현 요약:** Epic 10의 마지막 통합 검증 스토리(SM-C). 신뢰속성(뱃지+면책)·희소 옵션 우선노출·NULL 제3상태는 10.2/10.3이 이미 구현·단위테스트로 굳혔으므로 **중복하지 않고**, SM-C를 재현 가능한 exit-gate로 굳히는 데 집중했다 — (a) 시드가 대표 매물을 결정화하고, (b) 카드·상세 **조립 계층** 회귀 가드를 커밋하고, (c) 로컬 실 DB + 브라우저로 네 상태(무사고/사고/단순교환/NULL)를 실측했다.

**변경 파일:**
- `supabase/seed-local/03_trust_demo.sql` — all-trust 대표 2행에 희소(HIGH 티어) 옵션 `파노라마선루프`를 멱등 append(`array_append`+존재검사) → SM-C 실증 매물 결정화(finding-5). **사후 게이트 `do $$` 추가**(대표 2행에 옵션이 실제로 심겼는지 raise로 강제 — "에러 없음"이 아니라 "불변식 성립"을 검사, B4).
- `web/src/components/listings/__tests__/ListingCard.test.ts` (신규 3건) — 카드가 `TrustAttributes(variant='card')`와 옵션칩 컨테이너를 **별개 노드로** 조립 + 칩 순서=`topOptions(options,4)`(희소 최상단) + NULL·빈옵션 분기. (리뷰 패치: 동어반복 단언 제거 + 기법 전제 ⚠️ 주석.)
- `web/src/app/(user)/listings/[id]/__tests__/detailSectionsAssembly.test.ts` (신규 4건, 리뷰 패치 VG-1) — 상세 `TrustInfoSection`이 `<TrustAttributes variant='detail'>` 마운트·NULL이면 섹션 숨김, `OptionsSection`이 옵션 칩(`<li>`) 렌더·빈옵션 문구. SM-C 카드+상세 비대칭 해소.
- `docs/tech-debt.md` — #114 ✅ 판단 완료(현행 유지 근거) · #115 ✅ 해소(블록 스칼라 전환) · #112 10.7 검토 기록(열린 채 유지) · 🟢/🟡 요약행 ✎ 노트.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 10-7 done, epic-10 done. `last_updated`를 YAML **블록 스칼라**로 전환(#115 지정 픽스).

**검증(오케스트레이터 직접 재실행):** web `lint`(0)·`tsc --noEmit`(0)·`test`(**212 passed**/16파일, 기존 205+카드3+상세4)·`build` 통과. 신규 두 가드 red/green 실측: 카드 `<TrustAttributes>` 마운트 제거→red·원복 green; 상세 `variant='detail'` 마운트 제거→red·`git checkout` 원복(바이트 동일)·green. 시드: 로컬 Supabase(55322)에 `03_trust_demo.sql` 2회 실행 → 대표 2행 `has_rare=t`, 재실행 시 append `UPDATE 0`(멱등), 사후 게이트 통과(green); 트랜잭션에서 한 행 옵션 제거 후 게이트가 `raise`(red) 확인 후 rollback(DB 무손상). api는 미변경이라 회귀 없음(읽기전용 소스·api/ diff 공집합 확인). YAML `yaml.safe_load` 파싱 확인(10-7/epic-10 = done).

**브라우저 실측(dev 세션, 로컬 Supabase):** 대표 all-trust 매물이 카드·상세에서 초록 뱃지 3 + "판매자 제공 정보" 면책이 한 몸으로, 옵션칩 최상단 `파노라마선루프` 확인. 상세 섹션 순서(신뢰정보→차량→옵션→판매자, 별개 섹션) 확인. 사고/단순교환/NULL 세 상태가 카드에서 서로 구분됨(무사고=초록 체크, 사고·단순교환=중립칩, NULL=신뢰블록 미표시·빈 여백 없음) 스크린샷 확인. 390px에서도 뱃지·면책 정상.

**리뷰 결과:** 4레인(적대·엣지케이스·검증갭·의도정합) 실행 → **patch 8(전부 low)·reject 7·intent_gap 0·bad_spec 0.** 상세는 Review Triage Log 참조.

**후속 리뷰 권고:** **true** (patch low 8 → 3×0+1×8=8 ≥ 5). low 하드닝·테스트 완결성 위주라 코드 위험은 낮으나 커밋 가드·시드를 여럿 건드려 1회 재리뷰 권고.

**잔여 리스크 / 사용자 확인 필요(B5):**
1. **#109 — 비로그인(anon) 사용자는 신뢰 뱃지를 못 본다.** Epic 10의 간판 기능인데 anon GRANT 미승인이라 로그아웃 상태에선 신뢰속성 3컬럼이 아예 조회되지 않는다. 해소하려면 **§9.3(b) 사용자 승인 + anon GRANT 마이그레이션**이 필요해 무인 실행 범위 밖(대장 #109). epic-10을 done으로 닫되 이 제약을 명시적으로 남긴다 — **탐색 단계 신뢰 표시를 원하면 이 승인이 선행돼야 한다.**
2. **SM-C의 시각 주장은 CI 자동 가드가 없다(#106).** 색·아이콘·시각 분리는 리포 표준상 E2E-only(커밋 Playwright 0개)라 이번에도 1회 수동 실측·기록에 그쳤다. 카드·상세 **조립**은 vitest가 잡지만, 렌더된 픽셀 구분은 수동 확인이다.
3. **로컬 `authenticated` 롤 GRANT 공백(#120)** — 로컬 db reset 시 로그인 경로가 막혀 dev가 세션 전용 grant로 우회(마이그레이션 아님·커밋 안 됨). 운영 Supabase는 플랫폼 기본권한이 있어 무관.
