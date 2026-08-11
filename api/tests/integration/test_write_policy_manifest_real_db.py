"""쓰기 경로 전수조사 판정을 실행되는 검사로 (Story 17.2, DW-803).

왜 이 파일이 필요한가:
  17.1(`0032_suspended_write_block.sql` 9절)이 `pg_policies`·`pg_proc` 실측으로 정지 회원의
  쓰기 경로 전수(21개 정책 + 11개 SECURITY DEFINER 함수)에 "막는다/안 막는다 + 이유" 판정을
  붙였다. 그런데 그 판정은 마이그레이션 주석·`docs/conventions.md` §8·스펙 표 세 곳에 **산문**
  으로만 있었다 — 강제하는 실행 코드가 0건이었다(DW-803). 새 마이그레이션이 `authenticated`
  대상 non-SELECT 정책을 정지 조건 없이 추가해도 아무것도 red가 되지 않는 상태였다. 이 파일은
  그 판정을 **매니페스트(파이썬 딕셔너리)**로 옮기고, 실측 집합과 매니페스트 집합을 화이트리스트
  대조한다 — "정지 조건이 걸린 정책이 N개 이상"류의 하한 검사가 아니라 **양방향 차집합이 모두
  비어야 통과**하는 형태다(하한 검사는 새 정책이 추가돼도 계속 통과하므로 이 항목의 요구를
  충족하지 못한다).

정본은 어디인가:
  값의 정본은 `docs/conventions.md` §8이다(project-context 규칙 1 — "값은 한쪽에만 산다").
  이 매니페스트·`0032` 9절 주석은 그 판정을 각자의 자리(기계가 읽는 형태 / self-contained
  마이그레이션)로 옮긴 사본이다. 세 곳의 항목 집합이 어긋나면 그 자체가 결함이고, 그 어긋남은
  사람이 눈으로 대조한다(Verification 참조) — 이 자동 검사는 "실측 DB ↔ 이 파일의 매니페스트"
  축만 본다.

왜 pytest(`api/tests/integration`)에 두고 `scripts/check_migrations.py`의 `PROBES`에 안 넣나:
  `PROBES`는 `(라벨, 단일쿼리, 기대문자열)` 3튜플이다 — "쿼리 결과가 이 문자열과 같다/다르다"
  형태만 표현할 수 있고, **두 집합의 화이트리스트 대조**(양방향 차집합)는 이 구조로 표현할 수
  없다. 억지로 넣으려면 3튜플 구조 자체를 바꿔야 하는데, 그건 이 스토리가 받은 범위(함수 하나 +
  검사 하나) 밖이다 — 구조를 바꾸는 판단은 다음 사람의 몫으로 남긴다. 반대로 `check_migrations.py`
  가 나은 상황도 있다: 이 검사는 pgvector 컨테이너(`api-db` CI 잡)가 있어야 도는데, `check_
  migrations.py`는 매 push마다 도커 하나로 도는 정적+동적 게이트라 **더 이른 단계**에서 실패를
  보여준다. "언제 실패를 보고 싶은가"가 다르면 두 장치가 상호 배제가 아니라 상호보완이다.

이 검사가 **안 보는 것** (추측이 아니라 실측/설계로 확인한 것):
  · **`cmd <> 'SELECT'`이고 `roles`에 `authenticated`나 `public`이 포함된 정책만 본다**
    (`public`도 포함하는 이유: `TO` 절 없이 만든 정책은 Postgres가 `roles={public}`으로 기본
    배정하는데, `authenticated`도 `public`의 일원이라 여전히 걸린다 — 2026-08-11 코드리뷰가
    `'authenticated' = any(roles)` 단독 검사로는 이 형태의 정책이 실측에도 안 잡힌다는 것을
    지적해 넓혔다). `anon`·`ai_readonly` **전용**(그 롤만 대상이고 `authenticated`·`public` 둘
    다 아닌) 쓰기 정책이 생기면 이 검사는 그 정책의 존재조차 모른다 — 매니페스트에도, 실측
    쿼리에도 안 걸린다. 지금은 그런 정책이 0건이라 공백이 드러나지 않을 뿐이다.
  · **정책·함수 정의문의 문자열 검사(아래 검사 ②)는 약하다.** `is_admin_active`/`status =
    'active'`/`status = 'suspended'` 마커가 정의문 어디에든 있으면 통과로 본다 —
    `docs/conventions.md` §6이 이미 기록한 함정과 같다: 조건을 `(status='on_sale' OR true)`처럼
    무력화해도 마커 문자열만 남아 있으면 이 검사는 계속 초록이다. **행위 검사(정지 세션으로 실제
    쓰기를 시도하는 `test_suspended_write_block_real_db.py`)가 본체이고, 이 검사는 "판정 자체가
    누락됐는가"만 잡는 보조 장치다.**
  · **함수 매니페스트는 `proname`(함수 이름)만 키로 쓴다** — 스펙 Always 절이 지정한 실측 쿼리
    (`select p.proname from pg_proc ...`)가 이름만 반환하기 때문이다. 같은 이름의 오버로드가
    생기면(현재 0건, 실측 확인) 이 검사는 그 둘을 구별하지 못한다.
  · **함수 매니페스트(`_fetch_functions`)는 `public` 스키마만 본다** — 다른 스키마(예: `storage`)의
    SECURITY DEFINER 함수는 대상이 아니다(실측 쿼리가 `n.nspname='public'`으로 명시 한정).
    **정책 매니페스트(`_fetch_policies`)는 스키마 제한이 없다** — `storage.objects`의 4개 정책도
    포함해서 본다. 이 둘을 섞어 "이 파일 전체가 public 스키마만 본다"로 읽지 않는다.
  · **GRANT(누가 이 함수를 실행할 수 있는지)는 보지 않는다.** `prosecdef`(SECURITY DEFINER
    여부)만 본다 — `anon`에게 EXECUTE가 있는지 없는지는 이 검사의 판단에 들어가지 않는다.
  · **원격(prod) Supabase의 정책·함수 집합이 로컬과 동일한지는 검증하지 않는다** — 이 파일은
    `TEST_DATABASE_URL`이 가리키는 DB(로컬 55322 또는 CI `api-db` 컨테이너) 하나만 본다.

실행: `cd api && pytest tests/integration/test_write_policy_manifest_real_db.py -q`
  `TEST_DATABASE_URL` 미설정 시 skip(conftest의 `pytestmark`, 거짓 통과 아님).
"""

import psycopg
import pytest

from conftest import _DSN, pytestmark  # noqa: F401

# ── 매니페스트 — docs/conventions.md §8 · 0032 9절의 판정을 기계가 읽는 형태로 옮긴 사본 ──────
# 값은 리터럴로 박는다(메모리 self-consistent-assertions-never-fail) — DB에서 값을 다시 읽어
# 기대값을 만들면 무엇을 넣어도 green이 된다.
#
# 키: (schemaname, tablename, policyname, cmd) — 스펙 Always 절이 지정한 실측 쿼리와 동일한 컬럼.
# 값: (judgment, reason) — judgment는 "blocked"/"exempt" 둘뿐이다.
POLICY_MANIFEST = {
    # ── 막는다(16) — 0032 1~7절이 정지 조건을 새로 걸거나 이미 걸려 있던 것 ──────────────────
    ("public", "listings", "listings_insert_own", "INSERT"): (
        "blocked",
        "본인 매물 등록 — 0032가 profiles.status='active' 조건 추가",
    ),
    ("public", "listings", "listings_update_own", "UPDATE"): (
        "blocked",
        "본인 매물 수정 — using에만 정지 조건(0015 sold-전환 비대칭 보존)",
    ),
    ("public", "listings", "listings_delete_own", "DELETE"): (
        "blocked",
        "본인 매물 삭제 — 0032가 정지 조건 추가",
    ),
    ("public", "listing_images", "listing_images_insert_own", "INSERT"): (
        "blocked",
        "본인 매물 사진 추가 — 0031 sold 차단 + 0032 정지 조건",
    ),
    ("public", "listing_images", "listing_images_update_own", "UPDATE"): (
        "blocked",
        "본인 매물 사진 수정 — 위와 동일",
    ),
    ("public", "listing_images", "listing_images_delete_own", "DELETE"): (
        "blocked",
        "본인 매물 사진 삭제 — 위와 동일",
    ),
    ("storage", "objects", "listing_images_objects_owner_insert", "INSERT"): (
        "blocked",
        "본인 사진 파일 업로드 — 경로 소유권 + 정지 조건 + sold 차단(DW-782)",
    ),
    ("storage", "objects", "listing_images_objects_owner_update", "UPDATE"): (
        "blocked",
        "본인 사진 파일 수정 — 위와 동일",
    ),
    ("storage", "objects", "listing_images_objects_owner_delete", "DELETE"): (
        "blocked",
        "본인 사진 파일 삭제 — 정지 조건 + sold 부정형 차단(고아 정리 허용)",
    ),
    ("public", "listings", "listings_delete_admin", "DELETE"): (
        "blocked",
        "관리자의 남의 매물 삭제 — is_admin() → is_admin_active()",
    ),
    ("public", "profiles", "profiles_update_admin", "UPDATE"): (
        "blocked",
        "관리자의 profiles 수정 — is_admin_active()",
    ),
    ("public", "profiles", "profiles_delete_admin", "DELETE"): (
        "blocked",
        "관리자의 profiles 삭제 — is_admin_active()",
    ),
    ("public", "chat_rooms", "chat_rooms_delete_admin", "DELETE"): (
        "blocked",
        "관리자의 채팅방 삭제 — is_admin_active()",
    ),
    ("public", "chat_messages", "chat_messages_delete_admin", "DELETE"): (
        "blocked",
        "관리자의 채팅 메시지 삭제 — is_admin_active()",
    ),
    ("storage", "objects", "listing_images_objects_admin_delete", "DELETE"): (
        "blocked",
        "관리자의 사진 파일 삭제 — is_admin_active()",
    ),
    ("public", "chat_messages", "chat_messages_insert_participant", "INSERT"): (
        "blocked",
        "채팅 발신 — 정지 발신자 차단 결정(스토리 17.1 Design Notes)",
    ),
    # ── 안 막는다(5) — 불변식 문장(매물·사진·파일·관리자 RPC·채팅 발신) 밖이라는 판단 ──────────
    ("public", "chat_rooms", "chat_rooms_insert_participant", "INSERT"): (
        "exempt",
        "채팅방 생성 — 발신만 결정 대상이었다(DW-799로 이월, 판단은 바뀌지 않음)",
    ),
    ("public", "wishlists", "wishlists_insert_own", "INSERT"): (
        "exempt",
        "찜 추가 — 본인만 보는 개인화 데이터, 타인에게 영향 없음(DW-801)",
    ),
    ("public", "wishlists", "wishlists_delete_own", "DELETE"): (
        "exempt",
        "찜 삭제 — 위와 동일(DW-801)",
    ),
    ("public", "chat_room_reads", "chat_room_reads_insert_participant", "INSERT"): (
        "exempt",
        "안읽음 커서 생성 — 본인 배지 계산에만 쓰임, 상대방에게 비노출(DW-802)",
    ),
    ("public", "chat_room_reads", "chat_room_reads_update_own", "UPDATE"): (
        "exempt",
        "안읽음 커서 갱신 — 위와 동일(DW-802)",
    ),
}

# 키: proname — 스펙 Always 절 실측 쿼리(`select p.proname from pg_proc ...`)와 동일 컬럼.
FUNCTION_MANIFEST = {
    # ── 막는다(3) ──────────────────────────────────────────────────────────────────────────
    "is_admin_active": (
        "blocked",
        "정지 판정 헬퍼 자체(Story 17.1 신설) — 관리자 쓰기 소비처 전부가 이 함수를 부른다",
    ),
    "admin_restore_sold_listing": (
        "blocked",
        "관리자 판매완료 되돌리기 RPC — is_admin() → is_admin_active()(DW-721)",
    ),
    "increment_listing_view": (
        "blocked",
        "조회수 증가 RPC — Story 17.2가 정지 가드 추가(DW-805, 0032 9절 판정을 뒤집음). "
        "비로그인(anon) 호출은 계속 통과(FR58)",
    ),
    # ── 전역 유지(1) — Always 3항: 전역으로 좁히지 않는다 ───────────────────────────────────
    "is_admin": (
        "exempt",
        "관리자 읽기 정책이 이 함수를 쓴다 — status를 넣으면 정지된 관리자의 열람까지 막힌다",
    ),
    # ── 해당 없음: 트리거 부산물(5) — 이미 정지 조건이 걸린 INSERT가 성공해야만 호출된다 ──────
    "chat_messages_broadcast": (
        "exempt",
        "chat_messages INSERT AFTER 트리거 — INSERT 자체가 이미 정지 조건으로 막힘",
    ),
    "chat_rooms_touch_last_message": (
        "exempt",
        "chat_messages INSERT 트리거 — 위와 동일 경로",
    ),
    "enforce_chat_room_seller": (
        "exempt",
        "chat_rooms INSERT 트리거 — chat_rooms INSERT 자체는 정지 무관(DW-799)이라 정지 회원이 "
        "만든 방에서도 돈다. 위조 방지 로직일 뿐 정지 여부와 무관",
    ),
    "set_chat_room_names": (
        "exempt",
        "chat_rooms INSERT 트리거 — 위와 동일",
    ),
    "set_listing_seller_name": (
        "exempt",
        "listings INSERT 트리거 — listings INSERT 자체가 이미 막히므로 정지 경로에서 안 불림",
    ),
    # ── 해당 없음: 가입 트리거(1) ────────────────────────────────────────────────────────────
    "handle_new_user": (
        "exempt",
        "auth.users INSERT 트리거 — 아직 존재하지 않는 사용자를 다룸, 정지 전제가 성립하지 않음",
    ),
    # ── 해당 없음: 읽기 전용(1) ──────────────────────────────────────────────────────────────
    "get_seller_public_summary": (
        "exempt",
        "판매자 공개 요약 조회 — 쓰기가 아니다(§6이 이미 문서화)",
    ),
}

# 검사 ②(보조, 약함)가 찾는 마커 — 위 헤더 docstring이 이 검사의 한계를 설명한다.
_SUSPENDED_MARKERS = ("is_admin_active", "status = 'active'", "status = 'suspended'")


@pytest.fixture
def db():
    with psycopg.connect(_DSN) as conn:
        with conn.cursor() as c:
            yield c
        conn.rollback()


def _fetch_policies(cur):
    """스펙 Always 절이 지정한 실측 쿼리(0032 9절이 쓴 것)를 **역할 축으로 넓힌 버전** —
    2026-08-11 코드리뷰(adversarial) 지적: `TO authenticated` 없이 만든 정책은 Postgres가
    `roles = {public}`로 배정하는데, `public` 역할은 `authenticated` 세션에도 그대로 적용된다.
    원본 쿼리(`'authenticated' = any(roles)`)는 그 문자열을 리터럴로만 찾으므로 그런 정책을
    영영 못 본다 — DW-803이 막으려는 바로 그 실패 모드(정지 게이트 판정 없는 새 authenticated
    쓰기 경로)가 한 단계 위에서 재현되는 셈이다. 지금은 그런 정책이 0건이라(실측 확인) 잠복
    상태지만, 검사가 스스로 못 보는 사각지대를 남겨 두지 않는다."""
    cur.execute(
        "select schemaname, tablename, policyname, cmd, qual, with_check "
        "from pg_policies where cmd <> 'SELECT' "
        "and (roles && '{authenticated,public}'::name[])"
    )
    return {(r[0], r[1], r[2], r[3]): (r[4] or "", r[5] or "") for r in cur.fetchall()}


def _fetch_functions(cur):
    """스펙 Always 절이 지정한 실측 쿼리 — 0032 9절이 쓴 것과 동일."""
    cur.execute(
        "select p.proname, p.oid from pg_proc p "
        "join pg_namespace n on n.oid = p.pronamespace "
        "where p.prosecdef and n.nspname = 'public'"
    )
    return {r[0]: r[1] for r in cur.fetchall()}


# ── 검사 ① — 실측 집합과 매니페스트 키 집합이 정확히 일치(양방향 차집합 모두 비어야 한다) ──────


def test_policy_manifest_matches_pg_policies_exactly(db):
    measured = set(_fetch_policies(db).keys())
    manifest = set(POLICY_MANIFEST.keys())

    new_unjudged = measured - manifest
    assert not new_unjudged, (
        f"새 쓰기 경로에 판정이 없다 — pg_policies 실측에는 있는데 매니페스트에 없음: {sorted(new_unjudged)}"
    )

    stale = manifest - measured
    assert not stale, (
        f"지워진 정책이 매니페스트에 남았다 — 매니페스트에는 있는데 pg_policies 실측에 없음: {sorted(stale)}"
    )


def test_function_manifest_matches_pg_proc_exactly(db):
    measured = set(_fetch_functions(db).keys())
    manifest = set(FUNCTION_MANIFEST.keys())

    new_unjudged = measured - manifest
    assert not new_unjudged, (
        f"새 SECURITY DEFINER 함수에 판정이 없다 — pg_proc 실측에는 있는데 매니페스트에 없음: {sorted(new_unjudged)}"
    )

    stale = manifest - measured
    assert not stale, (
        f"지워진 함수가 매니페스트에 남았다 — 매니페스트에는 있는데 pg_proc 실측에 없음: {sorted(stale)}"
    )


# ── 검사 ② — blocked 항목의 정의문에 정지 판정 마커가 실제로 있는지(보조, 약함 — 헤더 참조) ────


def test_blocked_policies_carry_suspended_predicate(db):
    measured = _fetch_policies(db)
    for key, (judgment, _reason) in POLICY_MANIFEST.items():
        if judgment != "blocked":
            continue
        assert key in measured, f"{key}가 blocked인데 실측에 없다(검사 ①이 먼저 잡아야 하는 상태)"
        qual, with_check = measured[key]
        combined = f"{qual} {with_check}"
        assert any(marker in combined for marker in _SUSPENDED_MARKERS), (
            f"{key}가 blocked로 표시됐지만 정의문에 정지 판정 마커가 없다: {combined!r}"
        )


def test_blocked_functions_carry_suspended_predicate(db):
    functions = _fetch_functions(db)
    for name, (judgment, _reason) in FUNCTION_MANIFEST.items():
        if judgment != "blocked":
            continue
        assert name in functions, f"{name}이 blocked인데 실측에 없다(검사 ①이 먼저 잡아야 하는 상태)"
        db.execute("select pg_get_functiondef(%s)", (functions[name],))
        functiondef = db.fetchone()[0]
        assert any(marker in functiondef for marker in _SUSPENDED_MARKERS), (
            f"{name}이 blocked로 표시됐지만 함수 정의에 정지 판정 마커가 없다: {functiondef!r}"
        )
