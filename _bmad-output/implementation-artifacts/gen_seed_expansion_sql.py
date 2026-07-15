# -*- coding: utf-8 -*-
"""seed-expansion JSON → 검증 + SQL 생성.
- 모든 enum 필드를 listings CHECK 허용값과 대조(불일치 시 즉시 에러 목록 출력).
- 전기차 displacement=0 등 정합성 점검.
- 통과하면 seed-expansion.sql 생성: 매물 58건(신규 판매자 2명에 30/28 분배, embedding NULL)
  + 가이드 new 6건 INSERT + replace 2건 UPDATE(embedding NULL로 재임베딩 유도).
"""
import json, sys, io
from pathlib import Path

HERE = Path(__file__).parent
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SELLER2 = "0f937a74-48ee-4e3a-9e78-4a3d85645727"  # seller-seed2@test.com
SELLER3 = "c19a85e7-6e23-432f-aa1c-efc57f1782af"  # seller-seed3@test.com

MANUF = {"현대","기아","제네시스","쉐보레","르노코리아","KG모빌리티","BMW","벤츠","아우디","폭스바겐","토요타","혼다","렉서스","테슬라","기타"}
BODY  = {"경차","소형차","준중형차","중형차","대형차","스포츠카","SUV","RV","경승합차","승합차","화물차","기타"}
COLOR = {"흰색","검정","회색","은색","파랑","빨강","갈색","녹색","기타"}
FUEL  = {"가솔린","디젤","하이브리드","전기","LPG"}
TRANS = {"자동","수동"}
REGION= {"서울","부산","대구","인천","광주","대전","울산","세종","경기","강원","충북","충남","전북","전남","경북","경남","제주"}
STATUS= {"on_sale","sold"}

def q(s: str) -> str:
    return "'" + str(s).replace("'", "''") + "'"

def arr(xs) -> str:
    if not xs:
        return "'{}'"
    return "array[" + ",".join(q(x) for x in xs) + "]"

listings = json.load(open(HERE/"seed-expansion-listings.json", encoding="utf-8"))
guides   = json.load(open(HERE/"seed-expansion-guides.json", encoding="utf-8"))

errors = []
for i, r in enumerate(listings):
    def chk(field, allowed):
        if r.get(field) not in allowed:
            errors.append(f"[{i}] {field}={r.get(field)!r} 허용값 아님")
    chk("manufacturer", MANUF); chk("body_type", BODY); chk("color", COLOR)
    chk("fuel", FUEL); chk("transmission", TRANS); chk("region", REGION); chk("status", STATUS)
    if not (2014 <= r.get("year",0) <= 2024): errors.append(f"[{i}] year 범위밖 {r.get('year')}")
    if not (0 <= r.get("price",-1)): errors.append(f"[{i}] price 음수")
    if not (0 <= r.get("mileage",-1)): errors.append(f"[{i}] mileage 음수")
    if not (2 <= r.get("seats",0) <= 11): errors.append(f"[{i}] seats 범위밖 {r.get('seats')}")
    if r.get("fuel")=="전기" and r.get("displacement",-1)!=0:
        errors.append(f"[{i}] 전기차인데 displacement={r.get('displacement')} (0이어야 함)")
    if not (0 <= r.get("displacement",-1)): errors.append(f"[{i}] displacement 음수")

if len(listings) != 58:
    errors.append(f"매물 수 {len(listings)} != 58")
if [g["mode"] for g in guides].count("replace") != 2:
    errors.append("replace 가이드가 2개가 아님")

if errors:
    print("❌ 검증 실패:")
    for e in errors: print("  -", e)
    sys.exit(1)

# ── SQL 생성 ──────────────────────────────────────────────
COLS = "(seller_id, status, manufacturer, model, body_type, year, price, mileage, color, fuel, transmission, displacement, seats, region, accident_free, options, description)"
rows = []
for i, r in enumerate(listings):
    seller = SELLER2 if i < 30 else SELLER3   # 30/28 분배
    rows.append(
        f"  ({q(seller)}, {q(r['status'])}, {q(r['manufacturer'])}, {q(r['model'])}, "
        f"{q(r['body_type'])}, {r['year']}, {r['price']}, {r['mileage']}, {q(r['color'])}, "
        f"{q(r['fuel'])}, {q(r['transmission'])}, {r['displacement']}, {r['seats']}, "
        f"{q(r['region'])}, {str(r['accident_free']).lower()}, {arr(r.get('options'))}, {q(r['description'])})"
    )

sql = []
sql.append("-- seed-expansion.sql — Phase A 확장분 (생성 스크립트 산출물; embedding은 NULL → 이후 backfill)")
sql.append("begin;")
sql.append(f"insert into public.listings\n  {COLS}\nvalues")
sql.append(",\n".join(rows) + ";")
sql.append("commit;")
# 가이드는 DB 직접 INSERT가 아니라 api/corpus/*.md 단일출처로 처리한다(backfill_guides가 corpus에서
# delete 후 재적재하므로 DB 직삽입은 지워진다). → write_corpus_files.py가 별도로 .md를 쓴다.

out = HERE/"seed-expansion.sql"
out.write_text("\n".join(sql), encoding="utf-8")

# ── seed.sql 단일출처 반영용 DO 블록 (재현성) ──────────────────
# 기존 seed.sql 컨벤션(auth.users+identities+profiles 승격, 멱등 delete 후 insert)을 따른다.
def values_for(idx_range):
    return ",\n".join(rows[i].replace(q(SELLER2),"v_s2").replace(q(SELLER3),"v_s3")
                       for i in idx_range)
# rows에는 seller UUID가 문자열로 박혀 있으니, DO 블록에선 변수로 치환
s2_vals = ",\n".join(rows[i] for i in range(0,30)).replace(q(SELLER2), "v_s2")
s3_vals = ",\n".join(rows[i] for i in range(30,58)).replace(q(SELLER3), "v_s3")

block = f"""
-- ════════════════════════════════════════════════════════════════════
-- [Phase A 확장] 신규 판매자 2명 + 매물 58건 (총 ~100건 데모 데이터)
-- ════════════════════════════════════════════════════════════════════
-- seller-seed2/3@test.com 을 seed.sql 컨벤션대로 생성하고, 각 30/28건 매물을 멱등 삽입한다.
-- embedding은 NULL(컬럼 생략) → backfill_embeddings.py 가 채운다.
-- ⚠️ 데모 전용 계정: seller-seed2@test.com / seller-seed3@test.com (비밀번호는 세션 변수 app.seed_password 로 주입)
do $$
declare
  v_emails text[] := array['seller-seed2@test.com','seller-seed3@test.com'];
  v_email  text;
  v_s2 uuid; v_s3 uuid;
begin
  foreach v_email in array v_emails loop
    if not exists (select 1 from auth.users where email = v_email) then
      insert into auth.users (
        id, instance_id, aud, role, email, encrypted_password,
        email_confirmed_at, raw_app_meta_data, raw_user_meta_data,
        confirmation_token, recovery_token, email_change_token_new, email_change,
        created_at, updated_at
      ) values (
        gen_random_uuid(), '00000000-0000-0000-0000-000000000000',
        'authenticated', 'authenticated', v_email,
        extensions.crypt(current_setting('app.seed_password', true), extensions.gen_salt('bf')), now(),
        '{{"provider":"email","providers":["email"]}}'::jsonb,
        '{{"role":"seller"}}'::jsonb, '', '', '', '', now(), now()
      );
      insert into auth.identities (provider_id, user_id, identity_data, provider, last_sign_in_at, created_at, updated_at)
      select id::text, id, jsonb_build_object('sub', id::text, 'email', v_email), 'email', now(), now(), now()
        from auth.users where email = v_email;
    end if;
    update public.profiles set role='seller'
     where id=(select id from auth.users where email=v_email) and role<>'seller';
  end loop;

  select id into v_s2 from auth.users where email='seller-seed2@test.com';
  select id into v_s3 from auth.users where email='seller-seed3@test.com';

  -- 멱등: 두 시드 판매자 소유 매물만 삭제 후 재삽입
  delete from public.listings where seller_id in (v_s2, v_s3);

  insert into public.listings
    {COLS}
  values
{s2_vals},
{s3_vals};

  raise notice '[seed] Phase A 확장 매물 준비 완료: seller2/3 합계 %건',
    (select count(*) from public.listings where seller_id in (v_s2, v_s3));
end $$;
"""
block_out = HERE/"seed-expansion-block.sql"
block_out.write_text(block, encoding="utf-8")

print("✅ 검증 통과.")
print(f"   매물 {len(listings)}건 (seller2 30 / seller3 28) — 가이드는 corpus .md로 별도 처리")
print(f"   → 라이브적용용: {out.name} ({out.stat().st_size} bytes)")
print(f"   → seed.sql병합용: {block_out.name} ({block_out.stat().st_size} bytes)")
