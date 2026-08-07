// 채팅 실시간 구독 토픽 계약 교차 검사 (Story 12.3 코드리뷰 patch, CLAUDE.md B9 —
// "주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가:
//   `chat:room:{room_id}`라는 토픽 문자열은 **서로 다른 언어로 쓰인 네 벌의 리터럴**로 존재한다 —
//   ① `supabase/migrations/0023_chat_realtime_broadcast.sql`의 트리거(방송을 내보내는 쪽)와
//      RLS 정책(구독을 인가하는 쪽), ② `ChatRoomMessages.tsx`의 `roomTopic()`(구독하는 쪽),
//      ③ `api/tests/integration/test_chat_realtime_broadcast_real_db.py`의 `_TOPIC_PREFIX`(실DB로
//      방송을 검증하는 쪽), ④ `app/lib/features/chat/chat_repository.dart`의 `roomTopic()`
//      (Flutter 앱 구독, Epic 16 Story 16.4). 한쪽만 바꿔도 컴파일·lint·기존 테스트가 전부
//      통과하는데, 실제로는 "방송은 계속 나가는데 아무도 못 듣는" 무음 실패가 된다.
//      docs/conventions.md §12가 이 위험을 글로 적어뒀지만 글은 실행되지 않는다 — 이 파일이
//      그 자리를 대신한다.
//
// 이 검사가 **안 보는 것**:
//   · 실제 Realtime 서버가 그 토픽으로 방송을 내보내고 구독이 붙는지(런타임 동작) — 그건
//     `api/tests/integration/test_chat_realtime_broadcast_real_db.py`(실DB)와 Story 12.6/16.4의
//     수동 2-클라이언트 검증 몫이다. 여기서는 "네 벌의 문자열이 서로 같은가"만 정적으로 고정한다.
//   Dart `roomTopic()`이 실제로 `supabase.channel(...)` 호출부(`chat_room_screen.dart`의
//   `_defaultChatSubscribe`)에서 private 채널로 쓰이는지는 아래 별도 검사가 앵커해서 본다
//   (코드리뷰 patch 2 — 이전엔 함수 *정의*만 대조하고 배선은 안 봐서, 함수는 맞는데 호출부가
//   `roomTopic(roomId)`를 안 쓰거나 `private:true`가 빠져도 이 파일 전체가 green이었다).
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';

// 이 파일 = <repo>/web/src/app/(user)/chat/[roomId]/__tests__/ → 7단계 위가 저장소 루트.
const REPO_ROOT = fileURLToPath(new URL('../../../../../../../', import.meta.url));
const MIGRATIONS_DIR = join(REPO_ROOT, 'supabase/migrations');
const COMPONENT = join(REPO_ROOT, 'web/src/app/(user)/chat/[roomId]/ChatRoomMessages.tsx');
const PY_INTEGRATION = join(
  REPO_ROOT,
  'api/tests/integration/test_chat_realtime_broadcast_real_db.py',
);
const DART_REPO = join(REPO_ROOT, 'app/lib/features/chat/chat_repository.dart');
const DART_ROOM_SCREEN = join(REPO_ROOT, 'app/lib/features/chat/chat_room_screen.dart');

// SQL에서 `'<접두사>' || <테이블별칭>.<컬럼>::text` 모양을 모두 뽑는다. 트리거의
// `'chat:room:' || new.room_id::text`와 RLS의 `'chat:room:' || r.id::text` 둘 다 잡히고,
// 별칭 없이 이름만 언급하는 설명 주석(`|| room_id::text`)은 잡히지 않는다.
const SQL_TOPIC_EXPR = /'([^']*)'\s*\|\|\s*\w+\.\w+::text/g;

/**
 * 마이그레이션 **전체**를 훑는다 — 0023 한 파일만 읽으면 안 된다(코드리뷰 patch 2차).
 * 이 레포의 DB 규칙은 전진(forward-only)이라, 토픽을 바꾸는 정상 경로는 0023을 고치는 게 아니라
 * `create or replace`를 담은 새 마이그레이션(0024+)을 뒤에 붙이는 것이다. 그 경로가 이 검사의
 * 사각지대이면, 정작 이 검사가 막으려던 단 하나의 실제 드리프트를 못 본 채 green을 유지한다.
 */
function allMigrationsSql(): string {
  return readdirSync(MIGRATIONS_DIR)
    .filter((f) => f.endsWith('.sql'))
    .sort()
    .map((f) => readFileSync(join(MIGRATIONS_DIR, f), 'utf8'))
    .join('\n');
}

// `-- 설명` 줄주석 제거 — 인자 사이에 주석이 끼면 인자 위치 정규식이 못 잡는다.
function stripSqlComments(sql: string): string {
  return sql.replace(/--[^\n]*/g, '');
}

// `//` 줄주석 제거 — Dart 쪽 검사 전용. 실측으로 드러난 함정(코드리뷰 patch 2 자체 검증 중
// 발견): `_defaultChatSubscribe` 바로 위 doc comment(64행)가 실제 호출 코드를 설명하려고
// `supabase.channel(roomTopic(roomId), opts: RealtimeChannelConfig(private: true, ...`를
// 그대로 인용해 적어뒀다 — 아래 호출부 앵커 검사가 이 주석 문자열에도 매치돼, 실제 호출 코드를
// `roomTopic(roomId)` 없이 리터럴로 망가뜨려도(뮤테이션 테스트로 확인) 주석만 남아 있으면
// green이 나왔다. 실제 코드 줄만 보게 주석을 먼저 걷어낸다.
function stripDartLineComments(source: string): string {
  return source
    .split('\n')
    .map((line) => line.replace(/\/\/.*$/, ''))
    .join('\n');
}

function sqlTopicPrefixes(): string[] {
  return [...allMigrationsSql().matchAll(SQL_TOPIC_EXPR)].map((m) => m[1]);
}

describe('채팅 실시간 토픽 계약 — SQL·TS·Python 세 사본이 같은 문자열인가', () => {
  it('마이그레이션 전체에서 방송(트리거)·인가(RLS) 토픽 리터럴이 서로 같다', () => {
    const prefixes = sqlTopicPrefixes();
    // 트리거 1 + RLS 1 = 최소 2곳. 한쪽이 사라지면(예: RLS를 다른 방식으로 재작성) 여기서 걸린다.
    expect(prefixes.length).toBeGreaterThanOrEqual(2);
    expect(new Set(prefixes)).toEqual(new Set(['chat:room:']));
  });

  it('ChatRoomMessages.tsx의 roomTopic()이 SQL과 동일한 토픽을 만든다', () => {
    const [sqlPrefix] = sqlTopicPrefixes();
    const source = readFileSync(COMPONENT, 'utf8');
    const match = source.match(/function roomTopic\([^)]*\)\s*\{\s*return\s+`([^`]*)`/);
    expect(match, 'roomTopic() 헬퍼를 찾지 못했습니다(이름이 바뀌었다면 이 검사도 함께 고칠 것)').not
      .toBeNull();
    // 템플릿 리터럴의 보간부(${roomId})를 뺀 접두사가 SQL 쪽과 글자 그대로 같아야 한다.
    expect(match![1]).toBe(`${sqlPrefix}\${roomId}`);
  });

  it('ChatRoomMessages.tsx가 private 채널로 구독한다(0023의 realtime.messages RLS가 평가되는 조건)', () => {
    const source = readFileSync(COMPONENT, 'utf8');
    // private:true가 빠지면 RLS 자체가 평가되지 않아 인가 계층이 통째로 무력화된다.
    // 그 **호출 하나**에 묶어 단언한다(코드리뷰 patch 2차) — 이전엔 게으른 매칭이라
    // "파일 어딘가에 channel( 이 있고 그 뒤 어딘가에 private:true가 있다"만 확인했고,
    // 이 파일에 채널이 하나 더 생기면 정작 채팅 채널이 public이어도 통과했다.
    //
    // Story 12.4가 같은 config에 broadcast.replay를 추가하면서 `{ config: { private: true } }`처럼
    // 그 두 프로퍼티만 딱 닫히는 모양이 아니게 됐다 — `[^}]*`로 private:true 앞에 다른 프로퍼티가
    // 있어도(config 객체가 `}`로 닫히기 전이라면) 통과하게 완화한다.
    // ⚠️ `[^}{]*`인 이유(3차 후속 리뷰 patch, low). 이전엔 `[^}]*`였는데, 그건 `{`를 건너뛸 수
    // 있어서 **config 안의 중첩 객체에 들어 있는 private까지** 매치했다 — 즉
    // `{ config: { broadcast: { private: true } } }`(채널은 private가 아니고 broadcast 옵션에 엉뚱한
    // 키가 있을 뿐인 상태)에서도 green이었다(실측). private:true가 빠지면 0023의 realtime.messages
    // RLS 자체가 평가되지 않아 인가 계층이 통째로 무력화되는 축이라, 그 false-green은 그냥 두면
    // 안 된다. `{`까지 금지하면 매치되는 것은 **config의 직속(평문) 프로퍼티인 private:true** 뿐이다
    // (앞에 다른 평문 프로퍼티가 오는 순서는 여전히 허용 — 순서를 강제할 이유는 없다).
    expect(source).toMatch(
      /supabase\.channel\(\s*roomTopic\([^)]*\)\s*,\s*\{\s*config:\s*\{[^}{]*\bprivate:\s*true\b/,
    );
  });

  it('갭보정의 Broadcast Replay 경로가 **채널 생성 호출 안에** 남아 있다', () => {
    // 후속 리뷰 patch(R7) — docs/conventions.md §12.5는 갭보정을 "Replay + 커서 재조회 두 경로를
    // 항상 함께"로 못박았는데, 위 private 검사는 replay가 통째로 사라져도 여전히 green이다(정규식이
    // private까지만 본다). 그러면 갭보정이 조용히 커서 재조회 한 경로로 축소되고 아무도 red를 보지
    // 않는다 — 계약을 실행되는 검사로 내린다(B9). since는 필수 인자이므로 그 존재까지 함께 본다.
    // (replay 값의 **타입**은 tsc가 이미 강제한다 — 여기서 지키는 것은 "이 설정이 존재한다"는 축이다.)
    //
    // ⚠️ 채널 생성 호출에 **앵커한다**(3차 후속 리뷰 patch, low). 이전엔 파일 전체를 스캔하는
    // `expect(source).toMatch(/broadcast: { replay: { … since:/)` 한 줄이라, config에서 replay를
    // 떼어내 같은 파일의 미사용 지역 상수나 주석으로 옮겨도 green이었다(실측 — 채팅 채널의 replay는
    // 완전히 사라지는데 red가 없다). 위 private 검사는 앵커돼 있는데 이 검사만 아니면, R7이 세우려던
    // "계약을 실행되는 검사로" 가 절반만 성립한다.
    const source = readFileSync(COMPONENT, 'utf8');
    expect(source).toMatch(
      /supabase\.channel\(\s*roomTopic\([^)]*\)\s*,\s*\{\s*config:\s*\{[^}{]*broadcast:\s*\{\s*replay:\s*\{[^}]*\bsince:/,
    );
  });

  it('재연결(SUBSCRIBED+everDropped) 시 커서 재조회 갭보정이 함께 돈다', () => {
    // 3차 후속 리뷰 patch(low) — §12.5는 갭보정을 "Replay + 커서 재조회를 **항상 병행**"으로 못박고,
    // 대장 #201은 그중 커서 재조회 쪽이 "항상 맞는 백스톱"이고 replay는 "있으면 좋은 최적화"라고
    // 적었다. 그런데 실행되는 가드는 replay(위 검사)에만 있었고 정작 백스톱인 커서 경로는 없었다 —
    // `void gapFillFromCursor();` 한 줄을 지워도 전체 테스트가 green이었다(실측). 보호 강도가 정확히
    // 거꾸로 붙어 있던 셈이라 같은 층으로 내린다(B9).
    //
    // 이 검사가 **안 보는 것**: 실제로 재연결 순간에 그 함수가 불려 메시지가 병합되는지(런타임
    // 동작) — 그건 Story 12.6의 수동 2-브라우저 검증 몫이다. 여기서는 "재연결 분기에 그 호출이
    // 배선돼 있고, 그 함수가 커서를 넘겨 조회한다"는 두 축만 정적으로 고정한다.
    const source = readFileSync(COMPONENT, 'utf8');
    expect(source).toMatch(/if\s*\(everDropped\)\s*\{[\s\S]{0,800}?void gapFillFromCursor\(\)/);
    expect(source).toMatch(/fetchMessages\(\s*supabase,\s*roomId,\s*cursor\s*\)/);
  });

  it('끊긴 동안 입력창·전송 버튼·연타 가드가 잠기지 않는다(FR42·UX-DR19 비차단)', () => {
    // 3차 후속 리뷰 patch(low) — 이 스토리의 최상위 인수조건("연결이 끊겨도 계속 작성·전송할 수
    // 있다")을 실제로 지키는 것은 아래 세 조건식뿐인데, 전부 주석으로만 보호돼 있었다. 셋 중 무엇을
    // 12.3 형태(`sending || loading` 등)로 되돌려도 전체 테스트가 green이었다(실측). 그리고 이 규칙은
    // **이 스토리 안에서 이미 한 번 깨졌다** — 후속 리뷰 R5가 정확히 그 순서 문제를 고쳤다. 한 번
    // 깨진 적 있는 규칙을 주석으로만 두지 않는다(B9).
    //
    // 이 검사가 **안 보는 것**: 실제 렌더 결과의 disabled 속성(이 레포 vitest는 environment:'node'라
    // RTL 상호작용 테스트를 쓸 수 없다 — web/vitest.config.ts 주석 참조). 소스 문자열 층에서
    // "그 조건식이 그대로 있다"만 고정한다. 이 파일의 다른 검사들과 같은 관용이다.
    const source = readFileSync(COMPONENT, 'utf8');
    expect(source).toMatch(/disabled=\{\(sending && !isDisconnected\) \|\| loading\}/);
    expect(source).toMatch(/loading=\{sending && !isDisconnected\}/);
    expect(source).toMatch(/if \(sending && !disconnectedRef\.current\) return;/);
  });

  it('flush 미전송 안내는 전송 에러(error) 칸이 아니라 전용 칸에 쓴다', () => {
    // 3차 후속 리뷰 patch(medium) — 이 안내가 fail-loud의 유일한 신호인데, error 칸은 handleSubmit
    // 첫 줄의 setError(null)이 **제출마다 무조건** 비우는 자리다. 큐가 막힌 사용자의 가장 자연스러운
    // 다음 행동이 "한 번 더 보내보기"라, 그 순간 신호가 사라지고 화면이 완전히 정상으로 보였다
    // (실제 브라우저로 재현해 확인 — 되돌리면 red). 수명이 다른 신호는 다른 칸에 둔다는 이 파일의
    // 기존 규칙(realtimeError·loadError 분할)을 이 신호에도 강제한다(B9).
    //
    // 이 검사가 **안 보는 것**: 그 안내가 실제로 렌더돼 사용자 눈에 보이는지 — 소스 문자열 층에서
    // "flush 실패 경로가 전용 setter를 쓰고, 그 값이 렌더된다"는 두 축만 고정한다.
    const source = readFileSync(COMPONENT, 'utf8');
    expect(source).toMatch(/if \(remaining\.length > 0\) \{[\s\S]{0,400}?setQueueStuckNotice\(/);
    expect(source).toMatch(/\{queueStuckNotice && \(/);
  });

  it('방송 이벤트 이름이 SQL(트리거)과 TS(구독 필터)에서 같다', () => {
    // 토픽과 완전히 같은 무음 실패 축인데 가드가 없었다(코드리뷰 patch 2차): 트리거가 내보내는
    // event와 `channel.on('broadcast', { event })`의 필터는 정확히 일치해야 하고, 어긋나면 방송은
    // 계속 나가고 RLS도 통과하는데 콜백만 영영 안 불린다 — 폴링이 없으니 증상은 "조용히 0건 수신".
    const sql = stripSqlComments(allMigrationsSql());
    const call = sql.match(/realtime\.broadcast_changes\(\s*'[^']*'\s*\|\|[^,]*,\s*(\w+)\s*,/);
    expect(call, 'realtime.broadcast_changes 호출을 찾지 못했습니다').not.toBeNull();
    // 트리거는 `tg_op`을 event로 넘긴다 → 그 값은 트리거가 걸린 시점(아래 단언)에 따라 정해진다.
    expect(call![1]).toBe('tg_op');
    // AFTER INSERT 전용이므로 tg_op은 항상 'INSERT'다. UPDATE/DELETE가 추가되면 이 단언이 red가
    // 되고, 그때 TS 쪽 필터도 함께 늘려야 한다는 사실이 드러난다.
    expect(sql).toMatch(/create trigger chat_messages_broadcast_trigger\s+after insert\s+on/);

    const source = readFileSync(COMPONENT, 'utf8');
    const on = source.match(/channel\.on\(\s*'broadcast',\s*\{\s*event:\s*'([^']*)'/);
    expect(on, "channel.on('broadcast', { event: ... }) 구독을 찾지 못했습니다").not.toBeNull();
    expect(on![1]).toBe('INSERT');

    // app(Flutter)도 같은 축이다(Epic 16.4 코드리뷰 patch 9) — Dart 쪽엔 이 교차검사가 전혀
    // 없었다. `channel.onBroadcast(event: 'INSERT', ...)`의 'INSERT' 리터럴이 위에서 이미 확인한
    // SQL(AFTER INSERT 전용 → tg_op은 항상 'INSERT')과 어긋나면, 방송은 계속 나가는데 Dart
    // 구독만 그 이벤트를 걸러내 조용히 0건 수신이 된다.
    const dartSource = stripDartLineComments(readFileSync(DART_ROOM_SCREEN, 'utf8'));
    const dartOn = dartSource.match(/channel\.onBroadcast\(\s*event:\s*'([^']*)'/);
    expect(dartOn, "channel.onBroadcast(event: ...) 구독을 찾지 못했습니다").not.toBeNull();
    expect(dartOn![1]).toBe('INSERT');
  });

  it('api 실DB 통합테스트의 _TOPIC_PREFIX가 SQL과 같다', () => {
    const [sqlPrefix] = sqlTopicPrefixes();
    const source = readFileSync(PY_INTEGRATION, 'utf8');
    const match = source.match(/^_TOPIC_PREFIX\s*=\s*"([^"]*)"/m);
    expect(match, '_TOPIC_PREFIX 상수를 찾지 못했습니다').not.toBeNull();
    expect(match![1]).toBe(sqlPrefix);
  });

  it('app/chat_repository.dart의 roomTopic()이 SQL과 동일한 토픽을 만든다(Epic 16.4, 네 번째 사본)', () => {
    // docs/conventions.md §12 도입부가 지정한 자리 — Dart 쪽이 세 번째 사본(web)을 그대로
    // 옮긴 top-level 함수다. 템플릿 리터럴 보간부(`${roomId}`)를 뺀 접두사가 SQL과 같아야 한다.
    const [sqlPrefix] = sqlTopicPrefixes();
    const source = readFileSync(DART_REPO, 'utf8');
    // Dart 문자열 보간은 `${roomId}`가 아니라 단순 식별자라 `$roomId`(중괄호 없음) 형태다.
    const match = source.match(/String roomTopic\(String roomId\)\s*=>\s*'([^']*)\$roomId'/);
    expect(
      match,
      'roomTopic() 함수를 찾지 못했습니다(이름·형태가 바뀌었다면 이 검사도 함께 고칠 것)',
    ).not.toBeNull();
    expect(match![1]).toBe(sqlPrefix);
  });

  it('app/chat_room_screen.dart의 _defaultChatSubscribe가 roomTopic()을 private 채널로 실제 호출한다(코드리뷰 patch 2)', () => {
    // 위 검사는 Dart `roomTopic()` *함수 정의*만 SQL과 대조한다 — 그 함수가 실제 채널 생성
    // 호출부(`supabase.channel(...)`)에서 쓰이는지, 그 호출이 private:true인지는 안 봤다. 위
    // web `private:true` 검사와 같은 원칙(호출 하나에 앵커 — 파일 어딘가에 channel(과 private:true가
    // 따로 있어도 통과하는 게으른 매칭을 피한다)으로, Dart 쪽 호출부도 같은 축을 고정한다.
    // 주석을 먼저 걷어낸다 — 이 함수 바로 위 doc comment가 같은 호출부 문자열을 그대로 인용해
    // 적어뒀어서, 주석을 안 걷으면 실제 코드가 망가져도(roomTopic(roomId)이 빠져도) 주석
    // 문자열에 매치돼 green이 나온다(위 stripDartLineComments 주석 참조, 실측).
    const source = stripDartLineComments(readFileSync(DART_ROOM_SCREEN, 'utf8'));
    // private:true 앵커는 그대로 유지하고, 같은 RealtimeChannelConfig(...) 호출 안에 갭보정의
    // Broadcast Replay(§12.5)까지 이어져 있는지 함께 본다(코드리뷰 patch 9) — 이전엔
    // private:true까지만 앵커돼 있어서, `replay: ReplayOption(...)` 전체를 지워도(갭보정 두
    // 경로 중 하나가 통째로 사라져도) 이 검사는 계속 green이었다(web의 동일 결함을 고친
    // "채널 생성 호출에 앵커한다" 원칙을 Dart 쪽에도 적용).
    expect(source).toMatch(
      /supabase\.channel\(\s*roomTopic\(roomId\)\s*,\s*opts:\s*RealtimeChannelConfig\(\s*private:\s*true\b[^)]*replay:\s*ReplayOption\(\s*since:/,
    );

    // 채널을 private+replay로 열어놓기만 하고 정작 아무 이벤트도 안 구독하거나(onBroadcast 삭제)
    // subscribe() 자체를 안 부르면(채널이 join되지 않아 위 config 전체가 무의미해진다) 방은
    // 여전히 죽는다 — 이 두 실제 배선 호출도 함께 고정한다(코드리뷰 patch 9, 이전엔 이 두 호출을
    // 확인하는 검사가 전혀 없었다).
    expect(source).toMatch(/channel\.onBroadcast\(\s*event:\s*'INSERT'\s*,\s*callback:\s*onInsert\s*\)/);
    expect(source).toMatch(/channel\.subscribe\(onStatus\)/);
  });
});
