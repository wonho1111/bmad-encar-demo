// AI 검색 호출 클라이언트 (FR12·Story 4-7) — 웹이 FastAPI `/ai/search`를 부르는 유일한 통로.
//
// 왜 이 파일 하나로 모으나(단일 출처):
//   호출 주소·헤더(인증 토큰)·요청/응답 형태·에러 변환을 한 곳에 격리하면, API 계약이 바뀌어도
//   이 파일만 고치면 된다. 화면(ChatAssistant)은 searchAi()만 부르고 HTTP 세부는 몰라도 된다.
//
// 백엔드 계약(api/app/schemas/ai.py·routers/ai.py, 4.1~4.6):
//   POST {NEXT_PUBLIC_API_BASE_URL}/ai/search
//   headers: Authorization: Bearer <supabase access_token>(필수), Content-Type: application/json
//   body:    { query, context? }    // context = 직전 대화(멀티턴, 최대 12턴)
//   200:     { answer, listings[] } // listings 원소 = ListingCardData 7필드(+증분 nullable 필드)
//   비200:   { error: { code, message } }  // 401·400·422·500·503 등 공통 포맷
//   FR58(8.5): 열람(매물 목록·상세)은 anon에 열렸지만 **AI 검색은 로그인 필수**다 —
//     검색 1회 = Gemini 호출 3회 내외 = 실제 과금이라 "열람"이 아니라 "행동"(docs/conventions.md §8).
import type { ListingCardData } from '@/components/listings/ListingCard';
import { getPublicUrl } from '@/lib/storage';
import { LISTING_IMAGES_BUCKET } from '@/lib/storage/bucket';

// 멀티턴 대화 한 턴(FR18). 서버 스키마(ConversationTurn)와 동일 — content는 서버가 1~2000자로 강제한다.
// 이 형태의 단일 출처는 api/docs/ai-demo-queries.md(최대 12턴·content 2000자). 여기 값을 그대로 따른다.
export type ConversationTurn = {
  role: 'user' | 'assistant';
  content: string;
};

// /ai/search 200 응답. listings는 매물카드(ListingCard)가 그대로 받는 7필드 배열.
export type SearchResult = {
  answer: string;
  listings: ListingCardData[];
};

export type SearchAiParams = {
  query: string;
  // 직전 대화 맥락(클라이언트 보관분). 없으면(첫 질의) 미동봉 — 서버는 단일턴으로 처리한다.
  context?: ConversationTurn[];
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
export async function searchAi({ query, context, accessToken }: SearchAiParams): Promise<SearchResult> {
  if (!accessToken) {
    throw new Error('로그인이 필요합니다. 로그인한 뒤 다시 시도해주세요.');
  }
  const url = `${getApiBaseUrl()}/ai/search`;
  // context가 있으면 동봉, 없으면 키 자체를 빼서 단일턴으로 보낸다(서버 기본값 None과 동일 효과).
  const body = context && context.length > 0 ? { query, context } : { query };
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
  } catch {
    // 네트워크 자체가 실패(API 미기동·CORS·끊김). 사용자에겐 원인 대신 일반 안내(서버 미가동을 흔한 원인으로 짚어줌).
    throw new Error('AI 검색 서버에 연결하지 못했습니다. 잠시 후 다시 시도해주세요.');
  }

  if (!res.ok) {
    // 공통 에러 포맷 {error:{code,message}}을 최대한 읽어 사용자에게 보여준다. 못 읽으면 상태코드 기반 일반 문구.
    const message = await extractErrorMessage(res);
    throw new Error(message);
  }

  // 200 — 응답 형태가 깨졌으면(파싱 실패) 일반 에러로 변환.
  let data: unknown;
  try {
    data = await res.json();
  } catch {
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
