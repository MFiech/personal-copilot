#!/usr/bin/env python3
"""
Script to setup and migrate all PM Co-Pilot prompts to Langfuse
This script creates versioned prompt templates in Langfuse for centralized management
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add the parent directory to the path so we can import from the backend
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
load_dotenv(backend_path / '.env')

from services.langfuse_service import get_langfuse_service

def create_pm_copilot_prompts():
    """Create all PM Co-Pilot prompts in Langfuse"""
    
    langfuse_service = get_langfuse_service()
    
    if not langfuse_service.is_enabled():
        print("❌ Langfuse service is not enabled. Please check your configuration.")
        return False
    
    print("🚀 Setting up PM Co-Pilot prompts in Langfuse...")
    print("=" * 60)
    
    # 1. Master Intent Router Prompt
    print("\n1. Creating Master Intent Router prompt...")
    intent_router_prompt = """You are an expert task router for a personal assistant application.
Analyze the user's query and recent conversation history.
Identify the primary intent from the following list:
- general_knowledge_qa: For general questions, facts, or conversation.
- search_emails: When the user wants to find emails. Extract keywords, sender, date_range if mentioned.
- search_calendar_events: When the user wants to find calendar events. Extract keywords, date, time if mentioned.
- initiate_send_email: When the user expresses a desire to send an email. Extract recipient, subject, or body hints.
- initiate_create_event: When the user wants to create a calendar event. Extract title, date, time, or attendee hints.
- create_draft: When the user wants to create a draft (email or calendar event). Extract draft_type, recipient/attendees, subject/title, body/description.

User Query: "{{user_query}}"
Conversation History (last 3 turns):
{{conversation_history}}

IMPORTANT: You must respond with a valid, properly escaped JSON object containing only two fields: "intent" and "parameters".
- The "intent" field must be exactly one of the intent types listed above.
- The "parameters" field must be an object containing any extracted parameters relevant to the intent.
- If no parameters are identified, use an empty object: {{}}.
- Do not include any explanation, introduction, or additional text outside of the JSON object.

Examples of valid responses:
{{"intent": "search_emails", "parameters": {{"keywords": "report", "sender": "john@example.com"}}}}
{{"intent": "general_knowledge_qa", "parameters": {{}}}}
{{"intent": "search_calendar_events", "parameters": {{"date": "tomorrow"}}}}

YOUR RESPONSE (JSON only):"""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-intent-router",
        prompt_content=intent_router_prompt,
        labels=["production", "intent", "classification"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 2. Gmail Query Builder Prompt
    print("\n2. Creating Gmail Query Builder prompt...")
    gmail_query_prompt = """You are an expert Gmail search query builder. Your task is to convert natural language email requests into precise Gmail search queries using Gmail's advanced search operators.

CURRENT DATE: {{current_date}} (use for relative date calculations)

AVAILABLE GMAIL SEARCH OPERATORS:
- from:email@domain.com (sender)
- to:email@domain.com (recipient) 
- subject:"exact phrase" or subject:keyword
- label:labelname (e.g., label:important, label:work)
- has:attachment (emails with attachments)
- is:unread, is:read, is:starred, is:important
- after:YYYY/MM/DD, before:YYYY/MM/DD (date ranges)
- newer_than:Nd, older_than:Nd (N days, e.g., newer_than:7d)
- size:larger:10M, size:smaller:1M (file sizes)
- AND, OR, NOT (logical operators)
- "exact phrase" (exact phrase matching)
- filename:type (e.g., filename:pdf, filename:doc)

CONVERSATION CONTEXT:
{{conversation_history}}

USER REQUEST: "{{user_query}}"

INSTRUCTIONS:
1. Analyze the user's request to identify email search criteria
2. Map natural language to appropriate Gmail operators
3. Handle relative dates (today, yesterday, last week, etc.) by converting to YYYY/MM/DD format
4. Use quotes for exact phrases and multi-word subjects
5. Combine operators with AND/OR as needed
6. **IMPORTANT: For queries about "recent emails", "latest emails", "last email", or general email requests without specific criteria, return empty string to show all recent emails**
7. Only add date filters when user explicitly mentions specific timeframes
8. Only add read/unread filters when user explicitly mentions email status
9. Be conservative - only add operators you're confident about from the user's request

EXAMPLES:
- "show me emails from john about the meeting" → from:john subject:meeting
- "unread emails from last week" → is:unread after:{{last_week_date}}
- "emails with attachments from sarah" → from:sarah has:attachment
- "important emails about project alpha" → is:important subject:"project alpha"
- "emails from gmail.com domain yesterday" → from:gmail.com after:{{yesterday_date}} before:{{today_date}}
- "show my emails" → (empty string)
- "what's the last email I received?" → (empty string)
- "latest emails" → (empty string)
- "recent emails" → (empty string)
- "and what's the last e-mail I received?" → (empty string)

RESPONSE FORMAT:
Return ONLY the Gmail search query string. Do not include explanations, quotes around the entire response, or additional text.
If no specific search criteria can be identified, return an empty string.

GMAIL QUERY:"""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-gmail-query-builder",
        prompt_content=gmail_query_prompt,
        labels=["production", "gmail", "query"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 3. Draft Detection Prompt
    print("\n3. Creating Draft Detection prompt...")
    draft_detection_prompt = """You are an expert at detecting draft creation intent and extracting information from natural language.

{{existing_draft_context}}

**🚨 ABSOLUTELY CRITICAL: DO NOT AUTO-GENERATE TIMES EVER! 🚨**

If the user says "Saturday" ONLY, you MUST extract NO start_time and NO end_time.
If the user says "tomorrow" ONLY, you MUST extract NO start_time and NO end_time.
If the user says "next week" ONLY, you MUST extract NO start_time and NO end_time.

ONLY extract time fields if the user specifies ACTUAL CLOCK TIMES like:
- "Saturday at 2pm" → extract start_time: "2025-07-05T14:00:00"
- "2pm to 4pm Saturday" → extract start_time and end_time
- "Saturday 3:30pm" → extract start_time only

**FORBIDDEN EXAMPLES - NEVER DO THIS:**
- User: "Saturday" → ❌ WRONG: start_time: "2025-07-05T00:00:00"
- User: "tomorrow" → ❌ WRONG: Any time extraction
- User: "next week" → ❌ WRONG: Any time extraction

CURRENT DATE: {{current_date}}

CONVERSATION CONTEXT:
{{conversation_history}}

USER QUERY: "{{user_query}}"

TASK: Analyze if the user wants to create a draft (email or calendar event) and extract relevant information.

DRAFT DETECTION CRITERIA:
- User explicitly mentions "draft" in relation to email or calendar/meeting
- User wants to prepare/compose an email or event for later confirmation
- User wants to create something but not send/schedule it immediately

EXTRACTION RULES:
1. DRAFT TYPE: Determine if it's "email" or "calendar_event"
2. RECIPIENTS/ATTENDEES: Extract names, email addresses, or contact references
   - If user provides email like "It's john@example.com" or "His email is john@example.com", extract it
   - Format as "Name (email@domain.com)" when both name and email are known
3. SUBJECT/TITLE: Extract email subject or event title
4. BODY/DESCRIPTION: Extract email body content or event description
5. DATE/TIME: ONLY extract if user specifies actual clock times (like "2pm", "14:00", "9:30am")
6. LOCATION: For calendar events, extract location if mentioned

**EMAIL ADDRESS EXTRACTION:**
- If user says "It's john@example.com" → extract attendee: "john@example.com"
- If user says "His email is john@example.com" → extract attendee: "john@example.com"  
- If user says "Add john@example.com" → extract attendee: "john@example.com"

**🚨 TIME EXTRACTION RULES - FOLLOW EXACTLY OR FAIL:**
- "Saturday" → MUST extract NO start_time, NO end_time (null/empty)
- "Saturday at 3pm" → extract start_time only: "2025-07-05T15:00:00"
- "Saturday 3pm to 5pm" → extract both start_time and end_time
- "tomorrow morning" → MUST extract NO times (null/empty)
- "next Tuesday" → MUST extract NO times (null/empty)
- "on Monday" → MUST extract NO times (null/empty)
- "this weekend" → MUST extract NO times (null/empty)

**IF NO CLOCK TIME IS MENTIONED, DO NOT EXTRACT TIME FIELDS AT ALL!**

MANDATORY EXTRACTION GUIDELINES:
- ONLY extract information that is EXPLICITLY stated by the user
- DO NOT auto-generate or assume missing information (especially times/dates)
- If a field is not clearly specified, DO NOT INCLUDE IT in the JSON response
- For partial time info, include ONLY what's specified, don't fill in missing parts
- When in doubt, COMPLETELY OMIT the field rather than guessing

**🚨 CRITICAL: If user says "Saturday" without a time, DO NOT include start_time or end_time fields AT ALL in the JSON response!**

IMPORTANT NOTES:
- Only detect draft intent when user explicitly mentions "draft" or wants to "prepare" something
- DO NOT detect draft intent for search/view requests ("show me", "pull all", "find events")
- Extract partial information - it's okay if some fields are missing
- Normalize dates to YYYY-MM-DD format and times to HH:MM:SS format
- For contacts, extract both names and email addresses if provided
- Be conservative - only extract what you're confident about

RESPONSE FORMAT:
Respond with a JSON object containing:
{{"is_draft_intent": boolean, "draft_data": object or null}}

If is_draft_intent is true, include draft_data with:
{{
  "draft_type": "email" or "calendar_event",
  "extracted_info": {{
    // For email drafts:
    "to_contacts": ["name1", "email1@domain.com"],
    "subject": "extracted subject",
    "body": "extracted body content",
    
    // For calendar event drafts:
    "summary": "event title",
    "start_time": "YYYY-MM-DDTHH:MM:SS",
    "end_time": "YYYY-MM-DDTHH:MM:SS", 
    "attendees": ["name1", "email1@domain.com"],
    "location": "extracted location",
    "description": "event description"
  }}
}}

EXAMPLES:
User: "Create a draft email to John about the meeting"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "email", "extracted_info": {{"to_contacts": ["John"], "subject": "", "body": "about the meeting"}}}}}}

User: "Draft a meeting with Sarah tomorrow at 2pm"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "calendar_event", "extracted_info": {{"summary": "meeting with Sarah", "attendees": ["Sarah"], "start_time": "2024-12-21T14:00:00"}}}}}}

User: "Create a draft for a meeting with Bob on Saturday"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "calendar_event", "extracted_info": {{"summary": "meeting with Bob", "attendees": ["Bob"]}}}}}}

User: "Thanks. Let's send the invitation to Paweł's email. It's stawskipawel@gmail.com"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "calendar_event", "extracted_info": {{"attendees": ["Paweł Stawski (stawskipawel@gmail.com)"]}}}}}}

User: "What's the weather like?"
Response: {{"is_draft_intent": false, "draft_data": null}}

User: "pull all events for current week"
Response: {{"is_draft_intent": false, "draft_data": null}}

User: "show me my calendar"
Response: {{"is_draft_intent": false, "draft_data": null}}

YOUR RESPONSE (JSON only):"""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-draft-detection",
        prompt_content=draft_detection_prompt,
        labels=["production", "draft", "detection"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 4. Email Summarization Prompt
    print("\n4. Creating Email Summarization prompt...")
    email_summarization_prompt = """You are an expert at summarizing email{{email_type_text}}.

Email{{email_type_text}} Content{{email_count_text}}:
---
{{email_body}}
---

{{summarization_instructions}}

Output only the summary without any introductory text or explanations. {{focus_instructions}}"""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-email-summarization",
        prompt_content=email_summarization_prompt,
        labels=["production", "email", "summarization"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 5. General QA Prompt
    print("\n5. Creating General QA prompt...")
    general_qa_prompt = """Current date and time: {{current_time}}

{{thread_history}}

{{retrieved_context}}

User Query: {{query}}

You are a helpful AI assistant. Respond to the user's query based on the retrieved context 
and your general knowledge. Be conversational and helpful. If the retrieved context is relevant,
synthesize it into your answer. Otherwise, use your general knowledge."""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-general-qa",
        prompt_content=general_qa_prompt,
        labels=["production", "qa", "general"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 6. Query Classification Prompt
    print("\n6. Creating Query Classification prompt...")
    query_classification_prompt = """You are an expert query classifier for a personal assistant that can access emails, calendar events, and contacts.

CONVERSATION CONTEXT (recent messages):
{{conversation_context}}

USER QUERY: "{{user_query}}"

CRITICAL DISAMBIGUATION RULES:
1. Questions about what exists/is planned = searching/viewing (not creating)
2. Commands to add/create/schedule = creating new items
3. "What do I have..." or "Do I have..." = always searching existing items
4. Past participles about existing items ("planned", "scheduled", "received") = searching
5. Consider the full query structure, not just individual keywords

FEW-SHOT EXAMPLES:

Example 1:
Query: "What emails do I have from Sarah?"
Intent: "email"
Reasoning: Searching for existing email messages from a specific sender

Example 2:
Query: "What do I have planned this week?"
Intent: "calendar"
Reasoning: Question about existing calendar events ("what do I have" + "planned")

Example 3:
Query: "Show me unread emails from today"
Intent: "email"
Reasoning: Request to view existing emails with specific filters

Example 4:
Query: "Do I have any meetings scheduled with John?"
Intent: "calendar"
Reasoning: Question about existing calendar events with specific attendee

Example 5:
Query: "What's Sarah's email address?"
Intent: "contact"
Reasoning: Requesting contact information (email address) for a person

Example 6:
Query: "Schedule a meeting with the team tomorrow at 3pm"
Intent: "calendar"
Reasoning: Command to create new calendar event (imperative "schedule")

Example 7:
Query: "Find emails about the project proposal"
Intent: "email"
Reasoning: Search request for emails with specific content

Example 8:
Query: "What meetings are planned for this afternoon?"
Intent: "calendar"
Reasoning: Question about existing events in specific time range

Example 9:
Query: "Show me emails I received yesterday"
Intent: "email"
Reasoning: Request to view emails from specific time period

Example 10:
Query: "What's on my calendar for next Monday?"
Intent: "calendar"
Reasoning: Question about existing events on specific date

CLASSIFICATION CATEGORIES:

1. "email" - User wants to find, search, view, or work with email messages
   - Strong indicators: "emails from", "messages", "inbox", "unread", "received", "sent"
   - Actions: searching, filtering, reading email content
   - NOT: asking for someone's email address (that's "contact")

2. "calendar" - User wants to find, view, create, or work with calendar events
   - Strong indicators: "calendar", "meeting", "event", "schedule", "appointment"
   - Search indicators: "what's planned", "what do I have", "scheduled", "upcoming"
   - Create indicators: imperative verbs like "schedule", "add", "create", "book"

3. "contact" - User wants contact information or details about people
   - Strong indicators: "email address", "phone number", "contact info", "email of [person]"
   - Actions: finding email addresses, phone numbers, or other contact details
   - NOT: searching for emails from someone (that's "email")

4. "general" - General questions or requests not related to email/calendar/contacts
   - Examples: weather, definitions, calculations, general knowledge

CONTEXT INHERITANCE RULES:
- Vague follow-ups ("and tomorrow?", "what about next week?") inherit previous intent
- Time references without service specification check recent context
- "Show me more" or "anything else?" maintains previous intent
- Pronouns ("those", "them", "it") refer to previously discussed items

RESPONSE FORMAT (JSON only):
{{
  "intent": "email" | "calendar" | "contact" | "general",
  "confidence": 0.00-1.00,
  "reasoning": "Brief explanation based on indicators and context",
  "parameters": {{
    "keywords": ["relevant", "search", "terms"],
    "time_reference": "today|tomorrow|this week|next week|etc",
    "person_name": "extracted person name if mentioned"
  }}
}}

Respond with ONLY the JSON object."""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-query-classification",
        prompt_content=query_classification_prompt,
        labels=["production", "classification", "intent"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    # 7. Calendar Intent Analysis Prompt
    print("\n7. Creating Calendar Intent Analysis prompt...")
    calendar_intent_prompt = """You are an expert calendar assistant. Analyze the user's query to determine if they want to CREATE a new calendar event or SEARCH/VIEW existing events.

CURRENT CONTEXT:
- Current date: {{current_date}} ({{current_weekday}})
- Current time: {{current_time}}

CONVERSATION CONTEXT:
{{conversation_context}}

USER QUERY: "{{user_query}}"

CRITICAL CLASSIFICATION RULES:
1. Questions about existing events are ALWAYS "search" operations
2. Past participles like "planned", "scheduled", "booked" referring to existing items indicate "search"
3. Future actions like "plan a meeting", "schedule for tomorrow" indicate "create"
4. Queries starting with interrogatives (what, when, where, who, which) typically indicate "search"
5. Commands or imperatives typically indicate "create"

FEW-SHOT EXAMPLES:

Example 1:
Query: "What do I have planned this week?"
Analysis: Question about existing events ("what do I have" + past participle "planned")
Operation: "search"
Parameters: {{"date_range": "this week"}}

Example 2:
Query: "Show me tomorrow's schedule"
Analysis: Request to view existing events ("show me")
Operation: "search"
Parameters: {{"date_range": "tomorrow"}}

Example 3:
Query: "Schedule a meeting with John for Friday at 2pm"
Analysis: Command to create new event ("schedule" as imperative verb)
Operation: "create"
Parameters: {{"title": "Meeting with John", "date": "2024-01-26", "start_time": "14:00", "end_time": "15:00"}}

Example 4:
Query: "What's on my calendar today?"
Analysis: Question about existing events ("what's on")
Operation: "search"
Parameters: {{"date_range": "today"}}

Example 5:
Query: "I need to plan a team standup for tomorrow at 10am"
Analysis: Statement expressing need to create new event ("need to plan" + future time)
Operation: "create"
Parameters: {{"title": "Team standup", "date": "{{tomorrow_date}}", "start_time": "10:00", "end_time": "10:30"}}

Example 6:
Query: "Do I have any meetings scheduled this afternoon?"
Analysis: Question about existing events ("Do I have" + "scheduled" referring to existing)
Operation: "search"
Parameters: {{"date_range": "today", "time_range": "afternoon", "keywords": "meetings"}}

Example 7:
Query: "Add dentist appointment next Monday at 3:30pm"
Analysis: Command to create new event ("add" imperative)
Operation: "create"
Parameters: {{"title": "Dentist appointment", "date": "2024-01-29", "start_time": "15:30", "end_time": "16:30"}}

Example 8:
Query: "What meetings do I have planned with Sarah?"
Analysis: Question about existing events with specific person
Operation: "search"
Parameters: {{"keywords": "Sarah", "date_range": "this week"}}

OPERATIONS:
1. "create" - User wants to create/schedule/add a new calendar event
   - Strong indicators: imperative verbs (schedule, add, create, book, set up, make, put)
   - Context: "I need to...", "Please...", "Can you...", "Let's..."
   - Extract: title, date, time, location, description, attendees

2. "search" - User wants to find/view/check existing calendar events
   - Strong indicators: question words (what, when, where, who, which, do I have)
   - Phrases: "what's planned", "what do I have", "show me", "list", "view", "check", "find"
   - Past participles referring to existing: "scheduled", "planned", "booked"
   - Extract: date_range, keywords, attendee_filter

PARAMETER EXTRACTION RULES:
For CREATE operations:
- title: Event title/summary (required) - extract the main subject
- date: Event date in YYYY-MM-DD format (required)
- start_time: Start time in HH:MM format (required)
- end_time: End time in HH:MM format (optional, default +1 hour)
- location: Event location (optional)
- description: Event description (optional)
- attendees: List of email addresses or names (optional)

For SEARCH operations:
- date_range: today/tomorrow/this week/next week/this month/specific date
- keywords: Search terms from the query (event names, people, topics)
- time_range: morning/afternoon/evening/night
- attendee_filter: Names or emails of specific attendees to filter by

DATE/TIME PARSING:
- "Friday" = next Friday if today is not Friday, today if today is Friday
- "tomorrow" = {{tomorrow_date}}
- "today" = {{current_date}}
- "this week" = current calendar week
- "next week" = following calendar week
- "5pm" = "17:00", "5:30pm" = "17:30"
- "noon" = "12:00", "midnight" = "00:00"
- Morning = 06:00-12:00, Afternoon = 12:00-18:00, Evening = 18:00-23:00
- If no time specified for create, use "09:00" as default

RESPONSE FORMAT (JSON only):
{{
  "operation": "create" | "search",
  "confidence": 0.00-1.00,
  "reasoning": "Brief explanation of classification",
  "parameters": {{
    // Include relevant parameters based on operation
  }}
}}

Respond with ONLY the JSON object."""
    
    success = langfuse_service.create_prompt(
        name="pm-copilot-calendar-intent-analysis",
        prompt_content=calendar_intent_prompt,
        labels=["production", "calendar", "intent"],
        prompt_type="text"
    )
    
    if not success:
        return False
    
    print(f"\n🎉 Successfully created 7 prompts in Langfuse!")
    print(f"📊 View them at: {os.getenv('LANGFUSE_HOST', 'http://localhost:4000')}/prompts")
    return True

def test_prompt_retrieval():
    """Test retrieving and compiling prompts"""
    
    print(f"\n🔍 Testing prompt retrieval and compilation...")
    
    langfuse_service = get_langfuse_service()
    
    if not langfuse_service.is_enabled():
        print("❌ Langfuse service not enabled for testing")
        return False
    
    try:
        # Test retrieving intent router prompt
        intent_prompt = langfuse_service.get_prompt("pm-copilot-intent-router")
        if intent_prompt:
            print("✅ Retrieved intent router prompt")
        else:
            print("❌ Failed to retrieve intent router prompt")
            return False
        
        # Test retrieving gmail query builder prompt
        gmail_prompt = langfuse_service.get_prompt("pm-copilot-gmail-query-builder")
        if gmail_prompt:
            print("✅ Retrieved gmail query builder prompt")
        else:
            print("❌ Failed to retrieve gmail query builder prompt")
            return False
        
        # Test retrieving draft detection prompt
        draft_prompt = langfuse_service.get_prompt("pm-copilot-draft-detection")
        if draft_prompt:
            print("✅ Retrieved draft detection prompt")
        else:
            print("❌ Failed to retrieve draft detection prompt")
            return False
        
        print("✅ All prompt retrieval tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test prompts: {e}")
        return False

def main():
    """Main function to setup PM Co-Pilot prompts"""
    print("🎯 PM Co-Pilot Prompt Management Setup")
    print("=" * 50)
    
    # Check environment variables
    required_vars = ['LANGFUSE_SECRET_KEY', 'LANGFUSE_PUBLIC_KEY', 'LANGFUSE_HOST']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these in your backend/.env file")
        return False
    
    print("✅ Environment variables found")
    
    # Create prompts
    creation_success = create_pm_copilot_prompts()
    if not creation_success:
        print("❌ Failed to create prompts")
        return False
    
    # Test retrieval  
    test_success = test_prompt_retrieval()
    if not test_success:
        print("❌ Failed prompt retrieval tests")
        return False
    
    print(f"\n🎊 Prompt Management Setup Complete!")
    print(f"📋 Next steps:")
    print(f"1. Visit {os.getenv('LANGFUSE_HOST', 'http://localhost:4000')}/prompts to see your prompts")
    print(f"2. Try editing a prompt version in the Langfuse UI")
    print(f"3. Run your PM Co-Pilot application to see prompts in action")
    print(f"4. Check the 'Generations' tab to see prompt usage")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
