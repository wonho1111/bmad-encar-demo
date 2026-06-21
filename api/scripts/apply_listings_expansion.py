# -*- coding: utf-8 -*-
"""seed-expansion.sql(매물 58건 INSERT)을 라이브 DB에 적용.
backfill 스크립트의 safe_conninfo(특수문자 비밀번호 처리)·연결 롤(postgres, 쓰기 가능)을 재사용한다.
embedding은 NULL로 들어가고, 이후 backfill_embeddings.py가 채운다.
"""
import sys, io
from pathlib import Path

API_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(API_ROOT))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import psycopg  # noqa: E402
from app.config import require, settings  # noqa: E402
from scripts.backfill_embeddings import safe_conninfo  # noqa: E402

SQL_FILE = API_ROOT.parent / "_bmad-output" / "implementation-artifacts" / "seed-expansion.sql"

def main() -> None:
    sql = SQL_FILE.read_text(encoding="utf-8")
    db_url = require("DATABASE_URL", settings.database_url)
    with psycopg.connect(safe_conninfo(db_url)) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)  # 파일에 begin;...commit; 포함
            cur.execute("select count(*) from public.listings")
            total = cur.fetchone()[0]
            cur.execute("select count(*) from public.listings where embedding is null")
            nulls = cur.fetchone()[0]
            cur.execute("select count(*) from public.listings where status='on_sale'")
            on_sale = cur.fetchone()[0]
    print(f"✅ 적용 완료. listings 총 {total}건 / on_sale {on_sale} / embedding NULL {nulls}")

if __name__ == "__main__":
    main()
