-- 0004_guide_documents.sql — FR15 문서 RAG 코퍼스② + pgvector HNSW
-- 적용 순서: 0001 → 0002(+0002b/c/d 패치) → 0004 → 0006(이미 적용). 0003(chat)·0005(admin)은 타 에픽이 채움(번호 갭 의도됨).
-- ⚠️ 0006(읽기전용 롤) 적용 후이므로, ai_readonly가 이 테이블을 읽으려면 GRANT(테이블 권한) + 정책(행 가시성)이 둘 다 필요.
--    (4.1 listings에서 겪은 "GRANT SELECT만으론 행이 안 보임" 함정을 guide_documents에 동일 적용.)
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
create table public.guide_documents (
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
create index guide_documents_embedding_hnsw
  on public.guide_documents using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- listings.embedding 의미검색(4.4)용 동일 인덱스(없으면 순차 스캔). NULL 임베딩은 인덱스가 스킵.
create index if not exists listings_embedding_hnsw
  on public.listings using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 200);

-- ── 4) ai_readonly 권한 + RLS 가시성 (⚠️ GRANT만으론 행 안 보임 — 정책 필수) ──
grant select on public.guide_documents to ai_readonly;
alter table public.guide_documents enable row level security;
create policy "guide_documents_ai_readonly_select" on public.guide_documents
  for select to ai_readonly using (true);
-- (클라이언트는 guide_documents를 직접 읽지 않음 → authenticated 정책은 미요구·생략. 필요해지면 후속에서 추가.)
