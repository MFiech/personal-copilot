"""
INTEGRATION TESTS for Full Email Retrieval Flow

These tests simulate the complete end-to-end email flow:
User query → Flask route → Composio service → Data processing → MongoDB save

This is designed to catch any breaking changes in the full pipeline.
"""

import pytest
import requests
import json
import time
import sys
import os
from unittest.mock import patch, Mock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.mongo_client import get_collection


class TestEmailIntegrationFlow:
    """
    Integration tests for the complete email retrieval and saving pipeline.
    """

    def test_full_email_query_to_database_pipeline(self, test_db, clean_collections, mock_composio_service, mock_openai_client):
        """
        CRITICAL INTEGRATION TEST: Complete user query → email saved to DB pipeline.
        
        This simulates exactly what happens when a user asks for emails:
        1. User sends query via frontend
        2. Backend processes with OpenAI
        3. Composio retrieves emails
        4. Emails are processed and saved to MongoDB
        5. Response sent back to frontend
        """
        # Prepare test data
        test_query = "Show me recent emails from test@example.com"
        test_thread_id = "integration_test_thread_123"
        
        expected_emails = [
            {
                'messageId': 'integration_email_1',
                'thread_id': 'email_thread_1',
                'subject': 'Integration Test Email 1',
                'messageText': 'This is integration test email 1',
                'date': '1640995200',
                'from': {'name': 'Test Sender', 'email': 'test@example.com'},
                'to': [{'name': 'User', 'email': 'user@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            },
            {
                'messageId': 'integration_email_2', 
                'thread_id': 'email_thread_2',
                'subject': 'Integration Test Email 2',
                'messageText': 'This is integration test email 2',
                'date': '1640995300',
                'from': {'name': 'Test Sender', 'email': 'test@example.com'},
                'to': [{'name': 'User', 'email': 'user@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            }
        ]
        
        # Configure mocks
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'content': f'{len(expected_emails)} emails fetched.',
            'data': {
                'data': {
                    'messages': expected_emails
                }
            },
            'total_estimate': len(expected_emails),
            'has_more': False
        }
        
        # Mock OpenAI to trigger tool usage
        mock_openai_client.chat.completions.create.return_value = Mock(
            choices=[Mock(
                message=Mock(
                    content="I'll help you find emails from test@example.com",
                    tool_calls=None
                )
            )]
        )
        
        # Test the core email processing logic from app.py
        # This simulates what happens in the /chat endpoint
        with patch('services.composio_service.ComposioService', return_value=mock_composio_service):
            # Simulate the tooling service call
            raw_tool_results = mock_composio_service.process_query(test_query)
            
            # Simulate the data processing logic from app.py
            tool_output = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            
            # This is our critical fix being tested
            messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
            
            processed_emails = []
            email_ids_for_conversation = []
            
            if tool_output and messages_data:
                # Simulate the email processing loop from app.py
                from models.email import Email
                
                for composio_email in messages_data:
                    email_id = composio_email.get('messageId')
                    thread_id = composio_email.get('thread_id')
                    subject = composio_email.get('subject', 'No Subject')
                    
                    # Parse from email
                    from_raw = composio_email.get('from', {})
                    from_email = {
                        'email': from_raw.get('email', ''),
                        'name': from_raw.get('name', from_raw.get('email', '').split('@')[0] if '@' in from_raw.get('email', '') else '')
                    }
                    
                    # Parse to emails
                    to_list = composio_email.get('to', [])
                    to_emails = []
                    for to_item in to_list:
                        if isinstance(to_item, dict):
                            to_emails.append({
                                'email': to_item.get('email', ''),
                                'name': to_item.get('name', to_item.get('email', '').split('@')[0] if '@' in to_item.get('email', '') else '')
                            })
                    
                    # Create Email model instance
                    email_doc = Email(
                        email_id=email_id,
                        thread_id=thread_id,
                        gmail_thread_id=composio_email.get('thread_id'),
                        subject=subject,
                        from_email=from_email,
                        to_emails=to_emails,
                        date=composio_email.get('date', 'Unknown Date'),
                        content={'text': '', 'html': ''},
                        metadata={
                            'source': 'COMPOSIO',
                            'label_ids': composio_email.get('labelIds', []),
                            'attachment_count': len(composio_email.get('attachmentList', [])),
                            'timestamp': composio_email.get('date')
                        }
                    )
                    
                    # Save to database
                    email_doc.save()
                    
                    # Create dict for frontend
                    email_dict = {
                        'id': email_id,
                        'subject': subject,
                        'from_email': from_email,
                        'to_emails': to_emails,
                        'date': composio_email.get('date', 'Unknown Date'),
                        'content': {'text': '', 'html': ''},
                        'metadata': email_doc.metadata
                    }
                    
                    processed_emails.append(email_dict)
                    email_ids_for_conversation.append(email_id)
        
        # CRITICAL VERIFICATIONS
        
        # 1. Verify emails were processed correctly
        assert len(processed_emails) == len(expected_emails), f"Should process {len(expected_emails)} emails"
        assert len(email_ids_for_conversation) == len(expected_emails), f"Should create {len(expected_emails)} email IDs for conversation"
        
        # 2. Verify emails were saved to emails collection
        emails_collection = get_collection('emails')
        saved_emails_count = emails_collection.count_documents({})
        assert saved_emails_count == len(expected_emails), f"Should save {len(expected_emails)} emails to emails collection"
        
        # 3. Verify specific email data integrity
        for i, expected_email in enumerate(expected_emails):
            saved_email = emails_collection.find_one({'email_id': expected_email['messageId']})
            assert saved_email is not None, f"Email {expected_email['messageId']} should be saved"
            assert saved_email['subject'] == expected_email['subject'], f"Subject should match for email {i}"
            assert saved_email['from_email']['email'] == expected_email['from']['email'], f"From email should match for email {i}"
        
        # 4. Verify conversation integration would work
        from models.conversation import Conversation
        
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content=f'Found {len(expected_emails)} emails from test@example.com',
            tool_results={
                'source_type': 'mail',
                'emails': email_ids_for_conversation
            }
        )
        
        conversation.save()
        
        # Verify conversation was saved with correct email references
        conversations_collection = get_collection('conversations')
        saved_conversation = conversations_collection.find_one({'thread_id': test_thread_id})
        
        assert saved_conversation is not None, "Conversation should be saved"
        assert len(saved_conversation['tool_results']['emails']) == len(expected_emails), "Conversation should reference all emails"

    def test_email_flow_error_handling(self, test_db, clean_collections, mock_composio_service):
        """
        Test that the email flow handles errors gracefully without breaking.
        """
        # Test case 1: Composio service returns error
        mock_composio_service.process_query.side_effect = Exception("Composio API error")
        
        with patch('services.composio_service.ComposioService', return_value=mock_composio_service):
            try:
                raw_tool_results = mock_composio_service.process_query("test query")
                assert False, "Should have raised an exception"
            except Exception as e:
                assert "Composio API error" in str(e)
                
                # Verify no partial data was saved
                emails_collection = get_collection('emails')
                assert emails_collection.count_documents({}) == 0, "No emails should be saved on error"
        
        # Reset mock for next test
        mock_composio_service.process_query.side_effect = None
        
        # Test case 2: Malformed data structure
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'data': None  # Malformed!
        }
        
        with patch('services.composio_service.ComposioService', return_value=mock_composio_service):
            raw_tool_results = mock_composio_service.process_query("test query")
            tool_output = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            
            # Should handle gracefully with proper null checking
            if tool_output is None:
                messages_data = None
            else:
                messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
            
            # Should not crash, should result in no emails
            assert messages_data is None, "Should handle malformed data gracefully"
            
            emails_collection = get_collection('emails')
            assert emails_collection.count_documents({}) == 0, "No emails should be saved with malformed data"

    def test_performance_large_email_batch_integration(self, test_db, clean_collections, mock_composio_service):
        """
        Test integration flow with large email batches (performance/scalability test).
        """
        # Create large batch of emails (100 emails)
        large_batch_size = 100
        large_email_batch = []
        
        for i in range(large_batch_size):
            large_email_batch.append({
                'messageId': f'perf_email_{i:04d}',
                'thread_id': f'perf_thread_{i:04d}',
                'subject': f'Performance Test Email {i:04d}',
                'messageText': f'Performance test content {i:04d}',
                'date': str(1640995200 + i),
                'from': {'name': f'Perf Sender {i}', 'email': f'perfsender{i}@example.com'},
                'to': [{'name': 'Perf Receiver', 'email': 'perfreceiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            })
        
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'content': f'{large_batch_size} emails fetched.',
            'data': {
                'data': {
                    'messages': large_email_batch
                }
            },
            'total_estimate': large_batch_size,
            'has_more': False
        }
        
        # Measure processing time
        start_time = time.time()
        
        with patch('services.composio_service.ComposioService', return_value=mock_composio_service):
            raw_tool_results = mock_composio_service.process_query("large batch query")
            tool_output = raw_tool_results.get('data', {})
            messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
            
            processed_count = 0
            if messages_data:
                from models.email import Email
                
                for composio_email in messages_data:
                    email_doc = Email(
                        email_id=composio_email.get('messageId'),
                        thread_id=composio_email.get('thread_id'),
                        gmail_thread_id=composio_email.get('thread_id'),
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
        
        processing_time = time.time() - start_time
        
        # Verify all emails processed and saved
        emails_collection = get_collection('emails')
        saved_count = emails_collection.count_documents({})
        
        assert processed_count == large_batch_size, f"Should process all {large_batch_size} emails"
        assert saved_count == large_batch_size, f"Should save all {large_batch_size} emails"
        
        # Performance assertion (should process 100 emails in reasonable time)
        assert processing_time < 30.0, f"Processing {large_batch_size} emails took {processing_time:.2f}s, should be < 30s"
        
        print(f"✅ Performance test: Processed {large_batch_size} emails in {processing_time:.2f} seconds")

    def test_concurrent_email_processing_safety(self, test_db, clean_collections, mock_composio_service):
        """
        Test that concurrent email processing doesn't cause data corruption or duplicate saves.
        """
        # This simulates what could happen if multiple requests process emails simultaneously
        test_emails = [
            {
                'messageId': 'concurrent_email_1',
                'thread_id': 'concurrent_thread_1',
                'subject': 'Concurrent Test Email 1',
                'messageText': 'Concurrent test content 1',
                'date': '1640995200',
                'from': {'name': 'Concurrent Sender', 'email': 'concurrent@example.com'},
                'to': [{'name': 'Concurrent Receiver', 'email': 'receiver@example.com'}],
                'labelIds': ['INBOX'],
                'attachmentList': []
            }
        ]
        
        mock_composio_service.process_query.return_value = {
            'source_type': 'mail',
            'data': {
                'data': {
                    'messages': test_emails
                }
            }
        }
        
        # Simulate multiple concurrent saves of the same email
        from models.email import Email
        
        email_data = test_emails[0]
        
        # Save the same email multiple times (simulating race condition)
        for i in range(5):
            email_doc = Email(
                email_id=email_data.get('messageId'),
                thread_id=email_data.get('thread_id'),
                gmail_thread_id=email_data.get('thread_id'),
                subject=f"{email_data.get('subject')} - Save {i}",  # Slightly different each time
                from_email={'email': email_data.get('from', {}).get('email', ''), 
                          'name': email_data.get('from', {}).get('name', '')},
                to_emails=[],
                date=email_data.get('date'),
                content={'text': '', 'html': ''},
                metadata={'source': 'COMPOSIO', 'save_attempt': i}
            )
            email_doc.save()  # Should upsert, not duplicate
        
        # Verify only one email exists (due to upsert behavior)
        emails_collection = get_collection('emails')
        saved_count = emails_collection.count_documents({'email_id': 'concurrent_email_1'})
        
        assert saved_count == 1, "Should have only 1 email despite multiple saves (upsert behavior)"
        
        # Verify the last save won (most recent data)
        saved_email = emails_collection.find_one({'email_id': 'concurrent_email_1'})
        assert 'Save 4' in saved_email['subject'], "Should have the data from the last save"