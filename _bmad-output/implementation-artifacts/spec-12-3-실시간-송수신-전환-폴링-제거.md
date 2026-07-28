---
title: '12.3 실시간 송수신 전환 (폴링 제거)'
type: 'feature'
created: '2026-07-29'
status: 'done'
baseline_revision: 'e7823fea203cf5af6c8fbebbe7b33b96b04680f3'
final_revision: '50513ee9942c715ab55898acfbd7cbba9ef02ae0'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 채팅방(`ChatRoomMessages.tsx`)은 아직 3초 폴링뿐이라 판매자가 문의를 실시간으로 못 받는다. 12.1의 멱등키(0022)·12.2의 Broadcast+RLS(0023) DB 토대는 이미 있지만 웹 클라이언트가 아직 하나도 안 쓴다 — 구독 코드가 없고 전송도 `client_message_id`를 안 채운다.

**Approach:** `ChatRoomMessages.tsx`의 `setInterval` 폴링을 제거하고 `chat:room:{roomId}` private 채널 실시간 구독으로 교체한다(초기 1회 전체 로드는 유지). 전송은 `crypto.randomUUID()` 멱등키를 실어 낙관적 pending 버블로 보이다가 서버 확정 시 실제 행으로 교체한다. Flutter 앱은 이 스토리 범위 밖(Epic 16 Story 16.4).

## Boundaries & Constraints

**Always:**
- 구독 토픽은 `` `chat:room:${roomId}` `` — 0023의 트리거·RLS 리터럴과 문자 그대로 동일해야 한다(한쪽만 다르면 조용히 깨짐).
- `supabase.channel(topic, { config: { private: true } })`로 구독하고, 구독 전에 현재 세션 access token으로 `supabase.realtime.setAuth(token)`을 호출한다(0023 Design Notes의 공식 Broadcast Authorization 패턴). `onAuthStateChange`(토큰 갱신)마다 다시 `setAuth`한다.
- 방송 payload의 `payload.record`(INSERT 신규 행)를 파싱해 기존 `mergeIncoming`(dedupeById + `created_at,id` 정렬)에 그대로 합류시킨다 — 도착 순서가 아니라 정렬 결과로 렌더한다.
- 방 진입 시 1회 전체 `fetchMessages` 로드는 유지한다 — 구독 이전 과거 메시지를 보여줄 유일한 경로. 그 이후 주기 재조회는 없다.
- `sendMessage`가 INSERT에 `client_message_id: crypto.randomUUID()`를 실어 보낸다. 전송 시작 시 그 키로 pending 버블 1개를 즉시 보여주고(`sending` 가드가 동시 다건을 막으므로 배열 불필요), 그 키를 단 실제 행이 "자기 응답" 또는 "브로드캐스트 에코" 중 먼저 도착하는 쪽으로 확정되면 pending을 지우고 그 행으로 교체한다(UX-DR15).
- INSERT가 `chat_messages_room_client_message_unique` 유니크 위반(`23505`)으로 실패하면(같은 키의 재전송) 에러로 보여주지 않고 `(room_id, client_message_id)`로 기존 행을 조회해 그 행으로 pending을 확정한다(멱등, 대장 `#186`).
- 채팅 입력창에 `#84`와 동일한 `size={1}` + `min-w-0`을 적용해 390px 가로 오버플로를 없앤다(대장 `#169` 이행). `viewport-audit.spec.ts`에 채팅방 화면 케이스를 추가한다.
- `docs/conventions.md`에 신설 절로 구독 토픽 형식·private+setAuth 타이밍·payload 파싱 규칙을 문서화한다 — Epic 16.4(Flutter)가 같은 계약을 따라야 한다.

**Block If:** (이 스토리 실행 범위 안에서 사람 판단이 필요한 신규 결정 없음 — 원격 Realtime 활성화 여부 확인은 이미 대장 `#195`·`#196`이 "배포 직전" 항목으로 못박아둔 것이라 여기서 새로 만들지 않는다.)

**Never:**
- 재연결 배너·오프라인 큐잉·갭 보정(Broadcast Replay/커서 재조회)은 만들지 않는다 — Story 12.4 범위.
- 안읽음 배지·방 목록 정렬은 만들지 않는다 — Story 12.5 범위.
- Flutter 앱(`app/lib/features/chat/**`)은 손대지 않는다 — Epic 16 Story 16.4가 전담(웹 안정화 후 미러링). 아래 Design Notes 참조.
- "실시간 즉시 반영(재로드 없이)" 자체를 검증하는 자동 E2E를 새로 만들지 않는다 — 이 성공 지표는 Story 12.6이 수동 2-브라우저로 검증하기로 에픽 컨텍스트가 이미 정해둠.
- 브로드캐스트 실패율 로그 등 새 관측/알람 인프라를 만들지 않는다 — 대장 `#195` 재판단 결과(아래 Design Notes).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 당사자 정상 전송 | 방 당사자, 유효 본문 | pending 버블 즉시 표시 → 서버 확정 시 실제 행으로 교체, 정렬 유지 | 없음 |
| 동일 키 재전송(네트워크 재시도) | 같은 `room_id`+`client_message_id` 재INSERT | `23505` → 기존 행 조회해 그 행으로 확정(중복 행 없음, 1행 수렴) | 없음(설계된 멱등 경로) |
| 상대 메시지 실시간 수신 | 구독 중 상대가 INSERT | 폴링 없이 방송으로 즉시 목록에 반영 | 없음 |
| 전송 자체 실패(RLS·네트워크 등, `23505` 아님) | INSERT가 다른 에러 반환 | 기존과 동일하게 에러 안내 + 입력 복원, pending 제거 | 기존 `handleSubmit` 에러 경로 재사용 |

</intent-contract>

## Code Map

- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- 폴링 제거, private 채널 구독 배선, pending 버블 상태 추가, 입력창 `size={1}`+`min-w-0`.
- `web/src/lib/messages.ts` -- `sendMessage`에 `client_message_id` 추가 + `23505` 흡수 후 기존 행 조회, `ChatMessageRow`에 `client_message_id` 필드 추가.
- `web/e2e/viewport-audit.spec.ts` -- 채팅방 화면 케이스 추가(가로 오버플로 없음).
- `web/e2e/helpers.ts` -- 채팅방 화면 접근용 헬퍼 필요 시 추가(시드된 `chat_rooms`에서 SEED_USER 참여 방 id 조회, `fetchOnSaleListingIdWithPhoto`와 동일한 psql 패턴).
- `docs/conventions.md` -- 신설 절(구독 토픽·private+setAuth·payload 파싱 계약).
- `supabase/migrations/0023_chat_realtime_broadcast.sql`(참고만, 무수정) -- 토픽 리터럴·RLS 정책의 정본.
- `web/src/components/ai/ChatAssistant.tsx:198-219`(참고만) -- `#84` `size={1}`+`min-w-0` 패턴의 기존 적용례.

## Tasks & Acceptance

**Execution:**
- `web/src/lib/messages.ts` -- `sendMessage`가 `client_message_id: crypto.randomUUID()`를 받아 INSERT에 싣고, `23505` 응답 시 기존 행을 조회해 반환하도록 수정 -- 멱등 전송의 단일 출처(대장 `#186`).
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- `setInterval` 폴링 제거, `chat:room:{roomId}` private 채널 구독(+`setAuth`) 배선, pending 버블 상태·교체 로직, 입력창 `size={1}`+`min-w-0` 적용 -- 이 스토리의 핵심 표면.
- `web/e2e/viewport-audit.spec.ts` + `web/e2e/helpers.ts` -- 채팅방 화면 오버플로 케이스 추가 -- 대장 `#169` 이행.
- `docs/conventions.md` -- 구독 계약 신설 절 -- Epic 16.4가 참조할 단일 출처.
- `docs/tech-debt.md` -- 이번에 내린 두 판단(웹 한정 범위 확정, `#195` 관측 인프라 보류)을 신규 항목으로 등재 -- B8(미룬 것도 적는다), 기존 항목은 무수정.

**Acceptance Criteria:**
- Given 구독이 활성 상태인 방에서 상대가 메시지를 보내면, when 방송이 도착하면, then 폴링 코드 없이 화면에 반영된다.
- Given 사용자가 메시지를 제출하면, when 제출 즉시, then pending 버블이 보이고 서버 확정 시 실제 행으로 교체된다(UX-DR15).
- Given 같은 `client_message_id`로 INSERT가 두 번 시도되면, when 두 번째가 유니크 위반이면, then `chat_messages`엔 정확히 1행만 남고 클라이언트는 그 행으로 수렴한다.
- Given 390px 뷰포트에서 채팅방에 진입하면, when 렌더되면, then 가로 스크롤이 생기지 않는다(`scrollWidth <= clientWidth`).
- Given 채팅 무결성 3중 장치(RLS·트리거·CHECK buyer≠seller), when 이 스토리의 변경 전후를 비교하면, then 동일하게 유지된다(CM-B, 회귀 없음).

## Spec Change Log

## Review Triage Log

### 2026-07-29 — Review pass (후속 3차 — `status: done` 스펙 재검토)
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 3, low 7)
- defer: 1: (high 0, medium 0, low 1)
- reject: 12
- addressed_findings:
  - `medium` `patch` **초기 로드와 구독 사이의 틈에 들어온 메시지가 영구히 유실된다** — 실측으로 재현했다. 코드 순서는 `fetchMessages` 먼저, `getSession`→`setAuth`→웹소켓 join이 나중이라 그 사이(수십~수백 ms)의 INSERT는 조회 응답에도 없고(이미 끝났다) 방송으로도 오지 않는다(아직 구독 전). 폴링이 있을 땐 3초 뒤 커서 조회가 주워 담았으므로 이건 이 스토리가 새로 만든 구멍이고, 실패 경로가 아니라 **정상 경로**라 앞선 두 패스의 "구독이 죽는 경우" 사냥에 걸리지 않았다. 실제 코드와 같은 순서로 돌린 프로브에서 baseline=유실 / fixed=수신을 확인. **최초 `SUBSCRIBED` 1회에 한해** 전체 로드를 한 번 더 돌려 닫았다(재연결마다 도는 갭 보정이 아니다 — 그건 Never 절대로 12.4 범위).
  - `medium` `patch` 초기 로드 실패 문구가 **다음 전송 한 번에 지워졌다** — 2차 패스가 `realtimeError`에 대해 고친 것과 똑같은 결함이 `error` 한 칸 옆에 그대로 남아 있었다(`handleSubmit` 첫 줄 `setError(null)`이 조회 실패 문구까지 지운다). 폴링이 없어 재조회 경로가 아예 없으므로 한 번 지워지면 영영 복구되지 않고, 남은 화면은 "원래 대화가 없던 방"과 구별되지 않는다. `loadError` state로 분리.
  - `medium` `patch` 끊겼다 자동 재조인되면 경고를 **그냥 지웠다** — 연결은 살아났지만 끊겨 있던 동안 온 메시지는 아무 데도 없다(갭 보정은 12.4). 경고를 지우면 사용자는 "다 정상"이라 읽고 그 구멍을 영영 모른다. 2차 패스가 넣은 fail-loud가 재조인 한 번에 스스로 꺼지는 구조였다. 문구를 "복구됐지만 끊긴 동안 온 메시지는 새로고침해야 보인다"로 바꿔 남긴다.
  - `low` `patch` `finally { setSending(false) }`에만 방 전환 가드가 없었다(다른 세 곳엔 2차 패스가 넣었다). A방 응답이 B방의 `sending`을 풀어 연타 차단이 뚫리면 서로 다른 멱등키로 두 번 INSERT돼 실제 중복 행이 생긴다 — pending을 단일 값으로 둔 근거("sending이 동시 다건을 막는다")도 함께 깨진다.
  - `low` `patch` 2차 패스의 `landedKeys` 흡수는 "에코가 실패 응답보다 **먼저** 온" 순서만 구제했다. 반대 순서에선 이미 "보내지 못했습니다"+입력 복원이 뜬 뒤 같은 메시지가 목록에 올라와 모순 화면이 남는다. 브로드캐스트 콜백에서 그 키가 실패 기록과 같으면 실패 표시를 거두도록 보완(사용자가 이미 고쳐 쓰고 있으면 입력은 건드리지 않는다).
  - `low` `patch` 초기 로드 중에는 목록이 "불러오는 중…" 한 줄로 대체돼 **pending 버블이 렌더될 자리가 없는데** 입력창은 잠기지 않았다 — UX-DR15(전송 즉시 낙관적 표시)가 하필 피드백이 가장 필요한 느린 로드 구간에서만 깨진다. `disabled={sending || loading}`.
  - `low` `patch` 2차 패스가 만든 토픽 계약 검사가 **0023 파일 하나에 고정**돼 있었다 — 이 레포의 DB 규칙은 전진(forward-only)이라 토픽을 바꾸는 정상 경로는 새 마이그레이션(0024+)의 `create or replace`인데, 그게 정확히 이 검사의 사각지대였다(검사가 막으려던 단 하나의 실제 드리프트를 못 본다). 마이그레이션 전체 글로브로 교체. 함께: **방송 이벤트 이름**(`tg_op` ↔ `event: 'INSERT'`)이 토픽과 완전히 같은 무음 실패 축인데 아무도 대조하지 않아 교차 검사 추가, `private: true` 단언이 게을러 "파일 어딘가에 있으면 통과"였던 것을 그 호출 하나에 묶었다.
  - `low` `patch` `dedupeById`의 (created_at, id) 정렬이 폴링 제거 후 **화면 시간순의 유일한 보장**이 됐는데 이 순수 함수를 부르는 테스트가 하나도 없었다. `fetchMessages`의 gte 커서 분기도 유일한 실행 경로(폴링)를 잃어 12.4가 재채택할 때까지 무검증이다. 둘 다 순수 유틸이라 이 레포의 web 테스트 규칙에 정확히 들어맞는 자리 — 단위 테스트 6건 추가.
  - `low` `patch` 멱등키 재사용 판정(60초 창)이 컴포넌트 안에 인라인이라 **어느 방향으로 뒤집혀도 아무 검사가 울지 않았다** — 이 판정은 1차 패스의 결함(재시도가 새 키 → 중복 행)과 2차 패스의 결함(옛 키 재사용 → 새 메시지 유실)이 정면으로 맞부딪히는 자리다. 순수 함수 `reuseFailedKey`로 분리하고 창 경계 양쪽(60,000ms=재사용 / 60,001ms=새 키)을 테스트로 고정.
  - `low` `patch` `docs/conventions.md` §12 세 곳 정정 — (a) §12.1이 여전히 "강제 장치가 없는 문자열 일치"라 적어 같은 절 도입부("실행되는 검사가 고정한다")와 자기모순, (b) §12.4의 NULL 안전 설명이 실제 코드와 반대 방향(가드는 `record` 쪽이 아니라 `pending` 쪽에 걸린다 — Epic 16.4가 Dart로 옮길 때 그대로 틀리게 옮길 자리), (c) §12.3에 위 조인 갭 마무리 조회 규칙 신설.
- defer 1건 — 관리자 대화 열람 화면(`/admin/chats/[roomId]`)이 같은 `chat_messages.body`를 `break-words` 없이 렌더한다. 2차 패스가 사용자 화면에서 실측으로 닫은 `#169`가 관리자 쪽엔 그대로 남아 있고 그 화면을 여는 검사도 없다(E2E는 목록만 방문, 신규 스캔 검사는 `ChatRoomMessages.tsx` 하드코딩). 이 diff가 건드린 파일이 아니라 이번 스토리에서 고치면 요청에 추적되지 않는 변경이 되므로(A3) 대장 신규 `#200`으로 등재.
- 기각 12건 — `created_at` 사전순 비교가 직렬화 경로에 따라 어긋난다(두 경로 모두 PostgREST 세션 UTC, edge-case 리뷰어도 검증 후 스스로 기각) · 스펙 `final_revision`이 1차 커밋을 가리킨다(사실이 아님 — 이미 2차 커밋 `0825d86`) · 실시간 수신 자체의 자동 E2E가 없다/E4가 푸시를 관측하지 않는다(스펙 Never + 에픽이 12.6 수동 검증으로 확정, 3연속 동일 기각) · 재연결 갭 보정이 없다(스펙 Never, 12.4) · `lastFailedRef`가 단일 슬롯이라 중간에 다른 전송이 성공하면 지워진다(60초 창과 겹쳐 실익 대비 과설계, A2) · `messageBubbleWrap` 검사의 하드코딩 카운트가 브리틀하다(의도된 트립와이어) · `viewport-audit`이 Docker/psql에 의존한다(이 스위트는 시드 로그인부터 로컬 전용) · `onAuthStateChange`의 `session === null` 미처리(setAuth 없이 구독해도 RLS가 거부해 `CHANNEL_ERROR`로 화면에 뜬다 — 이미 fail-loud) · 브로드캐스트 payload 런타임 형태 검증 부재(`realtime.messages`에 클라 INSERT 정책이 없어 외부 주입 경로가 닫혀 있음) · `atOrAfterCreatedAt`를 죽은 코드로 지워야 한다(12.4 재사용이 이미 확정 — 대신 이번에 테스트를 붙였다) · AC5(채팅 무결성 3중 장치 회귀 없음)가 측정되지 않았다(측정으로 확인: 이 diff는 `supabase/**`를 단 한 줄도 건드리지 않는다 — RLS·트리거·CHECK가 정의된 유일한 자리다) · 대장 `#64`·`#169`·`#186`·`#195`의 상태를 갱신해야 한다(이번 실행의 호출 지시가 기존 항목의 상태·해소를 오케스트레이터 소관으로 명시 유보 — 아래 "사람 확인 필요"로 보고만 한다).

### 2026-07-29 — Review pass (후속 2차 — `status: done` 스펙 재검토)
- intent_gap: 0
- bad_spec: 0
- patch: 12: (high 1, medium 6, low 5)
- defer: 0
- reject: 10
- addressed_findings:
  - `high` `patch` `lastFailedRef`(1차 패스가 넣은 멱등키 재사용)에 **만료가 없어** 반대 방향의 조용한 유실이 생겼다: 전송이 실패했지만 서버엔 실제로 저장된 경우(응답만 유실) 그 키가 무기한 남아 있다가, 한참 뒤 사용자가 우연히 **같은 본문**을 보내면 그 키가 재사용돼 `23505` → 옛 행으로 수렴하고 새 메시지는 전송되지 않은 채 UI만 성공으로 보인다. 이 앱의 실제 메시지는 매우 짧고 반복적이라(시드 데이터에 `ㅇㅇ`·`ㅎㅇ`) 우연한 일치가 사변적이지 않다. 재사용 창(`FAILED_KEY_REUSE_WINDOW_MS = 60초`)을 도입하고, 실패 기록에 시각을 함께 남기도록 수정.
  - `medium` `patch` 구독 실패 경고가 **다음 전송 한 번에 지워졌다** — `handleSubmit` 첫 줄의 `setError(null)`이 `error` 한 칸을 공유하는 구독 실패 문구까지 지운다. 폴링이 사라진 상태에서 사용자는 "정상"이라 믿고 계속 쓰게 된다(1차 패스가 넣은 fail-loud 장치가 사용자 행동 한 번으로 무력화). 수명이 다른 신호이므로 `realtimeError` state를 분리하고 재구독 성공(`SUBSCRIBED`) 시에만 지우도록 수정.
  - `medium` `patch` `subscribe` 콜백이 `CHANNEL_ERROR`/`TIMED_OUT`만 보고 **`CLOSED`를 놓쳤다.** 라이브러리 소스로 확인: `@supabase/phoenix`의 `channel.js` `onClose` 훅은 `rejoinTimer.reset()` + `socket.remove(this)` — 즉 **자동 재조인이 없는 종착 상태**다(일시적 끊김은 `onError`를 타 `CHANNEL_ERROR`로 오고 재조인이 예약된다). 폴링이 없으므로 이걸 놓치면 메시지가 조용히 영영 안 온다. `CLOSED`를 같은 분기에 포함(우리 쪽 정리로 닫히는 경우는 기존 `cancelled` 가드가 이미 걸러낸다).
  - `medium` `patch` `getSession`/`setAuth`를 도는 async IIFE에 `try/catch`가 없어, `setAuth`가 거부되면 `channel.subscribe(...)` 자체가 호출되지 않는다 — 즉 "실패를 화면에 남긴다"던 그 콜백이 **아예 배선되지 않은** 채 화면은 초기 로드분만 띄우고 영영 조용해진다. `try/catch`로 감싸 그 경로도 사용자에게 보이게 수정.
  - `medium` `patch` 전송 응답이 실패로 왔지만 **브로드캐스트 에코가 이미 그 행을 목록에 올려둔 경우**(응답만 유실된, 멱등키가 존재하는 바로 그 시나리오) 화면에 메시지가 보이는 채로 "보내지 못했습니다" + 입력값 복원이 함께 뜨는 모순이 있었다. 목록에 올라온 키를 `landedKeysRef`로 기억해, 그 키가 이미 도착했으면 성공으로 취급하도록 수정.
  - `medium` `patch` 메시지 버블에 줄바꿈 규칙이 없어(`max-w-[80%] whitespace-pre-wrap`뿐) **공백 없는 긴 본문(붙여넣은 URL 등)이 버블 밖으로 넘쳤다.** 추측이 아니라 실측: 시드 방에 200자 URL 한 건을 넣고 390px에서 재니 `scrollWidth 672 > clientWidth 390` — 이 스토리가 닫으려던 대장 `#169`의 결함이 같은 화면에서 재현됐다(신규 viewport 케이스는 시드 방 메시지가 최대 20자라 이걸 못 잡는다). 세 버블에 `break-words` 적용.
  - `medium` `patch` 토픽 리터럴에 **실행되는 교차 검사가 없었다**(B9 — "지켜야 하는 규칙이면 실행되는 검사로 바꾼다"). 게다가 사본은 둘이 아니라 셋이었다(0023 SQL, `roomTopic()`, `api/tests/integration/test_chat_realtime_broadcast_real_db.py`의 `_TOPIC_PREFIX`) — `conventions.md` §12는 둘만 적고 "사람이 맞춰야 한다"고 서술했다. 세 사본을 읽어 대조하는 vitest(`roomTopicContract.test.ts`, `private: true` 구독도 함께 단언)를 추가하고 §12를 그 검사를 가리키도록 정정. red/green 실측 완료.
  - `low` `patch` `crypto.randomUUID()`가 `try` **밖**에서 `setSending(true)`·`setInput('')` 뒤에 호출돼, 여기서 예외가 나면 `finally { setSending(false) }`를 건너뛰어 입력값은 이미 지워진 채 전송 버튼이 영구히 잠긴다(새로고침 외 복구 불가). 1차 패스는 "도달 가능한가"로 기각했으나 이 지적은 **위치(피해 범위)**에 관한 것이라 별개다 — 키 생성을 `try` 안으로 옮김.
  - `low` `patch` 전송 응답을 기다리는 동안 다른 방으로 이동하면(리마운트 없는 네비게이션) A방 메시지가 B방 목록에 병합되고 A방 입력값이 B방 입력창에 복원됐다. 1차 패스가 초기 로드를 덮어쓰기→병합으로 바꾸면서 이 잔상이 지워지지 않고 남게 된 것. `roomIdRef` 가드 추가.
  - `low` `patch` `onAuthStateChange`의 `setAuth` 호출이 await·catch 없이 떠 있어(초기 경로의 동일 호출은 await한다) 토큰 회전 실패가 unhandled rejection으로 사라졌다 — 이 리스너가 막으려던 상황이 조용히 지나간다. `void ... .catch(log)` + `cancelled` 가드 추가.
  - `low` `patch` `_bmad-output/project-context.md` §8이 "전송 방식의 정본 = `ChatRoomMessages.tsx`의 `POLL_INTERVAL_MS`"라고 가리키는데 이 스토리가 그 상수를 지웠다 — 매 세션 주입되는 규칙 파일에 끊긴 포인터가 남았다. `docs/conventions.md` §12를 가리키도록 정정(앱은 아직 폴링이라는 사실도 명시).
  - `low` `patch` `web/e2e/helpers.ts`에서 `fetchChatRoomIdForSeedUser`를 설명하는 18줄 JSDoc이 바로 뒤 `sqlLit`(2줄 이스케이프 함수)에 붙어 있었다. 또 그 안의 "Node 프로세스에서 세션을 재사용할 수 없다"는 근거는 사실이 아니다(같은 파일의 `SEED_USER`에 비밀번호가 있어 토큰 발급이 가능하다). 주석을 제 함수로 옮기고 근거를 실제 이유로 정정.
- 기각 10건 — 실시간 수신 자체의 자동 E2E가 없다·E4가 실제로는 푸시를 관측하지 않는다(스펙 Never 절 + 에픽이 Story 12.6 수동 검증으로 이미 확정, 스펙 자신이 아니라 에픽 레벨의 권위) · web E2E가 CI에 없다(이미 대장 `#168`) · 브로드캐스트 payload 런타임 형태 검증 없음(`realtime.messages`에 클라 INSERT 정책이 없어 외부 주입 경로가 닫혀 있고 트리거는 같은 레포 안에서 통제됨) · 로그아웃(`session === null`) 미처리(사변적, 1차 패스와 동일) · `atOrAfterCreatedAt`가 죽은 코드가 됨(바로 다음 12.4가 갭 보정에 재사용하기로 이미 확정, 문서화됨) · `viewport-audit`이 이제 Docker/psql에 의존한다(이 스위트는 시드 로그인부터 로컬 스택 전용이라 비로컬 실행 선례가 없음) · pending 버블이 과설계다(스펙 Always가 UX-DR15로 명시 요구) · 원격 전제 미확인 상태로 폴링을 걷었다·관측 인프라가 없다(스펙 Never + 대장 `#195`~`#197`이 "원격 적용 직전"으로 이미 등재, 스펙 Residual risks에도 있음) · 대장 `#169`·`#195`·`#186`을 닫아야 한다(이번 실행의 호출 지시가 기존 대장 항목의 상태·해소를 오케스트레이터 소관으로 명시 유보 — 아래 "사람 확인 필요"로 보고만 한다).

### 2026-07-29 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 1, medium 3, low 3)
- defer: 0
- reject: 8
- addressed_findings:
  - `high` `patch` 전송 실패 후 사용자가 같은 내용으로 재시도해도 매번 새 `client_message_id`가 생성돼, 이 앱의 유일한 재전송 경로(자동 재시도 없음 — 실패→입력 복원→사용자가 다시 전송 클릭)에서 FR41 멱등 보호가 실제로 발동하지 않았다(서버엔 저장됐는데 응답만 유실된 경우 재전송이 새 키로 중복 저장될 수 있음, 어드버서리얼+edge-case 교차 지적). `ChatRoomMessages.tsx`에 `lastFailedRef`를 추가해 실패 시점 `{clientMessageId, body}`를 기억하고, 재시도 시 입력값이 그때와 글자 그대로 같으면 그 키를 재사용하도록 수정.
  - `medium` `patch` 방 진입 시 초기 전체 로드(`fetchMessages`)가 실시간 구독보다 늦게 끝나면 `setMessages(res.messages)`가 이미 화면에 올라간 실시간 메시지(자기 전송 포함)를 통째로 덮어써 지우는 레이스가 있었다(edge-case-hunter 실측 지적 — 다른 모든 갱신 경로는 병합을 거치는데 이 자리만 예외). `dedupeById([...prev, ...res.messages])` 병합으로 통일.
  - `medium` `patch` 실시간 채널이 `CHANNEL_ERROR`/`TIMED_OUT`이어도 `console.error`만 남기고 화면엔 아무 표시가 없어, 이 파일 자신이 다른 곳에서 명시한 "조용한 실패 금지(fail-loud)" 원칙과 어긋났다(adversarial 지적). 같은 분기에서 사용자에게 보이는 `error` state도 설정하도록 수정(재연결 로직은 12.4 범위라 새로 만들지 않음).
  - `medium` `patch` 리마운트 없이 방을 전환할 때(React가 같은 컴포넌트 인스턴스 재사용) `pending`/`error`/`input`/`sending`이 안 지워져 이전 방의 잔상이 새 방 화면에 보일 수 있었고, 브로드캐스트 콜백도 `cancelled` 가드가 없어 전환/언마운트 후 도착한 이벤트가 여전히 `setState`할 수 있었다(adversarial+edge-case 교차 지적). roomId 변경 시 네 state를 함께 초기화하고, 브로드캐스트 콜백 맨 위에 `cancelled` 체크를 추가.
  - `low` `patch` `web/e2e/helpers.ts`의 `fetchChatRoomIdForSeedUser`가 이메일을 이스케이프 없이 psql 문자열에 직접 넣어 이 파일의 기존 이스케이프 관례(`sqlLit()`)와 어긋났다(adversarial 지적). 동일 관례로 이스케이프하도록 수정.
  - `low` `patch` `sendMessage`의 23505 복구 경로가 재조회한 행이 정말 호출자 자신의 것인지 확인하지 않고 바로 성공 반환했다(adversarial 지적 — 이 함수의 계약은 "호출자 자신의 확정된 전송을 돌려준다"는 것). `existing.sender_id === senderId && existing.body === trimmed` 확인을 추가하고, 불일치 시 일반 에러로 폴백 + 회귀 테스트 2건 추가.
  - `low` `patch` `docs/conventions.md` §12 도입부가 "§1·§7과 같은 패턴"이라고 썼으나 그 둘은 코드가 import하는 공유 상수 하나로 강제되는 반면, §12.1의 토픽 형식은 SQL·TS에 각자 따로 쓰인 두 리터럴이라 자동 강제 장치가 없다(adversarial 지적). 문구를 "자동 강제 없이 사람이 양쪽을 맞춰야 한다"로 정정.
- 기각 8건 — `onAuthStateChange`에서 `session`이 null(로그아웃)일 때 명시적 처리가 없다는 지적(이 화면은 로그인 후에만 도달하고 로그아웃 시 통상 즉시 이탈/언마운트되므로 사변적) · 브로드캐스트 payload 캐스트에 런타임 형태 검증이 없다는 지적(DB 트리거 계약이 같은 레포 안에서 통제되는 자리라 드리프트 시나리오가 사변적) · `roomTopic(roomId)`에 입력 검증이 없다는 지적(roomId는 항상 RLS로 확인된 서버 페이지 파라미터에서만 옴) · `crypto.randomUUID()`가 try 블록 밖에서 예외를 낼 수 있다는 지적(이 프로젝트의 실제 배포 대상(Vercel/HTTPS, 로컬은 localhost)에서 secure context 위반 경로 자체가 없어 발생 불가) · `clientMessageId`에 형식 검증이 없다는 지적(DB uuid 컬럼 타입이 이미 막음, body처럼 다층 방어가 필요한 사용자 입력이 아님) · 재연결 시 갭 보정이 없다는 지적(스펙 Never 절이 이미 Story 12.4 범위로 명시) · 실시간 수신 자체를 검증하는 자동 E2E가 없다는 지적(에픽 문서가 이 성공 지표를 Story 12.6의 수동 2-브라우저 검증으로 이미 정해둠 — 스펙 자기 자신이 아니라 에픽 레벨의 권위 있는 범위 결정) · 23505 흡수 경로가 mock 테스트만 있고 실DB 통합 테스트가 없다는 지적(0022의 UNIQUE 제약이 실제로 23505를 내는지는 12-1의 `test_chat_idempotency_real_db.py`(무수정, 여전히 존재)가 이미 검증하고 있어 이번 diff의 mock 테스트와 합쳐 계약 전체가 커버됨 — 이 레포가 이미 쓰는 "DB 제약=api/tests, 클라이언트 분기=web/src" 분리 관례와 동일).

## Design Notes

**왜 웹 한정인가(대장 `#186`의 "web·app 양쪽" 언급과의 긴장 해소):** 에픽 문서가 Epic 16 Story 16.4를 "실시간 채팅(앱)"으로 이미 분리해뒀고, 16.4 자체가 "Realtime Broadcast·멱등키·chat_room_reads(Epic 12)"를 전제조건으로 인용한다 — 즉 12.3이 완성한 웹 코드가 아니라 Epic 12가 놓은 **DB 토대**를 앱이 나중에 소비하는 구조다. Epic 12의 어느 스토리 AC에도 앱 파일이 등장하지 않고, Epic 16 소개도 "웹 기능이 안정된 뒤 미러링"이라 명시한다. `#186`의 "web·app 양쪽"은 이 분리를 반영하지 못한 채 작성된 것으로 판단해, 이번엔 웹만 채우고 앱은 16.4로 남긴다(새 tech-debt 항목으로 이 판단 근거만 기록, `#186` 자체는 무수정).

**`#195` 재판단(트리거 도래):** 브로드캐스트가 조용히 삼켜지는 위험(플랫폼 `realtime.send()`)에 새 관측 인프라를 만들지 않는다 — (1) 바로 다음 Story 12.4가 재연결 갭보정을 붙이므로 연결-드롭 경로의 유실은 그때 닫힌다, (2) 연결이 살아있는데 방송만 조용히 안 오는 순수 실패는 원격 전제(`#195`·`#196`, 배포 직전 확인 대상)이지 로컬/CI에서 재현 가능한 코드 결함이 아니다, (3) 방 최초 진입 시 전체 조회는 그대로 유지해 새로고침하면 항상 최신 상태로 복구된다. (새 tech-debt 항목으로 기록, `#195` 자체는 무수정.)

**pending 버블 확정 경로:** "자기 `sendMessage` 응답"과 "브로드캐스트 에코" 중 먼저 도착하는 쪽을 따른다 — 같은 `client_message_id`를 가진 실제 행이 어느 경로로든 먼저 도착하면 그걸로 pending을 지운다(이중 경로 레이스 대비, 어느 쪽이 늦게 와도 이미 지워진 pending과 dedupeById가 중복 렌더를 막는다).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 warnings.
- `cd web && npx tsc --noEmit` -- expected: 0 errors.
- `cd web && npm test` -- expected: 기존 + 신규 vitest 전부 green(멱등 흡수 로직 단위 테스트 포함).
- `cd web && npx playwright test viewport-audit write-flows` -- expected: 전부 green(채팅방 오버플로 신규 케이스 + 기존 E4 두-브라우저 시나리오 회귀 없음).

**Manual checks (if no CLI):**
- 로컬 Supabase 스택에서 buyer/seller 두 브라우저 세션으로 실제 실시간 송수신(새로고침 없이 상대 메시지가 뜨는지)을 실측 확인하고, 폴링 관련 코드(`setInterval`)가 실제로 사라졌는지 코드로도 확인한다(B4).
- 멱등 재전송을 실제로 두 번 INSERT해 1행 수렴을 확인한다(가능하면 vitest/통합 테스트, 아니면 psql로 직접).

## Auto Run Result

**요약:** `ChatRoomMessages.tsx`의 3초 `setInterval` 폴링을 제거하고, 0023(Story 12.2)이 놓은 `chat:room:{roomId}` private 채널 Broadcast+RLS 토대를 웹이 처음 구독하도록 배선했다. `sendMessage`는 0022(Story 12.1)의 멱등키 컬럼을 처음 실전 투입해 `client_message_id`를 INSERT에 싣고, `23505`(재전송) 응답 시 기존 행을 조회해 그 행으로 수렴시킨다. 전송은 낙관적(pending 버블 즉시 표시 → 서버 확정 또는 브로드캐스트 에코 중 먼저 오는 쪽으로 확정)이다(UX-DR15). 대장 `#169`(390px 채팅 입력창 가로 오버플로) 이행 — `#84`와 동일한 `size={1}`+`min-w-0` 패턴 적용 + `viewport-audit.spec.ts`에 채팅방 케이스 신설. Flutter 앱은 범위 밖(Epic 16 Story 16.4가 전담) — 그 판단 근거를 tech-debt `#198`로 기록. 대장 `#195`(브로드캐스트 실패 무관측)의 트리거가 이번에 도래해 재판단했고, 결과는 "여전히 관측 인프라를 새로 만들지 않는다"이며 그 근거를 tech-debt `#199`로 기록.

**Files changed:**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 폴링 제거, private 채널 구독(+`setAuth`)·pending 버블·재시도 시 멱등키 재사용·방 전환 시 상태 리셋·구독 실패 가시화·초기 로드 병합(코드리뷰 patch 5건 포함) 배선. 입력창 `size={1}`+`min-w-0`.
- `web/src/lib/messages.ts`(수정) — `sendMessage`에 `client_message_id` 파라미터 + `23505` 흡수(재조회한 행의 `sender_id`·`body` 일치 확인 포함, 코드리뷰 patch). `ChatMessageRow`에 `client_message_id` 추가.
- `web/src/lib/__tests__/messages.test.ts`(신규) — 멱등 흡수 로직 단위 테스트 6건(client_message_id 전달 1건 + 23505 흡수/폴백/회귀 3건 + 코드리뷰 patch로 추가한 sender_id·body 불일치 회귀 2건).
- `web/e2e/viewport-audit.spec.ts`, `web/e2e/helpers.ts`(수정) — 채팅방 화면 오버플로 케이스 + 시드 채팅방 조회 헬퍼(코드리뷰 patch로 `sqlLit()` 이스케이프 적용).
- `docs/conventions.md`(수정) — §12 신설(구독 토픽·private+setAuth·payload 파싱·멱등 전송 계약, 코드리뷰 patch로 도입부 문구 정정).
- `docs/tech-debt.md`(수정) — 신규 등재 2건: `#198`(웹 한정 범위 판단 근거) · `#199`(`#195` 재판단 결과, defer). 기존 항목 무수정.

**Review findings breakdown** (adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 레이어 병렬 실행, 오케스트레이터가 diff·코드를 직접 대조해 오탐 제외):
- patch 7건(high 1·medium 3·low 3) — 상세는 위 Review Triage Log 참조. 핵심 3건: (1) 전송 실패 후 재시도가 새 멱등키를 만들어 FR41 멱등 보호가 재전송 경로에서 실제로 무력화됨(high) — 실패 시점 키를 기억해 같은 내용 재시도 시 재사용하도록 수정. (2) 초기 로드가 먼저 도착한 실시간 메시지를 덮어쓰는 레이스(medium) — 병합으로 통일. (3) 실시간 구독 실패가 화면에 안 보임(medium, 이 파일 자신의 fail-loud 원칙 위반) — 에러 상태 노출 추가.
- reject 8건 — 전부 사변적 시나리오(secure-context 위반, DB 트리거 드리프트, roomId 위조 등 이 레포 배포 토폴로지·기존 방어층에서 실제로 도달 불가) 또는 이미 명시적으로 다른 스토리 범위(12.4 갭보정, 12.6 수동 검증)로 확정된 것들. 상세 근거는 Review Triage Log 참조.
- intent_gap·bad_spec 0건 — intent-alignment auditor가 이 diff를 "12.3의 스펙이 미리 좁혀둔 읽기(웹만, DB 토대 소비, 자동 E2E 대신 수동 검증)를 충실히 구현한 것"이라 확인. 유일하게 짚은 것은 "diff 자체엔 그 수동 2-브라우저 검증이 실제로 수행됐다는 증거(로그·스크린샷)가 없다"는 점 — 이를 받아 오케스트레이터가 아래처럼 별도로 직접 재현했다.

**Follow-up review recommendation:** `true`. 이번 패스 패치 7건 중 high 1건(재시도 멱등키 미재사용) → 규칙상 `true`.

**Verification 수행 (오케스트레이터가 직접 재실행, 서브에이전트 보고에 의존하지 않음):**
- 구현 직후: `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(243 passed) · `npx playwright test viewport-audit write-flows`(23 passed, 10 skipped — 기존 E4 두-브라우저 시나리오 포함) 전부 오케스트레이터가 직접 재실행해 확인.
- **실시간 수신을 오케스트레이터가 실제 코드 경로로 직접 재현**: `@supabase/supabase-js`로 buyer·seller 두 개의 독립 세션을 만들어, seller가 `ChatRoomMessages.tsx`와 동일한 방식(`chat:room:{roomId}` private 채널 + `setAuth` + `broadcast`/`INSERT` 구독)으로 이미 구독을 열어둔 상태에서 buyer가 실제 `chat_messages`에 INSERT → **51ms만에 seller의 열린 구독이 새로고침·재조회 없이 그 메시지를 수신**함을 확인(PASS). 프로브로 만든 행은 세션이 RLS로 삭제를 못 해(0행 영향) 슈퍼유저 psql로 직접 정리, 잔여 0건 확인.
- 코드리뷰 patch 7건 적용 후: `npm run lint`(0) · `npx tsc --noEmit`(0) · `npm test -- --run`(245 passed, 신규 회귀 2건 포함) · `npx playwright test viewport-audit write-flows`(23 passed, 10 skipped, 회귀 없음) 전부 오케스트레이터가 다시 직접 재실행해 확인. 구현 세션도 별도로 두 브라우저 컨텍스트 재실측(PASS)을 보고.
- **DW-5 처리 결과** (활성화 시 로드한 persistent fact 지시사항): `deferred-work.md`의 `DW-5`(status: open, 12-1 review-budget-followup)를 확인 — `docs/tech-debt.md` `#192`에 이미 이관돼 있음(2026-07-29 Story 12-2 착수 시 처리됨). 이번 스토리에서 추가 조치 없음. 동결 파일 자체는 무수정.

**Residual risks:**
- 대장 `#195`·`#196`·`#197` — 원격(운영) Supabase 프로젝트 적용 직전 사용자가 확인할 것(Realtime/Broadcast 활성화, `realtime.send` `private` 기본값, 파티션 유지, `rolbypassrls`). 이번 스토리가 새로 만든 위험이 아니라 12.2가 이미 등재해둔 것 — 트리거는 "원격 적용 직전"으로 동일.
- 실시간 수신·전송 전체를 검증하는 **자동** E2E는 여전히 없다(의도적 — Story 12.6이 수동 2-브라우저로 검증하기로 에픽 레벨에서 이미 정해짐). 오케스트레이터가 이번에 스크립트로 핵심 경로를 1회 직접 재현했으나, 이는 상시 회귀 방지 수단은 아니다.
- 재연결 시 갭 보정(끊긴 동안 놓친 메시지 재조회)은 여전히 없다 — Story 12.4 범위로 이미 확정.
- Flutter 앱(`app/lib/features/chat/**`)은 이번에 전혀 손대지 않았다 — Epic 16 Story 16.4가 전담, 이번에 문서화한 `docs/conventions.md` §12 계약을 그대로 따라가면 됨.

**잔여 아티팩트:** 이 스펙 파일 자체의 `final_revision` 프론트매터 값(커밋 해시)은 커밋이 끝난 뒤에야 알 수 있어, 그 값을 적은 이 편집분은 커밋에 포함되지 않았다(커밋하면 HEAD가 또 움직여 기록한 해시가 어긋난다) — `git status --porcelain`에 이 파일만 수정 상태로 남는 것은 의도된 것이다.

---

## Auto Run Result — 후속 리뷰 패스 (2026-07-29, 3차)

**무엇을 했나:** 2차 패스가 `followup_review_recommended: true`로 닫혔기에 `status: done`이던 이 스펙을 다시 열어 독립 후속 리뷰를 돌렸다. 4개 레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment)를 새 컨텍스트 서브에이전트로 병렬 실행하고, 오케스트레이터가 각 주장을 코드·실제 실행으로 직접 대조해 판정했다. 결과: **패치 10건(medium 3·low 7), defer 1건, 기각 12건.** intent_gap·bad_spec 0건 — intent-alignment auditor는 이 diff가 갈릴 수 있는 모든 축에서 방어적(넓은) 읽기를 택해 Always 8개·Never 5개를 코드 수준에서 빠짐없이 이행했다고 확인했고, 갈라지는 곳은 "무엇을 했나"가 아니라 "어디서 그것을 붙잡는가"(검사가 사는 표면)라고 짚었다 — 이번 패치의 절반이 정확히 그 지적을 받은 것이다.

**핵심 3건(왜 중요한가):**
1. **(medium) 초기 로드와 구독 사이의 틈에 들어온 메시지가 영구히 유실된다 — 실측으로 재현했다.** 코드 순서상 전체 조회가 먼저 나가고 `setAuth`→웹소켓 join이 나중이라, 그 사이에 상대가 보낸 메시지는 조회 응답에도 방송에도 없다. 폴링이 있을 땐 3초 뒤 커서 조회가 주워 담던 자리다. 앞선 두 패스가 "구독이 죽는 경우"만 훑은 탓에 **정상 경로에 난 이 구멍**이 두 번 다 통과했다. 최초 `SUBSCRIBED` 1회에 한해 전체 로드를 한 번 더 돌려 닫았다(재연결 갭 보정은 여전히 12.4 몫).
2. **(medium×2, 같은 뿌리) 사용자에게 "지금 뭔가 잘못됐다"를 알리는 신호가 스스로 꺼지는 경로가 둘 남아 있었다** — 초기 로드 실패 문구가 다음 전송 한 번에 지워지고(2차 패스가 `realtimeError`에 대해 고친 것과 똑같은 결함이 한 칸 옆에 그대로 있었다), 끊겼다 재조인되면 경고가 그냥 사라진다(끊긴 동안 온 메시지는 아무 데도 없는데). 폴링이 없어진 뒤로는 둘 다 "조용한 영구 유실"이라 신호를 각각 제 수명대로 남기게 고쳤다.
3. **(low×3, 같은 뿌리) 2차 패스가 만든 가드들이 자기가 지킨다고 주장한 것보다 적게 지키고 있었다** — 토픽 검사가 0023 파일 하나에 고정돼 이 레포의 정상 변경 경로(새 마이그레이션의 `create or replace`)를 구조적으로 못 보고, 방송 이벤트 이름은 토픽과 같은 무음 실패 축인데 아무도 대조하지 않았으며, 60초 재사용 창은 어느 방향으로 뒤집어도 전 검사가 green이었다. 셋 다 실제로 깨서 red를 확인한 뒤 고정했다.

**Files changed (이번 패스):**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 최초 SUBSCRIBED 1회 마무리 조회, `loadError` 분리, 재조인 경고 문구 유지, `finally` 방 가드, 실패-후-에코 뒷정리, 로드 중 입력 잠금, 멱등키 판정을 순수 함수 호출로 교체.
- `web/src/lib/messages.ts`(수정) — 멱등키 재사용 판정을 순수 함수 `reuseFailedKey`로 분리(+`FailedSend` 타입).
- `web/src/lib/__tests__/messages.test.ts`(수정) — `dedupeById` 3건 · `fetchMessages` 커서 3건 · `reuseFailedKey` 5건 = 11건 추가.
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`(수정) — 마이그레이션 전체 글로브, 방송 이벤트 이름 교차 검사 신설, `private: true` 단언을 그 호출 하나에 묶음.
- `docs/conventions.md`(수정) — §12.1 자기모순 정정 · §12.3 조인 갭 마무리 조회 규칙 신설 · §12.4 NULL 안전 설명을 실제 코드 방향으로 정정(Epic 16.4가 Dart로 옮길 자리).
- `docs/tech-debt.md`(수정) — defer 1건을 신규 `#200`으로 등재(관리자 대화 화면 `break-words` 미적용). 기존 항목 무수정.

**Verification (오케스트레이터가 직접 실행):**
- `npm run lint` 0 warning · `npx tsc --noEmit` 0 error.
- `npm test -- --run` **263 passed**(패스 시작 시 251 → 신규 12건).
- **red→green 실측(B4 "만들었다가 아니라 잡는다가 완료다")** 4건 전부: ① TS 이벤트 이름을 `'INSERTED'`로 훼손 → red(`expected 'INSERTED' to be 'INSERT'`) → 원복 green. ② 토픽을 바꾸는 가짜 `0024` 마이그레이션 추가 → red(`Set{'chat:room:','chat:rooms:'}`) → 제거 green. **이 케이스가 패치 전 버전(0023 고정)이었다면 green이었다** — 검사가 실제로 넓어졌음을 증명한다. ③ `dedupeById` 정렬 무력화 → 2건 red → 원복 green. ④ 재사용 창 조건 반전 → 2건 red → 원복 green.
- **조인 갭 결함 자체를 실측으로 재현·해소**: 실제 코드와 같은 순서(전체 조회 → 그 틈에 상대가 INSERT → `setAuth`+구독)로 도는 프로브를 로컬 스택에서 실행 — `baseline`(구독 후 재조회 없음)=**유실**, `fixed`(최초 SUBSCRIBED 1회 재조회)=**수신(PASS)**.
- **실시간 수신·멱등 재전송 재확인**(구독 콜백을 고쳤으므로 다시 봤다): 구독을 열어둔 상태에서 상대가 INSERT → **38ms만에 수신(PASS)**, 이어서 같은 키로 재INSERT → `23505` → 그 방+키 행 **정확히 1건**.
- `npx playwright test viewport-audit write-flows` **23 passed / 10 skipped** — 이전 패스와 동일(E4 두-브라우저 채팅·390px 채팅방 케이스 포함, 회귀 없음).
- 프로브가 만든 행은 전부 정리 — RLS에 `chat_messages` DELETE 정책이 없어(메시지는 영속·불변, 0003) 세션 삭제는 0행이므로 슈퍼유저 psql로 지우고 잔여 0건을 확인했다.
- **AC5(채팅 무결성 3중 장치 회귀 없음) 측정**: 리뷰가 "근거 없이 선언됐다"고 짚어 확인했다 — 이 diff는 `supabase/**`를 단 한 줄도 건드리지 않는다(RLS·트리거·`buyer_id <> seller_id` CHECK가 정의된 유일한 자리). 논증이 아니라 diff 범위로 확인한 사실이다.

**Follow-up review recommendation:** `true`. 이번 패스 패치 10건은 high **0건**·medium 3·low 7이고, 규칙은 "high가 하나라도 있거나 `3×medium + 1×low ≥ 5`"다 — 점수 3×3+1×7 = **16**이라 `true`. (다만 성격은 2차 패스와 다르다: 이번엔 high가 없고, 패치 절반이 코드 결함이 아니라 "가드가 주장만큼 지키지 못하던 것"의 보강이다.)

**DW 처리 결과:** `deferred-work.md`(동결)의 `DW-1`~`DW-5`는 2차 패스에서 확인한 대로 실체가 모두 대장에 이관돼 있다(`#148`·`#149`·`#164`·`#184`·`#192`). 이번 패스에서 새로 생긴 DW 항목 없음, 동결 파일 무수정.

**대장(`docs/tech-debt.md`) 변경:** 신규 `#200` 1건 등재(위 defer). 기존 항목은 무수정(호출 지시가 기존 항목의 상태·해소를 오케스트레이터 소관으로 유보).

**사람 확인이 필요한 것(오케스트레이터/사용자 판단 영역):**
- 대장 항목 상태 갱신 4건 — `#169`(390px 채팅 오버플로: 이번 스토리가 입력창·버블 양쪽을 실측으로 닫음) · `#186`(c)항(재전송 1행 수렴: 2차·3차 패스 프로브에서 실측 확인) · `#195`(트리거 도래 후 `#199`가 답함) · `#64`(`crypto.randomUUID()` secure context — 이번 스토리가 세 번째 호출부를 추가했는데 항목 본문은 두 곳만 적고 있다). 넷 다 이번 실행 권한 밖이라 손대지 않았다.

**Residual risks (이번 패스 기준 갱신):**
- 원격(운영) 전제 3건(`#195`·`#196`·`#197`)은 여전히 열려 있다 — 원격 적용 직전 확인 대상. 변동 없음.
- **재연결 시 갭 보정은 여전히 없다(Story 12.4).** 다만 이번에 두 가지가 달라졌다 — 최초 구독 시점의 갭은 닫혔고(그건 이 스토리가 만든 구멍이었다), 재연결 후에는 경고가 사라지지 않고 "새로고침해야 놓친 메시지가 보인다"고 남는다. 즉 남은 구멍은 **사용자에게 보이는** 구멍이 됐다.
- 실시간 송수신 전체의 **자동** E2E는 여전히 없다(의도적, Story 12.6 수동 검증). 이번 패스가 늘린 CI 가드는 토픽·이벤트 이름·`private` 플래그·버블 줄바꿈·정렬 불변식·멱등키 창까지다 — 전부 정적/순수함수 층이고, 실제 웹소켓 왕복은 여전히 오케스트레이터의 1회성 프로브로만 확인된다.
- web E2E는 여전히 CI에 없다(대장 `#168`).
- 관리자 대화 화면의 `break-words` 미적용(`#200`)은 이번에 고치지 않았다 — 사용자 화면과 달리 관리자 화면에서는 긴 URL 본문이 여전히 가로로 넘친다.

---

## Auto Run Result — 후속 리뷰 패스 (2026-07-29, 2차)

**무엇을 했나:** `status: done`이던 이 스펙을 다시 열어 독립 후속 리뷰를 돌렸다(1차가 `followup_review_recommended: true`로 닫혔기 때문). 4개 레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment)를 새 컨텍스트 서브에이전트로 병렬 실행하고, 오케스트레이터가 각 주장을 코드·라이브러리 소스·실제 실행으로 직접 대조해 판정했다. 결과: **패치 12건(high 1·medium 6·low 5), defer 0, 기각 10건.** intent_gap·bad_spec 0건 — intent-alignment auditor는 이 diff가 스펙의 모든 Always 8개·Never 5개를 코드 수준에서 이행했고, 갈릴 수 있는 다섯 축에서 전부 **방어적(넓은) 읽기**를 택했다고 확인했다.

**핵심 3건(왜 중요한가):**
1. **(high)** 1차 패스가 넣은 멱등키 재사용에 만료가 없어, 반대 방향의 조용한 유실이 생겼다 — 실패했지만 서버엔 저장된 키가 무기한 남아 있다가 나중의 **같은 본문** 메시지를 옛 행으로 흡수해 UI만 성공으로 보인다. 60초 재사용 창으로 한정.
2. **(medium×3, 같은 뿌리)** 실시간 구독이 죽어도 사용자가 모르는 경로가 셋 남아 있었다 — 경고가 다음 전송에 지워짐 / `CLOSED`(재조인 없는 종착 상태) 미처리 / `setAuth` 실패 시 `subscribe` 자체가 배선되지 않음. 폴링이 사라진 뒤로는 셋 다 "조용한 영구 유실"이라 fail-loud를 세 곳 모두에 채웠다.
3. **(medium)** 이 스토리가 닫으려던 대장 `#169`(390px 가로 오버플로)가 **긴 메시지에서 실제로 재현됐다**(실측 `scrollWidth 672 > 390`) — 버블에 줄바꿈 규칙이 없었다. `break-words` 적용 + CI에서 도는 스캔 검사로 고정.

**Files changed (이번 패스):**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx`(수정) — 위 패치 9건(`realtimeError` 분리, `CLOSED`+`SUBSCRIBED` 처리, 구독 준비 `try/catch`, `landedKeysRef` 기반 에코 확정, 멱등키 재사용 창, `break-words`, 키 생성 `try` 내부 이동, `roomIdRef` 방 전환 가드, `onAuthStateChange` setAuth catch).
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`(신규) — 토픽 리터럴 3사본(SQL·TS·Python) 대조 + `private: true` 구독 단언 4건.
- `web/src/app/(user)/chat/[roomId]/__tests__/messageBubbleWrap.test.ts`(신규) — 폭 제한 버블 전부가 `break-words`를 갖는지 2건.
- `web/e2e/helpers.ts`(수정) — JSDoc을 제 함수로 이동 + 근거 정정.
- `web/e2e/viewport-audit.spec.ts`(수정) — 채팅방 케이스가 **안 보는 것**(짧은 시드 메시지라 버블 오버플로는 못 잡음, 병렬 프로젝트 간 DB 간섭으로 E2E에서 만들 수 없음)을 검사 옆에 명시(B4).
- `docs/conventions.md`(수정) — §12 도입부를 "사람이 맞춰야 한다" → "실행되는 검사가 고정한다"로 정정, 사본 3곳 목록화.
- `_bmad-output/project-context.md`(수정) — §8의 끊긴 `POLL_INTERVAL_MS` 포인터를 §12로 교체.

**Verification (오케스트레이터가 직접 실행):**
- `npm run lint` 0 warning · `npx tsc --noEmit` 0 error.
- `npm test -- --run` **251 passed**(패스 시작 시 245 → 신규 6건: 토픽 계약 4 + 버블 줄바꿈 2).
- **red→green 실측(B4 "만들었다가 아니라 잡는다가 완료다")**: 토픽 검사 — TS를 `chat:rooms:`로, Python `_TOPIC_PREFIX`를 `chat:rooms:`로 각각 일부러 깨서 2건 red 확인 후 원복해 green 재확인. 버블 검사 — `break-words`를 제거해 red 확인 후 원복해 green 재확인.
- **오버플로 결함 자체를 실측으로 재현**: 시드 방에 200자 URL을 넣고 `viewport-audit`(390px)을 돌려 `scrollWidth 672 > clientWidth 390` red를 확인한 뒤 `break-words`로 해소, 프로브 행은 삭제(잔여 0건 확인).
- **실시간 수신 재현**: 구독 코드를 고쳤으므로 다시 확인했다 — buyer·seller 두 독립 세션으로 `chat:room:{roomId}` private 채널 + `setAuth` 후 구독을 열어두고 buyer가 실제 INSERT → **61ms만에 수신(PASS)**. 이어서 같은 키로 재INSERT → `23505` → 그 방+키 행 **정확히 1건** 확인. 프로브 행 정리 후 잔여 0건 확인.
- `npx playwright test viewport-audit write-flows` **23 passed / 10 skipped** — 패치 전과 동일(E4 두-브라우저 채팅 포함, 회귀 없음).

**Follow-up review recommendation:** `true`. 이번 패스 패치 12건 중 **high 1건**(멱등키 재사용 만료 없음) → 규칙상 `true`. (참고 점수: 3×medium 6 + 1×low 5 = 23.)

**DW 처리 결과:** `deferred-work.md`(동결)의 `DW-1`~`DW-5`가 모두 `status: open`이지만 실체는 이미 대장에 전부 이관돼 있다 — `DW-1`→`#148`, `DW-2`→`#149`, `DW-3`→`#164`, `DW-4`→`#184`, `DW-5`→`#192`. 신규 항목 없음, 동결 파일 무수정.

**대장(`docs/tech-debt.md`) 변경 없음:** defer 0건이라 신규 등재가 없다. 기존 항목도 무수정(이번 실행의 호출 지시가 기존 항목의 상태·해소를 오케스트레이터 소관으로 유보).

**사람 확인이 필요한 것(오케스트레이터/사용자 판단 영역):**
- 리뷰가 지적했으나 이번 실행 권한 밖이라 손대지 않은 것: 대장 `#169`(390px 채팅 오버플로)의 실행 항목은 이번 스토리가 실제로 다 수행했고, `#195`의 트리거("Story 12.3 착수 시")는 이미 도래해 `#199`가 답했으며, `#186`의 (c)항(재전송 1행 수렴을 실제 PostgREST 경로로 확인)은 이번 패스에서 **실측으로 확인됐다**(위 프로브: 23505 → 1행). 세 항목의 상태 갱신 여부는 오케스트레이터가 판단할 몫이다.

**Residual risks (이번 패스 기준 갱신):**
- 원격(운영) 전제 3건(`#195`·`#196`·`#197`)은 여전히 열려 있다 — 원격 적용 직전 확인 대상. 변동 없음.
- 재연결 시 갭 보정은 여전히 없다(Story 12.4). 다만 이제 연결이 끊기면 **화면에 남는 경고**가 뜨므로, 사용자가 "새로고침하면 복구된다"는 안전망을 실제로 인지할 수 있다(이전엔 콘솔에만 있었다).
- 실시간 송수신 전체의 **자동** E2E는 여전히 없다(의도적, Story 12.6 수동 검증). 다만 토픽·`private` 플래그·버블 줄바꿈은 이제 CI에서 도는 검사가 지킨다 — 이전엔 아무것도 없었다.
- web E2E는 여전히 CI에 없다(대장 `#168`) — 그래서 이번 패치의 회귀 가드를 E2E가 아니라 vitest 스캔에 둔 것이다.
