from datetime import datetime, timedelta
import random
import uuid

class MockVeyraXService:
    """
    Mock VeyraX service for testing purposes.
    Returns fake data for Gmail and Google Calendar.
    """
    
    def __init__(self, api_key=None):
        """Initialize mock service."""
        self.api_key = api_key or "mock_api_key"
        print("Mock VeyraX service initialized successfully")
    
    def get_tools(self):
        """Return a mock list of available tools."""
        return {
            "tools": {
                "gmail": {
                    "methods": {
                        "listEmails": {
                            "parameters": {
                                "query": "string",
                                "maxResults": "number"
                            }
                        }
                    }
                },
                "google-calendar": {
                    "methods": {
                        "listEvents": {
                            "parameters": {
                                "timeMin": "string",
                                "timeMax": "string",
                                "maxResults": "number"
                            }
                        }
                    }
                }
            }
        }
    
    def tool_call(self, tool_name, method_name, params=None):
        """
        Mock tool call implementation.
        
        Args:
            tool_name (str): The name of the tool (e.g., 'gmail', 'google-calendar')
            method_name (str): The method to call on the tool
            params (dict): Parameters for the method call
            
        Returns:
            dict: Mock response data
        """
        if params is None:
            params = {}
            
        print(f"Mock tool call: {tool_name}.{method_name} with params {params}")
        
        if tool_name == "gmail":
            if method_name == "listEmails":
                return self._mock_gmail_list_emails(params)
        elif tool_name == "google-calendar":
            if method_name == "listEvents":
                return self._mock_calendar_list_events(params)
        
        return {"error": f"Unknown tool or method: {tool_name}.{method_name}"}
    
    def _mock_gmail_list_emails(self, params):
        """Generate mock Gmail emails."""
        count = params.get("maxResults", 10)
        if isinstance(count, str) and count.isdigit():
            count = int(count)
        elif isinstance(count, str):
            count = 10
            
        senders = [
            "john.doe@example.com", 
            "project.manager@company.com",
            "team.lead@organization.org",
            "notifications@github.com",
            "support@jira.com"
        ]
        
        subjects = [
            "Project Status Update - May 2025",
            "Meeting Notes from Yesterday's Call",
            "Review Request: New Feature Proposal",
            "Reminder: Team Huddle at 3 PM",
            "Weekly Sprint Planning",
            "[URGENT] Server Downtime Scheduled",
            "Quarterly Goals Review",
            "New Task Assignment: UI Redesign",
            "Feedback Requested: Client Presentation",
            "Holiday Schedule for Next Month"
        ]
        
        messages = []
        for i in range(min(count, 10)):
            date = (datetime.now() - timedelta(days=i, hours=random.randint(0, 23), minutes=random.randint(0, 59))).isoformat()
            
            messages.append({
                "id": f"msg_{uuid.uuid4()}",
                "sender": random.choice(senders),
                "subject": random.choice(subjects),
                "date": date,
                "snippet": f"This is a mock email snippet {i+1}. It contains some text that would normally be the first few sentences of the email content..."
            })
        
        return {"messages": messages}
    
    def _mock_calendar_list_events(self, params):
        """Generate mock Google Calendar events."""
        max_results = params.get("maxResults", 10)
        if isinstance(max_results, str) and max_results.isdigit():
            max_results = int(max_results)
        elif isinstance(max_results, str):
            max_results = 10
            
        event_titles = [
            "Team Stand-up",
            "Project Review Meeting",
            "Client Call: Implementation Discussion",
            "Sprint Planning",
            "1:1 with Manager",
            "Code Review Session",
            "Product Demo",
            "Quarterly Strategy Meeting",
            "Interview: Senior Developer Position",
            "Team Lunch"
        ]
        
        locations = [
            "Conference Room A",
            "Zoom Meeting",
            "Google Meet",
            "Main Office",
            "Client Site",
            "",  # Some events have no location
        ]
        
        attendees = [
            {"email": "john.doe@example.com"},
            {"email": "jane.smith@company.com"},
            {"email": "director@organization.org"},
            {"email": "client.contact@client.com"}
        ]
        
        # Get current date and create some events spanning the next few days
        now = datetime.now()
        events = []
        
        for i in range(min(max_results, 10)):
            # Create event start time (random time in the next few days)
            start_date = now + timedelta(days=random.randint(0, 7), hours=random.randint(9, 16))
            # Event duration between 30 min and 2 hours
            duration = timedelta(minutes=random.choice([30, 60, 90, 120]))
            end_date = start_date + duration
            
            # Random subset of attendees
            event_attendees = random.sample(attendees, random.randint(1, len(attendees)))
            
            events.append({
                "id": f"event_{uuid.uuid4()}",
                "title": random.choice(event_titles),
                "start": {"dateTime": start_date.isoformat()},
                "end": {"dateTime": end_date.isoformat()},
                "location": random.choice(locations),
                "attendees": event_attendees
            })
        
        return {"events": events}
    
    # Convenience methods that mirror the VeyraXService API
    
    def get_recent_emails(self, count=10, query=None):
        """Get recent emails from Gmail."""
        params = {}
        if count:
            params["maxResults"] = count
        if query:
            params["query"] = query
        return self.tool_call("gmail", "listEmails", params)
    
    def search_emails(self, query, count=10):
        """Search for emails with a specific query."""
        return self.get_recent_emails(count=count, query=query)
    
    def get_upcoming_events(self, days=7, max_results=10):
        """Get upcoming calendar events."""
        now = datetime.now()
        time_min = now.isoformat() + "Z"
        time_max = (now.replace(hour=23, minute=59, second=59) + 
                   timedelta(days=days)).isoformat() + "Z"
        
        params = {
            "timeMin": time_min,
            "timeMax": time_max,
            "maxResults": max_results
        }
        
        return self.tool_call("google-calendar", "listEvents", params)
    
    def get_events_for_date(self, date=None):
        """Get calendar events for a specific date."""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
            
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        time_min = date_obj.replace(hour=0, minute=0, second=0).isoformat() + "Z"
        time_max = date_obj.replace(hour=23, minute=59, second=59).isoformat() + "Z"
        
        params = {
            "timeMin": time_min,
            "timeMax": time_max
        }
        
        return self.tool_call("google-calendar", "listEvents", params)
    
    def summarize_emails(self, emails):
        """Format emails for easy reading."""
        if not emails or "error" in emails:
            return "I couldn't retrieve your emails. Please try again later."
        
        if isinstance(emails, dict) and "messages" in emails:
            emails = emails.get("messages", [])
        
        summary = []
        for i, email in enumerate(emails[:10], 1):  # Limit to 10 emails
            sender = email.get("sender", "Unknown Sender")
            subject = email.get("subject", "No Subject")
            date = email.get("date", "Unknown Date")
            snippet = email.get("snippet", "")
            
            summary.append(f"{i}. From: {sender}")
            summary.append(f"   Subject: {subject}")
            summary.append(f"   Date: {date}")
            summary.append(f"   Preview: {snippet[:100]}..." if len(snippet) > 100 else f"   Preview: {snippet}")
            summary.append("")
        
        if not summary:
            return "No emails found."
            
        return "\n".join(summary)
    
    def get_email_message(self, message_id, mark_as_read=False):
        """
        Mock implementation of getting a specific email message.
        
        Args:
            message_id (str): ID of the message to retrieve
            mark_as_read (bool): Whether to mark the message as read
            
        Returns:
            dict: Mock email message data
        """
        # Generate a mock email message with some HTML and text content
        message = {
            "id": message_id,
            "subject": "Mock Email Subject",
            "from": {
                "email": "sender@example.com",
                "name": "Mock Sender"
            },
            "to": [
                {
                    "email": "recipient@example.com",
                    "name": "Mock Recipient"
                }
            ],
            "date": datetime.now().isoformat(),
            "textBody": "This is a mock email message with plain text content. It contains information that might be important for testing purposes.",
            "htmlBody": """
                <html>
                    <head>
                        <style>
                            body { font-family: Arial, sans-serif; margin: 20px; }
                            .header { background-color: #f0f0f0; padding: 10px; }
                            .content { padding: 20px; }
                            .footer { font-size: 12px; color: gray; padding: 10px; }
                        </style>
                    </head>
                    <body>
                        <div class="header">
                            <h2>Mock Email Subject</h2>
                        </div>
                        <div class="content">
                            <p>This is a mock email message with <strong>HTML content</strong>.</p>
                            <p>It contains information that might be important for testing purposes.</p>
                            <ul>
                                <li>Item one</li>
                                <li>Item two</li>
                                <li>Item three</li>
                            </ul>
                            <p>Best regards,<br>Mock Sender</p>
                        </div>
                        <div class="footer">
                            This is an automatically generated mock email for testing.
                        </div>
                    </body>
                </html>
            """
        }
        
        return {
            "data": {
                "message": message
            }
        }
    
    def get_email_details(self, email_id):
        """
        Get the full details of an email, including HTML content.
        
        Args:
            email_id (str): ID of the email to retrieve
            
        Returns:
            str: HTML content of the email, or plain text if HTML is not available
        """
        try:
            # Get the full email message from our mock implementation
            response = self.get_email_message(email_id)
            
            if "error" in response:
                print(f"Error retrieving mock email details: {response['error']}")
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
            print(f"Error in get_email_details mock: {str(e)}")
            return None
    
    def summarize_calendar_events(self, events):
        """Format calendar events for easy reading."""
        if not events or "error" in events:
            return "I couldn't retrieve your calendar events. Please try again later."
        
        if isinstance(events, dict) and "events" in events:
            events = events.get("events", [])
        
        summary = []
        for i, event in enumerate(events[:10], 1):  # Limit to 10 events
            title = event.get("title", "Untitled Event")
            start = event.get("start", {}).get("dateTime", event.get("start", {}).get("date", "Unknown Time"))
            end = event.get("end", {}).get("dateTime", event.get("end", {}).get("date", ""))
            location = event.get("location", "")
            attendees = event.get("attendees", [])
            
            summary.append(f"{i}. {title}")
            summary.append(f"   When: {start} to {end}" if end else f"   When: {start}")
            if location:
                summary.append(f"   Where: {location}")
            if attendees:
                attendee_names = [a.get("email", "Unknown") for a in attendees[:3]]
                if len(attendees) > 3:
                    attendee_names.append(f"and {len(attendees) - 3} more")
                summary.append(f"   Who: {', '.join(attendee_names)}")
            summary.append("")
        
        if not summary:
            return "No calendar events found."
            
        return "\n".join(summary) 