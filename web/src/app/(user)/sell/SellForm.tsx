'use client';

// 매물 등록 폼 (FR5·FR7) — 15필드 입력 → listings INSERT → status=on_sale로 즉시 노출.
//
// 설계(signup/page.tsx 패턴 재사용):
//   · noValidate + 직접 검증 → 한국어 오류 메시지(네이티브 영문 검증 끔).
//   · loading으로 중복 제출 차단.
//   · 고정 목록 6필드는 <select> 드롭다운(LISTING_OPTIONS 단일출처) → 목록 밖 값 선택 불가(AC2·AC5).
//   · seller_id는 현재 로그인 user.id로 명시(INSERT RLS with check가 위조 차단 — 2-1).
//   · 단위(원·km·cc·년·명)는 입력란 라벨에 표기, 저장은 정수(AC3).
//   · DB CHECK/RLS 위반은 한국어로 변환해 노출(원본·코드는 콘솔에만).
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { createClient } from '@/lib/supabase/client';
import { LISTING_OPTIONS, LISTING_RANGES, LISTING_STATUS, UNITS } from '@/lib/constants';

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

// Postgres/Supabase 에러를 사용자용 한국어 메시지로 변환(원본 메시지·코드는 화면에 직접 노출하지 않음).
//   23514 = check_violation(목록 밖 값·범위 위반), 42501 = insufficient_privilege(RLS 거부).
function toKoreanError(err: { message: string; code?: string }): string {
  const code = err.code ?? '';
  if (code === '23514') {
    return '입력값이 허용 목록/범위를 벗어났습니다. 드롭다운 항목과 숫자 범위를 확인해주세요.';
  }
  if (code === '42501') {
    return '본인 명의로만 매물을 등록할 수 있습니다. 다시 로그인 후 시도해주세요.';
  }
  return '매물 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.';
}

export default function SellForm() {
  const router = useRouter();
  const [form, setForm] = useState<FormState>(INITIAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

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
    if (loading) return; // 중복 제출 차단
    setError(null);
    setSuccess(null);

    const built = validateAndBuild();
    if (!built.ok) {
      setError(built.message);
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

      const { error: insertError } = await supabase
        .from('listings')
        .insert({ ...built.payload, seller_id: user.id });

      if (insertError) {
        // 원본 에러·코드는 콘솔에만(디버깅), 사용자에겐 한국어.
        console.error('[sell] listings insert 실패:', insertError);
        setError(toKoreanError(insertError));
        return;
      }

      // 성공 → 폼 초기화 + 본인 매물 섹션(서버 컴포넌트) 갱신으로 "즉시 노출" 반영(FR7).
      setForm(INITIAL);
      setSuccess('매물이 등록되었습니다. 아래 목록에 바로 노출됩니다.');
      router.refresh();
    } catch (err) {
      setError(`네트워크 오류가 발생했습니다: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
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

      <button
        type="submit"
        disabled={loading}
        className="rounded bg-zinc-900 px-4 py-2 font-medium text-white disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900"
      >
        {loading ? '등록 중…' : '매물 등록'}
      </button>
    </form>
  );
}
