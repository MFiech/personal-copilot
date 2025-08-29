"""
CI/CD Configuration for GitHub Actions

This module provides configuration settings specifically for CI/CD environments
to prevent external API calls and ensure tests run reliably.
"""

import os

def is_ci_environment():
    """Check if running in a CI/CD environment."""
    return os.getenv('CI') == 'true' or os.getenv('TESTING') == 'true'

def get_ci_environment_vars():
    """Get environment variables for CI/CD testing."""
    return {
        'MONGO_URI': os.getenv('MONGO_URI', 'mongodb://localhost:27017'),
        'MONGO_DB_NAME': os.getenv('MONGO_DB_NAME', 'pm_copilot_test'),
        'COMPOSIO_API_KEY': os.getenv('COMPOSIO_API_KEY', 'test_key_for_mocking'),
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY', 'test_key_for_mocking'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY', 'test_key_for_mocking'),
        'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', 'test_key_for_mocking'),
        'PINECONE_API_TOKEN': os.getenv('PINECONE_API_TOKEN', 'test_key_for_mocking'),
        'TESTING': os.getenv('TESTING', 'false'),
        'CI': os.getenv('CI', 'false')
    }

def should_mock_external_services():
    """Determine if external services should be mocked."""
    return is_ci_environment()

def get_mock_config():
    """Get configuration for mocking external services."""
    return {
        'mock_composio': True,
        'mock_openai': True,
        'mock_anthropic': True,
        'mock_google': True,
        'mock_pinecone': True,
        'mock_mongodb': False  # Keep MongoDB for actual testing
    }
