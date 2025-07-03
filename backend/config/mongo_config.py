import os
from dotenv import load_dotenv
from .mongo_schema import (
    CONVERSATIONS_SCHEMA,
    INSIGHTS_SCHEMA,
    EMAILS_SCHEMA,
    DRAFTS_SCHEMA,
    CONVERSATIONS_INDEXES,
    INSIGHTS_INDEXES,
    EMAILS_INDEXES,
    DRAFTS_INDEXES
)

# Load environment variables
load_dotenv()

# MongoDB Configuration
# Default to MongoDB Atlas if MONGO_URI is provided, otherwise use local MongoDB
MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
MONGO_DB_NAME = os.getenv('MONGO_DB_NAME', 'pm_copilot')

# Collection names
CONVERSATIONS_COLLECTION = 'conversations'
INSIGHTS_COLLECTION = 'insights'
EMAILS_COLLECTION = 'emails'
CONTACTS_COLLECTION = 'contacts'
CONTACT_SYNC_LOG_COLLECTION = 'contact_sync_log'
DRAFTS_COLLECTION = 'drafts'

# MongoDB connection options
MONGO_OPTIONS = {
    'connectTimeoutMS': 5000,
    'socketTimeoutMS': 30000,
    'serverSelectionTimeoutMS': 5000,
    'retryWrites': True,
    'retryReads': True
}

def init_collections(db):
    """Initialize collections with schema validation"""
    # Initialize conversations collection
    if CONVERSATIONS_COLLECTION not in db.list_collection_names():
        db.create_collection(
            CONVERSATIONS_COLLECTION,
            **CONVERSATIONS_SCHEMA
        )
        print(f"Created collection: {CONVERSATIONS_COLLECTION}")
    
    # Initialize insights collection
    if INSIGHTS_COLLECTION not in db.list_collection_names():
        db.create_collection(
            INSIGHTS_COLLECTION,
            **INSIGHTS_SCHEMA
        )
        print(f"Created collection: {INSIGHTS_COLLECTION}")
    
    # Initialize emails collection
    if EMAILS_COLLECTION not in db.list_collection_names():
        db.create_collection(
            EMAILS_COLLECTION,
            **EMAILS_SCHEMA
        )
        print(f"Created collection: {EMAILS_COLLECTION}")
    
    # Initialize drafts collection
    if DRAFTS_COLLECTION not in db.list_collection_names():
        db.create_collection(
            DRAFTS_COLLECTION,
            **DRAFTS_SCHEMA
        )
        print(f"Created collection: {DRAFTS_COLLECTION}")
    
    # Create indexes
    conversations = db[CONVERSATIONS_COLLECTION]
    insights = db[INSIGHTS_COLLECTION]
    emails = db[EMAILS_COLLECTION]
    drafts = db[DRAFTS_COLLECTION]
    
    for index_config in CONVERSATIONS_INDEXES:
        conversations.create_index(**index_config)
    
    for index_config in INSIGHTS_INDEXES:
        insights.create_index(**index_config)
        
    for index_config in EMAILS_INDEXES:
        emails.create_index(**index_config)
    
    for index_config in DRAFTS_INDEXES:
        drafts.create_index(**index_config) 