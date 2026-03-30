"""
Coverage tests for scouting/admin/views.py.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


def make_user(username):
    return User.objects.create_user(username=username, email=f"{username}@example.com", password="pass")


@pytest.mark.django_db
class TestSeasonViewExceptionPaths:
    """Lines 120-121, 141-143, 151-152"""

    def test_post_season_exception(self, api_client):
        """Lines 120-121: POST season raises exception"""
        user = make_user("sv_post")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_season", side_effect=Exception("DB error")):
            response = api_client.post("/scouting/admin/season/", {
                "season": "2099", "current": "n", "game": "TestGame", "manual": "http://x.com"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()

    def test_put_season_has_access(self, api_client):
        """Lines 141-143: PUT season - has_access=True"""
        user = make_user("sv_put")
        api_client.force_authenticate(user=user)
        from rest_framework.response import Response
        mock_season_response = Response({"result": "ok"})
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_season", return_value=mock_season_response):
            response = api_client.put("/scouting/admin/season/", {
                "season": "2025", "current": "n", "game": "G", "manual": "http://x.com"
            }, format="json")
        assert response.status_code == 200

    def test_put_season_exception(self, api_client):
        """Lines 151-152: PUT season - raises exception"""
        user = make_user("sv_putex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_season", side_effect=Exception("DB error")):
            response = api_client.put("/scouting/admin/season/", {
                "season": "2025", "current": "n", "game": "G", "manual": "http://x.com"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestRemoveTeamToEventViewPaths:
    """Lines 357-364: DELETE team from event - access denied + exception"""

    def test_delete_team_from_event_access_denied(self, api_client):
        """Line 357: access denied"""
        user = make_user("rte_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.post("/scouting/admin/remove-team-to-event/", {
                "id": None, "season_id": 1, "event_nm": "x", "date_st": "2024-01-01T00:00:00Z",
                "date_end": "2024-01-02T00:00:00Z", "event_cd": "x", "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()

    def test_delete_team_from_event_exception(self, api_client):
        """Lines 360-364: exception path"""
        user = make_user("rte_ex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.remove_link_team_to_event", side_effect=Exception("err")):
            response = api_client.post("/scouting/admin/remove-team-to-event/", {
                "id": None, "season_id": 1, "event_nm": "x", "date_st": "2024-01-01T00:00:00Z",
                "date_end": "2024-01-02T00:00:00Z", "event_cd": "x", "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestMatchViewPaths:
    """Lines 398-405: POST match - access denied + exception"""

    def test_post_match_access_denied(self, api_client):
        user = make_user("match_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.post("/scouting/admin/match/", {
                "match_number": 1, "event": {"id": 1, "season_id": 1, "event_nm": "E",
                "date_st": "2024-01-01T00:00:00Z", "date_end": "2024-01-02T00:00:00Z",
                "event_cd": "2024e", "void_ind": "n"}, "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()

    def test_post_match_exception(self, api_client):
        user = make_user("match_ex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_match", side_effect=Exception("err")):
            response = api_client.post("/scouting/admin/match/", {
                "match_number": 1, "event": {"id": 1, "season_id": 1, "event_nm": "E",
                "date_st": "2024-01-01T00:00:00Z", "date_end": "2024-01-02T00:00:00Z",
                "event_cd": "2024e", "void_ind": "n"}, "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestScoutFieldScheduleViewPaths:
    """Lines 458-469: POST scout schedule - access denied + exception + success"""

    def test_post_scout_schedule_access_denied(self, api_client):
        user = make_user("sfs_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.post("/scouting/admin/scout-field-schedule/", {
                "event_id": 1, "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z",
                "red_one_id": None, "red_two_id": None, "red_three_id": None,
                "blue_one_id": None, "blue_two_id": None, "blue_three_id": None,
                "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()

    def test_post_scout_schedule_exception(self, api_client):
        user = make_user("sfs_ex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_scout_schedule", side_effect=Exception("err")):
            response = api_client.post("/scouting/admin/scout-field-schedule/", {
                "event_id": 1, "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z",
                "red_one_id": None, "red_two_id": None, "red_three_id": None,
                "blue_one_id": None, "blue_two_id": None, "blue_three_id": None,
                "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()

    def test_post_scout_schedule_success(self, api_client):
        """Line 460: success path - save called and return message"""
        user = make_user("sfs_ok")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_scout_schedule", return_value=MagicMock()):
            response = api_client.post("/scouting/admin/scout-field-schedule/", {
                "event_id": 1, "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z",
                "red_one_id": None, "red_two_id": None, "red_three_id": None,
                "blue_one_id": None, "blue_two_id": None, "blue_three_id": None,
                "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "saved" in str(response.data).lower() or "field schedule" in str(response.data).lower()


@pytest.mark.django_db
class TestScheduleViewPaths:
    """Lines 497-508: POST schedule - access denied + exception + success"""

    def test_post_schedule_access_denied(self, api_client):
        user = make_user("sch_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.post("/scouting/admin/schedule/", {
                "sch_typ": "pit", "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z", "user": None, "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()

    def test_post_schedule_exception(self, api_client):
        user = make_user("sch_ex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_schedule", side_effect=Exception("err")):
            response = api_client.post("/scouting/admin/schedule/", {
                "sch_typ": "pit", "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z", "user": None, "void_ind": "n"
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()

    def test_post_schedule_success(self, api_client):
        """Line 499: success path"""
        user = make_user("sch_ok")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_schedule", return_value=MagicMock()):
            response = api_client.post("/scouting/admin/schedule/", {
                "sch_typ": "pit", "st_time": "2024-01-01T18:00:00Z",
                "end_time": "2024-01-01T20:00:00Z", "user": None, "void_ind": "n"
            }, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestNotifyUserViewPaths:
    """Lines 534, 537: GET notify-user - sch_id and no params"""

    def test_get_notify_user_with_sch_id(self, api_client):
        """Line 534: sch_id param path"""
        user = make_user("notify_sch")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.notify_user", return_value="Notified") as mock_notify:
            response = api_client.get("/scouting/admin/notify-user/?sch_id=1")
        assert response.status_code == 200
        mock_notify.assert_called_once_with("1")

    def test_get_notify_user_no_params(self, api_client):
        """Line 537: No ID provided - raises exception"""
        user = make_user("notify_none")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True):
            response = api_client.get("/scouting/admin/notify-user/")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestScoutingUserInfoViewPaths:
    """Lines 567-569, 602: GET/POST scouting-user-info"""

    def test_get_scouting_user_info_access_denied(self, api_client):
        user = make_user("sui_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.get("/scouting/admin/scouting-user-info/")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()

    def test_get_scouting_user_info_success(self, api_client):
        """Lines 567-569: GET success path"""
        user = make_user("sui_get")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.get_scouting_user_info", return_value=[]):
            response = api_client.get("/scouting/admin/scouting-user-info/")
        assert response.status_code == 200

    def test_post_scouting_user_info_success(self, api_client):
        """Line 602: POST save called successfully"""
        user = make_user("sui_post")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_scouting_user_info") as mock_save:
            response = api_client.post("/scouting/admin/scouting-user-info/", {
                "user": {"id": user.id, "username": user.username, "first_name": "F",
                         "last_name": "L", "email": user.email, "is_active": True},
                "under_review": False,
                "group_leader": False,
                "eliminate_results": False,
            }, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestMarkScoutPresentViewPaths:
    """Lines 635-636: GET mark-scout-present"""

    def test_mark_scout_present_exception(self, api_client):
        user = make_user("msp_ex")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.util.get_scout_field_schedule", side_effect=Exception("not found")):
            response = api_client.get("/scouting/admin/mark-scout-present/?scout_field_sch_id=9999&user_id=1")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()

    def test_mark_scout_present_success(self, api_client):
        """Lines 635-636: success path"""
        user = make_user("msp_ok")
        api_client.force_authenticate(user=user)
        mock_sfs = MagicMock()
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.util.get_scout_field_schedule", return_value=mock_sfs), \
             patch("scouting.field.util.check_in_scout", return_value="Successfully checked in"):
            response = api_client.get("/scouting/admin/mark-scout-present/?scout_field_sch_id=1&user_id=1")
        assert response.status_code == 200


@pytest.mark.django_db
class TestFieldFormViewPaths:
    """Lines 732-733, 749: FieldFormView GET success, POST invalid data + access denied"""

    def test_get_field_form_success(self, api_client):
        """Lines 732-733: GET success path"""
        user = make_user("ff_get")
        api_client.force_authenticate(user=user)
        with patch("scouting.util.get_field_form", return_value={"id": 1, "season_id": 1}):
            response = api_client.get("/scouting/admin/field-form/")
        assert response.status_code == 200

    def test_post_field_form_invalid_data(self, api_client):
        """Line 749: POST - has_access=True but serializer invalid"""
        user = make_user("ff_inv")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.views.FieldFormSerializer") as mock_ser_cls:
            mock_ser = MagicMock()
            mock_ser.is_valid.return_value = False
            mock_ser.errors = {"img": ["bad file"]}
            mock_ser_cls.return_value = mock_ser
            response = api_client.post("/scouting/admin/field-form/", {}, format="json")
        assert response.status_code == 200
        assert "invalid" in str(response.data).lower() or "error" in str(response.data).lower()

    def test_post_field_form_save_success(self, api_client):
        """POST save called successfully"""
        user = make_user("ff_save")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=True), \
             patch("scouting.admin.util.save_field_form") as mock_save:
            response = api_client.post("/scouting/admin/field-form/", {
                "id": None, "season_id": 1
            }, format="json")
        assert response.status_code == 200

    def test_post_field_form_access_denied(self, api_client):
        """Access denied"""
        user = make_user("ff_deny")
        api_client.force_authenticate(user=user)
        with patch("scouting.admin.views.has_access", return_value=False):
            response = api_client.post("/scouting/admin/field-form/", {
                "id": None, "season_id": 1
            }, format="json")
        assert response.status_code == 200
        assert "access" in str(response.data).lower()
