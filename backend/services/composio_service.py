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

    def _execute_action(self, action: Action, params: dict = None):
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

    def get_recent_emails(self, count=25, query=None, **kwargs):
        """
        Get recent emails using the GMAIL_FETCH_EMAILS action.
        """
        response = self._execute_action(
            action=Action.GMAIL_FETCH_EMAILS,
            params={"query": query or "", "max_results": count}
        )
        # The new action returns data directly, not nested
        return {"data": {"messages": response.get("data", [])}} if response.get("successful") else {"error": response.get("error")}

    def get_email_details(self, email_id):
        # This action might need adjustment based on the new SDK version
        response = self._execute_action(
            action=Action.GMAIL_GET_EMAIL,
            params={"message_id": email_id, "format": "full"}
        )
        if response.get("successful"):
            email_data = response.get("data", {})
            payload = email_data.get("payload", {})
            html_content = ""
            if payload.get("mimeType") == "text/html":
                body_data = payload.get("body", {}).get("data")
                if body_data:
                    html_content = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
            elif "parts" in payload:
                for part in payload.get("parts", []):
                    if part.get("mimeType") == "text/html":
                        body_data = part.get("body", {}).get("data")
                        if body_data:
                            html_content = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                            break
            return html_content or email_data.get("snippet", "")
        return None

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
                    "data": response.get("data")
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