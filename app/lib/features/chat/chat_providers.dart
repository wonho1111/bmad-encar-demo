// 채팅 Riverpod providers — 레포 1개 공유 + 목록·방헤더 비동기 조회.
//   메시지 송수신·폴링은 화면(ChatRoomScreen)이 StatefulWidget 으로 타이머·커서를 직접 쥔다
//   (web ChatRoomMessages 가 컴포넌트 상태로 setInterval·cursor 를 보유한 패턴과 동형).
//   여기 providers 는 "한 번 읽고 끝나는" 목록/헤더 조회만 담당한다.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'chat_models.dart';
import 'chat_repository.dart';

/// 레포지토리 단일 인스턴스(전역 supabase 클라이언트 사용).
final chatRepositoryProvider = Provider<ChatRepository>((ref) {
  return ChatRepository();
});

/// 내 채팅방 목록 — autoDispose: 목록 화면을 닫으면 캐시를 버려 재진입 시 최신을 다시 읽는다.
final chatRoomsProvider =
    FutureProvider.autoDispose<List<ChatRoomSummary>>((ref) async {
  final repo = ref.watch(chatRepositoryProvider);
  return repo.fetchRooms();
});

/// 방 1건(헤더·상대표기·매물상세 링크용). roomId 별 family + autoDispose.
final chatRoomDetailProvider =
    FutureProvider.autoDispose.family<ChatRoomSummary?, String>((ref, roomId) async {
  final repo = ref.watch(chatRepositoryProvider);
  return repo.fetchRoom(roomId);
});
