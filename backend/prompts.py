"""
This module contains all the prompt templates used in the application.
Each prompt has a specific purpose and is optimized for a particular task.
"""
from datetime import datetime

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