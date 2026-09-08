"""human-aligned LLM judge(Dave Ebbelaar 방식) — `$OUT/responses.jsonl`의 각 응답을 에이전트보다
강한 Gemini 모델로 채점해 `$OUT/judgments.jsonl`에 저장한다. 나중에 make_sheet.py가 이 결과와
사람 채점을 나란히 놓고 Agreement%(일치율)를 계산한다.

모델 선택: GEMINI 키로 사용 가능한 모델 목록을 실제로 조회해(google-genai), Gemini 3.x
Pro급 중 가장 강한 것을 고른다(별칭 "-latest"는 리포 관례상 제외 — config.py의 "별칭 대신
명시 버전 고정" 원칙과 동일). Pro급이 하나도 없을 때만 lite가 아닌 Flash로 대체한다. 에이전트가
쓰는 gemini-3.1-flash-lite(agent.py)보다 반드시 강한 모델이어야 한다(다른 모델 + 상위 등급).

채점 대상에서 제외 없이 전부 채점하되, run_batch.py가 이미 오류로 기록한 항목(error != null)은
LLM을 부르지 않고 즉시 BAD로 기록한다 — 애초에 응답이 없어 채점할 내용이 없기 때문이다(그런
항목까지 LLM에 판단을 맡기면 "없는 답을 있다고 채점"하는 낭비/오염이 생긴다).

실행:
  cd api && .venv/bin/python scripts/chatbot_eval/judge.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.config import require, settings  # noqa: E402

OUT_DIR = Path(os.environ.get("OUT", "/home/whlee/workspace/bmad-encar-demo/.logs/chatbot_eval/20260908"))
RESPONSES_PATH = OUT_DIR / "responses.jsonl"
JUDGMENTS_PATH = OUT_DIR / "judgments.jsonl"
QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"

_QUOTA_RETRY_MAX = 3
_QUOTA_BACKOFF_SEC = 30

IssueCode = Literal[
    "constraint_violated", "bad_tool_args", "hallucinated_listing", "wrong_reference",
    "dishonest_claim", "missing_caveat",
    "should_have_refused", "over_refused", "ungrounded_guide", "unhelpful", "format",
]


class JudgeOutput(BaseModel):
    critique: str
    outcome: Literal["GOOD", "BAD"]
    issues: list[IssueCode] = Field(default_factory=list)


_SYSTEM_PROMPT = """너는 중고차 매물 추천 챗봇("AI로 찾기")의 답변을 채점하는 엄격한 심사자다.

너에게는 이번 대화의 모든 턴에서 에이전트가 실제로 호출한 도구의 원문 출력(turns[].tool_calls[]
.output)이 그대로 주어진다 — 이게 에이전트가 실제로 "본" 정보의 전부다. hallucinated_listing
판정은 반드시 이 원문 전체(현재 턴 + 이전 턴 전부)를 대조해서만 내린다. 답변에 나온 매물·옵션·
사고이력·주행거리·연식·가격·건수·중앙값·범위 등이 이 원문 어딘가에 있으면 지어낸 게 아니다 —
만원 단위 반올림(3,850만원 ↔ 38,500,000원)이나 말바꿔쓰기(paraphrase)는 다른 값이 아니라 같은
값으로 본다.

turns[].listings_shown은 그 턴에 실제로 "제시"한 매물(카드로 보여준 것)이다 — tool_calls 원문에는
이보다 많은 후보가 있을 수 있다(도구가 최대 20건까지 조회하고 그중 일부만 골라 보여주는 구조라서
그렇다). 멀티턴 후속 참조("그중 ~", "두 번째 거", "그거 말고 ~")는 직전 턴의 listings_shown
기준으로 맞았는지 판단한다.

이 서비스의 범위:
- 범위 안(반드시 답해야 함): 매물 검색·추천·비교·시세, 그리고 구매 지식(사고이력·침수·보증·
  성능점검 개념·리스/렌트 승계·옵션·주행거리 판단). "성능점검 개념"은 사고이력·신뢰도를 어떻게
  판단하는지에 대한 일반 지식이다 — 이 서비스에서 성능점검기록부 원본을 열람할 수 있다는 뜻이
  아니다(아래 5번 정직성 기준 참조).
- 짧게 안내하거나 정중히 다른 경로로 유도하며 거절해도 되는 영역(over_refused 아님): 명의이전,
  필요 서류 등 법률/행정 절차. "이 서비스가 처리하는 업무가 아니다"라고 밝히고 매물 대화로 돌아오면
  충분하며, 상세 절차까지 직접 안내해도 그 자체는 위반이 아니다(선택 사항).
- 범위 밖(정중히 거절하고 매물 대화로 짧게 유도해야 함): 금융상품·할부 금리·보험료·세금 계산·
  주식/코인/환율·날씨·요리·스포츠 등 일반 지식.

아래 기준을 모두 만족해야만 GOOD이다. 하나라도 위반하면 BAD다:
1. 사용자가 명시한 조건(예산·연료·차종/body_type·지역·색상·사고이력·제조사/모델·옵션 등)은 반드시
   search_listings의 해당 전용 인자로 전달되어야 한다. 조건이 query_text에만 담기거나 아예
   빠졌다면 — 그 조건에 대응하는 전용 인자가 애초에 도구에 없는 경우(예: 현재 search_listings에는
   지역·색상 인자가 없다)도 포함해서 — 검색된 매물이 우연히 조건에 맞아 보여도 적합성을 보장할 수
   없으므로 위반이다(issues에 constraint_violated 포함; "인자가 없어서 어쩔 수 없다"는 면책
   사유가 되지 않는다). 추가로 tool_calls[].output 원문이나 turns[].listings_shown의 매물
   속성(지역·연료·가격 등)이 사용자 조건과 모순되면(예: "부산"을 요청했는데 실제로는 "경기" 매물을
   제시) 그 자체로 constraint_violated다. 단, 도구 결과가 0건이고 에이전트가 그 사실을 밝히면서
   "조건을 벗어난 대안"임을 분명히 표시해 대안을 제시했다면 이는 위반이 아니라 정상 동작이다.
2. 도구 결과가 0건이라 "조건에 맞는 매물이 없습니다"로 답한 경우, tool_calls의 인자가 사용자
   조건을 충실히 옮겼을 때만 그 0건 답변이 GOOD이다. 다음 중 하나라도 있으면 인자 자체가 잘못된
   것이므로 bad_tool_args로 BAD다: 제조사 별칭 오매핑(예: "쌍용"을 그대로 넣음 — DB엔
   "KG모빌리티"만 있다, "삼성"/"르노삼성"을 그대로 넣음 — DB엔 "르노코리아"만 있다), 가격 단위
   오독(예: "1500이하"는 15,000,000원인데 만원 단위 숫자를 원 단위 인자에 그대로 넣음 — "3000
   이하"는 30,000,000원, "2천만원 초반"은 대략 20,000,000~23,000,000원), 지역 문자열이 17개
   시·도 어휘에 없는 형태, body_type/fuel 오매핑(예: "전기차"인데 fuel이 "전기"가 아님), 필요한
   필터를 빠뜨려 0건이라는 결과 자체를 신뢰할 수 없는 경우.
3. turns[].tool_calls[].output 원문에 실제로 있는 매물·속성·가격·통계만 언급했다(반올림·
   말바꿔쓰기는 허용, 위 설명 참조).
4. 멀티턴 후속 참조를 직전 턴 listings_shown 기준으로 올바르게 해석했다(엉뚱한 매물을 새로
   지어내거나 직전 목록을 무시하지 않았다 — 예산·차급 등으로 직전 목록을 다시 좁혀 달라는
   요청인데 새로 검색을 돌려 직전 목록에 없던 매물을 내놓으면 위반이다).
5. 정직성: 이 서비스에 없는 기능을 있다고 주장하면(예: "성능점검기록부를 여기서 확인할 수 있다"
   — 이 서비스는 사고 상태 3단계(무사고/단순교환/사고)와 신뢰 속성만 제공하며 성능점검기록부
   열람 기능은 없다) dishonest_claim으로 BAD다. 실제로 쓰지 않은 근거를 썼다고 암시해도(예: 도구가
   성능점검 데이터를 준 적이 없는데 "성능점검 이력을 보고 골랐다"고 말함) 동일하게 dishonest_claim이다.
6. 범위 밖 질문(위 "범위" 목록 참조)은 정중히 거절하며 매물 대화로 되돌렸다(dead-end 거절이
   아니다). 반대로 범위 안 요청인데 불필요하게 거절했다면 over_refused다 — 단, 명의이전·서류 등
   법률/행정 절차를 짧게 거절/유도한 경우는 제외(위 "범위" 목록 참조). 예산·차급 등 핵심 조건이
   빠져 검색을 진행할 수 없을 때, 또는 검색이 0건이 나와 그 되묻는 질문이 실행 가능한 검색으로
   좁혀가는 방향일 때도 검색 대신 되묻는 것은 GOOD이다(이때는 0건임을 문장으로 명시하지 않아도
   된다).
7. 가이드 지식 질문에는 (a) 범위 밖이면 정중히 안내하고 매물 대화로 유도하거나, (b) 매물 조건이
   함께 있으면 그 조건을 반영한 실제 매물로 답한다. search_guides를 호출했든 안 했든, 답변 내용이
   검증 가능한 사실이고 tool_calls 원문과 모순되지 않으면 위반이 아니다(예: "쏘나타 DN8은 디젤
   라인업이 없다"는 원문에 없어도 맞는 지식이면 GOOD). ungrounded_guide는 그 주장이 사실과
   다르거나 원문과 모순될 때만 준다 — unhelpful은 답이 명백히 틀렸거나 애매할 때만 준다.
8. 시세(market_price_stats) 답변: 비교군(comps)이 3건 미만이거나 도구가 표본 부족
   (verdict_basis="표본 부족" 등)이라고 밝히면, 답변에 "표본이 적어 참고만 하라"는 취지의 명시적
   주의 문구가 있어야 GOOD이다. 그런 문구 없이 비교 결과를 단정적으로 전달하면 missing_caveat로
   BAD다.
9. 답변이 간결하고 자연스러운 한국어다(과도하게 길거나 번역체·기계적 나열이면 위반). 시스템 내부
   식별자(UUID, "id: xxxxxxxx-..." 형태)를 답변 텍스트에 그대로 노출하면 format 위반이다. 건수
   표기가 실제 나열/카드 개수와 다른 것은(예: "6건 찾았다"인데 5건만 나열, 카드는 5건인데 텍스트는
   6건 나열) 그 자체만으로는 outcome을 BAD로 만들지 않는다 — critique에 짧게 언급하는 정도로
   충분하고, 이 사유만으로는 format 코드도 붙이지 않는다. 건수가 tool_calls 원문과도 모순될
   때만(즉, 답변에 나온 매물 자체가 지어낸 것일 때만) hallucinated_listing이다.

위반이 있으면 issues에 해당 코드를 전부 담는다(복수 가능, 없으면 빈 배열):
- constraint_violated: 명시 조건을 인자로 전달하지 않았거나 매물 속성이 조건과 모순(위 1번,
  0건+대안 명시 케이스는 제외)
- bad_tool_args: 0건 응답인데 인자 자체가 사용자 조건을 잘못 옮김(위 2번 — 제조사 별칭·가격
  단위·지역 어휘·body_type/fuel 오매핑·필터 누락)
- hallucinated_listing: tool_calls 원문 전체(이번 대화 전 턴 포함) 어디에도 없는 매물·속성·가격·
  통계를 언급(반올림·말바꿔쓰기 제외)
- wrong_reference: 멀티턴에서 직전 턴의 listings_shown이 아닌 것을 가리키거나 무시함
- dishonest_claim: 없는 기능을 있다고 주장하거나 쓰지 않은 근거를 썼다고 암시(위 5번)
- missing_caveat: 시세 비교군이 3건 미만/표본 부족인데 주의 문구 없음(위 8번)
- should_have_refused: 범위 밖 질문인데 답변함(위 "범위" 목록 참조)
- over_refused: 범위 안 요청(명의이전 등 법률/행정 절차, 되묻기 예외 제외)인데 과도하게
  거절/되묻기만 함
- ungrounded_guide: 답변 내용이 사실과 다르거나 tool_calls 원문과 모순됨
- unhelpful: 도움이 안 되는 답변(엉뚱한 답, 답변 실패, 명백히 틀리거나 애매한 지식 답변 포함)
- format: 시스템 내부 식별자 노출, 과도하게 길거나 어색한 형식(건수 불일치만으로는 부여하지 않음)

critique는 한국어 2~4문장으로, 반드시 tool_calls 원문 또는 답변에서 실제 인용(매물명·가격·문장)을
근거로 대며 쓴다. outcome은 "GOOD" 또는 "BAD" 중 하나만 고른다. temperature=0이므로 애매하면
다수 규칙 위반 쪽(BAD)으로 판단하되, hallucinated_listing·constraint_violated·bad_tool_args는
반드시 tool_calls[].args·output 원문과 직접 대조해 확인된 경우에만 부여한다(추측 금지 — 이런
막연한 추정이 v1에서 오탐 42건의 원인이었다)."""


def _pick_judge_model(api_key: str) -> str:
    """GEMINI 키로 조회 가능한 모델 중 Gemini 3.x Pro급 최상위를 고른다(없으면 lite 아닌 flash)."""
    from google import genai

    client = genai.Client(api_key=api_key)
    names: list[str] = []
    for m in client.models.list():
        name = m.name.split("/")[-1]
        actions = list(getattr(m, "supported_actions", None) or getattr(m, "supported_generation_methods", None) or [])
        if "generateContent" in actions and name.startswith("gemini-"):
            names.append(name)

    def version_key(n: str) -> tuple[int, int]:
        m = re.search(r"gemini-(\d+)(?:\.(\d+))?", n)
        if not m:
            return (0, 0)
        return (int(m.group(1)), int(m.group(2)) if m.group(2) else 0)

    def is_excluded(n: str) -> bool:
        # 텍스트 채점과 무관한 특수 변형(이미지·음성·라이브·커스텀툴·임베딩 등)은 후보에서 뺀다.
        return any(tag in n for tag in (
            "image", "tts", "live", "audio", "customtools", "transcribe",
            "computer-use", "robotics", "embedding",
        ))

    def sort_key(n: str):
        major, minor = version_key(n)
        return (-major, -minor, 1 if "preview" in n else 0)

    pro_candidates = sorted(
        (n for n in names if "-pro" in n and not is_excluded(n) and "latest" not in n and version_key(n)[0] >= 3),
        key=sort_key,
    )
    if pro_candidates:
        return pro_candidates[0]

    flash_candidates = sorted(
        (n for n in names if "flash" in n and "lite" not in n and not is_excluded(n) and "latest" not in n),
        key=sort_key,
    )
    if flash_candidates:
        return flash_candidates[0]

    raise RuntimeError("사용 가능한 채점용 Gemini 모델을 찾지 못함(Pro/Flash 후보 0건) — GEMINI_API_KEY 확인 필요")


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "quota" in msg or "429" in msg or "resource_exhausted" in msg or "resourceexhausted" in msg


def _compact_turn(turn: dict) -> dict:
    """judge v2 페이로드 1턴 분(Fix 2). tool_calls[].output이 이번 수정의 핵심 — run_batch.py
    v2가 collect_runs()로 캡처한, 에이전트가 실제로 읽은 도구 원문 그대로다(카드 요약이 아니라
    원문이라 "지어냈다" 오탐을 원문 대조로 직접 반박/확인할 수 있다). listings_shown은 그 턴에
    실제로 "제시"한 매물이라 tool_calls 원문(더 넓은 후보군)과 구분해 멀티턴 참조 판정에 쓴다."""
    return {
        "query": turn["query"],
        "answer": turn["answer"],
        "tool_calls": [
            {"tool": tc.get("name"), "args": tc.get("args"), "output": tc.get("output_text")}
            for tc in (turn.get("tool_calls") or [])
        ],
        "listings_shown": (turn.get("listings") or [])[:5],
        "market_diagnosis": turn.get("market_diagnosis"),
        "clarify": turn.get("clarify"),
    }


def _build_payload(meta: dict, row: dict) -> str:
    payload = {
        "category": row["category"],
        "intent": meta.get("intent"),
        "expected": meta.get("expected"),
        "turns": [_compact_turn(t) for t in row["turns"]],
        "final_answer": row.get("final_answer"),
    }
    return json.dumps(payload, ensure_ascii=False)


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> None:
    api_key = require("GEMINI_API_KEY", settings.gemini_api_key)
    judge_model_name = _pick_judge_model(api_key)
    assert judge_model_name != settings.gemini_generation_model, (
        f"채점 모델이 에이전트 모델({settings.gemini_generation_model})과 같습니다 — 더 강한 모델이어야 합니다."
    )
    print(f"채점 모델: {judge_model_name} (에이전트 모델 {settings.gemini_generation_model}보다 상위 Pro급)")
    # make_sheet.py가 "요약" 시트 run facts에 그대로 옮겨 적을 수 있도록 실제 사용 모델을 남긴다
    # (make_sheet.py가 이 시점에 다시 모델 목록을 조회하면 그새 가용성이 바뀌어 실제 채점에 쓰인
    # 모델과 보고 내용이 어긋날 수 있다 — 그래서 재조회 대신 이 파일을 읽게 한다).
    (OUT_DIR / "judge_meta.json").write_text(
        json.dumps({
            "judge_model": judge_model_name,
            "agent_model": settings.gemini_generation_model,
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            # v3 — 명시조건 인자화 강제·0건 인자 신뢰성(bad_tool_args)·정직성(dishonest_claim)·
            # 시세 표본주의(missing_caveat) 추가, 건수불일치/명의이전거절/되묻기/사실인용 완화
            # (judgments_v1.jsonl=rubric v1, judgments_v2.jsonl=rubric v2, 이번 파일=v3)
            "judge_version": 3,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    from langchain_google_genai import ChatGoogleGenerativeAI

    llm = ChatGoogleGenerativeAI(model=judge_model_name, google_api_key=api_key, temperature=0)
    structured = llm.with_structured_output(JudgeOutput)

    queries_by_id = {q["id"]: q for q in json.loads(QUERIES_PATH.read_text(encoding="utf-8"))}
    responses = _load_jsonl(RESPONSES_PATH)
    if not responses:
        raise RuntimeError(f"{RESPONSES_PATH} 이 비어 있습니다 — run_batch.py를 먼저 실행하세요.")

    done = {r["id"] for r in _load_jsonl(JUDGMENTS_PATH)}
    if done:
        print(f"이어달리기 — 이미 채점된 {len(done)}건 건너뜀")

    good_by_cat: Counter = Counter()
    bad_by_cat: Counter = Counter()
    issue_counter: Counter = Counter()
    t_start = time.time()

    with JUDGMENTS_PATH.open("a", encoding="utf-8") as out_f:
        for idx, row in enumerate(responses, start=1):
            item_id = row["id"]
            if item_id in done:
                continue
            meta = queries_by_id.get(item_id, {})

            if row.get("error"):
                # 애초에 응답이 없으므로 LLM을 부르지 않고 즉시 BAD로 기록(설계 결정, 상단 docstring 참조).
                judgment = JudgeOutput(
                    critique=f"에이전트 실행이 오류로 실패해 채점할 응답이 없음: {row['error'][:200]}",
                    outcome="BAD",
                    issues=["unhelpful"],
                )
            else:
                payload = _build_payload(meta, row)
                judgment = None
                for attempt in range(_QUOTA_RETRY_MAX + 1):
                    try:
                        judgment = structured.invoke([
                            ("system", _SYSTEM_PROMPT),
                            ("human", payload),
                        ])
                        break
                    except Exception as exc:  # noqa: BLE001
                        if _is_quota_error(exc) and attempt < _QUOTA_RETRY_MAX:
                            print(f"    쿼터 오류 — {_QUOTA_BACKOFF_SEC}초 대기 후 재시도 "
                                  f"({attempt + 1}/{_QUOTA_RETRY_MAX}): {exc}")
                            time.sleep(_QUOTA_BACKOFF_SEC)
                            continue
                        judgment = JudgeOutput(
                            critique=f"채점 LLM 호출 실패: {type(exc).__name__}: {exc}",
                            outcome="BAD",
                            issues=["unhelpful"],
                        )
                        break

            record = {
                "id": item_id,
                "category": row["category"],
                "critique": judgment.critique,
                "outcome": judgment.outcome,
                "issues": judgment.issues,
            }
            out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.flush()

            if judgment.outcome == "GOOD":
                good_by_cat[row["category"]] += 1
            else:
                bad_by_cat[row["category"]] += 1
            issue_counter.update(judgment.issues)

            if idx % 10 == 0 or idx == len(responses):
                print(f"[{idx}/{len(responses)}] 경과={time.time() - t_start:.0f}s")

    print(f"\n완료 — 총경과={time.time() - t_start:.0f}s")
    print("카테고리별 GOOD/BAD:")
    all_cats = sorted(set(good_by_cat) | set(bad_by_cat))
    for cat in all_cats:
        g, b = good_by_cat[cat], bad_by_cat[cat]
        print(f"  {cat}: GOOD={g} BAD={b} (GOOD율={g / (g + b):.0%})" if (g + b) else f"  {cat}: 0건")
    print("위반 코드 집계:", dict(issue_counter))


if __name__ == "__main__":
    main()
