// AI 검색 호출 클라이언트 (FR12·Story 4-7) — 웹이 FastAPI `/ai/search`를 부르는 유일한 통로.
//
// 왜 이 파일 하나로 모으나(단일 출처):
//   호출 주소·헤더(인증 토큰)·요청/응답 형태·에러 변환을 한 곳에 격리하면, API 계약이 바뀌어도
//   이 파일만 고치면 된다. 화면(ChatAssistant)은 searchAi()만 부르고 HTTP 세부는 몰라도 된다.
//
// 백엔드 계약(api/app/schemas/ai.py·routers/ai.py, 4.1~4.6):
//   POST {NEXT_PUBLIC_API_BASE_URL}/ai/search
//   headers: Authorization: Bearer <supabase access_token>(필수), Content-Type: application/json
//   body:    { query, context?, listing_id? }    // context = 직전 대화(멀티턴, 최대 12턴)
//                                            // listing_id = 상세 페이지 "AI 시세 진단" 버튼이 동봉하는
//                                            //   대상 매물 id(5단계, 선택 — 일반 채팅 질의는 안 보냄)
//   200:     { answer, listings[], clarify, narrowed_by, market_diagnosis, market_diagnoses } // listings 원소 = ListingCardData 7필드(+증분 nullable 필드)
//                                            // clarify = 되묻기 페이로드 또는 null(13.4, conventions.md §4)
//                                            // narrowed_by = REJECT 전용 고정 상수 또는 null(13.5, conventions.md §4)
//                                            // market_diagnosis = 시세 진단 결과 또는 null(5단계,
//                                            //   api/app/market_price.py diagnose() 반환 그대로)
//                                            // market_diagnoses = 다건 시세 진단(2026-08-31) — 2건
//                                            //   이상일 때만 배열로 채워지고, 그 외엔 null
//   비200:   { error: { code, message } }  // 401·400·422·500·503 등 공통 포맷
//   FR58(8.5): 열람(매물 목록·상세)은 anon에 열렸지만 **AI 검색은 로그인 필수**다 —
//     검색 1회 = Gemini 호출 3회 내외 = 실제 과금이라 "열람"이 아니라 "행동"(docs/conventions.md §8).
import type { ListingCardData } from '@/components/listings/ListingCard';
import type { MarketDiagnosisData } from '@/components/ai/MarketDiagnosis';
import { getPublicUrl } from '@/lib/storage';
import { LISTING_IMAGES_BUCKET } from '@/lib/storage/bucket';

// 멀티턴 대화 한 턴(FR18). 서버 스키마(ConversationTurn)와 동일 — content는 서버가 1~2000자로 강제한다.
// 이 형태의 단일 출처는 api/docs/ai-demo-queries.md(최대 12턴·content 2000자). 여기 값을 그대로 따른다.
export type ConversationTurn = {
  role: 'user' | 'assistant';
  content: string;
  // 멀티턴 매물 참조(FR18 확장) — 이 턴(assistant 전용)이 실제로 보여준 매물 id들. 서버
  // agent.py가 이 id들로 DB를 조회해 "직전에 보여준 매물" 요약을 시스템 프롬프트에 붙인다
  // ("그중 두 번째", "그 5개 비교해줘" 같은 후속 요청이 재검색 대신 이 id들로 처리되게
  // 하는 핵심 배선). user 턴엔 없다(undefined) — 서버 스키마도 assistant 턴에만 의미를 둔다.
  listing_ids?: string[];
};

// /ai/search 200 응답. listings는 매물카드(ListingCard)가 그대로 받는 7필드 배열.
export type SearchResult = {
  answer: string;
  listings: ListingCardData[];
  // 되묻기 페이로드(FR46, Story 13.4) — 서버가 되묻는 중일 때만 채워지고, 그 외(다른 라우트이거나
  // 상한 초과로 서버가 결과를 강제 제시한 경우)엔 null이다. 웹은 아직 **렌더**하지 않는다 —
  // 칩 UI를 만들 웹 스토리가 없다(DW-587). 단, searchAi()가 값은 그대로 실어 보낸다(아래 매핑).
  // (`?`를 붙이지 않는다 — searchAi()가 항상 값을 채우므로 소비처가 다뤄야 할 상태는
  //  "페이로드 있음 / null" 두 가지뿐이다. undefined까지 세 가지로 만들 이유가 없다.)
  clarify: ClarifyPayload | null;
  // REJECT 전용 고정 상수 사유 술어 배열(FR47, CR4, Story 13.5) — 서버가 REJECT(매물 무관 질의
  // 거절) 경로를 타면 항상 채워지고, 그 외 라우트는 null이다. clarify와 동일하게 웹은 아직
  // 탭 가능한 "재제안 칩" UI로 렌더하지 않는다(값만 배선 — clarify.chips와 동일 경계).
  narrowed_by: string[] | null;
  // 시세 진단 결과(5단계) — 에이전트가 market_price_stats를 호출했을 때만 채워지고, 그 외
  // (일반 매물 추천 질의 등)엔 null이다. ChatAssistant가 있으면 MarketDiagnosis 블록을 렌더한다.
  // (narrowed_by와 동일하게 wire 키 그대로 snake_case를 쓴다 — 이 타입은 응답 그대로의 계약이다.)
  market_diagnosis: MarketDiagnosisData | null;
  // 다건 시세 진단(2026-08-31, 사용자 승인 설계 변경) — market_price_stats가 이번 대화에서
  // 2건 이상 결과를 냈을 때만 채워진다(그 전부, 상한 5). 1건 이하면 null — ChatAssistant는
  // 이 경우 기존 market_diagnosis(단건 차트)를 그대로 쓴다.
  market_diagnoses: MarketDiagnosisData[] | null;
};

/** 되묻기 페이로드(FR46) — 서버가 CLARIFY 경로에서 상한 이내일 때만 채워 보낸다. */
export type ClarifyPayload = { question: string; chips: string[] };

/** wire의 clarify가 실제로 계약 형태인지 확인한다(문자열 question + 문자열 배열 chips). */
function isValidClarify(value: unknown): value is ClarifyPayload {
  if (!value || typeof value !== 'object') return false;
  const c = value as Partial<ClarifyPayload>;
  return (
    typeof c.question === 'string' &&
    Array.isArray(c.chips) &&
    c.chips.every((chip) => typeof chip === 'string')
  );
}

/** wire의 narrowed_by가 실제로 계약 형태인지 확인한다(문자열 배열, Story 13.5).
 *
 * 빈 배열(`[]`)은 거른다 — 서버 계약상 narrowed_by가 채워지면 항상 고정 3개이므로, 빈 배열은
 * 정상값이 아니라 wire/스키마 버그 신호다. `narrowed_by !== null`을 REJECT 판별로 쓰는 소비처가
 * 있다면(conventions.md §4) 빈 배열을 통과시키면 그 판별이 잘못된 REJECT 신호를 받게 된다.
 */
function isValidNarrowedBy(value: unknown): value is string[] {
  return Array.isArray(value) && value.length > 0 && value.every((v) => typeof v === 'string');
}

/** wire의 market_diagnosis가 최소한의 계약 형태(listing/criteria 객체 + comps 배열)를 갖췄는지
 * 확인한다 — 백엔드가 `dict | None`(스키마 미검증)으로 내려보내므로, 이 파일이 유일한 방어선이다
 * (listings/clarify/narrowed_by와 동일한 방침). 필드 하나하나를 다 검사하지 않는 이유는
 * MarketDiagnosis 컴포넌트가 없는 하위 필드(stats·percentile·verdict·tabpfn.price 등)를 이미
 * null-safe하게 다루도록 설계됐기 때문이다(§4 "계약-외 값은 소비처가 막는다"와 동일 결).
 */
function isValidMarketDiagnosis(value: unknown): value is MarketDiagnosisData {
  if (!value || typeof value !== 'object') return false;
  const v = value as Partial<MarketDiagnosisData>;
  return (
    typeof v.listing === 'object' &&
    v.listing !== null &&
    typeof v.criteria === 'object' &&
    v.criteria !== null &&
    Array.isArray(v.comps)
  );
}

/** wire의 market_diagnoses(복수, 2026-08-31 추가)가 배열이면 각 원소를 isValidMarketDiagnosis로
 * 걸러 유효한 것만 남긴다 — 깨진 원소 하나 때문에 표 전체를 못 그리는 대신, 그 원소만 뺀다
 * (listings의 isValidListing과 동일 태도). 2건 미만이면 표를 그릴 이유가 없으므로 null로
 * 정규화한다(백엔드 계약과 동일 — 2건 이상일 때만 채워진다).
 */
function isValidMarketDiagnoses(value: unknown): MarketDiagnosisData[] | null {
  if (!Array.isArray(value)) return null;
  const valid = value.filter(isValidMarketDiagnosis);
  return valid.length >= 2 ? valid : null;
}

export type SearchAiParams = {
  query: string;
  // 직전 대화 맥락(클라이언트 보관분). 없으면(첫 질의) 미동봉 — 서버는 단일턴으로 처리한다.
  context?: ConversationTurn[];
  // 상세 페이지 "AI 시세 진단" 버튼이 넘기는 대상 매물 id(5단계). 없으면(일반 채팅 질의) 미동봉.
  listingId?: string;
  // Supabase 세션의 access_token. 없으면(비로그인·세션 만료) 호출하지 않고 바로 throw 한다.
  accessToken: string | null | undefined;
};

// API 주소를 읽고 끝 슬래시를 정규화한다. 누락 시 불투명 throw 대신 "무엇이 비었는지" 한국어로 알린다
// (getSupabaseEnv와 동일 철학) — 설정 실수를 빨리 드러내기 위함.
function getApiBaseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!base) {
    throw new Error(
      'NEXT_PUBLIC_API_BASE_URL 환경변수가 설정되지 않았습니다. web/.env.local(로컬) 또는 배포 환경변수에 AI API 주소를 넣어주세요.',
    );
  }
  // 'http://x:8000/' + '/ai/search' 가 이중 슬래시(//ai/search)가 되지 않도록 끝 슬래시 제거.
  return base.replace(/\/+$/, '');
}

/**
 * 자연어 질의를 AI 검색 API로 보내고 {answer, listings}를 받는다.
 * 토큰이 없으면 네트워크 호출 없이 바로 throw 한다 — 서버가 어차피 401이고(로그인 필수),
 * 헛된 왕복을 만들지 않는다.
 * 비200 응답이면 한국어 메시지를 담은 Error를 throw 한다(조용한 실패 금지 — fail-loud).
 */
export async function searchAi({ query, context, listingId, accessToken }: SearchAiParams): Promise<SearchResult> {
  if (!accessToken) {
    throw new Error('로그인이 필요합니다. 로그인한 뒤 다시 시도해주세요.');
  }
  const url = `${getApiBaseUrl()}/ai/search`;
  // context·listing_id는 있을 때만 동봉, 없으면 키 자체를 뺀다(서버 기본값 None과 동일 효과).
  const body: Record<string, unknown> = { query };
  if (context && context.length > 0) body.context = context;
  if (listingId) body.listing_id = listingId;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${accessToken}`,
  };

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    });
  } catch (err) {
    // 네트워크 자체가 실패(API 미기동·CORS·끊김). 사용자에겐 원인 대신 일반 안내(서버 미가동을 흔한 원인으로 짚어줌).
    // 개발자용으로는 콘솔에 질의·원본 에러를 남긴다(DW-659) — 화면 문구·throw 동작은 그대로.
    console.error('[aiSearch] 네트워크 요청 실패:', { query, err });
    throw new Error('AI 검색 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.');
  }

  if (!res.ok) {
    // 진단용 원본 본문을 먼저 확보한다. Response 본문은 한 번만 읽히므로 clone()으로 갈라
    // extractErrorMessage(사용자 메시지 추출)와 별도로 읽는다.
    const rawBody = await res
      .clone()
      .text()
      .catch(() => '(본문 읽기 실패)');
    console.error('[aiSearch] HTTP 상태 오류:', { query, status: res.status, body: rawBody });
    // 공통 에러 포맷 {error:{code,message}}을 최대한 읽어 사용자에게 보여준다. 못 읽으면 상태코드 기반 일반 문구.
    const message = await extractErrorMessage(res);
    throw new Error(message);
  }

  // 200 — 응답 형태가 깨졌으면(파싱 실패) 일반 에러로 변환.
  let data: unknown;
  try {
    data = await res.json();
  } catch (err) {
    console.error('[aiSearch] 200 응답 JSON 파싱 실패:', { query, err });
    throw new Error('AI 검색 응답을 해석하지 못했습니다. 잠시 후 다시 시도해주세요.');
  }
  const result = data as Partial<SearchResult>;
  return {
    answer: typeof result.answer === 'string' ? result.answer : '',
    // 배열 여부만 보지 않고 "카드 한 장이 7필드를 제대로 갖췄는지"까지 검사한 뒤 깨진 원소는 버린다.
    // 이렇게 안 하면 서버가 id·price·mileage가 빠진 매물을 주었을 때 ListingCard가 렌더 도중
    // (price.toLocaleString) 터지고, 그 오류는 try/catch 밖이라 대화 화면 전체가 날아간다.
    // 깨진 원소를 버린 뒤(위 주석), 남은 카드의 image_path를 공개 URL로 조립해 image_url에 넣는다(9.6).
    listings: Array.isArray(result.listings)
      ? result.listings.filter(isValidListing).map(resolveCardImage)
      : [],
    // 되묻기 페이로드(Story 13.4) — listings와 같은 규칙으로 형태를 검사한 뒤에만 통과시키고,
    // 없거나 형태가 깨졌으면 null로 정규화한다.
    // 왜 검사하나: 타입만 선언하고 값을 그대로 흘리면, 칩 UI를 만드는 사람이 타입을 믿고
    // `clarify.chips.map(...)`을 쓰는데 서버가 chips를 문자열로 보내면 렌더 도중 터진다 —
    // listings에 isValidListing이 있는 이유와 똑같다(이 파일이 wire 값의 유일한 방어선).
    clarify: isValidClarify(result.clarify) ? result.clarify : null,
    // narrowed_by(Story 13.5) — listings/clarify와 같은 규칙: 형태가 깨졌으면(문자열 배열이 아니면)
    // null로 정규화한다(이 파일이 wire 값의 유일한 방어선).
    narrowed_by: isValidNarrowedBy(result.narrowed_by) ? result.narrowed_by : null,
    // market_diagnosis(5단계) — listings/clarify/narrowed_by와 같은 규칙: 형태가 깨졌으면 null로
    // 정규화한다(이 파일이 wire 값의 유일한 방어선).
    market_diagnosis: isValidMarketDiagnosis(result.market_diagnosis) ? result.market_diagnosis : null,
    // market_diagnoses(복수, 2026-08-31) — 위와 동일한 방어선 원칙.
    market_diagnoses: isValidMarketDiagnoses(result.market_diagnoses),
  };
}

/**
 * /ai/search 응답의 매물 원소 — 카드 계약 + `image_path`(AI 응답 **전용** 필드, Story 9.6).
 *
 * 왜 `image_url`이 아니라 별도 필드인가: **api는 사진 URL을 만들지 않는다**(`docs/conventions.md`
 * §10 — `ai_readonly` 최소권한 CR2, `api/tests/test_storage_signed_url_contract.py`가 강제).
 * 그래서 api는 원본 경로(`listing_images.storage_path`)만 보내고, URL 조립은 web이 한다.
 *
 * `image_count`를 `unknown`으로 다시 여는 이유: 아래 `isValidListing`은 **필수 7필드만** 검증하고
 * 신규 nullable 필드는 보지 않는다(§4 "런타임 가드 범위 주의"). 즉 여기 오는 값은 서버가 무엇을
 * 보냈든 아직 검증되지 않았다 — 타입이 number라고 **가정하면** 그 가정이 틀렸을 때 화면에서 터진다.
 */
type AiListingWire = Omit<ListingCardData, 'image_count'> & {
  image_path?: unknown;
  image_count?: unknown;
};

/**
 * wire 원소 → 카드 데이터. `image_path`를 공개 URL로 바꿔 `image_url`에 넣고 **경로는 버린다**.
 *
 * 이 매핑 한 겹이 이 스토리의 web 작업 전부다 — 카드 렌더(`ListingCard`/`ListingCardImage`)는
 * 9.4에서 이미 완성됐고 사진 유무 분기·"N장" 배지·2겹 로드 실패 폴백을 전부 갖고 있다.
 * `image_url`이 채워지면 그쪽이 알아서 사진을 그린다(새 컴포넌트를 만들지 않는다).
 *
 * 계약-외 값 방어(§4 "계약-외 값 정규화" — 소비처가 스스로 막는다):
 *   · `image_path`가 문자열이 아니거나 비었으면 `image_url = null` → "사진 준비중" 플레이스홀더.
 *     빈 경로로 URL을 만들면 버킷 루트를 가리키는 URL이 나와 **깨진 이미지**가 렌더된다.
 *   · `image_count`가 숫자가 아니면 0, 음수는 0으로 하한("조회 -3" 류 노출 금지).
 */
export function resolveCardImage(wire: AiListingWire): ListingCardData {
  // image_path는 여기서 소멸한다 — ListingCardData 계약에 없는 필드다(카드는 URL만 안다).
  const { image_path: rawPath, image_count: rawCount, ...card } = wire;
  const path = typeof rawPath === 'string' ? rawPath.trim() : '';
  const count = typeof rawCount === 'number' && Number.isFinite(rawCount) ? rawCount : 0;
  const url = path === '' ? null : getPublicUrl(LISTING_IMAGES_BUCKET, path);
  return {
    ...card,
    image_url: url,
    // ✎ 2026-07-20 코드리뷰 2건:
    //   · Math.trunc — Number.isFinite(2.7)은 true라 소수가 그대로 통과해 "2.7장" 배지가
    //     렌더됐다. 계약(§4)의 타입은 int이므로 여기서 정수로 자른다(반올림 아님).
    //   · url이 null이면 count도 0 — 둘을 따로 정규화하면 "사진 준비중" 플레이스홀더 위에
    //     "5장" 배지가 얹히는 자기모순 화면이 나온다. ListingCardImage가 배지를 사진 분기
    //     **밖**에 두는 것은 의도된 설계지만(로드 실패해도 장수는 남긴다 — 9.4), 그건
    //     "경로는 있는데 로드 실패"용이고 "경로가 아예 없음"과는 구분돼야 한다.
    image_count: url === null ? 0 : Math.max(0, Math.trunc(count)),
  };
}

// 매물카드 한 장이 ListingCard가 요구하는 7필드를 올바른 타입으로 갖췄는지 확인한다(런타임 가드).
// 응답 형태가 계약을 벗어났을 때 화면을 깨뜨리는 대신 그 원소만 조용히 제외한다(나머지는 정상 표시).
// ⚠️ 신규 nullable 필드(image_path·image_count 등)는 **일부러 검증하지 않는다**(§4) —
//    사진이 없다고 카드를 버리면 안 되기 때문이다. 그 방어는 resolveCardImage가 맡는다.
function isValidListing(item: unknown): item is AiListingWire {
  if (typeof item !== 'object' || item === null) return false;
  const l = item as Record<string, unknown>;
  return (
    typeof l.id === 'string' &&
    typeof l.manufacturer === 'string' &&
    typeof l.model === 'string' &&
    typeof l.year === 'number' &&
    typeof l.price === 'number' &&
    typeof l.mileage === 'number' &&
    typeof l.region === 'string'
  );
}

// 비200 응답에서 한국어 에러 메시지를 뽑는다. 백엔드 공통 포맷({error:{code,message}})이면 그 message를 쓰고,
// 아니면 상태코드별 일반 문구로 폴백한다(메시지 누락에도 사용자 안내가 비지 않게).
async function extractErrorMessage(res: Response): Promise<string> {
  try {
    const data = (await res.json()) as { error?: { message?: string } };
    const message = data?.error?.message;
    if (typeof message === 'string' && message.trim() !== '') {
      return message;
    }
  } catch {
    // JSON 파싱 실패 — 아래 상태코드 폴백으로.
  }
  if (res.status === 401) return '로그인이 필요합니다. 다시 로그인한 뒤 시도해주세요.';
  if (res.status === 400) return '요청을 처리할 수 없습니다. 질문을 바꿔 다시 시도해주세요.';
  if (res.status === 422) return '질문 형식이 올바르지 않습니다. 다시 입력해주세요.';
  if (res.status >= 500) return 'AI 검색 서버에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해주세요.';
  return 'AI 검색에 실패했습니다. 잠시 후 다시 시도해주세요.';
}
