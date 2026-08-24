#!/usr/bin/env bash
# check_env_integrity.sh — verify 게이트의 **첫 관문**: "이 환경이 아직 성한가"
#
# 왜 있나 (Epic 12 회고 액션 B3, 사용자 결정 2026-07-29 = (b)안):
#   무인 루프의 세션들이 **자기 실행 환경을 망가뜨린 사고가 이 에픽에만 두 번** 났다.
#     · #191 — 리뷰 세션이 `pip uninstall -y websockets` 하고 되돌리지 않음. websockets는
#       langsmith·realtime·langgraph-sdk·google-genai·langgraph-api 5개가 요구하는 전이
#       의존성이라, langgraph import 체인이 죽어 **api 테스트 11파일이 수집 단계에서 전멸**했다.
#       그게 verify 게이트의 첫 명령이라 **그 시점 이후 모든 스토리가 코드와 무관하게 막히고**,
#       rollback_on_failure=true라 자동 롤백·이월됐다 — 멀쩡한 12-2가 그렇게 이월됐다.
#     · #211 — 로컬 Supabase 컨테이너의 anon/authenticated 기본 테이블 권한이 통째로 빠져
#       **전 기능이 42501(permission denied)로 죽어 있었다.** `supabase db reset`은 마이그레이션
#       재생 방식이라 이 컨테이너 레벨 기본값을 복구하지 못해, 되돌린 뒤에도 깨진 채였다.
#
#   기존 규칙은 *"검증용 **데이터**는 넣었으면 반드시 원복한다"* 뿐이라 **데이터에만** 걸려 있었고
#   패키지·권한 같은 실행 환경에는 같은 규칙이 없었다. 문서에 한 줄 더 쓰는 (a)안 대신
#   **실행되는 검사**로 만든 이유는 CLAUDE.md B9 — *"주석·문서는 계약이 아니다. 지켜야 하는
#   규칙이면 실행되는 검사로 바꾼다. 안 바꾸면 아무도 실행하지 않는다."*
#
#   이 검사가 고치는 것은 오염 자체가 아니라 **오진**이다. 오염되면 지금까지는 "테스트 11개 실패"로
#   보여 스토리 코드를 의심하게 됐다. 앞으로는 여기서 먼저 멈추고 **환경이 원인이라고 이름을 대준다.**
#
# 이 검사가 **안 보는 것**(추측이 아니라 실측/설계로 갈라둔 것):
#   · 오염을 **막지** 못한다. 세션이 패키지를 지우는 것 자체는 여전히 가능하고, 이 검사는
#     그 다음 스토리에서 알아챌 뿐이다. 같은 세션 안에서 지웠다 그 세션이 끝나기 전이면 못 잡는다.
#   · **원격 DB는 안 본다.** 여기서 보는 건 로컬 스택뿐이다(무인 루프는 test/* 브랜치에서 돌아
#     로컬을 본다). 원격 권한이 바뀐 것은 이 검사로 안 잡힌다.
#   · 로컬 스택이 **꺼져 있으면 권한 축을 건너뛴다**(아래 SKIP). 즉 "초록"이 "권한이 성하다"를
#     뜻하지 않는 경우가 있다 — 그래서 건너뛸 땐 반드시 소리내어 출력한다(조용한 통과 금지).
#     스택 부재를 실패로 하지 않는 이유는 `check_migrations.py`를 verify에서 뺀 것과 같다:
#     도커가 꺼졌다고 멀쩡한 스토리를 전부 막으면 게이트가 통째로 무시된다.
#
# 종료코드: 통과 0 / 위반 1.

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# 테스트 가능하게 뚫어둔 구멍(이 검사의 red를 실제로 확인하려면 필요하다 — CLAUDE.md B4
# "만들었다가 아니라 잡는다가 완료다"). 평소에는 건드리지 않는다.
API_VENV_PY="${API_VENV_PY:-$REPO_ROOT/api/.venv/bin/python}"
DB_CONTAINER="${DB_CONTAINER:-supabase_db_bmad-encar-demo}"

failed=0
fail() { echo "[환경오염] $*" >&2; failed=1; }

# ── ① 파이썬 의존성 정합성 ────────────────────────────────────────────────
# `pip check`는 "설치된 패키지가 요구하는 것이 실제로 설치돼 있나"를 본다. #191의
# `pip uninstall websockets`가 정확히 이 축에서 걸린다(5개 패키지가 요구하는데 없음).
if [ ! -x "$API_VENV_PY" ]; then
  fail "api 가상환경이 없다: $API_VENV_PY — 'cd api && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt'"
else
  if ! pip_out="$("$API_VENV_PY" -m pip check 2>&1)"; then
    fail "pip 의존성이 깨져 있다 — 누군가 패키지를 지우고 되돌리지 않았다:"
    echo "$pip_out" | sed 's/^/    /' >&2
  else
    echo "[ok] pip 의존성 정합성 — $pip_out"
  fi

  # `pip check`는 메타데이터만 본다. 실제로 import 체인이 서는지는 별개 축이라 한 번 세워본다
  # (#191에서 죽은 것이 바로 이 체인이고, 그때 pytest 11파일이 수집 단계에서 전멸했다).
  if ! imp_err="$("$API_VENV_PY" -c 'import langgraph, websockets' 2>&1)"; then
    fail "핵심 import 체인이 서지 않는다(langgraph/websockets):"
    echo "$imp_err" | tail -3 | sed 's/^/    /' >&2
  else
    echo "[ok] import 체인 — langgraph·websockets"
  fi
fi

# ── ② 로컬 DB 권한 스모크 ────────────────────────────────────────────────
# #211은 "권한이 있는데 정책이 없다"가 아니라 **권한 자체가 사라진** 사고였다. 그래서 두 방향을
# 같이 본다 — CLAUDE.md B9 *"권한만 주고 정책이 없으면 다 보이고, 정책만 있고 권한이 없으면
# 아무것도 안 보인다. 둘 다 확인한다."*
#   허용 축: 있어야 하는 권한이 있나 (없으면 전 기능이 42501로 죽는다 — #211의 증상)
#   차단 축: 마이그레이션이 좁혀둔 것이 아직 좁혀져 있나 (넓어졌으면 하드닝이 되돌아간 것)
# 단언값은 2026-07-29 로컬 스택에서 **실측한 현재 상태**다(추측 아님). anon을 테이블 단위가
# 아니라 **컬럼 단위**로 보는 이유: 0011이 anon을 컬럼 화이트리스트로 좁혀서
# has_table_privilege(anon,'listings','SELECT')는 정상 상태에서도 false다(실측하다 걸렸다).
if ! docker exec "$DB_CONTAINER" true >/dev/null 2>&1; then
  echo "[SKIP] 로컬 Supabase 스택($DB_CONTAINER)이 떠 있지 않아 권한 스모크를 건너뛴다."
  echo "       → 이 실행의 초록은 '권한이 성하다'를 뜻하지 않는다. 스택을 띄우려면 'npx supabase start'."
else
  perm_sql="
select
  case when has_table_privilege('authenticated','public.profiles','SELECT')      then '' else 'authenticated가 profiles를 못 읽는다; ' end ||
  case when has_table_privilege('authenticated','public.listings','SELECT')      then '' else 'authenticated가 listings를 못 읽는다; ' end ||
  case when has_table_privilege('authenticated','public.chat_rooms','SELECT')    then '' else 'authenticated가 chat_rooms를 못 읽는다; ' end ||
  case when has_table_privilege('authenticated','public.chat_messages','INSERT') then '' else 'authenticated가 chat_messages에 못 쓴다; ' end ||
  case when has_column_privilege('anon','public.listings','id','SELECT')         then '' else 'anon이 listings.id를 못 읽는다; ' end ||
  case when has_column_privilege('authenticated','public.listings','view_count','UPDATE')
       then '[하드닝 역행] authenticated가 listings.view_count를 UPDATE할 수 있다(0020이 막아둔 것); ' else '' end ||
  case when has_column_privilege('anon','public.listings','embedding','SELECT')
       then '[하드닝 역행] anon이 listings.embedding을 읽을 수 있다(0011이 막아둔 것); ' else '' end
  as problems;"
  if ! perm_out="$(docker exec -i "$DB_CONTAINER" psql -U postgres -d postgres -Atc "$perm_sql" 2>&1)"; then
    fail "로컬 DB 권한 조회에 실패했다(스택은 떠 있는데 psql이 안 된다):"
    echo "$perm_out" | tail -3 | sed 's/^/    /' >&2
  elif [ -n "$perm_out" ]; then
    fail "로컬 DB 권한이 기대와 다르다 — $perm_out"
    echo "    → #211과 같은 사고다. 복구법은 docs/tech-debt.md #211의 '조치' 문단 참조." >&2
  else
    echo "[ok] 로컬 DB 권한 스모크 — 허용 5축·차단 2축 전부 기대대로"
  fi
fi

if [ "$failed" -ne 0 ]; then
  echo "" >&2
  echo "=== 환경 무결성 검사 실패 — 스토리 코드의 문제가 아니다. 환경을 먼저 고칠 것 ===" >&2
  exit 1
fi
echo "=== 환경 무결성 검사 통과 ==="
