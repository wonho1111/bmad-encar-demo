// 채팅 레포지토리 — 방 생성/재사용 + 메시지 조회/전송(멱등)/안읽음 집계/읽음 갱신의 단일 출처.
//   web 의 lib/chat.ts(openOrCreateRoom·markChatRoomRead)·lib/messages.ts(fetchMessages·sendMessage·
//   dedupeById·reuseFailedKey·flushMessageQueue)를 Flutter 로 이식한 것. 규칙을 한 곳에 모아
//   실시간 수신·전송·재연결 flush 세 경로가 같은 dedupe·정렬·멱등을 공유 → drift 없음.
//
// DB 가 보장하는 무결성을 신뢰한다(supabase/migrations):
//   · 0003c enforce_chat_room_seller 트리거: chat_rooms INSERT 시 seller_id 를 매물 실소유자로 강제.
//     → 클라는 seller_id 를 보내지 않는다(보내도 무시). insert 에는 listing_id·buyer_id 만.
//   · 0003 RLS: 방/메시지 모두 "당사자만" read/write(제3자 0건). sender_id=auth.uid() 강제.
//   · UNIQUE(listing_id,buyer_id,seller_id) → 같은 (매물,구매자)는 항상 같은 방(재사용 토대).
//   · CHECK(buyer_id<>seller_id) / CHECK(body 공백금지) → 본인매물·빈본문은 23514 로 거부.
//   · 0008: buyer_name/seller_name(이메일 @앞부분) 트리거 자동기록 — 앱은 읽기만.
//   · 0022: UNIQUE(room_id, client_message_id) — 같은 멱등키 재INSERT(네트워크 재시도)는 23505.
//   · 0023: chat_messages AFTER INSERT 트리거가 `chat:room:{room_id}` private 채널로 방송.
//   · 0024~0026: chat_room_reads(읽음 시각)·chat_rooms.last_message_at(정렬)·
//     chat_unread_count()/chat_unread_by_room() RPC(안읽음 집계).
//
// 통신선/컬럼은 snake_case(AR5). 에러는 사용자에게 한국어로만(원본은 print 로그) — listings_repository 규칙과 동일.
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:supabase_flutter/supabase_flutter.dart';

import '../../core/supabase/supabase_client.dart';
import 'chat_models.dart';

// Postgres SQLSTATE 코드(PostgrestException.code 에 그대로 실려 온다).
const String _pgUniqueViolation = '23505'; // UNIQUE 위반(방 동시 생성 경합 / 멱등 재전송)
const String _pgCheckViolation = '23514'; // CHECK 위반(본인매물 문의 / 빈 본문)
const String _pgFkViolation = '23503'; // FK 위반(없는 매물 — 0003c 트리거가 같은 코드로 거부)

/// 채팅 메시지 조회·전송 select 문자열(client_message_id 포함) — fetchMessages·sendMessage·
/// 멱등 재조회 세 자리가 같은 컬럼 집합을 쓰도록 한 곳에 둔다(drift 방지).
const String _messageColumns = 'id, room_id, sender_id, body, created_at, client_message_id';

/// 실시간 구독 토픽 문자열의 **단일 출처**. `supabase/migrations/0023_chat_realtime_broadcast.sql`
/// 의 트리거(`'chat:room:' || new.room_id::text`)·RLS(`'chat:room:' || r.id::text`) 리터럴과
/// 문자 그대로 동일해야 한다(docs/conventions.md §12 — web `ChatRoomMessages.tsx`의 `roomTopic()`이
/// 세 번째 사본, 이 함수가 Dart 네 번째 사본). 한쪽만 바뀌면 방송은 계속 나가는데 아무도 못 듣거나
/// 그 반대가 된다 — `web/.../__tests__/roomTopicContract.test.ts`가 이 문자열을 SQL과 대조한다.
String roomTopic(String roomId) => 'chat:room:$roomId';

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

/// 멱등 재전송(23505) 후 재조회한 기존 행이 "내가 방금 보낸 그 메시지"인지 판정하는 순수 술어
/// (wishlist_repository.dart의 isIgnorableWishInsertError·isWishlistBlocked와 동일 추출 원칙 —
/// 이 판정을 sendMessage 본문에 직접 두면, 이 리포의 관례상 실 네트워크를 타는 레포지토리 메서드는
/// 단위테스트로 갈아 끼워지지 않으므로 이 분기 자체가 어떤 테스트로도 실행되지 않는다). sender_id·
/// body 둘 다 일치해야 성공(UUID 충돌·손상 데이터 배제) — web sendMessage 133-154행과 동일 방어.
bool isIdempotentResendMatch({
  required String existingSenderId,
  required String existingBody,
  required String callerSenderId,
  required String callerBody,
}) => existingSenderId == callerSenderId && existingBody == callerBody;

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
  ///   최신 문의 순(last_message_at desc, FR57·docs/conventions.md §12.6 — 방 생성순이 아니라
  ///   그 방의 마지막 메시지 시각순) + id 2차정렬(같은 시각 순서 안정화 — search 와 동일 정신).
  Future<List<ChatRoomSummary>> fetchRooms() async {
    final rows = await _client
        .from('chat_rooms')
        .select(
          'id, listing_id, buyer_id, seller_id, buyer_name, seller_name, last_message_at, '
          'listings(manufacturer, model, year, price, status)',
        )
        .order('last_message_at', ascending: false)
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
  ///   atOrAfterCreatedAt(갭보정 커서, §12.5)을 주면 그 시각 "이상(gte)"만 — 동시각 경계 행을
  ///   다시 포함해 누락을 막고, 그 중복은 호출부 dedupeById 가 제거(누락0·중복0). web messages.ts
  ///   실측 근거. ⚠️ gt(>) 면 동일 created_at 의 새 메시지를 영구 누락 → 반드시 gte(>=).
  Future<List<ChatMessage>> fetchMessages(
    String roomId, {
    String? atOrAfterCreatedAt,
  }) async {
    var query = _client.from('chat_messages').select(_messageColumns).eq('room_id', roomId);

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
  ///
  /// clientMessageId(멱등키, 0022·§12.4) — 호출부(화면)가 전송 시작 시점에 만들어 넘긴다. 같은
  /// (room_id, client_message_id)로 재INSERT(네트워크 재시도)하면 DB가 23505로 거부하는데, 이
  /// 함수는 그걸 에러로 올리지 않고 기존 행을 조회해 그 행으로 수렴시킨다(재전송 = 항상 성공).
  /// 조회된 행이 호출자 자신의 전송인지(sender_id·body 일치) 확인한 뒤에만 성공으로 취급한다 —
  /// web sendMessage 133-154행과 동일 방어(UUID 충돌·손상 데이터 배제).
  Future<SendMessageResult> sendMessage({
    required String roomId,
    required String senderId,
    required String body,
    required String clientMessageId,
  }) async {
    final trimmed = body.trim();
    if (trimmed.isEmpty) {
      return const SendMessageFailure('메시지를 입력해주세요.');
    }
    try {
      final row = await _client
          .from('chat_messages')
          .insert({
            'room_id': roomId,
            'sender_id': senderId,
            'body': trimmed,
            'client_message_id': clientMessageId,
          })
          .select(_messageColumns)
          .single();
      final msg = ChatMessage.fromMap(row);
      if (msg != null) return SendMessageSuccess(msg);
      return const SendMessageFailure('메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.');
    } on PostgrestException catch (e) {
      // 멱등 재전송(23505, UNIQUE(room_id, client_message_id) 위반) — 같은 키로 이미 저장된 행이
      // 있다는 뜻이므로 에러로 보여주지 않고 그 행을 조회해 확정한다.
      if (e.code == _pgUniqueViolation) {
        try {
          final existing = await _client
              .from('chat_messages')
              .select(_messageColumns)
              .eq('room_id', roomId)
              .eq('client_message_id', clientMessageId)
              .single();
          final msg = ChatMessage.fromMap(existing);
          if (msg != null &&
              isIdempotentResendMatch(
                existingSenderId: msg.senderId,
                existingBody: msg.body,
                callerSenderId: senderId,
                callerBody: trimmed,
              )) {
            return SendMessageSuccess(msg);
          }
        } catch (_) {
          // 조회 자체도 실패 → 아래 일반 안내로 폴백.
        }
        // ignore: avoid_print
        print('[chat] 멱등 재전송 후 기존 행 조회 실패(또는 불일치)');
        return const SendMessageFailure('메시지를 보내지 못했습니다. 잠시 후 다시 시도해주세요.');
      }
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

  /// 로그인 사용자의 안읽음 메시지 총합(내비 채팅 탭 배지). `chat_unread_count()` RPC(0024,
  /// docs/conventions.md §12.6) 하나가 유일한 계산처 — 화면은 재구현하지 않는다. 조회 실패는
  /// 0으로 폴백한다(배지는 부가 정보라 렌더 자체를 막지 않는다, 콘솔 로그만 — wishlist_repository
  /// 의 fetchWishedListingIds 와 동일 방침).
  Future<int> fetchUnreadTotal() async {
    try {
      final res = await _client.rpc('chat_unread_count');
      return _asChatInt(res) ?? 0;
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 안읽음 총합 조회 실패: $e');
      return 0;
    }
  }

  /// 방별 안읽음 메시지 수(DW-548, 목록 각 행 배지). `chat_unread_by_room()` RPC(0026)가 안읽음이
  /// 있는 방만 행으로 준다 — 행이 없는 방은 호출부가 0으로 읽는다. 조회 실패는 빈 Map(전부 0으로
  /// 보임)으로 폴백한다(총합 배지와 동일 방침).
  Future<Map<String, int>> fetchUnreadByRoom() async {
    try {
      final rows = await _client.rpc('chat_unread_by_room');
      return parseUnreadByRoomRows(rows);
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 방별 안읽음 조회 실패: $e');
      return {};
    }
  }

  /// 방 진입 시 본인의 "마지막으로 읽은 시각"을 지금 시각으로 upsert한다(FR57, §12.6). 호출부가
  /// 이미 당사자 대조(myId == buyerId || sellerId)를 끝낸 뒤에만 불러야 한다 — 이 함수 자체는
  /// 그 대조를 하지 않는다(web markChatRoomRead 와 동일 계약, RLS가 그 조건을 다시 강제한다).
  /// 실패해도 화면을 막지 않는다(배지는 부가 정보) — 콘솔 로그만.
  Future<void> markRoomRead(String roomId) async {
    final userId = _client.auth.currentUser?.id;
    if (userId == null) return;
    try {
      await _client.from('chat_room_reads').upsert(
        {
          'user_id': userId,
          'room_id': roomId,
          'last_read_at': DateTime.now().toUtc().toIso8601String(),
        },
        onConflict: 'user_id,room_id',
      );
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 읽음 상태 갱신 실패: $e');
    }
  }
}

/// `chat_unread_by_room()` RPC(0026) 응답을 {room_id: unread} Map으로 파싱하는 순수 함수 —
/// fetchUnreadByRoom()의 매핑 로직을 그대로 뽑아냈다(isIdempotentResendMatch와 동일 추출 원칙,
/// 코드리뷰 patch 6 — fetchUnreadByRoom() 자체는 실 네트워크 호출이라 이 리포 관례상
/// 단위테스트 대상이 아니라, 이 매핑이 어떤 테스트로도 실행되지 않고 있었다. RPC 응답 형태가
/// 바뀌어도(예: `unread` 컬럼명 변경) 잡아낼 방법이 없었다). rows가 List가 아니거나, 각 행이
/// Map이 아니거나, room_id가 String이 아니거나, unread가 정수로 안 읽히면 그 행만 조용히
/// 건너뛴다(전체 실패로 번지지 않는다 — fetchUnreadByRoom()의 "실패는 빈 Map" 방침과 같은 결).
@visibleForTesting
Map<String, int> parseUnreadByRoomRows(Object? rows) {
  final map = <String, int>{};
  if (rows is List) {
    for (final row in rows) {
      if (row is! Map) continue;
      final roomId = row['room_id'];
      final unread = _asChatInt(row['unread']);
      if (roomId is String && unread != null) map[roomId] = unread;
    }
  }
  return map;
}

/// RPC 응답의 정수 안전 변환(int/double/문자열 흡수) — chat_models.dart의 _asInt 와 같은 방어를
/// PostgREST RPC 응답(scalar/count)에도 적용한다.
int? _asChatInt(Object? v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is double) return v.toInt();
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v.trim());
  return null;
}

/// 직전에 실패한 전송의 기억(화면이 들고 있는 값 그대로) — web FailedSend 미러.
class FailedSend {
  const FailedSend({required this.clientMessageId, required this.body, required this.at});

  final String clientMessageId;
  final String body;
  final int at; // epoch ms(DateTime.now().millisecondsSinceEpoch) — 재사용 창 판정용.
}

/// "이번 전송이 방금 실패한 그 전송의 재시도인가"를 판정해, 맞으면 재사용할 멱등키를 돌려준다.
/// 아니면 null(호출부가 새 클라이언트 메시지 id를 만든다). web reuseFailedKey 미러
/// (docs/conventions.md §12.4) — 본문이 글자 그대로 같고 재사용 창(windowMs) 안일 때만 재사용한다.
///
/// 왜 너무 안 쓰면/너무 오래 쓰면 둘 다 위험한가는 web 쪽 주석 참조(같은 트레이드오프): 재사용 안
/// 하면 "서버엔 저장됐는데 응답만 유실"에서 재시도가 새 키로 중복 행을 만들고, 창이 없으면 한참
/// 뒤 우연히 같은 본문을 보낼 때 옛 키가 재사용돼 새 메시지가 조용히 사라진다.
String? reuseFailedKey(FailedSend? remembered, String body, int now, int windowMs) {
  if (remembered == null) return null;
  if (remembered.body != body) return null;
  if (now - remembered.at > windowMs) return null;
  return remembered.clientMessageId;
}

/// 오프라인 큐 flush 결과 — remaining(순서 보존, 다음 재연결에 재시도) / sent(성공분, 화면 병합용).
class FlushQueueResult {
  const FlushQueueResult({required this.remaining, required this.sent});

  final List<QueuedChatMessage> remaining;
  final List<ChatMessage> sent;
}

/// 오프라인 큐를 순서대로(순차 await) flush하는 순수 알고리즘 — web flushMessageQueue 미러
/// (docs/conventions.md §12.5). 화면(ChatRoomScreen)에서 네트워크·상태를 떼어내 단위테스트로
/// 직접 검증한다(B9 "실행되는 검사로 고정").
///
/// 규칙: 큐 순서대로 하나씩 sendFn을 호출한다(동시 전송 없음 — 순서 보존). 항목이 성공하면
/// sent에 담고 다음으로, 실패하면 그 항목(과 그 뒤로 아직 시도 안 한 나머지)을 remaining에 그대로
/// 남기고 즉시 멈춘다 — 뒤 항목을 먼저 보내면 순서가 깨지고, 실패한 항목을 버리면 메시지가
/// 유실된다. sendFn이 던지는 경우도 실패로 동일하게 취급한다(이미 성공한 앞쪽 sent 는 보존).
Future<FlushQueueResult> flushChatMessageQueue(
  List<QueuedChatMessage> queue,
  Future<SendMessageResult> Function(QueuedChatMessage msg) sendFn,
) async {
  final sent = <ChatMessage>[];
  for (var i = 0; i < queue.length; i++) {
    SendMessageResult res;
    try {
      res = await sendFn(queue[i]);
    } catch (e) {
      // ignore: avoid_print
      print('[chat] 큐 flush 중 전송 예외: $e');
      return FlushQueueResult(remaining: queue.sublist(i), sent: sent);
    }
    switch (res) {
      case SendMessageSuccess(:final message):
        sent.add(message);
      case SendMessageFailure():
        return FlushQueueResult(remaining: queue.sublist(i), sent: sent);
    }
  }
  return FlushQueueResult(remaining: const [], sent: sent);
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
