// Supabase 연결에 필요한 환경변수를 한 곳에서 읽고, 누락 시 "어떤 변수가 비었는지"를
// 명확한 한국어 에러로 알린다.
// 기존 코드는 `process.env.X!`(비-널 단언)을 썼는데, 이는 컴파일러만 침묵시킬 뿐
// 값이 실제로 비어 있어도 런타임에서는 불투명한 에러로 터진다(원인 진단 불가).
// 이 헬퍼로 모든 클라이언트가 같은 진단 가능한 가드를 공유한다.
export function getSupabaseEnv() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

  const missing: string[] = [];
  if (!url) missing.push('NEXT_PUBLIC_SUPABASE_URL');
  if (!anonKey) missing.push('NEXT_PUBLIC_SUPABASE_ANON_KEY');

  if (missing.length > 0) {
    throw new Error(
      `Supabase 환경변수가 설정되지 않았습니다: ${missing.join(', ')}. ` +
        `web/.env.local 파일에 값을 넣어주세요.`,
    );
  }

  return { url: url as string, anonKey: anonKey as string };
}
