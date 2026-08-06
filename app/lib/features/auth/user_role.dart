// 사용자 역할 enum — web의 lib/constants.ts USER_ROLE 와 값이 일치해야 한다
// (DB 트리거 handle_new_user 가 여전히 이 문자열만 배정한다).
// ⚠️ profiles.role의 DB CHECK는 Epic 14(Story 14.1, 0027)로 완화되어 이 3값만 강제하지 않는다.
//   다만 이 enum이 실제로 파싱하는 값은 profiles.role이 **아니다** — currentRoleProvider
//   (auth_controller.dart)가 읽는 것은 세션의 `user_metadata['role']`이고, 그건 web 가입 폼이
//   실어 보낸 값이라 트리거가 profiles에 쓰는 값과 별개로 흘러간다. 그래서 14.2가 가입 역할선택을
//   없애고 트리거 기본값을 바꾸면 metadata에는 role이 아예 안 실려 fromValue(null) → null이 된다
//   (CHECK 완화 때문이 아니라 metadata 경로가 끊겨서다). 14.2는 이 파일과 그 provider를 함께 봐야 한다.
// 가입에서 고를 수 있는 역할은 buyer/seller 뿐(admin 은 web 트리거가 차단, 모바일은 admin 제외 AR9).
enum UserRole {
  buyer('buyer', '구매자'),
  seller('seller', '판매자'),
  admin('admin', '관리자');

  const UserRole(this.value, this.label);

  /// DB 에 저장되는 영문 값(profiles.role 과 일치).
  final String value;

  /// 화면 표시용 한국어 라벨.
  final String label;

  /// 가입 화면에서 선택 가능한 역할(admin 제외).

  /// 문자열(메타데이터·profiles.role)을 enum 으로. 알 수 없으면 null.
  static UserRole? fromValue(String? raw) {
    if (raw == null) return null;
    for (final r in UserRole.values) {
      if (r.value == raw) return r;
    }
    return null;
  }
}
