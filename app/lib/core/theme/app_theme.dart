// 앱 전역 테마 — 웹(web/src/app/globals.css)의 차콜/zinc 미니멀 팔레트를 그대로 옮긴다.
// 목적: ① 색상을 웹과 일치 ② AppBar 전경색을 명시해 "흰 글씨라 안 보이던" 로그아웃 등 가시화
//       ③ 버튼·입력 톤 통일. 화면별 인라인 색 대신 여기 AppColors 를 참조한다.
import 'package:flutter/material.dart';

/// 웹과 동일한 색 토큰(Tailwind zinc 기반). 화면에서 인라인 Colors.* 대신 사용.
class AppColors {
  AppColors._();
  static const ink = Color(0xFF18181B); // zinc-900 = primary(브랜드 차콜)
  static const ink2 = Color(0xFF171717); // 본문 텍스트
  static const muted = Color(0xFF71717A); // zinc-500 = 보조 텍스트
  static const border = Color(0xFFE4E4E7); // zinc-200 = 보더
  static const surfaceMuted = Color(0xFFF4F4F5); // zinc-100 = 옅은 면
  static const danger = Color(0xFFDC2626); // red-600 = 에러/위험
  static const successBg = Color(0xFFDCFCE7); // green-100 = 성공 배지 배경
  static const successFg = Color(0xFF15803D); // green-700 = 성공 배지 글씨
}

/// 라이트 테마(앱은 라이트 고정). 웹이 라이트 기본이라 동일하게 맞춘다.
ThemeData buildAppTheme() {
  // 차콜 시드에서 시작해, 핵심 색을 웹 토큰으로 강제 덮어쓴다(시드 자동 톤 대신 정확한 값).
  final base = ColorScheme.fromSeed(
    seedColor: AppColors.ink,
    brightness: Brightness.light,
  );
  final scheme = base.copyWith(
    primary: AppColors.ink,
    onPrimary: Colors.white,
    surface: Colors.white,
    onSurface: AppColors.ink2,
    onSurfaceVariant: AppColors.muted,
    surfaceContainerHighest: AppColors.surfaceMuted,
    outline: AppColors.border,
    outlineVariant: AppColors.border,
    error: AppColors.danger,
    onError: Colors.white,
  );

  return ThemeData(
    colorScheme: scheme,
    useMaterial3: true,
    scaffoldBackgroundColor: Colors.white,

    // AppBar: 웹 헤더처럼 흰 배경 + 검정 전경 + 하단 1px 보더. (로그아웃 글씨 가시화)
    appBarTheme: const AppBarTheme(
      backgroundColor: Colors.white,
      foregroundColor: AppColors.ink2,
      elevation: 0,
      scrolledUnderElevation: 0,
      surfaceTintColor: Colors.transparent,
      centerTitle: false,
      titleTextStyle: TextStyle(
        color: AppColors.ink2,
        fontSize: 18,
        fontWeight: FontWeight.w700,
      ),
      shape: Border(bottom: BorderSide(color: AppColors.border)),
    ),

    // 주요 버튼: 차콜 배경·흰 글씨·라운드 8(웹 primary 버튼과 동일 톤).
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        backgroundColor: AppColors.ink,
        foregroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      ),
    ),

    // 보조 버튼(테두리): zinc 보더.
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(
        foregroundColor: AppColors.ink2,
        side: const BorderSide(color: AppColors.border),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
    ),

    // 입력칸: 기본 보더 zinc-200, 포커스 시 차콜.
    inputDecorationTheme: InputDecorationTheme(
      isDense: true,
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.border),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: AppColors.ink),
      ),
    ),

    // FAB: 차콜·흰 글씨(AI 검색).
    floatingActionButtonTheme: const FloatingActionButtonThemeData(
      backgroundColor: AppColors.ink,
      foregroundColor: Colors.white,
    ),
  );
}
