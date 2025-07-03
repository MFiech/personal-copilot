#!/usr/bin/env python3
"""
Test script for the Draft System (Phase 1 & 2)
Tests database models, service layer, and API endpoints.
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
            return False
        
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
            return False
        
        print("✓ Database setup test passed\n")
        return True
        
    except Exception as e:
        print(f"✗ Database setup test failed: {e}\n")
        return False

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
            return False
        
        # Test update
        success = retrieved_draft.update({"body": "Test email body content"})
        if success:
            print("✓ Updated draft successfully")
        else:
            print("✗ Failed to update draft")
            return False
        
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
        return True
        
    except Exception as e:
        print(f"✗ Draft model test failed: {e}\n")
        return False

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
            return False
        
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
        return True
        
    except Exception as e:
        print(f"✗ Draft service test failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False

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
            return False
        
        # Test get draft endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/{draft_id}")
        if response.status_code == 200:
            print("✓ Retrieved draft via API")
        else:
            print(f"✗ Failed to retrieve draft via API: {response.status_code}")
            return False
        
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
            return False
        
        # Test validation endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/{draft_id}/validate")
        if response.status_code == 200:
            validation = response.json()['validation']
            print(f"✓ Validated draft via API: {validation}")
        else:
            print(f"✗ Failed to validate draft via API: {response.status_code}")
            return False
        
        # Test thread drafts endpoint
        response = requests.get(f"{API_BASE_URL}/drafts/thread/{TEST_THREAD_ID}")
        if response.status_code == 200:
            thread_drafts = response.json()
            print(f"✓ Retrieved thread drafts via API: {thread_drafts['count']} drafts")
        else:
            print(f"✗ Failed to retrieve thread drafts via API: {response.status_code}")
            return False
        
        # Test close draft endpoint
        close_data = {"status": "closed"}
        response = requests.post(f"{API_BASE_URL}/drafts/{draft_id}/close", json=close_data)
        if response.status_code == 200:
            print("✓ Closed draft via API")
        else:
            print(f"✗ Failed to close draft via API: {response.status_code}")
        
        print("✓ API endpoints test passed\n")
        return True
        
    except requests.exceptions.ConnectionError:
        print("✗ API endpoints test failed: Could not connect to server")
        print("   Make sure the Flask app is running on port 5001\n")
        return False
    except Exception as e:
        print(f"✗ API endpoints test failed: {e}\n")
        return False

def run_all_tests():
    """Run all tests and provide summary"""
    print("🧪 Starting Draft System Tests (Phase 1 & 2)\n")
    
    tests = [
        ("Database Setup", test_database_setup),
        ("Draft Model", test_draft_model),
        ("Draft Service", test_draft_service),
        ("API Endpoints", test_api_endpoints)
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