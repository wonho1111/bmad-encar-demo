// 업로더가 다루는 사진 항목의 **타입과 순수 변환 함수만** 두는 모듈.
// web `web/src/app/(user)/sell/photo-item.ts` + `lib/images/order.ts` + `lib/images/validate.ts`의
// 미러(코드맵이 파일을 photo_item.dart 하나로 지정해 세 web 파일의 순수 함수를 여기 모았다 —
// 셋 다 DOM·Supabase 없이 배열/값만 다루는 소규모 순수 함수라 새 파일로 쪼갤 이유가 없다, A2).
//
// 이 파일은 화면(위젯) 의존이 없다 — 위젯 트리 없이도(순수 함수) 단위테스트할 수 있다.
import 'package:image_picker/image_picker.dart';

/// 매물당 사진 상한. 정본: docs/conventions.md §10.
const int maxPhotos = 10;

/// 허용 확장자(§10 MIME 3종의 클라 1차 방어 — 실제 재인코딩 후 저장 포맷은 photo_resize.dart가
/// 결정하므로, 여기서는 "픽커가 고른 원본이 그럴듯한 이미지인가"만 값싸게 거른다).
const Set<String> allowedImageExtensions = {'jpg', 'jpeg', 'png', 'webp'};

/// 원본 파일 용량 상한 5MB. 버킷 file_size_limit과 같아야 한다(정본: conventions §10).
const int maxImageBytes = 5 * 1024 * 1024;

/// 업로드 진행·실패는 **이 화면 인스턴스의 로컬 상태일 뿐**이고 wire(DB·JSON)로 나가지 않는다.
/// web PhotoStatus와 동일 3값 — 'uploading'이 없는 이유도 동일하다(업로드는 제출 시점에 한 번에
/// 일어나 사진 한 장씩의 진행 표시가 나올 자리가 없다).
enum PhotoStatus { idle, uploaded, error }

/// 업로더 항목 하나(기존 저장 사진 또는 새로 고른 사진).
class PhotoItem {
  const PhotoItem({
    required this.key,
    this.previewUrl,
    this.status = PhotoStatus.idle,
    this.error,
    this.retryable = false,
    this.file,
    this.storagePath,
    this.rowId,
  });

  /// 목록 key 겸 항목 식별자(재배치해도 위젯이 튀지 않도록 안정적이어야 한다).
  final String key;

  /// 화면에 그릴 미리보기. 기존 사진은 공개 버킷 URL(고정), 새로 고른 사진은 로컬 파일 경로
  /// (`file!.path`) — web의 objectURL 자리에 해당한다. 소비처는 `file != null` 로 두 경우를
  /// 가른다(`Image.network` vs `Image.file`).
  final String? previewUrl;

  final PhotoStatus status;

  /// 인라인 오류 사유(한국어). status==uploaded 가 아닐 때만 채운다.
  final String? error;

  /// 다시 시도해볼 만한 실패인가. 용량초과·포맷 거부는 재시도해도 같은 결과라 false.
  final bool retryable;

  /// 새로 고른 파일(아직 Storage에 없음). 기존 사진이면 null.
  final XFile? file;

  /// 이미 저장된 사진의 Storage 경로. 새 사진은 업로드 성공 후 채워진다.
  final String? storagePath;

  /// 이미 저장된 사진의 listing_images 행 id.
  final String? rowId;
}

/// 새로 고른 로컬 항목의 key 생성기. Dart는 단일 isolate라 web처럼 "서버·브라우저 두 런타임이
/// 각자 다른 카운터를 가져 key가 충돌"하는 문제(photo-item.ts 주석 참조)가 구조적으로 없다 —
/// 그래도 재배치·재생성에 안정적인 값이 필요해 타임스탬프+카운터로 충돌을 피한다.
int _localKeySeq = 0;
String nextLocalPhotoKey() =>
    'photo-local-${DateTime.now().microsecondsSinceEpoch}-${_localKeySeq++}';

/// 서버가 내려준 기존 사진 원행 → 업로더 항목. 수정 화면 진입 시 `listing_images` 조회 후 호출한다
/// (web toPhotoItems 미러). 계약 위반 행(경로 없음 등)은 조용히 건너뛴다(§10.2와 동일 방어 원칙).
List<PhotoItem> toPhotoItems(
  List<Map<String, dynamic>> rows,
  String Function(String path) buildUrl,
) {
  final result = <PhotoItem>[];
  for (final r in rows) {
    final id = r['id'];
    final path = r['storage_path'];
    if (id is! String || path is! String || path.trim().isEmpty) continue;
    result.add(
      PhotoItem(
        key: 'photo-row-$id',
        previewUrl: buildUrl(path),
        status: PhotoStatus.uploaded,
        storagePath: path,
        rowId: id,
      ),
    );
  }
  return result;
}

/// 검증 결과 — 성공(ok)이면 통과, 실패면 사용자에게 그대로 보여줄 한국어 사유.
class PickValidation {
  const PickValidation.ok() : ok = true, reason = null;
  const PickValidation.error(this.reason) : ok = false;

  final bool ok;
  final String? reason;
}

/// 파일명에서 확장자를 뽑는다(소문자, 점 제외). 없으면 빈 문자열.
String _extensionOf(String path) {
  final dot = path.lastIndexOf('.');
  if (dot < 0 || dot == path.length - 1) return '';
  return path.substring(dot + 1).toLowerCase();
}

/// 새로 고른 파일 1장을 검증한다 — **UX 층의 1차 방어**일 뿐, 실제 강제는 서버(버킷
/// file_size_limit·allowed_mime_types, 0012)에 남는다(docs/conventions.md §10).
PickValidation validatePickedFile({required String path, required int size}) {
  if (!allowedImageExtensions.contains(_extensionOf(path))) {
    return const PickValidation.error('JPG · PNG · WebP 형식만 올릴 수 있어요.');
  }
  if (size <= 0) {
    return const PickValidation.error('빈 파일이에요. 다른 사진을 선택해주세요.');
  }
  if (size > maxImageBytes) {
    return const PickValidation.error('장당 최대 5MB까지 올릴 수 있어요.');
  }
  return const PickValidation.ok();
}

// ── 순서 계산 — 배열만 다루는 순수 함수 (web lib/images/order.ts 미러) ────────────
//
// ⚠️ 대표를 계산하는 함수가 여기 없는 것은 의도다. 대표 = 배열 0번이다. 대표를 별도 상태로
// 두면 순서와 대표가 각각 움직여 진실이 두 군데 생긴다 — "대표로 지정"은 moveToFront(0번으로
// 이동)라는 순서 조작 하나로만 표현한다. DB의 is_cover는 이 규칙의 파생 결과다(photo_sync.dart).

bool _inRange(List<Object?> items, int i) => i >= 0 && i < items.length;

/// index 항목을 제거한다. 0번(대표)을 지우면 다음 장이 0번이 되어 자동으로 대표가 승격된다.
List<PhotoItem> removePhotoAt(List<PhotoItem> items, int index) {
  if (!_inRange(items, index)) return List.of(items);
  return [...items.sublist(0, index), ...items.sublist(index + 1)];
}

/// from 위치 항목을 to 위치로 옮긴다(드래그·재배치). 나머지 상대 순서는 보존된다.
List<PhotoItem> reorderPhotos(List<PhotoItem> items, int from, int to) {
  if (!_inRange(items, from) || !_inRange(items, to)) return List.of(items);
  final next = List.of(items);
  final moved = next.removeAt(from);
  next.insert(to, moved);
  return next;
}

/// index 항목을 맨 앞으로 옮긴다 = [대표로] 버튼의 동작. reorderPhotos(items, index, 0)과 동일.
List<PhotoItem> moveToFront(List<PhotoItem> items, int index) =>
    reorderPhotos(items, index, 0);
