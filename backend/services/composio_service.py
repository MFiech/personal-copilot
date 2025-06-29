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
        time_min = datetime.utcnow().isoformat() + "Z"
        time_max = (datetime.utcnow() + timedelta(days=days)).isoformat() + "Z"
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_GET_EVENTS,
            params={"calendarId": "primary", "maxResults": max_results, "timeMin": time_min, "timeMax": time_max}
        )
        return {"data": {"items": response.get("data", [])}} if response.get("successful") else {"error": response.get("error")}

    def create_calendar_event(self, summary, start_time, end_time, location=None, description=None, attendees=None, calendar_id="primary"):
        attendee_emails = []
        if attendees:
            for att in attendees:
                attendee_emails.append(att['email'] if isinstance(att, dict) else att)
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_CREATE_EVENT,
            params={
                "calendar_id": calendar_id, "summary": summary, "start_time": start_time, "end_time": end_time,
                "description": description, "location": location, "attendees": attendee_emails
            }
        )
        return {"data": response.get("data", {})} if response.get("successful") else {"error": response.get("error")}

    def update_calendar_event(self, event_id, summary=None, start_time=None, end_time=None, location=None, description=None, attendees=None, calendar_id="primary"):
        """
        Update a calendar event using Composio's GOOGLECALENDAR_UPDATE_EVENT tool.
        """
        arguments = {"event_id": event_id, "calendar_id": calendar_id}
        if summary: arguments["summary"] = summary
        if start_time: arguments["start_time"] = start_time
        if end_time: arguments["end_time"] = end_time
        if description: arguments["description"] = description
        if location: arguments["location"] = location
        if attendees:
            attendee_emails = [att['email'] for att in attendees if isinstance(att, dict) and 'email' in att]
            arguments["attendees"] = attendee_emails

        try:
            execution_details = self._execute_action(
                action=Action.GOOGLECALENDAR_UPDATE_EVENT,
                params=arguments
            )
            if execution_details and execution_details.get("successful"):
                return {"data": execution_details.get("data", {})}
            else:
                return {"error": execution_details.get("error", "Unknown error")}
        except Exception as e:
            return {"error": str(e)}
            
    def delete_calendar_event(self, event_id, calendar_id="primary"):
        """
        Delete a calendar event using Composio's GOOGLECALENDAR_DELETE_EVENT tool.
        """
        try:
            execution_details = self._execute_action(
                action=Action.GOOGLECALENDAR_DELETE_EVENT,
                params={
                    "event_id": event_id,
                    "calendar_id": calendar_id
                }
            )
            return execution_details and execution_details.get("successful", False)
        except Exception as e:
            print(f"Error deleting calendar event via Composio: {e}")
            return False

    def get_events_for_date(self, date=None):
        """
        Get calendar events for a specific date using Composio.
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

        try:
            execution_details = self._execute_action(
                action=Action.GOOGLECALENDAR_GET_EVENTS,
                params={
                    "calendar_id": "primary",
                    "time_min": time_min,
                    "time_max": time_max
                }
            )
            if execution_details and execution_details.get("successful"):
                events = execution_details.get("data", [])
                return {"data": {"items": events}}
            else:
                return {"error": execution_details.get("error", "Unknown error")}
        except Exception as e:
            return {"error": str(e)}

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
            response = self.get_upcoming_events()
            if response and not response.get("error"):
                 return {
                    "source_type": "google-calendar",
                    "content": "Events fetched.",
                    "data": response.get("data")
                }
            else:
                 return {"source_type": "google-calendar", "content": f"I couldn't retrieve your events: {response.get('error')}", "data": {"items": []}}
            
        return None 