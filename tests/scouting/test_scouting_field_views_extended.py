"""
Additional tests for scouting field views to improve coverage.
Tests access control, error handling, and edge cases.
"""
import pytest
from unittest.mock import Mock, patch
from rest_framework.response import Response


@pytest.mark.django_db
class TestFieldViewsAccessControl:
    """Tests for field view access control."""

    def test_form_view_without_permission(self, authenticated_api_client, test_user):
        """Test FormView denies access without proper permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/field/form/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True
            assert 'do not have access' in response.data['retMessage']

    def test_form_view_with_permission(self, authenticated_api_client, test_user):
        """Test FormView allows access with proper permissions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.field.util.get_field_form', return_value={}):
                response = authenticated_api_client.get('/scouting/field/form/')
                
                assert response.status_code == 200

    def test_response_columns_view_with_permission(self, authenticated_api_client, test_user, default_user):
        """Test ResponseColumnsView with proper permissions."""
        from scouting.models import Season
        
        season = Season.objects.create(season='2024', game='Test', manual='Test', current='y')
        
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.field.util.get_field_question_aggregates', return_value=[]):
                with patch('scouting.field.util.get_table_columns', return_value=[]):
                    response = authenticated_api_client.get('/scouting/field/response-columns/')
                    
                    assert response.status_code == 200

    def test_response_columns_view_without_permission(self, authenticated_api_client, test_user):
        """Test ResponseColumnsView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/field/response-columns/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_response_columns_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test ResponseColumnsView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.field.util.get_field_question_aggregates', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/field/response-columns/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True


@pytest.mark.django_db
class TestResponsesView:
    """Tests for ResponsesView."""

    def test_responses_view_returns_response_object(self, authenticated_api_client, test_user, default_user):
        """Test ResponsesView when get_responses returns a Response object."""
        from scouting.models import Season
        
        season = Season.objects.create(season='2024', game='Test', manual='Test', current='y')
        
        mock_response = Response({'data': 'test'})
        
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.field.util.get_responses', return_value=mock_response):
                response = authenticated_api_client.get('/scouting/field/responses/')
                
                # When get_responses returns a Response, it should be returned directly
                assert response.status_code == 200


@pytest.mark.django_db
class TestCheckInView:
    """Tests for CheckInView."""

    def test_check_in_view_with_permission(self, authenticated_api_client, test_user, default_user):
        """Test CheckInView with proper permissions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_scout_field_schedule') as mock_get_sfs:
                mock_sfs = Mock()
                mock_get_sfs.return_value = mock_sfs
                
                with patch('scouting.field.util.check_in_scout', return_value='Checked in successfully'):
                    response = authenticated_api_client.get(
                        '/scouting/field/check-in/?scout_field_sch_id=1'
                    )
                    
                    assert response.status_code == 200

    def test_check_in_view_without_permission(self, authenticated_api_client, test_user):
        """Test CheckInView denies access without permissions."""
        with patch('general.security.has_access', return_value=False):
            response = authenticated_api_client.get('/scouting/field/check-in/')
            
            assert response.status_code == 200
            assert 'error' in response.data
            assert response.data['error'] is True

    def test_check_in_view_exception(self, authenticated_api_client, test_user, default_user):
        """Test CheckInView handles exceptions."""
        with patch('general.security.has_access', return_value=True):
            with patch('scouting.util.get_scout_field_schedule', side_effect=Exception('Test error')):
                response = authenticated_api_client.get('/scouting/field/check-in/')
                
                assert response.status_code == 200
                assert 'error' in response.data
                assert response.data['error'] is True

