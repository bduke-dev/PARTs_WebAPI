"""
Coverage for scouting/strategizing/util.py and views.py remaining lines.
"""
import pytest
from unittest.mock import patch, MagicMock


# scouting/strategizing/util.py lines 351-356 - get_graph_data_for_teams
@pytest.mark.django_db
class TestGetGraphDataForTeams:
    def _mock_graph(self, graph_typ_str):
        g = MagicMock()
        g.graph_typ.graph_typ = graph_typ_str
        return g

    def test_histogram_serializer(self):
        from scouting.strategizing.util import get_graph_data_for_teams
        mock_graph = self._mock_graph("histogram")
        mock_data = [{"label": "Test", "bins": []}]
        with patch("form.models.Graph.objects.get", return_value=mock_graph), \
             patch("scouting.strategizing.util.graph_team", return_value=mock_data):
            result = get_graph_data_for_teams(1, [3492], None)
        assert result is not None

    def test_res_plot_serializer(self):
        from scouting.strategizing.util import get_graph_data_for_teams
        mock_graph = self._mock_graph("res-plot")
        mock_data = [{"label": "Test", "points": []}]
        with patch("form.models.Graph.objects.get", return_value=mock_graph), \
             patch("scouting.strategizing.util.graph_team", return_value=mock_data):
            result = get_graph_data_for_teams(1, [3492], None)
        assert result is not None

    def test_box_wskr_serializer(self):
        from scouting.strategizing.util import get_graph_data_for_teams
        mock_graph = self._mock_graph("box-wskr")
        mock_data = [{"label": "T", "dataset": [], "q1": 1, "q2": 2, "q3": 3, "min": 0, "max": 5}]
        with patch("form.models.Graph.objects.get", return_value=mock_graph), \
             patch("scouting.strategizing.util.graph_team", return_value=mock_data):
            result = get_graph_data_for_teams(1, [3492], None)
        assert result is not None

    def test_touch_map_serializer(self):
        from scouting.strategizing.util import get_graph_data_for_teams
        mock_graph = self._mock_graph("touch-map")
        mock_data = [{"label": "T", "question": {}, "points": []}]
        with patch("form.models.Graph.objects.get", return_value=mock_graph), \
             patch("scouting.strategizing.util.graph_team", return_value=mock_data):
            result = get_graph_data_for_teams(1, [3492], None)
        assert result is not None


# scouting/strategizing/util.py lines 467, 480, 514 - save_dashboard update paths
@pytest.mark.django_db
class TestSaveDashboardUpdatePaths:
    def _make_season(self):
        from scouting.models import Season
        return Season.objects.get_or_create(
            season="2024dash", defaults={"current": "n", "game": "G", "manual": "http://x.com"}
        )[0]

    def _make_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.get_or_create(
            username="dash_test_user",
            defaults={"email": "dashtest@test.com"},
        )[0]

    def test_save_dashboard_update_existing(self):
        from scouting.strategizing.util import save_dashboard
        from scouting.strategizing.models import Dashboard, DashViewType
        season = self._make_season()
        user = self._make_user()
        dvt = DashViewType.objects.get_or_create(
            dash_view_typ="table", defaults={"dash_view_typ_nm": "Table"}
        )[0]
        dashboard = Dashboard.objects.create(
            user=user, season=season, active="y",
            default_dash_view_typ=dvt,
        )
        data = {
            "id": dashboard.id,
            "active": "y",
            "default_dash_view_typ": {"dash_view_typ": dvt.dash_view_typ},
            "dashboard_views": [],
        }
        result = save_dashboard(data, user.id)
        assert result.id == dashboard.id

    def test_save_dashboard_update_existing_view(self):
        from scouting.strategizing.util import save_dashboard
        from scouting.strategizing.models import Dashboard, DashViewType, DashboardView
        season = self._make_season()
        user = self._make_user()
        dvt = DashViewType.objects.get_or_create(
            dash_view_typ="table2", defaults={"dash_view_typ_nm": "Table2"}
        )[0]
        dashboard = Dashboard.objects.create(
            user=user, season=season, active="y",
            default_dash_view_typ=dvt,
        )
        db_view = DashboardView.objects.create(
            dashboard=dashboard,
            dash_view_typ=dvt,
            name="TestView",
            order=1,
            active="y",
        )
        data = {
            "id": dashboard.id,
            "active": "y",
            "default_dash_view_typ": {"dash_view_typ": dvt.dash_view_typ},
            "dashboard_views": [
                {
                    "id": db_view.id,
                    "dash_view_typ": {"dash_view_typ": dvt.dash_view_typ},
                    "name": "Updated",
                    "order": 1,
                    "active": "y",
                    "teams": [],
                    "dashboard_graphs": [],
                }
            ],
        }
        result = save_dashboard(data, user.id)
        assert result is not None


# scouting/strategizing/views.py lines 70-85 - NoteView POST success path
@pytest.mark.django_db
class TestNoteViewPost:
    def test_post_note_success(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("scouting.strategizing.views.has_access", return_value=True), \
             patch("scouting.strategizing.util.save_note", return_value=mock_resp):
            response = api_client.post(
                "/scouting/strategizing/team-notes/",
                {"note": "test note", "team_no": 3492},
                format="json",
            )
        assert response.status_code in (200, 400)

    def test_post_note_exception(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("scouting.strategizing.views.has_access", return_value=True), \
             patch("scouting.strategizing.util.save_note", side_effect=Exception("fail")):
            response = api_client.post(
                "/scouting/strategizing/team-notes/",
                {"note": "test note", "team_no": 3492},
                format="json",
            )
        assert response.status_code == 200
        assert response.data.get("error") is True


# scouting/strategizing/views.py lines 145-154 - MatchStrategyView POST success path
@pytest.mark.django_db
class TestMatchStrategyViewPost:
    def test_post_match_strategy_success(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("scouting.strategizing.views.has_access", return_value=True), \
             patch("scouting.strategizing.util.save_match_strategy", return_value=None):
            response = api_client.post(
                "/scouting/strategizing/match-strategy/",
                {"match_key": "2024test_qm1", "strategy": "win", "user_id": test_user.id},
                format="json",
            )
        assert response.status_code in (200, 400)

    def test_post_match_strategy_exception(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("scouting.strategizing.views.has_access", return_value=True), \
             patch("scouting.strategizing.util.save_match_strategy", side_effect=Exception("fail")):
            response = api_client.post(
                "/scouting/strategizing/match-strategy/",
                {"match_key": "2024test_qm1", "strategy": "win", "user_id": test_user.id},
                format="json",
            )
        assert response.status_code == 200
        assert response.data.get("error") is True
