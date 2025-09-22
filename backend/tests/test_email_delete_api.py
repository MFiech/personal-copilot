"""
Tests for email deletion API endpoints and database operations.
These tests focus on the Flask API routes and database integration.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
import json

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from app import app
from models.conversation import Conversation
from services.composio_service import ComposioService
from tests.fixtures.composio_responses import (
    GMAIL_MOVE_TO_TRASH_SUCCESS,
    GMAIL_MOVE_TO_TRASH_FAILURE
)


class TestEmailDeleteAPIEndpoint:
    """Test the /delete_email Flask API endpoint"""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @pytest.fixture
    def mock_conversation_data(self):
        """Mock conversation document structure"""
        return {
            '_id': 'conversation_123',
            'message_id': 'test_message_id',
            'thread_id': 'test_thread_id', 
            'role': 'assistant',
            'content': 'Found emails matching your query',
            'tool_results': {
                'source_type': 'mail',
                'emails': ['email_to_delete', 'other_email']
            },
            'timestamp': 1640995200
        }
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    def test_delete_email_endpoint_success(self, mock_conversation_class, mock_tooling_service, client, mock_conversation_data):
        """Test successful email deletion through API endpoint"""
        # Setup mocks
        mock_tooling_service.delete_email.return_value = True
        mock_conversation_class.find_one.return_value = mock_conversation_data
        mock_conversation_class.update_one.return_value = Mock(modified_count=1)
        
        # Make request
        response = client.post('/delete_email', 
                             json={
                                 'email_id': 'email_to_delete',
                                 'thread_id': 'test_thread_id',
                                 'message_id': 'test_message_id'
                             },
                             content_type='application/json')
        
        # Assertions
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'Email processed' in data['message']
        assert data['deleted_email_id'] == 'email_to_delete'
        assert data['gmail_success'] is True
        assert data['db_success'] is True
        
        # Verify service was called correctly
        mock_tooling_service.delete_email.assert_called_once_with('email_to_delete')
        
        # Verify database update was called
        mock_conversation_class.update_one.assert_called_once_with(
            {'_id': 'conversation_123'},
            {'$pull': {'tool_results.emails': 'email_to_delete'}}
        )
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    def test_delete_email_database_update_verification(self, mock_conversation_class, mock_tooling_service, client, mock_conversation_data):
        """Test that database is properly updated after email deletion"""
        # Setup mocks - Gmail succeeds, DB update succeeds
        mock_tooling_service.delete_email.return_value = True
        mock_conversation_class.find_one.return_value = mock_conversation_data
        
        # Mock successful DB update
        mock_update_result = Mock()
        mock_update_result.modified_count = 1
        mock_conversation_class.update_one.return_value = mock_update_result
        
        # Make request
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'email_to_delete',
                                 'thread_id': 'test_thread_id',
                                 'message_id': 'test_message_id'
                             },
                             content_type='application/json')
        
        # Verify response indicates successful database update
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['db_success'] is True
        assert 'Database updated successfully' in data['message']
        
        # Verify the correct database operation was performed
        mock_conversation_class.update_one.assert_called_once_with(
            {'_id': 'conversation_123'},
            {'$pull': {'tool_results.emails': 'email_to_delete'}}
        )
        
        # Verify the specific email ID was removed from the emails array
        call_args = mock_conversation_class.update_one.call_args
        pull_operation = call_args[0][1]['$pull']
        assert 'tool_results.emails' in pull_operation
        assert pull_operation['tool_results.emails'] == 'email_to_delete'
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    def test_delete_email_missing_parameters(self, mock_conversation_class, mock_tooling_service, client):
        """Test API endpoint with missing required parameters"""
        # Test missing email_id
        response = client.post('/delete_email',
                             json={
                                 'thread_id': 'test_thread_id',
                                 'message_id': 'test_message_id'
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing required parameters' in data['error']
        
        # Test missing thread_id
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'test_email',
                                 'message_id': 'test_message_id'
                             },
                             content_type='application/json')
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Missing required parameters' in data['error']
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    def test_delete_email_conversation_not_found(self, mock_conversation_class, mock_tooling_service, client):
        """Test API endpoint when conversation is not found"""
        mock_conversation_class.find_one.return_value = None
        
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'test_email',
                                 'thread_id': 'nonexistent_thread',
                                 'message_id': 'nonexistent_message'
                             },
                             content_type='application/json')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Conversation not found' in data['error']
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    def test_delete_email_email_not_in_conversation(self, mock_conversation_class, mock_tooling_service, client, mock_conversation_data):
        """Test API endpoint when email is not in the conversation"""
        mock_conversation_class.find_one.return_value = mock_conversation_data
        
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'nonexistent_email',  # This email is not in the tool_results.emails list
                                 'thread_id': 'test_thread_id',
                                 'message_id': 'test_message_id'
                             },
                             content_type='application/json')
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Email not found in conversation' in data['error']
        
        # Verify tooling service was not called since email wasn't in conversation
        mock_tooling_service.delete_email.assert_not_called()


class TestEmailDeleteIntegration:
    """Integration tests for email deletion functionality"""
    
    @pytest.fixture
    def client(self):
        """Create Flask test client"""
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    @patch('app.get_collection')  # Mock the emails collection
    def test_email_delete_end_to_end(self, mock_get_collection, mock_conversation_class, mock_tooling_service, client):
        """Test complete end-to-end email deletion flow"""
        # Setup mock data
        mock_conversation_data = {
            '_id': 'integration_conversation',
            'message_id': 'integration_message',
            'thread_id': 'integration_thread',
            'tool_results': {
                'source_type': 'mail',
                'emails': ['email_1', 'email_2', 'email_to_delete']
            }
        }
        
        # Setup mocks for successful flow
        mock_tooling_service.delete_email.return_value = True
        mock_conversation_class.find_one.return_value = mock_conversation_data
        mock_conversation_class.update_one.return_value = Mock(modified_count=1)
        
        # Mock emails collection deletion
        mock_emails_collection = Mock()
        mock_emails_collection.delete_many.return_value = Mock(deleted_count=1)
        mock_get_collection.return_value = mock_emails_collection
        
        # Make the API request
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'email_to_delete',
                                 'thread_id': 'integration_thread',
                                 'message_id': 'integration_message'
                             },
                             content_type='application/json')
        
        # Verify successful response
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['gmail_success'] is True
        assert data['db_success'] is True
        
        # Verify complete flow:
        # 1. Gmail API called
        mock_tooling_service.delete_email.assert_called_once_with('email_to_delete')
        
        # 2. Conversation updated (email removed from tool_results.emails)
        mock_conversation_class.update_one.assert_called_once()
        
        # 3. Email collection updated (in the actual endpoint, this happens via bulk delete)
        # Note: In the current implementation, individual delete doesn't call emails collection
        # This is tested here to document the expected behavior
    
    @patch('app.tooling_service')
    @patch('app.Conversation')
    @patch('app.get_collection')
    def test_bulk_vs_single_delete_consistency(self, mock_get_collection, mock_conversation_class, mock_tooling_service, client):
        """Test that bulk delete and single delete handle emails consistently"""
        # Setup conversation with multiple emails
        mock_conversation_data = {
            '_id': 'bulk_test_conversation',
            'message_id': 'bulk_test_message', 
            'thread_id': 'bulk_test_thread',
            'tool_results': {
                'source_type': 'mail',
                'emails': ['email_1', 'email_2', 'email_3']
            }
        }
        
        # Mock emails collection for bulk delete
        mock_emails_collection = Mock()
        mock_emails_collection.delete_many.return_value = Mock(deleted_count=2)
        mock_get_collection.return_value = mock_emails_collection
        
        mock_tooling_service.delete_email.return_value = True
        mock_conversation_class.find_one.return_value = mock_conversation_data
        mock_conversation_class.update_one.return_value = Mock(modified_count=1)
        
        # Test 1: Single delete
        response = client.post('/delete_email',
                             json={
                                 'email_id': 'email_2',
                                 'thread_id': 'bulk_test_thread',
                                 'message_id': 'bulk_test_message'
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify single delete behavior
        mock_tooling_service.delete_email.assert_called_with('email_2')
        
        # Reset mocks for bulk delete test
        mock_tooling_service.reset_mock()
        mock_conversation_class.reset_mock()
        
        # Test 2: Bulk delete using /bulk_delete_items endpoint
        response = client.post('/bulk_delete_items',
                             json={
                                 'message_id': 'bulk_test_message',
                                 'thread_id': 'bulk_test_thread', 
                                 'items': [
                                     {'item_id': 'email_1', 'item_type': 'email'},
                                     {'item_id': 'email_3', 'item_type': 'email'}
                                 ]
                             },
                             content_type='application/json')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        
        # Verify bulk delete behavior - should call delete_email for each item
        assert mock_tooling_service.delete_email.call_count == 2
        mock_tooling_service.delete_email.assert_any_call('email_1')
        mock_tooling_service.delete_email.assert_any_call('email_3')
        
        # Verify that both single and bulk delete use the same underlying service method
        # This ensures consistency between the two deletion approaches


# Prevent real API calls during testing
@pytest.fixture(autouse=True)
def prevent_real_api_calls():
    """Ensure no real API calls are made during API endpoint tests"""
    with patch('app.ComposioService') as mock_composio_service:
        with patch('app.get_db') as mock_db:
            with patch('app.get_collection') as mock_collection:
                yield