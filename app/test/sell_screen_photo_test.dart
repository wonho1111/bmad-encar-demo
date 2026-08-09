// 매물 등록 화면의 사진 업로더 위젯테스트(Story 16.7, UX-DR13) — 추가/삭제/정원/오류표시·재시도를
// 다룬다. 재배치는 [대표로] 버튼 경로로 확인한다(길게 눌러 끄는 실제 드래그 제스처는 타이밍이
// 얽혀 위젯테스트로 안정적으로 재현하기 어렵다 — `photo_item.dart`의 `reorderPhotos`/`moveToFront`
// 순수 함수 자체는 그 로직을 이미 구현·사용하고 있고, [대표로] 버튼이 그 함수를 호출한다).
//
// SellScreen을 통째로 마운트한다(`sell_screen_test.dart`와 같은 셋업 — 실 네트워크로 나가지
// 않도록 ListingsRepository의 쓰기 메서드만 가짜로 갈아 끼운다). 실제 카메라/갤러리 접근은
// `ImagePickerPlatform.instance`를 가짜로 교체해 피한다(플랫폼 채널 없이 위젯 트리만 구동).
//
// ⚠️ 이 검사가 **안 보는 것**: 실제 기기의 카메라/갤러리 권한 요청 UI, 실제 리사이즈 인코딩
// (flutter_image_compress 플랫폼 채널) — 둘 다 위젯테스트가 닿지 않는 영역이다(스토리
// Verification의 "Manual checks" 항목 참조).
import 'dart:typed_data';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker_platform_interface/image_picker_platform_interface.dart';
import 'package:plugin_platform_interface/plugin_platform_interface.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'package:app/features/auth/auth_controller.dart';
import 'package:app/features/listings/listings_providers.dart';
import 'package:app/features/listings/listings_repository.dart';
import 'package:app/features/listings/photo_item.dart';
import 'package:app/features/listings/sell_screen.dart';

/// 쓰기 두 경로를 가로채는 가짜 레포 — 실제 네트워크로 나가지 않는다(sell_screen_test.dart 동일 패턴).
class _RecordingRepo extends ListingsRepository {
  @override
  Future<String> createListing(
    Map<String, dynamic> payload, {
    required String sellerId,
  }) async => 'listing-id';

  @override
  Future<int> updateListing(String id, Map<String, dynamic> payload) async => 1;
}

/// 갤러리/카메라 피커를 가짜로 갈아 끼운다 — 플랫폼 채널 없이 원하는 파일 목록을 즉시 돌려준다.
class _FakeImagePickerPlatform extends ImagePickerPlatform with MockPlatformInterfaceMixin {
  List<XFile> multiImages = [];
  XFile? singleImage;

  @override
  Future<List<XFile>> getMultiImageWithOptions({
    MultiImagePickerOptions options = const MultiImagePickerOptions(),
  }) async => multiImages;

  @override
  Future<XFile?> getImageFromSource({
    required ImageSource source,
    ImagePickerOptions options = const ImagePickerOptions(),
  }) async => singleImage;
}

/// 실제 파일시스템 없이 만드는 XFile — 매물당 5MB 이하 JPG로 검증을 통과시킨다.
/// ⚠️ `path:`를 반드시 준다 — `validatePickedFile`은 확장자를 **경로**에서 판정한다(실제
/// image_picker가 돌려주는 XFile은 항상 실 파일 경로를 갖는다). `path` 없이 `XFile.fromData`만
/// 쓰면 빈 경로가 되어 "포맷 거부"로 잘못 분류된다.
XFile _fakeImage(String name, {int bytes = 100}) => XFile.fromData(
  Uint8List.fromList(List.filled(bytes, 0)),
  path: '/tmp/$name.jpg',
  name: '$name.jpg',
  mimeType: 'image/jpeg',
);

User _fakeUser() => User(
  id: '00000000-0000-0000-0000-000000000001',
  appMetadata: const {},
  userMetadata: const {},
  aud: 'authenticated',
  email: 'seller@test.com',
  createdAt: DateTime.utc(2026, 1, 1).toIso8601String(),
);

/// 이미 저장된 사진 N장(수정 화면 진입 상황을 흉내낼 때 씀).
List<PhotoItem> _savedPhotos(int n) => List.generate(
  n,
  (i) => PhotoItem(
    key: 'row-$i',
    previewUrl: 'https://cdn.test/$i.webp',
    status: PhotoStatus.uploaded,
    storagePath: 'u/l/$i.webp',
    rowId: 'row-$i',
  ),
);

Future<void> _pumpSellScreen(
  WidgetTester tester, {
  List<PhotoItem> initialPhotos = const [],
}) async {
  final container = ProviderContainer(
    overrides: [
      listingsRepositoryProvider.overrideWithValue(_RecordingRepo()),
      currentUserProvider.overrideWithValue(_fakeUser()),
    ],
  );
  addTearDown(container.dispose);

  await tester.pumpWidget(
    UncontrolledProviderScope(
      container: container,
      child: MaterialApp(
        home: SellScreen(showAppBar: false, initialPhotos: initialPhotos),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  late _FakeImagePickerPlatform fakePicker;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    await Supabase.initialize(
      url: 'https://example.supabase.co',
      // ignore: deprecated_member_use
      anonKey: 'test-anon-key-not-real',
    );
  });

  setUp(() {
    fakePicker = _FakeImagePickerPlatform();
    ImagePickerPlatform.instance = fakePicker;
  });

  testWidgets('사진 0장 — "0/10" 카운터와 안내 문구가 보인다', (tester) async {
    await _pumpSellScreen(tester);
    await tester.ensureVisible(find.byKey(const Key('photo_count')));

    expect(find.text('0/10'), findsOneWidget);
    expect(find.text('사진은 선택이에요. 없어도 등록되지만, 있으면 문의가 훨씬 잘 와요.'), findsOneWidget);
  });

  testWidgets('갤러리에서 2장을 고르면 목록에 추가되고 카운터가 올라간다(AC1)', (tester) async {
    fakePicker.multiImages = [_fakeImage('a'), _fakeImage('b')];

    await _pumpSellScreen(tester);
    await tester.ensureVisible(find.byKey(const Key('photo_add_button')));
    await tester.tap(find.byKey(const Key('photo_add_button')));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('photo_pick_gallery')));
    await tester.pumpAndSettle();

    expect(find.text('2/10'), findsOneWidget);
  });

  testWidgets('10장이 이미 있으면 "+" 버튼이 사라진다(정원 게이트, AC 매트릭스 "10장 초과")', (
    tester,
  ) async {
    await _pumpSellScreen(tester, initialPhotos: _savedPhotos(10));
    await tester.ensureVisible(find.byKey(const Key('photo_count')));

    expect(find.text('10/10'), findsOneWidget);
    expect(find.byKey(const Key('photo_add_button')), findsNothing);
  });

  testWidgets('이미 8장 있는데 5장을 더 고르면 2장만 받고 초과 안내가 뜬다(I/O 매트릭스)', (
    tester,
  ) async {
    fakePicker.multiImages = [
      _fakeImage('a'), _fakeImage('b'), _fakeImage('c'), _fakeImage('d'), _fakeImage('e'),
    ];

    await _pumpSellScreen(tester, initialPhotos: _savedPhotos(8));
    // 두 겹의 스크롤을 순서대로 다룬다: 바깥(세로, 폼 전체) 먼저 photo_scroll 자체를 뷰포트
    // 안으로 들여온 뒤 — 그래야 dragUntilVisible이 그 스크롤 위젯의 중심 좌표를 잴 수 있다 —
    // 안쪽(가로, 썸네일 목록)의 "+"는 8장이면 캐시 범위 밖이라 아직 엘리먼트 트리에 없다(sliver
    // lazy build) — ensureVisible은 "이미 트리에 있는 것"만 스크롤하므로 안쪽엔 안 통한다.
    await tester.ensureVisible(find.byKey(const Key('photo_scroll')));
    await tester.dragUntilVisible(
      find.byKey(const Key('photo_add_button')),
      find.byKey(const Key('photo_scroll')),
      const Offset(-200, 0),
    );
    // dragUntilVisible이 멈춘 시점엔 관성(fling) 애니메이션이 아직 안 끝났을 수 있다 — 그 상태로
    // 좌표를 재면 실제 렌더 위치와 어긋난다(실측: hit-test 경고). 완전히 멈춘 뒤에 탭한다.
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('photo_add_button')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('photo_pick_gallery')));
    await tester.pumpAndSettle();

    expect(find.text('10/10'), findsOneWidget, reason: '방(room)=2장만 받아 정원을 채운다');
    expect(
      find.textContaining('3장은 제외했어요'),
      findsOneWidget,
      reason: '나머지 3장은 제외됐다는 안내가 화면에 남아야 한다(AC3)',
    );
  });

  testWidgets('삭제 버튼을 누르면 그 항목이 사라지고 카운터가 줄어든다', (tester) async {
    await _pumpSellScreen(tester, initialPhotos: _savedPhotos(2));
    await tester.ensureVisible(find.byKey(const Key('photo_count')));
    expect(find.text('2/10'), findsOneWidget);

    await tester.tap(find.byKey(const Key('photo_remove_row-0')));
    await tester.pumpAndSettle();

    expect(find.text('1/10'), findsOneWidget);
    expect(find.byKey(const Key('photo_item_row-0')), findsNothing);
    expect(find.byKey(const Key('photo_item_row-1')), findsOneWidget);
  });

  testWidgets('0번(대표) 사진을 지우면 다음 사진이 자동으로 대표가 된다(AC3 — 대표=0번 파생값)', (
    tester,
  ) async {
    await _pumpSellScreen(tester, initialPhotos: _savedPhotos(2));
    await tester.ensureVisible(find.byKey(const Key('photo_item_row-1')));
    // 대표 배지가 0번(row-0)에만 있다 — [대표로] 버튼은 대표가 아닌 항목에만 뜬다.
    expect(find.byKey(const Key('photo_make_cover_row-0')), findsNothing);
    expect(find.byKey(const Key('photo_make_cover_row-1')), findsOneWidget);

    await tester.tap(find.byKey(const Key('photo_remove_row-0')));
    await tester.pumpAndSettle();

    // row-1이 이제 유일한(=0번) 항목이라 [대표로] 버튼이 사라진다(자기 자신이 이미 대표).
    expect(find.byKey(const Key('photo_make_cover_row-1')), findsNothing);
  });

  testWidgets('[대표로]를 누르면 그 사진이 맨 앞으로 온다(재배치 진입점 ②, moveToFront)', (
    tester,
  ) async {
    await _pumpSellScreen(tester, initialPhotos: _savedPhotos(3));
    await tester.ensureVisible(find.byKey(const Key('photo_make_cover_row-2')));

    await tester.tap(find.byKey(const Key('photo_make_cover_row-2')));
    await tester.pumpAndSettle();

    // row-2가 새 0번(대표)이 됐으므로 이제 [대표로] 버튼이 없다 — row-0에는 생겼다.
    expect(find.byKey(const Key('photo_make_cover_row-2')), findsNothing);
    expect(find.byKey(const Key('photo_make_cover_row-0')), findsOneWidget);
  });

  testWidgets('업로드 실패(재시도 가능) 항목은 인라인 오류 + 재시도 버튼을 보여준다(AC3)', (
    tester,
  ) async {
    final failed = PhotoItem(
      key: 'k-fail',
      previewUrl: '/tmp/fail.jpg',
      status: PhotoStatus.error,
      error: '사진을 올리지 못했어요. 다시 시도해주세요.',
      retryable: true,
      file: _fakeImage('fail'),
    );
    await _pumpSellScreen(tester, initialPhotos: [failed]);
    await tester.ensureVisible(find.byKey(const Key('photo_error_k-fail')));

    expect(find.text('사진을 올리지 못했어요. 다시 시도해주세요.'), findsOneWidget);
    expect(find.byKey(const Key('photo_retry_k-fail')), findsOneWidget);

    await tester.tap(find.byKey(const Key('photo_retry_k-fail')));
    await tester.pumpAndSettle();

    // 재시도는 로컬 상태만 idle로 되돌린다 — 실제 재업로드는 다음 제출에서 일어난다(Design Notes).
    expect(find.byKey(const Key('photo_error_k-fail')), findsNothing);
    expect(find.byKey(const Key('photo_retry_k-fail')), findsNothing);
  });

  testWidgets('용량초과·포맷거부(재시도 불가) 항목은 재시도 버튼이 없다', (tester) async {
    const rejected = PhotoItem(
      key: 'k-big',
      status: PhotoStatus.error,
      error: '장당 최대 5MB까지 올릴 수 있어요.',
      retryable: false,
    );
    await _pumpSellScreen(tester, initialPhotos: [rejected]);
    await tester.ensureVisible(find.byKey(const Key('photo_error_k-big')));

    expect(find.text('장당 최대 5MB까지 올릴 수 있어요.'), findsOneWidget);
    expect(find.byKey(const Key('photo_retry_k-big')), findsNothing);
    // 거부된 항목은 정원 계산에서 빠진다(storagePath 없음 + retryable:false).
    expect(find.text('0/10'), findsOneWidget);
  });
}
