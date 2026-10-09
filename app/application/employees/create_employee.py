"""Create employee use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import ConflictError, NotFoundError
from app.infrastructure.database.models.employee import Employee
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class CreateEmployeeInput:
    employee_code: str
    first_name: str
    last_name: str
    email: str
    joining_date: date
    phone: str | None = None
    date_of_birth: date | None = None
    status: str = "ACTIVE"
    department_id: str | None = None
    designation: str | None = None
    manager_id: str | None = None
    location: str | None = None
    emergency_contact: dict | None = None
    profile: dict | None = None
    user_id: str | None = None


async def create_employee(
    data: CreateEmployeeInput,
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> Employee:
    # Unique email
    existing = await uow.employees.get_by_email(data.email)
    if existing:
        raise ConflictError("An employee with this email already exists.")

    # Unique employee_code
    existing = await uow.employees.get_by_employee_code(data.employee_code)
    if existing:
        raise ConflictError("An employee with this employee code already exists.")

    # Department must exist and not soft-deleted
    if data.department_id:
        dept = await uow.departments.get_by_id(data.department_id)
        if dept is None:
            raise NotFoundError("Department not found or has been deleted.")

    # Manager must exist if set
    if data.manager_id:
        manager = await uow.employees.get_by_id(data.manager_id)
        if manager is None:
            raise NotFoundError("Manager not found.")

    employee = Employee(
        employee_code=data.employee_code,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone=data.phone,
        date_of_birth=data.date_of_birth,
        joining_date=data.joining_date,
        status=data.status,
        department_id=data.department_id,
        designation=data.designation,
        manager_id=data.manager_id,
        location=data.location,
        emergency_contact=data.emergency_contact,
        profile=data.profile,
        user_id=data.user_id,
    )

    employee = await uow.employees.create(employee)

    await write_audit(
        uow,
        actor_id=actor_id,
        action="employee.created",
        entity_type="employee",
        entity_id=employee.id,
        new={"employee_code": employee.employee_code, "email": employee.email},
        request_context=ctx,
    )

    await uow.commit()
    # Re-fetch to ensure all eager loads are populated after commit
    employee = await uow.employees.get_by_id(employee.id)  # type: ignore[assignment]
    return employee
