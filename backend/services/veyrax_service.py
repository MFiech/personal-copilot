import os
import requests
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
import html

# Load environment variables
load_dotenv()
VEYRAX_API_KEY = os.getenv('VEYRAX_API_KEY')
VEYRAX_API_URL = "https://veyraxapp.com"

class VeyraXService:
    """
    Service to interact with VeyraX API for accessing Gmail and Google Calendar.
    """
    
    def __init__(self, api_key=None):
        """Initialize with API key from env or passed directly."""
        self.api_key = api_key or VEYRAX_API_KEY
        if not self.api_key:
            raise ValueError("VeyraX API key is required. Set VEYRAX_API_KEY in .env file.")
        
        # Headers according to VeyraX documentation
        self.headers = {
            "VEYRAX_API_KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Tool availability flags - initialize as empty
        self.available_tools = {}
        
        # Check API connection and available tools on initialization
        self.check_auth()
    
    def check_auth(self):
        """Check if the API key is valid and discover available tools and methods."""
        try:
            # Try the mail test connection to check if mail is available
            mail_response = requests.post(
                f"{VEYRAX_API_URL}/mail/test_connection",
                headers=self.headers,
                json={}
            )
            
            if mail_response.status_code == 200:
                print("VeyraX API connection successful (mail test)")
                self.available_tools["mail"] = True
                
            # Try listing calendars to check if google-calendar is available
            calendar_response = requests.post(
                f"{VEYRAX_API_URL}/google-calendar/list_calendars",
                headers=self.headers,
                json={}
            )
            
            if calendar_response.status_code == 200:
                print("Google Calendar is available")
                self.available_tools["google-calendar"] = True
            
            # Check if we have at least one working tool
            if not self.available_tools:
                print(f"Warning: No VeyraX tools are available. Please check your account and permissions.")
                return False
                
            return True
        except requests.RequestException as e:
            print(f"Warning: VeyraX API connection check failed: {e}")
            return False
    
    def post_request(self, endpoint, payload=None):
        """
        Make a POST request to the VeyraX API.
        
        Args:
            endpoint (str): The API endpoint
            payload (dict): The JSON payload for the request
            
        Returns:
            dict: Response from the API or error message
        """
        if payload is None:
            payload = {}
            
        try:
            url = f"{VEYRAX_API_URL}{endpoint}"
            print(f"Calling VeyraX API: {url}")
            print(f"Payload: {json.dumps(payload)}")
            
            response = requests.post(
                url,
                headers=self.headers,
                json=payload
            )
            
            # Print response for debugging
            print(f"Response status: {response.status_code}")
            print(f"Response preview: {response.text[:200] if response.text else 'Empty response'}")
                
            # Even if status code is not 200, return the response data if possible
            try:
                data = response.json()
                
                # If there's an error in the response, format it consistently
                if response.status_code >= 400:
                    return {
                        "error": data.get("message", f"API error: {response.status_code}"),
                        "status_code": response.status_code,
                        "raw_response": data
                    }
                return data
            except ValueError:
                if response.status_code >= 400:
                    return {
                        "error": f"API error: {response.status_code}",
                        "status_code": response.status_code,
                        "raw_response": response.text
                    }
                return {"data": response.text}
            
        except requests.RequestException as e:
            error_msg = str(e)
            print(f"Error calling {endpoint}: {error_msg}")
            
            return {
                "error": error_msg,
                "status_code": getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            }
    
    # Gmail/Mail specific methods
    def get_recent_emails(self, count=25, query=None, folder="INBOX", offset=0, mark_as_read=False, from_date=None, to_date=None):
        """
        Get recent emails from Gmail.
        
        Args:
            count (int): Number of emails to fetch
            query (str): Gmail search query (optional)
            folder (str): Folder to fetch emails from (default: INBOX)
            offset (int): Number of messages to skip
            mark_as_read (bool): Mark fetched messages as read
            from_date (str): Filter messages sent on or after this date (format: YYYY-MM-DD)
            to_date (str): Filter messages sent on or before this date (format: YYYY-MM-DD)
            
        Returns:
            dict: Email data or error message
        """
        # Parameter format per documentation
        params = {
            "limit": count,
            "folder": folder,
            "offset": offset,
            "mark_as_read": mark_as_read
        }
        
        if query:
            params["search_query"] = query
            
        if from_date:
            params["from_date"] = from_date
            
        if to_date:
            params["to_date"] = to_date
            
        # Use the correct endpoint from documentation
        return self.post_request("/mail/get_messages", params)
    
    def get_email_message(self, message_id, mark_as_read=False):
        """
        Get a specific email message.
        
        Args:
            message_id (str): ID of the message to retrieve
            mark_as_read (bool): Whether to mark the message as read
            
        Returns:
            dict: Email message data or error message
        """
        params = {
            "message_id": message_id,
            "mark_as_read": mark_as_read
        }
        
        return self.post_request("/mail/get_message", params)
    
    def get_email_details(self, email_id):
        """
        Get the full details of an email, including HTML content.
        
        Args:
            email_id (str): ID of the email to retrieve
            
        Returns:
            str: HTML content of the email, or plain text if HTML is not available
        """
        try:
            # Log the ID being used
            print(f"Attempting to get details for email_id: {email_id}")

            # Get the full email message
            response = self.get_email_message(email_id)

            # Log the raw response from get_email_message
            print(f"Raw response from get_email_message for ID {email_id}: {response}")

            if "error" in response:
                print(f"Error retrieving email details for ID {email_id}: {response['error']}")
                return None
            
            # Extract email content - prefer HTML content if available
            if "data" in response and "message" in response["data"]:
                message = response["data"]["message"]
                
                # Try to get HTML content first
                html_content = message.get("htmlBody", "")
                if html_content:
                    return html_content
                
                # Fall back to plain text
                text_content = message.get("textBody", "")
                if text_content:
                    return text_content
                
                # If neither is available, try to construct a basic representation
                subject = message.get("subject", "No Subject")
                sender = message.get("from", {}).get("email", "Unknown Sender")
                sender_name = message.get("from", {}).get("name", sender)
                date = message.get("date", "Unknown Date")
                
                # Create a basic representation
                basic_content = f"From: {sender_name} <{sender}>\nDate: {date}\nSubject: {subject}\n\n"
                basic_content += "This email doesn't contain any text content."
                
                return basic_content
                
            return "Email content not available"
            
        except Exception as e:
            print(f"Error in get_email_details: {str(e)}")
            return None
    
    def send_email(self, to, subject, body_text=None, body_html=None, cc=None, bcc=None):
        """
        Send an email.
        
        Args:
            to (list/str): Recipient email addresses (can be list of dicts, list of strings, or single string)
            subject (str): Email subject
            body_text (str): Plain text email body
            body_html (str): HTML email body
            cc (list/str): CC recipients (can be list of dicts, list of strings, or single string)
            bcc (list/str): BCC recipients (can be list of dicts, list of strings, or single string)
            
        Returns:
            dict: Response data or error message
        """
        # Helper function to parse email address format "Name <email@example.com>"
        def parse_email(email_str):
            if not isinstance(email_str, str):
                return email_str
            
            # Match pattern like "Name <email@example.com>"
            match = re.match(r'(.*?)\s*<([^>]+)>', email_str)
            if match:
                name = match.group(1).strip()
                email = match.group(2).strip()
                return {"email": email, "name": name}
            
            # If it's just an email address
            if '@' in email_str:
                # Extract a proper name from the email instead of duplicating the email
                name_part = email_str.split('@')[0]
                # Convert to proper case and replace dots/underscores with spaces
                name = name_part.replace('.', ' ').replace('_', ' ').title()
                return {"email": email_str, "name": name}
            
            # If no email pattern found
            return {"email": email_str, "name": "Recipient"}
            
        # Process main recipient(s)
        if isinstance(to, str):
            to = [parse_email(to)]
        elif isinstance(to, list):
            to = [parse_email(item) if isinstance(item, str) else item for item in to]
        
        # Process CC recipient(s)
        if isinstance(cc, str):
            cc = [parse_email(cc)]
        elif isinstance(cc, list):
            cc = [parse_email(item) if isinstance(item, str) else item for item in cc]
            
        # Process BCC recipient(s)
        if isinstance(bcc, str):
            bcc = [parse_email(bcc)]
        elif isinstance(bcc, list):
            bcc = [parse_email(item) if isinstance(item, str) else item for item in bcc]
        
        # Handle encoding for non-ASCII content
        if subject and any(ord(c) > 127 for c in subject):
            # Use ASCII-friendly version for non-ASCII subject
            ascii_subject = ''.join(c if ord(c) < 128 else '?' for c in subject)
            subject = ascii_subject
        
        # Create the parameters with explicit encoding information
        params = {
            "to": to,
            "subject": subject,
            "headers": {
                "Content-Type": "text/plain; charset=UTF-8"
            }
        }
        
        # Handle body text with potential special characters
        if body_text:
            # If body contains non-ASCII characters, use HTML version as well
            if any(ord(c) > 127 for c in body_text):
                # Create a simple HTML version with proper encoding
                if not body_html:
                    body_html = f"<html><body><pre>{html.escape(body_text)}</pre></body></html>"
                params["body_html"] = body_html
            params["body_text"] = body_text
        elif body_html:
            params["body_html"] = body_html
            
        if cc:
            params["cc"] = cc
        if bcc:
            params["bcc"] = bcc
            
        return self.post_request("/mail/send_message", params)
    
    def get_email_folders(self, include_counts=False):
        """
        Get email folders.
        
        Returns:
            dict: Folder data or error message
        """
        # The API doesn't support the include_counts parameter based on the error messages
        # Try to get folders without any parameters
        result = self.post_request("/mail/get_folders", {})
        
        # Check if the response indicates a specific error about include_counts
        # If the error message is about include_counts but we didn't send that parameter,
        # it may be a server-side issue with the endpoint
        if "error" in result:
            error_msg = result.get("error", "")
            if "include_counts" in error_msg and not include_counts:
                # Fall back to get_messages and extract folder info
                emails = self.get_recent_emails(count=1)
                if "error" not in emails and "data" in emails and "messages" in emails["data"]:
                    messages = emails["data"]["messages"]
                    if messages:
                        # Extract folder names from the first message
                        folders = []
                        # Add the folder from the first message
                        folder = messages[0].get("folder", "INBOX")
                        folders.append({"name": folder, "message_count": len(messages)})
                        
                        # Always include INBOX if it's not already there
                        if folder != "INBOX":
                            folders.append({"name": "INBOX", "message_count": None})
                            
                        # Common Gmail folders to include
                        for common_folder in ["Sent", "Drafts", "Trash", "Spam"]:
                            if folder != common_folder:
                                folders.append({"name": common_folder, "message_count": None})
                        
                        return {
                            "data": {
                                "folders": folders
                            }
                        }
        
        return result
    
    def test_mail_connection(self):
        """
        Test connection to SMTP and IMAP servers.
        
        Returns:
            dict: Connection test results or error message
        """
        return self.post_request("/mail/test_connection", {})
    
    def delete_email(self, message_id, folder="INBOX", permanently=False):
        """
        Delete an email from Gmail.
        
        Args:
            message_id (str): ID of the message to delete
            folder (str): Folder containing the message (default: "INBOX")
            permanently (bool): Whether to permanently delete the message (default: False)
            
        Returns:
            bool: True if deletion was successful, False otherwise
        """
        try:
            if not message_id:
                print("Error: No message_id provided")
                return False
                
            print(f"Calling VeyraX API to delete email with ID: {message_id}")
            
            payload = {
                "message_id": message_id,
                "folder": folder,
                "permanently": permanently
            }
            print(f"Delete email request payload: {payload}")
            print(f"Delete email API endpoint: /mail/delete_message")
            
            response = self.post_request("/mail/delete_message", payload)
            print(f"VeyraX API Delete Response (raw): {response}")
            
            # Enhanced response validation
            if not response:
                print("Error: Empty response from VeyraX API")
                return False
                
            if isinstance(response, dict):
                # Check for error objects
                if "error" in response:
                    error_msg = response.get("error")
                    print(f"VeyraX API Error: {error_msg}")
                    return False
                    
                # Check for success flag in data object according to VeyraX API documentation
                if "data" in response and response["data"].get("success", False):
                    print(f"Successfully deleted email with ID: {message_id}")
                    return True
                else:
                    error_msg = response.get("message", "Unknown error")
                    print(f"Failed to delete email: {error_msg}")
                    # Print full response for debugging
                    print(f"Full response content: {response}")
                    return False
            else:
                print(f"Invalid response format: {type(response)}")
                print(f"Response content: {response}")
                return False
                
        except Exception as e:
            print(f"Exception while deleting email: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    # Google Calendar specific methods
    def get_upcoming_events(self, days=7, max_results=10):
        """
        Get upcoming calendar events.
        
        Args:
            days (int): Number of days to look ahead
            max_results (int): Maximum number of events to return
            
        Returns:
            dict: Calendar event data or error message
        """
        now = datetime.now()
        after_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        before_date = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {
            "filters": {
                "after_date": after_date,
                "before_date": before_date,
                "max_results": max_results,
                "calendarId": "michal.fiech@gmail.com"
            }
        }
        return self.post_request("/google-calendar/list_events", params)
    
    def get_calendar_event(self, event_id, calendar_id="michal.fiech@gmail.com"):
        """
        Get details of a specific calendar event.
        
        Args:
            event_id (str): ID of the event to retrieve
            calendar_id (str): ID of the calendar (default: primary)
            
        Returns:
            dict: Event data or error message
        """
        params = {
            "event_id": event_id,
            "calendar_id": calendar_id
        }
        return self.post_request("/google-calendar/get_event", params)
    
    def create_calendar_event(self, summary, start_time, end_time, location=None, description=None, attendees=None, calendar_id="michal.fiech@gmail.com"):
        """
        Create a new calendar event.
        
        Args:
            summary (str): Event title
            start_time (str): Start time in RFC 3339 format (e.g., "2023-06-15T09:00:00Z")
            end_time (str): End time in RFC 3339 format
            location (str): Event location
            description (str): Event description
            attendees (list): List of attendees (dict with 'email')
            calendar_id (str): ID of the calendar (default: primary)
            
        Returns:
            dict: Created event data or error message
        """
        params = {
            "event": {
                "summary": summary,
                "start": {"dateTime": start_time},
                "end": {"dateTime": end_time}
            },
            "calendar_id": calendar_id
        }
        
        if location:
            params["event"]["location"] = location
        if description:
            params["event"]["description"] = description
        if attendees:
            params["event"]["attendees"] = attendees
        
        return self.post_request("/google-calendar/create_event", params)
    
    def list_calendars(self):
        """
        List all available calendars.
        
        Returns:
            dict: Calendar list data or error message
        """
        return self.post_request("/google-calendar/list_calendars", {})
    
    def _parse_date_string(self, date_str):
        """
        Convert common date strings like 'tomorrow', 'today' to YYYY-MM-DD format.
        
        Args:
            date_str (str): Date string to parse
            
        Returns:
            str: Date in YYYY-MM-DD format
        """
        today = datetime.now()
        
        if date_str is None:
            return today.strftime("%Y-%m-%d")
        
        date_str = str(date_str).lower()
        
        if date_str == "today":
            return today.strftime("%Y-%m-%d")
        elif date_str == "tomorrow":
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_str == "yesterday":
            return (today - timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_str.startswith("next"):
            # Handle "next monday", "next week", etc.
            if "week" in date_str:
                return (today + timedelta(days=7)).strftime("%Y-%m-%d")
            elif "month" in date_str:
                # Add roughly a month
                next_month = today.replace(month=today.month + 1) if today.month < 12 else today.replace(year=today.year + 1, month=1)
                return next_month.strftime("%Y-%m-%d")
            
        # If we can't parse it as a special term, return it as is
        return date_str
        
    def get_events_for_date(self, date=None):
        """
        Get calendar events for a specific date.
        
        Args:
            date (str): Date in 'YYYY-MM-DD' format, or natural language like 'tomorrow' (defaults to today)
            
        Returns:
            dict: Calendar event data or error message
        """
        date = self._parse_date_string(date)
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            time_min = date_obj.replace(hour=0, minute=0, second=0).strftime("%Y-%m-%dT%H:%M:%SZ")
            time_max = date_obj.replace(hour=23, minute=59, second=59).strftime("%Y-%m-%dT%H:%M:%SZ")
            params = {
                "filters": {
                    "after_date": time_min,
                    "before_date": time_max,
                    "calendarId": "michal.fiech@gmail.com"
                }
            }
            return self.post_request("/google-calendar/list_events", params)
        except ValueError as e:
            print(f"Error parsing date {date}: {e}")
            return {"error": f"Invalid date format: {date}. Please use YYYY-MM-DD format."}
    
    def summarize_emails(self, emails):
        """
        Format emails for easy reading.
        
        Returns:
            tuple: (formatted_summary, email_ids_dict) where email_ids_dict maps display numbers to message IDs
        """
        try:
            print(f"Summarizing emails: {type(emails)} - {len(emails) if isinstance(emails, list) else '(not a list)'}")
            
            if not emails:
                print("No emails to summarize")
                return "No emails found.", {}
                
            if isinstance(emails, dict) and "error" in emails:
                error_msg = emails.get("error", "Unknown error")
                print(f"Error in emails data: {error_msg}")
                if "not available" in error_msg:
                    return f"I couldn't access your Gmail account. {error_msg}", {}
                elif "Authentication error" in error_msg:
                    return "I couldn't access your Gmail account. Please make sure your Gmail account is connected in VeyraX and try again.", {}
                else:
                    return f"I couldn't retrieve your emails: {error_msg}", {}
            
            # Handle different response formats
            if isinstance(emails, dict) and "messages" in emails:
                print("Found messages directly in dict")
                emails = emails.get("messages", [])
            elif isinstance(emails, dict) and "data" in emails and "messages" in emails.get("data", {}):
                print("Found messages in data.messages")
                emails = emails.get("data", {}).get("messages", [])
            
            # Debug output
            print(f"Processing {len(emails)} email messages")
            if emails and len(emails) > 0:
                print(f"First email structure: {json.dumps(emails[0], default=str)}")
            
            # Store message IDs with their display numbers
            email_ids_dict = {}
            
            summary = []
            for i, email in enumerate(emails[:10], 1):  # Limit to 10 emails
                # Store the message ID with its display number
                message_id = email.get("id")
                if message_id:
                    email_ids_dict[str(i)] = message_id
                    
                # Get sender information - try different field names that might be used
                sender_email = None
                sender_name = None
                
                # Try the from_email structure
                if "from_email" in email:
                    sender_email = email.get("from_email", {}).get("email", "Unknown Sender")
                    sender_name = email.get("from_email", {}).get("name", "")
                # Try the from structure
                elif "from" in email:
                    if isinstance(email["from"], dict):
                        sender_email = email["from"].get("email", "Unknown Sender")
                        sender_name = email["from"].get("name", "")
                    elif isinstance(email["from"], str):
                        sender_email = email["from"]
                # Try the sender structure
                elif "sender" in email:
                    if isinstance(email["sender"], dict):
                        sender_email = email["sender"].get("email", "Unknown Sender")
                        sender_name = email["sender"].get("name", "")
                    elif isinstance(email["sender"], str):
                        sender_email = email["sender"]
                
                # Use name if available, otherwise use email
                sender = sender_name if sender_name else (sender_email or "Unknown Sender")
                
                # Get subject and date with fallbacks
                subject = email.get("subject", "No Subject")
                date_str = email.get("date", email.get("timestamp", "Unknown Date"))
                
                # Format the date into a readable timestamp
                formatted_date = date_str
                try:
                    # Try different date formats
                    date_formats = [
                        "%a, %d %b %Y %H:%M:%S %z",  # RFC 2822 format with timezone
                        "%a, %d %b %Y %H:%M:%S %Z",  # RFC 2822 format with named timezone
                        "%Y-%m-%dT%H:%M:%S%z",       # ISO 8601 format
                        "%Y-%m-%dT%H:%M:%S.%f%z",    # ISO 8601 with microseconds
                        "%Y-%m-%d %H:%M:%S"          # Simple format
                    ]
                    
                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            break
                        except (ValueError, TypeError):
                            continue
                    
                    if parsed_date:
                        formatted_date = parsed_date.strftime("%B %d, %Y at %I:%M %p")
                    else:
                        # If we couldn't parse with any format, use as is
                        formatted_date = date_str
                except Exception as date_error:
                    print(f"Error parsing date: {date_error}")
                    formatted_date = date_str
                
                # Format the email entry in the requested format
                summary.append(f"{i}. {sender}, {subject}, {formatted_date}")
            
            if not summary:
                return "No emails found.", {}
            
            result = "\n".join(summary)
            print(f"Email summary: {result}")
            return result, email_ids_dict
        except Exception as e:
            print(f"Error summarizing emails: {e}")
            import traceback
            print(f"Summarize emails traceback: {traceback.format_exc()}")
            # Return a safe fallback message
            return "I was able to access your emails, but encountered an error formatting them. Please try a more specific query.", {}
    
    def summarize_calendar_events(self, events):
        """Format calendar events for easy reading."""
        try:
            if not events or "error" in events:
                error_msg = events.get("error", "Unknown error") if isinstance(events, dict) else "Unknown error"
                if "not available" in error_msg:
                    return f"I couldn't access your Google Calendar. {error_msg}"
                elif "Authentication error" in error_msg:
                    return "I couldn't access your Google Calendar. Please make sure your calendar is connected in VeyraX and try again."
                else:
                    return f"I couldn't retrieve your calendar events: {error_msg}"
            
            # Handle different response structures
            items = []
            if isinstance(events, dict):
                if "data" in events and "items" in events.get("data", {}):
                    items = events.get("data", {}).get("items", [])
                elif "items" in events:
                    items = events.get("items", [])
            
            summary = []
            for i, event in enumerate(items[:10], 1):  # Limit to 10 events
                title = event.get("summary", "Untitled Event")
                
                # Handle different date formats
                start = event.get("start", {})
                if isinstance(start, dict):
                    start_time = start.get("dateTime", start.get("date", "Unknown Time"))
                else:
                    # If start is a string (direct datetime), use it directly
                    start_time = start or "Unknown Time"
                
                end = event.get("end", {})
                if isinstance(end, dict):
                    end_time = end.get("dateTime", end.get("date", ""))
                else:
                    # If end is a string (direct datetime), use it directly
                    end_time = end or ""
                
                location = event.get("location", "")
                attendees = event.get("attendees", [])
                
                summary.append(f"{i}. {title}")
                summary.append(f"   When: {start_time} to {end_time}" if end_time else f"   When: {start_time}")
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
        except Exception as e:
            print(f"Error summarizing calendar events: {e}")
            # Return a safe fallback message
            return "I was able to access your calendar, but encountered an error formatting the events. Please try a more specific query."
    
    def update_calendar_event(self, event_id, summary=None, start_time=None, end_time=None, location=None, description=None, attendees=None, calendar_id="michal.fiech@gmail.com"):
        """
        Update an existing calendar event.
        
        Args:
            event_id (str): ID of the event to update
            summary (str): New event title (optional)
            start_time (str): New start time in RFC 3339 format (optional)
            end_time (str): New end time in RFC 3339 format (optional)
            location (str): New event location (optional)
            description (str): New event description (optional)
            attendees (list): New list of attendees (optional)
            calendar_id (str): ID of the calendar (default: primary)
            
        Returns:
            dict: Updated event data or error message
        """
        # Build the update payload with only the fields that are provided
        event_update = {}
        if summary is not None:
            event_update["summary"] = summary
        if start_time is not None:
            event_update["start"] = {"dateTime": start_time}
        if end_time is not None:
            event_update["end"] = {"dateTime": end_time}
        if location is not None:
            event_update["location"] = location
        if description is not None:
            event_update["description"] = description
        if attendees is not None:
            event_update["attendees"] = [{"email": email} for email in attendees]
        
        params = {
            "event_id": event_id,
            "event": event_update,
            "calendar_id": calendar_id
        }
        
        return self.post_request("/google-calendar/update_event", params)
    
    def delete_calendar_event(self, event_id, calendar_id="michal.fiech@gmail.com"):
        """
        Delete a calendar event.
        
        Args:
            event_id (str): ID of the event to delete
            calendar_id (str): Calendar ID (default: "primary")
            
        Returns:
            dict: Response data or error message
        """
        params = {
            "event_id": event_id,
            "calendarId": calendar_id
        }
        
        return self.post_request("/google-calendar/delete_event", params)
        
    def process_query(self, query, thread_history=None):
        """
        Process a user query and return relevant data from VeyraX services.
        
        Args:
            query (str): The user's query
            thread_history (list): List of previous messages in the thread
            
        Returns:
            dict: Context data from VeyraX services
        """
        # Handle None query
        if query is None:
            print("Received None query in process_query, returning None")
            return None

        query_lower = query.lower()
        
        # Enhanced email-related keywords with variations
        email_keywords = [
            "email", "e-mail", "mail", "gmail", "inbox", "message", "received", 
            "sent", "sender", "from", "attachment", "subject", "read", "unread",
            "check mail", "check email", "check my mail", "check my email", 
            "any new", "any emails", "show me emails", "show me mail", 
            "recent emails", "recent mail"
        ]
        
        calendar_keywords = [
            "calendar", "event", "meeting", "schedule", "appointment", 
            "call", "zoom", "conference", "webinar", "session", "reminder",
            "upcoming", "agenda", "planned", "scheduled"
        ]
        
        # Improved email detection logic
        is_email_query = (
            any(keyword in query_lower for keyword in email_keywords) or
            any(f" {keyword} " in f" {query_lower} " for keyword in ["mail", "inbox", "sent"]) or
            "email" in query_lower or "e-mail" in query_lower
        )
        
        # Improved calendar detection logic
        is_calendar_query = (
            any(keyword in query_lower for keyword in calendar_keywords) or
            "schedule" in query_lower or "meeting" in query_lower
        )
        
        # Debug logging
        print(f"Query: '{query_lower}'")
        print(f"Is email query: {is_email_query}")
        print(f"Is calendar query: {is_calendar_query}")
        
        # Check if query is about emails
        if is_email_query:
            # Check if user is asking for unread emails
            unread_requested = any(keyword in query_lower for keyword in 
                               ['unread', 'new email', 'new message', 'haven\'t read', 'not read'])
            
            # Prepare request parameters
            params = {
                "limit": 10,
                "folder": "INBOX",
                "offset": 0,
                "mark_as_read": False
            }
            
            # Add search query for unread if requested
            if unread_requested:
                params["search_query"] = "is:unread"  # Gmail search syntax for unread messages
            
            # Extract search terms for more specific searches
            search_terms = []
            
            # Check for sender keywords
            if "from" in query_lower or "sender" in query_lower:
                # Try to extract an email address or name after "from" or "sender"
                for keyword in ["from", "sender"]:
                    if keyword in query_lower:
                        parts = query_lower.split(keyword, 1)[1].strip()
                        if parts:
                            # Take the first word after "from" or "sender" as a potential sender
                            potential_sender = parts.split()[0]
                            if "@" in potential_sender:  # Looks like an email
                                search_terms.append(f"from:{potential_sender}")
                            else:
                                # Try to get a name (might be multiple words)
                                name_parts = []
                                for word in parts.split():
                                    if word in ["about", "containing", "with", "regarding", "on", "for", "in"]:
                                        break
                                    name_parts.append(word)
                                if name_parts:
                                    search_terms.append(f"from:{' '.join(name_parts)}")
            
            # Check for subject keywords
            if "subject" in query_lower or "about" in query_lower or "regarding" in query_lower:
                for keyword in ["subject", "about", "regarding"]:
                    if keyword in query_lower:
                        parts = query_lower.split(keyword, 1)[1].strip()
                        if parts:
                            # Extract the subject terms
                            subject_parts = []
                            for word in parts.split():
                                if word in ["from", "sent", "by", "on", "for", "in"]:
                                    break
                                subject_parts.append(word)
                            if subject_parts:
                                search_terms.append(f"subject:{' '.join(subject_parts)}")
            
            # Combine search terms if any were identified
            if search_terms:
                params["search_query"] = " ".join(search_terms)
                
            print(f"Email search parameters: {params}")
            
            # Make the API request
            response = self.post_request("/mail/get_messages", params)
            
            print(f"Email search response: {response}")
            
            if "error" in response:
                return {
                    "source_type": "mail",
                    "content": f"I couldn't retrieve your emails: {response.get('error', 'Unknown error')}",
                    "data": {"messages": []}
                }
            
            # Format the emails for display
            messages = response.get("data", {}).get("messages", [])
            formatted_emails, email_ids = self.summarize_emails(messages)
            
            return {
                "source_type": "mail",
                "content": formatted_emails,
                "data": {
                    "messages": messages,
                    "filter_applied": params.get("search_query") is not None
                }
            }
            
        # Check if query is about calendar
        elif is_calendar_query:
            # Default to upcoming events in the next 7 days
            days = 7
            
            # Try to extract a date or time period
            if "today" in query_lower:
                events = self.get_events_for_date()
            elif "tomorrow" in query_lower:
                events = self.get_events_for_date("tomorrow")
            elif "next week" in query_lower:
                days = 7
                events = self.get_upcoming_events(days=days)
            elif "next month" in query_lower:
                days = 30
                events = self.get_upcoming_events(days=days)
            else:
                events = self.get_upcoming_events(days=days)
                
            formatted_events = self.summarize_calendar_events(events)
            
            # Extract events from the response
            event_items = []
            if isinstance(events, dict):
                if "data" in events and "items" in events["data"]:
                    event_items = events["data"]["items"]
                elif "items" in events:
                    event_items = events["items"]
            
            return {
                "source_type": "google-calendar",
                "content": formatted_events,
                "data": {
                    "events": event_items,
                    "filter_applied": True  # Always using primary calendar
                }
            }
            
        return None 