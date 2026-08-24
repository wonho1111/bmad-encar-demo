// 사용자 역할 enum — web의 lib/constants.ts USER_ROLE 와 값이 일치해야 한다.
// ⚠️ (DW-681로 바로잡음) DB 트리거 handle_new_user는 더 이상 이 문자열만 배정하지
//   않는다 — 0028(Story 14.1)이 신규 가입 기본값을 'user'로 바꿨다. 아래 정본은
//   docs/conventions.md §14(Role 어휘)다.
// ⚠️ profiles.role의 DB CHECK는 Epic 14(Story 14.1, 0027)로 완화되어 이 3값만 강제하지 않는다.
//   다만 이 enum이 실제로 파싱하는 값은 profiles.role이 **아니다** — currentRoleProvider
//   (auth_controller.dart)가 읽는 것은 세션의 `user_metadata['role']`이고, 그건 web 가입 폼이
//   실어 보낸 값이라 트리거가 profiles에 쓰는 값과 별개로 흘러간다. 그래서 14.2가 가입 역할선택을
//   없애고 트리거 기본값을 바꾸면 metadata에는 role이 아예 안 실려 fromValue(null) → null이 된다
//   (CHECK 완화 때문이 아니라 metadata 경로가 끊겨서다). 14.2는 이 파일과 그 provider를 함께 봐야 한다.
// ⚠️ (2026-08-10 Epic 16 묶음 코드리뷰로 정정) 여기 있던 *"가입에서 고를 수 있는 역할은
//   buyer/seller 뿐"* 문장을 지웠다 — **Story 16-0이 가입 역할 선택 자체를 없앴으므로**
//   (`signup_screen.dart`의 역할 선택 UI 제거) 가입 시점에 고르는 역할은 이제 없다.
//   같은 커밋이 거짓으로 만든 문장이 그대로 남아 있었다.
enum UserRole {
  buyer('buyer', '구매자'),
  seller('seller', '판매자'),
  admin('admin', '관리자');

  const UserRole(this.value, this.label);

  /// DB 에 저장되는 영문 값(profiles.role 과 일치).
  final String value;

  /// 화면 표시용 한국어 라벨.
  final String label;

  // ✎ 2026-08-10 — 여기 있던 `/// 가입 화면에서 선택 가능한 역할(admin 제외).` 은 바로 아래
  //   `signupRoles` 상수가 16-0에서 삭제되면서 **아래에 아무것도 없는 고아 doc 주석**이 됐다.
  //   문서 주석은 대상이 있어야 주석이므로 함께 지운다(Epic 16 묶음 코드리뷰 발견).

  /// 문자열(메타데이터·profiles.role)을 enum 으로. 알 수 없으면 null.
  static UserRole? fromValue(String? raw) {
    if (raw == null) return null;
    for (final r in UserRole.values) {
      if (r.value == raw) return r;
    }
    return null;
  }
}
