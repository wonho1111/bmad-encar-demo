"""judge v2→v3 정렬 비교 엑셀 산출 — `$OUT/chatbot_alignment_v3.xlsx`.

judge v1(카드 요약만 보고 채점) 라운드는 이미 `chatbot_alignment.xlsx`로 사람이 채점해
`human_labels.json`(100건 — id·category·human·human_critique 등)을 만들었다. 이 스크립트는
그 결과를 고정된 정답으로 삼아 judge v2와 v3(judge.py rubric v3, `$OUT/judgments.jsonl`)를
나란히 놓고 Agreement%(사람과의 일치율)가 v2→v3에서 얼마나 개선됐는지 보여준다 — 그래서 이번
평가표의 Human Outcome/Critique는 사람이 채울 빈 칸이 아니라 human_labels.json에서 그대로
가져온 값이다(Alignment는 여전히 셀 수식으로 계산해 원본 judgments 파일을 다시 돌리지 않고도
엑셀에서 바로 검산할 수 있게 한다).

시트 3개:
  평가표  — 항목별 1행. Human Critique/Outcome은 human_labels.json에서 채우고, Judge v2
            Outcome과 Judge v3 Critique/Outcome은 각각 judgments_v2.jsonl/judgments.jsonl(v3)
            에서 채운다. Alignment v2·v3는 사람 판정과 각 버전의 일치 여부를 셀 수식으로 계산한다.
  요약    — 카테고리별 Agreement(v2 vs v3), 카테고리별 GOOD율(v1 vs v2 vs v3), 위반 코드
            집계(v1 vs v2 vs v3), 실행 사실(날짜·에이전트/채점 모델·DB·건수).
  질의목록 — queries.json 원본(추적용).

실행:
  cd api && .venv/bin/python scripts/chatbot_eval/make_sheet.py
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

OUT_DIR = Path(os.environ.get("OUT", "/home/whlee/workspace/bmad-encar-demo/.logs/chatbot_eval/20260908"))
QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"
RESPONSES_PATH = OUT_DIR / "responses.jsonl"
HUMAN_LABELS_PATH = OUT_DIR / "human_labels.json"
JUDGMENTS_PATH = OUT_DIR / "judgments.jsonl"  # v3(rubric v3) — judge.py 최신 실행 결과
JUDGE_META_PATH = OUT_DIR / "judge_meta.json"
JUDGMENTS_V2_PATH = OUT_DIR / "judgments_v2.jsonl"  # rubric v2 백업(judge.py 재실행 전 mv)
JUDGE_META_V2_PATH = OUT_DIR / "judge_meta_v2.json"
# v1(구 rubric, 카드 요약만 보고 채점) 판정 백업 — 요약 시트 GOOD율 표에서 v1/v2/v3를 나란히
# 보여주는 데만 쓴다. 없어도(파일 부재) _load_jsonl이 빈 리스트를 돌려줘 죽지 않는다.
JUDGMENTS_V1_PATH = OUT_DIR / "judgments_v1.jsonl"
JUDGE_META_V1_PATH = OUT_DIR / "judge_meta_v1.json"
XLSX_PATH = OUT_DIR / "chatbot_alignment_v3.xlsx"

HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
HEADER_FONT = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")

COLUMNS = [
    "ID", "범주", "Input(전 턴, 줄바꿈)", "Model Response(최종 답변)", "도구 원문(요약)",
    "Human Critique", "Human Outcome", "Judge v2 Outcome", "Judge v3 Critique",
    "Judge v3 Outcome", "판정 코드 v3", "Alignment v2", "Alignment v3",
]
COL_WIDTHS = [6, 8, 36, 40, 38, 32, 12, 14, 40, 14, 28, 11, 11]


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


def _load_human_labels(path: Path) -> dict[str, dict]:
    """human_labels.json은 jsonl이 아니라 JSON 배열이라 _load_jsonl과 별도 로더가 필요하다."""
    if not path.exists():
        return {}
    return {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))}


def _input_text(turns: list[dict]) -> str:
    queries = [t["query"] for t in turns]
    if len(queries) == 1:
        return queries[0]
    return "\n".join(f"{i + 1}. {q}" for i, q in enumerate(queries))


def _tool_raw_summary(turns: list[dict]) -> str:
    """모든 턴의 tool_calls output_text(judge가 실제로 본 원문)를 이어붙여 앞 400자만
    남긴다 — 매물 카드 요약이 아니라 도구가 실제로 뭐라고 답했는지 원문으로 대조하는 열."""
    parts = [
        tc.get("output_text") or ""
        for turn in turns
        for tc in (turn.get("tool_calls") or [])
    ]
    return " | ".join(p for p in parts if p)[:400]


def _build_평가표(
    wb: Workbook,
    queries: list[dict],
    responses_by_id: dict,
    judgments_v3_by_id: dict,
    judgments_v2_by_id: dict,
    human_labels_by_id: dict,
) -> int:
    ws = wb.active
    ws.title = "평가표"

    n = len(queries)
    last_row = n + 1  # 헤더가 1행이므로 데이터는 2..last_row

    # 상단 요약 셀(오른쪽) — Alignment v2는 L열(12), Alignment v3는 M열(13).
    ws["O1"] = "Agreement% v2"
    ws["O1"].font = HEADER_FONT
    ws["P1"] = f'=IFERROR(AVERAGE(L2:L{last_row}),"")'
    ws["P1"].number_format = "0%"
    ws["O2"] = "Agreement% v3"
    ws["O2"].font = HEADER_FONT
    ws["P2"] = f'=IFERROR(AVERAGE(M2:M{last_row}),"")'
    ws["P2"].number_format = "0%"

    for col_idx, title in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for col_idx, width in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    for i, item in enumerate(queries):
        row = i + 2
        resp = responses_by_id.get(item["id"])
        judg3 = judgments_v3_by_id.get(item["id"])
        judg2 = judgments_v2_by_id.get(item["id"])
        human = human_labels_by_id.get(item["id"])

        turns = resp["turns"] if resp else []
        values = [
            item["id"],
            item["category"],
            _input_text(item["turns"]),
            (resp or {}).get("final_answer") or "",
            _tool_raw_summary(turns),
            (human or {}).get("human_critique") or "",
            (human or {}).get("human") or "",
            (judg2 or {}).get("outcome", ""),
            (judg3 or {}).get("critique", ""),
            (judg3 or {}).get("outcome", ""),
            ", ".join((judg3 or {}).get("issues") or []),
            None,  # Alignment v2 — 수식으로 채움(아래)
            None,  # Alignment v3 — 수식으로 채움(아래)
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            if col_idx in (3, 4, 5, 6, 9):
                cell.alignment = WRAP
            else:
                cell.alignment = TOP
        # G=Human Outcome(7), H=Judge v2 Outcome(8), J=Judge v3 Outcome(10).
        ws.cell(row=row, column=12, value=f'=IF(OR(G{row}="",H{row}=""),"",IF(G{row}=H{row},1,0))')
        ws.cell(row=row, column=13, value=f'=IF(OR(G{row}="",J{row}=""),"",IF(G{row}=J{row},1,0))')

    ws.freeze_panes = "A2"
    return last_row


def _build_요약(
    wb: Workbook,
    queries: list[dict],
    judgments_v3_by_id: dict,
    judgments_v2_by_id: dict,
    judgments_v1_by_id: dict,
    human_labels_by_id: dict,
) -> None:
    ws = wb.create_sheet("요약")
    meta_v3 = json.loads(JUDGE_META_PATH.read_text(encoding="utf-8")) if JUDGE_META_PATH.exists() else {}
    meta_v2 = json.loads(JUDGE_META_V2_PATH.read_text(encoding="utf-8")) if JUDGE_META_V2_PATH.exists() else {}
    meta_v1 = json.loads(JUDGE_META_V1_PATH.read_text(encoding="utf-8")) if JUDGE_META_V1_PATH.exists() else {}

    r = 1
    ws.cell(row=r, column=1, value="실행 사실").font = HEADER_FONT
    r += 1
    facts = [
        ("응답 생성일(responses.jsonl)", "2026-09-08"),
        ("에이전트 모델", meta_v3.get("agent_model", "확인불가")),
        ("채점 모델 v1", f"{meta_v1.get('judge_model', '확인불가')} ({meta_v1.get('started_at', '?')})"),
        ("채점 모델 v2", f"{meta_v2.get('judge_model', '확인불가')} ({meta_v2.get('started_at', '?')})"),
        ("채점 모델 v3(현재 판정)", f"{meta_v3.get('judge_model', '확인불가')} "
         f"(judge_version={meta_v3.get('judge_version', '?')}, {meta_v3.get('started_at', '?')})"),
        ("DB", "로컬 Supabase(127.0.0.1:55322, 시드 매물 166건)"),
        ("입력 건수(n)", len(queries)),
    ]
    for label, value in facts:
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=value)
        r += 1

    # --- 카테고리별 Agreement(사람 vs 판정) — v2 vs v3 ---
    r += 1
    ws.cell(row=r, column=1, value="카테고리별 Agreement(사람 vs 판정) — v2 vs v3").font = HEADER_FONT
    r += 1
    headers_agree = ["범주", "건수", "v2 일치", "v2 Agreement%", "v3 일치", "v3 Agreement%"]
    for c, h in enumerate(headers_agree, start=1):
        ws.cell(row=r, column=c, value=h).font = HEADER_FONT
    r += 1

    def _agreement_by_cat() -> dict[str, list]:
        # {category: [n, v2_agree, v3_agree]}, "전체"는 합산 행으로 별도 유지.
        out: dict[str, list] = {}
        for item in queries:
            cat = item["category"]
            human = human_labels_by_id.get(item["id"]) or {}
            human_outcome = human.get("human")
            v2_outcome = (judgments_v2_by_id.get(item["id"]) or {}).get("outcome")
            v3_outcome = (judgments_v3_by_id.get(item["id"]) or {}).get("outcome")
            row_ = out.setdefault(cat, [0, 0, 0])
            row_[0] += 1
            if human_outcome is not None and human_outcome == v2_outcome:
                row_[1] += 1
            if human_outcome is not None and human_outcome == v3_outcome:
                row_[2] += 1
        return out

    agree_by_cat = _agreement_by_cat()
    total_n = sum(v[0] for v in agree_by_cat.values())
    total_v2 = sum(v[1] for v in agree_by_cat.values())
    total_v3 = sum(v[2] for v in agree_by_cat.values())
    ws.cell(row=r, column=1, value="전체")
    ws.cell(row=r, column=2, value=total_n)
    ws.cell(row=r, column=3, value=total_v2)
    ws.cell(row=r, column=4, value=(total_v2 / total_n if total_n else None)).number_format = "0%"
    ws.cell(row=r, column=5, value=total_v3)
    ws.cell(row=r, column=6, value=(total_v3 / total_n if total_n else None)).number_format = "0%"
    for c in range(1, 7):
        ws.cell(row=r, column=c).font = Font(bold=True)
    r += 1
    for cat in sorted(agree_by_cat):
        n_cat, v2_agree, v3_agree = agree_by_cat[cat]
        ws.cell(row=r, column=1, value=cat)
        ws.cell(row=r, column=2, value=n_cat)
        ws.cell(row=r, column=3, value=v2_agree)
        ws.cell(row=r, column=4, value=(v2_agree / n_cat if n_cat else None)).number_format = "0%"
        ws.cell(row=r, column=5, value=v3_agree)
        ws.cell(row=r, column=6, value=(v3_agree / n_cat if n_cat else None)).number_format = "0%"
        r += 1

    # --- 카테고리별 GOOD율 — v1 vs v2 vs v3 ---
    def _cat_counts(judg_by_id: dict) -> dict[str, Counter]:
        counts: dict[str, Counter] = {}
        for item in queries:
            judg = judg_by_id.get(item["id"])
            outcome = (judg or {}).get("outcome")
            counts.setdefault(item["category"], Counter())[outcome or "미채점"] += 1
        return counts

    v1_counts = _cat_counts(judgments_v1_by_id)
    v2_counts = _cat_counts(judgments_v2_by_id)
    v3_counts = _cat_counts(judgments_v3_by_id)

    r += 1
    ws.cell(row=r, column=1, value="카테고리별 GOOD율 — v1(구 rubric) vs v2(도구원문 근거) vs v3(조건 인자화·정직성·표본주의)").font = HEADER_FONT
    r += 1
    headers_good = [
        "범주", "v1 GOOD", "v1 BAD", "v1 GOOD율",
        "v2 GOOD", "v2 BAD", "v2 GOOD율",
        "v3 GOOD", "v3 BAD", "v3 GOOD율",
    ]
    for c, h in enumerate(headers_good, start=1):
        ws.cell(row=r, column=c, value=h).font = HEADER_FONT
    r += 1
    all_cats = sorted(set(v1_counts) | set(v2_counts) | set(v3_counts))
    for cat in all_cats:
        g1, b1 = v1_counts.get(cat, Counter()).get("GOOD", 0), v1_counts.get(cat, Counter()).get("BAD", 0)
        g2, b2 = v2_counts.get(cat, Counter()).get("GOOD", 0), v2_counts.get(cat, Counter()).get("BAD", 0)
        g3, b3 = v3_counts.get(cat, Counter()).get("GOOD", 0), v3_counts.get(cat, Counter()).get("BAD", 0)
        ws.cell(row=r, column=1, value=cat)
        ws.cell(row=r, column=2, value=g1)
        ws.cell(row=r, column=3, value=b1)
        ws.cell(row=r, column=4, value=(g1 / (g1 + b1) if (g1 + b1) else None)).number_format = "0%"
        ws.cell(row=r, column=5, value=g2)
        ws.cell(row=r, column=6, value=b2)
        ws.cell(row=r, column=7, value=(g2 / (g2 + b2) if (g2 + b2) else None)).number_format = "0%"
        ws.cell(row=r, column=8, value=g3)
        ws.cell(row=r, column=9, value=b3)
        ws.cell(row=r, column=10, value=(g3 / (g3 + b3) if (g3 + b3) else None)).number_format = "0%"
        r += 1

    # --- 위반 코드 집계 — v1 vs v2 vs v3 ---
    r += 1
    ws.cell(row=r, column=1, value="위반 코드 집계 — v1 vs v2 vs v3").font = HEADER_FONT
    r += 1
    issue_v1: Counter = Counter()
    for judg in judgments_v1_by_id.values():
        issue_v1.update(judg.get("issues") or [])
    issue_v2: Counter = Counter()
    for judg in judgments_v2_by_id.values():
        issue_v2.update(judg.get("issues") or [])
    issue_v3: Counter = Counter()
    for judg in judgments_v3_by_id.values():
        issue_v3.update(judg.get("issues") or [])
    headers_issue = ["코드", "v1 건수", "v2 건수", "v3 건수"]
    for c, h in enumerate(headers_issue, start=1):
        ws.cell(row=r, column=c, value=h).font = HEADER_FONT
    r += 1
    all_codes = sorted(
        set(issue_v1) | set(issue_v2) | set(issue_v3),
        key=lambda code: -(issue_v1[code] + issue_v2[code] + issue_v3[code]),
    )
    for code in all_codes:
        ws.cell(row=r, column=1, value=code)
        ws.cell(row=r, column=2, value=issue_v1.get(code, 0))
        ws.cell(row=r, column=3, value=issue_v2.get(code, 0))
        ws.cell(row=r, column=4, value=issue_v3.get(code, 0))
        r += 1

    for col, width in zip("ABCDEFGHIJ", (46, 14, 10, 12, 10, 10, 12, 10, 10, 12)):
        ws.column_dimensions[col].width = width


def _build_질의목록(wb: Workbook, queries: list[dict]) -> None:
    ws = wb.create_sheet("질의목록")
    headers = ["id", "category", "turns", "intent", "expected"]
    for col_idx, title in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for i, item in enumerate(queries):
        row = i + 2
        turns_text = " / ".join(t["query"] for t in item["turns"])
        values = [item["id"], item["category"], turns_text, item.get("intent", ""), item.get("expected", "")]
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            cell.alignment = WRAP if col_idx in (3, 4, 5) else TOP
    for col, width in zip("ABCDE", (6, 8, 50, 40, 45)):
        ws.column_dimensions[col].width = width
    ws.freeze_panes = "A2"


def main() -> None:
    queries = json.loads(QUERIES_PATH.read_text(encoding="utf-8"))
    responses_by_id = {r["id"]: r for r in _load_jsonl(RESPONSES_PATH)}
    judgments_v3_by_id = {j["id"]: j for j in _load_jsonl(JUDGMENTS_PATH)}
    judgments_v2_by_id = {j["id"]: j for j in _load_jsonl(JUDGMENTS_V2_PATH)}
    judgments_v1_by_id = {j["id"]: j for j in _load_jsonl(JUDGMENTS_V1_PATH)}  # 없어도 빈 dict
    human_labels_by_id = _load_human_labels(HUMAN_LABELS_PATH)

    if not responses_by_id:
        raise RuntimeError(f"{RESPONSES_PATH} 이 비어 있습니다 — run_batch.py를 먼저 실행하세요.")
    if not judgments_v3_by_id:
        raise RuntimeError(f"{JUDGMENTS_PATH} 이 비어 있습니다 — judge.py(v3)를 먼저 실행하세요.")
    if not judgments_v2_by_id:
        raise RuntimeError(f"{JUDGMENTS_V2_PATH} 이 비어 있습니다 — v2 판정을 이 이름으로 백업해 두세요.")
    if not human_labels_by_id:
        raise RuntimeError(f"{HUMAN_LABELS_PATH} 이 비어 있습니다 — 사람 채점 결과가 필요합니다.")

    wb = Workbook()
    last_row = _build_평가표(wb, queries, responses_by_id, judgments_v3_by_id, judgments_v2_by_id, human_labels_by_id)
    _build_요약(wb, queries, judgments_v3_by_id, judgments_v2_by_id, judgments_v1_by_id, human_labels_by_id)
    _build_질의목록(wb, queries)

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX_PATH)
    print(f"저장: {XLSX_PATH}")
    print(f"평가표 데이터 행: 2..{last_row} ({last_row - 1}건), 시트: {wb.sheetnames}")


if __name__ == "__main__":
    main()
