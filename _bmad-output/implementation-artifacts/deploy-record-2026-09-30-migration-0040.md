# 원격 적용 기록 — 마이그레이션 0040 (2026-09-30)

프로젝트: `psrnsasxpkpwqdukjdmt` · 적용자: **사용자(Supabase 대시보드 SQL Editor)** · 승인: 사용자(2026-09-30 "2단계 ㅇㅇ")
절차 근거: `docs/deployment-runbook.md` §7. **§7-2(MCP `apply_migration`)를 따르지 못했다** — 오케스트레이터 세션의 운영 DB 조회·적용이 자동 권한 검사에 막혀, 같은 SQL을 사용자가 SQL Editor에서 직접 실행했다.

## 1. 적용 전 게이트 (§7-1)
`python3 scripts/check_migrations.py` → 통과(일회용 컨테이너에 프렐류드 + 0001~0040 적용, 프로브 3종 정상).

## 2. 적용 전 원문 (§7-1b, 사용자가 SQL Editor에서 조회해 전달)
```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  insert into public.profiles (id, role, status, name)
  values (new.id, 'user', 'active', split_part(new.email, '@', 1))
  on conflict (id) do nothing;

  return new;
end;
$function$
```
= 저장소 0033과 동일.

## 3. 적용
`supabase/migrations/0040_handle_new_user_oauth_name.sql`의 `create or replace function` 문을 SQL Editor에서 실행.

## 4. 적용 후 원문 (사용자가 같은 조회로 전달)
```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'public'
AS $function$
begin
  insert into public.profiles (id, role, status, name)
  values (
    new.id,
    'user',
    'active',
    coalesce(
      nullif(split_part(new.email, '@', 1), ''),
      nullif(new.raw_user_meta_data->>'name', ''),
      nullif(new.raw_user_meta_data->>'nickname', ''),
      nullif(new.raw_user_meta_data->>'full_name', ''),
      '회원'
    )
  )
  on conflict (id) do nothing;

  return new;
end;
$function$
```
대조: 바뀐 것은 name 식 하나. SECURITY DEFINER·search_path=public·role/status·on conflict 그대로.

## 5. 이 기록이 확인하지 못한 것
- **원격 마이그레이션 원장(`supabase_migrations.schema_migrations`)에 0040 행이 없다** — SQL Editor 실행은 원장을 쓰지 않는다. 원장 마지막은 0039(2026-09-30 적용 전 `list_migrations`로 확인). → DW-895.
- 트리거 배선·execute 권한은 조회하지 못했다(운영 조회 차단). `create or replace`는 함수 객체를 유지하므로 바뀌지 않는다는 것은 PostgreSQL 동작에 따른 추론이지 이번 실측이 아니다. 미리보기 사이트의 실제 카카오 가입으로 프로필 생성을 확인한다.
- 같은 날 사용자가 대시보드에서 한 설정: Auth → Kakao provider 활성화(REST API 키·Client Secret), URL Configuration Redirect URLs에 운영·미리보기 주소 추가. 저장소에 파일로 남지 않는 설정이다.
