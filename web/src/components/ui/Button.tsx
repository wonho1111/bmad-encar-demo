// 공용 버튼 컴포넌트 — 앱 전체 버튼의 외형·커서·로딩 표시를 한 곳에서 관리한다.
//
// 왜 만들었나:
//   그동안 버튼을 화면마다 직접(<button className="rounded ...">) 써서, 커서(손가락/화살표)와
//   "처리 중" 표시가 제각각이었다(예: 검색 버튼은 커서가 화살표라 눌러도 죽은 느낌). 이 컴포넌트로
//   스타일을 단일 출처로 모아, 새 버튼은 <Button>만 쓰면 자동으로 통일되게 한다.
//
// 두 가지 export:
//   · <Button> — 실제 <button> 엘리먼트(클릭 액션·제출용). loading이면 비활성 + loadingText 표시.
//   · buttonClasses() — 같은 외형을 <Link>(화면 이동용 링크)에도 입히기 위한 클래스 문자열 생성 함수.
//     (링크는 <a>라 브라우저가 이미 손가락 커서를 주므로 별도 컴포넌트 대신 스타일만 공유한다.)
import type { ButtonHTMLAttributes } from 'react';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'info';
export type ButtonSize = 'md' | 'sm';

// variant = 색/강조. primary=주버튼(검정), secondary=보조(테두리), danger=삭제(빨강), info=구매완료(파랑).
const VARIANT_CLASSES: Record<ButtonVariant, string> = {
  primary: 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900',
  secondary: 'border border-zinc-300 dark:border-zinc-700',
  danger: 'border border-red-300 text-red-700 dark:border-red-800 dark:text-red-300',
  info: 'border border-blue-300 text-blue-700 dark:border-blue-800 dark:text-blue-300',
};

// size = 크기. md=기본(폼 제출·검색 등), sm=목록 행의 작은 버튼(구매완료·수정·삭제).
const SIZE_CLASSES: Record<ButtonSize, string> = {
  md: 'px-4 py-2 text-sm',
  sm: 'px-2 py-1 text-xs',
};

// 공용 스타일 문자열을 만든다. <button>은 아래 Button이 쓰고,
// 버튼처럼 보여야 하는 <Link>는 이 함수를 className에 직접 넣어 같은 외형을 공유한다.
//   cursor-pointer = 마우스를 올리면 손가락 커서(클릭 가능 신호). 비활성 시엔 not-allowed로 덮는다.
export function buttonClasses({
  variant = 'primary',
  size = 'md',
  className = '',
}: { variant?: ButtonVariant; size?: ButtonSize; className?: string } = {}): string {
  return [
    'inline-flex items-center justify-center rounded font-medium cursor-pointer',
    'transition-opacity disabled:opacity-50 disabled:cursor-not-allowed',
    SIZE_CLASSES[size],
    VARIANT_CLASSES[variant],
    className,
  ]
    .filter(Boolean)
    .join(' ');
}

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean; // 처리 중이면 자동으로 비활성 + loadingText 표시(중복 클릭 방지는 호출부 로직과 함께 동작)
  loadingText?: string; // 처리 중 라벨(예: "처리 중…"). 없으면 children을 그대로 둔다.
};

export default function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  loadingText,
  disabled,
  className,
  type = 'button', // 기본 button — 폼 안에서 실수로 제출되지 않게(제출 버튼은 type="submit" 명시)
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading} // 로딩 중엔 항상 비활성(연타 차단)
      className={buttonClasses({ variant, size, className })}
      {...rest}
    >
      {loading && loadingText ? loadingText : children}
    </button>
  );
}
