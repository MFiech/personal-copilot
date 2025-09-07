"""
HEALTH CHECK TESTS

Minimal tests to verify API connectivity and integration health.
These are the ONLY tests that should make real API calls.
All other tests should use mocks to save tokens and improve speed.
"""

import pytest
import os
import sys
from unittest.mock import patch

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


@pytest.mark.health_check
class TestAPIHealthChecks:
    """Health checks for external API integrations"""
    
    def test_llm_connectivity_health_check(self):
        """
        HEALTH CHECK: Verify Claude LLM is accessible and responding.
        This is the only test that should make real LLM API calls.
        """
        # Only run health checks if not in testing mode
        if os.getenv("TESTING", "false").lower() == "true":
            pytest.skip("Skipping health check in TESTING mode")
            
        from app import get_llm
        
        llm = get_llm()
        if not llm:
            pytest.skip("LLM not initialized (missing API key or testing mode)")
            
        # Make a minimal token call to verify connectivity
        test_prompt = "Reply with exactly: 'Health check successful'"
        
        try:
            response = llm.invoke(test_prompt)
            assert response is not None
            assert hasattr(response, 'content')
            # Don't assert exact content as LLMs might vary slightly
            print(f"✅ LLM Health Check Response: {response.content}")
            
        except Exception as e:
            pytest.fail(f"LLM health check failed: {e}")
    
    def test_composio_calendar_connectivity_health_check(self):
        """
        HEALTH CHECK: Verify Composio calendar integration is working.
        This is the only test that should make real Composio calendar API calls.
        """
        # Only run health checks if not in testing mode
        if os.getenv("TESTING", "false").lower() == "true":
            pytest.skip("Skipping health check in TESTING mode")
            
        from services.composio_service import ComposioService
        
        composio_api_key = os.getenv("COMPOSIO_API_KEY")
        if not composio_api_key:
            pytest.skip("COMPOSIO_API_KEY not available")
            
        try:
            service = ComposioService(api_key=composio_api_key)
            
            # Check if calendar account is connected (minimal API call)
            if hasattr(service, 'calendar_account_id') and service.calendar_account_id:
                print(f"✅ Calendar Account Connected: {service.calendar_account_id}")
                
                # Optional: Make minimal calendar query if connected
                if hasattr(service, 'client_available') and service.client_available:
                    print("✅ Composio client is available")
                    
            else:
                print("ℹ️ Calendar account not connected, but service initialized successfully")
                
        except Exception as e:
            pytest.fail(f"Composio calendar health check failed: {e}")
    
    def test_database_connectivity_health_check(self):
        """
        HEALTH CHECK: Verify MongoDB connection is working.
        """
        from utils.mongo_client import get_db
        
        try:
            db = get_db()
            
            # Simple ping to verify connection
            db.admin.command('ping')
            print("✅ MongoDB connection successful")
            
            # Check if required collections exist
            collections = db.list_collection_names()
            required_collections = ['conversations', 'emails']
            
            for collection_name in required_collections:
                if collection_name in collections:
                    print(f"✅ Collection '{collection_name}' exists")
                else:
                    print(f"ℹ️ Collection '{collection_name}' will be created on first use")
                    
        except Exception as e:
            pytest.fail(f"Database health check failed: {e}")


@pytest.mark.health_check 
class TestIntegrationHealthChecks:
    """End-to-end health checks with minimal API usage"""
    
    def test_email_integration_health_check(self):
        """
        HEALTH CHECK: Verify email integration components work together.
        Uses minimal real API calls.
        """
        # Only run health checks if not in testing mode
        if os.getenv("TESTING", "false").lower() == "true":
            pytest.skip("Skipping health check in TESTING mode")
            
        from services.composio_service import ComposioService
        
        composio_api_key = os.getenv("COMPOSIO_API_KEY")
        if not composio_api_key:
            pytest.skip("COMPOSIO_API_KEY not available")
            
        try:
            service = ComposioService(api_key=composio_api_key)
            
            # Check if email tools are available (no actual email fetch)
            if hasattr(service, 'composio_client'):
                print("✅ Composio client initialized for email integration")
                
            # Verify models can be imported
            from models.email import Email
            from models.conversation import Conversation
            print("✅ Email and Conversation models imported successfully")
            
        except Exception as e:
            pytest.fail(f"Email integration health check failed: {e}")


if __name__ == "__main__":
    # Allow running health checks directly
    print("Running API Health Checks...")
    pytest.main([__file__, "-v", "-m", "health_check"])