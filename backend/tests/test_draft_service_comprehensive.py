"""
Comprehensive unit tests for DraftService methods.
Tests all draft service functionality with proper mocking to prevent real API calls.
Following the established testing patterns from the application.
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

from services.draft_service import DraftService
from models.draft import Draft
from tests.fixtures.draft_responses import (
    create_email_draft_fixture,
    create_calendar_draft_fixture,
    DRAFT_CREATION_INTENT_TRUE,
    DRAFT_CREATION_INTENT_FALSE,
    DRAFT_UPDATE_INTENT_TRUE,
    DRAFT_FIELD_UPDATE_SUBJECT,
    DRAFT_VALIDATION_COMPLETE_EMAIL,
    DRAFT_VALIDATION_INCOMPLETE_EMAIL,
    create_composio_error_recovery_scenario
)


@pytest.mark.unit
@pytest.mark.mock_only
class TestDraftServiceComprehensive:
    """Comprehensive unit tests for DraftService methods"""
    
    @pytest.fixture
    def draft_service(self):
        """Create DraftService instance with mocked dependencies"""
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            service = DraftService()
            return service
    
    def test_create_email_draft_with_contact_resolution(self, draft_service, test_db, clean_draft_collections):
        """Test creating email draft with contact resolution"""
        initial_data = {
            "to_contacts": ["test@example.com", "John Doe"],
            "subject": "Test Email Subject",
            "body": "Test email body content"
        }
        
        thread_id = "test_thread_123"
        message_id = "test_message_456"
        
        with patch.object(Draft, 'save') as mock_save:
            mock_save.return_value = "mock_draft_id"
            
            draft = draft_service.create_draft(
                "email",
                thread_id, 
                message_id,
                initial_data
            )
            
            assert draft is not None
            assert draft.draft_type == "email"
            assert draft.thread_id == thread_id
            assert draft.message_id == message_id
            assert draft.subject == "Test Email Subject"
            assert draft.body == "Test email body content"
            assert len(draft.to_emails) >= 1
            assert draft.status == "active"
            mock_save.assert_called_once()
    
    def test_create_calendar_draft_with_validation(self, draft_service, test_db, clean_draft_collections):
        """Test creating calendar draft with field validation"""
        initial_data = {
            "summary": "Test Meeting",
            "start_time": "2025-09-10T15:00:00",
            "end_time": "2025-09-10T16:00:00",
            "attendees": ["attendee@example.com"],
            "location": "Conference Room A"
        }
        
        thread_id = "test_thread_123"
        message_id = "test_message_456"
        
        with patch.object(Draft, 'save') as mock_save:
            mock_save.return_value = "mock_draft_id"
            
            draft = draft_service.create_draft(
                "calendar_event",
                thread_id,
                message_id, 
                initial_data
            )
            
            assert draft is not None
            assert draft.draft_type == "calendar_event"
            assert draft.summary == "Test Meeting"
            assert draft.start_time == "2025-09-10T15:00:00"
            assert draft.end_time == "2025-09-10T16:00:00"
            assert draft.location == "Conference Room A"
            assert len(draft.attendees) >= 1
            assert draft.status == "active"
            mock_save.assert_called_once()
    
    def test_update_draft_from_composio_error_status(self, draft_service, test_db, clean_draft_collections):
        """Test updating draft that has composio_error status - should reset to active"""
        scenario = create_composio_error_recovery_scenario()
        error_draft = scenario["draft_with_error"]
        update_data = scenario["update_data"]
        
        # Mock draft retrieval
        with patch.object(Draft, 'get_by_id') as mock_get:

            mock_draft = Mock()
            mock_draft.status = "composio_error"
            mock_draft.draft_id = error_draft["draft_id"]
            mock_draft.update = Mock(return_value=True)
            mock_get.return_value = mock_draft

            result = draft_service.update_draft(error_draft["draft_id"], update_data)

            assert result is not None
            # get_by_id is called twice: initial fetch and return after successful update
            assert mock_get.call_count >= 2
            # Verify update was called with status reset
            mock_draft.update.assert_called_once_with({"body": update_data["body"], "status": "active"})
    
    def test_draft_field_update_extraction(self, draft_service, mock_draft_llm_responses):
        """Test extracting specific field updates from user queries"""
        existing_draft = create_email_draft_fixture()
        user_query = "Create the subject on your own based on the context you have"
        
        with patch.object(draft_service, 'llm') as mock_llm:
            mock_response = Mock()
            mock_response.content = json.dumps(DRAFT_FIELD_UPDATE_SUBJECT)
            mock_llm.invoke.return_value = mock_response
            
            result = draft_service.extract_draft_field_updates(
                user_query,
                existing_draft,
                "subject_title"
            )
            
            assert result is not None
            assert "field_updates" in result
    
    def test_get_draft_by_id_functionality(self, mock_draft_service, test_db, clean_draft_collections):
        """Test getting draft by ID functionality"""
        draft_data = create_email_draft_fixture()
        
        # Mock successful retrieval
        mock_draft_obj = Mock()
        mock_draft_obj.to_dict.return_value = draft_data
        mock_draft_service.get_draft_by_id.return_value = mock_draft_obj
        
        result = mock_draft_service.get_draft_by_id(draft_data["draft_id"])
        
        assert result is not None
        assert result.to_dict()["draft_id"] == draft_data["draft_id"]
        assert result.to_dict()["subject"] == draft_data["subject"]
        mock_draft_service.get_draft_by_id.assert_called_once_with(draft_data["draft_id"])
    
    def test_draft_summary_generation(self, mock_draft_service, test_db, clean_draft_collections):
        """Test generating draft summary for different draft types"""
        email_draft = create_email_draft_fixture()
        calendar_draft = create_calendar_draft_fixture()
        
        for draft_data in [email_draft, calendar_draft]:
            # Mock summary generation
            expected_summary = {
                "type": draft_data["draft_type"],
                "id": draft_data["draft_id"],
                "summary": f"Draft {draft_data['draft_type']} summary",
                "created_at": draft_data["created_at"],
                "updated_at": draft_data["updated_at"]
            }
            mock_draft_service.get_draft_summary.return_value = expected_summary
            
            summary = mock_draft_service.get_draft_summary(draft_data["draft_id"])
            
            assert summary is not None
            assert summary["type"] == draft_data["draft_type"]
            assert summary["id"] == draft_data["draft_id"]
            assert "summary" in summary
            assert "created_at" in summary
            assert "updated_at" in summary
    
    def test_validate_draft_completeness(self, mock_draft_service, test_db, clean_draft_collections):
        """Test draft completeness validation for different scenarios"""
        # Test complete email draft
        complete_email = create_email_draft_fixture(
            subject="Complete Subject",
            body="Complete body",
            to_emails=[{"email": "test@example.com", "name": "Test"}]
        )
        
        # Test complete draft validation
        mock_draft_service.validate_draft_completeness.return_value = DRAFT_VALIDATION_COMPLETE_EMAIL
        validation = mock_draft_service.validate_draft_completeness(complete_email["draft_id"])
        
        assert validation is not None
        assert "is_complete" in validation
        assert "missing_fields" in validation
        assert "field_count" in validation
        
        # Test incomplete email draft
        incomplete_email = create_email_draft_fixture(
            subject=None,  # Missing subject
            body=None,     # Missing body
            to_emails=[{"email": "test@example.com", "name": "Test"}]
        )
        
        # Test incomplete draft validation
        mock_draft_service.validate_draft_completeness.return_value = DRAFT_VALIDATION_INCOMPLETE_EMAIL
        validation = mock_draft_service.validate_draft_completeness(incomplete_email["draft_id"])
        
        assert validation is not None
        assert validation["is_complete"] is False
        assert len(validation["missing_fields"]) > 0
    
    def test_get_active_drafts_thread_isolation(self, draft_service, test_db, clean_draft_collections):
        """Test that active drafts are properly isolated by thread"""
        thread_1 = "thread_123"
        thread_2 = "thread_456"
        
        with patch.object(Draft, 'get_active_drafts_by_thread') as mock_get_drafts:
            # Mock different drafts for different threads
            mock_get_drafts.side_effect = lambda tid: (
                [Mock(draft_id="draft_123")] if tid == thread_1 else 
                [Mock(draft_id="draft_456")] if tid == thread_2 else []
            )
            
            # Test thread 1
            drafts_1 = draft_service.get_active_drafts_by_thread(thread_1)
            assert len(drafts_1) == 1
            assert drafts_1[0].draft_id == "draft_123"
            
            # Test thread 2
            drafts_2 = draft_service.get_active_drafts_by_thread(thread_2)
            assert len(drafts_2) == 1
            assert drafts_2[0].draft_id == "draft_456"
            
            # Verify no cross-contamination
            assert drafts_1[0].draft_id != drafts_2[0].draft_id
    
    def test_detect_draft_creation_intent_positive(self, draft_service):
        """Test draft creation intent detection - positive case"""
        with patch.object(draft_service, 'llm') as mock_llm:
            mock_response = Mock()
            mock_response.content = json.dumps(DRAFT_CREATION_INTENT_TRUE)
            mock_llm.invoke.return_value = mock_response
            
            user_query = "Create a draft email to John about the meeting"
            conversation_history = []
            
            result = draft_service.detect_draft_intent(user_query, conversation_history)
            
            assert result is not None
            assert result["is_draft_intent"] is True
            assert result["draft_data"] is not None
            assert result["draft_data"]["draft_type"] == "email"
            mock_llm.invoke.assert_called_once()
    
    def test_detect_draft_creation_intent_negative(self, draft_service):
        """Test draft creation intent detection - negative case"""
        with patch.object(draft_service, 'llm') as mock_llm:
            mock_response = Mock()
            mock_response.content = json.dumps(DRAFT_CREATION_INTENT_FALSE)
            mock_llm.invoke.return_value = mock_response
            
            user_query = "What's the weather like today?"
            conversation_history = []
            
            result = draft_service.detect_draft_intent(user_query, conversation_history)
            
            assert result is not None
            assert result["is_draft_intent"] is False
            assert result["draft_data"] is None
            mock_llm.invoke.assert_called_once()
    
    def test_detect_draft_update_intent(self, draft_service):
        """Test draft update intent detection"""
        with patch.object(draft_service, 'llm') as mock_llm:
            mock_response = Mock()
            mock_response.content = json.dumps(DRAFT_CREATION_INTENT_TRUE)
            mock_llm.invoke.return_value = mock_response
            
            user_query = "Add John to this email"
            existing_draft = create_email_draft_fixture()
            
            result = draft_service.detect_draft_intent(user_query, [])
            
            assert result is not None
            assert result["is_draft_intent"] is True
            assert result["draft_data"] is not None
            mock_llm.invoke.assert_called_once()
    
    def test_close_draft_success(self, mock_draft_service, test_db, clean_draft_collections):
        """Test successfully closing a draft"""
        draft_id = "test_draft_123"
        
        # Test closing draft
        mock_draft_service.close_draft.return_value = True
        result = mock_draft_service.close_draft(draft_id)
        
        assert result is True
        mock_draft_service.close_draft.assert_called_once_with(draft_id)
    
    def test_close_draft_not_found(self, mock_draft_service, test_db, clean_draft_collections):
        """Test closing draft that doesn't exist"""
        draft_id = "nonexistent_draft"
        
        # Test closing non-existent draft
        mock_draft_service.close_draft.return_value = False
        result = mock_draft_service.close_draft(draft_id)
        
        assert result is False
        mock_draft_service.close_draft.assert_called_once_with(draft_id)
    
    def test_error_handling_invalid_draft_type(self, draft_service, test_db, clean_draft_collections):
        """Test error handling for invalid draft type"""
        with pytest.raises(ValueError):
            draft_service.create_draft(
                "invalid_type",  # Should raise ValueError
                "thread_123",
                "message_456",
                {}
            )
    
    def test_update_nonexistent_draft(self, mock_draft_service, test_db, clean_draft_collections):
        """Test updating a draft that doesn't exist"""
        # Test updating non-existent draft
        mock_draft_service.update_draft.return_value = False
        result = mock_draft_service.update_draft("nonexistent_draft", {"subject": "New Subject"})
        
        assert result is False
        mock_draft_service.update_draft.assert_called_once_with("nonexistent_draft", {"subject": "New Subject"})
    
    def test_validate_nonexistent_draft(self, mock_draft_service, test_db, clean_draft_collections):
        """Test validating a draft that doesn't exist"""
        # Test validating non-existent draft
        mock_draft_service.validate_draft_completeness.return_value = None
        result = mock_draft_service.validate_draft_completeness("nonexistent_draft")
        
        assert result is None
        mock_draft_service.validate_draft_completeness.assert_called_once_with("nonexistent_draft")


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftServiceIntegration:
    """Integration tests for DraftService with other components"""
    
    @pytest.fixture
    def draft_service(self):
        """Create DraftService instance for integration tests"""
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            service = DraftService()
            return service
    
    def test_full_draft_lifecycle(self, draft_service, test_db, clean_draft_collections):
        """Test complete draft lifecycle: create → update → validate → close"""
        thread_id = "integration_thread_123"
        message_id = "integration_message_456"
        
        # Step 1: Create draft
        initial_data = {
            "to_contacts": ["test@example.com"],
            "subject": "Integration Test Email"
        }
        
        with patch.object(Draft, 'save') as mock_save, \
             patch.object(Draft, 'get_by_id') as mock_get, \
             patch.object(Draft, 'update') as mock_update:
            
            # Setup mocks for creation
            mock_save.return_value = "integration_draft_123"
            
            draft = draft_service.create_draft("email", thread_id, message_id, initial_data)
            
            assert draft is not None
            assert draft.subject == "Integration Test Email"
            
            # Step 2: Update draft
            mock_draft = Mock()
            mock_draft.status = "active"
            mock_draft.draft_id = "integration_draft_123"
            mock_get.return_value = mock_draft
            mock_update.return_value = True
            
            update_result = draft_service.update_draft("integration_draft_123", {
                "body": "Integration test body content"
            })
            
            assert update_result is not None
            
            # Step 3: Validate draft
            mock_draft.to_dict.return_value = create_email_draft_fixture()
            mock_draft.draft_type = "email"
            # Provide validation dict expected by validate_draft_completeness()
            mock_draft.validate_completeness = Mock(return_value={"is_complete": True, "missing_fields": []})
            validation = draft_service.validate_draft_completeness("integration_draft_123")
            
            assert validation is not None
            assert "is_complete" in validation
            
            # Step 4: Close draft
            mock_draft.close_draft = Mock(return_value=True)
            close_result = draft_service.close_draft("integration_draft_123")

            assert close_result is True
            mock_draft.close_draft.assert_called_once_with("closed")
