// 업로드 전 클라이언트 다운스케일·압축(AC4, docs/conventions.md §10.1) — web `resize.ts`의 미러.
//
// 왜 필요한가: app(Flutter)은 저장된 **원본**을 그대로 받는다(ADR-IMG-02). 리사이즈 없이 그대로
// 올리면 목록에서 여러 장 받을 때 NFR7(응답 시간)이 깨진다. 웹은 브라우저 canvas로 새 의존성
// 없이 이걸 하지만(resize.ts 주석), Dart엔 그런 내장 인코더가 없다 — 그래서 `flutter_image_compress`
// (WebP 지원)를 신규 의존성으로 들인다(이 프로젝트는 Android 전용이라 플랫폼 호환 문제는 없다).
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter_image_compress/flutter_image_compress.dart';

/// 저장본의 긴 변 상한(px). 정본: docs/conventions.md §10.1.
const int maxImageEdge = 1600;

/// WebP 인코딩 품질(정본 §10.1).
const int imageQuality = 82;

/// WebP를 못 만드는 환경에서 쓰는 JPEG 폴백 품질(정본 §10.1).
const int fallbackQuality = 85;

/// 원본 크기 → 저장본 크기. **순수 함수라 단위테스트 대상**(web `computeTargetSize` 미러).
/// 긴 변을 [maxImageEdge]에 맞추고 비율을 유지한다. 상한 이하면 억지로 키우지 않는다.
({int width, int height}) computeTargetSize(int width, int height) {
  final longest = width > height ? width : height;
  if (longest <= maxImageEdge) return (width: width, height: height);

  final scale = maxImageEdge / longest;
  // 극단 비율에서 짧은 변이 0으로 내려가지 않도록 최소 1px을 보장한다(web과 동일 방어).
  return (
    width: (width * scale).round().clamp(1, width),
    height: (height * scale).round().clamp(1, height),
  );
}

/// 재인코딩된 저장본 — 실제 인코딩 결과에 맞는 확장자·MIME을 함께 들고 다닌다(폴백 여부에 따라
/// 둘 다 달라지므로, 호출부가 따로 판정하지 않게 한 곳에서 묶는다).
class EncodedPhoto {
  const EncodedPhoto({
    required this.bytes,
    required this.extension,
    required this.mimeType,
  });

  final Uint8List bytes;
  final String extension; // 'webp' | 'jpg'
  final String mimeType; // 'image/webp' | 'image/jpeg'
}

/// 이미지 파일을 저장본 규격(긴 변 ≤[maxImageEdge]px · WebP · quality [imageQuality])으로 다시
/// 인코딩한다. WebP 인코딩이 실패하면 JPEG(quality [fallbackQuality])로 폴백한다.
///
/// `autoCorrectionAngle: true` — EXIF Orientation(폰 세로사진에 흔한 6/8)을 반영해 인코딩한다
/// (web의 `imageOrientation: 'from-image'`와 동일 목적. 없으면 90° 돌아간 채로 저장된다).
///
/// 실패(디코딩 불가·WebP·JPEG 둘 다 인코딩 실패)는 throw한다 — 호출부(photo_sync.dart)가 그
/// 사진 항목만 인라인 오류로 표시하고 폼 제출은 막지 않는다(AC3).
Future<EncodedPhoto> resizeImage(XFile file) async {
  final original = await file.readAsBytes();
  final size = await _decodeSize(original);
  final target = computeTargetSize(size.width, size.height);

  try {
    final webp = await FlutterImageCompress.compressWithList(
      original,
      minWidth: target.width,
      minHeight: target.height,
      quality: imageQuality,
      format: CompressFormat.webp,
      autoCorrectionAngle: true,
    );
    return EncodedPhoto(bytes: webp, extension: 'webp', mimeType: 'image/webp');
  } catch (_) {
    // WebP 인코딩 실패 — JPEG로 폴백한다(§10.1). 폴백도 실패하면 그 예외를 그대로 던진다.
  }

  final jpeg = await FlutterImageCompress.compressWithList(
    original,
    minWidth: target.width,
    minHeight: target.height,
    quality: fallbackQuality,
    format: CompressFormat.jpeg,
    autoCorrectionAngle: true,
  );
  return EncodedPhoto(bytes: jpeg, extension: 'jpg', mimeType: 'image/jpeg');
}

/// 원본 바이트를 디코딩해 픽셀 크기만 얻는다(재인코딩 전 목표 크기 계산용).
Future<({int width, int height})> _decodeSize(Uint8List bytes) async {
  final codec = await ui.instantiateImageCodec(bytes);
  final frame = await codec.getNextFrame();
  final result = (width: frame.image.width, height: frame.image.height);
  frame.image.dispose();
  return result;
}
