# Addendum — 차장님 증분 PRD (기술 how·다운스트림 재료)

> PRD 본문(capability)엔 두지 않는 **기술적 how·후보·근거**. 아키텍처(`bmad-create-architecture`)·UX(`bmad-ux`) 단계 입력. 확정 아님(후보·방향).

## 이미지 (F7)
- **스토리지 후보**: Supabase Storage(기존 Supabase 스택 재사용). **업로드는 anon key + Storage RLS(본인 경로에만 insert)만 사용 — service_role 금지(규칙 6, viewcount RPC와 대칭)**. 공개 접근 여부(공개 버킷 vs 서명URL)는 OI-3에서 FR11 우회 위험과 함께 결정. 대안: 외부 CDN(범위 밖 과설계).
- **스키마 방향**(택1, 아키텍처 확정):
  - (a) `listings`에 `image_urls text[]`(nullable) — 최소 변경, 데모 단순. 순서=대표사진.
  - (b) 별도 `listing_images` 테이블(listing_id FK, url, sort_order) — 정규화, 확장성. 데모엔 (a)가 A2 부합 가능.
- **마이그레이션**: forward-only 신규 마이그레이션(0011~). **non-null 금지**(기존 100건 보존). 5:3 크롭은 업로드 시 또는 표시 시 CSS `aspect-ratio`.
- 계약 변경: `docs/conventions.md §4 ListingCard`에 사진 필드 추가(현재 "사진 없음" 명시를 개정), `project-context 규칙 5`도 갱신.
- **시드 사진 소싱(OI-5 확정) = Wikimedia Commons + 이미지별 크레딧(㉠)**:
  - 절차: 시드의 `manufacturer`+`model`(예: "Hyundai Sonata DN8")로 Commons API(`action=query&generator=search&gsrnamespace=6&prop=imageinfo&iiprop=url|extmetadata`) 검색 → **CC-BY/CC-BY-SA/CC0/PD만** 필터 → 모델당 3~4장 → Supabase Storage 업로드 → `image_urls`에 [대표1, 상세2~3] 세팅. 색·연식은 근접 매칭(정확 일치 아님), 동일모델 중복은 각도 다른 컷 분배.
  - **라이선스 크레딧 저장(㉠, 필수)**: 다수가 **CC BY-SA 4.0**이라 "출처: Commons" 한 줄로 부족 → 이미지별 **저작자·라이선스명·원본링크**를 저장. 스키마 방향: `image_urls text[]`와 병렬로 `image_credits jsonb`(또는 `listing_images` 정규화 시 행에 credit 컬럼). BY-SA는 2차물 동일 라이선스(사진 자체엔 영향 없음). CC0/PD만 쓰면 크레딧 의무 0이나 풀이 좁아짐 → ㉠ 채택.
  - **커버리지 실측**(2026-07-12, 6모델 API probe): 국산 세대코드(DN8·MQ4·DL3·RG3)까지 실차 사진 매칭됨. 15모델 목업(쏘나타·쏘렌토 각 2장 포함)으로 자동매칭·크레딧·동일모델 편차 실증 → 커버리지 양호, 배경은 모터쇼/길거리/해외로 제각각(실제 엔카 판매자 사진과 동일 결, 합성 미혼합이 핵심).
  - 목업 화질 열화(자글자글)는 **다운스케일 앨리어싱**(큰 사진을 작은 카드에 브라우저가 즉석 축소) — 소스/방안 문제 아님. 실서비스는 Next.js Image/이미지 CDN이 카드 크기 썸네일을 Lanczos로 미리 생성해 서빙하므로 무관.
- **조회수 정렬(OI-5 확정) = view_count + SECURITY DEFINER RPC**:
  - `listings.view_count int not null default 0` 추가. 상세 진입 시 RPC `increment_listing_view(p_id uuid)` 호출로 +1. `listings` UPDATE RLS=소유자 전용 + `service_role` 금지(규칙 6)라 클라 직접 UPDATE 불가 → RPC로 우회(anon도 조회수 올려야 하므로).
  - **Supabase 표준 확인**(agent-reach 다방면, GitHub Discussions #4364 메인테이너 동일 패턴). 보안 필수: ① 함수 `SET search_path=''` + 스키마 정규화 참조 ② 본문은 그 id의 `view_count = view_count + 1` **한 문장만**(임의 UPDATE 금지) ③ `GRANT EXECUTE ... TO anon, authenticated`. 내장 rate-limit 없음 → 데모는 무시, 실서비스는 IP/세션 중복방지(별도 카운트 테이블 or 시간창) 추가. 상세=`research-supabase-viewcount-rpc.md`.
  - 마이그레이션 순서: 0011 이미지(text[]+credits) → 0012 신뢰속성 → 0013 role CHECK 완화 → **0014 view_count + RPC**(additive, 상호 무충돌).

## 신뢰속성·옵션 (F8) — 리서치 결론(`research-data-*.md`)
- **신뢰속성 스키마**: `accident_status`(무사고/사고 2단; 이상적 enum 무사고/외판교환/사고) + `is_single_owner bool` + `is_non_smoker bool`. 기존 `accident_free bool` 승격. 전부 **판매자 신고 티어** → UI에 "판매자 제공 정보" 라벨.
- **옵션 희소도**: 앱 레이어 상수 2개 — ① `COMMON_OPTIONS`(보편, 저순위: 스마트키·블루투스·후방카메라·열선시트·자동에어컨·크루즈 등) ② `OPTION_PRIORITY`(옵션명→점수; 엔카 감가율 랭킹 선루프>내비≈HUD>차로이탈 + 희소 옵션 오토파일럿·파노라마·V2L 수동 추가). 카드=priority desc 상위 3~4, 상세=카테고리 전량.
- 옵션 카테고리(엔카 5분류): 외관/내장·안전·편의/멀티미디어·시트·기타.

## 실시간 채팅 (F12)
- **transport 후보**: Supabase Realtime(Postgres 변경 구독). 기존 `chat_messages` + RLS 재사용, service_role 불필요. 폴링(3초, `ChatRoomMessages.tsx`) 제거.
- **멱등키(#6)**: 클라 생성 uuid를 메시지 PK/유니크로 → 재전송 시 upsert/무시. `web/src/lib/messages.ts` sendMessage 경로.
- **재연결(#7)**: 구독 상태(connected/reconnecting/offline) → 비차단 배너.
- Flutter: `supabase_flutter`의 Realtime 구독으로 동일.

## RAG·DB (F13) — 리서치 3종 기반 설계 (research-current-rag-implementation / research-langx-rag-patterns)
- **현황 확증**: `graph.py`가 A/B/C 3분기 StateGraph. `router_node.py` = Gemini 구조화출력(`Literal["A","B","C"]`)+코드 재검증. 경로 B(`doc_rag_node.py`)=벡터 전용, 가이드 문서(`guide_documents` 12개)는 **title만 부가**·content 미반영. 하이브리드·되묻기·청킹·LangSmith 없음.
- **4분기 라우팅**: `add_conditional_edges` 딕셔너리를 `{REJECT→guard, CLARIFY→clarify(신규), SQL→sql, HYBRID→hybrid}`로 확장. 라우터 Literal 4값. 구조 변경 작음. (Command 패턴 리팩터는 선택)
- **CLARIFY(신규 노드)**: `interrupt()`/체크포인터 **미사용**(REST 단발요청 부적합·재실행 함정). 되묻기 문장을 answer로 반환 → 프런트가 채팅에 표시 → 사용자 다음 메시지를 기존 멀티턴 `contextualize_query`로 이어붙여 그래프 재호출. CLARIFY는 "조건 전무 극단 질의"에만 좁게(라우터 프롬프트 신호).
- **HYBRID**: `doc_rag_node` 승격. `sql_guard` WHERE(구조조건) + `ORDER BY embedding <=> %s::vector`를 **단일 쿼리**(CTE·RRF 없이). 구조조건 못 뽑으면 기존 벡터검색 유지(회귀 없음). 주의: 매물 급증 시 `hnsw.iterative_scan=relaxed_order` 필요할 수 있음(현재 ~100건 저위험).
- **가이드 문서 content 반영 + 컷오프**: 코사인 거리 `<=>`가 임계값(예 0.3) 이하일 때만 content를 답변 근거로 사용(현재 무조건 title 부착 → 노이즈). 임계값은 실측 튜닝.
- **청킹**: 현 12문서=문서당 1임베딩 ≈ page-level(NVIDIA 벤치 부합) → **미도입**. ≥20문서/≥800토큰 시 `##` 헤딩 섹션 청킹(오버랩 불필요).
- **LangSmith**: Developer 무료. `LANGCHAIN_TRACING_V2=true` + `LANGCHAIN_API_KEY` env 2개(코드변경 0, 자동계측). 카드 미등록=5000trace/월 하드캡. 평가/Deployment 미도입(eval이 trace 과금).
- **커넥션 풀(#5)**: `api/app/db/readonly.py` psycopg 풀 + `connect_timeout` + async/스레드풀(이벤트루프 블로킹 해소). RAG 착수 前 선행.

## 디자인 시스템 (F10)
- Tailwind v4 `@theme`(CSS-first) 토큰. 팔레트(목업 v1): brand 페트롤 `#0C6E6B`, accent 앰버 `#DC7A2E`, trust green `#1E8E63`, 다크테마 토큰 별도. 이미지 비율 5:3.
- 반응형: 단일 코드(m-dot 아님). 카드 그리드→모바일 캐러셀, 필터 사이드바→바텀시트.

## 역할 모델 (OI-1) — 확정: 역할 통합 (F14)
- 업계 표준(6/6, `research-account-nav-model.md`) + 사용자 결정 = **통합**.
- **영향 지점(구현 시)**: `profiles.role` **컬럼은 존치**(제거 금지 — `is_admin()`·`0005` 의존, 제거 시 관리자 기능 전멸). buyer/seller 값만 **무의미화**하고 admin은 유지 → 방향은 `account_type`(admin/일반 2값)로 **축소·재활용**(미래 개인 vs 사업자 축을 싸게 열어둠). · 가입 화면(역할선택 제거) · 매물 RLS(이미 소유권 기반이라 사실상 무변경) · 채팅 RLS·트리거(이미 참여자/소유권 기준) · 관리자 역할관리 화면(구매자/판매자 구분 UI 정리).
- **마이그레이션**: `role` CHECK 완화(buyer/seller 무의미화, admin 존치). 기존 계정 데이터 보존(forward 마이그레이션). 매물·채팅 RLS는 이미 role 비의존이라 재작성 최소.
- 성격이 UI/이미지 증분과 달라(인증·권한) 구현 단계에서 **분리 관리** 권장.

## party-mode 리뷰 반영 — 아키텍처/구현 "숨은 궁합" (Winston·Amelia)
- **이미지 스토리지 × FR11**: Supabase Storage **공개 버킷**이면 sold/삭제 매물 사진 **공개 URL이 살아남아** FR11(비노출) 우회. 결정 필요: 비공개+서명URL(일관되나 비용/복잡) vs 공개+수용(명시 기록). `image_urls text[]`는 매물 삭제 시 스토리지 **고아 정리** 주체를 명시해야(text[]엔 cascade 없음).
- **웹소켓 재연결 갭**: Supabase Realtime은 끊긴 동안 메시지 replay 안 함 → 재구독 시 **"마지막 수신 이후" 1회 보정 select** 필요(폴링이 완전 사라지는 게 아님). 멱등키는 `chat_messages` 불변이라 **`ON CONFLICT DO NOTHING`**(upsert-update는 RLS 거부).
- **커넥션 풀 × SET ROLE(#5·FR50)**: 트랜잭션 풀러(:6543)는 세션 `SET ROLE ai_readonly` 누수 → 각 쿼리를 `BEGIN; SET LOCAL ROLE ai_readonly; SELECT…; COMMIT`으로 감싸 격리. 선행이라 우선순위 높음.
- **F8 스키마 연쇄(drift 금지)**: `accident_free`→`accident_status`/`is_single_owner`/`is_non_smoker`는 **추가만(드롭 금지)** + `sql_guard` 화이트리스트 + AI 프롬프트 스키마 + 시드 backfill + `ListingCard` 계약(conventions §4·규칙5) + web/app 매퍼까지 **락스텝**. 옵션 희소도 상수는 conventions.md 단일출처 선언(web TS·app Dart 이원화 금지).
- **가이드 content 주입 × answer_node**: 현재 `answer_node`는 LLM 재작성 금지(고정 템플릿). content 반영은 "거리 컷오프 통과분만 답변 꼬리에 근거 문단"으로 좁혀 무상태·결정론 계약 유지.
- **라우터 4분기 회귀**: `RouterDecision` Literal · `_fallback_route` · `_route_decision` **3곳 동시 확장**(하나 빠지면 신 라우트를 C로 흡수해 조용한 회귀). 4값 분기·CLARIFY 발동에 결정론적 단위테스트 신설(부채 #13/#14 연계).
- **마이그레이션 순서(additive)**: 0011 이미지(text[] nullable + image_credits) → 0012 신뢰속성+backfill(accident_free 병존) → 0013 role CHECK 완화(admin 존치) → 0014 view_count + increment RPC. 전부 additive, 상호 충돌 없음.
- **배포 순서**: db(마이그레이션)→api(Cloud Run)→web(Vercel), 새 필드 nullable 하위호환(3개 따로 배포라 순서 안 맞으면 카드 렌더 깨짐).
- **관측성 사각(다음 증분)**: LangSmith는 api RAG만 봄. 웹소켓 구독실패·이미지 업로드실패는 구조화 로그 한 줄 정도만(전면 APM은 과설계).
