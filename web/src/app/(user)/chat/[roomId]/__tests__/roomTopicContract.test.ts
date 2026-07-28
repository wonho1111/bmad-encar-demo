// 채팅 실시간 구독 토픽 계약 교차 검사 (Story 12.3 코드리뷰 patch, CLAUDE.md B9 —
// "주석·문서는 계약이 아니다. 지켜야 하는 규칙이면 실행되는 검사로 바꾼다").
//
// 왜 필요한가:
//   `chat:room:{room_id}`라는 토픽 문자열은 **서로 다른 언어로 쓰인 세 벌의 리터럴**로 존재한다 —
//   ① `supabase/migrations/0023_chat_realtime_broadcast.sql`의 트리거(방송을 내보내는 쪽)와
//      RLS 정책(구독을 인가하는 쪽), ② `ChatRoomMessages.tsx`의 `roomTopic()`(구독하는 쪽),
//      ③ `api/tests/integration/test_chat_realtime_broadcast_real_db.py`의 `_TOPIC_PREFIX`(실DB로
//      방송을 검증하는 쪽). 한쪽만 바꿔도 컴파일·lint·기존 테스트가 전부 통과하는데, 실제로는
//      "방송은 계속 나가는데 아무도 못 듣는" 무음 실패가 된다. docs/conventions.md §12가 이 위험을
//      글로 적어뒀지만 글은 실행되지 않는다 — 이 파일이 그 자리를 대신한다.
//
// 이 검사가 **안 보는 것**:
//   · 실제 Realtime 서버가 그 토픽으로 방송을 내보내고 구독이 붙는지(런타임 동작) — 그건
//     `api/tests/integration/test_chat_realtime_broadcast_real_db.py`(실DB)와 Story 12.6의 수동
//     2-브라우저 검증 몫이다. 여기서는 "세 벌의 문자열이 서로 같은가"만 정적으로 고정한다.
//   · Flutter 앱(Epic 16 Story 16.4가 네 번째 사본을 만들 자리) — 아직 존재하지 않으므로 범위 밖.
//     그 사본이 생기면 여기에 한 줄 추가한다.
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
    expect(source).toMatch(
      /supabase\.channel\(\s*roomTopic\([^)]*\)\s*,\s*\{\s*config:\s*\{\s*private:\s*true\s*\}\s*\}\s*\)/,
    );
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
  });

  it('api 실DB 통합테스트의 _TOPIC_PREFIX가 SQL과 같다', () => {
    const [sqlPrefix] = sqlTopicPrefixes();
    const source = readFileSync(PY_INTEGRATION, 'utf8');
    const match = source.match(/^_TOPIC_PREFIX\s*=\s*"([^"]*)"/m);
    expect(match, '_TOPIC_PREFIX 상수를 찾지 못했습니다').not.toBeNull();
    expect(match![1]).toBe(sqlPrefix);
  });
});
