---
title: "Supabase 조회수(view_count) RPC 패턴 검증 리서치"
date: 2026-07-12
scope: "SECURITY DEFINER 함수로 owner-only RLS를 우회해 조회수 +1 하는 패턴이 Supabase 표준 관행인지 검증"
method: "agent-reach (exa_search + WebSearch/WebFetch) — docs.supabase.com, supabase.com/docs, GitHub Discussions 우선"
---

> **용어 한 줄 설명**
> - **RLS(Row Level Security)**: Postgres(=Supabase가 쓰는 DB 엔진) 기능으로, 테이블의 "행(row) 단위"로 누가 읽고/쓸 수 있는지 규칙을 거는 것. 우리 프로젝트는 "매물 소유자만 자기 매물을 수정 가능"이라는 RLS 정책이 이미 있음.
> - **RPC(Remote Procedure Call)**: 클라이언트가 DB에 저장된 함수를 이름으로 호출하는 방식. Supabase는 `supabase.rpc('함수이름', {...})`로 씀.
> - **SECURITY DEFINER**: Postgres 함수 옵션. "이 함수를 부른 사람"이 아니라 "이 함수를 만든 사람(주로 DB 소유자)"의 권한으로 실행됨 → 그 안에서는 RLS를 무시(우회)할 수 있음.
> - **anon / authenticated**: Supabase가 기본 제공하는 두 역할(role). `anon`=로그인 안 한 사용자, `authenticated`=로그인한 사용자. 우리 프로젝트는 service_role(전권 관리자 키)을 쓰지 않기로 했으므로 이 둘만 대상.
> - **search_path**: Postgres가 `테이블이름`처럼 스키마를 안 붙인 이름을 찾을 때 뒤지는 스키마 목록. SECURITY DEFINER 함수에서 이게 고정 안 되어 있으면, 공격자가 같은 이름의 가짜 테이블/함수를 다른 스키마에 만들어 "이름 가로채기(스키마 하이재킹)"를 할 수 있음.

---

## 1. 질문별 소견 + 공식 근거

### Q1. SECURITY DEFINER 함수로 RLS 우회해 특정 컬럼만 증가 — 공식 권장 패턴인가?

**결론: 예 (O). Supabase가 공식적으로 이 정확한 유스케이스를 답변한 사례가 있다.**

Supabase 공식 GitHub Discussions #4364 "How to increment a column without general update access?"(정확히 이 질문)에서 Supabase 메인테이너가 직접 답변:
- "Unless you use 'security definer' in your function it will respect RLS on any tables it accesses." (SECURITY DEFINER를 안 쓰면 함수도 RLS를 그대로 따른다 → 즉 카운터 증가 같은 예외를 만들려면 SECURITY DEFINER가 필요하다는 뜻)
- 권장 조합: ① 테이블에 RLS로 일반 UPDATE 차단 ② SECURITY DEFINER 함수 하나만 만들어 그 안에서 증가 로직 수행 ③ `anon`의 테이블 직접 접근 권한(GRANT)은 명시적으로 회수(REVOKE)해서, "함수를 거치지 않은 직접 UPDATE"는 애초에 불가능하게 만듦.

출처: https://github.com/orgs/supabase/discussions/4364

**즉 우리 채택안의 "골격"(owner-only RLS 유지 + SECURITY DEFINER 함수로 카운터만 증가 + anon/authenticated에 execute grant)은 Supabase 커뮤니티/메인테이너가 명시적으로 제시한 해법과 일치한다.** 이는 임의로 지어낸 우회가 아니라 "RLS가 막아놓은 좁은 구멍을 함수로 뚫는" 표준 Postgres/Supabase 패턴(functions as a controlled escape hatch)이다.

다만 확인 필요: Supabase의 정식 "How-to" 가이드 문서(작성 가이드 형식)에 조회수 예제가 박제되어 있는지는 이번 조사로 **확인하지 못했다** — 위 근거는 커뮤니티 Q&A(Discussions)이지 `supabase.com/docs`의 튜토리얼 페이지는 아니다. 다만 Discussions는 Supabase 팀이 공식 계정으로 직접 운영하는 지원 채널이라 신뢰도는 준공식(semi-official)으로 본다.

### Q2. SECURITY DEFINER 함수의 보안 주의사항

Supabase 공식 문서 "Database Functions"(https://supabase.com/docs/guides/database/functions)의 명시적 문구:

- **기본값은 SECURITY INVOKER를 쓰라는 것**: "It is best practice to use `security invoker` (which is also the default)." → SECURITY DEFINER는 "필요할 때만" 예외적으로 쓰는 것이지 기본 선택지가 아니다.
- **search_path 고정은 필수**: "If you implement `security definer`, you must configure `search_path`." 예시로 `SET search_path = ''`(빈 문자열)를 쓰고, 이 경우 함수 안의 모든 테이블 참조에 스키마를 명시(`from public.listings`)해야 한다고 명시. 이유: "This restriction limits the potential damage if you allow access to schemas which the user executing the function should not have." → 스키마 하이재킹 방지.
- **노출 스키마 금지**: RLS 문서(https://supabase.com/docs/guides/database/postgres/row-level-security)의 경고: "Security-definer functions should never be created in a schema in the 'Exposed schemas' inside your API settings." (다만 우리 패턴은 함수 자체를 RPC로 "의도적으로" 노출시키는 것이므로, 이 경고는 "숨은 헬퍼 함수"를 대상으로 한 것 — 우리처럼 명시적으로 API에 공개할 RPC라면 이 항목은 해당 없음. 대신 grant 범위를 최소화하는 게 핵심 방어선이 됨.)
- **grant execute 범위 최소화**: Securing your API 문서(https://supabase.com/docs/guides/api/securing-your-api)의 명시적 경고: "For functions, RLS does not apply. Instead, control access by granting EXECUTE privileges only to the roles that should be able to call the function, and review any SECURITY DEFINER functions carefully." → **함수는 RLS 대상이 아니므로 GRANT/REVOKE가 유일한 접근 제어 수단**이라는 뜻. 즉 "필요한 역할에만" execute를 주고, 나머지는 기본적으로 막혀 있어야 한다.
- **Postgres 표준 린트 경고(function_search_path_mutable)**: Supabase 대시보드의 보안 어드바이저(Advisor)가 SECURITY DEFINER 함수 중 `search_path`가 고정 안 된 걸 자동으로 잡아낸다. (https://supabase.com/docs/guides/database/database-advisors) — 즉 이 항목은 Supabase가 자동 린팅까지 하는, 확실한 "함정"으로 취급됨.
- **SQL injection 방지**: 함수 파라미터를 동적 SQL(`EXECUTE '... ' || 사용자입력`)로 조립하지 않는 한 일반적인 `plpgsql`의 `UPDATE ... SET x = x + 1 WHERE id = 파라미터` 형태는 파라미터 바인딩이라 SQL 인젝션 여지가 없음. 이번 조사에서 Supabase 공식 문서가 "카운터 함수에서의 SQL injection"을 별도로 경고한 사례는 찾지 못함(확인 불가) — 다만 일반 원칙은 "동적 SQL을 쓰지 않으면 위험 없음"이라 우리 유스케이스(파라미터 하나, 정적 UPDATE문)에는 해당 사항이 거의 없다.

### Q3. anon(비로그인)에게 RPC execute 권한 — 안전한가?

**부분 O — 패턴 자체는 안전하지만, "무제한 재호출로 인한 카운트 조작"은 Supabase가 자체적으로 막아주지 않는다는 게 확인됨.**

- Supabase는 RPC/DB 호출에 대한 내장 rate limit이 없다: 조사 중 확인된 커뮤니티 답변 요지 — "there is no built-in rate limiting for DB/RPC calls besides Cloudflare DDOS protection... it's possible to spam DB/RPC endpoints using the public key." (출처: Supabase 공식 Rate limits 문서 https://supabase.com/docs/guides/auth/rate-limits 및 관련 커뮤니티 논의 종합. Auth 엔드포인트는 요율 제한이 있지만 일반 DB/RPC 엔드포인트는 별도.)
- 즉 `increment_view`가 `anon`에게 열려 있으면, 같은 매물 id로 무한히 호출해 view_count를 인위적으로 부풀리는 게 기술적으로 가능하다. **"인기 정렬"에 쓰는 값이라면 이 조작이 정렬 결과를 왜곡할 수 있다는 점은 실제 리스크.**
- Supabase가 제시하는 완화책(문서 종합): ① 애플리케이션 레벨에서 자체 rate limit 함수 작성(요청 빈도를 별도 테이블/타임스탬프로 체크) ② Cloudflare 등 CDN단 rate limit ③ Redis 등 외부 원자적 카운터로 우회 ④ 세션/쿠키/IP 기준 "1회만 카운트" 로직을 함수 안에 넣기.
- **데모 규모 판단(우리 프로젝트 맥락)**: 데모/과제용, 실사용자 트래픽이 없는 환경이므로 악의적 스팸 위협은 사실상 0에 가깝다. CLAUDE.md의 A2(단순함 우선) 원칙상, 지금 단계에서 rate limit·세션당 1회 제한 같은 방어 로직을 추가하는 건 "요청받지 않은 기능"에 해당해 과설계 소지가 있다. **다만 "실사용 서비스로 발전시킬 경우 반드시 필요한 보완"이라는 점은 문서화해 둘 필요가 있다.**

### Q4. 대안 비교

| 방식 | 장점 | 단점 | Supabase 관행상 위치 |
|---|---|---|---|
| **(채택안) SECURITY DEFINER RPC 함수** | RLS 정책 구조를 안 건드림(소유자 전용 정책 그대로 유지). 원자적(atomic) 증가(`x = x+1`)가 한 SQL문으로 처리돼 동시성 문제 적음. Supabase 메인테이너가 명시적으로 권장한 해법(#4364). | search_path 고정 등 보안 설정을 사람이 직접 챙겨야 함. anon 남용 방어는 별도 구현 필요. | **커뮤니티/메인테이너가 가장 많이 제시하는 표준 해법** |
| (a) 좁은 UPDATE RLS 정책(컬럼 단위 허용) | 함수 없이 정책만으로 해결 가능해 보임 | **Postgres RLS는 컬럼 단위 세분화를 지원하지 않는다.** `USING`/`WITH CHECK`는 행 단위 조건만 걸 수 있고, "이 컬럼만 바꾸는 UPDATE는 허용, 다른 컬럼은 금지"는 RLS만으로 불가능(트리거로 컬럼 변경 감시를 추가해야 함 — 결국 함수/트리거가 필요해져 채택안보다 복잡해짐). | 비권장 — RLS의 구조적 한계로 실무에서 거의 안 씀 |
| (b) 별도 INSERT-only 이벤트 테이블(`view_events`) + count 집계 | RLS가 매우 단순해짐(INSERT만 허용하면 됨, `WITH CHECK (true)`). 조작 탐지·중복 제거·감사(audit) 로그로도 활용 가능. 나중에 "어뷰징 감지"나 "일별 조회 추이" 같은 기능 확장에 유리. | 인기 정렬 시 매번 `count(*)` 집계 필요(캐시/materialized view 필요) → 조회수 컬럼 하나 읽는 것보다 쿼리 비용 큼. 데이터量 늘어남. | 대규모/분석 지향 서비스에서 흔히 권장되는 "정석"이지만 초기 구현 비용이 채택안보다 큼 |
| (c) Edge Function | 애플리케이션 로직(rate limit, IP 체크 등)을 TypeScript로 유연하게 넣기 쉬움 | 별도 배포·콜드스타트·네트워크 홉 하나 추가. DB 함수보다 원자성 보장이 약해질 수 있음(Edge Function에서 SQL 실행 시 결국 같은 DB 함수나 직접 UPDATE를 호출해야 함 — 결국 이 문제의 본질 해법은 아니고 "앞단 게이트"만 추가하는 것). | 남용 방지가 중요한 서비스에서 (채택안)과 **병행**하는 경우는 있으나, 단독 대체재는 아님 |
| (d) DB 트리거 | 다른 이벤트(예: 매물 상세 SELECT 시 자동 카운트)에 반응해 자동 처리 가능 | **Postgres 트리거는 SELECT에는 못 건다(SELECT는 트리거 대상 이벤트가 아님)** → "조회할 때마다 증가"를 트리거만으로 구현 불가, 결국 클라이언트가 명시적으로 RPC를 호출해야 하는 채택안과 근본적으로 다르지 않음. INSERT 기반(b)의 보조 장치로는 유용(집계 자동 갱신용 트리거). | 단독 해법이 아니라 (b)의 구현 디테일로 쓰이는 경우가 많음 |

**Supabase 관행상 우세한 것**: 소규모/단순 요구사항(우리 데모처럼 "조회수 1개 정수, 인기순 정렬만 필요")에는 **(채택안=SECURITY DEFINER RPC)**가 가장 실무에서 많이 쓰이고 메인테이너도 이를 명시적으로 답변했다. **(b) 이벤트 테이블**은 "누가 언제 봤는지"까지 필요하거나 어뷰징 방지가 중요해지는 단계에서 우세해지는 정석 대안이며, 서비스가 커지면 자연스러운 다음 단계다.

### Q5. 고빈도 쓰기의 성능/경합(lock) 이슈, 데모 규모에서의 현실 판단

- Postgres 카운터 컬럼의 근본 문제: 동시에 여러 트랜잭션이 **같은 행(row)**을 UPDATE하려 하면 그 행에 대해 순차적으로 락(lock)이 걸려 대기가 발생한다. 트래픽이 매우 높은 서비스(초당 수백~수천 조회)에서는 이게 병목이 될 수 있고, 커뮤니티에서 제시하는 완화책은: ① 카운터를 여러 "샤드(bin)"로 쪼개 락 경합 확률을 낮추는 방법 ② INSERT 기반 이벤트 로그 + 배치 집계(수만 TPS까지 가능, 하지만 지연 발생) ③ 일정 주기로만 카운터를 갱신(배치화). 출처: Cybertec PostgreSQL 블로그(https://www.cybertec-postgresql.com/en/how-to-count-hits-on-a-website-in-postgresql/), Medium "Ultra fast asynchronous counters in Postgres"(https://medium.com/@timanovsky/ultra-fast-asynchronous-counters-in-postgres-44c5477303c3) 등 커뮤니티 소스(Postgres 일반론이며 Supabase 특정 문서는 아님).
- **데모 규모 판단**: 우리 프로젝트는 "데모/과제용" 중고차 직거래 서비스로, 동시 사용자 수가 극히 적다(수 명~수십 명 수준으로 추정). 이 규모에서 단일 행 UPDATE의 락 경합은 사실상 무시 가능한 수준이다. 이벤트 테이블 샤딩·배치화 같은 고급 최적화는 **A2(단순함 우선) 원칙상 지금 도입할 이유가 없다.** "인기순 정렬"이라는 요구사항 자체도 정확한 실시간 카운트가 아니어도 되므로, 단순 `view_count` 정수 컬럼 + 단일 UPDATE 방식으로 충분하다.

---

## 2. SECURITY DEFINER 보안 체크리스트 (이번 조사에서 확인된 항목만)

함수를 만들 때 반드시:

1. `SECURITY DEFINER` 옆에 **`SET search_path = ''`(또는 최소한 `public`으로 명시 고정)**를 반드시 붙인다. 안 붙이면 Supabase 보안 어드바이저가 `function_search_path_mutable` 경고를 띄운다.
   - search_path를 빈 문자열로 하면 함수 안의 모든 테이블 참조 앞에 스키마명을 붙여야 한다(`update public.listings set ...`).
2. 함수는 **딱 하나의 좁은 동작만** 하게 만든다 — 우리 경우 "이 id의 listings.view_count를 1 증가시키는 것"만. 범용 UPDATE를 넣지 않는다(예: 여러 컬럼을 파라미터로 받아 바꾸는 함수는 절대 금지).
3. `anon`, `authenticated`의 **테이블 직접 UPDATE 권한**은 여전히 owner-only RLS로 막혀 있어야 한다(채택안 그대로 유지) — 함수가 "유일한 문"이 되도록.
4. 함수에 대한 `GRANT EXECUTE`는 필요한 역할(`anon`, `authenticated`)에만 명시적으로 준다. 기본적으로 `PUBLIC`에 자동으로 열리지 않는지 확인한다(신규 함수는 기본적으로 `PUBLIC` execute가 열리는 Postgres 기본 동작이 있으므로, 필요시 `REVOKE EXECUTE ... FROM PUBLIC` 후 필요한 역할에만 재부여하는 게 더 안전).
5. 함수는 **의도적으로 노출하는 RPC**이므로 "Exposed schemas에 두지 말라"는 경고는 우리 케이스에는 해당 없음(그 경고는 내부용 헬퍼 함수 얘기). 대신 4번(grant 범위)이 우리의 실질적 방어선.
6. 배포 후 Supabase 대시보드의 **Advisors(보안 어드바이저)**를 한 번 돌려 이 함수가 경고에 걸리는지 확인한다.

---

## 3. 대안 비교표 (요약)

| 기준 | 채택안(SECURITY DEFINER RPC) | (a)컬럼단위 RLS | (b)이벤트 테이블 | (c)Edge Function | (d)트리거 |
|---|---|---|---|---|---|
| RLS 구조 변경 필요 | 없음(그대로 유지) | 불가능(컬럼 단위 RLS 자체가 없음) | 크게 변경(새 테이블+RLS) | 없음(밑단은 결국 함수/UPDATE 필요) | SELECT엔 못 검 |
| 구현 난이도(데모 기준) | 낮음 | N/A(구조적으로 불가) | 중간 | 중간~높음 | N/A(단독 불가) |
| 조작 방지 | 약함(별도 rate limit 필요) | N/A | 강함(행 단위 추적·중복 제거 가능) | rate limit 넣기 쉬움 | N/A |
| 확장성(초고빈도 트래픽) | 낮음(단일 행 락) | N/A | 높음(배치 집계) | 중간 | N/A |
| 데모 프로젝트 적합성 | **가장 적합** | 부적합 | 과설계(현 단계) | 과설계(현 단계) | 부적합(단독 불가) |

---

## 4. 출처

- Supabase 공식 GitHub Discussions #4364 "How to increment a column without general update access?" — https://github.com/orgs/supabase/discussions/4364 (메인테이너 답변, 채택안과 정확히 일치하는 해법 제시)
- Supabase Docs, Database Functions — https://supabase.com/docs/guides/database/functions (SECURITY DEFINER vs INVOKER, search_path 고정 필수 규정)
- Supabase Docs, Row Level Security — https://supabase.com/docs/guides/database/postgres/row-level-security (SECURITY DEFINER가 RLS를 우회하는 원리, "Exposed schemas"에 두지 말라는 경고)
- Supabase Docs, Securing your API — https://supabase.com/docs/guides/api/securing-your-api (함수는 RLS 미적용, GRANT EXECUTE로만 통제한다는 명시)
- Supabase Docs, Performance and Security Advisors — https://supabase.com/docs/guides/database/database-advisors (function_search_path_mutable 자동 린트 경고)
- Supabase Docs, Rate limits (Auth) — https://supabase.com/docs/guides/auth/rate-limits (DB/RPC 레벨엔 내장 rate limit 없음, Auth 엔드포인트만 별도)
- Cybertec PostgreSQL Blog, "How to count hits on a website" — https://www.cybertec-postgresql.com/en/how-to-count-hits-on-a-website-in-postgresql/ (Postgres 카운터 락 경합 일반론, Supabase 특정 문서 아님)
- Medium, "Ultra fast asynchronous counters in Postgres" — https://medium.com/@timanovsky/ultra-fast-asynchronous-counters-in-postgres-44c5477303c3 (샤딩/이벤트 배치 대안, 일반 Postgres 커뮤니티 소스)
- 확인 불가: Supabase의 정식 "how-to 튜토리얼" 문서(`supabase.com/docs`의 스텝별 가이드 형식)에 "조회수 카운터" 전용 공식 예제가 있는지는 이번 조사로 찾지 못함 — 근거는 커뮤니티 Discussions(준공식)에 한정됨. SQL injection과 카운터 함수를 직접 엮은 Supabase 공식 경고 문구도 찾지 못함(일반 원칙에서 유추).

---

## 5. 우리 채택안 평가

### 표준 관행 부합 여부: **O (표준 맞음)**

- 골격(owner-only RLS 유지 + SECURITY DEFINER 함수로 특정 컬럼 증가만 우회 + anon/authenticated에 execute grant)은 Supabase 메인테이너가 공식 Discussions에서 명시적으로 제시한 해법과 일치.
- 데모 규모(트래픽 적음, 실사용자 위협 낮음)에서는 이벤트 테이블(b) 같은 정석적 확장형 대안보다 **더 단순하고 적합**하다 — CLAUDE.md A2(단순함 우선) 원칙과도 부합.

### 반드시 지켜야 할 보안 주의사항 (3가지 핵심)

1. **`SET search_path = ''`(또는 `public`으로 명시 고정)를 함수 정의에 반드시 포함** — 안 하면 스키마 하이재킹 위험 + Supabase 보안 어드바이저가 자동으로 경고(`function_search_path_mutable`).
2. **함수 범위를 "이 id의 view_count만 +1"로 극도로 좁게 유지** — 파라미터로 임의 컬럼/SQL을 받는 범용 함수로 확장하지 않는다. 소유자 전용 UPDATE RLS는 손대지 말고 그대로 둔다.
3. **`GRANT EXECUTE`는 `anon`/`authenticated`에만 명시적으로, 그 외 역할에는 주지 않는다** — 함수가 RLS 우회 통로이므로, 이 grant 범위가 사실상의 유일한 접근 통제선이다.

### anon 부여 안전성

패턴 자체(함수 통해서만 우회)는 안전하지만, **"같은 매물을 무한 재호출해 조회수를 부풀리는 조작"은 Supabase가 기본으로 막아주지 않는다.** 데모 단계에서는 실질적 위협이 거의 없어 무시 가능하지만, 나중에 실사용자에게 공개할 경우 반드시 IP/세션/쿠키 기준 "중복 카운트 방지" 로직 추가를 검토해야 한다(현재는 요청받지 않은 범위라 구현하지 않음 — 필요 시 별도 스토리로 제안).

### 데모 권고

**현재 채택안 그대로 진행 권고.** 추가로 넣을 필요 없는 것(과설계 방지): 카운터 샤딩, rate limit, 이벤트 테이블, Edge Function 게이트 — 전부 트래픽 규모 대비 불필요. 넣어야 하는 것: 위 체크리스트 3가지(search_path 고정, 함수 범위 최소화, grant 범위 최소화)뿐이며, 이는 SQL 몇 줄 추가로 끝나는 수준이라 A2(단순함) 원칙을 벗어나지 않는다.
