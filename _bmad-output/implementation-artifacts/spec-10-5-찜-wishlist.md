---
title: 'Story 10.5 — 찜 (wishlist)'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: 'aefc3b8'
final_revision: '28bf363'
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

**Problem:** 로그인 사용자가 마음에 든 매물을 모아 다시 찾아올 방법이 없다. 재방문을 유도하는 핵심 고리(찜)가 비어 있고, 카드의 하트(♡) 버튼은 Epic 9가 만든 죽은 자리표시자(`disabled`)로만 존재한다.

**Approach:** `wishlists(user_id, listing_id, created_at, PK(user_id,listing_id))` 테이블 + 본인 전용 RLS를 신설하고, 카드 하트를 낙관적 토글 버튼으로 살린다(비로그인=로그인 게이트+원위치 복귀 후 자동 반영, 실패=롤백+조용한 토스트). "찜한 매물" 목록 페이지와 상단 내비 진입점을 추가한다. 찜 여부는 ListingCard wire 필드가 아니라 **사용자별 오버레이**(별도 조회)로 다룬다(conventions §4·65 계약 오염 방지).

## Boundaries & Constraints

**Always:**
- 스키마는 epic이 지정한 그대로: `wishlists(user_id, listing_id, created_at)` + 복합 PK `(user_id, listing_id)`. 정규화·집계(찜 개수) 컬럼·스냅샷 컬럼을 더하지 않는다(A2, epic "인기신호=보류, 스키마만 남김").
- 마이그레이션 파일 번호는 **착수 시 `supabase/migrations/` 목록의 다음 빈 번호**로 정한다 — 현재 최신은 `0017`이므로 `0018_wishlists.sql`. additive·forward-only(§9).
- 본인 전용 RLS 3정책(select/insert/delete, `auth.uid() = user_id`)만. anon·ai_readonly 정책 없음(로그인 전용). 명시 GRANT 추가 금지(레포 관례: authenticated=플랫폼 기본, 정책 부재 롤=0행 — `0003_chat.sql`·`0011` 참조).
- FK 둘 다 `on delete cascade`(레포 전 자식 테이블 관례 `0002`/`0003`/`0012`와 동일; 복합 PK는 NOT NULL이라 set null 불가, restrict는 판매자 삭제를 막으므로 부적합).
- 찜 여부 상태는 `ListingCardData`(wire 계약)에 넣지 않는다 — `ListingCard`에 별도 sibling prop(`wished`/`authed`)으로 주입(conventions §4·65).
- 낙관적 토글: 누르면 즉시 채워짐 → 서버 확정, 실패 시 아이콘 롤백 + 조용한 토스트(house 채팅 전송 패턴 `ChatRoomMessages.tsx` 준용). 진행 중 연타 차단.
- 로그인 게이트는 어포던스를 숨기지 않는다(FR58) — 비로그인도 하트를 보고, 누르면 `/login?redirectedFrom=<현재경로+wish=id>`로 보냈다가 복귀 후 그 찜을 자동 반영. `resolveSafeRedirect`(`web/src/lib/auth/redirect.ts`) 사용.
- 접근성: 하트 히트영역 ≥44×44px(현 `h-11 w-11` 유지), `aria-pressed` + "찜하기"↔"찜 취소" 라벨 전환.
- 찜 목록의 판매완료 매물은 회색 + "판매완료" 비활성 배지 + 상세 진입 차단(FR11·UX-DR20). 빈 상태 문구 = "아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요."(UX-DR19).
- `/wishlist`를 `web/src/proxy.ts`의 `PROTECTED_PREFIXES`에 추가(개인 페이지 1차 게이트, `/chat`과 동급).
- **대장 `#89` 시드 재실행 판단을 이 스토리에서 내리고 근거와 함께 `docs/tech-debt.md`에 남긴다**(B5·B8, 아래 Design Notes 참조).
- **본인 RLS가 실제로 "듣는지" red-green 실측**(Epic 9 회고 A5): 타인 계정으로 남의 찜 조회 시 0행, 정책 무력화 대조군에서 1행 누수 확인.

**Block If:**
- (없음 — 스키마·RLS·UX·게이트 관용구가 전부 epic/conventions/기존 코드로 확정됨. 아래 Design Notes의 "삭제된 매물 배지" 판단은 epic이 지정한 PK가 이미 선택을 강제하므로 미해결 결정이 아님.)

**Never:**
- app(Flutter) 미러 금지 — 찜은 wire 필드가 아니라 app 계약(conventions §4) 무변경, 위젯은 Epic 16. 이 스토리는 web 전용.
- 전역 토스트 라이브러리(`sonner` 등) 도입·전역 토스트 인프라 신설 금지(A2 — 첫 소비처는 로컬 transient로 충분, 공용화는 2번째 소비처 트리거로 대장에 이월).
- `ListingCardData`·`api/schemas/ai.py`·app `listing.dart` 카드 계약 변경 금지(찜은 wire 필드 아님 → §4.1 락스텝 대상 아님).
- 시드 `seed.sql`을 고정 id로 전환하는 리팩터 금지(이 스토리 범위 밖·별도 스토리 — 아래 #89 판단 참조).
- 스냅샷 컬럼(제목/상태 저장)으로 "하드삭제 후에도 찜 관계 유지"를 구현하지 않는다(epic 지정 PK·additive·A2에 반함 — Design Notes).
- 찜 개수 집계·인기 정렬 신호 구현 금지(epic 범위 밖, 스키마만 남겨둠).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 로그인 사용자 찜 토글 | 카드 하트(♡) 클릭(현재 미찜) | 즉시 채워짐(♥, aria-pressed=true, 라벨 "찜 취소") → `wishlists` insert 확정. 재클릭 시 delete·복귀 | insert 실패 시 아이콘 롤백 + 조용한 `role=status` 토스트 |
| 비로그인 찜 클릭 | 미로그인 상태로 하트 클릭 | `/login?redirectedFrom=<경로+wish=id>`로 이동(아이콘 미변경 — 저장 불가) | 없음 |
| 로그인 후 복귀 자동 반영 | 위 게이트 통과 후 원위치 URL에 `?wish=<id>` | 마운트 시 해당 카드가 자동 찜(insert)되고 채워짐, `wish` 파라미터는 URL에서 제거 | insert 실패 시 롤백 + 토스트(중복이면 무시) |
| 이미 찜한 매물 재클릭 | 채워진 하트 클릭 | 즉시 비워짐 → `wishlists` delete 확정 | delete 실패 시 롤백 + 토스트 |
| 찜 목록 조회 | 로그인 사용자가 `/wishlist` 진입 | 본인 찜 매물이 최신순 카드 그리드로 표시(전부 찜 상태) | 조회 실패 시 `role=alert` 안내 |
| 찜 목록 빈 상태 | 찜이 0건 | EmptyState "아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요." | 없음 |
| 찜 목록의 판매완료 매물 | 찜한 매물이 sold(타인 소유→RLS로 embed=null, 또는 본인 소유→status=sold) | 회색 처리 + "판매완료" 비활성 배지 + 상세 링크 없음(진입 차단), 찜 관계는 유지 | 없음 |
| 찜한 매물이 하드삭제됨 | 판매자가 매물 delete | cascade로 찜 행이 함께 제거 → 목록에서 사라짐("삭제된 매물" 배지는 도달 불가, Design Notes) | 없음 |

</intent-contract>

## Code Map

- `supabase/migrations/0018_wishlists.sql` -- **신규**. wishlists 테이블 + 복합 PK + `listing_id` 인덱스 + RLS 3정책. house 관용구는 `0003_chat.sql`(테이블+RLS 동거)·`0002_listings.sql:88-118`(정책 네이밍) 미러.
- `web/src/lib/wishlist.ts` -- **신규**. 서버 헬퍼 `fetchWishedListingIds(supabase, userId, listingIds): Promise<Set<string>>`, `fetchWishlist(supabase, userId)`(wishlists ⨝ listings 조회). 순수 술어 `isWishedListingBlocked(embed): boolean`(embed=null 또는 status==='sold' ⟹ true). 클라이언트 mutation은 WishButton 인라인(얇음).
- `web/src/components/listings/WishButton.tsx` -- **신규** `'use client'`. props `{ listingId: string; initialWished: boolean; authed: boolean }`. 낙관적 토글·게이트·`?wish=` 복귀 반영·롤백·transient 토스트·`aria-pressed`·라벨 전환. `usePathname`/`useSearchParams`/`useRouter` + 브라우저 supabase(`@/lib/supabase/client`).
- `web/src/components/listings/ListingCard.tsx:103-120` -- 죽은 하트 자리표시자(`disabled aria-hidden tabIndex=-1`)를 `<WishButton listingId={listing.id} initialWished={wished} authed={authed} />`로 교체. props에 sibling `wished?: boolean`·`authed?: boolean` 추가(**`ListingCardData`엔 넣지 않음**). 카드는 서버 렌더 유지(WishButton이 클라 경계).
- `web/src/app/page.tsx:57-73,150-152` -- 로그인 시 `fetchWishedListingIds`로 preview 매물의 찜 집합 조회, `<ListingCard ... wished={...} authed={!!user} />`.
- `web/src/app/(user)/search/page.tsx:112-153,204-206` -- 동일하게 검색 결과에 찜 오버레이 주입.
- `web/src/app/(user)/wishlist/page.tsx` -- **신규** 서버 컴포넌트. `getUser()`(없으면 로그인 리다이렉트) → `fetchWishlist` → `attachCoverImages`(on_sale만) → on_sale은 `ListingCard`(wished=true), sold/embed-null은 회색 "판매완료" 비활성 타일, 0건은 `EmptyState`. `search/page.tsx`의 3분기(error/empty/grid) 구조 준용.
- `web/src/proxy.ts:26` -- `PROTECTED_PREFIXES`에 `'/wishlist'` 추가.
- `web/src/components/layout/AppHeader.tsx:34-43` -- 로그인 사용자에게 `/wishlist`로 가는 "찜" 링크 추가(현 placeholder 헤더에 최소 진입점 — 전체 내비 재구성은 Epic 11.2).
- `web/src/lib/__tests__/wishlist.test.ts` -- **신규**. `isWishedListingBlocked` 3상태(on_sale=false·sold=true·null=true) + `fetchWishedListingIds`의 Set 구성 로직(주입 가능하면) 단위테스트.
- `docs/tech-debt.md` -- `#89` 판단 기록(근거+트리거) + 신규 이월(공용 토스트 인프라·"삭제된 매물 배지 도달불가")를 형식대로 등재.
- `_bmad-output/implementation-artifacts/sprint-status.yaml:2,144` -- `10-5-찜-wishlist` 상태 + `last_updated` 한 줄 요약.

## Tasks & Acceptance

**Execution:** (의존 순서대로 — 만드는 쪽[DB] → 읽는 쪽[UI], B3)

- `supabase/migrations/0018_wishlists.sql` -- **신규**. `create table if not exists public.wishlists(user_id uuid not null references public.profiles(id) on delete cascade, listing_id uuid not null references public.listings(id) on delete cascade, created_at timestamptz not null default now(), primary key(user_id, listing_id));` + `create index if not exists wishlists_listing_id_idx on public.wishlists(listing_id);` + `enable row level security` + 3정책(`wishlists_select_own`/`insert_own`/`delete_own`, `auth.uid() = user_id`). 헤더 주석에 "로그인 전용·GRANT 없음·cascade 근거" 명시. -- DB 토대.
- `web/src/lib/wishlist.ts` -- **신규**. `fetchWishedListingIds`(주어진 listing_id 목록 중 본인 찜 집합)·`fetchWishlist`(본인 찜 ⨝ listings 카드컬럼, 최신순)·순수 `isWishedListingBlocked(embed)`. -- 서버 조회 + 순수 술어.
- `web/src/components/listings/WishButton.tsx` -- **신규** 낙관적 토글 버튼(위 Code Map 명세). 조용한 토스트 = 로컬 state에 짧게 담고 `role="status"`로 렌더 후 setTimeout 자동 소멸(전역 인프라 없이). -- 하트 상호작용.
- `web/src/components/listings/ListingCard.tsx` -- 하트 자리표시자를 `WishButton`으로 교체 + sibling props 추가. 다른 로직 무변경. -- 카드에 찜 배선.
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` -- 로그인 시 찜 오버레이 조회 후 카드에 `wished`/`authed` 주입. -- 카드 초기 상태 공급(두 렌더 지점).
- `web/src/app/(user)/wishlist/page.tsx` -- **신규** 찜 목록 페이지(빈 상태·판매완료 회색 비활성·on_sale 클릭 가능). -- 목록 도달점.
- `web/src/proxy.ts` -- `PROTECTED_PREFIXES`에 `/wishlist`. -- 1차 게이트.
- `web/src/components/layout/AppHeader.tsx` -- 로그인 시 "찜" 링크. -- 내비 진입점.
- `web/src/lib/__tests__/wishlist.test.ts` -- **신규** 순수 술어·집합 로직 단위테스트(red-green 1회 실측). -- 실행되는 검사(B9).
- `docs/tech-debt.md` -- `#89` 판단(근거+트리거) 기록 + 신규 이월 2건 등재. -- 대장 정합(B5·B8).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-5` 상태 + `last_updated` 갱신. -- 상태 정합.

**Acceptance Criteria:**
- Given 로그인 사용자가 카드의 하트를 누르면, when insert가 성공하면, then 하트가 즉시 채워지고(`aria-pressed=true`, 라벨 "찜 취소") `wishlists`에 (내 id, 매물 id) 행이 생기며, 재클릭 시 delete되어 비워진다.
- Given insert/delete가 실패하면, when 서버가 거부하면, then 하트 아이콘이 직전 상태로 롤백되고 조용한 `role="status"` 토스트가 잠깐 떴다 사라진다(연타 중에는 재요청이 나가지 않는다).
- Given 비로그인 사용자가 하트를 누르면, when 클릭하면, then `/login?redirectedFrom=<현재경로&wish=매물id>`로 이동하고, 로그인 성공 후 원위치로 복귀하면 그 매물이 자동으로 찜되며 URL의 `wish` 파라미터는 제거된다.
- Given 로그인 사용자가 상단 내비의 "찜"으로 `/wishlist`에 도달하면, when 찜이 있으면, then 본인 찜 매물이 최신순 카드로 표시되고, 없으면 "아직 찜한 매물이 없어요. ♡를 눌러 관심 매물을 모아보세요."가 표시된다.
- Given 찜한 매물이 판매완료(sold)면, when 찜 목록을 렌더하면, then 그 카드는 회색 + "판매완료" 비활성 배지 + 상세 링크 없음(진입 차단)으로 보이되 찜 관계는 유지된다(하드삭제된 매물은 cascade로 목록에서 사라진다).
- Given 타인 계정이 남의 찜을 조회하면, when `wishlists`를 select하면, then 0행이고, 정책 조건을 일부러 무력화한 대조군에서는 1행이 새어 red-green이 성립한다.
- Given `isWishedListingBlocked`에 on_sale/sold/null을 넣으면, when 술어를 돌리면, then 각각 false/true/true이고, 판정식을 뒤집으면 red가 되었다가 되돌리면 green이다.

## Design Notes

**"삭제된 매물" 배지가 도달 불가인 이유 — epic 지정 PK가 선택을 강제한다.** AC 원문(UX-DR20)은 "판매완료/삭제된 매물" 두 배지를 나열하지만, epic은 동시에 `PK(user_id, listing_id)`를 **명시적으로 지정**한다. 복합 PK 컬럼은 NOT NULL이라 `listing_id`에 `on delete set null`을 쓸 수 없고, `restrict`는 판매자 삭제(`ListingActions.tsx` 하드 delete)를 막는다. 따라서 레포 전 자식 테이블과 동일한 `on delete cascade`가 유일하게 정합적인 선택이며, 그 결과 **하드삭제된 매물의 찜 행은 함께 사라진다**(목록에 남지 않음). 남는 회색 케이스는 **sold** 하나뿐이고, 이때는 (타인 소유면 RLS로 embed=null, 본인 소유면 status='sold') `isWishedListingBlocked`가 걸러 회색+"판매완료"로 렌더한다. cascade 특성상 찜 목록에 남은 행 중 embed가 없는 것은 **반드시 sold**다(삭제분은 이미 제거됨) → null=sold 추론이 신뢰 가능. "하드삭제 후에도 관계 유지 + 삭제 배지"를 원하면 스냅샷 컬럼이 필요하나 이는 epic의 스키마 최소화·additive·A2에 정면으로 반하므로 범위 밖(대장에 트리거로 이월).

**#89(시드 재실행이 자식을 지운다) 판단 — 이 스토리의 결정 = 현행 유지(b), 근거는 숫자.** `seed.sql`은 매물 id를 `gen_random_uuid()`로 재발급하며 delete+재삽입한다(Story 9.7 실측: id 보존 0/97). `wishlists`가 새 cascade 자식이 되므로 재시드 시 찜도 전량 삭제된다. **그럼에도 (a) 고정 id 전환을 이 스토리에서 하지 않는다:** (1) 재시드는 데모 리셋 전용이고, 갓 시드된 DB엔 잃을 찜이 없다(찜은 상호작용으로만 생기며 리셋은 그 상호작용 상태를 의도적으로 비우는 행위다) — "유실 체감이 크다"던 근거는 운영 영속성 축인데 찜은 시드되지 않고 운영에선 재시드가 돌지 않는다. (2) 고정 id 전환은 사진·채팅까지 걸린 delete+재삽입 전략 전체를 바꾸는 교차 리팩터라 단일 찜 스토리에 끼워 넣으면 A2/A3 위반이다 — 전용 스토리 몫. → `docs/tech-debt.md #89`에 이 판단과 트리거(운영/스테이징 재시드가 필요해지거나 고정-id 전용 스토리 착수 시)를 남긴다.

**낙관적 토글은 채팅 전송 패턴을 그대로 준용.** `ChatRoomMessages.tsx:97-123`가 이미 "로컬 즉시 반영 → await → 실패 시 롤백 + 에러" house style이다. 찜은 단일 행이라 id-dedupe 병합이 불필요해 더 단순하다. 진행 중 플래그로 연타 차단(`ListingActions.tsx:33` 관례).

**RLS는 자동 테스트 하네스가 없다 — MCP 수동 실측이 house 관례.** 이 레포엔 RLS 롤 임퍼소네이션 pytest가 없고, `set local role authenticated` + `set local request.jwt.claims`로 조회 후 rollback하는 방식으로 스토리 문서에 실측을 남긴다(Story 2-1 선례). 본 스토리도 로컬 Supabase MCP `execute_sql`로 (타인=0행 / 정책 무력화 대조군=1행) red-green을 실측·기록한다 — 커밋되는 자동 테스트가 아님을 명시(리뷰어의 "자동 테스트 누락" 오인 방지).

**조용한 토스트는 로컬 transient로 최소 구현.** 레포에 토스트 인프라가 전무하다(`role="alert"` 인라인만 존재). 첫 소비처인 찜 실패 알림은 WishButton 내부 로컬 state + `role="status"` + setTimeout 자동 소멸로 충분하다(A2). 2번째 소비처가 생기면 공용 primitive로 승격 — 대장에 트리거로 이월.

## Verification

**Commands:**
- `cd web && npm run test` -- expected: 기존 케이스 + `wishlist.test.ts` 신규 전부 green. `isWishedListingBlocked` 판정식 뒤집어 red→복원 green 1회 실측.
- `cd web && npm run lint` -- expected: 신규/수정 파일 경고 0.
- `cd web && npm run build` -- expected: 타입·빌드 통과(`next build`).
- `python3 scripts/check_migrations.py` -- expected: `0018_wishlists.sql` 파일명·번호 규약 통과.

**Manual checks (로컬 Supabase + Playwright MCP — 찜 DoD, B4):**
- 마이그레이션 적용(로컬 stack) 후 **RLS 실측(MCP `execute_sql`)**: 사용자 A가 매물 X를 찜 → B 컨텍스트(`set local request.jwt.claims sub=B`)로 `select from wishlists` = **0행** 확인. 그 뒤 `select_own` 정책을 `using(true)`로 임시 교체한 대조군에서 **1행 누수** 확인 → 원복(rollback)해 red-green 성립을 스토리 문서에 기록.
- 브라우저 E2E(시드 계정): 카드 하트 토글(채워짐↔비워짐, `aria-pressed`·라벨 전환), 실패 롤백(네트워크 차단 등으로 유도)·토스트, 비로그인 클릭→로그인 게이트→복귀 후 `?wish=` 자동 반영, `/wishlist` 목록(빈 상태·판매완료 회색 비활성·진입 차단), 상단 "찜" 내비 도달을 각각 확인. 390px에서 레이아웃 깨짐·가로 스크롤 없음(D5).
- 환경 문제(로컬 Supabase·인증)로 자동화가 막히면 그 사실을 로그와 함께 정직히 보고하고 수동 확인 범위를 명시한다(재보기 전 선언 금지, B4).

## Spec Change Log

(없음 — bad_spec 루프백이 없었다.)

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 1, low 4)
- defer: 1
- reject: 8
- addressed_findings:
  - `[medium]` `[patch]` 찜 목록의 판매완료(회색) 타일에 찜 해제 수단이 전혀 없어(on_sale 카드는 WishButton으로 해제되는데 비대칭) sold가 된 찜이 목록에 영구히 남던 문제 — `RemoveWishButton`(신규, `wishlists` delete + `router.refresh()`)을 `BlockedWishTile`에 배선. 실브라우저로 제거 시 타일 즉시 소멸 확인.
  - `[low]` `[patch]` 페이지가 on_sale 그룹 전체를 먼저·blocked 그룹을 나중에 렌더해 `fetchWishlist`의 `created_at desc` 정렬이 그룹 경계에서 깨지던 문제 — `entries`를 원래 순서로 한 번만 순회하며 자리마다 카드/타일을 고르도록 재작성(on_sale은 id→ListingCardData Map으로 조회). 최신순 보존 실측.
  - `[low]` `[patch]` `authed`가 서버 렌더 시점 값이라 세션 만료 시 true로 남아 클릭이 게이트를 건너뛰고 `getUser()` null → "재시도해도 안 되는" 실패 토스트만 뜨던 문제 — `applyToggle`에서 user가 null이면 토스트 대신 롤백 후 로그인 게이트로 보내도록 수정(`RemoveWishButton`도 동일). 쿠키 삭제로 세션 만료시켜 실브라우저 확인.
  - `[low]` `[patch]` `isWishedListingBlocked`가 denylist(`=== sold`)라 status가 undefined(select 드리프트)거나 미래 제3상태면 "정상 클릭 카드"로 새던 문제 — allowlist(`!== on_sale`)로 전환해 기본-차단(fail-safe)으로. 신규 테스트 2건(undefined/미래값→blocked) + red/green 실측.
  - `[low]` `[patch]` `/wishlist` 페이지가 `attachCoverImages`를 새로 호출하는데 conventions §6 이미지 축 소비처 목록(규칙7)에 미등재던 문제 — §6에 한 줄 등재(on_sale 찜 id만 넘기고 `listing_images` RLS가 강제).

Reject 요지(8): 오버레이 조회 실패 시 빈 Set(=attachCoverImages와 동일한 house 관례) · 실패 토스트 `role="status"`(스펙이 "조용한 토스트"로 지정 — `role="alert"`는 "조용한"에 반함, 롤백이 1차 신호) · `useSearchParams` 전 카드 재렌더(현 규모 무영향·A2) · `getUser()` 매 쓰기 왕복(세션 검증 겸용·P3가 그 결과를 씀) · `wishlists` insert에 on_sale 가드 없음(하트는 on_sale 카드에만 있어 정상 UX로 도달 불가·FK가 경계·P4가 stray를 회색화) · 위시 페이지 on_sale 카드 해제 후 stale 타일(스펙 "실시간 sync 아님"·하트는 정확·이동 시 해소) · 크래프트된 `?wish=` 링크 무단 찜(우리 로그인 흐름만 `?wish=` 생성·제거 가능한 on_sale 1건·수정은 로그인복귀 마커 필요=범위밖) · 로그인 복귀 후 대상 미렌더 시 찜 유실(홈 프리뷰 절삭·페이지네이션 한정 엣지).

Defer(1) → `docs/tech-debt.md #118`: 찜 RLS 격리·FK cascade가 커밋된 회귀 테스트 없이 1회 수동 실측에만 의존(레포에 RLS 임퍼소네이션 하네스 부재, 2-1과 동일 관례). 트리거 = 하네스 도입 시 또는 wishlists RLS/FK 다음 수정 시.

### 2026-07-22 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 1: (high 0, medium 0, low 1)
- defer: 0
- reject: 12
- addressed_findings:
  - `[low]` `[patch]` `BlockedWishTile`(wishlist/page.tsx:44-45) 주석이 "pointer-events는 이 버튼만 정상 값"이라 타일이 `pointer-events-none`인 것처럼 읽히나, 실제 코드는 타일에 pointer-events를 끄는 곳이 전혀 없다(opacity-60은 시각 처리뿐). 주석/코드 드리프트 — 미래 유지보수자가 주석에 맞춰 타일을 "고치면" 버튼이 죽을 수 있다. 주석을 실제 동작대로("opacity-60은 클릭을 막지 않는다") 정정. lint·build·test·migration 게이트 재실행 전부 green.

Reject 요지(12): ① `/wishlist`에서 on_sale 카드 하트로 찜 해제 시 카드가 즉시 안 사라짐(하트는 ♥→♡로 정확히 반영·이동 시 해소, 공유 WishButton을 라우트에 결합하면 A2 위반, 이전 패스 동일 reject) · ② `wishlists_listing_id_idx`가 "미래 인기수 집계용 사변 인덱스"라는 지적은 오독 — FK cascade(매물 하드삭제 시 wishlists를 listing_id로 스캔, PG는 FK 컬럼 자동 인덱스 안 함)가 정당화 · ③ `fetchWishlist` 페이지네이션 없음(데모 규모·레포 무페이지네이션 관례와 동일·low) · ④ `useSearchParams` Suspense 미경계(현 호스트 페이지가 dynamic이라 build 통과·정적 라우트 재사용 시에만 표면화하고 그때 next가 요란히 실패) · ⑤ 자동반영 insert 일시 실패 시 `autoWishPending` 미리셋으로 재시도 없음(롤백+토스트 피드백 있고 수동 재클릭 가능·엣지의 엣지) · ⑥ `?wish=`가 add-intent만 실어 세션 경계 넘긴 해제 의도 유실(우리 로그인 흐름은 add만 생성·범위밖 엣지) · ⑦ `RemoveWishButton`이 `router.refresh()`를 await 안 함/`pending`을 finally에서 해제(이 Next의 refresh는 void 반환·재활성 창은 새로고침까지의 짧은 cosmetic·언마운트 경고 실질 없음) · ⑧ `RemoveWishButton` 에러가 자동소멸 안 함/`role="alert"`(intent의 "조용한 토스트"는 하트 토글 규정·삭제 실패엔 assertive가 오히려 타당·별 affordance·low) · ⑨ 매 토글마다 `getUser()` 왕복(세션 재검증 겸용·P3 게이트가 그 결과 사용·이전 패스 동일 reject) · ⑩ `PROTECTED_PREFIXES` 느슨한 prefix 매치(`/chat`·`/sell` 기존 관례·충돌 `/wishlist-*` 라우트 없음·매치 의미 변경은 교차 리팩터로 범위밖) · ⑪ 인증 사용자가 profiles 행 없을 때 FK 23503→일반 토스트(정상 흐름 도달불가 — 가입이 profiles 생성·예외적 DB 오류엔 일반 처리로 충분) · ⑫ 클라 토글/자동반영/에러 계층에 커밋된 회귀 테스트 부재(intent의 Verification이 수동 브라우저 E2E를 DoD로 지정·레포에 컴포넌트/E2E 하네스 자체가 house 관례상 없음·DB축 슬라이스는 이미 #118로 추적). 이 중 V1의 "실클릭 도달성" 하위주장은 코드로 기각 — 버튼은 `pointer-events-auto`인 최상위 후행 절대배치 형제라 구조적으로 눌린다(Playwright native click의 간헐 무동작은 hover-transition 액셔너빌리티 플레이키니스, 실사용자 차단 아님).

## Auto Run Result

Status: done
Story: Epic 10 / Story 10.5 — 찜 (wishlist)

**구현 요약:** 로그인 사용자가 매물을 찜(♡)해 모아볼 수 있게 했다. `wishlists(user_id, listing_id, created_at, PK(user_id,listing_id))` 테이블 + 본인 전용 RLS 3정책(select/insert/delete, `auth.uid()=user_id`, 로그인 전용·GRANT 미명시)을 `0018`로 신설했다. Epic 9가 만든 죽은 하트 자리표시자를 낙관적 토글 `WishButton`으로 살렸다 — 누르면 즉시 채워지고 서버 확정, 실패 시 롤백+조용한 토스트, 비로그인은 `/login?redirectedFrom=<경로+wish=id>`로 보냈다가 복귀 시 `?wish=` 자동 반영. "찜한 매물" 페이지(`/wishlist`, proxy 게이트 + 페이지 재확인)와 상단 "찜" 내비 진입점을 추가했고, 판매완료(sold)는 회색 비활성 타일+진입 차단으로 렌더한다. 찜 여부는 wire 필드가 아니라 사용자별 오버레이(`fetchWishedListingIds`)로 카드에 주입한다(계약 오염 방지).

**변경 파일:**
- `supabase/migrations/0018_wishlists.sql` -- **신규** wishlists 테이블 + 복합 PK + `listing_id` 인덱스 + 본인 RLS 3정책.
- `web/src/lib/wishlist.ts` -- **신규** `fetchWishedListingIds`·`fetchWishlist`·순수 `isWishedListingBlocked`(allowlist)·`buildWishedIdSet`.
- `web/src/components/listings/WishButton.tsx` -- **신규** 낙관적 토글·로그인 게이트·`?wish=` 자동반영·세션만료 게이트·`aria-pressed`·조용한 토스트.
- `web/src/components/listings/RemoveWishButton.tsx` -- **신규**(리뷰 P1) 판매완료 타일용 찜 해제 버튼(delete + `router.refresh()`).
- `web/src/app/(user)/wishlist/page.tsx` -- **신규** 찜 목록 페이지(최신순 단일 순회 렌더·on_sale 카드/판매완료 타일·빈 상태·에러).
- `web/src/components/listings/ListingCard.tsx` -- 하트 자리표시자를 `WishButton`으로 교체 + sibling props `wished`/`authed`(계약 미오염).
- `web/src/app/page.tsx` · `web/src/app/(user)/search/page.tsx` -- 로그인 시 찜 오버레이 주입.
- `web/src/proxy.ts` -- `PROTECTED_PREFIXES`에 `/wishlist`.
- `web/src/components/layout/AppHeader.tsx` -- 로그인 시 "찜" 링크.
- `web/src/lib/__tests__/wishlist.test.ts` -- **신규** 순수 술어·집합 로직 테스트(리뷰 후 8건).
- `docs/conventions.md` -- §6 이미지 축 소비처 목록에 `/wishlist` 등재(규칙7).
- `docs/tech-debt.md` -- `#89` 판단 완료(현행 유지, 근거) · `#116`(토스트 인프라) · `#117`(삭제 배지 도달불가 + cascade 실측) · `#118`(RLS/cascade 회귀 테스트 부재, 리뷰 defer).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-5` done + `last_updated` 갱신.

**리뷰 findings:** patch 5건 적용(P1~P5, 위 Triage Log) · defer 1(#118) · reject 8 · intent_gap 0 · bad_spec 0.
**Follow-up review 권고:** true (patched: high 0·medium 1·low 4 → 점수 3×1+1×4=7 ≥ 5).

**검증(오케스트레이터 직접 재실행):** `npm run test` 190/190 green(패치 후) · `npm run lint` exit 0 · `npm run build` exit 0(`/wishlist` 라우트 생성) · `check_migrations.py` 통과. P4 allowlist red→green 1회 실측(denylist로 되돌리면 신규 2건 red). RLS red-green 실측(로컬 Supabase, `set local role/request.jwt.claims`): A의 찜을 B로 조회=0행, `using(true)` 대조군=1행 누수 → rollback. cascade 실측: 매물 하드삭제 시 wishlists 1→0행(트랜잭션 rollback). 브라우저 E2E(buyer·seller 시드): 하트 토글·aria-pressed·라벨, 실패 롤백+토스트, 비로그인 게이트, `?wish=` 자동반영, 판매완료 회색 타일 제거·최신순, 세션만료 게이트, 390px D5 확인.

**잔여 리스크:** (1) 찜 RLS 격리·FK cascade의 회귀 보호가 커밋 테스트가 아니라 1회 수동 실측이다(레포에 RLS 임퍼소네이션 하네스 없음 — `#118`로 이월, 2-1과 동일 관례). (2) "삭제된 매물" 배지는 epic 지정 PK+cascade로 구조적 도달 불가 — sold만 회색 처리(`#117`, 트리거=스냅샷 컬럼 요구 시). (3) 공용 토스트 인프라 부재 — 첫 소비처라 로컬 transient로 최소 구현(`#116`, 트리거=2번째 소비처). (4) `?wish=` 자동반영은 대상이 복귀 화면에 렌더될 때만 성립(홈 프리뷰 절삭·페이지네이션 엣지에서 유실 가능 — reject, 페이지레벨 재설계 필요). (5) app(Flutter) 미러는 Epic 16(계약만 공유, 찜은 wire 필드 아님).

---

**Follow-up review pass (2026-07-22):** 이미 done인 스토리를 새 세션 4-리뷰어(adversarial·edge-case·verification-gap·intent-alignment)로 재검토. 결과 = **저심각도 주석 정정 1건만 패치**, 나머지 12건 reject, intent_gap/bad_spec 0 — 수렴 신호(patch 점수 1<5 → follow-up 재권고 false). 패치: `BlockedWishTile` 주석이 존재하지 않는 `pointer-events-none`을 있는 것처럼 서술하던 드리프트를 실제 동작대로 정정(코드 동작 무변경, 유지보수자 오도 방지). 재검증: `npm run test` 190/190 green · `npm run lint` clean · `npm run build` OK(`/wishlist` dynamic) · `check_migrations.py` 통과. intent-alignment 감사 결론: 구현이 방어 가능한 해석(RLS 수동 실측·판매완료 allowlist·세션만료→게이트)을 충실히 구현했고, 테스트가 순수술어 표면만 덮고 RLS/클라 상호작용 표면은 안 덮는 갭은 **은폐가 아니라 #117/#118로 공시·이월된 상태**임을 확인.
