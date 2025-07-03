#!/usr/bin/env python3
"""
Test script for Phase 4: LLM Integration & Detection
Tests the draft detection and automatic creation functionality.
"""

import sys
import os
import requests
import json

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend'))

# Test configuration
API_BASE_URL = "http://localhost:5001"

def test_draft_detection_via_chat():
    """Test draft detection through the main chat endpoint"""
    print("=== Test: Draft Detection via Chat ===")
    
    test_queries = [
        "Create a draft email to John about the project update",
        "Draft a meeting with Sarah for tomorrow at 2pm",
        "What's the weather like today?",  # Should not create draft
        "I need to draft an email to the team about the new policy"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: '{query}'")
        
        try:
            response = requests.post(f"{API_BASE_URL}/chat", json={
                "query": query,
                "thread_id": f"test_thread_phase4_{i}"
            })
            
            if response.ok:
                data = response.json()
                print(f"✓ Response received")
                print(f"  Assistant response: {data.get('response', 'No response')[:100]}...")
                
                if 'draft_created' in data:
                    draft_info = data['draft_created']
                    print(f"✓ Draft created!")
                    print(f"  Draft ID: {draft_info.get('draft_id')}")
                    print(f"  Draft Type: {draft_info.get('draft_type')}")
                    print(f"  User Message ID: {draft_info.get('user_message_id')}")
                    
                    # Test getting the draft
                    draft_response = requests.get(f"{API_BASE_URL}/drafts/message/{draft_info.get('user_message_id')}")
                    if draft_response.ok:
                        draft_data = draft_response.json()
                        print(f"✓ Draft retrieved successfully")
                        print(f"  Draft details: {json.dumps(draft_data.get('draft', {}), indent=2)[:200]}...")
                    else:
                        print(f"✗ Failed to retrieve draft")
                        
                else:
                    print(f"○ No draft created (expected for non-draft queries)")
                    
            else:
                print(f"✗ Chat request failed: {response.status_code}")
                print(f"  Error: {response.text}")
                
        except Exception as e:
            print(f"✗ Error: {e}")

def test_manual_draft_endpoints():
    """Test the manual draft creation endpoints still work"""
    print("\n=== Test: Manual Draft Creation ===")
    
    try:
        # Create a manual draft
        response = requests.post(f"{API_BASE_URL}/drafts", json={
            "draft_type": "email",
            "thread_id": "test_manual_thread",
            "message_id": "test_manual_message",
            "initial_data": {
                "to_emails": [{"email": "test@example.com", "name": "Test User"}],
                "subject": "Manual Test Email"
            }
        })
        
        if response.ok:
            data = response.json()
            draft_id = data.get('draft', {}).get('draft_id')
            print(f"✓ Manual draft created: {draft_id}")
            
            # Validate the draft
            validation_response = requests.get(f"{API_BASE_URL}/drafts/{draft_id}/validate")
            if validation_response.ok:
                validation_data = validation_response.json()
                print(f"✓ Draft validation: {validation_data.get('validation', {})}")
            else:
                print(f"✗ Draft validation failed")
                
        else:
            print(f"✗ Manual draft creation failed: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

if __name__ == "__main__":
    print("🚀 Testing Phase 4: LLM Integration & Detection")
    print("=" * 50)
    
    test_draft_detection_via_chat()
    test_manual_draft_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Phase 4 testing complete!")
    print("\nTo test the frontend:")
    print("1. Start the backend: cd backend && python app.py")
    print("2. Start the frontend: cd frontend && npm start")
    print("3. Try queries like 'Create a draft email to John about the meeting'") 