// 본인 profiles.status 조회 — 단일 헬퍼 (spec-17-3).
//
// 왜 필요한가: 17.1(RLS)이 정지 회원의 쓰기를 DB에서 이미 전부 막았다. 그런데 화면은 그 사실을
// 몰라 0행/42501 거부를 전부 "본인 매물이 아니다" 같은 엉뚱한 사유로 안내했다(DW-804 (b)).
// 이 파일은 "거부가 난 뒤에" 사유를 조회하는 유일한 경로다 — 절대 쓰기 전에 먼저 이 함수를 불러
// 막는 형태로 쓰지 않는다. 그러면 화면이 사전 검사가 되어 강제력의 자리를 앱 코드로 옮기게 된다
// (스토리 Always 규칙, CLAUDE.md B9).
//
// 서버(guard.ts)·클라이언트(ListingActions.tsx·SellForm.tsx) 양쪽에서 재사용한다 — 그래서 이 파일
// 안에서 Supabase 클라이언트를 직접 만들지 않고 호출부가 만든 인스턴스를 인자로 받는다(서버 전용
// 모듈인 '@/lib/supabase/server'를 여기서 import하면 'use client' 컴포넌트가 그걸 끌고 들어가 빌드가
// 깨진다).
import type { SupabaseClient } from '@supabase/supabase-js';
import { PROFILE_STATUS, type ProfileStatus } from '@/lib/constants';

// 17.1이 실제로 막는 범위와 정확히 일치해야 한다(docs/conventions.md §8) — 사실만 말한다.
// ⚠️ 구매 완료도 이 열거에 포함한다(2026-08-11 3차 코드리뷰 patch) — E2E B4가 확인하듯 이 문구는
// 구매 완료 경로(ListingActions.handleComplete)에도 그대로 뜨는데, 원래 열거엔 그 행위가 빠져
// 있어 방금 구매 완료를 누른 사용자가 자신이 하지 않은 행동 목록을 읽게 됐다.
export const SUSPENDED_WRITE_MESSAGE =
  '정지된 계정입니다. 매물 등록·수정·삭제·구매 완료 처리와 채팅 보내기가 제한됩니다.';

/**
 * 현재 로그인 사용자의 profiles.status를 조회한다. profiles_select_self RLS(0001)가 본인 행만
 * 열어주므로 새 정책은 필요 없다.
 *
 * 조회 실패(비로그인·네트워크 오류·행 없음) 시 기본값은 'active'다 — 강제력은 DB(RLS)에 있으므로
 * 화면이 상태를 잘못 판단해도 "안내 문구가 틀릴 뿐"이지 보안 구멍이 되지 않는다. 반대로 실패를
 * "정지"로 읽으면 일시적 조회 장애만으로 활성 사용자 전원이 잘못된 정지 안내를 보게 된다.
 */
export async function getOwnStatus(supabase: SupabaseClient): Promise<ProfileStatus> {
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    // 이 함수는 **쓰기 거부를 받은 뒤에만** 불린다 — 그 시점에 세션이 없다는 건 비로그인 방문이
    // 아니라 **세션이 그새 만료됐다**는 뜻이다(만료되면 RLS가 anon으로 보므로 본인 매물도 0행이
    // 돌아온다). 그 경우 사용자는 "본인 매물만 삭제할 수 있습니다"를 보게 되는데 실제 사유는
    // 재로그인 필요다 — 이 계층에서 그 둘을 구분해 안내하지는 않지만(스토리 범위 밖), 아래
    // profiles 조회 실패와 같은 이유로 흔적은 남긴다(2026-08-11 후속 코드리뷰 patch — 두 실패
    // 경로 중 한쪽만 로그가 있는 비대칭이었다).
    console.error('[auth] profiles.status 조회 생략: 세션 없음(만료 의심) — 거부 사유를 정지로 구분할 수 없다');
    return PROFILE_STATUS.ACTIVE;
  }

  const { data: profile, error } = await supabase
    .from('profiles')
    .select('status')
    .eq('id', user.id)
    .single();

  if (error) {
    // 조회 자체가 실패(네트워크·GRANT 등) — 'active'로 폴백하는 건 의도된 동작이지만(위 주석),
    // 그 실패가 로그 어디에도 안 남으면 이 스토리가 고치려던 "0행은 흔적이 없다"와 같은 문제가
    // 이 헬퍼 안에 그대로 재현된다. 흔적만 남긴다 — 폴백 동작 자체는 바꾸지 않는다.
    console.error('[auth] profiles.status 조회 실패:', error);
  }

  return profile?.status === PROFILE_STATUS.SUSPENDED ? PROFILE_STATUS.SUSPENDED : PROFILE_STATUS.ACTIVE;
}

/**
 * 쓰기 거부(0행 또는 42501) 이후 사유를 고르는 순수 함수 — status가 'suspended'면 정지 문구,
 * 아니면 호출부가 준 기존 문구(비소유/이미 삭제됨 등, 이 계층에서는 둘을 구분하지 않는다 — 아래
 * "이 검사가 안 보는 것" 참고) 그대로.
 */
export function writeRejectionMessage(status: ProfileStatus, fallback: string): string {
  return status === PROFILE_STATUS.SUSPENDED ? SUSPENDED_WRITE_MESSAGE : fallback;
}
