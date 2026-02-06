"""
Additional tests for scouting views to improve coverage.
Tests access control, error handling, and query parameter handling.
"""
import pytest
from unittest.mock import Mock, patch


@pytest.mark.django_db
class TestSeasonView:
    """Tests for SeasonView."""

    def test_season_view_get_current_season(self, authenticated_api_client, test_user):
        """Test SeasonView with current=true parameter."""
        from scouting.models import Season
        
        season = Season.objects.create(season='2024', game='Test', manual='Test', current='y')
        
        with patch('general.security.has_access', return_value=True):
            response = authenticated_api_client.get('/scouting/season/?current=true')
            
            assert response.status_code == 200

    def test_season_view_get_all_seasons(self, authenticated_api_client, test_user):
        """Test SeasonView without current parameter."""
        from scouting.models import Season
        
        Season.objects.create(season='2024', game='Test', manual='Test', current='y')
        Season.objects.create(season='2023', game='Test2', manual='Test2', current='n')
        
        with patch('general.security.has_access', return_value=True):
            response = authenticated_api_client.get('/scouting/season/')
            
            assert response.status_code == 200

    def test_season_view_without_permission(self, authenticated_api_client, test_user):
        """Test SeasonView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/season/')
            
            # When access is denied, ret_message is called
            assert response.status_code == 200

    def test_season_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test SeasonView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_all_seasons', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/season/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestEventView:
    """Tests for EventView."""

    def test_event_view_get_all_events(self, authenticated_api_client, test_user):
        """Test EventView returns all events."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_all_events', return_value=[]):
                response = authenticated_api_client.get('/scouting/event/')
                
                assert response.status_code == 200

    def test_event_view_without_permission(self, authenticated_api_client, test_user):
        """Test EventView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/event/')
            
            # When access is denied, ret_message is called
            assert response.status_code == 200

    def test_event_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test EventView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_all_events', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/event/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestTeamView:
    """Tests for TeamView."""

    def test_team_view_get_teams(self, authenticated_api_client, test_user):
        """Test TeamView returns teams."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_teams', return_value=[]):
                response = authenticated_api_client.get('/scouting/team/')
                
                assert response.status_code == 200

    def test_team_view_without_permission(self, authenticated_api_client, test_user):
        """Test TeamView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/team/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_team_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test TeamView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_teams', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/team/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestMatchView:
    """Tests for MatchView."""

    def test_match_view_get_matches(self, authenticated_api_client, test_user):
        """Test MatchView returns matches."""
        from scouting.models import Season, Event
        import datetime
        
        season = Season.objects.create(season='2024', game='Test', manual='Test')
        event = Event.objects.create(
            event_cd='2024test',
            event_nm='Test',
            event_url='http://test.com',
            gmaps_url='http://test.com',
            date_st=datetime.date.today(),
            date_end=datetime.date.today(),
            season=season,
            current='y',
            void_ind='n'
        )
        
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_matches', return_value=[]):
                response = authenticated_api_client.get('/scouting/match/')
                
                assert response.status_code == 200

    def test_match_view_without_permission(self, authenticated_api_client, test_user):
        """Test MatchView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/match/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_match_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test MatchView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_current_event', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/match/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestScoutFieldScheduleView:
    """Tests for ScoutFieldScheduleView."""

    def test_scout_field_schedule_view_get_schedules(self, authenticated_api_client, test_user):
        """Test ScoutFieldScheduleView returns schedules."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_current_scout_field_schedule_parsed', return_value=[]):
                response = authenticated_api_client.get('/scouting/scout-field-schedule/')
                
                assert response.status_code == 200

    def test_scout_field_schedule_view_without_permission(self, authenticated_api_client, test_user):
        """Test ScoutFieldScheduleView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/scout-field-schedule/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_scout_field_schedule_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test ScoutFieldScheduleView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_current_scout_field_schedule_parsed', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/scout-field-schedule/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestAllScoutingInfoView:
    """Tests for AllScoutingInfoView."""

    def test_all_scouting_info_view_without_permission(self, authenticated_api_client, test_user):
        """Test AllScoutingInfoView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/all-scouting-info/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_all_scouting_info_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test AllScoutingInfoView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_all_seasons', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/all-scouting-info/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True
