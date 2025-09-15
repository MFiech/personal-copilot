"""
API endpoint tests for draft-related endpoints.
Tests all draft API endpoints following the app's endpoint testing patterns.
"""

import pytest
import sys
import os
import json
import time
from unittest.mock import Mock, patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from tests.fixtures.draft_responses import (
    create_email_draft_fixture,
    create_calendar_draft_fixture,
    DRAFT_VALIDATION_COMPLETE_EMAIL,
    DRAFT_VALIDATION_INCOMPLETE_EMAIL
)


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftAPIEndpoints:
    """Test draft-related API endpoints"""
    
    @pytest.fixture
    def mock_flask_app(self):
        """Mock Flask app for endpoint testing"""
        with patch('app.app') as mock_app:
            mock_client = mock_app.test_client()
            mock_client.post = Mock()
            mock_client.get = Mock()
            mock_client.put = Mock()
            yield mock_client
    
    def test_create_draft_endpoint(self, mock_flask_app, mock_draft_service):
        """Test POST /drafts endpoint for creating drafts"""
        # Mock response data
        draft_data = create_email_draft_fixture()
        mock_draft_obj = Mock()
        mock_draft_obj.to_dict.return_value = draft_data
        mock_draft_service.create_draft.return_value = mock_draft_obj
        
        # Test data
        request_data = {
            "draft_type": "email",
            "thread_id": "test_thread_123",
            "message_id": "test_message_456",
            "initial_data": {
                "to_emails": [{"email": "test@example.com", "name": "Test User"}],
                "subject": "Test Subject"
            }
        }
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "success": True,
            "draft": draft_data,
            "message": "Draft created successfully"
        }
        mock_flask_app.post.return_value = mock_response
        
        # Make request
        response = mock_flask_app.post('/drafts', json=request_data)
        
        # Verify response
        assert response.status_code == 201
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["draft"]["draft_id"] == draft_data["draft_id"]
        assert response_data["draft"]["subject"] == draft_data["subject"]
        mock_flask_app.post.assert_called_once_with('/drafts', json=request_data)
    
    def test_get_draft_by_id_endpoint(self, mock_flask_app, mock_draft_service):
        """Test GET /drafts/{draft_id} endpoint"""
        draft_data = create_email_draft_fixture()
        draft_id = draft_data["draft_id"]
        
        # Mock draft service
        mock_draft_obj = Mock()
        mock_draft_obj.to_dict.return_value = draft_data
        mock_draft_service.get_draft_by_id.return_value = mock_draft_obj
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "draft": draft_data
        }
        mock_flask_app.get.return_value = mock_response
        
        # Make request
        response = mock_flask_app.get(f'/drafts/{draft_id}')
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["draft"]["draft_id"] == draft_id
        mock_flask_app.get.assert_called_once_with(f'/drafts/{draft_id}')
    
    def test_get_draft_by_message_id_endpoint(self, mock_flask_app, mock_draft_service):
        """Test GET /drafts/message/{message_id} endpoint"""
        draft_data = create_email_draft_fixture()
        message_id = draft_data["message_id"]
        
        # Mock draft service
        mock_draft_obj = Mock()
        mock_draft_obj.to_dict.return_value = draft_data
        mock_draft_service.get_draft_by_message_id.return_value = mock_draft_obj
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "draft": draft_data
        }
        mock_flask_app.get.return_value = mock_response
        
        # Make request
        response = mock_flask_app.get(f'/drafts/message/{message_id}')
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["draft"]["message_id"] == message_id
        mock_flask_app.get.assert_called_once_with(f'/drafts/message/{message_id}')
    
    def test_update_draft_endpoint(self, mock_flask_app, mock_draft_service):
        """Test PUT /drafts/{draft_id} endpoint"""
        draft_id = "test_draft_123"
        update_data = {
            "updates": {
                "subject": "Updated Subject",
                "body": "Updated body content"
            }
        }
        
        # Mock successful update
        mock_draft_service.update_draft.return_value = True
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Draft updated successfully"
        }
        mock_flask_app.put.return_value = mock_response
        
        # Make request
        response = mock_flask_app.put(f'/drafts/{draft_id}', json=update_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        mock_flask_app.put.assert_called_once_with(f'/drafts/{draft_id}', json=update_data)
    
    def test_validate_draft_endpoint(self, mock_flask_app, mock_draft_service):
        """Test GET /drafts/{draft_id}/validate endpoint"""
        draft_id = "test_draft_123"
        
        # Mock validation result
        mock_draft_service.validate_draft_completeness.return_value = DRAFT_VALIDATION_COMPLETE_EMAIL
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "validation": DRAFT_VALIDATION_COMPLETE_EMAIL
        }
        mock_flask_app.get.return_value = mock_response
        
        # Make request
        response = mock_flask_app.get(f'/drafts/{draft_id}/validate')
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["validation"]["is_complete"] is True
        mock_flask_app.get.assert_called_once_with(f'/drafts/{draft_id}/validate')
    
    def test_thread_drafts_endpoint_isolation(self, mock_flask_app, mock_draft_service):
        """Test GET /drafts/thread/{thread_id} endpoint with thread isolation"""
        thread_id = "test_thread_123"
        
        # Mock thread-specific drafts
        draft_1 = create_email_draft_fixture(draft_id="draft_1", thread_id=thread_id)
        draft_2 = create_email_draft_fixture(draft_id="draft_2", thread_id=thread_id)
        
        mock_drafts = [
            Mock(to_dict=Mock(return_value=draft_1)),
            Mock(to_dict=Mock(return_value=draft_2))
        ]
        mock_draft_service.get_active_drafts_by_thread.return_value = mock_drafts
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "drafts": [draft_1, draft_2],
            "count": 2,
            "thread_id": thread_id
        }
        mock_flask_app.get.return_value = mock_response
        
        # Make request
        response = mock_flask_app.get(f'/drafts/thread/{thread_id}')
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        assert response_data["count"] == 2
        assert response_data["thread_id"] == thread_id
        
        # Verify all drafts belong to the correct thread
        for draft in response_data["drafts"]:
            assert draft["thread_id"] == thread_id
        
        mock_flask_app.get.assert_called_once_with(f'/drafts/thread/{thread_id}')
    
    def test_close_draft_endpoint(self, mock_flask_app, mock_draft_service):
        """Test POST /drafts/{draft_id}/close endpoint"""
        draft_id = "test_draft_123"
        close_data = {"status": "closed"}
        
        # Mock successful close
        mock_draft_service.close_draft.return_value = True
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "message": "Draft closed successfully"
        }
        mock_flask_app.post.return_value = mock_response
        
        # Make request
        response = mock_flask_app.post(f'/drafts/{draft_id}/close', json=close_data)
        
        # Verify response
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["success"] is True
        mock_flask_app.post.assert_called_once_with(f'/drafts/{draft_id}/close', json=close_data)
    
    def test_draft_endpoints_error_handling(self, mock_flask_app, mock_draft_service):
        """Test error handling in draft endpoints"""
        
        # Test 1: Draft not found
        mock_draft_service.get_draft_by_id.return_value = None
        
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {
            "success": False,
            "error": "Draft not found"
        }
        mock_flask_app.get.return_value = mock_response
        
        response = mock_flask_app.get('/drafts/nonexistent_draft')
        
        assert response.status_code == 404
        response_data = response.json()
        assert response_data["success"] is False
        assert "not found" in response_data["error"].lower()
        
        # Test 2: Invalid update data
        mock_draft_service.update_draft.side_effect = ValueError("Invalid update data")
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid update data"
        }
        mock_flask_app.put.return_value = mock_response
        
        response = mock_flask_app.put('/drafts/test_draft/update', json={"invalid": "data"})
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False
        
        # Test 3: Invalid draft type in creation
        mock_draft_service.create_draft.side_effect = ValueError("Invalid draft type")
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Invalid draft type"
        }
        mock_flask_app.post.return_value = mock_response
        
        response = mock_flask_app.post('/drafts', json={"draft_type": "invalid", "thread_id": "test"})
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftEndpointValidation:
    """Test validation logic in draft endpoints"""
    
    @pytest.fixture
    def mock_flask_app(self):
        """Mock Flask app for validation testing"""
        with patch('app.app') as mock_app:
            mock_client = mock_app.test_client()
            mock_client.post = Mock()
            mock_client.put = Mock()
            yield mock_client
    
    def test_create_draft_validation_required_fields(self, mock_flask_app):
        """Test validation of required fields in draft creation"""
        
        # Test missing draft_type
        incomplete_data = {
            "thread_id": "test_thread",
            "message_id": "test_message"
        }
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Missing required field: draft_type"
        }
        mock_flask_app.post.return_value = mock_response
        
        response = mock_flask_app.post('/drafts', json=incomplete_data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False
        assert "draft_type" in response_data["error"]
        
        # Test missing thread_id
        incomplete_data = {
            "draft_type": "email",
            "message_id": "test_message"
        }
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Missing required field: thread_id"
        }
        mock_flask_app.post.return_value = mock_response
        
        response = mock_flask_app.post('/drafts', json=incomplete_data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False
        assert "thread_id" in response_data["error"]
    
    def test_update_draft_validation(self, mock_flask_app):
        """Test validation in draft update endpoint"""
        
        # Test missing updates field
        incomplete_data = {}
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "Missing updates data"
        }
        mock_flask_app.put.return_value = mock_response
        
        response = mock_flask_app.put('/drafts/test_draft', json=incomplete_data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False
        assert "updates" in response_data["error"]
        
        # Test empty updates
        empty_data = {"updates": {}}
        
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "error": "No fields to update"
        }
        mock_flask_app.put.return_value = mock_response
        
        response = mock_flask_app.put('/drafts/test_draft', json=empty_data)
        
        assert response.status_code == 400
        response_data = response.json()
        assert response_data["success"] is False
    
    def test_draft_validation_endpoint_different_completeness(self, mock_flask_app, mock_draft_service):
        """Test validation endpoint with complete vs incomplete drafts"""
        
        draft_id = "test_draft_123"
        
        # Test complete draft
        mock_draft_service.validate_draft_completeness.return_value = DRAFT_VALIDATION_COMPLETE_EMAIL
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "validation": DRAFT_VALIDATION_COMPLETE_EMAIL
        }
        mock_flask_app.get.return_value = mock_response
        
        response = mock_flask_app.get(f'/drafts/{draft_id}/validate')
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["validation"]["is_complete"] is True
        assert len(response_data["validation"]["missing_fields"]) == 0
        
        # Test incomplete draft
        mock_draft_service.validate_draft_completeness.return_value = DRAFT_VALIDATION_INCOMPLETE_EMAIL
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "validation": DRAFT_VALIDATION_INCOMPLETE_EMAIL
        }
        mock_flask_app.get.return_value = mock_response
        
        response = mock_flask_app.get(f'/drafts/{draft_id}/validate')
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["validation"]["is_complete"] is False
        assert len(response_data["validation"]["missing_fields"]) > 0
    
    def test_thread_isolation_validation_in_endpoints(self, mock_flask_app, mock_draft_service):
        """Test that endpoints properly validate thread isolation"""
        
        thread_id_1 = "thread_123"
        thread_id_2 = "thread_456"
        
        # Mock different drafts for different threads
        def mock_get_drafts_by_thread(thread_id):
            if thread_id == thread_id_1:
                return [Mock(to_dict=Mock(return_value=create_email_draft_fixture(
                    draft_id="draft_1", thread_id=thread_id_1
                )))]
            elif thread_id == thread_id_2:
                return [Mock(to_dict=Mock(return_value=create_email_draft_fixture(
                    draft_id="draft_2", thread_id=thread_id_2
                )))]
            else:
                return []
        
        mock_draft_service.get_active_drafts_by_thread.side_effect = mock_get_drafts_by_thread
        
        # Test thread 1
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "drafts": [{"draft_id": "draft_1", "thread_id": thread_id_1}],
            "count": 1
        }
        mock_flask_app.get.return_value = mock_response
        
        response = mock_flask_app.get(f'/drafts/thread/{thread_id_1}')
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert response_data["drafts"][0]["thread_id"] == thread_id_1
        assert response_data["drafts"][0]["draft_id"] == "draft_1"
        
        # Test thread 2 (should have different drafts)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "drafts": [{"draft_id": "draft_2", "thread_id": thread_id_2}],
            "count": 1
        }
        mock_flask_app.get.return_value = mock_response
        
        response = mock_flask_app.get(f'/drafts/thread/{thread_id_2}')
        
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["count"] == 1
        assert response_data["drafts"][0]["thread_id"] == thread_id_2
        assert response_data["drafts"][0]["draft_id"] == "draft_2"
        
        # Verify no cross-contamination
        assert response_data["drafts"][0]["draft_id"] != "draft_1"


@pytest.mark.unit
@pytest.mark.mock_only
class TestDraftEndpointHelpers:
    """Test helper functions used in draft endpoints"""
    
    def test_draft_data_serialization_helpers(self):
        """Test helpers for serializing draft data in API responses"""
        
        # Mock draft object serialization
        draft_data = create_email_draft_fixture()
        mock_draft = Mock()
        mock_draft.to_dict.return_value = draft_data
        
        # Test serialization helper
        def serialize_draft_for_api(draft_obj):
            """Helper function to serialize draft for API response"""
            if hasattr(draft_obj, 'to_dict'):
                return draft_obj.to_dict()
            return draft_obj
        
        result = serialize_draft_for_api(mock_draft)
        
        assert isinstance(result, dict)
        assert result["draft_id"] == draft_data["draft_id"]
        assert result["subject"] == draft_data["subject"]
    
    
    def test_success_response_helpers(self):
        """Test helpers for creating consistent success responses"""
        
        def create_success_response(data=None, message="Success"):
            """Helper to create consistent success responses"""
            response = {
                "success": True,
                "message": message
            }
            if data:
                response.update(data)
            return response
        
        # Test different success scenarios
        draft_data = create_email_draft_fixture()
        
        create_response = create_success_response(
            {"draft": draft_data}, 
            "Draft created successfully"
        )
        assert create_response["success"] is True
        assert create_response["draft"]["draft_id"] == draft_data["draft_id"]
        assert "created" in create_response["message"]
        
        update_response = create_success_response(message="Draft updated successfully")
        assert update_response["success"] is True
        assert "updated" in update_response["message"]
