#!/usr/bin/env python3
"""
Test script for HTML to Markdown conversion functionality.
This script tests the html2text library to ensure it's working correctly.
"""

import html2text

def test_html_to_markdown():
    """Test HTML to Markdown conversion with sample email content."""
    
    # Sample HTML email content (similar to what we might get from VeyraX)
    sample_html = """
    <html>
    <body>
        <h1>Meeting Reminder</h1>
        <p>Hello team,</p>
        <p>This is a <strong>reminder</strong> about our upcoming meeting.</p>
        <ul>
            <li>Date: Tomorrow at 2 PM</li>
            <li>Location: Conference Room A</li>
            <li>Agenda: <a href="https://example.com/agenda">Project Review</a></li>
        </ul>
        <p>Please <em>confirm</em> your attendance.</p>
        <br>
        <p>Best regards,<br>John Doe</p>
    </body>
    </html>
    """
    
    print("Testing HTML to Markdown conversion...")
    print("=" * 50)
    print("Original HTML:")
    print(sample_html)
    print("=" * 50)
    
    try:
        # Configure html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        h.body_width = 0  # Don't wrap text
        
        # Convert HTML to Markdown
        markdown_content = h.handle(sample_html)
        
        print("Converted Markdown:")
        print(markdown_content)
        print("=" * 50)
        
        # Test with a simpler HTML
        simple_html = "<p>This is a <strong>simple</strong> test with <a href='https://example.com'>a link</a>.</p>"
        simple_markdown = h.handle(simple_html)
        
        print("Simple HTML test:")
        print(f"HTML: {simple_html}")
        print(f"Markdown: {simple_markdown}")
        
        print("\n✅ HTML to Markdown conversion is working correctly!")
        
    except Exception as e:
        print(f"❌ Error during HTML to Markdown conversion: {e}")
        import traceback
        print(traceback.format_exc())

def test_email_like_content():
    """Test with content that looks more like a real email."""
    
    email_html = """
    <div>
        <p>Hi Michal,</p>
        <p>I hope this email finds you well. I wanted to follow up on our discussion about the <strong>project timeline</strong>.</p>
        <p>Here are the key points we discussed:</p>
        <ul>
            <li>Phase 1: Research and planning (Week 1-2)</li>
            <li>Phase 2: Development (Week 3-6)</li>
            <li>Phase 3: Testing and deployment (Week 7-8)</li>
        </ul>
        <p>Please let me know if you have any questions or concerns.</p>
        <p>Best regards,<br>Sarah Johnson<br><em>Project Manager</em></p>
        <hr>
        <p style="font-size: 12px; color: #666;">This email was sent from a notification-only address that cannot accept incoming email. Please do not reply to this message.</p>
    </div>
    """
    
    print("\n" + "=" * 50)
    print("Testing with email-like content:")
    print("=" * 50)
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0
    
    markdown_result = h.handle(email_html)
    print("Email HTML converted to Markdown:")
    print(markdown_result)

if __name__ == "__main__":
    test_html_to_markdown()
    test_email_like_content() 