// 업로더가 다루는 사진 항목의 **타입과 변환 함수만** 두는 모듈.
//
// 왜 PhotoUploader.tsx에서 떼어냈나 (실측으로 배운 것, 2026-07-18):
//   처음엔 toPhotoItems를 PhotoUploader.tsx에 뒀는데, 그 파일은 'use client'라
//   수정 페이지(서버 컴포넌트)가 부르는 순간 런타임에 죽었다 —
//   "Attempted to call toPhotoItems() from the server but toPhotoItems is on the client".
//   ⚠️ tsc·eslint·next build **셋 다 통과했고** 실제로 페이지를 열어서야 500으로 드러났다.
//   경계 위반은 타입이 아니라 실행이 잡는다.
// 이 파일에는 'use client'가 없어서 서버·브라우저 양쪽에서 안전하게 import된다.

/** 매물당 사진 상한. 정본: docs/conventions.md §10. */
export const MAX_PHOTOS = 10;

// 업로드 진행·실패는 **이 세션의 화면 상태일 뿐**이고 wire(DB·JSON)로 나가지 않는다(AC6).
export type PhotoStatus = 'idle' | 'uploading' | 'uploaded' | 'error';

export type PhotoItem = {
  /** React key 겸 항목 식별자(순서를 바꿔도 미리보기가 튀지 않도록 안정적이어야 한다). */
  key: string;
  /** 화면에 그릴 URL. 기존 사진은 서버가 발급한 서명 URL, 새 사진은 objectURL. */
  previewUrl: string | null;
  status: PhotoStatus;
  /** 인라인 오류 사유(한국어). status==='error'일 때만 채운다. */
  error?: string;
  /** 다시 시도해볼 만한 실패인가. 용량초과·포맷 거부는 재시도해도 같은 결과라 false. */
  retryable?: boolean;

  /** 새로 고른 파일(아직 Storage에 없음). 기존 사진이면 undefined. */
  file?: File;
  /** 이미 저장된 사진의 Storage 경로. 새 사진은 업로드 성공 후 채워진다. */
  storagePath?: string;
  /** 이미 저장된 사진의 listing_images 행 id. */
  rowId?: string;
};

// ⚠️ 예전엔 `let seq = 0`(모듈 레벨 카운터)였다 — 서버(toPhotoItems)와 브라우저(toLocalPhotoItem)가
// 각자 다른 모듈 인스턴스를 가져서 둘 다 1부터 세고, 그 결과 같은 화면에 기존 사진과 새 사진이
// 같은 key(`photo-1`)를 갖는 충돌이 났다(코드리뷰 2026-07-19). crypto.randomUUID()는 두 런타임
// 모두에서 쓸 수 있어(새 의존성 없음) 충돌이 구조적으로 없다.
const nextKey = () => `photo-${crypto.randomUUID()}`;

/** 서버가 내려준 기존 사진을 업로더 항목으로 바꾼다(수정 화면 진입 시 서버에서 호출). */
export function toPhotoItems(
  rows: { id: string; storage_path: string; url: string | null }[],
): PhotoItem[] {
  return rows.map((r) => ({
    key: nextKey(),
    previewUrl: r.url,
    status: 'uploaded' as const,
    storagePath: r.storage_path,
    rowId: r.id,
  }));
}

/** 브라우저에서 새로 고른 파일을 항목으로 만든다(PhotoUploader 전용). */
export function toLocalPhotoItem(file: File, previewUrl: string | null, error?: string): PhotoItem {
  return error
    ? { key: nextKey(), previewUrl, status: 'error', error, retryable: false, file }
    : { key: nextKey(), previewUrl, status: 'idle', file };
}
