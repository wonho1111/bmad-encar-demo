#!/usr/bin/env bash
# scripts/dev-reranker.sh — 리랭커(크로스인코더) 사이드카를 로컬에 띄운다.
#
# 언제 쓰나: api가 리랭킹(4단계 부품 A)까지 붙여 로컬에서 테스트하고 싶을 때. 이걸 안 띄우면
#   api/.env의 RERANKER_URL이 비어 있는 것과 같아서 app/rerank_client.py가 항상 None을
#   돌려주고 호출부는 기존 순서를 그대로 쓴다(회귀 아님 — 선택 기능이 조용히 꺼질 뿐).
#
# 왜 api/.venv가 아니라 별도 venv(~/bench/venv-rr)로 띄우나: sentence-transformers(torch
#   의존)를 api venv에 넣으면 시세 진단 엔진(tabpfn)과 충돌한다(실측, api/pyproject.toml
#   market 그룹 주석 참조). venv-rr은 이미 torch(GPU)+sentence-transformers가 설치돼 있고
#   HF 모델도 캐시돼 있다(~/.cache/huggingface, 재다운로드 없음).
#
# 전제: ~/bench/venv-rr 가 존재하고 fastapi·uvicorn·sentence-transformers가 설치돼 있어야
#   한다(uv pip install --python ~/bench/venv-rr/bin/python <pkg> 로 추가).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_RR="${VENV_RR:-$HOME/bench/venv-rr}"

RERANKER_PORT="${RERANKER_PORT:-8801}"
RERANKER_DEVICE="${RERANKER_DEVICE:-cuda}"

if [ ! -x "$VENV_RR/bin/python" ]; then
  echo "[dev-reranker] 오류: $VENV_RR 가 없습니다. venv-rr을 먼저 준비하세요." >&2
  exit 1
fi

export RERANKER_PORT
export RERANKER_DEVICE

echo "[dev-reranker] 리랭커 사이드카를 :$RERANKER_PORT 에 device=$RERANKER_DEVICE 로 띄웁니다(모델 로드에 10초 이상 걸릴 수 있음)."
echo "[dev-reranker]   api가 이걸 쓰려면 api/.env 에 RERANKER_URL=http://127.0.0.1:$RERANKER_PORT"
exec "$VENV_RR/bin/python" "$REPO_ROOT/api/reranker_service.py"
