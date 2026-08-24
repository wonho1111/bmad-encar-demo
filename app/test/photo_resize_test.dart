// 저장본 규격(긴 변 ≤1600px 유지, 비율 보존) 단위테스트 — web `resize.test.ts`의 미러.
//
// ⚠️ 이 파일이 다루지 않는 것: 실제 인코딩(`resizeImage`)은 `flutter_image_compress` 플랫폼
// 채널을 타므로 `flutter test`(헤드리스 flutter_tester)에서 실행할 수 없다 — web도 같은 이유로
// canvas 기반 실제 인코딩은 브라우저 관찰 몫이고, `resize.test.ts`는 순수 함수인
// `computeTargetSize`만 검증한다. 이 파일도 동일한 경계를 따른다.
import 'package:app/features/listings/photo_resize.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('computeTargetSize — 긴 변 상한 1600px, 비율 보존', () {
    test('긴 변이 상한 이하면 그대로 둔다(억지로 키우지 않는다)', () {
      final r = computeTargetSize(800, 600);
      expect(r.width, 800);
      expect(r.height, 600);
    });

    test('긴 변이 정확히 상한이면 그대로 둔다', () {
      final r = computeTargetSize(1600, 900);
      expect(r.width, 1600);
      expect(r.height, 900);
    });

    test('가로가 긴 변이면 가로를 1600으로, 세로는 비율대로 줄인다', () {
      // 3200x1800 → 가로가 긴 변, scale=0.5 → 1600x900.
      final r = computeTargetSize(3200, 1800);
      expect(r.width, 1600);
      expect(r.height, 900);
    });

    test('세로가 긴 변이면 세로를 1600으로, 가로는 비율대로 줄인다', () {
      // 1800x3200 → 세로가 긴 변, scale=0.5 → 900x1600.
      final r = computeTargetSize(1800, 3200);
      expect(r.width, 900);
      expect(r.height, 1600);
    });

    test('극단 비율(가로 1px)에서도 짧은 변이 0으로 내려가지 않는다(최소 1px 보장)', () {
      final r = computeTargetSize(8000, 1);
      expect(r.width, 1600);
      expect(r.height, greaterThanOrEqualTo(1));
    });

    test('정사각형 이미지는 양변이 동일하게 줄어든다', () {
      final r = computeTargetSize(3000, 3000);
      expect(r.width, 1600);
      expect(r.height, 1600);
    });
  });
}
