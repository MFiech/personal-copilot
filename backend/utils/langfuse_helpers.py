"""
Langfuse helper functions for PM Co-Pilot
Provides convenient access to Langfuse-managed prompts
"""

from datetime import datetime, timedelta
from services.langfuse_service import get_langfuse_service
from typing import Optional, List, Dict, Any

def get_managed_prompt(prompt_name: str, **variables) -> Optional[str]:
    """
    Get and compile a Langfuse-managed prompt with variables.
    
    Args:
        prompt_name: Name of the prompt in Langfuse
        **variables: Variables to compile into the prompt
        
    Returns:
        Compiled prompt string or None if not available
    """
    langfuse_service = get_langfuse_service()
    
    if not langfuse_service.is_enabled():
        return None
    
    try:
        prompt = langfuse_service.get_prompt(prompt_name, label="production")
        if prompt:
            # Compile the prompt with variables
            compiled_prompt = prompt.compile(**variables)
            return compiled_prompt
        else:
            print(f"⚠️ Prompt '{prompt_name}' not found in Langfuse")
            return None
    except Exception as e:
        print(f"⚠️ Failed to get prompt '{prompt_name}': {e}")
        return None

def format_conversation_history(thread_history: List[Dict]) -> str:
    """Format conversation history for prompt inclusion."""
    if not thread_history:
        return ""
    
    history_text = ""
    for msg in thread_history:
        if isinstance(msg, dict):
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            history_text += f"{role.capitalize()}: {content}\n"
    
    return history_text

def get_intent_router_prompt(user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Get the intent router prompt from Langfuse or fallback to hardcoded version.
    
    Args:
        user_query: User's query
        conversation_history: Recent conversation context
        
    Returns:
        Formatted prompt string
    """
    history_text = format_conversation_history(conversation_history) if conversation_history else ""
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-intent-router",
        user_query=user_query,
        conversation_history=history_text
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback to hardcoded prompt
    print("⚠️ Using fallback intent router prompt")
    return f"""You are an expert task router for a personal assistant application.
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

YOUR RESPONSE (JSON only):"""

def get_gmail_query_builder_prompt(user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Get the Gmail query builder prompt from Langfuse or fallback.
    
    Args:
        user_query: User's query
        conversation_history: Recent conversation context
        
    Returns:
        Formatted prompt string
    """
    current_date = datetime.now()
    yesterday_date = (current_date - timedelta(days=1)).strftime('%Y/%m/%d')
    today_date = current_date.strftime('%Y/%m/%d')
    last_week_date = (current_date - timedelta(days=7)).strftime('%Y/%m/%d')
    
    history_context = ""
    if conversation_history:
        recent_messages = conversation_history[-6:]  # Last 3 exchanges
        for msg in recent_messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:200]  # Truncate for brevity
            history_context += f"{role.capitalize()}: {content}\n"
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-gmail-query-builder",
        user_query=user_query,
        conversation_history=history_context,
        current_date=current_date.strftime('%Y-%m-%d'),
        yesterday_date=yesterday_date,
        today_date=today_date,
        last_week_date=last_week_date
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback to original implementation
    print("⚠️ Using fallback Gmail query builder prompt")
    from prompts import gmail_query_builder_prompt
    return gmail_query_builder_prompt(user_query, conversation_history)

def get_draft_detection_prompt(user_query: str, conversation_history: Optional[List[Dict]] = None, existing_draft: Optional[Dict] = None) -> str:
    """
    Get the draft detection prompt from Langfuse or fallback.
    
    Args:
        user_query: User's query
        conversation_history: Recent conversation context
        existing_draft: Information about existing draft
        
    Returns:
        Formatted prompt string
    """
    current_date = datetime.now()
    history_context = format_conversation_history(conversation_history) if conversation_history else ""
    
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
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-draft-detection",
        user_query=user_query,
        conversation_history=history_context,
        current_date=current_date.strftime('%Y-%m-%d %H:%M:%S'),
        existing_draft_context=existing_draft_context
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback to original implementation
    print("⚠️ Using fallback draft detection prompt")
    from prompts import draft_detection_prompt
    return draft_detection_prompt(user_query, conversation_history, existing_draft)

def get_email_summarization_prompt(email_body: str, is_thread_email: bool = False, thread_email_count: int = 1) -> str:
    """
    Get the email summarization prompt from Langfuse or fallback.
    
    Args:
        email_body: Email content to summarize
        is_thread_email: Whether this is a thread
        thread_email_count: Number of emails in thread
        
    Returns:
        Formatted prompt string
    """
    if is_thread_email and thread_email_count > 1:
        email_type_text = " threads and conversations"
        email_count_text = f" ({thread_email_count} emails)"
        summarization_instructions = """Provide a comprehensive summary (3-5 sentences) of this email thread. Include:
1. The main topic/subject being discussed
2. Key points from the conversation
3. Any decisions made or action items mentioned
4. The overall flow and conclusion of the discussion"""
        focus_instructions = "Focus on the conversation as a whole, not individual emails."
    else:
        email_type_text = " content"
        email_count_text = ""
        summarization_instructions = "Provide a concise summary (2-4 sentences) of the above email. Highlight the main topic, key information, and any explicit action items mentioned."
        focus_instructions = "Focus solely on the text, not HTML. At most, you can HTML to understand better the email structure/heading."
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-email-summarization",
        email_body=email_body,
        email_type_text=email_type_text,
        email_count_text=email_count_text,
        summarization_instructions=summarization_instructions,
        focus_instructions=focus_instructions
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback to original implementation
    print("⚠️ Using fallback email summarization prompt")
    from prompts import email_summarization_prompt
    return email_summarization_prompt(email_body, is_thread_email, thread_email_count)

def get_query_classification_prompt(user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Get the query classification prompt from Langfuse or fallback.
    
    Args:
        user_query: User's query
        conversation_history: Recent conversation context
        
    Returns:
        Formatted prompt string
    """
    # Build conversation context
    conversation_context = ""
    if conversation_history:
        # Include last 6 messages for context (3 exchanges)
        recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:300]  # Truncate for brevity
            conversation_context += f"{role.capitalize()}: {content}\n"
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-query-classification",
        user_query=user_query,
        conversation_context=conversation_context
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback prompt (simplified version)
    print("⚠️ Using fallback query classification prompt")
    return f"""You are an expert query classifier for a personal assistant that can access emails, calendar events, and contacts.

CONVERSATION CONTEXT (recent messages):
{conversation_context}

USER QUERY: "{user_query}"

CLASSIFICATION TASK:
Analyze the user's query considering the conversation context. Classify the intent as one of:

1. "email" - User wants to find, search, or work with emails/messages
   Examples: "show me emails", "check my inbox", "emails from John", "unread messages"

2. "calendar" - User wants to find, search, or work with calendar events/meetings
   Examples: "what's on my calendar", "meetings today", "schedule for this week", "upcoming events"

3. "contact" - User wants to find, search, or get information about contacts/people
   Examples: "what's the email of John Doe", "contact info for Sarah", "find contact Dawid"

4. "general" - General questions, conversation, or non-email/calendar/contact requests
   Examples: "how's the weather", "what is AI", "tell me a joke"

RESPONSE FORMAT (JSON only):
{{
  "intent": "email" | "calendar" | "contact" | "general",
  "confidence": 0.95,
  "reasoning": "Brief explanation of classification decision",
  "parameters": {{
    "keywords": ["extracted", "keywords"],
    "time_reference": "today|tomorrow|this week|etc",
    "person_name": "extracted person name if relevant"
  }}
}}

Respond with ONLY the JSON object."""

def get_calendar_intent_analysis_prompt(user_query: str, conversation_history: Optional[List[Dict]] = None) -> str:
    """
    Get the calendar intent analysis prompt from Langfuse or fallback.
    
    Args:
        user_query: User's query
        conversation_history: Recent conversation context
        
    Returns:
        Formatted prompt string
    """
    current_date = datetime.now()
    current_weekday = current_date.strftime('%A')
    tomorrow_date = (current_date + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Build conversation context
    conversation_context = ""
    if conversation_history:
        recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
        for msg in recent_history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')[:300]
            conversation_context += f"{role.capitalize()}: {content}\n"
    
    # Try to get from Langfuse first
    managed_prompt = get_managed_prompt(
        "pm-copilot-calendar-intent-analysis",
        user_query=user_query,
        conversation_context=conversation_context,
        current_date=current_date.strftime('%Y-%m-%d'),
        current_weekday=current_weekday,
        current_time=current_date.strftime('%H:%M'),
        tomorrow_date=tomorrow_date
    )
    
    if managed_prompt:
        return managed_prompt
    
    # Fallback to simpler prompt
    print("⚠️ Using fallback calendar intent analysis prompt")
    return f"""You are an expert calendar assistant. Analyze the user's query to determine if they want to CREATE a new calendar event or SEARCH for existing events.

CURRENT CONTEXT:
- Current date: {current_date.strftime('%Y-%m-%d')} ({current_weekday})
- Current time: {current_date.strftime('%H:%M')}

CONVERSATION CONTEXT:
{conversation_context}

USER QUERY: "{user_query}"

TASK: Determine the operation type and extract parameters.

OPERATIONS:
1. "create" - User wants to create/schedule/add a new calendar event
   - Keywords: create, schedule, add, book, set up, plan, new, make
   - Extract: title, date, time, location, description, attendees

2. "search" - User wants to find/view existing calendar events  
   - Keywords: show, find, what's, check, list, view, see
   - Extract: date_range, keywords, attendee_filter

RESPONSE FORMAT (JSON only):
{{
  "operation": "create" | "search",
  "confidence": 0.95,
  "parameters": {{
    // Parameters based on operation type
  }}
}}

Respond with ONLY the JSON object."""
