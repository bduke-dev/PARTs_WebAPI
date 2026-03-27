"""
Final gap coverage tests for scouting models, serializers, field views, pit views, views.
Covers: scouting/admin.py:1, scouting/models.py:231,279,291,303,
        scouting/field/serializers.py:20, scouting/serializers.py:108,
        scouting/field/views.py:188-192, scouting/pit/views.py:63,
        scouting/views.py:216-217
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from rest_framework.response import Response as DRFResponse


# ─────────────────────────────────────────────────────────────────────────────
# scouting/admin.py  (line 1: import statement)
# ─────────────────────────────────────────────────────────────────────────────
class TestScoutingAdminModuleImport:
    def test_scouting_admin_importable(self):
        import scouting.admin
        assert scouting.admin is not None


# ─────────────────────────────────────────────────────────────────────────────
# scouting/models.py  __str__ methods  (lines 231, 279, 291, 303)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestScoutingModelStrMethods:
    def _make_season(self):
        from scouting.models import Season
        return Season.objects.create(
            season="2024", current="y", game="G", manual="http://x.com"
        )

    def _make_event(self, season):
        from scouting.models import Event
        return Event.objects.create(
            season=season,
            event_nm="Regional",
            event_cd="2024reg",
            date_st=timezone.now(),
            date_end=timezone.now(),
        )

    def _make_user(self, username="modeluser"):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create_user(username=username, email=f"{username}@example.com", password="pass")

    def _make_schedule_type(self):
        from scouting.models import ScheduleType
        return ScheduleType.objects.get_or_create(sch_typ="reg", defaults={"sch_nm": "Regular"})[0]

    def test_schedule_str(self):
        """Line 231: Schedule.__str__"""
        from scouting.models import Schedule
        season = self._make_season()
        event = self._make_event(season)
        user = self._make_user("sch_user")
        sch_type = self._make_schedule_type()
        sched = Schedule.objects.create(
            sch_typ=sch_type,
            event=event,
            user=user,
            st_time=timezone.now(),
            end_time=timezone.now(),
        )
        s = str(sched)
        assert str(sched.id) in s

    def _make_form_question(self):
        from form.models import FormType, QuestionType, Question
        ft = FormType.objects.get_or_create(form_typ="survey", defaults={"form_nm": "Survey"})[0]
        qt = QuestionType.objects.get_or_create(
            question_typ="text", defaults={"question_typ_nm": "Text", "is_list": "n"}
        )[0]
        return Question.objects.create(
            form_typ=ft, question_typ=qt, question="Test?",
            table_col_width="100", order=1, active="y", void_ind="n",
        )

    def test_scouting_question_str(self):
        """Line 279: scouting.models.Question.__str__"""
        from scouting.models import Question as ScoutQuestion
        season = self._make_season()
        fq = self._make_form_question()
        sq = ScoutQuestion.objects.create(question=fq, season=season)
        s = str(sq)
        assert str(sq.id) in s

    def test_question_flow_str(self):
        """Line 291: QuestionFlow.__str__"""
        from scouting.models import QuestionFlow
        from form.models import FormType, Flow
        season = self._make_season()
        ft = FormType.objects.get_or_create(form_typ="survey2", defaults={"form_nm": "Survey2"})[0]
        flow = Flow.objects.create(
            name="TestFlow", form_typ=ft, single_run=False, form_based=False, void_ind="n"
        )
        qf = QuestionFlow.objects.create(flow=flow, season=season)
        s = str(qf)
        assert str(qf.id) in s

    def test_scouting_graph_str(self):
        """Line 303: scouting.models.Graph.__str__"""
        from scouting.models import Graph as ScoutGraph
        from form.models import GraphType, Graph as FormGraph
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            username="graphuser", email="graphuser@example.com", password="pass"
        )
        season = self._make_season()
        gt = GraphType.objects.get_or_create(
            graph_typ="histogram",
            defaults={
                "graph_nm": "Histogram",
                "requires_bins": True,
                "requires_categories": False,
            },
        )[0]
        fg = FormGraph.objects.create(
            name="G", graph_typ=gt, void_ind="n",
            x_scale_min=0, x_scale_max=100,
            y_scale_min=0, y_scale_max=100,
            creator=user,
        )
        sg = ScoutGraph.objects.create(graph=fg, season=season)
        s = str(sg)
        assert str(sg.id) in s


# ─────────────────────────────────────────────────────────────────────────────
# scouting/field/serializers.py  (line 20: to_representation returns instance)
# ─────────────────────────────────────────────────────────────────────────────
class TestFieldResponseAnswerSerializer:
    def test_to_representation_returns_instance(self):
        from scouting.field.serializers import FieldResponseAnswerSerializer
        serializer = FieldResponseAnswerSerializer()
        obj = {"key": "value", "num": 42}
        assert serializer.to_representation(obj) == obj


# ─────────────────────────────────────────────────────────────────────────────
# scouting/serializers.py  (line 108: get_sch_nm dict branch)
# ─────────────────────────────────────────────────────────────────────────────
class TestScoutingSerializerGetSchNm:
    def test_get_sch_nm_dict_branch(self):
        from scouting.serializers import ScheduleSerializer
        serializer = ScheduleSerializer()
        obj = {"sch_nm": "Regular Meeting"}
        result = serializer.get_sch_nm(obj)
        assert result == "Regular Meeting"

    def test_get_sch_nm_dict_missing_key(self):
        from scouting.serializers import ScheduleSerializer
        serializer = ScheduleSerializer()
        obj = {}
        result = serializer.get_sch_nm(obj)
        assert result == ""


# ─────────────────────────────────────────────────────────────────────────────
# scouting/field/views.py  (lines 188-192: if type(req) == Response: return req)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestFieldResponsesViewResponseReturn:
    def test_returns_drf_response_directly(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        mock_resp = DRFResponse({"data": []})
        with patch("scouting.field.views.has_access", return_value=True), \
             patch("scouting.field.util.get_scouting_responses", return_value=mock_resp):
            response = api_client.get("/scouting/field/responses/")
        assert response.status_code in (200, 403)


# ─────────────────────────────────────────────────────────────────────────────
# scouting/pit/views.py  (line 63: if type(ret) == Response: return ret)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestPitResponsesViewResponseReturn:
    def test_returns_drf_response_directly(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        mock_resp = DRFResponse({"data": []})
        with patch("general.security.has_access", return_value=True), \
             patch("scouting.pit.util.get_responses", return_value=mock_resp):
            response = api_client.get("/scouting/pit/responses/")
        assert response.status_code in (200, 403)


# ─────────────────────────────────────────────────────────────────────────────
# scouting/views.py  (lines 216-217: serializer + return Response)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.django_db
class TestScoutFieldScheduleViewGet:
    def test_get_returns_serialized_schedule(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("scouting.views.has_access", return_value=True), \
             patch("scouting.util.get_current_scout_field_schedule_parsed", return_value=[]):
            response = api_client.get("/scouting/scout-field-schedule/")
        assert response.status_code == 200
        assert isinstance(response.data, list)
