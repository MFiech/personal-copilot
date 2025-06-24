import os
import sys
import uuid
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mongo_client import get_db
from config.mongo_config import CONVERSATIONS_COLLECTION
from config.mongo_schema import CONVERSATIONS_SCHEMA, CONVERSATIONS_INDEXES

def migrate_schema():
    """Migrate the conversations collection to the new schema"""
    try:
        db = get_db()
        collection = db[CONVERSATIONS_COLLECTION]
        
        print("Starting schema migration...")
        
        # Drop existing collection
        print("Dropping existing collection...")
        db.drop_collection(CONVERSATIONS_COLLECTION)
        
        # Create new collection with updated schema
        print("Creating new collection with updated schema...")
        db.create_collection(
            CONVERSATIONS_COLLECTION,
            **CONVERSATIONS_SCHEMA
        )
        
        # Create indexes
        print("Creating indexes...")
        for index_config in CONVERSATIONS_INDEXES:
            collection.create_index(**index_config)
            print(f"Created index: {index_config['name']}")
        
        print("\nSchema migration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during schema migration: {str(e)}")
        raise

if __name__ == "__main__":
    migrate_schema() 