#!/usr/bin/env python3
"""
Test script for the new email content retrieval functionality.
This script tests the /get_email_content endpoint.
"""

import requests
import json

def test_get_email_content():
    """Test the get_email_content endpoint."""
    
    # Test data - you'll need to replace this with a real email ID from your system
    test_email_id = "test_email_id_123"
    
    print("Testing /get_email_content endpoint...")
    print(f"Using test email ID: {test_email_id}")
    
    try:
        # Make request to the endpoint
        response = requests.post(
            'http://localhost:5001/get_email_content',
            headers={'Content-Type': 'application/json'},
            json={'email_id': test_email_id}
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Response:")
            print(json.dumps(data, indent=2))
        else:
            print("❌ Error response:")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection error: Make sure the backend server is running on port 5001")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

def test_with_real_email_id():
    """Test with a real email ID from the database."""
    
    print("\n" + "="*50)
    print("To test with a real email ID:")
    print("1. Start the backend server: python app.py")
    print("2. Query for emails in the frontend")
    print("3. Get an email ID from the database or logs")
    print("4. Update the test_email_id variable in this script")
    print("5. Run this test again")

if __name__ == "__main__":
    test_get_email_content()
    test_with_real_email_id() 