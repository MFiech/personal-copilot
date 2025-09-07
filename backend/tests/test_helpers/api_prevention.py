"""
Test helpers to prevent real API calls and ensure proper mocking.
"""

import pytest
from unittest.mock import patch, Mock
import os


class APICallPrevention:
    """Context manager and helpers to prevent real API calls during testing"""
    
    @staticmethod
    def prevent_composio_calls():
        """Prevent real Composio API calls"""
        return patch('composio.Composio', side_effect=RuntimeError(
            "Real Composio API call attempted in test! Use proper mocking."
        ))
    
    @staticmethod
    def prevent_openai_calls():
        """Prevent real OpenAI API calls"""
        return patch('openai.OpenAI', side_effect=RuntimeError(
            "Real OpenAI API call attempted in test! Use proper mocking."
        ))
    
    @staticmethod
    def prevent_anthropic_calls():
        """Prevent real Anthropic API calls"""
        return patch('langchain_anthropic.ChatAnthropic', side_effect=RuntimeError(
            "Real Anthropic API call attempted in test! Use proper mocking."
        ))
    
    @staticmethod
    def prevent_google_calls():
        """Prevent real Google API calls"""
        return patch('langchain_google_genai.ChatGoogleGenerativeAI', side_effect=RuntimeError(
            "Real Google API call attempted in test! Use proper mocking."
        ))
    
    @staticmethod
    def prevent_all_external_apis():
        """Prevent all external API calls"""
        patches = [
            APICallPrevention.prevent_composio_calls(),
            APICallPrevention.prevent_openai_calls(),
            APICallPrevention.prevent_anthropic_calls(),
            APICallPrevention.prevent_google_calls()
        ]
        
        class MultiPatchContext:
            def __enter__(self):
                self.mocks = [p.__enter__() for p in patches]
                return self.mocks
            
            def __exit__(self, *args):
                for p in reversed(patches):
                    p.__exit__(*args)
        
        return MultiPatchContext()


def assert_no_real_api_calls(func):
    """Decorator to ensure no real API calls are made in a test function"""
    def wrapper(*args, **kwargs):
        with APICallPrevention.prevent_all_external_apis():
            return func(*args, **kwargs)
    return wrapper


def mock_composio_service_safely():
    """Create a safely mocked ComposioService that won't make real API calls"""
    with patch('services.composio_service.Composio') as mock_composio:
        mock_instance = Mock()
        mock_composio.return_value = mock_instance
        
        # Ensure any attempt to call real methods fails loudly
        mock_instance.execute.side_effect = RuntimeError(
            "Real Composio execute() called! Use _execute_action mocking instead."
        )
        
        return mock_composio, mock_instance


def validate_mock_usage(mock_execute_action):
    """Validate that _execute_action is being mocked correctly in tests"""
    if not mock_execute_action.called:
        pytest.fail("_execute_action was not called - test may not be testing actual logic")
    
    # Verify proper parameters are passed
    for call in mock_execute_action.call_args_list:
        args, kwargs = call
        if 'action' not in kwargs:
            pytest.fail("_execute_action called without 'action' parameter")


# Pytest fixtures for common use
@pytest.fixture
def safe_composio_service():
    """Fixture that provides a safely mocked ComposioService"""
    mock_composio, mock_instance = mock_composio_service_safely()
    
    # Import and create service after mocking
    from services.composio_service import ComposioService
    service = ComposioService("test_api_key")
    service.client_available = True
    
    yield service


@pytest.fixture
def prevent_all_apis():
    """Fixture that prevents all external API calls"""
    with APICallPrevention.prevent_all_external_apis():
        yield


# Environment validation
def ensure_test_environment():
    """Ensure we're running in a proper test environment"""
    if not os.getenv("TESTING") and not os.getenv("CI"):
        pytest.skip("Not in testing environment - set TESTING=true to run")


# Mock validation utilities
class MockValidator:
    """Utilities to validate mock usage in tests"""
    
    @staticmethod
    def assert_composio_method_called(mock_execute, expected_action, expected_params=None):
        """Assert that ComposioService._execute_action was called correctly"""
        assert mock_execute.called, "ComposioService._execute_action was not called"
        
        call_args = mock_execute.call_args
        assert call_args is not None, "No call arguments found"
        
        kwargs = call_args[1] if len(call_args) > 1 else call_args.kwargs
        assert 'action' in kwargs, "Missing 'action' parameter in _execute_action call"
        assert kwargs['action'] == expected_action, f"Expected action {expected_action}, got {kwargs['action']}"
        
        if expected_params:
            assert 'params' in kwargs, "Missing 'params' parameter in _execute_action call"
            for key, value in expected_params.items():
                assert kwargs['params'].get(key) == value, f"Expected {key}={value}, got {kwargs['params'].get(key)}"
    
    @staticmethod
    def assert_no_real_composio_client_used(service):
        """Assert that the service is using mocked client, not real one"""
        # The composio client should be a Mock object, not the real Composio class
        assert hasattr(service.composio, '_mock_name') or str(type(service.composio)).find('Mock') != -1, \
            "ComposioService is using real Composio client instead of mock"
    
    @staticmethod
    def assert_fixtures_realistic(fixture_response):
        """Assert that fixture responses have realistic structure"""
        required_keys = ['successful', 'data', 'error', 'logId']
        for key in required_keys:
            assert key in fixture_response, f"Fixture missing required key: {key}"
        
        # If successful, data should not be None
        if fixture_response.get('successful'):
            assert fixture_response.get('data') is not None, "Successful response should have data"
        
        # If not successful, error should be present
        if not fixture_response.get('successful'):
            assert fixture_response.get('error') is not None, "Failed response should have error message"
