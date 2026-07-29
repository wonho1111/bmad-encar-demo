-- migration-check-prelude.sql — 마이그레이션 게이트가 fresh DB에 미리 까는 "Supabase 플랫폼 계약면" 재현
--
-- 여기 있는 것 = 우리가 Supabase에 의존한다고 인정한 것. 추가하려면 그 의존이 정당한지 먼저 답할 것.
-- (프렐류드를 늘려 게이트의 red를 무마하는 우회를 막기 위한 규칙 — Story 8.6 Task 2)
--
-- ⚠️ "정당한 확장"과 "red 무마 우회"를 가르는 기준 (2026-07-15 코드리뷰 추가):
--   · 정당하다 = 실제 Supabase 플랫폼에 **있는데** 이 스텁이 빠뜨려서 red가 났다.
--     → 실측값을 근거로 추가하라(원격에서 확인한 뒤 그 사실을 주석에 남긴다).
--       예: auth.users는 지금 3컬럼 스텁이라, 마이그가 실재하는 created_at·phone 등을
--           참조하면 원격은 멀쩡한데 게이트만 red다 — 이건 스텁의 결함이지 마이그의 결함이 아니다.
--   · 우회다 = 플랫폼에 **없는 것**을 여기 만들어 red를 없앤다.
--     → 금지. 그 red는 진짜 self-containment 위반이고, 마이그를 고쳐야 한다.
--   이 구분이 없으면 "확장 금지"가 탈출구 없는 규칙이 되어 결국 통째로 무시된다.
--
-- self-contained의 정의(이 프렐류드가 그 기준선이다):
--   선언된 프렐류드 계약면 + 자기보다 앞 번호 마이그레이션, 이 둘만으로 성립하는가.
--
-- 대상: pgvector/pgvector:pg17 빈 컨테이너(postgres 슈퍼유저로 실행). 원격 매니지드 DB엔 절대 적용하지 않는다
-- (원격은 이미 이 계약면을 플랫폼이 제공하므로 불필요 — 오히려 충돌 가능).

-- ── auth 스키마 + auth.users (0001의 FK·가입 트리거가 읽는 컬럼만) ──────────
create schema if not exists auth;

create table if not exists auth.users (
  id                 uuid primary key,
  email              text,
  raw_user_meta_data jsonb
);

-- ── auth.uid() 스텁 — 0001 RLS 정책이 참조 ──────────────────────────────
create or replace function auth.uid()
returns uuid
language sql
stable
as $$
  select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
$$;

-- ── Supabase 표준 롤 (0001·0002·0003c·0007~0009·0011이 참조) ────────────
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then
    create role anon nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then
    create role authenticated nologin;
  end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then
    create role service_role nologin;
  end if;
end $$;

-- 롤 postgres는 컨테이너 기본 슈퍼유저 — 그대로 쓴다(별도 생성 불필요).
-- vector 확장은 이미지에 포함되어 있고, 마이그레이션(0002·0004)이 `create extension if not exists vector`로
-- 자체 수행한다 — 여기서 만들지 않는다.
-- ai_readonly 롤은 0006이 만드는 것이므로 여기 넣지 않는다(마이그의 몫).

-- ── 플랫폼 기본 GRANT (2026-07-14 운영 Supabase 실측 — pg_default_acl 재현, 추정 아님) ──
--   원본: postgres 롤의 기본권한 = {anon=arwdDxtm, authenticated=arwdDxtm, service_role=arwdDxtm, ai_readonly=r}
--   (arwdDxtm = insert·select·update·delete·truncate·references·trigger·maintain)
--   ai_readonly=r은 0006이 만드는 것이므로 여기 넣지 않는다.
-- service_role은 프렐류드에만 등장하고 마이그는 안 쓴다(project-context 규칙 6 — service_role 키 금지).
-- 실측 재현이라 넣을 뿐, 이걸 근거로 마이그에서 service_role을 쓰지 마라.
alter default privileges in schema public
  grant all on tables to anon, authenticated, service_role;

-- ── storage 스키마 최소 스텁 (0012_listing_images가 참조 — 2026-07-16 원격 실측 기반, Story 9.1) ──
--   실측 근거: information_schema.columns(storage.buckets/objects 전체 컬럼) + pg_class.relrowsecurity를
--   원격에서 직접 조회(Story 9.1 Task 1). 이 레포 최초의 storage 마이그라 스텁이 아예 없었다.
--   "정당한 확장" 기준 충족: 실제 Supabase 플랫폼에 있는 걸 스텁이 빠뜨려 red가 나는 경우다(우회 아님).
--   스텁은 0012가 실제로 건드리는 컬럼만 담는다(선례: auth.users 3컬럼 스텁과 동일 원칙) — owner 등
--   나머지 실컬럼은 원격엔 있지만 여기 없다(마이그가 안 쓰므로 필요 없음).
create schema if not exists storage;

create table if not exists storage.buckets (
  id                  text primary key,
  name                text not null,
  public              boolean,
  file_size_limit     bigint,
  allowed_mime_types  text[]
);

create table if not exists storage.objects (
  id         uuid primary key default gen_random_uuid(),
  bucket_id  text,
  name       text
);

-- 원격 실측(2026-07-16): relrowsecurity = true — 플랫폼이 이미 켜둔 상태를 재현.
-- (0012는 이 문을 스스로 켜지 않는다 — 원격에서 소유자가 아닌 롤이 건드리면 실패할 수 있어서다.)
alter table storage.objects enable row level security;
-- storage 스텁은 여기까지(Story 9.1, 0012 전용).

-- ── realtime 스키마 최소 스텁 (0023_chat_realtime_broadcast가 참조 — 2026-07-28 로컬 스택 실측 기반, Story 12.2) ──
--   실측 근거: 로컬 Supabase Docker 스택(포트 55322)에 psql로 직접 접속해 확인(원격이 아니라 로컬인 이유는
--   storage 스텁 때와 달리 이번엔 로컬 스택이 이미 떠 있어 그걸로 충분했기 때문 — 플랫폼 계약면은
--   로컬·원격이 동일하다, 둘 다 Supabase가 배포하는 같은 realtime 확장이다):
--     · `\d realtime.messages` → 컬럼(topic/extension/payload/event/private/updated_at/inserted_at/
--       id/binary_payload), relrowsecurity=t, 정책 0건(플랫폼 기본이 이미 RLS만 켜둔 상태).
--     · `information_schema.role_table_grants` → anon/authenticated/service_role에 이미
--       INSERT/SELECT/UPDATE 테이블 GRANT가 있음(플랫폼 기본 — 그래서 0023이 GRANT를 추가하지 않는다).
--     · `pg_get_functiondef`로 `realtime.broadcast_changes()`·`realtime.send()`·`realtime.topic()`
--       정의를 그대로 복사(셋 다 `security definer`가 아니다 — `pg_proc.prosecdef=f`, 소유자는
--       supabase_admin/supabase_realtime_admin). 0023의 트리거 함수가 SECURITY DEFINER인 이유는
--       이 함수들 자체가 아니라 마이그레이션을 적용하는 postgres 롤의 `rolbypassrls=true` 속성에
--       있다(실측: `select rolbypassrls from pg_roles where rolname='postgres'` → t).
--   "정당한 확장" 기준 충족: 실제 Supabase 플랫폼(로컬·원격 공통)에 있는 걸 스텁이 빠뜨려 red가 나는
--   경우다(우회 아님) — storage 스텁과 동일한 논리.
--   ⚠️ 실제 realtime.messages는 `inserted_at` 기준 range 파티션 테이블이다. 이 스텁은 평범한(비파티션)
--   테이블로 단순화한다 — 어느 마이그도 파티션을 **만들거나 참조하지 않기** 때문이다(storage 스텁이
--   owner 등 미사용 컬럼을 생략한 것과 같은 원칙, "실제로 건드리는 것만 재현").
--   ⚠️ 다만 **테스트는 다르다**: 실제 플랫폼에서는 그 시각에 해당하는 파티션이 있어야 방송 INSERT가
--   성공한다(없으면 `realtime.send()`가 예외를 삼켜 방송만 조용히 사라진다). 비파티션 스텁 위에서는
--   그 실패 모드가 **구조적으로 발생할 수 없어**, 방송 행 개수를 세는 테스트들이 여기선 항상 초록이다.
--   즉 "파티션 유지가 자동인가"는 이 프렐류드가 답할 수 없는 질문이고, 원격 확인 항목으로 열려 있다
--   (`docs/tech-debt.md` #195 ②). 스텁을 파티션 테이블로 바꾸려는 다음 사람은 이 문단부터 읽을 것.
--
--   ✅ 2026-07-29 원격 실측으로 갱신(#196·#197의 확인 항목 — 위 :7-9 "원격에서 확인한 뒤 주석에 남긴다" 충족).
--      대상: 원격 프로젝트 psrnsasxpkpwqdukjdmt(운영), MCP execute_sql로 조회. 넣어본 행은 전부 rollback 했다.
--     ⓐ Realtime 가용: `pg_publication` supabase_realtime 1건, `realtime.broadcast_changes()` 존재,
--        anon 키로 실제 채널 구독 → `SUBSCRIBED`. → 0023 적용이 chat_messages INSERT를 죽이지 않는다.
--     ⓑ `realtime.send` 정의가 이 스텁과 동일하고 **`private boolean DEFAULT true`** 다(실측).
--        → 트리거가 인자 3개만 넘겨도 방송은 private 채널로 나가고, 0023의 RLS가 실제 관문이다.
--     ⓒ `realtime.messages`는 원격도 range 파티션(`relkind='p'`). **파티션 유지는 "자동"이 아니라
--        "Realtime 테넌트가 활성일 때 자동"이다** — 확인 시작 시점엔 자식 파티션이 **0개**였고, 그 상태에서
--        INSERT는 `23514 no partition of relation "messages" found for row`로 실패했다(실측). anon 클라이언트가
--        한 번 구독하자 Realtime 서비스가 5일치(07-28~08-01)를 만들었고, 그 뒤 같은 INSERT는 1행 성공했다
--        (`private=t` 확인). → 이 프로젝트는 Realtime을 쓴 적이 없어 비어 있었던 것이며, 실사용이 시작되면
--        유지된다. 다만 **무활동이 길면 다시 비어 방송만 조용히 사라질 수 있다**(`docs/tech-debt.md` #232).
--     ⓓ 적용 롤 `postgres`의 `rolbypassrls=t`(rolsuper=f). → 0023의 "INSERT 정책 불필요" 전제가 원격에서도
--        성립한다(#197의 ⓓ). 이 값이 f로 바뀌면 방송만 조용히 사라지므로, 롤이 바뀌면 다시 확인할 것.
create schema if not exists realtime;

-- 스키마 USAGE GRANT — 실측: `has_schema_privilege('authenticated', 'realtime'::regnamespace, 'USAGE')`
-- → t (anon·service_role도 동일). 이게 없으면 authenticated 롤이 realtime.messages를 아예 못 봐
-- "permission denied for schema realtime"으로 죽는다(테이블 GRANT와 별개 축).
grant usage on schema realtime to anon, authenticated, service_role;

create table if not exists realtime.messages (
  id             uuid primary key default gen_random_uuid(),
  topic          text not null,
  extension      text not null,
  payload        jsonb,
  event          text,
  private        boolean default false,
  updated_at     timestamp without time zone not null default now(),
  inserted_at    timestamp without time zone not null default now(),
  binary_payload bytea
);

alter table realtime.messages enable row level security;

grant insert, select, update on realtime.messages to anon, authenticated, service_role;

-- realtime.topic() — 세션 GUC `realtime.topic`을 읽는다(Realtime 서버가 채널 구독 시 이 GUC를
-- 설정한다). 0023의 RLS 정책이 참조한다.
create or replace function realtime.topic()
returns text
language sql
stable
as $$
  select nullif(current_setting('realtime.topic', true), '')::text
$$;

-- realtime.send() — broadcast_changes()가 내부에서 호출해 실제로 realtime.messages에 행을 쓴다.
-- (원본 그대로: private 기본값 true라 chat 트리거처럼 인자 3개만 넘기면 항상 비공개 채널이 된다.)
create or replace function realtime.send(payload jsonb, event text, topic text, private boolean default true)
returns void
language plpgsql
as $$
declare
  generated_id uuid;
  final_payload jsonb;
begin
  begin
    generated_id := gen_random_uuid();
    if payload ? 'id' then
      final_payload := payload;
    else
      final_payload := jsonb_set(payload, '{id}', to_jsonb(generated_id));
    end if;
    execute format('set local realtime.topic to %L', topic);
    insert into realtime.messages (id, payload, event, topic, private, extension)
    values (generated_id, final_payload, event, topic, private, 'broadcast');
  exception
    when others then
      raise warning 'WarnSendingBroadcastMessage: %', sqlerrm;
  end;
end;
$$;

-- realtime.broadcast_changes() — "Broadcast from Database" 패턴의 진입점. 0023의 트리거 함수가
-- 부른다.
create or replace function realtime.broadcast_changes(
  topic_name text, event_name text, operation text, table_name text, table_schema text,
  new record, old record, level text default 'ROW'
)
returns void
language plpgsql
as $$
declare
  row_data jsonb := '{}'::jsonb;
begin
  if level = 'STATEMENT' then
    raise exception 'function can only be triggered for each row, not for each statement';
  end if;
  if operation = 'INSERT' or operation = 'UPDATE' or operation = 'DELETE' then
    row_data := jsonb_build_object('old_record', old, 'record', new, 'operation', operation, 'table', table_name, 'schema', table_schema);
    perform realtime.send(row_data, event_name, topic_name);
  else
    raise exception 'Unexpected operation type: %', operation;
  end if;
exception
  when others then
    raise exception 'Failed to process the row: %', sqlerrm;
end;
$$;
-- realtime 스텁은 여기까지(Story 12.2, 0023 전용).
