"""신뢰속성(accident_status·is_single_owner·is_non_smoker)을 판매중 매물에 배분한다.

사용자 지정 비율(판매중 전체 기준):
  3개 다 보유  약 15건   (드물게)
  2개 보유     약 40건   (가장 흔하게)
  1개 보유     약 25건
  없음         나머지 절반

결정론: id 오름차순으로 줄을 세우고 위치로 배정한다. 같은 DB에 다시 돌리면 같은 결과가 나오고,
DB가 달라도(운영/로컬) 같은 규칙이 적용된다. 난수를 쓰지 않는 이유 — 운영과 로컬에서 다른
결과가 나오면 나중에 "왜 다르지"를 추적할 수 없다.

정합성 규칙:
  · accident_status='무사고'는 accident_free=true인 매물에만 준다(초록 뱃지).
  · accident_free=false인 매물이 accident_status를 받으면 '사고' 또는 '단순교환'(중립 칩).
    → 이건 뱃지가 아니라 상태칩이라 "신뢰속성 보유 3종"에서 초록 1개로 세지 않는다.

멱등: 매번 전체를 다시 계산해 덮어쓴다(부분 실행 후 재실행해도 같은 최종 상태).
"""

import os
import sys

import psycopg

DB = os.environ.get("TRUST_DB_URL")
if not DB:
    print("TRUST_DB_URL 환경변수가 필요합니다.", file=sys.stderr)
    raise SystemExit(2)

APPLY = "--apply" in sys.argv

N_ALL3, N_TWO, N_ONE = 15, 40, 25

with psycopg.connect(DB) as conn:
    with conn.cursor() as cur:
        cur.execute(
            "select id, accident_free from public.listings "
            "where status='on_sale' order by id"
        )
        rows = cur.fetchall()

total = len(rows)
print(f"판매중 매물 {total}건")

# 초록 뱃지를 줄 수 있는 후보(무사고)와 그렇지 않은 것을 나눈다.
clean = [r for r in rows if r[1]]
dirty = [r for r in rows if not r[1]]
print(f"  accident_free=true {len(clean)} / false {len(dirty)}")

plan = {}  # id -> (accident_status, single_owner, non_smoker)

# 1) 3개 전부 — 무사고 후보 중 앞에서부터
i = 0
for lid, _ in clean[i : i + N_ALL3]:
    plan[lid] = ("무사고", True, True)
i += N_ALL3

# 2) 2개 — 무사고+1인소유 / 무사고+비흡연 / 1인소유+비흡연 을 번갈아
combos2 = [("무사고", True, None), ("무사고", None, True), (None, True, True)]
for n, (lid, _) in enumerate(clean[i : i + N_TWO]):
    plan[lid] = combos2[n % 3]
i += N_TWO

# 3) 1개 — 무사고만 / 1인소유만 / 비흡연만
combos1 = [("무사고", None, None), (None, True, None), (None, None, True)]
for n, (lid, _) in enumerate(clean[i : i + N_ONE]):
    plan[lid] = combos1[n % 3]
i += N_ONE

# 4) 사고 이력이 있는 매물 일부에 상태칩(중립)을 준다 — 초록 뱃지가 아니라 '사고'/'단순교환'.
#    전체가 무사고뿐이면 카드에서 중립 상태칩을 볼 일이 없어 UI 검증이 불가능해진다.
for n, (lid, _) in enumerate(dirty[: max(1, len(dirty) // 2)]):
    plan[lid] = ("사고" if n % 2 else "단순교환", None, None)

print(f"\n배정: 3개 {N_ALL3} · 2개 {N_TWO} · 1개 {N_ONE} · 상태칩 {len([1 for v in plan.values() if v[0] in ('사고','단순교환')])}")
print(f"신뢰속성 보유 합계 {len(plan)} / 판매중 {total} = {len(plan)*100//total}%")

if not APPLY:
    print("\n(미적용 — 실제로 반영하려면 --apply)")
    raise SystemExit(0)

with psycopg.connect(DB) as conn:
    with conn.cursor() as cur:
        # 멱등: 판매중 전체를 먼저 비우고 계획대로 다시 채운다.
        cur.execute(
            "update public.listings set accident_status=null, is_single_owner=null, "
            "is_non_smoker=null where status='on_sale'"
        )
        for lid, (st, so, ns) in plan.items():
            cur.execute(
                "update public.listings set accident_status=%s, is_single_owner=%s, "
                "is_non_smoker=%s where id=%s",
                (st, so, ns, lid),
            )
    conn.commit()

with psycopg.connect(DB) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select
              count(*) filter (where accident_status='무사고' and is_single_owner and is_non_smoker) as all3,
              count(*) filter (where accident_status is not null or is_single_owner or is_non_smoker) as any_attr,
              count(*) filter (where accident_status='무사고') as clean_badge,
              count(*) filter (where accident_status in ('사고','단순교환')) as chip,
              count(*) filter (where is_single_owner) as single,
              count(*) filter (where is_non_smoker) as nonsmoke,
              count(*) as total
            from public.listings where status='on_sale'
        """)
        a3, anyv, cb, chip, so, ns, tot = cur.fetchone()
print(f"\n✅ 적용 완료 (판매중 {tot}건)")
print(f"  3개 전부      {a3}")
print(f"  하나라도 보유  {anyv}  ({anyv*100//tot}%)")
print(f"  무사고 뱃지    {cb} · 상태칩(사고/단순교환) {chip}")
print(f"  1인소유 {so} · 비흡연 {ns}")
