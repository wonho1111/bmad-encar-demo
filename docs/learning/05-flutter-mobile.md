# 05. 모바일 앱 — Flutter (Dart)

> 웹과 **"같은 백엔드(Supabase·FastAPI), 다른 화면 기술(Flutter)"** 입니다. 같은 데이터를 폰 앱에선 어떻게 보여주는지 비교하며 읽으면 가장 잘 이해됩니다.
> 대상 코드: `app/lib/` (공통 `core/`, 기능별 `features/`).

---

## 5-1. 먼저 알아둘 것

- *Flutter*: 하나의 코드로 안드로이드·iOS 앱을 만드는 구글 프레임워크. 언어는 **Dart**.
- *위젯(widget)*: Flutter의 모든 화면 요소(버튼·글자·목록 등). 화면은 위젯을 레고처럼 쌓아 만듦.
- *Riverpod*: 이 앱의 **상태 관리** 라이브러리. "데이터를 어디에 두고 화면에 어떻게 전달할지"를 책임짐.
- *Supabase Dart SDK*: 웹과 똑같은 Supabase를 Dart 코드에서 호출하는 도구.

핵심: 관리자(admin)는 모바일에서 **차단**됩니다(관리 기능은 웹 전용). 모바일은 구매자·판매자용.

---

## 5-2. 폴더 구조 (웹과 비슷한 철학)

```
app/lib/
├─ main.dart           앱 시작점
├─ core/               공통 인프라
│   ├─ supabase/       Supabase 초기화·환경변수
│   ├─ theme/          색·테마 (웹과 같은 차콜 톤)
│   └─ format/         숫자 포맷(천단위 콤마, 원/km/cc)
└─ features/           기능별 모듈
    ├─ auth/           로그인·가입·홈·역할
    ├─ listings/       매물 탐색·상세·등록·내매물
    ├─ ai_search/      AI 검색
    └─ chat/           문의 채팅
```

각 feature 안은 **역할별로 파일이 나뉩니다** (이게 핵심 패턴):

| 파일 종류 | 역할 | 예시 |
|-----------|------|------|
| `*_screen.dart` | 화면(UI 위젯) | `search_screen.dart` |
| `*_controller.dart` / `*_providers.dart` | 상태 + 동작(액션) | `sell_controller.dart` |
| `*_repository.dart` | Supabase 호출 캡슐화 | `listings_repository.dart` |
| `*.dart` (모델) | 데이터 모양 | `listing.dart`, `chat_models.dart` |

> 이 구조를 **Riverpod + Repository 패턴**이라고 합니다. "화면(보여주기) / 상태(관리) / 데이터접근(DB)"을 분리해 각자 역할만 하게 합니다. 웹의 "컴포넌트 / lib 헬퍼" 분리와 같은 철학입니다.

---

## 5-3. 앱이 켜지는 순서 (main.dart)

```
main()
 1) Flutter 엔진 준비 (WidgetsFlutterBinding)
 2) Supabase 키 있나 확인 → 없으면 ConfigErrorScreen (원인 표시)
 3) Supabase.initialize() (DB·인증 연결)
 4) ProviderScope로 앱 감싸기 (Riverpod 켜기)
 5) AuthGate: 로그인 세션을 감시해 화면 분기
     - 미로그인 → LoginScreen
     - admin   → AdminBlockedScreen (모바일 차단)
     - buyer/seller → HomeScreen
```

- *ProviderScope*: Riverpod이 동작하려면 앱 최상단을 이걸로 감싸야 함.
- *AuthGate*: "로그인 상태에 따라 어떤 첫 화면을 보일지" 결정하는 문지기 위젯.
- 키가 없어도 앱은 켜지고 에러 화면으로 안내(fail-loud, 웹·API와 같은 철학).

---

## 5-4. 상태 관리 — Riverpod 한 예로 이해하기

매물 탐색을 예로 봅시다.

```dart
// 1) Repository를 공급하는 provider
final listingsRepositoryProvider = Provider((ref) => ListingsRepository());

// 2) 검색 상태 + 동작을 가진 Controller
class SearchController extends Notifier<SearchState> {
  SearchState build() {
    Future.microtask(search);                  // 화면 뜨면 자동 1회 검색
    return SearchState(results: AsyncValue.loading());
  }
  Future<void> search() async {
    state = state.copyWith(results: AsyncValue.loading());   // 로딩 표시
    try {
      final list = await ref.read(listingsRepositoryProvider).fetchListings(filters);
      state = state.copyWith(results: AsyncValue.data(list));  // 성공
    } catch (e, st) {
      state = state.copyWith(results: AsyncValue.error(e, st)); // 실패
    }
  }
}
```

화면에선:
```dart
final results = ref.watch(searchControllerProvider).results;
// results.when(loading: ..., error: ..., data: ...) 로 3상태를 자동 분기
```

핵심 용어:
- *Notifier<T>*: 상태(T)를 들고 있으면서 그 상태를 바꾸는 메서드(search 등)를 가진 클래스.
- *AsyncValue<T>*: 비동기 작업의 세 가지 상태(**loading / error / data**)를 한 번에 감싸는 타입. 로딩 스피너·에러 메시지·결과를 깔끔히 분기하게 해줌.
- *ref.watch()*: provider 값 변화를 **감시**(바뀌면 화면 다시 그림).
- *ref.read()*: 값을 **한 번만** 읽음(다시 그리지 않음).

> 웹의 React 상태관리와 목적이 같습니다: "데이터가 바뀌면 화면이 따라 바뀌게."

---

## 5-5. Repository — DB 호출을 한곳에

웹이 `lib/listings.ts` 헬퍼에 규칙을 모았듯, 모바일은 **Repository 클래스**에 Supabase 호출을 모읍니다.

```dart
// listings_repository.dart — 구매자는 항상 판매중만 (FR11)
_buyerQuery(cols) => _client.from('listings').select(cols).eq('status', 'on_sale');

Future<List<ListingCardData>> fetchListings(filters) async {
  var q = _buyerQuery('id, manufacturer, model, ... , seller_name');
  // 필터 적용: keyword(ilike), bodyType(eq), 가격범위(gte/lte) ...
  // 정렬: created_at desc, id desc
}
```

- `chat_repository.dart`의 `openOrCreateRoom`도 웹과 똑같은 로직: 기존 방 재사용 → 없으면 INSERT(트리거가 seller_id 강제) → 경합 처리.
- Repository는 에러를 **그대로 던지고**, Controller가 한국어 메시지로 바꿉니다(역할 분리).

---

## 5-6. 화면별 역할

| 화면 | 파일 | 보여주는 것 |
|------|------|-------------|
| 로그인 | `login_screen.dart` | 이메일·비밀번호 |
| 가입 | `signup_screen.dart` | 이메일·비밀번호·역할(buyer/seller) |
| 홈 | `home_screen.dart` | 역할 배지·이메일, 최근 매물 4건, AI검색 버튼(FAB) |
| 탐색 | `search_screen.dart` | 필터 10종 + 매물 카드 목록(판매중만) |
| 상세 | `listing_detail_screen.dart` | 15필드 + 옵션·설명 + 문의하기 |
| 등록 | `sell_screen.dart` + `sell_controller.dart` | 15필드 폼 → INSERT(판매자만) |
| 수정 | `edit_listing_screen.dart` | 기존값 로드 → UPDATE |
| 내매물 | `my_listings_screen.dart` | 본인 매물(판매중+완료) + 구매완료/수정/삭제 |
| AI검색 | `ai_chat_screen.dart` | 자연어 질의 → 답변 + 매물카드 |
| 채팅목록 | `chat_list_screen.dart` | 내 채팅방 목록 |
| 채팅방 | `chat_room_screen.dart` | 메시지 + 입력칸 (3초 폴링) |

- *FAB(Floating Action Button)*: 화면 우하단에 떠 있는 동그란 버튼(여기선 AI 검색 진입).
- *Scaffold*: Material 디자인의 기본 화면 틀(상단바·본문·FAB 자리).

---

## 5-7. AI 검색 (웹과 동일한 API 호출)

```dart
// ai_search_api.dart — 웹의 aiSearch.ts와 같은 엔드포인트
searchAi({query, context, accessToken}) {
  POST '${apiBaseUrl}/ai/search'
  headers: { Authorization: 'Bearer $accessToken' }   // Supabase 토큰
  body: { query, if(context) context }                 // 멀티턴 동봉
  → 200: SearchResult{answer, listings[]}
}
```

- 멀티턴 맥락(`buildContext`)은 최근 12턴만, 각 2000자로 잘라 보냅니다(서버 무상태).
- 화면(`ai_chat_screen.dart`)은 내 질문을 **낙관적으로** 먼저 버블에 추가하고, 응답이 오면 답변+카드를 붙입니다.

> 즉 AI 검색은 웹이든 앱이든 **같은 FastAPI를 같은 계약으로** 부릅니다. 백엔드를 공유하는 이점.

---

## 5-8. 채팅 폴링 (모바일판)

웹의 `setInterval`에 대응하는 게 Dart의 `Timer.periodic`입니다.

```dart
_timer = Timer.periodic(Duration(seconds: 3), (_) => _poll());  // 3초마다
...
@override
void dispose() { _timer?.cancel(); }   // 화면 나가면 타이머 정리(메모리 누수 방지)
```

- 증분 조회(`gte` 커서) + id 중복 제거(dedupe) + 시간순 정렬 → **웹과 완전히 같은 전략**.
- 모바일은 배터리를 고려해 3초가 적절한 타협점(준실시간 NFR).

---

## 5-9. 웹 ↔ 모바일 비교표

| 관점 | 공통 | 다른 점 |
|------|------|---------|
| 백엔드 | 동일 Supabase + 동일 FastAPI `/ai/search` | — |
| 인증 | 이메일+비밀번호, 메타데이터 역할 | — |
| DB 규칙 | 동일 RLS·CHECK·트리거 | — |
| 상태관리 | (둘 다) 분리된 상태 계층 | 웹=React, 앱=Riverpod |
| 화면 기술 | — | 웹=컴포넌트, 앱=위젯 |
| 라우팅 | — | 웹=파일기반, 앱=Navigator 스택(push/pop) |
| 채팅 | 3초 폴링 + dedupe | 웹=setInterval, 앱=Timer |
| 관리자 | — | 웹=가능, 앱=차단(AdminBlockedScreen) |
| 사진 | 둘 다 미사용 | — |

> 같은 백엔드를 공유하므로 **데이터·규칙·보안은 동일**하고, 화면을 그리는 기술만 다릅니다. 이게 "백엔드 분리"의 가장 큰 이점입니다.

---

## 5-10. 흐름 예시: 앱 켜기 → 로그인 → 탐색 → AI 검색

```
main() → Supabase 초기화 → ProviderScope → AuthGate
  ↓ (미로그인)
LoginScreen → signIn() → 세션 발생 → AuthGate가 감지 → HomeScreen
  ↓ "매물 탐색" 탭
SearchScreen → SearchController.search() → repository.fetchListings()
   → on_sale 매물 카드 목록 → 카드 탭 → ListingDetailScreen
  ↓ 우하단 FAB(AI검색)
AiChatScreen → searchAi(query, context, token) → POST /ai/search
   → answer + 매물카드 표시
```

---

## 5-11. 핵심 개념 정리 (이 파트에서 꼭 배워야 할 것)

1. **위젯(Widget)** — 모든 UI의 단위. StatelessWidget(상태 없음) vs StatefulWidget(상태 있음).
2. **ConsumerWidget** — Riverpod provider를 watch하는 위젯.
3. **Riverpod 상태관리** — Provider / Notifier / `ref.watch`·`ref.read`.
4. **AsyncValue<T>** — 비동기의 loading/error/data 3상태를 깔끔히 분기.
5. **Repository 패턴** — DB 호출을 한 클래스에 캡슐화(웹의 lib 헬퍼와 같은 역할).
6. **async/await + Future** — Dart의 비동기 처리.
7. **Navigator(push/pop)** — 화면 스택 기반 이동.
8. **Supabase Dart SDK** — `auth.signIn`, `from().select().eq()` 등(웹과 같은 개념).
9. **Timer.periodic + dispose** — 폴링과 자원 정리(메모리 누수 방지).
10. **백엔드 공유 관점** — "같은 데이터·규칙, 다른 화면 기술"의 이점 체감.

---

이전: [00-overview.md](00-overview.md) | [01-db.md](01-db.md) | [02-backend-api.md](02-backend-api.md) | [03-langgraph-ai.md](03-langgraph-ai.md) | [04-web-frontend.md](04-web-frontend.md)
