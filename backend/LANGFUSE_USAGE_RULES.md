# Langfuse Usage Rules for PM Co-Pilot

## 🎯 **Universal Rules for AI Agents**

This document defines the standardized Langfuse usage patterns that **ALL AI agents, services, and developers** must follow when working with PM Co-Pilot.

---

## 📋 **Core Principles**

### **1. Thread-Based Sessions**
- **Rule**: One session per conversation thread in the database
- **Format**: `pm_copilot_{service_name}_{thread_id}`
- **Examples**:
  - `pm_copilot_conversation_thread_123`
  - `pm_copilot_email_thread_456`
  - `pm_copilot_calendar_thread_789`

### **2. No Date-Based Sessions**
- **❌ NEVER**: Include dates in session IDs
- **✅ ALWAYS**: Use thread ID as primary grouping mechanism
- **Reason**: Threads span multiple days - keep everything grouped

### **3. Testing Environment**
- **Rule**: No Langfuse data during testing
- **Implementation**: `TESTING=true` → `LANGFUSE_ENABLED=false`
- **Verification**: Check environment before initializing Langfuse

---

## 🏗️ **Implementation Patterns**

### **Pattern 1: Service Initialization**

```python
class YourService:
    def __init__(self, service_name: str):
        self.service_name = service_name
        
        # Check testing environment first
        is_testing = os.getenv("TESTING", "false").lower() == "true"
        langfuse_enabled = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"
        
        # Disable Langfuse during testing
        if is_testing:
            langfuse_enabled = False
            
        if langfuse_enabled:
            self.langfuse = Langfuse(
                secret_key=os.getenv('LANGFUSE_SECRET_KEY'),
                public_key=os.getenv('LANGFUSE_PUBLIC_KEY'),
                host=os.getenv('LANGFUSE_HOST', 'http://localhost:4000'),
                flush_at=1,
                flush_interval=1
            )
        else:
            self.langfuse = None
    
    def create_session_id(self, thread_id: str) -> str:
        return f"pm_copilot_{self.service_name}_{thread_id}"
```

### **Pattern 2: Workflow Tracing**

```python
def process_workflow(self, thread_id: str, user_input: str):
    if not self.langfuse:
        return self._process_without_tracing(user_input)
    
    session_id = self.create_session_id(thread_id)
    
    with self.langfuse.start_as_current_span(
        name=f"{self.service_name}_workflow",
        input={"user_input": user_input, "thread_id": thread_id},
        metadata={"service": self.service_name}
    ) as main_span:
        main_span.update_trace(
            session_id=session_id,
            user_id=f"thread_{thread_id}",
            tags=[self.service_name, "pm_copilot", "workflow"]
        )
        
        return self._process_with_tracing(user_input, main_span)
```

### **Pattern 3: LLM Call Tracing**

```python
@observe(as_type="generation", name="llm_operation_name")
def call_llm(self, prompt: str):
    """
    REQUIRED: Use @observe decorator for ALL LLM calls
    - as_type="generation" for LLM calls
    - name should describe the operation clearly
    """
    return self.llm.invoke(prompt)

# Alternative: Manual generation for complex cases
def complex_llm_call(self, prompt: str, parent_span):
    if not self.langfuse:
        return self.llm.invoke(prompt)
        
    generation = self.langfuse.generation(
        name="complex_llm_operation",
        model="claude-3-sonnet",
        input={"prompt": prompt},
        trace_id=parent_span.trace_id
    )
    
    result = self.llm.invoke(prompt)
    
    generation.end(
        output={"response": result.content},
        usage={"total_tokens": len(result.content) // 4}  # Estimate
    )
    
    return result
```

---

## 📊 **Session Categories**

### **Primary Sessions**
| Service | Session Format | Purpose |
|---------|----------------|---------|
| **Conversation** | `pm_copilot_conversation_{thread_id}` | Main user interactions |
| **Email** | `pm_copilot_email_{thread_id}` | Email search/operations |
| **Calendar** | `pm_copilot_calendar_{thread_id}` | Calendar operations |
| **Drafts** | `pm_copilot_drafts_{thread_id}` | Draft creation/management |

### **Metadata Requirements**

```python
# REQUIRED: Always include these metadata fields
metadata = {
    "service": self.service_name,
    "thread_id": thread_id,
    "timestamp": datetime.now().isoformat(),
    "environment": os.getenv("ENVIRONMENT", "development")
}

# OPTIONAL: Add service-specific metadata
if self.service_name == "email":
    metadata.update({
        "email_count": len(emails),
        "search_query": query
    })
```

---

## 🚫 **What NOT to Do**

### **❌ Forbidden Patterns**

1. **Date-based sessions**: `pm_copilot_conversation_2025-01-09_thread_123`
2. **Testing data pollution**: Creating traces when `TESTING=true`
3. **Missing error handling**: Failing when Langfuse is unavailable
4. **Complex custom abstractions**: Use standard Langfuse patterns
5. **Inconsistent naming**: Follow exact naming conventions

### **❌ Bad Examples**

```python
# DON'T: Date in session ID
session_id = f"conversation_{datetime.now().strftime('%Y-%m-%d')}_{thread_id}"

# DON'T: Complex custom service layers
class ComplexLangfuseWrapper:
    def create_super_trace(self): ...

# DON'T: Missing testing check
langfuse = Langfuse()  # Will pollute test data!

# DON'T: Inconsistent naming
session_id = "my_custom_session_name"
```

---

## ✅ **Testing Rules**

### **Environment Setup**
```bash
# Testing environment - NO Langfuse data
TESTING=true
LANGFUSE_ENABLED=false  # Automatically set when TESTING=true

# Development environment - WITH Langfuse
TESTING=false
LANGFUSE_ENABLED=true
```

### **Mock Integration**
```python
# In test fixtures (conftest.py)
@pytest.fixture
def mock_langfuse_client():
    """Mock Langfuse client for testing"""
    if os.getenv("TESTING", "false").lower() == "true":
        # Return None or mock client
        return None
    else:
        # Return real client for development
        return Langfuse(...)
```

---

## 🔍 **Error Handling**

### **Required Pattern**
```python
def safe_langfuse_operation(self):
    if not self.langfuse:
        return self._fallback_operation()
    
    try:
        # Langfuse operations
        return self._traced_operation()
    except Exception as e:
        print(f"⚠️ Langfuse operation failed: {e}")
        # NEVER fail the main operation due to tracing issues
        return self._fallback_operation()
```

### **Graceful Degradation**
- **Always** provide fallback functionality
- **Never** fail user operations due to tracing issues
- **Log** errors but continue processing
- **Flush** traces safely with error handling

---

## 📝 **Prompt Management**

### **Standard Pattern**
```python
def get_managed_prompt(self, prompt_name: str, **variables):
    if not self.langfuse:
        return self._get_fallback_prompt(prompt_name, **variables)
    
    try:
        prompt = self.langfuse.get_prompt(prompt_name, label="production")
        return prompt.compile(**variables)
    except Exception as e:
        print(f"⚠️ Failed to get managed prompt: {e}")
        return self._get_fallback_prompt(prompt_name, **variables)
```

### **Naming Convention**
- Format: `pm-copilot-{service}-{operation}`
- Examples:
  - `pm-copilot-intent-router`
  - `pm-copilot-email-summarization`
  - `pm-copilot-calendar-analysis`

---

## 🎯 **Quality Standards**

### **Trace Quality Checklist**
- [ ] Session ID follows thread-based format
- [ ] Proper input/output data captured
- [ ] Rich metadata included
- [ ] Error handling implemented
- [ ] Testing environment respected
- [ ] Performance impact minimal (<5%)

### **Session Quality Checklist**
- [ ] One session per conversation thread
- [ ] All thread activity grouped together
- [ ] No date fragmentation
- [ ] Proper tags and user_id set
- [ ] Workflow context clear

---

## 🚀 **Quick Start Checklist**

For any new service or AI agent:

1. **✅ Environment Check**
   - Verify `TESTING` and `LANGFUSE_ENABLED` flags
   - Initialize Langfuse client safely

2. **✅ Session Creation**
   - Use thread-based session ID format
   - Include required metadata

3. **✅ Trace Implementation**
   - Use `@observe` decorators for LLM calls
   - Context managers for workflows
   - Proper error handling

4. **✅ Testing Integration**
   - Mock Langfuse during tests
   - No test data pollution
   - Preserve functionality when disabled

5. **✅ Documentation**
   - Follow naming conventions
   - Include usage examples
   - Update this document if needed

---

## 📞 **Support & Questions**

- **Documentation**: This file is the source of truth
- **Examples**: See `services/langfuse_service.py` and related files
- **Testing**: Use `tests/test_optimized_integration.py` patterns
- **Issues**: Create tickets for clarification or updates

---

## 🔄 **Version & Updates**

- **Version**: 1.0 (Post-Standardization)
- **Last Updated**: January 2025
- **Next Review**: When adding new services or major changes

**Remember**: These rules ensure consistency, reliability, and clean analytics across all PM Co-Pilot services. When in doubt, follow the patterns shown here exactly.