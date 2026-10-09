"""Idempotent seed script – creates permissions, roles, dev admin, and leave types.

Usage:
    uv run python scripts/seed.py

Safety: refuses to run when APP_ENV=production.
"""

from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.permissions import ALL_PERMISSIONS, ROLE_PERMISSIONS
from app.core.security import hash_password
from app.domain.users.enums import UserStatus
from app.infrastructure.database.models.leave import LeaveType
from app.infrastructure.database.models.user import Permission, Role, User
from app.infrastructure.database.uow import SqlAlchemyUnitOfWork


async def seed() -> None:
    settings = get_settings()

    if settings.APP_ENV == "production":
        print("ERROR: seed.py refuses to run in production.")
        sys.exit(1)

    print(f"Seeding HRMF ({settings.APP_ENV}) …")

    async with SqlAlchemyUnitOfWork() as uow:
        # ── 1. Permissions (upsert by code) ──────────────────────
        for code in sorted(ALL_PERMISSIONS):
            await uow.permissions.upsert_by_code(code)
        await uow.commit()
        print(f"  ✓ {len(ALL_PERMISSIONS)} permissions upserted")

        # Re-fetch all permissions into session after commit
        result = await uow.session.execute(select(Permission))
        all_perms = {p.code: p for p in result.scalars().all()}

        # ── 2. Roles (upsert by name) + wire permissions ────────
        role_count = 0
        for role_name, perm_codes in ROLE_PERMISSIONS.items():
            role = await uow.roles.upsert_by_name(role_name)
            # Eagerly load permissions to avoid lazy-load issues
            await uow.session.execute(
                select(Role)
                .options(selectinload(Role.permissions))
                .where(Role.id == role.id)
            )
            role.permissions = [all_perms[c] for c in perm_codes if c in all_perms]
            role_count += 1
        await uow.commit()
        print(f"  ✓ {role_count} roles upserted with permissions")

        # ── 3. Dev admin user ────────────────────────────────────
        admin_email = settings.DEV_ADMIN_EMAIL
        admin_password = settings.DEV_ADMIN_PASSWORD
        if not admin_password:
            print("  ⚠ DEV_ADMIN_PASSWORD not set; skipping admin creation")
        else:
            user = await uow.users.get_by_email(admin_email)
            if user is None:
                super_role_result = await uow.session.execute(
                    select(Role).where(Role.name == "SUPER_ADMIN")
                )
                super_role = super_role_result.scalars().first()
                user = User(
                    email=admin_email,
                    password_hash=hash_password(admin_password),
                    status=UserStatus.ACTIVE,
                    roles=[super_role] if super_role else [],
                )
                await uow.users.create(user)
                await uow.commit()
                print(f"  ✓ Dev admin created: {admin_email}")
            else:
                super_role_result = await uow.session.execute(
                    select(Role).where(Role.name == "SUPER_ADMIN")
                )
                super_role = super_role_result.scalars().first()
                if super_role and super_role not in user.roles:
                    user.roles.append(super_role)
                    await uow.commit()
                print(f"  ✓ Dev admin already exists: {admin_email}")

        # ── 4. Leave types ───────────────────────────────────────
        leave_types = [
            {"name": "Annual Leave", "code": "ANNUAL", "max_days_per_year": Decimal("21.0")},
            {"name": "Sick Leave", "code": "SICK", "max_days_per_year": Decimal("12.0")},
        ]
        for lt in leave_types:
            result = await uow.session.execute(
                select(LeaveType).where(LeaveType.code == lt["code"])
            )
            existing = result.scalars().first()
            if existing is None:
                uow.session.add(
                    LeaveType(
                        name=lt["name"],
                        code=lt["code"],
                        max_days_per_year=lt["max_days_per_year"],
                        is_paid=True,
                        is_active=True,
                    )
                )
        await uow.commit()
        print("  ✓ Leave types seeded")

    print("Done ✓")


if __name__ == "__main__":
    asyncio.run(seed())
