"""
Coverage for user/views.py remaining lines: 254, 395-400, 418, 1216-1225
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model


@pytest.mark.django_db
class TestUserViewPostGenericException:
    """user/views.py line 254 - generic exception (error_string = None)"""

    def test_post_generic_exception(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch("user.views.user.util.save_user", side_effect=Exception("some other error")):
            response = api_client.post(
                "/user/user/",
                {
                    "username": "newuser_xyz",
                    "first_name": "A",
                    "last_name": "B",
                    "email": "newxyz@test.com",
                    "groups": [],
                },
                format="json",
            )
        assert response.status_code == 200
        assert response.data.get("error") is True


@pytest.mark.django_db
class TestUserViewPutSuperuserFlags:
    """user/views.py lines 395-400 - superuser editing flags"""

    def test_put_superuser_can_edit_flags(self, api_client):
        User = get_user_model()
        admin = User.objects.create_superuser(
            username="superadmin_flags",
            email="superflags@test.com",
            ******,
        )
        target = User.objects.create_user(
            username="flagtarget",
            email="flagtarget@test.com",
            ******,
        )
        api_client.force_authenticate(user=admin)
        with patch("user.views.user.util.save_user", return_value=None):
            response = api_client.put(
                "/user/user/",
                {
                    "username": target.username,
                    "first_name": target.first_name,
                    "last_name": target.last_name,
                    "email": target.email,
                    "is_staff": True,
                    "is_active": True,
                    "is_superuser": False,
                },
                format="json",
            )
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserViewPutUniqueConstraintException:
    """user/views.py line 418 - unique constraint on PUT"""

    def test_put_unique_constraint_exception(self, api_client, test_user):
        api_client.force_authenticate(user=test_user)
        with patch(
            "user.views.user.util.save_user",
            side_effect=Exception("UNIQUE constraint failed: auth_user.username"),
        ):
            response = api_client.put(
                "/user/user/",
                {
                    "username": test_user.username,
                    "first_name": "A",
                    "last_name": "B",
                    "email": test_user.email,
                },
                format="json",
            )
        assert response.status_code == 200
        assert response.data.get("error") is True


@pytest.mark.django_db
class TestSimulateUserView:
    """user/views.py lines 1216-1225 - SimulateUserView GET"""

    def test_simulate_user(self, api_client):
        User = get_user_model()
        admin = User.objects.create_superuser(
            username="simulate_admin",
            email="simadmin@test.com",
            ******,
        )
        target = User.objects.create_user(
            username="simulate_target",
            email="simtarget@test.com",
            ******,
        )
        api_client.force_authenticate(user=admin)
        with patch("user.views.has_access", return_value=True), \
             patch("user.views.user.util.get_user", return_value=target):
            response = api_client.get(
                f"/user/simulate/?user_id={target.id}"
            )
        assert response.status_code == 200
