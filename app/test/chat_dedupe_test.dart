// 7.5 dedupeById 단위 테스트 — 중복 제거(첫 등장)·시간순 안정 정렬.
//   web dedupeById 동작 미러: 폴링 증분과 낙관 전송이 같은 행을 두 번 넣어도 중복 없음,
//   거의 동시에 양쪽이 보낼 때 화면이 시간 역순으로 보이지 않게 (created_at, id) 재정렬.
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/chat/chat_models.dart';
import 'package:app/features/chat/chat_repository.dart';

ChatMessage _msg(String id, String createdAt, {String body = 'x'}) => ChatMessage(
      id: id,
      roomId: 'r1',
      senderId: 's1',
      body: body,
      createdAt: createdAt,
    );

void main() {
  group('dedupeById', () {
    test('같은 id 는 첫 등장만 남긴다(중복 제거)', () {
      final out = dedupeById([
        _msg('a', '2026-06-25T10:00:00Z', body: '첫번째'),
        _msg('a', '2026-06-25T10:00:00Z', body: '두번째(중복)'),
        _msg('b', '2026-06-25T10:00:01Z'),
      ]);
      expect(out.length, 2);
      expect(out[0].id, 'a');
      expect(out[0].body, '첫번째'); // 첫 등장 보존
      expect(out[1].id, 'b');
    });

    test('append 순서가 뒤섞여도 (created_at, id) 시간순으로 재정렬', () {
      // 내 낙관 전송(더 늦은 시각)이 먼저 들어오고, 상대의 더 이른 메시지가 뒤에 들어온 상황.
      final out = dedupeById([
        _msg('me', '2026-06-25T10:00:05Z', body: '내메시지'),
        _msg('other', '2026-06-25T10:00:02Z', body: '상대메시지(더 이름)'),
      ]);
      expect(out.map((m) => m.id).toList(), ['other', 'me']);
    });

    test('동일 created_at 은 id 로 안정 정렬', () {
      final out = dedupeById([
        _msg('z', '2026-06-25T10:00:00Z'),
        _msg('a', '2026-06-25T10:00:00Z'),
        _msg('m', '2026-06-25T10:00:00Z'),
      ]);
      expect(out.map((m) => m.id).toList(), ['a', 'm', 'z']);
    });

    test('빈 입력 → 빈 출력', () {
      expect(dedupeById(const []), isEmpty);
    });
  });
}
