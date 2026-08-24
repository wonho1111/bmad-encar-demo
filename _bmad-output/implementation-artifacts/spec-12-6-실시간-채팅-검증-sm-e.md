---
title: '12.6 실시간 채팅 검증 (SM-E)'
type: 'chore'
created: '2026-07-29'
status: 'done'
baseline_revision: 'dd000bbd4bcf1fae83ce89f2d39928049057b8c7'
final_revision: '13260fa8ccf32e85169a91fa7e2ea7104516fceb'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 12.1~12.5로 채팅이 폴링에서 실시간(Broadcast)으로 전환됐지만, 실시간 송수신·재연결·갭보정·멱등성과 기존 채팅 무결성 3중 장치(CM-B: RLS·트리거·CHECK)가 실제 두 브라우저(구매자·판매자) 환경에서 자동 테스트로는 못 잡는 방식으로 깨지지 않았는지 아직 실측된 적이 없다(SM-E).

**Approach:** 로컬 Supabase 스택에서 구매자·판매자 두 실제 브라우저 세션으로 실시간 송수신·네트워크 단절/재연결·갭보정·멱등 재전송·CM-B를 직접 확인하고 결과를 기록한다. 새 결함을 코드로 고치지 않는 확인 전용 패스이되, 이미 대장에 "이 스토리에서 재실측 후 필요하면 그 자리에서 고친다"고 못박힌 두 건(`#206` 재시도 UX, `#215` 뒤로가기 배지)만 예외로, 재현되면 대장이 지정한 최소 수정을 적용한다.

## Boundaries & Constraints

**Always:**
- 이 스토리의 산출물은 "확인"이지 "빌드"가 아니다 — 새로 발견한 결함(아래 두 예외 제외)은 코드로 고치지 않고 `docs/tech-debt.md`에 다음 번호로, 기존 항목과 같은 형식(위치·내용·왜 지금 안 고치나·트리거)으로 등재한다.
- 로컬 실행 전 `select has_table_privilege('authenticated','public.chat_messages','select');`로 `#211`(로컬 스택의 authenticated/anon 테이블 기본 권한 누락)이 재발했는지 먼저 확인한다. `f`면 `#211`에 적힌 세션 내 임시 조치(`ALTER DEFAULT PRIVILEGES ... GRANT ... TO authenticated, anon` + 기존 테이블 전체 `GRANT` + 0011/0012/0020의 REVOKE·컬럼별 GRANT 재적용)를 그대로 재적용한 뒤 계속한다.
- 두 브라우저 세션은 시드 계정 `buyer@test.com` / `seller-seed2@test.com`(비밀번호 둘 다 `seller123`)을 쓴다 — `chat_rooms` 시드(`supabase/seed-local/data/chat_rooms.json`)에서 이 둘이 실제로 같은 방(`buyer_id`=buyer@test.com, `seller_id`=seller-seed2@test.com)을 공유하는 유일한 페어다. `buyer@test.com`·`seller@test.com`은 서로 방을 공유하지 않으므로 쓰지 않는다.
- 재연결 상태 전이는 색상만이 아니라 텍스트로도 확인한다(기존 비색 신호 계약).
- CM-B는 기존 실DB pytest 스위트(`test_chat_idempotency_real_db.py`, `test_chat_realtime_broadcast_real_db.py`, `test_chat_unread_real_db.py`)를 그대로 재실행해 green을 확인하는 방식으로 검증한다 — 새 자동 검사를 만들지 않는다.
- `#206`(오프라인 큐 flush 부분 실패 시 재시도 수단 없음)과 `#215`(방 목록으로 뒤로가기 시 안읽음 배지가 옛값으로 복원)는 대장이 이 스토리에서 재실측하도록 명시한 항목이다 — 반드시 재현을 시도하고, 재현 여부에 따라 아래 Block If 기준대로 처리한다.
- Flutter 앱은 여전히 폴링 기반이라(`app/lib/features/chat/chat_room_screen.dart`, 재연결 배너·갭보정·오프라인 큐 없음, `tech-debt #198`) 이번 실시간 검증의 대상이 아니다 — 이 divergence를 결과에 명시적으로 재확인·기록한다(`#198` 참조, 새 항목 아님).

**Block If:**
- `#206` 재현 시도 결과 flush 부분 실패로 큐에 남은 항목이 다음 재연결 전까지 자동 복구되지 않음을 확인했다면 → `ChatRoomMessages.tsx`의 미전송 안내 옆에 `flushQueue()`를 직접 호출하는 재시도 버튼을 추가한다(`#206`이 명시한 최소 수정). 재현되지 않으면 코드를 건드리지 않고 그 사실만 기록한다.
- `#215` 재현 시도 결과 방 진입 후 브라우저 뒤로가기로 목록에 복귀했을 때 안읽음 배지가 새로고침 없이는 줄지 않음을 확인했다면 → `/chat` 목록 페이지에 `pageshow` 이벤트(`event.persisted`, bfcache 복원)에서 `router.refresh()`를 호출하는 작은 클라이언트 컴포넌트를 추가한다(`#215`이 명시한 안 (a)). 재현되지 않으면 코드를 건드리지 않고 그 사실만 기록한다.
- 위 두 건 외의 어떤 새 결함이든 실제 메시지 유실·중복(멱등 실패)·CM-B(RLS/트리거/CHECK) 위반이 실측되면 — 이미 `done`인 스토리(12.1~12.5)의 회귀이므로 이 스토리 범위로 고치지 않는다. `docs/tech-debt.md`에 신규 항목으로 등재하고 status `blocked`로 HALT한다(핵심 보장이 깨진 것이므로 사람의 즉시 판단이 필요).
- 로컬 스택을 띄울 수 없거나(`supabase start` 실패 등) 두 시드 계정으로 로그인할 수 없으면 HALT with status `blocked`, blocking condition `environment blocker`.

**Never:**
- `#206`·`#215` 외의 어떤 기존 결함도 이 스토리에서 고치지 않는다 — 범위는 두 건의 사전 승인된 최소 수정으로 한정한다.
- 새 Playwright/pytest 자동 회귀 검사를 추가하지 않는다 — 이 스토리는 정의상 자동 테스트가 못 잡는 것을 사람이 직접 보는 일회성 확인이다.
- Flutter 앱에 실시간(Broadcast)·재연결 배너·갭보정을 구현하지 않는다(Epic 16.4 범위, `tech-debt #198`).
- 실DB `chat_messages`를 수동 SQL DELETE로 지우고 정리하지 않은 채 두지 않는다 — Realtime Replay가 지운 행의 방송을 되살릴 수 있다(`docs/conventions.md` §12.5, `tech-debt #202`). 테스트로 지웠다면 확인 후 정리한다.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 실시간 송수신 | 구매자·판매자 세션이 같은 방을 열어둔 채 구매자가 메시지 전송 | 판매자 화면에 새로고침 없이 수 초 내 표시 | 지연·미표시 시 회귀 — Block If |
| 재연결 표시 | 판매자 세션 오프라인 전환 후 복귀 | 끊김 동안 배너(텍스트+색), 복귀 시 성공 텍스트+색 후 소멸 | 표시 없으면 회귀 |
| 갭보정 | 판매자 오프라인 중 구매자가 메시지 2건 전송, 판매자 재연결 | 유실 없이 2건 모두 병합 표시(created_at+id 순) | 유실 시 회귀 — Block If |
| 멱등 재전송 | 오프라인 큐가 재연결 후 자동 재전송, 같은 client_message_id | DB에 정확히 1행만 존재 | 중복 행 발견 시 회귀 — Block If |
| flush 부분 실패 (`#206`) | 재연결 직후 재차단으로 일부 전송 실패 유도 | 미전송 안내 표시, 재현되면 재시도 버튼 동작 확인 | 재현 안 되면 기록만 |
| 뒤로가기 배지 (`#215`) | 안읽음 있는 방 진입 후 브라우저 뒤로가기 | 새로고침 없이도 감소한 배지 표시(재현 시 수정 적용) | 재현 안 되면 기록만 |
| CM-B 무결성 | 기존 실DB pytest 3종 재실행 | 전부 green | 실패 시 회귀 — Block If |

</intent-contract>

## Code Map

- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` -- 실시간 구독·재연결 배너·오프라인 큐·flush 로직(참고, `#206` 재현 시 재시도 버튼 추가 지점)
- `web/src/app/(user)/chat/page.tsx` -- 방 목록(정렬), `#215` 재현 시 pageshow 리프레시 추가 지점
- `web/src/lib/messages.ts` -- `sendMessage` 멱등 처리, `fetchMessages` 갭보정 커서(참고)
- `docs/conventions.md` §12 -- 실시간 채팅 배선 계약(토픽·페이로드·갭보정·멱등키) 원문
- `docs/tech-debt.md` -- `#198`(앱 divergence)·`#206`·`#211`·`#215` 원문 확인 + 실측 결과 반영 + 신규 결함 등재 대상
- `api/tests/integration/test_chat_idempotency_real_db.py`, `test_chat_realtime_broadcast_real_db.py`, `test_chat_unread_real_db.py` -- CM-B 재확인용 기존 실DB 테스트(수정 없이 재실행만)
- `web/e2e/helpers.ts` -- 시드 계정 로그인 헬퍼(참고, 재사용 가능하면 재사용)
- `app/lib/features/chat/chat_room_screen.dart` -- 앱이 여전히 폴링임을 재확인(참고, 미수정)

## Tasks & Acceptance

**Execution:**
- `supabase start` / `scripts/use-env.sh local` / `scripts/seed-local.sh` -- 로컬 스택 기동 + `#211` 권한 재확인·필요시 재적용 + `web`에서 `npm run dev` -- 두 브라우저 세션이 동작할 토대
- `web/src/app/(user)/chat/[roomId]/page.tsx` (두 세션에서 같은 방 URL 접속) -- 구매자/판매자 실시간 송수신 실측 -- SM-E 핵심 확인
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` (판매자 세션 오프라인 전환 → 구매자 메시지 2건 전송 → 판매자 재연결) -- 갭보정·유실 없음·재연결 표시 실측
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` + `chat_messages` 테이블 직접 조회 (재연결 후 자동 재전송된 건 확인) -- 멱등(중복 없음) 실측 — 화면에 중복 버블 미표시 + DB 1행만 존재 둘 다 확인
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` (`#206` 재현 시도: 재연결 직후 재차단으로 flush 부분 실패 유도) → 재현되면 재시도 버튼 추가 -- 사전 승인된 최소 수정 적용
- `web/src/app/(user)/chat/page.tsx` (`#215` 재현 시도: 방 진입 후 뒤로가기) → 재현되면 pageshow 리프레시(옆 클라이언트 컴포넌트) 추가 -- 사전 승인된 최소 수정 적용
- `api/tests/integration/test_chat_idempotency_real_db.py`, `test_chat_realtime_broadcast_real_db.py`, `test_chat_unread_real_db.py` 재실행 -- CM-B 유지 확인
- `app/lib/features/chat/chat_room_screen.dart` (여전히 폴링임을 확인) -- app/web divergence 재확인, `#198` 참조로 결과에 기록
- `docs/tech-debt.md` -- 실측 결과(재현 여부, 적용한 수정, 새 결함이 있다면 신규 번호) 반영 -- B8 대장 갱신

**Acceptance Criteria:**
- Given 두 브라우저(구매자·판매자) 세션과 실시간 채팅, when 메시지를 주고받으면, then 폴링 지연 없이 즉시 상대 화면에 표시됨이 실측된다.
- Given 판매자 세션의 네트워크를 끊었다 재연결하면, when 그 동안 구매자가 메시지를 보내면, then 재연결 후 유실 없이 화면에 병합 표시되고, 자동 재전송에도 메시지가 화면에 중복 표시되지 않으며 DB에도 정확히 1행만 존재함이 실측된다.
- Given 재연결 상태 전이, when 끊김·재연결이 발생하면, then 배너가 색+텍스트로 상태를 표시함이 실측된다.
- Given 기존 CM-B(RLS·트리거·CHECK) 실DB 테스트 스위트, when 재실행하면, then 전부 green임이 확인된다.
- Given `#206`·`#215`, when 실제로 재현을 시도하면, then 재현 여부와(재현됐다면) 적용한 최소 수정이 `docs/tech-debt.md`에 기록된다.
- Given Flutter 앱의 채팅 화면, when 이번 실시간 검증과 비교하면, then 앱이 여전히 폴링 기반이라는 divergence가 확인·기록된다(`#198` 참조).

## Spec Change Log

### 2026-07-29 — `#215` 수정 메커니즘 정정 (코드리뷰 adversarial+intent-alignment 지적)
- **트리거 finding:** Block If 절이 `#215` 수정을 `pageshow`(`event.persisted`) 이벤트 + `/chat` 페이지 자신에 배치하라고 구체적으로 지정했으나, 실제 구현 중 실측(Playwright)으로 둘 다 반증됐다 — (1) 이 앱의 뒤로/앞으로가기 전환에서 `pageshow`는 발생하지 않는다(Next.js App Router가 popstate를 자체 처리해 문서 언로드·bfcache 복원 없이 클라이언트 라우팅만 함), (2) `/chat` 페이지 자신에 `popstate` 리스너를 둬도 `/chat/[roomId]`로 이동하는 순간 그 페이지가 언마운트되고, 뒤로가기의 popstate는 재마운트 전에 발생해 리스너가 그 이벤트를 구조적으로 놓친다(닭-달걀 문제).
- **무엇을 정정했나:** 위 두 가지 반증된 사실을 이 항목으로 못박는다. 실제 구현은 이벤트를 `popstate`로, 배치를 `/chat`·`/chat/[roomId]`의 유일한 공통 조상인 루트 레이아웃(`app/layout.tsx`)으로 바꿨다 — 의도(뒤로가기 복귀 감지 → `router.refresh()`, 배지 계산 로직 자체는 불변)는 원안과 동일하고, 감지 이벤트·배선 위치만 실측에 맞게 바뀌었다.
- **피하는 known-bad 상태:** 이 정정 없이는 다음 사람이 이 스펙 원문(`pageshow`+`/chat` 페이지)만 보고 "구현이 스펙을 안 따랐다"고 오판해 되돌릴 수 있고, 되돌리면 방금 닫은 `tech-debt #215`(뒤로가기 시 안읽음 배지가 옛값으로 복원)가 재발한다. 상세 경위·실측 로그는 `docs/tech-debt.md` `#215`의 종결 노트와 `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx` 파일 상단 주석에 있다.
- **KEEP:** 의도 자체(뒤로가기 복귀 시 `router.refresh()`로 최신 배지를 다시 계산, 배지 계산 로직 자체는 건드리지 않음)는 유효했고 그대로 유지해야 한다 — 바뀐 것은 구현 메커니즘(이벤트 종류·배치 위치)뿐이다.

### 2026-07-29 — Never 절("새 자동 회귀 검사 추가 금지")과 vitest 계약 테스트 2건의 관계 명시 (후속 코드리뷰 intent-alignment 지적)

- **트리거 finding:** `<intent-contract>`의 Never 절은 "새 Playwright/pytest 자동 회귀 검사를 추가하지 않는다 — 이 스토리는 정의상 자동 테스트가 못 잡는 것을 사람이 직접 보는 일회성 확인이다"라고 적었는데, 1차 리뷰 패스가 vitest 소스 스캔 계약 테스트 2건(`queueRetryWiringContract.test.ts`, `bfcacheRefreshContract.test.ts`)을 신설했다. 이 충돌이 어느 문서에도 판정·기록되지 않아, 다음 사람이 "스펙이 금지한 걸 넣었다"고 보고 지울 수 있었다.
- **채택한 해석과 근거:** Never 절이 금지한 것은 **SM-E 확인 자체를 자동 테스트로 대체하는 것**이다(그래서 근거 문장이 "자동 테스트가 못 잡는 것을 사람이 직접 본다"이고, 지목한 도구도 이 저장소에서 동작 검증에 쓰는 Playwright·pytest 둘이다). 신설된 두 계약 테스트는 SM-E를 검증하지 않는다 — 스펙이 **사전 승인한 두 코드 수정**(`#206` 재시도 버튼 배선, `#215` popstate 가드 배선)이 지워지거나 옮겨져도 조용히 통과하던 사각지대를 막는 배선 고정 장치이고, 승인된 코드 변경에 실행되는 검사를 붙이는 것은 이 저장소의 상시 규칙(CLAUDE.md B9)이다. 두 축은 대상이 다르므로 충돌하지 않는다.
- **피하는 known-bad 상태:** 이 기록이 없으면 다음 사람이 Never 절 문자만 읽고 두 테스트를 "스펙 위반"으로 지우고, 그 순간 `#206`·`#215` 배선이 다시 무방비가 된다(둘 다 지워져도 lint·tsc·나머지 vitest가 전부 초록인 축이다 — 그게 이 테스트들이 생긴 이유다).
- **KEEP:** Never 절의 원래 취지(SM-E 확인은 사람이 두 브라우저로 직접 본다, 그걸 자동 테스트로 대체하지 않는다)는 그대로 유효하다 — 실제로 이번에도 새 Playwright/pytest 검사는 하나도 만들지 않았고 CM-B는 기존 실DB pytest 재실행으로만 확인했다.

## Review Triage Log

### 2026-07-29 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 4, low 3)
- defer: 4: (medium 1, low 3)
- reject: 1
- addressed_findings:
  - `low` `patch` **"다시 보내기" 재시도 버튼이 연결이 끊긴 상태에서도 눌렸다**(edge-case-hunter+adversarial 교차 지적). `onClick`에 `disconnectedRef.current` 가드를 추가해 끊긴 동안은 no-op으로 만듦(새 state 없이 기존 ref 재사용).
  - `medium` `patch` **`role="alert"`가 포커스 가능한 재시도 버튼까지 감싸고 있었다**(adversarial 지적, 접근성 안티패턴 — alert 리전은 읽기 전용 알림용). `role="alert"`를 안내 텍스트(`<span>`)에만 걸고 버튼은 형제 요소로 뺌(시각 레이아웃 불변).
  - `low` `patch` **`flushQueueRef`가 방 전환 시 다른 형제 ref들(`onlineInFlightKeyRef` 등)과 달리 리셋되지 않았다**(adversarial 지적). 지금은 안전했으나(재배선이 항상 먼저 돎) 그 가정이 코드에 문서화돼 있지 않았음 — 형제 ref들과 같은 자리에서 명시적으로 리셋 추가.
  - `low` `patch` **`ChatListBfcacheRefresh`의 경로 비교가 정확히 `/chat`만 인정해 `/chat/`(끝 슬래시) 변형에서 방금 고친 `#215`가 재현될 여지가 있었다**(edge-case-hunter 지적). 끝 슬래시를 정규화한 뒤 비교하도록 수정.
  - `medium` `patch` **재시도 버튼 배선(`flushQueueRef`)에 회귀 검사가 전혀 없었다**(verification-gap 지적 — 배선 줄이 지워지거나 옮겨져도 lint·tsc·vitest 전부 초록이었을 것). 기존 `roomTopicContract.test.ts`/`unreadWiringContract.test.ts`와 같은 소스 스캔 방식으로 `queueRetryWiringContract.test.ts` 신설, red→green 확인.
  - `medium` `patch` **뒤로가기 배지 새로고침(popstate 가드) 배선에도 회귀 검사가 없었다**(verification-gap 지적). 같은 소스 스캔 방식으로 `bfcacheRefreshContract.test.ts` 신설(jsdom 미설치라 실제 렌더링 테스트 대신 — 이 저장소의 기존 방침, `vitest.config.ts` 주석이 이미 명시) — popstate 리스너 등록/해제, `router.refresh()`가 `/chat` 가드 안에 있는지, 루트 레이아웃이 컴포넌트를 실제로 렌더하는지 확인. red→green 확인.
  - `medium` `patch` **스펙의 `#215` Block If가 지정한 구체 메커니즘(`pageshow`+`/chat` 페이지)이 실측으로 반증됐는데 그 사실이 스펙 본문 어디에도 기록되지 않았다**(adversarial+intent-alignment 교차 지적). 위 Spec Change Log 항목으로 정정 기록 — 다음 사람이 스펙 원문만 보고 "구현이 스펙을 안 따랐다"고 오판해 되돌리는 것을 방지.
- 기각 1건 — popstate가 짧은 간격으로 여러 번 발생하면 `router.refresh()`가 매번 새로 불릴 수 있다는 지적(edge-case-hunter, 오류로 이어지지 않고 데모 규모에서 무해 — 디바운스 추가는 A2가 경계하는 불필요한 방어).
- defer 4건 — `docs/tech-debt.md` `#220`~`#223`으로 등재(스펙 frontmatter가 가리키는 `deferred-work.md`는 2026-07-15에 동결된 파일이라 이 저장소의 `block-frozen-ledger.py` 훅이 신규 쓰기를 거부한다 — 훅 안내에 따라 정본 대장인 `docs/tech-debt.md`에 직접 기존 항목과 같은 형식으로 등재했다, 기존 항목 무수정): `#220` 재시도 버튼에 진행 중 표시(로딩 상태)가 없음(`isFlushing`이 state가 아니라 effect 지역 변수라 승격에는 이 패스 범위를 넘는 구조 변경 필요) · `#221` 재시도 버튼에 연타 방지(쿨다운)가 없음(자동 재시도는 실제 재연결 이벤트로 빈도가 제한되나 수동 버튼은 아님 — 백엔드가 멱등이라 실제 피해는 없음) · `#222` `ChatListBfcacheRefresh`가 Next.js의 문서화되지 않은 popstate 처리 순서라는 내부 동작에 의존하며 이를 지켜주는 자동 테스트가 없음(다음 Next.js 업그레이드 시 조용히 깨질 수 있음 — `#207`의 supabase-js 버전 의존과 같은 종류의 위험) · `#223` 이 리스너가 채팅과 무관한 모든 페이지의 뒤로가기에서도 매번 실행됨(루트 레이아웃 배치의 불가피한 트레이드오프, 내부 pathname 가드로 지금은 안전하나 같은 패턴이 반복되면 layout.tsx가 비대해질 위험).

### 2026-07-29 — Follow-up review pass (독립 후속 리뷰, `followup_review_recommended: true`로 트리거)
- intent_gap: 0
- bad_spec: 0
- patch: 7: (high 0, medium 3, low 4)
- defer: 3: (medium 2, low 1)
- reject: 7
- addressed_findings:
  - `medium` `patch` **`queueRetryWiringContract.test.ts`가 끊김 가드의 극성(polarity)을 고정하지 못했다** — 세 레이어(adversarial·edge-case-hunter·verification-gap)가 각자 뮤테이션으로 실증: 컴포넌트의 `if (!disconnectedRef.current)`를 `if (disconnectedRef.current)`로 뒤집으면(= 버튼이 렌더되는 유일한 상태에서 죽는다) 검사가 3/3 그대로 통과했다. `#206` 재발을 막으려고 만든 검사가 가장 치명적인 1글자 회귀를 못 본 것. 정규식을 `if\s*\(\s*!\s*disconnectedRef\.current\s*\)\s*flushQueueRef\.current\(\)` 전체 표현으로 고정. **red→green 실증:** 가드를 뒤집은 상태 `1 failed | 2 passed`(실패 메시지가 정확히 이 단언) → 되돌린 뒤 `3 passed`.
  - `medium` `patch` **미전송 안내 문구가 바로 옆 재시도 버튼과 모순됐다**(adversarial 지적). 문구가 "…그때까지는 전송되지 않습니다"인데 즉시 전송하는 버튼이 옆에 붙어 있어, 안내만 읽은 사용자는 할 수 있는 게 없다고 결론짓고 버튼을 쓰지 않는다. `role="alert"`가 이 텍스트에만 걸려 있으므로 스크린리더 사용자에게는 재시도 수단의 존재 자체가 전달되지 않는 문제이기도 했다. 문구를 "아래 \"다시 보내기\"를 누르면 지금 다시 시도하고, 누르지 않으면 연결이 다시 끊겼다 회복될 때 재시도합니다"로 바꿔 두 경로를 모두 사실대로 적음.
  - `medium` `patch` **재시도 버튼이 끊긴 동안 멀쩡해 보이는 채로 조용히 no-op이었다**(edge-case-hunter 지적). 1차 패스가 넣은 `disconnectedRef` 가드는 옳았지만 버튼 외형이 그대로여서 클릭해도 아무 반응·피드백이 없었다(fail-silent). `disabled={isDisconnected}`를 추가해 잠긴 상태를 시각적으로 드러냄(전송 버튼이 이미 쓰는 같은 렌더용 값, 새 state 없음). `onClick` 가드는 render→click 사이 경합 대비로 그대로 유지.
  - `low` `patch` **재시도 버튼이 좁은 화면에서 2줄로 밀릴 수 있었다** — `project-context.md` 규칙13(D5)이 "2줄로 밀리는 버튼"을 명시적 금기로 규정하는데, 이 행은 `justify-between` 안에 ~60자 한국어 문장과 `shrink-0`/`whitespace-nowrap` 없는 `<Button>`이 나란히 있었다(`buttonClasses`는 둘 다 안 내보낸다). 버튼에 `shrink-0 whitespace-nowrap`, 문장에 `min-w-0`을 붙여 공간 부족을 문장이 흡수하게 함.
  - `low` `patch` **`queueRetryWiringContract.test.ts`가 "안 보는 것"에 도달 가능성(reachability)을 안 적었다**(verification-gap 뮤테이션 실증: ref 대입을 `if (roomId === "__never__") ...`로 감싸도 스위트 288건 전부 통과). 소스 스캔은 대입의 텍스트·위치만 고정하고 그 줄이 실행되는지는 못 본다 — CLAUDE.md B4("그 검사가 안 보는 것을 검사 옆에 적는다")대로 실측 결과를 헤더 주석에 명시.
  - `low` `patch` **`bfcacheRefreshContract.test.ts`도 같은 사각지대를 안 적었다**(verification-gap 뮤테이션 실증: `handlePopState` 맨 앞에 `if (!document.hidden) return;`을 끼워도 288건 전부 통과). 같은 방식으로 헤더 주석에 명시.
  - `low` `patch` **Never 절("새 자동 회귀 검사 추가 금지")과 1차 패스가 신설한 vitest 계약 테스트 2건의 충돌이 어디에도 판정·기록되지 않았다**(intent-alignment 지적). 위 Spec Change Log 항목으로 채택한 해석과 근거를 기록 — 다음 사람이 Never 절 문자만 보고 두 테스트를 지워 `#206`·`#215` 배선을 다시 무방비로 만드는 것을 방지.
- defer 3건 — `docs/tech-debt.md` `#224`~`#226`으로 신규 등재(오케스트레이터 지시대로 기존 항목은 무수정, 신규만 추가): `#224` 큐가 Broadcast 에코 등 다른 경로로 비워지면 "N건 미전송" 안내가 영구히 안 지워지고 재시도 버튼으로도 못 지운다(medium, 12.4가 만든 기존 조기 반환 경로) · `#225` `#215` 수정이 `/chat`에만 걸려 배지를 가진 나머지 9개 경로로 뒤로가기하면 같은 증상이 남고 cross-document bfcache(`pageshow`) 경로도 미커버(medium, 브라우저 재측정은 안 했음을 항목에 명시) · `#226` 재시도 버튼의 끊김 가드는 Realtime 웹소켓 상태를 보는데 실제 전송은 PostgREST HTTP라 소켓만 끊긴 상태에서 과도하게 잠긴다(low).
- 기각 7건 — ① 연속 popstate 시 `router.refresh()` 디바운스 부재(1차 패스에서 이미 같은 근거로 기각한 동일 주장) · ② 스펙 파일이 untracked(의도된 워크플로 결정, Auto Run Result에 이미 기록됨) · ③ `#222`의 "jsdom 없음" 근거가 Playwright E2E 존재를 누락 / ④ `#206`·`#215` 헤더의 심각도 태그 형식 이탈 / ⑤ `#219`가 같은 종류의 8번째 항목이라는 지적 — ③~⑤는 전부 **기존 대장 항목 수정**이 필요한데 이번 실행은 신규 등재만 허용받았고(오케스트레이터 지시), 실질 피해도 없다 · ⑥ `stripComments`가 문자열 리터럴 속 `//`도 지움·200자 창 — 깨지면 시끄러운 false RED이지 조용한 회귀가 아니다 · ⑦ `path === '/chat'` 하드코딩이 `basePath` 도입 시 깨진다 — 이 저장소에 `basePath`가 없는 추측성 방어(A2).

### 2026-07-29 — 2차 독립 후속 리뷰 pass

- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 4, low 1)
- defer: 4: (medium 3, low 1)
- reject: 18
- addressed_findings:
  - `medium` `patch` **미전송 안내가 "버튼을 누르라"고 말하는데 그 버튼이 잠겨 있는 상태가 실제로 도달 가능했다**(adversarial+edge-case-hunter 교차 지적). 직전 패스가 같은 회차에 ① 안내 문구를 "옆 버튼을 누르면 지금 재시도"로 바꾸고 ② 버튼에 `disabled={isDisconnected}`를 붙였는데, 스펙이 지정한 `#206` 재현 절차(재연결 → 부분 실패 → 재차단)가 정확히 그 모순 상태를 만든다 — 사용자는 누를 수 없는 버튼을 누르라는 안내를 읽는다. `queueStuckNotice` state에는 "몇 건 남았나"라는 사실만 담고, "어떻게 다시 보내나"는 render에서 `isDisconnected`로 갈라 쓰도록 고침(끊긴 동안엔 "연결이 회복되면 자동으로 재시도합니다").
  - `medium` `patch` **`disabled={isDisconnected}`에 회귀 검사가 없었다**(adversarial+verification-gap 교차, 둘 다 뮤테이션으로 실증). 직전 패스가 조용한 실패를 없애려고 넣은 바로 그 줄인데, 지워도 스위트 288건이 전부 통과했다. `queueRetryWiringContract.test.ts`의 버튼 창 안에 단언 추가. **red→green 실증:** prop 삭제 시 `1 failed | 20 passed` → 복원 시 `21 passed`.
  - `medium` `patch` **`bfcacheRefreshContract.test.ts`가 가드 대상 `path`의 출처를 안 봤다**(adversarial 뮤테이션 실증). `window.location.pathname`을 `window.location.hash`로 바꾸면 컴포넌트가 영구히 아무 일도 안 하게 되는데(=`#215` 완전 재발) 검사는 그대로 통과했다 — "정규화가 있다"와 "가드 안에 refresh가 있다"만 보고 있었다. `const path = window.location.pathname.replace(` 전체를 고정. **red→green 실증** 완료.
  - `medium` `patch` **`'use client'` 지시자에 아무 검사가 없었다**(verification-gap 지적, 이번에 직접 재현). 이 파일은 서버 컴포넌트인 루트 레이아웃이 직접 import하므로 지시자가 빠지면 **앱 전체**가 빌드 실패하는데, `npm run lint`·vitest 290건은 전부 통과하고 web CI 잡엔 `next build` 스텝이 없어 CI가 초록인 채로 배포 빌드에서야 터진다(직접 확인: 지시자 제거 후 `npm run build` → `useRouter`/`useEffect` RSC 경계 위반 2 errors). 첫 줄 단언 추가, **red→green 실증** 완료. CI 사각지대 자체는 `#229`로 등재.
  - `low` `patch` **재시도 버튼 검사가 라벨에서 400자를 거꾸로 세는 매직넘버 창을 썼다**(adversarial+edge-case-hunter+verification-gap 3중 지적). 버튼에 prop이 몇 줄만 더 붙어도(대장 `#220`이 예고한 `loading`·`loadingText`) `onClick`이 창 밖으로 밀려 **동작은 멀쩡한데 검사만 빨개진다** — 거짓 RED는 검사를 약화·삭제하게 만드는 경로다. 창의 시작을 `<Button` 여는 태그로 잡아 구조로 고정.
- defer 4건 — `docs/tech-debt.md` `#227`~`#230`으로 **신규만** 등재(오케스트레이터 지시대로 기존 항목 무수정): `#227` 방을 옮기면 아직 못 보낸 오프라인 큐가 경고 없이 통째로 버려진다(12.4 기존 코드지만 이번에 붙인 재시도 버튼이 "복구할 수 있다"고 약속한 탓에 비대칭이 새로 생김, 브라우저 재현은 안 했음을 항목에 명시) · `#228` `#215` 수정이 기대는 문서화되지 않은 Next 내부 동작이 `#222`가 적은 popstate 순서 말고도 2건 더 있다(`router.refresh()`의 무효화 범위가 세그먼트가 아니라 캐시 전체라는 점, `useRouter()` 반환값의 참조 안정성 — 둘 다 추론이고 계측 안 했음을 명시) · `#229` web CI에 `next build`가 없어 RSC 경계 위반이 CI 초록으로 통과한다(직접 실측) · `#230` 재시도 버튼 배선의 실행 순서 불변식이 검사로 고정돼 있지 않다(IIFE 맨 앞에 `await` 한 줄이면 버튼이 영구 no-op이 되는데 288건 통과, 뮤테이션 실증 — 검사 헤더 주석에 사각지대로 명시).
- 기각 18건 — 크게 네 묶음. ① **기존 대장 항목 수정이 필요한 것 6건**(`#206`·`#215`의 "✅ 해소" 표기가 같은 커밋의 신규 8건과 상충한다 / `#215` 마감이 `#225`와 모순 / "0.3~3.3초" 표현이 관찰 창인지 지연인지 모호 / `#219`가 같은 종류의 8번째라 `#129`로 통합해야 / `#211` 사전 점검이 boolean 하나였다 / `#224`에 두 번째 진입 경로 추가) — 이번 실행은 신규 등재만 허용받았고 실질 피해도 없다. ② **이미 등재·기각된 것 7건**(컴포넌트 이름 `...BfcacheRefresh` 오칭 → `#225`에 이미 기록 / `(user)/chat` 폴더 배치와 하이드레이션 비용 → `#223` / popstate 디바운스·왕복 비용 → 1·2차 패스에서 같은 근거로 2회 기각 / 안내 건수(count) 박제 → `#224`와 같은 자리·같은 트리거 / `stripComments`가 문자열 속 `//`도 지움 → 1차 후속에서 기각 / 스펙 파일 untracked → 워크플로 결정). ③ **사실 확인 결과 성립 안 함 2건**(`pageshow`가 절대 안 온다는 주석이 틀렸다는 지적 — 실제 주석은 "이 앱의 back/forward 전환에서"로 범위를 한정하고 괄호에 "진짜 문서 단위 내비게이션/bfcache에서만 온다"까지 적어둬 `#225`와 모순되지 않는다 / 부분 실패 전에는 재시도 수단이 없다 — 그 상태는 재연결 자동 flush가 담당하는 설계대로다). ④ **추측성·잔여 극미 3건**(세션 만료 시 refresh가 로그인으로 튕길 수 있다 — 재현 근거 없음 / `onClick` 경합 시점의 조용한 no-op 잔존 — `disabled`+안내 분기로 실질 해소되고 남은 창은 render→click 사이 극미 / Never 절 재해석을 사람에게 escalate해야 한다 — 1차 패스가 이미 판정해 Spec Change Log에 근거와 함께 기록했고 새 정보가 없다).

## Design Notes

**왜 CM-B를 새 수동 절차가 아니라 기존 pytest 재실행으로 확인하나:** 12.2~12.5 코드리뷰가 이미 RLS·트리거·CHECK를 실DB로 검증하는 스위트를 만들어 뒀다(각 스토리 리뷰가 이걸 실측 도구로 썼다). 같은 걸 브라우저로 다시 손으로 확인하면 같은 결론을 더 느리고 덜 정확하게 재확인하는 것이라 A2 위반이다 — 재실행 green이 "실시간 전환 후에도 유지"의 근거로 충분하다.

**왜 `#206`·`#215`만 예외로 코드를 고치나:** 다른 defer 항목과 달리 이 둘은 담당 리뷰가 "Story 12.6에서 재실측 후 사람이 판단해 필요하면 그 자리에서 고친다"고 트리거를 명시적으로 이 스토리에 지정해 뒀다(B5 — 회고 약속을 인수조건으로 심는 것). 사람이 상시 붙어있지 않는 자동 실행이므로, "재현되면 고친다"는 판단 기준 자체를 스펙에 미리 못박아 실행 시점에 새로 고민하지 않게 했다.

## Verification

**Commands:**
- `select has_table_privilege('authenticated','public.chat_messages','select');` (로컬 DB 직접 조회) -- expected: `t` (환경 사전 점검, `f`면 `#211` 조치 재적용 후 재확인)
- `cd api && python -m pytest tests/integration/test_chat_idempotency_real_db.py tests/integration/test_chat_realtime_broadcast_real_db.py tests/integration/test_chat_unread_real_db.py -v` -- expected: 전부 pass
- (`#206`·`#215` 중 하나라도 수정을 적용했다면) `cd web && npm run lint && npx tsc --noEmit` -- expected: 0 warnings/errors

**Manual checks (if no CLI):**
- Playwright로 독립된 두 browser context를 열어 각각 `buyer@test.com`/`seller-seed2@test.com`으로 로그인, 시드된 공유 방(`chat_rooms.json`의 buyer_id/seller_id가 이 둘로 매칭되는 방)에서 실시간 송수신을 직접 관찰한다.
- 한쪽 `context.setOffline(true)` → 반대쪽에서 메시지 전송 → `setOffline(false)` → 유실 없음과 배너 텍스트를 직접 확인한다.
- 방에 진입했다가 브라우저 뒤로가기로 목록에 복귀해 배지 값을 직접 확인한다(`#215`).
- 재연결 직후 다시 오프라인으로 전환해 flush 부분 실패를 유도하고, 안내 문구와 재시도 가능 여부를 직접 확인한다(`#206`).

## Auto Run Result

### 2026-07-29 — 구현 + 코드리뷰 결과

**요약:** Epic 12(12.1~12.5)가 만든 실시간 채팅을 구매자·판매자 두 실브라우저 세션(`buyer@test.com`/`seller-seed2@test.com`)으로 실측 검증했다 — 실시간 송수신(새로고침 없이 ~57ms 내 표시), 재연결 배너(끊김~47s 후 텍스트+색 전환, 복귀 시 성공 텍스트+색 후 자동 소멸), 갭보정(오프라인 중 발송된 2건이 재연결 후 유실 없이 병합), 멱등 재전송(DB 정확히 1행, 화면 중복 없음) 모두 실측 확인됐다. 사전 승인된 두 예외(대장 `#206`·`#215`)는 재현을 시도해 둘 다 실제로 재현됐고, 스펙이 지정한 최소 수정을 적용해 종결했다 — 단 `#215`는 스펙이 지정한 구체 메커니즘(`pageshow`+`/chat` 페이지)이 실측으로 반증돼 동일 의도의 다른 배선(`popstate`+루트 레이아웃)으로 대체했다(Spec Change Log 기록). CM-B(RLS·트리거·CHECK)는 기존 실DB pytest 3종(38건) 재실행으로 green 확인. Flutter 앱은 여전히 폴링 기반임을 재확인(`#198` 참조, 미수정). 코드리뷰 4레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 실행 결과 intent_gap 0, bad_spec 0, patch 7건(medium 4·low 3), defer 4건(medium 1·low 3), reject 1건.

**Files changed:**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` — `#206` 최소 수정: 미전송 안내 옆 "다시 보내기" 버튼 추가(`flushQueueRef`로 기존 `flushQueue()` 재호출, 새 전송 경로 없음) + 코드리뷰 patch 3건(오프라인 시 no-op 가드, `role="alert"`를 텍스트에만 적용, 방 전환 시 ref 리셋).
- `web/src/app/(user)/chat/ChatListBfcacheRefresh.tsx` (신규) — `#215` 최소 수정: 뒤로가기로 `/chat` 복귀 시 `popstate` 감지 후 `router.refresh()`(스펙의 `pageshow`+`/chat` 페이지 배치는 실측으로 반증돼 루트 레이아웃 배치로 대체) + 코드리뷰 patch 1건(trailing-slash 정규화).
- `web/src/app/layout.tsx` — 위 컴포넌트를 루트 레이아웃에 마운트.
- `web/src/app/(user)/chat/[roomId]/__tests__/queueRetryWiringContract.test.ts` (신규, 코드리뷰 patch) — 재시도 버튼 배선(`flushQueueRef`) 소스 스캔 계약 테스트.
- `web/src/app/(user)/chat/__tests__/bfcacheRefreshContract.test.ts` (신규, 코드리뷰 patch) — bfcache popstate 가드 배선 소스 스캔 계약 테스트(jsdom 미설치로 실제 렌더링 테스트 대신 이 저장소 기존 컨벤션을 따름).
- `docs/tech-debt.md` — `#206`·`#215` "✅ 해소"로 종결, `#211` 사전 점검 메모, `#198` 재확인 메모, `#219`(`deferred-work.md`의 `DW-8` 이관) 신규 등재, `#220`~`#223`(이번 코드리뷰 defer 4건) 신규 등재.

**Review findings breakdown:**
- patch 7건(medium 4·low 3): 재시도 버튼 오프라인 no-op 가드(low)·`role="alert"` 접근성 수정(medium)·`flushQueueRef` 리셋(low)·trailing-slash 정규화(low)·재시도 버튼 배선 회귀 테스트 신설(medium)·bfcache 가드 배선 회귀 테스트 신설(medium)·스펙 Change Log에 `#215` 메커니즘 정정 기록(medium). 전부 구현 서브에이전트에 위임해 적용, 재검증 green.
- defer 4건(medium 1·low 3): `docs/tech-debt.md` `#220`(재시도 버튼 로딩 표시 없음, low)·`#221`(재시도 버튼 쿨다운 없음, low)·`#222`(bfcache 가드가 문서화 안 된 Next.js 내부 동작 의존, 자동 테스트 부재, medium)·`#223`(popstate 리스너가 앱 전체에 마운트, low).
- reject 1건: 연속 popstate 발생 시 `router.refresh()` 중복 호출 가능성(디바운스 미적용) — 데모 규모에서 무해, A2가 경계하는 불필요한 방어.
- follow-up review recommendation 계산: patch만 집계(defer·reject 제외) — high 0건, medium 4건, low 3건 → `3×4 + 1×3 = 15 ≥ 5` → **true**.

**Verification 수행:**
- `select has_table_privilege('authenticated','public.chat_messages','select');` → `t`(`#211` 재발 없음, 조치 불필요).
- `cd api && python3 -m pytest tests/integration/test_chat_idempotency_real_db.py tests/integration/test_chat_realtime_broadcast_real_db.py tests/integration/test_chat_unread_real_db.py -v` → **38 passed**(오케스트레이터가 직접 재실행해 독립 확인).
- `cd web && npm run lint && npx tsc --noEmit && npm test -- --run` → lint clean·tsc clean·**vitest 288 passed**(패치 전 282 + 신규 6건, 패치 후 오케스트레이터가 직접 재실행해 독립 확인).
- 두 브라우저(Playwright, buyer@test.com/seller-seed2@test.com, 시드 방 `9485e05f-3b63-461c-9d9c-aa1715c25c55`) 실측: 실시간 송수신·재연결 배너(텍스트+색)·갭보정(2건 무손실 병합)·멱등(DB 1행·화면 무중복) 전부 확인. `#206`·`#215` 재현 → 수정 적용 → 재검증 통과. 이 검증 세션이 만든 테스트 메시지(`RT-`·`GAP1/2-`·`IDEMP-`·`FLUSH1/2-`·`RETRY1/2-`·`BADGE/BADGE2-` 접두사)는 오케스트레이터가 DB에서 직접 조회해 중복 없음(멱등)까지 재확인했고, 로컬 dev DB에 그대로 남겨뒀다(스펙 Never 절 — 수동 SQL DELETE로 Realtime Replay 오염 방지).

**Residual risks:**
- `#222`: `#215` 수정이 Next.js의 문서화되지 않은 popstate 처리 순서에 의존한다 — 다음 Next.js 업그레이드 시 브라우저로 재실측 필요(`#207`과 같은 트리거).
- `#220`·`#221`: 재시도 버튼의 로딩 표시·쿨다운 부재 — 데모 규모에서 실제 피해 없음, `isFlushing` state 승격 작업 시 함께 처리.
- `#223`: popstate 리스너가 루트 레이아웃에 있어 전 페이지에서 실행됨 — 내부 가드로 지금은 안전, 같은 패턴 반복 시 `(user)` 그룹 전용 layout 신설 재판단.
- `followup_review_recommended: true` — 이 스토리에 대한 독립 후속 리뷰가 권장된다(패치 점수 15).
- Flutter 앱(app/lib/features/chat/**)은 이번 스토리에서 손대지 않았다 — 여전히 폴링 기반, Epic 16.4로 이관(`#198`).
- 이 스펙 파일은 커밋에 포함하지 않았다(선행 스토리들과 동일 이유 — 커밋하면 HEAD가 움직여 `final_revision`이 어긋난다).

### 2026-07-29 — 독립 후속 리뷰(follow-up review) 결과

**요약:** 1차 패스가 `followup_review_recommended: true`(패치 점수 15)로 권고한 독립 후속 리뷰를 새 세션에서 돌렸다. 코드는 새로 만들지 않고 `dd000bb..ca9ea57` diff(283줄)를 4레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 리뷰했다. **가장 중요한 결과: 1차 패스가 `#206` 회귀 방지용으로 신설한 계약 테스트가 정작 그 회귀를 못 잡는 거짓 초록이었다** — 세 레이어가 각자 뮤테이션으로 실증했다(가드 `!`를 지워 버튼을 완전히 죽여도 3/3 통과). 이 축을 포함해 patch 7건(medium 3·low 4)을 적용하고, defer 3건을 `docs/tech-debt.md` `#224`~`#226`으로 신규 등재, 7건 기각. intent_gap 0·bad_spec 0으로 스펙 인텐트는 손대지 않았다(기록용 Spec Change Log 1건만 추가).

**Files changed (이 패스):**
- `web/src/app/(user)/chat/[roomId]/__tests__/queueRetryWiringContract.test.ts` — 끊김 가드 단언을 `/disconnectedRef\.current/`에서 표현식 전체(`if (!disconnectedRef.current) flushQueueRef.current()`)로 강화(극성 고정) + "안 보는 것"에 도달 가능성 사각지대 명시 + 안내 문구에 같은 문자열이 생겨 `indexOf`→`lastIndexOf`로 라벨 탐색 보정.
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` — 재시도 버튼에 `disabled={isDisconnected}`(조용한 no-op 제거) + `shrink-0 whitespace-nowrap`, 안내 `<span>`에 `min-w-0`(D5) + 미전송 안내 문구를 버튼 존재에 맞게 정정.
- `web/src/app/(user)/chat/__tests__/bfcacheRefreshContract.test.ts` — "안 보는 것"에 제어흐름 도달 가능성 사각지대 명시.
- `docs/tech-debt.md` — `#224`·`#225`·`#226` 신규 등재(기존 항목 무수정).

**Review findings breakdown:** 위 `## Review Triage Log`의 2026-07-29 follow-up 항목 참조. patch 7건(medium 3·low 4) → 점수 `3×3 + 1×4 = 13 ≥ 5` → `followup_review_recommended: true` 유지.

**Verification 수행 (전부 이 세션이 직접 실행):**
- `cd web && npm run lint && npx tsc --noEmit && npm test -- --run` → lint clean · tsc clean · **vitest 288 passed (31 files)**.
- **red→green 실증(B4):** 컴포넌트 가드를 `if (disconnectedRef.current)`로 뒤집음 → `queueRetryWiringContract.test.ts` **1 failed | 2 passed**(강화 전에는 3/3 통과했던 바로 그 축) → 되돌림 → **3 passed**.
- `select has_table_privilege('authenticated','public.chat_messages','select');` → **`t`**(`#211` 재발 없음).
- `TEST_DATABASE_URL=…:55322 pytest tests/integration/test_chat_{idempotency,realtime_broadcast,unread}_real_db.py` → **38 passed**(CM-B 유지 재확인).
- ⚠️ 처음에 로컬 Postgres 포트를 `54322`로 잡았는데 그 포트는 **다른 프로젝트**의 Supabase 컨테이너(`supabase_db_beatmakers`)였다(이 프로젝트는 `55322`). 그 DB에 테스트 픽스처가 `auth.users` 3행을 남겼고, 확인 후 **그 3행만 지정 삭제해 원상복구**(잔여 0건 확인)한 뒤 올바른 포트로 다시 돌렸다. 이 저장소의 DB에는 영향 없음.

**Residual risks:**
- 이번 패치 4건(버튼 `disabled`·nowrap·`min-w-0`·안내 문구)은 **브라우저로 재측정하지 않았다** — 화면에 띄우려면 flush 부분 실패를 다시 유도해야 해 비용이 크고, 변경 자체가 순수 가산적(CSS 클래스·문자열·`disabled` prop)이라 회귀 위험이 없다고 판단했다. D5 준수도 규칙 적용이지 실측이 아니다.
- `#224`(안내 박제) — 실제 재현 순서(부분 실패 → Broadcast 에코 → 버튼 클릭)를 아직 만들어보지 않았다. 처리 시 재현부터 한다.
- `#225`(`/chat` 외 경로의 stale 배지) — 소스와 `#215`의 근본 원인 서술에서 도출했고 나머지 9개 경로를 브라우저로 재측정하지 않았다. 항목에 그 한계를 명시했다.
- `#226`(웹소켓 가드 vs HTTP 전송) — 이번엔 조용한 실패만 없앴고, 가드 존치 여부 자체는 미결.
- 소스 스캔 계약 테스트 2종은 여전히 **도달 가능성**을 보지 못한다(이번에 주석으로 명시). 실제 렌더링 테스트로 바꾸려면 jsdom 도입 결정이 선행돼야 한다(`#222`).
- bmad-loop 장부 점검: `deferred-work.md`의 `DW-1`~`DW-8`은 **전부 이미 `docs/tech-debt.md`에 있다**(`#148`·`#149`·`#164`·`#184`·`#192`·`#203`·`#208`·`#219`) — 이번 실행에서 이관할 신규 DW 항목 없음, 동결 파일 무수정.
- 이 스펙 파일은 커밋에 포함하지 않는다(선행 패스와 동일 이유 — 커밋하면 HEAD가 움직여 `final_revision`이 어긋난다).

### 2026-07-29 — 2차 독립 후속 리뷰(follow-up review) 결과

**요약:** 직전 패스가 `followup_review_recommended: true`(패치 점수 13)로 권고한 후속 리뷰를 새 세션에서 다시 돌렸다. 코드는 새로 만들지 않고 `dd000bb..a5a082e` diff(472줄, 6파일)를 4레이어(adversarial·edge-case-hunter·verification-gap·intent-alignment) 병렬 리뷰했다. **가장 중요한 결과 두 가지:** ① 직전 패스가 "조용한 실패를 없앴다"며 넣은 `disabled={isDisconnected}`와 같은 패스가 고친 안내 문구가 **서로 모순**이었다 — 스펙이 지정한 `#206` 재현 절차가 정확히 "잠긴 버튼을 누르라고 안내하는" 상태를 만든다. ② 이번에 새로 실증한 뮤테이션 3종(`disabled` 삭제 / `pathname`→`hash` / `'use client'` 삭제)이 전부 스위트를 초록으로 통과했고, 그중 `'use client'` 삭제는 **앱 전체의 배포 빌드를 깨뜨리는데 CI에는 `next build` 스텝이 없어** 초록으로 통과한다(직접 재현 확인). patch 5건(medium 4·low 1) 적용, defer 4건을 `docs/tech-debt.md` `#227`~`#230`으로 신규 등재, 18건 기각. intent_gap 0·bad_spec 0으로 스펙 인텐트는 손대지 않았다.

**Files changed (이 패스):**
- `web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx` — `queueStuckNotice` state는 "몇 건 남았나"만 담고, "어떻게 다시 보내나"는 render에서 `isDisconnected`로 갈라 쓴다(잠긴 버튼을 누르라는 거짓 안내 제거).
- `web/src/app/(user)/chat/[roomId]/__tests__/queueRetryWiringContract.test.ts` — `disabled={isDisconnected}` 단언 추가 + 안내 문구 분기 단언(신규 it) 추가 + 버튼 탐색 창을 400자 매직넘버에서 `<Button` 여는 태그 앵커로 교체 + 실행 순서 사각지대(`#230`)를 헤더 주석에 명시.
- `web/src/app/(user)/chat/__tests__/bfcacheRefreshContract.test.ts` — `'use client'` 첫 줄 단언(신규 it) + 가드 대상 `path`가 `window.location.pathname`에서 온다는 단언 추가.
- `docs/tech-debt.md` — `#227`·`#228`·`#229`·`#230` 신규 등재(기존 항목 무수정, 총 230→234항목).

**Review findings breakdown:** 위 `## Review Triage Log`의 2026-07-29 2차 후속 항목 참조. patch 5건(medium 4·low 1) → 점수 `3×4 + 1×1 = 13 ≥ 5` → `followup_review_recommended: true` 유지.

**Verification 수행 (전부 이 세션이 직접 실행):**
- `cd web && npm run lint && npx tsc --noEmit && npm test -- --run` → lint clean · tsc clean · **vitest 290 passed (31 files)**(직전 288 + 신규 단언 2건).
- **red→green 실증(B4) 4종** — 각각 뮤테이션 적용 → 해당 검사 RED 확인 → 복원 → GREEN 확인(채팅 스코프 21건 기준): ① `disabled={isDisconnected}` 삭제 → `1 failed | 20 passed` · ② 안내 문구를 예전처럼 state에 박제 → `1 failed | 20 passed` · ③ `window.location.pathname` → `.hash` → `1 failed | 20 passed` · ④ `'use client'` 삭제 → `1 failed | 20 passed`. 복원 후 `21 passed`.
- `npm run build` → **성공**(전 라우트 빌드 확인). 이어서 `'use client'` 제거 상태로 재실행해 **실패 재현**(`You're importing a module that depends on 'useRouter'/'useEffect' into a React Server Component module`, 2 errors) 후 복원 — `#229`의 근거다.
- `.github/workflows/tests.yml`의 `web` 잡 스텝을 직접 확인: `npm ci` → `npm run lint` → `npm test`(빌드 없음).
- ⚠️ 패치 중 기존 검사 1건을 실제로 깨뜨렸다가 고쳤다 — `roomTopicContract.test.ts`가 `if (remaining.length > 0) { … setQueueStuckNotice(` 사이 **400자**를 창으로 잡아 실패 경로 배선을 고정하는데, 처음에 설명 주석을 그 `if` 블록 **안**에 넣어 창을 밀어냈다(`1 failed | 289 passed`). 검사를 약화시키는 대신 주석을 블록 밖으로 옮겨 창을 원래대로 지켰고, 그 이유를 주석에 남겼다. (같은 종류의 매직넘버 창 취약성이 이번 patch 5번의 근거이기도 하다.)
- 실브라우저 재측정은 하지 않았다(아래 Residual risks).

**bmad-loop 장부 점검:** `deferred-work.md`의 `DW-1`~`DW-8`(전부 `status: open`)은 **이미 전부 `docs/tech-debt.md`에 있다**(`#148`·`#149`·`#164`·`#184`·`#192`·`#203`·`#208`·`#219`) — 이번 실행에서 이관할 신규 DW 항목 없음, 동결 파일 무수정.

**Residual risks:**
- 이번 patch 중 사용자 눈에 보이는 변경(안내 문구 분기)은 **브라우저로 재측정하지 않았다.** 문구를 state에서 render로 옮긴 순수 표현 변경이고 vitest·tsc·lint·`next build`가 전부 초록이지만, 실제 화면에서 두 문장이 어떻게 읽히는지는 사람이 보지 않았다. 다음에 `#206` 재현을 다시 만들 때 함께 확인한다.
- 이번에 추가한 검사 4종은 전부 **소스 스캔**이라 여전히 도달 가능성·실행 순서를 못 본다(`#230`에 등재, 검사 헤더 주석에 명시). 실제 렌더링 테스트로 바꾸려면 jsdom 도입 결정이 선행돼야 한다(`#222`).
- `#229`(CI에 빌드 없음)는 이번에 `ChatListBfcacheRefresh.tsx` **한 파일만** 정적으로 막았다 — RSC 경계 위반 전반은 여전히 CI가 못 본다.
- `#227`(방 전환 시 큐 폐기)·`#228`(Next 내부 동작 의존 2건)은 소스 독해에서 도출했고 브라우저·계측으로 재확인하지 않았다 — 항목마다 그 한계를 명시했다.
- 이 스펙 파일은 커밋에 포함하지 않는다(선행 패스와 동일 이유 — 커밋하면 HEAD가 움직여 `final_revision`이 어긋난다). 즉 SM-E 실측 결과의 서술이 버전 관리 밖에 있다는 구조는 그대로다(intent-alignment 레이어가 지적한 축).
