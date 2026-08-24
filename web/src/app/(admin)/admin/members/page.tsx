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
import { USER_ROLE, PROFILE_STATUS, type ProfileStatus } from '@/lib/constants';
import Badge from '@/components/ui/Badge';
import MemberActions from './MemberActions';

// 목록에 보여줄 최소 필드.
// ⚠️ role은 `UserRole`이 아니라 `string`이다 — profiles.role의 3값 CHECK를 0027(Story 14.1)이
// 걷어내 DB가 더 이상 어휘를 강제하지 않는다. 다른 화면들은 여전히 제네릭
// `ROLE_LABEL[role as UserRole] ?? role` 폴백 패턴을 쓰지만, 이 화면(회원관리)만은 FR61이
// admin/일반 두 값 표시 축을 명시로 요구한다(spec-15-3) — 그래서 `role === USER_ROLE.ADMIN`
// 판별로 바꾼다. 이 판별은 어떤 문자열이 들어와도 항상 '관리자' 아니면 '일반'을 반환하므로
// (undefined가 나올 수 없음), roleLabelFallback.test.ts가 지키는 "ROLE_LABEL 인덱싱은 폴백
// 필수"와는 애초에 무관하다 — 이 파일은 더 이상 ROLE_LABEL을 인덱싱하지 않는다.
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
        <h1 className="text-section font-bold text-ink-primary">회원 관리</h1>
        <p className="text-body text-ink-muted">
          전체 회원을 조회하고 이상 회원을 정지하거나 삭제할 수 있습니다.
        </p>
      </section>

      <section className="flex flex-col gap-3">
        {membersError ? (
          <p role="alert" className="text-body text-danger">
            회원 목록을 불러오지 못했습니다. 잠시 후 새로고침 해주세요.
          </p>
        ) : !members || members.length === 0 ? (
          <p className="text-body text-ink-muted">회원이 없습니다.</p>
        ) : (
          <ul className="flex flex-col gap-2">
            {members.map((m) => {
              const isSelf = m.id === user.id;
              const isSuspended = m.status === PROFILE_STATUS.SUSPENDED;
              // 표시 이름(이메일 @앞부분, 0009). 없으면 UUID 앞자리로 폴백.
              const memberLabel = m.name ?? shortId(m.id);
              // FR61 — 회원관리 화면은 구매자/판매자가 아니라 admin/일반 두 값 축으로 표시한다.
              const roleLabel = m.role === USER_ROLE.ADMIN ? '관리자' : '일반';
              return (
                <li
                  key={m.id}
                  className="flex items-center justify-between gap-3 rounded-card border border-border-hairline bg-surface-raised px-4 py-3 text-body shadow-card dark:shadow-none"
                >
                  {/* min-w-0 + truncate: 오른쪽 Badge/액션이 shrink-0이라 좁은 폭에서 양보할 쪽은
                      회원 라벨(이메일 앞부분)뿐이다. 공백 없는 긴 라벨이 min-content를 밀어 행이
                      가로로 넘치는 것을 …로 자른다(D5, 코드리뷰 patch 15.1). */}
                  <span className="flex min-w-0 items-center gap-2">
                    <span className="font-medium">{roleLabel}</span>
                    <span className="truncate text-ink-muted">{memberLabel}</span>
                    {isSelf && <Badge tone="highlight">나</Badge>}
                  </span>
                  <div className="flex items-center gap-3">
                    {isSuspended ? (
                      <Badge tone="danger">정지됨</Badge>
                    ) : (
                      <Badge tone="active">활성</Badge>
                    )}
                    {/* 본인 행에는 액션을 노출하지 않는다(자기 정지/삭제로 운영 권한 상실 방지). */}
                    {!isSelf && (
                      <MemberActions
                        memberId={m.id}
                        status={m.status}
                        label={`${roleLabel} ${memberLabel}`}
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
