-- 0004_guide_documents.sql — FR15 문서 RAG 코퍼스② + pgvector HNSW
-- 원격(살아있는 DB)에 실제 적용된 순서(과거 사실 기록): 0001 → 0002(+0002b/c/d 패치) → 0004 → 0006.
--   0003(chat)·0005(admin)은 타 에픽이 채움(번호 갭 의도됨). 이 순서는 지금의 요구사항이 아니다 —
--   Story 8.6부터 self-containment(=자기보다 앞 번호 마이그만 가정)를 마이그레이션 게이트(CI)가 강제한다.
-- ⚠️ ai_readonly가 이 테이블을 읽으려면 GRANT(테이블 권한) + 정책(행 가시성)이 둘 다 필요.
--    (4.1 listings에서 겪은 "GRANT SELECT만으론 행이 안 보임" 함정을 guide_documents에 동일 적용.)
-- ⚠️ Story 8.6: 이 파일은 원래 ai_readonly 롤이 0006에서만 생성된다고 가정해 self-contained가 아니었다
--    (0004가 자기보다 뒤 번호인 0006의 상태를 가정 — 게이트가 fresh DB 적용에서 이를 실제로 잡았다).
--    아래 "④' 읽기전용 롤 보장"이 0006:22-26과 동일한 멱등 가드를 여기 복사해 그 역참조를 끊는다.
--    fresh DB 번호순 적용: 0004가 롤을 만듦 → 0006의 동일 DO 블록은 no-op. 원격(이미 롤 존재): 양쪽 no-op.
--
-- 이 마이그레이션이 하는 일:
--   1) pgvector 확장 보장(이미 0.8.0 설치됨 — 멱등)
--   2) guide_documents 테이블 — 차량 상식·구매 가이드 문서(코퍼스②) + embedding vector(768)
--   3) HNSW 인덱스 2개 — guide_documents.embedding + listings.embedding(4.4 의미검색용)
--   4) ai_readonly 권한(GRANT SELECT) + RLS enable + 가시성 정책(함정 회피)
--
-- 임베딩 차원: vector(768) — gemini-embedding-001(output 768, L2 정규화) 정합 (docs/conventions.md §1)

-- ── 1) pgvector 확장 보장 ────────────────────────────────────────────
create extension if not exists vector;

-- ── 2) guide_documents 테이블 ────────────────────────────────────────
-- if not exists: 재적용·신규 환경 재생성 시 "already exists"로 중단되지 않게(멱등).
create table if not exists public.guide_documents (
  id          uuid primary key default gen_random_uuid(),
  title       text not null,
  content     text not null,
  embedding   vector(768),                 -- 코퍼스② 임베딩(4.2 backfill로 채움, 그 전엔 NULL)
  created_at  timestamptz not null default now()
);

comment on table public.guide_documents is
  'FR15 문서 RAG 코퍼스② — 차량 상식·구매 가이드. embedding은 4.2 backfill(L2 정규화 768)로 채움. AI 읽기전용 경로만 조회.';
comment on column public.guide_documents.embedding is
  '문서 content의 768차원 임베딩(gemini-embedding-001, L2 정규화). HNSW 코사인 인덱스 대상.';

-- ── 3) HNSW 인덱스 (코사인). 정규화된 768 벡터 대상. 연구 권장 m=16, ef_construction=200 ──
-- HNSW: 벡터 유사도 검색을 빠르게 해주는 그래프형 인덱스. 빈 테이블에 먼저 만들어도 행 추가 시 점진 색인됨.
create index if not exists guide_documents_embedding_hnsw
  on public.guide_documents using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- listings.embedding 의미검색(4.4)용 동일 인덱스(없으면 순차 스캔). NULL 임베딩은 인덱스가 스킵.
create index if not exists listings_embedding_hnsw
  on public.listings using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- ── 4) ai_readonly 권한 + RLS 가시성 (⚠️ GRANT만으론 행 안 보임 — 정책 필수) ──
-- ④' 읽기전용 롤 보장(0006:22-26과 동일 — 그대로 복사, 새 패턴 발명 금지).
--    0006과 중복 생성이지만 양쪽 다 멱등이라 번호순·역순 어느 쪽으로 적용해도 안전.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'ai_readonly') then
    create role ai_readonly nologin;
  end if;
end $$;

grant select on public.guide_documents to ai_readonly;
alter table public.guide_documents enable row level security;
-- Postgres엔 'create policy if not exists'가 없으므로 drop-후-create로 재적용 안전(멱등).
drop policy if exists "guide_documents_ai_readonly_select" on public.guide_documents;
create policy "guide_documents_ai_readonly_select" on public.guide_documents
  for select to ai_readonly using (true);
-- (클라이언트는 guide_documents를 직접 읽지 않음 → authenticated 정책은 미요구·생략. 필요해지면 후속에서 추가.)
