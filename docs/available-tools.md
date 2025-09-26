# Available Tools and Methods

## **Composio Email Tools**
- **search_emails** - Find emails by query. Searches through Gmail using natural language queries, keywords, sender filters, date ranges, and other criteria to retrieve relevant email messages.

- **send_email** - Send new email. Composes and sends a new email message to specified recipients with subject, body, CC/BCC options, and attachments support.

- **reply_to_thread** - Reply to email thread. Responds to an existing email conversation by sending a reply message that maintains the thread context and includes original recipients.

- **delete_email** - Delete email. Permanently removes an email message from Gmail, moving it to trash and optionally purging it completely.

- **get_email_details** - Get full email content. Retrieves complete email information including headers, body content, attachments, and metadata for a specific email ID.

## **Composio Calendar Tools**
- **search_calendar_events** - Find calendar events. Searches through Google Calendar to find events matching criteria like date ranges, keywords, attendees, or event titles.

- **create_calendar_event** - Create new event. Creates a new calendar event with specified title, date/time, location, description, attendees, and other event details.

- **update_calendar_event** - Update event (PUT method). Completely replaces an existing calendar event with new information, requiring all event fields to be provided again.

- **patch_calendar_event** - Patch event (PATCH method). Partially updates specific fields of an existing calendar event without affecting other event properties, more efficient for small changes.

- **delete_calendar_event** - Delete event. Removes a calendar event permanently from Google Calendar, notifying attendees if configured to do so.

## **Composio Contact Tools**
- **search_contacts** - Find contacts by name/email. Searches through Google Contacts to find people by name, email address, or other contact information fields.

## **Draft Tools**
- **create_draft** - Create email/calendar draft. Creates a draft for user review before execution, allowing them to modify and approve email or calendar event details.

- **update_draft** - Update existing draft. Modifies fields in an active draft based on user feedback, maintaining the draft state until user decides to send.

- **send_draft** - Execute draft (calls appropriate Composio tool). Converts an approved draft into actual action by calling the corresponding Composio method (send_email, create_calendar_event, etc.).

- **validate_draft** - Check draft completeness. Verifies that all required fields are present in a draft and identifies missing information needed before execution.

## **LLM Functions**
- **Query classification** (email/calendar/contact/general) - Analyzes user queries to determine the primary intent and route to appropriate tool categories. Uses conversation context and keywords to classify requests into email, calendar, contact, or general conversation types.

- **Calendar intent analysis** (create vs search) - Distinguishes between requests to create new calendar events versus searching for existing events. Analyzes language patterns and verbs to determine if user wants to add something new or find existing items.

- **Gmail query building** - Converts natural language email search requests into proper Gmail search syntax. Translates user queries like "emails from John last week" into Gmail query format with appropriate operators.

- **Draft creation intent detection** - Identifies when user wants to create a draft for review versus immediate execution. Recognizes language patterns indicating user preference for reviewing content before sending or scheduling.

- **Draft update intent detection** - Determines when user wants to modify an existing draft versus creating something new. Analyzes context and anchored items to route requests to draft update functionality.

- **General conversation/summarization** - Handles non-tool queries through natural conversation and provides summaries of information. Responds to general questions, clarifications, and conversational interactions outside of specific tool usage.

## **Utility Tools**
- **Vector search** (retrieve documents) - Searches through stored documents and knowledge base using semantic similarity. Retrieves relevant information from previous conversations, saved documents, or knowledge repositories.

- **Conversation memory** - Maintains context and history of ongoing conversations across multiple turns. Stores and retrieves conversation state to provide coherent responses and maintain context awareness.

- **Thread management** - Organizes conversations into threads and manages conversation flow and context. Creates, updates, and retrieves conversation threads to maintain organized communication history.

- **Bulk operations** (delete multiple items) - Performs batch operations on multiple emails or calendar events simultaneously. Allows users to delete, modify, or organize multiple items in a single action for efficiency.