from datetime import datetime

# Schema for conversations collection
CONVERSATIONS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["thread_id", "message_id", "role", "content", "timestamp"],
            "properties": {
                "thread_id": {
                    "bsonType": "string",
                    "description": "Unique identifier for the conversation thread"
                },
                "message_id": {
                    "bsonType": "string",
                    "description": "Unique identifier for the individual message"
                },
                "role": {
                    "bsonType": "string",
                    "enum": ["user", "assistant"],
                    "description": "Role of the message sender"
                },
                "content": {
                    "bsonType": "string",
                    "description": "Content of the message"
                },
                "timestamp": {
                    "bsonType": "int",
                    "description": "Unix timestamp of the message"
                },
                "insight_id": {
                    "bsonType": ["string", "null"],
                    "description": "Reference to related insight if applicable"
                },
                "veyra_results": {
                    "bsonType": ["object", "null"],
                    "description": "Results from VeyraX service",
                    "properties": {
                        "emails": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "string",
                                "description": "Email ID from emails collection"
                            },
                            "description": "Array of email IDs referenced from emails collection"
                        },
                        "calendar_events": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "object",
                                "properties": {
                                    "id": {
                                        "bsonType": "string",
                                        "description": "Event ID from Google Calendar"
                                    },
                                    "summary": {
                                        "bsonType": ["string", "null"],
                                        "description": "Event title/summary"
                                    },
                                    "description": {
                                        "bsonType": ["string", "null"],
                                        "description": "Event description"
                                    },
                                    "location": {
                                        "bsonType": ["string", "null"],
                                        "description": "Event location"
                                    },
                                    "start": {
                                        "anyOf": [
                                            {"bsonType": "string"},
                                            {"bsonType": "object"}
                                        ],
                                        "description": "Event start time"
                                    },
                                    "end": {
                                        "anyOf": [
                                            {"bsonType": "string"},
                                            {"bsonType": "object"}
                                        ],
                                        "description": "Event end time"
                                    },
                                    "attendees": {
                                        "bsonType": ["array", "null"],
                                        "description": "Event attendees"
                                    },
                                    "htmlLink": {
                                        "bsonType": ["string", "null"],
                                        "description": "Link to the event in Google Calendar"
                                    },
                                    "creator": {
                                        "bsonType": ["object", "null"],
                                        "description": "Event creator information"
                                    },
                                    "status": {
                                        "bsonType": ["string", "null"],
                                        "description": "Event status (confirmed, tentative, cancelled)"
                                    }
                                }
                            }
                        }
                    }
                },
                "metadata": {
                    "bsonType": "object",
                    "description": "Additional metadata about the conversation",
                    "properties": {
                        "source": {
                            "bsonType": "string",
                            "enum": ["chat", "email", "calendar"],
                            "description": "Source of the conversation"
                        },
                        "context": {
                            "bsonType": "object",
                            "description": "Context information for the conversation"
                        },
                        "tags": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "string"
                            },
                            "description": "Tags associated with the conversation"
                        }
                    }
                }
            }
        }
    }
}

# Schema for insights collection
INSIGHTS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["insight_id", "content", "timestamp", "source"],
            "properties": {
                "insight_id": {
                    "bsonType": "string",
                    "description": "Unique identifier for the insight"
                },
                "content": {
                    "bsonType": "string",
                    "description": "The insight content"
                },
                "timestamp": {
                    "bsonType": "string",
                    "description": "ISO format timestamp of when the insight was created"
                },
                "source": {
                    "bsonType": "string",
                    "enum": ["user", "clickup", "help_center", "internal_docs", "emails"],
                    "description": "Source of the insight"
                },
                "metadata": {
                    "bsonType": "object",
                    "description": "Source-specific metadata",
                    "properties": {
                        # Clickup metadata
                        "owner_id": {
                            "bsonType": "string",
                            "description": "Clickup task owner ID"
                        },
                        "ticket_owner": {
                            "bsonType": "string",
                            "description": "Clickup ticket owner ID"
                        },
                        "task_id": {
                            "bsonType": "string",
                            "description": "Clickup task ID"
                        },
                        "task_name": {
                            "bsonType": "string",
                            "description": "Clickup task name"
                        },
                        "task_url": {
                            "bsonType": "string",
                            "description": "Clickup task URL"
                        },
                        "task_type": {
                            "bsonType": "string",
                            "description": "Clickup task type"
                        },
                        "list_name": {
                            "bsonType": "string",
                            "description": "Clickup list name"
                        },
                        "folder_name": {
                            "bsonType": "string",
                            "description": "Clickup folder name"
                        },
                        "close_date": {
                            "bsonType": "string",
                            "description": "Clickup task close date"
                        },
                        "task_length": {
                            "bsonType": "double",
                            "description": "Length of the task content"
                        },
                        # Help center metadata
                        "article_name": {
                            "bsonType": "string",
                            "description": "Help center article name"
                        },
                        "article_id": {
                            "bsonType": "string",
                            "description": "Help center article ID"
                        },
                        "article_category": {
                            "bsonType": "string",
                            "description": "Help center article category"
                        },
                        "article_url": {
                            "bsonType": "string",
                            "description": "Help center article URL"
                        },
                        # Internal docs metadata
                        "sub_source": {
                            "bsonType": "string",
                            "description": "Internal docs sub-source"
                        },
                        "insight_name": {
                            "bsonType": "string",
                            "description": "Internal docs insight name"
                        },
                        "insight_url": {
                            "bsonType": "string",
                            "description": "Internal docs insight URL"
                        },
                        # Email metadata
                        "email_source": {
                            "bsonType": "string",
                            "enum": ["POSTMARK", "CMS"],
                            "description": "Email source system"
                        },
                        "template_name": {
                            "bsonType": "string",
                            "description": "Email template name or ID"
                        },
                        "email_subject": {
                            "bsonType": "string",
                            "description": "Email subject"
                        },
                        "email_body": {
                            "bsonType": "string",
                            "description": "Email body"
                        }
                    }
                },
                "vector_id": {
                    "bsonType": "string",
                    "description": "ID of the vector in Pinecone"
                },
                "tags": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "string"
                    },
                    "description": "Tags associated with the insight"
                }
            }
        }
    }
}

# Schema for emails collection
EMAILS_SCHEMA = {
    "validator": {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["email_id", "thread_id", "subject", "from_email", "date", "content"],
            "properties": {
                "email_id": {
                    "bsonType": "string",
                    "description": "Unique identifier for the email"
                },
                "thread_id": {
                    "bsonType": "string",
                    "description": "Reference to the conversation thread this email belongs to"
                },
                "subject": {
                    "bsonType": "string",
                    "description": "Email subject"
                },
                "from_email": {
                    "bsonType": "object",
                    "description": "Email sender information",
                    "required": ["email", "name"],
                    "properties": {
                        "email": {
                            "bsonType": "string",
                            "description": "Sender's email address"
                        },
                        "name": {
                            "bsonType": "string",
                            "description": "Sender's name"
                        }
                    }
                },
                "to_emails": {
                    "bsonType": "array",
                    "items": {
                        "bsonType": "object",
                        "properties": {
                            "email": {
                                "bsonType": "string",
                                "description": "Recipient's email address"
                            },
                            "name": {
                                "bsonType": "string",
                                "description": "Recipient's name"
                            }
                        }
                    },
                    "description": "List of email recipients"
                },
                "date": {
                    "bsonType": "string",
                    "description": "Email date in ISO format"
                },
                "content": {
                    "bsonType": "object",
                    "required": ["html", "text"],
                    "properties": {
                        "html": {
                            "bsonType": "string",
                            "description": "HTML content of the email"
                        },
                        "text": {
                            "bsonType": "string",
                            "description": "Plain text content of the email"
                        }
                    },
                    "description": "Email content in both HTML and plain text formats"
                },
                "metadata": {
                    "bsonType": "object",
                    "description": "Additional metadata about the email",
                    "properties": {
                        "source": {
                            "bsonType": "string",
                            "enum": ["POSTMARK", "CMS", "VEYRA"],
                            "description": "Source system of the email"
                        },
                        "template_name": {
                            "bsonType": "string",
                            "description": "Template name or ID if applicable"
                        },
                        "tags": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "string"
                            },
                            "description": "Tags associated with the email"
                        },
                        "summary": {
                            "bsonType": "string",
                            "description": "AI-generated summary of the email content"
                        }
                    }
                },
                "created_at": {
                    "bsonType": "int",
                    "description": "Unix timestamp when the email was first stored"
                },
                "updated_at": {
                    "bsonType": "int",
                    "description": "Unix timestamp when the email was last updated"
                }
            }
        }
    }
}

# Index configurations for emails collection
EMAILS_INDEXES = [
    {
        "keys": [("email_id", 1)],
        "name": "email_id_idx",
        "unique": True
    },
    {
        "keys": [("thread_id", 1)],
        "name": "thread_id_idx"
    },
    {
        "keys": [("date", -1)],
        "name": "date_idx"
    },
    {
        "keys": [("from_email.email", 1)],
        "name": "from_email_idx"
    },
    {
        "keys": [("metadata.tags", 1)],
        "name": "tags_idx"
    },
    {
        "keys": [("created_at", -1)],
        "name": "created_at_idx"
    }
]

# Index configurations
CONVERSATIONS_INDEXES = [
    {
        "keys": [("thread_id", 1)],
        "name": "thread_id_idx"
    },
    {
        "keys": [("message_id", 1)],
        "name": "message_id_idx"
    },
    {
        "keys": [("timestamp", -1)],
        "name": "timestamp_idx"
    },
    {
        "keys": [("insight_id", 1)],
        "name": "insight_id_idx"
    },
    {
        "keys": [("metadata.source", 1)],
        "name": "source_idx"
    }
]

INSIGHTS_INDEXES = [
    {
        "keys": [("insight_id", 1)],
        "name": "insight_id_idx"
    },
    {
        "keys": [("timestamp", -1)],
        "name": "timestamp_idx"
    },
    {
        "keys": [("source", 1)],
        "name": "source_idx"
    },
    {
        "keys": [("vector_id", 1)],
        "name": "vector_id_idx"
    },
    {
        "keys": [("tags", 1)],
        "name": "tags_idx"
    }
] 