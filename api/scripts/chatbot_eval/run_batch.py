"""챗봇 평가 배치 실행기 — queries.json(100개 신규 입력)을 run_search_agent로 실제 실행해
`$OUT/responses.jsonl`에 저장한다(verify_agent_regression.py와 동일한 in-process 호출 관례).

안전장치(운영 DB 오염 방지, CLAUDE.md B3): DATABASE_URL이 로컬 Supabase(127.0.0.1:55322)를
가리키지 않으면 즉시 실패한다 — api/.env의 DATABASE_URL은 운영 Supabase pooler를 가리키므로,
환경변수를 깜빡 export하지 않으면 이 스크립트가 조용히 운영 DB를 두드리게 된다. 그 사고를
"실행되는 검사"로 막는다(주석이 아니라 코드로).

멀티턴 처리: 1턴을 실행해 얻은 결과로, 웹 클라이언트(ChatAssistant.tsx)와 동일한 규칙으로
다음 턴 context를 조립한다 — user 턴 + assistant 턴(listing_ids=이 턴이 실제로 보여준 매물
id들: 카드 목록이 있으면 그 id들, 없고 단건 시세 진단만 있으면 그 진단 대상 id 1개, 둘 다
없으면 None). 이 규칙은 verify_agent_regression.py의 `_client_listing_ids`와 동일하다.

이어달리기(resume): 이미 `responses.jsonl`에 적힌 id는 건너뛴다 — 중간에 멈춰도 재실행하면
안 한 항목부터 이어간다.

실행:
  cd api && DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:55322/postgres" \
    LANGCHAIN_PROJECT="chatbot-eval-20260908" .venv/bin/python scripts/chatbot_eval/run_batch.py

출력 디렉토리는 --out CLI 인자로 지정한다(예: --out /경로/20260909). 생략하면 기존 OUT
  환경변수(하위호환)를, 그것도 없으면 20260908 경로를 쓴다. judge.py·make_sheet.py는 여전히
  OUT 환경변수만 읽으므로, --out으로 새 디렉토리를 지정해 이 스크립트를 돌렸다면 이어지는
  두 스크립트는 OUT=그 경로로 맞춰 실행해야 한다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from dotenv import dotenv_values

# ── 운영 DB 오염 방지 가드 — app.graph.agent를 import하기 전에 검사한다(DB·LLM 호출 이전 차단).
_LOCAL_DB_MARKERS = ("127.0.0.1:55322", "localhost:55322")
_db_url = os.environ.get("DATABASE_URL", "")
if not any(marker in _db_url for marker in _LOCAL_DB_MARKERS):
    raise RuntimeError(
        "DATABASE_URL이 로컬 Supabase(127.0.0.1:55322)를 가리키지 않습니다 — 운영 DB 오염을 "
        "막기 위해 중단합니다. api/.env의 DATABASE_URL은 운영 pooler를 가리키므로 반드시 "
        "아래처럼 로컬 DB를 명시적으로 export한 뒤 실행하세요:\n"
        '  DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:55322/postgres" '
        ".venv/bin/python scripts/chatbot_eval/run_batch.py"
    )

os.environ.setdefault("LANGCHAIN_PROJECT", "chatbot-eval-20260908")

# verify_agent_regression.py와 동일 관례 — api 루트를 sys.path에 얹어 app.* 임포트를 가능하게 한다.
_API_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_API_ROOT))

# Fix 1 전제조건 — LangSmith 트레이싱을 app.* 임포트 "이전"에 켠다. app.config.py에도
# _promote_env_from_dotenv(.env → os.environ)가 있지만, 이 스크립트처럼 app.graph.agent를
# 바로 import하면 그 모듈이 langchain_google_genai를 먼저 import해버려 langsmith의
# get_env_var(lru_cache)가 "꺼짐" 상태로 먼저 굳는다 — config.py의 승격은 그 뒤라 이미 늦다
# (실측 확인: probe_collect_runs.py — app.graph.agent import 후 os.environ엔 값이 들어와
# 있는데도 tracing_is_enabled()는 False). 그래서 여기서 dotenv_values로 직접, 가장 먼저 켠다.
_dotenv_vals = dotenv_values(str(_API_ROOT / ".env"))
for _key in ("LANGCHAIN_TRACING_V2", "LANGCHAIN_API_KEY"):
    if _dotenv_vals.get(_key) and _key not in os.environ:
        os.environ[_key] = _dotenv_vals[_key]

from app.graph.agent import run_search_agent  # noqa: E402
from langchain_core.tracers.context import collect_runs  # noqa: E402
import langsmith.utils as _ls_utils  # noqa: E402

if not _ls_utils.tracing_is_enabled():
    raise RuntimeError(
        "LangSmith 트레이싱이 꺼져 있습니다 — Fix 1(도구 원문 캡처)이 동작하려면 반드시 켜져야 "
        "합니다. api/.env의 LANGCHAIN_TRACING_V2=true·LANGCHAIN_API_KEY를 확인하세요."
    )

QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"


def _parse_args() -> argparse.Namespace:
    """--out(출력 디렉토리)·--category(콤마 구분 부분집합, 예: "가이드" 또는 "거절,경계")를
    함께 파싱한다. --category 생략 시 queries.json 전체(기존 동작, 회귀 0)를 돈다 — DW-873
    재검증(가이드 15건만 2회, 거절+경계 15건만 1회)처럼 카테고리 단위로 좁혀 돌릴 때 쓴다."""
    parser = argparse.ArgumentParser(description="챗봇 평가 배치 실행기")
    parser.add_argument("--out", type=str, default=None, help="응답을 저장할 디렉토리(기본: OUT 환경변수)")
    parser.add_argument(
        "--category", type=str, default=None,
        help="콤마로 구분한 category 부분집합만 실행(예: '가이드' 또는 '거절,경계'). 생략 시 전체.",
    )
    args, _unknown = parser.parse_known_args()
    return args


def _resolve_out_dir(args: argparse.Namespace) -> Path:
    """--out CLI 인자를 우선하고, 없으면 기존 OUT 환경변수(하위호환)를 쓴다."""
    if args.out:
        return Path(args.out)
    return Path(os.environ.get("OUT", "/home/whlee/workspace/bmad-encar-demo/.logs/chatbot_eval/20260908"))


_ARGS = _parse_args()
OUT_DIR = _resolve_out_dir(_ARGS)
OUT_PATH = OUT_DIR / "responses.jsonl"
_CATEGORY_FILTER = (
    {c.strip() for c in _ARGS.category.split(",") if c.strip()} if _ARGS.category else None
)

_MAX_CALLS = 140  # 예산 상한(사용자 지시) — 재시도 포함 전체 run_search_agent 호출 수.
_QUOTA_RETRY_MAX = 3
_QUOTA_BACKOFF_SEC = 30


def _card_summary(card) -> dict:
    """listing 카드 요약 — 답변이 실제로 서술할 수 있는(narratable) 필드는 전부 남긴다.

    최초 버전은 id·model·year·mileage·price·fuel·accident_status만 남겼는데, 실측
    스팟체크(judgments.jsonl 1차 결과)에서 judge가 "옵션을 지어냈다"고 여러 건을 BAD
    처리한 게 실은 진짜 DB options(예: 그랜저 GN7 하이브리드 6218befb의 통풍시트·파노라마
    선루프·어댑티브크루즈·헤드업디스플레이)를 그대로 옮긴 정답이었다 — judge에게 options·
    region·1인소유·비흡연을 아예 안 보여줘서 생긴 오탐(false positive)이었다. 사진·집계용
    필드(image_url/image_path/view_count/image_count)만 제외한다 — 채팅 답변이 서술할
    일이 없는 UI 메타데이터이기 때문이다.
    """
    return {
        "id": card.id,
        "manufacturer": card.manufacturer,
        "model": card.model,
        "year": card.year,
        "mileage": card.mileage,
        "price": card.price,
        "region": card.region,
        "fuel": card.fuel,
        "accident_status": card.accident_status,
        "is_single_owner": card.is_single_owner,
        "is_non_smoker": card.is_non_smoker,
        "options": card.options,
    }


def _diagnosis_summary(md: dict | None) -> dict | None:
    """market_price_stats 결과(app/market_price.diagnose() dict)를 그대로 남긴다.

    처음엔 verdict·tabpfn 예측가·비교군 건수만 남겼는데, 실측 스팟체크에서 에이전트 답변이
    percentile("하위 67% 수준")·stats.min/median/max("1,050만~1,950만 원, 중앙값 1,180만")를
    실제로 인용하는데도 judge에게 안 보여줘 같은 종류의 오탐을 만들 뻔했다 — 크기가 작으므로
    (비교군 상한 5건, agent.py _MAX_MARKET_DIAGNOSES) 통째로 넘기는 쪽이 안전하다.
    """
    return md


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "quota" in msg or "429" in msg or "resource_exhausted" in msg or "resourceexhausted" in msg


# ── Fix 1 — 도구 원문 캡처 ───────────────────────────────────────────────
# v1 judge는 카드 요약(위 _card_summary/_diagnosis_summary)만 봤는데, 이것도 결국 "사람이
# 고른 필드"라 에이전트가 실제로 인용한 문장(예: search_guides 원문, market_price_stats의
# 서술형 판정문)까지는 못 덮는다. collect_runs()로 run_search_agent 1회 호출 동안 실행된
# LangChain run을 전부 받아 tool 타입만 골라 ToolMessage.content(에이전트가 실제로 읽은
# 텍스트) 그대로 넘긴다 — 사람이 만든 요약이 아니라 원문이라 "지어냈다" 오탐이 구조적으로
# 줄어든다.
#
# 실측(2026-09-08, probe_collect_runs.py 2회): 이 에이전트 루프(run_search_agent)는
# @traceable로 감싸여 있지 않아 그 안의 LLM 호출·도구 호출이 서로 부모-자식으로 안 엮이고
# 각자 독립된 root run이 된다(parent_run_id=None, trace_id=자기 id). 그래서 tool run은
# collect_runs()의 traced_runs 최상위에 바로 나오고 child_runs는 항상 비어 있다 — 그래도
# 구조가 바뀔 가능성에 대비해 재귀는 유지한다(사용자 지시).
_LANGSMITH_ENDPOINT = "https://api.smith.langchain.com"
_TRACE_POLL_TIMEOUT_SEC = 30
_TRACE_POLL_INTERVAL_SEC = 3
rest_fallback_used = 0  # 진단용 — 로컬 캡처가 놓쳐서 REST로 보강한 횟수(최종 리포트에 남긴다)


def _tool_output_text(run) -> str:
    """tool 런 1건에서 에이전트가 실제로 본 텍스트(ToolMessage.content)를 뽑는다."""
    outputs = getattr(run, "outputs", None)
    if outputs:
        output = outputs.get("output") if isinstance(outputs, dict) else None
        content = getattr(output, "content", None)  # 로컬 in-memory ToolMessage 객체
        if content is not None:
            return content
        if isinstance(output, dict) and "content" in output:  # REST로 되돌아온 직렬화 형태
            return output["content"]
    error = getattr(run, "error", None)
    if error:
        return f"[도구 실행 오류] {error}"
    return "[도구 출력 없음 — 로컬 캡처 실패, REST 재조회도 실패]"


def _collect_tool_runs(runs: list) -> list:
    """traced_runs(및 child_runs 재귀)에서 run_type=='tool'인 run만 실행 순서대로 모은다."""
    found: list = []

    def walk(run) -> None:
        if getattr(run, "run_type", None) == "tool":
            found.append(run)
        for child in getattr(run, "child_runs", None) or []:
            walk(child)

    for run in runs:
        walk(run)
    return found


def _rest_poll_run(run_id: str, api_key: str) -> dict | None:
    """LangSmith REST로 run 1건이 서버에 올라올 때까지 최대 30초 폴링 후 조회한다
    (verify_answer_numbers.py의 POST /runs/query + x-api-key 패턴과 동일). 이 에이전트의
    tool run은 서로 독립 root라(위 설계결정 참조) trace_id가 곧 그 run 자신의 id다."""
    import requests

    body = {
        "filter": f'eq(trace_id, "{run_id}")',
        "limit": 1,
        "select": ["id", "name", "run_type", "inputs", "outputs", "error"],
    }
    deadline = time.time() + _TRACE_POLL_TIMEOUT_SEC
    while True:
        resp = requests.post(
            f"{_LANGSMITH_ENDPOINT}/runs/query", json=body,
            headers={"x-api-key": api_key, "Content-Type": "application/json"}, timeout=30,
        )
        resp.raise_for_status()
        found = resp.json().get("runs", [])
        if found:
            return found[0]
        if time.time() >= deadline:
            return None
        time.sleep(_TRACE_POLL_INTERVAL_SEC)


def _build_tool_calls(traced_runs: list, tools_used: list[str]) -> list[dict]:
    """이번 턴에 실제로 실행된 도구 호출을 [{name, args, output_text}]로 만든다(호출 순서
    보존). 로컬 캡처가 tools_used보다 적게 잡히면(실측상 발생 안 함, 방어적 코드) LangSmith
    REST로 그 run을 재조회해 보강한다."""
    global rest_fallback_used
    tool_runs = _collect_tool_runs(traced_runs)
    calls: list[dict] = []
    api_key = os.environ.get("LANGCHAIN_API_KEY")
    for run in tool_runs:
        text = _tool_output_text(run)
        if text.startswith("[도구 출력 없음") and api_key:
            remote = _rest_poll_run(str(run.id), api_key)
            if remote and remote.get("outputs"):
                rest_fallback_used += 1
                out = (remote["outputs"] or {}).get("output")
                text = out.get("content", str(out)) if isinstance(out, dict) else str(out)
        calls.append({"name": run.name, "args": run.inputs, "output_text": text})

    if len(calls) < len(tools_used):
        # tool_obj 자체가 없는 경우(모델이 존재하지 않는 도구 이름을 지어낸 환각) — agent.py가
        # tool_obj.invoke()를 아예 호출하지 않아 애초에 트레이싱 대상이 아니다(로컬·REST 둘 다
        # 못 찾는다, 설계 한계 — 실측 2회에서는 발생하지 않았다).
        missing = Counter(tools_used) - Counter(c["name"] for c in calls)
        for name, cnt in missing.items():
            calls.extend(
                {"name": name, "args": None,
                 "output_text": "[알 수 없는 도구 이름 — 실행되지 않아 트레이싱 없음]"}
                for _ in range(cnt)
            )
    return calls


def _call_with_retry(
    query: str, context: list | None, listing_id: str | None
) -> tuple[dict | None, str | None, int, list[dict], str | None]:
    """run_search_agent를 호출한다. 쿼터 오류면 30초 대기 후 최대 3회 재시도.
    반환: (결과 또는 None, 오류 메시지 또는 None, 실제 호출 횟수, tool_calls, trace_id).
    tool_calls·trace_id는 Fix 1 — collect_runs()로 이번 호출 동안의 LangChain run을 모아
    도구 원문을 뽑는다(성공한 시도에서만 의미 있음, 실패한 재시도는 버려도 무해)."""
    calls = 0
    for attempt in range(_QUOTA_RETRY_MAX + 1):
        calls += 1
        try:
            with collect_runs() as cb:
                result = run_search_agent(query, context=context, listing_id=listing_id)
            tool_calls = _build_tool_calls(cb.traced_runs, result.get("tools_used") or [])
            trace_id = str(cb.traced_runs[0].id) if cb.traced_runs else None
            return result, None, calls, tool_calls, trace_id
        except Exception as exc:  # noqa: BLE001 — 항목 단위 fail-loud 대신 기록 후 계속(사용자 지시).
            if _is_quota_error(exc) and attempt < _QUOTA_RETRY_MAX:
                print(f"    쿼터 오류 — {_QUOTA_BACKOFF_SEC}초 대기 후 재시도 "
                      f"({attempt + 1}/{_QUOTA_RETRY_MAX}): {exc}")
                time.sleep(_QUOTA_BACKOFF_SEC)
                continue
            return None, f"{type(exc).__name__}: {exc}", calls, [], None
    return None, "재시도 초과", calls, [], None  # pragma: no cover - 위 루프가 항상 먼저 반환


def _client_listing_ids(result: dict) -> list[str] | None:
    """웹 ChatAssistant.tsx의 listingIdsOf와 동일 규칙(verify_agent_regression.py 동일 함수 재현)."""
    listings = result.get("listings") or []
    if listings:
        return [c.id for c in listings]
    diagnosis = result.get("market_diagnosis")
    if diagnosis:
        return [diagnosis["listing"]["id"]]
    return None


def _load_done_ids() -> set[str]:
    if not OUT_PATH.exists():
        return set()
    done = set()
    with OUT_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                continue
    return done


def main() -> None:
    items = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    if _CATEGORY_FILTER is not None:
        items = [it for it in items if it.get("category") in _CATEGORY_FILTER]
        print(f"--category 필터 적용: {sorted(_CATEGORY_FILTER)} → {len(items)}건")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    done_ids = _load_done_ids()
    if done_ids:
        print(f"이어달리기 — 이미 완료된 {len(done_ids)}건 건너뜀")

    calls_made = 0
    n_ok = 0
    n_err = 0
    tools_counter: dict[str, int] = {}
    t_start = time.time()
    budget_hit = False

    with OUT_PATH.open("a", encoding="utf-8") as out_f:
        for idx, item in enumerate(items, start=1):
            if item["id"] in done_ids:
                continue
            if calls_made >= _MAX_CALLS:
                print(f"예산 상한({_MAX_CALLS}회 호출) 도달 — 나머지 항목은 다음 실행에서 이어감")
                budget_hit = True
                break

            t0 = time.time()
            context: list[dict] = []
            turn_records: list[dict] = []
            final_result: dict | None = None
            error: str | None = None

            try:
                for turn in item["turns"]:
                    if calls_made >= _MAX_CALLS:
                        error = "예산 상한 도달 — 이 항목의 후속 턴을 실행하지 못함"
                        break
                    result, err, used, tool_calls, trace_id = _call_with_retry(
                        turn["query"], context or None, turn.get("listing_id")
                    )
                    calls_made += used
                    if err is not None:
                        error = err
                        break
                    final_result = result
                    for t in result["tools_used"]:
                        tools_counter[t] = tools_counter.get(t, 0) + 1
                    turn_records.append({
                        "query": turn["query"],
                        "answer": result["answer"],
                        "listings": [_card_summary(c) for c in result["listings"]],
                        "tools_used": result["tools_used"],
                        "market_diagnosis": _diagnosis_summary(result.get("market_diagnosis")),
                        "clarify": result.get("clarify"),
                        "tool_calls": tool_calls,  # Fix 1 — 도구 원문(judge v2가 이걸로 환각 여부를 대조)
                        "trace_id": trace_id,
                    })
                    # 다음 턴 context 조립(웹 클라이언트와 동일 규칙) — 마지막 턴이면 안 써도 무해.
                    answer_text = result["answer"] or "(빈 응답)"
                    context.append({"role": "user", "content": turn["query"][:2000]})
                    context.append({
                        "role": "assistant",
                        "content": answer_text[:2000],
                        "listing_ids": _client_listing_ids(result),
                    })
            except Exception as exc:  # noqa: BLE001 — 항목 단위로 격리, 배치 전체를 죽이지 않는다.
                error = f"{type(exc).__name__}: {exc}"

            record = {
                "id": item["id"],
                "category": item["category"],
                "queries": [t["query"] for t in item["turns"]],
                "turns": turn_records,
                "final_answer": final_result["answer"] if final_result else None,
                "elapsed_sec": round(time.time() - t0, 2),
                "error": error,
            }
            out_f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
            out_f.flush()

            if error:
                n_err += 1
            else:
                n_ok += 1

            if idx % 10 == 0 or idx == len(items):
                print(f"[{idx}/{len(items)}] ok={n_ok} err={n_err} calls={calls_made} "
                      f"경과={time.time() - t_start:.0f}s")

    print(f"\n완료 — ok={n_ok} err={n_err} 총호출={calls_made} 총경과={time.time() - t_start:.0f}s"
          f"{' (예산 상한으로 중단, 재실행 시 이어감)' if budget_hit else ''}")
    print("tools_used 분포:", tools_counter)
    print(f"Fix 1 — LangSmith REST 폴백으로 보강한 도구 호출 수: {rest_fallback_used}건 "
          "(0이면 로컬 collect_runs() 캡처만으로 전부 충분했다는 뜻)")


if __name__ == "__main__":
    main()
