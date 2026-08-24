# Epic 12 Context: 실시간 문의 채팅

<!-- Generated from planning artifacts. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Buyer-seller inquiry chat moves from polling to realtime: messages appear instantly, a reconnect banner keeps users typing/sending through network drops with no message loss (gap-fill on reconnect), duplicate sends are prevented by an idempotency key, and sellers get unread badges + recency-sorted room lists so they stop missing inquiries. This is the epic's core value: today sellers can silently miss buyer messages because chat only polls every few seconds. The existing three-layer chat integrity (RLS, insert trigger enforcing seller identity, message-length/participant CHECK constraints) must keep working unchanged through the transition.

## Stories

- Story 12.1: 멱등키 마이그레이션 (idempotency key column + constraint)
- Story 12.2: Realtime Broadcast + 참가자 인가 RLS
- Story 12.3: 실시간 송수신 전환 (폴링 제거)
- Story 12.4: 재연결 배너 + 갭 보정
- Story 12.5: 안읽음 배지 + 방 목록 정렬
- Story 12.6: 실시간 채팅 검증 (SM-E, 수동 2-브라우저)

## Requirements & Constraints

- Covers: realtime delivery replacing polling, duplicate-send prevention via idempotency key, non-blocking reconnect banner with lossless gap-fill, unread badge + room-list recency sort, and revised requirements confirming messages stay DB-persisted (not transport-only).
- The existing chat integrity triad — RLS, the insert trigger that forces the correct sender identity, and the length/participant CHECK constraints — must survive the realtime transition unregressed; this is verified, not assumed.
- Every new migration in this epic must take the next unused number under `supabase/migrations/` at kickoff time (recount, don't hardcode a number) and must be self-contained: it may only depend on lower-numbered migrations or create its own idempotent guard, never assume a higher-numbered migration ran first. A CI migration-order gate enforces this.
- Status changes must be signaled non-color-only: reconnect success = color change + explicit text, unread = dot + numeral text (not color alone).
- The realtime send/receive and reconnect-recovery success metric is verified manually with two browser sessions (buyer + seller), not by an automated check.

## Technical Decisions

- Transport is Supabase's "Broadcast from Database" pattern: a DB trigger broadcasts row changes into a private Realtime channel; the chat messages table itself stays the unchanged source of truth, with broadcast as a layer on top of it.
- One topic/event/payload contract is shared identically by three places — the DB trigger, the Realtime authorization policy, and the client subscription — using the room's actual identifier column. Any mismatch between the three silently breaks auth or delivery, so all three must be changed together.
- The client parses the inserted-row payload out of the broadcast envelope and renders in `created_at` + row-id order (not arrival order, since broadcast delivery order isn't guaranteed).
- Realtime authorization is enforced by a policy that parses the channel topic and checks the requester is actually the buyer or seller of that room (private channel + client-side auth handshake required) — this is the security-critical checkpoint for who can receive which room's messages.
- Idempotency: the client generates a random id per message and sends it; a uniqueness constraint on (room, that id) plus "ignore on conflict" makes duplicate sends a no-op. This must coexist with the existing sender-identity trigger and length CHECK without side effects — verified by inserting the same key twice and confirming exactly one row lands with no extra trigger effects.
- Reconnect gap-fill: prefer the Realtime replay buffer (bounded, recent-window only) first; anything older falls back to a direct query using an inclusive "at or after last-seen timestamp" cursor (not strict-after, because same-timestamp messages would otherwise be skipped), deduplicated by the idempotency key.
- Sends are optimistic: a pending bubble shows immediately, then reconciles against the server-confirmed row via the idempotency key.
- Unread tracking uses a per-user, per-room "last read" timestamp; unread count/badge = messages newer than that timestamp sent by someone other than the current user (own messages never count as unread). The timestamp updates on room entry/view.
- New wire fields follow the project-wide snake_case convention for anything crossing the web/api/app boundary.

## UX & Interaction Patterns

- Reconnect banner is non-blocking: while disconnected, users can keep typing and sending (queued locally) with copy like "connection dropped, reconnecting… you can keep writing"; on success it briefly turns green with confirming text, then disappears.
- Unread badge lives on the chat entry point in navigation (dot + numeral), and the room list itself sorts by most recent inquiry first.
- (Pre-existing, unchanged by this epic) inquiry entry point swaps to a "manage my listing" affordance instead of "inquire" when viewing one's own listing.

## Cross-Story Dependencies

- 12.3 (realtime send/receive) depends on 12.1's idempotency constraint and 12.2's broadcast/authorization plumbing both being in place first.
- 12.4 (reconnect banner + gap-fill) builds directly on 12.3's live subscription — it has nothing to attach to otherwise.
- 12.5 (unread badges) reads from the same message stream 12.3 establishes, so it should land after realtime send/receive is stable.
- 12.3 also carries a standing ledger item: the chat message input overflows horizontally on narrow mobile viewports, a known duplicate of a fix already applied elsewhere in the app. Story 12.3's acceptance criteria already require applying that same fix here and extending the viewport-audit end-to-end test to include the chat room screen — this is a planted obligation, not optional cleanup.
- 12.6 is a manual verification pass across all of 12.1–12.5 (not new build work) and is the story that closes out the epic's realtime-chat success metric.
