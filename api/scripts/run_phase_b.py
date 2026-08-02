"""Phase B G2 baseline 캡처 러너 — 큐리셋을 실제 `run_search()`로 1회씩 돌려 raw 결과를 만든다.

⚠️ 과금 보호: `test_live_smoke.py`와 동일 게이트 — 환경변수 `RUN_LIVE_SMOKE=1`이 아니면 절대
  실제 LLM/DB를 호출하지 않는다(CI·무심코 실행한 pytest·다음 dev-auto 루프가 실수로 Gemini를
  호출하지 않게 — 13.1 스토리 Boundaries).
  ✎ 2026-07-30 정정: 여기 있던 "무료 티어 일일 쿼터" 표현은 사실이 아니다 — 이 프로젝트 키는
  **유료 티어**다(사용자 확인). 게이트는 그대로 두되(무심코 과금되는 것은 여전히 막아야 한다),
  "쿼터 때문에 전량을 못 돌린다"는 근거는 성립하지 않는다. `test_live_smoke.py` 헤더 참조.

역할: `docs/ai-ab-test-queryset.json`의 각 item(단일/멀티턴)을 `app.graph.graph.run_search()`
  로 N=1회 실행해, `score_ab.score_model()`이 기대하는 shape으로 직렬화한다:
    results[id] = [{route_last, ids_last, answer_last, turns?, tokens_in, tokens_out, latency_ms}]
  (멀티턴도 `turns[]`와 별개로 route_last/ids_last/answer_last를 "마지막 턴" 값으로 채운다 —
   score_model의 flaky 판정이 kind와 무관하게 이 두 키를 읽기 때문.)
  N=3(flaky 판정)·tokens_in/out 실측은 이 스토리 범위 밖이다 — tokens는 run_search()가 현재
  노출하지 않으므로 best-effort 0(비용 축은 1차 관심사가 아님, G2 핵심 신호는
  result_mean/gate_pass/routing_correct — Design Notes).

내결함성(코드리뷰 패치 + review pass 4): item 구조 오류(kind 오타·멀티턴 turns 누락·query
  누락·중복 id·`--out` 상위 디렉터리 없음)는 **라이브 호출 전에** fail-fast로 즉시 raise한다
  (쿼터 낭비 방지 — 데이터가 깨졌으면 아예 시작하지 않는다). 반면 실행 중 발생하는 라이브
  실패(429·네트워크 등, run_search 호출 자체의 실패)는 item별로 잡아 그 item 결과에
  `{"error": ...}`로 기록하고 다음 item으로 계속 진행한다 — 47개 전량 실행 중 하나가 죽어도
  이미 확보한 앞선 결과가 통째로 날아가지 않는다. 매 item 처리 직후 `--out`에 지금까지의
  누적 결과를 원자적으로(임시파일 → replace) flush한다(중간에 프로세스가 죽어도 그 시점까지는
  파일에 남는다 — 직접 write_text는 truncate-then-write라 이 보장이 깨진다).
  `RUN_LIVE_SMOKE`가 아니거나 캡처 중 item이 하나라도 에러였으면 종료코드는 0이 아니다 —
  `run_phase_b.py && score_ab.py ...`처럼 셸에서 체인해도 게이트 차단이나 부분 실패가
  조용히 삼켜지지 않는다. `--out`은 필수다(기본값이 커밋된 baseline 산출물 자체였다).

실행 — 전량(47개. 큐리셋 2026-08-02 재설계(DW-609) 기준):
  api/ 에서 RUN_LIVE_SMOKE=1 DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:55322/postgres \
    .venv/bin/python scripts/run_phase_b.py --out docs/g2-capture-YYYY-MM-DD.json

실행 — 일부만(디버깅·재캡처용):
  ... --subset S1,H1,CL1 --out docs/g2-capture-YYYY-MM-DD-partial.json

⚠️ `--out`을 `docs/g2-baseline.json`·`docs/g2-baseline-partial.json`으로 주지 말 것 — 그 둘은
  **커밋된 비교 기준선**이고 G2 게이트가 대조 대상으로 읽는다. 덮어쓰면 회귀 판정의 기준점이
  사라지고(되돌리려면 유료 라이브 재캡처밖에 없다), 그게 바로 위에서 `--out`을 필수로 만든
  이유다. 기준선을 의도적으로 다시 뜨는 것(re-baselining)은 별도 결정으로 다룬다.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

# G2 게이트가 비교 대상으로 읽는 커밋된 기준선 — --out으로 지목하면 거부한다(main() 참조).
_PROTECTED_BASELINES = frozenset({
    (API_ROOT / "docs" / "g2-baseline.json").resolve(),
    (API_ROOT / "docs" / "g2-baseline-partial.json").resolve(),
})


def _card_id(card) -> str:
    """listings 항목에서 id를 꺼낸다 — ListingCard(pydantic 속성) · dict(테스트 모킹) 둘 다 지원."""
    return card.id if hasattr(card, "id") else card["id"]


def _validate_item(item: dict) -> None:
    """item 구조를 사전 검증한다 — 캡처 루프(라이브 호출) 시작 전에 fail-fast로 즉시 raise한다.

    kind 오타·필드 누락은 데이터 버그이지 일시적 실행 실패가 아니다 — 원인불명의 KeyError로
    죽거나(구 동작) item별 try/except에 조용히 삼켜지는 대신, 전체 캡처를 시작하기 전에
    명시적으로 거부해 쿼터를 낭비하지 않는다(코드리뷰 패치).

    query 누락도 여기서 잡는다(review pass 4) — 이전엔 kind·turns만 봐서 `query` 키가 없는
    single item이나 turn 오타(예: `q_typo`)는 라이브 호출 도중 `KeyError`로 터져
    `{"error": "'query'"}`로 삼켜졌다. 이건 데이터 버그이지 429 같은 일시적 실패가 아닌데,
    같은 모양의 에러 문자열이라 구분이 안 됐다 — 그리고 그 구분이 안 되는 순간은 이미
    앞선 item들이 쿼터를 태운 뒤였다. 그래서 라이브 호출 0회 상태에서 미리 잡는다.
    """
    kind = item.get("kind")
    if kind not in ("single", "multiturn"):
        raise ValueError(f"unknown kind: {kind!r} (id={item.get('id')!r})")
    if kind == "single":
        if not item.get("query"):
            raise ValueError(f"missing query: id={item.get('id')!r}")
    else:  # "multiturn"
        turns = item.get("turns")
        if not turns:
            raise ValueError(f"empty turns: id={item.get('id')!r}")
        for ti, turn in enumerate(turns):
            if not turn.get("query"):
                raise ValueError(f"missing query in turn {ti}: id={item.get('id')!r}")


def _run_single(item: dict, run_search) -> dict:
    """single kind item 1회 실행 — score_model이 읽는 run 1개 shape을 만든다."""
    t0 = time.monotonic()
    out = run_search(item["query"])
    latency_ms = (time.monotonic() - t0) * 1000
    return {
        "route_last": out.get("route", ""),
        "ids_last": [_card_id(c) for c in out.get("listings", [])],
        "answer_last": out.get("answer", ""),
        # 되묻기 페이로드({question, chips})를 그대로 남긴다(DW-609) — 질문 문구만 캡처하면
        # "칩을 눌러도 된다"고 말해 놓고 칩이 0개인 상태를 채점기가 볼 수 없다. score_ab의
        # CLARIFY 채점이 이 키의 유무로 "칩까지 검사할 수 있는 캡처인가"를 판단한다.
        "clarify_last": out.get("clarify"),
        # run_search()가 토큰 사용량을 노출하지 않아 항상 0(placeholder)이다. 여기에 별도의
        # "측정 안 함" 플래그는 찍지 않는다(review pass 5) — score_ab.score_model()은 플래그가
        # 아니라 토큰 합계가 0인지로 직접 판단하고(그 이유는 그쪽 주석 참조), 아무도 안 읽는
        # 플래그를 남겨두면 다음 사람이 "True로 찍으면 비용 축이 켜진다"고 오해한다.
        "tokens_in": 0,
        "tokens_out": 0,
        "latency_ms": latency_ms,
    }


def _run_multiturn(item: dict, run_search) -> dict:
    """multiturn kind item 1회 실행 — turns[] 조립 + route_last/ids_last/answer_last(마지막 턴).

    맥락(context)은 run_search(query, context) 인자로만 흘리고 저장하지 않는다(FR18 무상태와
    동일 원칙) — 이전 턴의 질의/답변을 그대로 다음 호출의 context로 누적해 넘긴다.
    turns가 비어 있으면(데이터 버그) `_validate_item`이 이미 앞서 걸러내므로 여기까진 안 온다.
    """
    context: list = []
    turns_out: list[dict] = []
    total_ms = 0.0
    last_route, last_ids, last_answer = "", [], ""
    last_clarify = None
    for turn in item["turns"]:
        t0 = time.monotonic()
        out = run_search(turn["query"], context or None)
        total_ms += (time.monotonic() - t0) * 1000
        ids = [_card_id(c) for c in out.get("listings", [])]
        route = out.get("route", "")
        answer = out.get("answer", "")
        clarify = out.get("clarify")  # 턴별 되묻기 페이로드(DW-609 — _run_single 주석 참조)
        turns_out.append({"route": route, "ids": ids, "answer": answer, "clarify": clarify})
        context = context + [
            {"role": "user", "content": turn["query"]},
            {"role": "assistant", "content": answer},
        ]
        last_route, last_ids, last_answer, last_clarify = route, ids, answer, clarify
    return {
        "route_last": last_route,
        "ids_last": last_ids,
        "answer_last": last_answer,
        "clarify_last": last_clarify,
        "turns": turns_out,
        "tokens_in": 0,
        "tokens_out": 0,  # 위 _run_single과 동일(플래그 없이 합계 0으로 판단)
        "latency_ms": total_ms,
    }


def capture(
    queryset: dict,
    subset: list[str] | None,
    model_name: str,
    run_search,
    out_path: str | Path | None = None,
) -> dict:
    """큐리셋 item들을 run_search()로 N=1회 실행해 score_ab.score_model()용 raw dict를 만든다.

    run_search는 인자로 주입한다 — 테스트가 라이브 호출 없이 모킹해 shape 조립만 검증할 수 있게.
    out_path를 주면 item 처리 직후마다 그 경로에 누적 결과를 flush한다(중간 실패로 이미 확보한
    결과까지 잃지 않게 — 코드리뷰 패치).

    구조 오류(kind 오타·멀티턴 turns 누락·query 누락·중복 id)는 어떤 item도 실행하기 전에 전량
    사전 검증해 fail-fast raise한다. `--out` 상위 디렉터리 존재 여부도 같은 사전검증 단계에서
    확인한다(review pass 4 — 없으면 첫 라이브 호출 뒤에야 `FileNotFoundError`로 터져 그 호출의
    비용이 낭비된다). 반면 실행 중 실제 run_search 호출이 실패하면(429 등 일시적 라이브 오류)
    그 item만 `{"error": str(exc)}`로 기록하고 다음 item으로 계속 진행한다.
    """
    items = queryset["items"]
    if subset is not None:
        wanted = set(subset)
        items = [it for it in items if it["id"] in wanted]

    # ── 사전검증(라이브 호출 0회 상태) ──────────────────────────────
    # id는 아래 중복검사·subset 필터가 이미 색인하므로 그 전에 존재를 확인한다(review pass 5).
    # 없으면 이 파일의 다른 구조 오류처럼 원인을 말해주는 ValueError가 아니라 맨 KeyError로
    # 죽어서, 어느 item이 문제인지 알 수 없었다.
    for idx, item in enumerate(items):
        if not item.get("id"):
            raise ValueError(f"missing item id at index {idx}")
    ids_seen = [it["id"] for it in items]
    dupes = sorted({i for i in ids_seen if ids_seen.count(i) > 1})
    if dupes:
        # 중복 id는 두 item이 같은 결과 슬롯에 쓰여 하나가 조용히 사라진다(review pass 4 —
        # 두 번 라이브 호출하고도 한 건만 남아 캡처 비용이 낭비된다). 시작 전에 거부한다.
        raise ValueError(f"duplicate item id(s): {dupes}")
    for item in items:
        _validate_item(item)  # 라이브 호출 0회 상태에서 전량 사전 검증(쿼터 낭비 방지)
    if out_path is not None:
        out_parent = Path(out_path).parent
        if str(out_parent) not in ("", ".") and not out_parent.exists():
            raise ValueError(f"--out 상위 디렉터리가 존재하지 않습니다: {out_parent}")

    results: dict[str, list[dict]] = {}

    def _flush() -> None:
        if out_path is None:
            return
        # 원자적 쓰기(review pass 4) — 임시 파일에 먼저 쓰고 os.replace로 교체한다. 이전엔
        # out_path를 직접 write_text했는데, 이는 열자마자 파일을 비우고(truncate) 그 다음에
        # 쓰는 동작이라 44개 중 어느 flush 창에서든 프로세스가 죽으면 그 시점까지 확보한
        # 유료 캡처 결과가 전부 유실된다(docstring이 약속한 "중간에 죽어도 남는다"의 반대).
        # replace는 같은 파일시스템 안에서 원자적이라, 임시 파일 쓰기 도중 죽어도 out_path
        # 자체는 직전 flush의 유효한 내용을 그대로 유지한다.
        tmp_path = Path(str(out_path) + ".tmp")
        tmp_path.write_text(
            json.dumps({"model": model_name, "results": results}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(out_path)

    # 루프 시작 전에 한 번 flush한다(review pass 5). 전엔 flush가 루프 안에만 있어, 매칭
    # item이 0개면 --out이 한 번도 안 써지고 **이전 실행의 낡은 파일이 그대로 남는데** main()은
    # "0개 item 캡처 완료"로 exit 0을 냈다 — `run_phase_b.py && score_ab.py --raw <out>` 체인이
    # 다른 모델의 옛 캡처를 새 baseline으로 채점한다. 먼저 비우면 그 경로가 막힌다.
    _flush()

    for item in items:
        try:
            if item["kind"] == "single":
                run = _run_single(item, run_search)
            else:  # "multiturn" — _validate_item이 이미 kind를 이 두 값으로 못박음
                run = _run_multiturn(item, run_search)
            results[item["id"]] = [run]
        except Exception as exc:  # noqa: BLE001 — 라이브 호출 실패를 item 단위로 흡수, 전체는 계속
            results[item["id"]] = [{"error": str(exc)}]
        _flush()

    return {"model": model_name, "results": results}


def main() -> None:
    if os.getenv("RUN_LIVE_SMOKE") != "1":
        print(
            "RUN_LIVE_SMOKE=1이 아니면 실행하지 않습니다(쿼터 보호 게이트 — "
            "tests/test_live_smoke.py와 동일 관례)."
        )
        # exit 0으로 조용히 끝나면 `run_phase_b.py && score_ab.py ...`처럼 셸에서 체인했을 때
        # 게이트가 막았다는 사실이 삼켜지고 뒤 명령이 이미 있던(낡은) --out 파일을 그대로
        # 채점해 버린다(review pass 4). 비정상 종료로 체인이 여기서 멈추게 한다.
        sys.exit(1)

    ap = argparse.ArgumentParser()
    ap.add_argument("--queryset", default="docs/ai-ab-test-queryset.json")
    ap.add_argument(
        "--subset", default=None,
        help="쉼표구분 item id 부분집합(예: S1,H1,CL1). 생략하면 --queryset 전량 — "
             "전량 실행은 실제 유료 API 호출을 발생시키니 신중히 사용할 것.",
    )
    # --out은 필수다(review pass 4) — 기본값이 커밋된 baseline 산출물
    # (docs/g2-baseline-partial.json) 자체였어서, --out을 깜빡하고 전량 실행하면 그 기준
    # 캡처가 item 1부터 조용히 덮어써진다. DW-554가 문서화한 실행 커맨드는 이미 --out을
    # 명시하므로 이 필수화로 깨지는 기존 사용법은 없다.
    ap.add_argument("--out", required=True, help="raw 결과를 기록할 경로(필수)")
    ap.add_argument("--model", default=None, help="raw 결과에 기록할 모델명(생략 시 gemini_generation_model 설정값)")
    args = ap.parse_args()

    # 커밋된 기준선은 --out으로 지목할 수 없다(13.8 3차 리뷰 patch). 위 독스트링이 이미 같은
    # 규칙을 ⚠️로 적었지만 주석은 실행되지 않는다(CLAUDE.md B9) — 실제로 재현해 보면
    # capture()가 루프 진입 **전에** 첫 _flush를 하므로 라이브 호출 0회로 죽는 실행도
    # 대상 파일을 이미 비운다(실측: 47항목 → 1항목). 복구 수단은 유료 47문항 재캡처뿐이라
    # 되돌리기가 없는 파괴다. 의도적 re-baselining은 이 스크립트가 아니라 별도 결정으로 다룬다.
    if Path(args.out).resolve() in _PROTECTED_BASELINES:
        ap.error(
            f"--out이 커밋된 G2 비교 기준선({args.out})을 가리킵니다 — 덮어쓰면 회귀 판정의 "
            "기준점이 사라집니다. 날짜형 경로(예: docs/g2-capture-YYYY-MM-DD.json)를 쓰세요."
        )

    subset = None
    if args.subset is not None:
        subset = [s.strip() for s in args.subset.split(",") if s.strip()]
        if not subset:
            ap.error("--subset이 빈 값입니다 — 쉼표구분 id를 지정하거나 옵션을 생략해 전량 실행하세요.")

    queryset = json.loads(Path(args.queryset).read_text(encoding="utf-8"))

    if subset is not None:
        # 오타 등으로 큐리셋에 없는 id를 섞으면 조용히 드롭하지 않고 명시 거부한다(코드리뷰 패치
        # — 바로 위 "빈 subset은 에러"와 일관되게).
        missing = set(subset) - {it["id"] for it in queryset["items"]}
        if missing:
            ap.error(f"--subset에 큐리셋에 없는 id가 있습니다: {sorted(missing)}")

    # RUN_LIVE_SMOKE=1로 확인된 뒤에만 app/DB 의존 모듈을 늦게 import한다(무게이트 실행 시
    # DB·Gemini 설정이 없어도 스크립트 자체는 죽지 않게).
    from app.config import settings
    from app.graph.graph import run_search

    model_name = args.model or settings.gemini_generation_model

    raw = capture(queryset, subset, model_name, run_search, out_path=args.out)
    # 실패(429 등)한 item은 "캡처 완료"가 아니라 실패로 센다(review pass 4 — 이전엔 에러
    # 항목도 결과 개수에 그냥 합산돼 "44개 캡처 완료"처럼 보이면서 실제로는 여러 건이
    # {"error": ...}뿐이었다).
    errored = sum(1 for runs in raw["results"].values() if runs and "error" in runs[0])
    captured = len(raw["results"]) - errored
    print(f"{captured}개 item 캡처 완료(실패 {errored}건) → {args.out}")
    if errored:
        sys.exit(1)


if __name__ == "__main__":
    main()
