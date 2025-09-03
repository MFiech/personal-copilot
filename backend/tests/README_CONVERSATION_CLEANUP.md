# Conversation Cleanup for Tests

This document explains how to use the new conversation cleanup functionality to prevent test conversations from cluttering your database.

## Problem

Previously, tests that created `Conversation` objects would leave them in the database after the test completed, leading to:
- Cluttered conversation lists in the UI
- Database bloat over time
- Potential test interference

## Solution

We've added comprehensive conversation cleanup functionality with multiple levels of protection:

### 1. Individual Test Cleanup (`conversation_cleanup` fixture)

Use this fixture in tests that create conversations to automatically clean them up after the test.

```python
def test_my_feature(self, test_db, clean_collections, conversation_cleanup):
    """Test that creates conversations"""
    # Track thread_id for cleanup
    test_thread_id = 'my_test_thread_123'
    conversation_cleanup(test_thread_id)
    
    # Create conversation
    conversation = Conversation(
        thread_id=test_thread_id,
        role='assistant',
        content='Test conversation'
    )
    conversation.save()
    
    # Test logic here...
    # Conversation will be automatically deleted after test
```

### 2. Session-Level Cleanup (`cleanup_all_test_conversations` fixture)

This fixture automatically runs at the end of the entire test session and removes any conversations with thread_ids containing test-related keywords:
- `test`
- `integration`
- `e2e`
- `workflow`
- `sample`

This provides a safety net in case individual tests don't use the `conversation_cleanup` fixture.

### 3. Manual Cleanup Methods

The `Conversation` model now includes cleanup methods:

```python
# Delete all conversations in a specific thread
deleted_count = Conversation.delete_by_thread_id('my_thread_123')

# Delete all test conversations (bulk cleanup)
deleted_count = Conversation.delete_test_conversations()
```

## Usage Examples

### Basic Usage

```python
def test_calendar_feature(self, test_db, clean_collections, conversation_cleanup):
    """Basic usage example"""
    # Track thread for cleanup
    thread_id = 'calendar_test_123'
    conversation_cleanup(thread_id)
    
    # Create conversation
    conversation = Conversation(
        thread_id=thread_id,
        role='assistant',
        content='Calendar test'
    )
    conversation.save()
    
    # Your test logic here...
```

### Multiple Conversations

```python
def test_multiple_conversations(self, test_db, clean_collections, conversation_cleanup):
    """Track multiple conversations for cleanup"""
    thread_ids = ['test_1', 'test_2', 'test_3']
    
    # Track all threads
    for thread_id in thread_ids:
        conversation_cleanup(thread_id)
    
    # Create multiple conversations
    for thread_id in thread_ids:
        conversation = Conversation(thread_id=thread_id, role='assistant', content='Test')
        conversation.save()
    
    # All will be cleaned up automatically
```

### Dynamic Thread IDs

```python
def test_dynamic_threads(self, test_db, clean_collections, conversation_cleanup):
    """Use dynamic thread IDs"""
    import time
    
    # Create dynamic thread ID
    thread_id = f'dynamic_test_{int(time.time())}'
    conversation_cleanup(thread_id)
    
    # Create conversation
    conversation = Conversation(thread_id=thread_id, role='assistant', content='Dynamic test')
    conversation.save()
    
    # Will be cleaned up automatically
```

## Best Practices

### 1. Always Track Before Creating

```python
# ✅ GOOD: Track thread_id before creating conversation
thread_id = 'my_test_123'
conversation_cleanup(thread_id)

conversation = Conversation(thread_id=thread_id, role='assistant', content='Test')
conversation.save()
```

```python
# ❌ BAD: Forgot to track thread_id
conversation = Conversation(thread_id='my_test_123', role='assistant', content='Test')
conversation.save()
# This conversation won't be cleaned up!
```

### 2. Use Descriptive Thread IDs

```python
# ✅ GOOD: Descriptive thread IDs
thread_id = 'test_calendar_deletion_integration_123'
conversation_cleanup(thread_id)
```

```python
# ❌ BAD: Generic thread IDs
thread_id = 'test123'
conversation_cleanup(thread_id)
```

### 3. Combine with Existing Fixtures

```python
# ✅ GOOD: Use both cleanup fixtures
def test_feature(self, test_db, clean_collections, conversation_cleanup):
    # clean_collections: Cleans all collections before/after test
    # conversation_cleanup: Tracks and cleans specific conversations
    pass
```

### 4. Handle Nonexistent Threads Gracefully

```python
# ✅ GOOD: Cleanup handles nonexistent threads gracefully
thread_id = 'nonexistent_thread_123'
conversation_cleanup(thread_id)  # No error if thread doesn't exist
```

## Migration Guide

### For Existing Tests

1. Add `conversation_cleanup` parameter to test methods that create conversations
2. Call `conversation_cleanup(thread_id)` before creating conversations
3. Use descriptive thread IDs

### Before (Old Way)
```python
def test_old_way(self, test_db, clean_collections):
    conversation = Conversation(
        thread_id='test_123',
        role='assistant',
        content='Test'
    )
    conversation.save()
    # Conversation left in database!
```

### After (New Way)
```python
def test_new_way(self, test_db, clean_collections, conversation_cleanup):
    thread_id = 'descriptive_test_123'
    conversation_cleanup(thread_id)  # Track for cleanup
    
    conversation = Conversation(
        thread_id=thread_id,
        role='assistant',
        content='Test'
    )
    conversation.save()
    # Conversation automatically cleaned up!
```

## Files Modified

- `backend/models/conversation.py` - Added cleanup methods
- `backend/tests/conftest.py` - Added cleanup fixtures
- `backend/tests/test_calendar_delete_integration.py` - Updated to use cleanup
- `backend/tests/test_conversation_cleanup_example.py` - Example usage

## Testing the Cleanup

Run the example tests to verify cleanup is working:

```bash
cd backend
python -m pytest tests/test_conversation_cleanup_example.py -v
```

You should see cleanup messages in the output:
```
[TEST CLEANUP] Deleted 1 conversations from 1 threads
[SESSION CLEANUP] Deleted 0 test conversations
```

## Troubleshooting

### Conversations Still Appearing

1. Check if you're using the `conversation_cleanup` fixture
2. Verify you're calling `conversation_cleanup(thread_id)` before creating conversations
3. Check if thread_id contains test-related keywords (will be caught by session cleanup)

### Cleanup Not Working

1. Verify the test is using the `test_db` fixture
2. Check that MongoDB is running and accessible
3. Look for error messages in test output

### Performance Issues

1. The session cleanup runs once at the end of all tests
2. Individual test cleanup is very fast
3. If you have many test conversations, consider running `Conversation.delete_test_conversations()` manually

## Future Improvements

- Add automatic cleanup for other test data types (emails, etc.)
- Add cleanup statistics reporting
- Add cleanup verification tests
- Consider adding cleanup to CI/CD pipeline
