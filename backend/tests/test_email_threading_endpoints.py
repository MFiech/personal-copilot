"""
API ENDPOINT TESTS for Email Threading Feature

These tests specifically target the new thread-related API endpoints:
- GET /emails/threads - Get grouped threads
- GET /emails/thread/<gmail_thread_id> - Get specific thread
- GET /emails/thread/<gmail_thread_id>/full - Get full thread with content

Tests cover:
- Successful endpoint responses
- Error handling
- Content processing
- Chronological ordering
- Performance requirements
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment before importing app
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from utils.mongo_client import get_collection
from models.email import Email


def mock_lazy_services():
    """Helper function to mock all lazy-initialized services."""
    return patch.multiple('app',
        get_pinecone_client=Mock(return_value=None),
        get_pinecone_index=Mock(return_value=None),
        get_embeddings=Mock(return_value=None),
        get_vectorstore=Mock(return_value=None),
        get_llm=Mock(return_value=None),
        get_gemini_llm=Mock(return_value=None),
        get_qa_chain=Mock(return_value=None)
    )


@pytest.fixture
def sample_thread_data():
    """Sample thread data for endpoint testing"""
    return [
        {
            'email_id': 'endpoint_email_001',
            'thread_id': 'conversation_thread_endpoint_123',
            'gmail_thread_id': 'endpoint_thread_123',
            'subject': 'API Test Thread',
            'from_email': {'name': 'Test User', 'email': 'test@example.com'},
            'to_emails': [{'name': 'Recipient', 'email': 'recipient@example.com'}],
            'date': '2024-01-15T10:00:00Z',
            'content': {
                'html': '<p>Test HTML content</p>',
                'text': 'Test HTML content'
            },
            'created_at': 1705312800,
            'updated_at': 1705312800
        },
        {
            'email_id': 'endpoint_email_002',
            'thread_id': 'conversation_thread_endpoint_123',
            'gmail_thread_id': 'endpoint_thread_123',
            'subject': 'Re: API Test Thread',
            'from_email': {'name': 'Recipient', 'email': 'recipient@example.com'},
            'to_emails': [{'name': 'Test User', 'email': 'test@example.com'}],
            'date': '2024-01-15T12:00:00Z',
            'content': {
                'html': '<p>Reply content</p>',
                'text': 'Reply content'
            },
            'created_at': 1705320000,
            'updated_at': 1705320000
        }
    ]


@pytest.fixture
def mock_tooling_service():
    """Mock tooling service for content fetching"""
    with patch('app.tooling_service') as mock_service:
        mock_service.get_email_details.return_value = "Mocked email content from Composio"
        yield mock_service


class TestEmailThreadsEndpoint:
    """Tests for GET /emails/threads endpoint"""
    
    def test_get_email_threads_success(self, test_db, clean_collections, sample_thread_data):
        """Test successful retrieval of grouped threads"""
        emails_collection = get_collection('emails')
        
        # Insert test data
        for email in sample_thread_data:
            emails_collection.insert_one(email.copy())
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/threads')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert 'data' in data
                assert 'gmail_threads' in data['data']
                assert 'individual_emails' in data['data']
                
                # Verify thread data
                threads = data['data']['gmail_threads']
                assert len(threads) == 1
                assert threads[0]['_id'] == 'endpoint_thread_123'
                assert threads[0]['email_count'] == 2
    
    def test_get_email_threads_with_limit(self, test_db, clean_collections, sample_thread_data):
        """Test threads endpoint with limit parameter"""
        emails_collection = get_collection('emails')
        
        # Create multiple threads
        for i in range(3):
            for j, email in enumerate(sample_thread_data):
                thread_email = email.copy()
                thread_email['gmail_thread_id'] = f'endpoint_thread_{i}'
                thread_email['email_id'] = f'endpoint_email_{i}_{j}'
                emails_collection.insert_one(thread_email)
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/threads?limit=2')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                # Should return only 2 threads due to limit
                assert len(data['data']['gmail_threads']) == 2
    
    def test_get_email_threads_empty_database(self, test_db, clean_collections):
        """Test threads endpoint with empty database"""
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/threads')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert len(data['data']['gmail_threads']) == 0
                assert len(data['data']['individual_emails']) == 0
    
    def test_get_email_threads_invalid_limit(self, test_db, clean_collections):
        """Test threads endpoint with invalid limit parameter"""
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/threads?limit=invalid')
                
                # Should handle gracefully and use default limit
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True


class TestEmailThreadByIdEndpoint:
    """Tests for GET /emails/thread/<gmail_thread_id> endpoint"""
    
    def test_get_thread_by_id_success(self, test_db, clean_collections, sample_thread_data):
        """Test successful retrieval of specific thread"""
        emails_collection = get_collection('emails')
        
        # Insert test data
        for email in sample_thread_data:
            emails_collection.insert_one(email.copy())
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/endpoint_thread_123')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert 'data' in data
                assert data['data']['gmail_thread_id'] == 'endpoint_thread_123'
                assert data['data']['email_count'] == 2
                
                # Verify emails are in chronological order
                emails = data['data']['emails']
                assert len(emails) == 2
                assert emails[0]['email_id'] == 'endpoint_email_001'  # Older
                assert emails[1]['email_id'] == 'endpoint_email_002'  # Newer
    
    def test_get_thread_by_id_not_found(self, test_db, clean_collections):
        """Test thread endpoint with non-existent thread ID"""
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/non_existent_thread')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                
                assert data['success'] is False
                assert 'error' in data
    
    def test_get_thread_by_id_empty_thread(self, test_db, clean_collections):
        """Test thread endpoint with empty thread"""
        emails_collection = get_collection('emails')
        
        # Insert email with different thread ID
        email = {
            'email_id': 'other_email',
            'thread_id': 'conversation_thread_other',
            'gmail_thread_id': 'other_thread',
            'subject': 'Other Thread',
            'from_email': {'email': 'other@example.com'},
            'to_emails': [],
            'date': '2024-01-15T10:00:00Z',
            'content': {'html': '', 'text': ''}
        }
        emails_collection.insert_one(email)
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/empty_thread')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert data['success'] is False


class TestEmailThreadFullEndpoint:
    """Tests for GET /emails/thread/<gmail_thread_id>/full endpoint"""
    
    def test_get_full_thread_success(self, test_db, clean_collections, sample_thread_data, mock_tooling_service):
        """Test successful retrieval of full thread with content"""
        emails_collection = get_collection('emails')
        
        # Insert test data
        for email in sample_thread_data:
            emails_collection.insert_one(email.copy())
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/endpoint_thread_123/full')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                assert data['success'] is True
                assert 'data' in data
                assert data['data']['gmail_thread_id'] == 'endpoint_thread_123'
                assert data['data']['email_count'] == 2
                
                # Verify emails have processed content
                emails = data['data']['emails']
                assert len(emails) == 2
                
                for email in emails:
                    assert 'content' in email
                    assert 'html' in email['content']
                    assert 'text' in email['content']
    
    def test_get_full_thread_content_processing(self, test_db, clean_collections, mock_tooling_service):
        """Test content processing in full thread endpoint"""
        emails_collection = get_collection('emails')
        
        # Insert email with HTML content
        html_email = {
            'email_id': 'html_test_email',
            'thread_id': 'conversation_thread_html_test',
            'gmail_thread_id': 'html_test_thread',
            'subject': 'HTML Test',
            'from_email': {'email': 'test@example.com'},
            'to_emails': [],
            'date': '2024-01-15T10:00:00Z',
            'content': {
                'html': '<p>This is <strong>HTML</strong> content</p>',
                'text': 'This is HTML content'
            }
        }
        emails_collection.insert_one(html_email)
        
        # Mock tooling service to return HTML content
        mock_tooling_service.get_email_details.return_value = '<p>This is <strong>HTML</strong> content</p>'
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/html_test_thread/full')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                email = data['data']['emails'][0]
                content = email['content']
                
                # Verify HTML and text are properly separated
                assert '<p>' in content['html']
                assert '<strong>' in content['html']
                assert '<p>' not in content['text']
                assert '<strong>' not in content['text']
    
    def test_get_full_thread_chronological_ordering(self, test_db, clean_collections, sample_thread_data, mock_tooling_service):
        """Test that full thread endpoint returns emails in chronological order"""
        emails_collection = get_collection('emails')
        
        # Insert emails in reverse chronological order
        for email in reversed(sample_thread_data):
            emails_collection.insert_one(email.copy())
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/endpoint_thread_123/full')
                
                assert response.status_code == 200
                data = json.loads(response.data)
                
                emails = data['data']['emails']
                
                # Verify chronological ordering (oldest first)
                assert emails[0]['email_id'] == 'endpoint_email_001'
                assert emails[1]['email_id'] == 'endpoint_email_002'
                
                # Verify dates are in ascending order
                dates = [email['date'] for email in emails]
                assert dates == sorted(dates)
    
    def test_get_full_thread_not_found(self, test_db, clean_collections):
        """Test full thread endpoint with non-existent thread"""
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/non_existent_thread/full')
                
                assert response.status_code == 404
                data = json.loads(response.data)
                assert data['success'] is False
    
    def test_get_full_thread_content_fetch_failure(self, test_db, clean_collections, sample_thread_data):
        """Test full thread endpoint when content fetching fails"""
        emails_collection = get_collection('emails')
        
        # Insert test data
        for email in sample_thread_data:
            emails_collection.insert_one(email.copy())
        
        # Mock tooling service to fail
        with patch('app.tooling_service') as mock_service:
            mock_service.get_email_details.return_value = None
            
            with mock_lazy_services():
                from app import app
                
                with app.test_client() as client:
                    response = client.get('/emails/thread/endpoint_thread_123/full')
                    
                    # Should still succeed but with fallback content
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True
                    
                    # Verify fallback content is used
                    emails = data['data']['emails']
                    for email in emails:
                        assert 'content' in email
                        assert 'html' in email['content']
                        assert 'text' in email['content']
    
    def test_get_full_thread_no_tooling_service(self, test_db, clean_collections, sample_thread_data):
        """Test full thread endpoint when tooling service is not available"""
        emails_collection = get_collection('emails')
        
        # Insert test data
        for email in sample_thread_data:
            emails_collection.insert_one(email.copy())
        
        # Mock no tooling service
        with patch('app.tooling_service', None):
            with mock_lazy_services():
                from app import app
                
                with app.test_client() as client:
                    response = client.get('/emails/thread/endpoint_thread_123/full')
                    
                    # Should still succeed with existing content
                    assert response.status_code == 200
                    data = json.loads(response.data)
                    assert data['success'] is True


class TestThreadEndpointErrorHandling:
    """Tests for error handling in thread endpoints"""
    
    def test_thread_endpoints_database_error(self):
        """Test thread endpoints when database is unavailable"""
        with patch('models.email.get_collection') as mock_collection:
            mock_collection.side_effect = Exception("Database connection failed")
            
            with mock_lazy_services():
                from app import app
                
                with app.test_client() as client:
                    # Test all thread endpoints
                    endpoints = [
                        '/emails/threads',
                        '/emails/thread/test_thread',
                        '/emails/thread/test_thread/full'
                    ]
                    
                    for endpoint in endpoints:
                        response = client.get(endpoint)
                        assert response.status_code == 500
                        data = json.loads(response.data)
                        assert data['success'] is False
                        assert 'error' in data
    
    def test_thread_endpoints_malformed_data(self, test_db, clean_collections):
        """Test thread endpoints with malformed email data"""
        emails_collection = get_collection('emails')
        
        # Insert malformed email data (with valid required fields)
        malformed_email = {
            'email_id': 'malformed_email',
            'thread_id': 'conversation_thread_malformed',
            'gmail_thread_id': 'malformed_thread',
            'subject': 'Test Subject',  # Required field
            'from_email': {'email': 'test@example.com'},  # Required field
            'to_emails': [],  # Required field
            'date': '2024-01-15T10:00:00Z',  # Required field
            'content': {'html': '', 'text': ''}  # Required field
        }
        emails_collection.insert_one(malformed_email)
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                response = client.get('/emails/thread/malformed_thread')
                
                # Should handle gracefully
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert len(data['data']['emails']) == 1


class TestThreadEndpointPerformance:
    """Performance tests for thread endpoints"""
    
    def test_threads_endpoint_performance(self, test_db, clean_collections):
        """Test performance of threads endpoint with multiple threads"""
        emails_collection = get_collection('emails')
        
        # Create 10 threads with 3 emails each
        for thread_num in range(10):
            for email_num in range(3):
                email = {
                    'email_id': f'perf_email_{thread_num}_{email_num}',
                    'thread_id': f'conversation_thread_perf_{thread_num}',
                    'gmail_thread_id': f'perf_thread_{thread_num}',
                    'subject': f'Thread {thread_num} Email {email_num}',
                    'from_email': {'email': f'user{thread_num}@example.com'},
                    'to_emails': [],
                    'date': f'2024-01-15T{10+thread_num}:{email_num*20:02d}:00Z',
                    'content': {'html': '', 'text': ''}
                }
                emails_collection.insert_one(email)
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                import time
                start_time = time.time()
                response = client.get('/emails/threads')
                end_time = time.time()
                
                assert response.status_code == 200
                assert end_time - start_time < 2.0  # Should complete within 2 seconds
                
                data = json.loads(response.data)
                assert len(data['data']['gmail_threads']) == 10
    
    def test_full_thread_endpoint_performance(self, test_db, clean_collections, mock_tooling_service):
        """Test performance of full thread endpoint with maximum emails (8)"""
        emails_collection = get_collection('emails')
        
        # Create thread with 8 emails (max allowed)
        for i in range(8):
            email = {
                'email_id': f'perf_full_email_{i}',
                'thread_id': 'conversation_thread_perf_full',
                'gmail_thread_id': 'perf_full_thread',
                'subject': f'Email {i+1}',
                'from_email': {'email': f'user{i}@example.com'},
                'to_emails': [],
                'date': f'2024-01-15T{10+i}:00:00Z',
                'content': {'html': f'<p>Content {i+1}</p>', 'text': f'Content {i+1}'}
            }
            emails_collection.insert_one(email)
        
        with mock_lazy_services():
            from app import app
            
            with app.test_client() as client:
                import time
                start_time = time.time()
                response = client.get('/emails/thread/perf_full_thread/full')
                end_time = time.time()
                
                assert response.status_code == 200
                assert end_time - start_time < 3.0  # Should complete within 3 seconds
                
                data = json.loads(response.data)
                assert data['data']['email_count'] == 8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
