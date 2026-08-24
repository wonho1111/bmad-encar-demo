// 카드·상세 갤러리가 공유하는 사진 시각 요소(web ListingCardImage.tsx/ListingGallery.tsx의
// PhotoPlaceholder·"N장"/"k/N" 배지를 Flutter로 미러). 두 화면이 같은 요소를 각자 만들면
// 어긋나므로 한 곳에 둔다(Code Map).
import 'package:flutter/material.dart';

import '../../core/theme/app_theme.dart';

/// "사진 준비중" 플레이스홀더 — 사진 없음(url null/빈문자열)과 로드 실패(errorBuilder) 공통.
/// 빈 영역·깨진 이미지 아이콘 대신 의도적으로 보이게 한다(web 동일 원칙, conventions.md §10.2).
/// web의 compact(썸네일 스트립용 축약판)는 이식하지 않는다 — 이 스토리는 썸네일 스트립 자체를
/// 만들지 않으므로(A2, ListingGallery 주석 참조) 쓰이지 않는 분기를 남기지 않는다.
class PhotoPlaceholder extends StatelessWidget {
  const PhotoPlaceholder({super.key});

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: AppColors.placeholderBg,
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.photo_camera_outlined,
              color: AppColors.inkMuted,
              size: 28,
            ),
            const SizedBox(height: 4),
            const Text(
              '사진 준비중',
              style: TextStyle(
                color: AppColors.inkMuted,
                fontSize: 12,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 사진/플레이스홀더 위에 얹는 불투명(반투명 아님) dark pill 배지 콘텐츠.
/// 카드 "N장"·갤러리 "k/N"이 공유 — 불투명이라 사진 밝기와 무관하게 흰 글자 대비가 고정된다(AC2).
/// ⚠️ 이 위젯 자체는 위치를 정하지 않는다(Stack 안에서만 의미가 있으므로) — 호출부가
/// `Positioned(bottom: 8, right: 8, child: PhotoCountBadge(...))`로 감싼다. 이전엔 build()가
/// 직접 Positioned를 반환해 Stack 밖에서 쓰면 런타임에 죽었다(구조로 막는 편이 문서화보다 낫다).
class PhotoCountBadge extends StatelessWidget {
  const PhotoCountBadge({super.key, required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Colors.black, // 불투명 고정 — web bg-black과 동일(반투명 pill 금지, AC2).
        borderRadius: BorderRadius.circular(11),
      ),
      child: Text(
        text,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 12,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}
