// 히어로 검색 → 로그인/AI 핸드오프 sessionStorage 단일 출처 (spec-11-3).
//
// 왜 필요한가: 랜딩 히어로에서 질의를 제출하면 그 자리에서 검색을 실행하지 않고 다른 화면으로
// 이동한다 — 비로그인은 로그인 게이트(/login)로, 로그인은 /ai로. 둘 다 "이동 후 이 질의를 어떻게
// 쓸지"를 다음 화면에 전달해야 하는데, URL 쿼리스트링은 이미 redirectedFrom(복귀 경로)이 쓰고
// 있고 질의 텍스트를 얹으면 인코딩이 지저분해진다(에픽 문서가 sessionStorage로 이미 못 박음).
// 히어로(쓰기)와 ChatAssistant(읽기) 두 컴포넌트가 각자 키·모양을 따로 정하면 어긋나는 사고가
// 나므로, 이 파일 하나가 유일한 출처다.
const STORAGE_KEY = 'encar-hero-search-handoff';

export type HeroSearchHandoff = {
  query: string;
  // true=로그인 사용자 제출(/ai에서 1회 자동 실행), false=비로그인 게이트(입력창 복원만, 자동 실행 금지).
  autoRun: boolean;
  // 상세 페이지 "AI 시세 진단" 버튼 전용(5단계) — 프리필 질의의 대상 매물 id. 히어로 검색·
  // 되묻기 칩 등 다른 발신처는 이 필드를 안 채운다(옵셔널, additive — 기존 소비처 회귀 없음).
  listingId?: string;
  // 매물 미니 카드 요약(개선 1, 2026-09-01) — listingId와 세트로만 채워진다("AI 시세 진단" 버튼
  // 전용, 다른 발신처는 이것도 안 채운다). ChatAssistant가 사용자 턴을 저장할 때 함께 보관해
  // 말풍선 위에 미니 카드로 렌더한다. 서버로 나가는 API 요청 계약은 무변경 — listingId만 그대로 간다.
  listingSummary?: {
    id: string;
    manufacturer: string;
    model: string;
    year: number;
    mileage: number;
    price: number;
    imageUrl?: string | null;
  };
};

function isListingSummary(value: unknown): value is NonNullable<HeroSearchHandoff['listingSummary']> {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === 'string' &&
    typeof v.manufacturer === 'string' &&
    typeof v.model === 'string' &&
    typeof v.year === 'number' &&
    typeof v.mileage === 'number' &&
    typeof v.price === 'number' &&
    (v.imageUrl === undefined || v.imageUrl === null || typeof v.imageUrl === 'string')
  );
}

function isHeroSearchHandoff(value: unknown): value is HeroSearchHandoff {
  if (typeof value !== 'object' || value === null) return false;
  const v = value as HeroSearchHandoff;
  if (typeof v.query !== 'string' || typeof v.autoRun !== 'boolean') return false;
  if (v.listingId !== undefined && typeof v.listingId !== 'string') return false;
  if (v.listingSummary !== undefined && !isListingSummary(v.listingSummary)) return false;
  return true;
}

/** 히어로 제출/제안칩 클릭 시 호출 — 다음 화면이 읽을 질의를 저장한다. */
export function setHeroSearchHandoff(value: HeroSearchHandoff): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(value));
  } catch (err) {
    // 프라이빗 모드 등으로 sessionStorage 접근이 막혀도 페이지 이동 자체는 막지 않는다(fail-soft) —
    // 핸드오프만 못 받을 뿐, 로그인 게이트·/ai 이동은 그대로 진행돼야 한다. 다만 원인은 남긴다
    // (fail-loud 관례, WishButton.tsx와 동일) — 조용히 삼키면 "왜 복원이 안 됐지"를 디버깅할 수 없다.
    console.error('[heroSearchHandoff] 저장 실패', err);
  }
}

/**
 * `expectedAutoRun`과 일치하는 핸드오프만 읽고 즉시 삭제한다(1회용) — 값이 없거나 모양이
 * 어긋나면 null. 일치하지 않으면(= 다른 소비처 몫) **지우지 않고 그대로 둔 채** null을 반환한다.
 *
 * 왜 조건부 소비인가: 히어로(비로그인 게이트 복원, autoRun:false)와 ChatAssistant(로그인 즉시실행,
 * autoRun:true)가 같은 저장소를 공유한다. 무조건 읽고 지우면, 로그인 사용자가 제출 직후 `/ai`가
 * 뜨기 전에 `/`로 돌아오는 경우(뒤로가기 등) 히어로의 마운트 effect가 ChatAssistant 몫의
 * autoRun:true 핸드오프를 가로채 텍스트 복원만 하고 자동실행 약속을 조용히 깬다 — 대칭적으로
 * ChatAssistant도 자기 것이 아닌 autoRun:false 값을 삼켜버릴 수 있다(11-3 코드리뷰 실측 지적).
 * "읽는 즉시 지운다"라는 재과금 방지 불변식은 **내 것일 때만** 적용해야 한다.
 */
export function consumeHeroSearchHandoff(expectedAutoRun: boolean): HeroSearchHandoff | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw === null) return null;
    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      // 손상된 JSON은 파싱 단계에서 던진다 — 아무도 못 쓰므로 청소한다(고아로 남겨두지 않는다).
      sessionStorage.removeItem(STORAGE_KEY);
      console.error('[heroSearchHandoff] 저장된 값 파싱 실패', err);
      return null;
    }
    if (!isHeroSearchHandoff(parsed)) {
      // 모양이 어긋난 값도 마찬가지로 청소한다.
      sessionStorage.removeItem(STORAGE_KEY);
      console.error('[heroSearchHandoff] 저장된 값의 모양이 어긋남(query/autoRun 누락 등)', parsed);
      return null;
    }
    if (parsed.autoRun !== expectedAutoRun) {
      // 내 것이 아니다 — 반대쪽 컴포넌트가 나중에 마운트될 때 여전히 읽을 수 있게 그대로 둔다.
      return null;
    }
    sessionStorage.removeItem(STORAGE_KEY);
    return parsed;
  } catch (err) {
    console.error('[heroSearchHandoff] 소비 실패', err);
    return null;
  }
}
