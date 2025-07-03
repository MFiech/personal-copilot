"""
This module contains all the prompt templates used in the application.
Each prompt has a specific purpose and is optimized for a particular task.
"""
from datetime import datetime, timedelta

def master_intent_router_prompt(user_query, conversation_history=None):
    """
    Prompt for identifying the user's intent from their query.
    Returns a JSON object with the identified intent and extracted parameters.
    
    Intents:
    - general_knowledge_qa: For general questions or conversation
    - search_emails: When the user wants to find emails
    - search_calendar_events: When the user wants to find calendar events
    - initiate_send_email: When the user wants to send an email
    - initiate_create_event: When the user wants to create a calendar event
    - create_draft: When the user wants to create a draft (email or calendar event)
    """
    history_text = ""
    if conversation_history:
        # Format the conversation history
        for msg in conversation_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_text += f"{role.capitalize()}: {content}\n"
    
    return f"""
You are an expert task router for a personal assistant application.
Analyze the user's query and recent conversation history.
Identify the primary intent from the following list:
- general_knowledge_qa: For general questions, facts, or conversation.
- search_emails: When the user wants to find emails. Extract keywords, sender, date_range if mentioned.
- search_calendar_events: When the user wants to find calendar events. Extract keywords, date, time if mentioned.
- initiate_send_email: When the user expresses a desire to send an email. Extract recipient, subject, or body hints.
- initiate_create_event: When the user wants to create a calendar event. Extract title, date, time, or attendee hints.
- create_draft: When the user wants to create a draft (email or calendar event). Extract draft_type, recipient/attendees, subject/title, body/description.

User Query: "{user_query}"
Conversation History (last 3 turns):
{history_text}

IMPORTANT: You must respond with a valid, properly escaped JSON object containing only two fields: "intent" and "parameters".
- The "intent" field must be exactly one of the intent types listed above.
- The "parameters" field must be an object containing any extracted parameters relevant to the intent.
- If no parameters are identified, use an empty object: {{}}.
- Do not include any explanation, introduction, or additional text outside of the JSON object.

Examples of valid responses:
{{"intent": "search_emails", "parameters": {{"keywords": "report", "sender": "john@example.com"}}}}
{{"intent": "general_knowledge_qa", "parameters": {{}}}}
{{"intent": "search_calendar_events", "parameters": {{"date": "tomorrow"}}}}

YOUR RESPONSE (JSON only):
"""

def email_results_intro_prompt(emails_found=True):
    """
    Simple prompt to generate the standardized text before displaying email tiles.
    This could be replaced with hardcoded strings.
    """
    if emails_found:
        return "Here are the recent emails based on your query:"
    else:
        return "I couldn't find any emails matching your query."

def calendar_results_intro_prompt(events_found=True):
    """
    Simple prompt to generate the standardized text before displaying calendar event tiles.
    This could be replaced with hardcoded strings.
    """
    if events_found:
        return "Here are your calendar events:"
    else:
        return "I couldn't find any calendar events matching your query."

def general_qa_prompt(query, thread_history=None, retrieved_docs=None):
    """
    Prompt for general question answering with RAG.
    """
    prompt_parts = []
    
    # Add current date and time
    current_time = datetime.now()
    prompt_parts.append(f"Current date and time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    prompt_parts.append("\n")
    
    # Add thread history to the prompt if available
    if thread_history:
        history_text = ""
        for msg in thread_history:
            if isinstance(msg, dict):
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                history_text += f"{role.capitalize()}: {content}\n"
        prompt_parts.append("Conversation History:")
        prompt_parts.append(history_text)
        prompt_parts.append("\n")
    
    # Add retrieved context to the prompt
    if retrieved_docs:
        prompt_parts.append("Retrieved Context:")
        for i, doc in enumerate(retrieved_docs, 1):
            metadata = getattr(doc, 'metadata', {}) or {}
            source = metadata.get("source", "Unknown")
            insight_id = metadata.get("insight_id", "Unknown")
            full_text = getattr(doc, 'page_content', '').strip()
            prompt_parts.append(f"{i}. Source: {source}, Insight ID: {insight_id}\nText: {full_text}\n")
    else:
        prompt_parts.append("No relevant context retrieved from the database.")
    
    # Add the user query
    prompt_parts.append(f"\nUser Query: {query}")
    
    # Add instructions
    prompt_parts.append("""
You are a helpful AI assistant. Respond to the user's query based on the retrieved context 
and your general knowledge. Be conversational and helpful. If the retrieved context is relevant,
synthesize it into your answer. Otherwise, use your general knowledge.
""")
    
    return "\n\n".join(prompt_parts)

def email_summarization_prompt(email_body):
    """
    Prompt for summarizing an email.
    """
    return f"""
You are an expert at summarizing email content.

Email Content:
---
{email_body}
---

Provide a concise summary (2-4 sentences) of the above email. Highlight the main topic, key information, and any explicit action items mentioned.
Output only the summary without any introductory text or explanations. Focus solely on the text, not HTML. At most, you can HTML to undderstand better the email structure/heading.
"""

def gmail_query_builder_prompt(user_query, conversation_history=None):
    """
    Prompt for building Gmail search queries from natural language user requests.
    This prompt instructs the LLM to parse user intent and construct proper Gmail search queries
    using Gmail's advanced search operators.
    """
    history_context = ""
    if conversation_history:
        # Include recent conversation for context
        recent_messages = conversation_history[-6:]  # Last 3 exchanges
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:200]  # Truncate for brevity
            history_context += f"{role.capitalize()}: {content}\n"
    
    current_date = datetime.now()
    yesterday_date = (current_date - timedelta(days=1)).strftime('%Y/%m/%d')
    today_date = current_date.strftime('%Y/%m/%d')
    last_week_date = (current_date - timedelta(days=7)).strftime('%Y/%m/%d')
    
    return f"""You are an expert Gmail search query builder. Your task is to convert natural language email requests into precise Gmail search queries using Gmail's advanced search operators.

CURRENT DATE: {current_date.strftime('%Y-%m-%d')} (use for relative date calculations)

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
{history_context}

USER REQUEST: "{user_query}"

INSTRUCTIONS:
1. Analyze the user's request to identify email search criteria
2. Map natural language to appropriate Gmail operators
3. Handle relative dates (today, yesterday, last week, etc.) by converting to YYYY/MM/DD format
4. Use quotes for exact phrases and multi-word subjects
5. Combine operators with AND/OR as needed
6. If no specific criteria mentioned, return empty string for general recent emails
7. Be conservative - only add operators you're confident about from the user's request

EXAMPLES:
- "show me emails from john about the meeting" → from:john subject:meeting
- "unread emails from last week" → is:unread after:{last_week_date}
- "emails with attachments from sarah" → from:sarah has:attachment
- "important emails about project alpha" → is:important subject:"project alpha"
- "emails from gmail.com domain yesterday" → from:gmail.com after:{yesterday_date} before:{today_date}
- "show my emails" → (empty string)

RESPONSE FORMAT:
Return ONLY the Gmail search query string. Do not include explanations, quotes around the entire response, or additional text.
If no specific search criteria can be identified, return an empty string.

GMAIL QUERY:""" 

def draft_detection_prompt(user_query, conversation_history=None, existing_draft=None):
    """
    Prompt for detecting draft creation intent and extracting information.
    Returns structured data for creating drafts.
    """
    history_context = ""
    if conversation_history:
        # Include recent conversation for context
        recent_messages = conversation_history[-6:]  # Last 3 exchanges
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_context += f"{role.capitalize()}: {content}\n"
    
    current_date = datetime.now()
    
    # Context for existing draft updates
    existing_draft_context = ""
    if existing_draft:
        existing_draft_context = f"""
🚨 EXISTING DRAFT CONTEXT - READ CAREFULLY:
There is already an active {existing_draft.get('draft_type', 'unknown')} draft.
Draft Summary: {existing_draft.get('summary', 'No summary')}
Current Attendees: {existing_draft.get('attendees', [])}
Current Times: {existing_draft.get('start_time', 'Not set')} to {existing_draft.get('end_time', 'Not set')}

🚨 UPDATE MODE RULES:
- If user is asking to ADD/UPDATE only specific fields (like "add email", "change time", "update attendee"), ONLY extract those specific fields
- If user says "add email address" or "his email is X", ONLY extract the attendee/email information
- DO NOT re-extract existing information unless explicitly asked to change it
- DO NOT include start_time, end_time, summary unless user specifically mentions changing them
- Focus ONLY on what the user is actually asking to modify

EXAMPLE UPDATE SCENARIOS:
- "Add John's email: john@email.com" → ONLY extract attendees: ["John (john@email.com)"]
- "Change time to 3pm" → ONLY extract start_time: "2025-07-05T15:00:00"  
- "Update the title to X" → ONLY extract summary: "X"
"""
    
    return f"""You are an expert at detecting draft creation intent and extracting information from natural language.

{existing_draft_context}

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

CURRENT DATE: {current_date.strftime('%Y-%m-%d %H:%M:%S')}

CONVERSATION CONTEXT:
{history_context}

USER QUERY: "{user_query}"

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

YOUR RESPONSE (JSON only):"""

def draft_information_extraction_prompt(user_query, existing_draft, conversation_history=None):
    """
    Prompt for extracting additional information to update an existing draft.
    """
    history_context = ""
    if conversation_history:
        recent_messages = conversation_history[-6:]
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_context += f"{role.capitalize()}: {content}\n"
    
    draft_type = existing_draft.get('draft_type', 'unknown')
    current_data = existing_draft.get('draft_data', {})
    
    return f"""You are an expert at extracting information to update existing drafts.

CONVERSATION CONTEXT:
{history_context}

EXISTING DRAFT:
Type: {draft_type}
Current Data: {current_data}

USER QUERY: "{user_query}"

TASK: Extract new information from the user's message to update the existing draft.

EXTRACTION RULES:
1. Only extract information that's explicitly mentioned or clearly implied
2. Don't overwrite existing data unless user specifically asks to change it
3. For email drafts: extract to_contacts, subject, body
4. For calendar events: extract summary, start_time, end_time, attendees, location, description
5. Normalize dates to YYYY-MM-DD format and times to HH:MM:SS format

RESPONSE FORMAT:
Return a JSON object with only the fields that should be updated:
{{
  "updates": {{
    // Only include fields that need updating
    "field_name": "new_value"
  }}
}}

EXAMPLES:
User: "Change the subject to 'Quarterly Review'"
Response: {{"updates": {{"subject": "Quarterly Review"}}}}

User: "Add Bob to the meeting"
Response: {{"updates": {{"attendees": ["existing_attendees", "Bob"]}}}}

User: "Set it for 3pm tomorrow"
Response: {{"updates": {{"start_time": "2024-12-21T15:00:00"}}}}

YOUR RESPONSE (JSON only):"""