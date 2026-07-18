// getPublicUrl — 공개 버킷 URL 조립 (Story 9.0).
//
// 왜 단위테스트인가: 순수 함수이고(서버 컴포넌트 밖) URL 문자열이 한 글자만 틀려도
// 모든 사진이 조용히 플레이스홀더로 떨어진다 — 화면으로는 "사진이 없는 매물"과 구별되지 않는다.
import { describe, expect, it, beforeAll } from 'vitest';

import { getPublicUrl } from './index';

const BASE = 'https://example.supabase.co';

beforeAll(() => {
  process.env.NEXT_PUBLIC_SUPABASE_URL = BASE;
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY = 'test-anon-key';
});

describe('getPublicUrl', () => {
  it('공개 오브젝트 경로 형식을 만든다', () => {
    expect(getPublicUrl('listing-images', 'uid/listing/a.webp')).toBe(
      `${BASE}/storage/v1/object/public/listing-images/uid/listing/a.webp`,
    );
  });

  it('경로 구분자(/)는 인코딩하지 않는다 — %2F가 되면 경로가 깨진다', () => {
    expect(getPublicUrl('b', 'x/y/z.webp')).not.toContain('%2F');
  });

  it('공백·한글 파일명을 세그먼트별로 인코딩한다', () => {
    expect(getPublicUrl('b', 'uid/listing/내 차 사진.webp')).toBe(
      `${BASE}/storage/v1/object/public/b/uid/listing/${encodeURIComponent('내 차 사진.webp')}`,
    );
  });
});
