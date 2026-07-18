'use client';

// 포커스 트랩 범용 래퍼 — 모달·바텀시트·드롭다운·로그인 게이트가 감싸 쓰는 메커니즘만 제공한다
// (실제 모달 UI는 만들지 않는다 — 소비 에픽 몫, A2). DOM 포커스를 직접 만지므로 클라이언트 컴포넌트다.
// 열릴 때: 첫 포커서블 요소로 이동. Tab/Shift+Tab: 트랩 안에서 순환. 클릭 등으로 포커스가 컨테이너
// 밖으로 벗어나도 다시 끌어옴. Esc: onClose 호출. 닫힐 때(언마운트): 트리거 요소로 포커스 복귀.
// role="dialog"/aria-modal/aria-labelledby 등 실제 모달 시맨틱은 강제하지 않는다 — 소비처가
// ...rest로 컨테이너 div에 직접 붙인다(코드리뷰 결정, deferred-work.md 참고).
import { useEffect, useRef } from 'react';
import type { HTMLAttributes, ReactNode } from 'react';

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

// querySelectorAll은 display:none 등으로 숨겨진 요소도 매칭한다 — offsetParent로 실제 보이는
// 요소만 걸러낸다(숨겨진 요소로 포커스가 가면 사용자 눈엔 아무것도 포커스 안 된 것처럼 보임).
function getVisibleFocusables(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
    (node) => node.offsetParent !== null,
  );
}

type FocusTrapProps = {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
} & HTMLAttributes<HTMLDivElement>;

export default function FocusTrap({ open, onClose, children, ...rest }: FocusTrapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLElement | null>(null);
  // onClose를 ref로 감싸 effect 의존성에서 뺀다 — 부모가 인라인 함수(매 렌더 새 identity)를
  // 넘겨도 effect가 재실행되지 않아, 트랩이 열려 있는 동안 포커스가 반복 튕기지 않는다.
  // 갱신은 렌더가 아니라 effect에서 한다 — 렌더 중 ref 쓰기는 React가 렌더를 버리거나
  // 재실행할 때 어긋난 값이 남을 수 있어 금지돼 있다(react-hooks/refs).
  const onCloseRef = useRef(onClose);
  useEffect(() => {
    onCloseRef.current = onClose;
  });

  useEffect(() => {
    if (!open) return;
    const container = containerRef.current;
    if (!container) return;

    triggerRef.current = document.activeElement as HTMLElement | null;
    // 포커서블 요소가 하나도 없어도(빈 컨테이너) 컨테이너 자체로 폴백 — 포커스가 갈 곳이 없어
    // 트랩 밖(브라우저 기본값)으로 새는 것을 막는다. tabIndex={-1}(아래)로 프로그램 포커스만 허용.
    (getVisibleFocusables(container)[0] ?? container).focus();

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onCloseRef.current();
        return;
      }
      if (event.key !== 'Tab' || !container) return;

      const nodes = getVisibleFocusables(container);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];

      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }

    // Tab 순환만으로는 컨테이너 밖 요소가 클릭 등으로 포커스를 받는 경우를 막지 못한다 —
    // 포커스가 컨테이너 밖으로 나가면 즉시 안으로 되돌린다(진짜 "트랩").
    function handleFocusIn(event: FocusEvent) {
      if (container && !container.contains(event.target as Node)) {
        (getVisibleFocusables(container)[0] ?? container).focus();
      }
    }

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('focusin', handleFocusIn);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('focusin', handleFocusIn);
      triggerRef.current?.focus();
    };
  }, [open]);

  if (!open) return null;

  return (
    <div ref={containerRef} tabIndex={-1} {...rest}>
      {children}
    </div>
  );
}
