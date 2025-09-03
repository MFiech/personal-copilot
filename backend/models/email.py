from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import EMAILS_COLLECTION
import time
import uuid

class Email:
    def __init__(self, email_id=None, thread_id=None, gmail_thread_id=None, subject=None, from_email=None, to_emails=None,
                 date=None, content=None, metadata=None):
        self.email_id = email_id or str(uuid.uuid4())
        self.thread_id = thread_id
        self.gmail_thread_id = gmail_thread_id
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
        print(f"[DEBUG EMAIL SAVE] Saving email with gmail_thread_id: {self.gmail_thread_id}")
        email_data = {
            'email_id': self.email_id,
            'thread_id': self.thread_id,
            'gmail_thread_id': self.gmail_thread_id,
            'subject': self.subject,
            'from_email': self.from_email,
            'to_emails': self.to_emails,
            'date': self.date,
            'content': self.content,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
        
        print(f"[DEBUG EMAIL SAVE] Final email_data before MongoDB insert: {email_data}")
        print(f"[DEBUG EMAIL SAVE] gmail_thread_id value: {email_data.get('gmail_thread_id')}")
        
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

    @classmethod
    def get_by_gmail_thread_id(cls, gmail_thread_id):
        """Get all emails in a Gmail thread, sorted by date (oldest first)"""
        collection = get_collection(EMAILS_COLLECTION)
        return list(collection.find({'gmail_thread_id': gmail_thread_id}).sort('date', 1))

    @classmethod
    def get_gmail_threads_grouped(cls, limit=50):
        """Get emails grouped by Gmail thread ID with thread metadata"""
        collection = get_collection(EMAILS_COLLECTION)
        
        # Aggregation pipeline to group by gmail_thread_id and get thread metadata
        pipeline = [
            # Match emails that have gmail_thread_id
            {'$match': {'gmail_thread_id': {'$ne': None, '$exists': True}}},
            # Sort by date descending to get latest first
            {'$sort': {'date': -1}},
            # Group by gmail_thread_id
            {'$group': {
                '_id': '$gmail_thread_id',
                'emails': {'$push': '$$ROOT'},
                'email_count': {'$sum': 1},
                'latest_date': {'$first': '$date'},
                'earliest_date': {'$last': '$date'},
                'latest_subject': {'$first': '$subject'},
                'participants': {'$addToSet': '$from_email.email'}
            }},
            # Sort by latest date descending
            {'$sort': {'latest_date': -1}},
            # Limit results
            {'$limit': limit}
        ]
        
        result = list(collection.aggregate(pipeline))
        
        # Also get individual emails (not part of any Gmail thread)
        individual_emails = list(collection.find({
            '$or': [
                {'gmail_thread_id': None},
                {'gmail_thread_id': {'$exists': False}}
            ]
        }).sort('date', -1).limit(limit))
        
        # Convert ObjectIds to strings in the result
        processed_result = {
            'gmail_threads': [],
            'individual_emails': []
        }
        
        # Process thread groups
        for thread in result:
            processed_thread = {
                '_id': str(thread['_id']) if thread['_id'] else None,
                'emails': [],
                'email_count': thread['email_count'],
                'latest_date': thread['latest_date'],
                'earliest_date': thread['earliest_date'],
                'latest_subject': thread['latest_subject'],
                'participants': thread['participants']
            }
            
            # Process emails in the thread
            for email in thread['emails']:
                processed_email = {
                    'email_id': email.get('email_id'),  # Use the actual email_id field
                    'thread_id': email.get('thread_id'),
                    'gmail_thread_id': email.get('gmail_thread_id'),
                    'subject': email.get('subject'),
                    'from_email': email.get('from_email'),
                    'to_emails': email.get('to_emails'),
                    'date': email.get('date'),
                    'content': email.get('content'),
                    'metadata': email.get('metadata'),
                    'created_at': email.get('created_at'),
                    'updated_at': email.get('updated_at')
                }
                processed_thread['emails'].append(processed_email)
            
            processed_result['gmail_threads'].append(processed_thread)
        
        # Process individual emails
        for email in individual_emails:
            processed_email = {
                'email_id': email.get('email_id'),  # Use the actual email_id field
                'thread_id': email.get('thread_id'),
                'gmail_thread_id': email.get('gmail_thread_id'),
                'subject': email.get('subject'),
                'from_email': email.get('from_email'),
                'to_emails': email.get('to_emails'),
                'date': email.get('date'),
                'content': email.get('content'),
                'metadata': email.get('metadata'),
                'created_at': email.get('created_at'),
                'updated_at': email.get('updated_at')
            }
            processed_result['individual_emails'].append(processed_email)
        
        return processed_result 