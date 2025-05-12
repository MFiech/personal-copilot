import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.mongo_client import get_db
from config.mongo_config import CONVERSATIONS_COLLECTION, CONVERSATIONS_INDEXES

def init_mongo_collections():
    """Initialize MongoDB collections and indexes"""
    try:
        # Get database connection
        db = get_db()
        print("✅ Connected to MongoDB successfully")
        
        # Initialize conversations collection
        if CONVERSATIONS_COLLECTION not in db.list_collection_names():
            db.create_collection(CONVERSATIONS_COLLECTION)
            print(f"✅ Created collection: {CONVERSATIONS_COLLECTION}")
        else:
            print(f"ℹ️ Collection {CONVERSATIONS_COLLECTION} already exists")
        
        # Create indexes
        collection = db[CONVERSATIONS_COLLECTION]
        for index_config in CONVERSATIONS_INDEXES:
            index_name = index_config['name']
            keys = index_config['keys']
            collection.create_index(keys, name=index_name)
            print(f"✅ Created index: {index_name}")
        
        print("\n🎉 MongoDB initialization completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error initializing MongoDB: {str(e)}")
        raise

if __name__ == "__main__":
    init_mongo_collections() 