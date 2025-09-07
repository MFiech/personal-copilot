#!/usr/bin/env python3
"""
Test script for PM Co-Pilot Langfuse integration
Tests tracing, sessions, and prompt management functionality
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from the backend
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
load_dotenv(backend_path / '.env')

from services.langfuse_service import get_langfuse_service
from utils.langfuse_helpers import get_managed_prompt, get_intent_router_prompt, get_gmail_query_builder_prompt

def test_environment_setup():
    """Test that all required environment variables are set"""
    print("🔍 Testing Environment Setup...")
    
    required_vars = [
        'LANGFUSE_SECRET_KEY', 
        'LANGFUSE_PUBLIC_KEY', 
        'LANGFUSE_HOST',
        'LANGFUSE_ENABLED'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ All required environment variables are set")
    return True

def test_service_initialization():
    """Test that the Langfuse service initializes correctly"""
    print("\n🔍 Testing Service Initialization...")
    
    try:
        langfuse_service = get_langfuse_service()
        
        if not langfuse_service.is_enabled():
            print("❌ Langfuse service is not enabled")
            return False
        
        print("✅ Langfuse service initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize Langfuse service: {e}")
        return False

def test_basic_tracing():
    """Test basic tracing functionality"""
    print("\n🔍 Testing Basic Tracing...")
    
    try:
        langfuse_service = get_langfuse_service()
        
        # Create a test trace
        trace = langfuse_service.start_conversation_trace(
            thread_id="test_thread_123",
            user_query="Test query for Langfuse integration",
            anchored_item=None,
            conversation_length=0
        )
        
        if not trace:
            print("❌ Failed to create conversation trace")
            return False
        
        print(f"✅ Created conversation trace: {trace.id}")
        
        # End the trace
        langfuse_service.end_conversation_trace(
            trace_span=trace,
            response="Test response from PM Co-Pilot",
            tool_results=None,
            draft_created=None
        )
        
        print("✅ Successfully ended conversation trace")
        
        # Flush to ensure data is sent
        langfuse_service.flush()
        print("✅ Flushed traces to Langfuse")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed basic tracing test: {e}")
        return False

def test_prompt_management():
    """Test prompt management functionality"""
    print("\n🔍 Testing Prompt Management...")
    
    try:
        langfuse_service = get_langfuse_service()
        
        # Test creating a test prompt
        test_prompt_content = "This is a test prompt for {{variable}}."
        success = langfuse_service.create_prompt(
            name="test-prompt-integration",
            prompt_content=test_prompt_content,
            labels=["test", "integration"],
            prompt_type="text"
        )
        
        if not success:
            print("❌ Failed to create test prompt")
            return False
        
        print("✅ Created test prompt successfully")
        
        # Test retrieving the prompt
        prompt = langfuse_service.get_prompt("test-prompt-integration")
        
        if not prompt:
            print("❌ Failed to retrieve test prompt")
            return False
        
        print("✅ Retrieved test prompt successfully")
        
        # Test using the helper function
        compiled_prompt = get_managed_prompt("test-prompt-integration", variable="integration testing")
        
        if not compiled_prompt:
            print("❌ Failed to compile prompt with helper")
            return False
        
        print(f"✅ Compiled prompt: {compiled_prompt}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed prompt management test: {e}")
        return False

def test_helper_functions():
    """Test the Langfuse helper functions"""
    print("\n🔍 Testing Helper Functions...")
    
    try:
        # Test intent router prompt helper
        intent_prompt = get_intent_router_prompt(
            user_query="Show me my recent emails",
            conversation_history=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there! How can I help you today?"}
            ]
        )
        
        if not intent_prompt:
            print("❌ Failed to get intent router prompt")
            return False
        
        print("✅ Got intent router prompt via helper")
        
        # Test Gmail query builder prompt helper
        gmail_prompt = get_gmail_query_builder_prompt(
            user_query="emails from john about the meeting",
            conversation_history=[]
        )
        
        if not gmail_prompt:
            print("❌ Failed to get Gmail query builder prompt")
            return False
        
        print("✅ Got Gmail query builder prompt via helper")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed helper functions test: {e}")
        return False

def test_session_functionality():
    """Test session creation and metadata"""
    print("\n🔍 Testing Session Functionality...")
    
    try:
        langfuse_service = get_langfuse_service()
        
        # Test session ID generation
        session_id = langfuse_service.create_session_id("test_thread_456", "conversation")
        expected_session_id = "conversation_test_thread_456"
        
        if session_id != expected_session_id:
            print(f"❌ Unexpected session ID: {session_id}, expected: {expected_session_id}")
            return False
        
        print(f"✅ Generated correct session ID: {session_id}")
        
        # Test thread metadata retrieval
        metadata = langfuse_service.get_thread_metadata("test_thread_456")
        
        if not isinstance(metadata, dict):
            print("❌ Thread metadata is not a dictionary")
            return False
        
        required_keys = ["thread_id", "thread_title", "created_at", "updated_at"]
        for key in required_keys:
            if key not in metadata:
                print(f"❌ Missing key in thread metadata: {key}")
                return False
        
        print("✅ Thread metadata contains all required keys")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed session functionality test: {e}")
        return False

def test_full_workflow():
    """Test a complete workflow with tracing and sessions"""
    print("\n🔍 Testing Full Workflow...")
    
    try:
        langfuse_service = get_langfuse_service()
        
        # Simulate a complete conversation turn
        print("  📝 Starting conversation trace...")
        trace = langfuse_service.start_conversation_trace(
            thread_id="workflow_test_123",
            user_query="Can you help me find emails from last week?",
            anchored_item=None,
            conversation_length=2
        )
        
        if not trace:
            print("❌ Failed to start conversation trace")
            return False
        
        # Simulate LLM processing with generation span
        print("  🤖 Creating generation span...")
        generation_span = langfuse_service.create_generation_span(
            parent_trace=trace,
            name="test_llm_call",
            model="claude-3-7-sonnet-latest",
            input_data={
                "prompt": "Test prompt for workflow",
                "user_query": "Can you help me find emails from last week?"
            },
            metadata={
                "temperature": 0.7,
                "max_tokens": 1000
            }
        )
        
        if not generation_span:
            print("❌ Failed to create generation span")
            return False
        
        # Simulate LLM completion
        print("  ✨ Ending generation span...")
        langfuse_service.end_generation_span(
            generation_span=generation_span,
            output_data={
                "response": "I can help you find emails from last week. Let me search for them.",
                "reasoning": "User is asking for email search with time constraint"
            },
            usage={
                "input": 50,
                "output": 25,
                "total": 75
            }
        )
        
        # End the conversation trace
        print("  🏁 Ending conversation trace...")
        langfuse_service.end_conversation_trace(
            trace_span=trace,
            response="I can help you find emails from last week. Let me search for them.",
            tool_results={"emails": ["test_email_1", "test_email_2"]},
            draft_created=None
        )
        
        # Flush all data
        print("  🚀 Flushing traces...")
        langfuse_service.flush()
        
        print("✅ Full workflow test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Failed full workflow test: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("🎯 PM Co-Pilot Langfuse Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Environment Setup", test_environment_setup),
        ("Service Initialization", test_service_initialization),
        ("Basic Tracing", test_basic_tracing),
        ("Prompt Management", test_prompt_management),
        ("Helper Functions", test_helper_functions),
        ("Session Functionality", test_session_functionality),
        ("Full Workflow", test_full_workflow)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            failed += 1
    
    print(f"\n🏁 Test Results:")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total: {len(tests)}")
    
    if failed == 0:
        print(f"\n🎉 All tests passed! Langfuse integration is working correctly.")
        print(f"📋 Next steps:")
        print(f"1. Start your Langfuse server at {os.getenv('LANGFUSE_HOST', 'http://localhost:4000')}")
        print(f"2. Run the setup_langfuse_prompts.py script to create production prompts")
        print(f"3. Test your PM Co-Pilot application to see traces and sessions")
        print(f"4. Check the Langfuse dashboard for observability data")
        return True
    else:
        print(f"\n⚠️ Some tests failed. Please check the errors above.")
        return False

def cleanup_test_data():
    """Cleanup any test data created during testing"""
    print(f"\n🧹 Cleaning up test data...")
    
    try:
        # Note: We can't directly delete prompts/traces via the SDK
        # This is just a placeholder for any cleanup that might be needed
        print("✅ Test cleanup completed")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

def main():
    """Main test runner"""
    success = run_all_tests()
    
    # Add a small delay to let traces flush
    print("\n⏳ Waiting for traces to flush...")
    time.sleep(3)
    
    cleanup_test_data()
    
    if success:
        print(f"\n🚀 Integration test completed successfully!")
        print(f"Visit {os.getenv('LANGFUSE_HOST', 'http://localhost:4000')} to view your traces.")
    else:
        print(f"\n💥 Integration test failed. Please check the errors and try again.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
