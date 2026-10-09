"""Resource-level policy helpers for authorization checks beyond RBAC.

These are pure functions that decide whether a given *actor* (CurrentUser)
can operate on a particular resource.  They intentionally stay free of
DB access – callers must supply the data needed for the decision.
"""

from __future__ import annotations

from app.core.dependencies import CurrentUser
from app.core.permissions import P


def can_view_employee(actor: CurrentUser, employee_user_id: str | None) -> bool:
    """The actor may view the employee if they own the record or hold employee.read."""
    if P.EMPLOYEE_READ in actor.permissions:
        return True
    return employee_user_id is not None and actor.id == employee_user_id


def can_update_employee(actor: CurrentUser, employee_user_id: str | None) -> bool:
    if P.EMPLOYEE_UPDATE in actor.permissions:
        return True
    return employee_user_id is not None and actor.id == employee_user_id


def can_manage_direct_report(
    actor: CurrentUser,
    manager_user_id: str | None,
) -> bool:
    """True when the actor is the direct manager of the target employee."""
    if manager_user_id is None:
        return False
    return actor.id == manager_user_id


def can_approve_leave(
    actor: CurrentUser,
    manager_user_id: str | None,
) -> bool:
    """Approve leave if actor is the manager or has the leave.approve perm."""
    if P.LEAVE_APPROVE in actor.permissions:
        return True
    return can_manage_direct_report(actor, manager_user_id)


def can_view_compensation(actor: CurrentUser, employee_user_id: str | None) -> bool:
    """Compensation is sensitive; only owners or users with the explicit perm."""
    if P.EMPLOYEE_COMPENSATION_READ in actor.permissions:
        return True
    return employee_user_id is not None and actor.id == employee_user_id


def can_delete_employee(actor: CurrentUser) -> bool:
    """Only actors with the explicit delete permission may soft-delete."""
    return P.EMPLOYEE_DELETE in actor.permissions
