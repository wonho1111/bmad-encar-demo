'use client';

// 매물 사진 업로더 (AC1·AC2·AC3·AC6) — 등록·수정 폼이 공유한다.
//
// **이 컴포넌트는 파일을 직접 올리지 않는다.** 선택·순서·삭제·표시만 하고, 실제 업로드는
// SellForm이 제출 시점에 한다. 이유는 AC5 — 저장 경로가 `{user_id}/{listing_id}/…`라
// 신규 등록은 listings INSERT로 listing_id를 받기 전엔 올릴 곳이 없다(스테이징 경로 없음).
// 등록·수정 두 모드가 같은 코드를 타도록 수정 모드도 같은 시점에 올린다.
//
// **대표 = 배열 0번**이다(사용자 확정 2026-07-18). 대표 전용 상태·토글이 없는 것은 의도다 —
// 순서와 대표가 각각 움직이면 진실이 두 군데 생긴다. [대표로] 버튼은 moveToFront(0번으로 이동)
// 하나만 호출한다(lib/images/order.ts).
import { useEffect, useId, useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import { validateImageFile } from '@/lib/images/validate';
import { moveToFront, remove, reorder } from '@/lib/images/order';
// 타입·변환은 'use client'가 없는 별도 모듈에 둔다 — 수정 페이지(서버 컴포넌트)가
// toPhotoItems를 부르기 때문이다(이 파일에 두면 런타임에 죽는다, photo-item.ts 주석 참조).
import { MAX_PHOTOS, toLocalPhotoItem, type PhotoItem } from './photo-item';

type PhotoUploaderProps = {
  items: PhotoItem[];
  onChange: (next: PhotoItem[]) => void;
  /** 제출 중에는 조작을 막는다(업로드가 진행 중인 목록을 흔들면 결과가 어긋난다). */
  disabled?: boolean;
};

export default function PhotoUploader({ items, onChange, disabled = false }: PhotoUploaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const inputId = useId();
  const [dragOver, setDragOver] = useState(false);
  const [dragFrom, setDragFrom] = useState<number | null>(null);
  // 파일 선택 자체가 거부된 경우(10장 초과)는 특정 항목에 붙일 수 없어 목록 위에 한 줄로 알린다.
  const [pickError, setPickError] = useState<string | null>(null);

  // objectURL은 명시적으로 놓아주지 않으면 탭이 닫힐 때까지 메모리에 남는다.
  // 언마운트 시 이 컴포넌트가 만든 것(file이 있는 항목)만 회수한다 — 서명 URL은 revoke 대상이 아니다.
  const itemsRef = useRef(items);
  useEffect(() => {
    itemsRef.current = items;
  });
  useEffect(() => {
    return () => {
      for (const p of itemsRef.current) {
        if (p.file && p.previewUrl) URL.revokeObjectURL(p.previewUrl);
      }
    };
  }, []);

  // 검증 실패(용량초과·포맷거부)로 애초에 업로드된 적 없는 항목 — 목록엔 남기지만(AC3) 저장될
  // 사진이 아니므로 정원(count/room/full)에서는 뺀다. storagePath가 있으면(=한 번이라도 저장된
  // 적 있는 사진) 상태가 error여도 여기서 빼지 않는다 — 실제로 자리를 차지하는 사진이라서다
  // (코드리뷰 2026-07-19).
  function isRejected(p: PhotoItem): boolean {
    return p.status === 'error' && p.retryable === false && !p.storagePath;
  }

  const count = items.filter((p) => !isRejected(p)).length;
  const full = count >= MAX_PHOTOS;
  // 대표 배지·[대표로]가 가리켜야 할 실제 위치 — photo-sync.ts가 저장하는 대표(survivors[0])와
  // 같은 기준(첫 error 아닌 항목)이어야 화면과 DB가 갈리지 않는다.
  const firstSavableIndex = items.findIndex((p) => p.status !== 'error');

  function addFiles(fileList: FileList | null) {
    if (!fileList || fileList.length === 0) return;
    setPickError(null);

    const room = MAX_PHOTOS - count;
    const picked = Array.from(fileList);

    // (a) UI가 10장 초과 선택을 애초에 막는다(AC9). ⚠️ 이건 UX 층의 1차 차단이고,
    //     강제는 서버(0012 트리거)에 남아 있다 — 클라가 막는다고 서버 검증을 빼지 않는다.
    const accepted = picked.slice(0, Math.max(0, room));
    if (picked.length > accepted.length) {
      setPickError(`사진은 최대 ${MAX_PHOTOS}장까지 올릴 수 있어요. ${picked.length - accepted.length}장은 제외했어요.`);
    }

    const next: PhotoItem[] = accepted.map((file) => {
      const verdict = validateImageFile(file);
      // 거부된 파일도 **목록에 남긴다** — 어느 파일이 왜 안 됐는지 보여야 하기 때문(AC3).
      // 재시도는 주지 않는다: 용량·포맷은 다시 눌러도 같은 결과다(고칠 방법은 다른 파일 선택뿐).
      if (!verdict.ok) return toLocalPhotoItem(file, null, verdict.reason);
      return toLocalPhotoItem(file, URL.createObjectURL(file));
    });

    onChange([...items, ...next]);
  }

  function handleRemove(index: number) {
    const target = items[index];
    // 새로 고른 파일의 미리보기만 회수한다(기존 사진의 서명 URL은 objectURL이 아니다).
    if (target?.file && target.previewUrl) URL.revokeObjectURL(target.previewUrl);
    // 0번을 지우면 다음 장이 0번이 되어 자동으로 대표가 승격된다 — 별도 처리가 없는 게 정상이다(AC3).
    onChange(remove(items, index));
    setPickError(null);
  }

  function handleRetry(index: number) {
    // 업로드 실패 항목을 다시 대기 상태로 되돌린다. 실제 재업로드는 다음 제출에서 일어난다.
    onChange(items.map((p, i) => (i === index ? { ...p, status: 'idle', error: undefined } : p)));
  }

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">사진</span>
        <span className="text-sm tabular-nums text-zinc-500 dark:text-zinc-400">
          {count}/{MAX_PHOTOS}
        </span>
      </div>

      {/* 드롭존 — button이라 키보드로 도달·활성화된다(Tab → Enter/Space). */}
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={disabled || full}
        aria-describedby={`${inputId}-hint`}
        onDragOver={(e) => {
          e.preventDefault();
          if (!disabled && !full) setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (disabled || full) return;
          // 순서 변경 드래그(썸네일)와 파일 드롭을 구분한다 — 파일이 없으면 여기서 처리하지 않는다.
          if (e.dataTransfer.files?.length) addFiles(e.dataTransfer.files);
        }}
        className={[
          'flex w-full cursor-pointer flex-col items-center gap-1 rounded border-2 border-dashed px-4 py-6 text-center',
          'disabled:cursor-not-allowed disabled:opacity-50',
          dragOver ? 'border-zinc-900 bg-zinc-50 dark:border-zinc-100 dark:bg-zinc-900' : 'border-zinc-300 dark:border-zinc-700',
        ].join(' ')}
      >
        <span className="text-sm font-medium">
          {full ? `사진 ${MAX_PHOTOS}장을 모두 채웠어요` : '사진을 끌어다 놓거나 클릭해서 선택하세요'}
        </span>
        {/* 문구 정본: docs/conventions.md §10 (목업의 "20MB" 표기는 낡았다 — 베끼지 말 것). */}
        <span className="text-xs text-zinc-500 dark:text-zinc-400">JPG · PNG · WebP, 장당 최대 5MB</span>
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        className="hidden"
        onChange={(e) => {
          addFiles(e.target.files);
          // 같은 파일을 연속으로 다시 고를 수 있게 값을 비운다(안 비우면 onChange가 안 뜬다).
          e.target.value = '';
        }}
      />

      {pickError && (
        <p role="alert" className="text-sm text-red-700 dark:text-red-300">
          {pickError}
        </p>
      )}

      {count > 0 && (
        // 반응형은 **열 수로만** 흡수한다(D5) — 썸네일 내부 배치는 어느 폭에서도 접지 않는다.
        <ul className="grid grid-cols-3 gap-3 sm:grid-cols-4">
          {items.map((p, i) => (
            <li
              key={p.key}
              draggable={!disabled}
              onDragStart={() => setDragFrom(i)}
              onDragEnd={() => setDragFrom(null)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                // 파일 드롭이 썸네일 위에 떨어진 경우는 순서 변경이 아니다.
                if (e.dataTransfer.files?.length) return;
                if (dragFrom === null || dragFrom === i) return;
                // 첫 칸으로 끌면 대표가 바뀐다 — 별도 필드를 건드리지 않는 게 핵심이다(AC1 진입점 ①).
                onChange(reorder(items, dragFrom, i));
                setDragFrom(null);
              }}
              className="flex flex-col gap-1"
            >
              <div className="relative aspect-square overflow-hidden rounded border border-zinc-200 dark:border-zinc-800">
                {p.previewUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element -- objectURL·서명 URL은 next/image의 최적화 대상이 아니다(외부 서명 URL은 도메인 화이트리스트가 필요하고 TTL이 있다).
                  <img src={p.previewUrl} alt={`${i + 1}번째 사진`} className="h-full w-full object-cover" />
                ) : (
                  <div className="flex h-full w-full items-center justify-center bg-zinc-100 text-xs text-zinc-500 dark:bg-zinc-900 dark:text-zinc-400">
                    미리보기 없음
                  </div>
                )}

                {/* 대표 배지는 **저장될 첫 칸에만**(firstSavableIndex). 검증 실패 항목이 0번 자리를
                    차지해도 그 항목은 저장되지 않으므로, 배지는 실제로 저장될 첫 항목을 따라간다
                    (코드리뷰 2026-07-19 — 전엔 i===0만 봐서 0번이 거부 항목이면 배지가 어디에도
                    없는데 DB 대표는 다른 행에 붙는 불일치가 있었다). */}
                {i === firstSavableIndex && (
                  <span className="absolute left-1 top-1 rounded bg-zinc-900/85 px-1.5 py-0.5 text-[10px] font-medium text-white">
                    대표
                  </span>
                )}
                {p.status === 'uploading' && (
                  <span className="absolute inset-0 flex items-center justify-center bg-white/70 text-xs dark:bg-zinc-950/70">
                    올리는 중…
                  </span>
                )}

                <button
                  type="button"
                  onClick={() => handleRemove(i)}
                  disabled={disabled}
                  aria-label={`${i + 1}번째 사진 삭제`}
                  className="absolute right-1 top-1 rounded bg-zinc-900/85 px-1.5 py-0.5 text-xs text-white cursor-pointer disabled:cursor-not-allowed disabled:opacity-50"
                >
                  ✕
                </button>
              </div>

              {/* 실패한 사진에는 [대표로]를 주지 않는다 — 저장되지 않을 사진을 대표로 지정하는 건
                  아무 의미가 없고, 배지 없는 첫 칸이 생겨 "대표가 없어 보이는" 화면이 된다. */}
              {i !== firstSavableIndex && p.status !== 'error' && (
                <Button size="sm" variant="secondary" onClick={() => onChange(moveToFront(items, i))} disabled={disabled}>
                  대표로
                </Button>
              )}

              {p.status === 'error' && (
                <div className="flex flex-col gap-1">
                  <p role="alert" className="text-[11px] leading-tight text-red-700 dark:text-red-300">
                    {p.error}
                  </p>
                  {p.retryable && (
                    <Button size="sm" variant="secondary" onClick={() => handleRetry(i)} disabled={disabled}>
                      재시도
                    </Button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      )}

      {/* 문구 정본: 스토리 AC2. 사진 0장도 정상 완료라는 것을 사용자가 알게 한다. */}
      <p id={`${inputId}-hint`} className="text-xs text-zinc-500 dark:text-zinc-400">
        사진은 선택이에요. 없어도 등록되지만, 있으면 문의가 훨씬 잘 와요.
      </p>
    </section>
  );
}
