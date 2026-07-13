// 에러 폴백 프리미티브 — 문구 + 재시도. `role="alert"`로 스크린리더가 즉시 announce한다.
// EXPERIENCE.md 규약: {danger} 톤은 파괴적/오류에만 쓰고, 404류(미존재·삭제)는 중립 톤이다.
// 그래서 톤은 소비처가 `tone`으로 고른다(하드코딩 금지).
export default function ErrorState({
  message,
  onRetry,
  tone = 'neutral',
}: {
  message: string;
  onRetry?: () => void;
  tone?: 'neutral' | 'danger';
}) {
  return (
    <div role="alert" className="flex flex-col items-center gap-3 px-6 py-12 text-center">
      <p className={`text-body ${tone === 'danger' ? 'text-danger' : 'text-ink-secondary'}`}>
        {message}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="min-h-[52px] rounded-chip border border-border-hairline px-4 text-body text-ink-primary cursor-pointer"
        >
          다시 시도
        </button>
      )}
    </div>
  );
}
