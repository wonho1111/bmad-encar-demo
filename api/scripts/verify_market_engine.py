"""시세 진단 엔진(app/market_price.diagnose) 전수 불변식 스윕.

on_sale 매물 전체(또는 --sample N 표본)에 diagnose()를 실제로 돌려, 결과가 지켜야 할
불변식(invariant) 8개(I1~I8)를 매 결과마다 검사한다. 위반이 있으면 고치지 않고 원자료
그대로 위반 목록에 담는다 — 이 스크립트의 역할은 "잡는다"까지고, 판단은 상위 세션 몫이다.

⚠️ 독립 계산 원칙(자기일관 단언 금지): I4·I7·I8은 diagnose()가 이미 계산해 돌려준 값을
  다시 인용해 자기 자신과 비교하지 않는다. LADDER 선언(dict)과 comp id로 별도 SELECT한
  원자료만으로 기대값을 처음부터 다시 계산한다 — diagnose 내부 헬퍼(_verdict·_base_model
  등)를 불러 "기대값"을 만들면, 그 헬퍼 자체가 잘못됐을 때 검사가 항상 통과해버린다
  (같은 이유로 _base_model_independent를 이 파일에 별도로 재구현했다 — market_price에서
  import하지 않는다).

DB 접근은 app.db.readonly.readonly_connection()(SELECT만 가능한 ai_readonly 롤) 하나만
쓴다 — 매물별로 production 라우터(app/routers/market_price.py)와 동일하게 "요청마다 새
readonly_connection()" 패턴을 따른다(긴 트랜잭션 하나로 290건을 묶지 않는다).

사용법:
  api/.venv/bin/python api/scripts/verify_market_engine.py                # 전수
  api/.venv/bin/python api/scripts/verify_market_engine.py --sample 60    # 표본(시드 고정)
"""

import argparse
import itertools
import re
import sys

from psycopg.rows import dict_row

sys.path.insert(0, ".")

from app.db.readonly import close_pool, readonly_connection  # noqa: E402
from app.market_price import LADDER, MAX_COMPS  # noqa: E402

# ── I8 파라미터: 이 단(step) 이하는 "세대(모델 완전 일치) 순도"를 요구한다(세대 오염 검사).
#   LADDER[0..2]는 model="exact"로 선언돼 있어 원래도 세대가 섞이면 안 된다 — 오늘 실측
#   이슈(비교군에 다른 세대가 섞여 나온 사례)를 잡기 위한 별도 검사다. red 증명 시에만
#   4로 일시 변경해 세대 해제 단(3~4)까지 "순도"를 요구하도록 만들어 검사가 실제로 위반을
#   잡는지 확인한다(고의로 틀린 기대를 만들어 검사기 자체를 시험) — 확인 후 반드시 2로 원복.
_GENERATION_PURITY_MAX_STEP = 2

# I6 퍼센타일 정합 검사의 허용 오차(부동소수 비교이므로 완전 0 대신 아주 작은 epsilon).
_PERCENTILE_EPS = 1e-6

# I7 note 형식: "기본 모델군 N건 학습"
_TABPFN_NOTE_RE = re.compile(r"^기본 모델군 (\d+)건 학습$")

# market_price._GENERATION_PREFIXES와 동일한 값 — 독립 재계산을 위해 그대로 복제한다
# (import하지 않는 이유는 모듈 docstring 참조).
_GENERATION_PREFIXES = ("더 뉴 ", "올 뉴 ")

# market_price._DISPLACEMENT_SUFFIX_RE와 동일한 값 — I9(트림 해제 순도) 독립 재계산용.
_DISPLACEMENT_SUFFIX_RE = re.compile(r"^\d\.\d$")

# verdict 새 기준(±5%, market_price._verdict_by_fair_price)의 독립 재계산용 — I5.
_FAIR_PRICE_TOLERANCE = 0.05


def _family_model_independent(model: str) -> str:
    """market_price._family_model과 동일 알고리즘을 별도로 재구현한 것(독립 계산 원칙).

    >>> _family_model_independent("더 뉴 그랜저 IG 3.3")
    '더 뉴 그랜저 IG'
    >>> _family_model_independent("아반떼 CN7 하이브리드")
    '아반떼 CN7 하이브리드'
    """
    tokens = model.split()
    if tokens and _DISPLACEMENT_SUFFIX_RE.match(tokens[-1]):
        return " ".join(tokens[:-1])
    return model


def _base_model_independent(model: str) -> str:
    """market_price._base_model과 동일 알고리즘을 별도로 재구현한 것(독립 계산 원칙).

    >>> _base_model_independent("더 뉴 그랜저 IG")
    '그랜저'
    >>> _base_model_independent("올 뉴 쏘렌토")
    '쏘렌토'
    >>> _base_model_independent("아반떼 CN7")
    '아반떼'
    """
    stripped = model
    for prefix in _GENERATION_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    tokens = stripped.split()
    return tokens[0] if tokens else stripped


def _new_counter():
    return {"checked": 0, "skipped": 0, "violated": 0}


INVARIANT_IDS = ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9"]


class Sweep:
    def __init__(self):
        self.counters = {code: _new_counter() for code in INVARIANT_IDS}
        self.violations = []  # [{listing_id, invariant, detail}]
        self.total = 0

    def record(self, code, listing_id, ok, detail=None, skipped=False):
        c = self.counters[code]
        if skipped:
            c["skipped"] += 1
            return
        c["checked"] += 1
        if not ok:
            c["violated"] += 1
            self.violations.append({"listing_id": listing_id, "invariant": code, "detail": detail})


def _fetch_targets(conn, sample, seed):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, model, year, mileage, transmission, fuel, accident_free, price "
            "FROM public.listings WHERE status = 'on_sale' ORDER BY id"
        )
        rows = cur.fetchall()
    if sample:
        import random

        rng = random.Random(seed)
        rows = rng.sample(rows, min(sample, len(rows)))
    return rows


def _fetch_comp_raw(conn, comp_ids):
    if not comp_ids:
        return {}
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT id, model, year, mileage, fuel, accident_status FROM public.listings "
            "WHERE id = ANY(%s::uuid[])",
            ([str(c) for c in comp_ids],),
        )
        rows = cur.fetchall()
    return {str(r["id"]): r for r in rows}


def _fetch_base_group_range(conn, target, base_name):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT min(price) AS lo, max(price) AS hi, count(*) AS cnt FROM public.listings "
            "WHERE status = 'on_sale' AND id <> %s AND transmission = %s AND model ILIKE %s",
            (str(target["id"]), target["transmission"], f"%{base_name}%"),
        )
        return cur.fetchone()


def _check_i1(sweep, listing_id, stats):
    if stats is None:
        sweep.record("I1", listing_id, True, skipped=True)
        return
    ok = stats["min"] <= stats["q1"] <= stats["median"] <= stats["q3"] <= stats["max"]
    sweep.record("I1", listing_id, ok, detail=stats if not ok else None)


def _check_i2(sweep, listing_id, sample_count, stats, percentile, verdict):
    if sample_count >= 1:
        ok = stats is not None and percentile is not None and verdict is not None
    else:
        ok = stats is None and percentile is None and verdict is None
    detail = None
    if not ok:
        detail = {
            "sample_count": sample_count,
            "stats_is_none": stats is None,
            "percentile_is_none": percentile is None,
            "verdict_is_none": verdict is None,
        }
    sweep.record("I2", listing_id, ok, detail=detail)


def _check_i3(sweep, listing_id, sample_count, comps, target_id):
    expected_len = min(sample_count, MAX_COMPS)
    len_ok = len(comps) == expected_len
    no_self = all(c["id"] != str(target_id) for c in comps)
    ok = len_ok and no_self
    detail = None
    if not ok:
        detail = {
            "expected_len": expected_len,
            "actual_len": len(comps),
            "contains_target": not no_self,
        }
    sweep.record("I3", listing_id, ok, detail=detail)


def _check_i4(sweep, listing_id, rung, target, comps, comp_raw_map, base_name, family_name):
    """멈춘 단(rung)의 선언 조건을 comps 전원이 실제로 만족하는지 원자료로 독립 검사."""
    bad = []
    for c in comps:
        raw = comp_raw_map.get(c["id"])
        if raw is None:
            bad.append({"comp_id": c["id"], "reason": "raw_row_not_found"})
            continue

        if rung["model"] == "exact":
            if raw["model"] != target["model"]:
                bad.append({"comp_id": c["id"], "reason": "model_exact", "actual": raw["model"]})
        elif rung["model"] == "family":
            if not raw["model"].startswith(family_name):
                bad.append({"comp_id": c["id"], "reason": "model_family_prefix", "actual": raw["model"]})
        else:  # "base"
            if base_name not in raw["model"]:
                bad.append({"comp_id": c["id"], "reason": "model_base_substr", "actual": raw["model"]})

        if rung["fuel"] and raw["fuel"] != target["fuel"]:
            bad.append({"comp_id": c["id"], "reason": "fuel", "actual": raw["fuel"]})

        if rung["accident"]:
            if target["accident_free"]:
                if raw["accident_status"] != "무사고":
                    bad.append({"comp_id": c["id"], "reason": "accident_free_expected", "actual": raw["accident_status"]})
            else:
                if raw["accident_status"] is None or raw["accident_status"] == "무사고":
                    bad.append({"comp_id": c["id"], "reason": "accident_not_free_expected", "actual": raw["accident_status"]})

        if abs(raw["year"] - target["year"]) > rung["year_band"]:
            bad.append({"comp_id": c["id"], "reason": "year_band", "actual": raw["year"]})

        if abs(raw["mileage"] - target["mileage"]) > rung["km_band"]:
            bad.append({"comp_id": c["id"], "reason": "km_band", "actual": raw["mileage"]})

    ok = not bad
    sweep.record("I4", listing_id, ok, detail=bad[:5] if bad else None)


def _check_i5(sweep, listing_id, price, stats, verdict, verdict_basis, tabpfn_price):
    """verdict 정합 — 2026-08-31 판정 기준 전환(사용자 승인) 반영.

    tabpfn 적정가가 있으면(verdict_basis="적정가") ±5% 괴리율로, 없으면(stats 있고
    verdict_basis="사분위") 기존 사분위(q1/q3)로 독립 재계산해 비교한다. 둘 다 없으면
    (sample_count==0, stats도 tabpfn도 없음) verdict가 None이어야 정상이라 스킵한다.
    """
    if stats is None and tabpfn_price is None:
        sweep.record("I5", listing_id, True, skipped=True)
        return
    if tabpfn_price is not None:
        diff = (price - tabpfn_price) / tabpfn_price
        if diff < -_FAIR_PRICE_TOLERANCE:
            expected = "저렴"
        elif diff > _FAIR_PRICE_TOLERANCE:
            expected = "높음"
        else:
            expected = "적정"
        expected_basis = "적정가"
    else:
        if price < stats["q1"]:
            expected = "저렴"
        elif price > stats["q3"]:
            expected = "높음"
        else:
            expected = "적정"
        expected_basis = "사분위"
    ok = verdict == expected and verdict_basis == expected_basis
    detail = None
    if not ok:
        detail = {
            "price": price, "tabpfn_price": tabpfn_price,
            "stats": stats, "expected": expected, "actual": verdict,
            "expected_basis": expected_basis, "actual_basis": verdict_basis,
        }
    sweep.record("I5", listing_id, ok, detail=detail)


def _check_i6(sweep, listing_id, price, sample_count, comps, percentile):
    if percentile is None or sample_count > MAX_COMPS or sample_count != len(comps):
        # comps가 60건 컷에 걸려 전수가 아니면 comps만으로 백분위를 재계산할 수 없다 — 스킵.
        sweep.record("I6", listing_id, True, skipped=True)
        return
    if sample_count == 0:
        sweep.record("I6", listing_id, True, skipped=True)
        return
    expected = sum(1 for c in comps if c["price"] <= price) / sample_count
    diff = abs(percentile - expected)
    ok = diff <= _PERCENTILE_EPS
    detail = None
    if not ok:
        detail = {"expected": expected, "actual": percentile, "diff": diff}
    sweep.record("I6", listing_id, ok, detail=detail)


def _check_i7(sweep, listing_id, tabpfn, conn, target, base_name):
    price = tabpfn.get("price")
    note = tabpfn.get("note")
    if price is None:
        sweep.record("I7", listing_id, True, skipped=True)
        return

    problems = []
    if not (isinstance(price, int) and price > 0):
        problems.append(f"price가 양수 정수가 아님: {price!r}")
    elif price % 10_000 != 0:
        problems.append(f"price가 만원 단위가 아님: {price}")

    m = _TABPFN_NOTE_RE.match(note or "")
    if not m:
        problems.append(f"note 형식 불일치: {note!r}")
    else:
        n = int(m.group(1))
        if n < 10:
            problems.append(f"note의 N이 10 미만: {n}")

    rng = _fetch_base_group_range(conn, target, base_name)
    if not rng or rng["lo"] is None:
        problems.append("기본 모델군 SELECT 결과 없음(범위 산정 불가)")
    else:
        lo_bound = rng["lo"] * 0.5
        hi_bound = rng["hi"] * 1.5
        if not (lo_bound <= price <= hi_bound):
            problems.append(
                f"price({price})가 기본 모델군 범위[{rng['lo']}~{rng['hi']}]의 "
                f"0.5~1.5배({lo_bound}~{hi_bound}) 밖"
            )

    ok = not problems
    sweep.record("I7", listing_id, ok, detail=problems if problems else None)


def _check_i8(sweep, listing_id, step, comps, comp_raw_map, target):
    if step > _GENERATION_PURITY_MAX_STEP:
        sweep.record("I8", listing_id, True, skipped=True)
        return
    bad = []
    for c in comps:
        raw = comp_raw_map.get(c["id"])
        model = raw["model"] if raw else c["model"]
        if model != target["model"]:
            bad.append({"comp_id": c["id"], "model": model})
    ok = not bad
    sweep.record("I8", listing_id, ok, detail={"step": step, "contaminants": bad[:5]} if bad else None)


# I9 파라미터 — "트림 해제(동일 세대 계열)" 단(LADDER step 3)의 순도 검사. exact 단(0~2)의
# 세대 순도(I8)와 별개로, 트림 해제 단이 실제로 "동일 세대"만 넓히고 다른 세대(예: GN7)를
# 끌어오지 않는지 확인한다(2026-08-31 신설, P4 실측 결함 재발 방지).
_TRIM_RELEASE_STEP = 3


def _check_i9(sweep, listing_id, step, comps, comp_raw_map, family_name):
    if step != _TRIM_RELEASE_STEP:
        sweep.record("I9", listing_id, True, skipped=True)
        return
    bad = []
    for c in comps:
        raw = comp_raw_map.get(c["id"])
        model = raw["model"] if raw else c["model"]
        if not model.startswith(family_name):
            bad.append({"comp_id": c["id"], "model": model})
    ok = not bad
    sweep.record("I9", listing_id, ok, detail={"family_name": family_name, "contaminants": bad[:5]} if bad else None)


def run_sweep(sample, seed):
    from app.market_price import diagnose

    sweep = Sweep()
    with readonly_connection() as conn:
        targets = _fetch_targets(conn, sample, seed)
    sweep.total = len(targets)
    print(f"[verify_market_engine] 대상 {sweep.total}건 검사 시작", file=sys.stderr)

    for i, target in enumerate(targets, start=1):
        listing_id = str(target["id"])
        with readonly_connection() as conn:
            result = diagnose(listing_id, conn)
            if result is None:
                print(f"[verify_market_engine] 경고: {listing_id} diagnose 결과 없음(스킵)", file=sys.stderr)
                continue

            criteria = result["criteria"]
            stats = result["stats"]
            percentile = result["percentile"]
            verdict = result["verdict"]
            verdict_basis = result["verdict_basis"]
            comps = result["comps"]
            tabpfn = result["tabpfn"]
            sample_count = criteria["sample_count"]
            step = criteria["step"]
            rung = LADDER[step]
            base_name = _base_model_independent(target["model"])
            family_name = _family_model_independent(target["model"])

            comp_raw_map = _fetch_comp_raw(conn, [c["id"] for c in comps])

            _check_i1(sweep, listing_id, stats)
            _check_i2(sweep, listing_id, sample_count, stats, percentile, verdict)
            _check_i3(sweep, listing_id, sample_count, comps, target["id"])
            _check_i4(sweep, listing_id, rung, target, comps, comp_raw_map, base_name, family_name)
            _check_i5(sweep, listing_id, target["price"], stats, verdict, verdict_basis, tabpfn.get("price"))
            _check_i6(sweep, listing_id, target["price"], sample_count, comps, percentile)
            _check_i7(sweep, listing_id, tabpfn, conn, target, base_name)
            _check_i8(sweep, listing_id, step, comps, comp_raw_map, target)
            _check_i9(sweep, listing_id, step, comps, comp_raw_map, family_name)

        if i % 10 == 0 or i == sweep.total:
            print(f"[verify_market_engine] 진행 {i}/{sweep.total}", file=sys.stderr)

    return sweep


def print_report(sweep):
    print(f"\n총 검사 매물 수: {sweep.total}")
    print(f"{'불변식':<6}{'검사':>8}{'스킵':>8}{'위반':>8}")
    for code in INVARIANT_IDS:
        c = sweep.counters[code]
        print(f"{code:<6}{c['checked']:>8}{c['skipped']:>8}{c['violated']:>8}")

    total_violations = len(sweep.violations)
    print(f"\n총 위반 건수: {total_violations}")
    if total_violations:
        print("\n위반 상세(최대 20건):")
        for v in sweep.violations[:20]:
            print(f"  [{v['invariant']}] listing={v['listing_id']} detail={v['detail']}")
        if total_violations > 20:
            print(f"  ... 외 {total_violations - 20}건 생략")


def main():
    ap = argparse.ArgumentParser(description="시세 진단 엔진(diagnose) 전수 불변식 스윕")
    ap.add_argument("--sample", type=int, default=None, help="표본 수(미지정 시 전수 검사)")
    ap.add_argument("--seed", type=int, default=20260831, help="표본 랜덤 시드(기본 고정값)")
    args = ap.parse_args()

    sweep = run_sweep(args.sample, args.seed)
    print_report(sweep)
    close_pool()  # 인터프리터 종료 시 psycopg_pool의 백그라운드 스레드 조인 에러 방지

    sys.exit(1 if sweep.violations else 0)


if __name__ == "__main__":
    main()
