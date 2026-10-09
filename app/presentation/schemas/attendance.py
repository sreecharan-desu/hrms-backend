"""Attendance Pydantic schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.domain.attendance.enums import AttendanceStatus


class ManualAttendanceRequest(BaseModel):
    employee_id: str
    work_date: date
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: AttendanceStatus = AttendanceStatus.PRESENT
    remarks: str | None = Field(None, max_length=500)


class UpdateAttendanceRequest(BaseModel):
    check_in: datetime | None = None
    check_out: datetime | None = None
    status: AttendanceStatus | None = None
    remarks: str | None = Field(None, max_length=500)
