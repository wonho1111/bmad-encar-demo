// 답변 텍스트 렌더 — 개행 보존 + 가벼운 번호 목록 처리(2026-08-31, 사용자 실측 결함 P3 수정).
//
// 문제: 답변이 개행 없는 벽처럼 이어졌다 — CSS(whitespace-pre-wrap)는 이미 \n을 살리지만,
// 에이전트가 애초에 \n을 넣지 않은 긴 문장을 그대로 냈다. 그래서 agent.py 프롬프트에 "2~3문장
// 단위로 문단을 나누고(빈 줄), 여러 매물을 다루면 번호 목록으로 써라"를 추가했고(B2), 이
// 컴포넌트는 그 결과(문단 사이 빈 줄 \n\n, "1. " 줄 앞머리)를 실제로 읽기 편하게 그린다.
//
// 마크다운 라이브러리를 추가하지 않는다(A2 단순함 우선) — 정규식 하나로 "숫자. " 시작 줄만
// 살짝 강조하는 최소 처리다.
const NUMBERED_LINE_RE = /^(\d{1,2})\.\s+(.*)$/;

// 2026-08-31 개정(실측 결함 F3): 프롬프트를 고쳐도 LLM이 가끔 개행 없이 "…적당해요. 2. 기아
// 쏘렌토는…"처럼 번호 목록을 한 문장에 이어붙인다 — whitespace-pre-wrap도 원래 없는 개행은
// 못 살리므로, 렌더 전 결정론 후처리로 그 지점만 줄바꿈으로 되살린다.
//
// 패턴: "비공백 문자 + 공백/탭 1개 + 1~2자리 숫자 + '. ' + 한글/영문"만 매칭한다 — 즉 문장이
// 이어지다가 갑자기 번호 항목이 시작되는 지점만 잡는다.
//   - 이미 줄 맨 앞(개행 직후)의 번호는 그대로 둔다: [ \t]만 보고 \n은 보지 않으므로, 앞이
//     개행이면 애초에 매칭 자체가 안 된다(무변경).
//   - 금액("1,957")·배기량("3.3")은 점 뒤에 공백이 없어 매칭되지 않는다(오탐 방지, 테스트로 고정).
const INLINE_NUMBERED_ITEM_RE = /(\S)[ \t](\d{1,2})\.[ \t]+(?=[가-힣A-Za-z])/g;

/** 문장 중간에 이어붙은 번호 목록(" 2. 기아 …")을 줄바꿈으로 분리한다. 순수 함수(단위테스트 대상). */
export function splitInlineNumberedList(text: string): string {
  return text.replace(INLINE_NUMBERED_ITEM_RE, (_match, before: string, num: string) => `${before}\n${num}. `);
}

export default function AnswerText({ text, className }: { text: string; className?: string }) {
  const normalized = splitInlineNumberedList(text);
  const paragraphs = normalized.split(/\n{2,}/); // 빈 줄 = 문단 구분
  const lineClass = ['whitespace-pre-wrap', className].filter(Boolean).join(' ');

  return (
    <>
      {paragraphs.map((para, pi) => (
        <div key={pi} className={pi > 0 ? 'mt-2' : undefined}>
          {para.split('\n').map((line, li) => {
            const m = line.match(NUMBERED_LINE_RE);
            return (
              <p key={li} className={lineClass}>
                {m ? (
                  <>
                    <span className="font-semibold">{m[1]}.</span> {m[2]}
                  </>
                ) : (
                  line
                )}
              </p>
            );
          })}
        </div>
      ))}
    </>
  );
}
