// 수정 모드 무한 리빌드 루프 회귀 테스트 — sell_screen.dart의 build()는 `sell.success != null`
// 이면 addPostFrameCallback을 예약해 컨트롤러 결과를 화면 로컬 상태(_photos/_baseline)로
// 병합한다. **수정(edit) 모드에서 사진 처리 일부가 실패하면**(sell_controller.dart 의 edit
// 분기가 success + error + photos 를 채우고 done 은 false 로 둔다) 이 콜백이 조건 없이
// setState를 부르면: setState → 리빌드 → success 는 그대로 → 콜백 재예약 → setState … 로
// 프레임이 끝없이 돈다(review 발견). 지금은 `!identical(incoming, _photos)`일 때만 setState해
// 한 번 병합한 뒤 스스로 멈춘다 — 이 검사가 그 가드를 고정한다.
//
// 셋업은 sell_screen_photo_test.dart(SellScreen 통째 마운트, currentUserProvider 오버라이드)와
// sell_controller_test.dart(전역 Supabase 싱글턴에 가짜 http 클라이언트를 물려 submit()의 실제
// 배선을 태우는 패턴)을 합친 것이다. listingsRepositoryProvider는 오버라이드하지 않고 기본값
// (전역 supabase 싱글턴)을 그대로 쓴다 — 그래야 updateListing과 syncListingPhotos가 같은 가짜
// http로 나가 화면→컨트롤러→레포→photo_sync 전체 배선이 실제로 도는 상태에서 루프를 재현한다.
//
// 사진 실패를 만드는 방법(과제 지시 힌트대로): listing_images PATCH(sort_order 갱신)에 0행을
// 돌려준다 — syncListingPhotos가 '사진 순서를 저장하지 못한 항목이 있어요' warning을 만들고,
// 컨트롤러가 success(매물 정보 자체는 저장됨) + error(그 warning) + done:false 로 상태를 채운다
// (photo_sync.dart 3단계 주석 참조).
//
// ⚠️ 이 검사가 안 보는 것: 실제 무한루프가 CPU를 어떻게 태우는지(그건 안 보여도 된다) —
// pumpAndSettle이 "더 예약된 프레임이 없다"를 확인하지 못해 타임아웃 예외로 실패하는 것 자체가
// red 신호다(CLAUDE.md B4, "루프가 있으면 pumpAndSettle이 timeout으로 실패한다").
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/listing.dart';
import 'package:app/features/listings/photo_item.dart';
import 'package:app/features/listings/sell_screen.dart';

/// listings PATCH(매물 정보 수정)는 1행 성공을 돌려준다. listing_images PATCH(사진 순서
/// 갱신·대표 리셋)는 전부 기본값(빈 배열=0행)을 돌려줘 사진 처리 일부 실패를 흉내낸다
/// (photo_sync.dart의 '사진 순서를 저장하지 못한 항목이 있어요' 경로).
class _FakeHttpClient extends http.BaseClient {
  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final path = request.url.path;
    Object body = <dynamic>[]; // 기본값: 0행 — listing_images PATCH가 이걸 그대로 받는다.
    if (request.method == 'PATCH' &&
        path.contains('/rest/v1/listings') &&
        !path.contains('listing_images')) {
      body = [
        {'id': 'listing-1'},
      ];
    }
    final bytes = utf8.encode(jsonEncode(body));
    return http.StreamedResponse(
      Stream.value(bytes),
      200,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

User _fakeUser() => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'seller@test.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

/// 본인 on_sale 매물 상세 — sell_controller_test.dart의 `_validInput`과 같은 값을 쓴다
/// (ListingOptions 드롭다운 목록 안 값임이 이미 그 테스트로 보장돼 있다).
ListingDetail _onSaleDetail() => ListingDetail(
  id: 'listing-1',
  sellerId: _fakeUser().id,
  manufacturer: '현대',
  model: '아반떼',
  bodyType: '준중형차',
  year: 2021,
  price: 20000000,
  mileage: 10000,
  color: '흰색',
  fuel: '가솔린',
  transmission: '자동',
  displacement: 1600,
  seats: 5,
  region: '서울',
  accidentFree: true,
  status: 'on_sale',
);

/// 이미 저장된 사진 1장(수정 화면 진입 시 edit_listing_screen.dart가 넘기는 형태).
const _savedPhoto = PhotoItem(
  key: 'row-0',
  previewUrl: 'https://cdn.test/0.webp',
  status: PhotoStatus.uploaded,
  storagePath: 'u/listing-1/0.webp',
  rowId: 'row-0',
);

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
      httpClient: _FakeHttpClient(),
    );
  });

  testWidgets(
    '수정 모드에서 사진 처리 일부가 실패해도(done:false) pumpAndSettle이 타임아웃 없이 끝나고 '
    '사진 실패 안내가 뜬다(무한 리빌드 루프 회귀, review 발견)',
    (tester) async {
      final container = ProviderContainer(
        overrides: [currentUserProvider.overrideWithValue(_fakeUser())],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            home: SellScreen(
              editDetail: _onSaleDetail(),
              initialPhotos: const [_savedPhoto],
            ),
          ),
        ),
      );
      // initState의 startEdit() postFrameCallback을 흘려보낸다(컨트롤러에 수정 모드 반영).
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.byKey(const Key('sell_submit')));
      await tester.tap(find.byKey(const Key('sell_submit')));

      // 루프가 있으면 여기서 "더 예약된 프레임이 없다"에 도달하지 못해 timeout으로 실패한다
      // (red) — 그게 이 검사의 목적이다. 가드가 살아 있으면 한 번의 병합 setState 뒤 스스로
      // 멈춰 정상 종료한다(green).
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('sell_error')),
        findsOneWidget,
        reason: '사진 처리 실패 안내(에러 배너)가 화면에 남아야 한다',
      );
      expect(
        find.textContaining('사진 처리 중 일부가 실패했어요'),
        findsOneWidget,
      );
    },
  );

  testWidgets(
    '사진 처리 일부 실패 배너가 시킨 복구(삭제 후 재시도)를 하면 다음 프레임이 되돌리지 않는다'
    '(review 발견, spec-16-7 후속 리뷰 patch — 예전엔 `!identical(incoming, _photos)` 가드가 '
    '삭제로 만들어진 새 리스트를 컨트롤러의 옛 사진 리스트로 한 프레임 뒤에 덮어썼다)',
    (tester) async {
      final container = ProviderContainer(
        overrides: [currentUserProvider.overrideWithValue(_fakeUser())],
      );
      addTearDown(container.dispose);

      await tester.pumpWidget(
        UncontrolledProviderScope(
          container: container,
          child: MaterialApp(
            home: SellScreen(
              editDetail: _onSaleDetail(),
              initialPhotos: const [_savedPhoto],
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.ensureVisible(find.byKey(const Key('sell_submit')));
      await tester.tap(find.byKey(const Key('sell_submit')));
      await tester.pumpAndSettle();

      // 사전조건: 위 테스트와 같은 부분 실패 상태 — row-0이 아직 화면에 남아 있다.
      expect(find.byKey(const Key('photo_item_row-0')), findsOneWidget);

      // 에러 배너가 시킨 복구 동작 — 문제의 사진을 지우고 다시 저장을 시도한다.
      await tester.ensureVisible(find.byKey(const Key('photo_remove_row-0')));
      await tester.tap(find.byKey(const Key('photo_remove_row-0')));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const Key('photo_item_row-0')),
        findsNothing,
        reason:
            '삭제가 한 프레임 뒤에 되돌아오면 안 된다 — 되돌아오면 배너가 시킨 복구 동작 자체를 '
            '사용자가 빠져나갈 수 없다',
      );
    },
  );
}
