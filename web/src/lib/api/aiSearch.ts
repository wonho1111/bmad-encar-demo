// AI 검색 호출 클라이언트 (FR12·Story 4-7) — 웹이 FastAPI `/ai/search`를 부르는 유일한 통로.
//
// 왜 이 파일 하나로 모으나(단일 출처):
//   호출 주소·헤더(인증 토큰)·요청/응답 형태·에러 변환을 한 곳에 격리하면, API 계약이 바뀌어도
//   이 파일만 고치면 된다. 화면(ChatAssistant)은 searchAi()만 부르고 HTTP 세부는 몰라도 된다.
//
// 백엔드 계약(api/app/schemas/ai.py·routers/ai.py, 4.1~4.6 확정):
//   POST {NEXT_PUBLIC_API_BASE_URL}/ai/search
//   headers: Authorization: Bearer <supabase access_token>, Content-Type: application/json
//   body:    { query, context? }    // context = 직전 대화(멀티턴, 최대 12턴)
//   200:     { answer, listings[] } // listings 원소 = ListingCardData 7필드
//   비200:   { error: { code, message } }  // 401·400·422·500·503 등 공통 포맷
import type { ListingCardData } from '@/components/listings/ListingCard';

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
  // Supabase 세션의 access_token. 없으면 호출 전에 막는다(어차피 서버가 401).
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
 * 인증 토큰이 없거나 비200 응답이면 한국어 메시지를 담은 Error를 throw 한다(조용한 실패 금지 — fail-loud).
 */
export async function searchAi({ query, context, accessToken }: SearchAiParams): Promise<SearchResult> {
  if (!accessToken) {
    // 이론상 proxy가 비로그인 진입을 막지만, 세션 만료 등으로 토큰이 없을 수 있어 방어한다.
    throw new Error('로그인이 필요합니다. 다시 로그인한 뒤 시도해주세요.');
  }

  const url = `${getApiBaseUrl()}/ai/search`;
  // context가 있으면 동봉, 없으면 키 자체를 빼서 단일턴으로 보낸다(서버 기본값 None과 동일 효과).
  const body = context && context.length > 0 ? { query, context } : { query };

  let res: Response;
  try {
    res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
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
    listings: Array.isArray(result.listings) ? result.listings.filter(isValidListing) : [],
  };
}

// 매물카드 한 장이 ListingCard가 요구하는 7필드를 올바른 타입으로 갖췄는지 확인한다(런타임 가드).
// 응답 형태가 계약을 벗어났을 때 화면을 깨뜨리는 대신 그 원소만 조용히 제외한다(나머지는 정상 표시).
function isValidListing(item: unknown): item is ListingCardData {
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
