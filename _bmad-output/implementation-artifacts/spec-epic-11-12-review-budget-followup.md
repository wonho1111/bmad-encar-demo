---
title: 'Epic 11+12 리뷰 예산 소진 후속 독립 리뷰 (DW-1~DW-9)'
type: 'chore'
created: '2026-07-30'
status: 'done'
baseline_revision: 'b0fb2a863601411fadbf42fae299e59818ed3b2c'
final_revision: '0ef5bd052d8bd2e0d5b1debe8345bdeb89bfc7f7'
review_loop_iteration: 0
followup_review_recommended: true
context: []
warnings: ['deferred-work.md는 grep 키워드 대조만 했고 전체를 다 읽지는 않음 — 중복 후보가 남아있을 여지 있음', 'defer-to-ledger 표준 처리를 호출 프롬프트 지시로 오버라이드함(아래 Never 절 참고)']
---

<intent-contract>

## Intent

**Problem:** 스토리 11-0, 11-1, 11-2, 11-5, 12-1, 12-3, 12-4, 12-5, 12-6 아홉 건은 각각 리뷰 예산(2 사이클)을 다 쓴 채 `review-budget-committed` 이벤트 직후 바로 `story-done`으로 종료됐고, 이후 그 diff를 실제로 들여다본 리뷰 세션이 한 번도 없다(대장 DW-1~DW-9). CLAUDE.md B4는 코드리뷰가 새 세션에서, 스토리 자신의 트리아지 로그가 아니라 실제 diff를 읽고 돌아야 한다고 못박는다.

**Approach:** 아홉 커밋 각각(스토리별 1커밋, 이미 병합됨)의 실제 diff를 대상으로, 이 프로젝트에 설정된 4개 리뷰 레이어(blind-hunter, edge-case-hunter, verification-gap, intent-alignment)를 사전 대화 맥락이 없는 새 세션들로 병렬 실행한다. 결과를 트리아지해 이 spec 파일에만 기록한다 — 대장(`deferred-work.md`)은 오케스트레이터가 이 결과를 읽고 직접 갱신하므로 이 실행은 절대 건드리지 않는다. 이 제약의 출처는 `intent.md` 본문이 아니라, 이 실행을 시작한 `/bmad-dev-auto` 호출 프롬프트 자체다: "Do NOT edit the deferred-work ledger; the orchestrator records resolution." (intent-alignment 감사에서 이 출처가 spec에 명시돼 있지 않다는 지적을 받아 여기 원문을 인용해 명확히 한다.)

## Boundaries & Constraints

**Always:**
- 리뷰 대상은 정확히 이 9개 커밋으로 한정한다: `b76ec57`(11-0), `d6548a9`(11-1), `48427e3`(11-2), `51c6154`(11-5), `fbdd5a0`(12-1), `b581b45`(12-3), `4ec2075`(12-4), `dd000bb`(12-5), `dfc3aaa`(12-6). 각 SHA·스토리 매핑은 `git show --format="%H %s"`로 사전에 실측 검증했다(9/9 일치).
- 4개 리뷰 레이어는 사전 대화 맥락이 전혀 없는 새 subagent로 실행한다(`Agent` 도구, 동기 호출). 각 레이어는 9개 커밋의 실제 diff(`git show`) 전체를 받으며, 스토리 자신의 spec 파일이나 트리아지 로그는 참고 자료로도 건네지 않는다(CLAUDE.md B4).
- 트리아지에서 실제로 확인된(reproduced) 발견만 유효로 센다 — 추정이나 다수결만으로 결론 내지 않는다. 상위 severity 항목은 이 세션이 직접 `grep`/`Read`로 재확인한다.
- 새로 발견된 실질적 이슈는 이 spec의 `## Auto Run Result`에 "신규 DW 후보"로 초안만 남긴다(제목/severity/근거 diff 위치) — `deferred-work.md`에 직접 append하지 않는다.
- 아무 새 이슈도 안 나오면 "새 이슈 없음"과 함께 실제로 리뷰한 9개 커밋의 SHA를 결과에 명시한다.

**Block If:** 리뷰 중 아홉 커밋 중 하나라도 이미 병합된 상태와 다르게 관측되면(커밋이 존재하지 않거나 diff가 예상과 다르면) HALT.

**Never:** 이 실행에서 `deferred-work.md`를 append/수정하지 않는다(위 Approach에 인용한 호출 프롬프트가 명시적으로 금지 — 표준 step-04의 defer 처리를 이 실행에 한해 오버라이드한다). 아홉 스토리의 이미 확정된 설계 결정(회고·대장에 근거로 남은)을 새 근거 없이 재론하지 않는다. 이 리뷰 범위 밖 코드(11-3, 11-4, 12-2 등 — 이 번들에 없는 스토리)를 **대상으로 삼아 새로 조사·판정하지 않는다** — 단, 이 9개 커밋에서 나온 발견을 반증하거나 영향 범위를 설명하기 위해 참고하는 것은 허용한다(예: 오탐 판정, 리스크 설명).

</intent-contract>

## Code Map

- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-1~DW-9 원문 소재. 읽기 전용, 절대 수정 금지.
- 커밋 `b76ec57`, `d6548a9`, `48427e3`, `51c6154`, `fbdd5a0`, `b581b45`, `4ec2075`, `dd000bb`, `dfc3aaa` -- 리뷰 대상 diff 원본(`git show <sha>`로 취득, 총 11개 커밋 stat 기준 약 9.8k줄 삽입).
- `_bmad/custom/bmad-dev-auto.toml` / `.user.toml`(있다면) -- `review_layers` 4종의 실제 프롬프트 정의(customize resolver로 이미 로드됨).

## Tasks & Acceptance

**Execution:**
- (subagent, 새 세션) `git show <9개 SHA>` -- 9개 커밋 diff를 확보 -- 스토리 자신의 트리아지 로그가 아니라 diff 자체를 읽는다(CLAUDE.md B4)
- 4개 리뷰 레이어(blind-hunter, edge-case-hunter, verification-gap, intent-alignment)를 새 세션 subagent로 병렬 실행, 위 diff와 이 spec의 intent-contract를 전달 -- 독립적 관점 4개로 놓친 문제를 잡는다
- 각 레이어 결과를 중복 제거 후 개별 판정(severity + 실재 여부, 상위 항목은 코드 재확인) -- 노이즈와 실제 이슈를 가른다
- 실제 이슈는 "신규 DW 후보"로 spec 결과에 초안 기록, 노이즈는 폐기 -- 대장 갱신은 오케스트레이터 몫이므로 여기서는 기록만
- `## Auto Run Result`에 리뷰한 커밋 범위, 레이어별 발견 요약, 트리아지 결과, 신규 DW 후보(있다면) 기록 -- 오케스트레이터가 DW-1~DW-9 종결 및 신규 DW 등재에 쓸 유일한 근거

**Acceptance Criteria:**
- Given 9개 커밋의 diff, when 4개 리뷰 레이어가 새 세션에서 병렬 실행되면, then 각 레이어의 원 발견이 spec에 요약 기록된다
- Given 트리아지 결과 새 이슈가 없으면, when spec을 마무리하면, then "새 이슈 없음 + 리뷰한 9개 커밋 SHA"가 명시적으로 기록된다
- Given 트리아지 결과 실제 새 이슈가 있으면, when spec을 마무리하면, then 각 이슈가 제목/severity/근거를 갖춘 신규 DW 후보로 기록되고 `deferred-work.md`는 변경되지 않는다

## Spec Change Log

## Review Triage Log

### 2026-07-30 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 0, medium 2, low 10)
- defer: 0
- reject: 8 (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` 신규 DW 후보 5건에 근거 diff 위치(원 커밋 SHA)가 빠져 있던 것을 각 후보에 추가(blind-hunter #7)
  - `[medium]` `[patch]` `deferred-work.md`를 건드리지 않는 제약의 출처가 spec 안에 없어 intent-alignment 감사가 이를 "verbatim intent와 배치"로 오인한 것을 — 실제 출처(`/bmad-dev-auto` 호출 프롬프트)를 Approach에 원문 인용해 명확히 함(intent-alignment)
  - `[low]` `[patch]` frontmatter `warnings: []`가 비어 있던 것을 실제 잔여 리스크·오버라이드 사실로 채움(blind-hunter #1/#15, edge-case-hunter #1/#2)
  - `[low]` `[patch]` `followup_review_recommended: false`가 신규 이슈 발견과 모순돼 보이는 것에 대해 필드 정의(패치 심각도 전용) 설명을 Auto Run Result에 추가(blind-hunter #1, edge-case-hunter #1)
  - `[low]` `[patch]` 신규 후보 #1(조회수 랭킹 조작)이 코드 읽기로만 확인되고 실제 재현(RPC 반복 호출)은 안 했다는 한계를 명시(blind-hunter #3)
  - `[low]` `[patch]` 신규 후보 #4를 유지하면서 비슷하게 "현재 도달 불가"인 다른 기각 항목과 왜 다르게 판정했는지 구분 기준(외부 라이브러리 콜백 순서 vs 이 코드 자체 변경 필요)을 명시(blind-hunter #4)
  - `[low]` `[patch]` 11-1 마이그레이션 게이트 반증이 "현재" 시점 재실행 결과이지 병합 당시 증거는 아니라는 한계를 명시(blind-hunter #6)
  - `[low]` `[patch]` `deferred-work.md` 중복 판정이 grep 대조뿐이라는 한계를 기각 목록에도 재명시(blind-hunter #8/#9)
  - `[low]` `[patch]` verification-gap 레이어가 다른 레이어보다 원 발견이 적었던 이유(9개 커밋 대부분 이미 어떤 형태로든 테스트 보유)를 명시(blind-hunter #10)
  - `[low]` `[patch]` Block If 판정 근거로 SHA-제목 매핑뿐 아니라 각 커밋의 stat(파일 수·삽입/삭제 줄 수) 대조도 했음을 명시(blind-hunter #12)
  - `[low]` `[patch]` "총 21건 중 발췌"가 실제로는 21건(원 발견)=5건(승격)+16건(기각)이라는 산식이 안 보이던 것을 명시(edge-case-hunter #6)
  - `[low]` `[patch]` Never 절의 "11-3/11-4는 건드리지 않는다"가 실제로는 "오탐 반증·영향 설명 목적 참고는 허용"이라는 경계였음을 명시(blind-hunter #2, edge-case-hunter #7)
  - (reject 8건: intent-alignment 레이어가 코드 결함을 안 낸 것은 그 레이어의 설계된 역할이라 결함 아님(blind-hunter #11) / status가 `in-review`에 머무는 것은 이 실행의 다음 단계인 Finalize가 즉시 처리하므로 결함 아님(blind-hunter #13) / 중첩 subagent 구조는 dev-auto 표준 오케스트레이션 패턴이라 이 실행 고유 문제 아님(blind-hunter #14) / Auto Run Result가 원 로그를 첨부하지 않고 서술형인 것은 spec 템플릿의 설계된 형식이며 검증 수행 절에 실행한 명령은 이미 나열돼 있음(blind-hunter 전체 self-attestation 지적) / HALT 결과 포맷·리뷰 레이어 실패 처리·심각도 상충 시 우선순위 규칙·high severity 전용 처리 경로가 spec에 없다는 4건(edge-case-hunter #3/#4/#5/#8)은 이번 1회성 chore 실행에서 실제로 발생하지 않은 가상 시나리오이며, 반복 실행되는 스크립트가 아니므로 CLAUDE.md A2(추측성 확장 금지)에 따라 지금 추가하지 않음)

## Verification

**Manual checks (if no CLI):**
- 9개 커밋 SHA 전부가 결과에서 실제로 다뤄졌는지 대조 확인(누락 스토리 없음)
- 신규 DW 후보가 있다면 각 항목이 현재 코드(`grep`/`Read`)에 실제로 근거하는지 재확인(스토리 자체 문서 근거는 불충분)
- `git status --porcelain`으로 이 spec 파일 외 변경이 없는지 확인

## Auto Run Result

**변경된 파일:** `_bmad-output/implementation-artifacts/spec-epic-11-12-review-budget-followup.md` (신규 생성, 이 파일 자체 — 리뷰 대상 9개 커밋이나 `deferred-work.md`는 전혀 건드리지 않았다). 그 외 변경 파일 없음.

**리뷰 범위:** 9개 커밋 전부 실제로 리뷰됨(누락 없음) — `b76ec57`(11-0), `d6548a9`(11-1), `48427e3`(11-2), `51c6154`(11-5), `fbdd5a0`(12-1), `b581b45`(12-3), `4ec2075`(12-4), `dd000bb`(12-5), `dfc3aaa`(12-6). SHA→스토리 매핑을 `git show --format="%H %s"`로 사전 실측 검증(9/9 일치).

**실행 방식:** 사전 대화 맥락 없는 구현 subagent 1개를 띄워, 그 안에서 다시 4개의 완전히 독립된 새 세션 subagent(blind-hunter/edge-case-hunter/verification-gap/intent-alignment)를 병렬 실행시켜 9개 커밋의 실제 diff(`git show`)를 각자 읽게 했다. 이후 그 결과를 `deferred-work.md`와 대조(grep)해 기존 등재 항목과 중복인지 가르고, 상위 severity 후보는 현재 소스(`Read`/`grep`)로 직접 재확인했다(`fonts.budget.test.ts`, `AppHeader.test.ts`, `ChatRoomMessages.tsx`, `playwright.config.ts`, `messages.ts`, `0024_chat_room_reads.sql` 등). 최고 severity 후보(조회수 랭킹 조작)는 이 세션이 직접 `web/src/lib/listings.ts` / `PopularRecentGrid.tsx`를 읽어 재확인했다. `python3 scripts/check_migrations.py`로 마이그레이션 게이트가 실제로 초록인지 확인해, 어드버서리얼 레이어의 "11-1 마이그레이션 게이트 깨짐" 주장을 반증했다. 코드 변경은 전혀 하지 않았고(`git status --porcelain` 결과 이 spec 파일 외 없음 확인), `deferred-work.md`는 건드리지 않았다.

**결론: 새 이슈가 있다.** 리뷰 예산이 소진된 채 넘어갔던 이 9개 스토리에서, 대장 어디에도 아직 안 걸려 있는 실질적 이슈 5건이 새로 확인됐다(아래). 오케스트레이터가 이 결과를 근거로 DW-1~DW-9를 종결하고, 아래 5건을 신규 DW로 등재하기를 권장한다. `deferred-work.md`는 이 실행에서 수정하지 않았다.

**레이어별 원 발견 건수(중복·오탐 포함, 트리아지 전, 합계 21건):**
- blind-hunter(adversarial): 9건
- edge-case-hunter: 10건
- verification-gap: 2건 — 이 9개 커밋은 대부분 이미 어떤 형태로든 테스트가 있어(스토리 자체가 검증 포함 종료) "검사는 있는데 검증을 안 함" 유형의 갭이 원래 적게 나올 수 있는 영역이다. 2건(ChatAssistant 수정이 CI 밖 e2e로만 관찰, `queueRetryWiringContract`가 정적 스캔뿐)이 이 레이어가 실제로 찾은 전부이며, 둘 다 아래에서 기존 대장 항목과 중복으로 확인됐다.
- intent-alignment: 서술형 정합성 보고(신규 코드 결함 없음) — 이 레이어는 원래 코드 결함을 찾는 게 아니라 "구현이 의도와 일치하는가"만 서술하도록 설계돼 있어 코드 레벨 발견이 0건인 게 정상이다. 리뷰 스펙의 문제 전제(9/9 대장 오픈, 독립 세션 재검증 이력 없음)를 뒷받침.

이 21건 중 5건이 아래 신규 DW 후보로 승격됐고, 16건은 기각(중복/오탐/노이즈)됐다.

**신규 DW 후보 (5건, 심각도는 "주 소비자에 미치는 영향" 기준):**

1. **[medium]** anon(비로그인 포함 누구나)에게 실행 권한이 열린 `increment_listing_view` RPC(`supabase/migrations/0020_listings_view_count.sql`, 레이트리밋·중복호출 방지 없음)의 조회수가 랜딩 "인기 매물" 섹션의 실제 정렬 입력값으로 쓰인다(`web/src/lib/listings.ts`가 `view_count desc`로 정렬 → `PopularRecentGrid.tsx`가 그대로 렌더). 기존 DW-445(오버플로 자체)·DW-447(값 의미 미정의)와는 다른 축 — "누구나 랭킹을 조작할 수 있다"는 조작 가능성 문제. CLAUDE.md B9 위반 패턴(클라이언트가 보낸/유발한 값이 서버 판단 없이 그대로 신뢰됨).
   - **근거 diff 위치:** anon GRANT는 `d6548a9`(11-1)의 `0020_listings_view_count.sql`에서 도입 — 이 부분이 리뷰 대상 9개 커밋 안에 있다. 영향을 설명하기 위해 참조한 `listings.ts`/`PopularRecentGrid.tsx`의 정렬·렌더 로직은 이 9개 커밋 어디에도 포함되지 않는다(`git show --stat`로 확인 — 이 번들 밖 스토리, 아마 11-4에서 도입). 즉 이 발견의 **원인**은 온전히 스코프 안(11-1)이고, 영향 범위 설명만 스코프 밖 코드를 참고했다(위 Never 절의 "반증·영향 설명 목적 참고는 허용" 예외에 해당).
   - **재현 방법:** RPC를 실제로 반복 호출해 랭킹이 바뀌는 걸 관찰(재현)하지는 않았다 — GRANT 문(`grant execute ... to anon, authenticated`)과 `listings.ts`의 정렬 조건을 코드 레벨에서 직접 읽어 확인한 것으로, "공격이 가능한 코드 경로가 실재한다"까지만 확인이고 "실제로 랭킹이 조작됨"을 동적으로 재현한 것은 아니다.
2. **[low]** 폰트 용량 가드(`web/`의 `fonts.budget.test.ts`, `51c6154`(11-5)에서 도입)가 파일 **크기**만 검사하고 **내용물(정체성)**은 검사하지 않는다 — sha256 해시 비교가 주석에만 언급되고 실제 검사 코드로는 안 옮겨져 있다(실측 확인). 크기가 같은 다른 파일로 바꿔치기해도 가드를 통과한다.
3. **[low]** `AppHeader.test.ts`의 소스 스캔 정규식(`APP_HEADER_TAG`, `48427e3`(11-2)에서 도입 — `dd000bb`(12-5)는 이 정규식을 건드리지 않고 다른 부분만 수정)이 스프레드 속성 호출부(`{...props}`)로 전달되는 경우를 못 잡는다 — 실제 컴포넌트 코드와 대조해 실측 확인.
4. **[low]** `ChatRoomMessages.tsx`에서 재연결 시 `realtimeError`를 지우는 조건식이 뒤집혀 있다 — `realtimeError` 상태 자체는 `b581b45`(12-3)가 도입했고, 문제의 재연결-클리어 조건은 재연결 배너를 다루는 `4ec2075`(12-4)에서 손댄 부분이다. 현재 라이브러리 동작 전제상 오늘은 사실상 도달 불가능한 코드 경로지만, Realtime 클라이언트의 재연결 콜백 순서가 바뀌면 바로 살아나는 잠복 결함이다. **다른 "현재 도달 불가" 후보(Playwright strict-mode `.catch`, 폰트 `<link>` 정규식 우회)는 기각하면서 이 항목만 남긴 기준**: 저 둘은 도달하려면 이 프로젝트 코드 자체가 먼저 바뀌어야 하는 반면(예: 매칭 요소가 2개 이상이 되도록 마크업을 새로 추가해야 함), 이 항목은 **외부 라이브러리(Supabase Realtime)의 콜백 호출 순서**라는, 이 프로젝트가 통제하지 못하는 조건 하나만 바뀌면 즉시 살아난다 — 통제 밖 트리거는 "사실상 죽은 코드"로 보지 않는다.
5. **[low]** `web/playwright.config.ts`(`51c6154`(11-5)에서 도입)에서 빈 문자열 env 값이 `.env.local` 값보다 우선 적용된다 — 같은 파일의 다른 env 필드는 이미 "값 없으면 즉시 실패"(fail-loud) 원칙을 따르는데 이 필드만 예외로 조용히 빈 값을 채택.

**리뷰했지만 신규 DW로 올리지 않은 것(기각 16건 중 대표 항목 발췌 — 나머지는 사소한 표현·중복 변형):**
- DW-435·DW-440·DW-443·DW-445·DW-447·DW-432와 동일 결함(이관 전 번호만 다름) — grep 대조로 확인(전체 통독은 아님 — 위 frontmatter `warnings` 참고).
- `queueRetryWiringContract`가 정적 배선 스캔뿐이라 실제 회귀를 못 잡음 — 이미 DW-530과 완전 중복(뮤테이션 기법까지 동일).
- `ChatAssistant` 수정이 CI 안 도는 e2e로만 관찰됨 — 이미 DW-468과 동일 근본 원인(E2E CI 미배선).
- `chat_unread_count()`의 admin RLS 결함 — 같은 9-커밋 번들 내(`0024`→`0025`)에서 이미 고쳐짐, 잔존 결함 아님.
- "11-3/11-4가 코드 없이 done으로 뒤집혔다"(오탐) — `git show`로 반증, 실은 번들 밖 별개 커밋의 unchanged diff context였을 뿐. (이 반증은 위 Never 절의 "오탐 판정을 위한 참고 허용" 예외에 해당 — 11-3/11-4 자체를 새로 조사·판정한 게 아니라, 이 9개 커밋 리뷰에서 나온 오탐 주장 하나를 반박한 것.)
- "11-1이 DoD(마이그레이션 게이트) 미충족인데 done"(오탐) — **현재** 환경에서 게이트를 재실행해 초록임을 확인해 반증했다. 단, 이는 "지금은 안 깨져 있다"는 증거이지 "11-1 병합 당시에도 안 깨져 있었다"는 증거는 아니다 — 과거 시점 주장을 현재 시점 증거만으로 완전히 반증한 것은 아니라는 한계가 있다. 다만 이 관찰 자체가 이미 DW-2(이 번들의 대상)와 동일 사안이라 별도 신규 등재는 어차피 불필요.
- 해시 전용 뒤로가기 미대응 — 가드가 이미 의도적으로 제거된 설계(주석에 명시).
- Playwright strict-mode `.catch(() => false)` — 현재 페이지엔 매칭 요소가 각 1개뿐이라 도달 불가(이 프로젝트 코드가 먼저 바뀌어야 도달 가능 — 위 신규 후보 4번과의 구분 기준 참고).
- 폰트 `<link>` 정규식 우회 가능성 — 실제 마크업 생성 경로상 발생 불가능한 케이스(위와 동일 기준).
- idempotency key 시계 역행 — 있어도 피해 방향이 안전 쪽(중복 방지가 더 엄격해질 뿐).
- 마이그레이션 백필 순서 — 대상 UPDATE가 멱등이라 순서 무관.

**검증 수행:** 코드 변경이 없어 별도 CLI 빌드/테스트 대상 없음. `git status --porcelain`으로 이 spec 파일 외 변경 없음 확인(2회, 구현 subagent 전/후). `python3 scripts/check_migrations.py` 실행해 그린 확인(어드버서리얼 레이어의 반증에 사용, 단 위에서 밝힌 대로 "지금" 기준). 위 1번 핵심 근거는 이 세션이 직접 `web/src/lib/listings.ts`/`PopularRecentGrid.tsx`를 읽어 재확인. 2~5번은 참조된 파일을 직접 읽어 실측 일치 확인. Block If("9개 커밋 중 하나라도 이미 병합된 상태와 다르게 관측되면 HALT")의 근거로 SHA→스토리 제목 매핑뿐 아니라 9개 커밋 각각의 `git show --stat` 변경 파일 수·삽입/삭제 줄 수도 리뷰 시작 시점에 캡처해 대조했다(예: 11-5=22 files/+1545/-12) — 9개 전부 기대와 일치, 이상 없음.

**`followup_review_recommended: true`에 대한 설명:** 이 필드는 spec 템플릿 정의상 "이번 step-04 리뷰 패스에서 patch로 처리한 발견의 심각도"만 반영한다(3×medium+1×low ≥ 5, 또는 high 1건 이상이면 true) — 아래 신규 DW 후보 5건과는 **별개 신호**다. 이번 패스는 4개 메타 리뷰 레이어(이 spec 문서 자체를 대상)가 낸 발견 중 12건을 patch로 직접 고쳤다(medium 2, low 10 → 점수 3×2+1×10=16 ≥ 5) — 그래서 true. 즉 "신규 DW 후보"는 오케스트레이터가 대장에 등재할 근거이고, `followup_review_recommended: true`는 (선택 사항으로) 이 spec 문서 자체를 다시 한 번 리뷰 패스에 태울 가치가 있다는 신호일 뿐, 대장 처리와는 무관하다.

**잔여 리스크:**
- `deferred-work.md`가 575KB로 커서 grep 키워드 대조만 했고 전체를 처음부터 끝까지 다 읽지는 않았다 — 위 5건 중 표현이 다른 기존 중복이 남아 있을 가능성이 작게 있다.
- 2~5번(low)은 이 세션이 참조 파일을 직접 읽어 확인했지만, edge-case-hunter 레이어가 낸 나머지 low 후보들만큼 전수 재확인하지는 않았다(스펙 지시대로 상위 severity 위주로 직접 재확인).
- 1번(view_count 랭킹 조작)은 데모 규모 트래픽에선 실질 피해가 작지만, 같은 "레이트리밋 없음" 설계 원인을 공유하는 기존 DW-445가 나중에 처리될 때 함께 고려할 가치가 있다.
