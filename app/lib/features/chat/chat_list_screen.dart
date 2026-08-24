// 문의 채팅방 목록(FR19 재현) — 내가 당사자인 방만 최신순. web (user)/chat/page.tsx 이식.
//   RLS(chat_rooms_select_participant)가 내 방만 통과(별도 필터 불필요). 각 행: 매물 요약 + 상대 표기.
//   매물 임베드 null(sold·조회불가)이면 플레이스홀더(FR11). 빈 상태는 역할별 분기.
//
// ⚠️ **셸 경계(spec-16-1)**: 방 하나를 여는 push는 `rootNavigator: true`로 셸 밖으로
//   보낸다 — 이 화면이 셸 브랜치 루트로 쓰일 때 그 push가 브랜치 안에 남으면 셸
//   AppBar·NavigationBar가 방 화면 위에 그대로 남는다.
//   ⚠️ **spec-16-8로 진입점이 하나로 줄었다**(후속 코드리뷰 spec-16-8 2차 리뷰 P8 확인,
//   `grep -rn 'ChatListScreen(' app/lib`) — 지금 이 화면을 만드는 자리는 하단 4탭 셸의
//   '채팅' 브랜치 루트(`app_router.dart`, `showAppBar: false` — 셸이 이미 공통 AppBar를
//   그린다) 하나뿐이다. 예전엔 `home_screen.dart`의 "문의 채팅" 퀵액션도 이 화면을
//   `showAppBar: true`(기본값)로 단독으로 열었으나, 그 퀵액션은 spec-16-8에서 제거됐다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format/number_format.dart';
import '../../core/theme/app_theme.dart';
import '../auth/auth_controller.dart';
import 'chat_models.dart';
import 'chat_providers.dart';
import 'chat_room_screen.dart';

class ChatListScreen extends ConsumerWidget {
  const ChatListScreen({super.key, this.showAppBar = true});

  /// 하단 4탭 셸의 '채팅' 브랜치 루트로 쓰일 때는 셸이 이미 공통 AppBar(제목+프로필
  /// 아바타)를 그리므로 이 화면 자신의 AppBar를 끈다(app_router.dart가 false로 넘긴다).
  /// 기본값 true지만, 지금 그 기본값을 실제로 쓰는 진입점은 없다(위 셸 경계 주석 참조 —
  /// 홈의 "문의 채팅" 퀵액션은 spec-16-8에서 제거됐다). 단독 화면으로 여는 진입점이 다시
  /// 생기면 뒤로가기가 있는 자기 AppBar가 필요하므로 기본값을 true로 남겨 둔다.
  final bool showAppBar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final roomsAsync = ref.watch(chatRoomsProvider);
    // 전역 `supabase` 싱글턴을 직접 읽지 않고 currentUserProvider를 거친다 — 이 한 줄 때문에
    // 위젯 테스트가 이 화면을 렌더하려면 실제 `Supabase.initialize`가 필요했고,
    // shared_preferences가 dev 의존으로 승격돼 있었다(spec-16-1 Task).
    final myId = ref.watch(currentUserProvider)?.id;
    // 방별 안읽음 배지(DW-548, docs/conventions.md §12.6) — RPC 실패는 빈 Map으로 폴백돼 있으므로
    // (chat_repository.dart) 여기서는 "없으면 0"으로만 읽는다. 렌더 자체를 막지 않는다.
    final unreadByRoom = ref.watch(chatUnreadByRoomProvider).maybeWhen(
      data: (m) => m,
      orElse: () => const <String, int>{},
    );

    return Scaffold(
      appBar: showAppBar ? AppBar(title: const Text('문의 채팅')) : null,
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
            // 역할 통합(FR52·FR53) 이후 빈 상태 문구는 **역할 중립**이다.
            // 옛 코드는 판매자/구매자로 문구를 갈랐는데, 이제 한 계정이 양쪽을 다 하므로
            // 어느 쪽으로 갈라도 절반은 틀린 안내가 된다. 두 경로를 함께 적는다.
            const msg =
                '아직 채팅방이 없습니다. 매물 상세에서 ‘문의하기’를 누르거나, '
                '내 매물에 문의가 들어오면 여기에 생깁니다.';
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
              // 하단 패딩: `viewPadding.bottom`이 아니라 `MediaQuery.paddingOf(context).bottom`을
              // 쓴다 — 탭 루트로 쓰일 때 셸의 NavigationBar가 이미 그 시스템 인셋을 흡수하므로,
              // 원본 viewPadding을 또 더하면 하단 여백이 이중으로 커진다(spec-16-1 Task —
              // home_screen.dart·sell_screen.dart와 같은 규칙. 세 탭 루트가 같아야 한다).
              padding: EdgeInsets.fromLTRB(
                12,
                12,
                12,
                12 + MediaQuery.paddingOf(context).bottom,
              ),
              itemCount: rooms.length,
              separatorBuilder: (_, _) => const SizedBox(height: 8),
              itemBuilder: (context, i) => _RoomTile(
                room: rooms[i],
                myId: myId,
                unread: unreadByRoom[rooms[i].id] ?? 0,
              ),
            ),
          );
        },
      ),
    );
  }
}

class _RoomTile extends StatelessWidget {
  const _RoomTile({
    required this.room,
    required this.myId,
    required this.unread,
  });

  final ChatRoomSummary room;
  final String? myId;

  // ✎ 2026-08-10 — `final WidgetRef ref;` 필드를 제거했다. 방을 닫고 돌아왔을 때 무효화하는
  //   용도였는데, 폐기된 ref를 비동기 콜백에서 쓰는 것이 바로 아래 onTap 주석의 결함이었다.
  //   이제 `ProviderScope.containerOf`로 그 자리에서 잡으므로 이 필드는 쓰이지 않는다.

  /// 이 방의 안읽음 메시지 수(DW-548) — 0이면 배지를 그리지 않는다.
  final int unread;

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
      color: AppColors.surfaceRaised,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(10),
        side: const BorderSide(color: AppColors.borderHairline),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(10),
        // 셸 브랜치 루트로 쓰일 때 여기서 방을 열면 브랜치 Navigator에 쌓이지 않도록
        // rootNavigator: true로 셸 밖에 쌓는다(위 파일 헤더 주석 참조).
        //
        // 방을 열고 돌아오면(pop) chatRoomsProvider를 무효화한다(home_screen.dart의
        // 퀵액션 push와 동일 패턴) — 채팅 탭 재진입(app_router.dart의 NavigationBar
        // onDestinationSelected)만 무효화를 걸어뒀더니, 실제로 가장 흔한 경로인 "채팅 탭 →
        // 방 열기 → 뒤로가기"는 안 잡혀 읽지 않음 카운터·최근 메시지가 방을 나와도 갱신되지
        // 않았다(review, spec-16-1 P2).
        //
        // chatUnreadByRoomProvider(목록 배지)·chatUnreadTotalProvider(내비 배지)도 함께
        // 무효화한다(Story 16.4 코드리뷰 patch 2) — 위 spec-16-1 P2가 고친 건 chatRoomsProvider
        // 뿐이었는데, 이 스토리가 새로 추가한 두 안읽음 provider는 같은 pop-back 경로에서
        // 다시 그 버그 클래스를 물려받았다: 방에서 markRoomRead가 끝나고 돌아와도 이미 채팅
        // 탭에 있으므로 app_router.dart의 탭 onActivate(재진입 트리거)가 다시 안 불려 배지가
        // 그대로 남는다(§12.6 "다음 진입 시점에 그만큼 줄어든다" 위반).
        //
        // ⚠️ **`.then()` 안에서 `ref`를 쓰지 않는다 — push 전에 컨테이너를 미리 잡는다.**
        // (2026-08-10 Epic 16 묶음 코드리뷰, 리뷰어 2명이 독립 발견)
        // 방을 열어 둔 채 로그아웃되거나 세션이 만료되면 라우터 redirect가 `_AppShell`을
        // 통째로 갈아치우고, 그 뒤 도착한 pop이 **이미 폐기된** `ref`로 invalidate를 부른다.
        // 그러면 flutter_riverpod 3.3.2의 `_assertNotDisposed()`가 unmounted element에 대해
        // 진짜 `StateError`를 던진다 — assert가 아니라 **모든 빌드 모드에서**.
        // `_RoomTile`은 `StatelessWidget`이라 `if (!mounted) return` 가드를 쓸 수도 없다.
        // 이 리포는 같은 실패를 `app_router.dart`의 `_ProfileAvatarButton`(내 매물 관리 push)
        // 에서 이미 겪고 `ProviderScope.containerOf`로 고쳤는데, 이 자리만 그 교훈을 안
        // 물려받고 있었다. 같은 해법을 그대로 쓴다 — 컨테이너는 위젯 생명주기와 무관하다.
        onTap: () {
          final container = ProviderScope.containerOf(context, listen: false);
          Navigator.of(context, rootNavigator: true)
              .push(
                MaterialPageRoute(
                  builder: (_) => ChatRoomScreen(roomId: room.id),
                ),
              )
              .then((_) {
                container.invalidate(chatRoomsProvider);
                container.invalidate(chatUnreadByRoomProvider);
                container.invalidate(chatUnreadTotalProvider);
              });
        },
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
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  color: AppColors.inkPrimary,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                wonText(l.price),
                                style: const TextStyle(
                                  fontWeight: FontWeight.w700,
                                  fontSize: 15,
                                  color: AppColors.inkPrimary,
                                ),
                              ),
                            ],
                          )
                        : const Text(
                            '판매 완료되었거나 조회할 수 없는 매물',
                            style: TextStyle(
                              fontWeight: FontWeight.w600,
                              color: AppColors.inkMuted,
                            ),
                          ),
                  ),
                  const SizedBox(width: 8),
                  // 방별 안읽음 배지(DW-548, §12.6) — 0건이면 그리지 않는다. 색+숫자를 함께
                  // 표기하고(비색 신호 중복), 시각 상한("99+")과 스크린리더 낭독(정확한 건수)을
                  // 분리한다(app_router.dart의 내비 총합 배지와 같은 규칙).
                  if (unread > 0)
                    Padding(
                      padding: const EdgeInsets.only(right: 4),
                      child: Semantics(
                        label: '안읽음 메시지 $unread건',
                        child: ExcludeSemantics(
                          child: Badge(
                            backgroundColor: AppColors.danger,
                            textColor: Colors.white,
                            label: Text(unread > 99 ? '99+' : '$unread'),
                          ),
                        ),
                      ),
                    ),
                  const Icon(Icons.chevron_right, color: AppColors.inkMuted),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                counter,
                style: const TextStyle(
                  color: AppColors.inkMuted,
                  fontSize: 12.5,
                ),
              ),
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
