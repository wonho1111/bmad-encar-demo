"""챗봇 답변 정합성 평가(human-aligned LLM judge, Dave Ebbelaar 방식) 파이프라인.

queries.json(신규 100입력) → run_batch.py(에이전트 응답 수집) → judge.py(강한 LLM 채점) →
make_sheet.py(사람 채점용 엑셀, Agreement% 계산) 순서로 실행한다. 산출물은 이 패키지 밖
`$OUT`(.logs/chatbot_eval/<날짜>/, git-ignored)에 쌓인다 — 코드만 이 패키지에 커밋된다.
"""
