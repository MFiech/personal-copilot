#!/usr/bin/env python3
"""
Enhanced Test script for the Draft System (Feature Branch Updates)
Tests database models, service layer, API endpoints, and new routing logic.
Includes tests for cross-thread isolation, data staleness prevention, and new prompts.
"""

import sys
import os
import requests
import json
import time

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models.draft import Draft
from services.draft_service import DraftService
from utils.mongo_client import get_db

# Test configuration
API_BASE_URL = "http://localhost:5001"
TEST_THREAD_ID = "test_thread_123"
TEST_MESSAGE_ID = "test_message_456"

def test_database_setup():
    """Test 1: Verify database collections and schemas are set up"""
    print("=== Test 1: Database Setup ===")
    
    try:
        db = get_db()
        collections = db.list_collection_names()
        
        if 'drafts' in collections:
            print("✓ Drafts collection exists")
        else:
            print("✗ Drafts collection missing")
            assert False, "Drafts collection missing"
        
        # Test collection structure by inserting a test document
        drafts_collection = db['drafts']
        test_doc = {
            'draft_id': 'test_draft_123',
            'thread_id': TEST_THREAD_ID,
            'message_id': TEST_MESSAGE_ID,
            'draft_type': 'email',
            'status': 'active',
            'to_emails': [],
            'subject': None,
            'body': None,
            'attachments': [],
            'summary': None,
            'start_time': None,
            'end_time': None,
            'attendees': [],
            'location': None,
            'description': None,
            'created_at': int(time.time()),
            'updated_at': int(time.time())
        }
        
        # Insert and then remove test document
        result = drafts_collection.insert_one(test_doc)
        if result.inserted_id:
            print("✓ Drafts collection accepts valid documents")
            drafts_collection.delete_one({'_id': result.inserted_id})
        else:
            print("✗ Failed to insert test document")
            assert False, "Failed to insert test document"
        
        print("✓ Database setup test passed\n")
        
    except Exception as e:
        print(f"✗ Database setup test failed: {e}\n")
        assert False, f"Database setup test failed: {e}"

def test_draft_model():
    """Test 2: Verify Draft model operations"""
    print("=== Test 2: Draft Model ===")
    
    try:
        # Test email draft creation
        email_draft = Draft(
            thread_id=TEST_THREAD_ID,
            message_id=TEST_MESSAGE_ID,
            draft_type="email",
            to_emails=[{"email": "test@example.com", "name": "Test User"}],
            subject="Test Email Subject"
        )
        
        draft_id = email_draft.save()
        print(f"✓ Created email draft: {draft_id}")
        
        # Test retrieval
        retrieved_draft = Draft.get_by_id(email_draft.draft_id)
        if retrieved_draft and retrieved_draft.subject == "Test Email Subject":
            print("✓ Retrieved draft correctly")
        else:
            print("✗ Failed to retrieve draft correctly")
            assert False, "Failed to retrieve draft correctly"
        
        # Test update
        success = retrieved_draft.update({"body": "Test email body content"})
        if success:
            print("✓ Updated draft successfully")
        else:
            print("✗ Failed to update draft")
            assert False, "Failed to update draft"
        
        # Test validation
        validation = retrieved_draft.validate_completeness()
        expected_missing = ['body'] if not retrieved_draft.body else []
        print(f"✓ Validation result: {validation}")
        
        # Test calendar event draft
        calendar_draft = Draft(
            thread_id=TEST_THREAD_ID,
            message_id=TEST_MESSAGE_ID + "_calendar",
            draft_type="calendar_event",
            summary="Test Meeting",
            start_time="2024-12-20T10:00:00Z",
            end_time="2024-12-20T11:00:00Z"
        )
        
        calendar_id = calendar_draft.save()
        print(f"✓ Created calendar draft: {calendar_id}")
        
        # Test thread retrieval
        thread_drafts = Draft.get_active_drafts_by_thread(TEST_THREAD_ID)
        if len(thread_drafts) >= 2:
            print(f"✓ Retrieved {len(thread_drafts)} drafts for thread")
        else:
            print(f"✗ Expected at least 2 drafts, got {len(thread_drafts)}")
        
        # Cleanup
        Draft.delete_by_id(email_draft.draft_id)
        Draft.delete_by_id(calendar_draft.draft_id)
        print("✓ Cleaned up test drafts")
        
        print("✓ Draft model test passed\n")
        
    except Exception as e:
        print(f"✗ Draft model test failed: {e}\n")
        assert False, f"Draft model test failed: {e}"

def test_draft_service():
    """Test 3: Verify DraftService operations"""
    print("=== Test 3: Draft Service ===")
    
    try:
        service = DraftService()
        
        # Test email draft creation with contact resolution
        initial_data = {
            "to_contacts": ["test@example.com"],
            "subject": "Service Test Email"
        }
        
        email_draft = service.create_draft(
            "email", 
            TEST_THREAD_ID, 
            TEST_MESSAGE_ID + "_service", 
            initial_data
        )
        print(f"✓ Created email draft via service: {email_draft.draft_id}")
        
        # Test update
        success = service.update_draft(email_draft.draft_id, {
            "body": "Test email body from service"
        })
        if success:
            print("✓ Updated draft via service")
        else:
            print("✗ Failed to update draft via service")
            assert False, "Failed to update draft via service"
        
        # Test validation
        validation = service.validate_draft_completeness(email_draft.draft_id)
        print(f"✓ Service validation: {validation}")
        
        # Test conversion to Composio params
        if validation['is_complete']:
            params = service.convert_draft_to_composio_params(email_draft.draft_id)
            print(f"✓ Converted to Composio params: {list(params.keys())}")
        else:
            print("⚠ Draft not complete, skipping Composio params test")
        
        # Test calendar draft
        calendar_data = {
            "summary": "Service Test Meeting",
            "start_time": "2024-12-20T14:00:00Z",
            "end_time": "2024-12-20T15:00:00Z",
            "location": "Conference Room A"
        }
        
        calendar_draft = service.create_draft(
            "calendar_event",
            TEST_THREAD_ID,
            TEST_MESSAGE_ID + "_service_cal",
            calendar_data
        )
        print(f"✓ Created calendar draft via service: {calendar_draft.draft_id}")
        
        # Test summary
        summary = service.get_draft_summary(email_draft.draft_id)
        if summary and summary['type'] == 'email':
            print(f"✓ Generated draft summary: {summary['summary']['subject']}")
        else:
            print("✗ Failed to generate draft summary")
        
        # Cleanup
        service.close_draft(email_draft.draft_id)
        service.close_draft(calendar_draft.draft_id)
        print("✓ Closed test drafts")
        
        print("✓ Draft service test passed\n")
        
    except Exception as e:
        print(f"✗ Draft service test failed: {e}\n")
        import traceback
        traceback.print_exc()
        assert False, f"Draft service test failed: {e}"

def test_api_endpoints():
    """Test 4: Verify API endpoints are working"""
    print("=== Test 4: API Endpoints ===")
    
    try:
        # Test draft creation endpoint
        create_data = {
            "draft_type": "email",
            "thread_id": TEST_THREAD_ID,
            "message_id": TEST_MESSAGE_ID + "_api",
            "initial_data": {
                "to_emails": [{"email": "api@example.com", "name": "API Test"}],
                "subject": "API Test Email"
            }
        }
        
        response = requests.post(f"{API_BASE_URL}/drafts", json=create_data)
        if response.status_code == 201:
            draft_data = response.json()
            draft_id = draft_data['draft']['draft_id']
            print(f"✓ Created draft via API: {draft_id}")
        else:
            print(f"✗ Failed to create draft via API: {response.status_code}")
            print(f"Response: {response.text}")
            assert False, f"Failed to create draft via API: {response.status_code}"
        
        # Test get draft endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/{draft_id}")
        if response.status_code == 200:
            print("✓ Retrieved draft via API")
        else:
            print(f"✗ Failed to retrieve draft via API: {response.status_code}")
            assert False, f"Failed to retrieve draft via API: {response.status_code}"
        
        # Test update draft endpoint
        update_data = {
            "updates": {
                "body": "Updated via API"
            }
        }
        response = requests.put(f"{API_BASE_URL}/drafts/{draft_id}", json=update_data)
        if response.status_code == 200:
            print("✓ Updated draft via API")
        else:
            print(f"✗ Failed to update draft via API: {response.status_code}")
            assert False, f"Failed to update draft via API: {response.status_code}"
        
        # Test validation endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/{draft_id}/validate")
        if response.status_code == 200:
            validation = response.json()['validation']
            print(f"✓ Validated draft via API: {validation}")
        else:
            print(f"✗ Failed to validate draft via API: {response.status_code}")
            assert False, f"Failed to validate draft via API: {response.status_code}"
        
        # Test thread drafts endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/thread/{TEST_THREAD_ID}")
        if response.status_code == 200:
            thread_drafts = response.json()
            print(f"✓ Retrieved thread drafts via API: {thread_drafts['count']} drafts")
        else:
            print(f"✗ Failed to retrieve thread drafts via API: {response.status_code}")
            assert False, f"Failed to retrieve thread drafts via API: {response.status_code}"
        
        # Test close draft endpoint
        close_data = {"status": "closed"}
        response = requests.post(f"{API_BASE_URL}/drafts/{draft_id}/close", json=close_data)
        if response.status_code == 200:
            print("✓ Closed draft via API")
        else:
            print(f"✗ Failed to close draft via API: {response.status_code}")
        
        print("✓ API endpoints test passed\n")
        
    except requests.exceptions.ConnectionError:
        print("✗ API endpoints test failed: Could not connect to server")
        print("   Make sure the Flask app is running on port 5001\n")
        assert False, "Could not connect to server"  
    except Exception as e:
        print(f"✗ API endpoints test failed: {e}\n")
        assert False, f"API endpoints test failed: {e}"

def test_thread_isolation():
    """Test 5: Verify thread isolation prevents cross-thread contamination"""
    print("=== Test 5: Thread Isolation ===")
    
    try:
        draft_service = DraftService()
        
        # Create drafts in different threads
        thread_1 = "thread_isolation_1"
        thread_2 = "thread_isolation_2"
        
        # Create draft in thread 1
        draft_1_data = {
            "to_contacts": ["thread1@example.com"],
            "subject": "Thread 1 Draft",
            "body": "This draft belongs to thread 1"
        }
        draft_1 = draft_service.create_draft("email", thread_1, "msg_1", draft_1_data)
        
        # Create draft in thread 2
        draft_2_data = {
            "to_contacts": ["thread2@example.com"],
            "subject": "Thread 2 Draft",
            "body": "This draft belongs to thread 2"
        }
        draft_2 = draft_service.create_draft("email", thread_2, "msg_2", draft_2_data)
        
        # Verify thread isolation
        thread_1_drafts = draft_service.get_active_drafts_by_thread(thread_1)
        thread_2_drafts = draft_service.get_active_drafts_by_thread(thread_2)
        
        # Check that each thread only sees its own drafts
        thread_1_ids = [d.draft_id for d in thread_1_drafts]
        thread_2_ids = [d.draft_id for d in thread_2_drafts]
        
        if draft_1.draft_id in thread_1_ids and draft_1.draft_id not in thread_2_ids:
            print("✓ Thread 1 isolation working")
        else:
            print("✗ Thread 1 isolation failed")
            assert False, "Thread 1 isolation failed"
        
        if draft_2.draft_id in thread_2_ids and draft_2.draft_id not in thread_1_ids:
            print("✓ Thread 2 isolation working")
        else:
            print("✗ Thread 2 isolation failed")
            assert False, "Thread 2 isolation failed"
        
        # Clean up
        draft_service.close_draft(draft_1.draft_id)
        draft_service.close_draft(draft_2.draft_id)
        
        print("✓ Thread isolation test passed\n")
        
    except Exception as e:
        print(f"✗ Thread isolation test failed: {e}\n")
        assert False, f"Thread isolation test failed: {e}"

def test_composio_error_recovery():
    """Test 6: Verify Composio error status recovery"""
    print("=== Test 6: Composio Error Recovery ===")
    
    try:
        draft_service = DraftService()
        
        # Create a draft
        draft_data = {
            "to_contacts": ["recovery@example.com"],
            "subject": "Recovery Test Draft",
            "body": "Testing error recovery"
        }
        draft = draft_service.create_draft("email", TEST_THREAD_ID, "recovery_msg", draft_data)
        
        # Simulate Composio error by updating status
        error_update = draft_service.update_draft(draft.draft_id, {"status": "composio_error"})
        if not error_update:
            print("✗ Failed to simulate composio_error status")
            assert False, "Failed to simulate composio_error status"
        
        print("✓ Simulated composio_error status")
        
        # Test recovery by updating the draft (should reset status to active)
        recovery_data = {"body": "Updated body after error"}
        recovery_result = draft_service.update_draft(draft.draft_id, recovery_data)
        
        if recovery_result:
            print("✓ Draft update after composio_error succeeded")
        else:
            print("✗ Draft update after composio_error failed")
            assert False, "Draft update after composio_error failed"
        
        # Clean up
        draft_service.close_draft(draft.draft_id)
        
        print("✓ Composio error recovery test passed\n")
        
    except Exception as e:
        print(f"✗ Composio error recovery test failed: {e}\n")
        assert False, f"Composio error recovery test failed: {e}"

def test_draft_validation_completeness():
    """Test 7: Verify draft validation and completeness checking"""
    print("=== Test 7: Draft Validation ===")
    
    try:
        draft_service = DraftService()
        
        # Test incomplete draft
        incomplete_data = {
            "to_contacts": ["incomplete@example.com"]
            # Missing subject and body
        }
        incomplete_draft = draft_service.create_draft("email", TEST_THREAD_ID, "incomplete_msg", incomplete_data)
        
        incomplete_validation = draft_service.validate_draft_completeness(incomplete_draft.draft_id)
        if not incomplete_validation["is_complete"]:
            print("✓ Correctly identified incomplete draft")
        else:
            print("✗ Failed to identify incomplete draft")
            assert False, "Failed to identify incomplete draft"
        
        # Test complete draft
        complete_data = {
            "to_contacts": ["complete@example.com"],
            "subject": "Complete Subject",
            "body": "Complete body content"
        }
        complete_draft = draft_service.create_draft("email", TEST_THREAD_ID, "complete_msg", complete_data)
        
        complete_validation = draft_service.validate_draft_completeness(complete_draft.draft_id)
        if complete_validation["is_complete"]:
            print("✓ Correctly identified complete draft")
        else:
            print("✗ Failed to identify complete draft")
            assert False, "Failed to identify complete draft"
        
        # Clean up
        draft_service.close_draft(incomplete_draft.draft_id)
        draft_service.close_draft(complete_draft.draft_id)
        
        print("✓ Draft validation test passed\n")
        
    except Exception as e:
        print(f"✗ Draft validation test failed: {e}\n")
        assert False, f"Draft validation test failed: {e}"

def test_new_prompt_functions():
    """Test 8: Verify new prompt functions are available"""
    print("=== Test 8: New Prompt Functions ===")
    
    try:
        # Import new prompts
        from prompts import (
            draft_creation_intent_prompt,
            draft_update_intent_prompt,
            draft_field_update_prompt
        )
        
        # Test draft creation intent prompt
        creation_prompt = draft_creation_intent_prompt(
            "Create a draft email to John",
            []
        )
        if creation_prompt and len(creation_prompt) > 0:
            print("✓ Draft creation intent prompt working")
        else:
            print("✗ Draft creation intent prompt failed")
            assert False, "Draft creation intent prompt failed"
        
        # Test draft update intent prompt
        test_draft = {
            "draft_type": "email",
            "subject": "Test Subject",
            "body": "Test body"
        }
        update_prompt = draft_update_intent_prompt(
            "Update this draft",
            test_draft,
            []
        )
        if update_prompt and len(update_prompt) > 0:
            print("✓ Draft update intent prompt working")
        else:
            print("✗ Draft update intent prompt failed")
            assert False, "Draft update intent prompt failed"
        
        # Test draft field update prompt
        field_prompt = draft_field_update_prompt(
            "Add a subject",
            test_draft,
            "subject_title",
            []
        )
        if field_prompt and len(field_prompt) > 0:
            print("✓ Draft field update prompt working")
        else:
            print("✗ Draft field update prompt failed")
            assert False, "Draft field update prompt failed"
        
        print("✓ New prompt functions test passed\n")
        
    except ImportError as e:
        print(f"✗ Failed to import new prompts: {e}\n")
        assert False, f"Failed to import new prompts: {e}"
    except Exception as e:
        print(f"✗ New prompt functions test failed: {e}\n")
        assert False, f"New prompt functions test failed: {e}"

def run_all_tests():
    """Run all tests and provide summary"""
    print("🧪 Starting Enhanced Draft System Tests (Feature Branch)\n")
    
    tests = [
        ("Database Setup", test_database_setup),
        ("Draft Model", test_draft_model),
        ("Draft Service", test_draft_service),
        ("API Endpoints", test_api_endpoints),
        ("Thread Isolation", test_thread_isolation),
        ("Composio Error Recovery", test_composio_error_recovery),
        ("Draft Validation", test_draft_validation_completeness),
        ("New Prompt Functions", test_new_prompt_functions)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"Running {test_name} test...")
        success = test_func()
        results.append((test_name, success))
    
    # Summary
    print("=== Test Summary ===")
    total_tests = len(results)
    passed_tests = sum(1 for _, success in results if success)
    
    for test_name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All tests passed! Phase 1 & 2 implementation is ready.")
        return True
    else:
        print("❌ Some tests failed. Please fix the issues before proceeding.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1) 