from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import os
import json
from datetime import datetime
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain.chains import RetrievalQA
from langchain.memory import ConversationBufferMemory
from pinecone import Pinecone
import anthropic
import uuid
from services.veyrax_service import VeyraXService
from services.mock_veyrax_service import MockVeyraXService
import re
import time
import requests
from models.conversation import Conversation
from models.insight import Insight
from utils.mongo_client import get_db, get_collection
from config.mongo_config import init_collections, CONVERSATIONS_COLLECTION
from models.thread import Thread

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
veyrax_api_key = os.getenv("VEYRAX_API_KEY")

if not all([pinecone_api_key, openai_api_key, anthropic_api_key]):
    raise ValueError("One or more required API keys are missing from .env")

# Initialize MongoDB
db = get_db()
init_collections(db)

# Initialize VeyraX service (if API key is available)
veyrax_service = None
USE_MOCK_VEYRAX = False  # Keep using the real VeyraX service

if USE_MOCK_VEYRAX:
    veyrax_service = MockVeyraXService(api_key=veyrax_api_key)
    print("Using mock VeyraX service")
elif veyrax_api_key:
    try:
        veyrax_service = VeyraXService(api_key=veyrax_api_key)
        # Test the connection
        if veyrax_service.check_auth():
            print("VeyraX service initialized and authenticated successfully")
        else:
            print("Warning: VeyraX service initialized but authentication failed")
            USE_MOCK_VEYRAX = True
            veyrax_service = MockVeyraXService(api_key=veyrax_api_key)
            print("Falling back to mock service")
    except Exception as e:
        print(f"Warning: Failed to initialize VeyraX service: {e}")
        print("Falling back to mock service")
        USE_MOCK_VEYRAX = True
        veyrax_service = MockVeyraXService(api_key=veyrax_api_key)
else:
    print("Warning: No VeyraX API key found. Using mock service.")
    USE_MOCK_VEYRAX = True
    veyrax_service = MockVeyraXService(api_key=None)

pc = Pinecone(api_key=pinecone_api_key)
index_name = "personal"  # Changed from "alohacamp" to "personal"
index = pc.Index(index_name)

# Initialize embeddings with text-embedding-3-large
embeddings = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key=openai_api_key)

# Set up a single vectorstore with the saved_insights namespace
vectorstore = PineconeVectorStore(
    index=index, 
    embedding=embeddings, 
    text_key="text", 
    namespace="saved_insights",  # Changed to use saved_insights namespace
    pinecone_api_key=pinecone_api_key
)

# Initialize the LLM
llm = ChatAnthropic(model="claude-3-7-sonnet-20250219", anthropic_api_key=anthropic_api_key)

# Initialize conversation memory
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

# Initialize the QA chain
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(),
    return_source_documents=True
)

def build_prompt(query, retrieved_docs, thread_history=None, veyrax_context=None):
    prompt_parts = []
    insight_id = None

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
    
    # Add VeyraX context if provided
    if veyrax_context:
        prompt_parts.append("\nExternal Data Sources:")
        if "source_type" in veyrax_context:
            if veyrax_context["source_type"] == "mail" or veyrax_context["source_type"] == "gmail":
                messages = veyrax_context.get("data", {}).get("messages", [])
                prompt_parts.append(f"Email data available: {len(messages)} messages found")
            elif veyrax_context["source_type"] == "google-calendar":
                prompt_parts.append("Calendar data available")
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
    
    return "\n\n".join(prompt_parts), insight_id

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
        veyra_results = None
        veyra_context = None
        veyra_pagination = {}
        if veyrax_service:
            try:
                print("\n=== Processing VeyraX Query ===")
                print(f"Using VeyraX service: {type(veyrax_service).__name__}")
                veyrax_data = veyrax_service.process_query(query, thread_history)
                print(f"[DEBUG] Raw veyrax_data from service: {json.dumps(veyrax_data, indent=2)[:1000]}")
                if veyrax_data:
                    source_type = veyrax_data.get("source_type", "")
                    print(f"VeyraX source type: {source_type}")
                    if source_type in ["mail", "gmail"]:
                        data = veyrax_data.get("data", {})
                        messages = data.get("messages", [])
                        print(f"VeyraX messages found: {len(messages) if messages else 0}")
                        if messages:
                            veyra_results = {"emails": messages}
                            veyra_context = veyrax_data
                            # Extract pagination info
                            veyra_pagination = {
                                "veyra_original_query_params": data.get("original_query_params"),
                                "veyra_current_offset": data.get("offset_used"),
                                "veyra_limit_per_page": data.get("limit_used"),
                                "veyra_total_emails_available": data.get("total_available"),
                                "veyra_has_more": (data.get("offset_used", 0) + data.get("limit_used", 10)) < data.get("total_available", 0)
                            }
                            print(f"[DEBUG] VeyraX pagination info: {veyra_pagination}")
                    elif source_type == "google-calendar":
                        events = veyrax_data.get("data", {}).get("events", [])
                        print(f"VeyraX calendar events found: {len(events) if events else 0}")
                        if events:
                            veyra_results = {"calendar_events": events}
                            veyra_context = veyrax_data
                print(f"[DEBUG] veyra_results after processing veyrax_data: {json.dumps(veyra_results, indent=2)[:1000]}")
            except Exception as e:
                print(f"Error processing VeyraX data: {str(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print("VeyraX service not initialized")
        # Get relevant documents using the retriever
        try:
            result = qa_chain.invoke({"query": query})
            retrieved_docs = result["source_documents"]
        except Exception as e:
            print(f"Error in QA chain: {str(e)}")
            retrieved_docs = []
        prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, veyra_context)
        try:
            response = llm.invoke(prompt)
            response_text = response.content.strip()
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
            content=query
        )
        user_message.save()
        print(f"User message saved. message_id: {user_message.message_id}, role: {user_message.role}, content: {user_message.content[:100]}...")
        # Step 2: Save the assistant's message (with Veyra results and pagination)
        print(f"\n=== Saving Assistant Message ===")
        assistant_message = Conversation(
            thread_id=thread_id,
            role='assistant',
            content=response_text,
            insight_id=insight_id,
            veyra_results=veyra_results,
            veyra_original_query_params=veyra_pagination.get("veyra_original_query_params"),
            veyra_current_offset=veyra_pagination.get("veyra_current_offset"),
            veyra_limit_per_page=veyra_pagination.get("veyra_limit_per_page"),
            veyra_total_emails_available=veyra_pagination.get("veyra_total_emails_available"),
            veyra_has_more=veyra_pagination.get("veyra_has_more")
        )
        assistant_message_attributes_for_saving = {
            "thread_id": assistant_message.thread_id,
            "message_id": assistant_message.message_id,
            "role": assistant_message.role,
            "content_for_db": assistant_message.content,
            "insight_id": assistant_message.insight_id,
            "veyra_results": assistant_message.veyra_results,
            "veyra_original_query_params": assistant_message.veyra_original_query_params,
            "veyra_current_offset": assistant_message.veyra_current_offset,
            "veyra_limit_per_page": assistant_message.veyra_limit_per_page,
            "veyra_total_emails_available": assistant_message.veyra_total_emails_available,
            "veyra_has_more": assistant_message.veyra_has_more,
            "timestamp": assistant_message.timestamp
        }
        print(f"[DEBUG] Assistant Conversation object attributes/related data BEFORE save: {json.dumps(assistant_message_attributes_for_saving, indent=2, default=str)}")
        assistant_message.save()
        print(f"Assistant message saved. message_id: {assistant_message.message_id}, role: {assistant_message.role}, content: {assistant_message.content[:100]}..., veyra_results: {json.dumps(assistant_message.veyra_results, indent=2)[:1000]}")
        # The response_data to the client should reflect the assistant's turn
        response_data = {
            "response": response_text,
            "thread_id": thread_id,
            "message_id": assistant_message.message_id,
            "veyra_results": veyra_results
        }
        # Add pagination info to response if present
        if veyra_pagination:
            response_data.update(veyra_pagination)
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

        # Correctly fetch the MongoDB collection
        conversations_collection = get_collection(CONVERSATIONS_COLLECTION)
        raw_message_docs = list(conversations_collection.find({'thread_id': thread_id}).sort('timestamp', 1))
        
        processed_messages_for_response = []
        for msg_doc in raw_message_docs: # msg_doc is a raw document from MongoDB
            
            message_data_for_response = {
                "role": msg_doc.get("role"),
                "content": msg_doc.get("content"),
                "query": msg_doc.get("query") if not msg_doc.get("role") else None, # For backward compatibility
                "response": msg_doc.get("response") if not msg_doc.get("role") else None, # For backward compatibility
                "veyra_results": msg_doc.get("veyra_results"),
                "message_id": msg_doc.get("message_id"),
                "timestamp": msg_doc.get("timestamp") 
            }

            # --- Start Veyra Results & Pagination Logic for Assistant Messages ---
            if msg_doc.get('role') == 'assistant' and msg_doc.get('veyra_results'):
                message_data_for_response['veyra_results'] = msg_doc.get('veyra_results')
                
                original_params = msg_doc.get('veyra_original_query_params')
                current_offset = msg_doc.get('veyra_current_offset')
                limit_per_page = msg_doc.get('veyra_limit_per_page')
                total_available = msg_doc.get('veyra_total_emails_available')
                has_more = msg_doc.get('veyra_has_more')

                if original_params is not None:
                    message_data_for_response['veyra_original_query_params'] = original_params
                if current_offset is not None:
                    message_data_for_response['veyra_current_offset'] = current_offset
                if limit_per_page is not None:
                    message_data_for_response['veyra_limit_per_page'] = limit_per_page
                if total_available is not None:
                    message_data_for_response['veyra_total_emails_available'] = total_available

                if has_more is None and current_offset is not None and limit_per_page is not None and total_available is not None:
                    has_more = (current_offset + limit_per_page) < total_available
                    print(f"[DEBUG /get_thread] Calculated veyra_has_more for message {msg_doc.get('message_id')}: {has_more}")
                elif has_more is not None:
                    print(f"[DEBUG /get_thread] Using stored veyra_has_more for message {msg_doc.get('message_id')}: {has_more}")
                
                if has_more is not None:
                    message_data_for_response['veyra_has_more'] = has_more
            # --- End Veyra Results & Pagination Logic ---
            
            processed_messages_for_response.append(message_data_for_response)

        print(f"Found and processed {len(processed_messages_for_response)} messages for thread {thread_id}")
        
        response_data = {
            "thread_id": thread_doc.get("thread_id"),
            "title": thread_doc.get("title"),
            "messages": processed_messages_for_response,
            "created_at": datetime.fromtimestamp(thread_doc.get("created_at")).isoformat() if isinstance(thread_doc.get("created_at"), (int, float)) else (
                            thread_doc.get("created_at").isoformat() if hasattr(thread_doc.get("created_at"), "isoformat") else None
                        ), # Handle both timestamp and existing datetime obj
            "updated_at": datetime.fromtimestamp(thread_doc.get("updated_at")).isoformat() if isinstance(thread_doc.get("updated_at"), (int, float)) else (
                            thread_doc.get("updated_at").isoformat() if hasattr(thread_doc.get("updated_at"), "isoformat") else None
                        )  # Handle both timestamp and existing datetime obj
        }
        print(f"Returning thread data: {json.dumps(response_data, default=str)[:500]}...")
        return jsonify(response_data), 200
    except Exception as e:
        print(f"[ERROR] Error fetching thread {thread_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {str(e)}"}), 500

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
        
        message_id = data.get('message_id')  # The conversation message ID
        email_id = data.get('email_id')      # The Gmail message ID
        thread_id = data.get('thread_id')
        
        if not email_id or not thread_id:
            print(f"Missing required parameters. email_id: {email_id}, thread_id: {thread_id}")
            return jsonify({
                'success': False,
                'error': 'Missing required parameters: email_id and thread_id are required'
            }), 400
        
        # Check if VeyraX service is initialized
        if not veyrax_service:
            print("VeyraX service not initialized")
            return jsonify({
                'success': False,
                'error': 'VeyraX service not initialized'
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
            
        # Check if the conversation has veyra_results with emails
        if not conversation.get('veyra_results') or not conversation.get('veyra_results').get('emails'):
            print(f"No emails found in conversation")
            return jsonify({
                'success': False,
                'error': 'No emails found in conversation'
            }), 404
        
        # Look for the email in veyra_results.emails
        emails = conversation.get('veyra_results').get('emails', [])
        print(f"Found {len(emails)} emails in conversation")
        
        # Debug: Print email IDs
        email_ids = [e.get('id') for e in emails]
        print(f"Email IDs in conversation: {email_ids}")
            
        # Find the email with the matching ID
        matching_email = next((e for e in emails if e.get('id') == email_id), None)
        
        if not matching_email:
            print(f"Email with ID {email_id} not found in conversation")
            return jsonify({
                'success': False,
                'error': 'Email not found in conversation'
            }), 404
            
        # Delete from Gmail using the email_id
        delete_success = veyrax_service.delete_email(email_id)
        print(f"Gmail deletion result: {delete_success}")
        
        if not delete_success:
            print(f"Failed to delete email from Gmail: {email_id}")
            # Continue anyway to update MongoDB
            
        # Update MongoDB to remove the email
        try:
            update_result = Conversation.update_one(
                {'_id': conversation['_id']},
                {'$pull': {'veyra_results.emails': {'id': email_id}}}
            )
            
            update_success = update_result.modified_count > 0
            db_message = "Database updated successfully" if update_success else "No changes made to database"
            
            if not update_success:
                print(f"No updates made to MongoDB for email: {email_id}")
                # This could be because the email was already removed
            
            print(f"Successfully processed email {email_id} from conversation {message_id}")
            return jsonify({
                'success': True,
                'message': f'Email processed: Gmail deletion {"succeeded" if delete_success else "failed"}, {db_message}',
                'deleted_email_id': email_id,
                'gmail_success': delete_success,
                'db_success': update_success
            })
            
        except Exception as db_error:
            print(f"Database error: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': f'Database error: {str(db_error)}'
            }), 500
        
    except Exception as e:
        print(f"Error in delete_email endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

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
        
        # Check if VeyraX service is initialized
        if not veyrax_service:
            print("VeyraX service not initialized")
            return jsonify({
                'success': False,
                'error': 'VeyraX service not initialized'
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
            
        # Check if the conversation has veyra_results with calendar events
        if not conversation.get('veyra_results') or not conversation.get('veyra_results').get('calendar_events'):
            print(f"No calendar events found in conversation")
            return jsonify({
                'success': False,
                'error': 'No calendar events found in conversation'
            }), 404
        
        # Look for the event in veyra_results.calendar_events
        events = conversation.get('veyra_results').get('calendar_events', [])
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
            
        # Delete from Google Calendar using VeyraX service
        delete_success = veyrax_service.delete_calendar_event(event_id)
        print(f"Google Calendar deletion result: {delete_success}")
        
        if not delete_success:
            print(f"Failed to delete event from Google Calendar: {event_id}")
            # Continue anyway to update MongoDB
            
        # Update MongoDB to remove the event
        try:
            update_result = Conversation.update_one(
                {'_id': conversation['_id']},
                {'$pull': {'veyra_results.calendar_events': {'id': event_id}}}
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

        message_id = data.get('message_id')  # Assistant's message ID from the VeyraResults block
        thread_id = data.get('thread_id')    # Current chat thread_id
        items_to_process = data.get('items', []) # List of {item_id, item_type}

        if not all([message_id, thread_id, items_to_process]):
            error_msg = "Missing required parameters: message_id, thread_id, and items are required"
            print(f"[/bulk_delete_items] Error: {error_msg}. Provided: message_id={message_id}, thread_id={thread_id}, items_count={len(items_to_process)}")
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400

        if not veyrax_service:
            error_msg = "VeyraX service not initialized"
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
            #    assistant_messages = [m for m in alternative_conversations if m.get('role') == 'assistant' and m.get('veyra_results')]
            #    if assistant_messages:
            #        conversation_doc = assistant_messages[-1] # Get the last one
            #        print(f"[/bulk_delete_items] Fallback: Found conversation by thread_id, using last assistant message: {conversation_doc.get('message_id')}")
            # if not conversation_doc: # if still not found
            return jsonify({'success': False, 'error': error_msg}), 404
        
        print(f"[/bulk_delete_items] Found conversation with _id: {conversation_doc.get('_id')} and message_id: {conversation_doc.get('message_id')}")

        if not conversation_doc.get('veyra_results'):
            error_msg = f"No veyra_results found in conversation {conversation_doc.get('message_id')}"
            print(f"[/bulk_delete_items] Error: {error_msg}")
            return jsonify({'success': False, 'error': error_msg}), 404

        processed_results = []
        email_ids_to_pull_from_db = []
        event_ids_to_pull_from_db = []

        current_emails_in_db = conversation_doc.get('veyra_results', {}).get('emails', [])
        current_events_in_db = conversation_doc.get('veyra_results', {}).get('calendar_events', [])

        print(f"[/bulk_delete_items] Initial emails in DB for this message: {len(current_emails_in_db)}")
        print(f"[/bulk_delete_items] Initial events in DB for this message: {len(current_events_in_db)}")

        for item_data in items_to_process:
            item_id = item_data.get('item_id')
            item_type = item_data.get('item_type')
            deletion_successful_veyrax = False
            item_error_message = None

            print(f"[/bulk_delete_items] Processing item: id={item_id}, type={item_type}")

            if not item_id or not item_type:
                item_error_message = 'Missing item_id or item_type in item_data'
                print(f"[/bulk_delete_items] Skipping item due to error: {item_error_message}. Data: {item_data}")
                processed_results.append({'item_id': item_id, 'item_type': item_type, 'deleted': False, 'error': item_error_message})
                continue

            try:
                item_exists_in_conversation_results = False
                # Initialize deletion_successful_veyrax, as it might not be set if item_type is unknown
                deletion_successful_veyrax = False 

                if item_type == 'email':
                    item_exists_in_conversation_results = any(e.get('id') == item_id for e in current_emails_in_db)
                    if item_exists_in_conversation_results:
                        print(f"[/bulk_delete_items] Attempting VeyraX delete for email: {item_id}")
                        try:
                            # Actual veyrax_service.delete_email returns a boolean
                            deletion_successful_veyrax = veyrax_service.delete_email(item_id)
                            
                            if deletion_successful_veyrax:
                                print(f"[/bulk_delete_items] VeyraX delete SUCCESS for email: {item_id}")
                                email_ids_to_pull_from_db.append(item_id)
                            else:
                                item_error_message = f"VeyraX call to delete email {item_id} returned False. This could be due to the item not being found on the VeyraX side or another issue."
                                print(f"[/bulk_delete_items] VeyraX delete FAILED for email: {item_id}. {item_error_message}")
                                # If VeyraX internally logs "not found" and returns False,
                                # we might still want to remove it from our DB if that's the desired behavior.
                                # For now, we only add to email_ids_to_pull_from_db if VeyraX confirmed deletion (returned True).
                        except Exception as delete_err:
                            deletion_successful_veyrax = False 
                            item_error_message = f"Exception during VeyraX API call for email {item_id}: {str(delete_err)}"
                            print(f"[/bulk_delete_items] {item_error_message}")
                            import traceback # Ensure traceback is imported here if not globally
                            print(traceback.format_exc())
                    else:
                        item_error_message = f"Email {item_id} not found in this conversation message's Veyra results. Skipping VeyraX call."
                        print(f"[/bulk_delete_items] {item_error_message}")
                        deletion_successful_veyrax = False
                        
                elif item_type == 'event':
                    item_exists_in_conversation_results = any(e.get('id') == item_id for e in current_events_in_db)
                    if item_exists_in_conversation_results:
                        print(f"[/bulk_delete_items] Attempting VeyraX delete for event: {item_id}")
                        try:
                            # Actual veyrax_service.delete_calendar_event returns a boolean
                            deletion_successful_veyrax = veyrax_service.delete_calendar_event(item_id)

                            if deletion_successful_veyrax:
                                print(f"[/bulk_delete_items] VeyraX delete SUCCESS for event: {item_id}")
                                event_ids_to_pull_from_db.append(item_id)
                            else:
                                item_error_message = f"VeyraX call to delete event {item_id} returned False. This could be due to the item not being found on the VeyraX side or another issue."
                                print(f"[/bulk_delete_items] VeyraX delete FAILED for event: {item_id}. {item_error_message}")
                        except Exception as delete_err:
                            deletion_successful_veyrax = False
                            item_error_message = f"Exception during VeyraX API call for event {item_id}: {str(delete_err)}"
                            print(f"[/bulk_delete_items] {item_error_message}")
                            import traceback # Ensure traceback is imported here if not globally
                            print(traceback.format_exc())
                    else:
                        item_error_message = f"Event {item_id} not found in this conversation message's Veyra results. Skipping VeyraX call."
                        print(f"[/bulk_delete_items] {item_error_message}")
                        deletion_successful_veyrax = False
                else:
                    item_error_message = f"Unknown item_type: {item_type}"
                    print(f"[/bulk_delete_items] {item_error_message}")
                    deletion_successful_veyrax = False

            except Exception as e: # This is the outer try-except for the item processing logic
                deletion_successful_veyrax = False 
                item_error_message = f"Outer exception processing item {item_type} {item_id}: {str(e)}"
                print(f"[/bulk_delete_items] {item_error_message}")
                import traceback # Ensure traceback is imported here if not globally
                print(traceback.format_exc())
            
            # This processed_results.append call should be outside the 'try...except e:' block above,
            # but still inside the 'for item_data in items_to_process:' loop.
            processed_results.append({
                'item_id': item_id, 
                'item_type': item_type, 
                'deleted': deletion_successful_veyrax, 
                'error': item_error_message
            })

        # Update MongoDB to remove items that were successfully deleted from VeyraX OR reported as not_found by VeyraX
        db_modified_count = 0
        if email_ids_to_pull_from_db or event_ids_to_pull_from_db:
            mongo_update_operations = {}
            if email_ids_to_pull_from_db:
                mongo_update_operations['$pull'] = {
                    'veyra_results.emails': {'id': {'$in': email_ids_to_pull_from_db}}
                }
                print(f"[/bulk_delete_items] Preparing to pull emails from DB: {email_ids_to_pull_from_db}")
            
            if event_ids_to_pull_from_db:
                event_pull_op = {'veyra_results.calendar_events': {'id': {'$in': event_ids_to_pull_from_db}}}
                if '$pull' in mongo_update_operations:
                    mongo_update_operations['$pull'].update(event_pull_op)
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
                except Exception as db_e:
                    db_error_msg = f"Database error during bulk update: {str(db_e)}"
                    print(f"[/bulk_delete_items] {db_error_msg}")
                    # This error should be logged, but the overall success for items is based on VeyraX deletion primarily.
                    # We might want to reflect this DB error in the individual item results if critical.
        else:
            print("[/bulk_delete_items] No items successfully deleted from VeyraX, so no MongoDB update needed.")

        print(f"[/bulk_delete_items] Final processed results: {json.dumps(processed_results)}")
        return jsonify({
            'success': True, # Indicates the endpoint processed the request as a whole
            'results': processed_results, # Detailed status for each item based on VeyraX deletion
            'db_items_removed_count': db_modified_count # How many items were intended to be pulled from DB based on VeyraX success
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
        # Fetch the specific assistant message
        assistant_message_doc = Conversation.find_one({
            'thread_id': thread_id, 
            'message_id': assistant_message_id,
            'role': 'assistant'
        })
        if not assistant_message_doc:
            print(f"[ERROR] Assistant message not found for ID: {assistant_message_id} in thread: {thread_id}")
            return jsonify({"error": "Assistant message not found"}), 404
        print(f"[DEBUG] Found assistant message: {assistant_message_doc.get('_id')}")
        # Retrieve stored pagination parameters
        original_params = assistant_message_doc.get('veyra_original_query_params')
        current_offset = assistant_message_doc.get('veyra_current_offset')
        limit_per_page = assistant_message_doc.get('veyra_limit_per_page')
        total_emails_available = assistant_message_doc.get('veyra_total_emails_available')
        print(f"[DEBUG] Stored pagination: offset={current_offset}, limit={limit_per_page}, total={total_emails_available}, original_params={original_params}")
        if original_params is None or current_offset is None or limit_per_page is None or total_emails_available is None:
            print("[ERROR] Missing one or more pagination parameters in the stored message.")
            return jsonify({"new_emails": [], "has_more": False, "message": "Pagination parameters missing in stored message."}), 400
        next_offset_to_fetch = current_offset + limit_per_page
        if next_offset_to_fetch >= total_emails_available:
            print("[INFO] No more emails to load.")
            return jsonify({"new_emails": [], "has_more": False, "message": "No more emails to load."}), 200
        if not veyrax_service:
            print("[ERROR] VeyraX service not initialized for /load_more_emails")
            return jsonify({"error": "VeyraX service not available"}), 500
        # Prepare parameters for VeyraX call
        fetch_params = {
            **original_params, # search_query, folder, etc.
            "limit": limit_per_page,
            "offset": next_offset_to_fetch
        }
        print(f"[DEBUG] Calling VeyraX with: {fetch_params}")
        veyrax_response = veyrax_service.post_request("/mail/get_messages", fetch_params)
        print(f"[DEBUG] VeyraX response for /load_more_emails: {json.dumps(veyrax_response)[:500]}")
        if "error" in veyrax_response:
            print(f"[ERROR] VeyraX error: {veyrax_response.get('error')}")
            return jsonify({"error": f"VeyraX error: {veyrax_response.get('error')}"}), 500
        new_data = veyrax_response.get("data", {})
        new_emails = new_data.get("messages", [])
        new_offset_used = new_data.get("offset", next_offset_to_fetch) # VeyraX returns the offset it used
        new_limit_used = new_data.get("limit", limit_per_page)
        new_total_available = new_data.get("total", total_emails_available) # VeyraX may update total
        print(f"[DEBUG] VeyraX returned: {len(new_emails)} emails, new_offset={new_offset_used}, new_total={new_total_available}")
        # Update the Conversation document in MongoDB
        update_operations = {
            '$push': {'veyra_results.emails': {'$each': new_emails}},
            '$set': {
                'veyra_current_offset': new_offset_used,
                'veyra_total_emails_available': new_total_available # Update if VeyraX provides a new total
            }
        }
        update_result = Conversation.update_one(
            {'message_id': assistant_message_id, 'thread_id': thread_id},
            update_operations
        )
        print(f"[DEBUG] MongoDB update result: matched={update_result.matched_count}, modified={update_result.modified_count}")
        if update_result.modified_count == 0 and update_result.matched_count > 0:
            print("[WARNING] MongoDB document matched but was not modified. This might happen if $push had an empty list or $set values were identical.")
        elif update_result.matched_count == 0:
            print("[ERROR] Failed to find the assistant message in DB for update after VeyraX call.")
            # This case should ideally not happen if the initial find_one was successful.
            # Consider how to handle this discrepancy. For now, proceed with returning emails to client.
        has_more_after_this_load = (new_offset_used + new_limit_used) < new_total_available
        response_payload = {
            "new_emails": new_emails,
            "current_offset": new_offset_used,
            "limit_per_page": new_limit_used,
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)
