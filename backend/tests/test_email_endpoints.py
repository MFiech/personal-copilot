"""
ENDPOINT TESTS for Email Content and Summarization

These tests specifically target the /get_email_content and /summarize_single_email endpoints
to ensure they work correctly and handle all edge cases properly.
"""

import pytest
import json
import time
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.mongo_client import get_collection
from models.conversation import Conversation
from models.email import Email


class TestGetEmailContentEndpoint:
    """
    Tests for the /get_email_content endpoint.
    
    This endpoint:
    1. Retrieves email content from database if it exists
    2. Fetches content from Composio if not in database
    3. Processes HTML/text content and converts between formats
    4. Saves content back to database
    5. Returns content in both HTML and text formats
    """

    def test_get_email_content_success_new_email(self, test_db, clean_collections, mock_composio_service):
        """
        Test successful email content retrieval for a new email not in database.
        """
        # Mock the tooling service to return email content
        mock_composio_service.get_email_details.return_value = "This is a test email content"
        
        # Test data
        email_id = "test_email_123"
        
        # Create a minimal email document in the database first
        emails_collection = get_collection('emails')
        minimal_email = {
            'email_id': email_id,
            'thread_id': 'test_thread_123',
            'subject': 'Test Email Subject',
            'from_email': {'email': 'test@example.com', 'name': 'Test Sender'},
            'to_emails': [{'email': 'user@example.com', 'name': 'Test User'}],
            'date': '1640995200',
            'content': {'html': '', 'text': ''},  # Empty content to trigger fetching
            'updated_at': int(time.time())
        }
        emails_collection.insert_one(minimal_email)
        
        # Mock the tooling service in the app
        with patch('app.tooling_service', mock_composio_service):
            # Import app after mocking
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                assert response.status_code == 200
                data = response.get_json()
                
                assert data['success'] is True
                assert data['email_id'] == email_id
                assert 'content' in data
                assert 'html' in data['content']
                assert 'text' in data['content']
                
                # Verify content was processed correctly
                assert "This is a test email content" in data['content']['text']
                assert "<pre>This is a test email content</pre>" in data['content']['html']
                
                # Verify content was saved to database
                saved_email = emails_collection.find_one({'email_id': email_id})
                assert saved_email is not None
                assert saved_email['content']['text'] == "This is a test email content"

    def test_get_email_content_success_existing_email(self, test_db, clean_collections):
        """
        Test successful email content retrieval for an email already in database.
        """
        # Pre-populate database with email content
        emails_collection = get_collection('emails')
        email_id = "existing_email_123"
        
        existing_email = {
            'email_id': email_id,
            'thread_id': 'test_thread_123',
            'subject': 'Test Email Subject',
            'from_email': {'email': 'test@example.com', 'name': 'Test Sender'},
            'to_emails': [{'email': 'user@example.com', 'name': 'Test User'}],
            'date': '1640995200',
            'content': {
                'html': '<html><body><p>Existing HTML content</p></body></html>',
                'text': 'Existing text content'
            },
            'updated_at': int(time.time())
        }
        emails_collection.insert_one(existing_email)
        
        # Test the endpoint
        from app import app
        
        with app.test_client() as client:
            response = client.post('/get_email_content', 
                                json={'email_id': email_id})
            
            assert response.status_code == 200
            data = response.get_json()
            
            assert data['success'] is True
            assert data['email_id'] == email_id
            assert data['content']['html'] == '<html><body><p>Existing HTML content</p></body></html>'
            assert data['content']['text'] == 'Existing text content'

    def test_get_email_content_html_processing(self, test_db, clean_collections, mock_composio_service):
        """
        Test that HTML content is properly processed and converted to text.
        """
        # Mock HTML content from Composio
        html_content = """<html>
            <body>
                <h1>Test Email</h1>
                <p>This is a <strong>test</strong> email with <em>formatting</em>.</p>
                <ul>
                    <li>Item 1</li>
                    <li>Item 2</li>
                </ul>
            </body>
        </html>"""
        mock_composio_service.get_email_details.return_value = html_content
        
        email_id = "html_email_123"
        
        # Create a minimal email document in the database first
        emails_collection = get_collection('emails')
        minimal_email = {
            'email_id': email_id,
            'thread_id': 'test_thread_123',
            'subject': 'Test Email Subject',
            'from_email': {'email': 'test@example.com', 'name': 'Test Sender'},
            'to_emails': [{'email': 'user@example.com', 'name': 'Test User'}],
            'date': '1640995200',
            'content': {'html': '', 'text': ''},  # Empty content to trigger fetching
            'updated_at': int(time.time())
        }
        emails_collection.insert_one(minimal_email)
        
        with patch('app.tooling_service', mock_composio_service):
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                assert response.status_code == 200
                data = response.get_json()
                
                # Verify HTML content is preserved
                assert data['content']['html'] == html_content
                
                # Verify text content is extracted (html2text conversion)
                text_content = data['content']['text']
                assert "Test Email" in text_content
                assert "This is a **test** email with _formatting_" in text_content  # html2text converts to markdown
                assert "Item 1" in text_content
                assert "Item 2" in text_content

    def test_get_email_content_missing_email_id(self, test_db, clean_collections):
        """
        Test error handling when email_id is missing.
        """
        from app import app
        
        with app.test_client() as client:
            # Test with no email_id
            response = client.post('/get_email_content', json={})
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'Missing email_id parameter' in data['error']
            
            # Test with empty email_id
            response = client.post('/get_email_content', json={'email_id': ''})
            assert response.status_code == 400
            
            # Test with whitespace-only email_id
            response = client.post('/get_email_content', json={'email_id': '   '})
            assert response.status_code == 400

    def test_get_email_content_composio_failure(self, test_db, clean_collections, mock_composio_service):
        """
        Test handling when Composio service fails to retrieve email content.
        """
        # Mock Composio service failure
        mock_composio_service.get_email_details.return_value = None
        
        email_id = "failed_email_123"
        
        with patch('app.tooling_service', mock_composio_service):
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                assert response.status_code == 404
                data = response.get_json()
                assert 'error' in data
                assert 'Could not retrieve email content' in data['error']

    def test_get_email_content_fallback_to_existing(self, test_db, clean_collections, mock_composio_service):
        """
        Test fallback to existing database content when Composio fails.
        """
        # Pre-populate database with minimal content
        emails_collection = get_collection('emails')
        email_id = "fallback_email_123"
        
        existing_email = {
            'email_id': email_id,
            'thread_id': 'test_thread_123',
            'subject': 'Test Email Subject',
            'from_email': {'email': 'test@example.com', 'name': 'Test Sender'},
            'to_emails': [{'email': 'user@example.com', 'name': 'Test User'}],
            'date': '1640995200',
            'content': {
                'text': 'Existing text content that should be used as fallback'
            }
        }
        emails_collection.insert_one(existing_email)
        
        # Mock Composio service failure
        mock_composio_service.get_email_details.return_value = None
        
        with patch('app.tooling_service', mock_composio_service):
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                # Should fall back to existing content
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert data['content']['text'] == 'Existing text content that should be used as fallback'

    def test_get_email_content_tooling_service_unavailable(self, test_db, clean_collections):
        """
        Test handling when tooling service is not available.
        """
        email_id = "unavailable_service_email_123"
        
        # Mock tooling service as None
        with patch('app.tooling_service', None):
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                assert response.status_code == 500
                data = response.get_json()
                assert 'error' in data
                assert 'Tooling service not available' in data['error']

    def test_get_email_content_options_method(self, test_db, clean_collections):
        """
        Test OPTIONS method handling for CORS.
        """
        from app import app
        
        with app.test_client() as client:
            response = client.options('/get_email_content')
            assert response.status_code == 200

    def test_get_email_content_database_update_failure(self, test_db, clean_collections, mock_composio_service):
        """
        Test handling when database update fails but content is still returned.
        """
        # Mock successful content retrieval
        mock_composio_service.get_email_details.return_value = "Test content for database failure test"
        
        email_id = "db_failure_email_123"
        
        with patch('app.tooling_service', mock_composio_service):
            from app import app
            
            with app.test_client() as client:
                response = client.post('/get_email_content', 
                                    json={'email_id': email_id})
                
                # Should still return content even if DB update fails
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert 'Test content for database failure test' in data['content']['text']


class TestSummarizeSingleEmailEndpoint:
    """
    Tests for the /summarize_single_email endpoint.
    
    This endpoint:
    1. Validates required parameters
    2. Generates email summaries using LLM (Gemini or Claude)
    3. Creates conversation entries for summaries
    4. Handles rate limiting and errors gracefully
    """

    def test_summarize_single_email_success_gemini(self, test_db, clean_collections):
        """
        Test successful email summarization using Gemini LLM.
        """
        # Pre-populate conversation
        thread_id = "test_thread_123"
        assistant_message_id = "assistant_msg_456"
        
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Test conversation'
        )
        conversation.save()
        
        # Test data
        email_id = "summary_email_123"
        email_content = "This is a test email about a meeting tomorrow at 2 PM. Please bring your project updates."
        
        # Mock Gemini LLM
        mock_gemini_response = Mock()
        mock_gemini_response.content = ["Meeting scheduled for tomorrow at 2 PM. Action items: bring project updates."]
        
        with patch('app.gemini_llm') as mock_gemini, \
             patch('app.llm') as mock_default_llm:
            
            # Create a proper mock instance and set it directly
            mock_gemini_instance = Mock()
            mock_gemini_instance.invoke.return_value = mock_gemini_response
            mock_gemini.return_value = mock_gemini_instance
            
            # Also patch the module-level variable
            import app
            app.gemini_llm = mock_gemini_instance
            
            from app import app
            
            with app.test_client() as client:
                response = client.post('/summarize_single_email', 
                                    json={
                                        'email_id': email_id,
                                        'thread_id': thread_id,
                                        'assistant_message_id': assistant_message_id,
                                        'email_content_full': email_content,
                                        'email_content_truncated': email_content
                                    })
                
                assert response.status_code == 200
                data = response.get_json()
                
                assert data['success'] is True
                assert 'Meeting scheduled for tomorrow at 2 PM' in data['response']
                assert data['thread_id'] == thread_id
                assert 'message_id' in data
                assert 'tool_results' in data
                assert data['tool_results']['email_summary']['email_id'] == email_id
                
                # Verify summary was saved to conversation
                saved_summary = Conversation.find_one({'message_id': data['message_id']})
                assert saved_summary is not None
                assert saved_summary['role'] == 'assistant'  # MongoDB document is a dict
                assert 'Meeting scheduled' in saved_summary['content']

    def test_summarize_single_email_success_claude_fallback(self, test_db, clean_collections):
        """
        Test successful email summarization using Claude LLM when Gemini is unavailable.
        """
        # Pre-populate conversation
        thread_id = "test_thread_124"
        assistant_message_id = "assistant_msg_457"
        
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Test conversation'
        )
        conversation.save()
        
        # Test data
        email_id = "summary_email_124"
        email_content = "Project deadline extended to next Friday. Team meeting on Monday to discuss progress."
        
        # Mock Claude LLM (default)
        mock_claude_response = Mock()
        mock_claude_response.content = "Project deadline extended to next Friday. Team meeting scheduled for Monday to discuss progress."
        
        with patch('app.gemini_llm', None), \
             patch('app.llm') as mock_default_llm:
            
            # Mock the default LLM properly
            mock_default_llm.invoke.return_value = mock_claude_response

            # Also set the module-level variable

            import app
            app.gemini_llm = None
            
            from app import app
            
            with app.test_client() as client:
                response = client.post('/summarize_single_email', 
                                    json={
                                        'email_id': email_id,
                                        'thread_id': thread_id,
                                        'assistant_message_id': assistant_message_id,
                                        'email_content_full': email_content,
                                        'email_content_truncated': email_content
                                    })
                
                assert response.status_code == 200
                data = response.get_json()
                assert data['success'] is True
                assert 'Project deadline extended' in data['response']

    def test_summarize_single_email_missing_parameters(self, test_db, clean_collections):
        """
        Test error handling when required parameters are missing.
        """
        from app import app
        
        with app.test_client() as client:
            # Test with missing email_id
            response = client.post('/summarize_single_email', 
                                json={
                                    'thread_id': 'test_thread',
                                    'assistant_message_id': 'assistant_msg'
                                })
            assert response.status_code == 400
            data = response.get_json()
            assert 'error' in data
            assert 'Missing required parameters' in data['error']
            
            # Test with missing thread_id
            response = client.post('/summarize_single_email', 
                                json={
                                    'email_id': 'test_email',
                                    'assistant_message_id': 'assistant_msg'
                                })
            assert response.status_code == 400
            
            # Test with missing assistant_message_id
            response = client.post('/summarize_single_email', 
                                json={
                                    'email_id': 'test_email',
                                    'thread_id': 'test_thread'
                                })
            assert response.status_code == 400

    def test_summarize_single_email_rate_limit_handling(self, test_db, clean_collections):
        """
        Test handling of rate limit errors from LLM services.
        """
        # Pre-populate conversation
        thread_id = "test_thread_125"
        assistant_message_id = "assistant_msg_458"
        
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Test conversation'
        )
        conversation.save()
        
        # Test data
        email_id = "rate_limit_email_123"
        email_content = "Test email content for rate limit testing."
        
        # Mock rate limit error
        with patch('app.gemini_llm') as mock_gemini:
            # Create a mock instance that raises the rate limit error
            mock_gemini_instance = Mock()
            mock_gemini_instance.invoke.side_effect = Exception("rate_limit_error: Too many requests")
            mock_gemini.return_value = mock_gemini_instance
            
            # Also set the module-level variable
            import app
            app.gemini_llm = mock_gemini_instance
            
            from app import app
            
            with app.test_client() as client:
                response = client.post('/summarize_single_email', 
                                    json={
                                        'email_id': email_id,
                                        'thread_id': thread_id,
                                        'assistant_message_id': assistant_message_id,
                                        'email_content_full': email_content,
                                        'email_content_truncated': email_content
                                    })
                
                assert response.status_code == 429
                data = response.get_json()
                assert data['success'] is False
                assert 'rate limit' in data['error'].lower()

    def test_summarize_single_email_llm_failure(self, test_db, clean_collections):
        """
        Test handling when LLM service fails completely.
        """
        # Pre-populate conversation
        thread_id = "test_thread_126"
        assistant_message_id = "assistant_msg_459"
        
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Test conversation'
        )
        conversation.save()
        
        # Test data
        email_id = "llm_failure_email_123"
        email_content = "Test email content for LLM failure testing."
        
        # Mock LLM failure
        with patch('app.gemini_llm', None), \
             patch('app.llm') as mock_default_llm:
            
            mock_default_llm.invoke.side_effect = Exception("LLM service unavailable")
            
            from app import app
            
            with app.test_client() as client:
                response = client.post('/summarize_single_email', 
                                    json={
                                        'email_id': email_id,
                                        'thread_id': thread_id,
                                        'assistant_message_id': assistant_message_id,
                                        'email_content_full': email_content,
                                        'email_content_truncated': email_content
                                    })
                
                assert response.status_code == 500
                data = response.get_json()
                assert data['success'] is False
                assert 'Failed to generate summary' in data['error']

    def test_summarize_single_email_options_method(self, test_db, clean_collections):
        """
        Test OPTIONS method handling for CORS.
        """
        from app import app
        
        with app.test_client() as client:
            response = client.options('/summarize_single_email')
            assert response.status_code == 200

    def test_summarize_single_email_conversation_not_found(self, test_db, clean_collections):
        """
        Test handling when the referenced conversation is not found.
        """
        # Test data for non-existent conversation
        email_id = "no_conversation_email_123"
        thread_id = "non_existent_thread"
        assistant_message_id = "non_existent_message"
        email_content = "Test email content."
        
        from app import app
        
        with app.test_client() as client:
            response = client.post('/summarize_single_email', 
                                json={
                                    'email_id': email_id,
                                    'thread_id': thread_id,
                                    'assistant_message_id': assistant_message_id,
                                    'email_content_full': email_content,
                                    'email_content_truncated': email_content
                                })
            
            # Should still work even if conversation not found (creates new one)
            assert response.status_code == 200
            data = response.get_json()
            assert data['success'] is True


class TestEmailEndpointsIntegration:
    """
    Integration tests that test both endpoints working together.
    """

    def test_email_content_and_summarization_workflow(self, test_db, clean_collections, mock_composio_service):
        """
        Test the complete workflow: get email content, then summarize it.
        """
        # Mock email content retrieval
        email_content = """
        Subject: Project Update Meeting
        
        Hi Team,
        
        We have a project update meeting scheduled for tomorrow at 3 PM.
        Please prepare your progress reports and bring any blockers you're facing.
        
        Agenda:
        1. Review current progress
        2. Discuss blockers and solutions
        3. Plan next week's tasks
        
        Best regards,
        Project Manager
        """
        
        mock_composio_service.get_email_details.return_value = email_content
        
        email_id = "workflow_email_123"
        thread_id = "workflow_thread_456"
        assistant_message_id = "workflow_assistant_789"
        
        # Create a minimal email document in the database first
        emails_collection = get_collection('emails')
        minimal_email = {
            'email_id': email_id,
            'thread_id': thread_id,
            'subject': 'Project Update Meeting',
            'from_email': {'email': 'manager@example.com', 'name': 'Project Manager'},
            'to_emails': [{'email': 'team@example.com', 'name': 'Team'}],
            'date': '1640995200',
            'content': {'html': '', 'text': ''},  # Empty content to trigger fetching
            'updated_at': int(time.time())
        }
        emails_collection.insert_one(minimal_email)
        
        # Create conversation
        conversation = Conversation(
            thread_id=thread_id,
            role='assistant',
            content='Test conversation'
        )
        conversation.save()
        
        with patch('app.tooling_service', mock_composio_service), \
             patch('app.gemini_llm') as mock_gemini:
            
            # Mock Gemini response
            mock_gemini_response = Mock()
            mock_gemini_response.content = ["Project update meeting tomorrow at 3 PM. Team needs to prepare progress reports and identify blockers."]
            
            # Create a proper mock instance
            mock_gemini_instance = Mock()
            mock_gemini_instance.invoke.return_value = mock_gemini_response
            mock_gemini.return_value = mock_gemini_instance
            
            # Also set the module-level variable
            import app
            app.gemini_llm = mock_gemini_instance
            
            from app import app
            
            with app.test_client() as client:
                # Step 1: Get email content
                content_response = client.post('/get_email_content', 
                                            json={'email_id': email_id})
                
                assert content_response.status_code == 200
                content_data = content_response.get_json()
                assert content_data['success'] is True
                assert 'Project Update Meeting' in content_data['content']['text']
                
                # Step 2: Summarize the email
                summary_response = client.post('/summarize_single_email', 
                                            json={
                                                'email_id': email_id,
                                                'thread_id': thread_id,
                                                'assistant_message_id': assistant_message_id,
                                                'email_content_full': content_data['content']['text'],
                                                'email_content_truncated': content_data['content']['text']
                                            })
                
                assert summary_response.status_code == 200
                summary_data = summary_response.get_json()
                assert summary_data['success'] is True
                assert 'Project update meeting tomorrow at 3 PM' in summary_data['response']
                
                # Verify both operations were successful
                emails_collection = get_collection('emails')
                saved_email = emails_collection.find_one({'email_id': email_id})
                assert saved_email is not None
                assert 'Project Update Meeting' in saved_email['content']['text']
                
                saved_summary = Conversation.find_one({'message_id': summary_data['message_id']})
                assert saved_summary is not None
                assert 'Project update meeting' in saved_summary['content']  # MongoDB document is a dict
