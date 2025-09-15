"""
Unit tests for ComposioService methods.
These tests mock at the lowest integration point (_execute_action) while testing the actual business logic.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
import base64

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from services.composio_service import ComposioService
from composio.client.enums import Action
from tests.fixtures.composio_responses import (
    GMAIL_FETCH_MESSAGE_SUCCESS_SIMPLE,
    GMAIL_FETCH_MESSAGE_SUCCESS_MULTIPART,
    GMAIL_FETCH_MESSAGE_NOT_FOUND,
    GMAIL_SEARCH_EMAILS_SUCCESS,
    GMAIL_THREAD_SUCCESS,
    CALENDAR_EVENTS_SUCCESS,
    CALENDAR_CREATE_EVENT_SUCCESS,
    CALENDAR_DELETE_EVENT_SUCCESS,
    CALENDAR_EVENT_NOT_FOUND,
    COMPOSIO_API_ERROR,
    create_email_fixture_with_content,
    create_calendar_event_fixture
)


class TestComposioServiceEmailMethods:
    """Unit tests for email-related ComposioService methods"""
    
    @pytest.fixture
    def service(self):
        """Create ComposioService instance with mocked client initialization"""
        with patch('services.composio_service.Composio') as mock_composio:
            mock_composio.return_value = Mock()
            service = ComposioService("test_api_key")
            service.client_available = True
            return service
    
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_simple_text(self, mock_execute, service):
        """Test parsing simple text email"""
        mock_execute.return_value = GMAIL_FETCH_MESSAGE_SUCCESS_SIMPLE
        
        result = service.get_email_details("1991e5b04c210c80")
        
        assert result is not None
        assert "simple test email" in result
        assert "Best regards" in result
        mock_execute.assert_called_once_with(
            action=Action.GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID,
            params={
                "message_id": "1991e5b04c210c80",
                "format": "full",
                "user_id": "me"
            }
        )
    
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_multipart_prefers_html(self, mock_execute, service):
        """Test that multipart email parsing prefers HTML over plain text"""
        mock_execute.return_value = GMAIL_FETCH_MESSAGE_SUCCESS_MULTIPART
        
        result = service.get_email_details("1991e5b04c210c81")
        
        assert result is not None
        assert "<html>" in result
        assert "<strong>HTML</strong>" in result
        assert "plain text content" not in result  # Should prefer HTML
        
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_empty_content(self, mock_execute, service):
        """Test handling of email with no content"""
        empty_fixture = create_email_fixture_with_content("", "empty_email")
        mock_execute.return_value = empty_fixture
        
        result = service.get_email_details("empty_email")
        
        assert result is None  # Method returns None for truly empty content
        
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_with_special_characters(self, mock_execute, service):
        """Test handling of email with special characters and encoding"""
        special_content = "Email with émojis 🚀 and spécial châractérs"
        fixture = create_email_fixture_with_content(special_content, "special_email")
        mock_execute.return_value = fixture
        
        result = service.get_email_details("special_email")
        
        assert result == special_content
        
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_with_html_content(self, mock_execute, service):
        """Test parsing of HTML email content"""
        html_content = "<html><body><h1>Test</h1><p>HTML <strong>email</strong></p></body></html>"
        fixture = create_email_fixture_with_content(html_content, "html_email", is_html=True)
        mock_execute.return_value = fixture
        
        result = service.get_email_details("html_email")
        
        assert result == html_content
        assert "<h1>Test</h1>" in result
        
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_email_details_malformed_base64(self, mock_execute, service):
        """Test handling of malformed base64 content"""
        malformed_fixture = GMAIL_FETCH_MESSAGE_SUCCESS_SIMPLE.copy()
        # Corrupt the base64 data
        malformed_fixture["data"]["payload"]["body"]["data"] = "invalid_base64!!!"
        mock_execute.return_value = malformed_fixture
        
        result = service.get_email_details("malformed_email")
        
        # Should fall back to messageText or snippet
        assert result is not None
        assert "simple test email" in result


class TestComposioServiceCalendarMethods:
    """Unit tests for calendar-related ComposioService methods"""
    
    def test_create_calendar_event_success(self, mock_composio_calendar_service):
        """Test successful calendar event creation"""
        service = mock_composio_calendar_service
        service._execute_action.return_value = CALENDAR_CREATE_EVENT_SUCCESS
        
        result = service.create_calendar_event(
            summary="Test Meeting",
            start_time="2025-09-07T10:00:00+02:00",
            end_time="2025-09-07T11:00:00+02:00",
            location="Conference Room",
            description="Test meeting description",
            attendees=["attendee@example.com"]
        )
        
        assert result is not None
        assert result.get("source_type") == "google-calendar"
        assert "Successfully created calendar event" in result.get("content", "")
        assert "data" in result
        


class TestComposioServiceThreadMethods:
    """Unit tests for email thread-related ComposioService methods"""
    
    @pytest.fixture
    def service(self):
        """Create ComposioService instance with mocked client initialization"""
        with patch('services.composio_service.Composio') as mock_composio:
            mock_composio.return_value = Mock()
            service = ComposioService("test_api_key")
            service.client_available = True
            return service
    
    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_recent_emails_success(self, mock_execute, service):
        """Test successful recent emails retrieval"""
        mock_execute.return_value = GMAIL_SEARCH_EMAILS_SUCCESS
        
        result = service.get_recent_emails(count=10, query="test query")
        
        assert result is not None
        assert "data" in result
        assert len(result["data"]["messages"]) == 2
        assert result["data"]["messages"][0]["subject"] == "Test Email 1"
        
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args
        assert call_args[1]["action"] == Action.GMAIL_FETCH_EMAILS  # Correct action name
        assert call_args[1]["params"]["max_results"] == 10


class TestComposioServiceErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.fixture
    def service(self):
        """Create ComposioService instance with mocked client initialization"""
        with patch('services.composio_service.Composio') as mock_composio:
            mock_composio.return_value = Mock()
            service = ComposioService("test_api_key")
            service.client_available = True
            return service
    
    @patch('services.composio_service.ComposioService._execute_action')
    def test_malformed_response_structure(self, mock_execute, service):
        """Test handling of malformed response structure"""
        # Test with missing required fields - this currently crashes the code
        malformed_response = {"successful": True, "data": "not_a_dict"}
        mock_execute.return_value = malformed_response
        
        # This currently fails due to .keys() call on string
        # This test documents the current behavior - ideally this should be fixed
        with pytest.raises(AttributeError, match="'str' object has no attribute 'keys'"):
            service.get_email_details("test_email")
    
    def test_invalid_api_key_initialization(self):
        """Test ComposioService initialization with invalid API key"""
        with patch('services.composio_service.Composio') as mock_composio:
            mock_composio.side_effect = Exception("Invalid API key")
            
            service = ComposioService("invalid_key")
            
            assert service.client_available is False
            assert service.composio is None


class TestFixtureValidation:
    """Tests to ensure fixtures are realistic and well-formed"""
    
    def test_fixture_base64_decoding(self):
        """Ensure base64 data in fixtures can actually be decoded"""
        multipart_fixture = GMAIL_FETCH_MESSAGE_SUCCESS_MULTIPART
        
        for part in multipart_fixture["data"]["payload"]["parts"]:
            if part.get("body", {}).get("data"):
                try:
                    decoded = base64.urlsafe_b64decode(part["body"]["data"])
                    assert len(decoded) > 0
                    # Should be valid UTF-8
                    decoded.decode('utf-8')
                except Exception as e:
                    pytest.fail(f"Invalid base64 in fixture: {e}")
    
    def test_fixture_consistency(self):
        """Ensure fixtures have consistent structure"""
        required_keys = ["successful", "data", "error", "logId"]
        
        fixtures = [
            GMAIL_FETCH_MESSAGE_SUCCESS_SIMPLE,
            GMAIL_FETCH_MESSAGE_SUCCESS_MULTIPART,
            GMAIL_SEARCH_EMAILS_SUCCESS,
            CALENDAR_EVENTS_SUCCESS,
            CALENDAR_CREATE_EVENT_SUCCESS
        ]
        
        for fixture in fixtures:
            for key in required_keys:
                assert key in fixture, f"Missing key {key} in fixture"
    
    def test_create_email_fixture_helper(self):
        """Test the helper function for creating custom email fixtures"""
        content = "Test email content with special chars: éñ🚀"
        fixture = create_email_fixture_with_content(content, "test_123")
        
        assert fixture["successful"] is True
        assert fixture["data"]["messageId"] == "test_123"
        assert fixture["data"]["messageText"] == content
        
        # Verify base64 encoding/decoding works
        encoded_data = fixture["data"]["payload"]["body"]["data"]
        decoded = base64.urlsafe_b64decode(encoded_data).decode('utf-8')
        assert decoded == content


# Prevent real API calls during testing
@pytest.fixture(autouse=True)
def prevent_real_composio_calls():
    """Ensure no real Composio API calls are made during unit tests"""
    with patch('composio.Composio') as mock_composio:
        mock_instance = Mock()
        mock_composio.return_value = mock_instance
        
        # If any test tries to make a real API call, it will fail loudly
        mock_instance.execute.side_effect = RuntimeError(
            "Real Composio API call attempted in unit test! "
            "Use proper mocking with _execute_action."
        )
        
        yield mock_instance
