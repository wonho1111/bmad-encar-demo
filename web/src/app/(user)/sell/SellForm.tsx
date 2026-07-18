'use client';

// 매물 등록·수정 겸용 폼 (FR5·FR7 등록 / FR6 수정) — 15필드 입력 → listings INSERT(등록) 또는 UPDATE(수정).
//
// mode로 동작을 가른다:
//   · 'create'(기본): INSERT → status=on_sale로 즉시 노출(2-2 동작 그대로, 회귀 금지).
//   · 'edit': 기존 매물(initialValues)을 폼에 미리 채우고, 제출 시 listingId 행을 UPDATE(2-3).
//       - status·seller_id는 UPDATE payload에서 제외 → 구매완료(2-4) 침범·소유권 위조 차단.
//       - UPDATE/DELETE는 RLS(listings_update_own)가 본인 매물만 허용 → 타인 매물은 0행 반환 → 한국어 거부 안내(AC4).
//
// 설계(signup/page.tsx 패턴 재사용):
//   · noValidate + 직접 검증 → 한국어 오류 메시지(네이티브 영문 검증 끔).
//   · loading으로 중복 제출 차단.
//   · 고정 목록 6필드는 <select> 드롭다운(LISTING_OPTIONS 단일출처) → 목록 밖 값 선택 불가.
//   · seller_id는 등록 시 현재 로그인 user.id로 명시(INSERT RLS with check가 위조 차단 — 2-1).
//   · 단위(원·km·cc·년·명)는 입력란 라벨에 표기, 저장은 정수.
//   · DB CHECK/RLS 위반은 한국어로 변환해 노출(원본·코드는 콘솔에만).
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { LISTING_OPTIONS, LISTING_RANGES, LISTING_STATUS, UNITS } from '@/lib/constants';
import Button from '@/components/ui/Button';
import FocusTrap from '@/components/ui/FocusTrap';
import PhotoUploader from './PhotoUploader';
import { type PhotoItem } from './photo-item';
import { syncListingPhotos } from './photo-sync';

// 폼 상태 — 통신선/DB와 일치하도록 snake_case 키. 수치는 문자열로 받고 제출 시 정수 변환(빈칸 구분 위함).
type FormState = {
  manufacturer: string;
  model: string;
  body_type: string;
  year: string;
  price: string;
  mileage: string;
  color: string;
  fuel: string;
  transmission: string;
  displacement: string;
  seats: string;
  region: string;
  accident_free: boolean;
  options: string; // 쉼표 구분 입력 → 배열 변환
  description: string;
};

const INITIAL: FormState = {
  manufacturer: '',
  model: '',
  body_type: '',
  year: '',
  price: '',
  mileage: '',
  color: '',
  fuel: '',
  transmission: '',
  displacement: '',
  seats: '',
  region: '',
  accident_free: true,
  options: '',
  description: '',
};

// 수정 모드 진입 시 서버가 넘겨주는 기존 매물 값(snake_case, DB 그대로). 폼 입력값(문자열)으로 변환해 미리 채운다.
export type ListingInitialValues = {
  manufacturer: string;
  model: string;
  body_type: string;
  year: number;
  price: number;
  mileage: number;
  color: string;
  fuel: string;
  transmission: string;
  displacement: number;
  seats: number;
  region: string;
  accident_free: boolean;
  options: string[] | null;
  description: string | null;
};

// DB 값(숫자·배열·null) → 폼 상태(문자열·쉼표문자열)로 변환. 등록 폼과 동일한 입력 규칙으로 맞춘다.
function toFormState(v: ListingInitialValues): FormState {
  return {
    manufacturer: v.manufacturer,
    model: v.model,
    body_type: v.body_type,
    year: String(v.year),
    price: String(v.price),
    mileage: String(v.mileage),
    color: v.color,
    fuel: v.fuel,
    transmission: v.transmission,
    displacement: String(v.displacement),
    seats: String(v.seats),
    region: v.region,
    accident_free: v.accident_free,
    options: (v.options ?? []).join(', '), // text[] → 쉼표 구분 문자열(입력 UI 규칙과 일치)
    description: v.description ?? '',
  };
}

type SellFormProps = {
  mode?: 'create' | 'edit';
  listingId?: string; // edit 모드 필수 — UPDATE 대상 행 id
  initialValues?: ListingInitialValues; // edit 모드 필수 — 기존 값 미리 채움
  // 수정 모드에서 서버가 발급한 서명 URL과 함께 내려주는 기존 사진(sort_order 순).
  // 서명은 반드시 서버에서 한다 — lib/storage/index.ts는 서버 전용이다(9.2).
  initialPhotos?: PhotoItem[];
};

// Postgres/Supabase 에러를 사용자용 한국어 메시지로 변환(원본 메시지·코드는 화면에 직접 노출하지 않음).
//   23514 = check_violation(목록 밖 값·범위 위반), 42501 = insufficient_privilege(RLS 거부).
function toKoreanError(err: { message: string; code?: string }, mode: 'create' | 'edit'): string {
  const code = err.code ?? '';
  if (code === '23514') {
    return '입력값이 허용 목록/범위를 벗어났습니다. 드롭다운 항목과 숫자 범위를 확인해주세요.';
  }
  if (code === '42501') {
    // 권한/RLS 거부 — 등록은 본인 명의 위조, 수정은 타인 매물 접근.
    return mode === 'edit'
      ? '본인 매물만 수정할 수 있습니다. 다시 로그인 후 시도해주세요.'
      : '본인 명의로만 매물을 등록할 수 있습니다. 다시 로그인 후 시도해주세요.';
  }
  return mode === 'edit'
    ? '매물 수정 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
    : '매물 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}

export default function SellForm({ mode = 'create', listingId, initialValues, initialPhotos = [] }: SellFormProps) {
  const router = useRouter();
  const startedInEditMode = mode === 'edit';
  // 수정 모드면 기존 값으로 초기화, 등록 모드면 빈 폼. (dirty 비교 기준선이라 최초 진입 시점 값으로
  // 고정한다 — 아래 isEditMode가 등록 성공 후 바뀌어도 이 기준선은 그대로여야 한다.)
  const initialForm = startedInEditMode && initialValues ? toFormState(initialValues) : INITIAL;
  const [form, setForm] = useState<FormState>(initialForm);
  const [photos, setPhotos] = useState<PhotoItem[]>(initialPhotos);
  // 등록 성공 직후 이 매물의 재제출을 "수정"으로 돌리기 위한 상태(F13, 코드리뷰 2026-07-19).
  // 왜 필요한가: 사진 일부가 실패해 폼이 화면에 남았을 때, 유일한 제출 버튼([매물 등록])을
  // 다시 누르면 이미 성공한 listings INSERT가 또 돌아 같은 차가 2건 등록됐다. 매물은 이미
  // 존재하므로 그 시점부터는 "수정"이 사실에 맞다 — mode prop 대신 상태로 관리해 세션 도중
  // create → edit로 전환할 수 있게 한다.
  const [isEditMode, setIsEditMode] = useState(startedInEditMode);
  const [activeListingId, setActiveListingId] = useState<string | undefined>(listingId);
  const [loading, setLoading] = useState(false);
  // 제출 중인가 — 렌더를 기다리지 않는 빗장(#61). 화면 표시는 위 `loading`이 담당한다.
  const submittingRef = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  // 이탈 확인 다이얼로그(AC7). null이면 닫힘, 값이 있으면 "확인 후 갈 곳".
  const [leaveTo, setLeaveTo] = useState<string | null>(null);

  // dirty = 초기값 대비 폼 필드가 바뀌었거나, 사진을 추가/삭제/순서변경했는가(AC7).
  // 사진은 key 나열을 비교한다 — 추가·삭제뿐 아니라 **순서 변경도 잡아야** 하기 때문
  // (순서가 곧 대표라서, 순서만 바꾸고 나가면 사용자가 한 일이 통째로 사라진다).
  const formDirty = (Object.keys(initialForm) as (keyof FormState)[]).some((k) => form[k] !== initialForm[k]);
  const photosDirty =
    photos.length !== initialPhotos.length || photos.some((p, i) => p.key !== initialPhotos[i]?.key);
  const dirty = formDirty || photosDirty;

  // 새로고침·탭 닫기·주소 직접 입력만 여기서 막힌다.
  // ⚠️ Next.js App Router에는 <Link> 내부 이동을 가로채는 공식 API가 없다 —
  //    그래서 이 폼의 [취소]는 Link가 아니라 버튼으로 바꿔 직접 확인을 띄운다(아래).
  //    그 외 내비게이션 링크(헤더 등)로 나가는 경로는 **막히지 않는다**(docs/tech-debt.md 등재).
  useEffect(() => {
    if (!dirty) return;
    function onBeforeUnload(e: BeforeUnloadEvent) {
      // 브라우저는 보안상 커스텀 문구를 무시하고 자체 확인창을 띄운다(문구 지정 불가).
      e.preventDefault();
      // preventDefault()만으로는 Safari 등 일부 브라우저가 확인창을 띄우지 않는다 — 그 환경에선
      // 경고 없이 작성 내용이 사라진다(코드리뷰 2026-07-19). 표준은 returnValue 설정도 요구한다.
      e.returnValue = '';
    }
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => window.removeEventListener('beforeunload', onBeforeUnload);
  }, [dirty]);

  /** 이탈 시도 — 변경이 없으면 경고 없이 바로 보낸다(AC7). */
  function attemptLeave(href: string) {
    if (dirty) setLeaveTo(href);
    else router.push(href);
  }

  function update<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  // 제출 전 클라이언트 검증 — 통과하면 정수 변환된 INSERT 페이로드를 반환, 실패하면 한국어 메시지 반환.
  function validateAndBuild():
    | { ok: true; payload: Record<string, unknown> }
    | { ok: false; message: string } {
    // 필수 텍스트/드롭다운
    if (!form.manufacturer) return { ok: false, message: '제조사를 선택해주세요.' };
    if (!form.model.trim()) return { ok: false, message: '모델명을 입력해주세요.' };
    if (!form.body_type) return { ok: false, message: '차종을 선택해주세요.' };
    if (!form.color) return { ok: false, message: '색상을 선택해주세요.' };
    if (!form.fuel) return { ok: false, message: '연료를 선택해주세요.' };
    if (!form.transmission) return { ok: false, message: '변속기를 선택해주세요.' };
    if (!form.region) return { ok: false, message: '지역을 선택해주세요.' };

    // 수치 — 정수 변환 + 범위 검증
    const year = Number(form.year);
    const price = Number(form.price);
    const mileage = Number(form.mileage);
    const displacement = Number(form.displacement);
    const seats = Number(form.seats);

    if (!form.year || !Number.isInteger(year) || year < LISTING_RANGES.year.min || year > LISTING_RANGES.year.max) {
      return { ok: false, message: `연식은 ${LISTING_RANGES.year.min}~${LISTING_RANGES.year.max}년 사이로 입력해주세요.` };
    }
    // price·mileage·displacement는 DB가 정수형(bigint/int)이라 소수를 넣으면 DB 단계에서 거절되고
    // 그 에러는 toKoreanError가 매핑하지 못해 일반 메시지로만 보인다 → 여기서 Number.isInteger로
    // 먼저 차단해 "정수만 저장(AC3)"을 폼이 보장하고 명확한 한국어 메시지를 준다(year·seats와 동일 규칙).
    if (form.price === '' || !Number.isInteger(price) || price < LISTING_RANGES.price.min) {
      return { ok: false, message: '가격은 0원 이상의 정수로 입력해주세요(소수점 불가).' };
    }
    if (form.mileage === '' || !Number.isInteger(mileage) || mileage < LISTING_RANGES.mileage.min) {
      return { ok: false, message: '주행거리는 0km 이상의 정수로 입력해주세요(소수점 불가).' };
    }
    if (form.displacement === '' || !Number.isInteger(displacement) || displacement < LISTING_RANGES.displacement.min) {
      return { ok: false, message: '배기량은 0cc 이상의 정수로 입력해주세요(전기차는 0, 소수점 불가).' };
    }
    if (!form.seats || !Number.isInteger(seats) || seats < LISTING_RANGES.seats.min || seats > LISTING_RANGES.seats.max) {
      return { ok: false, message: `인승은 ${LISTING_RANGES.seats.min}~${LISTING_RANGES.seats.max}명 사이로 입력해주세요.` };
    }

    // options: 쉼표 구분 → 공백 제거 → 빈 항목 제외한 배열
    const options = form.options
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    return {
      ok: true,
      payload: {
        manufacturer: form.manufacturer,
        model: form.model.trim(),
        body_type: form.body_type,
        year, // 정수
        price, // 원(정수)
        mileage, // km(정수)
        color: form.color,
        fuel: form.fuel,
        transmission: form.transmission,
        displacement, // cc(정수)
        seats, // 정수
        region: form.region,
        accident_free: form.accident_free,
        options, // text[]
        description: form.description.trim() || null,
        status: LISTING_STATUS.ON_SALE, // 즉시 노출(기본값과 동일하나 의도 명시)
      },
    };
  }

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    // ⚠️ 중복 제출 차단은 **ref로** 한다(tech-debt #61). `loading` 상태는 다음 렌더에야 반영되므로,
    //    같은 틱에 들어온 두 번째 클릭은 아직 false를 보고 통과한다 — 실측(2026-07-19)에서 동기
    //    연속 클릭 시 PATCH가 각각 두 번씩 나갔다. ref는 렌더를 기다리지 않아 즉시 닫힌다.
    //    `loading` 상태는 그대로 둔다 — 그건 버튼 문구·스피너용이지 빗장이 아니다.
    if (submittingRef.current) return;
    submittingRef.current = true;
    setError(null);
    setSuccess(null);

    const built = validateAndBuild();
    if (!built.ok) {
      setError(built.message);
      submittingRef.current = false; // 빗장을 반드시 되돌린다 — 안 그러면 폼이 영영 제출 불가가 된다.
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();

      // 현재 로그인 사용자 확인 → seller_id 명시(위조는 RLS with check가 막지만 명시가 정상 경로).
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) {
        setError('로그인이 필요합니다. 다시 로그인 후 시도해주세요.');
        return;
      }

      if (isEditMode) {
        // ── 수정(UPDATE) ──────────────────────────────────────────────
        if (!activeListingId) {
          setError('수정할 매물 정보가 올바르지 않습니다. 목록에서 다시 시도해주세요.');
          return;
        }
        // status·seller_id는 보내지 않는다(구매완료 2-4 침범 금지·소유권 위조 금지). created_at은 트리거가 불변 보장.
        const { status: _status, ...updatePayload } = built.payload;
        void _status;

        // .select()로 반환 행을 받아 "몇 행이 바뀌었나"를 본다.
        //   RLS(listings_update_own)는 타인 매물 UPDATE를 에러가 아니라 0행으로 막는다 → 0행이면 권한 거부로 안내(AC4).
        const { data: updated, error: updateError } = await supabase
          .from('listings')
          .update(updatePayload)
          .eq('id', activeListingId)
          .select('id');

        if (updateError) {
          console.error('[sell] listings update 실패:', updateError);
          setError(toKoreanError(updateError, 'edit'));
          return;
        }
        if (!updated || updated.length === 0) {
          // RLS로 막혀 0행 — 본인 매물이 아니거나 이미 삭제됨.
          setError('본인 매물만 수정할 수 있습니다. (매물을 찾을 수 없거나 접근 권한이 없습니다.)');
          return;
        }

        // 사진 반영(추가·삭제·순서=대표). 실패해도 매물 수정 자체는 이미 성공이다(AC3).
        const photoResult = await syncListingPhotos(user.id, activeListingId, photos, initialPhotos);
        setPhotos(photoResult.photos);
        if (photoResult.failedCount > 0 || photoResult.warnings.length > 0) {
          // failedCount(저장 자체가 안 된 사진) + warnings(저장은 됐지만 순서·대표 등 뒷정리가
          // 어긋난 것) — 둘 다 "성공"이라고만 말하면 화면과 DB가 갈린 걸 사용자가 모르게 된다.
          const reasons = [
            ...(photoResult.failedCount > 0 ? [`사진 ${photoResult.failedCount}장은 실패했어요`] : []),
            ...photoResult.warnings,
          ];
          setError(`매물 정보는 저장했지만 ${reasons.join(' · ')}. 아래에서 다시 시도할 수 있어요.`);
          return; // 화면에 남겨 재시도할 수 있게 한다(이동하면 실패한 사진이 사라진다).
        }

        // 성공 → 관리 목록(/sell)으로 이동 + 갱신해 반영 확인.
        router.push('/sell');
        router.refresh();
        return;
      }

      // ── 등록(INSERT) — 2-2 동작 그대로(회귀 금지) ────────────────────
      // .select('id').single() 추가: 사진 저장 경로가 {user_id}/{listing_id}/…라
      // 방금 만든 매물의 id를 받아야 사진을 올릴 수 있다(AC5 — 스테이징 경로 없음).
      const { data: created, error: insertError } = await supabase
        .from('listings')
        .insert({ ...built.payload, seller_id: user.id })
        .select('id')
        .single();

      if (insertError || !created) {
        // 원본 에러·코드는 콘솔에만(디버깅), 사용자에겐 한국어.
        console.error('[sell] listings insert 실패:', insertError);
        setError(toKoreanError(insertError ?? { message: 'insert 결과 없음' }, 'create'));
        return;
      }

      // 매물은 이미 등록됐다 — 여기서부터 실패해도 등록을 되돌리지 않는다(AC3).
      const photoResult = await syncListingPhotos(user.id, created.id, photos, []);

      if (photoResult.failedCount > 0 || photoResult.warnings.length > 0) {
        // 매물 INSERT는 이미 성공했다 — 이 시점부터 재제출은 "수정"이 사실에 맞다. edit 모드로
        // 전환해 재제출이 listings를 다시 INSERT(=매물 중복 등록)하지 않고, 기존 UPDATE 경로
        // (사진 재시도 포함)를 그대로 타게 한다(F13, 코드리뷰 2026-07-19).
        setActiveListingId(created.id);
        setIsEditMode(true);
        // 매물은 살리고 사진만 남겨 재시도하게 한다 — "무엇이 됐고 무엇이 안 됐는지"가 분명해야 한다.
        setPhotos(photoResult.photos);
        const reasons = [
          ...(photoResult.failedCount > 0 ? [`사진 ${photoResult.failedCount}장 실패`] : []),
          ...photoResult.warnings,
        ];
        setSuccess(
          `매물이 등록되었습니다. (사진 ${photoResult.savedCount}장 저장${reasons.length > 0 ? `, ${reasons.join(' · ')}` : ''})`,
        );
        // 화면에 실제로 있는 건 [재시도] 버튼과 이 폼 자체다 — 안내 문구가 없는 화면(수정 화면)을
        // 가리키면 안 된다(코드리뷰 2026-07-19, 전엔 "매물 수정 화면에서 다시 시도"라 적혀 있었다).
        setError('사진 처리 중 일부가 실패했어요. 아래에서 다시 시도한 뒤 다시 저장해주세요.');
        router.refresh();
        return;
      }

      // 성공 → 폼 초기화 + 본인 매물 섹션(서버 컴포넌트) 갱신으로 "즉시 노출" 반영(FR7).
      // objectURL은 언마운트 시에만 자동 회수된다(PhotoUploader) — setPhotos([])는 언마운트가
      // 아니라 목록만 비우므로, 여기서 먼저 회수하지 않으면 새 파일 blob이 탭을 닫을 때까지
      // 메모리에 남는다(코드리뷰 2026-07-19).
      for (const p of photoResult.photos) {
        if (p.file && p.previewUrl) URL.revokeObjectURL(p.previewUrl);
      }
      setForm(INITIAL);
      setPhotos([]);
      setSuccess(
        photoResult.savedCount > 0
          ? `매물이 등록되었습니다. (사진 ${photoResult.savedCount}장) 아래 목록에 바로 노출됩니다.`
          : '매물이 등록되었습니다. 아래 목록에 바로 노출됩니다.',
      );
      router.refresh();
    } catch (err) {
      // 원본 에러는 콘솔에만(디버깅), 사용자에겐 한국어 일반 안내(원본 메시지 노출 금지 — 스토리 §AC4 규칙).
      console.error(`[sell] listings ${isEditMode ? 'update' : 'insert'} 예외:`, err);
      setError('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setLoading(false);
      submittingRef.current = false;
    }
  }

  const inputCls =
    'rounded border border-zinc-300 px-3 py-2 dark:border-zinc-700 dark:bg-zinc-900';

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {/* 제조사 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">제조사</span>
          <select
            value={form.manufacturer}
            onChange={(e) => update('manufacturer', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.manufacturer.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        {/* 모델 (자유 입력) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">모델</span>
          <input
            type="text"
            value={form.model}
            onChange={(e) => update('model', e.target.value)}
            placeholder="예: 아반떼 CN7"
            className={inputCls}
          />
        </label>

        {/* 차종 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">차종</span>
          <select
            value={form.body_type}
            onChange={(e) => update('body_type', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.body_type.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        {/* 연식 */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">연식 (년)</span>
          <input
            type="number"
            value={form.year}
            onChange={(e) => update('year', e.target.value)}
            min={LISTING_RANGES.year.min}
            max={LISTING_RANGES.year.max}
            placeholder="예: 2021"
            className={inputCls}
          />
        </label>

        {/* 가격 (원) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">가격 ({UNITS.price})</span>
          <input
            type="number"
            value={form.price}
            onChange={(e) => update('price', e.target.value)}
            min={0}
            placeholder="예: 29800000"
            className={inputCls}
          />
        </label>

        {/* 주행거리 (km) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">주행거리 ({UNITS.mileage})</span>
          <input
            type="number"
            value={form.mileage}
            onChange={(e) => update('mileage', e.target.value)}
            min={0}
            placeholder="예: 103000"
            className={inputCls}
          />
        </label>

        {/* 색상 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">색상</span>
          <select
            value={form.color}
            onChange={(e) => update('color', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.color.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        {/* 연료 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">연료</span>
          <select
            value={form.fuel}
            onChange={(e) => update('fuel', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.fuel.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        {/* 변속기 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">변속기</span>
          <select
            value={form.transmission}
            onChange={(e) => update('transmission', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.transmission.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>

        {/* 배기량 (cc) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">배기량 ({UNITS.displacement})</span>
          <input
            type="number"
            value={form.displacement}
            onChange={(e) => update('displacement', e.target.value)}
            min={0}
            placeholder="예: 1598 (전기차는 0)"
            className={inputCls}
          />
        </label>

        {/* 인승 */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">인승 (명)</span>
          <input
            type="number"
            value={form.seats}
            onChange={(e) => update('seats', e.target.value)}
            min={LISTING_RANGES.seats.min}
            max={LISTING_RANGES.seats.max}
            placeholder="예: 5"
            className={inputCls}
          />
        </label>

        {/* 지역 (드롭다운) */}
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">지역</span>
          <select
            value={form.region}
            onChange={(e) => update('region', e.target.value)}
            className={inputCls}
          >
            <option value="">선택</option>
            {LISTING_OPTIONS.region.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        </label>
      </div>

      {/* 무사고 여부 */}
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={form.accident_free}
          onChange={(e) => update('accident_free', e.target.checked)}
        />
        <span className="text-sm font-medium">무사고 차량</span>
      </label>

      {/* 옵션 (쉼표 구분, 선택) */}
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium">옵션 (쉼표로 구분, 선택)</span>
        <input
          type="text"
          value={form.options}
          onChange={(e) => update('options', e.target.value)}
          placeholder="예: 선루프, 후방카메라, 내비게이션"
          className={inputCls}
        />
      </label>

      {/* 설명 (선택) */}
      <label className="flex flex-col gap-1">
        <span className="text-sm font-medium">설명 (선택)</span>
        <textarea
          value={form.description}
          onChange={(e) => update('description', e.target.value)}
          rows={3}
          placeholder="차량 상태·이력 등을 자유롭게 적어주세요."
          className={inputCls}
        />
      </label>

      {/* 사진 (선택) — 대표는 순서 0번이다(AC1). */}
      <PhotoUploader items={photos} onChange={setPhotos} disabled={loading} />

      {error && (
        <p role="alert" className="rounded bg-red-50 px-3 py-2 text-sm text-red-700 dark:bg-red-950 dark:text-red-300">
          {error}
        </p>
      )}
      {success && (
        <p role="status" className="rounded bg-green-50 px-3 py-2 text-sm text-green-700 dark:bg-green-950 dark:text-green-300">
          {success}
        </p>
      )}

      <div className="flex items-center gap-3">
        <Button
          type="submit"
          variant="primary"
          loading={loading}
          loadingText={isEditMode ? '저장 중…' : '등록 중…'}
        >
          {isEditMode ? '수정 저장' : '매물 등록'}
        </Button>
        {/* 수정 모드에서만 취소(목록으로 돌아가기) 제공. 등록 모드는 단독 버튼.
            Link가 아니라 button인 이유: App Router에는 Link 이동을 가로채는 API가 없어서
            Link로 두면 작성 중인 내용이 경고 없이 사라진다(AC7). 여기서만이라도 직접 막는다. */}
        {isEditMode && (
          <Button variant="secondary" onClick={() => attemptLeave('/sell')} disabled={loading}>
            취소
          </Button>
        )}
      </div>

      {/* 이탈 확인 (AC7) — 새 모달 프리미티브를 만들지 않고 기존 FocusTrap을 재사용한다. */}
      {leaveTo && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <FocusTrap
            open
            onClose={() => setLeaveTo(null)}
            role="dialog"
            aria-modal="true"
            aria-labelledby="leave-guard-title"
            className="w-full max-w-sm rounded bg-white p-5 shadow-lg dark:bg-zinc-900"
          >
            <p id="leave-guard-title" className="text-sm">
              저장하지 않고 나가시겠어요? 작성한 내용이 사라져요.
            </p>
            <div className="mt-4 flex items-center justify-end gap-2">
              <Button variant="secondary" onClick={() => setLeaveTo(null)}>
                계속 작성
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  const href = leaveTo;
                  setLeaveTo(null);
                  router.push(href);
                }}
              >
                나가기
              </Button>
            </div>
          </FocusTrap>
        </div>
      )}
    </form>
  );
}
