// 채팅 Riverpod providers — 레포 1개 공유 + 목록·방헤더·안읽음 배지 비동기 조회.
//   메시지 송수신·실시간 구독·재연결 큐는 화면(ChatRoomScreen)이 StatefulWidget 으로 채널·큐·
//   커서를 직접 쥔다(web ChatRoomMessages 가 컴포넌트 상태로 채널·pendingQueue 를 보유한 패턴과
//   동형, Design Notes — Dart State 필드는 React ref 미러링이 필요 없다).
//   여기 providers 는 "한 번 읽고 끝나는" 목록/헤더/배지 조회만 담당한다.
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

/// 채팅 탭 아이콘 안읽음 총합(§12.6) — non-autoDispose: 하단 내비 셸(`_AppShell`)이 항상 살아있는
/// 자리에서 이 값을 그리므로, 목록 화면을 열고 닫는 것과 수명이 다르다(autoDispose 로 두면 채팅
/// 탭 밖에서 캐시가 버려져 배지가 깜빡인다). `app_router.dart`의 탭 onActivate 가 명시 무효화한다.
final chatUnreadTotalProvider = FutureProvider<int>((ref) async {
  final repo = ref.watch(chatRepositoryProvider);
  return repo.fetchUnreadTotal();
});

/// 채팅 목록 각 행의 방별 안읽음(DW-548, §12.6) — autoDispose: 목록 화면에서만 쓰는 값이라
/// chatRoomsProvider 와 같은 수명으로 둔다.
final chatUnreadByRoomProvider = FutureProvider.autoDispose<Map<String, int>>((ref) async {
  final repo = ref.watch(chatRepositoryProvider);
  return repo.fetchUnreadByRoom();
});
