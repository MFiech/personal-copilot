#!/usr/bin/env python3
"""
Contact Database Initialization Script

This script initializes the contact-related collections and indexes in MongoDB.
Run this script once to set up the contact system database structure.
"""

import sys
import os

# Add the backend directory to the path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mongo_client import get_db
from config.mongo_config import (
    CONTACTS_COLLECTION, 
    CONTACT_SYNC_LOG_COLLECTION
)
from config.mongo_schema import (
    CONTACTS_SCHEMA, 
    CONTACT_SYNC_LOG_SCHEMA,
    CONTACTS_INDEXES,
    CONTACT_SYNC_LOG_INDEXES
)

def init_contact_collections():
    """Initialize contact-related MongoDB collections with schemas and indexes"""
    try:
        print("=== Contact Database Initialization ===")
        
        # Get database connection
        db = get_db()
        print(f"Connected to database: {db.name}")
        
        # Initialize contacts collection
        print(f"\n1. Initializing '{CONTACTS_COLLECTION}' collection...")
        
        # Create collection with schema validation
        try:
            db.create_collection(CONTACTS_COLLECTION, validator=CONTACTS_SCHEMA["validator"])
            print(f"✓ Created '{CONTACTS_COLLECTION}' collection with schema validation")
        except Exception as e:
            if "already exists" in str(e):
                print(f"✓ Collection '{CONTACTS_COLLECTION}' already exists")
                # Update schema validation for existing collection
                db.command("collMod", CONTACTS_COLLECTION, validator=CONTACTS_SCHEMA["validator"])
                print(f"✓ Updated schema validation for '{CONTACTS_COLLECTION}'")
            else:
                raise e
        
        # Create indexes for contacts collection
        contacts_collection = db[CONTACTS_COLLECTION]
        for index_config in CONTACTS_INDEXES:
            try:
                contacts_collection.create_index(
                    list(index_config["keys"]), 
                    name=index_config["name"],
                    unique=index_config.get("unique", False)
                )
                print(f"✓ Created index '{index_config['name']}' on '{CONTACTS_COLLECTION}'")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✓ Index '{index_config['name']}' already exists on '{CONTACTS_COLLECTION}'")
                else:
                    print(f"✗ Failed to create index '{index_config['name']}': {e}")
        
        # Initialize contact sync log collection
        print(f"\n2. Initializing '{CONTACT_SYNC_LOG_COLLECTION}' collection...")
        
        # Create collection with schema validation
        try:
            db.create_collection(CONTACT_SYNC_LOG_COLLECTION, validator=CONTACT_SYNC_LOG_SCHEMA["validator"])
            print(f"✓ Created '{CONTACT_SYNC_LOG_COLLECTION}' collection with schema validation")
        except Exception as e:
            if "already exists" in str(e):
                print(f"✓ Collection '{CONTACT_SYNC_LOG_COLLECTION}' already exists")
                # Update schema validation for existing collection
                db.command("collMod", CONTACT_SYNC_LOG_COLLECTION, validator=CONTACT_SYNC_LOG_SCHEMA["validator"])
                print(f"✓ Updated schema validation for '{CONTACT_SYNC_LOG_COLLECTION}'")
            else:
                raise e
        
        # Create indexes for contact sync log collection
        sync_log_collection = db[CONTACT_SYNC_LOG_COLLECTION]
        for index_config in CONTACT_SYNC_LOG_INDEXES:
            try:
                sync_log_collection.create_index(
                    list(index_config["keys"]), 
                    name=index_config["name"],
                    unique=index_config.get("unique", False)
                )
                print(f"✓ Created index '{index_config['name']}' on '{CONTACT_SYNC_LOG_COLLECTION}'")
            except Exception as e:
                if "already exists" in str(e):
                    print(f"✓ Index '{index_config['name']}' already exists on '{CONTACT_SYNC_LOG_COLLECTION}'")
                else:
                    print(f"✗ Failed to create index '{index_config['name']}': {e}")
        
        print(f"\n=== Contact Database Initialization Complete ===")
        print(f"✓ Collections created: {CONTACTS_COLLECTION}, {CONTACT_SYNC_LOG_COLLECTION}")
        print(f"✓ Indexes created: {len(CONTACTS_INDEXES)} for contacts, {len(CONTACT_SYNC_LOG_INDEXES)} for sync logs")
        print(f"✓ Schema validation enabled for both collections")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Contact database initialization failed: {e}")
        import traceback
        print(traceback.format_exc())
        return False

def check_contact_collections():
    """Check if contact collections exist and are properly configured"""
    try:
        print("=== Contact Database Status Check ===")
        
        db = get_db()
        
        # Check contacts collection
        if CONTACTS_COLLECTION in db.list_collection_names():
            contacts_collection = db[CONTACTS_COLLECTION]
            contact_count = contacts_collection.count_documents({})
            indexes = list(contacts_collection.list_indexes())
            print(f"✓ '{CONTACTS_COLLECTION}' collection exists with {contact_count} documents and {len(indexes)} indexes")
        else:
            print(f"✗ '{CONTACTS_COLLECTION}' collection does not exist")
        
        # Check contact sync log collection
        if CONTACT_SYNC_LOG_COLLECTION in db.list_collection_names():
            sync_log_collection = db[CONTACT_SYNC_LOG_COLLECTION]
            log_count = sync_log_collection.count_documents({})
            indexes = list(sync_log_collection.list_indexes())
            print(f"✓ '{CONTACT_SYNC_LOG_COLLECTION}' collection exists with {log_count} documents and {len(indexes)} indexes")
        else:
            print(f"✗ '{CONTACT_SYNC_LOG_COLLECTION}' collection does not exist")
        
        print("=== Status Check Complete ===")
        
    except Exception as e:
        print(f"✗ Status check failed: {e}")

def main():
    """Main function to run the contact database initialization"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Initialize contact database collections')
    parser.add_argument('--check', action='store_true', help='Only check status, do not initialize')
    parser.add_argument('--force', action='store_true', help='Force re-initialization even if collections exist')
    
    args = parser.parse_args()
    
    if args.check:
        check_contact_collections()
    else:
        print("Starting contact database initialization...")
        if init_contact_collections():
            print("\n🎉 Contact database initialization successful!")
            print("\nYou can now:")
            print("1. Start syncing contacts with: POST /contacts/sync")
            print("2. Search contacts with: POST /contacts/search")
            print("3. View contacts with: GET /contacts")
        else:
            print("\n❌ Contact database initialization failed!")
            sys.exit(1)

if __name__ == "__main__":
    main() 