// 업로드 전 파일 검증 — MIME 화이트리스트 + 원본 용량 상한 (AC1·AC3).
//
// ⚠️ 이건 **UX 층의 1차 차단**이지 강제가 아니다. 브라우저 코드는 우회할 수 있으므로
// 실제 강제는 서버에 남는다 — 버킷의 allowed_mime_types·file_size_limit(0012)와
// 경로 정합성 트리거(0013). 여기서 막는다고 서버 검증을 빼지 말 것
// (docs/conventions.md §10 · :193).
//
// 값의 정본은 docs/conventions.md §10이다. 아래 두 상수는 그 계약을 코드로 옮긴 것이며,
// 호출부가 5MB·MIME 목록을 다시 적지 않도록 여기서만 내보낸다.

/** 허용 MIME 3종. 버킷 allowed_mime_types와 같아야 한다(정본: conventions §10). */
export const ALLOWED_IMAGE_MIME = ['image/jpeg', 'image/png', 'image/webp'] as const;

/** 원본 파일 용량 상한 5MB. 버킷 file_size_limit과 같아야 한다(정본: conventions §10). */
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;

/** 사용자에게 그대로 보여줄 수 있는 한국어 사유를 담는다(throw하지 않는 이유: 파일 1장의 실패가 폼 전체를 막으면 안 된다 — AC3). */
export type ImageValidationResult = { ok: true } | { ok: false; reason: string };

/** 검증에 필요한 최소 형태만 받는다 — File 전체를 요구하지 않아 테스트가 DOM 없이 돈다. */
type ValidatableFile = { type: string; size: number };

export function validateImageFile(file: ValidatableFile): ImageValidationResult {
  // MIME을 먼저 본다 — 포맷은 사용자가 그 자리에서 고칠 수 없는 문제라
  // "용량을 줄여보세요"라고 먼저 안내하면 헛수고를 시킨다.
  if (!(ALLOWED_IMAGE_MIME as readonly string[]).includes(file.type)) {
    return { ok: false, reason: 'JPG · PNG · WebP 형식만 올릴 수 있어요.' };
  }
  if (file.size <= 0) {
    return { ok: false, reason: '빈 파일이에요. 다른 사진을 선택해주세요.' };
  }
  if (file.size > MAX_IMAGE_BYTES) {
    return { ok: false, reason: '장당 최대 5MB까지 올릴 수 있어요.' };
  }
  return { ok: true };
}
