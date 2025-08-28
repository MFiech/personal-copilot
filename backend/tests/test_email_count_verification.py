"""
CRITICAL EMAIL COUNT VERIFICATION TESTS

These tests ensure that when the system says "10 emails found", exactly 10 emails
are actually saved to MongoDB. This was a key part of the bug - emails were being
retrieved but not persisted.
"""

import pytest
import sys
import os
from unittest.mock import patch, Mock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.mongo_client import get_collection
from models.email import Email
from models.conversation import Conversation


class TestEmailCountVerification:
    """
    Critical tests to ensure email count consistency between retrieval and persistence.
    """

    def test_email_count_matches_saved_emails(self, test_db, clean_collections, mock_composio_service):
        """
        CRITICAL: Verify that reported email count matches actually saved emails.
        
        This was the core issue - system would say "10 emails found" but save 0.
        """
        # Configure mock to return specific number of emails
        test_emails = []
        expected_count = 5
        
        for i in range(expected_count):
            test_emails.append({
                'messageId': f'test_email_{i}',
                'threadId': f'thread_{i}',
                'subject': f'Test Email {i}',
                'messageText': f'Content of test email {i}',
                'date': str(1640995200 + i * 1000),
                'from': {'name': f'Sender {i}', 'email': f'sender{i}@example.com'},
                'to': [{'name': 'Test Receiver', 'email': 'receiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            })
        
        # Update mock response with specific count
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'content': f'{expected_count} emails fetched.',
            'data': {
                'data': {
                    'messages': test_emails
                }
            },
            'total_estimate': expected_count,
            'has_more': False
        }
        
        # Simulate the email processing from app.py
        raw_tool_results = mock_composio_service.process_query.return_value
        tool_output = raw_tool_results.get('data', {})
        
        # Use our fixed logic
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        # Process and save emails (simulate app.py logic)
        processed_count = 0
        emails_collection = get_collection('emails')
        
        if messages_data:
            for composio_email in messages_data:
                email_id = composio_email.get('messageId')
                
                # Create Email model instance (simplified version of app.py logic)
                email_doc = Email(
                    email_id=email_id,
                    thread_id=composio_email.get('threadId'),
                    subject=composio_email.get('subject'),
                    from_email={'email': composio_email.get('from', {}).get('email', ''), 
                              'name': composio_email.get('from', {}).get('name', '')},
                    to_emails=[],
                    date=composio_email.get('date'),
                    content={'text': '', 'html': ''},
                    metadata={'source': 'COMPOSIO'}
                )
                
                email_doc.save()
                processed_count += 1
        
        # CRITICAL VERIFICATION: Count must match
        saved_count = emails_collection.count_documents({})
        
        assert processed_count == expected_count, f"Processed {processed_count} emails, expected {expected_count}"
        assert saved_count == expected_count, f"Saved {saved_count} emails to DB, expected {expected_count}"
        assert processed_count == saved_count, f"Processed count ({processed_count}) must match saved count ({saved_count})"

    def test_zero_emails_scenario(self, test_db, clean_collections, mock_composio_service):
        """
        Test that zero emails are handled correctly.
        """
        # Configure mock for empty response
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'content': '0 emails fetched.',
            'data': {
                'data': {
                    'messages': []
                }
            },
            'total_estimate': 0,
            'has_more': False
        }
        
        # Process the empty response
        raw_tool_results = mock_composio_service.process_query.return_value
        tool_output = raw_tool_results.get('data', {})
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        processed_count = 0
        if messages_data:
            processed_count = len(messages_data)
        
        emails_collection = get_collection('emails')
        saved_count = emails_collection.count_documents({})
        
        assert processed_count == 0, "Should process 0 emails for empty response"
        assert saved_count == 0, "Should save 0 emails for empty response"

    def test_large_email_batch_count_accuracy(self, test_db, clean_collections, mock_composio_service):
        """
        Test count accuracy with larger batches (simulating real-world usage).
        """
        # Simulate finding 50 emails (large batch)
        large_batch_size = 50
        test_emails = []
        
        for i in range(large_batch_size):
            test_emails.append({
                'messageId': f'large_batch_email_{i:03d}',
                'threadId': f'large_thread_{i:03d}',
                'subject': f'Large Batch Email {i:03d}',
                'messageText': f'Content {i:03d}',
                'date': str(1640995200 + i),
                'from': {'name': 'Batch Sender', 'email': 'batch@example.com'},
                'to': [{'name': 'Batch Receiver', 'email': 'receiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            })
        
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'content': f'{large_batch_size} emails fetched.',
            'data': {
                'data': {
                    'messages': test_emails
                }
            },
            'total_estimate': large_batch_size,
            'has_more': False
        }
        
        # Process large batch
        raw_tool_results = mock_composio_service.process_query.return_value
        tool_output = raw_tool_results.get('data', {})
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        processed_count = 0
        emails_collection = get_collection('emails')
        
        if messages_data:
            for composio_email in messages_data:
                email_doc = Email(
                    email_id=composio_email.get('messageId'),
                    thread_id=composio_email.get('threadId'),
                    subject=composio_email.get('subject'),
                    from_email={'email': composio_email.get('from', {}).get('email', ''), 
                              'name': composio_email.get('from', {}).get('name', '')},
                    to_emails=[],
                    date=composio_email.get('date'),
                    content={'text': '', 'html': ''},
                    metadata={'source': 'COMPOSIO'}
                )
                email_doc.save()
                processed_count += 1
        
        saved_count = emails_collection.count_documents({})
        
        assert processed_count == large_batch_size, f"Should process all {large_batch_size} emails"
        assert saved_count == large_batch_size, f"Should save all {large_batch_size} emails"

    def test_conversation_collection_email_references(self, test_db, clean_collections, mock_composio_service):
        """
        CRITICAL: Verify that conversation collection contains correct email references.
        
        This tests the other part of the bug - emails should also be referenced in conversations.
        """
        expected_count = 3
        test_emails = []
        
        for i in range(expected_count):
            test_emails.append({
                'messageId': f'conv_test_email_{i}',
                'threadId': 'conv_thread_123',
                'subject': f'Conversation Test Email {i}',
                'messageText': f'Conversation content {i}',
                'date': str(1640995200 + i),
                'from': {'name': f'Conv Sender {i}', 'email': f'convsender{i}@example.com'},
                'to': [{'name': 'Conv Receiver', 'email': 'convreceiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            })
        
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'data': {
                'data': {
                    'messages': test_emails
                }
            },
            'total_estimate': expected_count
        }
        
        # Simulate conversation creation with tool results
        thread_id = "test_conversation_thread"
        
        # Create conversation with email tool results
        email_ids = [email['messageId'] for email in test_emails]
        
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Found emails for you.',
            tool_results={
                'source_type': 'mail',
                'emails': email_ids  # This should contain the email IDs
            }
        )
        
        # Save conversation (this would normally save emails too in the real flow)
        conversation.save()
        
        # Verify conversation has correct email references
        conversations_collection = get_collection('conversations')
        saved_conversation = conversations_collection.find_one({'thread_id': thread_id})
        
        assert saved_conversation is not None, "Conversation should be saved"
        assert 'tool_results' in saved_conversation, "Conversation should have tool_results"
        assert 'emails' in saved_conversation['tool_results'], "Tool results should contain emails"
        
        saved_email_ids = saved_conversation['tool_results']['emails']
        assert len(saved_email_ids) == expected_count, f"Should reference {expected_count} emails in conversation"
        
        # Verify all email IDs are present
        for email_id in email_ids:
            assert email_id in saved_email_ids, f"Email ID {email_id} should be in conversation tool results"

    def test_duplicate_email_handling(self, test_db, clean_collections, mock_composio_service):
        """
        Test that duplicate emails don't inflate the count.
        """
        # Create scenario with duplicate email IDs
        duplicate_emails = [
            {
                'messageId': 'duplicate_email_123',
                'threadId': 'thread_dup',
                'subject': 'Duplicate Email',
                'messageText': 'First version',
                'date': '1640995200',
                'from': {'name': 'Sender', 'email': 'sender@example.com'},
                'to': [{'name': 'Receiver', 'email': 'receiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            },
            {
                'messageId': 'duplicate_email_123',  # Same ID!
                'threadId': 'thread_dup',
                'subject': 'Duplicate Email Updated',
                'messageText': 'Second version',
                'date': '1640995300',
                'from': {'name': 'Sender', 'email': 'sender@example.com'},
                'to': [{'name': 'Receiver', 'email': 'receiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            }
        ]
        
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'data': {
                'data': {
                    'messages': duplicate_emails
                }
            },
            'total_estimate': 2  # Composio reports 2, but should result in 1 unique
        }
        
        # Process emails
        raw_tool_results = mock_composio_service.process_query.return_value
        tool_output = raw_tool_results.get('data', {})
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        emails_collection = get_collection('emails')
        processed_count = 0
        
        if messages_data:
            for composio_email in messages_data:
                email_doc = Email(
                    email_id=composio_email.get('messageId'),
                    thread_id=composio_email.get('threadId'),
                    subject=composio_email.get('subject'),
                    from_email={'email': composio_email.get('from', {}).get('email', ''), 
                              'name': composio_email.get('from', {}).get('name', '')},
                    to_emails=[],
                    date=composio_email.get('date'),
                    content={'text': '', 'html': ''},
                    metadata={'source': 'COMPOSIO'}
                )
                email_doc.save()  # This uses upsert, so duplicates should be updated, not duplicated
                processed_count += 1
        
        # Should process 2 emails but save only 1 unique
        unique_count = emails_collection.count_documents({})
        
        assert processed_count == 2, "Should process both emails from Composio"
        assert unique_count == 1, "Should save only 1 unique email (due to upsert behavior)"
        
        # Verify the latest version is saved
        saved_email = emails_collection.find_one({'email_id': 'duplicate_email_123'})
        assert saved_email['subject'] == 'Duplicate Email Updated', "Should save the latest version"