---
baseline_commit: 745e7b8
---

# Story 9.7: 시드 사진 + 이미지 하위호환 검증 (G3/CM-A)

Status: ready-for-dev

## Story

As a 데모 운영자,
I want 기존 매물에 실차 사진을 채우고 사진 없는 매물도 안 깨지길,
so that 데모가 실제 서비스처럼 보이고 기존 매물이 정상 표시된다.

**범위: 데이터 시딩 + 검증 + 마이그레이션 1장.** 새 화면·새 컴포넌트·새 이미지 파이프라인은 **만들지 않는다.**
이 스토리는 **Epic 9의 exit-gate**다 — 9.1~9.6이 만든 것이 실제 데이터 규모에서 안 깨지는지 **실측으로 증명**하는 자리다.

---

## ✅ 범위 결정: A안 — "되는 만큼 전량" (사용자 결정 2026-07-21)

**`SEARCH_TERMS`를 최대한 늘리고, Wikimedia Commons에 허용 라이선스 사진이 없는 모델은 사진 없이 남긴다.**
남는 플레이스홀더는 결함이 아니라 **AC2(G3/CM-A)의 실전 검증 재료**다 — 사진 있는 매물과 없는 매물이 한 화면에 섞여야 하위호환을 실제로 시험할 수 있다.

- **커버리지 수치 목표를 세우지 않는다.** "몇 %"를 약속하면 Commons에 없는 모델을 억지로 채우려다 라이선스 필터를 느슨하게 만들 유인이 생긴다(#69가 정확히 그 사고였다).
- **못 채운 모델은 "왜 못 채웠는지"와 함께 표로 기록한다**(검색 결과 0건 / 허용 라이선스 없음 / 검색어 매핑 실패). 이게 다음에 다시 시도할 때의 출발점이 된다.

### 결정의 근거가 된 실측 (2026-07-21, 원격 DB)

에픽 원문·대장 #68은 **"100건 전량 시딩"**이라 적었지만, **착수 전 실측 결과 그 문장 그대로는 불가능하다.**
아래는 추측이 아니라 2026-07-21 원격 DB 실측이다 — dev는 이 숫자를 다시 재고 시작한다.

| 측정 | 값 |
|---|---|
| `listings` 전체 | **103** (on_sale 95 · sold 8) |
| 사진이 있는 매물 | **5** (`listing_images` 10행, 전부 `credit` 채워짐) |
| `seed_listing_photos.py`의 `SEARCH_TERMS`가 매칭하는 on_sale 매물 | **16** (그중 5건이 이미 시딩됨 → **남은 대상 11건**) |
| 스크립트를 지금 그대로 돌렸을 때 늘어나는 매물 | **최대 11건** (5 → 16) |
| 시딩되지 않은 on_sale 매물의 고유 (제조사, 모델) 조합 | **약 66종** |

즉 **전량을 채우려면 `SEARCH_TERMS`를 15종 → 약 66종으로 늘리는 것이 이 스토리 작업량의 대부분**이고,
그중 국산 마이너 모델(캐스퍼·베뉴·봉고3·포터2·모닝 JA 등)은 **Wikimedia Commons에 허용 라이선스 사진이 있는지 자체가 미지수**다(측정 전엔 단정하지 않는다).

*(검토했던 대안: **B. 수치 목표**(예 "on_sale의 N% 이상") · **C. 현행 유지**(대응표 확장 없이 남은 11건만). A를 택했다.)*

### ⚠️ 향후 매물 ~50건 추가와의 관계 (사용자 확인 2026-07-21)

`deferred-work.md:174`에 **"신규 ~50건(인기 국산 준중형·중형·대형 세단, 사용자가 나중 추가)"** 계획이 살아 있다.
단 그건 **보류된 기능("문서 기반 차량 상태 관리" — 성능점검표·보험처리이력)의 시드 전략**이고, **이번 증분(Epic 9~16)에는 들어 있지 않다.**

**그래서 이 스토리에 주는 함의 — dev는 이걸 알고 `SEARCH_TERMS`를 짠다:**
- 그 50건은 **인기 국산 준중형·중형·대형 세단**으로 예고돼 있다 = 쏘나타·그랜저·K5·아반떼·SM6·말리부 계열. **이미 대응표에 있거나 이번에 넣을 것들과 겹친다.**
- 따라서 **대응표를 "지금 있는 매물"에만 맞춰 좁게 짜지 말 것.** 세대코드 변형(`쏘나타`/`쏘나타 DN8`, `아반떼 MD`/`아반떼MD`)을 넉넉히 넣어두면 50건이 들어올 때 **시드 스크립트를 다시 안 고쳐도 된다.**
- ⚠️ 반대로 **50건을 미리 만들지 않는다** — 이번 스토리 범위 밖이고, 그 기능 자체가 보류다(A2).

---

## Acceptance Criteria

원문 출처: `_bmad-output/planning-artifacts/epics-increment-2026-07-12.md:560-577` Story 9.7 (SM-A, CM-A, G3, ㉠).
출처별 분류:
- **에픽 원문 유래**: AC1(시딩·credit) · AC2(G3/CM-A 플레이스홀더) · AC3(#27 재실행) · AC6(데이터 보존)
- **대장 이월**(`docs/tech-debt.md`가 이 스토리를 예약·트리거로 지목 — CLAUDE.md B5): **AC4**(#54 마이그레이션) · **AC5**(#73·#83·#80 트리거 도달) · **AC7**(#68 닫기)
- **검증 DoD**: AC8

---

1. **시드 사진을 채운다 — 기존 스크립트를 고쳐 쓴다. 새 스크립트를 만들지 않는다.**
   - 자산: `scripts/seed_listing_photos.py` (이미 존재하고 **동작이 검증된 상태다** — 현재 DB의 10장이 이 스크립트 산출물이다). Commons 검색 → 라이선스 필터 → 1600px WebP q0.82 재인코딩 → 시드 판매자 JWT로 업로드 → `listing_images` 행 INSERT(`credit` jsonb 포함).
   - **손댈 곳은 `SEARCH_TERMS` 딕셔너리 하나**(`:49-65`)다. 나머지 로직(라이선스 토큰 필터 `is_license_allowed` · `sort_order`/`is_cover` 파생 · 순차 INSERT · 고아 정리)은 **코드리뷰로 이미 고쳐진 것**이라 건드리지 않는다(A3, 대장 #68 "부수" · #69).
   - ⚠️ **`SEARCH_TERMS`는 `(제조사, 모델)` 정확 일치다.** DB에 표기 흔들림이 실재한다 — `니로 EV`/`니로EV`, `아반떼 MD`/`아반떼MD`, `쏘나타`/`쏘나타 DN8`. **DB 값을 고치지 말고**(그건 이 스토리 범위 밖의 데이터 변경이다) **딕셔너리에 변형을 각각 넣는다.**
   - ⚠️ **스크립트는 판매자 한 명만 본다** (`seller_id=eq.{uid}`, 기본 `--email seller-seed@test.com`). 시드 판매자가 **3명**이고 매물이 그들에게 흩어져 있다:

     | seller_id (앞 8자) | 매물 | on_sale | 사진 있음 |
     |---|---|---|---|
     | `12dfba00` (= `seller-seed@test.com`) | 44 | 42 | 5 |
     | `0f937a74` (= `seller-seed2@test.com`) | 31 | 29 | 0 |
     | `c19a85e7` (= `seller-seed3@test.com`) | 28 | 24 | 0 |
     | `748caac4` · `e2c9bae0` (비-시드 실사용자) | 3 · 2 | 3 · 2 | 0 |

     → **`--email`을 바꿔 3번 돌린다.** 비-시드 판매자 5건은 비밀번호를 모르므로 **대상 밖**이다(그대로 "사진 준비중"으로 남는 것이 정상이며, 오히려 AC2의 검증 재료다).
   - `credit`(저작자·라이선스·원본링크)은 **저장만 한다. 화면에 표시하지 않는다** — 대장 **#70**이 ⚪ 의도적 보류로 닫혀 있다(사용자 결정 2026-07-20). 표시 코드를 추가하지 말 것. *(되살아나는 조건은 #70 본문에 있다.)*
   - 실행 결과(매물 수·행 수·건너뛴 모델과 그 이유)를 **Completion Notes에 표로** 남긴다.
   (에픽 `:568-570`, ㉠, tech-debt #68·#69·#70)

2. **G3/CM-A — 사진 없는 매물이 세 화면 전부에서 "사진 준비중"으로 뜨고 에러 0건.**
   - 확인할 세 소비처(전부 **이미 구현돼 있다** — 새로 만들지 않는다):
     1. **목록 카드** — `web/src/components/listings/ListingCardImage.tsx` (`/search`, 홈)
     2. **상세 갤러리** — `web/src/components/listings/ListingGallery.tsx` (`PhotoPlaceholder`, 0장 분기 `:68-74`)
     3. **AI 응답 카드** — `web/src/components/ai/ChatAssistant.tsx` → 같은 `ListingCard` 재사용 (`/ai`)
   - **"에러 0건"의 정의를 코드로 못박는다**: 브라우저 콘솔 에러 0 · 네트워크 4xx/5xx 0 · **깨진 이미지 아이콘 0**. 셋을 각각 관찰하고 결과를 적는다.
   - ⚠️ **`onError` 2겹 폴백이 실제로 발화하는지 확인한다** — `conventions.md` §10.2가 규정한 ①`onError` + ②ref 콜백(`img.complete && naturalWidth===0`)이다. 존재 확인이 아니라 **작동 확인**(B4).
     재현법(§10.2에 이미 적혀 있다): 이미지 호스트를 블랙홀로 돌리고 렌더한다 —
     `chrome-headless-shell --host-resolver-rules="MAP <supabase-host> 127.0.0.1" --screenshot=... <URL>`
     → **"사진 준비중"이 떠야 한다.** alt 텍스트·깨진 아이콘이 보이면 폴백이 죽은 것이다.
   - **sold 매물(8건)도 함께 본다**: 구매자 경로 어디에도 안 나타나는 것(FR11) + api 응답 JSON에 그 매물의 `image_path`가 없는 것.
   (에픽 `:571`, G3/CM-A, `conventions.md` §6·§10.2)

3. **#27 — 시드 재실행 시 사진이 살아남는지 **측정**한다. "에러 0건"으로 갈음 금지.**
   - **대장 #27이 이 스토리를 검증 자리로 지목했다.** 핵심 문장: *"`ON DELETE CASCADE`는 조용히 지우므로 **에러 0건이 곧 정상이 아니다**."*
   - 🚨 **원격 DB에서 `seed.sql`을 그대로 재실행하지 않는다.** 착수 전 실측으로 파괴 범위를 확인했다:
     - `supabase/seed.sql:196` = `delete from public.listings where seller_id = v_seller_id;` (그리고 `:413-414`가 seller2·3에 대해 같은 일) → 새 uuid로 재삽입.
     - `listings`의 **CASCADE 자식이 둘**이다 — `listing_images`(0012) **와 `chat_rooms`(0003)**.
     - 현재 `chat_rooms` 5건 · `chat_messages` 10건이 **전부 시드 매물에 걸려 있다**(실측). 즉 재실행은 **사진 + 채팅 이력 전부**를 지운다. 게다가 Storage 오브젝트는 CASCADE 대상이 아니라 **파일만 남는 고아**가 된다.
     - ✎ **#27 본문의 *"`listing_images`가 `listings`의 첫 자식 테이블"* 은 사실이 아니다** — `chat_rooms`가 Epic 5(0003)부터 먼저 있었다. 이 정정을 #27에 기록한다.
   - **어떻게 측정하나**: 파괴적 실행 대신 **도커 fresh Postgres**에서 잰다(마이그레이션 게이트가 쓰는 것과 같은 방식 — `scripts/check_migrations.py` · `scripts/migration-check-prelude.sql`). Storage 없이도 `listing_images` 행만으로 이 질문에 답할 수 있다:
     1. 마이그 전량 적용 → `seed.sql` 1회 실행 → 시드 매물 몇 건에 `listing_images` 더미 행 삽입 → **행 수 A**와 **매물 id 목록 A** 기록
     2. `seed.sql` **2회차** 실행 → **행 수 B**와 **매물 id 목록 B** 기록
     3. **A vs B를 숫자로 비교**하고, **id가 같은지 다른지**를 명시적으로 기록한다
   - **결과가 "사진이 안 살아남는다"로 나와도 그것이 정답이다.** 이 AC가 요구하는 것은 "살아남게 만들라"가 아니라 **"사실을 측정해서 기록하라"**다. 측정 결과에 따라:
     - id가 **바뀌면** → delete-재삽입이 여전히 일어나는 것 → **Epic 10.5 `wishlists`에서 되살아난다**는 사실을 #27에 남긴다(에픽 원문이 지정).
     - 그리고 **운영 결론을 런북에 한 줄로 남긴다**: "이 DB에서 `seed.sql` 재실행은 사진·채팅을 파괴한다 — 하려면 먼저 X를 한다."
   - ⚠️ `seed_listing_photos.py`의 재실행(사진이 있는 매물을 건너뜀)과 **혼동하지 않는다.** #27이 묻는 것은 **`seed.sql`** 재실행이다.
   (에픽 `:573-577`, tech-debt #27)

4. **마이그레이션 `0015` — `listings_update_own`에 `status <> 'sold'`를 넣는다 (#54).**
   - 대장 **#54**가 *"📅 예약: Story 9.7 마이그레이션 … 9.7 스토리 AC에 체크박스로 심을 것"*이라고 이 스토리를 지목했다.
   - 현재(`0002_listings.sql`): `using (auth.uid() = seller_id) with check (auth.uid() = seller_id)` — **status 조건이 없다.** 그래서 수정 폼을 열어둔 채 다른 탭에서 구매완료 처리하면 **sold 매물이 그대로 수정된다**(화면 층 단일 방어).
   - **앱 코드가 아니라 DB에 박는다** — 화면이 늘어도 안 샌다(CLAUDE.md B9).
   - 파일명: `supabase/migrations/0015_listings_update_not_sold.sql` (다음 번호. 현재 마지막은 `0014`).
   - **self-contained**여야 한다 — 마이그레이션 게이트(`scripts/check_migrations.py`) 통과가 DoD다(`conventions.md` §9.1: *"자기가 필요로 하는 선행 상태를 스스로 만들거나, 번호가 더 작은 마이그에만 의존한다"*).
   - ⚠️ **`using`과 `with check`를 둘 다 본다.** `using`만 고치면 "sold를 못 고른다"이고, `with check`까지 봐야 "on_sale을 sold로 못 바꾼다"까지 막히는데 — **그건 FR7(구매 완료 처리) 자체를 막는다.** 구매완료가 계속 동작해야 하므로 **`using`에만 `status <> 'sold'`를 건다**. 이 판단을 마이그 주석에 남긴다.
   - **red-green 증명**(B4): 마이그 적용 전 sold 매물 UPDATE가 **통과**하는 것을 실측 → 적용 후 **거부**되는 것을 실측 → **on_sale 매물의 정상 수정과 구매완료(on_sale→sold)는 여전히 통과**하는 것도 실측. 세 결과를 다 적는다.
   - GRANT 축은 건드리지 않는다(정책 수정뿐) → #18 (a′) 절차 해당 없음. 그래도 **적용 전 원격 정책 원문을 떠서 기록**한다.
   (tech-debt #54, `conventions.md` §9.1, CLAUDE.md B9)

5. **전량 시딩이 트리거인 대장 3건을 재평가한다 — 이 스토리가 그 트리거다.**
   대장이 *"#68 전량 시딩 시점에 다시 연다"*고 명시한 항목들이다. **해소가 아니라 재측정 + 판단 기록**이 이 AC의 요구다.
   - **#73 (3중 무음 폴백)** — *"사진이 실제 매물 대부분에 붙는 시점(#68 전량 시딩 이후)"*이 트리거. 시딩 후에는 "전면 장애"와 "사진 없는 매물"이 처음으로 구별 가능해진다(그전엔 플레이스홀더가 다수라 이상 신호가 안 보였다). **AC2의 블랙홀 재현이 정확히 이 구별을 시험하는 실험**이다 — 결과를 #73에 기록하고, 해소할지/계속 이월할지 판단한다.
   - **#83 (썸네일이 원본을 그대로 받는다)** — 트리거가 *"#68 전량 시딩 — 매물당 사진이 5~10장이 되면 상세 1건이 3~4MB"*. **시딩 후 사진 장수가 가장 많은 매물의 상세 페이지 전송량을 `curl`로 실측**해 숫자로 남긴다. 오늘의 시드는 매물당 1~3장이라 실제로 그 규모가 되는지부터 확인.
   - **#80 (용량 근거 "196~205KB"가 틀렸다)** — #83과 같은 자리. **아직 안 고친 자리가 명시돼 있다**: `web/src/components/listings/ListingCardImage.tsx:54`의 주석과 9.4 스토리 문서. 이 스토리가 카드 이미지 경로를 실측하므로 **그 주석을 실측값으로 정정한다**(트리거: *"9.4 카드 이미지를 손대는 스토리"*).
   - ⚠️ **셋 다 "새 최적화를 도입하라"가 아니다.** 9.5에서 사용자가 C안(현 상태 수용)을 택했다. 요구는 **숫자를 재고 기록하는 것**이다 — 9.5에서 벌어진 일이 정확히 "실측 없이 괜찮다고 적은 것"이었다.
   (tech-debt #73·#83·#80)

6. **CM-A — 기존 데이터가 보존된다. 시딩은 더하기만 한다.**
   - 시딩 전후로 다음이 **변하지 않아야** 한다: `listings` 행 수 · 각 매물의 `id` · `embedding`(AI 검색 근간) · `guide_documents`.
   - **시딩 전/후 스냅샷을 숫자로 찍어 비교한다** — `count(*)`, `count(*) where embedding is not null`, 표본 id 몇 개. "안 건드렸으니 괜찮다"로 갈음하지 않는다(B4).
   - 시딩은 `listing_images` INSERT + Storage 업로드뿐이다. `listings`를 UPDATE하지 않는다.
   (에픽 `:572`, CM-A)

7. **대장·문서 정리 — 이 스토리가 닫는 것과 기록하는 것.**
   - **닫는다**: **#68**(시드 사진 스크립트가 스토리 밖에서 만들어짐 — 이 스토리가 남은 4개 체크박스를 전부 소화하면 닫힌다) · **#54**(AC4 마이그레이션으로 해소).
   - **갱신한다**: **#27**(AC3 측정 결과 + *"첫 자식은 `chat_rooms`였다"* 정정 + Epic 10.5 `wishlists` 인계 문구).
   - **기록한다**: **#73**·**#83**·**#80**(AC5의 재측정 결과와 판단).
   - **런북**(`docs/deployment-runbook.md`): AC3의 운영 결론("`seed.sql` 재실행의 파괴 범위") 한 줄.
   - ⚠️ **항목에 줄을 더할 땐 위쪽에 그걸 부정하는 줄이 있는지부터 본다** — #18이 같은 실수를 두 번 냈다(*"경고문은 자기 자신을 지키지 못한다"*).
   (CLAUDE.md B8 "일을 끝내면 대장을 닫는다")

8. **검증 DoD — 실제로 돌려 관찰하고 결과를 남긴다.** "코드를 그렇게 짰다"로 갈음하지 않는다(CLAUDE.md B4).
   - `pytest`(api 전체) · `vitest`(web) · `tsc` · `eslint` · `next build` · `scripts/check_migrations.py` — 각각 결과를 적는다.
   - **실브라우저 E2E**: `/search` 목록 → 사진 있는 카드와 "사진 준비중" 카드가 **한 화면에** 보이는 것 · 상세 갤러리(사진 있는 매물 / 0장 매물 각 1건) · `/ai` 검색 결과 카드. **스크린샷**으로 남긴다.
   - **반응형 D5**: 1280 · 800 · 390px 세 뷰포트에서 카드가 안 깨지는 것(`project-context.md` 규칙13). ⚠️ `/ai` 390px 가로 넘침은 **기존 결함 #84**이고 **이 스토리가 만든 것이 아니다** — 재현되면 #84를 인용하고 넘어간다(고치지 않는다, 트리거는 Epic 11.3/13.4/11.5).
   - ⚠️ **E2E 도구 클릭이 무동작하는 간헐 현상(#88)** 이 세 번 관측됐고 **원인 미규명**이다. 재현되면 시간을 쓰지 말고 #88에 관측을 한 줄 더하고 다른 경로(직접 URL 이동 등)로 진행한다.

---

## Tasks / Subtasks

- [ ] **Task 1. 시드 사진 채우기** (AC1 — 범위는 A안 확정됨)
  - [ ] 시딩 전 스냅샷 기록 (AC6) — `listings` 행 수 · embedding 채워진 수 · `listing_images` 행 수
  - [ ] `SEARCH_TERMS` 확장 (표기 변형 + 향후 50건 세단 계열까지 넉넉히). `--dry-run`으로 매칭 결과 먼저 확인
  - [ ] 못 채운 모델을 **사유별로** 표에 기록(검색 0건 / 허용 라이선스 없음 / 매핑 실패)
  - [ ] `--email`을 바꿔 시드 판매자 3명에 대해 실행
  - [ ] 시딩 후 스냅샷 + 건너뛴 모델 표를 Completion Notes에
- [ ] **Task 2. 마이그레이션 0015** (AC4)
  - [ ] 적용 전: 원격 `listings_update_own` 정책 원문 덤프 + sold 매물 UPDATE가 **통과**하는 것 실측(red)
  - [ ] `0015_listings_update_not_sold.sql` 작성 (self-contained, `using`에만 조건)
  - [ ] `scripts/check_migrations.py` 통과 확인
  - [ ] 적용 후: sold UPDATE **거부** · on_sale 수정 **통과** · 구매완료(on_sale→sold) **통과** 3건 실측(green)
- [ ] **Task 3. #27 시드 재실행 측정** (AC3)
  - [ ] 도커 fresh Postgres에 마이그 전량 + `seed.sql` 1회 → 더미 `listing_images` 삽입 → 행 수·id 기록
  - [ ] `seed.sql` 2회차 → 행 수·id 기록 → **비교표** 작성
  - [ ] 결과와 정정(첫 자식 = `chat_rooms`)을 #27에 반영, 런북에 운영 결론 한 줄
- [ ] **Task 4. G3/CM-A 검증** (AC2)
  - [ ] 세 소비처(목록·상세·AI) 실브라우저 관찰 — 콘솔 에러 / 네트워크 4xx·5xx / 깨진 아이콘 각각 0건 확인
  - [ ] 블랙홀 재현(`--host-resolver-rules`)으로 2겹 폴백 발화 확인 → 스크린샷
  - [ ] sold 매물 FR11 + api 응답 JSON에 `image_path` 부재 확인
  - [ ] 1280·800·390px D5 확인
- [ ] **Task 5. 대장 트리거 3건 재측정** (AC5)
  - [ ] #83 — 사진 최다 매물 상세 전송량 `curl` 실측
  - [ ] #80 — `ListingCardImage.tsx:54` 주석의 "196~205KB"를 실측값으로 정정
  - [ ] #73 — Task 4의 블랙홀 실험 결과로 판단 기록
- [ ] **Task 6. 대장·문서 정리** (AC7) — #68·#54 닫기 · #27 갱신 · #73·#83·#80 기록 · 런북 한 줄
- [ ] **Task 7. 검증 DoD** (AC8) — 테스트 전량 + 스크린샷

---

## Dev Notes

### 0. 범위 경계 — 먼저 읽을 것

**만들지 않는 것:**
- 새 화면·새 컴포넌트·새 이미지 최적화(`next/image`·썸네일 규격). 9.5에서 사용자가 **현 상태 수용**을 택했다(#83).
- `credit` 화면 표시 — **#70이 ⚪ 의도적 보류로 닫혀 있다.** 저장만 하고 표시 안 한다.
- Flutter 앱 사진 — **Epic 16.2**의 몫이다. 앱 목록 카드는 아직 사진을 그리지 않는다.
- `seed.sql`의 매물 INSERT문을 고정 id로 바꾸는 리팩터 — #27이 **(c) 근거 있는 이월**로 판단했고, 재판단 시점은 **Epic 10.5**다.
- DB의 모델명 표기 정규화(`니로 EV`/`니로EV` 등) — 데이터 변경은 범위 밖. 딕셔너리에 변형을 넣어 흡수한다.

**고치는 파일(예상):** `scripts/seed_listing_photos.py`(`SEARCH_TERMS`만) · `supabase/migrations/0015_*.sql`(신규) · `web/src/components/listings/ListingCardImage.tsx`(주석 숫자 1줄, #80) · `docs/tech-debt.md` · `docs/deployment-runbook.md`.

### 1. 현재 이미지 파이프라인 — 이미 다 있다

| 층 | 자리 | 상태 |
|---|---|---|
| 스키마 | `supabase/migrations/0012_listing_images.sql` — `credit jsonb` 포함, 10장 트리거, 대표 1장 부분 유니크 인덱스 | 완료 |
| 경로 무결성 | `0013` — 소유자를 `storage_path`에서 파싱하지 않고 `listings`에서 직접 구해 대조하는 트리거 | 완료 |
| 버킷 | `0014` — **공개 버킷**(`public=true`). 서명 URL 없음, 만료 없음 | 완료 |
| URL 조립 | `web/src/lib/storage/index.ts:15` `getPublicUrl()` — 동기·실패 없음·**파일 존재 미확인** | 완료 |
| 대표 판별 | `web/src/lib/images/coverImages.ts` — `order by sort_order, id`, **`is_cover`를 안 본다** | 완료 |
| 목록 카드 | `ListingCardImage.tsx` — 2겹 폴백(`onError` + ref `naturalWidth===0`) | 완료 |
| 상세 갤러리 | `ListingGallery.tsx` — 대표·썸네일 양쪽 2겹 폴백 + 0장 분기 | 완료 |
| AI 카드 | `api/app/graph/listing_cards.py::attach_cover_images` → `web/src/lib/api/aiSearch.ts::resolveCardImage` | 완료 |
| 시드 도구 | `scripts/seed_listing_photos.py` | 완료(딕셔너리만 부족) |

**→ 이 스토리는 배관을 만들지 않는다. 물을 흘려보내고 새는 데가 없는지 본다.**

### 2. `seed_listing_photos.py`를 쓰는 법

```bash
python3 -m venv .venv && .venv/bin/pip install requests Pillow   # api/ venv에 넣지 않는다
.venv/bin/python scripts/seed_listing_photos.py --limit 5 --dry-run
.venv/bin/python scripts/seed_listing_photos.py --limit 40 --email seller-seed2@test.com
```
- 환경값: `web/.env.local`(`NEXT_PUBLIC_SUPABASE_URL`·`ANON_KEY`) · `supabase/.env.seed`(`SEED_PASSWORD`)
- **`service_role` 키를 쓰지 않는다** — 시드 판매자로 실제 로그인해 그 JWT로 올린다. 그래서 Storage RLS와 `0013` 경로 트리거가 **브라우저와 똑같이** 적용된다. 이 성질을 깨지 말 것(`conventions.md` §5).
- 장수는 `counts = [3,1,2,3,1,2,3,1]` 순환 — **일부러 섞는다**(N장 배지와 플레이스홀더가 한 화면에 같이 보여야 검증이 된다).
- `--dry-run`은 다운로드·변환까지 하고 업로드만 건너뛴다 → **`SEARCH_TERMS` 확장의 적중률을 안전하게 미리 잴 수 있다.**

### 3. 자주 밟는 지뢰 (이 프로젝트에서 실제로 밟은 것들)

- **"에러 0건 = 정상"이 아니다.** `ON DELETE CASCADE`도, `on conflict do nothing`도, `UPDATE ... where`도 전부 **조용히 아무것도 안 하고 성공**한다. 이 프로젝트는 같은 함정을 #27·#44에서 두 번 밟았다. **행 수를 세라.**
- **"존재 확인 ≠ 작동 확인."** 폴백 코드가 파일에 있는 것과 실제로 발화하는 것은 다르다 — 9.4에서 리뷰 3개 레이어가 전부 놓쳤다(`onError`가 하이드레이션 전 실패에 발화하지 않는 문제).
- **`getPublicUrl`은 파일 존재를 확인하지 않는다.** 경로만 있으면 URL이 나온다 → 없는 파일은 로드 실패 → **소비처의 2겹 폴백이 유일한 방어**다.
- **`is_cover`를 읽지 마라.** 파생값이고 시드·레거시 행은 전부 `false`일 수 있다. 대표 = `order by sort_order, id`의 첫 행.
- **문서 숫자를 검산 없이 인용하지 마라.** "196~205KB"가 두 번의 독립 실측으로 틀렸다고 확인됐는데(#80), 그 정정 문장 자체도 한 번 오기재됐다.

### 4. 참고 — 착수 전 실측 원본 (2026-07-21, 원격 DB)

```
listings_total=103  on_sale=95  sold=8
listing_images=10   listings_with_images=5   images_with_credit=10
chat_rooms=5  chat_messages=10  (5건 전부 시드 매물에 걸려 있음)
listings의 CASCADE 자식: listing_images(0012), chat_rooms(0003)
SEARCH_TERMS 매칭 on_sale=16 / 미매칭 on_sale=79
```

### Project Structure Notes

- 마이그레이션: `supabase/migrations/NNNN_이름.sql`, **전진(forward-only)**, RLS 정책은 해당 테이블 마이그와 **동거**. 현재 마지막 = `0014` → 이 스토리는 `0015`.
- 시드 도구는 `scripts/`(루트). **`api/` 가상환경에 의존성을 넣지 않는다** — api는 Cloud Run 이미지라 시드 도구로 부풀리지 않는다.
- 원장(마이그 번호 정본)은 `epics-increment-2026-07-12.md`의 "마이그레이션 원장" 표다. 거기엔 `0014=wishlists`로 적혀 있으나 **9.0이 `0014`를 공개 버킷 전환에 썼다** — 파일 목록이 정본이고, 뒤 번호는 그만큼 밀린다. 이 사실을 원장 표에 한 줄 반영할 것.

### References

- [Source: _bmad-output/planning-artifacts/epics-increment-2026-07-12.md#Story 9.7] (`:560-577`) — AC 원문
- [Source: _bmad-output/planning-artifacts/epics-increment-2026-07-12.md#지표 추적 매트릭스] (`:238,245,250`) — SM-A·CM-A·G3가 9.7에 착지
- [Source: docs/tech-debt.md#27] — 시드 멱등 delete, "에러 0건 ≠ 정상"
- [Source: docs/tech-debt.md#54] — `listings_update_own`에 `status <> 'sold'` (📅 9.7 마이그레이션)
- [Source: docs/tech-debt.md#68] — 9.7에 남은 체크박스 4건
- [Source: docs/tech-debt.md#70] — credit 표시 ⚪ 의도적 보류 (구현 금지)
- [Source: docs/tech-debt.md#73·#80·#83] — 트리거 = 전량 시딩
- [Source: docs/tech-debt.md#84·#88] — 이 스토리가 만든 것이 아닌 기존 결함
- [Source: docs/conventions.md#10] — 이미지 스토리지 계약 (공개 버킷·경로 규칙·상한 강제 주체)
- [Source: docs/conventions.md#10.1] — 쓰는 쪽 규칙 (저장본 규격·대표=sort_order 0·삭제 순서)
- [Source: docs/conventions.md#10.2] — 읽는 쪽 규칙 (정렬·`is_cover` 금지·2겹 폴백·재현법)
- [Source: docs/conventions.md#6] — FR11 강제 지점 목록
- [Source: docs/conventions.md#9.1] — 마이그 self-contained 불변식
- [Source: _bmad-output/project-context.md#규칙13] — D5 반응형 무결성
- [Source: _bmad-output/implementation-artifacts/9-6-ai-응답-카드-사진.md] — 직전 스토리 (AI 카드 사진 부착)

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### File List
