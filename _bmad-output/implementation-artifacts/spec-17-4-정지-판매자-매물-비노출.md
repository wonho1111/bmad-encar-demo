---
title: '17.4 정지된 판매자의 매물 비노출 (사용자 결정으로 에픽 불변식을 뒤집는 스토리)'
type: 'feature'
created: '2026-08-11'
status: 'done'
baseline_revision: '5f11c39' # 17.3 완료 커밋으로 갱신 — 계획 시점(2026-08-12) 실측이 17.2/17.3 반영 후 상태를 확인했음
final_revision: '8bc119a'  # 후속 리뷰 3회차 커밋. ✎ amend 대신 후속 커밋으로 적는다 — amend는 항상
                           # 새 해시를 만들어 적힌 값이 도달 불가 커밋이 된다(이전 값 886dbfe가 실제로
                           # 그랬다). 관례 자체의 수정은 [[DW-822]]가 들고 있다.
review_loop_iteration: 0
followup_review_recommended: true # 3회차: patch 5건(high 0, medium 1, low 4) — 3×1 + 1×4 = 7 ≥ 5
warnings: ['oversized']
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
- `docs/conventions.md` §8(`## 8. 접근 게이트 계약 (Access Gate Contract, FR58)`, line ~192) --
  2026-08-12 실측: 위 Intent 문단이 인용한 문장은 **지금 파일에 그 표기 그대로는 없다**(낡은 인용).
  line ~217의 실제 현재 문장 *"정지(`profiles.status='suspended'`)도 이 축의 '행동' 게이트다... 로그인·
  열람(매물 조회, 본인 profiles 조회 등)은 막지 않는다"* 가 **정정 대상**이고, 바로 다음 line ~218에
  17.3이 admin 콘솔 읽기용 예외(`requireRole`)를 이미 **명시적 예외**로 박아 뒀다(DB `is_admin()`
  SELECT 정책은 그대로, 클라이언트 게이트만 막음). **이 스토리는 그 옆에 두 번째 예외를 추가하는 게
  아니라 "열람은 안 막는다"는 원칙 자체를 매물 조회 축에 한해 뒤집는다** — ✎ 정정 문구는 admin 콘솔
  예외와 나란히 두되 범위가 다름을 분명히 적는다(admin 콘솔=한 화면의 클라이언트 게이트, 17.4=매물
  조회 전 경로의 DB 레벨 차단).
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
- `docs/conventions.md` §8 -- line ~217의 실제 현재 문장(위 Code Map 참고, *"로그인·열람은 막지
  않는다"* 취지)을 **정정**한다. 원문을 지우지 말고 ✎ 표기로 "2026-08-11 사용자 결정으로 매물
  조회도 좁혔다(17.4) — 단 본인·관리자 조회는 그대로, 다른 축(로그인·profiles 조회 등)은 원문대로"
  를 붙인다. line ~218의 17.3 admin 콘솔 예외 문단은 건드리지 않는다(범위가 다른 별개 예외).
- `api/tests/integration/test_suspended_seller_hidden_real_db.py` -- NEW. 5주체(anon · 로그인 구매자 ·
  판매자 본인 · 관리자 · `ai_readonly`) × (정지 판매자 매물 / 활성 판매자 매물) 격자를 **전부** 검사한다.
  17.1의 `_as()`·`_insert_listing()`·`_suspend()`·`_make_admin()`(`api/tests/integration/
  test_suspended_write_block_real_db.py`) + `_create_user()`(공용, `api/tests/integration/conftest.py`)
  헬퍼 재사용(2026-08-12 실측: `_create_user`는 17.1 파일이 아니라 conftest 공용 픽스처에 있다).
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

## Review Triage Log

### 2026-08-12 — Review pass

- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 3, low 2)
- defer: 0
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` `get_seller_public_summary`가 정지된 판매자 **본인**·**관리자**가 자기(또는
    관리 대상) 매물 상세를 볼 때도 `other_on_sale_count`를 무조건 0으로 돌린다 — 다른 매물이 실제로
    있어도 그렇다. Always 절("판매자 본인과 관리자에게는 그대로 보인다")의 취지를 이 요약 위젯이
    깬다. `is_seller_active(p_seller_id) or auth.uid()=p_seller_id or is_admin()` 조건으로 고침.
  - `[medium]` `[patch]` `chat_rooms`/`chat_room_reads` 화면이 정지 판매자 매물을 null embed로
    받는 새 경로(FR11의 sold null-embed와 같은 메커니즘)가 이 스토리로 처음 생겼는데, 그 렌더
    경로를 지키는 자동 검사가 없었다(AC "찜·채팅 회귀"가 요구). 회귀 테스트를 추가.
  - `[medium]` `[patch]` 스펙 자신이 요구한 Design Notes 6개 항목(인라인 서브쿼리 재현 결과 ·
    `listing_images` 자동상속 실측 · `ai_readonly`/FR11 무회귀 실측 · GRANT 롤 목록 · Flutter
    무수정 실측 · red 증명 ⓐⓑ 로그 요약 · "이 검사가 안 보는 것")가 비어 있었다 — 구현 세션이
    실측은 했지만(마이그레이션 헤더·테스트 docstring·대화 보고에 흩어져 있음) 스펙 본문에 옮기지
    않았다. 이미 확보된 실측 결과를 Design Notes에 채워 넣음.
  - `[low]` `[patch]` `test_suspended_seller_listings_excluded_from_count`가 `joined_at`을
    받아 놓고 단언하지 않는다 — 마이그레이션 주석의 "가입일은 계속 반환돼야 한다" 약속이 검사로
    안 잠겨 있었다. 단언 추가.
  - `[low]` `[patch]` `docs/conventions.md` §6.2가 "찜 축은 기존 sold 처리 메커니즘이 그대로
    재사용된다"고 단정했는데, 정작 이를 확인한 테스트 파일 자신은 "SQL 시뮬레이션으로만
    확인했다"고 그 한계를 적어 뒀다 — 계약 문서 문구가 검증 수준을 과장. 문서 문구에 그 한계를
    반영.

### 2026-08-12 — Review pass (후속 2회차)

- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 1, medium 2, low 5)
- defer: 5 (high 0, medium 1, low 4)
- reject: 10
- addressed_findings:
  - `[high]` `[patch]` **`public.is_seller_active(uuid)`가 anon에게 정지 여부 oracle이 됐다.** PostgREST는
    `public` 스키마 함수를 `/rest/v1/rpc/`로 자동 노출하는데(`supabase/config.toml:13`), 이 함수는 **남의
    uuid**를 인자로 받아 `profiles.status`를 되돌려준다. 2026-08-12 로컬 실측: anon 키만으로 RPC 호출 →
    `true`, 그 계정을 `suspended`로 바꾸면 → `false`, 되돌리면 → `true`. **대조군**: 같은 키로 `profiles`를
    직접 조회하면 `[]`(RLS가 정상 차단), 형제 함수 `is_admin`은 `42501`(무인자 + `authenticated` 전용이라
    같은 문제가 없다). 즉 0035 주석의 *"is_admin()·is_admin_active()와 동일하게 회수한다"* 는 판단이
    틀렸고, 스펙 Never 절(*"남의 회원 정보를 열어 주지 않는다"*)이 금지한 노출을 다른 문으로 만들었다.
    → `0036_is_seller_active_private_schema.sql` 신설: 함수를 노출 목록 밖 `private` 스키마로 옮기고
    정책 3개·`get_seller_public_summary`의 참조를 갱신, `public` 판을 drop. 17.2가 만든 정의자 함수
    전수조사(`test_write_policy_manifest_real_db.py`)가 스키마 이동으로 눈이 머는 것을 막으려
    census 범위를 `public` → `public,private`로 넓혔다.
  - `[medium]` `[patch]` `/wishlist`의 회색 타일이 정지 판매자 매물을 **"판매완료"** 로 단정했다 —
    팔린 게 아닌데 팔렸다고 말한다. 임베드 null의 원인이 0035로 두 개(sold / 판매자 정지)가 됐는데
    채팅 축만 1회차 패치에서 헤지 문구를 받고 찜 축이 빠졌다(AC "찜·채팅 회귀"는 둘 다 요구). null
    분기만 헤지 문구·`조회 불가` 배지로 바꾸고(임베드가 있는 본인 sold 분기는 그대로), 순수 함수로
    빼내 단위검사로 고정.
  - `[medium]` `[patch]` `readonly.py:14`·`doc_rag_node.py:109`·`sql_guard.py:305`가 아직 *"ai_readonly
    정책은 using(true)"* 라고 단언한다 — 0035가 그걸 뒤집었다. 특히 `readonly.py`의 주석은 하이브리드
    실DB 검사를 생략한 근거로 Design Notes가 인용한 자리라 계약처럼 읽힌다. 세 주석 정정(동작 무변경).
  - `[low]` `[patch]` 새 테스트 파일 헤더가 `listing_images_objects_read`의 *"자동 상속될 것으로 예상"* 을
    범위 제외의 근거로 들었는데, 그 정책은 `0014`가 이미 drop했고 버킷이 공개라 **RLS를 아예 안 탄다**.
    제외 결론은 유지하되 근거를 0014·§6.1 사실로 정정.
  - `[low]` `[patch]` `_LISTING_COLS` 미사용 상수 삭제(이 변경이 만든 고아 — A3).
  - `[low]` `[patch]` `get_seller_public_summary`의 새 carve-out에 **인증된 제3자(비관리자) 음성 케이스**가
    없었다 — `auth.uid() = p_seller_id`를 `auth.uid() is not null`로 넓혀도 전 검사가 green이었다. 케이스 추가.
  - `[low]` `[patch]` 건수 대조군이 n=1이라 AC가 요구한 *"정확히 그 1명의 매물 수만큼"* 과 *"1행만큼"* 을
    구별하지 못했다. 2건 보유 판매자를 정지시키는 케이스를 추가하고 이름으로 무엇을 고정하는지 분리.
  - `[low]` `[patch]` `chat.test.ts`의 두 "트리거" 테스트가 입력·기대 모두 동일(둘 다 `null`)이라 검사
    수만 늘고 잡는 회귀는 그대로였다. 하나로 합치고 이유를 헤더에 남김.

### 2026-08-12 — Review pass (후속 3회차)

- intent_gap: 0
- bad_spec: 0
- patch: 5 (high 0, medium 1, low 4)
- defer: 5 (high 0, medium 2, low 3)
- reject: 8 (high 0, medium 0, low 8)
- addressed_findings:
  - `[medium]` `[patch]` **`private.is_seller_active`가 PARALLEL UNSAFE라 anon 매물 조회가 병렬
    플랜을 통째로 잃었다.** `create function`에 `parallel` 절이 없으면 Postgres 기본값이
    PARALLEL UNSAFE인데, 이 함수는 `listings` SELECT 정책 3개의 `using` 절에 들어간다. 실측
    (로컬 55322, 트랜잭션+rollback, 병렬 비용 GUC 0): 현재 판 anon 플랜 → `Seq Scan`, 정책 없는
    슈퍼유저 대조군 → `Gather/Workers Planned: 2`. ⓐ 함수 조건을 빼 17.4 이전 형태로 되돌리면
    → `Gather` 복구(17.4가 만든 회귀임이 증명), ⓑ 조건은 두고 `parallel safe`만 주면 →
    `Gather` 복구(한 단어가 원인). `0036`을 in-place 수정(런북 4항 — 코드리뷰 지적은 새 번호를
    만들지 않는다, 원격 미적용)하고 `proparallel='s'` 회귀 가드를 심었다.
  - `[low]` `[patch]` 정의자 함수 전수조사가 스코프를 `public`+`private`로 넓히면서 반환 키는
    `proname` 하나뿐이라, 두 스키마에 같은 이름이 생기면 뒤 행이 앞 행을 **조용히 덮어쓴다**
    (차집합 검사가 초록으로 통과하고, 술어 검사는 엉뚱한 스키마 판의 oid를 검사한다). 매니페스트
    키 형식은 그대로 두고(20여 항목 보존, A2) 딕셔너리로 접기 전에 중복 0건 단언을 넣었다.
  - `[low]` `[patch]` 사진 축에 불변식 **후반부**(본인·관리자에게는 그대로 보인다) 검사가 없었다
    — `listings` 축은 고정했는데 `listing_images`는 "숨김"만 고정했다. 실측 결과 동작은 이미
    옳았고(정지 후에도 본인·관리자에게 매물 1행·사진 1행) **검사만 없었다.** 두 케이스 추가.
  - `[low]` `[patch]` GRANT 가드가 `has_function_privilege`만 봤다 — `0036`은 "스키마 USAGE +
    함수 EXECUTE 둘 다 있어야 하고 하나라도 빠지면 42501"이라고 적었는데 USAGE 축은 안 봤다.
    세 롤에 `has_schema_privilege(..., 'private', 'usage')` 단언 추가.
  - `[low]` `[patch]` 건수 대조군이 `listings` **전역** 카운트라 자기 시드 밖 행에 의존했다
    (`after > 0`이 남의 행 덕에 통과할 수 있고, READ COMMITTED에서 다른 세션 커밋이 사이에
    보인다). `_on_sale_count`에 선택적 판매자 범위를 넣고 두 건수 테스트를 자기 시드로 좁혔다.

## Design Notes

- **인라인 서브쿼리가 실제로 전부를 숨기는지 재본 결과** — 재현 확정. 2026-08-12 로컬 55322에서
  트랜잭션+rollback으로 활성 판매자의 on_sale 매물 1건을 심고 `listings_select_on_sale_anon`을
  `status='on_sale' and exists (select 1 from public.profiles where id=listings.seller_id and
  status='active')`(인라인 서브쿼리)로 임시 교체한 뒤 `set local role anon; select count(*) from
  listings where status='on_sale'`을 실행 — 결과 **0건**(활성 판매자의 매물인데도 안 보임, 예측
  그대로 재현). 그 뒤 SECURITY DEFINER 함수(`is_seller_active`)로 교체하고 같은 조회를 실행하면
  정상적으로 1건 이상 보임을 확인한 뒤 그 판으로 확정했다(`0035` 파일 헤더에도 같은 요약이 있다).
- **`listing_images` 축의 자동 상속 실측 결과** — 자동으로 따라왔다(별도 정책 추가 없음). 같은
  트랜잭션+rollback 프로브에서 정지 판매자의 매물 사진 1건 + 활성 판매자의 매물 사진 1건을 심고
  anon·로그인 구매자(비소유자) 양쪽으로 `listing_images`를 조회 — 정지 판매자 사진은 0행, 활성
  판매자 사진은 정상 노출. `listing_images_select_on_sale`/`_anon`(0012)이 `exists (select 1 from
  listings l where l.id=listing_images.listing_id and l.status='on_sale')`로 `listings`에 조인하는데,
  이 서브쿼리도 호출자 권한으로 평가되므로 위 2절이 `listings` SELECT를 좁힌 순간 같은 좁아진
  `listings`를 보게 된다 — 이 성질 때문에 자동 상속이 성립한다.
- **`ai_readonly` 좁히기가 FR11(sold) 축을 깨지 않았는지 실측 결과** — 안 깨졌다. `set local role
  ai_readonly`로 `status='sold'`인 매물(판매자는 활성)을 조회하면 여전히 보인다 — RLS는 판매자
  활성 여부만 추가로 보고, sold 필터는 원래대로 코드(`doc_rag_node.py`·`hybrid_rag_node.py`·
  `sql_guard.py`의 `WHERE status='on_sale'`)가 전담한다(0006 CR2 설계 유지). 이 회귀는
  `api/tests/integration/test_suspended_seller_hidden_real_db.py::test_ai_readonly_still_sees_sold_listing_from_active_seller_fr11_regression`
  와 `test_doc_rag_node_real_db.py`의 기존 sold 케이스(`test_sold_listing_never_reaches_doc_rag_semantic_search_on_real_postgres`)
  가 함께 고정한다. 하이브리드 경로(`hybrid_rag_node`)는 실제 Gemini 호출이 필요해 real-db 함수
  호출 테스트를 새로 만들지 않았다 — doc_rag_node와 동일한 `ai_readonly` 커넥션 풀(`app/db/
  readonly.py`)·동일 RLS를 공유한다는 사실(코드 확인)로 커버리지를 대신한다(`test_doc_rag_node_real_db.py`
  헤더에 근거를 남겼다).
- **`is_seller_active`에 GRANT를 준 롤** — `anon`·`authenticated`·`ai_readonly` 셋(0035 1절
  `grant execute on function public.is_seller_active(uuid) to anon, authenticated, ai_readonly`).
  GRANT를 빠뜨렸을 때의 증상은 이번엔 실제로 재현하지 않았다(0035 최초 작성부터 세 롤 모두에
  GRANT를 넣고 시작해 "빠뜨린 판"을 따로 만들지 않았다) — 스펙 Boundaries 절이 경고하는 증상
  (42501로 조회 전체가 죽음)은 17.1·17.2의 같은 패턴(`is_admin_active()`·
  `increment_listing_view`)에서 이미 실측된 것과 동일할 것으로 추정하며, 별도 재현은 생략했다.
- **앱(Flutter)이 코드 수정 없이 따라왔는지** — **코드 읽기로만 확인, 런타임 실행은 안 했다**
  (정직하게 구분한다 — B4 "재보기 전엔 선언하지 않는다"). `app/lib/features/listings/
  listings_repository.dart`의 `_buyerQuery`가 `.eq('status','on_sale')` 필터 + 앱의 anon/
  authenticated Supabase 세션(= RLS 경유)로만 구성돼 있고 판매자 상태를 따로 걸러내는 클라이언트
  코드가 없음을 코드 리딩으로 확인했다 — 그래서 DB에서 막으면 자동으로 따라오는 구조라는 판단은
  섰지만, 실제로 Flutter 앱을 빌드해 화면에서 눈으로 확인하지는 않았다(환경 시간 제약). 코드는
  건드리지 않았다(Never 절 준수) — 남은 검증은 다음 세션의 몫으로 남긴다.
- **red 증명 ⓐ·ⓑ 실행 로그 요약** — 둘 다 로컬 55322에서 수동 트랜잭션+rollback 프로브로
  실행했다(CI에 상시 도는 자동 정책-뒤집기 테스트로는 안 남겼다 — 17.1의
  `test_suspended_write_block_real_db.py`도 같은 이유로 이 패턴을 피한다: 공유 DB에서 정책을
  실시간으로 뒤집는 것 자체가 위험하다는 판단).
  - ⓐ (정책 조건 제거) `listings_select_on_sale_anon`을 `status='on_sale'`만 남기고
    `is_seller_active` 조건을 뺀 뒤, 정지 판매자의 on_sale 매물을 anon으로 조회 → **결과 t**(보임,
    "안 보인다" 단언이 실패 = red 확인). 원복 후 재조회 → f(안 보임, green 재확인).
  - ⓑ (함수 본문 반전) `is_seller_active` 본문의 `status='active'`를 `status='suspended'`로
    뒤집은 뒤, **활성** 판매자의 on_sale 매물을 anon으로 조회 → **결과 f**(안 보임, 긍정 대조군
    "보인다" 단언이 실패 = red 확인, 앞서 ⓐ와 다른 단언이 깨짐을 확인). 원복 후 재조회 → t(보임,
    green 재확인).
- **이 검사가 안 보는 것** (`test_suspended_seller_hidden_real_db.py` 헤더 docstring 요약, 전문은
  그 파일 참조):
  - red 증명 ⓐⓑ는 CI에 상시 도는 자동화 테스트가 아니라 위처럼 수동 프로브로만 검증됐다(이유는
    위 항목 참조).
  - `chat_rooms` 방 생성 진입점은 이 스토리가 안 닫는다 — `enforce_chat_room_seller()`(0016)가
    SECURITY DEFINER라 listings RLS를 우회해 seller_id를 조회하므로, listing_id를 이미 아는
    구매자는 API를 직접 호출해 여전히 방을 만들 수 있다(브라우저 정상 흐름의 진입점만 닫힘,
    [[DW-799]]가 재판정을 들고 열려 있다).
  - `/wishlist` 회색 타일 흡수는 raw SQL로 PostgREST의 null-embed 동작을 시뮬레이션해서만
    확인했다(`wishlists LEFT JOIN listings` 형태로 재현, 에러 없이 NULL 확인) — 실제 PostgREST
    HTTP 응답이나 `/wishlist` 화면 렌더까지는 이 스토리가 검증하지 않는다(`web/src/lib/
    __tests__/wishlist.test.ts`의 `isWishedListingBlocked(null) === true`가 sold 축으로 이미
    있고, 정지 축도 같은 null 입력이라 같은 단언이 적용된다 — 별도 케이스를 안 만든 이유이며
    코드리뷰 patch 이후 `docs/conventions.md` §6.2도 이 한계를 반영하도록 문구를 낮췄다).
  - `/chat` 화면의 null-embed 흡수는 코드리뷰 patch로 `web/src/lib/chat.ts`의
    `chatListingSummary` 순수 함수를 추출해 sold 트리거와 정지-판매자 트리거 둘 다 같은 폴백
    문구를 낸다는 것을 단위테스트로 고정했다(`web/src/lib/__tests__/chat.test.ts`) — 다만 이것도
    "함수가 null을 받으면 안전하다"까지만 보고, 실제 PostgREST가 이 트리거로 null을 돌려주는지는
    앞 항목과 같은 raw SQL 시뮬레이션 수준이다(HTTP·실제 화면 렌더 e2e는 여전히 미검증).
  - ✎ **2026-08-12 후속 리뷰 정정 — 판정 함수는 이제 `private.is_seller_active`다.** 위 항목들이
    `public.is_seller_active`로 적은 자리는 전부 `private` 스키마 판을 가리킨다(`0036`). 이유는
    실측이다: `public` 스키마 함수는 PostgREST가 `/rest/v1/rpc/`로 자동 노출하는데, 이 함수는 남의
    uuid를 받아 `profiles.status`를 되돌려주므로 anon 키만으로 임의 계정의 정지 여부를 알 수 있었다
    (true → 정지 처리 → false → 해제 → true로 재현). 같은 키의 `profiles` 직접 조회는 `[]`,
    `is_admin` RPC는 `42501`이라 **이 함수만 예외였다.** 위 "GRANT를 준 롤" 항목이 *"17.1·17.2의 같은
    패턴과 동일할 것으로 추정"* 하고 재현을 생략했던 바로 그 자리에서, 실제로는 **패턴이 달랐다**
    (`is_admin()`·`is_admin_active()`는 무인자 + `authenticated` 전용이라 노출돼도 남의 정보를 안 준다).
    0036 적용 후 재측정: anon RPC → `PGRST202`(경로 소멸), `Accept-Profile: private` → 404,
    **긍정 대조군** anon 매물 읽기 → 200 + 1행(읽기 경로 무손상).
  - ✎ **2026-08-12 후속 리뷰 — 불변식을 HTTP 표면에서 다시 쟀다(건수 대조군 n=54).** 로컬 스택에서
    on_sale 매물 54건을 가진 판매자를 정지 → anon `/rest/v1/listings?status=eq.on_sale` 건수
    **158 → 104**(정확히 −54, 0이 아님) → 해제 → **158 복구**. 스펙 AC의 "정확히 그 판매자의 매물
    수만큼만 줄어든다"를 SQL이 아니라 실제 REST 응답에서 확인한 결과다.
  - ✎ **2026-08-12 후속 리뷰 — 새 가드의 red를 실제로 증명했다.** 일회용 pgvector 컨테이너에
    마이그레이션 전량을 적용한 뒤 `public.is_seller_active`를 일부러 되살리고(= 노출 재현)
    `pytest tests/integration` 실행 → `test_public_is_seller_active_removed_private_version_exists_with_grants`
    **1건 red**(나머지 197 green). 프로브 함수를 drop하고 재실행 → **198 green**. 컨테이너 삭제 확인.
  - ✎ **2026-08-12 후속 리뷰 — 아래 "이 검사가 안 보는 것" 목록에 두 항목이 빠져 있었고, 둘 다
    실측으로 재현해 대장에 열었다**: `increment_listing_view`(정의자 함수라 숨겨진 매물의 조회수를
    anon이 계속 올린다 — 가시성 0행인데 view_count 0→1, [[DW-819]])와 **기존 채팅방**(구매자는
    계속 보낼 수 있고 판매자는 RLS로 막혀 영영 못 답한다 — DW-804(a)가 적은 증상 그대로, [[DW-820]]).
  - ✎ **2026-08-12 후속 리뷰 3회차 — 이 설계의 성능 축을 처음 쟀고, 회귀가 하나 있었다.**
    판정 함수가 `parallel` 절 없이 만들어져 PARALLEL UNSAFE였고, 그 함수가 `listings` SELECT
    정책 3개의 `using` 절에 들어가면서 **`listings`를 읽는 모든 쿼리가 병렬 플랜을 못 받게 됐다.**
    EXPLAIN 실측으로 ⓐ(함수 조건 제거 → `Gather` 복구 = 17.4가 만든 회귀) · ⓑ(`parallel safe`만
    추가 → `Gather` 복구 = 한 단어가 원인)를 확인하고 `0036`을 in-place 수정했다. 남은 성능 축
    (정의자 함수라 인라인 불가 · pgvector recall)은 여전히 미측정이며 [[DW-821]]이 들고 있다.
  - ✎ **2026-08-12 후속 리뷰 3회차 — 사진 축의 carve-out은 검사가 아니라 실측으로만 서 있었다.**
    정지 후에도 본인·관리자에게 매물·사진이 그대로 보이는 것은 동작상 옳았지만 이 파일의 검사가
    그 절반을 고정하지 않고 있었다(숨김 축만 고정). 두 케이스를 추가해 닫았다.
  - ✎ **2026-08-12 후속 리뷰 3회차 — `private` 차단의 성립 조건은 아직 로컬에서만 참이다.**
    `private` 스키마가 PostgREST에 안 올라간다는 근거로 `supabase/config.toml`을 인용했는데 그
    파일은 **로컬 스택 전용**이고, 런북은 원격 적용이 Supabase MCP라고 못박는다. 원격의 Data API
    노출 스키마 목록은 이 리포가 읽지도 검사하지도 않는다 — [[DW-824]]가 들고 있다(원격 적용의
    선행 조건).
  - `listing_images_objects_read`(storage.objects 파일 자체 열람)는 검증하지 않는다 — §6.1(사진
    파일 URL은 FR11 대상이 아니다)과 같은 이유로 이 스토리 범위를 매물·사진 **행** 조회로
    한정했다(파일 URL 접근은 별도 축).

## Verification

- `cd api && pytest tests -q && pytest tests/integration -q` — 전량 green.
- `cd web && npm run test && npm run test:e2e` — 전량 green.
- `python scripts/check_migrations.py` — 게이트 통과.
- 로컬 실DB에서 **5주체 × 2매물** 격자를 직접 조회해 관찰(존재 확인이 아니라 작동 확인 — B4).
- 브라우저로 정지 처리 → 목록에서 사라짐 → 정지 해제 → 다시 나타남을 **눈으로** 확인하고
  스크린샷을 남긴다(원격 조종 키트 사용 시 Discord 보고).

## Auto Run Result

Status: done

**구현 요약**: `profiles.status='suspended'`인 판매자의 `on_sale` 매물을 구매자·비로그인·AI 3경로
(sql_guard 검증 LLM SQL·doc_rag_node 고정 SQL·hybrid_rag_node) 어디서도 노출되지 않게 숨겼다.
판정은 SECURITY DEFINER 함수 `public.is_seller_active(uuid)` 하나로 모았다(`profiles` RLS를
우회해야 하는 이유 — Intent 1번 실측으로 확정). 본인·관리자 조회는 그대로 두었고, 숨김은 저장이
아니라 조회 시점 판정이라 정지 해제 시 자동 복구된다. `listing_images`는 중첩 RLS로 자동 상속됨을
실측 확인. `docs/conventions.md` §6.2 신설·§8 정정, DW-804(a) 닫음, DW-799 재판정(API 직접 호출로
채팅방 생성은 여전히 열려 있음을 확인하고 열어 둠).

**파일 변경 (12개, 최초 구현 8개 + 리뷰 패치 4개):**
- `supabase/migrations/0035_hide_suspended_seller_listings.sql` — NEW. `is_seller_active` 함수 +
  `listings_select_on_sale`/`_anon`/`listings_ai_readonly_select`/`get_seller_public_summary` 개정.
- `api/tests/integration/test_suspended_seller_hidden_real_db.py` — NEW. 5주체×2매물 격자 15건.
- `api/tests/integration/test_doc_rag_node_real_db.py` — 정지 판매자 케이스 + 긍정 대조군 추가.
- `api/tests/integration/test_seller_summary_real_db.py` — 정지 판매자 집계 제외 + 본인/관리자
  예외 케이스(리뷰 패치) 추가.
- `api/tests/integration/test_write_policy_manifest_real_db.py` — `is_seller_active`를 읽기
  전용(exempt)으로 등재(연쇄 수정, 안 하면 기존 전수조사 검사가 red).
- `docs/conventions.md` — §6.2 신설(정지 판매자 비노출 축) + §8 ✎ 정정 + 리뷰 패치로 찜 축 문구의
  검증 수준을 정확히 낮춤.
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-804(a) 닫음, DW-799 재판정.
- `web/src/lib/chat.ts` — NEW(리뷰 패치). `chatListingSummary` 순수 함수로 null-embed 폴백 로직을
  한 곳에 모음(기존 sold 폴백 동작·문구는 그대로).
- `web/src/app/(user)/chat/page.tsx`, `web/src/app/(user)/chat/[roomId]/page.tsx` — 리뷰 패치.
  위 함수를 쓰도록 교체(중복 삼항연산자 제거).
- `web/src/lib/__tests__/chat.test.ts` — 리뷰 패치. sold·정지-판매자 두 트리거 각각의 null-embed
  폴백을 이름 붙여 회귀 고정.

**리뷰 결과**: 4개 렌즈(blind-hunter/adversarial · edge-case-hunter · verification-gap ·
intent-alignment) 병렬 실행, 총 12건 발견 → intent_gap 0 · bad_spec 0 · patch 5(high 0, medium 3,
low 2) · defer 0 · reject 8. reject된 8건은 대부분 이미 이 스토리가 의도적으로 남긴 것(DW-799
잔여 경로 등)이거나 다른 검토로 반증된 것(카운트 검사 병렬경합 우려 — CI가 순차 실행임을 실측
확인)이었다. 상세는 `## Review Triage Log` 참고. 5건 패치는 구현 세션에 재위임해 전부 적용·재검증
그린으로 마쳤다.

**검증**: `cd api && pytest tests -q`(685 passed, 8 skipped) + `pytest tests/integration -q`
(195 passed) + `python scripts/check_migrations.py`(정적+동적 게이트 통과) + `cd web && npm run
test`(375 passed) + `npm run test:e2e`(82 passed, 122 skipped, 0 failed) — 전부 이 세션이 **패치
적용 전·후 두 번** 독립적으로 재실행해 직접 확인했다(1회성 pgvector 컨테이너 2개, 매번 처음부터
마이그레이션 전량 재적용). 브라우저(Playwright MCP) 실측: 정지 처리 → `/search`·`/listings/[id]`
에서 사라짐(404) → 정지 해제 → 재노출, 스크린샷 확인 후 throwaway 데이터 정리.

**잔존 위험**:
- DW-799: 정지 판매자 매물의 `listing_id`를 이미 아는 구매자는 API 직접 호출로 여전히 채팅방을
  생성할 수 있다(`enforce_chat_room_seller()`가 SECURITY DEFINER라 RLS 우회). 브라우저 정상 흐름의
  진입점(상세페이지 → 문의하기)은 닫혔다. 대장에 열어 둠, 다음 채팅 쓰기 스토리가 판단.
- `hybrid_rag_node.py`는 실제 Gemini 호출이 필요해 through-code 실DB 검사가 없다 — 같은
  `ai_readonly` RLS를 공유한다는 사실과 그 RLS 자체의 격자 검사로 커버리지를 대체(기존
  `test_hybrid_rag_node.py`도 전부 모킹인 것과 같은 이유).
- red 증명 ⓐⓑ는 CI에 상시 도는 자동 정책-뒤집기 테스트가 아니라 수동 트랜잭션+rollback 프로브로만
  확인(17.1과 동일 관례 — 공유 DB에서 정책을 실시간 뒤집는 위험을 피함).
- `/wishlist`·채팅방 화면의 null-embed 흡수는 raw SQL 시뮬레이션 + 단위테스트 수준까지 확인했고,
  실제 PostgREST HTTP 응답·화면 렌더 e2e까지는 검증하지 않았다(리뷰로 문서에 이 한계를 명시).
- `oversized` 경고: 이 스펙 파일 자체가 900–1600 토큰 목표를 크게 넘는다(사용자가 사전에 상세하게
  작성한 백로그 스펙을 그대로 승계했기 때문). 다음에 이 스펙을 참고 문서로 쓸 세션은 전체를 로드하지
  말고 필요한 절만 찾아 읽을 것.

---

## Auto Run Result — 후속 리뷰 2회차 (2026-08-12)

Status: done

**무엇을 했나**: 1회차와 무관한 새 세션에서 4개 렌즈(adversarial · edge-case-hunter · verification-gap ·
intent-alignment)를 병렬로 다시 돌려 총 23건을 받았고, 보고를 그대로 믿지 않고 **핵심 주장마다 직접
재현**한 뒤 8건 패치 · 5건 이월 · 10건 기각으로 분류했다.

**가장 중요한 발견 — 이 스토리가 스스로 금지한 노출을 다른 문으로 만들었다.**
17.4는 판매자의 정지 여부를 판정하려고 `public.is_seller_active(uuid)`라는 SECURITY DEFINER 함수를
만들었다. 그런데 Supabase는 `public` 스키마의 함수를 자동으로 웹 API(`/rest/v1/rpc/`)에 올린다 —
그래서 **로그인하지 않은 사람도 아무 계정의 uuid만 알면 그 계정이 정지됐는지 물어볼 수 있었다.**
직접 확인했다: anon 키로 호출 → `true`, 그 계정을 정지시키고 다시 호출 → `false`, 되돌리면 → `true`.
같은 키로 회원 테이블을 직접 조회하면 `[]`(정상 차단)이고 형제 함수 `is_admin`은 `42501`(거부)이라,
**새로 만든 이 함수 하나만 뚫려 있었다.** 스펙 Never 절이 *"남의 회원 정보를 열어 주지 않는다"* 고
못박은 바로 그 노출이다. → 함수를 웹에 안 올라가는 `private` 스키마로 옮기고(`0036`), 정책과
`get_seller_public_summary`의 참조를 갈아 끼운 뒤 `public` 판을 지웠다. 옮기면 17.2가 만든 "정의자
함수 전수조사"의 시야에서 사라지므로, 그 조사 범위도 `public,private`로 함께 넓혔다.

**파일 변경 (14개):**
- `supabase/migrations/0036_is_seller_active_private_schema.sql` — NEW. 판정 함수를 `private`로 이전,
  정책 3개 + `get_seller_public_summary` 참조 갱신, `public` 판 drop.
- `api/tests/integration/test_write_policy_manifest_real_db.py` — 정의자 함수 전수조사 범위를
  `public` → `public,private`로 확장(안 하면 이전과 동시에 그물에 구멍).
- `api/tests/integration/test_suspended_seller_hidden_real_db.py` — `public` 판 부재 + `private` 판 존재
  + 3개 롤 GRANT 회귀 검사 추가, 헤더의 `listing_images_objects_read` 근거 정정, 죽은 상수 삭제,
  건수 대조군을 n=2로 보강.
- `api/tests/integration/test_seller_summary_real_db.py` — 인증된 제3자(비관리자) 음성 케이스 추가.
- `api/app/db/readonly.py` · `api/app/db/sql_guard.py` · `api/app/graph/doc_rag_node.py` — `ai_readonly`
  정책이 `using(true)`라는 낡은 주석 3곳 정정(동작 무변경).
- `web/src/lib/wishlist.ts` · `web/src/app/(user)/wishlist/page.tsx` · `web/src/lib/__tests__/wishlist.test.ts`
  — 찜 회색 타일의 null 분기 문구를 헤지("판매 완료되었거나 조회할 수 없는 매물" · `조회 불가` 배지)로
  바꾸고 순수 함수로 빼내 두 트리거를 이름 붙여 고정.
- `web/src/lib/__tests__/chat.test.ts` — 입력·기대가 같던 중복 트리거 테스트를 하나로 통합.
- `docs/conventions.md` §6.2 — 판정 함수 경로를 `private`로 갱신 + 왜 `public`을 못 쓰는지 등재.
- `_bmad-output/implementation-artifacts/deferred-work.md` — 신규 5건([[DW-819]]~[[DW-823]]) 추가만.
  기존 항목은 오케스트레이터 소유라 한 줄도 고치지 않았다.

**검증 (전부 이 세션이 직접 실행·관찰):**
- `python3 scripts/check_migrations.py` — 정적+동적 게이트 통과(0036 포함 36개 전량 적용).
- `cd api && pytest tests -q` — 490 passed, 206 skipped(실DB 미설정 가드). 실DB 환경에서는 688/8 —
  합계 696으로 동일.
- 일회용 pgvector 컨테이너에 마이그레이션 전량 재적용 후 `pytest tests/integration -q -rs` —
  **198 passed**(기존 195 + 신규 3). 컨테이너 삭제 확인.
- **red 증명**: 같은 컨테이너에서 `public.is_seller_active`를 일부러 되살려 노출을 재현 →
  새 가드 **1건 red**(197 green). drop 후 재실행 → **198 green**.
- `cd web && npm run test` — **376 passed**. `npm run test:e2e` — **82 passed, 122 skipped, 0 failed**
  (기준선과 정확히 일치).
- **불변식 재측정(HTTP 표면)**: 매물 54건 보유 판매자를 정지 → anon이 보는 on_sale 건수
  **158 → 104**(정확히 −54, 0 아님) → 해제 → **158 복구**.
- **P1 표면 검증**: anon RPC → `PGRST202`(경로 소멸), `Accept-Profile: private` → 404,
  긍정 대조군 anon 매물 읽기 → 200 + 1행.
- 프로브로 건드린 로컬 DB 값은 전부 원복 확인(`status='active'` 재조회).

**이월 5건** — 전부 실측 후 등재: [[DW-819]] 조회수 RPC가 판매자 정지를 안 본다(숨겨진 매물인데
view_count 0→1 재현) · [[DW-820]] 기존 채팅방에서 구매자는 계속 보내고 판매자는 못 답한다(양쪽 INSERT를
실제로 시도해 확인) · [[DW-821]] 최핫경로 성능·pgvector recall 미측정 · [[DW-822]] `final_revision`이
amend 관례 때문에 도달 불가 커밋을 가리킨다 · [[DW-823]] DW-804의 `trigger:` 줄이 아직 일을 배정 중이다.

**기각 10건 중 판단이 갈렸던 것**(다음 리뷰가 같은 지적을 반복하지 않도록):
- *"doc_rag 픽스처가 conftest 롤백 계약을 어겼다"* — 그 파일이 **이미** 그 이탈을 헤더에 문서화하고
  정당화해 뒀고(노드가 자기 커넥션을 따로 연다), 새 픽스처는 그 기존 패턴을 따랐다.
- *"seller_summary의 admin 픽스처가 conftest를 안 쓴다"* — conftest 자신이 그 파일을 **이관 제외
  5개** 중 하나로 명시했다. 새 코드는 파일의 기존 스타일을 따른 것이 맞다(A3).
- *"listing_images의 ai_readonly 정책이 아직 `using(true)`라 샌다"* — 다른 두 렌즈가 전이적으로 닫혀
  있음을 확인했다(`sql_guard.ALLOWED_TABLES={"listings"}`, 커버 이미지 SQL이 `listings` 조인).
- *"GRANT 존재를 단언하는 검사가 없다"* — 격자 검사가 anon으로 실제 조회하므로 GRANT가 빠지면
  42501로 red가 난다. 이미 잡힌다(그럼에도 P1 패치에 명시 단언을 함께 넣었다).
- *"Flutter `chat_models.dart` 주석이 낡았다"* — Never 절(앱 무수정) + A3(인접 주석 개선 금지).

**잔존 위험**:
- 1회차가 남긴 위험은 그대로 유효하다(하이브리드 경로 through-code 검사 없음 · red 증명 ⓐⓑ는 수동
  프로브 · `/wishlist`·채팅 화면의 null-embed 흡수는 시뮬레이션+단위검사 수준).
- 이번에 추가된 것: 로컬 개발 스택(55321/55322)에 `0036`이 적용된 상태다(원격 아님).
- `public.is_seller_active`가 다시 생기는 것은 새 가드가 잡지만, **PostgREST HTTP 표면 자체**를 도는
  자동 검사는 없다 — pytest는 DB만 본다. 이 한계를 테스트 헤더에 적어 뒀다.

---

## Auto Run Result — 후속 리뷰 3회차 (2026-08-12)

Status: done

**무엇을 했나**: 앞선 두 패스와 무관한 새 세션에서 4개 렌즈(adversarial · edge-case-hunter ·
verification-gap · intent-alignment)를 병렬로 다시 돌려 23건을 받았고, **보고를 그대로 믿지 않고
핵심 주장마다 로컬 실DB·HTTP로 직접 재현**한 뒤 중복을 합쳐 18건으로 정리해 patch 5 · 이월 5 ·
기각 8로 분류했다. 재현 결과 리뷰어 판단이 **뒤집힌 건이 2건**이다(아래 참조).

**가장 중요한 발견 — 이 스토리가 매물 조회 최핫경로에서 병렬 처리를 통째로 꺼 버렸다.**
Postgres는 `create function`에 `parallel` 절이 없으면 그 함수를 **PARALLEL UNSAFE**로 간주하고,
그런 함수가 쿼리 어디에라도(정책의 `using` 절 포함) 들어가면 그 쿼리는 병렬 플랜을 **아예 못 받는다.**
17.4의 판정 함수는 `listings` SELECT 정책 3개에 들어갔으므로, 매물을 읽는 모든 조회가 영향을 받았다.
직접 쟀다(로컬 55322, 트랜잭션+rollback, 병렬 비용 GUC를 0으로): 지금 판의 anon 조회 플랜은
`Seq Scan`, 정책이 안 걸리는 슈퍼유저 대조군은 `Gather / Workers Planned: 2 / Parallel Seq Scan`.
원인을 두 방향으로 갈라 확인했다 — ⓐ 정책에서 함수 조건만 빼 17.4 이전 형태로 되돌리면 `Gather`가
돌아오고(= 이 회귀를 17.4가 만들었다), ⓑ 조건은 그대로 두고 `parallel safe` 한 단어만 주면 역시
`Gather`가 돌아온다(= 함수 호출 자체가 아니라 표시가 원인). 이 함수는 단일 테이블 SELECT만 하고
쓰기·시퀀스·트랜잭션 상태 변경이 없어 PARALLEL SAFE 조건을 만족한다. `0036`을 in-place 수정하고
(`docs/deployment-runbook.md` 4항 — 코드리뷰 지적은 새 번호를 만들지 않는다, 원격 미적용 상태)
`proparallel='s'` 회귀 가드를 심었다.

**리뷰어 판단을 실측으로 뒤집은 2건** (다음 리뷰가 같은 지적을 반복하지 않도록):
- *"`get_seller_public_summary`가 P1이 닫은 정지 오라클을 다시 연다"*(두 렌즈 독립 지적) — **기각.**
  anon 키로 실제 호출해 보니 정지 판매자와 **매물 0건인 활성 판매자**의 응답이 구별되지 않는다
  (`joined_at`은 그대로, `other_on_sale_count`만 0). 즉 정지 여부 오라클이 아니다. 다만 그 과정에서
  **임의 uuid의 계정 존재 여부와 가입일**이 anon에게 열려 있다는 좁은 사실이 확인돼(0019 설계,
  이 스토리가 만든 것이 아님) [[DW-826]]으로 따로 열었다.
- *"사진 축의 본인·관리자 조회가 함께 좁아졌을 수 있다"* — **동작은 이미 옳았다.** 정지 후에도
  본인·관리자에게 매물 1행·사진 1행이 그대로 보인다(실측). 진짜 결함은 **그 절반을 고정하는 검사가
  없었다는 것**이라, 결론을 바꿔 검사만 추가했다.

**파일 변경 (3개):**
- `supabase/migrations/0036_is_seller_active_private_schema.sql` — `private.is_seller_active`에
  `parallel safe` 추가(in-place) + 그 근거(EXPLAIN ⓐⓑ 실측·PARALLEL SAFE 충족 근거·형제 함수는
  건드리지 않았다는 범위 한정)를 `comment on function`에 등재.
- `api/tests/integration/test_suspended_seller_hidden_real_db.py` — 신규 3건(`proparallel='s'` 가드 ·
  정지 판매자 **본인**의 사진 · **관리자**의 사진), GRANT 가드에 스키마 USAGE 단언 추가, 건수
  대조군을 자기 시드 범위로 좁힘.
- `api/tests/integration/test_write_policy_manifest_real_db.py` — 전수조사가 두 스키마를 볼 때
  proname 중복 0건을 단언(스코프를 넓힌 자리에서 그 구멍을 함께 닫음).

**검증 (전부 이 세션이 직접 실행·관찰):**
- `python3 scripts/check_migrations.py` — 일회용 컨테이너에 0001~0036 전량 재적용, 정적+동적 게이트
  통과(프로브 ①②③ 포함).
- `cd api && pytest tests/integration -q`(로컬 55322) — **201 passed**(기준선 198 + 신규 3).
- `cd api && pytest tests -q` — **691 passed, 8 skipped**(기준선 688/8 + 신규 3).
- `cd web && npm run test` — **376 passed**(기준선 일치, web 파일 무변경).
- `E2E_PORT=3020 npm run test:e2e` — **82 passed, 122 skipped, 0 failed**(기준선 정확히 일치.
  포트 3000은 이 세션 밖 프로세스가 점유 중이라 3020으로 우회했고, 그 프로세스는 건드리지 않았다).
- **red 증명 3건 — 서로 다른 표기로, 서로 다른 단언을 깼다:**
  ⓐ `proparallel` 가드는 **합성 변조 없이** red를 봤다 — 로컬 DB가 아직 0036 재적용 전이라 실제
  `'u'` 상태였고, 그 상태에서 신규 가드만 1건 red. 0036 재적용 후 green.
  ⓑ census 중복 단언 — **이미 매니페스트에 있는 이름**(`is_admin`)을 `private`에 복제해, "새 함수라
  차집합이 깨진 것"이 아니라 **중복 단언 자체**가 걸린 것을 메시지로 확인(`{'is_admin': ['public',
  'private']}`). 프로브 drop 후 4 passed.
  ⓒ 스키마 USAGE 단언 — `revoke usage on schema private from anon` 후 그 단언만 red(메시지에 42501
  실패 모드 명시), 즉시 `grant`로 원복 후 20 passed. 원복 뒤 anon HTTP 읽기 긍정 대조군도 재확인
  (`/rest/v1/listings?status=eq.on_sale&select=id&limit=1` → 1행).
- **P1(2회차) 수정 재확인**: anon 키 `POST /rest/v1/rpc/is_seller_active` → `PGRST202`(경로 없음),
  긍정 대조군 anon 매물 읽기 → 1행.
- 프로브로 건드린 로컬 DB 객체·권한은 전부 원복을 재조회로 확인했다.

**이월 5건** — 전부 실측 후 등재(기존 항목은 오케스트레이터 소유라 한 줄도 고치지 않았다):
[[DW-824]] `private` 차단의 성립 조건(원격 Data API 노출 스키마)이 미측정이고 그 계층 자동 검사가 0건 ·
[[DW-825]] Flutter 찜 화면만 아직 "판매완료"로 단정하고 앱 테스트가 그 옛 문구를 고정 ·
[[DW-826]] `get_seller_public_summary`가 anon에게 임의 uuid의 가입일을 돌려준다 ·
[[DW-827]] [[DW-814]]의 `trigger:`도 17.4를 지목한 채 남았다([[DW-823]]이 한 건만 셌다) ·
[[DW-828]] 정지→비노출→해제→복귀를 도는 브라우저 검사가 없다(이번 확인도 수동 관찰).

**기각 8건 중 판단이 갈렸던 것**:
- *"찜 회색 타일 문구를 `판매완료`로 되돌려라(흔한 쪽이 sold다)"* — 되돌리면 **팔리지 않은 매물을
  팔렸다고 단정**하는 상태로 회귀한다. 2회차 패치의 판단이 옳다. 4열에서 20자가 `truncate`되는 것은
  D5가 명시적으로 허용한 처리다(금기는 줄바꿈 찌그러짐이지 말줄임이 아니다).
- *"`private`는 권한 경계가 아니다 — default privileges도 회수하라"* — `0036`이 이미
  `revoke all ... from public`을 하고 있다. 미래 함수용 규약은 이 스토리 범위 밖.
- *"Design Notes의 GRANT 항목이 재현 없이 단정한다"* — 그 문단은 이미 *"추정하며 별도 재현은
  생략했다"* 라고 스스로 밝히고 있다. B4 위반이 아니다.
- *"`0032` 주석이 아직 `nspname='public'`이라 다음 전수조사가 그걸 복사한다"* — 전진 원칙상 0032는
  수정 불가이고, 확장의 근거는 이미 테스트 docstring에 있다.
- *"`final_revision`이 HEAD가 아니다"* — [[DW-822]]가 고른 (a)안의 **의도된 동작**이다(값이 가리키는
  것은 HEAD가 아니라 실제 작업 커밋이고, 그래야 도달 가능하다).

**잔존 위험**:
- 1·2회차가 남긴 위험은 그대로 유효하다(하이브리드 경로 through-code 검사 없음 · red 증명 ⓐⓑ는
  수동 프로브 · `/wishlist`·채팅 화면의 null-embed 흡수는 시뮬레이션+단위검사 수준).
- 이번에 추가된 것: 로컬 개발 스택(55321/55322)에 **`0036`이 재적용**됐다(정책 3개 drop→create,
  적용 후 5개 정책·`proparallel='s'` 재조회로 확인. 원격 아님).
- 성능 축은 **병렬 플랜 한 축만** 닫혔다 — 정의자 함수 인라인 불가와 pgvector recall은 여전히
  미측정이며 [[DW-821]]이 들고 있다.
- `private` 스키마 차단이 원격에서도 성립하는지는 **이 세션이 재지 않았다**([[DW-824]], 원격 접속은
  스펙 Never 절이 금지).
