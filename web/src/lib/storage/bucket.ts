// 버킷 이름 상수만 두는 파일 — **서버·브라우저 어느 쪽에서도 안전하게 import된다.**
//
// 왜 별도 파일인가: 이 폴더의 index.ts는 서버 전용(서버 Supabase 클라이언트)이고
// upload.ts는 브라우저 전용(anon 클라이언트)이다. 상수를 둘 중 하나에 두면
// 반대편에서 쓰는 순간 엉뚱한 클라이언트가 번들에 딸려간다. 값만 있는 파일은 그 위험이 없다.
//
// 값의 정본은 docs/conventions.md §10.

/** 매물 사진 버킷(비공개). */
export const LISTING_IMAGES_BUCKET = 'listing-images';
