// Playwright(E2E) 설정 — 이 레포 최초의 실브라우저 자동화 층(spec-11-5, #86/#160/#127의 트리거 해소).
//
// 왜 여기 있나: web/e2e/*.spec.ts가 여기 정의된 3개 뷰포트 프로젝트로 각각 돈다.
// 뷰포트 매트릭스는 project-context 규칙13(D5)·이전 실측(9.6/9.7/#84)이 이미 쓴 값과 동일하게
// 고정한다(연속성) — 데스크톱 1280×800 · 태블릿 800×1024 · 모바일 390×844.
//
// webServer: `next build && next start`(운영 빌드)를 띄운다 — 처음엔 `next dev`로 시도했으나
// 실측(2026-07-28): 여러 스펙 파일이 서로 다른 라우트를 동시에 처음 여는 순간, dev 모드의 온디맨드
// 컴파일이 요청마다 수 초씩 걸려 병렬 워커가 한꺼번에 몰리자 30초 테스트 타임아웃을 넘겨 무더기로
// 실패했다(개별 스펙 파일만 돌리면 전부 green, 전체를 한 번에 돌리면 dev 컴파일 경합으로 red —
// 코드 결함이 아니라 인프라 병목임을 실측으로 구분했다, B4). 빌드 서버는 요청마다 재컴파일하지
// 않아 이 경합이 사라진다. Next.js가 `.env.local`을 빌드·서빙 양쪽에서 자체적으로 읽으므로
// (로컬 Supabase 스택을 가리킴 — scripts/use-env.sh가 복사해 둔 파일) 별도 env 전달이 필요 없다.
// 다만 이 설정 파일과 스펙 파일 자체(Node 프로세스, Next 서버가 아니라 Playwright 테스트 러너)도
// NEXT_PUBLIC_SUPABASE_URL 등을 읽어야 한다(예: 시드 매물 id를 REST로 직접 조회할 때) — 그래서
// 아래에서 같은 .env.local을 수동으로 한 번 더 파싱해 process.env에 채운다(dotenv 의존성 추가 없이
// 단순하게, A2).
import { defineConfig, devices } from '@playwright/test';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { PROJECT_NAMES } from './e2e/project-names';

function loadDotEnvLocal() {
  const file = path.resolve(__dirname, '.env.local');
  if (!existsSync(file)) {
    // 조용히 넘어가지 않는다(코드리뷰 patch) — 예전엔 여기서 그냥 return해, 이 파일이 없으면
    // 스펙들이 한참 뒤 NEXT_PUBLIC_SUPABASE_URL 미설정·로그인 실패 등 불투명한 타임아웃으로만
    // 죽었다. 무엇이 없고 어떻게 만드는지 바로 알려준다.
    throw new Error(
      `web/.env.local이 없습니다. E2E는 로컬 Supabase 스택을 가리키는 이 파일이 있어야 합니다. ` +
        `저장소 루트에서 \`bash scripts/use-env.sh local\`을 실행해 만드세요(로컬 스택이 안 떠 있으면 먼저 \`npx supabase start\`).`,
    );
  }
  for (const line of readFileSync(file, 'utf-8').split('\n')) {
    const trimmed = line.trim();
    if (trimmed === '' || trimmed.startsWith('#')) continue;
    const eq = trimmed.indexOf('=');
    if (eq === -1) continue;
    const key = trimmed.slice(0, eq).trim();
    let value = trimmed.slice(eq + 1).trim();
    // 실제 dotenv와 동일하게 값을 감싼 따옴표(단/쌍따옴표)를 벗긴다(코드리뷰 patch) — 이게 없으면
    // `KEY="value"` 형태가 리터럴 따옴표까지 포함한 문자열로 들어가 URL·키 값이 깨진다.
    if (
      (value.startsWith('"') && value.endsWith('"') && value.length >= 2) ||
      (value.startsWith("'") && value.endsWith("'") && value.length >= 2)
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = value;
  }
}
loadDotEnvLocal();

// 이 레포는 포트 3000이 종종 이미 점유돼 있다(코드리뷰 patch) — 하드코딩이면 그때마다 스위트
// 자체가 못 돈다. E2E_PORT로 오버라이드 가능하게 하고, baseURL·webServer 커맨드가 같은 값을 본다.
//
// E2E_PORT 값을 검증한다(코드리뷰 patch, P7) — `Number(process.env.E2E_PORT ?? 3000)`을 그대로
// 쓰면 빈 문자열은 `0`, 오타(`"abcd"`)는 `NaN`이 되어 `http://localhost:NaN`·`next start -p NaN`으로
// 조용히 새어나간다. 그것도 전체 빌드(수십 초)가 끝난 뒤에야 실패해 비용이 크다 — `.env.local`
// 누락 검사와 같은 fail-loud 스타일로, 빌드 전에 즉시 에러를 던진다.
const rawPort = process.env.E2E_PORT ?? '3000';
const PORT = Number(rawPort);
if (!Number.isInteger(PORT) || PORT < 1 || PORT > 65535) {
  throw new Error(
    `E2E_PORT 값이 올바르지 않습니다("${rawPort}") — 1~65535 사이의 정수여야 합니다. ` +
      `빈 문자열은 0, 숫자가 아닌 값은 NaN이 되어 http://localhost:NaN으로 새어나갑니다.`,
  );
}
const BASE_URL = `http://localhost:${PORT}`;

// 3개 뷰포트 프로젝트 — intent-contract "Always"가 못박은 정확한 값.
// 이름은 PROJECT_NAMES(코드리뷰 patch, ./e2e/project-names.ts)에서 가져온다 — 여기서 이름을
// 바꾸면 그 상수를 쓰는 스펙의 test.skip 가드도 같이 바뀌어, 이름이 어긋나 테스트가 조용히
// 전량 스킵되는 사고를 구조적으로 막는다.
const projects = [
  {
    name: PROJECT_NAMES.desktop,
    use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } },
  },
  {
    name: PROJECT_NAMES.tablet,
    use: { ...devices['Desktop Chrome'], viewport: { width: 800, height: 1024 } },
  },
  {
    name: PROJECT_NAMES.mobile,
    use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 } },
  },
];

// PROJECT_NAMES의 각 이름이 실제 projects 배열에도 있는지 로드 시점에 확인한다(코드리뷰 patch,
// P4) — project-names.ts는 "이름 문자열"만 config·스펙이 공유하게 해줄 뿐, 프로젝트 "존재"
// 자체까지 묶어주지는 않는다. 예를 들어 위 배열에서 항목 하나를 통째로 지워도 PROJECT_NAMES의
// 상수는 여전히 정의돼 있어, `image-fallback.spec.ts`·`nav-interactions.spec.ts`의
// `test.skip(testInfo.project.name !== PROJECT_NAMES.desktop, ...)` 조건이 항상 참이 되고 그
// 7개 테스트가 exit 0인 채로 조용히 전량 스킵된다(B9 — 규칙은 어길 수 없는 자리에 박는다).
// ⚠️ 이 검사가 못 닫는 축: `npx playwright test --project=<name>`처럼 사용자가 명시적으로 한
// 프로젝트만 골라 실행하면, 다른 프로젝트를 대상으로 한 스펙은 당연히 스킵된다 — 그건 사용자가
// 의도한 부분집합 실행이지 이름 어긋남(drift)이 아니다. 여기서 막는 건 "config 자체에서
// 프로젝트가 통째로 사라졌는데 아무도 모르는" 경우뿐이다.
const configuredProjectNames = new Set(projects.map((p) => p.name));
for (const name of Object.values(PROJECT_NAMES)) {
  if (!configuredProjectNames.has(name)) {
    throw new Error(
      `playwright.config.ts의 projects 배열에 PROJECT_NAMES 항목 "${name}"이 없습니다 — 이 이름을 ` +
        `쓰는 test.skip 가드가 항상 참이 되어 관련 테스트가 조용히 전량 스킵됩니다.`,
    );
  }
}

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  fullyParallel: true,
  // 워커를 4로 고정한다(2026-07-28, 대장 #182로 스펙 4개가 합류하며 스위트가 2배가 된 뒤 실측).
  //
  // 왜: 기본값(코어의 50% = 이 머신에선 8)으로 돌리면 **매 실행마다 1~2건이 무작위로 red**가
  // 났다. 실패 지점이 실행마다 옮겨 다녔고(image-fallback → core-flows C7 → nav-and-hero B8)
  // 그중엔 이번에 손대지 않은 기존 스펙도 섞여 있었다. 원인을 추측하지 않고 인증 컨테이너
  // 로그를 직접 읽어 확정했다:
  //   504 /token · /user → "failed to connect to host=supabase_db_bmad-encar-demo:
  //                         hostname resolving error (lookup ... on 127.0.0.11:53: i/o timeout)"
  // 한 번 실행에 GoTrue `/user` 요청이 **5,231건** 나가는데(페이지 이동마다 서버가 세션을
  // 확인한다), 8워커가 동시에 때리면 **도커 내부 DNS(127.0.0.11)가 포화**돼 인증이 간헐적으로
  // 504를 뱉는다 → 앱은 "로그인 중 오류가 발생했습니다"를 띄우고 그 테스트가 죽는다.
  // 제품 결함도 테스트 로직 결함도 아니고 **로컬 스택의 한계**다.
  //
  // 4로 낮추자 2회 연속 `53 passed / 0 failed`였고, 오히려 **더 빨랐다**(1.3분 vs 1.8분 —
  // 8워커에선 메모리·DNS 경합으로 서로를 기다린다. 이 머신은 16코어지만 RAM이 7.7GB다).
  // ⚠️ 이 값은 "이 머신에서 재서 얻은 값"이지 이론값이 아니다. 다른 환경(특히 CI, #168)에 이
  // 스위트를 올릴 땐 거기서 다시 재고 이 주석을 갱신할 것 — 숫자만 옮기지 말 것.
  workers: 4,
  // 로컬 전용(#86 — CI엔 이 스펙을 안 배선한다, Never 항목). 재시도 없이 실패를 그대로 본다.
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
  },
  projects,
  webServer: {
    // -p로 PORT를 명시한다(코드리뷰 patch) — 안 그러면 next start가 기본 3000으로 뜨는데
    // PORT를 E2E_PORT로 바꿔도 baseURL만 바뀌고 서버는 여전히 3000이라 서로 어긋난다.
    command: `npm run build && npm run start -- -p ${PORT}`,
    url: BASE_URL,
    // 항상 새로 빌드·기동한다(코드리뷰 patch) — `!process.env.CI`로 기존 프로세스를 재사용하면,
    // 포트 3000에 떠 있는 것이 정말 "이 diff를 반영한 신선한 빌드"인지 검증하지 않는다. 이 스위트
    // 자체가 회귀 방지(#86)가 목적이라, 남아 있는 낡은 서버를 그대로 믿고 돌리면 그 목적이 무너진다.
    // 빌드 시간이 매번 들지만(수십 초), 정확성이 그 비용보다 우선한다.
    reuseExistingServer: false,
    // 빌드(수십 초) + 기동을 합친 예산. next dev보다 최초 1회 비용은 크지만 이후 요청은
    // 재컴파일 없이 즉시 응답해 병렬 워커 경합이 없다(위 주석 실측 근거).
    timeout: 180_000,
  },
});
