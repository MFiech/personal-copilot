"""
CALENDAR DELETE INTEGRATION TESTS

Integration tests for the /delete_calendar_event endpoint covering:
- Full HTTP request/response flow
- Database operations
- Composio service integration
- Error handling scenarios
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"


class TestCalendarDeleteIntegration:
    """Integration tests for calendar event deletion endpoint"""
    
    def test_delete_calendar_event_success(self, test_db, clean_collections, mock_openai_client, conversation_cleanup):
        """Test successful calendar event deletion through HTTP endpoint"""
        from app import app
        from models.conversation import Conversation
        
        # Track this thread for cleanup
        test_thread_id = 'test_thread_123'
        conversation_cleanup(test_thread_id)
        
        # Create a test conversation with calendar events
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Here are your calendar events',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'test_event_789',
                        'summary': 'Test Meeting',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'},
                        'organizer': {'email': 'test@example.com'}
                    }
                ]
            }
        )
        conversation.save()
        
        with patch('app.tooling_service') as mock_tooling_service:
            # Mock the tooling service
            mock_tooling_service.delete_calendar_event.return_value = True
            
            # Make the HTTP request
            with app.test_client() as client:
                response = client.post('/delete_calendar_event', 
                    json={
                        'event_id': 'test_event_789',
                        'thread_id': 'test_thread_123',
                        'message_id': 'test_message_456'
                    },
                    content_type='application/json'
                )
                
                # Assertions
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'message' in data
                
                # Verify tooling service was called correctly
                mock_tooling_service.delete_calendar_event.assert_called_once_with('test_event_789')
                
                # Verify event was removed from conversation
                updated_conversation = Conversation.find_one({'thread_id': 'test_thread_123'})
                assert len(updated_conversation['tool_results']['calendar_events']) == 0
    
    def test_delete_calendar_event_not_found_in_conversation(self, test_db, clean_collections, conversation_cleanup):
        """Test deletion when event is not found in conversation"""
        from app import app
        from models.conversation import Conversation
        
        # Track this thread for cleanup
        test_thread_id = 'test_thread_123'
        conversation_cleanup(test_thread_id)
        
        # Create a test conversation without the target event
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Here are your calendar events',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'different_event_123',
                        'summary': 'Different Meeting',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'}
                    }
                ]
            }
        )
        conversation.save()
        
        with app.test_client() as client:
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': 'nonexistent_event_789',
                    'thread_id': 'test_thread_123',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Event not found in conversation' in data['error']
    
    def test_delete_calendar_event_conversation_not_found(self, test_db, clean_collections, conversation_cleanup):
        """Test deletion when conversation is not found"""
        from app import app
        
        # Track this thread for cleanup (even though it won't exist)
        test_thread_id = 'nonexistent_thread_123'
        conversation_cleanup(test_thread_id)
        
        with app.test_client() as client:
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': 'test_event_789',
                    'thread_id': test_thread_id,
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Conversation not found' in data['error']
    
    def test_delete_calendar_event_missing_parameters(self, test_db, clean_collections):
        """Test deletion with missing required parameters"""
        from app import app
        
        with app.test_client() as client:
            # Test missing event_id
            response = client.post('/delete_calendar_event', 
                json={
                    'thread_id': 'test_thread_123',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Missing required parameters' in data['error']
            
            # Test missing thread_id
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': 'test_event_789',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Missing required parameters' in data['error']
    
    def test_delete_calendar_event_composio_failure(self, test_db, clean_collections, conversation_cleanup):
        """Test deletion when Composio service fails"""
        from app import app
        from models.conversation import Conversation
        
        # Track this thread for cleanup
        test_thread_id = 'test_thread_123'
        conversation_cleanup(test_thread_id)
        
        # Create a test conversation with calendar events
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Here are your calendar events',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'test_event_789',
                        'summary': 'Test Meeting',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'}
                    }
                ]
            }
        )
        conversation.save()
        
        with patch('app.tooling_service') as mock_tooling_service:
            # Mock the tooling service to return failure
            mock_tooling_service.delete_calendar_event.return_value = False
            
            with app.test_client() as client:
                response = client.post('/delete_calendar_event', 
                    json={
                        'event_id': 'test_event_789',
                        'thread_id': 'test_thread_123',
                        'message_id': 'test_message_456'
                    },
                    content_type='application/json'
                )
                
                # Should still return success (200) but with warning
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True  # Endpoint succeeds even if Composio fails
                
                # Verify tooling service was still called
                mock_tooling_service.delete_calendar_event.assert_called_once_with('test_event_789')
                
                # Verify event was still removed from conversation
                updated_conversation = Conversation.find_one({'thread_id': 'test_thread_123'})
                assert len(updated_conversation['tool_results']['calendar_events']) == 0
    
    def test_delete_calendar_event_no_calendar_events(self, test_db, clean_collections, conversation_cleanup):
        """Test deletion when conversation has no calendar events"""
        from app import app
        from models.conversation import Conversation
        
        # Track this thread for cleanup
        test_thread_id = 'test_thread_123'
        conversation_cleanup(test_thread_id)
        
        # Create a test conversation without calendar events
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='No calendar events here',
            tool_results={}
        )
        conversation.save()
        
        with app.test_client() as client:
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': 'test_event_789',
                    'thread_id': 'test_thread_123',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            # Assertions
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'No calendar events found in conversation' in data['error']
    
    def test_delete_calendar_event_options_request(self, test_db, clean_collections):
        """Test OPTIONS request for CORS preflight"""
        from app import app
        
        with app.test_client() as client:
            response = client.options('/delete_calendar_event')
            
            # Assertions
            assert response.status_code == 200
            assert response.data == b''


# Note: Parameter validation tests are covered by existing unit tests in test_calendar_service_unit.py
# The parameter naming fixes we implemented are already tested there.
