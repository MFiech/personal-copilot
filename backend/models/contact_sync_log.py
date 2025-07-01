import time
import uuid
from utils.mongo_client import get_collection
from config.mongo_config import CONTACT_SYNC_LOG_COLLECTION

class ContactSyncLog:
    def __init__(self, sync_type="gmail_contacts", sync_id=None):
        self.sync_id = sync_id or str(uuid.uuid4())
        self.sync_type = sync_type
        self.started_at = int(time.time())
        self.completed_at = None
        self.status = "running"
        self.total_fetched = None
        self.total_processed = None
        self.new_contacts = None
        self.updated_contacts = None
        self.error_count = 0
        self.errors = []
        self.collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)

    def start_sync(self):
        """Initialize sync log in database"""
        sync_data = {
            'sync_id': self.sync_id,
            'sync_type': self.sync_type,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status,
            'total_fetched': self.total_fetched,
            'total_processed': self.total_processed,
            'new_contacts': self.new_contacts,
            'updated_contacts': self.updated_contacts,
            'error_count': self.error_count,
            'errors': self.errors
        }
        
        result = self.collection.insert_one(sync_data)
        return result.inserted_id

    def complete_sync(self, stats):
        """Complete sync with final statistics"""
        self.completed_at = int(time.time())
        self.total_fetched = stats.get('total_fetched', 0)
        self.total_processed = stats.get('total_processed', 0)
        self.new_contacts = stats.get('new_contacts', 0)
        self.updated_contacts = stats.get('updated_contacts', 0)
        self.error_count = len(self.errors)
        
        # Determine final status
        if self.error_count == 0:
            self.status = "success"
        elif self.total_processed > 0:
            self.status = "partial"
        else:
            self.status = "failed"
        
        # Update in database
        update_data = {
            'completed_at': self.completed_at,
            'status': self.status,
            'total_fetched': self.total_fetched,
            'total_processed': self.total_processed,
            'new_contacts': self.new_contacts,
            'updated_contacts': self.updated_contacts,
            'error_count': self.error_count,
            'errors': self.errors
        }
        
        result = self.collection.update_one(
            {'sync_id': self.sync_id},
            {'$set': update_data}
        )
        return result.modified_count > 0

    def add_error(self, error_message, contact_data=None):
        """Add an error to the sync log"""
        error_entry = {
            'error': str(error_message),
            'contact_data': contact_data,
            'timestamp': int(time.time())
        }
        
        self.errors.append(error_entry)
        self.error_count = len(self.errors)
        
        # Update errors in database
        result = self.collection.update_one(
            {'sync_id': self.sync_id},
            {
                '$push': {'errors': error_entry},
                '$set': {'error_count': self.error_count}
            }
        )
        return result.modified_count > 0

    def fail_sync(self, error_message):
        """Mark sync as failed with error message"""
        self.completed_at = int(time.time())
        self.status = "failed"
        self.add_error(error_message)
        
        update_data = {
            'completed_at': self.completed_at,
            'status': self.status,
            'error_count': self.error_count
        }
        
        result = self.collection.update_one(
            {'sync_id': self.sync_id},
            {'$set': update_data}
        )
        return result.modified_count > 0

    @classmethod
    def get_latest_sync(cls, sync_type=None):
        """Get the most recent sync log"""
        collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        
        query = {}
        if sync_type:
            query['sync_type'] = sync_type
        
        return collection.find_one(
            query,
            sort=[('started_at', -1)]
        )

    @classmethod
    def get_sync_history(cls, limit=10, sync_type=None):
        """Get sync history with optional filtering by type"""
        collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        
        query = {}
        if sync_type:
            query['sync_type'] = sync_type
        
        return list(collection.find(query)
                   .sort('started_at', -1)
                   .limit(limit))

    @classmethod
    def get_by_sync_id(cls, sync_id):
        """Get sync log by sync_id"""
        collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        return collection.find_one({'sync_id': sync_id})

    @classmethod
    def get_running_syncs(cls):
        """Get all currently running syncs"""
        collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        return list(collection.find({'status': 'running'}))

    @classmethod
    def cleanup_old_logs(cls, days_to_keep=30):
        """Remove sync logs older than specified days"""
        collection = get_collection(CONTACT_SYNC_LOG_COLLECTION)
        
        cutoff_timestamp = int(time.time()) - (days_to_keep * 24 * 60 * 60)
        result = collection.delete_many({
            'started_at': {'$lt': cutoff_timestamp}
        })
        
        return result.deleted_count

    def to_dict(self):
        """Convert sync log to dictionary"""
        return {
            'sync_id': self.sync_id,
            'sync_type': self.sync_type,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status,
            'total_fetched': self.total_fetched,
            'total_processed': self.total_processed,
            'new_contacts': self.new_contacts,
            'updated_contacts': self.updated_contacts,
            'error_count': self.error_count,
            'errors': self.errors
        } 