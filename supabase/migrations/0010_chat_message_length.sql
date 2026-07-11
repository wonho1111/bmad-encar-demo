-- 0010_chat_message_length.sql — 채팅 본문 최대 길이 CHECK (기술부채 #8)
--
-- 왜: chat_messages.body 가 text(무제한)라 초대용량 붙여넣기가 그대로 INSERT되면
--   행·폴링 페이로드가 비대해진다. 상한을 DB로 못박아(project-context 규칙 8) 클라 우회도 차단한다.
--   값 2000자 = docs/conventions.md §7 · web/src/lib/constants.ts 의 CHAT.MESSAGE_MAX_LENGTH 와 일치.
--   (기존 빈-본문 CHECK length(btrim(body))>0 는 0003_chat.sql 에 있음 — 여기서는 상한만 추가.)
--
-- 안전: 도입 시점 기존 chat_messages 최대 길이 28자(<< 2000)라 기존 행 위반 없음(추가·역방향 안전).

alter table public.chat_messages
  add constraint chat_messages_body_max_len
  check (char_length(body) <= 2000);
