from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import CONVERSATIONS_COLLECTION
import time
import uuid
import json

EMAILS_COLLECTION = 'emails'

print("THIS IS conversation.py VERSION 000 - VERY TOP OF FILE")

class Conversation:
    def __init__(self, thread_id=None, role=None, content=None, insight_id=None, metadata=None, veyra_results=None, query=None, response=None,
                 veyra_original_query_params=None, veyra_current_offset=None, veyra_limit_per_page=None, veyra_total_emails_available=None,
                 veyra_has_more=None, timestamp=None):
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
        
        # Use provided timestamp or generate new one
        self.timestamp = timestamp if timestamp is not None else int(time.time())
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
        # If veyra_results is present, ensure emails are saved to the emails collection and only IDs are stored
        if self.veyra_results:
            veyra_results = self.veyra_results.copy()
            if 'emails' in veyra_results and veyra_results['emails']:
                email_ids = []
                emails_collection = get_collection(EMAILS_COLLECTION)
                for email in veyra_results['emails']:
                    if isinstance(email, dict) and 'id' in email:
                        # Transform the email data to match the schema
                        from_email = email.get('from_email', {})
                        formatted_email = {
                            'email_id': email['id'],  # Map 'id' to 'email_id'
                            'thread_id': self.thread_id,  # Add thread_id from conversation
                            'subject': email.get('subject', ''),
                            'from_email': {
                                'email': from_email.get('email', ''),
                                'name': from_email.get('name') or from_email.get('email', '').split('@')[0].replace('.', ' ').title()
                            },
                            'date': email.get('date', ''),
                            'content': {
                                'html': email.get('body', {}).get('html', '') if 'body' in email else '',
                                'text': email.get('body', {}).get('text', '') if 'body' in email else ''
                            },
                            'metadata': {
                                'source': 'VEYRA',
                                'folder': email.get('folder', 'INBOX'),
                                'is_read': email.get('is_read', False),
                                'size': email.get('size')
                            },
                            'attachments': email.get('attachments', []),
                            'cc': email.get('cc', []),
                            'bcc': email.get('bcc', []),
                            'reply_to': email.get('reply_to'),
                            'to_emails': [
                                {
                                    'email': recipient['email'],
                                    'name': recipient.get('name') or recipient['email'].split('@')[0].replace('.', ' ').title()
                                }
                                for recipient in email.get('to', [])
                            ],
                            'created_at': int(time.time()),
                            'updated_at': int(time.time())
                        }
                        try:
                            # Use email_id as the unique identifier for upsert
                            emails_collection.update_one(
                                {'email_id': formatted_email['email_id']},
                                {'$set': formatted_email},
                                upsert=True
                            )
                            email_ids.append(email['id'])
                        except Exception as e:
                            print(f"Error saving email {email['id']}: {str(e)}")
                            print(f"Problematic email data: {json.dumps(formatted_email)}")
                            raise
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
        print(f"\n=== [LOG] Starting get_by_thread_id for thread_id: {thread_id} ===")
        
        conversations_collection = get_collection(CONVERSATIONS_COLLECTION)
        if conversations_collection is None:
            print(f"  [LOG CRITICAL] Failed to get CONVERSATIONS_COLLECTION object for thread_id: {thread_id}.")
            return [] # Cannot proceed without the collection

        messages_cursor = conversations_collection.find({'thread_id': thread_id}).sort('timestamp', 1)
        messages = list(messages_cursor) # Convert cursor to list to get length and iterate
        print(f"  [LOG] Found {len(messages)} message(s) in thread {thread_id} from conversations collection.")
        
        formatted_messages = []
        
        for i, msg_from_db in enumerate(messages):
            msg_id = msg_from_db.get('message_id', 'N/A')
            msg_role = msg_from_db.get('role', 'N/A')
            print(f"\n  [LOG] Processing DB message {i+1}/{len(messages)}: ID {msg_id}, Role: {msg_role}")

            # Basic structure of the message to be returned
            formatted_message = {
                'message_id': msg_id,
                'role': msg_role,
                'content': msg_from_db.get('content', ''),
                'timestamp': msg_from_db.get('timestamp')
            }
            
            # Process veyra_results only for assistant messages that have it
            if msg_role == 'assistant' and 'veyra_results' in msg_from_db and msg_from_db['veyra_results']:
                print(f"    [LOG] Assistant message {msg_id} has veyra_results.")
                veyra_data_from_db = msg_from_db['veyra_results']
                
                # Initialize veyra_results for the formatted_message with a copy of what's in the DB.
                # This ensures other pagination fields in veyra_data_from_db are preserved.
                formatted_message['veyra_results'] = veyra_data_from_db.copy()

                if 'emails' in veyra_data_from_db and veyra_data_from_db['emails']:
                    email_ids_from_db = veyra_data_from_db['emails']
                    
                    if not isinstance(email_ids_from_db, list):
                        print(f"    [LOG WARNING] email_ids_from_db is not a list! Type: {type(email_ids_from_db)}, Value: {email_ids_from_db}. Skipping email processing for this message.")
                        # veyra_results in formatted_message already has the original non-list 'emails' field.
                    elif not email_ids_from_db:
                        print(f"    [LOG] 'emails' key exists in veyra_results for message {msg_id}, but the list is empty. No IDs to query.")
                        formatted_message['veyra_results']['emails'] = [] # Ensure it's an empty list in the output
                    else:
                        print(f"    [LOG] Found {len(email_ids_from_db)} email ID(s) in veyra_results: {email_ids_from_db}")
                        
                        if not all(isinstance(eid, str) for eid in email_ids_from_db):
                            print(f"    [LOG WARNING] Not all email IDs are strings! Details: {[(eid, type(eid)) for eid in email_ids_from_db]}")

                        current_emails_collection = get_collection(EMAILS_COLLECTION)
                        if current_emails_collection is None:
                            print(f"    [LOG CRITICAL] Failed to get EMAILS_COLLECTION object for message {msg_id}!")
                            retrieved_email_objects = [] # Default to empty list
                        else:
                            print(f"    [LOG] EMAILS_COLLECTION object obtained: {current_emails_collection.name} in db {current_emails_collection.database.name}")
                            emails_query = {'email_id': {'$in': email_ids_from_db}}
                            print(f"    [LOG] Querying '{current_emails_collection.name}' collection with: {emails_query}")
                            
                            try:
                                email_objects_cursor = current_emails_collection.find(emails_query)
                                retrieved_email_objects = list(email_objects_cursor) # Convert cursor to list
                                print(f"    [LOG] Query executed. Retrieved {len(retrieved_email_objects)} email object(s) from emails collection.")
                            except Exception as e:
                                print(f"    [LOG CRITICAL] Exception during emails_collection.find() or list conversion for message {msg_id}: {str(e)}")
                                retrieved_email_objects = [] # Default to empty list on error
                        
                        if len(retrieved_email_objects) != len(email_ids_from_db):
                            print(f"    [LOG WARNING] Mismatch for message {msg_id}! Expected {len(email_ids_from_db)} emails based on IDs, got {len(retrieved_email_objects)} objects from DB.")
                            if retrieved_email_objects:
                                retrieved_ids_from_email_objects = {e.get('email_id') for e in retrieved_email_objects if isinstance(e, dict)}
                                print(f"      [LOG DETAIL] IDs found in retrieved email objects: {retrieved_ids_from_email_objects}")
                                print(f"      [LOG DETAIL] Original IDs from conversation: {set(email_ids_from_db)}")
                                print(f"      [LOG DETAIL] IDs in conversation but NOT found in retrieved email objects: {set(email_ids_from_db) - retrieved_ids_from_email_objects}")
                            else:
                                print(f"      [LOG DETAIL] All {len(email_ids_from_db)} email IDs were effectively missing from emails collection based on the query: {set(email_ids_from_db)}")
                        
                        # Replace the list of IDs with the list of (potentially fewer) full email objects
                        formatted_message['veyra_results']['emails'] = retrieved_email_objects
                        print(f"    [LOG] Updated 'emails' in veyra_results for message {msg_id} with {len(retrieved_email_objects)} full email object(s).")
                else: # 'emails' key missing or list is empty
                    print(f"    [LOG] No 'emails' key in veyra_results or 'emails' list is empty/null for message {msg_id}.")
                    if 'emails' not in formatted_message['veyra_results']: # If emails key was missing entirely
                         formatted_message['veyra_results']['emails'] = [] # Ensure it exists as an empty list
            
            elif msg_role == 'assistant': # Assistant message but 'veyra_results' was missing or null/falsey
                print(f"    [LOG] Assistant message {msg_id} does not have truthy 'veyra_results'. Value: {msg_from_db.get('veyra_results')}")
                formatted_message['veyra_results'] = msg_from_db.get('veyra_results') # Preserve null or original veyra_results

            else: # User message or other roles that don't have veyra_results
                 formatted_message['veyra_results'] = None


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