-- seed-depreciation-adjustments.sql — 기존 아반떼·쏘렌토·그랜저 매물 중 v3 감가 규칙가와 25% 넘게 괴리된 행의 가격 조정 제안(별도 승인 대상)
begin;
update public.listings set price = 23400000 where id = '48a04c3b-30f2-40e0-9fae-2b4e8e932eaa';
update public.listings set price = 30710000 where id = '38ec1bab-983e-455e-a8e3-c1be96660884';
update public.listings set price = 14010000 where id = '661b38a9-a387-4864-a16d-f2cfed91c29b';
update public.listings set price = 23450000 where id = '3345a3cc-731e-4385-97bf-5fa4df1398c5';
update public.listings set price = 24560000 where id = 'b4c2b201-c65d-4208-8154-9304fa400eda';
update public.listings set price = 23440000 where id = 'acb88fea-2d25-42d6-8391-29f6b48b6848';
update public.listings set price = 13320000 where id = '3796aab6-7236-4dd0-acb4-3922c721a9c6';
commit;
