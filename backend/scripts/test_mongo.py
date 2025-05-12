import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from utils.mongo_client import get_db
from models.conversation import Conversation
from config.mongo_config import CONVERSATIONS_COLLECTION

def test_mongo_connection():
    """Test MongoDB connection and basic operations"""
    try:
        # Test connection
        db = get_db()
        print("✅ Successfully connected to MongoDB")
        
        # Test insert
        test_thread_id = str(uuid.uuid4())
        conversation = Conversation(
            thread_id=test_thread_id,
            query="Test query",
            response="Test response"
        )
        conversation.save()
        print("✅ Successfully inserted test document")
        
        # Test retrieve
        messages = Conversation.get_by_thread_id(test_thread_id)
        print(f"✅ Successfully retrieved {len(messages)} messages for thread {test_thread_id}")
        
        # Test VeyraX data
        veyrax_conversation = Conversation(
            thread_id=test_thread_id,
            query="Test VeyraX query",
            response="Test VeyraX response",
            insight_id="test_insight_123"
        )
        veyrax_conversation.save()
        print("✅ Successfully inserted VeyraX test document")
        
        # Test list threads
        threads = Conversation.get_all_threads()
        print(f"✅ Successfully retrieved {len(threads)} threads")
        
        print("\nAll MongoDB tests completed successfully!")
        return True
    except Exception as e:
        print(f"❌ Error testing MongoDB connection: {str(e)}")
        raise

if __name__ == "__main__":
    test_mongo_connection() 