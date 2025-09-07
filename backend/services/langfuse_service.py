"""
Centralized Langfuse service for PM Co-Pilot
Handles tracing, sessions, and prompt management
"""

import os
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from langfuse import Langfuse, observe
from utils.mongo_client import get_db


class LangfuseService:
    """
    Centralized service for Langfuse integration in PM Co-Pilot
    """
    
    def __init__(self):
        """Initialize Langfuse client with configuration from environment"""
        self.enabled = os.getenv('LANGFUSE_ENABLED', 'true').lower() == 'true'
        self.langfuse = None
        
        if self.enabled:
            try:
                # Use host.docker.internal for Docker containers to access host services
                host = os.getenv('LANGFUSE_HOST', 'http://localhost:4000')
                if os.getenv('DOCKER_ENV') or host == 'http://localhost:4000':
                    # When running in Docker, use host.docker.internal to access host machine
                    host = 'http://host.docker.internal:4000'
                
                self.langfuse = Langfuse(
                    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
                    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
                    host=host,
                    flush_at=1,  # Flush after 1 event for real-time visibility
                    flush_interval=1  # Flush every 1 second
                )
                print("✅ Langfuse service initialized successfully")
            except Exception as e:
                print(f"⚠️ Warning: Failed to initialize Langfuse: {str(e)}")
                print("🔄 Falling back to offline mode - app will continue normally")
                self.enabled = False
                self.langfuse = None
        else:
            print("🔕 Langfuse service disabled via LANGFUSE_ENABLED=false")
    
    def is_enabled(self) -> bool:
        """Check if Langfuse is enabled and configured"""
        return self.enabled and self.langfuse is not None
    
    def create_session_id(self, thread_id: str, session_type: str = "conversation") -> str:
        """
        Generate consistent session IDs for different types of interactions
        
        Args:
            thread_id: Thread/conversation ID
            session_type: Type of session (conversation, workflow, drafts)
        
        Returns:
            Formatted session ID string
        """
        return f"{session_type}_{thread_id}"
    
    def get_thread_metadata(self, thread_id: str) -> Dict[str, Any]:
        """
        Get metadata for a conversation thread from MongoDB
        
        Args:
            thread_id: Thread ID to get metadata for
            
        Returns:
            Dictionary containing thread metadata
        """
        try:
            from models.thread import Thread
            thread = Thread.get_by_id(thread_id)
            
            if thread:
                return {
                    "thread_id": thread_id,
                    "thread_title": getattr(thread, 'title', 'Unknown Thread'),
                    "created_at": getattr(thread, 'created_at', datetime.now()).isoformat() if hasattr(getattr(thread, 'created_at', None), 'isoformat') else str(getattr(thread, 'created_at', datetime.now())),
                    "updated_at": getattr(thread, 'updated_at', datetime.now()).isoformat() if hasattr(getattr(thread, 'updated_at', None), 'isoformat') else str(getattr(thread, 'updated_at', datetime.now()))
                }
            else:
                return {
                    "thread_id": thread_id,
                    "thread_title": "New Thread",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
        except Exception as e:
            print(f"⚠️ Warning: Could not get thread metadata: {e}")
            return {
                "thread_id": thread_id,
                "thread_title": "Unknown Thread",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
    
    def start_conversation_trace(self, 
                               thread_id: str, 
                               user_query: str,
                               anchored_item: Optional[Dict] = None,
                               conversation_length: int = 0) -> Optional[Any]:
        """
        Start a new conversation trace with session context
        
        Args:
            thread_id: Conversation thread ID
            user_query: User's query/message
            anchored_item: Any anchored email/calendar item
            conversation_length: Number of messages in conversation
            
        Returns:
            Trace span object or None if not enabled
        """
        if not self.is_enabled():
            return None
        
        try:
            session_id = self.create_session_id(thread_id, "conversation")
            thread_metadata = self.get_thread_metadata(thread_id)
            
            # Create trace with rich metadata
            trace_span = self.langfuse.trace(
                name="pm_copilot_conversation_turn",
                session_id=session_id,
                user_id=f"thread_{thread_id}",  # Use thread as user identifier for now
                input={
                    "user_query": user_query,
                    "query_length": len(user_query),
                    "has_anchored_item": bool(anchored_item),
                    "anchored_item_type": anchored_item.get('type') if anchored_item else None
                },
                metadata={
                    **thread_metadata,
                    "conversation_length": conversation_length,
                    "timestamp": datetime.now().isoformat(),
                    "session_type": "conversation",
                    "anchored_item": anchored_item if anchored_item else None
                }
            )
            
            return trace_span
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to start conversation trace: {e}")
            return None
    
    def end_conversation_trace(self, 
                             trace_span: Any, 
                             response: str,
                             tool_results: Optional[Dict] = None,
                             draft_created: Optional[Dict] = None) -> None:
        """
        End a conversation trace with output data
        
        Args:
            trace_span: The trace span to end
            response: LLM response text
            tool_results: Any tool results (emails, calendar events, etc.)
            draft_created: Information about any created draft
        """
        if not self.is_enabled() or not trace_span:
            return
        
        try:
            output_data = {
                "response": response,
                "response_length": len(response),
                "has_tool_results": bool(tool_results),
                "has_draft_created": bool(draft_created)
            }
            
            # Add tool result details
            if tool_results:
                if "emails" in tool_results:
                    output_data["emails_found"] = len(tool_results.get("emails", []))
                if "calendar_events" in tool_results:
                    output_data["events_found"] = len(tool_results.get("calendar_events", []))
                if "contacts" in tool_results:
                    output_data["contacts_found"] = len(tool_results.get("contacts", []))
            
            # Add draft details
            if draft_created:
                output_data.update({
                    "draft_id": draft_created.get("draft_id"),
                    "draft_type": draft_created.get("draft_type"),
                    "draft_status": draft_created.get("status")
                })
            
            trace_span.update(output=output_data)
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to end conversation trace: {e}")
    
    def create_generation_span(self,
                             parent_trace: Any,
                             name: str,
                             model: str,
                             input_data: Dict[str, Any],
                             metadata: Optional[Dict[str, Any]] = None) -> Optional[Any]:
        """
        Create a generation span for LLM calls
        
        Args:
            parent_trace: Parent trace to attach to
            name: Name of the generation
            model: Model being used
            input_data: Input data for the LLM call
            metadata: Additional metadata
            
        Returns:
            Generation span object or None
        """
        if not self.is_enabled() or not parent_trace:
            return None
        
        try:
            generation_span = self.langfuse.generation(
                name=name,
                model=model,
                input=input_data,
                metadata=metadata or {},
                trace_id=parent_trace.id
            )
            
            return generation_span
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to create generation span: {e}")
            return None
    
    def end_generation_span(self,
                          generation_span: Any,
                          output_data: Dict[str, Any],
                          usage: Optional[Dict[str, Any]] = None) -> None:
        """
        End a generation span with output and usage data
        
        Args:
            generation_span: Generation span to end
            output_data: Output from the LLM
            usage: Token usage information
        """
        if not self.is_enabled() or not generation_span:
            return
        
        try:
            generation_span.end(
                output=output_data,
                usage=usage
            )
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to end generation span: {e}")
    
    def get_prompt(self, name: str, label: str = "production") -> Optional[Any]:
        """
        Retrieve a prompt template from Langfuse
        
        Args:
            name: Prompt template name
            label: Version label (production, development, testing)
            
        Returns:
            Prompt template object or None
        """
        if not self.is_enabled():
            return None
        
        try:
            prompt = self.langfuse.get_prompt(name, label=label)
            return prompt
            
        except Exception as e:
            print(f"⚠️ Warning: Failed to get prompt '{name}': {e}")
            return None
    
    def create_prompt(self, 
                     name: str,
                     prompt_content: str,
                     labels: List[str] = None,
                     prompt_type: str = "text") -> bool:
        """
        Create or update a prompt template in Langfuse
        
        Args:
            name: Prompt name
            prompt_content: Prompt template content
            labels: Labels for the prompt
            prompt_type: Type of prompt (text, chat)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False
        
        try:
            self.langfuse.create_prompt(
                name=name,
                prompt=prompt_content,
                labels=labels or ["production"],
                type=prompt_type
            )
            
            print(f"✅ Created/updated prompt '{name}'")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create prompt '{name}': {e}")
            return False
    
    def flush(self) -> None:
        """Flush all pending traces to Langfuse"""
        if self.is_enabled():
            try:
                self.langfuse.flush()
            except Exception as e:
                print(f"⚠️ Warning: Failed to flush traces: {e}")
    
    def __del__(self):
        """Cleanup: flush any remaining traces"""
        self.flush()


# Global service instance
_langfuse_service = None

def get_langfuse_service() -> LangfuseService:
    """Get the global Langfuse service instance"""
    global _langfuse_service
    if _langfuse_service is None:
        _langfuse_service = LangfuseService()
    return _langfuse_service
