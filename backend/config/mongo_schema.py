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
                                "bsonType": ["string", "object"],
                                "description": "Array of email IDs or email objects"
                            }
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
            "required": ["email_id", "thread_id", "subject", "from_email", "to_emails", "date"],
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
                    "required": ["email"],
                    "properties": {
                        "email": {
                            "bsonType": "string",
                            "description": "Sender's email address"
                        },
                        "name": {
                            "bsonType": ["string", "null"],
                            "description": "Sender's name"
                        }
                    }
                },
                "to_emails": {
                    "bsonType": "array",
                    "description": "List of email recipients",
                    "items": {
                        "bsonType": "object",
                        "required": ["email"],
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
                "cc": {
                    "bsonType": "array",
                    "description": "CC recipients",
                    "items": {
                        "bsonType": "object",
                        "required": ["email"],
                        "properties": {
                            "email": {
                                "bsonType": "string",
                                "description": "CC recipient's email address"
                            },
                            "name": {
                                "bsonType": ["string", "null"],
                                "description": "CC recipient's name"
                            }
                        }
                    }
                },
                "bcc": {
                    "bsonType": "array",
                    "description": "BCC recipients",
                    "items": {
                        "bsonType": "object",
                        "required": ["email"],
                        "properties": {
                            "email": {
                                "bsonType": "string",
                                "description": "BCC recipient's email address"
                            },
                            "name": {
                                "bsonType": ["string", "null"],
                                "description": "BCC recipient's name"
                            }
                        }
                    }
                },
                "reply_to": {
                    "bsonType": ["object", "null"],
                    "description": "Reply-to address",
                    "properties": {
                        "email": {
                            "bsonType": "string",
                            "description": "Reply-to email address"
                        },
                        "name": {
                            "bsonType": ["string", "null"],
                            "description": "Reply-to name"
                        }
                    }
                },
                "date": {
                    "bsonType": "string",
                    "description": "Email date"
                },
                "content": {
                    "bsonType": "object",
                    "description": "Email content",
                    "properties": {
                        "html": {
                            "bsonType": "string",
                            "description": "HTML content"
                        },
                        "text": {
                            "bsonType": "string",
                            "description": "Plain text content"
                        }
                    }
                },
                "metadata": {
                    "bsonType": "object",
                    "description": "Additional metadata",
                    "properties": {
                        "source": {
                            "bsonType": "string",
                            "description": "Email source"
                        },
                        "folder": {
                            "bsonType": "string",
                            "description": "Email folder"
                        },
                        "is_read": {
                            "bsonType": "bool",
                            "description": "Read status"
                        },
                        "size": {
                            "bsonType": ["int", "null"],
                            "description": "Email size"
                        }
                    }
                },
                "attachments": {
                    "bsonType": "array",
                    "description": "Email attachments",
                    "items": {
                        "bsonType": "object"
                    }
                },
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
        "keys": [("metadata.folder", 1)],
        "name": "folder_idx"
    },
    {
        "keys": [("metadata.is_read", 1)],
        "name": "is_read_idx"
    }
] 