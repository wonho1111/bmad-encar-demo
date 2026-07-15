# DESIGN.md ↔ EXPERIENCE.md 일관성 리뷰

리뷰 대상: `DESIGN.md`, `EXPERIENCE.md`, `.decision-log.md` (2026-07-12, status: final)
방법: 7개 체크리스트(웹/앱 패리티, 토큰 상호참조, 라벨 일관성, 신뢰속성 색, 상세 섹션 순서, FR-스파인 매핑, 목업-스파인 충돌) 전수 대조 + `mockups/*.html` 실제 내용 검증.

---

## Findings

- **[critical]** `mockups/landing-1.html`의 상단 내비(541~559행, 879~892행)가 **폐기된 개발용어 라벨 "매물 탐색"·"AI 검색"을 그대로 사용** — D4/D13에서 확정한 "내 차 사기"/"AI로 찾기"와 정면 충돌하고, DESIGN.md의 Don't 규칙("개발/스펙 용어 라벨 금지('매물 탐색'·'탐색' 등)", DESIGN.md:145)도 정면 위반한다. `detail-1.html`(섹션 순서)은 두 스파인 모두 명시적 "구버전·스파인이 정답" 각주가 있는데, `landing-1.html`은 DESIGN.md:127(AI 히어로 밴드 컴포넌트)·EXPERIENCE.md IA에서 그대로 링크되면서도 이런 각주가 전혀 없다. 최상위 일반 면책("스파인이 목업과 충돌하면 스파인이 우선", DESIGN.md:59)만으로는 이 구체적 라벨 충돌을 독자가 알아채기 어렵다.
  *Fix:* `landing-1.html`의 두 nav 블록 라벨을 "내 차 사기"·"AI로 찾기"로 갱신하거나, 최소한 detail-1.html과 동일한 각주("이 목업 nav 라벨은 구버전, 최종 라벨은 D4/D13 참조")를 DESIGN.md/EXPERIENCE.md에 추가한다.

- **[high]** amber 색상 governing 규칙과 실제 토큰 정의가 서로 모순된다. DESIGN.md는 "amber는 가격·CTA에만"(Colors 규칙, DESIGN.md:89)과 "amber는 오직 가격·핵심 CTA에"(Do's, DESIGN.md:138)를 governing으로 못 박으면서도, 같은 문서 frontmatter에 `warn-amber-bg`/`warn-amber-ink`(DESIGN.md:32-33, "정직성 고지·주의 배너")를 정의하고 Colors 표(DESIGN.md:85)에도 명시한다. 정직성 고지 배너는 가격도 CTA도 아니므로, 이 토큰의 존재·용도가 governing 규칙과 직접 충돌한다. EXPERIENCE.md의 등록폼 고지("실제와 다르게 표기하면…", EXPERIENCE.md:56)·신뢰섹션 고지(EXPERIENCE.md:55) 문구가 바로 이 배너에 해당하는데, 이 규칙 충돌 때문에 "이 배너에 amber를 써도 되는가"가 두 문서 모두에서 애매하다.
  *Fix:* governing 규칙 문구를 "amber는 가격·CTA·경고 배너에만(신뢰속성·태그·일반 강조는 금지)"로 넓히거나, `warn-amber-*`를 amber 계열이 아닌 별도 색상 패밀리로 바꿔 규칙과 토큰을 일치시킨다.

- **[medium]** 상세 페이지 가격 크기 불일치. `.decision-log.md` D9(122행 인근, line117)는 상세 페이지 가격을 **"30/800 amber"**로 확정했는데, DESIGN.md의 최종 typography 스케일(frontmatter `typography.scale.price`, DESIGN.md:42)은 `size: 26`(주석 "24~26")만 정의하고, 카드용 26px와 상세용 30px를 구분하지 않는다. EXPERIENCE.md도 상세 가격 크기를 별도로 언급하지 않는다. 두 스파인 모두 D9의 30px 지시를 흡수하지 못한 채 Finalize된 것으로 보인다.
  *Fix:* DESIGN.md typography scale에 `price-detail: 30/800`(또는 유사 토큰)을 추가하거나, 카드/상세 공용 26px로 의도적으로 통일했다면 그 사실과 D9와의 차이를 스파인에 명시한다.

- **[medium]** 앱 홈에서 "내 차 사기"(전체 매물 탐색) 접근 경로가 스파인 텍스트에 없다. EXPERIENCE.md D12/D14(EXPERIENCE.md:43, 145)는 앱 홈을 "AI검색 최상단(웹 히어로의 앱 번역판)"으로만 서술한다. 실제로는 `mockups/app-home-2.html`(612·678행)에 "지금 인기"+"전체보기" 섹션이 존재해 웹 랜딩의 차종칩·인기·최신 구성이 앱에도 이식된 것으로 보이지만, 이 사실이 EXPERIENCE.md 어디에도 문장으로 확정되어 있지 않다. 웹 내비에는 "내 차 사기"가 독립 메뉴(EXPERIENCE.md:41)인데 앱 4탭(홈·찜·채팅·내차팔기, EXPERIENCE.md:43)엔 대응 탭이 없어, "내 차 사기가 앱에서 사라진 것인지 홈에 흡수된 것인지"가 목업을 보지 않으면 스파인 텍스트만으로는 판단 불가.
  *Fix:* EXPERIENCE.md D12/D14 서술에 "홈 탭은 AI 검색 히어로 + 차종칩 + 인기/최신 발췌(웹 랜딩 전체 구성 이식) — '내 차 사기' 목록은 홈의 '전체보기'로 진입, 별도 탭 없음" 한 줄을 명시적으로 추가.

- **[low]** `warn-amber-bg`/`warn-amber-ink` 토큰(DESIGN.md:32-33)이 EXPERIENCE.md 어디에서도 `{token}` 형태로 참조되지 않는다. 정작 이 토큰이 스타일링해야 할 문구(등록폼 고지·신뢰섹션 고지, EXPERIENCE.md:55-56, Key Flow ② 4단계 EXPERIENCE.md:122)는 EXPERIENCE.md에 존재하므로, 구현자가 "이 배너에 어떤 토큰을 쓸지" 스파인만으로 알 수 없다.
  *Fix:* EXPERIENCE.md 해당 문구 옆이나 State Patterns 표에 `{warn-amber-bg}`/`{warn-amber-ink}` 참조를 추가.

---

## 체크리스트별 결과 요약 (문제 없음으로 확인된 항목)

- **토큰 상호참조:** EXPERIENCE.md의 모든 `{token}` (`placeholder-bg`, `brand-petrol`, `surface-raised`, `price-emphasis`, `trust-green-ink`, `trust-green-bg`)는 DESIGN.md frontmatter에 정확히 존재. 고아 참조(orphan) 없음.
- **신뢰속성 색:** 두 문서 전체에서 신뢰 뱃지(무사고/1인소유/비흡연)는 예외 없이 초록(`trust-green-*`)이며, "amber 절대 금지" 문구가 DESIGN.md·`card-final-1.html` 목업 양쪽에 명시. 과거 폐기안(D1 폐기본, amber 계열 trust-badge)의 잔재 없음.
- **상세 섹션 순서:** DESIGN.md·EXPERIENCE.md 둘 다 "신뢰→차량→옵션→판매자"(D9)로 일치하고, `detail-1.html` 구버전 순서에 대해 두 문서 모두 동일한 각주로 명확히 무효화.
- **라벨(내비 문구):** DESIGN.md·EXPERIENCE.md 본문 텍스트 자체에는 "매물 탐색"·"중고차" 같은 잔재 없음(둘 다 "내 차 사기"·"AI로 찾기"로 통일). 유일한 잔재는 위 critical 항목의 목업 파일.
- **FR-스파인 매핑 스팟체크:** 사진(5:3/10장/플레이스홀더), N장 배지, 신뢰/옵션 분리, 채팅 실시간+멱등키+재연결, 찜 낙관적 토글, 역할 통합 가입, sold 미노출(FR11) 등은 결정로그와 두 스파인 간 정합성 확인됨(가격 크기 항목 제외).

---

## 종합 판단

전반적으로 두 스파인은 **강하게 정합적**이며(토큰·색상 규칙·라벨·섹션 순서 대부분 일치), 결정로그(D1~D14)를 충실히 증류했다. 다만 **핵심 목업(landing-1.html)에 폐기된 라벨이 무방비로 남아있는 점**과 **amber governing 규칙 vs warn-amber 토큰의 내부 모순**은 실제 구현 단계에서 혼란을 일으킬 수 있는 실질적 결함이다.
