# 06. 파일별 역할 레퍼런스 (전체 목록)

> 프로젝트의 **모든 파일을 빠짐없이** 한 줄 이상으로 설명하는 사전입니다. "이 파일 뭐지?" 싶을 때 여기서 찾으세요.
> 깊은 동작 설명은 각 파트 문서([01](01-db.md)~[05](05-flutter-mobile.md))에, 여기는 **전 파일 색인**입니다.

## 무엇을 포함/제외했나

- **포함**: 앱을 이루는 모든 코드 + 조금이라도 기능에 관련된 설정·데이터 파일(`.json`, 설정, `.env` 견본, Docker, 테스트, 가이드 문서 등).
- **제외**(앱 기능과 무관):
  - `.claude/` — Claude Code/BMad **개발 도구** 정의(스킬·에이전트). 앱 실행과 무관.
  - `_bmad/`, `_bmad-output/` — BMad 프레임워크와 기획 산출물(스토리·아키텍처 문서).
  - `node_modules/`, `.venv/`, `.next/`, `build/`, `.dart_tool/`, `__pycache__/`, `*.egg-info/`, `*.tsbuildinfo`, `*.stackdump` — 외부 라이브러리·빌드 캐시(자동 생성).
  - `docs/` 의 순수 문서(`idea.md` 기획, `conventions.md` 규칙, `e2e-*.md` 테스트표) — 코드가 아닌 참고 문서라 본 색인에선 생략(맨 아래에 한 줄씩만 언급).

---

## 📁 루트 (프로젝트 최상위)

| 파일 | 역할 |
|------|------|
| `CLAUDE.md` | 이 프로젝트의 AI 작업 지침(한국어 답변·커밋 규칙·배포 전략 등). 사람이 읽어도 프로젝트 운영 규칙 요약서. |
| `.env.example` | **환경변수 견본**. web/api/app 각각 어떤 키(Supabase·Gemini·DB 주소)가 필요한지 값 없이 키만 문서화. 실제 값은 각 폴더의 `.env`에. |
| `.gitignore` | git이 추적하지 않을 파일 목록(비밀값·빌드물·의존성 등). |
| `.mcp.json` | 이 프로젝트에서 쓰는 MCP 서버 등록(테스트·자동화용): `supabase`(DB), `playwright`(웹 브라우저 자동화), `mobile`(안드로이드 자동화). |

---

## 📁 supabase/ (데이터베이스) → 자세히는 [01-db.md](01-db.md)

| 파일 | 역할 |
|------|------|
| `migrations/0001_profiles.sql` | 회원(profiles) 테이블 + 가입 자동화 트리거 + 관리자 판별 함수 + RLS. |
| `migrations/0002_listings.sql` | 매물(listings) 테이블 15필드 + 임베딩 벡터 + 수정시각 트리거 + 소유권/판매완료 RLS. |
| `migrations/0003_chat.sql` | 채팅방·메시지 테이블 + 인덱스 + 당사자 한정 RLS. |
| `migrations/0003c_chat_room_integrity.sql` | 채팅방 생성 시 `seller_id`를 진짜 매물 주인으로 강제하는 보안 트리거. |
| `migrations/0004_guide_documents.sql` | AI용 가이드 문서 테이블 + 벡터(HNSW) 인덱스 + 읽기전용 권한. |
| `migrations/0005_admin_policies.sql` | 관리자 전용 RLS 7개(회원/매물/채팅 가로지르는 관리 권한). |
| `migrations/0006_readonly_role.sql` | AI 전용 "읽기 전용" 롤(`ai_readonly`) 생성·권한 설정. |
| `migrations/0007_listings_seller_name.sql` | 매물에 판매자 표시 이름 컬럼 추가(비정규화) + 트리거. |
| `migrations/0008_chat_room_names.sql` | 채팅방에 구매자·판매자 표시 이름 컬럼 추가 + 트리거. |
| `migrations/0009_profiles_name.sql` | 회원에 표시 이름 컬럼 추가 + 가입 트리거 갱신. |
| `seed.sql` | **데모 초기 데이터 단일 출처**. 관리자 계정 1개 + 샘플 매물을 멱등하게 생성. (마이그레이션 적용 후 실행) |

---

## 📁 api/ (AI 백엔드, FastAPI) → 자세히는 [02-backend-api.md](02-backend-api.md), [03-langgraph-ai.md](03-langgraph-ai.md)

### 앱 핵심 코드 (`api/app/`)
| 파일 | 역할 |
|------|------|
| `app/__init__.py` | `app`을 파이썬 패키지로 인식시키는 빈 표식 파일. |
| `app/main.py` | FastAPI 앱 시작점. 라우터 등록, CORS, 공통 에러 포맷, `/health`. |
| `app/config.py` | 환경변수·설정 로드(pydantic-settings). 비밀값은 필요 시점에 fail-loud로 검증. |
| `app/auth.py` | Supabase JWT(로그인 토큰) 검증. 로그인한 사람만 AI 검색 가능(401/503 구분). |
| `app/embeddings.py` | Gemini 768차원 임베딩 생성 + L2 정규화 + 차원/이상치 검증. |
| `app/db/__init__.py` | `db` 패키지 표식. |
| `app/db/readonly.py` | 읽기 전용 롤(`ai_readonly`)로 DB 접속해 SELECT만 실행. |
| `app/db/sql_guard.py` | LLM이 만든 SQL을 실행 전에 검사하는 다층 안전장치(SELECT 전용·OR 금지·화이트리스트 등). |
| `app/routers/__init__.py` | `routers` 패키지 표식. |
| `app/routers/ai.py` | `POST /ai/search` 엔드포인트. 인증→그래프 호출→응답 포장. |
| `app/schemas/__init__.py` | `schemas` 패키지 표식. |
| `app/schemas/ai.py` | 요청·응답 데이터 모양(Pydantic): SearchRequest/Response, ListingCard, RouterDecision 등. |

### LangGraph AI 노드 (`api/app/graph/`)
| 파일 | 역할 |
|------|------|
| `graph/__init__.py` | `graph` 패키지 표식. |
| `graph/graph.py` | 그래프 조립·실행(지휘자). `run_search()` 진입 함수, 노드/엣지 연결. |
| `graph/contextualize_node.py` | 멀티턴 맥락화. "그 중 더 싼 거"를 독립 질문으로 재작성 + 주제전환 감지. |
| `graph/router_node.py` | 질문을 A(조건검색)/B(의미검색)/C(거절)로 분류 + 코드 보정. |
| `graph/sql_rag_node.py` | 경로 A: 자연어→SQL 생성→가드 검사→읽기전용 실행→매물카드. |
| `graph/doc_rag_node.py` | 경로 B: 질문 임베딩→pgvector 코사인 유사도 검색→매물+가이드. |
| `graph/guard_node.py` | 경로 C: LLM 없이 고정 거절 문구 반환(갈림길 유도). |
| `graph/answer_node.py` | 최종 답변 정규화(0건 안내·형식 보정). 새 답변은 만들지 않음. |
| `graph/listing_cards.py` | 경로 A·B 공유 헬퍼. DB 행을 ListingCard로 변환(컬럼 단일 출처). |

### 설정·실행 파일 (`api/`)
| 파일 | 역할 |
|------|------|
| `Dockerfile` | Docker 컨테이너 이미지 설계도. Python 환경 구성 후 FastAPI 실행 → Cloud Run이 이걸로 배포. |
| `.dockerignore` | 컨테이너에 넣지 않을 파일(테스트·비밀값·문서) 목록. 이미지 작게·빌드 빠르게. |
| `requirements.txt` | 런타임용 파이썬 라이브러리 목록(개발용 제외). Docker/Cloud Run이 이걸로 설치. |
| `pyproject.toml` | 프로젝트 메타·의존성 정의. 로컬은 `pip install -e ".[ai]"`로 설치. |
| `.env.example` | api 환경변수 견본(SUPABASE_*·DATABASE_URL·GEMINI_API_KEY 등 키만). |

### 데이터 적재·평가 스크립트 (`api/scripts/`)
| 파일 | 역할 |
|------|------|
| `scripts/apply_listings_expansion.py` | 샘플 매물 58건을 DB에 일괄 INSERT(임베딩은 NULL, 다음 스크립트가 채움). |
| `scripts/backfill_embeddings.py` | 매물 설명·옵션과 가이드 문서를 Gemini 임베딩 벡터로 변환해 DB에 채우는 스크립트(멱등). |
| `scripts/run_ab_eval.py` | Gemini 두 모델 A/B 비교 실행. 질의셋을 모델별로 여러 번 돌려 raw 결과(JSON) 저장. |
| `scripts/score_ab.py` | A/B raw 결과를 채점(라우팅·결과 정확도·오염·비용)해 우승 모델 결정. |

### 테스트 (`api/tests/`)
| 파일 | 역할 |
|------|------|
| `tests/__init__.py` | 테스트 패키지 표식(비어 있음). |
| `tests/demo_queries.py` | 데모 질의셋을 코드 자료구조로 정의(질의↔기대경로). 다른 테스트가 참조하는 단일 출처. |
| `tests/test_health.py` | `/health`·OpenAPI 문서가 정상 노출되는지(앱 기동) 검증. |
| `tests/test_auth.py` | JWT 인증: 토큰 없음/형식오류=401, 정상=통과 검증. |
| `tests/test_ai_search.py` | `/ai/search` HTTP 계약 유지 검증(그래프 모킹, 네트워크 불필요). |
| `tests/test_readonly.py` | 읽기전용 롤이 SELECT는 되고 쓰기는 막히는지 라이브 DB로 검증. |
| `tests/test_sql_guard.py` | SQL 안전장치가 위험·범위밖 쿼리를 차단하는지 단위 테스트. |
| `tests/test_embeddings.py` | 임베딩 L2 정규화·차원 검증의 수치 정확성 단위 테스트. |
| `tests/test_router_node.py` | 라우터 분류·환각 보정·키 부재 fail-loud를 LLM 모킹으로 검증. |
| `tests/test_sql_rag_node.py` | 경로 A 로직·응답 파싱·카드 매핑 검증(네트워크 불필요). |
| `tests/test_doc_rag_node.py` | 경로 B 임베딩·벡터검색 SQL·0건 안내를 모킹으로 검증. |
| `tests/test_contextualize_node.py` | 멀티턴 맥락화·폴백 로직을 모킹으로 검증. |
| `tests/test_graph.py` | 전체 그래프 라우팅·분기·응답 계약을 모킹으로 검증. |
| `tests/test_demo_acceptance.py` | 데모 질의셋으로 라우팅·결과 정확도·가드를 결정론적으로 합격 판정. |
| `tests/test_ab_scoring.py` | A/B 채점 하니스의 순수 함수(골든 SQL·지표·게이트)를 단위 테스트. |
| `tests/test_live_smoke.py` | 라이브 Gemini로 A/B/C 대표 질의를 실제 호출(기본 skip, 환경변수로 활성). |

### 평가 데이터·명세 문서 (`api/docs/`)
| 파일 | 역할 |
|------|------|
| `docs/ai-demo-queries.md` | 라우터·세 경로(A/B/C) 기대 동작 명세 **권위 문서**. 프롬프트·테스트가 참조. |
| `docs/ai-ab-test-queryset.md` | 모델 A/B 비교 질의셋 개요(사람용 설명). |
| `docs/ai-ab-test-queryset.json` | A/B 테스트 입력 질의셋 44개(기대경로·골든조건·기대건수). 평가 스크립트 입력. |
| `docs/ai-e2e-hard-queryset.json` | 스트레스 테스트 질의셋(한글숫자·억단위·범위 등 비표준 표현으로 견고성 측정). |
| `docs/ab-eval-raw-gemini-3.1-flash-lite.json` | 3.1 모델 A/B 평가 raw 결과(경로·매물ID·답변·토큰·지연). |
| `docs/ab-eval-raw-gemini-2.5-flash-lite.json` | 2.5 모델 A/B 평가 raw 결과(같은 구조). |
| `docs/ab-eval-report.json` | A/B 채점 최종 리포트(우승 모델·이유·지표 요약). |

### 가이드 문서 코퍼스 (`api/corpus/`) — 경로 B 임베딩 검색의 근거 지식
| 파일 | 주제 |
|------|------|
| `corpus/01-차종별-특성.md` | 차급(경차~SUV/RV/상용)별 크기·용도·특성. |
| `corpus/02-패밀리카-적합-차종.md` | 가족용 차 조건과 차급별 추천. |
| `corpus/03-초보운전자-적합-차종.md` | 초보 운전자에게 맞는 차 조건. |
| `corpus/04-연료별-유지비-연비.md` | 가솔린·디젤·하이브리드·전기·LPG 비교. |
| `corpus/05-중고차-신뢰성-체크포인트.md` | 무사고·주행·연식·정비 등 점검 항목. |
| `corpus/06-차형-용어-매핑.md` | 사용자 용어(세단 등)↔서비스 차종 매핑. |
| `corpus/07-전기차-충전-보조금.md` | 중고 전기차 배터리·충전·보조금 고려사항. |
| `corpus/10-사고이력-침수-판별.md` | 사고이력·침수차·주행거리 조작 판별법. |
| `corpus/11-주행거리-연식-판단.md` | 연식 대비 적정 주행거리·조작 의심 신호. |
| `corpus/12-옵션-가치-판단.md` | 중고 시장에서 가치 있는/없는 옵션 구분. |
| `corpus/_excluded/08-할부-리스-현금-비교.md` | (제외됨) 구매 방식 TCO 비교 — 금융 일반지식. |
| `corpus/_excluded/09-보험-세금-기초.md` | (제외됨) 취득세·자동차세·보험 기초 — 세금 일반지식. |
| `corpus/_excluded/README.md` | **제외 사유**: 금융·세금 일반지식은 "어떤 매물을 보여줄지" 안 바꿔서 경로 B 근거에서 뺌. (08·09가 결번인 이유) |

---

## 📁 web/ (사용자·관리자 웹, Next.js) → 자세히는 [04-web-frontend.md](04-web-frontend.md)

### 설정 파일
| 파일 | 역할 |
|------|------|
| `package.json` | 의존성(Next.js 16·React 19·Supabase SSR·Tailwind)·스크립트(dev/build/lint) 정의. |
| `package-lock.json` | 의존성 버전 잠금(자동 생성). |
| `next.config.ts` | Next.js 빌드 옵션(현재 거의 비어 있음). |
| `tsconfig.json` | TypeScript 설정(strict, 경로 별칭 `@/*` → `./src/*`). |
| `next-env.d.ts` | Next.js 자동 생성 타입(수정 금지). |
| `eslint.config.mjs` | 코드 검사 규칙(Next.js 권장 + TS). |
| `postcss.config.mjs` | CSS 처리(Tailwind v4 플러그인). |
| `.env.local` | 로컬 환경변수(NEXT_PUBLIC_SUPABASE_URL/ANON_KEY, API_BASE_URL). |
| `.gitignore` | 제외 목록(node_modules·.next·.env 등). |
| `AGENTS.md` / `CLAUDE.md` | "이 Next.js는 버전이 달라 문서를 먼저 보라"는 AI 작업 주의서(CLAUDE.md는 AGENTS.md 참조). |
| `README.md` | create-next-app 기본 안내. |
| `public/*.svg` | 기본 제공 로고/아이콘 5개(file·globe·next·vercel·window). 데모 기능과 무관. |

### 페이지 (`web/src/app/`) — 폴더=URL, `( )`는 그룹
| 파일 | URL / 역할 |
|------|-----------|
| `layout.tsx` | 전체 공통 틀(HTML 뼈대·헤더). 모든 페이지를 감쌈. |
| `page.tsx` | `/` 홈. 로그인 여부로 분기, 최근 매물·내 채팅방 수 등. |
| `globals.css` | 전역 스타일(Tailwind·차콜 테마 토큰). |
| `favicon.ico` | 브라우저 탭 아이콘. |
| `health/page.tsx` | `/health` 배포 기동 확인용 단순 페이지. |
| `(auth)/login/page.tsx` | `/login` 로그인 폼(클라이언트). |
| `(auth)/signup/page.tsx` | `/signup` 회원가입 폼(역할 선택, 클라이언트). |
| `(user)/search/page.tsx` | `/search` 매물 탐색(서버: URL 필터 읽어 조회·렌더). |
| `(user)/search/SearchFilters.tsx` | 필터 입력 UI(클라이언트). 입력→URL 갱신. |
| `(user)/listings/[id]/page.tsx` | `/listings/:id` 매물 상세(서버). |
| `(user)/listings/[id]/InquiryButton.tsx` | "문의하기" 버튼(클라이언트). 채팅방 생성/이동. |
| `(user)/sell/page.tsx` | `/sell` 판매자 내 매물 목록(서버). |
| `(user)/sell/layout.tsx` | sell 영역 판매자 역할 게이트(`requireRole(seller)`). |
| `(user)/sell/SellForm.tsx` | 매물 등록·수정 15필드 폼(클라이언트, 검증 포함). |
| `(user)/sell/ListingActions.tsx` | 내 매물 행의 구매완료/수정/삭제 버튼(클라이언트). |
| `(user)/sell/[id]/edit/page.tsx` | `/sell/:id/edit` 매물 수정 화면(서버: 기존값 로드). |
| `(user)/ai/page.tsx` | `/ai` AI 검색 화면(ChatAssistant 배치). |
| `(user)/chat/page.tsx` | `/chat` 내 채팅방 목록(서버). |
| `(user)/chat/[roomId]/page.tsx` | `/chat/:roomId` 채팅방(서버: 당사자 확인·헤더). |
| `(user)/chat/[roomId]/ChatRoomMessages.tsx` | 메시지 목록·입력·3초 폴링(클라이언트). |
| `(admin)/layout.tsx` | admin 영역 관리자 역할 게이트(`requireRole(admin)`). |
| `(admin)/admin/page.tsx` | `/admin` 관리 기능 허브(회원/매물/거래/채팅 링크). |
| `(admin)/admin/members/page.tsx` | `/admin/members` 전체 회원 조회(서버). |
| `(admin)/admin/members/MemberActions.tsx` | 회원 정지/삭제 버튼(클라이언트). |
| `(admin)/admin/listings/page.tsx` | `/admin/listings` 전체 매물(판매완료 포함) 조회(서버). |
| `(admin)/admin/listings/ListingAdminActions.tsx` | 매물 삭제 버튼(클라이언트). |
| `(admin)/admin/listings/[id]/page.tsx` | `/admin/listings/:id` 관리자 매물 상세(sold 포함). |
| `(admin)/admin/listings/[id]/BackButton.tsx` | "돌아가기" 버튼(클라이언트, router.back+폴백). |
| `(admin)/admin/transactions/page.tsx` | `/admin/transactions` 거래내역(판매완료 매물 조회 전용·요약통계). |
| `(admin)/admin/chats/page.tsx` | `/admin/chats` 전체 채팅방 목록(서버). |
| `(admin)/admin/chats/ChatAdminActions.tsx` | 채팅방 삭제 버튼(클라이언트). |
| `(admin)/admin/chats/[roomId]/page.tsx` | `/admin/chats/:roomId` 관리자 대화 열람(서버). |

### 공유 컴포넌트 (`web/src/components/`)
| 파일 | 역할 |
|------|------|
| `ai/ChatAssistant.tsx` | AI 검색 대화 UI(클라이언트). 멀티턴 맥락 보관·`searchAi` 호출·매물카드 표시. |
| `auth/LogoutButton.tsx` | 로그아웃 버튼(클라이언트). |
| `layout/AppHeader.tsx` | 상단 헤더(역할 라벨·로그아웃 등). |
| `listings/ListingCard.tsx` | 매물 요약 카드(목록·검색 결과에 재사용). |
| `listings/ListingDetailFields.tsx` | 매물 15필드 상세 표시(사용자·관리자 화면 공유). |
| `ui/Button.tsx` | 공용 버튼 스타일(`buttonClasses`)·컴포넌트. |

### 라이브러리/헬퍼 (`web/src/lib/`) + 미들웨어
| 파일 | 역할 |
|------|------|
| `lib/supabase/client.ts` | 브라우저용 Supabase 클라이언트. |
| `lib/supabase/server.ts` | 서버 컴포넌트용 Supabase 클라이언트(쿠키 세션). |
| `lib/supabase/session.ts` | 미들웨어에서 토큰 갱신·쿠키 설정. |
| `lib/supabase/env.ts` | Supabase 환경변수 검증(누락 시 한국어 경고). |
| `lib/auth/guard.ts` | `requireUser`/`requireRole` 역할 기반 접근 제어. |
| `lib/listings.ts` | `buyerListingsQuery` — "구매자는 판매중만"(FR11) 단일 출처. |
| `lib/chat.ts` | `openOrCreateRoom` — 채팅방 생성/재사용 규칙. |
| `lib/messages.ts` | `fetchMessages`/`dedupeById` — 메시지 조회·중복제거. |
| `lib/constants.ts` | 공유 상수(역할·상태·단위·매물 허용값·범위). DB CHECK와 일치하는 단일 출처. |
| `lib/api/aiSearch.ts` | FastAPI `/ai/search` 호출 헬퍼(토큰·context 동봉). |
| `proxy.ts` | 미들웨어. 모든 요청에서 토큰 갱신 + 비로그인 보호경로 차단. |

---

## 📁 app/ (모바일 앱, Flutter) → 자세히는 [05-flutter-mobile.md](05-flutter-mobile.md)

### 설정 파일
| 파일 | 역할 |
|------|------|
| `pubspec.yaml` | Flutter 의존성 정의: 상태관리 `flutter_riverpod`, 백엔드 `supabase_flutter`, 통신 `http`. |
| `pubspec.lock` | 의존성 버전 잠금(자동 생성). |
| `analysis_options.yaml` | Dart 코드 분석 규칙(`flutter_lints`). |
| `.env.example` | 앱 환경변수 견본(SUPABASE_URL/ANON_KEY, API_BASE_URL). |
| `.metadata` | Flutter 마이그레이션 추적(자동 생성, 수정 금지). |
| `README.md` | Flutter 기본 시작 안내. |
| `.gitignore` | 제외 목록(build·.dart_tool·서명키 등). |

### 앱 코드 (`app/lib/`)
| 파일 | 역할 |
|------|------|
| `main.dart` | 앱 시작점. Supabase 초기화→ProviderScope→AuthGate(로그인 상태로 첫 화면 분기). |
| `core/supabase/env.dart` | 환경변수 읽기·검증(가드). |
| `core/supabase/supabase_client.dart` | Supabase 클라이언트 초기화. |
| `core/theme/app_theme.dart` | 앱 색·테마(웹과 같은 차콜 톤). |
| `core/format/number_format.dart` | 숫자 포맷(천단위 콤마, 원/km/cc 단위 텍스트). |
| `features/auth/auth_controller.dart` | 로그인·회원가입·로그아웃 상태/동작(Riverpod). |
| `features/auth/auth_errors.dart` | 인증 오류 → 한국어 메시지 변환. |
| `features/auth/user_role.dart` | 역할(enum) 정의·변환·가입 가능 여부. |
| `features/auth/login_screen.dart` | 로그인 화면. |
| `features/auth/signup_screen.dart` | 회원가입 화면(역할 선택). |
| `features/auth/home_screen.dart` | 홈(역할 배지·최근 매물·AI검색 FAB). |
| `features/auth/admin_blocked_screen.dart` | 관리자 모바일 차단 안내 화면. |
| `features/listings/listing.dart` | 매물 데이터 모델(목록/상세). |
| `features/listings/listings_repository.dart` | 매물 Supabase 조회·등록·수정 캡슐화(판매중만 등 규칙). |
| `features/listings/listings_providers.dart` | 매물 관련 Riverpod provider(검색 컨트롤러 등). |
| `features/listings/listing_filters.dart` | 검색 필터 입력값 검증·해석. |
| `features/listings/search_screen.dart` | 매물 탐색 화면(필터+결과). |
| `features/listings/listing_card.dart` | 매물 카드 위젯. |
| `features/listings/listing_detail_screen.dart` | 매물 상세 화면(15필드+문의). |
| `features/listings/sell_screen.dart` | 매물 등록 화면. |
| `features/listings/sell_controller.dart` | 등록 상태/동작(Riverpod). |
| `features/listings/listing_form.dart` | 등록·수정 폼 검증 순수 로직. |
| `features/listings/edit_listing_screen.dart` | 매물 수정 화면. |
| `features/listings/my_listings_screen.dart` | 내 매물 목록(판매중+완료). |
| `features/listings/my_listings_controller.dart` | 내 매물 상태/동작(구매완료·삭제 등). |
| `features/listings/listing_errors.dart` | 매물 DB 오류 → 한국어 변환. |
| `features/ai_search/ai_chat_screen.dart` | AI 검색 대화 화면. |
| `features/ai_search/ai_search_api.dart` | FastAPI `/ai/search` 호출(토큰·context). |
| `features/ai_search/chat_message.dart` | AI 대화 메시지 모델·멀티턴 context 빌더. |
| `features/chat/chat_list_screen.dart` | 내 채팅방 목록 화면. |
| `features/chat/chat_room_screen.dart` | 채팅방 화면(메시지+입력+3초 폴링). |
| `features/chat/chat_repository.dart` | 채팅 Supabase 호출(방 생성/재사용·메시지 조회·dedupe). |
| `features/chat/chat_providers.dart` | 채팅 관련 Riverpod provider. |
| `features/chat/chat_models.dart` | 채팅방·메시지 모델. |

### Android 플랫폼 (`app/android/`)
| 파일 | 역할 |
|------|------|
| `app/build.gradle.kts` | 앱 모듈 빌드 설정(앱 ID `com.encardemo.app`·SDK 버전·서명). |
| `build.gradle.kts` | 루트 Gradle 설정(저장소·빌드 디렉터리). |
| `settings.gradle.kts` | Flutter/Kotlin/Android 플러그인 로더·모듈 포함. |
| `gradle.properties` | 빌드 JVM 메모리·AndroidX 등(저사양 대응 포함). |
| `gradle/wrapper/gradle-wrapper.properties` | 사용할 Gradle 버전 지정. |
| `app/src/main/AndroidManifest.xml` | 앱 매니페스트. **INTERNET 권한**(릴리스 필수)·진입 액티비티·테마. |
| `app/src/debug/AndroidManifest.xml`, `app/src/profile/AndroidManifest.xml` | 개발/프로파일 빌드용 INTERNET 권한 자동 주입. |
| `app/src/main/kotlin/com/encardemo/app/MainActivity.kt` | Flutter를 띄우는 안드로이드 진입 액티비티(한 줄). |
| `app/src/main/res/**` | 런처 아이콘(mipmap)·스플래시(drawable)·테마(values). |
| `.gitignore` | 서명키·local.properties 등 제외. |

### Flutter 웹 빌드 (`app/web/`)
| 파일 | 역할 |
|------|------|
| `web/index.html`, `web/manifest.json`, `web/favicon.png`, `web/icons/**` | Flutter를 웹으로 빌드할 때 쓰는 HTML 진입점·PWA 설정·아이콘. (가벼운 UI 점검용) |

### 테스트 (`app/test/`)
| 파일 | 역할 |
|------|------|
| `test/ai_search_test.dart` | AI 응답 파싱·깨진 매물 필터 검증. |
| `test/chat_dedupe_test.dart` | 채팅 메시지 중복 제거·시간순 정렬 검증. |
| `test/chat_model_test.dart` | 채팅 메시지 모델 변환·null 처리 검증. |
| `test/listing_error_test.dart` | 매물 DB 오류코드→한국어 변환 검증. |
| `test/listing_filters_test.dart` | 필터 입력 검증 함수 테스트. |
| `test/listing_form_test.dart` | 등록 폼 검증(필수·범위·옵션) 테스트. |
| `test/listing_form_edit_test.dart` | 수정 폼 값 보존(왕복) 검증. |
| `test/listing_model_test.dart` | 매물 카드 모델 변환·타입 캐스팅 검증. |
| `test/number_format_test.dart` | 천단위·단위 텍스트 포맷 검증. |
| `test/widget_test.dart` | 역할 enum·오류 변환 등 기초 로직 검증. |

---

## 📄 부록: 코드가 아닌 문서들 (`docs/`)

기능 코드가 아니라 본 색인에선 제외했지만, 참고용으로 한 줄씩:

| 파일 | 역할 |
|------|------|
| `docs/idea.md` | 프로젝트 기획서(기능 범위·AI 검색 설계·기술 스택). |
| `docs/conventions.md` | 코딩 규칙·단위·허용값 단일 출처(코드 상수가 이걸 따름). |
| `docs/e2e-test-cases.md` | E2E 테스트 케이스 모음(웹·모바일). |
| `docs/e2e-checklist.md` | E2E 점검 체크리스트. |
| `docs/learning/**` | (바로 이 학습 문서 묶음.) |

> 그 외 `_bmad-output/` 의 PRD·아키텍처·스토리 문서는 "왜 이렇게 만들었나"의 기획 근거입니다. 코드 이해엔 위 01~06으로 충분하고, 설계 배경이 궁금할 때 참고하세요.
