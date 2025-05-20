from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import CONVERSATIONS_COLLECTION
import time
import uuid

EMAILS_COLLECTION = 'emails'

class Conversation:
    def __init__(self, thread_id=None, role=None, content=None, insight_id=None, metadata=None, veyra_results=None, query=None, response=None,
                 veyra_original_query_params=None, veyra_current_offset=None, veyra_limit_per_page=None, veyra_total_emails_available=None,
                 veyra_has_more=None):
        self.thread_id = thread_id
        self.role = role
        self.content = content
        
        # For backward compatibility - map query/response to role/content if used
        if query is not None and role is None:
            self.role = 'user'
            self.content = query
        elif response is not None and role is None:
            self.role = 'assistant'
            self.content = response
        
        self.insight_id = insight_id
        self.metadata = metadata
        self.veyra_results = veyra_results
        self.veyra_original_query_params = veyra_original_query_params
        self.veyra_current_offset = veyra_current_offset
        self.veyra_limit_per_page = veyra_limit_per_page
        self.veyra_total_emails_available = veyra_total_emails_available
        self.veyra_has_more = veyra_has_more
        self.timestamp = int(time.time())
        self.message_id = None  # Will be set after save
        self.collection = get_collection(CONVERSATIONS_COLLECTION)

    def save(self):
        """Save conversation to MongoDB with validation"""
        self.message_id = str(uuid.uuid4())
        if self.content is None:
            print(f"Warning: Conversation content was None for role '{self.role}'. Setting to empty string.")
            self.content = ""
        message = {
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'role': self.role,
            'content': self.content,
            'timestamp': self.timestamp,
            'metadata': self.metadata or {}
        }
        if self.insight_id:
            message['insight_id'] = self.insight_id
        # If veyra_results is present, ensure emails is a list of IDs
        if self.veyra_results:
            veyra_results = self.veyra_results.copy()
            if 'emails' in veyra_results and veyra_results['emails']:
                email_ids = []
                emails_collection = get_collection(EMAILS_COLLECTION)
                for email in veyra_results['emails']:
                    if isinstance(email, dict) and 'id' in email:
                        # Insert email into emails collection if not present
                        if not emails_collection.find_one({'id': email['id']}):
                            emails_collection.insert_one(email)
                        email_ids.append(email['id'])
                    elif isinstance(email, str):
                        email_ids.append(email)
                veyra_results['emails'] = email_ids
            message['veyra_results'] = veyra_results
        if self.veyra_original_query_params is not None:
            message['veyra_original_query_params'] = self.veyra_original_query_params
        if self.veyra_current_offset is not None:
            message['veyra_current_offset'] = self.veyra_current_offset
        if self.veyra_limit_per_page is not None:
            message['veyra_limit_per_page'] = self.veyra_limit_per_page
        if self.veyra_total_emails_available is not None:
            message['veyra_total_emails_available'] = self.veyra_total_emails_available
        if self.veyra_has_more is not None:
            message['veyra_has_more'] = self.veyra_has_more
        return self.collection.insert_one(message)

    @classmethod
    def get_by_thread_id(cls, thread_id):
        """Get all messages in a thread"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        messages = list(collection.find({'thread_id': thread_id}).sort('timestamp', 1))
        emails_collection = get_collection(EMAILS_COLLECTION)
        formatted_messages = []
        for msg in messages:
            formatted_message = {
                'message_id': msg.get('message_id'),
                'role': msg['role'],
                'content': msg['content'],
                'timestamp': msg['timestamp']
            }
            if msg['role'] == 'assistant' and 'veyra_results' in msg:
                veyra_results = msg['veyra_results']
                if veyra_results and 'emails' in veyra_results:
                    email_ids = veyra_results['emails']
                    emails = list(emails_collection.find({'id': {'$in': email_ids}})) if email_ids else []
                    veyra_results = veyra_results.copy()
                    veyra_results['emails'] = emails
                formatted_message['veyra_results'] = veyra_results
            formatted_messages.append(formatted_message)
        return formatted_messages

    @classmethod
    def get_all_threads(cls):
        """Get all unique thread IDs"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return list(collection.distinct('thread_id'))

    @classmethod
    def get_by_insight_id(cls, insight_id):
        """Get conversation by insight ID"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return collection.find_one({'insight_id': insight_id})

    @classmethod
    def get_by_source(cls, source):
        """Get conversations by source type"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return list(collection.find({'metadata.source': source}).sort('timestamp', -1))

    @classmethod
    def get_by_tags(cls, tags):
        """Get conversations by tags"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return list(collection.find({'metadata.tags': {'$in': tags}}).sort('timestamp', -1))

    @classmethod
    def add_tag(cls, thread_id, tag):
        """Add a tag to a conversation thread"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return collection.update_many(
            {'thread_id': thread_id},
            {'$addToSet': {'metadata.tags': tag}}
        )

    @classmethod
    def remove_tag(cls, thread_id, tag):
        """Remove a tag from a conversation thread"""
        collection = get_collection(CONVERSATIONS_COLLECTION)
        return collection.update_many(
            {'thread_id': thread_id},
            {'$pull': {'metadata.tags': tag}}
        )

    @classmethod
    def remove_email_from_results(cls, thread_id, message_id):
        try:
            # Find the message containing the email
            message = cls.collection.find_one({
                'thread_id': thread_id,
                'veyra_results.emails.message_id': message_id
            })
            
            if not message:
                print(f"Message not found for thread_id: {thread_id}, message_id: {message_id}")
                return False
                
            # Update the message to remove the email
            result = cls.collection.update_one(
                {
                    'thread_id': thread_id,
                    'veyra_results.emails.message_id': message_id
                },
                {
                    '$pull': {
                        'veyra_results.emails': {'message_id': message_id}
                    }
                }
            )
            
            success = result.modified_count > 0
            print(f"Updated message in MongoDB: {result.modified_count} documents modified")
            
            if success:
                print(f"Successfully deleted email {message_id} from thread {thread_id}")
            else:
                print(f"Failed to delete email {message_id} from thread {thread_id}")
                
            return success
            
        except Exception as e:
            print(f"Error removing email from results: {e}")
            return False

    @classmethod
    def update_one(cls, filter_query, update_query):
        """
        Update a single conversation document.
        
        Args:
            filter_query (dict): Filter criteria for finding the document
            update_query (dict): Update operations to perform
            
        Returns:
            UpdateResult: MongoDB update result
        """
        try:
            collection = get_collection(CONVERSATIONS_COLLECTION)
            result = collection.update_one(filter_query, update_query)
            print(f"MongoDB update result: {result.matched_count} matches, {result.modified_count} modified")
            return result
        except Exception as e:
            print(f"Error in update_one: {str(e)}")
            raise
            
    @classmethod
    def find_one(cls, filter_query):
        """
        Find a single conversation document.
        
        Args:
            filter_query (dict): Filter criteria for finding the document
            
        Returns:
            dict: MongoDB document or None
        """
        try:
            collection = get_collection(CONVERSATIONS_COLLECTION)
            result = collection.find_one(filter_query)
            return result
        except Exception as e:
            print(f"Error in find_one: {str(e)}")
            return None 