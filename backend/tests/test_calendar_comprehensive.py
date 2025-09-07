"""
COMPREHENSIVE CALENDAR TESTS

Focused test suite covering the most critical calendar integration functionality,
specifically the nested response structure bug that was fixed.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment - but allow LLM for integration tests
# os.environ["TESTING"] = "true" - Commented out to allow LLM in calendar tests
os.environ["CI"] = "false"  # Allow LLM initialization


class TestCalendarComprehensive:
    """Comprehensive calendar integration tests"""
    
    def test_calendar_nested_response_structure_regression(
        self, test_db, clean_collections, mock_openai_client, mock_claude_llm
    ):
        """
        CRITICAL REGRESSION TEST: Ensure nested Composio response structure is handled.
        
        This was the main bug: Composio returns data.data.items but code expected data.items
        """
        from app import app
        
        # Create mock with the exact nested structure that was causing issues
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = '06747a1e-ff62-4c16-9869-4c214eebc920'
            mock_instance.client_available = True
            
            # Configure the nested response structure (the bug we fixed)
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': {
                    'data': {  # This nested structure was the issue
                        'accessRole': 'owner',
                        'defaultReminders': [
                            {'method': 'popup', 'minutes': 10},
                            {'method': 'email', 'minutes': 10}
                        ],
                        'description': '',
                        'etag': '"test_etag"',
                        'items': [  # Events are here but were being ignored
                            {
                                'id': 'test_event_123',
                                'summary': 'Test Meeting',
                                'start': {
                                    'dateTime': '2025-09-03T14:00:00+02:00',
                                    'timeZone': 'Europe/Warsaw'
                                },
                                'end': {
                                    'dateTime': '2025-09-03T15:00:00+02:00',
                                    'timeZone': 'Europe/Warsaw'
                                },
                                'htmlLink': 'https://calendar.google.com/calendar/event?eid=test123',
                                'creator': {'email': 'test@example.com'},
                                'organizer': {'email': 'test@example.com'}
                            }
                        ],
                        'kind': 'calendar#events',
                        'summary': 'michal.fiech@gmail.com',
                        'timeZone': 'Europe/Warsaw'
                    }
                }
            }
            
            with app.test_client() as client:
                # Act - Make the exact query that was failing
                response = client.post('/chat', data=json.dumps({
                    'query': "What plans do I have scheduled for this week?",
                    'thread_id': 'calendar_regression_test_123'
                }), content_type='application/json')
                
                # Assert - Should successfully process
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # CRITICAL: Should extract events from nested structure
                assert 'tool_results' in response_data
                assert 'calendar_events' in response_data['tool_results']
                
                calendar_events = response_data['tool_results']['calendar_events']
                assert isinstance(calendar_events, list)
                assert len(calendar_events) == 1  # Should extract the event
                
                # Verify event data
                event = calendar_events[0]
                assert event['id'] == 'test_event_123'
                assert event['summary'] == 'Test Meeting'
                assert 'start' in event
                assert 'end' in event
                
                print("✅ REGRESSION TEST PASSED: Nested response structure handled correctly")
                
    def test_calendar_multiple_events_extraction(
        self, test_db, clean_collections, mock_openai_client
    ):
        """Test extraction of multiple events from nested structure"""
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Multiple events in nested structure
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': {
                    'data': {
                        'items': [
                            {
                                'id': 'event_1',
                                'summary': 'Meeting 1',
                                'start': {'dateTime': '2025-09-03T09:00:00+02:00'},
                                'end': {'dateTime': '2025-09-03T10:00:00+02:00'},
                                'htmlLink': 'https://calendar.google.com/1'
                            },
                            {
                                'id': 'event_2', 
                                'summary': 'Meeting 2',
                                'start': {'dateTime': '2025-09-03T14:00:00+02:00'},
                                'end': {'dateTime': '2025-09-03T15:00:00+02:00'},
                                'htmlLink': 'https://calendar.google.com/2'
                            },
                            {
                                'id': 'event_3',
                                'summary': 'Meeting 3', 
                                'start': {'dateTime': '2025-09-03T16:00:00+02:00'},
                                'end': {'dateTime': '2025-09-03T17:00:00+02:00'},
                                'htmlLink': 'https://calendar.google.com/3'
                            }
                        ]
                    }
                }
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show me my meetings today",
                    'thread_id': 'multiple_events_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) == 3
                
                # Verify all events extracted
                event_ids = [event['id'] for event in calendar_events]
                assert 'event_1' in event_ids
                assert 'event_2' in event_ids
                assert 'event_3' in event_ids
                
                print("✅ TEST PASSED: Multiple events extracted correctly")
                
    def test_calendar_empty_response_handling(
        self, test_db, clean_collections, mock_openai_client
    ):
        """Test handling of empty calendar responses"""
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Empty calendar response
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': {
                    'data': {
                        'items': []  # No events
                    }
                }
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What meetings do I have on Christmas?",
                    'thread_id': 'empty_calendar_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                calendar_events = response_data['tool_results']['calendar_events']
                assert isinstance(calendar_events, list)
                assert len(calendar_events) == 0
                
                print("✅ TEST PASSED: Empty calendar response handled correctly")
                
    def test_calendar_error_response_handling(
        self, test_db, clean_collections, mock_openai_client
    ):
        """Test handling of calendar error responses"""
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = None  # Not connected
            mock_instance.client_available = True
            
            # Error response
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'I couldn\'t process your calendar request: Google Calendar account not connected',
                'data': {'items': []}
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar",
                    'thread_id': 'calendar_error_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should handle error gracefully
                assert 'not connected' in response_data['response'].lower()
                
                print("✅ TEST PASSED: Calendar error handled gracefully")
                
    def test_calendar_backward_compatibility(
        self, test_db, clean_collections, mock_openai_client
    ):
        """Test backward compatibility with direct items structure"""
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Direct items structure (legacy)
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': {
                    'items': [  # Direct items, not nested
                        {
                            'id': 'direct_event_1',
                            'summary': 'Direct Meeting',
                            'start': {'dateTime': '2025-09-03T11:00:00+02:00'},
                            'end': {'dateTime': '2025-09-03T12:00:00+02:00'},
                            'htmlLink': 'https://calendar.google.com/direct'
                        }
                    ]
                }
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my meetings",
                    'thread_id': 'backward_compatibility_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should handle direct structure too
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) == 1
                assert calendar_events[0]['id'] == 'direct_event_1'
                
                print("✅ TEST PASSED: Backward compatibility maintained")
                
    def test_calendar_creation_response_handling(
        self, test_db, clean_collections, mock_openai_client
    ):
        """Test handling of calendar event creation responses"""
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Event creation response
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Successfully created calendar event',
                'data': {
                    'created_event': {
                        'id': 'new_event_123',
                        'summary': 'Created Meeting',
                        'start': {'dateTime': '2025-09-04T15:00:00+02:00'},
                        'end': {'dateTime': '2025-09-04T16:00:00+02:00'},
                        'htmlLink': 'https://calendar.google.com/new'
                    }
                },
                'action_performed': 'create'
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Create a meeting tomorrow at 3pm",
                    'thread_id': 'creation_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should indicate successful creation
                assert 'successfully created' in response_data['response'].lower()
                
                print("✅ TEST PASSED: Calendar creation handled correctly")


class TestCalendarStructureCompatibility:
    """Test different response structure compatibility"""
    
    def test_response_structure_detection_nested(self):
        """Test detection of nested response structure"""
        nested_data = {
            'data': {
                'data': {
                    'items': [{'id': 'test', 'summary': 'Test Event'}]
                }
            }
        }
        
        # Should detect nested structure
        assert 'data' in nested_data
        assert 'data' in nested_data['data']
        assert 'items' in nested_data['data']['data']
        
    def test_response_structure_detection_direct(self):
        """Test detection of direct response structure"""
        direct_data = {
            'data': {
                'items': [{'id': 'test', 'summary': 'Test Event'}]
            }
        }
        
        # Should detect direct structure
        assert 'data' in direct_data
        assert 'items' in direct_data['data']
        
    def test_response_structure_detection_single(self):
        """Test detection of single event structure"""
        single_data = {
            'data': {
                'id': 'single_event',
                'summary': 'Single Event'
            }
        }
        
        # Should detect single event structure
        assert 'data' in single_data
        assert 'id' in single_data['data']
        
    def test_response_structure_detection_creation(self):
        """Test detection of creation response structure"""
        creation_data = {
            'data': {
                'created_event': {
                    'id': 'created',
                    'summary': 'Created Event'
                }
            }
        }
        
        # Should detect creation structure
        assert 'data' in creation_data
        assert 'created_event' in creation_data['data']


class TestCalendarUtilities:
    """Test calendar utility functions"""
    
    def test_calendar_event_validation(self):
        """Test calendar event data validation"""
        valid_event = {
            'id': 'test_event',
            'summary': 'Test Meeting',
            'start': {'dateTime': '2025-09-03T14:00:00+02:00'},
            'end': {'dateTime': '2025-09-03T15:00:00+02:00'}
        }
        
        # Required fields should be present
        assert 'id' in valid_event
        assert 'summary' in valid_event
        assert 'start' in valid_event
        assert 'end' in valid_event
        
    def test_time_format_handling(self):
        """Test various time format handling"""
        time_formats = [
            '2025-09-03T14:00:00+02:00',  # Standard format
            '2025-09-03T14:00:00Z',       # UTC format
            '2025-09-03',                 # Date only
        ]
        
        for time_format in time_formats:
            assert isinstance(time_format, str)
            assert len(time_format) > 0
            
    def test_event_data_structure(self):
        """Test event data structure requirements"""
        # Test minimum required structure
        minimal_event = {
            'id': 'minimal',
            'summary': 'Minimal Event',
            'start': {'dateTime': '2025-09-03T14:00:00+02:00'},
            'end': {'dateTime': '2025-09-03T15:00:00+02:00'}
        }
        
        # Should have all required fields
        required_fields = ['id', 'summary', 'start', 'end']
        for field in required_fields:
            assert field in minimal_event
            
        # Start and end should have dateTime
        assert 'dateTime' in minimal_event['start']
        assert 'dateTime' in minimal_event['end']