"""Verify the permissions map: SUPER_ADMIN should have every permission."""

from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS, Role


def test_super_admin_has_all_permissions():
    assert ROLE_PERMISSIONS[Role.SUPER_ADMIN] == ALL_PERMISSIONS


def test_all_roles_have_subset_of_all_permissions():
    for role_name, perms in ROLE_PERMISSIONS.items():
        missing = perms - ALL_PERMISSIONS
        assert not missing, f"{role_name} has unknown permissions: {missing}"


def test_employee_role_has_basic_perms():
    emp_perms = ROLE_PERMISSIONS[Role.EMPLOYEE]
    assert "leave.create" in emp_perms
    assert "leave.read" in emp_perms
    assert "attendance.create" in emp_perms
    assert "admin.manage" not in emp_perms
