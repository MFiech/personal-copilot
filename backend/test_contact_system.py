#!/usr/bin/env python3
"""
Contact System Test Script

This script tests the contact system functionality including:
- Contact model operations
- Contact sync service
- Database operations
- Composio integration (mock)
"""

import sys
import os
import time

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.contact import Contact
from models.contact_sync_log import ContactSyncLog
from services.contact_service import ContactSyncService

def test_contact_model():
    """Test the Contact model functionality"""
    print("=== Testing Contact Model ===")
    
    try:
        # Test contact creation
        print("1. Testing contact creation...")
        contact = Contact(
            emails="test@example.com",
            name="Test User",
            phone="+1234567890",
            source="manual",
            metadata={"test": True}
        )
        
        contact_id = contact.save()
        print(f"✓ Created contact with ID: {contact_id}")
        
        # Test contact retrieval
        print("2. Testing contact retrieval...")
        retrieved_contact = Contact.get_by_email("test@example.com")
        if retrieved_contact:
            print(f"✓ Retrieved contact: {retrieved_contact['name']} ({retrieved_contact['primary_email']})")
        else:
            print("✗ Failed to retrieve contact")
            return False
        
        # Test contact search
        print("3. Testing contact search...")
        search_results = Contact.search_by_name("Test", limit=5)
        print(f"✓ Found {len(search_results)} contacts matching 'Test'")
        
        # Test contact stats
        print("4. Testing contact statistics...")
        stats = Contact.get_stats()
        print(f"✓ Contact stats: {stats}")
        
        # Test contact deduplication (create duplicate)
        print("5. Testing contact deduplication...")
        duplicate_contact = Contact(
            emails="test@example.com",  # Same email
            name="Test User Updated",  # Updated name
            phone="+0987654321",       # Updated phone
            source="gmail_contacts"
        )
        
        duplicate_id = duplicate_contact.save()
        print(f"✓ Deduplication test: {duplicate_id} (should be same as {contact_id})")
        
        # Check if contact was updated
        updated_contact = Contact.get_by_email("test@example.com")
        if updated_contact and updated_contact['name'] == "Test User Updated":
            print("✓ Contact was properly updated through deduplication")
        else:
            print("✗ Contact deduplication failed")
        
        return True
        
    except Exception as e:
        print(f"✗ Contact model test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_contact_sync_log():
    """Test the ContactSyncLog model functionality"""
    print("\n=== Testing Contact Sync Log Model ===")
    
    try:
        # Test sync log creation
        print("1. Testing sync log creation...")
        sync_log = ContactSyncLog(sync_type="gmail_contacts")
        sync_log.start_sync()
        print(f"✓ Created sync log with ID: {sync_log.sync_id}")
        
        # Test adding errors
        print("2. Testing error logging...")
        sync_log.add_error("Test error message", {"test": "data"})
        print("✓ Added error to sync log")
        
        # Test completing sync
        print("3. Testing sync completion...")
        stats = {
            'total_fetched': 10,
            'total_processed': 9,
            'new_contacts': 5,
            'updated_contacts': 4
        }
        sync_log.complete_sync(stats)
        print(f"✓ Completed sync with status: {sync_log.status}")
        
        # Test retrieving sync history
        print("4. Testing sync history retrieval...")
        history = ContactSyncLog.get_sync_history(limit=5)
        print(f"✓ Retrieved {len(history)} sync log entries")
        
        return True
        
    except Exception as e:
        print(f"✗ Contact sync log test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_contact_service():
    """Test the ContactSyncService functionality"""
    print("\n=== Testing Contact Service ===")
    
    try:
        # Initialize contact service
        print("1. Testing contact service initialization...")
        contact_service = ContactSyncService()
        print("✓ Contact service initialized")
        
        # Test contact stats
        print("2. Testing contact statistics...")
        stats = contact_service.get_contact_stats()
        print(f"✓ Service stats: {stats}")
        
        # Test contact search
        print("3. Testing contact search...")
        search_results = contact_service.search_contacts("test", limit=5)
        print(f"✓ Search found {len(search_results)} contacts")
        
        # Test getting all contacts
        print("4. Testing get all contacts...")
        all_contacts = contact_service.get_all_contacts(limit=10)
        print(f"✓ Retrieved {len(all_contacts)} contacts")
        
        # Test sync status
        print("5. Testing sync status...")
        sync_status = contact_service.get_sync_status()
        if 'error' not in sync_status:
            print(f"✓ Latest sync status: {sync_status}")
        else:
            print(f"✓ No previous sync found (expected): {sync_status['error']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Contact service test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def test_mock_composio_integration():
    """Test mock Composio integration"""
    print("\n=== Testing Mock Composio Integration ===")
    
    try:
        contact_service = ContactSyncService()
        
        # Test the contact data processing function
        print("1. Testing contact data processing...")
        
        # Mock Google People API response format
        mock_contact_data = {
            "resourceName": "people/c123456789",
            "etag": "test_etag",
            "names": [
                {
                    "metadata": {"primary": True},
                    "displayName": "John Doe",
                    "givenName": "John",
                    "familyName": "Doe"
                }
            ],
            "emailAddresses": [
                {
                    "metadata": {"primary": True},
                    "value": "john.doe@example.com"
                }
            ],
            "phoneNumbers": [
                {
                    "metadata": {"primary": True},
                    "value": "+1-555-123-4567"
                }
            ]
        }
        
        # Test processing contact data
        result = contact_service._process_contact_data(mock_contact_data)
        print(f"✓ Processed contact: {result}")
        
        # Test converting to dict format
        contact_dict = contact_service._process_contact_data_to_dict(mock_contact_data)
        print(f"✓ Converted to dict: {contact_dict}")
        
        return True
        
    except Exception as e:
        print(f"✗ Mock Composio integration test failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def cleanup_test_data():
    """Clean up test data"""
    print("\n=== Cleaning Up Test Data ===")
    
    try:
        # Delete test contacts
        contact_service = ContactSyncService()
        
        # Find and delete test contacts
        test_contacts = Contact.get_all(limit=1000)
        deleted_count = 0
        
        for contact in test_contacts:
            if 'test' in contact.get('email', '').lower() or 'example.com' in contact.get('email', ''):
                from utils.mongo_client import get_collection
                from config.mongo_config import CONTACTS_COLLECTION
                collection = get_collection(CONTACTS_COLLECTION)
                collection.delete_one({'email': contact['email']})
                deleted_count += 1
        
        print(f"✓ Deleted {deleted_count} test contacts")
        
        # Clean up test sync logs
        from utils.mongo_client import get_collection
        from config.mongo_config import CONTACT_SYNC_LOG_COLLECTION
        sync_log_collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        result = sync_log_collection.delete_many({'sync_type': 'test_sync'})
        print(f"✓ Deleted {result.deleted_count} test sync logs")
        
        return True
        
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Starting Contact System Tests\n")
    
    tests = [
        ("Contact Model", test_contact_model),
        ("Contact Sync Log", test_contact_sync_log),
        ("Contact Service", test_contact_service),
        ("Mock Composio Integration", test_mock_composio_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            if test_func():
                print(f"\n✅ {test_name} - PASSED")
                passed += 1
            else:
                print(f"\n❌ {test_name} - FAILED")
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} - ERROR: {e}")
            failed += 1
    
    # Cleanup
    print(f"\n{'='*50}")
    print("Cleanup")
    print('='*50)
    cleanup_test_data()
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Total:  {passed + failed}")
    
    if failed == 0:
        print("\n🎉 All tests passed! Contact system is ready to use.")
        return True
    else:
        print(f"\n⚠️  {failed} test(s) failed. Please check the errors above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 