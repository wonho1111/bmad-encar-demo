// requireRole 단위테스트 (spec-17-3, DW-806).
//
// 왜 필요한가: `/admin` 콘솔 게이트가 지금까지 `role`만 보고 `status`를 안 봐서, 정지된 관리자가
// 콘솔에 그대로 들어가 버튼을 누르면 DB가 조용히 0행으로 거부했다(화면·로그 어디에도 흔적 없음).
// 이 테스트는 requireRole이 role·status 두 축을 모두 판정하는지를 실DB·브라우저 없이 값싸게
// 고정한다 — E2E(`web/e2e/suspended-access.spec.ts`)는 이 로직이 실제 라우팅에 배선됐는지(무한
// 리다이렉트 없음 포함)를 별도로 확인한다. 여기가 보는 것은 순수 로직 분기뿐이다.
//
// 기법: AppHeader.test.ts와 동일하게 '@/lib/supabase/server'를 vi.mock으로 가짜 클라이언트로
// 치환한다(next/headers의 cookies()는 요청 스코프 밖인 vitest에서 호출 자체가 실패하므로).
// redirect()는 실제로 throw하며 실행을 멈추는 Next.js 동작을 그대로 흉내 낸다 — 그래야 "role은
// 맞는데 status 검사에서 또 redirect가 호출되는" 이중 호출 버그도 잡을 수 있다(첫 redirect가
// throw하면 그 뒤 코드는 애초에 실행되지 않는다).
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

// hoisting 때문에 vi.mock 팩토리 안에서 바깥 변수를 쓸 수 없다(photo-sync.test.ts·AppHeader.test.ts와
// 동일 관례) — 기록·조작은 vi.hoisted로 만든 객체에 둔다.
const h = vi.hoisted(() => ({
  redirects: [] as string[],
  user: { id: 'u1', email: 'admin@test.com' } as { id: string; email: string } | null,
  profile: null as { role: string; status: string } | null,
  // 실제로 요청된 쿼리를 기록한다(2026-08-11 후속 코드리뷰 patch). 이게 없으면 가짜 클라이언트가
  // select 인자를 무시하고 profile을 통째로 돌려주므로, `.select('role, status')`를 `.select('role')`로
  // 되돌려도 — 이 스토리가 고친 바로 그 before-state로 되돌려도 — 네 테스트가 전부 green이었다.
  selects: [] as string[],
  eqs: [] as Array<[string, unknown]>,
  // profiles 조회 자체가 실패(네트워크·GRANT 등)하는 경우를 흉내 낸다(2026-08-11 3차 코드리뷰
  // patch — status.test.ts의 failSelect와 동일 관례를 여기에도 이식). 이게 없으면 guard.ts:65-69의
  // `if (error) { console.error(...) }` 블록을 통째로 지워도 이 파일의 어떤 테스트도 그 분기에
  // 들어가지 않으므로 전량 green이었다.
  failSelect: false,
}));

vi.mock('next/navigation', () => ({
  redirect: (path: string) => {
    h.redirects.push(path);
    // Next.js의 redirect()는 throw로 그 지점 이후 실행을 멈춘다 — 흉내 내지 않으면 role
    // 검사가 실패해도 뒤이은 status 검사·return user가 계속 돌아 이중 호출이 안 잡힌다.
    throw new Error(`REDIRECT:${path}`);
  },
}));

vi.mock('@/lib/supabase/server', () => ({
  createClient: async () => ({
    auth: {
      getUser: async () => ({ data: { user: h.user } }),
    },
    from: () => ({
      select: (columns: string) => {
        h.selects.push(columns);
        return {
          eq: (column: string, value: unknown) => {
            h.eqs.push([column, value]);
            return {
              // 요청된 컬럼만 돌려준다 — 가짜가 실제 PostgREST보다 관대하면 검사가 회귀를 못 본다.
              single: async () =>
                h.failSelect
                  ? { data: null, error: { message: 'boom' } }
                  : {
                      data:
                        h.profile === null
                          ? null
                          : Object.fromEntries(
                              columns
                                .split(',')
                                .map((c) => c.trim())
                                .filter((c) => c in h.profile!)
                                .map((c) => [c, h.profile![c as keyof typeof h.profile]]),
                            ),
                      error: null,
                    },
            };
          },
        };
      },
    }),
  }),
}));

// vi.mock은 파일 최상단으로 끌어올려지므로(hoisting) 정적 import보다 소스상 뒤에 있어도
// guard.ts는 항상 위 가짜를 문다(AppHeader.test.ts와 동일 관례).
import { requireRole } from './guard';
import { USER_ROLE } from '@/lib/constants';

describe('requireRole', () => {
  beforeEach(() => {
    h.redirects.length = 0;
    h.selects.length = 0;
    h.eqs.length = 0;
    h.user = { id: 'u1', email: 'admin@test.com' };
    // profile도 반드시 리셋한다(2026-08-11 후속 코드리뷰 patch) — 안 하면 profile을 설정하지 않은
    // 테스트가 앞 테스트의 값을 조용히 물려받아 "엉뚱한 이유로 통과"한다(테스트 순서 의존).
    h.profile = null;
    h.failSelect = false;
  });

  afterEach(() => {
    // console.error를 vi.spyOn한 테스트가 있다(아래) — 다음 테스트로 새지 않게 원복한다
    // (status.test.ts와 동일 관례).
    vi.restoreAllMocks();
  });

  it('(긍정 대조군) 활성 관리자는 리다이렉트 없이 통과하고 사용자를 반환한다 — 회귀 0', async () => {
    h.profile = { role: 'admin', status: 'active' };
    const user = await requireRole(USER_ROLE.ADMIN);
    expect(user).toEqual(h.user);
    expect(h.redirects).toEqual([]);
  });

  // 왜 별도 단언인가(2026-08-11 후속 코드리뷰 patch): 위 분기 검사들은 "status 값이 무엇일 때
  // 어떻게 되는가"만 본다. 정작 가장 그럴듯한 회귀 — .select에서 status를 도로 빼는 것 — 은
  // 값 분기를 하나도 건드리지 않는다. 기대값은 글자 그대로 박는다(상수에서 만들면 함께 바뀐다).
  it('profiles 조회가 role과 status를 함께 요청하고 본인 행으로 좁힌다', async () => {
    h.profile = { role: 'admin', status: 'active' };
    await requireRole(USER_ROLE.ADMIN);
    expect(h.selects, "select가 'role, status'가 아니다 — status를 안 읽으면 게이트가 무너진다").toEqual([
      'role, status',
    ]);
    expect(h.eqs, '본인 행으로 좁히지 않았다(profiles_select_self 전제)').toEqual([['id', 'u1']]);
  });

  it('(이 파일의 가짜 클라이언트 자체를 검증 — requireRole은 안 부른다) select 인자가 프로젝션을 실제로 좁힌다', async () => {
    // ⚠️ 제목 정정(2026-08-11 3차 코드리뷰 patch): 이전 제목 "status 컬럼을 요청하지 않으면
    // 정지된 관리자를 통과시킨다"는 requireRole의 동작처럼 읽히지만, 이 테스트 본문은 requireRole을
    // 아예 호출하지 않는다 — 위 "profiles 조회가 role과 status를 함께 요청하고…" 테스트가 성립하려면
    // **이 가짜 클라이언트가 select 인자를 실제로 존중한다**는 전제가 필요한데, 그 전제 자체를
    // 검증하는 것이 이 테스트다(회귀 탐지 단언들의 전제 조건이지, 프로덕션 동작 검사가 아니다).
    h.profile = { role: 'admin', status: 'suspended' };
    const supabase = await (await import('@/lib/supabase/server')).createClient();
    const { data } = await supabase.from('profiles').select('role').eq('id', 'u1').single();
    expect(data, "select('role')이 status까지 돌려주면 이 파일의 회귀 검사가 전부 헛돈다").toEqual({
      role: 'admin',
    });
  });

  it('정지된 관리자는 홈(/)으로 리다이렉트된다(DW-806) — 콘솔을 렌더하지 않는다', async () => {
    h.profile = { role: 'admin', status: 'suspended' };
    await expect(requireRole(USER_ROLE.ADMIN)).rejects.toThrow('REDIRECT:/');
    expect(h.redirects).toEqual(['/']);
  });

  it('(긍정 대조군, 기존 역할 게이트 회귀 없음) 활성·비관리자는 여전히 홈으로 리다이렉트된다', async () => {
    h.profile = { role: 'user', status: 'active' };
    await expect(requireRole(USER_ROLE.ADMIN)).rejects.toThrow('REDIRECT:/');
    expect(h.redirects).toEqual(['/']);
  });

  it('비로그인은 /login으로 리다이렉트된다(status 검사 이전에 이미 멈춤 — 회귀 없음)', async () => {
    h.user = null;
    await expect(requireRole(USER_ROLE.ADMIN)).rejects.toThrow('REDIRECT:/login');
    expect(h.redirects).toEqual(['/login']);
  });

  // 왜 필요한가(2026-08-11 3차 코드리뷰 patch): guard.ts:65-69의 `if (error) { console.error(...) }`는
  // 지금까지 어떤 테스트도 실행하지 않았다 — 이 파일의 가짜 single()은 항상 성공 응답만 흉내 냈다.
  // 그 블록을 통째로 지워도(에러 로그가 사라져도) 이 파일이 전량 green이었다는 뜻이다. status.ts의
  // getOwnStatus는 같은 실패를 이미 이 방식(failSelect 스위치)으로 잡고 있었는데 여기엔 없었다.
  it('profiles 조회 자체가 실패하면 흔적을 남기고(fail-closed) 홈으로 리다이렉트한다', async () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    h.failSelect = true;
    // ⚠️ getOwnStatus(status.ts)와 반대다 — 저쪽은 조회 실패를 'active'로 폴백(fail-open)해
    // "강제력은 DB에 있으니 안내 문구만 틀릴 뿐"이지만, 여기는 콘솔 **열람** 자체를 여는 유일한
    // 차단이라 실패 시 통과시키면 진짜 구멍이 된다 — 그래서 실패도 "권한 없음"과 동일하게 홈으로
    // 보낸다(guard.ts의 새 주석이 이 비대칭을 명시한다).
    await expect(requireRole(USER_ROLE.ADMIN)).rejects.toThrow('REDIRECT:/');
    expect(h.redirects, 'profiles 조회 실패 시에도 콘솔을 열어 주면 안 된다(fail-closed)').toEqual(['/']);
    expect(spy, 'profiles 조회 실패가 로그에 아무 흔적도 남기지 않는다').toHaveBeenCalledWith(
      '[auth] requireRole profiles 조회 실패:',
      expect.anything(),
    );
  });
});

// 이 검사가 **안 보는 것**(실측 기반):
//   · requireRole이 실제로 (admin)/layout.tsx에 배선돼 있는지 — 소스 스캔이나 E2E 몫.
//   · web/src/app/page.tsx의 관리자 랜딩 분기가 이 조건과 락스텝인지(무한 리다이렉트 방지 축) —
//     그건 서버 컴포넌트 간의 배선이라 이 파일은 각 파일을 독립적으로만 본다. 실제 왕복은
//     web/e2e/suspended-access.spec.ts가 브라우저로 확인한다(ERR_TOO_MANY_REDIRECTS 없음).
//   · profiles 조회 자체가 GRANT 부재 등으로 실패하는 경우(DW-722 계열) — 이 가짜 클라이언트는
//     항상 성공 응답만 흉내 낸다. 실DB 조회 실패 시나리오는 이 파일 범위 밖이다.
