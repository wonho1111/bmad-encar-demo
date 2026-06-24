// 7.5 채팅 모델 단위 테스트 — fromMap 가드(깨진 행 제외)·임베드 null 처리.
import 'package:flutter_test/flutter_test.dart';
import 'package:app/features/chat/chat_models.dart';

void main() {
  group('ChatMessage.fromMap', () {
    test('정상 5필드 → 메시지', () {
      final m = ChatMessage.fromMap({
        'id': 'm1',
        'room_id': 'r1',
        'sender_id': 's1',
        'body': '안녕하세요',
        'created_at': '2026-06-25T10:00:00+00:00',
      });
      expect(m, isNotNull);
      expect(m!.body, '안녕하세요');
      expect(m.roomId, 'r1');
      expect(m.senderId, 's1');
    });

    test('필수 필드 누락/타입 깨짐 → null(그 행 제외)', () {
      expect(ChatMessage.fromMap({'id': 'm1'}), isNull);
      // body 가 문자열이 아님
      expect(
        ChatMessage.fromMap({
          'id': 'm1',
          'room_id': 'r1',
          'sender_id': 's1',
          'body': 123,
          'created_at': '2026-06-25T10:00:00Z',
        }),
        isNull,
      );
      expect(ChatMessage.fromMap(null), isNull);
      expect(ChatMessage.fromMap('not a map'), isNull);
    });
  });

  group('ChatRoomSummary.fromMap', () {
    Map<String, dynamic> base() => {
          'id': 'room1',
          'listing_id': 'l1',
          'buyer_id': 'b1',
          'seller_id': 's1',
          'buyer_name': 'buyer',
          'seller_name': 'seller',
        };

    test('정상 + 임베드 매물 → listing 채워짐', () {
      final r = ChatRoomSummary.fromMap({
        ...base(),
        'listings': {
          'manufacturer': '현대',
          'model': '소나타',
          'year': 2020,
          'price': 25000000,
          'status': 'on_sale',
        },
      });
      expect(r, isNotNull);
      expect(r!.buyerName, 'buyer');
      expect(r.sellerName, 'seller');
      expect(r.listing, isNotNull);
      expect(r.listing!.model, '소나타');
      expect(r.listing!.status, 'on_sale');
    });

    test('임베드 null(sold·조회불가) → listing null (플레이스홀더)', () {
      final r = ChatRoomSummary.fromMap({...base(), 'listings': null});
      expect(r, isNotNull);
      expect(r!.listing, isNull);
    });

    test('이름 없음(예전 방) → buyer_name/seller_name null', () {
      final r = ChatRoomSummary.fromMap({
        'id': 'room1',
        'listing_id': 'l1',
        'buyer_id': 'b1',
        'seller_id': 's1',
        'listings': null,
      });
      expect(r, isNotNull);
      expect(r!.buyerName, isNull);
      expect(r.sellerName, isNull);
    });

    test('필수 식별자 누락 → null', () {
      expect(ChatRoomSummary.fromMap({...base()}..remove('id')), isNull);
      expect(ChatRoomSummary.fromMap({...base()}..remove('listing_id')), isNull);
      expect(ChatRoomSummary.fromMap('not a map'), isNull);
    });
  });
}
