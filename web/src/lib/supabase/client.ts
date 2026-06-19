// 브라우저(클라이언트 컴포넌트)용 Supabase 클라이언트.
// 'use client' 컴포넌트에서 호출해 인증·CRUD·채팅을 RLS 경유로 직접 수행한다.
// anon key는 RLS가 보호하므로 브라우저 노출이 안전하다(service_role 키는 사용하지 않음).
import { createBrowserClient } from '@supabase/ssr';
import { getSupabaseEnv } from './env';

export function createClient() {
  // env 누락 시 어떤 변수가 비었는지 한국어로 알려주는 가드(불투명 throw 방지).
  const { url, anonKey } = getSupabaseEnv();
  return createBrowserClient(url, anonKey);
}
