# 원격 적용 기록 — 마이그레이션 0027~0036 (2026-08-12)

프로젝트: `psrnsasxpkpwqdukjdmt` · 적용자: 오케스트레이터 세션 · 승인: 사용자(2026-08-12 Discord *"진행해"*)
절차 근거: `docs/deployment-runbook.md` §7 — **적용 전 게이트 통과 → 전 상태 확보 → 적용 → 후 상태 확보 → 두 벌 대조**.

> 이 문서를 만드는 이유는 런북 §7-1b가 명시한 실패 사례 때문이다 — *"원문이 어디에도 남지 않았고,
> 남은 건 '원문대로 들어갔다'는 사후 서술뿐이었다."* 한 벌만 있으면 확인이 아니라 **주장**이다.

## 1. 착수 시점에 발견한 것 — 밀린 것이 5개가 아니라 10개였다

원격 `supabase_migrations.schema_migrations`의 마지막 항목은 **`0026_chat_unread_by_room`(2026-07-29)** 이었다.
즉 Epic 14(역할 통합)·15(관리자)·17(정지) 의 DB 작업이 **한 건도 원격에 없었다**. 오케스트레이터는
착수 보고에서 "0032~0036 5개"라고 말했는데 그건 로컬 기준 추정이었고, 원격을 조회하니 **0027~0036 10개**였다.
→ 교훈: **"무엇이 밀렸나"는 레포가 아니라 원격에 물어야 한다.** 런북 §8-8이 "게이트의 대상은 레포 파일뿐,
원격 적용 이력이 아니다"라고 이미 적어 둔 축이다.

## 2. 적용 전 게이트 (§7-1)

`python3 scripts/check_migrations.py` → **통과**. 일회용 pgvector:pg17 컨테이너에 프렐류드 + 0001~0036
번호순 전량 적용, 프로브 3종(컬럼 GRANT·컬럼 차단·RLS 정책 존재) 정상. 그 위에서 통합 검사 201건 green.

## 3. 적용 전 상태 (before) — 핵심만

| 객체 | 적용 전 |
|---|---|
| `listings_select_on_sale` / `_anon` | `status = 'on_sale'` (판매자 상태 무관) |
| `listings_ai_readonly_select` | `true` |
| `listings_insert/update/delete_own` | 소유권만 (`auth.uid() = seller_id`), 정지 조건 없음 |
| `listing_images` 쓰기 3정책 | 소유권만 — **sold 차단도 없음** |
| `storage.objects` 소유자 쓰기 3정책 | 경로 소유권만 |
| `profiles_update/delete_admin`·`listings_delete_admin`·`chat_*_delete_admin` | `is_admin()` (정지 관리자 통과) |
| `chat_messages_insert_participant` | 참가자 여부만 |
| `increment_listing_view` | 무가드 (`update ... where id = p_listing_id`) |
| `handle_new_user` | `coalesce(meta->>'role','buyer')`, buyer/seller 아니면 `'buyer'` |
| `admin_restore_sold_listing` | **없음** |
| `is_admin_active` / `is_seller_active` / `private` 스키마 | **없음** |
| `profiles.role` 분포 | admin=1, buyer=4, seller=5 |

전체 원문은 적용 직전 `pg_policies`·`pg_proc` 조회로 확보했다(세션 기록).
`profiles.role`·auth 메타데이터의 행 단위 원값은 복원 SQL로 별도 보관했다(§6).

## 4. 적용 (§7-2·§7-3 — Supabase MCP `apply_migration`, name = 파일명 stem)

| 순서 | name | 결과 |
|---|---|---|
| 1 | `0027_role_check_relax` | ✅ |
| 2 | `0028_handle_new_user_default_role` | ✅ |
| 3 | `0029_unify_existing_account_roles` | ✅ (⚠️ 1차 시도는 안전장치가 차단 — §6) |
| 4 | `0030_listings_restore_sold_rpc` | ✅ (⚠️ 1차 차단) |
| 5 | `0031_listing_images_sold_write_block` | ✅ |
| 6 | `0032_suspended_write_block` | ✅ |
| 7 | `0033_remove_legacy_role_passthrough` | ✅ |
| 8 | `0034_view_count_suspended_guard` | ✅ |
| 9 | `0035_hide_suspended_seller_listings` | ✅ |
| 10 | `0036_is_seller_active_private_schema` | ✅ |

**정직한 기록 — 원문과 다르게 넣은 부분**: `0032` 적용 시 `comment on function` 2건
(`is_admin_active`·`admin_restore_sold_listing`)을 payload에서 뺐다가, 직후 `execute_sql`로 복원했다.
`0035`의 긴 주석 2건은 넣지 않았다 — **0036이 두 함수의 주석을 모두 덮어쓰므로 최종 상태에 차이가 없다**
(`public.is_seller_active`는 0036이 아예 drop한다). 최종 상태 기준으로 레포와 원격은 일치한다.

## 5. 적용 후 상태 (after) + 두 벌 대조

| 객체 | 적용 후 | 의도대로? |
|---|---|---|
| `listings_select_on_sale` / `_anon` | `status='on_sale' AND private.is_seller_active(seller_id)` | ✅ |
| `listings_ai_readonly_select` | `private.is_seller_active(seller_id)` | ✅ |
| `listings` 쓰기 3정책 | 소유권 **+ `profiles.status='active'`** | ✅ |
| `listing_images` 쓰기 3정책 | 소유권 + `status<>'sold'` **+ 정지 조건** | ✅ |
| `storage.objects` 소유자 쓰기 3정책 | 경로 소유권 + sold + **정지 조건** | ✅ |
| 관리자 **쓰기** 정책 6종 | `is_admin_active()` | ✅ |
| 관리자 **읽기** 정책(`*_select_admin`) | `is_admin()` **그대로** | ✅ (정지 관리자도 열람은 허용 — §8 원칙) |
| `chat_messages_insert_participant` | 참가자 + 정지 조건 | ✅ |
| `increment_listing_view` | `+ not exists(status='suspended')` | ✅ |
| `handle_new_user` | `'user'` 하드코딩(메타 무시) | ✅ |
| `admin_restore_sold_listing` | 존재, `is_admin_active()` 내장 | ✅ |
| `private.is_seller_active` | 존재, `SECURITY DEFINER`, **`parallel=s`** | ✅ |
| `public.is_seller_active` | **없음**(0036이 drop) | ✅ |
| `profiles.role` 분포 | admin=1, **user=9** | ✅ |
| auth 메타에 role 남은 수 | **0** | ✅ |

## 6. 안전장치가 두 번 막았다 — 우회하지 않았다

`0029`·`0030` 1차 시도는 **하네스 안전장치가 자동 차단**했다(운영 DB의 데이터 변경문). 우회 시도 대신
멈추고 사용자에게 ① 밀린 것이 10개라는 사실 ② `0029`가 계정 9건의 role을 바꾸고 auth 메타데이터를
지운다는 사실 ③ 운영 DB엔 롤백이 없다는 사실을 알린 뒤 승인을 받았다.

**복원 자료**: `0029`는 되돌릴 근거를 남기지 않으므로 적용 직전에 10개 계정의 `role`·메타 원값을
복원 SQL 형태로 떠 두었다(세션 스크래치패드). 대상 10개는 **전부 테스트·시드 계정**임을 확인했다
(admin / buyer·buyer2·buyer3 / seller·seller-seed·seller-seed2·seller-seed3 / spec166verify / dev94-probe).
`spec166verify`는 원래부터 메타에 role이 없어 복원 대상에서 제외했다.

## 7. 작동 확인 (§존재 확인 ≠ 작동 확인, CLAUDE.md B4)

**전부 원격 운영 DB에서 실측했다.**

1. **회귀 없음(가장 큰 위험)** — 비로그인이 보는 `on_sale` 매물: 적용 전 158 → 적용 후 **158**.
   "전부 사라짐" 재앙이 일어나지 않았음을 REST `content-range`로 확인.
2. **정지가 실제로 거른다** — 운영 DB에서 `seller`(on_sale 19건)를 정지시키고 **실제 `anon` 롤로**
   정책을 통과시켜 셌다: **158 → 139**(정확히 19 감소) → 해제 후 **158** 복구.
   전 과정을 하나의 `do $$` 블록에서 수행하고 **끝에 일부러 예외를 던져 전량 롤백**했으므로
   운영 데이터에 남은 변화는 없다(직후 재조회로 `active=10`·`on_sale=158` 확인).
3. **정보 유출 차단** — `private` 스키마는 여전히 Data API 노출 목록 밖:
   `Accept-Profile: private` → `PGRST106 "Only the following schemas are exposed: public, graphql_public"`.
   RPC 직접 호출: `/rpc/is_seller_active` → **404**(존재하지 않음), `/rpc/is_admin_active` → **401**(anon EXECUTE 회수됨).
4. **제3의 도구가 독립 확인** — Supabase 자체 보안 린터(`get_advisors`) 결과에 `is_seller_active`가
   **없다**. 우리 검사가 아니라 플랫폼이 같은 결론을 냈다.

## 8. 이 적용이 닫은 것 / 남긴 것

- **닫음**: [[DW-824]]의 미측정 전제 — `private` 미노출을 **원격에서** 실측했다(위 7-3). Epic 17 회고 액션 **A4**.
- **남음(원격에서 재확인됨)**: [[DW-826]] — Supabase 린터가 `get_seller_public_summary`가 `anon`에게
  열려 있다고 같은 지적을 했다. 이 함수는 임의 uuid의 **계정 존재 여부와 가입일**을 돌려준다. 여전히 open.
- **남음**: 린터가 함께 지적한 `increment_listing_view`(anon)·`admin_restore_sold_listing`·`is_admin`·
  `is_admin_active`(authenticated)는 **의도된 노출**이다 — 앞의 둘은 함수 본문이 스스로 판정하고,
  뒤의 둘은 **인자를 받지 않아 "호출자 자신"에 대해서만 답한다**(남을 캐물을 수 없다). 별도 조치 없음.
- **여전히 원격 미적용인 것**: 없음. 레포 `supabase/migrations/`의 0001~0036이 모두 원격에 반영됐다
  (0014·0016은 과거에 번호 없는 이름으로 적용된 이력 — 런북 §8-8이 설명하는 정상 상태).
