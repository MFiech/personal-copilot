# VeyraX Integration for PM Co-Pilot

This document explains how to set up and use the VeyraX integration with PM Co-Pilot to access Gmail and Google Calendar data.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Setup](#setup)
3. [Testing the Integration](#testing-the-integration)
4. [Troubleshooting](#troubleshooting)
5. [API Documentation](#api-documentation)

## Prerequisites

Before using the VeyraX integration, ensure you have:

1. A VeyraX account with API access
2. Connected Gmail/Mail in your VeyraX account
3. Connected Google Calendar in your VeyraX account
4. A VeyraX API key

## Setup

1. **Set up your environment variables**

   Add your VeyraX API key to your `.env` file:

   ```
   VEYRAX_API_KEY=your_api_key_here
   ```

2. **Ensure the correct service is being used**

   In your application code, make sure you're importing and using the VeyraXService:

   ```python
   from services.veyrax_service import VeyraXService
   
   # Initialize the service
   veyrax_service = VeyraXService()
   
   # Now you can use methods like:
   # - veyrax_service.get_recent_emails()
   # - veyrax_service.get_upcoming_events()
   ```

## Testing the Integration

We've provided several test scripts to verify your VeyraX integration:

1. **Basic connection test**

   ```bash
   cd pm-copilot/backend
   python scripts/test_veyrax_connection.py
   ```

   This script tests basic connectivity to the VeyraX API and attempts to access Gmail and Google Calendar data.

2. **Detailed API endpoint test**

   ```bash
   cd pm-copilot/backend
   python scripts/simple_veyrax_test.py
   ```

   This script tests specific API endpoints with detailed request/response information for debugging.

## Troubleshooting

If you encounter issues with the VeyraX integration:

1. **Check your API key**
   - Verify that your VEYRAX_API_KEY is correctly set in the .env file
   - Ensure there are no extra spaces or characters

2. **Check your VeyraX account**
   - Log into your VeyraX account and ensure Gmail/Mail is connected
   - Verify that Google Calendar is connected
   - Check that you have the appropriate permissions for these services

3. **Common errors and solutions**

   | Error | Possible Solution |
   |-------|-------------------|
   | "Authentication failed" | Check your API key |
   | "Tool not available" | Connect the service in your VeyraX account |
   | "Method not found" | Verify the method name matches the documentation |
   | "Bad request" | Check the parameters you're sending |

4. **Run the diagnostic scripts**
   - The test scripts will help pinpoint where the issue is occurring

## API Documentation

### Mail/Gmail Methods

- `get_recent_emails(count=10, query=None, folder="INBOX", offset=0, mark_as_read=False)`
  - Gets recent emails from Gmail
  - Returns email data or error message

- `get_email_message(message_id, mark_as_read=False)`
  - Gets a specific email message
  - Returns email message data or error message

- `send_email(to, subject, body_text=None, body_html=None, cc=None, bcc=None)`
  - Sends an email
  - Returns response data or error message

- `get_email_folders(include_counts=False)`
  - Gets email folders
  - Returns folder data or error message

- `test_mail_connection()`
  - Tests connection to SMTP and IMAP servers
  - Returns connection test results or error message

### Google Calendar Methods

- `get_upcoming_events(days=7, max_results=10)`
  - Gets upcoming calendar events
  - Returns calendar event data or error message

- `get_calendar_event(event_id, calendar_id="primary")`
  - Gets details of a specific calendar event
  - Returns event data or error message

- `create_calendar_event(summary, start_time, end_time, location=None, description=None, attendees=None, calendar_id="primary")`
  - Creates a new calendar event
  - Returns created event data or error message

- `list_calendars()`
  - Lists all available calendars
  - Returns calendar list data or error message

- `get_events_for_date(date=None)`
  - Gets calendar events for a specific date
  - Returns calendar event data or error message

## Response Formats

### Gmail/Mail Responses

Successful response for getting messages:
```json
{
  "data": {
    "limit": 10,
    "total": 42,
    "offset": 0,
    "messages": [
      {
        "cc": [],
        "id": "123456",
        "to": [
          {
            "name": "Jane Smith",
            "email": "jane.smith@example.com"
          }
        ],
        "bcc": [],
        "body": {
          "html": "<p>Email content</p>",
          "text": "Email content"
        },
        "date": "Mon, 10 Jul 2023 10:30:45 +0000",
        "size": 2045,
        "folder": "INBOX",
        "headers": [],
        "is_read": false,
        "subject": "Email Subject",
        "from_email": {
          "name": "John Doe",
          "email": "john.doe@example.com"
        },
        "attachments": []
      }
    ]
  }
}
```

### Google Calendar Responses

Successful response for listing events:
```json
{
  "data": {
    "items": [
      {
        "id": "evt123456789",
        "end": "2023-05-02T11:00:00Z",
        "start": "2023-05-02T10:00:00Z",
        "status": "confirmed",
        "creator": {
          "email": "organizer@example.com",
          "displayName": "Meeting Organizer"
        },
        "summary": "Weekly Team Meeting",
        "htmlLink": "https://www.google.com/calendar/event?eid=abc123",
        "location": "Conference Room A",
        "attendees": [
          {
            "email": "person1@example.com",
            "displayName": "Person One",
            "responseStatus": "accepted"
          }
        ],
        "description": "Meeting description"
      }
    ],
    "nextPageToken": null
  }
}
``` 