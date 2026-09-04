"""엔카 실매물 오프라인 평가 — 제품의 `app.market_price.diagnose()`를 encar_eval DB의 테스트
매물마다 돌려, tabpfn_price·comps_median·regression_pred 세 방법의 정확도를 실제값과 비교한다
(report.md §1 배경 — 시드 데이터 위에서 잰 정확도는 고객용 근거가 못 된다는 지적에 대한 대응).

전제: api/scripts/build_eval_db.py로 encar_eval DB가 이미 구성돼 있고(listings 7,081행 +
eval_meta.split), --mode holdout으로 평가하려면 그 스크립트의 `--holdout on`으로 테스트 매물의
status를 미리 'sold'로 바꿔 둬야 한다(이 스크립트는 status를 바꾸지 않는다 — DB 상태 토글은
build_eval_db.py의 책임, 이 스크립트는 순수 조회만).

회귀 기준선("세대별 회귀", 사람이 하듯 손으로 짜는 감가식)은 report.md §5(step2_depreciation.json)와
같은 형태다: price ~ 1 + (anchor_year − year) + mileage/1e4 + option_count_choice
             + [accident_status=='단순교환'] + [accident_status=='사고']
anchor_year = 그 학습군에서 관측된 최댓값 year(가장 최신 연식을 기준/나이=0으로 삼는 감가 곡선
관례 — step2_depreciation.json 실측으로 확인). (target_slug, fuel) 학습행이 40건 미만이면
target_slug 단위로 되돌리고, 그마저 40건 미만이면 예측하지 않는다(null).
"""

import argparse
import collections
import csv
import json
import pathlib
import random
import re
import sys
import time
import uuid

import numpy as np
import psycopg
from psycopg.rows import dict_row

# market_price.py는 app/__init__.py가 비어 있어 app.config를 끌어들이지 않는다(실측 확인) —
# 그래도 혹시 모를 secrets 요구를 방어하려고 import 전에 DATABASE_URL을 채워 둔다.
sys.path.insert(0, ".")

DEFAULT_OUT_DIR = pathlib.Path("/home/whlee/workspace/bmad-encar-demo/.logs/encar_eval/20260905")
DEFAULT_CSV = DEFAULT_OUT_DIR / "listings_eval.csv"
DEFAULT_TEST_IDS = DEFAULT_OUT_DIR / "eval" / "test_ids.json"
DEFAULT_DB_URL = "postgresql://postgres:postgres@127.0.0.1:55322/encar_eval"

MIN_TRAIN_ROWS = 40  # 회귀 기준선 최소 학습표본(과제 지시)
TRAIN_N_RE = re.compile(r"(\d+)건")  # tabpfn_note "기본 모델군 47건 학습" / "학습 표본 3건 — 10건 미만" 공통
METHODS = ["tabpfn_price", "comps_median", "regression_pred"]
EXPECTED_VERDICT_PCT = {"저렴": 10, "다소 저렴": 15, "적정": 50, "다소 높음": 15, "높음": 10}


# ── CSV의 option_count_choice — DB엔 옵션 코드 배열만 있고 표준/선택 구분이 없어 CSV에서 조인 ──
def load_option_choice_counts(csv_path: pathlib.Path) -> dict:
    lookup = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lookup[row["encar_id"]] = int(row["option_count_choice"])
    return lookup


# ── 회귀 기준선("세대별 회귀") ────────────────────────────────────────────────
def fit_regression(rows: list, option_lookup: dict):
    if len(rows) < MIN_TRAIN_ROWS:
        return None
    anchor_year = max(r["year"] for r in rows)
    X, y = [], []
    for r in rows:
        opt = option_lookup.get(r["encar_id"], 0)
        simple = 1.0 if r["accident_status"] == "단순교환" else 0.0
        acc = 1.0 if r["accident_status"] == "사고" else 0.0
        X.append([1.0, anchor_year - r["year"], r["mileage"] / 1e4, opt, simple, acc])
        y.append(r["price"])
    coef, *_ = np.linalg.lstsq(np.array(X, dtype=float), np.array(y, dtype=float), rcond=None)
    return {"anchor_year": anchor_year, "coef": coef, "n": len(rows)}


def predict_regression(fit, year: int, mileage: int, opt_choice: int, accident_status):
    if fit is None:
        return None
    simple = 1.0 if accident_status == "단순교환" else 0.0
    acc = 1.0 if accident_status == "사고" else 0.0
    x = np.array([1.0, fit["anchor_year"] - year, mileage / 1e4, opt_choice, simple, acc])
    return float(x @ fit["coef"])


def build_regression_fits(conn, option_lookup: dict):
    """(target_slug, fuel) 단위 fit + target_slug 단위 폴백 fit을 학습행(split='train')만으로 미리 만든다."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT m.encar_id, m.target_slug, l.year, l.mileage, l.fuel, "
            "l.accident_status, l.price "
            "FROM public.listings l JOIN public.eval_meta m ON m.listing_id = l.id "
            "WHERE m.split = 'train'"
        )
        rows = cur.fetchall()

    by_slug_fuel = collections.defaultdict(list)
    by_slug = collections.defaultdict(list)
    for r in rows:
        by_slug_fuel[(r["target_slug"], r["fuel"])].append(r)
        by_slug[r["target_slug"]].append(r)

    fits_slug_fuel = {k: fit_regression(v, option_lookup) for k, v in by_slug_fuel.items()}
    fits_slug = {k: fit_regression(v, option_lookup) for k, v in by_slug.items()}
    return fits_slug_fuel, fits_slug


def regression_predict_for(fits_slug_fuel, fits_slug, target_slug, fuel, year, mileage, opt, accident_status):
    fit = fits_slug_fuel.get((target_slug, fuel)) or fits_slug.get(target_slug)
    return predict_regression(fit, year, mileage, opt, accident_status)


def parse_train_n(note):
    m = TRAIN_N_RE.search(note or "")
    return int(m.group(1)) if m else None


# ── 케이스 1건 실행 ───────────────────────────────────────────────────────
def run_case(conn, item: dict, option_lookup: dict, fits_slug_fuel: dict, fits_slug: dict) -> dict:
    from app import market_price  # 지연 import — 파일 상단 sys.path.insert 이후여야 함

    base = {
        "listing_id": item["listing_id"],
        "encar_id": item["encar_id"],
        "target_slug": item["target_slug"],
    }
    t0 = time.perf_counter()
    result = market_price.diagnose(uuid.UUID(item["listing_id"]), conn)
    elapsed = time.perf_counter() - t0
    if result is None:
        return {**base, "error": "diagnose()가 None을 반환(매물 없음)", "elapsed_s": elapsed}

    listing = result["listing"]
    stats = result["stats"] or {}
    tabpfn = result["tabpfn"]
    quantiles = tabpfn.get("quantiles") or {}
    opt = option_lookup.get(item["encar_id"], 0)
    reg_pred = regression_predict_for(
        fits_slug_fuel, fits_slug, item["target_slug"], listing["fuel"],
        listing["year"], listing["mileage"], opt, listing["accident_status"],
    )

    return {
        **base,
        "model": listing["model"],
        "fuel": listing["fuel"],
        "year": listing["year"],
        "mileage": listing["mileage"],
        "accident_status": listing["accident_status"],
        "actual_price": listing["price"],
        "comps_step": result["criteria"]["step"],
        "comps_n": result["criteria"]["sample_count"],
        "comps_median": stats.get("median"),
        "comps_q1": stats.get("q1"),
        "comps_q3": stats.get("q3"),
        "percentile": result["percentile"],
        "verdict": result["verdict"],
        "verdict_basis": result["verdict_basis"],
        "tabpfn_price": tabpfn.get("price"),
        "q10": quantiles.get("q10"),
        "q25": quantiles.get("q25"),
        "q50": quantiles.get("q50"),
        "q75": quantiles.get("q75"),
        "q90": quantiles.get("q90"),
        "tabpfn_note": tabpfn.get("note"),
        "train_n": parse_train_n(tabpfn.get("note")),
        "regression_pred": reg_pred,
        "elapsed_s": elapsed,
    }


# ── jsonl 입출력 ─────────────────────────────────────────────────────────
def append_jsonl(path: pathlib.Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: pathlib.Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_cases_csv(cases: list, path: pathlib.Path) -> None:
    if not cases:
        return
    fields, seen = [], set()
    for c in cases:
        for k in c:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(cases)


# ── 지표 ─────────────────────────────────────────────────────────────────
def method_metrics(cases: list, key: str) -> dict:
    apes = [
        abs(c[key] - c["actual_price"]) / c["actual_price"]
        for c in cases
        if c.get(key) is not None and c.get("actual_price")
    ]
    if not apes:
        return {"n": 0, "mdape": None, "mape": None, "hit5": None, "hit10": None, "hit20": None}
    arr = np.array(apes)
    return {
        "n": len(apes),
        "mdape": float(np.median(arr)),
        "mape": float(np.mean(arr)),
        "hit5": float(np.mean(arr <= 0.05)),
        "hit10": float(np.mean(arr <= 0.10)),
        "hit20": float(np.mean(arr <= 0.20)),
    }


def tabpfn_extra_metrics(cases: list) -> dict:
    cov_10_90, cov_25_75 = [], []
    verdict_counts = collections.Counter()
    train_ns, elapsed = [], []
    for c in cases:
        if c.get("elapsed_s") is not None:
            elapsed.append(c["elapsed_s"])
        verdict_counts[c.get("verdict") or "(없음)"] += 1
        if c.get("train_n") is not None:
            train_ns.append(c["train_n"])
        actual = c.get("actual_price")
        if actual is not None and c.get("q10") is not None and c.get("q90") is not None:
            cov_10_90.append(c["q10"] <= actual <= c["q90"])
        if actual is not None and c.get("q25") is not None and c.get("q75") is not None:
            cov_25_75.append(c["q25"] <= actual <= c["q75"])
    n = len(cases)
    not_quantile = sum(1 for c in cases if c.get("verdict_basis") != "분위수")
    return {
        "coverage_q10_q90": (sum(cov_10_90) / len(cov_10_90)) if cov_10_90 else None,
        "coverage_q25_q75": (sum(cov_25_75) / len(cov_25_75)) if cov_25_75 else None,
        "verdict_counts": dict(verdict_counts),
        "verdict_expected_pct": EXPECTED_VERDICT_PCT,
        "share_basis_not_quantile": (not_quantile / n) if n else None,
        "train_n_mean": float(np.mean(train_ns)) if train_ns else None,
        "train_n_median": float(np.median(train_ns)) if train_ns else None,
        "elapsed_mean_s": float(np.mean(elapsed)) if elapsed else None,
    }


def compute_metrics(cases: list, mode: str) -> dict:
    overall = {m: method_metrics(cases, m) for m in METHODS}
    by_slug = collections.defaultdict(list)
    for c in cases:
        by_slug[c.get("target_slug")].append(c)
    per_target = {
        slug: {m: method_metrics(group, m) for m in METHODS} for slug, group in by_slug.items()
    }
    return {
        "mode": mode,
        "n_cases": len(cases),
        "overall": overall,
        "per_target": per_target,
        "tabpfn_extra": tabpfn_extra_metrics(cases),
    }


# ── --compare loo holdout ──────────────────────────────────────────────
def do_compare(out_dir: pathlib.Path, modes: list) -> None:
    mode_a, mode_b = modes
    cases_a = {c["listing_id"]: c for c in read_jsonl(out_dir / f"cases_{mode_a}.jsonl")}
    cases_b = {c["listing_id"]: c for c in read_jsonl(out_dir / f"cases_{mode_b}.jsonl")}
    common = sorted(set(cases_a) & set(cases_b))
    deltas, verdict_agree = [], 0
    for lid in common:
        a, b = cases_a[lid], cases_b[lid]
        actual = a.get("actual_price")
        pa, pb = a.get("tabpfn_price"), b.get("tabpfn_price")
        if pa is not None and pb is not None and actual:
            deltas.append(abs(pa - pb) / actual)
        if a.get("verdict") == b.get("verdict"):
            verdict_agree += 1
    result = {
        "modes": modes,
        "n_common": len(common),
        "mean_abs_delta_tabpfn_over_actual": float(np.mean(deltas)) if deltas else None,
        "median_abs_delta_tabpfn_over_actual": float(np.median(deltas)) if deltas else None,
        "verdict_agreement_rate": (verdict_agree / len(common)) if common else None,
    }
    (out_dir / "compare.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db-url", default=DEFAULT_DB_URL)
    ap.add_argument("--mode", choices=["loo", "holdout"], default="loo",
                     help="정보용 라벨 — DB status 토글은 build_eval_db.py --holdout이 담당")
    ap.add_argument("--test-ids", default=str(DEFAULT_TEST_IDS))
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--out", default=str(DEFAULT_OUT_DIR / "eval"))
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resume", action="store_true", help="cases_<mode>.jsonl에 이미 있는 id는 건너뜀")
    ap.add_argument("--compare", nargs=2, metavar=("MODE_A", "MODE_B"),
                     help="진단을 돌리지 않고 두 모드의 cases 파일을 비교")
    args = ap.parse_args()

    out_dir = pathlib.Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.compare:
        do_compare(out_dir, args.compare)
        return

    import os
    os.environ.setdefault("DATABASE_URL", args.db_url)
    from app import market_price  # noqa: F401  — import 자체가 되는지 여기서 먼저 확인

    test_items = json.loads(pathlib.Path(args.test_ids).read_text(encoding="utf-8"))
    cases_path = out_dir / f"cases_{args.mode}.jsonl"

    done_ids = set()
    if args.resume:
        done_ids = {c["listing_id"] for c in read_jsonl(cases_path)}
    elif cases_path.exists():
        cases_path.unlink()  # 새로 시작 — append 전제와 충돌하지 않게 이전 파일을 비운다

    todo = [t for t in test_items if t["listing_id"] not in done_ids]
    if args.limit is not None:
        todo = todo[: args.limit]

    option_lookup = load_option_choice_counts(pathlib.Path(args.csv))

    with psycopg.connect(args.db_url, row_factory=dict_row, autocommit=True) as conn:
        fits_slug_fuel, fits_slug = build_regression_fits(conn, option_lookup)
        print(f"회귀 기준선 fit: (target_slug,fuel) {len(fits_slug_fuel)}개군, target_slug {len(fits_slug)}개군")
        for i, item in enumerate(todo, 1):
            record = run_case(conn, item, option_lookup, fits_slug_fuel, fits_slug)
            append_jsonl(cases_path, record)
            print(f"[{i}/{len(todo)}] {item['encar_id']} elapsed={record.get('elapsed_s', 0):.2f}s "
                  f"tabpfn={record.get('tabpfn_price')} train_n={record.get('train_n')} "
                  f"comps_n={record.get('comps_n')}")

    all_cases = read_jsonl(cases_path)
    metrics = compute_metrics(all_cases, args.mode)
    (out_dir / f"metrics_{args.mode}.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    write_cases_csv(all_cases, out_dir / f"cases_{args.mode}.csv")
    print(f"완료: 누적 {len(all_cases)}건 → {cases_path}")
    print(json.dumps(metrics["overall"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
