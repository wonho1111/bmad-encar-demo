-- 02_data.sql — 로컬 스택 전용: 업무 데이터(매물·사진·채팅·가이드 문서) 적재
--
-- 무엇을 하나:
--   supabase/seed-local/data/*.json (운영에서 미리 받아둔 스냅샷)을 그대로 로컬에 넣는다.
--   외래키 순서: listings → listing_images → chat_rooms → chat_messages → guide_documents.
--
-- embedding 제외: listings·guide_documents의 embedding(vector(768))은 JSON에 없다(추출 시 select에서 뺐다
--   — 행당 9.5KB라 스냅샷이 과도하게 커짐). jsonb_populate_recordset은 JSON에 없는 컬럼을 NULL로 채우므로
--   그대로 insert하면 embedding=NULL로 들어간다. 검색·AI 기능에 필요하면 별도 backfill 스크립트로 채운다.
--
-- 트리거가 값을 다시 계산하는 컬럼: listings.seller_name, chat_rooms.buyer_name/seller_name은
--   BEFORE INSERT 트리거(set_listing_seller_name, set_chat_room_names)가 auth.users 이메일로 재계산한다.
--   01_accounts.sql이 운영과 같은 id·이메일로 계정을 먼저 만들어 두므로 결과가 운영과 같아진다.
--   즉 이 파일이 JSON의 seller_name 등 값을 그대로 못 믿어도 트리거가 정합성을 보장한다.
--
-- 멱등성: 전부 id가 PK이자 운영과 동일한 고정값이므로 on conflict (id) do nothing으로 재실행 안전.
--
-- 실행 방법: scripts/seed-local.sh 가 psql -v seed_local_dir=<이 파일이 있는 디렉터리 절대경로> -f 로 실행한다.
--   :seed_local_dir 을 \cd로 이동한 뒤 data/*.json을 상대경로로 읽는다(백틱 명령 substitution은
--   psql의 현재 작업 디렉터리를 기준으로 실행되므로 \cd가 먼저 필요하다).

\cd :seed_local_dir
\set ON_ERROR_STOP on

-- ── 1) listings ───────────────────────────────────────────────────────
-- ⚠️ `select *`가 아니라 명시적 컬럼 목록(0020 이전 25개 컬럼, view_count 제외)을 쓴다.
--   jsonb_populate_recordset은 JSON에 없는 키를 명시적 NULL로 채우는데(위 embedding 설명과
--   동일 원리), listings.view_count(0020)는 not null default 0이라 명시적 NULL이 그대로
--   제약 위반이 된다 — `select *`는 view_count까지 선택해 그 NULL을 그대로 insert에 넘기므로
--   시드 전체가 여기서 멈춘다(뒤따르는 listing_images·chat·guide_documents까지 함께 막힘,
--   ON_ERROR_STOP 때문). 아래처럼 view_count를 목록에서 아예 빼면 INSERT가 그 컬럼을 언급하지
--   않은 것과 같아 컬럼 기본값(0)이 대신 적용된다.
\set listings_json `cat data/listings.json`
insert into public.listings (
  id, seller_id, status, embedding, created_at, updated_at,
  manufacturer, model, body_type, year, price, mileage, color, fuel, transmission,
  displacement, seats, region, accident_free, options, description, seller_name,
  accident_status, is_single_owner, is_non_smoker
)
select
  id, seller_id, status, embedding, created_at, updated_at,
  manufacturer, model, body_type, year, price, mileage, color, fuel, transmission,
  displacement, seats, region, accident_free, options, description, seller_name,
  accident_status, is_single_owner, is_non_smoker
from jsonb_populate_recordset(null::public.listings, :'listings_json'::jsonb)
on conflict (id) do nothing;

-- ── 2) listing_images ────────────────────────────────────────────────
\set listing_images_json `cat data/listing_images.json`
insert into public.listing_images
select * from jsonb_populate_recordset(null::public.listing_images, :'listing_images_json'::jsonb)
on conflict (id) do nothing;

-- ── 3) chat_rooms ────────────────────────────────────────────────────
--   BEFORE INSERT 트리거 enforce_chat_room_seller가 listings.seller_id로 seller_id를 강제 재계산한다
--   (1단계에서 listings가 먼저 들어와 있어야 한다 — 파일 순서가 곧 실행 순서).
--   ⚠️ `select *`가 아니라 명시적 컬럼 목록(last_message_at 제외, Story 12.5)을 쓴다 — 위 1번
--   listings.view_count와 동일한 이유: 스냅샷 JSON엔 이 컬럼이 없어 jsonb_populate_recordset이
--   명시적 NULL로 채우는데, last_message_at은 not null이라 그 NULL이 그대로 제약 위반이 된다
--   (실측: "null value in column last_message_at ... violates not-null constraint"로 시드 전체가
--   멈춤). 컬럼을 목록에서 빼면 기본값(now())이 대신 적용되고, 아래 4번 다음의 백필 UPDATE가
--   실제 마지막 메시지 시각으로 다시 정확히 맞춘다.
\set chat_rooms_json `cat data/chat_rooms.json`
insert into public.chat_rooms (id, listing_id, buyer_id, seller_id, created_at, buyer_name, seller_name)
select id, listing_id, buyer_id, seller_id, created_at, buyer_name, seller_name
from jsonb_populate_recordset(null::public.chat_rooms, :'chat_rooms_json'::jsonb)
on conflict (id) do nothing;

-- ── 4) chat_messages ─────────────────────────────────────────────────
\set chat_messages_json `cat data/chat_messages.json`
insert into public.chat_messages
select * from jsonb_populate_recordset(null::public.chat_messages, :'chat_messages_json'::jsonb)
on conflict (id) do nothing;

-- 4b) chat_rooms.last_message_at 재백필(Story 12.5) — chat_messages_touch_room_last_message
--   트리거가 위 대량 INSERT의 각 행마다 발화해 last_message_at을 그 행의 created_at으로 덮어쓰지만,
--   스냅샷 JSON의 행 순서가 시간순이라는 보장이 없어(실측: 한 방 안에서도 뒤 행이 앞 행보다 이른
--   시각인 경우가 있었다) 트리거만으로는 "마지막으로 처리된 행"이 "가장 늦은 메시지"와 다를 수
--   있다. 그래서 0024 마이그레이션의 백필과 동일한 공식으로 한 번 더 정확히 맞춘다(멱등 — 여러 번
--   실행해도 항상 같은 결과로 수렴).
update public.chat_rooms r
set last_message_at = coalesce(
  (select max(m.created_at) from public.chat_messages m where m.room_id = r.id),
  r.created_at
);

-- ── 5) guide_documents ───────────────────────────────────────────────
\set guide_documents_json `cat data/guide_documents.json`
insert into public.guide_documents
select * from jsonb_populate_recordset(null::public.guide_documents, :'guide_documents_json'::jsonb)
on conflict (id) do nothing;
