"""
INTEGRATION TESTS for Google Calendar Full Flow

These tests simulate the complete end-to-end calendar flow:
User query → Flask route → Composio service → Data processing → Response formatting

This is designed to catch any breaking changes in the full calendar pipeline,
especially the response structure handling that was fixed.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Set testing environment before importing app
os.environ["TESTING"] = "true" 
os.environ["CI"] = "true"

from tests.test_utils.calendar_helpers import (
    create_mock_calendar_search_response,
    create_mock_calendar_creation_response,
    assert_calendar_events_equal
)


class TestCalendarIntegrationFlow:
    """Integration tests for the complete calendar pipeline"""
    
    def test_full_calendar_query_to_response_pipeline(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, calendar_test_queries
    ):
        """
        CRITICAL INTEGRATION TEST: Complete user query → calendar response pipeline.
        
        This simulates exactly what happens when a user asks for calendar events:
        1. User sends query via frontend
        2. Backend processes with LLM
        3. Composio retrieves calendar events
        4. Events are processed and formatted for frontend
        5. Response sent back with correct structure
        """
        # Import here to avoid circular imports during test discovery
        from app import app
        
        with app.test_client() as client:
            # Prepare test data
            test_query = calendar_test_queries['search_this_week']
            test_thread_id = "integration_calendar_test_123"
            
            # Configure mock to return calendar data with nested structure (the bug we fixed)
            calendar_response = create_mock_calendar_search_response('this_week', 2)
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': calendar_response['data'],  # This has the nested structure
                'search_context': {
                    'date_range': 'this_week',
                    'search_method': 'list_events (time-based)'
                }
            }
            
            # Prepare request payload
            request_payload = {
                'query': test_query,
                'thread_id': test_thread_id,
                'user_id': 'test_user_calendar_integration'
            }
            
            # Act - Make request to chat endpoint
            response = client.post(
                '/chat',
                data=json.dumps(request_payload),
                content_type='application/json'
            )
            
            # Assert - Verify successful processing
            assert response.status_code == 200
            
            response_data = json.loads(response.data)
            
            # Verify response structure
            assert 'response' in response_data
            assert 'thread_id' in response_data
            assert response_data['thread_id'] == test_thread_id
            
            # CRITICAL: Verify calendar events were processed correctly from nested structure
            assert 'tool_results' in response_data
            assert 'calendar_events' in response_data['tool_results']
            
            calendar_events = response_data['tool_results']['calendar_events']
            assert isinstance(calendar_events, list)
            assert len(calendar_events) == 2  # Should have extracted 2 events from nested response
            
            # Verify event structure
            for event in calendar_events:
                assert 'id' in event
                assert 'summary' in event
                assert 'start' in event
                assert 'end' in event
            
            print(f"✅ INTEGRATION TEST PASSED: Calendar events correctly extracted from nested Composio response")
            
    def test_calendar_search_this_week_flow(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, calendar_test_queries
    ):
        """Test specific 'this week' calendar search flow"""
        from app import app
        
        with app.test_client() as client:
            # Configure mock for 'this week' search
            calendar_response = create_mock_calendar_search_response('this_week', 3)
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': calendar_response['data']
            }
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': calendar_test_queries['search_this_week'],
                'thread_id': 'this_week_test_123'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            # Should have processed 3 events
            calendar_events = response_data['tool_results']['calendar_events']
            assert len(calendar_events) == 3
            
            # Events should have 'Weekly Meeting' pattern
            for i, event in enumerate(calendar_events):
                assert f'Weekly Meeting {i+1}' in event['summary']
                
    def test_calendar_creation_flow(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, calendar_test_queries
    ):
        """Test calendar event creation flow"""
        from app import app
        
        with app.test_client() as client:
            # Configure mock for event creation
            creation_response = create_mock_calendar_creation_response(
                title="Created Test Meeting",
                start_time="2025-09-04T15:00:00+02:00"
            )
            mock_composio_calendar_service.process_query.return_value = creation_response
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': calendar_test_queries['create_meeting'],
                'thread_id': 'creation_test_123'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            # Should indicate successful creation
            assert 'Successfully created' in response_data['response']
            
    def test_mixed_email_and_calendar_query(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services
    ):
        """Test handling queries that could be both email and calendar related"""
        from app import app
        
        with app.test_client() as client:
            # Configure calendar-focused response
            calendar_response = create_mock_calendar_search_response('today', 1)
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': calendar_response['data']
            }
            
            # Act - Query that could be interpreted as email or calendar
            response = client.post('/chat', data=json.dumps({
                'query': "Show me my meetings today",
                'thread_id': 'mixed_query_test_123'
            }), content_type='application/json')
            
            # Assert - Should be processed as calendar
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            assert 'tool_results' in response_data
            assert 'calendar_events' in response_data['tool_results']
            
    def test_calendar_search_results_formatting(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, sample_calendar_events
    ):
        """Test that calendar search results are properly formatted for frontend"""
        from app import app
        
        with app.test_client() as client:
            # Configure mock with sample events
            nested_response = {
                'data': {
                    'data': {
                        'items': sample_calendar_events,
                        'accessRole': 'owner'
                    }
                }
            }
            
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': nested_response['data']
            }
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': "What meetings do I have?",
                'thread_id': 'formatting_test_123'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            calendar_events = response_data['tool_results']['calendar_events']
            assert len(calendar_events) == 2
            
            # Verify each event has required frontend fields
            for event in calendar_events:
                assert 'id' in event
                assert 'summary' in event
                assert 'start' in event
                assert 'end' in event
                # Optional fields should be preserved if present
                if 'location' in event:
                    assert isinstance(event['location'], str)
                if 'attendees' in event:
                    assert isinstance(event['attendees'], list)


class TestCalendarLLMClassificationIntegration:
    """Test LLM classification integration with calendar processing"""
    
    def test_query_classification_calendar_intent(
        self, mock_composio_calendar_service, calendar_test_queries
    ):
        """Test that calendar queries are properly classified"""
        # Mock Gemini classification response
        with patch('services.composio_service.ComposioService.classify_query_with_llm') as mock_classify:
            mock_classify.return_value = {
                'intent': 'calendar',
                'confidence': 0.95,
                'reasoning': 'User asking about calendar events',
                'parameters': {
                    'timeframe': 'this_week',
                    'keywords': ['plans', 'scheduled']
                }
            }
            
            # Should call calendar processing
            result = mock_composio_calendar_service.process_query(
                calendar_test_queries['search_this_week']
            )
            
            assert result is not None
            mock_classify.assert_called_once()
            
    def test_query_classification_with_conversation_context(
        self, mock_composio_calendar_service
    ):
        """Test calendar classification with conversation context"""
        # Arrange - Previous conversation about calendar
        conversation_history = [
            {'role': 'user', 'content': 'What meetings do I have today?'},
            {'role': 'assistant', 'content': 'You have 2 meetings today...'},
        ]
        
        with patch('services.composio_service.ComposioService.classify_query_with_llm') as mock_classify:
            mock_classify.return_value = {
                'intent': 'calendar',
                'confidence': 0.98,
                'reasoning': 'Follow-up question about calendar in context',
                'parameters': {
                    'context_inherited': True,
                    'timeframe': 'tomorrow'
                }
            }
            
            # Act - Follow-up query should inherit context
            result = mock_composio_calendar_service.process_query(
                "What about tomorrow?",
                thread_history=conversation_history
            )
            
            # Assert
            assert result is not None
            mock_classify.assert_called_once_with("What about tomorrow?", conversation_history)
            
    def test_query_classification_fallback_to_keywords(
        self, mock_composio_calendar_service
    ):
        """Test fallback to keyword-based classification when LLM unavailable"""
        # Arrange - Mock LLM failure
        mock_composio_calendar_service.gemini_llm = None
        
        with patch('services.composio_service.ComposioService._fallback_keyword_classification') as mock_fallback:
            mock_fallback.return_value = {
                'intent': 'calendar',
                'confidence': 0.7,
                'reasoning': 'Keyword-based classification',
                'parameters': {'keywords': ['calendar', 'meeting']}
            }
            
            # Act
            result = mock_composio_calendar_service.process_query("Show my calendar meetings")
            
            # Assert - Should use fallback
            mock_fallback.assert_called_once()


class TestCalendarFrontendIntegration:
    """Test calendar frontend response formatting"""
    
    def test_calendar_events_frontend_format(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, sample_calendar_events
    ):
        """Test calendar events are formatted correctly for frontend consumption"""
        from app import app
        
        with app.test_client() as client:
            # Configure mock with nested structure (the bug we fixed)
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'Events fetched.',
                'data': {
                    'data': {  # Nested structure
                        'items': sample_calendar_events
                    }
                }
            }
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': "Show me my meetings",
                'thread_id': 'frontend_format_test'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            # Verify frontend-friendly structure
            assert 'tool_results' in response_data
            assert 'calendar_events' in response_data['tool_results']
            
            events = response_data['tool_results']['calendar_events']
            assert len(events) == 2
            
            # Each event should have frontend-required fields
            for event in events:
                assert 'id' in event
                assert 'summary' in event
                assert 'start' in event
                assert 'end' in event
                assert 'htmlLink' in event  # For frontend links
                
    def test_calendar_creation_frontend_response(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services
    ):
        """Test calendar creation response formatted for frontend"""
        from app import app
        
        with app.test_client() as client:
            # Configure creation response
            creation_response = create_mock_calendar_creation_response()
            mock_composio_calendar_service.process_query.return_value = creation_response
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': "Create a meeting tomorrow at 3pm",
                'thread_id': 'creation_frontend_test'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            # Should have success message
            assert 'Successfully created' in response_data['response']
            
    def test_calendar_error_frontend_response(
        self, test_db, clean_collections, mock_composio_calendar_service, 
        mock_all_llm_services, mock_composio_calendar_errors
    ):
        """Test calendar error responses are handled gracefully for frontend"""
        from app import app
        
        with app.test_client() as client:
            # Configure error response
            mock_composio_calendar_service.process_query.return_value = {
                'source_type': 'google-calendar',
                'content': 'I couldn\'t process your calendar request: Calendar not connected',
                'data': {'items': []}
            }
            
            # Act
            response = client.post('/chat', data=json.dumps({
                'query': "Show my calendar",
                'thread_id': 'error_frontend_test'
            }), content_type='application/json')
            
            # Assert
            assert response.status_code == 200
            response_data = json.loads(response.data)
            
            # Should handle error gracefully
            assert 'couldn\'t process' in response_data['response']
            
            # Should still have empty calendar structure for frontend
            if 'tool_results' in response_data:
                assert 'calendar_events' in response_data['tool_results']
                assert isinstance(response_data['tool_results']['calendar_events'], list)