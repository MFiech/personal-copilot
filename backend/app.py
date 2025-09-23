import warnings
import os

# Suppress LangChain deprecation warnings BEFORE any imports
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain_pinecone")
warnings.filterwarnings("ignore", message=".*pydantic_v1.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")
warnings.filterwarnings("ignore", message=".*migrating_memory.*", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*", category=DeprecationWarning)

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from dotenv import load_dotenv
import json
from datetime import datetime

from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from pinecone import Pinecone
import anthropic
import uuid
from services.composio_service import ComposioService
from services.langfuse_client import create_langfuse_client
from langfuse import observe
import re
import time
import requests
from models.conversation import Conversation
from models.insight import Insight
from utils.mongo_client import get_db, get_collection
from config.mongo_config import init_collections, CONVERSATIONS_COLLECTION, EMAILS_COLLECTION
from models.thread import Thread
from prompts import email_summarization_prompt
from bson import ObjectId
from models.email import Email
from utils.date_parser import parse_email_date
from pydantic import SecretStr
from services.contact_service import ContactSyncService
from services.draft_service import DraftService

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))
pinecone_api_key = os.getenv("PINECONE_API_TOKEN")
openai_api_key = os.getenv("OPENAI_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
google_api_key = os.getenv("GOOGLE_API_KEY")
composio_api_key = os.getenv("COMPOSIO_API_KEY")

# Check if we're in testing mode
is_testing = os.getenv("TESTING", "false").lower() == "true"
is_ci = os.getenv("CI", "false").lower() == "true"

if not all([pinecone_api_key, openai_api_key, anthropic_api_key]):
    # Keep google_api_key optional for now, only required if summarization is used with Gemini
    print("Warning: One or more required API keys (Pinecone, OpenAI, Anthropic) are missing from .env")
    # raise ValueError("One or more required API keys are missing from .env") # Soften this for now

# Initialize MongoDB
db = get_db()
init_collections(db)

# Initialize Composio service
try:
    if not composio_api_key:
        raise ValueError("COMPOSIO_API_KEY not found in .env file. Please add it.")
    tooling_service = ComposioService(api_key=composio_api_key)
    print("Composio service initialized successfully")
except Exception as e:
    print(f"FATAL: Failed to initialize Composio service: {e}")
    tooling_service = None

# Initialize Contact service
try:
    contact_service = ContactSyncService()
    print("Contact service initialized successfully")
except Exception as e:
    print(f"Warning: Failed to initialize Contact service: {e}")
    contact_service = None

# Initialize Langfuse client for conversation service
try:
    conversation_langfuse = create_langfuse_client("conversation")
    print(f"✅ [CONVERSATION] Langfuse client initialized: {'enabled' if conversation_langfuse.is_enabled() else 'disabled'}")
except Exception as e:
    print(f"⚠️ [CONVERSATION] Failed to initialize Langfuse client: {e}")
    conversation_langfuse = None

# Lazy initialization for external services to prevent API calls during import
_pinecone_client = None
_pinecone_index = None
_embeddings = None
_vectorstore = None
_llm = None
_gemini_llm = None
_qa_chain = None

def get_pinecone_client():
    """Lazy initialization of Pinecone client."""
    global _pinecone_client
    if _pinecone_client is None and pinecone_api_key and not (is_testing or is_ci):
        try:
            _pinecone_client = Pinecone(api_key=pinecone_api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Pinecone client: {e}")
            _pinecone_client = None
    return _pinecone_client

def get_pinecone_index():
    """Lazy initialization of Pinecone index."""
    global _pinecone_index
    if _pinecone_index is None:
        client = get_pinecone_client()
        if client:
            try:
                _pinecone_index = client.Index("personal")
            except Exception as e:
                print(f"Warning: Failed to initialize Pinecone index: {e}")
                _pinecone_index = None
    return _pinecone_index

def get_embeddings():
    """Lazy initialization of OpenAI embeddings."""
    global _embeddings
    if _embeddings is None and openai_api_key and not (is_testing or is_ci):
        try:
            _embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large", 
                api_key=SecretStr(openai_api_key) if openai_api_key else None
            )
        except Exception as e:
            print(f"Warning: Failed to initialize OpenAI embeddings: {e}")
            _embeddings = None
    return _embeddings

def get_vectorstore():
    """Lazy initialization of Pinecone vectorstore."""
    global _vectorstore
    if _vectorstore is None:
        index = get_pinecone_index()
        embeddings = get_embeddings()
        if index and embeddings:
            try:
                _vectorstore = PineconeVectorStore(
                    index=index, 
                    embedding=embeddings, 
                    text_key="text", 
                    namespace="saved_insights",
                    pinecone_api_key=pinecone_api_key
                )
            except Exception as e:
                print(f"Warning: Failed to initialize Pinecone vectorstore: {e}")
                _vectorstore = None
    return _vectorstore

def get_llm():
    """Lazy initialization of Claude LLM."""
    global _llm
    if _llm is None and anthropic_api_key and not (is_testing or is_ci):
        try:
            _llm = ChatAnthropic(model="claude-3-7-sonnet-latest", anthropic_api_key=anthropic_api_key)
        except Exception as e:
            print(f"Warning: Failed to initialize Claude LLM: {e}")
            _llm = None
    return _llm

def get_gemini_llm():
    """Lazy initialization of Gemini LLM."""
    global _gemini_llm
    if _gemini_llm is None and google_api_key and not (is_testing or is_ci):
        try:
            _gemini_llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-lite",
                google_api_key=google_api_key,
                convert_system_message_to_human=True
            )
            print("Gemini (gemini-2.0-flash-lite) LLM for summarization initialized successfully.")
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini LLM: {e}. Summarization might fall back or fail.")
            _gemini_llm = None
    return _gemini_llm

def get_qa_chain():
    """Lazy initialization of QA chain."""
    global _qa_chain
    if _qa_chain is None:
        llm = get_llm()
        vectorstore = get_vectorstore()
        if llm and vectorstore:
            try:
                _qa_chain = RetrievalQA.from_chain_type(
                    llm=llm,
                    chain_type="stuff",
                    retriever=vectorstore.as_retriever(),
                    return_source_documents=True
                )
            except Exception as e:
                print(f"Warning: Failed to initialize QA chain: {e}")
                _qa_chain = None
    return _qa_chain

# Initialize conversation memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Traced LLM wrapper functions
@observe(as_type="generation", name="claude_main_conversation")
def traced_main_llm_call(prompt: str):
    """Traced wrapper for main Claude LLM calls in conversation"""
    llm = get_llm()
    if llm:
        return llm.invoke(prompt)
    else:
        raise ValueError("Claude LLM not available")

@observe(as_type="generation", name="qa_chain_retrieval")
def traced_qa_chain_call(query: str):
    """Traced wrapper for QA chain calls with retrieval"""
    qa_chain = get_qa_chain()
    if qa_chain:
        return qa_chain.invoke({"query": query})
    else:
        raise ValueError("QA chain not available")

def convert_objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj

def extract_content_from_conversation(thread_history, draft_data):
    """
    Extract content from recent conversation that should be applied to draft.
    Looks for LLM-generated content that appears to be draft content.
    """
    if not thread_history:
        return {}
    
    # Look at the most recent assistant messages for content that looks like draft content
    recent_assistant_messages = []
    for msg in reversed(thread_history[-6:]):  # Last 3 exchanges
        if msg.get('role') == 'assistant':
            recent_assistant_messages.append(msg.get('content', ''))
            if len(recent_assistant_messages) >= 2:  # Max 2 recent assistant messages
                break
    
    updates = {}
    draft_type = draft_data.get('draft_type', 'email')
    
    for content in recent_assistant_messages:
        if not content:
            continue
            
        # Simple heuristics to detect if assistant generated draft content
        content_lower = content.lower()
        
        if draft_type == 'email':
            # Look for email-like content
            if ('subject:' in content_lower or 'email' in content_lower) and len(content) > 50:
                # Try to extract structured email content
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith('subject:'):
                        subject = line[8:].strip().strip('"').strip("'")
                        if subject and not draft_data.get('subject'):
                            updates['subject'] = subject
                            
                # Look for email body content (longer text blocks)
                if not draft_data.get('body') and len(content) > 100:
                    # Extract content that looks like email body
                    potential_body = content
                    # Clean up common assistant prefixes
                    for prefix in ["I'll draft", "Here's", "Based on", "I'll create"]:
                        if potential_body.startswith(prefix):
                            # Find the actual content after the explanation
                            sentences = potential_body.split('.')
                            if len(sentences) > 2:
                                potential_body = '. '.join(sentences[1:]).strip()
                                break
                    
                    if len(potential_body) > 50 and any(word in potential_body.lower() for word in ['meeting', 'discuss', 'agenda', 'time']):
                        updates['body'] = potential_body
        
        elif draft_type == 'calendar_event':
            # Look for calendar event content
            if any(word in content_lower for word in ['meeting', 'event', 'calendar', 'schedule']):
                # Try to extract event details
                if not draft_data.get('summary') and len(content) > 20:
                    # Extract potential event title
                    lines = content.split('\n')
                    for line in lines:
                        if 'meeting' in line.lower() and len(line.strip()) < 100:
                            updates['summary'] = line.strip()
                            break
    
    print(f"[DRAFT] Content extraction found: {updates}")
    return updates

def build_prompt(query, retrieved_docs, thread_history=None, tool_context=None, anchored_item=None, draft_context=None):
    print("=== BUILD_PROMPT FUNCTION CALLED ===")
    prompt_parts = []
    insight_id = None

    # Debug logging
    print(f"[DEBUG] build_prompt called with:")
    print(f"  - query: {query}")
    # print(f"  - tool_context: {json.dumps(tool_context, indent=2) if tool_context else 'None'}")
    print(f"  - retrieved_docs count: {len(retrieved_docs) if retrieved_docs else 0}")
    print(f"  - draft_context: {draft_context}")

    # Add current date and time
    current_time = datetime.now()
    prompt_parts.append(f"Current date and time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
    prompt_parts.append("\n")

    # Add draft context if available
    if draft_context:
        prompt_parts.append("IMPORTANT - Active Draft Context:")
        prompt_parts.append(f"You are currently helping the user with an active {draft_context['draft_type'].replace('_', ' ')} draft.")
        prompt_parts.append(f"Draft ID: {draft_context['draft_id']}")
        prompt_parts.append(f"Draft Summary: {draft_context['summary']}")
        
        if draft_context['is_complete']:
            prompt_parts.append("✅ This draft is COMPLETE and ready to send.")
            prompt_parts.append("If the user is asking for changes, update the existing draft.")
            prompt_parts.append("If the user wants to send it, direct them to use the Send button in the orange bar.")
        else:
            missing_fields_text = ", ".join(draft_context['missing_fields'])
            prompt_parts.append(f"⚠️ This draft is INCOMPLETE. Missing: {missing_fields_text}")
            prompt_parts.append("Focus on gathering the missing information from the user.")
            prompt_parts.append("Ask specific questions to complete the draft.")
        
        prompt_parts.append("DO NOT suggest creating a new draft - update the existing one.")
        prompt_parts.append("Always acknowledge the existing draft in your response.")
        prompt_parts.append("\n")

    # Add anchored item context if available
    if anchored_item:
        prompt_parts.append("IMPORTANT - Anchored Item Context:")
        item_type = anchored_item.get('type', 'unknown')
        item_data = anchored_item.get('data', {})
        
        if item_type == 'email':
            email_id = anchored_item.get('id')
            subject = item_data.get('subject', 'No Subject')
            from_email = item_data.get('from_email', {})
            sender_name = from_email.get('name', 'Unknown Sender')
            sender_email = from_email.get('email', 'unknown@unknown.com')
            date = item_data.get('date', 'Unknown Date')
            
            prompt_parts.append(f"The user has ANCHORED this email for context:")
            prompt_parts.append(f"- Email ID: {email_id}")
            prompt_parts.append(f"- Subject: {subject}")
            prompt_parts.append(f"- From: {sender_name} <{sender_email}>")
            prompt_parts.append(f"- Date: {date}")
            prompt_parts.append("When the user refers to 'this email', 'the email', or similar terms, they are referring to this anchored email.")
            
        elif item_type == 'calendar_event':
            event_id = anchored_item.get('id')
            summary = item_data.get('summary', 'Untitled Event')
            start_time = item_data.get('start', {}).get('dateTime') or item_data.get('start', {}).get('date', 'Unknown Start')
            end_time = item_data.get('end', {}).get('dateTime') or item_data.get('end', {}).get('date', 'Unknown End')
            location = item_data.get('location', '')
            
            prompt_parts.append(f"The user has ANCHORED this calendar event for context:")
            prompt_parts.append(f"- Event ID: {event_id}")
            prompt_parts.append(f"- Title: {summary}")
            prompt_parts.append(f"- Start: {start_time}")
            prompt_parts.append(f"- End: {end_time}")
            if location:
                prompt_parts.append(f"- Location: {location}")
            prompt_parts.append("When the user refers to 'this event', 'the meeting', 'the appointment', or similar terms, they are referring to this anchored event.")
        
        prompt_parts.append("Use this anchored item information when processing the user's query. The IDs provided can be used with Composio services for actions like replies, modifications, deletions, etc.")
        prompt_parts.append("\n")

    # Add thread history to the prompt if available
    if thread_history:
        history_text = ""
        for msg in thread_history:
            history_text += f"{msg['role'].capitalize()}: {msg['content']}\n"
        prompt_parts.append("Thread History:")
        prompt_parts.append(history_text)
        prompt_parts.append("\n")
    else:
        chat_history = memory.load_memory_variables({})["chat_history"]
        if chat_history:
            history_text = ""
            for msg in chat_history:
                role = "Human" if msg.type == "human" else "AI"
                history_text += f"{role}: {msg.content}\n"
            prompt_parts.append("Chat History:")
            prompt_parts.append(history_text)
            prompt_parts.append("\n")

    # Add general instruction with simplified response schema
    prompt_parts.append("""Instructions: You are a helpful AI assistant with access to vector search and external data sources. 
When responding to email-related queries:

1. If emails are found, ONLY respond with: "Here are the recent emails based on your query:"
2. If no emails are found, respond with: "I couldn't find any emails matching your query."
3. Do not list or describe any emails - they will be shown as tiles.
4. Do not add any other text or explanations.

When responding to calendar-related queries:

1. If a calendar EVENT WAS CREATED, provide a helpful summary of the created event with details like title, date, time, location, etc.
2. If calendar events are found from a SEARCH (when you see "Calendar data available: X events found" where X > 0), ONLY respond with: "Here are your calendar events:"
3. If no calendar events are found from a search (when you see "Calendar data available: 0 events found"), provide a helpful explanation of why no events were found and what was searched for. Be specific about the search criteria that failed (e.g., date range, keywords, etc.).
4. For calendar searches, do not list or describe any events - they will be shown as tiles.
5. IMPORTANT: Always check the "Calendar data available" line to determine if events were found (X > 0) or not found (X = 0) before deciding your response.

When responding to contact-related queries:

1. If contacts are found (when you see "Contact data available: X contacts found" where X > 0), provide the contact information directly in your response. Include name, email address, phone number, and any other relevant details from the contact data.
2. If no contacts are found (when you see "Contact data available: 0 contacts found"), provide a helpful explanation that no contacts were found matching the search term.
3. Format the contact information in a clear, readable way for the user.
4. IMPORTANT: Always check the "Contact data available" line to determine if contacts were found (X > 0) or not found (X = 0) before deciding your response.

For non-email, non-calendar, and non-contact queries, provide a helpful response based on the retrieved context when available. If no relevant context is found, provide a helpful response based on your knowledge.""")
    
    # Add Tooling context if provided
    if tool_context:
        prompt_parts.append("\nExternal Data Sources:")
        if "source_type" in tool_context:
            if tool_context["source_type"] == "mail" or tool_context["source_type"] == "gmail":
                messages = tool_context.get("data", {}).get("messages", [])
                prompt_parts.append(f"Email data available: {len(messages)} messages found")
                print(f"[DEBUG] Added to prompt: Email data available: {len(messages)} messages found")
                print(f"[DEBUG] messages type: {type(messages)}")
                print(f"[DEBUG] messages content: {json.dumps(messages, indent=2)[:500] if messages else 'None'}")
                print(f"[DEBUG] messages truthy check: {bool(messages)}")
            elif tool_context["source_type"] == "google-calendar":
                # Check if this is a calendar creation or search response
                data = tool_context.get("data", {})
                if "created_event" in data:
                    # This is a calendar creation response - provide detailed event information
                    created_event = data.get("created_event", {})
                    
                    # Extract event details for LLM context
                    title = created_event.get("summary", "Untitled Event")
                    location = created_event.get("location", "")
                    
                    # Parse start and end times
                    start_info = created_event.get("start", {})
                    end_info = created_event.get("end", {})
                    start_datetime = start_info.get("dateTime", "")
                    end_datetime = end_info.get("dateTime", "")
                    
                    # Format the detailed event information for LLM
                    event_details = f"""Calendar event created successfully! Here are the details of the event that was added to the calendar:

Event Details:
- Title: {title}"""
                    
                    if location:
                        event_details += f"\n- Location: {location}"
                    
                    if start_datetime:
                        try:
                            # Parse the datetime string (e.g., "2025-07-04T17:00:00+02:00")
                            start_dt = datetime.fromisoformat(start_datetime.replace('Z', '+00:00'))
                            formatted_date = start_dt.strftime("%A, %B %d, %Y")
                            formatted_time = start_dt.strftime("%I:%M %p").lstrip('0')
                            
                            event_details += f"\n- Date: {formatted_date}"
                            event_details += f"\n- Start Time: {formatted_time}"
                            
                            if end_datetime:
                                end_dt = datetime.fromisoformat(end_datetime.replace('Z', '+00:00'))
                                end_formatted_time = end_dt.strftime("%I:%M %p").lstrip('0')
                                duration_hours = (end_dt - start_dt).total_seconds() / 3600
                                event_details += f"\n- End Time: {end_formatted_time}"
                                event_details += f"\n- Duration: {duration_hours:.1f} hour(s)"
                        except:
                            # Fallback if datetime parsing fails
                            event_details += f"\n- Start: {start_datetime}"
                            if end_datetime:
                                event_details += f"\n- End: {end_datetime}"
                    
                    event_details += f"\n\nThe user requested to create this event and it has been successfully added to their Google Calendar."
                    
                    prompt_parts.append(event_details)
                    print(f"[DEBUG] Added detailed event information to prompt")
                else:
                    # This is a calendar search response  
                    events = data.get("events", [])
                    total_events = len(events)
                    
                    if total_events == 0:
                        # Provide search context for LLM to generate helpful error message
                        search_context = tool_context.get("search_context", {})
                        context_info = f"Calendar search performed with user query: '{query}'"
                        
                        if search_context:
                            if search_context.get("date_range"):
                                context_info += f", Date range searched: {search_context.get('date_range')}"
                            if search_context.get("keywords"):
                                context_info += f", Keywords searched: '{search_context.get('keywords')}'"
                            if search_context.get("time_min") and search_context.get("time_max"):
                                context_info += f", Time range: {search_context.get('time_min')} to {search_context.get('time_max')}"
                            if search_context.get("search_method"):
                                context_info += f", Search method used: {search_context.get('search_method')}"
                        
                        prompt_parts.append(f"Calendar data available: {total_events} events found (NO EVENTS). {context_info}")
                        print(f"[DEBUG] Added to prompt: Calendar data available: {total_events} events found with search context")
                    else:
                        prompt_parts.append(f"Calendar data available: {total_events} events found (EVENTS FOUND - use success message)")
                        print(f"[DEBUG] Added to prompt: Calendar data available: {total_events} events found")
                    
                    print(f"[DEBUG] events type: {type(events)}")
                    print(f"[DEBUG] events content: {json.dumps(events, indent=2)[:500] if events else 'None'}")
                    print(f"[DEBUG] events truthy check: {bool(events)}")
            elif tool_context["source_type"] == "contact":
                # Handle contact search results
                contacts = tool_context.get("data", {}).get("contacts", [])
                search_term = tool_context.get("data", {}).get("search_term", "")
                total_contacts = len(contacts)
                
                if total_contacts == 0:
                    prompt_parts.append(f"Contact data available: {total_contacts} contacts found (NO CONTACTS). Search term: '{search_term}'")
                    print(f"[DEBUG] Added to prompt: Contact data available: {total_contacts} contacts found (NO CONTACTS)")
                else:
                    prompt_parts.append(f"Contact data available: {total_contacts} contacts found (CONTACTS FOUND - provide contact details)")
                    print(f"[DEBUG] Added to prompt: Contact data available: {total_contacts} contacts found")
                    
                    # Add the actual contact details to the prompt for the LLM to use
                    prompt_parts.append("\nContact Details Found:")
                    for i, contact in enumerate(contacts[:5], 1):  # Limit to first 5 contacts to avoid prompt bloat
                        contact_info = []
                        if contact.get('name'):
                            contact_info.append(f"Name: {contact['name']}")
                        
                        # Include primary email
                        if contact.get('primary_email'):
                            contact_info.append(f"Primary Email: {contact['primary_email']}")
                        
                        # Include ALL emails from the emails array
                        emails = contact.get('emails', [])
                        if emails and len(emails) > 1:
                            all_emails = []
                            for email_obj in emails:
                                email_addr = email_obj.get('email', '')
                                if email_addr and email_addr != contact.get('primary_email'):
                                    all_emails.append(email_addr)
                            if all_emails:
                                contact_info.append(f"Additional Emails: {', '.join(all_emails)}")
                        
                        # Include phone
                        if contact.get('phone'):
                            contact_info.append(f"Phone: {contact['phone']}")
                        
                        prompt_parts.append(f"{i}. {', '.join(contact_info)}")
                        
                        # Add some spacing between contacts if there are multiple
                        if len(contacts) > 1 and i < len(contacts[:5]):
                            prompt_parts.append("")
                
                print(f"[DEBUG] contacts type: {type(contacts)}")
                try:
                    safe_contacts_for_logging = convert_objectid_to_str(contacts)
                    print(f"[DEBUG] contacts content: {json.dumps(safe_contacts_for_logging, indent=2)[:500] if contacts else 'None'}")
                except Exception as log_err:
                    print(f"[DEBUG] Could not serialize contacts for logging: {log_err}")
                print(f"[DEBUG] contacts truthy check: {bool(contacts)}")
        prompt_parts.append("\n")

    # Add retrieved context to the prompt
    if retrieved_docs:
        prompt_parts.append("\nRetrieved Context:")
        for i, doc in enumerate(retrieved_docs, 1):
            metadata = doc.metadata or {}
            source = metadata.get("source", "Unknown")
            insight_id = metadata.get("insight_id", "Unknown")
            full_text = doc.page_content.strip()
            prompt_parts.append(f"{i}. Source: {source}, Insight ID: {insight_id}\nText: {full_text}\n")
            
            # Just get the first insight_id
            if i == 1 and insight_id != "Unknown":
                break
    else:
        prompt_parts.append("\nNo relevant context retrieved from the database.")

    # Add the user query
    prompt_parts.append(f"\nUser Query: {query}\n\nResponse:")
    
    final_prompt = "\n\n".join(prompt_parts)
    # print(f"[DEBUG] Final prompt (first 1000 chars): {final_prompt[:1000]}")
    
    return final_prompt, insight_id

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.get_json()
        query = data.get('query')
        thread_id = data.get('thread_id')
        anchored_item = data.get('anchored_item')
        print(f"\n=== New Chat Request ===")
        print(f"Query: {query}")
        print(f"Thread ID: {thread_id}")
        print(f"Anchored Item: {anchored_item}")
        if not query:
            return jsonify({"error": "No query provided"}), 400

        # Get current timestamp for the entire conversation
        current_timestamp = int(time.time())

        # Create or update thread
        if not thread_id:
            thread = Thread(title=query[:50] + "..." if len(query) > 50 else query)
            thread.save()
            thread_id = thread.thread_id
        else:
            thread = Thread.get_by_id(thread_id)
            if not thread:
                thread = Thread(thread_id=thread_id, title=query[:50] + "..." if len(query) > 50 else query)
                thread.save()

        # Get thread history
        thread_history = []
        if thread_id:
            messages = Conversation.get_by_thread_id(thread_id)
            for msg in messages:
                if 'role' in msg:
                    thread_history.append({"role": msg['role'], "content": msg['content']})
                else:
                    thread_history.append({"role": "user", "content": msg['query']})
                    thread_history.append({"role": "assistant", "content": msg['response']})
        print(f"Thread history length: {len(thread_history)}")

        # Start Langfuse conversation tracing with new context manager pattern
        conversation_span = None
        try:
            if conversation_langfuse and conversation_langfuse.is_enabled():
                conversation_span = conversation_langfuse.create_workflow_span(
                    name="pm_copilot_conversation_turn",
                    thread_id=thread_id,
                    input_data={
                        "user_query": query,
                        "anchored_item": anchored_item,
                        "conversation_length": len(thread_history)
                    },
                    metadata={
                        "workflow_type": "conversation",
                        "has_anchored_item": bool(anchored_item)
                    }
                )
                if conversation_span:
                    conversation_langfuse.update_span_with_session(conversation_span, thread_id, ["conversation", "pm_copilot"])
                print(f"[LANGFUSE] Started conversation span: {conversation_span.trace_id if conversation_span else 'None'}")
        except Exception as e:
            print(f"[LANGFUSE] Warning: Failed to start conversation span: {e}")

        # Initialize variables for tooling results
        raw_tool_results = None
        assistant_tool_results = None
        raw_email_list = None

        # Step 0: NEW SEPARATED DRAFT ROUTING LOGIC
        print(f"\n🔄 === DRAFT INTENT ROUTING STARTED ===")
        print(f"[DRAFT_ROUTING] Query: {query}")
        print(f"[DRAFT_ROUTING] Anchored Item: {anchored_item}")
        should_skip_tooling = False
        draft_detection_result = None  # Store result to reuse later
        draft_update_result = None  # Store draft update result
        
        try:
            from services.draft_service import DraftService
            draft_service = DraftService()
            
            if anchored_item and anchored_item.get('type') == 'draft':
                # Route 1: Draft Anchored - Check for Update Intent
                print(f"[DRAFT] Draft anchored - checking for update intent")
                
                # CRITICAL FIX: Always refresh draft data from database to avoid staleness
                draft_id = anchored_item.get('id')
                fresh_draft = draft_service.get_draft_by_id(draft_id)
                if fresh_draft:
                    anchored_draft_data = fresh_draft.to_dict()
                    print(f"[DRAFT] Refreshed draft data from database")
                else:
                    print(f"[DRAFT] WARNING: Could not refresh draft {draft_id} from database, using stale data")
                    anchored_draft_data = anchored_item.get('data', {})
                
                update_intent = draft_service.detect_draft_update_intent(
                    query, anchored_draft_data, thread_history, thread_id=thread_id
                )
                
                if update_intent.get("is_update_intent"):
                    print(f"[DRAFT] Update intent detected - processing draft update")
                    print(f"[DRAFT] Update category: {update_intent.get('update_category')}")
                    
                    # Extract field updates
                    field_updates = draft_service.extract_draft_field_updates(
                        query, anchored_draft_data, update_intent.get('update_category'), 
                        thread_history, thread_id=thread_id
                    )
                    
                    # Handle different update categories
                    update_category = update_intent.get('update_category')
                    
                    if update_category == "completion_finalization":
                        print(f"[DRAFT] Completion/finalization detected - checking for content to apply")
                        # Check if there's recent LLM-generated content in conversation that should be applied
                        content_updates = extract_content_from_conversation(thread_history, anchored_draft_data)
                        if content_updates:
                            print(f"[DRAFT] Found content to apply: {list(content_updates.keys())}")
                            field_updates = {"field_updates": content_updates}
                        else:
                            print(f"[DRAFT] No content to apply - draft marked as complete")
                            field_updates = {"field_updates": {}}  # No updates, just acknowledgment
                    
                    elif update_category == "content_application":
                        print(f"[DRAFT] Content application detected - extracting from conversation")
                        content_updates = extract_content_from_conversation(thread_history, anchored_draft_data)
                        field_updates = {"field_updates": content_updates or {}}
                    
                    else:
                        # Normal field extraction for other categories
                        field_updates = draft_service.extract_draft_field_updates(
                            query, anchored_draft_data, update_category, 
                            thread_history, thread_id=thread_id
                        )
                    
                    if field_updates.get("field_updates"):
                        # Apply updates to the draft
                        draft_id = anchored_item.get('id')
                        success = draft_service.update_draft(draft_id, field_updates.get("field_updates"))
                        
                        if success:
                            print(f"[DRAFT] Successfully updated draft {draft_id}")
                            draft_update_result = {
                                "success": True,
                                "draft_id": draft_id,
                                "updates": field_updates.get("field_updates"),
                                "message": "Draft updated successfully",
                                "update_category": update_category
                            }
                            should_skip_tooling = True  # Skip tooling since we handled the update
                        else:
                            print(f"[DRAFT] Failed to update draft {draft_id}")
                    else:
                        if update_category == "completion_finalization":
                            print(f"[DRAFT] Draft completion acknowledged - no updates needed")
                            should_skip_tooling = True  # Skip tooling, just acknowledge
                        else:
                            print(f"[DRAFT] No field updates extracted")
                else:
                    print(f"[DRAFT] No update intent - proceeding to tooling service")
                    should_skip_tooling = False
                    
            else:
                # Route 2: No Draft Anchored - Check for Creation Intent
                print(f"[DRAFT] No draft anchored - checking for creation intent")
                
                draft_detection_result = draft_service.detect_draft_creation_intent(
                    query, thread_history, thread_id=thread_id
                )
                
                if draft_detection_result.get("is_draft_intent"):
                    print(f"[DRAFT] Creation intent detected - SKIPPING tooling service")
                    print(f"[DRAFT] Draft creation result: {draft_detection_result}")
                    should_skip_tooling = True
                else:
                    print(f"[DRAFT] No creation intent - proceeding with normal tooling flow")
                    should_skip_tooling = False
                    
        except Exception as e:
            print(f"[DRAFT] Error in draft routing: {e}")
            import traceback
            traceback.print_exc()
            # If draft routing fails, proceed with normal flow
            should_skip_tooling = False

        if tooling_service and not should_skip_tooling:
            print(f"[DEBUG] Tooling service is available, starting processing...")
            try:
                print("\n=== Processing Tooling Query ===")
                print(f"Using Tooling service: {type(tooling_service).__name__}")
                print(f"[DEBUG] About to call tooling_service.process_query...")
                raw_tool_results = tooling_service.process_query(query, thread_history, anchored_item, thread_id=thread_id)
                print(f"[DEBUG] tooling_service.process_query completed successfully")
                # Safe logging that handles ObjectIds
                try:
                    safe_results_for_logging = convert_objectid_to_str(raw_tool_results)
                    print(f"[DEBUG] Raw data from service assigned to raw_tool_results: {json.dumps(safe_results_for_logging, indent=2)[:1000]}")
                except Exception as log_err:
                    print(f"[DEBUG] Could not serialize raw_tool_results for logging: {log_err}")
                    print(f"[DEBUG] raw_tool_results type: {type(raw_tool_results)}")
                print(f"[DEBUG] raw_tool_results type: {type(raw_tool_results)}")
                print(f"[DEBUG] raw_tool_results keys: {list(raw_tool_results.keys()) if isinstance(raw_tool_results, dict) else 'N/A'}")
                print(f"[DEBUG] raw_tool_results source_type: {raw_tool_results.get('source_type') if isinstance(raw_tool_results, dict) else 'N/A'}")
                print(f"[DEBUG] raw_tool_results truthy check: {bool(raw_tool_results)}")
                
                tool_output = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}

                # Check if the results are emails and transform them into the structure our Conversation model expects.
                # Handle nested data structure: tool_output.data.messages or tool_output.messages
                messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
                if tool_output and messages_data:
                    print(f"[DEBUG] Processing mail results from tool_output...")
                    print(f"[DEBUG] Found messages_data via nested structure handling")
                    print(f"[DEBUG] messages_data type: {type(messages_data)}")
                    print(f"[DEBUG] messages_data keys: {list(messages_data.keys()) if isinstance(messages_data, dict) else 'N/A'}")
                    print(f"[DEBUG] messages_data content: {json.dumps(messages_data, indent=2)[:500] if messages_data else 'None'}")
                    
                    if isinstance(messages_data, dict):
                        raw_gmail_emails = messages_data.get("messages", [])
                        # Gmail API pagination metadata
                        next_page_token = raw_tool_results.get('next_page_token') if raw_tool_results else None
                        total_available = raw_tool_results.get('total_estimate', len(raw_gmail_emails)) if raw_tool_results else len(raw_gmail_emails)
                        print(f"[DEBUG] next_page_token: {next_page_token}, total_estimate: {total_available}, raw_gmail_emails count: {len(raw_gmail_emails)}")
                        pagination_data = {
                            'page_token': None,  # First page has no token
                            'next_page_token': next_page_token,
                            'limit': len(raw_gmail_emails),
                            'total': total_available,
                            'has_more': bool(next_page_token)  # Has more if we got a next_page_token
                        }
                        print(f"[DEBUG] Extracted raw Gmail emails from nested dict: {len(raw_gmail_emails) if raw_gmail_emails else 0}")
                        print(f"[DEBUG] Gmail API pagination data: {pagination_data}")
                    elif isinstance(messages_data, list):
                        raw_gmail_emails = messages_data
                        # For list format, assume we might have more if we got exactly 10
                        next_page_token = raw_tool_results.get('next_page_token') if raw_tool_results else None
                        total_available = raw_tool_results.get('total_estimate', len(raw_gmail_emails)) if raw_tool_results else len(raw_gmail_emails)
                        pagination_data = {
                            'page_token': None,
                            'next_page_token': next_page_token,
                            'limit': len(raw_gmail_emails),
                            'total': total_available,
                            'has_more': bool(next_page_token)
                        }
                        print(f"[DEBUG] messages_data is already a list: {len(raw_gmail_emails)}")
                        print(f"[DEBUG] Gmail API pagination data: {pagination_data}")
                    else:
                        print(f"[DEBUG] messages_data is neither dict nor list: {type(messages_data)}")
                        raw_gmail_emails = []
                        pagination_data = {'page_token': None, 'next_page_token': None, 'limit': 0, 'total': 0, 'has_more': False}

                    if raw_gmail_emails is not None and len(raw_gmail_emails) > 0:
                        print(f"[DEBUG] Processing {len(raw_gmail_emails)} raw Gmail emails...")
                        
                        # Process each raw Gmail email and create Email model instances
                        processed_emails = []
                        email_ids_for_conversation = []
                        
                        for composio_email in raw_gmail_emails:
                            try:
                                # Extract data from Composio response format
                                email_id = composio_email.get('messageId', str(uuid.uuid4()))
                                
                                # Extract available fields from Composio format
                                message_text = composio_email.get('messageText', '')
                                label_ids = composio_email.get('labelIds', [])
                                attachment_list = composio_email.get('attachmentList', [])
                                
                                # Extract actual email metadata from Composio fields
                                subject = composio_email.get('subject', f"Email {email_id[:8]}")
                                sender_raw = composio_email.get('sender', '')
                                to_raw = composio_email.get('to', '')
                                date_timestamp = composio_email.get('messageTimestamp', '')
                                
                                # Parse sender information
                                from_email = {'email': 'unknown@unknown.com', 'name': 'Unknown Sender'}
                                if sender_raw:
                                    # Parse format like '"Michał Fiech" <michal.fiech@gmail.com>' or just 'email@domain.com'
                                    import re
                                    email_match = re.search(r'<([^>]+)>', sender_raw)
                                    name_match = re.search(r'"([^"]+)"', sender_raw)
                                    
                                    if email_match:
                                        email_addr = email_match.group(1)
                                        name = name_match.group(1) if name_match else email_addr.split('@')[0]
                                        from_email = {'email': email_addr, 'name': name}
                                    elif '@' in sender_raw:
                                        # Just an email address
                                        from_email = {'email': sender_raw.strip(), 'name': sender_raw.split('@')[0]}
                                
                                # Parse recipient information
                                to_emails = [{'email': 'unknown@unknown.com', 'name': 'Unknown Recipient'}]
                                if to_raw:
                                    # Parse format like 'Przemyslaw Dyrda <p.dyrda@kropidlowscy.com>'
                                    email_match = re.search(r'<([^>]+)>', to_raw)
                                    name_match = re.search(r'^([^<]+)', to_raw)
                                    
                                    if email_match:
                                        email_addr = email_match.group(1)
                                        name = name_match.group(1).strip() if name_match else email_addr.split('@')[0]
                                        to_emails = [{'email': email_addr, 'name': name}]
                                    elif '@' in to_raw:
                                        # Just an email address
                                        to_emails = [{'email': to_raw.strip(), 'name': to_raw.split('@')[0]}]
                                
                                # Parse date from timestamp
                                date_header = date_timestamp if date_timestamp else 'Unknown Date'
                                
                                # Don't save any content during initial fetch to keep DB light
                                content = {
                                    'text': '',
                                    'html': ''
                                }
                                
                                # Extract Gmail thread ID from Composio response
                                gmail_thread_id = composio_email.get('thread_id') or composio_email.get('threadId', '')
                                
                                # Create Email model instance
                                email_doc = Email(
                                    email_id=email_id,
                                    thread_id=thread_id,
                                    gmail_thread_id=gmail_thread_id,  # Pass the Gmail thread ID
                                    subject=subject,
                                    from_email=from_email,
                                    to_emails=to_emails,
                                    date=date_header,
                                    content=content,
                                    metadata={
                                        'source': 'COMPOSIO',
                                        'label_ids': label_ids,
                                        'attachment_count': len(attachment_list),
                                        'thread_id': gmail_thread_id,  # Also store in metadata for backward compatibility
                                        'timestamp': date_timestamp
                                    }
                                )
                                
                                # Save to database
                                email_doc.save()
                                print(f"[DEBUG] Saved email to database: {email_id} - Subject: {subject[:50]}")
                                
                                # Create a dict representation for frontend use (no content to keep it light)
                                email_dict = {
                                    'id': email_id,
                                    'subject': subject,
                                    'from_email': from_email,
                                    'to_emails': to_emails,
                                    'date': date_header,
                                    'content': content,  # Empty content as per requirement
                                    'metadata': email_doc.metadata
                                }
                                
                                processed_emails.append(email_dict)
                                email_ids_for_conversation.append(email_id)
                                
                            except Exception as e:
                                print(f"[DEBUG] Error processing Composio email {composio_email.get('messageId', 'unknown')}: {str(e)}")
                                import traceback
                                print(f"[DEBUG] Traceback: {traceback.format_exc()}")
                                continue
                        
                        # Set the variables for use in the rest of the function
                        raw_email_list = processed_emails  # For frontend response
                        assistant_tool_results = {
                            "source_type": "mail",
                            "emails": email_ids_for_conversation  # Only IDs for conversation storage
                        }
                        print(f"[DEBUG] Processed {len(processed_emails)} emails. Created {len(email_ids_for_conversation)} email IDs for conversation.")
                    else:
                        print(f"[DEBUG] No emails extracted. raw_gmail_emails: {raw_gmail_emails}")
                        raw_email_list = []
                        assistant_tool_results = {
                            "source_type": "mail",
                            "emails": []
                        }
                elif raw_tool_results and raw_tool_results.get('source_type') == 'google-calendar':
                    # Process calendar events for database storage
                    print(f"[DEBUG] Processing calendar results for database storage")
                    calendar_data = raw_tool_results.get('data', {})
                    
                    # Handle both creation and search responses
                    events = []
                    if calendar_data:
                        if 'created_event' in calendar_data:
                            # This is a creation response - wrap the single event in a list
                            created_event = calendar_data.get('created_event', {})
                            if created_event:
                                events = [created_event]
                            print(f"[DEBUG] Processing calendar creation response with 1 created event")
                        elif 'data' in calendar_data and isinstance(calendar_data['data'], dict) and 'items' in calendar_data['data']:
                            # Nested items in calendar_data.data.items (Composio structure) - for database storage
                            events = calendar_data['data'].get('items', [])
                            print(f"[DEBUG] Processing calendar search response with {len(events)} events (nested items for DB)")
                        elif 'items' in calendar_data:
                            # Direct items in calendar_data.items (legacy compatibility) - for database storage
                            events = calendar_data.get('items', [])
                            print(f"[DEBUG] Processing calendar search response with {len(events)} events (direct items for DB)")
                        else:
                            # Fallback: check if calendar_data itself is an event object
                            if isinstance(calendar_data, dict) and 'id' in calendar_data:
                                events = [calendar_data]
                                print(f"[DEBUG] Processing single calendar event as fallback")
                    
                    # For calendar events, we store the full event objects (not just IDs like emails)
                    assistant_tool_results = {
                        "source_type": "google-calendar", 
                        "calendar_events": events
                    }
                    print(f"[DEBUG] Processed {len(events)} calendar events for conversation storage")
                elif raw_tool_results and raw_tool_results.get('source_type') == 'contact':
                    # For contact tool results, structure the data for prompt building
                    contact_data = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
                    contacts = contact_data.get('contacts', [])
                    search_term = contact_data.get('search_term', '')
                    
                    tool_context = {
                        'source_type': 'contact',
                        'data': {
                            'contacts': contacts,
                            'search_term': search_term,
                            'total_contacts': len(contacts)
                        }
                    }
                else:
                    print(f"[DEBUG] Not processing as mail or calendar results. source_type: {raw_tool_results.get('source_type') if raw_tool_results and isinstance(raw_tool_results, dict) else 'N/A'}")
                    print(f"[DEBUG] raw_tool_results is: {raw_tool_results}")

            except Exception as e:
                print(f"Error processing Tooling data: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print("Tooling service not initialized")

        # `tool_context` is used for prompt building. We need to provide processed data to the LLM.
        tool_context = None
        if raw_tool_results and raw_tool_results.get('source_type') == 'mail' and raw_email_list:
            tool_context = {
                'source_type': 'mail',
                'data': {
                    'messages': raw_email_list  # Use processed emails for LLM context
                }
            }
        elif raw_tool_results and raw_tool_results.get('source_type') == 'google-calendar':
            # For calendar tool results, maintain the source_type and structure the data properly
            calendar_data = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            
            # Handle both creation and search responses for tool_context
            if 'created_event' in calendar_data:
                # This is a creation response - pass the creation data directly
                tool_context = {
                    'source_type': 'google-calendar',
                    'data': calendar_data  # Pass the whole data including created_event
                }
            else:
                # This is a search response - extract events list with nested structure handling
                events = []
                if calendar_data:
                    if 'data' in calendar_data and isinstance(calendar_data['data'], dict) and 'items' in calendar_data['data']:
                        # Nested items in calendar_data.data.items (Composio structure)
                        events = calendar_data['data'].get('items', [])
                    elif 'items' in calendar_data:
                        # Direct items in calendar_data.items (legacy compatibility)
                        events = calendar_data.get('items', [])
                tool_context = {
                    'source_type': 'google-calendar',
                    'data': {
                        'events': events,
                        'total_events': len(events)
                    }
                }
                # Pass through search context if available
                if raw_tool_results and raw_tool_results.get('search_context'):
                    tool_context['search_context'] = raw_tool_results.get('search_context')
        elif raw_tool_results and raw_tool_results.get('source_type') == 'contact':
            # For contact tool results, structure the data for prompt building
            contact_data = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            contacts = contact_data.get('contacts', [])
            search_term = contact_data.get('search_term', '')
            
            tool_context = {
                'source_type': 'contact',
                'data': {
                    'contacts': contacts,
                    'search_term': search_term,
                    'total_contacts': len(contacts)
                }
            }
        elif raw_tool_results and raw_tool_results.get('source_type') not in ['mail', 'google-calendar']:
            # For other tool results, use the original structure but preserve source_type
            tool_context = {
                'source_type': raw_tool_results.get('source_type'),
                'data': raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            }
        
        # Decide whether to bypass LLM for mail results
        mail_mode = bool(raw_tool_results and raw_tool_results.get('source_type') == 'mail')

        if mail_mode:
            # DEBUG: Add focused debugging for mail handling
            print("\n[MAIL][DEBUG] Tool raw result keys:",
                  list(raw_tool_results.keys()) if isinstance(raw_tool_results, dict) else type(raw_tool_results))
            print("[MAIL][DEBUG] total_estimate:", raw_tool_results.get("total_estimate"))
            print("[MAIL][DEBUG] next_page_token:", (raw_tool_results.get("next_page_token") or "")[:24] if isinstance(raw_tool_results, dict) else None)

            raw_email_list = []
            try:
                # Debug: Log the structure of raw_tool_results
                print(f"[MAIL][DEBUG] raw_tool_results keys: {list(raw_tool_results.keys())}")
                print(f"[MAIL][DEBUG] raw_tool_results['data'] type: {type(raw_tool_results.get('data'))}")
                if raw_tool_results.get('data'):
                    print(f"[MAIL][DEBUG] raw_tool_results['data'] keys: {list(raw_tool_results.get('data').keys())}")
                    print(f"[MAIL][DEBUG] raw_tool_results['data']['messages'] type: {type(raw_tool_results.get('data', {}).get('messages'))}")
                    print(f"[MAIL][DEBUG] raw_tool_results['data']['messages'] length: {len(raw_tool_results.get('data', {}).get('messages', []))}")
                    print(f"[MAIL][DEBUG] raw_tool_results['data']['messages'] content preview: {str(raw_tool_results.get('data', {}).get('messages', []))[:200]}...")
                    print(f"[MAIL][DEBUG] raw_tool_results['data'] full content: {str(raw_tool_results.get('data'))[:500]}...")
                
                # Fix: Composio response has nested data structure: data.data.messages
                raw_email_list = raw_tool_results.get("data", {}).get("data", {}).get("messages", []) or raw_tool_results.get("emails", []) or []
                print(f"[MAIL][DEBUG] After extraction - raw_email_list type: {type(raw_email_list)}, length: {len(raw_email_list)}")
                if raw_email_list:
                    print(f"[MAIL][DEBUG] First email keys: {list(raw_email_list[0].keys()) if isinstance(raw_email_list[0], dict) else 'Not a dict'}")
            except Exception as e:
                print("[MAIL][ERROR] Failed to extract email list:", e)

            print("[MAIL][DEBUG] emails_type:", type(raw_email_list), "len:", (len(raw_email_list) if isinstance(raw_email_list, list) else "n/a"))
            if isinstance(raw_email_list, list) and raw_email_list:
                sample = raw_email_list[0]
                print("[MAIL][DEBUG] sample_email_keys:", (list(sample.keys()) if isinstance(sample, dict) else type(sample)))
            # Deterministic assistant text for email queries
            K = pagination_data['limit'] if 'pagination_data' in locals() else (len(raw_email_list) if raw_email_list else 0)
            total_available = None
            if 'pagination_data' in locals() and isinstance(pagination_data, dict):
                total_available = pagination_data.get('total')
            if total_available is None:
                total_available = len(raw_email_list) if raw_email_list else 0

            if total_available == 0:
                response_text = "No messages found."
            else:
                response_text = f"Found {total_available} emails (showing {K})."
            
            print(f"[MAIL][DEBUG] K={K}, N={total_available}, assistant_text: {response_text}")

            insight_id = None
            print(f"[MAIL] Bypassing LLM; total_estimate={total_available}, showing={K}")
        else:
            # Get relevant documents using the retriever
            try:
                result = traced_qa_chain_call(query)
                retrieved_docs = result["source_documents"]
            except Exception as e:
                print(f"Error in QA chain: {str(e)}")
                retrieved_docs = []

            # Step 1: Build the LLM prompt with context
            print(f"\n=== Building LLM Prompt ===")

            # Check for active drafts in this thread for LLM context
            draft_context = None
            try:
                from services.draft_service import DraftService
                draft_service = DraftService()
                print(f"[DRAFT_CONTEXT] Looking for active drafts in thread: {thread_id}")
                # CRITICAL: Add thread isolation check
                if not thread_id:
                    print(f"[DRAFT_CONTEXT] ❌ ERROR: thread_id is None or empty, skipping draft context")
                    active_drafts = []
                else:
                    active_drafts = draft_service.get_active_drafts_by_thread(thread_id)
                    print(f"[DRAFT_CONTEXT] Query returned {len(active_drafts)} drafts for thread {thread_id}")

                if active_drafts:
                    print(f"[DRAFT_CONTEXT] Found {len(active_drafts)} active draft(s) for thread {thread_id}")
                    for i, draft in enumerate(active_drafts):
                        draft_dict = draft.to_dict() if hasattr(draft, 'to_dict') else {"draft_id": getattr(draft, 'draft_id', 'unknown')}
                        print(f"[DRAFT_CONTEXT] Draft {i}: {draft_dict.get('draft_id')} in thread {draft_dict.get('thread_id')}")
                    
                    # Create draft context for the most recent active draft
                    latest_draft = active_drafts[0]  # get_active_drafts_by_thread sorts by created_at desc

                    # CRITICAL FIX: Convert Draft object to dict to avoid serialization issues
                    draft_dict = latest_draft.to_dict() if hasattr(latest_draft, 'to_dict') else {
                        "draft_id": getattr(latest_draft, 'draft_id', None),
                        "draft_type": getattr(latest_draft, 'draft_type', None),
                        "thread_id": getattr(latest_draft, 'thread_id', None),
                        "to_emails": getattr(latest_draft, 'to_emails', []),
                        "subject": getattr(latest_draft, 'subject', None),
                        "body": getattr(latest_draft, 'body', None),
                        "summary": getattr(latest_draft, 'summary', None),
                        "start_time": getattr(latest_draft, 'start_time', None),
                        "created_at": getattr(latest_draft, 'created_at', None)
                    }

                    # CRITICAL VALIDATION: Ensure draft actually belongs to current thread
                    draft_thread_id = draft_dict.get("thread_id")
                    if draft_thread_id != thread_id:
                        print(f"[DRAFT_CONTEXT] ❌ CRITICAL ERROR: Draft {draft_dict.get('draft_id')} belongs to thread {draft_thread_id} but current thread is {thread_id}")
                        print(f"[DRAFT_CONTEXT] ❌ SKIPPING draft context to prevent cross-thread contamination")
                        draft_context = None
                        raise Exception(f"Cross-thread draft contamination detected")  # Skip draft context creation

                    # Validate the draft to get missing fields info
                    validation_result = draft_service.validate_draft_completeness(latest_draft.draft_id)
                    missing_fields = validation_result.get('missing_fields', []) if validation_result else []

                    # Create draft summary using the dict data
                    if draft_dict.get("draft_type") == "email":
                        to_list = [email.get("name", email.get("email", "Unknown")) for email in (draft_dict.get("to_emails") or [])]
                        summary = f"Email to {', '.join(to_list[:2])}" + ("..." if len(to_list) > 2 else "")
                        if draft_dict.get("subject"):
                            summary += f" - Subject: {draft_dict['subject']}"
                    else:  # calendar_event
                        summary = f"Calendar event: {draft_dict.get('summary') or 'Untitled'}"
                        if draft_dict.get("start_time"):
                            summary += f" on {draft_dict['start_time']}"

                    # Safe created_at handling
                    created_at_str = None
                    created_at = draft_dict.get("created_at")
                    if created_at:
                        if hasattr(created_at, 'isoformat'):
                            created_at_str = created_at.isoformat()
                        else:
                            created_at_str = str(created_at)

                    draft_context = {
                        "type": "active_draft",
                        "draft_id": draft_dict.get("draft_id"),
                        "draft_type": draft_dict.get("draft_type"),
                        "summary": summary,
                        "is_complete": len(missing_fields) == 0,
                        "missing_fields": missing_fields,
                        "created_at": created_at_str
                    }
                    print(f"[DRAFT] Created context for draft {draft_dict.get('draft_id')}: {draft_dict.get('draft_type')}, complete: {draft_context['is_complete']}")

            except Exception as e:
                print(f"[DRAFT] Error getting draft context: {e}")

            prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, raw_tool_results, anchored_item, draft_context)

            try:
                print(f"[DEBUG] Calling LLM with prompt...")
                response = traced_main_llm_call(prompt)
                response_text = response.content[0] if isinstance(response.content, list) else response.content
                response_text = response_text.strip() if isinstance(response_text, str) else str(response_text)
                print(f"[DEBUG] LLM response: '{response_text}'")
            except Exception as e:
                if "overloaded_error" in str(e):
                    error_message = "The AI service is currently experiencing high load. Please try again in a few moments."
                    return jsonify({"error": error_message}), 503
                raise e

        # Step 1: Save the user's message
        print(f"\n=== Saving User Message ===")
        user_message = Conversation(
            thread_id=thread_id,
            role='user',
            content=query,
            timestamp=current_timestamp
        )
        user_message.save()
        print(f"User message saved. message_id: {user_message.message_id}, role: {user_message.role}, content: {user_message.content[:100] if user_message.content else 'None'}...")

        # Step 1.5: Check for draft creation intent
        # Process Draft Operations - handle both creation and updates
        print(f"\n=== Processing Draft Operations ===")
        draft_created = None
        try:
            # Initialize draft service if not already available
            if 'draft_service' not in locals():
                from services.draft_service import DraftService
                draft_service = DraftService()
                
            # Handle draft update result (from anchored draft updates)
            if draft_update_result and draft_update_result.get("success"):
                print(f"[DRAFT] Processing draft update result")
                # Get the updated draft to return in response
                updated_draft = draft_service.get_draft_by_id(draft_update_result.get("draft_id"))
                if updated_draft:
                    draft_created = updated_draft  # Reuse variable for consistency
                    print(f"[DRAFT] Draft update processed: {draft_update_result}")
                detection_result = None  # No creation needed
                
            elif anchored_item and anchored_item.get('type') == 'draft':
                # Draft was anchored but no update performed - skip draft operations
                print(f"[DRAFT] Draft anchored but no update intent - skipping draft operations")
                detection_result = None
                
            else:
                # Handle draft creation (no anchored draft)
                print(f"[DRAFT_CREATION] Looking for existing drafts in thread: {thread_id}")
                existing_drafts = draft_service.get_active_drafts_by_thread(thread_id)
                print(f"[DRAFT_CREATION] Found {len(existing_drafts)} existing drafts in thread {thread_id}")
                detection_result = draft_detection_result  # Reuse from routing logic
            
            if (not mail_mode) and detection_result and detection_result.get("is_draft_intent"):
                print(f"[DRAFT] Draft intent detected: {detection_result}")
                
                # Check if we should update an existing draft instead of creating new one
                draft_data = detection_result.get("draft_data", {})
                draft_type = draft_data.get("draft_type")
                
                # Look for existing active draft of the same type
                existing_draft = None
                for draft in existing_drafts:
                    if draft.draft_type == draft_type and draft.status == "active":
                        existing_draft = draft
                        break
                
                if existing_draft:
                    print(f"[DRAFT] Found existing active draft {existing_draft.draft_id}, updating instead of creating new")
                    
                    # Extract updates from the detection result
                    extracted_info = draft_data.get("extracted_info", {})
                    updates = {}
                    
                    if draft_type == "calendar_event":
                        if "summary" in extracted_info and extracted_info["summary"]:
                            updates["summary"] = extracted_info["summary"]
                        if "start_time" in extracted_info and extracted_info["start_time"]:
                            updates["start_time"] = extracted_info["start_time"]
                        if "end_time" in extracted_info and extracted_info["end_time"]:
                            updates["end_time"] = extracted_info["end_time"]
                        if "attendees" in extracted_info:
                            # Smart merge attendees - update existing ones with emails when provided
                            current_attendees = existing_draft.attendees or []
                            new_contacts = extracted_info["attendees"]
                            
                            # Process new contacts to see if they provide emails for existing attendees
                            updated_contacts = []
                            for new_contact in new_contacts:
                                # Check if this is in format "Name (email@domain.com)"
                                if isinstance(new_contact, str) and "(" in new_contact and "@" in new_contact:
                                    # Extract name and email
                                    import re  # Local import to avoid scoping issues
                                    paren_match = re.search(r'^(.+?)\s*\(([^)]+@[^)]+)\)$', new_contact.strip())
                                    if paren_match:
                                        name_part = paren_match.group(1).strip()
                                        email_part = paren_match.group(2).strip()
                                        
                                        # Find existing attendee with this name but no email
                                        found_existing = False
                                        for existing_att in current_attendees:
                                            if (existing_att.get("name", "").lower() == name_part.lower() and 
                                                (not existing_att.get("email") or existing_att.get("needs_clarification"))):
                                                # Update this attendee with the email
                                                existing_att["email"] = email_part
                                                existing_att["needs_clarification"] = False
                                                found_existing = True
                                                print(f"[DRAFT] Updated attendee '{name_part}' with email '{email_part}'")
                                                break
                                        
                                        if not found_existing:
                                            # Add as new attendee
                                            updated_contacts.append(name_part + " (" + email_part + ")")
                                    else:
                                        # Add as regular contact
                                        updated_contacts.append(new_contact)
                                else:
                                    # Add as regular contact
                                    updated_contacts.append(new_contact)
                            
                            # Only add truly new contacts (not email updates)
                            if updated_contacts:
                                current_names = [att.get("name", att.get("email", "")) for att in current_attendees]
                                all_contacts = list(set(current_names + updated_contacts))
                                updates["attendee_contacts"] = all_contacts
                        if "location" in extracted_info and extracted_info["location"]:
                            updates["location"] = extracted_info["location"]
                        if "description" in extracted_info and extracted_info["description"]:
                            updates["description"] = extracted_info["description"]
                    
                    elif draft_type == "email":
                        if "to_contacts" in extracted_info:
                            # Merge recipients instead of replacing
                            current_contacts = [email.get("name", email.get("email", "")) for email in existing_draft.to_emails]
                            new_contacts = extracted_info["to_contacts"]
                            all_contacts = list(set(current_contacts + new_contacts))  # Remove duplicates
                            updates["to_contacts"] = all_contacts
                        if "subject" in extracted_info and extracted_info["subject"]:
                            updates["subject"] = extracted_info["subject"]
                        if "body" in extracted_info and extracted_info["body"]:
                            updates["body"] = extracted_info["body"]
                    
                    if updates:
                        updated_draft = draft_service.update_draft(existing_draft.draft_id, updates)
                        if updated_draft:
                            print(f"[DRAFT] Successfully updated existing draft {existing_draft.draft_id}")
                            draft_created = updated_draft  # Use updated draft as "created" for response
                        else:
                            print(f"[DRAFT] Failed to update existing draft, creating new one")
                            draft_created = draft_service.create_draft_from_detection(
                                thread_id, 
                                user_message.message_id, 
                                detection_result
                            )
                    else:
                        print(f"[DRAFT] No updates to apply to existing draft")
                        draft_created = existing_draft  # Return existing draft
                else:
                    # No existing draft found, create new one
                    try:
                        # Check if this is a reply to an anchored email
                        if anchored_item and anchored_item.get('type') == 'email':
                            print(f"[DRAFT] Detected anchored email - preparing reply context")
                            anchored_email = anchored_item.get('data', {})
                            gmail_thread_id = anchored_email.get('gmail_thread_id') or anchored_email.get('metadata', {}).get('thread_id')

                            if gmail_thread_id:
                                print(f"[DRAFT] Adding reply context: gmail_thread_id={gmail_thread_id}")

                                # Inject reply context into detection_result
                                if 'draft_data' not in detection_result:
                                    detection_result['draft_data'] = {}
                                if 'extracted_info' not in detection_result['draft_data']:
                                    detection_result['draft_data']['extracted_info'] = {}

                                # Add reply-specific fields
                                detection_result['draft_data']['extracted_info']['gmail_thread_id'] = gmail_thread_id
                                detection_result['draft_data']['extracted_info']['reply_to_email_id'] = anchored_item.get('id')

                                # Auto-populate recipients: To = original sender, CC = original recipients
                                from_email = anchored_email.get('from_email', {})
                                to_emails = anchored_email.get('to_emails', [])

                                # Set primary recipient to original sender
                                # from_email is already a dict with 'email' and 'name', use it directly as to_emails format
                                if from_email and from_email.get('email'):
                                    detection_result['draft_data']['extracted_info']['to_emails'] = [from_email]
                                    print(f"[DRAFT] Auto-populated To: {from_email}")

                                # Set CC to original recipients
                                if to_emails:
                                    detection_result['draft_data']['extracted_info']['cc_emails'] = to_emails
                                    print(f"[DRAFT] Auto-populated CC: {to_emails}")

                                print(f"[DRAFT] Reply context injected into detection_result")

                        draft_created = draft_service.create_draft_from_detection(
                            thread_id,
                            user_message.message_id,
                            detection_result
                        )
                        if not draft_created:
                            print(f"[DRAFT] ❌ Draft creation failed - create_draft_from_detection returned None")
                    except Exception as e:
                        print(f"[DRAFT] ❌ Exception during draft creation: {e}")
                        import traceback
                        print(f"[DRAFT] ❌ Draft creation traceback: {traceback.format_exc()}")
                        draft_created = None
                
                # NOW provide draft context to LLM after creation/update
                if draft_created:
                    print(f"[DRAFT] Successfully created/updated draft {draft_created.draft_id}")
                    
                    # Validate the draft to get missing fields info
                    validation_result = draft_service.validate_draft_completeness(draft_created.draft_id)
                    missing_fields = validation_result.get('missing_fields', []) if validation_result else []
                    
                    # Create draft summary
                    if draft_created.draft_type == "email":
                        to_list = [email.get("name", email.get("email", "Unknown")) for email in draft_created.to_emails] if draft_created.to_emails else ["Not specified"]
                        summary = f"Email to {', '.join(to_list[:2])}" + ("..." if len(to_list) > 2 else "")
                        if draft_created.subject:
                            summary += f" - Subject: {draft_created.subject}"
                    else:  # calendar_event
                        summary = f"Calendar event: {draft_created.summary or 'Untitled'}"
                        if draft_created.start_time:
                            summary += f" on {draft_created.start_time}"
                    
                    # Create draft context for the LLM
                    draft_context = {
                        "type": "active_draft",
                        "draft_id": draft_created.draft_id,
                        "draft_type": draft_created.draft_type,
                        "summary": summary,
                        "is_complete": len(missing_fields) == 0,
                        "missing_fields": missing_fields,
                        "created_at": draft_created.created_at.isoformat() if hasattr(draft_created.created_at, 'isoformat') else str(draft_created.created_at)
                    }
                    print(f"[DRAFT] Created context for LLM: {draft_created.draft_type}, complete: {draft_context['is_complete']}")
                    
                    # Rebuild the prompt with draft context
                    prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, raw_tool_results, anchored_item, draft_context)
                    
                    # Call LLM again with draft context
                    try:
                        print(f"[DEBUG] Calling LLM again with draft context...")
                        response = traced_main_llm_call(prompt)
                        response_text = response.content[0] if isinstance(response.content, list) else response.content
                        response_text = response_text.strip() if isinstance(response_text, str) else str(response_text)
                        print(f"[DEBUG] LLM response with draft context: {response_text[:200]}...")
                    except Exception as e:
                        print(f"[DEBUG] LLM call failed: {e}")
                        response_text = f"I've created a draft for you, but there was an error generating the response. Please check the orange anchor bar for details."
                else:
                    print(f"[DRAFT] Failed to create/update draft from detection")
                    # If draft creation failed but we detected intent, provide helpful message
                    if detection_result and detection_result.get("is_draft_intent"):
                        draft_type = detection_result.get("draft_data", {}).get("draft_type", "item")
                        friendly_type = "email" if draft_type == "email" else "calendar event"
                        response_text = f"I detected that you want to create a {friendly_type} draft, but I encountered an error during creation. Please check the logs for more details and try again."
                        print(f"[DRAFT] Setting fallback error message: {response_text}")
            else:
                print(f"[DRAFT] No draft intent detected")
                
        except Exception as e:
            print(f"[DRAFT] Error in draft detection: {e}")
            import traceback
            print(f"[DRAFT] Traceback: {traceback.format_exc()}")

        # If no draft was created, use the original response logic (skip for mail_mode)
        if (not mail_mode) and (not draft_created):
            prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, raw_tool_results, anchored_item)
            
            try:
                print(f"[DEBUG] Calling LLM with original prompt...")
                response = traced_main_llm_call(prompt)
                response_text = response.content[0] if isinstance(response.content, list) else response.content
                response_text = response_text.strip() if isinstance(response_text, str) else str(response_text)
                print(f"[DEBUG] LLM response: {response_text[:200]}...")
            except Exception as e:
                print(f"[DEBUG] LLM call failed: {e}")
                response_text = "Sorry, I couldn't process your request at this time."

        # Step 2: Save the assistant's message with the PROCESSED tool results
        print(f"\n=== Saving Assistant Message ===")
        assistant_message = Conversation(
            thread_id=thread_id,
            role='assistant',
            content=response_text,
            insight_id=insight_id,
            tool_results=assistant_tool_results, # Pass the correctly structured data
            timestamp=current_timestamp + 1
        )
        
        # Add pagination metadata if we have email results
        if raw_email_list is not None and 'pagination_data' in locals():
            assistant_message.metadata = assistant_message.metadata or {}
            
            # Debug the Gmail query storage process
            print(f"[DEBUG-APP] 🔍 Gmail Query Storage Debug:")
            print(f"[DEBUG-APP] 📝 Original user query: '{query}'")
            print(f"[DEBUG-APP] 📦 raw_tool_results type: {type(raw_tool_results)}")
            print(f"[DEBUG-APP] 🗂️ raw_tool_results is dict: {isinstance(raw_tool_results, dict)}")
            
            if isinstance(raw_tool_results, dict):
                print(f"[DEBUG-APP] 🔑 raw_tool_results keys: {list(raw_tool_results.keys())}")
                original_gmail_query = raw_tool_results.get('original_gmail_query')
                print(f"[DEBUG-APP] 🎯 Found 'original_gmail_query': {original_gmail_query}")
            else:
                original_gmail_query = None
                print(f"[DEBUG-APP] ❌ raw_tool_results is not dict, cannot extract 'original_gmail_query'")
            
            # Use the Gmail query for pagination, not the original user query
            gmail_query = original_gmail_query if original_gmail_query else query
            
            print(f"[DEBUG-APP] 📊 Final decision:")
            print(f"[DEBUG-APP] 📥 Will store query: '{gmail_query}'")
            print(f"[DEBUG-APP] 🏷️ Query source: {'original_gmail_query' if original_gmail_query else 'fallback_to_user_query'}")
            
            assistant_message.metadata.update({
                'tool_original_query_params': {'query': gmail_query, 'count': pagination_data['limit']},
                'tool_current_page_token': pagination_data['page_token'],
                'tool_next_page_token': pagination_data['next_page_token'],
                'tool_limit_per_page': pagination_data['limit'],
                'tool_total_emails_available': pagination_data['total'],
                'tool_has_more': pagination_data['has_more']
            })
            print(f"[DEBUG-APP] ✅ Stored pagination metadata with query: '{gmail_query}'")
        assistant_message.save()
        print(f"Assistant message saved. message_id: {assistant_message.message_id}, role: {assistant_message.role}, content: {assistant_message.content[:100] if assistant_message.content else 'None'}...")

        # The response_data to the client should reflect the assistant's turn
        response_data = {
            "response": response_text,
            "thread_id": thread_id,
            "message_id": assistant_message.message_id,
        }
        
        # Add draft information if a draft was created or updated
        if draft_created:
            if draft_update_result and draft_update_result.get("success"):
                # Draft was updated
                update_category = draft_update_result.get("update_category")
                updates = draft_update_result.get("updates", {})
                
                # Create appropriate message based on update type
                if update_category == "completion_finalization":
                    if updates:
                        message = f"Applied content to draft and marked as ready"
                    else:
                        message = "Draft marked as complete"
                elif update_category == "content_application":
                    message = f"Applied content from conversation to draft"
                else:
                    message = draft_update_result.get("message", "Draft updated successfully")
                
                response_data["draft_updated"] = {
                    "draft_id": draft_created.draft_id,
                    "draft_type": draft_created.draft_type,
                    "user_message_id": user_message.message_id,
                    "status": "updated",
                    "updates": updates,
                    "update_category": update_category,
                    "message": message,
                    "draft_data": convert_objectid_to_str(draft_created.to_dict())
                }
                # Flag for frontend to auto-anchor this updated draft
                response_data["auto_anchor_draft"] = True
                print(f"[DRAFT] Added updated draft data to response for auto-anchoring: {draft_created.draft_id}")
            else:
                # Draft was created - include full draft data for immediate anchoring
                response_data["draft_created"] = {
                    "draft_id": draft_created.draft_id,
                    "draft_type": draft_created.draft_type,
                    "user_message_id": user_message.message_id,
                    "status": "created",
                    "draft_data": convert_objectid_to_str(draft_created.to_dict())
                }
                # Flag for frontend to auto-anchor this draft
                response_data["auto_anchor_draft"] = True
                print(f"[DRAFT] Added draft data to response for auto-anchoring: {draft_created.draft_id}")
        
        # If we have email results, add them in the proper tile format for the frontend
        if raw_email_list is not None:
            print(f"[DEBUG] raw_email_list is not None, length: {len(raw_email_list)}")
            # Sort emails by date, newest first, before sending to frontend
            sorted_emails = sorted(raw_email_list, key=lambda e: parse_email_date(e.get('date')), reverse=True)
            
            # Create tile data for each email
            email_tiles = []
            for email in sorted_emails:
                tile_data = {
                    "id": email.get('id', email.get('email_id')),
                    "type": "email",
                    "subject": email.get('subject'),
                    "from_email": email.get('from_email'),
                    "to_emails": email.get('to_emails'),
                    "date": email.get('date'),
                    "content": email.get('content'),
                    "metadata": email.get('metadata'),
                    # Include any other email fields the frontend might need
                    **{k: v for k, v in email.items() if k not in ['id', 'subject', 'from_email', 'to_emails', 'date', 'content', 'metadata']}
                }
                email_tiles.append(tile_data)
            
            # Add both tile data and raw email data to the response
            response_data['tool_results'] = {
                'emails': sorted_emails,  # Keep the raw email data for compatibility
                'tiles': email_tiles      # Add tile data for the frontend
            }
            
            # Add pagination metadata to the response if available
            if 'pagination_data' in locals():
                response_data.update({
                    'tool_current_page_token': pagination_data['page_token'],
                    'tool_next_page_token': pagination_data['next_page_token'],
                    'tool_limit_per_page': pagination_data['limit'],
                    'tool_total_emails_available': pagination_data['total'],
                    'tool_has_more': pagination_data['has_more']
                })
                print(f"[DEBUG] Added pagination metadata to response: next_page_token={pagination_data['next_page_token']}, has_more={pagination_data['has_more']}")
            
            print(f"[DEBUG] Added {len(sorted_emails)} email objects and {len(email_tiles)} email tiles to response")
        
        # If we have calendar results, add them in the proper format for the frontend
        elif raw_tool_results and raw_tool_results.get('source_type') == 'google-calendar':
            print(f"[DEBUG] Processing calendar results for frontend")
            calendar_data = raw_tool_results.get('data', {})
            
            print(f"[DEBUG] Calendar data type: {type(calendar_data)}")
            print(f"[DEBUG] Calendar data keys: {list(calendar_data.keys()) if isinstance(calendar_data, dict) else 'Not a dict'}")
            print(f"[DEBUG] Calendar data content (first 500 chars): {str(calendar_data)[:500] if calendar_data else 'None'}")
            
            # Handle both creation and search responses for frontend
            events = []
            if calendar_data:
                if 'created_event' in calendar_data:
                    # This is a creation response - wrap the single event in a list
                    created_event = calendar_data.get('created_event', {})
                    if created_event:
                        events = [created_event]
                    print(f"[DEBUG] Processing calendar creation response for frontend with 1 created event")
                elif 'items' in calendar_data:
                    # Direct items in calendar_data
                    events = calendar_data.get('items', [])
                    print(f"[DEBUG] Processing calendar search response for frontend with {len(events)} events (direct items)")
                elif 'data' in calendar_data and isinstance(calendar_data['data'], dict) and 'items' in calendar_data['data']:
                    # Nested items in calendar_data.data.items (Composio structure)
                    events = calendar_data['data'].get('items', [])
                    print(f"[DEBUG] Processing calendar search response for frontend with {len(events)} events (nested items)")
                else:
                    # Fallback: check if calendar_data itself is an event object
                    if isinstance(calendar_data, dict) and 'id' in calendar_data:
                        events = [calendar_data]
                        print(f"[DEBUG] Processing single calendar event for frontend as fallback")
                    else:
                        print(f"[DEBUG] Calendar data structure not recognized - no 'items', 'created_event', or 'id' found")
            
            response_data['tool_results'] = {
                'calendar_events': events
            }
            print(f"[DEBUG] Added {len(events)} calendar events to response")
        
        # If we have contact results, add them in the proper format for the frontend
        elif raw_tool_results and raw_tool_results.get('source_type') == 'contact':
            print(f"[DEBUG] Processing contact results for frontend")
            # For contact queries, we let the LLM provide direct responses instead of tiles
            # contact_data = raw_tool_results.get('data', {})
            # contacts = contact_data.get('contacts', [])
            # search_term = contact_data.get('search_term', '')
            
            # Convert contacts to proper format and ensure ObjectIds are converted
            # processed_contacts = [convert_objectid_to_str(contact) for contact in contacts]
            
            # response_data['tool_results'] = {
            #     'contacts': processed_contacts,
            #     'search_term': search_term,
            #     'count': len(processed_contacts)
            # }
            print(f"[DEBUG] Contact information provided directly in LLM response - no tiles needed")
        
        else:
            print(f"[DEBUG] No email, calendar, or contact results to add to response")
            # Ensure tool_results is present, even if empty, if a tool was called.
            response_data['tool_results'] = assistant_message.tool_results if assistant_message.tool_results else None
            print(f"[DEBUG] Using assistant_message.tool_results: {assistant_message.tool_results}")

        # End Langfuse conversation tracing
        try:
            if conversation_langfuse and conversation_langfuse.is_enabled() and conversation_span:
                # Determine tool results for tracing
                tool_results_for_trace = None
                if 'tool_results' in response_data and response_data['tool_results']:
                    tool_results_for_trace = response_data['tool_results']
                elif assistant_tool_results:
                    tool_results_for_trace = assistant_tool_results
                
                # Determine draft info for tracing
                draft_info_for_trace = None
                if 'draft_created' in response_data:
                    draft_info_for_trace = response_data['draft_created']
                elif draft_created:
                    draft_info_for_trace = {
                        "draft_id": getattr(draft_created, 'draft_id', None),
                        "draft_type": getattr(draft_created, 'draft_type', None),
                        "status": "created"
                    }
                
                # End span with output data
                conversation_span.end(
                    output={
                        "response": response_text,
                        "tool_results": tool_results_for_trace,
                        "draft_created": draft_info_for_trace
                    }
                )
                
                # Flush traces to ensure they're sent
                conversation_langfuse.flush()
                print(f"[LANGFUSE] Ended conversation span and flushed")
        except Exception as e:
            print(f"[LANGFUSE] Warning: Failed to end conversation span: {e}")

        print(f"\n=== Sending Response ===")
        print(f"Response data: {json.dumps(response_data, indent=2)[:1000]}")
        return jsonify(response_data)
    except Exception as e:
        print(f"\n=== Error in chat endpoint ===")
        print(f"Error: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        error_message = "The AI service is currently experiencing high load. Please try again in a few moments."
        if "overloaded_error" in str(e):
            return jsonify({"error": error_message}), 503
        return jsonify({"error": str(e)}), 500

@app.route('/threads', methods=['GET'])
def get_threads():
    threads = Thread.get_all()
    formatted_threads = []
    
    for thread in threads:
        formatted_threads.append({
            "thread_id": thread["thread_id"],
            "title": thread["title"],
            "updated_at": thread["updated_at"]
        })
    
    return jsonify({"threads": formatted_threads})

@app.route('/threads/<thread_id>/rename', methods=['PUT'])
def rename_thread(thread_id):
    try:
        data = request.get_json()
        new_title = data.get('title')
        
        if not new_title:
            return jsonify({"error": "No title provided"}), 400
        
        Thread.update_title(thread_id, new_title)
        return jsonify({"success": True, "thread_id": thread_id, "title": new_title})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat/<thread_id>', methods=['GET'])
def get_thread(thread_id):
    print(f"\n=== Get Thread Request ===")
    print(f"Fetching thread with ID: {thread_id}")
    try:
        thread_doc = Thread.get_by_id(thread_id)
        if not thread_doc:
            print(f"[ERROR] Thread not found: {thread_id}")
            return jsonify({"error": "Thread not found"}), 404
        conversations_collection = get_collection(CONVERSATIONS_COLLECTION)
        raw_message_docs = list(conversations_collection.find({'thread_id': thread_id}).sort('timestamp', 1))
        emails_collection = get_collection(EMAILS_COLLECTION)
        processed_messages_for_response = []
        
        for msg_doc in raw_message_docs:
            # Convert the entire message document to handle any ObjectId fields
            processed_msg_doc = convert_objectid_to_str(msg_doc)
            
            # Ensure processed_msg_doc is a dictionary
            if not isinstance(processed_msg_doc, dict):
                print(f"[WARNING] Skipping non-dict message: {type(processed_msg_doc)}")
                continue
            
            message_data_for_response = {
                "role": processed_msg_doc.get("role"),
                "content": processed_msg_doc.get("content"),
                "query": processed_msg_doc.get("query") if not processed_msg_doc.get("role") else None,
                "response": processed_msg_doc.get("response") if not processed_msg_doc.get("role") else None,
                "message_id": processed_msg_doc.get("message_id"),
                "timestamp": processed_msg_doc.get("timestamp") 
            }
            
            # Add pagination fields for assistant messages (check both root level and metadata)
            if processed_msg_doc.get('role') == 'assistant':
                metadata = processed_msg_doc.get('metadata', {})
                
                # Check root level first, then metadata
                for field in ['tool_original_query_params', 'tool_current_page_token', 'tool_next_page_token', 'tool_limit_per_page', 'tool_total_emails_available', 'tool_has_more']:
                    if field in processed_msg_doc:
                        message_data_for_response[field] = processed_msg_doc[field]
                    elif field in metadata:
                        message_data_for_response[field] = metadata[field]
            
            if processed_msg_doc.get('role') == 'assistant' and 'tool_results' in processed_msg_doc:
                tool_results = processed_msg_doc['tool_results']
                if isinstance(tool_results, dict) and 'emails' in tool_results:
                    email_ids = tool_results['emails']
                    if isinstance(email_ids, list):
                        fetched_email_docs = list(emails_collection.find({'email_id': {'$in': email_ids}})) if email_ids else []
                        
                        # Sort emails by date, newest first
                        fetched_email_docs.sort(key=lambda e: parse_email_date(e.get('date')), reverse=True)

                        # Convert all email documents to handle any ObjectId fields
                        processed_emails = [convert_objectid_to_str(email_doc) for email_doc in fetched_email_docs]
                        
                        # Create tile data for each email for the frontend
                        email_tiles = []
                        for email in processed_emails:
                            if isinstance(email, dict):
                                tile_data = {
                                    "id": email.get('email_id', email.get('_id')),
                                    "type": "email",
                                    "subject": email.get('subject'),
                                    "from_email": email.get('from_email'),
                                    "to_emails": email.get('to_emails'),
                                    "date": email.get('date'),
                                    "content": email.get('content'),
                                    "metadata": email.get('metadata'),
                                    # Include any other email fields the frontend might need
                                    **{k: v for k, v in email.items() if k not in ['email_id', '_id', 'subject', 'from_email', 'to_emails', 'date', 'content', 'metadata']}
                                }
                                email_tiles.append(tile_data)
                        
                        # Create a copy to avoid modifying the original dict in a loop
                        tool_results_copy = tool_results.copy()
                        tool_results_copy['emails'] = processed_emails
                        tool_results_copy['tiles'] = email_tiles  # Add tile data for the frontend
                        message_data_for_response['tool_results'] = tool_results_copy
                
                # Handle calendar events in tool_results
                elif isinstance(tool_results, dict) and 'calendar_events' in tool_results:
                    calendar_events = tool_results['calendar_events']
                    if isinstance(calendar_events, list):
                        # Calendar events are already stored as full objects, so just pass them through
                        tool_results_copy = tool_results.copy()
                        message_data_for_response['tool_results'] = tool_results_copy
                        print(f"[DEBUG] Added {len(calendar_events)} calendar events to thread response")
                
                # Handle other tool results or empty tool results
                else:
                    message_data_for_response['tool_results'] = tool_results
            processed_messages_for_response.append(message_data_for_response)
            
        return jsonify(processed_messages_for_response)
    except Exception as e:
        print(f"[ERROR] Exception in get_thread: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500

@app.route('/save_insight', methods=['POST'])
def save_insight():
    data = request.get_json()
    user_input = data.get('content')
    if not user_input:
        return jsonify({"error": "No content provided"}), 400
    
    # Generate embedding and save to Pinecone
    embedding = get_embeddings().embed_query(user_input)
    insight_id = f"insight_{uuid.uuid4()}"
    
    # Save to the saved_insights namespace in the personal index
    get_pinecone_index().upsert(
        vectors=[(insight_id, embedding, {
            "text": user_input, 
            "source": "user",
            "insight_id": insight_id,
            "timestamp": datetime.now().isoformat()
        })],
        namespace="saved_insights"
    )
    
    # Save to MongoDB
    insight = Insight(
        content=user_input,
        source="user",
        vector_id=insight_id
    )
    insight.save()
    
    return jsonify({
        "message": "User insight saved successfully", 
        "insight_id": insight_id
    })

@app.route('/delete_email', methods=['POST', 'OPTIONS'])
def delete_email():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        print(f"Received delete request with data: {data}")
        message_id = data.get('message_id')
        email_id = data.get('email_id')
        thread_id = data.get('thread_id')
        if not email_id or not thread_id:
            print(f"Missing required parameters. email_id: {email_id}, thread_id: {thread_id}")
            return jsonify({'success': False, 'error': 'Missing required parameters: email_id and thread_id are required'}), 400
        if not tooling_service:
            print("Tooling service not initialized")
            return jsonify({'success': False, 'error': 'Tooling service not initialized'}), 500
        query = {'thread_id': thread_id}
        if message_id:
            query['message_id'] = message_id
        print(f"Finding conversation with query: {query}")
        conversation = Conversation.find_one(query)
        if not conversation:
            print(f"Conversation not found with initial query. Trying broader query...")
            conversation = Conversation.find_one({'thread_id': thread_id})
        if not conversation:
            print(f"Conversation not found for thread_id: {thread_id}")
            return jsonify({'success': False, 'error': 'Conversation not found'}), 404
        if not conversation.get('tool_results') or not conversation.get('tool_results').get('emails'):
            print(f"No emails found in conversation")
            return jsonify({'success': False, 'error': 'No emails found in conversation'}), 404
        email_ids = conversation.get('tool_results').get('emails', [])
        if email_id not in email_ids:
            print(f"Email with ID {email_id} not found in conversation")
            return jsonify({'success': False, 'error': 'Email not found in conversation'}), 404
        delete_success = tooling_service.delete_email(email_id)
        print(f"Gmail deletion result: {delete_success}")
        if not delete_success:
            print(f"Failed to delete email from Gmail: {email_id}")
        try:
            update_result = Conversation.update_one(
                {'_id': conversation['_id']},
                {'$pull': {'tool_results.emails': email_id}}
            )
            update_success = update_result.modified_count > 0
            db_message = "Database updated successfully" if update_success else "No changes made to database"
            if not update_success:
                print(f"No updates made to MongoDB for email: {email_id}")
            print(f"Successfully processed email {email_id} from conversation {message_id}")
            return jsonify({'success': True, 'message': f'Email processed: Gmail deletion {"succeeded" if delete_success else "failed"}, {db_message}', 'deleted_email_id': email_id, 'gmail_success': delete_success, 'db_success': update_success})
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return jsonify({'success': False, 'error': f'Database error: {str(db_error)}'}), 500
    except Exception as e:
        print(f"Error in delete_email endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/delete_calendar_event', methods=['POST', 'OPTIONS'])
def delete_calendar_event():
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        data = request.get_json()
        print(f"Received delete calendar event request with data: {data}")
        
        message_id = data.get('message_id')  # The conversation message ID
        event_id = data.get('event_id')      # The calendar event ID
        thread_id = data.get('thread_id')
        
        if not event_id or not thread_id:
            print(f"Missing required parameters. event_id: {event_id}, thread_id: {thread_id}")
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: event_id and thread_id are required'
            }), 400
        
        # Check if Tooling service is initialized
        if not tooling_service:
            print("Tooling service not initialized")
            return jsonify({
                'success': False,
                'error': 'Tooling service not initialized'
            }), 500
            
        # Find the conversation - first try with all parameters
        query = {'thread_id': thread_id}
        
        # If message_id is provided, add it to the query
        if message_id:
            query['message_id'] = message_id
        
        print(f"Finding conversation with query: {query}")
        conversation = Conversation.find_one(query)
        
        if not conversation:
            print(f"Conversation not found with initial query. Trying broader query...")
            # Try just with thread_id
            conversation = Conversation.find_one({'thread_id': thread_id})
        
        if not conversation:
            print(f"Conversation not found for thread_id: {thread_id}")
            return jsonify({
                'success': False,
                'error': 'Conversation not found'
            }), 404
            
        # Check if the conversation has tool_results with calendar events
        if not conversation.get('tool_results') or not conversation.get('tool_results').get('calendar_events'):
            print(f"No calendar events found in conversation")
            return jsonify({
                'success': False,
                'error': 'No calendar events found in conversation'
            }), 404
        
        # Look for the event in tool_results.calendar_events
        events = conversation.get('tool_results').get('calendar_events', [])
        print(f"Found {len(events)} events in conversation")
        
        # Debug: Print event IDs
        event_ids = [e.get('id') for e in events]
        print(f"Event IDs in conversation: {event_ids}")
            
        # Find the event with the matching ID
        matching_event = next((e for e in events if e.get('id') == event_id), None)
        
        if not matching_event:
            print(f"Event with ID {event_id} not found in conversation")
            return jsonify({
                'success': False,
                'error': 'Event not found in conversation'
            }), 404
            
        # Delete from Google Calendar using Tooling service
        print(f"🔴 [DELETE] Attempting to delete event {event_id} from Google Calendar...")
        print(f"🔴 [DELETE] Event details: {matching_event}")
        delete_success = tooling_service.delete_calendar_event(event_id)
        print(f"🔴 [DELETE] Google Calendar deletion result: {delete_success}")
        
        if not delete_success:
            print(f"Failed to delete event from Google Calendar: {event_id}")
            # Continue anyway to update MongoDB
            
        # Update MongoDB to remove the event
        try:
            update_result = Conversation.update_one(
                {'_id': conversation['_id']},
                {'$pull': {'tool_results.calendar_events': {'id': event_id}}}
            )
            
            update_success = update_result.modified_count > 0
            db_message = "Database updated successfully" if update_success else "No changes made to database"
            
            if not update_success:
                print(f"No updates made to MongoDB for event: {event_id}")
                # This could be because the event was already removed
            
            print(f"Successfully processed event {event_id} from conversation {message_id}")
            return jsonify({
                'success': True,
                'message': f'Event processed: Google Calendar deletion {"succeeded" if delete_success else "failed"}, {db_message}',
                'deleted_event_id': event_id,
                'calendar_success': delete_success,
                'db_success': update_success
            })
            
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
            
    except Exception as e:
        print(f"Error in delete_calendar_event endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/bulk_delete_items', methods=['POST', 'OPTIONS'])
def bulk_delete_items():
    if request.method == 'OPTIONS':
        print("[/bulk_delete_items] OPTIONS request received")
        return '', 200

    try:
        data = request.get_json()
        print(f"[/bulk_delete_items] Received bulk delete request. Data: {json.dumps(data)}")

        message_id = data.get('message_id')  # Assistant's message ID from the ToolResults block
        thread_id = data.get('thread_id')    # Current chat thread_id
        items_to_process = data.get('items', []) # List of {item_id, item_type}

        if not all([message_id, thread_id, items_to_process]):
            error_msg = "Missing required parameters: message_id, thread_id, and items are required"
            print(f"[/bulk_delete_items] Error: {error_msg}. Provided: message_id={message_id}, thread_id={thread_id}, items_count={len(items_to_process)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        if not tooling_service:
            error_msg = "Tooling service not initialized"
            print(f"[/bulk_delete_items] Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 500

        # Find the specific conversation document for this assistant message
        # The message_id here is the ID of the assistant's message in the conversation
        conversation_query = {'message_id': message_id, 'thread_id': thread_id}
        print(f"[/bulk_delete_items] Querying for conversation with: {conversation_query}")
        conversation_doc = Conversation.find_one(conversation_query)

        if not conversation_doc:
            error_msg = f"Conversation not found for message_id: {message_id} and thread_id: {thread_id}"
            print(f"[/bulk_delete_items] Error: {error_msg}")
            # As a fallback, try to find the latest assistant message in the thread if direct message_id match fails
            # This might be useful if message_id propagation has issues, but can be risky.
            # For now, strict matching is safer.
            # alternative_conversations = Conversation.get_by_thread_id(thread_id)
            # if alternative_conversations:
            #    assistant_messages = [m for m in alternative_conversations if m.get('role') == 'assistant' and m.get('tool_results')]
            #    if assistant_messages:
            #        conversation_doc = assistant_messages[-1] # Get the last one
            #        print(f"[/bulk_delete_items] Fallback: Found conversation by thread_id, using last assistant message: {conversation_doc.get('message_id')}")
            # if not conversation_doc: # if still not found
            return jsonify({'success': False, 'error': error_msg}), 404
        
        print(f"[/bulk_delete_items] Found conversation with _id: {conversation_doc.get('_id')} and message_id: {conversation_doc.get('message_id')}")

        if not conversation_doc.get('tool_results'):
            error_msg = f"No tool_results found in conversation {conversation_doc.get('message_id')}"
            print(f"[/bulk_delete_items] Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404

        processed_results = []
        email_ids_to_pull_from_db = []
        event_ids_to_pull_from_db = []

        current_emails_in_db = conversation_doc.get('tool_results', {}).get('emails', [])
        current_events_in_db = conversation_doc.get('tool_results', {}).get('calendar_events', [])

        print(f"[/bulk_delete_items] Initial emails in DB for this message: {len(current_emails_in_db)}")
        print(f"[/bulk_delete_items] Initial events in DB for this message: {len(current_events_in_db)}")

        for item_data in items_to_process:
            item_id = item_data.get('item_id')
            item_type = item_data.get('item_type')
            deletion_successful_tooling = False
            item_error_message = None

            print(f"[/bulk_delete_items] Processing item: id={item_id}, type={item_type}")

            if not item_id or not item_type:
                item_error_message = 'Missing item_id or item_type in item_data'
                print(f"[/bulk_delete_items] Skipping item due to error: {item_error_message}. Data: {item_data}")
                processed_results.append({'item_id': item_id, 'item_type': item_type, 'deleted': False, 'error': item_error_message})
                continue

            try:
                item_exists_in_conversation_results = False
                # Initialize deletion_successful_tooling, as it might not be set if item_type is unknown
                deletion_successful_tooling = False 

                if item_type == 'email':
                    item_exists_in_conversation_results = any(e == item_id for e in current_emails_in_db)
                    if item_exists_in_conversation_results:
                        print(f"[/bulk_delete_items] Attempting Tooling delete for email: {item_id}")
                        try:
                            # Actual tooling_service.delete_email returns a boolean
                            deletion_successful_tooling = tooling_service.delete_email(item_id)
                            
                            if deletion_successful_tooling:
                                print(f"[/bulk_delete_items] Tooling delete SUCCESS for email: {item_id}")
                                email_ids_to_pull_from_db.append(item_id)
                            else:
                                item_error_message = f"Tooling call to delete email {item_id} returned False. This could be due to the item not being found on the Tooling side or another issue."
                                print(f"[/bulk_delete_items] Tooling delete FAILED for email: {item_id}. {item_error_message}")
                                # If Tooling internally logs "not found" and returns False,
                                # we might still want to remove it from our DB if that's the desired behavior.
                                # For now, we only add to email_ids_to_pull_from_db if Tooling confirmed deletion (returned True).
                        except Exception as delete_err:
                            deletion_successful_tooling = False 
                            item_error_message = f"Exception during Tooling API call for email {item_id}: {str(delete_err)}"
                            print(f"[/bulk_delete_items] {item_error_message}")
                            import traceback # Ensure traceback is imported here if not globally
                            print(traceback.format_exc())
                    else:
                        item_error_message = f"Email {item_id} not found in this conversation message's Tool results. Skipping Tooling call."
                        print(f"[/bulk_delete_items] {item_error_message}")
                        deletion_successful_tooling = False
                        
                elif item_type == 'event':
                    item_exists_in_conversation_results = any(e.get('id') == item_id for e in current_events_in_db)
                    if item_exists_in_conversation_results:
                        print(f"[/bulk_delete_items] Attempting Tooling delete for event: {item_id}")
                        try:
                            # Actual tooling_service.delete_calendar_event returns a boolean
                            deletion_successful_tooling = tooling_service.delete_calendar_event(item_id)

                            if deletion_successful_tooling:
                                print(f"[/bulk_delete_items] Tooling delete SUCCESS for event: {item_id}")
                                event_ids_to_pull_from_db.append(item_id)
                            else:
                                item_error_message = f"Tooling call to delete event {item_id} returned False. This could be due to the item not being found on the Tooling side or another issue."
                                print(f"[/bulk_delete_items] Tooling delete FAILED for event: {item_id}. {item_error_message}")
                        except Exception as delete_err:
                            deletion_successful_tooling = False
                            item_error_message = f"Exception during Tooling API call for event {item_id}: {str(delete_err)}"
                            print(f"[/bulk_delete_items] {item_error_message}")
                            import traceback # Ensure traceback is imported here if not globally
                            print(traceback.format_exc())
                    else:
                        item_error_message = f"Event {item_id} not found in this conversation message's Tool results. Skipping Tooling call."
                        print(f"[/bulk_delete_items] {item_error_message}")
                        deletion_successful_tooling = False
                else:
                    item_error_message = f"Unknown item_type: {item_type}"
                    print(f"[/bulk_delete_items] {item_error_message}")
                    deletion_successful_tooling = False

            except Exception as e: # This is the outer try-except for the item processing logic
                deletion_successful_tooling = False 
                item_error_message = f"Outer exception processing item {item_type} {item_id}: {str(e)}"
                print(f"[/bulk_delete_items] {item_error_message}")
                import traceback # Ensure traceback is imported here if not globally
                print(traceback.format_exc())
            
            # This processed_results.append call should be outside the 'try...except e:' block above,
            # but still inside the 'for item_data in items_to_process:' loop.
            processed_results.append({
                'item_id': item_id, 
                'item_type': item_type, 
                'deleted': deletion_successful_tooling, 
                'error': item_error_message
            })

        # Update MongoDB to remove items that were successfully deleted from Tooling OR reported as not_found by Tooling
        db_modified_count = 0
        if email_ids_to_pull_from_db or event_ids_to_pull_from_db:
            mongo_update_operations = {}
            if email_ids_to_pull_from_db:
                mongo_update_operations['$pull'] = {
                    'tool_results.emails': {'$in': email_ids_to_pull_from_db}
                }
                print(f"[/bulk_delete_items] Preparing to pull emails from DB: {email_ids_to_pull_from_db}")
            
            if event_ids_to_pull_from_db:
                event_pull_op = {'tool_results.calendar_events': {'id': {'$in': event_ids_to_pull_from_db}}}
                if '$pull' in mongo_update_operations:
                    # Merge the pull operations
                    mongo_update_operations['$pull'] = {**mongo_update_operations['$pull'], **event_pull_op}
                else:
                    mongo_update_operations['$pull'] = event_pull_op
                print(f"[/bulk_delete_items] Preparing to pull events from DB: {event_ids_to_pull_from_db}")

            if mongo_update_operations:
                try:
                    print(f"[/bulk_delete_items] Executing MongoDB update on conversation _id {conversation_doc['_id']} with operations: {json.dumps(mongo_update_operations)}")
                    update_result = Conversation.update_one(
                        {'_id': conversation_doc['_id']}, 
                        mongo_update_operations
                    )
                    db_modified_count = update_result.modified_count
                    if db_modified_count > 0:
                        print(f"[/bulk_delete_items] MongoDB update successful. Modified count: {db_modified_count}")
                    else:
                        print(f"[/bulk_delete_items] MongoDB update executed, but no documents were modified. This might be okay if items were already removed or IDs didn't match perfectly for a $pull that expected them.")
                    # Remove emails from the emails collection as well
                    from config.mongo_config import EMAILS_COLLECTION
                    from utils.mongo_client import get_collection
                    emails_collection = get_collection(EMAILS_COLLECTION)
                    delete_result = emails_collection.delete_many({'email_id': {'$in': email_ids_to_pull_from_db}})
                    print(f"[/bulk_delete_items] Deleted {delete_result.deleted_count} emails from emails collection.")
                except Exception as db_e:
                    db_error_msg = f"Database error during bulk update: {str(db_e)}"
                    print(f"[/bulk_delete_items] {db_error_msg}")
                    # This error should be logged, but the overall success for items is based on Tooling deletion primarily.
                    # We might want to reflect this DB error in the individual item results if critical.
        else:
            print("[/bulk_delete_items] No items successfully deleted from Tooling, so no MongoDB update needed.")

        print(f"[/bulk_delete_items] Final processed results: {json.dumps(processed_results)}")
        return jsonify({
            'success': True, # Indicates the endpoint processed the request as a whole
            'results': processed_results, # Detailed status for each item based on Tooling deletion
            'db_items_removed_count': db_modified_count # How many items were intended to be pulled from DB based on Tooling success
        })

    except Exception as e:
        final_error_msg = f"Unexpected error in /bulk_delete_items endpoint: {str(e)}"
        print(f"[/bulk_delete_items] {final_error_msg}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': final_error_msg}), 500

@app.route('/threads/<thread_id>/delete', methods=['DELETE'])
def delete_thread(thread_id):
    try:
        success = Thread.delete(thread_id)
        if success:
            return jsonify({"success": True, "message": "Thread and conversations deleted successfully"})
        else:
            return jsonify({"error": "Thread not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/load_more_emails', methods=['POST', 'OPTIONS'])
def load_more_emails():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        thread_id = data.get('thread_id')
        assistant_message_id = data.get('assistant_message_id')
        print(f"\n=== Load More Emails Request ===")
        print(f"Thread ID: {thread_id}, Assistant Message ID: {assistant_message_id}")
        if not thread_id or not assistant_message_id:
            print("[ERROR] Missing thread_id or assistant_message_id")
            return jsonify({"error": "Missing thread_id or assistant_message_id"}), 400
        assistant_message_doc = Conversation.find_one({
            'thread_id': thread_id, 
            'message_id': assistant_message_id,
            'role': 'assistant'
        })
        if not assistant_message_doc:
            print(f"[ERROR] Assistant message not found for ID: {assistant_message_id} in thread: {thread_id}")
            return jsonify({"error": "Assistant message not found"}), 404
        print(f"[DEBUG] Found assistant message: {assistant_message_doc.get('_id')}")
        # Check both root level and metadata for pagination fields
        metadata = assistant_message_doc.get('metadata', {})
        original_params = assistant_message_doc.get('tool_original_query_params') or metadata.get('tool_original_query_params')
        next_page_token = assistant_message_doc.get('tool_next_page_token') or metadata.get('tool_next_page_token')
        limit_per_page = assistant_message_doc.get('tool_limit_per_page') or metadata.get('tool_limit_per_page')
        total_emails_available = assistant_message_doc.get('tool_total_emails_available') or metadata.get('tool_total_emails_available')
        
        print(f"[DEBUG] Stored pagination: next_page_token={next_page_token}, limit={limit_per_page}, total={total_emails_available}, original_params={original_params}")
        if original_params is None or limit_per_page is None or total_emails_available is None:
            print("[ERROR] Missing one or more pagination parameters in the stored message.")
            return jsonify({"new_emails": [], "has_more": False, "message": "Pagination parameters missing in stored message."}), 400
        
        if not next_page_token:
            print("[INFO] No more emails to load - no next page token available.")
            return jsonify({"new_emails": [], "has_more": False, "message": "No more emails to load."}), 200
        if not tooling_service:
            print("[ERROR] Composio service not initialized for /load_more_emails")
            return jsonify({"error": "Composio service not available"}), 500
        # Extract original Gmail query from stored params for pagination
        # Gmail page tokens do NOT preserve query context - we must include the original query
        print(f"[DEBUG-LOAD-MORE] 🔍 Gmail Query Extraction Debug:")
        print(f"[DEBUG-LOAD-MORE] 📦 original_params type: {type(original_params)}")
        print(f"[DEBUG-LOAD-MORE] 🗂️ original_params is dict: {isinstance(original_params, dict)}")
        
        if isinstance(original_params, dict):
            print(f"[DEBUG-LOAD-MORE] 🔑 original_params keys: {list(original_params.keys())}")
            print(f"[DEBUG-LOAD-MORE] 📊 original_params content: {original_params}")
        
        original_query = None
        if original_params and isinstance(original_params, dict):
            # The stored query should be the processed Gmail query, not the user's natural language
            original_query = original_params.get('query')
            print(f"[DEBUG-LOAD-MORE] 🎯 Extracted stored query: '{original_query}'")
        else:
            print(f"[DEBUG-LOAD-MORE] ❌ Cannot extract query - invalid original_params structure")

        fetch_params_for_composio = {
            "count": limit_per_page,
            "page_token": next_page_token
        }
        
        # Include original Gmail query for pagination if available (critical for filter preservation)
        if original_query:
            fetch_params_for_composio["query"] = original_query
            print(f"[DEBUG] Including original Gmail query in pagination: {original_query}")
        
        print(f"[DEBUG] Calling Composio with params (including query): {fetch_params_for_composio}")
        tooling_response = tooling_service.get_recent_emails_with_thread_expansion(**fetch_params_for_composio)

        # Debug logging with safe JSON serialization (handles MagicMock in tests)
        try:
            print(f"[DEBUG] Composio response for /load_more_emails: {json.dumps(tooling_response)[:500]}")
        except TypeError as e:
            # Handle MagicMock objects in tests that aren't JSON serializable
            print(f"[DEBUG] Composio response for /load_more_emails (non-JSON): {str(tooling_response)[:500]}")
            print(f"[DEBUG] JSON serialization skipped due to: {str(e)}")
        if "error" in tooling_response or not tooling_response.get("data"):
            error_msg = tooling_response.get('error') or "No data returned from Composio"
            print(f"[ERROR] Composio error: {error_msg}")
            return jsonify({"error": f"Failed to load more emails: {error_msg}"}), 500
        new_data = tooling_response.get("data", {})
        if new_data is None:
            new_data = {}
        
        # Extract new pagination info from response
        new_next_page_token = tooling_response.get('next_page_token')
        new_total_available = tooling_response.get('total_estimate', total_emails_available)
        
        # Handle different response formats from Composio
        if isinstance(new_data, dict) and "messages" in new_data:
            # Nested format: {"data": {"messages": {"messages": [...]}}}
            messages_container = new_data.get("messages", {})
            if isinstance(messages_container, dict) and "messages" in messages_container:
                new_emails = messages_container.get("messages", [])
            else:
                new_emails = messages_container if isinstance(messages_container, list) else []
        else:
            # Direct format: {"data": [...]}
            new_emails = new_data if isinstance(new_data, list) else []
            
        print(f"[DEBUG] Extracted new_emails: {len(new_emails)} emails, first email type: {type(new_emails[0]) if new_emails else 'N/A'}")
        print(f"[DEBUG] Composio returned: {len(new_emails)} emails, new_next_page_token={new_next_page_token}, new_total={new_total_available}")
        # Insert new emails into emails collection and collect their IDs
        emails_collection = get_collection(EMAILS_COLLECTION)
        new_email_ids = []
        for email in new_emails:
            # Handle both formats: Composio returns 'messageId', but we expect 'id'
            email_id = email.get('messageId') or email.get('id')
            if email_id:
                # Transform the email data to match the schema
                # Handle Composio format - extract subject, sender, date from the raw format
                subject = email.get('subject', f"Email {email_id[:8]}")
                sender_raw = email.get('sender', '')
                date_timestamp = email.get('messageTimestamp', '')
                
                # Parse sender information like in the main chat function
                from_email = {'email': 'unknown@unknown.com', 'name': 'Unknown Sender'}
                if sender_raw:
                    import re
                    email_match = re.search(r'<([^>]+)>', sender_raw)
                    name_match = re.search(r'"([^"]+)"', sender_raw)
                    
                    if email_match:
                        email_addr = email_match.group(1)
                        name = name_match.group(1) if name_match else email_addr.split('@')[0]
                        from_email = {'email': email_addr, 'name': name}
                    elif '@' in sender_raw:
                        from_email = {'email': sender_raw.strip(), 'name': sender_raw.split('@')[0]}
                
                # Extract Gmail thread ID from Composio response
                gmail_thread_id = email.get('thread_id') or email.get('threadId', '')
                
                formatted_email = {
                    'email_id': email_id.strip(),
                    'thread_id': thread_id,
                    'gmail_thread_id': gmail_thread_id,  # Add Gmail thread ID
                    'subject': subject[:1000],  # Truncate subject if too long
                    'from_email': from_email,
                    'date': date_timestamp or '',
                    'content': {
                        'html': "",  # Empty until user requests summarization
                        'text': ""   # Empty until user requests summarization
                    },
                    'metadata': {
                        'source': 'TOOL',
                        'folder': email.get('folder', 'INBOX'),
                        'is_read': email.get('is_read', False),
                        'size': email.get('size'),
                        'thread_id': gmail_thread_id  # Also store in metadata for backward compatibility
                    },
                    'attachments': email.get('attachments', [])[:10],  # Limit attachments
                    'cc': email.get('cc', [])[:50],  # Limit CC recipients
                    'bcc': email.get('bcc', [])[:50],  # Limit BCC recipients
                    'reply_to': email.get('reply_to'),
                    'to_emails': [
                        {
                            'email': 'unknown@unknown.com',
                            'name': 'Unknown Recipient'
                        }
                    ],  # Simplified for now, can be enhanced later
                    'created_at': int(time.time()),
                    'updated_at': int(time.time())
                }
                
                try:
                    # Use email_id as the unique identifier for upsert
                    emails_collection.update_one(
                        {'email_id': formatted_email['email_id']},
                        {'$set': formatted_email},
                        upsert=True
                    )
                    new_email_ids.append(email_id)
                except Exception as e:
                    print(f"Error saving email {email_id}: {str(e)}")
                    print(f"Problematic email data: {json.dumps(formatted_email)[:1000]}")
                    raise e
        # Update the Conversation document in MongoDB
        update_operations = {
            '$push': {'tool_results.emails': {'$each': new_email_ids}},
            '$set': {
                'tool_next_page_token': new_next_page_token,
                'tool_total_emails_available': new_total_available
            }
        }
        update_result = Conversation.update_one(
            {'message_id': assistant_message_id, 'thread_id': thread_id},
            update_operations
        )
        print(f"[DEBUG] MongoDB update result: matched={update_result.matched_count}, modified={update_result.modified_count}")
        has_more_after_this_load = (new_next_page_token is not None)
        # Fetch full email objects for response
        full_new_emails = list(emails_collection.find({'email_id': {'$in': new_email_ids}})) if new_email_ids else []

        # Sort the newly fetched emails by date, newest first
        full_new_emails.sort(key=lambda e: parse_email_date(e.get('date')), reverse=True)
        print(f"[DEBUG] Sorted {len(full_new_emails)} new email(s) by date.")

        response_payload = {
            "new_emails": [convert_objectid_to_str(e) for e in full_new_emails],
            "current_page_token": next_page_token,
            "next_page_token": new_next_page_token,
            "limit_per_page": limit_per_page,
            "total_emails_available": new_total_available,
            "has_more": has_more_after_this_load
        }
        print(f"[DEBUG] Response for /load_more_emails: {json.dumps(response_payload)[:500]}")
        return jsonify(response_payload)
    except Exception as e:
        print(f"[ERROR] Unexpected error in /load_more_emails: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return jsonify({"error": "An unexpected error occurred"}), 500

# New endpoint for summarizing a single email
@app.route('/summarize_single_email', methods=['POST', 'OPTIONS'])
def summarize_single_email():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        thread_id = data.get('thread_id')
        assistant_message_id = data.get('assistant_message_id')
        email_content_full = data.get('email_content_full')
        email_content_truncated = data.get('email_content_truncated')
        
        if email_id:
            email_id = email_id.strip()

        if not email_id or not thread_id or not assistant_message_id:
            return jsonify({'error': 'Missing required parameters'}), 400
            
        conversation = Conversation.find_one({
            'thread_id': thread_id,
            'message_id': assistant_message_id
        })
        
        # Note: Email content is now properly stored in the content field via get_email_content endpoint
        # No need to update the email document here as it's already handled
        
        # 3. Generate summary using LLM
        prompt = email_summarization_prompt(email_content_truncated)
        current_llm_for_summary = get_llm()
        if get_gemini_llm():
            current_llm_for_summary = get_gemini_llm()
            print("[INFO] Using Gemini Pro for summarization.")
        else:
            print("[INFO] Gemini Pro not available, using default LLM (Claude) for summarization.")
            
        try:
            response = current_llm_for_summary.invoke(prompt)
            summary = response.content[0] if isinstance(response.content, list) else response.content
            summary = summary.strip() if isinstance(summary, str) else str(summary)
            print(f"[INFO] Generated summary for email_id: {email_id} using {type(current_llm_for_summary).__name__}")
        except Exception as e:
            error_message = str(e)
            if "rate_limit_error" in error_message.lower() or "429" in error_message:
                print(f"[ERROR] Rate limit error during summarization with {type(current_llm_for_summary).__name__}: {error_message}")
                return jsonify({
                    "success": False,
                    "error": f"Summarization service is busy (rate limit). Please try again in a moment."
                }), 429
            else:
                print(f"[ERROR] Error generating summary with {type(current_llm_for_summary).__name__}: {error_message}")
                import traceback
                print(traceback.format_exc())
                return jsonify({
                    "success": False,
                    "error": "Failed to generate summary. Please try again."
                }), 500
                
        # 4. Create a new conversation entry for the summary
        summary_message = Conversation(
            thread_id=thread_id,
            role='assistant',
            content=summary,
            tool_results={'email_summary': {'email_id': email_id}}
        )
        summary_message.save()
        print(f"[INFO] Created new conversation entry for summary with message_id: {summary_message.message_id}")
        
        # 5. Return the response in the same format as the chat endpoint
        response_data = {
            "success": True,
            "response": summary,
            "thread_id": thread_id,
            "message_id": summary_message.message_id,
            "tool_results": {'email_summary': {'email_id': email_id}}
        }
        return jsonify(response_data), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in summarize_single_email: {str(e)}")
        return jsonify({'error': str(e)}), 500

# New endpoint for getting email content
@app.route('/get_email_content', methods=['POST', 'OPTIONS'])
def get_email_content():
    if request.method == 'OPTIONS':
        return '', 200
    try:
        data = request.get_json()
        email_id = data.get('email_id')
        
        if email_id:
            email_id = email_id.strip()

        if not email_id:
            return jsonify({'error': 'Missing email_id parameter'}), 400
            
        # Check if email content already exists in database
        emails_collection = get_collection(EMAILS_COLLECTION)
        email_doc = emails_collection.find_one({'email_id': email_id})
        
        # Check if we have substantial content already (either HTML or text with significant length)
        existing_content = email_doc.get('content', {}) if email_doc else {}
        has_html = existing_content.get('html', '').strip()
        has_substantial_text = len(existing_content.get('text', '').strip()) > 100  # More than just snippet
        
        if email_doc and (has_html or has_substantial_text):
            # Content already exists and is substantial, return it
            print(f"[DEBUG] get_email_content - Using existing content for {email_id}")
            return jsonify({
                'success': True,
                'email_id': email_id,
                'content': existing_content
            }), 200
        
        # Content doesn't exist or is insufficient, fetch it from Tooling
        if not tooling_service:
            return jsonify({'error': 'Tooling service not available'}), 500
        
        print(f"[DEBUG] get_email_content - Fetching full content for {email_id} from Composio")
        # Get full email content from Tooling
        email_content = tooling_service.get_email_details(email_id)
        
        if not email_content:
            print(f"[DEBUG] get_email_content - No content retrieved from Composio for {email_id}")
            # If we have an email in DB but failed to get full content, use existing content as fallback
            if email_doc and existing_content.get('text'):
                print(f"[DEBUG] get_email_content - Using existing DB content as fallback for {email_id}")
                return jsonify({
                    'success': True,
                    'email_id': email_id,
                    'content': existing_content
                }), 200
            return jsonify({'error': 'Could not retrieve email content'}), 404
        
        # Process the content to extract HTML and convert to markdown
        html_content = ""
        text_content = ""
        
        # If it's HTML content, convert to markdown
        if email_content.startswith('<'):
            html_content = email_content
            # Convert HTML to markdown using html2text
            try:
                import html2text
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.ignore_images = False
                h.body_width = 0  # Don't wrap text
                text_content = h.handle(html_content)
            except ImportError:
                # Fallback to simple HTML stripping if html2text is not available
                import re
                text_content = re.sub('<[^<]+?>', '', email_content)
                text_content = re.sub(r'\s+', ' ', text_content).strip()
        else:
            text_content = email_content
            # Create simple HTML wrapper for text content
            html_content = f"<html><body><pre>{email_content}</pre></body></html>"
        # Ensure text_content is always a string
        if text_content is None:
            text_content = ""
        
        # Update the email document in database with the content
        # If email doesn't exist in DB, we need to handle that case
        if email_doc:
            update_result = emails_collection.update_one(
                {'email_id': email_id},
                {
                    '$set': {
                        'content.html': html_content,
                        'content.text': text_content,
                        'updated_at': int(time.time())
                    }
                }
            )
            
            if update_result.modified_count == 0 and update_result.matched_count == 0:
                print(f"[DEBUG] get_email_content - Email {email_id} not found in DB for update")
                # Email doesn't exist in DB, we can still return the content for summarization
        else:
            print(f"[DEBUG] get_email_content - Email {email_id} not in DB, returning content without saving")
        
        return jsonify({
            'success': True,
            'email_id': email_id,
            'content': {
                'html': html_content,
                'text': text_content
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in get_email_content: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/emails/threads', methods=['GET'])
def get_email_threads():
    """Get grouped email threads"""
    try:
        limit = request.args.get('limit', 50, type=int)
        
        # Get grouped threads from Email model
        result = Email.get_gmail_threads_grouped(limit=limit)
        
        return jsonify({
            'success': True,
            'data': result
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in get_email_threads: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/emails/thread/<gmail_thread_id>', methods=['GET'])
def get_email_thread(gmail_thread_id):
    """Get specific email thread by Gmail thread ID"""
    try:
        # Get emails in the thread
        emails = Email.get_by_gmail_thread_id(gmail_thread_id)
        
        if not emails:
            return jsonify({
                'success': False,
                'error': 'Thread not found'
            }), 404
        
        # Convert ObjectId to string for JSON serialization
        serializable_emails = []
        for email in emails:
            email_dict = email.copy()
            if '_id' in email_dict:
                email_dict['_id'] = str(email_dict['_id'])
            serializable_emails.append(email_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'gmail_thread_id': gmail_thread_id,
                'email_count': len(serializable_emails),
                'emails': serializable_emails
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in get_email_thread: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/emails/thread/<gmail_thread_id>/full', methods=['GET'])
def get_full_email_thread(gmail_thread_id):
    """Get full email thread with processed content"""
    try:
        # Get emails in the thread
        emails = Email.get_by_gmail_thread_id(gmail_thread_id)
        
        if not emails:
            return jsonify({
                'success': False,
                'error': 'Thread not found'
            }), 404
        
        # Process each email to get full content
        processed_emails = []
        for email in emails:
            email_dict = email.copy()
            
            # Get the full content for this email using the existing get_email_content endpoint logic
            try:
                # Use the tooling service to get full email content
                if tooling_service:
                    email_content = tooling_service.get_email_details(email_dict.get('email_id'))
                    if email_content:
                        # Process the content to extract HTML and convert to text
                        html_content = ""
                        text_content = ""
                        
                        # If it's HTML content, convert to markdown
                        if email_content.startswith('<'):
                            html_content = email_content
                            # Convert HTML to markdown using html2text
                            try:
                                import html2text
                                h = html2text.HTML2Text()
                                h.ignore_links = False
                                h.ignore_images = False
                                h.body_width = 0  # Don't wrap text
                                text_content = h.handle(html_content)
                            except ImportError:
                                # Fallback to simple HTML stripping if html2text is not available
                                import re
                                text_content = re.sub('<[^<]+?>', '', email_content)
                                text_content = re.sub(r'\s+', ' ', text_content).strip()
                        else:
                            text_content = email_content
                            # Create simple HTML wrapper for text content
                            html_content = f"<html><body><pre>{email_content}</pre></body></html>"
                        
                        # Ensure text_content is always a string
                        if text_content is None:
                            text_content = ""
                        
                        email_dict['content'] = {
                            'html': html_content,
                            'text': text_content
                        }
                    else:
                        # Fallback to existing content if available
                        email_dict['content'] = {
                            'html': email_dict.get('content', {}).get('html', ''),
                            'text': email_dict.get('content', {}).get('text', '')
                        }
                else:
                    # No tooling service, use existing content
                    email_dict['content'] = {
                        'html': email_dict.get('content', {}).get('html', ''),
                        'text': email_dict.get('content', {}).get('text', '')
                    }
            except Exception as e:
                print(f"[ERROR] Failed to process content for email {email_dict.get('email_id')}: {str(e)}")
                # Use existing content as fallback
                email_dict['content'] = {
                    'html': email_dict.get('content', {}).get('html', ''),
                    'text': email_dict.get('content', {}).get('text', '')
                }
            
            processed_emails.append(email_dict)
        
        # Sort emails by date (oldest first - chronological order)
        processed_emails.sort(key=lambda x: x.get('date', ''), reverse=False)
        
        # Convert ObjectId to string for JSON serialization
        serializable_emails = []
        for email in processed_emails:
            email_dict = email.copy()
            if '_id' in email_dict:
                email_dict['_id'] = str(email_dict['_id'])
            serializable_emails.append(email_dict)
        
        return jsonify({
            'success': True,
            'data': {
                'gmail_thread_id': gmail_thread_id,
                'email_count': len(serializable_emails),
                'emails': serializable_emails
            }
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Exception in get_full_email_thread: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/test_pagination', methods=['POST'])
def test_pagination():
    """
    Test endpoint to compare different Gmail pagination approaches.
    """
    try:
        data = request.get_json()
        query = data.get('query', '')
        count = data.get('count', 5)
        
        print(f"[DEBUG] Testing pagination approaches with query: '{query}', count: {count}")
        
        # Initialize Composio service
        composio_service = ComposioService()
        
        # Run the test
        test_results = composio_service.test_pagination_approaches(query=query, count=count)
        
        return jsonify({
            "success": True,
            "test_results": test_results,
            "message": "Pagination test completed. Check server logs for detailed output."
        })
        
    except Exception as e:
        print(f"[ERROR] Test pagination error: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# ===========================================
# CONTACT MANAGEMENT ENDPOINTS  
# ===========================================

@app.route('/contacts/sync', methods=['POST', 'OPTIONS'])
def sync_contacts():
    """Sync contacts from Gmail"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        data = request.get_json() or {}
        full_sync = data.get('full_sync', True)
        
        result = contact_service.sync_gmail_contacts(full_sync=full_sync)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Contact sync completed successfully',
                'sync_id': result['sync_id'],
                'stats': result['stats']
            })
        else:
            return jsonify({
                'success': False,
                'error': result['error'],
                'sync_id': result['sync_id']
            }), 500
            
    except Exception as e:
        print(f"[ERROR] Contact sync error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts', methods=['GET'])
def get_contacts():
    """Get all contacts with pagination"""
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        
        contacts = contact_service.get_all_contacts(limit=limit, offset=offset)
        stats = contact_service.get_contact_stats()
        
        return jsonify({
            'success': True,
            'contacts': convert_objectid_to_str(contacts),
            'pagination': {
                'limit': limit,
                'offset': offset,
                'total': stats.get('total_contacts', 0)
            },
            'stats': stats
        })
        
    except Exception as e:
        print(f"[ERROR] Get contacts error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts/search', methods=['POST', 'OPTIONS'])
def search_contacts():
    """Search contacts by name or email"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        limit = data.get('limit', 20)
        
        if not query:
            return jsonify({'error': 'Search query is required'}), 400
        
        results = contact_service.search_contacts(query, limit)
        
        return jsonify({
            'success': True,
            'query': query,
            'contacts': convert_objectid_to_str(results),
            'count': len(results)
        })
        
    except Exception as e:
        print(f"[ERROR] Search contacts error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts/sync/status', methods=['GET'])
def get_sync_status():
    """Get status of contact sync operations"""
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        sync_id = request.args.get('sync_id')
        
        if sync_id:
            status = contact_service.get_sync_status(sync_id)
        else:
            status = contact_service.get_sync_status()
        
        if 'error' in status:
            return jsonify({'success': False, 'error': status['error']}), 404
        
        return jsonify({
            'success': True,
            'sync_status': convert_objectid_to_str(status)
        })
        
    except Exception as e:
        print(f"[ERROR] Get sync status error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts/sync/history', methods=['GET'])
def get_sync_history():
    """Get history of contact sync operations"""
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        limit = int(request.args.get('limit', 10))
        
        history = contact_service.get_sync_history(limit)
        
        return jsonify({
            'success': True,
            'sync_history': convert_objectid_to_str(history),
            'count': len(history)
        })
        
    except Exception as e:
        print(f"[ERROR] Get sync history error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts/stats', methods=['GET'])
def get_contact_stats():
    """Get contact statistics"""
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        stats = contact_service.get_contact_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        print(f"[ERROR] Get contact stats error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/contacts/cleanup', methods=['POST', 'OPTIONS'])
def cleanup_contact_logs():
    """Clean up old contact sync logs"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        data = request.get_json() or {}
        days_to_keep = data.get('days_to_keep', 30)
        
        deleted_count = contact_service.cleanup_old_sync_logs(days_to_keep)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up {deleted_count} old sync logs',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        print(f"[ERROR] Cleanup contact logs error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Test/Debug endpoints (remove in production)
@app.route('/contacts/debug/delete_all', methods=['POST', 'OPTIONS'])
def debug_delete_all_contacts():
    """Delete all contacts - DEBUG ONLY"""
    if request.method == 'OPTIONS':
        return '', 200
    
    if not contact_service:
        return jsonify({'error': 'Contact service not available'}), 500
    
    try:
        deleted_count = contact_service.delete_all_contacts()
        
        return jsonify({
            'success': True,
            'message': f'Deleted {deleted_count} contacts',
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        print(f"[ERROR] Debug delete all contacts error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ===========================================
# DRAFT MANAGEMENT ENDPOINTS  
# ===========================================

@app.route('/drafts', methods=['POST', 'OPTIONS'])
def create_draft():
    """Create a new draft"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        draft_type = data.get('draft_type')
        thread_id = data.get('thread_id')
        message_id = data.get('message_id')
        initial_data = data.get('initial_data', {})
        
        if not all([draft_type, thread_id, message_id]):
            return jsonify({'error': 'Missing required parameters: draft_type, thread_id, message_id'}), 400
        
        if draft_type not in ['email', 'calendar_event']:
            return jsonify({'error': 'draft_type must be "email" or "calendar_event"'}), 400
        
        # Initialize draft service
        draft_service = DraftService()
        
        # Create draft
        draft = draft_service.create_draft(draft_type, thread_id, message_id, initial_data)
        
        return jsonify({
            'success': True,
            'draft': convert_objectid_to_str(draft.to_dict()),
            'message': f'Created {draft_type} draft successfully'
        }), 201
        
    except Exception as e:
        print(f"[ERROR] Create draft error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>', methods=['GET'])
def get_draft(draft_id):
    """Get a draft by its ID"""
    try:
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        draft = draft_service.get_draft_by_id(draft_id)
        
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        
        return jsonify({
            'success': True,
            'draft': convert_objectid_to_str(draft.to_dict())
        })
        
    except Exception as e:
        print(f"[ERROR] Get draft error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>', methods=['PUT', 'OPTIONS'])
def update_draft(draft_id):
    """Update a draft"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        updates = data.get('updates', {})
        
        if not updates:
            return jsonify({'error': 'No updates provided'}), 400
        
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        success = draft_service.update_draft(draft_id, updates)
        
        if not success:
            return jsonify({'error': 'Failed to update draft or draft not found'}), 404
        
        # Get updated draft
        updated_draft = draft_service.get_draft_by_id(draft_id)
        
        return jsonify({
            'success': True,
            'draft': convert_objectid_to_str(updated_draft.to_dict()),
            'message': 'Draft updated successfully'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"[ERROR] Update draft error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>/validate', methods=['GET'])
def validate_draft(draft_id):
    """Check if draft has all required fields for execution"""
    try:
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        validation = draft_service.validate_draft_completeness(draft_id)
        
        return jsonify({
            'success': True,
            'validation': validation
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        print(f"[ERROR] Validate draft error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>/send', methods=['POST', 'OPTIONS'])
def send_draft(draft_id):
    """Execute draft via Composio (send email or create calendar event)"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        # Validate completeness first
        validation = draft_service.validate_draft_completeness(draft_id)
        if not validation['is_complete']:
            return jsonify({
                'success': False,
                'error': f'Draft is incomplete. Missing fields: {validation["missing_fields"]}'
            }), 400
        
        # Get draft details
        draft = draft_service.get_draft_by_id(draft_id)
        if not draft:
            return jsonify({'error': 'Draft not found'}), 404
        
        # Convert to Composio parameters
        composio_params = draft_service.convert_draft_to_composio_params(draft_id)
        
        # Execute via Composio
        if not tooling_service:
            return jsonify({'error': 'Composio service not available'}), 500
        
        try:
            if draft.draft_type == 'email':
                # Check if this is a reply to a thread
                if composio_params.get('gmail_thread_id'):
                    print(f"[DRAFT] Detected reply draft for thread: {composio_params['gmail_thread_id']}")

                    # Use reply_to_thread for thread replies
                    result = tooling_service.reply_to_thread(
                        thread_id=composio_params['gmail_thread_id'],
                        recipient_email=composio_params['to_emails'][0] if composio_params['to_emails'] else None,
                        message_body=composio_params.get('body'),
                        cc_emails=composio_params.get('cc_emails'),
                        bcc_emails=composio_params.get('bcc_emails')
                    )
                else:
                    # Send new email via Composio
                    print(f"[DRAFT] Sending new email (no thread context)")
                    result = tooling_service.send_email(
                        to_emails=composio_params['to_emails'],
                        subject=composio_params.get('subject'),
                        body=composio_params.get('body'),
                        cc_emails=composio_params.get('cc_emails'),
                        bcc_emails=composio_params.get('bcc_emails')
                    )
                
            elif draft.draft_type == 'calendar_event':
                # Create calendar event via Composio
                result = tooling_service.create_calendar_event(
                    summary=composio_params['summary'],
                    start_time=composio_params['start_time'],
                    end_time=composio_params['end_time'],
                    location=composio_params.get('location'),
                    description=composio_params.get('description'),
                    attendees=composio_params.get('attendees', [])
                )
            else:
                return jsonify({'error': f'Unknown draft type: {draft.draft_type}'}), 400
            
            # Check result and update draft status
            if not result.get('success', True) or 'error' in result:
                # Mark draft as error
                error_msg = result.get('error', 'Unknown error')
                draft_service.close_draft(draft_id, 'composio_error')
                return jsonify({
                    'success': False,
                    'error': f'Composio execution failed: {error_msg}'
                }), 500
            else:
                # Mark draft as completed
                draft_service.close_draft(draft_id, 'closed')
                success_msg = result.get('message', f'{draft.draft_type.replace("_", " ").title()} executed successfully')
                return jsonify({
                    'success': True,
                    'result': result,
                    'message': success_msg
                })
                
        except Exception as composio_error:
            # Mark draft as error
            draft_service.close_draft(draft_id, 'composio_error')
            raise composio_error
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"[ERROR] Send draft error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>/close', methods=['POST', 'OPTIONS'])
def close_draft(draft_id):
    """Close a draft with specified status"""
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        status = data.get('status', 'closed')
        
        if status not in ['closed', 'composio_error']:
            return jsonify({'error': 'Status must be "closed" or "composio_error"'}), 400
        
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        success = draft_service.close_draft(draft_id, status)
        
        if not success:
            return jsonify({'error': 'Failed to close draft or draft not found'}), 404
        
        return jsonify({
            'success': True,
            'message': f'Draft closed with status: {status}'
        })
        
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 404
    except Exception as e:
        print(f"[ERROR] Close draft error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/thread/<thread_id>', methods=['GET'])
def get_drafts_by_thread(thread_id):
    """Get all drafts for a thread"""
    try:
        active_only = request.args.get('active_only', 'false').lower() == 'true'
        
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        if active_only:
            drafts = draft_service.get_active_drafts_by_thread(thread_id)
        else:
            drafts = draft_service.get_all_drafts_by_thread(thread_id)
        
        return jsonify({
            'success': True,
            'drafts': [convert_objectid_to_str(draft.to_dict()) for draft in drafts],
            'count': len(drafts)
        })
        
    except Exception as e:
        print(f"[ERROR] Get drafts by thread error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/message/<message_id>', methods=['GET'])
def get_draft_by_message(message_id):
    """Get draft by the message ID that created it"""
    try:
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        draft = draft_service.get_draft_by_message_id(message_id)
        
        if not draft:
            return jsonify({'error': 'No draft found for this message'}), 404
        
        return jsonify({
            'success': True,
            'draft': convert_objectid_to_str(draft.to_dict())
        })
        
    except Exception as e:
        print(f"[ERROR] Get draft by message error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/drafts/<draft_id>/summary', methods=['GET'])
def get_draft_summary(draft_id):
    """Get a human-readable summary of a draft for UI display"""
    try:
        from services.draft_service import DraftService
        draft_service = DraftService()
        
        summary = draft_service.get_draft_summary(draft_id)
        
        if not summary:
            return jsonify({'error': 'Draft not found'}), 404
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        print(f"[ERROR] Get draft summary error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for Docker"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'pm-copilot-backend'
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
