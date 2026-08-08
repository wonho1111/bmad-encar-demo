---
title: '4분기 AI 응답·되묻기 칩 (앱)'
type: 'feature'
created: '2026-08-08'
status: 'done'
baseline_revision: '30c2c74d03456affabb99dde9bd57ce0785f389b'
final_revision: '279012d'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-16-context.md'
  - '{project-root}/docs/conventions.md'
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** Flutter 앱 AI 검색(`ai_chat_screen.dart`)은 `/ai/search` 응답의 `answer`+`listings`만 처리한다. 서버(Epic 13)는 이미 4분기 계약(`{answer, listings, clarify, narrowed_by}`, `docs/conventions.md` §4)을 내려보내지만 앱은 `clarify`(되묻기 질문+칩)를 파싱조차 하지 않아, 되묻기 응답이 오면 질문 텍스트만 뜨고 칩도 카드도 없는 막다른 화면이 된다(대장 DW-592가 이 스토리를 해소 자리로 지정). 입력 글자수 상한도 서버 하드 상한(1000)을 그대로 쓰고 있어 웹의 UX 확정값(500)과 어긋난다.

**Approach:** 서버가 이미 구조화해 보내는 `clarify`/`narrowed_by`를 파싱해 응답 모델에 싣고, `clarify != null`일 때만 탭 가능한 되묻기 칩을 렌더한다(탭 = 그 문자열로 다음 질의 전송). 되묻기 상한은 서버가 `context` 길이로 이미 강제하므로(DW-563) 클라는 별도 카운터 없이 `clarify` null 여부만 본다. 입력 상한을 500자로 낮추고 실시간 카운터를 붙인다(웹 `HeroSearch.tsx` 미러).

## Boundaries & Constraints

**Always:**
- `SearchResult`에 `clarify: ClarifyPayload?`(`question: String`, `chips: List<String>`)와 `narrowed_by: List<String>?`를 추가하고, `parseSearchResult`가 두 필드를 방어적으로 파싱한다(형태가 깨지면 해당 필드만 null로 폴백, `answer`/`listings` 파싱은 계속 진행) — `parseClarifyPayload`/`parseNarrowedBy` 순수 함수로 분리해 단위테스트한다(이 레포의 `parseUnreadByRoomRows` 관례, web `isValidClarify`/`isValidNarrowedBy` 동등 방어 수준 미러).
- `ChatMessage`(assistant 턴)에 `clarify: ClarifyPayload?` 필드를 추가해 화면까지 실어 나른다. `narrowed_by`는 렌더하지 않으므로(Never) `ChatMessage`에는 필드를 추가하지 않는다.
- 되묻기 칩은 `message.clarify != null && chips.isNotEmpty`일 때만 assistant 버블 아래 렌더한다. 탭하면 그 문자열을 다음 질의로 즉시 전송한다 — 기존 `_submit()` 경로를 재사용해(질의 문자열을 받는 파라미터로 확장) 낙관적 버블·에러 롤백·로딩이 칩 전송에도 동일하게 적용되게 한다.
- 칩이 떠 있는 동안에도 자유 입력창은 항상 활성 상태다(칩 존재가 타이핑을 막지 않는다).
- 되묻기 상한(서버 3턴)은 클라가 별도로 세지 않는다 — `clarify`가 null로 오면(상한 초과 강제 폴백 포함) 칩을 안 그리는 것 자체가 상한 반영이다.
- AI 입력창 글자수 상한을 500으로 낮추고(`chat_message.dart`의 `maxQueryLength`), `TextField`에 `maxLength: 500`+실시간 카운터를 적용해 초과 입력 자체를 막는다. 기존 제출 시점 사전 안내(길이 초과 에러 메시지)는 방어적으로 유지하되 기준값만 500으로 갱신한다.
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md`의 I12("무상태이므로 클라 강제")를 "서버가 `context` 길이로 강제(`api/app/graph/graph.py`) + 클라는 `clarify` null이면 칩 미표시"로 정정한다(대장 DW-589, 트리거가 이 스토리의 스펙 작성 시점을 정확히 지정).
- 작업 완료 후 대장(`deferred-work.md`)의 DW-589(정정 완료)·DW-592(해소)·DW-594(아래 Never 결정으로 닫음)·DW-597(앱 쪽만 닫음, 웹 쪽은 이미 Epic 15로 retarget돼 있어 그대로 둠)를 갱신한다.

**Block If:** (없음 — 계약·서버 구현·웹 파싱 참고 구현이 이미 확정돼 있다.)

**Never:**
- `narrowed_by`(REJECT 사유 술어, 예 `"price<=30000000"`)를 화면에 렌더하지 않는다 — 원시 술어 문자열이라 사람이 읽을 텍스트가 아니고, 탭-재검색 UI를 만들려면 술어→라벨 번역과 별도 컴포넌트가 필요해 이 스토리 크기를 넘는다(대장 DW-597 — 웹도 동일 결정). 파싱은 하되 소비하지 않는다.
- 클라이언트 측 되묻기 턴 카운터를 새로 만들지 않는다 — I12 구버전 문구대로 클라 상태로 상한을 추적하면 서버(3턴)·클라(2~3턴)가 각자 세는 두 상한이 생긴다(DW-589가 경고한 결함 그 자체).
- `clarify.chips`의 값 자체(가격·차종·연료 vs EXPERIENCE.md 예시 문구 "7인승")를 검증하거나 하드코딩하지 않는다 — 서버가 보내는 문자열을 그대로 렌더할 뿐이다. 칩 축 선택은 `clarify_node.py`(Epic 13)의 제품 판단이라 범위 밖이다(대장 DW-594 — 렌더링은 값의 의미와 무관하므로 이 결정으로 닫는다).
- REJECT/HYBRID/SQL 세 갈래에 대해 CLARIFY와 다른 새 버블 스타일·레이아웃을 만들지 않는다 — 기존 assistant 버블(텍스트+매물카드)이 이미 4갈래를 자연히 구분한다(SQL/HYBRID=카드 있음, CLARIFY=칩 있음, REJECT=텍스트만). 범위는 되묻기 칩 렌더 하나로 좁힌다.
- 홈 화면의 AI 진입 CTA·라우팅(`home_screen.dart`, 16.1에서 이미 확정)을 바꾸지 않는다.
- 전역 Riverpod `StateNotifier`로 AI 채팅 상태를 새로 만들지 않는다 — 조사 결과 웹 `ChatAssistant.tsx` 자체가 순수 로컬 `useState`뿐이라 미러링할 전역 패턴이 없다. D14의 "Riverpod 검색 상태 미러링"은 기존 `_AiChatScreenState`의 로컬 필드 구조를 그대로 확장하는 것으로 충분하다(spec-16-4 Design Notes와 같은 원칙).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 구조형/하이브리드 응답 | `{answer, listings:[...], clarify:null, narrowed_by:null}` | 기존과 동일(텍스트+카드), 칩 없음 | 기존 에러 처리 유지 |
| 되묻기 응답 | `{answer, listings:[], clarify:{question,chips:[...]}, narrowed_by:null}` | 질문 텍스트 아래 탭 가능한 칩 행 렌더 | chips가 빈 배열이면 칩 행 자체를 안 그림 |
| 거절 응답 | `{answer, listings:[], clarify:null, narrowed_by:[...]}` | 텍스트 안내만(칩·카드 없음) | narrowed_by는 파싱만 하고 미렌더 |
| 되묻기 상한 초과(서버 강제 폴백) | `{answer, listings:[...], clarify:null}` | 칩 없이 매물카드로 렌더(구조형과 같은 경로) | 클라 카운터 없음 — clarify null이 유일 신호 |
| 칩 탭 | 되묻기 칩 문자열 | 그 문자열로 즉시 다음 질의 전송(기존 `_submit` 경로) | 실패 시 기존 롤백(낙관적 버블 제거+입력 복원) 동일 적용 |
| 입력 500자 초과 시도 | 501번째 글자 입력 | `TextField`가 더 받지 않음(하드 제한) | 카운터가 500/500 표시 |
| clarify 필드 형태 깨짐 | `clarify: "문자열"` 또는 `{question:123}` | null로 폴백(칩 없음), answer/listings 파싱은 계속 | 크래시 없음 |

</intent-contract>

## Code Map

- `app/lib/features/ai_search/ai_search_api.dart` -- `ClarifyPayload` 클래스 신설, `SearchResult`에 `clarify`/`narrowed_by` 필드 추가, `parseClarifyPayload`/`parseNarrowedBy` 순수 함수 신설(web `isValidClarify`/`isValidNarrowedBy` 미러) 후 `parseSearchResult`에서 호출
- `app/lib/features/ai_search/chat_message.dart` -- `ChatMessage`에 `clarify` 필드 추가, `maxQueryLength` 1000→500
- `app/lib/features/ai_search/ai_chat_screen.dart` -- assistant 메시지 생성 시 `clarify` 전달, `_submit`에 질의 문자열 파라미터 추가(칩 탭 재사용), 되묻기 칩 위젯(`_ClarifyChips`) 신설·`_MessageBubble`에 배선, `TextField`에 `maxLength:500`+카운터
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md` -- I12 문구 정정(서버 강제로, DW-589)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-589/592/594/597 상태 갱신(닫음 또는 정정 반영)
- `app/test/ai_search_test.dart` -- `parseClarifyPayload`/`parseNarrowedBy`/`parseSearchResult`(clarify·narrowed_by 통합) 단위테스트 확장
- `app/test/ai_chat_screen_test.dart` -- 되묻기 칩 렌더·탭 전송·500자 상한 위젯테스트 추가

## Tasks & Acceptance

**Execution:**
- `app/lib/features/ai_search/ai_search_api.dart` -- `ClarifyPayload`+파싱 순수 함수 -- 계약 소비의 단일 출처
- `app/lib/features/ai_search/chat_message.dart` -- `clarify` 필드+글자상한 500 -- 화면 배선 준비
- `app/lib/features/ai_search/ai_chat_screen.dart` -- 칩 렌더+탭 전송+글자상한 UI -- 헤드라인 기능
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md` -- I12 정정 -- DW-589 해소
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-589/592/594/597 갱신 -- CLAUDE.md B8 장부 닫기
- `app/test/ai_search_test.dart` -- 파싱 단위테스트 -- I/O 매트릭스 커버
- `app/test/ai_chat_screen_test.dart` -- 위젯테스트 -- I/O 매트릭스 커버

**Acceptance Criteria:**
- Given 서버가 CLARIFY 라우트로 응답(`clarify` 필드가 채워짐), when 그 응답이 화면에 그려지면, then 질문 텍스트 아래 탭 가능한 칩이 `chips` 배열 순서대로 렌더된다.
- Given 되묻기 칩을 탭하면, when 전송이 성공하면, then 그 칩 문자열이 사용자 메시지로 추가되고 다음 AI 응답이 이어진다(직접 타이핑과 동일 파이프라인, 자유 타이핑과 병존).
- Given REJECT 응답(`narrowed_by`만 채워짐), when 화면에 그려지면, then 텍스트 안내만 보이고 칩·카드는 없으며 크래시가 없다.
- Given 사용자가 500자를 넘겨 입력을 시도하면, when 501번째 글자를 치면, then 입력창이 더 받지 않고 카운터가 500/500을 보여준다.
- Given 서버가 되묻기 상한 초과로 강제 폴백(`clarify:null`, `listings` 채움)하면, when 화면에 그려지면, then 칩 없이 매물카드가 렌더된다(클라 자체 카운터 없이 서버 신호만으로 동작).

## Spec Change Log

## Review Triage Log

### 2026-08-08 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6 (high 0, medium 3, low 3)
- defer: 0
- reject: 10 (high 0, medium 0, low 10)
- addressed_findings:
  - `[medium]` `[patch]` 칩 탭(`overrideQuery` 경로)이 `_submit()`의 기존 `_input.clear()`(성공 시)·`_input.text = query`(실패 롤백 시)를 무조건 그대로 타, 사용자가 입력창에 따로 써 둔 미전송 초안이 칩 탭 한 번에 조용히 사라지거나 칩 문자열로 덮어써졌다(adversarial·edge-case-hunter 독립 발견). `overrideQuery != null`일 때는 `_input`을 건드리지 않도록 두 지점 모두 가드.
  - `[medium]` `[patch]` 되묻기 칩이 탭하거나 새 턴이 와도 소비되지 않고 대화가 끝날 때까지 계속 탭 가능한 상태로 남아, 사용자가 예전 턴의 칩을 다시 누르면 그 시점까지의 전체 대화를 context로 실어 조용히 "되감기"하며 서버의 되묻기 턴 상한 소진 속도까지 사용자 모르게 앞당겼다(adversarial 발견). 칩이 탭되거나 더 최신 사용자 턴이 제출되면 그 메시지의 칩 행이 더 이상 반응하지 않도록 수정.
  - `[medium]` `[patch]` 되묻기 칩 행이 `Wrap`을 써서 좁은 화면에서 2번째 줄로 밀릴 수 있다 — 이 프로젝트가 옵션·칩류 가로 배치에 못박은 절대 규칙(D5, project-context.md 규칙 13: "2줄로 밀리는 버튼 = 절대 금기", 초과분은 가로 스크롤·truncate로만 처리)을 새 컴포넌트가 곧바로 어긴다(adversarial 발견). `Wrap`을 가로 스크롤 단일 행으로 교체.
  - `[low]` `[patch]` 칩이 탭 전후 시각 변화가 전혀 없이 처음부터 끝까지 동일한 petrol 채움으로 렌더돼, `EXPERIENCE.md`가 명시한 "탭 시 petrol 채움 선택 상태로 전환"과 어긋나고 스크린리더용 선택 시맨틱도 없었다(adversarial 독립 발견 2건). 위 되감기 패치와 함께 탭된 칩에 선택 표시를 남기도록 보강.
  - `[low]` `[patch]` `parseClarifyPayload`가 칩 원소의 타입만 확인하고 빈 문자열/공백뿐인 칩은 그대로 통과시켜, 눌러도 아무 반응 없는 "죽은 칩"이 뜰 수 있었다(edge-case-hunter 발견). 다른 형태 불량과 같은 기준으로 공백뿐인 칩도 폐기하도록 확장.
  - `[low]` `[patch]` 칩 `Key`가 칩 문자열 자체(`clarify_chip_$chip`)만 써서, 서버가 훗날 같은 문자열을 중복으로 보내면 같은 부모 아래 중복 Key로 렌더 크래시 위험이 있었다(adversarial 발견, 지금은 서버가 항상 서로 다른 고정 3개만 보내 우연히 안전). 인덱스를 key에 섞어 근본 차단.
- rejected_as_noise (기록용, 근거 포함):
  - 대장(`deferred-work.md`)의 DW-589/592/594가 스펙 자신이 아직 `in-review`인 시점에 `done`으로 먼저 닫혔다(adversarial 발견) — 이 순서는 dev-auto 워크플로 자체(step-03에서 구현+대장 갱신, step-04에서 리뷰)가 정한 것이라 이 스토리 코드의 문제가 아니다. 이번 패스가 bad_spec/intent_gap 없이 patch만으로 끝나 재파생이 없으므로 실제로도 어긋나지 않는다.
  - `followup_review_recommended: false`가 Manual checks 미완료 상태에서 스스로 선언됐다(adversarial 발견) — 이 값은 Finalize 단계에서 이번 패스의 patch 심각도로 기계적으로 재계산되므로 이 지적은 그 시점에 자동 해소된다.
  - 핵심 AC(칩 렌더·탭)가 실제 화면 렌더로 확인되지 못했다(adversarial 발견) — 이미 `deferred-work.md`(source_spec: spec-16-5)에 동일 내용이 trigger(Epic 16-6)와 함께 defer로 등재돼 있어 신규 등재가 아니라 중복.
  - 이번에 마주친 렌더 실패("Null check operator")를 이전 선례(CanvasKit 크래시)와 같은 면제 사유로 취급했다(adversarial 발견) — 근본 사실(수동 검증 미실행)은 이미 위 defer로 추적 중이라 별도 조치가 남지 않는다.
  - 서버가 `listings`와 `clarify.chips`를 동시에 채워 보내는 경우가 방어되지 않는다(edge-case-hunter 발견) — `api/app/graph/clarify_node.py` 실측 결과 CLARIFY 경로는 항상 `listings: []`를 반환해 계약상 도달 불가능한 상태다.
  - `ClarifyPayload.question`이 파싱만 되고 화면에 안 쓰인다(edge-case-hunter 발견) — `api/app/graph/clarify_node.py`를 직접 읽어 확인: `answer`와 `clarify.question`은 항상 같은 상수 문자열(`_CLARIFY_QUESTION`)이라 별도 렌더는 순수 중복이다.
  - REJECT·구조형/하이브리드 응답에 전용 위젯테스트가 없다(intent-alignment 발견) — verification-gap 레이어가 코드를 직접 추적해 REJECT는 이미 존재하는 "칩 빈 배열" 위젯테스트와 동일한 렌더 분기(`clarify==null` 또는 `chips.isEmpty`)를 타는 것을 확인했고, 구조형/하이브리드는 파싱 단위테스트로 필드 영향 없음이 이미 커버된다.
  - "Riverpod 검색 상태 미러링"(D14)이 전역 상태 클래스가 아니라 로컬 위젯 필드로 구현됐다(intent-alignment 발견) — 계획 단계에서 웹 참조 구현(`ChatAssistant.tsx`)이 애초에 로컬 `useState`뿐임을 실측 확인하고 스펙 Design Notes에 근거를 남긴 의도된 결정이다.
  - 되묻기 상한(2~3턴)을 클라가 직접 세지 않는다(intent-alignment 발견) — 스펙 Never 절이 명시적으로 요구한 설계(서버 강제, DW-589 정정)이며 우연이 아니다.
  - `narrowed_by`가 화면에 렌더되지 않는다(intent-alignment 발견) — `docs/conventions.md` §4(Story 13.5)가 이미 정한 선행 결정이며 스펙 Never 절이 근거와 함께 재확인했다.

### 2026-08-08 — Review pass (후속, 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 0, medium 4, low 5)
- defer: 4 (high 0, medium 4, low 0)
- reject: 6 (high 0, medium 0, low 6)
- addressed_findings:
  - `[medium]` `[patch]` "빈 chips면 칩 행을 안 그린다" 테스트가 이 레포에 존재하지 않는 위젯 타입(`ActionChip`)을 찾고 있어 **항상 통과**했다 — 칩은 전부 `ChoiceChip`이다(adversarial·edge-case-hunter·verification-gap 3개 레이어 독립 발견). 변이 실측으로 확인: 렌더 조건에서 `chips.isNotEmpty`를 지워도 317/317 green이었다. `_ClarifyChips`에 `Key('clarify_chips')`를 달고 그 키와 `ChoiceChip` 부재로 단언하도록 교체.
  - `[medium]` `[patch]` 칩 탭 전송이 **실패하면 그 칩이 영구 비활성**이 됐다(3개 레이어 독립 발견, 두 곳에서 실행 실측). `_onChipTap`이 요청 전에 `usedChip`을 찍는데 실패 롤백이 그걸 안 지워, 롤백으로 칩 행은 다시 활성화되지만 방금 누른 칩만 `isSelected` 때문에 못 눌리는 상태가 남았다 — 일시적 네트워크 실패 한 번이 그 칩을 영영 죽인다. `_submit`이 성공 여부를 반환하게 하고, 실패 시 `ChatMessage.clearUsedChip()`으로 표시를 되돌린다(`copyWith`는 `?? this`라 null로 되돌릴 수 없어 별도 메서드 신설).
  - `[medium]` `[patch]` 글자수 상한을 **서로 다른 단위로 두 번** 셌다 — `TextField.maxLength`는 그래핌, 제출 가드의 `String.length`는 UTF-16 코드유닛(adversarial·edge-case-hunter 독립 발견, 실측). 이모지 400개를 넣으면 카운터는 "400/500"인데 전송은 막히고 "500자 이내로 줄이라"는 안내가 떠, 사용자가 빠져나갈 방법을 알 수 없다. 가드를 `query.characters.length`로 통일.
  - `[medium]` `[patch]` wire JSON → 화면 **이음매를 지나가는 검사가 하나도 없었다**(intent-alignment 발견) — 파싱 단위테스트는 JSON→`SearchResult`까지, 위젯테스트는 손으로 만든 `SearchResult`→화면부터라 둘이 만나지 않았다(16.4에서 실제로 사고가 난 형태). 라이브 curl로 받은 실제 wire JSON을 `parseSearchResult`에 통과시켜 화면에 주입하는 위젯테스트를 추가해 이었다.
  - `[low]` `[patch]` 못 누르는 칩(지난 턴·로딩 중)이 활성 칩과 **거의 같아 보였다**(adversarial·edge-case-hunter 발견) — Flutter 기본 `disabledColor`는 배경만 흐리게 하고 여기서 하드코딩한 petrol 테두리·글자색은 그대로 남는다. 사용자는 눌리는 칩으로 보고 반복 탭한다. 잠긴 칩의 테두리·글자를 `inkMuted`로 갈랐다(선택된 칩은 petrol 채움 유지).
  - `[low]` `[patch]` `maxLength`가 만든 기본 Material 카운터가 입력 박스 높이에 얹혀 **전송 버튼을 10px 아래로 밀었다**(adversarial 발견, 위젯테스트로 실측: 버튼 중심 554 vs 입력 텍스트 중심 544). 기본 카운터를 끄고(`counterText: ''`) 카운터를 Row 밖 별도 줄로 직접 그렸다(웹 `HeroSearch.tsx`도 카운터를 입력 밖에 둔다). 재측정 결과 543 == 543.
  - `[low]` `[patch]` 공백뿐인 칩을 폐기하는 규칙(1차 패스에서 추가)이 **어떤 테스트도 지나가지 않아** 지워도 전 스위트가 green이었다(verification-gap 변이 실측). 빈/공백 칩 케이스 2건을 추가하고, "web `isValidClarify` 미러"라는 주석이 사실과 달랐던 것(웹엔 이 규칙이 없다)도 "한 겹 더 엄격하다 + 그 이유"로 정정.
  - `[low]` `[patch]` `chat_message.dart` 상수 블록 주석이 자기모순이었다(adversarial 발견) — 세 상수를 묶어 "단일 출처: `api/app/schemas/ai.py`"라고 선언하는데 `maxQueryLength`만 의도적으로 서버(1000)와 다른 500이다. 다음 사람이 "정본으로 되돌리기"를 하면 AC가 조용히 뒤집힌다. 주석을 갈라 예외임을 못박았다.
  - `[low]` `[patch]` 정정한 I12가 "서버가 강제한다"를 **무조건적 보장처럼** 읽히게 썼다(adversarial 발견) — 같은 대장의 DW-591(열림)이 "클라가 `context`를 비우면 무력화된다"를 이미 기록하고 있다. I12에 그 한계와 DW-591 참조를 덧붙였다(정본이 둘로 갈리는 것을 막으려던 정정이 다시 반쪽 사실이 되지 않도록).
- rejected_as_noise (기록용, 근거 포함):
  - `ClarifyPayload.question`이 파싱만 되고 렌더되지 않아 `answer`가 비면 질문 없이 칩만 뜬다(adversarial·edge-case-hunter 발견) — 1차 패스가 `clarify_node.py`를 직접 읽어 `answer`와 `clarify.question`이 항상 같은 상수임을 확인하고 reject한 사안이며, 재현 전제(`answer: ''`)가 서버 계약상 도달 불가다. 불가능한 시나리오용 방어를 넣지 않는다(CLAUDE.md A2).
  - `buildContext`가 빈 content 턴을 버려 서버의 `len(context)//2` 턴수 계산이 어긋날 수 있다(edge-case-hunter 발견) — 위와 같은 전제(빈 answer)에서만 성립하고, 서버 강제의 잔여 우회는 DW-591이 이미 열린 항목으로 추적 중이다(이번 패스에서 I12에 그 사실을 명시하는 것으로 대응).
  - `parseNarrowedBy`가 소비처 없는 죽은 코드다(adversarial 발견) — 스펙 Always가 파싱을, Never가 미렌더를 각각 명시적으로 요구한 설계다(DW-597, 웹도 동일 결정). intent-alignment 레이어도 "Never 4건 모두 지켜짐"으로 확인했다.
  - `chips: []`는 통과시키면서 `narrowed_by: []`는 null로 떨구는 비대칭(adversarial 발견) — 스펙 I/O 매트릭스가 "chips 빈 배열 → 칩 행만 안 그림"을 명시적으로 규정했고 웹도 같다. 서로 다른 계약을 가진 두 필드라 비대칭이 아니라 각자의 계약이다.
  - 요청 중 자유 입력창이 잠긴다(`enabled: !_loading`)는 것이 "칩이 떠 있는 동안 입력창 항상 활성"과 어긋난다(intent-alignment 발견) — 그 Always 절은 "칩 존재가 타이핑을 막지 않는다"는 뜻이고, `enabled: !_loading`은 이번 스토리가 건드리지 않은 기존 동작이다.
  - `sprint-status.yaml`이 HEAD에서 아직 `backlog`인데 대장은 16.5를 done으로 닫았다(adversarial 발견) — 이 파일은 오케스트레이터 소유이며 해당 변경이 이미 작업트리에 대기 중이다(아래 residual artifacts 참조). 이 스토리 코드의 문제가 아니다.

### 2026-08-08 — Review pass (후속, 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 0, medium 4, low 8)
- defer: 2 (high 0, medium 2, low 0)
- reject: 13 (high 0, medium 1, low 12)
- addressed_findings:
  - `[medium]` `[patch]` **이 스토리의 헤드라인 AC("탭한 칩 문자열 그대로 다음 질의로 보낸다")를 지나가는 검사가 없었다** — 기존 단언은 호출 횟수와 화면의 'SUV' 텍스트뿐인데, 그 버블은 전송값과 **같은 지역변수**로 그려져 전송값이 틀려도 화면은 멀쩡해 보인다(verification-gap 변이 실측: 칩 경로가 `'MUTATED-WRONG-QUERY'`를 보내게 해도 전 스위트 green). 오버라이드에서 실제 인자를 붙잡아 단언하도록 교체.
  - `[medium]` `[patch]` 같은 이유로 **칩 탭이 `context`를 싣는지도 아무도 안 봤다**(변이 실측: 칩 경로에서 context 를 null 로 떨궈도 green). 서버는 이 배열 길이로 되묻기 3턴 상한을 세고(정정된 I12) 클라엔 카운터가 없으므로(스펙 Never), 여기가 끊기면 모든 칩 탭이 서버에 "1턴째"로 보여 상한이 영영 안 걸린다. 직전 두 턴이 실려 나가는지 단언 추가.
  - `[medium]` `[patch]` **REJECT 갈래만 화면까지 가는 검사가 없었다**(스펙 AC3 + Never "narrowed_by 미렌더"). 앞선 두 패스는 "REJECT 는 `clarify==null`이라 빈-chips 테스트와 같은 분기를 탄다"는 **추론**으로 이 자리를 비워 뒀는데, 변이 실측 결과 버블 본문에 `narrowed_by`를 이어 붙여도 전 스위트가 green이었다 — 그 Never 를 지키는 실행되는 검사가 하나도 없었다(CLAUDE.md B4: 정연한 논증은 검증이 아니다). REJECT wire 페이로드를 화면까지 통과시키는 위젯테스트 신설.
  - `[medium]` `[patch]` **같은 문자열 칩이 둘이면 하나를 탭한 것만으로 둘 다 선택·비활성**이 됐다(adversarial·edge-case 독립 발견, 오케스트레이터 실측: chips `['SUV','SUV','세단']`에서 첫 칩 탭 → selected 플래그 `[true, true, false]`). 1차 패스가 칩 `Key`를 인덱스로 굳혀 중복을 가른 판단과 정면으로 어긋나는 절반짜리 방어였다. 선택 기억을 `usedChip`(문자열) → `usedChipIndex`(인덱스)로 바꿔 두 곳의 기준을 일치시켰다.
  - `[low]` `[patch]` **같은 프레임 연타가 진행 중인 칩의 선택 표시를 지웠다**(edge-case 발견, 실측: `selected=false`). 첫 탭이 `_loading`을 켜지만 칩 행이 비활성으로 다시 그려지는 건 다음 build 이후라, 그 전에 들어온 두 번째 탭이 표시를 찍고 → `_submit`이 `_loading` 때문에 즉시 false 를 돌려주고 → 그 롤백이 **첫 탭의 표시까지** 지웠다. 가드를 `_onChipTap` 맨 앞으로 옮겼다(렌더 게이트로는 못 막는 자리다).
  - `[low]` `[patch]` 렌더 게이트의 `_loading ||` 조건이 **도달 불가능**한데 주석은 "두 조건 모두 필요"라고 선언하고 있었다(verification-gap이 변이 + 전용 Completer 테스트 두 방향으로 확인). `_loading`이 켜지는 `setState`가 같은 자리에서 낙관적 user 버블을 append 하므로 clarify 를 가진 메시지는 로딩 중에 결코 `isLast`가 아니다. 죽은 조건을 걷어내고 주석을 사실로 맞췄다(연타 방어는 위 `_onChipTap` 가드가 담당).
  - `[low]` `[patch]` **칩 탭 실패 시 초안 보존이 성공 경로에서만 검사되고 있었다**(verification-gap 변이 실측: 롤백의 `overrideQuery == null` 조건을 지워도 green). 일시적 실패 한 번이 사용자 초안을 칩 문자열로 덮어쓰는 경로다. 기존 실패 테스트에 초안 단언 추가.
  - `[low]` `[patch]` **선택 신호가 색 하나뿐이어도 안 걸렸다**(verification-gap 변이 실측: `avatar: null`로 지워도 green). `showCheckmark: false`라 `selected: true`만으로는 체크 표시가 생기지 않는다 — EXPERIENCE.md 비색 신호 중복 규칙을 실제로 지키는지 아이콘 단언 추가.
  - `[low]` `[patch]` **web·iOS에서 한글 조합 중 카운터가 상한을 넘겨 표시**될 수 있었다(adversarial·edge-case 발견, Flutter SDK 실측으로 갈랐다 — 두 레이어 주장이 엇갈렸고 사실은 Android·Windows만 `enforced`, web·iOS·macOS·linux는 `truncateAfterCompositionEnds`). 조합 중 강제로 바꾸면 CJK 입력이 깨지므로(그래서 그게 Flutter 기본값이다) 표시값만 clamp 했다. iOS 플랫폼 오버라이드 + 조합 구간을 단 입력으로 검사 추가.
  - `[low]` `[patch]` 기본 Material 카운터를 끄면서(`counterText: ''`) **딸려 나간 접근성 시맨틱을 되살리지 못했다**(edge-case 발견, `input_decorator.dart` 실측: 기본 카운터는 `Semantics(liveRegion)`로 감싸여 글자수를 읽어 준다). 직접 그린 카운터에 `Semantics(liveRegion)` 배선.
  - `[low]` `[patch]` **기하를 재는 검사 2건이 배포되지 않는 표면에서 재고 있었다**(intent-alignment 발견) — `main.dart`의 `MaterialApp` 4곳은 전부 `buildAppTheme()`를 쓰는데 테스트는 한 곳도 안 씌운다. 실측 결과 지금 값은 테마 유무 모두 543.0으로 동일했으나(틀린 값이 있는 건 아니다), 테마가 바뀌어도 검사가 못 느끼는 구조라 두 검사에 실제 테마를 배선했다(나머지 테스트 파일은 신규 defer로 등재).
  - `[low]` `[patch]` **검사 3건이 대상이 아니라 픽스처를 검사**하고 있었다(adversarial 발견). ① D5 검사가 "셋째 칩이 화면 밖"(`right > 360`)을 단언해, 서버 칩 문자열이 짧아지면 D5 위반 없이도 빨간불이 된다 → 가로 스크롤이 실제로 흡수하는지(`maxScrollExtent > 0`)로 교체. ② 정렬 검사의 부동소수 **정확 일치** → 1px 여유(막으려는 회귀는 10px이라 그대로 잡힌다). ③ `parseNarrowedBy` 주석이 빈 배열을 "wire/스키마 버그 신호"라 적어 검사가 있는 것처럼 읽혔으나 로그도 assert도 없다 → 주석을 코드 사실에 맞춰 낮췄다(CLAUDE.md B9). 함께 `_MessageBubble.onTapChip` 주석("null이면 로딩 중" — 실제 게이트는 `isLast`)과 `_ClarifyChips` 주석의 사실오류("채팅 버블 폭 안에 갇힌 행" — 실제로는 버블의 형제라 버블보다 넓어질 수 있다)도 정정했다. `ChatMessage`의 손으로 유지하던 전-필드 복사 2벌(`copyWith`+`clearUsedChip`)은 `withUsedChipIndex(int?)` 하나로 합쳤다 — 필드가 늘면 한쪽이 조용히 그 필드를 떨구는 형태였다.
- rejected_as_noise (기록용, 근거 포함):
  - `[medium]` 되묻기 칩을 지난 메시지에도 그리는 설계 자체가 과설계이니 "마지막 메시지에만 렌더"로 단순화하라(adversarial) — 스크롤백에서 무엇을 탭했는지 남기는 것은 1차 패스가 **의도적으로 추가한 기능**이다. 두 패스가 수렴시킨 설계를 3차에서 되돌리는 것은 개선이 아니라 churn이고, 기능을 잃는다.
  - `sprint-status.yaml`이 HEAD에서 `backlog`인데 스펙·대장은 done(adversarial) — 오케스트레이터 소유 파일이며 리뷰 diff 밖이다. 해당 변경은 작업트리에 대기 중이고 residual artifacts로 이미 기록돼 있다.
  - `review_loop_iteration: 0`이 2회 리뷰 기록과 모순(adversarial) — 이 필드는 리뷰 횟수가 아니라 **bad_spec 재작성 루프** 카운터다(step-04는 bad_spec 루프백 직전에만 증가시키고, `done` 스펙 재진입 시 step-01이 0으로 되돌린다). 정의대로 동작 중이다. `final_revision`의 7자리 sha 표기도 동일하게 표기 취향 문제.
  - I11 문서 오류(문서 500 vs 서버 1000)를 같은 파일을 편집하는 김에 고쳤어야 한다(adversarial) — 이 스토리 이전부터 있던 어긋남이고 **2차 패스가 이미 대장에 등재**했다(트리거: 그 파일을 다음에 손대는 자리 또는 Epic 16 회고). 중복 등재는 장부만 흐린다.
  - 정정한 I12가 길어 제약과 경위가 섞였다(adversarial, CLAUDE.md B8) — 실제 지적은 타당하나, 그 문단이 길어진 이유는 "한 번 틀렸던 불변식"이라는 사실 자체가 다음 사람에게 필요한 정보이기 때문이다. 경위를 `decisions-archive.md`로 옮기는 것은 문서 구조 재편이라 이 스토리의 리뷰 패치 범위를 넘는다.
  - DW-592/DW-594가 실제 종료 조건이 충족되기 전에 닫혔다(adversarial 2건) — 지적 자체는 맞지만 **두 항목 모두 2차 패스가 같은 내용을 신규 항목으로 다시 세워 추적 중**이고(배포 게이트 재확인, "7인승" 불일치), 기존 항목의 상태는 오케스트레이터 소유라 이 세션이 고칠 수 없다(이번 호출의 명시 제약).
  - 신규 장부 항목이 `### DW-<번호>` 형식이 아니다(adversarial) — 이 파일은 두 형식이 **설계상 공존**한다. step-04가 규정한 `- source_spec:` 리스트 형태에 이 프로젝트 규약인 `trigger:`를 얹는 것이 최근 항목들의 일관된 모양이다.
  - 길이 가드(`_submit`의 500자 체크)에 전용 테스트가 없다(adversarial·edge-case) — 타이핑 경로는 `maxLength`가 이미 막으므로 이 가드를 트립시키려면 **서버가 500그래핌 넘는 칩을 보내야** 하는데, 계약상(고정 3개 짧은 문자열) 도달 불가다. 불가능한 시나리오용 검사를 만들지 않는다(CLAUDE.md A2). 단위(그래핌)는 이모지 테스트가 이미 못박고 있다.
  - 500그래핌이 서버의 1000 코드포인트를 넘을 수 있어 가드가 선제적이지 않다(intent-alignment) — ZWJ 연쇄 이모지 500개 같은 병리적 입력에서만 성립하고 결과는 서버 422 안내다. 같은 A2 근거.
  - 칩 행에 스크롤 어포던스(Scrollbar·부분 노출)가 없다(adversarial) — D5(project-context.md 13)가 초과분 흡수 수단으로 **가로 스크롤과 가장자리 부분 클리핑을 명시적으로 허용**한다. Scrollbar 추가는 intent에 없는 새 UI 설계다.
  - 공백만 입력하면 전송이 조용히 무시된다(edge-case) — 이 스토리 이전부터의 동작이고, 빈 제출을 조용히 무시하는 것은 통상적이다.
  - `answer`가 비고 `clarify`만 오면 빈 버블이 뜬다(edge-case) — 1·2차 패스가 `clarify_node.py`를 직접 읽어 `answer`와 `clarify.question`이 항상 같은 상수임을 확인하고 두 번 reject한 사안. 전제가 서버 계약상 도달 불가.
  - `parseNarrowedBy`가 소비처 없는 죽은 코드다(adversarial) — 스펙 Always가 파싱을, Never가 미렌더를 각각 명시적으로 요구한 설계다(DW-597).
  - 매트릭스 "칩 탭" 행의 "실패 시 …입력 복원"과 구현이 다르다(intent-alignment) — 칩 문자열을 사용자가 타이핑한 적 없는 입력창에 밀어 넣는 것은 초안 파괴이므로 합리적 독해가 하나뿐이다(1차 패스가 판단하고 Triage Log에 근거를 남겼다). intent_gap 아님.
  - 검증 기록의 숫자가 안 맞는다(adversarial) — 사실이라 **reject가 아니라 아래 Auto Run Result에서 직접 정정**했다(2차 "새 검사 8건" → 실제 신규 테스트 7건 + 변이 8건, 1차 "신규 3건" → 실제 +1건).

## Design Notes

**D14("Riverpod 검색 상태를 웹과 동일 형태로 미러링")는 새 전역 상태 클래스를 요구하지 않는다.** 계획 단계 조사 결과 웹 `ChatAssistant.tsx`(66-77행)는 `useState` 5개(messages/input/loading/error/wishedIds)뿐인 순수 로컬 상태이고, `clarify`/`narrowed_by`를 아예 렌더하지 않아 미러링할 전역 패턴 자체가 없다. 앱은 이미 같은 형태(로컬 `State` 필드 + `wishedListingIdsProvider` 하나만 전역)를 쓰고 있어 이번 스토리로 아키텍처를 바꿀 필요가 없다(spec-16-4가 확인한 "Dart State 필드는 ref 미러링 불필요" 원칙의 연장).

**입력 500자 상한은 서버 하드 상한(1000)과 다른 층이다.** `api/app/schemas/ai.py`의 `MAX_QUERY_LENGTH=1000`은 서버가 422로 거부하는 절대 상한이고, 500은 웹 `HeroSearch.tsx:24`(`MAX_QUERY_LENGTH = 500`)가 이미 쓰는 더 엄격한 UX 상한이자 `EXPERIENCE.md:110`·이 스토리의 epics AC가 명시한 값이다. 웹 `ChatAssistant.tsx`는 아직 1000을 쓰는 드리프트가 있는데(대화 화면 전용, 히어로와 불일치), 그건 웹 자체의 미해결 불일치이지 이 스토리가 따라야 할 정본이 아니다 — 앱은 EXPERIENCE.md·epics AC의 500을 따른다.

**칩 탭 전송은 `_submit()` 경로를 재사용한다.** 새 전송 함수를 만들면 낙관적 버블·에러 롤백·로딩 잠금 로직이 두 벌이 된다. `_submit({String? overrideQuery})` 형태로 확장해 칩 탭이 `_submit(overrideQuery: chipText)`를 호출하게 하면 기존 동작을 그대로 물려받는다.

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 로컬/개발 API로 "패밀리카로 무난한 거 추천해줘" 같은 애매한 질의를 던져 실제 되묻기 칩이 뜨는지, 탭 시 다음 턴이 이어지는지 1회 실측. 이 세션(헤드리스 샌드박스)이 CanvasKit `CONTEXT_LOST_WEBGL`로 렌더를 못 띄우면(spec-16-4 선례) 대장에 등재하고 위젯테스트로 대체 확인한 사실을 명시한다.

## Auto Run Result

**Status:** done (후속 리뷰 3차 반영)

### 3차 후속 리뷰 패스 (2026-08-08)

**Summary:** 이번 패스의 수확은 대부분 **"있다고 적혀 있었지만 실제로는 아무것도 안 보던 검사"**다. 4개 레이어가 독립적으로 같은 방향을 가리켰고, 변이(mutation)로 하나씩 확인했다 — 이 스토리의 헤드라인 AC(칩 문자열을 그대로 보낸다)와 그 옆의 `context` 전달, 그리고 4갈래 중 REJECT 하나가 전부 실행되는 검사 없이 "추론으로 커버됨" 처리돼 있었다. 특히 REJECT 는 앞선 두 패스가 "같은 렌더 분기를 타므로 커버된다"고 논증해 비워 둔 자리였는데, 실제로 `narrowed_by`를 화면에 흘리는 변이를 넣어도 전 스위트가 green 이었다(CLAUDE.md B4가 말하는 "정연한 논증은 검증이 아니다"의 실례). 행동 결함은 둘 — 같은 문자열 칩 둘 중 하나를 탭하면 **둘 다** 선택·비활성이 됐고(1차 패스가 칩 `Key`를 인덱스로 굳힌 판단과 어긋나는 절반짜리 방어였다), 같은 프레임 연타가 진행 중인 칩의 선택 표시를 지웠다. 둘 다 코드를 읽고 끝내지 않고 프로브를 띄워 실제 플래그를 찍어 확인했다. 나머지는 플랫폼별 `maxLength` 강제 차이(web·iOS의 한글 조합 중 카운터 초과), 기본 카운터를 끄며 잃은 스크린리더 시맨틱, 그리고 픽스처를 검사하던 단언 3건이다.

**Files changed (이번 패스):**
- `app/lib/features/ai_search/ai_chat_screen.dart` — `_onChipTap` 맨 앞 `_loading` 가드(연타 경합), 칩 선택을 인덱스 기준으로, 도달 불가능한 `_loading ||` 렌더 게이트 제거 + 주석 정정, 카운터 표시 clamp + `Semantics(liveRegion)`, `_MessageBubble`/`_ClarifyChips` 주석 사실 정정
- `app/lib/features/ai_search/chat_message.dart` — `usedChip`(문자열) → `usedChipIndex`(인덱스), `copyWith`+`clearUsedChip` 두 벌을 `withUsedChipIndex(int?)` 하나로 통합
- `app/lib/features/ai_search/ai_search_api.dart` — `parseNarrowedBy` 주석을 코드 사실에 맞춰 정정(빈 배열을 "신고"하지 않는다)
- `app/test/ai_chat_screen_test.dart` — 전송 인자(query·context) 실단언, 체크 아이콘 단언, 실패 시 초안 보존 단언, D5 를 가로 스크롤 실동작으로 단언, 정렬 1px 여유, 기하 검사 2건에 실제 앱 테마 배선, 신규 4건(중복 문자열 칩 · 같은 프레임 연타 · IME 조합 중 카운터 clamp · REJECT 갈래)
- `_bmad-output/implementation-artifacts/deferred-work.md` — 신규 defer 2건 등재(기존 항목 무수정)

**Review findings breakdown (이번 패스):** patch 12건(medium 4, low 8 — 전부 반영+재검증) · defer 2건(전부 신규 등재) · reject 13건(medium 1, low 12) · intent_gap 0 · bad_spec 0.

**Follow-up review recommendation:** true (patch high 0 → 점수 계산: 3×medium 4 + 1×low 8 = 20 ≥ 5).

**Verification performed (오케스트레이터 직접 실행):**
- `flutter analyze` — No issues found (패치 전·후)
- `flutter test` — 패치 전 324/324 green → 패치 후 **328/328 green**(신규 테스트 4건, 기존 테스트에 단언 6건 추가)
- `flutter build web --dart-define-from-file=.env.json` — ✓ Built build/web
- **검사 증명(red/green) 10건** — 각각 프로덕션 코드를 한 곳씩 변이시켜 **의도한 그 테스트가** 실패하는 것을 확인하고 백업본으로 원복(`git checkout` 미사용, 원복 후 md5 일치 확인): ① 선택 판정을 문자열 비교로 되돌림 ② `_onChipTap`의 `_loading` 가드 제거 ③ 카운터 clamp 제거 ④ `narrowed_by`를 버블 본문에 노출 ⑤ 칩 탭이 다른 문자열 전송 ⑥ 칩 경로에서 `context` 떨굼 ⑦ 실패 롤백이 초안 덮어씀 ⑧ 체크 아이콘 제거 ⑨ 가로 스크롤 자체 제거(2차의 `Row`→`Wrap`과 **다른 형태**로 깼다 — 세션 메모리 "검사 증명은 형태를 바꿔 다시 깨본다") ⑩ 기본 Material 카운터 복귀. 원복 후 328/328 green 재확인.
- 주장 대신 **측정**한 것 3건: (a) 중복 칩 프로브 — `['SUV','SUV','세단']`에서 첫 칩 탭 후 selected 플래그 `[true, true, false]` (b) 연타 프로브 — 진행 중인 칩 `selected=false`, 요청은 1회 (c) 테마 유무별 정렬 — 전송 버튼/입력 텍스트 세로 중심이 **양쪽 모두 543.0**(테마 부재가 지금 값을 틀리게 하고 있지는 않다는 반증까지 포함). 프로브 파일은 전부 삭제했다.
- 리뷰 레이어 두 곳의 **주장이 엇갈린 지점은 SDK 소스로 갈랐다** — `maxLength` 기본 강제 방식은 Android·Windows만 `enforced`, web·iOS·macOS·linux는 `truncateAfterCompositionEnds`(`text_formatter.dart` 실측). 한쪽 레이어의 "Android도 조합 중 초과 허용" 주장은 사실과 달랐다.

**Residual risks (이번 패스 이후):**
- **여전히 실기기/정상 브라우저 렌더는 0회다.** 이번 패스도 소스와 위젯트리만 보고 중복 칩·연타·조합 중 카운터를 새로 잡아냈다 — 세 패스 연속으로 "읽기만 해도 나오는 결함"이 계속 나온다는 것은 렌더 단계에만 사는 결함이 아직 한 번도 걸러지지 않았다는 뜻이다(대장 기등재, 트리거: Epic 13의 `main` 병합 자리 및 Epic 16-6).
- HTTP 층(`jsonDecode`·상태코드·헤더)은 여전히 어떤 검사도 지나가지 않는다 — `searchAi`에 주입 시접이 없다. **이번 패스에서 신규 defer 로 등재**했다(트리거: wire 계약을 다음에 넓히는 자리).
- 위젯테스트가 실제 앱 테마를 안 씌우는 문제는 이 스토리의 기하 검사 2건만 고쳤고, 나머지 테스트 파일은 그대로다(신규 defer 등재).
- 대장의 DW-592(배포 게이트)·DW-594("7인승" 불일치)가 실제 종료 조건 충족 전에 `done`으로 닫혀 있다는 지적은 타당하나, 두 사안 모두 2차 패스가 신규 항목으로 다시 세워 추적 중이고 기존 항목 상태는 오케스트레이터 소유라 이 세션이 고치지 않았다.

**Residual artifacts (커밋하지 않고 그대로 둔 것):** `_bmad-output/implementation-artifacts/sprint-status.yaml`(16-5를 `backlog`→`done`으로 바꾸는 미커밋 변경) — 이번 리뷰 diff 밖이며 오케스트레이터 소유 파일이라 손대지 않았다.

---

### 2차 후속 리뷰 패스 (2026-08-08)

**Summary:** 1차에서 done으로 닫힌 코드를 4개 레이어로 다시 훑어 **9건을 패치**했다. 성격이 갈린다 — ① 1차 패스가 만든 칩 상태머신(`usedChip`·`isLast` 게이트)의 뒷면: 전송 실패 시 그 칩이 영구 비활성이 되고, 잠긴 칩이 활성 칩과 똑같이 보였다. ② 1차 패스가 "검증했다"고 적은 것 중 **실제로는 아무것도 안 보던 검사** 3건: 빈 chips 테스트가 존재하지 않는 위젯 타입을 찾고 있었고(변이 실측으로 확인 — 렌더 조건을 지워도 green), 공백 칩 규칙에 테스트가 없었고, wire JSON→화면 이음매를 지나가는 검사가 없었다. ③ 상한을 두 단위로 세는 문제(이모지에서 카운터와 전송 가드가 갈림)와 카운터가 전송 버튼을 10px 밀어낸 정렬 어긋남. 신규 테스트 7건 + 기존 테스트의 단언 교체 1건에 대해 **변이 8건을 일부러 넣어 red 확인 → 원복해 green 확인**했다. (※ 3차 패스 정정: 원문은 "새 검사 8건"이라 적었으나 테스트 수는 7건이고 8은 변이 횟수다 — 324−317=7과 어긋나던 것을 실제 수치로 맞춘다.)

**Files changed (이번 패스):**
- `app/lib/features/ai_search/ai_chat_screen.dart` — `_submit`이 성공 여부 반환(칩 실패 롤백용), `_onChipTap` 실패 시 선택 표시 해제, 잠긴 칩 흐린색 분기, 그래핌 기준 길이 가드, 기본 카운터 제거 + Row 밖 자체 카운터, `_ClarifyChips`에 테스트용 Key
- `app/lib/features/ai_search/chat_message.dart` — `clearUsedChip()` 신설, 상수 블록 주석 분리(UX 상한은 서버 계약의 예외임을 명시)
- `app/lib/features/ai_search/ai_search_api.dart` — `parseClarifyPayload` 주석 정정(웹 미러가 아니라 한 겹 엄격, 이유 포함)
- `app/test/ai_chat_screen_test.dart` — 빈 chips 단언 교체(Key 기반), 신규 5건(칩 실패 후 재탭·잠긴 칩 색·D5 한 줄·이모지 그래핌·wire JSON 이음매), "이 검사들이 안 보는 것" 명시
- `app/test/ai_search_test.dart` — 공백/빈 문자열 칩 케이스 2건
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md` — I12에 서버 강제의 잔여 우회(DW-591) 한 줄 추가
- `_bmad-output/implementation-artifacts/deferred-work.md` — 신규 defer 4건 등재(기존 항목 무수정)

**Review findings breakdown (이번 패스):** patch 9건(medium 4, low 5 — 전부 반영+재검증) · defer 4건(전부 신규 등재) · reject 6건(전부 low) · intent_gap 0 · bad_spec 0.

**Follow-up review recommendation:** true (patch high 0 → 점수 계산: 3×medium 4 + 1×low 5 = 17 ≥ 5).

**Verification performed (오케스트레이터 직접 실행):**
- `flutter analyze` — No issues found (패치 전·후)
- `flutter test` — 패치 전 317/317 green → 패치 후 **324/324 green**(신규 7건)
- `flutter build web --dart-define-from-file=.env.json` — ✓ Built build/web
- **검사 증명(red/green) 8건** — 각각 프로덕션 코드를 한 곳씩 변이시켜 의도한 테스트가 정확히 실패하는 것을 확인하고 백업본으로 원복(`git checkout` 미사용): ① 렌더 조건 `chips.isNotEmpty` 제거 ② 칩 실패 롤백 제거 ③ 잠긴 칩 흐린색 제거 ④ `Row`→`Wrap`(D5 위반) ⑤ 기본 Material 카운터 복귀(정렬 깨짐) ⑥ `characters.length`→`length`(이모지) ⑦ `parseSearchResult`가 clarify 무시(이음매) ⑧ 공백 칩 폐기 규칙 제거. 원복 후 324/324 green 재확인.
- 정렬은 주장이 아니라 **측정**했다: 수정 전 전송 버튼 중심 y=554 vs 입력 텍스트 중심 y=544(10px 어긋남) → 수정 후 543 == 543. D5 한 줄 유지도 360px 뷰포트에서 칩 3개의 top이 모두 동일하고 총폭이 화면을 넘는 것(=가로 스크롤이 흡수)으로 실측.

**Residual risks (이번 패스 이후):**
- **여전히 실기기/정상 브라우저 렌더는 0회다.** 이번 패스가 소스만 읽고 잠긴 칩 무신호·10px 정렬 어긋남을 새로 잡아냈다는 사실이 그 부재의 증거다(대장 신규 등재, 트리거: Epic 13의 `main` 병합 자리 및 Epic 16-6).
- HTTP 층(jsonDecode·상태코드·헤더)은 위젯테스트가 지나가지 않는다 — `searchAi`가 top-level `http.post`를 직접 불러 주입 시접이 없다. wire→화면 이음매는 `parseSearchResult`까지만 이어져 있다(테스트 파일 헤더에 명시).
- 데모 각본의 "7인승" 칩과 서버 고정 3축의 불일치, 웹 `ChatAssistant.tsx`의 1000자 드리프트, I11 문서 오류는 전부 신규 defer로 등재만 하고 이번 범위에서 고치지 않았다.

**Residual artifacts (커밋하지 않고 그대로 둔 것):** `_bmad-output/implementation-artifacts/sprint-status.yaml`(16-5를 `backlog`→`done`으로 바꾸는 미커밋 변경) — 이번 리뷰 diff 밖이며 오케스트레이터 소유 파일이라 손대지 않았다.

---

### 1차 패스 (2026-08-08)

**Summary:** Flutter 앱 AI 검색이 서버의 4분기 응답 계약(`clarify`·`narrowed_by`)을 파싱해 되묻기 칩을 렌더하게 됐다. 되묻기 칩은 탭 가능하고, 탭하면 기존 `_submit()` 파이프라인(낙관적 버블·에러 롤백·로딩)을 그대로 타 다음 질의를 보낸다. 되묻기 상한은 서버가 `context` 길이로 강제하므로(정정된 I12) 클라는 별도 카운터 없이 `clarify` null 여부만 본다. 입력 상한을 500자로 낮췄다(서버 하드 상한 1000과는 별개의 UX 상한). 리뷰 패스에서 발견된 6건(초안 유실, 낡은 칩 재사용에 의한 대화 되감기, D5 위반 2줄 밀림, 선택 상태 미표시, 공백 칩 미필터, 칩 Key 충돌 위험)을 전부 패치했다.

**Files changed:**
- `app/lib/features/ai_search/ai_search_api.dart` -- `ClarifyPayload` 클래스, `parseClarifyPayload`/`parseNarrowedBy` 순수 함수(공백 칩 방어 포함), `SearchResult`에 `clarify`/`narrowedBy` 필드
- `app/lib/features/ai_search/chat_message.dart` -- `ChatMessage`에 `clarify`/`usedChip` 필드+`copyWith`, `maxQueryLength` 1000→500
- `app/lib/features/ai_search/ai_chat_screen.dart` -- `_submit(overrideQuery:)` 확장(칩 탭 재사용, 사용자 초안 보존), `_onChipTap`(선택 표시+마지막 메시지만 활성), `_ClarifyChips`(가로 스크롤 단일 행, `ChoiceChip` 선택 상태), `TextField maxLength:500`
- `_bmad-output/planning-artifacts/architecture-increment-2026-07-12.md` -- I12 정정(서버 강제로, DW-589)
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-589/592/594 닫음, DW-597 앱 쪽만 progress 주석, 수동검증 미실행 defer 신규 등재
- `app/test/ai_search_test.dart` -- `parseClarifyPayload`/`parseNarrowedBy`/`parseSearchResult` 단위테스트 확장(공백 칩 케이스 포함)
- `app/test/ai_chat_screen_test.dart` -- 칩 렌더·탭 전송·빈 chips 미렌더·500자 상한·초안 보존·낡은 칩 비활성화·선택 상태 위젯테스트

**Review findings breakdown:** patch 6건(medium 3, low 3, 전부 반영+재검증 완료) · defer 0건(신규, 기존 defer 1건은 이번 패스 이전에 이미 등재됨) · reject 10건(전부 low — 워크플로 자체의 순서 문제이거나, 실측/코드 추적으로 반증됐거나, 스펙이 이미 근거와 함께 확정한 의도된 설계였다 — Review Triage Log에 근거 포함 기록).

**Follow-up review recommendation:** true (patch 3×medium + 3×low → 3×3+1×3=12 ≥ 5).

**Verification performed (오케스트레이터 직접 재실행 확인, 패치 전/후 각각):**
- `flutter analyze` — 0 issues (패치 전·후 모두)
- `flutter test` — 패치 전 316/316 green, 패치 후 317/317 green (※ 3차 패스 정정: 원문은 "신규 3건 포함"이라 적었으나 실제 증가분은 +1건이다 — 초안 보존·낡은 칩 비활성화·선택 상태 중 뒤 둘은 새 테스트가 아니라 기존 테스트에 추가된 단언이었다)
- `flutter build web --dart-define-from-file=.env.json` — 빌드 성공(구현 단계에서 확인, 패치 적용 에이전트가 재확인)
- I/O & Edge-Case Matrix 7행 전부 실행되는 테스트로 커버(REJECT/구조형/하이브리드 응답은 verification-gap 리뷰 레이어가 코드 경로 동치성을 직접 추적해 "칩 빈 배열" 위젯테스트와 같은 렌더 분기를 탄다는 것을 확인 — 별도 전용 위젯테스트 없이도 커버로 판정)
- Manual checks(로컬 API로 화면 상에서 되묻기 칩 확인)는 이 세션(헤드리스 샌드박스)에서 실행 불가(Playwright는 Flutter 웹 부트스트랩 중 JS null-check 예외, 실기기는 adb 연결 불안정) — 대신 로컬 FastAPI+Supabase에 4개 시나리오(되묻기/칩 재요청/거절/상한초과)를 curl로 직접 호출해 백엔드 계약과 파싱 가정이 정확히 일치함을 실측 확인. 화면 렌더 자체는 장부(`deferred-work.md`, source_spec: spec-16-5)에 등재, 트리거는 Epic 16-6(SM-D 통합 시연 검증, 실기기)

**Residual risks:**
- 실기기/정상 브라우저에서 되묻기 칩이 실제로 그려지고 탭이 다음 턴을 잇는지 한 번도 실측되지 않았다(대장 등재, 트리거: Epic 16-6). 이번 리뷰가 소스만 읽고 D5 위반(2줄 밀림)·선택 상태 미표시를 잡아냈다는 사실 자체가 실측 부재의 증거이므로, 실기기 확인 시 시각적 회귀가 없는지 함께 본다.
- `clarify.chips`의 값 축(가격·차종·연료 vs EXPERIENCE.md 예시 "7인승")은 이 스토리가 렌더링은 값의 의미와 무관하다는 원칙으로 결정을 닫았지만, 어느 쪽이 제품적으로 옳은지는 여전히 미정이다(DW-594, Epic 13 소관).
- DW-597(REJECT `narrowed_by`의 재제안 칩 UI)은 앱 쪽만 이번 스토리에서 닫혔고 웹 쪽은 Epic 15로 그대로 열려 있다 — 의도된 부분 해소.
