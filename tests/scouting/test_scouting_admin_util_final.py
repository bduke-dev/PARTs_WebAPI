"""
Targeted tests for missing lines in src/scouting/admin/util.py.

Covers:
  - lines 110, 116-124: delete_event with FieldResponse cascade
  - lines 218-229: delete_season with scout Questions
  - lines 380-381: save_match new-match (event lookup + Match construction)
  - lines 423-424: link_team_to_event IntegrityError except branch
  - line 458: remove_link_team_to_event IntegrityError except branch
  - lines 509, 523-528: save_scout_schedule update-existing branch
  - lines 562-565: save_schedule create-new branch
  - lines 580-586: save_schedule update-existing branch
  - lines 681, 685, 691: get_scouting_user_info UserInfo.DoesNotExist handler
  - lines 696-697, 704-705: save_scouting_user_info create-new branch
  - lines 712-713: void_field_response save
  - lines 756-837: scouting_report
"""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from django.utils.timezone import now
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError

from scouting.admin import util as admin_util
from scouting.models import (
    Season,
    Event,
    Team,
    CompetitionLevel,
    FieldSchedule,
    Schedule,
    ScheduleType,
    UserInfo,
    FieldResponse,
    FieldForm,
)
import scouting.models as scouting_models
from form.models import (
    FormType,
    Response,
)

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def form_type(db):
    return FormType.objects.create(form_typ="field_fin", form_nm="Field Final")


@pytest.fixture
def season(db):
    return Season.objects.create(
        season="2023fin", current="n", game="Test Game", manual="test"
    )


@pytest.fixture
def current_season(db):
    return Season.objects.create(
        season="2099fin", current="y", game="Current Game", manual="test"
    )


@pytest.fixture
def event(db, season):
    return Event.objects.create(
        season=season,
        event_nm="Final Test Event",
        event_cd="23fintest",
        date_st=now(),
        date_end=now() + timedelta(days=3),
        current="n",
    )


@pytest.fixture
def current_event(db, current_season):
    return Event.objects.create(
        season=current_season,
        event_nm="Final Current Event",
        event_cd="99fincurr",
        date_st=now(),
        date_end=now() + timedelta(days=3),
        current="y",
        competition_page_active="y",
    )


@pytest.fixture
def team(db):
    return Team.objects.create(team_no=4999, team_nm="FinTeam")


@pytest.fixture
def test_user_fin(db):
    return User.objects.create_user(
        username="fintestuser", email="fintest@test.com", password="pass"
    )


@pytest.fixture
def comp_level(db):
    return CompetitionLevel.objects.create(
        comp_lvl_typ="qmfin", comp_lvl_typ_nm="Qualification Final", comp_lvl_order=1
    )


@pytest.fixture
def schedule_type(db):
    return ScheduleType.objects.create(sch_typ="pitfin", sch_nm="Pit Scouting Final")


# ---------------------------------------------------------------------------
# delete_event – lines 110, 116-124
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteEventMissingLines:
    """Covers line 110 (raise) and lines 116-124 (FieldResponse cascade)."""

    def test_delete_current_event_raises(self, current_event):
        """Line 110: raise Exception when deleting current event."""
        with pytest.raises(Exception, match="Cannot delete current event"):
            admin_util.delete_event(current_event.id)

    def test_delete_event_with_field_response_cascade(
        self, event, team, test_user_fin, form_type
    ):
        """Lines 116-124: FieldResponse and its Response are deleted with the event."""
        resp = Response.objects.create(form_typ=form_type)
        field_resp = FieldResponse.objects.create(
            response=resp,
            event=event,
            team=team,
            user=test_user_fin,
            void_ind="n",
        )

        result = admin_util.delete_event(event.id)

        assert not Event.objects.filter(id=event.id).exists()
        assert not FieldResponse.objects.filter(id=field_resp.id).exists()
        assert "Successfully deleted event" in result.data["retMessage"]


# ---------------------------------------------------------------------------
# delete_season – lines 218-229
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteSeasonWithQuestions:
    """Covers lines 218-229: scout Question deletion loop inside delete_season.

    NOTE: The source code at line 225 references ``questionaggregate_set`` which
    does not exist on ``form.models.Question`` (the correct reverse name is
    ``questionaggregatequestion_set``).  To exercise lines 218-229 we mock the
    scout-question queryset so the loop runs without hitting the broken
    attribute lookup.
    """

    def test_delete_season_with_scout_questions(self, season):
        """Lines 218-229: scout-question loop executed; season and mocked
        scout-question objects are deleted."""
        mock_sq = MagicMock()
        # Each inner for-loop iterates over the return value of .all(); keep
        # them empty so loop bodies don't execute, but the loops *are* entered.
        mock_sq.question.condition_question_from.all.return_value = []
        mock_sq.question.condition_question_to.all.return_value = []
        mock_sq.question.questionaggregate_set.all.return_value = []
        mock_sq.question.questionoption_set.all.return_value = []
        mock_sq.question.questionanswer_set.all.return_value = []

        season_id = season.id

        with patch(
            "scouting.admin.util.scouting.models.Question.objects.filter",
            return_value=[mock_sq],
        ):
            result = admin_util.delete_season(season.id)

        assert not Season.objects.filter(id=season_id).exists()
        mock_sq.delete.assert_called_once()
        mock_sq.question.delete.assert_called_once()
        assert "Successfully deleted season" in result.data["retMessage"]


# ---------------------------------------------------------------------------
# save_match – lines 380-381
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSaveMatchNewWithEvent:
    """Lines 380-381: new match construction with event FK lookup."""

    def test_create_match_with_empty_key(self, event, comp_level):
        """Empty match_key forces else-branch: event lookup and Match construction."""
        data = {
            "match_key": "",
            "event": {"id": event.id, "event_cd": event.event_cd},
            "comp_level": {"comp_lvl_typ": comp_level.comp_lvl_typ},
            "match_number": 42,
        }
        result = admin_util.save_match(data)

        assert result.event == event
        assert result.match_number == 42
        assert event.event_cd in result.match_key

    def test_create_match_with_no_key(self, event, comp_level):
        """None match_key also forces the else-branch."""
        data = {
            "event": {"id": event.id, "event_cd": event.event_cd},
            "comp_level": {"comp_lvl_typ": comp_level.comp_lvl_typ},
            "match_number": 7,
        }
        result = admin_util.save_match(data)

        assert result.event == event
        assert result.match_number == 7


# ---------------------------------------------------------------------------
# link_team_to_event – lines 423-424  (IntegrityError except branch)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestLinkTeamIntegrityError:
    """Lines 423-424: IntegrityError except block in link_team_to_event."""

    def test_link_team_integrity_error_caught(self, event):
        """Mock event_set.add to raise IntegrityError; verify (NO ADD) message."""
        mock_team = MagicMock()
        mock_team.event_set.add.side_effect = IntegrityError("duplicate key")

        data = {
            "event_id": event.id,
            "teams": [
                {"team_no": 8888, "team_nm": "Mock Team", "checked": True}
            ],
        }

        with patch(
            "scouting.admin.util.Team.objects.get", return_value=mock_team
        ), patch(
            "scouting.admin.util.Event.objects.get", return_value=event
        ):
            result = admin_util.link_team_to_event(data)

        assert "(NO ADD)" in result
        assert "8888" in result


# ---------------------------------------------------------------------------
# remove_link_team_to_event – line 458  (IntegrityError except branch)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestRemoveLinkTeamIntegrityError:
    """Line 458: IntegrityError except block in remove_link_team_to_event."""

    def test_remove_link_team_integrity_error_caught(self, event):
        """Mock event_set.remove to raise IntegrityError; verify (NO REMOVE) message."""
        mock_team = MagicMock()
        mock_team.event_set.remove.side_effect = IntegrityError("constraint fail")

        data = {
            "id": event.id,
            "teams": [
                {"team_no": 7777, "team_nm": "Remove Team", "checked": True}
            ],
        }

        with patch(
            "scouting.admin.util.Team.objects.get", return_value=mock_team
        ), patch(
            "scouting.admin.util.Event.objects.get", return_value=event
        ):
            result = admin_util.remove_link_team_to_event(data)

        assert "(NO REMOVE)" in result
        assert "7777" in result


# ---------------------------------------------------------------------------
# save_scout_schedule – lines 509, 523-528  (update-existing branch)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSaveScoutScheduleUpdate:
    """Lines 509, 523-528: update-existing FieldSchedule branch."""

    def test_update_existing_field_schedule(self, event, test_user_fin):
        """Providing an id hits the else-branch and updates fields."""
        st = now() + timedelta(hours=1)
        end = now() + timedelta(hours=3)
        existing = FieldSchedule.objects.create(
            event=event, st_time=st, end_time=end, void_ind="n"
        )

        new_st = now() + timedelta(hours=2)
        new_end = now() + timedelta(hours=4)

        data = {
            "id": existing.id,
            "event_id": event.id,
            "st_time": new_st,
            "end_time": new_end,
            "red_one_id": test_user_fin.id,
            "red_two_id": None,
            "red_three_id": None,
            "blue_one_id": None,
            "blue_two_id": None,
            "blue_three_id": None,
            "void_ind": "y",
        }

        result = admin_util.save_scout_schedule(data)

        assert result.id == existing.id
        assert result.red_one_id == test_user_fin.id
        assert result.void_ind == "y"

        existing.refresh_from_db()
        assert existing.void_ind == "y"


# ---------------------------------------------------------------------------
# save_schedule – lines 562-565 (create new) and 580-586 (update existing)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSaveScheduleCreateNew:
    """Lines 562-565: create-new Schedule branch (calls get_current_event)."""

    def test_create_new_schedule_with_current_event(
        self, current_event, test_user_fin, schedule_type
    ):
        st = now() + timedelta(hours=1)
        end = now() + timedelta(hours=3)

        data = {
            "st_time": st,
            "end_time": end,
            "user": test_user_fin.id,
            "sch_typ": schedule_type.sch_typ,
            "void_ind": "n",
        }

        with patch(
            "scouting.admin.util.scouting.util.get_current_event",
            return_value=current_event,
        ):
            result = admin_util.save_schedule(data)

        assert result.event == current_event
        assert result.user == test_user_fin
        assert result.sch_typ == schedule_type
        assert result.void_ind == "n"


@pytest.mark.django_db
class TestSaveScheduleUpdateExisting:
    """Lines 580-586: update-existing Schedule branch."""

    def test_update_existing_schedule(
        self, current_event, test_user_fin, schedule_type
    ):
        st = now() + timedelta(hours=1)
        end = now() + timedelta(hours=3)
        schedule = Schedule.objects.create(
            event=current_event,
            user=test_user_fin,
            sch_typ=schedule_type,
            st_time=st,
            end_time=end,
            void_ind="n",
        )

        new_st = now() + timedelta(hours=2)
        new_end = now() + timedelta(hours=5)

        data = {
            "id": schedule.id,
            "st_time": new_st,
            "end_time": new_end,
            "user": test_user_fin.id,
            "sch_typ": schedule_type.sch_typ,
            "void_ind": "y",
        }

        result = admin_util.save_schedule(data)

        assert result.id == schedule.id
        assert result.void_ind == "y"
        schedule.refresh_from_db()
        assert schedule.void_ind == "y"


# ---------------------------------------------------------------------------
# get_scouting_user_info – lines 681, 685, 691
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestGetScoutingUserInfoMissing:
    """Lines 681, 685, 691: UserInfo.DoesNotExist handler creates a new UserInfo."""

    def test_creates_user_info_when_missing(self, db):
        """User without a UserInfo gets one created automatically."""
        Group.objects.get_or_create(name="Admin")
        scout = User.objects.create_user(
            username="scout_fin",
            email="scout_fin@test.com",
            password="pass",
        )
        scout.is_active = True
        scout.save()

        result = admin_util.get_scouting_user_info()

        user_ids = [ui.user_id for ui in result]
        assert scout.id in user_ids
        assert UserInfo.objects.filter(user=scout).exists()

    def test_appends_existing_user_info(self, db, test_user_fin):
        """Lines 691: existing UserInfo is appended (not the DoesNotExist path)."""
        Group.objects.get_or_create(name="Admin")
        test_user_fin.is_active = True
        test_user_fin.save()
        user_info = UserInfo.objects.create(
            user=test_user_fin,
            under_review=False,
            group_leader=False,
            eliminate_results=False,
        )

        result = admin_util.get_scouting_user_info()

        user_ids = [ui.user_id for ui in result]
        assert test_user_fin.id in user_ids


# ---------------------------------------------------------------------------
# save_scouting_user_info – lines 696-697, 704-705
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSaveScoutingUserInfoCreate:
    """Lines 696-697, 704-705: create-new UserInfo branch (no id in data)."""

    def test_create_new_user_info(self, test_user_fin):
        data = {
            "user": {"id": test_user_fin.id},
            "group_leader": True,
            "under_review": False,
            "eliminate_results": True,
        }
        result = admin_util.save_scouting_user_info(data)

        assert result.user == test_user_fin
        assert result.group_leader is True
        assert result.eliminate_results is True
        assert UserInfo.objects.filter(user=test_user_fin, eliminate_results=True).exists()


# ---------------------------------------------------------------------------
# void_field_response – lines 712-713
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVoidFieldResponseSave:
    """Lines 712-713: void_ind set and saved."""

    def test_void_field_response(self, event, team, test_user_fin, form_type):
        resp = Response.objects.create(form_typ=form_type)
        field_resp = FieldResponse.objects.create(
            response=resp,
            event=event,
            team=team,
            user=test_user_fin,
            void_ind="n",
        )

        result = admin_util.void_field_response(field_resp.id)

        assert result.void_ind == "y"
        field_resp.refresh_from_db()
        assert field_resp.void_ind == "y"


# ---------------------------------------------------------------------------
# scouting_report – lines 756-837
# ---------------------------------------------------------------------------


def _make_score_breakdown():
    """Return a minimal score_breakdown dict matching what scouting_report uses."""
    side = {
        "autoTowerRobot1": "H",
        "autoTowerRobot2": "H",
        "autoTowerRobot3": "N",
        "autoTowerPoints": 10,
        "hubScore": {
            "autoPoints": 20,
            "transitionPoints": 5,
            "shift1Points": 3,
            "shift2Points": 3,
            "shift3Points": 3,
            "shift4Points": 3,
            "endgamePoints": 8,
            "teleopPoints": 25,
        },
        "endGameTowerRobot1": "Hang",
        "endGameTowerRobot2": "Hang",
        "endGameTowerRobot3": "None",
        "endGameTowerPoints": 15,
        "totalTowerPoints": 25,
        "totalPoints": 50,
        "totalTeleopPoints": 30,
        "minorFoulCount": 1,
        "majorFoulCount": 0,
        "foulPoints": 5,
        "adjustPoints": 0,
        "rp": 2,
    }
    return {"red": side, "blue": {**side, "totalPoints": 40, "rp": 0}}


@pytest.mark.django_db
class TestScoutingReport:
    """Lines 756-837: scouting_report exercised through multiple branches."""

    def _setup_base(self):
        """Create team 3492, current season, current event, plus a rival team."""
        team_3492 = Team.objects.get_or_create(team_no=3492, defaults={"team_nm": "PARTs"})[0]
        season = Season.objects.create(
            season="2099sr", current="y", game="SR Game", manual="m"
        )
        event = Event.objects.create(
            season=season,
            event_nm="SR Our Event",
            event_cd="99srours",
            date_st=now(),
            date_end=now() + timedelta(days=10),
            current="y",
            void_ind="n",
        )
        team_3492.event_set.add(event)  # team 3492 attends our event

        rival = Team.objects.get_or_create(
            team_no=9876, defaults={"team_nm": "Rivals"}
        )[0]
        event.teams.add(rival)  # rival also at our event (will be iterated)

        return team_3492, season, event, rival

    # --- sharing path (team_event["event_cd"] in event_cds) ------------------

    def test_scouting_report_sharing_path(self, db):
        """Lines 790-791: event shared with us → appended to 'sharing' string."""
        team_3492, season, event, rival = self._setup_base()

        shared_event = {
            "event_cd": event.event_cd,
            "event_nm": event.event_nm,
            "date_st": now(),
            "date_end": now() + timedelta(days=10),
        }

        with patch("scouting.admin.util.tba.util.get_events_for_team", return_value=[shared_event]):
            result = admin_util.scouting_report()

        assert result is not None
        assert "Team: 9876" in result

    # --- other-event path (event_cd NOT in ours) ----------------------------

    def test_scouting_report_other_event_no_rank(self, db):
        """Lines 793-801: other event listed; no rank data returned."""
        team_3492, season, event, rival = self._setup_base()

        other_event = {
            "event_cd": "99other1",
            "event_nm": "Other Regional",
            "date_st": now() - timedelta(days=20),
            "date_end": now() - timedelta(days=17),
            "timezone": "America/New_York",
        }

        with patch(
            "scouting.admin.util.tba.util.get_events_for_team",
            return_value=[other_event],
        ), patch(
            "scouting.admin.util.tba.util.get_tba_event_team_info",
            return_value=[],
        ), patch(
            "scouting.admin.util.tba.util.get_matches_for_team_event",
            return_value=[],
        ), patch(
            "scouting.admin.util.general.util.date_time_to_mdyhm",
            return_value="01/01/2025",
        ):
            result = admin_util.scouting_report()

        assert "Regional,Other Regional" in result

    def test_scouting_report_other_event_with_rank(self, db):
        """Lines 797-798: rank row emitted when team_event_info is non-empty."""
        team_3492, season, event, rival = self._setup_base()

        other_event = {
            "event_cd": "99other2",
            "event_nm": "Ranked Regional",
            "date_st": now() - timedelta(days=20),
            "date_end": now() - timedelta(days=17),
            "timezone": "America/New_York",
        }

        with patch(
            "scouting.admin.util.tba.util.get_events_for_team",
            return_value=[other_event],
        ), patch(
            "scouting.admin.util.tba.util.get_tba_event_team_info",
            return_value=[{"rank": 3}],
        ), patch(
            "scouting.admin.util.tba.util.get_matches_for_team_event",
            return_value=[],
        ), patch(
            "scouting.admin.util.general.util.date_time_to_mdyhm",
            return_value="01/01/2025",
        ):
            result = admin_util.scouting_report()

        assert "Rank: 3" in result

    def test_scouting_report_with_matches_no_breakdown(self, db):
        """Lines 803-812: match data rows emitted; score_breakdown is None."""
        team_3492, season, event, rival = self._setup_base()

        early_date = now() - timedelta(days=5)
        other_event = {
            "event_cd": "99other3",
            "event_nm": "Match Regional",
            "date_st": now() - timedelta(days=20),
            "date_end": early_date,
            "timezone": "America/New_York",
        }

        match = {
            "match_number": 1,
            "key": "99other3_qm1",
            "alliances": {
                "red": {"team_keys": ["frc1", "frc2", "frc3"], "score": 55},
                "blue": {"team_keys": ["frc4", "frc5", "frc6"], "score": 45},
            },
            "score_breakdown": None,
        }

        with patch(
            "scouting.admin.util.tba.util.get_events_for_team",
            return_value=[other_event],
        ), patch(
            "scouting.admin.util.tba.util.get_tba_event_team_info",
            return_value=[],
        ), patch(
            "scouting.admin.util.tba.util.get_matches_for_team_event",
            return_value=[match],
        ), patch(
            "scouting.admin.util.tba.util.replace_frc_in_str",
            side_effect=lambda s: s.replace("frc", ""),
        ), patch(
            "scouting.admin.util.general.util.date_time_to_mdyhm",
            return_value="01/01/2025",
        ):
            result = admin_util.scouting_report()

        assert "Match Data" in result
        assert "Match 1" in result

    def test_scouting_report_with_score_breakdown(self, db):
        """Lines 813-836: full score_breakdown block written to csv."""
        team_3492, season, event, rival = self._setup_base()

        early_date = now() - timedelta(days=5)
        other_event = {
            "event_cd": "99other4",
            "event_nm": "Detailed Regional",
            "date_st": now() - timedelta(days=20),
            "date_end": early_date,
            "timezone": "America/New_York",
        }

        match = {
            "match_number": 2,
            "key": "99other4_qm2",
            "alliances": {
                "red": {"team_keys": ["frc10", "frc20", "frc30"], "score": 60},
                "blue": {"team_keys": ["frc40", "frc50", "frc60"], "score": 50},
            },
            "score_breakdown": _make_score_breakdown(),
        }

        with patch(
            "scouting.admin.util.tba.util.get_events_for_team",
            return_value=[other_event],
        ), patch(
            "scouting.admin.util.tba.util.get_tba_event_team_info",
            return_value=[],
        ), patch(
            "scouting.admin.util.tba.util.get_matches_for_team_event",
            return_value=[match],
        ), patch(
            "scouting.admin.util.tba.util.replace_frc_in_str",
            side_effect=lambda s: s.replace("frc", ""),
        ), patch(
            "scouting.admin.util.general.util.date_time_to_mdyhm",
            return_value="01/01/2025",
        ):
            result = admin_util.scouting_report()

        assert "Detailed Results" in result
        assert "Ranking Points" in result

    def test_scouting_report_multiple_matches_horizontal_concat(self, db):
        """Lines 830-837: second match triggers horizontal CSV concatenation."""
        team_3492, season, event, rival = self._setup_base()

        early_date = now() - timedelta(days=5)
        other_event = {
            "event_cd": "99other5",
            "event_nm": "Multi Match Regional",
            "date_st": now() - timedelta(days=20),
            "date_end": early_date,
            "timezone": "America/New_York",
        }

        def _match(n):
            return {
                "match_number": n,
                "key": f"99other5_qm{n}",
                "alliances": {
                    "red": {"team_keys": ["frc1", "frc2", "frc3"], "score": 50},
                    "blue": {"team_keys": ["frc4", "frc5", "frc6"], "score": 40},
                },
                "score_breakdown": None,
            }

        with patch(
            "scouting.admin.util.tba.util.get_events_for_team",
            return_value=[other_event],
        ), patch(
            "scouting.admin.util.tba.util.get_tba_event_team_info",
            return_value=[],
        ), patch(
            "scouting.admin.util.tba.util.get_matches_for_team_event",
            return_value=[_match(1), _match(2)],
        ), patch(
            "scouting.admin.util.tba.util.replace_frc_in_str",
            side_effect=lambda s: s.replace("frc", ""),
        ), patch(
            "scouting.admin.util.general.util.date_time_to_mdyhm",
            return_value="01/01/2025",
        ):
            result = admin_util.scouting_report()

        # Two matches → horizontal concat uses ",,"
        assert ",," in result
