// 내 정보 (Story 11.2) — 읽기전용 계정 페이지, 서버 컴포넌트.
//
// 프로필▾ 드롭다운의 "내 정보"가 가리키는 목적지. 닉네임 편집 등 EXPERIENCE.md가 그려둔 전체
// 기능(필수·공백 검증·저장/취소·토스트)을 만드는 스토리가 아직 없어(백로그 전수 확인, Epic
// 6~14) 이번엔 이메일·역할·이름을 보여만 준다 — 편집 폼·profiles UPDATE는 이 스토리 범위 밖
// (신규 DB 마이그레이션 없음, docs/tech-debt.md #150로 이관). 근거는 spec-11-2 Design Notes 참조.
//
// 게이트: requireUser()가 비로그인을 /login으로 1차 차단(defense-in-depth) — 실사용 경로는
// proxy.ts의 PROTECTED_PREFIXES('/account' 추가)가 redirectedFrom을 실어 먼저 막는다.
//
// 매 요청 최신 프로필을 반영해야 하므로(다른 화면과 동일 관례) 정적화하지 않는다.
import { requireUser } from '@/lib/auth/guard';
import { createClient } from '@/lib/supabase/server';
import { ROLE_LABEL, type UserRole } from '@/lib/constants';
import AppHeader from '@/components/layout/AppHeader';
import ErrorState from '@/components/ui/ErrorState';

export const dynamic = 'force-dynamic';

export default async function AccountPage() {
  const user = await requireUser();
  const supabase = await createClient();

  // 본인 행만(profiles_select_self RLS, 0001) — role·name 두 컬럼만 읽는다(이메일은 auth user에서).
  // .single()이 아니라 .maybeSingle() — profiles 행이 없어도(가입 트리거 지연 등) PGRST116
  // 에러가 아니라 data: null로 받는다(코드리뷰 지적). 이 페이지의 목적은 "내가 어느 계정으로
  // 로그인했나"를 보여주는 것인데, .single()이면 행 부재만으로 DB를 거치지 않는 user.email까지
  // 함께 가려졌었다.
  const { data: profile, error } = await supabase
    .from('profiles')
    .select('role, name')
    .eq('id', user.id)
    .maybeSingle();

  if (error) {
    // 원본은 서버 로그에만, 사용자에겐 한국어 안내(sellerSummaryError와 동일 패턴 — listings/[id]/page.tsx).
    console.error('[account] 프로필 조회 실패:', error);
  }

  const roleLabel = profile?.role ? (ROLE_LABEL[profile.role as UserRole] ?? profile.role) : null;

  return (
    <>
      {/* roleLabel은 여기 넘기지 않는다(3차 코드리뷰 지적 P8) — consumer 분기는 그 prop을 받기만
          하고 렌더하지 않는다(기존 6개 호출부의 죽은 prop, 대장 #153). 이 파일은 신규 호출부라
          그 죽은 관행을 새로 반복하지 않는다 — roleLabel 변수 자체는 아래 <dd>가 그대로 쓴다. */}
      <AppHeader email={user.email} currentPath="/account" />
      <main className="mx-auto flex max-w-2xl flex-col gap-6 p-6">
        <h1 className="text-section font-bold text-ink-primary">내 정보</h1>
        {/* 진짜 에러(네트워크·RLS 등)일 때만 배너로 위에 얹는다 — .maybeSingle()이라 행 부재는
            여기 안 걸린다(코드리뷰 지적). 에러여도 아래 <dl>은 항상 그리고 이메일은 무조건 보여준다
            (이 페이지의 목적 자체가 "어느 계정으로 로그인했나" 확인이라 이메일만은 못 가린다). */}
        {error && (
          <ErrorState
            tone="danger"
            message="프로필 정보를 불러오지 못했습니다. 잠시 후 다시 시도해주세요."
          />
        )}
        <dl className="flex flex-col gap-4 rounded-card border border-border-hairline bg-surface-raised p-5 shadow-card dark:shadow-none">
          <div className="flex flex-col gap-1">
            <dt className="text-caption text-ink-muted">이메일</dt>
            <dd className="text-body text-ink-primary">{user.email ?? '-'}</dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-caption text-ink-muted">역할</dt>
            <dd className="text-body text-ink-primary">{roleLabel ?? '-'}</dd>
          </div>
          <div className="flex flex-col gap-1">
            <dt className="text-caption text-ink-muted">이름</dt>
            <dd className="text-body text-ink-primary">{profile?.name ?? '-'}</dd>
          </div>
        </dl>
      </main>
    </>
  );
}
