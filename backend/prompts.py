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