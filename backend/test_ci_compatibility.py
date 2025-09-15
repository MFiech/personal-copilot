#!/usr/bin/env python3
"""
Test script to verify CI environment compatibility.
Simulates the CI environment and runs a subset of tests to ensure compatibility.
"""

import os
import sys
import subprocess
from pathlib import Path

def setup_ci_environment():
    """Set up environment variables that match CI configuration."""
    ci_env = {
        'TESTING': 'true',
        'CI': 'true',
        'MONGO_URI': 'mongodb://localhost:27017',
        'MONGO_DB_NAME': 'pm_copilot_test',
        'COMPOSIO_API_KEY': 'test_key_for_mocking',
        'OPENAI_API_KEY': 'test_key_for_mocking',
        'ANTHROPIC_API_KEY': 'test_key_for_mocking',
        'GOOGLE_API_KEY': 'test_key_for_mocking',
        'PINECONE_API_TOKEN': 'test_key_for_mocking',
    }
    
    # Update current environment
    os.environ.update(ci_env)
    return ci_env

def run_test_subset():
    """Run a subset of tests to verify CI compatibility."""
    backend_dir = Path(__file__).parent
    
    test_commands = [
        # Test health checks (should skip in CI)
        ['python', '-m', 'pytest', 'tests/test_health_checks.py', '-v', '--tb=short'],
        
        # Test calendar service (should pass)
        ['python', '-m', 'pytest', 'tests/test_calendar_service_unit.py::TestCalendarServiceUnit::test_list_events_success', '-v', '--tb=short'],
        
        # Test composio service (should pass)  
        ['python', '-m', 'pytest', 'tests/test_composio_service_unit.py::TestComposioServiceEmailMethods::test_get_email_details_simple_text', '-v', '--tb=short'],
        
        # Test draft functionality (should pass)
        ['python', '-m', 'pytest', 'tests/test_draft_api_endpoints.py::TestDraftEndpoints::test_create_draft_endpoint', '-v', '--tb=short'],
    ]
    
    print("🚀 Running CI compatibility tests...")
    print(f"📁 Working directory: {backend_dir}")
    
    for i, cmd in enumerate(test_commands, 1):
        print(f"\n🔍 [{i}/{len(test_commands)}] Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=backend_dir,
                capture_output=True,
                text=True,
                timeout=60  # 1 minute timeout per test
            )
            
            if result.returncode == 0:
                print(f"✅ Test {i} PASSED")
            else:
                print(f"❌ Test {i} FAILED")
                print(f"STDOUT:\n{result.stdout}")
                print(f"STDERR:\n{result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"⏰ Test {i} TIMED OUT")
            return False
        except Exception as e:
            print(f"💥 Test {i} ERROR: {e}")
            return False
    
    return True

def main():
    """Main function to run CI compatibility check."""
    print("🧪 CI Compatibility Test Suite")
    print("=" * 50)
    
    # Set up CI environment
    print("🔧 Setting up CI environment variables...")
    ci_env = setup_ci_environment()
    
    for key, value in ci_env.items():
        print(f"  {key}={value}")
    
    # Run test subset
    success = run_test_subset()
    
    if success:
        print("\n🎉 All CI compatibility tests PASSED!")
        print("✅ The updated workflow should work correctly in GitHub Actions.")
        return 0
    else:
        print("\n💥 CI compatibility tests FAILED!")
        print("❌ There may be issues with the GitHub Actions workflow.")
        return 1

if __name__ == '__main__':
    sys.exit(main())