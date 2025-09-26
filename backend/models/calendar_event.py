from datetime import datetime
from utils.mongo_client import get_collection, get_db
from config.mongo_config import CALENDAR_EVENTS_COLLECTION
import time
import uuid

class CalendarEvent:
    def __init__(self, internal_event_id=None, google_event_id=None, recurring_event_id=None,
                 summary=None, description=None, start_time=None, end_time=None,
                 attendees=None, status=None, location=None, google_updated=None,
                 created_at=None, updated_at=None):
        self.internal_event_id = internal_event_id or str(uuid.uuid4())
        self.google_event_id = google_event_id
        self.recurring_event_id = recurring_event_id
        self.summary = summary
        self.description = description
        self.start_time = start_time
        self.end_time = end_time
        self.attendees = attendees or []
        self.status = status
        self.location = location
        self.google_updated = google_updated
        self.created_at = created_at if created_at is not None else int(time.time())
        self.updated_at = updated_at if updated_at is not None else int(time.time())
        self.collection = get_collection(CALENDAR_EVENTS_COLLECTION)

    def save(self):
        """Save calendar event to MongoDB with validation"""
        print(f"[DEBUG CALENDAR EVENT SAVE] Saving event with google_event_id: {self.google_event_id}")

        self.updated_at = int(time.time())

        event_data = {
            'internal_event_id': self.internal_event_id,
            'google_event_id': self.google_event_id,
            'recurring_event_id': self.recurring_event_id,
            'summary': self.summary,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'attendees': self.attendees,
            'status': self.status,
            'location': self.location,
            'google_updated': self.google_updated,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

        print(f"[DEBUG CALENDAR EVENT SAVE] Event data to save: {event_data}")

        # Update if exists, insert if not (using google_event_id as unique key)
        result = self.collection.update_one(
            {'google_event_id': self.google_event_id},
            {'$set': event_data},
            upsert=True
        )

        print(f"[DEBUG CALENDAR EVENT SAVE] Upsert result: matched_count={result.matched_count}, modified_count={result.modified_count}, upserted_id={result.upserted_id}")
        return result.upserted_id or self.internal_event_id

    @classmethod
    def get_by_internal_id(cls, internal_event_id):
        """Get calendar event by internal ID"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        event_data = collection.find_one({'internal_event_id': internal_event_id})
        if event_data:
            return cls._from_dict(event_data)
        return None

    @classmethod
    def get_by_google_event_id(cls, google_event_id):
        """Get calendar event by Google event ID"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        event_data = collection.find_one({'google_event_id': google_event_id})
        if event_data:
            return cls._from_dict(event_data)
        return None

    @classmethod
    def get_by_recurring_event_id(cls, recurring_event_id):
        """Get all instances of a recurring event"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        events_data = list(collection.find({
            'recurring_event_id': recurring_event_id
        }).sort('start_time', 1))

        return [cls._from_dict(event_data) for event_data in events_data]

    @classmethod
    def get_events_in_range(cls, start_date, end_date):
        """Get all events within a date range"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        events_data = list(collection.find({
            'start_time': {
                '$gte': start_date,
                '$lte': end_date
            }
        }).sort('start_time', 1))

        return [cls._from_dict(event_data) for event_data in events_data]

    @classmethod
    def delete_by_internal_id(cls, internal_event_id):
        """Delete calendar event by internal ID"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        result = collection.delete_one({'internal_event_id': internal_event_id})
        return result.deleted_count > 0

    @classmethod
    def delete_by_google_event_id(cls, google_event_id):
        """Delete calendar event by Google event ID"""
        collection = get_collection(CALENDAR_EVENTS_COLLECTION)
        result = collection.delete_one({'google_event_id': google_event_id})
        return result.deleted_count > 0

    def update(self, updates):
        """Update specific fields of the calendar event"""
        self.updated_at = int(time.time())

        # Update instance attributes
        for key, value in updates.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Add updated_at to the updates
        updates['updated_at'] = self.updated_at

        # Update in database
        result = self.collection.update_one(
            {'internal_event_id': self.internal_event_id},
            {'$set': updates}
        )
        return result.modified_count > 0

    def to_dict(self):
        """Convert calendar event to dictionary"""
        return {
            'internal_event_id': self.internal_event_id,
            'google_event_id': self.google_event_id,
            'recurring_event_id': self.recurring_event_id,
            'summary': self.summary,
            'description': self.description,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'attendees': self.attendees,
            'status': self.status,
            'location': self.location,
            'google_updated': self.google_updated,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

    @classmethod
    def _from_dict(cls, data):
        """Create CalendarEvent instance from dictionary"""
        return cls(
            internal_event_id=data.get('internal_event_id'),
            google_event_id=data.get('google_event_id'),
            recurring_event_id=data.get('recurring_event_id'),
            summary=data.get('summary'),
            description=data.get('description'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            attendees=data.get('attendees', []),
            status=data.get('status'),
            location=data.get('location'),
            google_updated=data.get('google_updated'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at')
        )