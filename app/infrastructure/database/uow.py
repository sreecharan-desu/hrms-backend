"""Unit of Work – async context manager wrapping a single SQLAlchemy session.

Usage::

    async with SqlAlchemyUnitOfWork() as uow:
        user = await uow.users.get_by_email("x@y.com")
        await uow.commit()
"""

from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.attendance import SqlAttendanceRepository
from app.infrastructure.database.repositories.departments import SqlDepartmentRepository
from app.infrastructure.database.repositories.employees import (
    SqlEmployeeCompensationRepository,
    SqlEmployeeRepository,
)
from app.infrastructure.database.repositories.leave import (
    SqlLeaveBalanceRepository,
    SqlLeaveRequestRepository,
    SqlLeaveTypeRepository,
)
from app.infrastructure.database.repositories.performance import (
    SqlPerformanceCycleRepository,
    SqlPerformanceGoalRepository,
    SqlPerformanceReviewRepository,
)
from app.infrastructure.database.repositories.recruitment import (
    SqlInterviewFeedbackRepository,
    SqlInterviewRepository,
    SqlJobApplicationRepository,
    SqlJobRepository,
)
from app.infrastructure.database.repositories.roles import (
    SqlPasswordResetRepository,
    SqlPermissionRepository,
    SqlRefreshTokenRepository,
    SqlRoleRepository,
)
from app.infrastructure.database.repositories.users import SqlUserRepository
from app.infrastructure.database.session import async_session_factory


class SqlAlchemyUnitOfWork:
    """Async Unit-of-Work backed by a single ``AsyncSession``.

    Lazily creates repository instances that share the same session.
    """

    session: AsyncSession

    def __init__(self, session_factory=async_session_factory) -> None:
        self._session_factory = session_factory
        self._users: SqlUserRepository | None = None
        self._roles: SqlRoleRepository | None = None
        self._permissions: SqlPermissionRepository | None = None
        self._refresh_tokens: SqlRefreshTokenRepository | None = None
        self._password_resets: SqlPasswordResetRepository | None = None
        self._employees: SqlEmployeeRepository | None = None
        self._employee_compensations: SqlEmployeeCompensationRepository | None = None
        self._departments: SqlDepartmentRepository | None = None
        self._attendances: SqlAttendanceRepository | None = None
        self._leave_types: SqlLeaveTypeRepository | None = None
        self._leave_balances: SqlLeaveBalanceRepository | None = None
        self._leave_requests: SqlLeaveRequestRepository | None = None
        self._jobs: SqlJobRepository | None = None
        self._job_applications: SqlJobApplicationRepository | None = None
        self._interviews: SqlInterviewRepository | None = None
        self._interview_feedbacks: SqlInterviewFeedbackRepository | None = None
        self._performance_cycles: SqlPerformanceCycleRepository | None = None
        self._performance_reviews: SqlPerformanceReviewRepository | None = None
        self._performance_goals: SqlPerformanceGoalRepository | None = None

    async def __aenter__(self) -> Self:
        self.session = self._session_factory()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()
        await self.session.close()

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    # ── Lazy repository accessors ────────────────────────────────────

    @property
    def users(self) -> SqlUserRepository:
        if self._users is None:
            self._users = SqlUserRepository(self.session)
        return self._users

    @property
    def roles(self) -> SqlRoleRepository:
        if self._roles is None:
            self._roles = SqlRoleRepository(self.session)
        return self._roles

    @property
    def permissions(self) -> SqlPermissionRepository:
        if self._permissions is None:
            self._permissions = SqlPermissionRepository(self.session)
        return self._permissions

    @property
    def refresh_tokens(self) -> SqlRefreshTokenRepository:
        if self._refresh_tokens is None:
            self._refresh_tokens = SqlRefreshTokenRepository(self.session)
        return self._refresh_tokens

    @property
    def password_resets(self) -> SqlPasswordResetRepository:
        if self._password_resets is None:
            self._password_resets = SqlPasswordResetRepository(self.session)
        return self._password_resets

    @property
    def employees(self) -> SqlEmployeeRepository:
        if self._employees is None:
            self._employees = SqlEmployeeRepository(self.session)
        return self._employees

    @property
    def employee_compensations(self) -> SqlEmployeeCompensationRepository:
        if self._employee_compensations is None:
            self._employee_compensations = SqlEmployeeCompensationRepository(self.session)
        return self._employee_compensations

    @property
    def departments(self) -> SqlDepartmentRepository:
        if self._departments is None:
            self._departments = SqlDepartmentRepository(self.session)
        return self._departments

    @property
    def attendances(self) -> SqlAttendanceRepository:
        if self._attendances is None:
            self._attendances = SqlAttendanceRepository(self.session)
        return self._attendances

    @property
    def leave_types(self) -> SqlLeaveTypeRepository:
        if self._leave_types is None:
            self._leave_types = SqlLeaveTypeRepository(self.session)
        return self._leave_types

    @property
    def leave_balances(self) -> SqlLeaveBalanceRepository:
        if self._leave_balances is None:
            self._leave_balances = SqlLeaveBalanceRepository(self.session)
        return self._leave_balances

    @property
    def leave_requests(self) -> SqlLeaveRequestRepository:
        if self._leave_requests is None:
            self._leave_requests = SqlLeaveRequestRepository(self.session)
        return self._leave_requests

    # ── Recruitment ──────────────────────────────────────────────

    @property
    def jobs(self) -> SqlJobRepository:
        if self._jobs is None:
            self._jobs = SqlJobRepository(self.session)
        return self._jobs

    @property
    def job_applications(self) -> SqlJobApplicationRepository:
        if self._job_applications is None:
            self._job_applications = SqlJobApplicationRepository(self.session)
        return self._job_applications

    @property
    def interviews(self) -> SqlInterviewRepository:
        if self._interviews is None:
            self._interviews = SqlInterviewRepository(self.session)
        return self._interviews

    @property
    def interview_feedbacks(self) -> SqlInterviewFeedbackRepository:
        if self._interview_feedbacks is None:
            self._interview_feedbacks = SqlInterviewFeedbackRepository(self.session)
        return self._interview_feedbacks

    # ── Performance ──────────────────────────────────────────────

    @property
    def performance_cycles(self) -> SqlPerformanceCycleRepository:
        if self._performance_cycles is None:
            self._performance_cycles = SqlPerformanceCycleRepository(self.session)
        return self._performance_cycles

    @property
    def performance_reviews(self) -> SqlPerformanceReviewRepository:
        if self._performance_reviews is None:
            self._performance_reviews = SqlPerformanceReviewRepository(self.session)
        return self._performance_reviews

    @property
    def performance_goals(self) -> SqlPerformanceGoalRepository:
        if self._performance_goals is None:
            self._performance_goals = SqlPerformanceGoalRepository(self.session)
        return self._performance_goals
