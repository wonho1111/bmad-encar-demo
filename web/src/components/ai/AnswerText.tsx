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

export default function AnswerText({ text, className }: { text: string; className?: string }) {
  const paragraphs = text.split(/\n{2,}/); // 빈 줄 = 문단 구분
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
