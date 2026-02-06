"""
Additional tests for TBA webhook verification and utility functions.
Tests for webhook signature verification, message saving, and helper functions.
"""
import pytest
import json
import hmac
from hashlib import sha256
from unittest.mock import Mock, patch, MagicMock
from django.conf import settings


@pytest.mark.django_db
class TestWebhookVerification:
    """Tests for TBA webhook signature verification."""

    def test_verify_tba_webhook_call_valid_signature(self):
        """Test webhook verification with a valid HMAC signature."""
        from tba.util import verify_tba_webhook_call
        
        # Create test data
        test_data = {
            'message_type': 'match_score',
            'message_data': {
                'event_key': '2024pahat',
                'match': {
                    'key': '2024pahat_qm1',
                    'match_number': 1
                }
            }
        }
        
        # Calculate expected signature
        json_str = json.dumps(test_data, ensure_ascii=True)
        expected_hmac = hmac.new(
            settings.TBA_WEBHOOK_SECRET.encode('utf-8'),
            json_str.encode('utf-8'),
            sha256
        ).hexdigest()
        
        # Create mock request
        mock_request = Mock()
        mock_request.data = test_data
        mock_request.META = {'HTTP_X_TBA_HMAC': expected_hmac}
        
        # Verify
        result = verify_tba_webhook_call(mock_request)
        assert result is True

    def test_verify_tba_webhook_call_invalid_signature(self):
        """Test webhook verification with an invalid HMAC signature."""
        from tba.util import verify_tba_webhook_call
        
        test_data = {
            'message_type': 'match_score',
            'message_data': {
                'event_key': '2024pahat'
            }
        }
        
        # Create mock request with wrong signature
        mock_request = Mock()
        mock_request.data = test_data
        mock_request.META = {'HTTP_X_TBA_HMAC': 'invalid_signature'}
        
        result = verify_tba_webhook_call(mock_request)
        assert result is False

    def test_verify_tba_webhook_call_missing_signature(self):
        """Test webhook verification when signature header is missing."""
        from tba.util import verify_tba_webhook_call
        
        test_data = {'message_type': 'match_score'}
        
        # Create mock request without signature
        mock_request = Mock()
        mock_request.data = test_data
        mock_request.META = {}
        
        result = verify_tba_webhook_call(mock_request)
        assert result is False


@pytest.mark.django_db
class TestMessageSaving:
    """Tests for saving webhook messages."""

    def test_save_message_success(self):
        """Test successfully saving a message to the database."""
        from tba.util import save_message
        from tba.models import Message
        
        message_data = {
            'message_type': 'match_score',
            'message_data': {
                'event_key': '2024pahat',
                'match': {
                    'key': '2024pahat_qm1',
                    'match_number': 1
                }
            }
        }
        
        result = save_message(message_data)
        
        assert result is not None
        assert result.message_type == 'match_score'
        assert '2024pahat' in result.message_data
        
        # Verify it was saved to database
        saved_message = Message.objects.get(message_id=result.message_id)
        assert saved_message.message_type == 'match_score'

    def test_save_message_truncates_long_data(self):
        """Test that very long message data gets truncated to 4000 characters."""
        from tba.util import save_message
        
        # Create a message with very long data
        long_data = 'x' * 5000
        message_data = {
            'message_type': 'test',
            'message_data': long_data
        }
        
        result = save_message(message_data)
        
        assert result is not None
        assert len(result.message_data) <= 4000


@pytest.mark.django_db
class TestHelperFunctions:
    """Tests for utility helper functions."""

    def test_replace_frc_in_str_with_prefix(self):
        """Test removing 'frc' prefix from team keys."""
        from tba.util import replace_frc_in_str
        
        result = replace_frc_in_str('frc3492')
        assert result == '3492'

    def test_replace_frc_in_str_without_prefix(self):
        """Test string without 'frc' prefix remains unchanged."""
        from tba.util import replace_frc_in_str
        
        result = replace_frc_in_str('3492')
        assert result == '3492'

    def test_replace_frc_in_str_multiple_occurrences(self):
        """Test removing multiple 'frc' occurrences."""
        from tba.util import replace_frc_in_str
        
        result = replace_frc_in_str('frcfrc3492')
        assert result == '3492'


@pytest.mark.django_db
class TestSyncMatches:
    """Tests for syncing matches from TBA."""

    def test_sync_matches_success(self, test_event_with_teams):
        """Test successfully syncing matches for an event."""
        from tba.util import sync_matches
        
        event, teams, comp_level = test_event_with_teams
        
        mock_matches = [
            {
                'key': f'{event.event_cd}_qm1',
                'match_number': 1,
                'event_key': event.event_cd,
                'comp_level': 'qm',
                'alliances': {
                    'red': {
                        'team_keys': [f'frc{teams[0].team_no}', f'frc{teams[1].team_no}', f'frc{teams[2].team_no}'],
                        'score': 100
                    },
                    'blue': {
                        'team_keys': [f'frc{teams[3].team_no}', f'frc{teams[4].team_no}', f'frc{teams[5].team_no}'],
                        'score': 90
                    }
                },
                'time': 1640000000
            }
        ]
        
        with patch('tba.util.requests.get') as mock_get:
            mock_get.return_value.text = json.dumps(mock_matches)
            
            result = sync_matches(event)
            
            assert '(ADD)' in result or '(UPDATE)' in result
            assert event.event_nm in result

    def test_sync_matches_handles_errors(self, test_event_with_teams):
        """Test that sync_matches handles errors gracefully."""
        from tba.util import sync_matches
        
        event, teams, comp_level = test_event_with_teams
        
        # Return invalid match data to trigger error
        with patch('tba.util.requests.get') as mock_get:
            mock_get.return_value.text = json.dumps([{'invalid': 'data'}])
            
            result = sync_matches(event)
            
            # Should return error message
            assert '(ERROR)' in result or result == ""


@pytest.mark.django_db
class TestGetTBAEventTeamInfo:
    """Tests for getting team ranking information from TBA."""

    def test_get_tba_event_team_info_success(self):
        """Test retrieving team ranking information."""
        from tba.util import get_tba_event_team_info
        from scouting.models import Team
        
        # Create test team
        team = Team.objects.create(
            team_no=3492,
            team_nm='PARTs',
            void_ind='n'
        )
        
        mock_rankings = {
            'rankings': [
                {
                    'team_key': 'frc3492',
                    'rank': 1,
                    'matches_played': 10,
                    'qual_average': 85.5,
                    'record': {
                        'wins': 8,
                        'losses': 2,
                        'ties': 0
                    },
                    'dq': 0
                }
            ]
        }
        
        with patch('tba.util.requests.get') as mock_get:
            mock_get.return_value.text = json.dumps(mock_rankings)
            
            result = get_tba_event_team_info('2024pahat')
            
            assert len(result) == 1
            assert result[0]['team_id'] == '3492'
            assert result[0]['rank'] == 1
            assert result[0]['matches_played'] == 10

    def test_get_tba_event_team_info_no_rankings(self):
        """Test handling of events with no rankings."""
        from tba.util import get_tba_event_team_info
        
        with patch('tba.util.requests.get') as mock_get:
            mock_get.return_value.text = json.dumps({'rankings': []})
            
            result = get_tba_event_team_info('2024empty')
            
            assert len(result) == 0


@pytest.mark.django_db
class TestSaveTBAMatch:
    """Tests for saving individual matches."""

    def test_save_tba_match_creates_new_match(self, test_event_with_teams):
        """Test creating a new match from TBA data."""
        from tba.util import save_tba_match
        from scouting.models import Match
        
        event, teams, comp_level = test_event_with_teams
        
        tba_match_data = {
            'key': f'{event.event_cd}_qm1',
            'match_number': 1,
            'event_key': event.event_cd,
            'comp_level': 'qm',
            'alliances': {
                'red': {
                    'team_keys': [f'frc{teams[0].team_no}', f'frc{teams[1].team_no}', f'frc{teams[2].team_no}'],
                    'score': 100
                },
                'blue': {
                    'team_keys': [f'frc{teams[3].team_no}', f'frc{teams[4].team_no}', f'frc{teams[5].team_no}'],
                    'score': 90
                }
            },
            'time': 1640000000
        }
        
        result = save_tba_match(tba_match_data)
        
        assert '(ADD)' in result
        assert event.event_nm in result
        
        # Verify match was created
        match = Match.objects.get(match_key=f'{event.event_cd}_qm1')
        assert match.match_number == 1
        assert match.red_score == 100
        assert match.blue_score == 90

    def test_save_tba_match_updates_existing_match(self, test_event_with_teams):
        """Test updating an existing match."""
        from tba.util import save_tba_match
        from scouting.models import Match
        
        event, teams, comp_level = test_event_with_teams
        
        # Create initial match
        initial_match = Match.objects.create(
            match_key=f'{event.event_cd}_qm1',
            match_number=1,
            event=event,
            red_one=teams[0],
            red_two=teams[1],
            red_three=teams[2],
            blue_one=teams[3],
            blue_two=teams[4],
            blue_three=teams[5],
            red_score=50,
            blue_score=40,
            comp_level=comp_level,
            void_ind='n'
        )
        
        # Updated data
        tba_match_data = {
            'key': f'{event.event_cd}_qm1',
            'match_number': 1,
            'event_key': event.event_cd,
            'comp_level': 'qm',
            'alliances': {
                'red': {
                    'team_keys': [f'frc{teams[0].team_no}', f'frc{teams[1].team_no}', f'frc{teams[2].team_no}'],
                    'score': 100
                },
                'blue': {
                    'team_keys': [f'frc{teams[3].team_no}', f'frc{teams[4].team_no}', f'frc{teams[5].team_no}'],
                    'score': 90
                }
            },
            'time': 1640000000
        }
        
        result = save_tba_match(tba_match_data)
        
        assert '(UPDATE)' in result
        
        # Verify match was updated
        match = Match.objects.get(match_key=f'{event.event_cd}_qm1')
        assert match.red_score == 100
        assert match.blue_score == 90
