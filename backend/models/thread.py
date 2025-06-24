from datetime import datetime
from utils.mongo_client import get_db
from bson import ObjectId
import time

class Thread:
    def __init__(self, thread_id=None, title="New Thread", created_at=None):
        self.thread_id = thread_id or str(ObjectId())
        self.title = title
        # Convert to epoch timestamp
        self.created_at = created_at or int(time.time())
        self.updated_at = int(time.time())
    
    def save(self):
        db = get_db()
        thread_data = {
            "thread_id": self.thread_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        
        # Update if exists, insert if not
        db.threads.update_one(
            {"thread_id": self.thread_id}, 
            {"$set": thread_data}, 
            upsert=True
        )
        return self.thread_id
    
    @classmethod
    def get_by_id(cls, thread_id):
        db = get_db()
        thread = db.threads.find_one({"thread_id": thread_id})
        return thread
    
    @classmethod
    def get_all(cls):
        db = get_db()
        return list(db.threads.find().sort("updated_at", -1))
    
    @classmethod
    def update_title(cls, thread_id, new_title):
        db = get_db()
        db.threads.update_one(
            {"thread_id": thread_id},
            {"$set": {"title": new_title, "updated_at": int(time.time())}}
        )
        return True 

    @classmethod
    def delete(cls, thread_id):
        """Delete a thread and all its conversations"""
        db = get_db()
        # Delete the thread
        thread_result = db.threads.delete_one({"thread_id": thread_id})
        # Delete all conversations in the thread
        conversation_result = db.conversations.delete_many({"thread_id": thread_id})
        return thread_result.deleted_count > 0 and conversation_result.deleted_count >= 0 