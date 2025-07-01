from composio.client.enums import Action
from composio.tools import ComposioToolSet
from datetime import datetime, timedelta
import base64
import openai
import os
import json
import zoneinfo
import time
from bson import ObjectId

class ComposioService:
    def __init__(self, api_key: str):
        """
        Initializes the ComposioToolSet client.
        """
        if not api_key:
            raise ValueError("Composio API key is required for ComposioService.")
        self.toolset = ComposioToolSet(api_key=api_key)
        # Note: Integration IDs are not used in execute calls, but are kept here for reference
        self.google_calendar_integration_id = "ac_ew6S2XYd__tb"
        self.gmail_integration_id = "ac_JyTGY5W15_eM" # Updated ID
        
        # Initialize Gemini LLM for query classification
        self.gemini_llm = None
        self._init_gemini_llm()

    def _init_gemini_llm(self):
        """Initialize Gemini LLM for query classification if available."""
        try:
            google_api_key = os.getenv('GOOGLE_API_KEY')
            if google_api_key:
                from langchain_google_genai import ChatGoogleGenerativeAI
                self.gemini_llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-lite",
                    google_api_key=google_api_key,
                    convert_system_message_to_human=True
                )
                print("[DEBUG] Gemini LLM initialized for Composio query classification")
            else:
                print("[WARNING] GOOGLE_API_KEY not found. Query classification will fall back to keyword matching.")
        except Exception as e:
            print(f"[WARNING] Failed to initialize Gemini LLM for query classification: {e}")
            self.gemini_llm = None

    def classify_query_with_llm(self, user_query, conversation_history=None):
        """
        Use Gemini LLM to classify user query intent with conversation context.
        
        Returns:
            dict: {
                "intent": "email" | "calendar" | "contact" | "general",
                "confidence": 0.0-1.0,
                "reasoning": "explanation",
                "parameters": {...}
            }
        """
        if not self.gemini_llm:
            print("[DEBUG] Gemini LLM not available, falling back to keyword classification")
            return self._fallback_keyword_classification(user_query)
        
        try:
            # Build conversation context
            context_text = ""
            if conversation_history:
                # Include last 6 messages for context (3 exchanges)
                recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                for msg in recent_history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')[:300]  # Truncate for brevity
                    context_text += f"{role.capitalize()}: {content}\n"
            
            # Create the classification prompt
            prompt = f"""You are an expert query classifier for a personal assistant that can access emails, calendar events, and contacts.

CONVERSATION CONTEXT (recent messages):
{context_text}

USER QUERY: "{user_query}"

CLASSIFICATION TASK:
Analyze the user's query considering the conversation context. Classify the intent as one of:

1. "email" - User wants to find, search, or work with emails/messages
   Examples: "show me emails", "check my inbox", "emails from John", "unread messages"

2. "calendar" - User wants to find, search, or work with calendar events/meetings
   Examples: "what's on my calendar", "meetings today", "schedule for this week", "upcoming events"

3. "contact" - User wants to find, search, or get information about contacts/people
   Examples: "what's the email of John Doe", "contact info for Sarah", "find contact Dawid", "email address of Mike", "all emails of John" (meaning email addresses), "phone number of Sarah"

4. "general" - General questions, conversation, or non-email/calendar/contact requests
   Examples: "how's the weather", "what is AI", "tell me a joke"

IMPORTANT CONTEXT RULES:
- If previous messages were about emails/calendar/contacts and current query is vague ("and this week?", "show me more", "what about tomorrow?"), inherit that context
- Time-related queries without explicit service ("today", "this week", "tomorrow") should prefer calendar if recent context suggests it
- Follow-up questions typically maintain the same intent as previous queries
- Queries asking for "email of [person]" or "emails of [person]" or "contact info" should be classified as "contact", not "email"
- "Emails from [person]" or "messages from [person]" should be classified as "email" (searching for messages)
- "Email addresses of [person]" or "all emails of [person]" should be classified as "contact" (contact information)

RESPONSE FORMAT (JSON only):
{{
  "intent": "email" | "calendar" | "contact" | "general",
  "confidence": 0.95,
  "reasoning": "Brief explanation of why this classification was chosen",
  "parameters": {{
    "timeframe": "today|this_week|tomorrow|...",
    "keywords": ["relevant", "search", "terms"],
    "context_inherited": true/false
  }}
}}

Respond with ONLY the JSON object, no additional text."""

            # Call Gemini
            response = self.gemini_llm.invoke(prompt)
            response_text = str(response.content).strip()
            
            print(f"[DEBUG] Gemini classification response: {response_text}")
            
            # Parse JSON response - strip markdown code blocks if present
            try:
                # Remove markdown code block formatting if present
                json_text = response_text
                if json_text.startswith('```json'):
                    json_text = json_text.replace('```json', '').replace('```', '').strip()
                elif json_text.startswith('```'):
                    json_text = json_text.replace('```', '').strip()
                
                classification = json.loads(json_text)
                
                # Validate the response structure
                if not isinstance(classification, dict) or "intent" not in classification:
                    raise ValueError("Invalid classification response structure")
                
                intent = classification.get("intent")
                if intent not in ["email", "calendar", "contact", "general"]:
                    raise ValueError(f"Invalid intent: {intent}")
                
                # Ensure confidence is present and reasonable
                confidence = classification.get("confidence", 0.8)
                if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                    confidence = 0.8
                    classification["confidence"] = confidence
                
                print(f"[DEBUG] Successfully classified query as '{intent}' with confidence {confidence}")
                return classification
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[WARNING] Failed to parse Gemini classification response: {e}")
                print(f"[WARNING] Raw response: {response_text}")
                return self._fallback_keyword_classification(user_query)
                
        except Exception as e:
            print(f"[ERROR] Error during Gemini query classification: {e}")
            return self._fallback_keyword_classification(user_query)

    def _fallback_keyword_classification(self, user_query):
        """
        Fallback keyword-based classification when LLM is unavailable.
        """
        query_lower = user_query.lower()
        
        # Email keywords
        email_keywords = ["email", "mail", "gmail", "inbox", "message", "unread"]
        # Calendar keywords  
        calendar_keywords = ["calendar", "event", "meeting", "schedule", "appointment", "agenda"]
        
        email_score = sum(1 for keyword in email_keywords if keyword in query_lower)
        calendar_score = sum(1 for keyword in calendar_keywords if keyword in query_lower)
        
        if email_score > calendar_score:
            intent = "email"
            confidence = min(0.9, 0.5 + email_score * 0.2)
        elif calendar_score > email_score:
            intent = "calendar" 
            confidence = min(0.9, 0.5 + calendar_score * 0.2)
        else:
            intent = "general"
            confidence = 0.3
        
        return {
            "intent": intent,
            "confidence": confidence,
            "reasoning": f"Keyword-based classification: email_score={email_score}, calendar_score={calendar_score}",
            "parameters": {
                "context_inherited": False,
                "keywords": user_query.split()[:3]  # First 3 words as keywords
            }
        }

    def _execute_action(self, action: Action, params: dict | None = None):
        """Helper to execute an action."""
        try:
            response = self.toolset.execute_action(
                action=action,
                entity_id="default",
                params=params or {}
            )
            return response
        except Exception as e:
            # Correctly handle printing the action enum
            print(f"Error executing action {str(action)}: {e}")
            return {"successful": False, "error": str(e)}

    def get_recent_emails(self, count=10, query=None, page_token=None, **kwargs):
        """
        Get recent emails using the GMAIL_FETCH_EMAILS action.
        Uses Gmail's native pagination tokens from Composio.
        """
        params = {
            "max_results": count
        }
        
        # Only include query on first request (when no page_token)
        if not page_token and query:
            params["query"] = query
            print(f"[DEBUG] First request with Gmail query: {query}")
        
        # Include Gmail's native page_token if provided
        if page_token:
            params["page_token"] = page_token
            print(f"[DEBUG] Subsequent request with Gmail page_token: {page_token[:50]}...")
        
        print(f"[DEBUG] Calling Composio with params: {params}")
        
        response = self._execute_action(
            action=Action.GMAIL_FETCH_EMAILS,
            params=params
        )
        
        if response.get("successful"):
            data = response.get("data", {})
            messages = data.get("messages", [])
            
            # Get Gmail's native nextPageToken from Composio response
            gmail_next_token = data.get("nextPageToken")
            
            print(f"[DEBUG] Gmail response: {len(messages)} messages")
            print(f"[DEBUG] Gmail nextPageToken from Composio: {gmail_next_token[:50] + '...' if gmail_next_token else 'None'}")
            
            # Get total estimate from Gmail
            result_size_estimate = data.get("resultSizeEstimate", len(messages))
            
            return {
                "data": data,
                "next_page_token": gmail_next_token,  # Use Gmail's native token
                "total_estimate": result_size_estimate,
                "has_more": bool(gmail_next_token and len(messages) == count)
            }
        else:
            print(f"[DEBUG] Gmail request failed: {response.get('error')}")
            return {"error": response.get("error")}

    def get_recent_emails_with_gmail_tokens(self, count=10, query=None, page_token=None, **kwargs):
        """
        Test version using pure Gmail pageToken approach.
        This method tests if Composio supports Gmail's native pagination tokens.
        """
        params = {
            "max_results": count
        }
        
        # Only include query on first request (when no page_token)
        if not page_token and query:
            params["query"] = query
            print(f"[DEBUG] First request with query: {query}")
        
        # Include page_token if provided (should be Gmail's opaque token)
        if page_token:
            params["page_token"] = page_token
            print(f"[DEBUG] Subsequent request with page_token: {page_token[:50]}...")
        
        print(f"[DEBUG] Gmail token test - calling Composio with params: {params}")
        
        response = self._execute_action(
            action=Action.GMAIL_FETCH_EMAILS,
            params=params
        )
        
        if response.get("successful"):
            data = response.get("data", {})
            messages = data.get("messages", [])
            
            # Try to get Gmail's native nextPageToken from response
            gmail_next_token = data.get("nextPageToken")
            
            print(f"[DEBUG] Gmail token test - got {len(messages)} messages")
            print(f"[DEBUG] Gmail token test - nextPageToken from response: {gmail_next_token[:50] if gmail_next_token else 'None'}...")
            
            # Estimate total
            result_size_estimate = data.get("resultSizeEstimate", len(messages))
            
            return {
                "data": data,
                "next_page_token": gmail_next_token,  # Use Gmail's native token
                "total_estimate": result_size_estimate,
                "has_more": bool(gmail_next_token and len(messages) == count),
                "token_type": "gmail_native"  # Flag to identify this approach
            }
        else:
            print(f"[DEBUG] Gmail token test - Error: {response.get('error')}")
            return {"error": response.get("error")}

    def test_pagination_approaches(self, query=None, count=5):
        """
        Test both pagination approaches side by side for comparison.
        Returns results from both methods to compare effectiveness.
        """
        print(f"\n=== Testing Pagination Approaches ===")
        print(f"Query: {query}, Count: {count}")
        
        # Test 1: Current date-based approach
        print(f"\n--- Test 1: Date-based pagination ---")
        try:
            date_result = self.get_recent_emails(count=count, query=query)
            print(f"Date-based result: {len(date_result.get('data', {}).get('messages', []))} messages")
            print(f"Date-based next_token: {date_result.get('next_page_token')}")
            print(f"Date-based has_more: {date_result.get('has_more')}")
        except Exception as e:
            print(f"Date-based approach failed: {e}")
            date_result = {"error": str(e)}
        
        # Test 2: Gmail native token approach
        print(f"\n--- Test 2: Gmail native token pagination ---")
        try:
            gmail_result = self.get_recent_emails_with_gmail_tokens(count=count, query=query)
            print(f"Gmail token result: {len(gmail_result.get('data', {}).get('messages', []))} messages")
            print(f"Gmail token next_token: {gmail_result.get('next_page_token', 'None')[:50] if gmail_result.get('next_page_token') else 'None'}...")
            print(f"Gmail token has_more: {gmail_result.get('has_more')}")
        except Exception as e:
            print(f"Gmail token approach failed: {e}")
            gmail_result = {"error": str(e)}
        
        # Compare results
        print(f"\n--- Comparison ---")
        date_count = len(date_result.get('data', {}).get('messages', [])) if 'error' not in date_result else 0
        gmail_count = len(gmail_result.get('data', {}).get('messages', [])) if 'error' not in gmail_result else 0
        
        print(f"Date-based approach: {date_count} messages, {'✓' if date_count > 0 else '✗'}")
        print(f"Gmail token approach: {gmail_count} messages, {'✓' if gmail_count > 0 else '✗'}")
        
        # Check if we got different message sets (which would indicate different sorting/pagination)
        if date_count > 0 and gmail_count > 0:
            date_ids = [msg.get('messageId') for msg in date_result.get('data', {}).get('messages', [])]
            gmail_ids = [msg.get('messageId') for msg in gmail_result.get('data', {}).get('messages', [])]
            
            common_ids = set(date_ids) & set(gmail_ids)
            print(f"Common messages between approaches: {len(common_ids)}/{min(date_count, gmail_count)}")
            
            if len(common_ids) == min(date_count, gmail_count):
                print("✓ Both approaches returned the same messages (possibly in different order)")
            else:
                print("⚠ Approaches returned different message sets")
        
        return {
            "date_based": date_result,
            "gmail_native": gmail_result,
            "comparison": {
                "date_count": date_count,
                "gmail_count": gmail_count,
                "both_successful": date_count > 0 and gmail_count > 0
            }
        }

    def get_email_details(self, email_id):
        """
        Get full email content using GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID action.
        Returns the full email content (HTML or text) for summarization.
        """
        response = self._execute_action(
            action=Action.GMAIL_FETCH_MESSAGE_BY_MESSAGE_ID,
            params={
                "message_id": email_id, 
                "format": "full",
                "user_id": "me"
            }
        )
        
        if response.get("successful"):
            email_data = response.get("data")
            if not email_data:
                email_data = {}
            print(f"[DEBUG] get_email_details - Full email data keys: {list(email_data.keys()) if email_data else 'None'}")
            
            # Try to extract content from the response
            # The response structure may vary, so we'll try multiple approaches
            content = ""
            
            # Try to get payload data (Gmail API format)
            payload = email_data.get("payload", {})
            if payload:
                print(f"[DEBUG] get_email_details - Payload mimeType: {payload.get('mimeType')}")
                
                # Check if it's a simple text/html message
                if payload.get("mimeType") in ["text/html", "text/plain"]:
                    body_data = payload.get("body", {}).get("data")
                    if body_data:
                        try:
                            content = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                            print(f"[DEBUG] get_email_details - Decoded simple message, length: {len(content)}")
                        except Exception as e:
                            print(f"[DEBUG] get_email_details - Error decoding simple message: {e}")
                
                # Check if it's a multipart message
                elif "parts" in payload:
                    print(f"[DEBUG] get_email_details - Multipart message with {len(payload.get('parts', []))} parts")
                    content = self._extract_content_from_parts(payload.get("parts", []))
            
            # Fallback to other fields if no content found in payload
            if not content:
                # Try messageText field (Composio specific)
                message_text = email_data.get("messageText", "")
                if message_text:
                    content = message_text
                    print(f"[DEBUG] get_email_details - Using messageText fallback, length: {len(content)}")
                
                # Final fallback to snippet
                if not content:
                    content = email_data.get("snippet", "")
                    print(f"[DEBUG] get_email_details - Using snippet fallback, length: {len(content)}")
            
            return content if content else None
        else:
            print(f"[DEBUG] get_email_details - Action not successful: {response.get('error', 'Unknown error')}")
            return None

    def _extract_content_from_parts(self, parts, depth=0):
        """
        Recursively extract content from email parts, handling nested multipart structures.
        """
        indent = "  " * depth
        content = ""
        
        for i, part in enumerate(parts):
            mime_type = part.get("mimeType", "")
            print(f"[DEBUG] get_email_details - {indent}Part {i}: {mime_type}")
            
            # If this is a multipart part, recurse into its parts
            if mime_type.startswith("multipart/") and "parts" in part:
                print(f"[DEBUG] get_email_details - {indent}Recursing into multipart with {len(part.get('parts', []))} sub-parts")
                nested_content = self._extract_content_from_parts(part.get("parts", []), depth + 1)
                if nested_content and not content:  # Use first non-empty content found
                    content = nested_content
            
            # If this is a text part, try to extract content
            elif mime_type in ["text/html", "text/plain"]:
                body_data = part.get("body", {}).get("data")
                if body_data:
                    try:
                        decoded_content = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                        print(f"[DEBUG] get_email_details - {indent}Decoded part {i}, length: {len(decoded_content)}")
                        
                        # Prefer HTML content, but accept text/plain as fallback
                        if mime_type == "text/html" or (not content and mime_type == "text/plain"):
                            content = decoded_content
                            if mime_type == "text/html":
                                break  # Prefer HTML, so break on first HTML part
                    except Exception as e:
                        print(f"[DEBUG] get_email_details - {indent}Error decoding part {i}: {e}")
        
        return content

    def delete_email(self, message_id, permanently=False, **kwargs):
        action = Action.GMAIL_DELETE_EMAIL_PERMANENTLY if permanently else Action.GMAIL_TRASH_EMAIL
        response = self._execute_action(
            action=action,
            params={"message_id": message_id}
        )
        return response.get("successful", False)

    def get_upcoming_events(self, days=7, max_results=10, **kwargs):
        """
        Legacy method for backwards compatibility. 
        Use list_events() for more flexible event listing.
        """
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        return self.list_events(time_min=time_min, time_max=time_max, max_results=max_results)

    def list_events(self, calendar_id="primary", time_min=None, time_max=None, max_results=10, 
                   single_events=True, order_by="startTime", show_deleted=False, **kwargs):
        """
        List calendar events with flexible filtering options.
        Enhanced replacement for get_upcoming_events() with more functionality.
        
        Args:
            calendar_id: Calendar identifier (default: "primary")
            time_min: Lower bound for event end time (RFC3339 timestamp)
            time_max: Upper bound for event start time (RFC3339 timestamp)
            max_results: Maximum number of events to return (1-2500)
            single_events: Expand recurring events into instances
            order_by: Order of events ("startTime" or "updated")
            show_deleted: Include deleted events
        """
        params = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": single_events,
            "showDeleted": show_deleted
        }
        
        # Add optional parameters
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if order_by:
            params["orderBy"] = order_by
            
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_EVENTS_LIST,
            params=params
        )
        if response and response.get("successful"):
            return {"data": response.get("data", {})}
        else:
            return {"error": response.get("error") if response else "No response received"}

    def find_events(self, query=None, calendar_id="primary", time_min=None, time_max=None, 
                   max_results=10, event_types=None, single_events=True, **kwargs):
        """
        Search for events using text query and filters.
        Perfect for "show me meetings with John" or "events about project X"
        
        Args:
            query: Free-text search terms to find events
            calendar_id: Calendar identifier (default: "primary")
            time_min: Lower bound for event end time (RFC3339 timestamp)
            time_max: Upper bound for event start time (RFC3339 timestamp)
            max_results: Maximum number of events to return (1-2500)
            event_types: List of event types to include
            single_events: Expand recurring events into instances
        """
        params = {
            "calendar_id": calendar_id,
            "max_results": max_results,
            "single_events": single_events
        }
        
        # Add search query
        if query:
            params["query"] = query
            
        # Add time filters
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
            
        # Add event types filter
        if event_types:
            params["event_types"] = event_types
            
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_FIND_EVENT,
            params=params
        )
        if response and response.get("successful"):
            return {"data": response.get("data", {})}
        else:
            return {"error": response.get("error") if response else "No response received"}

    def create_calendar_event(self, summary, start_time, end_time, location=None, description=None, attendees=None, calendar_id="primary"):
        """
        Create a calendar event with improved parameter handling and validation.
        """
        # Process attendees
        attendee_emails = []
        if attendees:
            for att in attendees:
                attendee_emails.append(att['email'] if isinstance(att, dict) else att)
        
        # Build parameters following Composio schema (not Google Calendar API format)
        params = {
            "calendarId": calendar_id,
            "summary": summary,
            "start_datetime": start_time,  # Flat field format for Composio
            "end_datetime": end_time       # Flat field format for Composio
        }
        
        # Add optional parameters
        if description:
            params["description"] = description
        if location:
            params["location"] = location
        if attendee_emails:
            params["attendees"] = [{"email": email} for email in attendee_emails]
        
        print(f"[DEBUG] Composio API call parameters: {params}")
        
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_CREATE_EVENT,
            params=params
        )
        
        if response and not response.get("error"):
            print(f"[DEBUG] Calendar event created successfully")
            event_data = response.get("data", {})
            print(f"[DEBUG] Event data received from API: {event_data}")
            
            # FRONTEND FIX: Flatten the response_data structure for frontend compatibility
            if "response_data" in event_data:
                # Extract the actual event data from response_data wrapper
                actual_event_data = event_data["response_data"]
                print(f"[DEBUG] Flattening response_data for frontend compatibility")
            else:
                actual_event_data = event_data
            
            # Add additional context for better LLM response
            response_content = {
                "source_type": "google-calendar",
                "content": f"Successfully created calendar event '{summary}' for {start_time}",
                "data": actual_event_data,  # Use flattened data
                "action_performed": "create",
                "event_details": {
                    "title": summary,
                    "date": start_time.split('T')[0],
                    "start_time": start_time.split('T')[1],
                    "end_time": end_time.split('T')[1],
                    "location": location
                }
            }
            print(f"[DEBUG] Returning creation response: action_performed=create")
            return response_content
        else:
            error_msg = response.get("error") if response else "Unknown error during event creation"
            print(f"[ERROR] Failed to create calendar event: {error_msg}")
            return {"error": error_msg}

    def update_calendar_event(self, event_id, summary=None, start_time=None, end_time=None, location=None, description=None, attendees=None, calendar_id="primary"):
        """
        Update a calendar event using enhanced parameter structure.
        """
        # Build parameters with proper schema structure
        params = {
            "calendarId": calendar_id,
            "eventId": event_id
        }
        
        # Add optional parameters with proper structure
        if summary: 
            params["summary"] = summary
        if start_time: 
            params["start_datetime"] = start_time  # Flat field format for Composio
        if end_time: 
            params["end_datetime"] = end_time     # Flat field format for Composio
        if description: 
            params["description"] = description
        if location: 
            params["location"] = location
        if attendees:
            attendee_emails = [att['email'] for att in attendees if isinstance(att, dict) and 'email' in att]
            params["attendees"] = [{"email": email} for email in attendee_emails]

        response = self._execute_action(
            action=Action.GOOGLECALENDAR_UPDATE_EVENT,
            params=params
        )
        
        if response and response.get("successful"):
            return {"data": response.get("data", {})}
        else:
            return {"error": response.get("error") if response else "No response received"}
            
    def delete_calendar_event(self, event_id, calendar_id="primary"):
        """
        Delete a calendar event using proper schema structure.
        """
        params = {
            "calendarId": calendar_id,  # Using camelCase as per schema
            "eventId": event_id
        }
        
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_DELETE_EVENT,
            params=params
        )
        
        return response and response.get("successful", False)

    def get_events_for_date(self, date=None):
        """
        Get calendar events for a specific date using the enhanced list_events method.
        """
        if date is None:
            date_obj = datetime.utcnow()
        else:
            try:
                # Basic parsing for YYYY-MM-DD
                date_obj = datetime.strptime(date, "%Y-%m-%d")
            except ValueError:
                return {"error": "Invalid date format. Please use YYYY-MM-DD."}

        time_min = date_obj.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + "Z"
        time_max = date_obj.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat() + "Z"

        # Use the enhanced list_events method
        return self.list_events(time_min=time_min, time_max=time_max, max_results=50)

    def summarize_emails(self, emails):
        """
        Format emails from Composio for easy reading, similar to the old Veyrax format.
        """
        if not emails:
            return "No emails found.", {}

        email_ids_dict = {}
        summary = []
        for i, email in enumerate(emails[:10], 1):  # Limit to 10 emails
            message_id = email.get("id")
            if message_id:
                email_ids_dict[str(i)] = message_id

            headers = email.get("payload", {}).get("headers", [])
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            date_str = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'Unknown Date')

            try:
                # Attempt to parse RFC 2822 date format
                date_obj = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')
                formatted_date = date_obj.strftime("%B %d, %Y at %I:%M %p")
            except (ValueError, TypeError):
                formatted_date = date_str

            summary.append(f"{i}. {sender}, {subject}, {formatted_date}")

        if not summary:
            return "No emails found.", {}

        return "\n".join(summary), email_ids_dict

    def summarize_calendar_events(self, events):
        """Format calendar events from Composio for easy reading."""
        if not events:
            return "No calendar events found."

        summary = []
        for i, event in enumerate(events[:10], 1):  # Limit to 10 events
            title = event.get("summary", "Untitled Event")
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "Unknown Time"))
            end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))
            location = event.get("location")
            attendees = event.get("attendees", [])

            summary.append(f"{i}. {title}")
            summary.append(f"   When: {start}" + (f" to {end}" if end else ""))
            if location:
                summary.append(f"   Where: {location}")
            if attendees:
                attendee_names = [a.get("email", a.get("displayName", "Unknown")) for a in attendees[:3]]
                if len(attendees) > 3:
                    attendee_names.append(f"and {len(attendees) - 3} more")
                summary.append(f"   Who: {', '.join(attendee_names)}")
            summary.append("")

        if not summary:
            return "No calendar events found."

        return "\n".join(summary)

    def build_gmail_query_with_llm(self, user_query, conversation_history=None):
        """
        Use LLM to intelligently build Gmail search queries from natural language.
        Returns a Gmail search query string or empty string for general queries.
        """
        try:
            from prompts import gmail_query_builder_prompt
            
            # Build the prompt
            prompt = gmail_query_builder_prompt(user_query, conversation_history)
            
            # Get OpenAI API key from environment
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                print("[WARNING] No OpenAI API key found, falling back to simple query building")
                return self._build_simple_query(user_query)
            
            # Call OpenAI API
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Using cost-effective model for query building
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,  # Gmail queries are typically short
                temperature=0.1,  # Low temperature for consistent, precise queries
                timeout=10  # Quick timeout for responsiveness
            )
            
            gmail_query = (response.choices[0].message.content or "").strip()
            print(f"[DEBUG] LLM-generated Gmail query: '{gmail_query}'")
            
            # Validate the query is reasonable (basic safety check)
            if len(gmail_query) > 500:  # Gmail has query limits
                print("[WARNING] Generated query too long, falling back to simple query")
                return self._build_simple_query(user_query)
            
            return gmail_query
            
        except Exception as e:
            print(f"[ERROR] Failed to build Gmail query with LLM: {e}")
            # Fallback to simple query building
            return self._build_simple_query(user_query)
    
    def _analyze_calendar_intent(self, user_query, thread_history=None):
        """
        Use LLM to analyze calendar intent and extract parameters.
        Determines if user wants to create or search calendar events and extracts relevant parameters.
        
        Returns:
            dict: {
                "operation": "create" | "search",
                "parameters": {...},
                "confidence": float
            }
        """
        if not self.gemini_llm:
            print("[DEBUG] Gemini LLM not available for calendar intent analysis, using fallback")
            return self._fallback_calendar_intent_analysis(user_query)
        
        try:
            # Build conversation context
            context_text = ""
            if thread_history:
                recent_history = thread_history[-6:] if len(thread_history) > 6 else thread_history
                for msg in recent_history:
                    role = msg.get('role', 'user')
                    content = msg.get('content', '')[:300]
                    context_text += f"{role.capitalize()}: {content}\n"
            
            current_date = datetime.now()
            current_weekday = current_date.strftime('%A')  # Monday, Tuesday, etc.
            
            prompt = f"""You are an expert calendar assistant. Analyze the user's query to determine if they want to CREATE a new calendar event or SEARCH for existing events.

CURRENT CONTEXT:
- Current date: {current_date.strftime('%Y-%m-%d')} ({current_weekday})
- Current time: {current_date.strftime('%H:%M')}

CONVERSATION CONTEXT:
{context_text}

USER QUERY: "{user_query}"

TASK: Determine the operation type and extract parameters.

OPERATIONS:
1. "create" - User wants to create/schedule/add a new calendar event
   - Keywords: create, schedule, add, book, set up, plan, new, make
   - Extract: title, date, time, location, description, attendees

2. "search" - User wants to find/view existing calendar events  
   - Keywords: show, find, what's, check, list, view, see
   - Extract: date_range, keywords, attendee_filter

PARAMETER EXTRACTION RULES:
For CREATE operations:
- title: Event title/summary (required)
- date: Event date in YYYY-MM-DD format (required) 
- start_time: Start time in HH:MM format (required)
- end_time: End time in HH:MM format (optional, default +1 hour)
- location: Event location (optional)
- description: Event description (optional)
- attendees: List of email addresses (optional)

For SEARCH operations:
- date_range: today/tomorrow/this week/next week/etc
- keywords: Search terms for event content
- time_range: morning/afternoon/evening

DATE/TIME PARSING:
- "Friday" = next Friday if today is not Friday, today if today is Friday
- "tomorrow" = {(current_date + timedelta(days=1)).strftime('%Y-%m-%d')}
- "today" = {current_date.strftime('%Y-%m-%d')}
- "5pm" = "17:00", "5:30pm" = "17:30"
- "noon" = "12:00", "midnight" = "00:00"
- If no time specified for create, use "09:00" as default

RESPONSE FORMAT (JSON only):
{{
  "operation": "create" | "search",
  "confidence": 0.95,
  "parameters": {{
    // For create:
    "title": "Event title",
    "date": "YYYY-MM-DD", 
    "start_time": "HH:MM",
    "end_time": "HH:MM",
    "location": "location",
    "description": "description",
    "attendees": ["email1@domain.com"]
    
    // For search:
    "date_range": "today|tomorrow|this week",
    "keywords": "search terms",
    "time_range": "morning|afternoon|evening"
  }}
}}

Respond with ONLY the JSON object."""

            # Call Gemini
            response = self.gemini_llm.invoke(prompt)
            response_text = str(response.content).strip()
            
            print(f"[DEBUG] Calendar intent analysis response: {response_text}")
            
            # Parse JSON response
            try:
                # Remove markdown code blocks if present
                json_text = response_text
                if json_text.startswith('```json'):
                    json_text = json_text.replace('```json', '').replace('```', '').strip()
                elif json_text.startswith('```'):
                    json_text = json_text.replace('```', '').strip()
                
                analysis = json.loads(json_text)
                
                # Validate response structure
                if not isinstance(analysis, dict) or "operation" not in analysis:
                    raise ValueError("Invalid analysis response structure")
                
                operation = analysis.get("operation")
                if operation not in ["create", "search"]:
                    raise ValueError(f"Invalid operation: {operation}")
                
                # Ensure confidence is present and reasonable
                confidence = analysis.get("confidence", 0.8)
                if not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
                    confidence = 0.8
                    analysis["confidence"] = confidence
                
                print(f"[DEBUG] Successfully analyzed calendar intent: {operation} (confidence: {confidence})")
                return analysis
                
            except (json.JSONDecodeError, ValueError) as e:
                print(f"[WARNING] Failed to parse calendar intent analysis: {e}")
                print(f"[WARNING] Raw response: {response_text}")
                return self._fallback_calendar_intent_analysis(user_query)
                
        except Exception as e:
            print(f"[ERROR] Error during calendar intent analysis: {e}")
            return self._fallback_calendar_intent_analysis(user_query)

    def _fallback_calendar_intent_analysis(self, user_query):
        """
        Fallback method for calendar intent analysis when LLM is unavailable.
        """
        query_lower = user_query.lower()
        
        # Keywords for creation
        create_keywords = ["create", "schedule", "add", "book", "set up", "plan", "new", "make"]
        # Keywords for searching  
        search_keywords = ["show", "find", "what's", "check", "list", "view", "see"]
        
        create_score = sum(1 for keyword in create_keywords if keyword in query_lower)
        search_score = sum(1 for keyword in search_keywords if keyword in query_lower)
        
        if create_score > search_score:
            operation = "create"
            confidence = min(0.8, 0.5 + create_score * 0.1)
            # Basic parameter extraction for fallback
            parameters = {
                "title": user_query,  # Use full query as title fallback
                "date": (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d'),  # Default to tomorrow
                "start_time": "09:00",  # Default start time
                "end_time": "10:00"     # Default end time
            }
        else:
            operation = "search"
            confidence = min(0.8, 0.5 + search_score * 0.1)
            parameters = {
                "date_range": "this week",
                "keywords": user_query
            }
        
        return {
            "operation": operation,
            "confidence": confidence,
            "parameters": parameters
        }

    def _process_calendar_intent(self, user_query, thread_history=None):
        """
        Enhanced calendar processing that handles both creation and searching using 2-stage approach.
        
        Stage 1: Analyze intent (create vs search) and extract parameters
        Stage 2: Execute appropriate action based on intent
        
        Args:
            user_query: The user's natural language query
            thread_history: Previous conversation context
            
        Returns:
            Response from appropriate calendar method
        """
        print(f"[DEBUG] Processing calendar intent for query: '{user_query}'")
        
        # Stage 1: Analyze intent and extract parameters
        analysis = self._analyze_calendar_intent(user_query, thread_history)
        
        operation = analysis.get("operation")
        parameters = analysis.get("parameters", {})
        confidence = analysis.get("confidence", 0.0)
        
        print(f"[DEBUG] Calendar intent analysis result:")
        print(f"  Operation: {operation}")
        print(f"  Confidence: {confidence}")
        print(f"  Parameters: {parameters}")
        
        # Stage 2: Execute appropriate action
        if operation == "create":
            return self._handle_calendar_creation(parameters)
        elif operation == "search":
            return self._handle_calendar_search(parameters, user_query)
        else:
            print(f"[WARNING] Unknown calendar operation: {operation}")
            # Fallback to search
            return self._handle_calendar_search(parameters, user_query)

    def _handle_calendar_creation(self, parameters):
        """
        Handle calendar event creation with extracted parameters.
        """
        try:
            # Validate required parameters
            title = parameters.get("title")
            date = parameters.get("date")
            start_time = parameters.get("start_time")
            
            if not all([title, date, start_time]):
                error_msg = f"Missing required parameters for event creation. Title: {title}, Date: {date}, Start time: {start_time}"
                print(f"[ERROR] {error_msg}")
                return {"error": error_msg}
            
            print(f"[DEBUG] Raw parameters received:")
            print(f"  Title: {title}")
            print(f"  Date: {date}")
            print(f"  Start time: {start_time}")
            print(f"  End time: {parameters.get('end_time')}")
            
            # Build start and end datetime strings in RFC3339 format
            end_time = parameters.get("end_time")
            if not end_time:
                # Default to 1 hour duration if no end time specified
                start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
                end_dt = start_dt + timedelta(hours=1)
                end_time = end_dt.strftime("%H:%M")
                print(f"[DEBUG] Generated end_time: {end_time}")
            
            # Get the local timezone (this will be the user's system timezone)
            # For Poland/Wrocław, this should be Europe/Warsaw
            try:
                local_tz = zoneinfo.ZoneInfo("Europe/Warsaw")  # Explicit timezone for Poland
                print(f"[DEBUG] Using timezone: Europe/Warsaw")
            except Exception as tz_error:
                # Fallback to system timezone if Europe/Warsaw is not available
                print(f"[WARNING] Europe/Warsaw timezone not available: {tz_error}")
                local_tz = zoneinfo.ZoneInfo(time.tzname[0])
                print(f"[DEBUG] Fallback to system timezone: {time.tzname[0]}")
            
            # Convert to timezone-aware datetime objects
            print(f"[DEBUG] Parsing datetime strings:")
            print(f"  Date + Start: '{date} {start_time}'")
            print(f"  Date + End: '{date} {end_time}'")
            
            start_dt = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
            
            print(f"[DEBUG] Parsed naive datetimes:")
            print(f"  Start: {start_dt}")
            print(f"  End: {end_dt}")
            
            # TIMEZONE FIX v2: Send as local time with timezone offset, but tell Composio the timezone
            # The issue is Composio treats naive datetime as UTC. We need to be explicit about local time.
            
            # Add timezone awareness to show this is local time
            start_dt_tz = start_dt.replace(tzinfo=local_tz)
            end_dt_tz = end_dt.replace(tzinfo=local_tz)
            
            # Convert to the format that represents the ACTUAL local time we want
            # But we'll adjust for the fact that Composio seems to expect UTC input
            
            # Calculate what UTC time would result in our desired local time
            # If we want 17:00 local (+02:00), we need to send 15:00 UTC so when converted it becomes 17:00 local
            utc_offset_hours = 2  # For Europe/Warsaw in summer (CEST)
            
            adjusted_start_dt = start_dt - timedelta(hours=utc_offset_hours)
            adjusted_end_dt = end_dt - timedelta(hours=utc_offset_hours)
            
            start_datetime = adjusted_start_dt.isoformat()
            end_datetime = adjusted_end_dt.isoformat()
            
            print(f"[DEBUG] Adjusted datetimes (accounting for Composio UTC conversion):")
            print(f"  Start: {start_datetime} (will become {start_time} local after Composio conversion)")
            print(f"  End: {end_datetime} (will become {end_time} local after Composio conversion)")
            
            # Get optional parameters
            location = parameters.get("location")
            description = parameters.get("description")
            attendees = parameters.get("attendees", [])
            
            print(f"[DEBUG] Final parameters for calendar creation:")
            print(f"  Title: {title}")
            print(f"  Start: {start_datetime}")
            print(f"  End: {end_datetime}")
            print(f"  Location: {location}")
            print(f"  Description: {description}")
            print(f"  Attendees: {attendees}")
            
            # Call the existing create_calendar_event method
            response = self.create_calendar_event(
                summary=title,
                start_time=start_datetime,
                end_time=end_datetime,
                location=location,
                description=description,
                attendees=attendees
            )
            
            if response and not response.get("error"):
                print(f"[DEBUG] Calendar event created successfully")
                event_data = response.get("data", {})
                print(f"[DEBUG] Event data received from API: {event_data}")
                
                # FRONTEND FIX: Flatten the response_data structure for frontend compatibility
                if "response_data" in event_data:
                    # Extract the actual event data from response_data wrapper
                    actual_event_data = event_data["response_data"]
                    print(f"[DEBUG] Flattening response_data for frontend compatibility")
                else:
                    actual_event_data = event_data
                
                # Add additional context for better LLM response
                response_content = {
                    "source_type": "google-calendar",
                    "content": f"Successfully created calendar event '{title}' for {date} at {start_time}",
                    "data": actual_event_data,  # Use flattened data
                    "action_performed": "create",
                    "event_details": {
                        "title": title,
                        "date": date,
                        "start_time": start_time,
                        "end_time": end_time,
                        "location": location
                    }
                }
                print(f"[DEBUG] Returning creation response: action_performed=create")
                return response_content
            else:
                error_msg = response.get("error") if response else "Unknown error during event creation"
                print(f"[ERROR] Failed to create calendar event: {error_msg}")
                return {"error": error_msg}
                
        except Exception as e:
            error_msg = f"Exception during calendar event creation: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {"error": error_msg}

    def _handle_calendar_search(self, parameters, original_query):
        """
        Handle calendar event searching with extracted parameters.
        Uses the existing search logic but with enhanced parameter processing.
        """
        print(f"[DEBUG] Handling calendar search with parameters: {parameters}")
        
        # Extract search parameters
        date_range = parameters.get("date_range")
        keywords = parameters.get("keywords", "")
        time_range = parameters.get("time_range")
        
        # Convert date_range to time_min/time_max
        time_min, time_max = None, None
        if date_range:
            time_min, time_max = self._extract_time_range(date_range.lower())
            print(f"[DEBUG] Date range '{date_range}' converted to time_min='{time_min}', time_max='{time_max}'")
        
        # Only use fallback keyword extraction if LLM analysis was incomplete (no date_range AND no keywords)
        # If LLM provided date_range but no keywords, that's intentional for date-only queries
        if (not keywords or not keywords.strip()) and (not date_range or not date_range.strip()):
            fallback_keywords = self._extract_search_terms(original_query)
            if fallback_keywords and fallback_keywords.strip():
                keywords = fallback_keywords
                print(f"[DEBUG] LLM analysis incomplete (no date_range or keywords), using fallback keywords from original query: '{keywords}'")
        elif date_range and (not keywords or not keywords.strip()):
            print(f"[DEBUG] LLM provided date_range='{date_range}' but no keywords - this is correct for date-only queries, skipping fallback")
        
        # Determine search method based on parameters
        search_context = {
            "date_range": date_range,
            "keywords": keywords,
            "time_min": time_min,
            "time_max": time_max,
            "original_query": original_query
        }
        
        if keywords and keywords.strip():
            # Use find_events for keyword-based search
            search_query = self._extract_search_terms(keywords)
            search_context["search_method"] = "find_events (keyword-based)"
            search_context["processed_keywords"] = search_query
            print(f"[DEBUG] Using find_events with query: '{search_query}'")
            result = self.find_events(
                query=search_query,
                time_min=time_min,
                time_max=time_max,
                max_results=20
            )
        elif time_min or time_max:
            # Use list_events for time-based search
            search_context["search_method"] = "list_events (time-based)"
            print(f"[DEBUG] Using list_events with time range: {time_min} to {time_max}")
            result = self.list_events(
                time_min=time_min,
                time_max=time_max,
                max_results=15
            )
        else:
            # No valid search method could be determined - return error for LLM to explain
            search_context["search_method"] = "none (unable to determine search criteria)"
            search_context["error"] = "Could not extract meaningful search criteria from the query"
            print(f"[DEBUG] No valid search method could be determined - returning error for LLM explanation")
            result = {
                "error": "Unable to determine search criteria",
                "data": {"items": []},
                "search_context": search_context
            }
        
        # Add search context to the result for error message generation
        if result and isinstance(result, dict):
            result["search_context"] = search_context
        
        return result

    def _process_calendar_query(self, user_query, thread_history=None):
        """
        DEPRECATED: Legacy method for backward compatibility.
        New code should use _process_calendar_intent() instead.
        """
        print(f"[WARNING] Using deprecated _process_calendar_query method. Consider migrating to _process_calendar_intent.")
        
        # For now, delegate to the new method to maintain functionality
        return self._process_calendar_intent(user_query, thread_history)

    def _extract_time_range(self, query_lower):
        """
        Extract time range from natural language query.
        Returns (time_min, time_max) as RFC3339 timestamps.
        """
        now = datetime.utcnow()
        
        if "today" in query_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat() + "Z", end.isoformat() + "Z"
            
        elif "tomorrow" in query_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat() + "Z", end.isoformat() + "Z"
            
        elif "this week" in query_lower:
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            start_of_week = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            return start_of_week.isoformat() + "Z", end_of_week.isoformat() + "Z"
            
        elif "next week" in query_lower:
            # Start of next week (Monday)
            days_since_monday = now.weekday()
            start_of_next_week = (now + timedelta(days=7-days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_next_week = start_of_next_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            return start_of_next_week.isoformat() + "Z", end_of_next_week.isoformat() + "Z"
            
        elif "this month" in query_lower:
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # Get last day of current month
            next_month = start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)
            end = next_month - timedelta(microseconds=1)
            return start.isoformat() + "Z", end.isoformat() + "Z"
        
        # Handle specific weekday names
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3, 
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for weekday_name, weekday_num in weekdays.items():
            if weekday_name in query_lower:
                current_weekday = now.weekday()
                
                # Calculate days until the target weekday
                if weekday_num >= current_weekday:
                    # Target weekday is today or later this week
                    days_until = weekday_num - current_weekday
                else:
                    # Target weekday is next week
                    days_until = 7 - current_weekday + weekday_num
                
                target_date = now + timedelta(days=days_until)
                start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                print(f"[DEBUG] Weekday '{weekday_name}' detected. Current: {current_weekday} ({now.strftime('%A')}), Target: {weekday_num} ({target_date.strftime('%A')}), Days until: {days_until}")
                return start.isoformat() + "Z", end.isoformat() + "Z"
        
        # Handle ISO date format (YYYY-MM-DD)
        import re
        iso_date_match = re.match(r'^(\d{4}-\d{2}-\d{2})$', query_lower.strip())
        if iso_date_match:
            date_str = iso_date_match.group(1)
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d')
                start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
                end = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
                
                print(f"[DEBUG] ISO date '{date_str}' detected. Converting to time range for {target_date.strftime('%A, %B %d, %Y')}")
                return start.isoformat() + "Z", end.isoformat() + "Z"
            except ValueError:
                print(f"[DEBUG] Invalid ISO date format: '{date_str}'")
                return None, None
            
        return None, None
    
    def _extract_search_terms(self, user_query):
        """
        Extract meaningful search terms from user query for event searching.
        """
        # Remove common calendar-related words and time indicators
        stop_words = {
            "show", "me", "my", "events", "meetings", "calendar", "find", "search",
            "today", "tomorrow", "this", "week", "month", "next", "on", "for",
            "about", "with", "regarding", "the", "and", "or", "in", "at"
        }
        
        # Split query into words and filter
        words = user_query.lower().split()
        meaningful_words = [word for word in words if word not in stop_words and len(word) > 2]
        
        return " ".join(meaningful_words) if meaningful_words else None

    def _build_simple_query(self, user_query):
        """
        Fallback method for simple query building when LLM is unavailable.
        """
        query_lower = user_query.lower()
        if "unread" in query_lower:
            return "is:unread"
        return ""

    def _extract_contact_search_term(self, user_query):
        """
        Extract the contact name or search term from a contact-related query.
        """
        query_lower = user_query.lower()
        
        # Remove common contact query prefixes and suffixes
        contact_stopwords = [
            "what's", "what", "is", "the", "email", "emails", "of", "for", 
            "contact", "info", "information", "details", "address", "phone",
            "number", "find", "search", "get", "show", "me", "tell", "about",
            "are", "all", "give", "provide", "list"
        ]
        
        # Split into words and filter out stopwords
        words = user_query.split()
        filtered_words = []
        
        for word in words:
            # Clean punctuation
            clean_word = word.strip("?.,!:;").lower()
            if clean_word not in contact_stopwords and len(clean_word) > 1:
                # Keep the original case for names
                filtered_words.append(word.strip("?.,!:;"))
        
        # Join the remaining words as the search term
        search_term = " ".join(filtered_words).strip()
        
        # Handle cases like "Dawid Tkocz" or "John Doe"
        if search_term:
            return search_term
        
        # Fallback: look for capitalized words (likely names)
        capitalized_words = [word for word in words if word and word[0].isupper()]
        if capitalized_words:
            return " ".join(capitalized_words)
        
        return None

    def process_query(self, query, thread_history=None):
        """
        Enhanced process_query that uses LLM-based classification and 2-stage approach for calendar processing.
        
        Stage 1: Classify intent (email, calendar, general)
        Stage 2: For calendar intent, use _process_calendar_intent for create vs search + parameter extraction
        """
        print(f"[DEBUG] Processing query with LLM classification: '{query}'")
        
        # Stage 1: Use LLM to classify the query with conversation context
        classification = self.classify_query_with_llm(query, thread_history)
        
        intent = classification.get("intent")
        confidence = classification.get("confidence", 0.0)
        reasoning = classification.get("reasoning", "")
        
        print(f"[DEBUG] LLM Classification Result:")
        print(f"  Intent: {intent}")
        print(f"  Confidence: {confidence}")
        print(f"  Reasoning: {reasoning}")
        
        # Stage 2: Process based on classified intent
        if intent == "email":
            # Use LLM to build intelligent Gmail query
            search_query = self.build_gmail_query_with_llm(query, thread_history)
            print(f"[DEBUG] Using Gmail query: '{search_query}'")
            response = self.get_recent_emails(query=search_query)
            
            # Store the actual Gmail query used for pagination (not the original user query)
            if response and isinstance(response, dict) and 'data' in response:
                response['original_gmail_query'] = search_query
            if response and isinstance(response, dict) and not response.get("error"):
                return {
                    "source_type": "mail",
                    "content": "Emails fetched.",
                    "data": response.get("data"),
                    "next_page_token": response.get("next_page_token"),
                    "total_estimate": response.get("total_estimate"),
                    "has_more": response.get("has_more")
                }
            else:
                error_msg = response.get("error") if response and isinstance(response, dict) else "Unknown error"
                return {"source_type": "mail", "content": f"I couldn't retrieve your emails: {error_msg}", "data": {"messages": []}}

        elif intent == "calendar":
            # Enhanced calendar processing using 2-stage approach
            print(f"[DEBUG] Using enhanced calendar processing with _process_calendar_intent")
            response = self._process_calendar_intent(query, thread_history)
            
            if response and isinstance(response, dict) and not response.get("error"):
                # Check if this is a creation response (has action_performed field)
                if response.get("action_performed") == "create":
                    # This is a calendar creation response
                    event_details = response.get("event_details", {})
                    print(f"[DEBUG] Calendar event creation successful, returning creation confirmation")
                    return {
                        "source_type": "google-calendar",
                        "content": f"Successfully created calendar event '{event_details.get('title', 'Untitled')}' for {event_details.get('date', 'unknown date')} at {event_details.get('start_time', 'unknown time')}",
                        "data": {"created_event": response.get("data", {}), "action": "create"}
                    }
                
                # Handle search/list responses
                elif "data" in response:
                    calendar_data = response.get("data", {})
                    
                    # Check if this is a creation response without action_performed (fallback)
                    if isinstance(calendar_data, dict) and "id" in calendar_data and "items" not in calendar_data:
                        # This is a single event creation response (fallback detection)
                        print(f"[DEBUG] Calendar event creation successful (fallback detection), event ID: {calendar_data.get('id')}")
                        return {
                            "source_type": "google-calendar",
                            "content": "Calendar event created successfully.",
                            "data": {"created_event": calendar_data, "action": "create"}
                        }
                    else:
                        # This is a search response (should have 'items' array)
                        result_data = {
                            "source_type": "google-calendar", 
                            "content": "Events fetched.",
                            "data": calendar_data
                        }
                        # Pass through search context if available
                        if "search_context" in response:
                            result_data["search_context"] = response["search_context"]
                        return result_data
                else:
                    # Response has no data field, treat as error
                    error_msg = "No data in calendar response"
                    print(f"[ERROR] {error_msg}")
                    return {"source_type": "google-calendar", "content": f"I couldn't process your calendar request: {error_msg}", "data": {"items": []}}
            else:
                error_msg = response.get("error") if response and isinstance(response, dict) else "Unknown error"
                print(f"[ERROR] Calendar processing failed: {error_msg}")
                
                # Check if this is a search criteria error that should be explained by LLM
                if response and response.get("search_context"):
                    return {
                        "source_type": "google-calendar", 
                        "content": "Events fetched.",
                        "data": {"items": []},
                        "search_context": response.get("search_context")
                    }
                else:
                    return {"source_type": "google-calendar", "content": f"I couldn't process your calendar request: {error_msg}", "data": {"items": []}}
        
        elif intent == "contact":
            # Handle contact searches
            print(f"[DEBUG] Processing contact search query")
            
            # Extract contact name/search term from the query
            search_term = self._extract_contact_search_term(query)
            print(f"[DEBUG] Extracted contact search term: '{search_term}'")
            
            if search_term:
                # Import ContactSyncService here to avoid circular imports
                try:
                    from services.contact_service import ContactSyncService
                    contact_service = ContactSyncService()
                    
                    # Search for contacts
                    contacts = contact_service.search_contacts(search_term, limit=10)
                    print(f"[DEBUG] Found {len(contacts)} matching contacts")
                    
                    # Convert ObjectIds to strings to prevent JSON serialization errors
                    def convert_objectid_to_str(obj):
                        if isinstance(obj, ObjectId):
                            return str(obj)
                        elif isinstance(obj, dict):
                            return {k: convert_objectid_to_str(v) for k, v in obj.items()}
                        elif isinstance(obj, list):
                            return [convert_objectid_to_str(item) for item in obj]
                        return obj
                    
                    processed_contacts = [convert_objectid_to_str(contact) for contact in contacts]
                    
                    return {
                        "source_type": "contact",
                        "content": f"Found {len(processed_contacts)} contact(s) matching '{search_term}'",
                        "data": {"contacts": processed_contacts, "search_term": search_term}
                    }
                except Exception as e:
                    print(f"[ERROR] Contact search failed: {str(e)}")
                    return {
                        "source_type": "contact", 
                        "content": f"I couldn't search for contacts: {str(e)}", 
                        "data": {"contacts": []}
                    }
            else:
                return {
                    "source_type": "contact", 
                    "content": "I couldn't understand what contact you're looking for. Please specify a name or email address.", 
                    "data": {"contacts": []}
                }
        
        # For general queries, return None to let the main system handle it
        print(f"[DEBUG] Query classified as 'general' - no tool processing needed")
        return None 