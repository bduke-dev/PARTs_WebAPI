"""
Tests for alerts/util.py - system user (-1) discord path (line 136).
"""
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.django_db
class TestSendAlertsSystemUser:
    """Cover src/alerts/util.py line 136 - user.id == -1 sets role mention"""

    def test_send_alerts_system_user_discord(self, system_user):
        """When alert.user.id == -1, u is set to @&1024485828283596941"""
        from alerts.models import CommunicationChannelType, Alert, ChannelSend
        from alerts.util import send_alerts

        comm_typ = CommunicationChannelType.objects.get_or_create(
            comm_typ="discord",
            defaults={"comm_nm": "Discord", "void_ind": "n"}
        )[0]

        alert = Alert.objects.create(
            user=system_user,
            subject="Test System Alert",
            body="Test body",
            void_ind="n"
        )

        cs = ChannelSend.objects.create(
            comm_typ=comm_typ,
            alert=alert,
            tries=0,
            void_ind="n"
        )

        sent_message = []

        def capture_discord(msg):
            sent_message.append(msg)

        with patch("alerts.util.send_message.send_discord_notification", side_effect=capture_discord):
            result = send_alerts()

        assert len(sent_message) >= 1
        assert "<@&1024485828283596941>" in sent_message[0]
