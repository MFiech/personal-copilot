"""
CALENDAR DELETE END-TO-END TESTS

End-to-end tests covering the complete calendar deletion workflow:
- Frontend request simulation
- Backend processing
- Composio integration
- Database updates
- Response validation
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


class TestCalendarDeleteE2E:
    """End-to-end tests for calendar event deletion workflow"""
    
    def test_complete_delete_workflow_success(self, test_db, clean_collections, mock_openai_client):
        """Test complete calendar deletion workflow from request to response"""
        from app import app
        from models.conversation import Conversation
        
        # Setup: Create a conversation with multiple calendar events
        conversation = Conversation(
            thread_id='e2e_thread_123',
            role='assistant',
            content='Here are your calendar events for this week',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'event_to_delete_789',
                        'summary': 'Meeting to Delete',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'},
                        'organizer': {'email': 'test@example.com'},
                        'attendees': [{'email': 'test@example.com', 'responseStatus': 'accepted'}]
                    },
                    {
                        'id': 'event_to_keep_456',
                        'summary': 'Meeting to Keep',
                        'start': {'dateTime': '2025-09-05T10:00:00+02:00'},
                        'end': {'dateTime': '2025-09-05T11:00:00+02:00'},
                        'organizer': {'email': 'test@example.com'}
                    }
                ]
            }
        )
        conversation.save()
        
        # Mock tooling service to simulate successful deletion
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.delete_calendar_event.return_value = True
            
            # Simulate frontend request
            with app.test_client() as client:
                response = client.post('/delete_calendar_event', 
                    json={
                        'event_id': 'event_to_delete_789',
                        'thread_id': 'e2e_thread_123',
                        'message_id': 'e2e_message_456'
                    },
                    content_type='application/json',
                    headers={
                        'Origin': 'http://localhost:3000',
                        'Access-Control-Request-Method': 'POST',
                        'Access-Control-Request-Headers': 'Content-Type'
                    }
                )
                
                # Verify HTTP response
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'message' in data
                assert 'Google Calendar deletion succeeded' in data['message']
                
                # Verify tooling service was called with correct parameters
                mock_tooling_service.delete_calendar_event.assert_called_once_with('event_to_delete_789')
                
                # Verify database was updated correctly
                updated_conversation = Conversation.find_one({'thread_id': 'e2e_thread_123'})
                remaining_events = updated_conversation['tool_results']['calendar_events']
                
                # Should have only one event remaining
                assert len(remaining_events) == 1
                assert remaining_events[0]['id'] == 'event_to_keep_456'
                assert remaining_events[0]['summary'] == 'Meeting to Keep'
                
                # Verify the deleted event is not in the list
                event_ids = [event['id'] for event in remaining_events]
                assert 'event_to_delete_789' not in event_ids
    
    def test_complete_delete_workflow_with_composio_failure(self, test_db, clean_collections):
        """Test complete workflow when Composio deletion fails but database is still updated"""
        from app import app
        from models.conversation import Conversation
        
        # Setup: Create a conversation with calendar events
        conversation = Conversation(
            thread_id='e2e_fail_thread_123',
            role='assistant',
            content='Here are your calendar events',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'failing_event_789',
                        'summary': 'Failing Event',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'}
                    }
                ]
            }
        )
        conversation.save()
        
        # Mock tooling service to simulate failure
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.delete_calendar_event.return_value = False  # Simulate failure
            
            with app.test_client() as client:
                response = client.post('/delete_calendar_event', 
                    json={
                        'event_id': 'failing_event_789',
                        'thread_id': 'e2e_fail_thread_123',
                        'message_id': 'e2e_fail_message_456'
                    },
                    content_type='application/json'
                )
                
                # Should still return success (200) even if Composio fails
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                
                # Verify tooling service was still called
                mock_tooling_service.delete_calendar_event.assert_called_once_with('failing_event_789')
                
                # Verify database was still updated (event removed from conversation)
                updated_conversation = Conversation.find_one({'thread_id': 'e2e_fail_thread_123'})
                remaining_events = updated_conversation['tool_results']['calendar_events']
                assert len(remaining_events) == 0
    
    def test_delete_workflow_with_invalid_event_id(self, test_db, clean_collections):
        """Test workflow with invalid event ID"""
        from app import app
        from models.conversation import Conversation
        
        # Setup: Create a conversation with calendar events
        conversation = Conversation(
            thread_id='e2e_invalid_thread_123',
            role='assistant',
            content='Here are your calendar events',
            tool_results={
                'calendar_events': [
                    {
                        'id': 'valid_event_123',
                        'summary': 'Valid Event',
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
                    'event_id': 'invalid_event_999',
                    'thread_id': 'e2e_invalid_thread_123',
                    'message_id': 'e2e_invalid_message_456'
                },
                content_type='application/json'
            )
            
            # Should return 404 for event not found
            assert response.status_code == 404
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Event not found in conversation' in data['error']
            
            # Verify original conversation was not modified
            unchanged_conversation = Conversation.find_one({'thread_id': 'e2e_invalid_thread_123'})
            assert len(unchanged_conversation['tool_results']['calendar_events']) == 1
            assert unchanged_conversation['tool_results']['calendar_events'][0]['id'] == 'valid_event_123'
    
    def test_delete_workflow_with_malformed_request(self, test_db, clean_collections):
        """Test workflow with malformed JSON request"""
        from app import app
        
        with app.test_client() as client:
            # Test with malformed JSON
            response = client.post('/delete_calendar_event', 
                data='{"event_id": "test", "thread_id": "test", "message_id": "test"',  # Missing closing brace
                content_type='application/json'
            )
            
            # Should return 500 for malformed JSON (Flask handles this as internal server error)
            assert response.status_code == 500
    
    def test_delete_workflow_cors_handling(self, test_db, clean_collections):
        """Test CORS handling for delete endpoint"""
        from app import app
        
        with app.test_client() as client:
            # Test OPTIONS request (CORS preflight)
            response = client.options('/delete_calendar_event')
            assert response.status_code == 200
            
            # Test actual request with CORS headers
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': 'test_event',
                    'thread_id': 'test_thread',
                    'message_id': 'test_message'
                },
                content_type='application/json',
                headers={
                    'Origin': 'http://localhost:3000',
                    'Access-Control-Request-Method': 'POST'
                }
            )
            
            # Should handle CORS properly (even if request fails due to missing conversation)
            assert response.status_code in [200, 404]  # 404 is expected for missing conversation


class TestCalendarDeleteErrorScenarios:
    """Tests for various error scenarios in calendar deletion"""
    
    def test_delete_with_empty_event_id(self, test_db, clean_collections):
        """Test deletion with empty event ID"""
        from app import app
        
        with app.test_client() as client:
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': '',
                    'thread_id': 'test_thread_123',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Missing required parameters' in data['error']
    
    def test_delete_with_none_event_id(self, test_db, clean_collections):
        """Test deletion with None event ID"""
        from app import app
        
        with app.test_client() as client:
            response = client.post('/delete_calendar_event', 
                json={
                    'event_id': None,
                    'thread_id': 'test_thread_123',
                    'message_id': 'test_message_456'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['success'] is False
            assert 'Missing required parameters' in data['error']
    
    def test_delete_with_very_long_event_id(self, test_db, clean_collections):
        """Test deletion with unusually long event ID"""
        from app import app
        from models.conversation import Conversation
        
        # Create a conversation with a very long event ID
        long_event_id = 'a' * 1000  # 1000 character event ID
        conversation = Conversation(
            thread_id='long_id_thread_123',
            role='assistant',
            content='Test with long event ID',
            tool_results={
                'calendar_events': [
                    {
                        'id': long_event_id,
                        'summary': 'Event with Long ID',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'}
                    }
                ]
            }
        )
        conversation.save()
        
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.delete_calendar_event.return_value = True
            
            with app.test_client() as client:
                response = client.post('/delete_calendar_event', 
                    json={
                        'event_id': long_event_id,
                        'thread_id': 'long_id_thread_123',
                        'message_id': 'long_id_message_456'
                    },
                    content_type='application/json'
                )
                
                # Should handle long event ID gracefully
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                
                # Verify tooling service was called with the long ID
                mock_tooling_service.delete_calendar_event.assert_called_once_with(long_event_id)
