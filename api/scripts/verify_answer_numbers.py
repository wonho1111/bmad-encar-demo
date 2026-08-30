"""LLM 설명문(run_search_agent의 answer) 수치 대조기 — LangSmith REST로 최근 런을 가져와,
answer 안의 금액·퍼센트 언급이 실제로 도구가 돌려준 값에 근거하는지 대조한다(환각 탐지).

키는 api/.env의 LANGCHAIN_API_KEY를 config.py와 동일한 방식(dotenv_values)으로 읽는다 —
os.environ 승격(config._promote_env_from_dotenv)에 기대지 않고 이 스크립트가 직접 읽는다
(이 스크립트는 app.config를 import하지 않는다 — LangSmith REST 호출만 하면 되므로 앱의
다른 설정 부담을 지지 않는다, 단순함 우선).

대조 대상: name="run_search_agent" 이면서 parent_run_id가 없는(=루트) 런만 본다 — 그래야
outputs가 run_search_agent의 반환 계약({answer, listings, market_diagnosis, ...})과 일치한다.
자식 런(ChatGoogleGenerativeAI·개별 도구 호출 등)은 이 계약을 안 따르므로 대상에서 뺀다.

허용 집합: market_diagnosis의 {listing.price, stats 5종(min/q1/median/q3/max), tabpfn.price,
comps[].price} + listings[].price + 그 값들 중 임의 두 값의 차(파생값, 퍼센트 계산용 값은
파생에서 제외). 만원 단위 반올림 오차 ±1만원(10,000원)까지는 같은 값으로 본다.

퍼센트는 별도 계산식 3가지(percentile*100, (price-median)/median*100, (price-tabpfn)/tabpfn*100)
와 ±1%p 오차 안에서만 "확인"으로 치고, 그 외 퍼센트 언급은 위반이 아니라 "미확인"으로만
집계한다(연식 등 이 스크립트가 모르는 다른 %가 답변에 나올 수 있음 — 스펙 명시).

사용법:
  api/.venv/bin/python api/scripts/verify_answer_numbers.py --limit 15
"""

import argparse
import itertools
import re
import sys

import requests
from dotenv import dotenv_values

_ENDPOINT = "https://api.smith.langchain.com"
_MONEY_TOLERANCE_WON = 10_000
_PERCENT_TOLERANCE_PP = 1.0

# "1,546만" / "1,546만원" / "1,546만 원" / "13,475,000원" / "약 90만 원" 을 모두 잡는다.
# man 그룹이 잡히면 "만" 단위(× 10,000), 아니면 "원" 앞의 숫자를 그대로 원 단위로 본다.
# (?!\s*km): "3만km"·"5만km"(LADDER 사다리 desc의 주행거리 밴드 표기, 실측으로 발견한 오탐 —
#   "만" 뒤에 "원"이 없으면 금액인지 거리 단위(만km)인지 구별이 안 되므로, 적어도 바로 뒤에
#   "km"가 오는 경우는 거리로 보고 배제한다.
_MONEY_RE = re.compile(r"(?P<num>\d[\d,]*)(?:\s*(?P<man>만)(?!\s*km)\s*원?|\s*원)")

# "-24.5%" / "−24.5%"(유니코드 마이너스) / "하위 30%"
_PERCENT_RE = re.compile(r"(?P<sign>[−\-]?)(?P<num>\d+(?:\.\d+)?)\s*%")


def parse_money_mentions(text: str) -> list[int]:
    """answer 텍스트에서 금액 언급을 원 단위 정수 리스트로 뽑아낸다.

    >>> parse_money_mentions("1,546만원짜리와 1,546만 매물, 13,475,000원, 약 90만 원")
    [15460000, 15460000, 13475000, 900000]
    >>> parse_money_mentions("주행 ±3만km 이내, 가격은 1,546만원")
    [15460000]
    """
    out = []
    for m in _MONEY_RE.finditer(text):
        num = int(m.group("num").replace(",", ""))
        if m.group("man"):
            num *= 10_000
        out.append(num)
    return out


def parse_percent_mentions(text: str) -> list[float]:
    """answer 텍스트에서 퍼센트 언급을 부호 있는 float 리스트로 뽑아낸다.

    >>> parse_percent_mentions("−24.5%, 하위 30%, 약 -5%")
    [-24.5, 30.0, -5.0]
    """
    out = []
    for m in _PERCENT_RE.finditer(text):
        val = float(m.group("num"))
        if m.group("sign") in ("-", "−"):
            val = -val
        out.append(val)
    return out


def _collect_allowed_money(market_diagnosis, listings):
    """대조 허용 금액 집합(파생값 포함)을 만든다. 파생값은 두 값의 절대차(diff)만 추가한다."""
    base = set()
    if market_diagnosis:
        listing = market_diagnosis.get("listing") or {}
        if listing.get("price") is not None:
            base.add(listing["price"])
        stats = market_diagnosis.get("stats")
        if stats:
            for key in ("min", "q1", "median", "q3", "max"):
                if stats.get(key) is not None:
                    base.add(round(stats[key]))
        tabpfn = market_diagnosis.get("tabpfn") or {}
        if tabpfn.get("price") is not None:
            base.add(tabpfn["price"])
        for comp in market_diagnosis.get("comps") or []:
            if comp.get("price") is not None:
                base.add(comp["price"])
    for listing in listings or []:
        if listing.get("price") is not None:
            base.add(listing["price"])

    derived = {abs(a - b) for a, b in itertools.combinations(base, 2)}
    return base | derived


def _money_is_allowed(candidate, allowed):
    return any(abs(candidate - v) <= _MONEY_TOLERANCE_WON for v in allowed)


def _percent_reference_values(market_diagnosis):
    """퍼센트 대조용 계산값 3가지(있는 것만) — percentile*100, (price-median)/median*100,
    (price-tabpfn)/tabpfn*100."""
    if not market_diagnosis:
        return []
    refs = []
    percentile = market_diagnosis.get("percentile")
    if percentile is not None:
        refs.append(round(percentile * 100, 2))

    listing = market_diagnosis.get("listing") or {}
    price = listing.get("price")
    stats = market_diagnosis.get("stats") or {}
    median = stats.get("median")
    if price is not None and median:
        refs.append((price - median) / median * 100)

    tabpfn_price = (market_diagnosis.get("tabpfn") or {}).get("price")
    if price is not None and tabpfn_price:
        refs.append((price - tabpfn_price) / tabpfn_price * 100)

    return refs


def _percent_is_confirmed(candidate, refs):
    return any(abs(candidate - r) <= _PERCENT_TOLERANCE_PP for r in refs)


def _context(text, idx, span=20):
    start = max(0, idx - span // 2)
    return text[start:start + span]


def evaluate_run(run: dict) -> dict:
    """런 1건을 판정한다. outputs가 없으면 status="skip". 그 외는 "clean"/"suspect"."""
    outputs = run.get("outputs")
    if not outputs:
        return {"run_id": run["id"], "start_time": run.get("start_time"), "status": "skip", "reason": "outputs 없음"}

    answer = outputs.get("answer") or ""
    market_diagnosis = outputs.get("market_diagnosis")
    listings = outputs.get("listings") or []

    allowed_money = _collect_allowed_money(market_diagnosis, listings)
    percent_refs = _percent_reference_values(market_diagnosis)

    money_hits = parse_money_mentions(answer)
    percent_hits = parse_percent_mentions(answer)

    suspects = []
    for val in money_hits:
        if not _money_is_allowed(val, allowed_money):
            idx = answer.find(str(val))  # 원문 위치 근사(정규화 전 표기와 다를 수 있어 근사치)
            suspects.append({"kind": "money", "value": val, "context": _context(answer, max(idx, 0))})

    percent_confirmed = 0
    percent_unconfirmed = 0
    for val in percent_hits:
        if _percent_is_confirmed(val, percent_refs):
            percent_confirmed += 1
        else:
            percent_unconfirmed += 1

    status = "suspect" if suspects else "clean"
    return {
        "run_id": run["id"],
        "start_time": run.get("start_time"),
        "status": status,
        "money_checked": len(money_hits),
        "money_suspects": suspects,
        "percent_checked": len(percent_hits),
        "percent_confirmed": percent_confirmed,
        "percent_unconfirmed": percent_unconfirmed,
        "has_market_diagnosis": market_diagnosis is not None,
    }


def _api_key() -> str:
    values = dotenv_values(".env")
    key = values.get("LANGCHAIN_API_KEY")
    if not key:
        raise RuntimeError("api/.env에 LANGCHAIN_API_KEY가 없습니다.")
    return key


def _fetch_sessions(key: str) -> list[str]:
    resp = requests.get(f"{_ENDPOINT}/sessions", headers={"x-api-key": key}, params={"limit": 100}, timeout=30)
    resp.raise_for_status()
    return [s["id"] for s in resp.json()]


def fetch_recent_root_runs(limit: int) -> list[dict]:
    """모든 프로젝트(session)를 통틀어 name="run_search_agent"인 루트 런 최근 limit건.

    LangSmith REST는 페이지당 limit<=100 제약이 있다(실측 확인) — limit>100 요청은 100으로
    자른다(전수 페이지네이션은 이 스크립트 용도(최근 N건 훑기)에 불필요, A2 단순함 우선).
    """
    key = _api_key()
    sessions = _fetch_sessions(key)
    body = {
        "session": sessions,
        "filter": 'and(eq(name, "run_search_agent"), eq(is_root, true))',
        "limit": min(limit, 100),
        "order": "desc",
        "select": ["id", "name", "start_time", "parent_run_id", "outputs", "inputs"],
    }
    resp = requests.post(
        f"{_ENDPOINT}/runs/query", json=body, headers={"x-api-key": key, "Content-Type": "application/json"}, timeout=60
    )
    resp.raise_for_status()
    runs = resp.json().get("runs", [])
    # 서버 필터를 신뢰하되, parent_run_id는 클라이언트에서 한 번 더 확인한다(독립 이중 확인).
    return [r for r in runs if r.get("parent_run_id") is None][:limit]


def print_report(results: list[dict]):
    print(f"\n{'run_id':<38}{'시각':<22}{'판정':<10}{'금액검사':>8}{'금액의심':>8}{'%검사':>7}{'%확인':>6}{'%미확인':>8}")
    for r in results:
        if r["status"] == "skip":
            print(f"{r['run_id']:<38}{str(r['start_time']):<22}{'skip':<10}(outputs 없음)")
            continue
        print(
            f"{r['run_id']:<38}{str(r['start_time']):<22}{r['status']:<10}"
            f"{r['money_checked']:>8}{len(r['money_suspects']):>8}"
            f"{r['percent_checked']:>7}{r['percent_confirmed']:>6}{r['percent_unconfirmed']:>8}"
        )

    suspects = [r for r in results if r["status"] == "suspect"]
    if suspects:
        print("\n의심 상세:")
        for r in suspects:
            for s in r["money_suspects"]:
                print(f"  run={r['run_id']} time={r['start_time']} 값={s['value']:,}원 문맥='{s['context']}'")

    clean = sum(1 for r in results if r["status"] == "clean")
    suspect = len(suspects)
    skip = sum(1 for r in results if r["status"] == "skip")
    print(f"\n총계: clean={clean} 의심={suspect} 스킵={skip} (전체 {len(results)}건)")


def main():
    ap = argparse.ArgumentParser(description="LangSmith run_search_agent 최근 런 수치 대조기")
    ap.add_argument("--limit", type=int, default=20, help="가져올 최근 루트 런 수(기본 20)")
    args = ap.parse_args()

    runs = fetch_recent_root_runs(args.limit)
    print(f"[verify_answer_numbers] 루트 런 {len(runs)}건 조회됨", file=sys.stderr)

    results = [evaluate_run(r) for r in runs]
    print_report(results)

    sys.exit(1 if any(r["status"] == "suspect" for r in results) else 0)


if __name__ == "__main__":
    main()
