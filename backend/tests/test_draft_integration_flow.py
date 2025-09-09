"""
End-to-end integration tests for draft workflows.
Tests complete draft flows from creation to completion following the app's integration patterns.
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

from utils.mongo_client import get_collection
from models.draft import Draft
from models.conversation import Conversation
from services.draft_service import DraftService
from tests.fixtures.draft_responses import (
    create_email_draft_fixture,
    create_calendar_draft_fixture,
    create_composio_error_recovery_scenario,
    CONVERSATION_WITH_DRAFT_CONTENT,
    EXPECTED_EXTRACTED_CONTENT,
    DRAFT_CREATION_INTENT_TRUE,
    DRAFT_UPDATE_INTENT_TRUE,
    DRAFT_FIELD_UPDATE_SUBJECT,
    COMPOSIO_SEND_EMAIL_SUCCESS
)


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftIntegrationFlow:
    """End-to-end integration tests for draft workflows"""
    
    def test_complete_email_draft_creation_to_send_pipeline(
        self, 
        test_db, 
        clean_draft_collections, 
        mock_draft_composio_service,
        conversation_cleanup
    ):
        """
        INTEGRATION TEST: Complete email draft creation → update → send pipeline.
        
        Tests the full workflow:
        1. User creates draft intent
        2. Draft is created and stored
        3. User updates draft with LLM content
        4. Draft is sent via Composio
        5. Status is updated appropriately
        """
        thread_id = "integration_test_thread_123"
        message_id = "integration_test_message_456"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Step 1: Create initial draft
            initial_data = {
                "to_contacts": ["john@example.com"],
                "subject": "Integration Test Email",
                "body": "Initial draft body"
            }
            
            with patch.object(Draft, 'save') as mock_save:
                mock_save.return_value = "integration_draft_123"
                
                draft = draft_service.create_draft(
                    "email",
                    thread_id,
                    message_id, 
                    initial_data
                )
                
                assert draft is not None
                assert draft.draft_id is not None
                assert draft.subject == "Integration Test Email"
                assert draft.status == "active"
                mock_save.assert_called_once()
            
            # Step 2: Update draft with additional content
            with patch.object(Draft, 'get_by_id') as mock_get:
                
                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.draft_id = "integration_draft_123"
                # Mock instance update method
                mock_draft.update = Mock(return_value=True)
                mock_get.return_value = mock_draft
                
                update_result = draft_service.update_draft(
                    "integration_draft_123",
                    {"body": "Updated draft body with more details"}
                )
                
                assert update_result is not None
                mock_draft.update.assert_called_once()
            
            # Step 3: Validate draft completeness
            complete_draft_data = create_email_draft_fixture(
                draft_id="integration_draft_123",
                subject="Integration Test Email",
                body="Updated draft body with more details",
                to_emails=[{"email": "john@example.com", "name": "John"}]
            )
            
            with patch.object(Draft, 'get_by_id') as mock_get:
                mock_draft = Mock()
                mock_draft.to_dict.return_value = complete_draft_data
                mock_draft.draft_type = "email"
                # Instance validation returns a dict
                mock_draft.validate_completeness = Mock(return_value={"is_complete": True, "missing_fields": []})
                mock_get.return_value = mock_draft

                validation = draft_service.validate_draft_completeness("integration_draft_123")

                assert validation is not None
                assert "is_complete" in validation
            
            # Step 4: Convert to Composio params and send
            with patch.object(Draft, 'get_by_id') as mock_get:
                mock_draft = Mock()
                mock_draft.to_dict.return_value = complete_draft_data
                mock_draft.draft_type = "email"
                # Ensure validate_completeness returns dict
                mock_draft.validate_completeness = Mock(return_value={"is_complete": True, "missing_fields": []})
                # Mock to_emails for convert_draft_to_composio_params
                mock_draft.to_emails = [{"email": "john@example.com", "name": "John"}]
                mock_draft.subject = "Integration Test Email"
                mock_draft.body = "Updated draft body with more details"
                mock_draft.attachments = []
                mock_get.return_value = mock_draft

                composio_params = draft_service.convert_draft_to_composio_params("integration_draft_123")
                
                assert composio_params is not None
                assert "to_emails" in composio_params
                assert "subject" in composio_params
                assert "body" in composio_params
                
                # Simulate sending via Composio
                send_result = mock_draft_composio_service.send_email(**composio_params)
                
                assert send_result["successful"] is True
                assert "messageId" in send_result["data"]
            
            # Step 5: Close draft after successful send
            with patch.object(Draft, 'get_by_id') as mock_get:

                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.close_draft = Mock(return_value=True)
                mock_get.return_value = mock_draft

                close_result = draft_service.close_draft("integration_draft_123")

                assert close_result is True
                mock_draft.close_draft.assert_called_once_with("closed")
    
    def test_draft_update_with_llm_content_extraction(
        self, 
        test_db, 
        clean_draft_collections,
        conversation_cleanup
    ):
        """
        INTEGRATION TEST: Draft update with LLM-generated content extraction.
        
        Tests the workflow where LLM generates content that needs to be applied to draft.
        """
        thread_id = "llm_content_thread_123"
        message_id = "llm_content_message_456"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Create existing draft
            existing_draft = create_email_draft_fixture(
                body="We need to discuss the timing for our meeting next week"
            )
            
            # Simulate content extraction from conversation
            user_query = "Create the subject on your own based on the context you have"
            
            # Mock LLM response for field update
            with patch.object(draft_service, 'llm') as mock_llm:
                mock_response = Mock()
                mock_response.content = json.dumps(DRAFT_FIELD_UPDATE_SUBJECT)
                mock_llm.invoke.return_value = mock_response
                
                # Test field update extraction  
                update_result = draft_service.extract_draft_field_updates(
                    user_query,
                    existing_draft,
                    "subject_title"
                )
                
                assert update_result is not None
                assert "field_updates" in update_result
                mock_llm.invoke.assert_called_once()
            
            # Test applying extracted content to draft
            with patch.object(Draft, 'get_by_id') as mock_get:
                
                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.draft_id = existing_draft["draft_id"]
                mock_draft.update = Mock(return_value=True)
                mock_get.return_value = mock_draft
                
                # Apply the extracted content
                update_success = draft_service.update_draft(
                    existing_draft["draft_id"],
                    update_result["field_updates"]
                )
                
                # update_draft returns updated Draft object (truthy) or None
                assert update_success is not None
                mock_draft.update.assert_called_once()
    
    def test_draft_status_recovery_from_composio_error(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """
        INTEGRATION TEST: Draft status recovery from Composio error.
        
        Tests the workflow where a draft fails to send and then recovers.
        """
        thread_id = "error_recovery_thread_123"
        conversation_cleanup(thread_id)
        
        scenario = create_composio_error_recovery_scenario()
        error_draft = scenario["draft_with_error"]
        update_data = scenario["update_data"]
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Step 1: Draft has composio_error status
            with patch.object(Draft, 'get_by_id') as mock_get:
                mock_draft = Mock()
                mock_draft.status = "composio_error"
                mock_draft.draft_id = error_draft["draft_id"]
                mock_draft.to_dict.return_value = error_draft
                # Provide validation to allow summary generation
                mock_draft.validate_completeness = Mock(return_value={"is_complete": False, "missing_fields": ["subject"]})
                # Ensure draft_type available for summary
                mock_draft.draft_type = "email"
                mock_draft.to_emails = []
                mock_draft.subject = None
                mock_draft.body = None
                mock_draft.created_at = 0
                mock_draft.updated_at = 0
                mock_get.return_value = mock_draft

                # Verify draft is in error state
                draft_summary = draft_service.get_draft_summary(error_draft["draft_id"])

                # Should handle error status appropriately
                # get_draft_summary may return dict or None if draft missing; since mocked get_by_id returns a draft,
                # we expect a dict here
                assert draft_summary is not None
            
            # Step 2: User updates draft → should reset status to active
            with patch.object(Draft, 'get_by_id') as mock_get:
                
                mock_draft = Mock()
                mock_draft.status = "composio_error"
                mock_draft.draft_id = error_draft["draft_id"]
                mock_draft.update = Mock(return_value=True)
                mock_get.return_value = mock_draft
                
                update_result = draft_service.update_draft(
                    error_draft["draft_id"],
                    update_data
                )
                
                assert update_result is not None
                
                # Verify update was called with status reset
                mock_draft.update.assert_called_once()
                update_call_args = mock_draft.update.call_args[0][0]
                assert "status" in update_call_args
                assert update_call_args["status"] == "active"
                assert update_call_args["body"] == update_data["body"]
            
            # Step 3: Draft should now be ready for retry
            with patch.object(Draft, 'get_by_id') as mock_get:
                mock_draft = Mock()
                mock_draft.status = "active"  # Reset status
                mock_draft.to_dict.return_value = {
                    **error_draft,
                    "status": "active",
                    "body": update_data["body"]
                }
                mock_draft.draft_type = "email"
                mock_get.return_value = mock_draft
                
                # Should be able to validate as complete
                validation = draft_service.validate_draft_completeness(error_draft["draft_id"])
                
                assert validation is not None
                # Can now retry sending
    
    def test_thread_specific_draft_management(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """
        INTEGRATION TEST: Thread-specific draft management and isolation.
        
        Tests that drafts are properly isolated between different threads.
        """
        thread_1 = "thread_isolation_1"
        thread_2 = "thread_isolation_2"
        conversation_cleanup(thread_1)
        conversation_cleanup(thread_2)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Create drafts in different threads
            with patch.object(Draft, 'save') as mock_save, \
                 patch.object(Draft, 'get_active_drafts_by_thread') as mock_get_drafts:
                
                mock_save.side_effect = ["draft_1", "draft_2"]
                
                # Thread 1 drafts
                draft_1 = draft_service.create_draft(
                    "email",
                    thread_1,
                    "message_1",
                    {"subject": "Thread 1 Draft"}
                )
                
                # Thread 2 drafts
                draft_2 = draft_service.create_draft(
                    "email", 
                    thread_2,
                    "message_2",
                    {"subject": "Thread 2 Draft"}
                )
                
                assert draft_1.thread_id == thread_1
                assert draft_2.thread_id == thread_2
                
                # Mock isolated draft retrieval
                def mock_get_drafts_side_effect(thread_id):
                    if thread_id == thread_1:
                        return [Mock(draft_id="draft_1", thread_id=thread_1)]
                    elif thread_id == thread_2:
                        return [Mock(draft_id="draft_2", thread_id=thread_2)]
                    else:
                        return []
                
                mock_get_drafts.side_effect = mock_get_drafts_side_effect
                
                # Test thread isolation
                thread_1_drafts = draft_service.get_active_drafts_by_thread(thread_1)
                thread_2_drafts = draft_service.get_active_drafts_by_thread(thread_2)
                
                assert len(thread_1_drafts) == 1
                assert len(thread_2_drafts) == 1
                assert thread_1_drafts[0].draft_id != thread_2_drafts[0].draft_id
                assert thread_1_drafts[0].thread_id == thread_1
                assert thread_2_drafts[0].thread_id == thread_2
    
    def test_anchored_draft_refresh_and_update_flow(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """
        INTEGRATION TEST: Anchored draft data refresh and update flow.
        
        Tests the complete flow of refreshing stale anchored data and updating.
        """
        thread_id = "anchored_refresh_thread_123"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Step 1: Frontend has stale anchored data
            stale_anchored_data = create_email_draft_fixture(
                draft_id="refresh_draft_123",
                body=None,  # Stale: no body
                status="active"
            )
            
            # Step 2: Database has fresh data
            fresh_database_data = create_email_draft_fixture(
                draft_id="refresh_draft_123",
                body="Fresh body content from database",
                status="active"
            )
            
            # Step 3: Simulate anchored draft refresh
            with patch.object(Draft, 'get_by_id') as mock_get:
                mock_draft = Mock()
                mock_draft.to_dict.return_value = fresh_database_data
                mock_get.return_value = mock_draft
                
                # Simulate the refresh logic from routing
                draft_id = stale_anchored_data["draft_id"]
                refreshed_draft = draft_service.get_draft_by_id(draft_id)
                refreshed_data = refreshed_draft.to_dict()
                
                # Verify fresh data was retrieved
                assert refreshed_data["body"] is not None
                assert refreshed_data["body"] == fresh_database_data["body"]
                assert refreshed_data["body"] != stale_anchored_data["body"]
            
            # Step 4: Use refreshed data for update intent detection
            with patch.object(draft_service, 'llm') as mock_llm:
                mock_response = Mock()
                mock_response.content = json.dumps(DRAFT_CREATION_INTENT_TRUE)
                mock_llm.invoke.return_value = mock_response
                
                update_intent = draft_service.detect_draft_intent(
                    "Add more content to this draft",
                    []  # Use conversation history
                )
                
                assert update_intent["is_draft_intent"] is True
                mock_llm.invoke.assert_called_once()
            
            # Step 5: Apply update to fresh data
            with patch.object(Draft, 'get_by_id') as mock_get:
                
                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.update = Mock(return_value=True)
                mock_get.return_value = mock_draft
                
                update_result = draft_service.update_draft(
                    draft_id,
                    {"body": "Fresh body content with additional updates"}
                )
                
                assert update_result is not None
                mock_draft.update.assert_called_once()


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftWorkflowEdgeCases:
    """Integration tests for draft workflow edge cases"""
    
    def test_concurrent_draft_updates(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """Test handling of concurrent draft updates"""
        thread_id = "concurrent_thread_123"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            draft_id = "concurrent_draft_123"
            
            # Simulate multiple updates to same draft
            with patch.object(Draft, 'get_by_id') as mock_get:
                
                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.draft_id = draft_id
                mock_draft.update = Mock(return_value=True)
                mock_get.return_value = mock_draft
                
                # Multiple rapid updates
                update_1 = draft_service.update_draft(draft_id, {"subject": "Update 1"})
                update_2 = draft_service.update_draft(draft_id, {"body": "Update 2"})
                update_3 = draft_service.update_draft(draft_id, {"subject": "Final Update"})
                
                assert all([update_1 is not None, update_2 is not None, update_3 is not None])
                assert mock_draft.update.call_count == 3
    
    def test_draft_creation_with_invalid_data(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """Test draft creation with various invalid data scenarios"""
        thread_id = "invalid_data_thread_123"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Test invalid draft type
            with pytest.raises(ValueError):
                draft_service.create_draft(
                    "invalid_type",
                    thread_id,
                    "message_123",
                    {}
                )
            
            # Test empty thread_id
            draft = draft_service.create_draft(
                "email",
                "",  # Empty thread_id
                "message_123",
                {}
            )
            assert draft is not None
            assert draft.thread_id == ""
            
            # Test None message_id
            draft = draft_service.create_draft(
                "email",
                thread_id,
                None,  # None message_id
                {}
            )
            assert draft is not None
            assert draft.message_id is None
    
    def test_draft_update_race_conditions(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """Test draft update race condition handling"""
        thread_id = "race_condition_thread_123"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            draft_id = "race_condition_draft_123"
            
            # Simulate race condition where draft is deleted during update
            with patch.object(Draft, 'get_by_id') as mock_get:

                # First call returns draft, second and third calls return None (draft deleted)
                mock_draft = Mock()
                mock_draft.status = "active"
                mock_draft.update = Mock(return_value=True)
                mock_get.side_effect = [mock_draft, None, None]

                # First update should succeed but return None due to second get_by_id returning None
                update_1 = draft_service.update_draft(draft_id, {"subject": "Update 1"})
                assert update_1 is None

                # Second update should raise ValueError as draft no longer exists
                with pytest.raises(ValueError):
                    draft_service.update_draft(draft_id, {"subject": "Update 2"})
    
    def test_large_draft_content_handling(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """Test handling of drafts with large content"""
        thread_id = "large_content_thread_123"
        conversation_cleanup(thread_id)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Create large content
            large_body = "This is a very long email body. " * 1000  # ~30KB
            large_subject = "A" * 500  # Long subject
            
            initial_data = {
                "subject": large_subject,
                "body": large_body,
                "to_contacts": ["test@example.com"]
            }
            
            with patch.object(Draft, 'save') as mock_save:
                mock_save.return_value = "large_draft_123"
                
                draft = draft_service.create_draft(
                    "email",
                    thread_id,
                    "large_message_123",
                    initial_data
                )
                
                assert draft is not None
                assert draft.subject == large_subject
                assert draft.body == large_body
                assert len(draft.body) > 10000  # Verify large content
                mock_save.assert_called_once()
    
    def test_draft_workflow_with_conversation_cleanup(
        self,
        test_db,
        clean_draft_collections,
        conversation_cleanup
    ):
        """Test complete draft workflow with proper conversation cleanup"""
        thread_id = "cleanup_workflow_thread_123"
        conversation_cleanup(thread_id)
        
        # Create conversation entries for this thread
        conversations_collection = get_collection('conversations')
        
        test_conversations = [
            {
                "thread_id": thread_id,
                "message_id": "test_msg_1",
                "role": "user",
                "content": "Create a draft email",
                "timestamp": int(time.time()),
                "created_at": int(time.time())
            },
            {
                "thread_id": thread_id,
                "message_id": "test_msg_2",
                "role": "assistant", 
                "content": "I'll create a draft for you",
                "timestamp": int(time.time()),
                "created_at": int(time.time())
            }
        ]
        
        conversations_collection.insert_many(test_conversations)
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Create and work with draft
            with patch.object(Draft, 'save') as mock_save:
                mock_save.return_value = "cleanup_draft_123"
                
                draft = draft_service.create_draft(
                    "email",
                    thread_id,
                    "cleanup_message_123",
                    {"subject": "Cleanup Test"}
                )
                
                assert draft is not None
                assert draft.thread_id == thread_id
                
            # Verify conversations exist
            found_conversations = list(conversations_collection.find({"thread_id": thread_id}))
            assert len(found_conversations) == 2
        
        # conversation_cleanup fixture will clean up automatically
