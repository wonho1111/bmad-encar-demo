#!/usr/bin/env bash
# scripts/dev-api.sh — AI 검색 백엔드(FastAPI)를 **로컬 스택에 붙여서** 띄운다.
#
# 언제 쓰나: 로컬에서 /ai(AI 검색) 화면까지 테스트하고 싶을 때.
#   웹의 매물·로그인·채팅·사진은 브라우저가 Supabase에 직접 붙으므로 이 서버가 필요 없다.
#   AI 검색만 이 서버를 거친다(브라우저 → FastAPI → Postgres 직결).
#
# 왜 api/.env 에 값을 넣지 않고 여기서 환경변수로 주나:
#   ① api/.env 에 운영 DB 주소를 두면 실수로 운영에 붙을 수 있다. 여기 값은 전부 로컬 고정값이라
#      이 스크립트로 띄우는 한 **운영에 닿을 수 없다**.
#   ② pydantic-settings 는 OS 환경변수를 .env 파일값보다 우선한다(실측 확인). 그래서
#      api/.env 에 무엇이 들어 있든 아래 값이 이긴다.
#   ③ GEMINI_API_KEY 만은 여기 두지 않는다 — 진짜 비밀값이라 api/.env(gitignore)에서 읽는다.
#
# 전제: 로컬 Supabase 스택이 떠 있어야 한다(npx supabase start).
#   임베딩이 비어 있으면 AI가 매물을 못 찾는다 → bash scripts/seed-local.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/api"

PORT="${PORT:-8000}"

if [ ! -x .venv/bin/python ]; then
  echo "[dev-api] 오류: api/.venv 가 없습니다. 파이썬 가상환경을 먼저 만드세요." >&2
  exit 1
fi
if ! grep -qE "^GEMINI_API_KEY=.+" .env 2>/dev/null; then
  echo "[dev-api] 오류: api/.env 에 GEMINI_API_KEY 가 없습니다. AI 검색은 이 키가 필요합니다." >&2
  exit 1
fi

# 로컬 스택 고정값(비밀 아님 — postgres:postgres 와 같은 성격의 알려진 개발용 값)
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:55322/postgres"
export SUPABASE_URL="http://127.0.0.1:55321"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
# 웹은 3000이 이미 쓰이면 3001로 뜬다. 둘 다 허용해야 CORS에서 막히지 않는다.
export CORS_ORIGINS="http://localhost:3000,http://localhost:3001"

echo "[dev-api] 로컬 DB(127.0.0.1:55322)에 붙여 AI 검색 서버를 :$PORT 에 띄웁니다."
echo "[dev-api]   웹이 이걸 쓰려면 web/.env.local 의 NEXT_PUBLIC_API_BASE_URL=http://localhost:$PORT"
exec .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT"
