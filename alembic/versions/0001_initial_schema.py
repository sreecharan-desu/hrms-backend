"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-10-09
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── permissions ───────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(120), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── roles ─────────────────────────────────────────────────────
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(60), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── role_permissions ──────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── users ─────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_status", "users", ["status"])
    op.create_index("ix_users_created_at", "users", ["created_at"])

    # ── user_roles ────────────────────────────────────────────────
    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    )

    # ── refresh_tokens ────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("family_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"])

    # ── password_reset_tokens ─────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])

    # ── departments ───────────────────────────────────────────────
    op.create_table(
        "departments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("parent_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("head_employee_id", sa.String(36), nullable=True),  # FK added after employees
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_departments_code"),
    )
    op.create_index("ix_departments_parent_id", "departments", ["parent_id"])

    # ── employees ─────────────────────────────────────────────────
    op.create_table(
        "employees",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_code", sa.String(30), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("date_of_birth", sa.Date, nullable=True),
        sa.Column("joining_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("designation", sa.String(120), nullable=True),
        sa.Column("manager_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("emergency_contact", postgresql.JSONB, nullable=True),
        sa.Column("profile", postgresql.JSONB, nullable=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_code", name="uq_employees_employee_code"),
        sa.UniqueConstraint("email", name="uq_employees_email"),
        sa.UniqueConstraint("user_id", name="uq_employees_user_id"),
    )
    op.create_index("ix_employees_department_id", "employees", ["department_id"])
    op.create_index("ix_employees_manager_id", "employees", ["manager_id"])
    op.create_index("ix_employees_status", "employees", ["status"])
    op.create_index("ix_employees_created_at", "employees", ["created_at"])

    # Add deferred FK from departments.head_employee_id → employees.id
    op.create_foreign_key(
        "fk_departments_head_employee_id",
        "departments",
        "employees",
        ["head_employee_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── employee_compensations ────────────────────────────────────
    op.create_table(
        "employee_compensations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("salary", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", name="uq_employee_compensations_employee_id"),
    )

    # ── attendances ───────────────────────────────────────────────
    op.create_table(
        "attendances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("work_date", sa.Date, nullable=False),
        sa.Column("check_in", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PRESENT"),
        sa.Column("source", sa.String(20), nullable=False, server_default="SYSTEM"),
        sa.Column("remarks", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("employee_id", "work_date", name="uq_attendances_employee_date"),
    )
    op.create_index("ix_attendances_employee_id", "attendances", ["employee_id"])
    op.create_index("ix_attendances_work_date", "attendances", ["work_date"])
    op.create_index("ix_attendances_status", "attendances", ["status"])

    # ── leave_types ───────────────────────────────────────────────
    op.create_table(
        "leave_types",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(60), unique=True, nullable=False),
        sa.Column("code", sa.String(20), unique=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("max_days_per_year", sa.Numeric(5, 1), nullable=False),
        sa.Column("is_paid", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── leave_balances ────────────────────────────────────────────
    op.create_table(
        "leave_balances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.String(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("year", sa.Integer, nullable=False),
        sa.Column("total_days", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("used_days", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("pending_days", sa.Numeric(5, 1), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leave_balances_employee_id", "leave_balances", ["employee_id"])
    op.create_index("ix_leave_balances_leave_type_id", "leave_balances", ["leave_type_id"])

    # ── leave_requests ────────────────────────────────────────────
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("leave_type_id", sa.String(36), sa.ForeignKey("leave_types.id", ondelete="CASCADE"), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("days", sa.Numeric(5, 1), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_comment", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leave_requests_employee_id", "leave_requests", ["employee_id"])
    op.create_index("ix_leave_requests_status", "leave_requests", ["status"])
    op.create_index("ix_leave_requests_leave_type_id", "leave_requests", ["leave_type_id"])
    op.create_index("ix_leave_requests_created_at", "leave_requests", ["created_at"])

    # ── documents ─────────────────────────────────────────────────
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.BigInteger, nullable=False),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_documents_employee_id", "documents", ["employee_id"])
    op.create_index("ix_documents_status", "documents", ["status"])
    op.create_index("ix_documents_created_at", "documents", ["created_at"])

    # ── jobs (recruitment) ────────────────────────────────────────
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("department_id", sa.String(36), sa.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("location", sa.String(120), nullable=True),
        sa.Column("employment_type", sa.String(30), nullable=True),
        sa.Column("salary_min", sa.Numeric(14, 2), nullable=True),
        sa.Column("salary_max", sa.Numeric(14, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="INR"),
        sa.Column("positions", sa.Integer, nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("hiring_manager_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closes_at", sa.Date, nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_department_id", "jobs", ["department_id"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    # ── job_applications ──────────────────────────────────────────
    op.create_table(
        "job_applications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("job_id", sa.String(36), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_name", sa.String(200), nullable=False),
        sa.Column("candidate_email", sa.String(255), nullable=False),
        sa.Column("candidate_phone", sa.String(20), nullable=True),
        sa.Column("resume_document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stage", sa.String(20), nullable=False, server_default="APPLIED"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_job_applications_job_id", "job_applications", ["job_id"])
    op.create_index("ix_job_applications_stage", "job_applications", ["stage"])
    op.create_index("ix_job_applications_created_at", "job_applications", ["created_at"])

    # ── interviews ────────────────────────────────────────────────
    op.create_table(
        "interviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("application_id", sa.String(36), sa.ForeignKey("job_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("interviewer_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer, nullable=False, server_default="60"),
        sa.Column("interview_type", sa.String(30), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="SCHEDULED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_interviews_application_id", "interviews", ["application_id"])
    op.create_index("ix_interviews_interviewer_id", "interviews", ["interviewer_id"])

    # ── interview_feedbacks ───────────────────────────────────────
    op.create_table(
        "interview_feedbacks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("interview_id", sa.String(36), sa.ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evaluator_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rating", sa.Integer, nullable=True),
        sa.Column("strengths", sa.Text, nullable=True),
        sa.Column("weaknesses", sa.Text, nullable=True),
        sa.Column("recommendation", sa.String(30), nullable=True),
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_interview_feedbacks_interview_id", "interview_feedbacks", ["interview_id"])

    # ── performance_cycles ────────────────────────────────────────
    op.create_table(
        "performance_cycles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── performance_reviews ───────────────────────────────────────
    op.create_table(
        "performance_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cycle_id", sa.String(36), sa.ForeignKey("performance_cycles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("employee_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reviewer_id", sa.String(36), sa.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("self_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("manager_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("final_rating", sa.Numeric(3, 1), nullable=True),
        sa.Column("self_comments", sa.Text, nullable=True),
        sa.Column("manager_comments", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_performance_reviews_employee_id", "performance_reviews", ["employee_id"])
    op.create_index("ix_performance_reviews_cycle_id", "performance_reviews", ["cycle_id"])
    op.create_index("ix_performance_reviews_status", "performance_reviews", ["status"])

    # ── performance_goals ─────────────────────────────────────────
    op.create_table(
        "performance_goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("review_id", sa.String(36), sa.ForeignKey("performance_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("weight", sa.Numeric(5, 2), nullable=True),
        sa.Column("target_date", sa.Date, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="OPEN"),
        sa.Column("achievement", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_performance_goals_review_id", "performance_goals", ["review_id"])

    # ── notifications ─────────────────────────────────────────────
    op.create_table(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("channel", sa.String(20), nullable=False, server_default="IN_APP"),
        sa.Column("is_read", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("link", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    # ── audit_logs ────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("old_values", postgresql.JSONB, nullable=True),
        sa.Column("new_values", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_entity_type_entity_id", "audit_logs", ["entity_type", "entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── background_jobs ───────────────────────────────────────────
    op.create_table(
        "background_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(120), nullable=False),
        sa.Column("payload", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_background_jobs_status", "background_jobs", ["status"])
    op.create_index("ix_background_jobs_available_at", "background_jobs", ["available_at"])
    op.create_index("ix_background_jobs_type", "background_jobs", ["type"])


def downgrade() -> None:
    op.drop_table("background_jobs")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("performance_goals")
    op.drop_table("performance_reviews")
    op.drop_table("performance_cycles")
    op.drop_table("interview_feedbacks")
    op.drop_table("interviews")
    op.drop_table("job_applications")
    op.drop_table("jobs")
    op.drop_table("documents")
    op.drop_table("leave_requests")
    op.drop_table("leave_balances")
    op.drop_table("leave_types")
    op.drop_table("attendances")
    op.drop_table("employee_compensations")
    op.drop_constraint("fk_departments_head_employee_id", "departments", type_="foreignkey")
    op.drop_table("employees")
    op.drop_table("departments")
    op.drop_table("refresh_tokens")
    op.drop_table("password_reset_tokens")
    op.drop_table("user_roles")
    op.drop_table("users")
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
