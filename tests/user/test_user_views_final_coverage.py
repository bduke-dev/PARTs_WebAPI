"""
Final coverage tests for user/views.py.
"""
import pytest
from unittest.mock import patch, MagicMock
from django.contrib.auth import get_user_model
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

User = get_user_model()


@pytest.mark.django_db
class TestUserViewPostUniqueConstraintGenericError:
    """Line 254: POST UserView - unique constraint exception with non-unique error (error_string = None)"""

    def test_post_user_generic_exception(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)
        with patch("user.views.User.objects.create_user", side_effect=Exception("some generic db error")):
            response = api_client.post("/user/save/", {
                "username": "newuser123",
                "first_name": "New",
                "last_name": "User",
                "email": "newuser@example.com",
                "password": "P@ssword1!",
            }, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestUserProfileViewPutImageUpload:
    """Lines 386-393: PUT UserProfile - image upload path"""

    def test_put_user_with_image(self, api_client):
        user = User.objects.create_user(
            username="imguser", email="imguser@example.com", password="pass",
            first_name="Img", last_name="User"
        )
        user.is_active = True
        user.save()
        api_client.force_authenticate(user=user)

        mock_img = MagicMock()

        with patch("user.views.general.cloudinary.upload_image", return_value={"public_id": "img123", "version": "9999"}):
            with patch("user.views.UserUpdateSerializer") as mock_serializer:
                mock_instance = MagicMock()
                mock_instance.is_valid.return_value = True
                mock_instance.validated_data = {
                    "id": user.id,
                    "image": mock_img,
                }
                mock_instance.errors = {}
                mock_serializer.return_value = mock_instance

                response = api_client.put("/user/profile/", {"image": "data:image/png;base64,abc"}, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserProfileViewPutSuperuserFlags:
    """Lines 395-400: PUT UserProfile - superuser editing staff/active/superuser flags"""

    def test_superuser_can_edit_flags(self, api_client, admin_user):
        target_user = User.objects.create_user(
            username="flaguser", email="flaguser@example.com", password="pass"
        )
        api_client.force_authenticate(user=admin_user)

        with patch("user.views.UserUpdateSerializer") as mock_serializer:
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = True
            mock_instance.validated_data = {
                "id": target_user.id,
                "is_staff": True,
                "is_active": True,
                "is_superuser": False,
            }
            mock_instance.errors = {}
            mock_serializer.return_value = mock_instance

            response = api_client.put("/user/profile/", {
                "is_staff": True, "is_active": True, "is_superuser": False
            }, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestUserProfileViewPutException:
    """Line 418: PUT UserProfile - exception during save"""

    def test_put_user_generic_exception(self, api_client, system_user):
        # system_user creates user with id=-1 needed by ret_message error logging
        user = User.objects.create_user(
            username="putex", email="putex@example.com", password="pass",
            first_name="Put", last_name="Ex"
        )
        user.is_active = True
        user.save()
        api_client.force_authenticate(user=user)

        with patch("user.views.UserUpdateSerializer") as mock_serializer:
            mock_instance = MagicMock()
            mock_instance.is_valid.return_value = True
            mock_instance.validated_data = {"id": user.id}
            mock_instance.errors = {}
            mock_serializer.return_value = mock_instance

            with patch.object(User, "save", side_effect=Exception("some db error")):
                response = api_client.put("/user/profile/", {}, format="json")
        assert response.status_code == 200
        assert "error" in str(response.data).lower() or "occurred" in str(response.data).lower()


@pytest.mark.django_db
class TestResetPasswordViewTokenNone:
    """Line 647: ResetPasswordView POST - when token=None path"""

    def test_reset_password_token_none_path(self, api_client, system_user):
        # system_user creates user with id=-1 needed by ret_message error logging
        user = User.objects.create_user(
            username="resetpw", email="resetpw@example.com", password="OldPass1!"
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))

        # Pass token=None to hit the None check in reset_password
        response = api_client.post("/user/reset-password/", {
            "uuid": uid,
            "token": None,
            "password": "NewPass1!",
            "email": "resetpw@example.com",
        }, format="json")
        assert response.status_code == 200


@pytest.mark.django_db
class TestSimulateUserView:
    """Lines 1216-1225: SimulateUserView GET - mock user.util.get_user and RefreshToken"""

    def test_simulate_user_get(self, api_client, admin_user):
        api_client.force_authenticate(user=admin_user)

        target_user = User.objects.create_user(
            username="simtarget", email="simtarget@example.com", password="pass"
        )

        mock_refresh = MagicMock()
        mock_refresh.__str__ = MagicMock(return_value="mock_refresh_token")
        mock_refresh.access_token.__str__ = MagicMock(return_value="mock_access_token")

        with patch("user.views.has_access", return_value=True), \
             patch("user.util.get_user", return_value=target_user), \
             patch("user.views.RefreshToken.for_user", return_value=mock_refresh), \
             patch("user.views.TokenRefreshSerializer") as mock_ser:
            mock_ser.return_value.data = {"access": "mock_access", "refresh": "mock_refresh"}
            response = api_client.get(f"/user/simulate/?user_id={target_user.id}")
        assert response.status_code == 200
