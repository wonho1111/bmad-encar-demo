// 빈 상태 프리미티브 — 아이콘 + 문구 + 선택적 CTA. 색 단독 신호를 피하려고 아이콘/텍스트를 함께 쓴다.
// 문구는 EXPERIENCE.md States 표가 정본이지만, 하드코딩하지 않고 소비처가 props로 맥락 문구를 넣는다.
import type { ReactNode } from 'react';

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div role="status" className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      {icon && (
        <span aria-hidden className="text-3xl text-ink-muted">
          {icon}
        </span>
      )}
      <p className="text-card-title font-semibold text-ink-primary">{title}</p>
      {description && <p className="text-body text-ink-secondary">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
