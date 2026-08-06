// 관리자 회원 관리 화면 (FR22) — 서버 컴포넌트.
// 역할 게이트는 (admin)/layout.tsx의 requireRole(admin)이 담당하므로(자동 상속) 여기선 데이터만 준비한다.
//
// 구성:
//   1) 전체 회원 목록 — profiles_select_admin RLS(0001)로 관리자는 전체 행을 본다.
//      · profiles엔 이메일이 없다(이메일은 auth.users 소관, anon-key로 타인 이메일 조회 불가) →
//        식별은 회원 id(축약)·역할 라벨·상태 배지·가입일로 한다(이메일 표시는 service-role 필요 → 범위 밖).
//   2) 행마다 정지/해제·삭제 액션(MemberActions, 클라이언트 컴포넌트). 단 본인 행은 액션을 숨긴다(자기 정지/삭제 방지).
import { createClient } from '@/lib/supabase/server';
import { requireUser } from '@/lib/auth/guard';
import { ROLE_LABEL, PROFILE_STATUS, type UserRole, type ProfileStatus } from '@/lib/constants';
import MemberActions from './MemberActions';

// 목록에 보여줄 최소 필드.
// ⚠️ role은 `UserRole`이 아니라 `string`이다 — 그 타입을 참으로 만들어주던 profiles.role의
// 3값 CHECK를 0027(Story 14.1)이 걷어냈다. DB가 더 이상 어휘를 강제하지 않으므로 표시할 때
// 폴백이 필요하다(형제 화면들이 이미 쓰는 `ROLE_LABEL[... as UserRole] ?? role` 패턴).
// 이 규칙은 주석이 아니라 검사가 지킨다 — `src/lib/__tests__/roleLabelFallback.test.ts`가
// web/src의 모든 ROLE_LABEL 인덱싱에 폴백이 붙어 있는지 CI(web 잡)에서 매번 확인한다.
type MemberRow = {
  id: string;
  role: string;
  status: ProfileStatus;
  name: string | null; // 표시 이름(이메일 @앞부분, 0009). 회원 식별에 사용.
  created_at: string;
};

// 이름이 없을 때(예전 회원·백필 누락)만 쓰는 폴백 — 회원 id를 짧게 보여준다(전체 UUID는 길어 가독성↓). 앞 8자.
function shortId(id: string): string {
  return id.slice(0, 8);
}

export default async function AdminMembersPage() {
  const supabase = await createClient();

  // 본인 id — 본인 행에 정지/삭제 버튼을 숨기기 위해 필요(layout이 admin을 이미 보장).
  const user = await requireUser();

  // 전체 회원 최신가입 순서 파악용으로 가입일 오름차순(먼저 가입한 관리자/시드가 위).
  // error를 함께 받아 "조회 실패"와 "회원 없음"을 구분한다(SellPage 패턴).
  const { data: members, error: membersError } = await supabase
    .from('profiles')
    .select('id, role, status, name, created_at')
    .order('created_at', { ascending: true })
    .returns<MemberRow[]>();

  if (membersError) {
    // 원본 에러는 서버 로그에만(디버깅), 사용자에겐 한국어 일반 안내.
    console.error('[admin/members] 회원 목록 조회 실패:', membersError);
  }

  return (
    <main className="mx-auto flex w-full max-w-2xl flex-col gap-6 p-6">
      <section className="flex flex-col gap-2">
        <h1 className="text-2xl font-semibold">회원 관리</h1>
        <p className="text-sm text-zinc-500">
          전체 회원을 조회하고 이상 회원을 정지하거나 삭제할 수 있습니다.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        {membersError ? (
          <p role="alert" className="text-sm text-red-600 dark:text-red-400">
            회원 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !members || members.length === 0 ? (
          <p className="text-sm text-zinc-500">회원이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {members.map((m) => {
              const isSelf = m.id === user.id;
              const isSuspended = m.status === PROFILE_STATUS.SUSPENDED;
              // 표시 이름(이메일 @앞부분, 0009). 없으면 UUID 앞자리로 폴백.
              const memberLabel = m.name ?? shortId(m.id);
              return (
                <li
                  key={m.id}
                  className="flex items-center justify-between gap-3 rounded border border-zinc-200 px-4 py-3 text-sm dark:border-zinc-800"
                >
                  <span className="flex items-center gap-2">
                    <span className="font-medium">{ROLE_LABEL[m.role as UserRole] ?? m.role}</span>
                    <span className="text-zinc-400">{memberLabel}</span>
                    {isSelf && (
                      <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-950 dark:text-blue-300">
                        나
                      </span>
                    )}
                  </span>
                  <div className="flex items-center gap-3">
                    <span
                      className={
                        isSuspended
                          ? 'rounded bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700 dark:bg-red-950 dark:text-red-300'
                          : 'rounded bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700 dark:bg-green-950 dark:text-green-300'
                      }
                    >
                      {isSuspended ? '정지됨' : '활성'}
                    </span>
                    {/* 본인 행에는 액션을 노출하지 않는다(자기 정지/삭제로 운영 권한 상실 방지). */}
                    {!isSelf && (
                      <MemberActions
                        memberId={m.id}
                        status={m.status}
                        label={`${ROLE_LABEL[m.role as UserRole] ?? m.role} ${memberLabel}`}
                      />
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </main>
  );
}
