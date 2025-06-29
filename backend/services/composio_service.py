from composio.client.enums import Action
from composio.tools import ComposioToolSet
from datetime import datetime, timedelta
import base64
import openai
import os

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
        
        # Build parameters following Composio schema
        params = {
            "calendarId": calendar_id,  # Using camelCase as per schema
            "summary": summary,
            "start": {"dateTime": start_time},  # Structured format
            "end": {"dateTime": end_time}
        }
        
        # Add optional parameters
        if description:
            params["description"] = description
        if location:
            params["location"] = location
        if attendee_emails:
            params["attendees"] = [{"email": email} for email in attendee_emails]
        
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_CREATE_EVENT,
            params=params
        )
        
        if response and response.get("successful"):
            return {"data": response.get("data", {})}
        else:
            return {"error": response.get("error") if response else "No response received"}

    def update_calendar_event(self, event_id, summary=None, start_time=None, end_time=None, location=None, description=None, attendees=None, calendar_id="primary"):
        """
        Update a calendar event using enhanced parameter structure.
        """
        # Build parameters with proper schema structure
        params = {
            "calendarId": calendar_id,  # Using camelCase as per schema
            "eventId": event_id
        }
        
        # Add optional parameters with proper structure
        if summary: 
            params["summary"] = summary
        if start_time: 
            params["start"] = {"dateTime": start_time}
        if end_time: 
            params["end"] = {"dateTime": end_time}
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
    
    def _process_calendar_query(self, user_query, thread_history=None):
        """
        Intelligently process calendar queries to determine the best method and parameters.
        
        Args:
            user_query: The user's natural language query
            thread_history: Previous conversation context
            
        Returns:
            Response from appropriate calendar method
        """
        query_lower = user_query.lower()
        
        # Check for specific search terms that would benefit from find_events()
        search_indicators = [
            "find", "search", "show me", "with", "about", "regarding", 
            "meeting with", "call with", "project", "client"
        ]
        
        # Check for time period specifications
        time_indicators = [
            "today", "tomorrow", "this week", "next week", "this month", "next month",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"
        ]
        
        # Determine time range if specified
        time_min, time_max = self._extract_time_range(query_lower)
        
        # If there are search terms, use find_events for better results
        if any(indicator in query_lower for indicator in search_indicators):
            # Extract search query (remove time indicators and common words)
            search_query = self._extract_search_terms(user_query)
            return self.find_events(
                query=search_query,
                time_min=time_min,
                time_max=time_max,
                max_results=20  # More results for search queries
            )
        
        # For general time-based queries, use list_events
        elif any(indicator in query_lower for indicator in time_indicators) or time_min or time_max:
            return self.list_events(
                time_min=time_min,
                time_max=time_max,
                max_results=15
            )
        
        # Default: show upcoming events
        else:
            return self.get_upcoming_events()
    
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

    def process_query(self, query, thread_history=None):
        query_lower = query.lower()
        email_keywords = ["email", "mail", "gmail"]
        calendar_keywords = ["calendar", "event", "meeting"]

        if any(keyword in query_lower for keyword in email_keywords):
            # Use LLM to build intelligent Gmail query
            search_query = self.build_gmail_query_with_llm(query, thread_history)
            print(f"[DEBUG] Using Gmail query: '{search_query}'")
            response = self.get_recent_emails(query=search_query)
            
            # Store the actual Gmail query used for pagination (not the original user query)
            if response and 'data' in response:
                response['original_gmail_query'] = search_query
            if response and not response.get("error"):
                 return {
                    "source_type": "mail",
                    "content": "Emails fetched.",
                    "data": response.get("data"),
                    "next_page_token": response.get("next_page_token"),
                    "total_estimate": response.get("total_estimate"),
                    "has_more": response.get("has_more")
                }
            else:
                return {"source_type": "mail", "content": f"I couldn't retrieve your emails: {response.get('error')}", "data": {"messages": []}}

        if any(keyword in query_lower for keyword in calendar_keywords):
            # Enhanced calendar query processing
            response = self._process_calendar_query(query, thread_history)
            if response and not response.get("error"):
                 return {
                    "source_type": "google-calendar",
                    "content": "Events fetched.",
                    "data": response.get("data")
                }
            else:
                 return {"source_type": "google-calendar", "content": f"I couldn't retrieve your events: {response.get('error')}", "data": {"items": []}}
            
        return None 