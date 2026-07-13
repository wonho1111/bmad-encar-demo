---
name: bmad-encar-demo
description: "차장님 — 중고차 직거래 마켓플레이스 UI·이미지 고도화 증분(FR26~61, 관리자 UI 통일 포함)의 시각 정체성 스파인. 밝은 본문 + 딥 petrol 히어로, amber는 가격·CTA 전용."
status: final
updated: 2026-07-12
sources:
  - "{planning_artifacts}/prds/prd-bmad-encar-demo-2026-07-11/prd.md"
  - "{planning_artifacts}/ux-designs/ux-bmad-encar-demo-2026-07-12/.decision-log.md"
  - "{planning_artifacts}/ux-designs/ux-bmad-encar-demo-2026-07-12/mockups/"

colors:
  # 표면 (D1)
  surface-base:        { light: "#FAFAF8", dark: "#201F1C" }   # 본문 바탕
  surface-raised:      { light: "#FFFFFF", dark: "#2B2A26" }   # 카드·시트·입력
  # 잉크 (D1)
  ink-primary:         { light: "#1A1E1D", dark: "#F5F3EE" }   # 본문·제목
  ink-secondary:       { light: "#565F5D", dark: "#C9C6BE" }   # 보조 텍스트
  ink-muted:           { light: "#676D69", dark: "#A6A196" }   # meta·면책·placeholder 글자 (AA 조정: 라이트 5.06:1·다크 5.58:1)
  border-hairline:     { light: "#E6E3DD", dark: "#3B3934" }   # 1px 구분선·카드 테두리
  # 브랜드 petrol = 신뢰·구조 (D1·D2)
  brand-petrol:        { light: "#1E6E6A", dark: "#4FA39D" }   # 내비·버튼·포커스·칩
  brand-petrol-strong: { light: "#14514E", dark: "#6BBAB4" }   # 강조 구조·히어로 밴드 상단
  petrol-deepest:      { light: "#0F3D3E", dark: "#0B2E2F" }   # 히어로 그라데이션 종단
  # 앰버 = 가격·CTA 전용 (D3)
  accent-amber:        { light: "#F0A339", dark: "#F0A339" }   # 핵심 CTA(검색·문의) — 글자·아이콘은 항상 어두운 잉크(#1A1E1D, 8.02:1). 흰색 금지
  price-emphasis:      { light: "#C0730F", dark: "#F5B860" }   # 가격 숫자 (AA 조정: 라이트 흰바탕 3.68:1)
  # 신뢰속성 = 차분한 초록 (D3, amber와 분리)
  trust-green-bg:      { light: "#E7F3EC", dark: "#1E3A2A" }   # 무사고/1인소유/비흡연 칩 바탕
  trust-green-ink:     { light: "#1B6E3D", dark: "#7FCE9E" }   # 신뢰속성 글자·✓ 글리프 (AA 조정: 라이트 5.51:1로 마진 확보)
  # 상태
  placeholder-bg:      { light: "#F1EFE9", dark: "#2A2924" }   # 사진 준비중 바탕
  warn-amber-bg:       { light: "#FDEFDA", dark: "#3A2E1C" }   # 정직성 고지·주의 배너 바탕
  warn-amber-ink:      { light: "#8A5A12", dark: "#F0C177" }   # 주의 배너 글자
  danger:              { light: "#C0392B", dark: "#F08A7E" }   # 확정: 오류·삭제·파괴적 액션 (표준 접근성 레드, #C0392B on 흰바탕 5.44:1·AA — review-accessibility.md 검증)

typography:
  font-family: "Pretendard (한글+라틴)"   # web=CDN(jsdelivr) 또는 self-host, Flutter=폰트 번들
  scale:
    display:    { size: 36, weight: 800, line-height: 1.15 }  # 히어로 헤드라인 (32~40 유동)
    section:    { size: 20, weight: 700, line-height: 1.3 }   # 섹션 제목
    card-title: { size: 16, weight: 600, line-height: 1.4 }   # 차량명
    price:      { size: 26, weight: 800, line-height: 1.2 }   # 가격 (price-emphasis · 24~26 · 상세 대표 가격은 large 변형 최대 30까지)
    body:       { size: 15, weight: 500, line-height: 1.6 }
    meta:       { size: 13, weight: 500, line-height: 1.5 }   # 주행·연료·지역 (ink-muted)
    caption:    { size: 12, weight: 500, line-height: 1.4 }   # 면책·배지 (11~12)

rounded:
  card: 16
  chip: 9
  badge: 11

spacing:
  rhythm: 4          # 4pt 리듬: 4·8·12·16·20·24
  card-padding: 18   # 카드 내부 여백 18~20
---

# 차장님 — Design Spine (시각 정체성)

> 이 스파인이 목업과 충돌하면 **스파인이 우선**한다. 목업(`mockups/`)은 시각 참고이지 구속 스펙이 아니다.

## Brand & Style

"차장님"은 믿음직한 시니어 자동차 전문가다. 오래 이 바닥을 봐온 사람의 **차분한 자신감** — 요란하지 않고, 과장하지 않고, 정직하게 짚어준다. 이 인격이 화면의 색·무게·여백으로 번역된다.

- **petrol = 신뢰·구조.** 내비·버튼·섹션 헤더·포커스링·히어로 밴드. 소심하게 쓰지 않는다 — 솔리드하게, 확실히.
- **amber = 돈.** 가격 숫자와 핵심 CTA(검색·문의)에만. 화면당 amber는 손에 꼽을 정도로.
- **밝은 본문 + 단 하나의 몰입 순간.** 목록·상세·폼은 밝은 표면. 딥 petrol 히어로 밴드가 유일한 어두운 몰입 구간이다.
- **"데모 티"의 진짜 원인은 색이 아니라 크래프트였다.** 소심한 petrol·빈약한 그림자·약한 타이포 위계가 원인. → 아래 **CRAFT BAR**를 항상 지킨다: 겹 그림자, 강한 타이포 위계(가격>제목>meta), 넉넉한 여백, 카드 radius 16px.

## Colors

토큰은 위 frontmatter가 원본(라이트/다크 hex 포함). 아래는 배정 규칙이다.

| 토큰 | 쓰임 |
|---|---|
| `surface-base` / `surface-raised` | 페이지 바탕 / 카드·시트·입력 표면 |
| `ink-primary` / `ink-secondary` / `ink-muted` | 본문·제목 / 보조 / meta·면책 |
| `border-hairline` | 1px 구분선·카드 테두리 |
| `brand-petrol` / `brand-petrol-strong` | 내비·버튼·칩·포커스 / 강조 구조·히어로 상단 |
| `petrol-deepest` | 히어로 그라데이션 종단(`brand-petrol-strong`→`petrol-deepest`) |
| `accent-amber` | 핵심 CTA(검색·문의) 배경 |
| `price-emphasis` | 가격 숫자 전용 |
| `trust-green-bg` / `trust-green-ink` | 신뢰속성 칩(무사고·1인소유·비흡연) |
| `placeholder-bg` | 사진 준비중 |
| `warn-amber-bg` / `warn-amber-ink` | 정직성 고지·주의 배너 |
| `danger` | 오류·삭제·파괴적 액션 |

**핵심 사용 규칙 (governing):**
- **브랜드 앰버(`accent-amber`·`price-emphasis`)는 가격·CTA 전용.** 신뢰속성·태그·일반 강조에 브랜드 앰버 금지 — 가격/CTA와 시각적으로 겹쳐 "돈" 신호가 희석된다.
- **`warn-amber`는 별개의 경고/고지 시맨틱(브랜드 강조 아님).** 정직성 고지·주의 배너 바탕/글자 전용이며, 위 "가격·CTA 전용" 규칙과 무관한 독립 색군이다(둘을 같은 강조로 섞지 않는다).
- **amber CTA(검색·문의) 버튼의 글자·아이콘 = 어두운 잉크(`#1A1E1D`, 8.02:1). 흰색 절대 금지.** 테마 토큰 자동 스왑 대상에서 제외(다크 테마 잉크로 바꾸면 1.89:1 실패).
- **petrol은 구조·내비·히어로에.** 소심한 petrol(연한 틴트로만 쓰기) 금지.
- **신뢰속성 = 초록.** 브랜드 앰버와 명확히 분리해 "가격 amber vs 신뢰 green" 두 신호가 안 섞이게.
- 다크모드는 라이트와 동등 지원. 히어로 밴드는 두 모드 모두 딥 petrol(밝아지지 않음).
- **대비 타깃(AA):** 위 조정 후 load-bearing 조합이 모두 AA 충족 — `ink-muted` 라이트 5.06:1·다크 5.58:1, `price-emphasis` 라이트 3.68:1(큰 텍스트 3:1), `trust-green-ink` 라이트 5.51:1, amber CTA 어두운 글자 8.02:1. meta·면책 본문은 `ink-muted`(조정치)로 4.5:1 확보.

## Typography

**Pretendard 일원화**(한글+라틴). OS 기본폰트가 "부실함"의 주원인이었음 → Pretendard로 프리미엄감 확보. **web = CDN(jsdelivr) 또는 self-host · Flutter = 폰트 번들.** 스케일은 frontmatter `typography.scale` 참조. Before/After 대비: `mockups/type-logo-1.html`.

위계가 곧 크래프트다: **가격(26/800) > 차량명(16/600) > meta(13/500 muted)** 의 대비가 확실히 벌어져야 카드가 프리미엄하게 읽힌다.

## Layout & Spacing

- **밝은 본문 + 딥 petrol 히어로 밴드.** 랜딩 최상단 AI 검색만 어둡고(다크 히어로 → 라이트 본문 전환), 나머지 전 화면은 밝은 표면. 참고: `mockups/landing-1.html`.
- **4pt 리듬**(4·8·12·16·20·24), 카드 내부 여백 18~20px, 섹션 간 넉넉히.
- **반응형 무결성 (governing · 전 UI, D5):** 가로폭이 줄면 **그리드 열 수로 흡수**한다(4→2→1). 개별 컴포넌트 **내부 가로 배치(신뢰속성 행·meta·옵션 칩)를 절대 세로로 접지 않는다** — 줄바꿈 찌그러짐 = 금기. 공간 부족은 `truncate`·"외 N"·열 축소로 처리. **가장자리 카드 부분 클리핑은 허용**(모바일에서 살짝 가려지는 정도). 레이아웃 어긋남·깨짐 = 절대 금기.

## Elevation & Depth

**겹 그림자로 깊이를 만든다**(단일 흐릿한 그림자 = 데모 티).

- 카드 기본: `0 1px 2px rgba(0,0,0,.04)` + `0 10px 30px -14px rgba(0,0,0,.18)`
- 호버: 위로 살짝 리프트(translateY) + 그림자 확장
- 떠 있는 요소(찜 버튼·바텀시트·sticky 문의 바): 더 강한 -12px 계열 겹 그림자
- 다크모드는 그림자 대신 `border-hairline`·표면 밝기차로 층을 표현

## Shapes

`rounded` 토큰: **카드 16 · 칩 9 · 배지 11.** 히어로 검색바·버튼은 카드와 조화되는 12~14 계열. 로고 배지는 라운드-스퀘어.

## Components

각 항목은 **시각 스펙**(작동은 EXPERIENCE.md). 최종 대형 카드·랜딩·상세·AI·폼·앱홈 목업은 `mockups/`.

> **목업의 내비 라벨은 확정 전 버전일 수 있음** — 최종 라벨(내 차 사기·AI로 찾기)은 EXPERIENCE Voice 표가 정답, **스파인 우선**. (예: `mockups/landing-1.html`의 구 라벨은 무시.)

- **매물 카드 — 레이아웃 B** (`mockups/card-final-1.html`): 사진(5:3, 깨끗) → **신뢰속성 전용 행**(사진 바로 아래, 초록 칩 + "판매자 제공 정보" 면책 `ink-muted` 11px) → **차량명 "[제조사] 모델·연식"** → meta(주행·연료·지역 muted) → **가격 최상위**(26/800 `price-emphasis`) → 희소옵션 칩(petrol 아웃라인 3~4개, 밀도 높을 땐 "대표 1개 + 외 N개"). **찜(♡) = 사진 밖** 우상단 원형 버튼(그림자). **"N장" 배지 = 사진 위** 다크 글래스 pill 우하단.
- **신뢰 뱃지** (초록): `trust-green-bg`/`trust-green-ink` + ✓ 글리프. 무사고·1인소유·비흡연, 부분 표시 허용. amber 절대 금지.
- **"N장" 배지**: 사진 위 다크 pill. `backdrop-filter: blur()`는 구형 WebView(Flutter)에서 no-op 가능 → **불투명 다크 pill 폴백**으로도 가독.
- **사진 준비중 플레이스홀더**: `placeholder-bg` + 중앙 카메라 아웃라인 글리프 + 조용한 문구. **의도적으로 보이게**(깨진 느낌 금지).
- **AI 히어로 밴드** (`mockups/landing-1.html`, `mockups/ai-flow-1.html`): 딥 petrol 그라데이션(`brand-petrol-strong`→`petrol-deepest`). 배경 깊이 = **H1 글로우/메시**(petrol·amber 빛무리 + 미세 노이즈)를 베이스로 은은히 + 그 위 **H2 대형 차 실루엣 라인아트**(오른쪽 가장자리로 흐릿하게 흘러나감) → "허전함" 해소 + 자동차 정체성. 헤드라인 일부 음절 amber 강조("말"·"로"). 흰 검색바 + amber "검색" 버튼 + petrol 반투명 제안칩.
- **로고 — 방향 A "차 배지"** (`mockups/type-logo-1.html`): petrol 라운드-스퀘어 배지 안에 굵은 "차"(Pretendard 800) + "차장님" 워드마크. 앱 아이콘 겸용. *실제 아트워크는 추후 제작 — 현재 lockup으로 임시 사용.*
- **버튼**: primary CTA = `accent-amber`(검색·문의) 또는 solid `brand-petrol`(구조적 확인). **amber CTA의 글자·아이콘 = 어두운 잉크(`#1A1E1D`), 흰색 절대 금지**(라이트/다크 공용 고정, 테마 스왑 제외). 모바일 주요 버튼 높이 ≥52px(등록·가입).
- **칩 2종**: (1) **상시 제안칩** = petrol 반투명(입력바 위 단축) · (2) **맥락 칩** = 되묻기/거절, 탭 시 **petrol 채움 "선택됨"** 상태. 스타일을 구분한다.
- **검색 pill**: 흰 배경 pill + 우측 amber 전송/검색 버튼. 히어로·AI 대화 하단 공용.
- **바텀 내비(Flutter)**: Material 3 `NavigationBar`, 4탭(홈(AI)·찜·채팅·내차팔기), FAB 없음. 활성 = petrol.
- **사진 업로더** (`mockups/forms-2.html`): 드롭존 + "3/10" 카운터 + "대표" 배지 + 순서변경/삭제.
- **채팅 메시지 버블**: 내 메시지 = `brand-petrol` 채움·우측 정렬 / 상대 = `surface-raised`·좌측 정렬. 하단 타임스탬프(`ink-muted`), 읽음 표시, pending(전송 중)은 반투명.
- **옵션 하이브리드 피커** (`mockups/forms-2.html`): 인기옵션 8칩 + "전체 옵션 더보기" 아코디언(카테고리 체크리스트) + 옵션 검색창. 희소옵션엔 "희소" 태그. 선택은 칩 요약 + 개수.
- **사진 갤러리(상세)**: 대표 사진 5:3 + 하단 썸네일 스트립 + 우하단 "1/N" 카운터. 웹=좌우 화살표 / 앱=스와이프.

## Do's and Don'ts

**Do**
- amber는 오직 가격·핵심 CTA에.
- amber CTA 버튼의 글자·아이콘은 어두운 잉크(`#1A1E1D`) — 흰색 절대 금지(라이트/다크 공용).
- CRAFT BAR 준수(겹 그림자·강한 타이포 위계·넉넉한 여백·radius 16).
- petrol을 확실히(솔리드 내비/버튼/포커스).
- 소비자 자연어 라벨("내 차 사기"·"AI로 찾기"·"문의하기").

**Don't**
- 신뢰속성·태그에 amber 쓰지 않기.
- 개발/스펙 용어 라벨 금지("매물 탐색"·"탐색" 등 → EXPERIENCE Voice 참조).
- 소심한 petrol(연 틴트로만) 금지.
- 가로 배치를 줄바꿈으로 세로화하지 않기(D5).

---
_상세 페이지 섹션 순서는 EXPERIENCE.md IA 참조 — **신뢰정보 → 차량정보 → 옵션 → 판매자정보**. `mockups/detail-1.html`은 구버전 순서(옵션→차량정보)이며 **스파인이 정답**._
