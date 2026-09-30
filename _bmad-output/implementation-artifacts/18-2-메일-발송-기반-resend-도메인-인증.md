# Story 18.2: 메일 발송 기반 (Resend + 도메인 인증)

Status: in-progress

## Story
As a 운영자, I want Auth 메일(가입 인증·비밀번호 재설정)이 내 도메인 이름으로 인증되어 나가게 하고 싶다, so that 기본 메일의 발송 제한 없이 받은편지함에 도착한다.

## Acceptance Criteria
1. 발신 도메인 `chajang.devmerc.dev`가 Resend에서 Verified(DKIM·SPF). 같은 도메인의 포트폴리오 SES 기록(`mail.`·루트 DKIM·`_dmarc`)은 건드리지 않는다.
2. 로컬·운영 Supabase Auth 메일이 Resend SMTP로 나가고 보낸 사람이 `차장님 <no-reply@chajang.devmerc.dev>`다. 비밀값은 저장소 밖.
3. 지메일 원본에서 SPF·DKIM·DMARC PASS를 확인한다.
4. 네이버·지메일 도착 위치(받은편지함/스팸함)를 실측해 기록한다. 스팸함이면 원인 추적 과정을 남긴다.

## 실측 (2026-09-30)
- AC1: Resend 요구 기록 3개 — TXT `resend._domainkey.chajang`, CNAME `rsend.chajang`→`rsend-apne1.forge.rmta.net`, CNAME `send.chajang`→`send.forge.rmta.net`(둘 다 DNS only). Cloudflare 수동 입력, 공개 DNS 조회로 전파 확인, Resend Verified. `send.chajang`의 CNAME 대상에 MX·SPF가 들어 있다(조회 확인).
- AC2 로컬: config.toml `[auth.email.smtp]`(커밋 6c88c5c). recover 요청 → 로컬 메일함 0통, 네이버 실수신.
- AC2 운영: 사용자가 대시보드 SMTP Settings 입력(운영용 키 별도). 대시보드에서 recovery·invite 발송 → 보낸 사람 `no-reply@chajang.devmerc.dev` 확인.
- AC3: 지메일 원본 — SPF PASS(23.251.234.57), DKIM PASS(chajang.devmerc.dev, selector resend) + amazonses.com 서명 1개 더, DMARC PASS(header.from=devmerc.dev, p=NONE). 실제 발송 서버는 `smtp-out.ap-northeast-1.amazonses.com` — Resend는 Amazon SES 위에서 돈다.
- AC4:
  | 발송 | 본문·링크 | 네이버 | 지메일 |
  | --- | --- | --- | --- |
  | 로컬 Supabase 기본 양식 | 영어, `http://127.0.0.1:55321/...` | 받은메일함 | 스팸함 |
  | Resend API 직접 | 한국어, `https://bmad-encar-demo.vercel.app/login` | — | **받은편지함** |
  | 운영 Supabase 기본 양식 | 영어, `https://…supabase.co/…&redirect_to=http://localhost:3000` | 받은메일함 | 스팸함 |
  - 결론(확정된 것만): 같은 도메인·같은 발신자로 받은편지함에 들어간 메일이 있으므로 **도메인 평판 문제는 아니다.** 인증 3종 통과와 받은편지함 도착은 별개다.
  - 미확정: 스팸 원인이 영어 기본 양식인지, 링크 안의 localhost인지, 둘 다인지 — 세 번의 발송에서 두 요소가 함께 바뀌어 분리되지 않았다. 18.3·18.4에서 한국어 양식 + Site URL 수정 후 다시 잰다.
- **발견한 운영 설정 오류**: 운영 Supabase의 Site URL이 `http://localhost:3000`이다(메일 링크의 redirect_to로 확인, 링크를 누르면 localhost가 열림). 카카오 로그인은 코드가 redirectTo를 직접 넘겨서 영향이 없었다. → Site URL을 `https://bmad-encar-demo.vercel.app`로 수정 필요(사용자, 대시보드).

## 남은 것
- [ ] 운영 Site URL 수정 후 메일 링크가 운영 사이트로 가는지 확인
- [ ] 테스트로 만든 운영 사용자(`onehoo314@gmail.com` 초대) 정리 여부 결정
- [ ] 실측 행 + `기능가이드/이메일_발송.md` Resend 절(freelance)
