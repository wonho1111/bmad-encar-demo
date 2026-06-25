// 문의 채팅방 목록(FR19 재현) — 내가 당사자인 방만 최신순. web (user)/chat/page.tsx 이식.
//   RLS(chat_rooms_select_participant)가 내 방만 통과(별도 필터 불필요). 각 행: 매물 요약 + 상대 표기.
//   매물 임베드 null(sold·조회불가)이면 플레이스홀더(FR11). 빈 상태는 역할별 분기.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format/number_format.dart';
import '../../core/supabase/supabase_client.dart';
import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import '../auth/user_role.dart';
import 'chat_models.dart';
import 'chat_providers.dart';
import 'chat_room_screen.dart';

class ChatListScreen extends ConsumerWidget {
  const ChatListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final roomsAsync = ref.watch(chatRoomsProvider);
    final role = ref.watch(currentRoleProvider);
    final myId = supabase.auth.currentUser?.id;

    return Scaffold(
      appBar: AppBar(title: const Text('문의 채팅')),
      body: roomsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        // 조회 실패 — "없음"과 구분해 빨강 에러(목록이 사라진 것처럼 오인 방지).
        error: (e, _) => const _CenterMessage(
          key: Key('chat_list_error'),
          icon: Icons.error_outline,
          color: Colors.red,
          message: '채팅방 목록을 불러오지 못했습니다. 잠시 후 다시 시도해주세요.',
        ),
        data: (rooms) {
          if (rooms.isEmpty) {
            // 역할별 빈 상태(구매자: 먼저 문의 / 판매자: 받는 입장).
            final msg = role == UserRole.seller
                ? '아직 들어온 문의가 없습니다. 구매자가 매물에 문의하면 여기에 채팅방이 생깁니다.'
                : '아직 문의한 채팅방이 없습니다. 매물 상세에서 ‘문의하기’를 눌러보세요.';
            return _CenterMessage(
              key: const Key('chat_list_empty'),
              icon: Icons.chat_bubble_outline,
              color: Colors.grey,
              message: msg,
            );
          }
          return RefreshIndicator(
            onRefresh: () async => ref.refresh(chatRoomsProvider.future),
            child: ListView.separated(
              // 하단 패딩에 시스템 내비바 높이를 더해(edge-to-edge) 마지막 항목이 가리지 않게.
              padding: EdgeInsets.fromLTRB(
                  12, 12, 12, 12 + MediaQuery.of(context).viewPadding.bottom),
              itemCount: rooms.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, i) =>
                  _RoomTile(room: rooms[i], myId: myId),
            ),
          );
        },
      ),
    );
  }
}

class _RoomTile extends StatelessWidget {
  const _RoomTile({required this.room, required this.myId});

  final ChatRoomSummary room;
  final String? myId;

  @override
  Widget build(BuildContext context) {
    // 내가 구매자면 상대는 판매자(이름), 판매자면 상대는 구매자(이름). 한 방엔 정확히 두 당사자.
    final iAmBuyer = myId != null && myId == room.buyerId;
    final counterName = iAmBuyer ? room.sellerName : room.buyerName;
    final counter = iAmBuyer
        ? (counterName != null ? '판매자 $counterName에게 문의' : '판매자에게 문의')
        : (counterName != null ? '구매자 $counterName 문의' : '구매자 문의');

    final l = room.listing;

    return Card(
      margin: EdgeInsets.zero,
      elevation: 0,
      color: Colors.white,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.border),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ChatRoomScreen(roomId: room.id)),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // 매물 카드와 동일한 다단 구조 — 제목(제조사·모델·연식) / 가격(별행). 길어도 안 무너짐.
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(
                    // 임베드 null = 판매완료(sold)·조회불가 → 플레이스홀더만(FR11).
                    child: l != null
                        ? Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '[${l.manufacturer}] ${l.model} · ${l.year}년',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600,
                                    color: AppColors.ink2),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                wonText(l.price),
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 15,
                                    color: AppColors.ink2),
                              ),
                            ],
                          )
                        : const Text(
                            '판매 완료되었거나 조회할 수 없는 매물',
                            style: TextStyle(
                                fontWeight: FontWeight.w600,
                                color: AppColors.muted),
                          ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(Icons.chevron_right, color: AppColors.muted),
                ],
              ),
              const SizedBox(height: 6),
              Text(counter,
                  style: const TextStyle(color: AppColors.muted, fontSize: 12.5)),
            ],
          ),
        ),
      ),
    );
  }
}

/// 빈 상태·에러 공통 본문(detail 화면 _MessageBody 톤).
class _CenterMessage extends StatelessWidget {
  const _CenterMessage({
    super.key,
    required this.icon,
    required this.color,
    required this.message,
  });

  final IconData icon;
  final Color color;
  final String message;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 48, color: color),
            const SizedBox(height: 16),
            Text(message, textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }
}
