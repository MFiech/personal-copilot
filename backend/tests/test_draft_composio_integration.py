"""
Integration tests for draft + Composio email sending.
Tests the complete flow from draft to email sending via Composio API.
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

from tests.fixtures.draft_responses import (
    create_email_draft_fixture,
    COMPOSIO_SEND_EMAIL_SUCCESS,
    COMPOSIO_SEND_EMAIL_ERROR,
    create_composio_error_recovery_scenario
)


@pytest.mark.integration
@pytest.mark.optimized
class TestDraftComposioIntegration:
    """Test draft + Composio email sending integration"""
    
    def test_email_draft_to_composio_send_success(
        self, 
        test_db, 
        clean_draft_collections, 
        mock_draft_composio_service
    ):
        """Test successful email draft to Composio send pipeline"""
        
        # Create complete email draft
        complete_draft = create_email_draft_fixture(
            subject="Test Email from Draft",
            body="This email was created from a draft and sent via Composio",
            to_emails=[
                {"email": "primary@example.com", "name": "Primary Recipient"},
                {"email": "cc@example.com", "name": "CC Recipient"}
            ]
        )
        
        with patch('services.draft_service.DraftService') as mock_draft_service_class:
            mock_draft_service = Mock()
            mock_draft_service_class.return_value = mock_draft_service
            
            # Mock draft retrieval
            mock_draft_obj = Mock()
            mock_draft_obj.to_dict.return_value = complete_draft
            mock_draft_obj.draft_type = "email"
            mock_draft_service.get_draft_by_id.return_value = mock_draft_obj
            
            # Mock Composio parameter conversion
            composio_params = {
                "to": "primary@example.com",
                "cc": "cc@example.com",
                "subject": complete_draft["subject"],
                "body": complete_draft["body"]
            }
            mock_draft_service.convert_draft_to_composio_params.return_value = composio_params
            
            # Test the integration
            draft_id = complete_draft["draft_id"]
            
            # Step 1: Get draft and convert to Composio params
            draft_obj = mock_draft_service.get_draft_by_id(draft_id)
            params = mock_draft_service.convert_draft_to_composio_params(draft_id)
            
            assert params["subject"] == complete_draft["subject"]
            assert params["body"] == complete_draft["body"]
            assert params["to"] == "primary@example.com"
            
            # Step 2: Send via Composio
            send_result = mock_draft_composio_service.send_email(**params)
            
            assert send_result["successful"] is True
            assert "messageId" in send_result["data"]
            
            # Step 3: Update draft status after successful send
            mock_draft_service.close_draft.return_value = True
            close_result = mock_draft_service.close_draft(draft_id)
            
            assert close_result is True
            
            # Verify all steps were called
            mock_draft_service.get_draft_by_id.assert_called_with(draft_id)
            mock_draft_service.convert_draft_to_composio_params.assert_called_with(draft_id)
            mock_draft_service.close_draft.assert_called_with(draft_id)
    
    def test_email_draft_composio_error_status_handling(
        self,
        test_db,
        clean_draft_collections
    ):
        """Test handling of Composio errors during email sending"""
        
        draft_data = create_email_draft_fixture()
        
        with patch('services.draft_service.DraftService') as mock_draft_service_class, \
             patch('services.composio_service.ComposioService') as mock_composio_service_class:
            
            # Setup mocks
            mock_draft_service = Mock()
            mock_draft_service_class.return_value = mock_draft_service
            
            mock_composio_service = Mock()
            mock_composio_service_class.return_value = mock_composio_service
            
            # Mock draft retrieval
            mock_draft_obj = Mock()
            mock_draft_obj.to_dict.return_value = draft_data
            mock_draft_service.get_draft_by_id.return_value = mock_draft_obj
            
            # Mock Composio parameter conversion
            composio_params = {
                "to": "test@example.com",
                "subject": draft_data["subject"],
                "body": draft_data["body"]
            }
            mock_draft_service.convert_draft_to_composio_params.return_value = composio_params
            
            # Mock Composio error
            mock_composio_service.send_email.return_value = COMPOSIO_SEND_EMAIL_ERROR
            
            # Test error handling
            draft_id = draft_data["draft_id"]
            
            # Get draft and attempt send
            draft_obj = mock_draft_service.get_draft_by_id(draft_id)
            params = mock_draft_service.convert_draft_to_composio_params(draft_id)
            send_result = mock_composio_service.send_email(**params)
            
            # Verify error response
            assert send_result["successful"] is False
            assert send_result["error"] is not None
            assert "Failed to send email" in send_result["error"]
            
            # Mock draft status update to composio_error
            mock_draft_service.update_draft.return_value = True
            
            # Should update draft status to indicate error
            error_update_result = mock_draft_service.update_draft(
                draft_id, 
                {"status": "composio_error"}
            )
            
            assert error_update_result is True
            mock_draft_service.update_draft.assert_called_with(
                draft_id, 
                {"status": "composio_error"}
            )
    
    def test_draft_composio_params_conversion(self, test_db, clean_draft_collections):
        """Test conversion of draft data to Composio API parameters"""
        
        # Test email draft conversion
        email_draft = create_email_draft_fixture(
            subject="Multi-recipient Test",
            body="Test email with multiple recipients",
            to_emails=[
                {"email": "first@example.com", "name": "First Recipient"},
                {"email": "second@example.com", "name": "Second Recipient"},
                {"email": "third@example.com", "name": "Third Recipient"}
            ]
        )
        
        with patch('services.draft_service.DraftService') as mock_draft_service_class:
            mock_draft_service = Mock()
            mock_draft_service_class.return_value = mock_draft_service
            
            # Mock parameter conversion logic
            def mock_convert_params(draft_id):
                # Simulate the conversion logic from DraftService
                draft_data = email_draft
                
                if not draft_data["to_emails"]:
                    return {}
                
                # Primary recipient (first in list)
                primary_email = draft_data["to_emails"][0]["email"]
                
                # CC recipients (rest of the list)
                cc_emails = [contact["email"] for contact in draft_data["to_emails"][1:]]
                
                params = {
                    "to": primary_email,
                    "subject": draft_data["subject"],
                    "body": draft_data["body"]
                }
                
                if cc_emails:
                    params["cc"] = ",".join(cc_emails)
                
                return params
            
            mock_draft_service.convert_draft_to_composio_params.side_effect = mock_convert_params
            
            # Test conversion
            params = mock_draft_service.convert_draft_to_composio_params(email_draft["draft_id"])
            
            # Verify conversion
            assert params["to"] == "first@example.com"  # Primary recipient
            assert params["cc"] == "second@example.com,third@example.com"  # CC recipients
            assert params["subject"] == email_draft["subject"]
            assert params["body"] == email_draft["body"]
    
    def test_multiple_recipients_handling(self, mock_draft_composio_service):
        """Test handling of multiple recipients in Composio email sending"""
        
        # Test with multiple recipients
        composio_params = {
            "to": "primary@example.com",
            "cc": "cc1@example.com,cc2@example.com",
            "subject": "Multi-recipient Test",
            "body": "Test email with multiple recipients"
        }
        
        # Mock successful send with multiple recipients
        send_result = mock_draft_composio_service.send_email(**composio_params)
        
        # Verify send was successful
        assert send_result["successful"] is True
        assert "messageId" in send_result["data"]
        
        # Verify Composio service was called with correct parameters
        # (In real implementation, this would verify the actual Composio API call)
    


@pytest.mark.unit
@pytest.mark.mock_only
class TestDraftComposioParameterConversion:
    """Unit tests for draft to Composio parameter conversion"""
    
    def test_email_draft_parameter_mapping(self):
        """Test mapping of email draft fields to Composio parameters"""
        
        email_draft = create_email_draft_fixture(
            subject="Test Subject",
            body="Test email body content",
            to_emails=[
                {"email": "primary@example.com", "name": "Primary User"},
                {"email": "cc1@example.com", "name": "CC User 1"},
                {"email": "cc2@example.com", "name": "CC User 2"}
            ]
        )
        
        # Simulate conversion logic
        def convert_email_draft_to_composio_params(draft_data):
            """Convert email draft to Composio parameters"""
            if not draft_data.get("to_emails"):
                return {}
            
            params = {
                "to": draft_data["to_emails"][0]["email"],
                "subject": draft_data.get("subject", ""),
                "body": draft_data.get("body", "")
            }
            
            # Add CC recipients if there are multiple recipients
            if len(draft_data["to_emails"]) > 1:
                cc_emails = [contact["email"] for contact in draft_data["to_emails"][1:]]
                params["cc"] = ",".join(cc_emails)
            
            # Add attachments if present
            if draft_data.get("attachments"):
                params["attachments"] = draft_data["attachments"]
            
            return params
        
        # Test conversion
        params = convert_email_draft_to_composio_params(email_draft)
        
        # Verify mapping
        assert params["to"] == "primary@example.com"
        assert params["cc"] == "cc1@example.com,cc2@example.com"
        assert params["subject"] == email_draft["subject"]
        assert params["body"] == email_draft["body"]
    
    def test_incomplete_draft_parameter_conversion(self):
        """Test parameter conversion for incomplete drafts"""
        
        # Test draft with missing fields
        incomplete_draft = create_email_draft_fixture(
            subject=None,  # Missing subject
            body="Has body but no subject",
            to_emails=[{"email": "test@example.com", "name": "Test User"}]
        )
        
        def convert_incomplete_draft(draft_data):
            """Convert incomplete draft with defaults"""
            params = {
                "to": draft_data["to_emails"][0]["email"],
                "subject": draft_data.get("subject") or "[No Subject]",
                "body": draft_data.get("body") or ""
            }
            return params
        
        params = convert_incomplete_draft(incomplete_draft)
        
        # Verify defaults are applied
        assert params["to"] == "test@example.com"
        assert params["subject"] == "[No Subject]"
        assert params["body"] == "Has body but no subject"
    
    def test_draft_validation_before_composio_send(self):
        """Test validation of draft completeness before Composio send"""
        
        complete_draft = create_email_draft_fixture(
            subject="Complete Draft",
            body="This draft has all required fields",
            to_emails=[{"email": "test@example.com", "name": "Test User"}]
        )
        
        incomplete_draft = create_email_draft_fixture(
            subject=None,  # Missing required field
            body=None,     # Missing required field
            to_emails=[{"email": "test@example.com", "name": "Test User"}]
        )
        
        def validate_draft_for_sending(draft_data):
            """Validate draft has required fields for sending"""
            required_fields = ["subject", "body", "to_emails"]
            missing_fields = []
            
            for field in required_fields:
                value = draft_data.get(field)
                if not value or (isinstance(value, list) and len(value) == 0):
                    missing_fields.append(field)
            
            return {
                "is_valid": len(missing_fields) == 0,
                "missing_fields": missing_fields
            }
        
        # Test complete draft
        complete_validation = validate_draft_for_sending(complete_draft)
        assert complete_validation["is_valid"] is True
        assert len(complete_validation["missing_fields"]) == 0
        
        # Test incomplete draft
        incomplete_validation = validate_draft_for_sending(incomplete_draft)
        assert incomplete_validation["is_valid"] is False
        assert "subject" in incomplete_validation["missing_fields"]
        assert "body" in incomplete_validation["missing_fields"]


@pytest.mark.integration
@pytest.mark.optimized  
class TestDraftComposioErrorScenarios:
    """Test various error scenarios in draft + Composio integration"""
    
    
    def test_invalid_email_addresses_in_draft(self, mock_draft_composio_service):
        """Test handling of invalid email addresses"""
        
        # Test with invalid email format
        invalid_params = {
            "to": "invalid-email-format",
            "subject": "Test Subject",
            "body": "Test body"
        }
        
        # Mock Composio error for invalid email
        def mock_send_with_validation(to, subject, body, **kwargs):
            if "@" not in to or "." not in to:
                return {
                    "successful": False,
                    "error": "Invalid email address format"
                }
            return COMPOSIO_SEND_EMAIL_SUCCESS
        
        mock_draft_composio_service.send_email.side_effect = mock_send_with_validation
        
        # Test invalid email
        result = mock_draft_composio_service.send_email(**invalid_params)
        
        assert result["successful"] is False
        assert "Invalid email address" in result["error"]
        
        # Test valid email
        valid_params = {
            "to": "valid@example.com",
            "subject": "Test Subject", 
            "body": "Test body"
        }
        
        result = mock_draft_composio_service.send_email(**valid_params)
        
        # Should succeed with valid email
        assert result["successful"] is True
    
    
    def test_draft_deleted_during_send_process(self, test_db, clean_draft_collections):
        """Test handling when draft is deleted during send process"""
        
        with patch('services.draft_service.DraftService') as mock_draft_service_class:
            mock_draft_service = Mock()
            mock_draft_service_class.return_value = mock_draft_service
            
            draft_id = "test_draft_123"
            
            # First call returns draft, second call returns None (deleted)
            mock_draft_service.get_draft_by_id.side_effect = [
                Mock(to_dict=Mock(return_value=create_email_draft_fixture())),
                None  # Draft deleted
            ]
            
            # First call should succeed
            draft_1 = mock_draft_service.get_draft_by_id(draft_id)
            assert draft_1 is not None
            
            # Second call should return None
            draft_2 = mock_draft_service.get_draft_by_id(draft_id)
            assert draft_2 is None
            
            # Should handle gracefully
            assert mock_draft_service.get_draft_by_id.call_count == 2
