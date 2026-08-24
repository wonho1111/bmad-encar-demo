# Epic 16 묶음 코드리뷰 (2026-08-10)

**범위:** `1e9cb33..af52c57` 의 `app/` — 앱 구현 40파일 +6,623/−801, 앱 테스트 43파일 +12,790
(Story 16-0 ~ 16-10 전체. 사용자가 스토리별 6회 대신 **1회 묶음**으로 결정)

**정본 컨텍스트:** `epic-16-context.md`(review_mode = full) + `project-context.md` + `docs/conventions.md`

## 어떻게 돌렸나

diff를 스토리 경계대로 5덩어리로 나누고(A 홈·카드·신뢰·찜 3,144줄 / D 사진·판매 2,187 /
B 채팅 1,617 / E 인증·라우팅·목록 1,530 / C AI 710), 각 덩어리에 4개 렌즈를 걸어 **20개 세션**을
병렬로 돌렸다. 나누면서 파일이 빠지는 것이 이 방식의 전형적 사고라, 나눈 뒤
`git diff --name-only` 전체 목록과 5개 diff의 `+++ b/` 합집합을 기계로 대조했다 — **40/40, 누락 0.**

- **렌즈 4개** = acceptance-auditor(①계약 위반) · verification-gap(②검사 사각지대) ·
  adversarial + edge-case-hunter(③회귀) — 사용자가 지정한 3축과 매핑.
- **실패한 레이어 없음**(20/20 완료).
- ⚠️ **스킬 step-02의 "리뷰 서브에이전트는 현 세션과 같은 모델 등급으로 돌린다"를 따르지 않았다.**
  `CLAUDE.md` B7이 "opus 단계도 내부에서 읽기와 판단을 분리한다 — diff·코드 읽기는 sonnet
  서브에이전트, 판단·종합만 opus"로 명시하고 CLAUDE.md가 기본 동작을 override하므로 리뷰어는
  sonnet, **최종 판정은 이 세션(opus)** 이 맡았다. 대신 아래 "실측" 표시가 붙은 항목은 전부
  오케스트레이터가 직접 코드를 열어 재확인한 것이다.
- ⚠️ **리뷰어에게 `flutter test`/`build`/`analyze` 실행을 금지**했다(WSL 메모리 — 20명이 동시에
  돌리면 스왑 스래싱으로 세션이 죽는다). 그래서 이 리뷰는 **정적 판독 기반**이고, 실행이 필요한
  검증은 아래 각 항목에 "미실행"으로 명시했다.

## 결과 요약

| 버킷 | 건수 |
|---|---|
| decision-needed(사람 판단 필요) | **2** |
| patch(수정 명백) | **16** (코드 9 + 검사 7) |
| defer(대장 등재) | **6** |
| dismiss(노이즈) | 3 |

**교차 검증된 것 3건** — 서로 모르는 리뷰어 2명이 같은 자리를 독립적으로 찍었다:
고아 사진→대표 승격(D/엣지 + D/적대) · `_RoomTile`의 폐기된 `ref`(B/인수 + B/엣지) ·
AI 게이트 입력 유실(C/인수 + C/엣지) · 찜 화면 인셋(A/검증 + A/적대).

---

## decision-needed (2)

### D1. 삭제가 반쯤 실패한 사진이 다음 저장에서 **대표 사진으로 승격**될 수 있다
- **위치:** `app/lib/features/listings/photo_sync.dart:313`(`saved` 필터) → `:320-341` → `:428-438`
- **출처:** edge-case-hunter + adversarial (독립 2건)
- **실측 확인(오케스트레이터):** 기전 전 구간을 코드로 따라가 확인했다 —
  `:308 next.addAll(undeletable)` 로 합류 → `:313 saved = next.where((p) => p.storagePath != null)`
  가 **`status`를 보지 않는다** → `:320 p.rowId != null` 분기로 `sort_order` UPDATE 성공 →
  `:339 order == 0`이면 `coverPath = p.storagePath`(이미 지워진 오브젝트 경로) →
  4단계가 그 경로에 `is_cover = true`.
- **트리거:** 사진이 1장뿐인 매물에서 그 사진을 삭제하다 ①Storage 삭제 성공 ②DB 행 삭제 실패
  (일시적 네트워크·DB 오류). 그러면 `saved`의 유일한 원소가 그 죽은 항목이라 반드시 `order == 0`.
- **결과:** 구매자 화면의 대표 이미지가 **없는 파일**을 가리킨 채 남는다. 판매자에게는
  "삭제 정보를 정리하지 못했어요" 안내만 뜨고, 그것이 방금 대표가 됐다는 사실은 안내되지 않는다.
- **왜 사람 판단이 필요한가:** 코드 주석(`:207-212`)이 밝히듯 **예전 방식(목록에서 아예 빼기)도
  문제였다** — 그러면 사용자가 재시도할 수단이 사라지고 DB엔 파일 없는 행이 영구히 남는다.
  그래서 "목록엔 남기되 대표 후보에서만 빼기"(최소)와 "3단계 재편입 자체를 막기"(근본)가 갈리고,
  후자는 대표 판정 규칙을 다루는 **[[DW-748]]과 한 덩어리**가 된다.
- **선택지:**
  - (a) **최소** — `saved` 필터 또는 `coverPath` 지정에서 `PhotoStatus.error` 항목 제외. 몇 줄.
  - (b) **근본** — DW-748(sort_order 중복·`(sort_order,id)` 최솟값 대표 판정)과 묶어 한 스토리로.
  - (c) 대장 등재만 하고 나중에.

### D2. 로그인 게이트가 **사용자 입력을 삼킨다** — `docs/conventions.md` §8 위반, 웹엔 있고 앱엔 없다
- **위치:** `app/lib/features/ai_search/ai_chat_screen.dart:92-101` (AI 질의) ·
  `app/lib/core/router/app_router.dart:224-253` (탭 리다이렉트 후 복귀)
- **출처:** acceptance-auditor + edge-case-hunter (독립 2건, C그룹) + edge-case-hunter (E그룹)
- **계약 원문(실측, `docs/conventions.md:210`):** *"행동 게이트는 사용자 입력을 삼키지 않는다:
  비로그인이 입력을 마친 뒤 게이트를 만나면, 그 입력을 보존했다가 로그인 복귀 시 복원한다
  (`redirectedFrom`은 경로만 나르고 폼 상태는 못 나른다 — 보존은 sessionStorage 등으로 명시 구현).
  **복원까지만 하고 자동 실행하지 않는다** — 과금 호출의 트리거를 페이지 로드에 매달면
  새로고침·뒤로가기가 재과금이 된다. (Story 11.3 히어로가 이 패턴의 첫 적용처.)"*
- **실측 확인(오케스트레이터):** 웹은 이 계약을 **전용 모듈로 구현**했다 —
  `web/src/lib/heroSearchHandoff.ts`(spec-11-3, `autoRun` 플래그로 게이트/즉시실행 구분).
  앱엔 대응 개념이 **전무**하다. 그리고 `app/test/ai_chat_screen_test.dart:888-937`은 오히려
  `expect(find.text('아반떼 찾아줘'), findsNothing)` 으로 **입력이 사라지는 것을 계약으로 고정**하고
  있다 — 검사가 위반을 지키고 있는 상태다.
- **범위 주의:** `spec-16-6`은 "비로그인 `/wishlist`·`/chat`·`/sell` 진입 → `/login` 리다이렉트
  (기존 동작 유지)"를 명시 승인했다. 그건 **튕겨내는 것**만 승인한 것이고 **되돌려 보내는 것**은
  다루지 않았다 — 두 주장을 쪼개서 판정했다(리뷰어 한 명은 이 승인을 근거로 전체를 기각했는데,
  그 기각은 범위를 넘는다).
- **왜 사람 판단이 필요한가:** 작은 수정이 아니다. Flutter엔 sessionStorage가 없어 보존 매체를
  고르고, 로그인 후 복귀 경로를 라우터에 새로 만들어야 한다. 그리고 §8이 **"복원만 하고 자동
  실행 금지"** 를 함께 요구하므로 UX 결정이 따라붙는다.
- **선택지:** (a) 스토리로 만들어 지금 · (b) 대장 등재 후 다음 라운드 · (c) AI 질의 보존만 먼저.

---

## patch — 코드 9건 (수정이 명백함)

| # | 무엇 | 위치 | 심각도 |
|---|---|---|---|
| P1 | `_RoomTile`이 폐기 가능한 `ref`를 필드로 들고 `.then()`에서 씀 → 방을 연 채 로그아웃/세션만료 시 `StateError`. **같은 리포가 이미 겪고 고친 버그**(`app_router.dart:528-546` 주석: *"riverpod 3.3.2의 `_assertNotDisposed()`가 unmounted element에 대해 진짜 StateError를 던진다 — assert가 아니라 **모든 빌드 모드에서**"*). 해법도 거기 있다: push **전에** `ProviderScope.containerOf(context, listen:false)`를 잡아 그 컨테이너로 `invalidate`. `grep "final WidgetRef ref;" app/lib` = **이 파일 하나뿐**(실측) | `chat_list_screen.dart:114,155-165` | medium |
| P2 | 하단 여백 이중 계산. **셸 4탭 중 찜 화면만** 옛 패턴(실측: home:113 `paddingOf` ✅ / chat_list:84 ✅ / sell:313 ✅ / **wishlist:59 `viewPadding` ❌**) | `wishlist_screen.dart:59` | low |
| P3 | 실시간 채널 구독 중 `subscribe()`가 예외를 던지면 `return` 전에 전파돼 handle이 null → `dispose`의 `removeChannel`이 안 불림 → 채널이 등록된 채 잔류(`realtime_client 2.8.0`은 `subscribe` **전에** `channels.add`) | `chat_room_screen.dart:67-83, 260-268` | low |
| P4 | 채팅 버블 `Text`에 `softWrap`/`overflow` 없음 — 공백 없는 긴 URL이 버블 밖으로. 웹은 같은 결함을 `break-words`로 이미 고침 | `chat_room_screen.dart:845` | low |
| P5 | `fetchRooms()`만 인증 가드·try/catch가 없다(형제 `fetchUnreadTotal`·`fetchUnreadByRoom`·`markRoomRead`는 전부 있음, 실측). 채팅 탭 `onActivate`도 비로그인 확인 없이 무효화 → 리다이렉트 **전에** 요청이 나감 | `chat_repository.dart:156` · `app_router.dart:155-158` | low |
| P6 | 대장 **DW-770 번호가 두 항목에 중복**(5956 카드 radius / 6063 히어로 글로우). 장부 전체에서 **유일한 중복**(실측). DW-772·773·775가 이미 카드 쪽 DW-770을 참조 중이라 관계망이 엉킨다 | `deferred-work.md:5956,6063` | medium |
| P7 | 헤드라인 문서 드리프트 — 코드는 `fontSize: 24`·`\n` 없음(1줄, 실측), 검사도 24를 단언(`home_ai_entry_test.dart:379`). 그런데 **DW-767 `status: done`은 "36px 2줄로 해소"**, **spec-16-10 AC(79행)는 "2줄로 나타나고"** 로 남아 있다 | `deferred-work.md:5932` · `spec-16-10…md:29,79` | medium |
| P8 | 실루엣 문서 드리프트 — 코드는 웹 규칙으로 통일(`home_screen.dart:533-534` `right:-4%·bottom:-6%`, 실측). 그런데 `epic-16-context.md:54`는 여전히 **"앱 출시값 `top:-14%` · 하나로 합치지 말 것"**, `:49`는 "우상단". [[DW-776]]도 "아직 안 고쳤다"로 열려 있다 | `epic-16-context.md:49,54` | medium |
| P9 | 16-0 역할 통합의 잔재 주석 — `:11` "가입에서 고를 수 있는 역할은 buyer/seller 뿐"은 **이 커밋이 거짓으로 만들었고**, `:25` `/// 가입 화면에서 선택 가능한 역할(admin 제외).` 은 아래가 비어 있는 고아 doc 주석(실측) | `user_role.dart:11,25` | low |

> **P6~P8은 어제 사용자 지시로 루프 없이 직접 고치면서 문서를 함께 안 고친 결과다.**
> 코드가 틀린 게 아니라 **문서가 뒤처졌다.** 그냥 두면 다음 작업이 옛 문서를 읽고 되돌린다
> (`project-context.md`가 경고하는 "사본이 원본보다 늙는" 실패 모드).

## patch — 검사 7건 (전부 "테스트가 초록인데 안 보는 것")

이 에픽의 존재 이유가 바로 이 축이었는데, 아직 남아 있다.

| # | 무엇이 무검사인가 | 위치 |
|---|---|---|
| T1 | **FR11(판매완료 비노출) 검사가 소스 문자열 매칭**이다 — `expect(fetchPopularListingsBody, contains('_buyerQuery'))`(실측). 주석에 그 식별자만 있어도 통과한다. sold가 실제로 걸러지는지 HTTP mock으로 보는 테스트 0건(같은 리포의 다른 파일들은 그 mock을 이미 쓴다) | `listings_repository_card_columns_test.dart:110` |
| T2 | 채팅 **재전송 멱등(23505) 경로**를 어떤 테스트도 실행하지 않는다 — 순수 판정 함수만 테스트하고, 위젯 테스트의 fake가 실구현을 통째로 덮는다. `grep 23505 app/test` = 0 | `chat_repository.dart:242-266` |
| T3 | 찜 버튼 `variant`(card/inline) 분기 무검사 — `grep WishButtonVariant app/test` = **0**(실측). 상세 화면의 `variant: inline`을 지워도 전부 green | `wish_button.dart:137,154` |
| T4 | 옵션 칩의 petrol 색 무검사 — `grep brandPetrol listing_card_test.dart` = **0**(실측). muted 칩만 색을 단언한다 | `listing_card.dart:315-324` |
| T5 | `dispose()`의 구독 해제 호출 무검사 — 테스트의 `unsubscribeOverride`가 둘 다 no-op 람다 | `chat_room_screen.dart:181-188` |
| T6 | INSERT 실패 시 **고아 오브젝트 보상 삭제**를 단언하는 검사 0건 | `photo_sync.dart:361` |
| T7 | `restoreInputOnFailure = true` 분기(히어로 자동제출 실패 시 문장 복원)를 실행하는 테스트 0건 — 이번 diff 신규 파라미터 | `ai_chat_screen.dart:163` |

## defer (6) — 대장 등재

| 무엇 | 왜 미루나 |
|---|---|
| 사진 업로더 썸네일(`SizedBox(height:140)`)이 시스템 글자 크기 확대 시 오버플로 가능 | **미실행 추정**이다(리뷰어가 정직하게 명시, 나도 실행 금지로 확인 못 함). [[DW-778]]과 **같은 계열·다른 위치**라 함께 처리 |
| `sold` 쓰기 차단이 `listing_images` 3정책에만 있고 `storage.objects`(0013)엔 없음 | 앱 정상 흐름으로는 도달 불가(`sell_controller`가 `listings` UPDATE를 먼저 통과해야 함). 직접 API 호출자에겐 열려 있는 잠재 구멍 |
| `searchControllerProvider`가 비-autoDispose 싱글턴이고 auth 변경 시 무효화 경로가 없음 | [[DW-758]](로그인 전환 직후 옛 결과) 인근. 트리거가 배경 타이밍이라 미확인 |
| 디코딩 실패가 항상 `retryable: true`(확장자만 검증) | [[DW-745]] 계열(실기기 미검증). 실기기 확인이 선행 |
| AI 대화 이력(`_messages`)에 길이 상한 없음 | 되묻기 칩이 긴 세션을 유도하는 신규 유인. 현재 규모에선 무해 |
| `authStateProvider` 리스너가 `tokenRefreshed`까지 로그인/로그아웃과 동일 처리 | 불필요한 재평가·재조회 반복. 기능 영향 없음 |

## dismiss (3)

- 되묻기 칩 문구가 500자를 넘으면 안내 문구가 부적절 — 서버가 고정 3개 칩만 보내는 현재 계약에선 발생 불가(리뷰어 스스로 low·가정부 명시).
- 200 OK인데 본문 전체가 깨진 경우 빈 말풍선 — **필드 단위 폴백은 팀이 의도·테스트한 설계**(`ai_search_test.dart`가 고정). 더 넓은 경계로 확장하는 것은 이 리뷰의 축이 아니다.
- 그래핌 500자 vs 서버 코드포인트 1000자 — 결합문자를 쌓는 비현실적 입력이고, 결과도 결국 서버 422로 이미 처리된다.

## 이 리뷰가 보지 못한 것 (추측 아님)

- **실행 검증 전부.** `flutter test`·`analyze`·빌드·실기기를 한 번도 돌리지 않았다(메모리 보호).
  따라서 "테스트가 없다" 계열은 확실하지만, "이 코드가 실제로 터진다"는 **P1·D1 포함 전부 미확인**이다.
- **웹 코드 자체.** 범위를 `app/`으로 한정했다. 웹은 [[DW-780]] 등으로 따로 열려 있다.
- **DB 실측.** RLS/GRANT는 마이그레이션 파일 읽기로만 확인했고 실제 데이터를 넣어 조회해 보지 않았다.

---

# 처리 결과 (2026-08-10, 사용자 결정 반영)

## 사용자 결정
- **D1**(고아 사진→대표 승격) → **근본수정**. *"데이터 쌓이는 건 좀 치명적인 것 같아서, 물론 과제긴 하지만 그래도 실사용 기반으로 하는 거니까."* → 별도 스토리로 [[DW-748]]과 묶어 처리한다(이 패치 묶음에 넣지 않았다).
- **D2**(§8 입력 보존) → **앱은 예외 처리, 웹은 손대지 않음**. *"앱에서는 그 기능 신경 쓰지 마, 따로 뭐 건들지를 마. 앱에서는 그냥 검색 누르면 로그인으로 넘어가고 끝."* → 코드 0줄, 계약 문서만 수정(커밋 `1d4007f`). 경위는 `docs/decisions-archive.md`.
- **patch 15건** → 전부 적용.

## ⛔ 실측으로 기각한 지적 1건 — 고치지 않았다

**"공백 없는 긴 URL이 채팅 버블 밖으로 넘친다"**(adversarial, confidence medium, 리뷰어가 *"Flutter 텍스트 레이아웃엔진의 정확한 줄바꿈 동작을 직접 확인하지는 못했다"* 고 스스로 단서를 달았다).

고치기 전에 **재봤다** — `chat_room_screen_test.dart`의 기존 하네스에 임시 프로브를 넣어 390×844에서 공백 0개 200자 본문을 렌더하고 오버플로를 셌다:

```
ZZPROBE_RESULT overflowCount=0 painted=Size(268.5, 240.0) first=none
```

버블 최대폭은 화면의 75% = 292.5px인데 **그려진 폭이 268.5px**로, Flutter가 공백 없는 긴 토큰을 알아서 여러 줄로 끊었다. 웹에는 **실재했던** 결함이고(390px에서 `scrollWidth 672 > clientWidth 390` 실측 후 `break-words`로 수정) 코드 구조도 닮아 그럴듯했지만, **Flutter는 그렇지 않다.**

고쳤다면 사용자 텍스트에 폭 0 줄바꿈 문자를 끼워 넣는 코드가 들어갈 뻔했다 — 복사할 때 그 문자가 딸려간다. **"재보기 전엔 선언하지 않는다"(CLAUDE.md B4)가 실제로 값을 한 번 더 증명한 자리다.** 프로브는 판정 후 백업본으로 원복했다(`git checkout` 금지 — 커밋 안 된 패치까지 날아간다).

## 적용한 것

**코드 5건** — `chat_list_screen`(폐기 ref → `ProviderScope.containerOf`, 고아 필드 제거) · `chat_room_screen`(subscribe 예외 시 채널 누수 차단) · `wishlist_screen`(하단 인셋 `paddingOf`) · `app_router`(찜·채팅 탭 비로그인 가드 — 리뷰는 채팅만 지목했으나 같은 결함이라 함께) · `user_role`(거짓이 된 주석 + 고아 doc 주석)

**문서 4건** — DW-770 번호 중복 해소(나중 등재분 → **DW-787**, 참조 4곳 동반 수정, 장부 중복 0 확인) · DW-767·spec-16-10 AC에 "실제는 24px 한 줄" 정정(원문 보존) · `epic-16-context` 실루엣 지시 폐기 표시 + 현재 값 · **[[DW-776]] done 처리**(이미 고쳐졌는데 장부만 열려 있었다)

**검사 6건 — 전부 뮤테이션 red → 원복 green**

| 검사 | 뮤테이션 | 결과 |
|---|---|---|
| FR11 wire(`status=eq.on_sale`) | `_buyerQuery` 호출 제거 + **식별자를 주석에만 남김** | **기존 소스텍스트 검사는 통과**, 새 검사만 red ⭐ |
| 멱등 재전송 23505 실경로 2건 | 재조회에서 `client_message_id` 필터 제거 | 새 검사만 red |
| 구독 해제 handle | `dispose`의 해제 호출 제거 | 새 검사만 red |
| 옵션 칩 petrol | 색 분기를 muted 고정 | 새 검사만 red, **나머지 476개 전부 green** |
| 찜 버튼 variant | 상세의 `variant: inline` 인자 제거 | 새 검사만 red |
| 사진 INSERT 실패 보상 삭제 | `deleteObject` 호출 제거 | 새 검사만 red |
| 히어로 자동제출 실패 복원 | `restoreInputOnFailure` 조건 제거 | 새 검사만 red |

## 검증

`flutter analyze` 0건 · `flutter test` **496 통과**(작업 전 487, +9) · 실기기(`SM-G991N`, mobile MCP) 설치·육안 확인

⚠️ **실기기 확인 중 발견한 것(제 변경과 무관, 기록만)**: `app/.env.json`이 **로컬 Supabase(`127.0.0.1:55321`)** 를 가리키고 있었고 그게 꺼져 있어 매물이 무한 로딩이었다. 폰에서 `127.0.0.1`은 폰 자신이라 애초에 닿을 수 없다. `.env.json.prod`로 다시 빌드하니 정상 로드됐다(`03-home-prod.png`). `.env.json`은 gitignore 대상이라 저장소에는 영향이 없고, **폰에 남은 APK는 운영 설정 빌드**다.

## 실기기에서 확인한 것 / 못 한 것

- ✅ 홈: 히어로(얼룩 없는 균일 면·하단 실루엣·한 줄 헤드라인·얇은 검색창·`전체` 선택 칩)·매물 카드 사진 로드 — `03-home-prod.png`
- ✅ **찜 탭 → 로그인 리다이렉트 정상** — 이번에 넣은 비로그인 가드가 내비게이션을 깨지 않는다는 확인 — `04-wish-tab-anon-redirect.png`
## ✎ 2026-08-10 추가 — 사용자가 테스트 계정을 줘서 위 ❌ 두 건을 다시 봤다

사용자가 `seller@test.com` / `buyer@test.com`을 제공했고, **운영 Supabase에서도 그대로 로그인된다**(로컬 시드 계정인 줄 알았는데 운영에도 있다). 그래서 "로그인이 없어 못 봤다"던 항목을 실기기에서 다시 확인했다.

- ✅ **찜 목록 정상 렌더** — `05-wishlist-logged-in.png`. 덤으로 **로그아웃 상태라 못 봤던 신뢰속성 행**(무사고·1인소유가 사진 아래·차량명 위)도 이번에 처음 눈으로 확인했다. 옵션 칩 3개 + "외 1개", 가격 강조도 함께 보인다.
  - ⚠️ **다만 하단 여백 자체는 여전히 판정 불가다** — 찜 매물이 1건뿐이라 목록이 화면을 채우지 못해 하단 여백 차이가 드러나지 않는다. 이 축은 계속 코드 일치(형제 3탭과 동일)와 위젯 테스트가 근거이고, **육안 확인은 안 된 것으로 남긴다.**
- ✅ **채팅 목록 → 방 열기 → 뒤로가기 정상** — `06`·`07`·`08`. P1(`_RoomTile`의 폐기 ref)이 고친 **바로 그 pop-back 경로**를 실제로 태웠고, `logcat`에 `StateError`·`_assertNotDisposed`·`Unhandled` 어느 것도 없다(앱 프로세스 생존 확인).
  - ⚠️ **크래시를 유발하는 비정상 경로는 여전히 미확인** — 트리거가 "방을 연 채 로그아웃/세션 만료"인데 방 화면이 셸을 덮고 있어 그 상태에서 로그아웃할 조작 경로가 없다. 즉 **"고친 코드가 정상 경로를 안 깼다"까지는 실측했고, "원래 터지던 것이 이제 안 터진다"는 실측하지 못했다.**

---

- ❌ (아래는 위 추가 확인 이전 시점의 기록이다) **찜 목록의 하단 여백 변화는 눈으로 못 봤다** — 로그인이 필요한데 운영 계정 자격증명이 없다. 지금 근거는 **형제 3개 탭과의 코드 일치**뿐이고, 시스템 인셋을 실제로 넣고 재는 검사는 이 화면에 없다(`FakeViewPadding`을 쓰는 테스트는 `listing_detail_screen_test.dart` 하나뿐).
- ❌ 채팅방 크래시 자리(`_RoomTile`)의 **실제 재현/수정 확인** — 트리거가 "방을 연 채 로그아웃/세션 만료"라 로그인이 필요하다. 지금 근거는 같은 리포가 이미 실측·기록한 선례와의 구조 일치뿐이다.
