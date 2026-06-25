// 채팅 데이터 모델 — 메시지(chat_messages)와 채팅방 요약(chat_rooms+임베드 매물).
// web ChatMessageRow(lib/messages.ts)·ChatRoomRow/Detail(chat/page.tsx) 미러.
// 통신선/컬럼은 snake_case 그대로 읽는다(변환 없음, AR5). 사진 없음.
//
// fromMap 가드(listing.dart 패턴): 필수 필드가 깨졌으면 null 을 돌려 그 원소를 버린다 —
//   렌더 도중 터지는 것을 막는다(web 의 isValidListing 런타임 가드와 같은 목적).

/// 숫자 필드 안전 변환(listing.dart 의 _asInt 와 동일). int/double/문자열 흡수, 실패 시 null.
int? _asInt(Object? v) {
  if (v == null) return null;
  if (v is int) return v;
  if (v is double) return v.toInt();
  if (v is num) return v.toInt();
  if (v is String) return int.tryParse(v.trim());
  return null;
}

/// 메시지 1건. created_at 은 ISO 문자열(timestamptz) 그대로 — 폴링 커서로 문자열 비교에 쓴다.
///   (web ChatMessageRow 와 동일 계약: id·room_id·sender_id·body·created_at)
class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.roomId,
    required this.senderId,
    required this.body,
    required this.createdAt,
  });

  final String id;
  final String roomId;
  final String senderId;
  final String body;
  final String createdAt; // ISO 문자열. 시간순 정렬·gte 커서 비교에 문자열 그대로 사용(ISO 는 사전식=시간순).

  /// Supabase row(Map) → 메시지. 5필드가 올바른 문자열이 아니면 null(깨진 행 제외).
  static ChatMessage? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final roomId = raw['room_id'];
    final senderId = raw['sender_id'];
    final body = raw['body'];
    final createdAt = raw['created_at'];

    if (id is! String ||
        roomId is! String ||
        senderId is! String ||
        body is! String ||
        createdAt is! String) {
      return null;
    }
    return ChatMessage(
      id: id,
      roomId: roomId,
      senderId: senderId,
      body: body,
      createdAt: createdAt,
    );
  }
}

/// 채팅방에 임베드된 매물 요약(목록·헤더 표시용). web ChatRoomRow.listings 미러.
///   임베드가 null(판매완료 sold·구매자 RLS상 조회불가)이면 ChatRoomSummary.listing 이 null 이 되고,
///   화면은 "판매 완료되었거나 조회할 수 없는 매물" 플레이스홀더를 보인다(FR11 — 구매자에게 sold 비노출).
class ChatRoomListing {
  const ChatRoomListing({
    required this.manufacturer,
    required this.model,
    required this.year,
    required this.price,
    required this.status,
  });

  final String manufacturer;
  final String model;
  final int year;
  final int price; // 원(KRW)
  final String status; // on_sale / sold

  static ChatRoomListing? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final manufacturer = raw['manufacturer'];
    final model = raw['model'];
    final status = raw['status'];
    final year = _asInt(raw['year']);
    final price = _asInt(raw['price']);
    if (manufacturer is! String ||
        model is! String ||
        status is! String ||
        year == null ||
        price == null) {
      return null;
    }
    return ChatRoomListing(
      manufacturer: manufacturer,
      model: model,
      year: year,
      price: price,
      status: status,
    );
  }
}

/// 채팅방 요약(목록·방 헤더). web ChatRoomRow/ChatRoomDetail 미러.
///   buyer_name/seller_name = 이메일 @앞부분(0008 비정규화). 앱은 읽기만(조인·재계산 금지).
///   상대 표기는 화면이 "내가 buyer 인지"로 정한다(iAmBuyer ? seller_name : buyer_name).
class ChatRoomSummary {
  const ChatRoomSummary({
    required this.id,
    required this.listingId,
    required this.buyerId,
    required this.sellerId,
    this.buyerName,
    this.sellerName,
    this.listing,
  });

  final String id;
  final String listingId;
  final String buyerId;
  final String sellerId;
  final String? buyerName; // 구매자 표시 이름(0008). 없으면(예전 방) 역할만 폴백.
  final String? sellerName; // 판매자 표시 이름(0008).
  final ChatRoomListing? listing; // 임베드 매물. null=sold/조회불가 → 플레이스홀더.

  static ChatRoomSummary? fromMap(Object? raw) {
    if (raw is! Map) return null;
    final id = raw['id'];
    final listingId = raw['listing_id'];
    final buyerId = raw['buyer_id'];
    final sellerId = raw['seller_id'];
    if (id is! String ||
        listingId is! String ||
        buyerId is! String ||
        sellerId is! String) {
      return null;
    }
    final buyerName = raw['buyer_name'];
    final sellerName = raw['seller_name'];
    return ChatRoomSummary(
      id: id,
      listingId: listingId,
      buyerId: buyerId,
      sellerId: sellerId,
      buyerName: buyerName is String ? buyerName : null,
      sellerName: sellerName is String ? sellerName : null,
      // listings 임베드는 PostgREST 가 단일 객체로 준다(FK 단방향). null/리스트형 모두 방어.
      listing: ChatRoomListing.fromMap(raw['listings']),
    );
  }
}
