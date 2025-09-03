from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import CONVERSATIONS_COLLECTION
from models.email import Email
from utils.date_parser import parse_email_date
import time
import uuid
import json

EMAILS_COLLECTION = 'emails'

print("THIS IS conversation.py VERSION 000 - VERY TOP OF FILE")

class Conversation:
    def __init__(self, thread_id=None, role=None, content=None, insight_id=None, metadata=None, tool_results=None, query=None, response=None, timestamp=None):
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
        self.metadata = metadata if metadata is not None else {}
        self.tool_results = tool_results if tool_results is not None else {}
        
        # Use provided timestamp or generate new one
        self.timestamp = timestamp if timestamp is not None else int(time.time())
        self.message_id = None  # Will be set after save
        self.collection = get_collection(CONVERSATIONS_COLLECTION)

    def save(self):
        """Save conversation to MongoDB, processing and linking emails from tool_results."""
        print(f"[DEBUG SAVE] Starting save() method for thread_id: {self.thread_id}")
        print(f"[DEBUG SAVE] tool_results keys: {list(self.tool_results.keys()) if self.tool_results else 'No tool_results'}")
        self.message_id = str(uuid.uuid4())
        
        message = {
            'message_id': self.message_id,
            'thread_id': self.thread_id,
            'role': self.role,
            'content': self.content or "",
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }

        if self.insight_id:
            message['insight_id'] = self.insight_id

        # Add pagination fields if they exist in metadata
        if self.metadata:
            for field in ['tool_original_query_params', 'tool_current_offset', 'tool_limit_per_page', 'tool_total_emails_available', 'tool_has_more']:
                if field in self.metadata:
                    message[field] = self.metadata[field]

        if 'emails' in self.tool_results and self.tool_results['emails']:
            print(f"[DEBUG SAVE] Processing {len(self.tool_results['emails'])} emails from tool_results")
            processed_email_ids = []
            emails_collection = get_collection(EMAILS_COLLECTION)
            
            for idx, email_data in enumerate(self.tool_results['emails']):
                print(f"[DEBUG SAVE] Processing email {idx + 1}: type={type(email_data)}")
                if isinstance(email_data, dict):
                    print(f"[DEBUG SAVE] Email {idx + 1} keys: {list(email_data.keys())}")
                else:
                    print(f"[DEBUG SAVE] Email {idx + 1} is not a dict: {email_data}")
                if not isinstance(email_data, dict) or 'id' not in email_data:
                    if isinstance(email_data, str):
                        processed_email_ids.append(email_data)
                    continue

                from_info = email_data.get('from_email', {})
                email_id = email_data['id'].strip()
                
                # DEBUG: Check for Gmail thread ID in different locations
                gmail_thread_id = None
                if 'threadId' in email_data:
                    gmail_thread_id = email_data['threadId']
                    print(f"[DEBUG] Found threadId in email_data: {gmail_thread_id}")
                elif 'gmail_thread_id' in email_data:
                    gmail_thread_id = email_data['gmail_thread_id']
                    print(f"[DEBUG] Found gmail_thread_id in email_data: {gmail_thread_id}")
                else:
                    print(f"[DEBUG] No threadId found in email_data keys: {list(email_data.keys())}")

                print(f"[DEBUG SAVE] Creating Email object with gmail_thread_id: {gmail_thread_id}")
                email_doc = Email(
                    email_id=email_id,
                    thread_id=self.thread_id,
                    gmail_thread_id=gmail_thread_id,  # Use the extracted Gmail thread ID
                    subject=email_data.get('subject', ''),
                    from_email={
                        'email': from_info.get('email', ''),
                        'name': from_info.get('name') or (from_info.get('email', '').split('@')[0] if '@' in from_info.get('email', '') else '')
                    },
                    to_emails=[
                        {'email': r.get('email', ''), 'name': r.get('name')}
                        for r in email_data.get('to', [])
                    ],
                    date=email_data.get('date'),
                    content=email_data.get('content', {"html": "", "text": ""}),
                    metadata={
                        'source': 'TOOL',
                        'folder': email_data.get('folder'),
                        'is_read': email_data.get('is_read'),
                    }
                )
                print(f"[DEBUG SAVE] About to save Email object to database")
                email_doc.save()
                print(f"[DEBUG SAVE] Email object saved successfully")
                processed_email_ids.append(email_id)
            
            self.tool_results['emails'] = processed_email_ids

        if self.tool_results:
            message['tool_results'] = self.tool_results

        return self.collection.insert_one(message)

    @classmethod
    def get_by_thread_id(cls, thread_id):
        """Get all messages in a thread"""
        print(f"\n=== [LOG] Starting get_by_thread_id for thread_id: {thread_id} ===")
        
        conversations_collection = get_collection(CONVERSATIONS_COLLECTION)
        if conversations_collection is None:
            print(f"  [LOG CRITICAL] Failed to get CONVERSATIONS_COLLECTION object for thread_id: {thread_id}.")
            return [] # Cannot proceed without the collection

        messages_cursor = conversations_collection.find({'thread_id': thread_id}).sort('timestamp', 1)
        messages = list(messages_cursor) # Convert cursor to list to get length and iterate
        print(f"  [LOG] Found {len(messages)} message(s) in thread {thread_id} from conversations collection.")
        
        formatted_messages = []
        
        for msg_from_db in messages:
            # Basic structure of the message to be returned
            formatted_message = {
                'message_id': msg_from_db.get('message_id'),
                'role': msg_from_db.get('role'),
                'content': msg_from_db.get('content', ''),
                'timestamp': msg_from_db.get('timestamp')
            }
            
            if msg_from_db.get('role') == 'assistant' and 'tool_results' in msg_from_db and msg_from_db['tool_results']:
                tool_data_from_db = msg_from_db['tool_results'].copy()

                if 'emails' in tool_data_from_db and tool_data_from_db['emails']:
                    email_ids_from_db = tool_data_from_db['emails']
                    
                    if email_ids_from_db:
                        emails_collection = get_collection(EMAILS_COLLECTION)
                        email_objects = list(emails_collection.find({'email_id': {'$in': email_ids_from_db}}))
                        
                        # Create a map of email_id to email_object for correct ordering
                        email_map = {e['email_id']: e for e in email_objects}
                        hydrated_emails = [email_map[eid] for eid in email_ids_from_db if eid in email_map]
                        
                        tool_data_from_db['emails'] = hydrated_emails
                    else:
                        tool_data_from_db['emails'] = []

                formatted_message['tool_results'] = tool_data_from_db
            else:
                 formatted_message['tool_results'] = msg_from_db.get('tool_results')

            formatted_messages.append(formatted_message)
        
        print(f"\n=== [LOG] Completed processing thread {thread_id}. Returning {len(formatted_messages)} formatted message(s). ===")
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
            collection = get_collection(CONVERSATIONS_COLLECTION)
            message = collection.find_one({
                'thread_id': thread_id,
                'tool_results.emails.message_id': message_id
            })
            if not message:
                print(f"Message not found for thread_id: {thread_id}, message_id: {message_id}")
                return False
                
            # Update the message to remove the email
            result = collection.update_one(
                {
                    'thread_id': thread_id,
                    'tool_results.emails.message_id': message_id
                },
                {
                    '$pull': {
                        'tool_results.emails': {'message_id': message_id}
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

    @classmethod
    def delete_by_thread_id(cls, thread_id):
        """
        Delete all conversations in a thread by thread_id.
        
        Args:
            thread_id (str): The thread ID to delete all conversations for
            
        Returns:
            int: Number of conversations deleted
        """
        try:
            collection = get_collection(CONVERSATIONS_COLLECTION)
            result = collection.delete_many({'thread_id': thread_id})
            print(f"[DEBUG] Deleted {result.deleted_count} conversations for thread_id: {thread_id}")
            return result.deleted_count
        except Exception as e:
            print(f"Error deleting conversations for thread_id {thread_id}: {str(e)}")
            return 0

    @classmethod
    def delete_test_conversations(cls):
        """
        Delete all conversations that appear to be from tests (contain 'test' in thread_id).
        This is a cleanup method for test environments.
        
        Returns:
            int: Number of conversations deleted
        """
        try:
            collection = get_collection(CONVERSATIONS_COLLECTION)
            # Delete conversations with thread_ids containing 'test', 'integration', 'e2e', etc.
            test_patterns = ['test', 'integration', 'e2e', 'workflow', 'sample']
            total_deleted = 0
            
            for pattern in test_patterns:
                result = collection.delete_many({
                    'thread_id': {'$regex': pattern, '$options': 'i'}
                })
                total_deleted += result.deleted_count
                if result.deleted_count > 0:
                    print(f"[DEBUG] Deleted {result.deleted_count} conversations matching pattern: {pattern}")
            
            print(f"[DEBUG] Total test conversations deleted: {total_deleted}")
            return total_deleted
        except Exception as e:
            print(f"Error deleting test conversations: {str(e)}")
            return 0 