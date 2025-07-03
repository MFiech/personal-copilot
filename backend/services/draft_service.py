import json
import re
from datetime import datetime
from langchain_anthropic import ChatAnthropic
from models.draft import Draft
from services.contact_service import ContactSyncService
from prompts import draft_detection_prompt, draft_information_extraction_prompt
import os

class DraftService:
    def __init__(self):
        self.contact_service = ContactSyncService()
        
        # Initialize LLM for draft detection and extraction
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_api_key:
            self.llm = ChatAnthropic(model="claude-3-haiku-20240307", anthropic_api_key=anthropic_api_key)
        else:
            print("[DraftService] Warning: ANTHROPIC_API_KEY not found - draft detection will be disabled")
            self.llm = None

    def create_draft(self, draft_type, thread_id, message_id, initial_data=None):
        """
        Create a new draft of specified type.
        
        Args:
            draft_type: "email" or "calendar_event"
            thread_id: Thread ID where the draft belongs
            message_id: Message ID that requested the draft creation
            initial_data: Dict with initial field values
        
        Returns:
            Draft: Created draft instance
        """
        if draft_type not in ["email", "calendar_event"]:
            raise ValueError("draft_type must be 'email' or 'calendar_event'")
        
        # Prepare initial data
        draft_data = {
            "draft_type": draft_type,
            "thread_id": thread_id,
            "message_id": message_id,
            "status": "active"
        }
        
        if initial_data:
            # Process contact names to emails for email drafts
            if draft_type == "email" and "to_contacts" in initial_data:
                resolved_emails = self._resolve_contacts_to_emails(initial_data["to_contacts"])
                draft_data["to_emails"] = resolved_emails
                del initial_data["to_contacts"]  # Remove the unresolved version
            
            # Process attendee names to emails for calendar drafts
            if draft_type == "calendar_event" and "attendee_contacts" in initial_data:
                resolved_attendees = self._resolve_contacts_to_emails(initial_data["attendee_contacts"])
                draft_data["attendees"] = resolved_attendees
                del initial_data["attendee_contacts"]  # Remove the unresolved version
            
            # Add other initial data
            draft_data.update(initial_data)
        
        # Create and save draft
        draft = Draft(**draft_data)
        draft.save()
        
        print(f"[DraftService] Created {draft_type} draft {draft.draft_id} for thread {thread_id}")
        return draft

    def update_draft(self, draft_id, updates):
        """
        Update an existing draft with new field values.
        
        Args:
            draft_id: ID of the draft to update
            updates: Dict of field updates
        
        Returns:
            Draft: Updated draft object if successful, None if failed
        """
        draft = Draft.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        if draft.status != "active":
            raise ValueError(f"Cannot update draft {draft_id} with status '{draft.status}'")
        
        # Process contact resolution if needed
        processed_updates = updates.copy()
        
        if "to_contacts" in updates:
            resolved_emails = self._resolve_contacts_to_emails(updates["to_contacts"])
            processed_updates["to_emails"] = resolved_emails
            del processed_updates["to_contacts"]
        
        if "attendee_contacts" in updates:
            resolved_attendees = self._resolve_contacts_to_emails(updates["attendee_contacts"])
            processed_updates["attendees"] = resolved_attendees
            del processed_updates["attendee_contacts"]
        
        # Update the draft
        success = draft.update(processed_updates)
        
        if success:
            print(f"[DraftService] Updated draft {draft_id} with {list(processed_updates.keys())}")
            # Return the updated draft object
            return Draft.get_by_id(draft_id)
        else:
            print(f"[DraftService] Failed to update draft {draft_id}")
            return None

    def get_draft_by_id(self, draft_id):
        """Get a draft by its ID."""
        return Draft.get_by_id(draft_id)

    def get_draft_by_message_id(self, message_id):
        """Get a draft by the message ID that created it."""
        return Draft.get_by_message_id(message_id)

    def get_active_drafts_by_thread(self, thread_id):
        """Get all active drafts in a thread."""
        return Draft.get_active_drafts_by_thread(thread_id)

    def get_all_drafts_by_thread(self, thread_id):
        """Get all drafts in a thread (any status)."""
        return Draft.get_all_drafts_by_thread(thread_id)

    def close_draft(self, draft_id, status="closed"):
        """
        Close a draft with specified status.
        
        Args:
            draft_id: ID of the draft to close
            status: "closed" or "composio_error"
        
        Returns:
            bool: True if closing was successful
        """
        draft = Draft.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        success = draft.close_draft(status)
        
        if success:
            print(f"[DraftService] Closed draft {draft_id} with status '{status}'")
        else:
            print(f"[DraftService] Failed to close draft {draft_id}")
        
        return success

    def validate_draft_completeness(self, draft_id):
        """
        Check if a draft has all required fields for execution.
        
        Args:
            draft_id: ID of the draft to validate
        
        Returns:
            dict: {"is_complete": bool, "missing_fields": [field_names]}
        """
        draft = Draft.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        return draft.validate_completeness()

    def convert_draft_to_composio_params(self, draft_id):
        """
        Convert a draft to parameters suitable for Composio API calls.
        
        Args:
            draft_id: ID of the draft to convert
        
        Returns:
            dict: Parameters ready for Composio service methods
        
        Raises:
            ValueError: If draft is not complete or not found
        """
        draft = Draft.get_by_id(draft_id)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Check completeness
        validation = draft.validate_completeness()
        if not validation["is_complete"]:
            raise ValueError(f"Draft {draft_id} is incomplete. Missing fields: {validation['missing_fields']}")
        
        if draft.draft_type == "email":
            # Convert to email parameters
            to_emails = [email["email"] for email in draft.to_emails if email.get("email")]
            
            return {
                "to": to_emails,
                "subject": draft.subject,
                "body": draft.body,
                "attachments": draft.attachments or []
            }
        
        elif draft.draft_type == "calendar_event":
            # Convert to calendar event parameters
            attendee_emails = [att["email"] for att in draft.attendees if att.get("email")]
            
            params = {
                "summary": draft.summary,
                "start_time": draft.start_time,
                "end_time": draft.end_time
            }
            
            if draft.location:
                params["location"] = draft.location
            if draft.description:
                params["description"] = draft.description
            if attendee_emails:
                params["attendees"] = attendee_emails
            
            return params
        
        else:
            raise ValueError(f"Unknown draft type: {draft.draft_type}")

    def _resolve_contacts_to_emails(self, contact_names):
        """
        Resolve contact names to email addresses using ContactSyncService.
        
        Args:
            contact_names: List of contact names or email addresses
        
        Returns:
            List of dicts with email and name
        """
        if not contact_names:
            return []
        
        resolved_emails = []
        
        for contact_name in contact_names:
            try:
                # Check if it's in format "Name (email@domain.com)" or "Name <email@domain.com>"
                email_in_parens = None
                clean_name = contact_name
                
                # Extract email from parentheses or angle brackets
                paren_match = re.search(r'\(([^)]+@[^)]+)\)', contact_name)
                angle_match = re.search(r'<([^>]+@[^>]+)>', contact_name)
                
                if paren_match:
                    email_in_parens = paren_match.group(1).strip()
                    clean_name = contact_name.replace(paren_match.group(0), '').strip()
                    print(f"[DraftService] Extracted email from parentheses: '{email_in_parens}' for name: '{clean_name}'")
                elif angle_match:
                    email_in_parens = angle_match.group(1).strip()
                    clean_name = contact_name.replace(angle_match.group(0), '').strip()
                    print(f"[DraftService] Extracted email from angle brackets: '{email_in_parens}' for name: '{clean_name}'")
                
                # If we found a specific email in the contact string, use it directly
                if email_in_parens and self._is_email_address(email_in_parens):
                    resolved_emails.append({
                        "email": email_in_parens,
                        "name": clean_name if clean_name else email_in_parens.split("@")[0]
                    })
                    print(f"[DraftService] Used specific email from parentheses: {email_in_parens} for '{clean_name}'")
                    continue
                
                # Check if the entire string is an email address
                if isinstance(contact_name, str) and self._is_email_address(contact_name):
                    resolved_emails.append({
                        "email": contact_name,
                        "name": contact_name.split("@")[0]  # Use email prefix as name
                    })
                    continue
                
                # Search for contact by name only if no specific email was provided
                contacts = self.contact_service.search_contacts(clean_name)
                
                if contacts and len(contacts) > 0:
                    # Be more conservative with fuzzy matching
                    contact = contacts[0]
                    contact_name_lower = contact["name"].lower() if contact.get("name") else ""
                    search_name_lower = clean_name.lower()
                    
                    # Only use contact if it's a reasonably close match AND has an email
                    if ((contact_name_lower == search_name_lower or 
                        search_name_lower in contact_name_lower or 
                        contact_name_lower in search_name_lower) and
                        contact.get("email")):  # MUST have email
                        
                        print(f"[DraftService] Resolved '{contact_name}' to {contact['email']}")
                        resolved_emails.append({
                            "email": contact["email"],
                            "name": contact.get("name", contact["email"])
                        })
                    else:
                        # Contact found but no email or poor match - require user clarification
                        if not contact.get("email"):
                            print(f"[DraftService] Contact '{contact_name}' found but has no email address - requiring clarification")
                        else:
                            print(f"[DraftService] Ambiguous match for '{contact_name}' - requiring clarification")
                        
                        # Add as placeholder requiring clarification
                        resolved_emails.append({
                            "email": None,  # Explicitly null - requires user input
                            "name": clean_name,
                            "needs_clarification": True
                        })
                else:
                    print(f"[DraftService] No contact found for '{contact_name}' - requiring clarification")
                    # No contact found - require user clarification
                    resolved_emails.append({
                        "email": None,  # Explicitly null - requires user input
                        "name": clean_name,
                        "needs_clarification": True
                    })
                    
            except Exception as e:
                print(f"[DraftService] Error resolving contact '{contact_name}': {e}")
                # Keep as unresolved
                resolved_emails.append({
                    "email": None,
                    "name": contact_name
                })
        
        return resolved_emails

    def _is_email_address(self, text):
        """Check if text is a valid email address."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, text))

    def get_draft_summary(self, draft_id):
        """
        Get a human-readable summary of a draft for display purposes.
        
        Args:
            draft_id: ID of the draft
        
        Returns:
            dict: Summary information for UI display
        """
        draft = Draft.get_by_id(draft_id)
        if not draft:
            return None
        
        validation = draft.validate_completeness()
        
        if draft.draft_type == "email":
            return {
                "type": "email",
                "id": draft.draft_id,
                "status": draft.status,
                "is_complete": validation["is_complete"],
                "missing_fields": validation["missing_fields"],
                "summary": {
                    "to": [f"{email.get('name', 'Unknown')} <{email.get('email', 'No Email')}>" 
                           for email in draft.to_emails] if draft.to_emails else [],
                    "subject": draft.subject or "[No Subject]",
                    "body_preview": (draft.body[:50] + "..." if draft.body and len(draft.body) > 50 
                                   else draft.body or "[No Body]")
                },
                "created_at": draft.created_at,
                "updated_at": draft.updated_at
            }
        
        elif draft.draft_type == "calendar_event":
            return {
                "type": "calendar_event",
                "id": draft.draft_id,
                "status": draft.status,
                "is_complete": validation["is_complete"],
                "missing_fields": validation["missing_fields"],
                "summary": {
                    "title": draft.summary or "[No Title]",
                    "start_time": draft.start_time or "[No Start Time]",
                    "end_time": draft.end_time or "[No End Time]",
                    "location": draft.location or "[No Location]",
                    "attendees": [f"{att.get('name', 'Unknown')} <{att.get('email', 'No Email')}>" 
                                for att in draft.attendees] if draft.attendees else []
                },
                "created_at": draft.created_at,
                "updated_at": draft.updated_at
            }
        
        return None

    def detect_draft_intent(self, user_query, conversation_history=None, existing_draft=None):
        """
        Use LLM to detect if user wants to create a draft and extract information.
        
        Args:
            user_query: The user's message
            conversation_history: Recent conversation context
            existing_draft: Information about existing draft for context
        
        Returns:
            dict: {"is_draft_intent": bool, "draft_data": dict or None}
        """
        if not self.llm:
            print("[DraftService] LLM not available for draft detection")
            return {"is_draft_intent": False, "draft_data": None}
        
        try:
            # Generate prompt for draft detection
            prompt = draft_detection_prompt(user_query, conversation_history, existing_draft)
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            detection_result = json.loads(response_text.strip())
            
            print(f"[DraftService] Draft detection result: {detection_result}")
            return detection_result
            
        except json.JSONDecodeError as e:
            print(f"[DraftService] Failed to parse draft detection response: {e}")
            print(f"[DraftService] Raw response: {response_text}")
            return {"is_draft_intent": False, "draft_data": None}
        except Exception as e:
            print(f"[DraftService] Error in draft detection: {e}")
            return {"is_draft_intent": False, "draft_data": None}

    def extract_draft_information(self, user_query, existing_draft, conversation_history=None):
        """
        Use LLM to extract information for updating an existing draft.
        
        Args:
            user_query: The user's message
            existing_draft: Current draft data
            conversation_history: Recent conversation context
        
        Returns:
            dict: {"updates": dict} - fields to update in the draft
        """
        if not self.llm:
            print("[DraftService] LLM not available for information extraction")
            return {"updates": {}}
        
        try:
            # Generate prompt for information extraction
            prompt = draft_information_extraction_prompt(user_query, existing_draft, conversation_history)
            
            # Get LLM response
            response = self.llm.invoke(prompt)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Parse JSON response
            extraction_result = json.loads(response_text.strip())
            
            print(f"[DraftService] Information extraction result: {extraction_result}")
            return extraction_result
            
        except json.JSONDecodeError as e:
            print(f"[DraftService] Failed to parse extraction response: {e}")
            print(f"[DraftService] Raw response: {response_text}")
            return {"updates": {}}
        except Exception as e:
            print(f"[DraftService] Error in information extraction: {e}")
            return {"updates": {}}

    def create_draft_from_detection(self, thread_id, message_id, detection_result):
        """
        Create a draft based on LLM detection result.
        
        Args:
            thread_id: Thread ID where the draft belongs
            message_id: Message ID that requested the draft
            detection_result: Result from detect_draft_intent()
        
        Returns:
            Draft: Created draft instance or None if failed
        """
        if not detection_result.get("is_draft_intent"):
            return None
        
        draft_data = detection_result.get("draft_data", {})
        draft_type = draft_data.get("draft_type")
        extracted_info = draft_data.get("extracted_info", {})
        
        if not draft_type or draft_type not in ["email", "calendar_event"]:
            print(f"[DraftService] Invalid draft type: {draft_type}")
            return None
        
        try:
            # Process extracted information based on draft type
            initial_data = {}
            
            if draft_type == "email":
                # Process email-specific fields
                if "to_contacts" in extracted_info:
                    initial_data["to_contacts"] = extracted_info["to_contacts"]
                if "subject" in extracted_info and extracted_info["subject"]:
                    initial_data["subject"] = extracted_info["subject"]
                if "body" in extracted_info and extracted_info["body"]:
                    initial_data["body"] = extracted_info["body"]
            
            elif draft_type == "calendar_event":
                # Process calendar-specific fields
                if "summary" in extracted_info and extracted_info["summary"]:
                    initial_data["summary"] = extracted_info["summary"]
                if "start_time" in extracted_info and extracted_info["start_time"]:
                    initial_data["start_time"] = extracted_info["start_time"]
                if "end_time" in extracted_info and extracted_info["end_time"]:
                    initial_data["end_time"] = extracted_info["end_time"]
                if "attendees" in extracted_info:
                    initial_data["attendee_contacts"] = extracted_info["attendees"]
                if "location" in extracted_info and extracted_info["location"]:
                    initial_data["location"] = extracted_info["location"]
                if "description" in extracted_info and extracted_info["description"]:
                    initial_data["description"] = extracted_info["description"]
            
            # Create the draft
            draft = self.create_draft(draft_type, thread_id, message_id, initial_data)
            
            print(f"[DraftService] Created draft {draft.draft_id} from detection")
            return draft
            
        except Exception as e:
            print(f"[DraftService] Error creating draft from detection: {e}")
            return None