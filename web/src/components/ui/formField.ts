// 폼 필드(라벨·입력칸) 표시 규칙 단일 출처 — 2026-08-13 사용자 결정.
//
// 왜 생겼나: `/search`의 필터 폼과 `/sell`의 등록 폼이 **같은 구조인데 다르게 생겼었다.**
//   · /search  라벨 `text-sm text-ink-secondary`, 입력칸 `bg-transparent px-2 py-1.5` (조밀)
//   · /sell    라벨 `text-sm font-medium`,        입력칸 `bg-surface-raised px-3 py-2` (큼직)
//   사용자 판단: **"콤보박스 배경은 흰색이 좋은데 나머지는 내 차 사기 쪽 UI가 괜찮아 보여."**
//   → 밀도·라벨은 /search 쪽(조밀)으로, 배경만 /sell 쪽(흰색=surface-raised)으로 합친다.
//
// ⚠️ 값을 여기 한 벌만 둔다. 두 파일에 각각 적어 두면 한쪽만 고쳐지고 또 갈린다(그게 이 상수가
//    생긴 이유 그 자체다). 새 폼을 만들 때도 이걸 쓴다.
//
// 이 상수가 **안 덮는 것**: 로그인·회원가입 폼(`(auth)/`)은 아직 자기 클래스를 들고 있다.
//   화면 성격이 달라(가운데 정렬된 단독 폼) 같은 밀도가 맞는지 확인이 필요해 이번 범위 밖으로 뒀다.

/** 필드 라벨(입력칸 위 설명) — 값보다 약한 잉크로 두어 값이 먼저 읽히게 한다. */
export const FIELD_LABEL_CLASS = 'text-sm text-ink-secondary';

/**
 * 입력칸 공통(select·input·textarea) — **배경은 흰색(surface-raised)이다.**
 * 예전 /search는 `bg-transparent`라 콤보박스가 페이지 배경과 같은 색이었고, 그래서 "입력할 수 있는
 * 칸"으로 안 읽혔다(사용자 지적). 테두리만으로는 부족하고 면(surface)이 달라야 눌러지는 것으로 보인다.
 */
export const FIELD_CONTROL_CLASS =
  'rounded border border-border-hairline bg-surface-raised px-2 py-1.5 text-sm text-ink-primary';
