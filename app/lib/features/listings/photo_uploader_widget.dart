// 매물 사진 업로더 UI(AC1·AC2·AC3·AC6, UX-DR13) — 등록·수정 폼(sell_screen.dart)이 공유한다.
// web `PhotoUploader.tsx`의 네이티브 피커 버전 — 웹의 드롭존 대신 "+"(카메라/갤러리 바텀시트),
// 웹의 마우스 드래그 대신 길게 눌러 옮기는 재배치(LongPressDraggable)를 쓴다.
//
// **이 위젯은 파일을 직접 올리지 않는다.** 선택·순서·삭제·표시만 하고, 실제 업로드는 폼 제출
// 시점에 sell_controller.dart가 한다(AC5 — 신규 등록은 listing_id가 생기기 전엔 올릴 곳이 없다).
//
// **대표 = 배열 0번**이다. [대표로] 버튼은 moveToFront(0번으로 이동) 하나만 호출한다 —
// 순서와 대표를 각각 두면 진실이 두 군데 생긴다(photo_item.dart 주석과 동일 원칙).
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';

import '../../core/theme/app_theme.dart';
import 'photo_item.dart';

class PhotoUploaderWidget extends StatefulWidget {
  const PhotoUploaderWidget({
    super.key,
    required this.items,
    required this.onChanged,
    this.disabled = false,
  });

  final List<PhotoItem> items;
  final ValueChanged<List<PhotoItem>> onChanged;

  /// 제출 중에는 조작을 막는다(업로드가 진행 중인 목록을 흔들면 결과가 어긋난다).
  final bool disabled;

  @override
  State<PhotoUploaderWidget> createState() => _PhotoUploaderWidgetState();
}

class _PhotoUploaderWidgetState extends State<PhotoUploaderWidget> {
  final _picker = ImagePicker();

  /// 파일 선택 자체가 거부된 경우(10장 초과)는 특정 항목에 붙일 수 없어 목록 위에 한 줄로 알린다.
  String? _pickError;

  /// 검증 실패(용량초과·포맷거부)로 애초에 업로드된 적 없는 항목 — 목록엔 남기지만(AC3) 저장될
  /// 사진이 아니므로 정원(N/10) 계산에서는 뺀다. storagePath가 있으면(=한 번이라도 저장된 적
  /// 있는 사진) status가 error여도 여기서 빼지 않는다 — 실제로 자리를 차지하는 사진이라서다.
  bool _isRejected(PhotoItem p) =>
      p.status == PhotoStatus.error && !p.retryable && p.storagePath == null;

  int _acceptedCount() => widget.items.where((p) => !_isRejected(p)).length;

  Future<void> _addFiles(List<XFile> files) async {
    if (files.isEmpty) return;

    final room = maxPhotos - _acceptedCount();
    final accepted = files.take(room < 0 ? 0 : room).toList();

    final next = <PhotoItem>[];
    for (final file in accepted) {
      final size = await file.length();
      final verdict = validatePickedFile(path: file.path, size: size);
      next.add(
        verdict.ok
            ? PhotoItem(key: nextLocalPhotoKey(), previewUrl: file.path, file: file)
            : PhotoItem(
                key: nextLocalPhotoKey(),
                previewUrl: null,
                status: PhotoStatus.error,
                error: verdict.reason,
                retryable: false,
                file: file,
              ),
      );
    }

    if (!mounted) return;
    setState(() {
      _pickError = files.length > accepted.length
          ? '사진은 최대 $maxPhotos장까지 올릴 수 있어요. ${files.length - accepted.length}장은 제외했어요.'
          : null;
    });
    widget.onChanged([...widget.items, ...next]);
  }

  Future<void> _pickFromCamera() async {
    final file = await _picker.pickImage(source: ImageSource.camera);
    if (file != null) await _addFiles([file]);
  }

  Future<void> _pickFromGallery() async {
    final room = maxPhotos - _acceptedCount();
    if (room <= 0) return;
    // 시스템 포토피커라 별도 권한이 필요 없다(AndroidManifest.xml 주석). limit보다 더 고르면
    // 시스템 피커가 알아서 자르지 않는 기기도 있어, 넉넉히 받고 _addFiles가 정원으로 다시 자른다.
    final files = await _picker.pickMultiImage();
    await _addFiles(files);
  }

  void _openPickerSheet() {
    if (widget.disabled || _acceptedCount() >= maxPhotos) return;
    showModalBottomSheet<void>(
      context: context,
      builder: (sheetContext) => SafeArea(
        child: Wrap(
          children: [
            ListTile(
              key: const Key('photo_pick_camera'),
              leading: const Icon(Icons.photo_camera_outlined),
              title: const Text('카메라로 촬영'),
              onTap: () {
                Navigator.of(sheetContext).pop();
                _pickFromCamera();
              },
            ),
            ListTile(
              key: const Key('photo_pick_gallery'),
              leading: const Icon(Icons.photo_library_outlined),
              title: const Text('갤러리에서 선택'),
              onTap: () {
                Navigator.of(sheetContext).pop();
                _pickFromGallery();
              },
            ),
          ],
        ),
      ),
    );
  }

  void _remove(int index) {
    setState(() => _pickError = null);
    widget.onChanged(removePhotoAt(widget.items, index));
  }

  void _retry(int index) {
    final items = widget.items;
    final p = items[index];
    // 다시 대기 상태로만 되돌린다 — 실제 재업로드는 다음 제출에서 일어난다(Design Notes).
    final reset = PhotoItem(
      key: p.key,
      previewUrl: p.previewUrl,
      file: p.file,
      storagePath: p.storagePath,
      rowId: p.rowId,
    );
    widget.onChanged([
      for (var i = 0; i < items.length; i++) if (i == index) reset else items[i],
    ]);
  }

  void _makeCover(int index) => widget.onChanged(moveToFront(widget.items, index));

  @override
  Widget build(BuildContext context) {
    final items = widget.items;
    final count = _acceptedCount();
    final full = count >= maxPhotos;
    // 대표 배지·[대표로]가 가리켜야 할 실제 위치 — photo_sync.dart가 대표를 거는 대상과 같은
    // 술어(거부되지 않은 첫 항목)로 골라야 화면과 DB가 갈리지 않는다.
    final firstSavableIndex = items.indexWhere((p) => !_isRejected(p));

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            const Text('사진', style: TextStyle(fontWeight: FontWeight.w600)),
            Text(
              '$count/$maxPhotos',
              key: const Key('photo_count'),
              style: const TextStyle(color: AppColors.inkMuted),
            ),
          ],
        ),
        const SizedBox(height: 8),
        SizedBox(
          // 88(썸네일) + 아래 한 줄(대표로 **또는** 오류문구+재시도, 최대 두 줄)의 여유.
          // 오류 상태(문구 최대 2줄 + 재시도 버튼)가 가장 큰 경우라 108로는 부족했다(실측 오버플로).
          height: 140,
          child: ListView(
            key: const Key('photo_scroll'),
            scrollDirection: Axis.horizontal,
            children: [
              for (var i = 0; i < items.length; i++)
                Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: _ReorderableThumb(
                    index: i,
                    item: items[i],
                    isCover: i == firstSavableIndex,
                    disabled: widget.disabled,
                    onReorder: (from, to) => widget.onChanged(reorderPhotos(items, from, to)),
                    onRemove: widget.disabled ? null : () => _remove(i),
                    onRetry: (!widget.disabled && items[i].retryable) ? () => _retry(i) : null,
                    onMakeCover:
                        (!widget.disabled && i != firstSavableIndex && items[i].status != PhotoStatus.error)
                        ? () => _makeCover(i)
                        : null,
                  ),
                ),
              if (!full)
                GestureDetector(
                  key: const Key('photo_add_button'),
                  onTap: widget.disabled ? null : _openPickerSheet,
                  child: Container(
                    width: 88,
                    height: 88,
                    decoration: BoxDecoration(
                      border: Border.all(color: AppColors.borderHairline),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.add_a_photo_outlined, color: AppColors.inkMuted),
                  ),
                ),
            ],
          ),
        ),
        if (_pickError != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              _pickError!,
              key: const Key('photo_pick_error'),
              style: const TextStyle(color: AppColors.danger, fontSize: 12),
            ),
          ),
        const SizedBox(height: 4),
        const Text(
          '사진은 선택이에요. 없어도 등록되지만, 있으면 문의가 훨씬 잘 와요.',
          style: TextStyle(fontSize: 12, color: AppColors.inkMuted),
        ),
      ],
    );
  }
}

/// 썸네일 1칸 — 미리보기 + 대표 배지 + 삭제 + (재시도 | 대표로) + 인라인 오류.
/// 길게 눌러 드래그하면 다른 칸과 위치를 바꾼다(재배치, DragTarget이 실제 순서 변경을 맡는다).
class _ReorderableThumb extends StatelessWidget {
  const _ReorderableThumb({
    required this.index,
    required this.item,
    required this.isCover,
    required this.disabled,
    required this.onReorder,
    required this.onRemove,
    required this.onRetry,
    required this.onMakeCover,
  });

  final int index;
  final PhotoItem item;
  final bool isCover;
  final bool disabled;
  final void Function(int from, int to) onReorder;
  final VoidCallback? onRemove;
  final VoidCallback? onRetry;
  final VoidCallback? onMakeCover;

  Widget _preview() {
    if (item.previewUrl == null || item.previewUrl!.isEmpty) {
      return const ColoredBox(
        color: AppColors.placeholderBg,
        child: Center(
          child: Text('미리보기 없음', style: TextStyle(fontSize: 10, color: AppColors.inkMuted)),
        ),
      );
    }
    // 기존(저장된) 사진 = 공개 URL, 새로 고른 사진 = 로컬 파일 경로.
    return item.file != null
        ? Image.file(File(item.previewUrl!), fit: BoxFit.cover)
        : Image.network(
            item.previewUrl!,
            fit: BoxFit.cover,
            errorBuilder: (context, error, stackTrace) => const ColoredBox(
              color: AppColors.placeholderBg,
              child: Center(
                child: Text('미리보기 없음', style: TextStyle(fontSize: 10, color: AppColors.inkMuted)),
              ),
            ),
          );
  }

  @override
  Widget build(BuildContext context) {
    final thumb = SizedBox(
      key: Key('photo_item_${item.key}'),
      width: 88,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 88,
            height: 88,
            child: Stack(
              fit: StackFit.expand,
              children: [
                ClipRRect(borderRadius: BorderRadius.circular(8), child: _preview()),
                if (isCover)
                  Positioned(
                    left: 4,
                    top: 4,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: AppColors.petrolDeepest.withValues(alpha: 0.85),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text(
                        '대표',
                        style: TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                if (onRemove != null)
                  Positioned(
                    right: 4,
                    top: 4,
                    child: GestureDetector(
                      key: Key('photo_remove_${item.key}'),
                      onTap: onRemove,
                      child: Container(
                        padding: const EdgeInsets.all(3),
                        decoration: BoxDecoration(
                          color: AppColors.petrolDeepest.withValues(alpha: 0.85),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: const Icon(Icons.close, color: Colors.white, size: 12),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          if (onMakeCover != null)
            TextButton(
              key: Key('photo_make_cover_${item.key}'),
              onPressed: onMakeCover,
              style: TextButton.styleFrom(
                padding: EdgeInsets.zero,
                minimumSize: const Size(0, 24),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: const Text('대표로', style: TextStyle(fontSize: 11)),
            ),
          if (item.status == PhotoStatus.error) ...[
            Text(
              item.error ?? '',
              key: Key('photo_error_${item.key}'),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: AppColors.danger, fontSize: 10),
            ),
            if (onRetry != null)
              TextButton(
                key: Key('photo_retry_${item.key}'),
                onPressed: onRetry,
                style: TextButton.styleFrom(
                padding: EdgeInsets.zero,
                minimumSize: const Size(0, 24),
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
                child: const Text('재시도', style: TextStyle(fontSize: 11)),
              ),
          ],
        ],
      ),
    );

    if (disabled) return thumb;

    return DragTarget<int>(
      onWillAcceptWithDetails: (details) => details.data != index,
      onAcceptWithDetails: (details) => onReorder(details.data, index),
      builder: (context, candidateData, rejectedData) {
        return LongPressDraggable<int>(
          data: index,
          feedback: Material(
            color: Colors.transparent,
            child: Opacity(opacity: 0.85, child: thumb),
          ),
          childWhenDragging: Opacity(opacity: 0.3, child: thumb),
          child: thumb,
        );
      },
    );
  }
}
