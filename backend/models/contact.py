import time
import uuid
from utils.mongo_client import get_collection
from config.mongo_config import CONTACTS_COLLECTION

class Contact:
    def __init__(self, emails, name, phone=None, source="gmail_contacts", metadata=None, contact_id=None):
        self.contact_id = contact_id or str(uuid.uuid4())
        
        # Handle emails - can be a single email string or list of email objects
        if isinstance(emails, str):
            # Single email string - convert to email object array
            self.emails = [{"email": emails.lower().strip(), "is_primary": True, "is_obsolete": None, "metadata": None}]
            self.primary_email = emails.lower().strip()
        elif isinstance(emails, list) and len(emails) > 0:
            # List of email objects or strings
            processed_emails = []
            primary_found = False
            
            for email_data in emails:
                if isinstance(email_data, str):
                    # Convert string to email object
                    email_obj = {
                        "email": email_data.lower().strip(),
                        "is_primary": not primary_found,  # First email is primary if none specified
                        "is_obsolete": None,
                        "metadata": None
                    }
                    if not primary_found:
                        primary_found = True
                        self.primary_email = email_data.lower().strip()
                else:
                    # Email object with metadata
                    email_obj = {
                        "email": email_data["email"].lower().strip(),
                        "is_primary": email_data.get("is_primary", not primary_found),
                        "is_obsolete": email_data.get("is_obsolete"),
                        "metadata": email_data.get("metadata")
                    }
                    if email_obj["is_primary"] and not primary_found:
                        primary_found = True
                        self.primary_email = email_obj["email"]
                
                processed_emails.append(email_obj)
            
            self.emails = processed_emails
            
            # If no primary was found, make the first one primary
            if not primary_found and processed_emails:
                self.emails[0]["is_primary"] = True
                self.primary_email = self.emails[0]["email"]
        else:
            raise ValueError("At least one email is required")
        
        self.name = name.strip() if name else None
        self.phone = phone.strip() if phone else None
        self.source = source
        self.metadata = metadata or {}
        self.created_at = int(time.time())
        self.updated_at = int(time.time())
        self.collection = get_collection(CONTACTS_COLLECTION)

    def save(self):
        """Save contact to MongoDB with deduplication logic"""
        if not self.primary_email or not self.name:
            raise ValueError("Primary email and name are required for contact")
        
        # Check if contact with this primary email already exists
        existing_contact = self.get_by_email(self.primary_email)
        
        if existing_contact:
            # Update existing contact with merged data
            merged_data = self.merge_contact_data(existing_contact, {
                'name': self.name,
                'phone': self.phone,
                'source': self.source,
                'metadata': self.metadata,
                'emails': self.emails
            })
            
            # Update the existing contact
            result = self.collection.update_one(
                {'primary_email': self.primary_email},
                {'$set': merged_data}
            )
            
            # Update our instance with the merged data
            for key, value in merged_data.items():
                setattr(self, key, value)
            
            return existing_contact['contact_id']
        else:
            # Create new contact
            contact_data = {
                'contact_id': self.contact_id,
                'primary_email': self.primary_email,
                'emails': self.emails,
                'name': self.name,
                'phone': self.phone,
                'source': self.source,
                'metadata': self.metadata,
                'created_at': self.created_at,
                'updated_at': self.updated_at
            }
            
            result = self.collection.insert_one(contact_data)
            return self.contact_id

    def update(self, **kwargs):
        """Update contact fields"""
        allowed_fields = ['name', 'phone', 'source', 'metadata']
        update_data = {}
        
        for field, value in kwargs.items():
            if field in allowed_fields:
                update_data[field] = value
                setattr(self, field, value)
        
        if update_data:
            update_data['updated_at'] = int(time.time())
            self.updated_at = update_data['updated_at']
            
            result = self.collection.update_one(
                {'contact_id': self.contact_id},
                {'$set': update_data}
            )
            return result.modified_count > 0
        
        return False

    @classmethod
    def get_by_email(cls, email):
        """Get contact by email address (searches in both primary_email and emails array)"""
        if not email:
            return None
        
        email = email.lower().strip()
        collection = get_collection(CONTACTS_COLLECTION)
        
        # First try primary email
        result = collection.find_one({'primary_email': email})
        if result:
            return result
        
        # Then search in emails array
        return collection.find_one({'emails.email': email})

    @classmethod
    def get_by_contact_id(cls, contact_id):
        """Get contact by contact_id"""
        collection = get_collection(CONTACTS_COLLECTION)
        return collection.find_one({'contact_id': contact_id})

    @classmethod
    def get_all(cls, limit=100, offset=0):
        """Get all contacts with pagination"""
        collection = get_collection(CONTACTS_COLLECTION)
        return list(collection.find({})
                   .sort('name', 1)
                   .skip(offset)
                   .limit(limit))

    @classmethod
    def search_by_name(cls, query, limit=20):
        """Search contacts by name using text search"""
        collection = get_collection(CONTACTS_COLLECTION)
        
        # Text search on name field
        text_results = list(collection.find(
            {'$text': {'$search': query}},
            {'score': {'$meta': 'textScore'}}
        ).sort([('score', {'$meta': 'textScore'})]).limit(limit))
        
        # If no text search results, try regex search for partial matches
        if not text_results:
            regex_pattern = {'$regex': query, '$options': 'i'}
            text_results = list(collection.find({
                '$or': [
                    {'name': regex_pattern},
                    {'primary_email': regex_pattern},
                    {'emails.email': regex_pattern}
                ]
            }).sort('name', 1).limit(limit))
        
        return text_results

    @classmethod
    def get_stats(cls):
        """Return contact statistics"""
        collection = get_collection(CONTACTS_COLLECTION)
        
        # Total count
        total_count = collection.count_documents({})
        
        # Count by source
        source_pipeline = [
            {'$group': {'_id': '$source', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        source_stats = list(collection.aggregate(source_pipeline))
        
        # Recent contacts (last 24 hours)
        recent_threshold = int(time.time()) - (24 * 60 * 60)
        recent_count = collection.count_documents({
            'created_at': {'$gte': recent_threshold}
        })
        
        return {
            'total_contacts': total_count,
            'recent_contacts': recent_count,
            'by_source': {stat['_id']: stat['count'] for stat in source_stats}
        }

    @classmethod
    def merge_contact_data(cls, existing_contact, new_data):
        """Merge new contact data with existing contact data"""
        merged = {}
        
        # Name: Keep the longer/more complete name
        existing_name = existing_contact.get('name', '')
        new_name = new_data.get('name', '')
        
        if len(new_name) > len(existing_name):
            merged['name'] = new_name
        else:
            merged['name'] = existing_name
        
        # Phone: Keep non-null value, prefer new if both exist
        existing_phone = existing_contact.get('phone')
        new_phone = new_data.get('phone')
        
        if new_phone:
            merged['phone'] = new_phone
        elif existing_phone:
            merged['phone'] = existing_phone
        else:
            merged['phone'] = None
        
        # Source: Use priority-based source selection
        existing_source = existing_contact.get('source')
        new_source = new_data.get('source')
        
        # Priority: gmail_contacts > calendar_attendees > manual
        source_priority = {
            'gmail_contacts': 3,
            'calendar_attendees': 2, 
            'manual': 1
        }
        
        existing_priority = source_priority.get(existing_source, 0)
        new_priority = source_priority.get(new_source, 0)
        
        # Use the source with higher priority
        if new_priority >= existing_priority:
            merged['source'] = new_source
        else:
            merged['source'] = existing_source
        
        # Emails: Merge email arrays, avoiding duplicates but preserving primary
        existing_emails = existing_contact.get('emails', [])
        new_emails = new_data.get('emails', [])
        
        # Create a merged email list
        merged_emails = []
        seen_emails = set()
        
        # Add existing emails first
        for email_obj in existing_emails:
            email = email_obj['email']
            if email not in seen_emails:
                merged_emails.append(email_obj)
                seen_emails.add(email)
        
        # Add new emails that aren't already present
        for email_obj in new_emails:
            email = email_obj['email']
            if email not in seen_emails:
                merged_emails.append(email_obj)
                seen_emails.add(email)
        
        # Ensure at least one primary email exists
        has_primary = any(email_obj.get('is_primary', False) for email_obj in merged_emails)
        if not has_primary and merged_emails:
            merged_emails[0]['is_primary'] = True
        
        merged['emails'] = merged_emails
        
        # Update primary_email based on the primary email in the array
        for email_obj in merged_emails:
            if email_obj.get('is_primary', False):
                merged['primary_email'] = email_obj['email']
                break
        
        # Metadata: Merge dictionaries, new data takes precedence
        existing_metadata = existing_contact.get('metadata', {})
        new_metadata = new_data.get('metadata', {})
        
        merged_metadata = existing_metadata.copy()
        merged_metadata.update(new_metadata)
        merged['metadata'] = merged_metadata
        
        # Always update timestamp
        merged['updated_at'] = int(time.time())
        
        return merged

    @classmethod
    def delete_all(cls):
        """Delete all contacts - useful for testing"""
        collection = get_collection(CONTACTS_COLLECTION)
        result = collection.delete_many({})
        return result.deleted_count

    def to_dict(self):
        """Convert contact to dictionary"""
        return {
            'contact_id': self.contact_id,
            'primary_email': self.primary_email,
            'emails': self.emails,
            'name': self.name,
            'phone': self.phone,
            'source': self.source,
            'metadata': self.metadata,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        } 