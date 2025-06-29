from composio.client.enums import Action
from composio.tools import ComposioToolSet
from datetime import datetime, timedelta
import base64

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
        Uses date-based chronological pagination instead of pageToken for consistent ordering.
        """
        # For chronological pagination, we use date-based queries instead of pageToken
        # pageToken doesn't guarantee chronological order across pages
        
        params = {
            "max_results": count
        }
        
        # Build query for chronological pagination
        search_query = query or ""
        
        # If page_token is provided, it's actually a date string for "before:" query
        if page_token:
            # page_token contains the date of the oldest email from previous batch
            if search_query:
                search_query = f"{search_query} before:{page_token}"
            else:
                search_query = f"before:{page_token}"
        
        params["query"] = search_query
            
        response = self._execute_action(
            action=Action.GMAIL_FETCH_EMAILS,
            params=params
        )
        
        if response.get("successful"):
            data = response.get("data", {})
            messages = data.get("messages", [])
            
            # For chronological pagination, we need to find the oldest email date
            # to use as the "before:" date for the next page
            next_page_token = None
            if messages and len(messages) == count:
                # Find the oldest email date from this batch
                oldest_date = None
                for message in messages:
                    # Try to get date from various possible fields
                    date_str = (message.get("messageTimestamp") or 
                              message.get("date") or 
                              message.get("internalDate"))
                    
                    if date_str:
                        try:
                            # Convert to Gmail search format (YYYY/MM/DD)
                            if date_str.isdigit():
                                # Unix timestamp in milliseconds
                                import datetime
                                timestamp_ms = int(date_str)
                                date_obj = datetime.datetime.fromtimestamp(timestamp_ms / 1000)
                            else:
                                # Try to parse ISO format or other formats
                                from utils.date_parser import parse_email_date
                                date_obj = parse_email_date(date_str)
                            
                            if date_obj:
                                gmail_date = date_obj.strftime("%Y/%m/%d")
                                if oldest_date is None or gmail_date < oldest_date:
                                    oldest_date = gmail_date
                        except Exception as e:
                            print(f"[DEBUG] Error parsing date {date_str}: {e}")
                            continue
                
                # Use the oldest date as the next page token for "before:" query
                next_page_token = oldest_date
            
            # Estimate total - we can't get exact total with date-based pagination
            result_size_estimate = data.get("resultSizeEstimate", len(messages))
            
            return {
                "data": data,
                "next_page_token": next_page_token,
                "total_estimate": result_size_estimate,
                "has_more": bool(next_page_token and len(messages) == count)
            }
        else:
            return {"error": response.get("error")}

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

    def process_query(self, query, thread_history=None):
        query_lower = query.lower()
        email_keywords = ["email", "mail", "gmail"]
        calendar_keywords = ["calendar", "event", "meeting"]

        if any(keyword in query_lower for keyword in email_keywords):
            search_query = "is:unread" if "unread" in query_lower else ""
            response = self.get_recent_emails(query=search_query)
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