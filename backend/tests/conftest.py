"""
Pytest configuration and fixtures for PM Co-Pilot backend tests.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
import tempfile
import shutil

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.mongo_client import get_db, get_collection
from models.email import Email
from models.conversation import Conversation


@pytest.fixture(scope="session")
def test_db_name():
    """Generate unique test database name"""
    return f"pm_copilot_test_{os.getpid()}"


@pytest.fixture
def test_db(test_db_name):
    """Provide isolated test database"""
    # Set test database name in environment
    original_db_name = os.environ.get('MONGO_DB_NAME')
    os.environ['MONGO_DB_NAME'] = test_db_name
    
    try:
        db = get_db()
        yield db
    finally:
        # Cleanup: drop test database
        try:
            db.client.drop_database(test_db_name)
        except Exception as e:
            print(f"Warning: Could not drop test database {test_db_name}: {e}")
        
        # Restore original database name
        if original_db_name:
            os.environ['MONGO_DB_NAME'] = original_db_name
        elif 'MONGO_DB_NAME' in os.environ:
            del os.environ['MONGO_DB_NAME']


@pytest.fixture
def mock_composio_service():
    """Mock Composio service responses"""
    with patch('services.composio_service.ComposioService') as mock_service:
        # Create mock instance
        mock_instance = Mock()
        mock_service.return_value = mock_instance
        
        # Configure typical email response with nested structure (the bug we fixed)
        mock_instance.process_query.return_value = {
            'source_type': 'mail',
            'content': 'Emails fetched.',
            'data': {
                'data': {
                    'messages': [
                        {
                            'messageId': '198efca4a33ef48d',
                            'thread_id': 'thread_123',
                            'subject': 'Test Email Subject',
                            'messageText': 'Test email content',
                            'date': '1640995200',  # Unix timestamp
                            'from': {'name': 'Test Sender', 'email': 'test@example.com'},
                            'to': [{'name': 'Test Receiver', 'email': 'receiver@example.com'}],
                            'labelIds': ['INBOX'],
                            'attachmentList': []
                        },
                        {
                            'messageId': '298efca4a33ef48e',
                            'thread_id': 'thread_124',
                            'subject': 'Another Test Email',
                            'messageText': 'Another test email content',
                            'date': '1640995300',
                            'from': {'name': 'Another Sender', 'email': 'sender2@example.com'},
                            'to': [{'name': 'Test Receiver', 'email': 'receiver@example.com'}],
                            'labelIds': ['INBOX'],
                            'attachmentList': []
                        }
                    ]
                }
            },
            'next_page_token': None,
            'total_estimate': 2,
            'has_more': False
        }
        
        yield mock_instance


@pytest.fixture
def sample_user_query():
    """Sample user query for email tests"""
    return "Show me recent emails from test@example.com"


@pytest.fixture
def sample_thread_id():
    """Sample thread ID for tests"""
    return "test_thread_12345"


@pytest.fixture
def clean_collections(test_db):
    """Ensure collections are clean before each test"""
    # Clean up any existing test data
    emails_collection = get_collection('emails')
    conversations_collection = get_collection('conversations')
    
    emails_collection.delete_many({})
    conversations_collection.delete_many({})
    
    yield
    
    # Clean up after test
    emails_collection.delete_many({})
    conversations_collection.delete_many({})


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing"""
    with patch('openai.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client
        
        # Mock typical OpenAI response for email query
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "I'll help you find recent emails."
        mock_response.choices[0].message.tool_calls = None
        
        mock_client.chat.completions.create.return_value = mock_response
        
        yield mock_client