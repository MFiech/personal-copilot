#!/usr/bin/env python3
"""
Test script for Phase 1: Auto-anchoring of drafts immediately after creation.

This script will:
1. Send a draft creation query to the backend
2. Verify that the response includes the auto_anchor_draft flag
3. Verify that draft_created includes the full draft_data
"""

import requests
import json
import sys

def test_draft_auto_anchoring():
    """Test that draft creation includes auto-anchoring data."""
    
    # Backend URL
    backend_url = "http://localhost:5001"
    
    # Test query that should trigger draft creation
    test_query = "Create a draft email to john@example.com about our meeting tomorrow"
    
    payload = {
        "query": test_query
    }
    
    print("🧪 Testing Phase 1: Auto-anchoring of drafts")
    print(f"📤 Sending query: {test_query}")
    
    try:
        # Send request to backend
        response = requests.post(f"{backend_url}/chat", json=payload)
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
        data = response.json()
        
        print(f"📥 Received response")
        print(f"Thread ID: {data.get('thread_id', 'Not provided')}")
        print(f"Response text: {data.get('response', 'No response')[:100]}...")
        
        # Check if draft was created
        draft_created = data.get('draft_created')
        auto_anchor_flag = data.get('auto_anchor_draft')
        
        if not draft_created:
            print("⚠️  No draft_created in response - this might be expected if LLM didn't detect draft intent")
            print("Full response keys:", list(data.keys()))
            return False
            
        print("✅ draft_created found in response!")
        print(f"   Draft ID: {draft_created.get('draft_id')}")
        print(f"   Draft Type: {draft_created.get('draft_type')}")
        print(f"   Status: {draft_created.get('status')}")
        
        # Check if auto_anchor_draft flag is present
        if not auto_anchor_flag:
            print("❌ auto_anchor_draft flag missing!")
            return False
            
        print("✅ auto_anchor_draft flag found!")
        
        # Check if draft_data is included
        draft_data = draft_created.get('draft_data')
        if not draft_data:
            print("❌ draft_data missing from draft_created!")
            return False
            
        print("✅ draft_data found in draft_created!")
        print(f"   Draft data keys: {list(draft_data.keys()) if isinstance(draft_data, dict) else 'Not a dict'}")
        
        # Verify essential fields
        essential_fields = ['draft_id', 'draft_type', 'status']
        missing_fields = [field for field in essential_fields if field not in draft_data]
        
        if missing_fields:
            print(f"❌ Missing essential fields in draft_data: {missing_fields}")
            return False
            
        print("✅ All essential fields present in draft_data!")
        
        print("\n🎉 Phase 1 Test PASSED!")
        print("   ✅ Draft creation detected")
        print("   ✅ auto_anchor_draft flag present")
        print("   ✅ draft_data included with all essential fields")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend server. Is it running on http://localhost:5001?")
        return False
    except Exception as e:
        print(f"❌ Error during test: {str(e)}")
        return False

def test_services_running():
    """Check if required services are running."""
    print("🔍 Checking if services are running...")
    
    try:
        # Check backend
        backend_response = requests.get("http://localhost:5001/threads", timeout=5)
        if backend_response.status_code == 200:
            print("✅ Backend service is running on http://localhost:5001")
        else:
            print(f"⚠️  Backend responded with status {backend_response.status_code}")
            
        # Check frontend
        frontend_response = requests.get("http://localhost:3000", timeout=5)
        if frontend_response.status_code == 200:
            print("✅ Frontend service is running on http://localhost:3000")
        else:
            print(f"⚠️  Frontend responded with status {frontend_response.status_code}")
            
        return True
        
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Service connection error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 PM Co-Pilot Phase 1 Auto-Anchoring Test")
    print("=" * 60)
    
    # Check services first
    if not test_services_running():
        print("\n❌ Cannot proceed - services are not running properly")
        sys.exit(1)
    
    print()
    
    # Run the main test
    success = test_draft_auto_anchoring()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 PHASE 1 IMPLEMENTATION SUCCESS!")
        print("Ready for user testing.")
    else:
        print("❌ PHASE 1 IMPLEMENTATION NEEDS FIXES")
        print("Please check the backend logs and fix issues.")
    print("=" * 60)
    
    sys.exit(0 if success else 1)