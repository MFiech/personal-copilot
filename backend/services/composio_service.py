from composio import Composio
from composio.client.enums import Action
from datetime import datetime, timedelta
import base64
import openai
import os
import json
import zoneinfo
import time
from bson import ObjectId
from langfuse import observe
from services.langfuse_client import create_langfuse_client
from utils.langfuse_helpers import get_gmail_query_builder_prompt, get_query_classification_prompt, get_calendar_intent_analysis_prompt

class ComposioService:
    # Environment flag for verbose logging
    VERBOSE_COMPOSIO_LOGS = os.getenv("VERBOSE_COMPOSIO_LOGS", "false").lower() == "true"
    
    @staticmethod
    def _strip_html(text):
        """Remove HTML tags from text and clean it up"""
        if not text:
            return ""
        # Remove HTML tags
        clean = re.sub('<.*?>', '', str(text))
        # Replace common HTML entities
        clean = clean.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        # Clean up whitespace
        clean = ' '.join(clean.split())
        return clean
    
    @staticmethod
    def _format_calendar_for_log(events):
        """Extract essential calendar fields for logging"""
        if not events:
            return []
        
        formatted = []
        for event in events[:3]:  # Limit to first 3 events
            attendees = []
            if event.get("attendees"):
                attendees = [a.get("email", "Unknown") for a in event["attendees"]]
            
            formatted.append({
                "name": event.get("summary", "Untitled")[:50],
                "description": (event.get("description", "")[:100] + "..." if len(event.get("description", "")) > 100 else event.get("description", "")),
                "attendees": attendees[:3],  # Max 3 attendees
                "location": event.get("location", "No location")[:50],
                "start": event.get("start", {}).get("dateTime", "No time"),
                "end": event.get("end", {}).get("dateTime", "No time")
            })
        return formatted
    
    @staticmethod
    def _format_email_for_log(emails):
        """Extract essential email fields for logging (NO HTML)"""
        if not emails:
            return []
        
        formatted = []
        for email in emails[:3]:  # Limit to first 3 emails
            # Get from address
            from_addr = "Unknown"
            if email.get("from"):
                from_addr = email["from"]
            
            # Get to addresses
            to_addrs = []
            if email.get("to"):
                if isinstance(email["to"], list):
                    to_addrs = email["to"][:3]  # Max 3 recipients
                else:
                    to_addrs = [email["to"]]
            
            # Get body and strip HTML completely
            body = email.get("body", "")
            clean_body = ComposioService._strip_html(body)[:100]  # Max 100 chars, no HTML
            if len(clean_body) >= 100:
                clean_body += "..."
            
            formatted.append({
                "from": from_addr,
                "to": to_addrs,
                "subject": (email.get("subject", "No subject")[:50] + "..." if len(email.get("subject", "")) > 50 else email.get("subject", "No subject")),
                "body_preview": clean_body
            })
        return formatted
    
    @staticmethod
    def _log_composio_response(operation_type, data, action_name=None):
        """Centralized logging for Composio responses"""
        if ComposioService.VERBOSE_COMPOSIO_LOGS:
            # Full verbose logging for development
            print(f"🔴 [COMPOSIO] Full {operation_type} response: {data}")
        else:
            # Simplified logging for production
            if operation_type == "calendar":
                if isinstance(data, dict) and "items" in data:
                    events = data["items"]
                    simplified = ComposioService._format_calendar_for_log(events)
                    print(f"🔴 [COMPOSIO] Calendar ({len(events)} events): {simplified}")
                else:
                    print(f"🔴 [COMPOSIO] Calendar response: {str(data)[:200]}...")
            
            elif operation_type == "email":
                if isinstance(data, list):
                    simplified = ComposioService._format_email_for_log(data)
                    print(f"🔴 [COMPOSIO] Email ({len(data)} emails): {simplified}")
                else:
                    print(f"🔴 [COMPOSIO] Email response: {str(data)[:200]}...")
            
            elif operation_type == "action":
                action_info = f" [{action_name}]" if action_name else ""
                print(f"🔴 [COMPOSIO] Action{action_info}: {str(data)[:200]}...")
            
            else:
                # Generic simplified logging
                print(f"🔴 [COMPOSIO] {operation_type}: {str(data)[:200]}...")

    def __init__(self, api_key: str):
        """
        Initializes the new Composio client with MCP (Model Context Protocol) support.
        """
        if not api_key:
            raise ValueError("Composio API key is required for ComposioService.")
        
        # New Composio configuration
        self.user_id = "michal.fiech@gmail.com"
        self.mcp_config_id = "a06cbb3a-cc69-4ee6-8bb3-be7bb30a6cb3"
        self.mcp_url = f"https://apollo-dwobt5e6g-composio.vercel.app/v3/mcp/{self.mcp_config_id}/mcp?user_id=michal.fiech%40gmail.com"
        
        # Auth config IDs from new setup
        self.gmail_auth_config_id = "ac_iAjd2trEsUx4"
        self.google_calendar_auth_config_id = "ac_RojXkl42zm7s"
        
        # Try to initialize new Composio client
        try:
            self.composio = Composio(api_key=api_key)
            print("[SUCCESS] New Composio client initialized successfully!")
            self.client_available = True
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Failed to initialize new Composio client: {error_msg}")
            self.composio = None
            self.client_available = False
            print("[WARNING] Composio client initialization failed. Email/calendar features will be limited.")
        
        # Initialize Langfuse client for composio service
        try:
            self.langfuse_client = create_langfuse_client("email")
        except Exception as e:
            print(f"⚠️ [EMAIL] Failed to initialize Langfuse client: {e}")
            self.langfuse_client = None
        
        # Initialize Gemini LLM for query classification
        self.gemini_llm = None
        self._init_gemini_llm()
        
        # Check and set up connected accounts if available
        if self.client_available:
            self._check_connected_accounts()

    def _check_connected_accounts(self):
        """Check if connected accounts are available and log their status."""
        try:
            # Get all connected accounts
            connected_accounts = self.composio.connected_accounts.get()
            
            if connected_accounts:
                print(f"[INFO] Found {len(connected_accounts)} connected accounts")
                
                gmail_account = None
                calendar_account = None
                
                for account in connected_accounts:
                    print(f"[INFO] - {account.appName}: {account.id} (status: {account.status})")
                    if account.appName == 'gmail' and account.status == 'ACTIVE':
                        gmail_account = account
                    elif account.appName == 'googlecalendar' and account.status == 'ACTIVE':
                        calendar_account = account
                
                # Store account IDs for later use
                self.gmail_account_id = gmail_account.id if gmail_account else None
                self.calendar_account_id = calendar_account.id if calendar_account else None
                
                if gmail_account:
                    print(f"[SUCCESS] Gmail connected and ready (ID: {gmail_account.id})")
                else:
                    print(f"[WARNING] No active Gmail connection found")
                    
                if calendar_account:
                    print(f"[SUCCESS] Google Calendar connected and ready (ID: {calendar_account.id})")
                else:
                    print(f"[WARNING] No active Google Calendar connection found")
                    
            else:
                print(f"[WARNING] No connected accounts found")
                self.gmail_account_id = None
                self.calendar_account_id = None
                
        except Exception as e:
            print(f"[ERROR] Failed to check connected accounts: {e}")
            self.gmail_account_id = None
            self.calendar_account_id = None

    def initiate_connection(self, service: str = "gmail"):
        """
        Initiate a connection for Gmail or Google Calendar using new toolkit authorization.
        Returns the redirect URL for user authentication.
        """
        if not self.client_available:
            return {"error": "Composio client not available"}
        
        try:
            if service.lower() == "gmail":
                toolkit = "gmail"
            elif service.lower() == "calendar":
                toolkit = "googlecalendar"
            else:
                return {"error": f"Unsupported service: {service}"}
            
            # Use the new toolkit authorization approach
            auth_result = self.composio.toolkits.authorize(
                user_id=self.user_id,
                toolkit=toolkit
            )
            
            return {
                "redirect_url": auth_result.redirect_url if hasattr(auth_result, 'redirect_url') else str(auth_result),
                "message": f"Please visit the URL to authorize {service}",
                "service": service
            }
            
        except Exception as e:
            return {"error": f"Failed to initiate {service} authorization: {str(e)}"}

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

    @observe(as_type="generation", name="query_classification")
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
            # Get the classification prompt using Langfuse helper
            prompt = get_query_classification_prompt(user_query, conversation_history)


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
        """Execute an action using the new Composio API."""
        if not self.client_available or self.composio is None:
            error_msg = "Composio client is not available due to initialization failure"
            print(f"[ERROR] {error_msg}")
            return {"successful": False, "error": error_msg}
            
        try:
            action_str = str(action)
            print(f"[DEBUG] Executing action: {action_str} with params: {params}")
            
            # Determine connected account ID based on action
            connected_account_id = None
            if "GMAIL" in action_str:
                connected_account_id = self.gmail_account_id
                if not connected_account_id:
                    error_msg = "Gmail account not connected"
                    print(f"[ERROR] {error_msg}")
                    return {"successful": False, "error": error_msg}
            elif "GOOGLECALENDAR" in action_str:
                connected_account_id = self.calendar_account_id
                if not connected_account_id:
                    error_msg = "Google Calendar account not connected"
                    print(f"[ERROR] {error_msg}")
                    return {"successful": False, "error": error_msg}
            else:
                error_msg = f"Unknown action type: {action_str}"
                print(f"[ERROR] {error_msg}")
                return {"successful": False, "error": error_msg}
            
            # Execute the action using the new API
            print(f"🔴 [COMPOSIO] Executing action: {action} with params: {params} on account: {connected_account_id}")
            response = self.composio.actions.execute(
                action=action,
                params=params or {},
                connected_account=connected_account_id
            )
            
            print(f"🔴 [COMPOSIO] Action execution response type: {type(response)}")
            
            # Safe logging of response to avoid printing issues
            try:
                if isinstance(response, dict):
                    response_keys = list(response.keys()) if response else []
                    print(f"🔴 [COMPOSIO] Response is dict with keys: {response_keys}")
                    # Use simplified logging instead of full dump
                    self._log_composio_response("action", response, str(action))
                else:
                    print(f"🔴 [COMPOSIO] Response attributes: {dir(response) if hasattr(response, '__dict__') else 'No attributes'}")
                    self._log_composio_response("action", response, str(action))
            except Exception as log_error:
                print(f"🔴 [COMPOSIO] Could not log response safely: {log_error}")
            
            # The response format might be different, so let's handle it properly
            if hasattr(response, 'successful'):
                print(f"🔴 [COMPOSIO] Response has 'successful' attribute: {response.successful}")
                result = {"successful": response.successful, "data": response.data if hasattr(response, 'data') else response}
                self._log_composio_response("result", result)
                return result
            elif isinstance(response, dict):
                # Handle dict response with potential typos in keys
                success_key = None
                if 'successful' in response:
                    success_key = 'successful'
                elif 'successfull' in response:  # Handle typo
                    success_key = 'successfull'
                
                if success_key:
                    success_value = response[success_key]
                    print(f"🔴 [COMPOSIO] Found success key '{success_key}': {success_value}")
                    result = {"successful": success_value, "data": response.get('data', response)}
                    self._log_composio_response("result", result)
                    return result
                else:
                    print(f"🔴 [COMPOSIO] No success key found in dict response, checking for errors")
                    if 'error' in response and response['error']:
                        print(f"🔴 [COMPOSIO] Error found in response: {response['error']}")
                        result = {"successful": False, "error": response['error'], "data": response}
                    else:
                        print(f"🔴 [COMPOSIO] No error found, assuming success")
                        result = {"successful": True, "data": response}
                    self._log_composio_response("result", result)
                    return result
            else:
                print(f"🔴 [COMPOSIO] Response doesn't have 'successful' attribute, assuming success")
                # Assume success if no error was thrown
                result = {"successful": True, "data": response}
                self._log_composio_response("result", result)
                return result
            
        except Exception as e:
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
        
        # Always include query if provided (Gmail page tokens don't preserve query context)
        if query:
            params["query"] = query
            print(f"[DEBUG] {'First' if not page_token else 'Paginated'} request with Gmail query: {query}")
        
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
        
        # Always include query if provided (Gmail page tokens don't preserve query context)
        if query:
            params["query"] = query
            print(f"[DEBUG] {'First' if not page_token else 'Paginated'} request with query: {query}")
        
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
            
            # The email data is at the top level, not nested
            actual_email_data = email_data
            if not actual_email_data:
                print(f"[DEBUG] get_email_details - No email data found")
                return None
                
            print(f"[DEBUG] get_email_details - Actual email data keys: {list(actual_email_data.keys())}")
            
            # Try to extract content from the response
            # The response structure may vary, so we'll try multiple approaches
            content = ""
            
            # Try to get payload data (Gmail API format)
            payload = actual_email_data.get("payload", {})
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
                message_text = actual_email_data.get("messageText", "")
                if message_text:
                    content = message_text
                    print(f"[DEBUG] get_email_details - Using messageText fallback, length: {len(content)}")
                
                # Final fallback to snippet
                if not content:
                    content = actual_email_data.get("snippet", "")
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



    def _parse_email_address(self, email_string):
        """Parse email address string like 'Name <email@domain.com>' or 'email@domain.com'"""
        try:
            if '<' in email_string and '>' in email_string:
                name = email_string.split('<')[0].strip().strip('"')
                email = email_string.split('<')[1].split('>')[0].strip()
                return {'name': name, 'email': email}
            else:
                return {'name': '', 'email': email_string.strip()}
        except:
            return {'name': '', 'email': email_string}

    def _extract_content_from_thread_message(self, message):
        """
        Extract content from a thread message object (already has full content).
        This avoids making another API call since the thread fetch already provides full content.
        """
        try:
            # The message object from thread fetch should already have the content
            # Check if it has a payload with content
            payload = message.get('payload', {})
            if not payload:
                print(f"[DEBUG] _extract_content_from_thread_message - No payload found")
                return None
            
            # Try to extract content from the payload
            content = self._extract_content_from_payload(payload)
            
            if content:
                print(f"[DEBUG] _extract_content_from_thread_message - Successfully extracted content, length: {len(content)}")
                return content
            else:
                print(f"[DEBUG] _extract_content_from_thread_message - No content found in payload")
                return None
                
        except Exception as e:
            print(f"[ERROR] _extract_content_from_thread_message - Error extracting content: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_content_from_payload(self, payload):
        """
        Extract content from a Gmail message payload.
        """
        try:
            content = ""
            
            # Check if it's a simple text/html message
            mime_type = payload.get('mimeType', '')
            if mime_type in ["text/html", "text/plain"]:
                body_data = payload.get("body", {}).get("data")
                if body_data:
                    try:
                        content = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                        print(f"[DEBUG] _extract_content_from_payload - Decoded simple message, length: {len(content)}")
                    except Exception as e:
                        print(f"[DEBUG] _extract_content_from_payload - Error decoding simple message: {e}")
            
            # Check if it's a multipart message
            elif "parts" in payload:
                print(f"[DEBUG] _extract_content_from_payload - Multipart message with {len(payload.get('parts', []))} parts")
                content = self._extract_content_from_parts(payload.get("parts", []))
            
            return content
            
        except Exception as e:
            print(f"[ERROR] _extract_content_from_payload - Error: {e}")
            return None

    def _parse_email_addresses(self, emails_string):
        """Parse multiple email addresses separated by commas"""
        try:
            addresses = []
            for email_part in emails_string.split(','):
                parsed = self._parse_email_address(email_part.strip())
                if parsed['email']:
                    addresses.append(parsed)
            return addresses
        except:
            return []

    def get_full_gmail_thread(self, gmail_thread_id):
        """
        Get full Gmail thread using GMAIL_FETCH_MESSAGE_BY_THREAD_ID action.
        Returns all messages in the thread with full content.
        """
        response = self._execute_action(
            action=Action.GMAIL_FETCH_MESSAGE_BY_THREAD_ID,
            params={
                "thread_id": gmail_thread_id,
                "format": "full",
                "user_id": "me"
            }
        )
        
        if response.get("successful"):
            # The Composio response has a nested 'data' key
            composio_raw_data = response.get("data", {})
            print(f"[DEBUG] get_full_gmail_thread - Composio raw data keys: {list(composio_raw_data.keys())}")
            
            # Extract the 'messages' array from the nested 'data'
            messages = composio_raw_data.get('messages', [])
            print(f"[DEBUG] get_full_gmail_thread - Found {len(messages)} messages in response")
            
            # Instead of complex message processing, fetch each email individually
            emails = []
            for i, message in enumerate(messages):
                message_id = message.get('messageId')
                if message_id:
                    print(f"[DEBUG] get_full_gmail_thread - Fetching email {i+1}/{len(messages)} with ID: {message_id}")
                    
                    # Get the full email content using the existing method
                    email_content = self.get_email_details(message_id)
                    if email_content:
                        # Create a simple email structure
                        email_data = {
                            'email_id': message_id,
                            'message_id': message_id,
                            'gmail_thread_id': gmail_thread_id,
                            'subject': '',
                            'from_email': {},
                            'to_emails': [],
                            'date': message.get('messageTimestamp', ''),
                            'content': email_content
                        }
                        
                        # Extract basic info from headers if available
                        headers = message.get('payload', {}).get('headers', [])
                        for header in headers:
                            name = header.get('name', '').lower()
                            value = header.get('value', '')
                            
                            if name == 'subject':
                                email_data['subject'] = value
                            elif name == 'from':
                                email_data['from_email'] = self._parse_email_address(value)
                            elif name == 'to':
                                email_data['to_emails'] = self._parse_email_addresses(value)
                            elif name == 'date':
                                email_data['date'] = value
                        
                        emails.append(email_data)
                        print(f"[DEBUG] get_full_gmail_thread - Successfully fetched email {i+1}")
                    else:
                        print(f"[DEBUG] get_full_gmail_thread - Failed to fetch email {i+1}")
                else:
                    print(f"[DEBUG] get_full_gmail_thread - No messageId found for message {i+1}")
            
            print(f"[DEBUG] get_full_gmail_thread - Final result: {len(emails)} emails fetched")
            return {
                'emails': emails,
                'gmail_thread_id': gmail_thread_id,
                'email_count': len(emails)  # Add email count for completeness
            }
        else:
            print(f"[DEBUG] get_full_gmail_thread - Action not successful: {response.get('error', 'Unknown error')}")
            return None

    def delete_email(self, message_id, permanently=False, **kwargs):
        action = Action.GMAIL_DELETE_EMAIL_PERMANENTLY if permanently else Action.GMAIL_TRASH_EMAIL
        response = self._execute_action(
            action=action,
            params={"message_id": message_id}
        )
        return response.get("successful", False)

    def send_email(self, to_emails, subject, body, cc_emails=None, bcc_emails=None, attachments=None):
        """
        Send an email using Composio Gmail API.
        
        Args:
            to_emails: List of recipient email addresses or single string
            subject: Email subject line
            body: Email body content (plain text with line breaks preserved)
            cc_emails: Optional list of CC recipients
            bcc_emails: Optional list of BCC recipients
            attachments: Optional list of attachments (not implemented yet)
        
        Returns:
            dict: Response from Composio API with success/error status
        """
        if not self.client_available or not self.gmail_account_id:
            return {"error": "Gmail not connected or unavailable"}
        
        # Handle recipient email - use first email as primary recipient
        if isinstance(to_emails, list) and to_emails:
            primary_recipient = to_emails[0]
            # Put additional recipients in CC if they exist
            additional_recipients = to_emails[1:] if len(to_emails) > 1 else []
        else:
            primary_recipient = to_emails if isinstance(to_emails, str) else str(to_emails)
            additional_recipients = []
        
        # Extract email addresses from objects if needed
        if isinstance(primary_recipient, dict):
            primary_recipient = primary_recipient.get('email', str(primary_recipient))
        
        # Build parameters for Composio Gmail API
        params = {
            "recipient_email": primary_recipient,
            "subject": subject or "No Subject",
            "body": body or "",
            "is_html": False  # Plain text with line breaks
        }
        
        # Add CC recipients (combine additional to_emails with explicit cc_emails)
        cc_list = []
        if additional_recipients:
            for email in additional_recipients:
                if isinstance(email, dict):
                    cc_list.append(email.get('email', str(email)))
                else:
                    cc_list.append(str(email))
        
        if cc_emails:
            for email in cc_emails:
                if isinstance(email, dict):
                    cc_list.append(email.get('email', str(email)))
                else:
                    cc_list.append(str(email))
        
        if cc_list:
            params["cc"] = cc_list
        
        # Add BCC recipients if provided
        if bcc_emails:
            bcc_list = []
            for email in bcc_emails:
                if isinstance(email, dict):
                    bcc_list.append(email.get('email', str(email)))
                else:
                    bcc_list.append(str(email))
            params["bcc"] = bcc_list
        
        print(f"[DEBUG] Sending email with params: {params}")
        
        try:
            response = self._execute_action(
                action=Action.GMAIL_SEND_EMAIL,
                params=params
            )
            
            if response and response.get("successful"):
                print(f"[DEBUG] Email sent successfully")
                return {
                    "success": True,
                    "message": f"Email sent successfully to {primary_recipient}" + (f" and {len(cc_list)} others" if cc_list else ""),
                    "data": response.get("data", {})
                }
            else:
                error_msg = response.get("error", "Unknown error") if response else "No response received"
                print(f"[ERROR] Failed to send email: {error_msg}")
                return {
                    "success": False,
                    "error": f"Failed to send email: {error_msg}"
                }
                
        except Exception as e:
            error_msg = f"Exception while sending email: {str(e)}"
            print(f"[ERROR] {error_msg}")
            import traceback
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "error": error_msg
            }

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
            print(f"[DEBUG] Added orderBy parameter: {order_by}")
            
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_EVENTS_LIST,
            params=params
        )
        if response and response.get("successful"):
            data = response.get("data", {})
            print(f"[DEBUG] GOOGLECALENDAR_EVENTS_LIST successful, data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            # Use simplified logging for calendar data
            self._log_composio_response("calendar", data)
            return {"data": data}
        else:
            print(f"[ERROR] GOOGLECALENDAR_EVENTS_LIST failed")
            if response:
                self._log_composio_response("error", response)
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
            "calendarId": calendar_id,  # GOOGLECALENDAR_CREATE_EVENT expects camelCase
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
            # Try just email strings first - if this fails, we know Composio expects objects
            params["attendees"] = attendee_emails
        
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
            "calendarId": calendar_id,  # GOOGLECALENDAR_UPDATE_EVENT expects camelCase
            "event_id": event_id        # But event_id stays snake_case
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
        print(f"🔴 [COMPOSIO] Starting delete_calendar_event for event_id: {event_id}, calendar_id: {calendar_id}")
        
        params = {
            "calendar_id": calendar_id,  # Using snake_case as per Composio schema
            "event_id": event_id
        }
        
        print(f"🔴 [COMPOSIO] Delete params: {params}")
        print(f"🔴 [COMPOSIO] Using action: {Action.GOOGLECALENDAR_DELETE_EVENT}")
        
        response = self._execute_action(
            action=Action.GOOGLECALENDAR_DELETE_EVENT,
            params=params
        )
        
        self._log_composio_response("calendar_delete", response, "DELETE_EVENT")
        
        success = response and response.get("successful", False)
        print(f"🔴 [COMPOSIO] Final success result: {success}")
        
        if not success:
            print(f"🔴 [COMPOSIO] Delete failed")
            if response and isinstance(response, dict):
                print(f"🔴 [COMPOSIO] Response keys: {list(response.keys())}")
                if 'error' in response:
                    print(f"🔴 [COMPOSIO] Error details: {response['error']}")
                if 'data' in response:
                    self._log_composio_response("error_data", response['data'])
        else:
            print(f"🔴 [COMPOSIO] Delete appears successful")
        
        return success

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

    @observe(as_type="generation", name="gmail_query_building")
    def build_gmail_query_with_llm(self, user_query, conversation_history=None):
        """
        Use LLM to intelligently build Gmail search queries from natural language.
        Returns a Gmail search query string or empty string for general queries.
        """
        try:
            # Build the prompt using Langfuse helper
            prompt = get_gmail_query_builder_prompt(user_query, conversation_history)
            
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
    
    @observe(as_type="generation", name="calendar_intent_analysis")
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
            # Get the calendar intent analysis prompt using Langfuse helper
            prompt = get_calendar_intent_analysis_prompt(user_query, thread_history)


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
        
        # Handle keywords being a list (from LLM responses) or string
        if isinstance(keywords, list):
            keywords = " ".join(keywords) if keywords else ""
        elif keywords is None:
            keywords = ""
        
        # Convert date_range to time_min/time_max
        time_min, time_max = None, None
        if date_range:
            # Handle date_range being a list
            if isinstance(date_range, list):
                date_range = date_range[0] if date_range else ""
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

    def _sort_events_chronologically(self, events):
        """
        Sort calendar events chronologically (oldest first, newest last).
        Handles different date formats and timezones.
        """
        def get_event_start_time(event):
            """Extract start time from event for sorting"""
            start = event.get('start', {})
            
            # Try dateTime first (for timed events)
            if 'dateTime' in start:
                try:
                    # Parse ISO format datetime
                    dt_str = start['dateTime']
                    if dt_str.endswith('Z'):
                        dt_str = dt_str[:-1] + '+00:00'
                    return datetime.fromisoformat(dt_str)
                except (ValueError, TypeError):
                    pass
            
            # Try date (for all-day events)
            if 'date' in start:
                try:
                    # Parse date format (YYYY-MM-DD)
                    date_str = start['date']
                    return datetime.fromisoformat(date_str)
                except (ValueError, TypeError):
                    pass
            
            # Fallback to a very old date if parsing fails
            return datetime.min.replace(tzinfo=zoneinfo.ZoneInfo("UTC"))
        
        try:
            # Sort by start time (oldest first)
            sorted_events = sorted(events, key=get_event_start_time)
            return sorted_events
        except Exception as e:
            print(f"[WARNING] Failed to sort events chronologically: {e}")
            return events  # Return original order if sorting fails

    def _extract_time_range(self, query_lower):
        """
        Extract time range from natural language query.
        Returns (time_min, time_max) as RFC3339 timestamps.
        Always uses CEST (Europe/Warsaw) timezone for consistent time handling.
        """
        # Use CEST timezone instead of UTC
        try:
            cest_tz = zoneinfo.ZoneInfo("Europe/Warsaw")
            now = datetime.now(cest_tz)
            print(f"[DEBUG] Using CEST timezone for time range extraction: {now}")
        except Exception as tz_error:
            print(f"[WARNING] Europe/Warsaw timezone not available: {tz_error}")
            # Fallback to UTC but log the issue
            now = datetime.utcnow()
            print(f"[WARNING] Fallback to UTC timezone: {now}")
        
        if "today" in query_lower:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()
            
        elif "tomorrow" in query_lower:
            tomorrow = now + timedelta(days=1)
            start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
            end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start.isoformat(), end.isoformat()
            
        elif "this week" in query_lower:
            # Start of current week (Monday) in CEST
            days_since_monday = now.weekday()
            start_of_week = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59, microseconds=999999)
            print(f"[DEBUG] This week range in CEST: {start_of_week.isoformat()} to {end_of_week.isoformat()}")
            return start_of_week.isoformat(), end_of_week.isoformat()
            
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

    def process_query(self, query, thread_history=None, anchored_item=None, thread_id=None):
        """
        Enhanced process_query that uses LLM-based classification and 2-stage approach for calendar processing.
        
        Stage 1: Classify intent (email, calendar, general)
        Stage 2: For calendar intent, use _process_calendar_intent for create vs search + parameter extraction
        """
        print(f"[DEBUG] Processing query with LLM classification: '{query}'")
        print(f"[DEBUG] Anchored item: {anchored_item}")
        
        # Check if this is an action on an anchored item
        if anchored_item and self._is_anchored_item_action(query, anchored_item):
            return self._handle_anchored_item_action(query, anchored_item)
        
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
            print(f"[DEBUG-COMPOSIO] 🔍 About to store Gmail query for pagination:")
            print(f"[DEBUG-COMPOSIO] 📝 User query: '{query}'")
            print(f"[DEBUG-COMPOSIO] 🎯 Generated Gmail query: '{search_query}'")
            print(f"[DEBUG-COMPOSIO] 📦 Response type: {type(response)}")
            print(f"[DEBUG-COMPOSIO] 🗂️ Response has 'data': {'data' in response if isinstance(response, dict) else 'N/A'}")
            
            if response and isinstance(response, dict) and 'data' in response:
                response['original_gmail_query'] = search_query
                print(f"[DEBUG-COMPOSIO] ✅ Successfully set 'original_gmail_query' to: '{search_query}'")
                print(f"[DEBUG-COMPOSIO] 🔑 Response keys after setting: {list(response.keys())}")
            else:
                print(f"[DEBUG-COMPOSIO] ❌ Failed to set 'original_gmail_query' - response structure invalid")
                print(f"[DEBUG-COMPOSIO] 📊 Response structure: {response if isinstance(response, dict) else type(response)}")
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

    def _is_anchored_item_action(self, query, anchored_item):
        """
        Determine if the query is an action on the anchored item.
        """
        query_lower = query.lower()
        
        # Email actions
        email_actions = [
            "reply", "reply to", "respond", "respond to", "forward", "delete",
            "archive", "mark as read", "mark as unread", "star", "unstar"
        ]
        
        # Calendar actions  
        calendar_actions = [
            "modify", "update", "change", "edit", "reschedule", "move",
            "cancel", "delete", "add attendee", "remove attendee"
        ]
        
        # Generic actions that work on both
        generic_actions = ["this", "it", "that"]
        
        # Check for specific action words
        for action in email_actions + calendar_actions + generic_actions:
            if action in query_lower:
                return True
                
        return False

    def _parse_time_modification(self, query_lower, item_data):
        """
        Parse time modification requests like "move 3 hours later", "shift 30 minutes earlier"
        """
        import re
        from datetime import datetime, timedelta
        
        # Get current start and end times
        current_start = item_data.get('start', {})
        current_end = item_data.get('end', {})
        
        start_time_str = current_start.get('dateTime')
        end_time_str = current_end.get('dateTime')
        
        if not start_time_str or not end_time_str:
            print(f"[DEBUG] Missing start/end time for calendar modification: start={start_time_str}, end={end_time_str}")
            return None
        
        try:
            # Parse current times (handle timezone)
            start_datetime = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_datetime = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
            
            # Extract timezone info for later use
            timezone_str = start_time_str[-6:] if start_time_str.endswith(('+', '-')) else None
            
            # Parse time modification patterns
            patterns = [
                # "move 3 hours later", "shift 2 hours later"
                r'(?:move|shift)\s+(\d+)\s+(hour|hours?|hr|hrs?)\s+(later|forward)',
                # "move 30 minutes later"
                r'(?:move|shift)\s+(\d+)\s+(minute|minutes?|min|mins?)\s+(later|forward)',
                # "move 3 hours earlier", "shift 1 hour earlier"  
                r'(?:move|shift)\s+(\d+)\s+(hour|hours?|hr|hrs?)\s+(earlier|backward|back)',
                # "move 15 minutes earlier"
                r'(?:move|shift)\s+(\d+)\s+(minute|minutes?|min|mins?)\s+(earlier|backward|back)',
                # "3 hours later"
                r'(\d+)\s+(hour|hours?|hr|hrs?)\s+(later|forward)',
                # "30 minutes later" 
                r'(\d+)\s+(minute|minutes?|min|mins?)\s+(later|forward)',
                # "2 hours earlier"
                r'(\d+)\s+(hour|hours?|hr|hrs?)\s+(earlier|backward|back)',
                # "45 minutes earlier"
                r'(\d+)\s+(minute|minutes?|min|mins?)\s+(earlier|backward|back)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, query_lower)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2)
                    direction = match.group(3)
                    
                    # Calculate time delta
                    if unit.startswith('hour') or unit.startswith('hr'):
                        delta = timedelta(hours=amount)
                    else:  # minutes
                        delta = timedelta(minutes=amount)
                    
                    # Apply direction
                    if direction in ['earlier', 'backward', 'back']:
                        delta = -delta
                    
                    # Calculate new times
                    new_start = start_datetime + delta
                    new_end = end_datetime + delta
                    
                    # Format back to ISO string with timezone
                    new_start_str = new_start.isoformat()
                    new_end_str = new_end.isoformat()
                    
                    # Preserve original timezone format if it was there
                    if timezone_str:
                        new_start_str = new_start_str.replace('+00:00', timezone_str)
                        new_end_str = new_end_str.replace('+00:00', timezone_str)
                    
                    # Create description
                    direction_text = "later" if direction in ['later', 'forward'] else "earlier"
                    unit_text = "hours" if unit.startswith('hour') else "minutes"
                    description = f"{amount} {unit_text} {direction_text}"
                    
                    print(f"[DEBUG] Parsed time modification: {description}")
                    print(f"[DEBUG] Old time: {start_time_str} - {end_time_str}")
                    print(f"[DEBUG] New time: {new_start_str} - {new_end_str}")
                    
                    return {
                        'old_start': start_time_str,
                        'old_end': end_time_str,
                        'new_start': new_start_str,
                        'new_end': new_end_str,
                        'description': description,
                        'amount': amount,
                        'unit': unit_text,
                        'direction': direction
                    }
            
            print(f"[DEBUG] No time modification pattern matched for: {query_lower}")
            return None
            
        except Exception as e:
            print(f"[DEBUG] Error parsing time modification: {e}")
            return None

    def _handle_anchored_item_action(self, query, anchored_item):
        """
        Handle actions on anchored items like "Reply to this email" or "Modify the date of this event"
        """
        query_lower = query.lower()
        item_type = anchored_item.get('type')
        item_id = anchored_item.get('id')
        item_data = anchored_item.get('data', {})
        
        print(f"[DEBUG] Handling anchored item action: {query_lower}")
        print(f"[DEBUG] Item type: {item_type}, ID: {item_id}")
        
        if item_type == 'email':
            # Handle email actions
            if any(word in query_lower for word in ["reply", "respond"]):
                # Prepare reply action - return information for LLM to handle
                return {
                    "source_type": "mail",
                    "action": "reply",
                    "content": f"I understand you want to reply to the email '{item_data.get('subject', 'Unknown Subject')}' from {item_data.get('from_email', {}).get('name', 'Unknown Sender')}. Please let me know what you'd like to say in your reply.",
                    "data": {
                        "email_id": item_id,
                        "original_subject": item_data.get('subject'),
                        "original_from": item_data.get('from_email'),
                        "action_type": "compose_reply"
                    }
                }
            elif any(word in query_lower for word in ["delete", "remove"]):
                # Handle email deletion
                try:
                    result = self.delete_email(item_id)
                    if result and not result.get("error"):
                        return {
                            "source_type": "mail",
                            "action": "delete",
                            "content": f"Successfully deleted the email '{item_data.get('subject', 'Unknown Subject')}'",
                            "data": {"email_id": item_id, "action_type": "delete", "success": True}
                        }
                    else:
                        error_msg = result.get("error") if result else "Unknown error"
                        return {
                            "source_type": "mail",
                            "action": "delete",
                            "content": f"Failed to delete the email: {error_msg}",
                            "data": {"email_id": item_id, "action_type": "delete", "success": False, "error": error_msg}
                        }
                except Exception as e:
                    return {
                        "source_type": "mail", 
                        "action": "delete",
                        "content": f"Error deleting email: {str(e)}",
                        "data": {"email_id": item_id, "action_type": "delete", "success": False, "error": str(e)}
                    }
        
        elif item_type == 'calendar_event':
            # Handle calendar event actions
            if any(word in query_lower for word in ["modify", "update", "change", "edit", "reschedule", "move", "shift"]):
                # Try to parse time modifications first
                time_change = self._parse_time_modification(query_lower, item_data)
                if time_change:
                    try:
                        # Perform the actual calendar update
                        result = self.update_calendar_event(
                            event_id=item_id,
                            start_time=time_change['new_start'],
                            end_time=time_change['new_end']
                        )
                        if result and not result.get("error"):
                            return {
                                "source_type": "google-calendar",
                                "action": "update_time",
                                "content": f"Successfully moved '{item_data.get('summary', 'Untitled Event')}' {time_change['description']}",
                                "data": {
                                    "event_id": item_id,
                                    "old_start": time_change['old_start'],
                                    "old_end": time_change['old_end'],
                                    "new_start": time_change['new_start'],
                                    "new_end": time_change['new_end'],
                                    "action_type": "time_updated",
                                    "success": True
                                }
                            }
                        else:
                            error_msg = result.get("error") if result else "Unknown error"
                            return {
                                "source_type": "google-calendar",
                                "action": "update_time",
                                "content": f"Failed to move the event: {error_msg}",
                                "data": {"event_id": item_id, "action_type": "time_update_failed", "success": False, "error": error_msg}
                            }
                    except Exception as e:
                        return {
                            "source_type": "google-calendar",
                            "action": "update_time",
                            "content": f"Error updating event time: {str(e)}",
                            "data": {"event_id": item_id, "action_type": "time_update_failed", "success": False, "error": str(e)}
                        }
                else:
                    # For general modifications, we need to understand what to change
                    return {
                        "source_type": "google-calendar",
                        "action": "modify",
                        "content": f"I understand you want to modify the event '{item_data.get('summary', 'Untitled Event')}'. What would you like to change? (e.g., date, time, location, title)",
                        "data": {
                            "event_id": item_id,
                            "current_summary": item_data.get('summary'),
                            "current_start": item_data.get('start'),
                            "current_end": item_data.get('end'),
                            "current_location": item_data.get('location'),
                            "action_type": "modify_event"
                        }
                    }
            elif any(word in query_lower for word in ["delete", "cancel", "remove"]):
                # Handle calendar event deletion
                try:
                    result = self.delete_calendar_event(item_id)
                    if result and not result.get("error"):
                        return {
                            "source_type": "google-calendar",
                            "action": "delete",
                            "content": f"Successfully deleted the event '{item_data.get('summary', 'Untitled Event')}'",
                            "data": {"event_id": item_id, "action_type": "delete", "success": True}
                        }
                    else:
                        error_msg = result.get("error") if result else "Unknown error"
                        return {
                            "source_type": "google-calendar",
                            "action": "delete", 
                            "content": f"Failed to delete the event: {error_msg}",
                            "data": {"event_id": item_id, "action_type": "delete", "success": False, "error": error_msg}
                        }
                except Exception as e:
                    return {
                        "source_type": "google-calendar",
                        "action": "delete",
                        "content": f"Error deleting event: {str(e)}",
                        "data": {"event_id": item_id, "action_type": "delete", "success": False, "error": str(e)}
                    }
        
        # If we can't handle the specific action, return a helpful message
        return {
            "source_type": item_type,
            "action": "unknown",
            "content": f"I understand you want to perform an action on the anchored {item_type.replace('_', ' ')}, but I'm not sure what specific action you'd like to take. Could you be more specific?",
            "data": {"item_id": item_id, "item_type": item_type, "query": query}
        } 