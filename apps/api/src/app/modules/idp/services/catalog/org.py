"""#4 HR_ROSTER — Danh sách nhân sự / sơ đồ tổ chức (04 §5 #4, order 10 §7.2.4)."""

from app.modules.idp.services.catalog.base import doc_type, f

_D, _T, _P, _E = ("ACT-create_department", "ACT-create_team", "ACT-create_position",
                  "ACT-create_employee")  # fmt: skip

HR_ROSTER = doc_type(
    "HR_ROSTER", "Danh sách nhân sự / sơ đồ tổ chức", "HR roster / org chart", ["O"], 4,
    ["danh sách nhân sự", "sơ đồ tổ chức", "mã nv", "phòng ban", "chức danh", "employee list"],
    [_D, _T, _P, _E],
    [
        f("department_code", "text", _D, "code", required=True,
          aliases=("mã phòng ban", "mã pb", "department code"), master_ref="hr.department_code"),
        f("department_name", "text", _D, "name", required=True,
          aliases=("phòng ban", "tên phòng ban", "department")),
        f("team_code", "text", _T, "code", aliases=("mã team", "mã tổ", "team code")),
        f("team_name", "text", _T, "name", aliases=("team", "tổ", "nhóm")),
        f("title", "text", _P, "title", aliases=("chức danh", "vị trí", "title", "position")),
        f("employee_code", "text", _E, required=True,
          aliases=("mã nv", "mã nhân viên", "employee code"), master_ref="hr.employee_code"),
        f("full_name", "person_name", _E, required=True, level=3,
          aliases=("họ tên", "họ và tên", "full name")),
        f("manager_code", "text", _E, aliases=("mã quản lý", "quản lý trực tiếp", "manager"),
          master_ref="hr.employee_code"),
        f("hire_date", "date", _E, required=True,
          aliases=("ngày vào", "ngày vào làm", "hire date")),
        f("status", "enum", _E, aliases=("trạng thái", "status"),
          enum=["probation", "active", "on_leave", "terminated"]),
        f("email", "text", _E, level=3, aliases=("email", "thư điện tử")),
        f("phone", "phone", _E, level=3, aliases=("điện thoại", "số điện thoại", "phone")),
        f("salary", "money", _E, critical=True, level=4,
          aliases=("lương", "lương cơ bản", "salary")),
        f("date_of_birth", "date", _E, level=4, aliases=("ngày sinh", "date of birth")),
        f("address", "text", _E, level=4, aliases=("địa chỉ", "address")),
        f("national_id", "text", _E, critical=True, level=4, aliases=("cccd", "cmnd", "số cccd")),
        f("bank_account", "text", _E, critical=True, level=4,
          aliases=("số tài khoản", "stk", "bank account")),
    ],
    [{"code": "VR-HR-01", "kind": "field", "severity": "fail",
      "expression": {"field": "hire_date", "op": "date_not_future"}}],
)  # fmt: skip
