---
title: 'Story 10.2 — 신뢰 뱃지 표시 + 면책 라벨'
type: 'feature'
created: '2026-07-22'
status: 'done'
baseline_revision: 'c5156d3'
final_revision: 'c7dfc24'  # follow-up 리뷰 패스 패치 2건 포함 커밋
review_loop_iteration: 0
followup_review_recommended: false
context:
  - '{project-root}/docs/conventions.md'
  - '{project-root}/_bmad-output/project-context.md'
  - '{project-root}/_bmad-output/implementation-artifacts/epic-10-context.md'
  - '{project-root}/docs/tech-debt.md'
  - '{project-root}/web/AGENTS.md'
warnings: ['oversized']
---

<intent-contract>

## Intent

**Problem:** Story 10.1이 신뢰속성 3컬럼(`accident_status`·`is_single_owner`·`is_non_smoker`)을 DB→api→web 카드까지 **흐르게** 했지만, 화면에는 아무것도 그려지지 않는다 — 카드의 신뢰 슬롯(②)과 상세의 신뢰 슬롯(①)은 값이 도달해도 빈 채다. 구매자는 "무사고" 여부를 한눈에 볼 수 없고, 본다 해도 그게 **판매자 자기신고**임을 알 방법이 없다(CM-C: 검증됨으로 오도 금지).

**Approach:** 웹 카드·상세에 신뢰 뱃지/중립 상태칩을 그리는 **단일 컴포넌트**(`TrustAttributes`)를 만들되, "판매자 제공 정보" 면책을 뱃지와 **구조적으로 한 몸**(같은 컴포넌트가 함께 emit — 뱃지만 있고 면책 빠지는 경로가 코드상 불가능, B9)으로 붙인다. 상세 select에 3컬럼을 로그인 분기로 추가하고(anon은 기존대로 미조회), 뱃지가 눈에 보이도록 데모 신뢰값을 시드에 심는다. **렌더는 웹만** — Flutter는 Epic 16.3 몫이다.

## Boundaries & Constraints

**Always:**
- **면책은 뱃지와 한 몸이다(B9).** 신뢰 뱃지/칩을 emit하는 코드 경로에는 반드시 "판매자 제공 정보" 면책이 **같은 컴포넌트 반환값 안에서** 함께 나온다. 두 조각을 호출부에서 조립하지 않는다(한쪽만 빠지는 경로가 생김).
- 색 규칙(§4·epic-10-context): `accident_status='무사고'`만 **초록 신뢰 뱃지**(`trust-green-bg`/`trust-green-ink`), `is_single_owner=true`·`is_non_smoker=true`도 초록 신뢰 칩. `'단순교환'`·`'사고'`는 **초록 아닌 가치중립 상태칩**(amber 절대 금지 — 가격/CTA 전용색). 초록 뱃지는 **색 단독이 아니라 색+아이콘(✓)+텍스트**로 표기(비색 신호 중복, 접근성).
- 계약-외 값 정규화(§4): `accident_status`가 3값 밖이거나 빈 문자열이면 `null`과 동일(미표시). `is_single_owner`/`is_non_smoker`는 `true`/`false`/`null` 3상태를 구분 — `null`·`false`를 "아님"으로 단정해 그리지 않는다(미표시).
- 미입력(전부 null) → 카드·상세 모두 **아무것도 렌더하지 않는다**(빈 높이·빈 테두리·빈 섹션 금지 — 상세는 신뢰 섹션 자체를 안 그린다).
- 상세 select 확장은 **로그인 분기**로 한다(`search/page.tsx`가 10.1에서 세운 패턴 그대로): 로그인 사용자만 3컬럼 조회, anon은 기존 컬럼만. anon `/listings/[id]`가 3컬럼을 조회하면 `42501`로 상세 전체가 죽는다(§9.3 — anon GRANT에 3컬럼 없음).
- 시드 데모값은 **additive**로만: 일부 매물에만 값을 심고 나머지는 NULL 유지(10.1의 "backfill 없음·NULL=제3상태" 원칙 보존). 무사고/1인소유/비흡연·단순교환·사고·NULL이 **네 가지 시각 상태로 다 보이게** 대표 분포로 심는다.
- 상세 신뢰 섹션 문구는 정확히: **"판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요."**(UX-DR19). 카드 면책은 짧게 **"판매자 제공 정보"**(11px 톤다운).
- web은 개조된 Next.js다(`web/AGENTS.md`) — 서버/클라이언트 컴포넌트 경계나 신규 파일 작성 전 `node_modules/next/dist/docs/` 해당 가이드를 본다.

**Block If:**
- anon에게도 신뢰 뱃지를 보여주려면 `0011` 이후 새 마이그레이션으로 anon에 3컬럼 `grant select`가 필요한데, §9.3(b)는 **새 컬럼 anon 노출을 델타 0이어도 사용자 승인 필수**로 못박는다. 이 무인 실행에는 승인 창구가 없다 → **GRANT를 넓히지 않는다**(위 로그인 분기가 확정 경로). 만약 스펙 해석이 "anon도 반드시 봐야 한다"로 강제된다면 승인이 필요하므로 HALT.

**Never:**
- **Flutter 앱 렌더를 하지 않는다**(Epic 16.3 범위 — `app/lib/**` 위젯 변경 금지). app 모델(`listing.dart`)은 10.1이 이미 파싱만 해 뒀고 그대로 둔다.
- **판매자 신뢰속성 입력 폼을 만들지 않는다**(대장 #108 — Epic 10 범위 밖). 값은 시드로만 공급한다.
- anon GRANT 마이그레이션을 만들지 않는다(위 Block If).
- 옵션 칩(슬롯 ⑥)·판매자 정보(슬롯 ④)·희소옵션은 건드리지 않는다(10.3/10.4/10.6).
- api `listing_cards.py`/`SELECT_COLUMNS`를 확장하지 않는다 — AI 카드 경로는 10.1이 이미 3컬럼을 실어 보내므로 `ListingCard` 렌더만으로 뱃지가 따라온다(대장 #110 트리거 미해당).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 무사고 | `accident_status='무사고'` | 초록 뱃지(✓ + "무사고") + 면책 한 몸 | 에러 없음 |
| 단순교환 | `accident_status='단순교환'` | 중립 상태칩("단순교환", 초록·amber 아님) + 면책 | 에러 없음 |
| 사고 | `accident_status='사고'` | 중립 상태칩("사고") + 면책 | 에러 없음 |
| 1인소유 | `is_single_owner=true` | 초록 신뢰 칩(✓ + "1인소유") + 면책 | 에러 없음 |
| bool 미상 | `is_single_owner=null` 또는 `false` | 그 칩 **미표시**(‘아님’으로 단정 안 함) | 에러 없음 |
| 미입력 | 3필드 전부 null | 카드·상세 **아무것도 렌더 안 함**(빈 섹션 없음) | 에러 없음 |
| 계약-외 값 | `accident_status='외판교환'` 또는 `''` | null과 동일(미표시) | 에러 없음 |
| 혼합 | `accident_status='사고'` + `is_non_smoker=true` | 중립칩("사고") + 초록칩("비흡연") + 면책 1개 | 에러 없음 |
| anon 상세 | 비로그인 `/listings/[id]` | 3컬럼 미조회 → 신뢰 섹션 미표시, 상세 정상 렌더 | `42501` 발생 안 함 |
| 면책 결속 | 뱃지/칩이 뜨는 모든 경로 | "판매자 제공 정보" 면책이 **항상** 동반(뱃지-only 경로 없음) | 에러 없음 |

</intent-contract>

## Code Map

- `web/src/app/globals.css:28-29,54-55,78-79` -- `--trust-green-bg`/`--trust-green-ink`(라이트/다크, AA 5.51:1) + Tailwind 유틸 매핑(`bg-trust-green-bg`·`text-trust-green-ink`). 신규 색 정의 금지 — 이걸 쓴다.
- `web/src/components/listings/ListingCard.tsx:27-29,44-45` -- `ListingCardData`에 3필드 **이미 존재**(타입 변경 불필요). 44-45행 "② 신뢰속성 행 슬롯"이 카드 렌더 위치.
- `web/src/app/(user)/listings/[id]/page.tsx:35-55,118-123,223` -- `ListingDetail` 타입(3필드 **없음** — 추가 대상) + 상세 select 문자열(3컬럼 없음) + 슬롯 ①("신뢰정보 — Epic 10.2가 채울 빈 슬롯"). `user`는 이미 상단(101-103행)에 있다 → 로그인 분기에 사용.
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx:17-34,47-54,78` -- `ListingDetailSectionsData`(3필드 없음), `Section`/`Field` 셸(재사용), 47-54 `Field`의 `truncate`에 `title` 없음(#79 ③), 78행은 구식 `accident_free` "사고이력" Field(**그대로 둔다** — 신뢰 뱃지와 별개 필드다).
- `web/src/app/(user)/search/page.tsx` -- 상세 select 로그인 분기의 **참조 패턴**(10.1이 `user ? 3컬럼 : 생략`으로 구현). 새로 손대지 않고 패턴만 따른다.
- `web/src/components/listings/ListingGallery.tsx:47-53,78-96,166-197` -- #79 ①(화살표 `go()`가 index만 바꾸고 aria-live 고지 없음)·②(썸네일 스트립 `overflow-x-auto`에 `scrollIntoView` 없음). 상세 신뢰 슬롯을 여는 김에 함께 닫는다.
- `supabase/seed.sql:196-479` -- 프로덕션/fresh DB 단일 시드 출처(seller별 delete 후 재삽입, 재실행 안전). 데모 신뢰값의 **정본** 자리.
- `supabase/seed-local/` · `scripts/seed-local.sh` · `data/listings.json` -- 로컬 fresh DB는 이 경로로 채워진다(`on conflict do nothing`, 103건 전부 신뢰속성 NULL). 로컬 관측·검증용 멱등 시드 자리.
- `supabase/migrations/0011_listings_anon_select.sql` · `docs/conventions.md` §9.3 -- anon GRANT 화이트리스트·승인 규칙(3컬럼 없음 → anon 미조회 근거).
- `docs/conventions.md` §4/§4.1 -- ListingCard 계약·렌더 정규화 규칙(3값 밖→미표시, bool 3상태) + 락스텝 지점(상세 select 포함).
- `docs/tech-debt.md` #79(라인 1063)·#108(1379)·#109(1386)·#111(1403) -- 이 스토리가 닫거나(#79) 갱신하는(#108/#109/#111) 대장 항목.

## Tasks & Acceptance

**Execution:**
- `web/src/components/listings/TrustAttributes.tsx` -- **신규**. `hasTrustAttributes(listing)` + `TrustAttributes({listing, variant})` export. 표시할 요소 계산(무사고→초록 ✓뱃지, `is_single_owner`/`is_non_smoker` true→초록 ✓칩, 단순교환/사고→중립칩; 계약-외·null·false는 제외). 요소 0개면 `null` 반환. ≥1개면 칩들 + 면책을 **같은 반환값**으로 emit: `variant='card'`는 짧은 "판매자 제공 정보"(11px, `text-ink-muted`), `variant='detail'`은 전체 문구(UX-DR19). 상태 없는(서버 렌더 가능) 컴포넌트 -- 면책-뱃지 결속을 한 파일에 가둬 B9로 못 어기게.
- `web/src/components/listings/ListingCard.tsx` -- 슬롯 ②(44-45행)에 `<TrustAttributes variant="card" listing={listing} />` 삽입 -- 카드에 신뢰 행을 그린다(값 없으면 컴포넌트가 null이라 슬롯은 빈 채, AC1 유지). 타입·다른 슬롯 불변.
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` -- (a) `ListingDetailSectionsData`에 `accident_status?`·`is_single_owner?`·`is_non_smoker?` 추가, (b) `TrustInfoSection({listing})` export: `!hasTrustAttributes`면 `null`, 아니면 `<Section title="신뢰정보">`에 `<TrustAttributes variant="detail" .../>`, (c) `Field`의 값 `<span>`에 `title={value}` 추가(#79 ③) -- 상세 신뢰 섹션 + 잘린 값 복구.
- `web/src/app/(user)/listings/[id]/page.tsx` -- (a) `ListingDetail`에 3필드 추가, (b) select 문자열을 **로그인 분기**(`user`면 `, accident_status, is_single_owner, is_non_smoker` 덧붙임; anon은 생략), (c) 슬롯 ①(223행)에 `<TrustInfoSection listing={listing} />` 삽입 -- 값이 상세까지 오게 + 신뢰 섹션 배치. anon 42501 회귀 없음.
- `web/src/components/listings/ListingGallery.tsx` -- #79 ①: 시각적으로 숨긴 `aria-live="polite"` 영역에 현재 사진("N / 총 M")을 담아 화살표 이동이 스크린리더에 고지되게. #79 ②: 활성 썸네일에 ref + index 변경 시 `scrollIntoView({block:'nearest',inline:'nearest'})`로 선택 테두리가 스트립 안에 남게 -- 갤러리 접근성 3종 중 2종(③은 위 Field).
- `web/src/components/listings/__tests__/TrustAttributes.test.tsx` (또는 리포 vitest 관례 위치) -- **신규**. I/O 매트릭스 전 케이스 + **면책 결속 red/green**: 뱃지가 뜨는 입력에서 "판매자 제공 정보"/전체 문구가 **항상 함께** 렌더되는지 단언, 그리고 면책 emit을 일부러 제거하면 이 테스트가 red가 되는지 실측(원복 green) -- "있는지"가 아니라 "결속되는지"를 잡는다. 검사가 **안 보는 것**(하이드레이션 전 시점, 스크린리더 실낭독 = E2E-only #106)을 테스트 옆 주석에 실측 근거로 적는다.
- `supabase/seed.sql` -- 시드된 매물 중 **대표 소수**(예: 무사고+1인소유+비흡연 2건, 단순교환 1건, 사고 1건)에 신뢰값을 additive로 심고 나머지는 NULL 유지 -- fresh/prod 데모에서 네 시각 상태가 다 보이게(정본). 어느 매물에 무엇을 심었는지 주석 1줄.
- `supabase/seed-local/03_trust_demo.sql` -- **신규**. 위와 같은 매물 id들에 대한 **멱등 UPDATE**(`update ... where id in (...)`, delete 없음 — #89 파괴 재현 안 함). `scripts/seed-local.sh` 실행 순서에 편입 -- 로컬 fresh·기존 DB 양쪽에서 뱃지가 보이고, 이 파일이 검증 시 관측용으로도 쓰인다.
- `docs/tech-debt.md` -- **#79를 `✅ 해소`로 닫는다**(3종 각각 어떻게 닫았는지 실측 1줄). **#108·#109·#111 갱신**: #108=(a) 시드 데모값 선택·폼 UI는 Epic 10 밖 확정 기록 / #109=상세 경로도 로그인 분기로 처리했고 anon 뱃지는 GRANT 승인 대기로 **여전히 open**(트리거·근거 갱신) / #111=상세 select 신규 추가·anon 분기 2곳(search+상세)으로 확대됐으나 자동 가드는 계속 defer(트리거 갱신) -- 대장은 하나, 미룬 것은 트리거와 함께(B8).
- `_bmad-output/implementation-artifacts/sprint-status.yaml` -- `10-2-...: done`, `last_updated`에 한 줄 요약 -- 상태 정합.

**Acceptance Criteria:**
- Given `accident_status='무사고'`인 매물, when 카드·상세를 렌더하면, then 초록 신뢰 뱃지(색+✓+"무사고")가 뜨고 "판매자 제공 정보" 면책이 **같은 블록**에 함께 뜬다. amber는 어디에도 쓰지 않는다.
- Given `accident_status='단순교환'`(또는 `'사고'`), when 렌더하면, then **초록이 아닌** 가치중립 상태칩으로 표시되고(검증됨으로 오도 안 함) 면책이 동반된다.
- Given 3필드 전부 null(또는 계약-외 값)인 매물, when 렌더하면, then 카드 신뢰 행·상세 신뢰 섹션이 **둘 다 그려지지 않는다**(빈 잉크 없음). `is_single_owner=false`는 "1인 아님"으로 그리지 않는다.
- Given 상세 신뢰 섹션이 뜨는 매물, when 렌더하면, then "판매자가 직접 입력한 정보예요. 차장님이 검증한 내용은 아니니, 계약 전 꼭 직접 확인하세요." 문구가 표시된다.
- Given **비로그인** 방문자, when `/listings/[id]`를 열면, then 상세가 42501 없이 정상 렌더되고 신뢰 섹션만 미표시다(anon은 3컬럼 미조회).
- Given 면책 결속 테스트, when 면책 emit을 제거하면, then 테스트가 **red**가 되고(잡는 걸 증명) 원복하면 green이다.
- Given 상세 갤러리, when 화살표로 사진을 넘기면, then 변경이 `aria-live`로 고지되고 선택 썸네일이 스트립 안으로 스크롤되며, 좁은 화면에서 잘린 상세 값은 `title`로 복구된다(대장 #79 3종).
- Given 시드된 로컬 DB, when `/search`·`/listings/[id]`를 로그인해 열면, then 네 시각 상태(초록 뱃지·중립칩·비흡연/1인소유 칩·미표시)가 실제로 눈에 구분돼 보인다.
- Given 대장, when 작업이 끝나면, then #79가 닫히고 #108/#109/#111이 트리거와 함께 갱신돼 있다.

## Spec Change Log

## Review Triage Log

### 2026-07-22 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 5: (high 0, medium 2, low 3)
- defer: 1: (high 0, medium 0, low 1)
- reject: 7: (high 0, medium 0, low 7)
- addressed_findings:
  - `[medium]` `[patch]` P1 — 면책-뱃지 결속이 순수함수(`getTrustDisplay`) 반환값에서만 증명되고 **렌더 층은 비어 있었다**: 컴포넌트가 뱃지와 면책을 별개 JSX 노드로 그려, 면책 `<span>`/`<p>`를 지워도 `getTrustDisplay`가 그대로면 테스트가 초록인 채 뱃지-only 화면이 나간다(스토리 헤드라인 AC "면책 없이 만들어 red 확인"이 이름한 표면에서 미강제). 검증갭·의도정합 두 레인이 수렴. **잡음 방식:** `TrustAttributes` 컴포넌트를 node vitest에서 함수로 직접 호출(무상태·훅 없음)해 반환된 React 엘리먼트 트리를 순회, 뱃지 라벨이 있으면 면책 문자열도 있음을 card·detail 양쪽 전 케이스로 단언(신규 12건). **red/green 실측:** 면책 JSX 삭제 → 신규 12건 red / 나머지 122 green → 복원 시 134 green. 컴포넌트 헤더의 "코드상 존재할 수 없다" 주장을 실제 보장 범위로 재조정.
  - `[medium]` `[patch]` P2 — `seed-local/03_trust_demo.sql`가 `status` 미필터로 뱃지를 **sold 매물**(로컬 스냅샷 8건)에 심을 수 있어 구매자 화면(`on_sale`만 노출)에 안 보이는 상태가 나올 수 있었다(AC9 4상태 관측 무력화). 세 SELECT에 `status='on_sale'` 추가 + on_sale `accident_free` 양측 2건 미만이면 `RAISE EXCEPTION`(조용한 0행 시딩을 시끄럽게). 멱등·가드 발화 실측(롤백).
  - `[low]` `[patch]` P3 — `seed.sql` 신뢰값 UPDATE가 모델명/연식 드리프트 시 조용히 0행 no-op. 각 UPDATE 뒤 `GET DIAGNOSTICS ROW_COUNT`가 1이 아니면 `RAISE EXCEPTION`. 정상·드리프트 양 경로 실측(롤백).
  - `[low]` `[patch]` P4 — `ListingGallery`의 `scrollIntoView` effect가 초기 마운트(index=0)에도 발화해 갤러리가 접힌 화면에서 뷰포트를 썸네일 스트립으로 끌어내릴 수 있었다. `hasMountedRef`로 첫 실행 스킵(실제 index 변경에만 발화). 390×700 실측(초기 `scrollY=0`, 이후 화살표 이동은 정상 스크롤).
  - `[low]` `[patch]` P5 — #79③ `title`은 마우스 hover에서만 뜨는데 주석·대장 #79 종결문이 "hover·focus·tap 어느 쪽으로든"으로 과장. 실제 범위로 정정(hover 복구 + truncate는 CSS-시각 전용이라 스크린리더는 전문을 읽음; `title`은 키보드 시각복구를 주지 않음). 새 포커스 장치 추가 없음(B4 정확성).

4개 리뷰 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 돌렸다(전부 opus, 무맥락 새 세션). **intent_gap·bad_spec 0** — 구현 자체는 스펙에 충실하고, 표면화한 것은 검증 견고성·시드 관측성·정확성 결함이었다.

- **defer 1건 → `docs/tech-debt.md` #112 신규 등재**(동결된 `deferred-work.md` 아님, 프로젝트 규칙 우선): 상세에 사고 정보가 `accident_status`(뱃지)·`accident_free`('사고이력' 행) 두 컬럼으로 교차검증 없이 나란히 뜬다. **지금은 무해**(시드가 일관, 쓰기 경로 #108 부재라 어긋난 데이터를 만들 자리가 없음). 트리거: #108 해소 또는 Epic 10.7.
- **reject 7건**(전부 low): 사고/단순교환이 같은 중립칩 스타일(에픽이 "가치중립 상태칩"으로 명시한 의도) · 카드 면책 11px 반복(에픽이 "한 몸·11px 톤다운"으로 명시) · aria-live가 위치만 고지(사진별 개별 캡션이 없어 위치 고지가 적절) · #111 4번째 select 손복사(이미 대장 #111에 이번 스토리가 갱신·등재) · anon 42501 자동검증 부재(#106/#111이 담는 E2E 공백, 수동 실측 완료) · anon 정규화가 `!user` 분기(두 분기가 같은 `user`에 묶여 현재 어긋날 수 없음, 엣지케이스 레인 확인) · seed-local 차량이 seed.sql과 다른 차종(일관성 축 accident_free↔accident_status는 보존, 산문 정합은 스코프 밖).

### 2026-07-22 — Review pass (follow-up)
- intent_gap: 0
- bad_spec: 0
- patch: 2: (high 0, medium 0, low 2)
- defer: 0
- reject: 8: (high 0, medium 0, low 8)
- addressed_findings:
  - `[low]` `[patch]` 갤러리 P4 마운트 가드가 StrictMode(dev)를 새어나갔다: `hasMountedRef`(useRef)가 StrictMode의 setup→cleanup→setup 재마운트를 가로질러 살아남아, 두 번째 setup에서 index=0인데도 `scrollIntoView`를 쏴 **P4가 없앤 스크롤 점프가 dev에서 되살아났다**(적대·엣지케이스 두 레인 수렴). **잡음 방식:** 마운트 1회 스킵 플래그 대신 **직전 index**(`prevIndexRef`)를 저장해 값이 실제로 바뀐 이동에만 스크롤 — 재실행은 prev===index라 조용히 건너뛴다(덤으로 index=0으로 되돌아오는 이동도 정상 스크롤). prod엔 StrictMode 이중호출이 없어 사용자 영향은 dev 한정(severity low). tsc·build 통과로 검증(이 클라이언트 컴포넌트는 node vitest로 못 돌린다 — #106).
  - `[low]` `[patch]` 렌더 결속 테스트가 뱃지 라벨·면책 텍스트만 보고 **초록 톤의 비색 신호(✓·초록 className)는 안 봤다**(검증갭 레인): 컴포넌트에서 `✓`(<span aria-hidden>)를 지우거나 `bg-trust-green-bg`→중립 className으로 바꿔도 라벨·면책이 멀쩡해 134 green이 유지 — 초록 뱃지가 '색만'으로 표기되는 §4 비색 신호 위반이 조용히 통과할 수 있었다(전 패스 P1의 면책 결속과 같은 계열의 빈틈). **잡음 방식:** `collectClassNames` 추가 + 톤 결속 5건(초록=✓·trust-green 동반, 중립=✓·trust-green 부재, 혼합=공존) 신설. **red/green 실측:** ✓ 노드 삭제 → 초록 3건 red / 나머지 green → 복원; 초록 className→중립 스왑 → trust-green 단언 3건 red → 복원 시 **139 green**(134→+5).

이 follow-up 패스는 전 패스가 `followup_review_recommended: true`(P1이 스토리 헤드라인 AC와 직결)로 남긴 권고에 따른 재리뷰다. 4개 레인(적대·엣지케이스·검증갭·의도정합)을 병렬로 재실행(전부 opus, 무맥락 새 세션). **intent_gap·bad_spec 0** — 구현은 여전히 스펙에 충실하고, 이번에 표면화한 것도 P1과 같은 성격의 검증 견고성 결함 2건뿐이었다.

- **reject 8건**(전부 low): (1) AI 챗 카드가 뱃지를 빠뜨린다 — **거짓양성**: api `SELECT_COLUMNS`(listing_cards.py:34, 10.1)가 3컬럼을 싣고 `rows_to_cards`가 ListingCard로 매핑하며, web `resolveCardImage`가 `...card` 스프레드로 그 필드를 보존해 `<ListingCard>`가 뱃지를 그린다(스펙 boundary 가정 실측 확인). (2) anon/로그인 select 분기 자동검증 부재 + authenticated GRANT 취약 — 이미 대장 #111/#106이 담는 E2E 공백이고 전 패스가 동일 지적을 reject; authenticated는 테이블 단위 GRANT라 현재 정상, 미래 조임은 가정. (3) 신뢰상태 화이트리스트 3곳 중복 — 계약-외 값→미표시는 §4 의도된 정규화, 4번째 값은 가정. (4) 시드가 단독/혼합 bool 칩을 안 심음 — AC9의 네 시각 상태(초록 뱃지·중립칩·비흡연/1인소유 칩·미표시)는 전부 시드돼 보이며, 추가 조합은 의도가 요구하지 않음. (5) 카드 면책 줄바꿈에 따른 카드 높이 편차 — cosmetic, 에픽이 명시한 "같은 행에 나란히" 레이아웃. (6) 안 잘린 값에도 `title` 부착 — nitpick, 전 패스 P5가 이미 범위 정정. (7) 갤러리 a11y 자동검증 부재 — 이미 #106 E2E-only 공백. (8) 시드 가드 CI 미실행 — 리포 표준 특성(가드는 진짜 런타임 검사, 수동 psql로 실측 완료).

## Design Notes

**면책-뱃지 결속을 "구조"로 강제한다(B9).** AC의 핵심은 "뱃지 있으면 면책도 반드시"인데, 이를 주석·규칙이 아니라 **한 컴포넌트가 둘을 함께 반환**하는 형태로 만든다. 호출부(카드·상세)는 `<TrustAttributes .../>` 하나만 꽂으므로, 면책만 빼는 코드 경로가 **문법적으로 존재할 수 없다**. 결속 테스트는 그 컴포넌트를 렌더해 "뱃지 텍스트가 있으면 면책 텍스트도 있다"를 단언하고, emit을 지웠을 때 red를 실측해 검사가 **작동**함을 증명한다.

**세 개의 초록, 하나의 중립.** 신뢰속성은 넷이지만 색은 둘뿐이다 — 긍정 자기신고(무사고·1인소유·비흡연)는 초록 신뢰 표기, 사고이력의 부정/중립값(단순교환·사고)은 **가치중립 상태칩**(초록도 amber도 아님). CM-C가 요구하는 "검증됨으로 오도 금지"는 색으로 지켜진다: 초록은 "판매자가 좋다고 신고", 중립칩은 "판매자가 사실을 신고", 둘 다 면책이 "우리가 검증한 게 아님"을 말한다. 기존 상세의 `accident_free` "사고이력" Field(78행)는 **별개 필드라 그대로 둔다** — 신뢰 섹션과 차량정보 섹션이 각자의 필드를 그린다.

**anon은 왜 못 보나(#109, 의도된 한계).** `/search`·`/listings/[id]`는 anon 열람 경로(§8)지만, anon은 `0011`이 컬럼 단위로 허용한 목록만 읽는다 — 3컬럼은 거기 없다. §9.3(b)는 이 목록을 넓히는 GRANT를 **델타 0이어도 사용자 승인 필수**로 못박고, 이 실행엔 승인 창구가 없다. 그래서 10.1이 `search`에서 쓴 로그인 분기를 상세에도 그대로 적용한다: **로그인 사용자만 뱃지를 본다.** anon 노출은 승인이 열리는 시점까지 #109에 open으로 남긴다 — 임의로 넓히지 않는다.

**뱃지를 볼 값이 없다(#108, 시드로 해결).** 기존 100건·시드 103건 전부 신뢰속성 NULL이라, 렌더를 붙여도 화면엔 뜰 게 없다. 등록 폼에 입력 UI를 넣는 건 Epic 10 범위 밖(#108)이므로 **(a) 데모 시드값**을 택한다: 정본(`seed.sql`)과 로컬 멱등 시드(`03_trust_demo.sql`)에 대표 분포를 심어, fresh·프로덕션·로컬 어디서든 네 상태가 보이게 한다. backfill이 아니라 **일부 매물만** 채우므로 10.1의 "NULL=제3상태" 원칙과 충돌하지 않는다.

## Verification

**Commands:**
- `cd web && npm run lint && npx tsc --noEmit && npm test` -- expected: 린트·타입 통과, vitest 통과(신규 `TrustAttributes` 테스트 포함).
- `cd web && npm run build` -- expected: 빌드 성공(상세 select 로그인 분기·신규 컴포넌트가 서버 컴포넌트 타입과 정합).
- **면책 결속 red/green 실측:** `TrustAttributes`에서 면책 emit을 임시 제거 → `npm test`가 해당 테스트로 **red** → 원복 → **green**. 두 출력을 기록한다("만들었다"가 아니라 "잡는다").
- `psql "postgresql://postgres:postgres@127.0.0.1:55322/postgres" -f supabase/seed-local/03_trust_demo.sql` -- expected: 멱등 UPDATE 성공, 대표 매물에 네 상태 분포가 실제로 들어감(`select id, accident_status, is_single_owner, is_non_smoker from listings where id in (...);`로 확인).

**Manual checks (재보기 전엔 선언하지 않는다, B4):**
- 로컬 dev(`cd web && npm run dev`, 3000) + 로컬 Supabase(55322) 기동 후, **로그인 상태**로 `/search`와 시드한 매물의 `/listings/[id]`를 브라우저(MCP)로 열어: 초록 뱃지(✓+텍스트)·중립 상태칩·비흡연/1인소유 칩·미표시(전부 null 매물)가 눈에 **구분돼** 보이는지, 면책이 뱃지와 붙어 있는지, 상세 문구가 뜨는지 스크린샷으로 확인.
- **비로그인**으로 같은 상세를 열어 42501 없이 정상 렌더되고 신뢰 섹션만 사라지는지 확인.
- 갤러리(#79): 좁은 폭(태블릿)에서 화살표로 8번째 사진까지 이동해 선택 썸네일이 스트립 안에 스크롤돼 남는지, 긴 값이 `title`로 복구되는지 확인.

## Auto Run Result

Status: done

**구현 요약.** 웹 카드·상세에 신뢰 뱃지/중립 상태칩 + "판매자 제공 정보" 면책을 그리는 단일 컴포넌트 `TrustAttributes`를 만들었다. 면책과 뱃지를 **한 컴포넌트가 같은 반환값으로 emit**해 뱃지-only 경로를 구조로 막는다(B9). `무사고`=초록 ✓뱃지, `1인소유`/`비흡연`(true)=초록 ✓칩, `단순교환`/`사고`=초록 아닌 가치중립 상태칩, 미입력/계약-외 값/`false`/`null`=미표시. 상세 select는 `search/page.tsx`가 세운 로그인 분기를 그대로 상세에도 적용해 anon 42501 회귀 없이 뱃지만 열었다(GRANT는 §9.3(b) 승인 없이 넓히지 않음 — 대장 #109 갱신). 뱃지가 눈에 보이도록 `seed.sql`·`seed-local/03_trust_demo.sql`에 대표 4상태를 additive 시드했다. 대장 #79(갤러리 접근성 3종) 해소. **Flutter 렌더는 Epic 16.3 범위라 손대지 않았다.**

**변경 파일.**
- `web/src/components/listings/TrustAttributes.tsx` (신규) — 뱃지·칩·면책을 한 몸으로 emit(`getTrustDisplay` 결속 + 컴포넌트 렌더).
- `web/src/components/listings/TrustAttributes.test.ts` (신규) — I/O 매트릭스 + 면책 결속을 **데이터 층(getTrustDisplay)·렌더 층(컴포넌트 엘리먼트 트리)** 두 겹으로 단언(코드리뷰 P1로 렌더 층 12건 추가).
- `web/src/app/(user)/listings/[id]/ListingDetailSections.tsx` — `TrustInfoSection`(신뢰정보 섹션) 신설 + 상세 타입 3필드 + `Field`에 `title`(#79③).
- `web/src/app/(user)/listings/[id]/page.tsx` — 상세 select 로그인 분기 + anon null 정규화 + 슬롯 ① 배선.
- `web/src/components/listings/ListingCard.tsx` — 슬롯 ②에 `<TrustAttributes variant="card">`.
- `web/src/components/listings/ListingGallery.tsx` — aria-live 고지 + 썸네일 `scrollIntoView`(마운트 스킵, #79①②).
- `supabase/seed.sql` · `supabase/seed-local/03_trust_demo.sql`(신규) · `scripts/seed-local.sh` — 대표 4상태 additive 시드(멱등, on_sale 한정·0행 가드).
- `docs/tech-debt.md` — #79 해소, #108(판정 (a))·#109(범위 확장·open 유지)·#111(4번째 소비처 갱신) 갱신, #112 신규 등재.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` — 10.2 done.

**리뷰 결과.** patch 5건(medium 2·low 3) / defer 1건(대장 #112) / reject 7건 / intent_gap·bad_spec 0건.

**후속 리뷰 권고.** `true` — 이번 패스 패치 점수 3×medium 2 + 1×low 3 = 9 ≥ 5(high 0). P1(면책 결속의 렌더 층 미검증)이 스토리 헤드라인 AC와 직결돼 한 번 더 볼 값이 있다.

**검증(직접 실행·관찰).**
- `cd web && npm run lint`·`npx tsc --noEmit`·`npm test`·`npm run build` — 전부 통과, 테스트 **134 green**(원 구현 121 → 코드리뷰 P1로 +13).
- **P1 면책 결속 red/green 실측:** 컴포넌트 JSX에서 면책 노드 삭제 → 렌더 층 테스트 **12 red** / 122 green → 복원 시 **134 green**. 데이터 층만 보던 원 테스트가 렌더 층 삭제를 놓쳤음을 확인하고 그 구멍을 닫았다("만들었다"가 아니라 "잡는다").
- **시드 실측:** `03_trust_demo.sql` 로컬 psql ×2 멱등(2/1/1), 4상태 전부 `on_sale`, sold 0건에 신뢰값; on_sale 부족 시 가드 발화(롤백). `seed.sql`은 트랜잭션+ROLLBACK으로 4건 UPDATE 및 드리프트 가드 발화 확인(부작용 없음).
- **수동 E2E(브라우저 MCP):** 로그인 상태 상세에 초록 뱃지 3종 + 전체 면책 문구, 로그아웃 상세는 200·42501 없음·신뢰 섹션만 사라짐, `/search` 카드 뱃지 + 짧은 면책, 신뢰값 없는 매물은 빈 섹션·빈 행 없음, `단순교환` 매물은 초록 아닌 중립칩. 갤러리는 390px에서 초기 `scrollY=0`·이동 시 썸네일 스트립 스크롤 확인(클릭이 React 핸들러에 안 닿는 대장 #88 환경 제약은 onClick prop 직접 구동으로 우회).

**잔여 위험.**
1. **anon은 신뢰 뱃지를 못 본다**(대장 #109, 의도적). §9.3(b) GRANT 승인 창구가 무인 실행에 없어 로그인 사용자에게만 뱃지가 보인다. `seed.sql`에 값이 있어도 배포 데모의 **비로그인 방문자에게는 안 보인다** — anon 노출은 승인 시점까지 #109에 open.
2. **신뢰속성 쓰기 경로 없음**(대장 #108). 신규 등록 매물은 계속 NULL — 시드 매물에서만 뱃지가 보인다. 폼 UI는 Epic 10 밖(판정 (a)).
3. **select 락스텝 자동 가드 부재**(대장 #111). anon 분기가 목록+상세 2곳에 손으로 쓰여 있고 이를 강제하는 검사가 없다 — 화면 렌더 검증이 E2E-only(#106)라 이번에 만들지 않았다.
4. **사고 정보 이중 표시**(대장 #112). 상세가 `accident_status` 뱃지와 `accident_free` '사고이력' 행을 둘 다 그린다 — 지금은 시드가 일관돼 무해, 쓰기 경로가 생기면 자기모순 위험.
5. **브랜치**: 이 작업은 `test/bmad-loop` 브랜치다(B3의 `develop` 흐름과 다름). 반영하려면 develop으로 옮기는 판단이 필요하다.

---

### Follow-up 리뷰 패스 (2026-07-22)

전 패스가 `followup_review_recommended: true`로 남긴 권고에 따라 4개 레인을 재실행했다. **intent_gap·bad_spec 0**, patch 2건(둘 다 low)·reject 8건·defer 0.

**패치 2건.**
- `web/src/components/listings/ListingGallery.tsx` — 갤러리 P4 마운트 가드가 StrictMode(dev) 재마운트를 새어나가 스크롤 점프를 되살리던 결함을, "직전 index 비교"(`prevIndexRef`)로 교체해 값이 실제 바뀐 이동에만 스크롤하게 고쳤다. prod엔 영향 없음(StrictMode 이중호출 없음).
- `web/src/components/listings/TrustAttributes.test.ts` — 렌더 결속 테스트가 초록 톤의 비색 신호(✓·`trust-green` className)를 안 보던 빈틈에 톤 결속 5건을 추가(전 패스 P1의 면책 결속과 같은 계열). `collectClassNames` 헬퍼 신설.

**검증(직접 실행·관찰).**
- `npm run lint`·`npx tsc --noEmit`·`npm test`·`npm run build` — 전부 통과, 테스트 **139 green**(134→+5).
- **톤 결속 red/green 실측:** 컴포넌트에서 `✓` 노드 삭제 → 초록 케이스 **3 red**/136 green → 복원; `bg-trust-green-bg` 초록 className을 중립으로 스왑 → `trust-green` 단언 **3 red** → 복원 시 **139 green**. 두 회귀 모드(✓ 삭제·톤 스왑)를 각각 잡는지 확인("만들었다"가 아니라 "잡는다").
- 갤러리 패치는 클라이언트 컴포넌트라 node vitest로 못 돌린다(#106) — tsc·build 통과 + React 표준 패턴 검토로 검증(수동 브라우저 E2E는 #106 범위).

**후속 리뷰 권고.** `false` — 이번 패스 patch 점수 = 3×medium(0) + 1×low(2) = 2 < 5, high 0. P1 계열 검증 견고성 결함을 닫아 수렴했다.

**AI 카드 뱃지(전 패스 이후 확인).** 적대 레인이 "AI 챗 카드에 뱃지가 안 뜬다"고 지적했으나 거짓양성으로 확인 — api `SELECT_COLUMNS`가 3컬럼을 싣고(10.1) web `resolveCardImage`가 스프레드로 보존해 뱃지가 그려진다. 스펙 boundary의 "AI 카드 경로는 10.1이 이미 실어 보낸다" 가정이 실측으로 맞았다.
