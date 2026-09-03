"""시세 진단 엔진 — 3단계 (docs/ai-advanced/HANDOFF.md §2, 02-seed-price-calibration.md "v3 최종 확정").

핵심 사상: 수치는 전부 SQL/모델이 낸다(파이썬 재계산 금지). LLM은 이 결과 위에 설명문만
  얹는다(4단계 이후) — 여기서는 결정론적 통계와 verdict만 만든다.

**동일 세대 원칙**(v3 확정): "더 뉴 그랜저 IG와 그랜저 IG는 가격이 너무 달라 같은 종끼리
  비교해야 한다" — 비교군 1순위는 모델 문자열 완전 일치(세대 동일), 완화 사다리에서만
  기본명 접두로 확장한다. LADDER의 model="exact"/"base" 구분이 그 원칙을 코드로 옮긴 것.

완화 사다리는 선언 리스트로 모듈 상단에 박아둔다(코드 로직에 흩뿌리지 않음) — 사다리 자체를
  바꿀 때 이 리스트 하나만 보면 된다.

**2026-08-31 개정(사용자 승인, 실측 결함 4건 중 P4)**: 사다리에 "트림 해제(동일 세대 계열)"
  단(LADDER step 3, model="family")을 추가했다 — 트림 그룹(예: "더 뉴 그랜저 IG 3.3", 표본
  5건)에서 사다리가 사고 해제 다음 곧장 세대 해제로 점프해 GN7까지 섞인 중앙값을 기준으로
  "저렴" 오판이 났다(같은 세대 14건 기준으론 상위 36% 가격이었음 — 실측). 동시에 verdict
  판정 기준을 사분위(q1/q3)에서 **TabPFN 적정가 대비 괴리율(±5%)**로 전환했다(tabpfn 없으면
  사분위 폴백 유지, `_verdict_by_fair_price`) — 표본이 적을수록 사분위 폭이 왜곡되는데 TabPFN은
  개별 특징(연식·주행·배기량 등)으로 더 안정적인 적정가를 낸다. 응답에 `verdict_basis`
  필드를 추가해(더하기만) 어느 기준으로 판정했는지 웹·설명문이 명시할 수 있게 했다.
  근거 표: docs/ai-advanced/02-seed-price-calibration.md "v3 최종 확정" 표(트림별 앵커가·
  연감가가 세대별로 크게 다름을 확인할 수 있다).

**2026-09-03 개정(사용자 결정, TabPFN 학습 세션 실측)**: verdict를 "적정가 대비 ±5%"에서
  **TabPFN 예측 분포의 분위수 5단**(q10/q25/q75/q90 경계, `_verdict_by_quantiles`)으로 전환했다.
  ±5%는 사람이 모든 매물에 같은 폭으로 정한 경계라 +5.1%/+4.9%에서 판정이 뒤집혔고(실측:
  아반떼 CN7 2020, 3만원 차이), 분위수는 그 매물의 이웃 분포에서 폭이 나온다(아반떼 53건 실측
  q25~q75 폭 6.0~15.9%, 42건이 ±5%보다 좁음 → 판정이 다소 엄격해짐: 적정 28→22건). 보정 검사
  (자기 제외 학습, 53건)에서 q90 위 5건·q10 아래 4건(기대 5.3)으로 꼬리가 맞았다 — 단 시드
  데이터(규칙+5% 노이즈) 기준이라 실매물 보정은 미확인. mean과 분위수는 predict(output_type=
  "full") 한 번에 같이 나와(실측 1.46s→1.49s) 지연 추가는 없다. 응답엔 `tabpfn.quantiles`를
  더했고(더하기만), verdict_basis 값은 "적정가"→"분위수", verdict 값에 "다소 저렴"/"다소 높음"이
  추가됐다(웹·앱은 verdict 문자열을 그대로 배지로 쓴다).
"""

import logging
import re

logger = logging.getLogger(__name__)

# ── 완화 사다리 (선언형, 위에서부터 순서대로 시도) ──────────────────────
# model: "exact"  → model = 대상모델 (세대 동일 비교, v3 확정 원칙)
#        "family" → 후미 배기량 토큰(예: "3.3") 제거한 접두로 model ilike '접두%' (동일 세대,
#                    트림만 다른 매물까지 허용 — 아래 _family_model 참조)
#        "base"   → "더 뉴 "/"올 뉴 " 접두 제거 후 첫 토큰으로 model ilike '%기본명%'
# fuel/accident: True면 조건을 건다(아래 _build_where 참조), False면 조건 해제.
# year_band/km_band: 대상 연식·주행 대비 허용 편차.
#
# 2026-08-31 사용자 실측 결함(P4): 트림 그룹(예: "더 뉴 그랜저 IG 3.3", 표본 5건)에서 사다리가
#   곧장 세대 해제(step 4, "base")로 점프해 GN7까지 섞인 중앙값을 기준으로 "저렴" 오판이 났다
#   (같은 세대 14건 기준으론 상위 36% 가격이었음 — 실측). "동일 세대 계열(트림 해제)" 단을 사고
#   해제(구 step2)와 세대 해제(구 step3) 사이에 끼워, 트림만 다른 동세대 매물까지 먼저 넓혀보고
#   그래도 표본이 모자랄 때만 세대를 넘어가게 한다.
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
        "desc": "트림 해제(동일 세대 계열)",
        "model": "family",
        "fuel": True,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
    {
        "step": 4,
        "desc": "세대 해제(기본 모델명 매칭)",
        "model": "base",
        "fuel": True,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
    {
        "step": 5,
        "desc": "연료 조건 해제",
        "model": "base",
        "fuel": False,
        "accident": False,
        "year_band": 3,
        "km_band": 50_000,
    },
]

MIN_SAMPLE = 5

# 2026-08-31 개정(사용자 실측 결함 F4, 소표본 과신 판정): 비교군이 이 미만(1~2건)이면
# 사분위(q1/q3)든 TabPFN 적정가든 verdict를 매기지 않고 보류한다 — 표본 1~2건의 사분위는
# 폭이 좁아 "저렴/높음" 배지가 통계적으로 근거가 못 된다(실측: 비교군 1건으로 "하위 0%"
# 배지가 뜬 사례). 0건(비교군 자체 없음)은 기존대로 verdict_basis도 None, 1~2건은
# verdict_basis="표본 부족"으로 구분해(웹이 다른 문구를 쓸 수 있게) 응답한다.
MIN_VERDICT_SAMPLE = 3

# "더 뉴 "/"올 뉴 " 접두 제거 후 기본 모델명(첫 토큰) 추출 — v3 확정 명칭 체계
# ("더 뉴 그랜저 IG" → "그랜저", "올 뉴 쏘렌토" → "쏘렌토").
_GENERATION_PREFIXES = ("더 뉴 ", "올 뉴 ")

# 후미 배기량 토큰 판정(예: "3.3", "2.5", "3.0") — model 문자열 마지막 토큰이 이 모양이면
# 트림(배기량) 표기로 보고 제거한다(_family_model). "더 뉴 그랜저 IG 3.3" → "더 뉴 그랜저 IG".
_DISPLACEMENT_SUFFIX_RE = re.compile(r"^\d\.\d$")

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

# TabPFN 예측 분포에서 읽는 분위수(하위 몇 %에 해당하는 가격)와 응답 키 — 5단 판정의 경계
# (2026-09-03 개정, 모듈 docstring 참조). 두 튜플은 자리끼리 대응한다.
_TABPFN_QUANTILES = (0.10, 0.25, 0.50, 0.75, 0.90)
_TABPFN_QUANTILE_KEYS = ("q10", "q25", "q50", "q75", "q90")

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


def _family_model(model: str) -> str:
    """model 문자열의 후미 배기량 토큰(정규식 ^\\d\\.\\d$, 예: "3.3")을 제거한 접두를 반환한다
    ("트림 해제(동일 세대 계열)" 단, LADDER step 3). 후미가 배기량 형태가 아니면 원본 model을
    그대로 돌려준다 — 그 경우 이 단의 `model ILIKE 원본%` 조건은 exact 단과 사실상 같은 표본을
    내므로 별도 처리 없이 그대로 통과시킨다(설계 확정, 구현 단순화 허용).

    >>> _family_model("더 뉴 그랜저 IG 3.3")
    '더 뉴 그랜저 IG'
    >>> _family_model("그랜저 IG 3.0")
    '그랜저 IG'
    >>> _family_model("아반떼 CN7 하이브리드")
    '아반떼 CN7 하이브리드'
    """
    tokens = model.split()
    if tokens and _DISPLACEMENT_SUFFIX_RE.match(tokens[-1]):
        return " ".join(tokens[:-1])
    return model


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
    elif rung["model"] == "family":  # 트림 해제 — 동일 세대 계열(배기량 접두 제거) 부분일치
        family = _family_model(target["model"])
        clauses.append("model ilike %s")
        params.append(f"{family}%")
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
    """[사분위 폴백] q1 미만=저렴, q3 초과=높음, 그 외 적정. 결정론(LLM 아님).

    TabPFN 분위수가 없을 때만 쓴다 — 있으면 _verdict_by_quantiles가 우선한다(diagnose()의
    verdict_basis 분기 참조, 2026-09-03 판정 기준 전환).
    """
    if price < q1:
        return "저렴"
    if price > q3:
        return "높음"
    return "적정"


def _verdict_by_quantiles(price: int, q: dict) -> str:
    """[예측 분포 기준] TabPFN 분위수 5단 판정(2026-09-03 사용자 결정, 모듈 docstring 참조).

    q10 미만 '저렴' / q25 미만 '다소 저렴' / q75 이하 '적정' / q90 이하 '다소 높음' / 그 위
    '높음'. 경계 포함 규칙: 아래쪽(q10·q25)은 미만, 위쪽(q75·q90)은 이하 — 정확히 q25도
    정확히 q75도 '적정'이라 가운데 절반(q25~q75)이 닫힌 구간이다. 폭은 사람이 정하지 않고
    그 매물의 이웃 분포(TabPFN 출력)에서 나온다 — 종전 ±5% 고정폭과의 차이는 그것뿐이다.
    """
    if price < q["q10"]:
        return "저렴"
    if price < q["q25"]:
        return "다소 저렴"
    if price <= q["q75"]:
        return "적정"
    if price <= q["q90"]:
        return "다소 높음"
    return "높음"


def _verdict_and_basis(
    sample_count: int, price: int, stats: dict | None, tabpfn_quantiles: dict | None
) -> tuple[str | None, str | None]:
    """verdict·verdict_basis를 함께 결정한다(항상 쌍으로 채워지거나 함께 None — I2 불변식).

    2026-09-03: tabpfn 분위수가 있으면 예측 분포 5단(verdict_basis="분위수"), 없으면 사분위
    폴백(verdict_basis="사분위"). 표본 부족 보류(F4)는 분위수 유무와 무관하게 먼저 적용된다.

    2026-08-31 사용자 실측 결함(F4) 수정: 표본이 MIN_VERDICT_SAMPLE(3) 미만이면(0건 제외,
    그건 비교군 자체가 없는 별개 케이스) 사분위·적정가 어느 기준으로도 판정하지 않고 보류한다
    (verdict_basis="표본 부족"). diagnose()에서만 쓰이고 DB 접근이 없어 단위 테스트로 경계
    (2건→보류, 3건→판정)를 DB 없이 직접 고정할 수 있다(test_market_price.py 참조).
    """
    if sample_count == 0:
        return None, None
    if sample_count < MIN_VERDICT_SAMPLE:
        return None, "표본 부족"
    if tabpfn_quantiles is not None:
        return _verdict_by_quantiles(price, tabpfn_quantiles), "분위수"
    return _verdict(price, stats["q1"], stats["q3"]), "사분위"


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


def _tabpfn_predict(
    target: dict, train_rows: list[dict]
) -> tuple[int | None, dict | None, str]:
    """학습 표본으로 TabPFN을 학습시켜 대상 1건의 적정가(mean)와 예측 분포의 분위수를 낸다.

    반환 (price, quantiles, note). 학습 표본 10건 미만이거나 tabpfn 미설치면 통계만 응답하고
    price·quantiles는 None으로 둔다(엔진 전체가 죽지 않는다 — 설계 확정).

    TabPFN 회귀는 값 하나가 아니라 가격 축 위의 확률 분포를 출력한다. output_type="full"은
    그 분포에서 mean·median·분위수를 한 번의 추론으로 같이 돌려준다(실측: 기본 predict와
    시간 동일, mean 값도 원 단위까지 동일) — 두 번 부르지 않는 이유. price는 종전대로
    mean을 만원 단위로 반올림한 값(웹·앱·I7 불변식 계약 유지), quantiles는 원 단위 정수.
    """
    if len(train_rows) < _TABPFN_MIN_COMPS:
        return None, None, f"학습 표본 {len(train_rows)}건 — {_TABPFN_MIN_COMPS}건 미만"

    try:
        from tabpfn import TabPFNRegressor
    except Exception:
        return None, None, "tabpfn 미설치"

    global _TABPFN_MODEL
    if _TABPFN_MODEL is None:
        _TABPFN_MODEL = TabPFNRegressor(device="cpu")

    x = [_tabpfn_features(c) for c in train_rows]
    y = [c["price"] for c in train_rows]
    _TABPFN_MODEL.fit(x, y)
    out = _TABPFN_MODEL.predict(
        [_tabpfn_features(target)], output_type="full", quantiles=list(_TABPFN_QUANTILES)
    )
    price = int(round(float(out["mean"][0]) / 10_000)) * 10_000
    quantiles = {
        key: int(round(float(values[0])))
        for key, values in zip(_TABPFN_QUANTILE_KEYS, out["quantiles"])
    }
    return price, quantiles, f"기본 모델군 {len(train_rows)}건 학습"


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
    else:
        stats = {
            "min": stats_row["min_price"],
            "q1": stats_row["q1"],
            "median": stats_row["median"],
            "q3": stats_row["q3"],
            "max": stats_row["max_price"],
        }
        percentile = stats_row["percentile"]

    # tabpfn 예측을 verdict보다 먼저 계산한다 — 판정 기준(2026-09-03 개정): tabpfn 분위수가
    # 있으면 예측 분포 5단(_verdict_by_quantiles)으로, 없으면 기존 사분위로 폴백한다.
    # sample_count==0이면 비교군 자체가 없으므로 verdict도 None으로 둔다(사분위 폴백조차
    # 근거가 없음 — I2 불변식: stats/percentile/verdict는 항상 함께 None이거나 함께 채워진다).
    # sample_count가 0은 아니지만 MIN_VERDICT_SAMPLE 미만(1~2건)이면 표본 부족으로 보류한다
    # (F4 수정, _verdict_and_basis 참조 — 이때도 stats/percentile은 그대로 채워진다, I2 개정).
    tabpfn_price, tabpfn_quantiles, tabpfn_note = _tabpfn_predict(target, train_rows)
    verdict, verdict_basis = _verdict_and_basis(
        sample_count, target["price"], stats, tabpfn_quantiles
    )

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
        "verdict_basis": verdict_basis,
        "tabpfn": {"price": tabpfn_price, "note": tabpfn_note, "quantiles": tabpfn_quantiles},
        "comps": [_comp_summary(r) for r in comp_rows],
    }
