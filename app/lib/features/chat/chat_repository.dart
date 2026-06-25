// 채팅 레포지토리 — 방 생성/재사용 + 메시지 조회/전송의 단일 출처.
//   web 의 lib/chat.ts(openOrCreateRoom)·lib/messages.ts(fetchMessages·sendMessage·dedupeById)를
//   Flutter 로 이식한 것. 규칙을 한 곳에 모아 폴링·전송 두 경로가 같은 dedupe·정렬을 공유 → drift 없음.
//
// DB 가 보장하는 무결성을 신뢰한다(supabase/migrations):
//   · 0003c enforce_chat_room_seller 트리거: chat_rooms INSERT 시 seller_id 를 매물 실소유자로 강제.
//     → 클라는 seller_id 를 보내지 않는다(보내도 무시). insert 에는 listing_id·buyer_id 만.
//   · 0003 RLS: 방/메시지 모두 "당사자만" read/write(제3자 0건). sender_id=auth.uid() 강제.
//   · UNIQUE(listing_id,buyer_id,seller_id) → 같은 (매물,구매자)는 항상 같은 방(재사용 토대).
//   · CHECK(buyer_id<>seller_id) / CHECK(body 공백금지) → 본인매물·빈본문은 23514 로 거부.
//   · 0008: buyer_name/seller_name(이메일 @앞부분) 트리거 자동기록 — 앱은 읽기만.
//
// 통신선/컬럼은 snake_case(AR5). 에러는 사용자에게 한국어로만(원본은 print 로그) — listings_repository 규칙과 동일.
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/supabase_client.dart';
import 'chat_models.dart';

// Postgres SQLSTATE 코드(PostgrestException.code 에 그대로 실려 온다).
const String _pgUniqueViolation = '23505'; // UNIQUE 위반(방 동시 생성 경합)
const String _pgCheckViolation = '23514'; // CHECK 위반(본인매물 문의 / 빈 본문)
const String _pgFkViolation = '23503'; // FK 위반(없는 매물 — 0003c 트리거가 같은 코드로 거부)

/// 방 열기 결과 — 성공이면 roomId, 실패면 사용자에게 보여줄 한국어 메시지.
sealed class OpenRoomResult {
  const OpenRoomResult();
}

class OpenRoomSuccess extends OpenRoomResult {
  const OpenRoomSuccess(this.roomId);
  final String roomId;
}

class OpenRoomFailure extends OpenRoomResult {
  const OpenRoomFailure(this.message);
  final String message; // 한국어
}

/// 메시지 전송 결과 — 성공이면 저장된 행, 실패면 한국어 메시지.
sealed class SendMessageResult {
  const SendMessageResult();
}

class SendMessageSuccess extends SendMessageResult {
  const SendMessageSuccess(this.message);
  final ChatMessage message;
}

class SendMessageFailure extends SendMessageResult {
  const SendMessageFailure(this.message);
  final String message; // 한국어
}

class ChatRepository {
  ChatRepository({SupabaseClient? client}) : _client = client ?? supabase;

  final SupabaseClient _client;

  // (listing_id, buyer_id)로 기존 방 1건 조회.
  //   반환: 방(있으면 id, 없으면 null) / 조회 자체 실패는 throw → 호출부가 "없음"과 구분.
  Future<String?> _findExistingRoom(String listingId, String buyerId) async {
    final row = await _client
        .from('chat_rooms')
        .select('id')
        .eq('listing_id', listingId)
        .eq('buyer_id', buyerId)
        .maybeSingle();
    final id = row?['id'];
    return id is String ? id : null;
  }

  /// 그 매물의 판매자와의 채팅방을 연다(있으면 재사용, 없으면 생성). web openOrCreateRoom 이식.
  ///   1) (listing_id,buyer_id)로 기존 방 조회 → 있으면 재사용(중복 방 방지, AC1).
  ///   2) 없으면 insert(listing_id, buyer_id) → 트리거가 seller_id 를 매물주로 채운다.
  ///   3) UNIQUE 경합(23505) → 그새 만들어진 방 재조회 흡수.
  ///   4) 본인 매물(buyer=seller, 23514) → 한국어 거부.
  ///   5) 없는 매물(23503 트리거) → 한국어 거부.
  Future<OpenRoomResult> openOrCreateRoom({
    required String listingId,
    required String buyerId,
  }) async {
    try {
      // 1) 기존 방 재사용 우선.
      final existing = await _findExistingRoom(listingId, buyerId);
      if (existing != null) return OpenRoomSuccess(existing);

      // 2) 없으면 생성. seller_id 는 보내지 않는다(트리거가 매물주로 강제 — 위조 차단·자동 연결).
      final created = await _client
          .from('chat_rooms')
          .insert({'listing_id': listingId, 'buyer_id': buyerId})
          .select('id')
          .single();
      final id = created['id'];
      if (id is String) return OpenRoomSuccess(id);
      return const OpenRoomFailure('채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } on PostgrestException catch (e) {
      // 3) UNIQUE 경합 → 그새 다른 요청이 만든 방을 다시 찾아 재사용.
      if (e.code == _pgUniqueViolation) {
        try {
          final raced = await _findExistingRoom(listingId, buyerId);
          if (raced != null) return OpenRoomSuccess(raced);
        } catch (_) {
          // 재조회도 실패 → 아래 일반 안내로.
        }
      }
      // 4) 본인 매물 문의(buyer=seller) → CHECK 위반.
      if (e.code == _pgCheckViolation) {
        return const OpenRoomFailure('본인 매물에는 문의할 수 없습니다.');
      }
      // 5) 없는 매물(0003c 트리거가 거부) → 삭제·판매완료된 매물일 수 있음.
      if (e.code == _pgFkViolation) {
        return const OpenRoomFailure('해당 매물을 찾을 수 없습니다. 삭제되었거나 판매가 완료된 매물일 수 있습니다.');
      }
      // ignore: avoid_print
      print('[chat] 채팅방 생성 실패: ${e.code} ${e.message}');
      return const OpenRoomFailure('채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 채팅방 열기 예외: $e');
      return const OpenRoomFailure('채팅방을 여는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    }
  }

  /// 내 채팅방 목록(매물 요약 임베드). RLS 가 당사자 방만 통과(별도 필터 불필요).
  ///   최신순(created_at desc) + id 2차정렬(같은 시각 순서 안정화 — search 와 동일 정신).
  Future<List<ChatRoomSummary>> fetchRooms() async {
    final rows = await _client
        .from('chat_rooms')
        .select(
          'id, listing_id, buyer_id, seller_id, buyer_name, seller_name, '
          'listings(manufacturer, model, year, price, status)',
        )
        .order('created_at', ascending: false)
        .order('id', ascending: false);

    return rows
        .map(ChatRoomSummary.fromMap)
        .whereType<ChatRoomSummary>()
        .toList();
  }

  /// 방 1건(헤더·상대표기·매물링크용). RLS 상 당사자가 아니면 null(없음·삭제·제3자 일괄).
  Future<ChatRoomSummary?> fetchRoom(String roomId) async {
    final row = await _client
        .from('chat_rooms')
        .select(
          'id, listing_id, buyer_id, seller_id, buyer_name, seller_name, '
          'listings(manufacturer, model, year, price, status)',
        )
        .eq('id', roomId)
        .maybeSingle();
    if (row == null) return null;
    return ChatRoomSummary.fromMap(row);
  }

  /// 한 방의 메시지를 시간순(오래된→최신)으로 조회. RLS 경유라 "내 방"만 보인다.
  ///   atOrAfterCreatedAt(폴링 커서)을 주면 그 시각 "이상(gte)"만 — 동시각 경계 행을 다시 포함해
  ///   누락을 막고, 그 중복은 호출부 dedupeById 가 제거(누락0·중복0). web messages.ts 실측 근거.
  ///   ⚠️ gt(>) 면 동일 created_at 의 새 메시지를 영구 누락 → 반드시 gte(>=).
  Future<List<ChatMessage>> fetchMessages(
    String roomId, {
    String? atOrAfterCreatedAt,
  }) async {
    var query = _client
        .from('chat_messages')
        .select('id, room_id, sender_id, body, created_at')
        .eq('room_id', roomId);

    if (atOrAfterCreatedAt != null) {
      query = query.gte('created_at', atOrAfterCreatedAt);
    }

    final rows = await query
        .order('created_at', ascending: true)
        .order('id', ascending: true);

    return rows.map(ChatMessage.fromMap).whereType<ChatMessage>().toList();
  }

  /// 메시지 전송(chat_messages INSERT → 영속, FR21). senderId 는 본인(RLS 가 auth.uid()=sender_id 강제).
  ///   1차로 공백만이면 보내지 않는다(DB CHECK 전에 낭비 차단). 우회한 빈 본문은 23514 로 최종 방어.
  Future<SendMessageResult> sendMessage({
    required String roomId,
    required String senderId,
    required String body,
  }) async {
    final trimmed = body.trim();
    if (trimmed.isEmpty) {
      return const SendMessageFailure('메시지를 입력해주세요.');
    }
    try {
      final row = await _client
          .from('chat_messages')
          .insert({'room_id': roomId, 'sender_id': senderId, 'body': trimmed})
          .select('id, room_id, sender_id, body, created_at')
          .single();
      final msg = ChatMessage.fromMap(row);
      if (msg != null) return SendMessageSuccess(msg);
      return const SendMessageFailure('메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.');
    } on PostgrestException catch (e) {
      if (e.code == _pgCheckViolation) {
        return const SendMessageFailure('빈 메시지는 보낼 수 없습니다.');
      }
      // ignore: avoid_print
      print('[chat] 메시지 전송 실패: ${e.code} ${e.message}');
      return const SendMessageFailure('메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.');
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 메시지 전송 예외: $e');
      return const SendMessageFailure('네트워크 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
    }
  }
}

/// id 기준 중복 제거 + (created_at asc, id asc) 안정 정렬. web dedupeById 미러.
///   폴링 증분과 "내 낙관적 전송"이 같은 행을 두 번 넣으려 할 때 중복을 막고(같은 id 첫 등장만),
///   거의 동시에 양쪽이 보낼 때 화면이 시간 역순으로 보이는 것을 방지(머지는 순서를 보장하지 않으므로 재정렬).
List<ChatMessage> dedupeById(List<ChatMessage> messages) {
  final seen = <String>{};
  final out = <ChatMessage>[];
  for (final m in messages) {
    if (seen.contains(m.id)) continue;
    seen.add(m.id);
    out.add(m);
  }
  // created_at 오름차순, 동시각이면 id 로 안정화(fetchMessages 의 order 와 동일 규칙).
  out.sort((a, b) {
    final c = a.createdAt.compareTo(b.createdAt);
    if (c != 0) return c;
    return a.id.compareTo(b.id);
  });
  return out;
}
