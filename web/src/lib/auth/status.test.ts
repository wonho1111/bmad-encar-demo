// getOwnStatus / writeRejectionMessage 단위테스트 (spec-17-3, DW-804 (b)).
//
// 왜 필요한가: 이 두 함수가 "쓰기 거부(0행/42501) 뒤에 정지 사유를 구분"하는 유일한 경로다
// (ListingActions.tsx·SellForm.tsx 4개 쓰기 경로가 전부 재사용). 서버/클라이언트 어느 Supabase
// 인스턴스를 넘겨도 동작해야 하므로, 여기서는 최소 인터페이스(auth.getUser + from().select().eq().single())
// 만 흉내 낸 가짜 객체로 순수 로직만 고정한다(DOM·React 불필요, vitest.config.ts 방침).
//
// "문구 분기 3갈래"(정지 / 비소유 / 이미 삭제됨) — 이 계층에서 뒤 두 가지는 **같은 신호**
// (status='active' + 0행/42501)라 구분하지 않는다(코드 주석·아래 "안 보는 것" 참고). 그래서
// 테스트도 셋을 "정지 → 정지 문구" 1개 + "비정지(비소유·이미삭제 공용) → 호출부가 준 기본
// 문구 그대로" 1개로 나눠 고정한다 — 이게 이 계층이 실제로 구분하는 전부다.
import { afterEach, describe, expect, it, vi } from 'vitest';
import { getOwnStatus, writeRejectionMessage } from './status';

// ⚠️ SUSPENDED_WRITE_MESSAGE를 **import하지 않는다**(2026-08-11 후속 코드리뷰 patch). 기대값을
// 피검사 모듈에서 가져오면 문구를 빈 문자열로 바꿔도 요청과 기대가 함께 바뀌어 영원히 통과한다
// (스펙 Always 절 + 메모리 self-consistent-assertions-never-fail, 2026-08-10 실측 사례).
// 그래서 사용자에게 실제로 뜨는 문구를 **글자 그대로** 박는다 — E2E가 쓰는 문자열과 같은 것이다.
const EXPECTED_SUSPENDED_MESSAGE = '정지된 계정입니다. 매물 등록·수정·삭제·구매 완료 처리와 채팅 보내기가 제한됩니다.';

// 최소 흉내 — supabase-js SupabaseClient 전체가 아니라 이 파일이 실제로 부르는 두 메서드만.
//
// ⚠️ select()·eq() 인자를 실제로 기록하고, single()은 **요청한 컬럼만** 돌려준다(2026-08-11 3차
// 코드리뷰 patch — guard.test.ts가 이미 고친 결함을 이 파일이 그대로 갖고 있었다). 전엔 인자를
// 무시하고 항상 opts.status를 통째로 돌려줘서, status.ts:45의 `.select('status')`를 `.select('role')`로
// 되돌려도(status가 항상 undefined가 되어 게이트가 무너지는 회귀) 전량 green이었다 — 가짜가 실제
// PostgREST보다 관대했기 때문이다.
function fakeSupabase(opts: {
  user: { id: string } | null;
  status?: string | null;
  failSelect?: boolean;
  selects?: string[];
  eqs?: Array<[string, unknown]>;
}) {
  return {
    auth: {
      getUser: async () => ({ data: { user: opts.user } }),
    },
    from: () => ({
      select: (columns: string) => {
        opts.selects?.push(columns);
        return {
          eq: (column: string, value: unknown) => {
            opts.eqs?.push([column, value]);
            return {
              single: async () => {
                if (opts.failSelect) return { data: null, error: { message: 'boom' } };
                // 요청된 컬럼만 돌려준다 — status.ts가 select하지 않은 컬럼은 undefined가 되어야
                // 회귀(예: 'status' 대신 'role'을 읽음)가 실제로 드러난다.
                const row: Record<string, unknown> = { status: opts.status };
                const data = Object.fromEntries(
                  columns
                    .split(',')
                    .map((c) => c.trim())
                    .filter((c) => c in row)
                    .map((c) => [c, row[c]]),
                );
                return { data, error: null };
              },
            };
          },
        };
      },
    }),
    // eslint 등이 완전한 타입을 요구하지 않도록 unknown 캐스팅은 호출부에서 처리.
  };
}

describe('getOwnStatus', () => {
  it('정지 계정은 suspended를 반환한다', async () => {
    const supabase = fakeSupabase({ user: { id: 'u1' }, status: 'suspended' });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('suspended');
  });

  it('활성 계정은 active를 반환한다', async () => {
    const supabase = fakeSupabase({ user: { id: 'u1' }, status: 'active' });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('active');
  });

  it('(기본값 근거) 비로그인은 active로 간주한다 — 강제력은 DB에 있으므로 화면 오판이 보안 구멍이 되지 않는다', async () => {
    const supabase = fakeSupabase({ user: null });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('active');
  });

  it('(기본값 근거) 조회 실패(네트워크 등)도 active로 간주한다 — 실패를 정지로 읽으면 장애 때 전원이 잠긴다', async () => {
    const supabase = fakeSupabase({ user: { id: 'u1' }, failSelect: true });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('active');
  });

  // 왜 별도 단언인가(2026-08-11 3차 코드리뷰 patch, guard.test.ts와 동일 관례): 위 분기 검사들은
  // "status 값이 무엇일 때 어떻게 되는가"만 본다. 정작 가장 그럴듯한 회귀 — status.ts:45의
  // `.select('status')`를 다른 컬럼으로 바꾸거나 `.eq('id', user.id)`의 id를 엉뚱한 값으로 바꾸는 것
  // — 은 값 분기를 하나도 건드리지 않는다. 기대값은 글자 그대로 박는다(상수에서 만들면 함께 바뀐다).
  it('profiles 조회가 status 컬럼만 요청하고 본인 행으로 좁힌다', async () => {
    const selects: string[] = [];
    const eqs: Array<[string, unknown]> = [];
    const supabase = fakeSupabase({ user: { id: 'u1' }, status: 'active', selects, eqs });
    await getOwnStatus(supabase as never);
    expect(selects, "select가 'status'가 아니다 — 다른 컬럼을 읽으면 status가 undefined가 되어 게이트가 무너진다").toEqual([
      'status',
    ]);
    expect(eqs, '본인 행으로 좁히지 않았다(profiles_select_self 전제)').toEqual([['id', 'u1']]);
  });

  // ── 실패가 흔적을 남기는지 (2026-08-11 후속 코드리뷰 patch) ──────────────────────────
  // 왜: 앞선 리뷰 패스가 두 실패 경로에 console.error를 넣었는데 **그걸 보는 검사가 없었다** —
  // 두 줄 다 지워도 전량 green이라, 다음 리팩터가 조용히 되돌리면 이 스토리가 고치려던
  // "실패는 흔적이 없다"가 그대로 재현된다(CLAUDE.md B4 — "만들었다가 아니라 잡는다가 완료다").
  it('profiles 조회 실패는 폴백하되 로그로 흔적을 남긴다', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const supabase = fakeSupabase({ user: { id: 'u1' }, failSelect: true });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('active');
    // ⚠️ 바로 아래 테스트("세션 없음")도 같은 console.error를 스파이하므로, 문구를 못박지 않으면
    // 이 단언은 **어느 실패 경로에서 왔든** 통과한다(2026-08-11 3차 코드리뷰 patch) — 예를 들어
    // profiles 조회 실패 로그를 통째로 지워도, 세션 없음 로그가 다른 테스트에서 호출된 적 있다는
    // 사실과 무관하게(스파이는 테스트마다 새로 만든다) 이 자리에서 정말 그 로그가 찍혔는지는
    // 문구로만 구분된다. 두 실패 경로가 실제로 다른 메시지를 낸다는 것까지 고정한다.
    expect(spy, 'profiles 조회 실패가 로그에 아무 흔적도 남기지 않는다').toHaveBeenCalledWith(
      expect.stringContaining('profiles.status 조회 실패'),
      expect.anything(),
    );
  });

  it('세션 없음(만료)도 폴백하되 로그로 흔적을 남긴다 — 두 실패 경로의 비대칭을 막는다', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const supabase = fakeSupabase({ user: null });
    await expect(getOwnStatus(supabase as never)).resolves.toBe('active');
    expect(spy, '세션 만료로 인한 거부가 로그에 아무 흔적도 남기지 않는다').toHaveBeenCalledWith(
      expect.stringContaining('세션 없음'),
    );
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('writeRejectionMessage', () => {
  const fallback = '본인 매물만 삭제할 수 있습니다. (매물을 찾을 수 없거나 접근 권한이 없습니다.)';

  it('정지(suspended)면 사유·문구를 정지 문구로 덮어쓴다', () => {
    expect(writeRejectionMessage('suspended', fallback)).toBe(EXPECTED_SUSPENDED_MESSAGE);
  });

  it('비소유(active, 타인 매물)면 호출부의 기존 문구를 그대로 쓴다', () => {
    expect(writeRejectionMessage('active', fallback)).toBe(fallback);
  });

  it('이미 삭제됨(active, 대상 행 없음)도 같은 신호라 동일하게 기존 문구를 그대로 쓴다', () => {
    // 이 계층은 "비소유"와 "이미 삭제됨"을 구분할 정보가 없다(둘 다 status='active' + 0행) —
    // 그래서 같은 fallback 인자를 받으면 같은 결과를 낸다. 실제 시나리오 재현은
    // web/e2e/suspended-access.spec.ts가 psql로 행을 직접 지운 뒤 UI에서 삭제를 눌러 확인한다.
    expect(writeRejectionMessage('active', fallback)).toBe(fallback);
  });
});

// 이 검사가 **안 보는 것**(실측 기반):
//   · profiles_select_self RLS가 실제로 본인 행을 열어주는지 — 실DB 몫(api/tests/integration이
//     이미 17.1에서 이 정책 자체를 고정했다. 이 파일은 그 정책을 호출하는 앱 로직만 본다).
//   · "비소유"와 "이미 삭제됨"을 서로 다른 문구로 구분할 수 있는지 — 위 주석대로 이 계층에선
//     구조적으로 불가능하다(같은 신호). 다음에 이걸 구분하려면 DB가 별도 신호를 내야 한다.
//   · ListingActions.tsx·SellForm.tsx가 실제로 이 함수들을 호출하는지(배선) — 이제
//     web/src/lib/auth/__tests__/suspendedGateWiringContract.test.ts가 정적 스캔으로 고정한다
//     (호출의 **존재**와 **순서**까지. 2026-08-11 후속 코드리뷰 patch 전에는 CI에 없는 E2E가
//     유일한 검증이었다). 실제 화면 문구 렌더는 여전히 web/e2e/suspended-access.spec.ts 몫.
//   · **세션 만료로 인한 거부를 "재로그인 필요"로 안내하지 못한다.** 만료되면 getUser()가 null을
//     주고 이 함수는 active로 폴백하므로, 사용자는 자기 매물인데 "본인 매물만 …" 문구를 본다
//     (로그에는 남는다 — 위 테스트가 그걸 고정한다). 구분해 안내하려면 호출부가 3상태를 받아야
//     하고 그건 이 스토리 범위 밖이다.
//   · **정지된 사용자의 거부는 실제 사유와 무관하게 전부 정지 문구가 된다**(역방향 오귀속). 정지
//     회원이 타인 매물이나 이미 삭제된 매물을 건드려도 "정지된 계정입니다"가 뜬다 — 이 계층엔
//     0행의 진짜 이유를 알 정보가 없고, 그 사용자에게 정지가 사실이긴 하므로 의도적으로 둔다.
