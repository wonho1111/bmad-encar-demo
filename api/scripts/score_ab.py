"""Phase B 채점 모듈 — A/B 모델 raw 결과를 골든셋과 대조해 점수·승부를 낸다.

역할(일회성 하니스):
  · predicate → 골든 SQL 생성(exact_ids 금지, 데이터 변해도 즉석 재생성) → 정답 결과집합(id 집합).
  · 경로별 채점: A=결과집합 정확도(precision/F1·Jaccard), B=라우팅+가이드 인용 recall, C=라우팅+거절.
  · 게이트: 멀티턴 오염(must_not_contain) 0건 · dead-end 0% — 위반 모델은 자격 탈락.
  · 사전식 승부: ①결과집합 → ②라우팅 → ③flaky → ④비용 → ⑤지연 (가중합 금지, party-mode 안건4).
  · 베이스라인 회귀 게이트: 후보가 베이스라인보다 결과정확도 하락 시 채택 불가.

순수 함수(build_golden_sql·jaccard·f1·score_path_a·lexicographic_winner)는 test_ab_scoring.py가
  라이브 API 없이 단위 검증한다. DB 조회(골든 실행)는 app.db.readonly.run_select(ai_readonly)를 쓴다.

실행(2파일 — A/B 비교, 사전식 승부·회귀 게이트 포함):
  api/ 에서  .venv/Scripts/python.exe scripts/score_ab.py \
          --queryset docs/ai-ab-test-queryset.json \
          --raw docs/ab-eval-raw-gemini-3.1-flash-lite.json docs/ab-eval-raw-gemini-2.5-flash-lite.json \
          --out docs/ab-eval-report.json

실행(1파일 — baseline 단독 기록, A/B 비교·회귀 게이트 없음. G2 baseline·13.1):
  api/ 에서  .venv/Scripts/python.exe scripts/score_ab.py \
          --queryset docs/ai-ab-test-queryset.json \
          --raw docs/g2-baseline-partial.json \
          --out docs/g2-baseline-report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

# 앱 기본 매물 개수(경로 A/B 공통 LIMIT). 결과집합 채점에서 "보여준 개수 상한"으로 쓴다.
try:
    from app.db.sql_guard import DEFAULT_LIMIT  # noqa: E402
except Exception:  # 단위테스트 등 앱 미로딩 환경 폴백
    DEFAULT_LIMIT = 5

# 모델별 단가($/1M 토큰) — 비용(사전식 ④) 산정용. (입력, 출력)
PRICE_PER_M: dict[str, tuple[float, float]] = {
    "gemini-3.1-flash-lite": (0.25, 1.50),
    "gemini-2.5-flash-lite": (0.10, 0.40),
}

# 가이드 문서 stem → guide_documents.title (B경로 인용 recall 채점). 2026-06-23 실DB 기준.
DOC_STEM_TO_TITLE: dict[str, str] = {
    "01-차종별-특성": "차종별 특성과 용도 가이드",
    "02-패밀리카-적합-차종": "패밀리카로 무난한 차종 고르기",
    "03-초보운전자-적합-차종": "초보 운전자에게 적합한 차종",
    "04-연료별-유지비-연비": "연료별 유지비와 연비 특성",
    "05-중고차-신뢰성-체크포인트": "중고차 신뢰성과 구매 체크포인트",
    "06-차형-용어-매핑": "차형 용어 매핑 가이드 (세단·해치백·쿠페 등)",
    "07-전기차-충전-보조금": "전기차 충전·보조금·주행거리 이해",
    "10-사고이력-침수-판별": "사고이력·침수차·주행거리 조작 판별법",
    "11-주행거리-연식-판단": "적정 주행거리와 연식 판단 기준",
    "12-옵션-가치-판단": "옵션의 가치 판단",
}

# 거절(C) answer가 "갈림길"인지 — guard_node 고정 멘트의 유도 문구. 둘 중 하나라도 있으면 redirect.
REDIRECT_MARKERS = ("매물을 찾아드릴게요", "예산", "용도를 알려주시면")

# 카테고리형 컬럼(must_not_contain 오염 검사용) — 반환 매물의 실제 값을 DB에서 조회해 대조.
CATEGORICAL_COLUMNS = ("manufacturer", "body_type", "fuel", "color", "region", "transmission")


# ─────────────────────────────────────────────────────────────────────────
# 1) predicate → 골든 SQL (순수 함수, 파라미터 바인딩)
# ─────────────────────────────────────────────────────────────────────────
# 단일값 또는 list 허용(list면 IN). 키 → 컬럼·연산자 매핑.
_EQ_COLS = {"manufacturer", "body_type", "fuel", "color", "region", "transmission"}
_CMP = {
    "price_max": ("price", "<="), "price_min": ("price", ">="),
    "mileage_max": ("mileage", "<="), "mileage_min": ("mileage", ">="),
    "year_min": ("year", ">="), "year_max": ("year", "<="),
    "seats_min": ("seats", ">="), "seats_max": ("seats", "<="),
}
_VALID_ORDER = {"price ASC", "price DESC", "mileage ASC", "mileage DESC",
                "year ASC", "year DESC"}


def build_golden_sql(predicate: dict) -> tuple[str, list]:
    """predicate dict → (SQL, params). 항상 status='on_sale'. SELECT id만.

    지원 키: 카테고리 등호(manufacturer/body_type/fuel/color/region/transmission, 값 str|list),
      accident_free(bool), price/mileage/year/seats의 min·max, options_all(list, 각 =ANY(options)),
      order(화이트리스트), limit(int). 값은 전부 %s 파라미터로만 바인딩(인젝션 0).
    """
    conds = ["status = 'on_sale'"]
    params: list = []

    for col in _EQ_COLS:
        if col in predicate:
            val = predicate[col]
            if isinstance(val, (list, tuple)):
                conds.append(f"{col} = ANY(%s)")
                params.append(list(val))
            else:
                conds.append(f"{col} = %s")
                params.append(val)

    for key, (col, op) in _CMP.items():
        if key in predicate:
            conds.append(f"{col} {op} %s")
            params.append(predicate[key])

    if "accident_free" in predicate:
        conds.append("accident_free = %s")
        params.append(bool(predicate["accident_free"]))

    for opt in predicate.get("options_all", []) or []:
        conds.append("%s = ANY(options)")
        params.append(opt)

    sql = "SELECT id FROM listings WHERE " + " AND ".join(conds)

    order = predicate.get("order")
    if order:
        if order not in _VALID_ORDER:
            raise ValueError(f"order 화이트리스트 위반: {order!r}")
        sql += f" ORDER BY {order}"

    limit = predicate.get("limit")
    if limit is not None:
        sql += " LIMIT %s"
        params.append(int(limit))

    return sql, params


# ─────────────────────────────────────────────────────────────────────────
# 2) 집합 지표 (순수 함수)
# ─────────────────────────────────────────────────────────────────────────
def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 1.0


def precision_recall_f1(returned: set, golden: set) -> tuple[float, float, float]:
    """returned(앱이 보여준 id) vs golden(정답 전체 id)."""
    if not returned:
        # 둘 다 비면 완벽(정답이 0건인데 0건 반환). golden만 있으면 0.
        p = 1.0 if not golden else 0.0
        r = 1.0 if not golden else 0.0
        return p, r, (1.0 if not golden else 0.0)
    inter = len(returned & golden)
    p = inter / len(returned)
    r = inter / len(golden) if golden else 1.0
    f1 = (2 * p * r / (p + r)) if (p + r) else 0.0
    return p, r, f1


def score_path_a(returned_ids: list[str], golden_ids: set, predicate: dict) -> dict:
    """경로 A 결과집합 채점.

    · top-N 질의(predicate.limit 존재): 순서 포함 정확 일치(정렬 검증) → result=1.0/0.0.
    · 일반 필터: golden이 앱 LIMIT 이하면 F1(완전 비교), 초과면 precision(보여준 게 다 맞는지).
      precision은 "예산 초과/엉뚱한 차" 혼입을 직접 잡는 핵심 신호((가) SQL 정확도).
    """
    returned = list(returned_ids)
    rset = set(returned)
    golden = set(golden_ids)

    if predicate.get("limit") is not None and predicate.get("order"):
        # 정렬+상한 = 순서 민감. golden_ids는 이미 정렬·LIMIT 적용된 리스트 순서로 들어온다.
        gold_order = list(golden_ids)  # build 시 정렬 보존하려면 리스트로 넘겨야 함(아래 run_golden 참조)
        exact = returned[: len(gold_order)] == gold_order
        return {"mode": "topn", "result": 1.0 if exact else 0.0,
                "returned_n": len(returned), "golden_n": len(gold_order)}

    p, r, f1 = precision_recall_f1(rset, golden)
    j = jaccard(rset, golden)
    if len(golden) <= DEFAULT_LIMIT:
        return {"mode": "f1", "result": f1, "precision": p, "recall": r,
                "jaccard": j, "returned_n": len(rset), "golden_n": len(golden)}
    return {"mode": "precision", "result": p, "precision": p, "recall": r,
            "jaccard": j, "returned_n": len(rset), "golden_n": len(golden)}


def doc_hit(answer: str, doc_refs: list[str]) -> bool:
    """B경로: answer의 '(참고: <title>)'에 기대 가이드 제목이 들어있나(인용 recall)."""
    titles = [DOC_STEM_TO_TITLE.get(s, s) for s in (doc_refs or [])]
    return any(t and t in (answer or "") for t in titles)


def is_redirect(answer: str) -> bool:
    return any(m in (answer or "") for m in REDIRECT_MARKERS)


def route_ok(actual: str, primary: str, acceptable: list[str] | None) -> bool:
    allowed = set(acceptable or [primary]) | {primary}
    return actual in allowed


# ─────────────────────────────────────────────────────────────────────────
# 3) 골든 실행 (DB) — 순서 보존 위해 리스트 반환
# ─────────────────────────────────────────────────────────────────────────
def run_golden_ids(predicate: dict) -> list[str]:
    from app.db.readonly import run_select
    sql, params = build_golden_sql(predicate)
    rows = run_select(sql, tuple(params) if params else None)
    return [str(r[0]) for r in rows]


def fetch_attrs(ids: list[str]) -> list[dict]:
    """반환 매물의 카테고리 값+가격 조회(must_not_contain 오염 검사용)."""
    if not ids:
        return []
    from app.db.readonly import run_select
    cols = ", ".join(("id", *CATEGORICAL_COLUMNS, "price"))
    rows = run_select(
        f"SELECT {cols} FROM listings WHERE id = ANY(%s)", ([*ids],)
    )
    out = []
    for r in rows:
        d = {"id": str(r[0]), "price": r[-1]}
        for i, c in enumerate(CATEGORICAL_COLUMNS, start=1):
            d[c] = r[i]
        out.append(d)
    return out


def contamination_violations(returned_ids: list[str], must_not_contain: list[str],
                             pricey_floor: int | None) -> list[str]:
    """반환 매물이 금지 조건을 어겼으면 위반 사유 리스트(빈 리스트=깨끗)."""
    viols: list[str] = []
    attrs = fetch_attrs(returned_ids)
    forbidden = set(must_not_contain or [])
    # 금지 토큰 중 카테고리 값과 정확히 일치하는 것만 결정적으로 검사(예: '준중형차','중형차').
    for a in attrs:
        for col in CATEGORICAL_COLUMNS:
            if a.get(col) in forbidden:
                viols.append(f"{a['id']}: {col}={a[col]} (금지)")
        if pricey_floor is not None and a.get("price") is not None and a["price"] >= pricey_floor:
            viols.append(f"{a['id']}: price={a['price']} >= {pricey_floor} (소프트예산 위반)")
    return viols


# ─────────────────────────────────────────────────────────────────────────
# 4) 사전식 승부 (순수 함수)
# ─────────────────────────────────────────────────────────────────────────
JACCARD_DELTA = 0.15   # 결과집합 "낫다" 선언 최소차(안건4: 차이 클 때만)
ROUTING_DELTA = 5      # 라우팅 오답 개수 차 임계


def lexicographic_winner(sa: dict, sb: dict) -> dict:
    """두 모델 요약(summary)을 사전식으로 비교해 승자·근거를 반환.

    입력 summary 키: name, result_mean, routing_correct, flaky_n, cost_usd, latency_ms_mean,
      gate_pass(bool). 게이트 탈락 모델은 자동 패배. 동률(임계 미만)이면 다음 기준으로.
    선택 키(review pass 4): flaky_measured·tokens_measured(bool, 기본 True) — False면 그
      축(③flaky·④비용)을 승부에서 아예 건너뛴다. 측정 안 한 축을 동률·승리로 잘못 읽지
      않기 위함(예: run_phase_b.py의 N=1 러너는 flaky_n이 구조적으로 항상 0, tokens는
      하드코딩 0이라 두 값 다 "측정"이 아니라 "안 잼"이다).
    """
    a, b = sa["name"], sb["name"]
    # 0) 게이트
    if sa["gate_pass"] != sb["gate_pass"]:
        win = a if sa["gate_pass"] else b
        return {"winner": win, "reason": "게이트(오염/dead-end) — 상대 탈락", "tier": "gate"}
    if not sa["gate_pass"] and not sb["gate_pass"]:
        return {"winner": None, "reason": "양쪽 게이트 탈락 — 채택 불가", "tier": "gate"}

    # ① 결과집합 정확도
    d = sa["result_mean"] - sb["result_mean"]
    if abs(d) >= JACCARD_DELTA:
        return {"winner": a if d > 0 else b,
                "reason": f"결과집합 정확도 {sa['result_mean']:.3f} vs {sb['result_mean']:.3f}",
                "tier": "result"}
    # ② 라우팅
    dr = sa["routing_correct"] - sb["routing_correct"]
    if abs(dr) >= ROUTING_DELTA:
        return {"winner": a if dr > 0 else b,
                "reason": f"라우팅 정답 {sa['routing_correct']} vs {sb['routing_correct']}",
                "tier": "routing"}
    # ③ flaky (낮을수록 좋음) — 양쪽 다 실제로 N>1 반복 실행돼 측정됐을 때만 이 축으로 승부한다.
    # run_phase_b.py(G2 baseline 러너)는 N=1이라 flaky_n이 구조적으로 항상 0이다 — 측정 안 한
    # 축을 "완벽하다"로 읽으면 그 baseline이 진짜 N=3으로 측정된 상대를 자동으로 이긴다
    # (review pass 4). flaky_measured 키가 없는 구(旧) summary는 기본 True(기존 2파일 모드
    # 회귀 없음 — 그쪽은 실제로 N회 반복 측정한 raw를 쓴다는 전제).
    flaky_measured = sa.get("flaky_measured", True) and sb.get("flaky_measured", True)
    if flaky_measured and sa["flaky_n"] != sb["flaky_n"]:
        return {"winner": a if sa["flaky_n"] < sb["flaky_n"] else b,
                "reason": f"flaky {sa['flaky_n']} vs {sb['flaky_n']}", "tier": "flaky"}
    # ④ 비용 (낮을수록 좋음) — 토큰이 실측이 아니면(run_phase_b.py의 하드코딩 0) 이 축도 건너뛴다.
    # 0.0 비용은 "가장 쌈"으로 항상 이기거나, 반대로 우연히 상대도 0이면 조용히 묻힌다 —
    # 둘 다 조작된 결과다(review pass 4).
    tokens_measured = sa.get("tokens_measured", True) and sb.get("tokens_measured", True)
    if tokens_measured and abs(sa["cost_usd"] - sb["cost_usd"]) > 1e-9:
        return {"winner": a if sa["cost_usd"] < sb["cost_usd"] else b,
                "reason": f"비용 ${sa['cost_usd']:.4f} vs ${sb['cost_usd']:.4f}", "tier": "cost"}
    # ⑤ 지연 (낮을수록 좋음)
    if abs(sa["latency_ms_mean"] - sb["latency_ms_mean"]) > 1e-9:
        return {"winner": a if sa["latency_ms_mean"] < sb["latency_ms_mean"] else b,
                "reason": f"지연 {sa['latency_ms_mean']:.0f}ms vs {sb['latency_ms_mean']:.0f}ms",
                "tier": "latency"}
    return {"winner": None, "reason": "모든 기준 동률 — 더 싼 모델 권장(외부 판단)", "tier": "tie"}


# ─────────────────────────────────────────────────────────────────────────
# 5) 한 모델 raw → summary (DB 골든 필요)
# ─────────────────────────────────────────────────────────────────────────
def score_model(queryset: dict, raw: dict) -> dict:
    """raw(러너 출력)와 queryset을 대조해 모델 1개의 채점 summary를 만든다."""
    items = {it["id"]: it for it in queryset["items"]}
    model = raw["model"]
    per_item: list[dict] = []

    result_scores_clean_A: list[float] = []
    routing_correct = 0
    routing_total = 0
    flaky_n = 0
    flaky_measured = False  # N>1로 실제 반복 실행된 item이 하나라도 있어야 True(review pass 4)
    errored_n = 0
    contamination = 0
    soft_obs = 0
    deadend = 0
    total_in = total_out = 0
    latencies: list[float] = []

    for rid, runs in raw["results"].items():
        item = items.get(rid)
        if not item:
            continue
        gray = item.get("category") == "gray"

        # 429 등 라이브 실패로 `{"error": ...}`만 남은 run은 채점에서 제외한다(review pass 4 —
        # 이전엔 `r["route_last"]`를 무조건 인덱싱해 이 run이 하나만 섞여도 score_model 전체가
        # KeyError로 죽어, 이미 정상 캡처된 다른 항목까지 채점 자체가 불가능했다. 이건 정확히
        # DW-554가 우려하는 44개 전량 실행 중 일부 429 시나리오다).
        usable_runs = [r for r in runs if "error" not in r]
        if not usable_runs:
            errored_n += 1
            per_item.append({
                "id": rid, "category": item.get("category"), "kind": item.get("kind"),
                "error": (runs[0].get("error") if runs else "no runs recorded"),
            })
            continue

        # N회 실행 중 대표(첫 실행) + flaky 판정 — usable_runs만 본다(에러 run은 서명에서 제외).
        rep = usable_runs[0]
        if len(usable_runs) > 1:
            flaky_measured = True
        sigs = {(r["route_last"], tuple(r["ids_last"])) for r in usable_runs}
        is_flaky = len(sigs) > 1
        if is_flaky:
            flaky_n += 1
        for r in usable_runs:
            total_in += r.get("tokens_in", 0)
            total_out += r.get("tokens_out", 0)
            latencies.append(r.get("latency_ms", 0.0))

        rec: dict = {"id": rid, "category": item.get("category"), "kind": item["kind"],
                     "flaky": is_flaky}

        if item["kind"] == "single":
            primary = item["primary_path"]
            acc = item.get("acceptable_paths")
            r_ok = route_ok(rep["route_last"], primary, acc)
            rec["route"] = rep["route_last"]
            rec["route_ok"] = r_ok
            routing_total += 1
            if r_ok:
                routing_correct += 1

            if primary == "A":
                golden = run_golden_ids(item["predicate"])
                sc = score_path_a(rep["ids_last"], golden, item["predicate"])
                rec["score"] = sc
                if not gray:
                    result_scores_clean_A.append(sc["result"])
            elif primary == "B":
                rec["doc_hit"] = doc_hit(rep["answer_last"], item.get("doc_refs"))
            elif primary == "C":
                red = is_redirect(rep["answer_last"])
                rec["redirect"] = red
                if item.get("expect_redirect") and not red:
                    deadend += 1
            # gray soft 예산 위반(단일)도 점검
            floor = item.get("soft_must_not_contain_pricey")
            if floor:
                v = contamination_violations(rep["ids_last"], [], floor)
                if v:
                    rec["soft_pricey_violation"] = v

        else:  # multiturn
            turn_recs = []
            last_route_ok = True
            for ti, turn in enumerate(item["turns"]):
                tr = rep["turns"][ti]
                primary = turn["primary_path"]
                r_ok = route_ok(tr["route"], primary, turn.get("acceptable_paths"))
                routing_total += 1
                if r_ok:
                    routing_correct += 1
                trec = {"turn": ti, "route": tr["route"], "route_ok": r_ok}
                # 하드 오염 게이트 — 카테고리 조건 "계승"은 경로 A(SQL 필터)에서만 발생 가능.
                #   B/C에서 같은 차종이 결과에 떠도 그건 의미검색의 우연이지 조건 잔존이 아니다
                #   (예: RESET이 B로 정상 라우팅됐는데 doc_rag가 중형차 1대 추천 → 오염 아님).
                mnc = turn.get("must_not_contain")
                if mnc and tr["route"] == "A":
                    v = contamination_violations(tr["ids"], mnc, None)
                    if v:
                        trec["contamination"] = v
                        contamination += 1
                # 소프트 예산 위반(알려진 quirk, ai-search-known-quirks) — 게이트 아님, 관찰만 집계.
                floor = turn.get("soft_must_not_contain_pricey")
                if floor:
                    sv = contamination_violations(tr["ids"], [], floor)
                    if sv:
                        trec["soft_pricey"] = sv
                        soft_obs += 1
                # dead-end(C 턴)
                if primary == "C" and turn.get("expect_redirect"):
                    if not is_redirect(tr["answer"]):
                        deadend += 1
                        trec["deadend"] = True
                # 마지막 A턴이면 결과집합도(클린만 본셋)
                if primary == "A" and turn.get("predicate"):
                    golden = run_golden_ids(turn["predicate"])
                    sc = score_path_a(tr["ids"], golden, turn["predicate"])
                    trec["score"] = sc
                    if not gray:
                        result_scores_clean_A.append(sc["result"])
                turn_recs.append(trec)
            rec["turns"] = turn_recs

        per_item.append(rec)

    pin, pout = PRICE_PER_M.get(model, (0.0, 0.0))
    cost = total_in / 1e6 * pin + total_out / 1e6 * pout
    result_mean = sum(result_scores_clean_A) / len(result_scores_clean_A) if result_scores_clean_A else 0.0

    # tokens_measured는 run 딕셔너리의 "tokens_measured" 키가 아니라 실측 합계에서 직접
    # 도출한다(review pass 4 재수정). 커밋된 g2-baseline-partial.json은 이 플래그가 생기기
    # 전에 캡처돼 그 키 자체가 없다 — 키 부재를 "True"로 기본 처리하면(구 버전) 바로 그
    # 파일에서 $0.0000 비용이 실측처럼 cost 티어를 이겨버린다(코디네이터 실측 확인). 대신
    # flaky_measured와 같은 방식으로 데이터에서 직접 판단한다: 채점된 run 전체의 토큰
    # 합계가 0이면 "측정 안 함"이다 — 신규·구버전 raw 모두에 옳고, 앞으로 러너가 이 플래그를
    # 깜빡 안 찍어도 깨지지 않는다.
    tokens_measured = (total_in + total_out) > 0

    # 커버리지(review pass 4) — "몇 건을 실제로 채점했나"가 summary에 안 남으면, 44개 중 3개만
    # 캡처된 부분 결과가 완전한 baseline처럼 보인다(result_mean=1.0·gate PASS인데 41개는 아예
    # 실행된 적이 없다는 사실이 어디에도 안 남는 것 — 실제로 커밋된 g2-baseline-partial.json이
    # 이 상태였다). queryset 전체 대비 채점된/에러난/아예 캡처 안 된(raw에 없는) id를 명시한다.
    queryset_total = len(items)
    scored_n = len(per_item) - errored_n
    missing_ids = sorted(set(items.keys()) - set(raw["results"].keys()))

    return {
        "name": model,
        "result_mean": result_mean,
        "result_n": len(result_scores_clean_A),
        "routing_correct": routing_correct,
        "routing_total": routing_total,
        "flaky_n": flaky_n,
        "flaky_measured": flaky_measured,
        "contamination": contamination,
        "soft_obs": soft_obs,
        "deadend": deadend,
        # 게이트는 "위반이 없다"가 아니라 "위반 없이 실제로 측정됐다"여야 한다(review pass 5).
        # 전엔 오염·데드엔드만 봤는데, 그 둘은 채점된 run이 하나도 없으면 구조적으로 0이다 —
        # 실측: 44건 전부 429로 실패한 캡처(errored_n=44·scored_n=0)와 아예 빈 캡처가 둘 다
        # gate_pass=True로 나왔다. 에픽 G2 게이트("baseline 이하면 에픽 미종료")가 그 값을
        # 읽으므로, 측정이 없는 PASS는 게이트를 통째로 무력화한다.
        "gate_pass": (contamination == 0 and deadend == 0 and errored_n == 0 and scored_n > 0),
        "tokens_in": total_in,
        "tokens_out": total_out,
        "tokens_measured": tokens_measured,
        "cost_usd": cost,
        "latency_ms_mean": sum(latencies) / len(latencies) if latencies else 0.0,
        "errored_n": errored_n,
        "coverage": {
            "queryset_total": queryset_total,
            "scored_n": scored_n,
            "errored_n": errored_n,
            "missing_n": len(missing_ids),
            "missing_ids": missing_ids,
        },
        "is_partial": scored_n < queryset_total,
        "per_item": per_item,
    }


def main() -> None:
    # Windows 콘솔(cp949)이 한글·em-dash를 못 찍어 죽지 않게 stdout을 UTF-8로 고정.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--queryset", default="docs/ai-ab-test-queryset.json")
    ap.add_argument(
        "--raw", nargs="+", required=True,
        help="raw JSON 1개(베이스라인 단독, G2 baseline 기록용) 또는 2개(베이스라인 먼저 + 후보, A/B 비교)",
    )
    ap.add_argument("--out", default="docs/ab-eval-report.json")
    args = ap.parse_args()

    if len(args.raw) not in (1, 2):
        ap.error("--raw는 1개(베이스라인 단독) 또는 2개(베이스라인 후보)만 허용합니다.")

    queryset = json.loads(Path(args.queryset).read_text(encoding="utf-8"))
    raws = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.raw]
    summaries = [score_model(queryset, r) for r in raws]

    if len(summaries) == 1:
        # 1개 모드 — A/B 비교(사전식 승부·회귀 게이트) 없이 그 raw 1개의 채점 요약만 기록한다.
        # 키는 "baseline_summary"다. 2개 모드가 이미 "baseline"을 모델명 문자열로 쓰고 있어(아래),
        # 같은 키를 요약 dict로 재사용하면 같은 필드명이 모드마다 타입이 바뀌는 API가 된다
        # (13.8이 이 파일을 소비할 때 어느 모드인지 모르고 깨질 수 있음 — Spec Change Log 참조).
        baseline_only = summaries[0]
        report = {
            "baseline_summary": {k: v for k, v in baseline_only.items() if k != "per_item"},
            "detail": {baseline_only["name"]: baseline_only["per_item"]},
        }
        Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print("=" * 70)
        print(f"[{baseline_only['name']}] (baseline 단독 모드 — A/B 비교 없음)")
        # 커버리지는 콘솔에도 찍는다(review pass 5). JSON에만 남기면 사람이 실제로 보는 화면엔
        # "게이트: PASS"만 뜨고, 3/44짜리 부분 캡처가 완전한 baseline로 승격된다 — 커버리지를
        # 기록한 이유 자체가 그걸 막는 것이었다.
        cov = baseline_only["coverage"]
        print(
            f"  커버리지: {cov['scored_n']}/{cov['queryset_total']} 채점"
            f"(실패 {cov['errored_n']} · 미캡처 {cov['missing_n']})"
            f"{'  ⚠ 부분 캡처' if baseline_only['is_partial'] else ''}"
        )
        print(f"  결과집합정확도(clean A, n={baseline_only['result_n']}): {baseline_only['result_mean']:.3f}")
        print(f"  라우팅: {baseline_only['routing_correct']}/{baseline_only['routing_total']}")
        print(
            f"  flaky: {baseline_only['flaky_n']} | 오염(하드): {baseline_only['contamination']} | "
            f"소프트관찰: {baseline_only['soft_obs']} | dead-end: {baseline_only['deadend']} | "
            f"게이트: {'PASS' if baseline_only['gate_pass'] else 'FAIL'}"
        )
        print(f"리포트: {args.out}")
        print("=" * 70)
        return

    baseline, candidate = summaries[0], summaries[1]

    verdict = lexicographic_winner(baseline, candidate)
    # 베이스라인 회귀 게이트 — 후보가 베이스라인보다 결과정확도 하락 시 채택 불가.
    regression = candidate["result_mean"] < baseline["result_mean"] - 1e-9
    report = {
        "baseline": baseline["name"], "candidate": candidate["name"],
        "verdict": verdict, "regression_block": regression,
        "summaries": [
            {k: v for k, v in s.items() if k != "per_item"} for s in summaries
        ],
        "detail": {s["name"]: s["per_item"] for s in summaries},
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    for s in summaries:
        print(f"[{s['name']}]")
        print(f"  결과집합정확도(clean A, n={s['result_n']}): {s['result_mean']:.3f}")
        print(f"  라우팅: {s['routing_correct']}/{s['routing_total']}")
        print(f"  flaky: {s['flaky_n']} | 오염(하드): {s['contamination']} | 소프트관찰: {s['soft_obs']} | dead-end: {s['deadend']} | 게이트: {'PASS' if s['gate_pass'] else 'FAIL'}")
        print(f"  토큰 in/out: {s['tokens_in']}/{s['tokens_out']} | 비용 ${s['cost_usd']:.4f} | 지연 {s['latency_ms_mean']:.0f}ms")
    print("-" * 70)
    print(f"사전식 승부: {verdict['winner']}  ({verdict['tier']}: {verdict['reason']})")
    # 최종 채택 = 회귀 게이트가 후보를 거부하면 베이스라인 유지(사전식이 후보 손을 들어도).
    if regression:
        final = baseline["name"]
        print(f"⚠️ 회귀 게이트 발동: 후보 결과정확도({candidate['result_mean']:.3f}) < 베이스라인({baseline['result_mean']:.3f}) → 후보 채택 불가")
        print(f"➡️ 최종 채택: {final} (베이스라인 유지)")
    else:
        final = verdict["winner"] or baseline["name"]
        print(f"➡️ 최종 채택: {final}")
    report["final_adopt"] = final
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리포트: {args.out}")
    print("=" * 70)


if __name__ == "__main__":
    main()
