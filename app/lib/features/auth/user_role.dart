// 사용자 역할 enum — web의 lib/constants.ts USER_ROLE 와 값이 일치해야 한다
// (profiles.role CHECK 제약·DB 트리거 handle_new_user 와 같은 문자열).
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
  static const List<UserRole> signupRoles = [UserRole.buyer, UserRole.seller];

  /// 문자열(메타데이터·profiles.role)을 enum 으로. 알 수 없으면 null.
  static UserRole? fromValue(String? raw) {
    if (raw == null) return null;
    for (final r in UserRole.values) {
      if (r.value == raw) return r;
    }
    return null;
  }
}
