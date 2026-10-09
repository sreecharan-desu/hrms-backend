"""Update employee compensation use case."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.audit import write_audit
from app.core.dependencies import RequestContext
from app.core.exceptions import NotFoundError
from app.infrastructure.database.models.employee import EmployeeCompensation
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


@dataclass(frozen=True, slots=True)
class CompensationInput:
    salary: Decimal
    currency: str = "INR"
    effective_from: date | None = None


async def update_compensation(
    employee_id: str,
    data: CompensationInput,
    uow: SqlAlchemyUnitOfWork,
    *,
    actor_id: str,
    ctx: RequestContext | None = None,
) -> EmployeeCompensation:
    employee = await uow.employees.get_by_id(employee_id)
    if employee is None:
        raise NotFoundError("Employee not found.")

    old_comp = await uow.employee_compensations.get_by_employee_id(employee_id)
    old_values = None
    if old_comp:
        old_values = {
            "salary": str(old_comp.salary),
            "currency": old_comp.currency,
        }

    comp = EmployeeCompensation(
        employee_id=employee_id,
        salary=data.salary,
        currency=data.currency,
        effective_from=data.effective_from or date.today(),
    )
    comp = await uow.employee_compensations.upsert(comp)

    await write_audit(
        uow,
        actor_id=actor_id,
        action="employee.salary.updated",
        entity_type="employee_compensation",
        entity_id=employee_id,
        old=old_values,
        new={"salary": str(data.salary), "currency": data.currency},
        request_context=ctx,
    )

    await uow.commit()
    return comp
