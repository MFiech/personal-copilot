"""
Calendar Test Utilities

Helper functions for creating realistic mock calendar data and assertions
for the Google Calendar integration tests.
"""

from datetime import datetime, timedelta
import json


def create_mock_calendar_event(
    event_id="test_event_123",
    title="Test Meeting", 
    start_time="2025-09-03T14:00:00+02:00",
    end_time="2025-09-03T15:00:00+02:00",
    location=None,
    description=None,
    attendees=None,
    **kwargs
):
    """
    Create realistic mock calendar event data matching Google Calendar API structure.
    
    Args:
        event_id: Unique event identifier
        title: Event summary/title
        start_time: ISO 8601 datetime string
        end_time: ISO 8601 datetime string  
        location: Event location (optional)
        description: Event description (optional)
        attendees: List of attendee email addresses (optional)
        **kwargs: Additional event properties
    
    Returns:
        dict: Mock calendar event in Google Calendar API format
    """
    event = {
        'id': event_id,
        'summary': title,
        'start': {
            'dateTime': start_time,
            'timeZone': 'Europe/Warsaw'
        },
        'end': {
            'dateTime': end_time, 
            'timeZone': 'Europe/Warsaw'
        },
        'created': '2025-08-30T12:18:42.000Z',
        'updated': '2025-08-30T12:18:42.000Z',
        'creator': {
            'email': 'michal.fiech@gmail.com',
            'self': True
        },
        'organizer': {
            'email': 'michal.fiech@gmail.com',
            'self': True
        },
        'htmlLink': f'https://www.google.com/calendar/event?eid={event_id}',
        'iCalUID': f'{event_id}@google.com',
        'eventType': 'default',
        'etag': f'"{hash(event_id)}"',
        'status': 'confirmed'
    }
    
    # Add optional fields
    if location:
        event['location'] = location
        
    if description:
        event['description'] = description
        
    if attendees:
        event['attendees'] = [
            {'email': email, 'responseStatus': 'needsAction'} 
            for email in attendees
        ]
    
    # Add any additional properties
    event.update(kwargs)
    
    return event


def create_mock_composio_response(events=None, structure='nested', error=None):
    """
    Create mock Composio API responses with different structures.
    
    Args:
        events: List of calendar events (or None for empty response)
        structure: Response structure type ('nested', 'direct', 'single')
        error: Error message for failure responses
    
    Returns:
        dict: Mock Composio response matching expected format
    """
    if error:
        return {
            'successful': False,
            'error': error,
            'data': None
        }
    
    if events is None:
        events = []
    
    # Ensure events is a list
    if not isinstance(events, list):
        events = [events] if events else []
    
    base_response = {
        'successful': True,
        'error': None,
        'successfull': True,  # Note: Composio API has this typo
        'logId': 'test_log_123'
    }
    
    if structure == 'nested':
        # The structure we fixed - data.data.items
        base_response['data'] = {
            'data': {
                'accessRole': 'owner',
                'defaultReminders': [
                    {'method': 'popup', 'minutes': 10},
                    {'method': 'email', 'minutes': 10}
                ],
                'description': 'Primary calendar',
                'etag': '"test_etag_123"',
                'items': events,
                'kind': 'calendar#events',
                'nextPageToken': None,
                'summary': 'michal.fiech@gmail.com',
                'timeZone': 'Europe/Warsaw',
                'updated': '2025-09-03T12:00:00.000Z'
            },
            'error': None,
            'successfull': True,
            'successful': True,
            'logId': 'nested_log_456'
        }
    elif structure == 'direct':
        # Direct items structure - data.items  
        base_response['data'] = {
            'items': events,
            'accessRole': 'owner',
            'etag': '"test_etag_direct"'
        }
    elif structure == 'single':
        # Single event response
        event = events[0] if events else {}
        base_response['data'] = event
    elif structure == 'creation':
        # Event creation response
        event = events[0] if events else {}
        base_response['data'] = {
            'created_event': event,
            'action': 'create'
        }
    
    return base_response


def create_mock_calendar_search_response(query_type='this_week', num_events=3):
    """
    Create realistic calendar search responses for different query types.
    
    Args:
        query_type: Type of search ('this_week', 'today', 'tomorrow', 'empty')
        num_events: Number of events to include
        
    Returns:
        dict: Mock calendar search response
    """
    if query_type == 'empty':
        return create_mock_composio_response(events=[], structure='nested')
    
    # Calculate dates based on query type
    now = datetime.now()
    
    if query_type == 'this_week':
        # Create events spread across the week
        events = []
        for i in range(num_events):
            start = now + timedelta(days=i, hours=14)
            end = start + timedelta(hours=1)
            
            event = create_mock_calendar_event(
                event_id=f'week_event_{i+1}',
                title=f'Weekly Meeting {i+1}',
                start_time=start.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
                end_time=end.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
                location=f'Room {i+1}' if i % 2 == 0 else None
            )
            events.append(event)
            
    elif query_type == 'today':
        # Create events for today
        events = []
        for i in range(num_events):
            start = now.replace(hour=9+i*2, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            
            event = create_mock_calendar_event(
                event_id=f'today_event_{i+1}',
                title=f'Today Meeting {i+1}',
                start_time=start.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
                end_time=end.strftime('%Y-%m-%dT%H:%M:%S+02:00')
            )
            events.append(event)
            
    elif query_type == 'tomorrow':
        # Create events for tomorrow
        tomorrow = now + timedelta(days=1)
        events = []
        for i in range(num_events):
            start = tomorrow.replace(hour=10+i*3, minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=1)
            
            event = create_mock_calendar_event(
                event_id=f'tomorrow_event_{i+1}',
                title=f'Tomorrow Meeting {i+1}',
                start_time=start.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
                end_time=end.strftime('%Y-%m-%dT%H:%M:%S+02:00')
            )
            events.append(event)
    
    return create_mock_composio_response(events=events, structure='nested')


def create_mock_calendar_creation_response(
    title="Created Test Event",
    start_time="2025-09-04T15:00:00+02:00",
    **kwargs
):
    """
    Create mock calendar event creation response.
    
    Args:
        title: Event title
        start_time: Event start time
        **kwargs: Additional event properties
        
    Returns:
        dict: Mock creation response
    """
    event = create_mock_calendar_event(
        event_id='created_event_123',
        title=title,
        start_time=start_time,
        end_time=kwargs.get('end_time', '2025-09-04T16:00:00+02:00'),
        **kwargs
    )
    
    # Safely parse date and time from start_time
    if 'T' in start_time:
        date_part, time_part = start_time.split('T', 1)
    else:
        date_part = start_time
        time_part = '15:00:00+02:00'  # Default time if not provided
    
    return {
        'source_type': 'google-calendar',
        'content': f'Successfully created calendar event \'{title}\'',
        'data': {
            'created_event': event,
            'action': 'create'
        },
        'action_performed': 'create',
        'event_details': {
            'title': title,
            'date': date_part,
            'start_time': time_part,
            'location': kwargs.get('location')
        }
    }


def assert_calendar_events_equal(expected, actual, ignore_fields=None):
    """
    Custom assertion for calendar event comparison with flexible field matching.
    
    Args:
        expected: Expected calendar event data
        actual: Actual calendar event data  
        ignore_fields: List of fields to ignore in comparison
        
    Raises:
        AssertionError: If events don't match
    """
    if ignore_fields is None:
        ignore_fields = ['etag', 'updated', 'created']
    
    def filter_dict(d, ignore):
        if isinstance(d, dict):
            return {k: filter_dict(v, ignore) for k, v in d.items() if k not in ignore}
        elif isinstance(d, list):
            return [filter_dict(item, ignore) for item in d]
        else:
            return d
    
    filtered_expected = filter_dict(expected, ignore_fields)
    filtered_actual = filter_dict(actual, ignore_fields)
    
    assert filtered_expected == filtered_actual, f"Calendar events don't match:\nExpected: {filtered_expected}\nActual: {filtered_actual}"


def assert_calendar_response_structure(response, expected_structure='nested'):
    """
    Assert that calendar response has the expected structure.
    
    Args:
        response: Calendar API response
        expected_structure: Expected structure type
        
    Raises:
        AssertionError: If structure doesn't match
    """
    assert isinstance(response, dict), "Response must be a dictionary"
    
    if expected_structure == 'nested':
        assert 'data' in response, "Response must have 'data' field"
        assert 'data' in response['data'], "Response must have nested 'data.data' field"
        assert 'items' in response['data']['data'], "Response must have 'data.data.items' field"
        assert isinstance(response['data']['data']['items'], list), "Items must be a list"
        
    elif expected_structure == 'direct':
        assert 'data' in response, "Response must have 'data' field"
        assert 'items' in response['data'], "Response must have 'data.items' field"
        assert isinstance(response['data']['items'], list), "Items must be a list"
        
    elif expected_structure == 'creation':
        assert 'data' in response, "Response must have 'data' field"
        assert 'created_event' in response['data'], "Response must have 'data.created_event' field"


def create_mock_composio_errors():
    """
    Create various Composio calendar error scenarios.
    
    Returns:
        dict: Dictionary of error scenarios
    """
    return {
        'auth_error': create_mock_composio_response(error='Google Calendar account not connected'),
        'permission_error': create_mock_composio_response(error='Insufficient permissions to access calendar'),
        'rate_limit_error': {
            'successful': False,
            'error': 'Rate limit exceeded for calendar API',
            'data': {'error_type': 'quota_exceeded', 'retry_after': 3600},
            'source_type': 'google-calendar',
            'content': 'Rate limit exceeded'
        },
        'service_unavailable': {
            'successful': False,
            'error': 'Calendar service is currently unavailable',
            'data': {'error_type': 'service_down', 'status_code': 503},
            'source_type': 'google-calendar',
            'content': 'Service unavailable'
        },
        'invalid_calendar_error': create_mock_composio_response(error='Calendar not found'),
        'timeout_error': create_mock_composio_response(error='Request timeout'),
        'malformed_response': {
            'successful': False,
            'error': 'Invalid response format',
            'data': {'corrupted': 'data'}
        },
        'authentication_failure': {
            'successful': False,
            'error': 'Authentication failed',
            'data': {'error_type': 'auth_failed', 'message': 'Invalid credentials'},
            'source_type': 'google-calendar',
            'content': 'Authentication failed'
        },
        'network_error': {
            'successful': False,
            'error': 'Network connection failed',
            'data': {'error_type': 'network_error', 'timeout': True},
            'source_type': 'google-calendar',
            'content': 'Network error'
        }
    }


# Time zone utilities for calendar tests
def get_test_timezone_times():
    """
    Get test times in different formats for timezone testing.
    
    Returns:
        dict: Various time formats for testing
    """
    base_time = datetime(2025, 9, 4, 15, 30, 0)
    
    return {
        'local_iso': base_time.strftime('%Y-%m-%dT%H:%M:%S+02:00'),
        'utc_iso': base_time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'date_only': base_time.strftime('%Y-%m-%d'),
        'time_only': base_time.strftime('%H:%M:%S'),
        'human_readable': base_time.strftime('%A, %B %d, %Y at %I:%M %p')
    }