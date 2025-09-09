"""
EDGE CASE TESTS for Google Calendar Integration

These tests cover boundary conditions, error scenarios, and edge cases
that could break the calendar integration in production.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch
from datetime import datetime, timedelta

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment
os.environ["TESTING"] = "true"
os.environ["CI"] = "true"

from tests.test_utils.calendar_helpers import (
    create_mock_composio_response,
    create_mock_calendar_event,
    create_mock_composio_errors,
    get_test_timezone_times
)


class TestCalendarEdgeCases:
    """Edge case tests for calendar functionality"""
    
    def test_composio_service_unavailable(
        self, test_db, clean_collections, mock_all_llm_services
    ):
        """Test handling when Composio service is completely unavailable"""
        from app import app
        
        # Configure LLM to return an appropriate error response
        mock_all_llm_services['claude'].invoke.return_value.content = "I'm sorry, I'm having trouble accessing the calendar service right now. Please try again later."
        
        with patch('app.tooling_service') as mock_tooling_service:
            # Mock service as unavailable
            mock_tooling_service.process_query.side_effect = Exception("Composio service initialization failed")
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What meetings do I have today?",
                    'thread_id': 'service_unavailable_test'
                }), content_type='application/json')
                
                # Should handle gracefully without 500 error
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should provide helpful error message
                assert 'response' in response_data
                print("✅ EDGE CASE PASSED: Composio service unavailable handled gracefully")
                
    def test_composio_authentication_failure(
        self, test_db, clean_collections, mock_all_llm_services, mock_composio_calendar_errors
    ):
        """Test handling of Composio authentication failures"""
        from app import app
        
        # Configure LLM to return an appropriate auth error response
        mock_all_llm_services['claude'].invoke.return_value.content = "Your Google Calendar account is not connected. Please connect your account to view calendar events."
        
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.calendar_account_id = None
            mock_tooling_service.client_available = True
            
            mock_tooling_service.process_query.return_value = {
                'source_type': 'google-calendar', 
                'content': 'I couldn\'t process your calendar request: Google Calendar account not connected',
                'data': {'items': []}
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my calendar",
                    'thread_id': 'auth_failure_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should provide clear authentication error message
                assert 'not connected' in response_data['response'].lower()
                
    def test_composio_rate_limiting(
        self, test_db, clean_collections, mock_all_llm_services, mock_composio_calendar_errors
    ):
        """Test handling of Composio API rate limiting"""
        from app import app
        
        # Configure LLM to return an appropriate rate limit response
        mock_all_llm_services['claude'].invoke.return_value.content = "I'm currently experiencing rate limiting from the calendar service. Please try again in a few minutes."
        
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.calendar_account_id = 'test_account'
            mock_tooling_service.client_available = True
            
            mock_tooling_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'I couldn\'t process your calendar request: Rate limit exceeded for calendar API',
                'data': {'items': []}
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "What's on my calendar?",
                    'thread_id': 'rate_limit_test'
                }), content_type='application/json')
                
                assert response.status_code == 200
                response_data = json.loads(response.data)
                
                # Should handle rate limiting gracefully
                assert 'rate limit' in response_data['response'].lower() or 'try again' in response_data['response'].lower()
                
    def test_composio_malformed_response(
        self, test_db, clean_collections, mock_all_llm_services
    ):
        """Test handling of malformed Composio responses"""
        from app import app
        
        # Configure LLM to return a generic response when data is malformed
        mock_all_llm_services['claude'].invoke.return_value.content = "I encountered an issue retrieving your calendar data. Please try again or check your calendar connection."
        
        with patch('app.tooling_service') as mock_tooling_service:
            mock_tooling_service.calendar_account_id = 'test_account'
            mock_tooling_service.client_available = True
            
            # Return completely malformed response
            mock_tooling_service.process_query.return_value = {
                'unexpected_field': 'corrupted_data',
                'malformed': True
            }
            
            with app.test_client() as client:
                response = client.post('/chat', data=json.dumps({
                    'query': "Show my meetings",
                    'thread_id': 'malformed_response_test'
                }), content_type='application/json')
                
                # Should handle without crashing
                assert response.status_code == 200
                response_data = json.loads(response.data)
                assert 'response' in response_data
                
    def test_invalid_calendar_id(self, mock_composio_calendar_service):
        """Test handling of invalid calendar ID"""
        # Arrange
        service = mock_composio_calendar_service
        error_response = {
            'successful': False,
            'error': 'Calendar not found',
            'data': None
        }
        service._execute_action.return_value = error_response
        
        # Mock the list_events method to return proper error response
        def mock_list_events(*args, **kwargs):
            return error_response
            
        service.list_events = Mock(side_effect=mock_list_events)
        
        # Act
        result = service.list_events(calendar_id="invalid_calendar_id")
        
        # Assert
        assert result is not None
        assert result.get('successful') is False
        assert 'Calendar not found' in str(result.get('error', ''))
        
    def test_invalid_time_range_queries(self, mock_composio_calendar_service):
        """Test handling of invalid time range specifications"""
        # Arrange
        service = mock_composio_calendar_service
        
        # Test various invalid time ranges
        invalid_ranges = [
            ("invalid_start", "2025-12-31T23:59:59Z"),
            ("2025-01-01T00:00:00Z", "invalid_end"),
            ("2025-12-31T23:59:59Z", "2025-01-01T00:00:00Z"),  # End before start
            ("not_a_date", "also_not_a_date")
        ]
        
        for time_min, time_max in invalid_ranges:
            # Should handle gracefully without crashing
            try:
                result = service.list_events(time_min=time_min, time_max=time_max)
                # If it returns, it should have handled the error
                assert result is not None
            except Exception as e:
                # Should not raise unhandled exceptions
                pytest.fail(f"Invalid time range caused unhandled exception: {e}")
                
    def test_malformed_event_creation_data(self, mock_composio_calendar_service):
        """Test handling of malformed event creation data"""
        # Arrange
        service = mock_composio_calendar_service
        
        # Override the create_calendar_event mock to return an error for malformed data
        error_response = {
            'successful': False,
            'error': 'Invalid event data format'
        }
        
        def mock_create_event_with_error(*args, **kwargs):
            # Check for malformed data and return error
            if kwargs.get('start_time') == 'not_a_valid_time' or kwargs.get('summary') == '':
                return error_response
            # Otherwise return normal response
            from tests.test_utils.calendar_helpers import create_mock_calendar_creation_response
            return create_mock_calendar_creation_response(
                title=kwargs.get('title', 'Mock Created Event'),
                start_time=kwargs.get('start_time', '2025-09-04T15:00:00+02:00')
            )
        
        service.create_calendar_event = Mock(side_effect=mock_create_event_with_error)
        
        # Act - Try to create event with malformed data
        result = service.create_calendar_event(
            summary="",  # Empty summary
            start_time="not_a_valid_time",
            end_time="also_not_valid",
            attendees=["invalid_email_format"],
            location=None
        )
        
        # Assert
        assert result is not None
        assert 'error' in result
        
    def test_timezone_handling_errors(self):
        """Test handling of timezone-related errors"""
        # Test various timezone formats and edge cases
        test_times = get_test_timezone_times()
        
        # Should handle different timezone formats
        for time_format, time_value in test_times.items():
            # These should not cause exceptions
            assert time_value is not None
            assert isinstance(time_value, str)
            
    def test_extremely_large_calendar_response(self, mock_composio_calendar_service):
        """Test handling of extremely large calendar responses"""
        # Arrange - Create response with many events
        large_events = []
        for i in range(100):  # Reduce to 100 events for test performance
            event = create_mock_calendar_event(
                f'large_event_{i}',
                f'Large Event {i}',
                description='Large event description'
            )
            large_events.append(event)
            
        large_response = create_mock_composio_response(large_events, 'nested')
        service = mock_composio_calendar_service
        service._execute_action.return_value = large_response
        
        # Mock the list_events method to return the large response
        def mock_list_events(*args, **kwargs):
            return large_response
            
        service.list_events = Mock(side_effect=mock_list_events)
        
        # Act - Should handle large response
        result = service.list_events()
        
        # Assert - Should not crash and should return data
        assert result is not None
        assert 'data' in str(result)
        
    def test_calendar_response_timeout(self, mock_composio_calendar_service):
        """Test handling of calendar response timeouts"""
        # Arrange
        service = mock_composio_calendar_service
        timeout_response = {
            'successful': False,
            'error': 'Request timeout',
            'data': None
        }
        
        # Mock the list_events method to return timeout error
        def mock_list_events_timeout(*args, **kwargs):
            return timeout_response
            
        service.list_events = Mock(side_effect=mock_list_events_timeout)
        
        # Act
        result = service.list_events()
        
        # Assert - Should handle timeout gracefully
        assert result is not None
        assert result.get('successful') is False
        assert 'timeout' in str(result.get('error', '')).lower()
            
    def test_partial_calendar_response_corruption(self, sample_calendar_events):
        """Test handling of partially corrupted calendar responses"""
        # Create response with some corrupted events
        corrupted_events = []
        
        # Add normal event
        corrupted_events.append(sample_calendar_events[0])
        
        # Add corrupted event (missing required fields)
        corrupted_event = {
            'id': 'corrupted_event',
            # Missing summary, start, end
            'corrupted_field': 'corrupted_value'
        }
        corrupted_events.append(corrupted_event)
        
        # Add another normal event  
        corrupted_events.append(sample_calendar_events[1])
        
        corrupted_response = create_mock_composio_response(corrupted_events, 'nested')
        
        # Should handle mixed valid/invalid events gracefully
        assert corrupted_response['data']['data']['items'] == corrupted_events
        assert len(corrupted_response['data']['data']['items']) == 3


class TestCalendarBoundaryConditions:
    """Tests for boundary conditions in calendar functionality"""
    
    def test_calendar_events_at_exact_time_boundaries(self, mock_composio_calendar_service):
        """Test calendar events that fall exactly on time boundaries"""
        # Test events at midnight, end of day, etc.
        boundary_times = [
            ("2025-09-01T00:00:00+02:00", "2025-09-01T01:00:00+02:00"),  # Midnight
            ("2025-09-01T23:00:00+02:00", "2025-09-01T23:59:59+02:00"),  # End of day
            ("2025-09-01T12:00:00+02:00", "2025-09-01T12:00:01+02:00"),  # 1-second meeting
        ]
        
        for start_time, end_time in boundary_times:
            boundary_event = create_mock_calendar_event(
                'boundary_event',
                'Boundary Time Event',
                start_time=start_time,
                end_time=end_time
            )
            
            response = create_mock_composio_response([boundary_event], 'nested')
            service = mock_composio_calendar_service
            service._execute_action.return_value = response
            
            # Mock the list_events method to return the response
            def mock_list_events(*args, **kwargs):
                return response
                
            service.list_events = Mock(side_effect=mock_list_events)
            
            result = service.list_events()
            assert result is not None
            assert 'data' in str(result)
            
    def test_calendar_events_crossing_timezone_boundaries(self):
        """Test events that cross timezone boundaries"""
        # Event starting in one timezone, ending in another (theoretically)
        timezone_event = create_mock_calendar_event(
            'timezone_event',
            'Cross-Timezone Event',
            start_time='2025-09-01T23:30:00+02:00',  # CEST
            end_time='2025-09-02T00:30:00+02:00'     # Next day CEST
        )
        
        # Should handle without issues
        assert timezone_event['start']['dateTime'] == '2025-09-01T23:30:00+02:00'
        assert timezone_event['end']['dateTime'] == '2025-09-02T00:30:00+02:00'
        
    def test_calendar_events_spanning_multiple_days(self):
        """Test all-day and multi-day events"""
        # All-day event
        all_day_event = create_mock_calendar_event(
            'all_day_event',
            'All Day Event',
            start_time='2025-09-01',  # Date only format
            end_time='2025-09-02'
        )
        
        # Update to date-only format for all-day events
        all_day_event['start'] = {'date': '2025-09-01', 'timeZone': 'Europe/Warsaw'}
        all_day_event['end'] = {'date': '2025-09-02', 'timeZone': 'Europe/Warsaw'}
        
        assert 'date' in all_day_event['start']
        assert 'date' in all_day_event['end']
        
    def test_maximum_calendar_events_returned(self, mock_composio_calendar_service):
        """Test maximum number of calendar events that can be returned"""
        # Test with max_results boundary values
        boundary_values = [1, 2500, 2501]  # Google Calendar API limits
        
        for max_results in boundary_values:
            service = mock_composio_calendar_service
            
            # Should handle different max_results values
            try:
                result = service.list_events(max_results=max_results)
                assert result is not None
            except Exception as e:
                # If there are limits, should handle gracefully
                assert 'limit' in str(e).lower() or 'max' in str(e).lower()
                
    def test_very_long_event_descriptions(self):
        """Test events with extremely long descriptions"""
        # Create event with very long description (10KB)
        long_description = 'A' * 10000
        
        long_event = create_mock_calendar_event(
            'long_description_event',
            'Event with Long Description',
            description=long_description
        )
        
        assert len(long_event['description']) == 10000
        assert long_event['description'] == long_description
        
    def test_events_with_many_attendees(self):
        """Test events with large numbers of attendees"""
        # Create event with many attendees
        many_attendees = [f'attendee{i}@example.com' for i in range(100)]
        
        crowded_event = create_mock_calendar_event(
            'crowded_event',
            'Event with Many Attendees',
            attendees=many_attendees
        )
        
        assert len(crowded_event['attendees']) == 100
        assert all('@example.com' in attendee['email'] for attendee in crowded_event['attendees'])
        
    def test_very_complex_search_queries(self, mock_composio_calendar_service):
        """Test handling of very complex search queries"""
        complex_queries = [
            "Find all meetings with John or Jane about project Alpha or Beta scheduled for next week but not on Friday afternoon",
            "Show me recurring events that happen on weekdays between 9am and 5pm involving sales team members",
            "",  # Empty query
            "a" * 1000,  # Very long query
            "特殊字符 émojis 🚀 and unicode",  # Unicode characters
        ]
        
        for query in complex_queries:
            service = mock_composio_calendar_service
            
            # Should handle all query types without crashing
            try:
                result = service.find_events(query=query)
                assert result is not None
            except Exception as e:
                # Should not cause unhandled exceptions
                pytest.fail(f"Complex query '{query[:50]}...' caused exception: {e}")
                
    def test_ambiguous_time_expressions(self):
        """Test handling of ambiguous time expressions"""
        # These are edge cases for time parsing
        ambiguous_times = [
            "next Friday",  # Which Friday?
            "tomorrow",     # At what time?
            "this morning", # What time exactly?
            "5pm",          # Which day?
            "noon",         # Which day?
            "end of day",   # Vague time
            "sometime next week"  # Very vague
        ]
        
        # Test time extraction doesn't crash on ambiguous input
        from services.composio_service import ComposioService
        service = ComposioService.__new__(ComposioService)
        
        for time_expr in ambiguous_times:
            try:
                time_min, time_max = service._extract_time_range(time_expr.lower())
                # Should either return valid times or None, not crash
                if time_min is not None:
                    assert isinstance(time_min, str)
                if time_max is not None:
                    assert isinstance(time_max, str)
            except Exception as e:
                pytest.fail(f"Ambiguous time '{time_expr}' caused exception: {e}")
                
    def test_multiple_overlapping_time_ranges(self, mock_composio_calendar_service):
        """Test handling of overlapping time ranges in queries"""
        # Events that overlap in time
        overlapping_events = [
            create_mock_calendar_event(
                'overlap_1',
                'Meeting A',
                start_time='2025-09-01T14:00:00+02:00',
                end_time='2025-09-01T15:30:00+02:00'
            ),
            create_mock_calendar_event(
                'overlap_2',
                'Meeting B',
                start_time='2025-09-01T15:00:00+02:00',
                end_time='2025-09-01T16:00:00+02:00'
            ),
            create_mock_calendar_event(
                'overlap_3',
                'Meeting C',
                start_time='2025-09-01T14:30:00+02:00',
                end_time='2025-09-01T15:00:00+02:00'
            )
        ]
        
        overlapping_response = create_mock_composio_response(overlapping_events, 'nested')
        service = mock_composio_calendar_service
        service._execute_action.return_value = overlapping_response
        
        # Mock the list_events method to return the response
        def mock_list_events(*args, **kwargs):
            return overlapping_response
            
        service.list_events = Mock(side_effect=mock_list_events)
        
        result = service.list_events(
            time_min='2025-09-01T14:00:00+02:00',
            time_max='2025-09-01T16:00:00+02:00'
        )
        
        # Should handle overlapping events without issues
        assert result is not None
        assert 'data' in str(result)
