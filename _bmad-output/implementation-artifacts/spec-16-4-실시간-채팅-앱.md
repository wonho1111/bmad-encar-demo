---
title: '실시간 채팅 (앱)'
type: 'feature'
created: '2026-08-08'
status: 'done'
baseline_revision: 'd9d4f9ea531b03bd4e3f25e55a5f657c995706ef'
final_revision: '62d029d643da7735761fb5c93a0a8cce2de21145'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/implementation-artifacts/epic-16-context.md'
  - '{project-root}/docs/conventions.md'
warnings: ['multiple-goals', 'oversized']
---

<intent-contract>

## Intent

**Problem:** Flutter 앱 채팅(`app/lib/features/chat/`)은 여전히 3초 폴링(`chat_room_screen.dart`의 `Timer.periodic`)이다. 웹은 Epic 12에서 이미 멱등 전송(`client_message_id`)·Realtime Broadcast 구독·재연결 배너/오프라인 큐/갭보정·안읽음 배지+최신순 정렬을 전부 구현했고, `docs/conventions.md` §12·§12.5·§12.6이 "Epic 16.4가 그대로 미러링한다"고 여러 번 못박아 둔 단일 출처인데 아직 아무도 옮기지 않았다.

**Approach:** §12/§12.5/§12.6 계약과 DB 토대(`0022`~`0026`, 이미 배포됨)를 그대로 소비해 폴링을 Realtime 구독으로 교체한다. 방 생성 로직(`openOrCreateRoom`)은 Epic 12 이전부터 이미 웹과 동형이라 손대지 않는다.

## Boundaries & Constraints

**Always:**
- 구독 토픽은 `` 'chat:room:' + roomId `` — SQL(`0023_chat_realtime_broadcast.sql`)의 트리거·RLS 리터럴과 문자 그대로 동일해야 한다. Dart에서 이 문자열을 만드는 자리를 **한 곳**(`chat_repository.dart`의 top-level 함수, 예: `roomTopic(String roomId)`)으로 못박는다 — `docs/conventions.md` §12가 "Epic 16.4가 네 번째 사본을 만들면 그 검사에 한 줄을 더한다"고 지정한 대상이 이 함수다.
- 구독은 `supabase.channel(roomTopic(roomId), opts: RealtimeChannelConfig(private: true, replay: ReplayOption(since: <ms>, limit: 25)))` — `private: true`가 없으면 `realtime.messages` RLS(0023) 자체가 평가되지 않는다(실측: `~/.pub-cache/hosted/pub.dev/realtime_client-2.8.0/lib/src/types.dart` `RealtimeChannelConfig`/`ReplayOption`이 이 형태를 그대로 지원한다 — 웹처럼 불리언이 아니라 이미 타입이 맞다). `since`는 72시간 전(ms epoch, **우리가 고른 값**), `limit=25`(**라이브러리 상한**) — 두 값의 출처가 다르다는 사실을 코드 주석으로 옮긴다(§12.5).
- 수신은 `.onBroadcast(event: 'INSERT', callback: ...)` — `payload['record']`를 기존 `dedupeById` 머지 경로로 합류시킨다(도착 순서가 아니라 정렬 결과로 렌더). 방 진입 1회 전체 로드는 유지하고, **최초 `RealtimeSubscribeStatus.subscribed` 도달 시 한 번 더** 전체 로드해 "조회~구독 사이" 틈을 메운다(§12.3, 재연결마다가 아니라 최초 1회 한정).
- 멱등 전송: `sendMessage`가 호출부(화면)가 전송 시작 시점에 만든 `client_message_id`를 INSERT에 싣는다. `23505`(UNIQUE(room_id, client_message_id))는 에러로 올리지 않고 `(room_id, client_message_id)`로 기존 행을 재조회해 그 행을 반환한다 — 단, `sender_id`·`body`가 호출자 값과 일치할 때만 성공으로 취급(§12.4, web `sendMessage` 133-154행과 동일 방어).
- 재연결 판단은 `RealtimeSubscribeStatus.channelError`/`timedOut`(끊김) ↔ `subscribed`(재연결, 이전에 끊긴 적 있을 때만)만 본다. `closed`는 기존처럼 별도 취급하고 재연결 배너 대상에 넣지 않는다(§12.5).
- 끊김 배너(비차단, `AppColors.warnAmberBg`/`warnAmberInk`): "연결이 끊겼어요. 다시 연결 중… 메시지는 계속 작성할 수 있어요." 재연결 배너(`AppColors.trustGreenBg`/`trustGreenInk`): "다시 연결됐어요" → 3000ms 후 자동 소멸. 색+텍스트 동시 표기(비색 신호 중복).
- 끊긴 동안 입력창·전송 버튼·연타가드를 잠그지 않는다 — 연타 가드(`sending`)는 **온라인 경로 전용**이다(web `disabled={(sending && !isDisconnected) || loading}` 미러).
- 오프라인 큐잉: 끊긴 동안 제출은 네트워크 호출을 시도하지 않고 즉시 pending 버블 + 인메모리 큐(순서 보존)에 적재, 재연결 시 순차(순서대로 await) flush. 큐잉 시점의 `client_message_id`를 그대로 재사용(새 키 생성 금지). 실패 항목(과 그 뒤 전부)은 remaining으로 남겨 다음 재연결 때 재시도.
- 재연결마다 두 경로를 **항상 함께** 수행: ① 채널 config의 `replay`(별도 소비 코드 불필요, 기존 `onBroadcast` 핸들러가 그대로 받음) ② 마지막으로 반영한 메시지의 `created_at`을 커서로 `fetchMessages(roomId, atOrAfterCreatedAt: cursor)` 재조회(`gte`, 백스톱 — replay 커버 여부와 무관하게 항상 돈다).
- 큐 flush가 다 못 보내면 몇 건 남았는지 화면에 남긴다(전송 에러 칸과 분리된 별도 칸 — 다음 제출 때 지워지면 안 된다).
- 방 진입 시 `chat_room_reads.last_read_at`을 지금 시각으로 **1회만** upsert한다 — 반드시 `myId == room.buyerId || myId == room.sellerId`로 직접 대조한 뒤에만 호출한다(§12.6, "방 조회 성공"과 "당사자"는 다른 것 — admin RLS가 OR로 합쳐지는 함정과 같은 축). 방이 열려 있는 동안 실시간 수신마다 재호출하지 않는다.
- `chat_rooms.last_message_at` 컬럼으로 목록을 정렬(`fetchRooms`의 select·order를 `last_message_at desc, id desc`로 교체 — 현재는 `created_at`으로 정렬돼 있어 §12.6과 어긋난다).
- 안읽음 배지 2곳: ① 하단 채팅 탭 아이콘에 총합(`chat_unread_count()` RPC, 0이면 미표시, 99 초과는 "99+"로 절삭하되 시맨틱 라벨은 정확한 건수) ② 채팅 목록 각 행에 방별 배지(`chat_unread_by_room()` RPC, 0건인 방은 미표시). 둘 다 **다음 진입/로드 시점 기준**이지 실시간 감소가 아니다(§12.6 — DW-548로 사용자 결정에 의해 방별 배지가 추가됐으므로 웹처럼 둘 다 구현한다).
- `docs/conventions.md` §12.6의 "방 목록 각 행에 개별 안읽음 표시를 두지 않는다(Never)" 문구는 **DW-548(2026-07-29)로 사용자 결정에 의해 뒤집혀 웹에 이미 구현돼 있다**(`web/src/app/(user)/chat/page.tsx` 83-93행·141행). 이 문구를 정정하고 앱의 미러링 사실을 등록한다(코드가 정본 — spec-16-3 Design Notes와 같은 종류의 문서 드리프트).
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts`에 Dart `roomTopic()`을 읽어 SQL 접두사와 비교하는 검사를 한 줄 추가한다(이 파일 자신의 주석·`docs/conventions.md` §12가 지정한 자리).

**Block If:** (없음 — 계약·DB 토대·웹 레퍼런스 구현이 전부 이미 확정돼 있다.)

**Never:**
- 폴링(`Timer.periodic`) 재도입 또는 유지 금지 — 이번 스토리가 걷어내는 대상 그 자체.
- 수동 재구독·채널/소켓 재생성 코드 금지 — 라이브러리(`realtime_client`)의 자동 rejoin에 의존한다(§12.5 Never 미러).
- `connectivity_plus` 등 OS 네트워크 상태 API로 연결 여부를 판단하지 않는다 — 채널 status 콜백 하나로 충분하다(§12.5, web의 `navigator.onLine` 미사용과 동일 원칙).
- 오프라인 큐 영속화(로컬 DB·`shared_preferences` 등) 금지 — 인메모리만. 방 이탈·앱 종료 시 큐 유실은 감수한 손실이다(§12.5, 새로고침 복구 불가와 동일).
- `openOrCreateRoom`(방 생성/재사용) 로직 변경 금지 — Epic 12 이전부터 이미 웹과 동형이고 이번 스토리 범위 밖이다.
- 새 마이그레이션·RLS 작성 금지 — `0022`~`0026`이 이미 존재.
- 관리자 채팅 화면(웹 `(admin)/admin/chats`) 미러링 금지 — 앱에 관리자 화면 자체가 없다(범위 밖).
- 웹의 `onAuthStateChange → setAuth` 수동 재호출 로직을 그대로 이식하지 않는다 — Dart `realtime_client`는 매 rejoin마다 `socket.accessToken`으로 자동 재인증한다(Design Notes 근거 실측). 이 사실을 검증 없이 "당연히 이식"하면 없어도 될 상태 배선이 하나 늘어난다.
- 옵션 희소도 표시(대장 #5452, 16.3이 미구현으로 남긴 에픽 AC 절)를 이 스토리로 흡수하지 않는다 — 별도 미해결 사용자 결정 사항이고 채팅과 무관하다.
- 채팅 메시지 최대 길이(2000자)의 클라이언트 측 사전 안내 문구를 이번에 새로 넣지 않는다 — 이 갭은 이번 스토리 이전부터 있었고(현재 Dart `sendMessage`엔 길이 가드가 전혀 없다), DB CHECK가 이미 최종 방어선이라 데이터 무결성 위험은 없다. 별도로 다룰 사안이며 이 스토리가 만든 결함이 아니다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 정상 전송 | 연결 정상, 메시지 입력 후 전송 | 즉시 pending 버블 → INSERT 성공 시 실제 행으로 교체 | 실패 시 한국어 에러 + 입력 복원(입력창이 비어 있을 때만) |
| 재전송(네트워크 재시도) | 동일 `client_message_id`로 재INSERT | `23505` → 기존 행 재조회해 그 행으로 수렴(중복 행 없음) | sender_id/body 불일치 시 일반 에러로 폴백 |
| 상대 메시지 실시간 수신 | 상대가 메시지 전송 | 폴링 없이 broadcast로 즉시 반영(정렬 결과로 렌더, 도착 순서 무관) | 최초 SUBSCRIBED 1회 보정 로드가 구독 이전 틈을 메움 |
| 연결 끊김 | `channelError`/`timedOut` | 비차단 배너, 입력·전송 계속 가능 | 끊긴 동안 제출은 네트워크 호출 없이 즉시 pending+로컬 큐 적재 |
| 재연결 | `subscribed`(이전에 끊긴 적 있음) | 초록 배너(3초 후 소멸) + 큐 순차 flush + 커서 갭보정 병행 | 큐 일부 실패 시 남은 건수 안내(전송 에러 칸과 분리), remaining 보존 |
| 방 이탈(끊긴 채, 큐에 항목 존재) | 오프라인 큐 비어있지 않음 | 큐 유실(인메모리, 감수한 손실) | 없음(설계된 동작) |
| 방 진입(당사자) | `myId == buyerId or sellerId` | `chat_room_reads.last_read_at` 1회 upsert | 실패해도 화면 안 막음(콘솔 로그만) |
| 채팅 탭 진입 | 로그인 사용자 | 목록이 `last_message_at desc, id desc` 정렬, 방별 안읽음 배지(0건 미표시) | 목록 조회 실패 시 기존 에러 안내 유지 |
| 내비 채팅 아이콘 안읽음 | 총합 > 0 | 배지 숫자(99+ 상한, 시맨틱 라벨은 정확한 건수) | RPC 실패 시 배지 미표시(콘솔 로그만, 렌더 자체는 안 막음) |

</intent-contract>

## Code Map

- `app/lib/features/chat/chat_models.dart` -- `ChatMessage`에 `clientMessageId`(String?) 필드+`fromMap` 파싱 추가, `ChatRoomSummary`에 `lastMessageAt`(String) 필드 추가, 오프라인 큐 항목용 소형 `QueuedChatMessage`(clientMessageId, body) 클래스 신설
- `app/lib/features/chat/chat_repository.dart` -- `roomTopic(roomId)` top-level 함수(토픽 문자열 단일 출처) 신설, `sendMessage`에 `clientMessageId` 매개변수 추가+23505 재조회 수렴 로직, `fetchRooms` select·order를 `last_message_at`으로 교체, `fetchUnreadTotal()`(`chat_unread_count` RPC)·`fetchUnreadByRoom()`(`chat_unread_by_room` RPC, Map<String,int> 반환)·`markRoomRead(roomId)`(`chat_room_reads` upsert) 신설, 순수 함수 `reuseFailedKey(...)`·`flushChatMessageQueue(...)`(web `messages.ts` 미러) 신설
- `app/lib/features/chat/chat_providers.dart` -- `chatUnreadTotalProvider`(non-autoDispose FutureProvider, 내비 배지)·`chatUnreadByRoomProvider`(FutureProvider.autoDispose, 목록 배지) 신설
- `app/lib/features/chat/chat_room_screen.dart` -- `Timer.periodic` 폴링 전면 제거, Realtime 채널 구독(`private:true`+`replay`)·상태 콜백(끊김/재연결 배너)·오프라인 큐+순차 flush·갭보정(커서 재조회)·`markRoomRead` 1회 호출 배선. 상태 전이 반응(배너·disabled·flush 트리거)을 위젯 바깥에서 직접 호출 가능한 형태로 분리해 위젯테스트가 실제 소켓 없이 시뮬레이션할 수 있게 한다
- `app/lib/features/chat/chat_list_screen.dart` -- 각 행에 `chatUnreadByRoomProvider` 결과로 방별 안읽음 배지 추가(0건이면 미표시)
- `app/lib/core/router/app_router.dart` -- `tab_chat`의 `NavigationDestination` 아이콘을 `chatUnreadTotalProvider` 값으로 `Badge` 래핑, `onActivate`에 `chatUnreadTotalProvider`·`chatUnreadByRoomProvider` invalidate 추가
- `docs/conventions.md` §12 -- 도입부에 Dart 네 번째 사본(위치: `chat_repository.dart`의 `roomTopic()`) 등록
- `docs/conventions.md` §12.6 -- "방별 개별 안읽음 표시를 두지 않는다(Never)" 문구를 DW-548 반전 경위로 정정 + 앱 미러링 파일 등록
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts` -- Dart `roomTopic()` 소스 문자열을 읽어 SQL 접두사와 비교하는 검사 1건 추가(파일 자신의 주석이 지정한 자리)
- `app/test/chat_model_test.dart` -- `clientMessageId`/`lastMessageAt` 파싱 단언 확장(기존 파일)
- `app/test/chat_repository_test.dart` (신규) -- `roomTopic` 형식·`reuseFailedKey` 4분기(없음/본문불일치/시간초과/유효재사용)·`flushChatMessageQueue`(전부성공/부분실패시 순서·remaining 보존/예외를 실패로 흡수) 단위테스트
- `app/test/chat_room_screen_test.dart` (신규) -- 가짜 레포(`_FakeChatRepository extends ChatRepository`, app_router_test.dart의 기존 `_FakeChatRepo` 패턴 재사용)로 초기 로드·전송·pending 버블·참여자일 때만 markRoomRead 호출을 검증, 상태-콜백 시뮬레이션으로 배너·disabled·큐 flush 반응 검증
- `app/test/app_router_test.dart` -- 채팅 탭 `onActivate`가 새 안읽음 provider들도 invalidate하는지 배선 단언 추가(기존 파일)

## Tasks & Acceptance

**Execution:**
- `app/lib/features/chat/chat_models.dart` -- 필드·클래스 추가 -- 멱등키·정렬·큐 데이터 계층
- `app/lib/features/chat/chat_repository.dart` -- 토픽 함수·멱등 전송·정렬·안읽음 RPC·읽음 upsert·순수 큐 함수 -- §12/§12.4/§12.5/§12.6 소비의 단일 출처
- `app/lib/features/chat/chat_providers.dart` -- 안읽음 provider 2종 -- 배지 공급
- `app/lib/features/chat/chat_room_screen.dart` -- 폴링→Realtime 전환, 배너·큐·갭보정·읽음 배선 -- §12/§12.5 핵심 AC
- `app/lib/features/chat/chat_list_screen.dart` -- 방별 배지 -- §12.6 AC
- `app/lib/core/router/app_router.dart` -- 내비 배지+invalidate 확장 -- §12.6 AC
- `docs/conventions.md` -- §12 4번째 사본 등록 + §12.6 정정 -- B8/B9 정본 유지
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts` -- Dart 검사 추가 -- 4곳 리터럴 드리프트 방지
- `app/test/chat_model_test.dart`·`chat_repository_test.dart`·`chat_room_screen_test.dart`·`app_router_test.dart` -- 단위·위젯테스트 -- I/O 매트릭스·순수 함수·배선 커버리지

**Acceptance Criteria:**
- Given 두 당사자가 같은 방에 있고, when 한쪽이 메시지를 보내면, then 폴링 없이 상대 화면에 곧바로 반영된다(토픽 `chat:room:{roomId}`, private+broadcast).
- Given 네트워크 재시도로 같은 `client_message_id`가 두 번 INSERT되면, when 두 번째 요청이 도착하면, then `chat_messages`엔 정확히 1행만 남고 클라이언트는 성공으로 본다.
- Given 실시간 구독이 끊기면, when 사용자가 계속 메시지를 입력·전송하면, then 입력·전송 버튼은 잠기지 않고 메시지는 로컬 큐에 쌓인다.
- Given 재연결되면, when 큐에 대기 항목이 있으면, then 순서대로 flush되고(같은 키 재사용), 상대가 끊긴 동안 보낸 메시지도 갭보정으로 누락 없이 채워진다.
- Given 로그인 사용자가 자신이 당사자인 방에 진입하면, when 진입이 완료되면, then 그 시각으로 읽음이 1회 기록되고, 채팅 탭 배지·해당 방의 목록 배지가 다음 진입 시점에 그만큼 줄어든다.
- Given 채팅 탭을 열면, when 여러 방이 있으면, then 마지막 메시지가 가장 최근인 방이 맨 위에 온다.

## Spec Change Log

## Review Triage Log

### 2026-08-08 — Review pass (후속 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 13 (high 1, medium 3, low 9)
- defer: 1 (high 0, medium 1, low 0)
- reject: 7 (high 0, medium 0, low 7)
- addressed_findings:
  - `[high]` `[patch]` **실시간 수신이 아예 동작하지 않았다** — `handleBroadcastInsert`가 브로드캐스트 봉투를 한 단계 얕게 읽어(`payload['record']`) 실제 방송이 오면 항상 `record == null`로 조기 return했다. `realtime_client-2.8.0`의 콜백은 안쪽 payload가 아니라 `{'type','event','payload'}` 전체 봉투를 넘긴다(실측: 라이브러리 자신의 `test/socket_test.dart:588-593`·`:594-625`가 정확히 이 형태를 단언). `docs/conventions.md` §12.3도 `message.payload.record`라고 못박아 뒀고 web도 그렇게 읽는다 — 스펙 intent-contract의 `payload['record']` 표기가 §12.3을 옮겨 적으며 한 단계를 흘린 것이고, §12.3이라는 단일 출처가 명확하므로 해석은 하나뿐이라 patch로 처리했다. 이번 스토리가 폴링 백스톱을 걷어냈으므로 상대 메시지는 방을 나갔다 다시 들어오기 전까지 영영 오지 않는 상태였다. `extractBroadcastRecord()` 순수 함수로 분리해 `payload['payload']['record']`를 방어적으로 읽도록 수정. 이 결함이 1차 리뷰를 통과한 이유는 **위젯테스트가 프로덕션 코드와 똑같이 틀린 모양을 스스로 만들어 넣어** 계약을 검사하는 게 아니라 정의하고 있었기 때문 — 그래서 테스트 페이로드를 실제 봉투 모양으로 고치고, 추가로 실제 `realtime_client`의 디스패치 경로(`RealtimeClient.onConnMessage`에 진짜 프레임 투입, 소켓 불필요)를 태우는 `app/test/chat_realtime_envelope_test.dart`를 신설했다(적용 에이전트가 함수 본문 변형으로 red/green 확인, 오케스트레이터가 **다른 형태**로 재검증 — 호출부를 원래 버그 표현으로 되돌려 red 2건 → 원복 green 24건)
  - `[medium]` `[patch]` 방을 열고 뒤로 나오는 **가장 흔한 경로**에서 안읽음 배지가 안 줄었다 — `chat_list_screen.dart`의 pop 복귀 훅이 `chatRoomsProvider`만 무효화하고 이번 스토리가 새로 만든 배지 provider 2종은 빼먹었다. 사용자는 이미 채팅 탭에 있으므로 탭 `onActivate`도 다시 안 돌아, "방 읽었는데 배지는 그대로"가 계속 남는다(스펙 AC "배지가 다음 진입 시점에 그만큼 줄어든다" 미충족). 바로 그 자리의 주석이 spec-16-1 P2에서 똑같은 결함을 고쳤다고 적어둔 곳인데 새 provider가 그 패턴을 다시 물려받았다 — 세 provider 모두 무효화 + 복귀 후 재조회 단언 테스트 추가
  - `[medium]` `[patch]` 온라인 전송 응답을 기다리는 도중 연결이 끊기면 그 메시지가 **조용히 증발**했다 — 끊기면 입력창이 즉시 다시 열리므로(연타가드는 온라인 전용) 사용자가 다음 글을 타이핑하고, 그 상태에서 앞선 전송이 실패하면 pending 버블은 지워지고 큐에도 안 들어가며 본문 복원도 "입력창이 비어있을 때만" 규칙에 걸려 안 된다 — 실패 시점에 끊겨 있으면 같은 `client_message_id`로 큐에 남겨 재연결 flush가 가져가도록 수정(복원 규칙 자체는 스펙 명시라 그대로 둠)
  - `[medium]` `[patch]` 실제 구독 배선(`_defaultChatSubscribe`)이 **어떤 테스트로도 실행되지 않고**, 유일한 정적 앵커 검사도 `private: true`까지만 보고 `replay: ReplayOption(...)`·`onBroadcast(event:'INSERT')`·`subscribe(onStatus)`는 안 봤다 — 위 high 결함이 통과한 구조적 이유다(verification-gap·intent-alignment 독립 지적). 앵커를 세 자리까지 넓히고 `'INSERT'` 리터럴을 0023이 방송하는 이벤트와 대조. 기존 `stripDartLineComments` 방어는 유지
  - `[low]` `[patch]` `_flushQueue`가 `senderId: _myId ?? ''`로 빈 문자열을 지어내 보냈다 — `_send()`는 같은 조건에서 아예 중단하는데 두 경로가 전제를 다르게 봤다(adversarial·edge-case-hunter 독립 발견). `myId == null`이면 큐를 그대로 남기고 중단하도록 통일
  - `[low]` `[patch]` 세션이 없을 때 `_subscribeRealtime()`이 배너도 에러도 없이 조용히 return했다 — 폴링이 없어진 지금 방은 멀쩡해 보이면서 아무것도 못 받는다(adversarial·edge-case-hunter 독립 발견). 바로 아래 catch와 같은 톤으로 `_realtimeError`를 세우도록 수정
  - `[low]` `[patch]` 한 번 끊긴 적이 있으면 `subscribed`가 와도 `_realtimeError`가 안 지워져, 빨간 "연결이 끊겼습니다"가 초록 "다시 연결됐어요" 위에 그대로 남을 수 있었다 — 분기 앞으로 옮겨 항상 지우도록 수정
  - `[low]` `[patch]` `docs/conventions.md` §12.2가 "구독 전 `setAuth` 필수, 내부 동작에 기대지 않는다"고 명령형으로 못박아 뒀는데 Dart 구현은 의도적으로 둘 다 안 하고(스펙 Design Notes 실측 + Never 절이 이식 금지), §12.2엔 그 예외가 아무 데도 안 적혀 있었다 — 다음에 §12를 미러링하는 사람이 코드와 계약 중 뭘 따를지 동전을 던지게 된다(CLAUDE.md B8). §12.1·§12.4·§12.6이 이미 쓰는 "✎" 형식으로 Dart 예외를 실측 근거(파일·행)와 함께 등재(문서만, 코드 무변경)
  - `[low]` `[patch]` 방 목록 타일 제목에 `maxLines`/`overflow`가 없는데 이번에 그 행에 배지+여백을 끼워 넣어 폭을 좁혔다 — 규칙 13(D5)이 요구하는 truncate 대신 줄바꿈으로 흡수될 수 있었다. `maxLines: 1` + 말줄임 추가 + 320dp 좁은 폭에 긴 제목·3자리 배지를 함께 렌더하는 테스트 추가
  - `[low]` `[patch]` `fetchRooms`의 `last_message_at desc, id desc` 정렬(FR57/§12.6)이 Dart 쪽에서 아무 검사에도 안 걸려 있었다 — `created_at`으로 되돌려도 전부 green. web이 같은 계약을 정적 소스 스캔으로 고정한 기법(`unreadWiringContract.test.ts`)을 Dart에 그대로 이식
  - `[low]` `[patch]` 지난 패스가 넣은 "계정 전환 시 이전 사용자 배지 잔존 방지" 배선(`authStateProvider` → invalidate)이 무검증이었다 — 실제 인증 이벤트를 흘리는 테스트 2개가 상수 override라 조회 횟수를 안 봤다. 카운팅 override로 바꿔 재조회를 단언
  - `[low]` `[patch]` `markRoomRead`의 upsert 인자·`onConflict: 'user_id,room_id'`가 무검증이었다 — 틀려도 catch가 콘솔로 삼켜 "배지가 영영 안 줄어듦"이 조용히 지나간다. web의 동일 테스트(`chat.test.ts`) 기법을 미러링해 가짜 http 클라이언트로 실제 요청(경로·쿼리·헤더·본문)을 단언
  - `[low]` `[patch]` `_lastFailed` → `reuseFailedKey` 배선이 무검증이었다(순수 함수만 테스트) — 그 대입을 지워도 green이고, 실제 결과는 `UNIQUE(room_id, client_message_id)`를 못 걸고 **같은 메시지가 두 행** 남는 것이다. 실패 후 같은 본문 재전송 시 같은 키 재사용 / 다른 본문은 새 키를 단언하도록 확장
- deferred (장부에 신규 등재):
  - `[medium]` 앱에 채팅 2000자 클라이언트 가드가 전혀 없고 `23514`를 무조건 "빈 메시지"로 안내한다(§7의 3중 방어 중 DB 한 겹만 존재) — 이번 스토리 이전 리비전에서 이미 그랬음을 직접 확인했고 스펙 Never가 명시적으로 범위에서 뺐다. 다만 이번에 도입한 오프라인 큐 때문에 영향이 커졌다(초과 메시지 1건이 큐 머리에 박히면 뒤의 정상 메시지까지 재연결마다 영원히 막힌다)
- rejected_as_noise (기록용, 근거 포함):
  - 큐 flush에 재시도 상한·항목 폐기 경로가 없어 영구 실패 항목이 뒤를 막는다 — 스펙 Always가 "실패 항목(과 그 뒤 전부)은 remaining으로 남겨 다음 재연결 때 재시도"라고 이 동작을 그대로 규정했다(영구 실패를 만드는 유일한 실제 원인인 길이 초과는 위 defer로 등재)
  - 초기 로드를 `await`한 뒤 구독을 시작해 "조회~구독" 틈이 넓어진다 — §12.3이 그 틈을 메우려고 둔 "최초 SUBSCRIBED 1회 재조회"가 이미 설계상 커버하는 지점이다
  - 내비 배지가 실시간으로 오르지 않아 알림 역할을 못 한다 — 스펙 Always가 "둘 다 다음 진입/로드 시점 기준이지 실시간 감소가 아니다"라고 규정한 동작이다
  - 방이 열려 있는 동안 도착한 메시지가 읽음 처리되지 않는다 — 스펙 Always 명시(1차 패스에서도 같은 근거로 기각)
  - `markRoomRead`가 기기 시각을 쓴다 — web `markChatRoomRead`도 동일(1차 패스 기각 유지)
  - `docs/conventions.md` §12.6이 뒤집힌 Never와 현행 규칙을 동시에 살려 자기모순이다 — 실제 문서를 직접 읽어 반증했다: 옛 문구는 규범 자리에서 빠지고 "예전에 …라고 적어 뒀었다"는 과거형 인용으로만 남았으며 문단이 "지금 정본은 … 세 가지 전부다"로 닫힌다(§12.4가 이미 쓰는 "✎ 정정" 관례와 동일 형식)
  - `_markReadIfParticipant`가 `build()`의 `chatRoomDetailProvider`와 같은 행을 한 번 더 조회한다 — 방 진입마다 중복 왕복 1회일 뿐 사용자에게 드러나는 결과 차이가 없다

### 2026-08-08 — Review pass (1차)
- intent_gap: 0
- bad_spec: 0
- patch: 9 (high 0, medium 5, low 4)
- defer: 4 (high 0, medium 4, low 0)
- reject: 18 (high 0, medium 0, low 18)
- addressed_findings:
  - `[medium]` `[patch]` `chatUnreadTotalProvider`(내비 배지, non-autoDispose)가 채팅 탭 activate에서만 invalidate돼, 계정 A 로그아웃 → 계정 B 로그인(앱 재시작 없이) 경로에서 B가 채팅 탭을 누르기 전까지 A의 안읽음 숫자가 남아 보였다(adversarial 렌즈 발견, 새로 만든 provider가 기존 provider들의 로그아웃 미정리 패턴을 그대로 물려받은 것) — `appRouterProvider`의 `ref.listen(authStateProvider, ...)`에서 함께 invalidate하도록 배선
  - `[medium]` `[patch]` `_subscribeRealtime()`이 `_defaultChatSubscribe`(또는 override) 호출을 try/catch 없이 해, 구독 시작 자체가 동기 예외를 던지면(`unawaited(_startRoom())` 경로라 조용히 묻힘) 사용자에게 아무 배너 없이 방이 죽었다(adversarial 렌즈 발견) — try/catch로 감싸 다른 실패 경로와 같은 톤의 `_realtimeError` 세팅
  - `[medium]` `[patch]` `_queueStuckNotice`(오프라인 큐 일부 미전송 안내)가 `_flushQueue()` 안에서만 set/clear되는데, `handleBroadcastInsert`도 pending 항목을 지울 수 있어(브로드캐스트 에코로 뒤늦게 확인) 그 경로로 항목이 빠지면 안내 문구가 실제보다 많은 건수로 남을 수 있었다(adversarial·edge-case-hunter 독립 발견) — `_refreshQueueStuckNotice()`를 신설해 `handleBroadcastInsert`에서도 현재 큐 상태로 재계산
  - `[medium]` `[patch]` 오프라인 큐 "일부 전송 실패" UI(안내 문구+"다시 보내기" 버튼)가 어떤 테스트로도 실행되지 않았다(verification-gap·edge-case-hunter 독립 발견, 기존 재연결 테스트는 전부-성공 경로만 검증) — 재연결 시 큐 2건 중 1건만 실패시켜 정확한 남은 건수·재시도 버튼 배선을 확인하는 테스트 추가
  - `[medium]` `[patch]` 갭보정(재연결 시 커서 재조회) 실패→복구 시나리오가 테스트되지 않았다(verification-gap 렌즈 발견, 가짜 레포가 `fetchMessages`를 실패시킬 방법이 없었음) — `_FakeChatRepository`에 `fetchMessagesShouldFail` 훅 추가 + "갭보정 실패→에러 표시→재연결→갭보정 성공→에러 소멸"(§12.5 "자기가 세운 안내만 거둔다") 시나리오 테스트 추가
  - `[low]` `[patch]` `roomTopicContract.test.ts`의 Dart 네 번째 사본 검사가 `roomTopic()` 함수 자신의 본문만 SQL과 대조하고, `_defaultChatSubscribe`가 실제로 그 함수를 `supabase.channel(...)` 호출부에서 쓰는지는 안 봤다(adversarial 렌즈 발견) — 호출부에 앵커한 검사 추가. 처음 구현이 doc comment의 인용문에 우연히 매치돼 실제 코드를 망가뜨려도 통과하는 거짓양성을 스스로 실측해 발견하고 `stripDartLineComments`로 재수정(패치 적용 에이전트 자체 실측)
  - `[low]` `[patch]` `chat_list_screen_test.dart`의 방별 안읽음 배지 테스트가 내비 배지 테스트(app_router_test.dart)와 달리 99+ 상한·스크린리더 라벨을 검증하지 않았다(verification-gap·adversarial 독립 발견) — 같은 두 케이스 추가
  - `[low]` `[patch]` `fetchUnreadByRoom()`의 RPC 응답 매핑(row 형태·room_id·unread 타입 가드)이 어떤 테스트로도 실행되지 않아, 응답 형태가 바뀌어도(예: 컬럼명 변경) 아무도 못 잡았다(adversarial 렌즈 발견) — `parseUnreadByRoomRows()` 순수 함수로 추출 + 정상/List아님/Map아님/room_id 이상/unread 이상 5케이스 단위테스트
  - `[low]` `[patch]` `docs/conventions.md` §12.6이 앱의 `AppColors.danger`가 web `bg-red-600`과 "정확히 같은 hex는 아니다"라면서도 실제 대비값을 안 적어 CLAUDE.md B4("재보기 전엔 선언하지 않는다")를 그 자리에서 스스로 어겼다(adversarial 렌즈 발견, 오케스트레이터가 직접 계산해 5.44:1 확인 — AA 4.5:1 충족, web 4.83:1보다도 높음) — 문서에 계산값 명시
- deferred (장부에 신규 등재):
  - `[medium]` 최초 `SUBSCRIBED` 재조회 성공이 그 이전 초기 로드 실패 안내(`_loadError`)를 안 지운다 — 다만 web `ChatRoomMessages.tsx`의 동일 블록도 똑같은 특성이라(직접 대조 확인) 미러링 원칙상 app만 단독으로 고치면 드리프트가 생긴다(edge-case-hunter 렌즈 발견)
  - `[medium]` 앱 백그라운드→포그라운드 복귀 시 소켓이 상태 콜백 없이 조용히 멎는 경우를 잡을 생명주기 훅(`WidgetsBindingObserver`)이 없다 — 실기기 검증 없이는 실제로 문제가 되는지 확인 불가(edge-case-hunter 렌즈 발견)
  - `[medium]` 폴링 백스톱 제거로 "소켓이 상태 콜백 없이 죽으면 복구 경로가 없다"는 위험이 남는다 — 다만 스펙 Never 절과 web §12.5가 이미 명시적으로 감수한 절충이다(edge-case-hunter 렌즈 발견)
  - `[medium]` 스펙의 Manual checks(로컬 Supabase 2계정 실시간 송수신·재연결 실측)가 이 세션(헤드리스 샌드박스, CanvasKit 크래시)에서 실행되지 못했다 — intent-alignment 렌즈가 "실행됐다는 증거가 스펙 어디에도 없다"고 독립 지적
- rejected_as_noise (기록용, 근거 포함):
  - `chat_rooms.last_message_at`이 NULL일 때 정렬에서 맨 앞으로 밀린다(edge-case-hunter 렌즈 발견) — 실측 결과 거짓 전제였다: `0024_chat_room_reads.sql`이 이 컬럼을 `not null default now()`로 선언해 NULL이 될 수 없다
  - 방이 열려있는 동안 실시간 메시지가 와도 읽음을 재갱신하지 않는다(edge-case-hunter 렌즈 발견) — 스펙 Always 절이 "실시간 수신마다 재호출하지 않는다"고 명시했고 web `docs/tech-debt.md` #210과 동일한 이미 수용된 edge case
  - 배지가 방을 나가도 즉시 안 줄고 탭 재진입 시점에만 줄어든다(edge-case-hunter 렌즈 발견) — 스펙 Always 절이 "다음 진입/로드 시점 기준"이라고 명시적으로 규정한 동작
  - `closed` 상태가 `channelError` 이후 온다면 큐가 영원히 flush 안 될 수 있다(edge-case-hunter 렌즈 발견) — web `docs/conventions.md` §12.5가 실측(`realtime-js` 2.108.2 소스)으로 이미 "CLOSED는 명시적 leave에서만 발생"이라고 못박은 설계이고 Dart 코드도 동일 근거의 주석을 그대로 인용
  - 브로드캐스트 메시지에 room_id 필터가 없어 다른 방 메시지가 섞일 수 있다(edge-case-hunter 렌즈 발견) — web `ChatRoomMessages.tsx`도 동일하게 필터가 없다(직접 대조), 토픽 자체가 방을 격리하는 플랫폼 보장에 의존하는 설계를 그대로 미러링한 것
  - `_myId`를 `ref.watch`가 아니라 `ref.read`로 읽어 세션 중 사용자 변경에 반응 안 한다(edge-case-hunter 렌즈 발견) — 라우터 redirect가 인증 상태 변화 시 이 화면을 이미 unmount시키므로 실사용에서 도달 불가(다른 화면들과 동일 전제)
  - 재연결 시 세션이 만료돼 있으면 빈 sender_id로 flush를 시도해 전부 RLS 거부된다(edge-case-hunter 렌즈 발견) — 실측 결과 이미 존재하는 `_queueStuckNotice` 일반 안내로 사용자에게 노출되며(완전 침묵 아님), 라우터 redirect로 이 시나리오 자체가 실사용에서 도달하기 어렵다
  - 온라인 전송 실패 시 사용자가 이미 새 글자를 입력해뒀으면 실패한 메시지 본문이 사라진다(edge-case-hunter 렌즈 발견) — web이 3차 후속 리뷰로 명시적으로 채택한 "입력창이 비어있을 때만 복원" 규칙을 그대로 미러링한 것(스펙 Always 절에 명시)
  - 오프라인 큐에 상한이 없다(edge-case-hunter 렌즈 발견) — web 원본도 동일하게 무제한이고 데모 규모에서 스펙이 요구하지 않은 범위
  - 23505 재조회가 다시 실패하면 실제로 저장된 메시지가 잠깐 "실패"로 보인다(adversarial 렌즈 발견) — 코드를 직접 추적한 결과 브로드캐스트 에코 도착 시 `_lastFailed`·`_error`가 자동으로 정리되는 기존 자기치유 경로가 이미 있어 자연 복구된다
  - `_markReadIfParticipant`의 실패가 print만 하고 재시도 없다(adversarial 렌즈 발견) — 스펙 Always 절이 "실패해도 화면을 막지 않는다(콘솔 로그만)"고 정확히 이 동작을 요구했다
  - `_landedKeys` Set이 화면 수명 내내 안 줄어든다(adversarial 렌즈 발견 — 다만 발견자 스스로도 "메시지 목록과 같은 증가율이라 특별히 더 나쁘지 않다"고 인정)
  - 테스트가 진짜 동시성(레이스)을 시뮬레이션하지 않고 순차 시나리오만 돈다(adversarial 렌즈 발견) — 실제 결함을 지목한 것이 아니라 테스트 방법론에 대한 일반적 지적이고, 이 레포의 다른 위젯테스트들도 같은 한계를 공유한다
  - 내비 배지 시맨틱 테스트의 정규식이 느슨하게 매칭한다(adversarial 렌즈 발견) — 테스트 엄밀성 지적일 뿐 실제 사용자 영향이 증명되지 않았다
  - `sendMessage()`의 23505 재조회 경로 자체(실제 네트워크 호출 포함)가 단위테스트되지 않는다(adversarial 렌즈 발견) — `isIdempotentResendMatch`로 판정 로직만 추출해 테스트하는 이 레포의 기존 관례(`wishlist_repository.dart`)를 그대로 따른 것이고, 이번 패스에서 이미 그 순수함수 테스트를 추가했다
  - `markRoomRead`가 서버 `DEFAULT now()`가 아니라 기기 시각(`DateTime.now()`)을 쓴다(edge-case-hunter 렌즈 발견) — web `markChatRoomRead`도 `new Date().toISOString()`으로 동일하게 기기 시각을 쓴다(직접 대조), 1:1 미러링
  - `roomTopicContract.test.ts`의 새 정규식이 주석 안 텍스트에 오매칭할 이론적 위험이 있다(edge-case-hunter 렌즈 발견) — 이번 패스에서 이미 `stripDartLineComments`로 실제로 막았다(패치 6 참조)
  - `Key('chat_error')`→`Key('chat_load_error')` 분리가 가상의 외부 E2E 셀렉터를 깰 수 있다(edge-case-hunter 렌즈 발견, 발견자 스스로 "확신도: 낮음") — 이 레포에 그 키를 참조하는 실제 E2E가 없음을 확인(웹 전용 Playwright, 앱은 위젯테스트뿐)

## Design Notes

**Dart `State` 필드는 React ref 미러링이 필요 없다.** 웹 구현은 `pendingQueueRef`·`lastMessageAtRef`·`disconnectedRef` 등 다수의 `useRef`로 "콜백이 stale closure를 읽는" React 특유의 문제를 우회한다. Flutter `StatefulWidget`의 인스턴스 메서드는 항상 `this.field`의 **현재** 값을 읽으므로(클로저 캡처 문제가 없음), 이 ref 미러링 패턴을 그대로 옮기지 않는다 — `pendingQueue`·`lastMessageAt`·`disconnected`를 그냥 `_ChatRoomScreenState`의 평범한 필드로 두면 충분하다. React 구현의 구조를 이유 없이 그대로 베끼면 Dart에선 없어도 될 복잡도가 늘어난다.

**Dart Realtime 클라이언트는 토큰 재인증을 자동으로 한다.** 웹은 `onAuthStateChange`마다 수동으로 `setAuth`를 재호출해야 하지만, 설치된 `realtime_client-2.8.0`(`~/.pub-cache/hosted/pub.dev/realtime_client-2.8.0/lib/src/realtime_channel.dart:165-190`, 실측 확인) 소스를 보면 채널이 매 join/rejoin마다 `socket.accessToken`(항상 최신 세션 토큰)을 join payload에 실어 보내고, 응답 후 `socket.setAuth(socket.accessToken)`을 **자동으로** 호출한다. 즉 웹의 "onAuthStateChange → 수동 setAuth" 배선은 Dart에서 불필요하다 — 옮기면 없어도 될 상태만 하나 늘어난다. 최초 구독 전 방어적으로 `supabase.realtime.setAuth(session.access_token)`을 한 번 호출해도 무해하지만, 정확성이 그 호출에 의존하지는 않는다.

**`docs/conventions.md` §12.6의 "Never" 문구는 이미 web에서 뒤집혔다.** DW-548(대장, 2026-07-29 done)이 "방 목록 각 행에 개별 안읽음 표시를 두지 않는다"는 Story 12.5의 Never를 사용자 요청으로 반전시켰고 `chat_unread_by_room()`(0026)·`web/src/app/(user)/chat/page.tsx` 83-93·141행이 이미 그 반전을 구현해 배포돼 있다. §12.6 문서 본문만 그 반전을 반영하지 못한 채 남아 있다(스펙-16-3의 "코드가 정본" 선례와 같은 종류의 문서 드리프트). 앱은 최신 실제 계약(웹 코드+DW-548)을 따라 방별 배지를 함께 구현하고, 그 김에 §12.6 문구도 고친다.

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 채팅 테스트)
- `cd web && npm test -- roomTopicContract` -- expected: green(Dart 4번째 사본 검사 포함)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 로컬 Supabase에서 두 계정(구매자·판매자)으로 같은 방을 열어 실제 실시간 송수신 1회 실측(폴링 없이 상대 메시지가 즉시 보이는지) — 실제 소켓 상태 전이는 위젯테스트로 재현하지 않으므로 이 수동 확인이 유일한 실제 검증 경로다(§12.5 web의 vitest node-environment 한계와 동일 이유).
- 한쪽 기기의 네트워크를 잠시 끊었다 복구해 배너 전환(끊김→재연결→자동소멸)과 그 사이 보낸 메시지가 재연결 후 전송되는지 확인.
- 안읽음 배지: 상대가 보낸 뒤 총합/방별 배지가 오르고, 방에 재진입하면(다음 로드 시점) 줄어드는지 확인.

## Auto Run Result

**Status:** done

**Summary:** Flutter 앱 채팅을 3초 폴링에서 Supabase Realtime Broadcast 구독으로 전환했다(`docs/conventions.md` §12/§12.4/§12.5/§12.6을 Dart로 미러링). 멱등 전송(client_message_id)·재연결 배너·오프라인 큐+순차 flush·갭보정(커서 재조회)·읽음 1회 갱신·안읽음 배지 2종(내비 총합·방별)·방 목록 최신순 정렬을 구현했다. 웹의 `roomTopicContract.test.ts`에 Dart를 네 번째 토픽 사본으로 등록했고, `docs/conventions.md` §12.6의 stale한 "방별 배지 Never" 문구를 DW-548 반전 경위로 정정했다.

**Files changed:**
- `app/lib/features/chat/chat_models.dart` -- `clientMessageId`·`lastMessageAt` 필드, `QueuedChatMessage` 추가
- `app/lib/features/chat/chat_repository.dart` -- `roomTopic()`, 멱등 `sendMessage`(+`isIdempotentResendMatch` 순수함수), `fetchRooms` 정렬 교체, `fetchUnreadTotal`/`fetchUnreadByRoom`(+`parseUnreadByRoomRows` 순수함수)/`markRoomRead` 신설, `reuseFailedKey`/`flushChatMessageQueue` 순수함수
- `app/lib/features/chat/chat_providers.dart` -- 안읽음 provider 2종
- `app/lib/features/chat/chat_room_screen.dart` -- 폴링 제거, Realtime 구독·재연결 배너·오프라인 큐·갭보정·읽음 갱신 전면 재작성(테스트 훅 `subscribeOverride`/`unsubscribeOverride` 포함)
- `app/lib/features/chat/chat_list_screen.dart` -- 방별 안읽음 배지
- `app/lib/core/router/app_router.dart` -- 채팅 탭 내비 배지 + `authStateProvider`/탭 activate 양쪽에서 안읽음 provider invalidate
- `docs/conventions.md` -- §12 4번째 사본 등록, §12.6 정정 + 대비값(5.44:1) 명시
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts` -- Dart 검사 추가(호출부 앵커 포함)
- `app/test/chat_model_test.dart`·`chat_repository_test.dart`(신규)·`chat_room_screen_test.dart`(신규)·`chat_list_screen_test.dart`(신규)·`app_router_test.dart` -- 단위·위젯테스트
- `_bmad-output/implementation-artifacts/deferred-work.md` -- defer 4건 등재

**Review findings breakdown:** patch 9건(medium 5, low 4, 전부 반영+재검증 완료) · defer 4건(전부 medium, 대장 등재) · reject 18건(spec 명시 동작이거나 web 원본과 동일 특성이거나 실측으로 반증됨 — Review Triage Log에 근거 포함 기록).

**Follow-up review recommendation:** true (patch 5×medium + 4×low → 3×5+1×4=19 ≥ 5).

**Verification performed:**
- `flutter analyze` — 0 issues (오케스트레이터 직접 재실행 확인)
- `flutter test` — 284/284 green (오케스트레이터 직접 재실행 확인)
- `npm test -- roomTopicContract` — 11/11 green (오케스트레이터 직접 재실행 확인)
- `flutter build web --dart-define-from-file=.env.json` — 빌드 성공(구현 단계에서 확인)
- I/O & Edge-Case Matrix 9행 전부 실행되는 테스트로 커버(방 목록 정렬 1행만 이 레포의 기존 관례상 네트워크 호출 리포지토리 메서드는 단위테스트하지 않는다는 이유로 코드 직접 대조로 대체 — `wishlist_repository_test.dart` 선례와 동일 근거)
- Manual checks(로컬 Supabase 2계정 실시간 송수신 실측)는 이 세션(헤드리스 샌드박스)에서 CanvasKit `CONTEXT_LOST_WEBGL` 크래시로 실행 불가 — 장부에 등재(위 Files changed의 deferred-work.md 항목)


**Residual risks:**
- 실제 소켓 연결·2계정 동시 송수신·진짜 네트워크 끊김→재연결은 위젯테스트의 상태-콜백 시뮬레이션으로만 검증됐고, 실기기/정상 브라우저에서 한 번도 실측되지 않았다(대장 등재, 트리거: 실기기 검증 또는 Epic 16-6).
- `realtime_client`의 자동 재조인 타이밍·백오프가 실제 네트워크 플랩 상황에서 §12.5가 기대하는 대로 동작하는지 라이브러리 소스 검토로만 확인했다.
- 최초 SUBSCRIBED 재조회 성공이 초기 로드 실패 안내를 안 지우는 특성이 web과 app 양쪽에 동일하게 존재한다(대장 등재, web과 함께 고칠 자리).
- 앱 백그라운드/포그라운드 전환 시 갭보정을 트리거할 생명주기 훅이 없다(대장 등재, 실기기 검증 필요).

---

## 후속 리뷰 패스 (2026-08-08, 2차)

**Summary:** `done`으로 닫혔던 스토리를 새 세션에서 다시 검토해 **실시간 수신이 실제로는 전혀 동작하지 않고 있었다**는 것을 잡아냈다(브로드캐스트 봉투를 한 단계 얕게 읽음 — 이 스토리의 헤드라인 기능). 1차 패스가 이걸 놓친 이유는 위젯테스트가 프로덕션 코드와 똑같이 틀린 페이로드 모양을 직접 만들어 넣어, 계약을 **검사하는 게 아니라 정의**하고 있었기 때문이다. 그 밖에 배지 갱신 누락·끊김 중 전송 유실 등 12건을 더 고치고, 실제 라이브러리 디스패치 경로를 태우는 검사를 신설했다.

**Files changed (2차):**
- `app/lib/features/chat/chat_room_screen.dart` -- `extractBroadcastRecord()` 신설(봉투 깊이 수정), 끊김 중 전송 실패 시 큐 보존, `_flushQueue` myId 가드, 세션 없음 시 에러 배너, `subscribed`에서 `_realtimeError` 항상 해제
- `app/lib/features/chat/chat_list_screen.dart` -- pop 복귀 시 배지 provider 2종도 무효화, 제목 말줄임(D5)
- `docs/conventions.md` -- §12.2에 Dart 예외(자동 재인증 실측 근거) 등재
- `web/src/app/(user)/chat/[roomId]/__tests__/roomTopicContract.test.ts` -- 앵커를 `replay`·`onBroadcast`·`subscribe`까지 확장
- `app/test/chat_realtime_envelope_test.dart` (신규) -- 실제 `realtime_client` 디스패치로 봉투 깊이를 고정
- `app/test/chat_room_screen_test.dart`·`chat_list_screen_test.dart`·`chat_repository_test.dart`·`app_router_test.dart` -- 위 배선들의 회귀 검사 추가
- `_bmad-output/implementation-artifacts/deferred-work.md` -- defer 1건 등재

**Review findings breakdown (2차):** patch 13건(high 1, medium 3, low 9 — 전부 반영+재검증) · defer 1건(medium) · reject 7건(전부 low, 근거는 Review Triage Log).

**Follow-up review recommendation:** true (high 1건 존재 → 무조건 true. 점수도 3×3 + 1×9 = 18 ≥ 5).

**Verification performed (2차, 오케스트레이터 직접 실행):**
- `flutter analyze` — `No issues found!`
- `flutter test` — 297/297 green(신규 검사 포함)
- `npm test -- roomTopicContract unreadWiringContract` — 14/14 green
- `flutter build web --dart-define-from-file=.env.json` — `✓ Built build/web`
- **핵심 결함 검사의 red/green을 형태를 바꿔 재확인**: 적용 에이전트는 `extractBroadcastRecord` 본문을 변형해 red를 봤다고 보고했는데, 그 표기에서만 성립할 수 있으므로 오케스트레이터가 **호출부를 원래 버그 표현(`payload['record']`)으로 되돌리는 다른 형태**로 다시 변형 → red 2건 확인 → 백업본으로 원복 → green 24건 확인(`git checkout` 미사용)

**Residual risks (2차 시점):**
- ⚠️ **실기기 실측이 여전히 0회다.** 이번 패스가 잡은 결함은 "자동 검사는 전부 green인데 실제 기능은 죽어 있었다"는 형태였고, 그걸 잡아낸 것은 테스트가 아니라 라이브러리 소스·계약 문서와의 대조였다. 남은 실제-소켓 축(private 채널 RLS 평가, 재연결 자동 rejoin, 2계정 송수신)은 여전히 같은 사각지대에 있다 — 대장에 등재된 Manual checks를 실기기에서 반드시 돌려야 한다(트리거: Epic 16-6).
- 앱 백그라운드/포그라운드 전환 시 갭보정을 트리거할 생명주기 훅이 없다(대장 등재, 실기기 검증 필요).
- 최초 SUBSCRIBED 재조회 성공이 초기 로드 실패 안내를 안 지우는 특성이 web·app 양쪽에 동일하게 존재한다(대장 등재, web과 함께 고칠 자리).
- 앱에 채팅 2000자 클라이언트 가드가 없어 초과 메시지가 오프라인 큐 머리에 박히면 뒤가 막힌다(2차 defer로 대장 등재).
