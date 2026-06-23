---
name: auto-epic
description: '하나의 에픽을 BMad 공식 절차(create-story→dev-story→code-review)로 스토리마다 서브에이전트를 돌려 자동 개발하고, 에픽이 끝나면 로컬 Playwright + develop preview 배포(Vercel MCP)로 자체 검증한 뒤 사용자에게 넘긴다. 사용자가 /auto-epic [에픽번호]로 명시 호출할 때만 실행.'
disable-model-invocation: true
argument-hint: [에픽번호]
---

# auto-epic — 한 에픽 자동 개발 오케스트레이터

당신(이 스킬을 실행하는 메인 세션)은 **오케스트레이터(orchestrator)** 다. 직접 코드를 짜지 말고,
스토리마다 서브에이전트를 띄워 BMad 공식 스킬을 돌리고, 그 결과를 조율·검증·보고한다.

## 핵심 원칙 (절대 어기지 말 것)

1. **범위 = 정확히 한 에픽.** 대상 에픽의 모든 스토리가 끝나면 **반드시 멈춘다.** 다음 에픽으로 자동 진행 금지.
2. **에픽이 끝나면 사용자가 최종 검증한다.** 당신의 자체 테스트는 사용자 검증을 대체하지 않는다.
3. **`main` 브랜치 push·병합 금지.** 이 작업에 한해 `develop` push만 허용된다. `main` 병합은 사용자가 명시 요청할 때만(이 스킬 범위 밖).
4. **얇은 조율자로 남아라.** 상태는 항상 디스크(`sprint-status.yaml`·스토리 파일)에서 다시 읽는다. 기억에만 의존하지 않는다.
5. **무인 진행 + 중대 사항만 사용자에게 보고**(아래 Halt 정책). 일상적 판단은 합리적 기본값으로 자율 진행.

## 실행 모드 안내

이 스킬은 Bash(git·dev 서버)·서브에이전트·MCP를 많이 쓰므로 **auto 권한 모드**에서 실행해야 끊김 없이 돈다.
시작 시 현재 모드가 plan/acceptEdits로 보이면, 사용자에게 *"shift+tab으로 auto 모드 전환 후 진행 권장"* 을 한 번 안내한다.

---

## 상수 (경로·ID)

- 스프린트 상태: `_bmad-output/implementation-artifacts/sprint-status.yaml`
- 에픽 정의: `_bmad-output/planning-artifacts/epics.md`
- 스토리 파일: `_bmad-output/implementation-artifacts/{story_key}.md`
- 웹 앱: `web/` (dev `npm run dev` → `http://localhost:3000`, 빌드 `npm run build`, 린트 `npm run lint`)
- 배포 브랜치: `develop` (push 허용) / `main` (금지)
- Vercel: project `prj_ilOPzABNV6jPP848AeTGMQOhpK5J`, team `team_HMqrwcpM05d59YDz98oYQ2U2`
  - (ID가 안 맞으면 `list_projects`/`list_teams`로 재확인)
- 커밋 컨벤션: `type(scope): 한국어 설명` + 마지막 줄 `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

---

## 0단계 — 진입 검증 (에픽 진입점에서만 동작)

1. 인자로 받은 에픽 번호를 `target_epic`으로 둔다. 인자가 없으면 `sprint-status.yaml`에서 status가 `backlog`인 **첫 에픽**을 `target_epic`으로 한다.
2. `sprint-status.yaml`을 전부 읽고 아래를 검사한다. **하나라도 어긋나면 진행하지 말고 사용자에게 사실과 함께 검증을 요청하고 멈춘다:**
   - `target_epic` **직전 에픽**이 `done`이 아니다.
   - `target_epic`의 스토리 중 이미 `in-progress`/`review`/`done`인 것이 있다 → **깨끗한 시작점이 아님**(에픽 중간 이어받기는 이 스킬 범위 밖).
   - 에픽/스토리 상태가 앞뒤로 모순된다.
3. 검증 통과 시: 안내 없이 **바로 1단계로 진행**한다. (이 스킬은 사용자 전용이라 시작 보고가 불필요하다. 정지는 Halt 정책 — 주요 의사결정·치명적 에러 시에만.)

---

## 1단계 — 스토리 루프 (순차)

`target_epic`의 스토리를 sprint-status 순서대로 **하나씩** 처리한다. 각 스토리는 **반드시 새 서브에이전트**로 시작한다(문맥 오염 방지).

### 1-A. 서브에이전트 A — create-story → dev-story

Agent 도구로 새 서브에이전트를 띄우고 아래 지시를 준다:

> 당신은 BMad 개발 서브에이전트다. **무인(자율)으로** 동작하라.
> 1. Skill 도구로 `bmad-create-story`를 실행해 다음 backlog 스토리의 명세 파일을 만든다(상태 backlog→ready-for-dev).
> 2. 이어서 Skill 도구로 `bmad-dev-story`를 실행해 그 스토리를 끝까지 구현한다(상태 ready-for-dev→in-progress→review). 프로젝트 지침(CLAUDE.md)대로 테스트까지 수행한다.
> 3. 작업이 끝나면 변경을 `type(scope): ...` 컨벤션으로 **git 커밋**한다(아래 Halt 정책 위배가 없을 때). **커밋 메시지에 `story_key`와 `(dev)` 표시를 넣어** 나중에 복원 지점을 찾기 쉽게 한다(예: `feat(2-2): 매물 등록 폼 (dev)`). `main`은 절대 건드리지 않는다.
> 4. **Halt 정책**(아래 2단계)을 따른다 — 일상 결정은 합리적 기본값으로 자율 진행하고, 중대 사항만 멈춰서 보고용 요약에 명확히 표기한다.
> 5. 반환: 처리한 `story_key`, 한 일 요약, 테스트 결과, 미해결/escalate 필요 항목, 최종 스토리 상태.

서브에이전트가 끝나면 닫힌다(새 문맥은 자동 종료).

### 1-B. 서브에이전트 B — code-review

**A가 escalate 없이 정상 종료(스토리 review 상태)** 했을 때만, 새 서브에이전트를 띄워 아래를 지시한다:

> 당신은 BMad 코드리뷰 서브에이전트다. **무인(자율)으로** 동작하라.
> 1. Skill 도구로 `bmad-code-review`를 방금 review 상태가 된 스토리에 실행한다.
> 2. 자체 리뷰 서브에이전트(여러 레이어)를 띄울 수 있으면 그대로 쓴다. **띄울 수 없으면(중첩 제한) 리뷰 레이어를 순차 인라인으로 수행**하고, 그 사실을 요약에 표기한다.
> 3. **[Patch] 지적은 자동 적용**해 스토리를 done까지 끌고 간다. **[Decision] 결정필요 지적은 자동으로 고르지 말고** 멈춰 요약에 그대로 담아 escalate한다.
> 4. **패치를 적용해 파일이 바뀌었으면 그 변경을 별도 git 커밋**한다(예: `fix(2-2): code-review 반영`). 바뀐 게 없으면 커밋 생략. → 스토리마다 "dev 커밋" + (있으면) "review 커밋"의 2개 복원 지점이 남는다.
> 5. 반환: 적용한 패치, escalate할 [Decision] 항목, 미해결 High/심각 지적 유무, 최종 스토리 상태(done/in-progress).

### 1-C. 진행 게이트

- B 결과에 **[Decision] 결정필요** 또는 **미해결 High/심각** 지적이 있으면 → **다음 스토리로 가지 말고** 사용자에게 그 항목을 보고하고 멈춘다(지시를 받으면 재개).
- 그 외(스토리 done) → 다음 스토리로.

### 1-D. 토대 스토리 — 무인 진행(자동 정지 없음)

- **첫(토대) 스토리라고 해서 자동으로 멈추지 않는다.** 정지 여부는 오직 Halt 정책(1-C·2단계)을 따른다 — **주요 의사결정([Decision]·모호한 AC 등)이나 치명적 에러(키 누락·연속 실패·미해결 High/심각)일 때만** 멈춘다.
- 다만 토대가 흔들리면 뒤 스토리가 다 무너지므로, 토대 스토리에서는 **판단 기준을 더 엄격히** 적용한다(애매하면 자율 통과보다 escalate 쪽으로). 문제 없으면 그대로 다음 스토리로 무인 진행한다.

### 1-E. 복원 지점(롤백) 설계

위 커밋 규칙 덕분에 **각 스토리(그리고 dev/review 단계)가 git 복원 지점**이 된다. 에픽이 끝난 뒤 특정 스토리 시점으로 되돌릴 수 있다:
- 어디로 되돌릴지 찾기: `git log --oneline` 에서 `(dev)`/`code-review 반영` 메시지로 스토리 커밋을 식별.
- **안전한 되돌리기(권장)**: `git revert <커밋>` — 해당 변경만 취소하는 새 커밋을 만든다. 이력을 보존하고, 이미 push된 develop에도 충돌 없이 쓸 수 있다.
- **강한 되돌리기**: `git reset --hard <커밋>` — 그 시점 이후 커밋을 버린다. 이미 push했다면 force-push가 필요하므로 사용자 확인 후에만.
- 보고 시, 사용자가 롤백을 원할 수 있으니 **스토리별 커밋 해시 목록**을 최종 요약에 함께 제공한다.

루프가 끝나면(모든 스토리 done) 3단계로 간다.

---

## 2단계 — 자율 Halt 정책 (서브에이전트에 주입)

서브에이전트는 BMad 스킬의 "사람에게 묻는 정지"를 만나면 다음처럼 처리한다:

- **자율 통과(기본값으로 진행)**: 다음 스토리 자동 선택, dev 진행, 일상적 선택 등.
- **멈추고 escalate(오케스트레이터→사용자 보고)**: 아래만 해당.
  - API 키/환경변수/설정 파일 누락
  - 구현 3회 연속 실패
  - AC(인수 조건)가 모호해 임의 판단이 위험
  - code-review의 **[Decision] 결정필요** 항목
- **code-review [Patch]** 지적은 자동 적용한다(멈추지 않음).

---

## 3단계 — 에픽 종료 자체 테스트 (사용자에게 넘기기 전)

모든 스토리가 done이 된 뒤, "사용자가 직접 테스트하세요"라고 말하기 **전에** 다음을 수행한다:

1. **로컬 자체 테스트(기능 검증의 핵심)**:
   - `web`에서 dev 서버를 백그라운드로 띄운다(`npm run dev`, `:3000`), health check 후
   - **Playwright MCP**로 이번 에픽이 추가/변경한 사용자 흐름을 실제 브라우저로 클릭·입력하며 E2E 점검한다.
   - 끝나면 dev 서버 프로세스를 정리한다.
   - 로컬이 실패하면 **여기서 멈추고 사실대로 보고**(아래 4·배포로 넘어가지 않음).
2. **develop preview 배포 검증(방식 c — URL 클릭 대신 MCP로 상태·로그만)**:
   - 변경을 `develop`에 commit & **push**(이 작업에 한해 허용).
   - Vercel MCP로 **해당 커밋 SHA의 배포**를 찾는다(`list_deployments`/`get_deployment`). preview 배포는 `target: null`이다.
   - `state`가 `READY`인지 확인하고, `get_deployment_build_logs`로 **빌드 에러가 없는지** 확인한다.
   - (보조) 페이지를 몇 개 접속시킨 뒤 `get_runtime_logs`(environment=preview)로 런타임 에러를 본다 — 트래픽이 없으면 로그가 비어 있을 수 있음(정상).
   - 배포가 `ERROR`거나 로그에 에러가 있으면 보고한다.

> **배포 링크 브라우저 E2E가 막힐 때(preview/production 공통):** Playwright 게스트모드에서 Vercel 보호벽 로그인이 안 돼 로컬로만 테스트하고 끝내지 말 것. 먼저 **① 이미 로그인된 크롬 세션으로 접속**을 시도하고, 안 되면 **② `get_access_to_vercel_url`로 그 배포의 share 링크(`?_vercel_share=<token>`, 23h 유효)를 발급**해 게스트모드에서 접속한다 — 공유 URL 한 번이면 인증 쿠키가 세팅돼 로컬과 동일하게 E2E 가능. (자세히는 [[preview-e2e-via-vercel-share-link]])

---

## 4단계 — 종료 + 인수인계

- 결과 요약을 사용자에게 보고한다: 스토리별 done 여부, 자체 테스트 결과(로컬 E2E + 배포/로그), escalate된 항목.
- 프로젝트 지침(CLAUDE.md "Epic 종료 시 직접 해야 할 일")대로 **사용자 직접 처리 항목**(키 입력·콘솔 설정·결제 등)을 모아 고지한다.
- **여기서 멈춘다.** 다음 에픽 자동 시작 금지. `main` 병합은 사용자가 직접 테스트 후 명시 요청할 때만.
