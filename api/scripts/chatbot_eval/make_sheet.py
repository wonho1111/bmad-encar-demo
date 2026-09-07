"""사람 채점용 엑셀 산출 — `$OUT/chatbot_alignment.xlsx`.

시트 3개:
  평가표  — 항목별 1행. Model Critique/Outcome은 judge.py 결과로 미리 채우고, Human Critique/
            Outcome은 사람이 채울 빈 칸으로 남긴다. Alignment는 두 판정 일치 여부를 셀 수식으로
            계산한다(파이썬이 미리 계산해 박아넣지 않는다 — 사람이 Human Outcome을 채우는 순간
            엑셀이 즉시 다시 계산해야 Agreement%가 실시간으로 의미 있다).
  요약    — 카테고리별 GOOD율, 위반 코드 집계, 실행 사실(날짜·에이전트/채점 모델·DB·건수).
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
from openpyxl.worksheet.datavalidation import DataValidation

OUT_DIR = Path(os.environ.get("OUT", "/home/whlee/workspace/bmad-encar-demo/.logs/chatbot_eval/20260908"))
QUERIES_PATH = Path(__file__).resolve().parent / "queries.json"
RESPONSES_PATH = OUT_DIR / "responses.jsonl"
JUDGMENTS_PATH = OUT_DIR / "judgments.jsonl"
JUDGE_META_PATH = OUT_DIR / "judge_meta.json"
# Fix 3 — v1(구 rubric, 카드 요약만 보고 채점) 판정 백업. 요약 시트에서 v1 vs v2 GOOD율을
# 나란히 보여주는 데 쓴다(카테고리별 집계에는 category 필드만 있으면 되므로 judgments만 필요
# — responses_v1.jsonl은 안 읽는다). 없어도(파일 부재) _load_jsonl이 빈 리스트를 돌려줘
# 죽지 않는다.
JUDGMENTS_V1_PATH = OUT_DIR / "judgments_v1.jsonl"
JUDGE_META_V1_PATH = OUT_DIR / "judge_meta_v1.json"
XLSX_PATH = OUT_DIR / "chatbot_alignment.xlsx"

HEADER_FILL = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
HEADER_FONT = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")
TOP = Alignment(vertical="top")

COLUMNS = [
    "ID", "범주", "Input(전 턴, 줄바꿈)", "Model Response(최종 답변)",
    "도구 결과 요약(매물 id·모델·가격 최대 5개)", "도구 원문(요약)", "Model Critique", "Model Outcome",
    "Human Critique", "Human Outcome", "Alignment", "판정 코드",
]
COL_WIDTHS = [6, 8, 38, 42, 34, 40, 42, 12, 34, 12, 10, 30]


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


def _input_text(turns: list[dict]) -> str:
    queries = [t["query"] for t in turns]
    if len(queries) == 1:
        return queries[0]
    return "\n".join(f"{i + 1}. {q}" for i, q in enumerate(queries))


def _tool_summary(turns: list[dict]) -> str:
    """매물 id·모델·가격(최대 5개) + 시세 판정 요약을 턴 순서대로 중복 제거해 압축한다."""
    parts: list[str] = []
    seen_ids: set[str] = set()
    for turn in turns:
        for listing in turn.get("listings") or []:
            if listing["id"] in seen_ids:
                continue
            seen_ids.add(listing["id"])
            parts.append(f"{listing['model']} {listing['year']} · {listing['price'] // 10000}만원 (id:{listing['id'][:8]})")
        md = turn.get("market_diagnosis")
        if md and md.get("verdict"):
            parts.append(f"[시세판정={md['verdict']}, tabpfn={md.get('tabpfn_price')}, comps={md.get('comps_n')}건]")
        if len(parts) >= 5:
            break
    return "; ".join(parts[:5])


def _tool_raw_summary(turns: list[dict]) -> str:
    """Fix 3 — 모든 턴의 tool_calls output_text(judge v2가 실제로 본 원문)를 이어붙여 앞
    400자만 남긴다. 사람이 "판정 코드가 맞는지" 확인할 때 매물 카드 요약이 아니라 도구가
    실제로 뭐라고 답했는지 원문으로 대조할 수 있게 하는 열이다."""
    parts = [
        tc.get("output_text") or ""
        for turn in turns
        for tc in (turn.get("tool_calls") or [])
    ]
    return " | ".join(p for p in parts if p)[:400]


def _build_평가표(wb: Workbook, queries: list[dict], responses_by_id: dict, judgments_by_id: dict) -> int:
    ws = wb.active
    ws.title = "평가표"

    n = len(queries)
    last_row = n + 1  # 헤더가 1행이므로 데이터는 2..last_row

    # 상단 요약 셀(오른쪽) — Agreement%: Human Outcome이 채워질수록 실시간으로 갱신된다.
    # 열 순서(Fix 3로 "도구 원문(요약)" 열 추가돼 한 칸씩 밀림): Alignment는 K열.
    ws["M1"] = "Agreement%"
    ws["M1"].font = HEADER_FONT
    ws["N1"] = f'=IFERROR(AVERAGE(K2:K{last_row}),"")'
    ws["N1"].number_format = "0%"

    for col_idx, title in enumerate(COLUMNS, start=1):
        cell = ws.cell(row=1, column=col_idx, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
    for col_idx, width in enumerate(COL_WIDTHS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = width

    for i, item in enumerate(queries):
        row = i + 2
        resp = responses_by_id.get(item["id"])
        judg = judgments_by_id.get(item["id"])

        turns = resp["turns"] if resp else []
        values = [
            item["id"],
            item["category"],
            _input_text(item["turns"]),
            (resp or {}).get("final_answer") or "",
            _tool_summary(turns),
            _tool_raw_summary(turns),  # Fix 3 — 도구 원문(요약)
            (judg or {}).get("critique", ""),
            (judg or {}).get("outcome", ""),
            "",  # Human Critique — 사람이 채움
            "",  # Human Outcome — 사람이 채움
            None,  # Alignment — 수식으로 채움(아래)
            ", ".join((judg or {}).get("issues") or []),
        ]
        for col_idx, value in enumerate(values, start=1):
            cell = ws.cell(row=row, column=col_idx, value=value)
            if col_idx in (3, 4, 5, 6, 7, 9):
                cell.alignment = WRAP
            else:
                cell.alignment = TOP
        # 열 순서: 5=도구결과요약, 6=도구원문요약(Fix 3 신규), 7=Model Critique, 8=Model
        # Outcome, 9=Human Critique, 10=Human Outcome, 11=Alignment, 12=판정 코드.
        ws.cell(row=row, column=11, value=f'=IF(OR(I{row}="",J{row}=""),"",IF(H{row}=J{row},1,0))')

    dv = DataValidation(type="list", formula1='"GOOD,BAD"', allow_blank=True, showDropDown=False)
    ws.add_data_validation(dv)
    dv.add(f"J2:J{last_row}")

    ws.freeze_panes = "A2"
    return last_row


def _build_요약(
    wb: Workbook, queries: list[dict], judgments_by_id: dict, judgments_v1_by_id: dict
) -> None:
    """Fix 3 — v1(카드 요약만 보고 채점)과 v2(도구 원문 근거 rubric)의 GOOD율을 나란히
    보여준다. v1 데이터(judgments_v1.jsonl)가 없으면 그 칸은 0/공백으로만 채워지고 죽지
    않는다(예: 이 스크립트를 v1 백업 없이 새로 돌리는 경우)."""
    ws = wb.create_sheet("요약")
    meta = json.loads(JUDGE_META_PATH.read_text(encoding="utf-8")) if JUDGE_META_PATH.exists() else {}
    meta_v1 = json.loads(JUDGE_META_V1_PATH.read_text(encoding="utf-8")) if JUDGE_META_V1_PATH.exists() else {}

    r = 1
    ws.cell(row=r, column=1, value="실행 사실").font = HEADER_FONT
    r += 1
    facts = [
        ("날짜", "2026-09-08"),
        ("에이전트 모델", meta.get("agent_model", "확인불가")),
        ("채점 모델(v2, 현재 판정)", f"{meta.get('judge_model', '확인불가')} "
         f"(judge_version={meta.get('judge_version', '?')})"),
        ("채점 모델(v1, 참고용 백업)", f"{meta_v1.get('judge_model', '확인불가')} "
         f"(judge_version={meta_v1.get('judge_version', 1)})"),
        ("DB", "로컬 Supabase(127.0.0.1:55322, 시드 매물 166건)"),
        ("입력 건수(n)", len(queries)),
    ]
    for label, value in facts:
        ws.cell(row=r, column=1, value=label)
        ws.cell(row=r, column=2, value=value)
        r += 1

    def _cat_counts(judg_by_id: dict) -> dict[str, Counter]:
        counts: dict[str, Counter] = {}
        for item in queries:
            judg = judg_by_id.get(item["id"])
            outcome = (judg or {}).get("outcome")
            counts.setdefault(item["category"], Counter())[outcome or "미채점"] += 1
        return counts

    v1_counts = _cat_counts(judgments_v1_by_id)
    v2_counts = _cat_counts(judgments_by_id)

    r += 1
    ws.cell(row=r, column=1, value="카테고리별 GOOD율 — v1(구 rubric) vs v2(도구 원문 근거)").font = HEADER_FONT
    r += 1
    headers = ["범주", "v1 GOOD", "v1 BAD", "v1 GOOD율", "v2 GOOD", "v2 BAD", "v2 GOOD율"]
    for c, h in enumerate(headers, start=1):
        ws.cell(row=r, column=c, value=h).font = HEADER_FONT
    r += 1
    all_cats = sorted(set(v1_counts) | set(v2_counts))
    for cat in all_cats:
        g1, b1 = v1_counts.get(cat, Counter()).get("GOOD", 0), v1_counts.get(cat, Counter()).get("BAD", 0)
        g2, b2 = v2_counts.get(cat, Counter()).get("GOOD", 0), v2_counts.get(cat, Counter()).get("BAD", 0)
        ws.cell(row=r, column=1, value=cat)
        ws.cell(row=r, column=2, value=g1)
        ws.cell(row=r, column=3, value=b1)
        ws.cell(row=r, column=4, value=(g1 / (g1 + b1) if (g1 + b1) else None)).number_format = "0%"
        ws.cell(row=r, column=5, value=g2)
        ws.cell(row=r, column=6, value=b2)
        ws.cell(row=r, column=7, value=(g2 / (g2 + b2) if (g2 + b2) else None)).number_format = "0%"
        r += 1

    r += 1
    ws.cell(row=r, column=1, value="위반 코드 집계 — v1 vs v2").font = HEADER_FONT
    r += 1
    issue_v1: Counter = Counter()
    for judg in judgments_v1_by_id.values():
        issue_v1.update(judg.get("issues") or [])
    issue_v2: Counter = Counter()
    for judg in judgments_by_id.values():
        issue_v2.update(judg.get("issues") or [])
    ws.cell(row=r, column=1, value="코드")
    ws.cell(row=r, column=2, value="v1 건수")
    ws.cell(row=r, column=3, value="v2 건수")
    for c in range(1, 4):
        ws.cell(row=r, column=c).font = HEADER_FONT
    r += 1
    all_codes = sorted(set(issue_v1) | set(issue_v2), key=lambda code: -(issue_v1[code] + issue_v2[code]))
    for code in all_codes:
        ws.cell(row=r, column=1, value=code)
        ws.cell(row=r, column=2, value=issue_v1.get(code, 0))
        ws.cell(row=r, column=3, value=issue_v2.get(code, 0))
        r += 1

    for col, width in zip("ABCDEFG", (22, 14, 10, 10, 10, 10, 10)):
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
    judgments_by_id = {j["id"]: j for j in _load_jsonl(JUDGMENTS_PATH)}
    judgments_v1_by_id = {j["id"]: j for j in _load_jsonl(JUDGMENTS_V1_PATH)}  # Fix 3, 없으면 빈 dict

    if not responses_by_id:
        raise RuntimeError(f"{RESPONSES_PATH} 이 비어 있습니다 — run_batch.py를 먼저 실행하세요.")
    if not judgments_by_id:
        raise RuntimeError(f"{JUDGMENTS_PATH} 이 비어 있습니다 — judge.py를 먼저 실행하세요.")

    wb = Workbook()
    last_row = _build_평가표(wb, queries, responses_by_id, judgments_by_id)
    _build_요약(wb, queries, judgments_by_id, judgments_v1_by_id)
    _build_질의목록(wb, queries)

    XLSX_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(XLSX_PATH)
    print(f"저장: {XLSX_PATH}")
    print(f"평가표 데이터 행: 2..{last_row} ({last_row - 1}건), 시트: {wb.sheetnames}")


if __name__ == "__main__":
    main()
