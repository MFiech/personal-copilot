from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from dotenv import load_dotenv
import os
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

pc = Pinecone(api_key=pinecone_api_key)
index_name = "personal"  # Changed from "alohacamp" to "personal"
index = pc.Index(index_name)

# Initialize embeddings with text-embedding-3-large
embeddings = OpenAIEmbeddings(model="text-embedding-3-large", api_key=SecretStr(openai_api_key) if openai_api_key else None)

# Set up a single vectorstore with the saved_insights namespace
vectorstore = PineconeVectorStore(
    index=index, 
    embedding=embeddings, 
    text_key="text", 
    namespace="saved_insights",  # Changed to use saved_insights namespace
    pinecone_api_key=pinecone_api_key
)

# Initialize the LLM (Claude for general chat)
llm = ChatAnthropic(model="claude-3-7-sonnet-latest", anthropic_api_key=anthropic_api_key)

# Initialize Gemini Pro LLM for Summarization
gemini_llm = None
if google_api_key:
    try:
        gemini_llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-lite",
            google_api_key=google_api_key,
            convert_system_message_to_human=True
        )
        print("Gemini (gemini-2.0-flash-lite) LLM for summarization initialized successfully.")
    except Exception as e:
        print(f"Warning: Failed to initialize Gemini LLM: {e}. Summarization might fall back or fail.")
else:
    print("Warning: GOOGLE_API_KEY not found. Summarization will use the default LLM (Claude) or fail if it's unavailable.")

# Initialize conversation memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Initialize the QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(),
    return_source_documents=True
)

def convert_objectid_to_str(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid_to_str(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid_to_str(item) for item in obj]
    return obj

def build_prompt(query, retrieved_docs, thread_history=None, tool_context=None):
    print("=== BUILD_PROMPT FUNCTION CALLED ===")
    prompt_parts = []
    insight_id = None

    # Debug logging
    print(f"[DEBUG] build_prompt called with:")
    print(f"  - query: {query}")
    # print(f"  - tool_context: {json.dumps(tool_context, indent=2) if tool_context else 'None'}")
    print(f"  - retrieved_docs count: {len(retrieved_docs) if retrieved_docs else 0}")

    # Add current date and time
    current_time = datetime.now()
    prompt_parts.append(f"Current date and time: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
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

1. If calendar events are found, ONLY respond with: "Here are your calendar events:"
2. If no calendar events are found, respond with: "I couldn't find any calendar events matching your query."
3. Do not list or describe any events - they will be shown as tiles.
4. Do not add any other text or explanations.

For non-email and non-calendar queries, provide a helpful response based on the retrieved context when available. If no relevant context is found, provide a helpful response based on your knowledge.""")
    
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
                events = tool_context.get("data", {}).get("events", [])
                total_events = len(events)
                prompt_parts.append(f"Calendar data available: {total_events} events found")
                print(f"[DEBUG] Added to prompt: Calendar data available: {total_events} events found")
                print(f"[DEBUG] events type: {type(events)}")
                print(f"[DEBUG] events content: {json.dumps(events, indent=2)[:500] if events else 'None'}")
                print(f"[DEBUG] events truthy check: {bool(events)}")
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
        print(f"\n=== New Chat Request ===")
        print(f"Query: {query}")
        print(f"Thread ID: {thread_id}")
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

        # Initialize variables for tooling results
        raw_tool_results = None
        assistant_tool_results = None
        raw_email_list = None

        if tooling_service:
            print(f"[DEBUG] Tooling service is available, starting processing...")
            try:
                print("\n=== Processing Tooling Query ===")
                print(f"Using Tooling service: {type(tooling_service).__name__}")
                print(f"[DEBUG] About to call tooling_service.process_query...")
                raw_tool_results = tooling_service.process_query(query, thread_history)
                print(f"[DEBUG] tooling_service.process_query completed successfully")
                print(f"[DEBUG] Raw data from service assigned to raw_tool_results: {json.dumps(raw_tool_results, indent=2)[:1000]}")
                print(f"[DEBUG] raw_tool_results type: {type(raw_tool_results)}")
                print(f"[DEBUG] raw_tool_results keys: {list(raw_tool_results.keys()) if isinstance(raw_tool_results, dict) else 'N/A'}")
                print(f"[DEBUG] raw_tool_results source_type: {raw_tool_results.get('source_type') if isinstance(raw_tool_results, dict) else 'N/A'}")
                print(f"[DEBUG] raw_tool_results truthy check: {bool(raw_tool_results)}")
                
                tool_output = raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}

                # Check if the results are emails and transform them into the structure our Conversation model expects.
                if tool_output and tool_output.get("messages"):
                    print(f"[DEBUG] Processing mail results from tool_output...")
                    messages_data = tool_output.get("messages")
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
                                
                                # Create Email model instance
                                email_doc = Email(
                                    email_id=email_id,
                                    thread_id=thread_id,
                                    subject=subject,
                                    from_email=from_email,
                                    to_emails=to_emails,
                                    date=date_header,
                                    content=content,
                                    metadata={
                                        'source': 'COMPOSIO',
                                        'label_ids': label_ids,
                                        'attachment_count': len(attachment_list),
                                        'thread_id': composio_email.get('threadId', ''),
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
                    events = calendar_data.get('items', []) if calendar_data else []
                    
                    # For calendar events, we store the full event objects (not just IDs like emails)
                    assistant_tool_results = {
                        "source_type": "google-calendar", 
                        "calendar_events": events
                    }
                    print(f"[DEBUG] Processed {len(events)} calendar events for conversation storage")
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
            events = calendar_data.get('items', []) if calendar_data else []
            tool_context = {
                'source_type': 'google-calendar',
                'data': {
                    'events': events,
                    'total_events': len(events)
                }
            }
        elif raw_tool_results and raw_tool_results.get('source_type') not in ['mail', 'google-calendar']:
            # For other tool results, use the original structure but preserve source_type
            tool_context = {
                'source_type': raw_tool_results.get('source_type'),
                'data': raw_tool_results.get('data', {}) if isinstance(raw_tool_results, dict) else {}
            }
        
        # Get relevant documents using the retriever
        try:
            result = qa_chain.invoke({"query": query})
            retrieved_docs = result["source_documents"]
        except Exception as e:
            print(f"Error in QA chain: {str(e)}")
            retrieved_docs = []
        
        prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, tool_context)
        
        try:
            print(f"[DEBUG] Calling LLM with prompt...")
            response = llm.invoke(prompt)
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
            # Use the Gmail query for pagination, not the original user query
            gmail_query = raw_tool_results.get('original_gmail_query', query) if raw_tool_results else query
            assistant_message.metadata.update({
                'tool_original_query_params': {'query': gmail_query, 'count': pagination_data['limit']},
                'tool_current_page_token': pagination_data['page_token'],
                'tool_next_page_token': pagination_data['next_page_token'],
                'tool_limit_per_page': pagination_data['limit'],
                'tool_total_emails_available': pagination_data['total'],
                'tool_has_more': pagination_data['has_more']
            })
            print(f"[DEBUG] Added pagination metadata to assistant message: {pagination_data}")
        assistant_message.save()
        print(f"Assistant message saved. message_id: {assistant_message.message_id}, role: {assistant_message.role}, content: {assistant_message.content[:100] if assistant_message.content else 'None'}...")

        # The response_data to the client should reflect the assistant's turn
        response_data = {
            "response": response_text,
            "thread_id": thread_id,
            "message_id": assistant_message.message_id,
        }
        
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
            events = calendar_data.get('items', []) if calendar_data else []
            
            response_data['tool_results'] = {
                'calendar_events': events
            }
            print(f"[DEBUG] Added {len(events)} calendar events to response")
        else:
            print(f"[DEBUG] No email or calendar results to add to response")
            # Ensure tool_results is present, even if empty, if a tool was called.
            response_data['tool_results'] = assistant_message.tool_results if assistant_message.tool_results else None
            print(f"[DEBUG] Using assistant_message.tool_results: {assistant_message.tool_results}")

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
    embedding = embeddings.embed_query(user_input)
    insight_id = f"insight_{uuid.uuid4()}"
    
    # Save to the saved_insights namespace in the personal index
    index.upsert(
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
        delete_success = tooling_service.delete_calendar_event(event_id)
        print(f"Google Calendar deletion result: {delete_success}")
        
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
        # For Gmail native tokens, we only need count and page_token
        # No query modification needed - Gmail token contains all context
        fetch_params_for_composio = {
            "count": limit_per_page,
            "page_token": next_page_token
        }
        
        print(f"[DEBUG] Using Gmail native token - calling Composio with: {fetch_params_for_composio}")
        tooling_response = tooling_service.get_recent_emails(**fetch_params_for_composio)

        print(f"[DEBUG] Composio response for /load_more_emails: {json.dumps(tooling_response)[:500]}")
        if "error" in tooling_response:
            print(f"[ERROR] Composio error: {tooling_response.get('error')}")
            return jsonify({"error": f"Composio error: {tooling_response.get('error')}"}), 500
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
                
                formatted_email = {
                    'email_id': email_id.strip(),
                    'thread_id': thread_id,
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
                        'size': email.get('size')
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
        current_llm_for_summary = llm
        if gemini_llm:
            current_llm_for_summary = gemini_llm
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)
