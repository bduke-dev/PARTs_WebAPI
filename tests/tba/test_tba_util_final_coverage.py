"""
Tests targeting specific uncovered lines in tba/util.py:
  - Lines 254-256: IntegrityError on team create in sync_event
  - Lines 263-264: IntegrityError on team-event link in sync_event
  - Lines 290-291: Exception handler in sync_matches
  - Lines 368-390: sync_event_team_info branches (UPDATE, ADD, no active event)
  - Lines 450-463: UPDATE path in save_tba_match
  - Lines 517-521: verify_tba_webhook_call
"""
import datetime
import json
from hashlib import sha256
import hmac
from unittest.mock import MagicMock, Mock, patch

import pytest
import pytz
from django.conf import settings

from scouting.models import (
    CompetitionLevel,
    Event,
    EventTeamInfo,
    Match,
    Season,
    Team,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_season(suffix="2024"):
    return Season.objects.create(
        season=suffix, current="n", game="Test Game", manual=""
    )


def _make_event(season, event_cd="2024test", current="n"):
    return Event.objects.create(
        season=season,
        event_cd=event_cd,
        event_nm="Test Event",
        date_st=datetime.datetime(2024, 3, 1, tzinfo=pytz.utc),
        date_end=datetime.datetime(2024, 3, 3, tzinfo=pytz.utc),
        current=current,
        competition_page_active="n",
        void_ind="n",
    )


def _make_team(team_no=3492, team_nm="PARTs"):
    return Team.objects.get_or_create(
        team_no=team_no, defaults={"team_nm": team_nm, "void_ind": "n"}
    )[0]


def _make_comp_level(comp_lvl_typ="qm"):
    return CompetitionLevel.objects.get_or_create(
        comp_lvl_typ=comp_lvl_typ,
        defaults={"comp_lvl_typ_nm": "Quals", "comp_lvl_order": 1, "void_ind": "n"},
    )[0]


_TBA_EVENT_DATA = {
    "event_nm": "Test Event",
    "date_st": datetime.datetime(2024, 3, 1, tzinfo=pytz.utc),
    "date_end": datetime.datetime(2024, 3, 3, tzinfo=pytz.utc),
    "event_cd": "2024test",
    "event_url": None,
    "gmaps_url": None,
    "address": None,
    "city": "Test City",
    "state_prov": "PA",
    "postal_code": "12345",
    "location_name": None,
    "timezone": "America/New_York",
    "webcast_url": "",
}


# ---------------------------------------------------------------------------
# Lines 254-256: IntegrityError on team create inside sync_event
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestSyncEventTeamIntegrityError:
    """Lines 254-256: team already exists → IntegrityError path on save."""

    def test_team_already_exists_triggers_integrity_error_branch(self):
        """When a team already exists, force_insert raises IntegrityError;
        the except branch retrieves the existing team instead."""
        from tba.util import sync_event

        season = _make_season()
        # Pre-create the team so that force_insert=True inside sync_event raises IntegrityError
        _make_team(team_no=1111, team_nm="Existing Team")

        mock_teams = [{"team_no": 1111, "team_nm": "Existing Team"}]

        with patch("tba.util.get_tba_event", return_value=dict(_TBA_EVENT_DATA, event_cd="2024cover1")), \
             patch("tba.util.get_tba_event_teams", return_value=mock_teams):
            result = sync_event(season, "2024cover1")

        # The except branch logs "(NO ADD)"
        assert "(NO ADD) Already have team: 1111" in result


# ---------------------------------------------------------------------------
# Lines 263-264: IntegrityError on event_set.add inside sync_event
# ---------------------------------------------------------------------------

@pytest.mark.django_db(transaction=True)
class TestSyncEventLinkIntegrityError:
    """Lines 263-264: adding team to event raises IntegrityError."""

    def test_event_set_add_integrity_error_branch(self):
        """Force IntegrityError on team.event_set.add so the except branch is hit."""
        from tba.util import sync_event

        season = _make_season(suffix="2025")
        mock_teams = [{"team_no": 2222, "team_nm": "Link Team"}]

        from django.db import IntegrityError as DjangoIntegrityError

        def add_raises(*args, **kwargs):
            raise DjangoIntegrityError("duplicate")

        # Get the dynamically-created ManyRelatedManager class from a Team instance
        dummy = Team.__new__(Team)
        dummy.pk = 99999
        mgr_class = type(dummy.event_set)

        with patch("tba.util.get_tba_event", return_value=dict(_TBA_EVENT_DATA, event_cd="2024cover2")), \
             patch("tba.util.get_tba_event_teams", return_value=mock_teams), \
             patch.object(mgr_class, "add", side_effect=add_raises):
            result = sync_event(season, "2024cover2")

        assert "(NO LINK) Team: 2222" in result


# ---------------------------------------------------------------------------
# Lines 290-291: Exception handler in sync_matches
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSyncMatchesExceptionHandler:
    """Lines 290-291: save_tba_match raises an exception → error logged."""

    def test_exception_in_save_tba_match_is_caught(self):
        """When save_tba_match throws, sync_matches catches it and logs (ERROR)."""
        from tba.util import sync_matches

        season = _make_season(suffix="2026")
        event = _make_event(season, event_cd="2026except")

        raw_matches = [{"match_number": 5, "key": "2026except_qm5"}]

        with patch("tba.util.requests.get") as mock_get, \
             patch("tba.util.save_tba_match", side_effect=Exception("boom")):
            mock_get.return_value.text = json.dumps(raw_matches)
            result = sync_matches(event)

        assert "(ERROR)" in result
        assert "boom" in result


# ---------------------------------------------------------------------------
# Lines 368-390: sync_event_team_info branches
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSyncEventTeamInfoUpdate:
    """Lines 368-372: UPDATE path — ETI already exists for the team/event pair."""

    def test_existing_eti_is_updated(self):
        """When ETI already exists, it should be updated rather than created."""
        from tba.util import sync_event_team_info

        season = _make_season(suffix="2027")
        today = datetime.date.today()
        # Make the event active so the if-branch is taken
        event = Event.objects.create(
            season=season,
            event_cd="2027update",
            event_nm="Update Event",
            date_st=datetime.datetime.combine(today, datetime.time.min, tzinfo=pytz.utc),
            date_end=datetime.datetime.combine(today, datetime.time.min, tzinfo=pytz.utc),
            current="y",
            competition_page_active="n",
            void_ind="n",
        )
        team = _make_team(team_no=3301, team_nm="Update Team")
        # Pre-create an ETI so the UPDATE branch is taken
        EventTeamInfo.objects.create(
            event=event,
            team=team,
            matches_played=2,
            qual_average=10,
            losses=1,
            wins=1,
            ties=0,
            rank=5,
            dq=0,
            void_ind="n",
        )

        rankings_info = [
            {
                "matches_played": 4,
                "qual_average": 20,
                "losses": 1,
                "wins": 3,
                "ties": 0,
                "rank": 2,
                "dq": 0,
                "team_id": "3301",
            }
        ]

        with patch("tba.util.sync_event"), \
             patch("tba.util.get_tba_event_team_info", return_value=rankings_info):
            result = sync_event_team_info(force=1)

        assert "(UPDATE)" in result
        eti = EventTeamInfo.objects.get(event=event, team=team)
        assert eti.matches_played == 4


@pytest.mark.django_db
class TestSyncEventTeamInfoAdd:
    """Lines 373-388: ADD path — ETI does not yet exist for the team/event pair."""

    def test_new_eti_is_created(self):
        """When no ETI exists, a new one is created (ADD path)."""
        from tba.util import sync_event_team_info

        season = _make_season(suffix="2028")
        today = datetime.date.today()
        event = Event.objects.create(
            season=season,
            event_cd="2028add",
            event_nm="Add Event",
            date_st=datetime.datetime.combine(today, datetime.time.min, tzinfo=pytz.utc),
            date_end=datetime.datetime.combine(today, datetime.time.min, tzinfo=pytz.utc),
            current="y",
            competition_page_active="n",
            void_ind="n",
        )
        team = _make_team(team_no=4411, team_nm="Add Team")

        rankings_info = [
            {
                "matches_played": 3,
                "qual_average": 15,
                "losses": 1,
                "wins": 2,
                "ties": 0,
                "rank": 4,
                "dq": 0,
                "team_id": "4411",
            }
        ]

        with patch("tba.util.sync_event"), \
             patch("tba.util.get_tba_event_team_info", return_value=rankings_info):
            result = sync_event_team_info(force=1)

        assert "(ADD)" in result
        assert EventTeamInfo.objects.filter(event=event, team=team).exists()


@pytest.mark.django_db
class TestSyncEventTeamInfoNoActiveEvent:
    """Line 390: else branch — event is not active and force=0."""

    def test_no_active_event_message_returned(self):
        """When event dates don't cover today and force=0, 'No active event' is returned."""
        from tba.util import sync_event_team_info

        season = _make_season(suffix="2029")
        # Set dates far in the past so the event is not active
        event = Event.objects.create(
            season=season,
            event_cd="2029past",
            event_nm="Past Event",
            date_st=datetime.datetime(2020, 1, 1, tzinfo=pytz.utc),
            date_end=datetime.datetime(2020, 1, 3, tzinfo=pytz.utc),
            current="y",
            competition_page_active="n",
            void_ind="n",
        )

        with patch("tba.util.sync_event"):
            result = sync_event_team_info(force=0)

        assert result == "No active event"


# ---------------------------------------------------------------------------
# Lines 450-463: UPDATE path in save_tba_match
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSaveTbaMatchUpdate:
    """Lines 450-463: existing match is updated rather than inserted."""

    def _build_tba_match(self, event, teams, comp_level):
        r1, r2, r3 = teams[:3]
        b1, b2, b3 = teams[3:6]
        return {
            "key": f"{event.event_cd}_qm1",
            "event_key": event.event_cd,
            "match_number": 1,
            "comp_level": comp_level.comp_lvl_typ,
            "time": None,
            "alliances": {
                "red": {
                    "team_keys": [
                        f"frc{r1.team_no}",
                        f"frc{r2.team_no}",
                        f"frc{r3.team_no}",
                    ],
                    "score": 100,
                },
                "blue": {
                    "team_keys": [
                        f"frc{b1.team_no}",
                        f"frc{b2.team_no}",
                        f"frc{b3.team_no}",
                    ],
                    "score": 80,
                },
            },
        }

    def test_existing_match_is_updated(self):
        """When a match with the same key exists, it is updated (lines 450-463)."""
        from tba.util import save_tba_match

        season = _make_season(suffix="2030")
        event = _make_event(season, event_cd="2030match")
        comp_level = _make_comp_level("qm")

        team_nos = [5001, 5002, 5003, 5004, 5005, 5006]
        teams = [_make_team(no, f"Team{no}") for no in team_nos]

        tba_match = self._build_tba_match(event, teams, comp_level)
        match_key = tba_match["key"]

        # Pre-create the match so save_tba_match takes the UPDATE path
        Match.objects.create(
            match_key=match_key,
            match_number=1,
            event=event,
            red_one=teams[0],
            red_two=teams[1],
            red_three=teams[2],
            blue_one=teams[3],
            blue_two=teams[4],
            blue_three=teams[5],
            red_score=50,
            blue_score=50,
            comp_level=comp_level,
            time=None,
            void_ind="n",
        )

        result = save_tba_match(tba_match)

        assert "(UPDATE)" in result
        updated = Match.objects.get(match_key=match_key)
        assert updated.red_score == 100
        assert updated.blue_score == 80


# ---------------------------------------------------------------------------
# Lines 517-521: verify_tba_webhook_call
# ---------------------------------------------------------------------------

class TestVerifyTbaWebhookCall:
    """Lines 517-521: HMAC-SHA256 webhook signature verification."""

    def _make_request(self, data: dict, hmac_value: str | None = None):
        mock_req = Mock()
        mock_req.data = data
        mock_req.META = {}
        if hmac_value is not None:
            mock_req.META["HTTP_X_TBA_HMAC"] = hmac_value
        return mock_req

    def _compute_hmac(self, data: dict, secret: str) -> str:
        json_str = json.dumps(data, ensure_ascii=True)
        return hmac.new(
            secret.encode("utf-8"), json_str.encode("utf-8"), sha256
        ).hexdigest()

    def test_valid_webhook_signature_returns_true(self):
        """A request with a correct HMAC signature is accepted."""
        from tba.util import verify_tba_webhook_call

        data = {"message_type": "ping", "message_data": {}}
        secret = settings.TBA_WEBHOOK_SECRET
        correct_hmac = self._compute_hmac(data, secret)

        request = self._make_request(data, hmac_value=correct_hmac)
        assert verify_tba_webhook_call(request) is True

    def test_invalid_webhook_signature_returns_false(self):
        """A request with a wrong HMAC signature is rejected."""
        from tba.util import verify_tba_webhook_call

        data = {"message_type": "ping", "message_data": {}}
        request = self._make_request(data, hmac_value="deadbeef" * 8)
        assert verify_tba_webhook_call(request) is False

    def test_missing_hmac_header_returns_false(self):
        """A request without an HMAC header is rejected."""
        from tba.util import verify_tba_webhook_call

        data = {"message_type": "ping", "message_data": {}}
        request = self._make_request(data, hmac_value=None)
        assert verify_tba_webhook_call(request) is False
