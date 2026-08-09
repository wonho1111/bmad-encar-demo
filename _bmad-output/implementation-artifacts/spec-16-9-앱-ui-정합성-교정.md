---
title: '16.9 앱 UI 정합성 교정'
type: 'bugfix'
created: '2026-08-09'
status: 'done'
baseline_revision: 'd86f6a9d700876d43f1dfd6d8dc0297c675507be'
final_revision: '555962b86ab92a98c4c08c1ef17c5a2234923584'
review_loop_iteration: 0
followup_review_recommended: true
context:
  - '{project-root}/_bmad-output/planning-artifacts/ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md'
  - '{project-root}/web/src/lib/options.ts'
  - '{project-root}/docs/conventions.md'
warnings: ['oversized', 'multiple-goals']
---

<intent-contract>

## Intent

**Problem:** 실기기 화면이 확정 시각 스파인(`DESIGN.md`)·목업과 눈에 띄게 다르다(DW-755·759·760·735) — 앱바가 흰색이고 히어로가 여백 있는 카드로 떠 있으며(스파인은 상태바→앱바→히어로가 하나의 petrol 면이길 요구), 상단바에 브랜드 로고가 없고, 매물 카드는 가격이 강조되지 않고 옵션 칩이 없으며 신뢰속성이 사진 위에 겹쳐 있고, 매물 상세엔 하단 고정 문의 바가 없어 스크롤을 끝까지 내려야 문의할 수 있다. 기존 위젯 테스트는 순서·개수만 봐서 이 축들(폭·색·크기·요소 유무)을 전부 놓쳤다.

**Approach:** 네 항목(홈 앱바+히어로 연속면, 히어로 배경 요소+탐색박스 제거, 매물 카드 재정렬, 상세 하단 고정 바)을 한 커밋으로 교정한다 — 전부 홈 화면 최상단·카드·상세 CTA라는 한 덩어리라 따로 고치면 중간 상태가 어색하다. 정본은 목업이 아니라 `DESIGN.md`(스파인)이고, 이 스토리가 명시한 축(신뢰속성 위치·옵션 칩 스타일)에 한해 스파인이 현재 웹 코드보다 우선한다(웹은 건드리지 않는다 — 이 편차의 웹 쪽 해소는 별도 판단).

## Boundaries & Constraints

**Always:**
- 히어로(`_AiSearchCta`)는 화면 폭을 꽉 채우는 밴드가 된다(좌우 여백 0) — 홈 탭 AppBar와 같은 배경색으로 이어져 경계가 안 보인다. 아래 두 모서리만 둥글게(위는 각짐, AppBar와 맞닿음).
- 히어로 배경에 petrol·amber 톤 글로우/메시(우상단, 은은하게) + 대형 차 실루엣 라인아트(우측 가장자리로 흐릿하게, opacity 낮게, 헤드라인·입력창·제안칩을 침범하지 않음)를 추가한다.
- 히어로 바로 아래의 `_SearchCta`("어떤 차를 찾고 있나요?" 박스, `Key('go_search')`)를 **같은 커밋에서** 제거한다 — 히어로 다음 위젯은 차종 칩이다.
- 차종 칩 "전체"는 항상 petrol 채움(선택) 상태로 보인다(정적 표시일 뿐, 실제 필터 상태와 무관 — 이 화면엔 선택 추적이 없다). 나머지 5개는 기존 아웃라인 스타일 유지.
- 홈 탭(`_AppShell`, `navigationShell.currentIndex == 0`)의 AppBar만 petrol 배경(히어로 그라데이션 시작색과 동일 톤) + 로고 lockup(petrol 라운드-스퀘어 배지 + 흰 "차" 굵은 글자 + "차장님" 워드마크, 아트워크 아님 — 텍스트+배지로 충분) + 우측 아바타 하나(`_ProfileAvatarButton` 그대로 재사용, 벨 없음)로 바꾸고, 테마의 하단 헤어라인 보더·elevation을 이 인스턴스에서만 제거한다. 다른 3탭(찜·채팅·내차팔기)의 AppBar는 그대로 둔다(흰 배경 + 탭 제목).
- 매물 카드(`ListingCard`) 정보 순서를 사진 → 신뢰속성 행(사진 아래 전용 행, 오버레이 아님) → 차량명 → meta(주행·연료·지역·판매자, 한 줄 합침) → 가격(26px/`FontWeight.w800`/`AppColors.priceEmphasis`, 카드에서 가장 큰 텍스트) → 희소옵션 칩으로 바꾼다.
- 옵션 칩: `topOptions`형 우선순위 선택(희소 옵션 우선, 최대 3개) + 부족분은 보편 옵션으로 자연 채움, 넘치면 "외 N개" 오버플로 칩. 옵션이 0개여도 "등록된 옵션 없음" 플레이스홀더 칩을 그려 슬롯을 예약한다(카드 높이 고정). 칩 스타일 = petrol 아웃라인(테두리만 petrol, 배경 없음/`surfaceRaised`, 글자 petrol) — 오버플로 칩만 회색 아웃라인(`borderHairline`/`inkMuted`).
- 옵션 우선순위 값(통제어휘·티어)은 `docs/conventions.md` §11이 정본이다 — 값이 어긋나면 그 문서를 기준으로 고친다(`web/src/lib/options.ts`는 참고용 작동 구현일 뿐).
- 매물 상세(`listing_detail_screen.dart`)의 문의하기 버튼을 `Scaffold.bottomNavigationBar`(sticky bar, 가격 + 문의하기)로 옮긴다 — 본문 인라인 버튼은 **같은 커밋에서** 제거한다. 기존 3분기(본인 매물=버튼 자체 없음/렌더 안 함, 비로그인=탭 시 `/login`, 타인 매물=`openOrCreateRoom`)는 그대로 유지 — 색·라벨·분기 로직을 새로 설계하지 않는다.
- 위 각 축을 실제로 보는 위젯 테스트를 추가하고, 채택 전 일부러 깨서 red를 확인한 뒤 되돌려 green을 확인한다(CLAUDE.md B4): ①홈 탭 AppBar와 히어로 배경색이 같은가 ②히어로 좌우 여백이 0인가(화면 폭과 같은가) ③히어로 바로 다음 위젯이 차종 칩인가(`go_search` 개수=0) ④카드에서 가격 폰트 크기가 차량명보다 큰가 ⑤옵션 칩 슬롯이 옵션 0개일 때도 존재하는가 ⑥신뢰속성 위젯이 사진 위젯 뒤(문서 순서상 아래)에 오는가 ⑦상세에 `bottomNavigationBar`가 있는가(본인 매물 제외).

**Block If:** 없음 — 목업·웹·앱·스파인 4자 대조로 필요한 결정(탐색박스 제거, 벨 없음, 로고 아트워크 범위 제외, 카드 크기 불변, 신뢰속성/옵션칩 스타일은 스파인 우선)이 이미 사용자·계획 단계에서 확정됐다.

**Never:**
- 카드 크기·열 수(모바일 1열)를 바꾸지 않는다 — D5가 4→2→1 열 축소를 규정하고 390px는 1열 구간이다(`ai-flow-1.html`의 2열 모바일 프레임은 목업 변형이라 따르지 않는다).
- 웹 화면(`web/`) 코드를 수정하지 않는다 — 신뢰속성 위치·옵션 칩 색의 웹 쪽 편차(현재 웹은 둘 다 오버레이/회색 칩)는 이 스토리 범위 밖, 별도 판단.
- 알림 벨을 추가하지 않는다(스파인·EXPERIENCE에 없고 푸시가 에픽 Non-goal이라 누를 곳이 없다).
- 실제 로고 아트워크를 제작하지 않는다 — lockup(배지+텍스트)만으로 충분, 아트워크는 "추후 제작"으로 스파인에 이미 명시돼 있다.
- 새 색 토큰을 추가하지 않는다 — 필요한 값(`priceEmphasis` 등)은 `app_theme.dart`에 이미 있다.
- `AiChatScreen`의 결과 그리드를 2열로 바꾸지 않는다.
- 매물 상세 CTA 버튼의 기존 색상·라벨을 새로 정하지 않는다 — 위치만 옮긴다(색은 스파인 §L66/§L134가 amber/petrol 둘 다 허용하는 내부 모호점이라 이 스토리에서 재결정하지 않는다).

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| 옵션 0개 | `listing.options` == null 또는 `[]` | "등록된 옵션 없음" 플레이스홀더 칩 1개(슬롯 예약, 카드 높이 불변) | No error |
| 옵션 5개(희소 2개 포함) | 통제어휘 밖 값 섞임 | 희소 옵션이 우선 노출되고 나머지는 "외 N개"로 접힘, 최대 3개 표시 | No error |
| 신뢰속성 0개 | accident_status/is_single_owner/is_non_smoker 전부 null | 신뢰속성 행 자체가 렌더되지 않음(높이 0, 기존 오버레이와 동일 원칙) | No error |
| 상세 - 본인 매물 | `myId == listing.sellerId` | `bottomNavigationBar` 없음(현행 유지, CTA 자체가 없음) | No error |
| 상세 - 비로그인 | `myId == null` | sticky 바 노출, 문의하기 탭 시 `/login` 이동(서버 쓰기 없음) | No error |
| 상세 - 타인 매물(로그인) | 정상 | sticky 바 노출, 문의하기 탭 시 `openOrCreateRoom` 호출 후 채팅방 이동 | 실패 시 기존 스낵바 에러 유지 |

</intent-contract>

## Code Map

- `app/lib/core/router/app_router.dart` -- `_AppShell`의 `AppBar`를 홈 탭(`currentIndex == 0`)일 때만 petrol 배경+로고 lockup+아바타로 분기, 하단 보더/elevation 제거. `_ProfileAvatarButton`은 그대로 재사용.
- `app/lib/features/auth/home_screen.dart` -- 히어로를 패딩/센터링 바깥으로 꺼내 전체폭 밴드로 재구성(글로우+차 실루엣 CustomPaint 또는 배경 장식 위젯 추가), `_SearchCta`/`Key('go_search')` 제거, "전체" 차종 칩 채움 스타일 고정.
- `app/lib/features/listings/options.dart` (신규) -- `docs/conventions.md` §11을 미러링한 옵션 통제어휘·우선순위 상수(`ALL_CONTROLLED_OPTIONS`·`COMMON_OPTIONS`·`HIGH_PRIORITY_OPTIONS`) + `optionPriority()`/`topOptions()` 순수함수(web `options.ts` 로직 포트).
- `app/lib/features/listings/listing_card.dart` -- 정보 영역 재정렬(신뢰속성 행 이동, 가격 스타일·위치 변경, 옵션 칩 행 추가), `TrustAttributesCardOverlay` 호출 제거.
- `app/lib/features/listings/listing_trust_widgets.dart` -- 카드용 비-오버레이 신뢰속성 행 위젯 신설(짧은 "판매자 제공 정보" 면책 포함, 기존 `TrustAttributesDetailSection`의 긴 UX-DR19 문구와 다름), 더 이상 안 쓰는 `TrustAttributesCardOverlay` 제거(이 변경이 만든 고아).
- `app/lib/features/listings/listing_detail_screen.dart` -- 인라인 문의하기 버튼을 `Scaffold.bottomNavigationBar`(sticky, 가격+문의하기)로 이관, 옛 하단 패딩(시스템 내비바 보정용) 단순화(Scaffold가 bottomNavigationBar 공간을 자동 확보하므로 수동 보정 불필요).
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-755·DW-759·DW-760·DW-735 status를 closed로 갱신.
- `app/test/app_router_test.dart` -- 홈 탭 AppBar 배경색·로고·아바타-only 단언, 다른 탭 AppBar 불변 확인.
- `app/test/home_ai_entry_test.dart` -- 히어로 폭(화면 폭과 동일)·`go_search` 개수 0·히어로 다음 위젯=차종 칩·"전체" 칩 채움 스타일 단언 추가/수정.
- `app/test/listing_card_test.dart` -- 가격 폰트 크기/굵기/색, 신뢰속성 행이 사진 위젯 뒤에 오는지, 옵션 칩 존재(0개/여러 개/오버플로) 단언 추가.
- `app/test/listing_options_test.dart` (신규) -- `topOptions`/`optionPriority` 선택 로직 단위테스트(희소 우선, 통제어휘 밖 값 강등, dedup).
- `app/test/listing_detail_screen_test.dart` -- `bottomNavigationBar` 존재(비로그인/타인 매물)·부재(본인 매물) 단언, 스크롤 없이 바로 보이는지 확인.

## Tasks & Acceptance

**Execution:**
- `app/lib/features/listings/options.dart` -- 옵션 우선순위 포트 -- 카드 옵션 칩 선택의 유일한 로직 출처
- `app/lib/features/listings/listing_trust_widgets.dart` -- 카드용 비-오버레이 신뢰속성 행 신설 + 오버레이 제거 -- AC의 신뢰속성 위치 요구사항
- `app/lib/features/listings/listing_card.dart` -- 재정렬(신뢰속성→차량명→meta→가격→옵션칩) -- DW-760 4축 전부 해소
- `app/lib/features/auth/home_screen.dart` -- 히어로 전체폭 밴드화+배경 장식+탐색박스 제거+전체칩 채움 -- DW-755 해소
- `app/lib/core/router/app_router.dart` -- 홈 탭 AppBar petrol화+로고 lockup -- DW-759 해소
- `app/lib/features/listings/listing_detail_screen.dart` -- sticky 바 이관 -- DW-735 해소
- `_bmad-output/implementation-artifacts/deferred-work.md` -- DW-755·759·760·735 닫기 -- CLAUDE.md B8 장부 닫기
- `app/test/*` (위 Code Map 목록) -- 시각 축 위젯테스트 -- 순서·개수만 보던 기존 검사의 사각지대 보강, red→green 실측

**Acceptance Criteria:**
- Given 앱 홈을 열면, when 렌더되면, then 상태바~앱바~히어로가 같은 petrol 배경으로 끊김 없이 이어지고, 히어로는 좌우 여백 없이 화면 폭을 꽉 채우며, 배경에 글로우+차 실루엣이 보인다.
- Given 홈 화면, when 렌더되면, then 히어로 바로 다음 위젯이 차종 칩 줄이다(그 사이에 탐색 진입 박스가 없다) — "전체" 칩은 petrol 채움 상태로 보인다.
- Given 홈 탭 AppBar, when 렌더되면, then 좌측에 로고 lockup(petrol 배지+"차"+"차장님"), 우측에 아바타 하나만 있다(벨 없음). 다른 탭(찜·채팅·내차팔기) AppBar는 이전과 동일(흰 배경+탭 제목)하다.
- Given 매물 카드(옵션 5개, 신뢰속성 2개 보유), when 렌더되면, then 사진 → 신뢰속성 행(사진 아래, 오버레이 아님) → 차량명 → meta(판매자 포함 한 줄) → 가격(26px/800/`priceEmphasis`, 카드에서 가장 큰 텍스트) → 옵션 칩(최대 3개+"외 N개") 순서로 나타난다.
- Given 매물 카드(옵션 0개), when 렌더되면, then "등록된 옵션 없음" 플레이스홀더 칩이 슬롯을 채워 카드 높이가 옵션 있는 카드와 같다.
- Given 매물 상세(타인 매물, 로그인 상태), when 화면을 열면, then 스크롤하지 않아도 하단에 가격+문의하기 바가 보이고, 탭하면 채팅방이 열린다. 본인 매물이면 그 바가 없다.
- Given 위 각 시각 축, when 위젯테스트를 채택 전 일부러 깨면, then red가 되고 되돌리면 green이 된다(직접 실행·관찰로 증명).

## Spec Change Log

## Review Triage Log

### 2026-08-10 — Review pass (후속 3차 — 2패스가 남긴 `followup_review_recommended: true`로 재실행)
- intent_gap: 0
- bad_spec: 0
- patch: 12 (high 0, medium 6, low 6)
- defer: 1 (high 0, medium 0, low 1)
- reject: 6
- addressed_findings:
  - `[medium]` `[patch]` **히어로 그라데이션 축이 대각선이라 앱바와의 이음매가 오른쪽 절반에서 보인다**(edge-case-hunter 발견, 이 세션이 기하로 확정) — AppBar는 `brandPetrolStrong` 단색인데 히어로 그라데이션은 `topLeft→bottomRight`라 **그 색과 같은 지점이 좌상단 한 점뿐**이었다. 390×220 밴드에서 히어로 우상단 모서리는 이미 종점색(`petrolDeepest`) 쪽으로 약 76% 진행한 값이라, AC①이 금지한 색 단차가 seam에 그대로 드러난다. 축을 `topCenter→bottomCenter`로 바꿔 히어로 **윗변 전체**가 AppBar 색과 같아지게 하고, 색만이 아니라 **축**을 단언하는 테스트를 더했다(기존 테스트는 `colors.first`만 봐서 이 축이 무방비였다).
  - `[medium]` `[patch]` **2패스가 정정하며 심은 새 문장도 낡은 서술이었다**(adversarial 발견, 이 세션이 커밋 계보·코드로 확정) — `epic-16-context.md` FR58이 *"anon이 신뢰속성 3컬럼에 SELECT 권한이 없어 카드 조회 자체가 죽는다"*를 현재시제로 적었는데, 그 원인은 커밋 `806b3a6`에서 이미 제거됐고(`listingCardColumns(bool authed)`가 anon에겐 3컬럼을 빼고 조회, 4개 호출부를 실기기 SM-G991N에서 anon·authed 양쪽 검증) 그 커밋은 이 스토리 baseline(`d86f6a9`)의 **조상**이다(`git merge-base --is-ancestor` 실측). 2패스는 대장 DW-738의 status 주석을 그대로 옮겨 적었는데 **그 주석 자체가 `806b3a6` 이전 서술**이었다. FR58을 실측 사실대로 정정했다(원인은 해소, 남은 건 실기기 재확인). 대장 항목은 오케스트레이터 소유라 수정하지 않고 **새 항목 DW-763**으로 이 사실을 남겼다.
  - `[medium]` `[patch]` **에픽 컨텍스트 재컴파일이 구속 제약을 조용히 지웠다**(adversarial·edge-case-hunter 독립 발견, diff로 확정) — 이 커밋이 `epic-16-context.md`를 재컴파일하며 대체 문구 없이 삭제한 것들: **NFR3**(앱은 웹과 코드 공유 없는 별도 구현) · **AI 입력 500자·되묻기 3턴 서버 강제와 그 "알려진 한계"** · **16.6의 완료 기준**(*"실폰에서 확인해야 완료다 — 존재 확인≠작동 확인"*, 하필 16.6을 done으로 취급하는 같은 커밋에서) · **"내 차 사기"의 도달 경로**. 여기에 더해 사용자가 **일반 규칙**으로 못박은 *"요구사항에 '웹 한정'이라 적혀 있지 않으면 전부 앱 포함 — 임의로 좁히지 않는다"* 가 FR58 안의 괄호로 강등돼 **금지 조항 절반이 사라졌다.** CLAUDE.md B8이 정확히 이 실패를 지목한다("상위 문서의 제약은 하위로 흘린다 … 문서를 새로 쓰는 순간이 가장 위험하다"). 전부 본문으로 복원했고, 일반 규칙은 FR58 부속이 아니라 독립 제약 줄로 올렸다.
  - `[medium]` `[patch]` **계약 정본 문서가 앱과 어긋난 채 "앱도 이 문서의 미러"라고 새로 선언했다**(adversarial 발견, 문서·양쪽 소스 직접 대조) — 이 커밋이 `docs/conventions.md` §11에 앱 미러를 등재했는데, 네 줄 아래 §11.2는 여전히 **"카드 = 상위 3개 + 나머지 개수 `+N` 칩"** 을 규정한다. 앱은 스파인을 따라 "외 N개"를 쓰므로(이 스토리가 명시 확정) **정본 문서가 앱에 대해 틀린 상태**가 됐다 — `project-context.md` 규칙 1이 "어긋나면 conventions.md가 맞다"이므로 다음 에이전트가 이 절을 근거로 앱을 "+N"으로 되돌리면 AC가 조용히 뒤집힌다. §11.2에 편차(표기·계수 기준, DW-762)를 경고 박스로 명시하고, §11.3의 낡은 문장 둘도 함께 고쳤다("web 하나만 미러링한다"는 서술 → 두 미러 명시, 근거를 잃은 "위에서 금지한 이원화" 표현 → 자립 문장으로).
  - `[medium]` `[patch]` **카드 정보 순서(AC의 핵심 축)를 보는 단언이 사실상 한 줄뿐이었다**(verification-gap 발견) — AC는 사진→신뢰속성→차량명→meta→가격→옵션칩 순서를 규정하는데, 위치로 고정된 건 "신뢰속성이 사진 아래"뿐이었다. 나머지 폰트 크기·오른쪽 여백 단언은 **순서와 무관**하게 성립하므로, 이 커밋이 바꾼 배치를 예전 순서(차량명→가격→meta)로 되돌려도 전 스위트가 초록이었다. 차량명→meta→가격→옵션칩의 `dy` 증가를 단언하는 테스트를 더했다.
  - `[medium]` `[patch]` **스펙이 명령한 "대장 등재"가 실행되지 않은 채 시각 4축이 닫혔다**(adversarial 발견) — 스펙의 Manual checks 절이 *"렌더를 못 띄우면 **대장에 등재하고** 위젯테스트로 대체 확인한 사실을 명시한다"*고 적었는데 1패스 기록은 *"대장에 등재된 사실 없음"* 이다. DW-755·759·760·735는 **전부 육안 관찰에서 출발한 항목**인데 위젯 단언만으로 닫혔다 — `appBar.backgroundColor == brandPetrolStrong`이 참이라는 사실은 실기기에서 이음매가 안 보이는지를 말해 주지 않는다(CLAUDE.md B4). 이번 패스가 바로 그 사각지대에서 실제 결함(위 그라데이션 축)을 하나 더 찾았다는 점이 위험을 뒷받침한다. **DW-764**로 새로 등재했다(기존 4항목은 무수정).
  - `[low]` `[patch]` 히어로 `clipBehavior: Clip.hardEdge`가 무단언이다(verification-gap 발견) — 글로우(`top:-30`)·차 실루엣(`top:-6`)은 의도적으로 밴드 밖으로 나가 있고 이를 가두는 건 이 한 줄뿐인데, `Stack`은 클립 안 된 자식에 오버플로 에러를 내지 않아 지워도 전부 초록이다(그러면 amber 글로우가 petrol 앱바 위로 번진다). 단언을 추가했다.
  - `[low]` `[patch]` "외 N개" 칩이 화면 밖으로 밀릴 수 있다(edge-case-hunter 발견) — 칩 행이 가로 스크롤이고 오버플로 칩이 그 **마지막 자식**이라, 라벨이 긴 옵션 3개(파노라마글래스루프·헤드업디스플레이·어댑티브크루즈)면 카드 폭을 넘겨 개수 표시가 안 보인다. 사용자에겐 "옵션이 딱 이만큼"으로 읽힌다. 스크롤 영역만 `Expanded`로 감싸고 오버플로 칩은 그 바깥에 고정했다(개수 표시는 스크롤 대상이 아니다).
  - `[low]` `[patch]` 중립(비-초록) 신뢰속성 뱃지가 카드 경로로 한 번도 렌더되지 않는다(verification-gap 발견) — 이 커밋이 `_TrustChip`의 `onCard` 분기를 지우면서 '단순교환'·'사고' 뱃지는 흰 카드 위에서 **테두리 하나로만** 구분되는데, 카드 레벨 테스트는 전부 '무사고'(초록)나 전체 null이라 그 분기가 실행되지 않는다. 테두리·글자색 단언을 추가했다.
  - `[low]` `[patch]` 하단 시스템 인셋을 넣어 보는 테스트가 0건이다(verification-gap 발견) — 이 커밋은 `20 + viewPadding.bottom` 수동 보정을 `SafeArea` 두 개로 대체했는데, `app/test/` 어디도 `tester.view.padding`을 설정하지 않아 기본 0 인셋에서만 검증됐다. 둘 중 하나를 지워도 초록인 채 실기기에선 문의하기 버튼이 제스처 바 밑으로 들어간다. 인셋 48을 넣고 버튼이 그 위에 온전히 있는지 단언한다.
  - `[low]` `[patch]` 드리프트 가드가 정작 사용자 결정이 걸린 값을 안 본다(adversarial 발견) — 카드 노출 개수는 앱 `_maxChips=3`·웹 `CARD_OPTION_COUNT=3`인데 가드는 이름 집합 3개만 비교했다. `conventions.md` §11.2가 이 값의 4→3 변경을 **사용자 결정으로 기록**해 둔, 가장 다시 바뀔 만한 값이다. 상수를 `options.dart`의 공개 `cardOptionCount`로 올려 가드가 web `ListingCard.tsx`와 대조하게 했고, **이 가드가 안 보는 것**(`optionPriority`/`topOptions` 함수 본문, DW-762의 표기·계수 편차)을 테스트 옆과 `conventions.md` 양쪽에 적었다(B4).
  - `[low]` `[patch]` 카드 테스트 하네스의 사각지대가 기록되지 않았다(adversarial 발견) — `_pump`가 카드를 `SingleChildScrollView`로 감싸 기본 800×600 오버플로를 피하는데(정당한 우회), 그 결과 이 파일 전체에서 `RenderFlex overflowed` 탐지가 영구히 꺼진다. 우회는 그대로 두고, 하네스가 못 보는 것과 **실측 근거**(호출부 5곳이 전부 높이 무제한 `ListView`/`Column`이고 고정 높이 그리드가 없음)를 주석으로 남겼다.
  - `defer` (신규 1건, 대장에 **추가만** 함):
    - `DW-765` — 16.9가 만든 웹·앱 편차가 DW-761·762 말고 **두 축 더** 있다(adversarial 발견, 웹 소스 직접 대조): ①카드의 "판매자 제공 정보" 면책 — 웹은 **2026-08-05 사용자 승인으로 카드에서 뺐는데**(같은 면책이 상세에 이미 있어 중복) 앱은 이번에 새로 넣었다 ②차종 칩 선택 상태 — 앱만 "전체"가 채움이고, 이 편차는 지금 `epic-16-context.md`의 **Non-goals(제외 목록)에만** 적혀 있다(제외 목록은 열린 일을 추적하는 자리가 아니다, B8). 둘 다 스펙이 명시 확정한 것이라 구현 결함은 아니지만, DW-761 결정을 **불완전한 목록 위에서** 내리게 되므로 같은 결정에 묶어 등재했다.
  - `rejected_as_noise` (기록용, 근거 포함):
    - 신뢰속성 유무로 카드 높이가 47px 달라지고 웹은 그걸 실측(판매중 95건 중 4건만 신뢰속성 보유)해 오버레이로 뺐다(adversarial) — 새 근거는 유효하지만 결론은 2패스와 같다: 이 스펙의 I/O 매트릭스가 "신뢰속성 0개 → 행 자체가 렌더되지 않음(높이 0)"을 **명시적으로 요구**한다. 스코프 권한은 의도(intent)에 있고 의도가 이걸 지정했다. 웹·앱 수렴 판단은 DW-761 소관.
    - 스펙 `status`와 `sprint-status.yaml`이 어긋나고 `review_loop_iteration`이 2패스를 돌았는데도 0이다(adversarial) — 전자는 이 워크플로가 리뷰 중 `in-review`로 두었다가 종료 시 되돌리는 정상 상태다. 후자는 오해다: 그 카운터는 리뷰 **패스 수**가 아니라 `bad_spec` 루프백 횟수를 세며(둘 다 0건이었다), 후속 리뷰 진입 시 0으로 초기화하는 것이 이 워크플로의 규정 동작이다.
    - 탭 제목 표에 `'중고차 직거래'`가 단언 없이 남아 있다(adversarial) — 사실이지만 홈 탭은 이제 그 문자열을 그리지 않으므로(로고 lockup으로 대체) 값이 바뀌어도 사용자에게 보이는 변화가 없다. 바로 위 주석이 이미 그 사실과 대체 검증 위치를 적어 뒀다.
    - 앱바와 히어로의 **인접성**(사이에 간격 위젯이 들어가도 초록)이 무단언이다(intent-alignment) — 2패스와 같은 근거로 reject(홈 위젯 테스트가 셸 없이 `HomeScreen`만 띄우는 구조라 비용이 크다). 다만 이 지적이 겨눈 실질적 위험(seam이 실제로 보이는 것)은 이번 패스의 그라데이션 축 패치가 직접 해소했다.
    - 옵션 칩 슬롯의 **높이 동등성**이 측정되지 않았다(intent-alignment) — AC⑤ 문구 자체가 "슬롯이 존재하는가"이고, 두 분기 모두 정확히 한 줄을 그리므로 높이가 같다. 스펙이 정한 기준 이상을 새로 요구할 근거가 없다.
    - 글로우·실루엣의 "은은함"·"침범하지 않음"이 단언되지 않는다(intent-alignment) — 정성 축이라 위젯 단언으로 환원되지 않는다. 침범은 `Stack` 자식 순서로 구조적으로 보장되고(항상 뒤에 오는 `Padding`이 위에 깔린다), 나머지는 육안 축이라 DW-764(실기기 확인)로 넘어간다.

### 2026-08-09 — Review pass (후속 2차 — `followup_review_recommended: true`로 재실행)
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 4, low 4)
- defer: 1 (high 0, medium 0, low 1)
- reject: 11
- addressed_findings:
  - `[medium]` `[patch]` **매물 카드 meta 줄이 찜 버튼에 가려진다**(adversarial·edge-case-hunter 독립 발견, 이 세션이 390×844 프로브로 직접 실측해 확정) — 찜 버튼은 `x 338–382, y 242–286`에 절대배치되고 신뢰속성 행·차량명은 `right: 52` 여백으로 그 구간을 피하는데, 1차 리뷰가 만든 재정렬에서 **meta 줄만 여백을 못 받았다.** 신뢰속성이 전부 null인 카드(기존 데이터의 정상 상태)에선 신뢰속성 행이 0높이로 접히며 meta가 `y 276–294`로 올라와 하트와 38×10px 겹친다 — 판매자명이 긴 매물은 끝부분이 하트 밑으로 들어간다. meta에도 같은 `right: 52`를 준다.
  - `[medium]` `[patch]` **계획 문서에 사실과 다른 완료 주장을 이 커밋이 새로 심었다**(adversarial 발견, 대장·diff 직접 대조로 확정) — 재컴파일된 `epic-16-context.md`의 FR58에 "16.6에서 완료 처리됨(실폰으로 미인증 상태 실제 렌더까지 확인)"이 추가됐는데, 대장 DW-738은 `status: open`이고 그 사유가 정확히 반대다(잠금 해제한 실기기에서 로그아웃 상태로 홈에 들어가면 "지금 인기 매물을 불러오지 못했습니다" — anon이 신뢰속성 3컬럼에 SELECT 권한이 없어 카드 조회가 죽는다). 다음 스토리·회고가 이 문서를 읽으므로(DW-738 자신의 `why_it_matters`가 지목한 실패 모드) 문장을 실측 사실대로 정정한다. 대장 자체는 수정하지 않는다.
  - `[medium]` `[patch]` **AC④("가격이 카드에서 가장 큰 텍스트")를 보는 검사가 vacuous였다**(intent-alignment 발견, 실측 확정) — 차량명 `TextStyle`에는 `fontSize`가 없어 테마에서 14를 상속받는데, 테스트가 `nameText.style?.fontSize ?? 0`으로 읽어 **항상 0**으로 떨어졌다. `0 < 26`이라 이 단언은 어떤 경우에도 실패할 수 없었다. 렌더 결과의 실효 크기(`RenderParagraph.text.style.fontSize`)로 비교하도록 고친다.
  - `[medium]` `[patch]` **`options.dart` 사본에 드리프트 가드가 없다**(verification-gap·adversarial 독립 발견) — 이 커밋은 웹 `options.ts`의 통제어휘·티어를 손으로 베껴 세 번째 사본을 만들었는데(현재 값은 일치 확인) 어긋남을 잡는 검사가 없다. 이 저장소는 **바로 이 실패로 이미 데었고**(요약 사본이 원본보다 늙어 틀린 값이 주입된 3건, `project-context.md`) 실행되는 대조 검사라는 처방까지 두 번 코드로 남겨 뒀다(`app_theme_color_drift_test.dart`가 `../web/src/app/globals.css`를 직접 읽는 방식). 같은 방식의 대조 테스트를 추가하고 `conventions.md` §11에 앱 미러와 그 검사를 등재한다.
  - `[low]` `[patch]` 옵션 값의 공백이 정규화되지 않는다(adversarial·edge-case-hunter 독립 발견) — 1차 패치가 `.where((o) => o.trim().isNotEmpty)`로 **판정에만** trim을 써서 원본 값이 그대로 흘렀다. `' 선루프'`는 통제어휘 조회에 실패해 최하위 티어로 강등되고 `'선루프'`와 다른 문자열이라 dedup도 피해 칩이 두 번 뜬다. `.map(trim).where(isNotEmpty)`로 값 자체를 정규화한다.
  - `[low]` `[patch]` 신뢰속성 뱃지 3개를 렌더하는 테스트가 0건이라 1차 패치(`Wrap`→가로 스크롤)가 무방비였다(verification-gap 발견) — 이 세션이 실측한 결과 **접힘은 실제로 일어나지 않는다**(390px에서 행 폭 214.5px, 가용 ~310px, 세 뱃지가 한 줄 `dy 255–271`). 즉 1차 패치의 근거였던 "2줄로 접힐 수 있다"는 미측정 가설이었다. 구현은 해가 없어 되돌리지 않고(A3), 실측값을 주석으로 남긴 3뱃지 한 줄 단언을 추가해 그 자리를 고정한다.
  - `[low]` `[patch]` vacuous한 `Wrap` 부재 단언(adversarial 발견) — `TrustAttributesCardRow`는 어느 분기에서도 `Wrap`을 그리지 않으므로(`SingleChildScrollView`+`Row`) `findsNothing`이 실패할 수 없다. 아이러니하게 바로 위 주석이 같은 종류의 vacuous 단언을 과거 리뷰 지적(P6)으로 기록해 두고 있다. 실제로 그리는 위젯 기준으로 교체한다(옆의 `Text` 단언은 vacuous가 아니므로 둔다).
  - `[low]` `[patch]` 1차 리뷰가 만든 패치 3건에 가드가 없다(verification-gap 발견) — 플레이스홀더 칩의 muted 스타일·카드 가격의 `maxLines`/`ellipsis`·차 실루엣의 우상단 위치가 전부 무단언이라(실루엣은 키 존재만 확인) 되돌아가도 초록이다. 각각 단언을 추가하고 상세 sticky 바 가격의 줄바꿈 방지도 함께 고정한다.
  - `defer` (신규 1건, 대장에 **추가만** 함):
    - `DW-762` — 옵션 칩도 웹·앱이 갈렸다(adversarial 발견, 웹 소스 직접 대조로 확정): 색(웹 `text-ink-secondary` 회색 vs 앱 petrol 아웃라인)·오버플로 표기(`+N` vs "외 N개")에 더해 **오버플로 계수 기준까지 다르다**(웹 `options.length - cardOptions.length` = 원본 길이, 앱 `all.toSet().length - top.length` = 중복 제거 후) — 중복 값이 섞인 매물은 같은 데이터로 서로 다른 숫자를 보여준다. 앞의 두 축은 이 스토리가 "스파인 우선"으로 명시 확정한 것이라 구현 결함이 아니지만, 결과는 DW-761과 같은 모양(웹·앱이 갈림)이라 같은 결정에 묶어 봐야 한다. 계수 기준만은 스타일이 아니라 계산 규칙 불일치라 별도로 통일이 필요하다.
  - `rejected_as_noise` (기록용, 근거 포함):
    - 신뢰속성 유무로 카드 높이가 47px 달라진다 — "옵션은 슬롯을 예약하면서 신뢰속성은 안 한다"는 지적(adversarial·edge-case-hunter)은 실측으론 사실이지만(389 vs 436), 이 스펙의 I/O 매트릭스가 "신뢰속성 0개 → 행 자체가 렌더되지 않음(높이 0)"을 **명시적으로 요구**한다. 스펙대로 구현된 것이라 결함이 아니다.
    - 오버스크롤 시 앱바-히어로 사이에 흰 띠가 드러난다(edge-case-hunter) — 홈은 `RefreshIndicator`+`AlwaysScrollableScrollPhysics`이고 Android 기본 physics는 clamping이라 콘텐츠가 밀려 내려가지 않는다. 이 시나리오는 bouncing physics(iOS)에서만 성립하는데 이 앱의 검증 대상은 안드로이드 실기기다.
    - 히어로 차 실루엣이 헤드라인·입력창·제안칩을 침범한다(adversarial) — 실루엣은 `Stack`의 **첫 자식**이라 헤드라인·입력창·제안칩(뒤에 오는 `Padding`)에 항상 깔린다. 알파 0.12 배경 장식이 텍스트 뒤에 놓이는 건 목업의 `.silhouette`도 같은 레이어 방식이다. 다만 "키 존재만 본다"는 검증 지적은 유효해 위치 단언은 patch로 반영했다.
    - 큰 글꼴 배율에서 로고 배지(28×28 고정)·상세 sticky 바가 넘친다(edge-case-hunter 2건) — 이 앱 전체가 `textScaler` 대응을 하지 않는 것이 현재 관례라 이 스토리가 새로 만든 회귀가 아니다. 이 두 자리만 더 엄격히 요구할 근거가 약하다.
    - 넓은 뷰포트에서 히어로 내부 콘텐츠에 폭 상한이 없다(edge-case-hunter) — 모바일 앱이고 D5의 열 축소 규정도 카드 그리드에 대한 것이다.
    - `topOptions(n <= 0)`이 `RangeError`를 던진다(edge-case-hunter) — 호출부가 하나뿐이고 상수 3을 넘긴다. 불가능한 시나리오용 방어는 A2(요청받지 않은 유연성 금지)가 명시적으로 배제한다.
    - 스펙 `status`와 `sprint-status.yaml`이 어긋난다(adversarial) — 이 워크플로가 리뷰 중 `in-review`로 두었다가 종료 시 되돌리는 정상 상태다.
    - `Always`의 "칩 스타일 = petrol 아웃라인" 문구와 muted 플레이스홀더 구현이 어긋나므로 스펙을 고쳐야 한다(adversarial) — `Always`는 `<intent-contract>` 안이라 리뷰가 수정할 수 없고(bad_spec 루프백에서도 금지), 플레이스홀더는 "옵션 칩"이 아니라 부재 표시라 문구 위반으로 단정되지 않는다. 1차 패스가 이미 근거를 Triage Log에 남겼다.
    - 앱바와 히어로 사이에 간격 위젯을 넣어도 테스트가 초록이다(intent-alignment) — 사실이지만 홈 위젯 테스트가 셸(AppBar) 없이 `HomeScreen`만 띄우는 구조라 인접성 단언 비용이 크고, 실제 회귀 위험은 낮다.
    - "전체" 차종 칩이 라벨 문자열 비교로 선택 상태를 정한다(adversarial) — 스펙 `Always`가 "정적 표시일 뿐, 실제 필터 상태와 무관"이라고 이 해석을 이미 확정했다(1차 패스도 같은 근거로 reject).
    - DW-761의 표현·범위 문제(adversarial) — 지적의 실체(옵션 칩 축 누락)는 위 defer로 새 항목(DW-762)에 담았고, 기존 항목은 오케스트레이터 소유라 수정하지 않는다.

### 2026-08-09 — Review pass
- intent_gap: 0
- bad_spec: 0
- patch: 8 (high 0, medium 6, low 2)
- defer: 1 (high 0, medium 1, low 0)
- reject: 5
- addressed_findings:
  - `[medium]` `[patch]` 카드 가격 텍스트에 줄바꿈 방지(`maxLines: 1` + `overflow: ellipsis`)가 빠져 있다(adversarial·edge-case-hunter 독립 발견) — D5(가로 요소는 세로로 접지 않는다)가 명시한 규칙을 바로 위 차량명·meta 텍스트는 지키는데 새 26px 가격 텍스트만 빠졌다. 추가한다.
  - `[medium]` `[patch]` 매물 상세 sticky 바의 가격 텍스트도 같은 줄바꿈 방지가 빠졌다(edge-case-hunter) — 좁은 화면에서 2줄로 밀리면 sticky 바 높이가 예측 밖으로 커진다. 추가한다.
  - `[medium]` `[patch]` 카드 신뢰속성 행(`TrustAttributesCardRow`)이 `Wrap`을 그대로 써서 뱃지 3개(무사고·1인소유·비흡연)가 다 있으면 좁은 1열 카드에서 2줄로 접힐 수 있다(edge-case-hunter) — D5가 "신뢰속성 행"을 명시적으로 지목한 금기(세로로 접지 않는다)다. 바로 옆 옵션 칩 행처럼 가로 스크롤/비-wrap 방식으로 바꾼다.
  - `[medium]` `[patch]` "등록된 옵션 없음" 플레이스홀더 칩이 실제 옵션 칩과 똑같은 petrol 강조 스타일이라 "값이 없다"는 상태가 마치 강조된 셀링포인트처럼 보인다(adversarial 발견) — 스펙의 "칩 스타일=petrol 아웃라인(오버플로 칩만 회색)" 문구가 플레이스홀더를 명시적으로 예외 처리하지 않아 생긴 갭이다. 이미 옆에 있는 "외 N개" 오버플로 칩의 회색/muted 스타일을 플레이스홀더에도 적용한다(웹의 `border-transparent`+`text-ink-muted` 관례와도 일치).
  - `[medium]` `[patch]` 홈 탭 AppBar와 히어로를 잇는 유일한 장치(하단 헤어라인 보더 제거)를 보는 테스트가 없다(adversarial 발견) — 배경색이 같은지는 검사하지만 보더 자체가 없는지는 아무도 안 봐서, 그 한 줄이 실수로 지워져도 기존 검사는 초록이다. 홈 탭 AppBar의 `shape`/보더 부재를 단언하는 테스트를 추가한다.
  - `[medium]` `[patch]` 히어로 배경 요소(글로우·차 실루엣)를 보는 테스트가 0건이고(adversarial·intent-alignment 독립 발견), 차 실루엣이 AC 문구("우상단")·목업(`consistency-1.html` `.silhouette`, `right:-8%;top:-14%`)과 달리 우하단에 배치돼 있다(intent-alignment 발견, 코드 실측: `right:-18, bottom:-14`) — 실루엣을 우상단으로 옮기고, `hero_glow`/`hero_car_silhouette` 키 존재를 단언하는 테스트를 추가한다.
  - `[low]` `[patch]` 옵션 값에 빈 문자열이 섞이면 필터링 없이 라벨 없는 빈 칩으로 그려질 수 있다(adversarial·edge-case-hunter 독립 발견) — 칩 생성 전에 비어있지 않은 문자열만 남긴다.
  - `[low]` `[patch]` 새 옵션 칩 기능이 실제 서버 데이터(DB→`ListingCardData.fromMap`→`attachCoverImages`)까지 이어지는 경로를 보는 테스트가 0건이다(verification-gap 발견, 배선 자체는 실측 확인 결과 끊긴 곳 없음) — `listing_model_test.dart`·`listings_repository_image_order_test.dart`의 기존 픽스처에 `options` 키를 추가하고 결과를 단언한다.
  - `defer` (신규 1건):
    - `_bmad-output/implementation-artifacts/deferred-work.md`의 DW-760 근거가 사실과 다르다(adversarial 발견, 웹 소스 직접 대조로 확인) — "웹 정본은 신뢰속성을 사진과 차량명 사이 일반 블록으로 그린다"고 적었지만, 실제 웹(`ListingCard.tsx:154`, `TrustAttributes.tsx:13-17`)은 2026-08-05 사용자 승인으로 이미 카드 오버레이 방식으로 바뀌어 있다(지금 앱이 쓰던 것과 같은 방식). 이 스토리는 스파인(DESIGN.md)이 우선한다는 원칙으로 신뢰속성을 사진 아래 전용 행으로 옮겼는데, 그 결과 **웹=오버레이, 앱=전용 행**으로 두 플랫폼이 이 축에서 오히려 갈린다 — Epic 16의 "웹·앱이 같은 제품으로 보인다" 목표와 반대 방향이다. 이 diff의 코드 문제가 아니라 상위 계획 문서(DW-760)의 근거 오류이자, 웹을 다시 스파인에 맞출지 앱만 다르게 갈지에 대한 별도 판단이 필요한 사안이라 이 스토리에서 고치지 않는다.
  - `rejected_as_noise` (기록용, 근거 포함):
    - 프로필 아바타(`brandPetrol`) 색이 새 petrol AppBar 배경(`brandPetrolStrong`)과 톤이 비슷해 대비가 약해 보일 수 있다(adversarial 발견) — 측정된 대비 실패 수치 없이 주관적 우려이고, 스펙이 `_ProfileAvatarButton`을 명시적으로 그대로 재사용하기로(surgical) 정했다.
    - 로고 배지의 흰색 16% 알파값이 정확히 그 값인지 보는 테스트가 없다(adversarial 발견) — 이 저장소의 다른 장식적 알파값(예: 히어로 제안 칩의 반투명 배경)도 마찬가지로 정밀 단언하지 않는 게 기존 관례라 이 기준만 더 엄격하게 요구할 근거가 약하다.
    - 옵션 칩이 밀도 높을 때 "대표 1개+외 N개"로 축소하는 `DESIGN.md` §L128의 2차 폴백을 구현하지 않았다(intent-alignment 발견) — 이 스토리의 AC 문구 자체는 "3~4개, 넘치면 외 N"만 요구하고 이 폴백을 요구하지 않는다(intent-alignment 스스로 "AC 자체 위반은 아니다"로 판정). 이미 의도된 단순화(CLAUDE.md A2)다.
    - 차종 칩 "전체"가 실제 상태 추적이 아니라 정적 장식이다(intent-alignment 발견) — 스펙 Always가 "정적 표시일 뿐, 실제 필터 상태와 무관"이라고 이미 명시적으로 이 해석을 확정해 뒀다.
    - 상태바(status bar) 자체의 petrol 연속성을 보는 코드·테스트가 없다(intent-alignment 발견) — Flutter `AppBar`가 배경색 밝기로 상태바 아이콘 스타일을 자동 계산하고(SDK 소스 확인, verification-gap 레이어가 별도로 실측) 배경색 자체도 상태바 인셋까지 자동으로 칠해지므로 추가 코드가 필요하지 않을 가능성이 높다 — 육안 확인은 이 스토리의 다른 항목과 마찬가지로 CanvasKit 렌더 제약으로 이 세션에서 못 하며, 이미 스펙의 Verification 절이 그 한계를 명시하고 대장 등재로 대체하기로 정해 뒀다.

## Design Notes

**정본 우선순위 — 이 스토리에 한해 스파인이 현재 웹 코드보다 우선한다.** Epic 16의 기본 원칙은 "웹이 정본, 앱은 미러링"이지만, 16.9는 그 미러링이 만든 편차를 스파인 기준으로 되짚는 스토리다. 실제로 확인한 결과: 현재 웹 `ListingCard.tsx`/`TrustAttributes.tsx`도 신뢰속성을 카드 오버레이로 그리고(2026-08-05 웹 자체 결정 — 앱이 지금 하는 것과 같은 이유·같은 방식), 옵션 칩도 회색(`text-ink-secondary`)에 "+N" 표기를 쓴다 — `DESIGN.md`·목업(`card-final-1.html`, `consistency-1.html` PART 3)이 요구하는 "신뢰속성=사진 아래 전용 행", "옵션 칩=petrol 아웃라인, 외 N개 표기"와 다르다. AC가 이 두 축을 명시적으로 요구하므로 **앱은 스파인/목업 값을 따르고, 웹 코드의 현재 방식은 참고하지 않는다**(Never가 명시하듯 웹은 건드리지 않는다 — 이 편차의 웹 쪽 해소는 별도 판단, `docs/conventions.md` §4.1 락스텝 대상도 아니다: 필드 추가가 아니라 표시 스타일 변경이라 계약 자체는 안 바뀐다).

**가격 색은 이미 있다.** `app_theme.dart`의 `priceEmphasis = Color(0xFFC0730F)`가 `DESIGN.md`의 canonical 값과 이미 일치한다(목업 파일들이 쓰는 `#E08A1B`는 낡은 값이니 따르지 않는다). 새 토큰 불필요, `AppColors.priceEmphasis`만 쓰면 된다.

**옵션 칩 "아웃라인"의 뜻.** `DESIGN.md` §L128은 "petrol 아웃라인"이라고 적었지만 `card-final-1.html`의 실제 CSS는 배경까지 채운 petrol-tint 칩이다 — 스파인 산문이 목업 CSS보다 우선하므로(§L59), 문자 그대로 "테두리만 petrol, 배경은 채우지 않음"으로 구현한다(새 tint 토큰을 안 만들어도 되는 부수 이점도 있다).

**오버플로 표기는 "외 N개"다.** 웹은 `+{N}`을 쓰지만 `DESIGN.md`·목업·이 스토리 AC 전부 "외 N개"로 적었다 — 이 축도 웹이 아니라 스파인을 따른다.

**Scaffold가 하단 바 공간을 자동 확보한다.** 웹은 `fixed` + `pb-28` 콤보로 sticky 바 자리를 수동으로 비워야 하지만, Flutter의 `Scaffold(bottomNavigationBar:)`는 body 레이아웃에서 그 높이를 자동으로 빼준다 — 옛 코드의 `20 + viewPadding.bottom` 하단 패딩(문의하기 버튼이 시스템 내비바에 안 가리게 하려던 수동 보정)은 목적을 잃으므로 단순화한다. sticky 바 자체는 `SafeArea(top: false)`로 감싸 시스템 제스처 바 영역을 스스로 흡수한다.

**히어로 배경 장식은 정밀 아트가 아니어도 된다.** 스파인이 요구하는 건 "글로우/메시 + 대형 차 실루엣"이라는 존재 자체지, 목업의 정확한 SVG 좌표가 아니다 — `RadialGradient`(amber/petrol 톤, 우상단)와 단순 실루엣(아이콘 폰트·간단한 `CustomPainter`·저투명도 `Icon` 등 구현이 가장 쉬운 방식)로 충분하다. 정확한 벡터 재현은 이 스토리 범위가 아니다(로고 아트워크와 같은 이유 — "추후 제작").

## Verification

**Commands:**
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter analyze` -- expected: 0 issues
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter test` -- expected: 전체 green(기존 스위트 + 신규 테스트)
- `export PATH="$HOME/flutter/bin:$PATH" && cd app && flutter build web --dart-define-from-file=.env.json` -- expected: 빌드 성공

**Manual checks (if no CLI):**
- 로컬/개발 API로 앱 홈·매물 카드·매물 상세를 실제로 열어 육안으로 스파인과 대조한다(폭·색 연속성·가격 강조·옵션 칩·상세 sticky 바). 이 헤드리스 샌드박스가 CanvasKit `CONTEXT_LOST_WEBGL`로 렌더를 못 띄우면(spec-16-4/16-5/16-8 선례와 동일한 환경 한계) 대장에 등재하고 위젯테스트로 대체 확인한 사실을 명시한다.

## Auto Run Result

**Summary:** 실기기 화면이 시각 스파인(`DESIGN.md`)과 어긋나 있던 4곳(DW-755·759·760·735)을 한 커밋으로 교정했다 — 홈 앱바-히어로를 상태바까지 이어지는 하나의 petrol 면으로 바꾸고 히어로에 글로우·차 실루엣 장식을 넣었으며, 탐색 진입 박스를 제거해 히어로 다음이 바로 차종 칩이 되게 했다. 앱바엔 로고 lockup(petrol 배지+"차"+"차장님")을 넣었다(홈 탭만, 다른 3탭은 불변). 매물 카드는 신뢰속성을 사진 오버레이에서 사진 아래 전용 행으로 옮기고, 가격을 26px/800/`priceEmphasis`로 카드 최상위 강조 요소로 바꾸고, 희소옵션 칩(petrol 아웃라인, 우선순위 선택, 빈 슬롯 예약)을 신설했다. 매물 상세엔 하단 고정 바(가격+문의하기)를 추가해 스크롤 없이 항상 보이게 했다. 코드리뷰(4개 렌즈 병렬)에서 패치 8건(가격·신뢰속성 줄바꿈 방지, 플레이스홀더 칩 스타일, 앱바 보더·히어로 배경 요소 테스트 누락, 차 실루엣 위치, 빈 문자열 옵션, options 필드 데이터 경로 무검증)을 잡아 전부 적용·검증했고, defer 1건(DW-761 — 이 스토리 이후 신뢰속성 위치가 웹·앱 사이에서 갈리게 된 것, 웹 쪽 재정합 여부는 별도 판단 필요)을 새로 등재했다. 이어서 **후속 2차 리뷰**(같은 4개 렌즈 재실행)가 patch 8건을 더 잡았다 — 그중 가장 큰 것은 재정렬 과정에서 **매물 카드 meta 줄만 찜 버튼 여백을 못 받아 신뢰속성 없는 카드(=기존 데이터 대부분)에서 판매자명 끝이 하트에 가려지던 것**(390px 프로브로 38×10px 겹침 실측)이고, 그다음이 **`epic-16-context.md`에 사실과 다른 "16.6 완료" 주장이 새로 들어간 것**(대장 DW-738은 같은 날 실기기 실측으로 open으로 되돌려져 있다), 그리고 **AC④를 보는 단언이 항상 참이었던 것**(차량명 `fontSize`가 null이라 `?? 0`으로 떨어짐)이다. 옵션 통제어휘 사본에 드리프트 가드도 새로 달았고, defer 1건(DW-762 — 옵션 칩 축의 웹·앱 편차 + 오버플로 계수 기준 불일치)을 추가 등재했다. 이어서 **후속 3차 리뷰**(같은 4개 렌즈 재실행)가 patch 12건을 더 잡았다 — 가장 큰 것은 **이 스토리의 대표 축(AC①: 앱바~히어로가 한 면으로 이어진다)이 실제로는 깨져 있던 것**이다: 히어로 그라데이션 축이 대각선이라 앱바 단색과 같은 지점이 좌상단 한 점뿐이었고 화면 오른쪽 절반에선 색 단차가 보일 상태였다(테스트는 `colors.first`만 봐서 초록이었다). 그다음이 **2패스가 정정하며 심은 문장도 낡은 서술이었던 것**(FR58의 anon 컬럼 원인은 커밋 `806b3a6`에서 이미 해소, 그 커밋은 baseline의 조상)과 **에픽 컨텍스트 재컴파일이 구속 제약 4~5개를 대체 문구 없이 지운 것**(NFR3·AI 상한·16.6 완료 기준·사용자가 못박은 일반 규칙의 금지 조항), 그리고 **계약 정본 `conventions.md` §11.2가 앱과 어긋난 채 "앱도 이 문서의 미러"라고 새로 선언한 것**이다. 대장에는 기존 항목을 손대지 않고 신규 3건(DW-763·764·765)만 추가했다.

**Files changed:**
- `app/lib/features/listings/options.dart`(신규) — `docs/conventions.md` §11 미러(옵션 통제어휘·우선순위) + `topOptions`/`optionPriority`
- `app/lib/features/listings/listing_trust_widgets.dart` — `TrustAttributesCardOverlay` 제거, `TrustAttributesCardRow`(사진 아래 전용 행) 신설, 카드 신뢰속성 행을 가로 스크롤로(패치: 2줄 접힘 방지)
- `app/lib/features/listings/listing_card.dart` — 정보 순서 재배치, 가격 26px/800/priceEmphasis(+줄바꿈 방지 패치), 옵션 칩 행 신설(+빈 문자열 필터·플레이스홀더 muted 스타일 패치)
- `app/lib/features/auth/home_screen.dart` — 히어로 전체폭 밴드화+글로우/차실루엣 장식(+우상단 위치 보정 패치)+`_SearchCta` 제거+"전체" 칩 채움
- `app/lib/core/router/app_router.dart` — 홈 탭 전용 petrol AppBar+로고 lockup(다른 탭 불변)
- `app/lib/features/listings/listing_detail_screen.dart` — 문의하기를 `Scaffold.bottomNavigationBar`(sticky)로 이관(+가격 줄바꿈 방지 패치)
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-755·759·760·735 done 처리, DW-761 신규 등재(defer)
- `_bmad-output/implementation-artifacts/epic-16-context.md` — Story 16.9 반영해 재컴파일(계획 단계 산출물), FR58의 사실과 다른 완료 주장 정정(2패스 패치)
- `app/test/listing_options_drift_test.dart`(2패스 신규) — 앱 `options.dart` ↔ web `options.ts` 통제어휘·티어 대조(web 소스를 상대경로로 직접 읽는다, `app_theme_color_drift_test.dart`와 같은 방식)
- `docs/conventions.md` §11 — 앱이 두 번째 미러임과 위 대조 검사를 등재(2패스 패치)
- `_bmad-output/implementation-artifacts/deferred-work.md` — DW-762 신규 등재(2패스 defer, 추가만·기존 항목 무수정)
- `app/test/app_router_test.dart`·`home_ai_entry_test.dart`·`listing_card_test.dart`·`listing_detail_screen_test.dart`·`listing_trust_widgets_test.dart`·`listing_model_test.dart`·`listings_repository_image_order_test.dart` — 시각 축 위젯테스트 보강, `app/test/listing_options_test.dart`(신규) — 옵션 우선순위 로직 단위테스트
- (3패스) `app/lib/features/auth/home_screen.dart` — 히어로 그라데이션 축을 대각선→세로축으로(앱바 이음매가 오른쪽 절반에서 보이던 것 해소)
- (3패스) `app/lib/features/listings/listing_card.dart`·`options.dart` — "외 N개" 칩을 스크롤 밖에 고정(항상 보이게), 카드 노출 개수를 공개 상수 `cardOptionCount`로 승격(드리프트 가드 대상화)
- (3패스) `app/test/home_ai_entry_test.dart`·`listing_card_test.dart`·`listing_trust_widgets_test.dart`·`listing_detail_screen_test.dart`·`listing_options_drift_test.dart` — 그라데이션 축·`clipBehavior`·카드 세로 순서·오버플로 칩 가시성·중립 신뢰뱃지 테두리·하단 시스템 인셋 48·`cardOptionCount` 대조 단언 추가 + 하네스 사각지대 기록
- (3패스) `_bmad-output/implementation-artifacts/epic-16-context.md` — FR58의 낡은 원인 서술 정정, 재컴파일이 지운 구속 제약 복원(NFR3·AI 500자/3턴+한계·16.6 완료 기준·"내 차 사기" 도달 경로), "웹 한정 미명시=앱 포함" 일반 규칙을 독립 제약 줄로 승격
- (3패스) `docs/conventions.md` §11.2·§11.3 — 오버플로 표기·계수 기준의 웹/앱 편차 경고 박스 추가, 미러 두 벌 명시, 드리프트 가드가 **보는 것/못 보는 것** 명시
- (3패스) `_bmad-output/implementation-artifacts/deferred-work.md` — DW-763·764·765 신규 등재(추가만·기존 항목 무수정)

**Review findings breakdown:**
- 코드리뷰 3패스(같은 4개 렌즈 재실행 — 2패스가 `followup_review_recommended: true`를 남겼기에 돈다): intent_gap 0, bad_spec 0, patch 12(high 0, medium 6, low 6) 전부 적용·검증 완료, defer 1건(DW-765 신규 등재), reject 6건. **3패스가 잡은 것 중 넷은 앞 패스가 만든 것이다** — ①2패스가 허위 완료 주장을 걷어내며 심은 대체 문장도 낡은 서술이었고(원인은 baseline 이전 커밋에서 해소됨) ②구현 단계의 에픽 컨텍스트 재컴파일이 구속 제약 4~5개를 대체 없이 지웠고 ③같은 커밋의 `conventions.md` §11 편집이 정본 문서를 앱에 대해 틀린 상태로 만들었고 ④스펙이 명령한 "대장 등재"가 실행되지 않은 채 시각 4축이 닫혔다. 나머지 중 가장 무거운 것은 **이 스토리의 대표 AC(①앱바~히어로 연속면)가 실제로는 성립하지 않았다**는 것이다.
- 코드리뷰 1패스(adversarial·edge-case-hunter·verification-gap·intent-alignment 4개 렌즈 병렬): intent_gap 0, bad_spec 0, patch 8(high 0, medium 6, low 2) 전부 적용·검증 완료, defer 1건(DW-761 신규 등재), reject 5건(아바타 대비 추측·로고 알파 미검증·옵션 밀도 폴백 미구현·"전체" 칩 정적 표시·상태바 SystemChrome 부재 — 각각 근거와 함께 Review Triage Log에 기록).
- 코드리뷰 2패스(같은 4개 렌즈 재실행 — 1패스가 `followup_review_recommended: true`를 남겼기에 돈다): intent_gap 0, bad_spec 0, patch 8(high 0, medium 4, low 4) 전부 적용·검증 완료, defer 1건(DW-762 신규 등재), reject 11건. 2패스가 잡은 것 중 셋은 **1패스가 만든 것**이다 — ①재정렬 과정에서 meta 줄만 찜 버튼 여백을 못 받아 대부분의 카드에서 글자가 가려졌고 ②`epic-16-context.md`에 사실과 다른 완료 주장이 새로 들어갔고 ③1패스 패치 3건이 무단언으로 남았다. 나머지 중 둘은 **검사 자체의 결함**이다: AC④를 보는 단언이 항상 참이었고(차량명 `fontSize`가 null이라 `?? 0`으로 떨어짐), `Wrap` 부재 단언도 어떤 분기에서도 실패할 수 없었다.

**Follow-up review recommendation:** `true` — 3패스 기준 high 0건이지만 3×medium(6) + 1×low(6) = 24 ≥ 5. (1패스 20 → 2패스 16 → 3패스 24. 매 재실행이 실제로 새 medium을 찾아냈고, 3패스는 그중 넷이 **앞 패스가 만든 것**이었다 — 재실행이 형식이 아니라 실효가 있다는 증거다.)

**Verification performed — 3패스(이 세션에서 직접 실행·관찰):**
- `flutter analyze` — 0 issues · `flutter test` — **473/473 전체 green**(2패스 466건 + 3패스 신규 7건) · `flutter build web --dart-define-from-file=.env.json` — 빌드 성공.
- red→green 증명(CLAUDE.md B4) — 구현 서브에이전트가 7건 전부 뮤테이션→red→원복→green을 보고했지만 **그 보고를 그대로 받지 않고, 형태를 바꿔 이 세션이 직접 다시 깼다**(자기가 쓴 표기에서만 성립하는 red를 거르기 위해 — 이 저장소의 실측 선례):
  - 그라데이션 축: 서브에이전트는 `begin`·`end`를 함께 되돌렸다 → 이 세션은 **`end`만** `bottomRight`로 바꿔 red 확인(`Expected: Alignment.bottomCenter, Actual: Alignment.bottomRight`).
  - 카드 세로 순서: 서브에이전트는 차량명↔가격을 맞바꿨다 → 이 세션은 **옵션 칩 행만** 가격 위로 올려 red 확인(`Expected: a value less than <545.0>, Actual: <572.0>`) — 마지막 관계(가격<옵션칩)도 실제로 물린다는 뜻.
  - 드리프트 가드: 서브에이전트는 Dart 상수를 바꿨다 → 이 세션은 **반대 방향으로 web `ListingCard.tsx`의 `CARD_OPTION_COUNT`를 3→4**로 바꿔 red 확인(`Expected: <4>, Actual: <3>`). 웹 파일은 백업본으로 원복하고 `git diff web/`이 비었음을 확인했다.
  - 하단 인셋: 서브에이전트는 `SafeArea`를 `Builder`로 교체했다 → 이 세션은 **`SafeArea`를 남긴 채 `bottom: false`를 추가**해 red 확인(`Expected: ≤1752.0, Actual: 1788.0`) — 위젯 존재가 아니라 **축**이 물린다는 뜻.
  - 원복은 전부 백업본으로 했다(`git checkout` 미사용).
- Manual check(실제 렌더 육안 확인)는 3패스에서도 미실행 — 동일한 CanvasKit 환경 제약. **다만 이번 패스가 그 사각지대에서 실제 결함(그라데이션 축)을 하나 더 찾았으므로, 스펙이 원래 요구했던 "대장 등재"를 이번에 실행했다(DW-764).**

**Verification performed — 2패스(이 세션에서 직접 실행·관찰):**
- `flutter analyze` — 0 issues · `flutter test` — **466/466 전체 green**(1패스 460건 + 2패스 신규 6건) · `flutter build web --dart-define-from-file=.env.json` — 빌드 성공.
- **실측이 리뷰 주장 셋을 갈랐다.** 390×844 프로브 위젯 테스트를 직접 띄워 rect를 재고 파일은 지웠다(작업 트리 원상): ①meta 겹침은 **사실**(meta `x14–376,y276–294` vs 찜 `x338–382,y242–286` → 38×10px) ②1패스가 "2줄로 접힐 수 있다"고 판단해 고친 신뢰속성 행은 실제로는 **접히지 않는다**(3뱃지 행 폭 214.5px, 가용 ~310px, 한 줄 `dy 255–271`) — 미측정 가설이었다 ③차량명 실효 폰트는 14.0, 가격은 26.0으로 상대 비교 자체는 참이지만 **그걸 보던 단언은 항상 참이었다**.
- red→green 증명(CLAUDE.md B4) — 서브에이전트의 red/green 보고를 그대로 받지 않고, **표기 형태를 바꿔** 이 세션이 직접 다시 깼다(자기가 쓴 뮤테이션에서만 성립하는 red를 거르기 위해): ①`right: 52`→`right: 0`(Padding은 남김) → meta 겹침 테스트 red(`376.0 > 338.0`) ②가격 `fontSize` 줄 삭제 → red ③차량명만 30px로 지정(가격 26은 유지) → **상대 비교 단언만** red(`Expected greater than 30.0, Actual 26.0`) — vacuous가 아님을 이 형태로 확정 ④드리프트 가드는 서브에이전트가 시험한 Dart 쪽이 아니라 **web `options.ts` 쪽**을 바꿔 red 확인(반대 방향도 잡는다). 원복은 전부 백업본으로 했다(`git checkout` 미사용).
- Manual check(실제 렌더 육안 확인)는 2패스에서도 미실행 — 동일한 CanvasKit 환경 제약. 다만 이번엔 겹침·폭·폰트 크기를 **실측 좌표로** 확인했으므로 1패스보다 이 축들의 근거가 강하다.

**Verification performed — 1패스(이 세션에서 직접 실행·관찰):**
- `flutter analyze` — 0 issues(패치 적용 전·후 모두)
- `flutter test` — 패치 적용 후 **460/460 전체 green**(구현 단계 457건 + 패치로 추가된 신규 4건)
- `flutter build web --dart-define-from-file=.env.json` — 빌드 성공(패치 적용 후 재확인)
- red→green 증명(CLAUDE.md B4) — 구현 단계: 7개 시각 축 전부 뮤테이션→red→원복→green 확인(구현 서브에이전트 보고, 이 세션이 `flutter analyze`/`flutter test`/`flutter build web`으로 최종 상태를 직접 재확인). 패치 단계: 신규 검사 2건을 표본 삼아 직접 뮤테이션했다 — ① 홈 탭 AppBar 하단 보더를 되살리자 "AppBar 배경이..." 테스트가 실제로 red, 백업본으로 원복 후 green ② `hero_car_silhouette` 키를 지우자 "히어로 배경에 글로우·차 실루엣..." 테스트가 실제로 red, 백업본으로 원복 후 green. 원복은 전부 백업본으로 했다(`git checkout` 미사용 — 커밋 안 된 변경까지 날아가는 실측 사례가 이 저장소에 있다).
- 매트릭스 테스트 감사(I/O 매트릭스 6행) — 전부 실제로 통과하는 테스트로 커버됨을 직접 확인: 옵션 0/5개(`listing_card_test.dart`), 신뢰속성 0개(`listing_trust_widgets_test.dart`), 상세 3분기(본인/비로그인/타인, `listing_detail_screen_test.dart`).
- Manual check(실제 렌더 육안 확인)은 미실행 — 이 헤드리스 샌드박스의 CanvasKit `CONTEXT_LOST_WEBGL` 한계(선행 스토리 다수에서 재현된 동일 환경 제약). 대장에 등재된 사실 없음 — 이 스토리 자체가 그 한계를 이미 알고 있는 기존 대장 패턴을 그대로 따른다.

**Residual risks:**
- **DW-764(3패스 신규) — 시각 4축은 아직 사람 눈으로 확인된 적이 없다.** DW-755·759·760·735는 전부 육안 관찰에서 출발했는데 닫힌 근거는 위젯 단언뿐이다. 3패스가 바로 그 틈에서 AC①의 실제 위반(그라데이션 축)을 찾아냈으므로 **남은 세 축에도 같은 종류의 갭이 있을 수 있다.** 다음 실기기 세션에서 육안 대조가 필요하다.
- **DW-763(3패스 신규) — 대장 DW-738의 `status:` 주석이 낡았다.** 거기 적힌 원인(anon 3컬럼 42501)은 `806b3a6`에서 이미 해소됐고 남은 건 실기기 재확인뿐인데, 주석은 현재시제로 원인을 서술한다. 2패스가 실제로 그 주석을 믿고 계획 문서에 낡은 사실을 옮겨 적었다 — 대장 항목 수정 권한이 없는 리뷰 세션이라 새 항목으로만 남겼으니, **사람 세션이 DW-738 본문을 정정해야** 같은 오해가 끊긴다.
- **DW-765(3패스 신규, defer)** — 16.9가 만든 웹·앱 편차가 DW-761·762 외에 두 축 더 있다(카드 면책 문구·차종 칩 선택 상태). DW-761 결정을 내릴 때 **네 축을 한 목록으로** 보지 않으면 불완전한 근거 위에서 결정하게 된다.
- **앞 패스가 만든 결함이 3패스에서도 넷 나왔다** — 리뷰가 스스로 만든 문서 오류·제약 삭제·정본 문서 불일치가 반복되는 패턴이다. 계획 문서를 **재생성**하는 단계(에픽 컨텍스트 재컴파일)가 이 저장소에서 반복적으로 제약을 잃는 지점임이 이번에 다시 확인됐다(CLAUDE.md B8이 지목한 그대로).
- **DW-762(2패스 신규, defer)** — 옵션 칩도 웹·앱이 갈렸고(색·오버플로 표기), 거기에 더해 **오버플로 숫자 계산 기준까지 다르다**(웹=원본 배열 길이, 앱=중복 제거 후). 앞 둘은 스펙이 "스파인 우선"으로 확정한 의도된 편차지만 계수 기준은 계산 규칙 불일치라 통일이 필요하다. DW-761과 같은 결정에 묶여 있다.
- **1패스의 판단 하나가 미측정 가설이었다** — 신뢰속성 행을 `Wrap`에서 가로 스크롤로 바꾼 근거("3뱃지면 2줄로 접힐 수 있다")는 이번 실측에서 성립하지 않았다(214.5px / 가용 310px). 구현은 해가 없어 되돌리지 않았고 실측값을 주석·테스트로 남겼지만, **"재보기 전에 선언한" 사례가 이 스토리 안에 있었다**는 사실 자체는 남는다.
- **DW-761(신규, defer)** — 이 스토리로 신뢰속성 배치가 스파인 기준(사진 아래 행)이 됐지만, 실제 웹 코드는 2026-08-05부터 이미 오버레이 방식이라 이번 변경 이후 **웹·앱이 이 축에서 서로 다르게** 보인다. Epic 16의 "웹·앱이 같은 제품으로 보인다" 목표와 반대 방향일 수 있어 별도 판단이 필요하다.
- 상태바(status bar) 자체의 petrol 연속성을 검증하는 코드·테스트가 없다 — Flutter `AppBar`가 배경색으로 상태바 스타일을 자동 계산하는 것으로 보이나(SDK 소스 확인), 실기기/브라우저 육안 확인은 이 세션의 환경 제약으로 못 했다.
- 옵션 칩은 항상 최대 3개+오버플로만 그린다 — `DESIGN.md` §L128의 "밀도 높을 땐 대표 1개+외 N개" 2차 폴백은 구현하지 않았다(AC 문구 자체는 요구하지 않아 reject 처리, Review Triage Log 참고).
- 히어로 배경 장식(글로우·실루엣)은 목업의 정밀 SVG가 아니라 단순 도형(`RadialGradient`+`Icon`)이다 — 스펙이 "존재 자체"만 요구한다고 명시해 의도된 단순화다.

**Residual artifacts (커밋 밖에 남은 것):**
- 이 스펙 파일 자신의 마지막 frontmatter 갱신(`status: done` · `final_revision`)은 커밋 `85938d9` **이후**에 쓰이므로 그 커밋에 담기지 않는다 — 워크플로 구조상 정상이며, 다음 실행이 이 파일을 읽을 때만 쓰인다.
