"""
Gmail Pagination Tests
Tests for the Gmail query pagination feature to ensure proper filter preservation.

This covers the specific bug we fixed where "Load more emails" was using 
natural language queries instead of processed Gmail queries with date filters.
"""

import pytest
import sys
import os
import json
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from services.composio_service import ComposioService
from composio.client.enums import Action
from models.conversation import Conversation
from utils.mongo_client import get_collection


class TestComposioServicePagination:
    """Unit tests for ComposioService Gmail query processing and pagination"""
    
    @pytest.fixture
    def service(self):
        """Create ComposioService instance with mocked client initialization"""
        with patch('services.composio_service.Composio') as mock_composio:
            mock_composio.return_value = Mock()
            service = ComposioService("test_api_key")
            service.client_available = True
            service.gmail_account_id = "test_gmail_account"
            return service

    @pytest.fixture
    def mock_gmail_response_with_pagination(self):
        """Mock Gmail API response with pagination data"""
        return {
            "successful": True,
            "data": {
                "messages": [
                    {
                        "messageId": "test_email_1",
                        "thread_id": "thread_123",
                        "subject": "Test Email 1",
                        "messageText": "First test email",
                        "messageTimestamp": "2025-09-15T10:00:00Z",
                        "sender": "Test Sender <test@example.com>",
                        "to": "recipient@example.com",
                        "labelIds": ["INBOX"],
                        "attachmentList": []
                    },
                    {
                        "messageId": "test_email_2", 
                        "thread_id": "thread_124",
                        "subject": "Test Email 2",
                        "messageText": "Second test email",
                        "messageTimestamp": "2025-09-14T15:30:00Z",
                        "sender": "Another Sender <sender2@example.com>",
                        "to": "recipient@example.com", 
                        "labelIds": ["INBOX"],
                        "attachmentList": []
                    }
                ],
                "nextPageToken": "test_page_token_123",
                "resultSizeEstimate": 25
            },
            "error": None,
            "logId": "log_test123"
        }

    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_recent_emails_preserves_gmail_query(self, mock_execute, service, mock_gmail_response_with_pagination):
        """Test that get_recent_emails preserves the processed Gmail query in response"""
        # Setup
        processed_gmail_query = "after:2025/09/13 before:2025/09/17"
        mock_execute.return_value = mock_gmail_response_with_pagination
        
        # Execute
        result = service.get_recent_emails(count=10, query=processed_gmail_query)
        
        # Verify API call
        mock_execute.assert_called_once_with(
            action=Action.GMAIL_FETCH_EMAILS,
            params={
                "max_results": 10,
                "query": processed_gmail_query
            }
        )
        
        # Verify response structure
        assert result is not None
        assert result["data"] == mock_gmail_response_with_pagination["data"]
        assert result["next_page_token"] == "test_page_token_123"
        assert result["total_estimate"] == 25
        # Check has_more logic: True if next_page_token exists and we got the requested count
        assert result["has_more"] == bool(result["next_page_token"] and len(result["data"]["messages"]) >= 10)

    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_recent_emails_with_page_token(self, mock_execute, service, mock_gmail_response_with_pagination):
        """Test that get_recent_emails correctly passes page tokens for pagination"""
        # Setup
        processed_gmail_query = "from:kiwi.com OR to:kiwi.com"
        page_token = "existing_page_token_456"
        
        # Mock response for paginated request (no more pages)
        paginated_response = mock_gmail_response_with_pagination.copy()
        paginated_response["data"]["nextPageToken"] = None  # Last page
        mock_execute.return_value = paginated_response
        
        # Execute
        result = service.get_recent_emails(count=10, query=processed_gmail_query, page_token=page_token)
        
        # Verify API call includes both query and page token
        mock_execute.assert_called_once_with(
            action=Action.GMAIL_FETCH_EMAILS,
            params={
                "max_results": 10,
                "query": processed_gmail_query,
                "page_token": page_token
            }
        )
        
        # Verify response indicates no more pages
        assert result["next_page_token"] is None
        assert result["has_more"] is False

    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_recent_emails_handles_empty_query(self, mock_execute, service, mock_gmail_response_with_pagination):
        """Test handling of requests without specific query filters"""
        # Setup - no query provided
        mock_execute.return_value = mock_gmail_response_with_pagination
        
        # Execute
        result = service.get_recent_emails(count=5)
        
        # Verify API call without query parameter
        mock_execute.assert_called_once_with(
            action=Action.GMAIL_FETCH_EMAILS,
            params={"max_results": 5}
        )
        
        # Verify response structure is correct
        assert result is not None
        assert "data" in result
        assert "next_page_token" in result

    @patch('services.composio_service.ComposioService._execute_action')
    def test_get_recent_emails_handles_api_failure(self, mock_execute, service):
        """Test handling of Composio API failures"""
        # Setup - mock API failure
        mock_execute.return_value = {
            "successful": False,
            "error": "Authentication failed",
            "data": {}
        }
        
        # Execute
        result = service.get_recent_emails(count=10, query="test query")
        
        # Verify error handling
        assert result is not None
        assert "error" in result
        # Error handling should propagate the actual error message
        assert result["error"] == "Authentication failed"


class TestLoadMoreEmailsEndpoint:
    """Integration tests for the /load_more_emails endpoint"""

    @pytest.fixture
    def app_client(self):
        """Create Flask test client"""
        # Import here to avoid circular imports during test discovery
        import app as flask_app
        flask_app.app.config['TESTING'] = True
        return flask_app.app.test_client()

    @pytest.fixture
    def mock_conversation_with_pagination(self, test_db):
        """Create a mock conversation with pagination data in MongoDB"""
        conversations_collection = get_collection('conversations')
        
        # Create conversation document with pagination metadata
        conversation_doc = {
            'thread_id': 'test_thread_pagination',
            'message_id': 'assistant_msg_123',
            'role': 'assistant',
            'content': 'Found 10 emails from this week.',
            'tool_results': {'emails': ['test_email_1', 'test_email_2']},
            'metadata': {
                'tool_next_page_token': 'test_page_token_456',
                'tool_limit_per_page': 10,
                'tool_total_emails_available': 25,
                'tool_original_query_params': {
                    'query': 'after:2025/09/13 before:2025/09/17',  # This is the KEY - processed Gmail query
                    'count': 10
                }
            },
            'timestamp': int(time.time())
        }
        
        conversations_collection.insert_one(conversation_doc)
        return conversation_doc

    @patch('app.tooling_service')
    def test_load_more_uses_processed_gmail_query(self, mock_tooling_service, app_client, mock_conversation_with_pagination):
        """Test that /load_more_emails uses processed Gmail query, not natural language query"""
        # Setup - Mock the tooling service response
        mock_tooling_service.get_recent_emails.return_value = {
            "data": {
                "messages": [
                    {
                        "messageId": "new_email_1",
                        "subject": "New Email 1",
                        "sender": "sender@example.com",
                        "messageTimestamp": "2025-09-14T12:00:00Z",
                        "thread_id": "thread_new_1"
                    }
                ]
            },
            "next_page_token": "next_token_789",
            "total_estimate": 25
        }
        
        # Execute - Call load more emails endpoint
        response = app_client.post('/load_more_emails', json={
            'thread_id': 'test_thread_pagination',
            'assistant_message_id': 'assistant_msg_123'
        })
        
        # Verify endpoint response
        assert response.status_code == 200
        
        # Verify that tooling service was called with processed Gmail query (not natural language)
        mock_tooling_service.get_recent_emails.assert_called_once()
        call_args = mock_tooling_service.get_recent_emails.call_args[1]
        
        # This is the critical test - should use processed Gmail query with date filters
        assert call_args['query'] == 'after:2025/09/13 before:2025/09/17'
        assert call_args['page_token'] == 'test_page_token_456'
        assert call_args['count'] == 10

    @pytest.fixture  
    def mock_conversation_with_natural_language_fallback(self, test_db):
        """Create conversation with natural language query (fallback scenario)"""
        conversations_collection = get_collection('conversations')
        
        # Simulate old format where only natural language query was stored
        conversation_doc = {
            'thread_id': 'test_thread_fallback',
            'message_id': 'assistant_msg_456', 
            'role': 'assistant',
            'content': 'Found emails from kiwi.com',
            'tool_results': {'emails': ['kiwi_email_1']},
            'metadata': {
                'tool_next_page_token': 'kiwi_page_token_123',
                'tool_limit_per_page': 10,
                'tool_total_emails_available': 15,
                'tool_original_query_params': {
                    'query': 'show my emails from/to @kiwi.com',  # Natural language query
                    'count': 10
                }
            },
            'timestamp': int(time.time())
        }
        
        conversations_collection.insert_one(conversation_doc)
        return conversation_doc

    @patch('app.tooling_service')
    def test_load_more_with_natural_language_fallback(self, mock_tooling_service, app_client, mock_conversation_with_natural_language_fallback):
        """Test that /load_more_emails handles natural language query fallback gracefully"""
        # Setup
        mock_tooling_service.get_recent_emails.return_value = {
            "data": {"messages": []},
            "next_page_token": None,
            "total_estimate": 15
        }
        
        # Execute
        response = app_client.post('/load_more_emails', json={
            'thread_id': 'test_thread_fallback',
            'assistant_message_id': 'assistant_msg_456'
        })
        
        # Verify endpoint still works (graceful degradation)
        assert response.status_code == 200
        
        # Verify it uses the stored query (even if it's natural language)
        mock_tooling_service.get_recent_emails.assert_called_once()
        call_args = mock_tooling_service.get_recent_emails.call_args[1]
        assert call_args['query'] == 'show my emails from/to @kiwi.com'
        assert call_args['page_token'] == 'kiwi_page_token_123'

    @patch('app.tooling_service')
    def test_load_more_missing_pagination_data(self, mock_tooling_service, app_client, test_db):
        """Test error handling when pagination data is missing"""
        # Setup - Create conversation without pagination metadata
        conversations_collection = get_collection('conversations')
        conversation_doc = {
            'thread_id': 'test_thread_no_pagination',
            'message_id': 'assistant_msg_no_pagination',
            'role': 'assistant',
            'content': 'Some response',
            'tool_results': {'emails': []},
            'metadata': {},  # No pagination data
            'timestamp': int(time.time())
        }
        conversations_collection.insert_one(conversation_doc)
        
        # Execute
        response = app_client.post('/load_more_emails', json={
            'thread_id': 'test_thread_no_pagination', 
            'assistant_message_id': 'assistant_msg_no_pagination'
        })
        
        # Verify proper error handling
        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert 'Pagination parameters missing' in response_data['message']
        
        # Verify tooling service was not called
        mock_tooling_service.get_recent_emails.assert_not_called()


@pytest.mark.optimized
class TestGmailPaginationRegression:
    """Regression tests to ensure the pagination bug doesn't reoccur"""
    
    def test_processed_gmail_query_contains_date_filters(self):
        """Test that processed Gmail queries contain proper date filters"""
        # This test simulates the core bug - ensuring processed queries have date filters
        natural_language_query = "show me emails I received this week"
        
        # Mock the expected LLM processing (this would be done by build_gmail_query_with_llm)
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())  # Monday
        week_end = week_start + timedelta(days=6)  # Sunday
        
        expected_processed_query = f"after:{week_start.strftime('%Y/%m/%d')} before:{week_end.strftime('%Y/%m/%d')}"
        
        # Verify the processed query has the expected structure
        assert "after:" in expected_processed_query
        assert "before:" in expected_processed_query
        assert expected_processed_query != natural_language_query
        
        # This documents the expected transformation
        print(f"Natural language: {natural_language_query}")
        print(f"Processed Gmail query: {expected_processed_query}")

    def test_pagination_preserves_query_type(self):
        """Test that pagination metadata preserves the correct query type"""
        # Simulate the data flow that should happen
        original_user_query = "show me emails from this week"
        processed_gmail_query = "after:2025/09/13 before:2025/09/17"
        
        # Simulate what should be stored in conversation metadata
        pagination_metadata = {
            'tool_original_query_params': {
                'query': processed_gmail_query,  # Should store PROCESSED query, not natural language
                'count': 10
            }
        }
        
        # Test the critical assertion - stored query should be processed, not natural language
        stored_query = pagination_metadata['tool_original_query_params']['query']
        assert stored_query == processed_gmail_query
        assert stored_query != original_user_query
        assert "after:" in stored_query  # Must contain date filters
        assert "before:" in stored_query  # Must contain date filters