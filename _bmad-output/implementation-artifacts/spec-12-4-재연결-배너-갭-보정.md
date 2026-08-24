---
title: '12.4 재연결 배너 + 갭 보정'
type: 'feature'
created: '2026-07-29'
status: 'done'
baseline_revision: 'b581b450b15f06623b79237a00abfc4616eb197d'
final_revision: '1a1fd5688a2b0159bdf6de9f3da1a69403097935'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 12.3이 `ChatRoomMessages.tsx`에 실시간 구독을 배선했지만, 연결이 끊겨도 사용자는 "새로고침 후 다시 시도"만 안내받는다 — 계속 타이핑·전송할 수 없고, 끊긴 동안 상대가 보낸 메시지는 재조회 경로가 없어 새로고침 전까지 화면에 없다.

**Approach:** 기존 `channel.subscribe((status, err) => ...)` 콜백이 이미 구분하는 CHANNEL_ERROR/TIMED_OUT(끊김) ↔ SUBSCRIBED(연결됨) 전이만으로 비차단 배너 상태를 만든다(새 재구독 로직 불필요 — 아래 Design Notes 실측 근거). 끊긴 동안 제출한 메시지는 네트워크 호출 없이 로컬 큐에 쌓아 즉시 pending으로 보여주고, 재연결되면 순서대로 flush한다(멱등키 재사용). 재연결 시 상대의 누락 메시지는 Broadcast Replay(채널 config 플래그 하나)와 `fetchMessages`의 기존 커서 재조회를 병행해 병합한다.

## Boundaries & Constraints

**Always:**
- 연결 상태는 기존 `channel.subscribe` 콜백의 CHANNEL_ERROR/TIMED_OUT(끊김) ↔ SUBSCRIBED(재연결, `everDropped`였을 때)만으로 판단한다 — 소켓·채널을 수동으로 재생성하거나 `channel.subscribe()`를 다시 호출하는 로직을 만들지 않는다(Design Notes 실측: 네트워크 드롭은 라이브러리의 채널 `rejoinTimer`가 자동으로 재조인한다).
- 끊김 시 배너 문구를 "연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요."로 바꾸고, 입력창·전송 버튼을 잠그지 않는다(FR42, UX-DR19 — 비차단).
- 끊긴 동안 제출된 메시지는 `sendMessage` 네트워크 호출을 시도하지 않고, 제출 시점에 만든 `client_message_id`로 즉시 pending 버블을 보여주며 로컬 큐(순서 보존)에 적재한다. 여러 건 동시 대기가 가능해야 하므로 기존 단일 `pending` 상태를 큐/배열로 확장한다.
- 재연결(SUBSCRIBED, 이전에 끊긴 적 있음) 시: (a) 배너를 초록 "다시 연결됐어요"(색+텍스트 동시 표기, 접근성 비색 신호 중복)로 바꾼 뒤 일정 시간 후(예: 3000ms) 사라지게 한다. (b) 큐를 순서대로(순차 await) 기존 `sendMessage()`로 전송한다 — 큐잉 시점의 `client_message_id`를 그대로 재사용한다(새 키 생성 금지, 재시도해도 `23505` 흡수 경로로 멱등이 성립하게 한다). 전송이 실패한 항목은 버리지 않고 큐 맨 앞에 남겨 다음 재연결 때 재시도한다.
- 재연결 시 상대가 보낸 누락 메시지 병합: 채널 생성 config에 `broadcast: { replay: true }`를 추가해(private 채널에서만 허용) Broadcast Replay를 활성화하고, **그와 별개로 항상** 마지막으로 반영한 메시지의 `created_at`을 커서로 `fetchMessages(supabase, roomId, cursor)`(`gte`, CR6 — strict `>` 아님) 재조회를 재연결마다 수행한다. 두 경로 모두 기존 `mergeIncoming`/`dedupeById`(id 기준)로 합류시킨다 — 경로가 겹쳐도 중복 없이 수렴한다.
- `docs/conventions.md` §12에 신설 절(§12.5)로 이 절의 재연결·큐잉·갭보정 계약(replay 플래그, 커서 병행 이유, CLOSED가 실제 네트워크 드롭에서 발생하지 않는다는 실측 사실)을 문서화한다 — Epic 16.4가 참조할 단일 출처.
- 채팅 무결성 3중 장치(RLS·트리거·CHECK)는 이번에도 무수정으로 유지한다(CM-B) — `realtime.messages`의 기존 0023 SELECT 정책이 topic 기반이라 replay 응답도 이미 동일하게 커버하므로 신규 마이그레이션이 필요 없다.

**Block If:** (사람 판단이 필요한 신규 결정 없음 — 재연결·갭보정의 기술적 축은 모두 위 Always와 아래 Design Notes 실측으로 이미 결정돼 있다.)

**Never:**
- CLOSED 상태를 위한 별도의 수동 재구독/소켓 재생성 로직을 새로 만들지 않는다 — 실측(Design Notes)상 네트워크 드롭은 CLOSED가 아니라 CHANNEL_ERROR/TIMED_OUT을 발생시키고, 라이브러리가 자동 재조인한다. CLOSED는 명시적 `leave()`(방 전환·언마운트)에서만 발생하며 기존 `cancelled` 가드로 이미 무해하다 — 12.3의 기존 CLOSED 분기는 그대로 둔다(제거·리팩터 금지, A3).
- 안읽음 배지·방 목록 정렬은 만들지 않는다 — Story 12.5 범위.
- Flutter 앱(`app/lib/features/chat/**`)은 손대지 않는다 — Epic 16 Story 16.4 전담.
- 재연결·오프라인 큐잉·갭보정 전체 흐름을 검증하는 새 자동 E2E를 만들지 않는다 — 이 성공 지표는 Story 12.6이 두 브라우저 수동 검증으로 닫기로 에픽 레벨에서 이미 정해져 있다(12.1~12.3과 동일 결정).
- Broadcast Replay의 ≤25건/72시간 한도를 client 코드로 재구현하거나 우회하지 않는다 — 플랫폼 기본값이며 커서 재조회가 그 한도를 넘는 몫을 이미 메운다.
- 네트워크 상태 감지에 `navigator.onLine`/`window` `online`/`offline` 이벤트를 새로 배선하지 않는다 — 실측(Design Notes)상 라이브러리는 이 신호를 쓰지 않고 순수 웹소켓 신호(끊김/heartbeat 타임아웃)로만 재연결한다. 채널 status 콜백 하나로 충분하다.
- 오프라인 큐를 `localStorage` 등으로 영속화하지 않는다 — 새로고침은 기존 경로(초기 전체 `fetchMessages` 로드)로 이미 복구되며, 인메모리 큐(컴포넌트 상태)만으로 이번 AC(연결이 끊긴 채로 계속 작성·전송)를 충족한다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 연결 끊김 발생 | 구독 중 CHANNEL_ERROR/TIMED_OUT 수신 | 비차단 배너("연결이 끊겼어요…") 노출, 입력·전송 계속 가능 | 없음(설계된 정상 경로) |
| 끊긴 동안 전송 | 배너 노출 중 사용자가 메시지 제출(여러 건 가능) | 네트워크 호출 없이 즉시 각각 pending 버블 표시 + 로컬 큐에 순서대로 적재 | 없음 |
| 재연결 성공 + 큐 존재 | SUBSCRIBED 재도달(`everDropped=true`), 큐에 N건 | 배너가 초록 "다시 연결됐어요"로 전환 후 사라짐, 큐가 순서대로 전송되고 중복 행 없음(동일 client_message_id 재사용 + 23505 흡수) | 큐 항목 전송 실패 시 그 항목을 큐에 남겨 다음 재연결에 재시도(버리지 않음) |
| 갭 보정(상대 메시지 누락) | 끊긴 동안 상대가 INSERT, 재연결됨 | Broadcast Replay + `created_at >= cursor` 재조회 병합으로 화면에 유실 없이 반영, 중복 없음(dedupeById) | 재조회 자체가 실패하면 기존 `loadError`류 안내(fail-loud), 큐 flush는 별개로 계속 진행 |

</intent-contract>

## Code Map

- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- 연결 상태(끊김/재연결) 추적 및 배너 문구·색상 전환+자동 소멸, `pending`을 단일 값에서 큐(배열)로 확장, 재연결 시 큐 flush(순차·키 재사용) + 갭보정(커서 재조회) 트리거, 채널 config에 `broadcast: { replay: true }` 추가.
- `web/src/lib/messages.ts` -- 필요 시 큐 항목 타입/순수 헬퍼 추가(네트워크 호출 자체는 기존 `sendMessage` 재사용 — 새 API 호출 경로를 만들지 않는다).
- `docs/conventions.md` -- §12.5 신설(재연결·오프라인 큐잉·Broadcast Replay+커서 병행 갭보정 계약, CLOSED가 네트워크 드롭에서 발생하지 않는다는 실측 사실).
- `web/e2e/helpers.ts`, `web/e2e/viewport-audit.spec.ts` -- 참고만(무수정 예상) — 이 스토리는 새 화면을 추가하지 않고 기존 채팅방 화면의 상태 전이만 바꾼다.
- `supabase/migrations/0023_chat_realtime_broadcast.sql` -- 참고만, 무수정 — `realtime.messages` SELECT 정책이 topic 기반이라 replay 응답도 이미 커버한다.

## Tasks & Acceptance

**Execution:**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- 채널 `config`에 `broadcast: { replay: true }` 추가, subscribe 콜백의 CHANNEL_ERROR/TIMED_OUT/SUBSCRIBED 분기를 재사용해 배너 문구·색상 전환(끊김→회색/빨강, 재연결→초록 후 타이머로 소멸) 배선 -- 이 스토리의 핵심 표면(재연결 신호).
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- `pending`을 큐(배열)로 확장하고 `handleSubmit`에 "연결 끊김이면 네트워크 호출 없이 큐잉만" 분기 추가, 재연결 시 큐를 순서대로 flush(동일 `client_message_id` 재사용, 실패 항목 재큐잉) -- 오프라인 큐잉(FR42).
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- 재연결 시 마지막 반영 메시지의 `created_at`을 커서로 `fetchMessages(supabase, roomId, cursor)` 재조회를 호출해 `mergeIncoming`으로 합류 -- 갭보정(AC-CHAT-2, CR6).
- `docs/conventions.md` -- §12.5 신설 -- Epic 16.4가 참조할 단일 출처, CLOSED 실측 사실 기록.
- `web/src/lib/__tests__/messages.test.ts` (또는 신규 큐 헬퍼 테스트) -- 새로 뺀 순수 로직이 있다면 그 단위 테스트 -- B9(실행되는 검사로 고정).
- `docs/tech-debt.md` -- 이번에 내린 판단(예: replay 25건/72h 한도 초과가 이 데모 규모에서 사실상 미도달) 신규 항목으로 등재 -- B8, 기존 항목은 무수정.

**Acceptance Criteria:**
- Given 실시간 구독 중 연결이 끊기면, when CHANNEL_ERROR/TIMED_OUT이 오면, then 비차단 배너가 뜨고 입력·전송이 계속 가능하다(FR42, UX-DR19).
- Given 배너가 떠 있는 동안 사용자가 메시지를 여러 건 제출하면, when 제출하면, then 네트워크 호출 없이 각각 즉시 pending 버블로 보이고 로컬 큐에 순서대로 쌓인다.
- Given 큐에 메시지가 있는 상태에서 재연결(SUBSCRIBED)되면, when 재연결되면, then 배너가 초록 "다시 연결됐어요"로 전환된 뒤 사라지고, 큐의 메시지가 순서대로 전송되며 `chat_messages`에 중복 행이 생기지 않는다.
- Given 끊겨 있던 동안 상대가 메시지를 보냈다면, when 재연결되면, then Broadcast Replay와 커서 재조회(`created_at >= cursor`)로 그 메시지가 유실 없이 병합되고 중복 없이 표시된다(AC-CHAT-2).
- Given 채팅 무결성 3중 장치(RLS·트리거·CHECK buyer≠seller), when 이 스토리의 변경 전후를 비교하면, then 동일하게 유지된다(CM-B, `supabase/**` 무수정으로 확인).

## Spec Change Log

## Review Triage Log

### 2026-07-29 — Review pass (후속 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 11: (high 0, medium 2, low 9)
- defer: 4: (high 0, medium 0, low 4)
- reject: 7
- addressed_findings:
  - `medium` `patch` **flush 미전송 안내가 하필 "다음 제출마다 무조건 지워지는" 칸(`error`)에 있어, 큐가 막힌 사용자가 메시지를 한 번 더 보내는 순간 유일한 신호가 사라졌다**(adversarial+edge-case-hunter+verification-gap 3중 지적). 2차 패스의 R3가 만든 자기모순이다 — 이 파일은 `realtimeError`·`loadError`를 굳이 갈라둔 이유를 주석으로 적어놓고도 새 신호를 그 규칙 밖에 뒀다. 전용 상태(`queueStuckNotice`)로 옮기고 큐가 실제로 비워질 때만 지우도록 수정. **문구도 함께 정정** — 재시도 트리거는 SUBSCRIBED 재도달 하나뿐이라 "연결이 회복되면 다시 시도합니다"는 거짓이다(그 시점엔 이미 회복돼 있다). **실제 브라우저에서 끊김→큐잉 2건→전송 실패→재연결→안내 노출→추가 제출 순서를 재현해 확인했고, 옛 코드로 되돌리면 그 재현이 red가 되는 것까지 확인**.
  - `medium` `patch` **끊김 중 뒤늦게 도착한 전송 실패 응답이 `setInput(body)`로 사용자가 그 사이 타이핑한 내용을 덮어썼다**(adversarial+edge-case-hunter 교차 지적). 2차 패스의 R5가 끊김 중 입력창 잠금을 푼 결과 "전송 → 응답 대기 중 끊김 → 그 사이 다음 메시지 작성"이 정상 경로가 됐는데, 실패 경로 두 곳은 무조건 옛 본문을 써 넣는 코드 그대로였다. 같은 파일이 이미 브로드캐스트 에코 경로에서 쓰는 함수형 가드(`setInput((cur) => cur === '' ? body : cur)`)를 두 실패 경로에도 적용.
  - `low` `patch` 갭보정 성공 시 `loadError`를 **무조건** 지워, 초기 전체 로드가 실패해 과거 대화가 비어 있다는 경고까지 함께 사라질 수 있었다(edge-case-hunter 지적). 커서 이후만 본 조회의 성공은 그 이전 구간의 증거가 아니다 — 안내의 출처를 추적해 **자기가 세운 것만** 거두게 하고, 커서 없이 돈 전체 재조회일 때만 초기 로드 실패도 함께 거두도록 수정.
  - `low` `patch` flush가 **온라인 경로가 아직 응답을 기다리는 항목까지** 스냅샷에 넣어 같은 키로 두 요청을 동시에 띄웠다(adversarial 지적). 멱등키가 중복 행은 막지만 두 완료 핸들러가 같은 항목에 서로 다른 화면 갱신을 한다 — 소유권 ref를 두어 flush가 그 키를 건너뛰도록 수정.
  - `low` `patch` `broadcast.replay` 계약 검사가 **채널 생성 호출에 앵커되지 않아** replay를 config 밖으로 빼도 green이었다(verification-gap 실측). 2차 패스가 R7로 세운 가드가 절반만 성립한 상태였다 — 형제 검사(private)와 같은 방식으로 앵커. **실제로 replay를 미사용 상수로 옮겨 red 확인 후 원복 → green**.
  - `low` `patch` `private: true` 정규식이 `[^}]*`라 **중첩 객체 안의 private까지** 매치해, 채널이 private가 아닌 상태에서도 green이었다(adversarial 실측). 0023의 `realtime.messages` RLS가 평가되는 유일한 조건이라 false-green을 두면 인가 계층이 조용히 무력화된다 — `[^}{]*`로 조여 config 직속 프로퍼티만 매치하게 수정. **중첩 형태로 바꿔 red 확인 후 원복**.
  - `low` `patch` 갭보정의 **커서 재조회 쪽에만 실행되는 검사가 없었다**(verification-gap 실측: `void gapFillFromCursor();` 한 줄을 지워도 전체 green). §12.5·대장 `#201`이 스스로 "replay는 최적화, 커서가 백스톱"이라 적어놓고 가드는 replay에만 붙어 있어 보호 강도가 거꾸로였다 — 재연결 분기의 호출과 커서 인자 전달을 고정하는 검사 신설. **일부러 지워 red 확인 후 원복**.
  - `low` `patch` 이 스토리의 **최상위 인수조건(끊김 중 비차단)을 지키는 세 조건식이 전부 주석으로만** 보호됐다(verification-gap 실측: 셋 다 12.3 형태로 되돌려도 green). 이 규칙은 이 스토리 안에서 **이미 한 번 깨졌던**(R5가 고친) 것이다 — 소스 스캔 검사 신설(B9). **되돌려 red 확인 후 원복**.
  - `low` `patch` flush 미전송 안내(위 medium 수정)를 지키는 검사도 함께 신설 — **옛 `error` 칸으로 되돌리면 red**가 되는 것까지 확인.
  - `low` `patch` 코드 주석 2곳이 여전히 "≤25건/72시간은 플랫폼 기본 한도"라고 적어, **같은 커밋이 문서에서 정정한 사실과 정면으로 모순**됐다(adversarial 지적). Epic 16.4가 코드를 먼저 읽고 72h를 플랫폼 상수로 오해할 자리라 두 값의 출처를 구분해 정정(`limit 25`=라이브러리 상한, `since 72h`=우리 선택).
  - `low` `patch` §12.5(Epic 16.4가 미러링할 단일 출처)에 **코드 주석에만 있던 제약 2건이 빠져 있었다**(adversarial+verification-gap 지적, B8 "상위 문서의 제약은 하위로 흘린다"): ① replay의 `since`가 마운트 시점에 한 번만 계산돼 탭이 오래 떠 있을수록 커버 구간이 과거로 밀린다(백스톱이 있어 무해한 이유 포함), ② 큐 비영속화의 근거가 사실과 달랐다 — 큐 항목은 정의상 아직 서버에 없으므로 `fetchMessages`가 되살릴 수 없고 새로고침·방 전환은 **복구가 아니라 손실**이다. 결론(비영속)은 유지하되 근거를 정확한 사실로 교체. 이번 패스에서 확정된 계약 4건(안내 칸 분리·문구 정확성·소유권·입력 복원 조건)도 함께 §12.5에 등재.
- defer 4건(대장 신규 등재, 기존 항목 무수정) — `#204` flush가 영구히 멈출 수 있다(supabase-js에 타임아웃이 없어 `isFlushing`이 안 풀리는 경로 + 같은 뿌리의 "끊김 감지 25~35초 지연 중 입력 잠금") · `#205` 오프라인 길이 가드의 재현 경로가 `maxLength` 때문에 실제로 도달 가능한지 미확인(정본 사본조차 경계값 테스트 없음) · `#206` 큐가 막히면 사용자가 다시 보낼 방법이 없다(재시도 트리거가 "다시 끊겼다 붙기" 하나뿐 — 인텐트가 명시적으로 고른 축이라 UI 추가는 하지 않고 문구만 정정) · `#207` 오프라인 큐잉 전체가 라이브러리 한 버전의 소스 독해 위에 서 있는데 의존성은 캐럿 범위다.
- 기각 7건 — 오프라인 경로의 `crypto.randomUUID()` 미보호(https/localhost 전용이라 던질 수 없다 — 1·2차 패스와 동일 근거) · CHANNEL_ERROR 뒤 CLOSED가 와서 배너가 박제된다는 지적(CLOSED가 `cancelled` 없이 도달한다는 근거가 제시되지 않았다 — 실측상 `leave()` 전용) · 구독 준비 실패 시 `disconnectedRef`가 안 켜져 제출이 온라인으로 간다는 지적(그 경우 죽은 것은 Realtime뿐이고 HTTP 전송은 정상이므로 온라인 경로가 오히려 옳다) · 커서 `gte`가 `created_at default now()`(트랜잭션 시작 시각) 때문에 메시지를 영구 누락한다는 지적(단문 INSERT 트랜잭션이라 창이 서브밀리초이고, 재연결은 수초~수분 뒤라 그때까지 미커밋으로 남아 있을 수 없다) · 영구 실패 항목의 head-of-line 블로킹을 방 삭제로 재현할 수 있다는 지적(방이 사라지면 그 화면 자체에 접근이 불가능하다 — 2차 패스와 동일 근거) · 첫 구독이 error→success일 때 갭보정과 초기 로드가 전량 조회를 중복 수행한다는 지적(낭비일 뿐 `mergeIncoming`이 접으므로 정확성 영향 없음, A2) · 방 전환 시 큐가 조용히 사라진다는 지적(인메모리 비영속은 스펙 Never가 명시적으로 택한 절충 — 단 그 **근거 문장**이 틀렸다는 부분은 받아들여 §12.5를 정정했다).

### 2026-07-29 — Review pass (후속 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 9: (high 0, medium 5, low 4)
- defer: 0
- reject: 9
- addressed_findings:
  - `medium` `patch` **오프라인 큐잉 경로가 `reuseFailedKey`를 건너뛰고 무조건 새 UUID를 만들어, FR41 멱등 보호가 뚫리는 실제 중복 저장 경로가 남아 있었다**(adversarial+edge-case-hunter 교차 지적). 재현 순서: 온라인 전송 실패(서버엔 저장됐고 응답만 유실) → 입력 복원 → 그 사이 연결 끊김 → 사용자가 그대로 다시 전송 → 새 키로 큐잉·flush → `chat_messages`에 두 행. 제출 시점의 키 선택 규칙을 온라인·오프라인 동일하게 맞추고, 큐가 키를 인수한 뒤 `lastFailedRef`를 비우도록 수정.
  - `medium` `patch` **온라인 전송이 응답을 기다리는 중에 연결이 끊기면 입력창·전송 버튼이 잠긴 채로 남아, "메시지는 계속 작성할 수 있어요" 배너와 화면이 정면으로 모순됐다**(edge-case-hunter 지적, intent-alignment도 같은 층에서 지적). `sending` 가드가 오프라인 분기보다 앞에 있었고 `disabled={sending || loading}`가 그대로 걸렸다 — supabase-js 호출엔 타임아웃이 없어 그 구간이 길어질 수 있다. 연타 가드를 온라인 경로 전용으로 좁히고, 끊김 중에는 입력창·버튼을 잠그지 않도록 수정(FR42·UX-DR19 비차단). **실제 브라우저에서 in-flight 전송 중 끊김을 만들어 잠금 해제와 큐잉을 실측 확인**.
  - `medium` `patch` **flush가 다 못 보낸 건이 `console.error`에만 남아, 사용자에겐 완전히 정상인 화면으로 보였다**(adversarial+edge-case-hunter+verification-gap 3중 지적). 남은 pending 버블은 정상 전송 중 버블과 시각적으로 동일하고, 재시도 트리거가 "다음 끊김→재연결"뿐이라 연결이 계속 정상이면 영영 재시도되지 않는다 — 초록 배너가 3초 뒤 사라지고 나면 아무 신호가 없다(fail-loud 위반). 남은 건수를 화면 에러로 표시하도록 수정.
  - `medium` `patch` **`isFlushing` 가드가 중복 요청을 "미루기"가 아니라 "버리기"로 처리해, flush 도중 flap으로 큐잉된 항목이 다음 끊김까지 정체됐다**(adversarial+edge-case-hunter 교차 지적). 진행 중이면 재실행 예약 플래그만 세우고 `finally`에서 한 번 더 돌도록 수정.
  - `medium` `patch` **갭보정이 성공해도 앞선 갭보정 실패 안내(`loadError`)가 지워지지 않았다**(adversarial+edge-case-hunter 교차 지적) — 이 상태를 비우는 경로가 "방 전환"뿐이라, 일시적 실패 한 번이 "새로고침 후 다시 시도해주세요"를 세션 내내 박제했다(메시지는 이미 병합돼 있는데). 성공 경로에서 해제하도록 수정. **실제 브라우저에서 조회 실패→성공 두 사이클로 실측 확인**.
  - `low` `patch` `flushMessageQueue`가 `sendFn`의 **예외**를 잡지 않아, 던지면 이 배치에서 이미 저장된 앞쪽 행(`sent`)이 통째로 버려졌다(adversarial+edge-case-hunter+verification-gap 3중 지적). `{ error }` 반환과 동일하게 취급하도록 try/catch 추가 + 그 경로의 vitest 케이스 신설(일부러 깨서 red 확인 후 green 복귀).
  - `low` `patch` `broadcast.replay` 설정을 지켜주는 검사가 하나도 없어, 통째로 사라져도 기존 `private:true` 정규식은 green을 유지했다(verification-gap 지적) — §12.5가 "Replay + 커서 재조회 항상 병행"을 계약으로 못박았으므로 실행되는 검사로 내렸다(B9). 계약 테스트에 replay 존재 단언 추가(일부러 깨서 red 확인 후 green 복귀).
  - `low` `patch` 대장 `#202`가 근거로 든 "정상 앱 흐름에는 DELETE 경로가 **없다**"가 사실이 아니었다(adversarial 지적, 실측 확인) — `0005_admin_policies.sql`에 관리자 삭제 정책(FR25)이 있고 관리자 화면에 방 삭제 버튼이 출고돼 있다. 결론(defer)은 유지하되 근거를 정확한 사실로 정정했다: 방 삭제는 방 자체를 없애 되살아난 방송을 볼 화면이 남지 않고, 단건 메시지 삭제는 정책만 있고 UI가 없다. (이 항목은 이번 스토리 diff가 만든 자기 산출물이라 사실만 정정했고, 상태·우선순위·트리거는 건드리지 않았다.)
  - `low` `patch` §12.5·대장 `#201`이 "25건/72시간이 플랫폼 기본값"이라고 단정했으나, 라이브러리가 정하는 것은 `limit` 상한 25뿐이고 **72시간은 우리가 고른 값**이다(`since`는 필수 인자, README 실측). Epic 16.4가 이 숫자를 "플랫폼 규정값"으로 오해하지 않도록 두 문서를 정정.
- 기각 9건 — 오프라인 큐잉이 웹소켓 상태로 게이트되는데 실제 전송은 HTTP라 "Realtime만 죽고 HTTP는 멀쩡한" 경우 기능 후퇴라는 지적(스펙 Always가 명시적으로 그렇게 결정한 축이다 — 재연결 시 flush되므로 지연일 뿐 유실이 아니고, 스코프 권위는 intent에 있다) · 관리자가 방을 지우면 재조인이 영구 CHANNEL_ERROR가 되어 큐가 조용히 소실된다는 지적(방이 사라지면 그 화면 자체에 접근할 수 없고, 이번에 넣은 "못 보낸 N건" 표시가 그 상황의 신호도 함께 준다) · `role="status"` 라이브 리전이 텍스트와 동시에 마운트돼 스크린리더가 안 읽는다는 지적(이 파일의 기존 모든 에러 안내와 동일한 패턴이라 이 스토리가 만든 문제가 아니고, 특정 스크린리더 동작 주장이 실측되지 않았다) · replay `limit:25`의 절단 방향(최신순/오래된순)이 미확인이라는 지적(커서 재조회가 항상 도는 백스톱이라 데이터 축에서 무해하고, 서버 동작 추측을 코드에 반영할 근거가 없다) · CLOSED 이후 `realtimeError`가 영영 안 지워진다는 지적(실측상 CLOSED는 그 채널의 종착 상태 — 1차 패스에서 이미 같은 근거로 기각) · 방 전환 시 큐가 조용히 사라진다는 지적(인메모리 비영속은 스펙 Never가 명시적으로 택한 절충이고 새로고침과 같은 성질이다) · 오프라인 경로의 `crypto.randomUUID()`에 try/catch가 없다는 지적(비보안 컨텍스트에서만 던지는데 이 앱은 https/localhost 전용 — A2 "불가능한 시나리오용 예외처리 금지") · 재연결 상태기계 전체를 순수 함수로 뽑아 컴포넌트 수준 테스트를 만들라는 지적(에픽 레벨에서 Story 12.6 수동 2브라우저 검증으로 닫기로 이미 정해진 성공 지표이고, 이번 패스에서 오케스트레이터가 라이브로 직접 재현했다) · `roomTopicContract` 정규식이 프로퍼티 순서에 취약하니 config를 export해 값으로 단언하자는 지적(동작하는 코드의 구조 변경이라 이 스토리 범위 밖 — A3).

### 2026-07-29 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 3, low 3)
- defer: 0
- reject: 7
- addressed_findings:
  - `medium` `patch` **오프라인 큐 flush가 스냅샷 기준으로 pendingQueue 전체를 덮어써, flush 도중 온라인 경로로 새로 추가된 pending 항목이 화면에서 잠깐 사라졌다**(실제 전송은 완료돼 `messages`엔 반영되지만 pending 버블만 깜빡이며 사라지는 혼란, adversarial+edge-case-hunter 교차 지적). `flushQueue()` 완료 시점에 스냅샷이 아니라 "지금" `pendingQueueRef.current`에서 성공한 id만 걷어내도록 수정(`sentIds` 필터).
  - `medium` `patch` `flushQueue()`·`gapFillFromCursor()`가 try/catch 없이 `void`로 호출돼, `sendMessage`(이미 이 파일의 `handleSubmit`이 던질 수 있다고 보고 감싸는 함수)가 예외를 던지면 unhandled rejection이 되고 그 배치의 pending 버블 전부가 "전송 중…"으로 영구 박제됐다(fail-loud 원칙 위반, adversarial+edge-case-hunter 교차 지적). 두 함수 모두 try/catch로 감싸 로그 + 가시적 신호(gapFill은 기존 `loadError` 재사용)를 남기도록 수정.
  - `medium` `patch` 오프라인 큐잉 경로(`disconnectedRef.current` 분기)가 `sendMessage`의 길이 검증(`CHAT.MESSAGE_MAX_LENGTH`)을 거치지 않아, 붙여넣기로 2000자 초과 메시지가 큐에 들어가면 재연결마다 계속 실패해 그 뒤의 모든 메시지까지 영구히 막았다(edge-case-hunter 지적, 구체적 재현 경로 포함). 온라인 경로와 동일한 길이 검증을 큐잉 직전에 수행해 즉시 에러 안내 + 입력 복원하도록 수정.
  - `low` `patch` 연결이 짧은 간격으로 여러 번 끊겼다 붙으면 `flushQueue()`가 동시에 두 번 돌 수 있었다(DB 멱등키가 실제 중복 행은 막아주지만 화면 상태가 꼬일 여지, adversarial+edge-case-hunter 교차 지적). `isFlushing` 가드 추가로 중복 실행 방지.
  - `low` `patch` `roomTopicContract.test.ts`의 정정 주석이 "private가 config의 첫 프로퍼티여야 한다"고 실제보다 강하게 주장했다 — 정규식을 직접 실행해 확인한 결과 그 순서를 강제하지 않는다(adversarial 지적, 실측 검증됨). 주석을 실제 정규식이 보장하는 바(중첩 객체가 앞서지 않으면 됨)로 정정.
  - `low` `patch` `REPLAY_SINCE_WINDOW_MS`가 채널 생성 시점(마운트)에 한 번만 계산되고 재조인마다 재사용돼, "재연결 시점 기준 72시간"이 아니라 탭이 오래 떠 있을수록 조용히 과거로 밀린다는 사실이 주석에 없었다(adversarial 지적, 커서 재조회 백스톱 덕에 현재는 무해함을 스스로 인정). 그 사실과 무해한 이유를 명시하는 주석 추가.
- 기각 7건 — 오프라인 경로에 `sending` 가드가 없어 동일 문구를 빠르게 두 번 제출하면 서로 다른 멱등키로 중복 저장될 수 있다는 지적(온라인 경로도 동일하게 무방비이고, 제출 즉시 입력이 비워지므로 "똑같은 문구를 일부러 다시 타이핑해 재전송"에 가까운 저확률 시나리오 — 온라인과 다르게 취급할 근거 없음) · CLOSED 이후 SUBSCRIBED가 와서 옛 경고 문구가 안 지워질 수 있다는 지적(Design Notes 실측: CLOSED는 그 채널 인스턴스를 소켓에서 완전히 떼어내는 종착 상태라 이후 어떤 status 콜백도 그 채널에서 다시 안 온다 — 시나리오 자체가 도달 불가) · 재연결 초록 배너가 갭보정 성공 여부와 무관하게 뜬다는 지적(두 안내가 실제로 모순되지 않는다 — "소켓은 재연결됨"과 "이번 갭보정 조회는 실패함"은 서로 다른 축이고, 이 결합까지 손보는 건 비용 대비 실익이 낮다) · 대장 `#202`의 정리 SQL을 스크립트로 만들자는 제안(수동 실시간 검증 시에만 필요한 드문 절차라 이번 스토리 범위 밖의 툴링 개선, A2) · 배너·큐·갭보정 배선(연결 상태 판단 분기, `flushQueue` 래퍼, `gapFillFromCursor`+커서 미러링) 3곳에 컴포넌트 수준 자동 테스트가 없다는 지적 3건(verification-gap) — 에픽 레벨에서 이미 확정된 결정(`Story 12.6`이 두 브라우저 수동 검증으로 이 성공 지표를 닫기로 함, `epics-increment-2026-07-12.md`·`epic-12-context.md`에 명시)이 스코프 권위이며, 이 리뷰 패스 자체에서 오케스트레이터가 실제 브라우저로 네트워크를 끊어 세 갈래(끊김 배너+오프라인 큐잉, 재연결 시 큐 flush, 갭보정 병합) 전부를 라이브로 실측 확인했다(아래 Verification 참조) — 그래서 "검증 안 됨"이 아니라 "자동 회귀 테스트는 없지만 이번 실행에서 실측 검증됨"으로 닫는다.

## Design Notes

**왜 새 재구독/소켓 로직이 필요 없는가 (실측 — `@supabase/realtime-js` 2.108.2 소스 직접 확인):**
네트워크가 끊기면 채널 상태는 `CHANNEL_ERROR`/`TIMED_OUT`(= `errored`)로 오지 `CLOSED`가 아니다. `CLOSED`는 명시적 `leave()`(방 전환·언마운트)에서만 발생한다. `errored` 채널은 각 채널이 생성 시점에 등록해둔 자기 자신의 `socket.onOpen()` 리스너를 통해 소켓이 재연결될 때마다 자동으로 `rejoin()`을 호출한다 — 소켓 자체의 재연결(끊김/heartbeat 타임아웃 감지, 지수 백오프)도 라이브러리가 전담한다. 즉 앱 코드가 지금 갖고 있는 **단 하나의 `channel.subscribe(callback)` 호출**이 최초 연결부터 끊김·자동 재조인·재연결까지 전체 라이프사이클의 상태를 계속 콜백으로 전달한다 — 재연결을 감지해 수동으로 다시 구독하거나 채널/소켓을 새로 만드는 코드는 불필요하며, 오히려 라이브러리의 자동 재조인과 중복돼 혼란을 더한다. `CLOSED`는 이 실측 결과 네트워크 드롭 시나리오에 사실상 도달하지 않는 분기이므로, 12.3이 이미 넣어둔 처리(회색 경고 + `cancelled` 가드)를 그대로 두되 이 스토리의 재연결 배너 로직이 그 분기에 새 의미를 부여할 필요는 없다.

**Broadcast Replay가 어떻게 동작하는가:** 채널 생성 시 `config: { private: true, broadcast: { replay: true } }`를 주면, Supabase Realtime 서버가 `realtime.broadcast_changes()`(0023)로 이미 영속되고 있는 `realtime.messages`의 최근 이력(플랫폼 기본 한도 ≤25건/72h)을 구독 시점에 같은 `broadcast`/`INSERT` 이벤트로 재생(replay)한다 — 별도의 소비 코드가 필요 없다(기존 `channel.on('broadcast', { event: 'INSERT' }, ...)` 핸들러가 그대로 받는다). 이 config는 재조인 시에도 그대로 재사용되므로(채널 객체에 저장된 join params), 재연결마다 다시 설정할 필요가 없다 — 최초 채널 생성 시 한 번만 추가한다. 다만 한도를 넘는 gap은 replay가 못 채우므로, 항상 커서 재조회를 병행한다(둘 다 실행해도 `dedupeById`가 겹치는 결과를 안전하게 접는다).

**큐 항목이 실패하면 왜 `reuseFailedKey`(60초 창)가 아니라 항목 자체의 고정 키를 쓰는가:** `reuseFailedKey`는 "이번 제출이 방금 실패한 그 제출의 재시도인가"를 **본문 일치 + 시간창**으로 추측하는 휴리스틱이다(사용자가 직접 재전송 버튼을 누르는 온라인 경로 전용). 큐 flush는 그 추측이 필요 없다 — 어떤 항목을 재시도하는지 큐 자체가 이미 알고 있으므로, 큐잉 시점에 만든 `client_message_id`를 그대로 재사용하면 된다(더 단순하고 더 정확하다, A2).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 warnings.
- `cd web && npx tsc --noEmit` -- expected: 0 errors.
- `cd web && npm test` -- expected: 기존 + 신규 vitest 전부 green.
- `cd web && npx playwright test viewport-audit write-flows` -- expected: 전부 green(회귀 없음).

**Manual checks (if no CLI):**
- 로컬 Supabase 스택에서 buyer/seller 두 세션으로 실제 연결을 끊었다 복구해(예: 로컬 Realtime 컨테이너 재시작, 또는 웹소켓 강제 종료 스크립트) 배너 전환(회색→초록→소멸)과 입력 잠금 없음을 실측 확인한다.
- 끊긴 동안 상대 세션에서 메시지를 보내고 재연결 후 유실 없이 병합되는지, 그리고 끊긴 동안 자기 세션에서 여러 건을 큐잉해 재연결 시 순서대로 전송되고 중복 행이 없는지(psql로 count 확인) 실측한다.

## Auto Run Result

### 2026-07-29 후속 리뷰 패스 (3차)

**요약:** `status: done`이던 이 스펙에 후속 코드리뷰를 한 패스 더 돌렸다(adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 레이어 병렬). 이번 패스의 지적은 **대부분 2차 패스의 패치가 만든 2차 효과**였다 — R3(미전송 안내)가 하필 제출마다 지워지는 칸을 골랐고, R5(끊김 중 입력 잠금 해제)가 "끊긴 채 타이핑"을 정상 경로로 만들면서 실패 시 입력 복원이 사용자 글을 덮게 됐다. 함께, **2차 패스가 새로 만든 계약 검사 자체가 false-green**이라는 사실이 실측으로 드러났다(replay 검사가 채널 호출에 앵커되지 않아 config 밖으로 빼도 통과). intent_gap·bad_spec은 0건 — 구현이 스펙을 벗어난 곳은 없다.

**Files changed** (커밋 아래 참조):
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 미전송 안내를 전용 상태 `queueStuckNotice`로 분리 + 문구를 실제 재시도 트리거대로 정정, 실패 시 입력 복원을 함수형 가드로 전환, 갭보정이 자기가 세운 안내만 거두도록 출처 추적, flush가 온라인 in-flight 항목을 건너뛰도록 소유권 ref 추가, replay 상수 주석의 출처 구분 정정.
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`(수정) — `private:true` 정규식을 `[^}{]*`로 조여 중첩 false-green 차단, replay 검사를 채널 생성 호출에 앵커, **신설 3건**(재연결 갭보정 커서 경로 배선 · 끊김 중 비차단 조건식 3개 · 미전송 안내의 칸 분리).
- `docs/conventions.md`(수정) — §12.5에 이번에 확정된 계약 6건 추가(안내 칸 분리 · 문구 정확성 · pending 소유권 · 입력 복원 조건 · replay `since`의 마운트 고정 위험 · 큐 비영속화의 **정정된** 근거), "≤25/72h가 플랫폼 기본값" 잔여 표현 정정, 두 갭보정 경로의 보호 강도 비대칭 정정.
- `docs/tech-debt.md`(수정) — **신규 등재 5건**: `#203`(bmad-loop `DW-6` 이관) · `#204`(타임아웃 부재로 flush가 영구 정지 + 끊김 감지 25~35초 지연 중 입력 잠금) · `#205`(오프라인 길이 가드의 재현 경로 미확인) · `#206`(큐가 막히면 수동 재시도 경로가 없다) · `#207`(오프라인 큐잉이 라이브러리 한 버전의 소스 독해 위에 있는데 의존성은 캐럿). **기존 항목은 상태·우선순위·트리거·본문 모두 무수정**이다.

**Verification 수행 (오케스트레이터가 직접 실행, 서브에이전트 보고에 의존하지 않음):**
- `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(**270 passed**, 이전 268 + 신규 2... 최종 신설 3건 반영 후 27 files/270) · `npx playwright test viewport-audit write-flows`(23 passed, 10 skipped — 회귀 없음).
- **신규·강화한 계약 검사 5건 전부 "만들었다"가 아니라 "잡는다"로 확인**(B4, 각각 일부러 깨서 red → 원복 green): ① `void gapFillFromCursor();` 삭제 → red, ② `disabled={(sending && !isDisconnected) || loading}`를 12.3 형태로 되돌림 → red, ③ replay config를 미사용 지역 상수로 이동 → red(앵커 전에는 green이었다), ④ `private: true`를 중첩 객체 안으로 이동 → red(조이기 전에는 green이었다), ⑤ 미전송 안내를 `setError`로 되돌림 → red.
- **실제 브라우저 라이브 재현**(Playwright + 로컬 dev 서버 + 로컬 Supabase 스택, buyer@test.com 시드 채팅방) — 이번 패스의 medium 수정을 사람이 보는 층에서 확인: `setOffline(true)`로 실제 네트워크를 끊어 CHANNEL_ERROR 유발 → 끊김 배너 + 입력창 `disabled=false` 확인 → 끊긴 채 2건 큐잉 확인 → `chat_messages` POST를 500으로 가로챈 뒤 복구해 재연결 → flush 전량 실패 → **"메시지 2건을 아직 보내지 못했습니다. 연결이 다시 끊겼다 회복될 때 재시도하며, 그때까지는 전송되지 않습니다." 노출 확인** → 그 상태에서 **메시지를 한 번 더 제출해도 안내가 그대로 남아 있음을 확인**(핵심 회귀). 옛 코드(`setError` 칸)로 되돌리면 이 재현이 **red**가 되는 것까지 확인한 뒤 원복했다.
- 재현에 쓴 임시 E2E 파일은 삭제했다(스펙 Never — 이 흐름의 새 자동 E2E를 만들지 않는다). 재현으로 만든 `chat_messages` 행은 **0건**(POST를 전부 가로채 500으로 돌려줬으므로 DB에 도달하지 않았다), `realtime.messages` 잔여 방송도 0건임을 컨테이너 psql로 확인했다.
- **라이브 재현으로 덮지 못한 축**(정직하게 남김): 입력 복원 함수형 가드(2번째 medium)·갭보정 안내 출처 추적·flush 소유권 ref는 타이밍을 인위적으로 만들기 어려워 코드 대조와 계약 검사로만 확인했고, 브라우저에서 재현하지는 않았다.
- **DW 처리 결과**: `deferred-work.md`(동결)에 `DW-1`~`DW-6`이 `status: open`으로 있다. `DW-1`~`DW-5`는 각각 대장 `#148`·`#149`·`#164`·`#184`·`#192`로 **이미 이관 완료**. **`DW-6`(12-3)은 미이관 상태였으므로 이번에 대장 `#203`으로 신규 이관**했다. 동결 파일 자체는 무수정이다.
  - `DW-1: 이미 #148에 있음` · `DW-2: 이미 #149에 있음` · `DW-3: 이미 #164에 있음` · `DW-4: 이미 #184에 있음` · `DW-5: 이미 #192에 있음` · `DW-6: 이관함 → #203`

**Follow-up review recommendation:** `true`. 이번 패스 패치는 high 0·medium 2·low 9이고 규칙은 "high가 하나라도 있거나 `3×medium + 1×low ≥ 5`" — 점수 3×2+1×9 = **15**.

**Residual risks (3차 패스 기준 갱신):**
- **이 파일의 어떤 네트워크 호출에도 타임아웃이 없다**(대장 `#204`). flush 영구 정지와 "끊김 감지 전 25~35초 입력 잠금"이 같은 뿌리이며, 둘 다 이번 패스가 고치지 않았다 — 새 타임아웃 메커니즘 도입은 이 패스의 층이 아니다.
- 큐가 막히면 사용자가 할 수 있는 일이 없다(대장 `#206`). 이번 패스는 **거짓 약속을 제거**했을 뿐 재시도 경로를 만들지 않았다 — 인텐트가 명시적으로 고른 축이라 리뷰가 임의로 넓힐 수 없다.
- 배너·큐·갭보정의 **배선 자체**를 지키는 자동 회귀 테스트는 여전히 소스 스캔 층이다(런타임 동작이 아니다). 이 레포 vitest는 `environment: 'node'`라 RTL 상호작용 테스트를 쓸 수 없고, 새 자동 E2E는 스펙 Never가 금지한다 — 이번 패스가 늘린 것은 "그 배선이 코드에 남아 있는가"까지이고, "실제로 그렇게 동작하는가"는 Story 12.6의 수동 2브라우저 검증 몫으로 남는다.
- 대장 `#195`·`#196`·`#197`(원격 Realtime/Broadcast 활성화 전제)·`#201`·`#202` 모두 열린 상태 그대로다 — 이번 패스는 이들 중 어느 것도 수정하지 않았다.

**잔여 아티팩트:** 이 스펙 파일의 프론트매터·로그 편집분과 `sprint-status.yaml`은 커밋에 포함되지 않았다 — 스펙을 커밋하면 HEAD가 또 움직여 방금 적은 `final_revision`이 어긋나고(1·2차와 동일 이유), `sprint-status.yaml`은 오케스트레이터 소유다.

---

### 2026-07-29 후속 리뷰 패스 (2차)

**요약:** `status: done`이던 이 스펙에 대해 후속 코드리뷰 1패스를 더 돌렸다(adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 레이어 병렬). 1차 패스가 놓친 **실제 중복 저장 경로 1건(FR41 멱등 보호 우회)**과 **AC 위반 1건(끊김 중 입력 잠금)**을 포함해 medium 5·low 4를 패치했다. intent_gap·bad_spec은 0건 — 구현이 스펙을 벗어난 곳은 없고, 지적은 전부 "스펙대로 만든 코드의 빈 구석"이었다.

**Files changed** (커밋 `11c5d49`):
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 오프라인 큐잉의 멱등키 선택을 온라인과 동일 규칙으로 통일(R2), 연타 가드를 온라인 전용으로 좁히고 끊김 중 입력창·전송 버튼 잠금 해제(R5), flush 미전송 건수 화면 표시(R3), flush 중복 가드를 재실행 예약으로 변경(R4), 갭보정 성공 시 실패 안내 해제(R1).
- `web/src/lib/messages.ts`(수정) — `flushMessageQueue`가 `sendFn` 예외에도 이미 보낸 행을 잃지 않도록 try/catch(R6).
- `web/src/lib/__tests__/messages.test.ts`(수정) — R6 경로의 단위 테스트 1건 신설.
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`(수정) — `broadcast.replay` 존재를 지키는 계약 단언 신설(R7).
- `docs/conventions.md`(수정) — §12.5에 이번에 확정된 4개 계약 추가(제출 시점 키 선택 규칙 · 끊김 중 잠금 금지 범위 · 미전송 건수 가시화 · flush 재요청은 미루기), replay `since`/`limit`의 출처 구분 정정.
- `docs/tech-debt.md`(수정) — `#202`의 사실관계 정정(관리자 삭제 경로가 실재함, 결론은 유지) · `#201`의 "플랫폼 기본값" 표현 정정. **기존 항목의 상태·우선순위·트리거는 건드리지 않았고, 이번 패스에서 defer로 분류된 신규 항목은 0건이다.**

**Verification 수행 (오케스트레이터가 직접 실행, 서브에이전트 보고에 의존하지 않음):**
- `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(**268 passed**, 이전 266 + 신규 2) · `npx playwright test viewport-audit write-flows`(23 passed, 10 skipped — 회귀 없음).
- **신규 검사 2건은 "만들었다"가 아니라 "잡는다"로 확인**(B4): (1) 채널 config에서 `broadcast.replay`를 실제로 제거해 계약 테스트가 red가 되는 것을 확인 후 복구 → green, (2) `flushMessageQueue`의 try/catch를 제거해 새 테스트가 red가 되는 것을 확인 후 복구 → green.
- **실제 브라우저 라이브 재현**(Playwright + 로컬 dev 서버 + 로컬 Supabase 스택, buyer@test.com 시드 채팅방): `setOffline(true)`로 실제 네트워크를 끊어 CHANNEL_ERROR(heartbeat timeout) 유발 → 배너 문구·비차단 확인 → 끊긴 채 2건 큐잉(즉시 pending, DB 미반영 확인) → psql로 판매자 명의 메시지를 INSERT해 "끊긴 동안 상대가 보낸 메시지" 시뮬레이션 → 복구 → 초록 배너 전환 후 **~2.8초 뒤 자동 소멸** 확인 → 갭보정 메시지가 올바른 시간순 위치에 병합 확인 → 큐 2건이 **순서대로 43ms 간격으로** 실제 행이 되고 **중복 0건**임을 psql로 확인.
- **이번에 바꾼 축 3개를 각각 따로 재현**: (R5) 전송 POST를 응답 없이 붙잡아 `sending=true`를 고정한 상태에서 연결을 끊어 → 입력창·버튼이 `disabled=true`에서 `false`로 풀리고 그 상태의 제출이 실제로 큐잉되는 것 확인(이전 코드에선 잠긴 채였다). (R3) POST를 실패시켜 재연결 → "메시지 1건을 아직 보내지 못했습니다…"가 화면에 뜨는 것 확인(이전엔 console만). (R1) 갭보정 GET을 실패시켜 안내를 띄운 뒤 정상화해 다시 재연결 → 안내가 해제되는 것 확인(이전엔 방 전환 전까지 박제).
- **라이브 재현으로 덮지 못한 축**(정직하게 남김): R2(오프라인 경로의 실패 키 재사용)·R4(flush 재실행 예약)는 타이밍을 인위적으로 만들기 어려워 코드 대조와 단위 테스트로만 확인했고, 브라우저에서 재현하지는 않았다.
- 검증으로 만든 `chat_messages` 3행과 그에 대응하는 `realtime.messages` 잔여 방송 3건을 모두 삭제해 로컬 DB를 원상복구했다(잔여 0건 확인, `#202`가 문서화한 정리 SQL 사용). 시드 방은 원래의 4개 메시지 상태로 돌아갔다.
- **DW 처리 결과**: `deferred-work.md`(동결)에 `### DW-` 형식의 신규 `status: open` 항목 없음 — 이번 패스에서 새로 생긴 DW 항목도 없다(defer 0건). 동결 파일 무수정.

**Follow-up review recommendation:** `true`. 이번 패스 패치는 high 0·medium 5·low 4이고 규칙은 "high가 하나라도 있거나 `3×medium + 1×low ≥ 5`" — 점수 3×5+1×4 = **19**.

**Residual risks (2차 패스 기준 갱신):**
- 재연결·오프라인 큐잉·갭보정 전체를 지키는 **자동 회귀 테스트는 여전히 없다**(의도적 — 에픽 레벨에서 Story 12.6 수동 2브라우저 검증으로 닫기로 확정). 이번 패스가 순수 함수(`flushMessageQueue`)와 채널 config 계약 두 축을 vitest로 더 고정했지만, 배너·큐·갭보정의 **배선 자체**는 사람이 돌려봐야 확인된다.
- 연결이 아주 짧은 간격으로 반복 flapping하는 극단 상황은 `isFlushing` + 재실행 예약으로 완화했으나 라이브 검증에선 재현하지 않았다.
- 대장 `#195`·`#196`·`#197`(원격 Realtime/Broadcast 활성화 전제)·`#201`·`#202` 모두 열린 상태 그대로다 — 이번 패스는 `#201`·`#202`의 **서술만** 사실에 맞게 고쳤고 상태는 바꾸지 않았다.

**잔여 아티팩트:** 이 스펙 파일의 프론트매터·로그 편집분과 `sprint-status.yaml`은 커밋에 포함되지 않았다 — 스펙을 커밋하면 HEAD가 또 움직여 방금 적은 `final_revision`이 어긋나고(12.3·12.4 1차와 동일 이유), `sprint-status.yaml`은 오케스트레이터 소유다.

---

### 2026-07-29 최초 구현 + 1차 리뷰 패스

**요약:** `ChatRoomMessages.tsx`에 재연결 배너(회색 "끊김" → 초록 "다시 연결됐어요" → 3초 후 자동 소멸), 오프라인 큐잉(끊긴 동안 제출한 메시지는 네트워크 호출 없이 로컬 큐에 순서대로 쌓고 즉시 pending 버블로 표시), 갭보정(재연결 시 Broadcast Replay + 커서 재조회 `fetchMessages(gte)` 병행)을 배선했다. `web/src/lib/messages.ts`에 순수 함수 `flushMessageQueue`(순차 flush, 실패 시 그 항목부터 뒤 전부를 남기고 멈춤)를 신설해 vitest로 검증하고, 컴포넌트는 이를 감싸 실제 `sendMessage`를 넘긴다. Broadcast Replay는 스펙의 Design Notes가 적은 `{ replay: true }`(불리언)가 실제 라이브러리 타입과 달라(`{ since, limit }` 객체 필요) 구현 단계에서 정정했다(플랫폼 기본 한도 25건/72h를 그대로 요청). 코드리뷰 1패스에서 나온 medium 3건·low 3건 패치를 전부 적용했다(아래 Review findings breakdown).

**Files changed:**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 재연결 배너 상태 전이(CHANNEL_ERROR/TIMED_OUT ↔ SUBSCRIBED), `pending`을 단일 값에서 큐(배열)로 확장, 오프라인 큐잉+길이 검증(코드리뷰 patch), 재연결 시 큐 flush(순차·스냅샷이 아닌 라이브 큐 기준 필터링, 코드리뷰 patch)+갭보정(커서 재조회) 동시 실행, `isFlushing` 중복 실행 가드(코드리뷰 patch), flush/갭보정 try/catch(코드리뷰 patch), 채널 config에 `broadcast.replay` 추가.
- `web/src/lib/messages.ts`(수정) — `QueuedMessage` 타입 + 순수 함수 `flushMessageQueue`(순서 보존 flush 알고리즘) 신설.
- `web/src/lib/__tests__/messages.test.ts`(수정) — `flushMessageQueue` 단위 테스트 3건(전부 성공/중간 실패 시 순서 보존/빈 큐).
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`(수정) — `broadcast.replay` 추가에 맞춰 정규식 완화 + 주석 정정(코드리뷰 patch, 실제 보장 범위로 정확화).
- `docs/conventions.md`(수정) — §12.5 신설(재연결·오프라인 큐잉·갭보정 계약, CLOSED 실측 사실, replay가 삭제된 행도 되살릴 수 있다는 로컬 함정 + 정리 SQL). §12.4에 pending 큐 배열화에 따른 소급 정정 각주.
- `docs/tech-debt.md`(수정) — 신규 등재 2건: `#201`(replay 25건/72h 한도가 이 데모 규모에서 사실상 미도달이라는 판단 근거) · `#202`(replay가 삭제된 chat_messages 행의 방송을 되살린 실측 결함, defer — 로컬 개발 환경 함정, 정리 SQL로 해소).

**Review findings breakdown** (adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 레이어 병렬 실행, 오케스트레이터가 diff·코드·라이브러리 소스·실제 실행으로 직접 대조해 판정):
- patch 6건(medium 3·low 3) — 핵심 3건: (1) 오프라인 큐 flush가 스냅샷으로 pendingQueue 전체를 덮어써 flush 도중 온라인 경로로 추가된 새 메시지의 pending 버블이 화면에서 잠깐 사라짐(adversarial+edge-case-hunter 교차 지적, 실제 데이터 유실은 아니고 UI 깜빡임) — 라이브 큐에서 성공 id만 필터링하도록 수정. (2) `flushQueue`/`gapFillFromCursor`에 예외 처리가 없어 `sendMessage`가 던지면 pending이 무기한 박제(fail-loud 위반) — try/catch 추가. (3) 오프라인 큐잉이 길이 검증을 안 거쳐 2000자 초과 메시지가 큐에 들어가면 재연결마다 실패를 반복하며 뒤 메시지까지 영구 정체 — 큐잉 전 동일 검증 추가.
- reject 7건 — 오프라인 중복 제출(온라인도 동일하게 무방비, 저확률) · CLOSED 이후 SUBSCRIBED 도달 가능성(실측상 CLOSED는 그 채널의 종착 상태라 불가능) · 재연결 배너와 갭보정 실패 안내의 "모순"(실제로는 서로 다른 축이라 모순 아님) · 대장 `#202` 정리 SQL의 스크립트화 제안(스코프 밖 툴링) · 컴포넌트 수준 자동 테스트 부재 3건(verification-gap) — 에픽 레벨 결정(Story 12.6 수동 검증)이 스코프 권위이고, 이번 리뷰 패스에서 오케스트레이터가 직접 라이브 검증을 수행해 닫음(아래 참조).
- intent_gap·bad_spec 0건 — intent-alignment auditor는 diff가 스펙의 전체 읽기(R3: 배너+오프라인 큐잉+이중 경로 갭보정, 수동 재구독 없음)를 코드 수준에서 충실히 구현했다고 확인했다. 유일하게 짚은 것은 "diff 자체엔 그 수동 검증이 실제로 수행됐다는 증거가 없다"는 점 — 이를 받아 오케스트레이터가 아래처럼 직접 재현했다.

**Verification 수행 (오케스트레이터가 직접 재실행, 서브에이전트 보고에 의존하지 않음):**
- 구현 직후 및 코드리뷰 패치 적용 후 각각: `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(266 passed) · `npx playwright test viewport-audit write-flows`(23 passed, 10 skipped, 회귀 없음) 전부 오케스트레이터가 직접 재실행해 확인.
- **재연결 배너·오프라인 큐잉·갭보정 전체 흐름을 오케스트레이터가 실제 브라우저(Playwright, 로컬 dev 서버 + 로컬 Supabase 스택)로 직접 재현**: buyer@test.com으로 로그인해 시드 채팅방에 진입 → `page.context().setOffline(true)`로 실제 네트워크를 끊어 `CHANNEL_ERROR`(heartbeat timeout) 발생 확인 → 배너 텍스트가 스펙 문구와 정확히 일치("연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요.") + 입력창 `disabled=false` 확인(PASS) → 끊긴 채로 메시지 2건을 제출해 즉시 pending 버블로 표시되고 DB엔 반영되지 않음을 확인(PASS, 네트워크 호출 없음) → psql로 다른 참가자(판매자) 명의 메시지를 직접 INSERT해 "끊긴 동안 상대가 보낸 메시지"를 시뮬레이션 → `setOffline(false)`로 복구 → 배너가 "다시 연결됐어요"(초록)로 전환된 뒤 정확히 ~3초 후 사라짐(PASS) → 그 사이 갭보정 메시지가 올바른 시간순 위치에 병합됨을 확인(PASS) → 큐에 있던 2건이 순서대로(38ms 간격, 순차 전송 확인) 실제 `chat_messages` 행으로 flush돼 중복 없이 정확히 1행씩 저장됨을 psql로 확인(PASS). 테스트로 만든 4개 행과 그 `realtime.messages` 잔여 방송(대장 `#202`가 문서화한 정리 SQL)을 모두 삭제해 로컬 DB를 원상복구했다(잔여 0건 확인).
- 이 라이브 재현이 I/O & Edge-Case Matrix 4행 전부(연결 끊김+비차단, 끊긴 동안 전송(큐잉), 재연결+큐 flush, 갭보정)를 실측으로 커버한다 — Matrix Test Audit을 자동 테스트가 아니라 이 실측으로 충족한다(에픽 레벨이 이미 이 성공 지표를 자동 E2E가 아닌 수동 검증으로 정해뒀으므로, CLAUDE.md B4 "재보기 전엔 선언하지 않는다"에 따라 선언 전에 실제로 돌려 확인한 것).
- **DW 처리 결과** (활성화 시 로드한 persistent fact 지시사항): `deferred-work.md`(동결)를 확인 — `status: open`인 `DW-1`~`DW-5` 모두 이전 스토리(12-1~12-3)에서 이미 `docs/tech-debt.md`로 이관 완료된 상태 그대로다. 이번 스토리에서 새로 생긴 DW 항목 없음, 동결 파일 무수정.

**Follow-up review recommendation:** `true`. 이번 패스 패치 6건은 high 0·medium 3·low 3이고, 규칙은 "high가 하나라도 있거나 `3×medium + 1×low ≥ 5`"다 — 점수 3×3+1×3 = **12**라 `true`.

**Residual risks:**
- 대장 `#195`·`#196`·`#197`(원격 Realtime/Broadcast 활성화 전제) — 여전히 열려 있다, 변동 없음.
- 대장 `#201`(replay 25건/72h 한도가 이 데모 규모에서 미도달) · `#202`(replay가 삭제된 행을 되살릴 수 있음, 로컬 개발 함정, defer) — 이번 스토리가 새로 등재.
- 재연결·오프라인 큐잉·갭보정 전체를 지키는 **자동 회귀 테스트**는 여전히 없다(의도적, Story 12.6 수동 검증 + 순수 함수 `flushMessageQueue`만 vitest 커버). 이번 실행에서 오케스트레이터가 라이브로 1회 재현해 정확성을 확인했으나, 향후 회귀를 상시로 잡아주는 장치는 아니다.
- 연결이 아주 짧은 간격으로 여러 번 반복 flapping하는 극단적 상황은 `isFlushing` 가드로 완화했으나 라이브 검증에선 재현하지 않았다(단발성 끊김→재연결만 실측).

**잔여 아티팩트:** 이 스펙 파일 자체의 `status: done`·`final_revision` 프론트매터 편집분은 커밋에 포함되지 않았다 — 커밋하면 HEAD가 또 움직여 방금 적은 해시가 어긋난다(12.3과 동일 이유). `git status --porcelain`에 이 파일만 수정 상태로 남는 것은 의도된 것이다.
