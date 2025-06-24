from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import EMAILS_COLLECTION
import time
import uuid

class Email:
    def __init__(self, email_id=None, thread_id=None, subject=None, from_email=None, to_emails=None,
                 date=None, content=None, metadata=None):
        self.email_id = email_id or str(uuid.uuid4())
        self.thread_id = thread_id
        self.subject = subject
        self.from_email = from_email
        self.to_emails = to_emails or []
        self.date = date
        self.content = content or {"html": "", "text": ""}
        self.metadata = metadata or {}
        self.created_at = int(time.time())
        self.updated_at = int(time.time())
        self.collection = get_collection(EMAILS_COLLECTION)

    def save(self):
        """Save email to MongoDB with validation"""
        email_data = {
            'email_id': self.email_id,
            'thread_id': self.thread_id,
            'subject': self.subject,
            'from_email': self.from_email,
            'to_emails': self.to_emails,
            'date': self.date,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        # Update if exists, insert if not
        result = self.collection.update_one(
            {'email_id': self.email_id},
            {'$set': email_data},
            upsert=True
        )
        return result.upserted_id or self.email_id

    @classmethod
    def get_by_id(cls, email_id):
        """Get email by its ID"""
        collection = get_collection(EMAILS_COLLECTION)
        return collection.find_one({'email_id': email_id})

    @classmethod
    def get_by_thread_id(cls, thread_id):
        """Get all emails in a thread"""
        collection = get_collection(EMAILS_COLLECTION)
        return list(collection.find({'thread_id': thread_id}).sort('date', -1))

    @classmethod
    def get_by_sender(cls, email):
        """Get all emails from a specific sender"""
        collection = get_collection(EMAILS_COLLECTION)
        return list(collection.find({'from_email.email': email}).sort('date', -1))

    @classmethod
    def get_by_tags(cls, tags):
        """Get emails by tags"""
        collection = get_collection(EMAILS_COLLECTION)
        return list(collection.find({'metadata.tags': {'$in': tags}}).sort('date', -1))

    @classmethod
    def add_tag(cls, email_id, tag):
        """Add a tag to an email"""
        collection = get_collection(EMAILS_COLLECTION)
        return collection.update_one(
            {'email_id': email_id},
            {
                '$addToSet': {'metadata.tags': tag},
                '$set': {'updated_at': int(time.time())}
            }
        )

    @classmethod
    def remove_tag(cls, email_id, tag):
        """Remove a tag from an email"""
        collection = get_collection(EMAILS_COLLECTION)
        return collection.update_one(
            {'email_id': email_id},
            {
                '$pull': {'metadata.tags': tag},
                '$set': {'updated_at': int(time.time())}
            }
        )

    @classmethod
    def update_summary(cls, email_id, summary):
        """Update the AI-generated summary of an email"""
        collection = get_collection(EMAILS_COLLECTION)
        return collection.update_one(
            {'email_id': email_id},
            {
                '$set': {
                    'metadata.summary': summary,
                    'updated_at': int(time.time())
                }
            }
        )

    @classmethod
    def delete(cls, email_id):
        """Delete an email"""
        collection = get_collection(EMAILS_COLLECTION)
        result = collection.delete_one({'email_id': email_id})
        return result.deleted_count > 0

    @classmethod
    def bulk_delete(cls, email_ids):
        """Delete multiple emails"""
        collection = get_collection(EMAILS_COLLECTION)
        result = collection.delete_many({'email_id': {'$in': email_ids}})
        return result.deleted_count 