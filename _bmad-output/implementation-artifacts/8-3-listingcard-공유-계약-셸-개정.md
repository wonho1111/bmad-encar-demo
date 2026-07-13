# Story 8.3: ListingCard 공유 계약 셸 개정

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a web·app·api 개발자,
I want ListingCard 계약에 이미지·조회수·신뢰속성 필드 자리를 먼저 확정하길,
so that 이후 에픽들이 계약 drift 없이 같은 데이터 셰이프를 공유한다.

> **이 스토리의 성격 (개발자 필독):** 8.1(토큰)·8.2(UI 프리미티브)에 이은 **세 번째 파운데이션 스토리**다. 이번 증분(이미지·신뢰속성·조회수)이 건드릴 **모든 신규 필드의 이름·자리를 한 번에** `docs/conventions.md §4`(단일 출처)와 web·api·app 3소비처 타입에 `nullable`로 선점한다 — **"계약은 여기서 1회 확정하고, 뒤 에픽은 값만 채운다"**(Epic 9=image_url/image_count, Epic 10=accident_status/is_single_owner/is_non_smoker, Epic 11=view_count). **DB 컬럼은 이 스토리에서 만들지 않는다** — 해당 컬럼이 아직 없으므로 값은 항상 `null`/미전달이고, 그래도 타입은 컴파일·렌더된다는 걸 실측으로 증명하는 게 이 스토리의 검증 핵심이다. A3 외과적 변경: 계약 문서 1곳 + 타입 3곳만 건드린다 — **화면 렌더링(JSX)·DB 마이그레이션·`select()` 컬럼 목록·`sql_guard.py` 화이트리스트는 이 스토리 범위 밖**이다(아래 "건드리지 않을 것" 참고).

## Acceptance Criteria

1. **(계약 필드 1회 확정 — AC-CONTRACT-1)** `docs/conventions.md §4`(ListingCard 계약, 단일 출처)에 이번 증분의 **모든 신규 필드 자리를 한 번에** nullable로 선점한다: `image_url`(대표 서명 URL) · `view_count` · `image_count` + **신뢰속성** `accident_status`(`'무사고'|'단순교환'|'사고'` 중 하나 또는 null) · `is_single_owner` · `is_non_smoker` — 전부 snake_case wire로 명문화된다. 값을 채우는 건 후속 에픽(9·10·11) 몫이며, 이 스토리는 **자리만** 만든다.
2. **(이미지 null 계약)** `image_url`이 null이면 클라가 "사진 준비중" 5:3 플레이스홀더를 렌더함이 **계약의 일부**로 conventions.md에 규정된다(변형 세트 {thumb/card/full}은 클라 렌더 파생이지 wire 계약이 아니라는 점도 명시).
3. **(찜은 wire 필드 아님)** 찜(wishlist) 상태는 ListingCard **wire 필드로 추가하지 않는다** — "내가 찜했는지"는 사용자별 오버레이라 별도 조회/조인으로 처리한다는 원칙이 conventions.md에 문서화된다(계약 오염 방지, Epic 10.5가 실제 구현).
4. **(AI 카드 계약 공유 문서화)** AI 검색 응답 카드(`SearchResponse.listings[]`)도 동일 ListingCard 계약을 공유함이 conventions.md에 명시된다.
5. **(하위호환 컴파일·렌더 — 3소비처)** 소비할 이미지·신뢰속성·조회수 데이터가 아직 DB에 없어도(컬럼 자체가 존재하지 않음) web·api·app 3소비처의 타입이 신규 필드를 **전부 optional/nullable**로 받아 **컴파일·타입체크·기존 렌더가 깨지지 않는다** — 기존 100건(신규 필드 미전달) 하위호환을 직접 실행·관찰로 확인한다.
6. **(크로스에픽 체크리스트)** "계약에 필드를 추가·변경할 땐 web·api·app 3소비처를 동시 갱신한다"는 규칙이 conventions.md에 **체크리스트 형태**로 박혀, 후속 에픽(9·10·11)이 참조할 수 있다.

## Tasks / Subtasks

- [x] **Task 1 — `docs/conventions.md` §4 개정 (AC: 1, 2, 3, 4, 6)**
  - [x] 기존 §4의 `ListingCard 필드(snake_case)` 줄을 확장: 기존 7필드(`id, manufacturer, model, year, price, mileage, region`)에 **이미 코드에는 있으나 문서엔 빠져 있던 `seller_name`(nullable, 0007 비정규화)**을 함께 명문화(문서-코드 drift 정정 — 아래 Dev Notes "발견한 문서 drift" 참고)한다.
  - [x] 신규 6필드를 **전부 nullable**로 추가: `image_url`(대표 서명 URL, null→"사진 준비중" 5:3 플레이스홀더가 계약의 일부) · `view_count`(int) · `image_count`(int) · `accident_status`(`'무사고'|'단순교환'|'사고'`|null) · `is_single_owner`(bool|null) · `is_non_smoker`(bool|null). 각 필드 옆에 "값 채움 = Epic N" 주석으로 소유 에픽을 명시.
  - [x] "찜(wishlist)은 ListingCard wire 필드가 아니다 — 사용자별 오버레이, 별도 조회/조인" 한 줄을 §4에 추가.
  - [x] "AI 검색 응답 카드도 동일 ListingCard 계약을 공유한다"를 §4에 명시(이미 응답 포맷 줄에 있으나 계약 공유를 명확히 재확인).
  - [x] **계약 변경 체크리스트**를 §4 말미에 추가(AC6): 필드 추가·변경 시 갱신할 3+1곳(conventions.md 자신 · web `ListingCard.tsx`의 `ListingCardData` · api `schemas/ai.py`의 `ListingCard` · app `listing.dart`의 `ListingCardData`) + "값까지 채울 때는 `listing_cards.py`·`sql_guard.py` ALLOWED_COLUMNS도 락스텝"이라는 후속 주의를 덧붙인다.

- [x] **Task 2 — web 타입 계약 개정 (AC: 1, 2, 5)**
  - [x] `web/src/components/listings/ListingCard.tsx`의 `ListingCardData` 타입(현재 12~21행)에 신규 6필드를 **optional + `| null`**로 추가. 기존 파일이 필드를 snake_case로 직접 노출하는 로컬 관례(`seller_name`과 동일 패턴)를 그대로 따른다 — camelCase 매핑층을 새로 만들지 않는다.
    ```ts
    export type ListingCardData = {
      id: string;
      manufacturer: string;
      model: string;
      year: number;
      price: number;
      mileage: number;
      region: string;
      seller_name?: string | null;
      // 증분 신규 — 전부 nullable, 값 채움은 후속 에픽(Epic 9/10/11)
      image_url?: string | null;
      view_count?: number | null;
      image_count?: number | null;
      accident_status?: '무사고' | '단순교환' | '사고' | null;
      is_single_owner?: boolean | null;
      is_non_smoker?: boolean | null;
    };
    ```
  - [x] 컴포넌트 본문(23~45행, JSX 렌더)은 **건드리지 않는다** — 신규 필드 렌더는 Epic 9(카드 레이아웃 B)의 몫.
  - [x] `web/src/lib/api/aiSearch.ts`의 `isValidListing`(103~115행)은 **수정하지 않는다** — 신규 필드가 optional이라 필수 7필드 가드만으로 타입이 그대로 성립한다(과잉 검증 금지, A2). 대신 파일 상단 주석(11~12행 "listings 원소 = ListingCardData 7필드")이 이제 부정확해지므로 "7필드(+증분 nullable 필드)"로 한 단어만 정정한다.

- [x] **Task 3 — api Pydantic 계약 개정 (AC: 1, 2, 4, 5)**
  - [x] `api/app/schemas/ai.py`의 `ListingCard` 모델(60~69행)에 신규 6필드를 **`... | None = None`**으로 추가:
    ```python
    class ListingCard(BaseModel):
        """매물 카드 — conventions.md §4 확정 계약. 증분 신규 6필드는 전부 nullable
        (값 채움은 후속 에픽: image_url·image_count=Epic 9, accident_status·is_single_owner·
        is_non_smoker=Epic 10, view_count=Epic 11)."""

        id: str
        manufacturer: str
        model: str
        year: int
        price: int       # 원(KRW)
        mileage: int     # km
        region: str
        image_url: str | None = None
        view_count: int | None = None
        image_count: int | None = None
        accident_status: Literal["무사고", "단순교환", "사고"] | None = None
        is_single_owner: bool | None = None
        is_non_smoker: bool | None = None
    ```
    (`seller_name`은 api 응답 계약에 없음 — web/app이 Supabase에서 직접 읽는 필드라 api `ListingCard`엔 원래도 없다. 추가하지 않는다.)
  - [x] `api/app/graph/listing_cards.py`(`SELECT_COLUMNS`·`rows_to_cards`)는 **수정하지 않는다** — 신규 필드가 전부 기본값 `None`인 optional이라 기존 위치 인자 매핑(7필드)이 그대로 유효하다. 파일 상단 주석(1~7행 "두 노드 모두 동일한 7필드")에 "(+ 증분 nullable 6필드, 기본 None — Epic 9/10/11이 값을 채울 때 SELECT_COLUMNS와 락스텝 확장)" 한 줄만 보강한다.
  - [x] `api/app/db/sql_guard.py`의 `ALLOWED_COLUMNS`(34~38행)는 **건드리지 않는다** — DB에 아직 없는 컬럼명을 화이트리스트에 넣으면 오히려 오해를 유발한다(LLM이 실제로 존재하지 않는 컬럼을 참조하는 SQL을 만들 근거가 없음, AI 프롬프트 스키마도 이 스토리에서 안 바뀜). 신뢰속성 컬럼이 실제로 생기는 **Story 10.1이 "sql_guard 화이트리스트·AI 프롬프트 스키마·ListingCard·web/app 매퍼 락스텝"으로 함께 갱신**한다(epics 10.1 AC 원문).

- [x] **Task 4 — app(Flutter) 타입 계약 개정 (AC: 1, 2, 5)**
  - [x] `app/lib/features/listings/listing.dart`의 `ListingCardData` 클래스(20~75행)에 신규 6필드를 **nullable 필드 + `fromMap`에서 snake_case→camelCase 매핑**으로 추가 — 기존 `sellerName`(29·39·63·72행) 패턴을 그대로 따른다(web과 달리 app은 이미 camelCase 매핑 관례가 확립돼 있음, A3 기존 스타일 계승):
    ```dart
    class ListingCardData {
      const ListingCardData({
        required this.id,
        required this.manufacturer,
        required this.model,
        required this.year,
        required this.price,
        required this.mileage,
        required this.region,
        this.sellerName,
        this.imageUrl,
        this.viewCount,
        this.imageCount,
        this.accidentStatus,
        this.isSingleOwner,
        this.isNonSmoker,
      });

      // ...기존 7필드 그대로...
      final String? sellerName;
      final String? imageUrl;
      final int? viewCount;
      final int? imageCount;
      final String? accidentStatus; // '무사고'|'단순교환'|'사고'|null — Dart는 별도 enum 없이 nullable String으로 단순 통과(A2)
      final bool? isSingleOwner;
      final bool? isNonSmoker;

      static ListingCardData? fromMap(Object? raw) {
        // ...기존 필수 7필드 검증 그대로(변경 없음)...
        final sellerName = raw['seller_name'];
        return ListingCardData(
          // ...기존 7필드...
          sellerName: sellerName is String ? sellerName : null,
          imageUrl: raw['image_url'] is String ? raw['image_url'] as String : null,
          viewCount: _asInt(raw['view_count']),
          imageCount: _asInt(raw['image_count']),
          accidentStatus: raw['accident_status'] is String ? raw['accident_status'] as String : null,
          isSingleOwner: raw['is_single_owner'] is bool ? raw['is_single_owner'] as bool : null,
          isNonSmoker: raw['is_non_smoker'] is bool ? raw['is_non_smoker'] as bool : null,
        );
      }
    }
    ```
  - [x] `app/lib/features/listings/listing_card.dart`(위젯 렌더)는 **건드리지 않는다** — 신규 필드 렌더는 Epic 16(Flutter 증분 반영)의 몫.
  - [x] `app/lib/features/listings/listings_repository.dart`의 select 컬럼 문자열(38~40행)은 **건드리지 않는다** — DB에 신규 컬럼이 없으므로 그대로 둔다.

- [x] **Task 5 — 검증 (AC: 5)**
  - [x] **web**: `web/`에서 `next build` 실행 → TS strict 0에러로 통과 확인(신규 optional 필드가 기존 `.returns<ListingCardData[]>()` 호출부·`isValidListing`과 충돌 없음을 컴파일로 증명).
  - [x] **web 회귀 관찰(B4)**: dev 서버 백그라운드 기동 → `/health`(또는 `/`) 200 확인 → Playwright로 `/`(로그인 홈 미리보기)와 `/search`(목록) 두 페이지를 로드해 **기존 카드가 여전히 정상 렌더**되는지 확인(제조사·모델·연식·가격·주행거리·지역·판매자명, 콘솔 에러 0). 신규 필드 렌더는 검증 대상 아님(값도 없고 화면도 없음) — 오직 "타입 확장이 기존 렌더를 안 깼다"만 확인.
  - [x] **api**: `api/`에서 `python -c "from app.schemas.ai import ListingCard; print(ListingCard(id='1', manufacturer='현대', model='아반떼', year=2020, price=15000000, mileage=50000, region='서울'))"` 로 신규 필드 없이도 인스턴스화되는지(전부 기본값 `None`) 확인. 이어서 관련 기존 pytest(`api/tests/test_ai_search.py`·`api/tests/test_sql_rag_node.py` 등 `ListingCard`/`listing_cards` 관련 스위트)를 실행해 회귀 없음을 확인(라이브 LLM 호출이 필요한 `test_live_smoke.py`는 이 스토리 범위 밖이므로 생략 가능).
  - [x] **app**: `app/`에서 `dart analyze` (또는 `flutter analyze`) 실행 → 0 issue 확인(신규 nullable 필드 추가가 기존 `ListingCardData` 생성 호출부를 깨지 않음을 정적 분석으로 증명). 별도 실폰 E2E는 화면 변경이 없으므로 생략(A2 — 검증 표면을 실제 변경 범위에 맞춤).
  - [x] `web/.next` 캐시 삭제, 임시로 띄운 dev 서버 프로세스 종료.

### Review Findings

_bmad-code-review(2026-07-14) — Blind Hunter·Edge Case Hunter·Acceptance Auditor 3레이어 병렬(opus). Auditor 판정=스펙 충실 이행(AC1~6 전부 충족, File List 6개 정확, non-goal 준수). 오탐 5건 dismiss(Literal import는 ai.py:7에 존재·`_asInt`는 실패 시 null 반환·TS seller_name은 설계상 정상·문서표 필드순서는 named 필드라 무의미·"7필드" docstring은 SELECT 기준이라 유효)._

- [x] [Review][Patch] (결정 해소 2026-07-14 → 옵션1 "문서 하드닝" 채택, 적용 완료) `docs/conventions.md §4`에 신규 필드 "계약-외 값" 정규화 규칙 명문화 [docs/conventions.md §4] — 3소비처 검증 비대칭(값이 흐르는 Epic 9/10/11에서 활성화될 5종)을 코드 변경 없이 계약 문서로 못박아 소비 에픽이 참조하게 한다: (1) **accident_status 도메인 밖 값 → 뱃지 없음/미표시**(Dart `listing.dart:89`·web `ListingCard.tsx:25`은 임의 문자열 통과, api만 `Literal` 강제). (2) **image_url 빈 문자열("")도 null과 동일 취급 → "사진 준비중" placeholder**(`listing.dart:86`·`ListingCard.tsx:22`). (3) **view_count/image_count 음수 → 0 하한**(3소비처, `listing.dart:11-13`·`ai.py:73-74`). (4) bool 필드는 참/거짓/미상(null) 3상태이며 소비처 파싱 관례차(Dart strict `is bool` vs Pydantic 강제변환, `listing.dart:90-91`·`ai.py:76-77`)를 명시. (5) web `isValidListing`(`aiSearch.ts:103-115`)이 신규 필드를 검증하지 않으므로 렌더 소비처가 방어적으로 읽어야 함을 §4.1 체크리스트에 주의로 추가.
- [x] [Review][Patch] 헤더 주석 "사진 없음(서비스 전체가 사진 미사용)"이 이번에 추가한 `image_url` 계약과 모순 [web/src/components/listings/ListingCard.tsx:2, app/lib/features/listings/listing.dart:2] — 이번 변경이 만든 거짓 진술(파일 자체 헤더가 새 계약을 부정). "현재 사진 렌더 없음(image_url 계약 자리 예약, 값·표시는 Epic 9)"로 정정 완료.

## Dev Notes

### 발견한 문서 drift — `seller_name`이 conventions.md §4에 없음
현재 `docs/conventions.md §4`는 ListingCard를 7필드(`id, manufacturer, model, year, price, mileage, region`)로만 적고 있지만, 실제 코드(`web/src/components/listings/ListingCard.tsx`·`app/lib/features/listings/listing.dart`)는 이미 `seller_name`(nullable, 0007 비정규화)을 8번째 필드로 갖고 있다. api `ListingCard`(`schemas/ai.py`)엔 `seller_name`이 없다 — **web/app은 Supabase에서 직접 읽고, api 응답엔 원래 포함되지 않는 필드**라 이 비대칭은 정상이다. 이번에 §4를 다시 쓰는 김에 이 drift(문서에 없던 기존 필드)도 함께 정정한다(Task 1) — "이번 증분 신규 필드"와 혼동하지 않도록 구분해서 적을 것.

### 정확한 필드 현황 (개정 전 → 후)

| 필드 | web `ListingCardData` | api `ListingCard`(응답) | app `ListingCardData` | 값 채움(소유 에픽) |
|---|---|---|---|---|
| `id`·`manufacturer`·`model`·`year`·`price`·`mileage`·`region` | 필수(기존) | 필수(기존) | 필수(기존) | — |
| `seller_name` | optional(기존, 문서 누락 상태였음) | **없음**(api 응답엔 원래 없음) | optional(기존) | — |
| `image_url` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 9 |
| `image_count` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 9 |
| `view_count` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 11 |
| `accident_status` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 10 |
| `is_single_owner` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 10 |
| `is_non_smoker` | optional·null 추가 | optional·null 추가 | optional·null 추가 | Epic 10 |
| 찜(wishlist) 여부 | **wire 필드 아님**(사용자별 오버레이, 별도 조회) | 〃 | 〃 | Epic 10.5 |

### `accident_status`의 타입 결정 — Literal 문자열, native enum 아님
아키텍처 확정치(`architecture-increment-2026-07-12.md` "확정된 값" 섹션): `accident_status` 타입 = **`text + CHECK`**(Postgres native enum 아님, 기존 `body_type`/`color`/`region` 관례와 일관). 값은 한국어 `'무사고'|'단순교환'|'사고'`(영문 코드 금지, 규칙3). 이 스토리는 DB 컬럼을 만들지 않지만, wire 타입은 이 확정치를 미리 반영해 web(`'무사고' | '단순교환' | '사고' | null`)·api(`Literal["무사고","단순교환","사고"] | None`)에 문자열 리터럴로 못박는다. **app(Dart)만 예외** — Dart는 문자열 리터럴 유니온이 번거로워(별도 enum 클래스 필요) `String?`로 단순 통과시킨다(A2 단순함 우선, 실제 검증은 Epic 10 렌더 시점에 필요하면 추가).

### 건드리지 않을 것 (범위 밖 — 명시적 non-goal)
- **DB 마이그레이션 없음.** 이번 6필드는 `listings`·`listing_images`·`wishlists` 등 어떤 테이블에도 아직 컬럼이 없다(Epic 9의 0011·Epic 10의 0012·0015, Epic 11의 0014가 각각 만든다). 이 스토리는 **wire 계약과 3소비처 타입만** 먼저 확정한다.
- **`select()` 컬럼 문자열 불변.** `web/src/app/page.tsx:58`·`web/src/app/(user)/search/page.tsx:101`·`app/lib/features/listings/listings_repository.dart:38-40`의 select 컬럼 목록(`id, manufacturer, model, year, price, mileage, region, seller_name`)은 **그대로 둔다** — DB에 없는 컬럼을 SELECT하면 즉시 에러가 나므로 손대면 안 된다.
- **`api/app/db/sql_guard.py`의 `ALLOWED_COLUMNS` 불변.** 신뢰속성 컬럼이 실제 생기는 Story 10.1이 sql_guard·AI 프롬프트 스키마·ListingCard·매퍼를 락스텝으로 갱신한다(epics 10.1 AC 원문 인용). 지금 추가하면 존재하지 않는 컬럼을 화이트리스트에 넣는 오류가 된다.
- **화면 렌더링(JSX/Widget) 변경 없음.** `ListingCard.tsx`의 컴포넌트 본문, `listing_card.dart`의 위젯 — 카드에 사진·조회수·신뢰뱃지를 실제로 그리는 건 Epic 9(레이아웃 B)·Epic 10(신뢰뱃지)의 몫. 이 스토리의 "카드"는 어디까지나 **타입/계약**이지 화면이 아니다.
- **`web/src/lib/constants.ts`·라벨 문자열 없음.** `accident_status` 한국어 라벨·뱃지 색상 등 표시 로직은 Epic 10.2("신뢰 뱃지 표시 + 면책 라벨")가 소유.

### 8.1·8.2와의 관계
8.1(디자인 토큰)·8.2(UI 프리미티브)는 **아직 이 계약을 소비하지 않는다** — 8.2 하니스의 "카드형 더미 블록"은 검증용이지 실제 `ListingCardData`가 아니다(8.2 스토리 Dev Notes에 명시된 경계). 8.3은 8.1/8.2와 **독립적으로 병행 가능한 파운데이션**이며, 실제로 이 셋이 합쳐지는 지점은 Epic 9.4(카드 레이아웃 B)부터다.

### 테스트 표준 (project-context 규칙12)
- web: E2E(Playwright) 우선 원칙이지만, 이 스토리는 신규 화면이 없어 **회귀 관찰**(기존 두 페이지가 안 깨짐)이 검증의 전부다.
- api: LLM을 fake로 교체한 결정론적 단위테스트가 표준이나, 이 스토리는 스키마 필드 추가뿐이라 **인스턴스화 확인 + 기존 관련 스위트 재실행**으로 충분(신규 로직 없음).
- app: 컨트롤러 로직이 복잡해질 때 단위테스트를 고려하는 게 원칙이나, 이 스토리는 순수 데이터 클래스 필드 추가라 **정적 분석(`dart analyze`)**으로 충분(신규 UI 없어 실폰 E2E 불필요).

### 배포·브랜치 (B3, AC-DEPLOY-1)
`develop`에서 작업·커밋 → 동작 확인. 이 스토리는 **DB 마이그레이션이 없는 순수 타입/문서 변경**이라 web(Vercel)·api(Cloud Run)·app 어느 쪽도 배포 순서 리스크가 없다(nullable 필드 추가는 항상 하위호환). `main` 병합은 사용자 승인 시에만.

### Project Structure Notes
- web import 별칭 `@/*` → `web/src/*`. TypeScript strict 켜짐. api는 Python ≥3.10(`str | None` 유니온 문법 가능, `from typing import Literal` 이미 `schemas/ai.py`에 import돼 있음). app은 Dart ^3.12.2(nullable 타입 `?` 표준).
- **변이(variance) 없음** — web은 snake_case 직접 노출(기존 `ListingCard.tsx` 관례), app은 camelCase 매핑(기존 `listing.dart` 관례) 그대로 유지. 두 언어가 서로 다른 관례를 쓰는 것은 의도된 기존 패턴이지 이번 스토리가 만드는 불일치가 아니다.

### References
- [Source: _bmad-output/planning-artifacts/epics-increment-2026-07-12.md#Story 8.3 (366~381행)] — AC 원문
- [Source: _bmad-output/planning-artifacts/architecture-increment-2026-07-12.md#CR3(361행)] — `image_url` 단일 서명 URL 계약(변형세트는 클라 파생)
- [Source: architecture-increment-2026-07-12.md#I7(373행)] — `image_count` 추가 근거
- [Source: architecture-increment-2026-07-12.md#확정된 값(382~387행)] — `accident_status`=text+CHECK, 한국어 값, 표시 규칙
- [Source: architecture-increment-2026-07-12.md#Data Architecture(174행)] — 신뢰속성 컬럼 3종·nullable=미입력 제3상태
- [Source: docs/conventions.md §4(36~43행)] — 현행 ListingCard 계약(개정 대상)
- [Source: web/src/components/listings/ListingCard.tsx:12-21] — `ListingCardData` 타입(수정 대상)
- [Source: web/src/lib/api/aiSearch.ts:23-26, 103-115] — `SearchResult`·`isValidListing`(참고, 비수정)
- [Source: api/app/schemas/ai.py:60-74] — `ListingCard`·`SearchResponse`(수정 대상)
- [Source: api/app/graph/listing_cards.py:1-34] — `SELECT_COLUMNS`·`rows_to_cards`(참고, 비수정)
- [Source: api/app/db/sql_guard.py:34-38] — `ALLOWED_COLUMNS`(참고, 비수정 — Story 10.1 몫)
- [Source: app/lib/features/listings/listing.dart:20-75] — `ListingCardData`·`fromMap`(수정 대상)
- [Source: app/lib/features/listings/listings_repository.dart:38-40] — select 컬럼(참고, 비수정)
- [Source: _bmad-output/planning-artifacts/epics-increment-2026-07-12.md#Story 10.1(550~563행)] — sql_guard/AI 프롬프트 스키마 락스텝 갱신 시점(향후)
- [Source: _bmad-output/project-context.md#규칙3] — snake_case wire·언어별 내부 표현 규칙
- [Source: _bmad-output/implementation-artifacts/8-2-ui-프리미티브-반응형-상태-접근성.md] — 8.2가 "ListingCard 계약은 8.3 몫"이라 명시적으로 경계 지은 대목(하니스 카드형 블록 = 계약 아님)
- [Source: docs/db-schema-guide.md#listings(98~129행)] — 현재 `listings` 테이블에 이미지·조회수·신뢰속성 컬럼 없음(accident_free만 존재) 확인

## Dev Agent Record

### Agent Model Used

claude-sonnet-5

### Debug Log References

- web: `next build` — TS strict 컴파일 성공(에러 0), 정적 라우트 11개 생성 확인.
- web: dev 서버(:3100) `/health` 200 확인 → Playwright로 buyer@test.com 로그인 후 `/`(홈 미리보기, 4건)·`/search`(93건) 카드 렌더 확인, 두 페이지 모두 콘솔 에러 0.
- api: `ListingCard(id=..., ...)` 신규 필드 미전달 인스턴스화 → 6필드 전부 `None` 기본값 확인.
- api: `pytest tests/test_ai_search.py tests/test_sql_rag_node.py` — 16 passed.
- app: `flutter analyze` — No issues found!(174.5s)

### Completion Notes List

- Task 1: `docs/conventions.md` §4를 단일 출처로 개정 — 기존 `seller_name` 문서 drift 정정, 신규 6필드(image_url·image_count·view_count·accident_status·is_single_owner·is_non_smoker) nullable 계약 명문화, 찜(wishlist) 비-wire 필드 원칙, AI 카드 계약 공유 재확인, §4.1 계약 변경 체크리스트 추가.
- Task 2: web `ListingCardData`(`ListingCard.tsx`)에 신규 6필드 optional·nullable 추가. JSX 렌더·`isValidListing`은 미변경(과잉 검증 금지, A2), `aiSearch.ts` 주석 1단어만 정정.
- Task 3: api `ListingCard`(Pydantic, `schemas/ai.py`)에 신규 6필드 `... | None = None` 추가. `listing_cards.py` 주석 한 줄 보강, `SELECT_COLUMNS`·`sql_guard.py`는 범위 밖이라 미변경.
- Task 4: app `ListingCardData`(`listing.dart`)에 신규 6필드 nullable + `fromMap` snake_case→camelCase 매핑 추가(기존 `sellerName` 패턴 계승). `accidentStatus`는 Dart에서 별도 enum 없이 `String?`로 단순 통과(A2).
- Task 5: 3소비처 하위호환을 직접 실행·관찰로 검증 — web(build+Playwright E2E 회귀 0), api(인스턴스화+pytest 16 passed), app(dart analyze 0 issue). DB 컬럼이 없으므로 신규 필드는 실측 내내 `null`/미전달 상태였고, 그럼에도 컴파일·기존 렌더가 전혀 깨지지 않았음을 확인.
- 이 스토리는 DB 마이그레이션·화면 렌더링·`select()` 컬럼·`sql_guard.py` 화이트리스트를 건드리지 않는 순수 계약/타입 변경이라는 범위를 그대로 지켰다.

### File List

- `docs/conventions.md`
- `web/src/components/listings/ListingCard.tsx`
- `web/src/lib/api/aiSearch.ts`
- `api/app/schemas/ai.py`
- `api/app/graph/listing_cards.py`
- `app/lib/features/listings/listing.dart`
- `_bmad-output/implementation-artifacts/8-3-listingcard-공유-계약-셸-개정.md`

### Change Log

- 2026-07-14: Story 8.3 구현 — ListingCard 공유 계약(conventions.md §4)에 이미지·조회수·신뢰속성 6필드 nullable 자리 확정, web·api·app 3소비처 타입 락스텝 개정, 3소비처 하위호환 직접 검증 완료.
- 2026-07-14: 코드리뷰(bmad-code-review) 완료 — Blind·EdgeCase·Auditor 3레이어 병렬(opus). Auditor=스펙 충실 이행 판정. 오탐 5건 dismiss. decision-needed 1건(계약-외 값 처리) → 옵션1 문서 하드닝 채택: `conventions.md §4`에 정규화 규칙(빈 문자열 image_url→placeholder·도메인 밖 accident_status→뱃지 없음·음수 count→0·bool 3상태) + §4.1 방어적 읽기 주의 추가. patch 1건(헤더 주석 "사진 미사용" 모순 정정, ListingCard.tsx·listing.dart) 적용. 문서·주석만 변경이라 런타임 무영향. Status→done.
