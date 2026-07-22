#!/usr/bin/env bash
# scripts/seed-local.sh — 운영(prod) Supabase 데이터를 로컬 Supabase 스택에 복사한다.
#
# 언제 쓰나: `supabase db reset` 뒤(마이그레이션만 재적용되고 데이터는 비어 있을 때) 이 스크립트로
#   데모 계정 9개 + 매물/사진/채팅/가이드 문서 + 사진 파일을 다시 채운다.
#
# 무엇을 하나 (3단계):
#   1) supabase/seed-local/01_accounts.sql — 운영과 "같은 UUID"로 데모 계정 9개 생성
#   2) supabase/seed-local/02_data.sql     — supabase/seed-local/data/*.json(운영 스냅샷)을 그대로 적재
#      (listings→listing_images→chat_rooms→chat_messages→guide_documents 순, embedding 컬럼은 비움)
#   3) storage.objects — data/storage_objects.json에 적힌 경로들을 운영 공개 버킷에서 내려받아
#      로컬 버킷에 올린다(캐시 재사용 가능)
#
# 전제: 로컬 Supabase 스택이 떠 있고(마이그레이션 적용 완료), listing-images 버킷이 존재해야 한다.
#   (마이그레이션 0012~0014가 만든다 — 이 스크립트는 스키마를 건드리지 않는다.)
#
# 비밀번호: supabase/.env.seed 의 SEED_PASSWORD를 읽는다(파일은 .gitignore 처리됨, 평문을 이 스크립트에
#   박지 않는다). 없으면 즉시 중단한다.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SEED_LOCAL_DIR="$REPO_ROOT/supabase/seed-local"
ENV_SEED_FILE="$REPO_ROOT/supabase/.env.seed"

# ── 접속 정보 (환경변수로 덮어쓸 수 있음 — 기본값은 이 프로젝트 로컬 스택 고정값) ──────
LOCAL_DB_URL="${LOCAL_DB_URL:-postgresql://postgres:postgres@127.0.0.1:55322/postgres}"
LOCAL_API_URL="${LOCAL_API_URL:-http://127.0.0.1:55321}"
# 로컬 스택 전용 고정 개발 키(운영 시크릿이 아니다 — `supabase status`가 로컬 JWT 시크릿으로부터
# 결정적으로 계산해내는 값. postgres:postgres DB 비번과 같은 성격의 "로컬 전용 알려진 값"이다).
# 스토리지 REST API에 apikey + Authorization 두 헤더 모두 필요하다(실측: 하나만 주면 403).
LOCAL_STORAGE_SECRET_KEY="${LOCAL_STORAGE_SECRET_KEY:-sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz}"
# 운영 프로젝트의 공개 URL(사진은 listing-images 버킷이 public이라 인증 없이 GET 가능).
PROD_PROJECT_URL="${PROD_PROJECT_URL:-https://psrnsasxpkpwqdukjdmt.supabase.co}"

echo "[seed-local] 1/3 계정 9개 준비 중..."

if [ ! -f "$ENV_SEED_FILE" ]; then
  echo "[seed-local] 오류: $ENV_SEED_FILE 이 없습니다. supabase/seed-secret.example 을 복사해 채우세요." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_SEED_FILE"
if [ -z "${SEED_PASSWORD:-}" ]; then
  echo "[seed-local] 오류: SEED_PASSWORD가 비어 있습니다 ($ENV_SEED_FILE)." >&2
  exit 1
fi

psql "$LOCAL_DB_URL" \
  -v seed_password="$SEED_PASSWORD" \
  -v ON_ERROR_STOP=1 \
  -f - <<PSQLEOF
SET app.seed_password = :'seed_password';
\i $SEED_LOCAL_DIR/01_accounts.sql
PSQLEOF

echo "[seed-local] 2/3 업무 데이터(매물·사진메타·채팅·가이드) 적재 중..."
psql "$LOCAL_DB_URL" \
  -v seed_local_dir="$SEED_LOCAL_DIR" \
  -v ON_ERROR_STOP=1 \
  -f "$SEED_LOCAL_DIR/02_data.sql"

echo "[seed-local] 2b/3 신뢰속성 데모값(Story 10.2, 멱등 UPDATE) 적용 중..."
psql "$LOCAL_DB_URL" \
  -v ON_ERROR_STOP=1 \
  -f "$SEED_LOCAL_DIR/03_trust_demo.sql"

echo "[seed-local] 3/3 사진 파일 복사 중 (운영 공개 버킷 → 로컬 버킷)..."

# 로컬에 버킷이 있는지 먼저 확인(마이그레이션 0012~0014가 만들었어야 한다). 없으면 중단.
bucket_exists=$(psql "$LOCAL_DB_URL" -tAc "select count(*) from storage.buckets where id='listing-images';")
if [ "$bucket_exists" != "1" ]; then
  echo "[seed-local] 오류: 로컬에 listing-images 버킷이 없습니다. 마이그레이션이 적용됐는지 확인하세요." >&2
  exit 1
fi

STORAGE_OBJECTS_JSON="$SEED_LOCAL_DIR/data/storage_objects.json"
CACHE_DIR="$REPO_ROOT/.seed-local-photo-cache"   # 재실행 시 재다운로드 생략용 캐시(.gitignore 대상)
mkdir -p "$CACHE_DIR"

ok=0
fail=0
fail_list=()

while IFS= read -r name; do
  local_file="$CACHE_DIR/$name"
  mkdir -p "$(dirname "$local_file")"
  ext="${name##*.}"
  if [ "$ext" = "webp" ]; then content_type="image/webp"; else content_type="application/octet-stream"; fi

  # 1) 운영 공개 URL에서 다운로드 (캐시에 **내용이 있으면** 재사용)
  #    ⚠️ `-f`(존재)가 아니라 `-s`(비어있지 않음)로 판단해야 한다. 다운로드가 중간에 끊기면
  #    0바이트 파일이 캐시에 남는데, 존재만 보면 그걸 정상으로 여겨 **0바이트를 그대로 업로드**하고
  #    "성공"으로 세어버린다(실측으로 재현함 — 사진이 0바이트로 서빙되는데 실패 0건으로 보고됐다).
  if [ ! -s "$local_file" ]; then
    dl_code=$(curl -s -o "$local_file" -w "%{http_code}" \
      "$PROD_PROJECT_URL/storage/v1/object/public/listing-images/$name")
    if [ "$dl_code" != "200" ]; then
      fail=$((fail + 1))
      fail_list+=("DOWNLOAD_FAIL($dl_code) $name")
      continue
    fi
    # 200인데 0바이트인 경우도 실패로 본다 — 단 `.emptyFolderPlaceholder`는 원래 0바이트다.
    if [ ! -s "$local_file" ] && [[ "$name" != *".emptyFolderPlaceholder" ]]; then
      fail=$((fail + 1))
      fail_list+=("EMPTY_DOWNLOAD $name")
      continue
    fi
  fi

  # 2) 로컬 버킷에 업로드 (x-upsert:true → 재실행해도 안전)
  resp_file="$(mktemp)"
  up_code=$(curl -s -o "$resp_file" -w "%{http_code}" -X POST \
    "$LOCAL_API_URL/storage/v1/object/listing-images/$name" \
    -H "apikey: $LOCAL_STORAGE_SECRET_KEY" \
    -H "Authorization: Bearer $LOCAL_STORAGE_SECRET_KEY" \
    -H "Content-Type: $content_type" \
    -H "x-upsert: true" \
    --data-binary @"$local_file")
  if [ "$up_code" = "200" ] || [ "$up_code" = "201" ]; then
    ok=$((ok + 1))
  else
    fail=$((fail + 1))
    fail_list+=("UPLOAD_FAIL($up_code) $name $(cat "$resp_file")")
  fi
  rm -f "$resp_file"
done < <(python3 -c "import json,sys; [print(o['name']) for o in json.load(open('$STORAGE_OBJECTS_JSON'))]")

echo "[seed-local] 사진 복사 결과: 성공 $ok / 실패 $fail"
if [ "$fail" -gt 0 ]; then
  echo "[seed-local] 실패 목록:"
  printf '  %s\n' "${fail_list[@]}"
fi

# ── 4/4 임베딩 재생성 (선택) ────────────────────────────────────────────────
# 운영 스냅샷에는 embedding(768차원 벡터)이 들어 있지 않다 — 행당 9.5KB라 스냅샷에서 뺐다.
# 대신 여기서 "다시 만든다". 원본을 옮기는 게 아니라 매물 정보를 Gemini에 보내 새로 계산하므로
# 결과는 운영과 값이 같지는 않지만 의미검색 품질은 동등하다.
# 키가 없으면 조용히 넘어가지 않고 "무엇이 빠졌는지" 알린다(AI 검색만 안 되고 나머지는 정상).
echo "[seed-local] 4/4 임베딩 생성 중(가능하면)..."

API_VENV="$REPO_ROOT/api/.venv/bin/python"
if [ ! -x "$API_VENV" ]; then
  echo "[seed-local] ⏭  건너뜀: api/.venv 가 없습니다. AI 의미검색(/ai)은 로컬에서 동작하지 않습니다."
elif ! grep -qE "^GEMINI_API_KEY=.+" "$REPO_ROOT/api/.env" 2>/dev/null; then
  echo "[seed-local] ⏭  건너뜀: api/.env 에 GEMINI_API_KEY 가 없습니다. AI 의미검색(/ai)은 로컬에서 동작하지 않습니다."
  echo "[seed-local]    채우려면: api/.env 에 키를 넣고 아래를 실행"
  echo "[seed-local]    DATABASE_URL=\"$LOCAL_DB_URL\" api/.venv/bin/python api/scripts/backfill_embeddings.py"
else
  # DATABASE_URL 은 OS 환경변수로 넘긴다 — pydantic-settings 에서 OS 변수가 api/.env 파일값을
  # 이깁니다(실측 확인). 즉 api/.env 에 운영 DB 주소가 들어 있어도 로컬로 강제된다.
  ( cd "$REPO_ROOT/api" && DATABASE_URL="$LOCAL_DB_URL" "$API_VENV" scripts/backfill_embeddings.py ) \
    || echo "[seed-local] ⚠️  임베딩 생성 실패 — 키 만료·할당량 등을 확인하세요. 나머지 데이터는 정상입니다."
fi

echo "[seed-local] 완료. 검증: psql \"$LOCAL_DB_URL\" 에서 각 테이블 count를 운영과 대조하세요."
