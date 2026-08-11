---
title: '17.4 정지된 판매자의 매물 비노출 (사용자 결정으로 에픽 불변식을 뒤집는 스토리)'
type: 'feature'
created: '2026-08-11'
status: 'backlog'
baseline_revision: '27e5b75'
review_loop_iteration: 0
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-17-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/spec-17-1-정지-회원-쓰기-차단-rls.md'
---

<intent-contract>

## Intent

**⚠️ 이 스토리는 Epic 17이 스스로 내건 원칙을 뒤집는다. 그 결정은 사용자가 했다.**

17.1의 불변식 후반부는 *"정지된 계정의 **읽기**는 아무것도 줄어들지 않는다"* 였고, Never 절은
*"`listings_select_*`를 좁히지 않는다 — 정지된 판매자의 기존 매물은 다른 구매자에게 **계속 보여야
한다**"* 라고 명시했다. **이 스토리는 그 문장을 폐기한다.**
근거는 추론이 아니라 **사용자 지시**다(2026-08-11 Discord, [[DW-804]] (a)에 대한 답 — *"숨겨야돼"*).
오케스트레이터가 세 선택지(숨김 / 유지 / "응답 불가" 배지)를 제시하고 "유지"를 기본값으로 두겠다고
밝힌 뒤 받은 답이다. **다음 사람이 "왜 읽기가 좁아졌지"를 다시 조사하지 않도록, 이 문단이 그 근거의
정본이다.**

**Problem:** 정지된 판매자의 `on_sale` 매물이 **계속 검색·노출되고 구매자가 채팅방을 열어 말을 걸
수 있는데, 판매자는 영원히 답할 수 없다**(17.1이 발신만 막았다). 구매자는 "무시당했다"고 읽는다
([[DW-804]] (a)).

**⚠️ 착수 전에 반드시 알아야 할 사실 3가지 — 모르고 시작하면 서비스가 통째로 빈 화면이 된다.**

1. **"주인이 활성인가?"를 정책 안에서 순진하게 물으면 매물이 전부 사라진다.**
   RLS 정책 안의 서브쿼리는 **참조 테이블의 RLS도 함께 탄다.** `profiles`의 정책은 실측상
   `profiles_select_self`(본인만) · `profiles_select_admin`(관리자만) 둘뿐이고 **`anon` 대상 정책은
   0건**이다(2026-08-11 로컬 55322 실측).
   그래서 `listings_select_on_sale`에
   `exists (select 1 from public.profiles where id = listings.seller_id and status='active')`
   를 넣으면 — **판매자의 profiles 행이 안 보이므로 `exists`가 항상 거짓** → 비로그인은 **모든
   매물**이, 로그인 사용자는 **자기 것 말고 전부**가 사라진다.
   17.1이 쓴 `exists (... where id = auth.uid() ...)`는 **본인 행**이라 `profiles_select_self`가 열어
   줘서 동작했다. **이번엔 남의 행이라 그 근거가 성립하지 않는다.**
   → 해결은 이 레포에 이미 있는 패턴이다: **SECURITY DEFINER 판정 함수**(`is_admin()`·
   `is_admin_active()`가 정확히 이 이유로 그렇게 만들어졌다).

2. **그 사고는 검사가 초록불로 통과한다.** *"정지 판매자 매물이 안 보인다"* 만 단언하면 —
   **안 보이니까 통과**한다. 실제로는 활성 판매자 매물까지 전부 사라진 상태인데도.
   그래서 이 스토리의 모든 검사는 **긍정 대조군이 필수**다(비로그인·로그인 양쪽에서 활성 판매자
   매물이 계속 보인다). 없으면 그 검사는 아무것도 안 본다.

3. **조회 경로는 RLS 하나가 아니다. 이미 같은 문제를 푼 지도가 있다.**
   `docs/conventions.md` §6이 FR11(판매완료 비노출)의 **강제 지점 전량**을 열거해 뒀다 — 구조가
   똑같으므로 **그 목록을 이 스토리의 체크리스트로 그대로 쓴다**:
   - **매물 축** — `listings` RLS(authenticated `listings_select_on_sale` / anon
     `listings_select_on_sale_anon`) + `api/app/db/sql_guard.py`(경로 A, LLM 생성 SQL) +
     `api/app/graph/doc_rag_node.py`(경로 B 고정 SQL) + `api/app/graph/hybrid_rag_node.py`(13.3)
   - **이미지 축** — `listing_images_select_on_sale` / `_anon`(0012, `listings`에 조인)
   - **SECURITY DEFINER 축** — `get_seller_public_summary`(0019, 함수 본문 조건이 유일한 강제 지점)
   ⚠️ **AI 3경로는 `ai_readonly` 롤로 붙고 그 롤의 `listings` 정책은 `listings_ai_readonly_select`
   = `using(true)`다**(실측 확인). 즉 **RLS가 AI 경로를 안 막는다.** 매물 RLS만 고치면
   **AI는 정지 판매자 매물을 계속 추천하는데 눌러 들어가면 없는** 상태가 된다.

**Value:** 답할 수 없는 판매자에게 구매자를 계속 보내는 것은 제재가 아니라 **양쪽 모두에 대한
사고**다. 그리고 매물 노출은 **판매자가 정지 중에도 계속 얻는 이득**이라, 제재의 의미 자체가 샌다.

## Boundaries & Constraints

**Always:**

- **불변식을 한 문장으로 먼저 못박는다(17.1의 것을 대체한다):**
  *"`profiles.status='suspended'`인 판매자의 매물은 **구매자·비로그인·AI 응답 어느 조회 경로에서도
  노출되지 않는다.** 단 **판매자 본인과 관리자에게는 그대로 보인다.**"*
  뒷문장이 앞문장만큼 중요하다. 본인이 자기 매물을 못 보면 정지가 풀린 뒤 복구할 방법이 없고,
  관리자가 못 보면 관리 콘솔이 빈 화면이 된다.

- **판정은 SECURITY DEFINER 함수 하나로 모은다.** 예: `public.is_seller_active(uuid)` —
  `security definer` · `set search_path = ''` · `stable`. 근거는 위 Intent 1번(`profiles` RLS 우회가
  **필요**하다). `is_admin()`(0001)·`is_admin_active()`(0032)와 **같은 형태**로 쓰고, 각주에 그 계보를
  적는다. GRANT 대상은 **실제로 이 함수를 부르는 롤 전부** — 최소 `anon`·`authenticated`,
  그리고 AI 경로를 DB에서 막기로 하면 `ai_readonly`도. **GRANT를 빠뜨리면 그 롤에서 조회가 통째로
  실패한다**(42501) — 정책이 조용히 0행이 되는 게 아니라 요청 전체가 죽는다. 실측으로 확인한다.

- **AI 3경로는 코드가 아니라 DB에서 막는 것을 우선 검토한다.**
  `listings_ai_readonly_select`를 `using(true)` → `using(public.is_seller_active(seller_id))`로
  좁히면 **경로 A·B·하이브리드 3개가 한 자리에서 닫힌다.** 코드 3곳에 조건을 흩는 것보다
  단순하고(A2), 새 조회 코드가 생겨도 안 뚫린다(B9).
  ⚠️ 단 `sql_guard`는 **검증기**이지 주입기가 아니다(실측: LLM이 만든 SQL에 `status='on_sale'`이
  부정 없이 들어 있는지 **검사만** 한다). 그래서 LLM에게 판매자 조건을 추가로 요구하는 방향은
  택하지 않는다 — 프롬프트로 강제하는 건 계약이 아니다(B9).
  **이 선택이 FR11(sold)의 `using(true)` 설계를 깨지 않는지 실측으로 확인**하고 결과를 적는다.
  깨진다면 대안(코드 3곳)으로 가되 **왜 그랬는지**를 남긴다.

- **`listing_images` 축은 "자동으로 따라오는지"를 실측으로 확인한다.**
  `listing_images_select_on_sale`은 `listings`에 조인해 `l.status='on_sale'`을 건다. 중첩 RLS가
  적용되면 매물이 안 보이는 순간 사진도 자동으로 안 보인다 — **그럴 것 같다는 추론으로 넘기지
  않는다.** 실제로 정지 판매자 매물의 사진을 조회해 0행인지 재고, 결과를 Design Notes에 적는다.
  자동으로 안 따라오면 그 축도 명시적으로 막는다.

- **모든 검사에 긍정 대조군을 짝으로 둔다**(위 Intent 2번 — 이게 없으면 "전부 사라짐"이 green이다).
  최소: 비로그인이 활성 판매자 매물을 본다 / 로그인 구매자가 본다 / 목록 건수가 정지 처리 전후로
  **정확히 정지된 판매자의 매물 수만큼만** 줄어든다(0이 되지 않는다).

- **"존재 확인"으로 닫지 않는다**(CLAUDE.md B4). 정책이 **있는 것**과 실제로 **거르는 것**은 다르다.
  정지 판매자·활성 판매자의 매물을 실제로 심고, anon·구매자·본인·관리자·AI 롤 **5주체로 각각 조회**해
  본다.

- **red를 서로 다른 표기로 두 번 증명한다**(메모리 `guard-proof-must-vary-shape`):
  ⓐ 정책의 조건을 지운다 → 정지 판매자 매물이 보이는 단언이 red
  ⓑ 판정 함수 본문을 뒤집는다(`status='suspended'`를 요구) → **긍정 대조군**이 red
  두 축이 서로 다른 단언을 깨야 한다.

- **프로브 원복은 백업본으로 한다**(메모리 `probe-revert-never-git-checkout`).

- **기대값을 피검사 대상에서 다시 계산하지 않는다**(메모리 `self-consistent-assertions-never-fail`).
  `'suspended'`·`'active'`·`'on_sale'`·정책 이름은 **글자 그대로 박는다.**

- **`docs/conventions.md` §6에 "정지 판매자 비노출" 축을 등재한다.** §6은 지금 FR11 전용인데,
  **강제 지점 목록이라는 성질이 같다.** §6 말미가 이미 *"새 조회 경로를 열면 이 목록에 강제 지점을
  추가한다(규칙7)"* 고 요구한다. 그리고 §8(정지의 의미)의 *"정지는 열람이 아니라 쓰기 행동만
  막는다"* 는 문장은 **이제 사실이 아니다** — 정정한다. 정정할 때 **17.1의 원문을 지우지 말고
  "언제·누가·왜 뒤집었는지"를 남긴다**(§6의 다른 ✎ 정정 표기와 같은 형식).

- **검사 옆에 "이 검사가 안 보는 것"을 실측해서 적는다**(Epic 13 회고 약속).

- 끝나면 [[DW-804]] (a)를 `resolution:`과 함께 닫는다. [[DW-799]](채팅방 생성 미차단)는 이 스토리가
  증상 (1)의 원인으로 지목됐으므로 **재판정한다** — 매물이 안 보이면 방 생성 진입점도 사라지는지
  실측하고, 그래도 남는 경로가 있으면 열어 둔 채 `trigger:`를 갱신한다.

**Block If (멈추고 escalate):**

- **정지 판매자 매물을 숨기면 기존 채팅방·찜이 깨진다**는 것이 실측으로 확인되고(예: 구매자의 찜
  목록이나 진행 중 채팅방이 오류를 내며 죽는다), 회색 타일 같은 기존 처리로 흡수되지 않으면 —
  "깨진 화면"과 "매물 노출" 중 무엇을 고를지는 사용자 판단이다. 멈추고 묻는다.
  (참고: `/wishlist`는 이미 `isWishedListingBlocked`로 **RLS 차단 항목을 회색 타일**로 처리한다 —
  §6에 기록돼 있다. 이 경로는 흡수될 가능성이 높으니 **먼저 재보고** 판단한다.)
- **`ai_readonly` 정책을 좁히는 것이 FR11(sold) 축이나 가이드 문서 RAG를 깨뜨리는 것**이 확인되면
  멈추고 묻는다 — 그 축은 Epic 4·13이 만든 자리다.
- 관리자 콘솔이 정지 판매자 매물을 **못 보게 되는 것**이 확인되고 우회 형태를 못 찾으면 멈추고 묻는다.

**Never:**

- **판매자 본인의 조회를 좁히지 않는다.** `listings_select_own`은 그대로 둔다.
- **관리자 조회를 좁히지 않는다.** `listings_select_admin`은 `is_admin()` 그대로다 — 17.1이
  *"정지된 관리자도 열람은 허용"* 원칙으로 `is_admin_active()`를 읽기에 안 쓴 자리이고, 그 회귀
  가드(`test_suspended_admin_can_still_read_via_admin_select_policies`)가 이미 있다. **깨지 않는다.**
- **매물 데이터를 지우거나 `status`를 바꾸지 않는다.** 숨김은 **조회 시점의 판정**이어야 한다 —
  정지가 풀리면 **자동으로 다시 보여야** 하기 때문이다. 정지 시점에 `status`를 일괄 변경하면
  되돌리기가 필요해지고, 그건 CLAUDE.md B3(*"DB는 되돌리기가 없다"*)와 정면으로 어긋난다.
- **`profiles`의 SELECT 정책을 넓혀서 문제를 풀지 않는다.** 남의 회원 정보를 열어 주는 것은 이
  스토리가 요청받은 게 아니고, 훨씬 큰 노출이다. SECURITY DEFINER 함수를 쓴다.
- **기존 마이그레이션 파일을 수정하지 않는다.** 새 번호로 추가한다(§9.1의 `drop policy → create
  policy` 전진 패턴).
- **17.2·17.3의 자리를 건드리지 않는다**(조회수 함수 · 화면 문구 · `requireRole`).
- **앱(Flutter)에 별도 필터를 넣지 않는다.** 앱의 `_buyerQuery`는 `.eq('status','on_sale')` + RLS로
  붙으므로 **DB에서 막으면 자동으로 따라온다** — 실측으로 확인만 하고 코드는 안 건드린다(A3).
  안 따라오면 그때 판단하고 근거를 남긴다.
- **운영(`main`) 배포·원격 DB 적용을 하지 않는다.** 로컬 검증까지만(CLAUDE.md B3).

</intent-contract>

## Code Map

- `supabase/migrations/0002_listings.sql` -- `listings_select_on_sale`(authenticated, `status='on_sale'`) 원본.
- `supabase/migrations/0011_listings_anon_select.sql` -- `listings_select_on_sale_anon`(anon) + **컬럼 단위
  GRANT 화이트리스트**. ⚠️ §8이 경고한다 — anon에 새 컬럼이 필요해지면 목록에 없는 한 **요청 전체가
  42501로 죽는다.** 이 스토리는 컬럼을 늘리지 않는 설계를 택한다(판정을 함수로 빼는 이유 중 하나).
- `supabase/migrations/0001_profiles.sql` -- `is_admin()`(SECURITY DEFINER) · `profiles_select_self`.
  새 판정 함수의 형태 원본.
- `supabase/migrations/0032_suspended_write_block.sql` -- `is_admin_active()`(SECURITY DEFINER,
  `authenticated`에만 grant). 같은 계보의 최신 예시.
- `supabase/migrations/0012_listing_images.sql` -- `listing_images_select_on_sale` / `_anon`
  (`listings` 조인) · `listing_images` 의 `ai_readonly` 정책 `using(true)`(0012:153 근처, 의도된 설계 CR2).
- `supabase/migrations/0019_seller_public_summary.sql` -- `get_seller_public_summary`,
  SECURITY DEFINER, 함수 안 `status='on_sale'`이 **유일한 강제 지점**. 정지 판매자 축도 여기 걸린다.
  강제 장치: `api/tests/integration/test_seller_summary_real_db.py`.
- `pg_policies` 실측(2026-08-11 로컬 55322) -- `listings` SELECT 정책 4개:
  `listings_ai_readonly_select`(`{ai_readonly}`, `true`) · `listings_select_admin`(`is_admin()`) ·
  `listings_select_on_sale`(`status='on_sale'`) · `listings_select_on_sale_anon`(anon, `status='on_sale'`).
  `profiles` 정책 4개: select_self · select_admin · update_admin · delete_admin — **anon 정책 0건.**
- `api/app/db/sql_guard.py:77-202` -- `status='on_sale'` **부정 우회 차단** 구조 검사(sqlparse 토큰).
  **검증기이지 주입기가 아니다** — 조건을 대신 붙여 주지 않는다.
- `api/app/graph/doc_rag_node.py:108-115` -- 고정 SQL의 `WHERE status='on_sale' AND embedding IS NOT NULL`.
  sql_guard를 안 거치고 `ai_readonly` RLS도 `using(true)`라 **이 한 줄이 유일한 강제 지점**.
- `api/app/graph/hybrid_rag_node.py` -- 코드가 `WHERE status='on_sale'`을 템플릿으로 붙인다(13.3).
- `docs/conventions.md` §6 -- FR11 강제 지점 전량 목록. **이 스토리의 체크리스트이자 갱신 대상.**
  §6.1(사진 파일 URL 면제)과 혼동 금지 — 면제 대상은 파일 URL이지 `listing_images` 테이블 조회가 아니다.
- `docs/conventions.md` §8 -- *"정지는 열람이 아니라 쓰기 행동만 막는다"* — **이 문장이 정정 대상.**
- `web/src/lib/listings.ts`(`buyerListingsQuery` 계열) · `web/src/lib/wishlist.ts`
  (`isWishedListingBlocked`) -- 이미 RLS 차단 항목을 회색 타일로 흡수하는 기존 처리.
- `app/lib/features/listings/listings_repository.dart` -- `_buyerQuery`(`.eq('status','on_sale')`),
  `_fetchCovers`, `fetchPopularListings`. RLS가 DB에서 이중 방어하는 구조 — 코드 수정 대상이 아니다.
- `api/tests/integration/test_doc_rag_node_real_db.py` · `api/tests/test_hybrid_rag_node.py` ·
  `api/tests/test_listing_cards.py` · `api/tests/integration/test_seller_summary_real_db.py` --
  FR11 축의 기존 강제 장치. **전부 계속 green이어야 한다**(회귀 0) + 정지 축 검사가 옆에 붙는다.
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-804]](a 닫음) · [[DW-799]](재판정).

## Tasks & Acceptance

**Execution:**

- `supabase/migrations/0035_hide_suspended_seller_listings.sql` -- NEW. 한 파일에:
  1. `public.is_seller_active(p_seller_id uuid)` 신설 — SECURITY DEFINER · `set search_path=''` ·
     `stable` · `profiles.status = 'active'` 판정. `revoke all from public` 후 실제 소비 롤에만
     `grant execute`. **판매자 행이 없는 경우의 반환값을 정하고 근거를 적는다**(profiles 행이 없는
     매물이 실재할 수 있는지 먼저 실측 — 없다면 그 사실을 적고 방어 코드를 넣지 않는다, A2).
  2. `listings_select_on_sale` · `listings_select_on_sale_anon` drop→create — 기존 `status='on_sale'`에
     `and public.is_seller_active(seller_id)` 추가.
  3. (위 Always의 검토 결과에 따라) `listings_ai_readonly_select` drop→create —
     `using(true)` → `using(public.is_seller_active(seller_id))`. **AI 3경로를 한 자리에서 닫는다.**
     택하지 않았다면 그 근거를 각주와 Design Notes에 남기고 코드 3곳을 대신 고친다.
  4. `get_seller_public_summary` `create or replace` — 함수 안에 정지 판매자 판정 추가.
  5. (실측 결과 필요할 때만) `listing_images_select_on_sale` / `_anon` 명시적 차단.
  각주에 §9.1이 요구하는 "왜"를 남긴다 — **특히 왜 SECURITY DEFINER 함수여야 하는지**(profiles RLS
  때문에 인라인 서브쿼리가 전부를 숨긴다는 Intent 1번의 실측).
- `docs/conventions.md` §6 -- "정지 판매자 비노출" 축을 FR11 목록과 같은 형식으로 등재
  (매물 축 / 이미지 축 / SECURITY DEFINER 축 + 각 강제 장치 테스트 파일명).
- `docs/conventions.md` §8 -- *"정지는 쓰기 행동만 막는다"* 를 **정정**한다. 17.1 원문을 지우지 말고
  ✎ 표기로 "2026-08-11 사용자 결정으로 조회도 좁혔다(17.4) — 단 본인·관리자 조회는 그대로" 를 붙인다.
- `api/tests/integration/test_suspended_seller_hidden_real_db.py` -- NEW. 5주체(anon · 로그인 구매자 ·
  판매자 본인 · 관리자 · `ai_readonly`) × (정지 판매자 매물 / 활성 판매자 매물) 격자를 **전부** 검사한다.
  17.1의 `_as()`·`_create_user`·`_insert_listing`·`_suspend` 헬퍼 재사용.
  파일 헤더에 "이 검사가 안 보는 것"을 실측해서 적는다.
- `api/tests/integration/…` (문서 RAG·하이브리드·판매자 요약 축) -- 기존 실DB 검사에 정지 판매자
  케이스를 **추가**한다(새 파일 만들지 않는다 — 같은 관심사).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- [[DW-804]](a) 닫음, [[DW-799]] 재판정.

**Acceptance Criteria:**

- Given 정지된 판매자의 `on_sale` 매물, when **비로그인(anon)** 이 목록·검색·상세를 조회, then 그
  매물이 **나오지 않는다**.
- Given 같은 매물, when **로그인한 다른 구매자**가 조회, then 나오지 않는다.
- **(긍정 대조군 ①·② — 없으면 "전부 사라짐"이 green이다)** Given **활성** 판매자의 `on_sale` 매물,
  when 비로그인이 조회 / 로그인 구매자가 조회, then **정상적으로 보인다**.
- **(긍정 대조군 ③ — 건수로 고정)** Given 활성 판매자 N명의 매물이 있는 상태에서 그중 1명을 정지,
  when 비로그인 목록 조회, then 건수가 **정확히 그 1명의 매물 수만큼만** 줄어든다(0이 되지 않는다).
- Given 정지된 판매자 **본인** 세션, when 자기 매물을 조회(`/sell` 경로), then **그대로 보인다**.
- Given **관리자**(활성·정지 무관) 세션, when 정지 판매자의 매물을 조회, then **그대로 보인다**
  (17.1의 `test_suspended_admin_can_still_read_via_admin_select_policies` 회귀 0).
- Given `set local role ai_readonly`, when 정지 판매자 매물을 조회, then **나오지 않는다**
  (AI 3경로가 이 한 자리에서 닫히는 설계를 택한 경우). 코드 3곳을 고치는 설계를 택했다면
  경로 A·B·하이브리드 **각각**에 대해 같은 단언을 둔다.
- **(AI 긍정 대조군)** Given `ai_readonly`, when 활성 판매자 `on_sale` 매물을 조회, then 보인다.
- Given 정지된 판매자의 매물, when `get_seller_public_summary`를 anon으로 호출, then 그 매물이
  집계에 포함되지 않는다.
- Given 정지된 판매자의 매물 사진, when 비로그인·구매자가 `listing_images`를 조회, then 0행
  (자동 cascade든 명시 차단이든 **결과가 0행이어야 한다** — 어느 쪽이었는지 Design Notes에 기록).
- **(정지 해제 복구 — 숨김이 조회 시점 판정임을 고정)** Given 정지된 판매자, when `status`를
  `'active'`로 되돌린다, then 그 매물이 **아무 추가 조치 없이 다시 보인다.**
- **(FR11 회귀 0)** Given `status='sold'` 매물과 활성 판매자, when 모든 조회 경로(목록·필터·상세·
  AI SQL·문서 RAG·하이브리드), then 기존과 동일하게 노출되지 않는다.
- **(찜·채팅 회귀)** Given 구매자가 찜해 둔 매물의 판매자가 정지됨, when `/wishlist` 조회, then
  화면이 **오류 없이** 렌더된다(회색 타일 등 기존 차단 처리로 흡수). 진행 중 채팅방도 동일.
- **(red 증명 ⓐ)** Given 정책에서 `is_seller_active(seller_id)` 조건을 제거한 판, when 검사 실행,
  then **"정지 판매자 매물이 안 보인다"** 단언이 실패. 원복 후 green.
- **(red 증명 ⓑ — 표기를 바꿔서)** Given 판정 함수 본문을 `status='suspended'`를 요구하도록 뒤집은 판,
  when 검사 실행, then **긍정 대조군**(활성 판매자 매물이 보인다)이 실패. 서로 다른 단언이 red가
  되는 것까지 확인한다.
- Given 전체 실DB 통합검사 + api 단위검사 + web 검사, when 실행, then 전량 green(기존 회귀 0).
- Given `python scripts/check_migrations.py`, when 실행, then 게이트 통과.

## Design Notes

_(구현 세션이 채운다. 최소한 아래는 반드시 담긴다.)_

- **인라인 서브쿼리가 실제로 전부를 숨기는지 재본 결과** — Intent 1번은 정책 목록에서 유도한
  예측이다. **한 번은 실제로 그렇게 짜서 재보고**(전부 사라지는지) 그 결과를 적는다. 그래야 다음
  사람이 "정말 그런가?"를 다시 조사하지 않는다. (재본 뒤 SECURITY DEFINER 판으로 간다.)
- `listing_images` 축이 중첩 RLS로 **자동으로 따라왔는지** 실측 결과.
- `ai_readonly` 정책을 좁히는 선택을 했는지 / FR11 sold 축이 안 깨졌는지 실측 결과.
- `is_seller_active`에 GRANT를 준 롤 목록과, 빠뜨렸을 때 어떤 증상이 났는지(재현했다면).
- 앱(Flutter)이 코드 수정 없이 따라왔는지 실측 결과.
- red 증명 ⓐ·ⓑ의 실행 로그 요약.
- 이 검사가 **안 보는 것** 목록(실측 기반).

## Verification

- `cd api && pytest tests -q && pytest tests/integration -q` — 전량 green.
- `cd web && npm run test && npm run test:e2e` — 전량 green.
- `python scripts/check_migrations.py` — 게이트 통과.
- 로컬 실DB에서 **5주체 × 2매물** 격자를 직접 조회해 관찰(존재 확인이 아니라 작동 확인 — B4).
- 브라우저로 정지 처리 → 목록에서 사라짐 → 정지 해제 → 다시 나타남을 **눈으로** 확인하고
  스크린샷을 남긴다(원격 조종 키트 사용 시 Discord 보고).
