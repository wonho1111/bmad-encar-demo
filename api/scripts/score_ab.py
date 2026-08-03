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
          --out docs/g2-recapture-<YYYY-MM-DD>-report.json

⚠️ `--out`을 커밋된 채점 리포트(`docs/g2-baseline-report.json` 등, `scripts/baseline_guard.py`의
  `PROTECTED_BASELINES` 목록)로 주지 말 것 — 그 파일은 사람이 눈으로 대조하는 세 축(라우팅·
  가이드인용·되묻기)의 유일한 기준점이라 부분 캡처로 덮어쓰면 조용히 사라진다(DW-635). 위
  예시(`<YYYY-MM-DD>`는 실제 날짜로 치환)는 그래서 날짜형 재캡처 경로를 쓴다 — 단, **이미
  커밋된 날짜형 증거 파일(예: `g2-recapture-2026-08-03.json`류)은 그 자체가 보호 목록에
  들어가므로 `--out`으로 재사용하지 말 것**, 매번 새 날짜로 써야 한다. `main()`이 이 목록을
  실제로 거부한다(CLAUDE.md B9).

종료 코드(두 모드 공통): 게이트가 떨어지면 **1**로 끝난다.
  · 2파일 모드 — top-level `gate_pass`가 false일 때(회귀·검증불가·개별 summary FAIL 어느 쪽이든).
  · 1파일 모드 — 그 raw의 `gate_pass`가 false일 때. 1파일 모드는 "이 캡처를 새 기준선으로
    올린다"는 자리라(G2 2단계), 여기서 exit 0을 내면 `score_ab.py … && cp … g2-baseline.json`
    같은 체인이 오염·전량 실패 캡처를 그대로 기준선으로 승격시킨다(실측: 47건 전량 errored인
    raw가 콘솔에 `게이트: FAIL`을 찍고도 exit 0이었다 — DW-636이 run_phase_b에서 닫은 것과
    같은 부류가 이쪽에 남아 있었다, 13.9 독립 후속 리뷰).
  위 실행 예시처럼 `run_phase_b.py … && score_ab.py …`로 이어 붙일 때 체인이 조용히 진행되지
  않게 하기 위해서다(run_phase_b.py와 같은 규칙).
  리포트 파일과 콘솔 요약은 종료 전에 이미 다 쓴다 — 게이트가 떨어져도 산출물은 남는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))

# 커밋된 G2 비교 근거(raw 캡처·채점 리포트) 보호 — run_phase_b.py와 목록을 공유한다(DW-635).
from scripts.baseline_guard import is_protected  # noqa: E402

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

# 거절(C) answer가 "갈림길"인지 — 셋 중 하나라도 있으면 redirect. 마커는 전부 **행동 유도 문구**여야
# 한다(다음에 뭘 하면 되는지 알려주는 절). 판정이 OR이므로 아무 데나 흔한 낱말을 넣으면 게이트가
# 구조적으로 항상 통과해 dead-end를 영영 못 잡는다.
# 13.5 2차 코드리뷰: 1차 패치가 넣은 "차장님"은 페르소나 호칭일 뿐 유도 의미가 없어(거절 문장을
#   통째로 지워도 통과) 제거하고, 함께 빠졌던 "용도를 알려주시면"을 되살렸다 — answer_node의
#   FR17 0건 fallback이 그 문구로 재유도하는데 1차 패치 후 dead-end로 오분류되고 있었다(실측).
# 커버 대상: guard_node._GUARD_ANSWER(마커 1·2) · answer_node._EMPTY_FALLBACK(마커 3).
# 이 결합은 tests/test_ab_scoring.py가 is_redirect()를 실제로 호출해 못박는다(주석은 계약이 아니다).
REDIRECT_MARKERS = ("매물을 찾아드릴게요", "조건을 말씀해 주시면", "용도를 알려주시면")

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


def score_path_hybrid(returned_ids: list[str], golden_ids: set) -> dict:
    """경로 HYBRID 결과집합 채점 — 항상 precision(보여준 게 전부 정답 집합 안인가).

    경로 A와 달리 F1/재현율을 쓰지 않는 이유: 하이브리드는 조건을 만족하는 매물 중
    **질의와 의미가 가까운 순으로 상위 N건만** 보여주는 것이 정상 동작이다(예: 조건에
    36건이 맞아도 5건만 반환). 재현율을 섞으면 정상 동작이 항상 감점돼 신호가 죽는다.

    큐리셋의 HYBRID predicate는 "가이드가 제시하는 구조조건까지 반영한 좁혀진 집합"이다.
    따라서 precision이 곧 **가이드가 실제로 결과를 좁혔는가**의 척도다 — 가이드를 못
    쓰면 같은 가격대의 엉뚱한 차종(경차·화물차 등)이 섞여 값이 떨어진다. 모델이 정답
    집합보다 **더 좁게** 뽑는 것(부분집합)은 감점하지 않는다.
    """
    returned = set(returned_ids)
    golden = set(golden_ids)
    if not returned:
        # 0건 반환: 정답도 0건이면 정상, 정답이 있는데 못 찾았으면 0점.
        return {"mode": "hybrid_precision", "result": 1.0 if not golden else 0.0,
                "returned_n": 0, "golden_n": len(golden)}
    p = len(returned & golden) / len(returned)
    return {"mode": "hybrid_precision", "result": p, "precision": p,
            "returned_n": len(returned), "golden_n": len(golden)}


def doc_hit(answer: str, doc_refs: list[str]) -> bool:
    """HYBRID 경로: answer의 '(참고: <title>)'에 기대 가이드 제목이 들어있나(인용 recall).

    hybrid_rag_node는 거리 컷오프(FR49) 이내 가이드를 채택했을 때만 이 접미사를 붙이므로,
    이 값이 곧 "가이드 문서가 실제로 쓰였나"의 관측점이다(FR44).
    """
    titles = [DOC_STEM_TO_TITLE.get(s, s) for s in (doc_refs or [])]
    return any(t and t in (answer or "") for t in titles)


def is_redirect(answer: str) -> bool:
    return any(m in (answer or "") for m in REDIRECT_MARKERS)


# 되묻기(CLARIFY)가 실제로 발동했는지 판정할 고정 문구 — clarify_node._CLARIFY_QUESTION의
# 앞부분이다. 이 노드는 LLM을 쓰지 않고 이 문자열을 그대로 돌려주므로 부분 일치로 충분하다.
# 아래 tests/test_ab_scoring.py가 실제 노드 상수를 import해 이 마커가 여전히 맞는지 못박는다
# (주석은 계약이 아니다 — 문구가 바뀌면 검사가 먼저 깨져야 한다).
CLARIFY_QUESTION_MARKER = "조건을 조금만 좁혀볼게요"


def clarify_question_ok(answer: str) -> bool:
    """되묻기 고정 질문이 answer에 실제로 나왔나."""
    return CLARIFY_QUESTION_MARKER in (answer or "")


def clarify_chips_ok(clarify: dict | None) -> bool:
    """되묻기 페이로드에 누를 칩이 실제로 담겼나(빈 배열·None이면 False).

    "칩을 눌러도 되고"라고 말해 놓고 칩이 0개면 사용자에겐 막다른 길이다 — 질문 문구만
    보는 검사는 그 상태를 통과시킨다. 러너가 `clarify_last`를 캡처한 경우에만 채점한다.
    """
    return bool((clarify or {}).get("chips"))


# 큐리셋 골든 라벨의 유일한 어휘(DW-609, 2026-08-02 재설계) — 라우터가 실제로 내는 값과
# 글자 그대로 같다. 이전에는 큐리셋이 구어휘(A/B/C)로 고정돼 있고 채점기가 A→SQL·B→CLARIFY·
# C→REJECT로 **번역해서** 비교했는데, 그 번역 계층이 "라벨과 실제 동작이 어긋나는" 문제를
# 반복 생산했다(DW-562·572·575·580·588·605·607). 큐리셋을 신어휘로 옮기면서 번역 계층을
# 걷어냈다 — 골든 라벨과 실제 route는 이제 같은 어휘라 중간 변환이 없다.
ROUTE_LABELS = ("SQL", "HYBRID", "CLARIFY", "REJECT")

# 이미 캡처된 **raw 파일**의 route 값을 올리는 별칭표는 남긴다(아래 captured_route 참조) —
# 큐리셋 어휘와 달리, 리포에 커밋된 옛 캡처 파일은 여전히 A/B/C로 적혀 있기 때문이다.
_LEGACY_ROUTE_ALIASES = {"A": "SQL", "B": "CLARIFY", "C": "REJECT"}


def _require_route_labels(primary: str, acceptable: list[str] | None, where: str) -> str:
    """큐리셋 골든 라벨(primary + acceptable 원소 전부)이 신 4값 어휘인지 확인한다.

    `acceptable_paths`도 함께 보는 이유(review-5 실측): 이 검사가 `primary`만 볼 때
    `route_ok("SQL", "SQL", ["SQL", "SQLL_TYPO"])`가 True를 돌려준다 — 오타 한 글자가
    허용집합에서 조용히 무시되고, 리포트 어디에도 흔적이 안 남는다. 골든 라벨은
    우리가 쓴 데이터이므로 두 자리를 같은 기준으로 막는다(B9).

    구어휘(A/B/C)는 여기서 fail-loud로 거부한다. 아래 `score_model()`의 채점 분기는
    이제 신어휘 리터럴(`"SQL"`/`"HYBRID"`/`"CLARIFY"`/`"REJECT"`)로만 갈라지므로,
    구어휘 큐리셋을 그대로 먹이면 **라우팅은 계속 맞다고 세면서 결과집합·인용 채점만
    조용히 0건이 된다**(구 버전에서 실측된 함정을 방향만 바꿔 되풀이하는 자리다).
    조용한 오답 대신 "큐리셋을 신어휘로 옮겨라"라고 말해 주는 편이 싸다.
    """
    for field, value in [("primary_path", primary)] + [
        ("acceptable_paths 원소", a) for a in (acceptable or [])
    ]:
        if value not in ROUTE_LABELS:
            raise ValueError(
                f"{where}: {field}={value!r}는 신 4값 어휘가 아니다(허용: {list(ROUTE_LABELS)}). "
                f"구어휘 A/B/C 큐리셋은 2026-08-02 재설계(DW-609)로 폐기됐다 — "
                f"docs/ai-ab-test-queryset.json을 신어휘로 옮긴 판본으로 채점하라."
            )
    return primary


def captured_route(value: str) -> str:
    """이미 캡처된 raw의 route 값을 신버전 어휘로 올린다(읽는 지점에서만).

    13.2 이후 라우터가 내는 값은 항상 신버전이다. 이 별칭표는 **구어휘 A/B/C로 캡처된
    옛 raw**를 위한 것이다 — 그런 파일을 지금 코드로 재채점하면 라우팅이 50/55 → 0/55로
    무너지고(review-4 실측), 멀티턴 하드 오염 게이트는 조건에 걸리지 않아 오염이 있어도
    조용히 통과한다(실측: 동일 오염 데이터가 route="A"면 contamination=0·gate_pass=True,
    "SQL"이면 1·False). DW-562가 막으려던 "전량 오판"이 방향만 바뀌어 되살아난 것이라,
    캡처 어휘를 읽는 지점에서 한 번 올려 준다. 신버전 캡처엔 별칭표가 안 걸려 무영향이다.

    ⚠️ 수치·상태 사본 주의(13.8 3차 리뷰 정정): 이 독스트링은 원래 "커밋된
    `docs/g2-baseline.json`(44개 전량)은 구어휘 A/B/C다"라고 단정했는데 **지금은 거짓**이다
    — DW-609가 2026-08-02에 재캡처해 그 파일은 47항목이고 route 값도 전부 신어휘다(실측).
    즉 현재 리포의 어떤 커밋된 raw도 이 별칭표를 타지 않는다. 여기 파일명·개수를 다시 적지
    말 것(사본은 늙는다) — 실제 파일을 열어 확인한다.

    `route_ok()`의 계약(actual은 번역하지 않는다)은 그대로다 — 어휘를 올리는 것은
    route_ok의 책임이 아니라 "구어휘로 캡처된 raw"라는 입력 파일의 성질이다.
    """
    return _LEGACY_ROUTE_ALIASES.get(value, value)


def route_ok(actual: str, primary: str, acceptable: list[str] | None) -> bool:
    """actual(캡처된 실제 route)과 primary/acceptable(큐리셋 골든 라벨)을 그대로 비교한다.

    양쪽이 같은 신 4값 어휘를 쓰므로 번역이 없다(DW-609 재설계). 구어휘로 캡처된 옛 raw만
    호출 전에 `captured_route()`로 올려서 넣는다 — 그건 큐리셋 어휘가 아니라 "입력 파일의
    성질"이라 읽는 지점에서 한 번 정규화하는 것이 맞다.

    두 경로가 모두 제품상 타당한 gray 케이스는 큐리셋의 `acceptable_paths`로 명시한다 —
    예전처럼 `A → {SQL, HYBRID}` 같은 **일괄** 번역으로 넓히지 않는다. 그 일괄 확장은
    "진짜 SQL 질의를 HYBRID로 오분류하는 버그"까지 정답으로 세어 가려버렸다.
    """
    allowed = {primary, *(acceptable or [primary])}
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

    # clean 카테고리의 SQL + HYBRID 결과집합 점수(사전식 ① 축). HYBRID를 여기 포함시키는 것이
    # DW-609 재설계의 핵심이다 — 전엔 A(구조형)만 세서, 13.6이 만든 가이드 질의확장이 회귀
    # 지표에 전혀 반영되지 않았다(게이트가 초록이어도 그 기능은 보고 있지 않았다).
    result_scores_clean: list[float] = []
    routing_correct = 0
    routing_total = 0
    # 가이드 인용(FR44) 관측 — HYBRID 문항에서만 센다. doc_hit_total이 0이면 그건 "인용이
    # 없다"가 아니라 "인용을 볼 문항이 없다"는 뜻이므로 요약에 분모까지 같이 남긴다.
    doc_hit_n = 0
    doc_hit_total = 0
    # 되묻기(FR46) 관측 — CLARIFY 문항에서만 센다. chips_unobserved는 러너가 clarify 페이로드를
    # 캡처하지 않은 옛 raw를 채점할 때 증가한다(질문 문구만 보고 판정했다는 표시).
    clarify_ok_n = 0
    clarify_total = 0
    clarify_chips_unobserved = 0
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
        # route는 captured_route()로 어휘를 올린 뒤 비교한다 — 안 그러면 같은 경로를 한 번은
        # "C", 한 번은 "REJECT"로 캡처한 raw(어휘 이관 중 부분 재캡처)가 "모델이 흔들린다"는
        # 거짓 flaky로 잡힌다(review-5: 다른 세 읽는 지점은 이미 정규화하는데 여기만 빠져 있었다).
        sigs = {(captured_route(r["route_last"]), tuple(r["ids_last"])) for r in usable_runs}
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
            acc = item.get("acceptable_paths")
            primary = _require_route_labels(item["primary_path"], acc, rid)
            r_ok = route_ok(captured_route(rep["route_last"]), primary, acc)
            rec["route"] = rep["route_last"]
            rec["route_ok"] = r_ok
            routing_total += 1
            if r_ok:
                routing_correct += 1

            if primary == "SQL":
                golden = run_golden_ids(item["predicate"])
                sc = score_path_a(rep["ids_last"], golden, item["predicate"])
                rec["score"] = sc
                if not gray:
                    result_scores_clean.append(sc["result"])
            elif primary == "HYBRID":
                # 결과집합(가이드가 실제로 좁혔나) + 인용(가이드가 실제로 쓰였나) 둘 다 본다.
                # 라우터가 다른 경로로 새서 매물이 0건이면 precision이 0이 되어 그대로 감점된다.
                golden = run_golden_ids(item["predicate"])
                sc = score_path_hybrid(rep["ids_last"], golden)
                rec["score"] = sc
                if not gray:
                    result_scores_clean.append(sc["result"])
                hit = doc_hit(rep["answer_last"], item.get("doc_refs"))
                rec["doc_hit"] = hit
                doc_hit_total += 1
                doc_hit_n += int(hit)
            elif primary == "CLARIFY":
                q_ok = clarify_question_ok(rep["answer_last"])
                clarify_total += 1
                if "clarify_last" in rep:
                    c_ok = q_ok and clarify_chips_ok(rep["clarify_last"])
                    rec["clarify_chips"] = (rep["clarify_last"] or {}).get("chips")
                else:
                    # 옛 캡처(칩 미기록) — 질문 문구만으로 판정하고, 그 사실을 남긴다.
                    c_ok = q_ok
                    clarify_chips_unobserved += 1
                    rec["clarify_chips_unobserved"] = True
                rec["clarify_ok"] = c_ok
                clarify_ok_n += int(c_ok)
            elif primary == "REJECT":
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
                turn_acc = turn.get("acceptable_paths")
                primary = _require_route_labels(turn["primary_path"], turn_acc, f"{rid}.t{ti}")
                r_ok = route_ok(captured_route(tr["route"]), primary, turn_acc)
                routing_total += 1
                if r_ok:
                    routing_correct += 1
                trec = {"turn": ti, "route": tr["route"], "route_ok": r_ok}
                # 하드 오염 게이트 — 카테고리 조건 "계승"은 sql_rag_node를 타는 경로(SQL·
                #   HYBRID — 13.2에서 HYBRID도 13.3 전까지 SQL과 동일 노드로 임시 배선됨)
                #   에서만 발생 가능. CLARIFY/REJECT에서 같은 차종이 결과에 떠도 그건 의미검색의
                #   우연이지 조건 잔존이 아니다(예: RESET이 CLARIFY로 정상 라우팅됐는데 doc_rag가
                #   중형차 1대 추천 → 오염 아님). tr["route"]는 캡처된 실제 route라 13.2 이후
                #   항상 신버전 어휘("A" 아님)이므로, 이 비교도 "SQL"로 갱신했었다(DW-562와
                #   같은 근본 원인). review-2·review-3이 지적한 대로 HYBRID도 같은 sql_rag_node를
                #   타므로 "SQL"만 검사하면 이 게이트가 HYBRID 경로의 조건 잔존을 조용히 놓친다
                #   (실측: route만 HYBRID로 바꾸면 contamination=0·gate_pass=True로 통과해버림) —
                #   그래서 두 route 모두 검사한다.
                # ✎ 2026-07-31(Story 13.3 리뷰): 위 "HYBRID도 같은 sql_rag_node를 탄다"는
                #   전제는 **이제 사실이 아니다** — 13.3이 HYBRID를 전용 hybrid_rag_node로
                #   재배선했다. 구조조건이 실제로 붙는 경로에서는 이 게이트가 여전히 옳지만,
                #   hybrid_rag_node가 구조조건을 못 뽑아 doc_rag_node로 폴백한 턴은 조건이
                #   하나도 안 붙은 순수 벡터검색인데도 route 라벨이 HYBRID라 여기서 하드
                #   오염으로 집계된다 — 바로 위 주석이 "오염 아님"이라고 못박은 CLARIFY/REJECT
                #   케이스와 같은 상황이다. 이번 스토리의 intent가 score_ab.py 변경을
                #   route_ok()로 한정해 손대지 않았다(DW-580).
                mnc = turn.get("must_not_contain")
                if mnc and captured_route(tr["route"]) in ("SQL", "HYBRID"):
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
                # dead-end(REJECT 턴)
                if primary == "REJECT" and turn.get("expect_redirect"):
                    if not is_redirect(tr["answer"]):
                        deadend += 1
                        trec["deadend"] = True
                # 되묻기 턴(CLARIFY) — 단일 문항과 같은 기준으로 센다.
                if primary == "CLARIFY":
                    q_ok = clarify_question_ok(tr["answer"])
                    clarify_total += 1
                    if "clarify" in tr:
                        c_ok = q_ok and clarify_chips_ok(tr["clarify"])
                        trec["clarify_chips"] = (tr["clarify"] or {}).get("chips")
                    else:
                        c_ok = q_ok
                        clarify_chips_unobserved += 1
                        trec["clarify_chips_unobserved"] = True
                    trec["clarify_ok"] = c_ok
                    clarify_ok_n += int(c_ok)
                # 결과집합 — SQL 턴은 경로 A 채점, HYBRID 턴은 precision + 인용 채점.
                if primary == "SQL" and turn.get("predicate"):
                    golden = run_golden_ids(turn["predicate"])
                    sc = score_path_a(tr["ids"], golden, turn["predicate"])
                    trec["score"] = sc
                    if not gray:
                        result_scores_clean.append(sc["result"])
                elif primary == "HYBRID" and turn.get("predicate"):
                    golden = run_golden_ids(turn["predicate"])
                    sc = score_path_hybrid(tr["ids"], golden)
                    trec["score"] = sc
                    if not gray:
                        result_scores_clean.append(sc["result"])
                    hit = doc_hit(tr["answer"], turn.get("doc_refs"))
                    trec["doc_hit"] = hit
                    doc_hit_total += 1
                    doc_hit_n += int(hit)
                turn_recs.append(trec)
            rec["turns"] = turn_recs

        per_item.append(rec)

    pin, pout = PRICE_PER_M.get(model, (0.0, 0.0))
    cost = total_in / 1e6 * pin + total_out / 1e6 * pout
    result_mean = sum(result_scores_clean) / len(result_scores_clean) if result_scores_clean else 0.0

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
        "result_n": len(result_scores_clean),
        "routing_correct": routing_correct,
        "routing_total": routing_total,
        # 가이드 인용·되묻기 관측(DW-609) — 게이트 판정에는 넣지 않고 지표로만 남긴다.
        # 분모(_total)를 함께 남기는 이유: 0/0과 0/12는 전혀 다른 상태인데 비율만 보면
        # 둘 다 0으로 읽힌다. 구셋이 정확히 그 상태였다(HYBRID 문항 0건 → 인용률 영구 0).
        "doc_hit_n": doc_hit_n,
        "doc_hit_total": doc_hit_total,
        "clarify_ok_n": clarify_ok_n,
        "clarify_total": clarify_total,
        "clarify_chips_unobserved": clarify_chips_unobserved,
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


def _observability_line(s: dict) -> str:
    """가이드 인용률·되묻기 발동률을 콘솔 한 줄로 — 분모가 0이면 "관측 대상 없음"이라고 말한다.

    "0%"와 "볼 문항이 없음"을 같은 화면 글자로 찍으면, 지표가 죽어 있는 상태가 정상처럼
    읽힌다(구셋이 정확히 그 상태였다 — DW-607/609). 사람이 보는 자리에서 구분한다.
    """
    def _ratio(n: int, total: int, zero_msg: str) -> str:
        return f"{n}/{total}" if total else zero_msg

    doc = _ratio(s.get("doc_hit_n", 0), s.get("doc_hit_total", 0), "해당 문항 없음 ⚠")
    clar = _ratio(s.get("clarify_ok_n", 0), s.get("clarify_total", 0), "해당 문항 없음 ⚠")
    line = f"  가이드 인용(HYBRID): {doc} | 되묻기 발동(CLARIFY): {clar}"
    if s.get("clarify_chips_unobserved"):
        line += f"  (칩 미캡처 {s['clarify_chips_unobserved']}건 — 질문 문구만으로 판정)"
    return line


def _resolve_evidence_path(raw_path: str) -> str:
    """리포트에 기록할 raw 경로를 해석한다(P7) — 스크래치패드 등 세션 한정 상대경로를 그대로
    남기면 그 세션이 끝난 뒤엔 산출물만 봐도 어느 파일을 가리키는지 되짚을 수 없다(DW-637
    "산출물만 봐도 방향을 되짚을 수 있어야 한다"는 목적 위반). resolve()해 API_ROOT(이 파일의
    api/ 루트) 기준 상대경로로 표현 가능하면 그걸 쓰고(리포 안 파일이 흔한 경우이므로 짧고
    이식성 있음), 리포 밖 경로(예: /tmp)면 해석된 절대경로 그대로 남긴다(폴백).

    ⚠️ repo-relative 표현은 항상 `/` 구분자로 낸다(P8) — `str(PurePath)`는 OS 네이티브
    구분자라 이 모듈의 독스트링이 문서화한 Windows(`.venv/Scripts/python.exe`)에서는
    `docs\\g2-baseline.json`이 나온다. 리포트는 OS를 건너 공유되는 커밋 산출물이고
    테스트도 `docs/g2-baseline.json`으로 못박혀 있으므로, 구분자를 플랫폼에 맡기지 않는다.
    (폴백인 리포 밖 절대경로는 그 OS의 실제 경로여야 의미가 있으므로 그대로 둔다.)
    """
    resolved = Path(raw_path).resolve()
    try:
        return resolved.relative_to(API_ROOT).as_posix()
    except ValueError:
        return str(resolved)


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

    # --out이 커밋된 G2 비교 근거를 가리키면 거부한다(DW-635 — run_phase_b.py와 목록 공유).
    if is_protected(args.out):
        ap.error(
            f"--out이 커밋된 G2 비교 근거({args.out})를 가리킵니다 — 덮어쓰면 채점 기준점이 "
            "사라집니다. 날짜형 리포트 경로(예: docs/g2-recapture-<YYYY-MM-DD>-report.json, "
            "실제 날짜로 치환)를 쓰세요 — 이미 커밋된 날짜형 파일은 재사용하지 마세요."
        )

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
        print(f"  결과집합정확도(clean SQL+HYBRID, n={baseline_only['result_n']}): {baseline_only['result_mean']:.3f}")
        print(f"  라우팅: {baseline_only['routing_correct']}/{baseline_only['routing_total']}")
        print(_observability_line(baseline_only))
        print(
            f"  flaky: {baseline_only['flaky_n']} | 오염(하드): {baseline_only['contamination']} | "
            f"소프트관찰: {baseline_only['soft_obs']} | dead-end: {baseline_only['deadend']} | "
            f"게이트: {'PASS' if baseline_only['gate_pass'] else 'FAIL'}"
        )
        print(f"리포트: {args.out}")
        print("=" * 70)
        # 1파일 모드도 게이트 탈락은 0이 아닌 코드로 끝낸다(13.9 독립 후속 리뷰) — 이 모드는
        # G2 2단계("이 캡처를 새 기준선으로 올린다")가 쓰는 자리라, 여기서 조용히 0을 내면
        # 뒤따르는 `cp … g2-baseline.json`이 오염·전량 실패 캡처를 기준선으로 승격시킨다.
        # 아래 2파일 모드와 같은 규칙이며, 리포트는 위에서 이미 썼으므로 산출물은 남는다.
        if not baseline_only["gate_pass"]:
            sys.exit(1)
        return

    baseline, candidate = summaries[0], summaries[1]

    verdict = lexicographic_winner(baseline, candidate)
    # 베이스라인 회귀 게이트(DW-626) — 예전엔 result_mean 한 축만 봤다. 13.4(되묻기)·13.6
    # (가이드 인용)이 통째로 죽어도 그 축들은 사람이 눈으로만 대조했다(리뷰가 뮤테이션으로
    # 실증: 인용 전량 제거·CLARIFY 전량 SQL 치환 둘 다 gate_pass:true로 통과했다). 이제 네
    # 축 전부를 자동 비교한다 — 하나라도 하락하면 regression_block이다.
    #
    # ⚠️ 세 축(routing_correct·doc_hit_n·clarify_ok_n)은 **원시 개수**다(코드리뷰 정정) —
    # result_mean처럼 문항 수로 나눈 평균이 아니다. baseline·candidate가 서로 다른 개수의
    # 문항을 채점했다면(부분 재캡처 등, coverage.scored_n 참조) 후보가 더 적게 채점됐다는
    # 이유만으로 이 세 개수가 항상 더 낮아 보여 실제로는 회귀가 아닌데 regression_block이
    # 뜬다. scored_n이 같을 때만 이 세 축을 신뢰하고, 다르면 "하락 아님"으로 조용히 넘기지
    # 않고 리포트에 검증 불가로 명시한다.
    coverage_matches = (
        baseline["coverage"]["scored_n"] == candidate["coverage"]["scored_n"]
    )
    # result_mean도 같은 종류의 커버리지 함정이 있다(코드리뷰 정정, P6) — 분모가 scored_n이
    # 아니라 result_n(clean SQL+HYBRID 채점 문항 수)이고, 그 값은 정확히 라우팅 스토리가
    # 흔드는 값이다(HYBRID로 새로 라우팅되는 문항이 늘면 result_n도 함께 늘어난다). result_n이
    # 다르면 평균끼리 비교해도 "더 많이/적게 채점된 평균"을 섞어 비교하는 셈이라, coverage_matches
    # 와 별도로 result_n도 확인한다.
    result_n_matches = baseline["result_n"] == candidate["result_n"]
    _count_axes = {
        "routing_correct": candidate["routing_correct"] < baseline["routing_correct"],
        "doc_hit_n": candidate["doc_hit_n"] < baseline["doc_hit_n"],
        "clarify_ok_n": candidate["clarify_ok_n"] < baseline["clarify_ok_n"],
    }
    regression_axes: dict = {}
    unverifiable_axes: list[str] = []
    if result_n_matches:
        regression_axes["result_mean"] = candidate["result_mean"] < baseline["result_mean"] - 1e-9
    else:
        unverifiable_axes.append("result_mean")
    if coverage_matches:
        regression_axes.update(_count_axes)
    else:
        unverifiable_axes.extend(_count_axes.keys())
    # ⚠️ 비교 축이 하나도 없는 경우(P4) — coverage_matches·result_n_matches가 **둘 다** 거짓이면
    #   네 축 전부가 unverifiable_axes로 빠져 regression_axes가 빈 dict가 된다. `any({})`는
    #   False라 그대로 두면 커밋된 리포트에 `regression_block: false`가 박히는데, 그건 "회귀를
    #   찾지 못했다"가 아니라 "아무것도 비교하지 못했다"이다 — 산출물만 읽는 다음 사람에게
    #   정반대로 읽힌다. 그 경우만 None(JSON에선 null = 판정 불가)으로 명시한다.
    #   gate_pass는 이미 unverifiable_axes로 걸러 False지만, regression_block 자체가 거짓말을
    #   하면 안 된다(B8 — 대장은 "안 한 것"과 "했는지 모르는 것"을 구별해야 한다).
    regression = any(regression_axes.values()) if regression_axes else None
    # DW-637 — 리포트의 baseline/candidate는 모델명 문자열이라, 같은 모델을 자기 자신과
    # 비교하면(13.9 재기준선처럼) 어느 파일이 baseline이었는지 산출물만으로 알 수 없다.
    # 원본 파일 경로를 함께 실어 순서(=방향)를 항상 되짚을 수 있게 한다.
    self_comparison = baseline["name"] == candidate["name"]
    report = {
        "baseline": baseline["name"], "candidate": candidate["name"],
        "baseline_raw": _resolve_evidence_path(args.raw[0]),
        "candidate_raw": _resolve_evidence_path(args.raw[1]),
        "self_comparison": self_comparison,
        "verdict": verdict, "regression_block": regression,
        "regression_axes": regression_axes, "unverifiable_axes": unverifiable_axes,
        # 위(4축) 회귀가 전부 없어도, 개수 축이 커버리지 불일치로 검증 불가 상태(unverifiable_axes)
        # 이거나 개별 summary 자체가 자기 게이트(오염·dead-end·미측정)에서 FAIL이면 top-level도
        # PASS라고 말하면 안 된다(P2) — 예전엔 `not regression`만 봐서 (a) 부분 재캡처로 세 축이
        # 전부 unverifiable이 돼도, (b) gray 문항의 오염처럼 result_mean에 안 잡히는 개별
        # summary 실패가 있어도 top-level gate_pass가 True로 나갔다(실측: RESET 오염이 gray
        # M6류 항목에서만 터지면 result_mean이 안 움직여 네 축 전부 초록인데 그 summary
        # 자신은 "게이트: FAIL"을 찍는 모순).
        "gate_pass": (not regression) and not unverifiable_axes and all(
            s["gate_pass"] for s in summaries
        ),
        "summaries": [
            {k: v for k, v in s.items() if k != "per_item"} for s in summaries
        ],
        "detail": {s["name"]: s["per_item"] for s in summaries},
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 70)
    if self_comparison:
        print(
            f"⚠️ baseline·candidate 모델명이 같습니다({baseline['name']}) — 파일 경로로만 "
            f"방향을 구분할 수 있습니다: baseline_raw={report['baseline_raw']}, "
            f"candidate_raw={report['candidate_raw']}"
        )
    if unverifiable_axes:
        print(f"⚠️ 검증 불가 축: {', '.join(unverifiable_axes)}")
        if not coverage_matches:
            print(
                f"  · 채점 문항 수가 다릅니다(baseline scored_n="
                f"{baseline['coverage']['scored_n']} vs candidate scored_n="
                f"{candidate['coverage']['scored_n']}) — 개수 기반 축(routing_correct·"
                "doc_hit_n·clarify_ok_n)은 부분 캡처를 회귀로 오판하지 않기 위해 판정에서 제외."
            )
        if not result_n_matches:
            print(
                f"  · result_mean 분모(result_n)가 다릅니다(baseline={baseline['result_n']} "
                f"vs candidate={candidate['result_n']}) — 라우팅 변화로 채점 대상 문항 수 자체가"
                " 달라져 평균을 직접 비교할 수 없으므로 result_mean도 판정에서 제외."
            )
    for s in summaries:
        print(f"[{s['name']}]")
        print(f"  결과집합정확도(clean SQL+HYBRID, n={s['result_n']}): {s['result_mean']:.3f}")
        print(f"  라우팅: {s['routing_correct']}/{s['routing_total']}")
        print(_observability_line(s))
        print(f"  flaky: {s['flaky_n']} | 오염(하드): {s['contamination']} | 소프트관찰: {s['soft_obs']} | dead-end: {s['deadend']} | 게이트: {'PASS' if s['gate_pass'] else 'FAIL'}")
        print(f"  토큰 in/out: {s['tokens_in']}/{s['tokens_out']} | 비용 ${s['cost_usd']:.4f} | 지연 {s['latency_ms_mean']:.0f}ms")
    print("-" * 70)
    print(f"사전식 승부: {verdict['winner']}  ({verdict['tier']}: {verdict['reason']})")
    # 최종 채택 = 회귀 게이트가 후보를 거부하면 베이스라인 유지(사전식이 후보 손을 들어도).
    if regression:
        final = baseline["name"]
        regressed = [axis for axis, hit in regression_axes.items() if hit]
        print(f"⚠️ 회귀 게이트 발동(하락 축: {', '.join(regressed)}) → 후보 채택 불가")
        print(f"➡️ 최종 채택: {final} (베이스라인 유지)")
    elif regression is None:
        # 위 P4 — 비교한 축이 0개다. "회귀 없음"이 아니라 "판정 불가"이므로 후보를 올리지 않는다.
        final = baseline["name"]
        print("⚠️ 비교 가능한 축이 0개(regression_block=null) → 회귀 여부를 판정하지 못함, 후보 채택 불가")
        print(f"➡️ 최종 채택: {final} (베이스라인 유지)")
    else:
        final = verdict["winner"] or baseline["name"]
        print(f"➡️ 최종 채택: {final}")
    report["final_adopt"] = final
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"리포트: {args.out}")
    print("=" * 70)

    # 게이트 탈락은 0이 아닌 코드로 종료한다(P3) — 예전엔 경고만 찍고 항상 0으로 끝나서,
    # 문서화된 `run_phase_b.py … && score_ab.py …` 체인이 진짜 회귀를 만나고도 그대로 다음
    # 단계로 넘어갔다(run_phase_b.py는 이미 같은 규칙으로 1을 낸다). 리포트 파일 쓰기와 콘솔
    # 요약은 위에서 끝났으므로 **산출물은 항상 남는다** — 종료 코드만 사실을 말하게 한다.
    if not report["gate_pass"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
