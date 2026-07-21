#!/usr/bin/env bash
# scripts/use-env.sh — 웹·앱의 접속 설정을 "로컬 DB용"과 "운영 DB용" 사이에서 갈아끼운다.
#
# 왜 필요한가: 자동 개발 루프가 운영 DB를 건드리지 않도록 로컬 Supabase 스택을 세웠는데,
#   웹·앱은 환경변수에 적힌 주소를 볼 뿐이라 그 파일을 바꿔주지 않으면 계속 운영을 본다.
#   그리고 그 파일들(.env*)은 git이 추적하지 않아 **브랜치를 바꿔도 저절로 바뀌지 않는다.**
#   그래서 갈아끼우는 행위를 스크립트로 만들고, .githooks/post-checkout 이 자동 호출한다.
#
# 사용법:
#   bash scripts/use-env.sh local   # 로컬 Supabase 스택(127.0.0.1:55321)을 보게 한다
#   bash scripts/use-env.sh prod    # 운영 Supabase를 보게 한다
#   bash scripts/use-env.sh auto    # 현재 git 브랜치를 보고 알아서 고른다(훅이 쓰는 모드)
#
# 브랜치 규칙(auto): main·develop 은 운영, **나머지 전부 로컬**.
#   develop을 운영에 둔 이유(사용자 결정 2026-07-21): develop은 Vercel 프리뷰로 배포되고
#   그 배포본은 어차피 운영 DB를 본다. 로컬에서만 다른 DB를 보면 "내 화면에선 되는데
#   배포하면 다르다"가 생긴다. 로컬 DB는 자동 개발 루프 전용(test/* 등)으로 좁힌다.
#   모르는 브랜치는 로컬로 보낸다 — 실수의 방향을 싼 쪽으로 기울인다.
#
# 값이 담긴 파일(전부 .gitignore 대상 — 이 스크립트에는 값이 없다):
#   web/.env.dev  → web/.env.local      web/.env.prod  → web/.env.local
#   app/.env.json.dev → app/.env.json   app/.env.json.prod → app/.env.json

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

MODE="${1:-auto}"

if [ "$MODE" = "auto" ]; then
  branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  case "$branch" in
    main|develop) MODE="prod" ;;
    *)            MODE="local" ;;
  esac
fi

case "$MODE" in
  local) suffix="dev" ;;
  prod)  suffix="prod" ;;
  *) echo "[use-env] 사용법: $0 {local|prod|auto}" >&2; exit 1 ;;
esac

changed=0

apply() {  # apply <원본> <대상>
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then
    echo "[use-env] 건너뜀: $src 이 없습니다(이 환경에서는 준비되지 않은 설정)." >&2
    return
  fi
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    return  # 이미 같은 내용 — 조용히 넘어간다(체크아웃마다 시끄럽지 않게)
  fi
  cp "$src" "$dst"
  changed=1
}

apply "web/.env.$suffix"      "web/.env.local"
apply "app/.env.json.$suffix" "app/.env.json"

if [ "$changed" = "1" ]; then
  if [ "$MODE" = "prod" ]; then
    echo "[use-env] ⚠️  운영 DB를 보도록 전환했습니다 (web/.env.local · app/.env.json)."
  else
    echo "[use-env] 로컬 Supabase 스택(127.0.0.1:55321)을 보도록 전환했습니다."
    echo "[use-env]   스택이 안 떠 있으면: npx supabase start · 데이터가 비었으면: bash scripts/seed-local.sh"
  fi
fi
