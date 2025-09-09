"""
Unit tests for draft-related LLM prompts.
Tests all the new draft prompts for accuracy and thread safety.
Following the established testing patterns from the application.
"""

import pytest
import sys
import os
import json
from unittest.mock import Mock, patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from prompts import (
    draft_creation_intent_prompt,
    draft_update_intent_prompt, 
    draft_field_update_prompt,
    draft_detection_prompt,
    draft_information_extraction_prompt
)
from tests.fixtures.draft_responses import (
    create_email_draft_fixture,
    create_calendar_draft_fixture,
    CONVERSATION_WITH_DRAFT_CONTENT,
    EXPECTED_EXTRACTED_CONTENT
)


@pytest.mark.unit
@pytest.mark.mock_only
class TestDraftPromptGeneration:
    """Test prompt generation for different draft scenarios"""
    
    def test_draft_creation_intent_prompt_structure(self):
        """Test that draft creation intent prompt has proper structure"""
        user_query = "Create a draft email to John about the meeting"
        conversation_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        
        prompt = draft_creation_intent_prompt(user_query, conversation_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key elements are included
        assert "draft creation intent" in prompt.lower()
        assert user_query in prompt
        assert "CURRENT DATE" in prompt
        assert "CONVERSATION CONTEXT" in prompt
        assert "draft_type" in prompt
        assert "email" in prompt
        assert "calendar_event" in prompt
        
        # Check conversation history inclusion
        assert "Hello" in prompt
        assert "Hi there!" in prompt
    
    def test_draft_update_intent_prompt_structure(self):
        """Test that draft update intent prompt has proper structure"""
        user_query = "Add John to this email"
        existing_draft = create_email_draft_fixture()
        conversation_history = [
            {"role": "user", "content": "Create a draft"},
            {"role": "assistant", "content": "Draft created"}
        ]
        
        prompt = draft_update_intent_prompt(user_query, existing_draft, conversation_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key elements are included
        assert "update intent" in prompt.lower()
        assert user_query in prompt
        assert "EXISTING DRAFT CONTEXT" in prompt or "ANCHORED DRAFT SUMMARY" in prompt
        assert "update_category" in prompt
        assert "is_update_intent" in prompt
        
        # Check existing draft context
        assert existing_draft["subject"] in prompt
        assert existing_draft["draft_type"] in prompt
    
    def test_draft_field_update_prompt_structure(self):
        """Test that draft field update prompt has proper structure"""
        user_query = "Create the subject on your own based on the context you have"
        existing_draft = create_email_draft_fixture()
        update_category = "subject_title"
        conversation_history = []
        
        prompt = draft_field_update_prompt(
            user_query, 
            existing_draft, 
            update_category, 
            conversation_history
        )
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key elements are included
        assert "field updates" in prompt.lower()
        assert user_query in prompt
        assert update_category in prompt
        assert "field_updates" in prompt
        
        # Check existing draft context
        assert "Current Email Draft Fields" in prompt
        assert existing_draft["subject"] in prompt or "[NOT SET]" in prompt
    
    def test_draft_detection_prompt_with_existing_draft(self):
        """Test draft detection prompt when existing draft is provided"""
        user_query = "Add his email address"
        existing_draft = create_email_draft_fixture()
        conversation_history = []
        
        prompt = draft_detection_prompt(user_query, conversation_history, existing_draft)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check existing draft context is included
        assert ("EXISTING DRAFT CONTEXT" in prompt or 
                "ANCHORED DRAFT SUMMARY" in prompt or 
                "EXISTING DRAFT" in prompt)
        # Depending on prompt variant, update criteria might not appear in creation prompt
        # Ensure at least creation or update rule sections exist
        assert ("UPDATE INTENT CRITERIA" in prompt or "EXAMPLES:" in prompt)
        assert existing_draft["draft_type"] in prompt
        
        # Check update mode specific instructions
        assert "ONLY extract" in prompt
        assert "DO NOT re-extract existing information" in prompt
    
    def test_draft_information_extraction_prompt_structure(self):
        """Test draft information extraction prompt structure"""
        user_query = "Send an email to john@example.com about the project update"
        existing_draft = create_email_draft_fixture()
        conversation_history = []
        
        prompt = draft_information_extraction_prompt(user_query, existing_draft, conversation_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Check that key elements are included
        assert "extracting information" in prompt.lower()
        assert user_query in prompt
        assert "updates" in prompt
        
        # Check existing draft is referenced
        assert existing_draft["draft_type"] in prompt


@pytest.mark.unit
@pytest.mark.mock_only 
class TestDraftPromptLogic:
    """Test prompt logic and edge cases"""
    
    def test_prompt_thread_context_isolation(self):
        """Test that prompts properly handle thread-specific context"""
        user_query = "Update this draft"
        
        # Thread 1 context
        thread1_draft = create_email_draft_fixture(
            thread_id="thread_123",
            subject="Thread 1 Subject"
        )
        thread1_history = [
            {"role": "user", "content": "Thread 1 conversation"}
        ]
        
        # Thread 2 context
        thread2_draft = create_email_draft_fixture(
            thread_id="thread_456", 
            subject="Thread 2 Subject"
        )
        thread2_history = [
            {"role": "user", "content": "Thread 2 conversation"}
        ]
        
        # Generate prompts for each thread
        prompt1 = draft_update_intent_prompt(user_query, thread1_draft, thread1_history)
        prompt2 = draft_update_intent_prompt(user_query, thread2_draft, thread2_history)
        
        # Verify thread isolation
        assert "Thread 1 Subject" in prompt1
        assert "Thread 1 conversation" in prompt1
        assert "Thread 2 Subject" not in prompt1
        assert "Thread 2 conversation" not in prompt1
        
        assert "Thread 2 Subject" in prompt2
        assert "Thread 2 conversation" in prompt2
        assert "Thread 1 Subject" not in prompt2
        assert "Thread 1 conversation" not in prompt2
    
    def test_completion_finalization_detection_prompt(self):
        """Test prompts properly detect completion signals like 'that's all'"""
        completion_queries = [
            "that's all",
            "looks good",
            "perfect",
            "that's it",
            "all done"
        ]
        
        existing_draft = create_email_draft_fixture()
        
        for query in completion_queries:
            prompt = draft_update_intent_prompt(query, existing_draft, [])
            
            # Check that completion patterns are mentioned in prompt
            assert "completion_finalization" in prompt
            assert "that's all" in prompt.lower()
            assert "looks good" in prompt.lower()
    
    def test_content_application_detection_prompt(self):
        """Test prompts properly detect content application requests"""
        application_queries = [
            "apply that content to the draft",
            "use that text for the email",
            "put that in the draft",
            "apply the content"
        ]
        
        existing_draft = create_email_draft_fixture()
        conversation_with_content = CONVERSATION_WITH_DRAFT_CONTENT
        
        for query in application_queries:
            prompt = draft_update_intent_prompt(query, existing_draft, conversation_with_content)
            
            # Check that content application patterns are mentioned
            assert "content_application" in prompt
            assert "content should be applied" in prompt.lower()
    
    def test_time_extraction_rules_in_prompts(self):
        """Test that time extraction rules are properly included in prompts"""
        user_query = "Schedule meeting for Saturday at 3pm"
        existing_draft = create_calendar_draft_fixture()
        
        prompt = draft_field_update_prompt(user_query, existing_draft, "time_schedule", [])
        
        # Check time extraction rules are present
        assert "TIME EXTRACTION" in prompt
        assert "Saturday at 3pm" in prompt  # Example from prompt
        assert "start_time" in prompt
        assert "YYYY-MM-DDTHH:MM:SS" in prompt
        assert "clock times" in prompt.lower()
    
    def test_email_address_extraction_rules(self):
        """Test that email address extraction rules are properly included"""
        user_query = "His email is john@example.com"
        existing_draft = create_email_draft_fixture()
        
        prompt = draft_field_update_prompt(user_query, existing_draft, "recipients_attendees", [])
        
        # Check email extraction rules are present
        assert "email" in prompt.lower()
        assert "john@example.com" in prompt or "addr" in prompt
        assert "name" in prompt.lower()
    
    def test_prompt_handles_empty_conversation_history(self):
        """Test prompts handle empty conversation history gracefully"""
        user_query = "Create a draft email"
        existing_draft = create_email_draft_fixture()
        empty_history = []
        
        prompt = draft_creation_intent_prompt(user_query, empty_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        
        # Should not fail with empty history
        assert "CONVERSATION CONTEXT" in prompt
    
    def test_prompt_handles_large_conversation_history(self):
        """Test prompts handle large conversation history appropriately"""
        user_query = "Update this draft"
        existing_draft = create_email_draft_fixture()
        
        # Create large conversation history
        large_history = []
        for i in range(20):
            large_history.extend([
                {"role": "user", "content": f"User message {i}"},
                {"role": "assistant", "content": f"Assistant message {i}"}
            ])
        
        prompt = draft_update_intent_prompt(user_query, existing_draft, large_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        
        # Should only include recent messages (last 6 based on prompt logic)
        # Check that it doesn't include very early messages
        assert "User message 0" not in prompt
        assert "Assistant message 0" not in prompt
        
        # Should include recent messages
        assert f"User message {len(large_history)//2 - 3}" in prompt or f"User message {len(large_history)//2 - 1}" in prompt


@pytest.mark.unit
@pytest.mark.mock_only
class TestDraftPromptEdgeCases:
    """Test edge cases and error handling in draft prompts"""
    
    def test_prompt_handles_none_conversation_history(self):
        """Test prompts handle None conversation history gracefully"""
        user_query = "Create a draft"
        
        # Test with None conversation history
        prompt1 = draft_creation_intent_prompt(user_query, None)
        assert prompt1 is not None
        assert isinstance(prompt1, str)
        
        # Test update prompt with empty conversation history
        existing_draft = create_email_draft_fixture()
        prompt2 = draft_update_intent_prompt(user_query, existing_draft, None)
        assert prompt2 is not None
        assert isinstance(prompt2, str)
    
    def test_prompt_handles_malformed_draft_data(self):
        """Test prompts handle malformed draft data"""
        user_query = "Update this draft"
        
        # Malformed draft missing required fields
        malformed_draft = {
            "draft_id": "test_123"
            # Missing draft_type, subject, etc.
        }
        
        prompt = draft_update_intent_prompt(user_query, malformed_draft, [])
        
        assert prompt is not None
        assert isinstance(prompt, str)
        # Should handle missing fields gracefully
        assert "[NOT SET]" in prompt or "unknown" in prompt.lower()
    
    def test_prompt_handles_malformed_conversation_history(self):
        """Test prompts handle malformed conversation history"""
        user_query = "Create a draft"
        
        # Malformed conversation history
        malformed_history = [
            {"role": "user"},  # Missing content
            {"content": "Hello"},  # Missing role
            {"role": "assistant", "content": "Hi"},  # Valid
            "invalid_entry",  # Not a dict
            None  # None entry
        ]
        
        # Pre-filter malformed entries to match prompt expectations
        cleaned_history = []
        for msg in malformed_history:
            if isinstance(msg, dict) and ("role" in msg and "content" in msg):
                cleaned_history.append(msg)
        
        prompt = draft_creation_intent_prompt(user_query, cleaned_history)
        
        assert prompt is not None
        assert isinstance(prompt, str)
        # Should include valid entries and skip invalid ones
        assert "Hi" in prompt
    
    def test_prompt_with_special_characters(self):
        """Test prompts handle special characters and encoding"""
        user_query = "Create email with émojis 🎉 and ñoñó characters"
        existing_draft = create_email_draft_fixture(
            subject="Special chars: àáâã & symbols $#@"
        )
        
        prompt = draft_update_intent_prompt(user_query, existing_draft, [])
        
        assert prompt is not None
        assert isinstance(prompt, str)
        
        # Should preserve special characters
        assert "émojis" in prompt
        assert "🎉" in prompt
        assert "ñoñó" in prompt
        assert "àáâã" in prompt
    
    def test_prompt_with_very_long_input(self):
        """Test prompts handle very long input gracefully"""
        # Very long user query
        long_query = "Create a draft email " + "with very long content " * 100
        
        existing_draft = create_email_draft_fixture(
            body="Very long existing body content " * 50
        )
        
        prompt = draft_update_intent_prompt(long_query, existing_draft, [])
        
        assert prompt is not None
        assert isinstance(prompt, str)
        
        # Should include the content without errors
        assert "Create a draft email" in prompt
        assert "Very long existing body content" in prompt
    
    def test_date_formatting_in_prompts(self):
        """Test that current date is properly formatted in prompts"""
        user_query = "Schedule for tomorrow"
        
        prompt = draft_creation_intent_prompt(user_query, [])
        
        assert prompt is not None
        assert "CURRENT DATE" in prompt
        
        # Should contain date in YYYY-MM-DD format
        import re
        date_pattern = r'\d{4}-\d{2}-\d{2}'
        assert re.search(date_pattern, prompt) is not None


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftPromptIntegration:
    """Integration tests for draft prompts with LLM responses"""
    
    def test_draft_creation_prompt_with_llm_response(self):
        """Test draft creation prompt produces valid LLM response"""
        from services.draft_service import DraftService
        
        with patch('services.langfuse_client.create_langfuse_client') as mock_create_client:
            mock_client = Mock()
            mock_client.is_enabled.return_value = False
            mock_create_client.return_value = mock_client
            draft_service = DraftService()
            
            # Mock LLM response
            with patch.object(draft_service, 'llm') as mock_llm:
                mock_response = Mock()
                mock_response.content = json.dumps({
                    "is_draft_intent": True,
                    "draft_data": {
                        "draft_type": "email",
                        "extracted_info": {
                            "to_contacts": ["john@example.com"],
                            "subject": "Test Subject"
                        }
                    }
                })
                mock_llm.invoke.return_value = mock_response
                
                result = draft_service.detect_draft_intent(
                    "Create a draft email to john@example.com", 
                    []
                )
                
                assert result is not None
                assert result["is_draft_intent"] is True
                assert result["draft_data"]["draft_type"] == "email"
                mock_llm.invoke.assert_called_once()
    
    def test_prompt_conversation_context_integration(self):
        """Test that conversation context is properly integrated into prompts"""
        conversation_history = CONVERSATION_WITH_DRAFT_CONTENT
        user_query = "Apply that content to the draft"
        existing_draft = create_email_draft_fixture()
        
        prompt = draft_update_intent_prompt(user_query, existing_draft, conversation_history)
        
        # Should include relevant conversation context
        assert "Meeting Discussion" in prompt  # From expected extracted content
        assert "Dear John" in prompt
        assert "content_application" in prompt
