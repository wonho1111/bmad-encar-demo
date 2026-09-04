"""엔카 실매물 오프라인 평가용 별도 DB(encar_eval) 구성 (report.md §1 배경 — 시드 데이터가 아닌
실매물로 시세 진단 엔진의 정확도를 재려면, 제품 스키마를 그대로 쓰되 운영/시연 DB와는 완전히
분리된 로컬 DB가 필요하다).

로컬 Supabase Postgres 컨테이너(supabase_db_bmad-encar-demo) 안에 `encar_eval`이라는 별도
데이터베이스를 만들고(= `postgres` DB의 테이블은 절대 건드리지 않는다), CI(api-db 잡)와 동일한
순서로 마이그레이션을 적용한 뒤 listings_eval.csv(7,081행)를 적재한다.

사용법(순서):
  1. python scripts/build_eval_db.py                              # DB 재생성 + 마이그레이션 + 판매자 + 적재 + 분할(20/타겟) + holdout off
  2. python scripts/build_eval_db.py --holdout on --keep           # (재생성 없이) status만 토글 — 평가 실행 직전
  3. python scripts/build_eval_db.py --holdout off --keep          # 원복

`--keep`이 있으면 1~6단계(재생성·마이그레이션·판매자·적재·분할)를 전부 건너뛰고 holdout 토글만 한다
— 이미 적재된 데이터를 지우지 않고 status만 바꾸는 용도.
"""

import argparse
import collections
import csv
import json
import pathlib
import random
import subprocess
import sys
import uuid
from urllib.parse import urlsplit, urlunsplit

import psycopg

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
PRELUDE_SQL = REPO_ROOT / "scripts" / "migration-check-prelude.sql"
MIGRATIONS_DIR = REPO_ROOT / "supabase" / "migrations"

DEFAULT_OUT_DIR = pathlib.Path("/home/whlee/workspace/bmad-encar-demo/.logs/encar_eval/20260905")
DEFAULT_CSV = DEFAULT_OUT_DIR / "listings_eval.csv"
DEFAULT_TEST_IDS = DEFAULT_OUT_DIR / "eval" / "test_ids.json"

# 고정 평가용 판매자 — conftest.py `_create_user`와 동일한 방식(auth.users insert → 가입 트리거
# → profiles.role을 seller로 UPDATE)으로 만든다. 이메일 로컬파트가 profiles.name·
# listings.seller_name(둘 다 트리거 자동기록, 0007/0009)이 되므로 "encar-eval"이 되도록 고른다.
SELLER_ID = uuid.UUID("00000000-0000-4000-8000-00000000e0a1")
SELLER_EMAIL = "encar-eval@eval.local"

LISTING_COLS = [
    "id", "seller_id", "status", "manufacturer", "model", "body_type", "year", "price",
    "mileage", "color", "fuel", "transmission", "displacement", "seats", "region",
    "accident_free", "options", "description", "accident_status", "is_single_owner",
    "is_non_smoker",
]
LISTING_INSERT_SQL = (
    f"INSERT INTO public.listings ({', '.join(LISTING_COLS)}) "
    f"VALUES ({', '.join(['%s'] * len(LISTING_COLS))})"
)
META_INSERT_SQL = (
    "INSERT INTO public.eval_meta (listing_id, encar_id, target_slug, seed_group, split) "
    "VALUES (%s, %s, %s, %s, 'train')"
)


def with_dbname(dsn: str, dbname: str) -> str:
    parts = urlsplit(dsn)
    return urlunsplit((parts.scheme, parts.netloc, "/" + dbname, parts.query, parts.fragment))


# ── 2) 마이그레이션 적용 — CI(tests.yml api-db 잡)와 동일 재료·순서 ────────────
def run_psql_file(container: str, dbname: str, path: pathlib.Path) -> None:
    proc = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", dbname,
         "-v", "ON_ERROR_STOP=1", "-q", "-f", "-"],
        input=path.read_bytes(), capture_output=True,
    )
    if proc.returncode != 0:
        sys.stdout.write(proc.stdout.decode("utf-8", "replace"))
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        raise SystemExit(f"마이그레이션 적용 실패: {path} (exit {proc.returncode})")
    print(f"  OK: {path.name}")


def apply_migrations(container: str, dbname: str) -> list[str]:
    applied = []
    run_psql_file(container, dbname, PRELUDE_SQL)
    applied.append(PRELUDE_SQL.name)
    for f in sorted(MIGRATIONS_DIR.glob("*.sql")):
        run_psql_file(container, dbname, f)
        applied.append(f.name)
    return applied


# ── 3) 판매자 1명 ──────────────────────────────────────────────────────────
def ensure_seller(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM public.profiles WHERE id = %s", (SELLER_ID,))
        if cur.fetchone() is None:
            cur.execute(
                "INSERT INTO auth.users (id, email, raw_user_meta_data) "
                "VALUES (%s, %s, jsonb_build_object('role', %s::text))",
                (SELLER_ID, SELLER_EMAIL, "seller"),
            )
            cur.execute("UPDATE public.profiles SET role = 'seller' WHERE id = %s", (SELLER_ID,))
        cur.execute("SELECT role, name FROM public.profiles WHERE id = %s", (SELLER_ID,))
        role, name = cur.fetchone()
    conn.commit()
    print(f"판매자 준비 완료: id={SELLER_ID} role={role} name={name}")


# ── 4) eval_meta 테이블 ─────────────────────────────────────────────────────
def ensure_eval_meta(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "CREATE TABLE IF NOT EXISTS public.eval_meta ("
            "  listing_id uuid PRIMARY KEY REFERENCES public.listings(id),"
            "  encar_id text UNIQUE,"
            "  target_slug text,"
            "  seed_group text,"
            "  split text"
            ")"
        )
    conn.commit()


# ── 5) CSV 적재 ─────────────────────────────────────────────────────────────
def _blank_to_none(v: str):
    return v if v != "" else None


def _bool_or_none(v: str):
    return None if v == "" else v == "True"


def load_csv(conn, csv_path: pathlib.Path) -> dict:
    listing_rows = []
    meta_rows = []
    per_target = collections.Counter()
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            lid = uuid.uuid4()
            options = json.loads(row["options"]) if row["options"] else []
            listing_rows.append((
                lid, SELLER_ID, "on_sale", row["manufacturer"], row["model"], row["body_type"],
                int(row["year"]), int(row["price"]), int(row["mileage"]), row["color"],
                row["fuel"], row["transmission"], int(row["displacement"]), int(row["seats"]),
                row["region"], row["accident_free"] == "True", options,
                _blank_to_none(row["description"]), _blank_to_none(row["accident_status"]),
                _bool_or_none(row["is_single_owner"]), _bool_or_none(row["is_non_smoker"]),
            ))
            meta_rows.append((lid, row["encar_id"], row["target_slug"], row["seed_group"]))
            per_target[row["target_slug"]] += 1

    try:
        with conn.cursor() as cur:
            cur.executemany(LISTING_INSERT_SQL, listing_rows)
            cur.executemany(META_INSERT_SQL, meta_rows)
    except Exception as exc:
        conn.rollback()
        raise SystemExit(f"CSV 적재 실패(롤백함, CHECK 위반 등): {exc}")
    conn.commit()
    return {"total": len(listing_rows), "per_target": per_target}


def verify_listing_count(conn, expected: int) -> None:
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM public.listings")
        (n,) = cur.fetchone()
    if n != expected:
        raise SystemExit(f"검증 실패: listings count={n} (기대 {expected})")
    print(f"검증: listings count={n} (기대와 일치), CHECK 위반 0건(트랜잭션 커밋 성공으로 확인)")


# ── 6) 타겟당 N건 무작위 테스트 분할 ─────────────────────────────────────────
def split_test_set(conn, n_per_target: int, seed: int, out_path: pathlib.Path):
    rng = random.Random(seed)
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT target_slug FROM public.eval_meta ORDER BY target_slug")
        slugs = [r[0] for r in cur.fetchall()]

        selected = []  # (listing_id, encar_id, target_slug)
        per_target_counts = {}
        for slug in slugs:
            cur.execute(
                "SELECT listing_id, encar_id FROM public.eval_meta "
                "WHERE target_slug = %s ORDER BY encar_id",
                (slug,),
            )
            group = cur.fetchall()
            k = min(n_per_target, len(group))
            picked = rng.sample(group, k)
            per_target_counts[slug] = k
            selected.extend((lid, encar_id, slug) for lid, encar_id in picked)

        ids = [s[0] for s in selected]
        cur.execute(
            "UPDATE public.eval_meta SET split = 'test' WHERE listing_id = ANY(%s::uuid[])",
            (ids,),
        )
    conn.commit()

    records = [
        {"listing_id": str(lid), "encar_id": encar_id, "target_slug": slug}
        for lid, encar_id, slug in selected
    ]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    return per_target_counts, len(selected)


# ── 7) holdout 토글 ─────────────────────────────────────────────────────────
def set_holdout(conn, on: bool) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE public.listings AS l "
            "SET status = CASE WHEN %s AND em.split = 'test' THEN 'sold' ELSE 'on_sale' END "
            "FROM public.eval_meta AS em "
            "WHERE em.listing_id = l.id",
            (on,),
        )
        cur.execute("SELECT status, count(*) FROM public.listings GROUP BY status")
        counts = dict(cur.fetchall())
    conn.commit()
    return counts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db-url", default="postgresql://postgres:postgres@127.0.0.1:55322/postgres",
                     help="슈퍼유저 DSN (postgres 유지보수 DB를 가리켜야 함)")
    ap.add_argument("--container", default="supabase_db_bmad-encar-demo")
    ap.add_argument("--csv", default=str(DEFAULT_CSV))
    ap.add_argument("--out", default=str(DEFAULT_TEST_IDS), help="test_ids.json 경로")
    ap.add_argument("--keep", action="store_true", help="재생성·마이그레이션·적재를 건너뛰고 holdout 토글만")
    ap.add_argument("--split-per-target", type=int, default=20)
    ap.add_argument("--seed", type=int, default=20260905)
    ap.add_argument("--holdout", choices=["on", "off"], default="off")
    args = ap.parse_args()

    eval_dsn = with_dbname(args.db_url, "encar_eval")

    if args.keep:
        with psycopg.connect(eval_dsn) as conn:
            counts = set_holdout(conn, args.holdout == "on")
        print(f"holdout={args.holdout} (--keep, status 토글만) → 상태별 카운트: {counts}")
        return

    # 1) DROP/CREATE DATABASE — postgres DB의 테이블은 건드리지 않는다.
    with psycopg.connect(args.db_url, autocommit=True) as conn:
        conn.execute("DROP DATABASE IF EXISTS encar_eval")
        conn.execute("CREATE DATABASE encar_eval")
    print("encar_eval 데이터베이스 재생성 완료")

    # 2) 마이그레이션
    print("마이그레이션 적용 중 (프렐류드 → 번호순)...")
    applied = apply_migrations(args.container, "encar_eval")
    print(f"마이그레이션 적용 완료: {len(applied)}개 파일")

    with psycopg.connect(eval_dsn) as conn:
        ensure_seller(conn)
        ensure_eval_meta(conn)

        stats = load_csv(conn, pathlib.Path(args.csv))
        print(f"listings 적재: {stats['total']}건")
        for slug, cnt in sorted(stats["per_target"].items()):
            print(f"  {slug}: {cnt}")
        verify_listing_count(conn, stats["total"])

        per_target_test, total_test = split_test_set(
            conn, args.split_per_target, args.seed, pathlib.Path(args.out)
        )
        print(f"테스트 분할(seed={args.seed}, target당 최대 {args.split_per_target}건): 총 {total_test}건")
        for slug, cnt in sorted(per_target_test.items()):
            print(f"  {slug}: {cnt}")

        counts = set_holdout(conn, args.holdout == "on")
        print(f"holdout={args.holdout} → 상태별 카운트: {counts}")


if __name__ == "__main__":
    main()
