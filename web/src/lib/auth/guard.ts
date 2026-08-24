// 서버 컴포넌트/레이아웃용 접근 제어 헬퍼 (FR3).
// proxy(루트 라우트 가드)가 "로그인 여부"를 빠르게 거른다면, 여기서는 데이터에 가까운 곳에서
// 실제 인가(역할 확인)를 집행한다 — Next.js 권장 이중 방어. Epic 2/3/6이 재사용할 단일 출처.
import { redirect } from 'next/navigation';
import { createClient } from '@/lib/supabase/server';
import { PROFILE_STATUS, type UserRole } from '@/lib/constants';

// 로그인 필수 — 비로그인 시 /login으로 보낸다. 반환: 로그인 사용자(이후 코드에서 non-null 보장).
export async function requireUser() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect('/login'); // redirect()는 throw하므로 이 아래로 진행되지 않는다.
  }
  return user;
}

// 특정 역할 필수 — 비로그인은 /login, 역할 불일치는 홈(/)으로 보낸다.
// 본인 역할은 profiles_select_self RLS로 읽는다(0001_profiles에 이미 존재, 새 정책 불필요).
//
// status도 함께 본다(spec-17-3, DW-806) — DB(0032_suspended_write_block.sql의 is_admin_active())는
// 관리자 쓰기 경로 전부를 role='admin' and status='active'로 요구하는데, 이 콘솔 게이트는 role만
// 봐서 정지된 관리자가 그대로 들어가 버튼을 전부 "살아 있는 상태"로 보고 눌러도 0행만 돌아왔다.
// 정지된 관리자도 role 불일치와 동일하게 홈(/)으로 보낸다 — web/src/app/page.tsx의 관리자 랜딩
// 분기가 status==='active'일 때만 /admin으로 되돌리도록 락스텝으로 맞춰져 있어(무한 리다이렉트
// 방지, 새 화면을 만들지 않는 선택지 ⓑ) 정지된 관리자는 홈에 그대로 머문다.
//
// ⚠️ **쓰기와 읽기의 강제 자리가 다르다 — 이 게이트는 "미리 알려줄 뿐"이 아니다**(2026-08-11
// 후속 코드리뷰 실측 정정. 그 전 주석은 "못 막아도 DB가 막는다"고 적었는데 읽기 축에서 거짓이다):
//   · 관리자 **쓰기**(회원 삭제·매물 삭제·복원 RPC 등) — 0032가 is_admin_active()로 교체해 DB가
//     막는다. 이 게이트가 없어도 안전하다.
//   · 관리자 **읽기**(콘솔의 회원·매물·채팅 목록/상세) — 0032가 admin SELECT 정책
//     (listings_select_admin·profiles_select_admin·chat_*_select_admin·listing_images_select_admin)을
//     **일부러 is_admin() 그대로 뒀다**(0032 파일 주석 13~18·45~46·265~266이 그 결정을 명시한다:
//     is_admin()을 전역으로 좁히면 읽기 정책까지 함께 좁아진다). 그래서 정지된 관리자는 DB 수준에서
//     여전히 관리자 읽기 권한을 갖고 있고, **이 앱 코드 게이트가 콘솔 열람의 유일한 차단**이다.
// 결과적으로 이 조건을 지우면 정지된 관리자가 회원 개인정보·채팅 로그를 다시 열람하게 된다 —
// DB가 받쳐 주지 않으므로 "어차피 DB가 막는다"를 근거로 지우면 안 된다. 이 예외는
// docs/conventions.md §8(정지는 열람을 막지 않는다)의 명시적 예외로 그 정본에 등재돼 있다.
//
// ⚠️ 이 status 검사는 role과 무관하게 걸린다 — role·status를 role 확인과 한 번의 조회로 묶어
// 매 요청마다 도는 게이트의 왕복을 줄이려는 의도적 선택이라, `web/src/lib/auth/status.ts`의
// `getOwnStatus`(단일 재사용 경로 원칙)를 여기서는 쓰지 않는다 — 그 헬퍼는 "쓰기 거부 뒤 사유
// 안내"용(ListingActions.tsx·SellForm.tsx 4경로)이고, 이 게이트는 "역할+정지를 한 번에" 묻는
// 별개 자리다. 지금은 admin에만 쓰이지만((admin)/layout.tsx), 나중에 열람 전용(구매자·판매자
// 등, "정지는 쓰기만 막고 열람은 허용"해야 하는 role)에 이 함수를 재사용하기 전에는 이 조건을
// 반드시 재검토할 것(docs/conventions.md §8 — 정지는 열람을 막지 않는다).
export async function requireRole(role: UserRole) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    redirect('/login');
  }

  const { data: profile, error } = await supabase
    .from('profiles')
    .select('role, status')
    .eq('id', user.id)
    .single();

  if (error) {
    // 조회 실패도 흔적을 남긴다(status.ts의 getOwnStatus와 동일 관례) — 아래 분기는 이미
    // profile이 없는 경우를 "권한 없음"으로 취급해 안전하게 홈으로 보내므로 동작은 그대로 둔다.
    console.error('[auth] requireRole profiles 조회 실패:', error);
  }

  // ⚠️ 여기(읽기 게이트)는 fail-closed, status.ts의 getOwnStatus(쓰기 거부 뒤 사유 안내)는
  // fail-open이다 — 둘을 "통일"하지 말 것(2026-08-11 3차 코드리뷰 patch). profile을 못 읽으면
  // (error가 있든 profile이 null이든) 아래 조건이 무조건 참이 되어 홈으로 보낸다 — 조회 실패가
  // 곧 "권한 없음"으로 처리된다. 반대로 getOwnStatus는 조회 실패를 'active'로 폴백한다. 다른
  // 이유다: 이 게이트는 콘솔 **열람** 자체를 여는 유일한 차단(위 주석 — 0032가 admin SELECT
  // 정책을 is_admin() 그대로 둬서 DB가 안 받쳐 준다)이라 실패 시 열어 주면 진짜 구멍이 되지만,
  // getOwnStatus는 이미 DB가 거부한 **뒤에** 안내 문구만 고르므로 실패해도 강제력은 그대로다.

  if (profile?.role !== role || profile?.status !== PROFILE_STATUS.ACTIVE) {
    redirect('/'); // 권한 없음 또는 정지 → 홈으로(권한 밖 화면 노출 차단).
  }
  return user;
}
