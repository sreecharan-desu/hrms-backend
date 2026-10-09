"""Import all ORM models so Alembic ``target_metadata`` sees every table."""

from app.infrastructure.database.models.attendance import Attendance
from app.infrastructure.database.models.audit import AuditLog
from app.infrastructure.database.models.department import Department
from app.infrastructure.database.models.document import Document
from app.infrastructure.database.models.employee import Employee, EmployeeCompensation
from app.infrastructure.database.models.jobs import BackgroundJob
from app.infrastructure.database.models.leave import LeaveBalance, LeaveRequest, LeaveType
from app.infrastructure.database.models.notification import Notification
from app.infrastructure.database.models.performance import (
    PerformanceCycle,
    PerformanceGoal,
    PerformanceReview,
)
from app.infrastructure.database.models.recruitment import (
    Interview,
    InterviewFeedback,
    Job,
    JobApplication,
)
from app.infrastructure.database.models.user import (
    PasswordResetToken,
    Permission,
    RefreshToken,
    Role,
    User,
    role_permissions,
    user_roles,
)

__all__ = [
    "Attendance",
    "AuditLog",
    "BackgroundJob",
    "Department",
    "Document",
    "Employee",
    "EmployeeCompensation",
    "Interview",
    "InterviewFeedback",
    "Job",
    "JobApplication",
    "LeaveBalance",
    "LeaveRequest",
    "LeaveType",
    "Notification",
    "PasswordResetToken",
    "PerformanceCycle",
    "PerformanceGoal",
    "PerformanceReview",
    "Permission",
    "RefreshToken",
    "Role",
    "User",
    "role_permissions",
    "user_roles",
]
