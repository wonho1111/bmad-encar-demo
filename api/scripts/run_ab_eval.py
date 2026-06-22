"""Phase B 라이브 러너 — 질의셋을 실제 AI 그래프에 N회 흘려 raw 결과를 모은다(모델 1개).

하는 일:
  · settings.gemini_generation_model을 --model로 교체(앱 코드 변경 없이 런타임만 바꿈).
  · 각 질의를 contextualize_query → COMPILED_GRAPH.invoke 로 직접 실행해 route(A/B/C)·listings·answer 획득.
    (run_search는 route를 안 돌려줘서 그래프를 직접 부른다 — 채점에 route가 필요.)
  · 멀티턴은 context(직전 user/assistant 턴)를 누적해 턴마다 실행.
  · 토큰은 ChatGoogleGenerativeAI._generate 모니터패치로 호출마다 usage_metadata를 합산(비용 산정).
  · N=3 반복(flaky 탐지)해 raw JSON 저장: docs/ab-eval-raw-{model}.json.

채점은 하지 않는다(score_ab.py가 골든셋과 대조). 이 단계는 "수집"만.

실행:  api/ 에서
  .venv/Scripts/python.exe scripts/run_ab_eval.py --model gemini-3.1-flash-lite --runs 3
  .venv/Scripts/python.exe scripts/run_ab_eval.py --model gemini-2.5-flash-lite --runs 3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

from app.config import settings  # noqa: E402

# ── 토큰 집계 모니터패치 ────────────────────────────────────────────────
_TOK = {"in": 0, "out": 0, "calls": 0}


def _install_token_meter() -> None:
    """ChatGoogleGenerativeAI._generate를 감싸 호출마다 usage_metadata를 _TOK에 더한다.

    라우터(구조화 출력)·맥락화·SQL 생성 — 어느 경로로 불리든 _generate가 공통 길목이라
    한 번만 감싸면 전부 잡힌다. usage_metadata가 없으면 텍스트 길이로 대략 추정(과소평가 방지).
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    if getattr(ChatGoogleGenerativeAI, "_ab_metered", False):
        return
    orig = ChatGoogleGenerativeAI._generate

    def metered(self, messages, stop=None, run_manager=None, **kwargs):
        result = orig(self, messages, stop=stop, run_manager=run_manager, **kwargs)
        _TOK["calls"] += 1
        try:
            msg = result.generations[0].message
            um = getattr(msg, "usage_metadata", None)
            if um:
                _TOK["in"] += int(um.get("input_tokens", 0) or 0)
                _TOK["out"] += int(um.get("output_tokens", 0) or 0)
            else:  # 폴백 추정 — 입력 메시지·출력 텍스트 길이 / 4 (대략 토큰)
                in_txt = sum(len(str(getattr(m, "content", m))) for m in messages)
                out_txt = len(str(getattr(msg, "content", "")))
                _TOK["in"] += in_txt // 4
                _TOK["out"] += out_txt // 4
        except Exception:
            pass
        return result

    ChatGoogleGenerativeAI._generate = metered
    ChatGoogleGenerativeAI._ab_metered = True


def _snapshot_and_reset() -> tuple[int, int]:
    i, o = _TOK["in"], _TOK["out"]
    _TOK["in"] = _TOK["out"] = 0
    return i, o


# ── 그래프 1회 실행 ────────────────────────────────────────────────────
def run_once(query: str, context: list | None) -> dict:
    """그래프를 1회 실행해 route·ids·answer·지연·토큰을 모은다."""
    from app.graph.contextualize_node import contextualize_query
    from app.graph.graph import COMPILED_GRAPH

    eff = contextualize_query(query, context)
    if not (eff or "").strip():
        eff = query
    t0 = time.perf_counter()
    state = COMPILED_GRAPH.invoke({"query": eff})
    dt = (time.perf_counter() - t0) * 1000.0
    tin, tout = _snapshot_and_reset()
    ids = [c.id for c in state.get("listings", [])]
    return {
        "route": state.get("route"),
        "ids": ids,
        "answer": state.get("answer", ""),
        "latency_ms": dt,
        "tokens_in": tin,
        "tokens_out": tout,
    }


def run_item(item: dict) -> dict:
    """단일/멀티턴 항목 1회 실행분(여러 턴이면 턴 배열 포함)."""
    if item["kind"] == "single":
        r = run_once(item["query"], None)
        return {
            "route_last": r["route"], "ids_last": r["ids"], "answer_last": r["answer"],
            "latency_ms": r["latency_ms"], "tokens_in": r["tokens_in"], "tokens_out": r["tokens_out"],
            "turns": None,
        }
    # 멀티턴 — context 누적
    context: list = []
    turns_out = []
    tin = tout = 0
    lat = 0.0
    last = None
    for turn in item["turns"]:
        r = run_once(turn["query"], context if context else None)
        turns_out.append({"route": r["route"], "ids": r["ids"], "answer": r["answer"]})
        context.append({"role": "user", "content": turn["query"]})
        context.append({"role": "assistant", "content": r["answer"]})
        tin += r["tokens_in"]; tout += r["tokens_out"]; lat += r["latency_ms"]
        last = r
    return {
        "route_last": last["route"], "ids_last": last["ids"], "answer_last": last["answer"],
        "latency_ms": lat, "tokens_in": tin, "tokens_out": tout, "turns": turns_out,
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # Windows cp949 콘솔 한글 깨짐·크래시 방지
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--queryset", default="docs/ai-ab-test-queryset.json")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--only", default=None, help="쉼표구분 id만 실행(스모크용)")
    args = ap.parse_args()

    settings.gemini_generation_model = args.model  # 런타임 모델 교체(앱 코드 불변)
    _install_token_meter()

    queryset = json.loads(Path(args.queryset).read_text(encoding="utf-8"))
    items = queryset["items"]
    if args.only:
        keep = set(args.only.split(","))
        items = [it for it in items if it["id"] in keep]

    out_path = args.out or f"docs/ab-eval-raw-{args.model}.json"
    results: dict[str, list] = {}
    print(f"모델={args.model} 항목={len(items)} runs={args.runs}")
    for it in items:
        runs = []
        for n in range(args.runs):
            runs.append(run_item(it))
        results[it["id"]] = runs
        rep = runs[0]
        print(f"  {it['id']:>4} route={rep['route_last']} ids={len(rep['ids_last'])} "
              f"tok={rep['tokens_in']}+{rep['tokens_out']} {rep['latency_ms']:.0f}ms")

    payload = {"model": args.model, "runs": args.runs, "results": results}
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장: {out_path}")


if __name__ == "__main__":
    main()
