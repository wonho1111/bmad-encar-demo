// 업로드 전 클라이언트 검증의 경계값 테스트 (AC1·AC3).
// 여기서 막는 건 UX 층의 1차 차단이다 — 강제는 서버(버킷 설정·트리거)에 남는다
// (docs/conventions.md:193 "클라 검증은 우회 가능하다"). 그래서 이 테스트가 초록이어도
// 서버 검증을 빼면 안 된다.
//
// **이 검사가 안 보는 것**(추측이 아니라 실제로 확인한 사각지대):
//  · file.type은 브라우저가 확장자로 추측한 값이라 **내용과 다를 수 있다** — .png로 이름만
//    바꾼 실행파일은 여기를 통과한다. 실제 차단은 버킷 allowed_mime_types(서버)가 한다.
//  · 10장 상한은 여기서 안 본다(파일 1장짜리 함수라 목록을 모른다) — PhotoUploader가 센다.
//  · 이 값들이 **버킷 설정과 실제로 같은지**는 코드가 증명하지 못한다. 두 곳에 각각 적혀
//    있고 어긋나도 아무도 안 깨진다 — 원격 버킷 설정 실측이 유일한 확인 수단이다.
//    (2026-07-18 실측: storage.buckets는 public=false · file_size_limit=5242880 ·
//     allowed_mime_types=[image/jpeg,image/png,image/webp] — 지금은 일치한다.
//     "지금은"이 핵심이다. 다음에 한쪽만 바뀌면 이 테스트는 여전히 초록이다.)
import { describe, it, expect } from 'vitest';
import { validateImageFile, MAX_IMAGE_BYTES, ALLOWED_IMAGE_MIME } from './validate';

// File 객체를 만들지 않고 필요한 두 필드만 넘긴다(node 환경엔 File이 없다 — vitest.config는 environment:'node').
const f = (type: string, size: number) => ({ type, size });

describe('validateImageFile', () => {
  it('허용 MIME 3종은 통과한다', () => {
    for (const type of ALLOWED_IMAGE_MIME) {
      expect(validateImageFile(f(type, 1024))).toEqual({ ok: true });
    }
  });

  it('5MB 정확히는 통과한다 (경계 포함)', () => {
    expect(validateImageFile(f('image/jpeg', MAX_IMAGE_BYTES))).toEqual({ ok: true });
  });

  it('5MB + 1바이트는 거부한다 (경계 바로 밖)', () => {
    const r = validateImageFile(f('image/jpeg', MAX_IMAGE_BYTES + 1));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toContain('5MB');
  });

  it('image/gif는 거부한다 (화이트리스트 밖)', () => {
    const r = validateImageFile(f('image/gif', 1024));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toContain('JPG');
  });

  it('빈 MIME(브라우저가 타입을 못 알아낸 파일)도 거부한다', () => {
    expect(validateImageFile(f('', 1024)).ok).toBe(false);
  });

  it('0바이트 파일은 거부한다', () => {
    expect(validateImageFile(f('image/png', 0)).ok).toBe(false);
  });

  it('MIME과 용량이 둘 다 틀리면 MIME 사유를 먼저 알린다 (고칠 수 없는 쪽 먼저)', () => {
    const r = validateImageFile(f('image/gif', MAX_IMAGE_BYTES + 1));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.reason).toContain('JPG');
  });
});
