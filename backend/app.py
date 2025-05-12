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
from utils.mongo_client import get_db
from config.mongo_config import init_collections
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
            # New thread - create with first message as title
            thread = Thread(title=query[:50] + "..." if len(query) > 50 else query)
            thread.save()
            thread_id = thread.thread_id
        else:
            # Existing thread - update its updated_at timestamp
            thread = Thread.get_by_id(thread_id)
            if not thread:
                # Thread doesn't exist, create it
                thread = Thread(thread_id=thread_id, title=query[:50] + "..." if len(query) > 50 else query)
                thread.save()
        
        # Get thread history
        thread_history = []
        if thread_id:
            messages = Conversation.get_by_thread_id(thread_id)
            for msg in messages:
                if 'role' in msg:  # New schema
                    thread_history.append({"role": msg['role'], "content": msg['content']})
                else:  # Old schema
                    thread_history.append({"role": "user", "content": msg['query']})
                    thread_history.append({"role": "assistant", "content": msg['response']})
        
        print(f"Thread history length: {len(thread_history)}")
        
        # First, check for VeyraX data
        veyra_results = None
        veyra_context = None
        if veyrax_service:
            try:
                print("\n=== Processing VeyraX Query ===")
                print(f"Using VeyraX service: {type(veyrax_service).__name__}")
                veyrax_data = veyrax_service.process_query(query, thread_history)
                print(f"VeyraX data received: {veyrax_data}")
                
                if veyrax_data:
                    source_type = veyrax_data.get("source_type", "")
                    print(f"VeyraX source type: {source_type}")
                    
                    if source_type in ["mail", "gmail"]:
                        messages = veyrax_data.get("data", {}).get("messages", [])
                        print(f"VeyraX messages found: {len(messages) if messages else 0}")
                        if messages:
                            veyra_results = {"emails": messages}
                            veyra_context = veyrax_data
                            print(f"VeyraX results prepared: {veyra_results}")
                    elif source_type == "google-calendar":
                        events = veyrax_data.get("data", {}).get("events", [])
                        print(f"VeyraX calendar events found: {len(events) if events else 0}")
                        if events:
                            veyra_results = {"calendar_events": events}
                            veyra_context = veyrax_data
                            print(f"VeyraX results prepared: {veyra_results}")
            except Exception as e:
                print(f"Error processing VeyraX data: {str(e)}")
                print(f"Error type: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
        else:
            print("VeyraX service not initialized")
        
        # Get relevant documents using the retriever
        try:
            result = qa_chain.invoke({"query": query})  # Using invoke instead of __call__
            retrieved_docs = result["source_documents"]
        except Exception as e:
            print(f"Error in QA chain: {str(e)}")
            retrieved_docs = []
        
        # Build prompt with context and get response from LLM
        prompt, insight_id = build_prompt(query, retrieved_docs, thread_history, veyra_context)
        
        try:
            response = llm.invoke(prompt)
            response_text = response.content.strip()
        except Exception as e:
            if "overloaded_error" in str(e):
                error_message = "The AI service is currently experiencing high load. Please try again in a few moments."
                return jsonify({"error": error_message}), 503
            raise e
        
        # Save conversation using the Conversation class
        conversation = Conversation(
            thread_id=thread_id,
            query=query,
            response=response_text,
            insight_id=insight_id,
            veyra_results=veyra_results
        )
        print(f"\n=== Saving Conversation ===")
        print(f"VeyraX results being saved: {veyra_results}")
        conversation.save()
        
        response_data = {
            "response": response_text,
            "thread_id": thread_id,
            "veyra_results": veyra_results
        }
        print(f"\n=== Sending Response ===")
        print(f"Response data: {response_data}")
        return jsonify(response_data)
        
    except Exception as e:
        print(f"\n=== Error in chat endpoint ===")
        print(f"Error: {str(e)}")
        print(f"Error type: {type(e)}")
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
    try:
        messages = Conversation.get_by_thread_id(thread_id)
        formatted_messages = []
        for msg in messages:
            if 'role' in msg:  # New schema
                formatted_message = {
                    "role": msg['role'],
                    "content": msg['content'],
                    "message_id": msg['message_id']  # Add message_id to the response
                }
                if msg['role'] == 'assistant' and 'veyra_results' in msg:
                    formatted_message['veyra_results'] = msg['veyra_results']
            else:  # Old schema
                # Convert old format to new format
                formatted_messages.append({
                    "role": "user",
                    "content": msg['query']
                })
                formatted_messages.append({
                    "role": "assistant",
                    "content": msg['response'],
                    "veyra_results": msg.get('veyra_results')
                })
                continue
            formatted_messages.append(formatted_message)
        return jsonify({"messages": formatted_messages})
    except Exception as e:
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

if __name__ == '__main__':
    app.run(port=5001, debug=True)
