---
title: 'Story 10.6 — 판매자 정보 섹션'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: '1c8a99d'
final_revision: '7346d10'
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-10-context.md'
  - '{project-root}/docs/tech-debt.md'
  - '{project-root}/web/AGENTS.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** 상세 페이지의 ④판매자정보 슬롯(Epic 9 골격)이 비어 있어 구매자가 "이 판매자가 어떤 사람인가"를 가늠할 근거가 전혀 없다. 동시에 문의 CTA(`InquiryButton`)가 데스크톱/모바일 두 벌로 항상 마운트돼 각자 `busy`/`error` 상태를 들고 있어, 한 배치에서 낸 에러가 리사이즈 시 다른 배치와 갈린다(대장 #82).

**Approach:** 그 슬롯을 **경량 판매자 정보(닉네임 + 가입 시점 + "이 판매자의 다른 판매중 매물 N건")** 로 채운다(FR56). 닉네임은 이미 조회 중인 비정규화 `listings.seller_name`을 재사용하고, RLS로 막힌 가입 시점과 on_sale 집계는 **SECURITY DEFINER RPC 하나**로 DB에서 직접 구한다 — FR11 강제지점(on_sale만·앱 레벨 필터 금지)을 데이터 계층에 박는다(B9). 문의 CTA는 두 배치를 **단일 `busy`/`error` 상태를 공유하는 하나의 클라이언트 컴포넌트**가 렌더하도록 합쳐 #82를 닫는다.

## Boundaries & Constraints

**Always:**
- 판매자 정보는 **닉네임·가입 시점·"다른 판매중 매물 N건" 3가지만** 노출한다.
- "다른 매물 N건" 집계는 **on_sale만 + 현재 매물 제외**이며, 그 필터는 **RPC(DB) 안에서** 강제한다 — 앱 코드에서 손으로 거르지 않는다(FR11 강제지점 "앱 레벨 필터 금지", B9).
- 마이그레이션은 **additive·forward-only**. 착수 시 `supabase/migrations/` 파일 목록의 **다음 빈 번호**를 쓴다(현재 관측 = `0019`; 실제 착수 시 재확인).
- 새 SECURITY DEFINER 함수는 0007 관례를 그대로 따른다: `language sql/plpgsql`, `security definer`, `set search_path = public`, 스키마 명시 참조. 실행 권한은 `grant execute … to anon, authenticated`(상세는 비로그인도 열람 — FR58).
- 문의 CTA는 **데스크톱 sticky aside + 모바일 하단 고정 바 두 배치를 그대로 유지**하되(AC7, Story 9.5), 두 배치가 **한 개의** `busy`/`error` 상태를 공유한다.
- 기존 마크업의 클래스·레이아웃·문구·시각을 보존한다(외과적 변경 — CTA를 합치되 픽셀이 바뀌면 안 된다).

**Block If:**
- 판매자 정보를 노출하려고 `listings`에 새 컬럼을 더해 anon GRANT 화이트리스트(`0011_listings_anon_select.sql`)를 넓혀야만 하는 상황 → §9.3(b)상 사용자 승인이 필요하다. 본 스펙은 RPC로 우회하므로 발생하지 않아야 한다. RPC 경로가 불가능하다고 판명되면 HALT.
- `profiles`/`auth` 스키마를 파괴적으로(드롭·타입 변경) 바꿔야만 구현되는 경우 HALT.

**Never:**
- 평판 점수·응답률·인증 배지·별점 등 **데이터가 없는 지표를 표시**(가짜 신뢰 UI — FR30 정직성·CM-C 위반).
- 옵션/판매자용 **정규화 테이블 신설**, 찜·판매자 정보의 **실시간 동기화**.
- 관리자와 공유하는 `web/src/components/listings/ListingDetailFields.tsx` 수정(Epic 15 몫).
- RPC **밖**(앱 컴포넌트)에서만 on_sale 필터를 적용하는 방식.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 다른 매물 있음 | 판매자가 현재 외 on_sale 2건 보유 | "이 판매자의 다른 판매중 매물 2건"(현재 매물 제외) + 닉네임 + "YYYY년 M월 가입" | 정상 |
| 다른 매물 없음 | 현재 매물이 그 판매자의 유일한 on_sale | "이 판매자의 다른 판매중 매물이 없어요." | 정상 |
| sold 제외 | 판매자가 sold 3건 + 현재 on_sale 1건 | 집계 = 0건(sold는 RPC의 `status='on_sale'`에서 걸러짐) | 정상 |
| 닉네임 없음 | `seller_name` = null | 닉네임 행만 숨김, 가입 시점·집계는 정상 표시 | 정상 |
| 집계/가입 조회 실패 | RPC 호출이 error/null 반환 | 섹션은 `seller_name`만으로 렌더(가입·집계 행 숨김), 페이지는 안 막힘 | 서버 콘솔 로그, 사용자 화면엔 조용히 생략 |
| 비로그인 열람 | anon이 상세 진입 | 판매자정보 섹션 전체 정상 표시(RPC가 anon에 GRANT됨) | 정상 |
| #82 상태 공유 | 데스크톱에서 문의 실패로 에러 표시 후 창을 <1024px로 좁힘 | 모바일 하단 바에도 **같은** 에러/busy가 반영(하나의 상태) | 기존 에러 문구 유지 |

</intent-contract>

## Code Map

- `supabase/migrations/0019_seller_public_summary.sql` -- **신규**. SECURITY DEFINER 함수 `get_seller_public_summary(p_seller_id uuid, p_exclude_listing_id uuid) returns table(joined_at timestamptz, other_on_sale_count integer)` + `grant execute … to anon, authenticated`. 관용구는 `0007_listings_seller_name.sql`(security definer·search_path)·`0011`(anon 노출 결정) 미러. **번호는 착수 시 재확인**(§Technical Decisions).
- `web/src/app/(user)/listings/[id]/page.tsx` -- 판매자 요약 RPC 호출(`supabase.rpc('get_seller_public_summary', …).maybeSingle()`), `<SellerInfoSection>`를 ④슬롯(현재 line 253 주석 자리)에 배선. 기존 서버 함수 `InquiryCta`와 두 배치(aside line 259-268 · 하단 바 line 277-284)를 **단일 `<InquiryCta>` 클라이언트 컴포넌트 1개**로 교체(grid 2번째 자식 자리). CTA 분기(anon/owner/inquiry)는 서버에서 `mode`로 계산해 넘긴다.
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` -- **신규 `SellerInfoSection`** export 추가. 기존 `Section`/`Field` 껍데기와 "값 없으면 행/섹션 숨김" 관례를 그대로 따르는 상태없는 서버 컴포넌트. 순수 헬퍼 `formatSellerJoinDate(iso)`·`sellerOtherListingsLabel(count)`를 같은 파일(또는 인접)에 두고 export(테스트 대상).
- `web/src/app/(user)/listings/[id]/InquiryCta.tsx` -- **신규 `'use client'`**. `InquiryButton.tsx`의 문의 개시 로직(`openOrCreateRoom` + busy/error)을 흡수해 **하나의 상태**로 두 배치(데스크톱 aside + 모바일 고정 바)를 렌더한다. props `{ mode, listingId, loginHref, priceText }`.
- `web/src/app/(user)/listings/[id]/InquiryButton.tsx` -- **삭제**(유일 사용처가 이 페이지였고 `InquiryCta.tsx`가 흡수 — 내 변경이 만든 고아, A3).
- `web/src/app/(user)/listings/[id]/__tests__/sellerInfo.test.ts` -- **신규**. `formatSellerJoinDate`·`sellerOtherListingsLabel` 순수 함수 단위테스트(0건/N건 분기, 날짜 포맷, null 입력).
- `docs/tech-debt.md` -- `#82`를 **닫는다**(형식대로 종결 기록: 무엇을·어떻게 닫았는지). 새로 생긴 이월(예: 판매자 가입일 anon 노출 재검토)이 있으면 형식대로 등재.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-6-판매자-정보-섹션` 상태 + `last_updated` 한 줄 요약 갱신.

## Tasks & Acceptance

**Execution:**
- `supabase/migrations/0019_seller_public_summary.sql` -- SECURITY DEFINER RPC + GRANT 작성 -- 가입 시점(RLS로 막힘)과 on_sale 집계를 DB가 권위 있게 구하고 FR11 필터를 데이터 계층에 강제(B9).
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` -- `SellerInfoSection` + 순수 헬퍼 추가 -- ④슬롯을 채우는 표시부(닉네임/가입/집계 3행, 값 없으면 숨김).
- `web/src/app/(user)/listings/[id]/InquiryCta.tsx` -- 단일 상태 공유 CTA 컴포넌트 신설 -- #82(두 벌 마운트 상태 분기)를 닫는 핵심.
- `web/src/app/(user)/listings/[id]/page.tsx` -- RPC 호출 + `SellerInfoSection` 배선 + CTA 두 배치를 `<InquiryCta>` 1개로 교체 -- 데이터 조회·인증 분기는 서버에서, 상태는 클라이언트 1곳에서.
- `web/src/app/(user)/listings/[id]/InquiryButton.tsx` -- 삭제 -- 흡수 후 고아 제거(A3).
- `web/src/app/(user)/listings/[id]/__tests__/sellerInfo.test.ts` -- 순수 헬퍼 단위테스트 -- I/O 매트릭스의 0건/N건·날짜 포맷·null 분기 고정.
- `docs/tech-debt.md` / `sprint-status.yaml` -- #82 종결 + 상태 갱신 -- 대장·스프린트 정합(B8).

**Acceptance Criteria:**
- Given Epic 9 골격의 판매자 섹션 슬롯, when 상세를 렌더하면, then 닉네임 + "YYYY년 M월 가입" + "이 판매자의 다른 판매중 매물 N건"이 표시된다(FR56).
- Given 판매자가 sold 매물과 현재 on_sale 매물을 보유, when 집계를 계산하면, then N은 **on_sale이면서 현재 매물이 아닌** 건수만 센다(sold·현재 매물 제외 — FR11 강제지점, 필터는 RPC 안).
- Given 데이터 없는 판매자 지표(평판·응답률·인증 배지), when 섹션을 렌더하면, then **그 어떤 것도 표시하지 않는다**(가짜 신뢰 금지).
- Given anon(비로그인) 사용자, when 상세에 진입하면, then 판매자정보 섹션이 정상 표시된다(RPC가 anon에 GRANT됨).
- Given 데스크톱 문의 CTA에서 에러가 난 상태, when 뷰포트를 <1024px로 좁히면, then 모바일 하단 바 CTA에도 **동일한** 에러/busy 상태가 보인다(단일 상태 — #82 종결).
- Given `seller_name`이 null이거나 RPC 조회가 실패, when 섹션을 렌더하면, then 해당 행만 숨기고 페이지 전체는 정상 렌더된다.

## Spec Change Log

(없음 — bad_spec 루프백이 없었다.)

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 3, low 2)
- defer: 2: (high 0, medium 0, low 2)
- reject: 4
- addressed_findings:
  - `[medium]` `[patch]` `formatSellerJoinDate`가 런타임 로컬 TZ(`getMonth()`)로 월을 계산 → UTC 서버·KST 서비스에서 월경계 가입월이 어긋남. `Intl.DateTimeFormat(Asia/Seoul)`로 교체 + 비자정 경계 회귀 테스트 추가(red→green 실측).
  - `[medium]` `[patch]` 신규 SECURITY DEFINER RPC가 새 FR11 강제지점인데 `conventions.md` §6 강제지점 목록에 미등재(Rule 7) → §6에 등재(RLS 미적용·`status='on_sale'`이 유일 가드 명시).
  - `[medium]` `[patch]` RPC의 on_sale·현재제외 필터가 커밋된 회귀 테스트 없이 수동 실측에만 의존 → `api/tests/integration/test_seller_summary_real_db.py` 신설(기존 `test_fr11_cover_images_real_db.py` 관례 미러, `api-db` CI 잡이 실행, red→green 실측).
  - `[low]` `[patch]` RPC가 `p_exclude_listing_id=NULL`(anon 직접 호출)에 0 반환 → `(p_exclude_listing_id is null or id <> …)` 가드.
  - `[low]` `[patch]` "0007 관례 그대로" 주석이 grant 포스처를 오도(0007=trigger-only) → 정정(definer·search_path 하드닝만 계승, execute는 RPC로 의도적 부여).
- deferred (→ `docs/tech-debt.md`, 프로젝트 규칙상 deferred-work.md 동결):
  - `[low]` #119 RPC가 anon에 임의 uuid 가입월 노출(데모 한정, 0007과 동일 성격 — 운영 재검토 트리거).
  - `[low]` #120 authenticated 롤 테이블 기본 GRANT 마이그레이션 부재 → 로컬 db reset 시 로그인 경로 42501(운영은 플랫폼 기본권한 암묵 의존, 미검증 가정).
- rejected: 4 — #82 공유상태 커밋 테스트 부재(리포 관례상 E2E 미커밋·단일 useState 구조적 보장) · `count<=0` 분기(`count(*)`는 음수 불가, 현행이 더 방어적) · RPC 실패 콘솔-only 관측성(하우스 패턴, #99/#73로 추적) · owner가 자기 판매자 카드 열람(정합적, 결함 아님).

### 2026-07-22 — Follow-up review pass (done 스펙 재리뷰, 4레인)
- intent_gap: 0
- bad_spec: 0
- patch: 3: (high 0, medium 0, low 3)
- defer: 0
- reject: 11
- addressed_findings:
  - `[low]` `[patch]` `0019`가 `revoke … from public` 없이 `grant execute to anon, authenticated`만 해, Postgres 기본 PUBLIC EXECUTE 때문에 명시 grant가 장식이 되고 #119의 "authenticated 전용으로 좁힘" 이연 경로가 조용히 무력화됨. 함수 정의 직후 `revoke all … from public`을 추가(0007 하드닝 관례 계승). 로컬 DB 실측: proacl이 `{postgres=X,anon=X,authenticated=X}`로 PUBLIC 항목 소거 + anon 실행 여전히 가능 확인. 마이그레이션 게이트 green.
  - `[low]` `[patch]` `conventions.md` §6 신규 "SECURITY DEFINER 함수 축"이 위험만 서술하고 강제 검사를 인용 안 함(형제 두 축은 "조건을 지우면 red" 테스트를 명시) → `test_seller_summary_real_db.py`를 강제 장치로 인용 추가(규칙7·B9 정합).
  - `[low]` `[patch]` `SellerInfoSection`의 조립 가드(`!sellerName && !joinLabel && !otherLabel` → 섹션째 숨김)·행별 숨김이 자동 커버리지 0 — 순수 헬퍼만 테스트됨(10.2 `TrustAttributes.test.ts` 렌더-계층 선례 미적용). `sellerInfo.test.ts`에 컴포넌트를 함수로 직접 호출해 반환 트리를 순회하는 렌더 테스트 3건 추가(세 값·닉네임행만 숨김·값 전무 시 null). red/green 실측: 가드 제거 시 "값 전무 → null" 테스트 red, 원복 시 205 green.
- rejected: 11 — 위 3 patch 외 전부. 주요: owner가 자기 카드 열람(정합적·직전 pass도 reject) · `count<=0` 음수 미도달 방어분기 · #82 공유상태 자동테스트 부재(직전 pass reject·단일 useState 구조 보장) · RPC 실패 콘솔-only 관측성(#73/#99 기존 추적) · `.maybeSingle<{}>` 타입 단언 드리프트(수정=생성타입/서버컴포넌트 렌더테스트로 범위 밖·A2 과설계·실DB가 컬럼명 고정) · 모바일 `position:fixed` 바가 grid 자손이라 미래 transform 조상에 취약(현재 그런 조상 없음·현 결함 아님·portal 수정은 A2/의도한 레이아웃 보존과 상충) · `formatSellerJoinDate` 파싱불가 무음 null(신뢰 DB timestamptz·저위험) · 실DB 픽스처 컬럼 하드코딩(스키마 변경 시 라우드 실패는 정상). **이미 대장 등재분 재발견은 신규 defer 금지(오케스트레이터 소유)**: #119(anon 임의 uuid 가입월) · #120(authenticated 기본 GRANT 부재·항목이 미검증 가정 자체를 명기) · sprint-status.yaml 인용부호 취약성(10.3에서 트리거와 함께 이연 등재됨).

## Design Notes

**왜 RPC 하나인가 — 가입 시점은 RLS로 막혀 있고, 집계는 FR11 강제지점이다.** 구매자는 남의 `profiles` 행을 못 읽는다(`0001` RLS: 본인·admin만). 그래서 가입 시점은 어떤 식으로든 정의자 권한이 필요하다. 이왕 DB로 내려가는 김에 "다른 매물 N건" 집계도 같은 함수에 넣으면 (1) 왕복 1회로 끝나고 (2) on_sale 필터가 **DB 안에** 박혀 앱이 잊을 수 없다(B9, FR11 "앱 레벨 필터 금지"). listings에 컬럼을 더하는 대안은 anon GRANT 화이트리스트를 넓혀 §9.3(b) 승인 게이트를 밟으므로(무인 실행 Block) 피한다. 닉네임은 이미 `listings.seller_name`(0007 비정규화)을 조회 중이라 재사용한다.

골든 예시(0007의 security definer·search_path 관례를 그대로):
```sql
create or replace function public.get_seller_public_summary(
  p_seller_id uuid, p_exclude_listing_id uuid
) returns table (joined_at timestamptz, other_on_sale_count integer)
language sql security definer set search_path = public as $$
  select
    (select created_at from public.profiles where id = p_seller_id),
    (select count(*)::int from public.listings
       where seller_id = p_seller_id and status = 'on_sale'
         and id <> p_exclude_listing_id);
$$;
grant execute on function public.get_seller_public_summary(uuid, uuid) to anon, authenticated;
```
`status='on_sale'` 리터럴은 SQL 계층의 기존 관례(0002·0011·0015가 같은 리터럴 사용)와 일치한다.

**#82 종결 방식 = 상태를 위로 올려 두 배치가 한 상태를 공유.** 현재는 `<InquiryButton>`이 두 곳에 마운트돼 `busy`/`error`가 각자다. 해소는 **하나의 클라이언트 컴포넌트**가 `busy`/`error`를 1개 들고, 그 값으로 데스크톱 aside 버튼과 모바일 고정 바 버튼을 **둘 다** 렌더하는 것이다(같은 상태를 읽는 두 DOM 노드). 모바일 바는 `position:fixed`라 grid 안에 중첩돼도 뷰포트 하단에 고정된다 — 배치·클래스는 기존 그대로 보존한다(외과적). 세 분기(anon 링크/owner 링크/inquiry 버튼) 중 상태를 갖는 건 inquiry뿐이며, `mode`는 서버(page.tsx, `user` 보유)가 계산해 넘긴다.

**가입일 anon 노출은 데모 한정 — 0007과 같은 판단.** 임의 uuid의 가입월을 anon이 조회할 수 있게 되지만, seller_id는 공개 매물에 이미 묶여 있고 가입월은 FR56이 공개 표시를 요구하는 값이다. 0007이 `seller_name`에 남긴 "운영 전 개인정보 재검토(데모 한정)"와 같은 성격 — 필요 시 대장에 트리거와 함께 이월한다(신설 스토리 아님).

## Verification

**Commands:**
- `cd web && npm run lint` -- expected: 0 errors
- `cd web && npx tsc --noEmit` -- expected: 타입 에러 0(새 컴포넌트·RPC 반환 타입 포함)
- `cd web && npm run test` -- expected: 기존 + 신규 `sellerInfo.test.ts` 전부 green (0건/N건·날짜 포맷·null 분기)
- `cd web && npm run build` -- expected: 빌드 성공(클라이언트/서버 경계 위반 없음)

**Manual checks (RLS/RPC는 자동 하네스가 없다 — 로컬 Supabase MCP `execute_sql`로 실측, 커밋되는 테스트 아님):**
- `supabase db reset`로 0019까지 적용 후, `execute_sql`로 함수 존재·GRANT 확인, 그리고 **anon 롤 임퍼소네이션**(`set local role anon`)으로 `select * from get_seller_public_summary(<seller>, <current_listing>)` 호출 → 가입 시점 반환 + 집계가 **on_sale·현재 제외** 건수와 일치하는지 확인. 대조군: 해당 판매자에 sold 매물을 하나 넣어도 집계가 안 늘어남을 실측(FR11 red/green).
- 로컬 dev(`npm run dev`)에서 상세 페이지를 **로그인/비로그인** 두 상태로 열어 판매자정보 섹션(닉네임·가입월·N건)이 뜨는지, 데스크톱→모바일 리사이즈에서 문의 CTA 에러 상태가 공유되는지(#82) 브라우저로 확인.

## Auto Run Result

Status: done

**구현 요약:** 상세 페이지 ④판매자정보 슬롯을 경량 정보(닉네임 + "YYYY년 M월 가입" + "이 판매자의 다른 판매중 매물 N건")로 채웠다(FR56). 닉네임은 기존 비정규화 `listings.seller_name`(0007) 재사용, 가입 시점(RLS로 구매자 차단)과 on_sale 집계(FR11 강제지점)는 SECURITY DEFINER RPC `get_seller_public_summary`(0019) 하나로 DB에서 구해 필터를 데이터 계층에 강제(B9). 문의 CTA 두 배치(데스크톱 aside·모바일 고정 바)를 단일 `busy`/`error`를 공유하는 `InquiryCta.tsx`로 합쳐 대장 #82(이중 마운트 상태 분기)를 닫았다.

**변경 파일:**
- `supabase/migrations/0019_seller_public_summary.sql` (신규) — 판매자 공개 요약 RPC(가입 시점 + 다른 on_sale 매물 수, 현재 매물 제외), anon/authenticated에 execute만 GRANT.
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` — `SellerInfoSection` + 순수 헬퍼 `formatSellerJoinDate`(Asia/Seoul 명시)·`sellerOtherListingsLabel`.
- `web/src/app/(user)/listings/[id]/InquiryCta.tsx` (신규 `'use client'`) — 두 배치 단일 상태 공유(#82 종결).
- `web/src/app/(user)/listings/[id]/InquiryButton.tsx` (삭제) — 흡수된 고아 제거(A3).
- `web/src/app/(user)/listings/[id]/page.tsx` — RPC 호출 + `SellerInfoSection` 배선 + CTA 1개로 교체.
- `web/src/app/(user)/listings/[id]/__tests__/sellerInfo.test.ts` (신규 12건) — 순수 헬퍼 0건/N건·날짜포맷·TZ 경계·null 분기.
- `api/tests/integration/test_seller_summary_real_db.py` (신규 5건) — RPC FR11 필터·자기제외·anon 접근 real-DB 회귀(`api-db` CI).
- `docs/conventions.md` — §6 FR11 강제지점 목록에 RPC 등재.
- `docs/tech-debt.md` — #82 종결 + 신규 defer #119·#120 등재.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 10-6 done + 요약.

**리뷰 결과:** 리뷰 4레인(적대·엣지케이스·검증갭·의도정합) 실행. 패치 5건(medium 3·low 2) 적용 · defer 2건(#119·#120, low) 대장 등재 · reject 4건. intent_gap·bad_spec 0.

**후속 리뷰 권고:** true (patch medium 3건 → 3×3=9 ≥ 5).

**검증:** web `lint`(0)·`tsc --noEmit`(0)·`test`(202 passed, TZ 경계 red→green 실측)·`build` 통과. api `pytest`(223 passed·integration 17/17, RPC FR11 필터 제거 시 red→복원 green 실측). `check_migrations.py` 게이트(0019) 통과. RPC FR11 red/green 로컬 psql 실측(현재·sold 제외 확인). #82 Playwright 실측(1280px 에러 유발→390px 리사이즈 시 동일 에러 문구 공유). 오케스트레이터 독립 재확인: web tsc/test 재실행 green, 신규 산출물·§6 등재·NULL 가드 존재 확인.

**잔여 리스크:** (1) #120 — 로컬 Supabase `authenticated` 기본 GRANT 부재(운영은 플랫폼 기본권한 암묵 의존, 미검증 가정 — 대장 등재). (2) #119 — RPC의 가입월 anon 노출(데모 한정, 0007과 동일 성격 — 대장 등재).

---

### 후속 리뷰 pass 결과 (2026-07-22, done 스펙 재리뷰)

`followup_review_recommended=true`(직전 pass) 대로 새 세션에서 4레인(적대·엣지케이스·검증갭·의도정합) 재리뷰 1회 실행. **patch 3건(전부 low) · defer 0 · reject 11 · intent_gap·bad_spec 0.**

- **patch 3건 적용:** (a) `0019`에 `revoke all … from public` 추가 — 명시 grant를 실효화(Postgres 기본 PUBLIC EXECUTE 제거, #119의 "authenticated 전용" 이연 경로가 실제로 동작하도록 전제 마련). (b) `conventions.md` §6 SECURITY DEFINER 축에 강제 검사(`test_seller_summary_real_db.py`) 인용 추가. (c) `sellerInfo.test.ts`에 `SellerInfoSection` 렌더-계층 테스트 3건 추가(조립 가드·행별 숨김 — 10.2 `TrustAttributes` 선례 적용).
- **재검증:** web `lint`(0)·`tsc --noEmit`(0)·`test`(205 passed, 신규 3건 포함·가드 제거 red→원복 green 실측)·`build` 통과. `check_migrations.py` 게이트(0019 revoke 포함) green. 로컬 DB(55322) 실측 — 0019 적용 후 함수 proacl `{postgres=X,anon=X,authenticated=X}`(PUBLIC 항목 소거) + `set role anon`으로 실행 여전히 성공 확인.
- **후속 리뷰 재권고:** **false** (patch high 0·medium 0·low 3 → 3×0+1×3=3 < 5). 이 pass는 low 하드닝/테스트 완결성만 남겨 추가 리뷰 루프 불필요.
- **신규 대장 등재:** 없음. 재발견된 #119·#120·sprint-yaml 취약성은 이미 등재된 항목이라 오케스트레이터 소유로 두고 신규 defer를 만들지 않음.
