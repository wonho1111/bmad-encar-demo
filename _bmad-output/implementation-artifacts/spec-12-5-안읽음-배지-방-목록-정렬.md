---
title: '12.5 안읽음 배지 + 방 목록 정렬'
type: 'feature'
created: '2026-07-29'
status: 'done'
baseline_revision: '4ec207519264a6f7ab4ffeb3655e59ec9fd4b1de'
final_revision: '3843c2697467a6ec3076b493e9b2f93071e74d97'
review_loop_iteration: 0
followup_review_recommended: true
context: ['{project-root}/docs/conventions.md']
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 판매자가 문의를 놓친다 — 채팅 진입점(내비 🔔)은 아이콘뿐이라 안읽은 문의가 있는지 알 방법이 없고, 방 목록은 방 생성 시각순이라 오래전에 연 방이 최근 새 메시지가 온 방보다 위에 뜰 수 있다(FR57).

**Approach:** 사용자별·방별 "마지막으로 읽은 시각"을 담는 `chat_room_reads` 테이블(architecture 지정 스키마)을 신설하고, 방 진입 시 그 값을 갱신한다. 안읽음 카운트는 그 값보다 늦고 상대가 보낸 메시지 수(RPC로 집계)로 계산해 내비 배지에 점+숫자로 표기한다. 방 목록은 방별 마지막 메시지 시각(신설 `chat_rooms.last_message_at`, 트리거로 유지)으로 정렬한다.

## Boundaries & Constraints

**Always:**
- 마이그레이션은 `supabase/migrations/`의 **착수 시점 다음 빈 번호**를 쓰고(이 스펙 작성 시점 기준 다음 번호는 `0024` — 구현 시작 시 파일 목록으로 재확인), 0023 이하에만 의존하는 self-contained 파일이어야 한다(에픽 제약).
- `chat_room_reads(user_id, room_id, last_read_at)` 신설(복합 PK `(user_id, room_id)`, 둘 다 on delete cascade) — RLS: 본인 행만 select/insert/update. insert는 그 방의 실제 당사자(buyer 또는 seller)일 때만 허용(0003 `chat_rooms_insert_participant`와 동일 패턴의 EXISTS 검사). update/select는 `auth.uid() = user_id`만으로 충분(방은 안 바뀜). delete 정책 없음(기본 거부).
- `chat_rooms.last_message_at timestamptz not null default now()` 신설 — 마이그레이션 시점에 기존 행 전부를 그 방의 실제 마지막 `chat_messages.created_at`(메시지가 없으면 `chat_rooms.created_at`)으로 백필한다(정렬이 롤아웃 즉시 정확해야 함). 이후 `chat_messages` AFTER INSERT 트리거(SECURITY DEFINER, `0016_chat_room_integrity.sql`의 `enforce_chat_room_seller`와 동일 패턴 — 클라이언트 직접 호출 차단을 위해 anon/authenticated/public 모두에서 EXECUTE 회수)가 그 방의 `last_message_at`을 새 메시지의 `created_at`으로 갱신한다.
- 안읽음 집계는 `chat_unread_count()`(인자 없음, SECURITY INVOKER — 정의자 권한 불필요, 호출자의 기존 RLS로 이미 자기 방만 보임) RPC 하나로 고정한다. 공식(FR57 AC 그대로): 내가 당사자인 방의 `chat_messages` 중 `sender_id <> auth.uid()` 이고 `created_at > coalesce(그 방의 내 chat_room_reads.last_read_at, '-infinity')`인 행의 개수. `authenticated`에만 EXECUTE 부여(anon 회수).
- 방 목록(`web/src/app/(user)/chat/page.tsx`) 정렬 기준을 `created_at`→`last_message_at`로 바꾼다(내림차순 유지, `id` 2차 정렬도 유지 — 동시각 안정화).
- 방 진입(`web/src/app/(user)/chat/[roomId]/page.tsx`, RLS로 당사자 확인이 끝난 지점) 시 서버에서 본인의 `chat_room_reads.last_read_at`을 지금 시각으로 upsert한다(`web/src/lib/chat.ts`에 헬퍼 함수 하나로 — `openOrCreateRoom`과 같은 파일, 같은 "방 단위 동작 단일 출처" 원칙).
- `SiteNav.tsx`의 채팅🔔에 로그인 시 안읽음 총합을 표기한다 — 점(색이 있는 작은 배지) 안에 숫자 텍스트를 넣어 "점+숫자"를 한 요소로 충족시키고, `aria-label`에도 건수를 반영해(예: "채팅, 안읽음 메시지 3건") 비색 신호 중복 원칙(UX-DR22)을 지킨다. 0이면 배지를 렌더하지 않는다. 이 카운트는 `AppHeader.tsx`가 consumer 분기·로그인 상태일 때만 `chat_unread_count()`를 호출해 계산한다(admin 분기·비로그인은 호출 안 함).
- `docs/conventions.md`에 §12.6을 신설해 이 계약(테이블·컬럼·RPC명·갱신 시점)을 기록한다 — Epic 16 Story 16.4(Flutter 안읽음 미러링)가 참조할 단일 출처(12.4의 §12.5 선례와 동일 원칙).

**Block If:** (사람 판단이 필요한 신규 결정 없음 — 스키마·집계공식·정렬기준 전부 architecture-increment-2026-07-12.md·epics-increment-2026-07-12.md AC에 이미 확정돼 있다.)

**Never:**
- 방 목록 각 행에 개별 안읽음 점(per-room indicator)을 추가하지 않는다 — FR57 AC가 요구하는 건 내비 배지(총합)와 정렬뿐이다(과설계 금지, A2).
- 방이 이미 열려 있는 동안(`ChatRoomMessages.tsx` 실시간 구독 중) 새로 도착하는 메시지마다 `last_read_at`을 다시 갱신하지 않는다 — "방 진입/열람 시 갱신"은 페이지 진입 1회로 한정한다. 방을 오래 열어둔 채 여러 건을 라이브로 본 뒤 재진입 없이 나가면 그 메시지들이 다음 진입 전까지 안읽음으로 남는 것은 알려진 범위 밖 edge case로 tech-debt에 등재한다(과설계 방지, 이미 3차 리뷰를 거친 `ChatRoomMessages.tsx`의 구독·큐 상태기계에 손대지 않는다 — A3).
- `ChatRoomMessages.tsx`의 재연결·오프라인 큐잉·갭보정 로직(12.4 완성분)은 이 스토리와 무관 — 손대지 않는다.
- Flutter 앱(`app/lib/**`)은 손대지 않는다 — Epic 16 Story 16.4 전담(12.4와 동일 원칙).
- 이 기능(안읽음·정렬) 전체를 검증하는 새 자동 E2E를 만들지 않는다 — 실시간 채팅 성공 지표는 Story 12.6의 수동 2-브라우저 검증으로 닫기로 에픽 레벨에서 이미 정해져 있다(12.1~12.4와 동일 결정).
- `chat_room_reads`·`chat_rooms.last_message_at`을 되돌리는 마이그레이션을 쓰지 않는다 — DB는 추가만(B3).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 새 문의 첫 메시지 | buyer가 새 방에서 첫 메시지 전송 | 트리거가 `last_message_at` 갱신 → seller 목록에서 그 방이 최상단, seller 배지 +1 | 없음 |
| 안읽던 방에 진입 | seller가 미열람 방을 처음 연다 | 서버 렌더 시 `last_read_at`이 지금 시각으로 upsert됨 → 다음 페이지 로드부터 그 방의 과거 메시지는 배지 집계에서 빠짐 | upsert 실패 시 콘솔 로그만(화면은 비차단 — 배지는 부가 정보) |
| 내 발신만 있는 방 | 상대가 아직 응답 안 함(마지막 메시지가 내 것) | 안읽음 0(`sender_id <> auth.uid()` 조건으로 본인 발신 제외) | 없음 |
| 롤아웃 시점 기존 대화 | 마이그레이션 적용 전부터 있던 방 | 정렬은 백필 덕에 즉시 정확. 안읽음은 이번이 최초 계산이라 그 방에서 상대가 보낸 과거 메시지 전부가 1회성으로 안읽음 집계에 잡힘(진입하면 해소) | 없음(공식이 의도한 최초 상태 — 별도 백필로 숨기지 않는다) |

</intent-contract>

## Code Map

- `supabase/migrations/0024_chat_room_reads.sql` (신규, 번호는 착수 시 재확인) -- `chat_room_reads` 테이블+RLS, `chat_rooms.last_message_at` 컬럼+백필+AFTER INSERT 트리거(SECURITY DEFINER), `chat_unread_count()` RPC(SECURITY INVOKER).
- `web/src/lib/chat.ts` -- `markChatRoomRead(supabase, roomId, userId)` 헬퍼 추가(upsert, 실패 시 console.error만).
- `web/src/app/(user)/chat/[roomId]/page.tsx` -- 방 조회 성공(당사자 확인 통과) 직후 `markChatRoomRead` 호출.
- `web/src/app/(user)/chat/page.tsx` -- `.order('created_at', ...)` → `.order('last_message_at', ...)`(id 2차 정렬 유지).
- `web/src/components/layout/AppHeader.tsx` -- consumer 분기·로그인 시 `chat_unread_count()` 호출해 `unreadCount`를 `SiteNav`에 전달(비동기 컴포넌트로 전환).
- `web/src/components/layout/SiteNav.tsx` -- `unreadCount?: number` prop, 채팅🔔에 점+숫자 배지(0이면 미표시) + aria-label 갱신.
- `web/src/lib/__tests__/chat.test.ts` (신규) -- `markChatRoomRead` 단위 테스트.
- `web/src/components/layout/SiteNav.test.ts` -- unreadCount 배지 렌더 케이스 추가.
- `docs/conventions.md` -- §12.6 신설(안읽음 계약, Epic 16.4 단일 출처).
- `docs/tech-debt.md` -- 신규 2건: (a) `AppHeader`의 RPC 호출이 대장 `#183`(getUser 증폭) 층에 하나 더 얹힘, (b) 방이 열린 채 라이브로 본 메시지가 재진입 전까지 안읽음으로 남는 edge case.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0024_chat_room_reads.sql` -- 테이블·RLS·컬럼·백필·트리거·RPC 전부 이 한 파일에(0003/0020 관례처럼 동거) -- FR57 스키마 토대.
- `web/src/lib/chat.ts` -- `markChatRoomRead` 추가 -- 방 단위 동작 단일 출처 유지.
- `web/src/app/(user)/chat/[roomId]/page.tsx` -- 당사자 확인 후 `markChatRoomRead` 호출 배선 -- "진입 시 갱신"(AC).
- `web/src/app/(user)/chat/page.tsx` -- 정렬 컬럼 교체 -- "최신 문의 순"(AC).
- `web/src/components/layout/AppHeader.tsx`, `SiteNav.tsx` -- 안읽음 총합 계산·배지 표기 배선 -- "내비 배지 점+숫자"(AC).
- `web/src/lib/__tests__/chat.test.ts`, `web/src/components/layout/SiteNav.test.ts` -- 신규 로직 단위테스트 -- B9(실행되는 검사로 고정).
- `docs/conventions.md` -- §12.6 신설 -- Epic 16.4 단일 출처, B8.
- `docs/tech-debt.md` -- 위 2건 등재 -- B8, 기존 항목 무수정.

**Acceptance Criteria:**
- Given `chat_room_reads` 마이그레이션, when 적용하면, then self-contained하게 생성되고 기존 RLS(0003 참여자 한정)와 충돌 없이 공존한다(FR57).
- Given 로그인 사용자가 자기 방들을 가지고 있으면, when 채팅 진입점(내비 🔔)을 보면, then `created_at > last_read_at AND sender_id != {me}`로 집계된 안읽음 카운트가 점+숫자 텍스트로 표시된다(I6, 0이면 배지 없음).
- Given 여러 채팅방이 있으면, when 방 목록(`/chat`)을 열면, then 최신 문의(마지막 메시지 시각) 순으로 정렬된다.
- Given 안읽음 배지가 N을 표시하던 중 그중 한 방에 진입했다가 방 목록으로 돌아오면, when 배지를 다시 보면(같은 세션 재방문·새로고침), then 그 방의 메시지 수만큼 총합이 줄어 있다(더 볼 방이 없으면 배지 자체가 사라진다).
- Given 채팅 무결성 3중 장치(RLS·트리거·CHECK), when 이 스토리의 변경 전후를 비교하면, then 동일하게 유지된다(CM-B, 기존 0003/0016/0023 무수정으로 확인).

## Spec Change Log

## Review Triage Log

### 2026-07-29 — Review pass (후속, 3차)
- intent_gap: 0
- bad_spec: 0
- patch: 8: (high 0, medium 4, low 4)
- defer: 4: (medium 1, low 3)
- reject: 15
- addressed_findings:
  - `medium` `patch` **관리자가 소비자 채팅방(`/chat/<id>`)을 열면 `markChatRoomRead`가 당사자가 아닌 방에 읽음 기록을 시도했다**(adversarial+edge-case-hunter 교차 지적 → 실브라우저로 재현). 2차 패스가 `chat_unread_count()`에서 고친 것과 **정확히 같은 축**을 한 파일 옆에서 놓친 것이다 — `0005`의 `chat_rooms_select_admin (using is_admin())`도 참여자 정책과 OR로 합쳐지므로 `!room` 가드 통과는 "당사자다"를 뜻하지 않는다. 주석은 "당사자 확인이 끝난 지점(RLS 통과)"이라고 **사실과 다르게** 적혀 있었다. `buyer_id`/`seller_id` 직접 대조 가드를 추가. **실측 red→green**: 가드 없는 상태로 관리자 방문 시 서버 로그에 `42501 new row violates row-level security policy for table "chat_room_reads"`가 재현됐고, 가드 적용 후 같은 방문에서 에러 0건·읽음 행 0건.
  - `medium` `patch` 2차 패스가 만든 **배선 계약 테스트가 `await`도 호출 위치도 고정하지 않았다**(verification-gap 지적, 실측). `await`를 지워도 lint·tsc·vitest 282건이 전부 green이었다 — async 서버 컴포넌트의 떠다니는 promise는 응답 전에 완료된다는 보장이 없고 `markChatRoomRead`는 실패를 콘솔로만 삼키므로, 배지가 조용히 안 줄어드는 회귀를 그 테스트가 못 잡았다. `await` 앵커 + "`!room` 가드와 당사자 대조보다 뒤"라는 위치 단언 추가. **깨뜨려 red 3종 확인 후 복원.**
  - `medium` `patch` **`last_message_at` 트리거 테스트(⑥)가 트리거를 통째로 비활성화해도 통과하는 공허한 검사였다**(edge-case-hunter가 실DB로 실증). 원인: 픽스처 전체가 한 트랜잭션이라 `now()`가 고정되는데 방의 `last_message_at` 기본값도 `now()`라, `later = now()`로 둔 순간 트리거가 값을 옮기기 **전부터** 단언이 성립했다. `later`를 확실히 뒤(+1h)로 옮기고 "초기값 ≠ later" 전제 단언 추가. **`alter table ... disable trigger`로 red 확인 → 복원해 green 확인.**
  - `medium` `patch` **0024의 백필 UPDATE가 어떤 검사에서도 데이터가 있는 상태로 실행된 적이 없었다**(verification-gap 지적) — CI의 `api-db` 잡도 마이그레이션 게이트도 빈 DB에 적용하므로 이 문장은 항상 0행에 대해 돌았다. 그런데 이건 운영 DB의 기존 방 **전부**의 정렬 기준을 한 번에 정하는 일회성 코드다. 실DB 테스트 ⑩ 신설 — 공식을 사본으로 다시 적지 않고 **마이그레이션 파일에서 문장을 읽어와 실행**하고 기대값은 파이썬이 독립 계산한다(사본이 같이 틀리는 `#146`류 방지). **red 2종 실증**: `max(`→`min(`으로 변조 시 값 불일치로 red, `coalesce(..., r.created_at)` 폴백 제거 시 `NotNullViolation`으로 red(= 운영에서 마이그레이션이 배포 도중 죽는 바로 그 모양).
  - `low` `patch` ⑧ 테스트의 두 줄 주석이 **바이트 단위로 중복**돼 있었다(adversarial·verification-gap 독립 지적) → 제거.
  - `low` `patch` `_unread_count_as` 헬퍼가 `role`만 되돌리고 `request.jwt.claim.sub`는 두고 나왔다(adversarial 지적). `set local`은 트랜잭션 끝까지 살아 있고 이 파일은 한 트랜잭션이라, 이후 문장들이 "남의 신분이 박힌 채" 실행된다 — 지금은 롤이 postgres로 돌아가 무해하지만 `auth.uid()`를 보는 트리거가 하나만 생겨도 조용히 틀린 초록이 된다 → 둘 다 reset.
  - `low` `patch` 정렬 키 계약 정규식이 **파일 전체(주석 포함)** 를 인덱스로 스캔했다(adversarial+edge-case-hunter 교차 지적). 이 리포는 실제로 `conventions.md` §12.6에 같은 형태의 `.order(...)` 예시 문자열을 갖고 있어, 주석 한 줄이 인덱스를 밀면 거짓 red/green이 난다 → 주석 제거 후 `from('chat_rooms')` 체인으로 범위를 좁히고 컬럼명 문자군을 `[a-z0-9_]`로 넓혔다.
  - `low` `patch` §12.6이 Epic 16.4의 단일 출처를 자처하면서 **소스 주석에만 있던 계약 2건을 담지 않았다**(adversarial 지적) → 배지 색 `bg-red-600`(#DC2626, 흰 글자 대비 4.83:1 — `red-500`은 3.76:1로 AA 미달)과 "RPC 실패 시 배지 미표시·렌더 비차단"을 명시. 위 관리자 축(당사자 확인은 조회 0건 여부가 아니라 `buyer_id`/`seller_id` 대조)도 §12.6에 못박았다.
- 기각 15건 — **관리자 로그인 판정을 `email` prop이 아니라 세션에서 직접 하라**(호출부 11곳 전부 이미 `getUser()` 결과를 넘기고 있고, 고치면 대장 `#183`·`#209`의 `getUser` 증폭 층에 호출이 하나 더 얹힌다) · `AppHeader`에 try/catch·비숫자 폴백 추가(supabase-js는 fetch 실패를 `{error}`로 돌려주고 `createClient()`가 던지는 조건은 앱 전체가 이미 죽은 상태 — 불가능 시나리오용 방어, A2) · `not null default now()`가 B3의 "새 열은 nullable" 규칙 위반(스펙 Always와 architecture가 이 형태를 명시적으로 지정했다 — 스코프 권한은 인텐트에 있다) · anon EXECUTE 권한 테스트(2차 패스에서 이미 판단했고 이번 검증에서 권한 실측도 재확인 — `auth.uid()`가 null이라 결과가 0이라 관측 가능한 결과가 없다) · RLS 메시지 대조가 로케일 의존적(깨지면 **시끄러운 red**이지 조용한 green이 아니다) · 트리거가 매 메시지마다 `chat_rooms` 행 락을 잡는다(실측된 성능 문제 없음, 데모 규모 — 2차 패스의 인덱스·조건부 UPDATE 기각과 동류) · 배포 순서 주의(B3·런북이 이미 규정, 2차 패스 기각과 동일) · `#211`이 세션 내 조치일 뿐이다(항목 자체가 이 사실과 정식 처방을 이미 기록) · `#213` 본문의 "1초 미만" 근거가 미실측(대장 기존 항목은 오케스트레이터 소유 — 이 세션이 고칠 자리가 아니다) · 99+ 상한의 근거가 CSS와 어긋난다(2차 패스가 내린 결정이고 접근성 분기는 이미 해소됨, 실측된 레이아웃 문제 없음) · 렌더 시점 upsert가 메시지 전달 전에 커밋된다(스펙 Always가 "방 진입 시 서버에서 upsert"를 명시 — 프리페치 축은 2차 패스가 실측으로 반증 완료) · `0024` 컬럼 주석의 "유일한 쓰기 통로" 문구가 백필과 모순(이미 적용된 마이그레이션 파일을 주석 때문에 고치는 대가가 더 크고, 바로 다음 절이 "authenticated 직접 UPDATE"로 범위를 한정한다) · seed-local이 CI에서 안 돈다(대장 `#122`가 이미 등재) · 기존 e2e가 접근성 이름 부분일치에 의존(2차 패스 기각과 동일).
- defer 4건(대장 신규 등재, 기존 항목 무수정) — `#215` **뒤로가기로 방 목록에 돌아오면 배지가 읽기 전 값으로 되살아난다**(실브라우저 실측: DB는 1인데 뒤로가기 후 배지 2, 새로고침·정방향 링크는 정상 — Next Router Cache가 스크롤 복원용으로 back/forward를 항상 캐시에서 되살린다. `#210`과 증상은 같고 원인이 달라 오진 방지용으로 따로 등재) · `#216` `markChatRoomRead`의 upsert가 단조증가가 아니다(같은 스토리가 `last_message_at`에는 일부러 넣은 `greatest()` 가드가 짝 컬럼엔 없다 — `#213`과 수정 지점이 같은 한 줄이라 함께 닫도록 트리거 지정) · `#217` `chat_rooms` 시드 삽입문도 명시 컬럼 목록으로 바뀌어 `#146`이 예고한 재발이 실제로 일어났다(`#146` 본문의 현황 서술이 낡아 다음 사람을 오도하므로 정정 기록으로만 등재, 처방은 `#146`이 정본) · `#218` 관리자가 소비자 방 라우트를 열면 Realtime 구독이 CHANNEL_ERROR로 계속 끊긴다(이번 관리자 축 검증 중 부수 관측, 12.2~12.4의 인가와 0005 정책이 만나는 선재 결함).

### 2026-07-29 — Review pass (후속, 2차)
- intent_gap: 0
- bad_spec: 0
- patch: 10: (high 0, medium 4, low 6)
- defer: 2: (low 2)
- reject: 14
- addressed_findings:
  - `medium` `patch` **`chat_unread_count()`가 "내가 당사자인 방" 조건을 SQL에 쓰지 않고 RLS에 맡겨, 관리자에게 플랫폼 전체 메시지 수가 집계됐다**(edge-case-hunter 지적 → 실DB·실브라우저로 재현). 0005의 `chat_messages_select_admin (using is_admin())`이 참여자 정책과 OR로 합쳐지므로 관리자에겐 전 메시지가 보인다. 실측: 참여 방 0개인 관리자에게 `chat_unread_count()` = 10(= DB 전체 메시지 수), 일반 구매자는 0(대조군). 실브라우저(prod 빌드, admin@test.com, `/search`)에서도 배지 "10"·aria-label "안읽음 메시지 10건"으로 재현됨 — `/`는 admin을 `/admin`으로 리다이렉트하지만 `/search`·`/chat`·`/wishlist`·`/account`·`/ai`는 리다이렉트가 없어 실제 도달 가능한 경로다. FR57 AC·§12.6이 규정한 공식이 원래 "내가 당사자인 방"이므로 새 규칙이 아니라 **빠진 조건의 복원**이다. 전진 원칙(B3·§9.1)에 따라 0024를 고치지 않고 `0025_chat_unread_participant_scope.sql`을 신설해 `chat_rooms` 조인을 함수 안에 넣었다.
  - `medium` `patch` 위 결함을 잡는 회귀 검사가 없었다 → `test_chat_unread_real_db.py`에 ⑦(당사자 아닌 방 배제, 양성 대조 포함)·⑧(관리자 누수)을 신설. **⑧은 패치 전 실제로 red(12 ≠ 0)를 확인한 뒤 0025 적용으로 green으로 되돌렸다.**
  - `medium` `patch` 신설 실DB 테스트가 **거부 경로만** authenticated 롤로 검사하고 통과해야 하는 쓰기는 전부 DSN 소유자(postgres) 권한으로 실행해, 정책이 과하게 좁아지거나 GRANT가 빠져 **정상 사용자의 읽음 기록이 막히는** 회귀를 잡지 못했다(verification-gap 지적 — 대장 `#211`이 실측한 로컬 붕괴가 정확히 이 축이고, 증상은 `markChatRoomRead`가 실패를 삼켜 조용하다) → ⑨ 신설(당사자의 INSERT + 재진입 `on conflict do update`가 authenticated 롤에서 실제로 통과하는지).
  - `medium` `patch` 방 목록 정렬 키와 방 페이지의 `markChatRoomRead` 호출 배선이 **어떤 검사에도 안 잡혔다**(verification-gap+intent-alignment 교차) — `.order('last_message_at')`를 `created_at`으로 되돌리거나 호출 줄을 지워도 lint·tsc·vitest·pytest 전부 green. 1차 패스가 "이 레포는 서버 페이지 컴포넌트를 단위테스트하지 않는다"로 기각했으나, 같은 레포에 이미 **소스 계약 스캔** 선례(`roomTopicContract.test.ts`·`AppHeader.test.ts`)가 있어 기각 근거가 성립하지 않았다 → `web/src/app/(user)/chat/__tests__/unreadWiringContract.test.ts` 신설(정렬 1·2차 키 + 호출 인자 순서 고정). **두 줄을 각각 일부러 깨뜨려 red 확인 후 복원해 green 확인.**
  - `low` `patch` 배지 상한 "99+"가 **aria-label에도** 적용돼, 스크린리더 사용자만 뭉갠 값을 받았다(intent-alignment 지적 D3). 상한의 이유는 작은 원형 배지의 레이아웃 사정이라 화면 낭독엔 해당되지 않는다 — 보이는 배지만 "99+"로 누르고 `aria-label`은 정확한 건수를 유지하도록 수정(UX-DR22 비색 신호 중복의 취지 복원). §12.6에도 명시.
  - `low` `patch` 배지 색 `bg-red-500`(#EF4444)은 흰 글자 대비 **3.76:1**로 AA(4.5:1) 미달이었다(10px 소형 텍스트). `bg-red-600`(#DC2626, 4.83:1)로 교체 — 라이트·다크 양쪽에서 같은 값을 쓴다.
  - `low` `patch` RLS 거부 테스트 2건이 `sqlstate == '42501'`만 봤다 — Postgres는 **RLS 위반과 GRANT 누락 모두 42501**이라, 대장 `#211`류로 환경이 깨진 상태에서도 초록이 됐을 검사였다(adversarial 지적) → 에러 메시지에 `row-level security policy`가 포함되는지 함께 단언.
  - `low` `patch` `AppHeader`의 RPC 실패 폴백 분기가 한 번도 실행되지 않았다(하네스에 `error` 필드는 있는데 채우는 테스트가 없었다) — 이 폴백이 깨지면 소비자 페이지 8곳이 배지 하나 때문에 통째로 500이 된다 → 실패 케이스 테스트 신설.
  - `low` `patch` `AppHeader.test.ts` 비로그인 케이스가 `siteNavNodes[0]`를 길이 단언 없이 읽어, **내비가 통째로 사라져도 통과**하는 검사였다(adversarial 지적) → `toHaveLength(1)` 추가.
  - `low` `patch` 신설 pytest 파일이 `conftest.py`의 공유 헬퍼(`_DSN`·`_create_user`·`_insert_listing`·`pytestmark`)를 사본으로 다시 구현했다 — conftest 자체가 그 복제 때문에 생긴 파일이고(대장 `#188`, 복제가 실제로 role 하드코딩 결함을 한 번 만들었다) docstring이 import를 지시한다 → 사본 제거하고 import로 교체.
- 기각 14건 — **프리페치가 방을 읽음 처리한다**는 지적(가장 파급이 큰 후보라 dev·prod 빌드 양쪽에서 실측: 목록만 열고 두 링크를 호버해도 `chat_room_reads` 행 0건·방 라우트 요청 0건. 양성 대조로 실제 클릭 시엔 행 1건 생성 확인 — 재현되지 않는다) · 롤아웃 시점 `chat_room_reads` 백필(스펙 I/O 매트릭스가 "별도 백필로 숨기지 않는다"고 명시) · 방별 개별 안읽음 표시(스펙 Never) · `#211` GRANT를 마이그레이션으로 커밋(대장에 정식 처방이 이미 등재됨, 프로젝트 전체 범위) · 배포 순서 주의(만드는 쪽→읽는 쪽은 CLAUDE.md B3·runbook이 이미 규정) · `chat_rooms(last_message_at desc)` 인덱스(실측된 성능 문제 없음, 데모 규모 — A2) · 트리거의 무조건 UPDATE를 조건부로(같은 이유) · RPC 실패와 0을 구분해 표시(스펙이 "실패 시 배지 없음, 비차단"으로 이미 규정) · 시드의 `select *` → 명시 컬럼(NOT NULL 컬럼 때문에 불가피, 실패는 시끄럽게 난다) · 백필 공식이 마이그·시드·트리거 3벌(의도된 형태 차이) · 뒤로가기 시 배지가 즉시 안 줄어듦(스펙 I/O 매트릭스가 "다음 페이지 로드부터"로 이미 규정) · 기존 e2e가 접근성 이름 부분일치에 의존(현재 통과, 고정 비용이 이득보다 큼) · `chat_unread_count()` EXECUTE 권한 테스트(anon은 `auth.uid()`가 null이라 결과가 0이고 RLS도 별도로 막는다 — 실익 없음) · upsert에 타임아웃 추가(과설계).
- defer 2건(대장 신규 등재, 기존 항목 무수정) — `#213` `last_read_at`을 DB `now()`가 아니라 web 서버 시계가 정한다(두 시계 비교 + 클라이언트가 값을 정하는 구조, B9 축 — 피해는 1초 미만 오차 구간과 자해 경로뿐이라 RPC 신설 비용이 더 크다) · `#214` `last_message_at` 트리거가 INSERT만 봐서 관리자가 마지막 메시지를 지우면 그 방이 목록 상단에 영구 고정된다(`greatest()` 단조증가 가드 때문에 되돌아갈 길도 없다).

### 2026-07-29 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 6: (high 0, medium 2, low 4)
- defer: 1: (low 1)
- reject: 8
- addressed_findings:
  - `low` `patch` **`chat_messages_touch_room_last_message` 트리거가 `last_message_at`을 조건 없이 덮어써, 커밋 순서가 실제 시각순과 어긋나면(동시 전송 등) 정렬 기준이 더 이른 시각으로 되돌아갈 수 있었다**(adversarial+edge-case-hunter 교차 지적, 시드 스크립트 자체가 이미 겪은 현상과 동종). `set last_message_at = greatest(last_message_at, new.created_at)`로 단조증가만 허용하도록 수정.
  - `low` `patch` `docs/conventions.md` §12.6이 **트리거 이름과 함수 이름을 혼동**해, 트리거 이름을 `chat_rooms_touch_last_message`(실제로는 함수명)라고 적어놨다(adversarial 지적). Epic 16.4가 이 문서를 SQL 검색의 단일 출처로 참조하므로 정정(실제 트리거명 `chat_messages_touch_room_last_message` 명시).
  - `low` `patch` `chat_room_reads_update_own` RLS 정책이 INSERT 정책과 달리 **참여자 재검증이 없어**, 크래프트된 UPDATE로 자신의 읽음 행의 `room_id`를 자신이 당사자 아닌 방으로 재지정할 수 있었다(edge-case-hunter 지적 — 실측: 자기 자신에게만 무해하지만 INSERT 정책과의 방어 수준 불일치). UPDATE의 `with check`에도 동일한 참여자 EXISTS 검사를 추가.
  - `low` `patch` `chat_unread_count()`가 `set search_path = public`을 써서, 같은 파일의 다른 DEFINER 함수(`chat_rooms_touch_last_message`)·0016·0023의 기존 관례(`search_path = ''`)와 어긋났다(adversarial 지적). 본문이 이미 전부 `public.` 접두이므로 동작 변화 없이 `''`로 통일.
  - `medium` `patch` 안읽음 배지 숫자에 **상한(예: 99+)이 없어**, 스펙 I/O 매트릭스가 이미 명시한 "롤아웃 시점엔 과거 메시지 전부가 1회성으로 잡힌다" 시나리오에서 3자리 이상 숫자가 작은 원형 배지를 깨뜨릴 수 있었다(adversarial+edge-case-hunter 교차 지적). 99 초과 시 "99+"로 표기하도록 `SiteNav.tsx` 수정 + 테스트 케이스 추가.
  - `medium` `patch` 이 리포의 확립된 관례(0020→`test_view_count_rpc_real_db.py`, 0022→`test_chat_idempotency_real_db.py`, 0023→`test_chat_realtime_broadcast_real_db.py`)와 달리, **신규 RPC(`chat_unread_count`)·트리거(`chat_rooms_touch_last_message`)·RLS(`chat_room_reads`)를 실제 Postgres로 검증하는 짝 테스트가 없었다**(verification-gap+intent-alignment 교차 지적, 독립적으로 각자 발견). 이번 세션의 수동 REST 검증(안읽음 카운트 계산·감소·본인 발신 제외·제3자 RLS 거부·백필)은 실측됐지만 회귀를 계속 잡지는 못한다 — 같은 패턴으로 `api/tests/integration/test_chat_unread_real_db.py` 신설(RLS 참여자 검사·안읽음 공식 경계값·트리거의 out-of-order 커밋 처리를 실제 롤로 확인).
- 기각 8건 — `markChatRoomRead` 실패가 console.error만 남기고 재시도가 없다는 지적(이 파일·`increment_listing_view`·`chat/page.tsx` 목록 조회 실패 등 이 레포 전체가 이미 쓰는 "비차단 배경 쓰기는 콘솔 로그만" 관례와 동일 — 이 스토리가 새로 만든 패턴이 아니다) · `AppHeader`가 비동기로 바뀌며 모든 소비자 페이지 렌더가 RPC 완료를 기다리게 됐다는 지적(대장 `#209`가 이미 같은 축을 등재해 다뤘고, 어차피 이 페이지들은 이미 `getUser()`·프로필 조회로 순차 대기 중이었다 — 새로운 결합 유형이 아니다) · `chat_room_reads`가 명시 GRANT 없이 플랫폼 기본 권한에 의존해 대장 `#211`과 같은 유형의 취약점을 반복한다는 지적(맞는 지적이나, 이 프로젝트의 다른 모든 테이블도 동일 패턴이라 이 테이블 하나만 예외로 만들면 일관성만 깨뜨린다 — `#211`이 이미 프로젝트 전체 대상의 정식 처방을 등재해 뒀다) · Supabase 클라이언트에 `Database` 제네릭이 없어 테이블/RPC 이름 오타를 tsc가 못 잡는다는 지적(레포 전체의 기존 패턴이라 이 스토리 범위 밖, A3) · 스펙 Verification 절에 "방을 열어둔 채 봐도 배지가 안 줄어드는" 알려진 edge case를 확인하는 수동 체크가 없다는 지적(그 축은 새 로직이 아니라 "호출을 안 함"이므로 검증할 새 동작이 없다) · 방 목록 정렬 컬럼 교체(`chat/page.tsx`)에 대응하는 자동 테스트가 없다는 지적(이 레포는 서버 페이지 컴포넌트 자체를 단위테스트하지 않는 기존 관례이고, 신설 real-db 테스트가 정렬 기준값의 정확성은 이미 커버한다) · `chat/[roomId]/page.tsx`가 `markChatRoomRead`를 실제로 호출하는지 확인하는 테스트가 없다는 지적(위와 동일 이유) · 대장 `#211`의 세션 내 임시 조치가 파일로 남지 않아 diff만으로는 "검증됨"이 재현되지 않는다는 지적(`#211` 자체가 이미 이 사실과 정식 처방을 상세히 기록해 뒀다 — 별도 조치 불필요).
- defer 1건(대장 신규 등재) — `#212` `chat_unread_count()`가 시간 창 없이 사용자의 전체 대화 이력을 매번 스캔한다(FR57 공식 자체가 시간 창을 두지 않으므로 정확성 문제는 아니고, 메시지가 누적될수록 커지는 조회 비용 축 — 데모 규모에서는 무해, 실사용 규모에서 재판단).

## Design Notes

**왜 `chat_room_reads`가 별도 테이블인가(2컬럼 추가안 대신):** architecture-increment-2026-07-12.md가 이 스키마(`chat_room_reads(user_id, room_id, last_read_at)`)를 이미 지정했다. 대안(`chat_rooms`에 `buyer_last_read_at`/`seller_last_read_at` 2컬럼)도 동작은 하지만, `chat_rooms`는 0003 주석이 "방 메타는 불변"이라 명시한 테이블이라 UPDATE 정책 자체가 없다 — 그 불변성을 깨지 않고도 별도 테이블(0018 wishlists와 동일한 "본인 소유 관계 테이블 + 단순 RLS" 패턴)로 풀 수 있어 기존 불변식을 그대로 둔다.

**`chat_unread_count()`가 SECURITY DEFINER가 아니라 INVOKER인 이유:** `increment_listing_view`(0020)·`enforce_chat_room_seller`(0016)는 호출자가 RLS상 볼 수 없는 데이터(다른 사람 소유 매물)를 조작·조회해야 해서 DEFINER가 필요했다. 이 RPC는 정반대다 — 호출자 자신의 RLS 그대로(자기 방·자기 메시지·자기 read 상태만)로 집계해도 정확한 답이 나오므로, 굳이 정의자 권한으로 승격할 이유가 없다(A2, 최소 권한).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 warnings.
- `cd web && npx tsc --noEmit` -- expected: 0 errors.
- `cd web && npm test` -- expected: 기존 + 신규 vitest 전부 green.

**Manual checks (if no CLI):**
- 로컬 Supabase 스택에 마이그레이션 적용 후, 기존 시드 채팅방들의 `chat_rooms.last_message_at`이 각 방의 실제 마지막 `chat_messages.created_at`과 일치하는지 psql로 확인(백필 검증).
- buyer/seller 두 시드 계정으로 실제 로그인해 문의 방을 만들고 메시지를 주고받아, seller 내비 배지 숫자가 실제 안읽은 메시지 수와 일치하는지, 방에 진입하면 배지가 그 방만큼 줄어드는지 실측 확인(psql로 `chat_room_reads.last_read_at` 갱신도 함께 확인).
- 제3자 계정(그 방의 당사자가 아닌 사용자)으로 로그인해 `chat_room_reads`에 다른 방의 행을 upsert 시도 → RLS로 거부되는지 확인(참여자 검사 검증).

## Auto Run Result

### 2026-07-29 — 후속 리뷰 패스(3차) 결과

**요약:** `status: done`이던 이 스토리에 독립 후속 리뷰를 한 패스 더 돌렸다(4개 레이어 병렬). **가장 큰 발견은 2차 패스가 고친 것과 똑같은 축을 한 파일 옆에서 놓쳤다는 것** — 2차는 안읽음 RPC에 "내가 당사자인 방" 조건을 복원했는데, 방 페이지의 읽음 기록 호출은 여전히 "RLS 조회가 0건이 아니다 = 당사자다"라고 가정하고 있었다(주석에도 그렇게 적혀 있었다). 관리자에게는 그 가정이 깨져 방문할 때마다 42501이 조용히 쌓였다 — 실브라우저로 재현하고 가드를 넣어 닫았다. 나머지는 **검사가 검사처럼 보이기만 하던 자리 3건**(트리거를 꺼도 통과하는 테스트, `await`를 지워도 통과하는 배선 계약, 데이터가 있는 상태로는 한 번도 실행된 적 없는 백필문)과 문서·테스트 위생 4건이다. 총 patch 8건(medium 4·low 4), defer 4건(대장 `#215`~`#218`), 기각 15건. intent_gap·bad_spec 0건.

**Files changed (이번 패스):**
- `web/src/app/(user)/chat/[roomId]/page.tsx`(수정) — `markChatRoomRead` 호출 앞에 `buyer_id`/`seller_id` 직접 대조 가드 추가. 사실과 달랐던 "당사자 확인이 끝난 지점(RLS 통과)" 주석을 정정.
- `web/src/app/(user)/chat/__tests__/unreadWiringContract.test.ts`(수정) — `await` 앵커 + 호출 위치 단언(`!room` 가드·당사자 대조보다 뒤) 추가, 정렬 키 스캔을 주석 제거 후 `from('chat_rooms')` 체인으로 한정, 컬럼명 문자군 확장.
- `api/tests/integration/test_chat_unread_real_db.py`(수정) — ⑩ 백필문 실행 검사 신설(마이그레이션 파일에서 문장을 읽어와 실행), ⑥ 공허했던 트리거 검사 수정(`later`를 기본값 뒤로 + 전제 단언), `_unread_count_as`가 jwt sub도 reset, 중복 주석 제거.
- `docs/conventions.md`(수정) — §12.6에 ① "당사자 확인"은 조회 0건 여부가 아니라 `buyer_id`/`seller_id` 대조라는 계약(관리자 OR 합성 근거 포함) ② 배지 색 대비 하한(`bg-red-600`, 4.83:1) ③ RPC 실패 시 배지 미표시·렌더 비차단을 명시(Epic 16.4 단일 출처).
- `docs/tech-debt.md`(수정) — 신규 4건 `#215`(뒤로가기 시 배지가 옛 값으로 복원)·`#216`(읽음 시각 upsert가 단조증가 아님)·`#217`(`chat_rooms` 시드도 명시 컬럼 목록 — `#146` 현황 정정)·`#218`(관리자가 소비자 방 라우트를 열면 Realtime CHANNEL_ERROR). 기존 항목은 건드리지 않았다.

**Verification 수행 (오케스트레이터가 직접 실행):**
- `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(**282 passed**) · `api/tests/integration/`(**77 passed**, 이전 76 + 신설 ⑩) · `python3 scripts/check_migrations.py`(0001~0025 전량 적용 + 프로브 3건 통과).
- **깨뜨려 red 확인 → 복원해 green 확인**(B4, 이번 패스 6종): ① 트리거 비활성화 → ⑥ red(이전엔 이 상태에서도 green이었다) ② 백필 `max(`→`min(` → ⑩ red ③ 백필 `coalesce` 폴백 제거 → ⑩ red(`NotNullViolation` — 운영에서 마이그레이션이 배포 도중 죽는 그 모양) ④ `await` 제거 → 배선 계약 red ⑤ 당사자 가드 제거 → 배선 계약 red ⑥ 정렬 키를 `created_at`으로 → 배선 계약 red. 전부 원복 후 green 재확인.
- **실브라우저 실측**(Playwright + dev 서버 + 로컬 스택): ① **관리자 축** — 가드 없는 상태에서 `admin@test.com`으로 남의 방을 열면 서버 로그에 `42501 new row violates row-level security policy for table "chat_room_reads"` 재현, 가드 적용 후 같은 방문에서 에러 0건·`chat_room_reads` 행 0건(대조군: 정상 당사자는 방문 시 행 1건 생성 확인). ② **뒤로가기 축(`#215`)** — `buyer2@test.com` 배지 "2건" → 방 클릭(DB 안읽음 1로 감소) → 브라우저 뒤로가기 → 배지 **"2건"으로 복원**. 같은 상태에서 `/chat` 새로 열기는 "1건", 방 안의 "채팅방 목록으로" 링크는 배지 없음(0) — 배지 계산은 옳고 back/forward 경로만 어긋남을 대조군으로 확정.
- 검증으로 생긴 데이터(buyer2의 읽음 행 2건)는 삭제해 **검증 전 스냅샷과 diff 0으로 원복 확인**했고, dev 서버도 종료했다.
- **DW 처리 결과**: `deferred-work.md`(동결)의 `DW-1`~`DW-7`은 전부 이미 대장에 있다(`#148`·`#149`·`#164`·`#184`·`#192`·`#203`·`#208`) — 신규 이관 대상 없음. 동결 파일 무수정.

**Residual risks (이번 패스):**
- `#215`(뒤로가기 시 배지 스테일)는 **인수조건 문구("방 목록으로 돌아오면 줄어 있다")와 직접 맞닿는 열린 항목**이다 — Story 12.6의 수동 2-브라우저 검증에서 이 경로를 뒤로가기로도 밟아보도록 대장 트리거에 지정해 뒀다.
- `#211`(로컬 스택 기본 권한 누락)은 여전히 세션 내 조치일 뿐이다 — `supabase db reset` 후 재현 가능.
- 대장 `#209`·`#210`·`#212`·`#213`·`#214`·`#216`·`#217`·`#218`은 열린 상태 그대로다(의도된 defer).
- `0025`는 로컬 스택과 마이그레이션 게이트에서만 검증됐다. 원격/운영 반영은 `docs/deployment-runbook.md` 절차와 사용자 승인이 필요하다(B3).
- 이 스펙 파일과 `sprint-status.yaml`은 커밋에 포함하지 않는다(선행 패스와 동일 이유 — 스펙을 커밋하면 HEAD가 또 움직여 `final_revision`이 어긋난다).

---

### 2026-07-29 — 후속 리뷰 패스(2차) 결과

**요약:** `status: done`이던 이 스토리에 독립 후속 리뷰 1패스(4개 레이어 병렬)를 돌렸다. **가장 큰 발견은 안읽음 RPC가 관리자에게 플랫폼 전체 메시지 수를 집계하던 것** — 실DB와 실브라우저 양쪽에서 재현했고, 빠져 있던 "내가 당사자인 방" 조건을 새 마이그레이션(`0025`)으로 복원했다. 그 외 검증 사각지대 3건(정렬·호출 배선 무검증, 성공 경로 RLS 무검증, 거부 테스트가 환경 붕괴와 구별 안 됨)과 접근성·대비 문제 2건을 패치했다. 총 patch 10건(medium 4·low 6), defer 2건(대장 `#213`·`#214`), 기각 14건. intent_gap·bad_spec 0건 — 스펙 자체를 고칠 사유는 없었다.

**Files changed (이번 패스):**
- `supabase/migrations/0025_chat_unread_participant_scope.sql`(신규) — `chat_unread_count()`에 `chat_rooms` 참여자 조인을 복원(`create or replace`, 전진 원칙). 0024는 수정하지 않았다.
- `api/tests/integration/test_chat_unread_real_db.py`(수정) — ⑦당사자 아닌 방 배제(양성 대조 포함)·⑧관리자 누수 회귀·⑨성공 경로 RLS(INSERT + 재진입 upsert) 3건 신설, 거부 테스트 2건에 RLS 메시지 대조 추가, 공유 헬퍼를 `conftest`에서 import로 교체.
- `web/src/app/(user)/chat/__tests__/unreadWiringContract.test.ts`(신규) — 목록 정렬 키(1차 `last_message_at` desc, 2차 `id`)와 방 페이지의 `markChatRoomRead(supabase, room.id, user.id)` 호출·인자 순서를 소스 계약으로 고정.
- `web/src/components/layout/SiteNav.tsx`(수정) — `aria-label`은 정확한 건수 유지(보이는 배지만 99+로 축약), 배지 색 `bg-red-500`→`bg-red-600`(대비 3.76:1→4.83:1).
- `web/src/components/layout/SiteNav.test.ts`(수정) — 99+ 케이스를 "배지만 축약, 라벨은 정확"으로 갱신.
- `web/src/components/layout/AppHeader.test.ts`(수정) — RPC 실패 폴백 테스트 신설, 비로그인 케이스에 SiteNav 렌더 단언 추가.
- `docs/conventions.md`(수정) — §12.6에 참여자 조건을 RLS에 맡기지 않는다는 계약(0025 근거·관리자 정책 OR 합성)과 aria-label 예외를 명시(Epic 16.4 단일 출처).
- `docs/tech-debt.md`(수정) — 신규 2건 `#213`(읽음 시각을 web 서버 시계가 정함)·`#214`(트리거가 INSERT만 봐서 관리자 삭제 시 정렬 고정). 기존 항목은 건드리지 않았다.

**Verification 수행 (오케스트레이터가 직접 실행):**
- `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(**282 passed**, 이전 279 + 신설 3) · `python3 scripts/check_migrations.py`(0001~0025 전량 적용 + 프로브 3건 통과) · `api/tests/integration/`(**76 passed**, 이전 73 + 신설 3).
- **깨뜨려 red 확인 → 복원해 green 확인**(B4): ⑧관리자 누수 테스트는 패치 전 실제로 실패(12 ≠ 0)했고 0025 적용 후 통과. 배선 계약 테스트는 정렬 키를 `created_at`으로, 호출 인자를 뒤바꿔 각각 red를 확인한 뒤 원복해 green 확인.
- **실DB 실측**(psql, 로컬 스택): 참여 방 0개인 관리자에게 수정 전 `chat_unread_count()` = 10(= 전체 메시지 수) → 수정 후 0. 일반 구매자는 수정 전후 모두 정상값(대조군).
- **실브라우저 실측**(Playwright + prod 빌드 + 로컬 스택): ① 관리자(admin@test.com)로 `/search` — 수정 전 배지 "10"·aria-label "안읽음 메시지 10건" 재현 → 수정 후 배지 없음·"채팅". ② 구매자(buyer2@test.com) — 배지 "1", aria-label "채팅, 안읽음 메시지 1건", 클래스 `bg-red-600` 확인. ③ **프리페치 반증**: 목록만 열고 두 링크를 호버해도 `chat_room_reads` 행 0건·방 라우트 요청 0건(dev·prod 양쪽), 실제 클릭 시에만 1건 생성(양성 대조).
- 검증으로 생긴 데이터(buyer2의 읽음 행 1건)는 삭제해 검증 전 상태로 원복했고, dev/prod 서버도 모두 종료했다.
- **DW 처리 결과**: `deferred-work.md`(동결)의 `DW-1`~`DW-7`은 전부 이미 대장에 있다(`#148`·`#149`·`#164`·`#184`·`#192`·`#203`·`#208`) — 신규 이관 대상 없음. 동결 파일 무수정.

**Residual risks (이번 패스):**
- `#211`(로컬 스택 기본 권한 누락)은 여전히 세션 내 조치일 뿐 영구 수정이 아니다 — `supabase db reset` 후 재현 가능.
- 대장 `#209`·`#210`·`#212`·`#213`·`#214`는 열린 상태 그대로다(의도된 defer).
- `0025`는 로컬 스택과 마이그레이션 게이트에서만 적용·검증됐다. 원격/운영 반영은 `docs/deployment-runbook.md` 절차와 사용자 승인이 필요하다(B3).
- 이 스펙 파일과 `sprint-status.yaml`은 커밋에 포함하지 않는다(선행 패스와 동일 이유 — 스펙을 커밋하면 HEAD가 또 움직여 `final_revision`이 어긋난다).

---

### 2026-07-29 — 최초 구현 + 1차 리뷰 결과

**요약:** 판매자가 문의를 놓치는 문제(FR57)를 고치려고, 사용자별·방별 "마지막으로 읽은 시각"을 담는 `chat_room_reads` 테이블과 방별 "마지막 메시지 시각"(`chat_rooms.last_message_at`, 트리거로 유지)을 신설했다. 안읽음 총합은 `chat_unread_count()` RPC로 집계해 내비 채팅🔔에 점+숫자 배지로 표기하고, 방 목록은 최신 문의 순으로 정렬한다. 코드리뷰 1패스(adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 레이어 병렬)에서 나온 지적 중 6건을 패치했고, 1건은 대장(tech-debt)에 이관했다. intent_gap·bad_spec 0건 — 구현이 스펙을 벗어난 곳은 없다.

**Files changed:**
- `supabase/migrations/0024_chat_room_reads.sql`(신규) — `chat_room_reads` 테이블+RLS(참여자 검사 포함 insert/update), `chat_rooms.last_message_at` 컬럼+백필+`greatest()` 단조증가 트리거, `chat_unread_count()` RPC(SECURITY INVOKER).
- `web/src/lib/chat.ts`(수정) — `markChatRoomRead(supabase, roomId, userId)` 추가(upsert, 실패 시 console.error만).
- `web/src/app/(user)/chat/[roomId]/page.tsx`(수정) — 당사자 확인 통과 직후 `markChatRoomRead` 호출.
- `web/src/app/(user)/chat/page.tsx`(수정) — 정렬 기준 `created_at`→`last_message_at`.
- `web/src/components/layout/AppHeader.tsx`(수정) — consumer 분기·로그인 시 `chat_unread_count()` 호출(비동기 컴포넌트로 전환), `unreadCount`를 `SiteNav`에 전달.
- `web/src/components/layout/SiteNav.tsx`(수정) — 채팅🔔에 점+숫자 배지, 99 초과는 "99+"로 표기(코드리뷰 patch), aria-label 갱신.
- `web/src/lib/__tests__/chat.test.ts`(신규) — `markChatRoomRead` 단위 테스트.
- `web/src/components/layout/SiteNav.test.ts`(수정) — unreadCount 배지 렌더 케이스(0/undefined/일반/99/100+ 경계값 포함).
- `web/src/components/layout/AppHeader.test.ts`(수정) — consumer·비로그인·admin 세 분기의 RPC 호출 여부·전달값 계약 테스트.
- `supabase/seed-local/02_data.sql`(수정, 스펙 범위 밖이지만 이번 마이그레이션이 만든 회귀라 필수) — `last_message_at` NOT NULL 컬럼이 스냅샷 JSON에 없어 시드가 죽던 것을 명시 컬럼 목록+재백필로 수정.
- `docs/conventions.md`(수정) — §12.6 신설(안읽음 계약, Epic 16.4 단일 출처), 코드리뷰 patch로 트리거/함수명 표기 정정.
- `docs/tech-debt.md`(수정) — 신규 5건 등재: `#208`(DW-7 이관), `#209`(AppHeader RPC가 `#183` 층에 추가), `#210`(방이 열린 채 본 메시지는 재진입 전까지 안읽음 유지, 의도적 범위 제외), `#211`(로컬 스택 `authenticated`/`anon` 기본 권한 누락 실측+세션 내 조치), `#212`(`chat_unread_count()` 시간 창 없음, 성능 축 defer).
- `api/tests/integration/test_chat_unread_real_db.py`(신규, 코드리뷰 patch) — RLS 참여자 검사(insert 거부·select 격리·update 재검증)·안읽음 공식 경계값(strict `>`, 본인 발신 제외)·`last_message_at` 트리거의 out-of-order 커밋 처리를 실제 Postgres로 검증(6건).

**Review 수행 (1패스, 4개 레이어 병렬 — adversarial·edge-case-hunter·verification-gap·intent-alignment):**
- patch 6건(high 0, medium 2, low 4) 전부 적용:
  - `low` 트리거 `last_message_at` 무조건 덮어쓰기 → `greatest()`로 단조증가만 허용(adversarial+edge-case-hunter 교차 지적, 시드 스크립트가 실측한 현상과 동종).
  - `low` `docs/conventions.md` §12.6이 트리거명과 함수명을 혼동 → 정정.
  - `low` `chat_room_reads_update_own`이 INSERT와 달리 참여자 재검증이 없어, 자기 행의 `room_id`를 당사자 아닌 방으로 재지정하는 UPDATE가 통과했다 → INSERT와 동일한 EXISTS 검사를 UPDATE `with check`에도 추가.
  - `low` `chat_unread_count()`의 `search_path`가 이 파일의 다른 함수·0016/0023과 달리 `public`이었다 → `''`로 통일.
  - `medium` 안읽음 배지에 상한이 없어(스펙이 이미 명시한 롤아웃 시점 대량 카운트 시나리오에서) 3자리 이상이 작은 원형 배지를 깨뜨릴 수 있었다 → 99 초과 시 "99+"로 표기.
  - `medium` 신규 RPC·트리거·RLS를 실제 Postgres로 검증하는 짝 테스트가 없어(0020/0022/0023이 세운 관례 이탈) 회귀를 못 잡는 상태였다(verification-gap+intent-alignment 독립 교차 지적) → `test_chat_unread_real_db.py` 신설(6건).
- **패치 2건(트리거 단조증가·UPDATE 참여자 재검증)은 일부러 패치 전 상태로 되돌려 새 회귀 테스트가 실제로 red가 되는 것을 확인한 뒤, 패치를 복원해 green으로 되돌렸다**(B4 — "잡는다"가 완료다). 나머지도 전체 재검증으로 green 확인.
- defer 1건(대장 `#212` 신규 등재) — `chat_unread_count()`가 시간 창 없이 전체 이력을 스캔(FR57 공식 자체가 시간 창이 없어 정확성 문제는 아님, 성능 축만 존재 — 데모 규모 무해).
- 기각 8건 — `markChatRoomRead` 콘솔 로그만(레포 전체의 기존 "비차단 배경 쓰기" 관례와 동일, 신규 패턴 아님) · `AppHeader` 비동기 전환이 페이지 렌더를 RPC에 묶는다(대장 `#209`가 이미 같은 축을 다룸, 새로운 결합 유형 아님) · `chat_room_reads`가 명시 GRANT 없이 플랫폼 기본에 의존(대장 `#211`이 프로젝트 전체 대상 정식 처방을 이미 등재) · Supabase 클라이언트에 `Database` 제네릭이 없음(레포 전체의 기존 패턴, 범위 밖) · 방이 열린 채 본 메시지가 안 줄어드는 edge case의 수동 체크가 Verification에 없음(새 동작이 아니라 "호출 안 함"이라 검증할 게 없음) · 방 목록 정렬 컬럼 교체·`markChatRoomRead` 호출 배선에 대응하는 자동 테스트가 없음(이 레포는 서버 페이지 컴포넌트를 단위테스트하지 않는 기존 관례, 신설 real-db 테스트가 값의 정확성은 이미 커버) · 대장 `#211`의 세션 내 조치가 파일로 안 남아 diff만으로 재현 안 됨(`#211` 자체가 이미 이 사실과 처방을 상세 기록).

**Verification 수행 (오케스트레이터가 직접 실행, 서브에이전트 보고에 의존하지 않음):**
- `npm run lint`(0 warning) · `npx tsc --noEmit`(0 error) · `npm test -- --run`(**279 passed**, 패치 전 277 + 신설 2) · `python3 scripts/check_migrations.py`(정적+동적 검사, 프로브 3건 전부 통과) · `api/tests/integration/`(**73 passed**, 신설 `test_chat_unread_real_db.py` 6건 포함).
- **실제 로컬 Supabase 스택 + REST API로 실측**(psql·curl, buyer@test.com/seller-seed2@test.com 실계정): `chat_unread_count()`가 실제 메시지 수와 정확히 일치(2→1→0으로 정확히 감소) · 본인 발신 메시지는 안읽음에서 제외(0 유지, 상대방 계정에서는 동시에 +1) · `last_message_at` 기준 정렬이 실제로 최신 문의를 최상단에 놓음 · 제3자 계정의 타인 방 `chat_room_reads` 삽입·재지정 시도가 RLS로 거부(`42501`) · 기존 시드 채팅방의 `last_message_at` 백필이 실제 마지막 메시지 시각과 일치.
- **실제 브라우저 라이브 재현**(Playwright + 로컬 dev 서버 + 로컬 Supabase 스택, buyer@test.com 실계정): 로그인 → 내비 배지 "채팅, 안읽음 메시지 1건"(🔔+"1") 확인 → 안읽던 방 진입 → 방 목록 복귀 시 배지가 사라짐(0으로 감소) 실측 확인. 사용한 테스트 메시지·데이터는 방 삭제 아님 확인 후 원상복구(백필 재계산)했다.
- **DW 처리 결과**: `deferred-work.md`(동결)의 `DW-7`(12-4 review-budget-followup, status: open)이 대장에 미이관 상태였다 — 이번에 대장 `#208`로 신규 이관했다. 동결 파일 자체는 무수정이다.

**환경 관련 중요 발견 (이 스토리 범위 밖이지만 반드시 알려야 함):** 검증 도중 이 프로젝트의 **로컬 Supabase Docker 스택 전체**가 `authenticated`/`anon` 롤의 테이블 기본 권한(SELECT/INSERT/UPDATE/DELETE)을 잃은 상태였다는 것을 발견했다 — 이 스토리의 새 테이블만이 아니라 `listings`·`chat_rooms`·`profiles`·`wishlists` 등 기존 전 기능이 로컬에서 42501로 죽어 있었다(원격/운영 Supabase는 무관). 세션 내에서 라이브로 복구했지만(마이그레이션 파일로 남기지 않음, 프로젝트 전체 범위라 이 스토리 diff에 섞지 않았다), **다음 `supabase db reset` 이후 재현될 수 있다** — `docs/tech-debt.md` #211에 실측 근거와 권장 영구 조치(0006의 `ai_readonly` 패턴을 anon/authenticated에도 적용)를 남겨뒀다. 사용자가 다음에 로컬 개발 환경을 새로 띄웠을 때 로그인 후 아무 화면이나 안 열리면 이 항목을 먼저 확인해달라.

**Residual risks:**
- 대장 `#209`·`#210`·`#212` 모두 열린 상태 그대로다 — 이번 패스는 이들 중 어느 것도 수정하지 않았다(의도된 defer/reject).
- `#211`(로컬 환경 기본 권한 누락)은 세션 내 조치일 뿐 영구 수정이 아니다 — 위 "환경 관련 중요 발견" 참조.
- 이 스펙 파일의 프론트매터·로그 편집분과 `sprint-status.yaml`은 커밋에 포함되지 않는다(스펙을 커밋하면 HEAD가 또 움직여 방금 적을 `final_revision`이 어긋난다 — 선행 스토리들과 동일 이유). `sprint-status.yaml`은 오케스트레이터 소유다.
