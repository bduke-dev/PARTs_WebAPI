"""
Fixtures for TBA tests.
"""
import pytest
import datetime
import pytz


@pytest.fixture
def test_event_with_teams(db):
    """
    Create a test event with teams and competition level.
    Returns tuple of (event, teams_list, comp_level).
    """
    from scouting.models import Season, Event, Team, CompetitionLevel
    
    # Create season
    season = Season.objects.create(
        season='2024',
        game='Test Game',
        manual='Test Manual'
    )
    
    # Create event
    event = Event.objects.create(
        event_cd='2024pahat',
        event_nm='Hatboro-Horsham',
        event_url='http://test.com',
        gmaps_url='http://maps.google.com',
        date_st=datetime.date(2024, 3, 15),
        date_end=datetime.date(2024, 3, 17),
        season=season,
        current='n',
        void_ind='n'
    )
    
    # Create competition level
    comp_level = CompetitionLevel.objects.create(
        comp_lvl_typ='qm',
        comp_lvl_typ_nm='Qualification',
        comp_lvl_order=1,
        void_ind='n'
    )
    
    # Create teams
    teams = []
    for i in range(6):
        team = Team.objects.create(
            team_no=3492 + i,
            team_nm=f'Team {3492 + i}',
            void_ind='n'
        )
        teams.append(team)
    
    return event, teams, comp_level


@pytest.fixture
def test_current_event(db):
    """
    Create a test event that is marked as current.
    Returns tuple of (event, teams_list).
    """
    from scouting.models import Season, Event, Team
    from django.utils import timezone
    
    # Create season
    season = Season.objects.create(
        season='2024',
        game='Test Game',
        manual='Test Manual'
    )
    
    # Create event that's currently active
    today = timezone.now().date()
    event = Event.objects.create(
        event_cd='2024pahat',
        event_nm='Hatboro-Horsham',
        event_url='http://test.com',
        gmaps_url='http://maps.google.com',
        date_st=today - datetime.timedelta(days=1),
        date_end=today + datetime.timedelta(days=1),
        season=season,
        current='y',
        void_ind='n'
    )
    
    # Create teams
    teams = []
    for i in range(6):
        team = Team.objects.create(
            team_no=3492 + i,
            team_nm=f'Team {3492 + i}',
            void_ind='n'
        )
        teams.append(team)
        # Link team to event
        event.team_set.add(team)
    
    return event, teams
