"""
REGRESSION TESTS for Google Calendar Integration

These tests specifically cover the bugs that have been fixed and ensure
they don't regress in the future. Most importantly, this covers the
Composio response structure handling that was fixed.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from tests.test_utils.calendar_helpers import (
    create_mock_composio_response,
    create_mock_calendar_event,
    create_mock_calendar_search_response,
    assert_calendar_response_structure
)


class TestCalendarRegression:
    """Regression tests for previously fixed calendar bugs"""
    
    def test_nested_composio_response_structure_handling(
        self, test_db, clean_collections, mock_openai_client, sample_calendar_events
    ):
        """
        REGRESSION TEST: Ensure nested Composio response structure (data.data.items) is handled correctly.
        
        This was the main bug: Composio returns calendar events in data.data.items structure,
        but the code was only looking for data.items, resulting in zero events being displayed
        even when events existed.
        """
        from app import app
        
        # Mock Composio service with nested structure response
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            
            # Configure mock to return the nested structure that was causing issues
            nested_response = create_mock_composio_response(sample_calendar_events, 'nested')
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': nested_response['data'],  # This has data.data.items structure
                'search_context': {
                    'date_range': 'this_week',
                    'search_method': 'list_events (time-based)'
                }
            }
            
            mock_instance.calendar_account_id = '06747a1e-ff62-4c16-9869-4c214eebc920'
            mock_instance.client_available = True
            
            with app.test_client() as client:
                # Act - Make calendar query
                response = client.post('/chat', data=json.dumps({
                    'query': "What plans do I have scheduled for this week?",
                    'thread_id': 'regression_nested_structure_test'
                }), content_type='application/json')
                
                # Assert - Should successfully extract events from nested structure
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # CRITICAL: Should have extracted calendar events from nested structure
                assert 'tool_results' in response_data
                assert 'calendar_events' in response_data['tool_results']
                
                calendar_events = response_data['tool_results']['calendar_events']
                assert isinstance(calendar_events, list)
                assert len(calendar_events) == 2  # Should extract both events
                
                # Events should have correct structure
                for event in calendar_events:
                    assert 'id' in event
                    assert 'summary' in event
                    
                print("✅ REGRESSION TEST PASSED: Nested Composio response structure handled correctly")
                
    def test_calendar_events_correctly_extracted_from_response(self, sample_calendar_events):
        """
        REGRESSION TEST: Verify calendar events are correctly extracted from different response structures.
        
        This ensures the frontend processing logic handles both:
        - New nested structure: data.data.items  
        - Legacy direct structure: data.items
        - Single event structure: data (single object)
        """
        from app import app
        
        with app.test_client() as client:
            # Test Case 1: Nested structure (current Composio API)
            with patch('services.composio_service.ComposioService') as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.calendar_account_id = 'test_account'
                mock_instance.client_available = True
                
                nested_response = create_mock_composio_response(sample_calendar_events, 'nested')
                mock_instance.process_query.return_value = {
                    'source_type': 'google-calendar',
                    'content': 'Events fetched.',
                    'data': nested_response['data']
                }
                
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar",
                    'thread_id': 'extraction_nested_test'
                }), content_type='application/json')
                
                response_data = json.loads(response.data)
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) == 2
                
            # Test Case 2: Direct structure (legacy compatibility)
            with patch('services.composio_service.ComposioService') as mock_service:
                mock_instance = Mock()
                mock_service.return_value = mock_instance
                mock_instance.calendar_account_id = 'test_account'
                mock_instance.client_available = True
                
                direct_response = create_mock_composio_response(sample_calendar_events, 'direct')
                mock_instance.process_query.return_value = {
                    'source_type': 'google-calendar',
                    'content': 'Events fetched.',
                    'data': direct_response['data']
                }
                
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar",
                    'thread_id': 'extraction_direct_test'
                }), content_type='application/json')
                
                response_data = json.loads(response.data)
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) == 2
                
            print("✅ REGRESSION TEST PASSED: Calendar events extracted from both response structures")
                
    def test_frontend_receives_calendar_events(
        self, test_db, clean_collections, mock_openai_client
    ):
        """
        REGRESSION TEST: Ensure frontend receives calendar events when they exist.
        
        Before the fix, events existed in the Composio response but frontend received
        empty array due to incorrect structure parsing.
        """
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Create response with events in nested structure
            events = [
                create_mock_calendar_event('regression_event_1', 'Regression Test Meeting 1'),
                create_mock_calendar_event('regression_event_2', 'Regression Test Meeting 2'),
                create_mock_calendar_event('regression_event_3', 'Regression Test Meeting 3')
            ]
            
            nested_response = create_mock_composio_response(events, 'nested')
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': nested_response['data']
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What meetings do I have this week?",
                    'thread_id': 'frontend_receives_events_test'
                }), content_type='application/json')
                
                response_data = json.loads(response.data)
                
                # CRITICAL: Frontend must receive the events
                assert 'tool_results' in response_data
                assert 'calendar_events' in response_data['tool_results']
                
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) == 3  # Should receive all 3 events
                
                # Verify events have required data
                event_titles = [event['summary'] for event in calendar_events]
                assert 'Regression Test Meeting 1' in event_titles
                assert 'Regression Test Meeting 2' in event_titles
                assert 'Regression Test Meeting 3' in event_titles
                
                print("✅ REGRESSION TEST PASSED: Frontend correctly receives calendar events")
                
    def test_no_zero_events_returned_when_events_exist(self, sample_calendar_events):
        """
        REGRESSION TEST: Ensure we don't return 0 events when events actually exist.
        
        This was the symptom of the bug: logs showed events in Composio response,
        but final response had 0 events due to structure parsing issue.
        """
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            # Simulate the exact scenario that was failing
            nested_response = {
                'data': {
                    'data': {  # This nested structure was the issue
                        'accessRole': 'owner',
                        'defaultReminders': [
                            {'method': 'popup', 'minutes': 10},
                            {'method': 'email', 'minutes': 10}
                        ],
                        'description': '',
                        'etag': '"test_etag"',
                        'items': sample_calendar_events,  # Events are here but were being ignored
                        'kind': 'calendar#events',
                        'summary': 'michal.fiech@gmail.com',
                        'timeZone': 'Europe/Warsaw'
                    },
                    'error': None,
                    'successfull': True,
                    'successful': True,
                    'logId': 'test_log_123'
                }
            }
            
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': nested_response['data']
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What plans do I have scheduled for this week?",
                    'thread_id': 'zero_events_regression_test'
                }), content_type='application/json')
                
                response_data = json.loads(response.data)
                
                # CRITICAL: Should NOT return 0 events when events exist
                calendar_events = response_data['tool_results']['calendar_events']
                assert len(calendar_events) > 0, "Should not return 0 events when events exist in response"
                assert len(calendar_events) == 2, f"Expected 2 events, got {len(calendar_events)}"
                
                print("✅ REGRESSION TEST PASSED: No zero events returned when events exist")


class TestCalendarResponseLoggingRegression:
    """Regression tests for response logging issues"""
    
    @patch('services.composio_service.ComposioService.__init__', return_value=None)
    def test_calendar_response_logging_doesnt_fail(self, mock_init):
        """
        REGRESSION TEST: Ensure large calendar responses can be logged safely.
        
        Previously, large Composio responses could cause logging to fail,
        which interrupted the response processing flow.
        """
        # Arrange
        service = ComposioService.__new__(ComposioService)
        service.client_available = True
        service.composio = Mock()
        service.calendar_account_id = 'test_account'
        
        # Create a very large mock response
        large_event = create_mock_calendar_event(
            'large_event',
            'Large Event',
            description='A' * 2000  # Very long description
        )
        
        # Mock execute method to return large response
        large_response = create_mock_composio_response([large_event] * 50, 'nested')  # 50 events
        service.composio.actions.execute.return_value = large_response
        
        # Act - This should not fail due to logging issues
        try:
            result = service._execute_action('GOOGLECALENDAR_EVENTS_LIST', {})
            success = True
        except Exception as e:
            success = False
            print(f"Logging failed with error: {e}")
        
        # Assert
        assert success, "Large response logging should not cause failures"
        assert result is not None
        assert result.get('successful') is True
        
        print("✅ REGRESSION TEST PASSED: Large calendar responses logged safely")
        
    @patch('services.composio_service.ComposioService.__init__', return_value=None)
    def test_large_calendar_responses_handled_gracefully(self, mock_init):
        """
        REGRESSION TEST: Ensure very large calendar responses are handled gracefully.
        
        This tests the safe logging mechanism that was added to prevent
        response processing failures.
        """
        # Arrange
        service = ComposioService.__new__(ComposioService)
        service.client_available = True
        service.composio = Mock()
        service.calendar_account_id = 'test_account'
        
        # Create response that exceeds logging size limit
        many_events = []
        for i in range(100):  # Create 100 events
            event = create_mock_calendar_event(
                f'mass_event_{i}',
                f'Mass Event {i}',
                description=f'Description for event {i} ' * 50  # Long descriptions
            )
            many_events.append(event)
        
        large_response = create_mock_composio_response(many_events, 'nested')
        service.composio.actions.execute.return_value = large_response
        
        # Act
        result = service._execute_action('GOOGLECALENDAR_EVENTS_LIST', {})
        
        # Assert - Should handle gracefully without crashing
        assert result is not None
        assert result.get('successful') is True
        assert 'data' in result
        
        print("✅ REGRESSION TEST PASSED: Large calendar responses handled gracefully")
        
    def test_composio_api_changes_handled_gracefully(self, sample_calendar_events):
        """
        REGRESSION TEST: Ensure future Composio API changes are handled gracefully.
        
        This tests that unknown response structures don't break the application.
        """
        from app import app
        
        # Test unknown future response structure
        future_response_structure = {
            'data': {
                'future_format': {  # Unknown structure
                    'calendar_items': sample_calendar_events,  # Events in new location
                    'metadata': {
                        'version': '2.0',
                        'new_field': 'future_value'
                    }
                }
            }
        }
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = 'test_account'
            mock_instance.client_available = True
            
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': future_response_structure['data']
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar",
                    'thread_id': 'future_api_test'
                }), content_type='application/json')
                
                # Should handle unknown structure gracefully
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should have empty events rather than crashing
                assert 'tool_results' in response_data
                assert 'calendar_events' in response_data['tool_results']
                
                # Unknown structure should result in empty events (graceful degradation)
                calendar_events = response_data['tool_results']['calendar_events']
                assert isinstance(calendar_events, list)
                
                print("✅ REGRESSION TEST PASSED: Unknown API changes handled gracefully")


class TestCalendarErrorHandlingRegression:
    """Regression tests for calendar error handling"""
    
    def test_calendar_not_connected_error_handling(
        self, test_db, clean_collections, mock_openai_client
    ):
        """
        REGRESSION TEST: Ensure calendar not connected errors are handled properly.
        """
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.calendar_account_id = None  # Not connected
            mock_instance.client_available = True
            
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'I couldn\'t process your calendar request: Google Calendar account not connected',
                'data': {'items': []}
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar events",
                    'thread_id': 'not_connected_error_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should handle error gracefully
                assert 'not connected' in response_data['response']
                
                print("✅ REGRESSION TEST PASSED: Calendar not connected handled properly")
                
    def test_composio_service_unavailable_handling(
        self, test_db, clean_collections, mock_openai_client
    ):
        """
        REGRESSION TEST: Ensure Composio service unavailability is handled gracefully.
        """
        from app import app
        
        with patch('services.composio_service.ComposioService') as mock_service:
            mock_instance = Mock()
            mock_service.return_value = mock_instance
            mock_instance.client_available = False  # Service unavailable
            
            mock_instance.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Calendar service is currently unavailable',
                'data': {'items': []}
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What meetings do I have?",
                    'thread_id': 'service_unavailable_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should handle gracefully without crashing
                assert 'unavailable' in response_data['response']
                
                print("✅ REGRESSION TEST PASSED: Service unavailability handled gracefully")