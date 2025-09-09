# PM Co-Pilot Drafts System - Comprehensive Analysis

> **Session Reference Document**: This file contains complete analysis of the drafts functionality in PM Co-Pilot for use across development sessions.

## 📋 Overview

The PM Co-Pilot application implements a sophisticated drafts system that allows users to create, manage, and execute email and calendar event drafts through natural language conversations, with intelligent LLM assistance and seamless Composio integration.

## 🎯 Draft Types and Structure

### 1. Email Drafts (`draft_type: "email"`)
- **Structure**: Recipients (to_emails), subject, body, attachments
- **Required fields**: to_emails, subject, body
- **Storage**: MongoDB collection with email-specific validation
- **Contact Resolution**: Automatic conversion of contact names to email addresses

### 2. Calendar Event Drafts (`draft_type: "calendar_event"`)
- **Structure**: Event summary, start_time, end_time, attendees, location, description
- **Required fields**: summary, start_time, end_time
- **Storage**: MongoDB collection with calendar-specific validation
- **Time Handling**: Intelligent parsing of natural language time expressions

### Common Draft Properties
- **Status**: "active", "closed", or "composio_error"
- **Timestamps**: created_at, updated_at
- **Relationships**: thread_id (conversation context), message_id (triggering message)
- **Unique identifier**: draft_id (UUID)

## 🔄 Draft Lifecycle

### 1. Creation Phase
- **Trigger**: LLM intent detection or manual API calls
- **Data Source**: User input + conversation context
- **Processing**: Contact resolution, field validation
- **Storage**: MongoDB persistence with schema validation

### 2. Population & Updates
- **Iterative Refinement**: Through conversation interactions
- **Context Awareness**: Existing draft data prevents re-extraction
- **Update Mode**: Only extracts newly specified fields
- **Validation**: Continuous completeness checking

### 3. Validation Phase
- **Real-time Checking**: Against required field sets
- **Missing Field Detection**: User-friendly field mapping
- **Completeness Status**: Boolean with detailed field list

### 4. Execution Phase
- **Parameter Conversion**: Draft → Composio API format
- **API Integration**: Gmail/Google Calendar via Composio
- **Status Management**: Success → "closed", Failure → "composio_error"

## 🤖 LLM Integration Flow

### Intent Detection Workflow

**Step 1** - User Query → App Backend:
```json
{
  "query": "Send email to John about meeting tomorrow", 
  "thread_id": "123"
}
```

**Step 2** - App Backend → LLM (Claude Haiku):
```json
{
  "prompt": "Draft detection prompt with conversation history",
  "model": "claude-3-haiku-20240307"
}
```

**Step 3** - LLM → App Backend:
```json
{
  "is_draft_intent": true,
  "draft_data": {
    "draft_type": "email",
    "to_contacts": ["John"],
    "subject": "Meeting Tomorrow",
    "body": "Hi John, I wanted to discuss our meeting scheduled for tomorrow..."
  }
}
```

**Step 4** - App Backend Processing:
- Contact resolution (John → john@company.com)
- Draft creation with resolved data
- MongoDB storage

### Update Detection Flow

**Step 1** - User Query (with existing draft context):
```json
{
  "query": "Actually, add Sarah to that email", 
  "anchored_item": {"type": "draft", "id": "draft_123"}
}
```

**Step 2** - App Backend → LLM:
```json
{
  "prompt": "Update mode prompt with existing draft context",
  "existing_draft": {
    "attendees": ["john@company.com"], 
    "subject": "Meeting Tomorrow"
  }
}
```

**Step 3** - LLM → App Backend:
```json
{
  "is_draft_intent": true,
  "draft_data": {
    "to_contacts": ["Sarah"]  // Only the NEW contact, not existing ones
  }
}
```

**Step 4** - Draft Update:
- Merge new contacts with existing ones
- Validate completeness
- Update MongoDB record

### Context Integration Features
- **Draft Context Injection**: Active drafts influence conversation prompts
- **Completeness Guidance**: LLM responses reflect missing field status
- **Update Mode Protection**: Prevents re-extraction of existing data
- **Conversation Memory**: Maintains draft state across message exchanges

## 🔗 Composio Integration

### Execution Flow

**Step 1** - User Trigger → App Backend:
```json
{"action": "send_draft", "draft_id": "draft_123"}
```

**Step 2** - App Backend Validation:
```json
{
  "validation": {
    "is_complete": true,
    "missing_fields": []
  }
}
```

**Step 3** - Draft → Composio Parameter Conversion:

For emails:
```json
{
  "to": ["john@company.com", "sarah@company.com"],
  "subject": "Meeting Tomorrow",
  "body": "Hi team, I wanted to discuss...",
  "attachments": []
}
```

For calendar events:
```json
{
  "summary": "Team Meeting",
  "start_time": "2024-01-15T14:00:00",
  "end_time": "2024-01-15T15:00:00",
  "location": "Conference Room A",
  "attendees": ["john@company.com"]
}
```

**Step 4** - App Backend → Composio API:
- Email: `composio_service.send_email(params)` (currently placeholder)
- Calendar: `composio_service.create_calendar_event(params)`

**Step 5** - Composio → External Services:
- Gmail API for email sending
- Google Calendar API for event creation

**Step 6** - Result Processing:
```json
{
  "successful": true,
  "data": {"message_id": "gmail_123", "status": "sent"}
}
```

**Step 7** - Draft Status Update:
- Success: status → "closed"
- Failure: status → "composio_error"

## ⚓ Anchoring System Integration

### Auto-Anchoring Flow

**Step 1** - Draft Creation Response → Frontend:
```json
{
  "success": true,
  "draft": {"draft_id": "draft_123", "draft_type": "email"},
  "message": "Created email draft successfully"
}
```

**Step 2** - Frontend Auto-Anchoring:
```json
{
  "anchored_item": {
    "id": "draft_123",
    "type": "draft",
    "data": {full_draft_object}
  }
}
```

**Step 3** - Frontend → Backend URL Update:
- Query params: `?anchorType=draft&anchorId=draft_123`
- State management: `setAnchoredItem(anchorData)`

### Anchored Context in Conversations

**Step 1** - User Query with Anchored Draft → App Backend:
```json
{
  "query": "Change the subject line",
  "anchored_item": {
    "type": "draft",
    "id": "draft_123",
    "data": {draft_object}
  }
}
```

**Step 2** - App Backend Context Building:
```json
{
  "draft_context": {
    "type": "active_draft",
    "draft_id": "draft_123",
    "draft_type": "email",
    "summary": "Email to John, Sarah - Subject: Meeting Tomorrow",
    "is_complete": false,
    "missing_fields": ["body"]
  }
}
```

**Step 3** - LLM Prompt Enhancement:
- Draft context injected into system prompt
- Current completeness status provided
- Missing fields highlighted
- Update mode instructions included

### Validation Integration

**Step 1** - Draft Anchoring → Frontend Validation Request:
```json
{"action": "validate_draft", "draft_id": "draft_123"}
```

**Step 2** - Backend Validation Response:
```json
{
  "validation": {
    "is_complete": false,
    "missing_fields": ["body"]
  }
}
```

**Step 3** - Frontend UI Updates:
- Orange completion bar showing missing fields
- Send button enable/disable based on completeness
- Field-specific validation indicators

## 📁 File Architecture

### Backend Core Files
- **`backend/models/draft.py`**: Draft data model with MongoDB integration
- **`backend/services/draft_service.py`**: Business logic and LLM integration
- **`backend/config/mongo_schema.py`**: Database schema definitions
- **`backend/app.py`**: REST API endpoints for draft operations

### Frontend Files
- **`frontend/src/utils/draftService.js`**: API client for draft operations
- **`frontend/src/App.js`**: Main application with anchoring logic
- **`frontend/test_drafts.html`**: Manual testing interface

### Testing Files
- **`backend/test_draft_system.py`**: Comprehensive integration tests
- **`backend/tests/test_langfuse_standardization_phase6.py`**: Langfuse integration tests

## 🛠️ API Endpoints

### Core CRUD Operations
- **POST** `/drafts` - Create new draft
- **GET** `/drafts/{draft_id}` - Retrieve draft by ID
- **PUT** `/drafts/{draft_id}` - Update draft fields
- **GET** `/drafts/{draft_id}/validate` - Check completeness
- **POST** `/drafts/{draft_id}/send` - Execute draft via Composio
- **POST** `/drafts/{draft_id}/close` - Close draft with status

### Query Operations
- **GET** `/drafts/thread/{thread_id}` - Get all drafts for thread
- **GET** `/drafts/message/{message_id}` - Get draft by message ID

### Request/Response Formats

Create Draft Request:
```json
{
  "draft_type": "email",
  "thread_id": "thread_123",
  "message_id": "msg_456",
  "initial_data": {
    "to_emails": [{"email": "john@example.com", "name": "John"}],
    "subject": "Meeting Tomorrow"
  }
}
```

Update Draft Request:
```json
{
  "updates": {
    "body": "Updated email content",
    "to_contacts": ["Sarah Smith"]
  }
}
```

Validation Response:
```json
{
  "validation": {
    "is_complete": false,
    "missing_fields": ["body"]
  }
}
```

## 🧪 Current Testing Coverage

### 1. Comprehensive Integration Tests (`test_draft_system.py`)
- **Database Setup**: Collection existence, schema validation
- **Draft Model**: CRUD operations, validation, thread queries
- **Draft Service**: Contact resolution, LLM integration, Composio conversion
- **API Endpoints**: All REST endpoints with real HTTP requests

### 2. Langfuse Integration Tests
- Service initialization with proper client configuration
- `@observe` decorator presence verification
- Testing environment isolation

### 3. Frontend Manual Testing
- Interactive browser-based API testing
- Error handling validation
- UI integration verification

## 🚫 Testing Gaps

### Missing Unit Tests
- `detect_draft_intent()` method with mocked LLM responses
- Draft detection prompt generation and parsing
- Contact resolution logic isolation
- Intent extraction from conversation history

### Missing Integration Tests
- Auto-anchoring behavior when drafts are created
- Draft context injection into conversation prompts
- Anchored draft URL handling and state management
- Actual Composio execution (currently placeholder)

### Missing Frontend Tests
- React component testing for draft UI elements
- Draft state management and validation behavior
- Send button enable/disable logic
- Error handling in UI components

## 💡 Key Insights & Best Practices

### LLM Integration
- **Update Mode Critical**: Prevents re-extraction of existing draft data
- **Context Awareness**: Existing draft information guides LLM responses
- **Time Handling**: Never auto-generate times without explicit user input
- **Contact Resolution**: Automatic email lookup from contact database

### Anchoring Benefits
- **Seamless Context**: Drafts automatically become conversation focus
- **Real-time Validation**: Immediate feedback on completeness
- **URL Persistence**: Shareable links maintain draft context
- **State Management**: Frontend/backend synchronization

### Error Handling
- **Graceful Degradation**: System continues functioning with incomplete drafts
- **Status Tracking**: Clear status progression (active → closed/error)
- **Validation Feedback**: User-friendly missing field descriptions
- **MongoDB Schema**: Enforced data integrity at database level

### Performance Considerations
- **Contact Caching**: Resolved contacts stored for reuse
- **Incremental Updates**: Only modified fields trigger database writes
- **Validation Caching**: Completeness checks cached until changes
- **MongoDB Indexing**: Optimized queries by thread_id and message_id