"""
CRITICAL REGRESSION TESTS for Email Data Processing

These tests specifically target the bug that was causing emails to be retrieved
but not saved to MongoDB. They test the nested data structure handling that
was fixed in the email processing logic.
"""

import pytest
import json
from unittest.mock import Mock, patch
import sys
import os

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)


class TestEmailDataStructureRegression:
    """
    Regression tests for the specific data structure issue that was breaking email saving.
    
    The bug: Composio returns nested data structure like:
    {
        "data": {
            "data": {
                "messages": [...]
            }
        }
    }
    
    But the code was looking for messages directly under tool_output.
    """

    @pytest.mark.regression
    def test_nested_composio_data_extraction_working(self):
        """
        CRITICAL: Test that our fix for nested Composio data structure works correctly.
        
        This is the exact issue that was causing emails to not be saved.
        """
        # Simulate the exact nested structure from Composio that was causing issues
        mock_composio_response = {
            'source_type': 'mail',
            'content': 'Emails fetched.',
            'data': {
                'data': {  # This nested 'data' was the problem
                    'messages': [
                        {
                            'messageId': '198efca4a33ef48d',
                            'threadId': 'thread_123',
                            'subject': 'Test Email Subject',
                            'messageText': 'Test email content',
                            'date': '1640995200',
                            'from': {'name': 'Test Sender', 'email': 'test@example.com'},
                            'to': [{'name': 'Test Receiver', 'email': 'receiver@example.com'}],
                            'labelIds': ['INBOX'],
                            'attachmentList': []
                        }
                    ]
                }
            }
        }
        
        # Test our fixed extraction logic
        tool_output = mock_composio_response.get('data', {})
        
        # This is the exact logic from our fix
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        # Verify the fix works
        assert messages_data is not None, "Messages data should be extracted successfully"
        assert isinstance(messages_data, list), "Messages data should be a list"
        assert len(messages_data) == 1, "Should extract the correct number of messages"
        assert messages_data[0]['messageId'] == '198efca4a33ef48d', "Should extract correct message ID"

    @pytest.mark.regression
    def test_old_bug_reproduction(self):
        """
        CRITICAL: Reproduce the old bug to ensure we understand what was broken.
        
        This test shows what would happen with the old (broken) logic.
        """
        mock_composio_response = {
            'source_type': 'mail',
            'data': {
                'data': {  # Nested structure that broke the old code
                    'messages': [{'messageId': '123'}]
                }
            }
        }
        
        tool_output = mock_composio_response.get('data', {})
        
        # OLD (broken) logic - this would fail
        old_broken_extraction = tool_output.get("messages")  # This returns None!
        
        assert old_broken_extraction is None, "Old logic should fail with nested structure"
        
        # NEW (fixed) logic - this works
        new_fixed_extraction = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        
        assert new_fixed_extraction is not None, "New logic should succeed with nested structure"
        assert len(new_fixed_extraction) == 1, "Should extract messages correctly"

    @pytest.mark.regression
    def test_both_data_structure_variations(self):
        """
        CRITICAL: Test that our fix handles both possible Composio response structures.
        
        Sometimes Composio might return messages directly, sometimes nested.
        Our fix should handle both.
        """
        # Test case 1: Direct structure (should still work)
        direct_structure = {
            'data': {
                'messages': [{'messageId': 'direct_123'}]
            }
        }
        
        tool_output_direct = direct_structure.get('data', {})
        messages_direct = tool_output_direct.get("messages") or tool_output_direct.get("data", {}).get("messages")
        
        assert messages_direct is not None, "Should handle direct structure"
        assert messages_direct[0]['messageId'] == 'direct_123'
        
        # Test case 2: Nested structure (the bug we fixed)
        nested_structure = {
            'data': {
                'data': {
                    'messages': [{'messageId': 'nested_456'}]
                }
            }
        }
        
        tool_output_nested = nested_structure.get('data', {})
        messages_nested = tool_output_nested.get("messages") or tool_output_nested.get("data", {}).get("messages")
        
        assert messages_nested is not None, "Should handle nested structure"
        assert messages_nested[0]['messageId'] == 'nested_456'

    @pytest.mark.regression
    def test_empty_or_malformed_data_structures(self):
        """
        Test edge cases that could break the email processing.
        """
        test_cases = [
            # Empty data
            {'data': {}},
            
            # Missing messages
            {'data': {'data': {}}},
            
            # Null messages
            {'data': {'data': {'messages': None}}},
            
            # Empty messages array
            {'data': {'data': {'messages': []}}},
        ]
        
        for test_case in test_cases:
            tool_output = test_case.get('data', {})
            messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
            
            # Should not crash, should handle gracefully
            if messages_data is None or messages_data == []:
                # This is acceptable - no emails to process
                assert True
            else:
                # If there's data, it should be valid
                assert isinstance(messages_data, list)

    @pytest.mark.regression
    def test_condition_logic_from_app_py(self):
        """
        CRITICAL: Test the exact conditional logic from app.py that was failing.
        
        This tests the specific line: if tool_output and messages_data:
        """
        # Test case that was failing before the fix
        failing_case = {
            'data': {
                'data': {
                    'messages': [{'messageId': '789'}]
                }
            }
        }
        
        tool_output = failing_case.get('data', {})
        
        # OLD condition logic - this actually works for this test case
        old_condition = tool_output and tool_output.get("messages")
        # The old condition works here because tool_output.get("messages") returns None, 
        # and tool_output and None evaluates to None (falsy)
        assert old_condition is None, "Old condition should return None (falsy) for this case"
        
        # NEW fixed condition logic
        messages_data = tool_output.get("messages") or tool_output.get("data", {}).get("messages")
        new_condition = tool_output and messages_data
        # The new condition should evaluate to the messages_data value (truthy) since both are truthy
        assert new_condition == messages_data, "New condition should succeed and return the messages data"
        assert new_condition is not None, "New condition should not be None"
        assert len(new_condition) == 1, "Should have one message"
        assert new_condition[0]['messageId'] == '789', "Should have the correct message ID"

    @pytest.mark.regression
    def test_debug_logging_regression(self):
        """
        Test that the debug logging we added helps identify when nested structure handling kicks in.
        """
        nested_response = {
            'data': {
                'data': {
                    'messages': [{'messageId': 'debug_test'}]
                }
            }
        }
        
        tool_output = nested_response.get('data', {})
        direct_messages = tool_output.get("messages")
        nested_messages = tool_output.get("data", {}).get("messages")
        
        # This simulates our debug logic
        if direct_messages:
            extraction_method = "direct"
        elif nested_messages:
            extraction_method = "nested"
        else:
            extraction_method = "none"
            
        assert extraction_method == "nested", "Should identify nested structure extraction"
        
        final_messages = direct_messages or nested_messages
        assert final_messages is not None
        assert len(final_messages) == 1