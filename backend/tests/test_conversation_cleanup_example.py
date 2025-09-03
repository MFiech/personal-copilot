"""
Example test file demonstrating how to use the conversation cleanup fixtures.

This file shows the proper way to use the conversation_cleanup fixture
to ensure test conversations are properly cleaned up after each test.
"""

import pytest
from models.conversation import Conversation


class TestConversationCleanupExample:
    """Example tests showing proper conversation cleanup usage"""
    
    def test_create_conversation_with_cleanup(self, test_db, clean_collections, conversation_cleanup):
        """Example: Create a conversation and track it for cleanup"""
        # Track the thread_id for cleanup
        test_thread_id = 'example_test_thread_123'
        conversation_cleanup(test_thread_id)
        
        # Create a test conversation
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='This is a test conversation',
            tool_results={'test_data': 'example'}
        )
        conversation.save()
        
        # Verify conversation was created
        saved_conversation = Conversation.find_one({'thread_id': test_thread_id})
        assert saved_conversation is not None
        assert saved_conversation['content'] == 'This is a test conversation'
        
        # The conversation will be automatically cleaned up after the test
    
    def test_create_multiple_conversations_with_cleanup(self, test_db, clean_collections, conversation_cleanup):
        """Example: Create multiple conversations and track them all for cleanup"""
        thread_ids = ['multi_test_1', 'multi_test_2', 'multi_test_3']
        
        # Track all thread_ids for cleanup
        for thread_id in thread_ids:
            conversation_cleanup(thread_id)
        
        # Create multiple test conversations
        for i, thread_id in enumerate(thread_ids):
            conversation = Conversation(
                thread_id=thread_id,
                role='assistant',
                content=f'Test conversation {i+1}',
                tool_results={'test_index': i}
            )
            conversation.save()
        
        # Verify all conversations were created
        for i, thread_id in enumerate(thread_ids):
            saved_conversation = Conversation.find_one({'thread_id': thread_id})
            assert saved_conversation is not None
            assert saved_conversation['content'] == f'Test conversation {i+1}'
        
        # All conversations will be automatically cleaned up after the test
    
    def test_conversation_cleanup_handles_nonexistent_threads(self, test_db, clean_collections, conversation_cleanup):
        """Example: Cleanup fixture handles nonexistent threads gracefully"""
        # Track a thread that doesn't exist
        nonexistent_thread_id = 'nonexistent_thread_456'
        conversation_cleanup(nonexistent_thread_id)
        
        # Try to find the nonexistent conversation
        conversation = Conversation.find_one({'thread_id': nonexistent_thread_id})
        assert conversation is None
        
        # Cleanup will handle this gracefully (no error)
    
    def test_conversation_cleanup_with_dynamic_thread_ids(self, test_db, clean_collections, conversation_cleanup):
        """Example: Use dynamic thread IDs and track them for cleanup"""
        import time
        
        # Create dynamic thread IDs
        timestamp = int(time.time())
        thread_ids = [
            f'dynamic_test_{timestamp}_1',
            f'dynamic_test_{timestamp}_2'
        ]
        
        # Track all dynamic thread_ids for cleanup
        for thread_id in thread_ids:
            conversation_cleanup(thread_id)
        
        # Create conversations with dynamic IDs
        for i, thread_id in enumerate(thread_ids):
            conversation = Conversation(
                thread_id=thread_id,
                role='assistant',
                content=f'Dynamic test conversation {i+1}',
                tool_results={'timestamp': timestamp, 'index': i}
            )
            conversation.save()
        
        # Verify conversations were created
        for i, thread_id in enumerate(thread_ids):
            saved_conversation = Conversation.find_one({'thread_id': thread_id})
            assert saved_conversation is not None
            assert saved_conversation['content'] == f'Dynamic test conversation {i+1}'
        
        # All dynamic conversations will be automatically cleaned up after the test


class TestConversationCleanupBestPractices:
    """Best practices for using conversation cleanup in tests"""
    
    def test_always_track_thread_ids_before_creating_conversations(self, test_db, clean_collections, conversation_cleanup):
        """Best Practice: Always track thread_ids before creating conversations"""
        # ✅ GOOD: Track thread_id before creating conversation
        test_thread_id = 'best_practice_thread_123'
        conversation_cleanup(test_thread_id)
        
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Best practice conversation'
        )
        conversation.save()
        
        # Verify it was created
        saved_conversation = Conversation.find_one({'thread_id': test_thread_id})
        assert saved_conversation is not None
    
    def test_use_descriptive_thread_ids(self, test_db, clean_collections, conversation_cleanup):
        """Best Practice: Use descriptive thread IDs that clearly indicate they're test data"""
        # ✅ GOOD: Descriptive thread IDs
        test_thread_id = 'test_calendar_deletion_integration_123'
        conversation_cleanup(test_thread_id)
        
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Descriptive thread ID conversation'
        )
        conversation.save()
        
        # Verify it was created
        saved_conversation = Conversation.find_one({'thread_id': test_thread_id})
        assert saved_conversation is not None
    
    def test_cleanup_works_with_existing_clean_collections_fixture(self, test_db, clean_collections, conversation_cleanup):
        """Best Practice: Use both clean_collections and conversation_cleanup fixtures together"""
        # Both fixtures work together:
        # - clean_collections: Cleans all collections before/after test
        # - conversation_cleanup: Tracks and cleans specific conversations
        
        test_thread_id = 'combined_fixtures_test_123'
        conversation_cleanup(test_thread_id)
        
        conversation = Conversation(
            thread_id=test_thread_id,
            role='assistant',
            content='Combined fixtures test'
        )
        conversation.save()
        
        # Verify it was created
        saved_conversation = Conversation.find_one({'thread_id': test_thread_id})
        assert saved_conversation is not None
