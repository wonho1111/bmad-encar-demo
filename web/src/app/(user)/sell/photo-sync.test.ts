// syncListingPhotos 회귀 테스트 (코드리뷰 2026-07-19 — F8).
//
// 왜 이 파일이 생겼나: 이 스토리가 "계약"으로 승격한 규칙 3개(삭제 순서 · 대표 2문장 ·
// 순차 INSERT)가 **주석에만** 있었다. 주석은 아무도 실행하지 않으므로 다음 사람이 그냥 어긴다
// (CLAUDE.md B9). 여기서 실행되는 검사로 옮긴다.
//
// ⚠️ 이 검사가 **안 보는 것**(추측 아니라 구조상 명백한 것):
//   - 실제 Supabase/Storage의 RLS·트리거 동작. 여기서는 그 경계를 가짜로 바꾸고 **우리 코드가
//     무엇을 어떤 순서로 부르는지**만 본다. "정책이 실제로 거르는가"는 원격 실측의 몫이다
//     (Task 0 · docs/conventions.md §10.1).
//   - 브라우저 실제 동작(EXIF 회전, objectURL 회수, beforeunload) — resizeImage를 가짜로 두므로
//     리사이즈 규격은 resize.test.ts와 브라우저 관찰이 담당한다.
import { describe, it, expect, vi, beforeEach } from 'vitest';
import type { PhotoItem } from './photo-item';

// ── 경계 가짜(mock) ────────────────────────────────────────────────────────
// hoisting 때문에 vi.mock 팩토리 안에서 바깥 변수를 쓸 수 없어, 기록은 vi.hoisted로 만든다.
const h = vi.hoisted(() => ({
  /** 우리 코드가 부른 순서를 **하나의 배열**에 모은다 — 순서가 계약이라서 따로 모으면 못 본다. */
  log: [] as string[],
  /** storagePath별 오브젝트 삭제 성공 여부(테스트가 조작). */
  deleteObjectOk: new Map<string, boolean>(),
  /** 업로드 성공 여부(테스트가 조작). key = 파일 이름. */
  uploadOk: new Map<string, boolean>(),
}));

vi.mock('@/lib/images/resize', () => ({
  resizeImage: async (file: File) => {
    h.log.push(`resize:${file.name}`);
    return new Blob(['x'], { type: 'image/webp' });
  },
  extensionFor: () => 'webp',
}));

vi.mock('@/lib/storage/upload', () => ({
  uploadListingImage: async (userId: string, listingId: string, filename: string) => {
    h.log.push(`upload:start`);
    // 실제 업로드는 비동기다 — 한 틱 쉬어 "순차인지 병렬인지"가 로그에 드러나게 한다.
    await new Promise((r) => setTimeout(r, 0));
    h.log.push(`upload:end`);
    const ok = h.uploadOk.size === 0 ? true : (h.uploadOk.get(filename) ?? true);
    return ok
      ? { ok: true, storagePath: `${userId}/${listingId}/${filename}` }
      : { ok: false, reason: '사진을 올리지 못했어요. 다시 시도해주세요.' };
  },
  deleteListingImageObject: async (storagePath: string) => {
    const ok = h.deleteObjectOk.get(storagePath) ?? true;
    h.log.push(`object:delete:${storagePath}:${ok ? 'ok' : 'fail'}`);
    return ok;
  },
}));

// ── 가짜 Supabase 클라이언트 ───────────────────────────────────────────────
// 체이닝(.from().update().eq().select())을 그대로 받아 **무엇을·어떤 필터로** 불렀는지 기록한다.
// thenable이라 어느 지점에서 await 해도 동작한다(실제 supabase-js와 같은 성질).
type Op = { op: string; payload?: Record<string, unknown>; filters: [string, unknown][]; single?: boolean };

/** 테스트가 특정 호출을 실패시키고 싶을 때 쓰는 훅. null을 주면 성공. */
let failWhen: (o: Op) => { message: string } | null = () => null;
/** 테스트가 특정 UPDATE를 **에러 없이 0행**으로 만들고 싶을 때 쓰는 훅(코드리뷰 2차).
 *  RLS로 막히거나 다른 세션이 먼저 지운 행은 error가 아니라 0행으로 돌아온다 — 실제 Supabase의
 *  성질이다. 전엔 이 갈래를 만들 방법이 없어 `data.length === 0` 검사를 지워도 전부 통과했다. */
let emptyWhen: (o: Op) => boolean = () => false;
let insertSeq = 0;
/** `select('storage_path')`가 돌려줄 행들(deleteListingPhotoObjects 테스트용). */
let existingRows: { storage_path: string }[] = [];

function fakeSupabase() {
  function build(op: string, payload?: Record<string, unknown>) {
    const o: Op = { op, payload, filters: [] };
    const b = {
      eq(col: string, val: unknown) {
        o.filters.push([col, val]);
        return b;
      },
      select() {
        return b;
      },
      single() {
        o.single = true;
        return b;
      },
      then<T>(res: (v: { data: unknown; error: unknown }) => T) {
        // 로그는 **결과가 정해지는 시점**이 아니라 호출 시점 기준으로 남긴다.
        const error = failWhen(o);
        // ⚠️ 필터(where 조건)를 **반드시** 로그에 담는다. 전엔 payload 값만 담아서
        // `.eq('storage_path', …)`나 `.eq('listing_id', …)`를 통째로 지워도 모든 검사가 통과했다
        // — 전자는 매물의 모든 사진을 대표로 만들어 유니크 인덱스에 걸려 죽고, 후자는 **전 매물**의
        // is_cover를 내린다. 조건절이 곧 계약이라 값만 보는 검사는 계약을 안 지킨다(코드리뷰 2차).
        const where = o.filters.map(([c, v]) => `${c}=${String(v)}`).join('&');
        const label =
          o.op === 'update' && 'is_cover' in (o.payload ?? {})
            ? `cover:${(o.payload as { is_cover: boolean }).is_cover}|${where}`
            : o.op === 'update' && 'sort_order' in (o.payload ?? {})
              ? `sort:${(o.payload as { sort_order: number }).sort_order}|${where}`
              : o.op === 'insert'
                ? `row:insert:sort=${(o.payload as { sort_order: number }).sort_order}`
                : `row:${o.op}:${o.filters.map(([, v]) => String(v)).join(',')}`;
        const empty = !error && emptyWhen(o);
        h.log.push(`${label}${error ? ':fail' : empty ? ':0행' : ''}`);

        if (error) return Promise.resolve({ data: null, error }).then(res);
        // 매물 삭제 전 사진 목록 조회(deleteListingPhotoObjects) — 테스트가 심어둔 행을 돌려준다.
        if (o.op === 'select') return Promise.resolve({ data: existingRows, error: null }).then(res);
        if (o.op === 'insert') return Promise.resolve({ data: { id: `row-${++insertSeq}` }, error: null }).then(res);
        // 0행 = error는 null인데 아무 행도 안 바뀐 상태(RLS 차단·행 없음). 실제 Supabase의 성질.
        if (o.op === 'update') return Promise.resolve({ data: empty ? [] : [{ id: 'row-x' }], error: null }).then(res);
        return Promise.resolve({ data: empty ? [] : null, error: null }).then(res);
      },
    };
    return b;
  }

  return {
    from: () => ({
      select: () => build('select'),
      delete: () => build('delete'),
      update: (payload: Record<string, unknown>) => build('update', payload),
      insert: (payload: Record<string, unknown>) => build('insert', payload),
    }),
  };
}

vi.mock('@/lib/supabase/client', () => ({ createClient: () => fakeSupabase() }));

// import는 mock 선언 뒤에 와야 한다(vitest가 hoist하지만 타입·가독성 때문에 명시적으로 아래 둔다).
const { syncListingPhotos, deleteListingPhotoObjects } = await import('./photo-sync');

// ── 픽스처 ────────────────────────────────────────────────────────────────
const USER = 'u1';
const LISTING = 'l1';

/** 새로 고른 사진(아직 저장 전). node 환경엔 File 생성자가 있지만 이름만 쓰므로 최소한으로 만든다. */
function newPhoto(name: string): PhotoItem {
  return { key: `k-${name}`, previewUrl: `blob:${name}`, status: 'idle', file: { name } as File };
}

/** 이미 저장된 사진(기존 행). */
function savedPhoto(name: string): PhotoItem {
  return {
    key: `k-${name}`,
    previewUrl: `signed:${name}`,
    status: 'uploaded',
    storagePath: `${USER}/${LISTING}/${name}.webp`,
    rowId: `row-${name}`,
  };
}

beforeEach(() => {
  h.log.length = 0;
  h.deleteObjectOk.clear();
  h.uploadOk.clear();
  failWhen = () => null;
  emptyWhen = () => false;
  insertSeq = 0;
  existingRows = [];
  vi.spyOn(console, 'error').mockImplementation(() => {});
});

/** 로그에서 접두사로 위치를 찾는다 — 라벨에 필터가 붙어 완전일치가 더는 안 되기 때문. */
const idxOf = (prefix: string) => h.log.findIndex((l) => l.startsWith(prefix));
const has = (prefix: string) => idxOf(prefix) >= 0;

// ── 계약 ① 삭제 순서: 오브젝트 먼저 → 행 나중 ─────────────────────────────
describe('계약① 삭제 순서 (Task 0 실측 · conventions §10.1)', () => {
  it('오브젝트를 먼저 지우고 그 다음 행을 지운다', async () => {
    const gone = savedPhoto('a');
    await syncListingPhotos(USER, LISTING, [], [gone]);

    const objIdx = h.log.indexOf(`object:delete:${gone.storagePath}:ok`);
    const rowIdx = h.log.indexOf('row:delete:row-a');
    expect(objIdx).toBeGreaterThanOrEqual(0);
    expect(rowIdx).toBeGreaterThanOrEqual(0);
    // 이 부등호가 계약 전부다 — 뒤집히면 소유자도 못 지우는 영구 고아가 된다(#46).
    expect(objIdx).toBeLessThan(rowIdx);
  });

  it('오브젝트 삭제가 실패하면 행을 지우지 않는다 (영구 고아 방지)', async () => {
    const gone = savedPhoto('a');
    h.deleteObjectOk.set(gone.storagePath!, false);

    const r = await syncListingPhotos(USER, LISTING, [], [gone]);

    expect(h.log).toContain(`object:delete:${gone.storagePath}:fail`);
    expect(h.log).not.toContain('row:delete:row-a'); // ← 행 삭제가 아예 안 나가야 한다
    expect(r.failedCount).toBe(1);
    expect(r.warnings).toContain('사진을 삭제하지 못했어요. 다시 시도해주세요.');
  });

  it('행 삭제가 실패하면 조용히 넘기지 않고 warning으로 알린다', async () => {
    const gone = savedPhoto('a');
    failWhen = (o) => (o.op === 'delete' ? { message: 'boom' } : null);

    const r = await syncListingPhotos(USER, LISTING, [], [gone]);
    expect(r.warnings).toContain('사진 삭제 정보를 정리하지 못했어요.');
  });
});

// ── 계약 ② 대표 기록: 반드시 2문장 ────────────────────────────────────────
describe('계약② 대표 기록 2문장 (#47-1 도커 실측)', () => {
  it('전체 false로 내린 뒤 1장만 true로 올린다 (단일 UPDATE 금지)', async () => {
    await syncListingPhotos(USER, LISTING, [newPhoto('a'), newPhoto('b')], []);

    const falseIdx = idxOf('cover:false');
    const trueIdx = idxOf('cover:true');
    expect(falseIdx).toBeGreaterThanOrEqual(0);
    expect(trueIdx).toBeGreaterThan(falseIdx); // 순서가 뒤집히면 duplicate key로 죽는다
    expect(h.log.filter((l) => l.startsWith('cover:true'))).toHaveLength(1); // 대표는 정확히 1장
  });

  it('두 문장 모두 이 매물로 범위를 좁힌다 (listing_id 필터가 계약이다)', async () => {
    // 이 검사가 없으면 `.eq('listing_id', listingId)`를 지워도 전부 통과했다 —
    // 실제로는 **전 매물**의 is_cover를 내리는 재앙적 UPDATE가 된다(코드리뷰 2차).
    // 새 사진은 파일명이 uuid라 경로를 예측할 수 없어, 경로가 정해진 기존 행으로 검사한다.
    const a = savedPhoto('a');
    await syncListingPhotos(USER, LISTING, [a], [a]);

    expect(h.log.filter((l) => l.startsWith('cover:'))).toEqual([
      `cover:false|listing_id=${LISTING}`,
      `cover:true|listing_id=${LISTING}&storage_path=${a.storagePath}`,
    ]);
  });

  it('대표 지정은 정확히 1장을 지목한다 (storage_path 필터가 계약이다)', async () => {
    // 이 검사가 없으면 `.eq('storage_path', …)`를 지워도 통과했다 — 실제로는 그 매물 전 사진에
    // is_cover=true를 걸어 부분 유니크 인덱스에 걸려 죽는다(#47-1).
    const a = savedPhoto('a');
    const b = savedPhoto('b');
    await syncListingPhotos(USER, LISTING, [a, b], [a, b]);

    const setCover = h.log.find((l) => l.startsWith('cover:true'));
    expect(setCover).toContain(`storage_path=${a.storagePath}`); // 0번 사진만
    expect(setCover).not.toContain(b.storagePath!);
  });

  it('리셋(false) 문장이 실패하면 두 번째 문장을 아예 쏘지 않고 알린다', async () => {
    failWhen = (o) => (o.op === 'update' && o.payload?.is_cover === false ? { message: 'boom' } : null);

    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);

    expect(has('cover:false')).toBe(true);
    expect(h.log.some((l) => l.startsWith('cover:false') && l.endsWith(':fail'))).toBe(true);
    expect(has('cover:true')).toBe(false); // 어차피 유니크 인덱스에 걸린다
    expect(r.warnings).toContain('대표 사진 정보를 정리하지 못했어요.');
  });

  it('대표 지정(true)이 실패하면 "성공"이라 말하지 않는다', async () => {
    failWhen = (o) => (o.op === 'update' && o.payload?.is_cover === true ? { message: 'boom' } : null);

    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);
    expect(r.warnings).toContain('대표 사진을 지정하지 못했어요.');
  });

  it('대표 지정이 0행이면(에러 아님) 조용히 넘기지 않는다 — 그 매물은 대표 0장이 된다', async () => {
    // 바로 앞 문장이 전체를 false로 내린 뒤라, 여기서 0행이면 결과는 "대표 없음"이다.
    // 전엔 .select()가 없어 error만 봤고, 0행이 성공으로 흘러 사용자는 성공 안내를 받았다(코드리뷰 2차).
    emptyWhen = (o) => o.op === 'update' && o.payload?.is_cover === true;

    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);
    expect(r.warnings).toContain('대표 사진을 지정하지 못했어요.');
  });

  it('대표 리셋이 0행이면(에러 아님) 두 번째 문장을 쏘지 않는다', async () => {
    emptyWhen = (o) => o.op === 'update' && o.payload?.is_cover === false;

    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);
    expect(has('cover:true')).toBe(false);
    expect(r.warnings).toContain('대표 사진 정보를 정리하지 못했어요.');
  });

  it('저장된 사진이 0장이면 대표 지정 문장을 쏘지 않는다', async () => {
    await syncListingPhotos(USER, LISTING, [], []);
    expect(has('cover:false')).toBe(true);
    expect(has('cover:true')).toBe(false);
  });
});

// ── 계약 ③ 순차 INSERT ────────────────────────────────────────────────────
describe('계약③ 업로드·행 INSERT는 순차 (#49 10장 상한 경합)', () => {
  it('업로드가 겹치지 않는다 (start,end,start,end — 병렬이면 start,start가 붙는다)', async () => {
    await syncListingPhotos(USER, LISTING, [newPhoto('a'), newPhoto('b'), newPhoto('c')], []);

    const uploads = h.log.filter((l) => l.startsWith('upload:'));
    expect(uploads).toEqual([
      'upload:start', 'upload:end',
      'upload:start', 'upload:end',
      'upload:start', 'upload:end',
    ]);
  });

  it('행 INSERT도 화면 순서대로 하나씩 나간다', async () => {
    await syncListingPhotos(USER, LISTING, [newPhoto('a'), newPhoto('b')], []);
    const inserts = h.log.filter((l) => l.startsWith('row:insert'));
    expect(inserts).toEqual(['row:insert:sort=0', 'row:insert:sort=1']);
  });
});

// ── 불변식: 대표 = sort_order 0번 (실패 경로 포함) ────────────────────────
describe('불변식 "대표 = sort_order 0번"이 실패 경로에서도 유지된다', () => {
  it('중간 INSERT가 실패해도 sort_order에 구멍이 남지 않는다', async () => {
    // 두 번째 INSERT만 실패시킨다.
    let n = 0;
    failWhen = (o) => (o.op === 'insert' && ++n === 2 ? { message: 'boom' } : null);

    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a'), newPhoto('b'), newPhoto('c')], []);

    // b가 실패했으니 c가 1번 자리를 그대로 메워야 한다 — 0,1,1(재시도) 이 아니라 0,1,1이 아니라
    // "0 → (실패) → 1" 이어야 한다.
    const inserts = h.log.filter((l) => l.startsWith('row:insert'));
    expect(inserts).toEqual(['row:insert:sort=0', 'row:insert:sort=1:fail', 'row:insert:sort=1']);
    expect(r.savedCount).toBe(2);
    expect(r.failedCount).toBe(1);
  });

  it('첫 INSERT가 실패하면 대표는 sort_order=0을 실제로 받은 사진에 붙는다', async () => {
    let n = 0;
    failWhen = (o) => (o.op === 'insert' && ++n === 1 ? { message: 'boom' } : null);

    await syncListingPhotos(USER, LISTING, [newPhoto('a'), newPhoto('b')], []);

    // a는 실패해 storagePath가 비워지므로 survivors[0] = b, 그리고 b가 받은 sort_order도 0이다.
    const inserts = h.log.filter((l) => l.startsWith('row:insert'));
    expect(inserts).toEqual(['row:insert:sort=0:fail', 'row:insert:sort=0']);
  });

  it('같은 사유의 경고는 한 번만 담는다 (사용자 문구에 그대로 이어 붙기 때문)', async () => {
    // 기존 행 3장 전부 순서 갱신 실패 → 같은 문구가 3번 쌓이면 안 된다.
    failWhen = (o) => (o.op === 'update' && 'sort_order' in (o.payload ?? {}) ? { message: 'boom' } : null);

    const rows = [savedPhoto('a'), savedPhoto('b'), savedPhoto('c')];
    const r = await syncListingPhotos(USER, LISTING, rows, rows);

    expect(r.warnings.filter((w) => w === '사진 순서를 저장하지 못한 항목이 있어요.')).toHaveLength(1);
  });

  it('sort_order 갱신이 0행이면(에러 아님) 성공으로 치지 않는다', async () => {
    // 전엔 이 갈래를 만들 수 없어 error로 대신 시뮬레이션했고, 그래서 `data.length === 0` 검사를
    // 지워도 통과했다. 이제 진짜 0행을 만든다(코드리뷰 2차).
    const a = savedPhoto('a');
    const b = savedPhoto('b');
    let seen = false;
    emptyWhen = (o) => {
      if (o.op === 'update' && o.payload?.sort_order === 0 && !seen) {
        seen = true;
        return true;
      }
      return false;
    };

    const r = await syncListingPhotos(USER, LISTING, [a, b], [a, b]);

    expect(r.warnings).toContain('사진 순서를 저장하지 못한 항목이 있어요.');
    // 실패한 항목이 카운터를 올리지 않으므로 b가 0번을 이어받는다.
    expect(h.log.filter((l) => l.startsWith('sort:')).map((l) => l.split('|')[0] + (l.endsWith(':0행') ? ':0행' : '')))
      .toEqual(['sort:0:0행', 'sort:0']);
  });

  it('🔴 기존 행의 sort_order 갱신이 실패해도 대표는 실제로 0번을 받은 행에 붙는다', async () => {
    // 1차 리뷰 P3은 **INSERT 실패 갈래만** 고쳤다. 기존 행의 UPDATE 실패 갈래는 storagePath를
    // 비우지 않아 survivors[0]에 그대로 남고, 대표가 sort_order=0이 아닌 행에 붙는다.
    // (코드리뷰 2차 A-1 — Auditor가 재현 실행으로 증명한 상태를 여기 고정한다.)
    const a = savedPhoto('a');
    const b = savedPhoto('b');
    // a의 순서 갱신만 실패시킨다(행 id로 지목) — sort_order 값으로 지목하면 b가 물려받은
    // 0번 갱신까지 같이 실패해 정작 보려던 상태가 안 만들어진다.
    failWhen = (o) =>
      o.op === 'update' && o.filters.some(([c, v]) => c === 'id' && v === a.rowId) ? { message: 'boom' } : null;

    await syncListingPhotos(USER, LISTING, [a, b], [a, b]);

    // a가 0번 갱신에 실패했으므로 실제로 sort_order=0을 받은 건 b다 → 대표도 b여야 한다.
    const setCover = h.log.find((l) => l.startsWith('cover:true'));
    expect(setCover).toContain(`storage_path=${b.storagePath}`);
    expect(setCover).not.toContain(`storage_path=${a.storagePath}`);
  });

  it('🔴 오브젝트 삭제에 실패한 사진이 대표가 되지 않는다', async () => {
    // 삭제 실패 항목은 목록에 되돌려주지만(아직 DB에 살아 있으니 사실이다), 사용자가 **지우려던**
    // 사진이다. 그런데 되돌리는 위치가 맨 앞이라 survivors[0]이 되어 대표 도장을 받았다.
    // (코드리뷰 2차 — 3개 레이어 전원 지목)
    const gone = savedPhoto('gone');
    const kept = savedPhoto('kept');
    h.deleteObjectOk.set(gone.storagePath!, false);

    const r = await syncListingPhotos(USER, LISTING, [kept], [gone, kept]);

    const setCover = h.log.find((l) => l.startsWith('cover:true'));
    expect(setCover).toContain(`storage_path=${kept.storagePath}`);
    // 사용자가 지우려던 사진이 화면 0번을 되찾아서도 안 된다.
    expect(r.photos[0].storagePath).toBe(kept.storagePath);
  });
});

// ── 재제출 안전성 (F1 역고아) ─────────────────────────────────────────────
describe('재제출 안전성', () => {
  it('INSERT 성공 시 rowId를 화면 상태에 되돌려준다 (재제출이 같은 사진을 다시 INSERT하지 않게)', async () => {
    const r = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);
    expect(r.photos[0].rowId).toBe('row-1');
    expect(r.photos[0].storagePath).toBeTruthy();
  });

  it('돌려받은 결과를 그대로 재제출하면 INSERT가 아니라 순서 UPDATE만 나간다', async () => {
    const first = await syncListingPhotos(USER, LISTING, [newPhoto('a')], []);
    h.log.length = 0;

    await syncListingPhotos(USER, LISTING, first.photos, first.photos);

    expect(h.log.filter((l) => l.startsWith('row:insert'))).toEqual([]); // 재INSERT 0건
    expect(has('sort:0')).toBe(true);
    expect(h.log.some((l) => l.startsWith('object:delete'))).toBe(false); // 저장된 파일을 지우지 않는다
  });
});

// ── 매물 삭제 전 사진 정리 (#60) ──────────────────────────────────────────
describe('deleteListingPhotoObjects — 매물 삭제 전 사진 파일 정리 (#60)', () => {
  it('그 매물의 오브젝트를 전부 지운다', async () => {
    existingRows = [{ storage_path: 'p/1.webp' }, { storage_path: 'p/2.webp' }];

    const r = await deleteListingPhotoObjects(LISTING);

    expect(r).toEqual({ ok: true, deleted: 2 });
    expect(h.log.filter((l) => l.startsWith('object:'))).toEqual([
      'object:delete:p/1.webp:ok',
      'object:delete:p/2.webp:ok',
    ]);
  });

  it('행은 지우지 않는다 — 그건 매물 삭제의 cascade 몫이고, 그 순서가 계약이다', async () => {
    existingRows = [{ storage_path: 'p/1.webp' }];
    await deleteListingPhotoObjects(LISTING);
    expect(h.log.some((l) => l.startsWith('row:delete'))).toBe(false);
  });

  it('오브젝트 삭제가 하나라도 실패하면 ok:false — 호출부가 매물 삭제를 멈춰야 한다', async () => {
    existingRows = [{ storage_path: 'p/1.webp' }, { storage_path: 'p/2.webp' }];
    h.deleteObjectOk.set('p/2.webp', false);

    const r = await deleteListingPhotoObjects(LISTING);
    expect(r.ok).toBe(false);
  });

  it('실패해도 나머지를 계속 시도한다 — 중단하면 앞부분만 지워진 채 재시도가 막힌다', async () => {
    // 첫 항목에서 return하면 뒤 항목은 손도 못 대고, 이미 지운 앞 항목은 되돌릴 수 없다.
    // 되돌릴 수 없는 일이 벌어졌으면 최소한 나머지도 정리를 시도해야 한다(코드리뷰 2차).
    existingRows = [{ storage_path: 'p/1.webp' }, { storage_path: 'p/2.webp' }, { storage_path: 'p/3.webp' }];
    h.deleteObjectOk.set('p/1.webp', false);

    const r = await deleteListingPhotoObjects(LISTING);

    expect(r.ok).toBe(false);
    expect(h.log.filter((l) => l.startsWith('object:delete'))).toEqual([
      'object:delete:p/1.webp:fail',
      'object:delete:p/2.webp:ok',
      'object:delete:p/3.webp:ok',
    ]);
    expect(r.deleted).toBe(2); // 실제로 지운 개수를 사실대로 돌려준다
  });

  it('목록 조회 자체가 실패하면 "사진 없음"으로 갈음하지 않는다', async () => {
    failWhen = (o) => (o.op === 'select' ? { message: 'boom' } : null);

    const r = await deleteListingPhotoObjects(LISTING);
    expect(r.ok).toBe(false); // 모르는 상태를 성공으로 넘기면 조용히 고아가 된다
  });

  it('사진이 0장이면 그대로 성공 — 삭제를 막지 않는다', async () => {
    existingRows = [];
    expect(await deleteListingPhotoObjects(LISTING)).toEqual({ ok: true, deleted: 0 });
  });
});

// ── 검증 실패(거부) 항목 취급 — 사용자 결정 ②-(a) ─────────────────────────
describe('검증 실패(용량초과·포맷거부) 항목', () => {
  const rejected: PhotoItem = {
    key: 'k-big',
    previewUrl: null,
    status: 'error',
    error: '5MB를 넘는 사진이에요.',
    retryable: false,
    file: { name: 'big.png' } as File,
  };

  it('failedCount에 세지 않는다 (세면 재제출 때마다 이동이 영구히 막힌다)', async () => {
    const r = await syncListingPhotos(USER, LISTING, [rejected, newPhoto('a')], []);
    expect(r.failedCount).toBe(0);
    expect(r.savedCount).toBe(1);
  });

  it('업로드를 시도하지 않고 목록에는 남긴다 (AC3 — 어느 파일이 왜 안 됐는지 보여준다)', async () => {
    const r = await syncListingPhotos(USER, LISTING, [rejected], []);
    expect(h.log.filter((l) => l.startsWith('upload:'))).toEqual([]);
    expect(r.photos).toHaveLength(1);
    expect(r.photos[0].status).toBe('error');
  });

  it('거부 항목이 0번이어도 대표는 실제로 저장된 사진에 붙는다', async () => {
    await syncListingPhotos(USER, LISTING, [rejected, newPhoto('a')], []);
    expect(h.log).toContain('row:insert:sort=0'); // 거부 항목이 0번을 잡아먹지 않는다
    expect(idxOf('cover:false')).toBeLessThan(idxOf('cover:true'));
  });
});
