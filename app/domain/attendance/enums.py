"""Attendance domain enums – pure Python, no ORM dependency."""

from __future__ import annotations

from enum import StrEnum


class AttendanceStatus(StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    HALF_DAY = "HALF_DAY"
    LATE = "LATE"
    ON_LEAVE = "ON_LEAVE"
    HOLIDAY = "HOLIDAY"
    WEEKEND = "WEEKEND"
    WORK_FROM_HOME = "WORK_FROM_HOME"


class AttendanceSource(StrEnum):
    SELF = "SELF"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"
    BIOMETRIC = "BIOMETRIC"
    MOBILE = "MOBILE"
