"""13-10이 데이터를 바꿨으므로 큐리셋 62문항의 `count_range`를 전부 다시 계산한다.

왜 전부인가: 정답 집합은 predicate를 DB에 돌려 만든다. 매물이 93 → 158건이 됐으니 예전 값은
새로 넣은 15문항뿐 아니라 **기존 47문항도 전부** 무효다. 안 고치면 13-11의 재캡처가 옛 기준과
비교하게 된다.

허용폭 보존: 원래 [n,n](정확)이면 [새n,새n], 원래 [a,b](여유 있음)면 같은 폭을 새 값 주위로
옮긴다 — 큐리셋을 만든 사람이 문항별로 정한 엄격도를 내가 임의로 바꾸지 않는다.
"""

import json
import pathlib
import sys

sys.path.insert(0, "api")
sys.path.insert(0, "api/scripts")

import psycopg  # noqa: E402
from score_ab import build_golden_sql  # noqa: E402

QS = pathlib.Path("api/docs/ai-ab-test-queryset.json")
DB = "postgresql://postgres:postgres@127.0.0.1:55322/postgres"
APPLY = "--apply" in sys.argv

data = json.loads(QS.read_text(encoding="utf-8"))
conn = psycopg.connect(DB)


def count_for(pred):
    sql, params = build_golden_sql(pred)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return len(cur.fetchall())


changes = []


def visit(node, label):
    pred = node.get("predicate")
    old = node.get("count_range")
    if not pred or not old:
        return
    n = count_for(pred)
    lo, hi = old
    if lo == hi:
        new = [n, n]
    else:  # 원래 허용폭을 유지한 채 중심만 이동
        half_lo, half_hi = lo - (lo + hi) // 2, hi - (lo + hi) // 2
        new = [max(0, n + half_lo), n + half_hi]
    if new != old:
        changes.append((label, old, new))
    node["count_range"] = new


for item in data["items"]:
    if item.get("kind") == "multiturn":
        for i, turn in enumerate(item.get("turns", [])):
            visit(turn, f"{item['id']}.t{i+1}")
    else:
        visit(item, item["id"])

print(f"변경 {len(changes)}건 / 전체 문항")
for label, old, new in changes[:80]:
    print(f"  {label:>8}  {old} → {new}")

if not APPLY:
    print("\n(미적용 — 실제 반영은 --apply)")
    raise SystemExit(0)

QS.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n✅ 반영 완료")
