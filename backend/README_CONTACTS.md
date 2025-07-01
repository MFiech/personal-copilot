# Contact Management System

A comprehensive contact management system that integrates with Gmail through Composio to provide contact synchronization, search, and management capabilities.

## Overview

This contact system provides:

- **Contact Synchronization**: Sync contacts from Gmail using Google People API via Composio
- **Smart Search**: Search contacts both locally and directly from Gmail
- **Deduplication**: Automatic contact deduplication based on email addresses
- **Comprehensive Logging**: Track all sync operations with detailed statistics and error handling
- **RESTful API**: Complete set of endpoints for contact management

## Architecture

### Database Schema

The system uses two MongoDB collections:

1. **`contacts`** - Stores contact information
2. **`contact_sync_log`** - Tracks sync operations and errors

### Core Components

1. **Models** (`models/`)
   - `contact.py` - Contact data model with CRUD operations
   - `contact_sync_log.py` - Sync operation logging

2. **Services** (`services/`)
   - `contact_service.py` - Main contact sync and management service

3. **API Endpoints** (`app.py`)
   - Complete REST API for contact management

4. **Scripts** (`scripts/`)
   - `init_contacts_db.py` - Database initialization
   - `test_contact_system.py` - Comprehensive testing

## Installation & Setup

### 1. Database Initialization

Run the database initialization script to set up collections and indexes:

```bash
cd backend
python scripts/init_contacts_db.py
```

To check if collections are properly set up:

```bash
python scripts/init_contacts_db.py --check
```

### 2. Dependencies

The contact system uses existing dependencies. Ensure you have:

- `composio-core` - For Gmail/People API integration
- `pymongo` - For MongoDB operations
- Standard Python libraries (uuid, time, logging)

### 3. Configuration

The system uses existing Composio configuration. Ensure your `.env` file contains:

```env
COMPOSIO_API_KEY=your_composio_api_key_here
```

## Usage

### API Endpoints

#### Contact Synchronization

**Sync Gmail Contacts**
```http
POST /contacts/sync
Content-Type: application/json

{
  "full_sync": true
}
```

**Response:**
```json
{
  "success": true,
  "message": "Contact sync completed successfully",
  "sync_id": "uuid-string",
  "stats": {
    "total_fetched": 150,
    "total_processed": 148,
    "new_contacts": 20,
    "updated_contacts": 128,
    "errors": []
  }
}
```

#### Contact Retrieval

**Get All Contacts**
```http
GET /contacts?limit=100&offset=0
```

**Search Contacts**
```http
POST /contacts/search
Content-Type: application/json

{
  "query": "john",
  "limit": 20
}
```

**Response:**
```json
{
  "success": true,
  "query": "john",
  "contacts": [
    {
      "contact_id": "uuid-string",
      "email": "john.doe@example.com",
      "name": "John Doe",
      "phone": "+1-555-123-4567",
      "source": "gmail_contacts",
      "metadata": {...},
      "created_at": 1234567890,
      "updated_at": 1234567890
    }
  ],
  "count": 1
}
```

#### Sync Management

**Get Sync Status**
```http
GET /contacts/sync/status
GET /contacts/sync/status?sync_id=uuid-string
```

**Get Sync History**
```http
GET /contacts/sync/history?limit=10
```

**Get Contact Statistics**
```http
GET /contacts/stats
```

#### Maintenance

**Cleanup Old Logs**
```http
POST /contacts/cleanup
Content-Type: application/json

{
  "days_to_keep": 30
}
```

### Programmatic Usage

```python
from services.contact_service import ContactSyncService

# Initialize service
contact_service = ContactSyncService()

# Sync contacts from Gmail
result = contact_service.sync_gmail_contacts(full_sync=True)
print(f"Sync completed: {result}")

# Search contacts
contacts = contact_service.search_contacts("john", limit=10)
print(f"Found {len(contacts)} contacts")

# Get contact statistics
stats = contact_service.get_contact_stats()
print(f"Total contacts: {stats['total_contacts']}")
```

## Features

### Contact Deduplication

The system automatically handles duplicate contacts:

- **Primary Key**: Email address (case-insensitive)
- **Merge Strategy**: 
  - Name: Keep longer/more complete name
  - Phone: Prefer new data, fallback to existing
  - Source: Combine multiple sources as array
  - Metadata: Merge dictionaries, new data takes precedence

### Smart Search

The search functionality provides:

1. **Local Database Search**: Fast search using MongoDB text indexes
2. **Gmail Direct Search**: Real-time search using Composio `GMAIL_SEARCH_PEOPLE`
3. **Hybrid Results**: Combines and deduplicates results from both sources

### Comprehensive Logging

All sync operations are logged with:

- Start/completion timestamps
- Total contacts fetched/processed
- New vs updated contact counts
- Detailed error tracking with contact data
- Sync status (running/success/failed/partial)

### Error Handling

Robust error handling includes:

- Individual contact processing errors don't fail entire sync
- Detailed error logging with problematic contact data
- Graceful fallbacks for missing data
- Comprehensive validation

## Composio Integration

### Actions Used

1. **`GMAIL_GET_CONTACTS`**
   - Fetches user's contacts from Gmail
   - Parameters: `resource_name`, `person_fields`, `page_token`
   - Returns: List of contacts with pagination support

2. **`GMAIL_SEARCH_PEOPLE`**
   - Searches contacts by query
   - Parameters: `query`, `pageSize`, `person_fields`, `other_contacts`
   - Returns: Matching contacts (limited to 30 by API)

### Data Processing

The system processes Google People API format:

```python
# Input: Google People API contact
{
  "resourceName": "people/c123456789",
  "names": [{"displayName": "John Doe", "givenName": "John", "familyName": "Doe"}],
  "emailAddresses": [{"value": "john@example.com", "metadata": {"primary": true}}],
  "phoneNumbers": [{"value": "+1-555-123-4567"}]
}

# Output: Normalized contact
{
  "email": "john@example.com",
  "name": "John Doe", 
  "phone": "+1-555-123-4567",
  "source": "gmail_contacts",
  "metadata": {"resourceName": "people/c123456789", "etag": "..."}
}
```

## Testing

### Run Tests

```bash
cd backend
python test_contact_system.py
```

This runs comprehensive tests for:

- Contact model operations (CRUD, deduplication)
- Sync log functionality 
- Contact service methods
- Mock Composio integration
- Database operations

### Test Coverage

The test suite covers:

- ✅ Contact creation and retrieval
- ✅ Contact deduplication logic
- ✅ Search functionality
- ✅ Sync log operations
- ✅ Error handling
- ✅ Data processing functions

## Future Enhancements

### Phase 2 Features (Not Implemented Yet)

1. **Calendar Integration**
   - Extract attendees from calendar events
   - Add them as contacts automatically

2. **LLM Integration**
   - Natural language contact queries
   - "Send email to John" → find John's contact
   - "Schedule meeting with team" → find team members

3. **Advanced Features**
   - Contact groups/labels
   - Contact frequency tracking
   - Email integration for recipient suggestions
   - Contact photo synchronization

## Database Schema Details

### Contacts Collection

```javascript
{
  "_id": ObjectId,
  "contact_id": "uuid-string",           // Unique identifier
  "email": "user@example.com",           // Primary key (unique, lowercase)
  "name": "User Name",                   // Display name
  "phone": "+1-555-123-4567",           // Phone number (optional)
  "source": "gmail_contacts",            // Source of contact data
  "metadata": {                          // Additional data from source APIs
    "resourceName": "people/c123456789",
    "etag": "etag-string",
    "photoUrl": "https://..."
  },
  "created_at": 1234567890,             // Unix timestamp
  "updated_at": 1234567890              // Unix timestamp
}
```

### Contact Sync Log Collection

```javascript
{
  "_id": ObjectId,
  "sync_id": "uuid-string",             // Unique sync identifier
  "sync_type": "gmail_contacts",        // Type of sync operation
  "started_at": 1234567890,            // Start timestamp
  "completed_at": 1234567890,          // Completion timestamp
  "status": "success",                  // running/success/failed/partial
  "total_fetched": 150,                // Contacts fetched from source
  "total_processed": 148,              // Contacts processed successfully
  "new_contacts": 20,                  // New contacts created
  "updated_contacts": 128,             // Existing contacts updated
  "error_count": 2,                    // Number of errors
  "errors": [                          // Array of error details
    {
      "error": "Missing email address",
      "contact_data": {...},
      "timestamp": 1234567890
    }
  ]
}
```

### Indexes

**Contacts Collection:**
- `contact_id` (unique)
- `email` (unique) 
- `name` (text search)
- `source`
- `created_at`
- `updated_at`

**Sync Log Collection:**
- `sync_id` (unique)
- `sync_type`
- `started_at`
- `status`

## Troubleshooting

### Common Issues

1. **Composio Action Not Found**
   - Ensure `GMAIL_GET_CONTACTS` and `GMAIL_SEARCH_PEOPLE` actions are available
   - Check Composio service initialization

2. **Database Connection Issues**
   - Run `python scripts/init_contacts_db.py --check`
   - Verify MongoDB connection in utils/mongo_client.py

3. **Empty Sync Results**
   - Check Composio API key and permissions
   - Verify Gmail/People API scopes are granted
   - Check sync logs for detailed errors

4. **Deduplication Not Working**
   - Ensure email addresses are properly normalized (lowercase)
   - Check Contact.merge_contact_data() logic

### Debug Endpoints

**Delete All Contacts (DEBUG ONLY)**
```http
POST /contacts/debug/delete_all
```

⚠️ **Warning**: This deletes all contacts. Use only for testing!

## Security Considerations

- Email addresses are normalized and validated
- Input sanitization for all API endpoints
- Error messages don't expose sensitive data
- Database schema validation enforced
- No direct access to raw Composio responses in API

## Performance Notes

- Contacts are paginated by default (100 per page)
- Text search uses MongoDB indexes
- Sync operations are tracked for monitoring
- Old sync logs can be cleaned up automatically
- Database operations are optimized with proper indexes 