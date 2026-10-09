"""Unit tests for attendance pure-domain rules."""


from app.domain.attendance.enums import AttendanceSource, AttendanceStatus


class TestAttendanceStatusEnum:
    def test_all_expected_statuses_exist(self) -> None:
        expected = {"PRESENT", "ABSENT", "HALF_DAY", "LATE", "ON_LEAVE", "HOLIDAY", "WEEKEND", "WORK_FROM_HOME"}
        actual = {s.value for s in AttendanceStatus}
        assert expected == actual

    def test_str_representation(self) -> None:
        assert str(AttendanceStatus.PRESENT) == "PRESENT"
        assert AttendanceStatus.LATE == "LATE"


class TestAttendanceSourceEnum:
    def test_all_expected_sources_exist(self) -> None:
        expected = {"SELF", "MANUAL", "SYSTEM", "BIOMETRIC", "MOBILE"}
        actual = {s.value for s in AttendanceSource}
        assert expected == actual

    def test_self_source(self) -> None:
        assert AttendanceSource.SELF == "SELF"
        assert AttendanceSource.MANUAL == "MANUAL"
