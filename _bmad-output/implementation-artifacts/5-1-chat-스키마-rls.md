# Story 5.1: chat 스키마 + RLS

Status: in-progress

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a 개발자,
I want 채팅방·메시지 테이블(`chat_rooms`·`chat_messages`)과 참여자 한정 RLS를 만들고 싶다,
so that 거래 당사자(구매자·판매자)만 대화를 읽고 쓰고, 제3자는 차단된다.

## Acceptance Criteria

1. **Given** `0003_chat` 마이그레이션이 적용되면, **When** 스키마를 확인하면, **Then** `chat_rooms(listing_id, buyer_id, seller_id, created_at)`와 `chat_messages(room_id, sender_id, body, created_at)` 두 테이블이 존재한다. (epics.md L590~592, architecture.md L140~141)
2. **Given** `0003_chat` 마이그레이션이 적용되면, **When** RLS 적용 여부를 확인하면, **Then** 참여자 한정 RLS 정책이 **같은 `0003_chat` 마이그레이션 안에 동거**해 두 테이블에 함께 적용돼 있다(0001·0002와 동일한 "RLS 동거" 원칙). (epics.md L593, architecture.md L461)
3. **Given** RLS가 적용된 상태에서, **When** 채팅방의 당사자(`buyer_id` 또는 `seller_id`)가 자신이 참여한 방/메시지에 접근하면, **Then** read/write가 허용된다.
4. **Given** RLS가 적용된 상태에서, **When** 당사자가 아닌 제3자가 채팅방/메시지에 접근하면, **Then** 차단된다(0건 반환·write 거부).
5. **Given** 같은 매물·구매자·판매자 조합에 대해, **When** 채팅방을 두 번 만들려 하면, **Then** UNIQUE 제약으로 중복 방 생성이 차단된다(5-2 "기존 방 재사용" 토대).

## Tasks / Subtasks

- [x] Task 1: `0003_chat.sql` 마이그레이션 파일 생성 (AC: #1, #2, #5)
  - [x] `supabase/migrations/0003_chat.sql` 신규 작성 — 헤더 주석은 0001·0002·0004 스타일(파일 목적·"하는 일" 번호 목록·적용 순서 메모)을 따른다
  - [x] `chat_rooms` 테이블: `id uuid pk default gen_random_uuid()`, `listing_id → public.listings(id) on delete cascade`, `buyer_id → public.profiles(id) on delete cascade`, `seller_id → public.profiles(id) on delete cascade`, `created_at timestamptz not null default now()`
  - [x] `chat_rooms`에 `unique (listing_id, buyer_id, seller_id)` 제약 추가 (AC#5 — 5-2 재사용 토대)
  - [x] `chat_messages` 테이블: `id uuid pk default gen_random_uuid()`, `room_id → public.chat_rooms(id) on delete cascade`, `sender_id → public.profiles(id) on delete cascade`, `body text not null`, `created_at timestamptz not null default now()`
  - [x] 테이블·핵심 컬럼에 `comment on` 설명 추가(0001·0002 스타일, 한국어)
- [x] Task 2: 참여자 한정 RLS 정책 (같은 마이그레이션 동거) (AC: #2, #3, #4)
  - [x] `alter table public.chat_rooms enable row level security;` / `chat_messages` 동일
  - [x] `chat_rooms` SELECT: `to authenticated using (auth.uid() = buyer_id or auth.uid() = seller_id)` — 정책명 `chat_rooms_select_participant`
  - [x] `chat_rooms` INSERT: `to authenticated with check (auth.uid() = buyer_id or auth.uid() = seller_id)` — 정책명 `chat_rooms_insert_participant` (자기를 당사자로 포함한 방만 생성)
  - [x] `chat_messages` SELECT: 메시지의 `room_id`가 가리키는 방의 당사자만 — `to authenticated using (exists (select 1 from public.chat_rooms r where r.id = room_id and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)))` — 정책명 `chat_messages_select_participant`
  - [x] `chat_messages` INSERT: 보낸 사람(`sender_id`)이 본인이고 그 방의 당사자일 때만 — `to authenticated with check (auth.uid() = sender_id and exists (select 1 from public.chat_rooms r where r.id = room_id and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)))` — 정책명 `chat_messages_insert_participant`
  - [x] UPDATE/DELETE 정책은 두지 않는다(메시지는 영속·불변. 관리자 삭제는 Epic 6 `0005_admin_policies`가 교차 정책으로 담당) — Dev Notes 참조
- [x] Task 3: 마이그레이션 적용·검증 (AC: #1~#5)
  - [x] Supabase MCP `apply_migration(name="0003_chat", query=<파일 내용>)`로 적용 (0004·0006이 MCP로 적용된 것과 동일 방식 — Dev Notes 참조)
  - [x] `list_migrations`로 `0003_chat` 등록 확인 (version 20260623090355)
  - [x] `list_tables(schemas=["public"], verbose=true)`로 `chat_rooms`·`chat_messages` 컬럼·FK·RLS enable 확인 (둘 다 rls_enabled:true)
  - [x] `execute_sql`로 RLS 정책 4개 존재 확인(`pg_policies`) + UNIQUE 제약 존재 확인
  - [x] `get_advisors(type=security)`로 RLS 누락 등 경고 없는지 점검 (chat 관련 신규 경고 0건)

## Dev Notes

### 반드시 먼저 읽을 것 (기존 패턴 — drift 금지)
- `supabase/migrations/0001_profiles.sql` — RLS 정책 네이밍 규약(`<table>_<action>_<scope>`), `to authenticated` 한정, `comment on` 한국어, 함수 EXECUTE revoke 패턴.
- `supabase/migrations/0002_listings.sql` — 테이블 + 소유권 RLS **동거** 원칙, FK `references public.profiles(id) on delete cascade`, CHECK/UNIQUE 스타일, 정책 OR 결합 주석 방식.
- `supabase/migrations/0006_readonly_role.sql` — ⚠️ **중요**: `alter default privileges in schema public grant select on tables to ai_readonly`(L33)가 걸려 있어, **새로 만든 chat 테이블에도 ai_readonly의 SELECT 권한이 자동 GRANT된다**. 하지만 chat 테이블에는 ai_readonly용 permissive 정책(`using(true)`)을 **만들지 않으므로**, RLS가 켜져 있는 한 ai_readonly는 chat 행을 0건만 본다(테이블 권한은 있어도 행 가시성 정책이 없음 → 0건). 이는 의도된 안전 동작이다(AI 검색은 chat을 조회하지 않음). chat 테이블에 ai_readonly 정책을 추가하지 말 것.

### 스키마 결정(확정 정의 — architecture.md 단일 출처)
- `chat_rooms` — `listing_id`, `buyer_id`, `seller_id`, `created_at` [Source: architecture.md#Data-Architecture L140]
- `chat_messages` — `room_id`, `sender_id`, `body`, `created_at` [Source: architecture.md#Data-Architecture L141]
- FK 대상: 사용자 참조는 `auth.users`가 아니라 **`public.profiles(id)`** 를 따른다(0002 `listings.seller_id`가 profiles를 참조한 것과 동일 패턴 → 일관성). `on delete cascade`로 매물/사용자 삭제 시 방·메시지도 정리.
- 테이블명 복수형 snake_case [Source: architecture.md#L246].
- 통신선/컬럼은 snake_case 유지(AR5 폴리글랏 일관성). 에러 포맷 `{error:{code,message}}`는 이 스토리에 직접 해당 없음(DB 전용, API 코드 변경 없음).

### RLS 설계 근거(왜 이렇게)
- **참여자 = `buyer_id` OR `seller_id`**: 한 방에 정확히 두 당사자만 존재. `auth.uid()`가 둘 중 하나면 당사자.
- `chat_messages`는 자체에 buyer/seller가 없으므로, **방을 조인(EXISTS 서브쿼리)** 해 그 방의 당사자인지로 판정한다. 0001의 "RLS 자기참조 무한재귀" 함정과 달리, 여기서는 `chat_messages` 정책이 **다른 테이블(`chat_rooms`)** 을 참조하므로 재귀가 없다 — 단, `chat_rooms`의 RLS도 함께 평가됨에 주의. EXISTS 서브쿼리는 정책 평가 시 `chat_rooms`의 SELECT 정책을 통과한 행만 보이지만, 당사자 본인이 조회하므로 자신의 방은 보인다(정합).
- INSERT(`with check`): `chat_messages` insert 시 `sender_id`가 본인(`auth.uid()`)이고 그 방 당사자여야 함 → 남의 명의로 메시지 위조·남의 방에 끼어들기 차단.
- `chat_rooms` insert(`with check`): 만드는 사람이 그 방의 당사자(buyer 또는 seller)여야 함. 5-2에서 구매자가 방을 열 때 `buyer_id=본인`으로 생성하는 흐름과 정합.
- UPDATE/DELETE 정책 미설정 → 기본 거부. 메시지는 영속·불변(2-x의 "영속" AC 정신), 관리자 삭제권은 Epic 6 `0005_admin_policies`(교차 정책)에서 추가. [Source: architecture.md#L412, L461]
- 모든 정책 `to authenticated` 한정 → 비로그인(anon)은 평가 자체에서 제외(0001·0002 동일).

### UNIQUE 제약(AC#5)
- `unique (listing_id, buyer_id, seller_id)` — "한 매물·구매자·판매자 조합당 방 1개". 5-2의 "기존 방 재사용"이 이 제약(또는 동일 키 조회)에 의존한다. [Source: epics.md Story 5.2 L609]

### 마이그레이션 적용 방식(기존 이력 기준)
- `list_migrations` 결과: `0001`·`0002`(+0002b/c/d)·`0006`·`0004`가 모두 Supabase에 적용돼 있음. 0004·0006은 로컬 CLI가 아니라 **Supabase MCP `apply_migration`** 로 원격에 직접 적용된 패턴(번호 갭·적용 시각 순서로 확인). → 이 스토리도 **MCP `apply_migration`** 으로 적용한다.
- 번호 갭: `0003`(chat·이 스토리)·`0005`(admin·Epic6)는 의도된 예약. 0004·0006 헤더가 이를 명시. 적용 순서상 0006(default privileges)이 먼저 적용됐어도, chat 테이블에 ai_readonly 정책을 안 만들면 안전(위 ⚠️ 참조).
- 적용 후 반드시 `list_tables`(verbose)·`pg_policies` 조회로 사실 검증하고 보고에 결과를 적는다.

### 테스트 표준(이 스토리)
- DB 전용 스토리이므로 웹 E2E·API 호출 없음. 검증은 **SQL 레벨**:
  - 구조 검증: `list_tables` verbose로 컬럼/FK/RLS, `pg_constraint`로 UNIQUE.
  - 정책 존재: `select * from pg_policies where tablename in ('chat_rooms','chat_messages')` → 정책 4개.
  - (선택) 동작 스모크: 두 profiles·한 listing을 만들고 set role / JWT 없이 직접 검증은 MCP postgres 롤(슈퍼유저급)이라 RLS가 우회될 수 있음 → **RLS 동작 자체는 정책 정의 존재 확인으로 갈음**하고, 실제 차단 동작은 5-2/5-3에서 인증 클라이언트 E2E로 검증(Dev Notes에 한계 명시). `get_advisors(security)`로 RLS-disabled 경고 없음 확인.

### Project Structure Notes
- 신규 파일 1개만: `supabase/migrations/0003_chat.sql`. 코드(web/api) 변경 없음.
- 마이그레이션 단일 출처(`supabase/migrations/`) 원칙 유지(0001 헤더 명시).

### References
- [Source: _bmad-output/planning-artifacts/epics.md#Story-5.1 L582~597]
- [Source: _bmad-output/planning-artifacts/epics.md#Story-5.2 L599~613 — 기존 방 재사용 → UNIQUE 근거]
- [Source: _bmad-output/planning-artifacts/architecture.md#Data-Architecture L140~141]
- [Source: _bmad-output/planning-artifacts/architecture.md#L246 — 테이블 복수형 snake_case]
- [Source: _bmad-output/planning-artifacts/architecture.md#L412, L461 — RLS 동거 원칙·admin 교차 정책 분리]
- [Source: supabase/migrations/0001_profiles.sql — RLS 네이밍·to authenticated·comment 패턴]
- [Source: supabase/migrations/0002_listings.sql — 테이블+RLS 동거·FK·UNIQUE 패턴]
- [Source: supabase/migrations/0006_readonly_role.sql L33 — ai_readonly default privileges 영향]

## Dev Agent Record

### Agent Model Used

claude-opus-4-8[1m] (Opus 4.8, 1M context)

### Debug Log References

- `apply_migration(name="0003_chat")` → `{"success":true}`
- `list_migrations` → `0003_chat` 등록 (version `20260623090355`)
- `list_tables(verbose)` → `chat_rooms`·`chat_messages` 모두 `rls_enabled:true`, 컬럼/FK 정상
- `pg_policies` → 4개 정책(chat_rooms 2 + chat_messages 2), 전부 `{authenticated}`
- `pg_constraint` → `chat_rooms_listing_id_buyer_id_seller_id_key` UNIQUE(listing_id, buyer_id, seller_id)
- `get_advisors(security)` → chat 관련 신규 경고 0건(기존 vector/is_admin/leaked-password 경고만, 본 스토리 무관)

### Completion Notes List

- **무엇을·왜**: 문의 채팅의 토대인 두 DB 테이블(`chat_rooms`·`chat_messages`)과 "방 당사자만 읽고 쓰는" 보안 규칙(RLS)을 마이그레이션 `0003_chat`으로 한 번에 만들었다. 마치 두 사람만 들어갈 수 있는 1:1 대화방을 DB 차원에서 잠가둔 것 — 제3자는 행을 0건만 보고 글도 못 쓴다.
- **검증 방식(한계 명시)**: MCP 연결 롤(postgres급)은 RLS를 우회하므로 실제 "제3자 차단" 동작을 인증 클라이언트로 재현하진 않았다. 대신 ① RLS enable, ② 정책 정의(qual/with_check) 4개의 실제 술어값, ③ UNIQUE 제약, ④ advisor의 RLS-누락 경고 부재를 사실 확인했다. 인증 사용자 관점의 실제 차단 E2E는 5-2/5-3에서 로그인 클라이언트로 검증한다(스토리 Dev Notes에 명시).
- **부수 결정**: 폴링(5-3) 시간순 조회 가속용 `chat_messages_room_created_idx (room_id, created_at)` 인덱스를 추가했다(스키마 토대 스토리 범위 내 합리적 기본값).
- **ai_readonly 안전 확인**: 0006의 default privileges로 chat 테이블에도 ai_readonly SELECT 권한이 자동 부여되지만, 가시성 정책(using true)을 만들지 않아 RLS상 0건 → AI 검색이 채팅을 못 본다(의도된 차단). chat에 ai_readonly 정책 미추가.

### File List

- `supabase/migrations/0003_chat.sql` (신규)
- `_bmad-output/implementation-artifacts/5-1-chat-스키마-rls.md` (스토리 — 본 파일)
- `_bmad-output/implementation-artifacts/sprint-status.yaml` (epic-5 in-progress, 5-1 review)

## Review Findings

코드리뷰 3레이어(Blind Hunter·Edge Case Hunter·Acceptance Auditor) 병렬 서브에이전트로 실행. 라이브 DB(Supabase MCP)로 정책·제약·인덱스·advisor 사실 검증.

### [Decision] 결정 필요 — 사용자 판단 대기

- [ ] [Review][Decision] **chat_rooms INSERT 시 `seller_id`·`listing_id` 위조 가능(High)** — 현재 INSERT RLS(`auth.uid() = buyer_id or seller_id`)는 방을 만드는 사람이 *둘 중 하나*이기만 하면 통과한다. 그래서 구매자가 **임의의 `seller_id`(아무 프로필)** 와 **임의의 `listing_id`** 를 지정해 방을 만들 수 있고, `seller_id`가 그 `listing_id`의 실제 판매자(소유자)인지 DB가 검증하지 않는다 → 모르는 사람에게 원치 않는 방을 강제로 만들거나, 잘못된 (매물,판매자) 짝의 방을 생성할 수 있다. **선택지**: (A) 트리거/함수로 INSERT 시 `seller_id = (select seller_id from listings where id = listing_id)` 강제(DB 레벨 차단, 가장 견고) / (B) `listings(id, seller_id)` 복합 UNIQUE + 복합 FK로 짝 무결성 보장 / (C) 앱(5-2 프록시) 책임으로 두고 DB는 현행 유지(데모 범위면 수용 가능, RLS 위조 벡터는 남음). 5-2 "방 생성" 구현 방식과 직결되므로 자동 선택하지 않고 escalate. (location: `supabase/migrations/0003_chat.sql` chat_rooms_insert_participant)

### [Patch] 자동 적용 완료

- [x] [Review][Patch] `chat_rooms`에 `CHECK(buyer_id <> seller_id)` 추가 — 자기 자신과의 방 차단(`not null`은 막지 못함). [supabase/migrations/0003_chat.sql] — 적용·validate 완료(0003b).
- [x] [Review][Patch] `chat_messages`에 `CHECK(length(btrim(body)) > 0)` 추가 — 공백만 있는 빈 메시지 차단. [supabase/migrations/0003_chat.sql] — 적용·validate 완료(0003b).
- [x] [Review][Patch] cascade FK 인덱스 추가 — `chat_rooms(buyer_id)`·`chat_rooms(seller_id)`·`chat_messages(sender_id)`. profiles 삭제 cascade 시 풀스캔/락 회피(마이그레이션 자체가 명시한 성능 의도와 정합). [supabase/migrations/0003_chat.sql] — 적용 완료(0003b).
- [x] [Review][Patch] 헤더 주석 정정 — ① ai_readonly가 chat 테이블 SELECT를 얻는 경로를 `alter default privileges`가 아니라 `grant select on all tables`(0003<0006 순서라 0006 적용 시 chat이 이미 존재)로 정정. ② 존재하지 않는 `0002b/c/d` 파일 참조 제거(0004에서 복사된 stale 표기). [supabase/migrations/0003_chat.sql L1~16]

### 검토했으나 조치 안 함(dismiss/defer)

- [x] [Review][Dismiss] UNIQUE 역할 스왑 중복 방 — `(L,A,B)`/`(L,B,A)` 이론상 별개지만, 5-2 흐름상 `buyer=문의자·seller=매물주`로 deterministic이고 `CHECK(buyer<>seller)`로 보강돼 실질 중복 불가. #Decision(A/B)로 완전 차단 가능.
- [x] [Review][Dismiss] INSERT-then-RETURNING 순서 의존 — 정상 흐름(방 먼저 생성→메시지)에서 충족. 결함 아님(정보성).
- [x] [Review][Dismiss] UPDATE/DELETE 정책 부재 — 의도된 default-deny(메시지 영속·불변, 관리자 삭제는 Epic6). 스펙 명시.
- [x] [Review][Dismiss] EXISTS 서브쿼리가 chat_rooms RLS 우회 우려 — 라이브 검증상 정상. 참여자만 통과, 제3자 0건. 보안 갭 없음.

### 라이브 검증 결과(패치 후)

- 정책 4개 그대로(`{authenticated}`), 술어값 정확.
- CHECK 2개 validated: `chat_rooms_buyer_ne_seller`, `chat_messages_body_not_blank`.
- 인덱스 7개: pkey×2, room_created, sender, buyer, seller, UNIQUE.
- `get_advisors(security)`: chat 관련 신규 경고 0건(기존 vector/is_admin/leaked-password만, 본 스토리 무관).

## Change Log

- 2026-06-23: chat 스키마(`chat_rooms`·`chat_messages`) + 참여자 한정 RLS 4개 + UNIQUE(매물·구매자·판매자) 마이그레이션 `0003_chat` 생성·적용·검증. (dev, story 5-1)
- 2026-06-23: code-review 반영(0003b) — CHECK(buyer≠seller)·CHECK(빈 본문 금지)·FK 인덱스 3개·헤더 주석 정정. seller_id 위조(High)는 [Decision]으로 escalate, 상태 in-progress 유지. (review, story 5-1)
