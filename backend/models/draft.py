from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import DRAFTS_COLLECTION
import time
import uuid

class Draft:
    def __init__(self, draft_id=None, thread_id=None, message_id=None, draft_type=None,
                 status="active", to_emails=None, subject=None, body=None, attachments=None,
                 summary=None, start_time=None, end_time=None, attendees=None, location=None,
                 description=None, cc_emails=None, bcc_emails=None, gmail_thread_id=None,
                 reply_to_email_id=None, created_at=None, updated_at=None):
        self.draft_id = draft_id or str(uuid.uuid4())
        self.thread_id = thread_id
        self.message_id = message_id
        self.draft_type = draft_type  # "email" or "calendar_event"
        self.status = status  # "active", "closed", "composio_error"
        
        # Email-specific fields
        self.to_emails = to_emails or []
        self.subject = subject
        self.body = body
        self.attachments = attachments or []
        self.cc_emails = cc_emails or []
        self.bcc_emails = bcc_emails or []

        # Reply-specific fields
        self.gmail_thread_id = gmail_thread_id  # Gmail thread ID for replies
        self.reply_to_email_id = reply_to_email_id  # Email ID being replied to
        
        # Calendar-specific fields
        self.summary = summary
        self.start_time = start_time
        self.end_time = end_time
        self.attendees = attendees or []
        self.location = location
        self.description = description
        
        # Timestamps
        self.created_at = created_at if created_at is not None else int(time.time())
        self.updated_at = updated_at if updated_at is not None else int(time.time())
        self.collection = get_collection(DRAFTS_COLLECTION)

    def save(self):
        """Save draft to MongoDB with validation"""
        print(f"[Draft] Saving draft {self.draft_id} to database...")
        
        try:
            self.updated_at = int(time.time())
            
            draft_data = {
                'draft_id': self.draft_id,
                'thread_id': self.thread_id,
                'message_id': self.message_id,
                'draft_type': self.draft_type,
                'status': self.status,
                'to_emails': self.to_emails,
                'subject': self.subject,
                'body': self.body,
                'attachments': self.attachments,
                'cc_emails': self.cc_emails,
                'bcc_emails': self.bcc_emails,
                'gmail_thread_id': self.gmail_thread_id,
                'reply_to_email_id': self.reply_to_email_id,
                'summary': self.summary,
                'start_time': self.start_time,
                'end_time': self.end_time,
                'attendees': self.attendees,
                'location': self.location,
                'description': self.description,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
            
            print(f"[Draft] Draft data to save: {draft_data}")
            print(f"[Draft] Collection: {self.collection}")
            
            # Update if exists, insert if not
            print(f"[Draft] Performing upsert operation...")
            result = self.collection.update_one(
                {'draft_id': self.draft_id},
                {'$set': draft_data},
                upsert=True
            )
            
            print(f"[Draft] Upsert result: matched_count={result.matched_count}, modified_count={result.modified_count}, upserted_id={result.upserted_id}")
            
            saved_id = result.upserted_id or self.draft_id
            print(f"[Draft] ✅ Successfully saved draft {self.draft_id} to database")
            return saved_id
            
        except Exception as e:
            print(f"[Draft] ❌ Error saving draft {self.draft_id}: {e}")
            import traceback
            print(f"[Draft] ❌ Save traceback: {traceback.format_exc()}")
            raise e

    def update(self, updates):
        """Update specific fields of the draft"""
        self.updated_at = int(time.time())
        
        # Update instance attributes
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)
        
        # Add updated_at to the updates
        updates['updated_at'] = self.updated_at
        
        # Update in database
        result = self.collection.update_one(
            {'draft_id': self.draft_id},
            {'$set': updates}
        )
        return result.modified_count > 0

    @classmethod
    def get_by_id(cls, draft_id):
        """Get draft by its ID"""
        collection = get_collection(DRAFTS_COLLECTION)
        draft_data = collection.find_one({'draft_id': draft_id})
        if draft_data:
            return cls._from_dict(draft_data)
        return None

    @classmethod
    def get_by_message_id(cls, message_id):
        """Get draft by the message ID that created it"""
        collection = get_collection(DRAFTS_COLLECTION)
        draft_data = collection.find_one({'message_id': message_id})
        if draft_data:
            return cls._from_dict(draft_data)
        return None

    @classmethod
    def get_active_drafts_by_thread(cls, thread_id):
        """Get all active drafts in a thread"""
        collection = get_collection(DRAFTS_COLLECTION)
        drafts_data = list(collection.find({
            'thread_id': thread_id,
            'status': 'active'
        }).sort('created_at', -1))
        
        return [cls._from_dict(draft_data) for draft_data in drafts_data]

    @classmethod
    def get_all_drafts_by_thread(cls, thread_id):
        """Get all drafts in a thread (any status)"""
        collection = get_collection(DRAFTS_COLLECTION)
        drafts_data = list(collection.find({
            'thread_id': thread_id
        }).sort('created_at', -1))
        
        return [cls._from_dict(draft_data) for draft_data in drafts_data]

    def close_draft(self, status="closed"):
        """Close the draft with specified status"""
        if status not in ["closed", "composio_error"]:
            raise ValueError("Status must be 'closed' or 'composio_error'")
        
        self.status = status
        self.updated_at = int(time.time())
        
        result = self.collection.update_one(
            {'draft_id': self.draft_id},
            {'$set': {'status': status, 'updated_at': self.updated_at}}
        )
        return result.modified_count > 0

    def validate_completeness(self):
        """Check if draft has all required fields for Composio execution"""
        missing_fields = []

        if self.draft_type == "email":
            if not self.to_emails or len(self.to_emails) == 0:
                missing_fields.append("to_emails")
            # Subject is optional for reply drafts (gmail_thread_id is set)
            # Gmail automatically uses "Re: [original subject]" for replies
            if not self.subject and not self.gmail_thread_id:
                missing_fields.append("subject")
            if not self.body:
                missing_fields.append("body")
                
        elif self.draft_type == "calendar_event":
            if not self.summary:
                missing_fields.append("summary")
            if not self.start_time:
                missing_fields.append("start_time")
            if not self.end_time:
                missing_fields.append("end_time")
        
        return {
            "is_complete": len(missing_fields) == 0,
            "missing_fields": missing_fields
        }

    def to_dict(self):
        """Convert draft to dictionary"""
        return {
            'draft_id': self.draft_id,
            'thread_id': self.thread_id,
            'message_id': self.message_id,
            'draft_type': self.draft_type,
            'status': self.status,
            'to_emails': self.to_emails,
            'subject': self.subject,
            'body': self.body,
            'attachments': self.attachments,
            'cc_emails': self.cc_emails,
            'bcc_emails': self.bcc_emails,
            'gmail_thread_id': self.gmail_thread_id,
            'reply_to_email_id': self.reply_to_email_id,
            'summary': self.summary,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'attendees': self.attendees,
            'location': self.location,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def _from_dict(cls, data):
        """Create Draft instance from dictionary"""
        return cls(
            draft_id=data.get('draft_id'),
            thread_id=data.get('thread_id'),
            message_id=data.get('message_id'),
            draft_type=data.get('draft_type'),
            status=data.get('status', 'active'),
            to_emails=data.get('to_emails', []),
            subject=data.get('subject'),
            body=data.get('body'),
            attachments=data.get('attachments', []),
            cc_emails=data.get('cc_emails', []),
            bcc_emails=data.get('bcc_emails', []),
            gmail_thread_id=data.get('gmail_thread_id'),
            reply_to_email_id=data.get('reply_to_email_id'),
            summary=data.get('summary'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            attendees=data.get('attendees', []),
            location=data.get('location'),
            description=data.get('description'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )

    @classmethod
    def delete_by_id(cls, draft_id):
        """Delete draft by ID"""
        collection = get_collection(DRAFTS_COLLECTION)
        result = collection.delete_one({'draft_id': draft_id})
        return result.deleted_count > 0 