# 접근성(Accessibility) 리뷰 — 차장님 UX 스파인 (DESIGN.md + EXPERIENCE.md)

> 기준: WCAG 2.1 AA (본문 4.5:1 / 큰 텍스트·UI 컴포넌트 3:1) + 모바일 a11y 관행.
> 대비(contrast) 계산은 WCAG 상대휘도(relative luminance) 공식으로 각 hex를 직접 산출(아래 표 근거).

## 총평

전체 구조(정보 전달 라벨, 신뢰뱃지 아이콘+텍스트 병기, 터치타깃 정책 명시, 포커스링 지정 등)는 **의도가 좋다** — 그러나 **실제 hex 값으로 계산하면 이 팀이 가장 자주 쓰게 될 조합 중 최소 3곳이 AA 기준 미달**이다. 특히 (1) `ink-muted`(meta·면책·placeholder 전용 잉크)가 라이트 모드에서 거의 모든 표면 위에서 **3.0~3.2:1**로 4.5:1에 크게 못 미치고, (2) `price-emphasis` amber가 흰 배경에서 **2.68:1**로 큰 텍스트 3:1도 못 넘으며(가격은 카드의 핵심 정보), (3) amber CTA 버튼의 글자색이 스파인에 명시돼 있지 않은데 흔한 기본값인 흰 글자를 쓰면 **2.10:1**로 대실패한다. 이 3건은 색 배정 규칙 자체를 조정해야 하는 **critical**이다. 그 외에는 시맨틱/포커스/모션 쪽 "명시 누락"이 다수(작성은 안 됐지만 구현 시 쉽게 어긋날 수 있는 지점들).

**Contrast pass/fail 하이라이트**
- ❌ FAIL — `ink-muted` on `surface-base`/`surface-raised` (라이트): **3.04:1 / 3.18:1** (요구 4.5:1)
- ❌ FAIL — `ink-muted` on `surface-raised` (다크): **4.46:1** (요구 4.5:1, 근소 미달)
- ❌ FAIL — `price-emphasis`(라이트 #E08A1B) on 흰 배경: **2.68:1** (요구 3:1, 큰 텍스트)
- ❌ FAIL — 흰 글자 on `accent-amber`(#F0A339) CTA 버튼: **2.10:1** (요구 3:1도 미달)
- ⚠️ 근소 PASS — `trust-green-ink` on `trust-green-bg` (라이트): **4.69:1** (요구 4.5:1, 마진 4%뿐)
- ✅ PASS — `brand-petrol` on 흰 배경(라이트/다크 모두), 흰 글자 on 히어로 밴드(petrol-strong/petrol-deepest, 두 모드 동일 hex), `warn-amber-ink` on `warn-amber-bg`(양 모드), 어두운 글자 on `accent-amber`(약 8:1)

**발견 건수**: critical 4 · high 4 · medium 5 · low 2 (총 15)

전체 상세는 아래 및 파일 본문 참조: `C:\Users\dnjsg\workspace\bmad-encar-demo\_bmad-output\planning-artifacts\ux-designs\ux-bmad-encar-demo-2026-07-12\review-accessibility.md`

---

## 1. Contrast — 계산 결과표

상대휘도 L = 0.2126·R + 0.7152·G + 0.0722·B (감마 보정 후), CR = (L1+0.05)/(L2+0.05).

| 조합 | 모드 | 전경 hex | 배경 hex | 계산 CR | 요구치 | 결과 |
|---|---|---|---|---|---|---|
| `ink-primary` on `surface-base` | 라이트 | #1A1E1D | #FAFAF8 | **16.11:1** | 4.5 | ✅ |
| `ink-primary` on `surface-raised` | 라이트 | #1A1E1D | #FFFFFF | **16.84:1** | 4.5 | ✅ |
| `ink-primary` on `surface-base`/`raised` | 다크 | #F5F3EE | #201F1C / #2B2A26 | **~14.7 / ~13.9:1**(역방향 동일 공식) | 4.5 | ✅ |
| `ink-muted`(meta·면책) on `surface-base` | 라이트 | #8B928F | #FAFAF8 | **3.04:1** | 4.5(본문) | ❌ **FAIL** |
| `ink-muted`(meta·면책) on `surface-raised` | 라이트 | #8B928F | #FFFFFF | **3.18:1** | 4.5 | ❌ **FAIL** |
| `ink-muted` on `surface-base` | 다크 | #948F85 | #201F1C | **5.12:1** | 4.5 | ✅ (여유 있음) |
| `ink-muted` on `surface-raised` | 다크 | #948F85 | #2B2A26 | **4.46:1** | 4.5 | ❌ **FAIL(근소)** |
| `price-emphasis`(가격, 큰 텍스트) on 흰 배경 | 라이트 | #E08A1B | #FFFFFF | **2.68:1** | 3.0(큰 텍스트) | ❌ **FAIL** |
| `price-emphasis` on `surface-base`/`raised` | 다크 | #F5B860 | #201F1C / #2B2A26 | **9.35 / 8.14:1** | 3.0 | ✅ |
| `brand-petrol`(버튼/UI 텍스트) on 흰 배경 | 라이트 | #1E6E6A | #FFFFFF | **6.01:1** | 3.0(UI)·4.5(본문) 모두 통과 | ✅ |
| `brand-petrol` on `surface-base`/`raised` | 다크 | #4FA39D | #201F1C / #2B2A26 | **5.54 / 4.83:1** | 4.5(본문 취급 시) | ✅ (raised는 근소) |
| 흰 글자 on 히어로 밴드 상단(`brand-petrol-strong`) | 공통(양모드 동일 hex) | #FFFFFF | #14514E | **9.07:1** | 4.5 | ✅ |
| 흰 글자 on 히어로 밴드 종단(`petrol-deepest`) | 공통 | #FFFFFF | #0F3D3E | **11.95:1** | 4.5 | ✅ |
| `trust-green-ink` on `trust-green-bg` | 라이트 | #1F7A44 | #E7F3EC | **4.69:1** | 4.5 | ⚠️ **근소 PASS**(마진 ~4%) |
| `trust-green-ink` on `trust-green-bg` | 다크 | #7FCE9E | #1E3A2A | **6.63:1** | 4.5 | ✅ |
| `warn-amber-ink` on `warn-amber-bg` | 라이트 | #8A5A12 | #FDEFDA | **5.22:1** | 4.5 | ✅ |
| `warn-amber-ink` on `warn-amber-bg` | 다크 | #F0C177 | #3A2E1C | **7.93:1** | 4.5 | ✅ |
| **amber CTA 버튼 — 흰 글자** on `accent-amber` | 공통 | #FFFFFF | #F0A339 | **2.10:1** | 3.0(큰/굵은 버튼 텍스트) | ❌ **FAIL(대실패)** |
| amber CTA 버튼 — `ink-primary`(라이트) 글자 | 공통 | #1A1E1D | #F0A339 | **8.02:1** | 3.0 | ✅ (권장 대안) |
| amber CTA 버튼 — `ink-primary`(**다크 테마 토큰**) 글자 ⚠ | 공통 | #F5F3EE | #F0A339 | **1.89:1** | 3.0 | ❌ **FAIL** — 다크모드라고 글자색을 밝은 잉크로 자동 스왑하면 실패함 |
| `ink-muted`(placeholder 문구 "사진 준비중") on `placeholder-bg` | 라이트 | #8B928F | #F1EFE9 | **2.77:1** | 4.5 | ❌ **FAIL** |
| `ink-secondary`(참고) on `surface-base` | 라이트 | #565F5D | #FAFAF8 | **6.30:1** | 4.5 | ✅ |
| `ink-secondary` on `surface-base`/`raised` | 다크 | #C9C6BE | #201F1C / #2B2A26 | **9.65 / 8.41:1** | 4.5 | ✅ |
| `danger`(참고, 오류/삭제) on 흰 배경 | 라이트 | #C0392B | #FFFFFF | **5.44:1** | 4.5 | ✅ |
| `danger` on `surface-base` | 다크 | #F08A7E | #201F1C | **6.78:1** | 4.5 | ✅ |

---

## 2. findings

- **[critical]** `ink-muted`가 meta(주행거리·연료·지역)·면책("판매자 제공 정보")·placeholder 문구 전용으로 지정돼 있는데, 라이트 모드에서 `surface-base`/`surface-raised` 위 대비가 **3.04~3.18:1**로 AA 본문 기준(4.5:1)에 크게 못 미침 (§DESIGN.md colors `ink-muted`, §Components 매물 카드 "판매자 제공 정보" 면책, §EXPERIENCE.md Voice "신뢰 면책"). 카드마다 반복 노출되는 요소라 영향 범위가 가장 넓다. *Fix:* 라이트 모드 `ink-muted`를 어둡게 조정(대략 L 0.28→0.16 이하가 되도록, 예: `#6B726F` 계열 재산정 후 재계산)하거나, meta/면책 텍스트 크기를 14px+ bold로 올려 "큰 텍스트" 3:1 트랙으로 옮기지 말고(폰트 크기 변경은 타이포 위계를 깨므로 권장 안 함) **색 자체를 진하게** 하는 쪽을 권장.
- **[critical]** 가격(`price-emphasis`, 26px/800, "큰 텍스트" 조건 충족)이 라이트 모드 흰/`surface-base` 배경에서 **2.68:1**로 큰 텍스트 최소 3:1도 못 넘음 (§DESIGN.md colors `price-emphasis`, §Components "가격 최상위(26/800 price-emphasis)"). 가격은 이 서비스의 핵심 정보인데 라이트 모드에서만 실패(다크는 9.3:1로 안전). *Fix:* 라이트 모드 `price-emphasis` hex를 더 진한 주황/앰버로 재산정(예: 채도 유지하며 명도만 낮춘 `#C97A15` 근방 재계산 필요) — 다크 모드 값(`#F5B860`)과 별개로 라이트 전용 수정.
- **[critical]** amber CTA 버튼(검색·문의, `accent-amber` 배경) 글자색이 DESIGN.md에 **명시돼 있지 않음**. 컬러 배경 버튼의 흔한 기본값인 흰 글자를 쓰면 **2.10:1**로 대실패(큰/굵은 버튼 텍스트 3:1 기준에도 미달) (§DESIGN.md Components "버튼: primary CTA = accent-amber(검색·문의)"). 어두운 글자(`ink-primary` 라이트, 8.02:1)는 통과하지만, 다크 테마 자동 매핑으로 `ink-primary`의 **다크 모드 값**(밝은 크림색)을 그대로 쓰면 1.89:1로 다시 실패 — 즉 "테마별 잉크 토큰을 그대로 대입"하는 흔한 구현 실수가 이 버튼에서 터진다. *Fix:* amber CTA 버튼 글자색은 라이트/다크 공용으로 **고정된 어두운 색**(예: `#1A1E1D` 또는 순수 블랙 계열)을 스파인에 명시 — 테마 토큰 자동 스왑 대상에서 제외.
- **[critical]** AI 히어로 밴드 헤드라인의 "일부 음절 amber 강조"가 배경의 "petrol·amber 빛무리(글로우)" 위에 놓임 (§DESIGN.md Components "AI 히어로 밴드... 헤드라인 일부 음절 amber 강조... 글로우/메시(petrol·amber 빛무리)"). amber 텍스트가 amber 글로우 위에 겹치는 지점에서는 사실상 전경/배경 색상이 근접해 **국소적으로 대비가 0에 가까워질 위험**이 있음 — 표에서 계산한 "흰 글자 on 히어로" 수치(9~12:1)는 균일한 petrol 그라데이션을 가정한 것이라 이 케이스엔 적용 안 됨. *Fix:* amber 강조 음절 뒤에만 얇은 다크 스크림(scrim)/텍스트섀도우를 넣거나, 글로우 배치 시 헤드라인 텍스트 영역을 회피 구역(safe zone)으로 지정.
- **[high]** `ink-muted`가 다크 모드 `surface-raised`(카드·시트·입력 표면) 위에서 **4.46:1**로 4.5:1에 근소 미달 (§DESIGN.md colors). 라이트 모드만큼 심각하진 않지만 다크 테마 카드의 meta 텍스트가 AA 경계선 아래. *Fix:* 위 라이트 모드 수정과 함께 다크 `ink-muted`도 소폭(예: `#9A958B` 정도) 조정 후 재검증.
- **[high]** 모달/바텀시트/드롭다운(로그인 게이트, 모바일 필터 바텀시트, `프로필▾` 드롭다운)에 대한 **포커스 트랩 요구사항이 전혀 명시돼 있지 않음** (§EXPERIENCE.md Accessibility Floor "웹은 전 인터랙션 키보드 도달 가능"만 있고 트랩/복귀 지점은 없음). 키보드 사용자가 열린 모달에서 Tab으로 배경 콘텐츠로 빠져나갈 위험. *Fix:* 각 오버레이형 컴포넌트(로그인 게이트, 필터 바텀시트, 프로필 드롭다운)에 "열림 시 포커스 이동+트랩, 닫힘 시 트리거 요소로 포커스 복귀" 규칙을 Accessibility Floor에 추가.
- **[high]** AI 채팅의 스크린리더 시맨틱이 전혀 정의되지 않음 — AI(차장님) 발화 vs 사용자 발화를 구분해 안내하는 role/label, 타이핑 인디케이터의 `aria-live` 공지, 스트리밍 응답 시 과도한 공지 방지 정책이 없음 (§EXPERIENCE.md State Patterns "AI/검색... 타이핑 인디케이터"는 시각 스펙만). AI가 "전역 1급 진입점"으로 규정된 핵심 기능인데 그 정도로 중요한 컴포넌트의 a11y 시맨틱이 빠짐. *Fix:* 채팅 버블에 발화자 role 텍스트(예: "차장님:" / "나:" 스크린리더 전용 라벨), 타이핑 중 상태를 `aria-live="polite"`로 1회 공지, 스트리밍 텍스트는 완결 단위로만 공지하는 규칙을 추가.
- **[high]** 아이콘 전용 소형 인터랙션 요소(찜♡ 원형 버튼, 상단 채팅🔔, 모바일 햄버거, 갤러리 좌우 화살표, 되묻기/제안 칩)에 대해 **개별 ≥44px 요구가 명시되지 않음** — Accessibility Floor는 "터치 타깃 ≥44px(모바일 주요 버튼 ≥52px: 등록·가입)"이라는 총론만 있고, 정작 사이즈 리스크가 가장 큰 원형 아이콘 버튼·칩류에 대한 명시적 최소 크기 지정이 없음 (§DESIGN.md Components "찜(♡) = 사진 밖 우상단 원형 버튼", §EXPERIENCE.md "칩 2종"). 시각적으로 "크래프트"를 위해 아이콘 버튼을 32~36px로 그리는 흔한 실수가 나올 수 있음. *Fix:* Accessibility Floor에 "모든 탭 가능 아이콘/칩은 시각 크기와 무관하게 히트영역(hit area) ≥44×44px"를 명문화.

- **[medium]** 채팅 오프라인→재연결 배너가 "색만" 전환되는 것으로 읽힘("배너 초록 전환") — 재연결 시 텍스트/아이콘이 함께 바뀌는지 불명확 (§EXPERIENCE.md Voice "오프라인 배너... 재연결 시 초록 전환", §State Patterns). 색맹 사용자에게는 상태 변화가 전달 안 될 위험. *Fix:* 재연결 성공 시 텍스트도 "다시 연결됐어요" 등으로 변경하거나 아이콘(✓) 동반 후 사라지도록 명시.
- **[medium]** 낙관적 찜(♡) 토글과 되묻기 칩 "선택됨" 상태가 시각(채워짐/petrol fill)으로만 기술되고, 스크린리더용 상태 전달(`aria-pressed`, "찜함"/"선택됨" 텍스트 대체)이 명시되지 않음 (§EXPERIENCE.md Component Patterns "찜 토글: 낙관적 토글(즉시 채워짐)", "되묻기 칩: 탭 시 petrol 채움 선택됨 상태"). *Fix:* 두 컴포넌트 모두 `aria-pressed`/`aria-selected` 상태와 대응하는 접근성 라벨 변경("찜 취소" ↔ "찜하기")을 스펙에 추가.
- **[medium]** 히어로 글로우/노이즈, 카드 호버 리프트, 타이핑 인디케이터 등 모션 요소에 대해 `prefers-reduced-motion` 대응이 전혀 언급되지 않음 (§DESIGN.md Elevation "호버: 위로 살짝 리프트 + 그림자 확장", §Components "AI 히어로 밴드... 글로우/메시... 은은히"). *Fix:* 모션에 민감한 사용자를 위해 `prefers-reduced-motion: reduce` 시 호버 리프트·글로우 애니메이션(정적 텍스처가 아니라면)을 축소/제거하는 규칙 추가.
- **[medium]** 모바일 웹 햄버거 메뉴 아이콘이 Accessibility Floor의 "아이콘 버튼 라벨" 목록(찜♡·채팅🔔·검색)에서 빠짐 (§EXPERIENCE.md Accessibility Floor, §IA "모바일 웹 = 링크는 햄버거"). *Fix:* 햄버거 아이콘도 명시 라벨 목록에 추가("메뉴 열기" 등).
- **[medium]** "N장" 배지가 다크 글래스 pill로 사진 위에 얹히는데, 구형 WebView에서 `backdrop-filter` no-op 시 "불투명 다크 pill 폴백"이라고만 돼 있고 그 폴백 상태에서 흰 텍스트 대비가 검증되지 않음 (§DESIGN.md Components "'N장' 배지"). 폴백 배경색이 사진에 따라 달라지는 반투명이 아니라 고정 불투명이라면 계산 가능하니, 실제 폴백 hex 확정 시 대비 재검증 필요. *Fix:* 폴백 다크 pill의 고정 hex를 스파인에 명시하고 흰 텍스트 대비를 계산해 4.5:1 이상 확보.

- **[low]** `trust-green-ink` on `trust-green-bg` (라이트)가 4.69:1로 통과하지만 요구치(4.5)와의 마진이 약 4%뿐 — 폰트 굵기/렌더링 차이로 실기기에서 미달 가능성. *Fix:* 구현 후 실기기 렌더 결과로 재검증 권장, 필요 시 `trust-green-ink`를 한 단계 더 진하게.
- **[low]** 주의 배너(`warn-amber-bg`/`warn-amber-ink`)가 대비는 통과하지만 아이콘 없이 텍스트만으로 구성돼 저시력 사용자의 빠른 인지에는 불리 (§EXPERIENCE.md Voice "등록폼 고지"). *Fix:* ⚠ 계열 아이콘 병기(선택 사항, 필수 아님).

---

## 3. 비-대비 항목 정성 평가 요약

- **스크린리더/시맨틱**: 찜♡·채팅🔔·검색 아이콘 라벨과 안읽음 배지 텍스트 대체는 **명시됨**(§Accessibility Floor). 신뢰뱃지·사진 준비중은 텍스트 병기라 별도 alt 불필요. AI 채팅 role 공지·햄버거 라벨·상태 토글(aria-pressed)은 **누락**(위 findings).
- **포커스/키보드(웹)**: 포커스링 색(`brand-petrol`) 지정 + "전 인터랙션 키보드 도달 가능" 원칙은 있음. 링 자체의 비텍스트 대비는 라이트 6.01:1·다크 4.83~5.54:1로 3:1 기준 통과. 다만 **모달류 포커스 트랩 규칙 부재**(위 findings).
- **비색상 신호(non-color)**: 신뢰뱃지(아이콘+텍스트)·가격(크기+굵기+위치)·선택된 칩(채움 vs 아웃라인 형태 차이)은 색만으로 신호하지 않아 **양호**. 재연결 배너·낙관적 토글 상태는 **색 단독 신호 위험**(위 findings).
- **모션/히어로 가독성**: 균일 그라데이션 구간의 흰 텍스트는 계산상 9~12:1로 매우 안전. 그러나 amber 강조 음절과 글로우가 겹치는 국소 구간, `prefers-reduced-motion` 미지정은 **위험**(critical/medium findings).

---

**파일**: `C:\Users\dnjsg\workspace\bmad-encar-demo\_bmad-output\planning-artifacts\ux-designs\ux-bmad-encar-demo-2026-07-12\review-accessibility.md`
