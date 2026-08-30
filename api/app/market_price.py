"""시세 진단 엔진 — 3단계 (docs/ai-advanced/HANDOFF.md §2, 02-seed-price-calibration.md "v3 최종 확정").

핵심 사상: 수치는 전부 SQL/모델이 낸다(파이썬 재계산 금지). LLM은 이 결과 위에 설명문만
  얹는다(4단계 이후) — 여기서는 결정론적 통계와 verdict만 만든다.

**동일 세대 원칙**(v3 확정): "더 뉴 그랜저 IG와 그랜저 IG는 가격이 너무 달라 같은 종끼리
  비교해야 한다" — 비교군 1순위는 모델 문자열 완전 일치(세대 동일), 완화 사다리에서만
  기본명 접두로 확장한다. LADDER의 model="exact"/"base" 구분이 그 원칙을 코드로 옮긴 것.

완화 사다리는 선언 리스트로 모듈 상단에 박아둔다(코드 로직에 흩뿌리지 않음) — 사다리 자체를
  바꿀 때 이 리스트 하나만 보면 된다.
"""

import logging

logger = logging.getLogger(__name__)

# ── 완화 사다리 (선언형, 위에서부터 순서대로 시도) ──────────────────────
# model: "exact"  → model = 대상모델 (세대 동일 비교, v3 확정 원칙)
#        "base"   → "더 뉴 "/"올 뉴 " 접두 제거 후 첫 토큰으로 model ilike '%기본명%'
# fuel/accident: True면 조건을 건다(아래 _build_where 참조), False면 조건 해제.
# year_band/km_band: 대상 연식·주행 대비 허용 편차.
LADDER = [
    {
        "step": 0,
        "desc": "동일 세대·연료·사고 상태, 연식 ±2년·주행 ±3만km",
        "model": "exact",
        "fuel": True,
        "accident": True,
        "year_band": 2,
        "km_band": 30_000,
    },
    {
        "step": 1,
        "desc": "밴드 확대: 연식 ±3년·주행 ±5만km",
        "model": "exact",
        "fuel": True,
        "accident": True,
        "year_band": 3,
        "km_band": 50_000,
    },
    {
        "step": 2,
        "desc": "사고 상태 조건 해제",
        "model": "exact",
        "fuel": True,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
    {
        "step": 3,
        "desc": "세대 해제(기본 모델명 매칭)",
        "model": "base",
        "fuel": True,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
    {
        "step": 4,
        "desc": "연료 조건 해제",
        "model": "base",
        "fuel": False,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
]

MIN_SAMPLE = 5

# "더 뉴 "/"올 뉴 " 접두 제거 후 기본 모델명(첫 토큰) 추출 — v3 확정 명칭 체계
# ("더 뉴 그랜저 IG" → "그랜저", "올 뉴 쏘렌토" → "쏘렌토").
_GENERATION_PREFIXES = ("더 뉴 ", "올 뉴 ")

# TabPFN 특징 벡터의 연료 원핫 순서(listings.fuel CHECK 목록, 0002_listings.sql과 동일 순서).
_FUEL_ORDER = ["가솔린", "디젤", "하이브리드", "전기", "LPG"]

# 대상가와 비교군을 만들 때 재사용할 comps 필드 — TabPFN 특징 계산에도 그대로 쓴다.
_COMP_COLUMNS = "id, model, year, mileage, price, displacement, fuel, options, accident_free"

# comps는 산점도용으로 최대 이만큼만 가져온다(설계 확정값). TabPFN 학습도 이 표본을
# 그대로 재사용한다 — 사다리 표본 규모(수~십수 건, v3 표 기준)에서는 60건 상한이
# 거의 걸리지 않아 별도 쿼리를 두 번 쏘지 않는 단순화다(판단 사항, 보고에 명시).
MAX_COMPS = 60

# TabPFN 적정가를 내려면 비교군이 이 이상이어야 한다(설계 확정값).
_TABPFN_MIN_COMPS = 10

# TabPFN 모델 객체 캐시 — 재로드(가중치 로딩)를 피하기 위해 모듈 레벨에 1회만 생성한다.
# fit()은 매 호출마다 비교군으로 다시 하므로(sklearn 스타일), 캐시하는 건 객체 생성 비용뿐이다.
_TABPFN_MODEL = None


def _base_model(model: str) -> str:
    """"더 뉴 "/"올 뉴 " 접두를 제거한 뒤 첫 토큰(기본 모델명)을 반환한다."""
    stripped = model
    for prefix in _GENERATION_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    tokens = stripped.split()
    return tokens[0] if tokens else stripped


def _build_where(rung: dict, target: dict) -> tuple[str, list]:
    """사다리 한 단(rung)의 WHERE 절과 파라미터를 만든다.

    공통 고정 조건(status='on_sale'·대상 제외·변속기 일치)은 매 단 공통이고,
    model/fuel/accident/연식·주행 밴드만 rung에 따라 달라진다.
    """
    clauses = ["status = 'on_sale'", "id <> %s", "transmission = %s"]
    params: list = [target["id"], target["transmission"]]

    if rung["model"] == "exact":
        clauses.append("model = %s")
        params.append(target["model"])
    else:  # "base" — 세대 해제, 기본 모델명 부분일치
        base = _base_model(target["model"])
        clauses.append("model ilike %s")
        params.append(f"%{base}%")

    clauses.append("year between %s and %s")
    params += [target["year"] - rung["year_band"], target["year"] + rung["year_band"]]

    km_lo = max(target["mileage"] - rung["km_band"], 0)
    clauses.append("mileage between %s and %s")
    params += [km_lo, target["mileage"] + rung["km_band"]]

    if rung["fuel"]:
        clauses.append("fuel = %s")
        params.append(target["fuel"])

    if rung["accident"]:
        # "대상이 무사고인가"는 accident_free(NOT NULL, 더 널리 채워짐 — sql_rag_node.py의
        # 기존 관례와 동일 판단 축)로 정하고, 실제 필터는 설계 확정대로 accident_status
        # 컬럼에 건다. accident_status는 NULL(미입력)일 수 있어 <> 비교 시 그 행은 자동으로
        # 제외된다(3값 논리 — 설계의 "NULL은 제외"와 일치).
        if target["accident_free"]:
            clauses.append("accident_status = %s")
        else:
            clauses.append("accident_status <> %s")
        params.append("무사고")

    return " AND ".join(clauses), params


def _stats_sql(where_sql: str) -> str:
    return (
        "SELECT count(*) AS cnt, min(price) AS min_price, "
        "percentile_cont(0.25) within group (order by price) AS q1, "
        "percentile_cont(0.5) within group (order by price) AS median, "
        "percentile_cont(0.75) within group (order by price) AS q3, "
        "max(price) AS max_price, "
        "(count(*) filter (where price <= %s))::float / nullif(count(*), 0) AS percentile "
        f"FROM public.listings WHERE {where_sql}"
    )


def _comps_sql(where_sql: str) -> str:
    return (
        f"SELECT {_COMP_COLUMNS} FROM public.listings "
        f"WHERE {where_sql} ORDER BY price LIMIT {MAX_COMPS}"
    )


def _verdict(price: int, q1: float, q3: float) -> str:
    """q1 미만=저렴, q3 초과=높음, 그 외 적정. 결정론(LLM 아님)."""
    if price < q1:
        return "저렴"
    if price > q3:
        return "높음"
    return "적정"


def _fuel_onehot(fuel: str | None) -> list[int]:
    return [1 if fuel == f else 0 for f in _FUEL_ORDER]


def _tabpfn_features(row: dict) -> list:
    options = row.get("options") or []
    return [
        row["year"],
        row["mileage"],
        row["displacement"],
        *_fuel_onehot(row["fuel"]),
        len(options),
        int(bool(row["accident_free"])),
    ]


def _tabpfn_predict(target: dict, train_rows: list[dict]) -> tuple[int | None, str]:
    """학습 표본으로 TabPFN을 학습시켜 대상 1건의 적정가를 예측한다.

    학습 표본 10건 미만이거나 tabpfn 미설치면 통계만 응답하고 가격은 None으로 둔다
    (엔진 전체가 죽지 않는다 — 설계 확정).
    """
    if len(train_rows) < _TABPFN_MIN_COMPS:
        return None, f"학습 표본 {len(train_rows)}건 — {_TABPFN_MIN_COMPS}건 미만"

    try:
        from tabpfn import TabPFNRegressor
    except Exception:
        return None, "tabpfn 미설치"

    global _TABPFN_MODEL
    if _TABPFN_MODEL is None:
        _TABPFN_MODEL = TabPFNRegressor(device="cpu")

    x = [_tabpfn_features(c) for c in train_rows]
    y = [c["price"] for c in train_rows]
    _TABPFN_MODEL.fit(x, y)
    predicted = _TABPFN_MODEL.predict([_tabpfn_features(target)])[0]
    price = int(round(predicted / 10_000)) * 10_000
    return price, f"기본 모델군 {len(train_rows)}건 학습"


def _listing_summary(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "manufacturer": row["manufacturer"],
        "model": row["model"],
        "year": row["year"],
        "mileage": row["mileage"],
        "price": row["price"],
        "fuel": row["fuel"],
        "transmission": row["transmission"],
        "displacement": row["displacement"],
        "accident_free": row["accident_free"],
        "accident_status": row["accident_status"],
        "region": row["region"],
    }


def _comp_summary(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "model": row["model"],
        "year": row["year"],
        "mileage": row["mileage"],
        "price": row["price"],
    }


def diagnose(listing_id: str, conn) -> dict | None:
    """대상 매물 1건의 시세를 진단한다. 매물이 없으면 None(라우터가 404로 변환).

    conn은 이미 ai_readonly 트랜잭션 안에 있는 psycopg 커넥션(db/readonly.py의
    readonly_connection() 산출물)을 그대로 받는다 — 이 함수는 별도로 롤·트랜잭션을
    열지 않는다(호출부 책임, DB 접근 경로 단일화).
    """
    from psycopg.rows import dict_row

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT * FROM public.listings WHERE id = %s", (listing_id,))
        target = cur.fetchone()
        if target is None:
            return None

        chosen_rung = where_sql = where_params = stats_row = None
        for rung in LADDER:
            w_sql, w_params = _build_where(rung, target)
            cur.execute(_stats_sql(w_sql), [target["price"], *w_params])
            row = cur.fetchone()
            chosen_rung, where_sql, where_params, stats_row = rung, w_sql, w_params, row
            if row["cnt"] >= MIN_SAMPLE:
                break

        cur.execute(_comps_sql(where_sql), where_params)
        comp_rows = cur.fetchall()

        # TabPFN 학습 표본은 화면 비교군과 분리해 더 넓게 잡는다 — 사다리(동종 비교)는
        # 5건이면 멈추는데 TabPFN 최소 표본은 10건이라, 동종 비교가 잘 될수록 예측이
        # 항상 "표본 부족"으로 빠지는 구멍이 있었다(운영 DB 실측: 더 뉴 그랜저 IG 표본 7).
        # 연식·배기량·연료가 특징값에 들어가므로 세대 차이는 모델이 흡수한다 — 통계
        # (사분위·백분위)는 여전히 동종 비교군만 쓴다("같은 종끼리 비교" 원칙 유지).
        base = _base_model(target["model"])
        cur.execute(
            f"SELECT {_COMP_COLUMNS} FROM listings "
            "WHERE status = 'on_sale' AND id <> %s AND transmission = %s "
            "AND model ILIKE %s ORDER BY year DESC, mileage ASC LIMIT 120",
            [target["id"], target["transmission"], f"%{base}%"],
        )
        train_rows = cur.fetchall()

    sample_count = stats_row["cnt"]
    if sample_count == 0:
        stats = None
        percentile = None
        verdict = None
    else:
        stats = {
            "min": stats_row["min_price"],
            "q1": stats_row["q1"],
            "median": stats_row["median"],
            "q3": stats_row["q3"],
            "max": stats_row["max_price"],
        }
        percentile = stats_row["percentile"]
        verdict = _verdict(target["price"], stats["q1"], stats["q3"])

    tabpfn_price, tabpfn_note = _tabpfn_predict(target, train_rows)

    return {
        "listing": _listing_summary(target),
        "criteria": {
            "step": chosen_rung["step"],
            "desc": chosen_rung["desc"],
            "sample_count": sample_count,
        },
        "stats": stats,
        "percentile": percentile,
        "verdict": verdict,
        "tabpfn": {"price": tabpfn_price, "note": tabpfn_note},
        "comps": [_comp_summary(r) for r in comp_rows],
    }
