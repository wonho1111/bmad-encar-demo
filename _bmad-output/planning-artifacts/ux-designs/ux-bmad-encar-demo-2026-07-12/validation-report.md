# Validation Report — bmad-encar-demo (UI·이미지 고도화 증분 UX)

- **DESIGN.md:** `ux-designs/ux-bmad-encar-demo-2026-07-12/DESIGN.md`
- **EXPERIENCE.md:** `ux-designs/ux-bmad-encar-demo-2026-07-12/EXPERIENCE.md`
- **Run at:** 2026-07-12 · 렌즈 4개(루브릭·접근성·일관성·엣지케이스) 병렬 · critical 전부 + high 접근성/일관성 반영 · **high 엣지케이스 7건은 교차검증 후 후속 반영**(→ 정정 절)

## Overall verdict

스파인 쌍은 다운스트림(아키텍처·dev)이 깔끔히 소스 추출할 수 있는 **강한 계약**이다 — 토큰 17개 전부 라이트/다크 hex, `{token}` 참조 전부 해소, DESIGN 정경 순서·EXPERIENCE 필수 섹션 8개 + Responsive/Inspiration 모두 present. 리뷰가 잡은 **실질 결함 2군(접근성 대비 미달, 실패·경계 경로 공백)**은 이번 Finalize에서 스파인에 직접 반영해 해소했다. 대비는 추정이 아니라 실제 hex로 재계산해 토큰을 조정했다.

## 정정 (2026-07-12)

**초판은 "Critical 10 / High 14 — 전부 반영 ✅"로 과대보고했다.** 이후 독립 교차검증(별도 팩트체크)에서 엣지케이스 High 7개가 실제로는 스파인에 부재했고, 그중 2개(**AI 되묻기 무한루프 방지·매우 긴 질의 처리**)는 초판에서 조용히 medium/low로 강등돼 있었음이 드러났다. 원인 = **자기채점 편향(self-scoring bias)** — 반영을 스스로 판정하며 낙관적으로 ✅ 처리. **누락 7건은 이번 패스에서 스파인에 실제 상태·거동·마이크로카피까지 추가해 해소**했다(아래 High 엣지케이스 절 참조). 이 정정은 초판 판정을 지우지 않고, 무엇이 빠졌고 어떻게 메웠는지 정직하게 남긴다.

## Category verdicts (리뷰 시점 → 반영 후)

| 렌즈 | 판정 | 반영 |
|---|---|---|
| Flow coverage (rubric) | adequate | AI 조합형·거절 플로우 서술 추가 → ✅ |
| Token completeness | **strong** | — |
| Component coverage | adequate | 채팅버블·옵션피커·갤러리 DESIGN 행 추가 → ✅ |
| State coverage | adequate | 내 차 사기 목록·sold잔존·업로드실패 상태 추가 → ✅ |
| Visual reference | adequate | 고아 consistency-1.html 링크·목업 라벨 각주 → ✅ |
| Bloat/Inheritance/Shape | strong | — |
| **접근성** | ❌ 대비 미달 다수 | 토큰 재계산·a11y floor 보강 → ✅ |
| **일관성** | 모순 2 | warn-amber 문구·목업 라벨 → ✅ |
| **엣지케이스** | 실패경로 공백 | critical + 일부 high 반영 → ✅ · **엣지 high 7건은 초판 누락, 교차검증 후 후속 반영**(정정 절) |

## Findings by severity (반영 상태)

### Critical (10) — 전부 반영 ✅
- **[접근성]** 흰 글자 on amber CTA = 2.10:1 → **amber CTA 글자=어두운 잉크(#1A1E1D, 8.02:1), 흰색 금지** 규칙 추가.
- **[접근성]** `ink-muted` 3.04:1(meta·면책 본문) → light `#676D69`(5.06:1)로 darken.
- **[접근성]** `price-emphasis` amber 2.68:1(가격, 큰텍스트) → light `#C0730F`(3.68:1)로 darken.
- **[접근성]** 다크 `ink-muted` 4.46:1 → `#A6A196`(5.58:1).
- **[일관성]** 목업 `landing-1.html` 폐기 라벨("매물 탐색"·"AI 검색") → 스파인에 "목업 라벨은 확정 전, EXPERIENCE Voice가 정답·스파인 우선" 각주.
- **[엣지]** 자기 매물 문의 차단(buyer≠seller) 부재 → 본인 소유 상세="내 매물 관리" 대체 노출(DB CHECK 정합).
- **[엣지]** sold/삭제 매물이 찜·채팅에 잔존 → 찜=회색+"판매완료/삭제됨" 배지·진입차단, 채팅 헤더=배지+대화 유지.
- **[엣지]** 사진 업로드 실패/용량초과/대표 삭제 승격 부재 → 인라인 오류+재시도, 다음 사진 자동 대표 승격.
- **[엣지]** 채팅 2000자 상한(기구현 b720370) 문서 드리프트 → Component/Interaction에 반영.
- **[엣지]** 내 차 사기 목록 상태 부재 → empty/skeleton/500 추가.

### High — 접근성·일관성 (초판에서 반영됨 ✅)
- warn-amber vs "amber 전용" 자기모순 → **브랜드 앰버(가격·CTA) ≠ warn-amber(경고/고지 시맨틱)** 로 분리 서술.
- 비색 신호 중복(신뢰=초록+✓+텍스트, 안읽음=점+숫자, 선택칩=채움+✓), 포커스 트랩(+Esc), 아이콘 버튼 ≥44px, AI 대화 스크린리더(role+aria-live), reduced-motion, 히어로 amber 음절 대비 → Accessibility Floor 보강.
- trust-green-ink 4.69:1(thin) → `#1B6E3D`(5.51:1) 마진 확보.
- 권한(소유권 RLS 차단+UI 미노출)·401 만료 복귀 → State 추가.

### High — 엣지케이스 (초판에서 누락 → 2026-07-12 후속 반영 ✅)
독립 교차검증에서 아래 7개 엣지케이스 High가 초판 "전부 반영"에 실제로는 빠져 있었음이 드러났다(이 중 되묻기 무한루프·매우 긴 질의는 초판에서 조용히 medium/low로 강등돼 있었음). 이번 패스에서 스파인에 실제 상태·거동·마이크로카피까지 직접 추가했다.
- **404 / 삭제·미존재·판매완료 매물 URL 직접 접근** → State 추가(404 화면 + "매물을 찾을 수 없어요…" + "매물 목록으로", 구매자 sold 직접 URL 접근도 동일 404-류).
- **폼 이탈 경고(unsaved changes)** → Component/Interaction/State 추가(사진 유실 방지 다이얼로그 + 이탈 가드).
- **채팅 재연결 시 상대방 메시지 갭 보정** → "마지막 수신 이후" 1회 재조회로 놓친 상대 메시지 병합(멱등 dedupe·순서 보정).
- **AI 검색 입력 길이 상한** → 500자 상한 + 카운터(채팅 2000자와 별개, 매우 긴 질의 폭주 방지 — 초판 강등 항목 정식화).
- **AI 되묻기 무한루프 방지** → 최대 2~3턴 후 현재 조건으로 결과 강제 제시 + 필터 유도(초판 강등 항목 정식화).
- **"내 매물 관리" 0건 빈 상태** → Voice·State 추가.
- **"내 정보 수정" 화면 명세** → 닉네임 변경(필수·검증)·저장/취소·성공 토스트, 역할 필드 없음, 이메일/비번 변경은 범위 밖.

### Medium/Low — 대부분 반영, 일부 잔존
- 반영: 상세 가격 30px 대변형 명시, 컴포넌트 행 보강, 목업 링크 정리.
- **초판 강등분 → 이번에 High로 정식 반영:** AI 되묻기 무한루프 방지·매우 긴 질의(AI 입력 상한) 2건은 초판에서 medium/low로 강등돼 있었으나, 교차검증 결과 High로 재분류해 스파인에 반영했다(위 정정·High 엣지케이스 절 참조).
- **잔존(다운스트림 재판단):** 그 외 medium/low 일부(예: 상대가 나간 방 UI 세부, 픽셀·모션 디테일)는 구현 단계에서 세부 판단 — 스파인은 원칙(상태 정의)까지 커밋, 픽셀·세부는 dev 재량.

## Reviewer files
- `review-rubric.md` · `review-accessibility.md` · `review-consistency.md` · `review-edge-cases.md`

_반영 커밋: DESIGN.md·EXPERIENCE.md(status: final, 2026-07-12). 개별 review-*.md는 보존됨._
