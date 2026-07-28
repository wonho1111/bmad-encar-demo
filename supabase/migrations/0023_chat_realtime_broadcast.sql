-- 0023_chat_realtime_broadcast.sql — chat_messages Realtime Broadcast + 참가자 인가 RLS
--   (Story 12.2, AC-CHAT-3, FR20·21 실시간 토대)
--
-- 왜: 채팅은 아직 3초 폴링뿐이다(Story 12.3 이전). 폴링을 없애려면 그 전에 "메시지 INSERT를
--   실시간 채널로 방송하고, 그 채널을 방 당사자만 구독할 수 있게 인가하는" DB 토대가 먼저 있어야
--   한다. 클라이언트 구독 코드(web/app)는 이 마이그레이션의 범위가 아니다 — Story 12.3 몫.
--
-- 이 마이그레이션이 하는 일:
--   1) chat_messages AFTER INSERT 트리거(SECURITY DEFINER) — Supabase Realtime의
--      "Broadcast from Database" 패턴(`realtime.broadcast_changes()`)으로 새 메시지를
--      `chat:room:{room_id}` 비공개(private) 채널에 방송한다.
--   2) `realtime.messages`에 SELECT 정책 1개 — 그 방(chat_rooms)의 buyer_id 또는 seller_id인
--      사용자만 자기 방 토픽을 읽을 수 있다. INSERT/UPDATE/DELETE 정책은 두지 않는다(아래 이유).
--
-- self-contained: `public.chat_rooms`/`public.chat_messages`(0003)에만 의존한다. `realtime` 스키마
--   (schema·messages 테이블·broadcast_changes()/topic() 함수)는 Supabase 플랫폼이 항상 제공하는
--   계약면이라 마이그레이션 번호에 의존하지 않는다(auth/storage 스키마와 동일한 축 — 원격은 플랫폼이
--   이미 갖추고 있고, `scripts/migration-check-prelude.sql`이 게이트·CI용 빈 컨테이너에 그 계약면을
--   재현한다. 이번에 realtime 스키마 스텁을 그 프렐류드에 추가했다 — 우회가 아니라 실제 플랫폼에
--   있는 걸 빠뜨려 게이트가 red나는 걸 막는 "정당한 확장"이다, docs/conventions.md §9.1).
--
-- ⚠️ INSERT 정책이 realtime.messages에 필요 없는 이유: 이 방송 INSERT는 클라이언트가 아니라
--   **이 트리거 함수(SECURITY DEFINER)** 가 수행한다. 함수는 마이그레이션 적용 롤(postgres) 소유가
--   되고, postgres는 `rolbypassrls=true`(실측: `select rolbypassrls from pg_roles where
--   rolname='postgres'` → t)라 이 INSERT는 RLS를 우회한다 — 0016의 `enforce_chat_room_seller()`가
--   이미 같은 원리로 `public.listings`를 조회한다. 클라이언트가 realtime.messages에 직접 쓰는
--   경로는 이 스토리에 없다(브로드캐스트를 클라가 보내는 기능은 범위 밖).
--
-- ⚠️ 토픽 리터럴 `'chat:room:' || room_id::text`는 트리거 함수·RLS 정책 양쪽에 **동일하게** 박는다
--   (한쪽만 바뀌면 조용히 깨진다 — 트리거는 방송을 계속하는데 정책은 다른 리터럴을 찾아 전원 차단,
--   또는 그 반대로 전원 허용이 될 수 있다).

-- ── 1) AFTER INSERT 트리거 (SECURITY DEFINER) ───────────────────────────
-- search_path를 빈 문자열로 고정 — 정의자 권한 함수의 search_path 하이재킹 방지(0016과 동일 원칙).
-- 본문의 모든 참조(realtime.broadcast_changes)를 스키마로 완전히 한정했으므로 빈 search_path에서도
-- 정상 동작한다.
create or replace function public.chat_messages_broadcast()
returns trigger
security definer
set search_path = ''
language plpgsql
as $$
begin
  perform realtime.broadcast_changes(
    'chat:room:' || new.room_id::text,  -- topic: 이 메시지가 속한 방의 비공개 채널
    tg_op,                               -- event
    tg_op,                               -- operation
    tg_table_name,                       -- table
    tg_table_schema,                     -- schema
    new,                                 -- new record
    old                                  -- old record (AFTER INSERT라 항상 NULL)
  );
  return null;  -- AFTER 트리거의 반환값은 무시되지만 관례상 null을 돌려준다.
end;
$$;

-- 트리거 함수는 클라이언트가 직접 호출할 필요가 없다. PostgREST가 public 함수를 /rest/v1/rpc로
--   자동 노출하므로 default EXECUTE(PUBLIC) 권한을 회수해 그 노출을 없앤다(0016의
--   enforce_chat_room_seller()와 동일 원칙, advisor 0028/0029).
--   (이전 문구는 "SECURITY DEFINER 직접 호출 경로"까지 막는다고 했는데 그건 사실이 아니다 —
--    트리거 함수는 EXECUTE가 있어도 `trigger functions can only be called as triggers`로 거부된다.
--    실측 확인. 막고 있는 건 RPC 목록 노출 한 축이다.)
--   트리거는 테이블 소유자 권한으로 발화하므로 EXECUTE 회수 후에도 정상 동작한다.
--   Supabase는 anon/authenticated에 EXECUTE를 직접 부여하므로 PUBLIC뿐 아니라 두 롤에서도 명시 회수한다.
revoke all on function public.chat_messages_broadcast() from public;
revoke all on function public.chat_messages_broadcast() from anon;
revoke all on function public.chat_messages_broadcast() from authenticated;

-- UPDATE/DELETE는 일반 사용자 경로에서 발생하지 않는다(0003 헤더: chat_messages는 영속·불변) —
-- 불필요한 이벤트 배선을 하지 않는다(A2 단순함 우선).
drop trigger if exists chat_messages_broadcast_trigger on public.chat_messages;
create trigger chat_messages_broadcast_trigger
after insert on public.chat_messages
for each row execute function public.chat_messages_broadcast();

-- ── 2) realtime.messages RLS: 방 당사자 한정 SELECT ─────────────────────
-- realtime.messages는 이 레포가 만든 테이블이 아니라 Supabase 플랫폼 테이블이다(storage.objects와
-- 같은 축) — 0012가 storage.objects에 한 것과 동일하게 drop-if-exists 후 재생성해 재적용 시에도
-- 안전하게 한다.
--
-- `realtime.topic()`은 세션 GUC `realtime.topic`을 읽는 함수다(Realtime 서버가 클라이언트의 채널
-- 구독 요청을 받으면 그 채널 이름으로 이 GUC를 설정하고, authenticated 롤 + 그 유저의 JWT로
-- realtime.messages를 조회해 인가를 확인한다 — 공식 Broadcast Authorization 패턴).
--
-- 조건이 두 축인 이유(2026-07-28 후속 코드리뷰가 실측으로 잡은 결함의 정정):
--   ① `exists (...)` = **세션 축** — "이 세션이 구독하려는 토픽(`realtime.topic()`)의 방에 당사자인가".
--      Realtime 서버가 구독 인가를 물을 때 판정해야 하는 것이 이것이다.
--   ② `topic = realtime.topic()` = **행 축** — "지금 보려는 이 행이 그 토픽의 행인가".
--      처음엔 ①만 뒀는데, ①은 행의 어떤 컬럼도 참조하지 않아 **세션 상수**로 평가된다. 그래서
--      아무 방 하나의 당사자이기만 하면 `select * from realtime.messages`(토픽 필터 없이)로
--      **모든 방의 방송 행**이 보였다 — 로컬 Supabase 스택에서 재현 확인(방1 구매자가 방2의
--      메시지 본문을 읽음). 오늘은 `realtime` 스키마가 PostgREST 노출 대상(public·graphql_public)이
--      아니라 클라이언트가 닿을 수 없고 Realtime 서버는 항상 토픽으로 필터링하지만, 그건 **정책이
--      아니라 외부 호출자가 공급하던 안전장치**였다(CLAUDE.md B9 "권한만 주고 정책이 없으면 다 보인다").
--   실제 구독 인가가 ②로 깨지지 않는지 확인함: 로컬 Realtime 서버(:55321)에 private broadcast 채널을
--   실제 웹소켓으로 구독해 ②추가 전/후 모두 당사자=ok(buyer·seller), 제3자=Unauthorized로 동일.
--   **메시지가 0건인 방에서도 인가된다** — Realtime의 읽기 검사는 기존 행을 찾는 게 아니라 그 토픽의
--   레코드로 정책을 평가하기 때문이라, ②를 더해도 "빈 채널은 구독 못 함" 같은 회귀가 없다(실측).
-- ⚠️ 이 정책은 `public.chat_rooms`의 RLS에 **의존한다.** `exists (...)` 하위 질의는 정책을 평가하는
--   롤(authenticated)의 권한으로 돌기 때문에, chat_rooms의 SELECT 정책이 그 방을 안 보여주면 여기서도
--   방을 못 찾아 구독이 거부된다. 즉 `chat_rooms_select_participant`(0003)를 좁히거나 authenticated의
--   SELECT GRANT를 거두면 **Realtime 구독이 조용히 전원 차단된다** — 원인이 이 파일에 없으므로 찾기
--   어렵다. 실측: 그 정책의 조건을 `false`로 바꾸니 이 스토리의 실DB 테스트 4건이 red가 됐다.
--   (오늘은 두 조건이 같은 것을 뜻해 중복이지만, 한쪽만 바뀌는 순간 갈라진다.)
drop policy if exists "chat_room_participants_select_broadcast" on realtime.messages;
create policy "chat_room_participants_select_broadcast"
on realtime.messages
for select
to authenticated
using (
  extension = 'broadcast'
  and topic = realtime.topic()
  and exists (
    select 1
    from public.chat_rooms r
    where 'chat:room:' || r.id::text = realtime.topic()
      and (auth.uid() = r.buyer_id or auth.uid() = r.seller_id)
  )
);
