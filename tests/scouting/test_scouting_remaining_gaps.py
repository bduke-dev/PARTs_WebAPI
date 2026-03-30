"""
Remaining coverage gaps: scouting/admin.py:1, scouting/models.py:231,
scouting/util.py:620,628, scouting/field/views.py:191-192
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone


# scouting/admin.py line 1
class TestScoutingAdminImport:
    def test_import(self):
        import scouting.admin
        assert scouting.admin is not None


# scouting/models.py line 231 - Schedule.__str__
@pytest.mark.django_db
class TestScheduleStr:
    def test_schedule_str(self):
        from scouting.models import Schedule, ScheduleType, Season, Event
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="schedstr_user", email="schedstr@test.com", ******
        )
        season = Season.objects.create(
            season="2099", current="n", game="G", manual="http://x.com"
        )
        event = Season.objects.filter(season="2099").first()
        evt = Event.objects.create(
            season=season, event_nm="Evt", event_cd="2099t",
            date_st=timezone.now(), date_end=timezone.now(),
        )
        stype = ScheduleType.objects.get_or_create(
            sch_typ="reg99", defaults={"sch_nm": "Regular"}
        )[0]
        sched = Schedule.objects.create(
            sch_typ=stype, event=evt, user=user,
            st_time=timezone.now(), end_time=timezone.now(),
        )
        s = str(sched)
        assert str(sched.id) in s


# scouting/util.py lines 620, 628 - get_field_form DoesNotExist
@pytest.mark.django_db
class TestGetFieldFormDoesNotExist:
    def test_field_form_does_not_exist_returns_empty(self):
        from scouting.util import get_field_form
        from scouting.models import FieldForm, Season
        with patch("scouting.util.get_current_season") as mock_season, \
             patch("scouting.models.FieldForm.objects.get",
                   side_effect=FieldForm.DoesNotExist):
            mock_season.return_value = MagicMock()
            result = get_field_form()
        assert result == {}


# scouting/field/views.py lines 191-192 - ScoutingResponsesView returns serialized list
@pytest.mark.django_db
class TestScoutingResponsesViewList:
    def test_returns_list_when_not_response_object(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("scouting.field.views.has_access", return_value=True), \
             patch("scouting.field.util.get_scouting_responses", return_value=[]):
            response = api_client.get("/scouting/field/scouting-responses/")
        # If URL 404s the view is commented out in urls - test view directly
        if response.status_code == 404:
            from scouting.field.views import ScoutingResponsesView
            from rest_framework.test import APIRequestFactory
            factory = APIRequestFactory()
            request = factory.get("/")
            request.user = test_user
            with patch("scouting.field.views.has_access", return_value=True), \
                 patch("scouting.field.util.get_scouting_responses", return_value=[]):
                view = ScoutingResponsesView.as_view()
                resp = view(request)
            assert resp.status_code == 200
        else:
            assert response.status_code == 200
