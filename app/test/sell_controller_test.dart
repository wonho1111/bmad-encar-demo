// SellController 수명 버그 회귀 방지 — spec-16-1 Design Notes "브랜치 영구 마운트 ↔
// autoDispose provider 수명 충돌"(review_loop_iteration 1, bug #2, high 심각도).
//
// ⚠️ 이 파일은 spec-16-1 Code Map이 명시한 신규 테스트 파일 목록(app_router_test.dart·
// current_role_provider_test.dart)에는 없다. 그래도 추가한 이유: 스토리 Verification의
// "채택 전 red 확인 #2"(등록이 UPDATE로 새는지)가 데이터 손상 버그를 다루는데, 이 계약을
// 위젯 트리(15필드 폼을 채우는 SellScreen)로 검증하면 무겁고 흔들리기 쉽다 — 컨트롤러를
// 직접 구동하는 편이 더 빠르고 안정적이며(CLAUDE.md A2), 이 버그의 근본 원인이 SellController
// 하나에 있다(CLAUDE.md B4: "검사를 만들면 일부러 깨서 red 확인 → 되돌려 green 확인"을
// 실행하기에도 이 층이 적합하다).
//
// 무엇이 문제였나: sellControllerProvider는 autoDispose이고 "화면이 닫히면 상태를 버린다"는
// 계약을 갖고 있었다(sell_controller.dart 주석). 그런데 하단 4탭 셸의 '/sell' 브랜치가
// IndexedStack으로 영구 마운트되면서 그 계약이 무력화됐다 — 수정 화면에서 startEdit()로
// 세팅된 state.editingId가 등록 화면으로 돌아와도 안 지워진다. submit()이
// `editingIdOverride ?? state.editingId`로 폴백했기 때문에, 등록 버튼을 눌러도 새 매물이
// INSERT되는 대신 직전 수정 대상 매물이 UPDATE로 새는 사고가 실측 확인됐다.
//
// 고치는 방향은 provider 수명을 되살리는 게 아니라(브랜치 영구 마운트는 유지해야 탭 상태
// 보존이 되므로), submit()이 state.editingId 폴백을 아예 안 하게(호출부 명시만 신뢰) 만드는
// 쪽이다 — 이 검사가 그 계약을 고정한다.
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/listing_form.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/photo_item.dart';
import 'package:app/features/listings/sell_controller.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

/// submit()이 내부에서 부르는 syncListingPhotos는 client를 명시하지 않고 전역 `supabase`
/// 싱글턴을 쓴다(sell_controller.dart 미주입) — 이 파일이 원래 Supabase.initialize를 피했던
/// 이유(파일 상단 주석)와 같은 자리다. "submit()이 실제 사진과 함께 호출됐을 때 배선이
/// 맞는지"(review 발견, verification-gap)를 보려면 그 전역 싱글턴에 가짜 http를 물려야 한다 —
/// sell_screen_photo_test.dart와 같은 패턴을 여기 최소한으로 들여온다.
class _FakeHttpClient extends http.BaseClient {
  final List<http.BaseRequest> requests = [];

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    requests.add(request);
    final bytes = utf8.encode(
      jsonEncode([
        {'id': 'row-x'},
      ]),
    );
    return http.StreamedResponse(
      Stream.value(bytes),
      200,
      request: request,
      headers: {'content-type': 'application/json', 'content-length': '${bytes.length}'},
    );
  }
}

/// createListing/updateListing 호출을 기록하는 가짜 레포 — 네트워크 없이 동작.
///
/// `ListingsRepository()`의 기본 생성자는 인자가 없으면 전역 `supabase` 게터(=
/// `Supabase.instance.client`)를 읽는데, 이 파일은 `Supabase.initialize`를 호출하지
/// 않는다(app_router_test.dart와 달리 이 테스트는 라우터·화면 없이 컨트롤러만 구동하므로
/// 그럴 필요가 없다 — CLAUDE.md A2). 그래서 `SupabaseClient`를 직접 새로 만들어(전역
/// 싱글턴을 건드리지 않는다) 넘긴다 — 어차피 createListing/updateListing을 오버라이드해
/// 실제로 이 클라이언트로 네트워크를 타지 않는다.
class _RecordingRepo extends ListingsRepository {
  _RecordingRepo()
    : this._own(
        SupabaseClient('https://example.supabase.co', 'test-anon-key-not-real'),
      );

  _RecordingRepo._own(this.client) : super(client: client);

  /// 이 레포 하나만을 위해 만든 더미 클라이언트 — 생성만 해도 GoTrue 세션 갱신 타이머가
  /// 시작된다. 예전엔 만들고 버려 dispose가 안 됐다(테스트가 끝나도 타이머가 살아있었다,
  /// review, spec-16-1 P11) — 이제 각 테스트가 `addTearDown(repo.client.dispose)`로 정리한다.
  final SupabaseClient client;

  final createCalls = <Map<String, dynamic>>[];
  final updateCalls = <String>[];

  @override
  Future<String> createListing(
    Map<String, dynamic> payload, {
    required String sellerId,
  }) async {
    createCalls.add(payload);
    return 'created-listing-id';
  }

  @override
  Future<int> updateListing(String id, Map<String, dynamic> payload) async {
    updateCalls.add(id);
    return 1;
  }
}

const _validInput = ListingFormInput(
  manufacturer: '현대',
  model: '아반떼',
  bodyType: '준중형차',
  year: '2021',
  price: '20000000',
  mileage: '10000',
  color: '흰색',
  fuel: '가솔린',
  transmission: '자동',
  displacement: '1600',
  seats: '5',
  region: '서울',
);

User _fakeUser() => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'seller@test.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

ProviderContainer _container(_RecordingRepo repo) {
  final container = ProviderContainer(
    overrides: [
      listingsRepositoryProvider.overrideWithValue(repo),
      currentUserProvider.overrideWithValue(_fakeUser()),
    ],
  );
  return container;
}

void main() {
  late _FakeHttpClient fakeHttp;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    fakeHttp = _FakeHttpClient();
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
      httpClient: fakeHttp,
    );
  });

  test('submit()은 state.editingId로 폴백하지 않는다 — 브랜치 영구 마운트로 남은 leftover '
      'state가 다음 등록에 새지 않는다(회귀: 직전엔 새 등록이 UPDATE로 샜다)', () async {
    final repo = _RecordingRepo();
    addTearDown(repo.client.dispose);
    final container = _container(repo);
    addTearDown(container.dispose);

    final notifier = container.read(sellControllerProvider.notifier);

    // 1) 수정 화면 방문을 흉내낸다 — startEdit()가 state.editingId를 남긴다(브랜치
    //    영구 마운트로 이 provider 인스턴스가 안 죽고 살아남는 상황의 재현).
    notifier.startEdit('listing-EDIT', _validInput);

    // 2) 등록 화면(/sell 탭)으로 돌아와 새 매물을 입력하고 제출한다. 등록 모드이므로
    //    editingId를 명시적으로 null 전달한다 — SellScreen._submit()의 실제 관례
    //    (editingId: widget.editDetail?.id, editDetail==null → null)를 그대로 재현한다.
    notifier.updateInput(_validInput);
    await notifier.submit(editingId: null);

    expect(
      repo.createCalls,
      hasLength(1),
      reason: '등록 모드로 명시했으면 INSERT가 일어나야 한다',
    );
    expect(
      repo.updateCalls,
      isEmpty,
      reason:
          '직전 수정 대상(listing-EDIT)이 새어 UPDATE로 가면 안 된다 — '
          '이게 실측된 데이터 손상 버그였다',
    );
  });

  test('editingId를 명시하면(수정 모드) UPDATE가 그 id로 간다 — 정상 수정 경로는 안 깨졌다', () async {
    final repo = _RecordingRepo();
    addTearDown(repo.client.dispose);
    final container = _container(repo);
    addTearDown(container.dispose);

    final notifier = container.read(sellControllerProvider.notifier);
    notifier.updateInput(_validInput);
    await notifier.submit(editingId: 'listing-EDIT');

    expect(repo.updateCalls, ['listing-EDIT']);
    expect(repo.createCalls, isEmpty);
  });

  test(
    'submit()이 실제 사진과 함께 호출되면 syncListingPhotos로 올바로 배선되고 결과가 '
    'state.photos에 병합된다(review 발견 — 부품은 테스트됐지만 이 배선 자체는 미검증이었다)',
    () async {
      fakeHttp.requests.clear();
      final repo = _RecordingRepo();
      addTearDown(repo.client.dispose);
      final container = _container(repo);
      addTearDown(container.dispose);

      final notifier = container.read(sellControllerProvider.notifier);
      notifier.updateInput(_validInput);

      // storagePath가 이미 있는(=저장된) 사진이라 실제 업로드/리사이즈(플랫폼 채널) 없이
      // sort_order 갱신 경로만 거친다 — 이 테스트가 보려는 건 배선(누구의 id로, 어느
      // listing_images에 요청이 나가는지)이지 리사이즈/업로드 자체(그건 photo_resize_test.dart·
      // photo_sync_test.dart가 이미 담당)가 아니다.
      final kept = PhotoItem(
        key: 'k-kept',
        previewUrl: 'https://cdn.test/kept',
        status: PhotoStatus.uploaded,
        storagePath: '${_fakeUser().id}/listing-EDIT/kept.webp',
        rowId: 'row-kept',
      );

      await notifier.submit(editingId: 'listing-EDIT', photos: [kept], baseline: [kept]);

      expect(repo.updateCalls, ['listing-EDIT']);
      expect(
        fakeHttp.requests.any(
          (r) =>
              r.method == 'PATCH' &&
              r.url.path.contains('listing_images') &&
              r.url.queryParameters['listing_id'] == 'eq.listing-EDIT',
        ),
        isTrue,
        reason:
            'syncListingPhotos가 실제로 호출돼 listing_images에 요청이 나갔어야 하고, '
            '그 listing_id가 수정 대상(listing-EDIT)과 같아야 한다',
      );

      final state = container.read(sellControllerProvider);
      expect(state.photos, isNotNull, reason: 'PhotoSyncResult.photos가 state로 병합돼야 한다');
      expect(state.photos!.single.key, 'k-kept');
      expect(state.error, isNull, reason: '실패 없이 끝났으면 에러가 남으면 안 된다');
    },
  );

  test(
    'submit()이 등록(신규) 모드로 사진과 함께 호출되면 createListing이 돌려준 id로 '
    'syncListingPhotos가 호출된다(review 발견 — 등록 분기를 태우는 배선 테스트가 0건이었다. '
    'syncListingPhotos(userId, listingId, ...)는 앞 두 인자가 둘 다 String이라 뒤바꿔도 '
    '컴파일되므로, 실제 요청에 실린 listing_id로 확인한다)',
    () async {
      fakeHttp.requests.clear();
      final repo = _RecordingRepo();
      addTearDown(repo.client.dispose);
      final container = _container(repo);
      addTearDown(container.dispose);

      final notifier = container.read(sellControllerProvider.notifier);
      notifier.updateInput(_validInput);

      // uploadFn/resizeFn 없이(파일피커·플랫폼 채널 없이) 배선만 보려면, sell_controller_test.dart의
      // 다른 테스트와 같이 "이미 저장된 사진"으로 취급되는 항목을 넘긴다 — 그러면 syncListingPhotos는
      // 업로드를 건너뛰고 sort_order 갱신 + 대표(is_cover) 재계산 단계로 가는데, 대표 재계산 단계가
      // `.eq('listing_id', listingId)`로 쏘는 요청이 있어 그 쿼리파라미터로 인자 배선을 확인할 수 있다.
      final kept = PhotoItem(
        key: 'k-kept',
        previewUrl: 'https://cdn.test/kept',
        status: PhotoStatus.uploaded,
        storagePath: '${_fakeUser().id}/created-listing-id/kept.webp',
        rowId: 'row-kept',
      );

      await notifier.submit(editingId: null, photos: [kept], baseline: const []);

      expect(repo.createCalls, hasLength(1), reason: '등록 모드이므로 INSERT가 일어나야 한다');
      expect(repo.updateCalls, isEmpty);

      expect(
        fakeHttp.requests.any(
          (r) =>
              r.method == 'PATCH' &&
              r.url.path.contains('listing_images') &&
              r.url.queryParameters['listing_id'] == 'eq.created-listing-id',
        ),
        isTrue,
        reason:
            'syncListingPhotos가 createListing이 돌려준 id(created-listing-id)로 불렸어야 한다 — '
            'userId/listingId 인자가 뒤바뀌면(둘 다 String이라 컴파일은 통과) 여기 listing_id가 '
            'user id로 새어 나온다',
      );

      final state = container.read(sellControllerProvider);
      expect(state.error, isNull, reason: '실패 없이 끝났으면 에러가 남으면 안 된다');
      expect(state.success, contains('매물이 등록되었습니다'));
    },
  );
}
