"""
Streamlined Langfuse client for PM Co-Pilot
Following podcast-analyzer patterns for simplicity and consistency
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from langfuse import Langfuse, observe


class LangfuseClient:
    """
    Simplified Langfuse client following podcast-analyzer patterns.
    Each service gets its own instance for better error isolation.
    """
    
    def __init__(self, service_name: str):
        """
        Initialize Langfuse client for a specific service
        
        Args:
            service_name: Name of the service (conversation, email, calendar, etc.)
        """
        self.service_name = service_name
        self.session_prefix = f"pm_copilot_{service_name}"
        
        # Check testing environment first (like podcast-analyzer)
        is_testing = os.getenv("TESTING", "false").lower() == "true"
        langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
        
        # Disable Langfuse during testing (podcast-analyzer pattern)
        if is_testing:
            langfuse_enabled = False
            print(f"🔕 [{self.service_name.upper()}] Langfuse disabled in testing mode")
        
        self.enabled = langfuse_enabled
        self.langfuse = None
        
        if self.enabled:
            try:
                # Use host.docker.internal for Docker containers (preserved from original)
                host = os.getenv('LANGFUSE_HOST', 'http://localhost:4000')
                if os.getenv('DOCKER_ENV') or host == 'http://localhost:4000':
                    host = 'http://host.docker.internal:4000'
                
                self.langfuse = Langfuse(
                    secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
                    public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
                    host=host,
                    flush_at=1,  # Flush after 1 event (podcast-analyzer pattern)
                    flush_interval=1  # Flush every 1 second
                )
                print(f"✅ [{self.service_name.upper()}] Langfuse client initialized successfully")
            except Exception as e:
                print(f"⚠️ [{self.service_name.upper()}] Failed to initialize Langfuse: {str(e)}")
                print(f"🔄 [{self.service_name.upper()}] Falling back to offline mode")
                self.enabled = False
                self.langfuse = None
        else:
            print(f"🔕 [{self.service_name.upper()}] Langfuse service disabled")
    
    def is_enabled(self) -> bool:
        """Check if Langfuse is enabled and configured"""
        return self.enabled and self.langfuse is not None
    
    def create_session_id(self, thread_id: str) -> str:
        """
        Generate thread-based session ID (NO dates per requirements)
        
        Args:
            thread_id: Thread/conversation ID
            
        Returns:
            Formatted session ID: pm_copilot_{service}_{thread_id}
        """
        return f"{self.session_prefix}_{thread_id}"
    
    def create_workflow_span(self, 
                           name: str,
                           thread_id: str,
                           input_data: Dict[str, Any],
                           metadata: Optional[Dict[str, Any]] = None):
        """
        Create a workflow-level span with session context (podcast-analyzer pattern)
        
        Args:
            name: Span name
            thread_id: Thread ID for session
            input_data: Input data for the span
            metadata: Additional metadata
            
        Returns:
            Span context manager or None
        """
        if not self.is_enabled():
            return None
        
        try:
            session_id = self.create_session_id(thread_id)
            
            # Build metadata
            span_metadata = {
                "service": self.service_name,
                "thread_id": thread_id,
                "timestamp": datetime.now().isoformat(),
                "environment": os.getenv("ENVIRONMENT", "development")
            }
            
            if metadata:
                span_metadata.update(metadata)
            
            # Use context manager pattern (podcast-analyzer style)
            return self.langfuse.start_as_current_span(
                name=name,
                input=input_data,
                metadata=span_metadata
            )
            
        except Exception as e:
            print(f"⚠️ [{self.service_name.upper()}] Failed to create workflow span: {e}")
            return None
    
    def update_span_with_session(self, span, thread_id: str, tags: Optional[list] = None):
        """
        Update span with session information (podcast-analyzer pattern)
        
        Args:
            span: Span to update
            thread_id: Thread ID
            tags: Optional tags list
        """
        if not span or not self.is_enabled():
            return
        
        try:
            session_id = self.create_session_id(thread_id)
            span_tags = [self.service_name, "pm_copilot"]
            
            if tags:
                span_tags.extend(tags)
            
            span.update_trace(
                session_id=session_id,
                user_id=f"thread_{thread_id}",
                tags=span_tags
            )
            
        except Exception as e:
            print(f"⚠️ [{self.service_name.upper()}] Failed to update span with session: {e}")
    
    def get_prompt(self, name: str, label: str = "production") -> Optional[Any]:
        """
        Retrieve a prompt template from Langfuse with fallback
        
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
            print(f"⚠️ [{self.service_name.upper()}] Failed to get prompt '{name}': {e}")
            return None
    
    def flush(self) -> None:
        """Flush all pending traces to Langfuse (podcast-analyzer pattern)"""
        if self.is_enabled():
            try:
                self.langfuse.flush()
            except Exception as e:
                print(f"⚠️ [{self.service_name.upper()}] Failed to flush traces: {e}")
    
    def __del__(self):
        """Cleanup: flush any remaining traces"""
        self.flush()


# Factory function for creating service-specific clients
def create_langfuse_client(service_name: str) -> LangfuseClient:
    """
    Factory function to create Langfuse clients for different services
    
    Args:
        service_name: Name of the service (conversation, email, calendar, drafts)
        
    Returns:
        LangfuseClient instance
    """
    return LangfuseClient(service_name)