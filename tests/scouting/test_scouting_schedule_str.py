"""
Test for Schedule.__str__ (src/scouting/models.py line 231).
"""
import pytest
from django.utils import timezone


@pytest.mark.django_db
class TestScheduleStr:
    """Cover src/scouting/models.py line 231 - Schedule.__str__"""

    def test_schedule_str(self):
        from scouting.models import Season, Event, Schedule, ScheduleType
        from django.contrib.auth import get_user_model
        User = get_user_model()

        season = Season.objects.create(season="2024sch", current="n", game="G", manual="http://x.com")
        event = Event.objects.create(
            season=season,
            event_nm="Test Event",
            event_cd="2024tst",
            date_st=timezone.now(),
            date_end=timezone.now(),
        )
        user = User.objects.create_user(username="schstr", email="schstr@example.com", password="pass")
        sch_type = ScheduleType.objects.get_or_create(sch_typ="pit", defaults={"sch_nm": "Pit"})[0]

        sched = Schedule.objects.create(
            sch_typ=sch_type,
            event=event,
            user=user,
            st_time=timezone.now(),
            end_time=timezone.now(),
        )

        s = str(sched)
        assert str(sched.id) in s
        assert "pit" in s or str(event) in s or str(user) in s
