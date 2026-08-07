// 앱 전역 테마 — 웹 디자인 토큰(DESIGN.md 라이트 팔레트)을 그대로 옮긴다(Story 16.1).
// 옛 zinc/차콜 임시 팔레트(웹 개편 이전)를 대체한다.
// ⚠️ 앱은 라이트 고정이다 — 웹은 라이트/다크를 모두 지원하지만, 이 스토리는 앱 범위를
//   라이트 값만으로 한정한다(기존 결정, spec-16-1 Boundaries). 다크모드 토큰은 옮기지 않는다.
// 목적: ① 색상을 웹과 일치 ② 화면별 인라인 색 대신 여기 AppColors 를 참조
//       ③ Pretendard 폰트 + petrol 기반 컴포넌트 테마 적용.
import 'package:flutter/material.dart';

/// 웹과 동일한 색 토큰(DESIGN.md 라이트 팔레트, hex 그대로). 화면에서 인라인 Colors.* 대신 사용.
class AppColors {
  AppColors._();

  // 표면 (D1)
  static const surfaceBase = Color(0xFFFAFAF8); // 본문 바탕
  static const surfaceRaised = Color(0xFFFFFFFF); // 카드·시트·입력

  // 잉크 (D1)
  static const inkPrimary = Color(0xFF1A1E1D); // 본문·제목
  static const inkSecondary = Color(0xFF565F5D); // 보조 텍스트
  static const inkMuted = Color(0xFF676D69); // meta·면책·placeholder 글자
  static const borderHairline = Color(0xFFE6E3DD); // 1px 구분선·카드 테두리

  // 브랜드 petrol = 신뢰·구조 (D1·D2)
  static const brandPetrol = Color(0xFF1E6E6A); // 내비·버튼·포커스·칩
  static const brandPetrolStrong = Color(0xFF14514E); // 강조 구조·히어로 밴드 상단
  static const petrolDeepest = Color(0xFF0F3D3E); // 히어로 그라데이션 종단

  // petrol 배경 위 잉크(Task: "새 하드코딩 색 금지" — 직전 구현이 이 자리에
  // Color(0xFFC9D9D8)·Colors.white70·Colors.white를 새로 박았던 것을 토큰화한다).
  static const onPetrol = Colors.white; // petrol 배경 위 기본 잉크(제목류)
  static const onPetrolMuted = Color(0xFFC9D9D8); // petrol 배경 위 보조 잉크(부제·아이콘류)

  // 앰버 = 가격·CTA 전용 (D3)
  static const accentAmber = Color(0xFFF0A339); // 핵심 CTA(검색·문의) — 글자·아이콘은 inkPrimary 고정(흰색 금지)
  static const priceEmphasis = Color(0xFFC0730F); // 가격 숫자

  // 신뢰속성 = 차분한 초록 (D3, amber와 분리)
  static const trustGreenBg = Color(0xFFE7F3EC); // 무사고/1인소유/비흡연 칩 바탕
  static const trustGreenInk = Color(0xFF1B6E3D); // 신뢰속성 글자·✓ 글리프

  // 상태
  static const placeholderBg = Color(0xFFF1EFE9); // 사진 준비중 바탕
  static const warnAmberBg = Color(0xFFFDEFDA); // 정직성 고지·주의 배너 바탕
  static const warnAmberInk = Color(0xFF8A5A12); // 주의 배너 글자
  static const danger = Color(0xFFC0392B); // 오류·삭제·파괴적 액션
}

/// 라이트 테마(앱은 라이트 고정). 웹이 라이트 기본이라 동일하게 맞춘다.
ThemeData buildAppTheme() {
  // petrol 시드에서 시작해, 핵심 색을 웹 토큰으로 강제 덮어쓴다(시드 자동 톤 대신 정확한 값).
  final base = ColorScheme.fromSeed(
    seedColor: AppColors.brandPetrol,
    brightness: Brightness.light,
  );
  final scheme = base.copyWith(
    primary: AppColors.brandPetrol,
    onPrimary: Colors.white,
    surface: AppColors.surfaceRaised,
    onSurface: AppColors.inkPrimary,
    onSurfaceVariant: AppColors.inkMuted,
    surfaceContainerHighest: AppColors.placeholderBg,
    outline: AppColors.borderHairline,
    outlineVariant: AppColors.borderHairline,
    error: AppColors.danger,
    onError: Colors.white,
  );

  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    fontFamily: 'Pretendard',
    scaffoldBackgroundColor: AppColors.surfaceBase,

    // AppBar: 웹 헤더처럼 밝은 배경 + petrol 잉크 전경 + 하단 1px 보더.
    appBarTheme: const AppBarTheme(
      backgroundColor: AppColors.surfaceRaised,
      foregroundColor: AppColors.inkPrimary,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: AppColors.inkPrimary,
        fontFamily: 'Pretendard',
        fontSize: 18,
        fontWeight: FontWeight.w700,
      ),
      shape: Border(bottom: BorderSide(color: AppColors.borderHairline)),
    ),

    // 주요 버튼: petrol 배경·흰 글씨·라운드 8(웹 primary 버튼과 동일 톤).
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.brandPetrol,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),

    // 보조 버튼(테두리): border-hairline.
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.inkPrimary,
        side: const BorderSide(color: AppColors.borderHairline),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),

    // 입력칸: 기본 보더 border-hairline, 포커스 시 petrol(웹 :focus-visible 규칙과 동일 색).
    inputDecorationTheme: InputDecorationTheme(
      isDense: true,
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.borderHairline),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.brandPetrol),
      ),
    ),

    // NavigationBar(하단 4탭): 활성 = petrol(DESIGN.md "바텀 내비(Flutter)" 규칙).
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: AppColors.surfaceRaised,
      indicatorColor: AppColors.brandPetrol.withValues(alpha: 0.12),
      labelTextStyle: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return TextStyle(
          fontFamily: 'Pretendard',
          fontSize: 12,
          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
          color: selected ? AppColors.brandPetrol : AppColors.inkMuted,
        );
      }),
      iconTheme: WidgetStateProperty.resolveWith((states) {
        final selected = states.contains(WidgetState.selected);
        return IconThemeData(
          color: selected ? AppColors.brandPetrol : AppColors.inkMuted,
        );
      }),
    ),

    // FAB 없음(D12·spec-16-1) — 어떤 화면도 floatingActionButton을 선언하지 않으므로
    // 테마 자체를 지운다(옛 죽은 코드 제거).
  );
}
