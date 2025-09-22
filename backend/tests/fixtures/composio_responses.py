"""
Real API response fixtures for Composio services.
These are sanitized versions of actual API responses to ensure tests reflect real behavior.
"""

import base64

# Gmail API Responses
GMAIL_FETCH_MESSAGE_SUCCESS_SIMPLE = {
    "successful": True,
    "data": {
        "messageId": "1991e5b04c210c80",
        "messageText": "Hi there,\n\nThis is a simple test email with plain text content.\n\nBest regards,\nTest User",
        "messageTimestamp": "2025-09-06T09:28:25Z",
        "payload": {
            "body": {"size": 0},
            "filename": "",
            "headers": [
                {"name": "Subject", "value": "Test Email Subject"},
                {"name": "From", "value": "Test User <test@example.com>"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Date", "value": "Sat, 06 Sep 2025 09:28:25 +0000"}
            ],
            "mimeType": "text/plain",
            "partId": ""
        },
        "subject": "Test Email Subject",
        "sender": "Test User <test@example.com>",
        "to": "recipient@example.com",
        "threadId": "1990a0c3f4744b10",
        "labelIds": ["INBOX"],
        "attachmentList": []
    },
    "error": None,
    "logId": "log_test123"
}

GMAIL_FETCH_MESSAGE_SUCCESS_MULTIPART = {
    "successful": True,
    "data": {
        "messageId": "1991e5b04c210c81",
        "messageText": "Hi there,\n\nThis is a multipart test email.\n\nBest regards,\nTest User",
        "messageTimestamp": "2025-09-06T09:30:00Z",
        "payload": {
            "body": {"size": 0},
            "filename": "",
            "headers": [
                {"name": "Subject", "value": "Multipart Test Email"},
                {"name": "From", "value": "Test User <test@example.com>"},
                {"name": "To", "value": "recipient@example.com"},
                {"name": "Content-Type", "value": "multipart/alternative; boundary=\"test-boundary\""}
            ],
            "mimeType": "multipart/alternative",
            "partId": "",
            "parts": [
                {
                    "body": {
                        "data": base64.urlsafe_b64encode("Hi there,\n\nThis is plain text content.\n\nBest regards,\nTest User".encode()).decode(),
                        "size": 64
                    },
                    "filename": "",
                    "headers": [
                        {"name": "Content-Type", "value": "text/plain; charset=\"utf-8\""}
                    ],
                    "mimeType": "text/plain",
                    "partId": "0"
                },
                {
                    "body": {
                        "data": base64.urlsafe_b64encode("<html><body><p>Hi there,</p><p>This is <strong>HTML</strong> content.</p><p>Best regards,<br>Test User</p></body></html>".encode()).decode(),
                        "size": 128
                    },
                    "filename": "",
                    "headers": [
                        {"name": "Content-Type", "value": "text/html; charset=\"utf-8\""}
                    ],
                    "mimeType": "text/html",
                    "partId": "1"
                }
            ]
        },
        "subject": "Multipart Test Email",
        "sender": "Test User <test@example.com>",
        "to": "recipient@example.com",
        "threadId": "1990a0c3f4744b11",
        "labelIds": ["INBOX"],
        "attachmentList": []
    },
    "error": None,
    "logId": "log_test124"
}

GMAIL_FETCH_MESSAGE_NOT_FOUND = {
    "successful": False,
    "error": "Requested entity was not found.",
    "data": None,
    "logId": "log_test125"
}

GMAIL_SEARCH_EMAILS_SUCCESS = {
    "successful": True,
    "data": {
        "messages": [
            {
                "messageId": "198efca4a33ef48d",
                "thread_id": "thread_123",
                "subject": "Test Email 1",
                "messageText": "First test email content",
                "date": "1640995200",
                "from": {"name": "Test Sender 1", "email": "sender1@example.com"},
                "to": [{"name": "Test Receiver", "email": "receiver@example.com"}],
                "labelIds": ["INBOX"],
                "attachmentList": []
            },
            {
                "messageId": "298efca4a33ef48e",
                "thread_id": "thread_124",
                "subject": "Test Email 2",
                "messageText": "Second test email content",
                "date": "1640995300",
                "from": {"name": "Test Sender 2", "email": "sender2@example.com"},
                "to": [{"name": "Test Receiver", "email": "receiver@example.com"}],
                "labelIds": ["INBOX", "IMPORTANT"],
                "attachmentList": []
            }
        ],
        "nextPageToken": None,
        "resultSizeEstimate": 2
    },
    "error": None,
    "logId": "log_search123"
}

GMAIL_THREAD_SUCCESS = {
    "successful": True,
    "data": {
        "id": "thread_123",
        "messages": [
            {
                "messageId": "msg_1",  # Changed from "id" to "messageId"
                "threadId": "thread_123",
                "labelIds": ["INBOX"],
                "snippet": "First message in thread",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Thread Subject"},
                        {"name": "From", "value": "user1@example.com"},
                        {"name": "To", "value": "user2@example.com"},
                        {"name": "Date", "value": "Mon, 01 Jan 2024 12:00:00 +0000"}
                    ],
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode("First message content".encode()).decode()
                    }
                },
                "internalDate": "1704110400000"
            },
            {
                "messageId": "msg_2",  # Changed from "id" to "messageId"
                "threadId": "thread_123",
                "labelIds": ["INBOX"],
                "snippet": "Second message in thread",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Re: Thread Subject"},
                        {"name": "From", "value": "user2@example.com"},
                        {"name": "To", "value": "user1@example.com"},
                        {"name": "Date", "value": "Mon, 01 Jan 2024 12:30:00 +0000"}
                    ],
                    "mimeType": "text/plain",
                    "body": {
                        "data": base64.urlsafe_b64encode("Second message content".encode()).decode()
                    }
                },
                "internalDate": "1704112200000"
            }
        ]
    },
    "error": None,
    "logId": "log_thread123"
}

# Calendar API Responses
CALENDAR_EVENTS_SUCCESS = {
    "successful": True,
    "data": {
        "items": [
            {
                "id": "event_123",
                "summary": "Test Meeting 1",
                "description": "This is a test meeting",
                "start": {
                    "dateTime": "2025-09-06T14:00:00+02:00",
                    "timeZone": "Europe/Berlin"
                },
                "end": {
                    "dateTime": "2025-09-06T15:00:00+02:00",
                    "timeZone": "Europe/Berlin"
                },
                "location": "Conference Room A",
                "attendees": [
                    {"email": "attendee1@example.com", "responseStatus": "accepted"},
                    {"email": "attendee2@example.com", "responseStatus": "needsAction"}
                ],
                "creator": {"email": "creator@example.com"},
                "organizer": {"email": "organizer@example.com"}
            },
            {
                "id": "event_124",
                "summary": "Test Meeting 2",
                "description": "Another test meeting",
                "start": {
                    "dateTime": "2025-09-06T16:00:00+02:00",
                    "timeZone": "Europe/Berlin"
                },
                "end": {
                    "dateTime": "2025-09-06T17:00:00+02:00",
                    "timeZone": "Europe/Berlin"
                },
                "location": "Conference Room B",
                "attendees": [],
                "creator": {"email": "creator@example.com"},
                "organizer": {"email": "organizer@example.com"}
            }
        ],
        "nextPageToken": None,
        "timeMin": "2025-09-06T00:00:00+02:00",
        "timeMax": "2025-09-13T23:59:59+02:00"
    },
    "error": None,
    "logId": "log_calendar123"
}

CALENDAR_CREATE_EVENT_SUCCESS = {
    "successful": True,
    "data": {
        "id": "event_new_123",
        "summary": "New Test Meeting",
        "description": "This is a newly created test meeting",
        "start": {
            "dateTime": "2025-09-07T10:00:00+02:00",
            "timeZone": "Europe/Berlin"
        },
        "end": {
            "dateTime": "2025-09-07T11:00:00+02:00",
            "timeZone": "Europe/Berlin"
        },
        "location": "Conference Room C",
        "attendees": [
            {"email": "attendee@example.com", "responseStatus": "needsAction"}
        ],
        "creator": {"email": "creator@example.com"},
        "organizer": {"email": "creator@example.com"},
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?eid=test123",
        "created": "2025-09-06T12:00:00Z",
        "updated": "2025-09-06T12:00:00Z"
    },
    "error": None,
    "logId": "log_create123"
}

GMAIL_MOVE_TO_TRASH_SUCCESS = {
    "successful": True,
    "data": {
        "message": "Message moved to trash successfully",
        "messageId": "19971444a7ca648b"
    },
    "error": None,
    "logId": "log_gmail_trash123"
}

GMAIL_MOVE_TO_TRASH_FAILURE = {
    "successful": False,
    "error": "Message not found or already deleted",
    "data": None,
    "logId": "log_gmail_trash_fail123"
}

CALENDAR_DELETE_EVENT_SUCCESS = {
    "successful": True,
    "data": {
        "message": "Event deleted successfully",
        "eventId": "event_123"
    },
    "error": None,
    "logId": "log_delete123"
}

CALENDAR_EVENT_NOT_FOUND = {
    "successful": False,
    "error": "Event not found",
    "data": None,
    "logId": "log_notfound123"
}

# Error responses
COMPOSIO_API_ERROR = {
    "successful": False,
    "error": "API rate limit exceeded",
    "data": None,
    "logId": "log_error123"
}

COMPOSIO_INVALID_AUTH = {
    "successful": False,
    "error": "Invalid authentication credentials",
    "data": None,
    "logId": "log_auth_error123"
}

# Helper function to create custom fixtures
def create_email_fixture_with_content(content: str, email_id: str = "test_email", is_html: bool = False):
    """Create a custom email fixture with specified content"""
    mime_type = "text/html" if is_html else "text/plain"
    encoded_content = base64.urlsafe_b64encode(content.encode()).decode()
    
    return {
        "successful": True,
        "data": {
            "messageId": email_id,
            "messageText": content,
            "messageTimestamp": "2025-09-06T12:00:00Z",
            "payload": {
                "body": {"data": encoded_content, "size": len(content)},
                "mimeType": mime_type,
                "headers": [
                    {"name": "Subject", "value": "Test Email"},
                    {"name": "From", "value": "test@example.com"}
                ]
            },
            "subject": "Test Email",
            "sender": "test@example.com",
            "threadId": "test_thread",
            "labelIds": ["INBOX"],
            "attachmentList": []
        },
        "error": None,
        "logId": "log_custom123"
    }

def create_calendar_event_fixture(event_id: str, summary: str, start_time: str, end_time: str = None):
    """Create a custom calendar event fixture"""
    if not end_time:
        # Default to 1 hour duration
        from datetime import datetime, timedelta
        start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(hours=1)
        end_time = end_dt.isoformat()
    
    return {
        "successful": True,
        "data": {
            "id": event_id,
            "summary": summary,
            "start": {"dateTime": start_time, "timeZone": "Europe/Berlin"},
            "end": {"dateTime": end_time, "timeZone": "Europe/Berlin"},
            "creator": {"email": "creator@example.com"},
            "organizer": {"email": "creator@example.com"},
            "status": "confirmed"
        },
        "error": None,
        "logId": f"log_{event_id}"
    }
