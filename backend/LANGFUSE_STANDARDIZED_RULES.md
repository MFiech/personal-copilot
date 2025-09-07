# Langfuse Standardized Usage Rules for PM Co-Pilot

## 🎯 **Universal Implementation Rules**

This document defines the **FINAL STANDARDIZED** Langfuse patterns that ALL AI agents, services, and developers must follow when working with PM Co-Pilot, now aligned with podcast-analyzer patterns.

---

## 🏗️ **Implementation Architecture**

### **Direct Client Pattern (NEW)**
```python
from services.langfuse_client import create_langfuse_client

class YourService:
    def __init__(self):
        # Each service gets its own client instance
        try:
            self.langfuse_client = create_langfuse_client("service_name")
        except Exception as e:
            print(f"⚠️ [SERVICE] Failed to initialize Langfuse client: {e}")
            self.langfuse_client = None
```

### **Testing Environment (CRITICAL)**
```python
# Testing automatically disables Langfuse
is_testing = os.getenv("TESTING", "false").lower() == "true"
if is_testing:
    langfuse_enabled = False  # NO Langfuse data during tests
```

---

## 📋 **Session Strategy - Thread-Based Only**

### **Session Format (FINAL)**
```
pm_copilot_{service_name}_{thread_id}
```

### **Service-Specific Sessions**
| Service | Session Format | Example |
|---------|-------------------|---------|
| **Conversation** | `pm_copilot_conversation_{thread_id}` | `pm_copilot_conversation_thread_123` |
| **Email** | `pm_copilot_email_{thread_id}` | `pm_copilot_email_thread_456` |
| **Calendar** | `pm_copilot_calendar_{thread_id}` | `pm_copilot_calendar_thread_789` |
| **Drafts** | `pm_copilot_drafts_{thread_id}` | `pm_copilot_drafts_thread_012` |

### **❌ FORBIDDEN: NO DATE-BASED SESSIONS**
```python
# ❌ NEVER DO THIS
session_id = f"pm_copilot_conversation_{datetime.now().strftime('%Y-%m-%d')}_{thread_id}"

# ✅ ALWAYS DO THIS  
session_id = f"pm_copilot_conversation_{thread_id}"
```

**Reason**: Threads span multiple days - all activity in one thread should be grouped together.

---

## 🔄 **Context Manager Pattern**

### **Workflow Tracing (NEW STANDARD)**
```python
def your_workflow_function(self, query, thread_id):
    if self.langfuse_client and self.langfuse_client.is_enabled():
        try:
            with self.langfuse_client.create_workflow_span(
                name="pm_copilot_your_workflow",
                thread_id=thread_id,
                input_data={"query": query},
                metadata={"workflow_type": "your_workflow"}
            ) as workflow_span:
                if workflow_span:
                    self.langfuse_client.update_span_with_session(
                        workflow_span, 
                        thread_id, 
                        ["your_service", "pm_copilot"]
                    )
                
                return self._process_workflow(query)
        except Exception as e:
            print(f"⚠️ Workflow tracing failed: {e}")
            return self._process_workflow(query)
    else:
        return self._process_workflow(query)
```

---

## 🚀 **LLM Call Tracing**

### **Standard @observe Pattern**
```python
from langfuse import observe

@observe(as_type="generation", name="your_operation_name")
def your_llm_function(self, prompt):
    """All LLM calls MUST use @observe decorator"""
    return self.llm.invoke(prompt)
```

### **Required Naming Convention**
- Format: `{service}_{operation}_{model}`
- Examples:
  - `draft_intent_detection`
  - `gmail_query_building` 
  - `calendar_intent_analysis`
  - `claude_main_conversation`

---

## ⚙️ **Service Integration Examples**

### **App.py (Main Conversation)**
```python
# Initialize conversation client
conversation_langfuse = create_langfuse_client("conversation")

# Use context manager for main conversation flow
conversation_span = conversation_langfuse.create_workflow_span(
    name="pm_copilot_conversation_turn",
    thread_id=thread_id,
    input_data={"user_query": query}
)
```

### **Draft Service**
```python
class DraftService:
    def __init__(self):
        self.langfuse_client = create_langfuse_client("drafts")
    
    @observe(as_type="generation", name="draft_intent_detection")
    def detect_draft_intent(self, query, thread_id=None):
        # Workflow tracing + LLM tracing combined
        pass
```

### **Composio Service** 
```python
class ComposioService:
    def __init__(self):
        self.langfuse_client = create_langfuse_client("email")
    
    def process_query(self, query, thread_id=None):
        # Email/calendar workflows with thread-based sessions
        pass
```

---

## 🧪 **Testing Integration**

### **Environment Variables**
```bash
# Testing mode - NO Langfuse traces
TESTING=true

# Development mode - WITH Langfuse traces  
TESTING=false
LANGFUSE_ENABLED=true
```

### **Automatic Disabling**
```python
# This happens automatically in langfuse_client.py
is_testing = os.getenv("TESTING", "false").lower() == "true"
if is_testing:
    langfuse_enabled = False
    print(f"🔕 [{service_name}] Langfuse disabled in testing mode")
```

---

## 🔍 **Error Handling Pattern**

### **Graceful Degradation (REQUIRED)**
```python
def safe_langfuse_operation(self):
    if not self.langfuse_client or not self.langfuse_client.is_enabled():
        return self._fallback_operation()
    
    try:
        # Langfuse operations
        return self._traced_operation()
    except Exception as e:
        print(f"⚠️ Langfuse operation failed: {e}")
        # NEVER fail main operation due to tracing
        return self._fallback_operation()
```

---

## 📊 **Quality Standards**

### **Session Quality Checklist**
- [ ] Thread-based session format: `pm_copilot_{service}_{thread_id}`
- [ ] NO dates in session IDs
- [ ] All thread activity grouped in same session
- [ ] Proper service-specific prefixes
- [ ] Testing environment respected

### **Trace Quality Checklist**  
- [ ] @observe decorators on all LLM calls
- [ ] Context managers for workflows
- [ ] Rich input/output data captured
- [ ] Proper error handling implemented  
- [ ] Graceful degradation when disabled

### **Code Quality Checklist**
- [ ] Direct client pattern used
- [ ] No centralized service dependencies
- [ ] Service-specific client initialization
- [ ] Thread IDs passed to all workflow functions
- [ ] Testing automatically disables Langfuse

---

## 🚫 **Migration Completed - Old Patterns Removed**

### **Removed Components**
- ❌ `services/langfuse_service.py` (backed up)
- ❌ Centralized `LangfuseService` class
- ❌ Complex trace management methods
- ❌ Date-based session formats

### **Updated Components**
- ✅ `services/langfuse_client.py` (new direct client)
- ✅ `app.py` (uses conversation client)
- ✅ `services/draft_service.py` (uses drafts client)
- ✅ `services/composio_service.py` (uses email client)
- ✅ `utils/langfuse_helpers.py` (uses helper client)

---

## 🎯 **Implementation Status**

### **✅ Completed Phases**
1. **Phase 1**: Refactor core LangfuseService to direct client pattern
2. **Phase 2**: Implement context manager pattern for traces  
3. **Phase 3**: Update session strategy to thread-based format
4. **Phase 4**: Standardize decorator usage across services
5. **Phase 5**: Update testing integration and validation

### **✅ Completed Phases**
6. **Phase 6**: Test and validate complete implementation - ✅ **COMPLETED**

### **🎉 STANDARDIZATION COMPLETE**
**All phases completed successfully!** See `PHASE6_VALIDATION_REPORT.md` for full validation results.

---

## 📞 **Usage Guidelines**

### **For New Services**
1. Import: `from services.langfuse_client import create_langfuse_client`
2. Initialize: `self.langfuse_client = create_langfuse_client("service_name")`
3. Add workflow tracing with context managers
4. Add @observe decorators to LLM calls  
5. Always include thread_id parameter

### **For Existing Services**
1. Replace old LangfuseService imports
2. Update initialization to direct client pattern
3. Add thread_id parameters where missing
4. Test with TESTING=true to ensure no traces

---

## 🏆 **Final Result**

PM Co-Pilot now uses the **same proven Langfuse patterns** as podcast-analyzer:

- ✅ **Direct client approach** (no centralized service)
- ✅ **Context manager pattern** for workflow tracing
- ✅ **@observe decorators** for LLM calls
- ✅ **Thread-based sessions** (no date fragmentation)
- ✅ **Automatic testing disablement** (TESTING=true)
- ✅ **Graceful error handling** (never break main flow)

**Implementation Status**: ✅ **COMPLETE AND VALIDATED**  
**Next Step**: Production deployment (ready for commit)