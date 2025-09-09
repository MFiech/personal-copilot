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

def email_summarization_prompt(email_body, is_thread_email=False, thread_email_count=1):
    """
    Prompt for summarizing an email or email thread.
    """
    if is_thread_email and thread_email_count > 1:
        return f"""
You are an expert at summarizing email threads and conversations.

Email Thread Content ({thread_email_count} emails):
---
{email_body}
---

Provide a comprehensive summary (3-5 sentences) of this email thread. Include:
1. The main topic/subject being discussed
2. Key points from the conversation
3. Any decisions made or action items mentioned
4. The overall flow and conclusion of the discussion

Output only the summary without any introductory text or explanations. Focus on the conversation as a whole, not individual emails.
"""
    else:
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
6. **IMPORTANT: For queries about "recent emails", "latest emails", "last email", or general email requests without specific criteria, return empty string to show all recent emails**
7. Only add date filters when user explicitly mentions specific timeframes
8. Only add read/unread filters when user explicitly mentions email status
9. Be conservative - only add operators you're confident about from the user's request

EXAMPLES:
- "show me emails from john about the meeting" → from:john subject:meeting
- "unread emails from last week" → is:unread after:{last_week_date}
- "emails with attachments from sarah" → from:sarah has:attachment
- "important emails about project alpha" → is:important subject:"project alpha"
- "emails from gmail.com domain yesterday" → from:gmail.com after:{yesterday_date} before:{today_date}
- "show my emails" → (empty string)
- "what's the last email I received?" → (empty string)
- "latest emails" → (empty string)
- "recent emails" → (empty string)
- "and what's the last e-mail I received?" → (empty string)

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

# ===== NEW SEPARATED DRAFT PROMPTS =====

def draft_update_intent_prompt(user_query, existing_draft, conversation_history=None):
    """
    Prompt for detecting if user wants to update an anchored draft.
    This is the first step in the update flow.
    """
    history_context = ""
    if conversation_history:
        recent_messages = conversation_history[-6:]
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_context += f"{role.capitalize()}: {content}\n"
    
    draft_type = existing_draft.get('draft_type', 'unknown')
    current_date = datetime.now()
    
    # Build current draft summary
    draft_summary = f"Type: {draft_type}"
    if draft_type == 'email':
        draft_summary += f"\nRecipients: {existing_draft.get('to_emails', [])}"
        draft_summary += f"\nSubject: {existing_draft.get('subject') or '[NOT SET]'}"
        draft_summary += f"\nBody: {(existing_draft.get('body') or '[NOT SET]')[:100]}..."
    else:  # calendar_event
        draft_summary += f"\nTitle: {existing_draft.get('summary') or '[NOT SET]'}"
        draft_summary += f"\nTime: {existing_draft.get('start_time') or '[NOT SET]'} to {existing_draft.get('end_time') or '[NOT SET]'}"
        draft_summary += f"\nAttendees: {existing_draft.get('attendees', [])}"
        draft_summary += f"\nLocation: {existing_draft.get('location') or '[NOT SET]'}"
    
    return f"""You are an expert at detecting if a user wants to update an existing draft.

CURRENT DATE: {current_date.strftime('%Y-%m-%d %H:%M:%S')}

CONVERSATION CONTEXT:
{history_context}

ANCHORED DRAFT SUMMARY:
{draft_summary}

USER QUERY: "{user_query}"

TASK: Determine if the user's query is about updating the anchored draft.

UPDATE INTENT CRITERIA:
- User explicitly wants to modify/change/update something about the draft
- User wants to add/remove recipients/attendees
- User wants to change subject/title, body/description, time, location
- User asks to generate/create missing fields (like "create subject", "add body")
- User provides additional information for the draft (like email addresses, times)
- User indicates completion/finalization (like "that's all", "that's it", "looks good", "perfect")
- User confirms content should be applied to draft after LLM generated suggestions

NOT UPDATE INTENT:
- General questions about the draft ("what's in the draft?", "show me the draft")
- Questions unrelated to the draft ("what's the weather?", "find my emails")
- Requests to send/execute the draft (this should go to send workflow)
- Pure conversational acknowledgments without draft context

RESPONSE FORMAT:
Return JSON object with:
{{
  "is_update_intent": boolean,
  "update_category": "string or null",
  "confidence": "high|medium|low"
}}

UPDATE CATEGORIES:
- "subject_title": User wants to modify subject (email) or title (calendar)
- "body_description": User wants to modify body (email) or description (calendar)  
- "recipients_attendees": User wants to add/remove/modify recipients or attendees
- "time_schedule": User wants to modify start/end times (calendar only)
- "location": User wants to modify location (calendar only)
- "completion_finalization": User indicates draft is complete/ready ("that's all", "looks good", "perfect")
- "content_application": User wants to apply previously suggested content to the draft
- "general_content": User wants to modify multiple fields or general improvements

EXAMPLES:

User: "Create the subject on your own based on the context you have"
Response: {{"is_update_intent": true, "update_category": "subject_title", "confidence": "high"}}

User: "Add John to this email"
Response: {{"is_update_intent": true, "update_category": "recipients_attendees", "confidence": "high"}}

User: "Change the meeting time to 3pm"
Response: {{"is_update_intent": true, "update_category": "time_schedule", "confidence": "high"}}

User: "What's the weather today?"
Response: {{"is_update_intent": false, "update_category": null, "confidence": "high"}}

User: "Show me what's in the draft"
Response: {{"is_update_intent": false, "update_category": null, "confidence": "high"}}

User: "His email is john@example.com"
Response: {{"is_update_intent": true, "update_category": "recipients_attendees", "confidence": "high"}}

User: "that's all"
Response: {{"is_update_intent": true, "update_category": "completion_finalization", "confidence": "high"}}

User: "looks good, that's it"
Response: {{"is_update_intent": true, "update_category": "completion_finalization", "confidence": "high"}}

User: "perfect, apply that content to the draft"
Response: {{"is_update_intent": true, "update_category": "content_application", "confidence": "high"}}

YOUR RESPONSE (JSON only):"""

def draft_field_update_prompt(user_query, existing_draft, update_category, conversation_history=None):
    """
    Prompt for extracting specific field updates based on detected update category.
    This is the second step in the update flow.
    """
    history_context = ""
    if conversation_history:
        recent_messages = conversation_history[-6:]
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_context += f"{role.capitalize()}: {content}\n"
    
    draft_type = existing_draft.get('draft_type', 'unknown')
    current_date = datetime.now()
    
    # Build detailed current draft context
    current_fields = ""
    if draft_type == 'email':
        current_fields = f"""Current Email Draft Fields:
- Recipients: {existing_draft.get('to_emails', [])}
- Subject: {existing_draft.get('subject') or '[NOT SET]'}
- Body: {existing_draft.get('body') or '[NOT SET]'}
- Attachments: {existing_draft.get('attachments', [])}"""
    else:  # calendar_event
        current_fields = f"""Current Calendar Event Fields:
- Title/Summary: {existing_draft.get('summary') or '[NOT SET]'}
- Start Time: {existing_draft.get('start_time') or '[NOT SET]'}
- End Time: {existing_draft.get('end_time') or '[NOT SET]'}
- Attendees: {existing_draft.get('attendees', [])}
- Location: {existing_draft.get('location') or '[NOT SET]'}
- Description: {existing_draft.get('description') or '[NOT SET]'}"""

    # Category-specific extraction rules
    category_rules = {
        "subject_title": "Extract subject (for email) or summary/title (for calendar). Use existing body/description as context for generation if user asks to 'create' or 'generate' subject.",
        "body_description": "Extract body content (for email) or description (for calendar). Can be additions to existing content or complete replacements.",
        "recipients_attendees": "Extract email addresses and names for to_emails (email) or attendees (calendar). Format as [{'email': 'addr', 'name': 'name'}].",
        "time_schedule": "Extract start_time and/or end_time for calendar events. Use YYYY-MM-DDTHH:MM:SS format. Only extract if user specifies actual clock times.",
        "location": "Extract location for calendar events.",
        "completion_finalization": "User indicates draft is complete. Check if any fields can be finalized or if this is just acknowledgment. Usually returns empty updates unless specific content needs to be applied.",
        "content_application": "User wants to apply previously generated content. Look for content in conversation history that should be applied to draft fields.",
        "general_content": "Extract any combination of the above fields that user mentions."
    }
    
    extraction_rule = category_rules.get(update_category, "Extract any field updates mentioned by the user.")
    
    return f"""You are an expert at extracting specific field updates for draft modifications.

CURRENT DATE: {current_date.strftime('%Y-%m-%d %H:%M:%S')}

CONVERSATION CONTEXT:
{history_context}

{current_fields}

UPDATE CATEGORY: {update_category}
EXTRACTION RULE: {extraction_rule}

USER QUERY: "{user_query}"

TASK: Extract the specific field updates based on the user's query and update category.

🚨 CRITICAL FIELD EXTRACTION RULES:

FOR SUBJECT/TITLE GENERATION:
- If user asks to "create", "generate", or "make" a subject based on context
- Use the existing body/description content to create an appropriate subject
- Generate concise, descriptive subjects that capture the main topic

FOR TIME EXTRACTION:
- ONLY extract if user specifies actual clock times (2pm, 14:00, 9:30am)
- "tomorrow" without time = NO time extraction
- "Saturday" without time = NO time extraction
- "Saturday at 2pm" = extract start_time

FOR RECIPIENTS/ATTENDEES:
- Extract email addresses in format: {{"email": "addr", "name": "name"}}
- If only email provided: {{"email": "addr", "name": ""}}
- If only name provided: {{"email": "", "name": "name"}}

RESPONSE FORMAT:
Return JSON object with updates to apply:
{{
  "field_updates": {{
    // Only include fields that should be updated
    "field_name": "new_value"
  }}
}}

EXAMPLES:

User: "Create the subject on your own based on the context you have"
Existing Body: "We need to discuss the timing for our meeting next week to finally agree on the product strategy."
Response: {{"field_updates": {{"subject": "Product Strategy Meeting - Next Week Timing Discussion"}}}}

User: "Add Sarah to this email"
Response: {{"field_updates": {{"to_emails": [/* existing emails */, {{"email": "", "name": "Sarah"}}]}}}}

User: "His email is john@example.com"
Response: {{"field_updates": {{"to_emails": [/* existing emails */, {{"email": "john@example.com", "name": ""}}]}}}}

User: "Change the time to 3pm tomorrow" 
Response: {{"field_updates": {{"start_time": "2024-12-21T15:00:00"}}}}

User: "Update the body to include budget discussion"
Response: {{"field_updates": {{"body": "/* existing body */ We should also discuss the budget implications."}}}}

YOUR RESPONSE (JSON only):"""

def draft_creation_intent_prompt(user_query, conversation_history=None):
    """
    Simplified prompt for detecting draft creation intent only.
    No update logic - purely focused on new draft creation.
    """
    history_context = ""
    if conversation_history:
        recent_messages = conversation_history[-6:]
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_context += f"{role.capitalize()}: {content}\n"
    
    current_date = datetime.now()
    
    return f"""You are an expert at detecting NEW draft creation intent and extracting initial information.

🎯 FOCUS: This prompt is ONLY for creating NEW drafts, not updating existing ones.

CURRENT DATE: {current_date.strftime('%Y-%m-%d %H:%M:%S')}

CONVERSATION CONTEXT:
{history_context}

USER QUERY: "{user_query}"

TASK: Detect if user wants to CREATE a new draft (email or calendar event) and extract initial information.

DRAFT CREATION CRITERIA:
- User explicitly mentions "draft" in relation to email or calendar/meeting
- User wants to prepare/compose an email or event for later confirmation
- User wants to create something but not send/schedule it immediately
- User mentions creating/drafting/preparing an email or meeting

NOT DRAFT CREATION:
- User wants to send email immediately (no draft needed)
- User wants to schedule meeting immediately (no draft needed)
- General questions or unrelated queries
- Requests about existing content

🚨 TIME EXTRACTION RULES - CRITICAL:
- "Saturday" → Extract NO start_time, NO end_time
- "Saturday at 3pm" → Extract start_time only: "2025-07-05T15:00:00"
- "tomorrow morning" → Extract NO times
- Only extract times when user specifies ACTUAL CLOCK TIMES

EXTRACTION RULES:
1. DRAFT TYPE: "email" or "calendar_event"
2. RECIPIENTS/ATTENDEES: Names, email addresses, contact references
3. SUBJECT/TITLE: Email subject or event title  
4. BODY/DESCRIPTION: Email body or event description
5. DATE/TIME: Only if actual clock times specified
6. LOCATION: For calendar events only

RESPONSE FORMAT:
{{
  "is_draft_intent": boolean,
  "draft_data": {{
    "draft_type": "email|calendar_event",
    "extracted_info": {{
      // Email fields:
      "to_contacts": ["name1", "email1@domain.com"],
      "subject": "extracted subject",
      "body": "extracted body",
      
      // Calendar fields:
      "summary": "event title",
      "start_time": "YYYY-MM-DDTHH:MM:SS",
      "end_time": "YYYY-MM-DDTHH:MM:SS",
      "attendees": ["name1", "email1@domain.com"],
      "location": "location",
      "description": "description"
    }}
  }}
}}

EXAMPLES:

User: "Create a draft email to John about the meeting"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "email", "extracted_info": {{"to_contacts": ["John"], "body": "about the meeting"}}}}}}

User: "Draft a meeting with Sarah tomorrow at 2pm"
Response: {{"is_draft_intent": true, "draft_data": {{"draft_type": "calendar_event", "extracted_info": {{"summary": "meeting with Sarah", "attendees": ["Sarah"], "start_time": "2024-12-21T14:00:00"}}}}}}

User: "Send an email to Bob now"
Response: {{"is_draft_intent": false, "draft_data": null}}

User: "What's the weather?"
Response: {{"is_draft_intent": false, "draft_data": null}}

YOUR RESPONSE (JSON only):"""