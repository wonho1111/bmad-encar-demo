"""사진 없는 매물에 기존 사진을 **복사**해 붙인다.

왜 복사인가(참조가 아니라):
  0013_listing_images_path_integrity.sql이 storage_path를 `{소유자}/{매물}/{파일명}`으로 강제하고,
  소유자를 클라 입력이 아니라 listings에서 직접 구해 검사한다. 다른 매물의 경로를 그대로 재사용하면
  트리거가 거부한다 — 그 제약은 실제 권한상승(남의 sold 매물 사진 공개)을 막으려고 넣은 것이라
  우회하지 않는다.

차형(body_type)이 같은 매물의 사진을 골라 붙인다 — 세단에 SUV 사진이 붙지 않게.
사진이 겹치는 것은 사용자가 허용했다("사진은 매물이 다른데 겹치는 경우가 좀 있더라고 이정도는 감안").

멱등: 이미 사진이 있는 매물은 건너뛴다. 재실행하면 남은 것만 처리한다.

⚠️ 0바이트 함정(scripts/seed-local.sh가 실측으로 기록해둔 것): 다운로드가 끊기면 200인데 0바이트가
   올 수 있다. 존재가 아니라 **크기**로 판단하지 않으면 0바이트를 업로드하고 성공으로 센다.
"""

import os
import random
import sys
import urllib.request
import uuid

import psycopg
from psycopg.types.json import Json

# 대상 경로의 UUID를 (매물, 순번)에서 결정론적으로 만든다(uuid4가 아니라 uuid5).
# 이유: 실패 후 재실행하면 uuid4는 매번 새 경로를 만들어, 앞 실행이 스토리지에 올려둔 파일이
# DB 행 없이 고아로 쌓인다(실측 — 1차 실행이 credit 어댑터 오류로 138장 전부 DB 삽입에 실패했는데
# 파일은 이미 올라가 있었다). uuid5면 같은 입력이 같은 경로를 내므로 x-upsert가 덮어써서 고아가 없다.
_NS = uuid.UUID("6f1c3a5e-9b2d-4c7a-8e15-2f0d7b4a9c31")

DB = os.environ["PHOTO_DB_URL"]
PUBLIC_BASE = os.environ["PHOTO_PUBLIC_BASE"]      # 다운로드 원본(공개 버킷)
UPLOAD_BASE = os.environ["PHOTO_UPLOAD_BASE"]      # 업로드 대상 storage API
UPLOAD_KEY = os.environ["PHOTO_UPLOAD_KEY"]        # 업로드 인증(로컬 secret 또는 사용자 JWT)
APPLY = "--apply" in sys.argv

rng = random.Random(20260805)  # 결정론 — 재실행·다른 환경에서도 같은 선택


def fetch(path: str) -> bytes:
    url = f"{PUBLIC_BASE}/storage/v1/object/public/listing-images/{path}"
    with urllib.request.urlopen(url, timeout=60) as r:
        if r.status != 200:
            raise RuntimeError(f"다운로드 실패 {r.status}: {path}")
        data = r.read()
    if not data:
        raise RuntimeError(f"0바이트 다운로드: {path}")
    return data


def upload(path: str, blob: bytes) -> None:
    url = f"{UPLOAD_BASE}/storage/v1/object/listing-images/{path}"
    req = urllib.request.Request(url, data=blob, method="POST")
    req.add_header("apikey", UPLOAD_KEY)
    req.add_header("Authorization", f"Bearer {UPLOAD_KEY}")
    req.add_header("Content-Type", "image/webp")
    req.add_header("x-upsert", "true")
    with urllib.request.urlopen(req, timeout=120) as r:
        if r.status not in (200, 201):
            raise RuntimeError(f"업로드 실패 {r.status}: {path}")


with psycopg.connect(DB) as conn, conn.cursor() as cur:
    cur.execute("""
        select l.id, l.seller_id, l.body_type
        from public.listings l
        where l.status='on_sale'
          and not exists (select 1 from public.listing_images i where i.listing_id=l.id)
        order by l.id
    """)
    targets = cur.fetchall()

    cur.execute("""
        select l.body_type, i.storage_path, i.credit
        from public.listing_images i join public.listings l on l.id=i.listing_id
        order by i.storage_path
    """)
    by_type: dict[str, list] = {}
    every = []
    for bt, path, credit in cur.fetchall():
        by_type.setdefault(bt, []).append((path, credit))
        every.append((path, credit))

print(f"사진 없는 판매중 매물 {len(targets)}건 · 원본 사진 풀 {len(every)}장")
if not targets:
    raise SystemExit(0)

plan = []
for lid, seller, bt in targets:
    pool = by_type.get(bt) or every
    n = rng.choice([1, 2, 2, 3])          # 기존 분포(매물당 평균 약 1.8장)와 비슷하게
    picks = rng.sample(pool, min(n, len(pool)))
    for order, (src_path, credit) in enumerate(picks):
        dst = f"{seller}/{lid}/{uuid.uuid5(_NS, f'{lid}:{order}')}.webp"
        plan.append((lid, src_path, dst, order, order == 0, credit))

print(f"복사 계획 {len(plan)}장 (매물당 평균 {len(plan)/len(targets):.1f}장)")
if not APPLY:
    for row in plan[:3]:
        print("  예:", row[1][:50], "->", row[2][:50])
    print("(미적용 — 실제로 반영하려면 --apply)")
    raise SystemExit(0)

ok = fail = 0
errors = []
with psycopg.connect(DB) as conn:
    for lid, src, dst, order, is_cover, credit in plan:
        try:
            blob = fetch(src)
            upload(dst, blob)
            with conn.cursor() as cur:
                cur.execute(
                    "insert into public.listing_images "
                    "(listing_id, storage_path, sort_order, is_cover, credit) "
                    "values (%s,%s,%s,%s,%s)",
                    (lid, dst, order, is_cover, Json(credit) if credit is not None else None),
                )
            conn.commit()
            ok += 1
        except Exception as e:  # noqa: BLE001
            conn.rollback()
            fail += 1
            errors.append(f"{dst[:60]}: {e}")

print(f"\n완료 — 성공 {ok} · 실패 {fail}")
for e in errors[:5]:
    print("  ✗", e)

with psycopg.connect(DB) as conn, conn.cursor() as cur:
    cur.execute("""
        select count(*) from public.listings l where l.status='on_sale'
          and not exists (select 1 from public.listing_images i where i.listing_id=l.id)
    """)
    print("남은 사진 없는 판매중 매물:", cur.fetchone()[0])
