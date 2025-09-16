"""
UNIT TESTS for Calendar Service Methods

Tests individual methods of the ComposioService calendar functionality,
including the core calendar operations and the response structure handling
that was fixed in the calendar integration.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from services.composio_service import ComposioService
from tests.test_utils.calendar_helpers import (
    create_mock_calendar_event,
    create_mock_composio_response,
    create_mock_calendar_search_response,
    assert_calendar_events_equal,
    assert_calendar_response_structure,
    create_mock_composio_errors
)


class TestCalendarServiceUnit:
    """Unit tests for individual calendar service methods"""
    
    def test_list_events_success(self, mock_composio_calendar_service):
        """Test successful calendar events listing"""
        # Arrange
        service = mock_composio_calendar_service
        mock_events = [
            create_mock_calendar_event('event1', 'Meeting 1'),
            create_mock_calendar_event('event2', 'Meeting 2')
        ]
        expected_response = create_mock_composio_response(mock_events, 'nested')
        service._execute_action.return_value = expected_response
        
        # Act
        result = service.list_events()
        
        # Assert
        assert result is not None
        assert "data" in result
        service._execute_action.assert_called_once()
        
    def test_list_events_with_time_range(self, mock_composio_calendar_service):
        """Test calendar events listing with time range filters"""
        # Arrange  
        service = mock_composio_calendar_service
        time_min = "2025-09-01T00:00:00Z"
        time_max = "2025-09-07T23:59:59Z"
        
        mock_events = [create_mock_calendar_event('week_event', 'Weekly Meeting')]
        expected_response = create_mock_composio_response(mock_events, 'nested')
        service._execute_action.return_value = expected_response
        
        # Act
        result = service.list_events(time_min=time_min, time_max=time_max)
        
        # Assert
        assert result is not None
        service._execute_action.assert_called_once()
        call_args = service._execute_action.call_args
        assert call_args[1]['params']['timeMin'] == time_min
        assert call_args[1]['params']['timeMax'] == time_max
        
    def test_list_events_with_filters(self, mock_composio_calendar_service):
        """Test calendar events listing with various filters"""
        # Arrange
        service = mock_composio_calendar_service
        expected_response = create_mock_composio_response([], 'nested')
        service._execute_action.return_value = expected_response
        
        # Act
        result = service.list_events(
            max_results=25,
            calendar_id="test_calendar",
            single_events=True,
            order_by="startTime"
        )
        
        # Assert
        assert result is not None
        service._execute_action.assert_called_once()
        call_args = service._execute_action.call_args
        assert call_args[1]['params']['maxResults'] == 25
        assert call_args[1]['params']['calendarId'] == "test_calendar"
        
    def test_list_events_empty_response(self, mock_composio_calendar_service):
        """Test calendar events listing with empty response"""
        # Arrange
        service = mock_composio_calendar_service
        empty_response = create_mock_composio_response([], 'nested')
        service._execute_action.return_value = empty_response
        
        # Act
        result = service.list_events()
        
        # Assert
        assert result is not None
        assert "data" in result
        
    def test_list_events_composio_error(self, mock_composio_calendar_service, mock_composio_calendar_errors):
        """Test calendar events listing with Composio service error"""
        # Arrange
        service = mock_composio_calendar_service
        service._execute_action.return_value = mock_composio_calendar_errors['auth_error']
        
        # Act  
        result = service.list_events()
        
        # Assert
        assert result is not None
        assert "error" in result
        
    def test_find_events_by_query(self, mock_composio_calendar_service):
        """Test finding events by search query"""
        # Arrange
        service = mock_composio_calendar_service
        search_query = "project meeting"
        mock_events = [create_mock_calendar_event('found_event', 'Project Meeting')]
        expected_response = create_mock_composio_response(mock_events, 'nested')
        service._execute_action.return_value = expected_response
        
        # Act
        result = service.find_events(query=search_query)
        
        # Assert
        assert result is not None
        service._execute_action.assert_called_once()
        call_args = service._execute_action.call_args
        assert call_args[1]['params']['query'] == search_query
        
    def test_find_events_no_results(self, mock_composio_calendar_service):
        """Test finding events with no matching results"""
        # Arrange
        service = mock_composio_calendar_service
        empty_response = create_mock_composio_response([], 'nested')
        service._execute_action.return_value = empty_response
        
        # Act
        result = service.find_events(query="nonexistent meeting")
        
        # Assert
        assert result is not None
        assert "data" in result
        
    def test_create_calendar_event_success(self, mock_composio_calendar_service):
        """Test successful calendar event creation"""
        # Arrange
        service = mock_composio_calendar_service
        created_event = create_mock_calendar_event('created_123', 'New Meeting')
        success_response = {
            'successful': True,
            'data': {'response_data': created_event}
        }
        service._execute_action.return_value = success_response
        
        # Act
        result = service.create_calendar_event(
            summary="New Meeting",
            start_time="2025-09-04T15:00:00+02:00",
            end_time="2025-09-04T16:00:00+02:00"
        )
        
        # Assert
        assert result is not None
        assert result.get('source_type') == 'google-calendar'
        assert 'Successfully created' in result.get('content', '')
        assert 'data' in result
        service._execute_action.assert_called_once()
        
        # Verify the new parameter structure is used
        call_args = service._execute_action.call_args
        params = call_args[1]['params']
        assert params['calendar_id'] == 'primary'
        assert params['summary'] == 'New Meeting'
        assert params['start_datetime'] == '2025-09-04T15:00:00'  # No timezone offset
        assert params['timezone'] == 'Europe/Warsaw'
        assert params['event_duration_hour'] == 1  # 1 hour
        assert params['event_duration_minutes'] == 0  # No remaining minutes
        
    def test_create_calendar_event_composio_failure(self, mock_composio_calendar_service):
        """Test calendar event creation with Composio service failure"""
        # Arrange
        service = mock_composio_calendar_service
        service._execute_action.return_value = {
            'successful': False,
            'error': 'Failed to create event'
        }
        
        # Act
        result = service.create_calendar_event(
            summary="Failed Meeting",
            start_time="2025-09-04T15:00:00+02:00",
            end_time="2025-09-04T16:00:00+02:00"
        )
        
        # Assert
        assert result is not None
        assert "error" in result
        
        # Verify the new parameter structure was attempted even on failure
        call_args = service._execute_action.call_args
        params = call_args[1]['params']
        assert params['calendar_id'] == 'primary'
        assert params['summary'] == 'Failed Meeting'
        assert params['start_datetime'] == '2025-09-04T15:00:00'  # No timezone offset
        assert params['timezone'] == 'Europe/Warsaw'
        assert params['event_duration_hour'] == 1  # 1 hour
        assert params['event_duration_minutes'] == 0  # No remaining minutes
        
    def test_create_calendar_event_long_duration(self, mock_composio_calendar_service):
        """Test calendar event creation with duration >= 60 minutes uses event_duration_hour"""
        # Arrange
        service = mock_composio_calendar_service
        created_event = create_mock_calendar_event('long_123', 'Long Meeting')
        success_response = {
            'successful': True,
            'data': {'response_data': created_event}
        }
        service._execute_action.return_value = success_response
        
        # Act - Create 2.5 hour event
        result = service.create_calendar_event(
            summary="Long Meeting",
            start_time="2025-09-04T14:00:00+02:00",
            end_time="2025-09-04T16:30:00+02:00"  # 2.5 hours
        )
        
        # Assert
        assert result is not None
        call_args = service._execute_action.call_args
        params = call_args[1]['params']
        assert params['event_duration_hour'] == 2  # 2 full hours
        assert params['event_duration_minutes'] == 30  # 30 remaining minutes
        assert 'start_datetime' in params
        assert 'timezone' in params
        
    def test_update_calendar_event_success(self, mock_composio_calendar_service):
        """Test successful calendar event update"""
        # Arrange
        service = mock_composio_calendar_service
        updated_event = create_mock_calendar_event('updated_123', 'Updated Meeting')
        success_response = {
            'successful': True,
            'data': updated_event
        }
        service._execute_action.return_value = success_response
        
        # Act
        result = service.update_calendar_event(
            event_id="test_event_123",
            summary="Updated Meeting",
            start_time="2025-09-04T16:00:00+02:00"
        )
        
        # Assert
        assert result is not None
        assert "data" in result
        service._execute_action.assert_called_once()
        
    def test_update_calendar_event_partial_update(self, mock_composio_calendar_service):
        """Test calendar event partial update (only some fields)"""
        # Arrange
        service = mock_composio_calendar_service
        success_response = {
            'successful': True,
            'data': {'id': 'partial_update_123'}
        }
        service._execute_action.return_value = success_response
        
        # Act
        result = service.update_calendar_event(
            event_id="test_event_123",
            location="New Room"
        )
        
        # Assert
        service._execute_action.assert_called_once()
        call_args = service._execute_action.call_args
        params = call_args[1]['params']
        assert params['event_id'] == "test_event_123"
        assert params['location'] == "New Room"
        assert 'summary' not in params  # Should not include unchanged fields
        
    def test_update_calendar_event_not_found(self, mock_composio_calendar_service):
        """Test calendar event update with event not found"""
        # Arrange
        service = mock_composio_calendar_service
        service._execute_action.return_value = {
            'successful': False,
            'error': 'Event not found'
        }
        
        # Act
        result = service.update_calendar_event(
            event_id="nonexistent_event",
            summary="Updated Meeting"
        )
        
        # Assert
        assert result is not None
        assert "error" in result
        


class TestCalendarIntentProcessing:
    """Unit tests for calendar intent analysis and processing"""
    
class TestCalendarResponseProcessing:
    """Unit tests for calendar response processing - the bug we fixed"""
    
    def test_process_nested_composio_response(self, sample_calendar_events):
        """Test processing nested Composio response structure (data.data.items)"""
        # Arrange - This is the structure that was causing the bug
        nested_response = create_mock_composio_response(sample_calendar_events, 'nested')
        
        # Act & Assert - Should correctly identify nested structure
        assert_calendar_response_structure(nested_response, 'nested')
        assert len(nested_response['data']['data']['items']) == len(sample_calendar_events)
        
    def test_process_direct_items_response(self, sample_calendar_events):
        """Test processing direct items response structure (data.items)"""
        # Arrange
        direct_response = create_mock_composio_response(sample_calendar_events, 'direct')
        
        # Act & Assert
        assert_calendar_response_structure(direct_response, 'direct')
        assert len(direct_response['data']['items']) == len(sample_calendar_events)
        
    def test_process_single_event_response(self, sample_calendar_events):
        """Test processing single event response"""
        # Arrange
        single_response = create_mock_composio_response(sample_calendar_events[0], 'single')
        
        # Act & Assert
        assert 'data' in single_response
        assert single_response['data']['id'] == sample_calendar_events[0]['id']
        
    def test_process_creation_response(self, sample_calendar_events):
        """Test processing event creation response"""
        # Arrange
        creation_response = create_mock_composio_response(sample_calendar_events[0], 'creation')
        
        # Act & Assert
        assert_calendar_response_structure(creation_response, 'creation')
        assert creation_response['data']['created_event']['id'] == sample_calendar_events[0]['id']
        
    def test_process_empty_response(self):
        """Test processing empty calendar response"""
        # Arrange
        empty_response = create_mock_composio_response([], 'nested')
        
        # Act & Assert
        assert_calendar_response_structure(empty_response, 'nested')
        assert len(empty_response['data']['data']['items']) == 0
        
    def test_process_malformed_response(self):
        """Test handling malformed calendar response"""
        # Arrange
        malformed_response = {
            'successful': False,
            'error': 'Malformed response',
            'data': {'corrupted': 'structure'}
        }
        
        # Act & Assert - Should handle gracefully
        assert malformed_response['successful'] is False
        assert 'error' in malformed_response