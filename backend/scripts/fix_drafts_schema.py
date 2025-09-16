#!/usr/bin/env python3
"""
Script to fix the MongoDB drafts collection schema to allow null emails for attendees.
This fixes the validation error that prevents calendar event drafts from being saved.
"""

import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from utils.mongo_client import get_db
from config.mongo_config import DRAFTS_COLLECTION

def update_drafts_schema():
    """Update the drafts collection schema to allow null emails for attendees"""
    
    try:
        db = get_db()
        
        print("🔧 Updating drafts collection schema...")
        
        # The new schema that allows null emails for attendees
        updated_schema = {
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["draft_id", "thread_id", "message_id", "draft_type", "status"],
                    "properties": {
                        "draft_id": {
                            "bsonType": "string",
                            "description": "Unique identifier for the draft"
                        },
                        "thread_id": {
                            "bsonType": "string",
                            "description": "Reference to the conversation thread"
                        },
                        "message_id": {
                            "bsonType": "string",
                            "description": "Reference to the conversation message that created this draft"
                        },
                        "draft_type": {
                            "bsonType": "string",
                            "enum": ["email", "calendar_event"],
                            "description": "Type of draft - email or calendar event"
                        },
                        "status": {
                            "bsonType": "string",
                            "enum": ["active", "closed", "composio_error"],
                            "description": "Draft status"
                        },
                        # Email-specific fields
                        "to_emails": {
                            "bsonType": "array",
                            "description": "List of email recipients",
                            "items": {
                                "bsonType": "object",
                                "properties": {
                                    "email": {
                                        "bsonType": "string",
                                        "description": "Recipient's email address"
                                    },
                                    "name": {
                                        "bsonType": ["string", "null"],
                                        "description": "Recipient's name"
                                    }
                                }
                            }
                        },
                        "subject": {
                            "bsonType": ["string", "null"],
                            "description": "Email subject"
                        },
                        "body": {
                            "bsonType": ["string", "null"],
                            "description": "Email body content"
                        },
                        "attachments": {
                            "bsonType": "array",
                            "description": "Email attachments",
                            "items": {
                                "bsonType": "object"
                            }
                        },
                        # Calendar-specific fields
                        "summary": {
                            "bsonType": ["string", "null"],
                            "description": "Calendar event title/summary"
                        },
                        "start_time": {
                            "bsonType": ["string", "null"],
                            "description": "Calendar event start time (ISO format)"
                        },
                        "end_time": {
                            "bsonType": ["string", "null"],
                            "description": "Calendar event end time (ISO format)"
                        },
                        "attendees": {
                            "bsonType": "array",
                            "description": "List of calendar event attendees",
                            "items": {
                                "bsonType": "object",
                                "properties": {
                                    "email": {
                                        "bsonType": ["string", "null"],
                                        "description": "Attendee's email address (optional)"
                                    },
                                    "name": {
                                        "bsonType": ["string", "null"],
                                        "description": "Attendee's name"
                                    }
                                }
                            }
                        },
                        "location": {
                            "bsonType": ["string", "null"],
                            "description": "Calendar event location"
                        },
                        "description": {
                            "bsonType": ["string", "null"],
                            "description": "Calendar event description"
                        },
                        # Timestamps
                        "created_at": {
                            "bsonType": "int",
                            "description": "Creation timestamp"
                        },
                        "updated_at": {
                            "bsonType": "int",
                            "description": "Last update timestamp"
                        }
                    }
                }
            }
        }
        
        # Update the collection schema
        db.command("collMod", DRAFTS_COLLECTION, **updated_schema)
        print("✅ Successfully updated drafts collection schema")
        print("📝 Attendee emails can now be null (optional)")
        
        # Test the schema by trying to insert a test document with null attendee email
        test_doc = {
            "draft_id": "test_schema_fix_123",
            "thread_id": "test_thread",
            "message_id": "test_message", 
            "draft_type": "calendar_event",
            "status": "active",
            "attendees": [{"name": "Test Attendee", "email": None}],
            "created_at": 1234567890,
            "updated_at": 1234567890
        }
        
        print("🧪 Testing schema with null attendee email...")
        drafts_collection = db[DRAFTS_COLLECTION]
        
        # Try to insert and then immediately delete
        result = drafts_collection.insert_one(test_doc)
        if result.inserted_id:
            print("✅ Schema test passed - null attendee emails are now allowed")
            drafts_collection.delete_one({"_id": result.inserted_id})
            print("🧹 Cleaned up test document")
        else:
            print("❌ Schema test failed")
            
    except Exception as e:
        print(f"❌ Error updating schema: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False
        
    return True

if __name__ == "__main__":
    print("🚀 Starting MongoDB drafts schema fix...")
    success = update_drafts_schema()
    if success:
        print("🎉 Schema fix completed successfully!")
        print("📅 Calendar event drafts with attendees should now work properly")
    else:
        print("💥 Schema fix failed - please check the logs")
        sys.exit(1)