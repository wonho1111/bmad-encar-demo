// splitInlineNumberedList 단위테스트(실측 결함 F3, 2026-08-31) — DOM 없이 순수 함수만
// 검증한다(vitest.config.ts 방침: node 환경, 컴포넌트 렌더는 E2E 몫 — MarketDiagnosis.test.ts와
// 동일 관례).
import { describe, expect, it } from 'vitest';

import { splitInlineNumberedList } from './AnswerText';

describe('splitInlineNumberedList', () => {
  it('문장 중간에 이어붙은 번호 목록을 줄바꿈으로 분리한다', () => {
    const input = '적당한 매물 3건을 찾았어요. 1. 현대 아반떼는 연비가 좋아요. 2. 기아 쏘렌토는 공간이 넓어요.';
    expect(splitInlineNumberedList(input)).toBe(
      '적당한 매물 3건을 찾았어요.\n1. 현대 아반떼는 연비가 좋아요.\n2. 기아 쏘렌토는 공간이 넓어요.',
    );
  });

  it('이미 줄 맨 앞에 있는 번호(정상 개행)는 건드리지 않는다(무변경)', () => {
    const input = '아래 두 매물을 추천해요.\n1. 현대 아반떼\n2. 기아 쏘렌토';
    expect(splitInlineNumberedList(input)).toBe(input);
  });

  it('금액 표기("1,957만원")는 오탐으로 분리하지 않는다', () => {
    const input = '이 매물은 1,957만원으로 시세보다 저렴해요.';
    expect(splitInlineNumberedList(input)).toBe(input);
  });

  it('배기량 표기("3.3")는 오탐으로 분리하지 않는다', () => {
    const input = '이 매물은 배기량 3.3 가솔린 모델이에요.';
    expect(splitInlineNumberedList(input)).toBe(input);
  });

  it('소수점 뒤에 공백 없이 이어지는 숫자는 오탐으로 분리하지 않는다', () => {
    const input = '가격대는 대략 2.5천만원 수준이에요.';
    expect(splitInlineNumberedList(input)).toBe(input);
  });

  it('두 자리 번호도 분리한다', () => {
    const input = '많은 후보 중 10. 제네시스 G80이 눈에 띄어요.';
    expect(splitInlineNumberedList(input)).toBe('많은 후보 중\n10. 제네시스 G80이 눈에 띄어요.');
  });

  it('번호 뒤에 숫자가 오면(목록이 아니라 우연한 문장) 분리하지 않는다', () => {
    const input = '가격은 2. 5천만원 정도로 예상돼요';
    // "2. " 뒤가 숫자("5")라 "한글/영문으로 시작하는 목록 항목" 조건에 걸리지 않는다.
    expect(splitInlineNumberedList(input)).toBe(input);
  });
});
