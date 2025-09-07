"""
Pytest configuration and fixtures for PM Co-Pilot backend tests.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
import tempfile
import shutil
from dotenv import load_dotenv

# Add backend directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Load environment variables for tests
load_dotenv(dotenv_path=os.path.join(backend_dir, '.env'))

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
def conversation_cleanup():
    """Fixture to track and clean up conversations created during tests"""
    from models.conversation import Conversation
    
    # Track thread_ids created during the test
    created_thread_ids = []
    
    def track_thread_id(thread_id):
        """Track a thread_id for cleanup"""
        if thread_id and thread_id not in created_thread_ids:
            created_thread_ids.append(thread_id)
    
    def cleanup_conversations():
        """Clean up all tracked conversations"""
        total_deleted = 0
        for thread_id in created_thread_ids:
            deleted_count = Conversation.delete_by_thread_id(thread_id)
            total_deleted += deleted_count
        
        if total_deleted > 0:
            print(f"[TEST CLEANUP] Deleted {total_deleted} conversations from {len(created_thread_ids)} threads")
        
        return total_deleted
    
    # Provide the tracking function to tests
    yield track_thread_id
    
    # Clean up after test
    cleanup_conversations()


@pytest.fixture(scope="session", autouse=True)
def cleanup_all_test_conversations():
    """Session-level fixture to clean up all test conversations at the end of test session"""
    from models.conversation import Conversation
    
    yield  # Run tests first
    
    # Clean up all test conversations after all tests complete
    print("\n[SESSION CLEANUP] Cleaning up all test conversations...")
    deleted_count = Conversation.delete_test_conversations()
    if deleted_count > 0:
        print(f"[SESSION CLEANUP] Deleted {deleted_count} test conversations")
    else:
        print("[SESSION CLEANUP] No test conversations found to delete")


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


@pytest.fixture
def mock_claude_llm():
    """Mock Claude LLM for testing"""
    with patch('app.get_llm') as mock_get_llm:
        mock_llm = Mock()
        
        # Create a proper LangChain response object
        mock_response = Mock()
        mock_response.content = "Based on your calendar data, here are your scheduled plans for this week: [test response]"
        
        # Mock Claude LLM response for calendar queries
        mock_llm.invoke.return_value = mock_response
        
        mock_get_llm.return_value = mock_llm
        yield mock_llm


# Calendar Testing Fixtures
@pytest.fixture
def mock_composio_calendar_service():
    """Mock Composio calendar service with realistic responses"""
    # Import the real ComposioService class to create a real instance
    from services.composio_service import ComposioService
    
    # Create a real instance with mock API key
    real_instance = ComposioService(api_key="mock_api_key")
    
    # Mock the _execute_action method directly
    real_instance._execute_action = Mock()
    
    # Import calendar helpers here to avoid circular imports
    import sys
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, backend_dir)
    from tests.test_utils.calendar_helpers import create_mock_calendar_search_response
    
    # Configure calendar search response (the nested structure we fixed)
    search_response = create_mock_calendar_search_response('this_week', 2)
    
    # Set up account status
    real_instance.calendar_account_id = '06747a1e-ff62-4c16-9869-4c214eebc920'
    real_instance.client_available = True
    
    # Mock the process_query method for integration tests
    real_instance.process_query = Mock(return_value={
        'source_type': 'google-calendar',
        'content': 'Events fetched.',
        'data': search_response['data'],
        'search_context': {
            'date_range': 'this_week',
            'search_method': 'list_events (time-based)'
        }
    })
    
    yield real_instance


@pytest.fixture  
def mock_calendar_creation_response():
    """Mock successful calendar event creation"""
    from tests.test_utils.calendar_helpers import create_mock_calendar_creation_response
    return create_mock_calendar_creation_response(
        title="Test Created Event",
        start_time="2025-09-04T15:00:00+02:00"
    )


@pytest.fixture
def mock_composio_calendar_errors():
    """Mock various Composio calendar error scenarios"""
    from tests.test_utils.calendar_helpers import create_mock_composio_errors
    return create_mock_composio_errors()


@pytest.fixture
def sample_calendar_events():
    """Sample calendar events for testing"""
    from tests.test_utils.calendar_helpers import create_mock_calendar_event
    return [
        create_mock_calendar_event(
            event_id='test_event_1',
            title='Test Meeting 1',
            start_time='2025-09-03T14:00:00+02:00',
            end_time='2025-09-03T15:00:00+02:00',
            location='Room A'
        ),
        create_mock_calendar_event(
            event_id='test_event_2', 
            title='Test Meeting 2',
            start_time='2025-09-03T16:00:00+02:00',
            end_time='2025-09-03T17:00:00+02:00',
            attendees=['attendee@example.com']
        )
    ]


@pytest.fixture
def calendar_test_queries():
    """Common calendar query patterns for testing"""
    return {
        'search_this_week': "What plans do I have scheduled for this week?",
        'search_today': "What meetings do I have today?",
        'search_tomorrow': "Show me tomorrow's calendar",
        'create_meeting': "Schedule a meeting with John at 3pm tomorrow",
        'create_detailed': "Create a meeting called 'Project Review' tomorrow at 2pm in Room A with john@example.com",
        'ambiguous': "What about next week?",
        'empty_result': "Do I have any meetings on Christmas?"
    }