from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config.mongo_config import MONGO_URI, MONGO_DB_NAME, MONGO_OPTIONS
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    """
    Get MongoDB database instance with automatic reconnection and error handling.
    Returns:
        Database: MongoDB database instance
    """
    try:
        client = MongoClient(MONGO_URI, **MONGO_OPTIONS)
        # Verify connection
        client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        return client[MONGO_DB_NAME]
    except ServerSelectionTimeoutError as e:
        logger.error(f"Could not connect to MongoDB server: {e}")
        logger.info("Please ensure MongoDB is running and accessible")
        raise
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while connecting to MongoDB: {e}")
        raise

def get_collection(collection_name):
    """
    Get MongoDB collection instance with error handling.
    Args:
        collection_name (str): Name of the collection
    Returns:
        Collection: MongoDB collection instance
    """
    try:
        db = get_db()
        return db[collection_name]
    except Exception as e:
        logger.error(f"Error getting collection {collection_name}: {e}")
        raise 