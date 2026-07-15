# UX Spine Rubric Walk — bmad-encar-demo 증분 (DESIGN.md · EXPERIENCE.md)

_리뷰 일자 2026-07-12 · 리뷰어: Rubric Walker · 대상: `ux-bmad-encar-demo-2026-07-12/` 스파인 쌍 + `.decision-log.md` + `mockups/`_

## Overall Verdict

다운스트림(아키텍처·개발)이 **깨끗이 소스 추출 가능한 강한 쌍이다.** 컬러 토큰은 전부 라이트/다크 hex를 갖고 `{token}` 참조가 모두 해소되며, DESIGN은 canonical 섹션 순서를, EXPERIENCE는 8개 필수 기본값 + Responsive/Inspiration을 모두 갖춰 shape가 온전하다. broken/critical은 없다. 다만 **medium 5건**이 남는다 — AI 4갈래 중 2갈래만 Key Flow로 서술, 채팅 버블·옵션 피커·상세 갤러리의 DESIGN 시각 행 부재, "내 차 사기" 목록 서피스의 상태 행 누락, orphan 목업 1개. 계약으로 넘기기 전 이 다섯을 메우면 완결이다.

---

## 1. Flow coverage — verdict: **adequate**

Key Flow 4개 모두 명명된 주인공 + 번호 단계 + `[climax]` + `[failure]`를 갖춤: ① 지수(AI 검색→문의), ② 민호(사진·옵션·신뢰정보 등록), ③ 비로그인(열람→찜→게이트), ④ 채팅 오프라인→재연결. photo(②-2)·trust attrs(②-4,①-4)·options(②-3)·favorite(③)·chat realtime(④)·landing(①-1,③-1)·signup gate(③-climax)·nav return(② R6·① failure R5) 모두 플로우에 착지.

- **[medium]** AI 4갈래 라우팅(FR43) 중 **구조형·되묻기 2갈래만** Key Flow ①에 서술되고, **조합형(FR45)·부드러운 거절(FR47)**은 Voice/State/Component 표에만 존재하고 번호 플로우 서술이 없다 (§EXPERIENCE Key Flows ①, §D10). 다운스트림이 조합형("차장님 가이드 참고" 태그+지식 혼합)과 거절의 턴 시퀀스를 표 3곳에서 재구성해야 함. *Fix:* Key Flow ①에 3a(조합형)·3b(거절+재제안 칩) 분기 스텝을 추가하거나, 별도 짧은 플로우 "⑤ AI가 못 찾을 때(거절·조합)"로 승격.

---

## 2. Token completeness — verdict: **strong**

frontmatter 17개 컬러 토큰 전부 **light+dark hex 보유**(accent-amber는 의도적으로 동일값, danger는 로그에 hex 없어 [NOTE] 제안 기본값 명시 — 정직하게 표기됨). EXPERIENCE 프로즈의 `{token}` 참조(`{placeholder-bg}`·`{brand-petrol}`·`{price-emphasis}`·`{trust-green-ink}`·`{trust-green-bg}`) **전부 DESIGN frontmatter로 해소**. Accessibility Floor가 load-bearing 조합 4종(petrol/흰바탕·amber가격/흰바탕·trust-green ink/bg·히어로 흰텍스트)에 WCAG AA 목표 명시.

- **[low]** `accent-amber` CTA(검색·문의) **버튼 위 텍스트 색 대비**가 load-bearing 조합 목록에 없음 (§EXPERIENCE Accessibility Floor). amber 배경 버튼은 화면의 주 액션인데 텍스트/amber 대비 목표 미상. *Fix:* 대비 조합에 "CTA 텍스트 on `{accent-amber}`" 한 줄 추가.
- **[low]** 정직성 고지 배너의 `{warn-amber-bg}`/`{warn-amber-ink}` 조합(FR30 안전장치, load-bearing)도 대비 목록 미포함 (§EXPERIENCE Accessibility Floor). *Fix:* 동일 목록에 추가.

---

## 3. Component coverage — verdict: **adequate**

DESIGN Components 11행(매물 카드 B·신뢰 뱃지·N장 배지·플레이스홀더·AI 히어로 밴드·로고·버튼·칩 2종·검색 pill·바텀 내비·사진 업로더) 대부분 EXPERIENCE에 거동 행이 대응(매물 카드·찜 토글·되묻기 칩·플레이스홀더·바텀 내비·업로더). 명명 일관.

- **[medium]** **채팅 메시지 버블**(우 petrol / 좌 white, D10)의 **DESIGN 시각 행이 없다.** EXPERIENCE Component Patterns "채팅"은 거동만(실시간·멱등키·배너) 서술 (§EXPERIENCE Component Patterns; §DESIGN Components). 다운스트림이 버블 색·정렬·radius를 D10 로그에서 역추적해야 함. *Fix:* DESIGN Components에 "채팅 버블" 시각 행 추가(우 petrol 채움/좌 raised, 꼬리 없음, radius).
- **[medium]** **옵션 하이브리드 피커**(인기옵션 8칩 + "전체 옵션 더보기" 아코디언 체크리스트 + 옵션 검색창)가 EXPERIENCE Component Patterns엔 거동 행이 있으나 **DESIGN Components 시각 행 부재** — "칩 2종" 행이 칩만 커버하고 아코디언/검색창 레이아웃은 미스펙 (§EXPERIENCE Component Patterns; §DESIGN Components). *Fix:* DESIGN에 피커 시각 행(칩 그리드→아코디언→검색창) 추가하거나 forms-2 참조를 시각 스펙 근거로 명시.
- **[low]** **사진 갤러리(상세)**(대표 5:3+썸네일 스트립+"1/8"+화살표)가 EXPERIENCE Component Patterns 거동 행은 있으나 DESIGN엔 5:3 비율만 카드 문맥에서 커버, 갤러리 자체 시각 행 없음 (§EXPERIENCE Component Patterns). *Fix:* DESIGN Components에 갤러리 시각 행 또는 detail 참조 명시.

---

## 4. State coverage — verdict: **adequate**

State Patterns 표가 찜·채팅목록·AI/검색0건·카드/상세 사진없음·상세·폼·전역을 empty/loading/error 축으로 커버. focus(petrol 링)·offline/재연결(비차단 배너·초록 전환)·no-photo(placeholder)·sold-hidden(FR11 상세경로)·permission-denied(403)·error(401/403/500) 모두 착지.

- **[medium]** **"내 차 사기" 목록 서피스**의 상태 행이 없다 (§EXPERIENCE State Patterns 표). 필터 결과 0건 및 전체 0건의 empty, cold-load 스켈레톤, error가 미기재 — FR17 "0건"은 AI/검색 문맥으로만 표기되어 목록 필터 0건이 여기 해당하는지 불명확. *Fix:* State 표에 "내 차 사기 목록" 행 추가(empty=완화 칩 재사용 여부 명시, loading=스켈레톤 그리드, error).
- **[low]** **랜딩(홈)** 인기(view_count)·최신 섹션의 cold-load 스켈레톤 미명시 (§EXPERIENCE IA/State). *Fix:* 랜딩 발췌 섹션 로딩 상태 한 줄.
- **[low]** **프로필·내 매물 관리** 서피스의 상태(내 매물 0건 등) 미기재 (§EXPERIENCE State Patterns). *Fix:* 필요 시 "내 매물 없음" empty 카피 추가(현재 Voice엔 없음).

---

## 5. Visual reference coverage — verdict: **adequate**

mockups/ 8개 중 7개가 관련 섹션에 인라인 링크 + 무엇을 예시하는지 명명: landing-1(레이아웃·히어로)·card-final-1(카드, 양 문서)·detail-1(구버전 순서, spine-wins 명시)·ai-flow-1(히어로)·forms-2(업로더·피커)·app-home-2(Flutter)·type-logo-1(타이포·로고). "스파인이 목업보다 우선" 규칙 DESIGN 상단 + 양 문서 푸터에 명시.

- **[medium]** **`consistency-1.html`가 orphan** — DESIGN·EXPERIENCE 어디에도 인라인 링크가 없다 (§mockups/). 일관성 검증용 목업으로 보이나 다운스트림엔 미참조 자원. *Fix:* 관련 섹션(예: Do's/Don'ts 또는 Foundation "공유 비주얼 언어")에 링크하거나, 리뷰 산출물이면 `.working/`로 이동해 mockups/를 승격본만 남기기.

---

## 6. Bloat & overspecification — verdict: **adequate**

전반적으로 토큰이 커버하는 곳에 픽셀을 남발하지 않고 표로 처리할 것을 표로 처리. Colors 배정 규칙·Voice·State·Responsive 브레이크포인트 모두 표. 소스 재진술 대신 증류됨.

- **[low]** Elevation 겹 그림자 정확 rgba값(`0 10px 30px -14px rgba(0,0,0,.18)` 등)이 토큰화 없이 프로즈에 하드코드 (§DESIGN Elevation & Depth). 단 CRAFT BAR의 핵심 craft 스펙이라 다운스트림 재현에 필요 — 허용 범위. *Fix(선택):* `shadow-card`·`shadow-float` 토큰으로 승격하면 web/Flutter 일관 강제 용이.

---

## 7. Inheritance discipline — verdict: **strong**

sources 경로(`{planning_artifacts}/…`)가 양 문서에서 일관되게 해소 가능한 템플릿 변수. EXPERIENCE는 시각/토큰을 DESIGN 원본으로 위임하고 `{token}`만 참조 — 참조 전부 해소. 컴포넌트명("매물 카드 레이아웃 B"·"옵션 하이브리드 피커"·"사진 업로더"·trust-green 토큰) 양 문서·로그 verbatim 일치.

- **[low]** "신뢰 뱃지 / 신뢰속성 / 신뢰정보(섹션)" 세 표기가 동일 개념군에 혼용됨 (§DESIGN Components·§EXPERIENCE Component Patterns·§IA). 의미 충돌은 아니나 verbatim 일치는 아님 — 다운스트림이 세 개를 다른 것으로 오해할 소지 미미. *Fix:* 카드 뱃지=`신뢰 뱃지`, 상세 섹션=`신뢰 정보`로 용어 고정 후 1회 각주.

---

## 8. Shape fit — verdict: **strong**

DESIGN이 canonical 순서를 정확히 따름: Brand & Style → Colors → Typography → Layout & Spacing → Elevation & Depth → Shapes → Components → Do's and Don'ts. EXPERIENCE 8개 필수 기본값 전부 present + 순서 정상: Foundation → IA → Voice and Tone → Component Patterns → State Patterns → Interaction Primitives → Accessibility Floor → Key Flows. 멀티 서피스(web+Flutter+관리자)이므로 **Responsive & Platform** present, 레퍼런스 제품(엔카·K Car·KB·첫차·당근·번개)이 있으므로 **Inspiration & Anti-patterns** present. 누락·순서 이탈 없음.

_(findings 없음)_

---

## Mechanical Notes

- **컬러 토큰(17):** surface-base/raised, ink-primary/secondary/muted, border-hairline, brand-petrol/-strong, petrol-deepest, accent-amber, price-emphasis, trust-green-bg/-ink, placeholder-bg, warn-amber-bg/-ink, danger — 전부 light+dark. danger만 로그 hex 부재(제안 기본값 [NOTE] 표기).
- **`{token}` 참조(EXPERIENCE):** placeholder-bg, brand-petrol, price-emphasis, trust-green-ink, trust-green-bg — 5종 전부 해소. (`{error:{code,message}}`는 토큰 아님 = API 계약 shape.)
- **mockups/ 참조 매트릭스:** landing-1 ✓ · card-final-1 ✓(양 문서) · detail-1 ✓(spine-wins) · ai-flow-1 ✓ · forms-2 ✓(양 문서) · app-home-2 ✓ · type-logo-1 ✓ · **consistency-1 ✗(orphan)**.
- **spines-win 선언:** DESIGN 상단 1회 + 양 문서 푸터. 존재.
- **Key Flows:** 4개 전부 주인공·번호·climax·failure 완비. AI 4갈래 중 2갈래만 서술(1건 medium).
- **Severity 집계:** critical 0 · high 0 · medium 5 · low 7.
