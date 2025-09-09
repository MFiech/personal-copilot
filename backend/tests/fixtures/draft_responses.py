"""
Test fixtures for draft system responses.
Following the pattern of composio_responses.py for consistent test data.
"""

import time
from datetime import datetime, timedelta


# Draft creation fixtures
def create_email_draft_fixture(
    draft_id="test_draft_email_123",
    thread_id="test_thread_123", 
    message_id="test_message_456",
    subject="Test Email Subject",
    body="Test email body content",
    to_emails=None,
    status="active"
):
    """Create email draft fixture with customizable fields"""
    if to_emails is None:
        to_emails = [{"email": "test@example.com", "name": "Test User"}]
    
    return {
        "draft_id": draft_id,
        "draft_type": "email",
        "thread_id": thread_id,
        "message_id": message_id,
        "status": status,
        "subject": subject,
        "body": body,
        "to_emails": to_emails,
        "attachments": [],
        "summary": None,
        "start_time": None,
        "end_time": None,
        "attendees": [],
        "location": None,
        "description": None,
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }


def create_calendar_draft_fixture(
    draft_id="test_draft_calendar_123",
    thread_id="test_thread_123",
    message_id="test_message_456", 
    summary="Test Meeting",
    start_time="2025-09-10T15:00:00",
    end_time="2025-09-10T16:00:00",
    attendees=None,
    location="Conference Room A",
    status="active"
):
    """Create calendar draft fixture with customizable fields"""
    if attendees is None:
        attendees = [{"email": "attendee@example.com", "name": "Test Attendee"}]
    
    return {
        "draft_id": draft_id,
        "draft_type": "calendar_event",
        "thread_id": thread_id,
        "message_id": message_id,
        "status": status,
        "subject": None,
        "body": None,
        "to_emails": [],
        "attachments": [],
        "summary": summary,
        "start_time": start_time,
        "end_time": end_time,
        "attendees": attendees,
        "location": location,
        "description": "Test meeting description",
        "created_at": int(time.time()),
        "updated_at": int(time.time())
    }


# LLM response fixtures for draft intent detection
DRAFT_CREATION_INTENT_TRUE = {
    "is_draft_intent": True,
    "draft_data": {
        "draft_type": "email",
        "extracted_info": {
            "to_contacts": ["john@example.com"],
            "subject": "Test Subject",
            "body": "Test body content"
        }
    }
}

DRAFT_CREATION_INTENT_FALSE = {
    "is_draft_intent": False,
    "draft_data": None
}

DRAFT_UPDATE_INTENT_TRUE = {
    "is_update_intent": True,
    "update_category": "subject_title",
    "confidence": "high"
}

DRAFT_UPDATE_INTENT_FALSE = {
    "is_update_intent": False,
    "update_category": None,
    "confidence": "high"
}

DRAFT_FIELD_UPDATE_SUBJECT = {
    "field_updates": {
        "subject": "Generated Subject Based on Content"
    }
}

DRAFT_FIELD_UPDATE_RECIPIENTS = {
    "field_updates": {
        "to_emails": [{"email": "new@example.com", "name": "New User"}]
    }
}

DRAFT_FIELD_UPDATE_COMPLETION = {
    "field_updates": {}  # No updates, just completion signal
}

# Draft validation fixtures
DRAFT_VALIDATION_COMPLETE_EMAIL = {
    "is_complete": True,
    "missing_fields": [],
    "field_count": {
        "total_fields": 3,
        "completed_fields": 3,
        "completion_percentage": 100.0
    }
}

DRAFT_VALIDATION_INCOMPLETE_EMAIL = {
    "is_complete": False,
    "missing_fields": ["subject", "body"],
    "field_count": {
        "total_fields": 3,
        "completed_fields": 1,
        "completion_percentage": 33.3
    }
}

DRAFT_VALIDATION_COMPLETE_CALENDAR = {
    "is_complete": True,
    "missing_fields": [],
    "field_count": {
        "total_fields": 4,
        "completed_fields": 4,
        "completion_percentage": 100.0
    }
}

DRAFT_VALIDATION_INCOMPLETE_CALENDAR = {
    "is_complete": False,
    "missing_fields": ["start_time", "end_time"],
    "field_count": {
        "total_fields": 4,
        "completed_fields": 2,
        "completion_percentage": 50.0
    }
}

# Composio integration fixtures
COMPOSIO_SEND_EMAIL_SUCCESS = {
    "successful": True,
    "data": {
        "messageId": "sent_message_123",
        "threadId": "thread_456",
        "labelIds": ["SENT"]
    },
    "error": None
}

COMPOSIO_SEND_EMAIL_ERROR = {
    "successful": False,
    "data": None,
    "error": "Failed to send email: Invalid recipient"
}

# Cross-thread contamination test fixtures
def create_cross_thread_draft_scenario():
    """Create scenario for testing cross-thread contamination prevention"""
    return {
        "current_thread": "thread_current_123",
        "other_thread": "thread_other_456",
        "current_draft": create_email_draft_fixture(
            draft_id="current_draft_123",
            thread_id="thread_current_123",
            subject="Current Thread Draft"
        ),
        "other_draft": create_email_draft_fixture(
            draft_id="other_draft_456", 
            thread_id="thread_other_456",
            subject="Other Thread Draft"
        )
    }

# Data staleness test fixtures
def create_stale_data_scenario():
    """Create scenario for testing data staleness prevention"""
    return {
        "anchored_draft_stale": create_email_draft_fixture(
            draft_id="stale_draft_123",
            body=None,  # Stale data shows no body
            status="active"
        ),
        "database_draft_fresh": create_email_draft_fixture(
            draft_id="stale_draft_123",
            body="Fresh body content from database",  # Fresh data has body
            status="active"
        )
    }

# Performance test fixtures
def create_large_thread_drafts(count=50):
    """Create large number of drafts for performance testing"""
    drafts = []
    base_time = int(time.time())
    
    for i in range(count):
        draft = create_email_draft_fixture(
            draft_id=f"perf_draft_{i}",
            thread_id="perf_thread_123",
            message_id=f"perf_message_{i}",
            subject=f"Performance Test Email {i}",
            body=f"This is performance test email number {i} with content.",
            created_at=base_time + i,
            updated_at=base_time + i
        )
        drafts.append(draft)
    
    return drafts

# Error recovery test fixtures  
def create_composio_error_recovery_scenario():
    """Create scenario for testing Composio error recovery"""
    return {
        "draft_with_error": create_email_draft_fixture(
            draft_id="error_draft_123",
            status="composio_error",
            subject="Failed Draft",
            body="This draft failed to send"
        ),
        "update_data": {
            "body": "Updated body content after error"
        },
        "expected_status_change": "active"  # Should reset to active after update
    }

# Content extraction test fixtures
CONVERSATION_WITH_DRAFT_CONTENT = [
    {"role": "user", "content": "Create a draft email to John about the meeting"},
    {"role": "assistant", "content": "I'll create an email draft for you. Here's what I'll include:\n\nSubject: Meeting Discussion\n\nDear John,\n\nI wanted to reach out regarding our upcoming meeting. Please let me know your availability.\n\nBest regards"},
    {"role": "user", "content": "that's all"}
]

EXPECTED_EXTRACTED_CONTENT = {
    "subject": "Meeting Discussion", 
    "body": "Dear John,\n\nI wanted to reach out regarding our upcoming meeting. Please let me know your availability.\n\nBest regards"
}

# Routing logic test fixtures
def create_routing_test_scenarios():
    """Create various scenarios for testing draft routing logic"""
    return {
        "no_draft_anchored_creation": {
            "query": "Create a draft email to John",
            "anchored_item": None,
            "expected_route": "draft_creation"
        },
        "draft_anchored_update": {
            "query": "Add his email address",
            "anchored_item": {
                "type": "draft",
                "data": create_email_draft_fixture()
            },
            "expected_route": "draft_update"
        },
        "non_draft_anchored_tooling": {
            "query": "Postpone this event by 1 hour",
            "anchored_item": {
                "type": "calendar_event",
                "data": {"event_id": "calendar_123", "title": "Test Event"}
            },
            "expected_route": "tooling_service"
        }
    }
