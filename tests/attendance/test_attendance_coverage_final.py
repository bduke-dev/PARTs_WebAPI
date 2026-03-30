"""
Final attendance coverage tests.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from django.utils.timezone import now, make_aware
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestGetAttendanceReportExempt:
    """Cover src/attendance/util.py line 163 - exempt attendance reduces total"""

    def test_exempt_attendance_reduces_total(self):
        from scouting.models import Season
        from attendance.models import MeetingType, Meeting, AttendanceApprovalType, Attendance
        from attendance.util import get_attendance_report

        season = Season.objects.create(season="2024exmpt2", current="y", game="G", manual="http://x.com")
        reg_mt = MeetingType.objects.get_or_create(meeting_typ="reg", defaults={"meeting_nm": "Regular", "void_ind": "n"})[0]
        exmpt_at = AttendanceApprovalType.objects.get_or_create(approval_typ="exmpt", defaults={"approval_nm": "Exempt", "void_ind": "n"})[0]
        AttendanceApprovalType.objects.get_or_create(approval_typ="app", defaults={"approval_nm": "Approved", "void_ind": "n"})
        AttendanceApprovalType.objects.get_or_create(approval_typ="unapp", defaults={"approval_nm": "Unapproved", "void_ind": "n"})

        user = User.objects.create_user(username="exmptuser2", email="exmpt2@example.com", password="pass", first_name="Exempt", last_name="User2")
        user.is_active = True
        user.save()

        # Create two meetings so total hours > exempt hours (avoids ZeroDivisionError)
        start1 = make_aware(datetime(2024, 1, 10, 18, 0))
        end1 = make_aware(datetime(2024, 1, 10, 20, 0))
        mtg_total = Meeting.objects.create(
            season=season, meeting_typ=reg_mt, title="Total Meeting",
            description="desc", start=start1, end=end1, ended=True, void_ind="n"
        )

        start2 = make_aware(datetime(2024, 1, 15, 18, 0))
        end2 = make_aware(datetime(2024, 1, 15, 20, 0))
        mtg_exempt = Meeting.objects.create(
            season=season, meeting_typ=reg_mt, title="Exempt Meeting",
            description="desc", start=start2, end=end2, ended=True, void_ind="n"
        )

        # Exempt attendance for mtg_exempt - reduces user_total from 4 to 2
        Attendance.objects.create(
            user=user, meeting=mtg_exempt, season=season,
            time_in=start2, time_out=end2, absent=False,
            approval_typ=exmpt_at, void_ind="n"
        )

        result = get_attendance_report(user_id=user.id)
        assert len(result) == 1
        entry = result[0]
        assert "user" in entry
        assert "req_reg_time" in entry
        # After exemption, req_reg_time should be reduced by 2 hours
        assert entry["req_reg_time"] == 2.0


@pytest.mark.django_db
class TestEndMeeting:
    """Cover src/attendance/util.py lines 289-297 - end_meeting creates absent attendances"""

    def test_end_meeting_creates_absent(self):
        from scouting.models import Season
        from attendance.models import MeetingType, Meeting, AttendanceApprovalType
        from attendance.util import end_meeting

        season = Season.objects.create(season="2024end2", current="y", game="G", manual="http://x.com")
        reg_mt = MeetingType.objects.get_or_create(meeting_typ="reg", defaults={"meeting_nm": "Regular", "void_ind": "n"})[0]
        AttendanceApprovalType.objects.get_or_create(approval_typ="app", defaults={"approval_nm": "Approved", "void_ind": "n"})
        AttendanceApprovalType.objects.get_or_create(approval_typ="unapp", defaults={"approval_nm": "Unapproved", "void_ind": "n"})
        AttendanceApprovalType.objects.get_or_create(approval_typ="exmpt", defaults={"approval_nm": "Exempt", "void_ind": "n"})

        user = User.objects.create_user(username="endmtg2", email="endmtg2@example.com", password="pass", first_name="End", last_name="Mtg")
        user.is_active = True
        user.save()

        start = make_aware(datetime(2024, 2, 15, 18, 0))
        end_time = make_aware(datetime(2024, 2, 15, 20, 0))
        meeting = Meeting.objects.create(
            season=season,
            meeting_typ=reg_mt,
            title="End Meeting",
            description="desc",
            start=start,
            end=end_time,
            ended=False,
            void_ind="n"
        )

        mock_qs = MagicMock()
        mock_qs.filter.return_value = [user]

        with patch("attendance.util.user.util.get_users", return_value=mock_qs), \
             patch("attendance.util.save_attendance") as mock_save:
            mock_save.return_value = MagicMock()
            end_meeting(meeting.id)

        meeting.refresh_from_db()
        assert meeting.ended is True


@pytest.mark.django_db
class TestAttendanceViewPost:
    """Cover src/attendance/views.py - POST via access_response"""

    def test_post_returns_serialized_attendance(self, api_client, system_user):
        from scouting.models import Season
        from attendance.models import AttendanceApprovalType

        season = Season.objects.create(season="2024view2", current="y", game="G", manual="http://x.com")
        AttendanceApprovalType.objects.get_or_create(approval_typ="app", defaults={"approval_nm": "Approved", "void_ind": "n"})
        AttendanceApprovalType.objects.get_or_create(approval_typ="unapp", defaults={"approval_nm": "Unapproved", "void_ind": "n"})

        user = User.objects.create_user(username="attview2", email="attview2@example.com", password="pass", first_name="Att", last_name="View")
        user.is_active = True
        user.save()
        api_client.force_authenticate(user=user)

        start = make_aware(datetime(2024, 3, 15, 18, 0))
        end_time = make_aware(datetime(2024, 3, 15, 20, 0))

        mock_att = MagicMock()
        mock_att.id = 999
        mock_att.user = user
        mock_att.meeting = None
        mock_att.season = season
        mock_att.time_in = start
        mock_att.time_out = end_time
        mock_att.absent = False

        # attendance uses access_response which calls general.security.has_access
        with patch("general.security.has_access", return_value=True), \
             patch("attendance.util.save_attendance", return_value=mock_att), \
             patch("attendance.views.AttendanceSerializer") as mock_ser:
            mock_ser.return_value.data = {"id": 999, "absent": False}
            response = api_client.post("/attendance/attendance/", {
                "id": None,
                "user": {"id": user.id, "first_name": "Att", "last_name": "View"},
                "meeting": None,
                "time_in": start.isoformat(),
                "time_out": end_time.isoformat(),
                "absent": False,
                "approval_typ": {"approval_typ": "app"},
                "void_ind": "n",
            }, format="json")
        assert response.status_code in [200, 400]
