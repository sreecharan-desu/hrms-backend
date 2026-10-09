"""Permission constants, role names, and role→permission mappings."""

from __future__ import annotations

# ── Permission strings ───────────────────────────────────────────────

class P:
    """Flat namespace of every permission string used in the system."""

    EMPLOYEE_READ = "employee.read"
    EMPLOYEE_CREATE = "employee.create"
    EMPLOYEE_UPDATE = "employee.update"
    EMPLOYEE_DELETE = "employee.delete"
    EMPLOYEE_COMPENSATION_READ = "employee.compensation.read"
    EMPLOYEE_COMPENSATION_UPDATE = "employee.compensation.update"

    DEPARTMENT_READ = "department.read"
    DEPARTMENT_CREATE = "department.create"
    DEPARTMENT_UPDATE = "department.update"
    DEPARTMENT_DELETE = "department.delete"

    ATTENDANCE_READ = "attendance.read"
    ATTENDANCE_CREATE = "attendance.create"
    ATTENDANCE_UPDATE = "attendance.update"

    LEAVE_READ = "leave.read"
    LEAVE_CREATE = "leave.create"
    LEAVE_APPROVE = "leave.approve"
    LEAVE_REJECT = "leave.reject"
    LEAVE_CANCEL = "leave.cancel"

    RECRUITMENT_READ = "recruitment.read"
    RECRUITMENT_CREATE = "recruitment.create"
    RECRUITMENT_UPDATE = "recruitment.update"
    RECRUITMENT_MANAGE = "recruitment.manage"

    PERFORMANCE_READ = "performance.read"
    PERFORMANCE_CREATE = "performance.create"
    PERFORMANCE_EVALUATE = "performance.evaluate"

    DOCUMENT_READ = "document.read"
    DOCUMENT_UPLOAD = "document.upload"
    DOCUMENT_DELETE = "document.delete"

    AUDIT_READ = "audit.read"
    ADMIN_MANAGE = "admin.manage"


ALL_PERMISSIONS: frozenset[str] = frozenset(
    v for k, v in vars(P).items() if not k.startswith("_") and isinstance(v, str)
)


# ── Role names ───────────────────────────────────────────────────────

class Role:
    SUPER_ADMIN = "SUPER_ADMIN"
    HR_ADMIN = "HR_ADMIN"
    HR_MANAGER = "HR_MANAGER"
    HR_EXECUTIVE = "HR_EXECUTIVE"
    MANAGER = "MANAGER"
    RECRUITER = "RECRUITER"
    INTERVIEWER = "INTERVIEWER"
    EMPLOYEE = "EMPLOYEE"


ALL_ROLES: frozenset[str] = frozenset(
    v for k, v in vars(Role).items() if not k.startswith("_") and isinstance(v, str)
)

# ── Role → permission mapping ────────────────────────────────────────

_HR_FULL = ALL_PERMISSIONS - {P.ADMIN_MANAGE}

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    Role.SUPER_ADMIN: ALL_PERMISSIONS,

    Role.HR_ADMIN: _HR_FULL | {P.ADMIN_MANAGE},

    Role.HR_MANAGER: frozenset({
        P.EMPLOYEE_READ, P.EMPLOYEE_CREATE, P.EMPLOYEE_UPDATE,
        P.EMPLOYEE_COMPENSATION_READ,
        P.DEPARTMENT_READ, P.DEPARTMENT_CREATE, P.DEPARTMENT_UPDATE,
        P.ATTENDANCE_READ, P.ATTENDANCE_CREATE, P.ATTENDANCE_UPDATE,
        P.LEAVE_READ, P.LEAVE_CREATE, P.LEAVE_APPROVE, P.LEAVE_REJECT, P.LEAVE_CANCEL,
        P.RECRUITMENT_READ, P.RECRUITMENT_CREATE, P.RECRUITMENT_UPDATE, P.RECRUITMENT_MANAGE,
        P.PERFORMANCE_READ, P.PERFORMANCE_CREATE, P.PERFORMANCE_EVALUATE,
        P.DOCUMENT_READ, P.DOCUMENT_UPLOAD,
        P.AUDIT_READ,
    }),

    Role.HR_EXECUTIVE: frozenset({
        P.EMPLOYEE_READ, P.EMPLOYEE_CREATE, P.EMPLOYEE_UPDATE,
        P.DEPARTMENT_READ,
        P.ATTENDANCE_READ, P.ATTENDANCE_CREATE, P.ATTENDANCE_UPDATE,
        P.LEAVE_READ, P.LEAVE_CREATE, P.LEAVE_APPROVE, P.LEAVE_REJECT,
        P.RECRUITMENT_READ, P.RECRUITMENT_CREATE, P.RECRUITMENT_UPDATE,
        P.PERFORMANCE_READ,
        P.DOCUMENT_READ, P.DOCUMENT_UPLOAD,
    }),

    Role.MANAGER: frozenset({
        P.EMPLOYEE_READ,
        P.DEPARTMENT_READ,
        P.ATTENDANCE_READ,
        P.LEAVE_READ, P.LEAVE_APPROVE, P.LEAVE_REJECT,
        P.PERFORMANCE_READ, P.PERFORMANCE_CREATE, P.PERFORMANCE_EVALUATE,
        P.DOCUMENT_READ,
    }),

    Role.RECRUITER: frozenset({
        P.EMPLOYEE_READ,
        P.RECRUITMENT_READ, P.RECRUITMENT_CREATE, P.RECRUITMENT_UPDATE, P.RECRUITMENT_MANAGE,
        P.DOCUMENT_READ, P.DOCUMENT_UPLOAD,
    }),

    Role.INTERVIEWER: frozenset({
        P.RECRUITMENT_READ,
        P.DOCUMENT_READ,
    }),

    Role.EMPLOYEE: frozenset({
        P.EMPLOYEE_READ,
        P.ATTENDANCE_READ, P.ATTENDANCE_CREATE,
        P.LEAVE_READ, P.LEAVE_CREATE, P.LEAVE_CANCEL,
        P.DOCUMENT_READ, P.DOCUMENT_UPLOAD,
        P.PERFORMANCE_READ,
    }),
}
