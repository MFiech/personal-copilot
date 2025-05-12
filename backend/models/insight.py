from datetime import datetime
from utils.mongo_client import get_collection
from config.mongo_config import INSIGHTS_COLLECTION

class Insight:
    def __init__(self, content, source="user", metadata=None, vector_id=None, tags=None):
        self.insight_id = f"insight_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.source = source
        self.metadata = metadata or {}
        self.vector_id = vector_id
        self.tags = tags or []
        self.collection = get_collection(INSIGHTS_COLLECTION)

    def save(self):
        """Save insight to MongoDB with validation"""
        insight_data = {
            'insight_id': self.insight_id,
            'content': self.content,
            'timestamp': self.timestamp,
            'source': self.source,
            'metadata': self.metadata,
            'vector_id': self.vector_id,
            'tags': self.tags
        }
        return self.collection.insert_one(insight_data)

    @classmethod
    def get_by_id(cls, insight_id):
        """Get insight by ID"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.find_one({'insight_id': insight_id})

    @classmethod
    def get_by_source(cls, source):
        """Get insights by source type"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return list(collection.find({'source': source}).sort('timestamp', -1))

    @classmethod
    def get_by_tags(cls, tags):
        """Get insights by tags"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return list(collection.find({'tags': {'$in': tags}}).sort('timestamp', -1))

    @classmethod
    def get_by_vector_id(cls, vector_id):
        """Get insight by vector ID"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.find_one({'vector_id': vector_id})

    @classmethod
    def add_tag(cls, insight_id, tag):
        """Add a tag to an insight"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.update_one(
            {'insight_id': insight_id},
            {'$addToSet': {'tags': tag}}
        )

    @classmethod
    def remove_tag(cls, insight_id, tag):
        """Remove a tag from an insight"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.update_one(
            {'insight_id': insight_id},
            {'$pull': {'tags': tag}}
        )

    @classmethod
    def update_metadata(cls, insight_id, metadata):
        """Update insight metadata"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.update_one(
            {'insight_id': insight_id},
            {'$set': {'metadata': metadata}}
        )

    @classmethod
    def delete(cls, insight_id):
        """Delete an insight"""
        collection = get_collection(INSIGHTS_COLLECTION)
        return collection.delete_one({'insight_id': insight_id}) 