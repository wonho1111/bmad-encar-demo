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
\set listings_json `cat data/listings.json`
insert into public.listings
select * from jsonb_populate_recordset(null::public.listings, :'listings_json'::jsonb)
on conflict (id) do nothing;

-- ── 2) listing_images ────────────────────────────────────────────────
\set listing_images_json `cat data/listing_images.json`
insert into public.listing_images
select * from jsonb_populate_recordset(null::public.listing_images, :'listing_images_json'::jsonb)
on conflict (id) do nothing;

-- ── 3) chat_rooms ────────────────────────────────────────────────────
--   BEFORE INSERT 트리거 enforce_chat_room_seller가 listings.seller_id로 seller_id를 강제 재계산한다
--   (1단계에서 listings가 먼저 들어와 있어야 한다 — 파일 순서가 곧 실행 순서).
\set chat_rooms_json `cat data/chat_rooms.json`
insert into public.chat_rooms
select * from jsonb_populate_recordset(null::public.chat_rooms, :'chat_rooms_json'::jsonb)
on conflict (id) do nothing;

-- ── 4) chat_messages ─────────────────────────────────────────────────
\set chat_messages_json `cat data/chat_messages.json`
insert into public.chat_messages
select * from jsonb_populate_recordset(null::public.chat_messages, :'chat_messages_json'::jsonb)
on conflict (id) do nothing;

-- ── 5) guide_documents ───────────────────────────────────────────────
\set guide_documents_json `cat data/guide_documents.json`
insert into public.guide_documents
select * from jsonb_populate_recordset(null::public.guide_documents, :'guide_documents_json'::jsonb)
on conflict (id) do nothing;
